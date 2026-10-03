"""A minimal template language.

Templates are HTML files with these tags:

* ``{{ name }}`` and ``{{ page.title }}`` insert an escaped value,
  ``{{{ name }}}`` inserts it unescaped;
* ``{{> partial }}`` includes ``templates/partials/partial.html``;
* ``{{#each list}} ... {{/each}}`` repeats its body for each item, with
  ``{{ item.field }}`` referring to the item, and ``{{#if value}} ...
  {{/if}}`` keeps its body only if the value is truthy.

Templates are compiled once into a tree of nodes, ``("text", s)``,
``("var", name, escape)``, ``("each", name, body)`` and ``("if", name, body)``.
"""

import html
import os
import re

_TOKEN = re.compile(r"(\{\{\{\s*[\w.]+\s*\}\}\}|\{\{[#/>]?\s*[\w.-]+(?:\s+[\w.]+)?\s*\}\})")


class TemplateError(Exception):
    """Raised for missing templates or partials and malformed tags."""


def compile_template(text, source="<string>"):
    """Compile template text (with partials already included) into nodes."""
    root = []
    stack = [("root", None, root)]
    for piece in _TOKEN.split(text):
        if not piece:
            continue
        if not piece.startswith("{{"):
            stack[-1][2].append(("text", piece))
            continue
        if piece.startswith("{{{"):
            stack[-1][2].append(("var", piece[3:-3].strip(), False))
            continue
        inner = piece[2:-2].strip()
        if inner.startswith("#"):
            kind, _, name = inner[1:].partition(" ")
            if kind not in ("each", "if") or not name.strip():
                raise TemplateError(f"{source}: bad block tag {piece}")
            body = []
            stack[-1][2].append((kind, name.strip(), body))
            stack.append((kind, name.strip(), body))
        elif inner.startswith("/"):
            if len(stack) == 1 or stack[-1][0] != inner[1:].strip():
                raise TemplateError(f"{source}: unexpected {piece}")
            stack.pop()
        elif inner.startswith(">"):
            raise TemplateError(f"{source}: partial {piece} was not included")
        else:
            stack[-1][2].append(("var", inner, True))
    if len(stack) != 1:
        raise TemplateError(f"{source}: unclosed {{{{#{stack[-1][0]} {stack[-1][1]}}}}}")
    return root


def render_nodes(nodes, context):
    """Render compiled nodes with a context dict."""
    out = []
    work = [(iter(nodes), context)]
    while work:
        iterator, scope = work[-1]
        node = next(iterator, None)
        if node is None:
            work.pop()
            continue
        kind = node[0]
        if kind == "text":
            out.append(node[1])
            continue
        value = scope
        for part in node[1].split("."):
            value = value.get(part) if isinstance(value, dict) else getattr(value, part, None)
            if value is None:
                break
        if kind == "var":
            if value is not None:
                out.append(html.escape(str(value)) if node[2] else str(value))
        elif kind == "if":
            if value:
                work.append((iter(node[2]), scope))
        else:
            for item in reversed(list(value or ())):
                work.append((iter(node[2]), dict(scope, item=item)))
    return "".join(out)


class Templates:
    """Templates of a site, loaded and compiled on first use."""

    def __init__(self, directory):
        self.directory = directory
        self._compiled = {}

    def _read(self, name):
        path = os.path.join(self.directory, name + ".html")
        if not os.path.exists(path):
            raise TemplateError(f"template not found: {name}")
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def get(self, name):
        if name not in self._compiled:
            text = re.sub(r"\{\{>\s*([\w-]+)\s*\}\}", lambda m: self._read("partials/" + m.group(1)), self._read(name))
            self._compiled[name] = compile_template(text, source=name)
        return self._compiled[name]

    def render(self, name, context):
        return render_nodes(self.get(name), context)
