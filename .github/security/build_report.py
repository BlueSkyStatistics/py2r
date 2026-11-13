#!/usr/bin/env python3
"""Turn raw scanner outputs into one Markdown security report.

Used by .github/workflows/security-scan.yml (same script in every BlueSky repo;
SCAN_TOOLS picks the scanners a repo runs). Reads the files the workflow
writes into RESULTS_DIR, writes report.md, summary.json and findings.json, and
compares against PREVIOUS_DIR (the last run's artifact) when it exists, so
each report shows what is new and what was resolved since the previous run.

Standard library only. Usage:
    python3 build_report.py RESULTS_DIR OUTPUT_DIR [PREVIOUS_DIR]
"""
import csv
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SEVERITIES = ["Critical", "High", "Medium", "Low", "Info"]
MAX_ROWS = 150

# ESLint rules sorted into report severities. Anything not listed is Low.
ESLINT_HIGH = {
    "no-unsanitized/method", "no-unsanitized/property",
    "@microsoft/sdl/no-inner-html", "@microsoft/sdl/no-html-method",
    "@microsoft/sdl/no-document-write", "@microsoft/sdl/no-electron-node-integration",
    "@microsoft/sdl/no-postmessage-star-origin",
    "no-eval", "no-implied-eval", "no-new-func", "security/detect-eval-with-expression",
}
ESLINT_MEDIUM = {
    "security/detect-child-process", "security/detect-non-literal-require",
    "@microsoft/sdl/no-insecure-url", "security/detect-unsafe-regex",
    "security/detect-pseudoRandomBytes", "security/detect-buffer-noassert",
    "security/detect-disable-mustache-escape", "security/detect-new-buffer",
}


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read().strip()
        return json.loads(text) if text else default
    except (OSError, ValueError):
        return default


def rel(path):
    workspace = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
    path = str(path)
    if path.startswith(workspace):
        path = path[len(workspace):].lstrip("/")
    return path


def finding(tool, severity, rule, location, detail, key=None):
    return {
        "tool": tool,
        "severity": severity,
        "rule": rule,
        "location": location,
        "detail": detail,
        # Line numbers shift between runs, so the change-tracking key leaves them out.
        "key": key or f"{tool}|{rule}|{location.split(':')[0]}|{detail}",
    }


def parse_gitleaks(results):
    data = load_json(results / "gitleaks.json", None)
    if data is None:
        return None, []
    out = []
    for leak in data:
        location = f"{leak.get('File')}:{leak.get('StartLine')}"
        detail = f"commit {leak.get('Commit', '')[:8]} on {leak.get('Date', '')[:10]} by {leak.get('Author', '')}"
        out.append(finding("gitleaks", "High", leak.get("RuleID", ""), location, detail,
                           key=f"gitleaks|{leak.get('RuleID')}|{leak.get('File')}|{leak.get('Fingerprint', '')}"))
    return True, out


def parse_npm_audit(results):
    data = load_json(results / "npm-audit.json", None)
    if data is None or "vulnerabilities" not in data:
        return None, []
    sev_map = {"critical": "Critical", "high": "High", "moderate": "Medium", "low": "Low", "info": "Info"}
    out = []
    for name, vuln in data["vulnerabilities"].items():
        advisories = [v for v in vuln.get("via", []) if isinstance(v, dict)]
        via = [v for v in vuln.get("via", []) if isinstance(v, str)]
        fix = vuln.get("fixAvailable")
        if isinstance(fix, dict):
            fix = f"{fix.get('name')}@{fix.get('version')}" + (" (major)" if fix.get("isSemVerMajor") else "")
        else:
            fix = "available" if fix else "none"
        if advisories:
            what = "; ".join(f"[{a.get('title', '')[:80]}]({a.get('url', '')})" for a in advisories[:3])
            if len(advisories) > 3:
                what += f" and {len(advisories) - 3} more"
        else:
            what = "via " + ", ".join(via)
        detail = f"{vuln.get('range', '')} - {what} - fix: {fix}"
        out.append(finding("npm audit", sev_map.get(vuln.get("severity"), "Medium"), name,
                           "package.json" if vuln.get("isDirect") else "transitive", detail,
                           key=f"npm|{name}|{','.join(sorted(a.get('url', '') for a in advisories))}"))
    return True, out


def deps_source(path=""):
    """Where dependency findings come from. Lists exported at scan time are reported as DEPS_SOURCE."""
    path = rel(path)
    if not path or os.path.isabs(path):
        return os.environ.get("DEPS_SOURCE") or os.path.basename(path) or "dependencies"
    return path


def osv_severity(score):
    try:
        value = float(score)
    except (TypeError, ValueError):
        return "Medium"
    if value >= 9:
        return "Critical"
    if value >= 7:
        return "High"
    if value >= 4:
        return "Medium"
    return "Low"


def parse_osv(results):
    data = load_json(results / "osv.json", None)
    if data is None:
        return None, []
    out = []
    for result in data.get("results", []):
        for pkg in result.get("packages", []):
            info = pkg.get("package", {})
            vulns = {v.get("id"): v for v in pkg.get("vulnerabilities", [])}
            for group in pkg.get("groups", []) or [{"ids": [i]} for i in vulns]:
                ids = group.get("ids", [])
                vuln = vulns.get(ids[0], {}) if ids else {}
                summary = vuln.get("summary") or vuln.get("details", "")[:80]
                detail = f"{info.get('version')} - {', '.join(ids[:3])} - {summary}"
                out.append(finding("OSV-Scanner", osv_severity(group.get("max_severity")),
                                   info.get("name", ""), deps_source(result.get("source", {}).get("path", "")),
                                   detail, key=f"osv|{info.get('name')}|{ids[0] if ids else ''}"))
    return True, out


def parse_pip_audit(results):
    data = load_json(results / "pip-audit.json", None)
    if data is None or "dependencies" not in data:
        return None, []
    # pip-audit does not rate severity; borrow OSV-Scanner's rating for the same advisory when it has one.
    osv_sev = {}
    for result in (load_json(results / "osv.json", {}) or {}).get("results", []):
        for pkg in result.get("packages", []):
            for group in pkg.get("groups", []):
                for vid in group.get("ids", []) + group.get("aliases", []):
                    osv_sev[vid] = osv_severity(group.get("max_severity"))
    out = []
    for dep in data["dependencies"]:
        seen = set()
        for vuln in dep.get("vulns", []):
            if vuln.get("id") in seen:
                continue
            seen.add(vuln.get("id"))
            ids = [vuln.get("id", "")] + vuln.get("aliases", [])
            severity = next((osv_sev[i] for i in ids if i in osv_sev), "Medium")
            fix = ", ".join(vuln.get("fix_versions", [])) or "none"
            text = re.sub(r"^(?:[#*\s]|Vulnerability Summary|Summary|Impact|Description)+", "",
                          " ".join((vuln.get("description") or "").split()))
            detail = f"{dep.get('version')} - {', '.join(ids[:3])} - {text[:80]} - fix: {fix}"
            out.append(finding("pip-audit", severity, dep.get("name", ""), deps_source(), detail,
                               key=f"pip-audit|{dep.get('name')}|{vuln.get('id')}"))
    return True, out


def parse_bandit(results):
    data = load_json(results / "bandit.json", None)
    if data is None or "results" not in data:
        return None, []
    sev_map = {"HIGH": "High", "MEDIUM": "Medium", "LOW": "Low"}
    out = []
    for res in data["results"]:
        severity = sev_map.get(res.get("issue_severity"), "Medium")
        # Low-confidence matches are mostly noise, so they drop one level.
        if res.get("issue_confidence") == "LOW" and severity != "Low":
            severity = SEVERITIES[SEVERITIES.index(severity) + 1]
        rule = f"{res.get('test_id')} {res.get('test_name')}"
        location = f"{rel(res.get('filename', '')).removeprefix('./')}:{res.get('line_number')}"
        out.append(finding("Bandit", severity, rule, location, " ".join(res.get("issue_text", "").split())[:140]))
    return True, out


def parse_electronegativity(results):
    path = results / "electronegativity.csv"
    if not path.exists():
        return None, []
    sev_map = {"CRITICAL": "Critical", "HIGH": "High", "MEDIUM": "Medium", "LOW": "Low", "INFORMATIONAL": "Info"}
    out = []
    with open(path, encoding="utf-8") as fh:
        rows = csv.reader(fh, skipinitialspace=True)
        next(rows, None)
        for row in rows:
            if len(row) < 7:
                continue
            issue, severity, _confidence, filename, location, sample, description = row[:7]
            loc = f"{filename}:{location.split(':')[0]}" if filename != "N/A" else "global"
            detail = description + (f" - `{sample.strip()[:90]}`" if sample and sample != "N/A" else "")
            out.append(finding("Electronegativity", sev_map.get(severity.upper(), "Medium"), issue, loc, detail))
    return True, out


def parse_eslint(results):
    data = load_json(results / "eslint.json", None)
    if data is None:
        return None, []
    out = []
    for file_result in data:
        path = rel(file_result.get("filePath", ""))
        for msg in file_result.get("messages", []):
            rule = msg.get("ruleId")
            if not rule:
                out.append(finding("ESLint", "Info", "parse-error", f"{path}:{msg.get('line', 0)}",
                                   "File could not be parsed and was not scanned"))
                continue
            severity = "High" if rule in ESLINT_HIGH else "Medium" if rule in ESLINT_MEDIUM else "Low"
            out.append(finding("ESLint", severity, rule, f"{path}:{msg.get('line')}", msg.get("message", "")[:140]))
    return True, out


def parse_semgrep(results):
    data = load_json(results / "semgrep.json", None)
    if data is None:
        return None, []
    sev_map = {"ERROR": "High", "WARNING": "Medium", "INFO": "Low"}
    out = []
    for res in data.get("results", []):
        extra = res.get("extra", {})
        rule = res.get("check_id", "").split(".")[-1]
        location = f"{rel(res.get('path', ''))}:{res.get('start', {}).get('line')}"
        message = " ".join(extra.get("message", "").split())[:140]
        out.append(finding("Semgrep", sev_map.get(extra.get("severity"), "Medium"), rule, location, message))
    return True, out


CHECKS = [
    ("Secrets in git history", "gitleaks", parse_gitleaks),
    ("Vulnerable dependencies", "npm audit", parse_npm_audit),
    ("Vulnerable Python dependencies", "pip-audit", parse_pip_audit),
    ("Vulnerable dependencies (OSV)", "OSV-Scanner", parse_osv),
    ("Electron configuration", "Electronegativity", parse_electronegativity),
    ("Code patterns (custom + registry rules)", "Semgrep", parse_semgrep),
    ("Code patterns (security lint)", "ESLint", parse_eslint),
    ("Python code patterns", "Bandit", parse_bandit),
]

# Tools whose Low findings are counted but not listed, because they are mostly noise.
QUIET_LOW = {"ESLint", "Bandit"}


def selected_checks():
    """SCAN_TOOLS (comma-separated tool names) limits the report to the scanners this repo runs."""
    wanted = {t.strip() for t in os.environ.get("SCAN_TOOLS", "").split(",") if t.strip()}
    return [c for c in CHECKS if not wanted or c[1] in wanted]


def sanitize_raw(results):
    """Strip source code and matched text from raw outputs before they are uploaded."""
    eslint = load_json(results / "eslint.json", None)
    if isinstance(eslint, list):
        for item in eslint:
            item.pop("source", None)
            item.pop("output", None)
        (results / "eslint.json").write_text(json.dumps(eslint), encoding="utf-8")
    bandit = load_json(results / "bandit.json", None)
    if isinstance(bandit, dict):
        for res in bandit.get("results", []):
            res.pop("code", None)
        (results / "bandit.json").write_text(json.dumps(bandit), encoding="utf-8")
    semgrep = load_json(results / "semgrep.json", None)
    if isinstance(semgrep, dict):
        for res in semgrep.get("results", []):
            res.get("extra", {}).pop("lines", None)
        (results / "semgrep.json").write_text(json.dumps(semgrep), encoding="utf-8")


def md_escape(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def severity_counts(findings):
    counts = Counter(f["severity"] for f in findings)
    return {s: counts.get(s, 0) for s in SEVERITIES}


def fmt_delta(now, before):
    if before is None:
        return ""
    diff = now - before
    return f" ({'+' if diff > 0 else ''}{diff})" if diff else ""


def main():
    results = Path(sys.argv[1])
    output = Path(sys.argv[2])
    previous = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    output.mkdir(parents=True, exist_ok=True)
    sanitize_raw(results)

    all_findings = []
    check_rows = []
    for title, tool, parser in selected_checks():
        ran, items = parser(results)
        all_findings.extend(items)
        check_rows.append((title, tool, ran, items))

    prev_summary = load_json(previous / "summary.json", None) if previous else None
    prev_findings = load_json(previous / "findings.json", None) if previous else None

    meta = {
        "repository": os.environ.get("GITHUB_REPOSITORY", "local"),
        "ref": os.environ.get("SCAN_BRANCH") or os.environ.get("GITHUB_REF_NAME", ""),
        "commit": (os.environ.get("SCAN_COMMIT") or os.environ.get("GITHUB_SHA", ""))[:8],
        "run_url": (f"{os.environ.get('GITHUB_SERVER_URL')}/{os.environ.get('GITHUB_REPOSITORY')}/actions/runs/"
                    f"{os.environ.get('GITHUB_RUN_ID')}") if os.environ.get("GITHUB_RUN_ID") else "",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    summary = {
        "meta": meta,
        "totals": severity_counts(all_findings),
        "by_tool": {tool: severity_counts(items) for _, tool, ran, items in check_rows if ran},
    }

    # Change tracking: compare multisets of finding keys with the previous run.
    now_keys = Counter(f["key"] for f in all_findings)
    new, resolved = [], []
    if prev_findings is not None:
        prev_keys = Counter(f["key"] for f in prev_findings)
        remaining = now_keys - prev_keys
        for f in all_findings:
            if remaining[f["key"]] > 0:
                new.append(f)
                remaining[f["key"]] -= 1
        gone = prev_keys - now_keys
        for f in prev_findings:
            if gone[f["key"]] > 0:
                resolved.append(f)
                gone[f["key"]] -= 1

    prev_totals = (prev_summary or {}).get("totals")
    prev_by_tool = (prev_summary or {}).get("by_tool", {})
    lines = [
        f"# Security scan report: {meta['repository']}",
        "",
        f"Generated {meta['generated']} for `{meta['ref']}` at commit `{meta['commit']}`."
        + (f" [Workflow run]({meta['run_url']})." if meta["run_url"] else ""),
        "",
    ]
    if prev_summary:
        pm = prev_summary.get("meta", {})
        lines += [f"Compared with the previous run on {pm.get('generated', '?')} (commit `{pm.get('commit', '?')}`). "
                  "Numbers in brackets are the change since then.", ""]
    else:
        lines += ["No previous run was found, so this report is the baseline for future comparisons.", ""]

    lines += ["## Results at a glance", "", "| Check | Tool | " + " | ".join(SEVERITIES) + " |",
              "| --- | --- | " + " | ".join("---" for _ in SEVERITIES) + " |"]
    for title, tool, ran, items in check_rows:
        if not ran:
            label = "skipped" if tool == "Electronegativity" and os.environ.get("SCAN_ELECTRON") == "false" else "not run"
            lines.append(f"| {title} | {tool} | " + " | ".join(label if i == 0 else "" for i, _ in enumerate(SEVERITIES)) + " |")
            continue
        counts = severity_counts(items)
        before = prev_by_tool.get(tool)
        cells = [f"{counts[s]}{fmt_delta(counts[s], before.get(s) if before else None)}" for s in SEVERITIES]
        lines.append(f"| {title} | {tool} | " + " | ".join(cells) + " |")
    totals = summary["totals"]
    lines.append("| **Total** | | " + " | ".join(
        f"**{totals[s]}{fmt_delta(totals[s], prev_totals.get(s) if prev_totals else None)}**" for s in SEVERITIES) + " |")
    quiet = [tool for _, tool, ran, _ in check_rows if ran and tool in QUIET_LOW]
    if quiet:
        lines += ["", f"Low findings from {' and '.join(quiet)} are mostly noise; "
                  "they are counted but not listed below.", ""]
    else:
        lines.append("")

    if prev_findings is not None:
        lines += ["## Changes since the previous run", ""]
        listed = {name: [f for f in items if not (f["tool"] in QUIET_LOW and f["severity"] == "Low")]
                  for name, items in (("New findings", new), ("Resolved findings", resolved))}
        if not new and not resolved:
            lines += ["No findings were added or resolved.", ""]
        elif not any(listed.values()):
            lines += [f"Only unlisted low-severity findings changed ({len(new)} new, {len(resolved)} resolved).", ""]
        for heading, items in listed.items():
            if not items:
                continue
            lines += [f"### {heading} ({len(items)})", "", "| Severity | Tool | Rule | Location | Detail |",
                      "| --- | --- | --- | --- | --- |"]
            for f in sorted(items, key=lambda f: SEVERITIES.index(f["severity"]))[:MAX_ROWS]:
                lines.append(f"| {f['severity']} | {f['tool']} | {md_escape(f['rule'])} | `{md_escape(f['location'])}` | {md_escape(f['detail'])} |")
            lines.append("")

    for title, tool, ran, items in check_rows:
        lines += [f"## {title} ({tool})", ""]
        if not ran:
            if tool == "Electronegativity" and os.environ.get("SCAN_ELECTRON") == "false":
                lines += ["Skipped: this repository is not an Electron app.", ""]
            else:
                lines += ["This scan did not run or produced no output. Check the workflow log.", ""]
            continue
        shown = [f for f in items if not (tool in QUIET_LOW and f["severity"] == "Low")]
        if not shown:
            lines += ["No findings." if not items else f"{len(items)} low-severity findings only; see the raw output.", ""]
            continue
        lines += ["| Severity | Rule | Location | Detail |", "| --- | --- | --- | --- |"]
        shown.sort(key=lambda f: (SEVERITIES.index(f["severity"]), f["rule"], f["location"]))
        for f in shown[:MAX_ROWS]:
            lines.append(f"| {f['severity']} | {md_escape(f['rule'])} | `{md_escape(f['location'])}` | {md_escape(f['detail'])} |")
        if len(shown) > MAX_ROWS:
            lines.append(f"\n{len(shown) - MAX_ROWS} more rows are in the raw output.")
        lines.append("")

    notes = [n for n in os.environ.get("SCAN_NOTES", "").split("||") if n.strip()]
    if notes:
        lines += ["## Notes and limitations", ""] + [f"- {n.strip()}" for n in notes] + [""]

    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output / "findings.json").write_text(json.dumps(all_findings, indent=1), encoding="utf-8")
    print(json.dumps(summary["totals"]))


if __name__ == "__main__":
    main()
