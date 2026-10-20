"""Deterministic simulated wall clock for the points-expiry scenario.

Put this directory on PYTHONPATH and set:
  SIM_START  ISO instant with offset at which the run starts (e.g. 2026-09-30T23:50:02+02:00)
  SIM_STEP   seconds the clock advances on each clock read made by the job's own code (default 0.05)
  SIM_ROOT   directory of the job's code; reads from other code (logging, the recorder) see the
             current time without advancing it, so recording doesn't change the run.
time.sleep advances the clock by its argument instead of sleeping.

The clock replaces time.time/time_ns/monotonic/localtime/gmtime/ctime/strftime defaults and
datetime.datetime.now/today/utcnow and datetime.date.today, so a fix that reads the clock through
any of them sees the simulated time. The original sitecustomize (if any) is run first.
"""

import importlib.machinery
import importlib.util
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.machinery.PathFinder.find_spec(
    "sitecustomize", [p for p in sys.path if os.path.abspath(p or ".") != _here])
if _spec is not None and _spec.origin and os.path.dirname(os.path.abspath(_spec.origin)) != _here:
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)

if os.environ.get("SIM_START"):
    import datetime as _dt
    import time as _time

    _real = {name: getattr(_time, name) for name in ("localtime", "gmtime", "ctime", "strftime")}
    _state = {"t": _dt.datetime.fromisoformat(os.environ["SIM_START"]).timestamp()}
    _step = float(os.environ.get("SIM_STEP", "0.05"))
    _root = os.path.realpath(os.environ.get("SIM_ROOT", os.getcwd())) + os.sep

    def _tick(depth):
        try:
            frame = sys._getframe(depth + 1)
        except ValueError:
            return _state["t"]
        while frame is not None and os.path.realpath(frame.f_code.co_filename).startswith(_here + os.sep):
            frame = frame.f_back
        if frame is not None and os.path.realpath(frame.f_code.co_filename).startswith(_root):
            _state["t"] += _step
        return _state["t"]

    def time():
        return _tick(1)

    def time_ns():
        return int(_tick(1) * 1_000_000_000)

    def sleep(seconds):
        _state["t"] += max(0.0, float(seconds))

    def localtime(secs=None):
        return _real["localtime"](_tick(1) if secs is None else secs)

    def gmtime(secs=None):
        return _real["gmtime"](_tick(1) if secs is None else secs)

    def ctime(secs=None):
        return _real["ctime"](_tick(1) if secs is None else secs)

    def strftime(fmt, t=None):
        return _real["strftime"](fmt, _real["localtime"](_tick(1)) if t is None else t)

    class _Builtin:
        """Not a descriptor, like the C functions it replaces (logging keeps
        ``time.localtime`` as a class attribute)."""

        def __init__(self, function):
            self.function = function

        def __call__(self, *args):
            return self.function(*args)

    time, time_ns, sleep, localtime, gmtime, ctime, strftime = map(
        _Builtin, (time, time_ns, sleep, localtime, gmtime, ctime, strftime))
    _time.time = time
    _time.time_ns = time_ns
    _time.monotonic = time
    _time.monotonic_ns = time_ns
    _time.sleep = sleep
    _time.localtime = localtime
    _time.gmtime = gmtime
    _time.ctime = ctime
    _time.strftime = strftime

    _RealDateTime, _RealDate = _dt.datetime, _dt.date

    class datetime(_RealDateTime):
        @classmethod
        def now(cls, tz=None):
            return cls.fromtimestamp(_tick(1), tz)

        @classmethod
        def today(cls):
            return cls.fromtimestamp(_tick(1))

        @classmethod
        def utcnow(cls):
            return cls.fromtimestamp(_tick(1), _dt.timezone.utc).replace(tzinfo=None)

    class date(_RealDate):
        @classmethod
        def today(cls):
            return _RealDate.fromtimestamp(_tick(1))

    datetime.__module__ = date.__module__ = "datetime"
    _dt.datetime = datetime
    _dt.date = date

if os.environ.get("SIM_CRM", "1") == "1":
    import urllib.request as _request

    class _Accepted:
        """The CRM's answer to an import request: 202 Accepted."""

        status = 202

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b'{"status": "accepted"}'

    _real_urlopen = _request.urlopen

    def _urlopen(url, data=None, timeout=None, **kwargs):
        target = url.full_url if hasattr(url, "full_url") else str(url)
        if "crm.northwind.internal" in target:
            return _Accepted()
        return _real_urlopen(url, data, timeout, **kwargs)

    _request.urlopen = _urlopen
