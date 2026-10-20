"""Estimate the reading time of a page."""

import math

from ..markdown import plain_text


def count_words(blocks):
    words = 0
    for block in blocks:
        if block["kind"] in ("paragraph", "quote"):
            words += len(plain_text(block["text"]).split())
        elif block["kind"] == "list":
            words += sum(len(plain_text(item).split()) for item in block["items"])
        elif block["kind"] == "code":
            words += len(block["text"].split()) // 2
    return words


def estimate_reading_time(page, site):
    words = count_words(page["blocks"])
    per_minute = int(site.get("words_per_minute") or 220)
    page["extra"]["words"] = words
    page["extra"]["minutes"] = max(1, math.ceil(words / per_minute))
