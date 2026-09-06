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