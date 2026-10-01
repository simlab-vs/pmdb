"""Generates random inputs for the calculator program (hidden from agents)."""

import random

TEMPLATES = [
  "let fact = fn(n) if n <= 1 then 1 else n * fact(n - 1) in fact({a})",
  "let fib = fn(n) if n < 2 then n else fib(n - 1) + fib(n - 2) in fib({s})",
  "let pow = fn(b, e) if e == 0 then 1 else b * pow(b, e - 1) in pow({b}, {s})",
  "let sum = fn(n) if n == 0 then 0 else n + sum(n - 1) in sum({a}) % {m}",
  "let collatz = fn(n, k) if n == 1 then k else if n % 2 == 0 then collatz(n / 2, k + 1) else collatz(3 * n + 1, k + 1) in collatz({p}, 0)",
  "let g = fn(a, b) if b == 0 then a else g(b, a % b) in g({x}, {y})",
  "let clamp = fn(x, lo, hi) max(lo, min(x, hi)) in clamp({x}, {y}, {z})",
  "let sign = fn(x) if x < 0 then -1 else if x > 0 then 1 else 0 in sign({x}) * {a}",
  "let twice = fn(f, x) f(f(x)) in twice(fn(v) v * {b} - {a}, {x})",
  "let x = {x} in let y = {y} in x / y + x % y",
  "{x} - {y} - {z}",
  "{x} / {y} * {z} - {a} % {b}",
  "-{a} * ({x} + {y}) / {b}",
  "if {x} > {y} && {y} >= {z} || !({a} == {b}) then {x} else {y}",
  "let digits = fn(n) if n < 10 then 1 else 1 + digits(n / 10) in digits({big})",
  "let tri = fn(n, acc) if n <= 0 then acc else tri(n - 1, acc + n) in tri({a}, {z})",
  "gcd({x}, {y}) + abs({z}) * {s}",
  "let f = fn(x) x * x - {a} in min(f({x}), f({y}), f({z}))",
  "let between = fn(v, lo, hi) lo <= v && v <= hi in between({x}, {y}, {z}) + between({a}, {b}, {m})",
  "let mod = fn(a, b) ((a % b) + b) % b in mod({x}, {b}) - mod({y}, {m})",
]


def generate(seed):
  rng = random.Random(seed)

  def value():
    return {
      "a": rng.randint(0, 12), "b": rng.randint(1, 9), "s": rng.randint(0, 15),
      "m": rng.randint(2, 50), "p": rng.randint(1, 60),
      "x": rng.randint(-60, 60), "y": rng.choice([rng.randint(-30, -1), rng.randint(1, 30)]),
      "z": rng.randint(-40, 40), "big": rng.randint(0, 10 ** rng.randint(1, 12)),
    }

  lines = []
  for _ in range(rng.randint(6, 12)):
    lines.append(rng.choice(TEMPLATES).format(**value()))
  return "\n".join(lines) + "\n"
