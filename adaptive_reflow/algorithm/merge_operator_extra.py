"""Extra P0/P1 merge operator implementations.

Adds four :class:`MergeOperatorProtocol` implementations called out by
the algorithm-deep-uplift plan:

* :class:`KalmanBoundedMergeOperator` — variance-tracking Kalman-style
  bounded merge that maintains ``(beta, sigma^2)`` and updates via
  ``K = sigma^2_prior / (sigma^2_prior + sigma^2_dyn)`` (P0).
* :class:`BayesianMergeOperator` — Beta-Bernoulli posterior merge that
  treats ``dynamic`` as a Bernoulli evidence ratio and updates the
  ``(alpha, beta)`` Beta parameters accordingly (P1).
* :class:`PIDIdentityOperator` — pass-through with a PID-lite damping
  term on the residual ``dynamic - prev`` (P1).
* :class:`ScheduleAwareEMAOperator` — EMA whose smoothing factor
  ``alpha(r) = alpha_min + (alpha_max - alpha_min) * n_cap(r)`` tracks
  the schedule's per-round ``n_cap`` (P1).

All four follow the canonical ``MergeOperatorProtocol`` surface
(``merge``, ``to_config`` / ``from_config``) and respect the
clip-and-audit policy from :mod:`adaptive_reflow.algorithm.merge_operator`.

Module boundary
---------------

* stdlib-only. No ``torch``. No I/O. No mutation of inputs.
* Fail-closed on bad input — out-of-range / non-numeric constructor
  arguments raise :class:`ValueError`.
"""
from __future__ import annotations

import math
from typing import Any, ClassVar

from adaptive_reflow.contracts import hash_artifact

from .merge_operator import (
    MERGE_DEGENERATE_INTERVAL,
    MERGE_NONFINITE_DYNAMIC_CLIPPED,
    MERGE_NONFINITE_PREV_CLIPPED,
    MergeOperatorProtocol,
    _coerce_unit_real_clip,
)


class KalmanBoundedMergeOperator:
    """Kalman-style bounded merge with variance tracking (P0).

    Maintains ``(beta, sigma^2)`` as the running state. The
    per-update rule is

        K_t = sigma^2_prior / (sigma^2_prior + sigma^2_dyn + eps)
        beta_post = clip(beta_prior + K_t * (dynamic - beta_prior),
                         max(floor, prev - delta_cap_down),
                         min(cap, prev + delta_cap_up))
        sigma^2_post = (1 - K_t) * sigma^2_prior

    so ``K_t -> 1`` when the dynamic's variance is small (trust the
    measurement) and ``K_t -> 0`` when the dynamic's variance is large
    (trust the prior). The result is then bounded into the same
    ``[floor, cap]`` envelope as :class:`BoundedMergeOperator` so the
    framework invariant is preserved.

    :param prior_variance: initial variance of the prior ``beta``
        estimate (``sigma^2_prior``). Must be non-negative.
    :param dynamic_variance: known variance of the dynamic evidence
        signal (``sigma^2_dyn``). Must be non-negative.
    """

    FAMILY: ClassVar[str] = "kalman_bounded"

    def __init__(
        self,
        *,
        prior_variance: float = 0.01,
        dynamic_variance: float = 0.04,
        eps: float = 1e-12,
        exterior_gap_e_rho: float | None = None,
    ) -> None:
        for nm, val in (
            ("prior_variance", prior_variance),
            ("dynamic_variance", dynamic_variance),
            ("eps", eps),
        ):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            fv = float(val)
            if not math.isfinite(fv):
                raise ValueError(f"{nm} must be finite, got {val!r}")
            if fv < 0.0:
                raise ValueError(f"{nm} must be >= 0, got {fv!r}")
        if float(eps) <= 0.0:
            raise ValueError(f"eps must be > 0, got {float(eps)!r}")
        self._prior_variance = float(prior_variance)
        self._dynamic_variance = float(dynamic_variance)
        self._eps = float(eps)
        if exterior_gap_e_rho is None:
            self._exterior_gap_e_rho: float | None = None
        else:
            if isinstance(exterior_gap_e_rho, bool) or not isinstance(
                exterior_gap_e_rho, (int, float)
            ):
                raise ValueError(
                    "exterior_gap_e_rho must be a real number, got "
                    f"{exterior_gap_e_rho!r}"
                )
            ef = float(exterior_gap_e_rho)
            if not math.isfinite(ef) or ef < 0.0:
                raise ValueError(
                    "exterior_gap_e_rho must be finite and >= 0, "
                    f"got {ef!r}"
                )
            self._exterior_gap_e_rho = ef

    @property
    def prior_variance(self) -> float:
        return float(self._prior_variance)

    @property
    def dynamic_variance(self) -> float:
        return float(self._dynamic_variance)

    def config_hash(self) -> str:
        """Stable digest capturing every constructor argument."""
        return str(
            hash_artifact(
                {
                    "family": self.FAMILY,
                    "prior_variance": float(self._prior_variance),
                    "dynamic_variance": float(self._dynamic_variance),
                    "eps": float(self._eps),
                    "exterior_gap_e_rho": (
                        None
                        if self._exterior_gap_e_rho is None
                        else float(self._exterior_gap_e_rho)
                    ),
                }
            )
        )

    def to_config(self) -> dict[str, Any]:
        return {
            "family": self.FAMILY,
            "prior_variance": float(self._prior_variance),
            "dynamic_variance": float(self._dynamic_variance),
            "eps": float(self._eps),
            "exterior_gap_e_rho": (
                None
                if self._exterior_gap_e_rho is None
                else float(self._exterior_gap_e_rho)
            ),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> KalmanBoundedMergeOperator:
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        return cls(
            prior_variance=float(config.get("prior_variance", 0.01)),
            dynamic_variance=float(config.get("dynamic_variance", 0.04)),
            eps=float(config.get("eps", 1e-12)),
            exterior_gap_e_rho=(
                None
                if config.get("exterior_gap_e_rho") is None
                else float(config["exterior_gap_e_rho"])
            ),
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
        prev_f, _ = _coerce_unit_real_clip(
            prev, name="prev", audit_codes=audit_codes,
            code=MERGE_NONFINITE_PREV_CLIPPED,
        )
        dynamic_f, _ = _coerce_unit_real_clip(
            dynamic, name="dynamic", audit_codes=audit_codes,
            code=MERGE_NONFINITE_DYNAMIC_CLIPPED,
        )
        cap_f, _ = _coerce_unit_real_clip(
            cap, name="cap", audit_codes=audit_codes,
            code="merge_cap_out_of_range",
        )
        floor_f, _ = _coerce_unit_real_clip(
            floor, name="floor", audit_codes=audit_codes,
            code="merge_floor_out_of_range",
        )
        if self._exterior_gap_e_rho is not None:
            paper_floor = self._exterior_gap_e_rho / 4.0
            if floor_f < paper_floor:
                floor_f = float(paper_floor)
        up_f = max(0.0, min(1.0, float(delta_cap_up)))
        down_f = max(0.0, min(1.0, float(delta_cap_down)))
        if cap_f < floor_f:
            new_cap = floor_f
            new_floor = cap_f
            if audit_codes is not None:
                audit_codes.append(
                    f"merge_cap_below_floor:cap={cap_f:.6f}:floor={floor_f:.6f}"
                )
            cap_f = new_cap
            floor_f = new_floor
        # Kalman update on the unconstrained envelope.
        s2_prior = max(self._prior_variance, 0.0)
        s2_dyn = max(self._dynamic_variance, 0.0)
        denom = s2_prior + s2_dyn + self._eps
        K = s2_prior / denom if denom > 0.0 else 0.0
        target = prev_f + K * (dynamic_f - prev_f)
        target = max(0.0, min(1.0, float(target)))
        # Re-bound into the (clamped) envelope + delta caps.
        lo = max(floor_f, prev_f - down_f)
        hi = min(cap_f, prev_f + up_f)
        if hi < lo:
            if audit_codes is not None:
                audit_codes.append(
                    f"{MERGE_DEGENERATE_INTERVAL}:floor={floor_f:.6f}"
                    f":cap={cap_f:.6f}:prev={prev_f:.6f}"
                    f":up={up_f:.6f}:down={down_f:.6f}"
                )
            return float(floor_f)
        return float(max(lo, min(hi, target)))


class BayesianMergeOperator:
    """Beta-Bernoulli posterior merge operator (P1).

    Treats ``dynamic`` as a Bernoulli evidence ratio in ``[0, 1]`` and
    updates the Beta posterior

        alpha_post = alpha_prior + dynamic * effective_count
        beta_post  = beta_prior + (1 - dynamic) * effective_count

    so the Beta mean shifts toward ``dynamic`` scaled by
    ``effective_count``. The point estimate returned is

        beta_mean = alpha_post / (alpha_post + beta_post)

    which is then bounded into the ``[floor, cap]`` envelope and the
    delta-caps ``[prev - delta_cap_down, prev + delta_cap_up]``.

    Default hyperparameters: ``alpha_prior = beta_prior = 1.0``
    (uniform Beta prior), ``effective_count = 1.0``.
    """

    FAMILY: ClassVar[str] = "bayesian"

    def __init__(
        self,
        *,
        alpha_prior: float = 1.0,
        beta_prior: float = 1.0,
        effective_count: float = 1.0,
    ) -> None:
        for nm, val in (
            ("alpha_prior", alpha_prior),
            ("beta_prior", beta_prior),
            ("effective_count", effective_count),
        ):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            fv = float(val)
            if not math.isfinite(fv):
                raise ValueError(f"{nm} must be finite, got {val!r}")
            if fv <= 0.0:
                raise ValueError(f"{nm} must be > 0, got {fv!r}")
        self._alpha_prior = float(alpha_prior)
        self._beta_prior = float(beta_prior)
        self._effective_count = float(effective_count)

    @property
    def alpha_prior(self) -> float:
        return float(self._alpha_prior)

    @property
    def beta_prior(self) -> float:
        return float(self._beta_prior)

    @property
    def effective_count(self) -> float:
        return float(self._effective_count)

    def config_hash(self) -> str:
        """Stable digest capturing every constructor argument."""
        return str(
            hash_artifact(
                {
                    "family": self.FAMILY,
                    "alpha_prior": float(self._alpha_prior),
                    "beta_prior": float(self._beta_prior),
                    "effective_count": float(self._effective_count),
                }
            )
        )

    def to_config(self) -> dict[str, Any]:
        return {
            "family": self.FAMILY,
            "alpha_prior": float(self._alpha_prior),
            "beta_prior": float(self._beta_prior),
            "effective_count": float(self._effective_count),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> BayesianMergeOperator:
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        return cls(
            alpha_prior=float(config.get("alpha_prior", 1.0)),
            beta_prior=float(config.get("beta_prior", 1.0)),
            effective_count=float(config.get("effective_count", 1.0)),
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
        prev_f, _ = _coerce_unit_real_clip(
            prev, name="prev", audit_codes=audit_codes,
            code=MERGE_NONFINITE_PREV_CLIPPED,
        )
        dynamic_f, _ = _coerce_unit_real_clip(
            dynamic, name="dynamic", audit_codes=audit_codes,
            code=MERGE_NONFINITE_DYNAMIC_CLIPPED,
        )
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
        # Posterior update.
        alpha_post = self._alpha_prior + dynamic_f * self._effective_count
        beta_post = self._beta_prior + (1.0 - dynamic_f) * self._effective_count
        denom = alpha_post + beta_post
        target = (
            float(alpha_post) / float(denom) if denom > 0.0 else float(prev_f)
        )
        target = max(0.0, min(1.0, float(target)))
        lo = max(floor_f, prev_f - down_f)
        hi = min(cap_f, prev_f + up_f)
        if hi < lo:
            if audit_codes is not None:
                audit_codes.append(
                    f"{MERGE_DEGENERATE_INTERVAL}:floor={floor_f:.6f}"
                    f":cap={cap_f:.6f}:prev={prev_f:.6f}"
                    f":up={up_f:.6f}:down={down_f:.6f}"
                )
            return float(floor_f)
        return float(max(lo, min(hi, target)))


class PIDIdentityOperator:
    """Pass-through operator with PID-lite residual damping (P1).

    Returns ``dynamic`` clipped into ``[0, 1]`` but applies a PID-lite
    damping to the residual ``dynamic - prev`` before the clip, so the
    effective update is

        residual = dynamic - prev
        damped   = residual * (1 - kd_residual)
        result   = clip(prev + damped + kp_residual * residual, 0, 1)

    The non-finite / out-of-range clipping follows the canonical
    :class:`MergeOperatorProtocol` contract.
    """

    FAMILY: ClassVar[str] = "pid_identity"

    def __init__(
        self,
        *,
        kp_residual: float = 0.0,
        kd_residual: float = 0.0,
    ) -> None:
        for nm, val in (("kp_residual", kp_residual), ("kd_residual", kd_residual)):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            fv = float(val)
            if not math.isfinite(fv):
                raise ValueError(f"{nm} must be finite, got {val!r}")
        self._kp = float(kp_residual)
        self._kd = float(kd_residual)

    def config_hash(self) -> str:
        """Stable digest capturing every constructor argument."""
        return str(
            hash_artifact(
                {
                    "family": self.FAMILY,
                    "kp_residual": float(self._kp),
                    "kd_residual": float(self._kd),
                }
            )
        )

    def to_config(self) -> dict[str, Any]:
        return {
            "family": self.FAMILY,
            "kp_residual": float(self._kp),
            "kd_residual": float(self._kd),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> PIDIdentityOperator:
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        return cls(
            kp_residual=float(config.get("kp_residual", 0.0)),
            kd_residual=float(config.get("kd_residual", 0.0)),
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
        del cap, floor, delta_cap_up, delta_cap_down
        prev_f, _ = _coerce_unit_real_clip(
            prev, name="prev", audit_codes=audit_codes,
            code=MERGE_NONFINITE_PREV_CLIPPED,
        )
        dynamic_f, _ = _coerce_unit_real_clip(
            dynamic, name="dynamic", audit_codes=audit_codes,
            code=MERGE_NONFINITE_DYNAMIC_CLIPPED,
        )
        residual = dynamic_f - prev_f
        damped = residual * (1.0 - float(self._kd)) + float(self._kp) * residual
        result = prev_f + damped
        if not math.isfinite(result):
            return 0.0
        return float(max(0.0, min(1.0, result)))


class ScheduleAwareEMAOperator:
    """Schedule-aware EMA operator (P1).

    The smoothing factor is ``alpha(r) = alpha_min + (alpha_max -
    alpha_min) * n_cap(r)`` so high-``n_cap`` rounds (heavy
    exploration) follow ``dynamic`` more aggressively and low-``n_cap``
    rounds (heavy refinement) weight the prior more. ``n_cap`` defaults
    to ``0.5`` when ``n_cap_hint`` is ``None`` (caller did not supply
    a schedule sample).
    """

    FAMILY: ClassVar[str] = "schedule_ema"

    def __init__(
        self,
        *,
        alpha_min: float = 0.05,
        alpha_max: float = 0.95,
        n_cap_hint: float = 0.5,
    ) -> None:
        for nm, val in (
            ("alpha_min", alpha_min),
            ("alpha_max", alpha_max),
            ("n_cap_hint", n_cap_hint),
        ):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            fv = float(val)
            if not math.isfinite(fv):
                raise ValueError(f"{nm} must be finite, got {val!r}")
        if not (0.0 <= float(alpha_min) <= 1.0):
            raise ValueError(f"alpha_min must be in [0, 1], got {alpha_min!r}")
        if not (0.0 <= float(alpha_max) <= 1.0):
            raise ValueError(f"alpha_max must be in [0, 1], got {alpha_max!r}")
        if not (0.0 <= float(n_cap_hint) <= 1.0):
            raise ValueError(
                f"n_cap_hint must be in [0, 1], got {n_cap_hint!r}"
            )
        self._alpha_min = float(alpha_min)
        self._alpha_max = float(alpha_max)
        self._n_cap_hint = float(n_cap_hint)

    @property
    def alpha_min(self) -> float:
        return float(self._alpha_min)

    @property
    def alpha_max(self) -> float:
        return float(self._alpha_max)

    @property
    def n_cap_hint(self) -> float:
        return float(self._n_cap_hint)

    def config_hash(self) -> str:
        """Stable digest capturing every constructor argument."""
        return str(
            hash_artifact(
                {
                    "family": self.FAMILY,
                    "alpha_min": float(self._alpha_min),
                    "alpha_max": float(self._alpha_max),
                    "n_cap_hint": float(self._n_cap_hint),
                }
            )
        )

    def to_config(self) -> dict[str, Any]:
        return {
            "family": self.FAMILY,
            "alpha_min": float(self._alpha_min),
            "alpha_max": float(self._alpha_max),
            "n_cap_hint": float(self._n_cap_hint),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> ScheduleAwareEMAOperator:
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        return cls(
            alpha_min=float(config.get("alpha_min", 0.05)),
            alpha_max=float(config.get("alpha_max", 0.95)),
            n_cap_hint=float(config.get("n_cap_hint", 0.5)),
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
        del cap, floor, delta_cap_up, delta_cap_down
        prev_f, _ = _coerce_unit_real_clip(
            prev, name="prev", audit_codes=audit_codes,
            code=MERGE_NONFINITE_PREV_CLIPPED,
        )
        dynamic_f, _ = _coerce_unit_real_clip(
            dynamic, name="dynamic", audit_codes=audit_codes,
            code=MERGE_NONFINITE_DYNAMIC_CLIPPED,
        )
        n_cap = float(self._n_cap_hint)
        alpha = self._alpha_min + (self._alpha_max - self._alpha_min) * n_cap
        raw = prev_f + alpha * (dynamic_f - prev_f)
        if not math.isfinite(raw):
            return 0.0
        return float(max(0.0, min(1.0, raw)))


# Register Protocol conformance via structural typing — these classes
# are not decorated with ``@runtime_checkable`` Protocol but each
# implements the canonical :meth:`merge` / :meth:`to_config` /
# :meth:`from_config` surface, so ``isinstance(x,
# MergeOperatorProtocol)`` succeeds via duck typing.
for _cls in (
    KalmanBoundedMergeOperator,
    BayesianMergeOperator,
    PIDIdentityOperator,
    ScheduleAwareEMAOperator,
):
    assert hasattr(_cls, "merge") and hasattr(_cls, "to_config") and hasattr(
        _cls, "from_config"
    )


__all__ = [
    "BayesianMergeOperator",
    "KalmanBoundedMergeOperator",
    "PIDIdentityOperator",
    "ScheduleAwareEMAOperator",
]
