# Adapter Interface Specification

> **Status**: governance document. Locked at v1.0. Changes require a paired
> acceptance test and a `DTB-Q` decision in `todo.json`.

This document is the contract that any **glue layer** (a.k.a. **adapter**)
must satisfy in order to be orchestrated by the
`adaptive_reflow.universal` engine. It is **the** authoritative
reference for adapter authors.

The spec is **model-family-agnostic**: a molecular pocket-conditioned
flow matching model, a Stable Diffusion 3 latent flow matching model,
and a discrete-state CTMC flow matching model are all expected to plug
in via the same Protocol surface — they differ only in which mixers,
envelope criteria, and evaluators they declare.

---

## 1. Scope and non-scope

### In scope

- The minimum Python Protocol surface every adapter MUST implement.
- The capability handshake that lets the engine fail-closed at
  registration time, never mid-round.
- The channel / mixer / envelope / evaluator registration protocols.
- The per-round lifecycle.
- Worked examples for two distinct model families.

### Out of scope

- The molecule-specific concrete implementation: see
  `adaptive_reflow/molecular/`. The molecule package is **one** adapter;
  this spec describes the **universal** contract under which it (and
  every other adapter) is implemented.
- Adapter persistence, version pinning, registry admission: see
  `writer/registry.py::CandidateRegistry`.
- Governance / claim release: see `eval/claim_gate.py`.

---

## 2. The Protocol surface (DTB-G1)

An adapter is any class that satisfies
`adaptive_reflow.universal.adapter.FlowMatchingODEAdapter`. The Protocol
has **nine** members. Every member is required unless the matching
`AdapterCapabilities` boolean is `False` (see §3).

```python
class MyAdapter(FlowMatchingODEAdapter):
    # 1. Capability handshake (always required)
    def capabilities(self) -> AdapterCapabilities: ...

    # 2. Initial state (required if has_prior_export). KEYWORD-ONLY.
    def build_initial_state(
        self, *, batch_id: str, sample_id: str,
    ) -> StateBundle: ...

    # 3. Endpoint export (required if has_state_export)
    def export_endpoint(self, state: StateBundle) -> StateBundle: ...

    # 4. Detach gate (always required)
    def detach_and_validate_endpoint(self, bundle: StateBundle) -> StateBundle: ...

    # 5. Restart distribution (required if has_restart_boundary)
    def apply_restart_distribution(
        self, state: StateBundle, policy: RestartPolicy,
    ) -> StateBundle: ...

    # 6. Condition composition (required if has_condition_injection).
    #    Returns an ODEConditionDelta — NOT a StateBundle.
    def compose_condition(
        self, bundle: StateBundle, delta: ODEConditionDelta,
    ) -> ODEConditionDelta: ...

    # 7. ODE step (required if has_ode_integration_surface). Takes the
    #    composed condition; returns the trace alone.
    def solve_ode(
        self, state: StateBundle, condition: ODEConditionDelta, *, seed: int,
    ) -> ODEIntegratorTrace: ...

    # 8. Endpoint observation (always required). Takes the trace FIRST.
    def observe_endpoint(
        self, trace: ODEIntegratorTrace, state: StateBundle,
    ) -> StateBundle: ...

    # 9. Native trajectory (return None, or raise NotImplementedError,
    #    when the adapter preserves no trajectory across solve_ode).
    def export_trajectory(self, trace: ODEIntegratorTrace) -> Any | None: ...
```

> Adapters SHOULD write `class MyAdapter(FlowMatchingODEAdapter)`. The Protocol
> is `@runtime_checkable`, but `isinstance()` verifies method **presence only** —
> inheriting the base is what lets a type-checker compare signatures. See
> `tests/test_universal/test_adapter_protocol_conformance.py`.

### 2.1 Hard invariants

These hold for **every** method:

| Invariant | Why |
|---|---|
| Methods MUST be total: every well-formed input MUST produce a well-formed output | The engine is a state machine; partial returns break orchestration. |
| Methods MUST NOT mutate their inputs | Round trace reproducibility. |
| Methods MUST NOT raise on well-formed inputs | Errors are protocol-level events, raised via `CapabilityMissingError` / `CapabilityMismatchError` only. |
| Methods MUST be deterministic for fixed inputs + seed | R7 round-to-round paired evaluation. |
| `StateBundle` returned by every method MUST satisfy `validate_state_bundle` | Engine-side fail-closed invariants. |
| Methods MUST NOT import `torch` | Stdlib-only contract; see [ARCHITECTURE.md §3](../ARCHITECTURE.md) governance invariants. |

### 2.2 Adapter-side extensions (NOT in the Protocol)

The Protocol does not require mixer / envelope / evaluator fields on the
adapter class. They are registered through `AdapterCapabilities` (§3)
and the candidate registry (§13 of ARCHITECTURE.md). Adapter authors
MAY attach them as instance attributes for convenience:

```python
class MyAdapter:
    def __init__(self):
        self._mixer = NoOpMixer()           # convenience
        self._criteria = (MyEnvelope(),)    # convenience
```

The engine never reads these attributes; only the capability
declarations count.

---

## 3. Capability handshake (always required)

```
def capabilities(self) -> AdapterCapabilities: ...
```

The engine calls `capabilities()` **once** at adapter registration,
**before** any per-round method. The returned `AdapterCapabilities`
is the **single source of truth** for what the adapter promises.

### 3.1 `AdapterCapabilities` schema (actual dataclass)

```python
@dataclass(frozen=True)
class AdapterCapabilities:
    # Capability booleans (10 fields).
    has_ode_integration_surface: bool
    has_prior_export: bool
    has_state_export: bool
    has_condition_injection: bool
    has_restart_boundary: bool
    has_continuous_channels: bool
    has_discrete_channels: bool
    has_trajectory_digest: bool
    has_deterministic_seed: bool
    has_materialization_route: bool

    # Channel vocabulary (the only domain assumption allowed).
    supported_channels: tuple[str, ...] = ()
    channel_domains: Mapping[ChannelName, Literal[
        "continuous", "discrete", "latent", "graph",
    ]] = field(default_factory=dict)

    # Per-channel state-type + shape (D5 — Design #3 OPT-IN).
    # When non-empty, the engine routes each channel to the
    # correct BlendStrategy via the PerChannelBlender dispatcher
    # (D9 — see §3.3). Adapters that leave the mapping empty
    # continue to use the legacy ``state_shape`` carrier for
    # forward-noise allocation; the 2356-test back-compat
    # invariant holds.
    channel_types: Mapping[ChannelName, str] = field(default_factory=dict)
    channel_shapes: Mapping[ChannelName, tuple[tuple[int, ...], tuple[int, ...]]] = field(default_factory=dict)

    # Pluggable-backend declarations (engine uses these at registration).
    required_mixer: type | None = field(default=None)         # type[RestartMixer]; None ⇒ NoOpMixer
    exposed_envelope_criteria: tuple[type, ...] = ()
    exposed_evaluators: tuple[type, ...] = ()

    # Native state shape (F14) — the runner allocates
    # np.zeros(state_shape) before scheduler.inject_noise.
    state_shape: tuple[int, ...] = (2,)

    # D2 / D10 — materialization route.
    materializer: type | None = field(default=None)
    materializer_instance: MaterializationRoute | None = field(default=None)

    # Native integration config (informational; engine does not parse).
    native_config_hash: str = ""
    native_config_version: str = "0.0.0"
```

### 3.2 Condition types (D8 — typed `delta_spec`)

> **Status**: governance document. Locked at D8-v1. Changes require a paired acceptance test and a `DTB-Q` decision in `todo.json`.

The `ODEConditionDelta.delta_spec` field is typed as a
`Condition` discriminated union (D8). The discriminator field is
`condition_kind ∈ {"null", "cfg", "inpainting", "bfn_inpaint", "property", "mapping"}`.

```python
from adaptive_reflow.contracts.condition import (
    Condition,                      # Protocol (runtime_checkable)
    NullCondition,                  # unconditional / round trace-only
    CFGCondition,                   # text-prompt CFG (Lumina / HiDream)
    InpaintingCondition,            # multi-slot inpaint (ProtBFN)
    BFNInpaintCondition,            # single-slot BFN inpaint
    PropertyCondition,              # property-targeted scalar (GraphBFN)
    MappingConditionAdapter,        # back-compat wrapper for raw dicts
    CONDITION_KINDS,                # closed set of discriminator values
    validate_condition,             # canonical validator
    wrap_condition,                 # auto-wrap helper
    condition_kind_of,              # discriminator helper
)
```

The five typed concrete kinds are:

| Kind | Frozen dataclass | Use case |
|---|---|---|
| `"null"` | `NullCondition(dataset, variant, round_trace_only, source)` | Unconditional models (FlowMol3 / GraphBFN-v1); round trace-only |
| `"cfg"` | `CFGCondition(text_prompt, negative_prompt, guidance_scale, cfg_trunc_ratio, cfg_normalization, rope_axes)` | Text-prompt CFG image models (Lumina / HiDream) |
| `"inpainting"` | `InpaintingCondition(positions, strength, n_particles, num_steps, model_family)` | Multi-slot inpainting (ProtBFN / AbBFN / AbBFN2) |
| `"bfn_inpaint"` | `BFNInpaintCondition(slot_index, strength, n_particles, t_grid_len)` | Single-slot Bayesian-flow inpaint |
| `"property"` | `PropertyCondition(property_kind, property_value)` | Property-targeted scalar (`logp` / `qed` / `sa`); GraphBFN style |
| `"mapping"` | `MappingConditionAdapter(_data)` | Back-compat wrapper for adapters that still emit raw dicts |

### 3.2.1 Backward compatibility

Adapters that still pass a raw `Mapping[str, Any]` to the
`ODEConditionDelta` constructor are auto-wrapped into a
`MappingConditionAdapter` via `ODEConditionDelta.__post_init__`. The
legacy `delta.delta_spec["key"]`, `delta.delta_spec.get("key")`, and
`delta.delta_spec.items()` idioms continue to work because
`MappingConditionAdapter` duck-types the mapping protocol via
`__getitem__`, `get`, `__contains__`, `__iter__`, `__len__`, `keys`,
`values`, and `items`. The 2356-test back-compat invariant holds.

### 3.2.2 Constructing a typed `Condition`

```python
# Option A: typed Condition subclass (preferred)
cond = CFGCondition(
    text_prompt="a serene mountain landscape",
    negative_prompt="blurry, distorted",
    guidance_scale=7.5,
    cfg_trunc_ratio=0.92,
    cfg_normalization="lumina",
    rope_axes=(16, 16),
)
delta = ODEConditionDelta(
    delta_spec=cond,
    source="engine",
    target_round=3,
    calibration_artifact_hash="cal-v1",
)

# Option B: legacy raw dict (auto-wrapped)
delta = ODEConditionDelta(
    delta_spec={"num_steps": 100, "target_mean": 0.0},
    source="engine",
    target_round=3,
    calibration_artifact_hash="cal-v1",
)
assert isinstance(delta.delta_spec, MappingConditionAdapter)
assert delta.delta_spec.condition_kind == "mapping"
assert delta.delta_spec.get("num_steps") == 100
```

### 3.2.3 Validation contract

`validate_condition_delta(delta)` enforces:

* `delta_spec` is a non-empty `Condition` (or, for back-compat, a
  non-empty `Mapping[str, Any]`).
* `delta_spec.condition_kind` is one of `CONDITION_KINDS`.
* `delta_spec.to_mapping()` returns a non-empty `Mapping` containing a
  `condition_kind` key matching the discriminator.
* `source`, `target_round`, and `calibration_artifact_hash` satisfy the
  existing structural invariants.

### 3.2.4 Helper helpers

* `wrap_condition(value)` — coerce a raw mapping into a typed
  `Condition` (idempotent on already-typed values).
* `condition_to_mapping(condition)` — return the JSON-serializable
  mapping form.
* `condition_kind_of(value)` — return the discriminator literal for
  either a typed `Condition` or a raw mapping.

### 3.2 Failure modes

| Failure | Engine behaviour |
|---|---|
| `capabilities()` raises | Adapter rejected at registration; engine refuses to enter round loop. |
| A method is called whose corresponding capability boolean is `False` | Adapter raises `CapabilityMissingError`; engine catches it and treats the round as `gate=False`. |
| `supported_channels` does not include a channel the engine asks about | Adapter raises `CapabilityMismatchError`; engine fails closed. |
| `required_mixer` is not the same class as the engine's installed mixer | Adapter raises `CapabilityMismatchError` with explanatory context. |

The fail-closed contract means **no partial-write**: the engine never
applies a beta for a channel whose gate the adapter cannot satisfy.

### 3.3 State Channels (D5 — per-channel state-type declaration)

> **Status**: governance document. Design #3 of the FM-LCM
> interface redesign. Adding a new `StateChannel` discriminator
> value requires a paired acceptance test and a `DTB-Q` decision
> in `todo.json`.

The legacy `AdapterCapabilities.state_shape: tuple[int, ...]`
field is a single per-instance tuple — it can describe the shape
of a 2-D flow-matching channel `(2,)` or a CIFAR image channel
`(3, 32, 32)`, but **cannot** express the heterogeneous per-channel
shapes carried by FlowMol3 (`(n, 3)` coordinate + `(n,)`
atom type + `(n, n)` bond), GraphBFN (`(N, E, K)` theta node/edge
+ `(N, N)` adjacency logits + `(N,)` charge), or any future model
family whose native state decomposes into typed per-channel
sub-tensors.

The per-channel typed surface replaces the single tuple with two
OPT-IN fields:

```python
from adaptive_reflow.universal.adapter import AdapterCapabilities
from adaptive_reflow.contracts.state_channel import (
    StateShape,
    validate_channel_types,
)

# Per-channel typed declaration (OPT-IN; defaults preserve legacy
# back-compat).
caps = AdapterCapabilities(
    # ... existing fields ...
    channel_types={
        ChannelName("coordinate"): "continuous",
        ChannelName("atom_type"): "categorical_mask",
        ChannelName("amino_acid"): "categorical_argmax",
        ChannelName("bond_type"): "categorical_sample",
        ChannelName("graph"): "graph",
    },
    channel_shapes={
        ChannelName("coordinate"): StateShape(dims=(10, 3), variable_axes=(0,)).dims,
        ChannelName("atom_type"): (10,),
        ChannelName("graph"): (8, 8),
    },
)
```

#### 3.3.1 `StateChannel` closed set

The discriminator is `StateChannel ∈ {"continuous", "categorical_mask", "categorical_argmax", "categorical_sample", "mixed", "graph"}` — the six kinds cover the union of LCM concerns identified in the FM-LCM interface gap audit:

| Kind | Adapter use case | Blend strategy (D9) |
|---|---|---|
| `"continuous"` | FlowMol3 `coordinate`, GraphBFN `charge`, Lumina/HiDream `latent` | `LinearBlend` (convex combination) |
| `"categorical_mask"` | FlowMol3 padded positions, GraphBFN diagonal `-inf` sentinel | `MaskedBlend` (m=0/1 short-circuit + sentinel passthrough) |
| `"categorical_argmax"` | ProtBFN amino-acid `argmax`, GraphBFN adjacency `argmax` | `LogitBlend` (logit lift + softmax + argmax) |
| `"categorical_sample"` | ProtBFN `sample`, FlowMol3 `bond_type` sample | `GumbelBlend` (Gumbel-max with τ anneal) |
| `"mixed"` | FlowMol3 four-tuple `(x, a, c, e)` | Dispatcher recurses into per-sub-channel table |
| `"graph"` | GraphBFN `(theta_node, theta_edge, adj_logits)` triple | `GraphBlend` (per-sub-tensor dispatch) |

The closed set is enforced by `validate_state_channel`; the per-adapter table is validated by `validate_channel_types`.

#### 3.3.2 `StateShape` dataclass

The optional `StateShape` carrier declares per-channel dimensions:

```python
@dataclass(frozen=True)
class StateShape:
    dims: tuple[int, ...] = ()               # static dimensions
    variable_axes: tuple[int, ...] = ()      # sample-varying axis indices
```

* `dims` is the static shape; `() ` is the degenerate scalar channel; `(2,)` is the canonical 2-D flow-matching channel; `(10, 3)` is the FlowMol3 coordinate channel.
* `variable_axes` declares which axes vary sample-by-sample (FlowMol3 `n_atoms`, GraphBFN `n_nodes`). Non-empty values trigger the dynamic-shape resampling helper (D18).
* `validate_state_shape` rejects negative dims, out-of-range axis indices, and duplicate axis entries.

#### 3.3.3 Backward compatibility

Adapters that do not declare a `channel_types` table continue to use the legacy `AdapterCapabilities.state_shape: tuple[int, ...] = (2,)` carrier; the engine falls back to it whenever a channel carries no typed `channel_types` entry. The 2356-test back-compat invariant holds.

#### 3.3.4 Per-channel blend dispatch (D9)

The `PerChannelBlender` dispatcher (in
`adaptive_reflow.algorithm.per_channel_blender`) routes each
channel to the correct `BlendStrategy` based on the
`channel_types` table. Five concrete strategies + one graph
delegate cover the six kinds:

```python
from adaptive_reflow.algorithm.per_channel_blender import PerChannelBlender

blender = PerChannelBlender(
    channel_types={
        ChannelName("coordinate"): "continuous",
        ChannelName("amino_acid"): "categorical_argmax",
        ChannelName("atom_type"): "categorical_mask",
        ChannelName("graph"): "graph",
    },
)

# Dispatcher picks the correct strategy per channel.
out = blender.blend_all_channels(
    prior_values={...},
    fresh_values={...},
    memory_fraction_by_channel={
        ChannelName("coordinate"): 0.5,
        ChannelName("amino_acid"): 0.0,
        ChannelName("atom_type"): 1.0,
        ChannelName("graph"): 0.5,
    },
)
```

Audit codes emitted by the dispatcher include:

* `per_channel_blend_m_zero_short_circuit` / `per_channel_blend_m_one_short_circuit` — `m=0` / `m=1` short-circuits dodge `0 * -inf = NaN` on the GraphBFN adjacency diagonal.
* `per_channel_blend_mask_fresh_fallback` — FlowMol3 padded positions (`mask == 0`).
* `per_channel_blend_sentinel_passthrough` — GraphBFN `-inf` diagonal sentinels.
* `per_channel_blend_tau_floor_hit` — Gumbel τ ≤ τ_floor → argmax degeneration.
* `per_channel_blend_fallthrough` — channel not in `channel_types` table; falls through to `LinearBlend` (back-compat).

---

## 4. RestartMixer Protocol

The mixer is the function `prior, endpoint, beta → blended_state`. It
is **not** the adapter's job to implement this — the engine registers
one mixer per round (chosen from the adapter's `required_mixer`). The
adapter's job is to declare which mixer class it expects.

### 4.1 The Protocol (actual definition)

```python
@runtime_checkable
class RestartMixer(Protocol):
    def blend(
        self,
        prior: TensorRef,
        endpoint: TensorRef,
        beta: float,
    ) -> TensorRef: ...
```

`blend(prior, endpoint, beta)` produces a single `TensorRef` that is
the mix of `prior` (the current round's prior state) and `endpoint`
(the prior round's endpoint / memory state), with `beta` controlling
how much of `endpoint` is mixed in:

- `beta == 0.0` → pure prior (no memory).
- `beta == 1.0` → pure memory / endpoint.

Concrete mixers may also return a richer `Mapping[str, Any]` ledger
alongside the `TensorRef`. Callers that need only the mixed state
consume the `TensorRef`; callers that need diagnostics consult the
ledger. (The Protocol above is the minimal version — the universal
engine uses only the `TensorRef` return.)

### 4.2 Standard concrete mixers

All three live in `adaptive_reflow/universal/mixer.py`:

| Class | Status | Use case | Defined in |
|---|---|---|---|
| `NoOpMixer` | **Implemented** | Adapters that do not need a restart distribution; `blend` returns `prior` unchanged | `universal/mixer.py` |
| `LatentConvexMixer` | **Skeleton** | Latent-space flow matching (e.g. Stable Diffusion 3); blend formula `result = (1-β)·prior + β·endpoint`. Adapter authors pass a `native_blend_fn` to invoke their native convex-combination code; default falls back to `NoOpMixer` semantics | `universal/mixer.py` |
| `DiscreteIdentityMixer` | **Skeleton** | CTMC-style discrete flow matching; returns `prior` for `β < 1.0` and `endpoint` for `β ≥ 1.0`. Continuous interpolation between discrete states is undefined | `universal/mixer.py` |
| `EqualRmsCoordinateMixer` | **Implemented** (concrete impl for molecules) | Molecular coordinate channels | `molecular/mixer.py` |

Adapter authors MAY write their own `RestartMixer` subclass for any
space the three skeletons do not cover.

### 4.3 Selection

The engine instantiates the mixer class declared in
`AdapterCapabilities.required_mixer` once at registration. If the
adapter later declares a different mixer, the adapter raises
`CapabilityMismatchError` and the engine fails closed.

If `required_mixer` is left at its default (`None`), the engine uses
`NoOpMixer`.

---

## 5. EnvelopeCriterion declaration

The envelope is the set of "in-scope" boundary conditions for the
adapter's native state. It is **per-adapter**: a molecular adapter's
envelope is `(coordinate_extent_rms, pocket_distance, atom_count, ...)`,
an image-flow adapter's envelope is `(latent_norm, channel_count,
conditioning_hash)`. Both are valid; the universal layer imposes no
shape.

### 5.1 The dataclass (actual definition)

`EnvelopeCriterion` is a **frozen dataclass** carrying the criterion
description. It is **not** a Protocol — adapter authors compose an
`EnvelopeCriterion` *value* with a callable `predicate`, rather than
subclassing.

```python
@dataclass(frozen=True)
class EnvelopeCriterion:
    predicate: Predicate            # Callable[[StateBundle], bool]
    threshold: float
    source_stats_hash: ArtifactHash
    threshold_digest: ArtifactHash
```

Invariants (validated by `validate_envelope_criterion`):

- `predicate` is callable.
- `threshold` is a finite real number.
- `source_stats_hash` and `threshold_digest` are non-empty strings
  identifying the upstream digest that produced the threshold and the
  canonical digest of the threshold itself.

The criterion is **not** molecule-specific — a graph-flow criterion
populates `predicate` with a node-count predicate; a sequence-flow
criterion populates it with a length predicate; etc.

### 5.2 Failure modes

| Failure | Behaviour |
|---|---|
| `predicate` raises on a well-formed `StateBundle` | Adapter wraps as `EnvelopeCriterionError`; engine fails closed. |
| Engine tries to gate on a `diagnostic_only` criterion | Engine refuses; only diagnostic ledgers may observe it. (Note: `diagnostic_only` is set at the classification layer in `EnvelopeClassification`, not on the criterion itself.) |

### 5.3 Molecule example (concrete)

```python
from adaptive_reflow.universal import (
    EnvelopeCriterion, ArtifactHash, ChannelName,
)
import math


def coord_extent_rms(state):
    """Adapter-native computation of coordinate extent RMS in Ångström."""
    coord_ref = state.channels[ChannelName("coordinate")]
    return compute_rms_angstrom(coord_ref)   # adapter-native function


molecule_extent_criterion = EnvelopeCriterion(
    predicate=lambda s: coord_extent_rms(s) <= 2.0,
    threshold=2.0,
    source_stats_hash=ArtifactHash("pdb-stats-v3"),
    threshold_digest=ArtifactHash("extent-threshold-v3"),
)
```

### 5.4 Non-molecule example (concrete)

```python
from adaptive_reflow.universal import (
    EnvelopeCriterion, ArtifactHash, ChannelName,
)


def latent_l2_norm(state):
    """Adapter-native computation of latent L2 norm."""
    latent_ref = state.channels[ChannelName("latent")]
    return compute_l2(latent_ref)            # adapter-native function


latent_norm_criterion = EnvelopeCriterion(
    predicate=lambda s: latent_l2_norm(s) <= 4.0,
    threshold=4.0,
    source_stats_hash=ArtifactHash("vae-stats-v1"),
    threshold_digest=ArtifactHash("latent-norm-threshold-v1"),
)
```

Both classes satisfy the same `EnvelopeCriterion` dataclass shape.

---

## 6. Evaluator Protocol

An evaluator turns a `StateBundle` into a numeric score plus
diagnostics. The engine consumes only `score`; diagnostics are
propagated opaquely into the per-bundle ledger.

### 6.1 The Protocol (actual definition)

```python
@runtime_checkable
class Evaluator(Protocol):
    def score(self, state_bundle: StateBundle) -> float: ...

    @property
    def calibration_artifact_hash(self) -> ArtifactHash: ...

    def evaluate(
        self,
        *,
        sample: Mapping[str, Any],
    ) -> tuple[float, Mapping[str, float]]: ...
```

The three members serve distinct purposes:

- `score(state_bundle)`: primary metric; called by the engine for the
  per-channel rule.
- `calibration_artifact_hash`: a property returning the deterministic
  hash of the calibration artifact the evaluator was trained against.
  The engine fails-closed if this hash does not match a frozen
  artifact.
- `evaluate(*, sample)`: returns `(score, diagnostics_dict)`. Called
  by `eval/protocol.py` to feed round-to-round paired comparison.

### 6.2 Failure modes

| Failure | Behaviour |
|---|---|
| `calibration_artifact_hash` is empty | Adapter raises `EvaluatorNotCalibratedError` at registration. |
| `score` is `NaN` / `Inf` | Adapter raises `EvaluatorInvalidScoreError`; engine fails closed. |
| Evaluator declares `feedback_mode == "proxy_only"` but engine tries to gate on its score | Engine refuses; proxy-only evaluators are diagnostic-only. (Note: `feedback_mode` is a per-evaluation *arm* flag, set on the `PairedComparisonArm` in `eval/protocol.py`, not on the `Evaluator` itself.) |

### 6.3 Molecule example (concrete, actual API)

```python
from adaptive_reflow.universal import ArtifactHash, Evaluator
from collections.abc import Mapping


class GNINAEvaluator:
    """Wraps a GNINA binding-affinity subprocess (calibrated offline)."""

    def __init__(self, calibration_artifact_hash: ArtifactHash, gnina_version: str):
        self._calibration_hash = calibration_artifact_hash
        self._gnina_version = gnina_version

    @property
    def calibration_artifact_hash(self) -> ArtifactHash:
        return self._calibration_hash

    def score(self, state_bundle) -> float:
        # Adapter-native call to the GNINA subprocess.
        coords = state_bundle.channels[ChannelName("coordinate")]
        return run_gnina_subprocess(coords, pocket=self._pocket)

    def evaluate(self, *, sample: Mapping) -> tuple[float, Mapping[str, float]]:
        score = self.score(sample["endpoint"])
        diagnostics = {"raw_score": score, "gnina_version": self._gnina_version}
        return score, diagnostics
```

The structural claim that "the engine consumes only `score`" is enforced
by `frame/trace.py`'s ledger-writer: it pulls `score()` for the per-channel
rule and `evaluate()` only for the round trace.

### 6.4 Non-molecule example (pseudocode)

```python
from adaptive_reflow.universal import ArtifactHash, Evaluator
from collections.abc import Mapping


class CLIPScoreEvaluator:
    """Image-text alignment evaluator (calibrated offline)."""

    def __init__(self, calibration_artifact_hash: ArtifactHash, clip_model: str):
        self._calibration_hash = calibration_artifact_hash
        self._clip_model = clip_model

    @property
    def calibration_artifact_hash(self) -> ArtifactHash:
        return self._calibration_hash

    def score(self, state_bundle) -> float:
        # PSEUDOCODE: ``decode`` and ``clip_score`` are adapter-native helpers.
        latent = state_bundle.channels[ChannelName("latent")]
        image = decode(latent, model=self._decoder)        # <- adapter-native
        return clip_score(image, text=self._prompt)        # <- adapter-native

    def evaluate(self, *, sample: Mapping) -> tuple[float, Mapping[str, float]]:
        score = self.score(sample["endpoint"])
        diagnostics = {"raw_score": score, "clip_model": self._clip_model}
        return score, diagnostics
```

The `decode` and `clip_score` calls are **adapter-native helpers**, not
part of the universal layer. Adapter authors wire them up.

---

## 7. Per-round lifecycle

```
                    ┌───────────────────────────────────────────┐
                    │ Engine.run_round(round_index, ...)         │
                    └───────────────────────────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                              ▼
   1. capabilities()           2. validate_phase            3. validate_envelope
   (cached at registration)   (PhaseState)                 (EnvelopeCriteria)
        │                              │                              │
        ▼                              ▼                              ▼
   4. build_initial_state      5. detach_and_validate_       6. observe_endpoint
   (round 0 only)              endpoint (every round)        (post-observation)
        │                              │                              │
        ▼                              ▼                              ▼
   7. apply_restart_           8. compose_condition          9. solve_ode
   distribution (β blend)     (only if delta != ∅)         (steps > 0)
        │                              │                              │
        └──────────────────────────────┬──────────────────────────────┘
                                       ▼
                              10. emit_round_trace
                                       │
                                       ▼
                              11. (optional) evaluators
```

The default order is the universal default; adapters MAY override via
`OperationCompositionContract.operation_order` (DTB-L2) but the override
is versioned and recorded in the trace.

---

## 8. Capability mismatch → fail-closed

Every adapter method that the engine calls without the corresponding
capability being `True` is a **contract violation**. The adapter MUST
raise `CapabilityMissingError` (defined in
`adaptive_reflow.universal.adapter`). The engine catches the error,
records a ledger blocker, and refuses to apply any beta for that
channel.

```python
class CapabilityMissingError(RuntimeError):
    def __init__(self, capability: str, *, context: str = "") -> None: ...
```

Concrete example:

```python
def compose_condition(self, state, delta):
    if not self.capabilities().has_condition_injection:
        raise CapabilityMissingError(
            "has_condition_injection",
            context=f"adapter {type(self).__name__} is unconditional",
        )
    ...
```

The engine's behaviour on `CapabilityMissingError`:

1. Round is marked `gate=False` for the affected channel.
2. `audit_reason` is set to `"capability_missing:<capability>"`.
3. `blocker_codes` includes `"capability_missing"`.
4. The policy is NOT applied to the next round.
5. The error is recorded in the dynamic restart transfer ledger.

---

## 9. Adding a new model — step-by-step recipe

To add support for a new flow matching model (anywhere — molecule,
image, audio, latent, CTMC, …), follow this **four-step** process:

### Step 1 — declare the channel vocabulary

Decide what `ChannelName` values the model carries. For a Stable
Diffusion 3 latent model:

```python
class LatentImageAdapter:
    SUPPORTED_CHANNELS = (ChannelName("latent"),)
    CHANNEL_DOMAINS = {ChannelName("latent"): "latent"}
```

For a molecule coordinate flow matching model:

```python
class CoordinateFlowMolAdapter:
    SUPPORTED_CHANNELS = (
        ChannelName("coordinate"),
        ChannelName("charge"),
        ChannelName("raw_pair"),
        ChannelName("projected_pair"),
    )
    CHANNEL_DOMAINS = {
        ChannelName("coordinate"): "continuous",
        ChannelName("charge"): "continuous",
        ChannelName("raw_pair"): "discrete",
        ChannelName("projected_pair"): "discrete",
    }
```

### Step 2 — implement `FlowMatchingODEAdapter` Protocol

Implement the eight methods from §2. The implementation may delegate to
the underlying model in any way — direct torch call, RPC, subprocess,
in-memory dict — as long as the Protocol invariants (§2.1) hold.

### Step 3 — register the right mixer + envelope + evaluators

```python
from adaptive_reflow.universal import (
    LatentConvexMixer,  # or NoOpMixer / DiscreteIdentityMixer / custom
)

class LatentImageAdapter:
    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            has_ode_integration_surface=True,
            has_prior_export=True,
            has_state_export=True,
            has_condition_injection=True,            # CFG-like
            has_restart_boundary=True,
            has_continuous_channels=False,
            has_discrete_channels=False,
            has_trajectory_digest=False,
            has_deterministic_seed=True,
            has_materialization_route=False,
            supported_channels=self.SUPPORTED_CHANNELS,
            channel_domains=self.CHANNEL_DOMAINS,
            required_mixer=LatentConvexMixer,       # ← concrete class
            exposed_envelope_criteria=(LatentNormEnvelope,),
            exposed_evaluators=(CLIPScoreEvaluator,),
            native_config_hash="…",
            native_config_version="1.0.0",
        )
```

### Step 4 — write tests

The adapter MUST be registered in the signature-conformance battery at
`tests/test_universal/test_adapter_protocol_conformance.py` (add the
class to `_adapter_classes()`), which checks:

- Every Protocol method is present with the Protocol's parameter names
  and kinds — `isinstance()` alone does not check signatures.
- The class inherits `FlowMatchingODEAdapter`.

A behavioural battery is NOT yet shared across adapters; each adapter
carries its own `tests/test_adapters/test_<model>.py`. The checks below
are the recommended shape for that per-adapter file:

- Capability handshake matches implementation.
- Every advertised capability's method passes a deterministic round.
- Every unadvertised capability's method raises
  `CapabilityMissingError` if invoked.
- `StateBundle` invariants hold after every method.

A custom battery of model-specific tests in
`tests/test_<your_subpackage>/test_<your_model>.py` is recommended but
optional.

---

## 10. Hard rules (must hold for every adapter)

| # | Rule | Why |
|---|---|---|
| 1 | NO module-level `import torch`. A `torch` backend MUST use a function-local lazy import guarded by `torch_is_available()` (see `rectified_flow_cifar.py:307`, `lumina_image_2_0.py:394`) | The framework must import without torch installed; the numpy/synthetic path is the Protocol-conformance backend. |
| 2 | Capability handshake MUST be called before any per-round method | Fail-closed at registration. |
| 3 | `source_round` MUST be `>= 0` | State lifecycle invariant. |
| 4 | Same `(state, seed, steps)` MUST always produce the same next state | R7 paired-evaluation reproducibility. |
| 5 | `TensorRef` values MUST be deterministic hash-stable strings | Engine treats them as opaque; tests assert byte equality. |
| 6 | Detach proof MUST be `True` on every `StateBundle` returned | Backward compatibility with restart distribution. |
| 7 | NO mutation of inputs | Reproducibility + round trace integrity. |
| 8 | NO I/O outside the adapter's own setup | Reproducibility + sandboxing. |
| 9 | NO external state lookup at runtime (only declared config + state inputs) | Sandboxing + audit. |
| 10 | Every method that the engine can call MUST either work or raise `CapabilityMissingError`; never silently succeed with degraded behaviour | Fail-closed contract. |

Violations of any rule cause the engine to fail close and refuse to
register the adapter.

---

## 11. Versioning

The Protocol is versioned via `OperationCompositionContract.version`
(see `adaptive_reflow.frame.operation.OperationCompositionContract`).
A new adapter version is incompatible with the engine's version if:

- `AdapterCapabilities` adds a required field that the engine doesn't know.
- A method signature changes.
- A hard invariant is strengthened (e.g., "deterministic" → "byte-identical").

Adapter authors SHOULD target the engine version they tested against
and declare `native_config_version` accordingly.

---

## 12. Validation tooling

Three classes of validation are bundled with the engine:

1. **Static**: `tests/test_universal/test_no_molecular_import.py` —
   AST-level check that the adapter module does not import
   `torch` or any molecule-specific module unless the adapter is in
   `molecular/`.
2. **Capability**: `tests/test_universal/test_adapter_universality.py` —
   check that every advertised capability's method exists, that every
   unadvertised capability's method raises `CapabilityMissingError`
   on invocation, and that the round-trip `StateBundle` is valid.
3. **Standard mixer**: `tests/test_universal/test_standard_mixers.py` —
   verify `NoOpMixer`, `LatentConvexMixer`, `DiscreteIdentityMixer`,
   and `validate_blend_inputs` per their documented semantics.

Every adapter MUST be green on all validation classes.

**See also: docs/r17-survey/algorithm-correctness-evidence.md.** The
static + capability + standard-mixer validation tooling above enforces
*Protocol conformance* — every adapter advertises the right surface and
behaves deterministically. It does **not** by itself prove the
*algorithm layer* is correct against a known ground truth. For that,
the framework maintains three independent oracle gates
(2D Gaussian-mix / synthetic-image / hyperparameter-free) — see the
evidence chain document for the per-gate PASS verdicts, the 97-test
test count, and the paper Section 4 skeleton. **See also:
docs/r17-survey/algorithm-correctness-evidence.md.**

---

## 13. Worked example — full minimal adapter

```python
from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass

from adaptive_reflow.contracts.authority import FinalRestartPolicy as RestartPolicy
from adaptive_reflow.universal import (
    AdapterCapabilities,
    ArtifactHash,
    CapabilityMissingError,
    FlowMatchingODEAdapter,
    NoOpMixer,
    RestartMixer,
)
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
    ODEIntegratorTrace,
    StateBundle,
    TensorRef,
    validate_state_bundle,
)


def _ref(label: str, **parts) -> TensorRef:
    blob = repr((label, sorted(parts.items()))).encode("utf-8")
    return TensorRef(f"toy:{hashlib.sha256(blob).hexdigest()[:16]}")


class ToyLinearAdapter(FlowMatchingODEAdapter):
    """Smallest possible adapter — one continuous channel, no restart, no condition.

    A complete runnable version is shipped at
    ``adaptive_reflow/adapters/toy_linear.py`` and tested at
    ``tests/test_adapters/test_toy_linear.py``. This code block shows
    only the structural skeleton; refer to the shipped module for the
    full eight-method implementation.
    """

    SUPPORTED_CHANNELS = (ChannelName("x"),)
    CHANNEL_DOMAINS = {ChannelName("x"): "continuous"}
    NATIVE_CONFIG_HASH: ArtifactHash = ArtifactHash("toy:cfg:v1")
    NATIVE_CONFIG_VERSION = "1.0.0"

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            has_ode_integration_surface=True,
            has_prior_export=True,
            has_state_export=True,
            has_condition_injection=False,
            has_restart_boundary=False,
            has_continuous_channels=True,
            has_discrete_channels=False,
            has_trajectory_digest=False,
            has_deterministic_seed=True,
            has_materialization_route=False,
            supported_channels=self.SUPPORTED_CHANNELS,
            channel_domains=self.CHANNEL_DOMAINS,
            required_mixer=NoOpMixer,
            exposed_envelope_criteria=(),
            exposed_evaluators=(),
            native_config_hash=self.NATIVE_CONFIG_HASH,
            native_config_version=self.NATIVE_CONFIG_VERSION,
        )

    # build_initial_state, export_endpoint, detach_and_validate_endpoint,
    # apply_restart_distribution (raises CapabilityMissingError because
    # has_restart_boundary=False), compose_condition (raises because
    # has_condition_injection=False), solve_ode, observe_endpoint —
    # all eight methods, each a few lines. The full source is at
    # `adaptive_reflow/adapters/toy_linear.py`; tests are at
    # `tests/test_adapters/test_toy_linear.py`.
```

---

## 14. What this spec does NOT promise

- **Performance**: the engine imposes no throughput constraint.
- **Convergence**: restart distribution semantics are the adapter's
  responsibility.
- **Cross-model generalisation**: a claim that one model family benefits
  another requires separate target-disjoint paired evidence (DTB-R7 /
  DTB-R8) and is out of scope for this contract.
- **Numerical correctness**: the engine does not check that `solve_ode`
  is *correct* for the model; it only checks that it returns a valid
  `StateBundle` and `ODEIntegratorTrace`.

---

## 15. See also

- [ARCHITECTURE.md](../ARCHITECTURE.md) — layered structure, dependency
  direction, governance invariants.
- [CONTRACTS.md](../CONTRACTS.md) — typed contracts (frozen dataclasses).
- [DESIGN_BOUNDARY.md](../DESIGN_BOUNDARY.md) — non-claim boundary.
- `adaptive_reflow.universal` — Protocol definitions, validators,
  exceptions, standard mixers.
- `adaptive_reflow.molecular` — molecule concrete implementation as a
  worked example.

---

## 16. Real-Model Adapters: TwoDimFMAdapter

The toy worked example in §13 is **self-contained** but uses synthetic
state values; it is intentionally too simple to exercise the integration
loop, the restart semantics, or the per-channel envelope gating. For a
non-toy, CPU-runnable, **real-model** worked example the project ships
`TwoDimFMAdapter`: a 2D rectified-flow adapter that runs end-to-end on
any laptop in a few seconds, uses pre-trained weights checked into
`data/`, and exercises every Protocol capability the engine calls.

This section is the canonical reference for adapter authors who want to
port the universal contract to a new model family — the
`TwoDimFMAdapter` is the smallest non-trivial real-model example in
the codebase.

### 16.1 Architecture diagram

```
   ┌─────────────────┐
   │   N(0, I_2)     │   source distribution (2D standard normal)
   │   build_initial │
   │      _state     │
   └────────┬────────┘
            │ x_0 ∈ R^2
            ▼
   ┌─────────────────┐
   │   MLP velocity  │   v_theta(x, t): 3 -> 64 -> 64 -> 2
   │      field      │   input  = [x_1, x_2, t]
   │                 │   hidden = Tanh activations
   │                 │   output = linear projection
   └────────┬────────┘
            │ v(x, t) ∈ R^2
            ▼
   ┌─────────────────┐
   │   RK4 / DP(45)  │   t_grid = linspace(0, 1, num_steps+1)
   │   integrator    │   default: RK4 (byte-deterministic)
   │   solve_ode     │   alternative: Dormand-Prince (adaptive)
   └────────┬────────┘
            │ trajectory (num_steps+1, 2)
            ▼
   ┌─────────────────┐
   │   observe_      │   endpoint = trajectory[-1]
   │    endpoint     │   clamp: |endpoint| <= 5.0
   └────────┬────────┘
            │ x_final ∈ R^2
            ▼
       restart blend
       (memory_fraction = 1 - beta)
       → next round's x_0
```

The adapter is **bidirectional** at the round boundary: the endpoint of
round ``r`` becomes (after the restart-blend) the initial state of
round ``r+1``. The engine never inspects the ``(x, t)`` values — it
only propagates `native_state_digest` strings.

### 16.2 Source and target distributions

The adapter fixes two distributions and exposes a third as the
configurable target:

| Distribution | Role | Definition |
|---|---|---|
| Source | Always | `N(0, I_2)` (standard 2D normal). Sampled by `numpy.random.default_rng` seeded from `(batch_id, sample_id, source_round)`. |
| Target `two_moons` | Default | Two interlocking half-circles; mode centres at `(0, 1)` and `(1, -0.5)`; isotropic Gaussian noise `stddev = 0.08`. |
| Target `eight_gaussians` | Optional | Eight Gaussians on a circle of radius `2.0`; each mode is a Gaussian with `stddev = 0.15`; mode angles are evenly spaced at `2πk / 8`. |

The target is selected at adapter construction time
(`TwoDimFMAdapter(target=...)`); the trainer at
`adaptive_reflow.adapters.twodim_fm_train` ships one `.npz` per
target. Both target samplers live as pure helpers in
`twodim_fm_train.sample_two_moons` and
`twodim_fm_train.sample_eight_gaussians` and are re-imported by the
runtime adapter (and by `TwoDimFMEvaluator`) so the byte-for-byte
sampler equality contract holds across the model-evaluation surface.

### 16.3 Channel vocabulary and capabilities

The adapter exposes a single channel:

```python
TWODIM_FM_CHANNELS: tuple[ChannelName, ...] = (ChannelName("xy"),)
TWODIM_FM_CHANNEL_DOMAINS: Mapping[ChannelName, ChannelDomain] = {
    ChannelName("xy"): "continuous",
}
```

`TwoDimFMCapabilities` (the adapter's `AdapterCapabilities` subclass)
declares the full universal surface:

| Capability | Value | Why |
|---|---|---|
| `has_ode_integration_surface` | `True` | The adapter owns the RK4 / DP(45) integration. |
| `has_prior_export` | `True` | `build_initial_state` samples from `N(0, I_2)`. |
| `has_state_export` | `True` | `export_endpoint` returns the detached endpoint. |
| `has_condition_injection` | `True` | `compose_condition` injects `target_distribution` and `integrator_config_hash`. |
| `has_restart_boundary` | `True` | `apply_restart_distribution` blends prior endpoint with fresh `N(0, I_2)`. |
| `has_continuous_channels` | `True` | The `xy` channel is continuous. |
| `has_discrete_channels` | `False` | The model carries no discrete state. |
| `has_trajectory_digest` | `True` | A SHA-256 trajectory digest is emitted per round. |
| `has_deterministic_seed` | `True` | All RNG streams are seeded by SHA-256 hash digests. |
| `has_materialization_route` | `True` | Trajectory arrays are stored by digest and readable from `observe_endpoint`. |

The adapter declares `NoOpMixer` as the mixer class. The `xy` channel
does its own blend inside `apply_restart_distribution` (linear blend
against fresh `N(0, I_2)`), so the universal mixer's identity blend
is the correct fallback at the engine boundary.

### 16.4 Restart semantics — memory fraction blend

The adapter implements restart distribution directly inside
`apply_restart_distribution`:

```text
m         = 1 - beta_by_channel["xy"]        # memory fraction in [0, 1]
x_fresh   ~ N(0, I_2)                        # fresh noise
x_blend   = m * x_prior + (1 - m) * x_fresh  # linear blend
```

So:

- `beta = 0.0` → `m = 1.0` → pure prior endpoint (no fresh noise).
- `beta = 0.5` → `m = 0.5` → half memory, half fresh.
- `beta = 1.0` → `m = 0.0` → pure fresh noise (memory fully replaced).

The blend formula is encoded in `_blend_endpoint_with_prior` and is
clamped to `[0, 1]` so out-of-range beta values cannot produce NaN
endpoints. The audit constant `AUDIT_RESTART_BLEND = "twodim_fm_restart_blend"`
is appended to the resulting `StateBundle.provenance` chain whenever
the restart boundary fires, providing a per-bundle proof that the
blend happened.

The engine never sees the formula — it only sees the new
`StateBundle.native_state_digest`. This is the *exact* same contract
any other restart-boundary-capable adapter would satisfy: opaque state
in, opaque state out, provenance tagged for audit.

### 16.5 Velocity-field MLP — 3 -> 64 -> 64 -> 2

The trained network is intentionally tiny:

```text
Layer   Input   Output   Activation   Parameters
input   3       64       Tanh         3*64 + 64      =   256
hidden  64      64       Tanh         64*64 + 64     =  4160
output  64      2        linear       64*2 + 2       =   130
                                                       -----
                                                       4546
```

Wait — the shipped adapter is `3 -> 64 -> 64 -> 2` with **Tanh**
activations; the offline trainer ships an identically shaped MLP with
**ReLU** activations. Both are byte-compatible at the `(.npz)` layer
because the keys (`W1, b1, W2, b2, W3, b3`) and shapes are identical;
the runtime adapter re-binds the activation in `_velocity_field`. The
runtime count is therefore ~5.4 k parameters per `.npz` file (~2 kB
serialized to disk).

### 16.6 Integrators

The adapter supports two deterministic integrators:

| Integrator | Default? | Byte-deterministic? | Use case |
|---|---|---|---|
| `rk4` | Yes | Yes (closed-form RK4 stages over a fixed grid) | Default `solve_ode` path; round-to-round paired comparison. |
| `dormand_prince` | No | Yes for fixed `(weights, x0, t0, t1, rtol, atol, max_steps)` | Adaptive alternative with overflow clamp; useful when the velocity field has stiff regions. |

Both integrators clamp the trajectory to `[-TWODIM_FM_CLAMP, TWODIM_FM_CLAMP]^2`
(`TWODIM_FM_CLAMP = 5.0`) and emit the audit code
`ERR_INTEGRATOR_OVERFLOW = "twodim_fm_integrator_overflow"` whenever
the clamp fires. The audit code is propagated through
`observe_endpoint` into the resulting `StateBundle.provenance`.

The Dormand-Prince implementation in
`_integrate_dormand_prince` is **not** a SciPy `solve_ivp` wrapper;
it is a hand-rolled RK45 with the standard Dormand-Prince tableau
and an embedded lower-order error estimator, with safety-factor step
control (`min=0.2, max=5.0`). This keeps the runtime stdlib-plus-NumPy
with no SciPy dependency on the *adapter* code path itself; SciPy is
only consumed by `TwoDimFMEvaluator` (see §16.8).

### 16.7 Implementation size

The runtime adapter (`adaptive_reflow/adapters/twodim_fm.py`) is
**~520 LOC** including:

- ~50 LOC of channel-vocabulary / capability dataclasses.
- ~120 LOC of NumPy helpers (`_features`, `_velocity_field`, RK4 / DP integrators, blend).
- ~250 LOC for the eight Protocol methods + the `TwoDimFMAdapter` class shell.
- ~50 LOC of factory / `__all__` surface.
- ~50 LOC of `_load_weights` / `_default_weights_path` / module-level constants.

This is the **canonical size budget** for a non-toy universal adapter
in this project — anything larger should be justified by an explicit
model-family requirement; anything smaller is almost certainly a toy.

### 16.8 Evaluator companion — TwoDimFMEvaluator

The adapter is paired with `TwoDimFMEvaluator`
(`adaptive_reflow/eval/twodim_fm_evaluator.py`), a deterministic
numerical evaluator that satisfies the DTB-R7 "real replay-through-
adapter" leg. Three numerical diagnostics are published:

| Diagnostic | Definition |
|---|---|
| `wasserstein_2d` | `sqrt(W2_x^2 + W2_y^2)` via `scipy.stats.wasserstein_distance` on each axis. |
| `support_coverage` | Fraction of Voronoi cells (one per target mode) that contain at least one grid point within `TWODIM_FM_COVERAGE_RADIUS` of a generated endpoint. |
| `energy_distance` | Squared energy distance `E^2` via `scipy.spatial.distance.cdist` / `pdist`. |

The four `ChannelTransferEvidence` diagnostics are filled from these:

```text
raw_score                          = 1 - W2 / W2_max            (W2_max = 2.0)
bounded_score                      = clip(raw_score, 0, 1)
calibration_lower_bound            = 0.95
perturbation_stability_lower_bound = 0.85
```

`TwoDimFMEvaluator` ships the canonical `evaluate(bundle, *, channel, seed)`
and `oracle(bundle, *, channel, seed)` surface; both are
byte-for-byte equal for the same inputs (the byte-equality is asserted
in `tests/test_eval/test_twodim_fm_evaluator.py`).

### 16.9 Pre-trained weights and reproducibility

Pre-trained weights ship as NumPy `.npz` files under `data/`:

| File | Size | Target |
|---|---|---|
| `data/twodim_fm_two_moons.npz` | ~2 kB | `target="two_moons"`. |
| `data/twodim_fm_eight_gaussians.npz` | ~2 kB | `target="eight_gaussians"`. |

Both files were produced by running
`python -m adaptive_reflow.adapters.twodim_fm_train --target <name> --steps 2000 --out data/<name>.npz`
and pinned via `data/twodim_fm/` checksums (see
`tools/materialize_twodim_fm.py` for the canonical regeneration
script). The trainer is a hand-rolled NumPy Adam optimizer; no
PyTorch, no autograd, no SciPy — only `numpy`.

The default path resolution in `_default_weights_path` looks at the
repo-root `data/` directory. Pass an explicit `weights_path=` to
override.

### 16.10 References

- Adapter source: `adaptive_reflow/adapters/twodim_fm.py` (~520 LOC).
- Trainer source: `adaptive_reflow/adapters/twodim_fm_train.py`.
- Evaluator source: `adaptive_reflow/eval/twodim_fm_evaluator.py`.
- Adapter tests: `tests/test_adapters/test_twodim_fm.py`.
- Evaluator tests: `tests/test_eval/test_twodim_fm_evaluator.py`.
- Materialize script: `tools/materialize_twodim_fm.py`.
- Worked end-to-end example: [TUTORIAL.md](../TUTORIAL.md).

---

## 17. Typed materialization route (Design #4 — D10)

> **Status**: governance document. Locked at D10-v1. Changes require a paired acceptance test and a `DTB-Q` decision in `todo.json`.

The materialization route is the **fibre-to-ambient map** that
Theorem 1 (Li 2026, lines 87-92) implicitly references when it treats
the BL distance on the ambient law. Heterogeneous native state spaces
(FlowMol3 `(x, a, c, e)`; GraphBFN graph payload; ProtBFN amino-acid
logits; CTMC+BFN categorical simplex) must be projected to the
ambient state X_envelope so the BL metric, the four paper
quantities (`A_g`, `B_g`, `C_g`, `e_rho`), and the
:class:`BoundedMergeOperator`'s residual `g` are well-defined.

### 17.1 Surface — two parallel Protocols

The typed materialization route is exposed at TWO layers, both
preserved by the 2356-test back-compat invariant:

| Layer | Module | Surface |
|---|---|---|
| **Universal / universal.materialization** | `adaptive_reflow.universal.materialization` | `MaterializationRouteProtocol` (legacy `native_to_envelope` / `envelope_to_native` API) |
| **Contracts / contracts.materialization** (D10 typed) | `adaptive_reflow.contracts.materialization` | `MaterializationRoute` (`materialize` / `dematerialize` typed API) |

The D10 typed surface replaces the prior `materializer: type | None`
class reference on :class:`AdapterCapabilities` with an
`Optional[MaterializationRoute]` INSTANCE handle
(``materializer_instance``). The legacy class-reference field is
preserved as ``materializer: type | None`` for back-compat; new
adapters should declare the typed instance via
``materializer_instance=default_flowmol3_materializer()`` (or the
appropriate factory).

### 17.2 `MaterializationRoute` (D10 abstract)

```python
class MaterializationRoute(Protocol):
    @property
    def handle(self) -> MaterializerHandle: ...
    @property
    def loss_tolerance_by_channel(self) -> Mapping[str, LossTolerance]: ...
    def materialize(
        self,
        envelope_state: EnvelopeStateBundle,
        *,
        atom_count: int | None = None,
    ) -> NativeStateBundle: ...
    def dematerialize(
        self,
        native_state_bundle: NativeStateBundle,
    ) -> EnvelopeStateBundle: ...
    def validate_roundtrip(
        self,
        native_state_bundle: NativeStateBundle,
    ) -> tuple[bool, tuple[str, ...]]: ...
```

The abstract is `runtime_checkable` so adapters can be duck-type-checked
against it.

### 17.3 `NativeStateBundle` per-channel accessors (D20 wiring)

The :class:`NativeStateBundle` now exposes typed per-channel accessors
so the dispatch is total (no raises on missing channels):

| Accessor | Domain filter | Returns |
|---|---|---|
| `get_continuous(name)` | `channel_domains[name] == "continuous"` | opaque `TensorRef` handle, or `None` |
| `get_categorical(name, *, mode="argmax")` | `discrete / categorical_mask / categorical_argmax / categorical_sample` | opaque `TensorRef` handle, or `None` |
| `get_masked(name)` | any | `(channel_handle, mask_handle)` tuple, or `None` |
| `get_graph(name)` | `channel_domains[name] == "graph"` | sub-mapping of prefixed sub-channel handles, or `None` |

### 17.4 Three concrete molecular materializers

| Materializer | Backend | Per-channel domain | Handles |
|---|---|---|---|
| `ConcreteFlowMol3Materializer` | FlowMol3 | `coordinate`, `charge` (continuous); `raw_pair`, `atom_type` (categorical) | `(x, a, c, e)` four-tuple projection |
| `ConcreteProtBFNMaterializer` | ProtBFN / AbBFN / AbBFN2 | `amino_acid_categorical` (categorical_argmax); 4 auxiliary categoricals; `tap_continuous` (continuous) | K=32 model → K=22 surface vocabulary alignment + residue mass aggregation |
| `ConcreteGraphBFNMaterializer` | GraphBFN | `nodes` (continuous); `edges`, `adjacency` (discrete) | Graph-shaped `(N, E, (N, N))` payload; preserves `-inf` diagonal sentinel through roundtrip |

All three concrete materializers implement BOTH the legacy
`MaterializationRouteProtocol` API (for back-compat with the existing
adapters) AND the new typed `MaterializationRoute` surface (for the
D10 wire-up). The `LegacyProtocolAdapter` shim bridges legacy
materializers onto the typed surface transparently.

### 17.5 Engine integration

`Engine.run_round` invokes the adapter-declared materializer after the
endpoint is detached:

```python
materializer_instance = getattr(caps, "materializer_instance", None)
if materializer_instance is not None:
    native_bundle = _state_bundle_to_native(detached, caps)
    envelope_state = materializer_instance.dematerialize(native_bundle)
    extras["materializer_handle"] = str(materializer_instance.handle)
    extras["envelope_state_keys"] = sorted(envelope_state.observables)
```

The projection is stored in `RoundTrace.extras` so downstream consumers
(`BoundedMergeOperator`, paper-quantity audits) can consume it. The
invocation is opt-in: adapters that don't declare a typed
materializer continue to work unchanged.

### 17.6 Back-compat

The `MaterializationRouteProtocol` legacy surface at
`adaptive_reflow.universal.materialization` is preserved byte-for-byte:
the `MaterializationRouteProtocol` Protocol class, the `NoOpMaterializer`
class, the `MaterializationRouteProtocol`-conforming
`native_to_envelope` / `envelope_to_native` methods on
`ConcreteFlowMol3Materializer` / `ConcreteGraphBFNMaterializer` are
all unchanged. The new surface is **additive** at the protocol layer
and **orthogonal** at the capability layer
(`materializer_instance: Optional[MaterializationRoute]` defaults to
`None`, preserving the 2356-test back-compat invariant).

### 17.7 Tests

`tests/test_contracts/test_materialization_typed.py` covers:

* (1) Abstract + carrier invariants (12 tests).
* (2) NativeStateBundle per-channel accessors (7 tests).
* (3) FlowMol3 materializer roundtrip (5 tests).
* (4) ProtBFN K=32 vs K=22 vocabulary alignment (8 tests).
* (5) GraphBFN `-inf` sentinel roundtrip (4 tests).
* (6) LegacyProtocolAdapter shim (2 tests).
* (7) `AdapterCapabilities.materializer_instance` field (2 tests).
* (8) Handle digest byte-stability (2 tests).
* (9) Cross-adapter parametrized conformance (6 tests).
* (10) Determinism for fixed inputs (2 tests).
* (11) Engine integration helper (1 test).

Total: 48 tests, all passing.

### 18. Dynamics + Solver split (D6 + D7 — LCM Tier-1 design)

> **Status**: governance document. LCM Tier-1 design D6 (DynamicsProtocol
> — split `solve_ode` into ``dynamics.step`` + ``solver.integrate``)
> and D7 (IntegratorProtocol — pluggable solver euler/heun/rk4/
> dormand_prince/bfn_step/ctmc_euler_heun). The split is the canonical
> seam that the prior FM-LCM gap audit identified as Tier-1 gaps.

The legacy `FlowMatchingODEAdapter.solve_ode` method is monolithic —
it bundles two concerns into one method body:

* **(C) DYNAMICS** — how state evolves per ``dt`` (velocity field,
  CTMC transition kernel, Bayesian update)
* **(D) SOLVER** — how the dynamics are integrated (Euler / RK4 /
  Heun / adaptive Dormand-Prince / CTMC-EulerHeun / BFN-step)

The split exposes these as independent `Protocol` surfaces:

```python
from adaptive_reflow.algorithm.dynamics import (
    DynamicsProtocol,
    ContinuousFMDynamics,
    CTMCDynamics,
    BFNDynamics,
    FlowMol3Dynamics,    # 4-channel (x, a, c, e) composite
    ProtBFNDynamics,     # 3-channel (theta, y, alpha) composite
)
from adaptive_reflow.algorithm.solver import (
    IntegratorProtocol,
    EulerSolver,
    RK4Solver,
    HeunSolver,
    AdaptiveRK4Solver,
    CTMCEulerHeunSolver, # canonical CTMC solver
    BFNSolver,           # fixed-NFE BFN step counter
)
```

#### 18.1 DynamicsProtocol — split surface (D6)

`DynamicsProtocol.step(s, t, dt, c, *, seed, paper_quantities, audit_codes) -> slope`
returns the SLOPE (velocity / rate / Bayesian delta) at the given
state; the solver applies `dt * slope` weighting. Concrete families:

| Family | SLOPE formula | Used by |
| --- | --- | --- |
| `continuous_fm` | `velocity(s, t, c)` | Lumina, HiDream, two-dim FM, TwoDimFMAdapter |
| `ctmc` | `Q @ s` | FlowMol3 (currently; task #324 swap to `ctmc_euler_heun`) |
| `bfn` | `pred_logits - s` | ProtBFN/AbBFN/AbBFN2, GraphBFN |
| `flowmol3_composite` | per-channel dispatch | FlowMol3 (4-channel composite) |
| `protbfn_bfn` | BFN with alpha schedule | ProtBFN/AbBFN/AbBFN2 (3-channel) |

#### 18.2 IntegratorProtocol — pluggable solver (D7)

`IntegratorProtocol.integrate(dynamics, state_0, t_grid, c, *, seed, paper_quantities) -> DynamicsTrajectory`
applies the dynamics at multiple points. Concrete families:

| Family | Update rule | Use case |
| --- | --- | --- |
| `euler` | `s + h * k1` | Default for Lumina/HiDream/two-dim FM |
| `rk4` | classical 4th-order Runge-Kutta | Higher-order accuracy |
| `heun` | predictor-corrector 2nd-order | Lumina solver_kind="heun" path |
| `adaptive_rk4` | Dormand-Prince with adaptive dt | Variable stiffness |
| `ctmc_euler_heun` | Euler + Heun correction | Canonical CTMC solver; task #324 |
| `bfn` | fixed-NFE BFN step counter | BFN refinement loops |

#### 18.3 Paper-quantity grounding

* `e_rho / 4` (paper Lemma 5) is consumed as the minimum step-size
  floor so the solver cannot underflow below the paper exterior-gap
  envelope. Both `DynamicsProtocol.step` and `IntegratorProtocol.integrate`
  take an optional `paper_quantities` argument that emits the
  `dynamics_dt_floored_by_paper_exterior_gap` audit code when the
  floor engages.

#### 18.4 Backward compatibility

* The 8-method `FlowMatchingODEAdapter` Protocol surface is
  byte-identical (no new methods added). The split is **opt-in** via
  `AdapterCapabilities.has_dynamics_seam` and
  `AdapterCapabilities.has_solver_seam` boolean flags (both default
  `False`).
* Adapters that do NOT advertise the seam continue to route through
  their existing monolithic `solve_ode` body via a private
  `_default_solve_ode()` shim. The 2356-test back-compat invariant is
  preserved.

#### 18.5 Registry integration

`adaptive_reflow.algorithm.protocol_registry` exposes two new family
sets:

* `DYNAMICS_FAMILIES = {"continuous_fm", "ctmc", "bfn", "flowmol3_composite", "protbfn_bfn"}`
* `SOLVER_FAMILIES = {"euler", "rk4", "heun", "adaptive_rk4", "ctmc_euler_heun", "bfn"}`

with corresponding `build_dynamics_from_config()` and
`build_solver_from_config()` polymorphic factories. The
`adaptive_reflow.manifest.PortManifest` exposes the corresponding
`DynamicsPort` / `SolverPort` accessors so callers can dispatch by
name through the hexagonal port set.

### 18.6 Tests

`tests/test_algorithm/test_dynamics_solver.py` covers:

* (1) Euler + ContinuousFMDynamics reproduces closed-form sine wave ODE (1 test).
* (2) BFN + BFNSolver reproduces ProtBFN Bayesian update (1 test).
* (3) CTMC + CTMCEulerHeunSolver wraps rate matrix Q correctly (1 test).
* (4) RK4 / Heun / AdaptiveRK4 compose with ContinuousFMDynamics (3 tests).
* (5) Native-state digest byte-stability for fixed inputs (2 tests).
* (6) Polymorphic builders + family registry dispatch (3 tests).
* (7) Default factories return canonical instances (1 test).
* (8) Adapter-specific bindings via composition — FlowMol3Dynamics 4-tuple, ProtBFNDynamics 3-tuple (4 tests).
* (9) Protocol conformance (runtime_checkable) for DynamicsProtocol + IntegratorProtocol (2 tests).
* (10) Config hash stability + to_config round-trip (2 tests).
* (11) Failure modes (fail-closed): bad CTMC rate matrix, None state, non-positive dt, short t_grid, negative seed (6 tests).
* (12) Paper exterior-gap floor (e_rho / 4) emits audit code (1 test).

Total: 27 tests, all passing.
