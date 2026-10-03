"""Small helpers shared by the invoicing modules."""


def ranked(items, key, descending=False):
    """The items ordered by ``key``, largest first when ``descending``."""
    items.sort(key=key, reverse=descending)
    return items


def first(items, predicate, default=None):
    """The first item satisfying ``predicate``, or ``default``."""
    for item in items:
        if predicate(item):
            return item
    return default


def group_by(items, key):
    """``{key: [items]}``, keeping the items' order within each group."""
    groups = {}
    for item in items:
        groups.setdefault(key(item), []).append(item)
    return groups
