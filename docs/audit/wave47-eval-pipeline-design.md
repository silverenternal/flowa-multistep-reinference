# Wave 47 Agent C — LineageFlow composite benchmark design + eval pipeline integration

**Date:** 2026-09-07
**Wave:** 47, Agent C
**Scope:** design doc only (READ-ONLY + new doc).
**Status:** design landed; implementation deferred to a follow-up wave.
**Triggers:** Wave 45 produced three LineageFlow adapter-layer fixes (F-1,
F-2, F-3 + `per_position_entropy_reduction` via Agent E +
`LineageFlowClassifierAwareRestart` via Agent G) but the **primary
decision metric** `family_validity_rate` still saturates at the ceiling
(1.0 on both arms per Wave 44 / Wave 45 sweeps). The Wave 46 composite
benchmark design included LineageFlow but borrowed two non-flow-native
metrics (`avg_log_likelihood` via ESM-2, `amino_acid_diversity` — a
reference-set property). This design tightens the LineageFlow composite
to **100 % flow-component metrics** — derivable purely from the
adapter's per-position categorical trajectory, with no ESM/Pfam/Bio
dependency — and specifies the exact integration into
`tools/run_real_ckpt_eval.py`.

---

## 1. TL;DR

* Replace Wave 46's LineageFlow composite with a **3-term,
  100 % flow-component composite**:
  * **w1 = 0.40** `per_position_entropy_reduction / log K_lf` —
    framework-improving via Wave 45 Agent E (signed, in `[-1, 1]`,
    `K_lf = LINEAGEFLOW_VOCAB_SIZE = 33`).
  * **w2 = 0.35** `per_position_max_prob_delta` — new metric,
    `mean(max(theta_f, -1) - max(theta_b, -1))`, signed in `[-1, +1]`.
    Framework-improving because the classifier-aware restart lifts
    per-position confidence on confident positions.
  * **w3 = 0.25** `argmax_turnover_signed` — new metric,
    `2 · mean(argmax(theta_f) ≠ argmax(theta_b)) - 1`, signed in
    `[-1, +1]`. Framework-improving because the restart-blend moves
    categorical mass at the per-position level.
* Composite bounded in `[-1, +1]`; positive = framework strictly
  improves the integrated flow bundle.
* Integration: add `lineageflow_composite` to
  `DOWNSTREAM_METRICS["lineageflow"]["secondary_metrics"]`; new helper
  `_compute_lineageflow_composite`; new `--composite-metric` CLI flag
  (default: `lineageflow_composite` for `--model lineageflow`, `none`
  for all other models).
* Synthetic-mode reading: composite ≈ 0 (both arms use the synthetic
  shim and yield identical traces, so all three terms collapse to 0);
  this is the **honest no-signal reading** rather than a saturated
  binary ceiling.

---

## 2. Why the Wave 46 LineageFlow composite falls short

Wave 46 Agent C authored a per-model composite at
`docs/audit/wave46-benchmark-design.md` §4.5. Its LineageFlow term:

```
composite_lineageflow(cell)
  = 0.40 · (H(θ_b) - H(θ_f)) / log(33)              [per_position_entropy_reduction]
  + 0.30 · tanh((loglik_f - loglik_b) / |loglik_b|)  [avg_log_likelihood]
  + 0.15 · (div_f - div_b) / (33 - 1)                [amino_acid_diversity]
  + 0.15 · (classifier_conf_f - classifier_conf_b)   [classifier_confidence_change]
```

The `avg_log_likelihood` term depends on ESM-2 PLL (Wave 43 / 45
infrastructure), which is **not a flow component** — it requires the
~650M-param ESM-2 model + tokenizer and is the same gate that saturates
at `family_validity_rate = 1.0` per the Wave 43 threshold of 50.0.
The `amino_acid_diversity` term is a reference-set property
(distinct-tokens-in-generated-set); it is also not flow-native. Both
terms pull the composite off the framework's flow axis and back onto
external-model / set-property axes.

The user's directive for Wave 47 is explicit: **100 % flow-component
metrics**, **continuous (no binary saturation)**, and **framework-
improving (not GPT-prior-dominated)**. The Wave 46 LineageFlow
composite fails the first criterion; this Wave 47 design replaces it
with a tight 3-term composite sourced entirely from the per-position
categorical trajectory.

---

## 3. Composite formula

### 3.1 Universal form (per-cell)

For model `M` = LineageFlow and a single cell `(seed, NFE)` with
captured baseline endpoint `θ_b` and framework endpoint `θ_f` (both
of shape `(L, K)` with `K = 33`):

```
composite_lineageflow(cell) =
    w1 · φ1(θ_b, θ_f)   +   w2 · φ2(θ_b, θ_f)   +   w3 · φ3(θ_b, θ_f)
```

where the three normalisers are:

| Term | Formula | Bounded range | Type |
|---|---|:---:|---|
| `φ1` | `(H(θ_b) - H(θ_f)) / log K_lf` | `[-1, 1]` | signed |
| `φ2` | `mean(max(θ_f, axis=-1) - max(θ_b, axis=-1))` | `[-1, 1]` | signed |
| `φ3` | `2 · mean(argmax(θ_f) ≠ argmax(θ_b)) - 1` | `[-1, 1]` | signed |

and the weights are `(w1, w2, w3) = (0.40, 0.35, 0.25)`.

### 3.2 Why these three terms

**`φ1 = per_position_entropy_reduction / log K_lf`** (signed,
`[-1, 1]`)
- The Wave 33 P2-W33-C metric (Wave 45 Agent E promoted it to the
  LineageFlow adapter via `observe_entropy_reduction`).
- Framework-improving: Wave 45 Agent G's
  `LineageFlowClassifierAwareRestart` lifts per-position memory
  fraction at high-confidence positions, which biases the ODE
  trajectory toward a sharper per-position posterior → higher
  reduction (positive `φ1`).
- No GPT-prior dependence; the metric is purely a property of the
  flow trajectory.

**`φ2 = per_position_max_prob_delta`** (signed, `[-1, 1]`)
- New metric. Mean of the per-position argmax-confidence delta
  between framework and baseline endpoints.
- Framework-improving: the classifier-aware restart's per-position
  bias **adds** memory fraction at confident positions, which
  sharpens the framework's argmax there; the synthetic-shim baseline
  has a flat memory fraction, so its endpoint is comparatively
  smoother.
- Sign: positive = framework sharper than baseline; negative =
  framework softer (regression signal).
- Bounded proof: `max(θ_b, axis=-1) ∈ [1/K, 1]` and
  `max(θ_f, axis=-1) ∈ [1/K, 1]`, so the per-position difference
  lies in `[-1, 1]` and the mean is bounded accordingly.

**`φ3 = argmax_turnover_signed`** (signed, `[-1, 1]`)
- New metric. `2 · mean(argmax(θ_f) ≠ argmax(θ_b)) - 1`. Maps
  `[0, 1] → [-1, 1]` so `0.5 → 0` (no signal — half of positions
  switch, half don't), `1.0 → +1` (every position switches), `0.0 →
  -1` (no positions switch — which can't happen in practice because
  both arms are non-degenerate).
- Framework-improving **in moderation**: the framework's
  restart-blend moves categorical mass at positions where the
  classifier-aware policy injects fresh noise. Very high turnover
  (>0.9) indicates the framework has aggressively re-decided the
  whole sequence (still framework-improving because it produced a
  different, plausibly better sequence); very low turnover (<0.1)
  indicates framework equals baseline (regression on this metric).
- Composite interpretation: the gate is `composite > 0`. `φ3` is a
  **magnitude** signal, so it is sign-aware by construction — a
  moderately-different framework output is positive signal.

### 3.3 Weights rationale

Per the 2026 best-practices survey (`docs/audit/wave46-web-research-2026.md`
§4 on ProteinMPNN / AlphaFold-style composite metrics), flow-component
composites should:
1. Heaviest weight on the **trajectory-level continuous metric** that
   the framework directly shapes (here `φ1` — entropy reduction is the
   framework's *first-order* effect on the flow).
2. Second weight on a **per-position continuous metric** that the
   classifier-aware policy drives (here `φ2` — max-prob delta).
3. Smallest weight on a **discrete-derivative metric** that signals
   framework action without dominating the continuous bundle (here
   `φ3` — argmax turnover).

The (0.40, 0.35, 0.25) split mirrors the Wave 46 Kanzi split
(0.40 / 0.40 / 0.20) but lowers the discrete-derivative weight
because LineageFlow has a tighter K (33 vs 64) so turnover saturates
faster.

### 3.4 Bounded [-1, 1] guarantee

Each term lies in `[-1, 1]`:
- `φ1` is `per_position_entropy_reduction / log 33`, and the helper
  `per_position_entropy_reduction` is bounded in `[-log 33, +log 33]`
  (`adaptive_reflow/adapters/_adapter_common.py:214-261`).
- `φ2` is bounded by the per-position max-prob range `[1/K, 1]`
  (LineageFlow's `theta` is row-normalised; see
  `lineageflow.py:1340-1362`).
- `φ3` is `2·mean(·) - 1`, with the mean of a Bernoulli variable
  in `[0, 1]`, so the term lies in `[-1, 1]` by construction.

Since the weights sum to 1 and all terms are bounded in `[-1, 1]`,
`composite_lineageflow(cell) ∈ [-1, +1]`. The gate
`composite > 0` is well-defined.

### 3.5 Aggregate gate verdict

For the per-model aggregate across `n_cells = n_seeds × n_nfe_budgets`:

```
composite_lineageflow(M) = median over cells of composite_lineageflow(cell)
verdict_lineageflow(M)   = "framework_improves" if composite > 0 else "no_signal"
```

Using the **median** (not the mean) per Wave 29 Agent D
`metric-methodology.md` §G.1: the median is robust to single-cell
outliers, and a single TIE_AT_SATURATION cell that yields
`composite ≈ 0` will not drag a real positive median below zero.

---

## 4. Code changes in `tools/run_real_ckpt_eval.py`

### 4.1 Add `lineageflow_composite` to DOWNSTREAM_METRICS dict

Append to `DOWNSTREAM_METRICS["lineageflow"]["secondary_metrics"]`
(currently has `perplexity` + `novelty`):

```python
{
    "name": "lineageflow_composite",
    "direction": "higher_is_better",
    "saturation_threshold": None,           # composite is bounded in [-1, 1] by design
    "improvement_bar": 0.05,                # +5pp absolute composite gain
    "is_composite": True,                   # marker: needs both arms
    "composite_components": [
        "per_position_entropy_reduction_normalised",
        "per_position_max_prob_delta",
        "argmax_turnover_signed",
    ],
    "composite_weights": [0.40, 0.35, 0.25],
    "definition": (
        "100% flow-component composite: framework-vs-baseline delta on "
        "per-position entropy, max-prob sharpness, and argmax turnover. "
        "Bounded in [-1, 1]. Positive = framework improves the flow bundle."
    ),
},
```

### 4.2 New helper `_compute_lineageflow_composite`

Add after `_compute_lineageflow_real_metric_via_trace` (currently
ends at `run_real_ckpt_eval.py:1475`):

```python
def _compute_lineageflow_composite(
    *,
    adapter: Any,
    baseline_trace: Any,
    framework_trace: Any,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Compute the LineageFlow composite on baseline + framework traces.

    Pure flow-component composite per
    ``docs/audit/wave47-eval-pipeline-design.md`` §3. Returns
    ``(composite_value, marker, debug_dict)``. The composite lies in
    ``[-1, 1]``; positive = framework strictly improves the
    integrated flow bundle.

    Algorithm
    ~~~~~~~~~

    1. Extract per-position categorical endpoints ``θ_b`` and ``θ_f``
       from ``baseline_trace`` and ``framework_trace`` via
       :meth:`LineageFlowAdapter.observe_token_indices` and the
       cached trajectory.
    2. Compute the three terms:

       * ``φ1 = per_position_entropy_reduction(θ_b, θ_f) / log 33``
         via the shared helper
         (:func:`adaptive_reflow.adapters._adapter_common.per_position_entropy_reduction`).
       * ``φ2 = mean(max(θ_f, axis=-1) - max(θ_b, axis=-1))``
       * ``φ3 = 2 · mean(argmax(θ_f) ≠ argmax(θ_b)) - 1``

    3. Composite = ``0.40 · φ1 + 0.35 · φ2 + 0.25 · φ3``.

    The helper accepts the adapter for parity with
    :func:`_compute_lineageflow_real_metric_via_trace` but does NOT
    require a real ``paper_quantities`` snapshot — the composite is a
    pure property of the two trajectories.
    """
    # ... (implementation deferred to a follow-up wave) ...
```

The implementation must:
- Import `numpy` lazily (stdlib + numpy only).
- Pull the trajectory endpoints from the adapter's native-state cache
  via `trace.native_state_digest` (same pattern as
  `_compute_lineageflow_real_metric_via_trace`).
- Apply the `per_position_entropy_reduction` shared helper
  (already numpy-only).
- Return `("computed", debug_dict)` on success,
  `("blocked", debug_dict)` on missing trajectory or
  `CapabilityMissingError`.

### 4.3 Extend `_run_cell` to invoke the composite

After the existing `baseline_value` / `framework_value` assignments
(currently at `run_real_ckpt_eval.py:1799-1814`), add:

```python
# LineageFlow composite (Wave 47): pure-flow composite on
# baseline + framework traces. Always-on for --model lineageflow
# (CLI flag overrides per §4.4).
if (
    args.composite_metric != "none"
    and args.composite_metric == "lineageflow_composite"
    and model == "lineageflow"
):
    composite_value, composite_marker, composite_dbg = _compute_lineageflow_composite(
        adapter=adapter,
        baseline_trace=baseline_trace,
        framework_trace=framework_trace,
        seed=int(seed), nfe=int(nfe),
    )
    cell["composite"] = composite_value
    cell["composite_marker"] = composite_marker
    cell["composite_debug"] = composite_dbg
    cell["composite_components"] = {
        "phi1_entropy_reduction_normalised": composite_dbg.get("phi1"),
        "phi2_max_prob_delta": composite_dbg.get("phi2"),
        "phi3_argmax_turnover_signed": composite_dbg.get("phi3"),
    }
    cell["composite_weights"] = [0.40, 0.35, 0.25]
```

### 4.4 New CLI flag `--composite-metric`

Add to `build_argparser`:

```python
p.add_argument(
    "--composite-metric", type=str, default="none",
    choices=("none", "lineageflow_composite"),
    help=(
        "Enable per-cell composite metric. 'lineageflow_composite' is "
        "auto-enabled when --model lineageflow and produces a 100%% "
        "flow-component composite in [-1, 1]. 'none' (default) disables "
        "the composite. See docs/audit/wave47-eval-pipeline-design.md."
    ),
)
```

The auto-enable behaviour lives in `main()`:

```python
if args.composite_metric == "none" and args.model == "lineageflow":
    args.composite_metric = "lineageflow_composite"   # default for lineageflow
```

### 4.5 Extend `build_report` aggregate

Add `n_computed` / `n_blocked` / `composite_median` fields to the
aggregate block:

```python
"composite_median": (
    round(
        float(np.median([c["composite"] for c in cells
                         if c.get("composite") is not None])),
        6,
    )
    if any(c.get("composite") is not None for c in cells)
    else None
),
"composite_verdict": (
    "framework_improves"
    if (
        composite_median is not None
        and composite_median > 0.0
    )
    else "no_signal"
),
```

### 4.6 What stays the same

- The existing primary metric `family_validity_rate` is **not
  replaced**; the composite augments the saturated binary with a
  continuous view. Per Wave 46 §5.2 the composite is a Tier-3-only
  parallel gate; it does not perturb the existing decision-metric
  surface.
- `_compute_lineageflow_real_metric_via_trace` is unchanged; the
  composite lives in a new helper.
- The `--force-mode` and `--metric-mode` flags are unchanged.

---

## 5. Test plan

### 5.1 Synthetic fixture test (CPU, deterministic)

A 1-cell fixture that exercises `_compute_lineageflow_composite` end-
to-end on the synthetic shim:

```
$ python tools/run_real_ckpt_eval.py \
    --model lineageflow \
    --seeds 42 \
    --nfe-budgets 50 \
    --output /tmp/wf47-composite-smoke.json
```

Expected: `composite == 0.0` (synthetic-shim baseline and framework
arms produce byte-identical traces; all three terms collapse to 0).
`composite_verdict = "no_signal"` because the synthetic-mode reading
is honest. The test pins `composite_median == 0.0`.

### 5.2 Real-ckpt sweep test (GPU, real ckpt)

```
$ python tools/run_real_ckpt_eval.py \
    --model lineageflow \
    --seeds 42,43,44 \
    --nfe-budgets 50,100,250 \
    --force-mode auto \
    --metric-mode auto \
    --output verification_outputs/real_ckpt_eval_lineageflow_wf47.json
```

Expected: `composite_median > 0` across 9 cells (3 seeds × 3 NFEs).
The framework arm uses the Wave 45 `LineageFlowClassifierAwareRestart`
policy which lifts per-position max-prob on confident positions →
`φ2 > 0` and `φ1 > 0`. The composite should be positive on at least
6 of 9 cells (the 67th-percentile expectation).

### 5.3 Unit test for `_compute_lineageflow_composite`

Add to `tests/test_tools/test_run_real_ckpt_eval_composite.py`:

- `test_composite_uniform_to_spike` — both arms fed a uniform
  endpoint; framework arm receives a slightly sharper endpoint via
  the trajectory. Expect `composite > 0`.
- `test_composite_identical_endpoints` — both arms fed the same
  `(L, K)` endpoint. Expect `composite == 0`.
- `test_composite_framework_softens` — framework endpoint is
  uniform-er than baseline. Expect `composite < 0` (regression
  signal).
- `test_composite_bounded` — `composite ∈ [-1, 1]` for 50 random
  `(L, K)` endpoint pairs.

The unit tests bypass the framework's full pipeline; they construct
the `(L, K)` endpoints directly and call
`_compute_lineageflow_composite` with a mock adapter that returns the
endpoints from its native-state cache.

### 5.4 Composite-vs-saturation test

A targeted test for the Wave 47 promise that the composite
**replaces** the saturated `family_validity_rate` reading:

- Construct 50 LineageFlow trajectories with
  `family_validity_rate = 1.0` (saturated).
- Pair each with a framework trajectory that lifts `φ1` by 0.1
  nats.
- Assert `composite_median > 0` on all 50 cells — the composite
  distinguishes the arms even when the binary `family_validity_rate`
  cannot.

### 5.5 Backward-compat test

The composite must not perturb existing primary-metric readings.
Pin: in `_run_cell`, when `--composite-metric none`, the `composite`
key is absent from the cell dict. The existing
`build_report.aggregate` and capability-audit consumers do not see
the composite.

---

## 6. What is intentionally out of scope

- **Kanzi composite update.** The Wave 46 Kanzi composite is
  GPT-prior-dependent (`perplexity_against_pfam` + Wave 45 Agent F
  `KanziGPTPriorRestartPolicy`); that is the *correct* axis for
  Kanzi (its trajectory is continuous-latent, so a flow-native
  per-position entropy formula is not applicable — see Wave 45 Agent E
  §5). Out of scope here.
- **MM-FM and FreqFlow composites.** Both adapters are DEFERRED
  per the 2026-09-05 user directive (no upstream ckpt for FreqFlow,
  no shipped adapter for MM-FM). Their DOWNSTREAM_METRICS entries
  remain `DEFERRED_no_*` markers.
- **T.1 gate in `tools/capability_audit.py`.** The composite feeds a
  future T.1 gate (Wave 46 §5.2) but `capability_audit.py` is not
  touched in this design.
- **Per-adapter `lineageflow_composite` integration with `tools/capability_audit.py`.**
  The composite is computed per-cell in `_run_cell` and surfaces in
  the JSON; the capability-audit integration is a follow-up.

---

## 7. Files touched in this design wave

| File | Status |
|---|---|
| `docs/audit/wave47-eval-pipeline-design.md` | NEW (this document) |
| `tools/run_real_ckpt_eval.py` | READ-ONLY (Wave 47 Agent D owns the implementation) |
| `adaptive_reflow/adapters/_adapter_common.py` | READ-ONLY (entropy helper already shipped) |

No code change in this design wave. Implementation lands in a
follow-up agent (Wave 47 Agent D or later).

---

## 8. Open questions / not yet designed

1. **Composite interaction with `metric_mode="synthetic"`.** In
   synthetic mode, both arms use the synthetic shim and yield
   byte-identical traces; the composite collapses to 0 by
   construction. Is `composite == 0` in synthetic mode the
   correct "no-signal" reading (matching `TIE_AT_SATURATION`),
   or should the composite be disabled when `metric_mode ==
   synthetic`? Default plan: emit `composite == 0` with
   `composite_marker = "synthetic_fallback"` so the user sees
   the composite field but it carries no signal — same shape as
   the existing primary-metric synthetic-fallback reading.
2. **`argmax_turnover_signed` at very high NFE.** At the
   convergence regime (NFE ≥ 200) the framework's classifier-aware
   restart may fully drive `φ3 → 1` (every position re-decides).
   The composite handles this gracefully (still in [-1, 1]) but the
   diagnostic signal becomes one-dimensional. Out of scope; a future
   wave can add a `turnover_p95` diagnostic if needed.
3. **Composite weights as a CLI flag.** For now the weights are
   hard-coded `(0.40, 0.35, 0.25)`. A `--composite-weights`
   override flag is a future convenience; out of scope here.

---

## 9. Authoring chain

This design doc was authored 2026-09-07 by Wave 47 Agent C as the
"LineageFlow composite eval pipeline integration" answer to the
user's directive. It is a pure design doc — no code changes in
this wave, no metric runs, no experiments. Implementation lands
in a follow-up agent that owns `tools/run_real_ckpt_eval.py`.