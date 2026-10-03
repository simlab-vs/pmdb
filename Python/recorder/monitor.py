"""Recording every call made in a program's own code, without modifying it.

    import recorder
    with recorder.recording("trace.pmdb"):    # records the calls of code under the current directory
      main()

A `Monitor` uses `sys.monitoring` (Python 3.12 and later) to record each call of a function whose
code is in one of its roots and not in an installed package (`site-packages`) or the standard
library: its arguments, by parameter name, as they were when the call started, and the value it
returned or the exception it raised. Generators and coroutines are recorded once per call, from
when they start running to when they finish; the calls they make when they are resumed are
nested in them. Calls made by different threads are recorded in separate branches of the tree.

`snap(label, value)` records a value with a label in the call being run, if a monitor is
recording, and returns `value`.
"""

import contextlib
import os
import sys
import sysconfig
import threading
import uuid

from .archive import describe
from .recorder import Call, NamedCall, Outcome, Snapshot, write_trace

PACKAGE = os.path.dirname(os.path.abspath(__file__))

# The flags of the code objects of generators, coroutines and asynchronous generators.
SUSPENDABLE = 0x20 | 0x80 | 0x100 | 0x200
OPTIMIZED, VARARGS, VARKEYWORDS = 0x01, 0x04, 0x08

# The monitor recording, if any.
active = None


def snap(label, value):
  """Records `value` with `label` (a string) in the call being run, if a monitor is recording,
  and returns `value`."""
  if active is not None:
    active.snap(label, value, sys._getframe(1))
  return value


@contextlib.contextmanager
def recording(path, roots=None, exclude=()):
  """Records the calls made while running the body of the `with` statement and writes the trace
  to `path` when it ends (even if it raises). See `Monitor` for `roots` and `exclude`."""
  m = Monitor(roots, exclude)
  m.start()
  try:
    yield m
  finally:
    m.stop()
    m.write(path)


class Monitor(object):
  """Records the calls of the functions defined in the Python files under `roots` (by default,
  the current directory), except those under a directory in `exclude`, in an installed package
  or in the standard library."""

  def __init__(self, roots=None, exclude=()):
    self.identifier = uuid.uuid4()
    self.roots = [self.directory(r) for r in (roots or [os.getcwd()])]
    paths = sysconfig.get_paths()
    self.exclude = [self.directory(d) for d in exclude] + [
      self.directory(paths[k]) for k in ("stdlib", "platstdlib", "purelib", "platlib")
      if k in paths] + [self.directory(PACKAGE)]
    self.observations = [Call("<root>", 0, "root", [], {})]
    self.parent = [0]
    self.stacks = {}      # thread identifier -> [(frame, index of its call)]
    self.suspended = {}   # frame of a generator or coroutine -> index of its call
    self.encoding = set() # threads encoding values, whose calls aren't recorded
    self.decisions = {}   # code object -> whether its calls are recorded
    self.tool = None
    self.failures = 0

  @staticmethod
  def directory(path):
    return os.path.join(os.path.realpath(path), "")

  def records(self, code):
    """Returns whether the calls running `code` are recorded."""
    decision = self.decisions.get(code)
    if decision is None:
      name, file = code.co_name, code.co_filename
      decision = False
      # Class bodies and modules aren't optimized; comprehensions and lambdas are named `<…>`.
      # `__annotate__` functions are generated for annotations (Python 3.14).
      if (code.co_flags & OPTIMIZED and not name.startswith("<") and not file.startswith("<")
          and name != "__annotate__"):
        path = os.path.realpath(file)
        decision = (any(path.startswith(r) for r in self.roots)
                    and not any(path.startswith(d) for d in self.exclude)
                    and os.sep + "site-packages" + os.sep not in path
                    and os.sep + "dist-packages" + os.sep not in path)
      self.decisions[code] = decision
    return decision

  # Recording.

  def start(self):
    """Starts recording."""
    global active
    if active is not None:
      raise RuntimeError("a monitor is already recording")
    m, e = sys.monitoring, sys.monitoring.events
    # Identifiers 3 and 4 aren't reserved for debuggers, coverage tools, profilers or optimizers.
    for tool in (4, 3, m.PROFILER_ID, m.COVERAGE_ID):
      if m.get_tool(tool) is None:
        break
    else:
      raise RuntimeError("no sys.monitoring tool identifier is free")
    m.use_tool_id(tool, "pmdb")
    self.tool = tool
    callbacks = {
      e.PY_START: self.on_start, e.PY_RESUME: self.on_resume, e.PY_THROW: self.on_throw,
      e.PY_YIELD: self.on_yield, e.PY_RETURN: self.on_return, e.PY_UNWIND: self.on_unwind}
    for event, f in callbacks.items():
      m.register_callback(tool, event, f)
    m.set_events(tool, sum(callbacks))
    active = self

  def stop(self):
    """Stops recording."""
    global active
    if self.tool is None:
      return
    m = sys.monitoring
    m.set_events(self.tool, 0)
    m.free_tool_id(self.tool)
    self.tool = None
    active = None
    if self.failures:
      print(f"pmdb: {self.failures} events could not be recorded", file=sys.stderr)

  def write(self, path):
    """Writes the trace to `path`."""
    with open(path, "wb") as f:
      f.write(write_trace(self.identifier, self.observations, self.parent).buffer)

  def encoded(self, make, *args):
    """Returns `make(*args)`, which encodes values, without recording the calls it makes."""
    thread = threading.get_ident()
    self.encoding.add(thread)
    try:
      return make(*args)
    finally:
      self.encoding.discard(thread)

  def append(self, observation, parent):
    self.observations.append(observation)
    self.parent.append(parent)
    return len(self.observations) - 1

  def stack(self):
    thread = threading.get_ident()
    s = self.stacks.get(thread)
    if s is None:
      s = self.stacks[thread] = []
    return s

  def leave(self, frame):
    """Removes the entry of `frame` from the current thread's stack, returning its call's index."""
    s = self.stack()
    for k in range(len(s) - 1, -1, -1):
      if s[k][0] is frame:
        index = s[k][1]
        del s[k]
        return index
    return None

  def snap(self, label, value, frame):
    if threading.get_ident() in self.encoding:
      return
    if not isinstance(label, str):
      raise TypeError(f"a snap's label must be a string, not {type(label).__name__}")
    s = self.stack()
    parent = s[-1][1] if s else 0
    self.append(self.encoded(Snapshot, frame.f_code.co_filename, frame.f_lineno, label, value),
                parent)

  # Callbacks of `sys.monitoring`. They return `DISABLE` for code that isn't recorded, so that
  # it is no longer monitored, and record their failures rather than raising them in the program.

  def on_start(self, code, offset):
    if not self.records(code):
      return sys.monitoring.DISABLE
    if threading.get_ident() in self.encoding:
      return
    try:
      frame = sys._getframe(1)
      s = self.stack()
      parent = s[-1][1] if s else 0
      caller = frame.f_back
      file, line = ((caller.f_code.co_filename, caller.f_lineno) if caller is not None
                    else (code.co_filename, code.co_firstlineno))
      positional, named = self.arguments(code, frame.f_locals)
      call = self.encoded(NamedCall, file, line, code.co_qualname,
                          (code.co_filename, code.co_firstlineno), positional, named)
      index = self.append(call, parent)
      s.append((frame, index))
      if code.co_flags & SUSPENDABLE:
        self.suspended[frame] = index
    except Exception:
      self.failed()

  def failed(self):
    self.failures += 1
    if os.environ.get("PMDB_DEBUG"):
      raise

  @staticmethod
  def arguments(code, values):
    """Returns the arguments of a call running `code`, whose local variables are `values` when
    it starts: a list of pairs of a parameter name and a positional argument (those collected by
    `*rest` named `*rest`), and a dict of the named arguments (keyword-only and `**`)."""
    names = code.co_varnames
    m, k = code.co_argcount, code.co_kwonlyargcount
    positional = [(n, values.get(n)) for n in names[:m]]
    named = {n: values.get(n) for n in names[m:m + k]}
    i = m + k
    if code.co_flags & VARARGS:
      rest = names[i]
      positional += [("*" + rest, a) for a in values.get(rest, ())]
      i += 1
    if code.co_flags & VARKEYWORDS:
      extra = values.get(names[i])
      if isinstance(extra, dict):
        named.update((str(n), a) for n, a in extra.items())
    return positional, named

  def on_resume(self, code, offset):
    if not self.records(code):
      return sys.monitoring.DISABLE
    self.resume(code)

  def on_throw(self, code, offset, exception):
    if self.records(code):
      self.resume(code)

  def resume(self, code):
    if threading.get_ident() in self.encoding:
      return
    frame = sys._getframe(2)
    index = self.suspended.get(frame)
    if index is not None:
      self.stack().append((frame, index))

  def on_yield(self, code, offset, value):
    if not self.records(code):
      return sys.monitoring.DISABLE
    if threading.get_ident() in self.encoding:
      return
    self.leave(sys._getframe(1))

  def on_return(self, code, offset, value):
    if not self.records(code):
      return sys.monitoring.DISABLE
    self.end(code, value, False)

  def on_unwind(self, code, offset, exception):
    if self.records(code):
      self.end(code, exception, True)

  def end(self, code, value, raised):
    if threading.get_ident() in self.encoding:
      return
    try:
      frame = sys._getframe(2)
      index = self.leave(frame)
      self.suspended.pop(frame, None)
      if index is None:
        return
      def make():
        v = {"type": type(value).__qualname__, "message": describe(value, str)} if raised else value
        return Outcome(code.co_filename, frame.f_lineno, index, raised, v)
      outcome = self.encoded(make)
      self.append(outcome, self.parent[index])
    except Exception:
      self.failed()
