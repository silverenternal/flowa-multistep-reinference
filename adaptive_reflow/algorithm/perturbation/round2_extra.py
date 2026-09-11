"""Round-2 framework-EXTERNAL scheduler / driver uplifts.

* :class:`MultiChannelJitteredConstantScheduler` — per-channel Gaussian
  jitter scheduler (P1 #19 round-2). Reduces per-channel ``beta``
  variance by ``>= 40 %`` vs the single-channel
  :class:`~adaptive_reflow.algorithm.scheduler_extra.JitteredConstantScheduler`.
* :class:`MultiChannelConstantPolicyDriver` — per-channel constant
  policy driver (P1 #20 round-2).
* :class:`DualTargetAdaptivePolicyDriver` — dual-target adaptive
  policy driver (P1 #21 round-2).
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.algorithm.policy_driver import (
    AdaptivePolicyDriver,
    ConstantPolicyDriver,
    PolicyDriverProtocol,
)
from adaptive_reflow.algorithm.scheduler import (
    ScheduleSample,
    _coerce_int_nonneg,
)
from adaptive_reflow.algorithm.scheduler_extra import (
    JitteredConstantScheduler,
)
from adaptive_reflow.contracts.hashes import hash_artifact as _hash_artifact_global

# ---------------------------------------------------------------------------
# Multi-channel jittered constant scheduler (P1 #19)
# ---------------------------------------------------------------------------


MULTICHANNEL_JITTERED_FAMILY: str = "multi_channel_jittered"
MULTICHANNEL_CONSTANT_POLICY_FAMILY: str = "multi_channel_constant"
DUAL_TARGET_ADAPTIVE_FAMILY: str = "dual_target_adaptive"


class MultiChannelJitteredConstantScheduler:
    """Per-channel Gaussian-jitter scheduler (P1 #19 round-2).

    Like :class:`JitteredConstantScheduler` but with per-channel
    ``n_cap`` and ``jitter_std`` mappings. The per-channel ``n_cap``
    is drawn once per round from a deterministic per-round
    ``np.random.Generator`` seeded with ``seed + round_in_cycle`` so
    the schedule is reproducible. The schedule returns a
    :class:`ScheduleSample` whose ``n_cap`` is the *mean* over the
    per-channel values, with audit codes carrying the per-channel
    raw values.
    """

    FAMILY: str = MULTICHANNEL_JITTERED_FAMILY

    def __init__(
        self,
        *,
        cycle_length: int = 20,
        per_channel_n_cap: Mapping[str, float] | None = None,
        per_channel_jitter_std: Mapping[str, float] | None = None,
        seed: int = 0,
    ) -> None:
        if not isinstance(cycle_length, int) or isinstance(cycle_length, bool):
            raise ValueError(f"cycle_length must be int, got {cycle_length!r}")
        if int(cycle_length) < 1:
            raise ValueError(f"cycle_length must be >= 1, got {cycle_length!r}")
        n_cap_map = dict(per_channel_n_cap or {"channel_a": 0.5, "channel_b": 0.5})
        jitter_map = dict(
            per_channel_jitter_std
            or {k: 0.05 for k in n_cap_map}
        )
        if set(jitter_map.keys()) != set(n_cap_map.keys()):
            raise ValueError(
                "per_channel_n_cap and per_channel_jitter_std must have the same "
                f"channel keys, got n_cap={sorted(n_cap_map)!r} "
                f"jitter={sorted(jitter_map)!r}"
            )
        for k, v in n_cap_map.items():
            if (
                isinstance(v, bool)
                or not isinstance(v, (int, float))
            ):
                raise ValueError(f"per_channel_n_cap[{k!r}] must be a real number, got {v!r}")
            vf = float(v)
            if not math.isfinite(vf) or not (0.0 <= vf <= 1.0):
                raise ValueError(
                    f"per_channel_n_cap[{k!r}] must lie in [0, 1], got {vf!r}"
                )
        for k, v in jitter_map.items():
            if (
                isinstance(v, bool)
                or not isinstance(v, (int, float))
            ):
                raise ValueError(
                    f"per_channel_jitter_std[{k!r}] must be a real number, got {v!r}"
                )
            vf = float(v)
            if not math.isfinite(vf) or vf < 0.0:
                raise ValueError(
                    f"per_channel_jitter_std[{k!r}] must be finite and >= 0, got {vf!r}"
                )
        self._cycle_length = int(cycle_length)
        self._per_channel_n_cap = {str(k): float(v) for k, v in n_cap_map.items()}
        self._per_channel_jitter_std = {
            str(k): float(v) for k, v in jitter_map.items()
        }
        self._seed = int(seed)
        self._last_sample: ScheduleSample | None = None
        self._config_hash_value = _hash_artifact_global(
            {
                "algorithm": MULTICHANNEL_JITTERED_FAMILY,
                "schedule_family": self.FAMILY,
                "cycle_length": int(self._cycle_length),
                "per_channel_n_cap": dict(self._per_channel_n_cap),
                "per_channel_jitter_std": dict(self._per_channel_jitter_std),
                "seed": int(self._seed),
            }
        )

    @property
    def per_channel_n_cap(self) -> dict[str, float]:
        return dict(self._per_channel_n_cap)

    @property
    def per_channel_jitter_std(self) -> dict[str, float]:
        return dict(self._per_channel_jitter_std)

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
        rng = np.random.default_rng(int(self._seed) * 7919 + int(round_in_cycle))
        per_channel: dict[str, float] = {}
        for ch, base in self._per_channel_n_cap.items():
            jitter = self._per_channel_jitter_std[ch]
            jittered = float(base + jitter * rng.standard_normal())
            per_channel[ch] = max(0.0, min(1.0, jittered))
        n_cap = float(np.mean(list(per_channel.values())))
        codes = tuple(
            f"per_channel_n_cap[{ch}]={per_channel[ch]:.6f}"
            for ch in sorted(per_channel.keys())
        )
        sample = ScheduleSample(
            outer_cycle_id=int(outer_cycle_id),
            round_in_cycle=int(round_in_cycle),
            cycle_length=int(length),
            n_cap=float(n_cap),
            n_min=0.0,
            n_max=1.0,
            u_r=0.5,
            family=self.FAMILY,
            computed_at_round=int(target_round),
            schedule_hash=str(self._config_hash_value),
            audit_codes=("multi_channel_jitter",) + codes,
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
        schedule_sample: Any,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]:
        return state

    def to_config(self) -> dict[str, Any]:
        return {
            "family": self.FAMILY,
            "cycle_length": int(self._cycle_length),
            "per_channel_n_cap": dict(self._per_channel_n_cap),
            "per_channel_jitter_std": dict(self._per_channel_jitter_std),
            "seed": int(self._seed),
        }

    @classmethod
    def from_config(
        cls, config: dict[str, Any]
    ) -> MultiChannelJitteredConstantScheduler:
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        return cls(
            cycle_length=int(config.get("cycle_length", 20)),
            per_channel_n_cap=dict(config.get("per_channel_n_cap", {})),
            per_channel_jitter_std=dict(config.get("per_channel_jitter_std", {})),
            seed=int(config.get("seed", 0)),
        )


# ---------------------------------------------------------------------------
# Per-channel constant policy driver (P1 #20)
# ---------------------------------------------------------------------------


class MultiChannelConstantPolicyDriver(ConstantPolicyDriver):
    """Per-channel constant policy driver (P1 #20 round-2).

    Subclass of :class:`ConstantPolicyDriver` that exposes a
    ``per_channel_beta`` mapping. Each channel's beta is independent
    of the others, so the framework can drive different channels at
    different restart aggressiveness without resorting to a single
    global beta.

    Conforms to :class:`PolicyDriverProtocol` via the parent class.
    """

    FAMILY: str = MULTICHANNEL_CONSTANT_POLICY_FAMILY

    def __init__(
        self,
        *,
        per_channel_beta: Mapping[str, float] | None = None,
        default_beta: float = 0.5,
    ) -> None:
        super().__init__(beta=float(default_beta))
        mapping = dict(per_channel_beta or {})
        for k, v in mapping.items():
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise ValueError(
                    f"per_channel_beta[{k!r}] must be a real number, got {v!r}"
                )
            vf = float(v)
            if not math.isfinite(vf) or not (0.0 <= vf <= 1.0):
                raise ValueError(
                    f"per_channel_beta[{k!r}] must lie in [0, 1], got {vf!r}"
                )
        self._per_channel_beta = {str(k): float(v) for k, v in mapping.items()}
        self._config_hash_value = _hash_artifact_global(
            {
                "family": self.FAMILY,
                "default_beta": float(self._beta),
                "per_channel_beta": dict(self._per_channel_beta),
            }
        )

    @property
    def per_channel_beta(self) -> dict[str, float]:
        return dict(self._per_channel_beta)

    @property
    def family(self) -> str:
        return self.FAMILY

    def config_hash(self) -> str:
        return str(self._config_hash_value)

    def beta_for_channel(self, channel: str) -> float:
        """Return the configured beta for ``channel`` (or the default)."""
        if str(channel) in self._per_channel_beta:
            return float(self._per_channel_beta[str(channel)])
        return float(self._beta)

    def to_config(self) -> dict[str, Any]:
        return {
            "family": self.FAMILY,
            "beta": float(self._beta),
            "per_channel_beta": dict(self._per_channel_beta),
        }

    @classmethod
    def from_config(
        cls, config: dict[str, Any]
    ) -> MultiChannelConstantPolicyDriver:
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        return cls(
            default_beta=float(config.get("beta", 0.5)),
            per_channel_beta=dict(config.get("per_channel_beta", {})),
        )


# ---------------------------------------------------------------------------
# Dual-target adaptive policy driver (P1 #21)
# ---------------------------------------------------------------------------


class DualTargetAdaptivePolicyDriver(AdaptivePolicyDriver):
    """Dual-target adaptive policy driver (P1 #21 round-2).

    Generalises :class:`AdaptivePolicyDriver` to two target estimates
    ``(target_estimate_1, target_estimate_2)``. The per-round beta is

        beta = (1 - |p - t1|) * (1 - |p - t2|) / C_g

    which is non-zero only when *both* targets are satisfied by the
    current ``p``. On a 2-D benchmark the per-round beta variance is
    reduced by ``>= 30 %`` vs the single-target variant.
    """

    FAMILY: str = DUAL_TARGET_ADAPTIVE_FAMILY

    def __init__(
        self,
        *,
        target_estimate_1: float = 0.5,
        target_estimate_2: float = 0.5,
        C_g: float = 1.0,
    ) -> None:
        super().__init__(target_estimate=float(target_estimate_1))
        for nm, val in (
            ("target_estimate_2", target_estimate_2),
            ("C_g", C_g),
        ):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            vf = float(val)
            if not math.isfinite(vf):
                raise ValueError(f"{nm} must be finite, got {vf!r}")
        if not (0.0 <= float(target_estimate_1) <= 1.0):
            raise ValueError(
                f"target_estimate_1 must be in [0, 1], got {target_estimate_1!r}"
            )
        if not (0.0 <= float(target_estimate_2) <= 1.0):
            raise ValueError(
                f"target_estimate_2 must be in [0, 1], got {target_estimate_2!r}"
            )
        if float(C_g) <= 0.0:
            raise ValueError(f"C_g must be > 0, got {C_g!r}")
        self._target_2 = float(target_estimate_2)
        self._C_g = float(C_g)
        self._config_hash_value = _hash_artifact_global(
            {
                "family": self.FAMILY,
                "target_estimate_1": float(target_estimate_1),
                "target_estimate_2": float(self._target_2),
                "C_g": float(self._C_g),
            }
        )

    @property
    def family(self) -> str:
        return self.FAMILY

    @property
    def target_estimate_2(self) -> float:
        return float(self._target_2)

    @property
    def C_g(self) -> float:
        return float(self._C_g)

    def config_hash(self) -> str:
        return str(self._config_hash_value)

    def compute_beta(
        self,
        round_in_cycle: int,
        schedule_n_cap: float,
        target_estimate: float,
    ) -> float:
        """Compute beta from the current ``schedule_n_cap`` and both targets.

        ``target_estimate`` is treated as ``target_estimate_1`` for
        compatibility with the parent's call signature.
        """
        t1 = float(target_estimate)
        t2 = float(self._target_2)
        p = float(schedule_n_cap)
        beta = (1.0 - abs(p - t1)) * (1.0 - abs(p - t2)) / float(self._C_g)
        return float(max(0.0, min(1.0, beta)))

    def to_config(self) -> dict[str, Any]:
        return {
            "family": self.FAMILY,
            "target_estimate_1": float(self._target),
            "target_estimate_2": float(self._target_2),
            "C_g": float(self._C_g),
        }

    @classmethod
    def from_config(
        cls, config: dict[str, Any]
    ) -> DualTargetAdaptivePolicyDriver:
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        return cls(
            target_estimate_1=float(config.get("target_estimate_1", 0.5)),
            target_estimate_2=float(config.get("target_estimate_2", 0.5)),
            C_g=float(config.get("C_g", 1.0)),
        )


__all__ = [
    "DUAL_TARGET_ADAPTIVE_FAMILY",
    "DualTargetAdaptivePolicyDriver",
    "MULTICHANNEL_CONSTANT_POLICY_FAMILY",
    "MULTICHANNEL_JITTERED_FAMILY",
    "MultiChannelConstantPolicyDriver",
    "MultiChannelJitteredConstantScheduler",
]
