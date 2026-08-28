"""Sequential :class:`SchedulerProtocol` chaining (P1-2, external).

Mirrors :class:`torch.optim.lr_scheduler.SequentialLR`. A
:class:`SequentialScheduler` takes a list of ``(scheduler, n_rounds)``
tuples and chains them so that round ``r`` is served by the scheduler
at index ``i`` where ``r`` falls in ``[sum(n_rounds[:i]),
sum(n_rounds[:i+1]))``.

Example:

    chain = SequentialScheduler(
        schedulers=[
            (CosineAnnealScheduler(cycle_length=8), 8),
            (ExponentialScheduler(cycle_length=4), 4),
        ],
    )

runs the cosine scheduler for the first 8 rounds, then the
exponential scheduler for the next 4 rounds.

Contract
--------

* :meth:`cycle_length` returns ``sum(n_rounds)`` (the chain's total
  length in rounds).
* :meth:`sample` selects the sub-scheduler by round index and
  translates ``round_in_cycle`` so the chosen sub-scheduler observes
  its own cycle-relative index, not the chain-relative one.
* :meth:`config_hash` includes every sub-scheduler's ``config_hash`` so
  two chains with the same shape but different sub-schedulers are
  distinguishable in provenance.
* :meth:`reset` resets the chain and every sub-scheduler.
* :meth:`inject_noise` delegates to the active sub-scheduler.
* :meth:`to_config` / :meth:`from_config` round-trip the entire chain
  (including sub-scheduler configs and ``n_rounds`` per slot).
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.algorithm.scheduler import (
    ScheduleSample,
)
from adaptive_reflow.contracts import (
    CosineScheduleSample,
    hash_artifact,
)
from adaptive_reflow.contracts.hashes import hash_artifact as _hash_artifact_global

SEQUENTIAL_FAMILY: str = "sequential"
"""Registry key for :class:`SequentialScheduler` (P1-2)."""

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SequentialSlot:
    """One slot in a :class:`SequentialScheduler`.

    A slot pairs a :class:`SchedulerProtocol` implementation with the
    number of rounds it should drive. ``n_rounds`` must be a positive
    integer.
    """

    scheduler: Any  # SchedulerProtocol (avoid runtime cycle by using Any)
    n_rounds: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be int, got {value!r}")
    if int(value) < 1:
        raise ValueError(f"{name} must be >= 1, got {value!r}")
    return int(value)


# ---------------------------------------------------------------------------
# SequentialScheduler
# ---------------------------------------------------------------------------


class SequentialScheduler:
    """Chain N :class:`SchedulerProtocol` instances by round range (P1-2).

    Takes ``schedulers=[(scheduler, n_rounds), ...]`` and serves the
    scheduler at index ``i`` for rounds
    ``[sum(n_rounds[:i]), sum(n_rounds[:i+1]))``. Mirrors
    :class:`torch.optim.lr_scheduler.SequentialLR`.

    Conforms to :class:`SchedulerProtocol`: every method of the protocol
    is implemented in terms of the active sub-scheduler.

    Config round-trip (P1-1): :meth:`to_config` returns a dict keyed by
    ``"family": "sequential"`` plus a ``"slots"`` list of
    ``{"scheduler": <sub-config>, "n_rounds": int}``. :meth:`from_config`
    dispatches each sub-config through :func:`_dispatch_scheduler_config`
    so any registered scheduler family round-trips.
    """

    def __init__(
        self,
        *,
        schedulers: list[tuple[Any, int]] | list[SequentialSlot],
    ) -> None:
        """Construct the sequential chain.

        :param schedulers: an ordered list of ``(scheduler, n_rounds)``
            tuples or :class:`SequentialSlot` instances. Each
            ``n_rounds`` must be a positive integer; the chain's total
            length is the sum of all ``n_rounds``.
        """
        if not schedulers:
            raise ValueError(
                "SequentialScheduler requires at least one sub-scheduler"
            )
        parsed: list[SequentialSlot] = []
        for idx, item in enumerate(schedulers):
            if isinstance(item, SequentialSlot):
                scheduler_obj = item.scheduler
                n_rounds = _validate_positive_int(item.n_rounds, f"schedulers[{idx}].n_rounds")
            elif isinstance(item, tuple) and len(item) == 2:
                scheduler_obj, raw_n = item
                n_rounds = _validate_positive_int(raw_n, f"schedulers[{idx}][1]")
            else:
                raise ValueError(
                    f"schedulers[{idx}] must be a (scheduler, n_rounds) tuple or "
                    f"SequentialSlot, got {type(item).__name__}"
                )
            if scheduler_obj is None:
                raise ValueError(
                    f"schedulers[{idx}][0] must be a SchedulerProtocol, got None"
                )
            # Lazy Protocol surface check via duck typing — every
            # SchedulerProtocol implementation has these methods.
            for required in ("sample", "cycle_length", "schedule_family",
                              "config_hash", "reset", "inject_noise",
                              "to_config", "from_config"):
                if not hasattr(scheduler_obj, required):
                    raise TypeError(
                        f"schedulers[{idx}][0] is missing required method "
                        f"{required!r}; not a SchedulerProtocol"
                    )
            parsed.append(
                SequentialSlot(scheduler=scheduler_obj, n_rounds=n_rounds)
            )
        self._slots: tuple[SequentialSlot, ...] = tuple(parsed)
        self._total_rounds: int = sum(s.n_rounds for s in self._slots)
        self._config_hash_value = _hash_artifact_global(
            {
                "algorithm": "sequential",
                "schedule_family": "sequential",
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
        self._last_sample: ScheduleSample | None = None
        # A9 uplift: per-call audit_codes accumulator for the
        # seq_inject_noise_fallback code emitted by ``inject_noise``
        # when the chain's total length is shorter than the caller's
        # ``computed_at_round``. Cleared on ``reset()``.
        self._audit_codes: list[str] = []

    # -- accessors ---------------------------------------------------------

    @property
    def slots(self) -> tuple[SequentialSlot, ...]:
        """Return the chain's slots as an immutable tuple."""
        return self._slots

    @property
    def total_rounds(self) -> int:
        """Return the sum of all slot ``n_rounds``."""
        return int(self._total_rounds)

    @property
    def last_sample(self) -> ScheduleSample | None:
        """Return the most recent :class:`ScheduleSample` (or ``None``)."""
        return self._last_sample

    @property
    def audit_codes(self) -> tuple[str, ...]:
        """Return the chain's audit_codes tuple (A9 uplift).

        The list is populated by :meth:`inject_noise` whenever the
        helper falls back to ``slot[0].inject_noise`` because the
        chain's total length is shorter than the caller's
        ``schedule_sample.computed_at_round``. Cleared on
        :meth:`reset`.
        """
        return tuple(self._audit_codes)

    # -- helpers -----------------------------------------------------------

    def _resolve_slot(self, round_in_cycle: int) -> tuple[int, SequentialSlot, int]:
        """Return ``(slot_index, slot, sub_round_in_cycle)`` for ``round_in_cycle``.

        ``round_in_cycle`` is the chain-relative round index (in
        ``[0, total_rounds - 1]``). ``sub_round_in_cycle`` is the
        cycle-relative round index passed to the sub-scheduler.
        """
        if not isinstance(round_in_cycle, int) or isinstance(round_in_cycle, bool):
            raise ValueError(
                f"round_in_cycle must be int, got {round_in_cycle!r}"
            )
        r = int(round_in_cycle)
        if r < 0 or r >= int(self._total_rounds):
            raise ValueError(
                f"round_in_cycle must be in [0, {int(self._total_rounds) - 1}], "
                f"got {round_in_cycle!r}"
            )
        cumulative = 0
        for idx, slot in enumerate(self._slots):
            nxt = cumulative + int(slot.n_rounds)
            if r < nxt:
                return (idx, slot, r - cumulative)
            cumulative = nxt
        # Unreachable: defensive fall-through.
        raise RuntimeError(
            f"round_in_cycle {round_in_cycle} did not resolve into any slot"
        )

    # -- SchedulerProtocol -------------------------------------------------

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        """Return the chain's capacity sample for ``round_in_cycle``.

        Selects the active sub-scheduler, computes the sub-round index,
        and delegates. The returned sample carries the chain's
        ``schedule_hash`` (so two chains with the same shape but
        different sub-schedulers are distinguishable in provenance).
        """
        slot_idx, slot, sub_round = self._resolve_slot(round_in_cycle)
        # Delegate sample to the sub-scheduler using its own sub-round.
        sub_sample = slot.scheduler.sample(
            outer_cycle_id=int(outer_cycle_id),
            round_in_cycle=int(sub_round),
            target_round=int(target_round),
        )
        # Rewrite the schedule_hash to the chain-level hash so downstream
        # consumers see one stable identifier for the entire chain.
        # P0-A1 / P0-A7: the sub-scheduler's ``audit_codes`` and
        # ``evidence_ratio`` are forwarded verbatim (prefixed with the
        # chain slot marker) so the chain never hides which family
        # actually produced the round.
        sub_codes = tuple(
            str(code) for code in getattr(sub_sample, "audit_codes", ()) or ()
        )
        rewritten = ScheduleSample(
            outer_cycle_id=int(sub_sample.outer_cycle_id),
            round_in_cycle=int(round_in_cycle),
            cycle_length=int(self._total_rounds),
            n_cap=float(sub_sample.n_cap),
            n_min=float(sub_sample.n_min),
            n_max=float(sub_sample.n_max),
            u_r=float(sub_sample.u_r),
            family=f"sequential[{slot_idx}]:{str(sub_sample.family)}",
            computed_at_round=int(sub_sample.computed_at_round),
            schedule_hash=str(self._config_hash_value),
            audit_codes=(f"sequential_slot:{slot_idx}",) + sub_codes,
            evidence_ratio=getattr(sub_sample, "evidence_ratio", None),
        )
        self._last_sample = rewritten
        return rewritten

    def cycle_length(self) -> int:
        """Return the chain's total length (sum of all slot ``n_rounds``)."""
        return int(self._total_rounds)

    def schedule_family(self) -> str:
        """Return the chain's family identifier."""
        return "sequential"

    def config_hash(self) -> str:
        """Return a stable identifier for the chain + every sub-scheduler.

        The hash includes each sub-scheduler's own ``config_hash`` so
        two chains with identical slot shapes but different sub-
        scheduler configurations produce distinct hashes (P1-2).
        """
        return str(self._config_hash_value)

    def reset(self) -> None:
        """Reset the chain and every sub-scheduler."""
        for slot in self._slots:
            slot.scheduler.reset()
        self._last_sample = None
        self._audit_codes = []

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        """Forward per-round feedback to *every* sub-scheduler (A8 uplift).

        P0-A8: the chain forwards ``metrics`` to every slot (active
        plus inactive) with a slot-relative round index clamped to
        ``[0, n_rounds - 1]``. Chained adaptive schedulers can now
        warm up before their slot starts instead of only ever seeing
        a single feedback call when their slot activates. Slots whose
        ``record_round_feedback`` is a no-op (e.g. cosine, constant)
        ignore the call without side-effects; slots whose method
        accepts arbitrary round indices (e.g.
        :class:`ConvergenceAdaptiveScheduler`) can build history
        across the entire chain length.

        Falls back to no-op when ``round_in_cycle`` is out of range
        (the chain was constructed with a shorter total length than
        the caller expected) — legacy behaviour preserved so callers
        that explicitly signal out-of-range do not silently warm up
        the chain's slots.
        """
        try:
            r = int(round_in_cycle)
        except (TypeError, ValueError):
            return
        if r < 0 or r >= int(self._total_rounds):
            return  # Out-of-range: silent no-op (legacy behaviour).
        # Resolve the cumulative offset to the *active* slot.
        active_offset = 0
        cumulative = 0
        for slot in self._slots:
            nxt = cumulative + int(slot.n_rounds)
            if r < nxt:
                active_offset = cumulative
                break
            cumulative = nxt
        # Forward to *every* slot with its own slot-relative index,
        # clamped to [0, slot.n_rounds - 1] so an out-of-cycle call
        # still warms up the scheduler at the slot boundary.
        for slot in self._slots:
            sub_round = r - active_offset
            if sub_round < 0:
                sub_round = 0
            elif sub_round >= int(slot.n_rounds):
                sub_round = int(slot.n_rounds) - 1
            slot.scheduler.record_round_feedback(
                round_in_cycle=int(sub_round),
                metrics=metrics,
            )

    def inject_noise(
        self,
        state: NDArray[np.float64],
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]:
        """Delegate noise injection to the active sub-scheduler.

        Looks up the sub-scheduler by ``schedule_sample.computed_at_round``
        (the engine always passes the round's per-cycle index here);
        when no slot matches the helper falls back to the first slot's
        ``inject_noise``.

        A9 uplift: when the fallback fires, the canonical audit code
        ``seq_inject_noise_fallback:total_rounds=<N>:computed_at_round=<R>``
        is appended to ``self._audit_codes`` so the runner / audit
        ledger can record the mis-wiring instead of silently using
        ``slot[0]``. The fallback itself is preserved for backward
        compatibility (the chain still returns a fresh state); the
        audit trail is the new signal.
        """
        if self._slots:
            try:
                _, slot, _ = self._resolve_slot(int(schedule_sample.computed_at_round))
                return slot.scheduler.inject_noise(
                    state, schedule_sample, generator=generator
                )
            except (ValueError, IndexError):
                pass
            except TypeError:
                # ``computed_at_round`` may be a non-int on legacy
                # call paths; fall through to the audit-emitting
                # fallback below.
                pass
        self._audit_codes.append(
            "seq_inject_noise_fallback"
            f":total_rounds={int(self._total_rounds)}"
            f":computed_at_round="
            f"{int(getattr(schedule_sample, 'computed_at_round', -1))}"
        )
        return self._slots[0].scheduler.inject_noise(
            state, schedule_sample, generator=generator
        )

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict for the chain."""
        return {
            "family": "sequential",
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
    def from_config(cls, config: dict[str, Any]) -> SequentialScheduler:
        """Rebuild a :class:`SequentialScheduler` from its ``to_config`` dict."""
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
            sub = _dispatch_scheduler_config(sub_cfg)
            parsed.append((sub, n_rounds))
        return cls(schedulers=parsed)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def _dispatch_scheduler_config(config: Any) -> Any:
    """Dispatch a sub-scheduler config dict to its registered family.

    Local copy of :func:`build_scheduler_from_config` so this module
    stays self-contained without dragging the full scheduler module
    back into itself (the parent module already exposes the canonical
    dispatcher; we keep a minimal mirror here to avoid an import cycle
    when the parent module imports :class:`SequentialScheduler` for
    registration in :data:`SCHEDULER_REGISTRY`).
    """
    if not isinstance(config, dict):
        raise TypeError(
            f"sub-scheduler config must be a dict, got {type(config).__name__}"
        )
    family = config.get("family")
    if not isinstance(family, str):
        raise ValueError(
            f"sub-scheduler config['family'] must be str, got {family!r}"
        )
    key = family.strip().lower()

    # Local imports to break the cycle: the parent module re-exports
    # the concrete classes; importing them here is safe because this
    # function is only invoked from :meth:`SequentialScheduler.from_config`.
    from adaptive_reflow.algorithm.scheduler import (
        CodimensionSheetScheduler,
        ConstantScheduler,
        ConvergenceAdaptiveScheduler,
        CosineAnnealScheduler,
        ExponentialScheduler,
        LinearScheduler,
        PolynomialScheduler,
        SigmoidScheduler,
    )

    if key == "sequential":
        # Nested sequential chains are supported but must be loaded
        # via the dedicated constructor to avoid recursion through
        # :meth:`from_config`.
        return SequentialScheduler.from_config(config)
    if key == "cosine":
        return CosineAnnealScheduler.from_config(config)
    if key == "constant":
        return ConstantScheduler.from_config(config)
    if key == "linear":
        return LinearScheduler.from_config(config)
    if key == "exponential":
        return ExponentialScheduler.from_config(config)
    if key == "polynomial":
        return PolynomialScheduler.from_config(config)
    if key == "sigmoid":
        return SigmoidScheduler.from_config(config)
    if key == "convergence_adaptive":
        return ConvergenceAdaptiveScheduler.from_config(config)
    if key == "codimension_sheet":
        return CodimensionSheetScheduler.from_config(config)
    raise KeyError(
        f"unknown scheduler family {family!r}; cannot dispatch sub-scheduler"
    )


__all__ = [
    "SEQUENTIAL_FAMILY",
    "SequentialScheduler",
    "SequentialSlot",
]
