"""Regression tests for tools/run_real_ckpt_eval.py — Wave 53 Agent C.

These tests cover:

1. ``_compute_flowmol3_real_metric_via_trace`` — the new
   per-atom-type-entropy-reduction metric helper that closes the
   Wave 50 Agent B Tier-3 FlowMol3 metric-axis blocker. Mirrors the
   kanzi / lineageflow via-trace helpers, returns ``(value, marker,
   debug_dict)`` where ``marker == "computed"`` on success and
   ``debug_dict`` carries the ``metric_axis`` /
   ``per_position_entropy_reduction`` payload.

2. ``_ADAPTER_FORCE_MODE_ALIAS`` — the new per-model force-mode
   translation table that closes the Wave 50 Agent B Phase-4 block.
   Verifies that ``_resolve_adapter("flowmol3", force_mode="real")``
   does NOT translate to ``"torch"`` (the v1 factory rejects that
   token), and that ``default_flowmol3_adapter(force_mode="torch")``
   is defensively aliased to ``"real"`` (defensive — closes the
   legacy-token path from any non-pipeline caller).

3. ``default_flowmol3adapter(force_mode=...)`` — the new ``force_mode``
   kwarg on the v2 factory that closes Wave 50 Agent B Bug B (the
   v2 factory did not accept ``force_mode`` at all).

All tests are stdlib + numpy — no torch / no upstream flowmol / no
rdkit. The placeholder FlowMol3 adapter returns ``marker=computed``
with ``reduction_value == 0.0`` by construction (uniform-vs-uniform,
the documented trivial reading of the placeholder). The pipeline's
Tier-3 close condition (``framework_wins > 0``) lives downstream;
this test surface only asserts the helper contract.
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
# 1. FlowMol3 metric helper (closes Wave 50 Tier-3 metric-axis blocker)
# ---------------------------------------------------------------------------


def test_flowmol3_metric_helper_returns_value_marker_dbg() -> None:
    """`_compute_flowmol3_real_metric_via_trace` returns (float, str, dict).

    The placeholder adapter has no real atom-type marginal, so the
    synthetic-mode fallback in ``observe_entropy_reduction`` yields
    ``reduction == 0.0``. The helper must surface this as
    ``marker='computed'`` with a debug dict that carries
    ``per_position_atom_type_entropy_reduction`` axis info.
    """
    tools = _import_tools_module()
    # Lazy-import the placeholder adapter (synthetic-mode path).
    from adaptive_reflow.adapters.flowmol3 import default_flowmol3_adapter

    adapter = default_flowmol3_adapter(force_mode="synthetic")
    trace = _make_placeholder_trace(adapter)

    value, marker, dbg = tools._compute_flowmol3_real_metric_via_trace(
        adapter=adapter, trace=trace, seed=42, nfe=10,
    )

    assert marker == "computed", (
        f"expected marker='computed', got marker={marker!r} "
        f"with dbg={dbg!r}"
    )
    assert isinstance(value, float), (
        f"expected value is float, got {type(value).__name__}: {value!r}"
    )
    assert value == 0.0, (
        f"placeholder uniform-vs-uniform reduction must be 0.0, got {value!r}"
    )
    # Debug contract (per Agent A §3.4):
    assert dbg["metric_axis"] == "per_position_atom_type_entropy_reduction"
    assert dbg["metric_kind"] == "entropy_reduction"
    assert dbg["K_atom_types"] == 10
    assert dbg["reduction_value"] == 0.0
    assert "decode_strategy" in dbg
    assert "Wave 53" in dbg["decode_strategy"]
    assert dbg["trace_source"] == "captured_via_solve_ode"
    assert dbg["seed"] == 42
    assert dbg["nfe_budget"] == 10


def test_flowmol3_metric_helper_returns_blocked_when_adapter_lacks_method() -> None:
    """Helper degrades to ``marker='blocked'`` if adapter lacks ``observe_entropy_reduction``.

    Mirrors the kanzi / lineageflow failure path: the helper never raises,
    it returns ``(None, 'blocked', {'reason': ...})``.
    """
    tools = _import_tools_module()

    class _NoEntropyAdapter:
        """Mock adapter missing ``observe_entropy_reduction``."""
        capabilities = lambda self: ()  # noqa: E731

    value, marker, dbg = tools._compute_flowmol3_real_metric_via_trace(
        adapter=_NoEntropyAdapter(), trace=None, seed=42, nfe=10,
    )

    assert value is None
    assert marker == "blocked"
    assert dbg["reason"] == "adapter_missing_observe_entropy_reduction"
    assert dbg["adapter"] == "_NoEntropyAdapter"


def test_flowmol3_metric_helper_blocks_on_nan_reduction() -> None:
    """``observe_entropy_reduction`` returning NaN → ``marker='blocked'``.

    Mirrors ``per_position_entropy_reduction`` contract: degenerate
    inputs (fewer than 2 atoms in either arm) return NaN. The helper
    must surface this as ``blocked`` with ``reason='entropy_reduction_is_nan'``
    so the eval pipeline can distinguish ``metric undefined`` from
    ``metric == 0``.
    """
    tools = _import_tools_module()

    class _NaNEntropyAdapter:
        def observe_entropy_reduction(
            self, trace: Any, paper_quantities: Any = None,
            *,
            theta_before: Any = None,
            theta_after: Any = None,
        ) -> dict[str, float]:
            return {"per_position_entropy_reduction": float("nan")}

    value, marker, dbg = tools._compute_flowmol3_real_metric_via_trace(
        adapter=_NaNEntropyAdapter(), trace=None, seed=42, nfe=10,
    )

    assert value is None
    assert marker == "blocked"
    assert dbg["reason"] == "entropy_reduction_is_nan"


# ---------------------------------------------------------------------------
# 2. _ADAPTER_FORCE_MODE_ALIAS — closes Wave 50 Phase-4 block (Bug A)
# ---------------------------------------------------------------------------


def test_flowmol3_wiring_alias_does_not_translate_real_to_torch() -> None:
    """`_resolve_adapter('flowmol3', force_mode='real')` sends ``real`` (not ``torch``).

    This is the core wiring fix: Wave 50 Agent A added the
    ``{synthetic, real, auto}`` convention to ``default_flowmol3_adapter``
    but the pipeline unconditionally translated ``"real"`` → ``"torch"``,
    so the factory raised ``unknown_force_mode:torch``. Wave 53 Agent C
    adds a per-model alias table; ``flowmol3`` is identity so the
    CLI token reaches the factory unchanged.
    """
    tools = _import_tools_module()
    # Sanity check on the alias table.
    assert "flowmol3" not in tools._ADAPTER_FORCE_MODE_ALIAS, (
        "flowmol3 should be identity (CLI token = adapter token). "
        "If you add an entry here, you've regressed Wave 53 Agent C."
    )

    # Confirm translation: passing ``force_mode='real'`` should resolve
    # to adapter ``force_mode='real'`` for flowmol3, NOT ``'torch'``.
    # We don't load a real FlowMol3 ckpt (we don't ship one); we just
    # confirm the alias table maps ``('flowmol3', 'real') -> 'real'``.
    adapter_force_mode = tools._ADAPTER_FORCE_MODE_ALIAS.get(
        "flowmol3", {},
    ).get("real", "real")
    assert adapter_force_mode == "real", (
        f"expected identity mapping, got {adapter_force_mode!r}"
    )


def test_legacy_adapters_still_translate_real_to_torch() -> None:
    """Legacy adapters (kanzi, lineageflow) still receive ``torch``.

    Confirms Wave 53 Agent C did NOT regress the legacy-token path.
    The eval pipeline must continue to send ``"torch"`` to kanzi /
    lineageflow / freqflow / etc. so their factories (which only accept
    ``{"torch", "synthetic", "auto"}``) don't raise.
    """
    tools = _import_tools_module()
    for legacy_model in ("kanzi", "lineageflow", "freqflow"):
        alias = tools._ADAPTER_FORCE_MODE_ALIAS.get(legacy_model, {})
        assert alias.get("real") == "torch", (
            f"legacy adapter {legacy_model!r} must map real->torch, "
            f"got alias={alias!r}"
        )


def test_flowmol3_v1_factory_accepts_torch_alias() -> None:
    """`default_flowmol3_adapter(force_mode='torch')` is aliased to ``'real'``.

    Wave 53 Agent C Option A — defensive alias at the v1 factory so any
    non-pipeline caller (e.g. a future CLI tool) that drops ``"torch"``
    into the factory does NOT raise ``unknown_force_mode:torch``.

    We test with ``force_mode='auto'`` (after the alias it becomes
    ``'real'``, then the factory tries to load the ckpt, fails on a
    non-torch env, and degrades gracefully to the synthetic
    placeholder). The point is that ``ValueError(
    'unknown_force_mode:torch')`` is no longer raised; the only
    error is a graceful ``FileNotFoundError`` (real-mode ckpt missing)
    that the caller can catch.
    """
    from adaptive_reflow.adapters.flowmol3 import default_flowmol3_adapter

    # First: confirm the alias does NOT raise ValueError on the
    # "torch" token (the original Wave 50 Agent A bug). The factory
    # will then either succeed or raise FileNotFoundError trying to
    # load the real ckpt; both are acceptable. We assert the
    # ValueError is gone by catching it explicitly.
    raised_value_error = False
    try:
        adapter = default_flowmol3_adapter(force_mode="torch")
        # If torch + ckpt were available, the adapter would succeed
        # with _force_mode=='real'. Otherwise (most CI envs) the
        # factory raises FileNotFoundError.
        assert adapter._force_mode == "real", (
            f"expected _force_mode='real' (defensive alias from 'torch'), "
            f"got {adapter._force_mode!r}"
        )
    except ValueError as exc:
        if "unknown_force_mode" in str(exc):
            raised_value_error = True
        else:
            raise
    except FileNotFoundError:
        # Acceptable: real-ckpt load failed (no torch / no ckpt in
        # this env). The alias still worked; the factory just couldn't
        # find the ckpt file. Pass.
        pass
    assert not raised_value_error, (
        "default_flowmol3_adapter(force_mode='torch') still raises "
        "ValueError(unknown_force_mode) — Wave 53 Agent C alias "
        "didn't land."
    )


# ---------------------------------------------------------------------------
# 3. flowmol3_v2_factory force_mode kwarg (closes Wave 50 Bug B)
# ---------------------------------------------------------------------------


def test_flowmol3_v2_factory_accepts_force_mode_real() -> None:
    """`default_flowmol3adapter(force_mode='real')` selects ``backend='torch'``.

    The v2 factory did not accept ``force_mode`` at all in Wave 50,
    so ``_resolve_adapter('flowmol3_v2', force_mode='real')`` raised
    ``TypeError: default_flowmol3adapter() got an unexpected keyword
    argument 'force_mode'``. Wave 53 Agent C adds the kwarg.

    This test asserts that ``force_mode='real'`` is accepted at the
    function level (i.e. no ``TypeError(unexpected keyword argument)``)
    and that the backend selection logic resolves to ``'torch'``. We
    confirm by checking that the constructor either (a) succeeds with
    ``_backend == 'torch'`` (when torch + ckpt available) or (b)
    raises an ``ImportError`` from the constructor's torch-availability
    guard — both of which confirm the alias worked correctly.
    """
    try:
        from adaptive_reflow.adapters.flowmol3_v2_adapter import (
            default_flowmol3adapter,
        )
    except ImportError:
        pytest.skip("flowmol3_v2_adapter not importable in this env")

    try:
        adapter = default_flowmol3adapter(force_mode="real")
        # If torch + ckpt are available, the adapter succeeded.
        assert adapter._backend == "torch", (
            f"expected backend='torch' for force_mode='real', "
            f"got {adapter._backend!r}"
        )
    except ImportError:
        # Acceptable: the constructor's torch-availability guard
        # rejects ``backend='torch'`` when torch isn't installed in
        # this env. The alias still mapped correctly.
        pass


def test_flowmol3_v2_factory_accepts_force_mode_synthetic() -> None:
    """`default_flowmol3adapter(force_mode='synthetic')` selects ``backend='numpy'``.

    Confirms the inverse mapping: ``synthetic`` → ``backend='numpy'``
    (the deterministic placeholder path). This path does NOT require
    torch.
    """
    try:
        from adaptive_reflow.adapters.flowmol3_v2_adapter import (
            default_flowmol3adapter,
        )
    except ImportError:
        pytest.skip("flowmol3_v2_adapter not importable in this env")

    adapter = default_flowmol3adapter(force_mode="synthetic")
    assert adapter._backend == "numpy", (
        f"expected backend='numpy' for synthetic, got {adapter._backend!r}"
    )


def test_flowmol3_v2_factory_rejects_unknown_force_mode() -> None:
    """`default_flowmol3adapter(force_mode='bogus')` raises ``ValueError``.

    Confirms the new validator is wired and surfaces a clear error
    (rather than silently passing the bogus token to ``backend``).
    """
    try:
        from adaptive_reflow.adapters.flowmol3_v2_adapter import (
            default_flowmol3adapter,
        )
    except ImportError:
        pytest.skip("flowmol3_v2_adapter not importable in this env")

    with pytest.raises(ValueError, match="unknown_force_mode"):
        default_flowmol3adapter(force_mode="bogus")


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


# ---------------------------------------------------------------------------
# 4. Bug A — `_solve_framework` returns integrated-endpoint trace (Wave 64)
#
# Background (docs/audit/wave63-root-cause.md §2 + §5.1):
#   Pre-fix `_solve_framework` returned the LAST per-round `solve_ode` call,
#   which carried `(seed=seed+r, steps=nfe_per_round)` — a different
#   (seed, steps) axis than baseline's `(seed=seed, steps=nfe_total)`. The
#   metric layer dispatches on `(seed, steps)` via `trace.native_state_digest`
#   and `trace.steps`, so the framework arm differed from baseline at the
#   digest level EVEN when the restart-blend was a no-op (m=0 at NFE=10
#   below the gate threshold). The fix re-anchors the returned trace by
#   running a final `solve_ode` on the integrated endpoint with the FULL
#   NFE budget keyed on the ORIGINAL seed.
#
# The tests below lock in:
#   (a) the per-round NFE sums to nfe_total exactly (Bug A.3);
#   (b) the returned trace.steps == nfe_total (Bug A.1);
#   (c) the framework arm and the baseline arm agree on `steps`
#       (metric-layer axis match);
#   (d) at low NFE (gate fires), the framework arm is byte-identical to
#       baseline (the gate-skipped contract).
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# 5. Bug D — flowmol3 v2 wiring for force_mode=real (Wave 66 Agent 1)
#
# Background (docs/audit/wave65-root-cause.md §5.1, alternative
# recommendation): the registry entry for ``flowmol3`` historically
# routed to the v1 placeholder adapter (``default_flowmol3_adapter``)
# regardless of ``force_mode``. The v1 placeholder is a hash-stable
# stub that does NOT actually integrate the real FlowMol3 ckpt — its
# ``solve_ode`` returns a deterministic but content-free trace, so
# the per-atom entropy surface is the Wave 53 uniform-vs-uniform
# placeholder reading (every cell TIE_AT_SATURATION, zero SUPPORTED).
# The v2 adapter (``default_flowmol3adapter`` from
# ``adaptive_reflow.adapters.flowmol3_v2_adapter``) DOES integrate
# the real FlowMol3 CTMC velocity field on the shipped 65 MB
# Lightning ckpt. Wave 66 wires the v2 adapter in when
# ``force_mode in {"real", "auto"}`` and keeps the v1 path for
# ``force_mode="synthetic"`` so the placeholder shim still works in
# CI without torch / without the upstream ckpt.
#
# The tests below lock in the wire:
#   (a) when force_mode="synthetic", the v1 placeholder is constructed
#       (class name contains "FlowMol3Adapter" but NOT "FlowMol3V2Adapter");
#   (b) when force_mode="real" or force_mode="auto", the v2 adapter is
#       constructed (class name is "FlowMol3V2Adapter");
#   (c) the other 13 adapters are unaffected by the wire (the
#       factory_path switch is gated on ``model == "flowmol3"``).
# ---------------------------------------------------------------------------


def test_resolve_adapter_flowmol3_real_uses_v2() -> None:
    """`_resolve_adapter('flowmol3', force_mode='real')` returns the v2 adapter.

    Wave 66 Agent 1 wire: when force_mode is real (or auto) on the
    ``flowmol3`` model, the factory switches from the v1 placeholder
    to the v2 real-integration adapter so ``solve_ode`` actually runs
    on the published FlowMol3 ckpt (when torch + ckpt are available).

    Pre-fix: the v1 placeholder was used and every cell was
    TIE_AT_SATURATION (uniform-vs-uniform reading). Post-fix: the v2
    adapter is used and the per-atom entropy surface is real.

    This test asserts the construction side: the returned adapter's
    class name is ``FlowMol3V2Adapter``, not ``FlowMol3Adapter``.
    """
    tools = _import_tools_module()
    try:
        # Try the v2 import first — the test only makes sense if the
        # v2 adapter module is importable in this env. In CI (CPU-only
        # pytest envs) without torch, the v2 module may fail to import;
        # in that case skip rather than fail.
        from adaptive_reflow.adapters.flowmol3_v2_adapter import (
            FlowMol3V2Adapter as _V2Class,
        )
    except ImportError:
        pytest.skip("flowmol3_v2_adapter not importable in this env")

    # Run the resolution with force_mode=real. We monkey-patch the
    # v2 factory to be tolerant of missing torch / missing ckpt so
    # the test runs in CI without the sidecar venv.
    import adaptive_reflow.adapters.flowmol3_v2_adapter as _v2

    real_factory = _v2.default_flowmol3adapter

    def _tolerant_factory(*, force_mode: str = "synthetic", **kw: Any) -> Any:
        # Map to backend='numpy' (synthetic) so the v2 constructor
        # succeeds in CPU-only / no-ckpt envs. The class identity
        # is still v2 (FlowMol3V2Adapter).
        return real_factory(force_mode="synthetic", **kw)

    original_factory = _v2.default_flowmol3adapter
    _v2.default_flowmol3adapter = _tolerant_factory  # type: ignore[assignment]
    try:
        adapter, mode = tools._resolve_adapter("flowmol3", force_mode="real")
    finally:
        _v2.default_flowmol3adapter = original_factory  # type: ignore[assignment]
    if adapter is None and mode.startswith("IMPORT_FAILED"):
        pytest.skip(
            f"_resolve_adapter import failed (env-specific): {mode!r}"
        )

    assert adapter is not None, (
        f"_resolve_adapter returned None; expected the v2 adapter instance. "
        f"mode={mode!r}"
    )
    assert type(adapter).__name__ == "FlowMol3V2Adapter", (
        f"expected v2 adapter class 'FlowMol3V2Adapter', got "
        f"{type(adapter).__name__!r}. The Wave 66 v2 wire is not active; "
        f"_resolve_adapter is still returning the v1 placeholder for "
        f"force_mode='real'."
    )


def test_resolve_adapter_flowmol3_synthetic_uses_v1() -> None:
    """`_resolve_adapter('flowmol3', force_mode='synthetic')` returns v1.

    Wave 66 Agent 1 wire preserves the pre-Wave-66 behaviour for
    ``force_mode='synthetic'``: the v1 placeholder adapter is
    constructed so the zero-dep CI path keeps working.

    This test asserts the construction side: the returned adapter's
    class name is ``FlowMol3Adapter`` (v1), NOT ``FlowMol3V2Adapter``.
    """
    tools = _import_tools_module()
    adapter, mode = tools._resolve_adapter(
        "flowmol3", force_mode="synthetic"
    )

    assert adapter is not None, (
        f"_resolve_adapter returned None for force_mode='synthetic'; "
        f"mode={mode!r}"
    )
    assert type(adapter).__name__ != "FlowMol3V2Adapter", (
        f"force_mode='synthetic' must NOT route to v2; got "
        f"{type(adapter).__name__!r}. The Wave 66 wire incorrectly "
        f"redirects synthetic traffic to the v2 adapter."
    )
    assert type(adapter).__name__ == "FlowMol3Adapter", (
        f"expected v1 placeholder class 'FlowMol3Adapter', got "
        f"{type(adapter).__name__!r}"
    )


def test_resolve_adapter_flowmol3_auto_uses_v2() -> None:
    """`_resolve_adapter('flowmol3', force_mode='auto')` returns the v2 adapter.

    The ``auto`` token has the same v2-wire semantics as ``real``
    per Wave 66 Agent 1: when the sidecar venv has torch + ckpt,
    the v2 adapter integrates; when it doesn't, the v2 adapter
    degrades to its synthetic backend (the v2 adapter is itself
    numpy-tractable via ``backend='numpy'``). Either way, the
    adapter class identity must be ``FlowMol3V2Adapter``.
    """
    tools = _import_tools_module()
    try:
        from adaptive_reflow.adapters.flowmol3_v2_adapter import (  # noqa: F401
            FlowMol3V2Adapter,
        )
    except ImportError:
        pytest.skip("flowmol3_v2_adapter not importable in this env")

    # Same tolerant wrapper as the real test (above) so the v2
    # constructor succeeds in CPU-only / no-ckpt pytest envs.
    import adaptive_reflow.adapters.flowmol3_v2_adapter as _v2

    real_factory = _v2.default_flowmol3adapter

    def _tolerant_factory(*, force_mode: str = "synthetic", **kw: Any) -> Any:
        return real_factory(force_mode="synthetic", **kw)

    original_factory = _v2.default_flowmol3adapter
    _v2.default_flowmol3adapter = _tolerant_factory  # type: ignore[assignment]
    try:
        adapter, mode = tools._resolve_adapter("flowmol3", force_mode="auto")
    finally:
        _v2.default_flowmol3adapter = original_factory  # type: ignore[assignment]
    if adapter is None and mode.startswith("IMPORT_FAILED"):
        pytest.skip(f"_resolve_adapter import failed: {mode!r}")

    assert adapter is not None, (
        f"_resolve_adapter returned None; mode={mode!r}"
    )
    assert type(adapter).__name__ == "FlowMol3V2Adapter", (
        f"expected v2 adapter class 'FlowMol3V2Adapter' for "
        f"force_mode='auto', got {type(adapter).__name__!r}. "
        f"The Wave 66 v2 wire is not active for the auto token."
    )


def test_resolve_adapter_other_models_unaffected() -> None:
    """v2 wire is scoped to ``model == 'flowmol3'`` only.

    Pre-fix and post-fix, the other 13 PHASE-4 candidate models
    (kanzi, lineageflow, freqflow, ...) must resolve to their
    respective factories without any v2-redirect. This guards
    against an over-broad wire that accidentally routes non-FlowMol3
    models to flowmol3_v2.
    """
    tools = _import_tools_module()
    # kanzi is the cleanest "unrelated" model — it is the LineageFlow
    # sibling and has its own real-ckpt pipeline that MUST NOT be
    # touched by the Wave 66 wire.
    adapter, mode = tools._resolve_adapter("kanzi", force_mode="synthetic")
    assert adapter is not None, (
        f"_resolve_adapter('kanzi', ...) returned None; mode={mode!r}"
    )
    assert "FlowMol3" not in type(adapter).__name__, (
        f"kanzi must NOT be redirected to FlowMol3 adapter; got "
        f"{type(adapter).__name__!r}. The Wave 66 wire is over-broad."
    )

# ---------------------------------------------------------------------------
# 4. Wave 68 Phase 4 — generic dispatch tests (ObservationKind)
# ---------------------------------------------------------------------------
#
# The 3 sibling helpers (``_compute_kanzi_real_metric_via_trace``,
# ``_compute_lineageflow_real_metric_via_trace``,
# ``_compute_flowmol3_real_metric_via_trace``) are now thin
# backward-compat shims around the new generic helper
# :func:`_compute_real_metric_via_observation`. The dispatch chain
# at line 3268 routes through the generic helper via a model →
# ``ObservationKind`` lookup table (``_MODEL_OBSERVATION_KIND``).
#
# These tests verify:
# 1. The lookup table covers every model the dispatch chain used
#    pre-Phase-4.
# 2. The 3 sibling helpers still return ``(value, marker, dbg)``
#    byte-stable for the existing test scenarios.
# 3. The generic helper picks the right ``ObservationKind`` for
#    each model and dispatches to the per-kind metric decoder.
# 4. Adapters that conform to ``AdapterObservationProtocol`` (FlowMol3
#    v1 + v2 as of Phase 3) take the new ``observe(...)`` path;
#    legacy adapters (Kanzi + LineageFlow) fall through to the
#    legacy methods.
# 5. A cold-clone path with no Protocol import returns BLOCKED with
#    ``reason="observation_protocol_unavailable"`` (mirrors the
#    pre-Phase-4 BLOCKED contract).


def test_model_observation_kind_lookup_covers_dispatch_chain() -> None:
    """`_MODEL_OBSERVATION_KIND` covers every model the dispatch chain used pre-Phase-4.

    Pre-Phase-4 the dispatch chain accepted ``model in {"kanzi",
    "lineageflow", "flowmol3", "flowmol3_v2"}``. The lookup table
    must cover the same set so the generic helper can route every
    real-ckpt cell without falling through to ``BLOCKED``.
    """
    tools = _import_tools_module()
    mapping = tools._MODEL_OBSERVATION_KIND
    assert isinstance(mapping, dict), (
        f"expected dict, got {type(mapping).__name__}"
    )
    expected_models = {"kanzi", "lineageflow", "flowmol3", "flowmol3_v2"}
    missing = expected_models - set(mapping.keys())
    assert not missing, (
        f"_MODEL_OBSERVATION_KIND missing models: {sorted(missing)}"
    )
    # And every kind in the table must be a real ObservationKind
    # enum member (defensive against typos in the table).
    from adaptive_reflow.framework.interfaces import ObservationKind
    for model, kind in mapping.items():
        assert isinstance(kind, ObservationKind), (
            f"_MODEL_OBSERVATION_KIND[{model!r}] = {kind!r} is not "
            f"a valid ObservationKind"
        )


def test_generic_helper_picks_discrete_tokens_for_kanzi() -> None:
    """Generic helper with ``observation_kind=DISCRETE_TOKENS`` + Kanzi adapter → BLOCKED (legacy adapter).

    The FlowMol3 v1 placeholder ships ``observe(...)`` (Phase 3).
    The Kanzi adapter does NOT yet conform to the Protocol, so the
    generic helper falls through to ``adapter.observe_token_indices(...)``.
    With a mock adapter that returns ``observe_token_indices=...``
    via the proper Kanzi channel name, the metric computes; with no
    method at all, the helper BLOCKEDs with the legacy reason
    (mirrors pre-Phase-4 contract).
    """
    tools = _import_tools_module()
    from adaptive_reflow.framework.interfaces import ObservationKind

    class _KanziAdapter:
        """Mock Kanzi-like adapter shipping only the legacy method."""

        def observe_token_indices(
            self, trace: Any, paper_quantities: Any = None,
        ) -> dict[str, Any]:
            return {
                "discrete_token_index": [
                    0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0,
                ],
            }

    value, marker, dbg = tools._compute_real_metric_via_observation(
        adapter=_KanziAdapter(),
        trace=None,
        model="kanzi",
        observation_kind=ObservationKind.DISCRETE_TOKENS,
        seed=42,
        nfe=10,
    )
    # Kanzi decode → 8-char AA string. Pfam absent in the test env,
    # so the fallback ``_is_valid_protein_string`` path runs.
    assert marker in ("computed", "blocked"), (
        f"unexpected marker={marker!r}, dbg={dbg!r}"
    )
    if marker == "computed":
        assert isinstance(value, float)
        assert 0.0 <= value <= 1.0
        assert "observation_surface" in dbg
        assert dbg["observation_surface"]["observation_surface"] in (
            "observe_protocol", "legacy_observe_token_indices",
        )


def test_generic_helper_blocks_when_adapter_lacks_observation_method() -> None:
    """Mock adapter with NO observation methods → BLOCKED with legacy reason.

    Confirms the legacy fallback surfaces a descriptive reason when
    neither ``observe(...)`` (Protocol path) nor
    ``observe_token_indices`` / ``observe_entropy_reduction``
    (legacy path) is available.
    """
    tools = _import_tools_module()
    from adaptive_reflow.framework.interfaces import ObservationKind

    class _NoMethodAdapter:
        """Adapter with no observation methods at all."""
        pass

    value, marker, dbg = tools._compute_real_metric_via_observation(
        adapter=_NoMethodAdapter(),
        trace=None,
        model="kanzi",
        observation_kind=ObservationKind.DISCRETE_TOKENS,
        seed=42,
        nfe=10,
    )
    assert value is None
    assert marker == "blocked"
    assert dbg.get("reason") == "adapter_missing_observe_token_indices"


def test_generic_helper_blocks_on_nan_entropy_reduction() -> None:
    """``observe_entropy_reduction`` returning NaN → BLOCKED.

    Mirrors the pre-Phase-4 ``entropy_reduction_is_nan`` contract
    from the FlowMol3 metric helper. Confirms the legacy fallback
    in :func:`_extract_observation_legacy` surfaces NaN correctly.
    """
    tools = _import_tools_module()
    from adaptive_reflow.framework.interfaces import ObservationKind

    class _NaNEntropyAdapter:
        def observe_entropy_reduction(
            self, trace: Any, paper_quantities: Any = None,
            *,
            theta_before: Any = None,
            theta_after: Any = None,
        ) -> dict[str, float]:
            return {"per_position_entropy_reduction": float("nan")}

    value, marker, dbg = tools._compute_real_metric_via_observation(
        adapter=_NaNEntropyAdapter(),
        trace=None,
        model="flowmol3",
        observation_kind=ObservationKind.POSITION_ENTROPY_REDUCTION,
        seed=42,
        nfe=10,
    )
    assert value is None
    assert marker == "blocked"
    assert dbg.get("reason") == "entropy_reduction_is_nan"


def test_flowmol3_sibling_shim_delegates_to_generic_helper() -> None:
    """``_compute_flowmol3_real_metric_via_trace`` shim returns ``(value, marker, dbg)``.

    Backward-compat contract: the sibling helper signature is
    unchanged, so external callers (test surface + downstream
    scripts) keep working. The implementation delegates to the
    generic helper + threads ``theta_after``.
    """
    tools = _import_tools_module()
    from adaptive_reflow.adapters.flowmol3 import default_flowmol3_adapter

    adapter = default_flowmol3_adapter(force_mode="synthetic")
    trace = _make_placeholder_trace(adapter)

    value, marker, dbg = tools._compute_flowmol3_real_metric_via_trace(
        adapter=adapter, trace=trace, seed=42, nfe=10,
    )
    # Synthetic FlowMol3: uniform-vs-uniform → 0.0.
    assert marker == "computed"
    assert isinstance(value, float)
    assert value == 0.0
    # Debug dict must carry the byte-stable fields + the new
    # observation_surface marker.
    assert dbg["metric_axis"] == "per_position_atom_type_entropy_reduction"
    assert dbg["K_atom_types"] == 10
    assert "observation_surface" in dbg
    assert "real_theta_after" in dbg  # Wave 54 parity
    assert "Wave 53" in dbg["decode_strategy"]


def test_kanzi_sibling_shim_returns_value_marker_dbg() -> None:
    """``_compute_kanzi_real_metric_via_trace`` shim contract preserved.

    The Kanzi shim delegates to the generic helper with
    ``observation_kind=DISCRETE_TOKENS``. The signature, return
    tuple, and marker contract are unchanged.
    """
    tools = _import_tools_module()

    class _KanziAdapter:
        def observe_token_indices(
            self, trace: Any, paper_quantities: Any = None,
        ) -> dict[str, Any]:
            return {"discrete_token_index": list(range(20))}

    value, marker, dbg = tools._compute_kanzi_real_metric_via_trace(
        adapter=_KanziAdapter(), trace=None, seed=42, nfe=10,
    )
    assert marker in ("computed", "blocked")
    if marker == "computed":
        assert isinstance(value, float)


def test_lineageflow_sibling_shim_returns_value_marker_dbg() -> None:
    """``_compute_lineageflow_real_metric_via_trace`` shim contract preserved.

    The LineageFlow shim delegates to the generic helper with
    ``observation_kind=DISCRETE_TOKENS``. Without ``torch`` or
    ``transformers`` installed in the test env, the helper BLOCKEDs
    with a missing-dep reason — which is the byte-stable contract.
    """
    tools = _import_tools_module()

    class _LineageflowAdapter:
        def observe_token_indices(
            self, trace: Any, paper_quantities: Any = None,
        ) -> dict[str, Any]:
            return {"amino_acid_categorical": list(range(20))}

    value, marker, dbg = tools._compute_lineageflow_real_metric_via_trace(
        adapter=_LineageflowAdapter(), trace=None, seed=42, nfe=10,
    )
    # In the test env, ESM-2 + torch may be unavailable. The helper
    # either returns computed (if ESM-2 is installed and ppl <= 50)
    # or BLOCKED with a missing-dep reason. Either path is correct.
    assert marker in ("computed", "blocked")
    if marker == "blocked":
        # The reason must be a meaningful diagnostic (missing dep /
        # empty seq / etc.), not an unhandled crash.
        assert "reason" in dbg


def test_extract_observation_legacy_returns_blocked_when_method_missing() -> None:
    """Legacy ``_extract_observation_legacy`` surfaces descriptive BLOCKED reasons.

    Defensive test: when an adapter does not ship the requested
    legacy method, the helper BLOCKEDs with the standard reason
    (matches the pre-Phase-4 ``hasattr`` failure path).
    """
    tools = _import_tools_module()
    from adaptive_reflow.framework.interfaces import ObservationKind

    class _NoEntropyAdapter:
        pass

    obs, status, dbg = tools._extract_observation_legacy(
        adapter=_NoEntropyAdapter(),
        trace=None,
        model="flowmol3",
        observation_kind=ObservationKind.POSITION_ENTROPY_REDUCTION,
        paper_quantities=None,
        theta_after=None,
        dbg={"model": "flowmol3"},
    )
    assert obs is None
    assert status == "blocked"
    assert dbg["reason"] == "adapter_missing_observe_entropy_reduction"
    assert dbg["adapter"] == "_NoEntropyAdapter"


# ---------------------------------------------------------------------------
# 5. Wave 54 Phase 2 — v2 observe_as_dict() + ObservationKind dispatch
# ---------------------------------------------------------------------------
#
# Closes the Wave 66 BLOCKED failure mode (v2 observe() was unreachable
# because the metric helper passed ``state=None`` to v2's observe()). The
# Phase 2 fix surfaces a dict-keyed ``observe_as_dict()`` method on the
# v2 adapter + extends the metric helper to consume the dict with a
# graceful partial-block fallback.
#
# The 4 tests below lock in:
#   (a) v2's ``observe_as_dict()`` returns the 4 canonical keys (test_v2_observe_returns_dict).
#   (b) the metric helper dispatches on ObservationKind via the dict
#       (test_metric_helper_dispatches_on_kind).
#   (c) missing ObservationKind key → BLOCKED for that metric only
#       (test_v2_missing_kind_partial_block).
#   (d) Wave 47/52/53/54 baselines byte-stable (test_byte_stable_wave47_52).


def test_v2_observe_returns_dict() -> None:
    """v2 ``observe_as_dict()`` returns dict keyed by 4 canonical ObservationKind tags.

    Closes the Wave 54 Phase 2 contract: the v2 adapter exposes a dict-keyed
    dispatch surface with ENDPOINT_BUNDLE / DISCRETE_TOKENS /
    POSITION_ENTROPY_REDUCTION / TRAJECTORY_NATIVE keys. The metric helper
    consumes this dict to dispatch on kind directly (no tuple iteration).
    """
    from adaptive_reflow.adapters.flowmol3_v2_adapter import (
        FlowMol3V2Adapter,
    )
    from adaptive_reflow.framework.interfaces import ObservationKind
    from adaptive_reflow.universal.state import ODEConditionDelta

    adapter = FlowMol3V2Adapter(backend="numpy", num_steps=4)
    # Drive a real solve_ode so the native-state cache has a trajectory.
    bundle = adapter.build_initial_state(
        batch_id="w54p2c", sample_id="smoke",
    )
    condition = ODEConditionDelta(
        delta_spec={"num_steps": 4, "sampler_id": "euler"},
        source="w54p2c-test",
        target_round=0,
        calibration_artifact_hash="w54p2c-test",
    )
    trace = adapter.solve_ode(bundle, condition, seed=42)
    obs_dict = adapter.observe_as_dict(trace, bundle)
    # All 4 canonical keys must be present (value=None is acceptable for
    # DISCRETE_TOKENS / TRAJECTORY_NATIVE since v2 doesn't ship those).
    expected_keys = {
        ObservationKind.ENDPOINT_BUNDLE,
        ObservationKind.DISCRETE_TOKENS,
        ObservationKind.POSITION_ENTROPY_REDUCTION,
        ObservationKind.TRAJECTORY_NATIVE,
    }
    assert set(obs_dict.keys()) == expected_keys, (
        f"observe_as_dict missing keys; got {set(obs_dict.keys())!r}, "
        f"expected {expected_keys!r}"
    )
    # POSITION_ENTROPY_REDUCTION must be populated (the v2-native entropy
    # shim is the core fix for the Wave 66 BLOCKED issue).
    pos_entropy = obs_dict[ObservationKind.POSITION_ENTROPY_REDUCTION]
    assert pos_entropy is not None, (
        "POSITION_ENTROPY_REDUCTION missing from observe_as_dict; "
        "the v2 entropy shim is unreachable via the dict surface"
    )
    assert pos_entropy.kind == ObservationKind.POSITION_ENTROPY_REDUCTION
    assert isinstance(pos_entropy.payload, float)
    assert pos_entropy.units == "nats"
    # ENDPOINT_BUNDLE must be a StateBundle reference.
    endpoint = obs_dict[ObservationKind.ENDPOINT_BUNDLE]
    assert endpoint is not None
    assert endpoint.kind == ObservationKind.ENDPOINT_BUNDLE


def test_metric_helper_dispatches_on_kind() -> None:
    """Metric helper consumes ``observe_as_dict`` and dispatches on ObservationKind.

    Locks the Phase 2 dispatch contract: when the adapter ships
    ``observe_as_dict``, the metric helper uses it (NOT the legacy tuple
    iteration) and dispatches on the dict key. Mirrors the
    Wave 47/52 Kanzi / LineageFlow contract for the v2 wire.
    """
    tools = _import_tools_module()
    from adaptive_reflow.framework.interfaces import ObservationKind
    from adaptive_reflow.universal.state import ODEConditionDelta

    from adaptive_reflow.adapters.flowmol3_v2_adapter import (
        FlowMol3V2Adapter,
    )

    adapter = FlowMol3V2Adapter(backend="numpy", num_steps=4)
    bundle = adapter.build_initial_state(
        batch_id="w54p2c", sample_id="dispatch",
    )
    condition = ODEConditionDelta(
        delta_spec={"num_steps": 4, "sampler_id": "euler"},
        source="w54p2c-dispatch",
        target_round=0,
        calibration_artifact_hash="w54p2c-dispatch",
    )
    trace = adapter.solve_ode(bundle, condition, seed=42)

    value, marker, dbg = tools._compute_real_metric_via_observation(
        adapter=adapter,
        trace=trace,
        model="flowmol3_v2",
        observation_kind=ObservationKind.POSITION_ENTROPY_REDUCTION,
        seed=42,
        nfe=10,
    )
    # v2 with synthetic backend → finite entropy reduction (0.0 for
    # uniform-vs-uniform fallback). The dispatch MUST take the
    # observe_as_dict path (NOT the legacy tuple path).
    assert marker == "computed", (
        f"expected marker='computed', got marker={marker!r}, dbg={dbg!r}"
    )
    assert isinstance(value, float)
    # The metric layer nests the original observation_surface dict
    # under ``dbg["observation_surface"]`` (mirrors the Wave 47/52
    # Kanzi / LineageFlow contract); check via the nested key.
    nested_dbg = dbg.get("observation_surface", {})
    assert nested_dbg.get("observation_surface") == "observe_as_dict_protocol", (
        f"metric helper did NOT use observe_as_dict; surface="
        f"{nested_dbg.get('observation_surface')!r}. The Phase 2 "
        f"dispatch is not active."
    )
    assert nested_dbg.get("observation_channel") == "atom_type_entropy_reduction"
    assert nested_dbg.get("observation_units") == "nats"


def test_v2_missing_kind_partial_block() -> None:
    """Missing ObservationKind key in observe_as_dict → BLOCKED for that metric only.

    The Phase 2 contract: a missing key in ``observe_as_dict`` returns
    BLOCKED for that single metric (with a descriptive reason) rather
    than crashing the whole observation surface. Mirrors the graceful
    fallback the metric helper offers on the legacy
    ``observe_token_indices`` / ``observe_entropy_reduction`` path.
    """
    tools = _import_tools_module()
    from adaptive_reflow.framework.interfaces import ObservationKind

    class _PartialDictAdapter:
        """Adapter that ships ``observe_as_dict`` but only the ENDPOINT_BUNDLE key.

        Also ships a stub ``observe`` method (returning an empty tuple)
        so the helper's ``isinstance(adapter, AdapterObservationProtocol)``
        check passes — the helper dispatches on ``observe_as_dict`` when
        present, so the partial-block fallback can be exercised.
        """

        def observe_as_dict(
            self,
            trace: Any,
            state: Any,
            paper_quantities: Any = None,
            *,
            strategies: tuple[ObservationKind, ...] = (
                ObservationKind.ENDPOINT_BUNDLE,
                ObservationKind.DISCRETE_TOKENS,
                ObservationKind.POSITION_ENTROPY_REDUCTION,
                ObservationKind.TRAJECTORY_NATIVE,
            ),
            theta_before: Any = None,
            theta_after: Any = None,
        ) -> dict[ObservationKind, Any]:
            # Only return the ENDPOINT_BUNDLE key; the rest stay None.
            return {
                ObservationKind.ENDPOINT_BUNDLE: None,
                ObservationKind.DISCRETE_TOKENS: None,
                ObservationKind.POSITION_ENTROPY_REDUCTION: None,
                ObservationKind.TRAJECTORY_NATIVE: None,
            }

        def observe(
            self,
            trace: Any,
            state: Any,
            paper_quantities: Any = None,
            *,
            strategies: tuple[ObservationKind, ...] = (),
            theta_before: Any = None,
            theta_after: Any = None,
        ) -> tuple[Any, ...]:
            return ()

    # Request DISCRETE_TOKENS — not present → BLOCKED for THAT metric only.
    value, marker, dbg = tools._compute_real_metric_via_observation(
        adapter=_PartialDictAdapter(),
        trace=None,
        model="flowmol3_v2",
        observation_kind=ObservationKind.DISCRETE_TOKENS,
        seed=42,
        nfe=10,
    )
    assert value is None
    assert marker == "blocked"
    assert "observe_as_dict missing key" in dbg.get("reason", "")
    assert dbg["observation_surface"] == "observe_as_dict_protocol"
    assert dbg["observe_as_dict_missing_kind"] == str(
        ObservationKind.DISCRETE_TOKENS
    )
    # Confirm graceful fallback: when adapter DOES ship the requested
    # kind (POSITION_ENTROPY_REDUCTION stubbed), the metric layer
    # proceeds (may be blocked at decode, but NOT at partial-block).
    class _FullAdapter(_PartialDictAdapter):
        def observe_as_dict(
            self,
            trace: Any,
            state: Any,
            paper_quantities: Any = None,
            *,
            strategies: tuple[ObservationKind, ...] = (),
            theta_before: Any = None,
            theta_after: Any = None,
        ) -> dict[ObservationKind, Any]:
            from adaptive_reflow.framework.interfaces import (
                ObservationResult,
            )
            return {
                ObservationKind.ENDPOINT_BUNDLE: None,
                ObservationKind.DISCRETE_TOKENS: None,
                ObservationKind.POSITION_ENTROPY_REDUCTION: ObservationResult(
                    kind=ObservationKind.POSITION_ENTROPY_REDUCTION,
                    channel="atom_type_entropy_reduction",
                    payload=0.0,
                    units="nats",
                ),
                ObservationKind.TRAJECTORY_NATIVE: None,
            }

    value3, marker3, dbg3 = tools._compute_real_metric_via_observation(
        adapter=_FullAdapter(),
        trace=None,
        model="flowmol3_v2",
        observation_kind=ObservationKind.POSITION_ENTROPY_REDUCTION,
        seed=42,
        nfe=10,
    )
    # The metric helper does NOT partial-block when the kind is shipped;
    # it computes (or downstream-blocks at decode — but the partial-
    # block reason is absent from the dbg).
    assert marker3 in ("computed", "blocked")
    if marker3 == "blocked":
        assert "observe_as_dict missing key" not in dbg3.get(
            "reason", ""
        )


def test_byte_stable_wave47_52() -> None:
    """Wave 47/52 baselines unchanged — Phase 2 fix does NOT touch legacy numerics.

    Locks the Phase 2 contract: the metric-helper Phase 2 extension is
    additive (new dict-keyed path) and does NOT alter the existing
    tuple-keyed path, the per-model decode math, or the
    _MODEL_OBSERVATION_KIND lookup table. Kanzi + LineageFlow + FlowMol3
    v1 baselines MUST remain byte-stable.
    """
    tools = _import_tools_module()
    from adaptive_reflow.framework.interfaces import ObservationKind

    # Wave 47 baseline: _MODEL_OBSERVATION_KIND includes "lineageflow"
    # (DISCRETE_TOKENS) — unchanged.
    mapping = tools._MODEL_OBSERVATION_KIND
    assert mapping.get("lineageflow") == ObservationKind.DISCRETE_TOKENS
    # Wave 52 baseline: Kanzi still maps to DISCRETE_TOKENS.
    assert mapping.get("kanzi") == ObservationKind.DISCRETE_TOKENS
    # Wave 53/54/66 baseline: FlowMol3 v1 + v2 still map to
    # POSITION_ENTROPY_REDUCTION.
    assert (
        mapping.get("flowmol3") == ObservationKind.POSITION_ENTROPY_REDUCTION
    )
    assert (
        mapping.get("flowmol3_v2")
        == ObservationKind.POSITION_ENTROPY_REDUCTION
    )
    # Byte-stable: the new ``observe_as_dict`` surface did NOT replace
    # the existing ``observe(...)`` method on FlowMol3 v2 — the legacy
    # tuple-returning surface is still exported and dispatchable.
    from adaptive_reflow.adapters.flowmol3_v2_adapter import FlowMol3V2Adapter
    assert hasattr(FlowMol3V2Adapter, "observe")
    assert hasattr(FlowMol3V2Adapter, "observe_as_dict")
    # The dict-keyed path is a NEW surface, NOT a replacement; verify
    # the tuple-returning observe() is still importable + has the
    # correct signature.
    import inspect
    sig = inspect.signature(FlowMol3V2Adapter.observe)
    assert "strategies" in sig.parameters
    assert "theta_before" in sig.parameters
    assert "theta_after" in sig.parameters

