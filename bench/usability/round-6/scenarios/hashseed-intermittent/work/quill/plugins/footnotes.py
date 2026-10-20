"""Footnotes: ``text[^1]`` references and ``[^1]: note`` definitions.

Definitions are removed from the body and collected in a "Notes" section at
the end of the page, and references become superscript links to them.
"""

import re

from ..markdown import heading, render_inline

_DEFINITION = re.compile(r"^\[\^([\w-]+)\]:\s*(.*)$")
_REFERENCE = re.compile(r"\[\^([\w-]+)\]")


def collect_footnotes(page, site):
    notes = {}
    kept = []
    for block in page["blocks"]:
        if block["kind"] == "paragraph":
            match = _DEFINITION.match(block["text"])
            if match:
                notes[match.group(1)] = match.group(2)
                continue
        kept.append(block)
    if not notes:
        page["blocks"] = kept
        return
    numbers = {}

    def reference(match):
        key = match.group(1)
        if key not in notes:
            return match.group(0)
        number = numbers.setdefault(key, len(numbers) + 1)
        return f'<sup><a href="#fn-{key}">{number}</a></sup>'

    for block in kept:
        if block["kind"] in ("paragraph", "quote"):
            block["text"] = _REFERENCE.sub(reference, block["text"])
        elif block["kind"] == "list":
            block["items"] = [_REFERENCE.sub(reference, item) for item in block["items"]]
    title = site["plugin_options"].get("footnotes", {}).get("title", "Notes")
    items = "".join(
        f'<li id="fn-{key}">{render_inline(notes[key])}</li>'
        for key in sorted(numbers, key=numbers.get)
    )
    kept.append(heading(2, title))
    kept.append({"kind": "html", "html": f'<ol class="footnotes">{items}</ol>'})
    page["blocks"] = kept
