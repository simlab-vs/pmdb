"""Carrying out the moves found by the neighbourhood scans."""

import logging

log = logging.getLogger(__name__)


def apply_move(plan, mv):
    """Changes `plan` as `mv` describes and returns the new totals of the routes it changed."""
    changed = OPERATIONS[mv.kind](plan, mv)
    log.debug("%s %s %s->%s gain %.3f", mv.kind, mv.stop, mv.v1, mv.v2, mv.gain)
    return changed


def _relocate(plan, mv):
    src = plan.routes[mv.r1].stops
    dst = plan.routes[mv.r2].stops
    stop = src.pop(mv.i)
    dst.insert(mv.j, stop)
    changed = []
    if src:
        changed.append(plan.refresh(mv.r1))
    else:
        plan.release(mv.r1)
    changed.append(plan.refresh(mv.r2))
    return changed


def _swap(plan, mv):
    s1 = plan.routes[mv.r1].stops
    s2 = plan.routes[mv.r2].stops
    s1[mv.i], s2[mv.j] = s2[mv.j], s1[mv.i]
    return [plan.refresh(mv.r1), plan.refresh(mv.r2)]


def _segment(plan, mv):
    s1 = plan.routes[mv.r1].stops
    s2 = plan.routes[mv.r2].stops
    seg = s1[mv.i:mv.i + mv.length]
    del s1[mv.i:mv.i + mv.length]
    if mv.reverse:
        seg.reverse()
    s2[mv.j:mv.j] = seg
    return [plan.refresh(mv.r1), plan.refresh(mv.r2)]


def _tails(plan, mv):
    s1 = plan.routes[mv.r1].stops
    s2 = plan.routes[mv.r2].stops
    s1[mv.i:], s2[mv.j:] = s2[mv.j:], s1[mv.i:]
    return [plan.refresh(mv.r1), plan.refresh(mv.r2)]


def _two_opt(plan, mv):
    s = plan.routes[mv.r1].stops
    s[mv.i:mv.j + 1] = s[mv.i:mv.j + 1][::-1]
    return [plan.refresh(mv.r1)]


OPERATIONS = {
    "relocate": _relocate,
    "swap": _swap,
    "segment": _segment,
    "tails": _tails,
    "two_opt": _two_opt,
}
