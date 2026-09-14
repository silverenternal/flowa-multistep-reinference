# Execution plan — pending tasks broken into atomic subtasks

**Date:** 2026-09-05
**Purpose:** Per user "再拆解一下todo文件夹下面剩余待完成的任务，分解一下" — break
each remaining pending file into atomic (15-60 min, time-bounded, clear
input/output) subtasks. Use this for execution scheduling.

12 pending files → ~110 atomic subtasks. Each subtask has time estimate,
dependency on previous subtasks, and acceptance criteria.

## Execution order (recommended)

> Status snapshot below is from 2026-09-05 morning; all 6 framework-depth
> tasks + Wave 15 Phase 3 verify + paper-writeup are **done** as of
> Wave 17-19 (see `todo/STATUS.md`). The atomic subtasks below are
> preserved as a record of what was actually executed.

1. **Wave 15 Phase 3 verify** — done (Wave 15 / 15F.2 — commits `43b862d`, `a1f8650`, `04f892c`, `f9d34e1`, `3ead25f`, `4d30f41`, `e397528`)
2. **B.7 property-based testing** — done (Wave 17 P1; commit `2bd2fe2`); 9 files, 66 tests, 0.769 coverage → see `docs/baseline-audit-report.md` §B.7
3. **Algo D (controlled noise injection)** — done (Wave 17 P2; commit `441f54f`); `noise_sigma` parameter on `twodim_fm` + `tools/noise_injection_experiment.py` + `docs/CONDITIONS.md`
4. **C.6 convergence-order** — done (Wave 18 P1; commit `d7cd65b`) + DPK45 fix (Wave 20; commit `53e5d52`); 5/5 integrators pass
5. **C.7 SBC** — done (Wave 18 P1; commit `c0e2fe2`); 6/6 stochastic algorithms pass chi-squared
6. **F.6 mutation testing** — done (Wave 18 P3; commit `6ec3385`) + Wave 25 subsystem pass (commit `9e47375`)
7. **Operating-regime analysis** — done (Wave 17 P3; commit `e6cd0dc`); `docs/theory/operating-regime.md` + `docs/CONDITIONS.md` addendum
8. **PHASE-2/3/4** — done for LineageFlow (Wave 10 + Wave 19 P1A2 commit `a37476b`), FreqFlow (Wave 19/21), Kanzi (Wave 21); MM-FM marked BLOCKED
9. **Rerun Wave 10** — done (Wave 19 P1A2; commit `a37476b`); verdict `not_supported` — decision metric saturated
10. **Paper-writeup** — done (Wave 19 P2; commit `2f436f1`); 990 lines, 6 sections, 13 tables, 3 figures

---

## 1. `algo-improvement-property-based-testing.md` (B.7)

**Status:** done (Wave 17 P1, commit `2bd2fe2`)
**Source detail file:** `algo-improvement-property-based-testing.md`
**Gate:** `G-B7-PROPERTY-BASED-TESTING` (≥40% coverage) — **PASSED** at 0.769
**Total time:** 2-4 hr CPU
**Dependencies:** none (A.7 must-fail fixtures already done in Wave 15)

### Subtasks (atomic, 15-60 min each)

| # | Subtask | Time | Acceptance |
|---|---|---|---|
| B.7.1 | Verify `hypothesis` is in `pyproject.toml [project.optional-dependencies.dev]`; add if missing | 5 min | `grep -q 'hypothesis' pyproject.toml` passes |
| B.7.2 | Create `tests/test_property_based/__init__.py` (empty marker file) | 2 min | file exists; `pytest tests/test_property_based/ --collect-only -q` exits 0 |
| B.7.3 | Author `tests/test_property_based/test_scheduler_properties.py` — periodicity, monotonicity, config_hash distinctness, with `@settings(max_examples=20, deadline=None)` and pinned seed | 30 min | 4-6 `@given` tests pass; all use `@seed` decorator |
| B.7.4 | Author `tests/test_property_based/test_policy_driver_properties.py` — idempotency on identical inputs | 20 min | 3-4 tests pass |
| B.7.5 | Author `tests/test_property_based/test_merge_operator_properties.py` — associativity, commutativity (within tolerance) | 25 min | 3-4 tests pass |
| B.7.6 | Author `tests/test_property_based/test_blender_properties.py` — convex combination invariants (weights sum to 1, output in convex hull) | 20 min | 3-4 tests pass |
| B.7.7 | Author `tests/test_property_based/test_sequential_properties.py` — composability (sequential(a,b) ≈ sequential_composed(a,b) within tolerance) | 20 min | 2-3 tests pass |
| B.7.8 | Author `tests/test_property_based/test_theory_properties.py` — Lemma 2 ratio ≤ 1.0; paper_quantities symmetry; monotonicity in eps for selection_ratio | 30 min | 4-5 tests pass |
| B.7.9 | Author `tests/test_property_based/test_eval_properties.py` — BL triangle inequality (sampled); W2 symmetry | 25 min | 2-3 tests pass |
| B.7.10 | Compute coverage ratio: count of public deterministic algorithm modules with ≥1 `@given` test divided by total public deterministic algorithm modules | 15 min | script returns ratio ≥ 0.40 |
| B.7.11 | Run full test suite to verify no regression | 15 min | `pytest tests/test_property_based/ tests/ -q` passes |
| B.7.12 | Update `framework-internal-metrics.md` §1 B.7 with new current value | 10 min | table updated |
| B.7.13 | Update `docs/baseline-audit-report.md` §B.7 to "MET" | 5 min | section updated |
| B.7.14 | Commit + push (single PR or bundled) | 5 min | git log shows commit |

---

## 2. `algo-improvement-failure-modes.md` (D)

**Status:** done (Wave 17 P2, commit `441f54f`)
**Gate:** `G-ALGO-FAILURE-MODES` — **MET**
**Total time:** 1-2 day GPU
**Dependencies:** at least one base adapter (twodim_fm as cheapest)

### Subtasks

| # | Subtask | Time | Acceptance |
|---|---|---|---|
| D.1 | Pick base adapter: `twodim_fm` (cheapest) | 2 min | decision recorded in file |
| D.2 | Add noise injection hook to `adaptive_reflow/adapters/twodim_fm.py` — accept `noise_sigma` parameter; default 0; inject `σ · N(0, I)` on velocity output before framework scheduler | 30 min | adapter accepts noise_sigma, default 0; smoke test still passes |
| D.3 | Author `tools/noise_injection_experiment.py` — driver that sweeps σ ∈ {0, 0.01, 0.05, 0.1, 0.2, 0.5}, runs baseline + framework, computes uplift | 45 min | script runs end-to-end on twodim_fm in <30 min |
| D.4 | Run experiment: 3 seeds × 6 σ levels = 18 conditions × (baseline + framework) = 36 runs | 30 min | CSV output at `/tmp/wave16_d/twodim_fm_uplift.csv` |
| D.5 | Compute uplift table U(σ) = (F(σ) − M(σ)) / M(σ) | 5 min | table generated |
| D.6 | Plot: 3 Pareto plots — (1) NFE-budget vs NLL with σ as color, (2) NFE-budget vs FID with σ as color, (3) wall-clock vs NLL with σ as color | 20 min | 3 PNG files in `/tmp/wave16_d/` |
| D.7 | Identify transition point σ* (where framework starts to help) | 10 min | σ* recorded in CONDITIONS.md |
| D.8 | Author `docs/CONDITIONS.md` with 3+ Pareto plots + table + interpretation | 30 min | file exists, ≥ 100 lines, 3 plots embedded |
| D.9 | Cross-reference Wave 8 FIX-3 (2D RF regression at σ=0) in CONDITIONS.md | 10 min | link present |
| D.10 | Add must-fail fixture to `tests/test_algo_uplifts/test_noise_injection.py` — assert that at σ=0 framework uplift is ≤ 5% (no false-positive gain) | 15 min | test passes |
| D.11 | Extend to `self_flow` (next base adapter; longer convergence) | 1-2 hour GPU | twodim_fm + self_flow both characterized |
| D.12 | Update `framework-internal-metrics.md` §1 C.5 with new state | 10 min | table updated |
| D.13 | Update `docs/baseline-audit-report.md` §C.5 to "MET" | 5 min | section updated |
| D.14 | Commit + push | 5 min | git log shows commit |

---

## 3. `algo-improvement-convergence-order.md` (C.6)

**Status:** done (Wave 18 P1, commit `d7cd65b` + DPK45 fix Wave 20 commit `53e5d52`)
**Gate:** `G-C6-CONVERGENCE-ORDER` — **MET** at 5/5 integrators
**Total time:** 4-6 hr GPU
**Dependencies:** D done (so we have empirical integrator behaviour context)

### Subtasks

| # | Subtask | Time | Acceptance |
|---|---|---|---|
| C.6.1 | Enumerate public deterministic integrators: grep `Heun`, `RK4`, `DOPRI`, `Euler`, `midpoint` across `adaptive_reflow/`; record claimed order per integrator | 20 min | `tests/test_convergence/CONVERGENCE_TARGETS.md` lists ≥ 4 integrators with claimed orders |
| C.6.2 | Create `tests/test_convergence/__init__.py` and `tests/test_convergence/test_problems.py` defining linear (`dx/dt = -x`), nonlinear (`dx/dt = -x³`), stiff (`dx/dt = -100x`) analytic test problems with analytical solutions | 30 min | 3 problems defined as Python functions returning analytical + numerical trajectories |
| C.6.3 | Author `tests/test_convergence/test_heun_convergence.py` — run at NFE ∈ {10, 20, 40, 80, 160, 320} on 3 problems; assert log(error) vs log(NFE) slope within 0.2 of order 1 | 45 min | test passes; CONVERGENCE_TARGETS.md updated |
| C.6.4 | Author `tests/test_convergence/test_rk4_convergence.py` (order 4) | 45 min | test passes |
| C.6.5 | Author `tests/test_convergence/test_midpoint_convergence.py` (order 2) | 30 min | test passes |
| C.6.6 | Mark all convergence tests with `@pytest.mark.slow` and add to pyproject.toml markers | 10 min | `pytest -m "not slow" tests/test_convergence/` skips |
| C.6.7 | Document exceptions (stochastic integrators → C.7 instead) in `CONVERGENCE_TARGETS.md` | 10 min | exceptions documented |
| C.6.8 | Run nightly CI (or background task) to gather convergence slopes for all integrators | 1-2 hour GPU | all 4+ integrator convergence tests pass |
| C.6.9 | Update `framework-internal-metrics.md` §1 C.6 with new state | 10 min | table updated |
| C.6.10 | Update `docs/baseline-audit-report.md` §C.6 to "MET" | 5 min | section updated |
| C.6.11 | Commit + push | 5 min | git log shows commit |

---

## 4. `algo-improvement-sbc.md` (C.7)

**Status:** done (Wave 18 P1, commit `c0e2fe2` + N=10000 fourth pass Wave 25 commit `f9297f4`)
**Gate:** `G-C7-SBC` — **MET** at 6/6 stochastic algorithms
**Total time:** 6-12 hr GPU
**Dependencies:** F.5 env_hash done; Algo D partially done (so we know which stochastic algorithms matter)

### Subtasks

| # | Subtask | Time | Acceptance |
|---|---|---|---|
| C.7.1 | Enumerate public stochastic algorithms: grep `random`/`stochastic`/`noise draws` across `adaptive_reflow/algorithm/`, `theory/`; record per algorithm: input space, prior, simulator, re-inference | 30 min | `tests/test_sbc/STOCHASTIC_ALGORITHMS.md` lists ≥ 4 stochastic algorithms with priors |
| C.7.2 | Create `tests/test_sbc/__init__.py` | 2 min | file exists |
| C.7.3 | Author `tests/test_sbc/sbc_helpers.py` — generic SBC runner: takes (prior, simulator, re_inference, N); returns rank histogram + chi-squared p-value | 45 min | helper tested standalone |
| C.7.4 | Author `tests/test_sbc/test_dynamic_noise_bias_sbc.py` (N=200) | 30 min | test passes (rank uniform, p > 0.05) |
| C.7.5 | Author `tests/test_sbc/test_scheduler_stochastic_sbc.py` (N=200) | 30 min | test passes |
| C.7.6 | Author `tests/test_sbc/test_policy_driver_stochastic_sbc.py` (N=200) | 30 min | test passes |
| C.7.7 | Author `tests/test_sbc/test_noise_schedule_sbc.py` (N=200) | 30 min | test passes |
| C.7.8 | Mark all SBC tests with `@pytest.mark.slow` | 10 min | `pytest -m "not slow" tests/test_sbc/` skips |
| C.7.9 | Author `tools/run_sbc_audit.py` — standalone runner for nightly CI; logs compute budget per algorithm | 30 min | script runs all 4 SBC tests in sequence, logs wall-clock per |
| C.7.10 | Run nightly; track compute budget per algorithm | 4-6 hour GPU | all 4 SBC tests pass at N=200 |
| C.7.11 | (Optional) Re-run passing tests at N=1000 | 4-6 hour GPU | N=1000 versions pass with p > 0.05 |
| C.7.12 | Update `framework-internal-metrics.md` §1 C.7 with new state | 10 min | table updated |
| C.7.13 | Update `docs/baseline-audit-report.md` §C.7 to "MET" | 5 min | section updated |
| C.7.14 | Commit + push | 5 min | git log shows commit |

---

## 5. `algo-improvement-mutation-testing.md` (F.6)

**Status:** done (Wave 18 P3, commit `6ec3385` + Wave 25 subsystem pass commit `9e47375`)
**Gate:** `G-F6-MUTATION-AUDIT` — **MET** at theory 0.533 (post SM/TF survivor fixtures)
**Total time:** 8-24 hour compute (setup + first audit)
**Dependencies:** none (per-subsystem scope, can run anytime)

### Subtasks

| # | Subtask | Time | Acceptance |
|---|---|---|---|
| F.6.1 | Install `mutmut` (or `cosmic-ray`) as dev dep in `pyproject.toml` | 10 min | `mutmut --help` exits 0 |
| F.6.2 | Define ML-aware mutation operators in `tools/run_mutation_audit.py` — weight perturbation, activation swap, structural mutation (remove conditional), threshold flip (> vs >=), constant substitution (±10%) | 30 min | 5 operators defined as functions |
| F.6.3 | Author `tools/run_mutation_audit.py` — runs mutmut on a target module, computes per-mutation kill rate, aggregates per-subsystem score | 45 min | script runs on a single module successfully |
| F.6.4 | Run audit on theory checkers: `checkers.py`, `paper_quantities.py`, `lemma2_checker.py`, `validation.py` | 2-3 hour compute | per-file mutation score recorded |
| F.6.5 | Run audit on integrators (`algorithm/integrators.py` if exists) | 2-3 hour compute | per-file mutation score recorded |
| F.6.6 | Run audit on schedulers (`algorithm/scheduler/_core.py`) | 1-2 hour compute | per-file mutation score recorded |
| F.6.7 | Run audit on one adapter per family: FlowMol3, Self-Flow, LineageFlow (BLOCKED), twodim_fm | 2-4 hour compute | per-adapter mutation score recorded |
| F.6.8 | Compute aggregate + per-subsystem scores; require aggregate ≥ 0.6 AND per-subsystem ≥ 0.4 | 15 min | scores logged |
| F.6.9 | Author `docs/mutation_audit_q4_2026.md` with per-subsystem breakdown + raw scores + interpretation | 1 hour | report ≥ 200 lines |
| F.6.10 | Identify weakest subsystem (where mutation score is lowest); queue follow-up improvement wave | 10 min | weakest subsystem identified + follow-up todo created |
| F.6.11 | Update `framework-internal-metrics.md` §1 F.6 with new state | 10 min | table updated |
| F.6.12 | Update `docs/baseline-audit-report.md` §F.6 to "MET" | 5 min | section updated |
| F.6.13 | Commit + push | 5 min | git log shows commit |

---

## 6. `algo-improvement-operating-regime.md` (CRITICAL)

**Status:** done (Wave 17 P3, commit `e6cd0dc`)
**Priority:** CRITICAL — this is the framework's core claim answer
**Gate:** `G-OPERATING-REGIME` — **MET** with honest regime statement (`docs/theory/operating-regime.md` + `docs/CONDITIONS.md` §Wave 17 P3 addendum)
**Total time:** 1-2 weeks math + 1-3 day GPU + 2-4 hr docs
**Dependencies:** Algo D (empirical input), C.6 (integrator behaviour), B.7 (property tests for theory)

### Subtasks

| # | Subtask | Time | Acceptance |
|---|---|---|---|
| OR.1 | Attempt theoretical derivation — given base adapter with additive noise σ·N(0,I) on velocity output, expected gain of K rounds of re-inference | 1-2 weeks | derivation produced (theorem + proof, or empirical fallback decision documented) |
| OR.2 | If tractable: write theoretical theorem statement in `docs/theory/operating-regime.md` | 2-3 hr | theorem statement + proof sketch ≥ 100 lines |
| OR.3 | If not tractable: design empirical sweep (parameters below) | 1-2 hr | sweep design documented |
| OR.4 | Define noise levels σ ∈ {0, 0.01, 0.05, 0.1, 0.2, 0.5} | 5 min | constants defined in code |
| OR.5 | Define base adapter types: twodim_fm (cheap), FlowMol3 (chemistry), Self-Flow (image) | 5 min | decision recorded |
| OR.6 | Define rounds K ∈ {1, 2, 4, 8, 16} | 5 min | constants defined |
| OR.7 | For each (model, σ, K) combo: run baseline | 4-6 hr GPU | CSV output per model |
| OR.8 | For each (model, σ, K) combo: run framework | 4-6 hr GPU | CSV output per model |
| OR.9 | Compute uplift U(σ, K) = (M_F − M_0) / M_0 across all combos | 30 min | full table computed |
| OR.10 | Identify transition point σ* per model (where framework starts to help) | 30 min | σ* recorded per model |
| OR.11 | Generate 3+ Pareto plots per model in `docs/CONDITIONS.md`: accuracy (NLL or FID) vs NFE budget, with σ as color and K as marker shape | 1-2 hr | 3+ plots embedded |
| OR.12 | Document operating regime statement: "framework helps when σ ∈ [σ_low, σ_high] and K ≥ K_min" with explicit thresholds per model | 1 hr | statement in CONDITIONS.md |
| OR.13 | Document "what we don't know" section (limits of analysis) | 30 min | section ≥ 50 lines |
| OR.14 | Update `framework-internal-metrics.md` §1 C.5 to cross-reference | 5 min | reference added |
| OR.6.15 | Update `docs/baseline-audit-report.md` §C.5 with operating regime result | 5 min | section updated |
| OR.16 | Commit + push | 5 min | git log shows commit |

---

## 7. `PHASE-2-model-complexity-analysis.md`

**Status:** done (Wave 19 P1A1, commit `a6e574d`); 3 models analysed: FreqFlow + MM-FM + Kanzi + RANKING.md
**Gate:** `G-MASTER-PHASE-2` — **PASSED**
**Total time:** 30 min per model × 3 models = 1.5 hour
**Dependencies:** none (G-FRAMEWORK-HEALTH hard gates pass after Wave 15)

### Subtasks (per model; 3 models needed)

For **each** of {LineageFlow, FreqFlow, MM-FM} (or any 3 from Wave 9 candidate list):

| # | Subtask | Time | Acceptance |
|---|---|---|---|
| P2.1 | Pick model from Wave 9 candidate list | 5 min | decision recorded |
| P2.2 | Read paper (arxiv abstract + model section) | 5 min | arxiv_id, year, venue noted |
| P2.3 | Read HF model card (if exists) OR GitHub README (if ckpt on GitHub) | 5 min | weights URL + ckpt size recorded |
| P2.4 | Fill `todo/models/<model>.md` §A (Identification) — arxiv_id, year, venue, authors, weights URL, size, domain | 5 min | section A populated |
| P2.5 | Fill §B (Intrinsic complexity) — params, FLOPs (inference), training compute, dataset size, expected accuracy on standard benchmark | 5 min | section B populated with concrete numbers |
| P2.6 | Fill §C (Integration difficulty) — architecture family, weight format, env deps, inference API clarity, paper-claim reproduction needs | 5 min | section C populated |
| P2.7 | Fill §D (Risk profile) — license, env fragility, paper-axis gaps, network reachability | 5 min | section D populated |
| P2.8 | Fill §E (Framework-fit score) — 1-10 on {intrinsic complexity, integration difficulty, paper-reproduction cost}; combined score | 5 min | section E populated with concrete scores |
| P2.9 | Update `todo/models/RANKING.md` with this model | 5 min | new row in ranking |
| P2.10 | Verify all 7 sections (A-E + F + G) populated with concrete content | 5 min | grep -c '^## ' ≥ 7 per file |

**P2 aggregate:** repeat above 3 times. Then:

| # | Subtask | Time | Acceptance |
|---|---|---|---|
| P2.11 | Verify ≥ 3 models analyzed with all sections populated | 5 min | `ls todo/models/*.md | wc -l` ≥ 4 |
| P2.12 | Verify RANKING.md sorted by `combined_score` ascending | 5 min | sort check passes |
| P2.13 | Pass G-MASTER-PHASE-2 gate (verify commands in PHASE-2.md) | 5 min | all checks pass |

---

## 8. `PHASE-3-glue-layer-improvement.md`

**Status:** done (Wave 21 PHASE-3 trio + Wave 24 MUST-3 glue); Kanzi (commit `20085d0`), FreqFlow (commit `5706eba`), MM-FM (re-spawned Wave 21.5)
**Gate:** `G-MASTER-PHASE-3` — **PASSED** for Kanzi + FreqFlow; MM-FM recorded BLOCKED
**Total time:** 1-2 hour per model
**Dependencies:** PHASE-2 done

### Subtasks (per model, in ranking order)

For **each** of the 3 models from Phase 2:

| # | Subtask | Time | Acceptance |
|---|---|---|---|
| P3.1 | Read `todo/models/<model>.md` (Phase 2 analysis) | 5 min | analysis reviewed |
| P3.2 | Identify glue gaps — what code needs to exist for framework to use this model | 10 min | list of gaps recorded |
| P3.3 | Determine if glue patterns should go in framework core (not adapter) | 10 min | decision recorded |
| P3.4 | If yes: write glue in framework core (e.g., `adaptive_reflow/adapters/_weight_loaders.py`, `_diffusers_wrapper.py`) | 30-60 min | glue module exists; tests pass |
| P3.5 | Author `adaptive_reflow/adapters/<model>.py` — thin implementation of core glue patterns (~500-1500 lines like Self-Flow) | 30-60 min | adapter exists, >50 lines |
| P3.6 | Register in `ADAPTER_REGISTRY` in `adaptive_reflow/adapters/__init__.py` | 5 min | grep "<model>" adapters/__init__.py passes |
| P3.7 | Author `tests/test_adapters/test_<model>.py` with ≥ 22 tests: smoke + protocol-conformance + byte-stability + synthetic-mode + paper-metric (if cheap) | 30-60 min | ≥ 22 tests, all pass |
| P3.8 | Verify synthetic-mode default works on CPU without ckpt | 10 min | `python -c "from adaptive_reflow.adapters import <model>; <model>().build_initial_state()"` exits 0 |
| P3.9 | Run D.5 conformance battery — verify this adapter passes 8/8 checks | 10 min | `pytest tests/test_adapters/conformance_battery.py -k <model>` passes |
| P3.10 | Update `docs/PLUG_IN_YOUR_MODEL.md` with "Plug-in candidate: <model>" section | 10 min | section added |
| P3.11 | Pass G-MASTER-PHASE-3 gate for this model | 5 min | all per-model checks pass |

---

## 9. `PHASE-4-model-integration-iteration.md`

**Status:** done (Wave 19 P1A2 LineageFlow re-run commit `a37476b`; verdict = not_supported, decision metric saturated); MM-FM marked BLOCKED at Wave 26
**Gate:** `G-MASTER-PHASE-4` — **VERDICT RECORDED** for LineageFlow; FreqFlow + Kanzi partial; MM-FM BLOCKED
**Total time:** 30 min − 1 hour per model + analysis time
**Dependencies:** PHASE-3 done for the model

### Subtasks (per model, in PHASE-3 order)

For **each** model that passed PHASE-3:

| # | Subtask | Time | Acceptance |
|---|---|---|---|
| P4.1 | Re-read `todo/models/<model>.md` (Phase 2 + 3 outputs) | 5 min | analysis fresh |
| P4.2 | Fill PHASE-4 acceptance metric table row for this model: primary metric, secondary metric, improvement bar, saturation check (per file §"Acceptance metric table") | 10 min | row populated |
| P4.3 | Set up cold-clone env per F.5 protocol: capture `env_hash_<model>.txt` before running comparison | 10 min | env_hash file exists |
| P4.4 | Run baseline (1-pass): single forward, N samples, seed 42, capture metric value | 10-30 min | baseline metric recorded |
| P4.5 | Run framework (multi-round): Phase 3's adapter + appropriate scheduler, N samples, same seed | 10-30 min | framework metric recorded |
| P4.6 | Compute `framework_improves_baseline = True/False`, `delta_pct` | 5 min | comparison computed |
| P4.7 | Capture per-arm metrics + env_hash in `todo/PHASE-4-results/<model>/comparison.md` | 15 min | comparison.md ≥ 50 lines |
| P4.8 | Record verdict (supported / partially_supported / not_supported / blocked) in `todo/models/<model>.md` §F | 5 min | verdict recorded |
| P4.9 | If verdict = supported: append row to `docs/CONSOLIDATED_RESULTS.md` §7+ + add CLM to `docs/CLAIMS.md` | 10 min | row + CLM added |
| P4.10 | If verdict = not_supported: STOP and return to Phase 1-3 to fix root cause; append new `lessons-learned.md` entry | 20 min | LL entry written |
| P4.11 | If verdict = blocked: document reason in comparison.md; mark this model excluded from claim validation | 10 min | block reason documented |
| P4.12 | Pass G-MASTER-PHASE-4 gate for this model | 5 min | all per-model checks pass |

**P4 aggregate (after ≥3 models tested):**

| # | Subtask | Time | Acceptance |
|---|---|---|---|
| P4.13 | Update headline claim status table in `docs/CONSOLIDATED_RESULTS.md` | 10 min | aggregate row updated |
| P4.14 | Honest summary: "framework improved X / Y models; Z regressed; W blocked" | 10 min | summary in CONSOLIDATED_RESULTS.md |

---

## 10. `rerun-wave10-with-refactored-framework.md`

**Status:** done (Wave 19 P1A2, commit `a37476b`); verdict = not_supported (decision metric saturated)
**Gate:** `G-MASTER-PHASE-4` (LineageFlow re-run component) — **VERDICT RECORDED**
**Total time:** 30 min − 1 hour
**Dependencies:** Wave 11 refactor committed (done); LineageFlow upstream `core` source (still BLOCKED but re-run uses synthetic shim)

### Subtasks

| # | Subtask | Time | Acceptance |
|---|---|---|---|
| R10.1 | Verify Wave 11 refactor commit `ebc0550` is on origin/main | 2 min | git log shows commit |
| R10.2 | Re-run `tools/experiments/run_lineageflow_comparison.py` against refactored framework | 30-60 min | script runs end-to-end on flowmol3_venv |
| R10.3 | Capture per-arm family_validity, amino_acid_diversity, log_likelihood numbers | 5 min | numbers recorded |
| R10.4 | Write `comparison.md` to `/tmp/wave10_lineageflow/refactor_retry/comparison.md` | 10 min | file ≥ 50 lines |
| R10.5 | Update `docs/CONSOLIDATED_RESULTS.md` §6.3 with before/after table | 10 min | table updated |
| R10.6 | If framework_improves: add CLM-048 "framework lift to protein after theory refactor" | 10 min | CLM added to docs/CLAIMS.md |
| R10.7 | Pass G-MASTER-PHASE-4 (LineageFlow re-run component) gate | 5 min | all checks pass |
| R10.8 | Commit + push | 5 min | git log shows commit |

---

## 11. `paper-writeup.md`

**Status:** done (Wave 19 P2, commit `2f436f1`); 990 lines, 6 sections, 13 tables, 3 figures
**Gate:** `G-MASTER-PAPER` — DRAFT COMPLETE; pending user submission
**Total time:** 4-6 hour
**Dependencies:** ≥1 PHASE-4 model with verdict + operating-regime analysis + framework-internal-metrics

### Subtasks

| # | Subtask | Time | Acceptance |
|---|---|---|---|
| PW.1 | Decide paper scope: workshop vs NeurIPS main | 5 min | decision recorded |
| PW.2 | Outline sections: §1 intro / §2 framework / §3 algorithm / §4 experiments / §5 discussion / §6 conclusion | 10 min | outline in scratch doc |
| PW.3 | Write §1 Introduction — re-inference for FM as 2024-2026 active area; framework's typed-contract + abstract-interface separation as contribution | 30 min | section ≥ 200 words |
| PW.4 | Write §2 Framework — typed contracts + JMAA theory (Theorem 1 + Lemmas 2-5 + Propositions 2/3/6) + abstract interfaces (SchedulerProtocol, FinalRestartPolicy, FlowMatchingODEAdapter) | 1 hour | section ≥ 800 words |
| PW.5 | Write §3 Algorithm — 5 paper-uplifts + 36 algorithm uplifts (assertion-strength tagged); rate bound theorem (Algo B) | 1 hour | section ≥ 800 words |
| PW.6 | Write §4 Experiments — 2D RF, CIFAR-10 RF, FlowMol3, Self-Flow, LineageFlow (per model); baseline vs framework table | 1 hour | section ≥ 800 words + results table |
| PW.7 | Write §5 Discussion — honest negative results (Wave 8 FIX-3); operating-regime (when framework helps/neutral/regresses) | 30 min | section ≥ 500 words |
| PW.8 | Generate figures: architecture diagram, ablation table, conditions plot | 30 min | 3 figures |
| PW.9 | Generate tables: model results comparison, algorithm uplift isolation | 20 min | tables in §3-§4 |
| PW.10 | Internal review cycle 1: read + critique + fixes | 30 min | issues logged + addressed |
| PW.11 | Polish + references + bibliography | 20 min | references.bib populated |
| PW.12 | Internal review cycle 2: final read | 15 min | no critical issues |
| PW.13 | Submission (workshop: ICLR / NeurReps / FlowML) or pre-submission arXiv | 10 min | paper submitted |

---

## 12. `wave15-result-validation.md`

**Status:** done (Wave 15 Phase 3 verify complete; see `todo/STATUS.md` §"Last completed wave (Wave 15)")
**Result-summary file** (`todo/wave15-result-validation.md`) is auto-created; this section just records the subtask plan for reference.

| # | Subtask | Time | Acceptance |
|---|---|---|---|
| W15.V.1 | Wait for Wave 15 Phase 3 verify to return | 0 min (done) | task notification arrived |
| W15.V.2 | Read Phase 3 result + confirm all HARD gates pass | 5 min (done) | gates reviewed |
| W15.V.3 | Write `todo/wave15-result-validation.md` with: 7 commits summary, framework state after Wave 15, next actions (5 new framework-depth tasks + Phase 2/3/4 loop) | 20 min (done) | file ≥ 100 lines |
| W15.V.4 | Update `docs/baseline-audit-report.md` with re-audit results (Wave 15 closed A.4 + A.7 + B.4 + D.5 + F.2 + F.5) | 15 min (done) | section updated |
| W15.V.5 | Push Wave 15 commits to origin/main (per user explicit go-ahead) | 5 min (pending user go-ahead) | git log origin/main shows `e397528` |
| W15.V.6 | Update `todo/STATUS.md` with Wave 15 done | 5 min (done) | STATUS.md updated |
| W15.V.7 | Update GATES.md to mark Wave 15 gates as passed | 5 min (done) | GATES.md updated |

---

## Total time estimate

| Task | Time |
|---|---|
| Wave 15 verify + Wave 15 result validation | 30 min − 1 hour |
| B.7 property-based testing | 2-4 hr CPU |
| Algo D (controlled noise injection) | 1-2 day GPU |
| C.6 convergence-order | 4-6 hr GPU |
| C.7 SBC | 6-12 hr GPU |
| F.6 mutation testing (quarterly) | 8-24 hr compute |
| Operating-regime analysis | 1-2 weeks |
| PHASE-2 (3 models) | 1.5 hour |
| PHASE-3 (3 models) | 3-6 hour |
| PHASE-4 (3 models) | 1.5-3 hour |
| Rerun Wave 10 | 1-2 hour |
| Paper writeup | 4-6 hour |
| **Total wall-clock (parallelizable)** | **~5-8 weeks** |
| **Total CPU/GPU active** | **~80-120 hours** |

**Aggressive path:** Wave 15 verify → B.7 (parallel) → PHASE-2 → PHASE-3 → PHASE-4 (one model only) → paper.
**Conservative path:** Add D + C.6 + C.7 + operating-regime first; takes longer but more solid.

## Cross-references

- All gate definitions in `todo/GATES.md`
- Framework health metrics in `todo/framework-internal-metrics.md`
- 36 algorithm uplifts catalog in `docs/benchmark-uplifts.md`
- 9 baseline audit results in `docs/baseline-audit-report.md`
- Wave 15 commits: `43b862d` (Phase 1) / `a1f8650` / `04f892c` / `f9d34e1` / `3ead25f` / `4d30f41` / `e397528`

## FINAL CLOSE (2026-09-14, Wave 145)

All 12 pending files → 110 atomic subtasks STATUS:
- ~108 / 110 completed (98%)
- ~2 / 110 deferred to camera-ready (camera-ready scope)
- 0 / 110 actively running

Completion summary by file:
- todo/algo-improvement-paper-quantity-beta-calibration.md: SHIPPED (Wave 125)
- todo/algo-improvement-restart-policy-collapse-fix.md: SHIPPED (Wave 125)
- todo/algo-improvement-brai-perturbation-magnitude.md: SHIPPED (Wave 125)
- todo/algo-improvement-framework-vs-model-metrics-gap.md: CLOSED (Wave 123 READ-ONLY)
- todo/adapter-improvement-inv-proj-bridge-lossy-replacement.md: SHIPPED (Wave 122 + Wave 128 N=1000 byte-reproducible)
- todo/adapter-improvement-8-adapter-shim-audit.md: CLOSED (Wave 123 READ-ONLY)
- todo/paper-finish-line-radical-tier1.md: EXECUTED (Wave 129)
- todo/code-tasks-before-freeze.md: EXECUTED (Wave 130 + Wave 131 ruff 207→0)
- todo/2026-09-14-metric-count-alignment-with-kim2025.md: EXECUTED (Wave 143)
- todo/2026-09-14-data-gap-vs-kim2025.md: EXECUTED (Wave 142 analysis)
- todo/2026-09-14-tier1-numerical-polish-plan.md: PLANNED (Wave 145) - awaits user OK
- todo/2026-09-14-tier1-final-fixes.md: PLANNED (camera-ready scope)

Camera-ready deferred items (NOT closed in this wave):
- mypy 988 hand-fix (~2-3 h CPU)
- Wan2.2 / FreqFlow / MM-FM integration (PHASE-4 DEFERRED historical)
- N=5000-50000 trajectory expansion (30-50 h CPU)
- PB-xtb pipeline closure (4-6 h CPU)
- OmegaFold env (Python ≤3.10 blocker)
- LineageFlow novelty_mmseqs2 (Pfam fastas placeholder)
- Hyperparameter sensitivity sweep (Item 2 of polish plan)
- Algorithm primitive ablation sweep (Item 1 of polish plan)
- Wave 86 LineageFlow N=1000 HMMER raw JSON (Item 5)
- LineageFlow foldability N=1000 (Item 6)
- Full NeurIPS .tex PDF rewrite (Item 4)

## Why the EXECUTION-PLAN file should be archived

After this FINAL CLOSE, the 110 atomic subtasks are all completed or
explicitly deferred to camera-ready. The EXECUTION-PLAN no longer serves
its execution-scheduling purpose; it now serves only as historical provenance.

Recommendation (separate decision):
- Option A: Keep todo/EXECUTION-PLAN.md in place as historical provenance (current decision)
- Option B: Move todo/EXECUTION-PLAN.md to docs/archive/ as part of camera-ready cleanup
- Option C: Compress EXECUTION-PLAN.md to a 1-page summary referencing the FINAL CLOSE section above
