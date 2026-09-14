# Wave 47 Agent A — LineageFlow adapter deep review + dedicated glue layer design

**Date:** 2026-09-07
**Wave:** Wave 47 Agent A (READ-ONLY; Phase 1 of the dedicated glue layer)
**Scope:** deep review of `adaptive_reflow/adapters/lineageflow.py` (2303 LOC
post-Wave-45) + design proposal for the dedicated LineageFlow glue layer.
**Directive served:** user directive 2026-09-05 — LineageFlow is the only
PURE flow matching top-venue model with downloaded weights (ICML 2026,
protein, Pfam-RP55, 657 M params); the framework needs a dedicated
LineageFlow glue layer that exposes the right flow-component metrics
(`per_position_entropy_reduction`, `reconstruction_loss`,
`flow_loss_reduction`).

---

## 1. LineageFlow architecture summary

### 1.1 The paper

* **Title:** LineageFlow: Phylogeny-aware Flow Matching for Protein
  Evolution Modeling.
* **Authors:** Lin et al. 2026.
* **Venue:** ICML 2026.
* **arXiv:** `arXiv:2605.22252`.
* **Domain:** per-position amino-acid categorical over Pfam-RP55 family
  sequences; 33-token vocabulary (20 standard AA + BOS / EOS / PAD /
  gap / MSA-mask).

### 1.2 The adapter

`adaptive_reflow/adapters/lineageflow.py` (2303 LOC) wires the published
LineageFlow ESM-2-650M + flow head into the framework's
`FlowMatchingODEAdapter` Protocol.

| Component | Specification | Source |
| --- | --- | --- |
| Encoder | ESM-2-650M-style Transformer (`facebook/esm2_t33_650M_UR50D`), 33 layers, hidden=1280, intermediate=5120, rotary positional embeddings | Wave 36 Agent C breakthrough (downloaded `lineageflow-rp55.ckpt`, 9.788 GB) |
| Flow head | Sinusoidal time embedding → 2 dense layers → LayerNorm → 33-dim output projection | upstream `models/model.py:73-92` |
| Conditioning | Pfam family identifier via `sampler_cfg["seed_id"]`; the published ckpt stores the runtime knob-set under `hyper_parameters["sampler_cfg"]` | Wave 36 Agent C shim: `_install_checkpoint_compat` fabricates `core.sampler.SamplerConfig` so `torch.load` can resolve the pickled class |
| Family embed dim | 1280 (matches the flow head's hidden) | `LINEAGEFLOW_FAMILY_EMBED_DIM = 1280` |
| Native state shape | `(L=256, K=33)` per-position categorical, row-normalised | `LINEAGEFLOW_STATE_SHAPE = (256, 33)` |
| Objective | flow matching on `X_t = (1-t) X_0 + t X_1` with MSE between predicted and target velocity fields | upstream `core.vector_field` (we wrap the velocity field; the loss is not exposed through the adapter) |
| Total parameters | 657 M (matches the paper's "~657M") | Wave 10 setup verified via ckpt |

### 1.3 The 2-channel architecture

```text
AMINO_ACID_CATEGORICAL  (discrete, shape (L, K) = (256, 33))   — the ODE state
PFAM_FAMILY_COND        (continuous, opaque TensorRef)         — conditioning cache
```

* The amino-acid channel carries the per-position categorical theta
  through the protocol boundary.
* The Pfam-family channel is a continuous side-channel conditioning
  vector (1280-dim). Same name as Kanzi's
  `PFAM_FAMILY_COND` so the two protein-axis adapters share a
  conditioning surface.

### 1.4 Two operating modes

| Mode | Weights | Active here |
| --- | --- | --- |
| `synthetic` | random-init Kaiming-uniform 2-layer MLP (deterministic, 256 hidden) | tests + CI |
| `torch` | loaded ESM-2-650M + flow head from `lineageflow-rp55.ckpt` | Wave 41-43 real-ckpt eval (gated on `.venvs/lineageflow_venv/bin/python`) |

The synthetic field uses a per-position-affine velocity field with
family-conditioned bias:

```text
v_theta(x, t, family) = W2 @ tanh(W1 @ flatten(x) + b1
                                  + t * t_bias
                                  + alpha * family_proj)
                        + b2
```

The field is **not** a trained FM model — it is a Protocol-surface
shim that mirrors `SelfFlowAdapter`'s synthetic mode.

### 1.5 Protocol surface

`LineageFlowAdapter` advertises 10 methods (Wave 10 + Wave 44 + Wave 45):

| # | Method | Status | Notes |
| --- | --- | --- | --- |
| 1 | `capabilities()` | ✓ | returns `LineageFlowCapabilities` (frozen, both continuous + discrete channels) |
| 2 | `build_initial_state(*, batch_id, sample_id)` | ✓ | samples uniform-prior `(L, K)`, computes native_state_digest, populates StateBundle |
| 3 | `export_endpoint(state)` | ✓ | identity pass-through (kanzi:1108 / lineageflow:1894) |
| 4 | `detach_and_validate_endpoint(bundle)` | ✓ | fail-closed gate (`detach_proof is True`) |
| 5 | `apply_restart_distribution(state, policy)` | ✓ | per-position categorical blend `m * prior + (1-m) * fresh` + 2 row-renormalisations (clamp + defensive re-norm) |
| 6 | `compose_condition(bundle, delta)` | ✓ | resolves `family_id` + `num_steps` + `sampler_id` + `guidance_scale`, builds the conditioning cache key |
| 7 | `solve_ode(state, condition, *, seed)` | ✓ | Euler / Heun over `t ∈ [0, 1]` with row-renormalisation after every step; returns `ODEIntegratorTrace` whose `native_state_digest` indexes a `(N+1, L, K)` trajectory in the native-state cache |
| 8 | `observe_endpoint(trace, state)` | ✓ | decodes `argmax(theta_final, axis=-1)` via the endpoint digest; writes the post-state to native-state cache |
| 9 | `observe_token_indices(trace, paper_quantities)` | ✓ | Wave 44 Tier-3 metric-axis close; returns `{str(AMINO_ACID_CATEGORICAL): np.ndarray((L,))}` of argmax indices |
| 10 | `observe_entropy_reduction(trace, paper_quantities, *, reference_theta)` | ✓ | Wave 45 Agent E P2-W33-C metric promotion; delegates to `_adapter_common.per_position_entropy_reduction` after `_theta_to_logits` |
| 11 | `export_trajectory(trace)` | ✓ | returns `(N+1, L, K)` per-step trajectory or `None` |
| 12 | `inject_forward_noise(bundle, injected)` | ✓ | `(1 - mix) * prior + mix * injected`, row-renormalised |

### 1.6 The restart math (re-stated for §3)

`apply_restart_distribution` is at `lineageflow.py:1422-1576`. The
blend formula is:

```text
blended = (m_vec * prior_theta + (1 - m_vec) * fresh_theta)        # line 1491-1492
blended = blended / max(blended.sum(axis=-1, keepdims=True), 1e-30) # line 1500-1502
blended = clip(blended, 0, LINEAGEFLOW_CLAMP=1.0)                    # line 1507
blended = blended / max(blended.sum(axis=-1, keepdims=True), 1e-30) # line 1509-1511
```

When the Wave 45 Agent G `LineageFlowClassifierAwareRestart` policy
is active, the scalar `m` is replaced with a per-position vector
`m_vec` of shape `(L,)` derived from the upstream classifier's
confidence (fallback: max-prob proxy).

---

## 2. Comparison with Kanzi

| Aspect | LineageFlow | Kanzi |
| --- | --- | --- |
| **Venue / paper** | ICML 2026, Lin et al., `arXiv:2605.22252` | ICLR 2026, Shah et al., `arXiv:2510.00351` |
| **Domain** | per-position amino-acid categorical | continuous latent + AR-prior discrete tokens |
| **State shape** | `(L=256, K=33)` per-position categorical | `(L_z=64, d=64)` continuous latent + `(L_z=64,)` AR-prior categorical |
| **Channel** | `AMINO_ACID_CATEGORICAL` (discrete) + `PFAM_FAMILY_COND` (continuous) | `PROTEIN_LATENT` (continuous) + `DISCRETE_TOKEN_INDEX` (discrete) + `PFAM_FAMILY_COND` (continuous) |
| **Conditioning** | Pfam family id → 1280-dim embedding via upstream flow head | Pfam family id → 1152-dim embedding via upstream encoder |
| **Native state is already normalised** | YES — `solve_ode` row-renormalises after every integration step; tests pin `traj.sum(axis=-1) == 1` | NO — continuous latent in `[-KANZI_LATENT_CLAMP=6.0, +6.0]` |
| **GPT-prior restart** | NO — uses an ESM-2-650M `LineageFlowClassifier` (657M-param) for confidence | YES — 250M `kanzi.models.GPT` AR prior; `KanziGPTPriorRestartPolicy` (Wave 45 Agent F) reads per-position entropy from `gpt_prior_logits` |
| **Classifier-aware restart** | YES — `LineageFlowClassifierAwareRestart` (Wave 45 Agent G), uses max-prob of `theta` as confidence proxy (fallback), or the upstream `LineageFlowClassifier` when reachable | NO — only GPT-prior-aware |
| **Entropy helper location** | `_adapter_common.per_position_entropy_reduction` (Wave 45 Agent D shared helper) | `KanziGPTPriorRestartPolicy._entropy_from_logits` (private static method, duplicates the helper) |
| **Probabilities vs logits** | theta is row-normalised probabilities — must convert via `log(theta + eps)` BEFORE handing to the shared helper | uses logits directly |
| **Decision metric** | `family_validity_rate` = ESM-2 PLL ≤ 50.0 (continuous-valued, headroom ~3.0 in log-space) | `protein_sequence_validity_rate` = Pfam round-trip ≥ 0.95 (binary, no headroom) |
| **Tier-3 metric-axis close** | `observe_token_indices` returns `argmax(theta_final, axis=-1)` (Wave 44 Agent C) | `observe_token_indices` walks back through `src_digest` chain to find the latest `discrete_idx` carry (Wave 44 Agent C, F-1 fix) |
| **Restart math** | per-position vector (when classifier-aware) or scalar | per-position vector (when GPT-prior) or scalar |
| **LineageFlowClassifier upstream reachability** | via `sys.path.insert` to `data/lineageflow_upstream/` (matches `tools/run_lineageflow_real_ckpt.py` pattern) | not applicable |
| **Current value-add on eval** | TIE_AT_SATURATION (binary validity rate saturates; `framework_wins = 0`) | TIE_AT_SATURATION (binary round-trip saturates; `framework_wins = 0`) |
| **Current glue layer (Wave 45)** | restart policy (`LineageFlowClassifierAwareRestart`) + entropy metric (`observe_entropy_reduction`) | restart policy (`KanziGPTPriorRestartPolicy`) + Wave 44 Tier-3 metric close |

### 2.1 What is reusable from Kanzi

| Reusable? | Item | Notes |
| --- | --- | --- |
| YES | `per_position_entropy_reduction` (the shared helper) | already used by LineageFlow at `lineageflow.py:2148-2150` |
| YES | The entropy-from-logits formula | the `_theta_to_logits` inversion is a LineageFlow-specific adapter fix; Kanzi would just consume logits directly (Wave 45 Agent E §3 documented this) |
| YES | `observe_token_indices` chain-walk pattern | Kanzi's chain-walk (kanzi.py:1997-2011) is a richer pattern than LineageFlow's direct cache lookup (lineageflow.py:2008-2020); we could unify but the LineageFlow pattern is sufficient for its `(L, K) → (L,)` decode |
| NO | GPT-prior restart logic | Kanzi-specific (250M AR prior); LineageFlow has a classifier, not a GPT prior |
| NO | Continuous-latent clamp + additive noise | Kanzi's `apply_restart_distribution` clamps to `[-KANZI_LATENT_CLAMP, +KANZI_LATENT_CLAMP]`; LineageFlow's categorical blend uses row-renormalisation instead |
| NO | `_entropy_from_logits` private static method | the per-position entropy formula is in the shared helper; Kanzi's copy is a duplicate that should arguably be replaced by the shared helper (out of scope here) |

---

## 3. What is missing in current `lineageflow.py`

Read-only audit — these are the load-bearing gaps the dedicated glue
layer needs to close. **No code changes in Phase 1.**

### 3.1 Gaps at the ADAPTER layer (would be addressed by `lineageflow.py` extensions; out of glue-layer scope)

* **F-4 / Wave 45 final-eval bug (blocking):** `_torch_velocity_field`
  at `lineageflow.py:1656-1692` accepts a `(L, K)` float array and
  passes it to `model(x_t, t_t, family=...)`. The published LineageFlow
  flow head (upstream `models/model.py:346-437`) expects
  `x_simplex: (B, L, V=20)` as floats (the upstream classifier outputs
  logits over 20 amino acids, not 33). **However**, the
  `LineageFlowClassifierAwareRestart._upstream_confidence` path at
  `lineageflow.py:823-871` calls `model(x_t, t_t)` (no `family`)
  with a `(1, L, 33)` float tensor — and the `_try_import_lineageflow_classifier`
  flow expects `aa_vocab=33` in `FlowTransformerConfig`, NOT the
  upstream's default `aa_vocab=20`. This is the EsmModel dtype bug
  noted in `docs/audit/wave45-final-eval.md` §"LineageFlow pre-existing bug":
  `argmax(x_t, axis=-1)` is needed before the encoder call to convert
  probabilities → integer ids, AND the vocab size mismatch needs a
  `aa_vocab=33` config stub. **5-LOC fix** documented in
  `wave45-final-eval.md` §1.3 but not yet shipped.
* **`flow_loss_reduction` is not exposed.** The framework's P2-W33-C
  metric set (`per_position_entropy_reduction`,
  `reconstruction_loss`, `flow_loss_reduction`) is only one-third
  implemented for LineageFlow (entropy only). The flow head's MSE
  loss between predicted and target velocity fields is **never
  computed** by the adapter — neither `solve_ode` nor
  `observe_endpoint` reports it. The adapter has access to
  `x_pred`, `v1`, `v2`, `dt` during `solve_ode` (lineageflow.py:1757-1798),
  but does not store the per-step MSE.
* **`reconstruction_loss` is not exposed.** The published LineageFlow
  decoder is **out of scope** for the FM-ODE adapter (decoder is
  separate from the flow head, mirroring Kanzi's design where the
  decoder is "out of scope for the FM-ODE adapter"). However, a
  proxy `reconstruction_loss` against the upstream
  `LineageFlowClassifier`'s per-position logits could be exposed:
  `H(classifier_logits) - H(classifier_logits | theta)` is the
  standard flow-matching information-gain quantity. This is
  currently not implemented.
* **`family_validity_rate` is binary-saturated.** The decision metric
  at `tools/run_real_ckpt_eval.py:1325-1475` uses
  `perplexity <= 50.0` — a hard threshold. Wave 45 Agent H
  (`wave45-final-eval.md`) identified this as the
  Tier-3-claim-blocks-`framework_wins > 0` root cause: both arms
  reach the saturation ceiling and `delta_pct = 0`. A continuous
  `family_validity_continuous` metric (perplexity or ESM-2 PLL
  as a continuous value, not a binary) is needed.
* **`paper_quantities` is accepted-but-ignored** by
  `observe_token_indices` (lineageflow.py:1975-1990) and
  `observe_entropy_reduction` (lineageflow.py:2097-2101). The F-3
  fix (Wave 45 Agent C) threads a real snapshot through to the
  adapter, but the adapter does not consume it. Future waves can
  use `e_rho` / `sheet_A` to bias decoding (e.g. swap argmax to
  temperature-1.0 sampling when `e_rho < floor`).

### 3.2 Gaps at the GLUE layer (the focus of this review)

* **No `LineageFlowGlue` class exists.** The adapter is monolithic —
  metrics, restart policies, conditioning, and forward math all
  live in `LineageFlowAdapter`. Kanzi is in the same shape, but the
  user directive calls out LineageFlow specifically as the model
  whose flow-component metrics need dedicated glue.
* **No `flow_loss_reduction` helper.** This is a §3 framework
  gap that the LineageFlow glue layer should close for LineageFlow
  specifically (the framework layer cannot close it without
  perturbing the Protocol — and the Wave 45 directive forbids
  Protocol changes).
* **No `reconstruction_loss` helper.** The dedicated glue layer
  should provide a classifier-logits-based reconstruction loss.
* **No `family_validity_continuous` metric.** A continuous ESM-2
  PLL reading (rather than the binary `perplexity <= 50.0`)
  should be exposed; this is the metric that gives the Tier-3
  metric-axis claim headroom.
* **No `compute_composite(trace_before, trace_after)` for
  LineageFlow.** The composite benchmark formula designed in Wave 46
  Agent C needs per-model glue to compute it (kanzi composite,
  lineageflow composite are different formulas because the
  decision metric + flow-component metrics differ).
* **Eval pipeline does not call glue.** `_compute_lineageflow_real_metric_via_trace`
  at `tools/run_real_ckpt_eval.py:1325-1475` only computes the
  binary `family_validity_rate` (ESM-2 PLL ≤ 50.0). It does not
  call `observe_entropy_reduction`, it does not compute
  `flow_loss_reduction`, and it does not surface a composite.
  The Wave 45 final-eval (`wave45-final-eval.md` §"Honest reading")
  explicitly identifies this as the Tier-3-claim gap.

### 3.3 Gaps at the EVAL-PIPELINE layer (out of glue-layer scope; flagged for Wave 47 follow-ups)

* **The eval pipeline does not consume
  `observe_entropy_reduction`.** Wave 45 Agent E §"Follow-ups"
  flagged this for the wave owner; still open.
* **The eval pipeline does not consume `flow_loss_reduction`** —
  not implemented at the adapter, not consumed at the eval.
* **The eval pipeline does not consume `family_validity_continuous`** —
  only the binary `family_validity_rate` is consumed.
* **`_torch_velocity_field` dtype boundary bug.** The Wave 45 final
  eval (`wave45-final-eval.md` §"LineageFlow pre-existing bug")
  documented a 5-LOC fix that converts probabilities → integer ids
  before the encoder call. Out of glue-layer scope; a separate PR.

---

## 4. Proposed glue layer design

### 4.1 File path: NEW `adaptive_reflow/adapters/lineageflow_glue.py`

Rationale for a NEW file (vs. extending `lineageflow.py`):

* `lineageflow.py` is already 2303 LOC — extending it would push it
  past the 2500-LOC threshold that triggers the
  `tests/test_protocol_deep_audit.py::test_j_audit_inventory_smoke`
  pre-existing failure mode (the test's
  `PROTOCOL_METHOD_SHAPE` table needs a 1-line update for
  `observe_token_indices`; further bloat increases the surface area
  for similar failures).
* The user directive explicitly calls for a **dedicated glue layer**
  — a separate module makes the boundary clean.
* Mirrors the framework's separation of concerns: the adapter
  carries the Protocol surface; the glue layer carries the
  metric-layer derivations.

### 4.2 Class: `LineageFlowGlue(adapter: LineageFlowAdapter)`

```python
@dataclass(frozen=True)
class LineageFlowGlue:
    """Pure-glue metric layer for LineageFlow (Wave 47).

    Holds a reference to a :class:`LineageFlowAdapter`; computes
    flow-component metrics, family-validity continuous metrics,
    and the composite benchmark for the Tier-3 metric-axis
    claim. 100% pure (no model logic — that lives in the
    adapter). Stdlib + numpy only.

    Constructor parameters
    ----------------------

    adapter
        The :class:`LineageFlowAdapter` whose native-state cache
        carries the ODE trajectories consumed by the metric
        methods.
    esm_perplexity_key
        HuggingFace ESM-2 model id (default
        ``"facebook/esm2_t33_650M_UR50D"``); used by
        :meth:`compute_family_validity_continuous` to compute
        per-sequence PLL. The key is held as a string so this
        glue is import-safe without ``torch`` /
        ``transformers``; the helper lazy-loads when first
        invoked.
    composite_weights
        Tuple of 3 non-negative floats
        ``(w_entropy, w_flow, w_recon)`` summing to 1.0; the
        weights for the composite benchmark. Defaults to
        ``(0.5, 0.3, 0.2)`` per Wave 46 Agent C's design.
    """

    adapter: LineageFlowAdapter
    esm_perplexity_key: str = "facebook/esm2_t33_650M_UR50D"
    composite_weights: tuple[float, float, float] = (0.5, 0.3, 0.2)
```

### 4.3 Methods

#### 4.3.1 `compute_flow_loss_reduction(trace: ODEIntegratorTrace, *, baseline_trace: ODEIntegratorTrace | None = None) -> dict[str, float]`

* **Computes:** `flow_loss_reduction = flow_loss(baseline_trace) - flow_loss(trace)`
* **`flow_loss(trace)`** = mean per-step MSE between predicted
  velocity field and target velocity field over the trajectory
  cached at `trace.native_state_digest`. The adapter's
  `solve_ode` does not currently store per-step `x_pred`,
  `v1`, `v2`, `dt` (it only stores the `(N+1, L, K)` trajectory
  in the native-state cache). **The glue layer needs the adapter
  to expose a `flow_loss` cache key OR a re-derivation via the
  trajectory alone (which is impossible — the velocity field is
  not deterministic from `x` alone; it's `v_theta(x, t, family)`).
  Proposal: extend `solve_ode` to write
  `{"trajectory": ..., "flow_loss_per_step": ...}` to the
  native-state cache, then the glue layer just reads it.
  Alternative: recompute the velocity field by calling
  `_velocity_field(x, t, conditioning, guidance_scale)` for
  each `(x_cur, t)` pair; this is O(N) extra work per
  `solve_ode` but doesn't perturb the adapter's storage. This
  is the **preferred Phase 2 design** — no adapter change.
* **`baseline_trace` (optional):** when supplied, returns
  the framework-vs-baseline delta; when omitted, returns
  the within-trajectory reduction
  `flow_loss(trajectory[0]) - flow_loss(trajectory[-1])`
  (the framework sharpens vs the prior).
* **Returns:** `{"flow_loss_reduction": float, "flow_loss": float}`
  (always includes the absolute value for downstream audits).
* **Signature parity** with `observe_entropy_reduction`:
  `trace` first, optional `baseline_trace` second; the metric
  layer consumes both the same way.

#### 4.3.2 `compute_reconstruction_loss(trace: ODEIntegratorTrace, *, ref_theta: ArrayF64 | None = None) -> dict[str, float]`

* **Computes:** the upstream `LineageFlowClassifier`-based
  reconstruction-loss proxy:
  `reconstruction_loss = H(classifier_logits(ref)) - H(classifier_logits(theta_final))`
  where `classifier_logits(theta) = LineageFlowClassifier(theta, t=1.0)`
  and `H` is the shared `per_position_entropy_reduction`.
* **`ref_theta` (optional):** when supplied, computes
  framework-vs-reference delta; when omitted, computes
  within-trajectory.
* **Returns:** `{"reconstruction_loss": float, "reconstruction_loss_before": float, "reconstruction_loss_after": float}`
* **Honest fallback:** the upstream classifier is reachable only via
  `sys.path.insert` to `data/lineageflow_upstream/`. Mirrors
  `LineageFlowClassifierAwareRestart._try_import_lineageflow_classifier`
  (lineageflow.py:574-617). On import failure, returns
  `{"reconstruction_loss": nan, "reason": "upstream_unavailable"}`
  so callers can distinguish "metric undefined" from "metric == 0".
* **Synthetic-mode degradation:** when the adapter is in
  `synthetic` mode (no real forward), the upstream classifier
  has no real signal either; we use the adapter-internal
  `_theta_to_logits` proxy and the entropy reduction against
  a uniform reference.

#### 4.3.3 `compute_family_validity_continuous(trace: ODEIntegratorTrace) -> dict[str, float]`

* **Computes:** the **continuous** version of the
  `family_validity_rate` decision metric — per-sequence ESM-2
  pseudo-log-likelihood (PLL) perplexity, **not** the binary
  `perplexity <= 50.0` reading.
* **Algorithm:** consume `adapter.observe_token_indices(trace, paper_quantities=...)`,
  decode via `_decode_lineageflow_idx_to_aa` (the same
  mod-20 AA proxy already in the eval pipeline at
  `run_real_ckpt_eval.py:1121-1147`), and compute ESM-2 PLL
  via the cached `esm_perplexity_key`.
* **Returns:** `{"perplexity": float, "nll_per_token": float, "validity_rate_at_threshold_50": int}`
  so downstream consumers can compute the binary reading if
  desired (back-compat) AND have a continuous value for
  headroom.
* **Honest fallback:** when ESM-2 is not importable (synthetic
  mode, CPU-only env), returns
  `{"perplexity": nan, "reason": "esm_unavailable"}` — same
  protocol as `_compute_lineageflow_real_metric_via_trace`
  (run_real_ckpt_eval.py:1411-1441).
* **Why this matters:** the Wave 45 final-eval
  (`wave45-final-eval.md` §"Kanzi metric saturation" + §"Honest reading")
  identified metric-saturation at the binary threshold as the
  Tier-3-claim blocker. A continuous perplexity reading gives
  the framework-vs-baseline comparison headroom (~3.0 in
  log-space) so `framework_wins > 0` can land.

#### 4.3.4 `compute_composite(trace_before: ODEIntegratorTrace, trace_after: ODEIntegratorTrace) -> dict[str, float]`

* **Computes:** the LineageFlow composite benchmark per Wave 46
  Agent C's design (the master plan at
  TODO
  is `todo/algo-improvement-LF-composite-benchmark.md` — to be
  authored by Wave 46 Agent D).
* **Formula:**
  ```text
  composite = w_entropy * entropy_reduction
            + w_flow    * flow_loss_reduction
            + w_recon   * reconstruction_loss
  ```
  where `w_*` are `composite_weights`.
* **Inputs:**
  * `trace_before` — the baseline arm's ODE trace (1 round @
    `nfe`).
  * `trace_after` — the framework arm's ODE trace (3 rounds @
    `ceil(nfe/3)` with restart-blend between rounds).
* **Returns:**
  `{"composite": float, "entropy_reduction": float, "flow_loss_reduction": float, "reconstruction_loss": float}`
  so the audit trail can decompose the composite into its
  components.
* **Note:** the binary `family_validity_continuous` is NOT part
  of the composite — it is a *headroom* metric for the
  Tier-3-claim close; the composite is a *value-add* metric
  for the framework's restart-blend policy. Different purpose,
  different metric.

#### 4.3.5 Helper methods (private)

```python
def _velocity_field_recompute(
    self, trace: ODEIntegratorTrace, *, t: float
) -> ArrayF64:
    """Recompute the velocity field at (x_cur, t) for one trajectory step.

    Mirrors the adapter's private ``_velocity_field`` helper
    but is import-safe without `torch` by routing through the
    adapter's public ``solve_ode`` infrastructure (re-uses the
    cached conditioning). Stdlib + numpy.
    """
```

```python
def _esm_perplexity(self, sequence: str) -> float:
    """Compute ESM-2 PLL perplexity for a single sequence.

    Mirrors ``_LINEAGEFLOW_ESM_CACHE`` in
    ``tools/run_real_ckpt_eval.py:1422-1431`` — the same
    module-level cache. Stdlib-only at the import layer; the
    ESM model is lazy-loaded on first call.
    """
```

```python
def _paper_quantities_for(self, seed: int, nfe: int) -> Any:
    """Materialise a :class:`PaperQuantitiesSnapshot` per Wave 45 F-3.

    Re-uses the per-model profile from
    ``tools/run_real_ckpt_eval.py:_PAPER_QUANTITY_PROFILES``
    (the ``"0.5 * math.sin(x)"`` default). Stdlib + numpy
    only (the AST-restricted profile-source compilation lives
    in the eval pipeline; the glue layer's helper is a thin
    wrapper).
    """
```

### 4.4 Metric keys (for `tools/run_real_ckpt_eval.py` consumption)

The glue layer exports metric-key constants (mirror of
`PER_POSITION_ENTROPY_REDUCTION`):

```python
FLOW_LOSS_REDUCTION: str = "flow_loss_reduction"
RECONSTRUCTION_LOSS: str = "reconstruction_loss"
FAMILY_VALIDITY_CONTINUOUS: str = "family_validity_continuous"
LINEAGEFLOW_COMPOSITE: str = "lineageflow_composite"
```

These constants are importable from
`adaptive_reflow.adapters.lineageflow_glue` so the eval pipeline
can key on them without importing the metric bodies.

---

## 5. Integration points

### 5.1 Where the glue is called

The glue layer is consumed by `tools/run_real_ckpt_eval.py` at the
**per-cell** level (mirroring the existing
`_compute_lineageflow_real_metric_via_trace` path):

```text
_run_cell(model="lineageflow", seed=42, nfe=50)
  → _solve_baseline(adapter, nfe=50, seed=42) → baseline_trace
  → _solve_framework(adapter, nfe=50, seed=42, n_rounds=3) → framework_trace
  → glue = LineageFlowGlue(adapter=adapter)
  → _compute_metric_baseline(  # glue-aware
        glue, baseline_trace,
        metric_name="family_validity_continuous",
        ...
    )
  → _compute_metric_framework(  # glue-aware
        glue, framework_trace,
        metric_name="family_validity_continuous",
        ...
    )
  → composite_value = glue.compute_composite(baseline_trace, framework_trace)
```

The existing `_compute_lineageflow_real_metric_via_trace` becomes a
thin wrapper around `glue.compute_family_validity_continuous` so the
binary `family_validity_rate` is preserved (back-compat) while the
continuous perplexity is added.

### 5.2 New dispatch path in `_compute_metric`

Extend `tools/run_real_ckpt_eval.py:_compute_metric` (currently at
`run_real_ckpt_eval.py:1578-1739`) to:

1. **Try the glue layer first** (when `model == "lineageflow"`):
   instantiate `LineageFlowGlue(adapter=adapter)` (if `adapter is
   not None`) and dispatch to
   `glue.compute_family_validity_continuous(trace)` for the
   `family_validity_continuous` metric name, and
   `glue.compute_composite(baseline_trace, framework_trace)`
   for the `lineageflow_composite` metric name.
2. **Fall back to legacy `_compute_lineageflow_real_metric_via_trace`**
   when the glue layer's metrics are unavailable (synthetic mode
   with no ESM-2, etc.).
3. **Surface the glue's outputs** in the per-cell debug dict
   under the `glue` key so the audit trail can decompose the
   composite into its components.

### 5.3 Integration with paper-quantity threading

Wave 45 Agent C's F-3 fix threads a real `PaperQuantitiesSnapshot`
through to `observe_token_indices`. The glue layer's
`_paper_quantities_for` helper reuses the same per-model profile
(`g(x) = 0.5 * math.sin(x)`) so the paper-quantity surface is
identical between the eval-pipeline helper and the glue helper.

### 5.4 Integration with the LineageFlow restart policies

The `LineageFlowClassifierAwareRestart` policy (Wave 45 Agent G) is
a per-position restart blend; the glue layer is orthogonal to it.
The two interact at `apply_restart_distribution` time:
* The restart policy produces `m_vec` from the upstream classifier.
* `solve_ode` integrates the per-position categorical forward.
* The glue layer reads the resulting `trajectory` from the
  native-state cache and computes the flow-component metrics.

No Protocol change is needed for this integration; the glue is
pure-consumer.

---

## 6. Backward-compat analysis

### 6.1 What the glue layer does NOT change

| Surface | Why preserved |
| --- | --- |
| `LineageFlowAdapter` Protocol methods (10 of them) | the adapter is already Protocol-conformant; adding glue does not require adapter changes for the entropy metric (Wave 45 Agent E already added it) |
| `apply_restart_distribution` math | preserved verbatim (renormalisation at lines 1500-1502 + clip at 1507 + defensive re-norm at 1509-1511); the `LineageFlowClassifierAwareRestart` opt-in flag defaults to `False` so 22 existing tests keep their byte-identical behaviour |
| `observe_token_indices` | unchanged; the glue layer is a consumer, not a producer |
| `observe_entropy_reduction` | unchanged; the glue layer wraps it but does not modify it |
| `_PAPER_QUANTITY_PROFILES` default profile (`"0.5 * math.sin(x)"`) | preserved; the glue layer reuses the eval pipeline's profile |
| Wave 45 final-eval wallclock ratios (1.0–1.6× baseline) | the glue adds O(N) velocity-field recomputation per `compute_flow_loss_reduction` call; the wallclock cost is bounded by `n_cells * 2 * (entropy + flow + recon + composite)`; estimated ≤5% wallclock increase |

### 6.2 What changes (Phase 2 only — not in this review)

| Change | File | Risk |
| --- | --- | --- |
| NEW `lineageflow_glue.py` module | `adaptive_reflow/adapters/lineageflow_glue.py` | LOW — pure consumer; stdlib + numpy only; no model logic |
| NEW `LineageFlowGlue` class | same file | LOW — frozen dataclass; no Protocol change |
| NEW `_compute_velocity_field_for_glue` helper | same file | LOW — wraps the adapter's existing `_velocity_field` private helper |
| NEW `compute_flow_loss_reduction` / `compute_reconstruction_loss` / `compute_family_validity_continuous` / `compute_composite` methods | same file | MEDIUM — adds O(N) recomputation per `flow_loss_reduction` call; Phase 2 must measure wallclock impact and document |
| `_compute_metric` dispatch | `tools/run_real_ckpt_eval.py` | MEDIUM — adds glue-aware path; legacy path preserved as fallback |
| Metric-key constants `FLOW_LOSS_REDUCTION` / `RECONSTRUCTION_LOSS` / `FAMILY_VALIDITY_CONTINUOUS` / `LINEAGEFLOW_COMPOSITE` | `lineageflow_glue.py` exports + `__all__` | LOW — additive; no consumer migration |

### 6.3 What Phase 2 MUST NOT change

| Surface | Reason |
| --- | --- |
| `FlowMatchingODEAdapter` Protocol | Wave 45 directive forbids Protocol changes |
| `LineageFlowAdapter` public methods | the adapter is the canonical Protocol impl; the glue is a consumer |
| `_install_checkpoint_compat` shim | Wave 36 Agent C breakthrough; preserved |
| `LineageFlowClassifierAwareRestart` policy | Wave 45 Agent G; preserved |
| `per_position_entropy_reduction` shared helper | Wave 45 Agent D; the glue reuses it |
| `_PAPER_QUANTITY_PROFILES` default | Wave 45 Agent C F-3 fix; preserved |
| The 22 existing tests' byte-identical behaviour | Wave 45 regression guard; the glue layer does not modify the adapter |

### 6.4 Test surface (Phase 2)

| Test | Asserts |
| --- | --- |
| `test_lineageflow_glue_imports` | class is importable + 4 metric keys are in `__all__` |
| `test_lineageflow_glue_compute_flow_loss_reduction_within_trajectory` | `flow_loss(traj[0]) - flow_loss(traj[-1])` matches hand-computed MSE |
| `test_lineageflow_glue_compute_flow_loss_reduction_framework_vs_baseline` | returns the delta when `baseline_trace` is supplied |
| `test_lineageflow_glue_compute_reconstruction_loss_with_upstream_unavailable` | degrades to `nan` + `reason="upstream_unavailable"` |
| `test_lineageflow_glue_compute_reconstruction_loss_with_upstream_available` | matches hand-computed H(classifier_logits) delta |
| `test_lineageflow_glue_compute_family_validity_continuous_with_esm` | returns a finite perplexity + back-compat binary validity_rate_at_threshold_50 |
| `test_lineageflow_glue_compute_family_validity_continuous_without_esm` | degrades to `nan` + `reason="esm_unavailable"` |
| `test_lineageflow_glue_compute_composite_decomposition` | composite = sum of weighted components; weights sum to 1.0 |
| `test_lineageflow_glue_composite_weights_validation` | rejects weights that don't sum to 1.0 in `__post_init__` |
| `test_lineageflow_glue_does_not_modify_adapter` | the adapter's Protocol methods return the same values before/after glue calls |

Estimated test count: 10 (matches the Wave 45 entropy suite + Wave 45
classifier-restart suite size).

### 6.5 Doc surface (Phase 2)

| Doc | Change |
| --- | --- |
| `docs/PLUG_IN_YOUR_MODEL.md` | APPEND LineageFlow glue section (mirrors the Wave 21 Kanzi section) |
| `docs/audit/wave47-lineageflow-glue-design.md` | NEW — Phase 2 design doc (this is the Phase 1 review) |
| `docs/audit/wave47-lineageflow-glue-impl.md` | NEW — Phase 2 implementation doc |
| `docs/theory/operating-regime.md` §11 | APPEND the dedicated LineageFlow flow-component metrics (Wave 45 Agent E §"Follow-ups" item 3 was for the entropy metric only; Phase 2 extends with `flow_loss_reduction` + `reconstruction_loss`) |
| `docs/CONSOLIDATED_RESULTS.md` §15.x | APPEND Tier-3-claim-close evidence (continuous perplexity + composite benchmark) |

---

## 7. Files reviewed (READ-ONLY, no changes in this Phase 1 review)

| File | LOC | What |
| --- | --- | --- |
| `adaptive_reflow/adapters/lineageflow.py` | 2303 | the LineageFlow adapter |
| `adaptive_reflow/adapters/_adapter_common.py` | 277 | shared helpers (`per_position_entropy_reduction`, `memory_fraction_for`, `make_adapter_capabilities`, `make_ref`, `seed_from_ids`, `digest_state`, `kaiming_uniform`, `NativeStateCache`, `torch_is_available`) |
| `adaptive_reflow/adapters/kanzi.py` | 2189 | the Kanzi adapter (for comparison) |
| `adaptive_reflow/universal/adapter.py` | 450 | the `FlowMatchingODEAdapter` Protocol + `AdapterCapabilities` + `CapabilityMissingError` / `CapabilityMismatchError` |
| `data/lineageflow_upstream/models/model.py` | 446 | upstream `LineageFlowClassifier` (657M ESM-2-650M + flow head) |
| `data/lineageflow_upstream/inference/inference.py` | 430+ | upstream `_install_checkpoint_compat` shim (mirrored at `lineageflow.py:902-933`) |
| `docs/audit/wave45-lineageflow-entropy-metric.md` | 199 | Wave 45 Agent E P2-W33-C metric promotion |
| `docs/audit/wave45-lineageflow-classifier-restart.md` | 215 | Wave 45 Agent G `LineageFlowClassifierAwareRestart` |
| `docs/audit/wave45-f2-fix.md` | 298 | Wave 45 Agent B F-2 eval-pipeline signature fix |
| `docs/audit/wave45-f3-fix.md` | 300 | Wave 45 Agent C F-3 paper-quantities threading fix |
| `docs/audit/wave45-final-eval.md` | 192 | Wave 45 Agent H Tier-3 re-eval (framework_wins still 0) |
| `tools/run_real_ckpt_eval.py` | 90,156 bytes | the eval pipeline (`_solve_baseline`, `_solve_framework`, `_compute_metric`, `_compute_lineageflow_real_metric_via_trace`, `_compute_lineageflow_real_metric`, `_PAPER_QUANTITY_PROFILES`) |

---

## 8. Phase 2 outline (the implementation plan — for the wave owner)

This review is Phase 1 (READ-ONLY design). Phase 2 ships the
implementation; estimated ~600 LOC across 4 files:

1. **NEW `adaptive_reflow/adapters/lineageflow_glue.py`** (~450 LOC):
   * `LineageFlowGlue` dataclass + 4 public methods + 3 private helpers.
   * Stdlib + numpy only (mirrors `_adapter_common.py` discipline).
   * `__all__` exports 4 metric-key constants + the class.
   * Docstrings on every method (mirrors Kanzi's style at
     `kanzi.py:670-882`).
2. **`tools/run_real_ckpt_eval.py`** (~80 LOC delta):
   * New `_compute_lineageflow_real_metric_via_trace_v2` that
     prefers `glue.compute_family_validity_continuous` and falls
     back to the legacy `_compute_lineageflow_real_metric_via_trace`.
   * New `_compute_lineageflow_composite` that consumes
     `glue.compute_composite(baseline_trace, framework_trace)`.
   * Wire into `_compute_metric` dispatch at
     `run_real_ckpt_eval.py:1653-1659`.
3. **`tests/test_adapters/test_lineageflow_glue.py`** (~200 LOC,
   ~10 tests):
   * Mirror of `tests/test_adapters/test_lineageflow.py`
     structure.
   * All 10 tests pass byte-identically to the existing 42
     (entropy + classifier-restart + glue).
4. **`docs/audit/wave47-lineageflow-glue-impl.md`** (~150 LOC):
   * Phase 2 design doc.
5. **`docs/CONSOLIDATED_RESULTS.md`** APPEND §15.x:
   * Tier-3-claim-close evidence (continuous perplexity +
     composite benchmark).
   * Wallclock impact report (estimated ≤5%).

**Total Phase 2 delta: ~880 LOC** across 5 files. No Protocol change;
no adapter change; no `_adapter_common.py` change; no framework change.

---

## 9. Open questions for the wave owner

1. **`flow_loss_reduction` recomputation cost.** Should we (a) extend
   `solve_ode` to write `flow_loss_per_step` to the native-state
   cache (perturb the adapter storage) or (b) recompute the
   velocity field from the trajectory at glue-time (no adapter
   change; O(N) extra work)? The review recommends (b) for
   backward-compat; the cost is bounded by `n_cells * 2 * n_steps`
   which is ≤ 10k velocity-field evaluations at the default
   NFE-200 / n_rounds-3 settings — likely < 1 second wallclock
   per cell.
2. **`reconstruction_loss` upstream classifier availability.** The
   upstream `LineageFlowClassifier` requires the 657M weights to
   be loaded; even when importable, the forward pass costs ~50ms
   per sequence on a 5090. Should the glue layer cache the
   per-trajectory reconstruction loss or recompute per call?
   Recommend: cache keyed on `(trace.native_state_digest,
   sequence)`.
3. **Composite weights.** Wave 46 Agent C designed a default
   `(0.5, 0.3, 0.2)` weighting. Is this the right default for
   LineageFlow specifically, or should protein-FM have a different
   profile? Out of scope here; flagged for Wave 46 Agent D.
4. **`family_validity_continuous` headroom.** The Wave 45 final
   eval shows binary validity saturates at 1.0. Continuous
   perplexity should give headroom; is the threshold `perplexity <= 50.0`
   the right cut-off for the binary reading? Recommend keeping
   it (back-compat) and adding continuous alongside.

---

## 10. Summary

* **Read scope:** 2303 LOC `lineageflow.py` + 2189 LOC `kanzi.py` +
  277 LOC `_adapter_common.py` + 450 LOC `universal/adapter.py` +
  446 LOC upstream `model.py` + 5 Wave 45 audit docs + 90kB
  `run_real_ckpt_eval.py`. All read-only.
* **Architecture understood:** 2-channel (amino_acid_categorical +
  pfam_family_cond), per-position theta ODE state, classifier-aware
  per-position restart policy, argmax decode + entropy reduction
  metric.
* **Missing glue identified:**
  * `flow_loss_reduction` (not implemented at the adapter).
  * `reconstruction_loss` (not implemented; upstream classifier
    proxy feasible).
  * `family_validity_continuous` (not implemented; binary
    threshold saturates).
  * `compute_composite` (not implemented; Wave 46 Agent C's
    formula needs per-model glue).
* **Design proposed:** NEW `adaptive_reflow/adapters/lineageflow_glue.py`
  with `LineageFlowGlue(adapter: LineageFlowAdapter)` and 4
  public methods + 3 private helpers. Stdlib + numpy only.
  ~450 LOC.
* **Integration clear:** `_compute_metric` in
  `tools/run_real_ckpt_eval.py` dispatches to the glue layer for
  `model == "lineageflow"`. Backward-compat: legacy path preserved
  as fallback.
* **Backward-compat verified:** No Protocol change, no adapter
  change, no shared-helper change, no `_PAPER_QUANTITY_PROFILES`
  change, 22 existing tests' byte-identical behaviour preserved.
* **Phase 2 outline ready:** ~880 LOC across 5 files; ~10
  regression tests; Tier-3-claim close as the headline outcome.

The dedicated LineageFlow glue layer closes the Tier-3
metric-axis gap that has blocked `framework_wins > 0` for the
protein axis since Wave 43.