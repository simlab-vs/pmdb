"""Generate the documentation site used by the scenario (deterministic).

Usage: python3 make_site.py OUT_SITE_DIR [--pages N] [--seed S] [--title T]
"""

import argparse
import os
import random

WORDS = ("the server keeps a journal of every change so that replicas can catch up after a restart "
         "while clients read from the nearest node and writes go to the leader which batches them "
         "into segments that are compacted in the background when the retention window expires "
         "operators can tune the batch size the flush interval and the number of open segments "
         "per partition and the defaults suit most deployments with moderate write rates").split()

SECTIONS = {
    "getting-started": ["Installation", "First steps", "Concepts", "Configuration basics", "Upgrading"],
    "guides": ["Replication", "Backups", "Monitoring", "Securing a cluster", "Tuning writes",
               "Tuning reads", "Multi-region setups", "Migrating data", "Rolling restarts", "Capacity planning"],
    "reference": ["Configuration file", "Environment variables", "HTTP API", "Metrics", "Log format",
                  "Error codes", "Limits", "Glossary"],
    "cli": ["tide", "tide init", "tide start", "tide stop", "tide status", "tide backup", "tide restore",
            "tide compact", "tide join", "tide leave"],
    "ops": ["Alerts", "Runbooks", "Disaster recovery", "Disk usage", "Network partitions", "Certificates"],
    "faq": ["General", "Performance", "Licensing"],
}

HEADINGS = ["Overview", "Before you begin", "How it works", "Options", "Examples", "Defaults",
            "Troubleshooting", "Limitations", "Related settings", "Choosing values", "Failure modes",
            "Verifying the result", "Next steps", "Background", "Common mistakes", "Performance"]
SUBHEADINGS = ["On Linux", "On macOS", "In containers", "With TLS", "Without TLS", "Small clusters",
               "Large clusters", "During upgrades", "Using the API", "From the command line"]


def sentence(rng, n=None):
    n = n or rng.randint(8, 18)
    words = [rng.choice(WORDS) for _ in range(n)]
    if rng.random() < 0.15:
        i = rng.randrange(len(words))
        words[i] = '"' + words[i] + '"'
    if rng.random() < 0.25:
        words.insert(rng.randrange(len(words)), rng.choice(["API", "CLI", "TLS"]))
    if rng.random() < 0.1:
        words.insert(rng.randrange(len(words)), "--")
    text = " ".join(words)
    return text[0].upper() + text[1:] + "."


def paragraph(rng):
    text = " ".join(sentence(rng) for _ in range(rng.randint(2, 5)))
    if rng.random() < 0.2:
        text += " See the [upstream notes](https://example.org/tide/notes) for details."
    if rng.random() < 0.15:
        text += " It's *usually* fine to keep the `default` value."
    return text


def code(rng):
    if rng.random() < 0.5:
        return "```sh\ntide start --config /etc/tide/tide.conf --data-dir /var/lib/tide\n# check the node\ntide status --verbose\n```"
    return "```python\nimport tide\n\nclient = tide.connect(\"localhost:7400\")\nfor key in client.scan(prefix=\"orders/\", limit=100):\n    print(key)  # each key once\n```"


def page_text(rng, title, weight, section):
    lines = ["---", f"title: {title}", f"weight: {weight}"]
    tags = rng.sample(["setup", "cluster", "storage", "security", "performance", "api", "operations"], rng.randint(0, 3))
    if len(tags) > 1:
        lines.append("tags: " + ", ".join(tags))
    elif tags:
        lines.append("tags: " + tags[0])
    if rng.random() < 0.1:
        lines.append("abbr: WAL=write-ahead log, RPO=recovery point objective")
    lines.append("---")
    body = [f"# {title}", "", paragraph(rng), ""]
    footnotes = []
    headings = rng.sample(HEADINGS, rng.randint(1, 6))
    for heading in headings:
        body += [f"## {heading}", ""]
        for _ in range(rng.randint(1, 3)):
            text = paragraph(rng)
            if rng.random() < 0.15:
                key = str(len(footnotes) + 1)
                text += f" This applies to version 3 and later[^{key}]."
                footnotes.append(f"[^{key}]: Earlier versions behave differently and are no longer supported.")
            body += [text, ""]
        r = rng.random()
        if r < 0.3:
            body += [f"- {sentence(rng, 6)}" for _ in range(rng.randint(2, 5))] + [""]
        elif r < 0.45:
            body += [code(rng), ""]
        elif r < 0.55:
            body += ["> " + sentence(rng), ""]
        if rng.random() < 0.3:
            body += [f"### {rng.choice(SUBHEADINGS)}", "", paragraph(rng), ""]
    for note in footnotes:
        body += [note, ""]
    return "\n".join(lines) + "\n" + "\n".join(body)


SITE_INI = """[site]
title = {title}
base_url = https://docs.tide.example/
language = en
default_template = page

[build]
plugins = {plugins}

[plugin:toc]
min_level = 2
max_level = 3

[plugin:abbr]
api = Application Programming Interface
cli = Command-Line Interface
tls = Transport Layer Security

[plugin:editlink]
repository = https://git.example.org/tide/docs
branch = main
path = content

[plugin:excerpt]
length = 160
"""

PLUGINS = "abbr, editlink, excerpt, extlinks, footnotes, heading-ids, headingshift, highlight, readingtime, search, smartypants, tags, toc"

PAGE_HTML = """<!doctype html>
<html lang="{{ site.language }}">
{{> head }}
<body>
{{> nav }}
<main>
<article>
<h1>{{ page.title }}</h1>
<p class="meta">{{#if extra.minutes}}{{ extra.minutes }} min read{{/if}}{{#each extra.tags}} <a class="tag" href="/tags/{{ item }}/">{{ item }}</a>{{/each}}</p>
{{> toc }}
{{{ content }}}
{{#if extra.edit_url}}<p class="edit"><a href="{{ extra.edit_url }}">Edit this page</a></p>{{/if}}
</article>
</main>
{{> footer }}
</body>
</html>
"""

TAG_HTML = """<!doctype html>
<html lang="{{ site.language }}">
<head><meta charset="utf-8"><title>{{ page.title }} — {{ site.title }}</title><link rel="stylesheet" href="/static/style.css"></head>
<body>
{{> nav }}
<main><h1>{{ page.title }}</h1>
<ul>{{#each page.entries}}<li><a href="{{ item.url }}">{{ item.title }}</a></li>{{/each}}</ul>
</main>
{{> footer }}
</body>
</html>
"""

PARTIALS = {
    "head": """<head>
<meta charset="utf-8">
<title>{{ page.title }} — {{ site.title }}</title>
<meta name="description" content="{{ extra.summary }}">
<meta name="generator" content="{{ generator }}">
<link rel="stylesheet" href="/static/style.css">
</head>""",
    "nav": """<nav class="sidebar">
{{#each navigation}}<section><h2>{{ item.name }}</h2><ul>{{#each item.pages}}<li><a href="{{ item.url }}">{{ item.title }}</a></li>{{/each}}</ul></section>
{{/each}}</nav>""",
    "toc": """{{#if toc}}<nav class="toc"><h2>On this page</h2><ul>
{{#each toc}}<li class="toc-{{ item.indent }}"><a href="{{ item.href }}">{{{ item.text }}}</a></li>
{{/each}}</ul></nav>{{/if}}""",
    "footer": """<footer><p>{{ site.title }} · built with {{ generator }}</p></footer>""",
}

STYLE = "body{font-family:sans-serif;display:flex}nav.sidebar{width:16rem}.toc-1{margin-left:1rem}\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--title", default="Tide documentation")
    parser.add_argument("--repeat", type=int, default=2, help="pages per entry in SECTIONS")
    args = parser.parse_args()
    rng = random.Random(args.seed)
    out = args.out
    os.makedirs(os.path.join(out, "content"), exist_ok=True)
    with open(os.path.join(out, "site.ini"), "w") as f:
        f.write(SITE_INI.format(title=args.title, plugins=PLUGINS))
    for section, titles in SECTIONS.items():
        os.makedirs(os.path.join(out, "content", section), exist_ok=True)
        for rep in range(args.repeat):
            for i, title in enumerate(titles):
                full = title if rep == 0 else f"{title} ({['advanced', 'examples', 'internals'][rep - 1]})"
                slug = full.lower().replace(" ", "-").replace("(", "").replace(")", "")
                with open(os.path.join(out, "content", section, slug + ".md"), "w") as f:
                    f.write(page_text(rng, full, (i + 1) * 10 + rep, section))
        with open(os.path.join(out, "content", section, "index.md"), "w") as f:
            f.write(page_text(rng, section.replace("-", " ").capitalize(), 0, section))
    with open(os.path.join(out, "content", "index.md"), "w") as f:
        f.write("---\ntitle: Tide documentation\n---\n# Tide documentation\n\n" + paragraph(rng) + "\n\n## Where to start\n\n" + paragraph(rng) + "\n\n## Getting help\n\n" + paragraph(rng) + "\n")
    os.makedirs(os.path.join(out, "templates", "partials"), exist_ok=True)
    with open(os.path.join(out, "templates", "page.html"), "w") as f:
        f.write(PAGE_HTML)
    with open(os.path.join(out, "templates", "tag.html"), "w") as f:
        f.write(TAG_HTML)
    for name, text in PARTIALS.items():
        with open(os.path.join(out, "templates", "partials", name + ".html"), "w") as f:
            f.write(text + "\n")
    os.makedirs(os.path.join(out, "static"), exist_ok=True)
    with open(os.path.join(out, "static", "style.css"), "w") as f:
        f.write(STYLE)


if __name__ == "__main__":
    main()
