"""Collect the search index entry of each page.

The builder writes the entries of all pages to ``search.json``.
"""

from ..markdown import plain_text


def index_page(page, site):
    if page["meta"].get("search") is False:
        return
    sections = []
    current = {"heading": page["title"], "anchor": "", "words": []}
    for block in page["blocks"]:
        if block["kind"] == "heading":
            if current["words"]:
                sections.append(current)
            current = {"heading": plain_text(block["text"]), "anchor": block.get("id") or "", "words": []}
        elif block["kind"] in ("paragraph", "quote"):
            current["words"].extend(plain_text(block["text"]).split())
        elif block["kind"] == "list":
            for item in block["items"]:
                current["words"].extend(plain_text(item).split())
    if current["words"]:
        sections.append(current)
    page["extra"]["search"] = [
        {
            "title": page["title"],
            "section": section["heading"],
            "url": page["url"] + ("#" + section["anchor"] if section["anchor"] else ""),
            "text": " ".join(section["words"][:60]),
        }
        for section in sections
    ]
