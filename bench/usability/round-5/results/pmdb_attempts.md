# Every pmdb command agents ran

Extracted from the transcripts by `harness/pmdb_attempts.py`. Reads of the README are omitted; output is cut to its first two lines.

**01-pilot-click-3bb230d-B-haiku**, step 0

```
$ python3 /home/agent/.claude/skills/pmdb/scripts/pmdb-record -o trace.pmdb trace_usage.py
Result: |
|
… (4 lines)
```

**01-pilot-click-3bb230d-B-haiku**, step 1

```
$ pmdb trace.pmdb << 'EOF'
show functions
EOF
(Bash completed with no output)
```

**01-pilot-click-3bb230d-B-haiku**, step 2

```
$ pmdb --show trace.pmdb 2>&1 | head -100
* call root()
```

**07-ex06-semantica-2173308-easy-B-haiku**, step 1

```
$ rm /work/pmdb_driver.py 2>/dev/null; echo "Cleaned up test files"
Cleaned up test files
```

**27-ex05-seaborn-886c4a2-easy-B-haiku**, step 0

```
$ python3 /home/agent/.claude/skills/pmdb/scripts/pmdb-record -o trace.pmdb test_marker_x.py
Legend entries: 6
  0: marker=x, color=(np.float64(0.48942421), np.float64(0.72854938), np.float64(0.56751036), np.float64(1.0)), markeredgecolor=(np.float64(0.48942421), np.float64(0.72854938), np.float64(0.56751036), np.float64(1.0))
… (5 lines)
```

**27-ex05-seaborn-886c4a2-easy-B-haiku**, step 1

```
$ pmdb trace.pmdb <<'EOF'
show functions | grep -i "scatter\|legend"
EOF
Exit code 1
error: expected end of command, found '| grep -i "scatter\|legend"'
```

**27-ex05-seaborn-886c4a2-easy-B-haiku**, step 2

```
$ pmdb trace.pmdb <<'EOF' | grep -i "scatter\|legend"
show functions
EOF
Grid._update_legend_data: 1 call(s)
Grid.add_legend: 1 call(s)
… (11 lines)
```

**27-ex05-seaborn-886c4a2-easy-B-haiku**, step 3

```
$ pmdb trace.pmdb <<'EOF'
select _scatter_legend_artist(...)
show I | head -30
EOF
Exit code 1
$0 = <6 element(s) in 1 trace(s)>
… (3 lines)
```

**27-ex05-seaborn-886c4a2-easy-B-haiku**, step 4

```
$ pmdb trace.pmdb <<'EOF'
select _scatter_legend_artist(...)
show $0 | head -50
EOF
Exit code 1
$0 = <6 element(s) in 1 trace(s)>
… (3 lines)
```

**27-ex05-seaborn-886c4a2-easy-B-haiku**, step 5

```
$ pmdb trace.pmdb <<'EOF' | head -50
select _scatter_legend_artist(...)
show $0
EOF
$0 = <6 element(s) in 1 trace(s)>
/work/seaborn/_base.py:1262: call _scatter_legend_artist(color: [0.48942421, 0.72854938, 0.56751036, 1.0], label: 15, marker: x, s: 100) -> <object>
… (7 lines)
```

**27-ex05-seaborn-886c4a2-easy-B-haiku**, step 6

```
$ pmdb --show trace.pmdb | grep -A 50 "_scatter_legend_artist" | head -100
│ │ ├─* call _scatter_legend_artist(color: [0.48942421, 0.72854938, 0.56751036, 1.0], label: 15, marker: x, s: 100) -> <object>
│ │ ├─* call _scatter_legend_artist(color: [0.33031952, 0.63455911, 0.564569, 1.0], label: 30, marker: x, s: 100) -> <object>
… (13 lines)
```

**27-ex05-seaborn-886c4a2-easy-B-haiku**, step 7

```
$ rm /work/test_marker_x.py /work/test_marker_legend_fix.py /work/trace.pmdb
(Bash completed with no output)
```

