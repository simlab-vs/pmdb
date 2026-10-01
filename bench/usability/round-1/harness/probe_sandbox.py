"""Checks what is visible and working inside the sandbox. Usage: python3 probe_sandbox.py"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import sandbox

PROBE = r"""
echo "user: $(id)"; echo "host: $(hostname 2>/dev/null || cat /proc/sys/kernel/hostname)"
echo "pwd: $PWD"; echo "root: $(ls / | tr '\n' ' ')"; echo "home: $(ls -A ~ | tr '\n' ' ')"
echo "/home: $(ls /home)"; echo "/opt: $(ls /opt 2>&1)"
test -e /home/ambrus && echo "LEAK: host home visible" || echo "host home hidden"
echo "env: $(env | cut -d= -f1 | sort | tr '\n' ' ')"
python3 -c 'import socket; print("dns:", socket.gethostbyname("api.anthropic.com"))'
python3 -c 'import ssl, urllib.request; print("https:", urllib.request.urlopen("https://api.anthropic.com", timeout=10).status)' 2>&1 | tail -1
claude --version
command -v pmdb && pmdb --help | head -1
echo x > /work/written && echo "work writable"; touch /nix/x 2>/dev/null && echo "LEAK: nix writable" || echo "nix read-only"
"""


def main():
  with tempfile.TemporaryDirectory() as t:
    root = Path(t)
    (root / "home").mkdir()
    (root / "work").mkdir()
    sandbox.prepare_etc(root)
    opt = Path(__file__).resolve().parent.parent / "_work" / "opt-pmdb"
    for o in (None, opt):
      print(f"--- opt={o}")
      r = subprocess.run(sandbox.command(root, ["bash", "-c", PROBE], opt=o if o and o.exists() else None),
                         capture_output=True, text=True, timeout=60)
      print(r.stdout, r.stderr[-1500:])


if __name__ == "__main__":
  main()
