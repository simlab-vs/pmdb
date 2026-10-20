"""Consistency checks before anything is sent to the warehouses."""

import logging

from . import catalog, ledger

log = logging.getLogger(__name__)


class CheckFailed(RuntimeError):
    pass


def check_stock():
    """No warehouse may have promised more than it had."""
    negative = ledger.negative_locations()
    if negative:
        raise CheckFailed(f"stock below zero at {len(negative)} locations, e.g. {negative[:3]}")


def check_lines(allocations):
    """Every line is allocated or backordered, unit for unit."""
    for allocation in allocations:
        if catalog.is_kit(allocation.sku):
            allocated = allocation.ordered if allocation.picks else 0
        else:
            allocated = sum(pick.qty for pick in allocation.picks)
        if allocated + allocation.backordered != allocation.ordered:
            raise CheckFailed(
                f"{allocation.order_id}/{allocation.line_no}: {allocated} allocated + "
                f"{allocation.backordered} backordered != {allocation.ordered} ordered"
            )


def check_single_source(allocations, ship_complete_orders):
    """Ship-complete lines and kits leave from one warehouse."""
    for allocation in allocations:
        if allocation.order_id in ship_complete_orders or catalog.is_kit(allocation.sku):
            if len({pick.warehouse for pick in allocation.picks}) > 1:
                raise CheckFailed(f"{allocation.order_id}/{allocation.line_no} ships from several warehouses")


def run_checks(allocations, ship_complete_orders):
    check_stock()
    check_lines(allocations)
    check_single_source(allocations, ship_complete_orders)
    log.info("checks passed: no stock promised twice, every unit allocated or backordered")
