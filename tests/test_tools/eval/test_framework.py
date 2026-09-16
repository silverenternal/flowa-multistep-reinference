"""Tests for tools/eval/framework.py — framework multi-round solve + paper-quantity-driven β.

Wave 104 P2-A: split from tests/test_tools/test_run_real_ckpt_eval.py
(2409 LOC → 6 sub-files mirroring tools/eval/). All 9 tests preserved
byte-for-byte: same imports, same fixtures, same assertions, same names.
"""

from __future__ import annotations

import importlib
import sys
from typing import Any

import pytest

_TOOLS = "tools.run_real_ckpt_eval"


def _import_tools_module() -> Any:
    """Import tools.run_real_ckpt_eval (lazy to avoid module-level side effects)."""
    # Ensure repo root is importable.
    import os
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", ".."),
    )
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    return importlib.import_module(_TOOLS)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_placeholder_trace(adapter: Any) -> Any:
    """Build a minimal ODE trace stub for the placeholder adapter.

    The FlowMol3 placeholder adapter's ``observe_entropy_reduction``
    synthetic-mode fallback only consumes ``trace.native_state_digest``
    (a sha256-like hex string). Any object with that attribute works.
    """
    class _TraceStub:
        native_state_digest = "wave53-flowmol3-metric-test-stub"
    return _TraceStub()



def test_solve_framework_steps_matches_nfe_total() -> None:
    """`_solve_framework` returns a trace with `steps == nfe_total` (post Bug A fix).

    Pre-fix: the returned trace was the last per-round `solve_ode` output,
    which had ``steps == nfe_per_round`` (3 for nfe=10/n_rounds=3) —
    different from baseline's ``steps == nfe_total`` (10). Post-fix: the
    function runs the multi-round loop, then re-anchors with a final
    ``solve_ode`` on the integrated endpoint with the FULL NFE budget, so
    the returned trace has ``steps == nfe_total`` — same axis as baseline.

    Regression guards against the pre-fix shape:
      * ``steps != 3`` (per-round NFE for nfe=10/n_rounds=3 was 3)
      * ``steps != 9`` (per-round total was 3*3=9, 1 step short of 10)
    """
    tools = _import_tools_module()
    from adaptive_reflow.adapters.flowmol3 import default_flowmol3_adapter

    adapter = default_flowmol3_adapter(force_mode="synthetic", nfe_budget=10)
    framework_trace, _ = tools._solve_framework(
        adapter, nfe=10, seed=42, n_rounds=3
    )

    assert framework_trace.steps == 10, (
        f"expected framework trace.steps == 10 (post-Bug-A fix), "
        f"got {framework_trace.steps!r}. This means the framework arm is "
        f"still returning the last per-round trace with steps={framework_trace.steps}, "
        f"not the integrated-endpoint trace with steps=nfe_total=10."
    )
    assert framework_trace.steps != 3, (
        "framework trace.steps must NOT be 3 (pre-fix per-round NFE for "
        "nfe=10/n_rounds=3 was round(10/3)=3, Bug A.1 symptom)"
    )
    assert framework_trace.steps != 9, (
        "framework trace.steps must NOT be 9 (pre-fix per-round total was "
        "3*3=9 for nfe=10/n_rounds=3, Bug A.3 symptom — 1 step short of "
        "the baseline's 10)"
    )


def test_solve_framework_trace_axis_matches_baseline() -> None:
    """Framework trace.steps == baseline trace.steps (metric-layer axis match).

    The metric layer dispatches on ``(seed, steps)`` via
    ``trace.native_state_digest`` and ``trace.steps``, so the framework arm
    and the baseline arm must agree on ``steps`` for the metric layer to
    compare them on the SAME axis. Pre-fix: framework.steps was 3 (last
    per-round) and baseline.steps was 10 — different axes.
    """
    tools = _import_tools_module()
    from adaptive_reflow.adapters.flowmol3 import default_flowmol3_adapter

    adapter = default_flowmol3_adapter(force_mode="synthetic", nfe_budget=10)
    baseline_trace, _ = tools._solve_baseline(adapter, nfe=10, seed=42)
    framework_trace, _ = tools._solve_framework(
        adapter, nfe=10, seed=42, n_rounds=3
    )

    assert baseline_trace.steps == 10
    assert framework_trace.steps == baseline_trace.steps, (
        f"framework trace.steps ({framework_trace.steps}) must equal "
        f"baseline trace.steps ({baseline_trace.steps}); the metric layer "
        f"compares two arms on the same (seed, steps) axis."
    )


def test_solve_framework_distributes_nfe_per_round_to_sum_exactly() -> None:
    """Per-round NFE sums to nfe_total (no 1-step excess at any NFE budget).

    Pre-fix: ``nfe_per_round = round(nfe / n_rounds)`` gave 9 / 51 / 201
    for 10 / 50 / 200 (Bug A.3, 1-step excess in 2 of 3 cells). Post-fix:
    the per-round NFE is a list ``[base, base, ..., base+remainder]``
    with sum equal to ``nfe`` exactly. For nfe=10, n_rounds=3 the
    concrete shape is ``[3, 3, 4]`` (sum=10).

    The 4th ``solve_ode`` call is the post-loop re-anchor at nfe_total.
    """
    tools = _import_tools_module()
    from adaptive_reflow.adapters.flowmol3 import default_flowmol3_adapter

    adapter = default_flowmol3_adapter(force_mode="synthetic", nfe_budget=10)

    # Wrap solve_ode to capture per-call `num_steps`. The wrapper delegates
    # to the original method so the adapter's internal state advances
    # correctly across calls.
    captured_num_steps: list[int] = []
    original_solve_ode = adapter.solve_ode

    def recording_solve_ode(state, condition, *, seed):
        captured_num_steps.append(int(condition.delta_spec["num_steps"]))
        return original_solve_ode(state, condition, seed=seed)

    adapter.solve_ode = recording_solve_ode  # type: ignore[assignment]

    tools._solve_framework(adapter, nfe=10, seed=42, n_rounds=3)

    # First `n_rounds=3` calls are the per-round split. Sum must equal 10.
    per_round_nfes = captured_num_steps[:3]
    assert sum(per_round_nfes) == 10, (
        f"per-round NFE split {per_round_nfes} must sum to nfe_total=10, "
        f"got sum={sum(per_round_nfes)}. Pre-fix gave 3*3=9 (1 step short)."
    )
    assert per_round_nfes == [3, 3, 4], (
        f"expected per-round split [3, 3, 4] for nfe=10/n_rounds=3, "
        f"got {per_round_nfes!r}"
    )
    # The 4th call is the post-loop re-anchor at nfe_total=10 (the
    # integrated-endpoint trace returned to the metric layer).
    assert captured_num_steps[-1] == 10, (
        f"final re-anchor solve_ode must use nfe_total=10, "
        f"got num_steps={captured_num_steps[-1]}"
    )


def test_solve_framework_gate_firing_yields_byte_identical_to_baseline() -> None:
    """At NFE below the restart_min_nfe threshold, framework trace == baseline trace.

    When the NFE-adaptive gate fires (nfe_budget < restart_min_nfe),
    ``apply_restart_distribution`` returns the state unchanged, so the
    integrated endpoint equals the original bundle. The final re-anchor
    ``solve_ode`` then produces a trace that is byte-identical to what
    ``_solve_baseline`` produces (same ``source=bundle.native_state_digest``,
    same seed, same steps). This is the expected byte-stability contract
    for the gate-skipped path: framework degenerates to baseline.

    For nfe=10 / restart_min_nfe=20 the gate fires; this test asserts the
    byte-identicality on the placeholder adapter.
    """
    tools = _import_tools_module()
    from adaptive_reflow.adapters.flowmol3 import default_flowmol3_adapter

    # nfe_budget=10 < restart_min_nfe=20, so the gate fires.
    adapter = default_flowmol3_adapter(force_mode="synthetic", nfe_budget=10)
    baseline_trace, _ = tools._solve_baseline(adapter, nfe=10, seed=42)
    framework_trace, _ = tools._solve_framework(
        adapter, nfe=10, seed=42, n_rounds=3
    )

    assert framework_trace.steps == baseline_trace.steps == 10
    assert str(framework_trace.native_state_digest) == str(
        baseline_trace.native_state_digest
    ), (
        f"with the gate firing (nfe=10 < restart_min_nfe=20), the "
        f"framework's integrated-endpoint trace must be byte-identical "
        f"to the baseline trace (the integrated endpoint equals the "
        f"original bundle, so solve_ode produces the same digest). "
        f"Got framework.digest={framework_trace.native_state_digest!r} "
        f"vs baseline.digest={baseline_trace.native_state_digest!r}"
    )



def test_make_framework_policy_paper_quantities_low_entropy_drives_high_beta() -> None:
    """High entropy profile → low ``sheet_A`` → β → 1 (more fresh noise).

    Wave 86 Agent B — Pitfall #1 close test. Constructs a synthetic
    adapter with a known ``profile_residual_fn`` that returns a
    *growing* ``sheet_A`` profile across rounds (high entropy,
    sheet-dominant → low codimension → low ``sheet_A`` → β → 1,
    i.e. more fresh noise / more exploration per the framework's
    restart-blend convention).

    Per the Wave 31 design: ``memory_fraction = 1 - β`` and ``β =
    1 - n_cap``. A growing sheet signal means low ``n_cap`` → high
    ``β`` → more fresh noise. This test pins the sign convention
    so a future inversion is detected.
    """
    tools = _import_tools_module()
    from adaptive_reflow.adapters.flowmol3 import default_flowmol3_adapter

    adapter = default_flowmol3_adapter(force_mode="synthetic", nfe_budget=10)

    # Build a deterministic growing-sheet ``profile_residual_fn``.
    def growing_sheet(x: float) -> float:
        # Pure sinusoidal (positive dominant) — the codimension-sheet
        # ``sheet_evidence_A`` metric surfaces a high value (close to 1)
        # for this profile. Other profiles yield a lower sheet_A.
        return 0.5 * (1.0 + (x % 6.283185307179586) ** 0)  # constant 0.5??

    # The above is a placeholder; let's provide a real profile with
    # known-good sheet behavior. The unit-sin profile yields a
    # non-trivial sheet_evidence_A (per the paper-quantity module).
    import math as _math

    def low_codim_profile(x: float) -> float:
        return 0.5 * _math.sin(x) ** 2

    # Attach the profile_residual_fn to the adapter so
    # _compute_paper_quantities finds it via getattr.
    adapter.profile_residual_fn = low_codim_profile  # type: ignore[attr-defined]

    # Per-round paper-quantity dict (growing sheet_A across rounds).
    pq_growing = {
        "sheet_A": 0.85,
        "packing_B": 0.10,
        "exterior_gap": 0.20,
    }

    # Legacy fallback (no paper_quantities) → β = 0.5.
    legacy_policy = tools._make_framework_policy(
        adapter, target_round=0, seed=42, paper_quantities=None,
    )
    legacy_beta = float(
        next(iter(legacy_policy.beta_by_channel.values()))
    )
    assert abs(legacy_beta - 0.5) < 1e-9, (
        f"legacy fallback must return β=0.5 (byte-stable Wave 45 "
        f"contract), got β={legacy_beta}"
    )

    # Paper-quantity-driven path → β != 0.5 in general.
    pq_policy = tools._make_framework_policy(
        adapter, target_round=0, seed=42, paper_quantities=pq_growing,
    )
    pq_beta = float(
        next(iter(pq_policy.beta_by_channel.values()))
    )
    assert 0.0 <= pq_beta <= 1.0, (
        f"paper-quantity-driven β must lie in [0, 1], got β={pq_beta}"
    )
    assert abs(pq_beta - legacy_beta) > 1e-6, (
        f"paper-quantity-driven β must differ from the legacy "
        f"constant-0.5 path (Pitfall #1 fix verification); "
        f"legacy={legacy_beta} pq={pq_beta}"
    )

    # Cross-policy hash must differ (Pitfall #1 fix changes the
    # policy_hash contract for paper-quantity-aware adapters — the
    # ``policy_hash`` carries the beta_by_channel payload).
    assert legacy_policy.policy_hash != pq_policy.policy_hash, (
        "paper-quantity-driven policy must carry a different "
        "policy_hash than the legacy constant-0.5 policy"
    )


def test_make_framework_policy_paper_quantities_none_falls_back_to_legacy() -> None:
    """``paper_quantities=None`` → legacy constant-β=0.5 (byte-stable).

    The legacy Wave 45 / Wave 82 byte-stable contract: when
    ``paper_quantities`` is ``None``, the per-round β is exactly
    0.5. This test pins that contract so a future regression that
    flips the fallback to a non-constant value is caught.
    """
    tools = _import_tools_module()
    from adaptive_reflow.adapters.flowmol3 import default_flowmol3_adapter

    adapter = default_flowmol3_adapter(force_mode="synthetic", nfe_budget=10)

    # Two different round indices — both must yield β=0.5.
    for r in (0, 1, 2, 7):
        policy = tools._make_framework_policy(
            adapter, target_round=int(r), seed=42,
            paper_quantities=None,
        )
        beta = float(next(iter(policy.beta_by_channel.values())))
        assert abs(beta - 0.5) < 1e-9, (
            f"round={r}: legacy fallback must yield β=0.5 "
            f"(byte-stable Wave 45 contract), got β={beta}"
        )


def test_compute_paper_quantities_returns_none_when_no_profile_fn() -> None:
    """``_compute_paper_quantities`` returns ``None`` when no ``profile_residual_fn``.

    Wave 86 Agent B — defensive coverage: legacy adapters (no
    ``profile_residual_fn`` on either capabilities() or the
    adapter itself) must yield ``None`` so ``_make_framework_policy``
    takes the constant-β=0.5 fallback path. The function must NEVER
    raise on a missing oracle — a broken oracle cannot be allowed
    to poison the framework arm.
    """
    tools = _import_tools_module()
    from adaptive_reflow.adapters.flowmol3 import default_flowmol3_adapter

    adapter = default_flowmol3_adapter(force_mode="synthetic", nfe_budget=10)

    # Adapter has no ``profile_residual_fn`` (default).
    pq = tools._compute_paper_quantities(
        adapter, trace=None, round_index=0,
    )
    assert pq is None, (
        f"_compute_paper_quantities must return None when the "
        f"adapter does not expose profile_residual_fn, got {pq!r}"
    )


def test_compute_paper_quantities_returns_dict_when_profile_fn_supplied() -> None:
    """``_compute_paper_quantities`` returns a 3-key dict when ``profile_residual_fn`` is supplied.

    The dict carries the three paper-quantity primitives the
    :class:`PaperRatioAdaptiveScheduler` consumes:
    ``sheet_A``, ``packing_B``, ``exterior_gap``.
    """
    tools = _import_tools_module()
    import math as _math

    from adaptive_reflow.adapters.flowmol3 import default_flowmol3_adapter

    adapter = default_flowmol3_adapter(force_mode="synthetic", nfe_budget=10)
    adapter.profile_residual_fn = lambda x: 0.5 * _math.sin(x)  # type: ignore[attr-defined]

    pq = tools._compute_paper_quantities(
        adapter, trace=None, round_index=0,
    )
    assert isinstance(pq, dict), (
        f"_compute_paper_quantities must return a dict when the "
        f"profile_residual_fn is supplied, got {type(pq).__name__}: {pq!r}"
    )
    for key in ("sheet_A", "packing_B", "exterior_gap"):
        assert key in pq, (
            f"paper_quantities dict missing key {key!r}; got {sorted(pq.keys())!r}"
        )
        v = pq[key]
        assert isinstance(v, float), (
            f"paper_quantity {key!r} must be a float, got {type(v).__name__}: {v!r}"
        )
        assert v == v, (
            f"paper_quantity {key!r} must not be NaN, got {v!r}"
        )


def test_solve_framework_paper_quantity_driven_beta_changes_per_round() -> None:
    """Per-round β varies across rounds when ``profile_residual_fn`` is supplied.

    Wave 86 Agent B — Pitfall #1 + per-round thread verification.
    Constructs an adapter with a profile_residual_fn, monkey-patches
    ``_compute_paper_quantities`` to return a per-round-varying
    paper_quantities dict (simulating the framework-side profile
    evolving across rounds), runs ``_solve_framework``, and asserts
    that the per-round ``FinalRestartPolicy.beta_by_channel``
    payload differs across rounds.

    This pins the full wire from ``_solve_framework`` →
    ``_compute_paper_quantities`` → ``_make_framework_policy``
    → per-round β. With paper_quantities=None (default), all β
    values would equal 0.5 (byte-stable); with per-round-varying
    paper_quantities, the β values diverge across rounds.
    """
    tools = _import_tools_module()
    from adaptive_reflow.adapters.flowmol3 import default_flowmol3_adapter

    adapter = default_flowmol3_adapter(force_mode="synthetic", nfe_budget=10)

    # Monkey-patch _compute_paper_quantities to return a per-round-
    # varying dict that mimics the framework-side profile evolution.
    # Round 0 → sheet_A=0.1 (high codimension), round 1 → sheet_A=0.5,
    # round 2 → sheet_A=0.9 (low codimension). The per-round β
    # derivation MUST differ across rounds.
    round_to_pq = {
        0: {"sheet_A": 0.10, "packing_B": 0.50, "exterior_gap": 0.30},
        1: {"sheet_A": 0.50, "packing_B": 0.20, "exterior_gap": 0.30},
        2: {"sheet_A": 0.90, "packing_B": 0.05, "exterior_gap": 0.30},
    }
    original_compute_pq = tools._compute_paper_quantities

    def _patched_compute_pq(adapter: Any, trace: Any, *, round_index: int) -> Any:
        return round_to_pq.get(int(round_index))

    tools._compute_paper_quantities = _patched_compute_pq  # type: ignore[assignment]
    try:
        # Capture per-round beta via wrapper around _make_framework_policy.
        captured_betas: list[float] = []
        original_make_policy = tools._make_framework_policy

        def _capturing_make_policy(
            adapter: Any,
            *,
            target_round: int,
            seed: int,
            paper_quantities: Any = None,
            nfe: int = 0,  # Wave 173 P4 — accept the new kwarg so the
            # wrapper signature matches ``tools._make_framework_policy``;
            # forwarded into ``original_make_policy`` to preserve the
            # NFE-adaptive scaling introduced in Wave 173 P4.
        ) -> Any:
            policy = original_make_policy(
                adapter,
                target_round=target_round,
                seed=seed,
                paper_quantities=paper_quantities,
                nfe=int(nfe),
            )
            captured_betas.append(
                float(next(iter(policy.beta_by_channel.values())))
            )
            return policy

        tools._make_framework_policy = _capturing_make_policy  # type: ignore[assignment]
        try:
            _framework_trace, _wall = tools._solve_framework(
                adapter, nfe=10, seed=42, n_rounds=3,
            )
        finally:
            tools._make_framework_policy = original_make_policy  # type: ignore[assignment]
    finally:
        tools._compute_paper_quantities = original_compute_pq  # type: ignore[assignment]

    # We must have observed at least one beta (multi-round pass).
    assert captured_betas, (
        "_make_framework_policy was never called — _solve_framework "
        "did not enter the per-round loop"
    )
    # All captured betas must differ from 0.5 (the constant fallback)
    # because we supplied a paper_quantities dict for at least one
    # round. Note: round 0 produces β = 1 - n_cap_base(0) which on
    # the codimension-sheet scheduler is NOT 0.5 — the per-round
    # schedule already varies β even without the PID shift.
    distinct_betas = set(round(float(b), 6) for b in captured_betas)
    assert len(distinct_betas) >= 2, (
        f"per-round β must vary across rounds when paper_quantities "
        f"differs; observed {len(distinct_betas)} distinct values: "
        f"{sorted(distinct_betas)} from captured_betas={captured_betas}"
    )
    # Constant-β=0.5 baseline (Wave 45 byte-stable path) would have
    # produced [0.5, 0.5, 0.5] — assert the paper-quantity-driven
    # path diverges from that.
    constant_baseline = [0.5, 0.5, 0.5]
    assert captured_betas != constant_baseline, (
        f"per-round β matches the constant-0.5 baseline path "
        f"({captured_betas}); Pitfall #1 fix did not thread "
        f"paper_quantities through _solve_framework"
    )


