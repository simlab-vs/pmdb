"""Tags: normalize the ``tags`` front matter entry.

The builder writes one listing page per tag.
"""


def normalize_tags(page, site):
    raw = page["meta"].get("tags")
    if not raw:
        page["extra"]["tags"] = []
        return
    values = raw if isinstance(raw, list) else [raw]
    tags = {str(value).strip().lower().replace(" ", "-") for value in values if str(value).strip()}
    page["extra"]["tags"] = sorted(tags)
