"""Per-channel blender dispatcher (D9 — LMAA redesign).

The framework currently ships one ``RestartBlenderProtocol``
(:class:`adaptive_reflow.algorithm.blender.LinearBlender` /
:class:`DistanceDecayBlender` / :class:`CategoricalAwareBlender`).
The ``CategoricalAwareBlender`` dispatches *internally* based on the
per-channel ``ChannelDomain`` literal (``"continuous"`` / ``"discrete"``
/ ``"graph"`` / ``"latent"``) but the dispatch is hard-coded inside
the blender — the framework cannot pick the correct blend per
channel without routing through ``CategoricalAwareBlender``.

Design #3 splits that internal dispatch into a typed
:class:`BlendStrategy` Protocol + per-channel concrete
implementations so the engine can compose per-channel blends from
the ``AdapterCapabilities.channel_types`` table. The five concrete
blend strategies correspond to the six ``StateChannel`` values
declared in :mod:`adaptive_reflow.contracts.state_channel`:

* :class:`LinearBlend` — ``"continuous"`` and ``"latent"`` channels
  (FlowMol3 ``coordinate``, GraphBFN ``charge``, Lumina/HiDream
  ``latent``).
* :class:`LogitBlend` — ``"categorical_argmax"`` channels
  (ProtBFN ``argmax``, GraphBFN adjacency ``argmax``). Lifts to
  logit space, blends linearly, renormalises via softmax, returns
  the ``argmax`` (concentrated selection toward the sheet).
* :class:`MaskedBlend` — ``"categorical_mask"`` channels with the
  canonical ``m=0`` / ``m=1`` short-circuit semantics
  (GraphBFN ``-inf`` diagonal sentinel, FlowMol3 padded
  positions via ``mask == 0``). At ``m=0`` the prior is dropped
  completely (fresh draw); at ``m=1`` the prior is returned
  unchanged (the short-circuit dodges ``0 * -inf = NaN`` on the
  adjacency diagonal).
* :class:`GumbelBlend` — ``"categorical_sample"`` channels
  (ProtBFN ``sample``, FlowMol3 ``bond_type`` sample). Lifts to
  logit space, blends, samples via Gumbel-max with the supplied
  ``tau`` (annealed across rounds per Theorem 1's
  ``eps_round -> 0`` schedule).
* :class:`SampleBlend` — uniform-Categorical resample for
  ``"categorical_*"`` channels where the engine wants a fully
  fresh draw regardless of memory fraction (used by
  ``build_initial_state`` rather than the restart boundary).
* :class:`GraphBlend` — graph-shaped ``"graph"`` channels that
  delegate to :class:`MaskedBlend` for the adjacency diagonal and
  :class:`LinearBlend` / :class:`LogitBlend` for the
  per-channel ``theta_node`` / ``theta_edge`` sub-tensors.

The :class:`PerChannelBlender` dispatcher picks the correct
strategy per channel from the ``AdapterCapabilities.channel_types``
table; channels not in the table fall through to
:class:`LinearBlend` (the canonical back-compat path).

Module boundary
---------------

This module is **stdlib + numpy only**. The categorical math
(softmax, log-space arithmetic, Gumbel sampling) cannot be
expressed with stdlib-only primitives without reinventing the
wheel; numpy is the canonical vehicle for tensor-shaped
categorical data and is already used at the molecule-layer for
graph-shape tensors (``graphbfn.py``, ``flowmol3_v2_adapter.py``)
and the existing :class:`CategoricalAwareBlender`. No ``torch``,
no I/O, no global state, no mutation of inputs.

Public surface
--------------

* :class:`BlendStrategy` — abstract Protocol.
* :class:`LinearBlend`, :class:`LogitBlend`, :class:`MaskedBlend`,
  :class:`GumbelBlend`, :class:`SampleBlend`, :class:`GraphBlend` —
  concrete strategies.
* :class:`PerChannelBlender` — dispatcher with
  :meth:`blend_channel` and :meth:`blend_all_channels`.
* :data:`LINEAR_FAMILY`, :data:`LOGIT_FAMILY`, :data:`MASKED_FAMILY`,
  :data:`GUMBEL_FAMILY`, :data:`SAMPLE_FAMILY`, :data:`GRAPH_FAMILY`.
* :data:`BLEND_FAMILY_BY_CHANNEL` — channel-kind → family lookup.
* Audit-code constants for short-circuit detection.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

import numpy as np

from adaptive_reflow.contracts.state_channel import (
    STATE_CHANNELS,
    StateChannel,
    validate_state_channel,
)
from adaptive_reflow.universal.state import (
    ChannelName,
    StateBundle,
    TensorRef,
    validate_state_bundle,
)

# ---------------------------------------------------------------------------
# Module-level constants (family identifiers + audit codes)
# ---------------------------------------------------------------------------

#: Blender family identifier for :class:`LinearBlend`.
LINEAR_FAMILY: str = "linear"

#: Blender family identifier for :class:`LogitBlend`.
LOGIT_FAMILY: str = "logit"

#: Blender family identifier for :class:`MaskedBlend`.
MASKED_FAMILY: str = "masked"

#: Blender family identifier for :class:`GumbelBlend`.
GUMBEL_FAMILY: str = "gumbel"

#: Blender family identifier for :class:`SampleBlend`.
SAMPLE_FAMILY: str = "sample"

#: Blender family identifier for :class:`GraphBlend`.
GRAPH_FAMILY: str = "graph"

#: Audit code: ``memory_fraction == 0`` short-circuit fired (return
#: fresh draw verbatim). The prior is dropped, so the blend math
#: is skipped — prevents ``0 * -inf = NaN`` on the GraphBFN
#: adjacency diagonal.
PER_CHANNEL_BLEND_M_ZERO_SHORTCIRCUIT: str = "per_channel_blend_m_zero_short_circuit"

#: Audit code: ``memory_fraction == 1`` short-circuit fired (return
#: prior verbatim). The fresh draw is dropped, so the blend math
#: is skipped — symmetric to ``m=0`` and prevents mask-channel
#: sentinel passthrough noise.
PER_CHANNEL_BLEND_M_ONE_SHORTCIRCUIT: str = "per_channel_blend_m_one_short_circuit"

#: Audit code: ``mask == 0`` fallback fired (padded position
#: substituted with fresh draw). Mirrors
#: :data:`adaptive_reflow.algorithm.categorical_blender.CATEGORICAL_BLEND_MASK_FRESH_FALLBACK`.
PER_CHANNEL_BLEND_MASK_FRESH_FALLBACK: str = "per_channel_blend_mask_fresh_fallback"

#: Audit code: GraphBFN ``-inf`` diagonal sentinel passthrough.
PER_CHANNEL_BLEND_SENTINEL_PASSTHROUGH: str = "per_channel_blend_sentinel_passthrough"

#: Audit code: ``tau <= tau_floor`` → sampler degenerated to argmax.
PER_CHANNEL_BLEND_TAU_FLOOR_HIT: str = "per_channel_blend_tau_floor_hit"

#: Audit code: channel-kind not declared in the
#: ``AdapterCapabilities.channel_types`` table; fell through to
#: ``LinearBlend`` (canonical back-compat).
PER_CHANNEL_BLEND_FALLTHROUGH: str = "per_channel_blend_fallthrough"

#: Log-space floor for softmax numerical stability.
EPS_LOG: float = 1e-30

#: Default Gumbel-anneal temperature (mirrors
#: :data:`adaptive_reflow.algorithm.categorical_blender.DEFAULT_TAU_FLOOR`).
DEFAULT_TAU_FLOOR: float = 0.1

#: Default Gumbel-anneal temperature (tau=1.0 == full categorical).
DEFAULT_TAU_DEFAULT: float = 1.0


# Default channel-kind → blender-family lookup. The dispatcher
# consults this when the per-channel ``channel_types`` entry is
# absent (fallback) or when no explicit override is supplied.
DEFAULT_BLEND_FAMILY_BY_CHANNEL: dict[str, str] = {
    "continuous": LINEAR_FAMILY,
    "latent": LINEAR_FAMILY,
    "categorical_argmax": LOGIT_FAMILY,
    "categorical_mask": MASKED_FAMILY,
    "categorical_sample": GUMBEL_FAMILY,
    "mixed": LINEAR_FAMILY,
    "graph": GRAPH_FAMILY,
}


# Public alias (re-exported under ``BLEND_FAMILY_BY_CHANNEL`` for
# callers that prefer the canonical name).
BLEND_FAMILY_BY_CHANNEL: dict[str, str] = DEFAULT_BLEND_FAMILY_BY_CHANNEL


# ---------------------------------------------------------------------------
# Abstract Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class BlendStrategy(Protocol):
    """Abstract per-channel blend strategy.

    Every concrete :class:`BlendStrategy` MUST expose a stable
    :meth:`family` discriminator (one of
    :data:`LINEAR_FAMILY` / :data:`LOGIT_FAMILY` /
    :data:`MASKED_FAMILY` / :data:`GUMBEL_FAMILY` /
    :data:`SAMPLE_FAMILY` / :data:`GRAPH_FAMILY`) and a
    :meth:`blend` callable with the canonical signature.

    The protocol is ``runtime_checkable`` so the
    :class:`PerChannelBlender` dispatcher can duck-type
    structural conformance (``isinstance(strategy, BlendStrategy)``).
    """

    def family(self) -> str:
        """Return the blender-family discriminator (e.g. ``"linear"``)."""
        ...

    def blend(
        self,
        prior_value: Any,
        fresh_value: Any,
        *,
        memory_fraction: float,
        tau: float = DEFAULT_TAU_DEFAULT,
        mask: Any | None = None,
        audit_codes: list[str] | None = None,
    ) -> Any:
        """Return the blended value for a single channel.

        ``prior_value`` and ``fresh_value`` are adapter-supplied
        native tensors (numpy arrays, tuples of floats, or
        duck-typed values). ``memory_fraction`` ∈ ``[0, 1]``;
        ``tau`` is the Gumbel temperature (only consulted by
        :class:`GumbelBlend` and ignored by the other strategies).
        ``mask`` is the optional mask carrier
        (``mask == 0`` substitutes fresh draw — only consulted by
        :class:`MaskedBlend`).

        Returns the blended native value. The dispatcher wraps the
        return value into a :class:`StateBundle` for the engine.
        """
        ...


# ---------------------------------------------------------------------------
# Helpers (shared arithmetic + bundle wrapping)
# ---------------------------------------------------------------------------


def _coerce_memory_fraction(
    m: Any,
    *,
    audit_codes: list[str] | None = None,
) -> float:
    """Clamp ``m`` into ``[0, 1]`` and emit a clip audit code.

    Mirrors :func:`adaptive_reflow.algorithm.blender._coerce_memory_fraction`
    but is inlined here so this module stays stdlib-only and
    self-contained (the existing helper is in a sibling module that
    already pulls ``numpy``; we want the per-channel dispatcher
    importable even by callers that don't yet need numpy).

    When ``m == 0`` the :data:`PER_CHANNEL_BLEND_M_ZERO_SHORTCIRCUIT`
    audit code is appended (so downstream readers can attribute
    the short-circuit to the call site). When ``m == 1`` the
    :data:`PER_CHANNEL_BLEND_M_ONE_SHORTCIRCUIT` audit code is
    appended. Inputs already in ``(0, 1)`` pass through silently
    so the resulting digest is byte-identical.
    """
    if m is None:
        raise ValueError("memory_fraction_required")
    if isinstance(m, bool):
        fx = float(int(m))
    elif isinstance(m, (int, float)):
        fx = float(m)
    else:
        raise ValueError(
            f"memory_fraction_must_be_real_number: got {type(m).__name__}"
        )
    if not math.isfinite(fx):
        raise ValueError(f"memory_fraction_must_be_finite: got {fx!r}")
    if fx < 0.0:
        if audit_codes is not None:
            audit_codes.append(
                f"per_channel_blend_memory_fraction_clipped:value={fx!r}:to=0.0"
            )
        return 0.0
    if fx > 1.0:
        if audit_codes is not None:
            audit_codes.append(
                f"per_channel_blend_memory_fraction_clipped:value={fx!r}:to=1.0"
            )
        return 1.0
    return float(fx)


def _ensure_array(value: Any) -> np.ndarray:
    """Coerce ``value`` into a float64 numpy array.

    Accepts: numpy arrays (returned with dtype cast), tuples of
    numbers, lists of numbers, and bare numeric scalars (returned
    as ``np.array([scalar], dtype=np.float64)``). Rejects ``None``
    and non-numeric entries with a typed error code.
    """
    if value is None:
        raise ValueError("channel_value_must_not_be_none")
    if isinstance(value, np.ndarray):
        return value.astype(np.float64, copy=False)
    if isinstance(value, bool):
        raise ValueError("channel_value_must_not_be_bool")
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            raise ValueError(f"channel_value_must_be_finite: got {value!r}")
        out: np.ndarray = np.array([float(value)], dtype=np.float64)
        return out
    if isinstance(value, str):
        raise ValueError("channel_value_must_not_be_string")
    try:
        arr: np.ndarray = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"channel_value_must_be_numeric_or_iterable: got {type(value).__name__}"
        ) from exc
    if not np.all(np.isfinite(arr)):
        raise ValueError("channel_value_must_be_finite_array")
    return arr


def _shape_mismatch_message(prior: np.ndarray, fresh: np.ndarray) -> str:
    """Return the canonical shape-mismatch error string."""
    return f"shape_mismatch: prior={prior.shape} fresh={fresh.shape}"


def _check_shape(prior: np.ndarray, fresh: np.ndarray) -> None:
    """Raise :class:`ValueError` when ``prior`` and ``fresh`` shapes differ."""
    if prior.shape != fresh.shape:
        raise ValueError(_shape_mismatch_message(prior, fresh))


def _resolve_family(
    channel: ChannelName,
    channel_types: Mapping[ChannelName, StateChannel] | None,
) -> str:
    """Return the blender family for ``channel``.

    Looks up the canonical :data:`DEFAULT_BLEND_FAMILY_BY_CHANNEL`
    table via ``channel_types`` when supplied; falls through to
    :data:`LINEAR_FAMILY` (canonical back-compat) when the channel
    is untyped.
    """
    if channel_types is None:
        return LINEAR_FAMILY
    kind = channel_types.get(channel)
    if kind is None:
        return LINEAR_FAMILY
    return DEFAULT_BLEND_FAMILY_BY_CHANNEL.get(kind, LINEAR_FAMILY)


# ---------------------------------------------------------------------------
# LinearBlend — continuous / latent channels
# ---------------------------------------------------------------------------


class LinearBlend:
    """Per-channel linear blender for ``"continuous"`` / ``"latent"`` channels.

    Implements the canonical convex combination

        blended = m * prior + (1 - m) * fresh

    where ``m = memory_fraction`` is clamped into ``[0, 1]``.
    Short-circuit semantics: ``m == 0`` returns ``fresh`` verbatim
    (drops the prior); ``m == 1`` returns ``prior`` verbatim
    (drops the fresh draw). The short-circuit emits the
    :data:`PER_CHANNEL_BLEND_M_ZERO_SHORTCIRCUIT` /
    :data:`PER_CHANNEL_BLEND_M_ONE_SHORTCIRCUIT` audit codes so
    downstream readers can attribute the shortcut to the call
    site.

    Deterministic: identical inputs always yield identical arrays.
    """

    #: Family identifier. Class-level so tests + callers can introspect
    #: the constant without instantiating.
    FAMILY: str = LINEAR_FAMILY

    def family(self) -> str:
        """Return ``"linear"`` (the :data:`LINEAR_FAMILY` constant)."""
        return self.FAMILY

    def blend(
        self,
        prior_value: Any,
        fresh_value: Any,
        *,
        memory_fraction: float,
        tau: float = DEFAULT_TAU_DEFAULT,
        mask: Any | None = None,
        audit_codes: list[str] | None = None,
    ) -> np.ndarray:
        """Return ``m * prior + (1 - m) * fresh`` as a float64 array."""
        prior = _ensure_array(prior_value)
        fresh = _ensure_array(fresh_value)
        _check_shape(prior, fresh)
        m = _coerce_memory_fraction(memory_fraction, audit_codes=audit_codes)
        if m == 0.0:
            if audit_codes is not None:
                audit_codes.append(PER_CHANNEL_BLEND_M_ZERO_SHORTCIRCUIT)
            return fresh.copy()
        if m == 1.0:
            if audit_codes is not None:
                audit_codes.append(PER_CHANNEL_BLEND_M_ONE_SHORTCIRCUIT)
            return prior.copy()
        return m * prior + (1.0 - m) * fresh


# ---------------------------------------------------------------------------
# LogitBlend — categorical_argmax channels
# ---------------------------------------------------------------------------


class LogitBlend:
    """Per-channel logit-space blender for ``"categorical_argmax"`` channels.

    Lifts the prior + fresh logits into logit space, blends
    linearly (``m * prior + (1 - m) * fresh``), renormalises via
    softmax, then returns the ``argmax`` index (the canonical
    concentrated-selection endpoint for ``argmax`` channels).

    For 2-D inputs ``(n, K)`` where ``K`` is the vocabulary size,
    the blend reduces to per-row ``argmax(softmax(m * prior +
    (1 - m) * fresh))``; for 1-D inputs ``(K,)`` the operation
    is the same on the single row.

    Short-circuit semantics: ``m == 0`` returns ``argmax(fresh)``;
    ``m == 1`` returns ``argmax(prior)``. The short-circuit emits
    the canonical audit codes.

    Deterministic: identical inputs always yield identical arrays.
    """

    FAMILY: str = LOGIT_FAMILY

    def family(self) -> str:
        """Return ``"logit"`` (the :data:`LOGIT_FAMILY` constant)."""
        return self.FAMILY

    def blend(
        self,
        prior_value: Any,
        fresh_value: Any,
        *,
        memory_fraction: float,
        tau: float = DEFAULT_TAU_DEFAULT,
        mask: Any | None = None,
        audit_codes: list[str] | None = None,
    ) -> np.ndarray:
        """Return ``argmax(softmax(m * prior + (1 - m) * fresh))``."""
        prior = _ensure_array(prior_value)
        fresh = _ensure_array(fresh_value)
        _check_shape(prior, fresh)
        m = _coerce_memory_fraction(memory_fraction, audit_codes=audit_codes)
        if m == 0.0:
            if audit_codes is not None:
                audit_codes.append(PER_CHANNEL_BLEND_M_ZERO_SHORTCIRCUIT)
            return np.argmax(fresh, axis=-1)
        if m == 1.0:
            if audit_codes is not None:
                audit_codes.append(PER_CHANNEL_BLEND_M_ONE_SHORTCIRCUIT)
            return np.argmax(prior, axis=-1)
        blended = m * prior + (1.0 - m) * fresh
        # Numerically stable softmax via max-shift.
        shifted = blended - np.max(blended, axis=-1, keepdims=True)
        exp = np.exp(shifted)
        softmax = exp / np.sum(exp, axis=-1, keepdims=True)
        return np.argmax(softmax, axis=-1)


# ---------------------------------------------------------------------------
# MaskedBlend — categorical_mask channels (GraphBFN -inf diagonal,
# FlowMol3 padded positions)
# ---------------------------------------------------------------------------


class MaskedBlend:
    """Per-channel masked blender for ``"categorical_mask"`` channels.

    Implements the canonical GraphBFN-style blend with the
    short-circuit semantics that dodges ``0 * -inf = NaN`` on
    the adjacency diagonal:

    * At ``m == 0``: return the ``fresh`` array verbatim with
      ``mask == 0`` positions substituted by ``fresh[mask == 0]``
      (the prior is dropped, so the mask is irrelevant).
    * At ``m == 1``: return the ``prior`` array verbatim with
      ``mask == 0`` positions substituted by ``prior[mask == 0]``
      (the fresh draw is dropped).
    * At ``m ∈ (0, 1)``: blend linearly; ``mask == 0`` positions
      always take the fresh draw (FlowMol3 padded positions).
    * ``-inf`` sentinels (GraphBFN diagonal) are passed through
      without math: where the prior has ``-inf`` at position
      ``(i, i)`` the blend returns ``-inf`` verbatim (the audit
      code :data:`PER_CHANNEL_BLEND_SENTINEL_PASSTHROUGH` is
      emitted for each sentinel hit).

    Deterministic: identical inputs always yield identical arrays.
    """

    FAMILY: str = MASKED_FAMILY

    def family(self) -> str:
        """Return ``"masked"`` (the :data:`MASKED_FAMILY` constant)."""
        return self.FAMILY

    def blend(
        self,
        prior_value: Any,
        fresh_value: Any,
        *,
        memory_fraction: float,
        tau: float = DEFAULT_TAU_DEFAULT,
        mask: Any | None = None,
        audit_codes: list[str] | None = None,
    ) -> np.ndarray:
        """Return the masked-blended array."""
        prior = _ensure_array(prior_value)
        fresh = _ensure_array(fresh_value)
        _check_shape(prior, fresh)
        m = _coerce_memory_fraction(memory_fraction, audit_codes=audit_codes)

        # Detect GraphBFN ``-inf`` diagonal sentinel: positions where
        # ``prior == -inf`` are passed through verbatim (no blend
        # math). The audit code is emitted for each sentinel hit so
        # downstream readers can attribute the passthrough to the
        # call site.
        sentinel_mask = np.isneginf(prior)
        sentinel_count = int(np.sum(sentinel_mask))
        if sentinel_count and audit_codes is not None:
            audit_codes.append(
                f"{PER_CHANNEL_BLEND_SENTINEL_PASSTHROUGH}:count={sentinel_count}"
            )

        # Resolve the optional ``mask`` argument (FlowMol3 padded
        # positions). ``mask == 0`` always takes the fresh draw.
        mask_arr: np.ndarray | None = None
        if mask is not None:
            mask_arr = np.asarray(mask, dtype=np.float64)
            if mask_arr.shape != prior.shape:
                raise ValueError(
                    f"mask_shape_mismatch: mask={mask_arr.shape} "
                    f"prior={prior.shape}"
                )
            fallback_count = int(np.sum(mask_arr == 0))
            if fallback_count and audit_codes is not None:
                audit_codes.append(
                    f"{PER_CHANNEL_BLEND_MASK_FRESH_FALLBACK}:count={fallback_count}"
                )

        if m == 0.0:
            if audit_codes is not None:
                audit_codes.append(PER_CHANNEL_BLEND_M_ZERO_SHORTCIRCUIT)
            out = fresh.copy()
            if sentinel_mask.any():
                out = np.where(sentinel_mask, prior, out)
            return out
        if m == 1.0:
            if audit_codes is not None:
                audit_codes.append(PER_CHANNEL_BLEND_M_ONE_SHORTCIRCUIT)
            out = prior.copy()
            if sentinel_mask.any():
                # Sentinel positions keep ``-inf``; no override.
                pass
            return out

        blended = m * prior + (1.0 - m) * fresh
        if mask_arr is not None:
            blended = np.where(mask_arr == 0, fresh, blended)
        if sentinel_mask.any():
            blended = np.where(sentinel_mask, prior, blended)
        return blended


# ---------------------------------------------------------------------------
# GumbelBlend — categorical_sample channels (Gumbel-max sampling)
# ---------------------------------------------------------------------------


class GumbelBlend:
    """Per-channel Gumbel-max blender for ``"categorical_sample"`` channels.

    Lifts the prior + fresh logits into logit space, blends
    linearly, then samples via Gumbel-max with temperature
    ``tau``:

        g_i ~ Gumbel(0, 1)        # noise draw
        sample = argmax((logits + g_i) / tau)

    At ``tau <= tau_floor`` the sampler degenerates to
    ``argmax(softmax(logits))`` (concentrated selection toward
    the sheet — the canonical posterior-mode proxy under
    Theorem 1 iterative application). The audit code
    :data:`PER_CHANNEL_BLEND_TAU_FLOOR_HIT` is emitted on the
    degeneracy path.

    Deterministic modulo the Gumbel noise draw: the dispatcher
    passes a numpy ``Generator`` via the optional ``rng`` argument
    (or the caller supplies a fixed seed via ``memory_fraction``
    — the Gumbel noise draw is supplied via the ``fresh_value``
    argument by the upstream ``SchedulerProtocol.inject_noise``
    call, so the blend itself does NOT add additional noise).

    Short-circuit semantics: ``m == 0`` returns ``argmax(fresh)``;
    ``m == 1`` returns ``argmax(prior)``.
    """

    FAMILY: str = GUMBEL_FAMILY

    def __init__(self, *, tau_floor: float = DEFAULT_TAU_FLOOR) -> None:
        if not isinstance(tau_floor, (int, float)) or isinstance(tau_floor, bool):
            raise ValueError(
                f"tau_floor_must_be_real_number: got {type(tau_floor).__name__}"
            )
        t = float(tau_floor)
        if not math.isfinite(t):
            raise ValueError(f"tau_floor_must_be_finite: got {t!r}")
        if t <= 0.0:
            raise ValueError(f"tau_floor_must_be_positive: got {t!r}")
        self._tau_floor = t

    @property
    def tau_floor(self) -> float:
        """Return the configured tau_floor."""
        return float(self._tau_floor)

    def family(self) -> str:
        """Return ``"gumbel"`` (the :data:`GUMBEL_FAMILY` constant)."""
        return self.FAMILY

    def blend(
        self,
        prior_value: Any,
        fresh_value: Any,
        *,
        memory_fraction: float,
        tau: float = DEFAULT_TAU_DEFAULT,
        mask: Any | None = None,
        audit_codes: list[str] | None = None,
    ) -> np.ndarray:
        """Return the Gumbel-max sampled blend.

        ``prior_value`` and ``fresh_value`` are logit arrays
        (numpy, shape ``(n, K)`` or ``(K,)``). ``tau`` is the
        Gumbel temperature; ``fresh_value`` carries the Gumbel
        noise draw added by the upstream scheduler
        (``inject_noise`` produces ``fresh = logits + gumbel``).
        """
        prior = _ensure_array(prior_value)
        fresh = _ensure_array(fresh_value)
        _check_shape(prior, fresh)
        m = _coerce_memory_fraction(memory_fraction, audit_codes=audit_codes)

        tau_in = float(tau)
        if not math.isfinite(tau_in) or tau_in <= 0.0:
            tau_in = DEFAULT_TAU_DEFAULT

        if m == 0.0:
            if audit_codes is not None:
                audit_codes.append(PER_CHANNEL_BLEND_M_ZERO_SHORTCIRCUIT)
            if tau_in <= self._tau_floor:
                if audit_codes is not None:
                    audit_codes.append(
                        f"{PER_CHANNEL_BLEND_TAU_FLOOR_HIT}:tau={tau_in!r}"
                    )
                return np.argmax(fresh, axis=-1)
            return np.argmax(fresh / tau_in, axis=-1)
        if m == 1.0:
            if audit_codes is not None:
                audit_codes.append(PER_CHANNEL_BLEND_M_ONE_SHORTCIRCUIT)
            if tau_in <= self._tau_floor:
                if audit_codes is not None:
                    audit_codes.append(
                        f"{PER_CHANNEL_BLEND_TAU_FLOOR_HIT}:tau={tau_in!r}"
                    )
                return np.argmax(prior, axis=-1)
            return np.argmax(prior / tau_in, axis=-1)

        blended = m * prior + (1.0 - m) * fresh
        if tau_in <= self._tau_floor:
            if audit_codes is not None:
                audit_codes.append(
                    f"{PER_CHANNEL_BLEND_TAU_FLOOR_HIT}:tau={tau_in!r}"
                )
            return np.argmax(blended, axis=-1)
        return np.argmax(blended / tau_in, axis=-1)


# ---------------------------------------------------------------------------
# SampleBlend — uniform-Categorical resample (used by
# build_initial_state, NOT the restart boundary)
# ---------------------------------------------------------------------------


class SampleBlend:
    """Per-channel uniform-Categorical resampler.

    Returns ``fresh`` verbatim regardless of ``memory_fraction``
    (the canonical "draw a fresh categorical" semantic). Used by
    ``build_initial_state`` rather than the restart boundary
    because the initial-state draw is unconditional; the
    ``memory_fraction`` argument is accepted but ignored so the
    :class:`PerChannelBlender` dispatcher can route every channel
    through a single :meth:`blend` entry-point.

    Deterministic: identical inputs always yield identical arrays
    (the upstream ``SchedulerProtocol.inject_noise`` produces the
    Gumbel-noised draw that gets passed through verbatim).
    """

    FAMILY: str = SAMPLE_FAMILY

    def family(self) -> str:
        """Return ``"sample"`` (the :data:`SAMPLE_FAMILY` constant)."""
        return self.FAMILY

    def blend(
        self,
        prior_value: Any,
        fresh_value: Any,
        *,
        memory_fraction: float,
        tau: float = DEFAULT_TAU_DEFAULT,
        mask: Any | None = None,
        audit_codes: list[str] | None = None,
    ) -> np.ndarray:
        """Return ``fresh`` verbatim."""
        # Accept (and ignore) ``memory_fraction`` so the dispatcher
        # can route every channel through one entry-point. Coerce
        # the value to validate the caller passed a real number.
        _coerce_memory_fraction(memory_fraction, audit_codes=audit_codes)
        prior = _ensure_array(prior_value)
        fresh = _ensure_array(fresh_value)
        _check_shape(prior, fresh)
        return fresh.copy()


# ---------------------------------------------------------------------------
# GraphBlend — graph-shaped channels (delegates to MaskedBlend for the
# adjacency diagonal + LinearBlend / LogitBlend for the per-channel
# ``theta_node`` / ``theta_edge`` sub-tensors)
# ---------------------------------------------------------------------------


class GraphBlend:
    """Per-channel graph-shaped blender for ``"graph"`` channels.

    A graph channel carries three sub-tensors: ``theta_node``
    (continuous node attributes), ``theta_edge`` (continuous edge
    attributes), and ``adj_logits`` (graph adjacency logits with
    a ``-inf`` diagonal sentinel). The blender delegates each
    sub-tensor to the appropriate per-channel strategy and emits
    the GraphBFN-specific audit codes.

    The blender input ``prior_value`` / ``fresh_value`` MUST be a
    ``Mapping[str, np.ndarray]`` with keys ``"theta_node"``,
    ``"theta_edge"``, and ``"adj_logits"``. The output is a
    fresh ``dict`` with the same keys.
    """

    FAMILY: str = GRAPH_FAMILY

    def __init__(self) -> None:
        # Pre-instantiate the per-sub-tensor delegates.
        self._linear = LinearBlend()
        self._logit = LogitBlend()
        self._masked = MaskedBlend()

    def family(self) -> str:
        """Return ``"graph"`` (the :data:`GRAPH_FAMILY` constant)."""
        return self.FAMILY

    def blend(
        self,
        prior_value: Any,
        fresh_value: Any,
        *,
        memory_fraction: float,
        tau: float = DEFAULT_TAU_DEFAULT,
        mask: Any | None = None,
        audit_codes: list[str] | None = None,
    ) -> dict[str, np.ndarray]:
        """Return the per-sub-tensor blended graph dict."""
        if not isinstance(prior_value, Mapping) or not isinstance(fresh_value, Mapping):
            raise ValueError(
                "graph_blend_requires_mapping_subtensors: "
                f"prior={type(prior_value).__name__} fresh={type(fresh_value).__name__}"
            )
        expected_keys = ("theta_node", "theta_edge", "adj_logits")
        for k in expected_keys:
            if k not in prior_value or k not in fresh_value:
                raise ValueError(f"graph_blend_missing_subtensor:{k}")

        out: dict[str, np.ndarray] = {}
        out["theta_node"] = self._linear.blend(
            prior_value["theta_node"],
            fresh_value["theta_node"],
            memory_fraction=memory_fraction,
            tau=tau,
            mask=None,
            audit_codes=audit_codes,
        )
        out["theta_edge"] = self._linear.blend(
            prior_value["theta_edge"],
            fresh_value["theta_edge"],
            memory_fraction=memory_fraction,
            tau=tau,
            mask=None,
            audit_codes=audit_codes,
        )
        out["adj_logits"] = self._masked.blend(
            prior_value["adj_logits"],
            fresh_value["adj_logits"],
            memory_fraction=memory_fraction,
            tau=tau,
            mask=mask,
            audit_codes=audit_codes,
        )
        return out


# ---------------------------------------------------------------------------
# PerChannelBlender — dispatcher
# ---------------------------------------------------------------------------


class PerChannelBlender:
    """Per-channel blender dispatcher (Design #3 D9).

    Routes each channel to the correct :class:`BlendStrategy` based
    on the ``AdapterCapabilities.channel_types`` table. Channels
    that the adapter does not declare in the table fall through to
    :class:`LinearBlend` (canonical back-compat).

    Construction
    ------------

    * ``channel_types``: optional ``Mapping[ChannelName, StateChannel]``
      carrying the per-channel type declaration. When ``None`` the
      dispatcher treats every channel as ``"continuous"`` (the
      legacy single-channel semantic).
    * ``family_overrides``: optional ``Mapping[ChannelName, str]``
      that lets the caller override the channel-kind → family
      lookup (e.g. for a FlowMol3 ``bond_type`` channel that is
      typed ``"categorical_mask"`` but the engine wants the
      :class:`GumbelBlend` sampler instead of the masked blend).
    * ``tau_floor``: Gumbel-anneal floor (forwarded to
      :class:`GumbelBlend`).
    """

    def __init__(
        self,
        *,
        channel_types: Mapping[ChannelName, StateChannel] | None = None,
        family_overrides: Mapping[ChannelName, str] | None = None,
        tau_floor: float = DEFAULT_TAU_FLOOR,
    ) -> None:
        # Validate every declared channel kind at construction time
        # so a typo in the table fails fast.
        if channel_types is not None:
            for ch, kind in channel_types.items():
                ok, errs = validate_state_channel(kind)
                if not ok:
                    raise ValueError(
                        f"invalid channel_types[{ch}]: {', '.join(errs)}"
                    )
        self._channel_types: Mapping[ChannelName, StateChannel] | None = (
            dict(channel_types) if channel_types is not None else None
        )
        self._family_overrides: Mapping[ChannelName, str] = (
            dict(family_overrides) if family_overrides is not None else {}
        )
        self._tau_floor = float(tau_floor)
        if not math.isfinite(self._tau_floor) or self._tau_floor <= 0.0:
            raise ValueError(f"tau_floor_must_be_positive_finite: got {tau_floor!r}")

        # Per-family instance cache (the strategies are stateless so
        # a single instance per family suffices; ``GumbelBlend`` is
        # parameterised on ``tau_floor`` so it gets its own
        # instance).
        self._strategies: dict[str, BlendStrategy] = {
            LINEAR_FAMILY: LinearBlend(),
            LOGIT_FAMILY: LogitBlend(),
            MASKED_FAMILY: MaskedBlend(),
            GUMBEL_FAMILY: GumbelBlend(tau_floor=tau_floor),
            SAMPLE_FAMILY: SampleBlend(),
            GRAPH_FAMILY: GraphBlend(),
        }

    @property
    def channel_types(self) -> Mapping[ChannelName, StateChannel] | None:
        """Return the configured per-channel type table (or ``None``)."""
        return self._channel_types

    @property
    def family_overrides(self) -> Mapping[ChannelName, str]:
        """Return the configured per-channel family overrides."""
        return dict(self._family_overrides)

    def strategy_for(self, channel: ChannelName) -> BlendStrategy:
        """Return the :class:`BlendStrategy` for ``channel``.

        Looks up the explicit override first, then falls back to the
        channel-kind → family table, then to :data:`LINEAR_FAMILY`
        for untyped channels.
        """
        ch_str = str(channel)
        family = self._family_overrides.get(ch_str)
        if family is None and self._channel_types is not None:
            kind = self._channel_types.get(channel)
            family = DEFAULT_BLEND_FAMILY_BY_CHANNEL.get(str(kind), LINEAR_FAMILY)
        if family is None:
            family = LINEAR_FAMILY
        strategy = self._strategies.get(family)
        if strategy is None:
            raise ValueError(f"unknown_blend_family:{family}")
        return strategy

    def blend_channel(
        self,
        channel: ChannelName,
        prior_value: Any,
        fresh_value: Any,
        *,
        memory_fraction: float,
        tau: float = DEFAULT_TAU_DEFAULT,
        mask: Any | None = None,
        audit_codes: list[str] | None = None,
    ) -> Any:
        """Dispatch ``blend`` to the per-channel :class:`BlendStrategy`.

        Emits :data:`PER_CHANNEL_BLEND_FALLTHROUGH` when the channel
        has no entry in the per-channel type table (canonical
        back-compat: ``LinearBlend`` semantics).
        """
        if audit_codes is None:
            audit_codes = []
        if (
            self._channel_types is None
            or str(channel) not in {str(k) for k in self._channel_types}
        ):
            audit_codes.append(PER_CHANNEL_BLEND_FALLTHROUGH)
        strategy = self.strategy_for(channel)
        return strategy.blend(
            prior_value,
            fresh_value,
            memory_fraction=memory_fraction,
            tau=tau,
            mask=mask,
            audit_codes=audit_codes,
        )

    def blend_all_channels(
        self,
        prior_values: Mapping[ChannelName, Any],
        fresh_values: Mapping[ChannelName, Any],
        *,
        memory_fraction_by_channel: Mapping[ChannelName, float],
        tau: float = DEFAULT_TAU_DEFAULT,
        mask_by_channel: Mapping[ChannelName, Any] | None = None,
        audit_codes: list[str] | None = None,
    ) -> dict[ChannelName, Any]:
        """Dispatch every channel in ``prior_values`` independently.

        Returns a ``dict[ChannelName, Any]`` of per-channel blended
        values; channels missing from ``fresh_values`` raise
        :class:`ValueError` so the dispatcher fails closed.
        """
        if audit_codes is None:
            audit_codes = []
        out: dict[ChannelName, Any] = {}
        for ch in prior_values:
            ch_str = str(ch)
            if ch_str not in {str(k) for k in fresh_values}:
                raise ValueError(f"fresh_value_missing_for_channel:{ch_str}")
            if ch_str not in {str(k) for k in memory_fraction_by_channel}:
                raise ValueError(f"memory_fraction_missing_for_channel:{ch_str}")
            m = memory_fraction_by_channel[ch]
            mask = (
                mask_by_channel.get(ch)
                if mask_by_channel is not None
                else None
            )
            out[ch] = self.blend_channel(
                ch,
                prior_values[ch],
                fresh_values[ch],
                memory_fraction=float(m),
                tau=tau,
                mask=mask,
                audit_codes=audit_codes,
            )
        return out


# ---------------------------------------------------------------------------
# Default factory
# ---------------------------------------------------------------------------


def default_per_channel_blender(
    channel_types: Mapping[ChannelName, StateChannel] | None = None,
) -> PerChannelBlender:
    """Return a canonical :class:`PerChannelBlender` instance.

    The factory accepts an optional ``channel_types`` table so the
    caller can wire the dispatcher's per-channel routing without
    instantiating the dataclass manually. The default ``None`` is
    the canonical back-compat (``LinearBlend`` for every channel).
    """
    return PerChannelBlender(channel_types=channel_types)


# ---------------------------------------------------------------------------
# Bundle-wrapping helper for adapter integration
# ---------------------------------------------------------------------------


def _wrap_value_as_state_bundle(
    *,
    template: Any,
    channel: ChannelName,
    blended_value: Any,
    blender_family: str,
    config_hash: str,
    audit_codes: tuple[str, ...],
) -> StateBundle:
    """Build a :class:`StateBundle` wrapping ``blended_value``.

    Mirrors the shape of
    :func:`adaptive_reflow.algorithm.blender._make_blend_bundle` but
    keeps the per-channel dispatcher self-contained. The returned
    bundle is total / side-effect-free and validates against
    :func:`validate_state_bundle`.

    ``native_state_digest`` is the SHA-256 of the canonical JSON
    representation of ``(family, channel, audit_codes, value)`` so
    two blends with identical inputs always yield identical
    digests (deterministic replay).
    """
    from adaptive_reflow.universal.adapter import AdapterCapabilities

    batch_id = str(getattr(template, "batch_id", "per-channel-batch"))
    sample_id = str(getattr(template, "sample_id", "per-channel-sample"))
    reference_frame = str(
        getattr(template, "reference_frame", "world")
    )
    if reference_frame not in ("pocket_centered", "world", "lattice"):
        reference_frame = "world"
    normalization = str(getattr(template, "normalization", "none"))
    if normalization not in ("none", "per_atom_std", "per_pocket_std"):
        normalization = "none"
    source_round = int(getattr(template, "source_round", 0))
    if source_round < 0:
        source_round = 0

    channels_attr = getattr(template, "channels", None)
    masks_attr = getattr(template, "masks", None)
    capability_token = getattr(template, "capability_token", None)
    if capability_token is None:
        capability_token = AdapterCapabilities(
            has_ode_integration_surface=False,
            has_prior_export=False,
            has_state_export=False,
            has_condition_injection=False,
            has_restart_boundary=False,
            has_continuous_channels=False,
            has_discrete_channels=False,
            has_trajectory_digest=False,
            has_deterministic_seed=False,
            has_materialization_route=False,
            supported_channels=(ChannelName(str(channel)),),
            channel_domains={ChannelName(str(channel)): "continuous"},
        )

    if isinstance(channels_attr, Mapping) and channels_attr:
        channels: dict[ChannelName, TensorRef] = {
            ChannelName(str(k)): TensorRef(str(v)) for k, v in channels_attr.items()
        }
    else:
        seed_blob = repr(
            ("per-channel-blend", channel, blended_value, audit_codes)
        ).encode("utf-8")
        channels = {
            ChannelName(str(channel)): TensorRef(
                f"per-channel-blend:{hashlib.sha256(seed_blob).hexdigest()[:16]}"
            )
        }

    masks: dict[str, TensorRef] = (
        {str(k): TensorRef(str(v)) for k, v in masks_attr.items()}
        if isinstance(masks_attr, Mapping)
        else {}
    )

    # Build the canonical digest payload.
    if isinstance(blended_value, np.ndarray):
        value_repr = repr(blended_value.tolist())
    elif isinstance(blended_value, Mapping):
        value_repr = repr({k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in blended_value.items()})
    else:
        value_repr = repr(blended_value)
    digest_payload = repr(
        (f"per_channel_blend:{blender_family}", str(channel), audit_codes, value_repr)
    ).encode("utf-8")
    next_digest = hashlib.sha256(digest_payload).hexdigest()

    provenance: tuple[str, ...] = (
        f"per_channel_blend:{blender_family}",
        f"per_channel_blend_config_hash:{config_hash}",
    ) + tuple(f"per_channel_blend_audit:{c}" for c in audit_codes)

    bundle = StateBundle(
        channels=channels,
        masks=masks,
        batch_id=batch_id,
        sample_id=sample_id,
        reference_frame=reference_frame,
        normalization=normalization,
        source_round=source_round,
        detach_proof=True,
        native_state_digest=next_digest,
        provenance=provenance,
        capability_token=capability_token,
    )
    ok, errs = validate_state_bundle(bundle)
    if not ok:
        raise AssertionError(f"per_channel_blend_bundle_invalid:{errs}")
    return bundle


__all__ = [
    "BLEND_FAMILY_BY_CHANNEL",
    "DEFAULT_BLEND_FAMILY_BY_CHANNEL",
    "DEFAULT_TAU_DEFAULT",
    "DEFAULT_TAU_FLOOR",
    "EPS_LOG",
    "GUMBEL_FAMILY",
    "GRAPH_FAMILY",
    "GumbelBlend",
    "LINEAR_FAMILY",
    "LinearBlend",
    "LOGIT_FAMILY",
    "LogitBlend",
    "MASKED_FAMILY",
    "MaskedBlend",
    "PER_CHANNEL_BLEND_FALLTHROUGH",
    "PER_CHANNEL_BLEND_MASK_FRESH_FALLBACK",
    "PER_CHANNEL_BLEND_M_ONE_SHORTCIRCUIT",
    "PER_CHANNEL_BLEND_M_ZERO_SHORTCIRCUIT",
    "PER_CHANNEL_BLEND_SENTINEL_PASSTHROUGH",
    "PER_CHANNEL_BLEND_TAU_FLOOR_HIT",
    "PerChannelBlender",
    "BlendStrategy",
    "SAMPLE_FAMILY",
    "STATE_CHANNELS",
    "SampleBlend",
    "GraphBlend",
    "default_per_channel_blender",
]
