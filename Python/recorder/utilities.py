def orelse(a, b):
  """Returns `a` iff it is not `None`. Otherwise, returns `b()`"""
  if a is None:
    return b()
  else:
    return a

def first_where(xs, predicate):
  """Returns the first element in `xs` that satisfies `preficate`."""
  for x in xs:
    if predicate(x):
      return x
  return None
