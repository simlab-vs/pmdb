# Table of contents links on the docs site sometimes don't work

Our nightly docs job runs, from the repository root:

```
python3 build.py site --out public
```

and publishes `public/` (Python 3.14, same machine every night).

Twice this month (the builds published on Sep 14 and Sep 27) the "On this page"
box on the docs pages was broken: clicking an entry didn't scroll to the
section. Looking at the published HTML, every entry was `<a href="#">…</a>`
instead of `<a href="#troubleshooting">…</a>` and so on. As far as I can tell it
was every page that has an "On this page" box; the rest of the pages, the
sidebar and the search looked normal, and the job log was the usual three lines
with no warnings:

```
INFO quill.plugins: loaded 13 plugins
INFO quill.content: loaded 91 pages from /srv/docs-nightly/site/content
INFO quill.builder: built 91 pages, 7 tag pages, 507 search entries in 0.5s
```

Both times the following night's build was fine again, with no change to the
site or to quill in between. I've built the site locally about ten times and
haven't been able to reproduce it.

Expected: the table of contents entries link to their sections, as they do
in every other build.
