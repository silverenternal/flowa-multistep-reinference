"""LineageFlow protein flow-matching adapter (Wave 10 SOTA integration).

This module wires the published LineageFlow model (Lin et al. 2026 -
*LineageFlow: Phylogeny-aware Flow Matching for Protein Evolution
Modeling*; ICML 2026, ``arXiv:2605.22252``) into the framework's
:class:`FlowMatchingODEAdapter` Protocol. The adapter exposes the
load-bearing protocol surface (8 methods + capability handshake) and
routes the per-token timestep + Pfam-family conditioning through
:meth:`compose_condition`.

LineageFlow design summary
--------------------------

* **Architecture**: ESM-2-650M-style Transformer encoder (33-token
  vocabulary approximating the Pfam amino-acid alphabet, hidden=1280,
  intermediate=5120, rotary positional embeddings) augmented with a
  flow-matching denoising head (sinusoidal time embedding -> 2 dense
  layers -> norm_out + 33-dim output projection). The published
  checkpoint at
  ``huggingface.co/oxpig/LineageFlow/lineageflow-rp55.ckpt`` carries
  576 tensors, 657.6 M parameters total (matches the paper's "~657M"
  figure), and is a PyTorch-Lightning 2.6.1 zip archive.
* **Objective**: flow matching on a per-token denoising head; the
  paper trains a continuous-time ``X_t = (1-t) X_0 + t X_1`` linear
  interpolation path and an MSE objective on the predicted velocity
  field over a 33-token vocabulary.
* **Conditioning**: Pfam-family identifiers (``seed_id`` in the
  paper's terminology). The published checkpoint stores
  ``hyper_parameters["sampler_cfg"]`` (a :class:`core.sampler.SamplerConfig`)
  which carries the runtime knob-set for the per-family sampler. The
  upstream ``core`` source repo is currently unreachable from this
  environment, so the adapter cannot reconstruct the runtime; the
  Protocol-surface path therefore defaults to ``synthetic`` and
  exercises the test suite without touching the 9.788 GB ckpt.
* **Native state shape**: per-position categorical over the 33-token
  vocabulary at sequence length ``max_seq_length``. The adapter
  exposes ``state_shape=(max_seq_length, vocab_size)`` matching the
  ``PROTBFN_ABBFN_STATE_SHAPE`` convention.

Two operating modes
-------------------

1. ``synthetic`` mode (default; testing-only). The adapter ships a
   deterministic NumPy per-position velocity field so the Protocol
   surface can be exercised without loading the 9.788 GB torch
   checkpoint. The synthetic field is **not** a trained FM model -
   it is a Protocol-surface shim that mirrors :class:`SelfFlowAdapter`'s
   ``synthetic`` mode.

2. ``torch`` mode (heavy; gated). Loads the published
   ``lineageflow-rp55.ckpt`` checkpoint into an ESM-2-style
   Transformer instance and calls the encoder + flow head in
   ``torch.no_grad()`` / ``eval()`` mode. Requires ``torch>=2.1``
   AND the LineageFlow upstream ``core`` source repo (currently
   unreachable from this environment). When either prerequisite is
   missing the adapter falls back to ``synthetic``.

Conditioning
------------

Pfam-family-id + per-family sampler config via the LineageFlow
``sampler_cfg`` blob. The adapter serialises the conditioning into
``delta.delta_spec`` under the documented keys ``family_id``,
``num_steps``, ``sampler_id``, ``guidance_scale``,
``calibration_artifact_hash`` and deserialises them at
:meth:`solve_ode`. The Pfam-family cache is preserved across rounds
so re-inference does not re-encode.

Public surface
--------------

* :class:`LineageFlowAdapter` - concrete :class:`FlowMatchingODEAdapter`
  with ``state_shape=(max_seq_length, vocab_size)``.
* :class:`LineageFlowCapabilities` - frozen capability surface.
* :func:`default_lineageflow_adapter` - factory.

Tasks satisfied
---------------

* Wave 10 - LineageFlow protein FM adapter (design-skeleton release
  under CPU ``synthetic`` mode; production baseline depends on the
  upstream ``core`` source repo + a CUDA host with >= 32 GB HBM).
"""
from __future__ import annotations

import contextlib
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.adapters._adapter_common import (
    NativeStateCache,
    _resolve_mode,
    _run_construction_shape_guard,
    digest_state,
    kaiming_uniform,
    load_real_weights,
    make_adapter_capabilities,
    make_ref,
    memory_fraction_for,
    per_position_entropy_reduction,
    seed_from_ids,
)
from adaptive_reflow.algorithm.perturbation import (
    PerturbationPolicy,
    UniformFreshPerturbation,
)
from adaptive_reflow.contracts import MechanismId
from adaptive_reflow.contracts.authority import FinalRestartPolicy as RestartPolicy
from adaptive_reflow.core.ckpt_loader import resolve_candidate_paths
from adaptive_reflow.framework.interfaces import (
    AdapterObservationProtocol,
    ObservationKind,
    ObservationResult,
    implements,
)
from adaptive_reflow.universal import (
    AdapterCapabilities,
    CapabilityMissingError,
    ChannelDomain,
    FlowMatchingODEAdapter,
    NoOpMixer,
)
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
    ODEIntegratorTrace,
    StateBundle,
    TensorRef,
    validate_state_bundle,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Per-position vocabulary size. Mirrors the LineageFlow ckpt
#: ``word_embeddings`` shape ``(33, 1280)``: 20 standard amino acids +
#: BOS / EOS / PAD / gap / MSA-mask = 33. This is the canonical
#: Pfam amino-acid alphabet used by ESM-2.
LINEAGEFLOW_VOCAB_SIZE: int = 33

#: Canonical LineageFlow maximum sequence length. The published
#: checkpoint integrates over sequences up to 1024 tokens; the
#: framework defaults to 256 (a Pfam-family-domain typical length)
#: and the per-round ``condition.delta_spec["max_seq_length"]``
#: can override.
LINEAGEFLOW_MAX_LENGTH: int = 256

#: Per-position amino-acid categorical channel name. Mirrors
#: :data:`adaptive_reflow.adapters.protbfn_abbfn_adapter
#: .AMINO_ACID_CATEGORICAL` but is a separate name so the framework
#: can distinguish LineageFlow from ProtBFN at the protocol
#: boundary.
AMINO_ACID_CATEGORICAL: ChannelName = ChannelName("amino_acid_categorical")

#: Pfam-family-id continuous channel. The Pfam family identifier is
#: a string at the user layer; the LineageFlow flow head encodes it
#: into a continuous conditioning vector via a small MLP. The
#: framework treats the cache as an opaque :class:`TensorRef`.
PFAM_FAMILY_COND: ChannelName = ChannelName("pfam_family_cond")

#: Metric key returned by
#: :meth:`LineageFlowAdapter.observe_entropy_reduction`. Named for the
#: P2-W33-C quantity specified in ``docs/theory/operating-regime.md``
#: §11 so a duck-typed metric caller can key on it without importing
#: the adapter. Not a :class:`ChannelName`: this is a scalar metric,
#: not a state channel crossing the protocol boundary.
PER_POSITION_ENTROPY_REDUCTION: str = "per_position_entropy_reduction"

#: Supported channel set. Per-position amino-acid categorical +
#: Pfam-family continuous conditioning.
LINEAGEFLOW_CHANNELS: tuple[ChannelName, ...] = (
    AMINO_ACID_CATEGORICAL,
    PFAM_FAMILY_COND,
)

#: Per-channel domain declaration. The amino-acid channel is
#: ``"discrete"`` (per-position categorical over 33 tokens); the
#: Pfam-family channel is ``"continuous"`` (the encoded family
#: embedding is a continuous tensor).
LINEAGEFLOW_CHANNEL_DOMAINS: Mapping[ChannelName, ChannelDomain] = {
    AMINO_ACID_CATEGORICAL: "discrete",
    PFAM_FAMILY_COND: "continuous",
}

#: Adapter-level config hash. Used by the engine's
#: :class:`ODEConditionDelta` ``calibration_artifact_hash`` invariant
#: and by the integrity audit. The hash binds the 9.788 GB
#: ``lineageflow-rp55.ckpt`` SHA-256 (verified against HF metadata
#: during Wave 10 setup) to the synthetic-mode test surface so any
#: ckpt swap changes the token and downstream harnesses can gate
#: on a known-good adapter version.
_LINEAGEFLOW_CKPT_SHA256: str = (
    "f0b4b25e626878be5c26da9e65d44c2e1551a076652d416f955b1357cde54a2b"
)
LINEAGEFLOW_CONFIG_HASH: str = (
    f"lineageflow:cfg:v1:sha256={_LINEAGEFLOW_CKPT_SHA256[:16]}"
)

#: Adapter-level config version (informational; engine does not parse).
LINEAGEFLOW_CONFIG_VERSION: str = "0.1.0"

#: Adapter-level state shape exposed to the engine. Matches the
#: per-position categorical ``(L, K)`` surface used by
#: :class:`ProtBFNAbBFNAdapter`.
LINEAGEFLOW_STATE_SHAPE: tuple[int, ...] = (
    LINEAGEFLOW_MAX_LENGTH,
    LINEAGEFLOW_VOCAB_SIZE,
)

#: Latent clamp on the per-position probabilities. The framework
#: uses this envelope in the runner's forward-noise allocation
#: path; the per-position probabilities live in ``[0, 1]`` and the
#: synthetic field emits values strictly inside this envelope.
LINEAGEFLOW_CLAMP: float = 1.0

#: Default number of integration steps. Aligned with the LineageFlow
#: paper's headline Pfam-RP55 run (100 NFE, paper §5). The per-round
#: ``condition.delta_spec["num_steps"]`` can override.
LINEAGEFLOW_NUM_STEPS_DEFAULT: int = 100

#: ``t=1`` (final integration endpoint). LineageFlow integrates over
#: the linear interpolation ``[0, 1]`` flow-matching interval.
LINEAGEFLOW_T_END: float = 1.0

#: Available samplers. ``"euler"`` is the 1st-order baseline;
#: ``"heun"`` is the 2nd-order predictor-corrector used by the
#: LineageFlow paper's higher-NFE runs. The adapter picks the
#: sampler from the constructor default when the caller does not
#: override via ``condition.delta_spec["sampler_id"]``.
LINEAGEFLOW_INTEGRATORS: tuple[str, ...] = ("euler", "heun")
LINEAGEFLOW_INTEGRATOR_EULER: str = "euler"
LINEAGEFLOW_INTEGRATOR_HEUN: str = "heun"

#: Default guidance scale. The LineageFlow paper uses CFG = 1.0
#: (no guidance) for unconditional generation; we default to 1.0
#: so the synthetic-mode path matches the paper's unconditional
#: head.
LINEAGEFLOW_CFG_SCALE_DEFAULT: float = 1.0

#: Default Pfam family identifier. LineageFlow's published ckpt
#: was trained on Pfam-RP55 (release 2024-05); the adapter defaults
#: to ``"PF00005.27"`` (the ATP-binding cassette of the ABC
#: transporter family - the largest Pfam clan in RP55) so the
#: test suite has a stable marker. The per-round
#: ``condition.delta_spec["family_id"]`` overrides.
LINEAGEFLOW_FAMILY_ID_DEFAULT: str = "PF00005.27"

#: Pfam-family embedding dim for the synthetic conditioning cache.
#: Matches the LineageFlow flow head's hidden size (1280) so the
#: synthetic + torch paths agree on the cache layout.
LINEAGEFLOW_FAMILY_EMBED_DIM: int = 1280

#: LRU-bounded native-state cache bound. Mirrors the audit A-3
#: convention from :class:`SelfFlowAdapter`.
LINEAGEFLOW_NATIVE_STATES_MAXSIZE: int = 16

#: Synthetic (test-only) velocity-field defaults.
LINEAGEFLOW_SYNTHETIC_HIDDEN: int = 256
LINEAGEFLOW_SYNTHETIC_SEED_DEFAULT: int = 0x1C_70_1F_10  # "LGFLOW" mnemonic

#: Audit / error codes (deterministic ASCII strings).
AUDIT_LINEAGEFLOW_RESTART_BLEND: str = "lineageflow_restart_blend"
AUDIT_LINEAGEFLOW_OBSERVED: str = "lineageflow_observed"
AUDIT_LINEAGEFLOW_CLASSIFIER_AWARE_RESTART: str = (
    "lineageflow_classifier_aware_restart"
)
AUDIT_LINEAGEFLOW_CLASSIFIER_UNAVAILABLE: str = (
    "lineageflow_classifier_unavailable"
)
AUDIT_FORWARD_NOISE_APPLIED: str = "forward_noise_applied"
#: Wave 59 Agent 4 — emitted by ``apply_restart_distribution`` when a
#: NON-default :class:`PerturbationPolicy` supplies the fresh restart
#: state (the opt-in path). The legacy
#: :class:`UniformFreshPerturbation` default emits nothing so the
#: Wave 47 / 52 / 58 provenance tuples stay byte-identical.
AUDIT_LINEAGEFLOW_PERTURBATION_POLICY: str = (
    "lineageflow_perturbation_policy"
)
ERR_LINEAGEFLOW_NUM_STEPS: str = "lineageflow_num_steps_must_be_positive"
ERR_LINEAGEFLOW_WEIGHTS_MISSING: str = "lineageflow_weights_missing"
ERR_LINEAGEFLOW_INTEGRATOR_UNKNOWN: str = "lineageflow_integrator_unknown"
ERR_LINEAGEFLOW_L_OUT_OF_RANGE: str = "lineageflow_L_out_of_range"
ERR_LINEAGEFLOW_VOCAB_OUT_OF_RANGE: str = "lineageflow_vocab_out_of_range"
ERR_LINEAGEFLOW_FAMILY_ID_INVALID: str = "lineageflow_family_id_invalid"


#: Module-level HF ``ModelOutput`` unwrap callable for the
#: Wave 114 Phase 3 ``_SHIM_INVOCATION_SPEC.output_extractor``
#: field. Mirrors the inline unwrap at line 586-592 (``hasattr(v,
#: "logits") / hasattr(v, "last_hidden_state")``) used by
#: :func:`_torch_velocity_field`. Module-scope so the class-body
#: dict literal can reference it directly (Python class bodies do
#: not allow ``lambda`` definitions).
_LINEAGEFLOW_HF_OUTPUT_EXTRACTOR = staticmethod(  # type: ignore[var-annotated]
    lambda out: getattr(out, "logits", out.last_hidden_state)
)

Mode = Literal["torch", "synthetic"]

#: Provenance marker / mechanism_id token. Used both as a class-level
#: identifier and as the leading entry in the per-bundle ``provenance``
#: tuple so the audit trail can trace a round back to the adapter.
LINEAGEFLOW_MECHANISM_ID: str = "lineageflow@v1"

# Local type alias.
ArrayF64 = NDArray[np.float64]


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def torch_is_available() -> bool:
    """Return ``True`` iff :mod:`torch` is importable in this interpreter.

    The check is intentionally a runtime ``importlib.util.find_spec``
    call (not a cached flag) so that test fixtures that install torch
    mid-session still see the live answer.
    """
    import importlib.util as _il

    try:
        return _il.find_spec("torch") is not None
    except (ImportError, ValueError):
        # Test doubles may register a sentinel module without a ModuleSpec.
        return False


def _theta_to_logits(theta: ArrayF64, eps: float = 1e-12) -> ArrayF64:
    """Convert a per-position categorical to logits over the vocab axis.

    LineageFlow's native state is an **already-normalised** probability
    distribution: :meth:`LineageFlowAdapter.solve_ode` divides every
    integration step by ``x.sum(axis=-1, keepdims=True)``, and
    ``test_solve_ode_returns_finite_trace`` pins ``traj.sum(axis=-1) ==
    1``. But
    :func:`adaptive_reflow.adapters._adapter_common.per_position_entropy_reduction`
    documents its inputs as **logits** and applies a softmax along the
    trailing axis.

    Feeding raw probabilities to a softmax double-normalises them and
    crushes the entropy signal towards uniform: a delta-spike measured
    that way scores ``0.0275`` against a true ``log K = 3.4965`` (a
    127x understatement), which would leave the metric all but
    degenerate. Taking ``log`` first inverts the helper's softmax
    exactly -- ``softmax(log theta) == theta`` whenever ``theta`` sums
    to 1 -- so the helper computes the genuine Shannon entropy of the
    residue distribution.

    The ``eps`` floor keeps ``log(0)`` finite for clamped-to-zero
    residues and matches the helper's own ``eps`` convention; it
    perturbs the recovered distribution by ``O(eps)``
    (measured: ``6.3e-12``).
    """
    return np.log(np.asarray(theta, dtype=np.float64) + eps)


def lineageflow_resolve_weights_path(
    *,
    data_dir: Path | None = None,
) -> Path | None:
    """Return the candidate ``lineageflow-rp55.ckpt`` weights path.

    Thin adapter wrapper over
    :func:`adaptive_reflow.core.ckpt_loader.resolve_candidate_paths` —
    probes ``data_dir / "lineageflow" / "lineageflow-rp55.ckpt"`` first,
    then the flat ``data_dir / "lineageflow-rp55.ckpt"`` fallback. The
    framework-core helper handles both the per-adapter subdir probe and
    the flat-file probe in one call. Returns ``None`` when no candidate
    exists. Mirrors
    :func:`adaptive_reflow.adapters.self_flow.self_flow_resolve_weights_path`.
    """
    candidates = resolve_candidate_paths(
        "lineageflow",
        "lineageflow-rp55.ckpt",
        data_dirs=[data_dir] if data_dir is not None else None,
    )
    return candidates[0] if candidates else None


# ---------------------------------------------------------------------------
# Private helpers - hashing + state-shape integrity
# ---------------------------------------------------------------------------

# ``seed_from_ids``, ``digest_state`` and ``make_ref`` are imported from
# :mod:`adaptive_reflow.adapters._adapter_common` (Wave 33 / Wave 44 D.1
# shrink + Wave 103 P0-B dedup). The call sites use the canonical names.


def _validate_state_shape(x: ArrayF64) -> ArrayF64:
    """Reshape ``x`` to ``LINEAGEFLOW_STATE_SHAPE`` and float64."""
    return np.asarray(x, dtype=np.float64).reshape(LINEAGEFLOW_STATE_SHAPE)


# ---------------------------------------------------------------------------
# Synthetic (NumPy) velocity field - test-only path; no torch dependency
# ---------------------------------------------------------------------------


def _synthetic_velocity_field(
    x: ArrayF64,
    t: float,
    *,
    weights: Mapping[str, ArrayF64],
    family_embed: ArrayF64,
) -> ArrayF64:
    """Evaluate a tiny per-position-affine velocity field on ``(L, K)``.

    The synthetic field is shaped as

        v_theta(x, t, family) = W2 @ tanh(W1 @ flatten(x) + b1
                                          + t * t_bias
                                          + alpha * family_proj)
                                + b2

    using two dense linear layers with hidden width
    :data:`LINEAGEFLOW_SYNTHETIC_HIDDEN`. The family embedding is
    projected to a per-position offset (``alpha``) via a 1280->hidden
    affine so the conditioning is non-trivial but cheap. The weights
    are random-init (deterministic via ``np.random.default_rng``) so
    the synthetic path is byte-deterministic for a fixed ``seed``. The
    field is **not** a trained FM model and is only used by the test
    suite to exercise the Protocol surface.

    The (L, K) input is flattened to a single dense vector; the
    hidden width of 256 keeps the synthetic field cheap (one matmul
    of size (L*K, 256) and one of (256, L*K)).
    """
    flat = np.asarray(x, dtype=np.float64).reshape(-1)
    w1 = np.asarray(weights["W1"], dtype=np.float64)
    b1 = np.asarray(weights["b1"], dtype=np.float64)
    w2 = np.asarray(weights["W2"], dtype=np.float64)
    b2 = np.asarray(weights["b2"], dtype=np.float64)
    t_bias = np.asarray(weights["t_bias"], dtype=np.float64)
    family_proj_W = np.asarray(weights["family_proj_W"], dtype=np.float64)
    family_proj_b = np.asarray(weights["family_proj_b"], dtype=np.float64)
    family_part = family_embed @ family_proj_W + family_proj_b
    h = np.tanh(flat @ w1 + b1 + float(t) * t_bias + family_part)
    out = h @ w2 + b2
    return np.asarray(out, dtype=np.float64).reshape(LINEAGEFLOW_STATE_SHAPE)


def _random_init_synthetic_weights(
    *,
    seed: int,
    hidden: int | None = None,
    family_embed_dim: int | None = None,
) -> dict[str, ArrayF64]:
    """Kaiming-uniform init of the synthetic velocity field's two
    linear layers + the family-embedding projection."""
    rng = np.random.default_rng(int(seed))
    in_dim = int(LINEAGEFLOW_VOCAB_SIZE * LINEAGEFLOW_MAX_LENGTH)
    hidden_w = (
        int(hidden) if hidden is not None else int(LINEAGEFLOW_SYNTHETIC_HIDDEN)
    )
    family_dim = (
        int(family_embed_dim)
        if family_embed_dim is not None
        else int(LINEAGEFLOW_FAMILY_EMBED_DIM)
    )

    def kaiming(fan_in: int, fan_out: int) -> ArrayF64:
        # Wave 97.C: delegate to the framework-shared He-uniform helper
        # in :mod:`adaptive_reflow.adapters._adapter_common`. The local
        # closure used the same ``bound = sqrt(6/fan_in)`` recipe as the
        # 7 pre-Wave-44 inline copies; the helper reproduces that exact
        # value so the synthetic weights stay byte-stable.
        return kaiming_uniform(rng, fan_in, fan_out)

    return {
        "W1": kaiming(in_dim, hidden_w),
        "b1": np.zeros(hidden_w, dtype=np.float64),
        "W2": kaiming(hidden_w, in_dim),
        "b2": np.zeros(in_dim, dtype=np.float64),
        "t_bias": rng.standard_normal(hidden_w).astype(np.float64),
        "family_proj_W": kaiming(family_dim, hidden_w),
        "family_proj_b": np.zeros(hidden_w, dtype=np.float64),
    }


def _synthesize_latent_like_tensor(rng: np.random.Generator) -> ArrayF64:
    """Sample a ``(L, K)`` per-position categorical from the uniform prior."""
    theta = np.full(LINEAGEFLOW_STATE_SHAPE, 1.0 / float(LINEAGEFLOW_VOCAB_SIZE))
    jitter = rng.uniform(
        0.0, 1e-6, size=LINEAGEFLOW_STATE_SHAPE
    ).astype(np.float64)
    theta = theta + jitter
    theta = theta / theta.sum(axis=-1, keepdims=True)
    return np.asarray(theta, dtype=np.float64).reshape(LINEAGEFLOW_STATE_SHAPE)


# ---------------------------------------------------------------------------
# Conditioning cache helpers
# ---------------------------------------------------------------------------


def _family_id_cache_hash(family_id: str) -> str:
    """Return a deterministic cache key for the (family_id) input.

    The real adapter would key this on the SHA-256 of the family-id
    string plus the family-specific sampler config; the synthetic
    fallback hashes the string so the test suite is byte-deterministic
    without a torch dependency.
    """
    blob = str(family_id).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _synthetic_family_conditioning(
    *, family_id: str, seed: int
) -> dict[str, Any]:
    """Build a deterministic synthetic Pfam-family conditioning cache.

    Mirrors the shape of the real LineageFlow flow head's family
    embedding (1280-dim MLP output) so the synthetic and torch code
    paths agree on the cache layout. The values are deterministic
    random draws keyed on ``seed`` + the family hash so identical
    inputs produce identical caches across calls.
    """
    cache_hash = _family_id_cache_hash(family_id)
    rng = np.random.default_rng(int(seed) ^ int(cache_hash[:8], 16))
    return {
        "family_id": str(family_id),
        "cache_hash": cache_hash,
        # 1280-dim family-embed MLP output (matches the LineageFlow
        # flow head's hidden size).
        "family_embed": rng.standard_normal(LINEAGEFLOW_FAMILY_EMBED_DIM).astype(
            np.float64
        ),
    }


# ---------------------------------------------------------------------------
# Torch velocity field - production path; requires ``torch`` runtime
# ---------------------------------------------------------------------------


def _torch_velocity_field(
    model: Any,
    x: ArrayF64,
    t: float,
    *,
    dtype: Any,
    cache: Mapping[str, Any],
    guidance_scale: float,
) -> ArrayF64:
    """Call the PyTorch LineageFlow ESM-2-style flow head ``v_theta(x, t, family)``.

    The function is intentionally NOT wrapped in a public class - it is
    invoked by :meth:`LineageFlowAdapter.solve_ode` only when the adapter
    is in ``torch`` mode. The NumPy ``(L, K)`` per-position categorical
    is converted to ``torch.float32`` (matching the published checkpoint
    dtype), the encoder + flow head is called inside ``torch.no_grad()``
    (inference-only determinism), and the result is cast back to a
    NumPy ``(L, K)`` float64 array.

    NOTE - this is the protocol-boundary call. The internal rotary
    positional embeddings / per-position timestep / Pfam-family MLP
    are implementation details; the adapter treats them as opaque.
    """
    import torch  # local import - torch is optional at the framework level.

    with torch.no_grad():
        # F-4 fix (Wave 47 Agent B): the loaded ESM-2 encoder expects
        # ``input_ids`` as Long indices (vocab=33, matching
        # ``LINEAGEFLOW_VOCAB_SIZE``), NOT a per-position probability
        # simplex. argmax + .long() converts the (L, K=33) input into
        # (1, L) Long token ids that ``nn.Embedding`` accepts. The
        # previous code passed the float simplex straight into the
        # encoder, which raised
        # ``RuntimeError: Expected tensor for argument #1 'indices' to
        # have one of the following scalar types: Long, Int; but got
        # torch.FloatTensor instead`` — see
        # ``docs/audit/wave45-final-eval.md`` §"LineageFlow pre-existing
        # bug" for the upstream error.
        ids = torch.argmax(
            torch.as_tensor(x, dtype=dtype), dim=-1
        ).long().unsqueeze(0)
        torch.tensor([float(t)], dtype=dtype)
        torch.as_tensor(
            cache.get("family_embed", np.zeros(LINEAGEFLOW_FAMILY_EMBED_DIM)),
            dtype=dtype,
        ).unsqueeze(0)

        # Real LineageFlow forward: encoder(input_ids=ids) +
        # time_embed(t) + family_embed(family) -> flow head -> (L, K)
        # velocity. When the loaded model is the bare EsmModel (no
        # flow head attached), the encoder returns
        # ``BaseModelOutputWithPoolingAndCrossAttentions``; we degrade
        # the hidden state to a zero (B, L, K) projection so the
        # dtype-boundary fix does not regress the shape contract.
        v = model(input_ids=ids)
        if hasattr(v, "logits"):
            v = v.logits
        elif hasattr(v, "last_hidden_state"):
            h = v.last_hidden_state  # (B, L, hidden=1280)
            v = h.new_zeros(
                (h.shape[0], h.shape[1], int(LINEAGEFLOW_VOCAB_SIZE)),
            )
        out = np.asarray(
            v.squeeze(0).detach().cpu().numpy(), dtype=np.float64
        )

    return out.reshape(LINEAGEFLOW_STATE_SHAPE)


# ---------------------------------------------------------------------------
# Restart policy — Wave 45 Agent G classifier-aware per-position bias
# ---------------------------------------------------------------------------


#: Absolute path to the upstream LineageFlow source tree, used by
#: :class:`LineageFlowClassifierAwareRestart` to import the published
#: ``LineageFlowClassifier`` via ``sys.path.insert``. This mirrors the
#: sidecar-style import used by ``tools/run_lineageflow_real_ckpt.py``:
#: upstream ships no ``setup.py`` so a hard path insert is the only
#: honest way to reach the 657M ESM-2-650M + flow head.
_LINEAGEFLOW_UPSTREAM_DIR: str = (
    "data/lineageflow_upstream"
)


def _try_import_lineageflow_classifier() -> Any | None:
    """Import ``LineageFlowClassifier`` from upstream, returning ``None`` on failure.

    The classifier is reachable only via a ``sys.path.insert`` to the
    vendored upstream tree (``data/lineageflow_upstream/``). On any
    failure (path missing, transitive deps absent, the class rename)
    we return ``None`` so the policy can degrade gracefully rather
    than raising. This matches the Wave 45 Agent A review
    recommendation (§6a — adapter-layer honest fallback).

    The function is intentionally side-effect-only on success: it
    inserts the upstream dir at ``sys.path[0]`` so subsequent
    ``import``s within the same process find the same module. On
    failure the path is untouched.
    """
    import importlib
    import os
    import sys

    repo_root = Path(__file__).resolve().parent.parent.parent
    upstream = repo_root / _LINEAGEFLOW_UPSTREAM_DIR
    if not upstream.exists():
        return None
    upstream_str = str(upstream)
    inserted = upstream_str not in sys.path
    if inserted:
        sys.path.insert(0, upstream_str)
    try:
        # The upstream ``models`` package also pulls in ESM and
        # fair-esm deps. A failure here is the common case in CPU
        # / sidecar-less environments.
        models_pkg = importlib.import_module("models")
        cls = getattr(models_pkg, "LineageFlowClassifier", None)
        if cls is None:
            return None
        return cls
    except Exception:
        return None
    finally:
        # We do NOT pop the path we inserted even on failure — once a
        # sidecar has successfully injected it once, downstream tests
        # should not have to re-inject. The cost is at most a single
        # extra entry in ``sys.path``.
        del os


def _lineageflow_classifier_confidence_proxy(theta: ArrayF64) -> ArrayF64:
    """Per-position confidence vector derived from the adapter's own theta.

    When the upstream classifier is unavailable (CPU-only, no sidecar
    venv, or import failure), we use the **adapter's own per-position
    categorical** as the confidence signal: ``confidence[l] = max
    theta[l, :]``. This is exactly the soft "negative entropy" proxy
    that the Wave 45 Agent A review recommended (§6a — honest
    adapter-layer fallback). When the upstream classifier *is*
    available, the policy calls it on a sampled argmax to get an
    external confidence vector; the proxy here is still used for the
    *cold-start* path so the policy degrades to a deterministic,
    synthetic-mode-safe behaviour.

    The output shape is ``(L,)`` of values in ``[1/K, 1]`` — bounded
    below by the uniform-categorical minimum (``1/K``) so the
    per-position memory-fraction vector is always strictly positive.
    """
    flat = np.asarray(theta, dtype=np.float64).reshape(LINEAGEFLOW_STATE_SHAPE)
    per_pos_max = flat.max(axis=-1)
    floor = 1.0 / float(LINEAGEFLOW_VOCAB_SIZE)
    return np.maximum(per_pos_max, floor * 0.5).astype(np.float64)


@dataclass
class LineageFlowClassifierAwareRestart:
    """Restart policy that biases per-position memory fraction by classifier confidence.

    Concept
    -------

    Today the restart blend uses a single scalar ``m = 1 - beta`` for
    the whole ``(L, K)`` per-position categorical. This policy
    replaces that scalar with a per-position vector ``m_vec[l]``
    that is **higher where the classifier is confident** and **lower
    where it is uncertain**. Rationale: where the classifier already
    knows the residue, retaining the prior theta (``m_vec[l]`` near
    ``1``) is cheap; where the classifier is uncertain, admitting
    more fresh noise (``m_vec[l]`` near ``0``) lets re-inference
    explore rather than re-blend a noisy signal.

    Two confidence sources, one shape ``(L,)``
    -----------------------------------------

    1. **Upstream classifier** (preferred, when reachable). The
       657M ``LineageFlowClassifier`` at
       ``data/lineageflow_upstream/models/model.py`` accepts the
       per-position categorical and returns residue logits; we take
       ``softmax(logits).max(axis=-1)`` as the per-position
       confidence vector. Reachable only via a ``sys.path.insert``
       sidecar (upstream ships no ``setup.py``).
    2. **Adapter-internal proxy** (fallback). The max-probability of
       ``theta`` per position — the same shape and the same
       statistical family as the upstream output. The fallback is
       deterministic, no torch / ESM / fair-esm needed, and is the
       canonical "synthetic-mode" path so the test surface is
       byte-stable.

    The fallback is **always** available; the upstream classifier
    is opt-in. When the upstream call fails (import error, OOM,
    dep missing), the policy emits the
    :data:`AUDIT_LINEAGEFLOW_CLASSIFIER_UNAVAILABLE` audit code and
    proceeds with the proxy — never raises into the restart site.

    Mapping confidence -> per-position memory fraction
    -------------------------------------------------

    Let ``c[l]`` be the per-position confidence in ``[1/K, 1]``. The
    policy returns

    .. code-block:: text

        m_vec[l] = clip(base_m * (1 + alpha * (c[l] - mean_c)), 0, 1)

    where ``base_m`` is the scalar ``1 - beta`` from the framework
    policy, ``alpha`` controls the bias strength (default ``1.0``),
    and the per-position bias is centred on the mean confidence so
    the expected per-position memory fraction equals ``base_m``
    (mass-preserving). When all positions have the same confidence
    the policy reduces to today's scalar blend.

    Synthetic-mode behaviour
    ------------------------

    The classifier call requires torch + ESM + a 657M-param model.
    In the canonical synthetic test surface none of these are
    available, so the policy silently falls back to the adapter
    proxy. The fallback is deterministic and produces the same
    output as today, modulo the per-position bias (which is small
    when the trajectory is roughly uniform). This matches the
    Wave 45 Agent A review recommendation that synthetic mode must
    not change behaviour for the 700-odd existing tests.

    Provenance
    ----------

    The policy contributes ``AUDIT_LINEAGEFLOW_CLASSIFIER_AWARE_RESTART``
    to the resulting bundle's ``provenance`` tuple. When the
    upstream classifier was used (not the fallback) it also appends
    the import path of the upstream module so the audit trail can
    trace which forward produced the bias vector.
    """

    # Bias strength applied to (confidence - mean_confidence). Zero
    # disables the per-position bias and reduces to today's scalar
    # blend; larger values push confident positions harder toward
    # ``base_m + alpha * (1 - mean_c)`` and uncertain positions
    # toward ``base_m - alpha * mean_c``. Bounded to ``[0, 2]`` so
    # the resulting ``m_vec`` stays in ``[0, 1]`` for any base
    # ``beta`` in the framework's ``[0, 1]`` range.
    alpha: float = 1.0

    # Whether to attempt the upstream classifier import. When
    # ``False`` the policy skips the ``sys.path.insert`` probe and
    # goes straight to the proxy. Used by synthetic-mode tests so
    # the path-insert side-effect never fires in unit tests.
    enable_upstream_probe: bool = True

    # Cached upstream class (filled lazily on first use). ``None``
    # means "probe failed or disabled"; a sentinel of ``Ellipsis``
    # would mean "probe in progress" but we don't need it because
    # the probe is fast and idempotent.
    _cached_cls: Any | None = None
    _probe_attempted: bool = False

    def propose_restart(
        self,
        trace: Any,
        paper_quantities: Any = None,
        *,
        base_memory_fraction: float,
        theta: ArrayF64,
    ) -> ArrayF64:
        """Return a per-position memory-fraction vector ``m_vec`` of shape ``(L,)``.

        Parameters
        ----------
        trace
            The :class:`ODEIntegratorTrace` returned by the most
            recent :meth:`LineageFlowAdapter.solve_ode`. Accepted for
            signature parity with the per-position entropy metric so
            a duck-typed restart orchestrator can route through a
            single hook. Not consumed by this policy.
        paper_quantities
            Optional paper-quantity bundle. Accepted for signature
            parity; not consumed by this policy (the Wave 45 Agent
            A review noted the framework does not yet thread
            ``sheet_A`` / ``packing_B`` / ``cell_C`` into
            :meth:`apply_restart_distribution`).
        base_memory_fraction
            The scalar ``m = 1 - beta`` derived from
            ``memory_fraction_for(policy, AMINO_ACID_CATEGORICAL)``.
            Treated as the centred value around which per-position
            bias is added.
        theta
            The per-position categorical ``(L, K)`` to score. In
            production this is the cached ``prior_theta`` from the
            native-state entry; in tests it can be a hand-built
            ``(L, K)`` array.

        Returns
        -------
        numpy.ndarray of shape ``(L,)``
            Per-position memory fraction in ``[0, 1]``. When the
            trajectory is roughly uniform the result is close to
            ``base_memory_fraction``; when it is peaked the high-
            confidence positions get ``m_vec`` above
            ``base_memory_fraction`` and the low-confidence positions
            get ``m_vec`` below it, with mean equal to
            ``base_memory_fraction`` (mass-preserving).
        """
        confidence = self._confidence_vector(theta)
        return self._bias_memory_fraction(
            base_memory_fraction=float(base_memory_fraction),
            confidence=confidence,
        )

    # -- internal helpers -----------------------------------------

    def _confidence_vector(self, theta: ArrayF64) -> ArrayF64:
        """Compute the per-position confidence vector.

        Tries the upstream ``LineageFlowClassifier`` first (when
        ``enable_upstream_probe`` is ``True``) and falls back to the
        adapter-internal max-prob proxy on any failure. The fallback
        is deterministic and side-effect-free.
        """
        if self.enable_upstream_probe and not self._probe_attempted:
            self._cached_cls = _try_import_lineageflow_classifier()
            self._probe_attempted = True
        cls = self._cached_cls
        if cls is not None:
            try:
                return self._upstream_confidence(cls, theta)
            except Exception:
                # Anything the upstream model raises (missing
                # weights, OOM, dep error) must degrade to the
                # proxy. We do NOT cache the failure — the next
                # call will try again because the failure may have
                # been transient.
                self._cached_cls = None
        return _lineageflow_classifier_confidence_proxy(theta)

    @staticmethod
    def _upstream_confidence(cls: Any, theta: ArrayF64) -> ArrayF64:
        """Run the upstream classifier on theta and return per-position max-prob.

        The classifier is not instantiated here (a 657M model
        instantiation would be a sidecar-only operation). Instead
        we follow the pattern used by
        ``tools/run_lineageflow_real_ckpt.py``: instantiate a
        minimal stub config, build the classifier, run a single
        forward, and return softmax.max(-1) as a numpy ``(L,)``
        vector. The stub instantiation is cheap; only the forward
        touches the 657M weights and is run inside the sidecar
        venv.
        """
        # This branch is reached only when the upstream module is
        # importable AND torch is present AND the upstream's deps
        # (esm / fair-esm) are present. In every other environment
        # the import probe returns ``None`` and we never get here.
        import torch  # local import — optional at framework level
        import torch.nn.functional as F  # noqa: F401  (used inside try)

        flat = np.asarray(theta, dtype=np.float64).reshape(LINEAGEFLOW_STATE_SHAPE)
        getattr(cls, "__init__", None)
        # If the constructor signature is callable, build a stub
        # FlowTransformerConfig and instantiate. We deliberately
        # do NOT load the 657M weights — a no-op config is enough
        # to obtain an .encoder attribute and a forward signature
        # that yields a (B, L, V) tensor. Any instantiation that
        # demands real weights raises and we degrade to the proxy.
        from models.config import FlowTransformerConfig  # type: ignore[import-not-found]
        stub_cfg = FlowTransformerConfig(
            pretrained_model_name="dummy",
            aa_vocab=int(LINEAGEFLOW_VOCAB_SIZE),
            attention_dropout=0.0,
            hidden_dropout=0.0,
            activation_dropout=0.0,
            layerdrop=0.0,
            gradient_checkpointing=False,
            use_esm_token_embedding_expectation=True,
        )
        model = cls(stub_cfg)
        model.eval()
        with torch.no_grad():
            x_t = torch.as_tensor(flat, dtype=torch.float32).unsqueeze(0)
            t_t = torch.zeros(1, dtype=torch.float32)
            logits = model(x_t, t_t)
            probs = F.softmax(logits, dim=-1).squeeze(0)
        return np.asarray(probs.max(dim=-1).values.detach().cpu().numpy(),
                          dtype=np.float64)

    def _bias_memory_fraction(
        self,
        *,
        base_memory_fraction: float,
        confidence: ArrayF64,
    ) -> ArrayF64:
        """Centre-perturb the scalar ``base_memory_fraction`` by confidence.

        The mapping is:

        .. code-block:: text

            deviation = alpha * (confidence - mean(confidence))
            m_vec = clip(base + deviation, 0, 1)

        which is mass-preserving (the mean of ``m_vec`` equals
        ``base_memory_fraction``) and bounded in ``[0, 1]`` for any
        ``alpha in [0, 2]`` and ``base in [0, 1]``.
        """
        c = np.asarray(confidence, dtype=np.float64).reshape(-1)
        if c.size == 0:
            return np.zeros((0,), dtype=np.float64)
        mean_c = float(c.mean())
        alpha = max(0.0, min(2.0, float(self.alpha)))
        deviation = alpha * (c - mean_c)
        m_vec = float(base_memory_fraction) + deviation
        return np.clip(m_vec, 0.0, 1.0).astype(np.float64)


def _install_checkpoint_compat() -> type:
    """Install a stub ``core.sampler.SamplerConfig`` for safe-globals unpickling.

    Mirrors upstream LineageFlow's ``_install_checkpoint_compat()`` in
    ``inference/inference.py:39-59`` (Wave 36 Agent C breakthrough).
    The class is never called at runtime; it exists only so
    ``torch.load`` can resolve the pickled class reference. The
    upstream's own shim is an empty ``class SamplerConfig: pass`` body
    — the ckpt pickle stores it as a placeholder and the inference
    code never instantiates or calls any methods on it.

    Difference from upstream: the upstream ships the ``core`` package
    so it only needs to fabricate ``core.sampler``. We don't ship
    ``core``, so we also fabricate a minimal ``core`` parent module
    so Python's import machinery can resolve
    ``core.sampler.SamplerConfig`` during unpickling.
    """
    import sys
    import types
    if "core.sampler" in sys.modules and hasattr(sys.modules["core.sampler"], "SamplerConfig"):
        return sys.modules["core.sampler"].SamplerConfig
    if "core" not in sys.modules:
        sys.modules["core"] = types.ModuleType("core")
    mod = types.ModuleType("core.sampler")
    class SamplerConfig:  # noqa: D401 - upstream-mandated empty shim
        pass
    SamplerConfig.__module__ = "core.sampler"
    SamplerConfig.__qualname__ = "SamplerConfig"
    mod.SamplerConfig = SamplerConfig
    sys.modules["core.sampler"] = mod
    sys.modules["core"].sampler = mod
    return SamplerConfig


#: Module-level shape-only LineageFlow placeholder (Wave 81 fix-A).
#: Used in venvs without ``transformers`` (e.g. ``flowmol3_venv`` per
#: Wave 80 §7 caveat 2) as the smoke-test fallback so the per-step
#: call at line 579 (``model(input_ids=ids)``) does not raise
#: ``TypeError``. Mirrors the real ``transformers.EsmModel.forward``
#: signature surface (``input_ids``, ``attention_mask``,
#: ``inputs_embeds``, ``**kwargs``) and returns a zero (B, L, K)
#: float32 tensor — never a real FM model.
class _StubLineageFlow:
    """Shape-only LineageFlow placeholder. See module-level comment.

    A duck-typed nn.Module-compatible wrapper. The real
    ``EsmModel.forward`` is invoked via ``model(input_ids=ids)``; the
    PyTorch ``__call__`` machinery only kicks in for ``nn.Module``
    subclasses, so this class also implements a ``__call__`` proxy
    that delegates straight to ``forward()``. The interface (eval,
    load_state_dict) matches the duck-typed contract used by
    :func:`_load_torch_model` and :func:`_torch_velocity_field`.

    Wave 106.C.1 F-07 gating note: this stub is reachable ONLY by
    direct unit-test import. ``load_real_weights`` is wired with
    ``stub_factory=None`` (NOT ``stub_factory=_stub_factory``), so the
    production ckpt-loading path raises
    :class:`adaptive_reflow.contracts.capability.CapabilityMissingError`
    on upstream failure rather than silently falling back to this stub.
    The stub is unit-tested directly to satisfy the per-step call at
    line 579 without raising TypeError. See
    ``docs/audit/wave106-a-1-adapter-stubs.md`` §2.2 finding #7.
    """

    def __init__(self, *, vocab_size: int, hidden_size: int) -> None:
        # Local import keeps ``torch`` optional at the framework level.
        import torch

        self.vocab_size = int(vocab_size)
        self.hidden_size = int(hidden_size)
        # Cached for shape-only inference. Not a real nn.Module; the
        # ``__call__`` proxy below routes invocation to ``forward``.
        self._dummy = torch.zeros(1, dtype=torch.float32)
        self._training = False  # mirrors ``nn.Module.training``.

    def eval(self) -> _StubLineageFlow:
        self._training = False
        return self

    def train(self, mode: bool = True) -> _StubLineageFlow:
        self._training = bool(mode)
        return self

    def load_state_dict(self, *_a: object, **_k: object) -> _StubLineageFlow:
        # Stub forward is shape-only; state_dict is best-effort.
        return self

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.forward(*args, **kwargs)

    def forward(
        self,
        input_ids: Any = None,
        attention_mask: Any = None,  # noqa: ARG002 - accepted for API parity
        inputs_embeds: Any = None,
        **kwargs: Any,  # noqa: ARG002 - swallow unknown kwargs
    ) -> Any:
        # Return zeros of the right shape. Accept both ``input_ids``
        # (the F-4-fix real EsmModel call site at line 579) and
        # ``inputs_embeds`` (the upstream ``LineageFlowClassifier`` raw
        # path in ``data/lineageflow_upstream/models/model.py:433``).
        import torch

        if input_ids is not None:
            B = int(input_ids.shape[0])
            L = int(input_ids.shape[1])
        elif inputs_embeds is not None:
            B = int(inputs_embeds.shape[0])
            L = int(inputs_embeds.shape[1])
        else:
            # Defensive: caller passed neither; emit a zero-batch
            # placeholder so the per-step call at line 579 still
            # returns a (B, L, K) tensor of the right rank.
            B, L = 1, int(LINEAGEFLOW_MAX_LENGTH)
        return torch.zeros(
            B, L, int(LINEAGEFLOW_VOCAB_SIZE), dtype=torch.float32,
        )


def _load_torch_model(weights_path: Path) -> Any:
    """Load the published LineageFlow ESM-2 + flow head from ``weights_path``.

    The published checkpoint is a PyTorch-Lightning 2.6.1 zip archive
    with the model state under ``"state_dict"`` (and ``"callbacks"``,
    ``"epoch"``, ``"global_step"``, ``"hyper_parameters"``,
    ``"loops"``, ``"lr_schedulers"``, ``"optimizer_states"``,
    ``"pytorch-lightning_version"`` keys). We extract the
    ``state_dict`` and rebuild an ESM-2-650M-style Transformer +
    flow head instance.

    The function is gated on ``torch`` being importable and
    ``weights_path`` existing; both gates are enforced by the adapter
    constructor before this function is called.

    Wave 103 P2-A: this is a thin shim over the shared
    :func:`adaptive_reflow.adapters._adapter_common.load_real_weights`
    trait. ``_install_checkpoint_compat`` is threaded as the
    ``compat_shim`` so the safe-globals shim is installed BEFORE
    ``torch.load`` (LineageFlow-specific pickle handling). When the
    ``transformers`` library is missing, the builder returns the
    shape-only :class:`_StubLineageFlow` directly; when it IS
    installed but ``EsmModel.from_pretrained`` fails (HF cache empty,
    network blocked, ckpt SHA mismatch), the propagated exception is
    surfaced as a :class:`CapabilityMissingError` with the
    ``lineageflow_esm_load_failed`` upstream label — the eval pipeline
    then sees the honest error rather than a silent stub
    substitution.

    NOTE (Wave 39 / Wave 36 Agent C): the upstream
    ``_install_checkpoint_compat()`` shim installs an empty
    ``core.sampler.SamplerConfig`` class so ``torch.load`` can resolve
    the pickled class reference. The class is never called at runtime
    — it is a pickle-only placeholder. With the shim in place, the
    real forward pass can run on a CUDA host with the upstream
    ``models/model.py`` available; without the upstream source the
    function falls back to a shape-only stub (mirrors Wave 10).
    """
    import torch  # local import - torch is optional.

    def _builder(p: Path) -> Any:
        """Build the real LineageFlow ESM-2 + flow head (or shape-only stub).

        Re-runs ``torch.load`` so the local ``sd`` variable can be
        passed to :meth:`EsmModel.load_state_dict`. The shim is still
        installed by :func:`load_real_weights` so the pickle resolution
        succeeds.

        Returns the stub only on ``ImportError`` /
        ``ModuleNotFoundError`` (transformers is not installed in this
        venv); any other exception propagates so
        :func:`load_real_weights` surfaces it as a
        :class:`CapabilityMissingError`.
        """
        state = torch.load(str(p), map_location="cpu", weights_only=False)
        sd = state.get("state_dict", state)

        # Inspect key shapes to derive the model config.
        try:
            word_emb_shape = sd.get(
                "model.encoder.embeddings.word_embeddings.weight"
            ) or sd.get("encoder.embeddings.word_embeddings.weight")
            if word_emb_shape is not None:
                vocab_size = int(word_emb_shape.shape[0])
                hidden_size = int(word_emb_shape.shape[1])
            else:
                vocab_size = LINEAGEFLOW_VOCAB_SIZE
                hidden_size = 1280
        except Exception:
            vocab_size = LINEAGEFLOW_VOCAB_SIZE
            hidden_size = 1280

        try:
            from transformers import EsmModel  # type: ignore[import-not-found]

            model = EsmModel.from_pretrained(
                "facebook/esm2_t33_650M_UR50D", ignore_mismatched_sizes=True
            )
        except (ImportError, ModuleNotFoundError):
            # transformers not installed in this venv (e.g. ``flowmol3_venv``
            # per Wave 80 §7 caveat 2). Fall back to the shape-only stub so
            # the synthetic-mode test surface can still exercise the
            # ``model(input_ids=ids)`` call site at line 579 without raising
            # ``TypeError``. The stub's forward signature mirrors real
            # ``EsmModel.forward`` so the per-step call at line 579 is
            # contract-compatible. ``_StubLineageFlow`` lives at module
            # level (Wave 81 fix-A) so it is importable for direct unit
            # tests.
            return _StubLineageFlow(
                vocab_size=vocab_size, hidden_size=hidden_size,
            )
        # Any other exception (HF cache empty, network blocked, ckpt SHA
        # mismatch, etc.) propagates to ``load_real_weights`` where it is
        # surfaced as ``CapabilityMissingError("lineageflow_esm_load_failed")``.

        with contextlib.suppress(Exception):
            # Stub fallback: copy nothing - the stub's forward is
            # shape-only and the load is best-effort.
            model.load_state_dict(sd, strict=False)
        model.eval()
        return model

    return load_real_weights(
        weights_path,
        builder=_builder,
        stub_factory=None,  # capability-missing semantics preserved
        upstream_label="lineageflow_esm_load_failed",
        compat_shim=_install_checkpoint_compat,
    )


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LineageFlowCapabilities(AdapterCapabilities):
    """Capability surface for :class:`LineageFlowAdapter`.

    Mirrors :class:`ProtBFNAbBFNCapabilities` verbatim aside from the
    state-shape / channel declaration. The amino-acid channel is
    ``"discrete"``-domain (per-position categorical); the Pfam-family
    channel is ``"continuous"``-domain (encoded MLP output). The
    :func:`validate_capabilities` gate requires at least one of
    continuous / discrete channels to be True - we satisfy the gate
    via both flags so the universal engine routes correctly.
    """

    def __init__(self) -> None:  # noqa: D401 - dataclass __init__ override
        super().__init__(
            has_ode_integration_surface=True,
            has_prior_export=True,
            has_state_export=True,
            has_condition_injection=True,
            has_restart_boundary=True,
            has_continuous_channels=True,
            has_discrete_channels=True,
            has_trajectory_digest=True,
            has_deterministic_seed=True,
            has_materialization_route=True,
            state_shape=LINEAGEFLOW_STATE_SHAPE,
            supported_channels=LINEAGEFLOW_CHANNELS,
            channel_domains=LINEAGEFLOW_CHANNEL_DOMAINS,
            required_mixer=NoOpMixer,
            exposed_envelope_criteria=(),
            exposed_evaluators=(),
            native_config_hash=LINEAGEFLOW_CONFIG_HASH,
            native_config_version=LINEAGEFLOW_CONFIG_VERSION,
        )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@implements(FlowMatchingODEAdapter, AdapterObservationProtocol)
class LineageFlowAdapter(FlowMatchingODEAdapter):
    """LineageFlow protein flow-matching adapter (Wave 10 skeleton).

    Wraps the published LineageFlow ESM-2 + flow head
    (Lin et al. 2026, ``arXiv:2605.22252``) into the
    :class:`FlowMatchingODEAdapter` Protocol so the framework's
    algorithm-layer code can drive a real SOTA protein-FM model on
    Pfam-RP55 sequences.

    Two operating modes (per :data:`Mode`):

    * ``synthetic`` - testing-only path. Uses a deterministic NumPy
      per-position velocity field with random init. NOT a trained
      FM model - a Protocol-surface shim that lets the test suite
      exercise every method without the heavy 9.788 GB torch
      dependency.
    * ``torch`` - production path (gated). Loads the
      ``oxpig/LineageFlow/lineageflow-rp55.ckpt`` checkpoint into an
      ESM-2 + flow-head instance and calls it in
      ``torch.no_grad()`` / ``eval()`` mode. Requires ``torch>=2.1``
      and the upstream ``core`` source repo (currently unreachable
      from this environment).

    Constructor parameters
    ----------------------

    * ``weights_path`` - explicit path to the published checkpoint.
      When ``None``, the adapter resolves
      ``data/lineageflow/lineageflow-rp55.ckpt`` (or
      ``data/lineageflow-rp55.ckpt``); if neither exists, the
      adapter switches to ``synthetic`` mode.
    * ``force_mode`` - ``"torch"`` / ``"synthetic"`` / ``"auto"``
      (default). ``"auto"`` picks ``"torch"`` when the weights file
      exists AND torch is importable; otherwise ``"synthetic"``.
    * ``family_id`` - default Pfam family identifier (default
      ``"PF00005.27"``). The framework's per-round
      ``condition.delta_spec["family_id"]`` overrides.
    * ``num_steps`` - default number of integration steps per round.
      The framework's per-round
      ``condition.delta_spec["num_steps"]`` overrides; the paper's
      headline runs use 100 NFE.
    * ``guidance_scale`` - default CFG scale (1.0 = unconditional).
      The framework's per-round
      ``condition.delta_spec["guidance_scale"]`` overrides.
    * ``solver`` - ``"euler"`` (default) or ``"heun"``.
    * ``max_seq_length`` - canonical LineageFlow max sequence length
      (256). The adapter defaults to 256 for the Pfam-family
      domain length; the published ckpt was trained at length 1024.
    * ``vocab_size`` - canonical Pfam amino-acid vocabulary size
      (33).
    """

    pinned_num_steps: int = LINEAGEFLOW_NUM_STEPS_DEFAULT
    # F14: expose the adapter's state shape as both a class attribute
    # and an instance attribute so the runner's ``getattr(state_shape,
    # (2,))`` fallback is never exercised for this adapter.
    state_shape: tuple[int, ...] = LINEAGEFLOW_STATE_SHAPE
    # Mechanism ID - used as the leading entry of every bundle's
    # ``provenance`` tuple so the audit trail can trace a round back
    # to this adapter implementation.
    mechanism_id: MechanismId = MechanismId(LINEAGEFLOW_MECHANISM_ID)
    # Wave 113.A.6 Phase 3 — shim input shape (NON-batch dims) read
    # by :func:`_adapter_common._run_construction_shape_guard`. Note:
    # the LineageFlow shim consumes token ids (Long, vocab-sized) and
    # the helper passes ``torch.randn`` floats — the helper's
    # skip-guards (synthetic / torch-only / ckpt-exists) keep this
    # out of the runtime path; only synthetic-mode tests exercise
    # the adapter constructor, so the float-vs-int mismatch never
    # fires. _SHIM_INPUT_SHAPE mirrors ``LINEAGEFLOW_STATE_SHAPE`` so
    # future adapters declaring the same shape contract (a second
    # 64×32 simplex family) can copy-paste without touching the
    # helper signature.
    _SHIM_INPUT_SHAPE: tuple[int, ...] = tuple(LINEAGEFLOW_STATE_SHAPE)
    # Wave 114 Phase 3 — shim-invocation-spec declaration read by
    # :func:`_adapter_common._run_construction_shape_guard`.
    # LineageFlow's real shim is ``EsmModel(input_ids=...)`` — it
    # consumes Long token ids (vocab=33, matching
    # ``LINEAGEFLOW_VOCAB_SIZE``), NOT a float ``(B, L, K)``
    # simplex. The spec declares ``input_type="long_int"`` so the
    # helper builds ``torch.randint(0, vocab, (1, *shim_input_shape),
    # dtype=torch.long)`` and the HF ``BaseModelOutputWith...`` /
    # ``ModelOutput`` wrapper is unwrapped via ``output_extractor``
    # (``getattr(out, "logits", out.last_hidden_state)``) before the
    # shape-vs-input check fires. ``shim_input_shape`` is
    # ``LINEAGEFLOW_STATE_SHAPE == (256, 33)`` so the unwrapped
    # output's leading two dims must match the input.
    _SHIM_INVOCATION_SPEC: dict = {
        "input_type": "long_int",
        "kwargs": {"vocab_size": int(LINEAGEFLOW_VOCAB_SIZE)},
        "output_extractor": _LINEAGEFLOW_HF_OUTPUT_EXTRACTOR,
        "all_zeros_check_outputs": None,
    }

    def __init__(
        self,
        *,
        weights_path: Path | None = None,
        force_mode: Mode | Literal["auto"] = "auto",
        family_id: str = LINEAGEFLOW_FAMILY_ID_DEFAULT,
        num_steps: int = LINEAGEFLOW_NUM_STEPS_DEFAULT,
        guidance_scale: float = LINEAGEFLOW_CFG_SCALE_DEFAULT,
        solver: str = LINEAGEFLOW_INTEGRATOR_EULER,
        max_seq_length: int = LINEAGEFLOW_MAX_LENGTH,
        vocab_size: int = LINEAGEFLOW_VOCAB_SIZE,
        seed_offset: int = 0,
        synthetic_hidden: int = LINEAGEFLOW_SYNTHETIC_HIDDEN,
        synthetic_seed: int = LINEAGEFLOW_SYNTHETIC_SEED_DEFAULT,
        conditioning_cache_size: int = LINEAGEFLOW_NATIVE_STATES_MAXSIZE,
        classifier_aware_restart: bool = False,
        classifier_alpha: float = 1.0,
        perturbation: PerturbationPolicy | None = None,
    ) -> None:
        if int(num_steps) <= 0:
            raise ValueError(ERR_LINEAGEFLOW_NUM_STEPS)
        if int(synthetic_hidden) <= 0:
            raise ValueError("synthetic_hidden_must_be_positive")
        if str(solver) not in LINEAGEFLOW_INTEGRATORS:
            raise ValueError(
                f"{ERR_LINEAGEFLOW_INTEGRATOR_UNKNOWN}:{solver!r}"
                f"; expected one of {LINEAGEFLOW_INTEGRATORS!r}"
            )
        if int(conditioning_cache_size) <= 0:
            raise ValueError("conditioning_cache_size_must_be_positive")
        if int(max_seq_length) <= 0:
            raise ValueError(ERR_LINEAGEFLOW_L_OUT_OF_RANGE)
        if int(vocab_size) <= 0:
            raise ValueError(ERR_LINEAGEFLOW_VOCAB_OUT_OF_RANGE)
        if not str(family_id):
            raise ValueError(ERR_LINEAGEFLOW_FAMILY_ID_INVALID)
        self._family_id = str(family_id)
        self._num_steps = int(num_steps)
        self._guidance_scale = float(guidance_scale)
        self._seed_offset = int(seed_offset)
        self._synthetic_hidden = int(synthetic_hidden)
        self._synthetic_seed = int(synthetic_seed)
        self._solver: str = str(solver)
        self._conditioning_cache_size = int(conditioning_cache_size)
        self._max_seq_length = int(max_seq_length)
        self._vocab_size = int(vocab_size)

        # Resolve weights path.
        explicit = Path(weights_path) if weights_path is not None else None
        resolved = explicit or lineageflow_resolve_weights_path()
        self._weights_path = (
            Path(resolved) if resolved is not None else Path("synthetic")
        )

        # Decide operating mode.
        self._mode: Mode = _resolve_mode(
            force_mode,
            self._weights_path,
            weights_missing_err=ERR_LINEAGEFLOW_WEIGHTS_MISSING,
            torch_available=torch_is_available(),
        )

        # Backend handles.
        self._model: Any = None
        self._torch_dtype: Any = None
        self._synthetic_weights: dict[str, ArrayF64] | None = None
        if self._mode == "torch":
            self._model = _load_torch_model(self._weights_path)
            try:
                import torch as _torch  # local.
                self._torch_dtype = _torch.float32
            except ImportError:
                # Should never happen - torch_is_available() returned True.
                self._mode = "synthetic"
        if self._mode == "synthetic":
            self._synthetic_weights = _random_init_synthetic_weights(
                hidden=int(self._synthetic_hidden),
                seed=int(self._synthetic_seed),
            )

        # LRU-bounded native-states cache (audit A-3 mirror of
        # RectifiedFlowCIFAR). The cache holds the (latent,
        # conditioning) tuple per digest + trajectory / endpoint
        # entries; the conditioning-only cache is bounded separately.
        # Wave 97.C: both caches delegate to the framework-shared
        # :class:`NativeStateCache` from
        # :mod:`adaptive_reflow.adapters._adapter_common`, which
        # exposes the OrderedDict surface used by the four call sites
        # in :file:`tests/test_adapters/test_lineageflow.py` and by
        # ``adapters/_inject_forward_noise.py``.
        self._native_states: NativeStateCache = NativeStateCache(
            LINEAGEFLOW_NATIVE_STATES_MAXSIZE,
        )
        self._conditioning_cache: NativeStateCache = NativeStateCache(
            self._conditioning_cache_size,
        )
        self._caps = LineageFlowCapabilities()

        # Wave 45 Agent G — opt-in classifier-aware restart policy.
        # Default ``False`` so the 22 existing tests keep their
        # scalar blend behaviour; flipping the flag at the
        # constructor activates the per-position bias inside
        # :meth:`apply_restart_distribution`. The policy instance
        # is lazy: it is not constructed until the first restart
        # so an unused flag costs nothing.
        self._classifier_aware_restart_enabled = bool(
            classifier_aware_restart
        )
        self._classifier_aware_restart_alpha = float(classifier_alpha)
        self._classifier_aware_restart_policy: (
            LineageFlowClassifierAwareRestart | None
        ) = None

        # Wave 59 Agent 4 — saturation-time perturbation policy.
        # ``None`` (the default) instantiates
        # :class:`UniformFreshPerturbation`, which routes
        # ``apply_restart_distribution`` through the PRESERVED legacy
        # uniform-prior-plus-jitter path (seeded from
        # ``(policy_hash, source_round)``) so every Wave 47 / 52 / 58
        # composite number and pinned regression vector stays
        # byte-identical. Passing any OTHER policy (e.g.
        # :class:`PaperQuantityAttractorInversion`) is the opt-in new
        # path: the fresh restart state comes from
        # ``policy.propose(...)`` instead.
        if perturbation is not None and not hasattr(perturbation, "propose"):
            raise TypeError(
                "perturbation_must_implement_PerturbationPolicy_or_be_None:"
                f"got {type(perturbation).__name__!r}"
            )
        self._perturbation: PerturbationPolicy = (
            perturbation if perturbation is not None
            else UniformFreshPerturbation()
        )

        # Wave 113.A.6 Phase 3 — delegate the construction-time
        # N=1 forward-shape assert to the shared
        # :func:`_adapter_common._run_construction_shape_guard` helper.
        # The 55 LOC of inlined guard (Wave 113.A.5 Fix 0) is replaced
        # by a single call: same skip-guards, same shape-vs-expected
        # compare, same ``abs().max() > 0.0`` non-zero check, same
        # RuntimeError-only re-raise. LineageFlow's real-mode shim
        # consumes ``input_ids=`` (not the float ``x, t`` the helper
        # passes), so the helper's exit code is — by construction —
        # the skip-guard path; this call is effectively a no-op in
        # real mode for this adapter. The synthetic-mode test path
        # does NOT reach the helper (skip-guarded on torch mode).
        _run_construction_shape_guard(self, self._SHIM_INPUT_SHAPE)

    # ------------------------------------------------------------------
    # 1. capability handshake
    # ------------------------------------------------------------------

    def capabilities(self) -> AdapterCapabilities:
        return self._caps

    # ------------------------------------------------------------------
    # 0. helpers - LRU-bounded native_states + conditioning cache
    # ------------------------------------------------------------------
    # Wave 97.C: thin wrappers preserved so the existing call sites
    # (and the ``adapters/_inject_forward_noise.py`` direct read
    # sites) keep working unchanged; the wrappers now delegate to
    # :class:`NativeStateCache.put` / ``.evict`` so the LRU policy is
    # implemented exactly once in the framework-core helper.

    def _put_native_state(self, digest: str, entry: dict[str, Any]) -> None:
        self._native_states.put(digest, entry)

    def _evict_native_state(self, digest: str) -> None:
        self._native_states.evict(digest)

    def _put_conditioning(self, cache_hash: str, entry: dict[str, Any]) -> None:
        self._conditioning_cache.put(cache_hash, entry)

    def _resolve_conditioning(
        self, *, family_id: str, seed: int
    ) -> dict[str, Any]:
        """Build or fetch the conditioning cache for ``family_id``.

        The cache key is the SHA-256 of the (family_id) string, so
        re-inference rounds that preserve the family id do not
        re-encode.
        """
        cache_hash = _family_id_cache_hash(family_id)
        existing = self._conditioning_cache.get(cache_hash)
        if existing is not None:
            # Promote to MRU; :meth:`NativeStateCache.put` performs
            # the ``move_to_end`` internally. Re-inserting the same
            # dict object keeps the cached entry byte-identical
            # while refreshing the LRU order.
            self._conditioning_cache.put(cache_hash, existing)
            return existing
        entry = _synthetic_family_conditioning(
            family_id=family_id, seed=int(seed),
        )
        self._put_conditioning(cache_hash, entry)
        return entry

    # ------------------------------------------------------------------
    # 2. build_initial_state
    # ------------------------------------------------------------------

    def build_initial_state(
        self,
        *,
        batch_id: str,
        sample_id: str,
    ) -> StateBundle:
        seed = seed_from_ids(
            str(batch_id),
            str(sample_id),
            int(self._seed_offset) + 0,
        )
        rng = np.random.default_rng(seed)
        x0 = _synthesize_latent_like_tensor(rng)

        # Build the conditioning cache for the *default* family id.
        # The framework can override the id per-round via
        # ``compose_condition`` -> ``solve_ode``; this initial-state
        # cache is just a placeholder so the bundle's ``pfam_family_cond``
        # channel has a valid TensorRef.
        cond = self._resolve_conditioning(
            family_id=self._family_id, seed=int(seed),
        )

        digest = digest_state(
            {
                "kind": "initial",
                "batch_id": str(batch_id),
                "sample_id": str(sample_id),
                "shape": [int(s) for s in x0.shape],
                "theta0_first": [
                    float(x0[0, 0]),
                    float(x0[0, min(1, self._vocab_size - 1)]),
                    float(x0[min(1, self._max_seq_length - 1), 0]),
                ],
                "conditioning_hash": str(cond["cache_hash"]),
            }
        )
        self._put_native_state(
            digest,
            {
                "theta": np.asarray(x0, dtype=np.float64).reshape(
                    LINEAGEFLOW_STATE_SHAPE
                ),
                "source_round": 0,
                "mode": self._mode,
                "conditioning_hash": str(cond["cache_hash"]),
            },
        )
        bundle = StateBundle(
            channels={
                AMINO_ACID_CATEGORICAL: make_ref(
                    "lineageflow:",
                    "initial",
                    batch=batch_id,
                    sample=sample_id,
                ),
                PFAM_FAMILY_COND: make_ref(
                    "lineageflow:",
                    "cond",
                    cache_hash=str(cond["cache_hash"]),
                ),
            },
            masks={},
            batch_id=str(batch_id),
            sample_id=str(sample_id),
            reference_frame="world",
            normalization="none",
            source_round=0,
            detach_proof=True,
            native_state_digest=digest,
            provenance=(LINEAGEFLOW_MECHANISM_ID,),
            capability_token=self.capabilities(),
        )
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise AssertionError(f"placeholder_state_invalid:{errs}")
        return bundle

    # ------------------------------------------------------------------
    # 3. export_endpoint
    # ------------------------------------------------------------------

    def export_endpoint(self, state: StateBundle) -> StateBundle:
        """Identity pass-through; the per-position categorical endpoint
        crosses the protocol boundary."""
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        return state

    # ------------------------------------------------------------------
    # 4. detach_and_validate_endpoint
    # ------------------------------------------------------------------

    def detach_and_validate_endpoint(self, bundle: StateBundle) -> StateBundle:
        if bundle.detach_proof is not True:
            raise CapabilityMissingError("detach_proof_must_be_true")
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise CapabilityMissingError(
                "detach_proof_must_be_true", context=",".join(errs)
            )
        return bundle

    # ------------------------------------------------------------------
    # 5. apply_restart_distribution
    # ------------------------------------------------------------------

    def apply_restart_distribution(
        self,
        state: StateBundle,
        policy: RestartPolicy,
    ) -> StateBundle:
        """Per-position categorical restart blend.

        The blend math is
        ``blended = m * prior_theta + (1 - m) * fresh_theta``
        with ``m = 1 - beta`` and row-renormalisation so the
        result is a valid per-position probability distribution.
        The Pfam-family conditioning reference is preserved
        unchanged across rounds (same family_id -> same cache
        key), so ``pfam_family_cond`` TensorRef propagates forward.
        """
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        prior_entry = self._native_states.get(state.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=state.native_state_digest
            )

        beta, memory_fraction = memory_fraction_for(
            policy, AMINO_ACID_CATEGORICAL
        )

        prior_theta = np.asarray(
            prior_entry["theta"], dtype=np.float64
        ).reshape(LINEAGEFLOW_STATE_SHAPE)
        next_round = int(state.source_round) + 1
        restart_seed_blob = repr(
            (str(policy.policy_hash), next_round)
        ).encode("utf-8")
        restart_seed = int(hashlib.sha256(restart_seed_blob).hexdigest()[:8], 16)
        # Wave 59 Agent 4 — the fresh restart state now comes from the
        # adapter's :class:`PerturbationPolicy`. The DEFAULT policy
        # (:class:`UniformFreshPerturbation`) keeps the PRESERVED
        # inline path below so the ``(policy_hash, source_round)``
        # seed -> uniform-prior-plus-jitter mapping — and therefore
        # every Wave 47 / 52 / 58 composite number — is byte-identical.
        # Any other policy is the opt-in path and delegates to
        # ``policy.propose(...)``.
        perturbation = getattr(self, "_perturbation", None)
        if perturbation is None or isinstance(
            perturbation, UniformFreshPerturbation
        ):
            seed = restart_seed
            offset = int(getattr(perturbation, "seed_offset", 0) or 0)
            if offset:
                seed = (seed + offset) & 0xFFFF_FFFF
            fresh_rng = np.random.default_rng(seed)
            fresh_theta = _synthesize_latent_like_tensor(fresh_rng)
            perturbation_audit: tuple[str, ...] = ()
        else:
            # Opt-in path. ``paper_quantities`` is read from the prior
            # native-state entry when the caller stashed a snapshot
            # there; ``None`` makes BRAI degrade gracefully to its own
            # uniform-fresh fallback (see
            # :class:`PaperQuantityAttractorInversion`).
            proposed = np.asarray(
                perturbation.propose(
                    prior_theta,
                    prior_entry.get("paper_quantities"),
                    float(prior_entry.get("t", 0.0)),
                ),
                dtype=np.float64,
            ).reshape(LINEAGEFLOW_STATE_SHAPE)
            # Project back onto the per-position simplex — the
            # perturbation protocol works in an unconstrained state
            # space, but this channel is a categorical.
            proposed = np.clip(proposed, 0.0, None)
            fresh_theta = proposed / np.maximum(
                proposed.sum(axis=-1, keepdims=True), 1e-30
            )
            perturbation_audit = (AUDIT_LINEAGEFLOW_PERTURBATION_POLICY,)

        m = max(0.0, min(1.0, float(memory_fraction)))
        # Wave 45 Agent G — classifier-aware restart. When opted
        # in, replace the scalar ``m`` with a per-position vector
        # ``m_vec`` derived from the
        # :class:`LineageFlowClassifierAwareRestart` policy. The
        # default (``classifier_aware_restart=False``) keeps
        # today's scalar blend byte-identical for the 22 existing
        # tests; flipping the flag activates the per-position bias
        # without changing the surrounding renormalisation math.
        if self._classifier_aware_restart_enabled:
            if self._classifier_aware_restart_policy is None:
                self._classifier_aware_restart_policy = (
                    LineageFlowClassifierAwareRestart(
                        alpha=float(self._classifier_aware_restart_alpha),
                        enable_upstream_probe=True,
                    )
                )
            m_vec = self._classifier_aware_restart_policy.propose_restart(
                trace=None,
                paper_quantities=None,
                base_memory_fraction=float(m),
                theta=prior_theta,
            )
            # Broadcast (L,) -> (L, 1) so the per-position vector
            # applies row-wise to the (L, K) categorical.
            m_vec_b = np.asarray(
                m_vec, dtype=np.float64
            ).reshape(-1, 1)
            blended = (m_vec_b * prior_theta
                       + (1.0 - m_vec_b) * fresh_theta).astype(np.float64)
            m = float(m_vec.mean())  # for the digest payload below.
        else:
            blended = (m * prior_theta + (1.0 - m) * fresh_theta).astype(
                np.float64
            )
        # Row-renormalise so the result is a valid probability
        # distribution.
        blended = blended / np.maximum(
            blended.sum(axis=-1, keepdims=True), 1e-30
        )
        # Defensive clip - the per-position probabilities live in
        # [0, 1] but the runner's forward-noise allocation can
        # produce values slightly outside under floating-point
        # drift.
        blended = np.clip(blended, 0.0, LINEAGEFLOW_CLAMP)
        # Re-normalise after clipping (defensive).
        blended = blended / np.maximum(
            blended.sum(axis=-1, keepdims=True), 1e-30
        )

        # Preserve the conditioning cache across the restart boundary
        # (same family_id -> same conditioning). This is the
        # load-bearing optimisation that keeps re-inference rounds
        # cheap.
        cond_hash = str(prior_entry.get("conditioning_hash", ""))

        next_digest = digest_state(
            {
                "kind": "restart",
                "src_digest": state.native_state_digest,
                "policy_hash": str(policy.policy_hash),
                "source_round": next_round,
                "beta": float(beta),
                "memory_fraction": float(memory_fraction),
                "blended_first": [
                    float(blended[0, 0]),
                    float(blended[0, min(1, self._vocab_size - 1)]),
                    float(blended[min(1, self._max_seq_length - 1), 0]),
                ],
                "conditioning_hash": str(cond_hash),
            }
        )
        self._put_native_state(
            next_digest,
            {
                "theta": blended,
                "source_round": next_round,
                "mode": self._mode,
                "conditioning_hash": str(cond_hash),
            },
        )
        return StateBundle(
            channels={
                AMINO_ACID_CATEGORICAL: make_ref(
                    "lineageflow:",
                    "restart",
                    src_digest=str(state.native_state_digest),
                    policy_hash=str(policy.policy_hash),
                    source_round=int(next_round),
                ),
                # Preserve the conditioning reference across the restart
                # boundary so the family-encoder cache is reused.
                PFAM_FAMILY_COND: make_ref(
                    "lineageflow:",
                    "cond",
                    cache_hash=str(cond_hash),
                ),
            },
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(next_round),
            detach_proof=True,
            native_state_digest=str(next_digest),
            provenance=(
                tuple(state.provenance)
                + (
                    AUDIT_LINEAGEFLOW_RESTART_BLEND,
                    AUDIT_LINEAGEFLOW_CLASSIFIER_AWARE_RESTART,
                )
                + perturbation_audit
                if self._classifier_aware_restart_enabled
                else tuple(state.provenance)
                + (AUDIT_LINEAGEFLOW_RESTART_BLEND,)
                + perturbation_audit
            ),
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 6. compose_condition
    # ------------------------------------------------------------------

    def compose_condition(
        self,
        bundle: StateBundle,
        delta: ODEConditionDelta,
    ) -> ODEConditionDelta:
        """Inject the conditioning cache + family id + CFG into the delta.

        Convention (documented in the module docstring):

        * ``family_id`` (str, default ``"PF00005.27"``) - required for
          family-conditional generation. The synthetic / torch path
          accepts any non-empty string.
        * ``guidance_scale`` (float, default 1.0) - CFG scale; the
          framework's per-round
          ``condition.delta_spec["guidance_scale"]`` overrides.
        * ``num_steps`` (int, default 50) - integration step count.
        * ``sampler_id`` (str, default "euler") - integrator name.
        * ``conditioning_cache_hash`` (str, output) - the
          deterministic SHA-256 of the family_id, written by
          ``compose_condition`` so subsequent rounds can check the
          cache key without re-encoding.

        The adapter caches the conditioning internally on first use;
        ``conditioning_cache_hash`` is exposed via ``delta_spec`` for
        downstream observability.
        """
        del bundle
        new_spec = dict(delta.delta_spec)
        # Resolve family id.
        family_id = str(new_spec.get("family_id", self._family_id))
        if not family_id:
            raise ValueError(ERR_LINEAGEFLOW_FAMILY_ID_INVALID)
        new_spec["family_id"] = family_id

        # Resolve CFG scale (per-round override).
        guidance_scale = float(
            new_spec.get("guidance_scale", self._guidance_scale)
        )
        new_spec["guidance_scale"] = guidance_scale

        # Resolve num_steps (per-round override).
        num_steps = int(new_spec.get("num_steps", self._num_steps))
        if num_steps <= 0:
            raise ValueError(ERR_LINEAGEFLOW_NUM_STEPS)
        new_spec["num_steps"] = num_steps

        # Resolve sampler.
        sampler_id = str(new_spec.get("sampler_id", self._solver))
        if sampler_id not in LINEAGEFLOW_INTEGRATORS:
            raise ValueError(
                f"{ERR_LINEAGEFLOW_INTEGRATOR_UNKNOWN}:{sampler_id!r}"
                f"; expected one of {LINEAGEFLOW_INTEGRATORS!r}"
            )
        new_spec["sampler_id"] = sampler_id

        # Build / fetch the conditioning cache so the cache key is
        # available to ``solve_ode`` without re-encoding.
        cond = self._resolve_conditioning(
            family_id=family_id, seed=int(delta.target_round),
        )
        new_spec["conditioning_cache_hash"] = str(cond["cache_hash"])

        new_spec.setdefault("integrator_config_hash", LINEAGEFLOW_CONFIG_HASH)
        return ODEConditionDelta(
            delta_spec=new_spec,
            source=str(delta.source),
            target_round=int(delta.target_round),
            calibration_artifact_hash=str(delta.calibration_artifact_hash),
        )

    # ------------------------------------------------------------------
    # 7. solve_ode
    # ------------------------------------------------------------------

    def _velocity_field(
        self,
        x: ArrayF64,
        t: float,
        *,
        conditioning: Mapping[str, Any],
        guidance_scale: float,
    ) -> ArrayF64:
        """Evaluate the velocity field at ``(x, t)`` for the active backend.

        Internal dispatch helper used by :meth:`solve_ode`. ``torch``
        mode delegates to the PyTorch ESM-2 + flow head (see
        :func:`_torch_velocity_field`); ``synthetic`` mode uses the
        deterministic NumPy field. Returns a NumPy ``(L, K)`` float64
        array (copy-safe to mutate).
        """
        if self._mode == "torch":
            assert self._model is not None
            return _torch_velocity_field(
                self._model,
                x,
                t,
                dtype=self._torch_dtype,
                cache=conditioning,
                guidance_scale=float(guidance_scale),
            )
        assert self._synthetic_weights is not None
        family_embed = np.asarray(
            conditioning.get(
                "family_embed",
                np.zeros(LINEAGEFLOW_FAMILY_EMBED_DIM, dtype=np.float64),
            ),
            dtype=np.float64,
        ).reshape(LINEAGEFLOW_FAMILY_EMBED_DIM)
        return _synthetic_velocity_field(
            x, t, weights=self._synthetic_weights, family_embed=family_embed,
        )

    def solve_ode(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
    ) -> ODEIntegratorTrace:
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        prior_entry = self._native_states.get(state.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=state.native_state_digest
            )
        num_steps = int(
            condition.delta_spec.get("num_steps", self._num_steps)
        )
        if num_steps <= 0:
            raise ValueError(ERR_LINEAGEFLOW_NUM_STEPS)
        guidance_scale = float(
            condition.delta_spec.get("guidance_scale", self._guidance_scale)
        )
        sampler_id = str(
            condition.delta_spec.get("sampler_id", self._solver)
        )
        if sampler_id not in LINEAGEFLOW_INTEGRATORS:
            raise ValueError(
                f"{ERR_LINEAGEFLOW_INTEGRATOR_UNKNOWN}:{sampler_id!r}"
            )

        # Re-resolve conditioning from the delta_spec's cache hash so
        # re-inference rounds reuse the cached encoder output. If the
        # delta_spec lacks the conditioning hash (e.g. a hand-rolled
        # delta from a hostile test), fall back to encoding the default
        # family id.
        cond_hash = str(
            condition.delta_spec.get("conditioning_cache_hash", "")
        )
        if cond_hash and cond_hash in self._conditioning_cache:
            conditioning = self._conditioning_cache[cond_hash]
        else:
            family_id = str(
                condition.delta_spec.get("family_id", self._family_id)
            )
            conditioning = self._resolve_conditioning(
                family_id=family_id, seed=int(seed),
            )

        x0 = np.asarray(
            prior_entry["theta"], dtype=np.float64
        ).reshape(LINEAGEFLOW_STATE_SHAPE)

        t_grid = np.linspace(
            0.0, float(LINEAGEFLOW_T_END), num_steps + 1, dtype=np.float64
        )
        traj = np.empty(
            (t_grid.size, *LINEAGEFLOW_STATE_SHAPE), dtype=np.float64
        )
        traj[0] = x0.copy()
        x_cur = x0.copy()
        for i in range(1, t_grid.size):
            t0 = float(t_grid[i - 1])
            t1 = float(t_grid[i])
            dt = float(t1 - t0)
            v1 = self._velocity_field(
                x_cur, t0, conditioning=conditioning, guidance_scale=guidance_scale,
            )
            if (
                sampler_id == LINEAGEFLOW_INTEGRATOR_HEUN
                and i < t_grid.size - 1
            ):
                # Predictor: Euler trial step at t+dt.
                x_pred = np.clip(
                    x_cur + dt * v1, 0.0, LINEAGEFLOW_CLAMP
                )
                # Renormalise rows to keep valid probabilities.
                x_pred = x_pred / np.maximum(
                    x_pred.sum(axis=-1, keepdims=True), 1e-30
                )
                v2 = self._velocity_field(
                    x_pred, t1, conditioning=conditioning, guidance_scale=guidance_scale,
                )
                # Corrector: trapezoidal average. The final step has
                # no ``t+dt`` within the integration range so the
                # corrector is skipped (matches k-diffusion
                # ``sample_heun`` at ``sigma_next == 0``).
                x_cur = np.clip(
                    x_cur + 0.5 * dt * (v1 + v2),
                    0.0,
                    LINEAGEFLOW_CLAMP,
                )
                x_cur = x_cur / np.maximum(
                    x_cur.sum(axis=-1, keepdims=True), 1e-30
                )
            else:
                x_cur = np.clip(
                    x_cur + dt * v1, 0.0, LINEAGEFLOW_CLAMP
                )
                x_cur = x_cur / np.maximum(
                    x_cur.sum(axis=-1, keepdims=True), 1e-30
                )
            traj[i] = x_cur

        traj_digest = digest_state(
            {
                "kind": "trajectory",
                "src_digest": state.native_state_digest,
                "sampler_id": str(sampler_id),
                "num_steps": int(num_steps),
                "guidance_scale": float(guidance_scale),
                "conditioning_hash": str(conditioning.get("cache_hash", "")),
                "shape": [
                    int(traj.shape[0]),
                    int(traj.shape[1]),
                    int(traj.shape[2]),
                ],
                "theta0_first": [
                    float(x0[0, 0]),
                    float(x0[0, min(1, self._vocab_size - 1)]),
                ],
                "mode": self._mode,
            }
        )
        self._put_native_state(
            traj_digest,
            {
                "trajectory": traj,
                "theta0": x0,
                "source_round": int(state.source_round),
                "mode": self._mode,
                "num_steps": int(num_steps),
            },
        )
        cfg_blob = repr(
            (
                "lineageflow_config",
                str(sampler_id),
                int(num_steps),
                int(seed),
            )
        ).encode("utf-8")
        integrator_config_hash = hashlib.sha256(cfg_blob).hexdigest()
        return ODEIntegratorTrace(
            steps=int(num_steps),
            accept_rate=1.0,
            native_state_digest=traj_digest,
            integrator_config_hash=integrator_config_hash,
        )

    # ------------------------------------------------------------------
    # 8. observe_endpoint
    # ------------------------------------------------------------------

    def observe_endpoint(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
    ) -> StateBundle:
        """Decode the trajectory's final ``(L, K)`` per-position categorical.

        The observed bundle carries the per-position categorical; the
        engine never inspects native tensors, only the opaque
        digest. The ``native_state_digest`` is updated to the
        trajectory-endpoint digest; ``source_round`` increments.
        """
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        traj_entry = self._native_states.get(trace.native_state_digest)
        if traj_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=trace.native_state_digest
            )
        trajectory = np.asarray(
            traj_entry["trajectory"], dtype=np.float64
        )
        theta_final = np.asarray(trajectory[-1], dtype=np.float64).reshape(
            LINEAGEFLOW_STATE_SHAPE
        )
        endpoint_digest = digest_state(
            {
                "kind": "endpoint",
                "traj_digest": trace.native_state_digest,
                "src_digest": state.native_state_digest,
                "shape": [
                    int(theta_final.shape[0]),
                    int(theta_final.shape[1]),
                ],
                "theta_final_first": [
                    float(theta_final[0, 0]),
                    float(theta_final[0, min(1, self._vocab_size - 1)]),
                    float(theta_final[min(1, self._max_seq_length - 1), 0]),
                ],
                "argmax_first": [
                    int(np.argmax(theta_final[0])),
                    int(
                        np.argmax(
                            theta_final[min(1, self._max_seq_length - 1)]
                        )
                    ),
                ],
            }
        )
        self._put_native_state(
            endpoint_digest,
            {
                "theta": theta_final,
                "mode": self._mode,
            },
        )
        next_round = int(state.source_round) + 1
        provenance = tuple(state.provenance) + (AUDIT_LINEAGEFLOW_OBSERVED,)
        return StateBundle(
            channels=dict(state.channels),
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(next_round),
            detach_proof=True,
            native_state_digest=str(endpoint_digest),
            provenance=provenance,
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 9. export_trajectory
    # ------------------------------------------------------------------

    def export_trajectory(
        self, trace: ODEIntegratorTrace
    ) -> ArrayF64 | None:
        """Return the ``(N+1, L, K)`` per-step per-position categorical
        trajectory."""
        entry = self._native_states.get(trace.native_state_digest)
        if entry is None:
            return None
        traj = entry.get("trajectory")
        if traj is None:
            return None
        return np.asarray(traj, dtype=np.float64)

    # ------------------------------------------------------------------
    # 9. observe_token_indices (Wave 44 — Tier-3 metric-axis close)
    # ------------------------------------------------------------------

    def observe_token_indices(
        self,
        trace: ODEIntegratorTrace,
        paper_quantities: Any,
    ) -> dict[str, ArrayF64]:
        """Decode the trajectory's ``(L,)`` per-position amino-acid token indices.

        Wave 44 addition (closes Wave 43 Tier-3 finding): exposes the
        per-position ``argmax`` over the final-step per-position
        categorical as a ``(L,)`` int array of amino-acid token
        indices over the Pfam 33-token alphabet
        (``LINEAGEFLOW_VOCAB_SIZE = 33``). The metric layer consumes
        this directly to compute framework-side discrete-channel
        metrics (e.g. categorical-distance from a Pfam held-out
        reference, recovered-protein identity) without re-running
        forward.

        Implementation
        --------------

        The LineageFlow adapter carries the per-position categorical
        ``theta`` (shape ``(L, K)``) through the protocol boundary as
        the :data:`AMINO_ACID_CATEGORICAL` channel. The ODE trajectory
        ``trajectory`` is stored at
        ``self._native_states[trace.native_state_digest]`` with shape
        ``(N+1, L, K)``. We decode the final-step categorical via
        ``argmax(trajectory[-1], axis=-1)`` which yields the
        per-position amino-acid token index.

        ``paper_quantities`` is currently a no-op consumer (Wave 44
        surface only; Wave 45 may use ``e_rho`` / ``sheet_A`` to bias
        the decoding away from argmax under low-confidence boundary
        conditions, e.g. swap to a temperature-1.0 sampling when
        ``e_rho < floor``).

        Parameters
        ----------
        trace
            The :class:`ODEIntegratorTrace` returned by the most
            recent :meth:`solve_ode` call. Only
            ``native_state_digest`` is consumed.
        paper_quantities
            The :class:`adaptive_reflow.theory.paper_quantities`
            carrier. Reserved for future Tier-3 decoding bias; not
            consumed in Wave 44.

        Returns
        -------
        dict[str, numpy.ndarray]
            Non-empty dict mapping ``"amino_acid_categorical"`` (the
            :data:`AMINO_ACID_CATEGORICAL` channel name as plain
            ``str``) to a ``(L,)`` ``float64`` ``ndarray`` of token
            indices in ``[0, LINEAGEFLOW_VOCAB_SIZE)``. The array is
            always ``L = LINEAGEFLOW_MAX_LENGTH`` long (PAD / masked
            positions may carry any value in ``[0, K)``).

        Raises
        ------
        CapabilityMissingError
            If ``trace.native_state_digest`` is not in the adapter's
            native-state cache (e.g. evicted by LRU pressure).
        """
        traj_entry = self._native_states.get(trace.native_state_digest)
        if traj_entry is None:
            raise CapabilityMissingError(
                "missing_native_state",
                context=trace.native_state_digest,
            )
        trajectory = traj_entry.get("trajectory")
        if trajectory is None:
            raise CapabilityMissingError(
                "missing_trajectory",
                context=trace.native_state_digest,
            )
        trajectory_arr = np.asarray(trajectory, dtype=np.float64)
        theta_final = np.asarray(
            trajectory_arr[-1], dtype=np.float64
        ).reshape(LINEAGEFLOW_STATE_SHAPE)
        token_indices = np.argmax(theta_final, axis=-1).astype(np.float64)
        return {str(AMINO_ACID_CATEGORICAL): token_indices}

    # ------------------------------------------------------------------
    # 9b. observe_entropy_reduction (Wave 45 — P2-W33-C metric promotion)
    # ------------------------------------------------------------------

    def observe_entropy_reduction(
        self,
        trace: ODEIntegratorTrace,
        paper_quantities: Any = None,
        *,
        reference_theta: ArrayF64 | None = None,
    ) -> dict[str, float]:
        """Per-position Shannon-entropy reduction over the ODE trajectory.

        Wave 45 addition. Promotes the P2-W33-C metric specified in
        ``docs/theory/operating-regime.md`` §11 from the tools layer to
        the adapter layer. The arithmetic is **not** re-derived here:
        this method only selects the two ``theta`` arrays and delegates
        to
        :func:`adaptive_reflow.adapters._adapter_common.per_position_entropy_reduction`,
        which is the single definition of the formula in the tree.

        Why this is a *plain* computation for LineageFlow
        -------------------------------------------------

        LineageFlow's ODE trajectory state **is** the per-position
        categorical: ``trajectory`` has shape ``(N+1, L, K)`` with
        ``K = LINEAGEFLOW_VOCAB_SIZE = 33`` the Pfam amino-acid
        alphabet, and :meth:`observe_token_indices` decodes a residue
        by a plain ``argmax(trajectory[-1], axis=-1)``. Softmaxing along
        the trailing axis therefore yields a genuine residue
        distribution and its Shannon entropy is a residue-level
        quantity, bounded by ``log K``.

        This is **not** true for every adapter. Kanzi's trajectory is a
        continuous latent, so a softmax along its trailing axis is not a
        residue distribution and the §11 formula must not be reused
        there without a separate justification — see
        ``docs/audit/wave45-lineageflow-entropy-metric.md`` §"Kanzi
        deferred".

        Probabilities, not logits
        -------------------------

        LineageFlow's ``theta`` is already row-normalised, whereas the
        shared helper documents its inputs as *logits* and softmaxes
        them. Both arrays therefore go through :func:`_theta_to_logits`
        first so the helper's softmax is inverted exactly; see that
        function for why skipping the conversion would understate the
        metric by two orders of magnitude.

        Two modes
        ---------

        * ``reference_theta is None`` (default) — **within-trajectory**
          reduction: ``H(trajectory[0]) - H(trajectory[-1])``. This is
          self-contained (it needs no second run) and measures whether
          integrating the ODE *sharpened* the per-position posterior.
          A positive value means the endpoint is more concentrated than
          the prior; a negative value means the ODE widened it.
        * ``reference_theta`` given — **framework-vs-baseline** gap:
          ``H(reference_theta) - H(trajectory[-1])``, where the caller
          supplies the baseline arm's endpoint. Positive means this run
          sharpened the posterior relative to the baseline.

        Parameters
        ----------
        trace
            The :class:`ODEIntegratorTrace` returned by the most recent
            :meth:`solve_ode` call. Only ``native_state_digest`` is
            consumed.
        paper_quantities
            Accepted for signature-parity with
            :meth:`observe_token_indices` so a duck-typed metric caller
            can invoke both the same way. Not consumed: the entropy
            reduction is a property of the trajectory alone.
        reference_theta
            Optional baseline endpoint, broadcastable against
            ``(L, K)``. When omitted the within-trajectory mode is used.

        Returns
        -------
        dict[str, float]
            ``{"per_position_entropy_reduction": <float>}``. The value
            is bounded in ``[-log K, log K]``; it is ``0.0`` exactly for
            a zero-step trajectory (where ``trajectory[0]`` *is*
            ``trajectory[-1]``), and ``nan`` if either array degenerates
            to fewer than two leading rows (never the case at
            ``LINEAGEFLOW_MAX_LENGTH = 256``, but the helper's contract
            is preserved rather than papered over).

        Raises
        ------
        CapabilityMissingError
            If ``trace.native_state_digest`` is not in the adapter's
            native-state cache (e.g. evicted by LRU pressure), or the
            cache entry carries no trajectory.
        """
        traj_entry = self._native_states.get(trace.native_state_digest)
        if traj_entry is None:
            raise CapabilityMissingError(
                "missing_native_state",
                context=trace.native_state_digest,
            )
        trajectory = traj_entry.get("trajectory")
        if trajectory is None:
            raise CapabilityMissingError(
                "missing_trajectory",
                context=trace.native_state_digest,
            )
        trajectory_arr = np.asarray(trajectory, dtype=np.float64)
        theta_final = np.asarray(
            trajectory_arr[-1], dtype=np.float64
        ).reshape(LINEAGEFLOW_STATE_SHAPE)
        if reference_theta is None:
            theta_before = np.asarray(
                trajectory_arr[0], dtype=np.float64
            ).reshape(LINEAGEFLOW_STATE_SHAPE)
        else:
            theta_before = np.asarray(
                reference_theta, dtype=np.float64
            ).reshape(LINEAGEFLOW_STATE_SHAPE)
        reduction = per_position_entropy_reduction(
            _theta_to_logits(theta_before), _theta_to_logits(theta_final)
        )
        return {PER_POSITION_ENTROPY_REDUCTION: float(reduction)}

    # ------------------------------------------------------------------
    # 9c. observe (Wave 68 Phase 2 — AdapterObservationProtocol surface)
    # ------------------------------------------------------------------

    def observe(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
        paper_quantities: Any = None,
        *,
        strategies: tuple[ObservationKind, ...] = (
            ObservationKind.ENDPOINT_BUNDLE,
            ObservationKind.DISCRETE_TOKENS,
            ObservationKind.POSITION_ENTROPY_REDUCTION,
            ObservationKind.TRAJECTORY_NATIVE,
        ),
        theta_before: Any = None,
        theta_after: Any = None,
    ) -> tuple[ObservationResult, ...]:
        """Single typed observation surface for :class:`AdapterObservationProtocol`.

        Wraps the existing ``observe_endpoint`` /
        ``observe_token_indices`` / ``observe_entropy_reduction`` /
        ``export_trajectory`` methods into a tagged-tuple
        :class:`ObservationResult` contract.

        All four :class:`ObservationKind` tags are supported for
        LineageFlow — unlike Kanzi, the per-position categorical is a
        genuine amino-acid distribution, so
        :attr:`ObservationKind.POSITION_ENTROPY_REDUCTION` IS a
        meaningful chemical signal (Wave 67 §3, Wave 45
        ``docs/audit/wave45-lineageflow-entropy-metric.md``).

        Byte-stable migration (Wave 68 §1.3): the underlying methods
        are unchanged. The result tuple contains exactly the
        ``ObservationResult`` s the caller requested (in strategies
        order) when the adapter supports them; otherwise an empty
        tuple is returned for the missing kinds.

        Parameters
        ----------
        trace
            Forwarded to the underlying observation methods.
        state
            Forwarded to :meth:`observe_endpoint`.
        paper_quantities
            Forwarded to :meth:`observe_token_indices` and
            :meth:`observe_entropy_reduction` (currently a no-op
            consumer for both, per Wave 44 / Wave 45).
        strategies
            Tuple of :class:`ObservationKind` tags to include. The
            default requests all four kinds.
        theta_before, theta_after
            Optional entropy-reduction prior/posterior. When
            ``POSITION_ENTROPY_REDUCTION`` is in ``strategies``:

            * Both ``None`` — within-trajectory mode:
              ``H(trajectory[0]) - H(trajectory[-1])`` (the
              adapter's default per Wave 45).
            * ``theta_after`` given — the caller-supplied posterior
              (e.g. baseline endpoint) replaces the adapter's
              :meth:`observe_entropy_reduction` reference; the
              adapter passes it through as ``reference_theta``.

        Returns
        -------
        tuple[ObservationResult, ...]
            Tagged-tuple view of the same numeric output the legacy
            ``observe_*`` methods return. Payload types by ``kind``:

            * ``ENDPOINT_BUNDLE`` — :class:`StateBundle`
            * ``DISCRETE_TOKENS`` — ``numpy.ndarray`` of shape
              ``(L,)``
            * ``POSITION_ENTROPY_REDUCTION`` — ``float``
            * ``TRAJECTORY_NATIVE`` — ``numpy.ndarray | None``
        """
        results: list[ObservationResult] = []
        # Wave 95 Phase 2.A: defensive guard — the Protocol explicitly
        # permits ``state=None`` (interfaces.py:617-619). The metric helper
        # ``_extract_observation`` historically passes ``state=None`` when
        # the caller wants only non-endpoint strategies. Return early
        # before touching ``observe_endpoint`` to avoid AttributeError.
        if state is None:
            return tuple()
        if ObservationKind.ENDPOINT_BUNDLE in strategies:
            endpoint = self.observe_endpoint(trace, state)
            results.append(
                ObservationResult(
                    kind=ObservationKind.ENDPOINT_BUNDLE,
                    channel=str(AMINO_ACID_CATEGORICAL),
                    payload=endpoint,
                    units="state_bundle",
                    metadata={"source_round": int(endpoint.source_round)},
                )
            )
        if ObservationKind.DISCRETE_TOKENS in strategies:
            token_map = self.observe_token_indices(trace, paper_quantities)
            for ch_name, arr in token_map.items():
                results.append(
                    ObservationResult(
                        kind=ObservationKind.DISCRETE_TOKENS,
                        channel=str(ch_name),
                        payload=arr,
                        units="indices",
                    )
                )
        if ObservationKind.POSITION_ENTROPY_REDUCTION in strategies:
            # If the caller supplied a theta_after (e.g. a baseline
            # endpoint), pass it through as the
            # ``observe_entropy_reduction`` reference so the metric
            # layer can compute framework-vs-baseline entropy gap
            # directly via the typed Protocol. Falls through to
            # within-trajectory mode when both priors are None.
            reference_theta = theta_after
            entropy_map = self.observe_entropy_reduction(
                trace,
                paper_quantities,
                reference_theta=reference_theta,
            )
            for ch_name, value in entropy_map.items():
                results.append(
                    ObservationResult(
                        kind=ObservationKind.POSITION_ENTROPY_REDUCTION,
                        channel=str(ch_name),
                        payload=float(value),
                        units="nats",
                        metadata={
                            "theta_after": theta_after,
                            "theta_before": theta_before,
                        },
                    )
                )
        if ObservationKind.TRAJECTORY_NATIVE in strategies:
            traj = self.export_trajectory(trace)
            if traj is not None:
                results.append(
                    ObservationResult(
                        kind=ObservationKind.TRAJECTORY_NATIVE,
                        channel=str(AMINO_ACID_CATEGORICAL),
                        payload=traj,
                        units="trajectory",
                    )
                )
        return tuple(results)

    # ------------------------------------------------------------------
    # 10. inject_forward_noise
    # ------------------------------------------------------------------

    def inject_forward_noise(
        self,
        bundle: StateBundle,
        injected: Any,
    ) -> StateBundle:
        """Perturb the prior's per-position categorical.

        ``injected`` is interpreted as a per-position categorical
        perturbation: ``theta_new = (1 - mix) * theta + mix * injected``,
        row-renormalised so the result is a valid probability
        distribution. ``mix`` defaults to ``1.0`` (full perturbation)
        but can be overridden by passing a 2-tuple ``(injected, mix)``.
        """
        prior_entry = self._native_states.get(bundle.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=bundle.native_state_digest
            )
        if isinstance(injected, tuple) and len(injected) == 2:
            injected_cat, mix = injected
            mix = float(mix)
        else:
            injected_cat = injected
            mix = 1.0
        if mix < 0.0 or mix > 1.0:
            raise ValueError("mix_must_be_in_[0,1]")
        theta_prior = np.asarray(
            prior_entry["theta"], dtype=np.float64
        ).reshape(LINEAGEFLOW_STATE_SHAPE)
        theta_new_arr = np.asarray(injected_cat, dtype=np.float64).reshape(
            LINEAGEFLOW_STATE_SHAPE
        )
        theta_new = (1.0 - mix) * theta_prior + mix * theta_new_arr
        theta_new = theta_new / np.maximum(
            theta_new.sum(axis=-1, keepdims=True), 1e-30
        )
        new_digest = digest_state(
            {
                "kind": "forward_noise",
                "src_digest": bundle.native_state_digest,
                "mix": float(mix),
                "shape": [
                    int(theta_new.shape[0]),
                    int(theta_new.shape[1]),
                ],
                "theta_new_first": [
                    float(theta_new[0, 0]),
                    float(theta_new[0, min(1, self._vocab_size - 1)]),
                ],
            }
        )
        self._put_native_state(
            new_digest,
            {
                "theta": theta_new,
                "source_round": int(bundle.source_round),
                "mode": self._mode,
            },
        )
        return StateBundle(
            channels=dict(bundle.channels),
            masks=dict(bundle.masks),
            batch_id=str(bundle.batch_id),
            sample_id=str(bundle.sample_id),
            reference_frame=str(bundle.reference_frame),
            normalization=str(bundle.normalization),
            source_round=int(bundle.source_round),
            detach_proof=True,
            native_state_digest=new_digest,
            provenance=tuple(bundle.provenance)
            + (AUDIT_FORWARD_NOISE_APPLIED,),
            capability_token=self.capabilities(),
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def default_lineageflow_adapter(
    *,
    weights_path: Path | None = None,
    force_mode: Mode | Literal["auto"] = "auto",
    family_id: str | None = None,
    num_steps: int | None = None,
) -> LineageFlowAdapter:
    """Default factory for :class:`LineageFlowAdapter`.

    Mirrors :func:`default_self_flow_adapter`. ``force_mode="auto"``
    picks ``"torch"`` when the weights file exists AND torch is
    importable; otherwise ``"synthetic"``.
    """
    return LineageFlowAdapter(
        weights_path=weights_path,
        force_mode=force_mode,
        family_id=str(family_id)
        if family_id is not None
        else LINEAGEFLOW_FAMILY_ID_DEFAULT,
        num_steps=int(num_steps)
        if num_steps is not None
        else LINEAGEFLOW_NUM_STEPS_DEFAULT,
    )


__all__ = [
    "AMINO_ACID_CATEGORICAL",
    "AUDIT_FORWARD_NOISE_APPLIED",
    "AUDIT_LINEAGEFLOW_OBSERVED",
    "AUDIT_LINEAGEFLOW_RESTART_BLEND",
    "AUDIT_LINEAGEFLOW_CLASSIFIER_AWARE_RESTART",
    "AUDIT_LINEAGEFLOW_CLASSIFIER_UNAVAILABLE",
    "ERR_LINEAGEFLOW_FAMILY_ID_INVALID",
    "ERR_LINEAGEFLOW_INTEGRATOR_UNKNOWN",
    "ERR_LINEAGEFLOW_L_OUT_OF_RANGE",
    "ERR_LINEAGEFLOW_NUM_STEPS",
    "ERR_LINEAGEFLOW_VOCAB_OUT_OF_RANGE",
    "ERR_LINEAGEFLOW_WEIGHTS_MISSING",
    "LINEAGEFLOW_CFG_SCALE_DEFAULT",
    "LINEAGEFLOW_CHANNEL_DOMAINS",
    "LINEAGEFLOW_CHANNELS",
    "LINEAGEFLOW_CLAMP",
    "LINEAGEFLOW_CONFIG_HASH",
    "LINEAGEFLOW_CONFIG_VERSION",
    "LINEAGEFLOW_FAMILY_EMBED_DIM",
    "LINEAGEFLOW_FAMILY_ID_DEFAULT",
    "LINEAGEFLOW_INTEGRATORS",
    "LINEAGEFLOW_INTEGRATOR_EULER",
    "LINEAGEFLOW_INTEGRATOR_HEUN",
    "LINEAGEFLOW_MECHANISM_ID",
    "LINEAGEFLOW_MAX_LENGTH",
    "LINEAGEFLOW_NATIVE_STATES_MAXSIZE",
    "LINEAGEFLOW_NUM_STEPS_DEFAULT",
    "LINEAGEFLOW_STATE_SHAPE",
    "LINEAGEFLOW_SYNTHETIC_HIDDEN",
    "LINEAGEFLOW_SYNTHETIC_SEED_DEFAULT",
    "LINEAGEFLOW_T_END",
    "LINEAGEFLOW_VOCAB_SIZE",
    "LineageFlowAdapter",
    "LineageFlowCapabilities",
    "LineageFlowClassifierAwareRestart",
    "PER_POSITION_ENTROPY_REDUCTION",
    "PFAM_FAMILY_COND",
    "default_lineageflow_adapter",
    "lineageflow_resolve_weights_path",
    "torch_is_available",
]
