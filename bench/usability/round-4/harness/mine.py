#!/usr/bin/env python3
"""Mechanical miner of real bug fixes for round 4 of the pmdb usability study.

Stages (each resumable; outputs in ../data, scratch in ../_work):
  1. repos    GitHub search -> filter (pure Python, pytest, declared test deps) -> shuffle(SEED)
  2. commits  first-parent fix commits since CUTOFF with small source diffs and test changes
  3. validate install at fix commit, changed tests pass; parent sources -> assertion failures
Selection never looks at the content of a bug, only at the mechanical criteria below.

Run:  nix shell nixpkgs#uv -c python3 harness/mine.py [--stage repos|all]
"""
import argparse
import base64
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path

SEED = 20261002
QUERY = "language:Python stars:300..20000 pushed:>2026-06-01 archived:false fork:false"
SEARCH_PAGES = 3          # 100 per page -> at most 300 repositories
CUTOFF = "2026-03-01"
MSG_RE = re.compile(r"\b(fix|fixes|fixed|bug)\b", re.I)
MAX_SRC_FILES = 2
MAX_SRC_LINES = 15
INSTALL_TIMEOUT = 300
FIX_TEST_TIMEOUT = 300
PARENT_TEST_LIMIT = 60
TARGET_BUGS = 25
MIN_REPOS = 8
MAX_PER_REPO = 4
MAX_COMMITS = 400
MAX_CONSEC_ENV_FAIL = 3   # stop a repo after this many environment failures in a row
ENV_FAILURES = ("install_failed", "install_timeout", "fix_tests_fail", "fix_no_tests_passed",
                "fix_tests_timeout")

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "harness"
DATA = ROOT / "data"
WORK = ROOT / "_work"
LOG = DATA / "mining_log.jsonl"
BUGS = DATA / "bugs.jsonl"
NIX_PY = "/nix/store/lb41b0anx1f98y9y5s9mdv97gjgsq740-python3-3.14.7/bin/python3"

NATIVE_EXT = {".c", ".pyx", ".pxd", ".rs", ".cpp", ".cc", ".cxx", ".cu"}
NATIVE_MARKERS = {"Cargo.toml", "CMakeLists.txt", "meson.build"}
NATIVE_BUILD = re.compile(r"maturin|scikit[-_]build|mesonpy|meson[-_]python|setuptools[-_]rust|"
                          r"cython|pybind11|cffi|nanobind", re.I)
TESTNAME = re.compile(r"^(test|tests|testing)$", re.I)
DEVNAME = re.compile(r"^(dev|develop|development)$", re.I)
IGNORED_DIRS = {"docs", "doc", "examples", "example", ".github", "benchmarks", "benchmark",
                "bench", ".ci", "ci"}
IGNORED_FILES = {"setup.py", "noxfile.py", "conftest.py", "tasks.py", "fabfile.py"}
REQ_TEST_FILES = ["requirements-test.txt", "requirements_test.txt", "requirements-tests.txt",
                  "requirements_tests.txt", "test-requirements.txt", "test_requirements.txt",
                  "tests/requirements.txt", "requirements/test.txt", "requirements/tests.txt",
                  "requirements/testing.txt", "requirements-testing.txt"]
REQ_DEV_FILES = ["requirements-dev.txt", "requirements_dev.txt", "dev-requirements.txt",
                 "requirements/dev.txt", "requirements/development.txt"]


# ---------------------------------------------------------------- utilities

def log(rec):
    rec = {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), **rec}
    with open(LOG, "a") as f:
        f.write(json.dumps(rec) + "\n")


def read_jsonl(p):
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def sh(cmd, cwd=None, timeout=None, env=None, check=True):
    r = subprocess.run(cmd, cwd=cwd, timeout=timeout, env=env, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{cmd!r} failed ({r.returncode}): {r.stderr[-2000:]}")
    return r


def gh_api(path, raw=False, params=None):
    cache = WORK / "gh_cache" / (re.sub(r"[^A-Za-z0-9._-]", "_", path + json.dumps(params or {}))[:200])
    if cache.exists():
        txt = cache.read_text()
        return None if txt == "\0404" else (txt if raw else json.loads(txt))
    cmd = ["gh", "api", "-X", "GET", path]
    for k, v in (params or {}).items():
        cmd += ["-f", f"{k}={v}"]
    if raw:
        cmd += ["-H", "Accept: application/vnd.github.raw"]
    for attempt in range(5):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            break
        if "404" in r.stderr or "Not Found" in r.stderr or "409" in r.stderr:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text("\0404")
            return None
        time.sleep(10 * (attempt + 1))
    else:
        raise RuntimeError(r.stderr)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(r.stdout)
    return r.stdout if raw else json.loads(r.stdout)


def path_parts(p):
    return p.split("/")


def is_test(p):
    parts = path_parts(p)
    base = parts[-1]
    return (any(TESTNAME.match(d) for d in parts[:-1]) or base.startswith("test_")
            or base.endswith("_test.py") or base == "conftest.py")


def is_runnable_test(p):
    base = path_parts(p)[-1]
    return p.endswith(".py") and is_test(p) and (base.startswith("test_") or base.endswith("_test.py"))


def is_source_py(p):
    if not p.endswith(".py") or is_test(p):
        return False
    parts = path_parts(p)
    if any(d.lower() in IGNORED_DIRS for d in parts[:-1]):
        return False
    if len(parts) == 1 and parts[0] in IGNORED_FILES:
        return False
    return True


# ---------------------------------------------------------------- test dependency spec

def poetry_spec(name, v):
    if isinstance(v, dict):
        if "path" in v or "git" in v or "url" in v:
            return None
        extras = f"[{','.join(v['extras'])}]" if v.get("extras") else ""
        v = v.get("version", "*")
        name = name + extras
    if isinstance(v, list):
        return None
    v = str(v).strip()
    if v in ("", "*"):
        return name
    out = []
    for part in v.split(","):
        part = part.strip()
        if part.startswith("^") or part.startswith("~") and not part.startswith("~="):
            out.append(">=" + part.lstrip("^~"))
        elif re.match(r"^\d", part):
            out.append("==" + part)
        else:
            out.append(part)
    return name + ",".join(out)


def test_dep_spec(read):
    """Mechanically derive how to install the project with its test dependencies.

    `read(path)` returns the text of a file at the repository root or None.
    Returns (spec, reason). spec = {"extras": [...], "groups": [...], "reqs": [...],
    "pkgs": [...], "kind": str}; spec is None when nothing is declared.
    """
    pp = read("pyproject.toml")
    data = {}
    if pp:
        try:
            data = tomllib.loads(pp)
        except Exception:
            data = {}
    spec = {"extras": [], "groups": [], "reqs": [], "pkgs": [], "kinds": []}
    groups = data.get("dependency-groups", {}) or {}
    extras = (data.get("project", {}) or {}).get("optional-dependencies", {}) or {}
    poetry = (data.get("tool", {}) or {}).get("poetry", {}) or {}
    pgroups = {k: (v or {}).get("dependencies", {}) for k, v in (poetry.get("group", {}) or {}).items()}
    if poetry.get("dev-dependencies"):
        pgroups.setdefault("dev", poetry["dev-dependencies"])
    pdm = ((data.get("tool", {}) or {}).get("pdm", {}) or {}).get("dev-dependencies", {}) or {}
    hatch = (((data.get("tool", {}) or {}).get("hatch", {}) or {}).get("envs", {}) or {})
    reqfiles_t = [f for f in REQ_TEST_FILES if read(f) is not None]
    reqfiles_d = [f for f in REQ_DEV_FILES if read(f) is not None]

    for rx in (TESTNAME, DEVNAME):     # test-named declarations first, dev-named as fallback
        spec["groups"] = [k for k in groups if rx.match(k)]
        spec["extras"] = [k for k in extras if rx.match(k)]
        pk = [k for k in pgroups if rx.match(k)] + [k for k in pdm if rx.match(k)]
        for k in pk:
            src = pgroups.get(k) if k in pgroups else None
            if src is not None:
                spec["pkgs"] += [s for n, v in src.items() if n.lower() != "python"
                                 for s in [poetry_spec(n, v)] if s]
            if k in pdm:
                spec["pkgs"] += [s for s in pdm[k] if isinstance(s, str) and not s.startswith("-e")]
        hk = [k for k in hatch if rx.match(k) or (rx is TESTNAME and k == "hatch-test")]
        for k in hk:
            spec["pkgs"] += [s for s in (hatch[k] or {}).get("dependencies", []) or []
                             if isinstance(s, str)] + \
                            [s for s in (hatch[k] or {}).get("extra-dependencies", []) or []
                             if isinstance(s, str)]
        spec["reqs"] = reqfiles_t if rx is TESTNAME else reqfiles_d
        if any(spec[k] for k in ("groups", "extras", "pkgs", "reqs")):
            spec["kind"] = "test" if rx is TESTNAME else "dev"
            break
    else:
        return None, "no_test_deps_declared"
    if read("requirements.txt") is not None:
        spec["reqs"].insert(0, "requirements.txt")
    spec.pop("kinds")
    return spec, None


def packaging_info(read):
    pp = read("pyproject.toml")
    if pp is None and read("setup.py") is None:
        return "no_packaging_metadata"
    if pp:
        try:
            data = tomllib.loads(pp)
        except Exception:
            return "bad_pyproject"
        bs = data.get("build-system", {}) or {}
        blob = " ".join([str(bs.get("build-backend", ""))] + [str(x) for x in bs.get("requires", [])])
        if NATIVE_BUILD.search(blob):
            return "compiled_build_backend"
        if "project" not in data and "poetry" not in (data.get("tool") or {}) and read("setup.py") is None:
            return "no_packaging_metadata"
    sp = read("setup.py")
    if sp and (NATIVE_BUILD.search(sp) or "Extension(" in sp):
        return "compiled_build_backend"
    return None


def uses_pytest(read, paths):
    if any(p.split("/")[-1] in ("conftest.py", "pytest.ini") for p in paths):
        return True
    for f in ("pyproject.toml", "setup.cfg", "tox.ini", "requirements-dev.txt") + tuple(REQ_TEST_FILES):
        t = read(f)
        if t and "pytest" in t:
            return True
    return False


# ---------------------------------------------------------------- stage 1: repositories

def stage_repos():
    out = DATA / "repos.jsonl"
    if out.exists():
        return read_jsonl(out)
    items = []
    for page in range(1, SEARCH_PAGES + 1):
        res = gh_api("search/repositories", params={"q": QUERY, "per_page": 100, "page": page})
        items += res["items"]
        if len(res["items"]) < 100:
            break
        time.sleep(4)  # search API: 30 requests/min
    snap = [{"full_name": it["full_name"], "stars": it["stargazers_count"],
             "default_branch": it["default_branch"], "pushed_at": it["pushed_at"],
             "license": (it.get("license") or {}).get("spdx_id"), "html_url": it["html_url"]}
            for it in items]
    with open(DATA / "repos_search.jsonl", "w") as f:
        for s in snap:
            f.write(json.dumps(s) + "\n")
    kept = []
    for s in sorted(snap, key=lambda s: s["full_name"]):
        fn = s["full_name"]
        tree = gh_api(f"repos/{fn}/git/trees/{s['default_branch']}", params={"recursive": "1"})
        if tree is None or tree.get("truncated"):
            log({"kind": "repo", "repo": fn, "status": "rejected",
                 "reason": "tree_unavailable_or_truncated"})
            continue
        paths = [e["path"] for e in tree["tree"] if e["type"] == "blob"]
        pset = set(paths)
        native = [p for p in paths if os.path.splitext(p)[1].lower() in NATIVE_EXT
                  or p.split("/")[-1] in NATIVE_MARKERS]
        if native:
            log({"kind": "repo", "repo": fn, "status": "rejected", "reason": "native_sources",
                 "detail": native[:5]})
            continue

        def read(p, fn=fn, pset=pset):
            if p not in pset:
                return None
            return gh_api(f"repos/{fn}/contents/{p}", raw=True)
        reason = packaging_info(read)
        if reason:
            log({"kind": "repo", "repo": fn, "status": "rejected", "reason": reason})
            continue
        if not uses_pytest(read, paths):
            log({"kind": "repo", "repo": fn, "status": "rejected", "reason": "no_pytest"})
            continue
        spec, reason = test_dep_spec(read)
        if spec is None:
            log({"kind": "repo", "repo": fn, "status": "rejected", "reason": reason})
            continue
        log({"kind": "repo", "repo": fn, "status": "accepted", "test_deps": spec})
        kept.append(s)
    random.Random(SEED).shuffle(kept)
    with open(out, "w") as f:
        for i, s in enumerate(kept):
            f.write(json.dumps({"order": i, **s}) + "\n")
    return read_jsonl(out)


# ---------------------------------------------------------------- stage 2: commits

def clone(repo):
    d = WORK / "repos" / repo["full_name"].replace("/", "__")
    if not (d / ".git").exists() and not (d / "HEAD").exists():
        d.parent.mkdir(parents=True, exist_ok=True)
        sh(["git", "clone", "--filter=blob:none", "--no-checkout", "--single-branch",
            "--branch", repo["default_branch"], f"https://github.com/{repo['full_name']}.git",
            str(d)], timeout=1800)
    return d


def git(d, *args, **kw):
    return sh(["git", "-C", str(d), *args], **kw).stdout


def list_commits(d, branch):
    out = git(d, "log", "--first-parent", f"--since={CUTOFF}T00:00:00Z", f"origin/{branch}",
              "--format=%H%x1f%P%x1f%cI%x1f%aI%x1f%B%x1e")
    res = []
    for rec in out.split("\x1e"):
        rec = rec.strip("\n")
        if not rec:
            continue
        h, parents, cdate, adate, msg = rec.split("\x1f", 4)
        res.append({"fix": h, "parent": parents.split()[0] if parents else None,
                    "committed": cdate, "authored": adate, "message": msg.strip()})
    return res


def classify_commit(d, c):
    if c["parent"] is None:
        return "root_commit", None
    ns = git(d, "diff", "--no-renames", "--name-status", c["parent"], c["fix"])
    files = []
    for line in ns.splitlines():
        st, path = line.split("\t", 1)
        files.append((st[0], path))
    src = [(s, p) for s, p in files if is_source_py(p)]
    tests = [p for s, p in files if s != "D" and is_runnable_test(p)]
    info = {"source_files": [p for _, p in src], "source_status": {p: s for s, p in src},
            "test_files": tests, "all_files": [p for _, p in files]}
    if not src:
        return "no_source_py_change", info
    if len(src) > MAX_SRC_FILES:
        return "too_many_source_files", info
    if not tests:
        return "no_test_file_change", info
    num = git(d, "diff", "--no-renames", "--numstat", c["parent"], c["fix"], "--",
              *[p for _, p in src])
    lines = 0
    for line in num.splitlines():
        a, b, _ = line.split("\t", 2)
        if a == "-":
            return "binary_change", info
        lines += int(a) + int(b)
    info["source_lines_changed"] = lines
    if lines > MAX_SRC_LINES:
        return "too_many_changed_lines", info
    return None, info


# ---------------------------------------------------------------- stage 3: validation

def uv():
    p = shutil.which("uv")
    if not p:
        sys.exit("uv not found: run inside `nix shell nixpkgs#uv`")
    return p


_LDPATH = None


def ld_library_path():
    """manylinux wheels (numpy, ...) need libstdc++/libz, which NixOS doesn't provide globally."""
    global _LDPATH
    if _LDPATH is None:
        out = sh(["nix", "build", "--no-link", "--print-out-paths",
                  "nixpkgs#stdenv.cc.cc.lib", "nixpkgs#zlib"]).stdout.split()
        _LDPATH = ":".join(f"{p}/lib" for p in out)
    return _LDPATH


ENV_PASS = ("PATH", "HOME", "USER", "LOGNAME", "TMPDIR", "SSL_CERT_FILE", "NIX_SSL_CERT_FILE",
            "UV_CACHE_DIR", "XDG_CACHE_HOME")


def build_env():
    """A clean environment (no FORCE_COLOR etc. from the caller's terminal)."""
    env = {k: os.environ[k] for k in ENV_PASS if k in os.environ}
    env["LD_LIBRARY_PATH"] = ld_library_path()
    env.update({"CC": "false", "CXX": "false", "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1",
                "UV_PYTHON_DOWNLOADS": "never", "PIP_NO_INPUT": "1", "LANG": "C.UTF-8",
                "TZ": "UTC"})
    return env


def install_cmd(env_dir, spec, date):
    """Dependencies are resolved as of the fix commit's date (uv --exclude-newer)."""
    py = str(env_dir / "bin" / "python")
    target = "." + (f"[{','.join(spec['extras'])}]" if spec["extras"] else "")
    cmd = ["uv", "pip", "install", "--python", py, "--exclude-newer", date, "-e", target]
    for g in spec["groups"]:
        cmd += ["--group", g]
    for r in spec["reqs"]:
        cmd += ["-r", r]
    cmd += spec["pkgs"] + ["pytest"]
    return cmd


def pytest_cmd(env_dir, tests):
    return [str(env_dir / "bin" / "python"), "-m", "pytest", "-p", "pmine_plugin",
            "-p", "no:randomly", "-q", "--no-header", *tests]


def run_pytest(tree, env_dir, tests, timeout, tag):
    rep = WORK / "reports" / f"{tree.name}.{tag}.jsonl"
    rep.parent.mkdir(parents=True, exist_ok=True)
    rep.unlink(missing_ok=True)
    env = build_env()
    env["PMINE_REPORT"] = str(rep)
    env["PYTHONPATH"] = str(HARNESS)
    env["PATH"] = f"{env_dir.resolve() / 'bin'}:{env.get('PATH', '')}"   # as an activated venv
    env["VIRTUAL_ENV"] = str(env_dir.resolve())
    t0 = time.time()
    try:
        r = subprocess.run(pytest_cmd(env_dir, tests), cwd=tree, env=env, capture_output=True,
                           text=True, timeout=timeout)
        rc, tail = r.returncode, (r.stdout + r.stderr)[-3000:]
    except subprocess.TimeoutExpired:
        rc, tail = "timeout", ""
    dt = time.time() - t0
    recs = read_jsonl(rep) if rep.exists() else []
    return {"rc": rc, "seconds": round(dt, 2), "reports": recs, "tail": tail}


def summarize(run):
    passed = [r["nodeid"] for r in run["reports"] if r["when"] == "call" and r["outcome"] == "passed"]
    skipped = [r["nodeid"] for r in run["reports"] if r["outcome"] == "skipped"]
    failed = [r for r in run["reports"] if r["outcome"] == "failed" and r["when"] == "call"]
    errors = [r for r in run["reports"] if r["outcome"] in ("failed", "error") and r["when"] != "call"]
    return passed, skipped, failed, errors


def last_tree_frame(rec, tree):
    """Innermost traceback frame inside the project tree (skips stdlib/site-packages frames,
    e.g. unittest's assertEqual), relative to the tree."""
    root = tree.resolve()
    for p in reversed(rec.get("exc_paths") or [rec.get("exc_path") or ""]):
        try:
            return str(Path(p).resolve().relative_to(root))
        except ValueError:
            continue
    return None


def is_value_assertion(rec, tree):
    """An AssertionError whose innermost in-project frame is in a test file."""
    if rec.get("exc_type") != "AssertionError":
        return False
    rel = last_tree_frame(rec, tree)
    return rel is not None and is_test(rel)


def source_loc(tree):
    files = git(tree, "ls-files").splitlines()
    n = 0
    for f in files:
        if is_source_py(f):
            try:
                n += sum(1 for l in (tree / f).read_text(errors="replace").splitlines() if l.strip())
            except OSError:
                pass
    return n


def cleanup(bug_id, repo_dir):
    tree = WORK / "trees" / bug_id
    if tree.exists():
        sh(["git", "-C", str(repo_dir), "worktree", "remove", "--force", str(tree)], check=False)
        shutil.rmtree(tree, ignore_errors=True)
    sh(["git", "-C", str(repo_dir), "worktree", "prune"], check=False)
    shutil.rmtree(WORK / "envs" / bug_id, ignore_errors=True)


def validate(repo, d, c, info, bug_id):
    """Returns (reason, record). reason None -> validated."""
    cleanup(bug_id, d)
    tree = WORK / "trees" / bug_id
    env_dir = WORK / "envs" / bug_id
    tree.parent.mkdir(parents=True, exist_ok=True)
    git(d, "worktree", "add", "--detach", str(tree), c["fix"], timeout=1800)

    def read(p):
        f = tree / p
        return f.read_text(errors="replace") if f.is_file() else None
    rec = {}
    spec, reason = test_dep_spec(read)
    if spec is None:
        return reason, rec
    if packaging_info(read):
        return packaging_info(read), rec
    sh([uv(), "venv", "--python", NIX_PY, "--relocatable", "--seed", "--quiet", str(env_dir)], env=build_env())
    cmd = install_cmd(env_dir, spec, c["committed"])
    rec["install_command"] = " ".join(cmd)
    rec["test_deps"] = spec
    cmd[0] = uv()
    try:
        r = subprocess.run(cmd, cwd=tree, env=build_env(), capture_output=True, text=True,
                           timeout=INSTALL_TIMEOUT)
    except subprocess.TimeoutExpired:
        return "install_timeout", rec
    if r.returncode != 0:
        rec["install_error"] = r.stderr[-1500:]
        return "install_failed", rec

    tests = info["test_files"]
    fixrun = run_pytest(tree, env_dir, tests, FIX_TEST_TIMEOUT, "fix")
    passed, skipped, failed, errors = summarize(fixrun)
    rec["fix_run"] = {"rc": fixrun["rc"], "seconds": fixrun["seconds"], "passed": len(passed),
                      "skipped": len(skipped), "failed": len(failed), "errors": len(errors)}
    if fixrun["rc"] == "timeout":
        return "fix_tests_timeout", rec
    if failed or errors:
        rec["fix_failures"] = [f["nodeid"] for f in failed + errors][:20]
        rec["fix_tail"] = fixrun["tail"][-1500:]
        return "fix_tests_fail", rec
    if not passed:
        rec["fix_tail"] = fixrun["tail"][-1500:]
        return "fix_no_tests_passed", rec

    # restore the source files changed by the fix to their parent versions
    for p in info["source_files"]:
        if info["source_status"][p] == "A":
            (tree / p).unlink(missing_ok=True)
        else:
            git(tree, "checkout", c["parent"], "--", p)
    prun = run_pytest(tree, env_dir, tests, PARENT_TEST_LIMIT, "parent")
    git(tree, "checkout", "-f", c["fix"], "--", ".")   # back to the fix state
    passed_p, skipped_p, failed_p, errors_p = summarize(prun)
    rec["parent_run"] = {"rc": prun["rc"], "seconds": prun["seconds"], "passed": len(passed_p),
                         "skipped": len(skipped_p), "failed": len(failed_p), "errors": len(errors_p)}
    if prun["rc"] == "timeout" or prun["seconds"] >= PARENT_TEST_LIMIT:
        return "parent_tests_too_slow", rec
    if errors_p:
        rec["parent_errors"] = [{k: e.get(k) for k in ("nodeid", "when", "exc_type", "exc_msg")}
                                for e in errors_p][:10]
        return "parent_errors", rec
    if not failed_p:
        return "parent_tests_pass", rec
    bad = [f for f in failed_p if not is_value_assertion(f, tree)]
    rec["parent_failures"] = [{"nodeid": f["nodeid"], "exc_type": f.get("exc_type"),
                               "exc_frame": last_tree_frame(f, tree)}
                              for f in failed_p]
    if bad:
        return "parent_non_assertion_failure", rec
    rec["failing_tests"] = [f["nodeid"] for f in failed_p]
    rec["pytest_command"] = " ".join(["<env>/bin/python", "-m", "pytest", "-p", "no:randomly", "-q", *tests])
    rec["ld_library_path"] = ld_library_path()
    rec["python_version"] = sh([str(env_dir / "bin" / "python"), "--version"]).stdout.strip()
    rec["source_loc"] = source_loc(tree)
    rec["fix_diff"] = git(d, "diff", c["parent"], c["fix"], "--", *info["source_files"])
    rec["test_diff"] = git(d, "diff", c["parent"], c["fix"], "--", *tests)
    return None, rec


# ---------------------------------------------------------------- driver

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["repos", "all"], default="all")
    args = ap.parse_args()
    DATA.mkdir(exist_ok=True)
    WORK.mkdir(exist_ok=True)
    repos = stage_repos()
    print(f"{len(repos)} repositories accepted", flush=True)
    if args.stage == "repos":
        return

    done = {}
    for e in read_jsonl(LOG):
        if e.get("kind") == "commit":
            done[(e["repo"], e["fix"])] = e
    bugs = read_jsonl(BUGS)
    # The MAX_COMMITS budget counts validation attempts: commits that pass the message and
    # diff-shape filters and reach stage 3. Every commit is logged either way.
    considered = sum(1 for e in done.values() if e.get("validated_attempt"))
    per_repo = {}
    for b in bugs:
        per_repo[b["repo"]] = per_repo.get(b["repo"], 0) + 1

    def finished():
        return (len(bugs) >= TARGET_BUGS and len(per_repo) >= MIN_REPOS) or considered >= MAX_COMMITS

    visited = {e["repo"] for e in read_jsonl(LOG) if e.get("kind") == "repo_visit"}
    for repo in repos:
        if finished():
            break
        fn = repo["full_name"]
        try:
            d = clone(repo)
            commits = list_commits(d, repo["default_branch"])
        except Exception as ex:
            if fn not in visited:
                log({"kind": "repo_visit", "repo": fn, "status": "clone_failed", "error": str(ex)[-500:]})
            continue
        matching = [c for c in commits if MSG_RE.search(c["message"])]
        if fn not in visited:
            log({"kind": "repo_visit", "repo": fn, "commits_since_cutoff": len(commits),
                 "message_matches": len(matching)})
        print(f"== {fn}: {len(commits)} commits, {len(matching)} match", flush=True)
        consec_env_fail = 0
        for i, c in enumerate(matching):
            if finished():
                break
            if per_repo.get(fn, 0) >= MAX_PER_REPO or consec_env_fail >= MAX_CONSEC_ENV_FAIL:
                why = "repo_cap" if per_repo.get(fn, 0) >= MAX_PER_REPO else "repo_env_failures"
                if not any(e.get("kind") == "repo_stop" and e["repo"] == fn for e in read_jsonl(LOG)):
                    log({"kind": "repo_stop", "repo": fn, "reason": why,
                         "unexamined_commits": len(matching) - i})
                break
            key = (fn, c["fix"])
            if key in done:
                r = done[key].get("reason")
                if r in ENV_FAILURES:
                    consec_env_fail += 1
                elif done[key].get("validated_attempt") and r != "harness_error":
                    consec_env_fail = 0
                continue
            bug_id = f"{fn.split('/')[1]}-{c['fix'][:7]}"
            base = {"kind": "commit", "repo": fn, "fix": c["fix"], "parent": c["parent"],
                    "bug_id": bug_id, "committed": c["committed"]}
            try:
                reason, info = classify_commit(d, c)
            except Exception as ex:
                log({**base, "status": "rejected", "reason": "git_error", "error": str(ex)[-500:]})
                continue
            if reason:
                log({**base, "status": "rejected", "reason": reason,
                     **({"source_files": info["source_files"], "test_files": info["test_files"]}
                        if info else {})})
                continue
            considered += 1
            base["validated_attempt"] = True
            print(f"  [{considered}] validating {bug_id}", flush=True)
            try:
                reason, rec = validate(repo, d, c, info, bug_id)
            except Exception as ex:
                reason, rec = "harness_error", {"error": str(ex)[-1500:]}
            if reason in ENV_FAILURES:
                consec_env_fail += 1
            elif reason != "harness_error":
                consec_env_fail = 0
            if reason:
                cleanup(bug_id, d)
                log({**base, "status": "rejected", "reason": reason, **info, **rec})
                print(f"    rejected: {reason}", flush=True)
                continue
            bug = {"id": bug_id, "repo": fn, "url": repo["html_url"], "license": repo["license"],
                   "stars": repo["stars"], "parent": c["parent"], "fix": c["fix"],
                   "committed": c["committed"], "authored": c["authored"], "message": c["message"],
                   "source_files": info["source_files"], "test_files": info["test_files"],
                   "source_lines_changed": info["source_lines_changed"],
                   "n_failing_tests": len(rec["failing_tests"]),
                   "tree": str((WORK / "trees" / bug_id).relative_to(ROOT)),
                   "env": str((WORK / "envs" / bug_id).relative_to(ROOT)), **rec}
            with open(BUGS, "a") as f:
                f.write(json.dumps(bug) + "\n")
            bugs.append(bug)
            per_repo[fn] = per_repo.get(fn, 0) + 1
            log({**base, "status": "validated", "failing_tests": rec["failing_tests"],
                 "fix_run": rec["fix_run"], "parent_run": rec["parent_run"]})
            print(f"    VALIDATED ({len(bugs)} total)", flush=True)
    print(f"done: {len(bugs)} bugs from {len(per_repo)} repos, {considered} commits considered",
          flush=True)


if __name__ == "__main__":
    main()
