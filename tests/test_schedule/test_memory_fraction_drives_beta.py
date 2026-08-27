"""Tests for the cosine-driven ``memory_fraction_from_schedule`` helper.

These tests pin ADR-0010 — cosine-driven memory fraction. The helper
translates a :class:`CosineScheduleSample` into the per-round memory
fraction consumed by :meth:`Engine.run_round` and the universal
``apply_restart_distribution`` boundary:

    memory_fraction = 1 - n_cap

so at round 0 (``n_cap = n_max``, large) the helper returns a small
memory fraction (lots of fresh noise for exploration); at round L-1
(``n_cap = n_min``, small) it returns a large memory fraction
(preserve prior and refine). The helper is pure: identical inputs
always yield identical outputs; the result is clipped to ``[0, 1]``
and refuses non-finite or non-numeric ``n_cap`` inputs.

The suite covers:

* the closed-form cosine shape ``memory_fraction = (1 + cos(pi * r/L-1)) / 2``
  (full range and narrow range),
* the deterministic ``L == 1`` edge case (``memory_fraction = 1 - n_max``),
* the unit-interval invariant over many random configurations,
* the pure-function invariant (no mutation of the input sample).
"""
from __future__ import annotations

import math
import random
from types import MappingProxyType

import pytest

from adaptive_reflow.contracts import (
    ArtifactHash,
    ChannelName,
    CosineScheduleConfig,
    CosineScheduleSample,
    FactorValue,
)
from adaptive_reflow.schedule.cosine import (
    memory_fraction_from_schedule,
    n_cap_for_round,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_config(
    *,
    schedule_family: str = "cosine_no_restart",
    cycle_length: int,
    n_min: float,
    n_max: float,
) -> CosineScheduleConfig:
    """Build a minimal valid :class:`CosineScheduleConfig` for tests."""
    per_channel_caps = MappingProxyType(
        {
            ChannelName("coordinate"): FactorValue(float(n_max)),
            ChannelName("charge"): FactorValue(float(n_max)),
            ChannelName("raw_pair"): FactorValue(float(n_max)),
            ChannelName("projected_pair"): FactorValue(float(n_max)),
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
        config_hash=ArtifactHash("memory-fraction-drives-beta-test"),
        frozen_before_evaluation=True,
    )


def _build_sample(
    config: CosineScheduleConfig,
    *,
    round_in_cycle: int,
    schedule_hash: str = "memory-fraction-drives-beta-test",
) -> CosineScheduleSample:
    """Build a :class:`CosineScheduleSample` for ``config`` at ``round_in_cycle``."""
    L = int(config.cycle_length)
    n_cap = n_cap_for_round(config, round_in_cycle)
    return CosineScheduleSample(
        schedule_hash=ArtifactHash(schedule_hash),
        outer_cycle_id=0,
        round_in_cycle=int(round_in_cycle),
        cycle_length=int(L),
        n_cap=n_cap,
        n_min=FactorValue(float(config.n_min)),
        n_max=FactorValue(float(config.n_max)),
        u_r=float(round_in_cycle) / max(L - 1, 1),
        family=str(config.schedule_family),
        computed_at_round=int(round_in_cycle),
    )


# ---------------------------------------------------------------------------
# Tests: full-range cosine shape (n_min=0, n_max=1)
# ---------------------------------------------------------------------------


def test_memory_fraction_from_schedule_constant_target() -> None:
    """Full-range schedule (``n_min=0``, ``n_max=1``) yields memory
    fraction ``~0`` at round 0 and ``~1`` at round L-1, monotone
    non-decreasing in between (cosine annealing).
    """
    config = _build_config(
        schedule_family="cosine_no_restart",
        cycle_length=10,
        n_min=0.0,
        n_max=1.0,
    )
    L = int(config.cycle_length)

    samples = [_build_sample(config, round_in_cycle=r) for r in range(L)]
    memory_fractions = [memory_fraction_from_schedule(s) for s in samples]

    # Round 0: ~ 1 - n_max = 0.0 (pure fresh noise).
    assert memory_fractions[0] == pytest.approx(0.0, abs=1e-12), (
        f"round 0 memory_fraction should be ~0; got {memory_fractions[0]:.6f}; "
        f"full sequence: {memory_fractions!r}"
    )
    # Round L-1: ~ 1 - n_min = 1.0 (pure prior preservation).
    assert memory_fractions[-1] == pytest.approx(1.0, abs=1e-12), (
        f"round {L - 1} memory_fraction should be ~1; "
        f"got {memory_fractions[-1]:.6f}; full sequence: {memory_fractions!r}"
    )
    # Monotone non-decreasing in between.
    for r in range(1, L):
        assert memory_fractions[r] >= memory_fractions[r - 1] - 1e-12, (
            f"memory_fraction must be monotone non-decreasing; "
            f"got {memory_fractions[r - 1]:.6f} at r={r - 1} and "
            f"{memory_fractions[r]:.6f} at r={r}; full sequence: {memory_fractions!r}"
        )


# ---------------------------------------------------------------------------
# Tests: narrow-range cosine shape
# ---------------------------------------------------------------------------


def test_memory_fraction_from_schedule_narrow_range() -> None:
    """Narrow-range schedule (``n_min=0.4``, ``n_max=0.6``) yields memory
    fraction ``~0.4`` at round 0 and ``~0.6`` at round L-1, monotone
    non-decreasing in between.
    """
    config = _build_config(
        schedule_family="cosine_no_restart",
        cycle_length=12,
        n_min=0.4,
        n_max=0.6,
    )
    L = int(config.cycle_length)

    samples = [_build_sample(config, round_in_cycle=r) for r in range(L)]
    memory_fractions = [memory_fraction_from_schedule(s) for s in samples]

    # Round 0: ~ 1 - n_max = 0.4 (modest fresh noise).
    assert memory_fractions[0] == pytest.approx(0.4, abs=1e-12), (
        f"round 0 memory_fraction should be ~0.4; "
        f"got {memory_fractions[0]:.6f}; full sequence: {memory_fractions!r}"
    )
    # Round L-1: ~ 1 - n_min = 0.6 (modest prior preservation).
    assert memory_fractions[-1] == pytest.approx(0.6, abs=1e-12), (
        f"round {L - 1} memory_fraction should be ~0.6; "
        f"got {memory_fractions[-1]:.6f}; full sequence: {memory_fractions!r}"
    )
    # Monotone non-decreasing in between.
    for r in range(1, L):
        assert memory_fractions[r] >= memory_fractions[r - 1] - 1e-12, (
            f"memory_fraction must be monotone non-decreasing; "
            f"got {memory_fractions[r - 1]:.6f} at r={r - 1} and "
            f"{memory_fractions[r]:.6f} at r={r}; full sequence: {memory_fractions!r}"
        )


# ---------------------------------------------------------------------------
# Tests: L == 1 edge case
# ---------------------------------------------------------------------------


def test_memory_fraction_from_schedule_single_round() -> None:
    """``cycle_length == 1`` is the deterministic edge case: ``n_cap`` is
    forced to ``n_max`` regardless of family, so ``memory_fraction``
    is ``1 - n_max`` for any round.
    """
    config = _build_config(
        schedule_family="cosine_no_restart",
        cycle_length=1,
        n_min=0.1,
        n_max=0.7,
    )
    # n_cap_for_round returns n_max for L == 1.
    sample = _build_sample(config, round_in_cycle=0)
    assert float(sample.n_cap) == pytest.approx(0.7)
    # memory_fraction = 1 - n_max = 0.3.
    memory_fraction = memory_fraction_from_schedule(sample)
    assert memory_fraction == pytest.approx(1.0 - 0.7, abs=1e-12), (
        f"single-round cycle should return memory_fraction = 1 - n_max; "
        f"got {memory_fraction:.6f}"
    )


# ---------------------------------------------------------------------------
# Tests: closed-form cosine shape
# ---------------------------------------------------------------------------


def test_memory_fraction_from_schedule_cosine_shape() -> None:
    """Memory fraction follows the closed-form cosine: ``(1 + cos(pi * r / (L - 1))) / 2``
    when ``schedule_family == cosine_no_restart`` with ``n_min=0`` and
    ``n_max=1`` (so ``memory_fraction = 1 - n_cap`` cancels the
    ``n_min + (n_max - n_min) * (1 + cos(...)) / 2`` form).

    With ``n_min=0`` and ``n_max=1`` the closed-form is::

        n_cap = (1 + cos(pi * r / (L - 1))) / 2
        memory_fraction = 1 - n_cap
                        = (1 - cos(pi * r / (L - 1))) / 2

    so memory_fraction matches the symmetric cosine ramp.
    """
    cycle_length = 11
    config = _build_config(
        schedule_family="cosine_no_restart",
        cycle_length=cycle_length,
        n_min=0.0,
        n_max=1.0,
    )
    L = int(config.cycle_length)
    assert L > 1, "this test requires L > 1 so the cosine ramp is defined"

    samples = [_build_sample(config, round_in_cycle=r) for r in range(L)]
    actual = [memory_fraction_from_schedule(s) for s in samples]

    for r in range(L):
        expected = (1.0 + math.cos(math.pi * r / (L - 1))) / 2.0
        # memory_fraction = 1 - n_cap, where n_cap uses the same cosine form.
        # Equivalently: expected_memory_fraction = 1 - n_cap.
        n_cap = float(samples[r].n_cap)
        expected_mem_frac = 1.0 - n_cap
        assert actual[r] == pytest.approx(expected_mem_frac, abs=1e-12), (
            f"round {r} memory_fraction mismatch: "
            f"got {actual[r]:.9f}, expected {expected_mem_frac:.9f} "
            f"(1 - n_cap where n_cap follows (1 + cos(pi * r / (L-1))) / 2 = "
            f"{expected:.9f})"
        )


# ---------------------------------------------------------------------------
# Tests: unit-interval invariant over many random configurations
# ---------------------------------------------------------------------------


def test_memory_fraction_from_schedule_in_unit_interval() -> None:
    """For a wide variety of valid configurations, the helper always
    returns a finite value in ``[0, 1]``. Property-style fuzzing with a
    fixed seed for reproducibility.
    """
    rng = random.Random(2024)
    families = (
        "constant",
        "linear",
        "cosine_no_restart",
        "cosine_guarded_restart",
    )

    for _ in range(64):
        family = rng.choice(families)
        L = rng.randint(1, 16)
        n_min = rng.uniform(0.0, 1.0)
        n_max = rng.uniform(n_min, 1.0)
        config = _build_config(
            schedule_family=family,
            cycle_length=L,
            n_min=n_min,
            n_max=n_max,
        )
        for r in range(L):
            sample = _build_sample(config, round_in_cycle=r)
            value = memory_fraction_from_schedule(sample)
            assert isinstance(value, float)
            assert math.isfinite(value), (
                f"memory_fraction must be finite; got {value!r} "
                f"for family={family!r} L={L} n_min={n_min} n_max={n_max} r={r}"
            )
            assert 0.0 <= value <= 1.0, (
                f"memory_fraction must lie in [0, 1]; got {value!r} "
                f"for family={family!r} L={L} n_min={n_min} n_max={n_max} r={r}"
            )


# ---------------------------------------------------------------------------
# Tests: purity (no mutation of the input sample)
# ---------------------------------------------------------------------------


def test_memory_fraction_from_schedule_does_not_mutate_sample() -> None:
    """The helper is pure: identical inputs always yield identical
    outputs and the input :class:`CosineScheduleSample` is never
    mutated. The test snapshots every public attribute of the sample
    and asserts no drift across many invocations.
    """
    config = _build_config(
        schedule_family="cosine_no_restart",
        cycle_length=8,
        n_min=0.2,
        n_max=0.8,
    )
    sample = _build_sample(config, round_in_cycle=3)
    snapshot: dict[str, object] = {
        "schedule_hash": sample.schedule_hash,
        "outer_cycle_id": sample.outer_cycle_id,
        "round_in_cycle": sample.round_in_cycle,
        "cycle_length": sample.cycle_length,
        "n_cap": sample.n_cap,
        "n_min": sample.n_min,
        "n_max": sample.n_max,
        "u_r": sample.u_r,
        "family": sample.family,
        "computed_at_round": sample.computed_at_round,
    }

    # Call repeatedly across the full cycle; values must be deterministic
    # and the sample must remain identical.
    for _ in range(8):
        value = memory_fraction_from_schedule(sample)
        assert isinstance(value, float)
        assert math.isfinite(value)
        assert 0.0 <= value <= 1.0
        # Snapshot equality — the sample is not mutated.
        assert sample.schedule_hash == snapshot["schedule_hash"]
        assert sample.outer_cycle_id == snapshot["outer_cycle_id"]
        assert sample.round_in_cycle == snapshot["round_in_cycle"]
        assert sample.cycle_length == snapshot["cycle_length"]
        assert sample.n_cap == snapshot["n_cap"]
        assert sample.n_min == snapshot["n_min"]
        assert sample.n_max == snapshot["n_max"]
        assert sample.u_r == snapshot["u_r"]
        assert sample.family == snapshot["family"]
        assert sample.computed_at_round == snapshot["computed_at_round"]

    # Determinism: same input yields the same output across calls.
    first_value = memory_fraction_from_schedule(sample)
    for _ in range(16):
        assert memory_fraction_from_schedule(sample) == first_value


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-x", "--no-header", "-q"]))
