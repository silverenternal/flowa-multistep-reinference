"""Lightweight adapter-compliance decorators (Wave 38 Agent A).

Split out from :mod:`adaptive_reflow.framework.interfaces` to break the
following cyclic import chain:

    framework.interfaces → theory.checkers → eval.lipschitz_diagnostic
      → eval → posterior_selection_evaluator → adapters.twodim_fm
      → framework.interfaces

When ``adapters.twodim_fm`` (and the other adapters in the cycle)
import ``implements`` from :mod:`framework.interfaces` at module-load
time, the cycle triggers a partial-load of :mod:`framework.interfaces`.
The :func:`implements` symbol MUST already be defined by then for the
cycle to resolve. ``implements`` and :class:`MissingProtocolError` are
pure stdlib (no heavy imports), so they live in this tiny module which
the heavy :mod:`framework.interfaces` re-exports for back-compat.

This module must remain stdlib-only — do not add any non-stdlib imports.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any


class MissingProtocolError(TypeError):
    """Raised when an adapter fails to satisfy a declared Protocol."""
    pass


def implements(*protocols: type) -> Callable[[type], type]:
    """Class decorator that declares which Protocols the class satisfies.

    Usage::

        @implements(ChannelwiseBlender, IntegratorProtocol)
        class MyAdapter:
            ...

    Stores the Protocol set on the class as ``__protocols__``. The
    set is consulted by :func:`assert_adapter_compliance`. This
    decorator is purely declarative (no runtime checks at decoration
    time); call :func:`assert_adapter_compliance` to enforce.

    Returns the class unchanged.

    Defined in :mod:`adaptive_reflow.framework._compliance` (a
    stdlib-only module) to break the cyclic import
    ``adapters.twodim_fm → framework.interfaces``. See the module
    docstring for the full cycle description.
    """
    for protocol in protocols:
        if not isinstance(protocol, type):
            raise TypeError(
                f"implements() expects Protocol *type* arguments, got {protocol!r}"
            )
    proto_set = tuple(protocols)

    def decorator(cls: type) -> type:
        existing = getattr(cls, "__protocols__", ())
        merged: list[type] = list(existing)
        for p in proto_set:
            if p not in merged:
                merged.append(p)
        cls.__protocols__ = tuple(merged)  # type: ignore[attr-defined]
        return cls

    return decorator


__all__ = ["MissingProtocolError", "implements"]
