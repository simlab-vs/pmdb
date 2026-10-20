"""Give every heading a unique ``id`` so that it can be linked to."""

import re
import unicodedata

from ..markdown import plain_text


def slugify(text):
    text = unicodedata.normalize("NFKD", plain_text(text))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text).strip("-") or "section"


def add_heading_ids(page, site):
    seen = {}
    for block in page["blocks"]:
        if block["kind"] != "heading" or block.get("id"):
            continue
        slug = slugify(block["text"])
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        block["id"] = slug if count == 0 else f"{slug}-{count}"
