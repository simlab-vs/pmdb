"""Splits calculator programs into tokens."""

KEYWORDS = {"let", "in", "if", "then", "else", "fn"}
OPERATORS = ["==", "!=", "<=", ">=", "&&", "||", "+", "-", "*", "/", "%", "<", ">", "!", "(", ")",
             ",", "="]


class LexError(Exception):
  pass


def tokenize(source):
  """Returns the tokens of `source` as a list of `(kind, text, position)` triples."""
  tokens = []
  i = 0
  while i < len(source):
    c = source[i]
    if c.isspace():
      i += 1
    elif c.isdigit():
      j = i
      while j < len(source) and source[j].isdigit():
        j += 1
      tokens.append(("int", source[i:j], i))
      i = j
    elif c.isalpha() or c == "_":
      j = i
      while j < len(source) and (source[j].isalnum() or source[j] == "_"):
        j += 1
      word = source[i:j]
      tokens.append(("keyword" if word in KEYWORDS else "name", word, i))
      i = j
    else:
      for op in OPERATORS:
        if source.startswith(op, i):
          tokens.append(("op", op, i))
          i += len(op)
          break
      else:
        raise LexError(f"unexpected character {c!r} at {i}")
  tokens.append(("end", "", len(source)))
  return tokens
