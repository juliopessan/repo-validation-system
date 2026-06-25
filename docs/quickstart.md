# Quickstart Guide

## Prerequisites

- Python 3.11+
- Git
- GitHub account (for pushing the project)

## Installation

```bash
git clone https://github.com/juliopessan/repo-validation-system.git
cd repo-validation-system
pip install -e ".[dev]"
```

## Validate your first repository

```bash
python scripts/validate.py juliopessan/arch-review-assistant
```

You'll see:
1. **Clone** — the repo is cloned to `~/.cache/repo-validator/repos/`
2. **Discovery** — stack, language, package manager detected
3. **Test Plan** — a structured plan is presented for your approval
4. **Execution** — tests run in isolation
5. **Report** — verdict + metrics printed, saved to `.validator-results/REPORT.md`
6. **Cleanup** — you decide whether to keep the cache

## CI mode (no prompts)

```bash
python scripts/validate.py owner/repo --ci --no-cleanup-prompt
```

## Compare multiple repos

```bash
# After validating several repos:
python scripts/compare.py juliopessan/arch-review-assistant juliopessan/llm-observability

# See all past evaluations:
python scripts/compare.py --all

# See last 5:
python scripts/compare.py --last 5
```

## Run A/B benchmark (via Claude agent)

The A/B benchmark requires a Claude agent. Open a conversation with Claude and invoke the `skill-ab-benchmark` skill:

```
Roda o benchmark A/B da skill skills/repo-validator/SKILL.md com 3 tarefas de validação.
```

The orchestrator agent will:
1. Read the skill
2. Propose tasks (including trap tasks)
3. Wait for your approval
4. Fire parallel baseline/treatment subagents
5. Generate an HTML report in `~/.cache/skill-ab/`

## GitHub Actions

Two workflows are included:

- **validate-on-pr.yml** — runs lint, tests, and spec integrity on every PR; can validate a specific repo via `workflow_dispatch`
- **nightly-benchmark.yml** — nightly self-check + health check of configured repos

Trigger manual validation from GitHub UI:
> Actions → Validate Repo on PR → Run workflow → Enter repo name
