# Verdict Criteria — Repo Validation System

## Repository Validation Verdicts

### ✅ RECOMMENDED

All of the following must be true:
- Test pass rate ≥ 90%
- Code coverage ≥ 70%
- Zero critical severity vulnerabilities
- Zero high severity vulnerabilities (or all have documented mitigations)
- Build succeeds
- README exists and is substantive (> 200 words)

### ⚠️ CONDITIONAL

All of the following must be true (and RECOMMENDED conditions NOT met):
- Test pass rate ≥ 70%
- Code coverage ≥ 40% (or no tests exist but build passes and linting is clean)
- Zero critical severity vulnerabilities
- High severity vulnerabilities are acceptable if: (a) they are in dev deps only, or (b) the maintainer has documented a mitigation plan
- Build succeeds or fails only on optional targets

Notes must explain *why* conditional rather than recommended, and what the user should verify before adopting.

### ❌ NOT RECOMMENDED

Any of the following is true:
- Test pass rate < 70%
- Critical severity vulnerability with no published fix
- Build fails on main/primary target
- Evidence of abandoned maintenance (no commits in > 18 months + open critical issues)

### 🚫 UNABLE TO VALIDATE

Any of the following occurred:
- Clone failed (repo not found, private without auth, network error)
- Installation failed and no partial testing was possible
- All test commands errored at the runner level (not test failures — infrastructure failures)

---

## A/B Benchmark Publication Gate

### 🚧 PILOT (not publishable)

- < 3 distinct tasks run
- Report MUST be stamped with "PILOTO — não publicável"
- User must be warned before sharing results externally

### ✅ PUBLISHABLE BENCHMARK

- ≥ 3 distinct tasks run
- Tasks include at least one "over-build trap" (complex feature where ruleset should suppress unnecessary complexity)
- Tasks include at least one "honest/minimal" task (simple task where ruleset should not cut needed code)
- n ≥ 1 per arm (POC), n ≥ 4 per arm (production-grade number)

### Reporting the honest delta

The primary metric for code-cutting rulesets MUST be **delta vs terse control** (not vs baseline), because:
- Baseline is the "unconstrained verbose" agent — any instruction reduces output vs baseline
- Control = agent with only "be concise" instruction
- True skill value = `delta_vs_control` (what the skill does *above and beyond* simply asking for brevity)

Both deltas should be reported, clearly labeled.

---

## Threshold Rationale

These thresholds reflect common open-source quality expectations:

- **90% test pass** = industry minimum for production-grade OSS (a repo with 1 in 10 tests failing is not production-ready)
- **70% coverage** = widely cited minimum (OWASP, Google's eng guidelines) for meaningful test suites
- **Critical vuln = block** = a known exploitable vulnerability with a public CVE and available fix should never be conditional
- **3 task minimum** = single-task A/B results have high variance; 3 tasks with different "trap" profiles give a much more honest signal
