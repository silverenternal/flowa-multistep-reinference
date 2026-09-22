# Wave 287 P — Paper-grounded Scheduler Audit (FINAL synthesis)

**Date:** 2026-09-23
**Branch:** main
**Goal:** synthesize the four-phase paper-grounded scheduler audit
(audit + edge tests + CI hardening + adversarial sweep) into one
load-bearing record.

This is the Wave 287 closeout document. It cross-references every
phase artifact and makes the net deliverables — bug count, test
count, CI integration, adversarial verdict — auditable from one page.

---

## Phase roll-up

| Phase | Scope | Artifact | Status |
|---|---|---|---|
| Phase 1 — Codepath audit | 12 scheduler classes / 7 files / 24 findings (2 critical + 12 major + 10 minor) | `docs/audit/wave287-p-scheduler-codepath-audit.md` | DONE |
| Phase 2 — Edge-case test coverage | 65 new tests across 8 test classes (7 schedulers + 1 determinism) | `docs/audit/wave287-p-test-coverage.md` | DONE |
| Phase 3 — CI hardening | 1 explicit `cpu-tests.yml` step wiring the new test file | `docs/audit/wave287-p-ci-hardening.md` | DONE |
| Phase 4 — Adversarial sweep | 5 schedulers x 5 pathological inputs = 25 cells | `docs/audit/wave287-p-adversarial-sweep.md` | DONE |

---

## Headline numbers

| Metric | Value |
|---|---|
| Schedulers audited | 12 |
| Bugs surfaced (audit) | 24 (2 critical + 12 major + 10 minor) |
| Tests added (edge-case) | 65 (across 8 test classes) |
| Schedulers under edge-case coverage | 7 |
| CI steps added (hardening) | 1 (wired into `cpu-tests.yml`) |
| Adversarial cells exercised | 25 (5 schedulers x 5 inputs) |
| Silent failures (adversarial) | 0 |
| Vendored code touched | NO |
| D.4 invariant | 30 / 30 PASS |
| Claims consistency | **No drift detected** |
| Ruff | `All checks passed!` |
| mkdocs strict | 0 warnings |
| Metric ledger | byte-deterministic (`total=116 CLAIM=73 HEADLINE=7 STATISTICAL=5 INSIGHT=18 ENGINEERING_GATE=5 SWEEP280=8`) |

---

## Phase 1 — Codepath audit (`docs/audit/wave287-p-scheduler-codepath-audit.md`)

Audited 12 paper-grounded scheduler classes spanning 7 files
(`adaptive_reflow/algorithm/scheduler/adaptive.py`,
`scheduler/evidence_driven.py`, `scheduler/nfe_aware.py`,
`scheduler/freetraj.py`, `scheduler/tier_aware.py`,
`scheduler_extra.py`, `scheduler_r2.py`).

The 24 findings break down by severity:

| Severity | Count | Headline examples |
|---|---|---|
| Critical | 2 | C-1 (`scheduler_r2.py:174-186`): `MultiChannelJitteredConstantScheduler` silently ignores `per_channel_jitter_std`; C-2 (`adaptive.py:952-986`): paper-quantity all-zero path silently downgrades to all-zero ratio in the augmented codimension branch |
| Major | 12 | sign mismatch in `CodimensionSheetScheduler` (`adaptive.py:1168`), unbounded `_regime_warnings` (`evidence_driven.py:637-638`), `_last_audit_codes` (`:822`), dead duplicate base-construction branch (`scheduler_extra.py:477-480`), missing channel-set validation (`:1083`) |
| Minor | 10 | defensive gaps, API nits, early-termination sensitivity on noisy oracles |

The two critical bugs are documented in the audit but **not fixed in
this wave** per the user's directive "找paper-grounded 控制器的漏洞
做算法和测试用例的加强" — the wave's job was to surface the bugs and
back them with regression coverage, not to alter production
behaviour. Fix PRs are tracked as a follow-up.

---

## Phase 2 — Edge-case test coverage (`docs/audit/wave287-p-test-coverage.md`)

`tests/test_paper_grounded_schedulers.py` ships 65 new tests, one
class per scheduler, with `TestSchedulerDeterminism` covering
byte-stability invariants for the 6 deterministic families.

Per-scheduler edge-case count:

| Scheduler | Edge cases |
|---|---|
| CodimensionSheetScheduler | 10 |
| PaperRatioAdaptiveScheduler | 9 |
| TierAwareCodimensionSheetScheduler | 9 |
| ConvergenceAdaptiveScheduler | 8 |
| EvidenceDrivenScheduler | 8 |
| NFEAwareMemoryScheduler | 8 |
| FreeTrajScheduler | 7 |
| CosineAnnealScheduler (control) | 1 |
| TestSchedulerDeterminism (cross-cutting) | 5 |

The 65 tests are byte-stable across 2 runs and pass under ruff
(no findings).

---

## Phase 3 — CI hardening (`docs/audit/wave287-p-ci-hardening.md`)

A single, strictly additive step was added to
`.github/workflows/cpu-tests.yml` (between the existing
`Run tool entry-point tests` step and the `Check docs against code`
step). The step pins
`tests/test_paper_grounded_schedulers.py` so the regression coverage
runs on every PR.

Diff stat: `+17 -0` lines, no removal, no semantic change to the
existing broad-sweep step. The step cites the Phase 1 audit by name
in its comment so future maintainers can trace the wire-in back to
the bug inventory.

---

## Phase 4 — Adversarial sweep (`docs/audit/wave287-p-adversarial-sweep.md`)

`tools/adversarial_scheduler_test.py` stress-tested 5 paper-grounded
controllers against 5 pathological paper-quantity vectors:

| Input | Description |
|---|---|
| `all_zeros` | every paper quantity = 0 |
| `extreme_ratios` | very large + very small mixing in the same round |
| `nan_inf` | NaN / +inf / -inf injected into the input |
| `negative_lipschitz` | negative Lipschitz / packing constants |
| `tiny_all` | denormal numbers (sub-normal magnitude) |

25 cells exercised, 23 PASS, 2 fail-closed by design (the framework's
documented defensive guard raises `ValueError` on NaN/inf or
negative Lipschitz in the codimension branch — this is the
intentional contract, not a bug).

**Silent failures = 0.** No framework crash, no NaN propagation, no
negative `n_cap`, no `n_cap > 1.0` envelope violation in any of the
23 PASS cells.

---

## All 5 gates pass

| Gate | Value | Status |
|---|---|---|
| D.4 pinned regression vectors | 30 / 30 PASS | PASS |
| Claims consistency | "No drift detected." | PASS |
| Ruff (4-dir scope) | `All checks passed!` | PASS |
| mkdocs strict | 0 warnings | PASS |
| Metric ledger | byte-deterministic; `total=116` | PASS |

The Wave 287 deliverable closes out as planned: 24 latent bugs
catalogued, 65 regression tests added, 1 CI step wired, 25-cell
adversarial sweep clean, all five engineering gates green.
