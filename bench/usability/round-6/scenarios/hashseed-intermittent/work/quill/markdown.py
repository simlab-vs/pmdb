"""A small Markdown parser.

Pages are parsed into a list of *blocks*, plain dicts with a ``kind`` and
kind-specific fields, so that plugins can inspect and rewrite them before
they are rendered to HTML by :mod:`quill.render`:

=========== ==============================================
kind        fields
=========== ==============================================
heading     ``level``, ``text``, ``id``
paragraph   ``text``
list        ``ordered``, ``items`` (list of strings)
code        ``lang``, ``text``
quote       ``text``
rule        (none)
html        ``html`` (raw HTML, inserted by plugins)
=========== ==============================================

Inline markup (emphasis, code spans, links, images) stays in the text and
is converted by :func:`render_inline`.
"""

import html
import re

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_ULIST = re.compile(r"^\s*[-*+]\s+(.*)$")
_OLIST = re.compile(r"^\s*\d+[.)]\s+(.*)$")
_FENCE = re.compile(r"^(```|~~~)\s*([\w+-]*)\s*$")
_RULE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")


def heading(level, text):
    return {"kind": "heading", "level": level, "text": text, "id": None}


def parse_blocks(source):
    """Parse Markdown text into a list of blocks."""
    lines = source.replace("\r\n", "\n").split("\n")
    blocks = []
    paragraph = []
    i = 0

    def flush_paragraph():
        if paragraph:
            blocks.append({"kind": "paragraph", "text": " ".join(paragraph)})
            paragraph.clear()

    while i < len(lines):
        line = lines[i]
        fence = _FENCE.match(line)
        if fence:
            flush_paragraph()
            marker, lang = fence.group(1), fence.group(2)
            body = []
            i += 1
            while i < len(lines) and not lines[i].startswith(marker):
                body.append(lines[i])
                i += 1
            blocks.append({"kind": "code", "lang": lang or None, "text": "\n".join(body)})
            i += 1
            continue
        if not line.strip():
            flush_paragraph()
            i += 1
            continue
        match = _HEADING.match(line)
        if match:
            flush_paragraph()
            blocks.append(heading(len(match.group(1)), match.group(2)))
            i += 1
            continue
        if _RULE.match(line):
            flush_paragraph()
            blocks.append({"kind": "rule"})
            i += 1
            continue
        if line.startswith(">"):
            flush_paragraph()
            quoted = []
            while i < len(lines) and lines[i].startswith(">"):
                quoted.append(lines[i][1:].strip())
                i += 1
            blocks.append({"kind": "quote", "text": " ".join(quoted)})
            continue
        for pattern, ordered in ((_ULIST, False), (_OLIST, True)):
            if pattern.match(line):
                flush_paragraph()
                items = []
                while i < len(lines) and pattern.match(lines[i]):
                    items.append(pattern.match(lines[i]).group(1))
                    i += 1
                    while i < len(lines) and lines[i].startswith("  ") and lines[i].strip():
                        items[-1] += " " + lines[i].strip()
                        i += 1
                blocks.append({"kind": "list", "ordered": ordered, "items": items})
                break
        else:
            paragraph.append(line.strip())
            i += 1
    flush_paragraph()
    return blocks


_CODE_SPAN = re.compile(r"`([^`]+)`")
_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_STRONG = re.compile(r"\*\*(.+?)\*\*")
_EM = re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])")
_PLACEHOLDER = "\x00{}\x00"


def render_inline(text):
    """Convert inline Markdown to HTML.

    Code spans are protected first so that their content is not interpreted;
    text that is already HTML (``<abbr>``, ``<sup>`` inserted by plugins) is
    kept as is.
    """
    stash = []

    def protect(fragment):
        stash.append(fragment)
        return _PLACEHOLDER.format(len(stash) - 1)

    text = _CODE_SPAN.sub(lambda m: protect(f"<code>{html.escape(m.group(1))}</code>"), text)
    text = re.sub(r"<(/?)(abbr|sup|a|span|em|strong)([^>]*)>", lambda m: protect(m.group(0)), text)
    text = html.escape(text, quote=False)
    text = _IMAGE.sub(_render_image, text)
    text = _LINK.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', text)
    text = _STRONG.sub(r"<strong>\1</strong>", text)
    text = _EM.sub(r"<em>\1</em>", text)
    return re.sub("\x00(\\d+)\x00", lambda m: stash[int(m.group(1))], text)


def _render_image(match):
    alt, src, title = match.group(1), match.group(2), match.group(3)
    title_attr = f' title="{title}"' if title else ""
    return f'<img src="{src}" alt="{alt}"{title_attr}>'


def plain_text(text):
    """Strip inline markup, keeping the visible text."""
    text = _IMAGE.sub(lambda m: m.group(1), text)
    text = _LINK.sub(lambda m: m.group(1), text)
    text = _CODE_SPAN.sub(lambda m: m.group(1), text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.replace("**", "").replace("*", "")
