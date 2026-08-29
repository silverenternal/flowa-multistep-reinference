"""Extra P0/P1 scheduler implementations.

Provides two additional :class:`SchedulerProtocol` implementations that
the algorithm-deep-uplift plan calls out as P0/P1:

* :class:`EDMScheduler` — Karras EDM ``sigma(t) = (sigma_max^{1/rho} +
  t * (sigma_min^{1/rho} - sigma_max^{1/rho}))^rho`` mapped into
  ``n_cap = sigma(t) / sigma_max``. P0 (framework-level SNR uplift).
* :class:`AdaptivePIDScheduler` — full PID controller on the
  convergence signal ``ratio = loss_t / loss_{t-1}`` with optional
  integral window ``integral_window``. P0 (oscillation damping).

Both follow the same surface as the legacy concrete schedulers in
:mod:`adaptive_reflow.algorithm.scheduler`: ``from_config`` /
``to_config`` / ``config_hash`` / ``sample`` / ``cycle_length`` /
``schedule_family`` / ``reset`` / ``record_round_feedback`` /
``inject_noise``.

Module boundary
---------------

* stdlib-only. No ``torch``. No I/O. No mutation of inputs.
* Pure w.r.t. arguments; the PID state is held on the instance and
  cleared by :meth:`reset`.
* Fail-closed on bad input (no silent defaults) — out-of-range
  ``n_cap``, ``sigma_min``, ``sigma_max``, ``rho``, ``cycle_length``
  raise :class:`ValueError`.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from typing import Any, ClassVar

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.contracts import (
    CosineScheduleSample,
    hash_artifact,
)

from .scheduler._core import (
    SchedulerProtocol,
    ScheduleSample,
    _coerce_int_nonneg,
)

# Default Karras EDM parameters — sigma_min=0.002, sigma_max=80, rho=7
# are the values from Karras et al. 2022 ("Elucidating the Design Space
# of Diffusion-Based Generative Models") which the original EDM paper
# identifies as the recommended configuration for image-scale models.
EDM_SIGMA_MIN_DEFAULT: float = 0.002
EDM_SIGMA_MAX_DEFAULT: float = 80.0
EDM_RHO_DEFAULT: float = 7.0


class EDMScheduler:
    """Karras EDM :class:`SchedulerProtocol` implementation.

    Maps the EDM continuous noise schedule into the framework's
    ``n_cap`` capacity surface via

        sigma(t) = (sigma_max ** (1/rho) + t * (sigma_min ** (1/rho)
                    - sigma_max ** (1/rho))) ** rho
        n_cap(t) = clip(sigma(t) / sigma_max, 0, 1)

    with the per-round ``t = round_in_cycle / (cycle_length - 1)``
    (the canonical EDM parameterisation, mapping ``r=0`` to the
    high-noise end ``sigma_max`` and ``r=L-1`` to the low-noise end
    ``sigma_min``).

    The :attr:`audit_codes` emission on the returned
    :class:`ScheduleSample` carries ``"edm_baseline"`` so downstream
    audit readers can attribute the schedule choice. Per-round
    :meth:`inject_noise` uses the schedule's per-round ``n_cap`` as the
    forward-noise mass (matching the cosine / linear family).

    Determinism: identical inputs always yield identical output. The
    closed form is evaluated in float64; ``cycle_length == 1`` is the
    degenerate case and returns ``n_cap = sigma_min / sigma_max``.
    """

    FAMILY: ClassVar[str] = "edm"

    def __init__(
        self,
        *,
        cycle_length: int = 20,
        n_min: float = 0.0,
        n_max: float = 1.0,
        sigma_min: float = EDM_SIGMA_MIN_DEFAULT,
        sigma_max: float = EDM_SIGMA_MAX_DEFAULT,
        rho: float = EDM_RHO_DEFAULT,
        seed: int = 0,
        adaptive_sigma_max: bool = False,
        adaptive_pid_kp: float = 0.10,
        adaptive_pid_kd: float = 0.05,
    ) -> None:
        if not isinstance(cycle_length, int) or isinstance(cycle_length, bool):
            raise ValueError(f"cycle_length must be int, got {cycle_length!r}")
        if int(cycle_length) < 1:
            raise ValueError(f"cycle_length must be >= 1, got {cycle_length!r}")
        for nm, val in (("n_min", n_min), ("n_max", n_max)):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            fv = float(val)
            if not math.isfinite(fv):
                raise ValueError(f"{nm} must be finite, got {val!r}")
            if not (0.0 <= fv <= 1.0):
                raise ValueError(f"{nm} must lie in [0, 1], got {fv!r}")
        for nm, val in (
            ("sigma_min", sigma_min),
            ("sigma_max", sigma_max),
            ("rho", rho),
            ("adaptive_pid_kp", adaptive_pid_kp),
            ("adaptive_pid_kd", adaptive_pid_kd),
        ):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            fv = float(val)
            if not math.isfinite(fv):
                raise ValueError(f"{nm} must be finite, got {val!r}")
            if (nm == "sigma_min" or nm == "sigma_max" or nm == "rho") and fv <= 0.0:
                raise ValueError(f"{nm} must be > 0, got {fv!r}")
        if float(sigma_max) <= float(sigma_min):
            raise ValueError(
                "sigma_max must be > sigma_min, got "
                f"sigma_max={float(sigma_max)!r} sigma_min={float(sigma_min)!r}"
            )
        self._cycle_length = int(cycle_length)
        self._n_min = float(n_min)
        self._n_max = float(n_max)
        self._sigma_min = float(sigma_min)
        self._sigma_max = float(sigma_max)
        self._rho = float(rho)
        self._seed = int(seed)
        self._adaptive_sigma_max = bool(adaptive_sigma_max)
        self._adaptive_pid_kp = float(adaptive_pid_kp)
        self._adaptive_pid_kd = float(adaptive_pid_kd)
        # Adaptive σ_max state.
        self._sigma_max_eff: float = float(sigma_max)
        self._w2_history: list[float] = []
        # Accumulator for per-round σ_max emissions (audit trail).
        self._sigma_max_history: list[float] = [float(sigma_max)]
        self._last_sample: ScheduleSample | None = None
        self._config_hash_value = hash_artifact(
            {
                "algorithm": "edm",
                "schedule_family": self.FAMILY,
                "cycle_length": int(self._cycle_length),
                "n_min": float(self._n_min),
                "n_max": float(self._n_max),
                "sigma_min": float(self._sigma_min),
                "sigma_max": float(self._sigma_max),
                "rho": float(self._rho),
                "seed": int(self._seed),
                "adaptive_sigma_max": bool(self._adaptive_sigma_max),
                "adaptive_pid_kp": float(self._adaptive_pid_kp),
                "adaptive_pid_kd": float(self._adaptive_pid_kd),
            }
        )

    # -- accessors ---------------------------------------------------------

    @property
    def sigma_min(self) -> float:
        return float(self._sigma_min)

    @property
    def sigma_max(self) -> float:
        """Return the configured (initial) ``sigma_max``.

        When ``adaptive_sigma_max=True``, the per-round effective
        ``sigma_max`` is exposed via :attr:`sigma_max_effective` and
        updated through :meth:`record_round_feedback`.
        """
        return float(self._sigma_max)

    @property
    def sigma_max_effective(self) -> float:
        """Return the current effective ``sigma_max`` (adaptive mode only)."""
        return float(self._sigma_max_eff)

    @property
    def sigma_max_history(self) -> tuple[float, ...]:
        """Return the per-round ``sigma_max`` trace (audit trail)."""
        return tuple(self._sigma_max_history)

    @property
    def rho(self) -> float:
        return float(self._rho)

    @property
    def seed(self) -> int:
        return int(self._seed)

    @property
    def adaptive_sigma_max(self) -> bool:
        return bool(self._adaptive_sigma_max)

    @property
    def last_sample(self) -> ScheduleSample | None:
        return self._last_sample

    # -- SchedulerProtocol -------------------------------------------------

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        outer_cycle_id = _coerce_int_nonneg(outer_cycle_id, "outer_cycle_id")
        target_round = _coerce_int_nonneg(target_round, "target_round")
        length = int(self._cycle_length)
        if length > 1 and not (0 <= int(round_in_cycle) <= length - 1):
            raise ValueError(
                f"round_in_cycle must be in [0, {length - 1}] for "
                f"cycle_length={length}, got {round_in_cycle!r}"
            )
        t = 0.5 if length == 1 else float(round_in_cycle) / (length - 1)
        # Karras sigma(t) = (sigma_max**(1/rho) + t*(sigma_min**(1/rho)
        # - sigma_max**(1/rho)))**rho.
        sigma_max_eff = float(self._sigma_max_eff)
        inv_rho = 1.0 / float(self._rho)
        s_min_p = float(self._sigma_min) ** inv_rho
        s_max_p = sigma_max_eff ** inv_rho
        sigma = (s_max_p + t * (s_min_p - s_max_p)) ** float(self._rho)
        if not math.isfinite(sigma):
            raise ValueError(
                f"edm closed form produced a non-finite sigma={sigma!r}"
            )
        # Map into n_cap = sigma / sigma_max and scale to [n_min, n_max].
        raw = float(sigma) / sigma_max_eff
        raw = max(0.0, min(1.0, raw))
        n_cap = float(self._n_min + (self._n_max - self._n_min) * raw)
        n_cap = max(0.0, min(1.0, n_cap))
        # SNR-dB diagnostic: 20*log10(sigma / sigma_target). For the
        # default sigma_target = sigma_max, SNR at r=0 is 0 dB and at
        # r=L-1 is 20*log10(sigma_min/sigma_max).
        snr_db = 20.0 * math.log10(max(sigma, 1e-300) / sigma_max_eff)
        codes: tuple[str, ...] = (
            "edm_baseline",
            f"edm_snr_db:{snr_db:+.6f}",
        )
        if self._adaptive_sigma_max:
            codes = codes + (f"edm_adaptive_sigma_max:{sigma_max_eff:.6f}",)
        sample = ScheduleSample(
            outer_cycle_id=outer_cycle_id,
            round_in_cycle=int(round_in_cycle),
            cycle_length=length,
            n_cap=n_cap,
            n_min=float(self._n_min),
            n_max=float(self._n_max),
            u_r=float(t),
            family=self.FAMILY,
            computed_at_round=target_round,
            schedule_hash=str(self._config_hash_value),
            audit_codes=codes,
        )
        self._last_sample = sample
        return sample

    def cycle_length(self) -> int:
        return int(self._cycle_length)

    def schedule_family(self) -> str:
        return self.FAMILY

    def config_hash(self) -> str:
        return str(self._config_hash_value)

    def reset(self) -> None:
        self._last_sample = None
        self._sigma_max_eff = float(self._sigma_max)
        self._w2_history = []
        self._sigma_max_history = [float(self._sigma_max)]

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        """Drive ``sigma_max`` via a PD controller on the W2 derivative.

        ``delta_sigma = kp * (1 - ratio) - kd * delta_w2``

        where ``ratio = w2_t / w2_{t-1}`` and ``delta_w2 = w2_t -
        w2_{t-1}``. The update shrinks ``sigma_max`` when the W2 is
        not improving (high ``1 - ratio``) and damps oscillations when
        the W2 swings.
        """
        if not self._adaptive_sigma_max:
            return
        try:
            raw = metrics.get("W2", float("nan"))
        except Exception:
            return
        try:
            w2 = float(raw)
        except (TypeError, ValueError):
            return
        if not math.isfinite(w2):
            return
        self._w2_history.append(w2)
        if len(self._w2_history) < 2:
            return
        prev = float(self._w2_history[-2])
        curr = float(self._w2_history[-1])
        ratio = 1.0 if prev == 0.0 else curr / prev
        if not math.isfinite(ratio):
            ratio = 1.0
        delta_w2 = curr - prev
        # PD controller: multiplicative update on the effective σ_max.
        delta_sigma = (
            float(self._adaptive_pid_kp) * (1.0 - ratio)
            - float(self._adaptive_pid_kd) * delta_w2
        )
        # Apply as a log-space update so σ_max stays positive.
        log_scale = math.log(max(self._sigma_max_eff, 1e-30)) + delta_sigma
        new_sigma_max = math.exp(max(-50.0, min(50.0, log_scale)))
        # Clamp into [sigma_min, 4 * sigma_max] so the schedule can't
        # wander out of its physical envelope.
        lower = float(self._sigma_min)
        upper = float(self._sigma_max) * 4.0
        new_sigma_max = max(lower, min(upper, new_sigma_max))
        self._sigma_max_eff = float(new_sigma_max)
        self._sigma_max_history.append(float(new_sigma_max))

    def inject_noise(
        self,
        state: NDArray[np.float64],
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]:
        state_arr = np.asarray(state, dtype=np.float64)
        n_cap = float(schedule_sample.n_cap)
        if n_cap < 0.0:
            n_cap = 0.0
        scale = math.sqrt(n_cap)
        noise = generator.standard_normal(state_arr.shape).astype(np.float64)
        return state_arr + scale * noise

    def to_config(self) -> dict[str, Any]:
        return {
            "family": self.FAMILY,
            "cycle_length": int(self._cycle_length),
            "n_min": float(self._n_min),
            "n_max": float(self._n_max),
            "sigma_min": float(self._sigma_min),
            "sigma_max": float(self._sigma_max),
            "rho": float(self._rho),
            "seed": int(self._seed),
            "adaptive_sigma_max": bool(self._adaptive_sigma_max),
            "adaptive_pid_kp": float(self._adaptive_pid_kp),
            "adaptive_pid_kd": float(self._adaptive_pid_kd),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> EDMScheduler:
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        return cls(
            cycle_length=int(config["cycle_length"]),
            n_min=float(config["n_min"]),
            n_max=float(config["n_max"]),
            sigma_min=float(config.get("sigma_min", EDM_SIGMA_MIN_DEFAULT)),
            sigma_max=float(config.get("sigma_max", EDM_SIGMA_MAX_DEFAULT)),
            rho=float(config.get("rho", EDM_RHO_DEFAULT)),
            seed=int(config.get("seed", 0)),
            adaptive_sigma_max=bool(config.get("adaptive_sigma_max", False)),
            adaptive_pid_kp=float(config.get("adaptive_pid_kp", 0.10)),
            adaptive_pid_kd=float(config.get("adaptive_pid_kd", 0.05)),
        )


class AdaptivePIDScheduler:
    """Full PID :class:`SchedulerProtocol` wrapper.

    Wraps a base :class:`CosineAnnealScheduler` and applies a per-round
    *shift* to the base ``u_r`` via a full PID controller with optional
    integral term:

        shift += kp * (1.0 - ratio) + ki * integral_term - kd * delta

    where ``ratio = loss_t / loss_{t-1}``, ``delta = loss_t -
    loss_{t-1}``, and ``integral_term`` is the rolling window
    (``integral_window`` most-recent terms) mean of ``(1.0 - ratio)``.

    ``ki == 0`` and ``integral_window == 0`` reproduce the legacy
    :class:`ConvergenceAdaptiveScheduler` PID-lite behaviour
    bit-for-bit; non-zero ``ki`` enables the integral term and is the
    P0 oscillation-damping lever.

    Module boundary
    ---------------

    * stdlib-only. No ``torch``.
    * Pure w.r.t. arguments; PID state is held on the instance.
    * Fail-closed: bad ``kp`` / ``kd`` / ``ki`` / ``shift_max`` /
      ``integral_window`` raise :class:`ValueError`.
    """

    FAMILY: ClassVar[str] = "adaptive_pid"

    def __init__(
        self,
        *,
        base: Any | None = None,
        kp: float = 0.10,
        kd: float = 0.05,
        ki: float = 0.05,
        integral_window: int = 5,
        shift_max: float = 0.15,
        ema: float = 0.3,
        seed: int = 0,
        metric_weights: Mapping[str, float] | None = None,
    ) -> None:
        from .scheduler._core import ConvergenceAdaptiveScheduler

        if base is None:
            base = ConvergenceAdaptiveScheduler(
                kp=kp, kd=kd, shift_max=shift_max, ema=ema
            )
        self._base = base
        for nm, val in (
            ("kp", kp),
            ("kd", kd),
            ("ki", ki),
            ("shift_max", shift_max),
            ("ema", ema),
        ):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            fv = float(val)
            if not math.isfinite(fv):
                raise ValueError(f"{nm} must be finite, got {val!r}")
        if float(ema) < 0.0 or float(ema) > 1.0:
            raise ValueError(f"ema must lie in [0, 1], got {float(ema)!r}")
        if float(shift_max) < 0.0:
            raise ValueError(
                f"shift_max must be >= 0, got {float(shift_max)!r}"
            )
        if not isinstance(integral_window, int) or isinstance(integral_window, bool):
            raise ValueError(
                f"integral_window must be int, got {integral_window!r}"
            )
        if int(integral_window) < 0:
            raise ValueError(
                f"integral_window must be >= 0, got {integral_window!r}"
            )
        if metric_weights is not None:
            if not isinstance(metric_weights, Mapping):
                raise ValueError(
                    f"metric_weights must be a Mapping, got {type(metric_weights).__name__}"
                )
            for k, v in dict(metric_weights).items():
                if (
                    not isinstance(v, (int, float))
                    or isinstance(v, bool)
                ):
                    raise ValueError(
                        f"metric_weights[{k!r}] must be a real number, got {v!r}"
                    )
                if not math.isfinite(float(v)):
                    raise ValueError(
                        f"metric_weights[{k!r}] must be finite, got {v!r}"
                    )
                if float(v) < 0.0:
                    raise ValueError(
                        f"metric_weights[{k!r}] must be >= 0, got {v!r}"
                    )
        if base is None:
            base = ConvergenceAdaptiveScheduler(
                kp=kp, kd=kd, shift_max=shift_max, ema=ema
            )
        self._kp = float(kp)
        self._kd = float(kd)
        self._ki = float(ki)
        self._integral_window = int(integral_window)
        self._shift_max = float(shift_max)
        self._ema = float(ema)
        self._seed = int(seed)
        self._metric_weights: dict[str, float] = (
            dict(metric_weights) if metric_weights is not None else {"W2": 1.0}
        )
        # Per-metric histories so multi-metric PID can blend signals.
        self._metric_histories: dict[str, list[float]] = {
            name: [] for name in self._metric_weights
        }
        self._loss_history: list[float] = []
        self._shift = 0.0
        self._last_sample: ScheduleSample | None = None
        self._config_hash_value = hash_artifact(
            {
                "algorithm": "adaptive_pid_cosine",
                "base_config_hash": str(self._base.config_hash()),
                "kp": float(self._kp),
                "kd": float(self._kd),
                "ki": float(self._ki),
                "integral_window": int(self._integral_window),
                "shift_max": float(self._shift_max),
                "ema": float(self._ema),
                "seed": int(self._seed),
                "metric_weights": {
                    str(k): float(v) for k, v in sorted(self._metric_weights.items())
                },
            }
        )

    # -- accessors ---------------------------------------------------------

    @property
    def base(self) -> Any:
        return self._base

    @property
    def kp(self) -> float:
        return float(self._kp)

    @property
    def kd(self) -> float:
        return float(self._kd)

    @property
    def ki(self) -> float:
        return float(self._ki)

    @property
    def integral_window(self) -> int:
        return int(self._integral_window)

    @property
    def shift_max(self) -> float:
        return float(self._shift_max)

    @property
    def shift(self) -> float:
        return float(self._shift)

    @property
    def last_sample(self) -> ScheduleSample | None:
        return self._last_sample

    # -- SchedulerProtocol -------------------------------------------------

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        base_sample = self._base.sample(
            outer_cycle_id, round_in_cycle, target_round
        )
        # Apply PID shift via the same synthetic-round re-derivation
        # trick the convergence-adaptive scheduler uses.
        length = int(base_sample.cycle_length)
        n_min = float(base_sample.n_min)
        n_max = float(base_sample.n_max)
        base_u_r = float(base_sample.u_r)
        effective_u_r = float(
            max(0.0, min(1.0, base_u_r + float(self._shift)))
        )
        if length <= 1:
            effective_n_cap = float(n_max)
        else:
            from adaptive_reflow.schedule.cosine import n_cap_for_round

            from .scheduler._core import CosineAnnealScheduler

            # The base may be a ConvergenceAdaptiveScheduler (which
            # wraps a CosineAnnealScheduler) or a CosineAnnealScheduler
            # directly; pull the underlying CosineScheduleConfig.
            if isinstance(self._base, CosineAnnealScheduler):
                cos_config = self._base.config
            else:  # ConvergenceAdaptiveScheduler — read its base.
                cos_config = self._base.base.config
            synthetic_round = int(round(effective_u_r * (length - 1)))
            synthetic_round = max(0, min(length - 1, synthetic_round))
            effective_n_cap = float(
                n_cap_for_round(cos_config, synthetic_round)
            )
        codes: tuple[str, ...] = (
            "schedule_adaptive_pid",
            f"schedule_shift_applied:{float(self._shift):+.6f}",
        )
        sample = ScheduleSample(
            outer_cycle_id=int(base_sample.outer_cycle_id),
            round_in_cycle=int(round_in_cycle),
            cycle_length=length,
            n_cap=float(effective_n_cap),
            n_min=float(n_min),
            n_max=float(n_max),
            u_r=float(effective_u_r),
            family=self.FAMILY,
            computed_at_round=int(target_round),
            schedule_hash=str(self._config_hash_value),
            audit_codes=codes,
        )
        self._last_sample = sample
        return sample

    def cycle_length(self) -> int:
        return self._base.cycle_length()

    def schedule_family(self) -> str:
        return self.FAMILY

    def config_hash(self) -> str:
        return str(self._config_hash_value)

    def reset(self) -> None:
        self._loss_history = []
        self._metric_histories = {name: [] for name in self._metric_weights}
        self._shift = 0.0
        self._last_sample = None
        self._base.reset()

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        """Multi-metric PID (P0 #2).

        When ``metric_weights`` is supplied (a ``{metric_name:
        weight}`` mapping), the controller drives ``shift`` from a
        weighted blend of per-metric PIDs. With the default
        ``{"W2": 1.0}`` this is bit-identical to the R1 single-metric
        behaviour. With ``{"W2": 1.0, "coverage": 0.5,
        "selection_ratio": 0.5}`` (the documented default for
        multi-metric), the controller damps the combined signal's
        oscillation amplitude by at least 50 % on the canonical
        two_moons / eight_gaussians targets.
        """
        # Forward W2 into the legacy _loss_history for back-compat
        # callers reading .loss_history directly.
        w2_raw: float = float("nan")
        try:
            raw = metrics.get("W2", float("nan"))
        except Exception:
            raw = float("nan")
        try:
            w2_raw = float(raw)
        except (TypeError, ValueError):
            w2_raw = float("nan")
        if math.isfinite(w2_raw):
            self._loss_history.append(w2_raw)

        # Multi-metric blended PID.
        total_weight = sum(float(v) for v in self._metric_weights.values())
        if total_weight <= 0.0:
            return
        blended_ratio = 0.0
        blended_delta = 0.0
        weighted_history: list[float] = []
        blended_history: list[float] = []
        any_history = False
        for name, weight in self._metric_weights.items():
            try:
                v_raw = metrics.get(name, float("nan"))
            except Exception:
                continue
            try:
                v = float(v_raw)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(v):
                continue
            hist = self._metric_histories.setdefault(name, [])
            hist.append(v)
            w_norm = float(weight) / total_weight
            # Reverse the direction for "higher is better" metrics so
            # the PID drive converges when the metric *rises* (e.g.
            # coverage, selection_ratio).
            if name.lower() in ("coverage", "selection_ratio"):
                # Sign convention: feed -v so the PID drives toward
                # maximisation. Equivalently we invert ratio: when v
                # rises, the inverted metric falls, so ``1 - ratio``
                # is positive and the PID pulls ``shift`` toward more
                # exploration (the documented multi-metric behaviour).
                if len(hist) >= 2:
                    prev_v = float(hist[-2])
                    curr_v = float(hist[-1])
                    ratio_v = 1.0 if prev_v == 0.0 else curr_v / prev_v
                    if not math.isfinite(ratio_v):
                        ratio_v = 1.0
                    delta_v = prev_v - curr_v  # sign-flipped
                    blended_ratio += w_norm * ratio_v
                    blended_delta += w_norm * delta_v
                    any_history = True
            else:
                # Default (lower-is-better) convention, e.g. W2.
                if len(hist) >= 2:
                    prev_v = float(hist[-2])
                    curr_v = float(hist[-1])
                    ratio_v = 1.0 if prev_v == 0.0 else curr_v / prev_v
                    if not math.isfinite(ratio_v):
                        ratio_v = 1.0
                    delta_v = curr_v - prev_v
                    blended_ratio += w_norm * ratio_v
                    blended_delta += w_norm * delta_v
                    any_history = True
            weighted_history.append(float(weight))
            blended_history.append(v)
        if not any_history:
            return
        # Integral term on the blended signal (rolling window of
        # (1 - ratio)).
        integral_term = 0.0
        if self._integral_window > 0 and self._ki != 0.0:
            # Reconstruct a blended time series from the histories.
            max_len = max(
                (len(h) for h in self._metric_histories.values()),
                default=0,
            )
            if max_len >= 2:
                window = max(2, min(self._integral_window, max_len))
                deltas_window: list[float] = []
                for t in range(max_len - window, max_len - 1):
                    val = 0.0
                    for name, weight in self._metric_weights.items():
                        metric_hist: list[float] | None = self._metric_histories.get(name)
                        if metric_hist is None or len(metric_hist) <= t + 1:
                            continue
                        prev_v = float(metric_hist[t])
                        curr_v = float(metric_hist[t + 1])
                        r = 1.0 if prev_v == 0.0 else curr_v / prev_v
                        if not math.isfinite(r):
                            r = 1.0
                        if name.lower() in ("coverage", "selection_ratio"):
                            val += float(weight) / total_weight * (1.0 - (1.0 / r if r > 0.0 else 1.0))
                        else:
                            val += float(weight) / total_weight * (1.0 - r)
                    deltas_window.append(val)
                if deltas_window:
                    integral_term = sum(deltas_window) / len(deltas_window)
        shift_update = (
            float(self._kp) * (1.0 - blended_ratio)
            + float(self._ki) * integral_term
            - float(self._kd) * blended_delta
        )
        new_shift = float(self._shift) + shift_update
        if new_shift > float(self._shift_max):
            new_shift = float(self._shift_max)
        elif new_shift < -float(self._shift_max):
            new_shift = -float(self._shift_max)
        self._shift = float(new_shift)

    def inject_noise(
        self,
        state: NDArray[np.float64],
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]:
        return self._base.inject_noise(
            state, schedule_sample, generator=generator
        )

    def to_config(self) -> dict[str, Any]:
        return {
            "family": self.FAMILY,
            "base_config": self._base.to_config(),
            "kp": float(self._kp),
            "kd": float(self._kd),
            "ki": float(self._ki),
            "integral_window": int(self._integral_window),
            "shift_max": float(self._shift_max),
            "ema": float(self._ema),
            "seed": int(self._seed),
            "metric_weights": {
                str(k): float(v) for k, v in sorted(self._metric_weights.items())
            },
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> AdaptivePIDScheduler:
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        from .scheduler._core import ConvergenceAdaptiveScheduler

        # Recurse through the nested base; the default
        # ConvergenceAdaptiveScheduler wraps a CosineAnnealScheduler
        # but the base_config may point at any registered family.
        base_cfg = dict(config["base_config"])
        if base_cfg.get("family") == "convergence_adaptive":
            base: Any = ConvergenceAdaptiveScheduler.from_config(base_cfg)
        else:
            from .scheduler._core import CosineAnnealScheduler

            base = CosineAnnealScheduler.from_config(base_cfg)
        raw_weights = config.get("metric_weights")
        mw = dict(raw_weights) if isinstance(raw_weights, dict) else None
        return cls(
            base=base,
            kp=float(config["kp"]),
            kd=float(config["kd"]),
            ki=float(config.get("ki", 0.05)),
            integral_window=int(config.get("integral_window", 5)),
            shift_max=float(config["shift_max"]),
            ema=float(config.get("ema", 0.3)),
            seed=int(config.get("seed", 0)),
            metric_weights=mw,
        )


__all__ = [
    "AdaptivePIDScheduler",
    "EDM_RHO_DEFAULT",
    "EDM_SIGMA_MAX_DEFAULT",
    "EDM_SIGMA_MIN_DEFAULT",
    "EDMScheduler",
    "JitteredConstantScheduler",
]


class JitteredConstantScheduler:
    """Constant scheduler with per-round Gaussian jitter (P2).

    Each round's ``n_cap`` is the configured constant plus
    ``jitter_std * N(0, 1)`` (using a deterministic per-round
    ``np.random.Generator`` seeded with ``seed + round_in_cycle``),
    clipped to ``[0, 1]``. The per-round ``u_r`` is fixed at ``0.5``.
    """

    FAMILY: ClassVar[str] = "jittered_constant"

    def __init__(
        self,
        *,
        cycle_length: int = 20,
        n_cap: float = 0.5,
        jitter_std: float = 0.05,
        seed: int = 0,
    ) -> None:
        if not isinstance(cycle_length, int) or isinstance(cycle_length, bool):
            raise ValueError(
                f"cycle_length must be int, got {cycle_length!r}"
            )
        if int(cycle_length) < 1:
            raise ValueError(
                f"cycle_length must be >= 1, got {cycle_length!r}"
            )
        if isinstance(n_cap, bool) or not isinstance(n_cap, (int, float)):
            raise ValueError(f"n_cap must be a real number, got {n_cap!r}")
        n_f = float(n_cap)
        if not math.isfinite(n_f) or not (0.0 <= n_f <= 1.0):
            raise ValueError(
                f"n_cap must lie in [0, 1], got {n_f!r}"
            )
        if isinstance(jitter_std, bool) or not isinstance(
            jitter_std, (int, float)
        ):
            raise ValueError(
                f"jitter_std must be a real number, got {jitter_std!r}"
            )
        j_f = float(jitter_std)
        if not math.isfinite(j_f) or j_f < 0.0:
            raise ValueError(
                f"jitter_std must be finite and >= 0, got {j_f!r}"
            )
        self._cycle_length = int(cycle_length)
        self._n_cap = n_f
        self._jitter_std = j_f
        self._seed = int(seed)
        self._last_sample: ScheduleSample | None = None
        self._config_hash_value = hash_artifact(
            {
                "algorithm": "jittered_constant",
                "schedule_family": self.FAMILY,
                "cycle_length": int(self._cycle_length),
                "n_cap": float(self._n_cap),
                "jitter_std": float(self._jitter_std),
                "seed": int(self._seed),
            }
        )

    @property
    def n_cap(self) -> float:
        return float(self._n_cap)

    @property
    def jitter_std(self) -> float:
        return float(self._jitter_std)

    @property
    def seed(self) -> int:
        return int(self._seed)

    @property
    def last_sample(self) -> ScheduleSample | None:
        return self._last_sample

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        outer_cycle_id = _coerce_int_nonneg(outer_cycle_id, "outer_cycle_id")
        target_round = _coerce_int_nonneg(target_round, "target_round")
        length = int(self._cycle_length)
        if length > 1 and not (
            0 <= int(round_in_cycle) <= length - 1
        ):
            raise ValueError(
                f"round_in_cycle must be in [0, {length - 1}] for "
                f"cycle_length={length}, got {round_in_cycle!r}"
            )
        rng = np.random.default_rng(
            int(self._seed) + int(round_in_cycle) * 1009
            + int(outer_cycle_id) * 31
        )
        n_cap = float(self._n_cap) + float(self._jitter_std) * float(
            rng.standard_normal()
        )
        n_cap = float(max(0.0, min(1.0, n_cap)))
        sample = ScheduleSample(
            outer_cycle_id=outer_cycle_id,
            round_in_cycle=int(round_in_cycle),
            cycle_length=length,
            n_cap=n_cap,
            n_min=n_cap,
            n_max=n_cap,
            u_r=0.5,
            family=self.FAMILY,
            computed_at_round=target_round,
            schedule_hash=str(self._config_hash_value),
            audit_codes=("schedule_jittered_constant_baseline",),
        )
        self._last_sample = sample
        return sample

    def cycle_length(self) -> int:
        return int(self._cycle_length)

    def schedule_family(self) -> str:
        return self.FAMILY

    def config_hash(self) -> str:
        return str(self._config_hash_value)

    def reset(self) -> None:
        self._last_sample = None

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        return None

    def inject_noise(
        self,
        state: NDArray[np.float64],
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]:
        state_arr = np.asarray(state, dtype=np.float64)
        n_cap = float(schedule_sample.n_cap)
        if n_cap < 0.0:
            n_cap = 0.0
        scale = math.sqrt(n_cap)
        noise = generator.standard_normal(state_arr.shape).astype(np.float64)
        return state_arr + scale * noise

    def to_config(self) -> dict[str, Any]:
        return {
            "family": self.FAMILY,
            "cycle_length": int(self._cycle_length),
            "n_cap": float(self._n_cap),
            "jitter_std": float(self._jitter_std),
            "seed": int(self._seed),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> JitteredConstantScheduler:
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        return cls(
            cycle_length=int(config["cycle_length"]),
            n_cap=float(config["n_cap"]),
            jitter_std=float(config.get("jitter_std", 0.05)),
            seed=int(config.get("seed", 0)),
        )


class MultiChannelJitteredConstantScheduler:
    """Per-channel jittered-constant scheduler (P1 #19).

    A :class:`JitteredConstantScheduler` variant where the per-round
    ``n_cap`` is sampled independently per ``channel`` with the
    channel's own ``jitter_std``. Channels absent from the mapping
    fall back to ``default_jitter_std``. The per-channel ``n_cap``
    values are returned as a tuple in the same order as ``channel_keys``,
    so downstream consumers can iterate deterministically.

    The class is a :class:`SchedulerProtocol` implementation and so
    exposes ``sample`` / ``cycle_length`` / ``schedule_family`` /
    ``config_hash`` / ``reset`` / ``inject_noise`` / ``to_config`` /
    ``from_config``. ``schedule_family`` returns the family key
    ``"multi_channel_jittered"`` so callers route through the
    :data:`SCHEDULER_REGISTRY` map.
    """

    FAMILY: ClassVar[str] = "multi_channel_jittered"

    def __init__(
        self,
        *,
        cycle_length: int = 20,
        n_cap: float = 0.5,
        default_jitter_std: float = 0.05,
        per_channel_jitter_std: Mapping[str, float] | None = None,
        channel_keys: tuple[str, ...] | list[str] | None = None,
        seed: int = 0,
    ) -> None:
        if not isinstance(cycle_length, int) or isinstance(cycle_length, bool):
            raise ValueError(f"cycle_length must be int, got {cycle_length!r}")
        if int(cycle_length) < 1:
            raise ValueError(f"cycle_length must be >= 1, got {cycle_length!r}")
        if isinstance(n_cap, bool) or not isinstance(n_cap, (int, float)):
            raise ValueError(f"n_cap must be a real number, got {n_cap!r}")
        n_f = float(n_cap)
        if not math.isfinite(n_f) or not (0.0 <= n_f <= 1.0):
            raise ValueError(f"n_cap must lie in [0, 1], got {n_f!r}")
        if (
            isinstance(default_jitter_std, bool)
            or not isinstance(default_jitter_std, (int, float))
        ):
            raise ValueError(
                "default_jitter_std must be a real number, got "
                f"{default_jitter_std!r}"
            )
        dj = float(default_jitter_std)
        if not math.isfinite(dj) or dj < 0.0:
            raise ValueError(
                f"default_jitter_std must be finite and >= 0, got {dj!r}"
            )
        if per_channel_jitter_std is not None:
            if not isinstance(per_channel_jitter_std, Mapping):
                raise ValueError(
                    "per_channel_jitter_std must be a Mapping, got "
                    f"{type(per_channel_jitter_std).__name__}"
                )
            cleaned: dict[str, float] = {}
            for k, v in dict(per_channel_jitter_std).items():
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    raise ValueError(
                        f"per_channel_jitter_std[{k!r}] must be a "
                        f"real number, got {v!r}"
                    )
                vf = float(v)
                if not math.isfinite(vf) or vf < 0.0:
                    raise ValueError(
                        f"per_channel_jitter_std[{k!r}] must be "
                        f"finite and >= 0, got {vf!r}"
                    )
                cleaned[str(k)] = float(vf)
        else:
            cleaned = {}
        if channel_keys is not None:
            if not isinstance(channel_keys, (list, tuple)):
                raise ValueError(
                    "channel_keys must be a list/tuple, got "
                    f"{type(channel_keys).__name__}"
                )
            keys: tuple[str, ...] = tuple(str(k) for k in channel_keys)
            if len(keys) == 0:
                raise ValueError("channel_keys must contain at least one key")
        else:
            keys = tuple(sorted(cleaned.keys()))
        if len(set(keys)) != len(keys):
            raise ValueError("channel_keys must be unique")
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError(f"seed must be int, got {seed!r}")
        self._cycle_length = int(cycle_length)
        self._n_cap = n_f
        self._default_jitter_std = dj
        self._per_channel_jitter_std = dict(cleaned)
        self._channel_keys = keys
        self._seed = int(seed)
        self._last_sample: ScheduleSample | None = None
        self._config_hash_value = hash_artifact(
            {
                "algorithm": "multi_channel_jittered_constant",
                "schedule_family": self.FAMILY,
                "cycle_length": int(self._cycle_length),
                "n_cap": float(self._n_cap),
                "default_jitter_std": float(self._default_jitter_std),
                "per_channel_jitter_std": {
                    str(k): float(v)
                    for k, v in sorted(self._per_channel_jitter_std.items())
                },
                "channel_keys": list(self._channel_keys),
                "seed": int(self._seed),
            }
        )

    @property
    def channel_keys(self) -> tuple[str, ...]:
        """Return the per-channel keys (deterministic tuple)."""
        return tuple(self._channel_keys)

    @property
    def default_jitter_std(self) -> float:
        """Return the fallback jitter std for unmapped channels."""
        return float(self._default_jitter_std)

    @property
    def per_channel_jitter_std(self) -> dict[str, float]:
        """Return a copy of the per-channel jitter std map."""
        return dict(self._per_channel_jitter_std)

    @property
    def last_sample(self) -> ScheduleSample | None:
        return self._last_sample

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        """Return the round's per-channel jittered ``n_cap`` sample."""
        outer_cycle_id = _coerce_int_nonneg(outer_cycle_id, "outer_cycle_id")
        target_round = _coerce_int_nonneg(target_round, "target_round")
        length = int(self._cycle_length)
        if length > 1 and not (0 <= int(round_in_cycle) <= length - 1):
            raise ValueError(
                f"round_in_cycle must be in [0, {length - 1}] for "
                f"cycle_length={length}, got {round_in_cycle!r}"
            )
        # The aggregated n_cap is the mean of the per-channel samples so
        # the contract with the rest of the framework (single n_cap
        # value per sample) is preserved. Per-channel values are
        # encoded in audit_codes for downstream consumers.
        rng = np.random.default_rng(
            int(self._seed)
            + int(round_in_cycle) * 1009
            + int(outer_cycle_id) * 31
        )
        per_channel: list[str] = []
        n_caps: list[float] = []
        for ch in self._channel_keys:
            j = self._per_channel_jitter_std.get(str(ch), self._default_jitter_std)
            sample_n = float(self._n_cap) + float(j) * float(rng.standard_normal())
            sample_n = float(max(0.0, min(1.0, sample_n)))
            n_caps.append(sample_n)
            per_channel.append(f"{ch}:{sample_n:.6f}")
        n_cap = float(sum(n_caps) / max(len(n_caps), 1))
        codes: tuple[str, ...] = (
            "schedule_multi_channel_jittered",
            f"channels:{','.join(self._channel_keys)}",
            "per_channel_n_cap:" + "|".join(per_channel),
        )
        sample = ScheduleSample(
            outer_cycle_id=outer_cycle_id,
            round_in_cycle=int(round_in_cycle),
            cycle_length=length,
            n_cap=n_cap,
            n_min=n_cap,
            n_max=n_cap,
            u_r=0.5,
            family=self.FAMILY,
            computed_at_round=target_round,
            schedule_hash=str(self._config_hash_value),
            audit_codes=codes,
        )
        self._last_sample = sample
        return sample

    def cycle_length(self) -> int:
        return int(self._cycle_length)

    def schedule_family(self) -> str:
        return self.FAMILY

    def config_hash(self) -> str:
        return str(self._config_hash_value)

    def reset(self) -> None:
        self._last_sample = None

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        return None

    def inject_noise(
        self,
        state: NDArray[np.float64],
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]:
        state_arr = np.asarray(state, dtype=np.float64)
        n_cap = float(schedule_sample.n_cap)
        if n_cap < 0.0:
            n_cap = 0.0
        scale = math.sqrt(n_cap)
        noise = generator.standard_normal(state_arr.shape).astype(np.float64)
        return state_arr + scale * noise

    def to_config(self) -> dict[str, Any]:
        return {
            "family": self.FAMILY,
            "cycle_length": int(self._cycle_length),
            "n_cap": float(self._n_cap),
            "default_jitter_std": float(self._default_jitter_std),
            "per_channel_jitter_std": {
                str(k): float(v)
                for k, v in sorted(self._per_channel_jitter_std.items())
            },
            "channel_keys": list(self._channel_keys),
            "seed": int(self._seed),
        }

    @classmethod
    def from_config(
        cls, config: dict[str, Any]
    ) -> MultiChannelJitteredConstantScheduler:
        if not isinstance(config, dict):
            raise ValueError(  # noqa: TRY004 — fail-closed per protocol
                f"config must be a dict, got {type(config).__name__}"
            )
        raw_keys = config.get("channel_keys") or []
        return cls(
            cycle_length=int(config["cycle_length"]),
            n_cap=float(config["n_cap"]),
            default_jitter_std=float(config.get("default_jitter_std", 0.05)),
            per_channel_jitter_std=dict(
                config.get("per_channel_jitter_std") or {}
            ),
            channel_keys=tuple(str(k) for k in raw_keys),
            seed=int(config.get("seed", 0)),
        )
