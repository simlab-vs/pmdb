"""Abbreviations: wrap known abbreviations in ``<abbr>`` elements.

Abbreviations come from the ``[plugin:abbr]`` section of ``site.ini`` and
from the page's ``abbr`` front matter entry (``ABBR=Expansion`` pairs).
"""

import re


def _definitions(page, site):
    definitions = dict(site["plugin_options"].get("abbr", {}))
    extra = page["meta"].get("abbr")
    if extra:
        for pair in extra if isinstance(extra, list) else [extra]:
            key, _, value = str(pair).partition("=")
            if value:
                definitions[key.strip().lower()] = value.strip()
    return {key.upper(): value for key, value in definitions.items()}


def mark_abbreviations(page, site):
    definitions = _definitions(page, site)
    if not definitions:
        return
    pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(definitions, key=len, reverse=True)) + r")\b")

    def wrap(text):
        pieces = re.split(r"(<[^>]+>|`[^`]*`)", text)
        for i in range(0, len(pieces), 2):
            pieces[i] = pattern.sub(lambda m: f'<abbr title="{definitions[m.group(1)]}">{m.group(1)}</abbr>', pieces[i])
        return "".join(pieces)

    for block in page["blocks"]:
        if block["kind"] == "paragraph":
            block["text"] = wrap(block["text"])
        elif block["kind"] == "list":
            block["items"] = [wrap(item) for item in block["items"]]
