def orelse(a, b):
  """Returns `a` iff it is not `None`. Otherwise, returns `b()`"""
  if a is None:
    return b()
  else:
    return a
