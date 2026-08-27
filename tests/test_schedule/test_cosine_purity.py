"""Purity boundary tests for :class:`CosineScheduleSampler` (gap B1 fix).

Gap B1: the legacy ``restart_trigger_event`` mutated ``self._last_sample``
as a hidden side effect, so two consecutive calls saw the AFTER state as
BEFORE. The split introduced by this fix:

* :meth:`CosineScheduleSampler.compute_restart_event` — pure w.r.t.
  ``self._last_sample``; reads the cached sample for
  ``noise_capacity_before`` and embeds the freshly-sampled
  ``noise_capacity_after`` sample in the returned event without
  writing it back.
* :meth:`CosineScheduleSampler.record_restart_event` — explicit mutation
  boundary; commits the after-sample embedded in the event to
  ``self._last_sample``. Idempotent.

These tests pin the boundary so the algorithmic gap cannot silently
regress.
"""
from __future__ import annotations

from types import MappingProxyType

import pytest

from adaptive_reflow.contracts import (
    ArtifactHash,
    BundleId,
    ChannelName,
    CosineScheduleConfig,
    FactorValue,
    ProvenanceChain,
    RestartTriggerCode,
    RestartTriggerEvent,
    TriggerId,
)
from adaptive_reflow.schedule.cosine import CosineScheduleSampler

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_config(
    *,
    schedule_family: str = "cosine_no_restart",
    cycle_length: int = 4,
    n_min: float = 0.1,
    n_max: float = 0.9,
) -> CosineScheduleConfig:
    """Build a minimal valid :class:`CosineScheduleConfig` for purity tests."""
    per_channel_caps = MappingProxyType(
        {
            ChannelName("coordinate"): FactorValue(0.9),
            ChannelName("charge"): FactorValue(0.9),
            ChannelName("raw_pair"): FactorValue(0.9),
            ChannelName("projected_pair"): FactorValue(0.9),
        }
    )
    floors = MappingProxyType(
        {
            ChannelName("coordinate"): FactorValue(0.05),
            ChannelName("charge"): FactorValue(0.05),
            ChannelName("raw_pair"): FactorValue(0.05),
            ChannelName("projected_pair"): FactorValue(0.05),
        }
    )
    deltas = MappingProxyType(
        {
            ChannelName("coordinate"): FactorValue(0.2),
            ChannelName("charge"): FactorValue(0.2),
            ChannelName("raw_pair"): FactorValue(0.2),
            ChannelName("projected_pair"): FactorValue(0.2),
        }
    )
    return CosineScheduleConfig(
        schedule_family=schedule_family,  # type: ignore[arg-type]
        cycle_length=int(cycle_length),
        n_min=FactorValue(float(n_min)),
        n_max=FactorValue(float(n_max)),
        per_channel_caps=per_channel_caps,
        fresh_noise_floor_by_channel=floors,
        symmetric_delta_caps_by_channel=deltas,
        restart_triggers_allowed=("tail_budget_violation",),
        config_hash=ArtifactHash("purity-test-config-hash"),
        frozen_before_evaluation=True,
    )


def _make_sampler(*, cycle_length: int = 4) -> CosineScheduleSampler:
    """Build a sampler whose ``last_sample`` is a known baseline."""
    sampler = CosineScheduleSampler(_make_config(cycle_length=cycle_length))
    sampler.sample(
        outer_cycle_id=0,
        round_in_cycle=cycle_length - 1,  # end of cycle 0 (n_min side)
        target_round=3,
    )
    return sampler


def _restart_args() -> dict:
    """Return the keyword args for a canonical restart call."""
    return {
        "trigger_code": "tail_budget_violation",  # type: ignore[arg-type]
        "outer_cycle_id_old": 0,
        "outer_cycle_id_new": 1,
        "discarded_bundle_ids": (BundleId("bundle-old-0"), BundleId("bundle-old-1")),
        "trigger_metric_snapshot": MappingProxyType({"tail_score": 0.42}),
        "unresolved_metric_deficit": MappingProxyType({"q90": 0.1}),
    }


# ---------------------------------------------------------------------------
# compute_restart_event purity
# ---------------------------------------------------------------------------


def test_compute_restart_event_does_not_mutate() -> None:
    """Two consecutive ``compute_restart_event`` calls with identical
    arguments must not mutate ``sampler.last_sample`` (BEFORE state on
    both calls). This pins the gap B1 fix: the mutating boundary is
    pushed out of the compute path.
    """
    sampler = _make_sampler()
    baseline = sampler.last_sample
    assert baseline is not None  # sanity: _make_sampler primes the cache

    args = _restart_args()
    event1 = sampler.compute_restart_event(**args)
    event2 = sampler.compute_restart_event(**args)

    # The cache is untouched.
    assert sampler.last_sample is baseline
    assert sampler.last_sample is not None
    assert sampler.last_sample.outer_cycle_id == baseline.outer_cycle_id
    assert sampler.last_sample.round_in_cycle == baseline.round_in_cycle
    assert sampler.last_sample.n_cap == baseline.n_cap

    # noise_capacity_before is the same on both calls (read from baseline).
    assert event1.noise_capacity_before == baseline.n_cap
    assert event2.noise_capacity_before == baseline.n_cap

    # noise_capacity_after is also the same on both calls (deterministic
    # sample at (1, 0, recorded_at_round)).
    assert event1.noise_capacity_after == event2.noise_capacity_after

    # Sanity: events are structurally equal but distinct objects.
    assert event1 == event2
    assert event1 is not event2


def test_compute_restart_event_with_no_prior_sample_does_not_mutate() -> None:
    """When no sample has been taken yet, ``compute_restart_event`` must
    still not write ``self._last_sample``; it should leave it as ``None``
    and use the ``n_max`` fallback for ``noise_capacity_before``.
    """
    sampler = CosineScheduleSampler(_make_config())
    assert sampler.last_sample is None

    event = sampler.compute_restart_event(**_restart_args())

    assert sampler.last_sample is None  # still unset
    # n_max fallback: 0.9 for the default config.
    assert float(event.noise_capacity_before) == pytest.approx(0.9)
    # noise_capacity_after is the closed-form sample at (1, 0, *), which
    # is n_max for every closed-form family.
    assert float(event.noise_capacity_after) == pytest.approx(0.9)


def test_compute_restart_event_embeds_after_sample_on_event() -> None:
    """The after-sample must be embedded on the returned event so a
    later :meth:`record_restart_event` call can commit it. The
    embedding is via a private ``_after_sample`` attribute on the
    (frozen) event dataclass.
    """
    sampler = _make_sampler()
    event = sampler.compute_restart_event(**_restart_args())

    embedded = getattr(event, "_after_sample", None)
    assert embedded is not None
    assert embedded.outer_cycle_id == 1
    assert embedded.round_in_cycle == 0
    assert embedded.n_cap == event.noise_capacity_after

    # The cache must still be the BEFORE baseline.
    assert sampler.last_sample is not None
    assert sampler.last_sample.outer_cycle_id == 0


def test_compute_restart_event_rejects_unknown_trigger_code() -> None:
    """The trigger-code validation must run before any side effect."""
    sampler = _make_sampler()
    baseline = sampler.last_sample
    args = _restart_args()
    args["trigger_code"] = "not_a_real_code"  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        sampler.compute_restart_event(**args)

    # No side effect on rejection.
    assert sampler.last_sample is baseline


def test_compute_restart_event_rejects_non_int_cycle_ids() -> None:
    """Cycle-id coercion must run before any side effect."""
    sampler = _make_sampler()
    baseline = sampler.last_sample
    args = _restart_args()
    args["outer_cycle_id_old"] = -1  # invalid

    with pytest.raises(ValueError):
        sampler.compute_restart_event(**args)

    assert sampler.last_sample is baseline


# ---------------------------------------------------------------------------
# record_restart_event mutation boundary
# ---------------------------------------------------------------------------


def test_record_restart_event_writes_last_sample() -> None:
    """After :meth:`record_restart_event`, ``sampler.last_sample`` must
    equal the after-sample embedded in the event.
    """
    sampler = _make_sampler()
    baseline = sampler.last_sample
    assert baseline is not None

    event = sampler.compute_restart_event(**_restart_args())
    assert sampler.last_sample is baseline  # still BEFORE

    sampler.record_restart_event(event)

    # The cache now points at the embedded after-sample.
    assert sampler.last_sample is event._after_sample  # type: ignore[attr-defined]
    assert sampler.last_sample is not baseline
    assert sampler.last_sample is not None
    assert sampler.last_sample.outer_cycle_id == 1
    assert sampler.last_sample.round_in_cycle == 0
    assert sampler.last_sample.n_cap == event.noise_capacity_after


def test_record_restart_event_is_idempotent() -> None:
    """Calling :meth:`record_restart_event` twice with the same event
    must leave ``self._last_sample`` equal to the embedded sample on
    both invocations.
    """
    sampler = _make_sampler()
    event = sampler.compute_restart_event(**_restart_args())

    sampler.record_restart_event(event)
    first = sampler.last_sample
    assert first is event._after_sample  # type: ignore[attr-defined]

    sampler.record_restart_event(event)
    second = sampler.last_sample
    assert second is first  # same object identity
    assert second is event._after_sample  # type: ignore[attr-defined]


def test_record_restart_event_rejects_untrusted_event() -> None:
    """An event not produced by :meth:`compute_restart_event` must be
    rejected so a stray caller cannot silently overwrite the cache.
    """
    sampler = _make_sampler()
    baseline = sampler.last_sample
    assert baseline is not None

    # Construct an event that lacks the private _after_sample attribute.
    raw_event = RestartTriggerEvent(
        trigger_id=TriggerId("trigger-raw"),
        outer_cycle_id_old=0,
        outer_cycle_id_new=1,
        trigger_code=RestartTriggerCode("tail_budget_violation"),
        trigger_metric_snapshot={"metric": 0.0},
        discarded_source_bundle_ids=(BundleId("b0"),),
        noise_capacity_before=FactorValue(0.5),
        noise_capacity_after=FactorValue(0.9),
        unresolved_metric_deficit={},
        provenance=ProvenanceChain(()),
        recorded_at_round=1,
    )

    with pytest.raises(ValueError):
        sampler.record_restart_event(raw_event)

    # Cache untouched.
    assert sampler.last_sample is baseline


# ---------------------------------------------------------------------------
# Legacy wrapper still behaves like before
# ---------------------------------------------------------------------------


def test_legacy_restart_trigger_event_still_mutates() -> None:
    """The back-compat ``restart_trigger_event`` wrapper must preserve
    the original single-call semantics: it computes AND commits, so
    ``last_sample`` advances to the after-sample on a single call.
    """
    sampler = _make_sampler()
    baseline = sampler.last_sample
    assert baseline is not None

    event = sampler.restart_trigger_event(**_restart_args())

    # Legacy wrapper must update the cache (this is the behavior callers
    # of the old API rely on).
    assert sampler.last_sample is not baseline
    assert sampler.last_sample is event._after_sample  # type: ignore[attr-defined]
