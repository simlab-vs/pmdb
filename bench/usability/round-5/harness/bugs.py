"""The exercise layer of round 5: round 4's mined bugs whose fix closes a GitHub issue.

The bugs are those of `data/bugs.jsonl` (written by `issues.py`); their trees, environments and
clones are round 4's (`../round-4/_work`), used read-only (environments and trees are copied with
reflinks). A bug is materialized in a root directory holding `work`, `env`, `home` and `etc`, in
one of two views:
- the agent's view (`tests=False`): `work` is the project at the PARENT commit, without `.git`,
  caches and build artifacts; every file changed by the fix, tests included, is at its parent
  version, so the fix's tests are hidden;
- the grading view (`tests=True`): the same with the fix commit's versions of the changed test
  files (the official tests).
`env` is a copy of the bug's virtual environment, in which the editable install of the project
points at `/work`. It is mounted read-only at `/opt/env`.
"""

import ast
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import _lib  # noqa: F401  (makes `pmdbbench` importable)
import offline
from pmdbbench import sandbox

ROOT = Path(__file__).resolve().parent.parent
ROUND4 = ROOT.parent / "round-4"
WORK = ROOT / "_work"
TMP = WORK / "tmp"  # temporary roots, on the same file system as round 4's envs for reflinks
OPT = WORK / "opt-pmdb"
SKILL = WORK / "skill"
PMDB = OPT / "bin" / "pmdb"
SKILL_IN_SANDBOX = "/home/agent/.claude/skills/pmdb"
ENV_IN_SANDBOX = "/opt/env"
# Tests of some projects need git (pipx's fixtures, camel's worktree toolkit), which was on PATH
# when the bugs were mined; the sandbox's tools don't include it.
EXTRA_TOOL_DIRS = [sandbox.store_dir("git")]
TEST_TIMEOUT = 600
RECORD_TIMEOUT = 600

# Removed from the copy of the tree wherever they are.
CACHE_NAMES = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
               ".hypothesis", ".tox", ".nox", ".pipx_tests"}
# Removed from the copy of the tree at its top level only (build artifacts and test reports).
TOP_LEVEL_ARTIFACTS = {"build", "dist", ".eggs", ".reports", "htmlcov", ".coverage"}

TESTNAME = re.compile(r"^(test|tests|testing)$", re.I)


def is_test(p):
  """Whether a path is a test file (round 4's `mine.is_test`)."""
  parts = p.split("/")
  base = parts[-1]
  return (any(TESTNAME.match(d) for d in parts[:-1]) or base.startswith("test_")
          or base.endswith("_test.py") or base == "conftest.py")


def load(path):
  """Returns the records of a JSON-lines file, in order."""
  return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def clone(bug):
  return ROUND4 / "_work" / "repos" / bug["repo"].replace("/", "__")


def tree(bug):
  """Round 4's tree of the bug: the project at the fix commit."""
  return ROUND4 / bug["tree"]


def git(bug, *args, check=True):
  r = subprocess.run(["git", "-C", str(clone(bug)), *args], capture_output=True, check=False)
  if check and r.returncode:
    raise RuntimeError(f"git {args} failed: {r.stderr.decode()[-500:]}")
  return r


def parent_version(bug, path):
  """Returns the bytes of `path` at the parent commit, or None if it didn't exist."""
  r = git(bug, "show", f"{bug['parent']}:{path}", check=False)
  return r.stdout if r.returncode == 0 else None


def changed_files(bug):
  """Returns `(status, path)` of every file changed by the fix."""
  out = git(bug, "diff", "--no-renames", "--name-status", bug["parent"], bug["fix"]).stdout.decode()
  return [tuple(l.split("\t", 1)) for l in out.splitlines() if l.strip()]


def hidden_test_files(bug):
  """The test files changed by the fix: at their parent version in the agent's view."""
  return [p for _, p in changed_files(bug) if is_test(p)]


# ---------------------------------------------------------------- issues

def issue_text(record):
  """The issue text an agent gets: the titles and bodies of the issues closed by the fix, in
  issue-number order, without HTML comments (templates' instructions) and without authors."""
  parts = []
  for issue in sorted(record["issues"], key=lambda i: i["number"]):
    body = re.sub(r"<!--.*?-->", "", issue["body"], flags=re.S)
    body = re.sub(r"\n{3,}", "\n\n", body.replace("\r\n", "\n")).strip()
    parts.append(f"{issue['title'].strip()}\n\n{body}".strip())
  return "\n\n---\n\n".join(parts)


def issues():
  """Returns the issue text of each bug of `data/issues.jsonl`, by bug id."""
  return {r["id"]: issue_text(r) for r in load(ROOT / "data" / "issues.jsonl") if r["issues"]}


# ---------------------------------------------------------------- localization

def _spans(source):
  """Returns `(start, end, qualified name, column, is_class)` of every function and class."""
  spans = []

  def visit(node, prefix):
    for child in ast.iter_child_nodes(node):
      if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        start = min([child.lineno] + [d.lineno for d in child.decorator_list])
        name = prefix + child.name
        spans.append((start, child.end_lineno, name, child.col_offset,
                      isinstance(child, ast.ClassDef)))
        visit(child, name + ".")
      else:
        visit(child, prefix)

  visit(ast.parse(source), "")
  return spans


def _changes(diff):
  """Yields `(path, old line, indentation)` for each change of a unified diff: a removed or
  replaced line (indentation None), or an insertion after an old line (with the indentation of
  its first non-blank inserted line)."""
  path = None
  old = 0
  pending = None  # the old line after which the current insertion was already yielded
  for line in diff.splitlines():
    if line.startswith("--- "):
      continue
    if line.startswith("+++ "):
      path = line[6:] if line.startswith("+++ b/") else None
      continue
    m = re.match(r"@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@", line)
    if m:
      old = int(m.group(1)) - 1  # the last old line seen
      pending = None
      continue
    if path is None or not line:
      continue
    if line[0] == "-":
      old += 1
      yield path, old, None
      pending = None
    elif line[0] == "+":
      text = line[1:]
      if text.strip() and pending != old:
        yield path, old, len(text) - len(text.lstrip())
        pending = old
    elif line[0] == " ":
      old += 1
      pending = None


def fix_functions(bug):
  """Returns the qualified names of the functions and methods, in the parent version of the
  source files, that enclose the lines changed by the fix (round 4's rule).

  A removed or replaced line belongs to the innermost function containing it. An insertion after
  old line k belongs to the innermost function containing line k whose body the inserted code is
  indented into. Lines in a class body outside its methods belong to the class. If no change is
  inside a function or class, the result is `["<module>"]`.
  """
  names = []
  sources = {}
  for path, line, indent in _changes(bug["fix_diff"]):
    if path not in sources:
      text = parent_version(bug, path)
      sources[path] = _spans(text.decode()) if text is not None else []
    containing = [s for s in sources[path] if s[0] <= line <= s[1]]
    if indent is not None:
      containing = [s for s in containing if indent > s[3]]
    if containing:
      name = max(containing, key=lambda s: s[0])[2]
      if name not in names:
        names.append(name)
  return names or ["<module>"]


def localized(claim, functions):
  """Whether a function named in an agent's `RESULT:` claim is one of `functions`, comparing the
  last components of the names. A claim may name several functions, separated by commas, `and`
  or `/`."""
  if not claim:
    return False
  names = re.split(r",|/|\band\b", str(claim.get("function", "")))
  claimed = {n.split("(")[0].strip().split(".")[-1] for n in names}
  return any(f.split(".")[-1] in claimed for f in functions)


# ---------------------------------------------------------------- materialization

def _copy(source, destination):
  subprocess.run(["cp", "-a", "--reflink=auto", str(source), str(destination)], check=True)


def _remove(path):
  if path.is_dir() and not path.is_symlink():
    shutil.rmtree(path)
  else:
    path.unlink()


def _clean_tree(work):
  for p in list(work.iterdir()):
    if p.name in TOP_LEVEL_ARTIFACTS or p.name.endswith(".egg-info"):
      _remove(p)
  for directory, dirs, files in os.walk(work):
    for name in list(dirs):
      if name in CACHE_NAMES or name.endswith(".egg-info"):
        shutil.rmtree(Path(directory) / name)
        dirs.remove(name)
    for name in files:
      if name in CACHE_NAMES:  # a worktree's `.git` is a file
        (Path(directory) / name).unlink()


def write_work(bug, work, tests=False):
  """Writes the project at the parent commit into `work` (which must not exist), with the fix
  commit's test files if `tests`."""
  _copy(tree(bug), work)
  _clean_tree(work)
  for _, path in changed_files(bug):
    if tests and is_test(path):
      continue
    text = parent_version(bug, path)
    target = work / path
    if text is None:
      target.unlink(missing_ok=True)
    else:
      target.parent.mkdir(parents=True, exist_ok=True)
      target.write_bytes(text)


def apply_fix(bug, work):
  """Puts the fix's versions of the source files into `work`."""
  for path in bug["source_files"]:
    source = tree(bug) / path
    if source.exists():
      shutil.copy(source, Path(work) / path)
    else:
      (Path(work) / path).unlink(missing_ok=True)


def host_references(directory):
  """Returns the files under `directory` mentioning round 4's or round 5's directory on the host."""
  r = subprocess.run(["grep", "-rlF", "--binary-files=text", "-e", str(ROUND4), "-e", str(ROOT),
                      str(directory)], capture_output=True, text=True)
  return r.stdout.split()


def write_env(bug, env):
  """Writes the bug's environment, relocated to see the project at /work, into `env`."""
  _copy(ROUND4 / bug["env"], env)
  host_tree = str(tree(bug))
  site = next((env / "lib").glob("python3*/site-packages"))
  for path in host_references(env):
    path = Path(path)
    if path.suffix == ".pyc":
      path.unlink()  # a bytecode cache compiled with the host path of the environment
      continue
    if site not in path.parents:
      continue
    try:
      text = path.read_text()
    except UnicodeDecodeError:
      continue
    path.write_text(text.replace(host_tree, "/work"))
  left = host_references(env)
  if left:
    raise RuntimeError(f"{bug['id']}: files of the environment still mention the host: {left[:10]}")


def materialize(bug, directory, env=True, tests=False):
  """Writes the agent's view of `bug` (or with `tests`, the grading view) into `directory`."""
  directory = Path(directory)
  directory.mkdir(parents=True, exist_ok=True)
  (directory / "home").mkdir(exist_ok=True)
  offline.prepare_etc(directory)
  write_work(bug, directory / "work", tests=tests)
  if env:
    write_env(bug, directory / "env")
  return directory


def install_skill(directory):
  """Installs the assembled skill as a user skill in the root's home, writable like a skill
  installed by a user (so that the root can be deleted)."""
  skill = Path(directory) / "home" / ".claude" / "skills" / "pmdb"
  shutil.copytree(SKILL, skill)
  for p in [skill, *skill.rglob("*")]:
    p.chmod(p.stat().st_mode | 0o200)


def temporary_root():
  TMP.mkdir(parents=True, exist_ok=True)
  return tempfile.TemporaryDirectory(dir=TMP)


# ---------------------------------------------------------------- running

def environment(bug, pmdb=False, env=None):
  path = ([f"{ENV_IN_SANDBOX}/bin"] + (["/opt/pmdb/bin"] if pmdb else []) + sandbox.TOOL_DIRS
          + EXTRA_TOOL_DIRS)
  result = {"PATH": ":".join(path), "LD_LIBRARY_PATH": bug["ld_library_path"]}
  if pmdb:
    result["PYTHONPATH"] = "/opt/pmdb/python"
  result.update(env or {})
  return result


def command(root, argv, bug, pmdb=False, env=None, api=False):
  """Returns the bwrap command line running `argv` in the sandbox of `bug` rooted at `root`.

  It is `offline.command` (no network; the API through the relay if `api`) with the bug's
  environment at /opt/env (first on `PATH`), git, the library path the environment's wheels need,
  and with `pmdb`, /opt/pmdb (pmdb on `PATH`, the recorder on `PYTHONPATH`).
  """
  return offline.command(Path(root), argv, opt=OPT if pmdb else None,
                         env=environment(bug, pmdb, env),
                         binds=[(Path(root) / "env", ENV_IN_SANDBOX)], api=api)


def cli_ids(bug, ids):
  """Returns test ids as given on the command line from /work.

  pytest reports node ids relative to its root directory, which isn't /work when a test
  directory has its own configuration (nltk's `nltk/test/pytest.ini`)."""
  result = []
  for i in ids:
    path, _, rest = i.partition("::")
    if not (tree(bug) / path).exists():
      matches = [t for t in bug["test_files"] if t.endswith("/" + path)]
      if len(matches) == 1:
        path = matches[0]
    result.append(path + ("::" + rest if rest else ""))
  return result


def shell_ids(bug, ids):
  return " ".join(shlex.quote(i) for i in cli_ids(bug, ids))


# pytest's cache goes to /tmp: disabling the cache plugin would break projects whose configuration
# sets `cache_dir` with `--strict-config` (beets).
PYTEST_ARGS = ["-p", "no:randomly", "-q", "-o", "cache_dir=/tmp/pytest-cache"]
MARKER = "@@pmdb-bench-reports@@"
RUNNER = r"""
import json, os, sys
import pytest
reports = []
class Reporter:
  def pytest_runtest_logreport(self, report):
    reports.append({"nodeid": report.nodeid, "when": report.when, "outcome": report.outcome})
  def pytest_collectreport(self, report):
    if report.failed:
      reports.append({"nodeid": report.nodeid, "when": "collect", "outcome": "error"})
code = pytest.main(sys.argv[1:], plugins=[Reporter()])
sys.stdout.flush()
os.write(1, ("\n" + MARKER + "\n" + json.dumps(reports) + "\n").encode())
sys.exit(int(code))
""".replace("MARKER", repr(MARKER))


def outcomes(reports):
  """Returns each test's outcome: `failed` if any phase failed, else `skipped` if skipped, else
  `passed`. Collection errors are listed under their collector's node id."""
  result = {}
  for r in reports:
    current = result.get(r["nodeid"])
    if r["outcome"] in ("failed", "error"):
      result[r["nodeid"]] = "failed"
    elif r["outcome"] == "skipped" and current != "failed":
      result[r["nodeid"]] = "skipped"
    elif r["outcome"] == "passed" and current is None:
      result[r["nodeid"]] = "passed"
  return result


def run_tests(root, bug, test_ids, timeout=TEST_TIMEOUT):
  """Runs pytest on `test_ids` (given as on the command line from /work) in the sandbox, offline.

  Nothing is written in /work by the harness: bytecode is disabled, pytest's cache is in /tmp, and
  outcomes are collected by a plugin (the tests themselves may write there; beets writes a JUnit
  report to .reports/). Returns the counts, per-test outcomes and pytest's output.
  """
  argv = ["python", "-c", RUNNER, *PYTEST_ARGS, *test_ids]
  started = time.time()
  try:
    r = subprocess.run(command(root, argv, bug, env={"PYTHONDONTWRITEBYTECODE": "1"}),
                       stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
    stdout, stderr, returncode = r.stdout, r.stderr, r.returncode
  except subprocess.TimeoutExpired as e:
    stdout = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
    stderr, returncode = "", "timeout"
  seconds = round(time.time() - started, 2)
  output, _, data = stdout.partition("\n" + MARKER + "\n")
  try:
    reports = json.loads(data) if data.strip() else []
  except json.JSONDecodeError:
    reports = []
  per_test = outcomes(reports)
  counts = {k: sum(v == k for v in per_test.values()) for k in ("passed", "failed", "skipped")}
  return {"returncode": returncode, "seconds": seconds, **counts, "outcomes": per_test,
          "output": output, "stderr": stderr[-3000:]}


# ---------------------------------------------------------------- recording (prepare's check (e))

# Run by `pmdb-record` from the directory the project's packages are imported from, so that the
# recorder instruments them; it runs the failing tests as a user would.
DRIVER = """\
import os
import sys

import pytest

os.chdir("/work")
sys.exit(pytest.main({args!r}))
"""
DRIVER_NAME = ".pmdb_driver.py"


def import_root(bug):
  """The directory, relative to /work, from which the project's packages are imported."""
  return "src" if all(p.startswith("src/") for p in bug["source_files"]) else ""


def _paths(directory):
  result = set()
  for d, dirs, files in os.walk(directory):
    for name in dirs + files:
      result.add(os.path.relpath(os.path.join(d, name), directory))
  return result


def record_failing_tests(directory, bug):
  """Records the official failing tests with the skill's `pmdb-record`, offline, in the root
  `directory` (the grading view, with the skill installed), to /work/report.pmdb. Returns a
  summary; `ok` iff the tests ran and failed under the recorder as without it and the trace
  records functions of the project."""
  work = directory / "work"
  before = _paths(work)
  relative = os.path.join(import_root(bug), DRIVER_NAME)
  args = PYTEST_ARGS + cli_ids(bug, bug["failing_tests"])
  (work / relative).write_text(DRIVER.format(args=args))
  try:
    r = subprocess.run(command(directory, [
      "python", f"{SKILL_IN_SANDBOX}/scripts/pmdb-record", "-o", "/work/report.pmdb",
      os.path.join("/work", relative)], bug, pmdb=True, env={"PYTHONDONTWRITEBYTECODE": "1"}),
      stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=RECORD_TIMEOUT)
  finally:
    (work / relative).unlink()
  (directory / "recording.log").write_text(r.stdout + "\n--- stderr\n" + r.stderr)
  if not (work / "report.pmdb").exists():
    return {"ok": False, "error": f"no trace: {r.stderr[-500:]}"}
  added = sorted(_paths(work) - before - {"report.pmdb"})
  shown = subprocess.run([str(PMDB), "--show", "--brief", str(work / "report.pmdb")],
                         capture_output=True, text=True, timeout=300).stdout
  calls = re.findall(r"call ([\w.<>]+)\(", shown)
  names = {c.split(".")[-1] for c in calls}
  failed = re.findall(r"(\d+) failed", r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
  summary = {"pytest_exit": r.returncode, "tests_failed": int(failed[0]) if failed else 0,
             "calls": len(calls), "functions": len(set(calls)),
             "fix_functions_recorded": [f for f in bug["fix_functions"]
                                        if f.split(".")[-1] in names],
             "written_by_tests": added, "size": (work / "report.pmdb").stat().st_size}
  summary["ok"] = (r.returncode == 1 and summary["tests_failed"] == len(bug["failing_tests"])
                   and len(set(calls) - {"root"}) > 0)
  return summary


# ---------------------------------------------------------------- grading

def project_python_files(directory):
  """Yields the relative paths of the Python files of a project directory that aren't tests."""
  for d, dirs, files in os.walk(directory):
    dirs[:] = [x for x in dirs if x not in CACHE_NAMES and not x.endswith(".egg-info")]
    for name in files:
      relative = os.path.relpath(os.path.join(d, name), directory)
      if name.endswith(".py") and not is_test(relative):
        yield relative


def grade(bug, final_dir):
  """Grades the project in `final_dir` on the bug's official tests, offline.

  The Python files of `final_dir` that aren't tests are copied over a fresh grading view (the
  parent's tree with the fix commit's test files), so that tests the agent wrote or changed don't
  count. The bug's test files are run. The result has `reported_ok` (every failing test now
  passes) and `regressions` (how many tests that passed with the fix, `bug["fix_passed"]` as found
  by `prepare.py`, no longer pass).
  """
  final_dir = Path(final_dir)
  with temporary_root() as t:
    root = materialize(bug, Path(t) / "root", tests=True)
    copied = []
    for relative in project_python_files(final_dir):
      source, target = final_dir / relative, root / "work" / relative
      if not target.exists() or target.read_bytes() != source.read_bytes():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, target)
        copied.append(relative)
    result = run_tests(root, bug, bug["test_files"])
  per_test = result["outcomes"]
  still_failing = [t for t in bug["failing_tests"] if per_test.get(t) != "passed"]
  regressed = [t for t in bug.get("fix_passed", []) if per_test.get(t) != "passed"
               and t not in bug["failing_tests"]]
  return {"reported_ok": not still_failing, "regressions": len(regressed),
          "still_failing": still_failing, "regressed_tests": regressed[:50],
          "changed_files": len(copied), "copied": copied[:50], "passed": result["passed"],
          "failed": result["failed"], "skipped": result["skipped"],
          "returncode": result["returncode"], "seconds": result["seconds"]}
