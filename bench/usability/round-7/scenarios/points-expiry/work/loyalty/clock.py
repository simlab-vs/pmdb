"""Wall clock of the programme.

Everything the programme does is dated in its home time zone (Europe/Berlin):
business dates, statement months and the expiry calendar of the terms and
conditions. Dates travel through the code as ISO strings (``YYYY-MM-DD``),
which is also how the points database stores them.
"""

import time
from datetime import datetime
from zoneinfo import ZoneInfo

ZONE_NAME = "Europe/Berlin"
ZONE = ZoneInfo(ZONE_NAME)


def now():
    """The current time in the programme's time zone."""
    return datetime.fromtimestamp(time.time(), ZONE)


def today():
    """The current calendar date in the programme's time zone, as ``YYYY-MM-DD``."""
    return now().date().isoformat()


def stamp():
    """The current time as an ISO 8601 string with offset, to the second."""
    return now().isoformat(timespec="seconds")


def utc_stamp():
    """The current time in UTC (for headers of outgoing requests)."""
    return datetime.fromtimestamp(time.time(), ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")
