"""
Snapshot GitHub repository traffic (views + clones) into CSVs under traffic/.

GitHub's Insights -> Traffic only retains the last 14 days. This script, run
daily by .github/workflows/traffic.yml, appends each day's counts to
traffic/views.csv and traffic/clones.csv so you keep a permanent history.

Reads GH_TOKEN and GH_REPO ("owner/name") from the environment. The traffic API
requires push access; the Actions GITHUB_TOKEN has it for its own repo.

NOTE: GitHub only exposes AGGREGATE counts (total + unique). It does NOT reveal
the identity of who viewed or cloned. See docs/ANALYTICS.md.
"""
from __future__ import annotations
import csv, json, os, urllib.request

API = "https://api.github.com"


def _get(path: str, token: str) -> dict:
    req = urllib.request.Request(
        f"{API}{path}",
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def _merge(path: str, rows: list[dict], key: str = "date"):
    existing: dict[str, dict] = {}
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing[row[key]] = row
    for row in rows:
        existing[row[key]] = row            # newer snapshot wins per day
    fields = ["date", "count", "uniques"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for d in sorted(existing):
            w.writerow(existing[d])
    return len(existing)


def main():
    token, repo = os.environ["GH_TOKEN"], os.environ["GH_REPO"]
    for kind, filename in (("views", "traffic/views.csv"),
                           ("clones", "traffic/clones.csv")):
        data = _get(f"/repos/{repo}/traffic/{kind}?per=day", token)
        rows = [{"date": p["timestamp"][:10], "count": p["count"],
                 "uniques": p["uniques"]} for p in data.get(kind, [])]
        total = _merge(filename, rows)
        print(f"{kind}: +{len(rows)} snapshot rows, {total} total days -> {filename}")


if __name__ == "__main__":
    main()
