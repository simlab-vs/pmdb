"""The price catalog: plans, their metered dimensions and price tiers."""

import json
from operator import attrgetter
from pathlib import Path
from typing import NamedTuple

from .util import ranked

PRICING_MODELS = ("graduated", "volume", "per_unit")
AGGREGATIONS = ("sum", "average", "max")


class Tier(NamedTuple):
    start: int
    upto: int | None
    unit_price: float


class CatalogError(ValueError):
    pass


def _parse_tier(raw, where):
    try:
        start = int(raw["from"])
        upto = None if raw.get("to") is None else int(raw["to"])
        price = float(raw["unit_price"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CatalogError(f"{where}: malformed tier {raw!r}") from exc
    if upto is not None and upto <= start:
        raise CatalogError(f"{where}: tier {start}..{upto} is empty")
    if price < 0:
        raise CatalogError(f"{where}: negative unit price")
    return Tier(start, upto, price)


def _check_tiers(tiers, where):
    """Tiers must start at zero, be contiguous, and only the last may be open-ended."""
    if not tiers:
        raise CatalogError(f"{where}: no tiers")
    if tiers[0].start != 0:
        raise CatalogError(f"{where}: first tier starts at {tiers[0].start}")
    for previous, tier in zip(tiers, tiers[1:]):
        if previous.upto is None:
            raise CatalogError(f"{where}: open-ended tier is not the last one")
        if tier.start != previous.upto:
            raise CatalogError(f"{where}: gap or overlap at {previous.upto}")


def _parse_metric(name, raw, where):
    model = raw.get("model", "graduated")
    if model not in PRICING_MODELS:
        raise CatalogError(f"{where}: unknown pricing model {model!r}")
    aggregate = raw.get("aggregate", "sum")
    if aggregate not in AGGREGATIONS:
        raise CatalogError(f"{where}: unknown aggregation {aggregate!r}")
    if model == "per_unit":
        tiers = [Tier(0, None, float(raw["unit_price"]))]
    else:
        tiers = ranked([_parse_tier(t, where) for t in raw["tiers"]], key=attrgetter("start"))
        _check_tiers(tiers, where)
    return {
        "metric": name,
        "label": raw.get("label", name.replace("_", " ")),
        "unit": raw.get("unit", "unit"),
        "model": model,
        "aggregate": aggregate,
        "included": int(raw.get("included", 0)),
        "tiers": tiers,
    }


def load_catalog(path):
    """Read ``plans.json`` into ``{plan id: plan}``.

    A plan is a dict with its ``id``, ``name``, monthly ``base_fee`` and
    ``metrics``, mapping each metered dimension to its pricing spec.
    """
    raw = json.loads(Path(path).read_text())
    plans = {}
    for plan_id, plan in raw["plans"].items():
        metrics = {
            name: _parse_metric(name, spec, f"plan {plan_id}, metric {name}")
            for name, spec in plan.get("metrics", {}).items()
        }
        plans[plan_id] = {
            "id": plan_id,
            "name": plan["name"],
            "base_fee": float(plan["base_fee"]),
            "metrics": metrics,
            "retired": bool(plan.get("retired", False)),
        }
    return plans


def metric_spec(plan, metric):
    """The pricing spec of ``metric`` in ``plan``, or ``None`` if it isn't billed."""
    return plan["metrics"].get(metric)


def billed_metrics(plans):
    """Every metric billed by at least one plan, with the aggregation it uses."""
    aggregations = {}
    for plan in plans.values():
        for name, spec in plan["metrics"].items():
            known = aggregations.setdefault(name, spec["aggregate"])
            if known != spec["aggregate"]:
                raise CatalogError(f"metric {name} is aggregated differently across plans")
    return aggregations
