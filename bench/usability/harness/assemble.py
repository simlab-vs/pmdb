"""Assembles the read-only /opt/pmdb tree given to agents in the pmdb arm.

It contains the pmdb binary, the Python recorder, `pmdb-record`, and a README made of a header
and the query language section of the repository's README, verbatim.

Usage: python3 assemble.py <pmdb binary> <output directory>
"""

import shutil
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPOSITORY = ROOT.parent.parent


def main(binary, output):
  output = Path(output)
  if output.exists():
    for p in [output, *output.rglob("*")]:
      p.chmod(p.stat().st_mode | stat.S_IWUSR)
    shutil.rmtree(output)
  (output / "bin").mkdir(parents=True)
  shutil.copy2(binary, output / "bin" / "pmdb")

  # Remove symbols and host paths, keeping only library paths into the Nix store.
  pmdb = str(output / "bin" / "pmdb")
  subprocess.run(["strip", pmdb], check=True)
  rpath = subprocess.run(["patchelf", "--print-rpath", pmdb], check=True, capture_output=True,
                         text=True).stdout.strip()
  kept = ":".join(p for p in rpath.split(":") if p.startswith("/nix/store/"))
  subprocess.run(["patchelf", "--set-rpath", kept, pmdb], check=True)
  shutil.copy2(ROOT / "opt-pmdb" / "bin" / "pmdb-record", output / "bin" / "pmdb-record")
  shutil.copytree(REPOSITORY / "Python" / "recorder", output / "python" / "recorder",
                  ignore=shutil.ignore_patterns("__pycache__"))

  readme = (REPOSITORY / "README.md").read_text()
  query_language = readme[readme.index("## Query Language"):]
  header = (ROOT / "opt-pmdb" / "HEADER.md").read_text()
  (output / "README.md").write_text(header + query_language)

  for p in output.rglob("*"):
    p.chmod(p.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


if __name__ == "__main__":
  main(*sys.argv[1:])
