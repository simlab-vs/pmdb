"""Carts: the units an order asks for, as a dict from SKU to quantity."""

from . import catalog

MAX_UNITS_PER_LINE = 24
MAX_UNITS = 40


class CartError(ValueError):
    """An order's lines don't make a valid cart."""


def build_cart(lines):
    """Merge the order ``lines`` into a cart ``{sku: quantity}``.

    Lines for the same SKU are added up, lines with a quantity of 0 are
    dropped, and SKUs are normalized to upper case.
    """
    cart = {}
    for number, line in enumerate(lines, 1):
        sku = str(line["sku"]).strip().upper()
        try:
            qty = int(line.get("qty", 1))
        except (TypeError, ValueError):
            raise CartError(f"line {number}: bad quantity {line.get('qty')!r}") from None
        if qty < 0 or qty > MAX_UNITS_PER_LINE:
            raise CartError(f"line {number}: quantity {qty} out of range")
        if qty == 0:
            continue
        product = catalog.product(sku)
        if not product.active:
            raise CartError(f"line {number}: {sku} is no longer sold")
        cart[sku] = cart.get(sku, 0) + qty
    if sum(cart.values()) > MAX_UNITS:
        raise CartError(f"more than {MAX_UNITS} units")
    return dict(sorted(cart.items()))


def cart_key(cart):
    """A hashable form of ``cart``, the same for equal carts."""
    return tuple(sorted(cart.items()))


def first_sku(cart):
    """The SKU the search prices next: the first in alphabetical order."""
    return min(cart)


def units(cart):
    """The number of units in ``cart``."""
    return sum(cart.values())


def contains(cart, take):
    """Whether ``cart`` holds at least the units in ``take``."""
    return all(cart.get(sku, 0) >= qty for sku, qty in take.items())


def remove_units(cart, take):
    """Return ``cart`` without the units in ``take``."""
    rest = dict(cart)
    for sku, qty in take.items():
        left = rest.get(sku, 0) - qty
        if left < 0:
            raise CartError(f"can't take {qty} x {sku} from the cart")
        if left:
            rest[sku] = left
        else:
            del rest[sku]
    return rest


def expand(cart, skus=None):
    """The cart's units as a sorted list of SKUs, one entry per unit."""
    out = []
    for sku in sorted(cart):
        if skus is None or sku in skus:
            out.extend([sku] * cart[sku])
    return out
