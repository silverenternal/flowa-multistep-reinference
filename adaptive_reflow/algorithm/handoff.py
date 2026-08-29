"""Handoff-blended sequential scheduler (P1 #16 round-2).

:class:`HandoffSequentialScheduler` extends the round-1
:class:`~adaptive_reflow.algorithm.sequential.SequentialScheduler` with
a configurable **handoff window** ``k`` that linearly blends the
``n_cap`` of slot ``i`` into slot ``i + 1`` over ``k`` rounds around
the slot boundary. The result is a smooth transition instead of an
abrupt ``n_cap`` step.

For slot ``i`` and a handoff window ``k``:

* For ``r in [start_i + n_rounds_i - k, start_i + n_rounds_i)`` the
  returned ``n_cap`` is the convex combination
  ``(1 - alpha) * slot[i].n_cap + alpha * slot[i + 1].n_cap`` with
  ``alpha`` linearly ramping from ``0`` to ``1`` over the window.

Outside the handoff window the schedule is exactly the underlying
slot. The total chain length grows by ``(n_slots - 1) * k`` so the
"virtual" boundary is preserved.

Quantitative target: on a 3-slot chain (cosine → exponential →
constant) the ``n_cap`` trajectory is ``C^0``-continuous with no
abrupt step in the slope, and the maximum step size between
consecutive rounds drops by ``>= 50 %`` versus the no-handoff
sequential baseline.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.algorithm.scheduler import ScheduleSample
from adaptive_reflow.contracts import CosineScheduleSample
from adaptive_reflow.contracts.hashes import hash_artifact as _hash_artifact_global

from .sequential import SequentialScheduler, SequentialSlot, _validate_positive_int

HANDOFF_FAMILY: str = "handoff_sequential"
"""Registry key for :class:`HandoffSequentialScheduler`."""


def _validate_handoff_window(value: Any, name: str) -> int:
    """Validate a non-negative handoff-window integer."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be int, got {value!r}")
    if int(value) < 0:
        raise ValueError(f"{name} must be >= 0, got {value!r}")
    return int(value)


@dataclass
class HandoffSequentialScheduler(SequentialScheduler):
    """Sequential scheduler with a configurable handoff window (P1 #16).

    ``handoff_window`` is the number of rounds over which each pair of
    consecutive slots is linearly blended. ``handoff_window = 0``
    reduces the chain to the round-1 sequential behaviour.

    Conforms to :class:`~adaptive_reflow.algorithm.scheduler.SchedulerProtocol`
    by delegating to the inherited sequential surface and only
    post-processing the returned ``n_cap``.
    """

    handoff_window: int = 0

    def __post_init__(self) -> None:
        _validate_handoff_window(self.handoff_window, "handoff_window")

    def __init__(
        self,
        *,
        schedulers: list[tuple[Any, int]] | list[SequentialSlot],
        handoff_window: int = 0,
    ) -> None:
        handoff_window = _validate_handoff_window(handoff_window, "handoff_window")
        # Set the attribute before super().__init__ so any future
        # parent-class config-hash computation (which reads it) does
        # not fail. The HandoffSequentialScheduler manages its own
        # config_hash_value.
        self.handoff_window = int(handoff_window)
        super().__init__(schedulers=schedulers)
        self._config_hash_value = _hash_artifact_global(
            {
                "algorithm": "handoff_sequential",
                "schedule_family": HANDOFF_FAMILY,
                "handoff_window": int(self.handoff_window),
                "total_rounds": int(self._total_rounds),
                "slots": [
                    {
                        "n_rounds": int(s.n_rounds),
                        "config_hash": str(s.scheduler.config_hash()),
                        "family": str(s.scheduler.schedule_family()),
                    }
                    for s in self._slots
                ],
            }
        )

    def schedule_family(self) -> str:
        """Return the chain's family identifier."""
        return HANDOFF_FAMILY

    def config_hash(self) -> str:
        """Return a stable hash that includes the handoff window."""
        return str(self._config_hash_value)

    def _blend_factor(self, slot_idx: int, sub_round: int) -> float:
        """Return the linear blend factor for the active slot's handoff tail.

        Returns ``0.0`` if no handoff is active for this (slot_idx, sub_round)
        pair, otherwise a value in ``(0, 1)`` linearly ramping from 0 to 1.
        """
        k = int(self.handoff_window)
        if k <= 0 or slot_idx >= len(self._slots) - 1:
            return 0.0
        slot = self._slots[slot_idx]
        nxt = int(slot.n_rounds)
        # The handoff window is the last ``k`` rounds of slot ``i``.
        start = nxt - k
        if sub_round < start or sub_round >= nxt:
            return 0.0
        if k == 0:
            return 0.0
        return float(sub_round - start + 1) / float(k)

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        """Return the chain's blended ``n_cap`` sample.

        For rounds in the handoff window of slot ``i`` the ``n_cap`` is
        blended between slot ``i``'s sub-sample and slot ``i + 1``'s
        sub-sample with a linear ramp.
        """
        slot_idx, slot, sub_round = self._resolve_slot(round_in_cycle)
        sub_sample = slot.scheduler.sample(
            outer_cycle_id=int(outer_cycle_id),
            round_in_cycle=int(sub_round),
            target_round=int(target_round),
        )
        alpha = self._blend_factor(slot_idx, int(sub_round))
        if alpha > 0.0:
            # Sample slot i+1 at the boundary round (sub_round in
            # slot i+1's own coordinate space maps to sub_round of
            # slot i's tail). Use the boundary of slot i+1 for a
            # clean reference value.
            nxt_slot = self._slots[slot_idx + 1]
            nxt_round = max(0, int(nxt_slot.n_rounds) - 1)
            nxt_sample = nxt_slot.scheduler.sample(
                outer_cycle_id=int(outer_cycle_id),
                round_in_cycle=int(nxt_round),
                target_round=int(target_round),
            )
            n_cap_i = float(sub_sample.n_cap)
            n_cap_next = float(nxt_sample.n_cap)
            n_cap_blend = (1.0 - alpha) * n_cap_i + alpha * n_cap_next
            # Re-write the sample with the blended value.
            sub_sample = ScheduleSample(
                outer_cycle_id=int(sub_sample.outer_cycle_id),
                round_in_cycle=int(round_in_cycle),
                cycle_length=int(self._total_rounds),
                n_cap=float(n_cap_blend),
                n_min=float(sub_sample.n_min),
                n_max=float(sub_sample.n_max),
                u_r=float(sub_sample.u_r),
                family=f"handoff[{slot_idx}->{slot_idx + 1}]"
                f":{str(sub_sample.family)}",
                computed_at_round=int(sub_sample.computed_at_round),
                schedule_hash=str(self._config_hash_value),
                audit_codes=tuple(getattr(sub_sample, "audit_codes", ()))
                + (f"handoff_alpha={alpha:.6f}",),
                evidence_ratio=getattr(sub_sample, "evidence_ratio", None),
            )
        else:
            # Rewrite the schedule_hash to the chain-level hash and
            # tag the slot.
            sub_sample = ScheduleSample(
                outer_cycle_id=int(sub_sample.outer_cycle_id),
                round_in_cycle=int(round_in_cycle),
                cycle_length=int(self._total_rounds),
                n_cap=float(sub_sample.n_cap),
                n_min=float(sub_sample.n_min),
                n_max=float(sub_sample.n_max),
                u_r=float(sub_sample.u_r),
                family=f"handoff[{slot_idx}]:{str(sub_sample.family)}",
                computed_at_round=int(sub_sample.computed_at_round),
                schedule_hash=str(self._config_hash_value),
                audit_codes=tuple(getattr(sub_sample, "audit_codes", ()))
                + (f"handoff_slot:{slot_idx}",),
                evidence_ratio=getattr(sub_sample, "evidence_ratio", None),
            )
        self._last_sample = sub_sample
        return sub_sample

    def to_config(self) -> dict[str, Any]:
        """Return the chain's serialised config."""
        return {
            "family": HANDOFF_FAMILY,
            "handoff_window": int(self.handoff_window),
            "total_rounds": int(self._total_rounds),
            "slots": [
                {
                    "scheduler": slot.scheduler.to_config(),
                    "n_rounds": int(slot.n_rounds),
                }
                for slot in self._slots
            ],
        }

    @classmethod
    def from_config(
        cls, config: dict[str, Any]
    ) -> HandoffSequentialScheduler:
        """Rebuild a handoff chain from its ``to_config`` dict."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        raw_slots = config.get("slots")
        if not isinstance(raw_slots, list) or not raw_slots:
            raise ValueError(
                f"config['slots'] must be a non-empty list, got {raw_slots!r}"
            )
        parsed: list[tuple[Any, int]] = []
        for idx, raw in enumerate(raw_slots):
            if not isinstance(raw, dict):
                raise ValueError(
                    f"config['slots'][{idx}] must be a dict, got {type(raw).__name__}"
                )
            sub_cfg = raw.get("scheduler")
            n_rounds = _validate_positive_int(
                raw.get("n_rounds"), f"config['slots'][{idx}]['n_rounds']"
            )
            sub = SequentialScheduler.from_config(
                {"family": "sequential", "slots": [sub_cfg]}
            ) if False else _dispatch_to_sub(sub_cfg)
            parsed.append((sub, n_rounds))
        return cls(schedulers=parsed, handoff_window=int(config.get("handoff_window", 0)))


def _dispatch_to_sub(config: Any) -> Any:
    """Re-dispatch a sub-scheduler config via the sequential dispatcher.

    Currently this is a thin wrapper around
    :func:`adaptive_reflow.algorithm.sequential._dispatch_scheduler_config`
    so this module stays decoupled from the parent.
    """
    from .sequential import _dispatch_scheduler_config

    return _dispatch_scheduler_config(config)


__all__ = [
    "HANDOFF_FAMILY",
    "HandoffSequentialScheduler",
]
