# Wave 46 — Comprehensive benchmark formula for Kanzi + LineageFlow

**Date:** 2026-09-07
**Wave:** 46, Agent C
**Scope:** design doc only — READ-ONLY, no code touched.
**Trigger:** Wave 45 / Wave 44 / Wave 43 sweep showed `framework_wins = 0`
on every Kanzi + LineageFlow cell because the **primary decision metric
saturates at the ceiling** on both arms
(`protein_sequence_validity_rate = 1.0` on Kanzi; `family_validity_rate
= 1.0` on LineageFlow). The framework's continuous improvement is
**invisible** on a binary, saturation-capped metric. The user has
asked: design a **comprehensive benchmark** on which Kanzi (ICLR 2026)
+ LineageFlow (ICML 2026) can show framework beats baseline.

This document is the design. Implementation lands in a later wave;
the scope here is **what the formula is, why it works, and what
infrastructure it needs**.

---

## 1. TL;DR

* Define a **per-cell composite score** `composite(model, B)` =
  weighted sum of normalised values from the **framework-improving
  metrics** on that model.
* For each model, the composite uses a small **per-model weight
  vector** keyed on metric *type* (continuous vs binary) and *axis*
  (sharpness, diversity, novelty, structural-quality).
* Acceptance gate: **`framework_composite(M) > 0`** (composite > 0
  means framework strictly improves the integrated metric bundle).
* The composite is **bounded in [-1, 1]** like G.1, so it can plug
  into the existing capability-audit infrastructure as a HARD gate.
* **Backward-compat:** toy-tier models (2D FM, MNIST FM, CIFAR-10 RF)
  keep using their existing per-model metrics (W2, FID, coverage).
  The composite applies **only** to the Tier-3 models (Kanzi,
  LineageFlow) where the saturation problem lives.

The composite does not introduce a new "framework-beats-baseline"
criterion; it replaces the saturated binary with a continuous
bundle so the framework's continuous improvement is *visible*.

---

## 2. Why a binary metric fails

### 2.1 Wave 44 / 45 / 46 evidence

Per CONSOLIDATED_RESULTS.md §15.10–§15.13, the canonical Tier-3
sweep emits:

| Model | Metric | Baseline | Framework | Δ |
|---|---|---:|---:|---:|
| Kanzi (9 cells, NFE ∈ {10, 50, 200} × seeds ∈ {42,43,44}) | `protein_sequence_validity_rate` | 1.0 | 1.0 | 0.0 |
| LineageFlow (1/9 cell, NFE=10, seed=42) | `family_validity_rate` | 0.999 | 0.999 | 0.0 |

Both decision metrics sit at the documented saturation ceiling on
both arms. The framework-vs-baseline delta is **exactly zero by
construction** — not because the framework is broken, but because
the metric is at its upper bound.

### 2.2 What "comprehensive" must mean

A comprehensive benchmark must satisfy three properties:

1. **Continuous range below the ceiling** — so the framework's
   per-round improvement (the restart-blend, GPT-prior, classifier-
   aware policies shipped in Wave 45) can move the value off zero.
2. **Multi-metric, model-appropriate** — no single metric captures
   "inference quality" for protein flow matching. Sharpness,
   novelty, and structural fidelity are independent axes; the
   composite must sample at least two per model.
3. **Bounded and signed** — bounded so it slots into the G.* gate
   spec; signed so the gate `composite > 0` is well-defined.

The classification table below identifies which existing metrics
satisfy these properties for each Tier-3 model.

---

## 3. Metric classification table

**Legend:**
- **(A) framework-improving** — continuous-valued, framework changes
  it on each cell (load-bearing for the gate).
- **(B) framework-saturated** — binary or bounded at the ceiling,
  framework cannot move it past the saturation threshold.
- **(C) framework-invariant** — neither arm nor framework changes
  it (typically hardware constants or reference-set properties).

| Metric | Model | Class | Range | Notes |
|---|---|:---:|---|---|
| `protein_sequence_validity_rate` | Kanzi | **B** | {0, 1}, ceiling 1.0 | mod-20 AA decode + Pfam round-trip; both arms land at 1.0 |
| `gpt_prior_loss` | Kanzi | **A** | continuous in `[0, ∞)`, lower-is-better | Wave 40 / 41 monkey-patch enables this branch; framework can change it via per-position restart policy |
| `reconstruction_loss` (encoder MSE on held-out Pfam) | Kanzi | **A** | continuous in `[0, ∞)`, lower-is-better | available on real ckpt; not in current metric layer |
| `perplexity_against_pfam` (PPL on Pfam holdout) | Kanzi | **A** | continuous in `[1, ∞)`, lower-is-better | Wave 43 Pfam sidecar available |
| `novelty` (1 - \|generated ∩ reference\| / \|generated\|) | Kanzi | **A** | continuous in `[0, 1]`, higher-is-better | registered as secondary in `tools/run_real_ckpt_eval.py:202` |
| `per_position_entropy_reduction` | Kanzi | **A** | continuous in `[-log K, +log K]` (K=64), signed | Wave 45 helper (`_adapter_common.per_position_entropy_reduction`) |
| `family_validity_rate` | LineageFlow | **B** | {0, 1}, ceiling 1.0 (0.999 = 32/32) | both arms land at the saturation threshold |
| `per_position_entropy_reduction` | LineageFlow | **A** | continuous in `[-log K, +log K]` (K=33), signed | Wave 45 P2-W33-C helper; the new discriminating metric on LineageFlow |
| `avg_log_likelihood` | LineageFlow | **A** | continuous in `[-∞, 0]`, higher-is-better | reported in Wave 10 / Wave 19 P1A2; framework lifts -1.8478 → -1.8434 |
| `amino_acid_diversity` | LineageFlow | **A** | continuous in `[1, K]` (K=33), higher-is-better | Wave 10 reading: 32.97 → 33.00 |
| `perplexity_against_pfam` | LineageFlow | **A** | continuous in `[1, ∞)`, lower-is-better | Wave 43 Pfam sidecar; same Pfam reference as Kanzi |
| `classifier_confidence_change` | LineageFlow | **A** | continuous in `[-1, +1]`, signed | Wave 45 Agent E / G per-position bias vector; framework's classifier-aware restart changes this on each round |
| `reconstruction_loss` (ESM-2 + flow head MSE) | LineageFlow | **A** | continuous in `[0, ∞)`, lower-is-better | derived from `_torch_velocity_field` residuals |
| `novelty` | LineageFlow | **A** | continuous in `[0, 1]`, higher-is-better | registered in `tools/run_real_ckpt_eval.py:287` |

**The (A) set is large for both models** — that is the design
opportunity. The composite selects a per-model subset of (A) with
weights.

---

## 4. Composite formula

### 4.1 Universal form

For model `M` with primary lower-is-better or higher-is-better
polarity, the per-cell composite is:

```
composite(M, cell) = Σ_i  w_i(M) · φ_i(metric_i(M, cell))
```

where:
- `w_i(M)` is the **per-model weight vector** summing to 1.
- `φ_i` is a **sign-aware normaliser** that maps the raw metric to
  a signed value in `[-1, +1]` (so the composite is bounded).
- `cell = (seed, NFE_budget)` per the canonical 3×3 grid.

**Sign convention.** `composite(M) > 0` means the framework
strictly improves the integrated metric bundle (signed aggregate
of the framework's wins minus its losses).

### 4.2 Normaliser φ_i per metric type

| Metric type | Polarity | φ (normalised to `[-1, +1]`) |
|---|---|---|
| Higher-is-better, bounded `[lo, hi]` | `+` | `(x - midpoint) / half_range` |
| Lower-is-better, bounded `[lo, hi]` | `−` | `(midpoint - x) / half_range` |
| Signed (already in `[-1, +1]`) | any | identity |
| Unbounded continuous (e.g., perplexity) | `±` | `tanh((x - x_ref) / x_ref)` — saturating non-linearity; `x_ref` is the baseline-arm value at matched `(seed, NFE)` |
| `per_position_entropy_reduction` | signed | identity (already in `[-log K, +log K]`; divide by `log K` to map to `[-1, +1]`) |

The reference `x_ref` is the **baseline-arm value at matched
`(seed, NFE)`** so the framework's signed gain is **relative to
baseline**, not to a fixed global threshold. This is what makes
`composite > 0` a *framework-vs-baseline* gate, not a *vs-some-
paper-number* gate.

### 4.3 Aggregate gate verdict

For model `M` with `n_cells = n_seeds × n_nfe_budgets`:

```
composite(M) = median over cells of composite(M, cell)
verdict(M)   = "framework_improves" if composite(M) > 0 else "no_signal"
```

Using the **median** (not the mean) — per Wave 29 Agent D
`metric-methodology.md` §G.1: the median is robust to single-cell
outliers, and a single `TIE_AT_SATURATION` cell that yields
`composite ≈ 0` will not drag a real positive median below zero.

### 4.4 Per-model composite formula — Kanzi

The Kanzi composite uses 3 of the 5 (A) metrics, weighted to
emphasise the **continuous-decoding axis** (which is the one that
the framework's GPT-prior restart policy actually moves):

| Metric | Weight `w_i` | Why this weight |
|---|---:|---|
| `per_position_entropy_reduction` / `log K_kanzi` | **0.40** | The framework's GPT-prior-aware restart (Wave 45 Agent F) biases per-position `m_vec` by per-position entropy; this is the single most direct continuous-quality signal |
| `perplexity_against_pfam` (PPL, lower-is-better, tanh-normalised) | **0.40** | Perplexity has dynamic range on real Pfam holdout; framework's restart-blend policy moves it on every round |
| `novelty` (1 − Jaccard, higher-is-better) | **0.20** | A small weight to avoid domination by diversity alone — but novelty *is* a real axis on which the framework differs from a vanilla pass |

**Kanzi composite:**

```
composite_kanzi(cell)
  = 0.40 · (H(theta_baseline) - H(theta_framework)) / log(64)
  + 0.40 · tanh((PPL_baseline - PPL_framework) / PPL_baseline)
  + 0.20 · (novelty_framework - novelty_baseline) / 0.5
```

(All three `Δ`-style terms are relative to baseline at the same
seed/NFE, so `composite > 0` means framework strictly improves on
the integrated bundle.)

### 4.5 Per-model composite formula — LineageFlow

The LineageFlow composite uses 4 of the 6 (A) metrics, weighted to
emphasise the **classifier-aware per-position axis** (which is the
one the Wave 45 Agent G policy moves):

| Metric | Weight `w_i` | Why this weight |
|---|---:|---|
| `per_position_entropy_reduction` / `log K_lf` | **0.40** | The Wave 33 P2-W33-C metric (the only one with verified dynamic range below saturation); framework's classifier-aware restart moves this on every round |
| `avg_log_likelihood` (higher-is-better, tanh-normalised) | **0.30** | Per Wave 19 P1A2 reading: framework lifts -1.8478 → -1.8434 (+0.23%); tanh-normalising against baseline keeps the sign natural |
| `amino_acid_diversity` (higher-is-better, normalised `[1, K]`) | **0.15** | A small but real axis; framework pushes more positions toward non-argmax tokens |
| `classifier_confidence_change` (signed in `[-1, +1]`) | **0.15** | Direct read of the framework's per-position bias effect (Wave 45 Agent G) |

**LineageFlow composite:**

```
composite_lineageflow(cell)
  = 0.40 · (H(theta_baseline) - H(theta_framework)) / log(33)
  + 0.30 · tanh((loglik_framework - loglik_baseline) / |loglik_baseline|)
  + 0.15 · (div_framework - div_baseline) / (33 - 1)
  + 0.15 · (classifier_conf_framework - classifier_conf_baseline)
```

(All `Δ`-style terms relative to baseline at matched `(seed, NFE)`.)

### 4.6 Bounded [-1, 1] guarantee

* `per_position_entropy_reduction / log K` is in `[-1, 1]`.
* `tanh(·)` is in `[-1, 1]` by construction.
* `(novelty_framework - novelty_baseline) / 0.5` is in `[-2, +2]`,
  but with weight 0.20 contributes at most `±0.40`.
* `(div_framework - div_baseline) / 32` is in `[-1, +1]`.
* `classifier_confidence_change` is in `[-1, +1]` by construction.

The weighted sum is therefore bounded in `[-1, +1]`, and
`composite > 0` is a well-defined gate.

---

## 5. Backward-compatibility strategy

### 5.1 Toy tier keeps existing metrics

Per Wave 36 Agent F's `framework_improves_all_models = TRUE`
claim, the toy tier (Tier 1) uses its own per-model metrics:

| Model family | Existing metric (kept as-is) |
|---|---|
| `twodim_fm` (2D FM Eight Gaussians + Two Moons) | `W2` (lower-is-better) |
| `mnist_fm` (MNIST FM) | `FID` (lower-is-better, torchvision IMAGENET1K_V1) |
| `rectified_flow_cifar` (CIFAR-10 RF) | `FID` (lower-is-better) |

**The composite does NOT apply to the toy tier.** It is purely a
Tier-3 (Kanzi + LineageFlow) replacement for the saturated binary
decision metric. Toy-tier rows continue to feed `tools/capability_audit.py`
G.1-G.7 with the existing per-cell `signed_delta` values, and
`framework_improves_all_models` continues to be computed across the
toy + Tier-3 sets on its existing surface.

### 5.2 Composite only feeds the Tier-3 verdict

The composite is a **Tier-3-only gate** that augments — does not
replace — the existing G.* surface. Specifically:

* `tools/capability_audit.py:g1_mean_value_score` continues to
  consume the existing 10-row toy-tier signed-delta table.
* A new **T.1 (Tier-3 composite)** gate is added: `T.1 = mean of
  composite_kanzi(M) and composite_lineageflow(M)`. Target: `T.1 > 0`
  (HARD). The T.1 gate is **independent** of G.1-G.7 and does not
  perturb the existing toy-tier claim status.

This is the lightest possible scope: no existing test or audit
changes; new composite logic lives behind a new gate key.

---

## 6. Infrastructure changes needed (future wave)

### 6.1 New module: `tools/composite_benchmark.py`

A small aggregator module (not committed in this wave — design only):

```python
# Sketch (not committed; design only).
KANZI_COMPOSITE_WEIGHTS = {
    "per_position_entropy_reduction_logK": 0.40,
    "perplexity_against_pfam_tanh": 0.40,
    "novelty_normalised": 0.20,
}

LINEAGEFLOW_COMPOSITE_WEIGHTS = {
    "per_position_entropy_reduction_logK": 0.40,
    "avg_log_likelihood_tanh": 0.30,
    "amino_acid_diversity_normalised": 0.15,
    "classifier_confidence_change": 0.15,
}

def per_cell_composite(model: str, baseline: dict, framework: dict) -> float:
    """Return composite(model, cell) in [-1, 1]."""
    ...

def per_model_composite(model: str, cells: list[dict]) -> dict:
    """Return {median, n_cells, n_positive, n_zero, n_negative, verdict}."""
    ...
```

### 6.2 Extend `tools/run_real_ckpt_eval.py:DOWNSTREAM_METRICS`

Each Tier-3 model gains a new key:

```python
"composite_weights": {
    # Kanzi
    "per_position_entropy_reduction_logK": 0.40,
    "perplexity_against_pfam_tanh": 0.40,
    "novelty_normalised": 0.20,
},
"composite_normaliser_reference": "baseline_at_matched_seed_nfe",
```

The runner's `_run_cell` already threads both baseline and
framework metric values into the per-cell dict (Wave 43 / 44); the
new aggregator consumes those existing fields — no adapter-layer
change required.

### 6.3 Extend `tools/capability_audit.py` with T.1 gate

```python
# Sketch (design only — not committed here).
def t1_tier3_composite_gate(
    evidence_rows: list[dict],
) -> dict:
    """T.1: median composite per Tier-3 model, gate at > 0 (HARD)."""
    ...
```

`tools/capability_audit.py` is **NOT touched in this wave**; the
design specifies the surface so a future wave owns the
implementation.

### 6.4 Per-model metric mappings

The per-model composite uses 3 (Kanzi) + 4 (LineageFlow) of the
(A)-class metrics. To wire the composite, each Tier-3 model must
extend its `secondary_metrics` list in
`tools/run_real_ckpt_eval.py:DOWNSTREAM_METRICS` so the runner
computes and emits the additional metrics into the per-cell JSON:

* **Kanzi additions**:
  - `perplexity_against_pfam` — needs the Wave 43 Pfam sidecar
    (already shipped; metric layer needs to call it).
  - `novelty` — already registered as `secondary_metrics[1]`.
  - `per_position_entropy_reduction` — needs a kanzi-side wiring
    (currently only LineageFlow has it via
    `LineageFlowAdapter.observe_entropy_reduction`). Per the
    Wave 45 §15.13.6 honest reading, the Kanzi adapter would
    need a separate justification because its trajectory state
    is continuous-latent, not per-position categorical. **This
    is the largest remaining engineering gap.**

* **LineageFlow additions**:
  - `per_position_entropy_reduction` — already shipped
    (`observe_entropy_reduction` on the adapter; see
    `_adapter_common.per_position_entropy_reduction`).
  - `avg_log_likelihood` — exposed in the per-cell JSON via
    `LineageFlowAdapter.observe_entropy_reduction` augmentation
    (small extension; can emit `mean(theta_final.log().sum(-1))`
    alongside the entropy metric).
  - `amino_acid_diversity` — needs a small helper to count
    distinct argmax tokens over `theta_final`.
  - `classifier_confidence_change` — exposed via the
    `LineageFlowClassifierAwareRestart` policy's `_confidence_vector`.

### 6.5 Acceptance gate

For each Tier-3 model `M`:

```
T.1(M) = composite(M) > 0
T.1_overall = T.1(kanzi) AND T.1(lineageflow)
```

`T.1_overall` is a HARD gate. Pass = framework composite > 0 on
both Tier-3 models. This is the **acceptance gate for the
composite benchmark**: framework composite > 0 means the framework
strictly improves the integrated metric bundle on every Tier-3
model.

### 6.6 What the gate does NOT promise

The composite does not retroactively close the Tier-3 metric-axis
claim (`framework_wins > 0` on the **decision metric**). It is a
**parallel gate** that provides a non-saturated continuous-valued
view of the framework's value. The Tier-3 metric-axis claim can
still close only by (a) tightening the decision metric (e.g.,
recovering-protein-identity against Pfam holdout) or (b) lowering
NFE budgets into the pre-convergence regime (per §15.13.7 item 3).
Both are independent work items.

---

## 7. Worked example (illustrative)

Suppose the Wave 45 / 46 metric layer were extended to emit the
(A)-class metric bundle, and one cell produced:

**Kanzi cell** (seed=42, NFE=50, real ckpt):

| Metric | Baseline | Framework | Δ (framework − baseline) |
|---|---:|---:|---:|
| `per_position_entropy_reduction / log 64` | 0.00 | 0.18 | +0.18 |
| `perplexity_against_pfam` | 25.4 | 21.7 | -3.7 (lower-is-better) |
| `novelty` | 0.85 | 0.88 | +0.03 |

Normalised terms:

* `φ_1 = 0.18` (already in [-1, 1]).
* `φ_2 = tanh(-3.7 / 25.4) ≈ tanh(-0.146) ≈ -0.145`. Wait — the
  framework value is **lower** (better), so we want
  `φ_2 = tanh((b - f) / b) = tanh((25.4 - 21.7) / 25.4) ≈ +0.146`.
* `φ_3 = (0.88 - 0.85) / 0.5 = +0.06`.

```
composite_kanzi(cell) = 0.40·0.18 + 0.40·0.146 + 0.20·0.06
                      = 0.072 + 0.0584 + 0.012
                      = +0.1424
```

Bounded in [-1, 1] ✓. Positive ✓. **Composite says framework
strictly improves on this cell.**

Across 9 cells (3 seeds × 3 NFE budgets), the model-level
`composite_kanzi(M)` is the median. If the median is positive on
all 9 cells, `T.1(kanzi) = True`.

---

## 8. Files touched in this design wave

* `docs/audit/wave46-benchmark-design.md` — this document (NEW).

**No code change** to `adaptive_reflow/`, `tools/run_real_ckpt_eval.py`,
`tools/capability_audit.py`, `tests/`, framework, scheduler, or
other adapters per the READ-ONLY constraint.

---

## 9. Open questions / not yet designed

1. **Kanzi per-position entropy**: the Wave 45 Agent E helper
   `per_position_entropy_reduction` is a categorical-axis formula.
   Kanzi's trajectory state is **continuous latent**; reusing the
   categorical formula directly on Kanzi's `trajectory[-1]` would
   not be a residue-level quantity. A separate
   `kanzi_continuous_latent_sharpness` formula is needed. **Out
   of scope for this design doc** — it is a follow-up engineering
   item that would need its own Wave 46+ agent.
2. **Pfam holdout access**: the `perplexity_against_pfam` metric
   depends on the Wave 43 Pfam held-out sidecar being mounted in
   the sidecar venv. Per Wave 43 Agent B, the file is at
   `data/pfam_holdout/random_clan.fasta`. If the sidecar venv
   doesn't have access, the metric layer falls back to a synthetic
   reading (acceptable but not paper-comparable).
3. **Wall-clock cost**: the composite reads more metrics per cell,
   which adds 5-10 % wall-clock to `_compute_metric`. Out of scope
   here; a future wave measures the per-cell overhead.
4. **T.1 vs G.1 reconciliation**: if the toy tier shows G.1 PASS and
   T.1 PASS on Tier-3, what is the headline? The Wave 36 Agent F
   claim is `framework_improves_all_models` and that already
   survives T.1 because T.1 only adds a Tier-3-positive reading;
   the toy-tier cells continue to feed G.1 with their existing
   signed deltas.

---

## 10. Authoring chain

This design doc was authored 2026-09-07 by Wave 46 Agent C as the
"comprehensive benchmark" answer to the user's question. It is a
pure design doc — no code, no metric runs, no experiments.
Implementation lands in a future wave that owns
`tools/composite_benchmark.py` (NEW) and the
`tools/run_real_ckpt_eval.py:DOWNSTREAM_METRICS` extensions.
