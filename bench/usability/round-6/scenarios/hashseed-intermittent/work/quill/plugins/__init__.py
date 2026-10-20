"""Plugin discovery and ordering.

A plugin is a Python module with a manifest of the same name next to it,
either in this package (built-in plugins) or in the site's ``plugins``
directory (site plugins, which take precedence over built-in plugins of the
same name)::

    [plugin]
    name = search
    entry = index_page
    after = heading-ids, excerpt

``entry`` names the function called for each page as ``entry(page, site)``.
``after`` and ``before`` list the plugins this plugin must run after or
before. Plugins that aren't enabled in ``site.ini`` may be named there; such
constraints are ignored, so that plugins can be enabled independently.
"""

import importlib
import importlib.util
import logging
import os
from typing import NamedTuple

from ..config import read_ini

log = logging.getLogger(__name__)

BUILTIN_DIR = os.path.dirname(os.path.abspath(__file__))


class PluginError(Exception):
    """Raised for unknown plugins, bad manifests and ordering cycles."""


class PluginSpec(NamedTuple):
    name: str
    entry: str = "run"
    after: tuple = ()
    before: tuple = ()
    path: str = ""
    origin: str = "builtin"


MANIFEST_KEYS = ("name", "entry", "after", "before")


def load_manifest(path, origin):
    """Read a plugin manifest."""
    meta = read_ini(path).get("plugin")
    if meta is None:
        raise PluginError(f"{path}: missing [plugin] section")
    unknown = set(meta) - set(MANIFEST_KEYS)
    if unknown:
        raise PluginError(f"{path}: unknown keys in [plugin]: {', '.join(sorted(unknown))}")
    meta.setdefault("name", os.path.splitext(os.path.basename(path))[0])
    fields = {key: PluginSpec.__annotations__[key](value) for key, value in meta.items()}
    return PluginSpec(path=os.path.splitext(path)[0] + ".py", origin=origin, **fields)


def scan(directory, origin):
    specs = {}
    if not os.path.isdir(directory):
        return specs
    for name in sorted(os.listdir(directory)):
        if name.endswith(".ini"):
            spec = load_manifest(os.path.join(directory, name), origin)
            if not os.path.exists(spec.path):
                raise PluginError(f"{spec.path}: plugin module not found")
            specs[spec.name] = spec
    return specs


def discover(site):
    """Return the available plugins of a site, by name."""
    specs = scan(BUILTIN_DIR, "builtin")
    site_dir = os.path.join(site["root"], site["plugin_dir"])
    for name, spec in scan(site_dir, "site").items():
        if name in specs:
            log.info("site plugin %s replaces the built-in plugin", name)
        specs[name] = spec
    return specs


def dependency_graph(specs, enabled):
    """Map each enabled plugin to the set of plugins it must run after."""
    unknown = [name for name in enabled if name not in specs]
    if unknown:
        raise PluginError(f"unknown plugins: {', '.join(unknown)}")
    names = set(enabled)
    graph = {name: set() for name in names}
    for name in names:
        spec = specs[name]
        for other in spec.after:
            if other in names:
                graph[name].add(other)
        for other in spec.before:
            if other in names:
                graph[other].add(name)
    return graph


def order_plugins(specs, enabled):
    """Return the enabled plugins in an order satisfying their constraints."""
    graph = dependency_graph(specs, enabled)
    pending = {name: set(deps) for name, deps in graph.items()}
    ready = {name for name, deps in pending.items() if not deps}
    order = []
    while ready:
        name = ready.pop()
        order.append(name)
        del pending[name]
        for other, deps in pending.items():
            if name in deps:
                deps.discard(name)
                if not deps:
                    ready.add(other)
    if pending:
        raise PluginError(f"plugin ordering cycle among: {', '.join(sorted(pending))}")
    log.debug("plugin order: %s", ", ".join(order))
    return order


def _import(spec):
    if spec.origin == "builtin":
        module_name = __name__ + "." + os.path.splitext(os.path.basename(spec.path))[0]
        return importlib.import_module(module_name)
    module_name = "quill_site_plugins." + spec.name
    loader_spec = importlib.util.spec_from_file_location(module_name, spec.path)
    module = importlib.util.module_from_spec(loader_spec)
    loader_spec.loader.exec_module(module)
    return module


def load_plugins(site):
    """Discover, order and import the plugins enabled for a site.

    Returns a list of ``(name, function)`` pairs in running order.
    """
    specs = discover(site)
    order = order_plugins(specs, site["plugins"])
    loaded = []
    for name in order:
        spec = specs[name]
        module = _import(spec)
        function = getattr(module, spec.entry, None)
        if function is None:
            raise PluginError(f"{spec.path}: no function {spec.entry}")
        loaded.append((name, function))
    log.info("loaded %d plugins", len(loaded))
    return loaded
