"""Handoff :class:`SequentialScheduler` (P1 #16).

Extends :class:`adaptive_reflow.algorithm.sequential.SequentialScheduler`
with a configurable handoff blending window: instead of switching from
slot ``i`` to slot ``i + 1`` as a step discontinuity, the scheduler
blends the two slots over ``handoff_window`` rounds using a cosine
ramp. Quantitative target: the ``n_cap`` trajectory at the slot
boundary has zero step discontinuity and a controlled Lipschitz
modulus on the handoff region.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.algorithm.scheduler import ScheduleSample
from adaptive_reflow.algorithm.sequential import (
    SEQUENTIAL_FAMILY,
    SequentialScheduler,
    SequentialSlot,
    _validate_positive_int,
)
from adaptive_reflow.contracts import (
    CosineScheduleSample,
    hash_artifact,
)

HANDOFF_FAMILY: str = "handoff_sequential"
"""Registry key for :class:`HandoffSequentialScheduler` (P1)."""


def _blend_n_cap(
    n_cap_a: float,
    n_cap_b: float,
    *,
    progress: float,
) -> float:
    """Cosine-ramp blend of two ``n_cap`` values on ``progress in [0, 1]``."""
    if not (0.0 <= progress <= 1.0):
        progress = max(0.0, min(1.0, progress))
    alpha = 0.5 * (1.0 - math.cos(math.pi * progress))
    return float((1.0 - alpha) * n_cap_a + alpha * n_cap_b)


class HandoffSequentialScheduler(SequentialScheduler):
    """Sequential scheduler with a cosine handoff window (P1 #16).

    Like :class:`SequentialScheduler`, takes a list of
    ``(scheduler, n_rounds)`` slots. In addition, every slot boundary
    is smoothed over the last ``handoff_window`` rounds of the
    outgoing slot plus the first ``handoff_window`` rounds of the
    incoming slot — within the handoff region the ``n_cap`` is a
    cosine-ramped blend of the two slots' ``n_cap`` values.

    ``handoff_window=0`` reproduces the legacy
    :class:`SequentialScheduler` byte-for-byte. ``handoff_window=1``
    smooths a single boundary round; ``handoff_window=n_rounds/2``
    gives a deep overlap. The blended sample carries the audit code
    ``"sequential_handoff:slot_i_to_slot_j:progress=K/N"`` so the
    audit trail records every boundary transition.

    Module boundary
    ---------------

    * Stdlib-only. No torch. No I/O.
    * Deterministic given identical inputs.
    * Pure w.r.t. arguments; state lives in instance attributes and
      is cleared on :meth:`reset`.
    """

    def __init__(
        self,
        *,
        schedulers: list[tuple[Any, int]] | list[SequentialSlot],
        handoff_window: int = 2,
    ) -> None:
        super().__init__(schedulers=schedulers)
        if isinstance(handoff_window, bool) or not isinstance(handoff_window, int):
            raise ValueError(
                f"handoff_window must be int, got {handoff_window!r}"
            )
        if int(handoff_window) < 0:
            raise ValueError(
                f"handoff_window must be >= 0, got {handoff_window!r}"
            )
        self._handoff_window = int(handoff_window)
        # Build a config hash that folds in the handoff window.
        self._config_hash_value = hash_artifact(
            {
                "algorithm": "handoff_sequential",
                "schedule_family": HANDOFF_FAMILY,
                "total_rounds": int(self._total_rounds),
                "handoff_window": int(self._handoff_window),
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

    @property
    def handoff_window(self) -> int:
        """Return the configured handoff window (rounds)."""
        return int(self._handoff_window)

    def schedule_family(self) -> str:
        """Return ``"handoff_sequential"``."""
        return HANDOFF_FAMILY

    def _handoff_pair(
        self,
        round_in_cycle: int,
    ) -> tuple[bool, SequentialSlot, SequentialSlot, float]:
        """Return ``(in_handoff, outgoing, incoming, progress)``.

        ``progress in [0, 1]`` is the cosine-ramp parameter, with
        ``0`` at the outgoing slot and ``1`` at the incoming slot.
        When the round is not in a handoff region, the function
        returns ``(False, active_slot, active_slot, 0.0)`` so callers
        can fall back to the parent class's sample.
        """
        if self._handoff_window <= 0 or len(self._slots) < 2:
            return (False, self._slots[0], self._slots[0], 0.0)
        cumulative = 0
        for i, slot in enumerate(self._slots[:-1]):
            nxt = cumulative + int(slot.n_rounds)
            # The handoff region straddles the boundary between slot i
            # (last ``handoff_window`` rounds) and slot i + 1 (first
            # ``handoff_window`` rounds).  Distance from the boundary
            # measured in rounds.
            r = int(round_in_cycle)
            if nxt - self._handoff_window <= r < nxt:
                # Inside the outgoing half of the handoff.
                steps_into = nxt - 1 - r  # 0 at boundary, positive inside
                if steps_into >= self._handoff_window:
                    break
                progress = float(steps_into + 1) / float(2 * self._handoff_window)
                return (True, slot, self._slots[i + 1], progress)
            if nxt <= r < nxt + self._handoff_window:
                # Inside the incoming half of the handoff.
                steps_into = r - nxt + 1  # 1 at boundary, positive inside
                if steps_into > self._handoff_window:
                    break
                progress = float(self._handoff_window + steps_into) / float(
                    2 * self._handoff_window
                )
                return (True, slot, self._slots[i + 1], progress)
            cumulative = nxt
        return (False, self._slots[0], self._slots[0], 0.0)

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        """Return a handoff-blended :class:`ScheduleSample`.

        Outside the handoff window this is identical to the parent
        class. Inside the window it returns a cos-blended ``n_cap``
        carrying the ``sequential_handoff`` audit code.
        """
        try:
            r = int(round_in_cycle)
        except (TypeError, ValueError):
            r = 0
        in_handoff, outgoing, incoming, progress = self._handoff_pair(r)
        # Use the parent class's behaviour for the basic sample shape.
        base = super().sample(outer_cycle_id, r, target_round)
        if not in_handoff:
            return base
        # Re-sample the outgoing and incoming slots at their own
        # round-relative index to get the unblended ``n_cap`` of each.
        out_idx = self._slots.index(outgoing)
        in_idx = self._slots.index(incoming)
        out_offset = sum(int(s.n_rounds) for s in self._slots[:out_idx])
        in_offset = sum(int(s.n_rounds) for s in self._slots[:in_idx])
        # Clamp sub-rounds into the slot's cycle range so a Constant
        # scheduler (which has a single round) still accepts the
        # ``round_in_cycle`` argument.
        out_len = int(outgoing.scheduler.cycle_length())
        in_len = int(incoming.scheduler.cycle_length())
        out_sub = max(0, min(out_len - 1, r - out_offset)) if out_len > 0 else 0
        in_sub = max(0, min(in_len - 1, r - in_offset)) if in_len > 0 else 0
        out_sample = outgoing.scheduler.sample(
            outer_cycle_id=outer_cycle_id,
            round_in_cycle=out_sub,
            target_round=target_round,
        )
        in_sample = incoming.scheduler.sample(
            outer_cycle_id=outer_cycle_id,
            round_in_cycle=in_sub,
            target_round=target_round,
        )
        blended_n_cap = _blend_n_cap(
            float(out_sample.n_cap), float(in_sample.n_cap), progress=progress
        )
        codes = base.audit_codes + (
            f"sequential_handoff:slot_{out_idx}_to_slot_{in_idx}"
            f":progress={progress:.4f}",
        )
        return ScheduleSample(
            outer_cycle_id=int(base.outer_cycle_id),
            round_in_cycle=int(r),
            cycle_length=int(self._total_rounds),
            n_cap=float(blended_n_cap),
            n_min=float(min(out_sample.n_min, in_sample.n_min)),
            n_max=float(max(out_sample.n_max, in_sample.n_max)),
            u_r=float(base.u_r),
            family=HANDOFF_FAMILY,
            computed_at_round=int(base.computed_at_round),
            schedule_hash=str(self._config_hash_value),
            audit_codes=tuple(codes),
            evidence_ratio=base.evidence_ratio,
        )

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict."""
        return {
            "family": HANDOFF_FAMILY,
            "total_rounds": int(self._total_rounds),
            "handoff_window": int(self._handoff_window),
            "slots": [
                {
                    "scheduler": slot.scheduler.to_config(),
                    "n_rounds": int(slot.n_rounds),
                }
                for slot in self._slots
            ],
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> HandoffSequentialScheduler:
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
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
            from adaptive_reflow.algorithm.sequential import _dispatch_scheduler_config
            sub = _dispatch_scheduler_config(sub_cfg)
            parsed.append((sub, n_rounds))
        return cls(schedulers=parsed, handoff_window=int(config.get("handoff_window", 2)))


__all__ = [
    "HANDOFF_FAMILY",
    "HandoffSequentialScheduler",
    "_blend_n_cap",
]
