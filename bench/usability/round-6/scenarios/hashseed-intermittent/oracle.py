#!/usr/bin/env python3
"""Grade a fix of the hashseed-intermittent scenario.

Usage: python3 oracle.py AGENT_WORK_DIR

Builds three sites with the agent's quill under several PYTHONHASHSEED values
and compares every output file with the output of the reference fix:

* the scenario's own site (pristine copy), including the failing run's seed;
* hidden/site-b: site plugins whose manifests name a single plugin in
  ``after`` / ``before``, where an alphabetical tie-break gives the wrong order;
* hidden/site-c: a subset of the built-in plugins.

Exit status 0 and "PASS" iff every build matches.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FAILING_SEED = 316
SEEDS = {
    "site": [FAILING_SEED, 39, 0, 1, 2, 3],
    "site-b": list(range(10)),
    "site-c": list(range(10)),
}
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "public", "report.pmdb", ".git")


def tree_digest(directory):
    digest = {}
    for root, dirs, files in os.walk(directory):
        dirs.sort()
        for name in sorted(files):
            path = os.path.join(root, name)
            with open(path, "rb") as handle:
                digest[os.path.relpath(path, directory)] = hashlib.sha256(handle.read()).hexdigest()
    return digest


def build(program, site, out, seed):
    env = dict(os.environ, PYTHONHASHSEED=str(seed), PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPATH", None)
    shutil.rmtree(out, ignore_errors=True)
    result = subprocess.run([sys.executable, "build.py", site, "--out", out], cwd=program, env=env,
                            capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        return None, result.stderr[-500:]
    return tree_digest(out), ""


def describe(expected, actual):
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    changed = sorted(k for k in set(expected) & set(actual) if expected[k] != actual[k])
    parts = []
    if missing:
        parts.append(f"{len(missing)} missing (e.g. {missing[0]})")
    if extra:
        parts.append(f"{len(extra)} unexpected (e.g. {extra[0]})")
    if changed:
        parts.append(f"{len(changed)} differ (e.g. {changed[0]})")
    return ", ".join(parts)


def main():
    if len(sys.argv) != 2:
        print("usage: oracle.py AGENT_WORK_DIR", file=sys.stderr)
        return 2
    agent_dir = os.path.abspath(sys.argv[1])
    with tempfile.TemporaryDirectory(prefix="oracle-hashseed-") as tmp:
        agent = os.path.join(tmp, "agent")
        reference = os.path.join(tmp, "reference")
        shutil.copytree(agent_dir, agent, ignore=IGNORE)
        shutil.copytree(os.path.join(HERE, "work"), reference, ignore=IGNORE)
        with open(os.path.join(HERE, "fix.patch")) as patch:
            subprocess.run(["patch", "-s", "-p1", "-d", reference], stdin=patch, check=True)
        sites = {
            "site": os.path.join(tmp, "site"),
            "site-b": os.path.join(tmp, "site-b"),
            "site-c": os.path.join(tmp, "site-c"),
        }
        shutil.copytree(os.path.join(HERE, "work", "site"), sites["site"])
        shutil.copytree(os.path.join(HERE, "hidden", "site-b"), sites["site-b"])
        shutil.copytree(os.path.join(HERE, "hidden", "site-c"), sites["site-c"])
        failures = []
        for name, site in sites.items():
            expected, error = build(reference, site, os.path.join(tmp, "out-ref"), 0)
            if expected is None:
                print(f"FAIL: reference build of {name} failed: {error}")
                return 1
            for seed in SEEDS[name]:
                actual, error = build(agent, site, os.path.join(tmp, "out-agent"), seed)
                if actual is None:
                    failures.append(f"{name} seed {seed}: build failed: {error.strip().splitlines()[-1] if error.strip() else '?'}")
                elif actual != expected:
                    failures.append(f"{name} seed {seed}: {describe(expected, actual)}")
        if failures:
            print(f"FAIL: {len(failures)} of {sum(map(len, SEEDS.values()))} builds differ from the reference")
            for line in failures[:8]:
                print("  " + line)
            return 1
        print(f"PASS: {sum(map(len, SEEDS.values()))} builds match the reference")
        return 0


if __name__ == "__main__":
    sys.exit(main())
