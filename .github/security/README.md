# Security scan

`.github/workflows/security-scan.yml` runs these scanners and builds one report:

| Check | Tool |
| --- | --- |
| Secrets in the full git history | gitleaks (`gitleaks.toml`) |
| Vulnerable Python dependencies | pip-audit, OSV-Scanner (both read a requirements list exported from `uv.lock`) |
| Python code patterns | Bandit |
| Code patterns | Semgrep (`p/python`, `p/secrets`, `p/dockerfile` + `semgrep-rules.yml`) |

The project rules in `semgrep-rules.yml` look for the risks specific to this backend:
a wildcard CORS header and all-interfaces bind on the local HTTP server, R code built with
string formatting, `exec`/`eval` of non-constant input, unverified SSH host keys,
hardcoded secrets, Docker ports published on every interface, and unpinned installs in the Dockerfile.

## Running it

- **On demand:** Actions tab → *Security scan* → *Run workflow*, and pick the branch.
- **Automatically:** every Monday at 06:00 UTC, on the branch set in `SCAN_BRANCH` in the workflow (`dev`).

GitHub only shows the *Run workflow* button, and only runs the schedule, once the workflow file is on the repository's **default branch** (`main` here).

Findings never fail the workflow. A failed run means a scanner or the report step broke.

## Reading the report

- The report appears on the run's **Summary** page.
- The `security-report-<branch>` artifact holds `report.md`, `summary.json`, `findings.json` and the raw scanner outputs. Secret values are redacted, and source code is stripped from the raw outputs.
- Each run compares itself with the last successful run on the same branch. The report shows the change in each count and lists new and resolved findings.
- pip-audit gives no severity rating. Its findings take OSV-Scanner's rating for the same advisory, or Medium when OSV has none.
- Bandit's Low findings (such as `try/except/pass`) are counted but not listed.

## Tuning

- Known false positives from gitleaks go in the `[allowlist]` in `gitleaks.toml`.
- New project-specific patterns go in `semgrep-rules.yml`.
- `build_report.py` is the same script used by the other BlueSky repositories; `SCAN_TOOLS` in the workflow picks which checks appear.
- Tool versions are pinned at the top of the workflow. Bump them deliberately: a new version can change the counts without any code change.
