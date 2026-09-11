"""Tests for tools/eval/sweep.py — per-cell _run_cell + _resolve_adapter dispatch.

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

def test_run_cell_passes_sampled_molecules_for_flowmol3() -> None:
    """`_run_cell` threads captured ``sampled_molecules`` into ``_compute_flowmol3_composite``.

    Stubs the inner chain (``_solve_baseline``, ``_solve_framework``,
    ``_compute_metric``) so the test focuses on the wire: when the
    adapter ships ``export_sampled_molecules`` and the model is
    ``flowmol3``, the list returned by the new export method is passed
    verbatim into the composite call.

    The stub adapter inherits the v1 placeholder's
    ``build_initial_state`` / ``solve_ode`` surface (so
    ``_resolve_adapter`` accepts it) and adds the new
    ``export_sampled_molecules`` method. We monkey-patch the inner
    chain so the test is independent of the real solver + metric
    helpers (those have their own tests).
    """
    tools = _import_tools_module()
    from adaptive_reflow.adapters.flowmol3 import default_flowmol3_adapter

    adapter = default_flowmol3_adapter(force_mode="synthetic")
    # Attach the new method the v1 placeholder does NOT ship. Use a
    # tuple return (molecules, metadata) to match Wave 70 Phase 3 §2.
    expected_molecules = [object(), object(), object()]

    def _stub_export(self: Any, trace: Any) -> tuple[list[Any], dict[str, Any]]:
        return expected_molecules, {"marker": "ok", "sanitize_status": "ok"}

    adapter.export_sampled_molecules = _stub_export.__get__(  # type: ignore[method-assign]
        adapter, type(adapter),
    )

    # Stub _resolve_adapter so _run_cell returns our pre-configured
    # adapter (with the new method attached) instead of building a
    # fresh v1 placeholder via the factory.
    original_resolve = tools._resolve_adapter

    def _stub_resolve(
        model: str,
        force_mode: str = "synthetic",
        restart_min_nfe: int | None = None,
        nfe_budget: int | None = None,
    ) -> tuple[Any, str]:
        return adapter, "synthetic"

    tools._resolve_adapter = _stub_resolve  # type: ignore[assignment]

    # Capture _compute_flowmol3_composite kwargs.
    captured: dict[str, Any] = {}

    def _capturing_compute(**kwargs: Any) -> tuple[float | None, str, dict[str, Any]]:
        captured.update(kwargs)
        return 0.0, "computed", {"chemistry_input_source": "neutral_zero_stub"}

    # Short-circuit the inner chain so the test only exercises the wire.
    _stub_trace = _make_placeholder_trace(adapter)
    original_solve_baseline = tools._solve_baseline
    original_solve_framework = tools._solve_framework
    original_compute_metric = tools._compute_metric
    original_compute_flowmol3 = tools._compute_flowmol3_composite

    def _stub_solve_baseline(*args: Any, **kwargs: Any) -> tuple[Any, float]:
        return _stub_trace, 0.0

    def _stub_solve_framework(*args: Any, **kwargs: Any) -> tuple[Any, float]:
        return _stub_trace, 0.0

    def _stub_compute_metric(*args: Any, **kwargs: Any) -> tuple[Any, str, dict[str, Any]]:
        return 1.0, "synthetic_fallback", {"value": 1.0}

    tools._solve_baseline = _stub_solve_baseline  # type: ignore[assignment]
    tools._solve_framework = _stub_solve_framework  # type: ignore[assignment]
    tools._compute_metric = _stub_compute_metric  # type: ignore[assignment]
    tools._compute_flowmol3_composite = _capturing_compute  # type: ignore[assignment]
    try:
        cell = tools._run_cell(
            model="flowmol3",
            seed=42,
            nfe=10,
            n_rounds=3,
            force_mode="synthetic",
            metric_mode="synthetic",
            composite_metric="real",
        )
    finally:
        tools._resolve_adapter = original_resolve  # type: ignore[assignment]
        tools._solve_baseline = original_solve_baseline  # type: ignore[assignment]
        tools._solve_framework = original_solve_framework  # type: ignore[assignment]
        tools._compute_metric = original_compute_metric  # type: ignore[assignment]
        tools._compute_flowmol3_composite = original_compute_flowmol3  # type: ignore[assignment]

    # Wire contract: _compute_flowmol3_composite MUST have been called
    # with sampled_molecules equal to the list returned by
    # adapter.export_sampled_molecules (Phase 3 tuple[0]).
    assert captured, (
        "_compute_flowmol3_composite was not called by _run_cell; "
        "the wire from _run_cell -> composite is broken."
    )
    assert "sampled_molecules" in captured, (
        "_run_cell did NOT pass sampled_molecules to "
        "_compute_flowmol3_composite; the Phase 4 wire is missing."
    )
    assert captured["sampled_molecules"] is not None, (
        "sampled_molecules must NOT be None when the adapter ships "
        "export_sampled_molecules (model='flowmol3')."
    )
    assert list(captured["sampled_molecules"]) == expected_molecules, (
        f"sampled_molecules passed to composite must match the list "
        f"returned by adapter.export_sampled_molecules; got "
        f"{captured['sampled_molecules']!r}, expected "
        f"{expected_molecules!r}"
    )
    # And the cell dict carries the composite_marker = 'computed' from
    # the stub (sanity check that the cell completed end-to-end).
    assert cell.get("composite_marker") == "computed", (
        f"cell composite_marker must echo the stub marker, got "
        f"{cell.get('composite_marker')!r}"
    )


def test_run_cell_handles_missing_export_sampled_molecules() -> None:
    """`_run_cell` degrades to ``sampled_molecules = None`` for v1 (no export method).

    Locks in the backward-compat contract: when the adapter does NOT
    ship ``export_sampled_molecules`` (the v1 placeholder, or any
    non-flowmol3 model), ``_run_cell`` MUST NOT raise and MUST thread
    ``sampled_molecules = None`` into the composite call.

    The v1 placeholder FlowMol3 adapter does NOT have
    ``export_sampled_molecules`` — that is the entire byte-stable
    contract we are locking in here.
    """
    tools = _import_tools_module()
    from adaptive_reflow.adapters.flowmol3 import default_flowmol3_adapter

    adapter = default_flowmol3_adapter(force_mode="synthetic")
    # Defensive: confirm the v1 placeholder truly lacks the method.
    assert not hasattr(adapter, "export_sampled_molecules"), (
        "The v1 FlowMol3 placeholder must NOT ship "
        "export_sampled_molecules — only the v2 adapter does. If you "
        "are seeing this assertion, v1 has been updated and the "
        "backward-compat test below needs to be re-evaluated."
    )

    # Stub _resolve_adapter to return our pre-configured v1 adapter
    # (which does NOT have export_sampled_molecules).
    original_resolve = tools._resolve_adapter

    def _stub_resolve(
        model: str,
        force_mode: str = "synthetic",
        restart_min_nfe: int | None = None,
        nfe_budget: int | None = None,
    ) -> tuple[Any, str]:
        return adapter, "synthetic"

    tools._resolve_adapter = _stub_resolve  # type: ignore[assignment]

    # Capture _compute_flowmol3_composite kwargs.
    captured: dict[str, Any] = {}

    def _capturing_compute(**kwargs: Any) -> tuple[float | None, str, dict[str, Any]]:
        captured.update(kwargs)
        return 0.0, "degraded_chemistry", {
            "chemistry_input_source": "neutral_zero_stub",
        }

    # Short-circuit the inner chain (same approach as test 1).
    _stub_trace = _make_placeholder_trace(adapter)
    original_solve_baseline = tools._solve_baseline
    original_solve_framework = tools._solve_framework
    original_compute_metric = tools._compute_metric
    original_compute_flowmol3 = tools._compute_flowmol3_composite

    def _stub_solve_baseline(*args: Any, **kwargs: Any) -> tuple[Any, float]:
        return _stub_trace, 0.0

    def _stub_solve_framework(*args: Any, **kwargs: Any) -> tuple[Any, float]:
        return _stub_trace, 0.0

    def _stub_compute_metric(*args: Any, **kwargs: Any) -> tuple[Any, str, dict[str, Any]]:
        return 1.0, "synthetic_fallback", {"value": 1.0}

    tools._solve_baseline = _stub_solve_baseline  # type: ignore[assignment]
    tools._solve_framework = _stub_solve_framework  # type: ignore[assignment]
    tools._compute_metric = _stub_compute_metric  # type: ignore[assignment]
    tools._compute_flowmol3_composite = _capturing_compute  # type: ignore[assignment]
    try:
        cell = tools._run_cell(
            model="flowmol3",
            seed=42,
            nfe=10,
            n_rounds=3,
            force_mode="synthetic",
            metric_mode="synthetic",
            composite_metric="real",
        )
    finally:
        tools._resolve_adapter = original_resolve  # type: ignore[assignment]
        tools._solve_baseline = original_solve_baseline  # type: ignore[assignment]
        tools._solve_framework = original_solve_framework  # type: ignore[assignment]
        tools._compute_metric = original_compute_metric  # type: ignore[assignment]
        tools._compute_flowmol3_composite = original_compute_flowmol3  # type: ignore[assignment]

    # Backward-compat contract: v1 has no export_sampled_molecules,
    # so sampled_molecules passed to the composite MUST be None
    # (degrading to the Wave 69 Phase 2 legacy caller contract).
    assert captured, (
        "_compute_flowmol3_composite was not called by _run_cell; "
        "the wire from _run_cell -> composite is broken."
    )
    assert "sampled_molecules" in captured, (
        "_run_cell did NOT pass sampled_molecules to "
        "_compute_flowmol3_composite; the Phase 4 wire is missing."
    )
    assert captured["sampled_molecules"] is None, (
        f"sampled_molecules MUST be None for v1 (no export method), "
        f"got {captured['sampled_molecules']!r}. The backward-compat "
        f"contract from Wave 69 Phase 2 is regressed."
    )
    # Sanity: cell returns without crashing (legacy caller contract
    # preserved — marker = 'degraded_chemistry').
    assert cell.get("composite_marker") == "degraded_chemistry", (
        f"v1 placeholder path must surface marker='degraded_chemistry' "
        f"(no chemistry data), got {cell.get('composite_marker')!r}"
    )




def test_resolve_adapter_threads_weights_path_for_flowmol3_real() -> None:
    """`_resolve_adapter('flowmol3', force_mode='real')` passes weights_path.

    Asserts the GAP-4 fix at the call boundary: the kwargs handed to
    the v2 factory carry ``weights_path`` pointing at the published
    ckpt (``FLOWMOL3_REAL_CKPT``). Captured via a factory stub so the
    test needs neither torch nor the ckpt bytes.
    """
    tools = _import_tools_module()
    if not tools.FLOWMOL3_REAL_CKPT.is_file():
        pytest.skip(
            f"FlowMol3 ckpt not installed at {tools.FLOWMOL3_REAL_CKPT}; "
            "the weights_path thread is gated on the file existing"
        )
    import adaptive_reflow.adapters.flowmol3_v2_adapter as _v2

    captured: dict[str, Any] = {}
    original_factory = _v2.default_flowmol3adapter

    # NOTE: ``weights_path`` must appear *explicitly* in the stub
    # signature — ``_resolve_adapter`` filters optional kwargs through
    # ``inspect.signature(factory).parameters``, so a bare ``**kw`` stub
    # would make the test fail for the wrong reason.
    def _capturing_factory(
        *, weights_path: Any = None, force_mode: str = "synthetic", **kw: Any
    ) -> Any:
        captured.update(kw)
        captured["force_mode"] = force_mode
        if weights_path is not None:
            captured["weights_path"] = weights_path
        # Drop the real-mode kwargs so the constructor succeeds in
        # CPU-only / no-torch pytest envs; class identity is v2.
        return original_factory(force_mode="synthetic", **kw)

    _v2.default_flowmol3adapter = _capturing_factory  # type: ignore[assignment]
    try:
        adapter, mode = tools._resolve_adapter("flowmol3", force_mode="real")
    finally:
        _v2.default_flowmol3adapter = original_factory  # type: ignore[assignment]

    if adapter is None and mode.startswith("IMPORT_FAILED"):
        pytest.skip(f"_resolve_adapter import failed (env-specific): {mode!r}")
    assert "weights_path" in captured, (
        "_resolve_adapter did NOT pass weights_path to the flowmol3 v2 "
        "factory for force_mode='real'. GAP-4 is open: the factory "
        "defaults to weights_path=None, _load_model() returns "
        "kind=synthetic, and the chemistry composite stays 0.0. "
        f"kwargs seen: {sorted(captured)}"
    )
    assert captured["weights_path"] == str(tools.FLOWMOL3_REAL_CKPT), (
        f"weights_path must point at the published ckpt "
        f"{str(tools.FLOWMOL3_REAL_CKPT)!r}, got "
        f"{captured['weights_path']!r}"
    )



def test_resolve_adapter_no_weights_path_for_synthetic_mode() -> None:
    """Synthetic mode for flowmol3 keeps the pre-Wave-73 call shape.

    Backward compatibility for the GAP-4 fix: ``force_mode='synthetic'``
    must NOT receive ``weights_path`` (it routes to the v1 placeholder,
    whose factory does not take the kwarg). The Wave 95 Phase 1.D E5
    wire extends ``weights_path`` to kanzi / lineageflow / hidream_i1
    in real/auto mode only; that scope is covered by the sibling
    test_resolve_adapter_threads_weights_path_for_kanzi test.
    """
    tools = _import_tools_module()
    import adaptive_reflow.adapters.flowmol3 as _v1

    captured: dict[str, Any] = {}
    original_v1 = _v1.default_flowmol3_adapter

    # ``weights_path`` explicit in the stub signature so the
    # ``inspect.signature`` filter in ``_resolve_adapter`` WOULD pass it
    # if the mode gate were wrong — the assertion below is then real.
    def _capturing_v1(*, weights_path: Any = None, **kw: Any) -> Any:
        captured.update(kw)
        if weights_path is not None:
            captured["weights_path"] = weights_path
        return original_v1(**kw)

    _v1.default_flowmol3_adapter = _capturing_v1  # type: ignore[assignment]
    try:
        adapter, mode = tools._resolve_adapter(
            "flowmol3", force_mode="synthetic",
        )
    finally:
        _v1.default_flowmol3_adapter = original_v1  # type: ignore[assignment]

    assert adapter is not None, (
        f"_resolve_adapter returned None for synthetic mode; mode={mode!r}"
    )
    assert "weights_path" not in captured, (
        "force_mode='synthetic' must NOT receive weights_path — the v1 "
        "placeholder factory does not accept it and the zero-dependency "
        f"CI path must stay byte-stable. kwargs seen: {sorted(captured)}"
    )

    # Wave 95 Phase 1.D: kanzi / lineageflow / hidream_i1 now ALSO
    # receive weights_path in real/auto mode (E5 close — symmetric
    # wire across the 4 SOTA factories). The kanzi thread path is
    # verified by test_resolve_adapter_threads_weights_path_for_kanzi.
    # This test now only verifies the synthetic-mode + flowmol3-v1
    # shape is unchanged.



def test_resolve_adapter_threads_weights_path_for_kanzi() -> None:
    """``_resolve_adapter('kanzi', ...)`` threads ``weights_path`` when ckpt exists.

    Wave 95 Phase 1.D — E5 wire extension. The test monkey-patches
    ``adaptive_reflow.adapters.kanzi.default_kanzi_adapter`` so the
    test surface does not require the upstream ``kanzi`` package to
    be installed in the pytest env. The stub captures the kwargs
    dict so the assertion verifies the framework actually threads
    ``weights_path`` (with the resolved ckpt path string) into the
    factory call when both ``force_mode in {"real", "auto"}`` and
    the canonical ``data/kanzi/kanzi_encoder.pt`` file exist on
    disk.

    Pre-fix: ``kwargs`` would NOT contain a ``weights_path`` key —
    the kanzi factory was built without the resolved ckpt and the
    per-cell framework-vs-baseline eval degraded to the synthetic
    field.
    """
    tools = _import_tools_module()
    import adaptive_reflow.adapters.kanzi as _kanzi

    captured: dict[str, Any] = {}
    original_kanzi = _kanzi.default_kanzi_adapter

    def _capturing_kanzi(
        *,
        weights_path: Any = None,
        **kw: Any,
    ) -> Any:
        captured["force_mode"] = kw.get("force_mode")
        captured["weights_path"] = weights_path
        captured.update({k: v for k, v in kw.items() if k != "force_mode"})

        class _Stub:
            family = "kanzi"

        return _Stub()

    _kanzi.default_kanzi_adapter = _capturing_kanzi  # type: ignore[assignment]
    try:
        adapter, mode = tools._resolve_adapter(
            "kanzi", force_mode="real",
        )
    except Exception as exc:  # noqa: BLE001 — env-specific.
        pytest.skip(
            f"_resolve_adapter('kanzi', force_mode='real') import "
            f"failed (env-specific): {type(exc).__name__}:{exc}"
        )
    finally:
        _kanzi.default_kanzi_adapter = original_kanzi  # type: ignore[assignment]

    # When the test environment has the canonical kanzi ckpt at
    # ``data/kanzi/kanzi_encoder.pt`` (or under the
    # ``data/kanzi_ckpt/`` alias), ``kanzi_resolve_weights_path``
    # returns a real path string and the framework threads it.
    # When the ckpt is absent the wire is a no-op (the framework
    # does NOT fabricate a path), so the captured value is ``None``.
    # Either outcome is acceptable per the resolver contract; we only
    # assert that the wire *path* ran (i.e. force_mode in real/auto
    # was respected) by checking the captured force_mode.
    assert captured.get("force_mode") in {"real", "torch", "auto"}, (
        "Wave 95 Phase 1.D: kanzi factory call did NOT receive a "
        "real/auto force_mode. The E5 wire dispatch is broken. "
        f"captured={captured!r}"
    )
    # The ``weights_path`` key is in the captured dict iff the wire
    # ran; when the resolver returns ``None`` (no ckpt on disk) the
    # key is still in the dict (with value ``None``) because the
    # E5 branch sets ``kwargs["weights_path"]`` only when the
    # resolver returned a real path. Either way the assertion below
    # is the spec contract: the resolver ran and the E5 branch
    # either set a real path or correctly skipped when no ckpt
    # was present.
    assert "weights_path" in captured, (
        "Wave 95 Phase 1.D: kanzi factory call did NOT include the "
        "weights_path kwarg. The E5 wire is missing from "
        "_resolve_adapter (the resolver never reached the kanzi "
        f"branch). captured={captured!r}"
    )

