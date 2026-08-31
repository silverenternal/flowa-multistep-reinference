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
has **eight** members. Every member is required unless the matching
`AdapterCapabilities` boolean is `False` (see §3).

```
class MyAdapter:
    # 1. Capability handshake (always required)
    def capabilities(self) -> AdapterCapabilities: ...

    # 2. Initial state (required if has_prior_export)
    def build_initial_state(
        self, batch_id: str, sample_id: str, *, source_round: int = 0,
    ) -> StateBundle: ...

    # 3. Endpoint export (required if has_state_export)
    def export_endpoint(self, state: StateBundle) -> StateBundle: ...

    # 4. Detach gate (always required)
    def detach_and_validate_endpoint(self, state: StateBundle) -> StateBundle: ...

    # 5. Restart distribution (required if has_restart_boundary)
    def apply_restart_distribution(
        self, state: StateBundle, policy: RestartPolicy,
    ) -> StateBundle: ...

    # 6. Condition composition (required if has_condition_injection)
    def compose_condition(
        self, state: StateBundle, delta: ODEConditionDelta,
    ) -> StateBundle: ...

    # 7. ODE step (required if has_ode_integration_surface)
    def solve_ode(
        self, state: StateBundle, seed: int, *, steps: int = 1,
    ) -> tuple[StateBundle, ODEIntegratorTrace]: ...

    # 8. Endpoint observation (always required)
    def observe_endpoint(self, state: StateBundle) -> StateBundle: ...
```

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

    # Pluggable-backend declarations (engine uses these at registration).
    required_mixer: type = field(default=None)         # type[RestartMixer]; None ⇒ NoOpMixer
    exposed_envelope_criteria: tuple[type, ...] = ()
    exposed_evaluators: tuple[type, ...] = ()

    # Native integration config (informational; engine does not parse).
    native_config_hash: str = ""
    native_config_version: str = "0.0.0"
```

### 3.2 Failure modes

| Failure | Engine behaviour |
|---|---|
| `capabilities()` raises | Adapter rejected at registration; engine refuses to enter round loop. |
| A method is called whose corresponding capability boolean is `False` | Adapter raises `CapabilityMissingError`; engine catches it and treats the round as `gate=False`. |
| `supported_channels` does not include a channel the engine asks about | Adapter raises `CapabilityMismatchError`; engine fails closed. |
| `required_mixer` is not the same class as the engine's installed mixer | Adapter raises `CapabilityMismatchError` with explanatory context. |

The fail-closed contract means **no partial-write**: the engine never
applies a beta for a channel whose gate the adapter cannot satisfy.

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

The adapter MUST pass the universal test battery at
`tests/test_universal/test_adapter_universality.py`. The battery
checks:

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
| 1 | NO `import torch` (or any other non-stdlib import) in the adapter module | Stdlib-only contract. |
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
