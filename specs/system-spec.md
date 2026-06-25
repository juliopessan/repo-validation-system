# System Specification — Repo Validation System

**Version:** 1.0.0  
**Status:** Production-Ready  
**Last updated:** 2026-06-25

---

## 1. Purpose

The Repo Validation System provides a reproducible, agent-driven pipeline for:

1. **Repository health auditing** — clone, analyze, test, score, and report on any GitHub repository
2. **Skill A/B benchmarking** — measure the quantified impact of a Claude skill/ruleset on code generation quality

---

## 2. System Components

### 2.1 Skills

Skills are the behavioral contracts for agent execution. They live in `skills/` and are consumed by agents and CLI scripts.

| Skill | Version | Description |
|-------|---------|-------------|
| `repo-validator` | 1.0 | 7-phase repository validation pipeline |
| `skill-ab-benchmark` | 1.0 | Controlled A/B benchmark for skill/ruleset impact measurement |

### 2.2 Agents

Agents are prompt templates that specialize Claude for specific tasks within the pipeline.

| Agent | Role | Consumes |
|-------|------|---------|
| `orchestrator` | Routes user intent, coordinates subagents | Both skills |
| `repo-audit-agent` | Executes full repo validation | `repo-validator` |
| `ab-runner-agent` | Runs A/B benchmarks | `skill-ab-benchmark` |

### 2.3 Scripts

Python/Bash scripts implement the skills as executable tools:

| Script | Purpose |
|--------|---------|
| `validate.py` | CLI wrapper for repo-validator |
| `benchmark.py` | CLI wrapper for skill-ab-benchmark |
| `compare.py` | Cross-repo comparison from evaluations history |
| `report.py` | Standalone report generator from saved metrics |

---

## 3. Repo Validator — Phase Specification

### Phase 0: Environment Setup
- Ensure `~/.cache/repo-validator/repos/` exists
- Ensure `~/.cache/repo-validator/evaluations.json` exists (create `[]` if not)

### Phase 1: Clone & Cache
- Normalize input (owner/repo, URL, short name)
- Check cache; offer reuse/update/reclone
- `git clone --depth 1`
- Measure size; warn if > 500MB

### Phase 2: Discovery
- Detect stack (language, package manager, test framework, web framework)
- Read README.md, CONTRIBUTING.md, ARCHITECTURE.md, CLAUDE.md/AGENTS.md
- Map directory structure (config files, test dirs, source dirs)
- Compute code stats (file count, LOC approx)
- Summarize for user

### Phase 3: Test Plan [HUMAN GATE]
Generate a structured plan covering:
- Environment (language, pm, test framework, isolation method)
- Installation steps
- Tests to run (lint, unit, build, e2e if applicable, coverage, security audit)
- Metrics to collect

**STOP — present plan, wait for explicit approval before continuing.**

### Phase 4: Installation (Isolated)
- Python: `venv` + `pip install`
- Node: detect `pnpm`/`yarn`/`npm`, install locally
- Go: `go mod download`
- Rust: `cargo build`
- **NEVER** install globally; **NEVER** modify system

### Phase 5: Execution
- Create `.validator-results/`
- Execute each approved test step
- Capture stdout+stderr to `.validator-results/{name}.log`
- Extract metrics: pass rate, coverage %, timing, build success, lint errors, vuln count

### Phase 6: Report
Generate `REPORT.md` + present in chat. Persist metrics to `evaluations.json`.

**Verdict criteria:**

| Verdict | Tests | Coverage | Vulns | Build |
|---------|-------|---------|-------|-------|
| RECOMMENDED | ≥ 90% | ≥ 70% | 0 critical | ✓ |
| CONDITIONAL | ≥ 70% | ≥ 40% | no critical | - |
| NOT RECOMMENDED | < 70% | any | critical | any |
| UNABLE TO VALIDATE | install/env failure | - | - | - |

### Phase 7: Cleanup [HUMAN GATE]
Ask: keep cache or remove? Execute accordingly.

---

## 4. A/B Benchmark — Phase Specification

### Phase 0: Plan Approval [HUMAN GATE]
Present to user (must be approved before proceeding):
- Ruleset / skill target
- Tasks list (≥ 3 for publishable; < 3 = pilot only)
- n runs per arm (1 = POC, 4 = robust)
- Estimated cost

**STOP — wait for explicit "ok" before continuing.**

### Phase 1: Dispatch Subagents
- Launch N agents in parallel (`Agent` tool, `model: sonnet`, `run_in_background: true`)
- N = tasks × 2 arms × n
- Baseline prompt: senior dev, no ruleset
- Treatment prompt: same spec + ruleset prefixed
- Output format: `=== FILE: path ===` blocks

### Phase 2: Extract Files
- Parse transcript JSONL
- Extract only `role == "assistant"` content blocks
- Parse `=== FILE: path ===` blocks by header (not END marker — unreliable)
- Strip code fences from baseline output
- Write to `~/.cache/skill-ab/{run-name}/{task}/{arm}/run{k}/`

### Phase 3: Measure
- LOC: non-empty lines in code files (by script, not by eye)
- Files: total file count
- Deps: new packages added
- Aggregate per (task, arm): mean across n runs

### Phase 4: Security Checklist (Qualitative)
For each treatment output verify:
- [ ] Input validation at trust boundaries maintained
- [ ] Error handling that prevents data loss maintained
- [ ] Accessibility (label/aria) maintained where applicable
- [ ] At least one runnable test/check for non-trivial logic

Flag any case where treatment cut safety along with code.

### Phase 5: Report
- Generate HTML from `report-template.html` → `{ROOT}/report.html`
- Generate `{ROOT}/REPORT.md`
- Persist to `~/.cache/skill-ab/evaluations.json`
- Present summary in chat

**UI naming rules (NEVER use internal terms in rendered HTML):**
- `baseline` → "Agente solto"
- `treatment` → "Com a skill"
- `terse` (prose control) → 'Só "seja breve"'

### Phase 6: Cleanup [HUMAN GATE]
Ask: keep `{ROOT}` or remove?

---

## 5. Metrics Schema

See `specs/metrics-schema.json` for the full JSON Schema definition.

### Repo Validator Entry

```json
{
  "repo": "owner/repo",
  "date": "ISO-8601",
  "commit": "abc1234",
  "verdict": "RECOMMENDED | CONDITIONAL | NOT RECOMMENDED | UNABLE TO VALIDATE",
  "metrics": {
    "tests_pass": 42,
    "tests_total": 45,
    "coverage": 87.3,
    "build_success": true,
    "lint_errors": 2,
    "vulns": 0,
    "test_time_seconds": 3.2,
    "repo_size_mb": 12.5,
    "code_files": 38
  },
  "strengths": ["..."],
  "weaknesses": ["..."]
}
```

### A/B Benchmark Entry

```json
{
  "ruleset": "skill-name",
  "date": "ISO-8601",
  "model": "claude-sonnet-4-6",
  "mode": "benchmark | pilot",
  "n": 4,
  "tasks": ["task1", "task2", "task3"],
  "metric": "LOC | words",
  "mean_delta_vs_control": -32.1,
  "mean_delta_vs_baseline": -41.5,
  "safety_notes": "..."
}
```

---

## 6. Security Constraints

1. **ISOLATION TOTAL** — never install anything globally; never modify system
2. **HUMAN GATES** — Phases 3 (validator) and 0 (benchmark) always pause for approval
3. **CLEANUP always offered** — always ask about removal
4. **LOGS preserved** — all test outputs saved to `.validator-results/`
5. **REPRODUCIBLE** — commit hash and tool versions recorded
6. **NEVER execute repo code outside sandbox/venv**
7. **NEVER run install scripts without reading them first**
8. **CACHE isolated** — all work in `~/.cache/`, never pollutes working directory

---

## 7. Extension Points

- New languages: add detection rules to Phase 2 of `repo-validator/SKILL.md`
- New metrics: add to `specs/metrics-schema.json` + update report template
- New skill types: add handling to Phase 5 metric detection of `skill-ab-benchmark/SKILL.md`
- New verdict tiers: update `specs/verdict-criteria.md`
