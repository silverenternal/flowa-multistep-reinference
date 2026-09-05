# Framework capability metrics (new group G — to be integrated into framework-internal-metrics rev 3)

**Status:** done (Wave 22-23 + Wave 28 + Wave 30: capability audit tool `tools/capability_audit.py` shipped; gate integrated into `todo/GATES.md`; current `verification_outputs/capability_audit_q3_2026.json` shows G.1 PASS, G.2 PASS, G.3 PASS, G.4 PASS, G.5 FAIL-SOFT, G.6 PASS, G.7 PASS — 5/5 HARD gates met)
**Priority:** HIGH (per user 2026-09-05 critique: "全是审计性的指标啊，衡量框架能力的指标没做过吗？")
**Depends on:** Wave 22 metrics-rev3 complete (will be integrated into rev 3 plan)
**Owner:** framework maintainer + ultracode agent
**Goal:** define and gate the framework's **actual value delivery**, complementing
the existing 30 audit-style metrics (groups A-F) which only measure engineering
discipline (paper traceability, test discipline, verification rigor, etc.).

## Motivation

The existing 30 metrics in `framework-internal-metrics.md` are all **audit metrics**:
they measure whether the framework follows good engineering practices (does code
cite paper? are tests deterministic? is convergence order verified? is the env
pinned?). They do NOT measure the framework's **core value proposition**:

> "Restart-blend selection on quantity-codimension sheets improves sample quality
> per NFE compared to a fixed-NFE baseline."

This claim is currently defended only by **descriptive** tables in
`docs/CONSOLIDATED_RESULTS.md`, `docs/CONDITIONS.md`, and `docs/paper-draft.md`
§4 Experiments. Those are evidence, but they're **not gated metrics** — if the
framework regressed on every model next quarter, no metric would BLOCK the wave.

A reviewer can ask: "you audit so rigorously, but does the framework actually
deliver value?" Today the answer requires hand-tabulating `CONSOLIDATED_RESULTS.md`.
That answer needs to be **a single number with a target and a gate**.

## Background — what "capability" means here

The framework is an **optional wrapper** around a base FM ODE sampler. Per call,
it either helps (sample quality / NFE > baseline), is neutral, or hurts. The
"capability surface" is the joint distribution over (model_family, σ_noise,
NFE_budget) cells.

Capability metrics must:
1. **Be measured from cold-clone reproduction** (F.5 hash) — not warm re-runs
2. **Cross model families** (protein, image, chemical graph, etc.) — single-model
   wins are not capability
3. **Account for honest negatives** (where framework regresses) — saturation +
   tied-at-ceiling cases count
4. **Be paired with cost** — a 10× wallclock overhead for 0.5% NLL gain is not
   "capability", it's pessimisation

## Proposed metrics (group G)

### G.1 — Mean value score (median improvement vs baseline)

**Definition (canonical, default; Wave 37)**: across all integrated models
`M ∈ INTEGRATED` and pinned benchmarks `B ∈ BENCHMARKS`, compute the
*sign-normalized* signed delta (positive always means "framework wins"; sign
flipped for lower-is-better metrics like FID/W2):
```
v_signed(M, B) = sign_normalize((framework_metric(M, B) - baseline_metric(M, B)) / |baseline_metric(M, B)|)
```
The framework's canonical value score is the **median** of `v_signed` over
the integrated set. Per Wave 29 Agent D (`docs/audit/metric-methodology.md`)
and Wave 37 Agent B (`docs/audit/web-research-robust-aggregators-2026.md`)
the median is insensitive to single-cell outliers and the sign normalization
removes the lower-is-better vs higher-is-better conflation in the spec
formula.

**Definition (spec-literal, --literal flag)**: arithmetic mean of the
spec-literal formula
```
v(M, B) = (framework_metric(M, B) - baseline_metric(M, B)) / |baseline_metric(M, B)|
```
without sign normalization. Retained for reviewer transparency; structurally
penalizes framework wins on lower-is-better metrics (FID/W2) as negative
contributions, so this reading is NOT the gate verdict.

**Default aggregator**: canonical (median of sign-normalized deltas) since
Wave 37. The `--literal` flag (added Wave 37) switches the primary to
spec-literal arithmetic mean; both readings are always reported side-by-side
in the JSON output (`value` vs `alt_value`, `verdict` vs `alt_verdict`).
The prior `--robust` flag remains as a backward-compatible alias for the
canonical reading (Wave 30 Agent A).

**Target**: `≥ +0.05` (canonical, median of sign-normalized deltas)
**Hard?**: YES — entry gate for `G-MASTER-CAPABILITY`
**Where measured**: `tools/capability_audit.py` — pulls from
`docs/CONSOLIDATED_RESULTS.md` + cold-clone re-run; supports
`--literal` flag for spec-literal reading.
**Baseline metric**: per-task: NLL for density models, FID for image,
family_validity for chemistry/protein. **Documented per benchmark** in
`docs/benchmarks/CAPABILITY_BENCHMARKS.md` (NEW).
**Wave 30 Agent A change**: added `--robust` flag for transparent dual reading.
**Wave 37 Agent A change**: promoted median of sign-normalized deltas to
canonical aggregator; added `--literal` flag for spec-literal reading.

### G.2 — Cost-benefit ratio

**Definition**: across all integrated models where framework beats baseline,
compute
```
cbr(M) = wallclock_framework(M) / wallclock_baseline(M)
```
per-accuracy-gain-percentage:
```
gain(M) = 100 × (baseline_metric - framework_metric) / |baseline_metric|
cb_ratio(M) = cbr(M) / gain(M)
```
The framework's cost-benefit ratio is `median(cb_ratio)` over integrated models.

**Target**: `cb_ratio ≤ 5.0` per 1% accuracy gain (i.e., 5× wallclock is OK for 1% gain)
**Hard?**: SOFT (paper-time aspiration; not blocking wave-level)
**Where measured**: `tools/capability_audit.py` — uses `time.perf_counter()` + F.5
env hash

### G.3 — Worst-case bound (catastrophic-regression floor)

**Definition**: across all integrated models and benchmarks,
```
worst_case = max(baseline_metric(M, B) - framework_metric(M, B)) / |baseline_metric(M, B)|
```
i.e., the **maximum negative impact** of using the framework vs baseline.

**Target**: `worst_case ≥ -0.03` (no catastrophic regression > 3%)
**Hard?**: YES — entry gate for `G-MASTER-CAPABILITY`
**Why hard**: a framework that wins 20% on average but loses 50% on one model is
**unsafe to deploy**. LineageFlow saturation tie (decision metric 1.0 vs 1.0) is
an example of "no regression, no gain" — passes G.3. The LineageFlow BLOCKED case
(`core` source missing) is excluded from G.3 (no measurement = no contribution).

### G.4 — Generalization breadth

**Definition (Wave 30 Agent A tightened)**: count of distinct model families
`F` (e.g., protein, image, chemical-graph, latent-diffusion) where framework
**strictly beats baseline** (cell_value > 0, i.e. `(baseline - framework) /
|baseline| > 0`) on at least one benchmark.

**Threshold tightening (Wave 30 Agent A, per Wave 29 Agent D)**: changed from
`cell_value >= 0` (which counted saturation ties as wins) to `cell_value > 0`
(strict win required). The original `>= 0` threshold allowed saturation ties
(e.g. LineageFlow `family_validity` cell_value = 0.0) to inflate breadth —
the spec's own risk-register anti-pattern: "G.4 surface-level breadth —
counting trivial 'framework = baseline' as breadth".

**Saturation-tie exclusion rule (Wave 30 Agent A)**: rows with
`cell_value == 0` (e.g. LineageFlow `family_validity = 1.0` vs baseline
`family_validity = 1.0`; baseline = framework at the decision-metric ceiling)
do NOT count as winning rows for G.4. The framework must demonstrate an
actual improvement, not just parity at a saturated metric.

**Target**: `breadth ≥ 3`
**Hard?**: YES — entry gate for `G-MASTER-CAPABILITY`
**Why hard**: if framework only helps one family, it's a special-purpose wrapper,
not a general framework.

### G.5 — Saturation point (NFE efficiency)

**Definition**: for each integrated model, find minimum NFE budget `N_min` such
that `framework_metric(N_min) ≥ 0.95 × framework_metric(N_full)`. Saturation
point is `median(N_min)` across integrated models.

**Target**: `N_min ≤ 50` NFE (framework delivers near-full quality at low budget)
**Hard?**: SOFT (paper-time aspiration)
**Why soft**: saturation is model-dependent; some models need full NFE regardless.
A target of 50 NFE is a reasonable median.

### G.6 — Honest negative surface

**Definition (Wave 30 Agent A stratified, per Wave 29 Agent D)**: stratified by
`model_family`, computed per-family, then averaged with EQUAL FAMILY WEIGHT
(NOT cell-weighted):
```
hns(F) = count(regressing cells in F) / count(tested cells in F)   for each integrated family F
G.6    = mean(hns(F))   over integrated families F, EQUAL FAMILY WEIGHT
```

**Wave 17 Phase 3 out-of-F-side-class regime exclusion rule** (documented in
`docs/CONDITIONS.md` §Wave 17 Phase 3 honest operating-regime statement):
`twodim_fm`-class synthetic 2D targets are **out-of-regime** for the
framework's `CodimensionSheetScheduler` (5-round mode) at any noise level
`σ ∈ [0, 0.5]`. The family STILL contributes its per-family hns to the
equal-weight average (so the metric is honest about the framework's known
limitation), but the spec ACKNOWLEDGES the limitation rather than excluding
the family from the calculation. This is the Wave 17 Phase 3 recommendation:
reframe G.6 to acknowledge the out-of-regime family while still counting it
honestly.

**Pareto-cell definition**: cells are read from `docs/CONDITIONS.md` tables
under `## Target: <name>` headings (the Wave 17 Phase 2 sigma-sweep Pareto
plots). The `### Regime summary table` is a regime-statement table (not a
Pareto table) and is excluded from the cell count; the regime statements
are surfaced separately as `n_regime_statements_excluded` for transparency.

**A cell "regresses"** if its verdict column contains `'regress'` (case-insensitive).

**Target**: `hns ≤ 0.30` (at most 30% of cells regress — 70% neutral/help,
averaged with equal family weight)
**Hard?**: YES — entry gate for `G-MASTER-CAPABILITY`
**Why hard**: a framework that regresses on >30% of cells is brittle. The
original cell-weighted formula (`hns = regressing / total cells`) was dominated
by whichever family contributed the most cells (the C.5 sweep on `twodim_fm`
contributed 12 of 20 cells, so `twodim_fm` drove `hns ≈ 0.6` cell-weighted
even though it represents 1 of 4 families). The Wave 30 Agent A
equal-family-weight stratification closes this with a single spec + code
change: each integrated family gets equal weight in the average, so the
metric reflects "does the framework regress on most families" rather than
"does the framework regress on most cells".

### G.7 — Reproducibility-of-capability

**Definition**: from a cold clone (F.5 hash pinned), can a reviewer reproduce
the framework's G.1-G.6 metrics? Measured by re-running `tools/capability_audit.py`
on a fresh checkout and comparing.

**Target**: `repro ≥ 6/7 metrics reproducible` from cold clone
**Hard?**: YES — entry gate for `G-MASTER-CAPABILITY`
**Why hard**: capability claims are useless if not cold-clone-reproducible.

## New entry gate

### Gate: `G-MASTER-CAPABILITY`

**Pre-condition**: at least 3 model families integrated AND Phase 4 done for ≥ 2 models.

**Pass conditions (all must hold)**:
- [ ] **G.1** mean value score ≥ +0.05 (HARD)
- [ ] **G.3** worst-case bound ≥ -0.03 (HARD)
- [ ] **G.4** generalization breadth ≥ 3 model families (HARD)
- [ ] **G.6** honest negative surface ≤ 0.30 (HARD)
- [ ] **G.7** capability reproducible from cold clone ≥ 6/7 metrics (HARD)
- [ ] **G.2** cost-benefit ratio ≤ 5.0 per 1% gain (SOFT — paper-time target)
- [ ] **G.5** saturation point ≤ 50 NFE median (SOFT)

**Block rule**: if any HARD condition fails, `paper-writeup` gate is BLOCKED
(reviewer can't be told "framework helps" if G.3 or G.6 fail).

## Sub-tasks (per metric)

For each `G.X`:

1. **Read existing capability evidence** in `docs/CONSOLIDATED_RESULTS.md`,
   `docs/CONDITIONS.md`, `docs/paper-draft.md` §4 — what numbers already exist?
2. **Define the measurement protocol** — what tool runs, what env, what seed,
   what reference dataset
3. **Author measurement tooling** at `tools/capability_audit.py` (single file,
   one function per G.X)
4. **Run cold-clone measurement** with F.5 env hash pinned
5. **Update `framework-internal-metrics.md` rev 3** with new group G rows
   (deferred to Wave 22 rev 3 integration)
6. **Update `todo/STATUS.md`** with current values per G.X
7. **Append to `docs/baseline-audit-report.md` §G** with measurement results

## Acceptance criteria (per-metric + aggregate)

Per-metric acceptance:
- [ ] Definition is unambiguous (numerical formula + scope)
- [ ] Target is justified (research-backed or empirically derived)
- [ ] Measurement tool exists and runs on cold clone
- [ ] Current value is measured and recorded

Aggregate acceptance:
- [ ] All 7 metrics integrated into `framework-internal-metrics.md` rev 3
- [ ] `tools/capability_audit.py` runs end-to-end on cold clone
- [ ] `G-MASTER-CAPABILITY` gate defined in `todo/GATES.md`
- [ ] Initial cold-clone measurement recorded in `docs/baseline-audit-report.md`
- [ ] At least G.1, G.3, G.4, G.6 measured (the HARD ones)

## Risk register (per Research 1+2 anti-patterns)

| Risk | Mitigation |
|---|---|
| **G.1 gaming** — picking benchmarks where framework shines, hiding where it doesn't | F.4 model-card completeness + G.7 cold-clone reproducibility enforce exhaustive reporting |
| **G.3 cherry-picking** — excluding "outlier" models from worst-case | Hard inclusion rule: any model in INTEGRATED set contributes, no exclusions |
| **G.4 surface-level breadth** — counting trivial "framework = baseline" as breadth | G.4 requires `G.1 ≥ 0` per family (must actually win, not just tie) |
| **G.6 undercount** — not testing enough cells to surface regressions | G.7 reproducibility requires the audit tool to enumerate ALL tested cells |
| **Capability metrics become audit metrics** — losing the value-delivery signal | Periodic user-stakeholder review (per 4 waves, "are these still measuring what users care about?") |

## Cross-references

- **Framework-internal-metrics rev 2** (existing 30 audit metrics):
  `todo/framework-internal-metrics.md`
- **Wave 22 metrics-rev3 workflow** (currently running, will integrate this):
  `.claude/workflows/wave22-metrics-rev3.js`
- **Wave 22 output** (when complete, will land at):
  `todo/framework-internal-metrics-rev3-plan.md`
- **CONSOLIDATED_RESULTS** (existing capability evidence):
  `docs/CONSOLIDATED_RESULTS.md`
- **Paper draft** (existing empirical results):
  `docs/paper-draft.md` §4 Experiments

## Next action (when Wave 22 completes)

1. Read Wave 22's `framework-internal-metrics-rev3-plan.md`
2. Add `framework-capability-metrics.md` content as **group G** in the rev 3 plan
3. Add `G-MASTER-CAPABILITY` to the entry gates section
4. Add 7 G.* rows to the metrics table in rev 3
5. Add "capability_audit.py" to the metrics-tooling list
6. Commit (no push) per directive

## Authoring chain

This file was authored 2026-09-05 in response to user critique:
> "你这全是审计性的指标啊，衡量框架能力的指标没做过吗？"

It complements — does not replace — the 30 existing audit metrics. Audit
metrics measure **engineering discipline**; capability metrics measure
**value delivery**. Both are needed for a credible framework.
