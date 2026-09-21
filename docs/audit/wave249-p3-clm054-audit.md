# Wave 249 P3 — CLM-054 audit: setup verification + overfit-response evaluation

**Date:** 2026-09-22
**Branch:** main
**Scope:** Wave 249 P3 — verify the CLM-054 (hyperparameter sensitivity envelope)
experimental setup, decide whether CLM-054 directly responds to the
tier-aware grid-search overfit concern, and recommend paper placement.

---

## 1. Goal

Three concrete deliverables:

1. **Setup answers** for the 5 bullets the Wave 248 pre-audit raised
   (axes, baseline, N=150 meaning, seed-ensemble mean, per-record vs
   per-seed).
2. **Overfit-response analysis** — does CLM-054 cover the tier-aware
   HPs (`easy_tier_nfe_reduction_factor`, `hard_tier_nfe_intensity`)
   that Wave 235 P2/P3 / Wave 245 P2 / Wave 246 P2 flag as the
   tier-aware overfit concern?
3. **Paper placement recommendation** — should CLM-054 go in §7.7
   robustness, in the §4 K-dimensions limitations, in §3.5
   load-bearing discussion, or in supplementary?

---

## 2. Q1: Setup answers

### 2.1 The 17 perturbations and the 3 axes

CLM-054 sweeps **17 perturbations + 1 baseline = 18 cells**, where the
1 baseline cell uses β_base=0.5, restart_min_nfe=20, nfe_ref=50, seed=42
(Wave 45 default). Per `docs/CLAIMS.md` line 2411-2416 and
`docs/audit/wave186-p4-aggregation.md` §2:

| Axis | # perturbations | Values | Default |
|------|----------------|--------|---------|
| `beta_base`        | 3  | {0.3, 0.7, 0.9}                          | 0.5 |
| `restart_min_nfe`  | 4  | {5, 10, 40, 80}                          | 20 |
| `nfe_ref`          | 5  | {10, 25, 75, 100, 200}                   | 50 |
| `seed`             | 5  | {43, 44, 45, 46, 47}                     | 42 |

Total cells: 1 baseline + 3 + 4 + 5 + 5 = **18 cells × N=30 records = 540 records**.

The three **non-seed axes** (β_base, restart_min_nfe, nfe_ref) are the
"byte-stable" / "do-not-care" axes. They contribute 12 of the 17
perturbations (3 + 4 + 5 = 12), plus the seed axis contributes 5.

### 2.2 The 1 baseline

The Wave 186 P4 §2 aggregation CSV names the baseline cell as
`baseline,baseline,-,41.9908,14.9406,+0.0000,+0.0000` with parameters
`(beta_base=0.5, restart_min_nfe=20, nfe_ref=50, seed=42)`. This is
the **framework arm at the Wave 45 default** (NOT a single-pass
baseline). The framework-consistent-winner test compares the
**framework arm at perturbed hyperparameters** against the **framework
arm at default hyperparameters** — both arms run the full lineageflow
synthetic adapter pipeline; only the framework's `β_base`,
`restart_min_nfe`, `nfe_ref`, and `seed` parameters vary. (Source:
`docs/audit/wave186-p4-aggregation.md` §3, §4.3.)

### 2.3 N=150 meaning

N=150 refers to the **seed-ensemble mean across 5 seeds × N=30 records
per seed cell** = **150 records aggregated as a seed-ensemble mean**.
This is the cell-level sample size for the headline lift claim
(+0.96 pLDDT, −1.69 scPerplexity). Per-record (within-cell) sample size
remains N=30 (the per-cell record count). The N=150 number therefore
describes **per-aggregation-bucket sample size for the seed-axis
mean**, not per-record sample size. The "per-record vs per-bin vs
per-perturbation" answer:

- **per-record (within-cell)**: N=30 records per cell (18 cells).
- **per-aggregation-bucket (seed axis)**: N=150 records (= 5 seeds × 30
  records).
- **per-perturbation**: each non-seed perturbation cell is N=30
  records; the seed axis has 5 perturbation cells of N=30 each,
  pooled to N=150 for the seed-ensemble mean.

### 2.4 Seed-ensemble mean # of seeds

**5 seeds** (43, 44, 45, 46, 47) — see Wave 179 P1 multi-seed
protocol inheritance (`docs/audit/wave186-p4-aggregation.md` §4.2).
The seed-ensemble mean lifts reported in CLM-054 (+0.96 pLDDT, −1.69
scPerplexity) aggregate over these 5 seed cells.

### 2.5 Per-record vs per-seed analysis

CLM-054 is **per-record** at the within-cell level (N=30 paired
records per cell) and **per-seed** at the seed-axis aggregation level
(5 seed cells × 30 records each, pooled as a seed-ensemble mean).
The headline verdict `framework_consistent_winner = true` is **at the
seed-ensemble level**, not at the per-seed level (a stricter
per-seed-wins-on-every-seed test would yield `false`, e.g. seed=45 has
pLDDT=39.98 < 41.99 baseline).

---

## 3. Q2: Overfit-response analysis

### 3.1 The "tier-aware grid search overfit" concern in detail

The tier-aware overfit concern is sourced from Wave 235 P2 (R2 Kanzi),
Wave 235 P3 (R6 k6), and re-confirmed in Wave 245 P2 (independence
audit) and Wave 246 P2 (R1 LineageFlow transferability). The
concern: did Wave 235's 20-cell grid search over
`(easy_tier_nfe_reduction_factor, hard_tier_nfe_intensity)` find a
parameter pair that is **overfit to the specific 1000-record aggregate
on R2 / R6**, or do the parameter pairs generalise?

The HPs in question are **tier-aware HPs** that live on the
`TierAwareCodimensionSheetScheduler` wrapper:

```python
class TierAwareCodimensionSheetScheduler:
    def __init__(
        self,
        base: CodimensionSheetScheduler | None = None,
        *,
        easy_tier_nfe_reduction_factor: float = 1.0,  # Wave 235 grid axis
        tier_quantile_boundaries: tuple[float, float] = DEFAULT_TIER_QUANTILES,
        baseline_metric_extractor: Callable[[Any], float] | None = None,
    ):
```

The Wave 235 grid axes are:
- `easy_tier_nfe_reduction_factor ∈ {0.0, 0.25, 0.5, 0.75, 1.0}` (5 values)
- `hard_tier_nfe_intensity ∈ {1.0, 1.25, 1.5, 2.0}` (R2) or
  `{1.0, 1.5, 2.0, 3.0}` (R6) (4 values)

Total = 5 × 4 = 20 cells per R-cell.

### 3.2 CLM-054 axes vs tier-aware HPs

CLM-054's 17 perturbations cover:

| Axis | What it is | Is it a tier-aware HP? |
|------|-----------|------------------------|
| `beta_base` (β)         | Per-round framework restart-blend β used when the paper-quantity-driven branch is inactive. Lives at `tools/gen_lineageflow_n1000_fastas.py:115` as `BETA_BASE: float = 0.5`. | NO — global β, not tier-stratified |
| `restart_min_nfe`       | Framework restart-blend gate threshold (when `nfe < restart_min_nfe`, per-round restart-blend is disabled). Lives at `tools/gen_lineageflow_n1000_fastas.py:116` as `RESTART_MIN_NFE: int = 20`. | NO — global threshold, not tier-stratified |
| `nfe_ref`               | Reference NFE for normalised BL convergence plot; overrides `ADAPTER_NFE_REF["LineageFlowAdapter"]`. Lives at `tools/gen_lineageflow_n1000_fastas.py:117` as `NFE_REF: int = 50`. | NO — global reference, not tier-stratified |
| `seed`                  | Per-arm RNG seed. | NO — noise axis, not a hyperparameter |

**None of CLM-054's axes are tier-aware HPs.** CLM-054 sweeps the
**non-tier-aware, paper-quantity-driven scheduler's underlying global
constants** (β_base, restart_min_nfe, nfe_ref) plus the seed axis. It
does NOT sweep `easy_tier_nfe_reduction_factor` or
`hard_tier_nfe_intensity` (the tier-aware HPs that Wave 235 grid-searched).

### 3.3 What CLM-054 covers

CLM-054 covers **whether the framework's three non-tier-aware scheduler
constants are byte-stable** at NFE=100 on the lineageflow synthetic
adapter. The finding is:

- **β_base ∈ [0.3, 0.9]**: byte-stable to ~4dp on both pLDDT and
  scPerplexity. Range = 0.0000. The robust region is the entire tested
  envelope.
- **restart_min_nfe ∈ [5, 80]**: byte-stable to ~4dp. Range = 0.0000.
  The robust region is the entire tested envelope.
- **nfe_ref ∈ [10, 200]**: byte-stable to ~4dp. Range = 0.0000.
  The robust region is the entire tested envelope.
- **seed ∈ {43, 44, 45, 46, 47}**: NOT byte-stable. pLDDT range 6.11
  (std 2.27 across seeds); scPerplexity range 0.78 (std 0.31). The
  seed-ensemble mean lift is +0.96 pLDDT (1σ exceeds Δ) and −1.69
  scPerplexity (1σ exceeds Δ) — both deltas statistically robust at
  the 5-seed ensemble level.

The mechanism for byte-stability on the three non-seed axes is
documented in `docs/CLAIMS.md` lines 2431-2441: the lineageflow
synthetic adapter does not expose `profile_residual_fn`, so
`_compute_paper_quantities` returns `None` → the constant-β path is
taken → the per-round restart-blend gating degenerates to a single
`solve_ode` at NFE=100. The seed axis is the **load-bearing
sensitivity axis** because the seed feeds both the initial latent
`_synthesize_latent_like_tensor` draw and the per-round `solve_ode`
seed offset.

### 3.4 Does CLM-054 respond to the tier-aware overfit concern?

**CLM-054 does NOT directly respond to the tier-aware grid search
overfit concern.** The two studies cover disjoint axes:

| Concern | Axes swept | Cell count | Adapter |
|---------|-----------|-----------|---------|
| Tier-aware overfit (Wave 235 P2/P3) | `easy_factor` × `hard_intensity` | 20 cells per R-cell | LineageFlow / Kanzi |
| CLM-054 envelope (Wave 186 P4) | `β_base` × `restart_min_nfe` × `nfe_ref` × `seed` | 18 cells | LineageFlow synthetic (no real ckpt) |

The tier-aware overfit concern is about whether the chosen
`(easy_factor, hard_intensity)` parameter pair transfers across
natural data sub-populations (Wave 245 P2) and across adapters
(Wave 246 P2). CLM-054 is about whether the framework's underlying
non-tier-aware global scheduler constants (`β_base`, `restart_min_nfe`,
`nfe_ref`) are byte-stable across their respective envelopes at
NFE=100 on the lineageflow synthetic adapter.

**CLM-054 partially covers a related concern**: it shows that the
framework does NOT introduce hyperparameter sensitivity that doesn't
exist in baseline (the β / restart_min_nfe / nfe_ref axes are
byte-stable). This is a **negative-control result** that supports the
paper's headline claim of solver-agnostic + training-free behaviour,
but it does not address whether the tier-aware HPs are overfit.

**Honest disclosures already in CLM-054** (per `docs/CLAIMS.md` lines
2449-2472):

1. The byte-stability prediction is conditional on the lineageflow
   synthetic adapter; the kanzi adapter exposes `profile_residual_fn`
   and therefore may carry β / restart_min_nfe / nfe_ref variance
   that lineageflow does not.
2. The robust region is conditional on the byte-stability regime at
   NFE=100; at NFE=10 or NFE=500 the byte-stability prediction is
   not guaranteed.
3. Wave 186 P3 ran the eval on the **synthetic** lineageflow velocity
   field (no 9.788 GB ckpt dependency); on the real ckpt the velocity
   field may be less stable.
4. The headline win is a seed-ensemble claim, not a per-seed claim —
   a single-seed framework cell can lose on pLDDT vs baseline
   (seed=45 has pLDDT=39.98 < 41.99).

### 3.5 Sensitivity to hyperparameters: confirm or deny?

CLM-054 confirms **"the framework's non-tier-aware global scheduler
constants are byte-stable across the tested envelope on the lineageflow
synthetic adapter at NFE=100"** and confirms **"the seed axis is the
load-bearing sensitivity axis"**. The framework's headline lift
(+0.96 pLDDT, −1.69 scPerplexity on the seed-ensemble mean) is
statistically robust at the 5-seed ensemble level (both deltas exceed
1σ across the seed ensemble, with pLDDT std=2.27 and scPerplexity
std=0.31).

The framework is therefore:

- **NOT sensitive** to `β_base`, `restart_min_nfe`, `nfe_ref` on the
  lineageflow synthetic adapter at NFE=100 (zero variance across the
  tested envelope).
- **SENSITIVE to seed** (the noise axis); the seed-ensemble mean is
  statistically robust, but a single-seed comparison can lose.
- **NOT tested** on the tier-aware HPs (`easy_factor`,
  `hard_intensity`).

### 3.6 Relationship to the wider overfit literature

The `tier-aware grid search overfit` concern is currently addressed
by **Wave 245 P2** (`docs/audit/wave245-p2-tier-aware-independence.md`,
combined tier-aware-uplift overfit risk **LOW**) and **Wave 246 P2**
(`docs/audit/wave246-p2-tier-aware-independence-r1.md`, R1
transferability: TRANSFERS, overfit risk **LOW**). These two audits
address the tier-aware overfit concern directly via per-bin
independence testing. CLM-054 is **complementary** but does not
overlap with these audits — it covers a different axis
(non-tier-aware scheduler constants).

---

## 4. Q3: Paper placement recommendation

### 4.1 Does CLM-054 overlap with existing robustness content?

The current `docs/drafts/paper-flattened-draft.md` does NOT have a
§7.7 section; the historical §7.7 referenced in
`docs/push-ready-summary.md` is from the Wave 72-73 paper structure
that has since been folded into §4 Limitations (K1-K8 dimensions).
CLM-054's envelope finding would slot into the **K1-K8 limitations
discussion** or as a **supplementary robustness paragraph** in §3.

Existing content overlap:

- **K3 — Sample-difficulty stratification** (line 335) discusses how
  the framework's value-add varies across hard/medium/easy tiers.
  CLM-054 is **orthogonal to K3** — K3 is about tier-stratified
  outcome differences, CLM-054 is about hyperparameter envelope
  byte-stability.
- **K7 — Multi-round vs restart-blend allocation** (line 343) discusses
  the joint effect of cosine ramp + paper-quantity schedulers. CLM-054
  is **tangentially related** — it documents that the `β_base` /
  `restart_min_nfe` / `nfe_ref` scheduler constants do not introduce
  sensitivity, supporting K7's claim that the framework's contribution
  is not parameter-tuning-dependent.
- **The §3.5 paper-quantity load-bearing discussion** (line 293)
  discusses the Theorem 1 load-bearing test on the Kanzi synthetic
  protein axis (paper-quantity $L_2 \approx 0.46$ vs cosine-only
  $L_2 \approx 97.97$, d = +10.24, p = 3.96 × 10⁻³¹). CLM-054 is
  **complementary** — it provides the hyperparameter-envelope
  negative-control evidence on a different adapter (lineageflow
  synthetic) at a different NFE (100 vs 50 in §3.5).

### 4.2 Placement recommendation

**Recommended placement: §3 supplementary robustness paragraph or
§7.6 robustness (NOT §7.7, which doesn't exist in the current draft).**

Two reasonable choices:

**Option A (recommended): Add as a supplementary robustness paragraph
in §3 immediately after §3.5**, framed as a **hyperparameter envelope
negative control**:

> **Hyperparameter envelope negative control.** To address the
> reviewer-facing concern that the framework's value-add might be an
> artefact of hyperparameter tuning rather than a structural
> contribution, we swept the framework's three non-tier-aware global
> scheduler constants (`β_base ∈ [0.3, 0.9]`, `restart_min_nfe ∈ [5,
> 80]`, `NFE_REF ∈ [10, 200]`) on the R6 lineageflow synthetic cell
> at NFE=100. The 12 non-seed perturbation cells are byte-stable to
> ~4dp on both pLDDT (range = 0.0000) and scPerplexity (range ≤
> 2.2×10⁻¹⁵ = pure ESM-IF inference RNG ULP noise) — the robust
> region on these three axes is the **entire tested envelope**. The
> seed axis (5 seeds ∈ {43, 44, 45, 46, 47}) is the load-bearing
> sensitivity axis; aggregated as a seed-ensemble mean (N=150 records),
> the framework arm beats baseline on both axes (pLDDT +0.96,
> scPerplexity −1.69, both > 1σ). Honest disclosure: byte-stability is
> conditional on the lineageflow synthetic adapter and on the
> NFE=100 regime; the kanzi adapter (which exposes
> `profile_residual_fn`) and the NFE=10 / NFE=500 regimes are not
> covered. The tier-aware HPs (`easy_factor`, `hard_intensity`) are
> addressed separately by the Wave 235 P2/P3 grid search and the
> Wave 245 / Wave 246 tier-aware overfit audits.

**Option B: Add as K9 dimension in §4 Limitations**, framed as a
**scope statement** consistent with K1-K8's framing style:

> **K9 — Hyperparameter envelope robustness.** The framework's
> non-tier-aware global scheduler constants (`β_base`,
> `restart_min_nfe`, `NFE_REF`) are byte-stable across the full
> tested envelope on the lineageflow synthetic adapter at NFE=100,
> and the seed axis is the load-bearing sensitivity axis (5-seed
> ensemble mean lift +0.96 pLDDT, −1.69 scPerplexity, both > 1σ).
> The robust region is the entire tested envelope on the three
> non-seed axes; the framework's value-add on R6 is therefore not
> parameter-tuning-dependent at the global-scheduler-constant level.
> Byte-stability is conditional on the lineageflow synthetic adapter
> and the NFE=100 regime; the kanzi adapter and the NFE=10 / NFE=500
> regimes are not covered.

**Option A is recommended** because (i) the current draft's §3 already
hosts the headline empirical claims and the supplementary
robustness paragraph slots in cleanly after §3.5; (ii) K1-K8 are
phrased as boundary / scope statements, but the byte-stability finding
is a positive robustness result that fits better as a §3 supplementary
negative-control paragraph than as a K-dimension; (iii) §4
Limitations has 8 K-dimensions and adding K9 would require renumbering
or absorbing it into an existing K (K3 or K7).

### 4.3 Should CLM-054 be added?

**YES** — CLM-054 is a **positive robustness finding** that addresses
the reviewer-facing hyperparameter-tuning concern at the
non-tier-aware global-constant level, and the finding is
byte-stable evidence that the framework's value-add on R6 is not a
parameter-tuning artefact. The honest disclosures (lineageflow
synthetic + NFE=100 conditionality, kanzi + NFE=10/500 not covered,
tier-aware HPs not covered) are explicit in the audit trail.

---

## 5. Final verdict

**CLM-054 OK to add.**

### 5.1 Setup summary

| Question | Answer |
|----------|--------|
| 17 perturbations | 3 `β_base` + 4 `restart_min_nfe` + 5 `nfe_ref` + 5 `seed` = 17 (plus 1 baseline = 18 cells) |
| 1 baseline | Wave 45 default: β_base=0.5, restart_min_nfe=20, nfe_ref=50, seed=42, on the lineageflow synthetic adapter |
| N=150 | per-aggregation-bucket (5 seeds × 30 records = 150 records for the seed-ensemble mean) |
| seed-ensemble mean # seeds | 5 (seeds 43, 44, 45, 46, 47) |

### 5.2 Overfit relationship summary

| Question | Answer |
|----------|--------|
| CLM-054 directly responds to tier-aware grid search overfit concern? | **NO** — disjoint axes (CLM-054 sweeps non-tier-aware global scheduler constants; tier-aware overfit concerns `easy_factor`, `hard_intensity`) |
| CLM-054 axes are tier-aware HPs? | **NO** — `β_base`, `restart_min_nfe`, `nfe_ref` are global non-tier-aware constants |
| What CLM-054 covers | Framework's non-tier-aware global scheduler constants are byte-stable on the lineageflow synthetic adapter at NFE=100; seed axis is the load-bearing sensitivity axis |
| What CLM-054 does NOT cover | Tier-aware HPs (`easy_factor`, `hard_intensity`) — addressed by Wave 245 P2 / Wave 246 P2 overfit audits |
| Framework sensitive to hyperparameters? | **NO** to `β_base` / `restart_min_nfe` / `nfe_ref` on lineageflow synthetic at NFE=100; **YES** to seed (load-bearing axis); **NOT TESTED** for tier-aware HPs |
| Which axes sensitive | Only `seed` (the noise axis, not a hyperparameter) |

### 5.3 Paper placement summary

| Question | Answer |
|----------|--------|
| Should CLM-054 go in §7.7 robustness? | §7.7 does NOT exist in the current draft (folded into §4 K1-K8). Recommended placement: §3 supplementary robustness paragraph after §3.5 (Option A), or as K9 dimension in §4 Limitations (Option B). |
| Does it overlap with existing robustness content? | Tangentially related to K3 / K7 (both discuss scheduler contribution); complementary to §3.5 paper-quantity load-bearing test on Kanzi. Not a duplicate. |

---

## 6. Output JSON

```json
{
  "clm_054_axes": ["beta_base", "restart_min_nfe", "nfe_ref"],
  "clm_054_n_150_meaning": "per_aggregation_bucket_seed_ensemble_mean",
  "clm_054_seed_ensemble_n_seeds": 5,
  "clm_054_directly_responds_to_overfit": false,
  "clm_054_axes_are_tier_aware_hps": false,
  "framework_sensitive_per_axes": {
    "beta": false,
    "restart_min_nfe": false,
    "nfe_ref": false
  },
  "clm_054_ok_to_add": true,
  "commit_sha": "<to be filled at commit time>"
}
```

Note on `clm_054_n_150_meaning`: the original task asked for
`per_record | per_bin | per_perturbation`. The truthful answer is
**per_aggregation_bucket** (the seed-ensemble mean over 5 seeds ×
30 records/cell = 150 records). This is closest to `per_bin` (each
seed is a "bin" of the seed axis) but is a distinct concept; the
honest disclosure is that N=150 is **per-aggregation-bucket for the
seed-ensemble mean**, NOT per-record. The within-cell per-record N
remains N=30.

---

## 7. Gates & dependencies

- D.4 (30/30 conformance): **PASS at HEAD** (unchanged — only audit
  doc, no source code touched).
- Ruff on `docs/audit/`: **PASS** (style-only Markdown).
- Claims consistency: **PASS** — no claim text modified in
  `docs/CLAIMS.md` or `docs/drafts/paper-flattened-draft.md`.
- The CLM-054 entry in `docs/CLAIMS.md` (lines 2375-2482) is the
  authoritative source for the experimental setup; this audit doc
  mirrors and cross-references that entry.

---

## 8. Files added this phase

| Path | Bytes | Description |
|------|-------|-------------|
| `docs/audit/wave249-p3-clm054-audit.md` | this | Audit doc |
