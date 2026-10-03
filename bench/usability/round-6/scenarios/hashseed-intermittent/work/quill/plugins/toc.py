"""Build the page's table of contents from its headings."""


def build_toc(page, site):
    options = site["plugin_options"].get("toc", {})
    lowest = options.get("min_level", 2)
    highest = options.get("max_level", 3)
    entries = []
    for block in page["blocks"]:
        if block["kind"] != "heading":
            continue
        if not lowest <= block["level"] <= highest:
            continue
        entries.append({
            "text": block["text"],
            "href": "#" + (block.get("id") or ""),
            "level": block["level"],
            "indent": block["level"] - lowest,
        })
    if len(entries) >= options.get("min_entries", 2):
        page["toc"] = entries
