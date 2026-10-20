"""Reading quill's INI-style files: ``site.ini`` and plugin manifests.

The format is a small subset of INI::

    [section]
    key = value
    other = first, second, third

Values are converted by :func:`parse_value`: comma-separated values become
lists, ``true``/``false`` become Booleans, integers become ``int`` and
anything else stays a string.
"""

import logging
import os

log = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised for malformed configuration files."""


def parse_value(raw):
    """Convert the text of a value to a Python value."""
    text = raw.strip()
    if "," in text:
        return [item.strip() for item in text.split(",") if item.strip()]
    lowered = text.lower()
    if lowered in ("true", "yes", "on"):
        return True
    if lowered in ("false", "no", "off"):
        return False
    if text.lstrip("-").isdigit():
        return int(text)
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    return text


def parse_ini(text, source="<string>"):
    """Parse INI text into a dict mapping section names to dicts of values."""
    sections = {}
    current = None
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            name = stripped[1:-1].strip()
            if not name:
                raise ConfigError(f"{source}:{number}: empty section name")
            current = sections.setdefault(name, {})
            continue
        if "=" not in stripped:
            raise ConfigError(f"{source}:{number}: expected 'key = value'")
        if current is None:
            raise ConfigError(f"{source}:{number}: value outside of a section")
        key, _, value = stripped.partition("=")
        current[key.strip().lower()] = parse_value(value)
    return sections


def read_ini(path):
    """Read and parse an INI file."""
    with open(path, encoding="utf-8") as handle:
        return parse_ini(handle.read(), source=os.fspath(path))


def as_list(value):
    """Return a configuration value as a list of strings."""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


DEFAULTS = {
    "title": "Untitled site",
    "base_url": "/",
    "language": "en",
    "content_dir": "content",
    "template_dir": "templates",
    "plugin_dir": "plugins",
    "default_template": "page",
    "words_per_minute": 220,
}


def load_site_config(site_dir):
    """Load ``site.ini`` from a site directory, filling in defaults."""
    path = os.path.join(site_dir, "site.ini")
    if not os.path.exists(path):
        raise ConfigError(f"{path}: not found")
    sections = read_ini(path)
    site = dict(DEFAULTS)
    site.update(sections.get("site", {}))
    site["plugins"] = as_list(sections.get("build", {}).get("plugins"))
    site["plugin_options"] = {
        name.split(":", 1)[1]: values
        for name, values in sections.items()
        if name.startswith("plugin:")
    }
    site["root"] = os.path.abspath(site_dir)
    log.debug("site config: %s", {k: v for k, v in site.items() if k != "plugin_options"})
    return site
