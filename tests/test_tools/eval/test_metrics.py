"""Tests for tools/eval/metrics.py — per-model real-ckpt metric dispatch (FlowMol3, Kanzi, LineageFlow).

Wave 104 P2-A: split from tests/test_tools/test_run_real_ckpt_eval.py
(2409 LOC → 6 sub-files mirroring tools/eval/). All 23 tests preserved
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
    from adaptive_reflow.adapters.flowmol3_v2_adapter import (
        FlowMol3V2Adapter,
    )
    from adaptive_reflow.framework.interfaces import ObservationKind
    from adaptive_reflow.universal.state import ODEConditionDelta

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


# ---------------------------------------------------------------------------
# 6. Wave 69 Phase 2 — FlowMol3 composite chemistry wire fix
# ---------------------------------------------------------------------------
#
# The Wave 69 Phase 1 audit identified
# ``tools/run_real_ckpt_eval.py:_compute_flowmol3_composite`` (lines
# 3122-3127 of the pre-fix tree) as the root cause of the closure
# sweep's `composite.chemistry_input = 0.0` anomaly: the function
# hard-coded the chemistry dict to zeros and never invoked
# ``FlowMol3Glue.compute_chemistry_metrics``.
#
# Wave 69 Phase 2 fix: the function now accepts an optional
# ``sampled_molecules`` kwarg (interface-first; default ``None``
# preserves all existing callers byte-stable). When supplied, it
# delegates to ``FlowMol3Glue.compute_chemistry_metrics`` and merges
# the real upstream readings into the chemistry stub. When the
# upstream ``flowmol`` / RDKit stack is unavailable, the function
# surfaces ``marker="degraded_chemistry"`` rather than fabricating
# ``marker="computed"`` with a zero reading.
#
# These two regression tests lock in the new contract:
#  - Legacy callers (``sampled_molecules=None``) surface
#    ``marker="degraded_chemistry"`` with ``chemistry_input_source``
#    set to ``"neutral_zero_stub"``.
#  - When ``sampled_molecules`` is supplied AND the upstream is
#    available, the function delegates and merges; when unavailable,
#    it still surfaces ``marker="degraded_chemistry"`` with
#    ``chemistry_input_source`` set to
#    ``"neutral_zero_stub_degraded"``.


def test_flowmol3_composite_legacy_caller_surfaces_degraded_chemistry() -> None:
    """`_compute_flowmol3_composite` (no sampled_molecules) → ``marker='degraded_chemistry'``.

    The Phase 1 audit §3.3 byte-stable contract: legacy callers (no
    ``sampled_molecules`` supplied) MUST surface
    ``marker="degraded_chemistry"`` (not ``"computed"``) because
    the upstream ``flowmol`` / RDKit stack is not importable on this
    venv. The composite value itself stays non-zero (the geometry
    axis + chemistry-stub renormalisation contribute), but the
    marker no longer fabricates a "computed" verdict for a degraded
    reading.
    """
    tools = _import_tools_module()
    from adaptive_reflow.adapters.flowmol3 import default_flowmol3_adapter

    adapter = default_flowmol3_adapter(force_mode="synthetic")
    trace = _make_placeholder_trace(adapter)

    # Legacy caller contract — no ``sampled_molecules`` kwarg.
    composite_value, marker, dbg = tools._compute_flowmol3_composite(
        adapter=adapter,
        baseline_trace=trace,
        framework_trace=trace,
        seed=42,
        nfe=10,
    )

    assert marker == "degraded_chemistry", (
        f"expected marker='degraded_chemistry' for legacy caller "
        f"(Phase 1 audit §3.3 contract), got {marker!r} with dbg={dbg!r}"
    )
    assert isinstance(composite_value, float), (
        f"expected composite_value is float, got "
        f"{type(composite_value).__name__}: {composite_value!r}"
    )
    # Byte-stable: debug dict carries the new chemistry_input_source
    # field that distinguishes the legacy stub from the
    # compute_chemistry_metrics path.
    assert dbg["chemistry_input_source"] == "neutral_zero_stub"
    assert "chemistry_input" in dbg
    assert "chemistry_compute_keys" not in dbg  # no upstream call attempted
    # Glue-class echo fields unchanged (Wave 49 / Wave 54 baseline).
    assert dbg["glue_class"] == "FlowMol3Glue"


def test_flowmol3_composite_with_sampled_molecules_invokes_glue() -> None:
    """`_compute_flowmol3_composite(sampled_molecules=...)` invokes ``FlowMol3Glue.compute_chemistry_metrics``.

    The Phase 2 fix wires the captured trajectory → RDKit molecule →
    upstream ``SampleAnalyzer.analyze`` path via
    :meth:`FlowMol3Glue.compute_chemistry_metrics`. On a venv where
    ``flowmol`` is not importable, the glue returns ``{}`` and the
    function surfaces ``marker="degraded_chemistry"`` with
    ``chemistry_input_source="neutral_zero_stub_degraded"`` plus a
    ``chemistry_compute_error`` field. On a venv where ``flowmol`` IS
    importable, the function merges the upstream readings and
    surfaces ``marker="computed"`` with
    ``chemistry_input_source="compute_chemistry_metrics"``.
    """
    tools = _import_tools_module()
    from adaptive_reflow.adapters.flowmol3 import default_flowmol3_adapter

    adapter = default_flowmol3_adapter(force_mode="synthetic")
    trace = _make_placeholder_trace(adapter)

    # Supply a non-empty sequence; the glue will attempt to call
    # compute_chemistry_metrics on the placeholder list. On a venv
    # without RDKit/flowmol, this returns ``{}`` and the function
    # falls back to ``marker='degraded_chemistry'``. On a venv with
    # RDKit/flowmol available, the function merges the real upstream
    # readings and surfaces ``marker='computed'``.
    sampled_molecules: list[Any] = [object()]  # any sequence works
    composite_value, marker, dbg = tools._compute_flowmol3_composite(
        adapter=adapter,
        baseline_trace=trace,
        framework_trace=trace,
        seed=42,
        nfe=10,
        sampled_molecules=sampled_molecules,
    )

    # Marker depends on upstream availability — verify one of the two
    # documented branches, not both.
    assert marker in ("computed", "degraded_chemistry"), (
        f"marker must be one of the two documented values, got "
        f"{marker!r} with dbg={dbg!r}"
    )
    assert isinstance(composite_value, float)
    # ``chemistry_input_source`` is the new audit field that records
    # which path produced the chemistry dict (Phase 1 audit §3.3
    # byte-stable contract — additive, does not collide with the
    # existing ``chemistry_input`` / ``geometry_input`` /
    # ``xtb_present`` fields).
    assert "chemistry_input_source" in dbg, (
        f"dbg must carry chemistry_input_source (Phase 1 audit §3.3), "
        f"got keys={sorted(dbg.keys())!r}"
    )
    assert dbg["chemistry_input_source"] in (
        "compute_chemistry_metrics",
        "neutral_zero_stub_degraded",
        "neutral_zero_stub",
    ), (
        f"chemistry_input_source must be one of the 3 documented "
        f"values, got {dbg['chemistry_input_source']!r}"
    )
    # Either we got real upstream readings (chemistry_compute_keys
    # populated) OR we got the degraded stub (chemistry_compute_error
    # field present on failure OR chemistry_input_source is the
    # degraded variant). Verify ONE of these branches.
    if dbg["chemistry_input_source"] == "compute_chemistry_metrics":
        assert "chemistry_compute_keys" in dbg
        assert isinstance(dbg["chemistry_compute_keys"], list)
        assert marker == "computed"
    else:
        # degraded / legacy stub path
        assert marker == "degraded_chemistry"



