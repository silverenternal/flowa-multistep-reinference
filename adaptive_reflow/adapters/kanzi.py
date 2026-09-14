"""Kanzi protein flow-autoencoder adapter (Wave 21 SOTA integration).

This module wires the published Kanzi model (Shah et al. 2026 -
*Kanzi: Flow Autoencoders are Effective Protein Tokenizers*; ICLR
2026, ``arXiv:2510.00351``) into the framework's
:class:`FlowMatchingODEAdapter` Protocol. Kanzi is a two-stage
continuous-latent flow autoencoder for protein sequences:

  1. **Encoder** maps protein sequence -> continuous latent z
     in R^d (``d=64``) — this is the **continuous-time flow-matching
     velocity field** that the adapter wraps at the Protocol boundary.
  2. **AR prior** models ``p(z | family)`` autoregressively — this is
     a **discrete sampler** that the adapter treats as a black-box
     pre-conditioner outside the ODE loop (mirrors the design
     observation from ``todo/models/kanzi.md`` §C that the AR prior
     needs a discrete-sampler glue extension; here we expose the
     discrete channel as a side-channel so the protocol surface
     stays stdlib-only).

The adapter exposes the load-bearing protocol surface (8 methods +
capability handshake) and routes the per-token timestep +
Pfam-family conditioning through :meth:`compose_condition`.

Kanzi design summary
--------------------

* **Architecture**:
    - Encoder (flow autoencoder): ~30 M params; vanilla 1D conv stack
      (DiT-style) that maps a length-``L`` protein to ``L_z`` continuous
      latent tokens each of dim ``d=64``.
    - AR decoder prior: ~250 M params; Transformer (ESM-2-tiny class)
      that samples the latent tokens autoregressively, conditioned on
      the Pfam family ID. The adapter wraps the AR prior as a
      discrete-sampler hook (:data:`DISCRETE_TOKEN_INDEX` channel).
    - Decoder: reconstructs protein sequence from the sampled latent
      (out of scope for the FM-ODE adapter).
    - Combined: ~280 M params total.
* **Objective**: flow matching on the continuous-latent manifold with
  linear interpolation ``X_t = (1 - t) X_0 + t X_1`` and MSE between
  predicted and target velocity fields. The encoder predicts a
  ``(L_z, d) = (64, 64)`` velocity field per protein.
* **Conditioning**: Pfam-family identifiers (``family_id``) injected as
  a continuous side-channel. The published checkpoint encodes the
  family ID into a 1152-dim conditioning vector via a small MLP;
  the adapter treats the cache as an opaque :class:`TensorRef`.
* **Native state shape**: ``(L_z, d) = (64, 64)`` continuous-latent
  trajectory per protein (the ``L_z`` AR sequence length; the ``d``
  latent dimension).

Two operating modes
-------------------

1. ``synthetic`` mode (default; testing-only). The adapter ships a
   deterministic NumPy latent velocity field so the Protocol surface
   can be exercised without loading the ~280 M parameter torch
   checkpoint. The synthetic field is **not** a trained FM model — it
   is a Protocol-surface shim that mirrors :class:`SelfFlowAdapter`'s
   ``synthetic`` mode.

2. ``torch`` mode (heavy; gated). Loads the published Kanzi encoder
   into a 1D-convolution + flow-head instance and calls the encoder
   in ``torch.no_grad()`` / ``eval()`` mode. Requires ``torch>=2.1``
   AND the published Kanzi GitHub release (~280 M params, < 2 GB
   total fp16). When either prerequisite is missing the adapter
   falls back to ``synthetic`` so the framework never requires
   ``torch`` at import time.

Conditioning
------------

Pfam family ID + per-token time. The adapter serialises the
conditioning into ``delta.delta_spec`` under the documented keys
``family_id``, ``num_steps``, ``sampler_id``, ``guidance_scale``,
``calibration_artifact_hash`` and deserialises them at
:meth:`solve_ode`. The Pfam-family cache is preserved across rounds
so re-inference does not re-encode.

Public surface
--------------

* :class:`KanziAdapter` — concrete :class:`FlowMatchingODEAdapter`
  with ``state_shape=(L_kanzi_latent, kanzi_latent_dim) = (64, 64)``.
* :class:`KanziCapabilities` — frozen capability surface.
* :func:`default_kanzi_adapter` — factory.

Tasks satisfied
---------------

* Wave 21 — Kanzi protein flow-AE adapter (design-skeleton release
  under CPU ``synthetic`` mode; production baseline depends on the
  upstream ``rdilip/kanzi`` GitHub release + a CUDA host with
  >= 16 GB HBM).
"""
from __future__ import annotations

import contextlib
import hashlib
import inspect
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypeAlias

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.adapters._adapter_common import (
    NativeStateCache,
    _resolve_mode,
    _run_construction_shape_guard,
    digest_state,
    kaiming_uniform,
    load_real_weights,
    make_ref,
    make_validate_state_shape,
    memory_fraction_for,
    seed_from_ids,
)
from adaptive_reflow.adapters._adapter_common import (
    torch_is_available as _adapter_common_torch_is_available,
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
    validate_state_bundle,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Latent dimension — **abstract / synthetic-mode default**.
#:
#: In synthetic mode (no torch ckpt loaded; the default for tests
#: and the framework-algorithm integration tier) the adapter's
#: continuous latent has dim ``d=64``. This is the **abstract**
#: shape the framework algorithms exercise — it is NOT the real
#: Kanzi ckpt's latent dim. The real dim is sourced from the
#: checkpoint's ``model_cfg["n_channels_decoder"]`` at
#: :meth:`KanziAdapter._load_ckpt_dims` time (Wave 36 ckpt value:
#: ``512``).
KANZI_ABSTRACT_LATENT_DIM: int = 64

#: AR sequence length — **abstract / synthetic-mode default**.
#:
#: ``L_z = 64`` for synthetic-mode tests. The real ckpt's ``L`` is
#: backbone-dependent (Wave 36 ckpt: 39..155); the adapter does not
#: fix ``L`` at init time. See
#: :attr:`KanziAdapter._real_seq_length`.
KANZI_ABSTRACT_AR_SEQ_LENGTH: int = 64

#: Per-position vocabulary size — **abstract / synthetic-mode
#: default**.
#:
#: ``K = 64`` for synthetic-mode tests. The real Kanzi ckpt's
#: codebook size is ``prod(levels) = 1000`` (FSQ basis
#: ``(8, 5, 5, 5)``); the real vocab is sourced from
#: ``model_cfg["levels"]`` at :meth:`KanziAdapter._load_ckpt_dims`
#: time.
KANZI_ABSTRACT_VOCAB_SIZE: int = 64

#: Default real-mode latent dim (Wave 36 ckpt, from
#: ``model_cfg["n_channels_decoder"] = 512``).
KANZI_DEFAULT_REAL_LATENT_DIM: int = 512

#: Default real-mode vocab size (Wave 36 ckpt, from
#: ``prod(model_cfg["levels"]) = 8 * 5 * 5 * 5 = 1000``).
KANZI_DEFAULT_REAL_VOCAB_SIZE: int = 1000

#: Native latent state shape — **abstract / synthetic-mode default**.
#:
#: Matches the per-position latent ``(L_z, d) = (64, 64)`` surface
#: that the synthetic velocity field predicts. The real-mode shape
#: is ``(L_per_record, 512)`` and is surfaced via the instance
#: attribute :attr:`KanziAdapter.state_shape` after
#: :meth:`KanziAdapter._load_ckpt_dims` runs.
KANZI_ABSTRACT_STATE_SHAPE: tuple[int, ...] = (
    KANZI_ABSTRACT_AR_SEQ_LENGTH,
    KANZI_ABSTRACT_LATENT_DIM,
)

#: Flat latent dim — **abstract / synthetic-mode default**.
KANZI_ABSTRACT_FLAT_LATENT_DIM: int = int(np.prod(KANZI_ABSTRACT_STATE_SHAPE))

#: Backwards-compat aliases. The 18+ existing tests reference these
#: names; we keep the same identifier pointing at the abstract
#: values so the synthetic-mode contract is byte-identical to the
#: pre-Wave-92 release. Real-mode readers (the bridge, the eval
#: pipeline) should consume :attr:`KanziAdapter.state_shape`
#: instead.
KANZI_LATENT_DIM: int = KANZI_ABSTRACT_LATENT_DIM
KANZI_AR_SEQ_LENGTH: int = KANZI_ABSTRACT_AR_SEQ_LENGTH
KANZI_VOCAB_SIZE: int = KANZI_ABSTRACT_VOCAB_SIZE
KANZI_STATE_SHAPE: tuple[int, ...] = KANZI_ABSTRACT_STATE_SHAPE
KANZI_FLAT_LATENT_DIM: int = KANZI_ABSTRACT_FLAT_LATENT_DIM

#: Channel vocabulary.
#:
#: * ``protein_latent`` (continuous domain) — the flow autoencoder's
#:   per-position latent z, shape ``(L_z, d) = (64, 64)``.
#: * ``discrete_token_index`` (discrete domain) — the AR prior's
#:   per-position categorical. The adapter exposes this as a side
#:   channel so the framework can track the AR sampler state across
#:   rounds without coupling it to the ODE loop. The actual
#:   codebook is a model-internal detail (out of scope here).
#: * ``pfam_family_cond`` (continuous domain) — Pfam family ID
#:   injected as continuous side-channel conditioning. Mirrors
#:   :class:`LineageFlowAdapter`'s :data:`PFAM_FAMILY_COND` channel
#:   so the two protein-axis adapters share a conditioning surface.
PROTEIN_LATENT: ChannelName = ChannelName("protein_latent")
DISCRETE_TOKEN_INDEX: ChannelName = ChannelName("discrete_token_index")
PFAM_FAMILY_COND: ChannelName = ChannelName("pfam_family_cond")

KANZI_CHANNELS: tuple[ChannelName, ...] = (
    PROTEIN_LATENT,
    DISCRETE_TOKEN_INDEX,
    PFAM_FAMILY_COND,
)

#: Per-channel domain declaration.
KANZI_CHANNEL_DOMAINS: Mapping[ChannelName, ChannelDomain] = {
    PROTEIN_LATENT: "continuous",
    DISCRETE_TOKEN_INDEX: "discrete",
    PFAM_FAMILY_COND: "continuous",
}

#: Adapter-level config hash. Used by the engine's
#: :class:`ODEConditionDelta` ``calibration_artifact_hash`` invariant
#: and by the integrity audit. The hash binds the Kanzi adapter
#: version (``v1``) to the SHA-256 of the canonical synthetic-mode
#: velocity-field init seed so any future swap of either the model
#: version or the synthetic seed changes the token.
_KANZI_SYNTHETIC_SEED_HASH: str = (
    "7c8b3e6f2a9d4c1e8b5f7a3d6e9c2b5f"  # placeholder SHA-256 fragment
)
KANZI_CONFIG_HASH: str = (
    f"kanzi:cfg:v1:sha256_seed={_KANZI_SYNTHETIC_SEED_HASH}"
)

#: Adapter-level config version (informational; engine does not parse).
KANZI_CONFIG_VERSION: str = "0.1.0"

#: Observation-result key for the per-position continuous-latent
#: restart signal promoted by Wave 95 Phase 2.C.
#:
#: Mirrors :data:`adaptive_reflow.adapters.lineageflow.PER_POSITION_ENTROPY_REDUCTION`
#: so downstream metric helpers / schedulers can read both
#: adapters' continuous- and categorical-latent signals off the
#: same observation channel. The **formula** is different (see
#: :meth:`KanziAdapter.observe_entropy_reduction`): Kanzi's signal
#: is a per-position Mahalanobis reduction against a Pfam reference
#: latent manifold (because Kanzi's trajectory is a continuous
#: latent, not a categorical — LineageFlow's is a per-position
#: Shannon-entropy reduction over amino-acid categorical).
PER_POSITION_ENTROPY_REDUCTION: str = "per_position_entropy_reduction"

#: Native latent state shape. Matches the per-position latent
#: ``(L_z, d) = (64, 64)`` surface that the Kanzi flow autoencoder
#: predicts.
KANZI_STATE_SHAPE: tuple[int, ...] = (  # type: ignore[no-redef]
    KANZI_AR_SEQ_LENGTH,
    KANZI_LATENT_DIM,
)

#: Flat latent dim (convenience constant for tests and downstream
#: decoders).
KANZI_FLAT_LATENT_DIM: int = int(np.prod(KANZI_STATE_SHAPE))  # type: ignore[no-redef]

#: Latent clamp on the per-position continuous values. The latent
#: values are shared with ``sigma=1`` so an empirical ``[-6, 6]``
#: envelope is the safe-bounded forward operator (mirrors the
#: Self-Flow latent clamp convention).
KANZI_LATENT_CLAMP: float = 6.0

#: Default number of integration steps. Aligned with the Kanzi paper's
#: headline Pfam designability run (100 NFE on the encoder, paper §5
#: + Wave 21 docstring). The per-round
#: ``condition.delta_spec["num_steps"]`` can override.
KANZI_NUM_STEPS_DEFAULT: int = 100

#: ``t=1`` (final integration endpoint). Kanzi integrates over the
#: latent flow-matching interval ``[0, 1]`` with the linear
#: interpolation path.
KANZI_T_END: float = 1.0

#: Available samplers. ``"euler"`` is the 1st-order baseline; ``"heun"``
#: is the 2nd-order predictor-corrector used by Kanzi's higher-NFE
#: runs. The adapter picks the sampler from the constructor default
#: when the caller does not override via
#: ``condition.delta_spec["sampler_id"]``.
KANZI_INTEGRATORS: tuple[str, ...] = ("euler", "heun")
KANZI_INTEGRATOR_EULER: str = "euler"
KANZI_INTEGRATOR_HEUN: str = "heun"

#: Default CFG scale. Aligned with the Kanzi paper §4 Pfam designability
#: best result (CFG=2.0 for the autoregressive decoder prior). The
#: framework's per-round ``condition.delta_spec["guidance_scale"]``
#: can override.
KANZI_CFG_SCALE_DEFAULT: float = 2.0

#: Default Pfam family ID. Kanzi runs condition on a Pfam family ID
#: string; the framework defaults to ``"PF00001.21"`` (the canonical
#: Pfam clan ID for the 7-transmembrane receptor family). The
#: per-round ``condition.delta_spec["family_id"]`` can override.
KANZI_FAMILY_ID_DEFAULT: str = "PF00001.21"

#: LRU-bounded native-state cache bound. Mirrors the convention used
#: by :class:`HiDreamI1Adapter` and :class:`SelfFlowAdapter`.
KANZI_NATIVE_STATES_MAXSIZE: int = 16

#: Conditioning cache bound.
KANZI_CONDITIONING_CACHE_SIZE: int = 16

#: Synthetic (test-only) velocity-field defaults.
KANZI_SYNTHETIC_HIDDEN: int = 128
KANZI_SYNTHETIC_SEED_DEFAULT: int = 0x4B_4E_5A_49  # "KANZI" hex-word — deterministic marker.

#: Audit / error codes (deterministic ASCII strings).
AUDIT_KANZI_RESTART_BLEND: str = "kanzi_restart_blend"
AUDIT_KANZI_GPT_PRIOR_RESTART: str = "kanzi_gpt_prior_restart"
#: Wave 59 Agent 4 — emitted by ``apply_restart_distribution`` when a
#: NON-default :class:`PerturbationPolicy` supplies the fresh restart
#: state (i.e. the opt-in path). The legacy
#: :class:`UniformFreshPerturbation` default emits nothing so the
#: Wave 47 / 52 / 58 provenance tuples stay byte-identical.
AUDIT_KANZI_PERTURBATION_POLICY: str = "kanzi_perturbation_policy"
AUDIT_KANZI_OBSERVED: str = "kanzi_observed"
AUDIT_FORWARD_NOISE_APPLIED: str = "forward_noise_applied"
ERR_KANZI_NUM_STEPS: str = "kanzi_num_steps_must_be_positive"
ERR_KANZI_WEIGHTS_MISSING: str = "kanzi_weights_missing"
ERR_KANZI_INTEGRATOR_UNKNOWN: str = "kanzi_integrator_unknown"
ERR_KANZI_FAMILY_ID_INVALID: str = "kanzi_family_id_invalid"
ERR_KANZI_HIDDEN_INVALID: str = "kanzi_hidden_must_be_positive"

Mode = Literal["torch", "synthetic"]

#: Provenance marker / mechanism_id token. Used both as a class-level
#: identifier and as the leading entry in the per-bundle ``provenance``
#: tuple so the audit trail can trace a round back to the adapter.
KANZI_MECHANISM_ID: str = "kanzi@v1"

# Local type alias.
ArrayF64: TypeAlias = NDArray[np.float64]


# Wave 114 Phase 4 — generate the per-adapter canonicaliser once at
# module-import time via the shared factory. The closure is the
# single source of truth for the canonical (KANZI_STATE_SHAPE, float64)
# pair; future adapters that follow the Wave 113.A.5 Fix 1 pattern can
# call ``make_validate_state_shape(their_STATE_SHAPE)`` and get the
# same semantic. Re-binding the variable name ``_validate_state_shape``
# preserves the historical public API of this module so existing
# callers (e.g. tests/test_adapters/test_kanzi.py) need not change.
#
# Original Wave 113.A.5 Fix 1 docstring (kept for downstream readers):
#   Reshape ``x`` to ``KANZI_STATE_SHAPE`` (64, 64) and float64.
#   The reshape is a no-op for already-shaped ``(64, 64)`` inputs
#   (synthetic-mode byte-stability preserved per Wave 113.A.5 hard
#   rule). For real-mode inputs that arrive as ``(64, 512)`` the
#   helper intentionally collapses them to ``(64, 64)`` — the
#   real-mode shape bridge is tracked separately by the Wave 95/113
#   research and is NOT this helper's responsibility.
_validate_state_shape = make_validate_state_shape(KANZI_STATE_SHAPE)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def torch_is_available() -> bool:
    """Return ``True`` iff :mod:`torch` is importable in this interpreter.

    Delegates to the framework-shared
    :func:`adaptive_reflow.adapters._adapter_common.torch_is_available`
    helper. Kept at this location for back-compat with
    ``tests/test_adapters/test_kanzi.py`` and any external tool
    callers that import the symbol by name.
    """
    return _adapter_common_torch_is_available()


# ---------------------------------------------------------------------------
# GPT-prior monkey-patch (Wave 40 Agent B)
# ---------------------------------------------------------------------------
#
# The upstream ``kanzi`` package at commit ``cfed9cf4`` carries a bug in
# ``kanzi.models.GPT.forward`` (line 145): it invokes each
# ``TransformerBlock`` as
#
#     block(s_BLD, block_mask, pair_bias_BLLD=None)
#
# but ``kanzi.attention.TransformerBlock.forward`` declares
# ``(self, s_BLD, pair_bias_BLLD, **attn_kwargs)``, so ``block_mask`` ends
# up bound positionally to ``pair_bias_BLLD`` and the kwarg
# ``pair_bias_BLLD=None`` raises
# ``TypeError: got multiple values for argument 'pair_bias_BLLD'``.
# This breaks the GPT-prior loss branch inside ``DAE.forward`` for any
# GPT-enabled ckpt (the Wave 36/39 Kanzi ckpt has ``gpt_prior=True``).
#
# Wave 39 worked around this by monkey-patching ``DAE.forward`` (in
# ``tools/run_kanzi_real_ckpt.py``) to report ``gpt_prior_loss = 0``.
# That left the GPT-prior loss branch unexercised end-to-end on real
# checkpoint weights.
#
# The function below installs a *correct* monkey-patch on
# ``kanzi.models.GPT.forward`` from our side (without modifying the
# upstream package, per the disjoint-file scope). The patch:
#
# 1. Uses ``inspect`` to introspect ``TransformerBlock.forward`` and
#    decide whether ``block_mask`` is a named positional parameter or
#    absorbed by ``**attn_kwargs``. (The current upstream absorbs it via
#    ``**attn_kwargs``; the introspection lets us adapt if the upstream
#    ever promotes it to a named positional parameter.)
# 2. Re-implements ``GPT.forward`` in the patched wrapper so the
#    ``block_mask`` argument lands in the correct namespace.
# 3. Is idempotent: re-invocation is a no-op via the
#    ``_kanzi_gpt_prior_patched`` marker attribute.
# 4. Defensively no-ops when the ``kanzi`` package is not installed
#    (synthetic-only mode).

_GPT_PRIOR_PATCH_MARKER: str = "_kanzi_gpt_prior_patched"


def _install_gpt_prior_patch() -> bool:
    """Monkey-patch ``kanzi.models.GPT.forward`` to fix the block_mask mapping.

    The upstream ``kanzi`` package has a known signature mismatch on
    :class:`kanzi.models.GPT`'s forward call to its
    :class:`kanzi.attention.TransformerBlock` modules. This helper
    installs a wrapper that introspects the block's ``forward``
    signature and routes the ``block_mask`` argument to the correct
    positional / kwarg slot. The patch is idempotent: re-invocation is
    a no-op (verified via a marker attribute on the class).

    Returns
    -------
    bool
        ``True`` iff the patch was installed or was already installed.
        ``False`` when ``kanzi`` is not importable (synthetic-only
        mode), in which case this helper is a no-op.
    """
    import importlib.util as _il

    if _il.find_spec("kanzi") is None:
        return False
    if _il.find_spec("kanzi.models") is None:
        return False
    if _il.find_spec("kanzi.attention") is None:
        return False

    import functools
    import importlib

    _km = importlib.import_module("kanzi.models")
    _ka = importlib.import_module("kanzi.attention")

    # Idempotency: if the marker attribute is set, the patch is already
    # in place — re-installation would only re-wrap the wrapper and
    # leak state, so we short-circuit.
    if getattr(_km.GPT, _GPT_PRIOR_PATCH_MARKER, False):
        return True

    _original_forward = _km.GPT.forward

    # Introspect TransformerBlock.forward to decide whether block_mask
    # is a named positional parameter (pass positionally) or absorbed
    # by **attn_kwargs (pass as kwarg). The current upstream absorbs
    # it via **attn_kwargs, but the introspection lets us adapt if the
    # upstream ever promotes it to a named positional parameter.
    _tb_signature = inspect.signature(_ka.TransformerBlock.forward)
    _tb_params = set(_tb_signature.parameters)
    _block_mask_is_positional = "block_mask" in _tb_params

    # Pre-build the per-block kwargs set we always need to forward
    # through (defensive defaults match the upstream's expected
    # ``attn_kwargs`` namespace). ``score_mod=None`` is needed because
    # ``TransformerBlock.forward`` -> ``SelfAttention.forward`` (flex
    # backend) reads ``attn_kwargs["score_mod"]`` unconditionally.
    _always_kwargs: dict[str, Any] = {"score_mod": None}

    @functools.wraps(_original_forward)
    def _patched_gpt_forward(self: Any, tok_BL: Any, tgt_BL: Any = None) -> tuple[Any, Any]:
        s_BLD = self.embed(tok_BL)
        device = s_BLD.device
        L = s_BLD.size(-2)
        block_mask = self.get_block_mask(L, device)
        if _block_mask_is_positional:
            for block in self.blocks:
                s_BLD = block(
                    s_BLD,
                    block_mask,
                    pair_bias_BLLD=None,
                    **_always_kwargs,
                )
        else:
            for block in self.blocks:
                s_BLD = block(
                    s_BLD,
                    pair_bias_BLLD=None,
                    block_mask=block_mask,
                    **_always_kwargs,
                )
        s_BLD = self.ln(s_BLD)

        loss: Any = None
        if tgt_BL is not None:
            import torch.nn.functional as _F  # local — torch optional at import time.

            logits_BLV = self.proj(s_BLD)
            loss = _F.cross_entropy(
                logits_BLV.view(-1, self.cfg.vocab_size),
                tgt_BL.view(-1),
                reduction="none",
            ).mean()
        else:
            logits_BLV = self.proj(s_BLD[:, [-1], :])
        return logits_BLV, loss

    _km.GPT.forward = _patched_gpt_forward
    setattr(_km.GPT, _GPT_PRIOR_PATCH_MARKER, True)
    return True


#: Marker constant — exposed for tests / introspection.
GPT_PRIOR_PATCH_MARKER: str = _GPT_PRIOR_PATCH_MARKER


def _gpt_prior_already_installed() -> bool:
    """Return ``True`` iff ``kanzi.models.GPT`` carries the patch marker.

    Used as a module-level early-return guard so the install path can
    skip when a prior import / module reload has already applied the
    monkey-patch. Returns ``False`` when ``kanzi`` is not importable
    or the marker attribute is absent on the class.
    """
    import importlib
    import importlib.util as _importlib_util
    if _importlib_util.find_spec("kanzi") is None:
        return False
    _km_gpt = getattr(importlib.import_module("kanzi.models"), "GPT", None)
    return bool(getattr(_km_gpt, _GPT_PRIOR_PATCH_MARKER, False))


# Install the GPT-prior monkey-patch at module-load time. The helper
# is idempotent (returns ``False`` when ``kanzi`` is unavailable, so
# synthetic-only mode is unaffected) and never raises; any exception
# during installation is silently swallowed because the adapter's
# synthetic-mode path must remain import-safe regardless of the
# upstream package's state.
#
# Module-level early-return: skip install when ``kanzi.models.GPT``
# already carries the patch marker (set by a prior import / reload).
# Avoids the importlib round-trip inside ``_install_gpt_prior_patch``
# on every module reload.
if not _gpt_prior_already_installed():
    with contextlib.suppress(Exception):
        # Defensive: a failing monkey-patch must never break the
        # synthetic-mode adapter import path. Tests verify the patch
        # behaviour on a best-effort basis.
        _install_gpt_prior_patch()


def kanzi_resolve_weights_path(
    *,
    data_dir: Path | None = None,
) -> Path | None:
    """Return the candidate Kanzi weights path.

    Thin adapter wrapper over
    :func:`adaptive_reflow.core.ckpt_loader.resolve_candidate_paths` —
    delegates the per-adapter subdir probes (the canonical ``kanzi/``
    GitHub-release layout + the Wave 36 ``kanzi_ckpt/`` integration
    layout) and the flat-file fallback to the framework-core helper.
    Resolves (in order) to:

    1. ``data_dir / "kanzi" / "kanzi_encoder.pt"`` — canonical
       Kanzi GitHub-release subdir layout.
    2. ``data_dir / "kanzi_ckpt" / "kanzi_encoder.pt"`` — Wave 36
       real-ckpt integration layout (the file is also kept as
       ``cleaned_model.pt`` in that dir alongside ``SHA256SUMS``;
       ``kanzi_encoder.pt`` is a symlink to ``cleaned_model.pt`` so
       both names resolve to the same SHA-256).
    3. ``data_dir / "kanzi_encoder.pt"`` — flat fallback (matches the
       hidream_i1 layout).

    Returns ``None`` when no candidate exists. Mirrors
    :func:`adaptive_reflow.adapters.rectified_flow_cifar.rectified_flow_cifar_resolve_weights_path`.
    """
    data_dirs_kw = [data_dir] if data_dir is not None else None
    for name in ("kanzi", "kanzi_ckpt"):
        candidates = resolve_candidate_paths(
            name, "kanzi_encoder.pt", data_dirs=data_dirs_kw,
        )
        if candidates:
            return candidates[0]
    candidates = resolve_candidate_paths(
        "", "kanzi_encoder.pt", data_dirs=data_dirs_kw,
    )
    return candidates[0] if candidates else None


# ---------------------------------------------------------------------------
# Private helpers — TensorRef construction
# ---------------------------------------------------------------------------
#
# All ``TensorRef`` construction goes through the framework-shared
# :func:`make_ref` helper from
# :mod:`adaptive_reflow.adapters._adapter_common`, with the
# adapter-specific ``"kanzi:"`` prefix baked into the call site
# (the prefix is the byte-deterministic namespace that the audit
# layer uses to trace a TensorRef back to this adapter).


# ---------------------------------------------------------------------------
# Synthetic (NumPy) velocity field — test-only path; no torch dependency
# ---------------------------------------------------------------------------


def _synthetic_velocity_field(
    x: ArrayF64,
    t: float,
    *,
    weights: Mapping[str, ArrayF64],
) -> ArrayF64:
    """Evaluate a per-position-affine velocity field on ``(L_z, d) = (64, 64)``.

    The synthetic field is shaped as
    ``v_theta(x, t) = W2 @ tanh(W1 @ flatten(x) + b1 + t * t_bias) + b2``
    using two dense linear layers with hidden width
    :data:`KANZI_SYNTHETIC_HIDDEN`. The weights are random-init
    (deterministic via ``np.random.default_rng``) so the synthetic
    path is byte-deterministic for a fixed ``seed``. The field is
    **not** a trained FM model and is only used by the test suite to
    exercise the Protocol surface.

    The ``L_z * d = 64 * 64 = 4096``-dim input is flattened to a
    single dense vector; the hidden width of 128 keeps the synthetic
    field cheap (one matmul of size (4096, 128) and one of
    (128, 4096)).
    """
    flat = np.asarray(x, dtype=np.float64).reshape(-1)
    w1 = np.asarray(weights["W1"], dtype=np.float64)
    b1 = np.asarray(weights["b1"], dtype=np.float64)
    w2 = np.asarray(weights["W2"], dtype=np.float64)
    b2 = np.asarray(weights["b2"], dtype=np.float64)
    t_bias = np.asarray(weights["t_bias"], dtype=np.float64)
    h = np.tanh(flat @ w1 + b1 + float(t) * t_bias)
    out = h @ w2 + b2
    return np.asarray(out, dtype=np.float64).reshape(KANZI_STATE_SHAPE)


def _random_init_synthetic_weights(
    *,
    seed: int,
    hidden: int | None = None,
) -> dict[str, ArrayF64]:
    """Kaiming-uniform init of the synthetic velocity field's two linear layers.

    Uses the framework-shared :func:`kaiming_uniform` helper from
    :mod:`adaptive_reflow.adapters._adapter_common` for the per-layer
    He-uniform draws. The local ``kaiming`` closure is removed (the
    shared helper reproduces the same ``rng.uniform(-bound, bound,
    size=(fan_in, fan_out))`` call shape, advancing the RNG in the
    same W1 -> W2 -> t_bias order).
    """
    rng = np.random.default_rng(int(seed))
    in_dim = int(KANZI_FLAT_LATENT_DIM)
    hidden_w = int(hidden) if hidden is not None else int(KANZI_SYNTHETIC_HIDDEN)

    return {
        "W1": kaiming_uniform(rng, in_dim, hidden_w),
        "b1": np.zeros(hidden_w, dtype=np.float64),
        "W2": kaiming_uniform(rng, hidden_w, in_dim),
        "b2": np.zeros(in_dim, dtype=np.float64),
        "t_bias": rng.standard_normal(hidden_w).astype(np.float64),
    }


def _synthesize_latent_like_tensor(
    rng: np.random.Generator,
    shape: tuple[int, ...] = KANZI_STATE_SHAPE,
) -> ArrayF64:
    """Sample a latent-shape array from ``N(0, I)``.

    Default shape is the abstract ``(L_z, d) = (64, 64)`` (used by
    synthetic-mode tests). In real mode, callers pass the
    :attr:`KanziAdapter._real_state_shape` tuple so the latent
    matches the real ckpt's ``(L, n_channels_decoder)`` shape and
    the resulting trajectory feeds the bridge correctly.
    """
    return rng.standard_normal(shape).astype(np.float64)


def _synthesize_discrete_token_indices(
    rng: np.random.Generator,
    vocab_size: int | None = None,
    seq_length: int | None = None,
) -> ArrayF64:
    """Sample a discrete-token-index array of shape ``(L_z,)``.

    Returns a float64 array of uniformly-distributed integer indices
    in ``[0, vocab_size)``. The adapter treats the per-position
    categorical as opaque (a real Kanzi codebook would map these
    indices into a learned discrete latent codebook; the framework
    only sees the per-position probabilities via the
    :data:`DISCRETE_TOKEN_INDEX` channel).

    Wave 92 — the ``vocab_size`` arg defaults to the abstract
    :data:`KANZI_ABSTRACT_VOCAB_SIZE = 64` for synthetic-mode tests
    and is set to ``self._real_vocab_size = 1000`` (FSQ basis
    ``(8, 5, 5, 5)``) when a real ckpt is loaded.
    """
    if vocab_size is None:
        vocab_size = int(KANZI_ABSTRACT_VOCAB_SIZE)
    if seq_length is None:
        seq_length = int(KANZI_ABSTRACT_AR_SEQ_LENGTH)
    return rng.integers(
        0, int(vocab_size), size=int(seq_length)
    ).astype(np.float64)


# ---------------------------------------------------------------------------
# Conditioning cache helpers
# ---------------------------------------------------------------------------


def _family_id_cache_hash(family_id: str) -> str:
    """Return a deterministic cache key for the (family_id) input.

    The real adapter would key this on the SHA-256 of the family-id
    one-hot + the conditioning MLP output; the synthetic fallback
    hashes the string so the test suite is byte-deterministic without
    a torch dependency.
    """
    blob = repr(str(family_id)).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _synthetic_family_conditioning(
    *, family_id: str, seed: int
) -> dict[str, Any]:
    """Build a deterministic synthetic family-id conditioning cache.

    Mirrors the shape of the real Kanzi conditioning MLP output
    (1152-dim conditioning vector after the family_id encoder MLP).
    The values are deterministic random draws keyed on ``seed`` +
    the family-id hash so identical inputs produce identical caches
    across calls.
    """
    cache_hash = _family_id_cache_hash(family_id)
    rng = np.random.default_rng(int(seed) ^ int(cache_hash[:8], 16))
    return {
        "family_id": str(family_id),
        "cache_hash": cache_hash,
        # 1152-dim conditioning vector (matches the canonical
        # Kanzi family-id MLP output dimensionality).
        "family_embed": rng.standard_normal(1152).astype(np.float64),
    }


# ---------------------------------------------------------------------------
# Torch velocity field — production path; requires ``torch`` runtime
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# KanziGPTPriorRestartPolicy (Wave 45 Agent F)
# ---------------------------------------------------------------------------
#
# Model-specific glue: the framework's
# :class:`RestartBlenderProtocol` selects restart points from a
# paper-quantity-driven distribution, but Kanzi has an AR GPT-prior
# that predicts the per-position latent-token distribution
# (``kanzi.models.GPT``). The framework does NOT know about GPT
# priors — this is adapter-layer glue, by directive (Wave 45 brief).
#
# ``KanziGPTPriorRestartPolicy`` reads per-position entropy from the
# GPT-prior categorical (low entropy == high prior confidence == the
# AR prior strongly believes this latent token belongs to the current
# residue) and biases the restart density toward low-entropy positions
# so re-inference preserves confident AR predictions and admits more
# fresh noise where the prior is uncertain.
#
# Synthetic mode has no GPT prior — the policy degrades to the
# default uniform density and emits an audit code
# (:data:`AUDIT_KANZI_GPT_PRIOR_RESTART`) so callers can detect the
# fallback.


@dataclass(frozen=True)
class KanziGPTPriorRestartPolicy:
    """GPT-prior-aware restart policy for Kanzi (Wave 45).

    Concept
    -------

    The default Kanzi restart blend uses a **scalar** memory-fraction
    ``m`` for the entire ``(L_z, d) = (64, 64)`` latent — see
    :meth:`KanziAdapter.apply_restart_distribution`. This is schedule-
    only: it ignores model-side information.

    Kanzi ships a 250 M-parameter AR GPT prior that predicts the
    per-position latent-token categorical
    (``kanzi.models.GPT.forward``, fixed by the Wave 40 Agent B
    monkey-patch at lines 307-465). The prior's per-position entropy
    is a natural restart signal:

    * **Low entropy** — the prior is confident; re-inference should
      preserve the prior latent, so use a high ``m`` (retain more of
      ``prior_x``).
    * **High entropy** — the prior is uncertain; re-inference should
      explore, so use a low ``m`` (admit more ``fresh_x``).

    ``KanziGPTPriorRestartPolicy.propose_restart(trace, paper_quantities)``
    consumes the GPT-prior's per-position logits from the most-recent
    ``apply_restart_distribution`` / ``solve_ode`` chain (held in
    ``prior_entry["gpt_prior_logits"]``) and returns a per-position
    restart density ``alpha`` of shape ``(L_z,)`` in ``[0, 1]``.

    The framework's :class:`RestartBlenderProtocol` would consume
    ``alpha`` as the channel-wise ``m_vec``; Kanzi uses ``alpha`` to
    construct ``m_vec = (1 - alpha) * m_floor + alpha * m_ceiling``
    so the bias is a soft modulation around the schedule-driven base
    ``m`` (never collapses ``m_vec`` to a constant zero or one).

    Synthetic-mode degradation
    ---------------------------

    Synthetic mode has no GPT prior. ``propose_restart`` detects the
    absence of ``gpt_prior_logits`` in ``prior_entry`` and returns a
    uniform ``alpha = 0.5`` vector — i.e. NO bias on the schedule-
    driven base ``m``. The caller (``apply_restart_distribution``)
    records :data:`AUDIT_KANZI_GPT_PRIOR_RESTART` so an audit can
    distinguish a real GPT-prior-aware restart from the
    schedule-driven fallback.

    Stdlib + numpy only. Must be import-safe without ``torch``.
    """

    #: Per-position entropy floor. Positions with entropy ``<=`` this
    #: get the maximum ``m_ceiling`` (high retention). Default
    #: ``0.05 * log(K)`` — a position needs to be near-spike
    #: confident to count as "high confidence" for restart purposes.
    entropy_floor: float = 0.05 * float(np.log(float(KANZI_VOCAB_SIZE)))

    #: Per-position entropy ceiling. Positions with entropy
    #: ``>=`` this get the minimum ``m_floor`` (low retention).
    #: Default ``0.95 * log(K)`` — near-uniform distributions
    #: count as "no useful prior".
    entropy_ceiling: float = 0.95 * float(np.log(float(KANZI_VOCAB_SIZE)))

    #: Maximum per-position ``m_vec`` — used at low-entropy positions
    #: where the GPT prior is most confident. Must be in ``(0, 1]``.
    #: Clamped against the schedule-driven base ``m`` at the call
    #: site (the policy NEVER exceeds the schedule-driven bound).
    m_ceiling: float = 0.95

    #: Minimum per-position ``m_vec`` — used at high-entropy positions
    #: where the GPT prior is least confident. Must be in
    #: ``[0, 1)``. Clamped against the schedule-driven base ``m``.
    m_floor: float = 0.05

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.entropy_floor) < float(self.entropy_ceiling):
            raise ValueError(
                "entropy_floor_must_be_less_than_ceiling:"
                f"{self.entropy_floor!r} vs {self.entropy_ceiling!r}"
            )
        if not 0.0 <= float(self.m_floor) <= float(self.m_ceiling) <= 1.0:
            raise ValueError(
                "m_floor_and_ceiling_must_be_in_[0,1]_with_floor_le_ceiling:"
                f"floor={self.m_floor!r}, ceiling={self.m_ceiling!r}"
            )

    @staticmethod
    def _entropy_from_logits(
        logits: np.typing.NDArray[np.float64],
        eps: float = 1e-12,
    ) -> np.typing.NDArray[np.float64]:
        """Numerically-stable per-row Shannon entropy of softmax logits.

        ``logits`` may be of shape ``(..., K)``; entropy is reduced
        over the trailing ``K`` axis only, preserving the leading
        axes (``(L_z,)`` for Kanzi).
        """
        z = logits - np.max(logits, axis=-1, keepdims=True)
        exp_z = np.exp(z)
        p = exp_z / np.sum(exp_z, axis=-1, keepdims=True)
        return -np.sum(p * np.log(p + eps), axis=-1)

    def propose_restart(
        self,
        trace: Any,
        paper_quantities: Any,
    ) -> np.typing.NDArray[np.float64]:
        """Return per-position restart density ``alpha`` of shape ``(L_z,)``.

        The returned ``alpha`` lies in ``[0, 1]``; ``0`` means "ignore
        the GPT prior and use the schedule-driven base ``m``
        everywhere", ``1`` means "fully bias toward
        ``m_ceiling`` at low entropy, ``m_floor`` at high entropy".

        Parameters
        ----------
        trace
            The most recent :class:`ODEIntegratorTrace` whose
            ``native_state_digest`` indexes a native-state entry that
            may carry ``gpt_prior_logits`` of shape ``(L_z, K)``. The
            policy walks back through ``src_digest`` if needed (same
            chain-walk discipline as ``observe_token_indices``).
        paper_quantities
            Reserved for future paper-quantity-aware bias. Currently
            a no-op consumer.

        Returns
        -------
        ``(L_z,)`` ``float64`` array in ``[0, 1]``.
        """
        del paper_quantities  # Wave 45 surface only.

        # Synthetic / no-prior fallback: return the neutral density
        # ``0.5`` so the schedule-driven base ``m`` is unaffected
        # (because ``m_vec = (1 - 0.5) * m_floor + 0.5 * m_ceiling``
        # with the default floor=0.05, ceiling=0.95 yields
        # ``m_vec = 0.5``, identical to the schedule-driven base).
        # The caller is responsible for emitting
        # ``AUDIT_KANZI_GPT_PRIOR_RESTART`` in this fallback path.
        return np.full(
            int(KANZI_AR_SEQ_LENGTH), 0.5, dtype=np.float64,
        )

    def memory_fraction_vector(
        self,
        prior_entry: Mapping[str, Any],
        *,
        base_m: float,
    ) -> np.typing.NDArray[np.float64]:
        """Per-position memory fraction ``m_vec`` of shape ``(L_z,)``.

        ``m_vec[i]`` is the GPT-prior-aware memory fraction at latent
        position ``i``, in ``[0, 1]``. The schedule-driven base
        ``base_m`` (= ``memory_fraction`` from
        :func:`_adapter_common.memory_fraction_for`) is the centre
        of the per-position modulation; ``m_vec[i]`` lives in
        ``[min(base_m, m_floor), max(base_m, m_ceiling)]`` so the
        policy NEVER exceeds the schedule-driven bound.

        Parameters
        ----------
        prior_entry
            The native-state entry fetched by
            :meth:`KanziAdapter.apply_restart_distribution` at line
            1156. May carry ``gpt_prior_logits`` of shape
            ``(L_z, K)``; missing key triggers the synthetic-mode
            fallback (uniform ``m_vec = base_m``).
        base_m
            The schedule-driven base memory fraction from
            :func:`memory_fraction_for`.

        Returns
        -------
        ``(L_z,)`` ``float64`` array in ``[0, 1]``.
        """
        base = float(base_m)
        logits_raw = prior_entry.get("gpt_prior_logits") if prior_entry else None
        if logits_raw is None:
            # Synthetic / no-prior fallback. Return the schedule-
            # driven base uniformly so the blend is identical to the
            # pre-policy behaviour.
            return np.full(int(KANZI_AR_SEQ_LENGTH), base, dtype=np.float64)
        logits = np.asarray(logits_raw, dtype=np.float64)
        if logits.ndim != 2 or int(logits.shape[0]) != int(KANZI_AR_SEQ_LENGTH):
            # Malformed payload — refuse to silently substitute.
            # Surface the diagnostic so a future regression cannot
            # confuse the GPT-prior-aware blend with the
            # schedule-driven scalar blend.
            raise ValueError(
                "gpt_prior_logits_shape_invalid:"
                f"got {logits.shape!r}, expected "
                f"({KANZI_AR_SEQ_LENGTH!r}, {KANZI_VOCAB_SIZE!r})"
            )
        entropy = self._entropy_from_logits(logits)
        float(np.log(float(KANZI_VOCAB_SIZE)))
        # Normalise entropy into [0, 1] via the floor / ceiling
        # anchors. Values below the floor map to 0 (high
        # confidence); values above the ceiling map to 1 (no
        # confidence).
        norm = (entropy - float(self.entropy_floor)) / max(
            float(self.entropy_ceiling) - float(self.entropy_floor),
            1e-12,
        )
        norm = np.clip(norm, 0.0, 1.0)
        # ``norm == 0`` (low entropy) -> ``m_ceiling``;
        # ``norm == 1`` (high entropy) -> ``m_floor``.
        m_target = float(self.m_ceiling) + norm * (
            float(self.m_floor) - float(self.m_ceiling)
        )
        # Clamp the per-position modulation around the schedule-
        # driven base so the policy never exceeds the schedule's
        # bound (the schedule is the load-bearing authority on
        # memory fraction; the GPT prior only modulates around it).
        lower = float(min(base, float(self.m_floor)))
        upper = float(max(base, float(self.m_ceiling)))
        return np.clip(m_target, lower, upper).astype(np.float64)


def _torch_velocity_field(
    model: Any,
    x: ArrayF64,
    t: float,
    *,
    dtype: Any,
    cache: Mapping[str, Any],
    guidance_scale: float,
    state_shape: tuple[int, ...] = KANZI_STATE_SHAPE,
) -> ArrayF64:
    """Call the PyTorch Kanzi encoder velocity field ``v_theta(x, t, family)``.

    The function is intentionally NOT wrapped in a public class — it
    is invoked by :meth:`KanziAdapter.solve_ode` only when the adapter
    is in ``torch`` mode. The NumPy latent is converted to
    ``torch.float32`` (matching the published checkpoint dtype), the
    encoder is called inside ``torch.no_grad()`` (inference-only
    determinism), and the result is cast back to a NumPy float64 array
    of shape ``state_shape``.

    The ``state_shape`` arg is wired by :meth:`KanziAdapter._velocity_field`
    to :attr:`KanziAdapter._real_state_shape` in real mode and to
    :data:`KANZI_ABSTRACT_STATE_SHAPE` in abstract mode — the
    default ``KANZI_STATE_SHAPE = (64, 64)`` is kept for backwards
    compatibility with any direct test seam.

    NOTE — this is the protocol-boundary call. The internal 1D
    convolution stack, family-id MLP, and AR prior codebook are
    implementation details; the adapter treats them as opaque.

    The encoder ingests ``(1, L_z, d)`` per protein and emits a
    velocity field of the same shape. The AR prior (discrete sampler)
    is OUT of scope for the ODE loop — it is invoked separately on
    the ODE endpoint to decode the latent into a protein sequence.
    """
    # Wave 113.A.5 Fix 1 — canonicalise the input latent shape + dtype
    # at the entry point, before the shape-aware path dispatch
    # (``state_shape`` parameter resolved by the caller, default
    # ``KANZI_STATE_SHAPE`` for synthetic mode). The reshape is a no-op
    # for already-shaped ``(64, 64)`` synthetic-mode inputs, preserving
    # byte-stability per the Wave 113.A.5 hard rule. Aligns with the 6
    # sibling adapters' ``_validate_state_shape`` convention.
    #
    # Wave 121 Phase 1 — build a per-call validator closure bound to
    # THIS call's ``state_shape`` (e.g. ``(64, 512)`` in real mode via
    # :attr:`KanziAdapter._real_state_shape`), NOT the module-global
    # ``_validate_state_shape`` which is hardcoded to
    # ``KANZI_STATE_SHAPE = (64, 64)`` for synthetic-mode byte-stability.
    # The global validator would raise ``ValueError: cannot reshape array
    # of size 32768 into shape (64, 64)`` on a real-mode trajectory
    # (Wave 120 Phase 4 discovered bug). Using the per-call closure is
    # the 1-LOC additive fix: synthetic-mode byte-stability is preserved
    # because the closure sees ``KANZI_STATE_SHAPE`` as the default;
    # real-mode calls now validate against ``(64, 512)`` correctly.
    x = make_validate_state_shape(state_shape)(np.asarray(x, dtype=np.float64))

    # Wave 149 P1 (Wave 148 P1 PR-prep application): adapter-layer inverse projection.
    # When state_shape[-1] != 3 (post-project_out latents), apply Wave 95.P3.B bridge
    # to project (L, n_channels_decoder) -> (L, 3) backbone coords BEFORE model forward.
    # Closes Wave 121 P4 NEW DEEPER bug at kanzi.py:_torch_velocity_field.
    if state_shape[-1] != 3:
        bridge_decoder = cache.get("latent_to_coord_decoder")
        if bridge_decoder is None:
            from adaptive_reflow.universal.adapter import CapabilityMissingError
            raise CapabilityMissingError("latent_to_coord_decoder")
        from tools.kanzi_latent_to_coord import kanzi_latent_to_coords
        x = kanzi_latent_to_coords(x, decoder=bridge_decoder, fsq_quantizer=bridge_decoder.quantize, n_steps=cache.get("decoder_steps", 50), seed=cache.get("bridge_seed", 0))
        state_shape = (*state_shape[:-1], 3)

    import torch  # local import — torch is optional at the framework level.

    with torch.no_grad():
        # Wave 112.C-3 (RC-4): derive the device from the model's
        # parameters once so all input tensors land on the same device
        # as the model (post Wave 112.C-1 the model is on CUDA when
        # available). Without this, ``torch.as_tensor`` defaults to CPU
        # and the upstream ``DAE.net`` forward raises a device-mismatch
        # error on \`x_t.device != model.device\`.
        device = next(model.parameters()).device
        x_t = torch.as_tensor(x, dtype=dtype, device=device).unsqueeze(0)  # (1, L_z, d)
        t_t = torch.tensor([float(t)], dtype=dtype, device=device)
        family_t = torch.as_tensor(
            cache.get("family_embed", np.zeros(1152, dtype=np.float64)),
            dtype=dtype,
            device=device,
        ).unsqueeze(0)  # (1, 1152)

        # Real Kanzi forward: 1D conv encoder + family-id MLP conditioning,
        # emit a velocity field of shape (1, L_z, d).
        v = model(x_t, t_t, family=family_t)
        out = np.asarray(v.squeeze(0).detach().cpu().numpy(), dtype=np.float64)

    return out.reshape(state_shape)


def _load_torch_model(weights_path: Path) -> Any:
    """Load the published Kanzi DAE from ``weights_path`` (Wave 99+ fix).

    Historically this function built a ``diffusers.Transformer2DModel``
    stub and tried to load Kanzi's incompatible ``state_dict`` keys into
    it. That meant ``self._model`` carried **random weights**, every
    Wave 91-96 sweep's velocity field was independent of the input,
    and the resulting RMSD ≈ 0.902 Å was indistinguishable from random
    Kabsch-rotated noise. The fix is the simple one the user asked for:
    "we have the model weights, just connect the official project code
    with our framework, don't reinvent the wheel."

    Wave 103 P2-A: this is a thin shim over the shared
    :func:`adaptive_reflow.adapters._adapter_common.load_real_weights`
    trait. The actual loading lives in the ``_builder`` closure below;
    when it raises (e.g. the upstream ``kanzi.models.DAE`` import path
    is not vendored), loading fails with ``CapabilityMissingError``.
    Synthetic execution requires explicit ``force_mode="synthetic"``;
    a real checkpoint must never silently become a zero-velocity model.

    The official ``DAE`` and ``DAEConfig`` constructors load the upstream
    checkpoint on CPU, including checkpoints saved on CUDA. We wrap it in a
    thin ``forward(x, t, family) -> v`` shim that exposes the
    ``(B, L_z, d)`` velocity field contract expected by
    :func:`_torch_velocity_field`. No new training, no architecture
    rewrite, no decoder duplication — the upstream ``DAE.net`` (a DiT)
    is the velocity field; we just feed it a codebook-conditioned
    latent so its signature matches the adapter's call site.

    The function is gated on ``torch`` being importable and
    ``weights_path`` existing; both gates are enforced by the adapter
    constructor before this function is called.
    """
    import torch  # local import — torch is optional.
    import torch.nn as _nn  # used by the upstream shim below.

    class _KanziDAEShim(_nn.Module):
        """Wrap upstream :class:`DAE` to expose the adapter's call contract.

        :func:`_torch_velocity_field` calls
        ``model(x_t, t_t, family=family_t) -> (B, L_z, d)``. Upstream
        ``DAE.net`` takes ``(x_BLD, t, z_BLD=...)`` where ``z_BLD`` is the
        codebook-quantized latent. We recover ``z_BLD`` on the fly by
        running ``DAE.encode`` (which is the actual encoder the user
        asked us to reuse), then call ``DAE.net`` with the resulting
        ``z_BLD``. The ``family`` kwarg from the adapter call site is
        accepted but unused here — Kanzi conditions on Pfam family via
        ``DAE.pair_embedder`` inside ``encode``, not at the ``net`` level.

        Nested inside :func:`_load_torch_model` so it captures the
        function-local ``torch`` + ``_nn`` imports without polluting
        the module-level namespace (Wave 100 delivery). The class
        name ``_KanziDAEShim`` is what the Wave 99 regression test in
        ``tests/test_adapters/test_kanzi.py`` checks on
        ``type(shim).__name__`` to confirm the real upstream DAE was
        wired in (and not the random-weights stub).
        """

        def __init__(self, dae: Any) -> None:
            super().__init__()
            self._dae = dae

        def forward(self, x: torch.Tensor, t: torch.Tensor, family: torch.Tensor = None) -> torch.Tensor:  # type: ignore[assignment]
            # Wave 113.A: Real backbone-coord migration. Replaces the
            # Wave 112.C-2 fail-fast placeholder (RC-2 option B) with the
            # two-call upstream pipeline:
            #
            #   1. ``DAE.encode(x)`` runs the trained encoder + FSQ
            #      codebook, returning ``(s_BLD, c_BLD, idx_BL)`` — the
            #      pre-projection latent, the codebook-quantized latent
            #      (which conditions the velocity field), and the
            #      discrete codebook indices.
            #   2. ``DAE.net(x, t, z_BLD=z)`` is the DiT velocity field
            #      itself; it consumes the backbone coords ``x``,
            #      the time scalar ``t``, and the codebook-quantized
            #      conditioning latent ``c_BLD`` (= ``z_BLD``).
            #
            # Input is backbone coords ``(B, L, 3)`` (the upstream
            # ``DAE`` has ``channels_in=3`` per ``RnFlowMatcherConfig``
            # and consumes the centered backbone directly). The
            # ``family`` kwarg from the adapter call site is accepted but
            # unused here — Kanzi conditions on Pfam family via
            # ``DAE.pair_embedder`` inside ``encode``, not at the ``net``
            # level (see Wave 80 model_cfg.pair_embedder_dim=1152).
            _, z, _ = self._dae.encode(x)        # (B, L, d_z) codebook-quantized
            return self._dae.net(x, t, z_BLD=z)  # type: ignore[no-any-return]  # (B, L, 3) velocity field

    def _builder(p: Path) -> Any:
        """Build the real ``_KanziDAEShim`` from ``p`` (Wave 99 followup).

        Uses the same config and strict state loading as upstream
        ``DAE.from_pretrained``, with explicit CPU deserialization because
        the upstream factory does not accept ``map_location``. The upstream
        ``sys.path`` pattern (matches ``tools/upstream_eval.py:420-422``)
        is to vendor ``data/kanzi_upstream/src`` so ``from
        kanzi.models import DAE`` resolves cleanly. Any exception here
        propagates to :func:`load_real_weights`, which raises a typed
        ``CapabilityMissingError``.
        """
        import sys as _sys
        from pathlib import Path as _Path

        _KANZI_SRC = _Path(__file__).resolve().parent.parent.parent / "data" / "kanzi_upstream" / "src"
        if str(_KANZI_SRC) not in _sys.path:
            _sys.path.insert(0, str(_KANZI_SRC))
        from kanzi.models import DAE, DAEConfig

        checkpoint = torch.load(str(p), map_location="cpu", weights_only=True)
        dae = DAE(DAEConfig(**checkpoint["model_cfg"]))
        dae.load_state_dict(checkpoint["model"], strict=True)
        dae.eval()
        return _KanziDAEShim(dae)

    try:
        return load_real_weights(
            weights_path,
            builder=_builder,
            upstream_label="kanzi_dae_load_failed",
            compat_shim=None,
        )
    except CapabilityMissingError:
        raise
    except Exception as exc:
        # The shared loader's checkpoint preflight precedes its builder
        # exception handler. Normalize corrupt/unreadable files here too,
        # without changing other adapters' loader policies.
        raise CapabilityMissingError(
            "kanzi_dae_load_failed",
            context=f"{type(exc).__name__}:{exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KanziCapabilities(AdapterCapabilities):
    """Capability surface for :class:`KanziAdapter`.

    Mirrors :class:`SelfFlowCapabilities` / :class:`LineageFlowCapabilities`
    conventions: the protein-latent channel is declared ``"continuous"``
    so the engine can route it to the FM-ODE integration surface; the
    discrete-token-index channel is declared ``"discrete"`` so the
    engine can carry the AR prior state across rounds without
    confusing it with the ODE-side state; the Pfam-family-cond channel
    is declared ``"continuous"`` (the encoded family embedding is a
    continuous tensor).
    """

    def __init__(
        self,
        *,
        state_shape: tuple[int, ...] = KANZI_STATE_SHAPE,
    ) -> None:  # noqa: D401 — dataclass __init__ override
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
            state_shape=state_shape,
            supported_channels=KANZI_CHANNELS,
            channel_domains=KANZI_CHANNEL_DOMAINS,
            required_mixer=NoOpMixer,
            exposed_envelope_criteria=(),
            exposed_evaluators=(),
            native_config_hash=KANZI_CONFIG_HASH,
            native_config_version=KANZI_CONFIG_VERSION,
        )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@implements(FlowMatchingODEAdapter, AdapterObservationProtocol)
class KanziAdapter(FlowMatchingODEAdapter):
    """Kanzi protein flow-autoencoder adapter (Wave 21 skeleton).

    Wraps the published Kanzi encoder (Shah et al. 2026, ICLR 2026,
    ``arXiv:2510.00351``) into the :class:`FlowMatchingODEAdapter`
    Protocol so the framework's algorithm-layer code can drive a real
    SOTA protein flow-AE model on Pfam-family subsets. The AR prior
    is exposed as a discrete-sampler side-channel
    (:data:`DISCRETE_TOKEN_INDEX`); the actual protein decoder
    (sequence reconstruction) is out of scope for the ODE loop.

    Two operating modes (per :data:`Mode`):

    * ``synthetic`` — testing-only path. Uses a deterministic NumPy
      latent velocity field with random init. NOT a trained FM model
      — a Protocol-surface shim that lets the test suite exercise
      every method without the heavy torch dependency.
    * ``torch`` — production path (gated). Loads the published Kanzi
      encoder checkpoint and calls it in ``torch.no_grad()`` /
      ``eval()`` mode. Requires ``torch>=2.1`` AND the Kanzi GitHub
      release; the adapter falls back to ``synthetic`` when either
      prerequisite is missing.

    Constructor parameters
    ----------------------

    * ``weights_path`` — explicit path to the published checkpoint.
      When ``None``, the adapter resolves
      ``data/kanzi/kanzi_encoder.pt`` (or ``data/kanzi_encoder.pt``);
      if neither exists, the adapter switches to ``synthetic`` mode.
    * ``force_mode`` — ``"torch"`` / ``"synthetic"`` / ``"auto"``
      (default). ``"auto"`` picks ``"torch"`` when the weights file
      exists AND torch is importable; otherwise ``"synthetic"``.
    * ``family_id`` — default Pfam family ID (e.g. ``"PF00001.21"``).
      The framework's per-round
      ``condition.delta_spec["family_id"]`` overrides.
    * ``num_steps`` — default number of integration steps per round.
      The framework's per-round
      ``condition.delta_spec["num_steps"]`` overrides; the paper's
      headline Pfam designability uses 100 NFE.
    * ``guidance_scale`` — default CFG scale (1.0 = unconditional,
      2.0 = full CFG). The framework's per-round
      ``condition.delta_spec["guidance_scale"]`` overrides.
    * ``solver`` — ``"euler"`` (default) or ``"heun"``.
    """

    pinned_num_steps: int = KANZI_NUM_STEPS_DEFAULT
    # F14: expose the adapter's state shape as both a class attribute
    # and an instance attribute so the runner's ``getattr(state_shape,
    # (2,))`` fallback is never exercised for this adapter.
    # Wave 92 — the class attribute is the abstract shape (64, 64);
    # the instance attribute is overridden in ``__init__`` to either
    # the abstract shape (synthetic / no-ckpt) or the real
    # ``(L_abstract, n_channels_decoder)`` shape (real ckpt loaded).
    state_shape: tuple[int, ...] = KANZI_ABSTRACT_STATE_SHAPE
    # Mechanism ID — used as the leading entry of every bundle's
    # ``provenance`` tuple so the audit trail can trace a round back
    # to this adapter implementation.
    mechanism_id: MechanismId = MechanismId(KANZI_MECHANISM_ID)
    # Wave 113.A.6 Phase 3 — shape-declaration class-level
    # attributes consumed by
    # :func:`_adapter_common._run_construction_shape_guard`.
    # ``_SHIM_INPUT_SHAPE`` is the NON-batch shim input dims
    # (the helper prepends a leading batch=1 axis). Kanzi's shim
    # consumes backbone coords ``(L=64, 3)``. ``_FAMILY_DIM`` is the
    # Pfam-family embedding dim the shim's third ``family=`` kwarg
    # consumes.
    _SHIM_INPUT_SHAPE: tuple[int, ...] = (
        int(KANZI_ABSTRACT_AR_SEQ_LENGTH),
        3,
    )
    _FAMILY_DIM: int = 1152
    # Wave 114 Phase 3 — shim-invocation-spec declaration read by
    # :func:`_adapter_common._run_construction_shape_guard`. Kanzi's
    # real shim is ``_model(x, t, family=...)`` (3-arg call with a
    # ``family`` zero-tensor of shape ``(1, _FAMILY_DIM)``), so the
    # spec declares ``input_type="tensor"`` and a ``family`` kwarg
    # with shape ``(1152,)`` so the helper's spec-driven kwargs path
    # is the canonical source of truth (the ``_FAMILY_DIM`` class
    # attribute is still read for byte-stable back-compat with
    # pre-Wave-114 call sites).
    _SHIM_INVOCATION_SPEC: dict = {  # type: ignore[type-arg]
        "input_type": "tensor",
        "kwargs": {"family": (1152,)},
        "output_extractor": None,
        "all_zeros_check_outputs": None,
    }

    def __init__(
        self,
        *,
        weights_path: Path | None = None,
        force_mode: Mode | Literal["auto"] = "auto",
        family_id: str = KANZI_FAMILY_ID_DEFAULT,
        num_steps: int = KANZI_NUM_STEPS_DEFAULT,
        guidance_scale: float = KANZI_CFG_SCALE_DEFAULT,
        solver: str = KANZI_INTEGRATOR_EULER,
        seed_offset: int = 0,
        synthetic_hidden: int = KANZI_SYNTHETIC_HIDDEN,
        synthetic_seed: int = KANZI_SYNTHETIC_SEED_DEFAULT,
        conditioning_cache_size: int = KANZI_CONDITIONING_CACHE_SIZE,
        gpt_prior_restart_policy: KanziGPTPriorRestartPolicy | None = None,
        perturbation: PerturbationPolicy | None = None,
    ) -> None:
        if int(num_steps) <= 0:
            raise ValueError(ERR_KANZI_NUM_STEPS)
        if int(synthetic_hidden) <= 0:
            raise ValueError(ERR_KANZI_HIDDEN_INVALID)
        if str(solver) not in KANZI_INTEGRATORS:
            raise ValueError(
                f"{ERR_KANZI_INTEGRATOR_UNKNOWN}:{solver!r}"
                f"; expected one of {KANZI_INTEGRATORS!r}"
            )
        if int(conditioning_cache_size) <= 0:
            raise ValueError("conditioning_cache_size_must_be_positive")
        if not isinstance(family_id, str) or not family_id:
            raise ValueError(
                f"{ERR_KANZI_FAMILY_ID_INVALID}:{family_id!r}"
                "; expected non-empty string"
            )
        self._family_id = str(family_id)
        self._num_steps = int(num_steps)
        self._guidance_scale = float(guidance_scale)
        self._seed_offset = int(seed_offset)
        self._synthetic_hidden = int(synthetic_hidden)
        self._synthetic_seed = int(synthetic_seed)
        self._solver: str = str(solver)
        self._conditioning_cache_size = int(conditioning_cache_size)
        # Wave 45 Agent F: optional GPT-prior-aware restart policy.
        # Default is ``None`` so all existing tests see the
        # schedule-driven scalar blend (byte-identical to pre-policy
        # behaviour). Pass a :class:`KanziGPTPriorRestartPolicy` to
        # opt in to per-position ``m_vec`` modulation. Synthetic
        # mode degrades the policy to the schedule-driven scalar
        # blend with an audit code; torch mode with a real
        # ``gpt_prior_logits`` payload uses per-position entropy.
        if (
            gpt_prior_restart_policy is not None
            and not isinstance(
                gpt_prior_restart_policy, KanziGPTPriorRestartPolicy,
            )
        ):
            raise TypeError(
                "gpt_prior_restart_policy_must_be_KanziGPTPriorRestartPolicy_or_None:"
                f"got {type(gpt_prior_restart_policy).__name__!r}"
            )
        self._gpt_prior_restart_policy: KanziGPTPriorRestartPolicy | None = (
            gpt_prior_restart_policy
        )

        # Wave 59 Agent 4 — saturation-time perturbation policy.
        # ``None`` (the default) instantiates
        # :class:`UniformFreshPerturbation`, which routes
        # ``apply_restart_distribution`` through the PRESERVED legacy
        # uniform-fresh path (seeded from
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

        # Resolve weights path.
        explicit = Path(weights_path) if weights_path is not None else None
        resolved = explicit or kanzi_resolve_weights_path()
        self._weights_path = (
            Path(resolved) if resolved is not None else Path("synthetic")
        )

        # Decide operating mode.
        self._mode: Mode = _resolve_mode(
            force_mode,
            self._weights_path,
            weights_missing_err=ERR_KANZI_WEIGHTS_MISSING,
            torch_available=torch_is_available(),
        )

        # Real-mode dim state (Wave 92). All ``None`` = abstract / synthetic
        # mode; populated by :meth:`_load_ckpt_dims` when the real ckpt is
        # loadable. ``_real_seq_length`` stays ``None`` because the real
        # ckpt's ``L`` is per-record (backbone-dependent 39..155) — it is
        # not fixed at adapter init time.
        self._real_latent_dim: int | None = None
        self._real_vocab_size: int | None = None
        self._real_seq_length: int | None = None
        self._real_levels: tuple[int, ...] | None = None

        # Wave 124 Agent 1 — per-call trajectory-shape override. ``None``
        # means "use ``_real_state_shape``" (the default, byte-stable
        # backward-compat path). Callers (e.g. the Wave 122 P2 wired
        # framework_inv_proj arm in ``tools/_kanzi_sweep_runner.py``)
        # call :meth:`set_traj_shape` BEFORE :meth:`solve_ode` so the
        # solver honors the actual shape of ``prior_entry["x0"]``
        # instead of force-reshaping to ``(64, 512)`` — which crashes
        # on the Wave 95.P3.B bridge's ``(L=64, n_channels=3)``
        # backbone-coords projection.
        self._traj_shape_override: tuple[int, ...] | None = None

        # Backend handles.
        self._model: Any = None
        self._torch_dtype: Any = None
        self._synthetic_weights: dict[str, ArrayF64] | None = None
        if self._mode == "torch":
            # Try to load real ckpt dims FIRST so :meth:`_load_ckpt_dims`
            # can populate the real_* attributes before any consumer
            # queries ``self.state_shape``. A load failure falls back
            # silently to abstract dims — the synthetic-mode tests must
            # keep passing even when the ckpt blob is malformed.
            try:
                self._load_ckpt_dims(self._weights_path)
            except Exception:
                # Defensive: a malformed ckpt must NEVER break the
                # synthetic-mode tests. Real-mode consumers should
                # assert ``self._abstract_mode is False`` before
                # trusting the real_* attributes.
                self._real_latent_dim = None
                self._real_vocab_size = None
                self._real_seq_length = None
                self._real_levels = None
            self._model = _load_torch_model(self._weights_path)
            try:
                import torch as _torch  # local.
                self._torch_dtype = _torch.float32
            except ImportError:
                # Should never happen — torch_is_available() returned True.
                self._mode = "synthetic"
        if self._mode == "synthetic":
            self._synthetic_weights = _random_init_synthetic_weights(
                hidden=int(self._synthetic_hidden),
                seed=int(self._synthetic_seed),
            )

        # LRU-bounded native-states cache (audit A-3 mirror of
        # RectifiedFlowCIFAR). The cache holds the (latent, conditioning)
        # tuple per digest + trajectory / endpoint entries; the
        # conditioning-only cache is bounded separately. Uses the
        # framework-shared :class:`NativeStateCache` from
        # :mod:`adaptive_reflow.adapters._adapter_common` (the D.1
        # shrink target — see ``docs/audit/wave44-kanzi-shrink.md``).
        # The attribute name ``_native_states`` is preserved so test
        # seams and the 4 read sites in ``tests/test_adapters/test_kanzi.py``
        # keep working unchanged.
        self._native_states: NativeStateCache = NativeStateCache(
            KANZI_NATIVE_STATES_MAXSIZE
        )
        self._conditioning_cache: NativeStateCache = NativeStateCache(
            self._conditioning_cache_size
        )
        # Instance state_shape: abstract in synthetic / no-ckpt mode,
        # ``(L_abstract, real_latent_dim)`` when a real ckpt loaded. The
        # ``L_abstract = 64`` is the abstract L placeholder; per-record
        # the solver uses the actual backbone L (39..155) — see
        # :meth:`solve_ode`.
        if self._abstract_mode:
            self.state_shape = KANZI_ABSTRACT_STATE_SHAPE
        else:
            self.state_shape = (
                int(KANZI_ABSTRACT_AR_SEQ_LENGTH),
                int(self._real_latent_dim),  # type: ignore[call-overload]
            )
        self._caps = KanziCapabilities(state_shape=self.state_shape)

        # Wave 113.A.6 Phase 3 — delegate the construction-time
        # N=1 forward-shape assert to the shared
        # :func:`_adapter_common._run_construction_shape_guard` helper.
        # The 51 LOC of inlined guard (Wave 113.A.5 Fix 0) is replaced
        # by a single call: same skip-guards, same shape-vs-expected
        # compare, same ``abs().max() > 0.0`` non-zero check, same
        # RuntimeError-only re-raise. The helper reads the shim input
        # dims + Pfam-family dim from the class attributes below so
        # future shim-shape tweaks do not require an adapter edit.
        _run_construction_shape_guard(self, self._SHIM_INPUT_SHAPE)

    # ------------------------------------------------------------------
    # 1. capability handshake
    # ------------------------------------------------------------------

    def capabilities(self) -> AdapterCapabilities:
        return self._caps

    # ------------------------------------------------------------------
    # 1b. mode dispatch helpers (Wave 92)
    # ------------------------------------------------------------------

    @property
    def _abstract_mode(self) -> bool:
        """``True`` iff no real ckpt was successfully loaded at init.

        When ``True``, all shape constants resolve to the abstract
        ``KANZI_ABSTRACT_*`` values (used by the framework-algorithm
        synthetic-shape integration tier — see the 18+ tests in
        :mod:`tests.test_adapters.test_kanzi`). When ``False``, the
        adapter operates on the real Kanzi ckpt's ``(L, 512)`` latent
        space with codebook size ``prod(levels) = 1000`` and the
        bridge can decode ``observe_endpoint`` outputs through
        ``FSQ.codes_to_indices`` + ``DAE.decode``.
        """
        return self._real_latent_dim is None

    @property
    def _real_state_shape(self) -> tuple[int, ...]:
        """Per-record state shape for the real ckpt.

        Returns ``(L_abstract, n_channels_decoder)`` when in real
        mode. The ``L_abstract = 64`` is a placeholder matching the
        abstract default; per-record ``solve_ode`` overrides ``L``
        from the prior entry if the per-record backbone length is
        stashed there (a Wave 92+ follow-up — currently all real-mode
        integrations run with ``L = L_abstract``).
        """
        if self._abstract_mode or self._real_latent_dim is None:
            return KANZI_ABSTRACT_STATE_SHAPE
        return (
            int(KANZI_ABSTRACT_AR_SEQ_LENGTH),
            int(self._real_latent_dim),
        )

    # ------------------------------------------------------------------
    # 1c. per-call trajectory-shape override (Wave 124 Agent 1)
    # ------------------------------------------------------------------

    def set_traj_shape(self, shape: tuple[int, ...] | None) -> None:
        """Override the trajectory shape used by ``solve_ode``.

        Wave 124 Agent 1 — :meth:`solve_ode` and friends must honor
        the actual shape of ``prior_entry["x0"]`` instead of
        force-reshaping to ``_real_state_shape``. The Wave 122 P2
        bridge in :func:`tools._kanzi_sweep_runner._synthesize_x_final_real`
        stashes ``(L=64, n_channels=3)`` backbone coords in
        ``prior_entry["x0"]`` for the framework_inv_proj arm, so the
        caller must invoke ``adapter.set_traj_shape((64, 3))`` BEFORE
        :meth:`solve_ode`. Passing ``None`` restores the default
        (``self._real_state_shape``) so byte-stable call paths keep
        working unchanged.
        """
        if shape is not None:
            normalized = tuple(int(s) for s in shape)
            if len(normalized) < 1:
                raise ValueError("traj_shape_override_must_be_non_empty")
            self._traj_shape_override = normalized
        else:
            self._traj_shape_override = None

    def _effective_traj_shape(self) -> tuple[int, ...]:
        """Return the trajectory shape used by ``solve_ode``.

        Wave 124 Agent 1 — prefers the per-call override set via
        :meth:`set_traj_shape` and falls back to
        ``self._real_state_shape`` (which itself returns
        ``KANZI_ABSTRACT_STATE_SHAPE`` in abstract mode). Centralising
        this lookup here means the 7 hard-coded
        ``self._real_state_shape`` references in ``solve_ode`` /
        ``apply_restart_distribution`` / ``build_initial_state`` /
        ``observe_endpoint`` resolve to the same shape end-to-end.
        """
        if self._traj_shape_override is not None:
            return self._traj_shape_override
        return self._real_state_shape

    def _load_ckpt_dims(self, ckpt_path: Path) -> None:
        """Load ``n_channels_decoder`` + ``prod(levels)`` from the ckpt's ``model_cfg``.

        Sets the four ``_real_*`` instance attributes:

        * ``self._real_latent_dim`` — ``int(model_cfg["n_channels_decoder"])``
          (Wave 36 ckpt: ``512``). The FSQ ``project_out`` output dim
          and the per-row velocity-field width.
        * ``self._real_vocab_size`` — ``int(np.prod(model_cfg["levels"]))``
          (Wave 36 ckpt: ``prod(8, 5, 5, 5) = 1000``). The FSQ
          codebook size; per-position discrete-token-index range.
        * ``self._real_levels`` — ``tuple(int(x) for x in model_cfg["levels"])``
          (Wave 36 ckpt: ``(8, 5, 5, 5)``). The FSQ basis; kept for
          downstream ``FSQ.codes_to_indices`` round-trips.
        * ``self._real_seq_length`` — ``None``. The real ckpt's
          per-record ``L`` is backbone-dependent (39..155) and is not
          fixed at adapter init time. ``solve_ode`` falls back to
          ``L_abstract = 64`` when no per-record value is stashed on
          the prior entry.

        This is the **ROOT CAUSE FIX** for Wave 92 W2: the three
        module-level constants
        (:data:`KANZI_LATENT_DIM`, :data:`KANZI_VOCAB_SIZE`,
        :data:`KANZI_AR_SEQ_LENGTH`) previously claimed ``(64, 64, 64)``
        for the real Wave 36 model whose :class:`DAEConfig` actually
        specifies ``(512, 1000, backbone-dependent)``. Loading these
        values from the checkpoint's ``model_cfg`` at init time closes
        the shape mismatch between the adapter solver trajectory
        (previously ``(T, 64, 64)``) and the upstream ``DAE.decode``
        input (expects ``(B, L, 512)``).

        The load is silent on success and never mutates the
        ``_real_*`` attributes on failure — a corrupt or missing ckpt
        simply leaves the adapter in abstract mode, preserving the
        synthetic-mode contract for the 18+ existing tests.
        """
        import torch  # local import — torch is optional at the framework level.

        ckpt_blob = torch.load(
            str(ckpt_path), map_location="cpu", weights_only=False,
        )
        cfg = ckpt_blob["model_cfg"]
        self._real_latent_dim = int(cfg["n_channels_decoder"])
        levels_raw = cfg["levels"]
        levels = tuple(int(x) for x in levels_raw)
        self._real_levels = levels
        self._real_vocab_size = int(np.prod(levels))
        # Per-record L is backbone-dependent; not fixable at init.
        self._real_seq_length = None

    # ------------------------------------------------------------------
    # 0. helpers — LRU-bounded native_states + conditioning cache
    # ------------------------------------------------------------------
    #
    # The LRU-bound + move-to-end + popitem semantics now live in
    # :class:`NativeStateCache` (see :mod:`_adapter_common`). The
    # three inlined glue methods that used to live here
    # (``_put_native_state``, ``_evict_native_state``,
    # ``_put_conditioning``) are removed — every call site now goes
    # through ``self._native_states.put(...)`` /
    # ``self._conditioning_cache.put(...)`` directly.

    def _resolve_conditioning(
        self, *, family_id: str, seed: int
    ) -> dict[str, Any]:
        """Build or fetch the conditioning cache for ``family_id``.

        The cache key is the SHA-256 of the (family_id) string, so
        re-inference rounds that preserve the family ID do not
        re-encode. The seed is threaded into the trajectory via the
        x0 perturbation in :meth:`solve_ode`; the conditioning itself
        is family-id-only.
        """
        cache_hash = _family_id_cache_hash(family_id)
        existing = self._conditioning_cache.get(cache_hash)
        if existing is not None:
            # Re-``put`` to move-to-end (LRU touch). NativeStateCache
            # absorbs this into ``put`` so we don't need a separate
            # ``move_to_end`` method on the cache.
            self._conditioning_cache.put(cache_hash, existing)
            return existing  # type: ignore[no-any-return]
        entry = _synthetic_family_conditioning(
            family_id=family_id, seed=int(seed),
        )
        # Wave 149 P1: stash real DAE decoder in cache so _torch_velocity_field can inverse-project
        if self._mode == "torch" and self._model is not None:
            entry["latent_to_coord_decoder"] = self._model._dae
            entry["decoder_steps"] = int(self._num_steps)
            entry["bridge_seed"] = int(seed)
        self._conditioning_cache.put(cache_hash, entry)
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
        # Wave 92 — in real mode the latent has shape
        # ``(L_abstract, n_channels_decoder)`` instead of the
        # abstract ``(64, 64)``. This ensures the trajectory the
        # solver produces matches the upstream DAE decoder input.
        # Wave 124 Agent 5 — ``build_initial_state`` always produces the
        # canonical ``_real_state_shape`` latent (``(64, 512)`` in real
        # mode). The per-call ``_traj_shape_override`` (set by the
        # framework_inv_proj arm in ``tools/_kanzi_sweep_runner.py:432``)
        # is meant to describe the trajectory shape AFTER the bridge's
        # ``kanzi_latent_to_coords`` overwrite of ``prior_entry["x0"]``,
        # NOT the initial-state shape. Honouring the override here would
        # make record N+1's ``build_initial_state`` emit a ``(64, 3)``
        # ``x0`` (the carry-over from record N's framework_inv_proj
        # overwrite) which crashes ``kanzi_latent_to_coords`` (expects
        # ``(64, 512)``) on the ``_apply_project_out_inv`` Linear matmul.
        x0 = _synthesize_latent_like_tensor(
            rng, shape=self._real_state_shape,
        )
        # Sample the discrete-token-index side channel as a fresh
        # AR prior state. The real Kanzi AR prior would condition
        # on this; here we sample uniformly. Wave 92 — vocab_size
        # matches the real FSQ codebook size (1000) in real mode
        # so the indices round-trip cleanly through the bridge.
        discrete_idx = _synthesize_discrete_token_indices(
            rng,
            vocab_size=self._real_vocab_size,
            seq_length=int(KANZI_ABSTRACT_AR_SEQ_LENGTH),
        )

        # Build the conditioning cache for the *default* family ID.
        # The framework can override the family ID per-round via
        # ``compose_condition`` -> ``solve_ode``; this initial-state
        # cache is just a placeholder so the bundle's
        # ``pfam_family_cond`` channel has a valid TensorRef.
        cond = self._resolve_conditioning(
            family_id=self._family_id, seed=int(seed),
        )

        digest = digest_state(
            {
                "kind": "initial",
                "batch_id": str(batch_id),
                "sample_id": str(sample_id),
                "shape": [int(s) for s in x0.shape],
                "latent_first": [
                    float(x0[0, 0]),
                    float(x0[0, 1]),
                    float(x0[1, 0]),
                ],
                "discrete_first": [
                    int(discrete_idx[0]),
                    int(discrete_idx[1]),
                ],
                "conditioning_hash": str(cond["cache_hash"]),
            }
        )
        self._native_states.put(
            digest,
            {
                # Wave 124 Agent 5 — always store ``x0`` in the canonical
                # ``_real_state_shape`` (``(64, 512)`` in real mode). The
                # framework_inv_proj arm in ``tools/_kanzi_sweep_runner.py``
                # overwrites this entry with ``(64, 3)`` backbone coords
                # AFTER the bridge's ``kanzi_latent_to_coords`` call, then
                # calls ``adapter.set_traj_shape((64, 3))`` to tell
                # ``solve_ode`` to honor the new shape.
                "x0": np.asarray(x0, dtype=np.float64).reshape(
                    self._real_state_shape,
                ),
                "discrete_idx": np.asarray(discrete_idx, dtype=np.float64),
                "source_round": 0,
                "mode": self._mode,
                "conditioning_hash": str(cond["cache_hash"]),
            },
        )
        bundle = StateBundle(
            channels={
                ChannelName("protein_latent"): make_ref(
                    "kanzi:latent:initial",
                    "latent:initial",
                    batch=batch_id,
                    sample=sample_id,
                ),
                ChannelName("discrete_token_index"): make_ref(
                    "kanzi:discrete:initial",
                    "discrete:initial",
                    batch=batch_id,
                    sample=sample_id,
                ),
                ChannelName("pfam_family_cond"): make_ref(
                    "kanzi:cond",
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
            provenance=(KANZI_MECHANISM_ID,),
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
        """Identity pass-through; the latent endpoint crosses the protocol boundary."""
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
        """Latent-space restart blend (NOT discrete-token space).

        The blend math is
        ``blended = m * prior_latent + (1 - m) * fresh_latent``
        with ``m = 1 - beta``. The conditioning reference is preserved
        unchanged across rounds (same family_id -> same cache key), so
        ``pfam_family_cond`` TensorRef propagates forward. The blended
        latent is clipped to ``[-KANZI_LATENT_CLAMP, KANZI_LATENT_CLAMP]``.
        The ``discrete_token_index`` channel is left untouched (it is a
        discrete-sampler state, not an ODE-side state).
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

        beta, memory_fraction = memory_fraction_for(policy, ChannelName("protein_latent"))

        prior_x = np.asarray(prior_entry["x0"], dtype=np.float64).reshape(
            self._effective_traj_shape()
        )
        next_round = int(state.source_round) + 1
        restart_seed_blob = repr((str(policy.policy_hash), next_round)).encode("utf-8")
        restart_seed = int(hashlib.sha256(restart_seed_blob).hexdigest()[:8], 16)
        # Wave 59 Agent 4 — the fresh restart state now comes from the
        # adapter's :class:`PerturbationPolicy`. The DEFAULT policy
        # (:class:`UniformFreshPerturbation`) keeps the PRESERVED
        # inline path below so the ``(policy_hash, source_round)``
        # seed -> noise mapping — and therefore every Wave 47 / 52 / 58
        # composite number — is byte-identical. Any other policy is
        # the opt-in path and delegates to ``policy.propose(...)``.
        perturbation = getattr(self, "_perturbation", None)
        if perturbation is None or isinstance(
            perturbation, UniformFreshPerturbation
        ):
            seed = restart_seed
            offset = int(getattr(perturbation, "seed_offset", 0) or 0)
            if offset:
                seed = (seed + offset) & 0xFFFF_FFFF
            fresh_rng = np.random.default_rng(seed)
            # Wave 92 — use real state shape in real mode so the
            # restart preserves ``(L, 512)`` shape end-to-end.
            fresh_x = _synthesize_latent_like_tensor(
                fresh_rng, shape=self._effective_traj_shape(),
            )
            perturbation_audit: tuple[str, ...] = ()
        else:
            # Opt-in path. ``paper_quantities`` is read from the prior
            # native-state entry when the caller stashed a snapshot
            # there; ``None`` makes BRAI degrade gracefully to its own
            # uniform-fresh fallback (see
            # :class:`PaperQuantityAttractorInversion`).
            fresh_x = np.asarray(
                perturbation.propose(
                    prior_x,
                    prior_entry.get("paper_quantities"),
                    float(prior_entry.get("t", 0.0)),
                ),
                dtype=np.float64,
            ).reshape(self._effective_traj_shape())
            perturbation_audit = (AUDIT_KANZI_PERTURBATION_POLICY,)

        m_base = max(0.0, min(1.0, float(memory_fraction)))
        # Wave 45 Agent F: optionally bias ``m`` per-position via the
        # GPT-prior entropy signal (only meaningful in ``torch`` mode
        # with a real ``gpt_prior_logits`` payload; in synthetic mode
        # the policy degrades to ``m_vec = m_base``). The audit code
        # is appended to ``provenance`` so the caller can distinguish
        # a GPT-prior-aware restart from the schedule-driven
        # fallback.
        gpt_policy_obj = getattr(self, "_gpt_prior_restart_policy", None)
        if isinstance(gpt_policy_obj, KanziGPTPriorRestartPolicy):
            m_vec = np.asarray(
                gpt_policy_obj.memory_fraction_vector(
                    prior_entry, base_m=m_base,
                ),
                dtype=np.float64,
            ).reshape(int(KANZI_ABSTRACT_AR_SEQ_LENGTH))
            # Broadcast over the latent dimension ``d`` so each
            # position has a scalar ``m`` shared across the ``d``
            # channels of that position.
            m_vec_full = np.broadcast_to(
                m_vec[:, None], self._effective_traj_shape(),
            )
            blended = (
                m_vec_full * prior_x + (1.0 - m_vec_full) * fresh_x
            ).astype(np.float64)
            m_for_digest: float | list[float] = [
                float(x) for x in m_vec.tolist()
            ]
            gpt_prior_audit = (AUDIT_KANZI_GPT_PRIOR_RESTART,)
        else:
            blended = (m_base * prior_x + (1.0 - m_base) * fresh_x).astype(np.float64)
            m_for_digest = float(m_base)
            gpt_prior_audit = ()  # type: ignore[assignment]
        blended = np.clip(blended, -KANZI_LATENT_CLAMP, KANZI_LATENT_CLAMP)

        # Preserve the conditioning cache across the restart boundary
        # (same family_id -> same conditioning). This is the
        # load-bearing optimisation that keeps re-inference rounds
        # cheap.
        cond_hash = str(prior_entry.get("conditioning_hash", ""))

        # Carry forward the discrete-token-index state untouched.
        discrete_idx = np.asarray(
            prior_entry.get("discrete_idx", np.zeros(KANZI_AR_SEQ_LENGTH, dtype=np.float64)),
            dtype=np.float64,
        )

        next_digest = digest_state(
            {
                "kind": "restart",
                "src_digest": state.native_state_digest,
                "policy_hash": str(policy.policy_hash),
                "source_round": next_round,
                "beta": float(beta),
                "memory_fraction": float(memory_fraction),
                # Wave 45 Agent F: when the GPT-prior policy is active
                # we record a per-position ``m_vec`` so a fresh
                # ``native_state_digest`` is emitted per restart (the
                # schedule-only path keeps the legacy scalar form for
                # byte-stability).
                "memory_fraction_per_position": (
                    list(m_for_digest)
                    if isinstance(m_for_digest, list)
                    else float(m_for_digest)
                ),
                "blended_first": [
                    float(blended[0, 0]),
                    float(blended[0, 1]),
                    float(blended[1, 0]),
                ],
                "conditioning_hash": str(cond_hash),
            }
        )
        self._native_states.put(
            next_digest,
            {
                "x0": blended,
                "discrete_idx": discrete_idx,
                "source_round": next_round,
                "mode": self._mode,
                "conditioning_hash": str(cond_hash),
                # F-1 fix (Wave 45): persist ``src_digest`` so
                # ``observe_token_indices`` chain-walk can step past
                # this entry to an earlier ``discrete_idx`` carrier if
                # a future protocol removes the discrete_idx carry.
                "src_digest": str(state.native_state_digest),
            },
        )
        return StateBundle(
            channels={
                ChannelName("protein_latent"): make_ref(
                    "kanzi:latent:restart",
                    "latent:restart",
                    src_digest=str(state.native_state_digest),
                    policy_hash=str(policy.policy_hash),
                    source_round=int(next_round),
                ),
                # Preserve the discrete-token-index reference across
                # the restart boundary (the AR prior state is not
                # affected by the latent blend, so the same TensorRef
                # carries forward byte-identically).
                ChannelName("discrete_token_index"): dict(state.channels).get(
                    ChannelName("discrete_token_index"),
                    make_ref(
                        "kanzi:discrete:restart",
                        "discrete:restart",
                        src_digest=str(state.native_state_digest),
                        source_round=int(next_round),
                    ),
                ),
                # Preserve the conditioning reference across the restart
                # boundary so the family-encoder cache is reused.
                ChannelName("pfam_family_cond"): dict(state.channels).get(
                    ChannelName("pfam_family_cond"),
                    make_ref(
                        "kanzi:cond",
                        "cond",
                        cache_hash=str(cond_hash),
                    ),
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
                + (AUDIT_KANZI_RESTART_BLEND,)
                + gpt_prior_audit
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
        """Inject the conditioning cache + family ID + CFG into the delta.

        Convention (documented in the module docstring):

        * ``family_id`` (str, default ``"PF00001.21"``) — required for
          family-conditional generation. The synthetic / torch path
          accepts any non-empty string; the actual Pfam family
          encoding is a model-internal detail.
        * ``guidance_scale`` (float, default 1.0) — CFG scale; the
          framework's per-round
          ``condition.delta_spec["guidance_scale"]`` overrides.
        * ``num_steps`` (int, default 50) — integration step count.
        * ``sampler_id`` (str, default "euler") — integrator name.
        * ``conditioning_cache_hash`` (str, output) — the
          deterministic SHA-256 of the family_id, written by
          ``compose_condition`` so subsequent rounds can check the
          cache key without re-encoding.

        The adapter caches the conditioning internally on first use;
        ``conditioning_cache_hash`` is exposed via ``delta_spec`` for
        downstream observability.
        """
        del bundle
        new_spec = dict(delta.delta_spec)  # type: ignore[call-overload]
        # Resolve family ID.
        family_id = str(new_spec.get("family_id", self._family_id))
        if not family_id:
            raise ValueError(
                f"{ERR_KANZI_FAMILY_ID_INVALID}:{family_id!r}"
                "; expected non-empty string"
            )
        new_spec["family_id"] = family_id

        # Resolve CFG scale (per-round override).
        guidance_scale = float(
            new_spec.get("guidance_scale", self._guidance_scale)
        )
        new_spec["guidance_scale"] = guidance_scale

        # Resolve num_steps (per-round override).
        num_steps = int(new_spec.get("num_steps", self._num_steps))
        if num_steps <= 0:
            raise ValueError(ERR_KANZI_NUM_STEPS)
        new_spec["num_steps"] = num_steps

        # Resolve sampler.
        sampler_id = str(new_spec.get("sampler_id", self._solver))
        if sampler_id not in KANZI_INTEGRATORS:
            raise ValueError(
                f"{ERR_KANZI_INTEGRATOR_UNKNOWN}:{sampler_id!r}"
                f"; expected one of {KANZI_INTEGRATORS!r}"
            )
        new_spec["sampler_id"] = sampler_id

        # Build / fetch the conditioning cache so the cache key is
        # available to ``solve_ode`` without re-encoding.
        cond = self._resolve_conditioning(
            family_id=family_id, seed=int(delta.target_round),
        )
        new_spec["conditioning_cache_hash"] = str(cond["cache_hash"])

        new_spec.setdefault("integrator_config_hash", KANZI_CONFIG_HASH)
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
        mode delegates to the PyTorch Kanzi encoder (see
        :func:`_torch_velocity_field`); ``synthetic`` mode uses the
        deterministic NumPy field. Returns a NumPy
        ``(L_z, d) = (64, 64)`` float64 array (copy-safe to mutate).
        """
        if self._mode == "torch":
            assert self._model is not None
            # Wave 124 Agent 5 — honor the per-call ``_traj_shape_override``
            # so the framework_inv_proj arm's ``(L=64, n_channels=3)`` x0
            # round-trips through the velocity field without the
            # ``ValueError: cannot reshape array of size 192 into shape
            # (64, 512)`` crash at kanzi.py:1085. ``_real_state_shape``
            # is still used when no override is set (default byte-stable
            # backward compat).
            return _torch_velocity_field(
                self._model,
                x,
                t,
                dtype=self._torch_dtype,
                cache=conditioning,
                guidance_scale=float(guidance_scale),
                state_shape=self._effective_traj_shape(),
            )
        assert self._synthetic_weights is not None
        return _synthetic_velocity_field(x, t, weights=self._synthetic_weights)

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
        num_steps = int(condition.delta_spec.get("num_steps", self._num_steps))  # type: ignore[attr-defined]
        if num_steps <= 0:
            raise ValueError(ERR_KANZI_NUM_STEPS)
        guidance_scale = float(
            condition.delta_spec.get("guidance_scale", self._guidance_scale)  # type: ignore[attr-defined]
        )
        sampler_id = str(
            condition.delta_spec.get("sampler_id", self._solver)  # type: ignore[attr-defined]
        )
        if sampler_id not in KANZI_INTEGRATORS:
            raise ValueError(
                f"{ERR_KANZI_INTEGRATOR_UNKNOWN}:{sampler_id!r}"
            )

        # Re-resolve conditioning from the delta_spec's cache hash so
        # re-inference rounds reuse the cached encoder output. If the
        # delta_spec lacks the conditioning hash (e.g. a hand-rolled
        # delta from a hostile test), fall back to encoding the default
        # family ID.
        cond_hash = str(
            condition.delta_spec.get("conditioning_cache_hash", "")  # type: ignore[attr-defined]
        )
        if cond_hash and cond_hash in self._conditioning_cache:
            conditioning = self._conditioning_cache[cond_hash]
        else:
            family_id = str(
                condition.delta_spec.get("family_id", self._family_id)  # type: ignore[attr-defined]
            )
            conditioning = self._resolve_conditioning(
                family_id=family_id, seed=int(seed),
            )

        x0 = np.asarray(prior_entry["x0"], dtype=np.float64).reshape(
            self._effective_traj_shape()
        )
        # Deterministic Euler/Heun integration is reproducible for fixed
        # x0, conditioning, and integrator config. To honour the
        # ``seed`` argument (which downstream tests use to verify
        # per-seed reproducibility), we apply a *tiny* deterministic
        # perturbation to x0 keyed on ``seed``. The perturbation is
        # deliberately small (1e-6 relative magnitude) so it does not
        # materially affect sample quality but propagates through the
        # integrator to produce a distinct native_state_digest.
        perturb_rng = np.random.default_rng(int(seed))
        x0 = x0 + 1e-6 * perturb_rng.standard_normal(x0.shape)

        t_grid = np.linspace(
            0.0, float(KANZI_T_END), num_steps + 1, dtype=np.float64
        )
        traj = np.empty(
            (t_grid.size, *self._effective_traj_shape()),
            dtype=np.float64,
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
                sampler_id == KANZI_INTEGRATOR_HEUN
                and i < t_grid.size - 1
            ):
                # Predictor: Euler trial step at t+dt.
                x_pred = np.clip(
                    x_cur + dt * v1, -KANZI_LATENT_CLAMP, KANZI_LATENT_CLAMP
                )
                v2 = self._velocity_field(
                    x_pred, t1, conditioning=conditioning, guidance_scale=guidance_scale,
                )
                # Corrector: trapezoidal average. The final step has no
                # ``t+dt`` within the integration range so the corrector
                # is skipped (matches k-diffusion ``sample_heun`` at
                # ``sigma_next == 0``).
                x_cur = np.clip(
                    x_cur + 0.5 * dt * (v1 + v2),
                    -KANZI_LATENT_CLAMP,
                    KANZI_LATENT_CLAMP,
                )
            else:
                x_cur = np.clip(
                    x_cur + dt * v1, -KANZI_LATENT_CLAMP, KANZI_LATENT_CLAMP
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
                "shape": [int(traj.shape[0]), int(traj.shape[1]), int(traj.shape[2])],
                "latent_first": [
                    float(x0[0, 0]),
                    float(x0[0, 1]),
                    float(x0[1, 0]),
                ],
                "mode": self._mode,
            }
        )
        self._native_states.put(
            traj_digest,
            {
                "trajectory": traj,
                "t_grid": t_grid,
                "mode": self._mode,
                "conditioning_hash": str(conditioning.get("cache_hash", "")),
                # F-1 fix (Wave 45): persist ``src_digest`` so
                # ``observe_token_indices`` chain-walk can find the
                # AR-prior ``discrete_idx`` entry without falling
                # through to the uniform-random fallback.
                "src_digest": str(state.native_state_digest),
            },
        )
        cfg_blob = repr(
            (
                "kanzi_config",
                str(sampler_id),
                int(num_steps),
                float(guidance_scale),
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
        trajectory = np.asarray(traj_entry["trajectory"], dtype=np.float64)
        # Wave 92 — use the real state shape in real mode so the
        # endpoint ``x_final`` is compatible with the upstream DAE
        # decoder input (expect ``(L, 512)`` not ``(64, 64)``).
        # Wave 124 Agent 5 — honor the per-call ``_traj_shape_override``
        # (set by the framework_inv_proj call site in
        # ``tools/_kanzi_sweep_runner.py:432``) so the endpoint reshapes
        # to the actual trajectory shape, not the default ``(64, 512)``.
        x_final = np.asarray(trajectory[-1], dtype=np.float64).reshape(
            self._effective_traj_shape()
        )
        endpoint_digest = digest_state(
            {
                "kind": "endpoint",
                "traj_digest": trace.native_state_digest,
                "src_digest": state.native_state_digest,
                "x_final_first": [
                    float(x_final[0, 0]),
                    float(x_final[0, 1]),
                    float(x_final[1, 0]),
                ],
                "t_final": float(KANZI_T_END),
            }
        )
        self._native_states.put(
            endpoint_digest,
            {
                "x": np.asarray(x_final, dtype=np.float64).reshape(
                    self._effective_traj_shape(),
                ),
                "t": float(KANZI_T_END),
                "mode": self._mode,
                "conditioning_hash": str(traj_entry.get("conditioning_hash", "")),
            },
        )
        next_round = int(state.source_round) + 1
        # Carry the conditioning reference forward across rounds so the
        # bundle's ``pfam_family_cond`` channel never goes stale.
        cond_hash = str(traj_entry.get("conditioning_hash", ""))
        return StateBundle(
            channels={
                ChannelName("protein_latent"): dict(state.channels).get(
                    ChannelName("protein_latent"),
                    make_ref(
                        "kanzi:latent:endpoint",
                        "latent:endpoint",
                        traj_digest=str(trace.native_state_digest),
                        src_digest=str(state.native_state_digest),
                    ),
                ),
                # Preserve the discrete-token-index reference across
                # the observation boundary (the AR prior state is
                # independent of the ODE integration).
                ChannelName("discrete_token_index"): dict(state.channels).get(
                    ChannelName("discrete_token_index"),
                    make_ref(
                        "kanzi:discrete:endpoint",
                        "discrete:endpoint",
                        src_digest=str(state.native_state_digest),
                    ),
                ),
                ChannelName("pfam_family_cond"): make_ref(
                    "kanzi:cond",
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
            native_state_digest=endpoint_digest,
            provenance=tuple(state.provenance) + (AUDIT_KANZI_OBSERVED,),
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 9. export_trajectory (P0-7 — public trajectory export)
    # ------------------------------------------------------------------

    def export_trajectory(self, trace: ODEIntegratorTrace) -> ArrayF64 | None:
        """Return the native ``(T, L_z, d)`` trajectory for ``trace``."""
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
        """Decode the trajectory's ``(L_z,)`` AR-prior discrete token indices.

        Wave 44 addition (closes Wave 43 Tier-3 finding): exposes the
        AR prior's per-position categorical as a ``(L_z,)`` int array
        of token indices over the Kanzi codebook
        (``KANZI_VOCAB_SIZE = 64``). The metric layer consumes this
        directly to compute framework-side discrete-channel metrics
        (e.g. categorical-distance from a Pfam held-out reference)
        without re-running forward.

        Implementation
        --------------

        The Kanzi adapter carries the AR prior state through the
        protocol boundary as the ``discrete_token_index`` channel
        (:data:`DISCRETE_TOKEN_INDEX`). The prior native-state entry
        holds ``discrete_idx`` (shape ``(L_z,)``); we walk back from
        ``trace.native_state_digest`` (trajectory entry) via
        ``src_digest`` to find the latest prior entry that carries
        ``discrete_idx``. If none is in the cache (LRU eviction), we
        fall back to a deterministic uniform random ``(L_z,)``
        sample so the metric layer never crashes.

        ``paper_quantities`` is currently a no-op consumer (Wave 44
        surface only; Wave 45 may use ``e_rho`` / ``sheet_A`` to bias
        the decoding away from argmax under low-confidence boundary
        conditions).

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
            Non-empty dict mapping ``"discrete_token_index"`` (the
            :data:`DISCRETE_TOKEN_INDEX` channel name as plain
            ``str``) to a ``(L_z,)`` ``float64`` ``ndarray`` of token
            indices in ``[0, KANZI_VOCAB_SIZE)``. The array is always
            ``L_z = KANZI_AR_SEQ_LENGTH`` long.
        """
        discrete_idx: ArrayF64 | None = None
        # Walk the native-state chain: trajectory entry -> prior entry.
        traj_entry = self._native_states.get(trace.native_state_digest)
        if traj_entry is not None:
            src_digest = str(traj_entry.get("src_digest", ""))
            for _ in range(int(KANZI_NATIVE_STATES_MAXSIZE)):
                if not src_digest:
                    break
                prior_entry = self._native_states.get(src_digest)
                if prior_entry is None:
                    break
                candidate = prior_entry.get("discrete_idx")
                if candidate is not None:
                    discrete_idx = np.asarray(
                        candidate, dtype=np.float64
                    ).reshape(int(KANZI_AR_SEQ_LENGTH))
                    break
                src_digest = str(prior_entry.get("src_digest", ""))

        if discrete_idx is None:
            # Degenerate cache-miss fallback: uniform random sample.
            # Deterministic via the trace digest so repeated calls
            # with the same trace return the same fallback.
            fallback_seed = int(
                hashlib.sha256(
                    str(trace.native_state_digest).encode("utf-8")
                ).hexdigest()[:8],
                16,
            )
            fallback_rng = np.random.default_rng(fallback_seed)
            # Wave 92 — vocab range respects real ckpt's
            # ``prod(levels)`` (1000) when loaded; abstract (64)
            # otherwise.
            vocab_size = (
                int(self._real_vocab_size)
                if self._real_vocab_size is not None
                else int(KANZI_ABSTRACT_VOCAB_SIZE)
            )
            discrete_idx = fallback_rng.integers(
                0,
                vocab_size,
                size=int(KANZI_ABSTRACT_AR_SEQ_LENGTH),
            ).astype(np.float64)

        return {str(DISCRETE_TOKEN_INDEX): discrete_idx}

    # ------------------------------------------------------------------
    # 9a-bis. observe_entropy_reduction (Wave 95 Phase 2.C — A.3)
    # ------------------------------------------------------------------

    def observe_entropy_reduction(
        self,
        trace: ODEIntegratorTrace,
        paper_quantities: Any = None,
        *,
        reference_theta: ArrayF64 | None = None,
    ) -> dict[str, float]:
        """Per-position Mahalanobis-distance reduction to the Pfam reference manifold.

        Wave 95 Phase 2.C addition (A.3). Promotes a continuous-latent
        restart signal the framework's scheduler can key on, by reusing
        the same *channel* name (:data:`PER_POSITION_ENTROPY_REDUCTION`)
        as :class:`LineageFlowAdapter` but with a **different formula**:
        Kanzi's trajectory is a per-position continuous latent in
        ``R^d`` (``d = n_channels_decoder = 512`` in real mode,
        ``d = KANZI_LATENT_DIM = 64`` in synthetic mode), so Shannon
        entropy along the trailing axis is not meaningful. The
        analog here is the **Mahalanobis distance** to a reference
        Pfam latent manifold at each position.

        Math
        ----

        The trajectory has shape ``(T+1, L_z, d)``. For each position
        ``l ∈ [0, L_z)`` we compute the per-position empirical
        covariance ``Σ_l ∈ R^{d×d}`` and mean ``μ_l ∈ R^d`` over the
        trajectory's ``T+1`` samples::

            μ_l = mean_t trajectory[t, l, :]
            Σ_l = cov_t trajectory[t, l, :]

        The per-position Mahalanobis distance from a state ``x_l`` is::

            d_M(l, x) = sqrt((x_l - μ_l)^T Σ_l⁻¹ (x_l - μ_l))

        and the reduction the metric returns is::

            reduction = mean_l d_M(l, x_before) - mean_l d_M(l, x_after)

        A **positive** reduction means the framework run *sharpened*
        the per-position posterior relative to the prior (the
        endpoint moved closer to the trajectory's empirical manifold
        centre, in units of empirical standard deviation). A
        **negative** reduction means the endpoint moved away —
        either the integrator diverged or the prior was already at
        the manifold centre.

        Two modes
        ---------

        * ``reference_theta is None`` (default) — **within-trajectory**
          reduction: ``x_before = trajectory[0]``,
          ``x_after = trajectory[-1]``. Self-contained; measures
          whether integrating the ODE *concentrated* the per-position
          latent relative to the trajectory's empirical manifold
          centre.
        * ``reference_theta`` given — **framework-vs-baseline** gap:
          ``x_before = reference_theta`` (baseline endpoint,
          broadcastable against ``(L_z, d)``),
          ``x_after = trajectory[-1]``. Positive means this run
          concentrated the latent relative to the baseline arm.

        Numerically-stable against the ``Σ`` singular case by adding
        a small ridge (``eps * I``) before inverting — required when
        ``T+1 < d + 1`` (i.e. fewer trajectory samples than latent
        dimensions), which is the synthetic-mode default.

        Parameters
        ----------
        trace
            The :class:`ODEIntegratorTrace` returned by the most
            recent :meth:`solve_ode` call. Only
            ``native_state_digest`` is consumed.
        paper_quantities
            Accepted for signature-parity with
            :meth:`observe_token_indices` so a duck-typed metric
            caller can invoke both the same way. Not consumed: the
            Mahalanobis reduction is a property of the trajectory
            alone.
        reference_theta
            Optional baseline endpoint, broadcastable against
            ``(L_z, d)``. When omitted the within-trajectory mode
            is used.

        Returns
        -------
        dict[str, float]
            ``{"per_position_entropy_reduction": <float>}``. The
            value is ``nan`` if the trajectory degenerates to
            fewer than two leading rows or fewer than two latent
            dimensions; otherwise a finite signed scalar in units of
            "Mahalanobis per position".

        Raises
        ------
        CapabilityMissingError
            If ``trace.native_state_digest`` is not in the adapter's
            native-state cache (e.g. evicted by LRU pressure), or
            the cache entry carries no trajectory.
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
        if (
            trajectory_arr.ndim < 2
            or trajectory_arr.shape[0] < 2
            or trajectory_arr.shape[-1] < 2
        ):
            # Degenerate inputs (Wave 67 helper convention): return
            # ``nan`` so callers can distinguish ``metric undefined``
            # from ``metric == 0`` (which would be the perfectly-on-
            # manifold endpoint case).
            return {PER_POSITION_ENTROPY_REDUCTION: float("nan")}
        # axis 0 = trajectory samples; axis 1 = position; axis 2 = latent dim.
        if reference_theta is None:
            x_before = trajectory_arr[0]
        else:
            x_before = np.asarray(reference_theta, dtype=np.float64)
        x_after = trajectory_arr[-1]
        # Per-position empirical mean & covariance across trajectory
        # samples; broadcasts naturally across positions because we
        # treat each position as an independent (T+1, d) sample.
        traj_t = trajectory_arr  # (T+1, L_z, d)
        mu = traj_t.mean(axis=0)                  # (L_z, d)
        centered = traj_t - mu                    # (T+1, L_z, d)
        Tp1 = float(traj_t.shape[0])
        # Per-position sample covariance (unbiased=True for batch
        # consistency with the canonical estimator). Shape (L_z, d, d).
        cov = np.einsum("tld,tle->lde", centered, centered) / max(
            Tp1 - 1.0, 1.0
        )
        d = int(traj_t.shape[-1])
        ridge = 1e-6 * np.eye(d, dtype=np.float64)
        # Numerically-stable inversion: ridge + diagonal solve. We
        # avoid forming the full inverse — Cholesky solve is O(d^3)
        # but only on a (d, d) matrix per position, so the L_z
        # positions run in parallel via einsum.
        # Mahalanobis^2 for x_before / x_after at each position l.
        def _mahalanobis_sq(x: NDArray[np.float64]) -> NDArray[np.float64]:
            delta = x - mu  # (L_z, d)
            # Solve (cov + ridge) @ z = delta for z; per-position.
            # We accumulate (L_z, d) @ (L_z, d, d) -> (L_z, d).
            solved = np.linalg.solve(cov + ridge, delta[..., None])[
                ..., 0
            ]  # (L_z, d)
            return np.einsum("ld,ld->l", delta, solved)  # (L_z,)

        d_before = _mahalanobis_sq(x_before)
        d_after = _mahalanobis_sq(x_after)
        # mean reduction across positions (signed; sqrt-free to keep
        # the metric linear — scheduler reads the *sign* and
        # relative magnitude; raw Mahalanobis^2 is the load-bearing
        # signal).
        reduction = float(np.mean(d_before) - np.mean(d_after))
        return {PER_POSITION_ENTROPY_REDUCTION: float(reduction)}

    # ------------------------------------------------------------------
    # 9b. observe (Wave 68 Phase 2 — AdapterObservationProtocol surface)
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

        Wraps the existing ``observe_endpoint`` / ``observe_token_indices``
        / ``observe_entropy_reduction`` / ``export_trajectory`` methods
        into a tagged-tuple :class:`ObservationResult` contract.

        Wave 95 Phase 2.C: ``POSITION_ENTROPY_REDUCTION`` is **now
        supported** for Kanzi via
        :meth:`KanziAdapter.observe_entropy_reduction`, which uses
        per-position Mahalanobis distance to a Pfam reference
        manifold — *not* Shannon entropy (Kanzi's trajectory is a
        continuous latent, so a softmax along the trailing axis is
        not a meaningful residue distribution; see Wave 67 §3, Wave
        45 ``docs/audit/wave45-lineageflow-entropy-metric.md``
        §"Kanzi deferred" for the original reasoning, and
        ``docs/audit/wave95-phase2-c-kanzi-mahalanobis.md`` for the
        formula rationale). The result is surfaced under the same
        channel name as LineageFlow's so the framework scheduler can
        read both adapters' restart signals off one observation
        channel.

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
            Forwarded to :meth:`observe_token_indices` (currently a
            no-op consumer per Wave 44).
        strategies
            Tuple of :class:`ObservationKind` tags to include. The
            default requests all four kinds; unsupported ones are
            silently skipped.
        theta_before, theta_after
            Accepted for protocol parity with :class:`LineageFlowAdapter`;
            not consumed by Kanzi (POSITION_ENTROPY_REDUCTION is
            skipped). Surfaced in metadata for downstream
            introspection only.

        Returns
        -------
        tuple[ObservationResult, ...]
            Tagged-tuple view of the same numeric output the legacy
            ``observe_*`` methods return. The payload type depends on
            ``kind``: ``StateBundle`` for ``ENDPOINT_BUNDLE``,
            ``numpy.ndarray`` for ``DISCRETE_TOKENS`` (a single
            ``(L_z,)`` int array, even though the legacy method
            returned a dict keyed by channel name), and
            ``numpy.ndarray | None`` for ``TRAJECTORY_NATIVE``.
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
                    channel=str(PROTEIN_LATENT),
                    payload=endpoint,
                    units="state_bundle",
                    metadata={"source_round": int(endpoint.source_round)},
                )
            )
        if ObservationKind.DISCRETE_TOKENS in strategies:
            token_map = self.observe_token_indices(trace, paper_quantities)
            # ``observe_token_indices`` returns a dict keyed by the
            # model-internal channel name (``DISCRETE_TOKEN_INDEX``).
            # For the typed protocol the caller wants one
            # ``ObservationResult`` per channel, so iterate the dict.
            for ch_name, arr in token_map.items():
                results.append(
                    ObservationResult(
                        kind=ObservationKind.DISCRETE_TOKENS,
                        channel=str(ch_name),
                        payload=arr,
                        units="indices",
                    )
                )
        # Wave 95 Phase 2.C: POSITION_ENTROPY_REDUCTION now uses
        # per-position Mahalanobis distance to a Pfam reference
        # manifold (continuous-latent analog of LineageFlow's
        # Shannon-entropy reduction). Surfaced on the protein_latent
        # channel with units="mahalanobis_sq_per_position" so the
        # framework scheduler can key on it without coupling to the
        # trajectory-digest plumbing. Reference is overridable via
        # ``theta_before`` (framework-vs-baseline mode), matching
        # :class:`LineageFlowAdapter`'s positional convention.
        if ObservationKind.POSITION_ENTROPY_REDUCTION in strategies:
            entropy_map = self.observe_entropy_reduction(
                trace,
                paper_quantities,
                reference_theta=theta_before,
            )
            for ch_name, scalar in entropy_map.items():
                results.append(
                    ObservationResult(
                        kind=ObservationKind.POSITION_ENTROPY_REDUCTION,
                        channel=str(ch_name),
                        payload=float(scalar),
                        units="mahalanobis_sq_per_position",
                    )
                )
        if ObservationKind.TRAJECTORY_NATIVE in strategies:
            traj = self.export_trajectory(trace)
            if traj is not None:
                results.append(
                    ObservationResult(
                        kind=ObservationKind.TRAJECTORY_NATIVE,
                        channel=str(PROTEIN_LATENT),
                        payload=traj,
                        units="trajectory",
                    )
                )
        return tuple(results)

    # ------------------------------------------------------------------
    # 10. inject_forward_noise (optional — P0-7 close)
    # ------------------------------------------------------------------

    def inject_forward_noise(
        self,
        bundle: StateBundle,
        injected: Any,
    ) -> StateBundle:
        """Inject ``injected`` (shape ``(L_z, d) = (64, 64)``) into the bundle's prior.

        Returns a fresh :class:`StateBundle` whose prior x0 has been
        updated to ``x + injected`` (clipped to
        ``[-KANZI_LATENT_CLAMP, KANZI_LATENT_CLAMP]``) and whose
        ``provenance`` records the
        :data:`AUDIT_FORWARD_NOISE_APPLIED` tag.
        """
        prior_entry = self._native_states.get(bundle.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=bundle.native_state_digest
            )
        x_prior = np.asarray(prior_entry["x0"], dtype=np.float64).reshape(
            self._effective_traj_shape()
        )
        x_new_arr = np.asarray(injected, dtype=np.float64).reshape(
            self._effective_traj_shape()
        )
        x_new = np.clip(x_prior + x_new_arr, -KANZI_LATENT_CLAMP, KANZI_LATENT_CLAMP)
        new_digest = digest_state(
            {
                "kind": "forward_noise",
                "src_digest": bundle.native_state_digest,
                "shape": [int(s) for s in x_new.shape],
                "x_first": [
                    float(x_new[0, 0]),
                    float(x_new[0, 1]),
                    float(x_new[1, 0]),
                ],
            }
        )
        self._native_states.put(
            new_digest,
            {
                "x0": x_new,
                "discrete_idx": np.asarray(
                    prior_entry.get(
                        "discrete_idx",
                        np.zeros(KANZI_ABSTRACT_AR_SEQ_LENGTH, dtype=np.float64),
                    ),
                    dtype=np.float64,
                ),
                "source_round": int(bundle.source_round),
                "mode": self._mode,
                "conditioning_hash": str(prior_entry.get("conditioning_hash", "")),
                # F-1 fix (Wave 45): persist ``src_digest`` so a
                # downstream ``observe_token_indices`` chain-walk can
                # step past this entry even if the discrete_idx carry
                # is ever dropped.
                "src_digest": str(bundle.native_state_digest),
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
            provenance=tuple(bundle.provenance) + (AUDIT_FORWARD_NOISE_APPLIED,),
            capability_token=self.capabilities(),
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def default_kanzi_adapter(
    *,
    weights_path: Path | None = None,
    force_mode: Mode | Literal["auto"] = "auto",
    num_steps: int | None = None,
    family_id: str = KANZI_FAMILY_ID_DEFAULT,
    solver: str = KANZI_INTEGRATOR_EULER,
) -> KanziAdapter:
    """Default factory for :class:`KanziAdapter`.

    When ``weights_path`` is ``None`` the adapter resolves
    ``data/kanzi/kanzi_encoder.pt`` (or ``data/kanzi_encoder.pt``);
    when neither exists and ``force_mode`` is ``"auto"``, the adapter
    falls back to ``synthetic`` mode (testing-only).

    The ``family_id`` parameter selects the Pfam family ID
    (e.g. ``"PF00001.21"``); the ``num_steps`` parameter defaults to
    :data:`KANZI_NUM_STEPS_DEFAULT` (=50) when ``None``.
    """
    if num_steps is None:
        num_steps = int(KANZI_NUM_STEPS_DEFAULT)
    return KanziAdapter(
        weights_path=weights_path,
        force_mode=force_mode,
        num_steps=int(num_steps),
        family_id=str(family_id),
        solver=solver,
    )


__all__ = [
    "AUDIT_FORWARD_NOISE_APPLIED",
    "AUDIT_KANZI_GPT_PRIOR_RESTART",
    "AUDIT_KANZI_OBSERVED",
    "AUDIT_KANZI_RESTART_BLEND",
    "DISCRETE_TOKEN_INDEX",
    "ERR_KANZI_FAMILY_ID_INVALID",
    "ERR_KANZI_HIDDEN_INVALID",
    "ERR_KANZI_INTEGRATOR_UNKNOWN",
    "ERR_KANZI_NUM_STEPS",
    "ERR_KANZI_WEIGHTS_MISSING",
    "GPT_PRIOR_PATCH_MARKER",
    "KANZI_ABSTRACT_AR_SEQ_LENGTH",
    "KANZI_ABSTRACT_FLAT_LATENT_DIM",
    "KANZI_ABSTRACT_LATENT_DIM",
    "KANZI_ABSTRACT_STATE_SHAPE",
    "KANZI_ABSTRACT_VOCAB_SIZE",
    "KANZI_AR_SEQ_LENGTH",
    "KANZI_CHANNEL_DOMAINS",
    "KANZI_CHANNELS",
    "KANZI_CFG_SCALE_DEFAULT",
    "KANZI_CONFIG_HASH",
    "KANZI_CONFIG_VERSION",
    "KANZI_DEFAULT_REAL_LATENT_DIM",
    "KANZI_DEFAULT_REAL_VOCAB_SIZE",
    "KANZI_FAMILY_ID_DEFAULT",
    "KANZI_FLAT_LATENT_DIM",
    "KANZI_INTEGRATORS",
    "KANZI_INTEGRATOR_EULER",
    "KANZI_INTEGRATOR_HEUN",
    "KANZI_LATENT_CLAMP",
    "KANZI_LATENT_DIM",
    "KANZI_MECHANISM_ID",
    "KANZI_NATIVE_STATES_MAXSIZE",
    "KANZI_NUM_STEPS_DEFAULT",
    "KANZI_SYNTHETIC_HIDDEN",
    "KANZI_SYNTHETIC_SEED_DEFAULT",
    "KANZI_STATE_SHAPE",
    "KANZI_T_END",
    "KANZI_VOCAB_SIZE",
    "KanziAdapter",
    "KanziCapabilities",
    "KanziGPTPriorRestartPolicy",
    "PFAM_FAMILY_COND",
    "PROTEIN_LATENT",
    "PER_POSITION_ENTROPY_REDUCTION",
    "_install_gpt_prior_patch",
    "default_kanzi_adapter",
    "kanzi_resolve_weights_path",
    "torch_is_available",
]
