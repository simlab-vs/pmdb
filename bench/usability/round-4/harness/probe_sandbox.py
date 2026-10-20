"""Checks what is visible and working inside the sandbox of a bug.

Usage: python3 probe_sandbox.py [bug id]   (default: the first bug of data/bugs.jsonl)
"""

import json
import subprocess
import sys
from pathlib import Path

import _lib  # noqa: F401  (makes `pmdbbench` importable)
import bugs

ROOT = Path(__file__).resolve().parent.parent

PROBE = r"""
echo "user: $(id)"; echo "host: $(hostname 2>/dev/null || cat /proc/sys/kernel/hostname)"
echo "pwd: $PWD"; echo "root: $(ls / | tr '\n' ' ')"; echo "home: $(ls -A ~ | tr '\n' ' ')"
echo "/home: $(ls /home)"; echo "/opt: $(ls /opt 2>&1 | tr '\n' ' ')"
echo "/work: $(ls -A /work | tr '\n' ' ')"
test -e /home/ambrus && echo "LEAK: host home visible" || echo "host home hidden"
echo "env: $(env | cut -d= -f1 | sort | tr '\n' ' ')"
echo "PATH=$PATH"; echo "PYTHONPATH=${PYTHONPATH:-}"
echo "python: $(command -v python) $(python --version 2>&1); python3: $(command -v python3)"
python -c 'import sys; print("sys.path:", sys.path)'
python -c 'import PACKAGE; print("project imported from", PACKAGE.__file__)'
python -m pytest --version
grep -rlF ROUND /opt/env 2>/dev/null | head -3 | sed 's/^/LEAK: host path in /'; echo "host paths in /opt/env checked"
touch /opt/env/x 2>/dev/null && echo "LEAK: env writable" || echo "env read-only"
python -c 'import socket; print("dns:", socket.gethostbyname("api.anthropic.com"))' 2>&1 | tail -1
python -c 'import ssl, urllib.request; print("https:", urllib.request.urlopen("https://api.anthropic.com", timeout=10).status)' 2>&1 | tail -1
claude --version
command -v pmdb && pmdb --help | head -1
python -c 'import recorder; print("recorder:", recorder.__file__)' 2>&1 | tail -1
echo x > /work/written && echo "work writable" && rm /work/written
touch /nix/x 2>/dev/null && echo "LEAK: nix writable" || echo "nix read-only"
"""


def main():
  wanted = sys.argv[1] if len(sys.argv) > 1 else None
  all_bugs = bugs.load(ROOT / "data" / "bugs.jsonl")
  bug = next(b for b in all_bugs if wanted in (None, b["id"]))
  package = bug["source_files"][0].removeprefix(bugs.import_root(bug) + "/").split("/")[0]
  package = package.removesuffix(".py")
  probe = PROBE.replace("PACKAGE", package).replace("ROUND", str(bugs.ROOT))
  print(f"bug {bug['id']}, package {package}")
  opt = ROOT / "_work" / "opt-pmdb"
  with bugs.temporary_root() as t:
    root = bugs.materialize(bug, Path(t) / "root")
    for o, network in ((None, True), (opt, True), (opt, False)):
      print(f"--- opt={o} network={network}")
      r = subprocess.run(bugs.command(root, ["bash", "-c", probe], bug,
                                      opt=o if o and o.exists() else None, network=network),
                         capture_output=True, text=True, timeout=120)
      print(r.stdout, r.stderr[-1500:])


if __name__ == "__main__":
  main()
