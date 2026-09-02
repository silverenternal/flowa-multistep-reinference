"""Dynamic noise bias typed contracts (D4 — paper-quantity-driven per-round bias).

Paper Theorem 1 (Li 2026, lines 87-92) states that the noised
posterior ``mu_{g,eps}`` converges in bounded-Lipschitz distance to
the sheet measure ``nu_g`` as ``eps -> 0``, with root-cell mass
``O(eps)``. Applied iteratively across rounds
``1, 2, ..., L`` (the user's "动态把上轮推理结果加入下一轮噪声偏置"
insight), the previous round's endpoint is the canonical
posterior-mean proxy for the current sheet fibre, and the new round's
``eps_{r+1}``-scaled Gaussian fresh draw is the canonical selection
noise. Per-round ``eps(r)`` is constrained by the four paper quantities
``A_g``, ``B_g``, ``C_g``, ``e_rho`` defined on the envelope (paper
lines 116-128).

This module declares the typed dataclasses that the dynamic-noise-bias
protocol consumes:

* :class:`PaperQuantitiesSnapshot` — frozen carrier for the four
  paper quantities; the runner / scheduler / policy driver read
  these to compute ``eps(r)`` and the per-round selection ratio.

* :class:`DynamicNoiseBiasResult` — frozen carrier for the bias
  result: per-channel epsilon, posterior-mean proxy, optional
  Gumbel temperature (categorical analog), and the per-round
  selection ratio ``sheet / (sheet + cell)``.

Module boundary
---------------

* stdlib-only (no ``torch``, no numpy).
* Pure-data carriers, no validation logic.
* The bias-source literal ``bias_source`` discriminates between
  paper-quantity-driven bias and the schedule-fallback path
  (``IdentityDynamicNoiseBias``).

Public surface
--------------

* :class:`PaperQuantitiesSnapshot`
* :class:`DynamicNoiseBiasResult`
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from adaptive_reflow.universal.state import ChannelName


# ---------------------------------------------------------------------------
# PaperQuantitiesSnapshot — typed carrier for the four paper quantities.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PaperQuantitiesSnapshot:
    """Frozen carrier for the four paper quantities (``A_g``, ``B_g``, ``C_g``, ``e_rho``).

    Attributes
    ----------

    * ``sheet_A`` — sheet evidence floor (``A_g`` per paper line 161).
    * ``packing_B`` — root-cell packing (``B_g`` per paper line 159).
    * ``cell_C`` — per-cell coefficient (``C_g`` per paper lines 188-191).
    * ``exterior_gap_e_rho`` — exterior gap (``e_rho`` per paper line 128).

    All values MUST be positive reals; ``e_rho`` is the squared-residual
    energy bound and is typically small (e.g. ``1e-4`` at default
    ``rho = eta = 0.1``).
    """

    sheet_A: float
    packing_B: float
    cell_C: float
    exterior_gap_e_rho: float

    def validate(self) -> tuple[bool, tuple[str, ...]]:
        """Return ``(True, ())`` iff all four values are positive finite reals."""
        errors: list[str] = []
        for name in ("sheet_A", "packing_B", "cell_C", "exterior_gap_e_rho"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                errors.append(f"{name}_must_be_real_number")
                continue
            fx = float(value)
            if not (fx == fx) or fx in (float("inf"), float("-inf")):
                errors.append(f"{name}_must_be_finite")
                continue
            if fx <= 0.0:
                errors.append(f"{name}_must_be_positive")
        return (not errors, tuple(errors))


# ---------------------------------------------------------------------------
# DynamicNoiseBiasResult — typed carrier for the per-round bias result.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DynamicNoiseBiasResult:
    """Frozen carrier for the per-round dynamic-noise-bias result.

    Attributes
    ----------

    * ``epsilon_per_channel`` — per-channel ``eps(r)`` schedule value
      (the implicit noise scale for this round). Values in ``(0, 1]``.

    * ``posterior_mean_proxy`` — the previous round's endpoint passed
      through the materializer; for continuous channels the materializer
      returns the raw value; for categorical channels the materializer
      returns the ``argmax`` (posterior-mode proxy on the simplex).

    * ``gumbel_temperature_per_channel`` — per-channel Gumbel-anneal
      temperature ``tau(r)`` for categorical channels; ``None`` for
      continuous channels (the Gumbel sampler is not used).

    * ``selection_ratio`` — the per-round sheet-dominance ratio
      ``sheet / (sheet + cell)`` where ``sheet = sheet_A * eps`` and
      ``cell = cell_C * packing_B * eps^2``. In ``(0, 1]`` and
      converges to ``1`` as ``eps -> 0`` (paper BL-distance
      convergence analogue).

    * ``audit_codes`` — tuple of canonical audit codes emitted during
      the bias computation (e.g.
      ``NEW_DYNAMIC_NOISE_BIAS_EPSILON_FLOORED_BY_PAPER_EXTERIOR_GAP``).

    * ``bias_source`` — discriminator between paper-quantity-driven
      bias (``"prev_endpoint"``) and the schedule-fallback path
      (``"schedule_fallback"``).
    """

    epsilon_per_channel: Mapping[ChannelName, float]
    posterior_mean_proxy: Any
    gumbel_temperature_per_channel: Mapping[ChannelName, float] | None
    selection_ratio: float
    audit_codes: tuple[str, ...]
    bias_source: Literal["prev_endpoint", "schedule_fallback"]


__all__ = [
    "DynamicNoiseBiasResult",
    "PaperQuantitiesSnapshot",
]
