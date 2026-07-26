# Repository Analytics — what you can (and cannot) know

Short version: **GitHub does not tell you the identity of people who view or
clone a public repo.** That is by design, for privacy. You *can* get aggregate
counts and the identities of people who explicitly engage (star/fork/watch).
Here is exactly what is available and how this repo captures it.

## 1. Aggregate traffic (anonymous) — views & clones
`Insights -> Traffic` shows, for the **last 14 days only**:
- **Views** — total page views and **unique visitors** (counts, no identities).
- **Clones** — total clones and **unique cloners** (counts, no identities).
- Top referring sites and top content paths.

Because GitHub discards this after 14 days, this repo ships a GitHub Action
(`.github/workflows/traffic.yml` + `scripts/collect_traffic.py`) that snapshots
the numbers **daily into `traffic/views.csv` and `traffic/clones.csv`**, giving
you a permanent history. It needs no secrets — the built-in `GITHUB_TOKEN` has
the required push-level access to the traffic API for its own repo.

> The traffic API still returns only counts + uniques. There is no endpoint,
> anywhere, that returns *who* viewed or cloned.

## 2. Identifiable engagement — stars, forks, watchers
These are public actions, so you *can* see who did them:
- **Stargazers:** `https://github.com/NITS-IIMA/causal-ehr-app/stargazers`
- **Forks:** the "Forks" tab / `GET /repos/{owner}/{repo}/forks`
- **Watchers:** `GET /repos/{owner}/{repo}/subscribers`
API: `GET /repos/NITS-IIMA/causal-ehr-app/stargazers` (add the header
`Accept: application/vnd.github.star+json` to include timestamps).

## 3. Release downloads (aggregate)
If you publish a GitHub **Release** and attach the packaged zip as an asset,
each asset exposes a **`download_count`** — total downloads, **not identities**:
`GET /repos/NITS-IIMA/causal-ehr-app/releases` -> `assets[].download_count`.
Cloning the repo or downloading the source zip does **not** produce per-user records.

## 4. Want actual identities of downloaders?
That is only possible if you **gate the download** behind something that captures
identity — e.g. host the artifact behind a form/email capture, or distribute via
a tracked link or your own site with analytics. For an open-source portfolio repo
this is unusual and tends to deter contributors, so it is not built in here.

Third-party "visitor counter" badges (e.g. a pixel that pings an external service
on README render) can count hits, but they are still anonymous and add an external
tracker to your README — use with care and disclosure.

## Quick reference
| Question | Answerable? | Where |
|---|---|---|
| How many views / unique visitors? | Yes (aggregate, 14 days; longer via the Action) | Insights -> Traffic / `traffic/*.csv` |
| How many clones / unique cloners? | Yes (aggregate) | Insights -> Traffic / `traffic/*.csv` |
| **Who** viewed or cloned? | **No** | not exposed by GitHub |
| Who starred / forked / watched? | Yes (identities) | Stargazers / Forks / Watchers APIs |
| How many release-asset downloads? | Yes (aggregate) | Releases API `download_count` |
| **Who** downloaded? | **No** (unless you gate it yourself) | — |
