#!/usr/bin/env python3
"""
compare.py — Cross-repo comparison from evaluations history
Part of: repo-validation-system

Usage:
    python scripts/compare.py juliopessan/arch-review-assistant juliopessan/llm-observability
    python scripts/compare.py --all                          # Show all past evaluations
    python scripts/compare.py --last 5                       # Show last 5 evaluations
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

EVALUATIONS_DB = Path.home() / ".cache" / "repo-validator" / "evaluations.json"

VERDICT_EMOJI = {
    "RECOMMENDED": "✅",
    "CONDITIONAL": "⚠️",
    "NOT RECOMMENDED": "❌",
    "UNABLE TO VALIDATE": "🚫",
}


def load_evaluations(db_path: Path = EVALUATIONS_DB) -> list:
    if not db_path.exists():
        return []
    try:
        return [e for e in json.loads(db_path.read_text()) if e.get("_type") == "repo-validator"]
    except (json.JSONDecodeError, KeyError):
        return []


def format_metric(value, suffix: str = "", precision: int = 1, width: int = 12) -> str:
    if value is None:
        return "N/A".ljust(width)
    if isinstance(value, float):
        return f"{value:.{precision}f}{suffix}".ljust(width)
    return f"{value}{suffix}".ljust(width)


def compare_repos(repos: list[str], evaluations: list[dict]) -> None:
    """Print a side-by-side comparison table."""

    # Find latest evaluation per repo
    latest: dict[str, dict] = {}
    for ev in evaluations:
        r = ev.get("repo", "")
        if r in repos:
            if r not in latest or ev["date"] > latest[r]["date"]:
                latest[r] = ev

    missing = [r for r in repos if r not in latest]
    if missing:
        print(f"⚠️  No evaluation found for: {', '.join(missing)}")
        repos = [r for r in repos if r in latest]

    if not repos:
        print("No evaluations to compare.")
        return

    # Header
    col_w = max(25, max(len(r) for r in repos) + 2)
    metric_w = 14

    header_line = "Metric".ljust(20) + " | ".join(r.ljust(col_w) for r in repos)
    print("\n" + "="*len(header_line))
    print(f"CROSS-REPO COMPARISON — {datetime.now().strftime('%Y-%m-%d')}")
    print("="*len(header_line))
    print(header_line)
    print("-"*len(header_line))

    def row(label: str, fn) -> str:
        cells = [fn(latest[r]) for r in repos]
        return f"{label.ljust(20)}" + " | ".join(str(c).ljust(col_w) for c in cells)

    print(row("Verdict", lambda e: f"{VERDICT_EMOJI.get(e.get('verdict', ''), '')} {e.get('verdict', 'N/A')}"))
    print(row("Date", lambda e: e.get("date", "N/A")[:10]))
    print(row("Commit", lambda e: e.get("commit", "N/A")))
    print(row("Language", lambda e: e.get("stack", {}).get("language", "N/A")))
    print("-"*len(header_line))
    print(row("Test pass rate", lambda e: f"{e.get('metrics', {}).get('tests_pass_rate', 'N/A')}%"))
    print(row("Coverage", lambda e: f"{e.get('metrics', {}).get('coverage', 'N/A')}{'%' if e.get('metrics', {}).get('coverage') is not None else ''}"))
    print(row("Build", lambda e: "✅ pass" if e.get("metrics", {}).get("build_success") else "❌ fail"))
    print(row("Lint errors", lambda e: str(e.get("metrics", {}).get("lint_errors", "N/A"))))
    print(row("Vulns (critical)", lambda e: f"{e.get('metrics', {}).get('vulns', 'N/A')} ({e.get('metrics', {}).get('vulns_critical', 0)} crit)"))
    print(row("Test time (s)", lambda e: f"{e.get('metrics', {}).get('test_time_seconds', 'N/A')}"))
    print(row("Repo size (MB)", lambda e: f"{e.get('metrics', {}).get('repo_size_mb', 'N/A')}"))
    print(row("Code files", lambda e: str(e.get("metrics", {}).get("code_files", "N/A"))))
    print("="*len(header_line))
    print()


def list_evaluations(evaluations: list[dict], n: Optional[int] = None) -> None:
    """List evaluations in reverse chronological order."""
    if not evaluations:
        print("No evaluations found in history.")
        return

    sorted_evals = sorted(evaluations, key=lambda e: e.get("date", ""), reverse=True)
    if n:
        sorted_evals = sorted_evals[:n]

    print(f"\n{'Date':<12} {'Repo':<40} {'Verdict':<22} {'Tests':<10} {'Coverage':<10}")
    print("-"*100)
    for ev in sorted_evals:
        verdict = ev.get("verdict", "N/A")
        icon = VERDICT_EMOJI.get(verdict, "")
        m = ev.get("metrics", {})
        tests = f"{m.get('tests_pass_rate', 'N/A')}%" if m.get('tests_pass_rate') is not None else "N/A"
        cov = f"{m.get('coverage', 'N/A')}%" if m.get('coverage') is not None else "N/A"
        print(f"{ev.get('date', '')[:10]:<12} {ev.get('repo', 'N/A'):<40} {icon} {verdict:<20} {tests:<10} {cov:<10}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare repo evaluations")
    parser.add_argument("repos", nargs="*", help="Repos to compare (owner/repo format)")
    parser.add_argument("--all", action="store_true", help="List all past evaluations")
    parser.add_argument("--last", type=int, help="Show last N evaluations")
    parser.add_argument("--db", type=Path, default=EVALUATIONS_DB, help="Path to evaluations JSON")
    args = parser.parse_args()

    evaluations = load_evaluations(args.db)

    if args.all or args.last:
        list_evaluations(evaluations, n=args.last)
    elif args.repos:
        compare_repos(args.repos, evaluations)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
