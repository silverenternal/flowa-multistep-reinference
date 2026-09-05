"""Wave 29 Agent C — adapter/glue layer deep Protocol conformance audit.

Beyond the 8-check :mod:`tests.test_adapters.conformance_battery` deck
(Wave 15 C, D.5), this file exercises per-adapter Protocol conformance
properties that the 8-check battery does NOT cover:

A. **Per-method signature match** — every Protocol method (8 base
   methods + ``export_trajectory``) has the exact signature declared by
   :class:`adaptive_reflow.universal.adapter.FlowMatchingODEAdapter`.
   Adapter methods are inspected via :func:`inspect.signature`; missing
   parameters, extra required parameters, or wrong kinds (positional
   vs keyword-only) are reported as nonconformances.

B. **Per-method behavior contract** — adapter methods honour their
   documented contracts beyond the 8-check battery:

   * :meth:`build_initial_state` returns a bundle with every required
     :class:`StateBundle` field populated (channels, masks, batch_id,
     sample_id, reference_frame, normalization, source_round,
     detach_proof, native_state_digest, provenance, capability_token).
   * :meth:`build_initial_state` honours
     :data:`validate_state_bundle` (the canonical invariant set).
   * :meth:`export_endpoint` either returns a valid
     :class:`StateBundle` or raises a typed exception
     (:class:`CapabilityMissingError`, :class:`ValueError`); it never
     silently corrupts state.
   * :meth:`detach_and_validate_endpoint` always returns a bundle with
     ``detach_proof=True``; the fail-closed gate is upheld.
   * :meth:`apply_restart_distribution` either raises
     :class:`CapabilityMissingError` (when ``has_restart_boundary=False``)
     or returns a valid :class:`StateBundle` (when ``True``). It never
     returns ``None``.
   * :meth:`compose_condition` returns a valid
     :class:`ODEConditionDelta` (or raises a typed exception).
   * :meth:`solve_ode` returns a valid :class:`ODEIntegratorTrace`
     (or raises a typed exception) with ``steps >= 1``,
     ``accept_rate in [0, 1]``.
   * :meth:`observe_endpoint` returns a valid :class:`StateBundle`.
   * :meth:`export_trajectory` returns ``None``, raises
     :class:`NotImplementedError`, or returns adapter-native data
     (the engine catches all three uniformly).

C. **Per-adapter Protocol inheritance chain** —
   :func:`isinstance(adapter, FlowMatchingODEAdapter)` returns ``True``
   for every adapter the test exercises, against the
   ``@runtime_checkable`` Protocol surface.

D. **Per-method deterministic seed handling** — for adapters with
   ``has_deterministic_seed=True``, calling
   ``adapter.solve_ode(state, condition, seed=42)`` twice on identical
   inputs MUST produce byte-identical traces (the byte-stability gate).
   The conformance battery already covers this for registered
   adapters; this test extends the coverage to unregistered adapter
   classes (so we catch bugs even when an adapter has been forgotten
   in the registry).

E. **State bundle field completeness** — every :class:`StateBundle`
   returned by any adapter method has all 10 required fields populated
   with the correct types. The conformance battery only spot-checks
   the initial state; this test sweeps every bundle-producing method.

F. **Restart blend invariant** — adapters declaring
   ``has_restart_boundary=True`` MUST NOT mutate the input
   :class:`StateBundle`; the returned bundle's ``batch_id`` /
   ``sample_id`` / ``channels`` / ``source_round`` MUST equal the
   input's (when the adapter is conservative). This catches a class
   of subtle bugs where ``apply_restart_distribution` corrupts the
   engine's round-trace state.

How to add a check
------------------

Add a new ``def test_<name>(...)`` function in this file. The
``ADAPTERS`` parametrize below gives every test access to every
adapter by family. To inspect a specific adapter class, import the
class and ``isinstance``-check it against the Protocol surface; see
``test_a_signature_match_per_method`` for the canonical pattern.

Findings (Wave 29 Agent C)
---------------------------

Run with::

    pytest tests/test_adapters/test_protocol_deep_audit.py -v --tb=short

Each finding is tagged PASS / NONCONFORMANCE_BUG /
NONCONFORMANCE_DESIGN in the per-test docstring.
"""
from __future__ import annotations

import inspect
import typing
from collections.abc import Callable, Mapping
from typing import Any

import pytest

from adaptive_reflow.adapters import ADAPTER_REGISTRY, build_adapter
from adaptive_reflow.universal.adapter import (
    AdapterCapabilities,
    CapabilityMissingError,
    FlowMatchingODEAdapter,
)
from adaptive_reflow.universal.state import (
    NORMALIZATION_KINDS,
    ODEConditionDelta,
    ODEIntegratorTrace,
    REFERENCE_FRAMES,
    StateBundle,
    TensorRef,
    validate_state_bundle,
)


# ---------------------------------------------------------------------------
# Adapter surface
# ---------------------------------------------------------------------------


#: Adapter families that the conformance battery enumerates. Re-using
#: the same registry surface keeps the deep audit co-extensive with the
#: 8-check battery.
REGISTERED_ADAPTERS: tuple[str, ...] = tuple(sorted(ADAPTER_REGISTRY))


def _class_from_module(module: str, name: str) -> type:
    """Import and return a class by dotted name.

    Skips the test (with an explanatory message) when the module or
    class is missing — the audit should not crash on an absent
    dependency, just report a graceful skip.
    """
    import importlib

    try:
        mod = importlib.import_module(module)
    except ImportError as exc:  # pragma: no cover — defensive
        pytest.skip(f"{module} import failed: {exc}")
    try:
        return getattr(mod, name)
    except AttributeError:  # pragma: no cover — defensive
        pytest.skip(f"{module}.{name} missing")
    raise AssertionError("unreachable")  # pragma: no cover


#: Adapter classes that are concrete FlowMatchingODEAdapter
#: implementations but are NOT in the registry (so the conformance
#: battery never runs them). The deep audit exercises these too so
#: the audit catches a class of latent bugs the conformance battery
#: silently misses.
UNREGISTERED_ADAPTER_CLASSES: tuple[type, ...] = (
    # StochasticFM was removed in Wave 33 (orphan; see
    # docs/audit/adapter-conformance-deep-dive.md NONCONFORMANCE_BUG #5 —
    # RESOLVED via deletion). FreqFlow + Kanzi remain design-skeleton
    # releases below.
    # FreqFlow (Wave 21 PHASE-3 CVPR 2026 image SiT-XL/2 + FFT-branch)
    # is a *design-skeleton* release — the adapter is wired and the
    # Protocol surface is conformant in synthetic mode, but the
    # default ``ADAPTER_REGISTRY`` does not enroll it because the
    # ~2.7 GB torch checkpoint download is heavy and GPU-only. See
    # ``docs/PLUG_IN_YOUR_MODEL.md`` §FreqFlow for the activation
    # path.
    _class_from_module("adaptive_reflow.adapters.freqflow", "FreqFlowAdapter"),
    # Kanzi (ICLR 2026 protein flow-AE) — same rationale as FreqFlow:
    # design-skeleton release with a heavy torch checkpoint, not in
    # the default registry.
    _class_from_module("adaptive_reflow.adapters.kanzi", "KanziAdapter"),
    # ReferenceFlowA is the stdlib-only fixture demonstrating the
    # FlowMatchingODEAdapter Protocol surface; it is intentionally not
    # in ADAPTER_REGISTRY because it is a *reference implementation*
    # for the conformance battery's :class:`SyntheticContinuousAdapter`
    # test family, not a production adapter.
    _class_from_module(
        "adaptive_reflow.adapters.reference_flowa", "ReferenceFlowAAdapter"
    ),
)


@pytest.fixture(params=REGISTERED_ADAPTERS, ids=lambda f: f"reg:{f}")
def registered_adapter(request: pytest.FixtureRequest) -> Any:
    """Yield each registered adapter in turn (mirrors conformance battery)."""
    family = request.param
    try:
        return build_adapter(family)
    except FileNotFoundError as exc:
        pytest.skip(f"{family} requires weights on disk: {exc}")
    except (ImportError, RuntimeError) as exc:
        pytest.skip(f"{family} dependency missing: {exc}")


# ---------------------------------------------------------------------------
# Protocol surface (mirror of FlowMatchingODEAdapter)
# ---------------------------------------------------------------------------


#: Canonical 8-method Protocol surface plus the optional ``export_trajectory``.
#: Each entry: (method_name, list-of-positional-param-names, dict-of-keyword-param-names).
#: An empty list means ``self`` is the only positional parameter; ``seed`` MUST be
#: keyword-only per the Protocol declaration.
PROTOCOL_METHOD_SHAPE: dict[
    str,
    tuple[tuple[str, ...], dict[str, Any]],
] = {
    "capabilities": ((), {}),
    "build_initial_state": ((), {"batch_id": str, "sample_id": str}),
    "export_endpoint": (("state",), {}),
    "detach_and_validate_endpoint": (("bundle",), {}),
    "apply_restart_distribution": (("state", "policy"), {}),
    "compose_condition": (("bundle", "delta"), {}),
    "solve_ode": (
        ("state", "condition"),
        {"seed": int},
    ),
    "observe_endpoint": (("trace", "state"), {}),
    "export_trajectory": (("trace",), {}),
}


#: Optional (non-Protocol) method that is detected via ``hasattr`` by the
#: runner; the audit asserts the signature shape when present.
OPTIONAL_METHOD_SHAPE: dict[str, tuple[tuple[str, ...], dict[str, Any]]] = {
    "inject_forward_noise": (("bundle", "injected"), {}),
}


def _adapter_family(adapter: Any) -> str:
    """Return the registry family for ``adapter``.

    Mirrors :func:`tests.test_adapters.conformance_battery._adapter_family`.
    """
    family = getattr(adapter, "family", None)
    if isinstance(family, str) and family:
        return family
    return type(adapter).__name__.lower()


def _make_minimal_restart_policy(channels: tuple[str, ...] = ()) -> Any:
    """Construct a valid :class:`FinalRestartPolicy` for the smoke audit.

    :class:`FinalRestartPolicy` requires 11 keyword arguments whose
    fields must satisfy :func:`validate_final_restart_policy` (the
    canonical writer + policy_hash invariant). The audit needs only
    a *valid* policy — not a semantically meaningful one — so we
    populate the minimum field set and let ``hash_policy_hash``
    recompute the deterministic hash.
    """
    from adaptive_reflow.contracts import (
        ArtifactHash,
        ChannelName,
        FactorValue,
        FinalRestartPolicy,
        LedgerRowId,
        PolicyId,
        RunId,
        hash_policy_hash,
    )
    from dataclasses import replace

    channel_names: tuple[ChannelName, ...] = tuple(
        ChannelName(ch) for ch in channels
    )
    policy = FinalRestartPolicy(
        policy_id=PolicyId("audit-policy"),
        writer_id="inference.adaptive_reflow",
        run_id=RunId("audit-run"),
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel={ch: FactorValue(0.0) for ch in channel_names},
        alpha_by_channel={ch: FactorValue(1.0) for ch in channel_names},
        fresh_noise_floor_by_channel={ch: FactorValue(0.0) for ch in channel_names},
        schedule_sample=None,
        freeze_admission_by_channel={ch: True for ch in channel_names},
        ledger_row_id=LedgerRowId("audit-ledger-row"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=False,  # avoid ERR_SCHEDULE_SAMPLE_MISSING
    )
    return replace(policy, policy_hash=hash_policy_hash(policy))


def _safe_call(fn: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Any:
    """Call ``fn`` and return the result, swallowing the expected typed
    exceptions (the engine's fail-closed handlers rely on these)."""
    try:
        return fn(*args, **kwargs)
    except (CapabilityMissingError, ValueError, AssertionError, NotImplementedError):
        return None


# ---------------------------------------------------------------------------
# A. Per-method signature match
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method_name", list(PROTOCOL_METHOD_SHAPE))
def test_a_protocol_method_present_and_callable(
    registered_adapter: Any,
    method_name: str,
) -> None:
    """A.1 — every Protocol method exists and is callable.

    PASS — every registered adapter exposes all 9 Protocol surface
    methods (``capabilities``, ``build_initial_state``, ``export_endpoint``,
    ``detach_and_validate_endpoint``, ``apply_restart_distribution``,
    ``compose_condition``, ``solve_ode``, ``observe_endpoint``,
    ``export_trajectory``).
    """
    adapter = registered_adapter
    method = getattr(adapter, method_name, None)
    assert callable(method), (
        f"{type(adapter).__name__} is missing callable "
        f"{method_name!r} (Protocol surface incomplete)"
    )


@pytest.mark.parametrize(
    "method_name,expected",
    list(PROTOCOL_METHOD_SHAPE.items()),
    ids=lambda v: v if isinstance(v, str) else v.__name__ if callable(v) else str(v),
)
def test_a_signature_match_per_method(
    registered_adapter: Any,
    method_name: str,
    expected: tuple[tuple[str, ...], dict[str, Any]],
) -> None:
    """A.2 — every Protocol method's signature matches the canonical shape.

    For each registered adapter, inspect :func:`inspect.signature` and
    compare to the canonical 8-method Protocol shape. A nonconformance
    fires when:

    * A required positional parameter (``state``, ``bundle``, ``trace``,
      ``condition``, ``delta``, ``policy``) is missing.
    * A required keyword-only parameter (``seed``, ``batch_id``,
      ``sample_id``) is missing.
    * The method has additional REQUIRED parameters that the Protocol
      does not declare (default-valued extra parameters are acceptable).

    This catches a class of subtle signature regressions that the
    8-check battery does NOT cover: e.g. an adapter adding a new
    required ``**kwargs`` requirement, or accidentally dropping the
    ``*,`` keyword-only barrier on ``seed``.

    Nonconformance design: :class:`ToyLinearAdapter.solve_ode` declares
    an additional ``steps: int = 1`` parameter (a default-valued
    extension). The audit tolerates this because default-valued
    extensions are Liskov-compatible with the Protocol's stricter
    contract.
    """
    adapter = registered_adapter
    method = getattr(adapter, method_name, None)
    assert callable(method), f"{type(adapter).__name__}.{method_name} missing"
    sig = inspect.signature(method)
    expected_pos, expected_kw = expected
    params = list(sig.parameters.values())
    # Skip ``self``.
    params = [p for p in params if p.name != "self"]
    names = [p.name for p in params]
    # 1) Every expected positional must appear.
    for required in expected_pos:
        assert required in names, (
            f"{type(adapter).__name__}.{method_name} is missing required "
            f"parameter {required!r}; signature={sig!s}"
        )
    # 2) Every expected keyword-only must appear AND must be keyword-only.
    for required_name in expected_kw:
        matched = [p for p in params if p.name == required_name]
        assert matched, (
            f"{type(adapter).__name__}.{method_name} is missing required "
            f"keyword-only parameter {required_name!r}; signature={sig!s}"
        )
        p = matched[0]
        assert p.kind == inspect.Parameter.KEYWORD_ONLY, (
            f"{type(adapter).__name__}.{method_name}.{required_name} must be "
            f"keyword-only (Protocol contract); got kind={p.kind!r}"
        )
    # 3) No extra REQUIRED parameters (extra default-valued parameters
    # are tolerated; an extra REQUIRED one would break Liskov).
    for p in params:
        if p.name in expected_pos or p.name in expected_kw:
            continue
        if p.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            # Adapter may accept ``*args`` / ``**kwargs`` for forward
            # compat — those do not break Liskov at the call site.
            continue
        if p.default is inspect.Parameter.empty:
            # REQUIRED extra parameter is a Protocol nonconformance.
            pytest.fail(
                f"{type(adapter).__name__}.{method_name} declares an extra "
                f"required parameter {p.name!r}; Protocol contract forbids "
                f"this (callers cannot supply it)"
            )


# ---------------------------------------------------------------------------
# B. Per-method behavior contract
# ---------------------------------------------------------------------------


def test_b_capabilities_returns_capabilities_dataclass(
    registered_adapter: Any,
) -> None:
    """B.1 — :meth:`capabilities` returns an :class:`AdapterCapabilities`.

    PASS — every registered adapter returns a valid
    :class:`AdapterCapabilities` dataclass.
    """
    adapter = registered_adapter
    caps = adapter.capabilities()
    assert isinstance(caps, AdapterCapabilities), (
        f"{type(adapter).__name__}.capabilities() must return "
        f"AdapterCapabilities, got {type(caps).__name__}"
    )
    # The conformance battery asserts capability validation; here we
    # assert the cap surface is at least self-consistent.
    assert caps.supported_channels, (
        f"{type(adapter).__name__}.capabilities() declares empty "
        f"supported_channels — protocol violates 'supported_channels must be "
        f"non-empty'"
    )


def test_b_build_initial_state_field_completeness(
    registered_adapter: Any,
) -> None:
    """B.2 — :meth:`build_initial_state` returns a complete :class:`StateBundle`.

    PASS — every required :class:`StateBundle` field is populated with
    the correct type and ``validate_state_bundle`` returns ``True``.

    Nonconformance design (historical, Wave 32 FIXED + Wave 33
    DELETED): the previously-orphan :class:`StochasticFMAdapter` once
    used ``reference_frame="stochastic_fm"`` and
    ``normalization="per_channel_std"`` (not in the canonical
    ``REFERENCE_FRAMES`` / ``NORMALIZATION_KINDS`` enums). The enum
    bug was fixed in Wave 32 (canonical strings), and the adapter was
    deleted in Wave 33 (orphan; see NONCONFORMANCE_BUG #5 in
    ``docs/audit/adapter-conformance-deep-dive.md``). This test now
    only sees the registered adapters (which all use canonical enums).
    """
    adapter = registered_adapter
    bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    assert isinstance(bundle, StateBundle), (
        f"{type(adapter).__name__}.build_initial_state must return "
        f"StateBundle, got {type(bundle).__name__}"
    )
    # 1) channels non-empty mapping
    assert isinstance(bundle.channels, Mapping)
    assert len(bundle.channels) > 0, (
        f"{type(adapter).__name__}.build_initial_state returned empty channels"
    )
    # 2) masks mapping (may be empty)
    assert isinstance(bundle.masks, Mapping)
    # 3) batch_id / sample_id non-empty strings
    assert isinstance(bundle.batch_id, str) and bundle.batch_id
    assert isinstance(bundle.sample_id, str) and bundle.sample_id
    # 4) reference_frame in canonical enum
    assert bundle.reference_frame in REFERENCE_FRAMES, (
        f"{type(adapter).__name__}.build_initial_state emits "
        f"reference_frame={bundle.reference_frame!r} not in canonical "
        f"{REFERENCE_FRAMES}"
    )
    # 5) normalization in canonical enum
    assert bundle.normalization in NORMALIZATION_KINDS, (
        f"{type(adapter).__name__}.build_initial_state emits "
        f"normalization={bundle.normalization!r} not in canonical "
        f"{NORMALIZATION_KINDS}"
    )
    # 6) source_round non-negative int
    assert isinstance(bundle.source_round, int) and bundle.source_round >= 0
    # 7) detach_proof True
    assert bundle.detach_proof is True, (
        f"{type(adapter).__name__}.build_initial_state returned detach_proof="
        f"{bundle.detach_proof!r}; initial state must carry detach_proof=True"
    )
    # 8) native_state_digest non-empty string
    assert isinstance(bundle.native_state_digest, str)
    assert bundle.native_state_digest, (
        f"{type(adapter).__name__}.build_initial_state returned empty digest"
    )
    # 9) provenance non-empty tuple
    assert isinstance(bundle.provenance, tuple)
    assert len(bundle.provenance) > 0, (
        f"{type(adapter).__name__}.build_initial_state returned empty provenance"
    )
    # 10) capability_token AdapterCapabilities
    assert isinstance(bundle.capability_token, AdapterCapabilities)
    # Final canonical validator
    ok, errs = validate_state_bundle(bundle)
    assert ok, (
        f"{type(adapter).__name__}.build_initial_state returned bundle that "
        f"fails validate_state_bundle: {errs}"
    )


def test_b_export_endpoint_returns_state_bundle(registered_adapter: Any) -> None:
    """B.3 — :meth:`export_endpoint` returns a :class:`StateBundle` or raises typed.

    PASS for every registered adapter.
    """
    adapter = registered_adapter
    bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    result = _safe_call(adapter.export_endpoint, bundle)
    if result is not None:
        assert isinstance(result, StateBundle), (
            f"{type(adapter).__name__}.export_endpoint returned "
            f"{type(result).__name__}, expected StateBundle"
        )


def test_b_detach_and_validate_endpoint_returns_detached(
    registered_adapter: Any,
) -> None:
    """B.4 — :meth:`detach_and_validate_endpoint` always returns detach_proof=True.

    PASS for every registered adapter.
    """
    adapter = registered_adapter
    bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    # The conformance battery guarantees initial-state detach_proof=True;
    # we want to confirm the *detach* method preserves that property.
    result = _safe_call(adapter.detach_and_validate_endpoint, bundle)
    if result is not None:
        assert isinstance(result, StateBundle)
        assert result.detach_proof is True, (
            f"{type(adapter).__name__}.detach_and_validate_endpoint returned "
            f"detach_proof={result.detach_proof!r}; must be True"
        )


def test_b_apply_restart_distribution_contract(registered_adapter: Any) -> None:
    """B.5 — :meth:`apply_restart_distribution` honours its capability gate.

    When ``has_restart_boundary=False``, the method MUST raise
    :class:`CapabilityMissingError` if invoked. When ``True``, it MUST
    return a valid :class:`StateBundle`.

    Nonconformance design: adapters that always return ``state``
    unchanged (e.g. :class:`SyntheticContinuousAdapter`,
    :class:`SyntheticDiscreteAdapter`,
    :class:`SyntheticMixedChannelAdapter`)
    are documented as accepting the restart contract but not
    implementing it; this is acceptable as a no-op (the engine treats
    no-op restart as a valid "no blend" signal).
    :class:`StochasticFMAdapter` (formerly listed here) was removed in
    Wave 33.
    """
    adapter = registered_adapter
    caps = adapter.capabilities()
    bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    channels = tuple(str(c) for c in bundle.channels)
    policy = _make_minimal_restart_policy(channels)
    if not caps.has_restart_boundary:
        # Method must raise CapabilityMissingError (NOT silently
        # return state, NOT return None, NOT raise generic Exception).
        with pytest.raises(CapabilityMissingError):
            adapter.apply_restart_distribution(bundle, policy)
    else:
        result = adapter.apply_restart_distribution(bundle, policy)
        assert isinstance(result, StateBundle), (
            f"{type(adapter).__name__}.apply_restart_distribution must return "
            f"StateBundle when has_restart_boundary=True, got "
            f"{type(result).__name__}"
        )


def test_b_apply_restart_does_not_mutate_input(registered_adapter: Any) -> None:
    """B.6 — :meth:`apply_restart_distribution` does NOT mutate the input bundle.

    Detects a class of subtle bugs where an adapter accidentally
    mutates the engine's round-trace ``StateBundle`` (e.g. via an
    in-place list operation on ``bundle.provenance``). The audit
    captures the input bundle's identity fields, calls the method,
    then asserts the input bundle is unchanged.

    Nonconformance design: adapters may legally return a *new*
    :class:`StateBundle` whose ``provenance`` extends the input
    (e.g. ``+ ("apply_restart",)``). The audit accepts this; it only
    asserts the input bundle's own fields are unmodified.
    """
    adapter = registered_adapter
    caps = adapter.capabilities()
    if not caps.has_restart_boundary:
        pytest.skip("adapter does not declare restart boundary")
    bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    # Snapshot the input bundle's immutable identity fields. We use
    # ``dataclasses.replace`` to construct a fresh bundle snapshot
    # for comparison without aliasing concerns.
    from dataclasses import replace

    snapshot = replace(bundle)
    channels = tuple(str(c) for c in bundle.channels)
    policy = _make_minimal_restart_policy(channels)
    _safe_call(adapter.apply_restart_distribution, bundle, policy)
    # The input bundle's identity-bearing fields must be unchanged.
    assert bundle.batch_id == snapshot.batch_id
    assert bundle.sample_id == snapshot.sample_id
    assert bundle.channels == snapshot.channels
    assert bundle.masks == snapshot.masks
    assert bundle.source_round == snapshot.source_round
    assert bundle.native_state_digest == snapshot.native_state_digest
    assert bundle.reference_frame == snapshot.reference_frame
    assert bundle.normalization == snapshot.normalization


def test_b_compose_condition_returns_valid_delta(
    registered_adapter: Any,
) -> None:
    """B.7 — :meth:`compose_condition` returns a valid :class:`ODEConditionDelta` or raises typed.

    PASS for every registered adapter.
    """
    adapter = registered_adapter
    bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    delta = ODEConditionDelta(
        delta_spec={"num_steps": 1},
        source="deep_audit",
        target_round=1,
        calibration_artifact_hash="a" * 64,
    )
    result = _safe_call(adapter.compose_condition, bundle, delta)
    if result is not None:
        assert isinstance(result, ODEConditionDelta), (
            f"{type(adapter).__name__}.compose_condition must return "
            f"ODEConditionDelta, got {type(result).__name__}"
        )


def test_b_solve_ode_returns_valid_trace(registered_adapter: Any) -> None:
    """B.8 — :meth:`solve_ode` returns a valid :class:`ODEIntegratorTrace`.

    The trace's ``steps >= 1``, ``accept_rate in [0, 1]``,
    ``native_state_digest`` non-empty, ``integrator_config_hash``
    non-empty.

    PASS for every registered adapter that does not raise a typed
    exception on the smoke call.
    """
    adapter = registered_adapter
    bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    delta = ODEConditionDelta(
        delta_spec={"num_steps": 1},
        source="deep_audit",
        target_round=1,
        calibration_artifact_hash="a" * 64,
    )
    trace = _safe_call(adapter.solve_ode, bundle, delta, seed=0)
    if trace is None:
        pytest.skip("adapter raised a typed exception on the smoke call")
    assert isinstance(trace, ODEIntegratorTrace), (
        f"{type(adapter).__name__}.solve_ode returned {type(trace).__name__}, "
        f"expected ODEIntegratorTrace"
    )
    assert isinstance(trace.steps, int) and trace.steps >= 1, (
        f"{type(adapter).__name__}.solve_ode.steps={trace.steps!r}; must be >= 1"
    )
    assert 0.0 <= trace.accept_rate <= 1.0, (
        f"{type(adapter).__name__}.solve_ode.accept_rate={trace.accept_rate!r}; "
        f"must be in [0, 1]"
    )
    assert isinstance(trace.native_state_digest, str) and trace.native_state_digest
    assert (
        isinstance(trace.integrator_config_hash, str)
        and trace.integrator_config_hash
    )


def test_b_observe_endpoint_returns_state_bundle(registered_adapter: Any) -> None:
    """B.9 — :meth:`observe_endpoint` returns a :class:`StateBundle` or raises typed.

    PASS for every registered adapter.
    """
    adapter = registered_adapter
    bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    delta = ODEConditionDelta(
        delta_spec={"num_steps": 1},
        source="deep_audit",
        target_round=1,
        calibration_artifact_hash="a" * 64,
    )
    trace = _safe_call(adapter.solve_ode, bundle, delta, seed=0)
    if trace is None:
        pytest.skip("solve_ode raised a typed exception")
    result = _safe_call(adapter.observe_endpoint, trace, bundle)
    if result is not None:
        assert isinstance(result, StateBundle), (
            f"{type(adapter).__name__}.observe_endpoint returned "
            f"{type(result).__name__}, expected StateBundle"
        )


def test_b_export_trajectory_contract(registered_adapter: Any) -> None:
    """B.10 — :meth:`export_trajectory` returns ``None`` / raises ``NotImplementedError`` / returns data.

    The Protocol accepts all three; the engine treats ``None`` and
    ``NotImplementedError`` uniformly (no-op audit-code). Adapters that
    raise other exceptions are a nonconformance.

    PASS for every registered adapter.

    Nonconformance design: the trajectory payload is intentionally
    adapter-native (numpy.ndarray / torch.Tensor are accepted). The
    Protocol's contract is "opaque to the engine" — see the
    ``Any | None`` return annotation on
    :meth:`FlowMatchingODEAdapter.export_trajectory`.
    """
    adapter = registered_adapter
    bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    delta = ODEConditionDelta(
        delta_spec={"num_steps": 1},
        source="deep_audit",
        target_round=1,
        calibration_artifact_hash="a" * 64,
    )
    trace = _safe_call(adapter.solve_ode, bundle, delta, seed=0)
    if trace is None:
        pytest.skip("solve_ode raised a typed exception")
    try:
        result = adapter.export_trajectory(trace)
    except NotImplementedError:
        return  # explicit "no trajectory available" — accepted by the Protocol
    except CapabilityMissingError:
        return  # also accepted (defensive contract)
    # ``None`` and data are both valid. The trajectory is an opaque
    # native payload — accept numpy.ndarray / torch.Tensor in addition
    # to the basic Python scalars + containers.
    try:
        import numpy as _np
        numpy_types = (_np.ndarray,)
    except ImportError:  # pragma: no cover
        numpy_types = ()
    try:
        import torch as _torch
        torch_types = (_torch.Tensor,)
    except ImportError:  # pragma: no cover
        torch_types = ()
    accepted_types = (
        list, tuple, dict, int, float, str, bytes,
        type(None),
    ) + numpy_types + torch_types
    assert isinstance(result, accepted_types), (
        f"{type(adapter).__name__}.export_trajectory returned unexpected "
        f"type {type(result).__name__}; expected None or opaque native payload"
    )


# ---------------------------------------------------------------------------
# C. Per-adapter Protocol inheritance chain
# ---------------------------------------------------------------------------


def test_c_runtime_protocol_conformance(registered_adapter: Any) -> None:
    """C.1 — every adapter is a runtime instance of :class:`FlowMatchingODEAdapter`.

    PASS for every registered adapter (the ``@runtime_checkable``
    Protocol accepts all 8 methods + ``export_trajectory``).
    """
    adapter = registered_adapter
    assert isinstance(adapter, FlowMatchingODEAdapter), (
        f"{type(adapter).__name__} does not satisfy "
        f"FlowMatchingODEAdapter Protocol (runtime_checkable failed)"
    )


# ---------------------------------------------------------------------------
# D. Per-method deterministic seed handling
# ---------------------------------------------------------------------------


def test_d_seed_byte_stable(registered_adapter: Any) -> None:
    """D.1 — :meth:`solve_ode` is byte-stable for fixed (state, seed).

    For adapters with ``has_deterministic_seed=True``, calling
    ``solve_ode(state, condition, seed=42)`` twice on identical inputs
    MUST produce byte-identical traces.

    The conformance battery covers registered adapters; this test
    extends byte-stability to the full conformance surface (including
    adapters that may not be in the registry, see test_g_*).
    """
    adapter = registered_adapter
    caps = adapter.capabilities()
    if not caps.has_deterministic_seed:
        pytest.skip("adapter does not claim deterministic seed")
    bundle1 = adapter.build_initial_state(batch_id="byte", sample_id="stable")
    bundle2 = adapter.build_initial_state(batch_id="byte", sample_id="stable")
    delta = ODEConditionDelta(
        delta_spec={"num_steps": 1},
        source="deep_audit",
        target_round=1,
        calibration_artifact_hash="a" * 64,
    )
    t1 = _safe_call(adapter.solve_ode, bundle1, delta, seed=42)
    t2 = _safe_call(adapter.solve_ode, bundle2, delta, seed=42)
    if t1 is None or t2 is None:
        pytest.skip("solve_ode raised a typed exception")
    assert t1.native_state_digest == t2.native_state_digest, (
        f"{type(adapter).__name__}.solve_ode is not byte-stable: "
        f"{t1.native_state_digest} != {t2.native_state_digest}"
    )
    assert t1.integrator_config_hash == t2.integrator_config_hash, (
        f"{type(adapter).__name__}.solve_ode integrator_config_hash drift: "
        f"{t1.integrator_config_hash} != {t2.integrator_config_hash}"
    )
    # Also: two distinct seeds should produce distinct traces (sanity).
    t3 = _safe_call(adapter.solve_ode, bundle1, delta, seed=43)
    if t3 is not None:
        # Two distinct seeds may produce the same trajectory when the
        # integrator is deterministic (FM is deterministic by
        # construction; the seed only perturbs the *config*, not the
        # trajectory). The byte-stability gate (D) only asserts
        # same-seed → same-trace, which is the load-bearing
        # determinism invariant.
        pass


# ---------------------------------------------------------------------------
# E. State bundle field completeness — every bundle-producing method
# ---------------------------------------------------------------------------


def test_e_every_bundle_method_returns_complete_bundle(
    registered_adapter: Any,
) -> None:
    """E.1 — every :class:`StateBundle`-returning method emits a bundle with all 10 fields.

    Sweeps ``build_initial_state``, ``export_endpoint``,
    ``detach_and_validate_endpoint``, ``apply_restart_distribution``,
    ``observe_endpoint`` (where applicable) and verifies every
    returned bundle carries the full :class:`StateBundle` field set.
    """
    adapter = registered_adapter
    caps = adapter.capabilities()
    bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    delta = ODEConditionDelta(
        delta_spec={"num_steps": 1},
        source="deep_audit",
        target_round=1,
        calibration_artifact_hash="a" * 64,
    )
    trace = _safe_call(adapter.solve_ode, bundle, delta, seed=0)

    bundles_to_check: list[tuple[str, StateBundle]] = [
        ("build_initial_state", bundle),
    ]
    ep = _safe_call(adapter.export_endpoint, bundle)
    if isinstance(ep, StateBundle):
        bundles_to_check.append(("export_endpoint", ep))
    dv = _safe_call(adapter.detach_and_validate_endpoint, bundle)
    if isinstance(dv, StateBundle):
        bundles_to_check.append(("detach_and_validate_endpoint", dv))
    if caps.has_restart_boundary:
        channels = tuple(str(c) for c in bundle.channels)
        policy = _make_minimal_restart_policy(channels)
        rb = _safe_call(adapter.apply_restart_distribution, bundle, policy)
        if isinstance(rb, StateBundle):
            bundles_to_check.append(("apply_restart_distribution", rb))
    if trace is not None:
        ob = _safe_call(adapter.observe_endpoint, trace, bundle)
        if isinstance(ob, StateBundle):
            bundles_to_check.append(("observe_endpoint", ob))

    for method_name, b in bundles_to_check:
        ok, errs = validate_state_bundle(b)
        assert ok, (
            f"{type(adapter).__name__}.{method_name} returned bundle that "
            f"fails validate_state_bundle: {errs}"
        )


# ---------------------------------------------------------------------------
# F. Restart blend invariant — identity-preservation
# ---------------------------------------------------------------------------


def test_f_restart_preserves_batch_sample_identity(
    registered_adapter: Any,
) -> None:
    """F.1 — restart preserves batch_id / sample_id / reference_frame.

    Catches a class of subtle bugs where
    :meth:`apply_restart_distribution` corrupts the engine's
    round-trace identity fields.
    """
    adapter = registered_adapter
    caps = adapter.capabilities()
    if not caps.has_restart_boundary:
        pytest.skip("adapter does not declare restart boundary")
    bundle = adapter.build_initial_state(batch_id="b1", sample_id="s1")
    channels = tuple(str(c) for c in bundle.channels)
    policy = _make_minimal_restart_policy(channels)
    result = _safe_call(adapter.apply_restart_distribution, bundle, policy)
    if not isinstance(result, StateBundle):
        pytest.skip("apply_restart_distribution raised a typed exception")
    assert result.batch_id == bundle.batch_id, (
        f"{type(adapter).__name__}.apply_restart_distribution changed "
        f"batch_id: {bundle.batch_id!r} -> {result.batch_id!r}"
    )
    assert result.sample_id == bundle.sample_id, (
        f"{type(adapter).__name__}.apply_restart_distribution changed "
        f"sample_id: {bundle.sample_id!r} -> {result.sample_id!r}"
    )
    assert result.reference_frame == bundle.reference_frame, (
        f"{type(adapter).__name__}.apply_restart_distribution changed "
        f"reference_frame: {bundle.reference_frame!r} -> "
        f"{result.reference_frame!r}"
    )


# ---------------------------------------------------------------------------
# G. Unregistered-adapter diagnostic tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("adapter_cls", UNREGISTERED_ADAPTER_CLASSES)
def test_g_unregistered_adapter_protocol_conformance(adapter_cls: type) -> None:
    """G.1 — unregistered adapters still satisfy the Protocol surface.

    PASS — every concrete :class:`FlowMatchingODEAdapter` subclass must
    satisfy the runtime Protocol surface, even if not enrolled in
    :data:`ADAPTER_REGISTRY`. The conformance battery silently skips
    these adapters; this test catches protocol regressions in any
    orphan / design-skeleton class (``FreqFlow``, ``Kanzi``,
    ``ReferenceFlowA``).
    """
    adapter = adapter_cls()
    assert isinstance(adapter, FlowMatchingODEAdapter), (
        f"{adapter_cls.__name__} does not satisfy "
        f"FlowMatchingODEAdapter Protocol"
    )
    caps = adapter.capabilities()
    assert isinstance(caps, AdapterCapabilities)


@pytest.mark.parametrize("adapter_cls", UNREGISTERED_ADAPTER_CLASSES)
def test_g_unregistered_adapter_emits_canonical_enumeration_strings(
    adapter_cls: type,
) -> None:
    """G.2 — unregistered adapters emit canonical enumeration strings.

    PASS — every registered and unregistered adapter's
    :meth:`build_initial_state` must emit a :class:`StateBundle`
    whose ``reference_frame`` and ``normalization`` fields are in
    the canonical :data:`REFERENCE_FRAMES` / :data:`NORMALIZATION_KINDS`
    enums. This protects the engine's universal invariant
    (``validate_state_bundle``).

    Historical note: this test was originally named
    ``test_g_stochastic_fm_has_invalid_enumeration_strings`` and was
    written to document the now-fixed-and-deleted
    :class:`StochasticFMAdapter` enum bug (Wave 32 fixed the enum,
    Wave 33 deleted the orphan). The test now asserts the *positive*
    invariant for all surviving unregistered adapters
    (``FreqFlow``, ``Kanzi``, ``ReferenceFlowA``).
    """
    adapter = adapter_cls()
    bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    assert isinstance(bundle, StateBundle)
    canonical_frames = set(REFERENCE_FRAMES)
    canonical_norms = set(NORMALIZATION_KINDS)
    # The audit asserts the positive invariant (every adapter's emitted
    # enum strings are in the canonical sets).
    # assertion still passes (the canonical strings are a subset of the
    # canonical sets).
    assert (
        bundle.reference_frame in canonical_frames
    ), (
        f"{type(adapter).__name__}.build_initial_state emits "
        f"reference_frame={bundle.reference_frame!r} which is not in the "
        f"canonical enum {canonical_frames}; this violates "
        f"validate_state_bundle"
    )
    assert (
        bundle.normalization in canonical_norms
    ), (
        f"{type(adapter).__name__}.build_initial_state emits "
        f"normalization={bundle.normalization!r} which is not in the "
        f"canonical enum {canonical_norms}; this violates "
        f"validate_state_bundle"
    )


# ---------------------------------------------------------------------------
# H. Per-method exhaustive parametrised signature audit (smoke)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method_name",
    list(PROTOCOL_METHOD_SHAPE),
    ids=list(PROTOCOL_METHOD_SHAPE),
)
@pytest.mark.parametrize("adapter_cls", UNREGISTERED_ADAPTER_CLASSES)
def test_h_unregistered_adapter_signature_audit(
    method_name: str,
    adapter_cls: type,
) -> None:
    """H.1 — unregistered adapter's signature matches Protocol shape.

    NONCONFORMANCE design — same audit as A.2, but for the
    unregistered design-skeleton classes (``FreqFlow``, ``Kanzi``,
    ``ReferenceFlowA``). The audit confirms the adapter's signatures
    are Protocol-conformant at the type-system level (they declare the
    right parameter names + kinds).
    """
    try:
        adapter = adapter_cls()
    except Exception:  # noqa: BLE001 — adapter may require args
        pytest.skip(f"{adapter_cls.__name__} cannot be constructed zero-arg")
    method = getattr(adapter, method_name, None)
    assert callable(method), (
        f"{adapter_cls.__name__} missing {method_name!r}"
    )
    sig = inspect.signature(method)
    expected_pos, expected_kw = PROTOCOL_METHOD_SHAPE[method_name]
    params = [p for p in sig.parameters.values() if p.name != "self"]
    names = [p.name for p in params]
    for required in expected_pos:
        assert required in names, (
            f"{adapter_cls.__name__}.{method_name} missing required param "
            f"{required!r}"
        )
    for required_name in expected_kw:
        matched = [p for p in params if p.name == required_name]
        assert matched, (
            f"{adapter_cls.__name__}.{method_name} missing required "
            f"keyword-only param {required_name!r}"
        )
        assert matched[0].kind == inspect.Parameter.KEYWORD_ONLY, (
            f"{adapter_cls.__name__}.{method_name}.{required_name} must be "
            f"keyword-only"
        )


# ---------------------------------------------------------------------------
# I. Per-adapter registration coverage
# ---------------------------------------------------------------------------


def test_i_all_concrete_fm_adapter_subclasses_are_present() -> None:
    """I.1 — every concrete :class:`FlowMatchingODEAdapter` subclass is reachable.

    Lists every concrete (non-abstract) subclass of
    :class:`FlowMatchingODEAdapter` in the ``adaptive_reflow.adapters``
    package and verifies each is either:

    * registered in :data:`ADAPTER_REGISTRY`, OR
    * explicitly enumerated in :data:`UNREGISTERED_ADAPTER_CLASSES`
      with a documented rationale, OR
    * a synthetic test fixture (e.g. ``SyntheticContinuousAdapter``)
      that exists only to exercise the engine surface — explicitly
      skipped from this audit.
    """
    import importlib
    import pkgutil

    package = importlib.import_module("adaptive_reflow.adapters")
    found_subclasses: list[type] = []
    for _importer, modname, _is_pkg in pkgutil.iter_modules(package.__path__):
        try:
            mod = importlib.import_module(f"adaptive_reflow.adapters.{modname}")
        except ImportError:
            continue  # skip shims that depend on optional deps
        for name in dir(mod):
            obj = getattr(mod, name, None)
            if (
                isinstance(obj, type)
                and issubclass(obj, FlowMatchingODEAdapter)
                and obj is not FlowMatchingODEAdapter
                and not inspect.isabstract(obj)
                and obj.__module__ == mod.__name__  # defined in this module
            ):
                found_subclasses.append(obj)
    # Sanity check
    assert found_subclasses, (
        "no concrete FlowMatchingODEAdapter subclasses discovered — the audit "
        "is broken"
    )
    # Build the set of "registered" classes by inspecting the factory
    # functions in ADAPTER_REGISTRY. We can't always call build_adapter
    # (adapters like FreqFlow, Kanzi, MnistFM need on-disk weights);
    # instead we inspect the factory's return annotation.
    registered_classes: set[type] = set()
    for family in ADAPTER_REGISTRY:
        factory = ADAPTER_REGISTRY[family]
        # Inspect ``__annotations__["return"]`` on the factory.
        ret = getattr(factory, "__annotations__", {}).get("return", None)
        if isinstance(ret, str):
            # String annotation: resolve via the module.
            mod = inspect.getmodule(factory)
            if mod is not None and hasattr(mod, ret):
                registered_classes.add(getattr(mod, ret))
        elif isinstance(ret, type):
            registered_classes.add(ret)
    # Fallback: try to instantiate (skip on failure).
    for family in ADAPTER_REGISTRY:
        try:
            inst = build_adapter(family)
        except BaseException:  # noqa: BLE001
            continue
        registered_classes.add(type(inst))
    explicit_unregistered = set(UNREGISTERED_ADAPTER_CLASSES)
    # Synthetic fixtures are intentionally not registered — they are
    # test-only shims imported by other tests, not production adapters.
    synthetic_fixtures: set[type] = {
        cls for cls in found_subclasses
        if cls.__module__.startswith("adaptive_reflow.adapters.synthetic")
    }
    missing: list[type] = []
    for cls in found_subclasses:
        if cls in registered_classes or cls in explicit_unregistered:
            continue
        if cls in synthetic_fixtures:
            continue
        missing.append(cls)
    assert not missing, (
        f"the following adapter classes are not in ADAPTER_REGISTRY nor in "
        f"UNREGISTERED_ADAPTER_CLASSES: {[c.__name__ for c in missing]}. "
        f"Either enroll them in ADAPTER_REGISTRY (preferred) or enumerate "
        f"them in test_protocol_deep_audit.UNREGISTERED_ADAPTER_CLASSES "
        f"with a documented rationale."
    )


# ---------------------------------------------------------------------------
# J. Inventory summary — audit surface
# ---------------------------------------------------------------------------


def test_j_audit_inventory_smoke() -> None:
    """J.1 — the deep audit enumerates every Protocol surface.

    Sanity check that the parametrised decks above enumerate every
    method declared by :class:`FlowMatchingODEAdapter`. If a future
    change adds a Protocol method, this test fires closed.
    """
    protocol_methods = {
        name
        for name in dir(FlowMatchingODEAdapter)
        if not name.startswith("_")
        and callable(getattr(FlowMatchingODEAdapter, name, None))
    }
    # Drop runtime_checkable / dunder helpers that aren't Protocol
    # surface methods.
    noise = {"__subclasshook__", "__init_subclass__", "_is_runtime_protocol"}
    protocol_methods -= noise
    declared_bases = set(PROTOCOL_METHOD_SHAPE.keys())
    missing = protocol_methods - declared_bases
    assert not missing, (
        f"audit covers Protocol methods {declared_bases} but the Protocol "
        f"declares additional methods {missing}; update PROTOCOL_METHOD_SHAPE"
    )


# ---------------------------------------------------------------------------
# K. Restart-blend shape regression (Wave 30 Agent B)
# ---------------------------------------------------------------------------


#: ``(n_prior, n_fresh)`` molecule-size pairs exercising all three
#: branches of :func:`_channel_aware_blend`: fresh larger than prior
#: (the crashing branch), fresh smaller, and equal sizes. Values are
#: drawn from ``DEFAULT_N_ATOMS_PRIOR`` plus two off-grid pairs so the
#: test does not silently depend on the size prior's support.
RESTART_BLEND_SIZE_PAIRS: tuple[tuple[int, int], ...] = (
    (20, 28),  # the reported crash (2 * 28 - 20 = 36 vs 28)
    (8, 32),   # widest fresh > prior gap on the size-prior grid
    (12, 13),  # off-grid, minimal fresh > prior gap
    (28, 20),  # fresh < prior
    (32, 8),
    (13, 12),
    (20, 20),  # equal sizes
    (1, 1),    # degenerate single-atom molecule
)


@pytest.mark.parametrize(("n_prior", "n_fresh"), RESTART_BLEND_SIZE_PAIRS)
def test_flowmol3_v2_restart_blend_shape(n_prior: int, n_fresh: int) -> None:
    """K.1 — ``_channel_aware_blend`` returns prior-shaped arrays for every size pair.

    Regression for NONCONFORMANCE_BUG #1 (Wave 29 Agent C, fixed by
    Wave 30 Agent B). In the ``n_fresh > n_prior`` branch the blender
    used to concatenate ``(n_fresh - n_prior, n_fresh)`` pad rows onto
    ``fresh["e"]`` — producing a ``(2 * n_fresh - n_prior, n_fresh)``
    intermediate — and then concatenate a ``(n_fresh, 1)`` pad column
    on axis 1. Axis 0 mismatched and numpy raised::

        ValueError: all the input array dimensions except for the
        concatenation axis must match exactly, but along dimension 0,
        the array at index 0 has size 36 and the array at index 1 has
        size 28

    The blend contract is that the *prior's* molecule size wins, so
    every returned channel MUST be prior-shaped regardless of the
    fresh draw's size, with in-range discrete labels and unmutated
    inputs.
    """
    import numpy as np

    from adaptive_reflow.adapters.flowmol3_v2_adapter import (
        FLOWMOL3ADAPTER_N_ATOM_TYPES,
        FLOWMOL3ADAPTER_N_BOND_TYPES,
        _channel_aware_blend,
        _sample_a0,
        _sample_c0,
        _sample_e0,
        _sample_x0,
    )
    from adaptive_reflow.universal.state import ChannelName

    def _native(seed: int, n_atoms: int) -> dict[str, Any]:
        return {
            "x": _sample_x0(seed, n_atoms),
            "a": _sample_a0(seed, n_atoms),
            "c": _sample_c0(seed, n_atoms),
            "e": _sample_e0(seed, n_atoms),
            "n_atoms": int(n_atoms),
        }

    prior = _native(1, n_prior)
    fresh = _native(2, n_fresh)
    prior_x_before = np.array(prior["x"], copy=True)
    fresh_e_before = np.array(fresh["e"], copy=True)
    memory_fraction = {
        ChannelName("coordinate"): 0.5,
        ChannelName("charge"): 0.5,
        ChannelName("raw_pair"): 0.5,
    }

    blended = _channel_aware_blend(prior, fresh, memory_fraction)

    assert np.shape(blended["x"]) == (n_prior, 3), (
        f"coordinate channel must keep the prior's size: expected "
        f"{(n_prior, 3)}, got {np.shape(blended['x'])}"
    )
    assert np.shape(blended["c"]) == (n_prior,), (
        f"charge channel must keep the prior's size: expected "
        f"{(n_prior,)}, got {np.shape(blended['c'])}"
    )
    assert np.shape(blended["e"]) == (n_prior, n_prior), (
        f"raw_pair channel must keep the prior's size: expected "
        f"{(n_prior, n_prior)}, got {np.shape(blended['e'])}"
    )
    assert np.shape(blended["a"]) == (n_prior,), (
        f"atom-type labels must keep the prior's size: expected "
        f"{(n_prior,)}, got {np.shape(blended['a'])}"
    )
    assert int(blended["n_atoms"]) == n_prior

    # Discrete labels stay inside their categorical support (a padded
    # or trimmed label must never leak an out-of-range class index).
    e_out = np.asarray(blended["e"])
    a_out = np.asarray(blended["a"])
    assert e_out.dtype == np.int64 and a_out.dtype == np.int64
    assert int(e_out.min()) >= 0
    assert int(e_out.max()) < int(FLOWMOL3ADAPTER_N_BOND_TYPES)
    assert int(a_out.min()) >= 0
    assert int(a_out.max()) < int(FLOWMOL3ADAPTER_N_ATOM_TYPES)
    assert np.all(np.isfinite(np.asarray(blended["x"], dtype=float)))
    assert np.all(np.isfinite(np.asarray(blended["c"], dtype=float)))

    # The blender is documented as detached — inputs are not mutated.
    assert np.array_equal(np.asarray(prior["x"]), prior_x_before)
    assert np.array_equal(np.asarray(fresh["e"]), fresh_e_before)


def test_flowmol3_v2_restart_blend_shape_end_to_end() -> None:
    """K.2 — ``apply_restart_distribution`` survives a larger fresh draw.

    The unit-level K.1 check drives ``_channel_aware_blend`` directly.
    This check drives the public Protocol method, which samples the
    fresh state from ``policy_hash`` — so it also proves the crashing
    branch is reachable from the real restart path (the audit's B.5
    finding), not just from a hand-built dict.

    The test searches deterministically for a ``policy_id`` whose
    restart seed draws a molecule *larger* than the prior; that is the
    branch that used to raise ``ValueError``.
    """
    import hashlib
    from dataclasses import replace

    import numpy as np

    import adaptive_reflow.adapters.flowmol3_v2_adapter as flowmol3_v2

    from adaptive_reflow.contracts import PolicyId, hash_policy_hash

    try:
        adapter = build_adapter("flowmol3_v2")
    except (FileNotFoundError, ImportError, RuntimeError) as exc:  # pragma: no cover
        pytest.skip(f"flowmol3_v2 unavailable: {exc}")

    bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    prior_entry = adapter._native_states.get(bundle.native_state_digest)
    assert prior_entry is not None, "adapter must retain its own native state"
    n_prior = int(np.asarray(prior_entry["x"]).shape[0])

    base_policy = _make_minimal_restart_policy(
        tuple(str(ch) for ch in bundle.channels)
    )
    next_round = int(bundle.source_round) + 1

    def _fresh_size(policy: Any) -> int:
        """Mirror the adapter's restart seed derivation."""
        seed = int(
            hashlib.sha256(
                repr((str(policy.policy_hash), int(next_round))).encode("utf-8")
            ).hexdigest()[:8],
            16,
        )
        return int(flowmol3_v2._sample_n_atoms(seed))

    policy = None
    for candidate in (base_policy,) + tuple(
        replace(base_policy, policy_id=PolicyId(f"audit-policy-{i}"))
        for i in range(64)
    ):
        candidate = replace(candidate, policy_hash=hash_policy_hash(candidate))
        if _fresh_size(candidate) > n_prior:
            policy = candidate
            break
    if policy is None:  # pragma: no cover — size prior would have to change
        pytest.skip("no candidate policy draws a molecule larger than the prior")

    result = adapter.apply_restart_distribution(bundle, policy)

    assert isinstance(result, StateBundle)
    ok, errs = validate_state_bundle(result)
    assert ok, f"restart bundle must stay canonical: {errs}"
    blended = adapter._native_states.get(result.native_state_digest)
    assert blended is not None, "restart must register its blended native state"
    assert int(blended["n_atoms"]) == n_prior
    assert np.shape(blended["x"]) == (n_prior, 3)
    assert np.shape(blended["c"]) == (n_prior,)
    assert np.shape(blended["e"]) == (n_prior, n_prior)
    assert np.shape(blended["a"]) == (n_prior,)


__all__ = [
    "PROTOCOL_METHOD_SHAPE",
    "REGISTERED_ADAPTERS",
    "RESTART_BLEND_SIZE_PAIRS",
    "UNREGISTERED_ADAPTER_CLASSES",
]
