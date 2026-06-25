# AGENTS.md — Instructions for AI Agents

This file governs how AI agents (Claude, Copilot, etc.) should behave when working on this repository.

---

## Project identity

**repo-validation-system** is a multi-agent system for automated repository validation and skill A/B benchmarking. It is built on top of two Claude skills (`repo-validator`, `skill-ab-benchmark`) and exposes them via CLI scripts, a Python API, and GitHub Actions workflows.

---

## Working principles

### 1. Read the spec before coding
Always read `specs/system-spec.md` before making changes. It is the source of truth for behavior and metrics definitions.

### 2. Isolation is sacred
The validation system NEVER:
- Installs packages globally
- Modifies system files
- Runs untrusted repo scripts without reading them first
- Executes code outside of isolated environments (venv, local node_modules, cargo target)

Any code you write must respect this constraint.

### 3. Human gates
The following actions ALWAYS require explicit human approval before proceeding:
- Phase 3 (Test Plan) of repo-validator
- Phase 0 (Benchmark Plan) of skill-ab-benchmark
- Cleanup decisions (keep or remove cache)
- Publishing benchmark results

### 4. Skills are the contract
The files under `skills/` are the authoritative specs for agent behavior. If the Python scripts diverge from the skill specs, fix the scripts — not the skills.

---

## File ownership

| Path | Owner | Notes |
|------|-------|-------|
| `skills/*/SKILL.md` | Skill authors | Do not edit without versioning |
| `specs/` | Architecture team | Propose changes via PR |
| `scripts/` | Engineering | Implements the skill specs |
| `agents/` | Architecture team | Agent prompt templates |
| `.github/workflows/` | DevOps | CI/CD automation |

---

## Code style

- Python 3.11+, type hints required on all public functions
- `ruff` for linting, `black` for formatting
- All new metrics must be added to `specs/metrics-schema.json`
- Report templates in `skills/skill-ab-benchmark/report-template.html` — follow the naming conventions strictly (never use `baseline`/`treatment` in rendered UI)

---

## Testing

```bash
# Run all tests
pytest tests/ -v --cov=src --cov-report=term-missing

# Run just unit tests (fast)
pytest tests/unit/ -v

# Run integration tests (needs network)
pytest tests/integration/ -v -m "not slow"
```

---

## When in doubt

1. Check `specs/system-spec.md`
2. Check the relevant `SKILL.md`
3. Check `docs/architecture.md`
4. Open a question as a GitHub Issue
