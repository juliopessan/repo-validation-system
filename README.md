# 🔍 Repo Validation System

> **Multi-agent system for automated repository auditing and skill A/B benchmarking.**  
> Built on two Claude skills: `repo-validator` and `skill-ab-benchmark`.

---

## Overview

This system combines two complementary AI skills into a unified validation pipeline:

| Skill | Purpose |
|-------|---------|
| `repo-validator` | Clone, analyze, test, and score any GitHub repository |
| `skill-ab-benchmark` | Measure the real-world impact of a skill/ruleset via controlled A/B runs |

Together they answer two questions every engineer should ask before shipping:
1. **Is this repo healthy?** (test coverage, build, linting, security)
2. **Does this skill actually make agents write better code?** (quantified A/B delta)

---

## Architecture

```
repo-validation-system/
├── skills/
│   ├── repo-validator/         # Phase 0-7 validator skill
│   └── skill-ab-benchmark/     # A/B benchmark skill + HTML report template
├── agents/
│   ├── orchestrator.md         # Orchestrator agent spec
│   ├── repo-audit-agent.md     # Repo audit subagent spec
│   └── ab-runner-agent.md      # A/B runner subagent spec
├── specs/
│   ├── system-spec.md          # Full system specification
│   ├── metrics-schema.json     # Metrics output schema
│   └── verdict-criteria.md     # Verdict scoring criteria
├── scripts/
│   ├── validate.sh             # CLI entrypoint (single repo)
│   ├── benchmark.sh            # CLI entrypoint (A/B benchmark)
│   ├── report.py               # Report generator
│   └── compare.py              # Cross-repo comparison tool
├── docs/
│   ├── quickstart.md
│   ├── architecture.md
│   └── extending-skills.md
├── .github/
│   └── workflows/
│       ├── validate-on-pr.yml  # Validate repos mentioned in PRs
│       └── nightly-benchmark.yml
├── AGENTS.md                   # Instructions for AI agents working on this repo
├── CHANGELOG.md
└── pyproject.toml
```

---

## Quickstart

### 1. Install

```bash
git clone https://github.com/juliopessan/repo-validation-system.git
cd repo-validation-system
pip install -e ".[dev]"
```

### 2. Validate a repository

```bash
# Interactive mode (recommended first run)
python scripts/validate.py juliopessan/arch-review-assistant

# Non-interactive (CI mode, auto-approves plan)
python scripts/validate.py juliopessan/arch-review-assistant --ci

# With full report saved
python scripts/validate.py owner/repo --output ./reports/
```

### 3. Run an A/B benchmark

```bash
# Benchmark a skill against a set of tasks
python scripts/benchmark.py \
  --skill skills/repo-validator/SKILL.md \
  --tasks specs/benchmark-tasks.yaml \
  --n 4 \
  --output ./reports/
```

### 4. Compare multiple repos

```bash
python scripts/compare.py \
  juliopessan/arch-review-assistant \
  juliopessan/llm-observability \
  juliopessan/ai-cost-optimizer
```

---

## Validation Verdicts

| Verdict | Criteria |
|---------|---------|
| ✅ **RECOMMENDED** | Tests ≥ 90%, Coverage ≥ 70%, 0 critical vulns, build ✓ |
| ⚠️ **CONDITIONAL** | Tests ≥ 70%, Coverage ≥ 40%, no critical (high ok if documented) |
| ❌ **NOT RECOMMENDED** | Tests < 70%, or critical vuln, or build fails |
| 🚫 **UNABLE TO VALIDATE** | Install/env failure prevented execution |

---

## A/B Benchmark Publication Gate

| Runs | Status |
|------|--------|
| 1 task | 🚧 PILOT only — not publishable |
| 2 tasks | 🚧 PILOT only — not publishable |
| ≥ 3 tasks | ✅ Publishable benchmark |
| n ≥ 4 per arm | ✅ Production-grade numbers |

---

## Agent Roles

### 🎯 Orchestrator
Receives user intent, selects the right skill, coordinates subagents, assembles final report.

### 🔬 Repo Audit Agent  
Executes the 7-phase validation workflow (clone → discover → plan → install → test → report → cleanup).

### ⚗️ A/B Runner Agent
Fires parallel baseline/treatment subagents, extracts code blocks, measures LOC/files/deps, runs security checklist.

---

## Metrics Schema

All runs persist metrics to `~/.cache/repo-validator/evaluations.json` (for validation) and `~/.cache/skill-ab/evaluations.json` (for benchmarks). See `specs/metrics-schema.json` for the full schema.

---

## Contributing

See [docs/extending-skills.md](docs/extending-skills.md) for how to add new skills or extend the validation pipeline.

---

## License

MIT — see LICENSE.
