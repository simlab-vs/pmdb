"""Statistical tests for paired comparisons."""

import collections
import math
import random
import statistics


def wilcoxon(differences):
  """Returns `(W+, n, two-sided exact p)` of the Wilcoxon signed-rank test, dropping zeros."""
  d = [x for x in differences if x != 0]
  n = len(d)
  if n == 0:
    return 0, 0, 1.0
  order = sorted(range(n), key=lambda i: abs(d[i]))
  ranks = [0.0] * n
  i = 0
  while i < n:
    j = i
    while j + 1 < n and abs(d[order[j + 1]]) == abs(d[order[i]]):
      j += 1
    for k in range(i, j + 1):
      ranks[order[k]] = (i + j) / 2 + 1
    i = j + 1
  doubled = [int(round(2 * r)) for r in ranks]
  w_plus = sum(r for r, x in zip(doubled, d) if x > 0)
  # Exact null distribution of the doubled W+ by dynamic programming.
  counts = collections.Counter({0: 1})
  for r in doubled:
    nxt = collections.Counter()
    for s, c in counts.items():
      nxt[s] += c
      nxt[s + r] += c
    counts = nxt
  total = 2 ** n
  mean = sum(doubled) / 2
  extreme = abs(w_plus - mean)
  p = sum(c for s, c in counts.items() if abs(s - mean) >= extreme - 1e-9) / total
  return w_plus / 2, n, min(1.0, p)


def mcnemar(pairs):
  """Exact McNemar test on `(a, b)` boolean pairs: returns `(b only, a only, p)`."""
  b_only = sum(1 for a, b in pairs if b and not a)
  a_only = sum(1 for a, b in pairs if a and not b)
  n = a_only + b_only
  k = min(a_only, b_only)
  p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n) if n else 1.0
  return b_only, a_only, p


def bootstrap_median(values, rounds=10000, seed=0):
  rng = random.Random(seed)
  medians = sorted(statistics.median(rng.choices(values, k=len(values))) for _ in range(rounds))
  return medians[int(0.025 * rounds)], medians[int(0.975 * rounds)]
