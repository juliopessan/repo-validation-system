"""
Unit tests for the repo validation system.
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# We test the scripts directly
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.validate import (
    normalize_repo,
    compute_verdict,
    detect_stack,
    count_code_files,
    VERDICT_RECOMMENDED,
    VERDICT_CONDITIONAL,
    VERDICT_NOT_RECOMMENDED,
    VERDICT_UNABLE,
)
from scripts.compare import load_evaluations


# ─── normalize_repo ───────────────────────────────────────────────────────────

class TestNormalizeRepo:
    def test_owner_slash_repo(self):
        assert normalize_repo("owner/project") == ("owner", "project")

    def test_full_github_url(self):
        assert normalize_repo("https://github.com/juliopessan/arch-review-assistant") == (
            "juliopessan", "arch-review-assistant"
        )

    def test_full_github_url_with_git(self):
        assert normalize_repo("https://github.com/owner/repo.git") == ("owner", "repo")

    def test_trailing_slash(self):
        assert normalize_repo("owner/repo/") == ("owner", "repo")

    def test_invalid_input(self):
        with pytest.raises(ValueError, match="Cannot parse repo"):
            normalize_repo("notarepo")

    def test_http_url(self):
        assert normalize_repo("http://github.com/owner/repo") == ("owner", "repo")


# ─── compute_verdict ─────────────────────────────────────────────────────────

class TestComputeVerdict:
    def test_recommended_all_green(self):
        metrics = {
            "tests_pass": 90, "tests_total": 100, "tests_pass_rate": 90.0,
            "coverage": 75.0, "build_success": True,
            "lint_errors": 0, "vulns": 0, "vulns_critical": 0,
        }
        assert compute_verdict(metrics) == VERDICT_RECOMMENDED

    def test_recommended_perfect(self):
        metrics = {
            "tests_pass": 100, "tests_total": 100, "tests_pass_rate": 100.0,
            "coverage": 95.0, "build_success": True,
            "vulns_critical": 0,
        }
        assert compute_verdict(metrics) == VERDICT_RECOMMENDED

    def test_conditional_70_percent(self):
        metrics = {
            "tests_pass": 70, "tests_total": 100, "tests_pass_rate": 70.0,
            "coverage": 50.0, "build_success": True,
            "vulns_critical": 0,
        }
        assert compute_verdict(metrics) == VERDICT_CONDITIONAL

    def test_not_recommended_critical_vuln(self):
        metrics = {
            "tests_pass": 95, "tests_total": 100, "tests_pass_rate": 95.0,
            "coverage": 80.0, "build_success": True,
            "vulns_critical": 1,
        }
        assert compute_verdict(metrics) == VERDICT_NOT_RECOMMENDED

    def test_not_recommended_build_fails(self):
        metrics = {
            "tests_pass": 95, "tests_total": 100, "tests_pass_rate": 95.0,
            "coverage": 80.0, "build_success": False,
            "vulns_critical": 0,
        }
        assert compute_verdict(metrics) == VERDICT_NOT_RECOMMENDED

    def test_not_recommended_low_pass_rate(self):
        metrics = {
            "tests_pass": 50, "tests_total": 100, "tests_pass_rate": 50.0,
            "coverage": 80.0, "build_success": True,
            "vulns_critical": 0,
        }
        assert compute_verdict(metrics) == VERDICT_NOT_RECOMMENDED

    def test_unable_no_tests_no_build(self):
        metrics = {
            "tests_pass": 0, "tests_total": 0,
            "build_success": False,
        }
        assert compute_verdict(metrics) == VERDICT_UNABLE

    def test_recommended_no_coverage_data(self):
        """Coverage = None should not block RECOMMENDED if tests are great."""
        metrics = {
            "tests_pass": 95, "tests_total": 100, "tests_pass_rate": 95.0,
            "coverage": None, "build_success": True,
            "vulns_critical": 0,
        }
        assert compute_verdict(metrics) == VERDICT_RECOMMENDED


# ─── detect_stack ─────────────────────────────────────────────────────────────

class TestDetectStack:
    def test_python_repo(self, tmp_path):
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "requirements.txt").write_text("pytest")
        stack = detect_stack(tmp_path)
        assert stack["language"] == "Python"
        assert stack["package_manager"] == "pip"
        assert stack["test_framework"] == "pytest"

    def test_typescript_with_jest(self, tmp_path):
        (tmp_path / "index.ts").write_text("const x = 1;")
        pkg = {"dependencies": {}, "devDependencies": {"jest": "^29.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        stack = detect_stack(tmp_path)
        assert stack["language"] == "TypeScript"
        assert stack["package_manager"] == "npm"
        assert stack["test_framework"] == "jest"

    def test_typescript_with_pnpm(self, tmp_path):
        (tmp_path / "index.ts").write_text("const x = 1;")
        (tmp_path / "pnpm-lock.yaml").write_text("")
        pkg = {"devDependencies": {"vitest": "^1.0.0"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        stack = detect_stack(tmp_path)
        assert stack["package_manager"] == "pnpm"
        assert stack["test_framework"] == "vitest"

    def test_go_repo(self, tmp_path):
        (tmp_path / "main.go").write_text("package main")
        (tmp_path / "go.mod").write_text("module example.com/app\ngo 1.21")
        stack = detect_stack(tmp_path)
        assert stack["language"] == "Go"
        assert stack["package_manager"] == "go"
        assert stack["test_framework"] == "go test"

    def test_rust_repo(self, tmp_path):
        (tmp_path / "main.rs").write_text("fn main() {}")
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'app'")
        stack = detect_stack(tmp_path)
        assert stack["language"] == "Rust"
        assert stack["package_manager"] == "cargo"

    def test_docker_detection(self, tmp_path):
        (tmp_path / "main.py").write_text("")
        (tmp_path / "Dockerfile").write_text("FROM python:3.11")
        stack = detect_stack(tmp_path)
        assert stack["has_docker"] is True

    def test_ci_detection(self, tmp_path):
        (tmp_path / "main.py").write_text("")
        gh_dir = tmp_path / ".github" / "workflows"
        gh_dir.mkdir(parents=True)
        (gh_dir / "ci.yml").write_text("name: CI")
        stack = detect_stack(tmp_path)
        assert stack["has_ci"] is True


# ─── count_code_files ─────────────────────────────────────────────────────────

class TestCountCodeFiles:
    def test_counts_python_files(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\ny = 2\n")
        (tmp_path / "b.py").write_text("z = 3\n")
        count, loc = count_code_files(tmp_path)
        assert count == 2
        assert loc == 3  # 2 + 1 non-empty lines

    def test_ignores_node_modules(self, tmp_path):
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "index.ts").write_text("const x = 1;")
        (tmp_path / "app.ts").write_text("const y = 2;")
        count, loc = count_code_files(tmp_path)
        assert count == 1

    def test_ignores_empty_lines(self, tmp_path):
        (tmp_path / "app.py").write_text("x = 1\n\n\ny = 2\n\n")
        count, loc = count_code_files(tmp_path)
        assert count == 1
        assert loc == 2


# ─── load_evaluations ─────────────────────────────────────────────────────────

class TestLoadEvaluations:
    def test_empty_file(self, tmp_path):
        db = tmp_path / "evaluations.json"
        db.write_text("[]")
        result = load_evaluations(db)
        assert result == []

    def test_filters_non_repo_validator_entries(self, tmp_path):
        db = tmp_path / "evaluations.json"
        data = [
            {"_type": "repo-validator", "repo": "owner/repo", "date": "2026-01-01", "verdict": "RECOMMENDED"},
            {"_type": "skill-ab-benchmark", "ruleset": "some-skill"},
        ]
        db.write_text(json.dumps(data))
        result = load_evaluations(db)
        assert len(result) == 1
        assert result[0]["_type"] == "repo-validator"

    def test_missing_file_returns_empty(self, tmp_path):
        result = load_evaluations(tmp_path / "nonexistent.json")
        assert result == []

    def test_corrupt_json_returns_empty(self, tmp_path):
        db = tmp_path / "evaluations.json"
        db.write_text("{invalid json}")
        result = load_evaluations(db)
        assert result == []


# ─── report_html ──────────────────────────────────────────────────────────────

class TestReportHtml:
    def test_render_recommended(self, tmp_path):
        from scripts.report_html import save_report
        p = save_report(
            output_path=tmp_path / "report.html",
            repo="owner/repo",
            commit="abc1234",
            verdict="RECOMMENDED",
            metrics={
                "tests_pass": 95, "tests_total": 100, "tests_pass_rate": 95.0,
                "coverage": 80.0, "build_success": True,
                "lint_errors": 0, "vulns": 0, "vulns_critical": 0,
                "code_files": 10,
            },
            stack={"language": "Python", "package_manager": "pip",
                   "test_framework": "pytest", "has_docker": True, "has_ci": True},
            strengths=["CI configurado"],
            weaknesses=[],
        )
        html = p.read_text()
        assert "owner/repo" in html
        assert "RECOMMENDED" in html
        assert "95" in html
        assert "ti-shield-check" in html
        assert "<!DOCTYPE html>" in html

    def test_render_conditional(self, tmp_path):
        from scripts.report_html import save_report
        p = save_report(
            output_path=tmp_path / "report.html",
            repo="owner/repo2",
            commit="def5678",
            verdict="CONDITIONAL",
            metrics={
                "tests_pass": 72, "tests_total": 100, "tests_pass_rate": 72.0,
                "coverage": 45.0, "build_success": True,
                "lint_errors": 3, "vulns": 2, "vulns_critical": 0,
                "code_files": 20,
            },
            stack={"language": "TypeScript", "package_manager": "pnpm",
                   "test_framework": "vitest", "has_docker": False, "has_ci": True},
            strengths=[],
            weaknesses=["Coverage baixo"],
        )
        html = p.read_text()
        assert "CONDITIONAL" in html
        assert "72" in html
        assert "Coverage baixo" in html

    def test_render_with_history(self, tmp_path):
        from scripts.report_html import save_report
        p = save_report(
            output_path=tmp_path / "report.html",
            repo="owner/repo",
            commit="abc",
            verdict="RECOMMENDED",
            metrics={"build_success": True, "code_files": 5, "tests_pass_rate": 91.0},
            stack={},
            strengths=[],
            weaknesses=[],
            history=[
                {"repo": "owner/repo", "date": "2026-01-01", "verdict": "CONDITIONAL",
                 "metrics": {"tests_pass_rate": 75, "coverage": 50}},
            ],
        )
        html = p.read_text()
        assert "Histórico" in html
        assert "CONDITIONAL" in html

    def test_html_has_chart_js(self, tmp_path):
        from scripts.report_html import save_report
        p = save_report(
            output_path=tmp_path / "report.html",
            repo="test/repo",
            commit="abc",
            verdict="RECOMMENDED",
            metrics={"build_success": True, "code_files": 1, "tests_pass_rate": 90.0},
            stack={},
            strengths=[],
            weaknesses=[],
        )
        html = p.read_text()
        assert "chart.umd.js" in html
        assert "tabler-icons" in html
        assert "metricsChart" in html

    def test_html_dark_mode_variables(self, tmp_path):
        from scripts.report_html import save_report
        p = save_report(
            output_path=tmp_path / "report.html",
            repo="test/repo",
            commit="abc",
            verdict="RECOMMENDED",
            metrics={"build_success": True, "code_files": 1, "tests_pass_rate": 90.0},
            stack={},
            strengths=[],
            weaknesses=[],
        )
        html = p.read_text()
        assert "prefers-color-scheme:dark" in html
        assert "--text-primary" in html
        assert "--surface-0" in html
