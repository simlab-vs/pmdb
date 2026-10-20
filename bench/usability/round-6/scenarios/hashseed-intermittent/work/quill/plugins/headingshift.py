"""Shift heading levels so that the body starts at ``<h2>``.

The page template renders the title as the page's only ``<h1>``; a body
that starts with ``# Title`` repeating it loses that heading, and the
remaining headings are shifted so that the highest is ``<h2>``.
"""


def shift_headings(page, site):
    blocks = page["blocks"]
    first = next((i for i, b in enumerate(blocks) if b["kind"] != "rule"), None)
    if first is not None and blocks[first]["kind"] == "heading" and blocks[first]["level"] == 1:
        if blocks[first]["text"].strip().lower() == page["title"].strip().lower():
            del blocks[first]
    levels = [b["level"] for b in blocks if b["kind"] == "heading"]
    if not levels:
        return
    shift = 2 - min(levels)
    if shift <= 0:
        return
    for block in blocks:
        if block["kind"] == "heading":
            block["level"] = min(6, block["level"] + shift)
