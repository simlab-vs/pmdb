"""Generate the oracle's hidden sites (deterministic).

site-b: the generator's site with two site plugins whose manifests name a
        single plugin in ``after``/``before``.
site-c: a smaller site enabling only a subset of the built-in plugins.
"""

import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "hidden")

TAGALIASES_PY = '''"""Rename tags according to [plugin:tagaliases] in site.ini."""


def alias_tags(page, site):
    aliases = site["plugin_options"].get("tagaliases", {})
    tags = page["extra"].get("tags")
    if tags:
        page["extra"]["tags"] = sorted({str(aliases.get(tag, tag)) for tag in tags})
'''

TAGALIASES_INI = """[plugin]
name = tagaliases
entry = alias_tags
after = tags
"""

LEAD_PY = '''"""Use a leading "TL;DR:" paragraph as the page summary."""


def take_lead(page, site):
    for block in page["blocks"]:
        if block["kind"] == "paragraph" and block["text"].startswith("TL;DR:"):
            page["meta"]["summary"] = block["text"][len("TL;DR:"):].strip()
            return
'''

LEAD_INI = """[plugin]
name = lead
entry = take_lead
before = excerpt
"""


def make(name, seed, repeat, plugins=None):
    site = os.path.join(OUT, name)
    shutil.rmtree(site, ignore_errors=True)
    subprocess.run([sys.executable, os.path.join(HERE, "make_site.py"), site, "--seed", str(seed),
                    "--repeat", str(repeat), "--title", f"Hidden {name}"], check=True)
    if plugins is not None:
        ini = os.path.join(site, "site.ini")
        text = open(ini).read()
        text = re.sub(r"^plugins = .*$", "plugins = " + ", ".join(plugins), text, flags=re.M)
        open(ini, "w").write(text)
    return site


def main():
    site_b = make("site-b", 7, 1, plugins=[
        "abbr", "editlink", "excerpt", "extlinks", "footnotes", "heading-ids",
        "headingshift", "highlight", "lead", "readingtime", "search", "smartypants", "tagaliases", "tags", "toc"])
    os.makedirs(os.path.join(site_b, "plugins"))
    for name, text in [("tagaliases.py", TAGALIASES_PY), ("tagaliases.ini", TAGALIASES_INI),
                       ("lead.py", LEAD_PY), ("lead.ini", LEAD_INI)]:
        with open(os.path.join(site_b, "plugins", name), "w") as f:
            f.write(text)
    with open(os.path.join(site_b, "site.ini"), "a") as f:
        f.write("\n[plugin:tagaliases]\nperformance = tuning\napi = http-api\n")
    for rel in ("ops/alerts.md", "getting-started/installation.md"):
        path = os.path.join(site_b, "content", rel)
        text = open(path).read()
        head, sep, body = text.partition("\n---\n")
        with open(path, "w") as f:
            f.write(head + sep + "TL;DR: the short version comes first and the details follow below.\n\n" + body)
    make("site-c", 11, 1, plugins=["excerpt", "heading-ids", "search", "tags", "toc"])


if __name__ == "__main__":
    main()
