"""Makes the code shared by the experiments in `bench/`, `bench/lib/pmdbbench`, importable."""

import sys
from pathlib import Path

LIB = str(Path(__file__).resolve().parents[3] / "lib")
if LIB not in sys.path:
  sys.path.append(LIB)
