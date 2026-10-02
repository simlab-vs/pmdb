"""Code shared by the experiments in `bench/`.

Experiments import this package after adding `bench/lib` to `sys.path` (see their
`harness/_lib.py`). Only code that doesn't depend on an experiment's design belongs here; an
experiment's prompts, parameters and analyses stay in its own harness.
"""
