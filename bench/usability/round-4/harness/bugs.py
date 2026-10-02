"""The exercise layer of round 4: real bugs mined by `mine.py` (`data/bugs.jsonl`).

An agent's view of a bug is a root directory holding
- `work`: the project at the fix commit, without `.git` and caches, with every file changed by the
  fix that isn't a test (the source files, but also changelogs and documentation, which would
  describe the fix) restored to its parent version, and the fixed tests kept;
- `env`: a copy of the bug's virtual environment, in which the editable install of the project
  points at `/work` instead of the host's tree. It is mounted read-only at `/opt/env`.
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
import mine
from pmdbbench import sandbox

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "_work"
TMP = WORK / "tmp"  # temporary roots, on the same file system as the envs for reflinks
ENV_IN_SANDBOX = "/opt/env"
# Tests of some projects need git (pipx's fixtures, camel's worktree toolkit), which was on PATH
# when the bugs were mined; the sandbox's tools don't include it.
EXTRA_TOOL_DIRS = [sandbox.store_dir("git")]
TEST_TIMEOUT = 600

# Removed from the copy of the tree wherever they are.
CACHE_NAMES = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
               ".hypothesis", ".tox", ".nox", ".pipx_tests"}
# Removed from the copy of the tree at its top level only (build artifacts and test reports).
TOP_LEVEL_ARTIFACTS = {"build", "dist", ".eggs", ".reports", "htmlcov", ".coverage"}


def load(path):
  """Returns the bugs of a JSON-lines file, in order."""
  return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def clone(bug):
  return WORK / "repos" / bug["repo"].replace("/", "__")


def tree(bug):
  return ROOT / bug["tree"]


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


def restored_files(bug):
  """The files changed by the fix that the agent sees at their parent version."""
  return [p for _, p in changed_files(bug) if not mine.is_test(p)]


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
  source files, that enclose the lines changed by the fix.

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
  last components of the names (as in round 2). A claim may name several functions, separated
  by commas, `and` or `/`."""
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


def write_work(bug, work):
  """Writes the project as the agent sees it into `work` (which must not exist)."""
  _copy(tree(bug), work)
  _clean_tree(work)
  for path in restored_files(bug):
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
  """Returns the files under `directory` mentioning the round's directory on the host."""
  r = subprocess.run(["grep", "-rlF", "--binary-files=text", "-e", str(ROOT), str(directory)],
                     capture_output=True, text=True)
  return r.stdout.split()


def write_env(bug, env):
  """Writes the bug's environment, relocated to see the project at /work, into `env`."""
  _copy(ROOT / bug["env"], env)
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
    raise RuntimeError(f"{bug['id']}: files of the environment still mention {ROOT}: {left[:10]}")


def materialize(bug, directory, env=True):
  """Writes the agent's view of `bug` into `directory` (`work`, `env`, `home` and `etc`)."""
  directory = Path(directory)
  directory.mkdir(parents=True, exist_ok=True)
  (directory / "home").mkdir(exist_ok=True)
  sandbox.prepare_etc(directory)
  write_work(bug, directory / "work")
  if env:
    write_env(bug, directory / "env")
  return directory


def temporary_root():
  TMP.mkdir(parents=True, exist_ok=True)
  return tempfile.TemporaryDirectory(dir=TMP)


# ---------------------------------------------------------------- running

def command(root, argv, bug, opt=None, env=None, network=True):
  """Returns the bwrap command line running `argv` in the sandbox of `bug` rooted at `root`.

  It is the sandbox of `pmdbbench.sandbox` with the bug's environment at /opt/env (first on
  `PATH`), git, the library path the environment's wheels need, the pmdb recorder on `PYTHONPATH` if
  `opt` is given, and no network if `network` is false.
  """
  path = ([f"{ENV_IN_SANDBOX}/bin"] + ([] if opt is None else ["/opt/pmdb/bin"]) + sandbox.TOOL_DIRS
          + EXTRA_TOOL_DIRS)
  environment = {"PATH": ":".join(path), "LD_LIBRARY_PATH": bug["ld_library_path"]}
  if opt is not None:
    environment["PYTHONPATH"] = "/opt/pmdb/python"
  environment.update(env or {})
  args = sandbox.command(Path(root), argv, opt=opt, env=environment)
  separator = args.index("--")
  # bwrap applies its options in order, so `--unshare-net` overrides the earlier `--share-net`.
  extra = ["--ro-bind", str(Path(root) / "env"), ENV_IN_SANDBOX]
  if not network:
    extra.append("--unshare-net")
  return args[:separator] + extra + args[separator:]


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


def run_tests(root, bug, test_ids, network=True, timeout=TEST_TIMEOUT):
  """Runs pytest on `test_ids` (given as on the command line from /work) in the sandbox.

  Nothing is written in /work by the harness: bytecode is disabled, pytest's cache is in /tmp, and
  outcomes are collected by a plugin (the tests themselves may write there; beets writes a JUnit
  report to .reports/). Returns the counts, per-test outcomes and pytest's output.
  """
  argv = ["python", "-c", RUNNER, *PYTEST_ARGS, *test_ids]
  started = time.time()
  try:
    r = subprocess.run(command(root, argv, bug, env={"PYTHONDONTWRITEBYTECODE": "1"},
                               network=network),
                       capture_output=True, text=True, timeout=timeout)
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


# ---------------------------------------------------------------- grading

def project_python_files(directory):
  """Yields the relative paths of the Python files of a project directory that aren't tests."""
  for d, dirs, files in os.walk(directory):
    dirs[:] = [x for x in dirs if x not in CACHE_NAMES and not x.endswith(".egg-info")]
    for name in files:
      relative = os.path.relpath(os.path.join(d, name), directory)
      if name.endswith(".py") and not mine.is_test(relative):
        yield relative


def grade(bug, final_dir, network=False):
  """Grades the project in `final_dir` on the bug's test files.

  The Python files of `final_dir` that aren't tests are copied over a fresh materialization, so
  that changes to the tests don't count. The result has `reported_ok` (every failing test now
  passes) and `regressions` (how many tests that passed at the fix commit, `bug["fix_passed"]`
  as found by `prepare.py`, no longer pass).
  """
  final_dir = Path(final_dir)
  with temporary_root() as t:
    root = materialize(bug, Path(t) / "root")
    copied = 0
    for relative in project_python_files(final_dir):
      source, target = final_dir / relative, root / "work" / relative
      if not target.exists() or target.read_bytes() != source.read_bytes():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, target)
        copied += 1
    result = run_tests(root, bug, bug["test_files"], network=network)
  per_test = result["outcomes"]
  still_failing = [t for t in bug["failing_tests"] if per_test.get(t) != "passed"]
  regressed = [t for t in bug.get("fix_passed", []) if per_test.get(t) != "passed"
               and t not in bug["failing_tests"]]
  return {"reported_ok": not still_failing, "regressions": len(regressed),
          "still_failing": still_failing, "regressed_tests": regressed[:50],
          "changed_files": copied, "passed": result["passed"], "failed": result["failed"],
          "skipped": result["skipped"], "returncode": result["returncode"],
          "seconds": result["seconds"]}


def import_root(bug):
  """The directory, relative to /work, from which the project's packages are imported."""
  return "src" if all(p.startswith("src/") for p in bug["source_files"]) else ""
