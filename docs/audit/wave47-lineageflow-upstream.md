# Wave 47 Agent B — LineageFlow upstream review

**Scope**: `data/lineageflow_upstream/` (models, core, inference, dataset) read-only review
to identify the right way to expose **`flow_loss`** and **`reconstruction_loss`** as
continuous metrics for the framework's composite eval pipeline.

**Status**: design only. This is **Phase 1** of the composite-benchmark integration
(Wave 46 master plan). No code changes, no commit beyond this review doc.

**Related prior work**:
* Wave 10 — LineageFlow integration + adapter (`adaptive_reflow/adapters/lineageflow.py`).
* Wave 36 — upstream clone + 5-LOC `SamplerConfig` shim.
* Wave 41 — upstream numerical forward unblock.
* Wave 42 — `--force-mode real` evaluation.
* Wave 44 — `observe_token_indices` + `per_position_entropy_reduction` (P2-W33-C).
* Wave 45 — `LineageFlowClassifierAwareRestart` (classifier log-prob proxy).
* Wave 46 — composite benchmark formula (Agent C) + review + research.

---

## 1. LineageFlowClassifier forward signature

**File**: `data/lineageflow_upstream/models/model.py:346-437`

```python
class LineageFlowClassifier(nn.Module):
    def forward(
        self,
        x_simplex: torch.Tensor,            # (B, L, V=20) simplex-valued input
        t:          torch.Tensor,           # (B,)   scalar times
        pad_mask:   Optional[torch.Tensor] = None,  # (B, L) bool, True for real tokens
        gap_flag:   Optional[torch.Tensor] = None,  # (B, L) bool/float, 1 for gap positions
        family_id:  Optional[torch.Tensor] = None,  # (B,)   family conditioning
    ) -> torch.Tensor:                       # (B, L, 20) logits over 20 AA only
        ...
```

Key observations:

1. **Input is simplex-valued**, not token-id-based. The head takes a per-position
   probability distribution over the 20 canonical amino acids as input. This is the
   *current* state of the ODE trajectory `x_t` in the framework adapter.
2. **Output is logits over the 20 amino acids only** (no gap head, no pad head).
   Gap and PAD positions are handled inside the encoder via ESM-token-embedding
   override (lines 378-388) rather than through the output head.
3. **Family conditioning** is an optional embedding (`family_embed_dim`); when
   disabled (`family_embed_dim=0`) the model is unconditional.
4. **Time** is the `α_t` of the Dirichlet conditional flow, normalised by the
   config's `α_min..α_max` (defaults 0..16) into `(0,1)` for the sinusoidal
   embedding.
5. **Expected ESM embedding trick** (lines 370-388): the simplex `x_t` is
   embedded via `Σ_k x_t[k] * emb(AA_k)`, then gap/pad positions are
   overridden with their dedicated embeddings. This keeps the input
   continuous and preserves pretrained biology.

The model **does not** expose a `compute_flow_loss(...)` method. The training
objective (per the Wave 10 paper §3.2) is a flow-matching MSE on the predicted
velocity field, evaluated by `inference.compute_family_vector_field(...)` and
`c_h(...)` at training time. The model's only forward returns logits.

---

## 2. flow_loss computation API

**There is no `model.compute_flow_loss(theta, dt)` method.** The loss is
constructed by composing the model forward with the Dirichlet conditional flow
coefficient. The two relevant functions are:

### 2a. `compute_family_vector_field` (per-step velocity)

**File**: `data/lineageflow_upstream/inference/inference.py:299-365`

```python
@torch.no_grad()
def compute_family_vector_field(
    x: torch.Tensor,                 # (B, L, K) simplex
    t: torch.Tensor,                 # (B,)   times
    logits: torch.Tensor,            # (B, L, K) classifier logits
    alpha_h: torch.Tensor,           # (L, K)   family prior
    denoiser_temperature: float = 1.0,
    pad_mask: Optional[torch.Tensor] = None,
    gap_mask: Optional[torch.Tensor] = None,
) -> torch.Tensor:                   # (B, L, K) vector field v_hat
```

The math is the family-specific Dirichlet conditional flow:

```
p_hat  = softmax(logits / T)            # classifier posterior over residues
c_vals = c_h(z, alpha_i, alpha_rest, alpha_t, alpha_max)   # Eq. (ch)
w      = c_vals * p_hat                 # (B, L, K)
v_hat  = w - w.sum(-1, keepdim=True) * x
```

### 2b. `integrate_base_flow` (per-segment ODE integration)

**File**: `data/lineageflow_upstream/inference/inference.py:382-426`

```python
@torch.no_grad()
def integrate_base_flow(
    model: torch.nn.Module,          # LineageFlowClassifier
    x0: torch.Tensor,                # (B, L, K) simplex at t0
    alpha_h: torch.Tensor,           # (L, K) family prior
    t0: float, t1: float,
    pad_mask: torch.Tensor,
    gap_mask: torch.Tensor,
    family_id: Optional[torch.Tensor],
    denoiser_temperature: float = 1.0,
    steps: int = 200,
    method: str = "euler",
) -> torch.Tensor:                   # (B, L, K) simplex at t1
```

The Euler loop calls `model(x, t)` at each substep, then `compute_family_vector_field`
to advance `x`. This is exactly the upstream analogue of our
`LineageFlowAdapter.solve_ode` (which carries the same loop + classifier-aware
restart on the `torch` mode path).

### 2c. flow_loss math (paper §3.2)

The LineageFlow training objective is the **flow-matching MSE** on the
velocity field, summed over positions and integrated over time:

```
flow_loss(theta_t) = E_t [ || v_target(x_t, t) - v_theta(x_t, t, family) ||^2 ]
```

For the framework's purposes — the **composite benchmark** uses the **trained
model as a fixed score function**, not for training — the right "loss" is the
**classifier cross-entropy** against the current state at the endpoint. This
is the **continuous, framework-improving** surrogate for the training loss:

```
flow_loss_per_round(theta, t_max) =
    - (1 / (B * L)) * Σ_{b,l} log p_theta(a*_{b,l} | x_{b,l}, t_max)
```

where `a*_{b,l} = argmax theta_{b,l}` is the current residue choice and
`p_theta = softmax(model(theta, t_max).logits / T)`.

This metric is:

* **continuous** (bounded in `[0, log K]` with `K = 20`).
* **framework-improving** (lower NLL on the *current* state is monotonically
  connected to framework improvement; the framework's per-round re-inference
  should drive it down).
* **adapter-bounded** (uses the upstream classifier; matches the
  `_lineageflow_classifier_confidence_proxy` we already expose).
* **aligned with the Wave 45 P2-W33-C metric** (`per_position_entropy_reduction`),
  which is the entropy analogue; the two together span the full
  `(mean-field) × (sharpness)` axes of the per-position categorical.

### 2d. API surface — where to call from

The cleanest glue point is **`LineageFlowAdapter.observe_endpoint` + a new
`observe_classifier_nll`** method. The upstream `compute_family_vector_field`
already calls `model(x, t)` per step; we can extend `solve_ode` to **also
accumulate the per-step NLL** into the trace. The Wave 45 pattern
(`observe_entropy_reduction`) is the template:

```python
def solve_ode(self, state, condition, *, seed) -> ODEIntegratorTrace:
    """... unchanged Euler/Heun loop, BUT accumulate
    per-step classifier NLL into the trajectory cache entry."""
    for i in range(1, t_grid.size):
        ... # existing v1, v2, x_cur update
        # NEW: classifier NLL accumulator
        with torch.no_grad():
            logits = model(x_cur, t_tensor)
            log_probs = F.log_softmax(logits / T, dim=-1)
            nll_t = -log_probs.argmax(-1).gather(-1, ...).mean()
        flow_loss_per_step.append(float(nll_t))
        traj[i] = x_cur
    ... # store flow_loss_per_step in self._native_states[traj_digest]
```

The new metric accessor mirrors `observe_entropy_reduction`:

```python
def observe_flow_loss(self, trace, paper_quantities=None) -> dict[str, float]:
    """Per-position classifier NLL at the ODE endpoint.

    Continuous, framework-improving, bounded in [0, log K=20] ~= 3.00.

    Returns:
        {"flow_loss": <scalar>}
    """
```

### 2e. Why this is the *right* loss to expose

* The framework is **post-training**; we are evaluating trained-model behaviour,
  not training. Flow-matching MSE on a frozen model is degenerate (zero at
  inference).
* Classifier NLL on the **current categorical state** is the **post-training
  analogue** of the FM loss in the same way that free energy bounds the
  likelihood: high NLL → the categorical state is in a low-density region of
  `p_theta`; low NLL → high-density region.
* It is **adapter-local** (no HMMER, no ESMFold, no MSA toolchain) — the
  classifier is already loaded by `LineageFlowClassifier.forward`.
* It is **identical in math** to the upstream `token_dirichlet_mutation`'s
  `post = softmax(logits / T)` line (inference.py:569) — we are not inventing
  a new score, we are just consuming the classifier that the upstream
  inference already uses for mutation selection.

---

## 3. reconstruction_loss

**There is no explicit "reconstruction loss" in the LineageFlow paper.** The
closest analogue is the **per-position categorical distance between the
ODE endpoint and either the (a) Pfam-held-out reference, or (b) the initial
state**. Two natural formulations:

### 3a. Per-position categorical KL to the prior (self-distance)

```
recon_loss(theta_t, alpha_h) =
    - (1 / L) * Σ_l Σ_k theta_{t,l,k} * log (alpha_{h,l,k} / theta_{t,l,k})
```

This is the **KL(theta || Dirichlet(alpha_h))** averaged over positions.
Bounded in `[0, log K]`, zero when `theta == alpha_h / sum(alpha_h)`,
positive when the endpoint has concentrated on a residue the prior considers
unlikely.

### 3b. Per-position Hamming distance to a held-out reference

```
recon_loss(theta_t, ref_tokens) =
    (1 / L_valid) * Σ_l I[argmax theta_{t,l} != ref_tokens_l]
```

Bounded in `[0, 1]`. This is the canonical "did the model regenerate the
native residue?" metric. The upstream `evaluation/family_validity_hmmer.py`
is the rigorous version (HMMER profile-HMM scan); the categorical distance
is a fast proxy.

### 3c. Which to expose?

**Both.** The composite benchmark (Wave 46 Agent C formula) treats them as
**separate axes**:

* `recon_loss_prior` (KL to family prior) — measures how far the endpoint
  drifted from the family consensus.
* `recon_loss_hamming` (categorical distance to held-out reference) —
  measures how well the endpoint recovered the native sequence.

The first is **self-contained** (no external reference needed); the second
requires the Pfam held-out reference subset that Wave 43 Agent B downloaded.

### 3d. API surface

```python
def observe_reconstruction_loss(
    self,
    trace: ODEIntegratorTrace,
    paper_quantities: Any = None,
    *,
    reference_theta: ArrayF64 | None = None,  # held-out reference (3b)
    prior_alpha: ArrayF64 | None = None,      # family prior (3a)
) -> dict[str, float]:
    """Per-position categorical distance to a reference (held-out or prior).

    Returns:
        {"reconstruction_loss_kl_prior": float,
         "reconstruction_loss_hamming": float}
    """
```

Mirrors `observe_entropy_reduction` and `observe_flow_loss` — same call
shape, same dict-returning pattern, so the composite benchmark aggregator
can key on the metric names.

---

## 4. family validity as continuous

The upstream evaluation computes **`family_validity`** as a **binary**:
"`hmmscan` says this sequence belongs to Pfam family X". The script is at
`data/lineageflow_upstream/evaluation/family_validity_hmmer.py:466`. The
binary nature makes it saturate at 0/1 and gives no gradient to the framework.

### 4a. Continuous analog — classifier log-prob delta

The **right continuous analog** is the **classifier log-prob delta** between
the predicted distribution `p_theta` and the family-prior distribution
`Dirichlet(alpha_h)`:

```
family_log_prob(theta, model) =
    (1 / L_valid) * Σ_l log p_theta(argmax theta_l | theta, t_max)

family_log_prob_baseline(theta, alpha_h) =
    (1 / L_valid) * Σ_l log p_prior(argmax theta_l | alpha_h)
    # = mean over l of log(alpha_h[l, argmax theta_l] / sum_j alpha_h[l, j])

family_log_prob_delta =
    family_log_prob(theta, model) - family_log_prob_baseline(theta, alpha_h)
```

A **positive delta** means the model *agrees with* the residue choices more
strongly than the family prior does; a **negative delta** means the model
*disagrees*. Bounded in `[-log K, log K]`, this is a **continuous,
non-saturating** analog of the binary `family_validity`.

### 4b. Adapter-internal vs upstream-classifier confidence

We already expose two confidence signals:

1. **`LineageFlowClassifierAwareRestart._lineageflow_classifier_confidence_proxy(theta)`**
   — adapter-internal `max(theta, axis=-1)` proxy. Cheap, no torch.
2. **`LineageFlowClassifierAwareRestart._upstream_confidence(cls, theta)`**
   — upstream `LineageFlowClassifier` forward → `softmax(logits).max(-1)`.
   Requires torch + ESM-2 (sidecar venv).

The **continuous family_validity** we want is a **third signal**: the
**log-prob delta** above. It is the natural upgrade of the binary
`family_validity` and **directly consumes** the upstream `LineageFlowClassifier`
that we already sidecar-load for the entropy/confidence metrics.

### 4c. Why not just use the existing confidence proxy?

`max(theta, axis=-1)` (current `_lineageflow_classifier_confidence_proxy`)
**is not the same** as family validity. Confidence in the *argmax* does
not say whether that argmax is the *correct Pfam-family residue*. A
deliberately mutated sequence could be `argmax = 'C'` at every position
with `max = 1.0` and still be a non-Pfam-family-valid sequence.

The **family log-prob delta** explicitly compares against the family
prior `alpha_h`, which is the correct reference distribution for
"is this a valid family X sequence?".

### 4d. API surface

```python
def observe_family_validity(
    self,
    trace: ODEIntegratorTrace,
    paper_quantities: Any = None,
    *,
    prior_alpha: ArrayF64,  # (L, K) family prior, required
) -> dict[str, float]:
    """Continuous family-validity analog of the binary HMMER scan.

    family_log_prob_delta = mean log p_model(argmax theta | theta, t_max)
                           - mean log p_prior(argmax theta | alpha_h)

    Bounded in [-log K, log K]; positive means the model agrees with the
    residue choices more strongly than the family prior.

    Returns:
        {"family_log_prob": float,
         "family_log_prob_baseline": float,
         "family_log_prob_delta": float}
    """
```

The three numbers let the composite benchmark triangulate:

* `family_log_prob` — absolute model belief in current residues.
* `family_log_prob_baseline` — absolute prior belief in current residues.
* `family_log_prob_delta` — the **family-validity gap**.

---

## 5. Concrete glue-layer signatures

These are the **recommended signatures** for the new metric methods to add
to `LineageFlowAdapter`. All three follow the same pattern as the existing
`observe_entropy_reduction` (Wave 45) and `observe_token_indices` (Wave 44).

### 5a. `observe_flow_loss` — per-position classifier NLL

```python
def observe_flow_loss(
    self,
    trace: ODEIntegratorTrace,
    paper_quantities: Any = None,
    *,
    denoiser_temperature: float = 1.0,
    reference_theta: ArrayF64 | None = None,
) -> dict[str, float]:
    """Per-position classifier NLL at the ODE endpoint (or vs reference).

    Args:
        trace: ODEIntegratorTrace from the most recent solve_ode.
        paper_quantities: Optional. Accepted for signature parity.
        denoiser_temperature: Softmax temperature for the classifier posterior.
        reference_theta: If given, compute the NLL of the reference's argmax
            under the *current* classifier posterior (proxy for "did the
            endpoint stay close to the reference?"). If None, compute the
            NLL of the endpoint's own argmax under its own classifier
            posterior (within-trajectory sharpness).

    Returns:
        {"flow_loss": float}  # in [0, log K=20]
    """
```

### 5b. `observe_reconstruction_loss` — per-position categorical distance

```python
def observe_reconstruction_loss(
    self,
    trace: ODEIntegratorTrace,
    paper_quantities: Any = None,
    *,
    reference_theta: ArrayF64 | None = None,  # (L, K) held-out reference
    prior_alpha: ArrayF64 | None = None,      # (L, K) family prior
) -> dict[str, float]:
    """Per-position categorical distance to a reference (held-out or prior).

    Args:
        trace: ODEIntegratorTrace.
        paper_quantities: Optional. Accepted for signature parity.
        reference_theta: Optional (L, K) held-out reference. When given,
            computes Hamming distance to argmax(theta) vs argmax(reference).
        prior_alpha: Optional (L, K) family prior alpha. When given,
            computes KL(theta || alpha_h / sum(alpha_h)).

    Returns:
        {"reconstruction_loss_kl_prior": float,   # in [0, log K]
         "reconstruction_loss_hamming": float}   # in [0, 1]
    """
```

### 5c. `observe_family_validity` — continuous family-validity analog

```python
def observe_family_validity(
    self,
    trace: ODEIntegratorTrace,
    paper_quantities: Any = None,
    *,
    prior_alpha: ArrayF64,                     # (L, K) family prior, required
    denoiser_temperature: float = 1.0,
) -> dict[str, float]:
    """Continuous family-validity analog of the binary HMMER scan.

    Args:
        trace: ODEIntegratorTrace.
        paper_quantities: Optional. Accepted for signature parity.
        prior_alpha: (L, K) family prior, required for the prior reference.
        denoiser_temperature: Softmax temperature for the classifier posterior.

    Returns:
        {"family_log_prob": float,
         "family_log_prob_baseline": float,
         "family_log_prob_delta": float}  # all in [-log K, log K]
    """
```

### 5d. Composite signature

All three new methods follow the existing observe_* contract:

* Input: `(trace, paper_quantities=None, **kwargs)`
* Output: `dict[str, float]` with metric names as keys
* Raise `CapabilityMissingError` if `trace.native_state_digest` is missing
  from `self._native_states` (LRU-evicted)

The composite benchmark aggregator can thus loop:

```python
adapter.observe_flow_loss(trace, paper_quantities)
adapter.observe_reconstruction_loss(trace, paper_quantities, reference_theta=ref, prior_alpha=alpha)
adapter.observe_family_validity(trace, paper_quantities, prior_alpha=alpha)
adapter.observe_entropy_reduction(trace, paper_quantities)  # Wave 45
adapter.observe_token_indices(trace, paper_quantities)      # Wave 44
```

…and aggregate the six metrics into the Wave 46 composite score.

---

## 6. Where the math lines up with upstream

| Composite metric | Upstream analogue | Framework file |
|---|---|---|
| `flow_loss` | `token_dirichlet_mutation`'s `softmax(logits / T)` (inference.py:569) | new `observe_flow_loss` |
| `recon_loss_kl_prior` | `apply_prior_randomization`'s `alpha / alpha.sum(-1)` (inference.py:572) | new `observe_reconstruction_loss` |
| `recon_loss_hamming` | `evaluation/family_validity_hmmer.py` per-seq scan | new `observe_reconstruction_loss` |
| `family_log_prob_delta` | `compute_family_vector_field`'s `p_hat = softmax(logits / T)` (inference.py:341) | new `observe_family_validity` |
| `per_position_entropy_reduction` | (no direct analogue; framework-defined in Wave 45) | existing `observe_entropy_reduction` |
| `amino_acid_categorical` | `observe_token_indices` decodes `argmax(theta)` (adapter line 2024) | existing `observe_token_indices` |

The composite benchmark is therefore **a direct re-purposing of the upstream
math** at the adapter boundary, not a new family of metrics. Each composite
metric has a one-line upstream analogue, which keeps the "framework improves
the model" claim auditable.

---

## 7. Wave 47 → Wave 48 plan

This review doc is **Phase 1** of the composite benchmark integration. The
follow-on phases are:

1. **Wave 47 Agent C/D** — implement `observe_flow_loss`,
   `observe_reconstruction_loss`, `observe_family_validity` on
   `LineageFlowAdapter`. The methods must respect the existing
   `observe_*` contract (Wave 44 + Wave 45 templates).
2. **Wave 47 Agent E** — wire the three new metrics into
   `tools/run_real_ckpt_eval.py` `_compute_metric` (already refactored
   for `adapter + trace` in Wave 44) so the composite benchmark
   aggregator picks them up.
3. **Wave 47 Agent F** — re-run the LineageFlow real-ckpt
   framework-vs-baseline sweep; the composite benchmark now has
   six axes (`flow_loss`, `recon_loss_kl_prior`, `recon_loss_hamming`,
   `family_log_prob_delta`, `per_position_entropy_reduction`,
   `amino_acid_categorical_distance`).

---

## 8. Files reviewed (read-only)

| File | Lines | Role |
|---|---|---|
| `data/lineageflow_upstream/models/model.py` | 1-446 | `LineageFlowClassifier.forward`, ESM-2-650M + flow head |
| `data/lineageflow_upstream/core/vector_field.py` | 1-199 | `c_h(...)` — Dirichlet conditional flow coefficient |
| `data/lineageflow_upstream/core/schedules.py` | 1-32 | Cosine ramp for fitness-weight scheduling |
| `data/lineageflow_upstream/core/hf_cache.py` | 1-61 | Offline HF cache resolver |
| `data/lineageflow_upstream/inference/inference.py` | 1-1215 | `compute_family_vector_field`, `integrate_base_flow`, `generate_with_intervention`, `token_dirichlet_mutation` |
| `data/lineageflow_upstream/dataset/pfam_dataset.py` | 1-368 | `PfamIterableDataset`, `collate_fn`, `AlphaCache` |
| `data/lineageflow_upstream/evaluation/family_validity_hmmer.py` | (existence-only) | The binary upstream `family_validity` HMMER scan |
| `adaptive_reflow/adapters/lineageflow.py` | 1-2303 | Existing `LineageFlowAdapter` + `LineageFlowClassifierAwareRestart` |
| `adaptive_reflow/adapters/_adapter_common.py` | 1-274 | `per_position_entropy_reduction`, `memory_fraction_for` |

---

## 9. Notes / caveats

1. **The upstream `core.sampler.SamplerConfig` is unreachable** — Wave 36
   Agent C's 5-LOC shim is still required for `torch.load` of the
   9.788 GB ckpt. The new metric methods do **not** need the shim because
   they only call `model.forward`, not `SamplerConfig`.
2. **The upstream `compute_family_vector_field` is `@torch.no_grad()`** —
   the new metric methods should also be no-grad (inference only).
3. **`family_log_prob_baseline` uses the prior mean** `alpha_h / sum(alpha_h)`
   as the reference distribution, not the Dirichlet sample. The framework
   `LineageFlowAdapter.apply_restart_distribution` already carries
   `alpha_h` through the conditioning cache, so the prior is accessible
   without an extra import.
4. **No scipy dependency** — all three new methods are stdlib + numpy
   + (optional) torch, matching the existing `observe_*` contract.
5. **The Pfam held-out reference subset** downloaded by Wave 43 Agent B is
   the natural input for `reference_theta` in `observe_reconstruction_loss`
   and `observe_token_indices`. The adapter already exports
   `amino_acid_categorical` via `observe_token_indices` (Wave 44).
6. **The composite benchmark formula** (Wave 46 Agent C) treats these
   three new metrics as **separate axes**, not a single scalar. The
   `family_log_prob_delta` axis is the most directly tied to the
   "binary family_validity saturates" complaint; the `flow_loss` axis
   is the most directly tied to the framework's per-round
   re-inference improvement.

---

**End of Wave 47 Agent B review.**
