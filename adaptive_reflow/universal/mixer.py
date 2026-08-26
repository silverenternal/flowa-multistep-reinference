"""Universal RestartMixer Protocol (DTB-L3 / DTB-L4 — generic layer).

This module declares the *model-family-agnostic* restart-mixing
contract. It is **stdlib-only** (no ``torch``, no molecule vocabulary)
and replaces the molecule-specific
``adaptive_reflow_memory_restart_coords`` (which hardcoded an ``(N, 3)``
coordinate tensor shape) that used to live in
``legacy/restart_mixer.py``.

A concrete mixer is allowed to declare its own tensor shape; the
universal layer imposes no constraint beyond ``beta ∈ [0, 1]``. A
molecule caller subclasses ``RestartMixer`` with
``RMSPreservingCoordinateMixer`` (added in Phase 6); a graph-flow
caller subclasses it with a ``LatentConvexMixer``; an image-flow
caller subclasses it with whatever mixer fits the model.

Public surface
--------------

Protocols
    :class:`RestartMixer`

NewType aliases
    :data:`TensorRef`

Validators
    :func:`validate_blend_inputs`

Tasks satisfied:

* ``DTB-L3`` — restart mixer is universal; molecule RMS-preserving
  mixer lives in ``molecular/mixer.py``.
* ``DTB-L4`` — restart mixing is observable; the returned ``TensorRef``
  carries the mixed state, the protocol does not introspect it.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import NewType, Protocol, runtime_checkable

from .state import TensorRef

# ---------------------------------------------------------------------------
# NewType aliases
# ---------------------------------------------------------------------------


# ``TensorRef`` is re-exported from ``.state`` so callers can ``from
# adaptive_reflow.universal.mixer import TensorRef`` without reaching
# into ``.state`` directly. The NewType is the *same* object.
__all__ = [
    "RestartMixer",
    "TensorRef",
    "validate_blend_inputs",
]


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class RestartMixer(Protocol):
    """Generic restart-mixer contract.

    Implementations MUST:

    * Be total / deterministic for a given tuple of opaque inputs.
    * NOT mutate their inputs.
    * Return a ``TensorRef`` whose shape is whatever the concrete mixer
      declares (no universal shape constraint).

    ``blend(prior, endpoint, beta)`` produces a single ``TensorRef`` that
    is the mix of ``prior`` (the current round's prior state) and
    ``endpoint`` (the prior round's endpoint / memory state), with
    ``beta`` controlling how much of ``endpoint`` is mixed in.
    Concretely:

    * ``beta == 0.0`` → pure prior (no memory).
    * ``beta == 1.0`` → pure memory / endpoint.

    Concrete mixers may also return a richer ``Mapping[str, Any]``
    ledger alongside the ``TensorRef`` (e.g. an RMS-preserving mixer
    returns the pre-/post-RMS diagnostics). Callers that need only the
    mixed state consume the ``TensorRef``; callers that need diagnostics
    consult the ledger.
    """

    def blend(
        self,
        prior: TensorRef,
        endpoint: TensorRef,
        beta: float,
    ) -> TensorRef: ...


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def validate_blend_inputs(
    prior: TensorRef,
    endpoint: TensorRef,
    beta: float,
) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``blend(prior, endpoint, beta)`` is well-formed.

    On failure, the returned tuple's second element is a deterministic,
    ASCII-only tuple of error codes; never raises.

    Invariants:

    * ``prior`` and ``endpoint`` are non-empty strings (engine never
      inspects the actual tensor payload).
    * ``beta`` is a finite real number in ``[0, 1]``.
    """
    errors: list[str] = []
    if prior is None or not isinstance(prior, str) or not prior:
        errors.append("prior_must_be_non_empty_tensor_ref")
    if endpoint is None or not isinstance(endpoint, str) or not endpoint:
        errors.append("endpoint_must_be_non_empty_tensor_ref")
    if not isinstance(beta, (int, float)) or isinstance(beta, bool):
        errors.append(f"beta must be a real number, got {type(beta).__name__}")
    else:
        b = float(beta)
        if not math.isfinite(b):
            errors.append(f"beta must be finite, got {b!r}")
        elif b < 0.0 or b > 1.0:
            errors.append(f"beta must be in [0, 1], got {b!r}")
    return (not errors, tuple(errors))


# ---------------------------------------------------------------------------
# Standard concrete mixers
# ---------------------------------------------------------------------------


class NoOpMixer:
    """A no-op mixer: ``blend(prior, endpoint, beta)`` returns ``prior``.

    Used by adapters that do NOT need a restart distribution (e.g.
    unconditional single-round flows, or flows where memory is carried
    entirely through the model state itself, not via a separate
    memory-blending step).

    Implements :class:`RestartMixer` Protocol. Deterministic; the
    returned ``TensorRef`` equals the input ``prior`` regardless of
    ``beta`` or ``endpoint``.
    """

    def blend(
        self,
        prior: TensorRef,
        endpoint: TensorRef,
        beta: float,
    ) -> TensorRef:
        ok, errs = validate_blend_inputs(prior, endpoint, beta)
        if not ok:
            raise ValueError(f"invalid_blend_inputs:{errs}")
        return prior


class LatentConvexMixer:
    """Latent-space convex mixer (skeleton) for non-molecular flow matching.

    Blend formula::

        result = (1 - beta) * prior + beta * endpoint

    Use this skeleton as a starting point for latent-flow adapters
    (e.g. Stable Diffusion 3 latent flow matching). Subclass and
    override ``blend`` for adapters whose latent space requires a
    non-convex or renormalising mixer.

    Implements :class:`RestartMixer` Protocol. The actual numerical
    convex combination happens in the adapter's native code; this
    class only records the intent and the ``TensorRef`` propagation.
    """

    def __init__(
        self,
        native_blend_fn: Callable[[TensorRef, TensorRef, float], TensorRef] | None = None,
    ) -> None:
        # ``native_blend_fn(prior, endpoint, beta) -> TensorRef`` is the
        # adapter-native convex combination. None means the adapter
        # falls back to returning the prior unchanged.
        self._native = native_blend_fn

    def blend(
        self,
        prior: TensorRef,
        endpoint: TensorRef,
        beta: float,
    ) -> TensorRef:
        ok, errs = validate_blend_inputs(prior, endpoint, beta)
        if not ok:
            raise ValueError(f"invalid_blend_inputs:{errs}")
        if self._native is None:
            return prior
        return TensorRef(self._native(prior, endpoint, beta))


class DiscreteIdentityMixer:
    """Discrete-space identity mixer (skeleton) for CTMC-style flow matching.

    Blend rules::

        beta < 1.0  → return prior
        beta == 1.0 → return endpoint

    Continuous interpolation between discrete states is undefined;
    CTMC flows transition at discrete events, not by convex
    combination. Any value other than ``0.0`` or ``1.0`` is a no-op
    on the prior side; full transitions require ``beta == 1.0``.

    Implements :class:`RestartMixer` Protocol.
    """

    def blend(
        self,
        prior: TensorRef,
        endpoint: TensorRef,
        beta: float,
    ) -> TensorRef:
        ok, errs = validate_blend_inputs(prior, endpoint, beta)
        if not ok:
            raise ValueError(f"invalid_blend_inputs:{errs}")
        return endpoint if beta >= 1.0 else prior
