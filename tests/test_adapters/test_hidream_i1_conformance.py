"""Conformance tests for :class:`HiDreamI1Adapter` (Wave 104 P1-B split).

This file is the **conformance** partition of the original
``test_hidream_i1.py`` (771 LOC). It exercises the deeper protocol
contracts that smoke tests do not cover:

* conditioning cache reuse (same prompt → same cache key)
* batched inference shape + byte-determinism
* 20-round ``Engine.run_round`` stress loop

The smoke tests (capability handshake, build/solve/observe, validation
paths, per-variant defaults) live in :mod:`test_hidream_i1_smoke`.

The metrics file :mod:`test_hidream_i1_metrics` exists for symmetry but
has no HiDream-I1-specific paper-metric tests at this time.

Wave 104 P1-B: pure file-system refactor. NO test_* function is
deleted, renamed, or modified. The shared helpers live in
:mod:`_hidream_helpers` (leading underscore prevents pytest
discovery — it is import-only).
"""
from __future__ import annotations

import time

import numpy as np
from _hidream_helpers import (
    _make_condition_delta,
    _make_final_policy,
    _make_phase_state,
    _validate_round_trace,
    hidream_adapter,
)

# ---------------------------------------------------------------------------
# 17. Conditioning cache reuses the same prompt
# ---------------------------------------------------------------------------


def test_conditioning_cache_reuses_same_prompt(hidream_adapter: object) -> None:
    """Repeated calls with the same prompt hit the cache; distinct prompts miss."""
    bundle = hidream_adapter.build_initial_state(
        batch_id="batch-hidream-10", sample_id="sample-hidream-10",
    )
    # First call populates the cache.
    delta_a = _make_condition_delta(
        target_round=0, num_steps=2, prompt="a serene lake at dawn",
    )
    composed_a = hidream_adapter.compose_condition(bundle, delta_a)
    hash_a = str(composed_a.delta_spec["conditioning_cache_hash"])
    assert hash_a in hidream_adapter._conditioning_cache  # noqa: SLF001
    # Second call with the same prompt returns the same cache key.
    delta_a_again = _make_condition_delta(
        target_round=1, num_steps=2, prompt="a serene lake at dawn",
    )
    composed_a_again = hidream_adapter.compose_condition(bundle, delta_a_again)
    hash_a_again = str(composed_a_again.delta_spec["conditioning_cache_hash"])
    assert hash_a == hash_a_again
    # Different prompt produces a different cache key.
    delta_b = _make_condition_delta(
        target_round=2, num_steps=2, prompt="a bustling city street at night",
    )
    composed_b = hidream_adapter.compose_condition(bundle, delta_b)
    hash_b = str(composed_b.delta_spec["conditioning_cache_hash"])
    assert hash_a != hash_b


# ---------------------------------------------------------------------------
# 18. batched_inference shape + determinism
# ---------------------------------------------------------------------------


def test_batched_inference_shape_and_determinism(hidream_adapter: object) -> None:
    """``batched_inference`` returns ``(n, 16, 128, 128)`` and is byte-deterministic."""
    a1 = hidream_adapter.batched_inference(n_samples=4, num_steps=2, seed=0)
    a2 = hidream_adapter.batched_inference(n_samples=4, num_steps=2, seed=0)
    assert a1.shape == (4, 16, 128, 128)
    np.testing.assert_array_equal(a1, a2)
    assert np.all(np.isfinite(a1))
    assert np.max(np.abs(a1)) <= 6.0 + 1e-9


# ---------------------------------------------------------------------------
# 21. Engine stress — 20 rounds alternating beta
# ---------------------------------------------------------------------------


def test_engine_stress_20_rounds_with_restart(hidream_adapter: object) -> None:
    """``Engine.run_round`` drives 20 rounds alternating ``beta``; every trace validates."""
    from adaptive_reflow.frame import Engine

    engine = Engine()
    bundle = hidream_adapter.build_initial_state(
        batch_id="batch-hidream-13", sample_id="sample-hidream-13",
    )
    start = time.perf_counter()
    b = bundle
    for r in range(20):
        policy = _make_final_policy(
            policy_id=f"policy-hidream-13-{r}",
            run_id="run-hidream-13",
            beta=(0.5 if r % 2 == 0 else 0.0),
            target_round=r,
        )
        delta = _make_condition_delta(target_round=r, num_steps=2)
        composed = hidream_adapter.compose_condition(b, delta)
        result = engine.run_round(
            round_index=r,
            phase_state=_make_phase_state(),
            bundle=b,
            adapter=hidream_adapter,
            policy=policy,
            condition_delta=composed,
        )
        trace = result.round_trace
        ok, errs = _validate_round_trace(trace)
        assert ok, f"round {r} trace failed: {errs!r}"
        b = hidream_adapter.observe_endpoint(
            trace.integrator_trace,
            hidream_adapter.build_initial_state(
                batch_id="batch-hidream-13",
                sample_id="sample-hidream-13",
            ),
        )
    elapsed = time.perf_counter() - start
    # The synthetic 2-step Euler loop is cheap on CPU; 20 rounds must
    # finish in well under 60 seconds even on the slowest CI box.
    assert elapsed < 60.0, f"stress run blew budget: {elapsed:.1f}s"
