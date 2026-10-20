"""Building a site: content pages to HTML files."""

import json
import logging
import os
import shutil
import time
from xml.sax.saxutils import escape

from . import __version__
from .config import load_site_config
from .content import load_pages
from .plugins import load_plugins
from .render import render_blocks
from .templates import Templates

log = logging.getLogger(__name__)


class BuildError(Exception):
    """Raised when a page can't be built."""


def apply_plugins(page, plugins, site):
    for name, function in plugins:
        try:
            function(page, site)
        except Exception as error:
            raise BuildError(f"{page['source']}: plugin {name} failed: {error}") from error
    return page


def output_path(out_dir, url):
    relative = url.strip("/")
    return os.path.join(out_dir, relative, "index.html") if relative else os.path.join(out_dir, "index.html")


def page_context(page, site, navigation):
    return {
        "site": {"title": site["title"], "base_url": site["base_url"], "language": site["language"]},
        "page": page,
        "content": render_blocks(page["blocks"]),
        "toc": page["toc"],
        "extra": page["extra"],
        "navigation": navigation,
        "generator": f"quill {__version__}",
    }


def build_navigation(pages):
    """Group pages by section, ordered by their ``weight`` and title."""
    sections = {}
    for page in pages:
        sections.setdefault(page["section"], []).append(page)
    navigation = []
    for section in sorted(sections):
        entries = sorted(
            sections[section],
            key=lambda p: (int(p["meta"].get("weight", 100)), p["title"].lower(), p["url"]),
        )
        navigation.append({
            "name": section.replace("-", " ").title() if section else "Home",
            "pages": [{"title": p["title"], "url": p["url"]} for p in entries],
        })
    return navigation


def write_file(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def write_search_index(out_dir, pages):
    entries = [entry for page in pages for entry in page["extra"].get("search", [])]
    write_file(os.path.join(out_dir, "search.json"), json.dumps(entries, indent=1, ensure_ascii=False, sort_keys=True))
    return len(entries)


def write_sitemap(out_dir, pages, site):
    base = str(site["base_url"]).rstrip("/")
    urls = sorted(page["url"] for page in pages)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    lines += [f"  <url><loc>{escape(base + url)}</loc></url>" for url in urls]
    lines.append("</urlset>")
    write_file(os.path.join(out_dir, "sitemap.xml"), "\n".join(lines) + "\n")


def write_tag_pages(out_dir, pages, site, templates, navigation):
    tagged = {}
    for page in pages:
        for tag in page["extra"].get("tags", []):
            tagged.setdefault(tag, []).append({"title": page["title"], "url": page["url"]})
    for tag, entries in sorted(tagged.items()):
        listing = {
            "title": f"Pages tagged “{tag}”",
            "url": f"/tags/{tag}/",
            "entries": sorted(entries, key=lambda e: e["url"]),
        }
        context = {"site": {"title": site["title"], "language": site["language"]}, "page": listing, "navigation": navigation}
        write_file(output_path(out_dir, listing["url"]), templates.render("tag", context))
    return len(tagged)


def copy_static(site, out_dir):
    static = os.path.join(site["root"], "static")
    if os.path.isdir(static):
        shutil.copytree(static, os.path.join(out_dir, "static"), dirs_exist_ok=True)


def build(site_dir, out_dir, clean=True):
    """Build the site in ``site_dir`` into ``out_dir``. Returns a summary dict."""
    started = time.perf_counter()
    site = load_site_config(site_dir)
    plugins = load_plugins(site)
    pages = load_pages(os.path.join(site["root"], site["content_dir"]))
    templates = Templates(os.path.join(site["root"], site["template_dir"]))
    if clean and os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    for page in pages:
        apply_plugins(page, plugins, site)
    navigation = build_navigation(pages)
    for page in pages:
        template = str(page["meta"].get("template", site["default_template"]))
        html = templates.render(template, page_context(page, site, navigation))
        write_file(output_path(out_dir, page["url"]), html)
    entries = write_search_index(out_dir, pages)
    write_sitemap(out_dir, pages, site)
    tags = write_tag_pages(out_dir, pages, site, templates, navigation)
    copy_static(site, out_dir)
    summary = {
        "pages": len(pages),
        "search_entries": entries,
        "tags": tags,
        "seconds": round(time.perf_counter() - started, 2),
    }
    log.info("built %(pages)d pages, %(tags)d tag pages, %(search_entries)d search entries in %(seconds)ss", summary)
    return summary
