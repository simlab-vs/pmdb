"""Plain records shared by the planner's modules."""

from typing import NamedTuple


class Stop(NamedTuple):
    """A delivery address (or the depot) with its order and time window, in minutes after 07:00."""

    id: str
    x: float
    y: float
    demand: int
    ready: int
    due: int
    service: int


class Vehicle(NamedTuple):
    """A vehicle of the fleet, available from 07:00 until `shift_end`."""

    id: str
    kind: str
    capacity: int
    cost_per_km: float
    fixed_cost: float
    shift_end: int


class RouteStats(NamedTuple):
    """Totals of one route, as used for costing and reporting."""

    vehicle: str
    stops: int
    load_kg: int
    capacity: int
    distance: float
    duration: float
    cost: float


class Move(NamedTuple):
    """A change to one or two routes found by a neighbourhood scan.

    `r1` and `r2` are route indices in the plan, `i` and `j` positions in those routes, and
    `length` the number of consecutive stops moved, where that applies. `v1`, `v2` and `stop`
    name the vehicles and the first stop involved, for the log.
    """

    kind: str
    r1: int
    r2: int
    i: int
    j: int
    length: int
    reverse: bool
    gain: float
    v1: str
    v2: str
    stop: str
