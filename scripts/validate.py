#!/usr/bin/env python3
"""
validate.py — CLI entrypoint for repo-validator skill
Part of: repo-validation-system

Usage:
    python scripts/validate.py owner/repo
    python scripts/validate.py https://github.com/owner/repo --ci
    python scripts/validate.py owner/repo --output ./reports/
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

CACHE_DIR = Path.home() / ".cache" / "repo-validator" / "repos"
EVALUATIONS_DB = Path.home() / ".cache" / "repo-validator" / "evaluations.json"
RESULTS_SUBDIR = ".validator-results"

VERDICT_RECOMMENDED = "RECOMMENDED"
VERDICT_CONDITIONAL = "CONDITIONAL"
VERDICT_NOT_RECOMMENDED = "NOT RECOMMENDED"
VERDICT_UNABLE = "UNABLE TO VALIDATE"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def normalize_repo(raw: str) -> tuple[str, str]:
    """Normalize repo input to (owner, repo) tuple."""
    raw = raw.strip().rstrip("/")
    # Full URL
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?$", raw)
    if m:
        return m.group(1), m.group(2)
    # owner/repo
    if "/" in raw:
        parts = raw.split("/")
        return parts[0], parts[1]
    raise ValueError(f"Cannot parse repo from: {raw!r}. Use owner/repo or a GitHub URL.")


def run(cmd: str, cwd: Optional[Path] = None, capture: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command. Prints output if not capturing."""
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=capture, text=True
    )
    if not capture:
        return result
    return result


def ensure_cache() -> None:
    """Ensure cache and evaluations DB exist."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not EVALUATIONS_DB.exists():
        EVALUATIONS_DB.write_text("[]", encoding="utf-8")


def load_evaluations() -> list:
    """Load evaluations history."""
    try:
        return json.loads(EVALUATIONS_DB.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_evaluation(entry: dict) -> None:
    """Append an evaluation entry to the history DB."""
    evals = load_evaluations()
    evals.append(entry)
    EVALUATIONS_DB.write_text(json.dumps(evals, indent=2, ensure_ascii=False), encoding="utf-8")


# ─── Phase 1: Clone & Cache ───────────────────────────────────────────────────

def get_cache_path(owner: str, repo: str) -> Path:
    return CACHE_DIR / f"{owner}-{repo}"


def clone_repo(owner: str, repo: str, force: bool = False) -> Path:
    """Clone or return cached repo path."""
    path = get_cache_path(owner, repo)
    if path.exists() and not force:
        print(f"✓ Cache hit: {path}")
        return path

    url = f"https://github.com/{owner}/{repo}.git"
    print(f"→ Cloning {url} ...")
    result = run(f"git clone --depth 1 {url} {path}")
    if result.returncode != 0:
        raise RuntimeError(f"Clone failed:\n{result.stderr}")

    # Check size
    size_result = run(f"du -sm {path}")
    if size_result.returncode == 0:
        size_mb = float(size_result.stdout.split()[0])
        if size_mb > 500:
            print(f"⚠️  WARNING: Repo is {size_mb:.0f} MB (> 500 MB threshold)")

    return path


# ─── Phase 2: Discovery ───────────────────────────────────────────────────────

def detect_stack(path: Path) -> dict:
    """Detect language, package manager, test framework, etc."""
    stack = {
        "language": "unknown",
        "package_manager": None,
        "test_framework": None,
        "web_framework": None,
        "has_docker": False,
        "has_ci": False,
    }

    files = set(p.name for p in path.rglob("*") if p.is_file())

    # Language detection by extension
    ext_counts: dict[str, int] = {}
    for f in path.rglob("*"):
        if f.is_file() and f.suffix:
            ext_counts[f.suffix] = ext_counts.get(f.suffix, 0) + 1

    lang_map = {
        ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript",
        ".js": "JavaScript", ".jsx": "JavaScript", ".go": "Go",
        ".rs": "Rust", ".java": "Java", ".rb": "Ruby", ".cs": "C#"
    }
    if ext_counts:
        best_ext = max(
            (e for e in ext_counts if e in lang_map),
            key=lambda e: ext_counts[e],
            default=None
        )
        if best_ext:
            stack["language"] = lang_map[best_ext]

    # Package manager
    if (path / "pnpm-lock.yaml").exists():
        stack["package_manager"] = "pnpm"
    elif (path / "yarn.lock").exists():
        stack["package_manager"] = "yarn"
    elif (path / "package.json").exists():
        stack["package_manager"] = "npm"
    elif (path / "pyproject.toml").exists():
        stack["package_manager"] = "pip/poetry"
    elif (path / "requirements.txt").exists():
        stack["package_manager"] = "pip"
    elif (path / "go.mod").exists():
        stack["package_manager"] = "go"
    elif (path / "Cargo.toml").exists():
        stack["package_manager"] = "cargo"

    # Test frameworks
    pkg_json = path / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "jest" in deps:
                stack["test_framework"] = "jest"
            elif "vitest" in deps:
                stack["test_framework"] = "vitest"
            elif "mocha" in deps:
                stack["test_framework"] = "mocha"
        except json.JSONDecodeError:
            pass

    if stack["language"] == "Python":
        stack["test_framework"] = "pytest"
    elif stack["language"] == "Go":
        stack["test_framework"] = "go test"
    elif stack["language"] == "Rust":
        stack["test_framework"] = "cargo test"

    # Docker & CI
    stack["has_docker"] = any(f in files for f in ("Dockerfile", "docker-compose.yml", "docker-compose.yaml"))
    stack["has_ci"] = any(
        (path / d).exists() for d in (".github/workflows", ".gitlab-ci.yml", "Jenkinsfile")
    )

    return stack


def count_code_files(path: Path) -> tuple[int, int]:
    """Return (code_file_count, approx_loc)."""
    code_exts = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".rb", ".cs"}
    skip_dirs = {"node_modules", "vendor", "__pycache__", ".git", "dist", "build", "target"}
    
    count = 0
    loc = 0
    for f in path.rglob("*"):
        if f.is_file() and f.suffix in code_exts:
            if not any(part in skip_dirs for part in f.parts):
                count += 1
                try:
                    lines = [l for l in f.read_text(errors="ignore").splitlines() if l.strip()]
                    loc += len(lines)
                except Exception:
                    pass
    return count, loc


# ─── Phase 3: Test Plan ───────────────────────────────────────────────────────

def build_test_plan(owner: str, repo: str, stack: dict, code_files: int) -> str:
    """Generate a markdown test plan."""
    lang = stack["language"]
    pm = stack["package_manager"] or "unknown"
    tf = stack["test_framework"] or "unknown"

    lang_commands = {
        "Python": {
            "install": f"python3 -m venv .validator-venv && source .validator-venv/bin/activate && pip install -e . 2>/dev/null || pip install -r requirements.txt",
            "lint": "ruff check . 2>&1 | tee .validator-results/lint.log",
            "test": "pytest --cov=. --cov-report=term-missing --tb=short 2>&1 | tee .validator-results/tests.log",
            "build": "python -m build 2>&1 | tee .validator-results/build.log",
            "audit": "pip-audit 2>&1 | tee .validator-results/audit.log",
        },
        "TypeScript": {
            "install": f"{pm} install",
            "lint": "npx eslint . 2>&1 | tee .validator-results/lint.log",
            "typecheck": "npx tsc --noEmit 2>&1 | tee .validator-results/typecheck.log",
            "test": f"{'npx vitest --coverage' if tf == 'vitest' else 'npx jest --coverage'} 2>&1 | tee .validator-results/tests.log",
            "build": f"{pm} run build 2>&1 | tee .validator-results/build.log",
            "audit": f"{pm} audit 2>&1 | tee .validator-results/audit.log",
        },
        "JavaScript": {
            "install": f"{pm} install",
            "test": f"{pm} test 2>&1 | tee .validator-results/tests.log",
            "build": f"{pm} run build 2>&1 | tee .validator-results/build.log",
            "audit": f"{pm} audit 2>&1 | tee .validator-results/audit.log",
        },
        "Go": {
            "install": "go mod download",
            "lint": "go vet ./... 2>&1 | tee .validator-results/lint.log",
            "test": "go test ./... -v -cover 2>&1 | tee .validator-results/tests.log",
            "build": "go build ./... 2>&1 | tee .validator-results/build.log",
        },
        "Rust": {
            "install": "cargo fetch",
            "lint": "cargo clippy 2>&1 | tee .validator-results/clippy.log",
            "test": "cargo test 2>&1 | tee .validator-results/tests.log",
            "build": "cargo build --release 2>&1 | tee .validator-results/build.log",
        },
    }

    cmds = lang_commands.get(lang, {
        "install": "# Manual install required",
        "test": "# No known test command for this stack",
    })

    steps = []
    i = 1
    if "lint" in cmds:
        steps.append(f"{i}. **Lint/Type check** — `{cmds.get('lint', cmds.get('typecheck', 'N/A'))}` — static analysis")
        i += 1
    if "typecheck" in cmds and "lint" in cmds:
        steps.append(f"{i}. **Type check** — `{cmds['typecheck']}` — TypeScript type safety")
        i += 1
    if "test" in cmds:
        steps.append(f"{i}. **Tests + Coverage** — `{cmds['test']}` — test pass rate and coverage %")
        i += 1
    if "build" in cmds:
        steps.append(f"{i}. **Build** — `{cmds['build']}` — production build verification")
        i += 1
    if "audit" in cmds:
        steps.append(f"{i}. **Security audit** — `{cmds['audit']}` — known CVEs in dependencies")
        i += 1

    plan = f"""## Plano de Validação: {owner}/{repo}

### Resumo
Repositório detectado com {code_files} arquivos de código fonte em {lang}.

### Ambiente
- **Linguagem:** {lang}
- **Package manager:** {pm}
- **Framework de teste:** {tf}
- **Isolamento:** {'venv (Python)' if lang == 'Python' else 'local node_modules' if lang in ('TypeScript', 'JavaScript') else 'cargo target / go build cache'}
- **Docker:** {'✓' if stack['has_docker'] else '✗'}
- **CI/CD:** {'✓' if stack['has_ci'] else '✗'}

### Instalação
```bash
{cmds.get('install', '# Manual install required')}
```

### Testes a executar
{chr(10).join(steps) if steps else '- Nenhum comando de teste detectado automaticamente'}

### Métricas a coletar
- [ ] Test pass rate (pass/total)
- [ ] Coverage percentual
- [ ] Tempo de execução dos testes
- [ ] Tempo de build
- [ ] Vulnerabilidades em dependências
- [ ] Erros de lint

### Riscos
- Dependências que precisam de rede durante testes?
- Secrets / env vars necessários?
- Recursos pesados (GPU, memória)?

---
**Aguardando aprovação para prosseguir com a instalação e execução.**
"""
    return plan


# ─── Phase 6: Report ─────────────────────────────────────────────────────────

def compute_verdict(metrics: dict) -> str:
    """Compute verdict from metrics."""
    tests_pass = metrics.get("tests_pass", 0)
    tests_total = metrics.get("tests_total", 0)
    coverage = metrics.get("coverage")
    build_success = metrics.get("build_success", False)
    vulns_critical = metrics.get("vulns_critical", 0)

    if tests_total == 0 and not build_success:
        return VERDICT_UNABLE

    pass_rate = (tests_pass / tests_total * 100) if tests_total > 0 else 0

    if vulns_critical > 0:
        return VERDICT_NOT_RECOMMENDED
    if not build_success:
        return VERDICT_NOT_RECOMMENDED
    if pass_rate < 70:
        return VERDICT_NOT_RECOMMENDED

    if pass_rate >= 90 and (coverage is None or coverage >= 70):
        return VERDICT_RECOMMENDED

    if pass_rate >= 70 and (coverage is None or coverage >= 40):
        return VERDICT_CONDITIONAL

    return VERDICT_NOT_RECOMMENDED


def generate_report(
    owner: str,
    repo: str,
    commit: str,
    stack: dict,
    metrics: dict,
    strengths: list[str],
    weaknesses: list[str],
    results_dir: Path,
    elapsed_minutes: float,
) -> str:
    """Generate a markdown report and save it."""
    verdict = compute_verdict(metrics)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    verdict_icons = {
        VERDICT_RECOMMENDED: "✅",
        VERDICT_CONDITIONAL: "⚠️",
        VERDICT_NOT_RECOMMENDED: "❌",
        VERDICT_UNABLE: "🚫",
    }

    metrics_rows = [
        ("Testes", f"{metrics.get('tests_pass', '?')}/{metrics.get('tests_total', '?')} ({metrics.get('tests_pass_rate', 0):.1f}%)",
         "✅" if metrics.get("tests_pass_rate", 0) >= 90 else "⚠️" if metrics.get("tests_pass_rate", 0) >= 70 else "❌"),
        ("Coverage", f"{metrics.get('coverage', 'N/A')}{'%' if metrics.get('coverage') is not None else ''}",
         "✅" if metrics.get("coverage", 0) >= 70 else "⚠️" if metrics.get("coverage", 0) >= 40 else "❌" if metrics.get("coverage") is not None else "-"),
        ("Build", "✓" if metrics.get("build_success") else "✗",
         "✅" if metrics.get("build_success") else "❌"),
        ("Lint errors", str(metrics.get("lint_errors", "N/A")),
         "✅" if metrics.get("lint_errors", 0) == 0 else "⚠️"),
        ("Vulnerabilidades", f"{metrics.get('vulns', 'N/A')} ({metrics.get('vulns_critical', 0)} critical)",
         "✅" if metrics.get("vulns_critical", 0) == 0 else "❌"),
        ("Tempo de testes", f"{metrics.get('test_time_seconds', 'N/A')}s", "-"),
        ("Tamanho do repo", f"{metrics.get('repo_size_mb', 'N/A')} MB", "-"),
        ("Arquivos de código", str(metrics.get("code_files", "N/A")), "-"),
    ]

    metrics_table = "\n".join(
        f"| {row[0]} | {row[1]} | {row[2]} |" for row in metrics_rows
    )

    report = f"""# Validação: {owner}/{repo}

**Data:** {now}  
**Versão avaliada:** `{commit}`  
**Tempo total:** {elapsed_minutes:.1f} minutos  
**Stack:** {stack.get('language', '?')} / {stack.get('package_manager', '?')} / {stack.get('test_framework', '?')}

---

## Veredito: {verdict_icons.get(verdict, '')} {verdict}

### Métricas

| Métrica | Resultado | Status |
|---------|-----------|--------|
{metrics_table}

### Pontos fortes
{chr(10).join(f'- {s}' for s in strengths) if strengths else '- Nenhum identificado'}

### Pontos fracos
{chr(10).join(f'- {w}' for w in weaknesses) if weaknesses else '- Nenhum identificado'}

### Critérios de veredito
- **RECOMMENDED**: testes ≥ 90%, coverage ≥ 70%, 0 vulns críticas, build ✓
- **CONDITIONAL**: testes ≥ 70%, coverage ≥ 40%, sem críticas
- **NOT RECOMMENDED**: testes < 70%, ou vuln crítica, ou build falha
- **UNABLE TO VALIDATE**: falha de instalação/ambiente

### Logs detalhados
Disponíveis em: `{results_dir}/`
"""

    report_path = results_dir / "REPORT.md"
    report_path.write_text(report, encoding="utf-8")
    return str(report_path)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a GitHub repository using the repo-validator skill"
    )
    parser.add_argument("repo", help="owner/repo or GitHub URL")
    parser.add_argument("--ci", action="store_true", help="CI mode: auto-approve test plan")
    parser.add_argument("--force-reclone", action="store_true", help="Force fresh clone")
    parser.add_argument("--output", type=Path, help="Copy final report to this directory")
    parser.add_argument("--no-cleanup-prompt", action="store_true", help="Skip cleanup prompt")
    args = parser.parse_args()

    # Setup
    ensure_cache()
    owner, repo = normalize_repo(args.repo)
    print(f"\n🔍 Repo Validation System — {owner}/{repo}\n")

    # Phase 1: Clone
    try:
        repo_path = clone_repo(owner, repo, force=args.force_reclone)
    except RuntimeError as e:
        print(f"❌ {e}")
        sys.exit(1)

    # Phase 2: Discovery
    print("→ Analyzing repository structure...")
    stack = detect_stack(repo_path)
    code_files, loc = count_code_files(repo_path)

    commit_result = run(f"git -C {repo_path} rev-parse --short HEAD")
    commit = commit_result.stdout.strip() if commit_result.returncode == 0 else "unknown"

    print(f"  Language: {stack['language']}")
    print(f"  Package manager: {stack['package_manager'] or 'unknown'}")
    print(f"  Test framework: {stack['test_framework'] or 'unknown'}")
    print(f"  Docker: {'✓' if stack['has_docker'] else '✗'}")
    print(f"  CI/CD: {'✓' if stack['has_ci'] else '✗'}")
    print(f"  Code files: {code_files} (~{loc} LOC)")

    # Phase 3: Test Plan [HUMAN GATE]
    plan = build_test_plan(owner, repo, stack, code_files)
    print(f"\n{'='*60}")
    print(plan)
    print(f"{'='*60}\n")

    if not args.ci:
        response = input("Aprovar plano e continuar? [s/N] ").strip().lower()
        if response not in ("s", "sim", "y", "yes"):
            print("Validação cancelada pelo usuário.")
            sys.exit(0)

    # Phase 4-5: Install & Execute
    results_dir = repo_path / RESULTS_SUBDIR
    results_dir.mkdir(exist_ok=True)

    print("\n→ Running validation...")
    metrics: dict = {
        "tests_pass": 0,
        "tests_total": 0,
        "tests_pass_rate": 0.0,
        "coverage": None,
        "build_success": False,
        "lint_errors": 0,
        "vulns": 0,
        "vulns_critical": 0,
        "test_time_seconds": None,
        "repo_size_mb": None,
        "code_files": code_files,
        "loc_approx": loc,
    }

    # Repo size
    size_result = run(f"du -sm {repo_path}")
    if size_result.returncode == 0:
        metrics["repo_size_mb"] = float(size_result.stdout.split()[0])

    # NOTE: In production, this would run the actual install + test commands.
    # For demo/CI purposes, we emit a placeholder noting the agent-driven execution.
    print("  ℹ️  Full execution requires the repo-audit-agent (Claude) to run the install + test commands.")
    print("  ℹ️  CLI stub records structure; agent fills in live metrics.")

    strengths: list[str] = []
    weaknesses: list[str] = []

    if stack["has_docker"]:
        strengths.append("Containerization with Docker")
    if stack["has_ci"]:
        strengths.append("CI/CD pipeline configured")
    if code_files > 0:
        strengths.append(f"Active codebase with {code_files} source files")

    # Phase 6: Report
    start_time = datetime.now(timezone.utc)
    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() / 60

    report_path = generate_report(
        owner, repo, commit, stack, metrics,
        strengths, weaknesses, results_dir, elapsed
    )

    # Persist evaluation
    verdict = compute_verdict(metrics)
    entry = {
        "_type": "repo-validator",
        "repo": f"{owner}/{repo}",
        "date": datetime.now(timezone.utc).isoformat(),
        "commit": commit,
        "verdict": verdict,
        "stack": stack,
        "metrics": metrics,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "report_path": report_path,
    }
    save_evaluation(entry)

    # Output
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        shutil.copy(report_path, args.output / f"{owner}-{repo}-report.md")
        print(f"✓ Report copied to: {args.output / f'{owner}-{repo}-report.md'}")

    print(f"\n{'='*60}")
    print(f"Verdict: {verdict}")
    print(f"Report: {report_path}")
    print(f"{'='*60}\n")

    # Phase 7: Cleanup
    if not args.no_cleanup_prompt and not args.ci:
        response = input("Manter repo no cache? [S/n] ").strip().lower()
        if response in ("n", "nao", "não", "no"):
            shutil.rmtree(repo_path)
            print(f"✓ Cache removido: {repo_path}")
        else:
            print(f"✓ Cache mantido: {repo_path}")


if __name__ == "__main__":
    main()
