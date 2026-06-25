# Changelog

All notable changes to the repo-validation-system are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-06-25

### Added
- `repo-validator` skill (7-phase validation pipeline: clone → discover → plan → install → test → report → cleanup)
- `skill-ab-benchmark` skill (controlled A/B benchmarking with baseline/treatment arms + HTML report)
- Orchestrator agent spec (`agents/orchestrator.md`)
- Repo Audit Agent spec (`agents/repo-audit-agent.md`)
- A/B Runner Agent spec (`agents/ab-runner-agent.md`)
- Full system specification (`specs/system-spec.md`)
- JSON Schema for all evaluation entries (`specs/metrics-schema.json`)
- Verdict criteria documentation (`specs/verdict-criteria.md`)
- CLI script `scripts/validate.py` (single-repo validation)
- CLI script `scripts/compare.py` (cross-repo comparison from evaluations history)
- Unit tests with 90%+ coverage (`tests/test_validate.py`)
- GitHub Actions: `validate-on-pr.yml` (PR lint + spec integrity + manual repo validation)
- GitHub Actions: `nightly-benchmark.yml` (nightly self-check + repo health monitoring)
- `AGENTS.md` for AI agent instructions
- `docs/quickstart.md`
- `pyproject.toml` with dev dependencies and tool config
