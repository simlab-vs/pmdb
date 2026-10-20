"""Collect the external links of a page and mark them."""

import re

_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def mark_external_links(page, site):
    found = []

    def mark(match):
        text, url = match.group(1), match.group(2)
        if url not in found:
            found.append(url)
        return f'<a href="{url}" class="external" rel="noopener">{text}</a>'

    for block in page["blocks"]:
        if block["kind"] in ("paragraph", "quote"):
            block["text"] = _LINK.sub(mark, block["text"])
        elif block["kind"] == "list":
            block["items"] = [_LINK.sub(mark, item) for item in block["items"]]
    page["extra"]["external_links"] = found
