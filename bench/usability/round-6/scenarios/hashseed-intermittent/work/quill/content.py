"""Loading content pages.

A page is a Markdown file with an optional front matter block::

    ---
    title: Installing quill
    weight: 10
    tags: setup, install
    ---
    # Installing quill
    ...

Pages are represented as dicts so that plugins can add fields freely.
"""

import logging
import os
import re

from .config import parse_value
from .markdown import parse_blocks

log = logging.getLogger(__name__)

_FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


class ContentError(Exception):
    """Raised for pages that can't be loaded."""


def split_front_matter(text, source):
    """Split a page into its front matter (a dict) and its body."""
    match = _FRONT_MATTER.match(text)
    if not match:
        return {}, text
    meta = {}
    for number, line in enumerate(match.group(1).splitlines(), start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ContentError(f"{source}:{number}: expected 'key: value' in front matter")
        meta[key.strip().lower()] = parse_value(value)
    return meta, text[match.end():]


def url_for(relpath):
    """Return the URL path of the page stored at ``relpath``."""
    stem, _ = os.path.splitext(relpath.replace(os.sep, "/"))
    if stem == "index":
        return "/"
    if stem.endswith("/index"):
        return "/" + stem[: -len("index")]
    return "/" + stem + "/"


def section_of(relpath):
    parts = relpath.replace(os.sep, "/").split("/")
    return parts[0] if len(parts) > 1 else ""


def load_page(content_dir, relpath):
    """Load one page."""
    path = os.path.join(content_dir, relpath)
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    meta, body = split_front_matter(text, relpath)
    blocks = parse_blocks(body)
    title = meta.get("title")
    if title is None:
        first = next((b for b in blocks if b["kind"] == "heading"), None)
        title = first["text"] if first else os.path.splitext(os.path.basename(relpath))[0]
    return {
        "source": relpath.replace(os.sep, "/"),
        "url": url_for(relpath),
        "section": section_of(relpath),
        "title": str(title),
        "meta": meta,
        "blocks": blocks,
        "toc": [],
        "extra": {},
    }


def find_pages(content_dir):
    """Return the relative paths of the Markdown files under ``content_dir``."""
    found = []
    for root, dirs, files in os.walk(content_dir):
        dirs[:] = sorted(d for d in dirs if not d.startswith((".", "_")))
        for name in sorted(files):
            if name.endswith(".md") and not name.startswith((".", "_")):
                found.append(os.path.relpath(os.path.join(root, name), content_dir))
    return found


def load_pages(content_dir):
    """Load every page of a site, skipping drafts."""
    pages = []
    for relpath in find_pages(content_dir):
        page = load_page(content_dir, relpath)
        if page["meta"].get("draft") is True:
            log.debug("skipping draft %s", relpath)
            continue
        pages.append(page)
    log.info("loaded %d pages from %s", len(pages), content_dir)
    return pages
