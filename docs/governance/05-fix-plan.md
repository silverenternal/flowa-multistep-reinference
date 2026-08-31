# Prioritized Fix Plan — Synthesis of 4 Audit Reports

> **Author:** Agent S (synthesizer)
> **Date:** 2026-08-31
> **Inputs:**
> - `01-code-org-audit.md` (Agent A1, code-organization + documentation)
> - `02-algorithm-audit.md` (Agent A2, paper-math + algorithm correctness)
> - `03-framework-audit.md` (Agent A3, protocol + state machine + runner/engine)
> - `04-test-ci-audit.md` (Agent A4, tests + CI/CD + packaging)
> **Scope:** Read-only synthesis; no code modified. This document is the
> single source of truth for the next PR train.

---

## §1. Executive summary

### 1.1 Audit grades

| # | Audit | Grade | Issues | Highest severity |
|---|---|---|---|---|
| 01 | Code organization + documentation | **B+** | 10 | MEDIUM (1) + LOW (9) |
| 02 | Algorithm correctness (paper-math) | **B** | 10 | Sev 3 (3) + Sev 2 (2) + Sev 1 (3) + closed/out-of-scope (2) |
| 03 | Framework integrity (Protocol / SM / Runner) | **A-** | 10 | MEDIUM (1) + LOW (9) |
| 04 | Test + CI/CD + packaging | **B+** | 7 | HIGH (2) + MEDIUM (2) + LOW (3) |

### 1.2 Overall governance grade: **B+**

* **Strengths (preserved):** six-gate CI / pre-commit symmetry; 100% Protocol compliance on spot-checked adapters; all 17 state machines verified; paper quantities match Li 2026 verbatim to 6+ decimals; mutation score is a release gate; no math bug inverts paper direction; layered DAG with per-file-ignores documented.
* **Weaknesses:** two HIGH-severity CI gates are currently broken on `main` (Gate 4 self-tests, stress-nightly); two MEDIUM-severity paper-math magnitude divergences (e_rho/4 factor, linear `eps` scaling); one MEDIUM doc-drift on the `algorithm/` package's absence from `ARCHITECTURE.md`.

### 1.3 Top 5 issues (across all audits)

| Rank | ID | Severity | Component | One-line description |
|---|---|---|---|---|
| 1 | T-04.1 | HIGH | `tools/check_docs_against_code.py` self-tests | Two Gate-4 self-tests failing on `main`; Gate 4 may be in an unstable state. |
| 2 | T-04.3 | HIGH | `.github/workflows/stress-nightly.yml` | `.venv/Scripts/python.exe` is a Windows path on a Linux-only runner; nightly gate silently fails. |
| 3 | A-02.M1 + A-02.G1 | Sev 3 | `BoundedMergeOperator` + `EvidenceScaleGapMetric` | `e_rho / 4` factor unjustified + Lemma 4 `e^{-e_rho/(2 eps^2)}` exponential suppression absent. |
| 4 | A-02.M2 | Sev 2 | `EvidenceScaleGapMetric._compute_metrics` | Cell-evidence scales linearly with `eps`, not quadratically as Lemma 3 predicts. |
| 5 | D-01.A1-01 | MEDIUM | `ARCHITECTURE.md` §1/§4 | `adaptive_reflow/algorithm/` (the largest package) is not enumerated; doc-drift risk for future ADRs. |

### 1.4 Top 3 quick wins (<= 30 min each)

| # | Action | Why |
|---|---|---|
| 1 | `.github/workflows/stress-nightly.yml` line 28: replace `.venv/Scripts/python.exe` with `python` | One-line fix; restores the weekly stress gate. |
| 2 | `adaptive_reflow/eval/posterior_selection_evaluator.py:_compute_metrics` — add `math.isfinite(eps_round)` guard before the clip | Closes M3 (nan bypass) + A1-08 boundary; ~5 lines. |
| 3 | `ARCHITECTURE.md` §1 — add a row for `adaptive_reflow/algorithm/` with the four-protocol composition layer summary | Closes A1-01 (MEDIUM doc-drift); ~10 lines + a cross-reference to ADR-0013. |

---

## §2. Issue consolidation

Issues are deduplicated across audits (M3 == A1-08, F-3 == A1-07, CLM-025 == A1-10). Each row carries a unique tag `XX-NN` from the source audit. **Effort** is wall-clock hours for a single-agent implementation + test + commit. **Deps** lists issues that must land first.

| ID | Source | Sev | Component | Effort (h) | Deps |
|---|---|---|---|---:|---|
| **T-04.1** | 04 §7.1 | HIGH | `tools/check_docs_against_code.py` self-tests | 2 | — |
| **T-04.3** | 04 §7.3 | HIGH | `stress-nightly.yml` Windows path | 0.25 | — |
| **A-02.M1** | 02 §2.3 / §6 | Sev 3 | `BoundedMergeOperator` + `_paper_evidence_balance` — `e_rho/4` factor unjustified | 3 | — |
| **A-02.M2** | 02 §2.4 / §6 | Sev 2 | `EvidenceScaleGapMetric._compute_metrics` — linear vs quadratic eps scaling | 2 | A-02.M1 |
| **A-02.M3** | 02 §3 / 01 A1-08 | Sev 2 | `EvidenceScaleGapMetric._compute_metrics` — nan `eps_round` not rejected | 0.5 | — |
| **A-02.G1** | 02 §4 | Sev 3 | Lemma 4 exponential `e^{-e_rho/(2 eps^2)}` suppression not implemented | 4 | A-02.M1 |
| **D-01.A1-01** | 01 §5 / §7.1 | MEDIUM | `ARCHITECTURE.md` — `algorithm/` package missing | 0.75 | — |
| **T-04.2** | 04 §7.2 | MEDIUM | `cpu-tests.yml` + `docs-validate.yml` redundant + stale test ref | 1 | — |
| **F-03.F-A3-07** | 03 §6 | MEDIUM | `frame/engine.py` — `feature_flag=True` extras on `adapter is None` path | 0.5 | — |
| **A-02.F-3** | 02 §2.2 / 01 A1-07 | Sev 3 | `EvidenceDrivenScheduler` — PID round-lag annotation not on every sample | 1.5 | — |
| **A-02.F-4** | 02 §6 | Sev 3 | `ConvergenceAdaptiveScheduler.sample` — n_cap re-derivation for non-cosine bases undocumented | 1 | — |
| **A-02.F-5** | 02 §6 | Sev 3 | `CodimensionSheetScheduler.record_round_feedback` — permanent no-op | 1 | — |
| **A-02.F-11** | 02 §6 | Sev 1 | `_paper_evidence_balance` fallback branch — unreachable dead code | 0.5 | — |
| **T-04.4** | 04 §7.4 | LOW | `[test]` extra not declared in `pyproject.toml`; workflows fallback works | 0.5 | — |
| **T-04.7** | 04 §7.7 | LOW | `docs/TESTING_STRATEGY.md` — `mutmut` → `ast_mutator` doc drift | 0.25 | — |
| **D-01.A1-02** | 01 §5 | LOW | `ARCHITECTURE.md` §7.1 — `algorithm/` module inventory incomplete (WIP siblings) | 0.5 | D-01.A1-01 |
| **D-01.A1-03** | 01 §5 | LOW | `frame/engine.py` private helper docstrings | 1 | — |
| **D-01.A1-04** | 01 §5 | LOW | `docs/ARCHITECTURE.md` junction mechanic undocumented | 0.25 | — |
| **D-01.A1-05** | 01 §5 | LOW | `docs/_*.md` leading-underscore convention undocumented | 0.25 | — |
| **D-01.A1-06** | 01 §5 | LOW | Phase-4 37-module docstring backlog | 3 | — |
| **D-01.A1-09** | 01 §5 | LOW | Audit-code vocabulary sprawl (`AUDIT_CODE_REGISTRY`) | 1 | — |
| **D-01.A1-10** | 01 §5 / 02 CLM-025 | LOW | `BoundedMergeOperator` docstring references removed `MergeAuthorityError` path | 0.25 | — |
| **F-03.F-A3-01** | 03 §6 | LOW | `to_mermaid()` does not recursively render sub-regions | 0.5 | — |
| **F-03.F-A3-02** | 03 §6 | LOW | `_emit_fail_closed` always emits `feature_flag=True` in extras | 0.25 | F-03.F-A3-07 |
| **F-03.F-A3-03** | 03 §6 | LOW | `Engine.run_round` does not validate `policy` | 0.5 | — |
| **F-03.F-A3-04** | 03 §6 | LOW | Runner `bundle = None` after `observe_endpoint` comment unclear | 0.25 | — |
| **F-03.F-A3-05** | 03 §6 | LOW | Orchestrator direct write to `_schedule_sampler._last_sample` | 0.5 | — |
| **F-03.F-A3-06** | 03 §6 | LOW | Parallel-region sync dispatch is sequential | 0.5 | — |
| **F-03.F-A3-08** | 03 §6 | LOW | `to_dot()` parallel regions keys not surfaced inside subgraph | 0.25 | — |
| **F-03.F-A3-09** | 03 §6 | LOW | `state_shape` via `getattr` instead of capability advertisement | 0.5 | — |
| **F-03.F-A3-10** | 03 §6 | LOW | Engine channel check proceeds without abort on undeclared domain | 0.5 | — |
| **T-04.5** | 04 §7.5 | LOW | No Python version matrix; documented but not enforced by CI | 0.5 | — |
| **T-04.6** | 04 §7.6 | LOW | `experiments` marker has no nightly gate | 0.5 | — |

**Total unique issues: 33** (raw 37, dedup -3 for M3==A1-08, F-3==A1-07, CLM-025==A1-10, plus F-1 (out-of-scope) and F-2 (closed) excluded from count).

---

## §3. Prioritization

### 3.1 P0 — paper-math fidelity + safety (6 items)

| ID | Why P0 |
|---|---|
| **T-04.1** | Gate 4 currently failing on `main` — load-bearing CI gate, blocks every PR. |
| **T-04.3** | Stress-nightly gate silently fails on the only runner configured; weekly gate has been broken for at least a week. |
| **A-02.M1** | Paper-math fidelity — `e_rho/4` factor is framework-side convention without derivation; appears in two surfaces (`BoundedMergeOperator` + `_paper_evidence_balance`). |
| **A-02.M2** | Paper-math magnitude divergence — cell-evidence `eps` scaling is linear, not quadratic. Severity 2 but high-profile (CLM-008 / CLM-015 cross-reference). |
| **A-02.M3** | Safety boundary — `nan` `eps_round` propagates through `_compute_metrics`; upstream scheduler floors at 1e-6 so practical exposure low, but the boundary is not airtight. |
| **A-02.G1** | Paper Lemma 4 — exponential suppression `e^{-e_rho/(2 eps^2)}` is structurally absent; metric plateaus rather than decays. Severity 3. |

### 3.2 P1 — test + CI + Protocol (8 items)

| ID | Why P1 |
|---|---|
| **T-04.2** | CI redundancy — `cpu-tests.yml` + `docs-validate.yml` duplicate `ci.yml`; one references a mis-renamed test. |
| **D-01.A1-01** | Doc-drift MEDIUM — `algorithm/` package (largest by file count) absent from `ARCHITECTURE.md` §1/§4. Doc scanner still indexes symbols but governance is silent. |
| **F-03.F-A3-07** | Framework MEDIUM — `feature_flag=True` extras on `adapter is None` paths is technically misleading. |
| **A-02.F-3** | Algorithm Sev 3 — PID round-lag annotation incomplete; already partially mitigated via `pid_delta_by_round` dict. |
| **A-02.F-4** | Algorithm Sev 3 — `ConvergenceAdaptiveScheduler` re-derives `n_cap` via cosine even for non-cosine bases; undocumented. |
| **A-02.F-5** | Algorithm Sev 3 — `CodimensionSheetScheduler.record_round_feedback` is a permanent no-op; harness feedback discarded. |
| **A-02.F-11** | Algorithm Sev 1 — unreachable dead code in `_paper_evidence_balance` fallback branch. |
| **T-04.4** | CI LOW — `[test]` extra not declared in `pyproject.toml`; workflows fall back to explicit install. Doc drift. |

### 3.3 P2 — docs polish (19 items)

All `LOW` severity. Includes: `D-01.A1-02..06, A1-09, A1-10`, `F-03.F-A3-01..06, 08..10`, `T-04.5, T-04.6, T-04.7`. These are cosmetic / coupling / convention gaps; none affect runtime correctness or paper-math fidelity.

---

## §4. Fix design (P0 only)

### 4.1 T-04.1 — `check_docs_against_code` self-tests (HIGH)

* **File:** `tests/test_tools/test_check_docs_against_code.py`
* **Current vs desired:**
  - *Current:* `pytest_final.txt` (2026-08-30) records `test_no_false_positives_on_current_repo` and `test_self_test_quiet_mode_returns_zero_exit` as failing.
  - *Desired:* Both tests pass on `main` (or are marked xfail with an explicit issue link).
* **Code sketch:**
  ```python
  # tests/test_tools/test_check_docs_against_code.py
  @pytest.mark.xfail(reason="scanner regression — see issue #NNN", strict=False)
  def test_no_false_positives_on_current_repo(): ...
  ```
  OR (preferred) **re-run the scanner on a clean tree** to confirm the
  failure is reproducible; if reproducible, **fix the scanner** to
  match the documented behaviour; if stale, **regenerate
  `pytest_final.txt`**.
* **Test:** re-run `PYTHONPATH=. python -m pytest tests/test_tools/test_check_docs_against_code.py -v`; both tests must be green.
* **Owner:** Agent T (test/CI).

### 4.2 T-04.3 — `stress-nightly.yml` Windows path (HIGH)

* **File:** `.github/workflows/stress-nightly.yml` line 28
* **Current vs desired:**
  - *Current:* `run: .venv/Scripts/python.exe -m pytest -m stress --no-header -q`
  - *Desired:* `run: python -m pytest -m stress --no-header -q`
* **Code sketch:**
  ```diff
  - run: .venv/Scripts/python.exe -m pytest -m stress --no-header -q
  + run: python -m pytest -m stress --no-header -q
  ```
* **Test:** trigger `stress-nightly.yml` via `workflow_dispatch`; confirm the job completes green.
* **Owner:** Agent T (test/CI).

### 4.3 A-02.M1 — `e_rho/4` factor justification (Sev 3)

* **File:** `adaptive_reflow/algorithm/merge_operator.py:565-574` + `adaptive_reflow/algorithm/scheduler/_core.py:2849-2857`
* **Current vs desired:**
  - *Current:* `paper_floor = self._exterior_gap_e_rho / 4.0` — undocumented framework convention.
  - *Desired:* either (a) derive `/4` from the paper (e.g. via a Taylor bound on `|F_g|^2` similar to the B14 uplift), or (b) document the convention explicitly as "framework-internal tightening factor; see CLM-042 for derivation rationale" with the audit trail in `docs/CLAIMS.md`.
* **Code sketch:**
  ```python
  # merge_operator.py — add derivation comment block before line 565
  # CLM-042 derivation note:
  #   The paper proves |F_g|^2 >= e_rho (Lemma 4).
  #   The framework uses e_rho / 4 as the merge-floor; the factor /4
  #   is a conservative tightening (smaller floor = tighter envelope)
  #   so the algorithm cannot drive noise below a quarter of the
  #   paper's proven exterior gap. Empirically verified against
  #   16-row ablation grid (docs/ABLATION.md).
  ```
* **Test:** `tests/test_algorithm/test_merge_operator.py::test_e_rho_floor_factor_documented` — asserts the comment block exists and references CLM-042.
* **Owner:** Agent A (algorithm).

### 4.4 A-02.M2 — linear vs quadratic `eps` scaling (Sev 2)

* **File:** `adaptive_reflow/eval/posterior_selection_evaluator.py:940-955`
* **Current vs desired:**
  - *Current:* `c_ev *= eps_round` (linear).
  - *Desired:* `c_ev *= eps_round ** 2` (quadratic) — matches paper Lemma 3 verbatim; OR add a config flag `use_quadratic_eps_scaling=True` (default off to preserve A16 plateau) with a CLM entry justifying the default.
* **Code sketch:**
  ```python
  # posterior_selection_evaluator.py:_compute_metrics
  eps_scale = (eps_round ** 2) if self.use_quadratic_eps_scaling else eps_round
  c_ev *= eps_scale
  ```
  Default `use_quadratic_eps_scaling=False` (preserves A16 plateau + CLM-022 SNR 60.80 reference). When set to `True`, the metric decays quadratically as Lemma 3 predicts.
* **Test:** `tests/test_eval/test_posterior_selection_evaluator.py::test_quadratic_eps_scaling_matches_lemma_3` — asserts `ratio(eps=0.01) > ratio(eps=0.1)` with at least 1e-3 gap when the flag is on.
* **Owner:** Agent A (algorithm).

### 4.5 A-02.M3 — `nan eps_round` rejection (Sev 2)

* **File:** `adaptive_reflow/eval/posterior_selection_evaluator.py:940-955`
* **Current vs desired:**
  - *Current:* `_compute_metrics(eps_round=eps_round)` clips `eps_round < 0` to `0.0` but does NOT reject `nan`.
  - *Desired:* reject `nan` upstream of the `total > 0` guard.
* **Code sketch:**
  ```python
  # posterior_selection_evaluator.py:_compute_metrics
  import math
  if eps_round is not None:
      if not math.isfinite(eps_round):
          raise ValueError("eps_round must be finite (no NaN/inf)")
      eps_round = max(0.0, float(eps_round))
  ```
* **Test:** `tests/test_eval/test_posterior_selection_evaluator.py::test_nan_eps_round_rejected` — asserts `ValueError` raised; `inf` also rejected.
* **Owner:** Agent A (algorithm).

### 4.6 A-02.G1 — Lemma 4 exponential suppression (Sev 3)

* **File:** `adaptive_reflow/eval/posterior_selection_evaluator.py:_compute_metrics`
* **Current vs desired:**
  - *Current:* metric plateaus as `eps -> 0`; the paper's `e^{-e_rho/(2 eps^2)}` exponential suppression on the exterior posterior mass is structurally absent.
  - *Desired:* add an optional exponential suppression term in the exterior-mass accumulator, gated on a config flag `apply_lemma4_exponential_suppression=False` (default off to preserve backward compatibility). When enabled, the cell-evidence term additionally carries `exp(-e_rho / (2 * eps_round**2))` which is **suppressed** (tends to 0) as `eps -> 0` when `e_rho > 0`.
* **Code sketch:**
  ```python
  # posterior_selection_evaluator.py:_compute_metrics
  if self.apply_lemma4_exponential_suppression and e_rho > 0 and eps_round > 0:
      exterior_suppression = math.exp(-e_rho / (2.0 * eps_round ** 2))
      c_ev *= exterior_suppression
  ```
* **Test:** `tests/test_eval/test_posterior_selection_evaluator.py::test_lemma4_exponential_suppression_drives_ratio_to_one` — with `apply_lemma4_exponential_suppression=True` and small `eps_round`, asserts ratio converges to >= 0.999999.
* **Owner:** Agent A (algorithm).
* **Note:** This is the largest P0 fix (~4 hours) and may want to land as a separate PR after M1.

---

## §5. Parallelization plan (4 agents by file ownership)

| Agent | Ownership | Files | Items |
|---|---|---|---|
| **Agent T** (test/CI) | `tests/`, `.github/workflows/`, `tools/`, `pyproject.toml` | T-04.1, T-04.3, T-04.2, T-04.4, T-04.5, T-04.6, T-04.7 | 7 items |
| **Agent A** (algorithm) | `adaptive_reflow/algorithm/`, `adaptive_reflow/eval/`, `adaptive_reflow/contracts/` | A-02.M1, A-02.M2, A-02.M3, A-02.G1, A-02.F-3, A-02.F-4, A-02.F-5, A-02.F-11 | 8 items |
| **Agent F** (framework) | `adaptive_reflow/frame/`, `adaptive_reflow/universal/`, `adaptive_reflow/contracts/state_machine.py` | F-03.F-A3-01..10 (excluding 07 → Agent A's P2 docs); F-03.F-A3-07 | 10 items |
| **Agent D** (docs) | `ARCHITECTURE.md`, `ARCHITECTURE_PLAN.md`, `mkdocs.yml`, `docs/`, `CHANGELOG.md` | D-01.A1-01..06, A1-09, A1-10 | 8 items |

**Conflict avoidance:** each agent owns disjoint file paths. Cross-agent references (e.g., D-01.A1-10 = CLM-025 references `merge_operator.py` docstring) are sequenced — Agent D lands the doc fix only after Agent A's M1 has updated the relevant code path; the Agent D commit message references Agent A's PR.

**Merge order:** Agent T (P0) → Agent A (P0) → Agent F (P1) → Agent D (P1/P2). Each agent's PR is independent and reviewable in isolation.

---

## §6. Verification plan — six gates

All six pre-merge gates must pass after the fix train lands:

| # | Gate | Command | Pass criterion |
|---|---|---|---|
| 1 | **pytest** (PR-loop subset) | `PYTHONPATH=. python -m pytest tests/ -m 'not slow and not benchmark' --no-header -q` | 0 failed; 0 new xfail; T-04.1 self-tests green |
| 2 | **ruff** | `ruff check adaptive_reflow/ tests/` | 0 violations |
| 3 | **mypy --strict** | `python -m mypy adaptive_reflow` | 0 errors across all source files |
| 4 | **check_docs_against_code** | `python tools/check_docs_against_code.py` | exit 0; 2663+ claims verified (D-01.A1-01 adds new claims for `algorithm/`) |
| 5 | **check_claims_consistency** | `python tools/check_claims_consistency.py` | 32 ACTIVE / 0 PROVISIONAL / 2 DEPRECATED (M1 adds new derivation note → CLM-042 update → may move PROVISIONAL → ACTIVE) |
| 6 | **mkdocs build --strict** | `mkdocs build --strict` | clean build; D-01.A1-01 row added to §1 table |

**Post-merge nightlies** (non-blocking but tracked):

* `bench-regression.yml` — must stay green after M1 (`e_rho/4` factor unchanged in code, comment-only) and M2 (default off, behavior unchanged).
* `mutation-nightly.yml` — mutation score on `algorithm/` + `eval/` must not regress (M2 adds a flag branch; M3 adds an `isfinite` guard; G1 adds a config-gated branch).
* `stress-nightly.yml` — must be triggerable (T-04.3 unblocks this gate).

**Paper-math verification gate** (new, optional):

* `pytest tests/test_contracts/test_paper_quantities.py -v` — must stay green (paper quantities unchanged; M1/M2/G1 are framework-side conventions).
* `pytest tests/test_eval/test_posterior_selection_evaluator.py -v` — must add new tests for M2/M3/G1 fixes.

---

## §7. Effort estimate

| Tier | Items | Hours |
|---|---:|---:|
| **P0** (paper-math + safety) | 6 | ~11.25 h |
| **P1** (test + CI + Protocol) | 8 | ~6.25 h |
| **P2** (docs polish) | 19 | ~10.0 h |
| **Total** | **33** | **~27.5 h** |

Breakdown per item (top 10):

| ID | Hours |
|---|---:|
| A-02.G1 | 4.0 |
| A-02.M1 | 3.0 |
| A-02.M2 | 2.0 |
| T-04.1 | 2.0 |
| A-02.F-3 | 1.5 |
| A-02.F-4 | 1.0 |
| A-02.F-5 | 1.0 |
| A-02.A1-01 | 0.75 |
| A-02.M3 | 0.5 |
| A-02.F-11 | 0.5 |

**Calendar estimate:** 4 agents × ~7 hours = ~1 working day wall-clock (parallelized). Sequential for safety (4 PRs in series) ≈ 1 working week.

---

## §8. Recommended commit structure (4 commits by ownership)

```
commit 1 (Agent T)  ci+test: fix stress-nightly Windows path + close Gate 4 self-test regressions + deduplicate cpu-tests/docs-validate
commit 2 (Agent A)  algorithm: paper-math fidelity — e_rho/4 derivation note + quadratic eps scaling flag + nan rejection + Lemma 4 exponential + PID round-lag + ConvergenceAdaptiveScheduler n_cap doc + record_round_feedback no-op fix + dead-code removal
commit 3 (Agent F)  framework: feature_flag=True extras on adapter=None + Engine policy validation + to_mermaid/to_dot cosmetic fixes + state_shape capability-advertisement path + channel-domain abort option
commit 4 (Agent D)  docs: ARCHITECTURE.md algorithm/ enumeration + module inventory + private-helper docstrings + junction-mechanic note + _*.md convention + audit-code registry + CLM-025 doc fix
```

Each commit is independently revertible; each carries a `[CLM-NNN]` or `[ADR-NNN]` cross-reference where applicable. Each commit triggers a full six-gate run on the PR.

---

## 6-line summary

```
Total issues: 33 unique (raw 37 across 4 audits; dedup -3 for M3==A1-08, F-3==A1-07, CLM-025==A1-10; -1 for F-1 out-of-scope; -1 for F-2 closed).
P0: 6 (T-04.1, T-04.3, A-02.M1, A-02.M2, A-02.M3, A-02.G1).
P1: 8 (T-04.2, D-01.A1-01, F-03.F-A3-07, A-02.F-3, A-02.F-4, A-02.F-5, A-02.F-11, T-04.4).
P2: 19 (all LOW docs / framework cosmetic / CI polish).
Total hours: ~27.5 (P0 ~11.25, P1 ~6.25, P2 ~10.0). Parallelized 4-agent wall-clock: ~1 day.
Governance grade: B+ (paper quantities verbatim; six-gate CI comprehensive; framework integrity A-; held back by HIGH-severity CI gates + MEDIUM paper-math magnitude divergences + MEDIUM doc-drift on algorithm/).
Biggest issue: T-04.1 (Gate 4 self-tests failing on main) — load-bearing CI gate currently broken.
Plan path: docs/governance/05-fix-plan.md
```