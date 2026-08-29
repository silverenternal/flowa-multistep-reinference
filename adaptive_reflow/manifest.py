"""Hexagonal port set for the adaptive_reflow component (P0-adjacent / D1).

Implements the hexagonal architecture pattern (Cockburn 2005, Vernon 2013):
the eight plug-in families that today live as scattered ``@runtime_checkable``
Protocols are codified as *named ports* with explicit ``register(...)`` /
``resolve(...)`` helpers and a single :class:`PortManifest` listing each
port's capability contract.

Module boundary
---------------

* **stdlib-only**. No ``torch``. No I/O. Module-level state lives only in
  the :data:`PORT_MANIFEST` singleton (single mutable carrier for port
  registrations, intentionally process-local).
* Every port exposes ``register(...)`` / ``resolve(...)``; bad input fails
  closed (raises :class:`PortRegistrationError`).
* The :func:`register_all_default` helper wires the canonical concrete
  implementations so callers who only need the stock set can ``from
  adaptive_reflow.manifest import PORT_MANIFEST`` and have everything
  resolvable without manual wiring.

Public surface
--------------

* :class:`PortManifest` — the single carrier for every port.
* :class:`SchedulerPort` / :class:`PolicyDriverPort` /
  :class:`MergeOperatorPort` / :class:`BlenderPort` /
  :class:`AdapterPort` / :class:`MixerPort` /
  :class:`EvaluatorPort` / :class:`EnvelopePort` — the eight port classes.
* :data:`PORT_MANIFEST` — the module-level default singleton.
* :func:`register_all_default` — populate the singleton with the stock set.
* :func:`manifest_dispatch` — protocol-registry dispatch through the manifest.

Why this exists
---------------

This module is the framework-driving seam called out in
``docs/r3-survey/06-frontier-decoupling.md`` §10 ("Top 3 recommendations")
and ``08-fix-plan.md`` §3 (D1 — Hexagonal port set). The four leak findings
(W1–W4) from ``03-coupling.md`` all stem from the same root cause: the
pluggable surface is implicit (re-exports in ``__init__.py``, raw
``@runtime_checkable`` Protocols, ``PROTOCOL_REGISTRY`` mutated at import
time). The Hexagonal port set turns that implicit surface into a single,
auditable, introspectable seam so:

* the engine can resolve its collaborators by *name* against a typed port,
* a test fixture can swap one port without touching the rest of the
  composition root, and
* the audit ledger can attribute a round's behaviour to a specific
  registered implementation per port.

Cross-references
----------------

* ``docs/r3-survey/06-frontier-decoupling.md`` §1 (Hexagonal Architecture).
* ``docs/r3-survey/08-fix-plan.md`` §3 (D1) + §6 (implementation seq #5).
* ``adaptive_reflow/algorithm/protocol_registry.py`` — the legacy
  flat-name registry, retained for backward compatibility. New code should
  prefer :func:`manifest_dispatch` (which delegates to the legacy registry
  for actual implementation lookup, keeping a single source of truth).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any, TypeVar

# ---------------------------------------------------------------------------
# Errors (fail-closed; surface bad caller input)
# ---------------------------------------------------------------------------


class PortRegistrationError(KeyError):
    """Raised when a port registration or resolution fails.

    Subclasses :class:`KeyError` so existing
    ``pytest.raises(KeyError)`` patterns continue to work; the message
    includes the supported family list so callers can recover.
    """


class PortContractError(TypeError):
    """Raised when a registered implementation does not satisfy the port contract.

    Subclasses :class:`TypeError` for back-compat with existing
    ``pytest.raises(TypeError)`` patterns.
    """


# ---------------------------------------------------------------------------
# Generic Port (parameterised on the concrete protocol type)
# ---------------------------------------------------------------------------


T = TypeVar("T")


class Port[T]:
    """A single named port — register / resolve against a family name.

    Each port holds a ``name`` (the canonical port identifier, e.g.
    ``"SchedulerProtocol"``), an optional ``protocol`` reference (the
    ``@runtime_checkable`` Protocol class the port dispatches against,
    used for runtime ``isinstance`` checks when supplied), and a private
    ``_registry`` dict mapping ``family -> implementation class or
    factory``.

    The :class:`Port` class is *generic* in the implementation type so
    type-checkers can narrow the return type of :meth:`resolve` per port
    instance (e.g. ``SchedulerPort.resolve("cosine")`` is annotated as
    returning the concrete scheduler type).

    Concurrent registrations are not supported; the port is process-local
    and intended to be populated once at composition root time (mirrors
    the OSGi service registry / Eclipse extension-point contract).
    """

    __slots__ = ("name", "protocol", "_registry")

    def __init__(
        self,
        *,
        name: str,
        protocol: type | None = None,
    ) -> None:
        if not isinstance(name, str) or not name:
            raise PortRegistrationError(
                f"port name must be a non-empty string, got {name!r}"
            )
        self.name: str = name
        self.protocol: type | None = protocol
        self._registry: dict[str, Any] = {}

    # -- introspection ----------------------------------------------------

    def families(self) -> tuple[str, ...]:
        """Return the registered family names, sorted for stability."""
        return tuple(sorted(self._registry.keys()))

    def __contains__(self, family: str) -> bool:
        return family in self._registry

    def __len__(self) -> int:
        return len(self._registry)

    # -- mutation ---------------------------------------------------------

    def register(
        self,
        family: str,
        implementation: T | Callable[..., T],
        *,
        replace: bool = False,
    ) -> None:
        """Register ``implementation`` under ``family``.

        Fails closed when ``family`` is already registered and
        ``replace=False`` (the default — explicit opt-in for re-binding
        prevents accidental shadowing in composition roots). When
        ``protocol`` is supplied, a runtime ``isinstance`` check is
        performed on the implementation as a courtesy (the canonical
        contract for the port).

        Parameters
        ----------
        family:
            The family identifier (e.g. ``"cosine"``,
            ``"bounded"``). Must be a non-empty string.
        implementation:
            Either a concrete class / instance satisfying the port
            contract, or a zero-argument factory callable.
        replace:
            When ``True``, silently overwrite an existing registration.
            When ``False`` (default), raise on collision.
        """
        if not isinstance(family, str) or not family:
            raise PortRegistrationError(
                f"{self.name}: family must be a non-empty string, "
                f"got {family!r}"
            )
        if implementation is None:
            raise PortRegistrationError(
                f"{self.name}: implementation must not be None "
                f"(family={family!r})"
            )
        if family in self._registry and not replace:
            raise PortRegistrationError(
                f"{self.name}: family {family!r} is already registered; "
                f"pass replace=True to overwrite. registered families: "
                f"{sorted(self._registry)!r}"
            )
        if self.protocol is not None and not callable(implementation):
            # Runtime contract check — ``isinstance`` against the
            # supplied Protocol. Skipped when ``implementation`` is a
            # factory callable (factories are validated at construction
            # time, not registration time).
            try:
                if not isinstance(implementation, self.protocol):
                    raise PortContractError(
                        f"{self.name}: implementation for family "
                        f"{family!r} does not satisfy protocol "
                        f"{self.protocol.__name__!r}; "
                        f"got {type(implementation).__name__}"
                    )
            except TypeError:
                # Some Protocols (e.g. ``typing.Protocol`` itself) do
                # not support ``isinstance``; skip the check rather
                # than fail closed on a structural-typing corner case.
                pass
        self._registry[family] = implementation

    def unregister(self, family: str) -> None:
        """Remove the registration for ``family``.

        Raises :class:`PortRegistrationError` when ``family`` is not
        currently registered.
        """
        if family not in self._registry:
            raise PortRegistrationError(
                f"{self.name}: cannot unregister unknown family {family!r}; "
                f"registered families: {sorted(self._registry)!r}"
            )
        del self._registry[family]

    # -- resolution -------------------------------------------------------

    def resolve(self, family: str) -> T | Callable[..., T]:
        """Return the implementation registered under ``family``.

        Raises :class:`PortRegistrationError` when ``family`` is not
        registered (fail-closed; callers should not silently fall back
        to a default — the registry is the source of truth).
        """
        if family not in self._registry:
            raise PortRegistrationError(
                f"{self.name}: unknown family {family!r}; "
                f"registered families: {sorted(self._registry)!r}"
            )
        return self._registry[family]  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Concrete port types (one per hexagonal port)
# ---------------------------------------------------------------------------


class SchedulerPort(Port[Any]):
    """Port for :class:`adaptive_reflow.algorithm.scheduler.SchedulerProtocol`.

    Holds the canonical ``"cosine"``, ``"linear"``, ``"exponential"`` etc.
    schedulers behind a single ``register`` / ``resolve`` seam so the
    engine can dispatch by family name without touching the legacy
    ``PROTOCOL_REGISTRY`` directly.
    """


class PolicyDriverPort(Port[Any]):
    """Port for :class:`adaptive_reflow.algorithm.policy_driver.PolicyDriverProtocol`."""


class MergeOperatorPort(Port[Any]):
    """Port for :class:`adaptive_reflow.algorithm.merge_operator.MergeOperatorProtocol`.

    The canonical bounded / identity / EMA / kalman / bayesian / PID /
    schedule-aware / multi-source operators all live behind this port;
    a new operator becomes one ``register(...)`` call.
    """


class BlenderPort(Port[Any]):
    """Port for :class:`adaptive_reflow.algorithm.blender.RestartBlenderProtocol`.

    Linear / distance-decay / OT-linear / multi-temperature /
    joint-OT-linear / barycentric blenders all live behind this port.
    Closes W1 from ``03-coupling.md``: every adapter that today inlines
    ``m * prior + (1 - m) * fresh`` in its ``apply_restart_distribution``
    can delegate to a registered blender via :meth:`BlenderPort.resolve`.
    """


class AdapterPort(Port[Any]):
    """Port for the flow-matching / flow-adaptive adapter surface.

    Wraps the ``FlowMatchingODEAdapter`` family (``TwoDimFMAdapter``,
    ``ToyLinearAdapter``, ``ToyGaussianAdapter``, etc.). Distinct from
    ``MixerPort`` in that adapters own the ODE integration surface
    while mixers own the restart-mixing surface.
    """


class MixerPort(Port[Any]):
    """Port for the restart-mixing surface (``NoOpMixer`` etc.).

    Adapters carry a ``required_mixer``; the mixer is the in-adapter
    transformation that turns a freshly-sampled state into the round's
    "fresh noise" contribution. Distinct from ``BlenderPort`` in that
    the blender operates *across* rounds (prior vs. fresh) while the
    mixer operates *within* a single round.
    """


class EvaluatorPort(Port[Any]):
    """Port for the ``Evaluator`` family.

    Oracle functions (QED, ADMET, GNINA, PoseBusters, synthetic oracle)
    all conform to the ``Evaluator`` Protocol; the port gives the
    framework a single seam to register / resolve them by name.
    """


class EnvelopePort(Port[Any]):
    """Port for the envelope-classification surface.

    Envelope predicates (``EnvelopeCriterion`` + derived / custom
    implementations) all conform to a small Protocol; this port is the
    framework-driven seam that future envelope-classifier plug-ins
    register against.
    """


# ---------------------------------------------------------------------------
# The PortManifest (carrier for every port)
# ---------------------------------------------------------------------------


class PortManifest:
    """Carrier for every named port in the system.

    Holds one :class:`Port` instance per hexagonal port and exposes the
    ``register(...)`` / ``resolve(...)`` API at the manifest level so
    callers can do ``manifest.register("SchedulerPort", "freetraj", cls)``
    without reaching into the per-port dicts.

    The manifest is a *value object*: every public mutation goes through
    a method that fails closed on bad input. There is **no** implicit
    auto-population — callers must explicitly invoke
    :func:`register_all_default` or register each (port, family, impl)
    tuple by hand.

    Concurrent access is not supported; the manifest is process-local
    and intended to be populated once at composition-root time.
    """

    __slots__ = (
        "_scheduler",
        "_policy_driver",
        "_merge_operator",
        "_blender",
        "_adapter",
        "_mixer",
        "_evaluator",
        "_envelope",
    )

    def __init__(self) -> None:
        self._scheduler: SchedulerPort = SchedulerPort(name="SchedulerProtocol")
        self._policy_driver: PolicyDriverPort = PolicyDriverPort(
            name="PolicyDriverProtocol"
        )
        self._merge_operator: MergeOperatorPort = MergeOperatorPort(
            name="MergeOperatorProtocol"
        )
        self._blender: BlenderPort = BlenderPort(name="RestartBlenderProtocol")
        self._adapter: AdapterPort = AdapterPort(name="FlowMatchingODEAdapter")
        self._mixer: MixerPort = MixerPort(name="RestartMixerProtocol")
        self._evaluator: EvaluatorPort = EvaluatorPort(name="EvaluatorProtocol")
        self._envelope: EnvelopePort = EnvelopePort(name="EnvelopeCriterionProtocol")

    # -- per-port accessors ----------------------------------------------

    @property
    def scheduler(self) -> SchedulerPort:
        return self._scheduler

    @property
    def policy_driver(self) -> PolicyDriverPort:
        return self._policy_driver

    @property
    def merge_operator(self) -> MergeOperatorPort:
        return self._merge_operator

    @property
    def blender(self) -> BlenderPort:
        return self._blender

    @property
    def adapter(self) -> AdapterPort:
        return self._adapter

    @property
    def mixer(self) -> MixerPort:
        return self._mixer

    @property
    def evaluator(self) -> EvaluatorPort:
        return self._evaluator

    @property
    def envelope(self) -> EnvelopePort:
        return self._envelope

    # -- bulk introspection ---------------------------------------------

    def families(self) -> Mapping[str, tuple[str, ...]]:
        """Return ``{port_name: tuple(family, ...)}`` for every port.

        Sorted per-port so the output is stable across runs and Python
        versions.
        """
        return {
            "SchedulerProtocol": self._scheduler.families(),
            "PolicyDriverProtocol": self._policy_driver.families(),
            "MergeOperatorProtocol": self._merge_operator.families(),
            "RestartBlenderProtocol": self._blender.families(),
            "FlowMatchingODEAdapter": self._adapter.families(),
            "RestartMixerProtocol": self._mixer.families(),
            "EvaluatorProtocol": self._evaluator.families(),
            "EnvelopeCriterionProtocol": self._envelope.families(),
        }

    def total_registered(self) -> int:
        """Return the sum of registrations across every port."""
        return (
            len(self._scheduler)
            + len(self._policy_driver)
            + len(self._merge_operator)
            + len(self._blender)
            + len(self._adapter)
            + len(self._mixer)
            + len(self._evaluator)
            + len(self._envelope)
        )

    # -- manifest-level register / resolve -------------------------------

    def register(
        self,
        port_name: str,
        family: str,
        implementation: Any,
        *,
        replace: bool = False,
    ) -> None:
        """Register ``implementation`` under ``(port_name, family)``.

        Dispatches to the correct port by name. Raises
        :class:`PortRegistrationError` for unknown port names or family
        collisions (when ``replace=False``).
        """
        port = self._resolve_port(port_name)
        port.register(family, implementation, replace=replace)

    def resolve(self, port_name: str, family: str) -> Any:
        """Return the implementation registered under ``(port_name, family)``."""
        port = self._resolve_port(port_name)
        return port.resolve(family)

    # -- internal helpers -----------------------------------------------

    def _resolve_port(self, port_name: str) -> Port[Any]:
        if not isinstance(port_name, str) or not port_name:
            raise PortRegistrationError(
                f"port_name must be a non-empty string, got {port_name!r}"
            )
        # Map canonical Protocol names → internal slot names.
        slot_map = {
            "schedulerprotocol": "_scheduler",
            "policydriverprotocol": "_policy_driver",
            "mergeoperatorprotocol": "_merge_operator",
            "restartblenderprotocol": "_blender",
            "flowmatchingdeadapter": "_adapter",
            "restartmixerprotocol": "_mixer",
            "evaluatorprotocol": "_evaluator",
            "envelopecriterionprotocol": "_envelope",
        }
        normalized = port_name.lower()
        slot = slot_map.get(normalized)
        if slot is None:
            raise PortRegistrationError(
                f"unknown port {port_name!r}; known ports: "
                f"{sorted(slot_map.values())!r}"
            )
        return getattr(self, slot)  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------


PORT_MANIFEST: PortManifest = PortManifest()
"""The module-level default :class:`PortManifest` singleton.

Callers who want a private manifest can instantiate their own
:class:`PortManifest` directly. This singleton is the default wiring for
the framework; :func:`register_all_default` populates it with the
canonical stock implementations so the framework resolves them by name.
"""


# ---------------------------------------------------------------------------
# Default-population helper
# ---------------------------------------------------------------------------


def register_all_default(
    manifest: PortManifest | None = None,
    *,
    replace: bool = False,
) -> PortManifest:
    """Populate ``manifest`` with the canonical stock implementations.

    Lazy-imports the concrete classes from their owning modules so this
    module loads without triggering circular imports at package load time
    (mirrors the lazy-import pattern in
    ``adaptive_reflow.algorithm.protocol_registry``).

    Parameters
    ----------
    manifest:
        Optional target manifest. Defaults to :data:`PORT_MANIFEST`.
    replace:
        When ``True``, overwrite existing registrations. Default
        ``False`` fails closed on collision so a second invocation
        surfaces drift instead of silently shadowing.

    Returns
    -------
    PortManifest
        The populated manifest (same object that was passed in, or the
        module-level singleton when ``manifest=None``).
    """
    if manifest is None:
        manifest = PORT_MANIFEST
    # Lazy imports — keep the manifest module import-time cheap and
    # avoid circular imports with the algorithm subpackage. We call
    # the *per-protocol builders* directly (not
    # ``_ensure_protocol_registry``) so this helper does not recurse
    # back through ``protocol_registry._ensure_protocol_registry``.
    from .algorithm.protocol_registry import (
        _build_blender_registry,
        _build_merge_operator_registry,
        _build_policy_driver_registry,
        _build_scheduler_registry,
    )

    families_to_register: dict[str, dict[str, Any]] = {
        "SchedulerProtocol": _build_scheduler_registry(),
        "PolicyDriverProtocol": _build_policy_driver_registry(),
        "MergeOperatorProtocol": _build_merge_operator_registry(),
        "RestartBlenderProtocol": _build_blender_registry(),
    }
    for port_name, families in families_to_register.items():
        for family, impl in families.items():
            try:
                manifest.register(port_name, family, impl, replace=replace)
            except PortRegistrationError:
                # Already-registered families are silently accepted
                # when ``replace=False`` so this helper is idempotent
                # across multiple invocations against the same singleton.
                if replace:
                    raise
                continue
    return manifest


# ---------------------------------------------------------------------------
# Dispatch helper (single seam for engine / orchestrator code)
# ---------------------------------------------------------------------------


def manifest_dispatch(
    port_name: str,
    family: str,
    *,
    manifest: PortManifest | None = None,
) -> Any:
    """Resolve ``(port_name, family)`` against ``manifest`` (default singleton).

    Single seam for engine / orchestrator code that wants to dispatch
    by name against the hexagonal port set without importing the
    legacy ``PROTOCOL_REGISTRY`` directly.

    Falls back to the legacy ``PROTOCOL_REGISTRY`` when ``manifest`` is
    not explicitly populated (preserves back-compat with callers that
    have not yet migrated to the manifest wiring).
    """
    if manifest is None:
        manifest = PORT_MANIFEST
    if manifest.total_registered() == 0:
        # Caller did not populate the manifest — fall through to the
        # legacy registry so this helper is safe to use even before
        # ``register_all_default`` has run.
        from .algorithm.protocol_registry import PROTOCOL_REGISTRY, _ensure_protocol_registry

        _ensure_protocol_registry()
        if port_name not in PROTOCOL_REGISTRY:
            raise PortRegistrationError(
                f"unknown port {port_name!r}; registered ports: "
                f"{sorted(PROTOCOL_REGISTRY)!r}"
            )
        families = PROTOCOL_REGISTRY[port_name]
        if family not in families:
            raise PortRegistrationError(
                f"{port_name}: unknown family {family!r}; "
                f"registered families: {sorted(families)!r}"
            )
        return families[family]
    return manifest.resolve(port_name, family)


# ---------------------------------------------------------------------------
# Protocol-registry hook (so PROTOCOL_REGISTRY can be re-derived from the
# manifest; this keeps the two surfaces in lockstep without forcing a
# full migration in one pass).
# ---------------------------------------------------------------------------


def rewire_protocol_registry_from_manifest(
    *,
    manifest: PortManifest | None = None,
) -> int:
    """Re-derive :data:`PROTOCOL_REGISTRY` from ``manifest``.

    Mutates the legacy :data:`PROTOCOL_REGISTRY` dict in place so that
    every port's registered families are reflected there. Returns the
    number of (port, family) tuples copied.

    Idempotent: re-invocations after a manifest re-population overwrite
    the legacy dict rather than appending. Pair with
    :func:`register_all_default` for the canonical wiring path:

        register_all_default()
        rewire_protocol_registry_from_manifest()
    """
    if manifest is None:
        manifest = PORT_MANIFEST
    from .algorithm.protocol_registry import PROTOCOL_REGISTRY

    count = 0
    # Walk every port explicitly so we copy the *mapping* of
    # ``family -> implementation``, not the sorted-tuple-of-names that
    # :meth:`PortManifest.families` returns. Only ports with at least
    # one registered family are copied — the legacy ``PROTOCOL_REGISTRY``
    # is the canonical surface for the four plug-in Protocols
    # (``SchedulerProtocol``, ``PolicyDriverProtocol``,
    # ``MergeOperatorProtocol``, ``RestartBlenderProtocol``); the other
    # hexagonal ports (Adapter/Mixer/Evaluator/Envelope) are populated
    # via :func:`manifest_dispatch` and should not appear here as empty
    # entries (the auto-populate invariant
    # ``test_protocol_registry_auto_populated`` would otherwise fail).
    for port_name, port in enumerate_ports(manifest):
        if not port._registry:
            continue
        PROTOCOL_REGISTRY[port_name] = dict(port._registry)
        count += len(port._registry)
    return count


# ---------------------------------------------------------------------------
# Introspection helpers
# ---------------------------------------------------------------------------


def enumerate_ports(
    manifest: PortManifest | None = None,
) -> Iterable[tuple[str, Port[Any]]]:
    """Yield ``(port_name, port)`` for every port in ``manifest``."""
    if manifest is None:
        manifest = PORT_MANIFEST
    yield ("SchedulerProtocol", manifest.scheduler)
    yield ("PolicyDriverProtocol", manifest.policy_driver)
    yield ("MergeOperatorProtocol", manifest.merge_operator)
    yield ("RestartBlenderProtocol", manifest.blender)
    yield ("FlowMatchingODEAdapter", manifest.adapter)
    yield ("RestartMixerProtocol", manifest.mixer)
    yield ("EvaluatorProtocol", manifest.evaluator)
    yield ("EnvelopeCriterionProtocol", manifest.envelope)


__all__ = [
    "PORT_MANIFEST",
    "AdapterPort",
    "BlenderPort",
    "EnvelopePort",
    "EvaluatorPort",
    "MergeOperatorPort",
    "MixerPort",
    "PolicyDriverPort",
    "Port",
    "PortContractError",
    "PortManifest",
    "PortRegistrationError",
    "SchedulerPort",
    "enumerate_ports",
    "manifest_dispatch",
    "register_all_default",
    "rewire_protocol_registry_from_manifest",
]
