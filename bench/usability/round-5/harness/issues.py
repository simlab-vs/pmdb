"""Fetches the GitHub issues closed by each bug's fix, and keeps the bugs that close at least one.

For each bug of round 4's `data/bugs.jsonl`, the number of the fix's pull request is read from the
commit message (the last `(#123)`, or `Merge pull request #123`). The pull request's
`closingIssuesReferences` (GitHub's GraphQL API, through `gh api graphql`) are the issues it closes.
Each closing issue's number, repository, title and body are recorded, without comments or authors.

Writes `data/issues.jsonl` (one record per bug of round 4, with its PR and closing issues) and
`data/bugs.jsonl` (the bugs of round 4 that close at least one issue, unchanged).

Usage: python3 issues.py
"""

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROUND4 = ROOT.parent / "round-4"

QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      number
      title
      merged
      closingIssuesReferences(first: 20) {
        nodes { number title body url repository { nameWithOwner } }
      }
    }
  }
}
"""


def pr_number(message):
  first = message.splitlines()[0] if message else ""
  m = re.search(r"Merge pull request #(\d+)", first)
  if m:
    return int(m.group(1))
  found = re.findall(r"\(#(\d+)\)", first) or re.findall(r"\(#(\d+)\)", message or "")
  return int(found[-1]) if found else None


def closing_issues(repo, number):
  owner, name = repo.split("/")
  r = subprocess.run(["gh", "api", "graphql", "-f", f"query={QUERY}", "-f", f"owner={owner}",
                      "-f", f"name={name}", "-F", f"number={number}"],
                     capture_output=True, text=True)
  if r.returncode:
    return None, r.stderr.strip()[-500:]
  pr = json.loads(r.stdout)["data"]["repository"]["pullRequest"]
  if pr is None:
    return None, "no such pull request"
  issues = [{"number": n["number"], "repository": n["repository"]["nameWithOwner"],
             "url": n["url"], "title": n["title"], "body": n["body"] or ""}
            for n in pr["closingIssuesReferences"]["nodes"]]
  return {"pr_title": pr["title"], "merged": pr["merged"],
          "issues": sorted(issues, key=lambda i: i["number"])}, None


def main():
  mined = [json.loads(l) for l in (ROUND4 / "data" / "bugs.jsonl").read_text().splitlines()
           if l.strip()]
  records, kept = [], []
  for bug in mined:
    number = pr_number(bug["message"])
    record = {"id": bug["id"], "repo": bug["repo"], "pr": number, "issues": [], "error": None}
    if number is None:
      record["error"] = "no pull request number in the commit message"
    else:
      data, error = closing_issues(bug["repo"], number)
      record["error"] = error
      if data:
        record.update(data)
    records.append(record)
    if record["issues"]:
      kept.append(bug)
    print(f"{bug['id']}: PR #{number}, closes {[i['number'] for i in record['issues']]}"
          + (f" ({record['error']})" if record["error"] else ""), flush=True)
  (ROOT / "data").mkdir(exist_ok=True)
  (ROOT / "data" / "issues.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
  (ROOT / "data" / "bugs.jsonl").write_text("".join(json.dumps(b) + "\n" for b in kept))
  print(f"{len(kept)} of {len(mined)} bugs close at least one issue")


if __name__ == "__main__":
  main()
