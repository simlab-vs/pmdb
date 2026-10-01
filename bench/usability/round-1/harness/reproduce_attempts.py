"""Re-runs queries that agents tried, and the forms that would have worked, in the agents' sandbox.

Each case runs a shell command in the sandbox of a recorded run, with the run's trace, and prints
the command and its output. Usage: python3 reproduce_attempts.py > ../_work/reproduced.md
"""

import subprocess
from pathlib import Path

import sandbox

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "_work" / "runs"
OPT = ROOT / "_work" / "opt-pmdb"

# (run whose trace is used, shell command, note)
CASES = [
  # Return values.
  ("01-pilot-scheduler-B-haiku", "pmdb report.pmdb -e 'select merge(_).$result'", "result of a call (pilot)"),
  ("01-pilot-scheduler-B-haiku", "pmdb report.pmdb -e 'select merge.$result'", "label written as documented"),
  ("01-pilot-scheduler-B-haiku", "pmdb report.pmdb -e 'select /merge\\.\\$result/'", "working form"),
  ("10-ex02-invoicing-subtle-B-haiku", "pmdb report.pmdb -e 'select spread(*)' -e 'show $0' | grep -c result", "show of calls has no results"),
  ("19-ex05-scheduler-rare-B-haiku", "pmdb report.pmdb -e 'select /utilization/\\.\\$result/'", "regex closed early"),
  ("33-ex08-routes-subtle-B-haiku", "pmdb report.pmdb -e \"select /fastest_route/.*result/\"", "regex closed early"),
  ("18-ex07-routes-rare-B-haiku", "pmdb report.pmdb -e \"select /fastest_route.*\\$result/ where true\"", "double-quoted shell: \\$ becomes $ (an anchor)"),
  ("18-ex07-routes-rare-B-haiku", "pmdb report.pmdb -e 'select /fastest_route.*\\$result/'", "same regex, single-quoted"),
  # Filtering by value.
  ("10-ex02-invoicing-subtle-B-haiku", "pmdb report.pmdb -e 'select spread(5000, [3597610, 33068])'", "literal values as argument patterns"),
  ("23-ex01-invoicing-rare-B-haiku", "pmdb report.pmdb -e \"select coupon_reductions(lines, subtotals, code) where code == 'BIG50'\"", "single-quoted string literal"),
  ("23-ex01-invoicing-rare-B-haiku", "pmdb report.pmdb -e 'select coupon_reductions(lines, subtotals, code) where code == \"BIG50\"'", "double-quoted string literal"),
  ("23-ex01-invoicing-rare-B-haiku", "pmdb report.pmdb -e 'select coupon_reductions(...) where code == \"BIG50\"'", "name not bound by ..."),
  ("33-ex08-routes-subtle-B-haiku", "pmdb report.pmdb -e 'select fastest_route(n, s, t) where s == \"B2\" and t == \"A0\"'", "`and` instead of `&&`"),
  ("33-ex08-routes-subtle-B-haiku", "pmdb report.pmdb -e 'select fastest_route(n, s, t) where s == \"B2\" && t == \"A0\"'", "working form"),
  ("18-ex07-routes-rare-B-haiku", "pmdb report.pmdb -e 'select fastest_route(E0, A0)'", "intended literals, arity 2 of 3"),
  ("18-ex07-routes-rare-B-haiku", "pmdb report.pmdb -e 'select fastest_route(_, E0, A0)'", "names are variables, not strings"),
  ("13-ex06-scheduler-subtle-B-haiku", "pmdb report.pmdb -e 'select subtract(_, _) where _'", "`_` in a where clause"),
  ("19-ex05-scheduler-rare-B-haiku", "pmdb report.pmdb -e 'select utilization(_) where _ != none'", "`_` in a where clause"),
  ("19-ex05-scheduler-rare-B-haiku", "pmdb report.pmdb -e 'select utilization($)'", "`$` as a pattern"),
  ("30-ex04-calc-subtle-B-haiku", "pmdb report.pmdb -e \"select call('parse', _) where _ > 0\"", "`call(name, ...)` form"),
  ("18-ex07-routes-rare-B-haiku", "pmdb report.pmdb -e 'select fastest_route($0)'", "variable as an argument pattern"),
  # Sources (from clauses).
  ("10-ex02-invoicing-subtle-B-haiku", "pmdb report.pmdb -e 'select spread(*) from * where true'", "`from *`"),
  ("23-ex01-invoicing-rare-B-haiku", "pmdb report.pmdb -e 'select /coupon_reductions.*\\$result/ from coupon_reductions(...)'", "subquery without select"),
  ("23-ex01-invoicing-rare-B-haiku", "pmdb report.pmdb -e 'select /coupon_reductions.*\\$result/ from select coupon_reductions(...)'", "subquery with select"),
  ("23-ex01-invoicing-rare-B-haiku", "pmdb report.pmdb -e 'select invoice(o) where o.coupon == \"BIG50\"'", "property of a table argument"),
  ("23-ex01-invoicing-rare-B-haiku", "pmdb report.pmdb -e 'select invoice(o) where o.id == \"0-4\"' -e 'select line_subtotal(l) from $0'", "calls made inside the selected call"),
  ("23-ex01-invoicing-rare-B-haiku", "pmdb report.pmdb -e 'select line_subtotal(l)' -e 'select line_subtotal(l) from $0' | grep '\\$'", "from keeps only the selected observations"),
  # Sessions and invocation.
  ("31-ex10-routes-crash-B-haiku", "pmdb report.pmdb -e 'show $0'", "variable from an earlier invocation"),
  ("10-ex02-invoicing-subtle-B-haiku", "echo 'select spread(*) | show $0' | pmdb report.pmdb", "commands piped with |"),
  ("01-pilot-scheduler-B-haiku", "printf 'select merge(_)\\nshow $0\\n' | pmdb report.pmdb | head -4", "REPL fed from stdin"),
  ("10-ex02-invoicing-subtle-B-haiku", "pmdb report.pmdb --show | head -3", "--show after the trace"),
  ("10-ex02-invoicing-subtle-B-haiku", "pmdb --show report.pmdb | wc -l", "size of --show"),
  ("13-ex06-scheduler-subtle-B-haiku", "pmdb report.pmdb -e 'select subtract(...)' -e 'show $0' | wc -l", "size of show for 30 calls"),
  ("18-ex07-routes-rare-B-haiku", "pmdb report.pmdb -e 'select fastest_route(*)' | head -2", "objects shown as <object>"),
]


def main():
  print("# Reproduced pmdb attempts\n")
  for run, command, note in CASES:
    root = RUNS / run
    script = f"{{ {command} ; }} 2>&1; echo \"[exit ${{PIPESTATUS[0]}}]\""
    r = subprocess.run(sandbox.command(root, ["bash", "-c", script],
                                       opt=OPT), capture_output=True, text=True, timeout=60)
    output = r.stdout.strip()
    lines = output.splitlines()
    if len(lines) > 8:
      output = "\n".join(lines[:6] + [f"... ({len(lines) - 7} more lines)", lines[-1]])
    print(f"## {note}\n\n```\n$ {command}\n{output}\n```\n")


if __name__ == "__main__":
  main()
