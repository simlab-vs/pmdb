"""Rendering blocks to HTML."""

import html

from .markdown import render_inline


def render_block(block):
    kind = block["kind"]
    if kind == "heading":
        level = block["level"]
        attr = f' id="{block["id"]}"' if block.get("id") else ""
        return f"<h{level}{attr}>{render_inline(block['text'])}</h{level}>"
    if kind == "paragraph":
        return f"<p>{render_inline(block['text'])}</p>"
    if kind == "list":
        tag = "ol" if block["ordered"] else "ul"
        items = "".join(f"<li>{render_inline(item)}</li>" for item in block["items"])
        return f"<{tag}>{items}</{tag}>"
    if kind == "code":
        lang = block.get("lang")
        cls = f' class="language-{lang}"' if lang else ""
        body = block.get("html") or html.escape(block["text"])
        return f"<pre><code{cls}>{body}</code></pre>"
    if kind == "quote":
        return f"<blockquote><p>{render_inline(block['text'])}</p></blockquote>"
    if kind == "rule":
        return "<hr>"
    if kind == "html":
        return block["html"]
    raise ValueError(f"unknown block kind: {kind}")


def render_blocks(blocks):
    return "\n".join(render_block(block) for block in blocks)
