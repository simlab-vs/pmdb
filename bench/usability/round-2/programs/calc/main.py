"""Evaluates each line of a file as a calculator program and prints its value."""

import sys

from evaluator import Closure, EvalError, evaluate
from lexer import LexError
from parser import ParseError, parse


def show(value):
  if isinstance(value, Closure) or callable(value):
    return "<function>"
  return str(value)


def main(path):
  with open(path) as f:
    for number, line in enumerate(f, start=1):
      line = line.strip()
      if not line or line.startswith("#"):
        continue
      try:
        print(f"{number}: {show(evaluate(parse(line)))}")
      except (LexError, ParseError, EvalError) as e:
        print(f"{number}: error: {e}")


if __name__ == "__main__":
  main(sys.argv[1])
