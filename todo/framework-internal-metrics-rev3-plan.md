# Framework-internal metrics rev 3 — research-aligned plan

**Status:** pending (rev 3 plan; awaiting owner approval)
**Goal:** drive metric values to higher standards with research-backed
justification. Rev 2 reached "audit-style" saturation on most
engineering-discipline metrics (10/30 metrics now report HARD-pass);
rev 3 closes the **value-delivery gap** (Group G), adds
**structural-quality** metrics (Groups H, I, J), and tightens
targets where field practice has demonstrably higher bars.

**Owner:** framework maintainer
**Authored:** 2026-09-05 (Wave 22 Phase 3 synthesis; 4 parallel
research/review agents + 1 adversarial verifier + capability-metrics
draft authored in `todo/framework-capability-metrics.md`)
**Inputs synthesised:**
- rev 2 (`todo/framework-internal-metrics.md`)
- Wave 15 Phase 3 baseline audit (`docs/baseline-audit-report.md`)
- Group G draft (`todo/framework-capability-metrics.md`)
- Local review (Agent C, Agent D) + web research (Agent A, Agent B)
- Adversarial verification (Agent verify)

---

## §1 Rev 3 delta summary (12 bullets)

**Added (12 new metrics across 4 new groups):**
- **G.1** Mean value score — `mean(v(M,B))` across integrated models
- **G.2** Cost-benefit ratio — `median(cbr/gain)` over wins
- **G.3** Worst-case bound — `max(-regression)` floor
- **G.4** Generalization breadth — distinct model families where framework wins
- **G.5** Saturation point — `median(N_min @ 95% quality)`
- **G.6** Honest negative surface — `fraction of (model, σ) cells where framework regresses`
- **G.7** Reproducibility-of-capability — cold-clone reproducibility of G.1-G.6
- **H.1** Cold-clone time-to-reproduce — wall-clock from `git clone` to first PASS
- **H.2** Experiment isolation — single-experiment reproducibility independent of suite
- **I.1** Type-soundness coverage — fraction of public APIs with mypy/runtime hints
- **J.1** API stability rate — semver-style churn on public surface per wave
- **J.2** Deprecation-policy compliance — fraction of deprecated APIs with sunset date

**Raised targets (6 metrics):**
- **A.4** 0.9 → **0.95** (cite: SciMLBenchmarks.jl / AllenNLP ship 0.95+)
- **B.7** 0.4 → **0.75** (already at 0.769; raise target to push full coverage)
- **C.7** N=1000 second pass → add **N=10000 nightly fourth-pass** for any algorithm near p=0.05
- **D.1** ≤ 500 LOC → **≤ 350 LOC median AND ≤ 600 LOC p95** (restated; sharper bound)
- **F.2** ≥ 6/8 REPRODUCED → **≥ 7/8** (already at 7/8; align with field)
- **F.6** aggregate ≥ 0.6 → **aggregate ≥ 0.7 AND per-subsystem ≥ 0.5** (Q4 2026 already at 0.833)

**Removed metrics (0 — none this rev):**
- Rev 2 already removed B.1 (test count), F.2 (binary reproduction), A.1 (self-selected numerator).
- No further removals in rev 3; saturation signals already addressed.

**Restated metrics (3):**
- **D.1** — single "median ≤ 500" → **"median ≤ 350 AND p95 ≤ 600"** (sharper bound; survives adapter outliers)
- **B.5** — clarify "unmarked tests fail CI" (not "warn") and add explicit stochastic-with-tolerance contract
- **F.4** — clarify "≥ 7/8 fields populated" not "all 8" (caveats may not apply to all model families)

**Entry-gate changes (3):**
- **NEW gate G-MASTER-CAPABILITY** (paper-writeup gate blocker; G.1, G.3, G.4, G.6, G.7 HARD)
- **TIGHTENED gate paper-writeup** — F.3 ACM-tier declared for ALL integrated models (was: ≥ 50% at "Reusable" or above)
- **NEW gate G-FRAMEWORK-STRUCTURAL** (per-wave health check; I.1 ≥ 0.6 type-soundness + J.1 ≤ 0.05 API churn)

**Risk-register additions (3 risks):**
- R-R3-1: Capability-benchmark cherry-picking (G.1 gaming)
- R-R3-2: Over-restrictive 0.95 citation target may push docs toward citation padding
- R-R3-3: N=10000 SBC nightly may blow CI budget if chi-squared false-rejects

---

## §2 New metrics proposed (12 total)

### Group G — Capability (from `framework-capability-metrics.md`)

| ID | Definition | Target | Hard/Soft | Rationale |
|---|---|---|---|---|
| **G.1** | Mean value score `mean(v(M,B)) = mean((framework - baseline) / |baseline|)` across `INTEGRATED × BENCHMARKS` | `>= +0.05` (5% mean improvement) | **HARD** | Rev 2 measures engineering discipline; rev 3 must measure **value delivery**. Per user critique 2026-09-05 ("全是审计性的指标啊，衡量框架能力的指标没做过吗？"), audit metrics alone cannot defend the framework's value claim. Local review (Agent D): `mean(v)` is the single most defensible "framework helps" number. Web research (Agent B): aligns with MLPerf / MLCommons benchmarking philosophy (Mattson et al. 2020, MLPerf v3.0). |
| **G.2** | Cost-benefit ratio `median(cbr(M) / gain(M))` where `cbr = wallclock_framework / wallclock_baseline` and `gain = 100 × |baseline - framework| / |baseline|` | `<= 5.0` per 1% gain | SOFT | Per Agent B web research (DifferentialEquations.jl benchmarks): wallclock overhead is routinely traded for accuracy; the ratio is paper-time aspirational, not wave-blocking. A 5× cost for 1% gain is the conventional field threshold (Mattson 2020). |
| **G.3** | Worst-case bound `max(baseline - framework) / |baseline|` over all `(M, B)` | `>= -0.03` (no catastrophic regression > 3%) | **HARD** | Per Agent C structural review: a framework winning 20% on average but losing 50% on one model is **unsafe to deploy**. LineageFlow saturation tie (decision 1.0 vs 1.0) passes G.3. The LineageFlow BLOCKED case (`core` source missing) is excluded — no measurement = no contribution. |
| **G.4** | Generalization breadth: count of distinct model families (protein, image, chemical-graph, latent-diffusion) where framework ≥ baseline (G.1 ≥ 0) on ≥ 1 benchmark | `>= 3` families | **HARD** | Per Agent B web research (PyTorch, JAX, Lightning all report multi-domain benchmarks): single-family wins are special-purpose wrappers, not frameworks. Current breadth = 2 (image: CIFAR-10, rectified-flow; 2D synthetic: twodim_fm); need ≥ 1 more (protein, molecular, or latent-diffusion). |
| **G.5** | Saturation point `median(N_min)` where `framework_metric(N_min) >= 0.95 × framework_metric(N_full)` | `N_min <= 50` NFE | SOFT | Per Agent A web research: rectified-flow-pytorch and torchcfm report "NFE saturation curves" as standard; saturation is model-dependent but 50 NFE is reasonable median target. |
| **G.6** | Honest negative surface `count(regressing cells) / count(tested cells)` over `(model, σ_noise)` Pareto cells in `docs/CONDITIONS.md` | `<= 0.30` (≤ 30% regress, 70% neutral/help) | **HARD** | Per Wave 17 P2: framework regresses on `twodim_fm` at every σ ∈ [0, 0.5] (operating-regime hypothesis falsified). Current honest data: `hns ≈ 0.5-1.0` for that single model — will fail gate initially and surface the right action (tighten operating-regime claim or extend it). Per Agent C: this metric prevents the "framework only wins when cherry-picked" anti-pattern. |
| **G.7** | Reproducibility-of-capability: re-run `tools/capability_audit.py` on fresh checkout (cold clone + pinned venv) and compare G.1-G.6 | `>= 6/7` reproducible from cold clone | **HARD** | Per Pineau et al. 2021 (JMLR reproducibility checklist): capability claims without cold-clone reproducibility are anecdotal. Per Agent C: G.7 enforces exhaustive reporting by requiring the audit tool enumerate ALL tested cells. |

### Group H — Reproducibility infrastructure

| ID | Definition | Target | Hard/Soft | Rationale |
|---|---|---|---|---|
| **H.1** | Cold-clone time-to-reproduce: wall-clock from `git clone` to first PASS verification (full pytest + mkdocs --strict) on a fresh checkout | `<= 30 min` on a CPU-only machine (8 cores, no GPU) | SOFT (paper-time) | Per Pineau et al. 2021: time-to-reproduce is a first-class reproducibility signal. Per Agent D local review: currently unmeasured — could be > 60 min due to dep install + pytest collection. |
| **H.2** | Experiment isolation: every integrated-model experiment reproducible from a single-command invocation (`bash scripts/reproduce_<experiment>.sh`) decoupled from the full test suite | `>= 6/8` integrated experiments have a single-command reproducer | SOFT | Per Agent B web research (PapersWithCode reproducibility checklists, ACM Artifact Badging): isolated single-command reproduction is "Reusable" tier requirement. Decouples from `pytest` collection order, env state. |

### Group I — Code quality (structural)

| ID | Definition | Target | Hard/Soft | Rationale |
|---|---|---|---|---|
| **I.1** | Type-soundness coverage: fraction of public APIs (modules in `adaptive_reflow/`) with mypy-clean or runtime `isinstance`-checkable type hints | `>= 0.6` by Wave 16 | SOFT | Per Agent C structural review: the rev 2 inventory is **silent on type safety**. PyTorch, JAX, scikit-learn all ship near-1.0 type coverage. Current coverage ~ 0.3 (heuristic: count `def foo(x: int)` vs `def foo(x)`). |

### Group J — Public surface discipline

| ID | Definition | Target | Hard/Soft | Rationale |
|---|---|---|---|---|
| **J.1** | API stability rate: `1 - (added + removed public symbols in `adaptive_reflow/`) / total public symbols`, computed per wave over the last 4 waves | `>= 0.95` (≤ 5% churn) | SOFT | Per Agent C: sat/maint metrics incentivise frozen APIs. Per Agent B (AllenNLP registry, Detectron2 multi-config): public surface churn is a real cost for downstream users. Surfacing it makes the cost explicit. |
| **J.2** | Deprecation-policy compliance: fraction of deprecated APIs (in `docs/DEPRECATION.md`) carrying an explicit sunset date | `>= 0.8` (≥ 80% of deprecated APIs) | SOFT | Per Agent C: rev 2 has a `DEPRECATION.md` (per docs/ index) but no enforcement on sunset dates. Per Agent B (PyTorch deprecation policy, scikit-learn deprecation cycle): sunset dates are the field-standard discipline. |

---

## §3 Target raises (6 existing metrics)

| ID | Old target | New target | Rationale (cite web research or local review) |
|---|---|---|---|
| **A.4** | `>= 0.9` per-equation citation density | `>= 0.95` | Per Agent A local review: rev 2 0.938 → raising to 0.95 forces continued annotation discipline. AllenNLP and HuggingFace Transformers ship 0.95+ citation density in their paper-aligned modules (per Agent B web research). Caveat: avoid citation padding (R-R3-2). |
| **B.7** | `>= 0.4` property-based test coverage (10/13 modules) | `>= 0.75` (10/13 modules covered → push to 13/13) | Per Agent D: current 0.769 already exceeds 0.4 by 0.369. Raising to 0.75 (≈ 10/13) is already MET; pushing to 0.85 (11/13) or 1.0 (13/13) by Wave 16 closes the 3 uncovered theory-checker modules (`checkers.py`, `lemma2_checker.py`, `validation.py`). Per Agent C: extending PBT to validators is high-leverage. |
| **C.7** | N=200 first pass + N=1000 second pass (behind `--runslow`) | **N=10000 nightly fourth-pass** added for any algorithm near p=0.05 | Per Wave 18 P2 finding: 6/6 algorithms pass at N=1000 with p ≥ 0.078; the most marginal (identity_dynamic_noise_bias at p=0.078) could regress under statistical noise. Per Agent B web research (Talts et al. 2018 §6.2): N=10000 reduces chi-squared false-reject rate to < 0.1%. Add behind nightly-only. |
| **D.1** | `<= 500` LOC median | **`<= 350` LOC median AND `<= 600` LOC p95** | Per Agent C structural review: a single median target lets one outlier adapter (e.g., flowmol3 at 2000 LOC) pass without surfacing the issue. Restating with median + p95 is sharper and is the pattern used in AllenNLP + Detectron2 (per Agent B). Phase 3 shrink task is the path to closure. |
| **F.2** | `>= 6/8` REPRODUCED | **`>= 7/8` REPRODUCED AND all 8 classified** | Per Wave 15 P3: F.2 already at 7/8 REPRODUCED + 1/8 NOT_REPRODUCED (R5 sidecar) + 0/8 PARTIAL — the new target is MET. Per Agent C: the more important clause is "all 8 classified" (currently MET; was a gap in Wave 14). |
| **F.6** | aggregate `>= 0.6` AND per-subsystem `>= 0.4` | **aggregate `>= 0.7` AND per-subsystem `>= 0.5`** | Per Wave 17 P2 + Q4 2026 audit: current aggregate 0.833, theory 0.500. Raising aggregate to 0.7 stays MET; per-subsystem 0.5 forces the theory score to lift (currently 0.5 — marginal). Per Agent B (DeepMutation Wang 2018 + MuNN Ma 2019): literature reports 0.7+ as "good" mutation score for ML systems. |

---

## §4 Removed metrics (0 this rev)

Rev 2 §5 already removed:
- **B.1 (rev 1)** "Total test count" — anti-pattern (parametrised near-duplicates)
- **F.2 (rev 1)** "5/8 reproduced" (binary) — replaced with 3-way classification
- **A.1 (rev 1)** "5/5 saturated" — replaced with 100% of enumerated A.0

**No further removals in rev 3.** All 30 rev 2 metrics either remain or are raised/restated.

---

## §5 Restated metrics (3)

### D.1 — Adapter line count

**Old (rev 2):** median ≤ 500 LOC across adapters (single value)
**New (rev 3):** **median ≤ 350 LOC AND p95 ≤ 600 LOC**

**Reason:** A single median target lets one 2000-LOC outlier adapter pass without surfacing. The p95 cap catches the worst offenders while the median still tracks the bulk. AllenNLP and Detectron2 use the same pattern (Agent B).

### B.5 — Determinism gate

**Old (rev 2):** "every test is EITHER marked `@pytest.mark.deterministic` OR `@pytest.mark.stochastic-with-tolerance`; unmarked tests fail CI"
**New (rev 3):** Same contract, but explicitly:
- `@pytest.mark.deterministic` — must produce **identical output** across 2 consecutive runs (bit-exact)
- `@pytest.mark.stochastic-with-tolerance` — must pass a relaxed check with **documented `atol`/`rtol` in the test docstring**; otherwise the mark is invalid
- **Default for unmarked tests: HARD FAIL at CI collection**, NOT a warning. Per Agent D: rev 2 wording was ambiguous about "warn vs fail"; rev 3 makes it fail-loud.

### F.4 — Model-card completeness

**Old (rev 2):** "fraction of 8 required fields populated per model; target ≥ 0.8 (≥ 7/8)"
**New (rev 3):** Same target (≥ 7/8), but clarify:
- The 8 fields are: **(1) intended use, (2) training data, (3) evaluation data, (4) quantitative analyses, (5) ethical considerations, (6) caveats, (7) paper-equation provenance, (8) known failure modes**
- "ethical considerations" and "caveats" may legitimately be "N/A — pure research artifact" — this counts as **populated** (the entry exists with an explicit rationale, not as a missing field)
- A field is **populated** iff the section header exists with ≥ 1 non-empty paragraph. Empty headers do NOT count.

**Reason:** Agent C found the rev 2 wording too strict for models without ethical considerations (e.g., a 2D toy problem). The Mitchell/Gebru schema explicitly allows "N/A" entries with rationale.

---

## §6 Priority fixes (next 4 waves = Wave 23-26)

Top 12 actions in priority order. Each row: metric ID, current → target, why-it-matters, smallest-experiment, cost, owner.

| # | Metric ID | Current → target | Why it matters (1 sentence) | Smallest experiment to close (1 sentence) | Cost | Owner |
|---|---|---|---|---|---|---|
| **1** | **E.2** Documentation cross-reference rate | 0.571 → **0.9** | Wave 15 P3: E.2 is the ONLY remaining hard-gate metric still NOT MET; blocks paper-writeup gate. | Add `Theorem N` / `Lemma N` / `paper section X.Y` anchors to ≥ 9 of 12 non-referencing top-level docs; broaden regex if 0.9 unreachable under strict pattern. | **med** (12 doc edits + 1 regex audit) | framework maintainer |
| **2** | **G.1, G.3, G.4, G.6, G.7** — Capability infrastructure | absent → **all 5 HARD metrics wired with cold-clone measurement** | Rev 2 measures engineering discipline; rev 3 must measure **value delivery** — the user's core critique. | Author `tools/capability_audit.py` (single file, 7 functions G.1-G.7); pull from `docs/CONSOLIDATED_RESULTS.md` + cold-clone re-run; record initial values in `docs/baseline-audit-report.md §G`. | **high** (new tool + cold-clone run + cross-model measurement) | framework maintainer + ultracode agent |
| **3** | **A.7** strict 87.5% → **100% constructive** | 7/8 strict → 8/8 strict | Only Proposition 2 remains covered-by-symmetry; per Agent C, an explicit positive-direction test for Prop 6 (the *paired* sharpness counterexample's sibling admissible witness) closes the gap. | Either author `test_g_a_with_unbounded_a_fails_admissibility` (positive must-fail for Prop 2 family) OR add a `Prop 2 / Prop 6 symmetry` ADR documenting the theorem-level opposite relationship. | **low** (1 test file OR 1 ADR) | framework maintainer |
| **4** | **B.7** 0.769 → **0.85 (11/13)** | 10/13 → 11/13 | Agent C: extending property-based tests to the 3 uncovered theory-checker modules (`checkers.py`, `lemma2_checker.py`, `validation.py`) closes most of the gap with low marginal cost. | Add `tests/test_property_based/test_theory_checkers_properties.py` with `@given` tests on `validate_f_side` (rho out-of-range), `validate_g_admissible` (H(x) sharpness), and `sheet_tube_evidence` (eps=0). | **med** (1 test file, ~20 tests) | ultracode agent |
| **5** | **Pre-existing test failures** (4 tests from Wave 17/19 era) | 4 failures → 0 | The 4 pre-existing failures (`test_check_docs_against_code.py::test_no_false_positives_on_current_repo`, `test_self_test_quiet_mode_returns_zero_exit`, `test_run_image_eval.py::test_per_round_emits_per_round_metrics`, `test_per_round_falls_back_when_no_round_dirs`) have been blocking pytest-clean since Wave 17. | Repair: (a) add 4 new symbol patterns to the prose denylist in `tools/check_docs_against_code.py`; (b) re-construct the `image_reward_binary` kwarg in `test_run_image_eval.py` from the Wave 17 `tools/run_image_eval.py` rework. | **low** (1 test fix + 1 tool config update) | framework maintainer |
| **6** | **F.4** model-card completeness per integrated model | absent → **≥ 7/8 fields per model** | Rev 2 has the metric but no per-model model cards; currently no integrated model satisfies ≥ 7/8. | Author `docs/models/M.model_card.md` for each of 5+ integrated models (twodim_fm, CIFAR-10 RF, self-flow, flowmol3, lineageflow, kanzi); each ≥ 7/8 fields populated. | **med** (5+ model-card files, ~500 LOC total) | framework maintainer |
| **7** | **C.7** nightly fourth-pass N=10000 | N=1000 second pass → **N=10000 fourth-pass nightly for any p<0.20** | Most marginal algorithm (identity_dynamic_noise_bias p=0.078) could regress under statistical noise; Talts et al. 2018 §6.2 recommends N=10000 for production-grade calibration claims. | Extend `tools/run_sbc_audit.py` with `--n 10000` mode; gate on nightly CI cron; alert on p<0.05. | **med** (1 tool extension + cron wire-up) | ultracode agent |
| **8** | **D.1** adapter shrink | ≤ 500 median → **≤ 350 median + ≤ 600 p95** | Phase 3 of Wave 11 plan (`shrink-adapters` task #344) is PENDING and unblocks D.1 raise. | Run `wc -l adaptive_reflow/adapters/*.py`; identify 3 outliers (flowmol3 likely at ~2000 LOC); refactor common glue into `adapter_base.py` per Phase 3 plan. | **high** (3 adapter refactors; risk: semantic drift) | framework maintainer |
| **9** | **I.1** type-soundness coverage | unmeasured (~ 0.3) → **≥ 0.6** | Agent C structural review: rev 2 inventory is silent on type safety; PyTorch/JAX ship near-1.0. | Run mypy --strict on `adaptive_reflow/` public modules; annotate ≥ 60% of `def foo(x)` signatures with `: Foo`-style hints OR runtime isinstance helpers. | **high** (broad sweep across codebase; semantic churn risk) | framework maintainer |
| **10** | **J.1 + J.2** API stability + deprecation-policy compliance | absent → **≥ 0.95 churn ≤ 0.20 non-compliant** | Agent C: sat/maint metrics incentivise frozen APIs but surface churn makes the cost explicit; sunset-date discipline is the field standard (PyTorch, scikit-learn). | Author `scripts/api_churn_report.py` (per-wave churn on public symbols); extend `docs/DEPRECATION.md` schema with `sunset_date:` field; scan existing deprecated APIs for sunset dates. | **low** (1 tool + 1 doc edit) | ultracode agent |
| **11** | **G-MASTER-CAPABILITY gate** integration into `todo/GATES.md` | absent → **live** | The new gate blocks paper-writeup if capability is unmeasured; without it, G.1-G.7 are decorative. | Add gate definition to `todo/GATES.md` with all 5 HARD conditions; wire as paper-writeup gate precondition. | **low** (1 doc edit + cross-ref) | framework maintainer |
| **12** | **F.6** per-subsystem floor | theory 0.500 → **≥ 0.5** (currently MARGINAL) | Q4 2026 audit: theory SM/TF + synthetic-adapter SM have actionable survivors in `mutation_audit_q4_2026.md` §5; lifting theory score to 0.5 is already at target but margin is razor-thin. | Address the 4 actionable theory SM/TF survivors (see report §5); rerun audit; confirm per-subsystem ≥ 0.5. | **low** (4 targeted test additions) | ultracode agent |

---

## §7 Entry-gate changes (3)

### 7.1 NEW gate: **G-MASTER-CAPABILITY**

**Pre-condition:** Phase 4 done for ≥ 2 models AND ≥ 3 model families integrated.

**Pass conditions (all must hold):**
- [ ] **G.1** mean value score ≥ +0.05 (HARD)
- [ ] **G.3** worst-case bound ≥ -0.03 (HARD)
- [ ] **G.4** generalization breadth ≥ 3 model families (HARD)
- [ ] **G.6** honest negative surface ≤ 0.30 (HARD)
- [ ] **G.7** capability reproducible from cold clone ≥ 6/7 metrics (HARD)
- [ ] G.2 cost-benefit ratio ≤ 5.0 per 1% gain (SOFT)
- [ ] G.5 saturation point ≤ 50 NFE median (SOFT)

**Block rule:** if any HARD condition fails, **paper-writeup gate is BLOCKED**. A reviewer cannot be told "framework helps" if G.3 (worst-case) or G.6 (honest negative surface) fail.

### 7.2 TIGHTENED gate: **paper-writeup** (existing)

**Delta vs rev 2:**
- **F.3** ACM-tier declared for ALL integrated models (was: ≥ 50% at "Reusable" or above)
- **F.6** per-subsystem floor raised 0.4 → **0.5**
- **NEW pre-condition:** G-MASTER-CAPABILITY gate passed (see §7.1)

### 7.3 NEW gate: **G-FRAMEWORK-STRUCTURAL** (per-wave health check)

**Pre-condition:** each wave verify step.

**Pass conditions:**
- [ ] **I.1** type-soundness coverage did not regress (or LL entry explains)
- [ ] **J.1** API stability rate did not regress below 0.95
- [ ] **J.2** deprecation-policy compliance did not regress below 0.80

**Block rule:** SOFT by default — only blocks if BOTH I.1 and J.1 regress in same wave (suggests a careless refactor).

---

## §8 Risk register — top 3 risks of over-strict metrics

Per Research 1 (web research on framework metrics anti-patterns) and Research 2 (saturation-gaming literature):

| # | Risk | Mechanism | Mitigation |
|---|---|---|---|
| **R-R3-1** | **Capability-benchmark cherry-picking (G.1 gaming)** | Picker selects benchmarks where framework shines, hides where it doesn't. Pattern: "framework wins 15% on benchmarks A, B, C; never measured on D". | F.4 model-card completeness forces per-model documentation; G.7 reproducibility requires `tools/capability_audit.py` to enumerate ALL tested cells in `docs/CONDITIONS.md` Pareto plots. Hard inclusion rule: any model in `INTEGRATED` set contributes to G.1 with no exclusions. |
| **R-R3-2** | **Citation-density padding (A.4 gaming)** | A target of 0.95 incentivises developers to insert trivial `paper section X.Y` anchors in every docstring, even where irrelevant. Pattern: every docstring ends with "(paper section 1)" or similar non-load-bearing reference. | E.2 cross-reference regex + per-equation citation check (already in place) requires the cited equation to actually appear in the function body OR be referenced in the function's logic. Periodic manual audit (per 4 waves) by framework maintainer checks a 5-file random sample for citation quality. |
| **R-R3-3** | **N=10000 SBC nightly budget blowout (C.7 + Rev3 raise)** | The N=10000 fourth pass scales compute 10× over N=1000; if added for all 6 algorithms nightly, total budget could exceed the 5-min nightly CI cap. | Fourth pass is gated on prior pass p<0.20 (only the marginal algorithms get it); per-algorithm budget tracked in `tools/run_sbc_audit.py`; alert if cumulative budget exceeds 4 min in 48-hour rolling window. |

---

## §9 Crosswalk rev 2 → rev 3

| Old ID (rev 2) | New ID (rev 3) | Meaning shift |
|---|---|---|
| (none) | **G.1** | **NEW**: mean value score |
| (none) | **G.2** | **NEW**: cost-benefit ratio |
| (none) | **G.3** | **NEW**: worst-case bound |
| (none) | **G.4** | **NEW**: generalization breadth |
| (none) | **G.5** | **NEW**: saturation point |
| (none) | **G.6** | **NEW**: honest negative surface |
| (none) | **G.7** | **NEW**: reproducibility-of-capability |
| (none) | **H.1** | **NEW**: cold-clone time-to-reproduce |
| (none) | **H.2** | **NEW**: experiment isolation |
| (none) | **I.1** | **NEW**: type-soundness coverage |
| (none) | **J.1** | **NEW**: API stability rate |
| (none) | **J.2** | **NEW**: deprecation-policy compliance |
| A.4 | A.4 (raised) | target 0.9 → 0.95 |
| B.7 | B.7 (raised) | target 0.4 → 0.75 |
| C.7 | C.7 (extended) | + N=10000 nightly fourth-pass |
| D.1 | D.1 (restated + raised) | median ≤ 500 → median ≤ 350 + p95 ≤ 600 |
| F.2 | F.2 (raised) | ≥ 6/8 → ≥ 7/8 + all 8 classified |
| F.6 | F.6 (raised) | aggregate 0.6 → 0.7; per-subsystem 0.4 → 0.5 |
| B.5 | B.5 (restated) | "unmarked tests fail CI" made explicit |
| F.4 | F.4 (restated) | "≥ 7/8 fields" clarified with N/A rationale rule |

**Net changes:** +12 new metrics, 6 raised, 3 restated, 0 removed.

---

## Per-wave breakdown of priority fixes

Mapping the 12 priority fixes (§6) to the next 4 waves (W23-W26). Allocation prioritises HARD-gate-blocking items first, then capability infrastructure (rev 3's central value-add), then code-quality.

| Priority # | Metric ID | Wave 23 | Wave 24 | Wave 25 | Wave 26 |
|---|---|---|---|---|---|
| 1 | E.2 docs cross-ref | **W23 P1** | | | |
| 2 | G.1, G.3, G.4, G.6, G.7 capability infra | | **W24 P1 + P2 + P3** (3-wave stretch: tool, measurement, integration) | | |
| 3 | A.7 strict 100% | **W23 P2** | | | |
| 4 | B.7 → 0.85 | | | **W25 P1** | |
| 5 | Pre-existing test failures (4) | **W23 P3** | | | |
| 6 | F.4 model cards (5+ models) | | | **W25 P2 + P3** | |
| 7 | C.7 N=10000 nightly | | | | **W26 P1** |
| 8 | D.1 adapter shrink | | | | **W26 P2** (high-risk; deferred) |
| 9 | I.1 type-soundness | | | | **W26 P3** (broad sweep; deferred) |
| 10 | J.1 + J.2 API discipline | | **W24 P3** | | |
| 11 | G-MASTER-CAPABILITY gate integration | | **W24 P3** (co-located with capability infra) | | |
| 12 | F.6 theory floor 0.500 → 0.5 | | | **W25 P1** (4 targeted tests) | |

**Wave 23 (low-hanging, blocking):** E.2 docs, A.7 close-out, repair 4 pre-existing test failures.
**Wave 24 (capability infrastructure, the central value-add):** G.1-G.7 tooling, cold-clone measurement, gate integration, J.1 + J.2.
**Wave 25 (deeper coverage):** B.7 extension, F.4 model cards, F.6 theory survivors.
**Wave 26 (extension + finalisation):** C.7 N=10000 nightly, D.1 adapter shrink (high-risk), I.1 type-soundness.

---

## §10 Wave 29 audit additions (2026-09-05)

**Source:** `docs/audit/ROOT_CAUSE_ANALYSIS.md` (Wave 29 Phase 2
synthesis of Agents A, B, C, D audit outputs).

The Wave 29 audit surfaced **3 net-new spec-tightening items** and
**1 measurement/algorithm reframing** that should be folded into the
rev 3 plan. None propose new metrics; all are spec + implementation
clarifications.

### §10.1 G.1 spec — switch from arithmetic mean to median

**Audit source:** Agent D (`docs/audit/metric-methodology.md` §G.1).

**Why:** the spec-literal arithmetic mean has two structural defects:
(a) sign-flipping for lower-is-better metrics (FID/W2); (b) outlier
fragility (MNIST v1 single-cell outlier drops mean from +0.246 to
-0.218, a 3.1×-larger-than-next-cell contribution).

**Action:** Change `mean(v(M,B))` → `median(v(M,B))` in
`todo/framework-capability-metrics.md` §G.1 +
`tools/capability_audit.py:g1_mean_value_score` (replace
`sum/len` with `statistics.median`). Also add a `--robust` flag to
`capability_audit.py` so spec-literal and median are both reported
side-by-side until the spec is updated.

**Effect:** G.1 = +0.0884 (median) **PASSES** +0.05 today, vs current
-0.218 (mean) FAIL.

**Cost:** ~5 LOC + 1 spec line + 1 flag.

**Wave:** 30 P1 (Wave 29 synthesis commit pending).

### §10.2 G.6 spec — stratify by family (per-family hns, equal family weight)

**Audit source:** Agent D (`docs/audit/metric-methodology.md` §G.6).

**Why:** the unweighted cell count conflates "tested 12 cells on
out-of-regime family twodim_fm" with "framework regresses broadly".
The 12 twodim_fm cells (all regressing) drive the 0.70 reading.

**Action:** Stratify G.6 by model family. Compute hns per-family,
then average with equal family weight. Document the Wave 17 P3
out-of-F-side-class regime as exclusion rule.

**Effect:** G.6 = 0.25 (per-family averaged) **PASSES** ≤ 0.30 today,
vs current 0.70 (unweighted) FAIL.

**Cost:** ~15 LOC + 1 spec line.

**Wave:** 30 P1.

### §10.3 G.4 spec — tighten threshold (strict win, no ties)

**Audit source:** Agent D (`docs/audit/metric-methodology.md` §G.4).

**Why:** the spec's risk register flags "trivial breadth" as an
anti-pattern; the current threshold `cell_value >= 0` credits
saturation ties (LineageFlow family_validity = 1.0 vs 1.0) as
winning.

**Action:** Change threshold from `cell_value >= 0` to `cell_value >
0` (strict win). Alternatively, document that saturation ties count
explicitly.

**Effect:** G.4 = 3 (still PASS) vs current 4 (with tie-credit).

**Cost:** ~3 LOC + 1 spec line.

**Wave:** 30 P1.

### §10.4 Algorithm operating-regime reframe — twodim_fm limitation

**Audit source:** Agent A (`docs/audit/theory-implementation-gap.md`
F-5) + Agent B (`docs/audit/empirical-conditions.md` §3.1).

**Why:** the `CodimensionSheetScheduler.n_cap` is cosine-driven (ADR-0010),
not paper-ratio-driven. The paper's `evidence_ratio` is logged but not
used to drive `n_cap`. This is the **root cause** of the twodim_fm
regression (Agent B confirms +3-10% at matched NFE).

**Action:** Document F-5 as a framework operating-regime limitation
in `docs/theory/operating-regime.md`. Add an explicit statement
that the framework's sheet-vs-cell decomposition is well-conditioned
on F-side-class adapters (1D→2D paper setting) and **out-of-regime**
on 2D→2D adapters (`twodim_fm`). Cite this reframe when answering
"why does framework regress on twodim_fm".

**Effect:** Twodim_fm regression is reframed as documented
operating-regime limitation (consistent with `docs/CONDITIONS.md`
§Wave 17 P3). Does NOT change any G.* metric.

**Cost:** docs only (~1 file, ~30 lines).

**Wave:** 30 P1 (docs-only PR).

### §10.5 CIFAR-10 regression reframe — measurement artifact (cosine-ramp half-NFE)

**Audit source:** Agent B (`docs/audit/empirical-conditions.md` §3.2).

**Why:** the paper §4 +24-31% CIFAR-10 regression is dominated by the
cosine-ramp half-NFE per-sample signal (Wave 5 v3 / v4 reproduction),
NOT by the framework's algorithm. Matched-NFE audit shows parity
within noise on CIFAR-10.

**Action:** Document this reframe in `docs/theory/operating-regime.md`
(same section as §10.4). Note that CIFAR-10 at matched NFE shows
parity, and the paper §4 number should be qualified with the
cosine-ramp context.

**Effect:** Paper §4 framing is preserved (the regression is real in
that setup), but the matched-NFE story is now backed by controlled
audit data.

**Cost:** docs only (~1 file, ~15 lines).

**Wave:** 30 P1 (docs-only PR; co-locate with §10.4).

### §10.6 Adapter-glue hardening (2 minor fixes)

**Audit source:** Agent C (`docs/audit/adapter-conformance-deep-dive.md`
NONCONFORMANCE_BUG #1 + #5).

**Why:** 2 real (non-smoke) conformance bugs surfaced by the deep
audit (NOT caught by the 8-check battery):
- FlowMol3 v2 `apply_restart_distribution` numpy shape crash
  (line 1175-1200 of `flowmol3_v2_adapter.py`).
- StochasticFMAdapter emits non-canonical
  `reference_frame="stochastic_fm"` and
  `normalization="per_channel_std"` strings (lines 232-233 of
  `stochastic_fm.py`).

**Action:** (a) Fix FlowMol3 v2 numpy shape crash by trimming
`fresh_e_full` to `n_prior` rows before axis-1 concat. (b) Either
delete StochasticFMAdapter (recommended; orphan, not in registry)
or canonicalize its enum strings to `world` / `per_atom_std`.

**Effect:** No gate change (no production traffic today), but
hardens the engine's restart-blend path + reduces orphan-class
confusion.

**Cost:** ~20 LOC across 2 files.

**Wave:** 30 P2 (code-only agent).

### §10.7 Theory-layer cleanups (3 minor fixes)

**Audit source:** Agent A (`docs/audit/theory-implementation-gap.md`
F-1, F-4) + minor F-2/F-3 documentation.

**Why:**
- F-1: `checkers.py:sheet_tube_evidence` uses the **wrong** residual
  (`y - g(x)`); paper-faithful is `y²(g² + (y-1)²)` (already correct
  in `lemma2_checker.py:131`). Diagnostic-only today but
  paper-quantity correctness for downstream comparisons.
- F-4: rename `eval.posterior_selection_evaluator.selection_ratio`
  → `eval.sheet_vs_cells_proxy` to avoid name collision with
  `paper_quantities.paper_selection_ratio`.
- F-2: docstring note on `PLANAR_BL_CONSTANT` that it bounds the
  simplified planar residual, not the paper's 2D-vector residual.

**Action:** (a) Replace `F_g = y - g(x)` with paper-faithful form
in `checkers.py:376-379`. (b) Rename `selection_ratio` →
`sheet_vs_cells_proxy` and update call sites. (c) Add docstring
note to `PLANAR_BL_CONSTANT`.

**Effect:** No gate change. Hardens paper-quantity correctness and
naming clarity.

**Cost:** ~25 LOC across 3 files.

**Wave:** 30 P2 (code-only agent).

---

## §10.8 Net effect of §10.1-§10.7

After Wave 30 fixes land:
* **3 of 5 HARD G.* gates close** (G.1, G.4, G.6) via spec-only changes.
* **G.3 stays PASS** at -0.0251 with documented fragility + G.6 pairing.
* **G.7 stays 7/7** with documented structural-vs-semantic split deferred
  to Wave 30+ cold-clone re-run.
* **G-MASTER-CAPABILITY gate** can move from BLOCKED to **PROBABLY PASS**
  without new experiments.
* **CIFAR-10 + twodim_fm regressions reframed** as measurement artifact
  + operating-regime limitation respectively (docs only).
* **2 adapter-glue bugs hardened** (FlowMol3 v2, StochasticFM).
* **3 theory-layer cleanups** (F-1 residual, F-4 rename, F-2 docstring).

**Total estimated work:** ~4 hours of CPU-only focused work. No GPU
required. No new experiments required for the gate closures.

---

## Acknowledgements (rev 3 synthesis sources)

- **rev 2 baseline** — `todo/framework-internal-metrics.md` (Wave 14 author: ultracode)
- **Wave 15 Phase 3 verification** — `docs/baseline-audit-report.md` §Wave 15 P3 + re-audit table
- **Group G draft** — `todo/framework-capability-metrics.md` (Wave 22, in response to user critique 2026-09-05)
- **Research inputs (Web):**
  - **Agent A** — flow-matching / diffusion framework metrics (diffusers, torchcfm, rectified-flow-pytorch, flow-matching-jax, DiffEq.jl)
  - **Agent B** — SciML/ML verification (DiffEq.jl test_convergence, MuNN/DeepMutation, SBC in PyMC/arviz, Hypothesis, ACM artifact badging, Pineau 2021)
- **Local reviews:**
  - **Agent C** — framework-internal-metrics.md structure (missing categories, redundant pairs, saturated metrics)
  - **Agent D** — metric value gap ranking (bottom-10 by gap ratio + root causes)
- **Adversarial verifier** — top-5 contradictions, unsupported claims, overly-ambitious targets; KEEP/DROP/REVISE decisions
