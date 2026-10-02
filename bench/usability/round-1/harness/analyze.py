"""Analyzes the study results as fixed in PROTOCOL.md.

Usage: python3 analyze.py > ../results/summary.md
"""

import collections
import json
import re
import statistics
from pathlib import Path

import _lib  # noqa: F401  (makes `pmdbbench` importable)
from pmdbbench import transcripts
from pmdbbench.stats import bootstrap_median, mcnemar, wilcoxon

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "_work"


def tokens(r):
  u = r.get("usage") or {}
  return sum(u.get(k) or 0 for k in ("input_tokens", "output_tokens", "cache_read_input_tokens",
                                    "cache_creation_input_tokens"))


def pmdb_errors(run_id):
  """Returns the error messages printed by pmdb commands in a run's transcript."""
  return transcripts.pmdb_errors(WORK / "runs" / run_id / "transcript.jsonl")


def main():
  records = [json.loads(l) for l in (WORK / "results.jsonl").read_text().splitlines() if l.strip()]
  main_runs = [r for r in records if not r["pilot"]]
  by_key = {(r["exercise"], r["model_alias"], r["arm"]): r for r in main_runs}
  pairs = [(by_key[(e, m, "A")], by_key[(e, m, "B")]) for (e, m, a) in by_key
           if a == "A" and (e, m, "B") in by_key]
  pairs.sort(key=lambda p: (p[0]["exercise"], p[0]["model_alias"]))

  print("# Usability study of pmdb: results\n")
  print(f"{len(main_runs)} runs, {len(pairs)} complete exercise × model pairs.\n")
  models = sorted({r["model"] for r in main_runs if r["model"]})
  print(f"Resolved models: {', '.join(models)}.\n")

  print("## Runs\n")
  print("| exercise | model | arm | success | localized | turns | tokens (k) | wall (s) | pmdb / record calls (failed) |")
  print("|---|---|---|---|---|---|---|---|---|")
  for a, b in pairs:
    for r in (a, b):
      print(f"| {r['exercise']} | {r['model_alias']} | {r['arm']} | {'✓' if r['success'] else '✗'} | "
            f"{'✓' if r['localized'] else '✗'} | {r['num_turns']} | {tokens(r) / 1000:.0f} | "
            f"{r['wall_seconds']:.0f} | {r['pmdb_calls']} / {r['pmdb_record_calls']} ({r['pmdb_failed']}) |")

  print("\n## Pre-registered comparisons (B − A, paired)\n")
  for label, f in (("total tokens", tokens), ("turns", lambda r: r["num_turns"] or 0),
                   ("wall time (s)", lambda r: r["wall_seconds"])):
    d = [f(b) - f(a) for a, b in pairs]
    w, n, p = wilcoxon(d)
    lo, hi = bootstrap_median(d) if d else (0, 0)
    print(f"- **{label}**: median difference {statistics.median(d):+.0f} "
          f"(95% CI {lo:+.0f} to {hi:+.0f}), Wilcoxon W+ = {w}, n = {n}, p = {p:.3f}")
  b_only, a_only, p = mcnemar([(a["success"], b["success"]) for a, b in pairs])
  print(f"- **success**: A {sum(a['success'] for a, _ in pairs)}/{len(pairs)}, "
        f"B {sum(b['success'] for _, b in pairs)}/{len(pairs)}; only B: {b_only}, only A: {a_only}, "
        f"exact McNemar p = {p:.3f}")
  print(f"- **localized**: A {sum(a['localized'] for a, _ in pairs)}/{len(pairs)}, "
        f"B {sum(b['localized'] for _, b in pairs)}/{len(pairs)}")

  print("\n## Descriptive breakdowns\n")
  print("| group | pairs | success A | success B | median tokens A (k) | median tokens B (k) | median turns A | median turns B |")
  print("|---|---|---|---|---|---|---|---|")
  groups = collections.defaultdict(list)
  for a, b in pairs:
    groups[f"category {a['category']}"].append((a, b))
    groups[f"model {a['model_alias']}"].append((a, b))
  for g in sorted(groups):
    ps = groups[g]
    print(f"| {g} | {len(ps)} | {sum(a['success'] for a, _ in ps)} | {sum(b['success'] for _, b in ps)} | "
          f"{statistics.median(tokens(a) for a, _ in ps) / 1000:.0f} | "
          f"{statistics.median(tokens(b) for _, b in ps) / 1000:.0f} | "
          f"{statistics.median(a['num_turns'] or 0 for a, _ in ps):.0f} | "
          f"{statistics.median(b['num_turns'] or 0 for _, b in ps):.0f} |")

  print("\n## pmdb usage in arm B\n")
  b_runs = [r for r in main_runs if r["arm"] == "B"]
  used = [r for r in b_runs if r["pmdb_calls"] or r["pmdb_record_calls"]]
  print(f"pmdb or pmdb-record used in {len(used)}/{len(b_runs)} runs; "
        f"{sum(r['pmdb_calls'] for r in b_runs)} pmdb calls, "
        f"{sum(r['pmdb_record_calls'] for r in b_runs)} pmdb-record calls, "
        f"{sum(r['pmdb_failed'] for r in b_runs)} failed.\n")
  print("### Error messages printed by pmdb\n")
  messages = collections.Counter()
  examples = {}
  for r in b_runs:
    for command, m in pmdb_errors(r["id"]):
      key = re.sub(r"'[^']*'", "'…'", m)[:120]
      messages[key] += 1
      examples.setdefault(key, command[:200])
  for m, c in messages.most_common():
    print(f"- {c}× `{m}` (e.g. `{examples[m]}`)")

  print("\n## Feedback\n")
  for field in ("pmdb_usefulness", "confidence"):
    for arm in ("A", "B"):
      values = [r["feedback"].get(field) for r in main_runs
                if r["arm"] == arm and isinstance(r.get("feedback"), dict)
                and isinstance(r["feedback"].get(field), (int, float))]
      if values:
        print(f"- {field} (arm {arm}): median {statistics.median(values)}, values {sorted(values)}")
  for field in ("pmdb_problems", "pmdb_wishes", "other_wishes", "wasted_effort", "key_step"):
    print(f"\n### {field}\n")
    for r in sorted(main_runs, key=lambda r: (r["arm"], r["exercise"], r["model_alias"])):
      fb = r.get("feedback") or {}
      value = fb.get(field)
      items = value if isinstance(value, list) else ([value] if value else [])
      for item in items:
        print(f"- [{r['arm']} {r['model_alias']} {r['exercise']}] {item}")


if __name__ == "__main__":
  main()
