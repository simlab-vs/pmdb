"""Page summaries for listings, feeds and the search index."""

from ..markdown import plain_text


def make_excerpt(page, site):
    explicit = page["meta"].get("summary")
    if explicit:
        page["extra"]["summary"] = str(explicit)
        return
    limit = site["plugin_options"].get("excerpt", {}).get("length", 160)
    for block in page["blocks"]:
        if block["kind"] == "paragraph":
            text = " ".join(plain_text(block["text"]).split())
            if len(text) > limit:
                cut = text.rfind(" ", 0, limit)
                text = text[: cut if cut > 0 else limit].rstrip(",.;:") + "…"
            page["extra"]["summary"] = text
            return
    page["extra"]["summary"] = ""
