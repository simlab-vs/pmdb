# Scenario: hashseed-intermittent (kind 5: intermittent failure)

## The program and the failing run

`work/` is **quill**, a small static site generator (about 1,200 lines of Python in 22 modules),
plus the site it builds: `site/` holds 91 Markdown pages of a fictional product's documentation,
templates and `site.ini`.

- **Pipeline.** Each page is parsed into a list of block dicts, goes through 13 plugins, and is
  rendered with a template.
- **Plugins.** Each plugin is a module in `quill/plugins/` with an INI manifest declaring
  `after` / `before` constraints. `order_plugins` sorts the plugins topologically with Kahn's
  algorithm. Its ready queue is a `set` of plugin names, consumed with `set.pop()`, so the order
  among unconstrained plugins depends on string hashing, and therefore on `PYTHONHASHSEED`.

The nightly job ran `python3 build.py site --out public` with a random hash seed. The recorded
failing run uses `PYTHONHASHSEED=316`; the agent isn't told the seed.

**Symptom (issue.md).** Twice in a month, the "On this page" table of contents (TOC) of every page
linked to `href="#"` instead of the sections; the next night's build was fine. The job log shows
nothing unusual.

## The bug

`toc.ini` declares `after = heading-ids`, a single name.

1. `config.parse_value` returns a list only when the value contains a comma, so a single name
   stays a string.
2. `load_manifest` converts each manifest value with its `PluginSpec` field type:
   `PluginSpec.__annotations__[key](value)`. For `after: tuple`, that's
   `tuple("heading-ids")`, which gives the characters `('h', 'e', 'a', …)`.
3. `dependency_graph` silently ignores names that aren't enabled plugins, by design: the docs
   say constraints may name plugins that aren't enabled. So every character is dropped and the
   constraint is lost.

toc and heading-ids are then ordered only by the other plugins' constraints. In 38 of 500 seeds
(0..499, 7.6%), `set.pop()` yields toc before heading-ids:

- toc then builds its entries from headings whose `id` is still `None`, so every href is `#`;
- in every other seed, heading-ids happens to run first and the output is correct;
- the first failing seed is 39, so `PYTHONHASHSEED=0..38` all build correctly.

**Fix (fix.patch).** In `load_manifest`, pass `after` and `before` through `config.as_list`,
which already turns a single value into a one-element list. Equivalent fixes pass, e.g. wrapping
`str` values for tuple fields.

## Why the faulty code looks plausible

- `PluginSpec.__annotations__[key](value)` is a generic "coerce manifest values to the declared
  field types" idiom, and works for every manifest with two or more names.
- `parse_value`'s comma rule is documented and reasonable for `site.ini`. `site.ini` itself uses
  `as_list` correctly, for the plugin list.
- Silently ignoring unknown plugin names is a documented feature.
- The README documents single names (`after` lists names "separated by commas").
- Only toc's manifest has a single name: all other manifests list two or three.

## Why reading alone is hard, and what a reader would suspect first

The symptom points at the TOC, which leads a reader to `toc.py`, `headingids.py`
(`slugify`), the templates (`templates.py`, `partials/toc.html`) and `render.py`. All of them are
correct, and every local build works, so nothing contradicts them.

A reader told the failure is intermittent looks for sources of nondeterminism. There are several
harmless candidates, and one that matters:

- harmless: `set` in `tags.py` (sorted afterwards), sets in `config.py`, in `dependency_graph`
  and in `load_manifest`'s key check, `os.walk` (sorted), `time.perf_counter`;
- the one that matters: the `ready` set in `order_plugins`.

Connecting "TOC without ids" to "plugin order" is natural, but `toc.ini` *does* declare
`after = heading-ids`, so the order looks guaranteed. The reader must then distrust the
constraint machinery and notice that a single-name value reaches `tuple()` as a `str`. That last
step needs reading `parse_value`, `load_manifest` and `dependency_graph` together, with the
`str`-is-iterable pitfall in mind.

**Honest estimate:** a strong reader who suspects plugin ordering can find this in roughly 8 to
15 turns. The chain is
`toc.py` → ids → `toc.ini` → `plugins/__init__.py` → `config.parse_value`. The scenario relies
on that chain not being the first hypothesis, and on the reader being unable to confirm it, since
local builds don't fail.

## How an agent without pmdb would likely proceed

1. **Read the TOC code and build locally.** Builds take about 0.5 s, and the output is correct
   for a random seed 92% of the time.
2. **Realize that hash randomization could matter.** If it does, loop over `PYTHONHASHSEED`
   values and diff the outputs. A sweep from 0 needs 40 builds (about 20 s) to hit seed 39; a
   random-seed loop needs about 13 builds on average. This is cheap once thought of. Then `-v`
   (DEBUG) logs the plugin order, and prints in `order_plugins` / `load_manifest` reveal the
   characters.
3. **If the agent doesn't think of hash seeds,** it may chase templates, slugify or the
   generated site, or "fix" the symptom: make toc compute its own ids, or add a deterministic
   tie-break. The hidden checks catch both: a sorted ready set happens to pass the main site but
   fails site-b; a manifest-only edit fails site-b.

## How pmdb shortens it

The trace *is* the failing run, so no reproduction is needed. `query.pmdb`:

```
select build_toc(page, _) where page.blocks.any(b => b.kind == "heading" && b.id == none)
select order_plugins(specs, enabled) -> order
show $1
select load_manifest(path, _) -> spec where spec.name == "toc"
show $2
```

Output, clipped, with paths shown as /work:

```
$0 = <91 element(s) in 1 trace(s)>
/work/quill/plugins/__init__.py:141: call order_plugins({abbr: {...}, ...}) -> [highlight, abbr,
    smartypants, editlink, extlinks, tags, footnotes, excerpt, headingshift, toc, heading-ids,
    search, readingtime]
/work/quill/plugins/__init__.py:67: call load_manifest(/work/quill/plugins/toc.ini, builtin)
    -> {after: [h, e, a, d, i, n, g, -, i, d, s], before: [], entry: build_toc, name: toc, ...}
```

Three queries take the agent from symptom to cause:

1. toc ran on all 91 pages while their headings had no id.
2. toc ran before heading-ids.
3. toc's `after` was recorded as characters.

A natural first query, `select build_toc(page, _)` and showing one call, already shows the
heading blocks with `id: none`.

## Threats to fairness

- **The hash-seed sweep is a cheap alternative** for an agent that knows about
  `PYTHONHASHSEED`. Reproduction costs about 20 s of builds. pmdb's advantage is then mostly
  that the agent needn't think of hash seeds, and needn't instrument the code to see the order
  and the parsed spec.
- **A strong reader can find it** (see the estimate above). The concealment is moderate, not
  strong.
- **The hidden checks are strict.** The oracle compares every output file with the reference
  fix's output.
  - A fix that edits only `toc.ini`, or only makes the order deterministic, fails, by design:
    hidden site-b brings its own plugins with single-name `after` / `before` (as documented in
    the README).
  - Unrelated output changes, such as reformatting, also fail. Agents should be told not to
    change behaviour beyond the fix, as usual.
- **The trace is larger than the input:** 31 MB and 38.8k observations, because every plugin
  call records the whole page dict. pmdb loads it in about 1 s, but `show` on plugin calls
  prints very long lines (use `clip`).
- **The trace's call-site paths** are `/work/...` when recorded by the harness in `/work`.

## Numbers

| | |
|---|---|
| failing run (no recording) | about 0.5 s |
| recording (`record.sh`) | about 2 s; `report.pmdb` 31 MB, 38,769 observations |
| failure rate of the unfixed build | 38 / 500 seeds (0..499), first failing seed 39; recorded seed 316 |
| oracle | 26 builds; about 7 s |

## Hidden inputs (`hidden/`, generated by `gen/make_hidden.py`)

| site | contents | seeds |
|---|---|---|
| the scenario's site | pristine copy | 316 (the failing run), 39, 0, 1, 2, 3 |
| site-b | site plugins `tagaliases` (`after = tags`) and `lead` (`before = excerpt`); an alphabetical tie-break runs tagaliases before tags | 0..9 |
| site-c | only excerpt, heading-ids, search, tags and toc; the unfixed build fails in about half the seeds | 0..9 |

The expected output is the reference fix's build with seed 0. It is identical for every seed,
which was checked for seeds 0..15 and 39 on all three sites. `work/site` is generated by
`gen/make_site.py`.

## Validation (validate.sh --rate 500)

```
PASS: failing run (seed 316) has broken TOC links on 83 pages; seed 0 has none
PASS: oracle fails the unfixed program          (15 of 26 builds differ)
PASS: fixed program, seed 316: TOC links work and output equals the good build
PASS: oracle passes the fixed program           (26 builds match)
PASS: record.sh writes report.pmdb and leaves no other changes
PASS: query.pmdb output contains every line of query_expect.txt
  unfixed build broken for 38 of 500 seeds
```

**Alternative fixes checked with the oracle:**
- a sorted ready set (`min(ready)`): FAIL (site-b);
- `toc.ini`'s value changed to `heading-ids,`: FAIL (site-b);
- wrapping `str` values for tuple fields: PASS.

83 of the 91 pages have a TOC; the other 8 have fewer than two headings.
