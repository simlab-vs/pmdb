"""pytest plugin loaded by mine.py (-p pmine_plugin): writes one JSON line per test report.

Output file: $PMINE_REPORT. For failures it records the exception type and the file of the
innermost traceback entry, so mine.py can tell assertion failures in tests from exceptions
raised by the code under test.
"""
import json
import os

import pytest

_OUT = os.environ.get("PMINE_REPORT")


def _write(rec):
    if _OUT:
        with open(_OUT, "a") as f:
            f.write(json.dumps(rec) + "\n")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if call.excinfo is not None and rep.failed:
        ei = call.excinfo
        try:
            last = str(ei.traceback[-1].path) if len(ei.traceback) else ""
        except Exception:
            last = ""
        rep.user_properties.append(("pmine_exc_type", ei.typename))
        rep.user_properties.append(("pmine_exc_path", last))
        try:
            paths = [str(e.path) for e in ei.traceback]
        except Exception:
            paths = []
        rep.user_properties.append(("pmine_exc_paths", paths))
        rep.user_properties.append(("pmine_exc_msg", str(ei.value)[:500]))


def pytest_runtest_logreport(report):
    props = dict(p for p in report.user_properties if isinstance(p, tuple) and len(p) == 2
                 and str(p[0]).startswith("pmine_"))
    if report.when == "call" or report.outcome != "passed":
        _write({"nodeid": report.nodeid, "when": report.when, "outcome": report.outcome,
                "duration": report.duration,
                "exc_type": props.get("pmine_exc_type"),
                "exc_path": props.get("pmine_exc_path"),
                "exc_paths": props.get("pmine_exc_paths"),
                "exc_msg": props.get("pmine_exc_msg")})


def pytest_collectreport(report):
    if report.failed:
        _write({"nodeid": report.nodeid, "when": "collect", "outcome": "error",
                "exc_msg": str(report.longrepr)[-500:]})
