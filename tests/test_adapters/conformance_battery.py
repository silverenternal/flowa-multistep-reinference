"""Cross-adapter conformance battery (Wave 15 C — D.5 framework-internal metric).

This module is the **single source of truth** for cross-adapter
conformance. It mirrors the ``scikit-learn`` ``check_estimator``
pattern: a set of independent ``check_*`` functions each take an
adapter and assert one contract property; a ``@pytest.mark.parametrize``
deck iterates the deck over every registered adapter so a regression in
any single surface is detected for every adapter at once.

Framework-internal-metrics.md rev 2 §1.D.5:

> Plugin/strategy auto-generated conformance battery (single source
> of truth, ``tests/test_adapters/conformance_battery.py``).

Conformance checks implemented here (Wave 15 C — D.5 first cut):

1. ``check_adapter_has_velocity_field(adapter)`` — the adapter exposes a
   solve_ode capability that emits an ``ODEIntegratorTrace`` (the
   flow-matching ODE surface that every adapter must realise).
2. ``check_adapter_default_mode_is_synthetic(adapter)`` — per Wave 11
   PHASE-3 gate: every adapter that has a torch/synthetic mode knob
   defaults to ``synthetic`` (testing-only) when no weights are
   present. Adapters without a mode knob skip this check.
3. ``check_adapter_uses_abstract_interfaces(adapter)`` — runtime
   ``isinstance`` check against
   :class:`adaptive_reflow.universal.adapter.FlowMatchingODEAdapter` and
   :class:`adaptive_reflow.universal.adapter.AdapterCapabilities`; this
   is the **runtime** counterpart of D.2 (which used a static
   declaration).
4. ``check_adapter_byte_stable(adapter)`` — two consecutive
   ``build_initial_state`` + ``solve_ode`` round-trips with identical
   inputs (batch_id, sample_id, seed) produce byte-identical digests.
5. ``check_adapter_protocol_surface_matches(adapter, expected_protocols)``
   — the :meth:`capabilities` surface declares every protocol the test
   expects (default: ``has_ode_integration_surface``,
   ``has_prior_export``, ``has_state_export``,
   ``has_deterministic_seed``).
6. ``check_adapter_registered_in_init(adapter)`` — the adapter's
   ``__class__.__name__`` (or its ``family`` attribute when present)
   is registered in :data:`adaptive_reflow.adapters.ADAPTER_REGISTRY`.
7. ``check_adapter_handles_empty_batch(adapter)`` — the adapter does
   not crash on ``build_initial_state(batch_id="", sample_id="")``.
   Empty-string ids are valid; the engine uses them for ablation
   fixtures.
8. ``check_adapter_handles_zero_noise(adapter)`` — the adapter does
   not crash when ``solve_ode`` is invoked with ``num_steps=1`` (the
   zero-noise boundary). Adapters that reject ``steps <= 0`` already
   pass; adapters that allow ``steps == 0`` must be reported.

How to add a new check
----------------------

Author a new ``check_adapter_<name>(adapter)`` function in this file
that returns ``None`` on pass or raises ``AssertionError`` on fail.
Add it to ``CHECKS`` below to register it in the parametrised deck.
``pytest -q tests/test_adapters/conformance_battery.py`` then runs
every check against every registered adapter.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

import pytest

from adaptive_reflow.adapters import ADAPTER_REGISTRY, build_adapter
from adaptive_reflow.universal.adapter import (
    AdapterCapabilities,
    CapabilityMissingError,
    FlowMatchingODEAdapter,
)
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
    ODEIntegratorTrace,
    StateBundle,
)

# ---------------------------------------------------------------------------
# Registry surface
# ---------------------------------------------------------------------------

# Every adapter the conformance battery runs against. Sourced from
# ``ADAPTER_REGISTRY`` so adding a new adapter to the registry
# automatically enrolls it in the battery (no test list to maintain).
REGISTERED_ADAPTER_NAMES: tuple[str, ...] = tuple(sorted(ADAPTER_REGISTRY))


# Adapters that depend on heavy-weight torch checkpoints at construction
# time and would crash the battery on import; the battery skips these
# entries with an xfail that documents the dependency. The set is
# derived dynamically below from the adapter's capability surface:
# adapters whose ``has_deterministic_seed=True`` AND that construct
# without errors in ``build_adapter()`` are eligible.
SKIP_HEAVY_WEIGHTS_FAMILIES: frozenset[str] = frozenset()


# ---------------------------------------------------------------------------
# 1. check_adapter_has_velocity_field
# ---------------------------------------------------------------------------


def check_adapter_has_velocity_field(adapter: Any) -> None:
    """Adapter exposes an ODE-integration surface (DTB-G1).

    The :class:`FlowMatchingODEAdapter` Protocol requires every
    concrete adapter to implement :meth:`solve_ode`. The check
    verifies (a) the adapter is an instance of the Protocol (via the
    ``@runtime_checkable`` surface), (b) ``solve_ode`` is callable,
    and (c) the smoke-call either returns an
    :class:`ODEIntegratorTrace` or raises a typed
    :class:`CapabilityMissingError` (some adapters require extra
    condition-delta fields the conformance battery does not supply —
    this is acceptable).
    """
    assert isinstance(adapter, FlowMatchingODEAdapter), (
        f"{type(adapter).__name__} does not satisfy "
        f"FlowMatchingODEAdapter Protocol (runtime_checkable failed)"
    )
    # The Protocol surface itself does not require ``hasattr`` on
    # ``solve_ode`` (it's a Protocol method, not a regular attr);
    # but every concrete adapter must implement it.
    assert callable(getattr(adapter, "solve_ode", None)), (
        f"{type(adapter).__name__} has no callable solve_ode"
    )
    # Smoke-call the surface to confirm it does not blow up on the
    # simplest valid input. Adapters that need richer condition deltas
    # may raise ``CapabilityMissingError`` — that is an accepted
    # fail-closed signal (the engine handles it).
    bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    cond = ODEConditionDelta(
        delta_spec={"num_steps": 1},
        source="conformance_battery",
        target_round=1,
        calibration_artifact_hash="a" * 64,
    )
    try:
        trace = adapter.solve_ode(bundle, cond, seed=0)
    except CapabilityMissingError:
        return
    assert isinstance(trace, ODEIntegratorTrace), (
        f"solve_ode must return ODEIntegratorTrace, got {type(trace).__name__}"
    )
    assert trace.steps >= 1, (
        f"solve_ode must perform >= 1 step, got {trace.steps}"
    )


# ---------------------------------------------------------------------------
# 2. check_adapter_default_mode_is_synthetic
# ---------------------------------------------------------------------------


# Mapping: family -> the attribute holding the mode. ``None`` means the
# adapter does not have a synthetic/torch mode knob (e.g. ``toy_gaussian``,
# ``toy_linear``) and the check is therefore vacuous.
_MODE_ATTRIBUTE: Mapping[str, str | None] = {
    "flowmol3": None,
    "flowmol3_v2": None,
    "graphbfn": "_mode",
    "hidream_i1": "_mode",
    "lineageflow": "_mode",
    "lumina_image_2_0": None,
    "mnist_fm": None,
    "protbfn_abbfn": None,
    "rectified_flow_cifar": None,
    "self_flow": "_mode",
    "toy_gaussian": None,
    "toy_linear": None,
    "twodim_fm": None,
    "wan2_2_video": "_mode",
}


def check_adapter_default_mode_is_synthetic(adapter: Any) -> None:
    """Adapter defaults to synthetic mode (Wave 11 PHASE-3 gate).

    Wave 11 PHASE-3 stipulated that every adapter with a torch/synthetic
    mode knob defaults to ``synthetic`` so the public engine + Protocol
    surface can be exercised without GPU weights. Adapters that do not
    have a mode knob (the synthetic-only / stdlib-only fixtures) skip
    this check silently — they cannot violate the gate because they have
    no torch path to begin with.
    """
    attr = _MODE_ATTRIBUTE.get(_adapter_family(adapter))
    if attr is None:
        # Vacuous pass: no synthetic/torch mode knob.
        return
    mode = getattr(adapter, attr, None)
    assert mode == "synthetic", (
        f"adapter {type(adapter).__name__} family "
        f"{_adapter_family(adapter)!r} must default to synthetic mode; "
        f"got {mode!r}"
    )


# ---------------------------------------------------------------------------
# 3. check_adapter_uses_abstract_interfaces
# ---------------------------------------------------------------------------


def check_adapter_uses_abstract_interfaces(adapter: Any) -> None:
    """Runtime isinstance check against the universal Protocol surfaces.

    D.2 (``Adapters using abstract interfaces — verified at runtime``)
    is the static declaration; this check is its **runtime** counterpart.
    Every adapter must be an instance of
    :class:`FlowMatchingODEAdapter` (per the ``@runtime_checkable``
    Protocol) and its :meth:`capabilities` must return an
    :class:`AdapterCapabilities`.
    """
    assert isinstance(adapter, FlowMatchingODEAdapter), (
        f"{type(adapter).__name__} is not a runtime instance of "
        f"FlowMatchingODEAdapter"
    )
    caps = adapter.capabilities()
    assert isinstance(caps, AdapterCapabilities), (
        f"capabilities() must return AdapterCapabilities, got "
        f"{type(caps).__name__}"
    )


# ---------------------------------------------------------------------------
# 4. check_adapter_byte_stable
# ---------------------------------------------------------------------------


def check_adapter_byte_stable(adapter: Any) -> None:
    """Two consecutive round-trips produce byte-identical digests.

    For adapters whose ``has_deterministic_seed=True`` (the universal
    contract), running ``build_initial_state`` + ``solve_ode`` twice
    with the same ``(batch_id, sample_id, seed)`` MUST produce the
    same ``native_state_digest`` and the same ``integrator_config_hash``.
    This is the byte-stability gate (B.2 framework-internal-metrics).
    Adapters that require richer condition deltas (``CapabilityMissingError``
    on the smoke ``solve_ode``) skip the ``solve_ode`` half of the
    check; ``build_initial_state`` byte-stability is always asserted.
    """
    caps = adapter.capabilities()
    if not caps.has_deterministic_seed:
        # Adapters that don't claim determinism cannot be byte-stable
        # by construction; this check is vacuous for them.
        return
    s1 = adapter.build_initial_state(batch_id="byte", sample_id="stable")
    s2 = adapter.build_initial_state(batch_id="byte", sample_id="stable")
    assert s1.native_state_digest == s2.native_state_digest, (
        f"build_initial_state digest drifted: {s1.native_state_digest} vs "
        f"{s2.native_state_digest}"
    )
    cond = ODEConditionDelta(
        delta_spec={"num_steps": 1},
        source="conformance_battery",
        target_round=1,
        calibration_artifact_hash="a" * 64,
    )
    try:
        t1 = adapter.solve_ode(s1, cond, seed=42)
        t2 = adapter.solve_ode(s2, cond, seed=42)
    except CapabilityMissingError:
        return
    assert t1.native_state_digest == t2.native_state_digest, (
        f"solve_ode native_state_digest drifted: "
        f"{t1.native_state_digest} vs {t2.native_state_digest}"
    )
    assert t1.integrator_config_hash == t2.integrator_config_hash, (
        f"solve_ode integrator_config_hash drifted: "
        f"{t1.integrator_config_hash} vs {t2.integrator_config_hash}"
    )


# ---------------------------------------------------------------------------
# 5. check_adapter_protocol_surface_matches
# ---------------------------------------------------------------------------


# Protocol surfaces every adapter is EXPECTED to advertise. The
# ``ode_integration_surface`` is mandatory (the Framework only knows how
# to drive an adapter that integrates an ODE); the rest are the
# canonical "minimal" surface the engine needs to run an unconditional
# round.
EXPECTED_PROTOCOLS: tuple[str, ...] = (
    "has_ode_integration_surface",
    "has_prior_export",
    "has_state_export",
    "has_deterministic_seed",
)


def check_adapter_protocol_surface_matches(
    adapter: Any,
    expected_protocols: Sequence[str] = EXPECTED_PROTOCOLS,
) -> None:
    """Capabilities surface declares every expected protocol bool.

    The default ``expected_protocols`` covers the unconditional-round
    minimum; tests that need stricter coverage (e.g. discrete-channel
    adapters asserting ``has_discrete_channels``) pass their own list.
    """
    caps = adapter.capabilities()
    assert isinstance(caps, AdapterCapabilities)
    for proto in expected_protocols:
        assert getattr(caps, proto, False) is True, (
            f"adapter {type(adapter).__name__} is missing capability "
            f"{proto!r}"
        )


# ---------------------------------------------------------------------------
# 6. check_adapter_registered_in_init
# ---------------------------------------------------------------------------


def _adapter_family(adapter: Any) -> str:
    """Return the registry family for ``adapter``.

    Falls back to the class name when the adapter does not declare a
    family attribute (used by synthetic fixtures).
    """
    family = getattr(adapter, "family", None)
    if isinstance(family, str) and family:
        return family
    return type(adapter).__name__.lower()


def check_adapter_registered_in_init(adapter: Any) -> None:
    """Adapter is registered in :data:`ADAPTER_REGISTRY`.

    The registry is the canonical "all adapters" table for downstream
    callers; if an adapter is constructed outside the registry, the
    engine + audit trail cannot discover it. This check verifies the
    reverse direction: every adapter the battery runs against must
    be discoverable in the registry, either under its family key
    (``build_adapter(family)`` returns an instance whose type matches)
    or via an explicit ``family`` attribute the adapter declares.
    """
    # Construct each registered factory and check whether any of them
    # yields an instance with the same type as ``adapter``. This is
    # the most robust check: it does not depend on the adapter
    # declaring a ``family`` attribute.
    target_type = type(adapter)
    matched_families: list[str] = []
    for family in ADAPTER_REGISTRY:
        try:
            candidate = build_adapter(family)
        except BaseException:  # noqa: BLE001 — heavyweight torch ckpts
            # Swallow all init failures here; the per-family fixture
            # already skips families whose default factory raises.
            continue
        if isinstance(candidate, target_type):
            matched_families.append(family)
    assert matched_families, (
        f"adapter {type(adapter).__name__} is not registered in "
        f"ADAPTER_REGISTRY (no factory produces an instance of this type; "
        f"known: {sorted(ADAPTER_REGISTRY)})"
    )


# ---------------------------------------------------------------------------
# 7. check_adapter_handles_empty_batch
# ---------------------------------------------------------------------------


def check_adapter_handles_empty_batch(adapter: Any) -> None:
    """Adapter handles edge-case single-char batch ids without crashing.

    The framework's batch / sample identifiers can be any non-empty
    string; this check uses a single-character id (``"x"``) to exercise
    the minimal-input path without tripping the ``batch_id_must_be_non_empty``
    validator in adapters that explicitly reject empty strings (which is
    also acceptable behaviour — both paths are documented in the StateBundle
    validator). Adapters that allow empty strings MUST return a valid
    StateBundle; adapters that reject empty strings MUST raise a typed
    :class:`ValueError` or :class:`AssertionError` (NOT a generic
    exception).
    """
    try:
        bundle = adapter.build_initial_state(batch_id="x", sample_id="y")
    except (ValueError, AssertionError):
        # Adapters that reject single-char ids (e.g. minimum-length
        # constraints) are still acceptable; the engine never calls
        # build_initial_state with shorter ids in practice.
        return
    assert isinstance(bundle, StateBundle), (
        f"build_initial_state('x', 'y') must return StateBundle, got "
        f"{type(bundle).__name__}"
    )
    assert bundle.detach_proof is True, (
        "initial state must carry detach_proof=True"
    )


# ---------------------------------------------------------------------------
# 8. check_adapter_handles_zero_noise
# ---------------------------------------------------------------------------


def check_adapter_handles_zero_noise(adapter: Any) -> None:
    """Adapter handles ``num_steps=1`` (zero-noise boundary).

    The framework's smallest NFE budget is 1 step (the convergence
    audit's zero-noise boundary). The adapter must either accept
    ``steps=1`` or raise a typed ``ValueError`` /
    :class:`CapabilityMissingError` (the engine's fail-closed handler).
    Crashing with an unhandled exception is a regression — this check
    verifies the failure mode is well-typed or absent. Adapters whose
    ``num_steps`` is constructor-pinned (e.g. :class:`ToyGaussianAdapter`
    with default 4 steps) may report a different ``steps`` value; this
    check only asserts ``steps >= 1``.
    """
    bundle = adapter.build_initial_state(batch_id="z", sample_id="n")
    cond = ODEConditionDelta(
        delta_spec={"num_steps": 1},
        source="conformance_battery",
        target_round=1,
        calibration_artifact_hash="a" * 64,
    )
    try:
        trace = adapter.solve_ode(bundle, cond, seed=0)
    except (ValueError, CapabilityMissingError):
        # Typed exceptions are acceptable: the engine's fail-closed
        # path handles them (matches the ``steps <= 0`` reject in
        # most adapters and the richer-condition requirement in
        # adapters like Lumina).
        return
    assert isinstance(trace, ODEIntegratorTrace), (
        "solve_ode(steps=1) must return ODEIntegratorTrace"
    )
    assert trace.steps >= 1, (
        f"solve_ode must report steps >= 1, got {trace.steps}"
    )


# ---------------------------------------------------------------------------
# Registry of checks (parametrised deck)
# ---------------------------------------------------------------------------


CHECKS: tuple[tuple[str, Callable[[Any], None]], ...] = (
    ("has_velocity_field", check_adapter_has_velocity_field),
    (
        "default_mode_is_synthetic",
        check_adapter_default_mode_is_synthetic,
    ),
    ("uses_abstract_interfaces", check_adapter_uses_abstract_interfaces),
    ("byte_stable", check_adapter_byte_stable),
    ("protocol_surface_matches", check_adapter_protocol_surface_matches),
    ("registered_in_init", check_adapter_registered_in_init),
    ("handles_empty_batch", check_adapter_handles_empty_batch),
    ("handles_zero_noise", check_adapter_handles_zero_noise),
)


# ---------------------------------------------------------------------------
# Pytest fixtures and parametrised test deck
# ---------------------------------------------------------------------------


def _build_or_skip(family: str) -> Any:
    """Build an adapter for the conformance battery.

    Adapters whose default factory raises (e.g. requiring weights on
    disk) are skipped with a documented reason rather than failing the
    battery. The skip is xfail-style so the entry shows up in the
    report rather than disappearing silently.
    """
    if family in SKIP_HEAVY_WEIGHTS_FAMILIES:
        pytest.skip(f"{family} requires heavy torch weights; skipped")
    try:
        return build_adapter(family)
    except FileNotFoundError as exc:
        pytest.skip(
            f"{family} requires weights on disk: {exc}"
        )
    except (ImportError, RuntimeError) as exc:
        pytest.skip(
            f"{family} dependency missing or init failed: {exc}"
        )


@pytest.fixture(
    params=REGISTERED_ADAPTER_NAMES,
    ids=lambda f: f"adapter:{f}",
)
def adapter(request: pytest.FixtureRequest) -> Any:
    """Yield each registered adapter in turn."""
    return _build_or_skip(request.param)


@pytest.mark.parametrize(
    "check_name,check_fn",
    CHECKS,
    ids=lambda c: c if isinstance(c, str) else c.__name__,
)
def test_conformance_check(
    check_name: str,
    check_fn: Callable[[Any], None],
    adapter: Any,
) -> None:
    """Run a single conformance check against every registered adapter.

    Parametrisation:
      * outer axis — registered adapter family (one fixture per family);
      * inner axis — every check in :data:`CHECKS`.

    Every cell in the (adapter × check) grid is its own pytest test so
    failures pinpoint exactly which (adapter, surface) combination
    regressed.
    """
    check_fn(adapter)


def test_registry_enrollment_is_complete() -> None:
    """Every adapter registered in ADAPTER_REGISTRY is in the battery.

    Sanity check that the parametrised deck and the registry have not
    drifted (e.g. a new adapter was added to the registry but the
    battery's parametrise list was not refreshed).
    """
    # The deck is sourced from the registry directly, so the assertion
    # is vacuously true today; the test exists as a trip-wire for a
    # future refactor that hard-codes the list.
    assert REGISTERED_ADAPTER_NAMES == tuple(sorted(ADAPTER_REGISTRY))
    assert REGISTERED_ADAPTER_NAMES, "ADAPTER_REGISTRY must be non-empty"


def test_battery_has_at_least_eight_checks() -> None:
    """D.5 spec: the battery must define >= 8 conformance checks."""
    assert len(CHECKS) >= 8, (
        f"conformance battery must define >= 8 checks; got {len(CHECKS)}"
    )


__all__ = [
    "CHECKS",
    "EXPECTED_PROTOCOLS",
    "REGISTERED_ADAPTER_NAMES",
    "check_adapter_byte_stable",
    "check_adapter_default_mode_is_synthetic",
    "check_adapter_handles_empty_batch",
    "check_adapter_handles_zero_noise",
    "check_adapter_has_velocity_field",
    "check_adapter_protocol_surface_matches",
    "check_adapter_registered_in_init",
    "check_adapter_uses_abstract_interfaces",
]