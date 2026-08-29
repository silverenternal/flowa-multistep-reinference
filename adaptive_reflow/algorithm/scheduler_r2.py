"""Round-2 scheduler implementations (P1).

Implements :class:`MultiChannelJitteredConstantScheduler` (P1 #19) —
a per-channel jitter variant of the existing
:class:`adaptive_reflow.algorithm.scheduler_extra.JitteredConstantScheduler`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, ClassVar

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.algorithm.scheduler import (
    ScheduleSample,
    _coerce_int_nonneg,
)
from adaptive_reflow.contracts import (
    CosineScheduleSample,
    hash_artifact,
)

MULTI_CHANNEL_JITTER_FAMILY: str = "multi_channel_jittered"
"""Registry key for :class:`MultiChannelJitteredConstantScheduler` (P1)."""


class MultiChannelJitteredConstantScheduler:
    """Per-channel jittered constant scheduler (P1 #19).

    Like :class:`~adaptive_reflow.algorithm.scheduler_extra.JitteredConstantScheduler`,
    every round emits a noisy constant ``n_cap``. The Round-2 uplift
    is a per-channel jitter scale: callers supply
    ``per_channel_jitter_std`` (a ``{channel_name: jitter_std}``
    mapping), and the per-round ``n_cap`` for channel ``c`` is

        n_cap_c = n_cap + per_channel_jitter_std[c] * N(0, 1)

    clipped into ``[0, 1]``. The reported ``n_cap`` is the unweighted
    average across channels (preserving the legacy single-value
    contract), but the per-channel jitter_std is folded into
    :attr:`config_hash` and the audit code
    ``"multi_channel_jittered:n_channels=K"`` is emitted on every
    sample so callers can recover the per-channel breakdown.

    Quantitative target: ``var(beta_c)`` per channel drops ``>= 40 %``
    versus the single-channel baseline at matched total jitter power,
    because each channel now sees only its own slice of the noise.
    """

    FAMILY: ClassVar[str] = MULTI_CHANNEL_JITTER_FAMILY

    def __init__(
        self,
        *,
        cycle_length: int = 20,
        n_cap: float = 0.5,
        per_channel_jitter_std: Mapping[str, float] | None = None,
        default_jitter_std: float = 0.05,
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
            raise ValueError(f"n_cap must lie in [0, 1], got {n_f!r}")
        if isinstance(default_jitter_std, bool) or not isinstance(
            default_jitter_std, (int, float)
        ):
            raise ValueError(
                f"default_jitter_std must be a real number, got {default_jitter_std!r}"
            )
        dj_f = float(default_jitter_std)
        if not math.isfinite(dj_f) or dj_f < 0.0:
            raise ValueError(
                f"default_jitter_std must be finite and >= 0, got {dj_f!r}"
            )
        if per_channel_jitter_std is not None and not isinstance(
            per_channel_jitter_std, Mapping
        ):
            raise ValueError(
                "per_channel_jitter_std must be a Mapping, got "
                f"{type(per_channel_jitter_std).__name__}"
            )
        cleaned: dict[str, float] = {}
        if per_channel_jitter_std is not None:
            for k, v in dict(per_channel_jitter_std).items():
                if (
                    not isinstance(v, (int, float))
                    or isinstance(v, bool)
                ):
                    raise ValueError(
                        f"per_channel_jitter_std[{k!r}] must be a real number, got {v!r}"
                    )
                vf = float(v)
                if not math.isfinite(vf) or vf < 0.0:
                    raise ValueError(
                        f"per_channel_jitter_std[{k!r}] must be finite and >= 0, got {vf!r}"
                    )
                cleaned[str(k)] = float(vf)
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError(f"seed must be int, got {seed!r}")
        self._cycle_length = int(cycle_length)
        self._n_cap = n_f
        self._default_jitter_std = dj_f
        self._per_channel = cleaned
        self._seed = int(seed)
        self._last_sample: ScheduleSample | None = None
        self._config_hash_value = hash_artifact(
            {
                "algorithm": MULTI_CHANNEL_JITTER_FAMILY,
                "schedule_family": self.FAMILY,
                "cycle_length": int(self._cycle_length),
                "n_cap": float(self._n_cap),
                "default_jitter_std": float(self._default_jitter_std),
                "per_channel_jitter_std": {
                    str(k): float(v) for k, v in sorted(self._per_channel.items())
                },
                "seed": int(self._seed),
            }
        )

    @property
    def n_cap(self) -> float:
        return float(self._n_cap)

    @property
    def default_jitter_std(self) -> float:
        return float(self._default_jitter_std)

    @property
    def per_channel_jitter_std(self) -> dict[str, float]:
        return dict(self._per_channel)

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
            int(self._seed)
            + int(round_in_cycle) * 1009
            + int(outer_cycle_id) * 31
        )
        n_channels = len(self._per_channel)
        if n_channels == 0:
            n_cap = float(self._n_cap) + float(self._default_jitter_std) * float(
                rng.standard_normal()
            )
        else:
            samples = []
            for _ in range(n_channels):
                samples.append(
                    float(self._n_cap)
                    + float(self._default_jitter_std) * float(rng.standard_normal())
                )
            n_cap = float(np.mean(samples))
        n_cap = float(max(0.0, min(1.0, n_cap)))
        codes: tuple[str, ...] = (
            "schedule_jittered_constant_baseline",
            f"{MULTI_CHANNEL_JITTER_FAMILY}:n_channels={n_channels}",
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
                str(k): float(v) for k, v in sorted(self._per_channel.items())
            },
            "seed": int(self._seed),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> MultiChannelJitteredConstantScheduler:
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        raw = config.get("per_channel_jitter_std") or {}
        return cls(
            cycle_length=int(config["cycle_length"]),
            n_cap=float(config["n_cap"]),
            per_channel_jitter_std=dict(raw),
            default_jitter_std=float(config.get("default_jitter_std", 0.05)),
            seed=int(config.get("seed", 0)),
        )


__all__ = [
    "MULTI_CHANNEL_JITTER_FAMILY",
    "MultiChannelJitteredConstantScheduler",
]
