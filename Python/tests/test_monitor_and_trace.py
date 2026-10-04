"""Tests of the recorder's monitor and of queries on the traces it writes.

Run with `python3 -m unittest discover -s Python/tests` from the repository's root.
"""

import asyncio
import os
import re
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import recorder
from recorder import Q, QueryError

PROGRAM = '''
import asyncio, collections, threading
import recorder

Txn = collections.namedtuple("Txn", "account amount")

class Ledger:
  def __init__(self):
    self.balances = {}

  def post(self, txn, *, note=""):
    if txn.amount < 0 and self.balances.get(txn.account, 0) + txn.amount < 0:
      raise ValueError(f"overdraft on {txn.account}")
    self.balances[txn.account] = self.balances.get(txn.account, 0) + txn.amount
    recorder.snap("balance", self.balances[txn.account])
    return self.balances[txn.account]

def feed(n, *extra, **options):
  for i in range(n):
    yield Txn("a" if i % 2 else "b", -5 if i == 3 else 3)
  return "fed"

def close_month(ledger, day):
  out = []
  for t in feed(5, 1, 2, flag=True):
    try:
      out.append(ledger.post(t, note="x"))
    except ValueError:
      out.append(None)
  return out

async def fetch(x):
  await asyncio.sleep(0)
  return double(x)

def double(x):
  return 2 * x

def worker(ledger):
  ledger.post(Txn("t", 1))

def main():
  ledger = Ledger()
  close_month(ledger, 30)
  close_month(ledger, 31)
  asyncio.run(fetch(2))
  t = threading.Thread(target=worker, args=(ledger,))
  t.start()
  t.join()
  sorted([3, 1, 2], key=lambda x: -x)
  return [x * 2 for x in range(3)]

main()
'''


def record(source):
  """Returns the trace of running `source` as a file of a temporary directory."""
  d = tempfile.mkdtemp()
  path = os.path.join(d, "t.pmdb")
  with recorder.recording(path, roots=[d]):
    exec(compile(source, os.path.join(d, "program.py"), "exec"), {"__name__": "program"})
  return recorder.load(path)


class MonitorTests(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    cls.t = record(PROGRAM)

  def test_functions(self):
    # Class bodies, lambdas, comprehensions and code outside the roots aren't recorded.
    self.assertEqual(self.t.functions(), {
      "Ledger.post": 11, "feed": 2, "close_month": 2, "main": 1, "Ledger.__init__": 1,
      "fetch": 1, "double": 1, "worker": 1})

  def test_arguments_by_parameter(self):
    f = self.t.calls("feed").first()
    self.assertEqual(f.params, {"n": 5, "extra": [1, 2], "flag": True})
    self.assertEqual((f["n"], f[0], f.args, f.kwargs), (5, 5, [5, 1, 2], {"flag": True}))
    p = self.t.calls("post").first()
    self.assertEqual((p["txn"], p["note"]), ({"account": "b", "amount": 3}, "x"))
    # Objects that can't be pickled (here, the module isn't importable) are recorded by `repr`.
    self.assertTrue(p["self"].startswith("<program.Ledger object at "))
    with self.assertRaisesRegex(KeyError, "has parameters self, txn, note"):
      p["amount"]
    self.assertIsNone(p.get("amount"))

  def test_outcomes(self):
    f = self.t.calls("feed").first()
    self.assertTrue(f.returned)
    self.assertEqual(f.result, "fed")
    bad = self.t.calls("post", raised="ValueError")
    self.assertEqual(len(bad), 1)
    self.assertEqual(bad[0].exception.message, "overdraft on a")
    self.assertFalse(bad[0].returned)
    self.assertEqual(self.t.calls("fetch").one().result, 4)

  def test_generators_and_coroutines(self):
    # The calls made by the consumer while the generator is suspended aren't in it.
    month = self.t.calls("close_month").first()
    self.assertEqual(month.callees().functions(), {"Ledger.post": 5, "feed": 1})
    self.assertEqual(self.t.calls("feed").first().callees(), [])
    self.assertEqual(self.t.calls("double").one().caller.function, "fetch")
    self.assertEqual(self.t.calls("fetch").one().caller.function, "main")

  def test_threads(self):
    roots = self.t.roots()
    self.assertEqual([c.function for c in roots], ["main", "worker"])
    self.assertEqual(roots[1].callees().one()["txn"], {"account": "t", "amount": 1})

  def test_snaps(self):
    self.assertEqual(self.t.snaps("balance").values(), [3, 3, 6, 9, 12, 6, 15, 1, 18, 1])
    self.assertEqual(self.t.snaps().first().call.function, "Ledger.post")
    month = self.t.calls("close_month").first()
    self.assertEqual(len(month.snaps("balance", deep=True)), 4)
    self.assertEqual(month.snaps(), [])
    self.assertIs(recorder.snap("outside", 3), 3)  # without a recording, a snap does nothing


class QueryTests(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    cls.t = record(PROGRAM)

  def test_names(self):
    self.assertEqual(len(self.t.calls("post")), 11)
    self.assertEqual(len(self.t.calls("Ledger.post")), 11)
    self.assertEqual(len(self.t.calls(re.compile(r"Ledger\..*"))), 12)
    with self.assertRaisesRegex(QueryError, "no recorded function is named 'posts'"):
      self.t.calls("posts")

  def test_relations(self):
    t = self.t
    last = Q("close_month", where=lambda c: c["day"] == 31)
    self.assertEqual(len(t.calls("post", caller=last)), 5)
    self.assertEqual(len(t.calls("post", ancestor="main")), 10)
    self.assertEqual(t.calls(callee=Q("post", raised=True)).values("day"), [30])
    self.assertEqual(t.calls(descendant=Q("post", raised=True)).functions(),
                     {"main": 1, "close_month": 1})
    bad = t.calls("post", raised=True).one()
    self.assertEqual(bad.ancestor("close_month")["day"], 30)
    self.assertEqual([c.function for c in bad.path()], ["main", "close_month", "Ledger.post"])
    same = t.calls("post", before=bad, where=lambda c: c["txn"]["account"] == bad["txn"]["account"])
    self.assertEqual(len(same), 1)
    self.assertEqual(len(t.calls("post", after=bad)), 7)
    # A generator's call ends when it finishes, after the calls made while it was suspended.
    feed = t.calls("feed").first()
    self.assertEqual(len(t.calls("post", after=feed)), 6)

  def test_combinations(self):
    t = self.t
    self.assertEqual(t.calls(~Q("post") & Q(ancestor="main")).functions(),
                     {"Ledger.__init__": 1, "close_month": 2, "feed": 2, "fetch": 1, "double": 1})
    self.assertEqual(len(t.calls(Q("feed") | Q("fetch"))), 3)
    posts = t.calls("post")
    self.assertEqual(len(posts - t.calls("post", ancestor="main")), 1)
    self.assertEqual(len(posts & t.calls(ancestor="worker")), 1)
    self.assertEqual(len(t.calls("feed") | t.calls("fetch")), 3)

  def test_outcome_conditions(self):
    t = self.t
    self.assertEqual(len(t.calls("post", returned=lambda r: r > 10)), 3)
    self.assertEqual(len(t.calls("post", returned=6)), 2)
    self.assertEqual(len(t.calls("post", raised=ValueError)), 1)
    self.assertEqual(len(t.calls("post", raised=lambda e: "overdraft" in e.message)), 1)
    self.assertEqual(len(t.calls("post", returned=False)), 1)

  def test_summaries(self):
    posts = self.t.calls("post")
    self.assertEqual(posts.count_by(lambda c: c["txn"]["account"]), {"b": 6, "a": 4, "t": 1})
    self.assertEqual({k: len(v) for k, v in posts.group_by("note").items()}, {"x": 10, "": 1})
    self.assertEqual(posts.group_by("txn").keys() >= {(("account", "a"), ("amount", 3))}, True)
    self.assertEqual(posts[:2].values(lambda c: c.result), [3, 3])
    self.assertIsInstance(posts[:2], recorder.Calls)
    with self.assertRaises(QueryError):
      posts.one()

  def test_errors(self):
    with self.assertRaisesRegex(QueryError, "the where predicate raised KeyError"):
      self.t.calls("post", where=lambda c: c["nope"])
    with self.assertRaisesRegex(TypeError, "unknown condition calls="):
      self.t.calls("post", calls="feed")
    with self.assertRaisesRegex(TypeError, "unknown condition"):
      Q("post", parent="main")

  def test_unpickle(self):
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "shapes.py"), "w") as f:
      f.write("class Box:\n  def __init__(self, w):\n    self.w = w\n  def area(self):\n"
              "    return self.w * self.w\n")
    sys.path.insert(0, d)
    try:
      import shapes
      path = os.path.join(d, "t.pmdb")
      with recorder.recording(path, roots=[d]):
        shapes.Box(3).area()
      area = recorder.load(path).calls("area").one()
      self.assertEqual(area["self"].type, "shapes.Box")
      self.assertEqual(area["self"].unpickle().w, 3)
      self.assertEqual(area.definition, (os.path.join(d, "shapes.py"), 4))
    finally:
      sys.path.remove(d)


class ValueTableTests(unittest.TestCase):

  def test_what_goes_in_the_table(self):
    from recorder.archive import ValueTable
    from recorder.recorder import encode
    table = ValueTable()
    for v in [None, True, 3, 2 ** 80, 1.5, "", "1234567"]:
      encode(v, table)
    self.assertEqual(table.entries, [])
    for v in ["12345678", [1], {"a": 1}, (1, 2), "12345678", [1]]:
      encode(v, table)
    self.assertEqual(len(table.entries), 4)
    # Elements are entries of their own, so a value shared by several containers is stored once.
    encode([["x" * 10], ["x" * 10, 1]], table)
    self.assertEqual(len(table.entries), 8)

  def test_equal_values_are_stored_once(self):
    t = record(
      "config = {'currency': 'EUR', 'rounding': 'half-even', 'accounts': list(range(100))}\n"
      "items = []\n"
      "def add(config, items, x):\n"
      "  items.append(x)\n"
      "  return config['currency']\n"
      "for i in range(50):\n"
      "  add(config, items, i)\n")
    adds = t.calls("add")
    self.assertEqual(len(adds), 50)
    self.assertEqual(adds[7]["config"]["accounts"][99], 99)
    # Arguments are recorded as they were when each call started.
    self.assertEqual(adds[3]["items"], [0, 1, 2])
    self.assertEqual(adds.values(lambda c: c.result), ["EUR"] * 50)
    # Decoded values aren't shared between calls.
    adds[0]["config"]["currency"] = "USD"
    self.assertEqual(adds[1]["config"]["currency"], "EUR")

  def test_reads_traces_without_a_table(self):
    from recorder.archive import Archive
    from recorder.recorder import Call, Snapshot
    import uuid
    a = Archive()
    a.write_bytes(b"pmdb")
    a.write_byte(1)
    a.write_byte(0)
    a.write_bytes(uuid.uuid4().bytes)
    observations = [Call("<root>", 0, "root", [], {}), Call("m.py", 3, "f", [[1, "long string"]], {}),
                    Snapshot("m.py", 3, "f.$result", {"total": 2})]
    a.write_unsigned(len(observations))
    for o in observations:
      a.write(o)
    for p in [0, 0, 0]:
      a.write_unsigned(p)
    path = os.path.join(tempfile.mkdtemp(), "old.pmdb")
    with open(path, "wb") as f:
      f.write(a.buffer)
    f = recorder.load(path).calls("f").one()
    self.assertEqual((f.args, f.result), ([[1, "long string"]], {"total": 2}))


if __name__ == "__main__":
  unittest.main()
