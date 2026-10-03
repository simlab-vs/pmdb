"""pmdb's Python recorder, and queries on the traces it writes.

    import recorder
    t = recorder.load("trace.pmdb")        # see `help(recorder.trace)` for queries
    t.calls("post", raised=True, caller="close_month")

`recorder.recording(path)` and the script `pmdb-record` record traces (see `recorder.monitor`),
and `recorder.snap(label, value)` records a value in the call being run.
"""

from .archive import Archive, register
from .recorder import Recorder
from .monitor import Monitor, recording, snap
from .trace import Calls, Q, QueryError, load

main = Recorder()
