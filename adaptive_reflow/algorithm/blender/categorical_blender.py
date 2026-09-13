"""Categorical-aware restart blender (D1 — sibling to LinearBlender / DistanceDecayBlender).

Lives at the algorithm layer (universal). Reads per-channel domain from
the existing :data:`ChannelDomain` literal (``universal/adapter.py``);
for ``"discrete"`` / ``"graph"`` channels it routes to logit-space
blend + softmax-renormalise + optional Gumbel-anneal sampling; for
``"continuous"`` / ``"latent"`` channels it delegates to LinearBlender
math.

Theory grounding: paper Theorem 1 (NoiseSelectedRectification_EN.md,
lines 87-92) gives BL-distance convergence of the noised profile
measure ``mu_{g,eps}`` to the sheet measure ``nu_g`` as ``eps -> 0``;
applied iteratively (round 1..N with ``eps_round -> 0``) the previous
round's endpoint is the posterior-mean proxy and the fresh draw is the
selection noise. For categorical outputs (FlowMol3 CTMC bond-types,
ProtBFN/AbBFN per-position amino-acid categorical, GraphBFN adjacency
logits) the SAME iterative principle applies but the math must
respect the simplex: linear ``m*p + (1-m)*f`` on raw labels is
entropy-INCREASING (mode-collapse direction — opposite of Theorem 1's
selection). The honest categorical equivalent lifts to logit space,
renormalises via softmax, then samples with Gumbel-anneal
(``tau: 1.0 -> 0.1`` across rounds per the user's prior fix attempt).
At ``tau -> 0`` the sampler degenerates to ``argmax`` (concentrated
selection toward the sheet); at ``tau = 1.0`` it samples from the
blend (full categorical). Theorem 1's ``eps_round`` now drives the
Gumbel temperature schedule so the sampler concentration increases
round-by-round.

Audit codes
-----------

* :data:`BLENDER_MEMORY_FRACTION_CLIPPED` (re-emitted on clip path,
  P1-A14 contract preserved)
* :data:`CATEGORICAL_BLEND_SENTINEL_PASSTHROUGH` (GraphBFN -inf diagonal
  detection)
* :data:`CATEGORICAL_BLEND_MASK_FRESH_FALLBACK` (FlowMol3 padded
  positions)
* :data:`CATEGORICAL_BLEND_TAU_FLOOR_HIT` (tau <= tau_floor -> argmax)

Module boundary
---------------

stdlib + numpy only. The categorical math (softmax, log-space
arithmetic, Gumbel sampling) cannot be expressed with stdlib-only
primitives without reinventing the wheel; numpy is the canonical
vehicle for tensor-shaped categorical data and is already used at the
molecule-layer for graph-shape tensors (``graphbfn.py``,
``flowmol3_v2_adapter.py``). No ``torch``, no I/O, no global state, no
mutation of inputs.

Public surface
--------------

* :class:`CategoricalAwareBlender` (concrete :class:`RestartBlenderProtocol`)
* :func:`default_categorical_blender` (canonical factory)
* Family identifier + audit-code constants
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any

import numpy as np

from adaptive_reflow.universal.state import (
    ChannelName,
    StateBundle,
    TensorRef,
    validate_state_bundle,
)

from .blender import (
    BLENDER_MEMORY_FRACTION_CLIPPED,
    DistanceDecayBlender,
    LinearBlender,
    RestartBlenderProtocol,
    _coerce_memory_fraction,
    _extract_channel_value,
    _make_blend_bundle,
)

# ---------------------------------------------------------------------------
# Module-level constants (family + config identifiers + audit codes)
# ---------------------------------------------------------------------------

CATEGORICAL_AWARE_FAMILY: str = "categorical_aware"
"""Blender family identifier for :class:`CategoricalAwareBlender`."""

DEFAULT_CATEGORICAL_AWARE_CONFIG_HASH: str = "blender:categorical_aware:v1"
"""Stable config hash for the default :class:`CategoricalAwareBlender`."""

DEFAULT_TAU_FLOOR: float = 0.1
"""Default Gumbel-anneal temperature floor.

Below this temperature the sampler degenerates to ``argmax`` (one-hot)
so the categorical selection is concentrated on the prior endpoint's
argmax — the canonical posterior-mode proxy under Theorem 1 selection.
"""

DEFAULT_TAU_SCHEDULE_KIND: str = "linear_anneal"
"""Default Gumbel-anneal temperature-schedule kind tag (audit-stable)."""

EPS_LOG: float = 1e-30
"""Log-space floor for softmax numerical stability."""

#: Audit code: GraphBFN -inf diagonal sentinel detected and passed
#: through without math (mirrors the ``graphbfn.py:281-287`` degenerate
#: weight short-circuit pattern).
CATEGORICAL_BLEND_SENTINEL_PASSTHROUGH: str = "categorical_blend_sentinel_passthrough"

#: Audit code: FlowMol3 padded positions (``mask == 0``) detected and
#: substituted with the fresh draw unconditionally (the prior is
#: structurally absent at those positions).
CATEGORICAL_BLEND_MASK_FRESH_FALLBACK: str = "categorical_blend_mask_fresh_fallback"

#: Audit code: Gumbel-anneal temperature fell below ``tau_floor`` and
#: the sampler degenerated to ``argmax`` (concentrated selection
#: toward the sheet).
CATEGORICAL_BLEND_TAU_FLOOR_HIT: str = "categorical_blend_tau_floor_hit"


# ---------------------------------------------------------------------------
# Concrete implementation
# ---------------------------------------------------------------------------


class CategoricalAwareBlender:
    """Domain-aware restart blender (sibling to LinearBlender / DistanceDecayBlender).

    Per-channel routing via :data:`ChannelDomain`:

    * ``"discrete"``: logit-space blend + softmax renormalise + optional
      Gumbel-anneal sampling.
    * ``"graph"``: same as ``"discrete"`` + sentinel short-circuit
      (``-inf`` diagonal passthrough) and upper-triangular mask
      handling.
    * ``"continuous"`` / ``"latent"``: delegate to :class:`LinearBlender`
      math (byte-stable continuous path).

    Configuration
    -------------

    * ``tau_floor``: ``float`` (default 0.1) — below this temperature
      the sampler degenerates to ``argmax`` (one-hot concentrated
      selection toward the sheet).
    * ``tau_schedule_kind``: ``str`` (default ``"linear_anneal"``) — kind
      tag for ``config_hash`` stability; the actual schedule is
      supplied per-call via the ``temperature`` kwarg so the audit
      trail records the per-round ``tau``.
    * ``sentinel_value``: ``float`` (default ``-inf``) — GraphBFN
      adjacency-diagonal short-circuit threshold; positions where
      either side carries the sentinel are passed through untouched.
    * ``eps_log``: ``float`` (default 1e-30) — log-space floor for
      softmax numerical stability.

    Family ID: :data:`CATEGORICAL_AWARE_FAMILY` (``"categorical_aware"``).
    """

    #: Family identifier. Class-level so tests + callers can introspect
    #: the constant without instantiating.
    FAMILY: str = CATEGORICAL_AWARE_FAMILY

    def __init__(
        self,
        *,
        tau_floor: float = DEFAULT_TAU_FLOOR,
        tau_schedule_kind: str = DEFAULT_TAU_SCHEDULE_KIND,
        sentinel_value: float = -math.inf,
        eps_log: float = EPS_LOG,
    ) -> None:
        if isinstance(tau_floor, bool) or not isinstance(tau_floor, (int, float)):
            raise ValueError("tau_floor_must_be_real_number")
        tf = float(tau_floor)
        if not math.isfinite(tf) or tf < 0.0:
            raise ValueError(f"tau_floor_must_be_nonneg_finite: got {tf!r}")
        if not isinstance(tau_schedule_kind, str) or not tau_schedule_kind:
            raise ValueError("tau_schedule_kind_must_be_nonempty_str")
        if isinstance(sentinel_value, bool) or not isinstance(sentinel_value, (int, float)):
            raise ValueError("sentinel_value_must_be_real_number")
        sv = float(sentinel_value)
        if math.isnan(sv):
            raise ValueError("sentinel_value_must_not_be_nan")
        if not math.isfinite(sv):
            # -inf is allowed (the GraphBFN default); +inf is rejected.
            if sv > 0.0:
                raise ValueError("sentinel_value_must_not_be_posinf")
        if isinstance(eps_log, bool) or not isinstance(eps_log, (int, float)):
            raise ValueError("eps_log_must_be_real_number")
        el = float(eps_log)
        if not math.isfinite(el) or el <= 0.0:
            raise ValueError(f"eps_log_must_be_positive_finite: got {el!r}")
        self._tau_floor = tf
        self._tau_schedule_kind = str(tau_schedule_kind)
        self._sentinel_value = sv
        self._eps_log = el

    @property
    def tau_floor(self) -> float:
        """Return the configured Gumbel temperature floor."""
        return float(self._tau_floor)

    @property
    def tau_schedule_kind(self) -> str:
        """Return the configured temperature-schedule kind tag."""
        return str(self._tau_schedule_kind)

    @property
    def sentinel_value(self) -> float:
        """Return the configured sentinel value for graph short-circuit."""
        return float(self._sentinel_value)

    @property
    def eps_log(self) -> float:
        """Return the configured log-space floor for softmax stability."""
        return float(self._eps_log)

    def blender_family(self) -> str:
        """Return :data:`CATEGORICAL_AWARE_FAMILY`."""
        return self.FAMILY

    def config_hash(self) -> str:
        """Return a stable digest of the categorical-aware-blender config.

        Two instances with the same constructor arguments compare equal
        (closes P2-3.3 — the audit trail must distinguish blenders
        constructed with different parameters).
        """
        sentinel_repr = (
            float(self._sentinel_value)
            if math.isfinite(self._sentinel_value)
            else "-inf"
        )
        payload = {
            "family": self.FAMILY,
            "qualname": type(self).__qualname__,
            "tau_floor": float(self._tau_floor),
            "tau_schedule_kind": str(self._tau_schedule_kind),
            "sentinel_value": sentinel_repr,
            "eps_log": float(self._eps_log),
        }
        text = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict (P1-1 round-trip)."""
        return {
            "family": CATEGORICAL_AWARE_FAMILY,
            "tau_floor": float(self._tau_floor),
            "tau_schedule_kind": str(self._tau_schedule_kind),
            "sentinel_value": (
                float(self._sentinel_value)
                if math.isfinite(self._sentinel_value)
                else "-inf"
            ),
            "eps_log": float(self._eps_log),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> CategoricalAwareBlender:
        """Build a :class:`CategoricalAwareBlender` from ``config``."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be dict, got {type(config).__name__}")
        sv = config.get("sentinel_value", -math.inf)
        if sv == "-inf":
            sv = -math.inf
        return cls(
            tau_floor=float(config.get("tau_floor", DEFAULT_TAU_FLOOR)),
            tau_schedule_kind=str(config.get("tau_schedule_kind", DEFAULT_TAU_SCHEDULE_KIND)),
            sentinel_value=float(sv),
            eps_log=float(config.get("eps_log", EPS_LOG)),
        )

    def blend(
        self,
        prior_state: Any,
        fresh_state: Any,
        *,
        memory_fraction: float,
        channel: str,
        audit_codes: list[str] | None = None,
        temperature: float | None = None,
        mask: np.ndarray | None = None,
        channel_domains: Mapping[str, str] | None = None,
    ) -> StateBundle:
        """Per-channel domain-aware blend.

        Routes to logit-space blend for ``"discrete"`` / ``"graph"``
        channels and to the canonical linear blend math for
        ``"continuous"`` / ``"latent"`` channels. Emits
        :data:`BLENDER_MEMORY_FRACTION_CLIPPED` on the clip path
        (P1-A14 contract preserved) and three categorical-specific
        audit codes on the respective short-circuit / fallback paths.

        Parameters
        ----------
        prior_state, fresh_state : Any
            StateBundle (or duck-typed carrier) holding the prior and
            freshly-sampled endpoint payloads.
        memory_fraction : float
            ``m`` ∈ [0, 1]; ``m -> 1`` collapses to the prior
            (posterior-mean proxy), ``m -> 0`` collapses to fresh
            (Theorem 1 selection noise).
        channel : str
            The channel name to blend.
        audit_codes : list[str] | None
            Optional audit list to which short-circuit / fallback codes
            are appended. ``None`` disables audit emission.
        temperature : float | None
            Optional Gumbel-anneal temperature. When ``None``, the
            blend returns probabilities (no sampling). When
            ``temperature <= tau_floor`` the sampler degenerates to
            ``argmax`` and emits :data:`CATEGORICAL_BLEND_TAU_FLOOR_HIT`.
        mask : np.ndarray | None
            Optional structural mask (FlowMol3 padded positions);
            ``mask == 0`` positions use the fresh draw unconditionally
            and emit :data:`CATEGORICAL_BLEND_MASK_FRESH_FALLBACK`.
        channel_domains : Mapping[str, str] | None
            Optional mapping from channel name to
            :data:`ChannelDomain`. Defaults to ``{}`` (treat every
            channel as ``"continuous"`` for the routing decision).
        """
        m = _coerce_memory_fraction(memory_fraction, audit_codes=audit_codes)
        domain_map = channel_domains if channel_domains is not None else {}
        domain = domain_map.get(str(channel), "continuous")
        if domain not in ("continuous", "discrete", "graph", "latent"):
            raise ValueError(f"unknown_channel_domain: {domain!r}")

        if domain in ("continuous", "latent"):
            # Byte-stable delegation to LinearBlender (P1-A14 audit
            # code already emitted by the clip path above if applicable).
            return LinearBlender().blend(
                prior_state,
                fresh_state,
                memory_fraction=m,
                channel=channel,
                audit_codes=audit_codes,
            )

        # Categorical path (discrete / graph).
        prior_value = _extract_channel_value(prior_state, channel)
        fresh_value = _extract_channel_value(fresh_state, channel)
        prior_arr = np.asarray(prior_value, dtype=np.float64)
        fresh_arr = np.asarray(fresh_value, dtype=np.float64)

        blended_probs = _logit_space_blend(
            prior=prior_arr,
            fresh=fresh_arr,
            memory_fraction=m,
            eps_log=self._eps_log,
        )

        if domain == "graph":
            blended_probs = _sentinel_short_circuit(
                prior=prior_arr,
                fresh=fresh_arr,
                blended=blended_probs,
                sentinel=self._sentinel_value,
                audit_codes=audit_codes,
            )

        if mask is not None:
            blended_probs = _masked_categorical_blend(
                blended=blended_probs,
                fresh=fresh_arr,
                mask=mask,
                audit_codes=audit_codes,
            )

        tau = self._resolve_temperature(temperature, audit_codes)
        if tau is None:
            # Deterministic probability return — caller samples.
            sampled = blended_probs
        elif tau <= self._tau_floor:
            if audit_codes is not None:
                audit_codes.append(CATEGORICAL_BLEND_TAU_FLOOR_HIT)
            # argmax degeneracy — one-hot per row.
            argmax_idx = blended_probs.argmax(axis=-1)
            sampled = np.zeros_like(blended_probs)
            rows = np.arange(blended_probs.shape[0])
            sampled[rows, argmax_idx] = 1.0
        else:
            sampled = _gumbel_anneal_sample(
                probs=blended_probs,
                temperature=tau,
                eps_log=self._eps_log,
            )

        flat = sampled.reshape(-1)
        flat_tuple = tuple(float(x) for x in flat)
        return _make_blend_bundle(
            prior_state,
            channel=channel,
            memory_fraction=m,
            blended_value=flat_tuple,
            blender_hash=self.config_hash(),
            blender_family=self.blender_family(),
            decay_factor=float(tau) if tau is not None else None,
        )

    def _resolve_temperature(
        self,
        temperature: float | None,
        audit_codes: list[str] | None,
    ) -> float | None:
        """Validate the optional ``temperature`` argument.

        Returns ``None`` if ``temperature`` was not supplied (caller
        wants probabilities only); otherwise returns the validated
        float.
        """
        if temperature is None:
            return None
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
            raise ValueError("temperature_must_be_real_number")
        t = float(temperature)
        if not math.isfinite(t) or t < 0.0:
            raise ValueError(f"temperature_must_be_nonneg_finite: got {t!r}")
        return t


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _logit_space_blend(
    *,
    prior: np.ndarray,
    fresh: np.ndarray,
    memory_fraction: float,
    eps_log: float,
) -> np.ndarray:
    """Compute logit-space blend: ``softmax(m*log(p+eps) + (1-m)*log(f+eps))``.

    Lifts both inputs to log-space, blends there (preserves the simplex
    constraint under convex combination), then renormalises via
    softmax. Limits:

    * ``m -> 1`` collapses to the prior (posterior-mean proxy).
    * ``m -> 0`` collapses to the fresh draw (Theorem 1 selection
      noise).

    Raises ``ValueError`` on shape mismatch.
    """
    if prior.shape != fresh.shape:
        raise ValueError(
            f"prior_fresh_shape_mismatch: prior={prior.shape} fresh={fresh.shape}"
        )
    m = float(memory_fraction)
    prior_safe = np.maximum(prior, 0.0) + float(eps_log)
    fresh_safe = np.maximum(fresh, 0.0) + float(eps_log)
    log_prior = np.log(prior_safe)
    log_fresh = np.log(fresh_safe)
    log_blend = m * log_prior + (1.0 - m) * log_fresh
    log_blend = log_blend - log_blend.max(axis=-1, keepdims=True)
    exp_lb = np.exp(log_blend)
    denom = exp_lb.sum(axis=-1, keepdims=True)
    denom = np.maximum(denom, float(eps_log))
    return exp_lb / denom


def _sentinel_short_circuit(
    *,
    prior: np.ndarray,
    fresh: np.ndarray,
    blended: np.ndarray,
    sentinel: float,
    audit_codes: list[str] | None,
) -> np.ndarray:
    """Pass through positions where prior OR fresh carry the sentinel value.

    GraphBFN adjacency diagonal carries ``-inf`` sentinels; the general
    formula ``0.0 * -inf = NaN`` would silently convert the masked
    self-loop into a NaN logit. Detection: positions where either side
    equals the sentinel value are emitted untouched (surviving side;
    default to fresh if both). Emits
    :data:`CATEGORICAL_BLEND_SENTINEL_PASSTHROUGH` per detected position.

    Sentinel-mask shape mirrors ``blended`` (per-element) so the
    broadcast aligns. The surviving-side rule is: if ``prior !=
    sentinel`` use prior, else use fresh.
    """
    sentinel_mask = (prior == sentinel) | (fresh == sentinel)
    n_sentinel = int(sentinel_mask.sum())
    if n_sentinel == 0:
        return blended
    if audit_codes is not None:
        audit_codes.append(
            f"{CATEGORICAL_BLEND_SENTINEL_PASSTHROUGH}:n={n_sentinel}"
        )
    # Build a "use_prior" mask of the same shape as blended: True where
    # prior is NOT the sentinel value at that position.
    use_prior = prior != sentinel
    # Where sentinel applies, emit (use_prior ? prior : fresh).
    out = np.where(use_prior, prior, fresh)
    # Where no sentinel applies, fall back to the blended value.
    return np.where(sentinel_mask, out, blended)


def _masked_categorical_blend(
    *,
    blended: np.ndarray,
    fresh: np.ndarray,
    mask: np.ndarray,
    audit_codes: list[str] | None,
) -> np.ndarray:
    """``mask == 0`` positions fall back to fresh draw unconditionally.

    FlowMol3 carries padded positions (extra atoms beyond prior size)
    where the prior is structurally absent. ``mask == 0`` says "this
    slot is padding; use the fresh draw". Emits
    :data:`CATEGORICAL_BLEND_MASK_FRESH_FALLBACK` per fallback position.

    Mask semantics: ``mask == 1`` (default / True) means "blend" and
    ``mask == 0`` means "use fresh". Adapters with inverted mask
    semantics must invert the mask before passing.
    """
    mask_arr = np.asarray(mask, dtype=np.float64)
    if mask_arr.shape != blended.shape[:-1]:
        raise ValueError(
            f"mask_shape_mismatch: mask={mask_arr.shape} blended={blended.shape}"
        )
    fallback_mask = mask_arr == 0.0
    n_fallback = int(fallback_mask.sum())
    if n_fallback > 0:
        if audit_codes is not None:
            audit_codes.append(
                f"{CATEGORICAL_BLEND_MASK_FRESH_FALLBACK}:n={n_fallback}"
            )
        broadcast = np.broadcast_to(fallback_mask[..., None], blended.shape)
        return np.where(broadcast, fresh, blended)
    return blended


def _gumbel_anneal_sample(
    *,
    probs: np.ndarray,
    temperature: float,
    eps_log: float,
) -> np.ndarray:
    """Gumbel-anneal categorical sample (deterministic seed-free form).

    At ``temperature = 1.0`` samples from the categorical (full
    stochasticity); at ``temperature <= tau_floor`` degenerates to
    ``argmax`` (concentrated selection); ``tau`` in between produces
    the annealed regime. The output is a one-hot / soft categorical
    tensor with the same shape as ``probs``.

    NOTE: This helper is non-deterministic by design (rng drawn from
    ``np.random.default_rng()`` without a seed). For deterministic
    sampling, callers should sample externally and pass the result as
    the ``fresh_state`` instead. The framework's audit trail records
    the per-call ``tau`` so the determinism question is per-round
    traceable.
    """
    rng = np.random.default_rng()
    log_p = np.log(np.maximum(probs, 0.0) + float(eps_log))
    uniform = np.maximum(rng.random(log_p.shape), float(eps_log))
    gumbel = -np.log(-np.log(uniform) + float(eps_log)) + float(eps_log)
    return np.exp((log_p + gumbel) / max(float(temperature), float(eps_log)))


# ---------------------------------------------------------------------------
# Default factory
# ---------------------------------------------------------------------------


def default_categorical_blender() -> CategoricalAwareBlender:
    """Return the canonical :class:`CategoricalAwareBlender` factory.

    The blender is cheap to construct (no state other than constructor
    args) so callers may also instantiate :class:`CategoricalAwareBlender`
    directly. This factory is the single entry point used by adapter
    wiring so the wrapper and the canonical categorical blender can
    never drift.
    """
    return CategoricalAwareBlender()


# ---------------------------------------------------------------------------
# Parameter-free default-eps-log entry point (DERIV-001 P-19 #12)
# ---------------------------------------------------------------------------


def derive_default_eps_log(
    *,
    e_rho: float | None = None,
    context: Any | None = None,
    rule: Any | None = None,
) -> float:
    """Return ``EPS_LOG`` from a derivation rule.

    Falls back to ``1e-30`` on missing context. The closed form is
    ``eps_log := e_rho / 8`` (paper-quantity exterior gap, Lemma 5).
    """
    from adaptive_reflow.algorithm._derivation import (
        default_eps_log as _d,
    )
    return _d(context, e_rho=e_rho, rule=rule)


__all__ = [
    "CATEGORICAL_AWARE_FAMILY",
    "CATEGORICAL_BLEND_MASK_FRESH_FALLBACK",
    "CATEGORICAL_BLEND_SENTINEL_PASSTHROUGH",
    "CATEGORICAL_BLEND_TAU_FLOOR_HIT",
    "DEFAULT_CATEGORICAL_AWARE_CONFIG_HASH",
    "DEFAULT_TAU_FLOOR",
    "DEFAULT_TAU_SCHEDULE_KIND",
    "CategoricalAwareBlender",
    "default_categorical_blender",
]
