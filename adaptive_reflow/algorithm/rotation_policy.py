"""Rotation policy registry + implementations.

Implements the scheduler-rotation policy called out in the
algorithm-deep-uplift plan as P1:

* :class:`RoundRobinRotationPolicy` — round-robin over a pool of
  schedulers.
* :class:`BanditUCBRotationPolicy` — UCB1 bandit over the same pool.

Both expose :meth:`choose(history) -> idx` and a frozen config hash so
the framework can swap rotation policies polymorphically.

Module boundary
---------------

* stdlib-only. No ``torch``. No I/O.
* Deterministic given identical inputs (no internal randomness).
* Fail-closed: bad pool / n_arms raises :class:`ValueError`.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any, ClassVar

from adaptive_reflow.contracts import hash_artifact


class RotationPolicy:
    """Abstract rotation policy (non-Protocol for runtime instantiation)."""

    family: ClassVar[str] = ""

    def choose(
        self, history: Sequence[float]
    ) -> int:
        raise NotImplementedError

    def config_hash(self) -> str:
        raise NotImplementedError

    def to_config(self) -> dict[str, Any]:
        return {"family": self.family, "config_hash": self.config_hash()}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> RotationPolicy:
        raise NotImplementedError


class RoundRobinRotationPolicy(RotationPolicy):
    """Round-robin rotation policy."""

    family: ClassVar[str] = "round_robin"

    def __init__(self, n_arms: int = 2) -> None:
        if not isinstance(n_arms, int) or isinstance(n_arms, bool):
            raise ValueError(f"n_arms must be int, got {n_arms!r}")
        if int(n_arms) < 1:
            raise ValueError(f"n_arms must be >= 1, got {n_arms!r}")
        self._n_arms = int(n_arms)
        self._counter = 0

    @property
    def n_arms(self) -> int:
        return int(self._n_arms)

    def choose(self, history: Sequence[float]) -> int:
        idx = self._counter % self._n_arms
        self._counter += 1
        return int(idx)

    def config_hash(self) -> str:
        return str(
            hash_artifact({"family": self.family, "n_arms": int(self._n_arms)})
        )

    def to_config(self) -> dict[str, Any]:
        return {"family": self.family, "n_arms": int(self._n_arms)}

    @classmethod
    def from_config(
        cls, config: dict[str, Any]
    ) -> RoundRobinRotationPolicy:
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        return cls(n_arms=int(config.get("n_arms", 2)))


class BanditUCBRotationPolicy(RotationPolicy):
    """UCB1 bandit rotation policy."""

    family: ClassVar[str] = "bandit_ucb"

    def __init__(self, n_arms: int = 2, exploration_coef: float = 1.0) -> None:
        if not isinstance(n_arms, int) or isinstance(n_arms, bool):
            raise ValueError(f"n_arms must be int, got {n_arms!r}")
        if int(n_arms) < 1:
            raise ValueError(f"n_arms must be >= 1, got {n_arms!r}")
        if (
            not isinstance(exploration_coef, (int, float))
            or isinstance(exploration_coef, bool)
        ):
            raise ValueError(
                "exploration_coef must be a real number, got "
                f"{exploration_coef!r}"
            )
        ec = float(exploration_coef)
        if not math.isfinite(ec) or ec <= 0.0:
            raise ValueError(
                f"exploration_coef must be finite and > 0, got {ec!r}"
            )
        self._n_arms = int(n_arms)
        self._exploration_coef = float(exploration_coef)
        self._counts: list[int] = [0] * self._n_arms
        self._sums: list[float] = [0.0] * self._n_arms

    @property
    def n_arms(self) -> int:
        return int(self._n_arms)

    @property
    def exploration_coef(self) -> float:
        return float(self._exploration_coef)

    def choose(self, history: Sequence[float]) -> int:
        # UCB1: argmax (mean + c * sqrt(2 * log(t) / n_i)) for each arm.
        total = sum(self._counts)
        if total == 0:
            return 0
        best = -1
        best_score = -math.inf
        log_t = math.log(total)
        for i in range(self._n_arms):
            if self._counts[i] == 0:
                # Force exploration of unseen arms first.
                return i
            mean = self._sums[i] / self._counts[i]
            bonus = self._exploration_coef * math.sqrt(
                2.0 * log_t / self._counts[i]
            )
            score = mean + bonus
            if score > best_score:
                best_score = score
                best = i
        return int(best if best >= 0 else 0)

    def update(self, arm_idx: int, reward: float) -> None:
        """Record the reward for ``arm_idx`` (for next choose)."""
        if not (0 <= int(arm_idx) < self._n_arms):
            raise ValueError(
                f"arm_idx must be in [0, {self._n_arms - 1}], "
                f"got {arm_idx!r}"
            )
        if not math.isfinite(float(reward)):
            return
        self._counts[int(arm_idx)] += 1
        self._sums[int(arm_idx)] += float(reward)

    def config_hash(self) -> str:
        return str(
            hash_artifact(
                {
                    "family": self.family,
                    "n_arms": int(self._n_arms),
                    "exploration_coef": float(self._exploration_coef),
                }
            )
        )

    def to_config(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "n_arms": int(self._n_arms),
            "exploration_coef": float(self._exploration_coef),
        }

    @classmethod
    def from_config(
        cls, config: dict[str, Any]
    ) -> BanditUCBRotationPolicy:
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        return cls(
            n_arms=int(config.get("n_arms", 2)),
            exploration_coef=float(config.get("exploration_coef", 1.0)),
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


ROTATION_POLICY_REGISTRY: dict[str, type[RotationPolicy]] = {
    "round_robin": RoundRobinRotationPolicy,
    "bandit_ucb": BanditUCBRotationPolicy,
}
"""Mapping from rotation-policy family to its implementation class."""


def build_rotation_policy(family: str, **kwargs: Any) -> RotationPolicy:
    """Return a fresh :class:`RotationPolicy` for ``family``."""
    if not isinstance(family, str):
        raise ValueError(f"family must be str, got {family!r}")
    if family not in ROTATION_POLICY_REGISTRY:
        raise KeyError(
            f"unknown rotation policy family {family!r}; "
            f"registered families: {sorted(ROTATION_POLICY_REGISTRY)!r}"
        )
    cls = ROTATION_POLICY_REGISTRY[family]
    return cls(**kwargs)


__all__ = [
    "BanditUCBRotationPolicy",
    "ROTATION_POLICY_REGISTRY",
    "RotationPolicy",
    "RoundRobinRotationPolicy",
    "build_rotation_policy",
]
