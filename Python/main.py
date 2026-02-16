import recorder
import sys


class Sublist(object):
  """
  A slice of a list.
  """

  def __init__(self, base, lower, upper):
    """
    Creates an instance over the contents of `base` in the half-open range from `lower` to `upper`.
    """
    assert lower <= upper, "invalid bounds"
    self.lower = lower
    self.upper = upper

    if isinstance(base, Sublist):
      assert (lower >= base.lower) and (upper <= base.upper), "invalid bounds"
      self.base = base.base
    else:
      assert (lower >= 0) and (upper <= len(base)), "invalid bounds"
      self.base = base

  def __len__(self):
    """
    Returns the length of `self`.
    """
    return self.upper - self.lower

  def first_index_where(self, predicate):
    """
    Returns the position of the first element in `self` that satisfies `predicate`.
    """
    i = self.lower
    while i != self.upper:
      if predicate(self.base[i]):
        return i
      i += 1
    return None

  def swap_at(self, i, j):
    """
    Swap the contents of `self` at the specified positions.
    """
    self.base[i], self.base[j] = self.base[j], self.base[i]

  @recorder.main.record
  def partition(self, in_first_part):
    """
    Reorders the contents of `self` so that elements satisfying `in_first_part` occur first and
    returns the position immediately after the last element satisfying `in_first_part`.
    """
    i = self.first_index_where(lambda x: not in_first_part(x))
    if i is None:
      return self.upper
    j = i + 1
    while j != self.upper:
      if in_first_part(self.base[j]):
        self.swap_at(i, j)
        i += 1
      j += 1
    return i

  @recorder.main.record
  def quicksort(self, less_than):
    """
    Sorts the contents of `self` using `less_than`to compare elements.

    `less_than` implements a strict weak ordering the elements in `self`. That is, for all elements
    `a`, `b`, `c`, the following properties hold:

    * irreflexivity: `assert not less_than(a, a)`
    * transitivity: `assert not (less_than(a, b) and less_than(b, c)) or less_than(a, c)`
    """
    if len(self) <= 1:
      return
    p = self.base[self.upper - 1]
    m = Sublist(self, self.lower, self.upper - 1).partition(lambda x: less_than(x, p))
    self.swap_at(m, self.upper - 1)
    Sublist(self, self.lower, m).quicksort(less_than)
    Sublist(self, m + 1, self.upper).quicksort(less_than)


@recorder.main.record
def factorial(n):
  return 1 if n < 2 else n * factorial(n - 1)

@recorder.main.record
def gcd(a, b):
  return a if b == 0 else gcd(b, a % b)

@recorder.main.record
def rho(n):
  @recorder.main.record
  def f(x, y, d):
    if d == 1:
      x1 = g(x)
      y1 = g(g(y))
      return f(x1, y1, gcd(abs(x1 - y1), n))
    else:
      return d if n != d else None

  @recorder.main.record
  def g(x):
    return (x * x + 1) % n

  return f(2, 2, 1)

if __name__ == "__main__":
  # # xs = [1, 8, 3, 2, 6, 5, 7, 9, 4]
  # xs = [1, 8, 3]
  # ys = Sublist(xs, 0, len(xs))
  # recorder.main.run(ys.quicksort, lambda x, y: x < y)

  # recorder.main.run(factorial, 6)
  recorder.main.run(rho, 15) # rho(10403)

  a = recorder.main.serialize()
  # print([hex(b) for b in a.buffer])
  with open("trace.data", "wb") as f:
    f.write(a.buffer)

  # a = recorder.Archive()
  # a.write_object(5.1)
  # print([hex(b) for b in a.buffer])

  # ys.quicksort(lambda x, y: x < y)
  # print(ys.base)

  # n = recorder.main.run(factorial, 6)
  # print(n)
