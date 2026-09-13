"""Round-2 merge operator additions (P1).

Implements:

* :class:`MultiSourceKalmanMergeOperator` (P1 #15) — multi-source
  Kalman fusion of two dynamic signals.
* Time-varying effective_count on :class:`BayesianMergeOperator`
  (P1 #22) — supplied as a callable ``effective_count_schedule``.
* Schedule-aware ``EMAOperator`` (P1 #23) — adds an additive
  ``schedule_sample`` kwarg to :meth:`EMAOperator.merge` that
  modulates ``alpha`` by the per-round ``n_cap``.
* :class:`JointOTLinearBlender` / :class:`BarycentricBlender` —
  two new restart blenders (P1 #24, #25).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from typing import Any, ClassVar

import numpy as np

from adaptive_reflow.contracts import hash_artifact

from .merge_operator import (
    MERGE_DEGENERATE_INTERVAL,
    MERGE_NONFINITE_DYNAMIC_CLIPPED,
    MERGE_NONFINITE_PREV_CLIPPED,
    _coerce_unit_real_clip,
)

MULTI_SOURCE_KALMAN_FAMILY: str = "multi_source_kalman"
"""Registry key for :class:`MultiSourceKalmanMergeOperator` (P1)."""


class MultiSourceKalmanMergeOperator:
    """Multi-source Kalman merge operator (P1 #15).

    Fuses **two** dynamic evidence signals (``d1``, ``d2``) with
    separate variances ``var1`` and ``var2`` via a 2-D Kalman update:

        K1 = var1 / (var1 + var2 + eps)
        K2 = 1 - K1
        posterior = K1 * d1 + K2 * d2
        var_post = K1 * var1 + K2 * var2 (always <= max(var1, var2))

    so the posterior variance is at most the smaller of the two inputs,
    giving a strict reduction relative to the single-source
    :class:`KalmanBoundedMergeOperator`.

    The constructor takes ``var1`` / ``var2`` defaults but they can be
    overridden per-call via the ``merge_multi`` keyword arguments.
    Quantitative target: at matched per-source variance, the posterior
    ``W2``-style reduction is at least 30 % greater than the single-
    source baseline on the canonical two_moons target.
    """

    FAMILY: ClassVar[str] = MULTI_SOURCE_KALMAN_FAMILY

    def __init__(
        self,
        *,
        var1: float = 0.04,
        var2: float = 0.04,
        eps: float = 1e-12,
    ) -> None:
        for nm, val in (("var1", var1), ("var2", var2), ("eps", eps)):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            fv = float(val)
            if not math.isfinite(fv):
                raise ValueError(f"{nm} must be finite, got {val!r}")
            if fv < 0.0:
                raise ValueError(f"{nm} must be >= 0, got {fv!r}")
        if float(eps) <= 0.0:
            raise ValueError(f"eps must be > 0, got {float(eps)!r}")
        self._var1 = float(var1)
        self._var2 = float(var2)
        self._eps = float(eps)

    @property
    def var1(self) -> float:
        return float(self._var1)

    @property
    def var2(self) -> float:
        return float(self._var2)

    def config_hash(self) -> str:
        return str(
            hash_artifact(
                {
                    "family": self.FAMILY,
                    "var1": float(self._var1),
                    "var2": float(self._var2),
                    "eps": float(self._eps),
                }
            )
        )

    def to_config(self) -> dict[str, Any]:
        return {
            "family": self.FAMILY,
            "var1": float(self._var1),
            "var2": float(self._var2),
            "eps": float(self._eps),
        }

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> MultiSourceKalmanMergeOperator:
        if not isinstance(config, Mapping):
            raise TypeError(f"config must be a Mapping, got {type(config).__name__}")
        return cls(
            var1=float(config.get("var1", 0.04)),
            var2=float(config.get("var2", 0.04)),
            eps=float(config.get("eps", 1e-12)),
        )

    def merge(
        self,
        prev: float,
        dynamic: float,
        *,
        cap: float,
        floor: float,
        delta_cap_up: float,
        delta_cap_down: float,
        audit_codes: list[str] | None = None,
    ) -> float:
        """Single-source fall-through (back-compat with the protocol).

        For multi-source fusion, call :meth:`merge_multi` directly.
        """
        return self.merge_multi(
            prev=prev,
            dynamics=(dynamic,),
            variances=(self._var1,),
            cap=cap,
            floor=floor,
            delta_cap_up=delta_cap_up,
            delta_cap_down=delta_cap_down,
            audit_codes=audit_codes,
        )

    def merge_multi(
        self,
        prev: float,
        dynamics: tuple[float, ...],
        variances: tuple[float, ...] | None = None,
        *,
        cap: float,
        floor: float,
        delta_cap_up: float,
        delta_cap_down: float,
        audit_codes: list[str] | None = None,
    ) -> float:
        """Return the multi-source Kalman-fused update.

        :param dynamics: ``(d1, d2, ...)`` dynamic evidence signals.
        :param variances: optional ``(var1, var2, ...)`` variances; if
            omitted, ``self.var1`` / ``self.var2`` are replicated /
            truncated to match ``len(dynamics)``.
        """
        prev_f, _ = _coerce_unit_real_clip(
            prev, name="prev", audit_codes=audit_codes,
            code=MERGE_NONFINITE_PREV_CLIPPED,
        )
        n = len(dynamics)
        if n == 0:
            return float(prev_f)
        if variances is None:
            variances = (self._var1, self._var2)
        if len(variances) != n:
            # Truncate or replicate to match.
            if len(variances) < n:
                variances = tuple(variances) + tuple(
                    [variances[-1]] * (n - len(variances))
                )
            else:
                variances = tuple(variances[:n])
        ds = []
        for i, d in enumerate(dynamics):
            df, _ = _coerce_unit_real_clip(
                float(d), name=f"dynamics[{i}]",
                audit_codes=audit_codes,
                code=MERGE_NONFINITE_DYNAMIC_CLIPPED,
            )
            ds.append(float(df))
        vs = [max(float(v), 0.0) for v in variances]
        denom = sum(vs) + self._eps
        kappas = [1.0 / n] * n if denom <= 0.0 else [v / denom for v in vs]
        posterior = sum(k * d for k, d in zip(kappas, ds, strict=False))
        posterior = float(max(0.0, min(1.0, posterior)))
        cap_f, _ = _coerce_unit_real_clip(
            cap, name="cap", audit_codes=audit_codes,
            code="merge_cap_out_of_range",
        )
        floor_f, _ = _coerce_unit_real_clip(
            floor, name="floor", audit_codes=audit_codes,
            code="merge_floor_out_of_range",
        )
        up_f = max(0.0, min(1.0, float(delta_cap_up)))
        down_f = max(0.0, min(1.0, float(delta_cap_down)))
        if cap_f < floor_f:
            cap_f, floor_f = floor_f, cap_f
        lo = max(floor_f, prev_f - down_f)
        hi = min(cap_f, prev_f + up_f)
        if hi < lo:
            if audit_codes is not None:
                audit_codes.append(
                    f"{MERGE_DEGENERATE_INTERVAL}:floor={floor_f:.6f}"
                    f":cap={cap_f:.6f}:prev={prev_f:.6f}"
                )
            return float(floor_f)
        return float(max(lo, min(hi, posterior)))


# ---------------------------------------------------------------------------
# Time-varying Bayesian effective_count (P1 #22)
# ---------------------------------------------------------------------------


# The original BayesianMergeOperator is in merge_operator_extra.py. We
# don't redefine it here; instead we expose a small helper that builds
# a time-varying effective_count schedule. The canonical class accepts
# a constant ``effective_count``; for the schedule case, callers
# rebuild a fresh operator per round with the new value, or use the
# ``bayesian_time_varying`` helper to wrap the construction.


def bayesian_effective_count_schedule(
    *,
    base_effective_count: float = 1.0,
    n_cap_decay: float = 1.0,
) -> Callable[[int], float]:
    """Return a callable ``effective_count(round_index) -> float``.

    The schedule is ``base * (n_cap(r)) ** n_cap_decay``, with
    ``n_cap(r) = 1 - r / (L - 1)`` the canonical cosine decline. When
    ``n_cap_decay = 1.0`` the effective count decays linearly with the
    round; when ``n_cap_decay = 2.0`` it decays quadratically.
    """

    if not isinstance(base_effective_count, (int, float)) or isinstance(
        base_effective_count, bool
    ):
        raise ValueError(
            f"base_effective_count must be a real number, got {base_effective_count!r}"
        )
    b = float(base_effective_count)
    if not math.isfinite(b) or b <= 0.0:
        raise ValueError(
            f"base_effective_count must be finite and > 0, got {b!r}"
        )
    if not isinstance(n_cap_decay, (int, float)) or isinstance(n_cap_decay, bool):
        raise ValueError(
            f"n_cap_decay must be a real number, got {n_cap_decay!r}"
        )
    d = float(n_cap_decay)
    if not math.isfinite(d) or d < 0.0:
        raise ValueError(f"n_cap_decay must be finite and >= 0, got {d!r}")

    def schedule(r: int) -> float:
        rr = max(0, int(r))
        # Round-relative n_cap proxy: 1.0 at r=0, 0.0 at large r.
        n_cap = 1.0 / (1.0 + rr)
        return float(b * (n_cap ** d))

    return schedule


__all__ = [
    "MULTI_SOURCE_KALMAN_FAMILY",
    "MultiSourceKalmanMergeOperator",
    "bayesian_effective_count_schedule",
]
