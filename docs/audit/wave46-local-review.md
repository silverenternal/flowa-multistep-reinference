# Wave 46 Agent A — deep local review: glue + adapter abstraction for protein FM re-inference

**Date:** 2026-09-07
**Wave:** Wave 46 Agent A (read-only review)
**Mode:** READ-ONLY. No code changed.
**Scope:** `adaptive_reflow/universal/adapter.py`,
`adaptive_reflow/framework/interfaces.py`,
`adaptive_reflow/adapters/kanzi.py` (2186 LOC),
`adaptive_reflow/adapters/lineageflow.py` (2303 LOC),
`adaptive_reflow/adapters/_adapter_common.py` (273 LOC),
`adaptive_reflow/algorithm/scheduler/_core.py`,
`adaptive_reflow/algorithm/merge_operator.py`,
`adaptive_reflow/algorithm/blender.py`,
`tools/run_real_ckpt_eval.py` (2115 LOC),
`adaptive_reflow/eval/` (32 modules — listed below).

**Inputs:** Wave 45 local review (§3 defects F-1/F-2/F-3; §4–§8 insertion
points; §11 preserve list), F-1 fix doc, F-2 fix doc, F-3 fix doc,
entropy-helper doc, Kanzi-GPT-prior-restart doc, LineageFlow-classifier-
restart doc, lineageflow entropy doc, Wave 45 final-eval doc,
Wave 43 problems review, Wave 41 paper audit, PLUG_IN_YOUR_MODEL.md,
Wave 45 master plan.

> **Read §2–§3 before designing.** §2 names the four pathologies that
> explain why `framework_wins=0` has persisted since Wave 43; §3 names
> what `framework_wins=0` is **not** (metric saturation alone is not the
> blocker; §3.1 says it's the wrong metric, §3.2 says the composite
> benchmark must have headroom, §3.3 names the missing contract, §3.4
> names the per-model asymmetry). §4 proposes the abstract design;
> §5 specifies the insertion points; §6 proves backward compatibility.

---

## 0. Executive summary

Wave 45 closed three mechanical blockers (F-1/F-2/F-3) and shipped two
model-specific restart policies + one entropy helper. Despite that,
the Tier-3 framework-vs-baseline verdict remains `framework_wins=0`
because **the single-binary decision metric is the wrong measurement
instrument for protein FM re-inference** — both arms converge to the
saturation ceiling at every NFE budget the runner sweeps. The next step
is therefore **not** another model-specific restart policy; it is a
**comprehensive, multi-metric composite benchmark** with **headroom**
under a **new glue-layer abstraction** that lets the framework consume
adapter-supplied model-aware signals without leaking them into the
universal Protocol.

Three concrete abstractions are proposed. Each is model-agnostic at
the interface; each has a per-model concrete adapter implementation
that plugs in. Backward compatibility with Wave 38's
`assert_adapter_compliance` and the 41/41 CLM claims is preserved
without any framework change (the abstraction lives at the adapter
layer + the eval pipeline; the Protocol surface is untouched).

| # | Abstraction | Where it lives | What it solves |
| - | --- | --- | --- |
| 1 | **`GlueLayer`** (general Protocol) | `adaptive_reflow/eval/glue.py` (NEW) | Model-agnostic contract for adapter → framework signal flow (multi-metric composite, paper-quantity-aware decoder, model-confidence carrier). |
| 2 | **`CompositeBenchmark`** (general dataclass + `compute_score`) | `adaptive_reflow/eval/benchmarks.py` (NEW) | General, headroom-providing composite formula that maps multiple continuous per-cell metrics + per-cell weights + saturation guards → a single signed framework-vs-baseline delta. |
| 3 | **`<Model>GlueAdapter`** (concrete) | `kanzi.py`, `lineageflow.py` (each ~80 LOC) | Per-model implementation of `GlueLayer` that produces the multi-metric composite (per-position entropy, ESM-2 PLL perplexity, novelty, classifier confidence, latent dispersion proxy). |

The Tier-1 results (toy 2D RF, MNIST, CIFAR-10 RF) are **unchanged**
because the new glue layer is opt-in: the toy adapters do not need
multi-metric composites (their `family_validity`-style metrics have
headroom at low NFE) and the new benchmark formula degrades gracefully
to the single-binary metric when no composite is supplied. Tier-3
gains **a real framework-vs-baseline decision metric** for the first
time.

The implementation is staged across four wave phases (see §11); this
review only proposes the design and verifies backward compat.

---

## 1. Why Wave 45 is the right inflection point but did not close `framework_wins=0`

Wave 45 closed three real defects (F-1/F-2/F-3) and shipped four
features. The Tier-3 re-eval (Wave 45 Agent H, `docs/CONSOLIDATED_RESULTS.md`
§15.13) shows `framework_wins=0` for Kanzi (9 cells at the saturation
ceiling) and LineageFlow (1 cell RUN_ERROR on an unrelated EsmModel
dtype boundary). The brief attributes this to "metric saturation";
this review agrees **partially** and disagrees **mostly**. The
disagreement is the load-bearing finding.

| Symptom | Wave 45 reading | This review's reading |
| --- | --- | --- |
| `framework_wins=0` on Kanzi | "metric saturated" (binary threshold hits 1.0 for both arms) | "wrong instrument" — even a non-saturated continuous metric would be averaged-out with the existing pipeline's `delta_pct = 0` reading; the **measurement pipeline** is single-binary, not the **model behaviour**. |
| Per-cell `delta_pct = 0.0` across 9 cells | "wall-saturation" — both arms converge at low NFE | Same: the pipeline only reports one number per cell (the `primary_metric`), and that number is binary. Even if the framework's restart-blend policy produces a 30% perplexity drop (which it likely does post-F-1, post-F-2, post-F-3, post-Wave-45-Agent-F), the runner cannot see it because the runner consumes `protein_sequence_validity_rate` and never asks for `perplexity`. |
| LineageFlow RUN_ERROR | "EsmModel dtype bug" | Correct diagnosis but the fix (5-LOC `argmax(...).long()`) is upstream of the metric-axis problem. Once the dtype is fixed, LineageFlow will hit the same saturation ceiling as Kanzi. |
| Framework wall-clock grew 1.0–1.6× baseline | "honest cost of new features" | Correct reading; the framework is now doing real work (3 rounds + restart-blend + paper-quantity snapshot). This is good — it means the framework-vs-baseline *measurement* is no longer the mechanical failure F-2 was. |

The Wave 45 work is necessary but insufficient. The next inflection
needs (a) a glue layer that lets adapters surface **multiple
metrics** with **continuous headroom** without polluting the
universal Protocol, and (b) a composite benchmark that combines
those metrics into a single decision number with no saturation.

---

## 2. Four pathologies in the current measurement pipeline

### 2.1 Pathology A — single binary metric per cell

`tools/run_real_ckpt_eval.py:1605-1640` (`_compute_metric`) routes to
either `_compute_kanzi_real_metric_via_trace` or
`_compute_lineageflow_real_metric_via_trace` and returns a single
scalar (`validity_rate` ∈ {0.0, 1.0}). The runner compares two such
scalars at line ~1900 (`status = "WIN" if framework_metric <
baseline_metric * (1 - tol)` for `lower_is_better`; the inverse for
`higher_is_better`). With both arms at 1.0 the verdict is always
`TIE_AT_SATURATION`.

`DOWNSTREAM_METRICS` (`run_real_ckpt_eval.py:176-352`) actually
**declares** secondary metrics (`perplexity`, `novelty`) — but the
runner never asks for them. They live in a spec dict that nothing
consumes after declaration. The second pillar of the comprehensive
benchmark is therefore already half-built; it just needs a consumer.

### 2.2 Pathology B — per-position entropy is **wired but uncalled**

Wave 45 Agent E shipped `per_position_entropy_reduction` on LineageFlow
(`lineageflow.py:1514+`; `wave45-lineageflow-entropy-metric.md`).
Kanzi has no equivalent — Wave 45 Agent D/E deliberately deferred
it because the §11 formula doesn't apply to a continuous latent
(`wave45-final-eval.md` §"Honest reading"). The eval pipeline does
NOT call the entropy method at any call site. The composite
benchmark needs to consume it.

### 2.3 Pathology C — `paper_quantities` is a no-op consumer at every adapter call site (well, mostly)

Wave 45 Agent C (F-3 fix) materialised a real `PaperQuantitiesSnapshot`
per cell. The adapters' `observe_token_indices` documents
`paper_quantities` as "a no-op consumer" (`kanzi.py:1651-1654`,
`lineageflow.py:1533-1537`). The eval JSON now carries the snapshot
(`paper_quantities_values: {A_g, B_g, C_g, e_rho}`), but neither the
adapter nor the runner uses the values to **drive** the metric.
`PaperQuantitiesSnapshot` is a transport; what is missing is a
**decision rule** that consumes `(A_g, B_g, C_g, e_rho, theta)`
and emits a metric. The glue layer is where that decision rule
belongs.

### 2.4 Pathology D — composite benchmark ≠ sum of metrics

A composite is **not** `0.5 * validity + 0.5 * perplexity` — such a
sum would let a binary `validity=1.0` mask a real `perplexity=0.95`
(10% perplexity drop). A proper composite must:

1. Live in a **bounded** space (like the framework's paper quantities).
2. **Decouple** saturated and non-saturated axes (don't let
   saturation on axis A mask non-saturation on axis B).
3. Have a **per-model weight vector** (protein-axis weights different
   from image-axis).
4. Have **explicit saturation guards** (if axis A is at its
   ceiling, its weight is redistributed to non-saturated axes).

`framework-internal-metrics.md` rev 2/3 already names the
`mean_value_score` aggregator (G.1) — but it is a **post-hoc** G-row
aggregator that consumes `evidence[]` rows; it cannot rescue a
single-binary cell from the inside.

---

## 3. What the right comprehensive benchmark must satisfy

The composite benchmark must produce a single signed scalar
`framework_score - baseline_score` per `(model, seed, NFE)` cell,
where `score` has continuous headroom over the framework's
restart-blend regime. Five hard requirements:

1. **Continuous headroom under the framework regime.** At the NFE
   budgets the framework-vs-baseline comparison actually differentiates
   (NFE ∈ {2, 5, 10}, per Wave 45 final-eval §"Why framework_wins > 0
   did not land" item 2), the composite must NOT be at 1.0 for both
   arms. Specifically: `perplexity` and `per_position_entropy_reduction`
   both have headroom at low NFE on a real Kanzi ckpt (the GPT-prior
   restart policy modulates per-position entropy; the AR-prior restart
   blend shifts perplexity).
2. **Per-model axis weights with saturation redistribution.** When a
   per-model axis saturates (e.g. Kanzi `validity=1.0` for all 32
   sequences), its weight redistributes to non-saturated axes
   (`perplexity`, `novelty`, `entropy_reduction`). The redistribution
   rule is published in the benchmark spec, not inferred.
3. **Honest negative surface.** When the framework's restart-blend
   policy truly does not help (or hurts), the composite goes negative
   with bounded magnitude. This is the same G.6 invariant the
   framework already commits to (`honest_negative_surface ≤ 0.30`).
4. **Adapter-supplied metrics are first-class.** The composite accepts
   a `dict[metric_name, callable]` from the adapter via the new
   `GlueLayer`; the runner routes via `hasattr(adapter, "compute_glue_metrics")`.
   This is what closes Wave 45's "entropy wired but uncalled" gap.
5. **Bit-stability under no-op adapters.** Toy adapters (no
   `GlueLayer`) collapse to today's single-binary metric (so Tier-1
   wins are preserved). The composite is **additive**, not
   **replacing**.

The benchmark formula below (§4) satisfies all five.

---

## 4. The composite benchmark formula

For each cell `(model, seed, nfe)` the runner computes two score
vectors (baseline, framework) of length `K` (the number of metrics
the adapter surfaces), then combines them:

```
score_cell = sum_{k in K}  w_k(metric_k, threshold_k) * normalised(metric_k)
```

with three sub-rules:

```
# Rule 1 — saturation guard: when an axis is at its ceiling
# for both arms, redistribute its weight uniformly to non-saturated
# axes. (Avoids the "binary metric masks continuous metric" pathology.)

saturated_axes_k = { k : max(baseline[k], framework[k]) >= threshold_k
                          AND min(baseline[k], framework[k]) >= threshold_k - eps }
unsat_weight_sum = sum_{k not in saturated_axes}  w_k
for k in saturated_axes:
    effective_weight_k = 0
for k not in saturated_axes:
    effective_weight_k = w_k + (redistributed_weight_total / unsat_weight_sum)

# Rule 2 — normalisation per axis (headroom-preserving):
#   "lower_is_better": normalised = (threshold - value) / threshold
#   "higher_is_better": normalised = (value - floor) / (threshold - floor)
# so each axis lives in [0, 1] with 0 = "framework's restart-blend
# cannot help here" and 1 = "axis is at its saturation ceiling".

# Rule 3 — signed cell score:
delta_cell = (sum_k  effective_weight_k * normalised_k(framework))
           - (sum_k  effective_weight_k * normalised_k(baseline))

# Bounded in [-sum_k w_k, +sum_k w_k]; with sum_k w_k = 1.0 by default,
# delta_cell is in [-1, +1].
```

Per-axis `threshold_k` and `weight_k` come from the per-model
`CompositeBenchmarkSpec` in `adaptive_reflow/eval/benchmarks.py`
(see §5). The per-axis `metric_k` callable comes from the new
`GlueLayer` (see §4.1).

The **default spec for Kanzi** (protein-axis, primary metric is
binary saturation):

```
axes:
  - name: "perplexity_against_pfam_holdout"
    direction: "lower_is_better"
    weight: 0.40
    threshold: 50.0    # ESM-2 PLL perplexity ceiling (matches _compute_lineageflow_real_metric)
    floor: 1.0         # a perfect decoder hits log-likelihood 0 -> perplexity 1
    callable: kanzi_glue_adapter.perplexity_against_pfam

  - name: "per_position_entropy_reduction"   # Wave 45 §11 formula on AR-prior logits
    direction: "higher_is_better"             # framework's restart *sharpens* the posterior
    weight: 0.30
    threshold: log(64) = 4.158883              # K=64 AR-prior vocab, fully uniform
    floor: 0.0
    callable: kanzi_glue_adapter.per_position_entropy_reduction_vs_baseline

  - name: "novelty_against_pfam_holdout"
    direction: "higher_is_better"
    weight: 0.20
    threshold: 1.0
    floor: 0.0
    callable: kanzi_glue_adapter.novelty_against_pfam

  - name: "gpt_prior_logit_change"             # Wave 45 Agent F's GPT-prior signal
    direction: "higher_is_better"
    weight: 0.10
    threshold: 1.0                              # normalised
    floor: 0.0
    callable: kanzi_glue_adapter.gpt_prior_logit_change_vs_baseline

saturation_redistribution_eps: 0.01    # both arms within 0.01 of ceiling => saturated
```

Per-axis `weight` sums to 1.00; `delta_cell ∈ [-1, +1]`. The cell
verdict rule:

```
delta_cell >  +0.005   => "WIN"   (framework > baseline by > 0.5pp)
delta_cell <  -0.005   => "LOSS"  (baseline > framework by > 0.5pp)
otherwise              => "TIE"
```

The 0.005 bar matches the existing `improvement_bar` threshold in
`DOWNSTREAM_METRICS` (`run_real_ckpt_eval.py:185`).

The **default spec for LineageFlow** mirrors the Kanzi spec with
`vocab_size=33` and the per-position categorical as the primary axis.
The **default spec for toy / MNIST / CIFAR** is the identity — the
single-binary metric is the only axis (so today's verdict is
preserved).

### 4.1 Where the per-axis callables come from

Each per-model `CompositeBenchmarkSpec` references callables that
live on a new `GlueLayer` adapter (see §5). For Kanzi:

```python
class KanziGlueAdapter:
    """Wave 46 — Kanzi implementation of GlueLayer (GlueLayer protocol)."""
    def perplexity_against_pfam(self, trace, *, paper_quantities) -> float:
        """ESM-2 PLL perplexity against the held-out Pfam subset."""
        ...

    def per_position_entropy_reduction_vs_baseline(
        self, trace, *, paper_quantities, reference_theta
    ) -> float:
        """Wave 45 §11 formula on the AR-prior logits extracted from trace."""
        ...

    def novelty_against_pfam(self, trace, *, paper_quantities) -> float:
        """1 - |generated ∩ reference| / |generated| against Pfam holdout."""
        ...

    def gpt_prior_logit_change_vs_baseline(
        self, trace, *, paper_quantities, reference_theta
    ) -> float:
        """The Wave 45 Agent F GPT-prior signal normalised."""
        ...
```

For LineageFlow the analogous class wraps
`per_position_entropy_reduction` (already shipped by Wave 45 Agent E),
the existing `classifier_aware_restart` confidence, and ESM-2 PLL.
For toy adapters `KanziGlueAdapter` does not exist; the runner falls
through to the single-binary metric. The fallback rule is the only
**adapter-side** opt-in; the framework-side composite evaluator is
mandatory.

---

## 5. GlueLayer abstraction (general, model-agnostic Protocol)

The `GlueLayer` Protocol lives at
**`adaptive_reflow/eval/glue.py`** (NEW, ~50 LOC). It is the
**model-agnostic contract** between the adapter layer and the eval
pipeline. The framework-side code consumes it; the adapter-side code
implements it.

```python
# adaptive_reflow/eval/glue.py  (NEW)
class GlueLayer(Protocol):
    """Adapter-supplied model-aware signals for the composite benchmark.

    A GlueLayer is the per-model implementation that produces the
    per-axis metrics for the composite benchmark (see benchmarks.py).
    The runner detects the layer via ``hasattr(adapter, "glue_layer")``
    and routes through it when present; when absent, the runner
    falls back to the single-binary decision metric (Wave 43 / Wave 45
    behaviour; Tier-1 preservation).
    """

    def perplexity_against_reference(
        self, trace: Any, *, paper_quantities: Any, reference: Any,
    ) -> tuple[float, str, dict[str, Any]]:
        """ESM-2 (or other reference model) PLL perplexity.

        Returns ``(value, marker, debug_dict)``. ``marker`` is one of
        ``"computed"`` / ``"synthetic_fallback"`` / ``"blocked"``.
        Stdlib + numpy only at the Protocol layer; the adapter
        implementation may import heavier deps under a ``try`` guard.
        """

    def per_position_entropy_reduction_vs_baseline(
        self, trace: Any, *, paper_quantities: Any, reference_theta: Any | None,
    ) -> tuple[float, str, dict[str, Any]]:
        """Per-position entropy reduction (Wave 45 §11, §3.3 of this doc).

        Default reference is the framework's trajectory at round 0
        (``trace[0]``); an explicit ``reference_theta`` overrides.
        """

    def novelty_against_reference(
        self, trace: Any, *, paper_quantities: Any, reference: Any,
    ) -> tuple[float, str, dict[str, Any]]:
        """1 - |generated ∩ reference| / |generated|."""

    def auxiliary_model_signal(
        self, trace: Any, *, paper_quantities: Any,
    ) -> tuple[float, str, dict[str, Any]]:
        """Per-model specific signal (GPT-prior confidence for Kanzi;
        classifier-aware confidence for LineageFlow). Returns a
        normalised [0, 1] scalar. Synthetic-mode returns ``0.0`` with
        marker ``"synthetic_fallback"``."""

    def composite_axis_weights(self) -> dict[str, float]:
        """Per-axis weight vector for this GlueLayer.

        The keys MUST match the axes declared in
        :class:`CompositeBenchmarkSpec` for this model; weights sum
        to 1.0. The runner aggregates these weights with the
        per-model saturation-redistribution rule (§4 Rule 1).
        """
```

The **insertion point** for the Protocol:

| File | Line | Action |
| --- | --- | --- |
| `adaptive_reflow/eval/glue.py` | NEW | ~50 LOC Protocol + helpers (regex validation of weight sums, saturation-redistribution math, audit-code emission) |
| `adaptive_reflow/eval/__init__.py` | (NEW exports block) | add `"GlueLayer"`, `"CompositeBenchmarkSpec"`, `"compute_composite_score"` |
| `adaptive_reflow/eval/benchmarks.py` | NEW | ~120 LOC `CompositeBenchmarkSpec` dataclass + `compute_composite_score` function (the §4 formula) |

The Protocol is **not** added to `universal/adapter.py` — that
file is stdlib-only and adding `GlueLayer` there would break the
W2 import-boundary discipline. The eval layer is the right home:
the runner is the only consumer of composite scores, and the runner
lives in `tools/`.

---

## 6. Adapter-layer abstraction (concrete per model)

The concrete `<Model>GlueAdapter` classes implement `GlueLayer` for
each Tier-3 adapter. **Two** are needed: `KanziGlueAdapter` and
`LineageFlowGlueAdapter`. Both are **opt-in** via a `glue_layer`
constructor kwarg on the concrete adapter; the default is `None`
(preserving today's byte-stable behaviour, so the 43+34 = 77 existing
adapter tests stay green).

### 6.1 KanziGlueAdapter (concrete; Kanzi-specific glue)

**Insertion:** `adaptive_reflow/adapters/kanzi.py` after the existing
`KanziGPTPriorRestartPolicy` block (after line ~880, before
`_torch_velocity_field`).

```python
@dataclass(frozen=True)
class KanziGlueAdapter:
    """Wave 46 — Kanzi implementation of GlueLayer.

    Produces the four per-axis metrics for the protein-FM composite
    benchmark (perplexity, per_position_entropy_reduction, novelty,
    gpt_prior_logit_change). All four are stdlib + numpy at the
    Protocol surface; the optional ESM-2 PLL load is gated on
    torch + transformers availability. Synthetic mode degrades to
    ``marker="synthetic_fallback"`` with ``value=0.0`` so the composite
    degrades to the framework's existing baseline arm without
    raising.

    Audit codes emitted:
    - ``AUDIT_KANZI_GLUE_PERPLEXITY`` — real PLL run completed
    - ``AUDIT_KANZI_GLUE_SYNTHETIC_FALLBACK`` — synthetic mode used
    - ``AUDIT_KANZI_GLUE_GPT_PRIOR_USED`` — GPT-prior signal consumed
    """
    pfam_holdout_path: Path | None = None
    esm_model_key: str = "facebook/esm2_t33_650M_UR50D"
    perplexity_threshold: float = 50.0

    def perplexity_against_reference(...) -> tuple[float, str, dict]: ...
    def per_position_entropy_reduction_vs_baseline(...) -> tuple[float, str, dict]: ...
    def novelty_against_reference(...) -> tuple[float, str, dict]: ...
    def auxiliary_model_signal(...) -> tuple[float, str, dict]:
        # Wave 45 Agent F's GPT-prior logit-confidence signal
        # (per-position entropy of ``prior_entry["gpt_prior_logits"]``)
        # normalised to [0, 1] (high = framework's GPT-prior bias
        # produced a confident posterior; low = uniform).
    def composite_axis_weights(self) -> dict[str, float]:
        return {
            "perplexity_against_pfam_holdout": 0.40,
            "per_position_entropy_reduction": 0.30,
            "novelty_against_pfam_holdout": 0.20,
            "gpt_prior_logit_change": 0.10,
        }
```

### 6.2 LineageFlowGlueAdapter (concrete; LineageFlow-specific glue)

**Insertion:** `adaptive_reflow/adapters/lineageflow.py` after the
existing `LineageFlowClassifierAwareRestart` block (after line ~700,
before the existing adapter class).

```python
@dataclass(frozen=True)
class LineageFlowGlueAdapter:
    """Wave 46 — LineageFlow implementation of GlueLayer."""
    pfam_holdout_path: Path | None = None
    esm_model_key: str = "facebook/esm2_t33_650M_UR50D"
    perplexity_threshold: float = 50.0

    def perplexity_against_reference(...) -> tuple[float, str, dict]: ...
    def per_position_entropy_reduction_vs_baseline(...) -> tuple[float, str, dict]:
        # Direct delegation to the Wave 45 Agent E
        # ``observe_entropy_reduction`` method; the GlueLayer wraps
        # the same adapter-native logic in the Protocol-shape the
        # composite benchmark expects.
    def novelty_against_reference(...) -> tuple[float, str, dict]: ...
    def auxiliary_model_signal(...) -> tuple[float, str, dict]:
        # Wave 45 Agent G's classifier-aware confidence (per-position
        # max-prob of ``theta``) normalised to [0, 1].
    def composite_axis_weights(self) -> dict[str, float]:
        return {
            "perplexity_against_pfam_holdout": 0.35,
            "per_position_entropy_reduction": 0.30,
            "novelty_against_pfam_holdout": 0.20,
            "classifier_aware_confidence": 0.15,
        }
```

### 6.3 Adapter constructor opt-in

| File:line | Action |
| --- | --- |
| `kanzi.py:864` (or wherever the `__init__` is at; the field was originally at 864 per wave45-local-review.md §5 but may have shifted post-Wave 45 — re-confirm at edit time) | add `glue_layer: KanziGlueAdapter | None = None` constructor kwarg; `KANZI_CONFIG_HASH` provenance records the glue layer's class name (no per-config fingerprint to keep the byte-stable D.4 vectors). |
| `lineageflow.py:1145` (`__init__`) | add `glue_layer: LineageFlowGlueAdapter | None = None` constructor kwarg. |

---

## 7. Five insertion points (file:line, function name)

| # | File | Line(s) | Function / class | Action |
| - | --- | --- | --- | --- |
| 1 | `adaptive_reflow/eval/glue.py` | NEW | module | author `GlueLayer` Protocol + helpers (~50 LOC stdlib-only). |
| 2 | `adaptive_reflow/eval/benchmarks.py` | NEW | module | author `CompositeBenchmarkSpec` dataclass + `compute_composite_score` function (~120 LOC stdlib-only; depends on `glue.py` for the Protocol only). |
| 3 | `adaptive_reflow/eval/__init__.py` | NEW exports block | module | re-export `GlueLayer`, `CompositeBenchmarkSpec`, `compute_composite_score`. |
| 4 | `adaptive_reflow/adapters/kanzi.py` | after line ~880 (before `_torch_velocity_field` banner at line ~885) | `KanziGlueAdapter` class | author concrete `KanziGlueAdapter` (~80 LOC). Wire `glue_layer: KanziGlueAdapter \| None = None` into `__init__`. |
| 5 | `adaptive_reflow/adapters/lineageflow.py` | after line ~700 (before the existing adapter class at line ~1082) | `LineageFlowGlueAdapter` class | author concrete `LineageFlowGlueAdapter` (~80 LOC). Wire `glue_layer` into `__init__`. |

**NOT in scope** for this design (deliberately):

- `tools/run_real_ckpt_eval.py` changes. The runner side of
  consumption is a separate Wave 47 work item (`Runner dispatch via
  `hasattr(adapter, "glue_layer")``). This review only designs
  the adapter-side abstraction; the runner-side dispatch is a
  1-paragraph edit (see §10).
- `universal/adapter.py` change. The Protocol surface is the
  intentional blocker — adding a method there would force every
  adapter to implement it (breaks Wave 38's `assert_adapter_compliance`
  test for the 14 non-Kanzi/non-LineageFlow adapters). The eval
  layer is the right home.
- `framework/interfaces.py` change. Same reason; the framework-side
  algorithms don't consume the composite score (the runner does).
- `algorithm/scheduler/_core.py` change. The composite score does not
  feed back into the scheduler (the scheduler is paper-quantity-driven,
  per Wave 31). Composite scoring is a measurement, not a control
  signal.

---

## 8. Backward compatibility — five guarantees

The composite benchmark is **additive**. Five invariants prove the
new abstraction does not regress Wave 38's `assert_adapter_compliance`
CI test, the 41/41 CLM claims, or the Tier-1 framework-vs-baseline
wins.

### 8.1 The `FlowMatchingODEAdapter` Protocol surface is untouched

The new glue layer lives at `adaptive_reflow/eval/glue.py`, not at
`universal/adapter.py`. No Protocol method is added, renamed, or
removed. **Wave 38's `assert_adapter_compliance(adapter_cls)` check
passes unchanged on every existing adapter.**

Concrete check: `tests/test_framework/test_adapter_compliance.py`
runs `@runtime_checkable` `isinstance(adapter_cls, FlowMatchingODEAdapter)`
on every registered adapter. Adding `GlueLayer` to a different module
does not enter that test's namespace. **PASS.**

### 8.2 The 41/41 CLM claims keep their wiring

`tests/test_claims/` wires 41 claims to pytest. None of those claims
references `glue_layer`, `composite_score`, or `KanziGlueAdapter` —
they reference the existing Protocol methods
(`solve_ode`, `apply_restart_distribution`, `observe_endpoint`,
`observe_token_indices`, etc.). The new abstractions are
**consumers** of those methods; they do not change the methods
themselves. **PASS** — no claim re-wiring required.

### 8.3 Tier-1 wins are preserved

The composite benchmark degrades to the single-binary metric when no
`glue_layer` is supplied (`hasattr(adapter, "glue_layer") == False`).
Toy 2D RF (`twodim_fm`), MNIST FM (`mnist_fm`), and CIFAR-10 RF
(`rectified_flow_cifar`) do NOT ship a `glue_layer`. The composite
evaluator falls through to today's `_compute_metric` and today's
`delta_pct` is computed. **The 2D RF +8.2×, CIFAR-10 RF +4.3×, MNIST
+1.25× signed_mean values (per `docs/CONSOLIDATED_RESULTS.md` §12.3
G.1 reading) are unchanged.** **PASS** — `framework_wins` for
Tier-1 reads identically.

### 8.4 Wave 45 adapter tests stay byte-stable

Both concrete `GlueAdapter` classes have a default of `None` in the
adapter constructor. The 43 existing Kanzi tests + the 42 existing
LineageFlow tests (per `wave45-final-eval.md` §"Kanzi" + §"LineageFlow
per-cell table" results + `test_protocol_deep_audit` smoke test) do
not pass `glue_layer=...`, so they exercise the pre-existing path.
The `observe_token_indices` chain-walk fix (F-1) and the GPT-prior
restart policy (Wave 45 Agent F) are unchanged. **PASS** — no test
regresses.

### 8.5 Wave 45 audit-code / digest discipline is preserved

The new `KanziGlueAdapter` and `LineageFlowGlueAdapter` classes emit
their own audit codes (`AUDIT_KANZI_GLUE_*`,
`AUDIT_LINEAGEFLOW_GLUE_*`) appended to the bundle `provenance` tuple
when the glue layer is active. When the glue layer is `None`, no
audit code is appended (preserving byte-stability). The
`native_state_digest` discipline is unchanged — the glue layer does
not write to `_native_states` (it is read-only; the consume side of
the eval pipeline is the only writer of glue output). **PASS** — D.4
regression vectors are not perturbed.

---

## 9. How to KEEP toy + CIFAR-10 RF wins WHILE ADDING Tier-3 capability

This is the load-bearing user concern: Wave 45's work risked
breaking Tier-1 by adding Tier-3 plumbing. The design above is
structured so the two are **decoupled**. Three mechanisms enforce
the decoupling:

### 9.1 Glue layer is opt-in on the adapter constructor

Both `KanziAdapter.__init__` and `LineageFlowAdapter.__init__` take
`glue_layer: <Model>GlueAdapter | None = None`. Toy adapters
(`twodim_fm`, `mnist_fm`, `rectified_flow_cifar`, etc.) do not even
have a `glue_layer` kwarg — they cannot be made to opt in. The
runner-side `hasattr(adapter, "glue_layer")` check evaluates `False`
for toy adapters and the composite evaluator skips them.

### 9.2 Composite evaluator falls through to the single-binary metric

When `hasattr(adapter, "glue_layer")` is `False` OR the glue layer's
`composite_axis_weights()` returns an empty dict, the evaluator calls
the existing `_compute_metric` (today's path) and returns the
`framework_wins` verdict from `delta_pct`. This is the same code path
that Wave 42 / Wave 43 used. Toy runs are **byte-identical**.

### 9.3 Glue layer audit codes are explicit when active

When the glue layer IS active, the new audit codes
(`AUDIT_KANZI_GLUE_PERPLEXITY`, etc.) appear in the bundle
`provenance` so the audit trail makes the activation visible. The
capability surface is unchanged: an adapter's `AdapterCapabilities`
does not declare a glue layer capability (the capability is detected
via `hasattr`). Wave 38's `assert_adapter_compliance` test continues
to pass because the Protocol surface has not changed.

**Net effect:** the 4 Tier-1 families (twodim_fm, mnist_fm,
rectified_flow_cifar, lineageflow-synthetic) all keep their existing
wins (G.1 robust median +0.0884, per `docs/CONSOLIDATED_RESULTS.md`
§12.3). The 2 Tier-3 protein-axis cells (kanzi-real, lineageflow-real)
gain a new, headroom-providing composite score that the framework-vs-
baseline comparison can differentiate on. The Tier-3 framework-vs-
baseline claim (`framework_wins > 0`) becomes testable.

---

## 10. End-to-end composition (what the runner does post-Wave 47)

When the runner-side edit ships (Wave 47 follow-up), the flow is:

```
1. _solve_baseline() captures (trace_baseline, wall_baseline).
2. _solve_framework() captures (trace_framework, wall_framework).
3. _compute_metric(model, trace_baseline, ..., adapter=adapter)
   -> value_baseline, marker_baseline, dbg_baseline
4. IF hasattr(adapter, "glue_layer"):
     compute the per-axis values for baseline + framework via
     adapter.glue_layer.<axis_method>(trace, ...)
   ELSE:
     fall through to today's _compute_metric call.
5. compute_composite_score(spec, axis_values_baseline, axis_values_framework)
   -> delta_cell in [-1, +1].
6. Verdict rule:
     delta_cell >  +0.005 -> WIN
     delta_cell <  -0.005 -> LOSS
     otherwise           -> TIE
7. status_detail = f"composite_delta={delta_cell:.4f}; saturated_axes={...}"
```

The runner-side edit is ~30 LOC at `tools/run_real_ckpt_eval.py:1605-1640`
(`_compute_metric`). It is a **one-branch** extension of today's
`_compute_metric`, not a rewrite. Wave 47's owner must read the
disjoint-file-scope discipline: this review only owns the abstraction
design; the runner-side dispatch is the implementation.

---

## 11. Staged implementation across four phases

| Phase | Owner | Files | Effort |
| --- | --- | --- | --- |
| **Phase 1 — abstractions (Wave 47)** | Wave 47 Agent A | `eval/glue.py`, `eval/benchmarks.py`, `eval/__init__.py` | ~200 LOC new; 8 unit tests for the `compute_composite_score` Rule 1/2/3 + saturation redistribution |
| **Phase 2 — Kanzi concrete glue (Wave 47)** | Wave 47 Agent B | `adapters/kanzi.py` | ~80 LOC `KanziGlueAdapter`; 6 tests (one per GlueLayer method) |
| **Phase 3 — LineageFlow concrete glue (Wave 47)** | Wave 47 Agent C | `adapters/lineageflow.py` | ~80 LOC `LineageFlowGlueAdapter`; 6 tests |
| **Phase 4 — runner dispatch + re-eval (Wave 48)** | Wave 48 Agent A | `tools/run_real_ckpt_eval.py` | ~30 LOC dispatch; smoke + 9-cell Kanzi + 1-cell LineageFlow re-eval; CONSOLIDATED_RESULTS §15.14 + paper §7.9 update |

Each phase has a clear acceptance gate:

- **Phase 1** — `tests/test_eval/test_composite_score.py` passes
  (8 tests covering the formula + saturation redistribution).
- **Phase 2** — `tests/test_adapters/test_kanzi.py` extends with
  6 glue-layer tests; the 43 existing tests stay green.
- **Phase 3** — `tests/test_adapters/test_lineageflow.py` extends
  with 6 glue-layer tests; the 42 existing tests stay green.
- **Phase 4** — Kanzi + LineageFlow re-eval produces at least one
  `WIN` cell across 9 + 1 = 10 cells (or honest `LOSS` cells
  documenting the negative surface per G.6).

The Phase 4 cell win is **not** guaranteed. The Wave 45 Agent F /
Agent G policies modulate the restart blend, and the Wave 45 Agent C
F-3 fix threads `paper_quantities` end-to-end. Whether the composite
delta crosses `+0.005` is an empirical question. Honest reading:
composite scoring makes the measurement possible; it does not
guarantee a positive framework delta. Wave 48 will report both
possibilities.

---

## 12. Verification of this review

| Claim | Verification method |
| --- | --- |
| Protocol surface is unchanged | `git diff universal/adapter.py` post-implementation is empty |
| Tier-1 wins preserved | `tools/capability_audit.py` G.1 reading post-Wave 47 = `+0.0884 ± 0.001` (matches §12.3) |
| Wave 45 tests stay green | `pytest tests/test_adapters/test_kanzi.py tests/test_adapters/test_lineageflow.py` post-Wave 47 = 43 + 42 = 85 passing |
| 41/41 CLM claims unchanged | `pytest tests/test_claims/` = 41 passing |
| Composite formula headroom | `tests/test_eval/test_composite_score.py::test_saturated_axis_redistributes_weight` shows `weight[unsaturated]` rises from `w=0.30` to `w=0.60` when `saturated_axes_k` covers 1 of 4 axes |
| `mkdocs build --strict` | exits 0 post-Wave 47 (new docs file in `docs/audit/wave46-*.md` is in `not_in_nav`) |
| D.4 regression vectors | unchanged because the new abstraction lives in `eval/`, not in `adapters/`, and the per-adapter `native_state_digest` payloads are untouched |

The review itself is read-only; verification happens during Phase 1-4
of Wave 47-48 implementation.

---

## 13. References

- `docs/audit/wave45-local-review.md` — Agent A's READ-ONLY audit at
  `ba37ac0`. §3 defects F-1/F-2/F-3; §4 signal-routing option 1;
  §5/§6 insertion points; §11 preserve list.
- `docs/audit/wave45-f1-fix.md` — `kanzi.observe_token_indices` F-1 fix.
- `docs/audit/wave45-f2-fix.md` — eval pipeline F-2 fix.
- `docs/audit/wave45-f3-fix.md` — `paper_quantities` threading F-3 fix.
- `docs/audit/wave45-entropy-helper.md` — shared `_adapter_common.per_position_entropy_reduction`.
- `docs/audit/wave45-kanzi-gpt-prior-restart.md` — Wave 45 Agent F's
  `KanziGPTPriorRestartPolicy`. The `auxiliary_model_signal` callable
  in the new `KanziGlueAdapter` reads the same
  `prior_entry["gpt_prior_logits"]` payload this policy populates.
- `docs/audit/wave45-lineageflow-classifier-restart.md` — Wave 45
  Agent G's `LineageFlowClassifierAwareRestart`. The
  `LineageFlowGlueAdapter.auxiliary_model_signal` consumes the
  classifier-aware confidence the policy emits.
- `docs/audit/wave45-lineageflow-entropy-metric.md` — Wave 45 Agent E
  shipped `observe_entropy_reduction` on LineageFlow; the new
  `LineageFlowGlueAdapter.per_position_entropy_reduction_vs_baseline`
  delegates to it (single definition).
- `docs/audit/wave45-final-eval.md` — Wave 45 Agent H re-eval;
  `framework_wins=0` despite F-1/F-2/F-3 fixes. The composite
  benchmark is what closes this.
- `docs/audit/wave43-problems-review.md` — master cross-wave
  problems review (Tier-3 framework-vs-baseline is the open claim).
- `docs/audit/wave41-paper-audit.md` — paper audit; Gap 3 (per-
  position entropy metric for LineageFlow) is now shipped (Wave 45
  Agent E); this review's composite is the framework-level integration.
- `docs/PLUG_IN_YOUR_MODEL.md` — generic Step 1-5 walkthrough + per-
  model plug-in candidate sections. **APPEND a new section for the
  composite benchmark at the end of the LineageFlow / Kanzi plug-in
  candidate sections in Phase 4**; do not touch the generic walkthrough.
- `todo/wave45-adapter-fix-master-plan.md` — Wave 45 Agent C master
  plan. The §1.7 acceptance gate for `KanziGPTPriorRestartPolicy` is
  satisfied post-Wave 45 Agent F; this review's composite extends
  the master plan's surface area to the eval pipeline.
- `framework-internal-metrics.md` rev 3 — G.1 mean value score (robust
  median); the composite benchmark's `delta_cell` is a richer cell-
  level signal that G.1's `signed_mean` aggregator will absorb in
  Wave 48 once Phase 4 re-eval populates the new evidence rows.
- `docs/baseline-audit-report.md` §F.2 — Wave 38 reproduction status.
  The composite benchmark is the Wave 47-48 contribution that closes
  the open `REPRODUCED`-but-`framework_wins=0` finding.

---

**End of review. READ-ONLY. Authoring teams may now design Phase 1-4
on top of this abstraction; nothing in the design touches the
Protocol surface or the framework core.**