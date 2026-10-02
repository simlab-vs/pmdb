"""Assembles what agents get in the pmdb arm: the read-only /opt/pmdb tree and the pmdb skill.

/opt/pmdb contains the pmdb binary and the Python recorder. The skill is a copy of the
repository's `skills/pmdb`, installed in each run as a user skill of Claude Code.

Usage: python3 assemble.py <pmdb binary> <opt directory> <skill directory>
"""

import shutil
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPOSITORY = ROOT.parent.parent.parent


def fresh(directory):
  if directory.exists():
    for p in [directory, *directory.rglob("*")]:
      p.chmod(p.stat().st_mode | stat.S_IWUSR)
    shutil.rmtree(directory)


def read_only(directory):
  for p in directory.rglob("*"):
    p.chmod(p.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def main(binary, opt, skill):
  opt, skill = Path(opt), Path(skill)
  fresh(opt)
  (opt / "bin").mkdir(parents=True)
  shutil.copy2(binary, opt / "bin" / "pmdb")

  # Remove symbols and host paths, keeping only library paths into the Nix store.
  pmdb = str(opt / "bin" / "pmdb")
  (opt / "bin" / "pmdb").chmod(0o755)
  subprocess.run(["strip", pmdb], check=True)
  rpath = subprocess.run(["patchelf", "--print-rpath", pmdb], check=True, capture_output=True,
                         text=True).stdout.strip()
  kept = ":".join(p for p in rpath.split(":") if p.startswith("/nix/store/"))
  subprocess.run(["patchelf", "--set-rpath", kept, pmdb], check=True)
  shutil.copytree(REPOSITORY / "Python" / "recorder", opt / "python" / "recorder",
                  ignore=shutil.ignore_patterns("__pycache__"))
  read_only(opt)

  fresh(skill)
  shutil.copytree(REPOSITORY / "skills" / "pmdb", skill,
                  ignore=shutil.ignore_patterns("__pycache__"))
  read_only(skill)


if __name__ == "__main__":
  main(*sys.argv[1:])
