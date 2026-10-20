"""Minimal syntax highlighting for code blocks."""

import html
import keyword
import re

_PY_TOKEN = re.compile(r"(#[^\n]*|\"[^\"\n]*\"|'[^'\n]*'|\b\d+(?:\.\d+)?\b|\b\w+\b)")
_SH_TOKEN = re.compile(r"(#[^\n]*|\"[^\"\n]*\"|'[^'\n]*'|(?<![\w-])--?[\w-]+)")


def _span(cls, text):
    return f'<span class="{cls}">{html.escape(text)}</span>'


def _python(code):
    out = []
    last = 0
    for match in _PY_TOKEN.finditer(code):
        out.append(html.escape(code[last:match.start()]))
        token = match.group(0)
        if token.startswith("#"):
            out.append(_span("c", token))
        elif token[0] in "\"'":
            out.append(_span("s", token))
        elif token[0].isdigit():
            out.append(_span("n", token))
        elif keyword.iskeyword(token):
            out.append(_span("k", token))
        else:
            out.append(html.escape(token))
        last = match.end()
    out.append(html.escape(code[last:]))
    return "".join(out)


def _shell(code):
    out = []
    last = 0
    for match in _SH_TOKEN.finditer(code):
        out.append(html.escape(code[last:match.start()]))
        token = match.group(0)
        cls = "c" if token.startswith("#") else "s" if token[0] in "\"'" else "o"
        out.append(_span(cls, token))
        last = match.end()
    out.append(html.escape(code[last:]))
    return "".join(out)


LANGUAGES = {"python": _python, "py": _python, "sh": _shell, "shell": _shell, "console": _shell}


def highlight_code(page, site):
    for block in page["blocks"]:
        if block["kind"] == "code":
            highlighter = LANGUAGES.get((block.get("lang") or "").lower())
            if highlighter:
                block["html"] = highlighter(block["text"])
