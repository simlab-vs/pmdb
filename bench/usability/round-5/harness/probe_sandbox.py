"""Checks what is visible and working inside the sandbox of a bug, and that the only network is the
relay to the API.

Usage: python3 probe_sandbox.py [bug id]   (default: the first bug of data/bugs.jsonl)

The probe runs in the agent's view of the bug three times: as the harness's test runs (no relay),
as arm A's runs and as arm B's runs (with the relay). Lines starting with LEAK are problems.
"""

import subprocess
import sys
from pathlib import Path

import _lib  # noqa: F401  (makes `pmdbbench` importable)
import bugs
import offline

ROOT = Path(__file__).resolve().parent.parent

PROBE = r"""
echo "user: $(id)"; echo "host: $(hostname 2>/dev/null || cat /proc/sys/kernel/hostname)"
echo "pwd: $PWD"; echo "root: $(ls / | tr '\n' ' ')"; echo "home: $(ls -A ~ | tr '\n' ' ')"
echo "/opt: $(ls /opt 2>&1 | tr '\n' ' ')"; echo "/run: $(ls /run 2>&1 | tr '\n' ' ')"
echo "/work: $(ls -A /work | tr '\n' ' ')"
test -e /home/ambrus && echo "LEAK: host home visible" || echo "host home hidden"
echo "env: $(env | cut -d= -f1 | sort | tr '\n' ' ')"
echo "PATH=$PATH"; echo "PYTHONPATH=${PYTHONPATH:-}"; echo "ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL:-}"
echo "python: $(command -v python) $(python --version 2>&1)"
python -c 'import PACKAGE; f = PACKAGE.__file__; print("project imported from", f); print("ok: project from /work" if f.startswith("/work/") else "LEAK: project not from /work")'
python -m pytest --version
for f in HIDDEN; do test -e "/work/$f" && echo "fix test file present at parent version: $f" || echo "fix test file absent: $f"; done
grep -rlF ROUND /opt/env 2>/dev/null | head -3 | sed 's/^/LEAK: host path in /'; echo "host paths in /opt/env checked"
touch /opt/env/x 2>/dev/null && echo "LEAK: env writable" || echo "env read-only"
echo "interfaces: $(ls /sys/class/net 2>/dev/null | tr '\n' ' ')"
cat /proc/net/route | tail -n +2 | grep -q . && echo "LEAK: a route exists" || echo "no routes"
python - <<'EOF'
import socket, ssl, urllib.request
def probe(label, f):
  try:
    print(f"{label}: reachable ({f()})")
  except Exception as e:
    print(f"{label}: unreachable ({type(e).__name__}: {str(e)[:80]})")
probe("dns pypi.org", lambda: socket.gethostbyname("pypi.org"))
probe("dns api.anthropic.com", lambda: socket.gethostbyname("api.anthropic.com"))
probe("tcp 1.1.1.1:443", lambda: socket.create_connection(("1.1.1.1", 443), timeout=5).close())
probe("https pypi.org", lambda: urllib.request.urlopen("https://pypi.org", timeout=5).status)
probe("https github.com", lambda: urllib.request.urlopen("https://github.com", timeout=5).status)
probe("https api.anthropic.com:443", lambda: urllib.request.urlopen("https://api.anthropic.com", timeout=5).status)
def relay():
  try:
    return urllib.request.urlopen("https://api.anthropic.com:8443/v1/models", timeout=10).status
  except urllib.error.HTTPError as e:
    return f"HTTP {e.code}, TLS verified"
probe("https api.anthropic.com:8443 (relay)", relay)
EOF
claude --version
command -v pmdb && pmdb --help 2>&1 | head -1
python -c 'import recorder; print("recorder:", recorder.__file__)' 2>&1 | tail -1
ls ~/.claude/skills 2>/dev/null
echo x > /work/written && echo "work writable" && rm /work/written
touch /nix/x 2>/dev/null && echo "LEAK: nix writable" || echo "nix read-only"
"""


def main():
  wanted = sys.argv[1] if len(sys.argv) > 1 else None
  all_bugs = bugs.load(ROOT / "data" / "bugs.jsonl")
  bug = next(b for b in all_bugs if wanted in (None, b["id"]))
  package = bug["source_files"][0].removeprefix(bugs.import_root(bug) + "/").split("/")[0]
  package = package.removesuffix(".py")
  probe = (PROBE.replace("PACKAGE", package).replace("ROUND", str(bugs.ROUND4))
           .replace("HIDDEN", " ".join(bugs.hidden_test_files(bug))))
  print(f"bug {bug['id']}, package {package}")
  with bugs.temporary_root() as t:
    root = bugs.materialize(bug, Path(t) / "root")
    bugs.install_skill(root)
    for label, pmdb, api in (("harness test run", False, False), ("arm A", False, True),
                             ("arm B", True, True)):
      print(f"--- {label}: pmdb={pmdb} relay={api}", flush=True)
      r = offline.run(root, ["bash", "-c", probe], opt=bugs.OPT if pmdb else None,
                      env=bugs.environment(bug, pmdb),
                      binds=[(root / "env", bugs.ENV_IN_SANDBOX)], api=api,
                      capture_output=True, text=True, timeout=180)
      print(r.stdout, r.stderr[-1500:], flush=True)


if __name__ == "__main__":
  main()
