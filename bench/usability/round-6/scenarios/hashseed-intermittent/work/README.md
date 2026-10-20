# quill

quill builds the Tide documentation site (`site/`) from Markdown into static
HTML. It needs only Python 3.11 or later.

```
python3 build.py site --out public
```

`public/` then holds one `index.html` per page, `search.json` (the search
index used by the site's search box), `sitemap.xml`, one listing page per tag
under `tags/`, and the static files.

Add `-v` to log debugging information.

## Site layout

```
site/
  site.ini          site settings, enabled plugins and plugin options
  content/          Markdown pages; directories are sections
  templates/        page.html, tag.html and partials/
  static/           copied as is
  plugins/          site plugins (optional)
```

Pages may start with front matter:

```
---
title: Replication
weight: 20
tags: cluster, storage
summary: How replicas catch up.
---
```

`weight` orders the pages of a section in the sidebar; `draft: true` skips a
page; `template` selects another template than `page`; `search: false` keeps a
page out of the search index.

## Plugins

Each page goes through the plugins enabled in `[build] plugins` of
`site.ini`, in an order that respects their declared constraints, and is
then rendered with its template. Built-in plugins live in `quill/plugins/`:

| plugin | does |
|---|---|
| abbr | wraps abbreviations (`[plugin:abbr]`, front matter `abbr`) in `<abbr>` |
| editlink | "Edit this page" link (`[plugin:editlink]`) |
| excerpt | page summary for `<meta name="description">` |
| extlinks | marks external links and lists them |
| footnotes | `[^1]` footnotes, collected in a Notes section |
| heading-ids | gives headings unique ids for links |
| headingshift | makes the body start at `<h2>` |
| highlight | highlights `python` and `sh` code blocks |
| readingtime | "N min read" |
| search | search index entries, per section |
| smartypants | curly quotes, dashes and ellipses |
| tags | normalizes `tags` |
| toc | the "On this page" table of contents (`[plugin:toc]`) |

A plugin is a module with a manifest next to it:

```
[plugin]
name = search
entry = index_page
after = heading-ids, excerpt
```

`entry` is the function called as `entry(page, site)` for each page.
`after` and `before` name the plugins it must run after or before, separated
by commas; plugins that aren't enabled are ignored there. A site can add its
own plugins, or replace built-in ones, by putting a module and a manifest in
`site/plugins/`.

## Development

The code has no dependencies outside the standard library. `quill/markdown.py`
implements the subset of Markdown the docs use: headings, paragraphs, lists,
fenced code, block quotes, rules, emphasis, code spans, links and images.
