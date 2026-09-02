"""Tests for the Hexagonal port set (``adaptive_reflow/manifest.py``).

D1 — Hexagonal port set + W1/W2 fixes (P0-adjacent). The manifest
codifies the eight plug-in families (SchedulerProtocol,
PolicyDriverProtocol, MergeOperatorProtocol, RestartBlenderProtocol,
FlowMatchingODEAdapter, RestartMixerProtocol, EvaluatorProtocol,
EnvelopeCriterionProtocol) as named ports with explicit
``register(...)`` / ``resolve(...)`` helpers. These tests assert:

* the default singleton is populated by :func:`register_all_default`;
* per-port registration / resolution is total and fail-closed;
* PROTOCOL_REGISTRY is a view of the manifest after the auto-populate
  hook runs (D1: re-wire ``protocol_registry.PROTOCOL_REGISTRY`` to
  dispatch through ``manifest``);
* the eight canonical families (cosine / bounded / linear / etc.) are
  resolvable through the manifest and the legacy registry in lockstep.
"""

from __future__ import annotations

import pytest

from adaptive_reflow.algorithm.protocol_registry import (
    PROTOCOL_REGISTRY,
    _ensure_protocol_registry,
)
from adaptive_reflow.manifest import (
    PORT_MANIFEST,
    AdapterPort,
    BlenderPort,
    EnvelopePort,
    EvaluatorPort,
    MergeOperatorPort,
    MixerPort,
    PolicyDriverPort,
    Port,
    PortManifest,
    PortRegistrationError,
    SchedulerPort,
    enumerate_ports,
    manifest_dispatch,
    register_all_default,
)

# ---------------------------------------------------------------------------
# Default-singleton population
# ---------------------------------------------------------------------------


def test_register_all_default_populates_eight_ports() -> None:
    """``register_all_default`` populates the eight canonical ports."""
    manifest = register_all_default()
    assert isinstance(manifest, PortManifest)
    assert manifest.total_registered() >= 16  # 14 sched + 8 merge + ...
    families = manifest.families()
    # The LCM extension (D1-D4) adds two new ports — DynamicsProtocol and
    # IntegratorProtocol — that split the legacy ``solve_ode`` seam. The
    # canonical eight remain; the LCM seam is opt-in via ``DynamicsPort``
    # / ``SolverPort`` registration.
    canonical_eight = {
        "SchedulerProtocol",
        "PolicyDriverProtocol",
        "MergeOperatorProtocol",
        "RestartBlenderProtocol",
        "FlowMatchingODEAdapter",
        "RestartMixerProtocol",
        "EvaluatorProtocol",
        "EnvelopeCriterionProtocol",
    }
    lcm_extension = {"DynamicsProtocol", "IntegratorProtocol"}
    assert set(families.keys()) == canonical_eight | lcm_extension


def test_register_all_default_is_idempotent() -> None:
    """Repeated calls are no-ops (no shadowing under ``replace=False``)."""
    manifest = register_all_default()
    total_first = manifest.total_registered()
    register_all_default()
    total_second = manifest.total_registered()
    assert total_first == total_second


def test_default_manifest_has_canonical_schedulers() -> None:
    """The manifest exposes the canonical scheduler families."""
    manifest = register_all_default()
    scheduler_families = set(manifest.scheduler.families())
    # At least the four families the runner's default config can pick from.
    assert {"cosine", "linear", "constant", "exponential"} <= scheduler_families


def test_default_manifest_has_canonical_merge_operators() -> None:
    """The manifest exposes the canonical merge operator families."""
    manifest = register_all_default()
    families = set(manifest.merge_operator.families())
    assert {"bounded", "identity", "ema"} <= families


def test_default_manifest_has_canonical_blenders() -> None:
    """The manifest exposes the canonical blender families."""
    manifest = register_all_default()
    families = set(manifest.blender.families())
    assert {"linear", "distance_decay"} <= families


# ---------------------------------------------------------------------------
# Per-port register / resolve semantics
# ---------------------------------------------------------------------------


def test_port_register_resolve_roundtrip() -> None:
    """A registered implementation resolves under the same family name."""
    manifest = PortManifest()
    sentinel = object()
    manifest.scheduler.register("sentinel", sentinel)
    assert manifest.scheduler.resolve("sentinel") is sentinel
    assert "sentinel" in manifest.scheduler


def test_port_register_collision_fails_closed() -> None:
    """Re-registering a family without ``replace=True`` raises."""
    manifest = PortManifest()
    manifest.scheduler.register("only_once", object())
    with pytest.raises(PortRegistrationError):
        manifest.scheduler.register("only_once", object())


def test_port_register_with_replace_overwrites() -> None:
    """``replace=True`` silently overwrites a prior registration."""
    manifest = PortManifest()
    first = object()
    second = object()
    manifest.scheduler.register("swap_me", first)
    manifest.scheduler.register("swap_me", second, replace=True)
    assert manifest.scheduler.resolve("swap_me") is second


def test_port_resolve_unknown_family_raises() -> None:
    """Resolving an unknown family raises with the family list."""
    manifest = PortManifest()
    with pytest.raises(PortRegistrationError):
        manifest.scheduler.resolve("does_not_exist")


def test_port_register_rejects_none() -> None:
    """``register`` rejects ``None`` implementations."""
    manifest = PortManifest()
    with pytest.raises(PortRegistrationError):
        manifest.scheduler.register("bad", None)


def test_port_register_rejects_empty_family() -> None:
    """``register`` rejects empty / non-string family names."""
    manifest = PortManifest()
    with pytest.raises(PortRegistrationError):
        manifest.scheduler.register("", object())
    with pytest.raises(PortRegistrationError):
        manifest.scheduler.register(123, object())  # type: ignore[arg-type]


def test_port_unregister_unknown_raises() -> None:
    """``unregister`` fails closed when the family is absent."""
    manifest = PortManifest()
    with pytest.raises(PortRegistrationError):
        manifest.scheduler.unregister("never_registered")


def test_port_families_returns_sorted_tuple() -> None:
    """``Port.families`` returns a tuple, sorted for stability."""
    port: Port[object] = SchedulerPort(name="SchedulerProtocol")
    port.register("zeta", object())
    port.register("alpha", object())
    port.register("mu", object())
    assert port.families() == ("alpha", "mu", "zeta")


def test_manifest_register_dispatches_by_name() -> None:
    """``PortManifest.register`` routes to the correct port by name."""
    manifest = PortManifest()
    sentinel = object()
    manifest.register("MergeOperatorProtocol", "sentinel", sentinel)
    assert manifest.merge_operator.resolve("sentinel") is sentinel


def test_manifest_register_unknown_port_raises() -> None:
    """``PortManifest.register`` raises for unknown port names."""
    manifest = PortManifest()
    with pytest.raises(PortRegistrationError):
        manifest.register("BogusProtocol", "x", object())


def test_manifest_resolve_dispatches_by_name() -> None:
    """``PortManifest.resolve`` routes to the correct port by name."""
    manifest = PortManifest()
    sentinel = object()
    manifest.register("SchedulerProtocol", "sentinel", sentinel)
    assert manifest.resolve("SchedulerProtocol", "sentinel") is sentinel


def test_manifest_total_registered_counts_all_ports() -> None:
    """``total_registered`` sums the registrations across every port."""
    manifest = PortManifest()
    manifest.scheduler.register("a", object())
    manifest.merge_operator.register("a", object())
    manifest.merge_operator.register("b", object())
    assert manifest.total_registered() == 3


def test_enumerate_ports_yields_eight_pairs() -> None:
    """``enumerate_ports`` yields the eight canonical port names."""
    ports = list(enumerate_ports())
    names = [name for name, _ in ports]
    # LCM extension (D1-D4): DynamicsProtocol + IntegratorProtocol added
    # after the eight canonical ports.
    assert names == [
        "SchedulerProtocol",
        "PolicyDriverProtocol",
        "MergeOperatorProtocol",
        "RestartBlenderProtocol",
        "FlowMatchingODEAdapter",
        "RestartMixerProtocol",
        "EvaluatorProtocol",
        "EnvelopeCriterionProtocol",
        "DynamicsProtocol",
        "IntegratorProtocol",
    ]


# ---------------------------------------------------------------------------
# PROTOCOL_REGISTRY dispatch through the manifest (D1 rewire)
# ---------------------------------------------------------------------------


def test_protocol_registry_matches_manifest_after_populate() -> None:
    """``PROTOCOL_REGISTRY`` and the manifest agree after auto-populate."""
    _ensure_protocol_registry()
    families_legacy = {
        name: set(impls.keys()) for name, impls in PROTOCOL_REGISTRY.items()
    }
    families_manifest = {
        name: set(impls) for name, impls in PORT_MANIFEST.families().items()
    }
    # Each canonical port must appear in both surfaces.
    for canonical in (
        "SchedulerProtocol",
        "PolicyDriverProtocol",
        "MergeOperatorProtocol",
        "RestartBlenderProtocol",
    ):
        assert canonical in families_legacy
        assert canonical in families_manifest


def test_manifest_dispatch_resolves_canonical_family() -> None:
    """``manifest_dispatch`` resolves a canonical scheduler / merge family."""
    _ensure_protocol_registry()
    cls = manifest_dispatch("SchedulerProtocol", "cosine")
    assert cls.__name__ == "CosineAnnealScheduler"


def test_manifest_dispatch_unknown_family_raises() -> None:
    """``manifest_dispatch`` raises for unknown (port, family) pairs."""
    _ensure_protocol_registry()
    with pytest.raises(PortRegistrationError):
        manifest_dispatch("SchedulerProtocol", "phantom_family")


def test_rewire_protocol_registry_is_idempotent() -> None:
    """Re-rewiring ``PROTOCOL_REGISTRY`` does not change its size."""
    from adaptive_reflow.manifest import rewire_protocol_registry_from_manifest

    _ensure_protocol_registry()
    size_before = sum(len(reg) for reg in PROTOCOL_REGISTRY.values())
    rewire_protocol_registry_from_manifest()
    size_after = sum(len(reg) for reg in PROTOCOL_REGISTRY.values())
    assert size_before == size_after
