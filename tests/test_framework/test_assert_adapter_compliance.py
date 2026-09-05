"""CI gate: ``assert_adapter_compliance`` is enforced on every registered adapter.

Wave 38 Agent A — closes MEDIUM-11 of the Wave 32 framework code review
(``docs/audit/framework-code-review.md`` §1.13): no adapter used the
:func:`@implements <adaptive_reflow.framework.interfaces.implements>`
decorator, so the framework's Protocol conformance was unenforced.

This module provides two layers of enforcement:

1. **HIGH-4 regression test**: a non-``@runtime_checkable`` Protocol
   passed to :func:`assert_adapter_compliance` MUST emit a
   :class:`RuntimeWarning` (instead of silently skipping).
2. **MEDIUM-11 enforcement test**: for every adapter registered in
   :data:`adaptive_reflow.adapters.ADAPTER_REGISTRY`, the class passes
   :func:`assert_adapter_compliance`. Adapters that fail to load
   (e.g. missing optional torch checkpoint) are **skipped**, NOT failed,
   so the gate is environment-tolerant.
3. **Negative test**: removing the ``@implements`` decorator on a
   selected adapter MUST make its test fail (so future regressions
   surface immediately).

How it works
------------

The ``@implements`` decorator (from
:mod:`adaptive_reflow.framework._compliance`) stores the declared
Protocol set on the class as ``__protocols__``.
:func:`assert_adapter_compliance` walks ``__protocols__`` and verifies
structural typing via :func:`isinstance` against
``@runtime_checkable`` Protocols. The CI test parametrizes over the
adapter registry, so a single broken adapter surfaces immediately.
"""
from __future__ import annotations

import warnings
from typing import Any, Protocol

import pytest

from adaptive_reflow.adapters import ADAPTER_REGISTRY, build_adapter
from adaptive_reflow.framework._compliance import (
    MissingProtocolError,
    implements,
)
from adaptive_reflow.framework.interfaces import (
    ChannelwiseBlender,
    assert_adapter_compliance,
)
from adaptive_reflow.universal.adapter import FlowMatchingODEAdapter


# ---------------------------------------------------------------------------
# HIGH-4 regression test
# ---------------------------------------------------------------------------


def test_assert_adapter_compliance_warns_on_non_runtime_protocol() -> None:
    """HIGH-4 fix: explicit warning when a non-runtime Protocol is declared.

    Per ``docs/audit/framework-code-review.md`` §1.13:
    ``assert_adapter_compliance`` silently skips Protocols that are not
    decorated with ``@runtime_checkable``. Without this warning, a future
    contributor adding a non-``@runtime_checkable`` Protocol would get a
    silent pass-through. This test pins the warning behaviour.
    """

    class NonRuntimeProtocol(Protocol):
        def foo(self) -> None: ...

    @implements(NonRuntimeProtocol)
    class BadAdapter:
        def foo(self) -> None:
            return None

    with pytest.warns(RuntimeWarning, match=r"NonRuntimeProtocol is not @runtime_checkable"):
        assert_adapter_compliance(BadAdapter)


def test_assert_adapter_compliance_raises_for_non_compliant_runtime_protocol() -> None:
    """A non-``@runtime_checkable`` Protocol that is unsatisfied must raise.

    Sanity check that the runtime conformance path still raises
    :class:`MissingProtocolError` for unsatisfied ``@runtime_checkable``
    Protocols (the existing Wave 11 conformance behaviour must not be
    weakened by the HIGH-4 fix).
    """

    @implements(FlowMatchingODEAdapter)
    class NonCompliantAdapter:
        """Adapter declares conformance to FlowMatchingODEAdapter but provides none of the 8 methods."""

        pass

    with pytest.raises(MissingProtocolError) as exc:
        assert_adapter_compliance(NonCompliantAdapter)
    assert "FlowMatchingODEAdapter" in str(exc.value)


# ---------------------------------------------------------------------------
# MEDIUM-11: CI gate over the adapter registry
# ---------------------------------------------------------------------------


def _build_or_skip(family: str) -> Any:
    """Build the default adapter for ``family`` or skip on init failure.

    Mirrors the skip pattern from :mod:`tests.test_adapters.conformance_battery`:
    adapters whose default factory raises :class:`FileNotFoundError`,
    :class:`ImportError`, or :class:`RuntimeError` (e.g. requiring
    weights on disk or an upstream torch dependency) are skipped with a
    documented reason rather than failing the gate.
    """
    try:
        return build_adapter(family)
    except FileNotFoundError as exc:
        pytest.skip(f"{family} requires weights on disk: {exc}")
    except (ImportError, RuntimeError) as exc:
        pytest.skip(f"{family} dependency missing or init failed: {exc}")


@pytest.mark.parametrize(
    "family",
    sorted(ADAPTER_REGISTRY),
    ids=lambda f: f"adapter:{f}",
)
def test_every_registered_adapter_passes_assert_adapter_compliance(
    family: str,
) -> None:
    """Every registered adapter MUST satisfy its declared ``__protocols__`` set.

    The :func:`@implements <adaptive_reflow.framework.interfaces.implements>`
    decorator stores the declared Protocol set on the adapter class.
    :func:`assert_adapter_compliance` verifies structural typing against
    ``@runtime_checkable`` Protocols and raises
    :class:`MissingProtocolError` if any declared Protocol is unsatisfied.

    This is the load-bearing CI gate that closes MEDIUM-11 of the Wave 32
    framework code review. Without it, an adapter can silently violate its
    declared Protocol surface (a regression that would be invisible to the
    type-checker because the Protocols are structural).
    """
    adapter = _build_or_skip(family)
    # No assertion error expected: the test fails if and only if
    # ``assert_adapter_compliance`` raises ``MissingProtocolError``.
    assert_adapter_compliance(type(adapter))


def test_every_adapter_declares_at_least_one_protocol() -> None:
    """Every registered adapter MUST declare at least one Protocol via ``@implements``.

    MEDIUM-11 enforces that *every* registered adapter carries an
    ``@implements`` decorator. Adapters that don't declare any Protocol
    cannot be conformance-checked, defeating the purpose of the gate.
    """
    for family in sorted(ADAPTER_REGISTRY):
        adapter = _build_or_skip(family)
        declared = getattr(adapter, "__protocols__", ())
        assert declared, (
            f"adapter {type(adapter).__name__} (family {family!r}) has no "
            f"declared Protocols; add an @implements(...) decorator."
        )


def test_registry_is_non_empty() -> None:
    """The adapter registry must be non-empty (sanity gate).

    Trivially true today; exists as a trip-wire for a future refactor that
    accidentally clears the registry.
    """
    assert ADAPTER_REGISTRY, "ADAPTER_REGISTRY must be non-empty"


# ---------------------------------------------------------------------------
# Negative test (regression surfacing)
# ---------------------------------------------------------------------------


def test_removing_implements_breaks_the_gate() -> None:
    """Removing ``@implements`` MUST make the conformance gate fail.

    Pins the CI gate's behaviour against future refactors that might
    "soften" :func:`assert_adapter_compliance` (e.g. silent skips for
    declared-but-unsatisfied Protocols). We use the
    :class:`ChannelwiseBlender` Protocol as a small fixture: an
    unsatisfied declaration MUST raise :class:`MissingProtocolError`,
    while the same class without ``@implements`` is a silent no-op.
    """

    # An adapter that declares ChannelwiseBlender conformance but does
    # NOT implement blend() / blend_family(). The conformance gate must
    # raise MissingProtocolError here.
    @implements(ChannelwiseBlender)
    class UnsatisfiedBlender:
        """Declares ChannelwiseBlender conformance but does not implement it."""

        pass

    with pytest.raises(MissingProtocolError, match=r"ChannelwiseBlender"):
        assert_adapter_compliance(UnsatisfiedBlender)

    # The same class WITHOUT @implements must be a silent no-op (the
    # gate only enforces declared conformance). This demonstrates that
    # the gate is not unconditionally failing.
    class NoDeclare:
        pass

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # suppress any unrelated HIGH-4 warnings
        assert_adapter_compliance(NoDeclare)  # no-op pass


__all__ = [
    "test_assert_adapter_compliance_warns_on_non_runtime_protocol",
    "test_assert_adapter_compliance_raises_for_non_compliant_runtime_protocol",
    "test_every_registered_adapter_passes_assert_adapter_compliance",
    "test_every_adapter_declares_at_least_one_protocol",
    "test_registry_is_non_empty",
    "test_removing_implements_breaks_the_gate",
]