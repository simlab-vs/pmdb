"""Typographic punctuation: curly quotes, dashes and ellipses."""

import re

_TAG_OR_CODE = re.compile(r"(<[^>]+>|`[^`]*`|\]\([^)]*\))")


def educate(text):
    parts = _TAG_OR_CODE.split(text)
    for i in range(0, len(parts), 2):
        part = parts[i]
        part = part.replace("---", "\u2014").replace("--", "\u2013").replace("...", "\u2026")
        part = re.sub(r"(^|[\s(\[])\"", "\\1\u201c", part)
        part = part.replace('"', "\u201d")
        part = re.sub(r"(^|[\s(\[])'", "\\1\u2018", part)
        part = part.replace("'", "\u2019")
        parts[i] = part
    return "".join(parts)


def educate_quotes(page, site):
    for block in page["blocks"]:
        kind = block["kind"]
        if kind in ("paragraph", "quote", "heading"):
            block["text"] = educate(block["text"])
        elif kind == "list":
            block["items"] = [educate(item) for item in block["items"]]
    page["title"] = educate(page["title"])
