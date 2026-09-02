"""Per-channel state-type + shape contracts (D5 — LMAA redesign).

The :class:`StateChannel` enum and :class:`StateShape` dataclass are
the **per-channel** typed surface that replaces the current single
``state_shape: tuple[int, ...] = (2,)`` carrier on
:class:`adaptive_reflow.universal.adapter.AdapterCapabilities`.

Background
----------

The current ``AdapterCapabilities.state_shape`` is a single
``tuple[int, ...]`` intended to describe the per-instance native
state shape. For a 2-D flow-matching adapter the value is ``(2,)``;
for a CIFAR adapter it is ``(3, 32, 32)``; for a molecule adapter it
is ``(n_atoms, 3)``. The LCM (least-common-multiple) redesign requires
**per-channel** declaration because a single adapter may carry:

* one *continuous* coordinate channel with shape ``(n_atoms, 3)``;
* one *categorical* atom-type channel with shape ``(n_atoms,)``;
* one *graph* adjacency channel with shape ``(n_nodes, n_nodes)``.

A single tuple cannot express this heterogeneity; the engine
therefore needs a typed :class:`StateShape` per channel
(:attr:`StateShape.dims`) plus an optional :attr:`StateShape.variable_axes`
indicator for channels whose first axis is sample-specific
(FlowMol3 ``n_atoms``, GraphBFN ``n_nodes``).

Public surface
--------------

* :class:`StateChannel` — closed set of per-channel types
  (``CONTINUOUS`` / ``CATEGORICAL_MASK`` / ``CATEGORICAL_ARGMAX`` /
  ``CATEGORICAL_SAMPLE`` / ``MIXED`` / ``GRAPH``).
* :class:`StateShape` — ``dims: tuple[int, ...]`` plus
  ``variable_axes: tuple[int, ...]`` indicator.
* :func:`validate_state_shape` — canonical validator.
* :data:`STATE_CHANNELS` — closed type universe (tuple of discriminator
  literals).

This module is **stdlib-only** (no ``torch``, no numpy, no I/O) so it
sits in the contracts layer alongside the other typed-carrier
modules.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Literal

from .types import ChannelName

# ---------------------------------------------------------------------------
# StateChannel — closed enum of per-channel native-state kinds
# ---------------------------------------------------------------------------

#: Canonical tuple of :attr:`StateChannel` discriminator values. Adding
#: a new kind requires a paired acceptance test and a ``DTB-Q``
#: decision in ``todo.json``.
STATE_CHANNELS: Final[tuple[str, ...]] = (
    "continuous",
    "categorical_mask",
    "categorical_argmax",
    "categorical_sample",
    "mixed",
    "graph",
)
"""Closed type universe for :class:`StateChannel` discriminator values."""

StateChannelKind = Literal[
    "continuous",
    "categorical_mask",
    "categorical_argmax",
    "categorical_sample",
    "mixed",
    "graph",
]
"""Stable discriminator literal for :class:`StateChannel.channel_kind`."""


#: Canonical alias used by other modules (``StateChannel`` is a
#: NewType-style name rather than a runtime class — the enum is the
#: tuple of literals above plus a thin runtime validator).
StateChannel = str
"""Per-channel native-state type. One of :data:`STATE_CHANNELS`.

A :class:`StateChannel` value is a closed-set string literal selected
from :data:`STATE_CHANNELS`. The closed set is enforced by
:func:`validate_state_channel`. The six values cover the union of
LCM concerns identified in the FM-LCM interface gap audit
(``docs/r17-survey/fm-lcm-interface-gap-audit.md``):

* ``"continuous"`` — additive Gaussian / ODE-integrated channel
  (FlowMol3 ``coordinate``, GraphBFN ``charge``, ``valence``,
  Lumina/HiDream ``latent``).
* ``"categorical_mask"`` — categorical channel where padded positions
  carry a sentinel mask (``mask == 0`` substitutes fresh draw;
  FlowMol3 ``atom_type`` padded positions, GraphBFN diagonal
  ``-inf`` sentinel).
* ``"categorical_argmax"`` — categorical channel whose endpoint
  observation is the ``argmax`` of a per-position softmax
  (ProtBFN amino-acid ``argmax``, GraphBFN adjacency ``argmax``).
* ``"categorical_sample"`` — categorical channel whose endpoint
  observation is a categorical sample drawn from the per-position
  softmax (ProtBFN ``sample``, FlowMol3 ``bond_type`` sample).
* ``"mixed"`` — channel carrying a tuple of typed sub-channels
  (FlowMol3 ``(x, a, c, e)`` four-tuple; the ``mixed`` kind tells
  the dispatcher to recurse into the per-sub-channel state_types
  table rather than treating the channel as atomic).
* ``"graph"`` — graph-shaped channel (node-edge-attribute triple;
  ``GraphBFN (theta_node, theta_edge, adj_logits)``);
  graph-blending needs the ``m=0`` / ``m=1`` short-circuit to dodge
  ``0 * -inf = NaN`` on the adjacency diagonal.
"""


def validate_state_channel(value: StateChannel) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``value`` is a canonical :class:`StateChannel`.

    Accepts the closed set :data:`STATE_CHANNELS`; rejects everything
    else with a typed error code. The validator is total and
    side-effect-free.
    """
    if not isinstance(value, str):
        return (False, (f"state_channel_must_be_str:{type(value).__name__}",))
    if not value:
        return (False, ("state_channel_must_be_non_empty",))
    if value not in STATE_CHANNELS:
        return (False, (f"state_channel_unknown:{value}",))
    return (True, ())


# ---------------------------------------------------------------------------
# StateShape — per-channel shape declaration with variable-axis marker
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StateShape:
    """Per-channel native-state shape (replaces the single-tuple carrier).

    Attributes
    ----------

    dims : ``tuple[int, ...]``
        The static dimensions of the channel's native state. ``()``
        (empty tuple) is the degenerate scalar channel; ``(2,)`` is
        the canonical 2-D flow-matching channel; ``(n_atoms, 3)`` is
        the FlowMol3 coordinate channel; ``(n_nodes, n_nodes)`` is
        the GraphBFN adjacency channel.

    variable_axes : ``tuple[int, ...]``
        Indices into ``dims`` whose extent varies sample-by-sample
        (FlowMol3 ``n_atoms``, GraphBFN ``n_nodes``). The default
        ``()`` means every axis is statically sized; non-empty
        values signal the framework to invoke the dynamic-shape
        resampling helper (D18 — ``DynamicShapePriorProtocol``).

    The :class:`StateShape` is opt-in: adapters that do not supply a
    per-channel ``state_shape`` field continue to use the legacy
    ``AdapterCapabilities.state_shape: tuple[int, ...] = (2,)``
    carrier; the framework falls back to it whenever a channel
    carries no typed :class:`StateShape` declaration. This preserves
    the 2356-test back-compat invariant.
    """

    dims: tuple[int, ...] = ()
    variable_axes: tuple[int, ...] = ()


def validate_state_shape(shape: StateShape) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``shape`` is a well-formed :class:`StateShape`.

    Validates:

    * ``dims`` is a tuple of non-negative integers; ``()`` is legal
      (scalar channel).
    * ``variable_axes`` is a tuple of distinct non-negative integer
      indices whose values are all ``< len(dims)``.
    """
    errors: list[str] = []
    if shape is None:
        return (False, ("state_shape_must_not_be_none",))
    if not isinstance(shape.dims, tuple):
        errors.append("state_shape_dims_must_be_tuple")
    else:
        for i, d in enumerate(shape.dims):
            if not isinstance(d, int) or isinstance(d, bool):
                errors.append(f"state_shape_dims[{i}]_must_be_int:{type(d).__name__}")
                continue
            if d < 0:
                errors.append(f"state_shape_dims[{i}]_must_be_non_negative:{d}")
    if not isinstance(shape.variable_axes, tuple):
        errors.append("state_shape_variable_axes_must_be_tuple")
    else:
        n_dims = len(shape.dims) if isinstance(shape.dims, tuple) else 0
        seen: set[int] = set()
        for i, ax in enumerate(shape.variable_axes):
            if not isinstance(ax, int) or isinstance(ax, bool):
                errors.append(
                    f"state_shape_variable_axes[{i}]_must_be_int:{type(ax).__name__}"
                )
                continue
            if ax < 0:
                errors.append(f"state_shape_variable_axes[{i}]_must_be_non_negative:{ax}")
            if ax >= n_dims:
                errors.append(
                    f"state_shape_variable_axes[{i}]_out_of_range:{ax}>=n_dims={n_dims}"
                )
            if ax in seen:
                errors.append(f"state_shape_variable_axes[{i}]_duplicate:{ax}")
            seen.add(ax)
    return (not errors, tuple(errors))


# ---------------------------------------------------------------------------
# Per-channel type table — typed carrier on AdapterCapabilities
# ---------------------------------------------------------------------------


def validate_channel_types(
    channel_types: Mapping[ChannelName, StateChannel],
    *,
    supported_channels: tuple[str, ...] | None = None,
) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``channel_types`` describes a valid table.

    Validates:

    * Every value is a canonical :class:`StateChannel` (closed set).
    * When ``supported_channels`` is supplied, every key must appear
      in ``supported_channels`` (channels that the adapter declares
      but does not type-tag are not a contract violation — the
      table is opt-in per channel).
    """
    errors: list[str] = []
    if channel_types is None:
        return (False, ("channel_types_must_not_be_none",))
    supported = frozenset(supported_channels) if supported_channels else None
    for ch, kind in channel_types.items():
        ch_str = str(ch)
        if supported is not None and ch_str not in {str(s) for s in supported}:
            errors.append(
                f"channel_types key {ch_str!r} must appear in supported_channels"
            )
        ok, kind_errs = validate_state_channel(kind)
        if not ok:
            for e in kind_errs:
                errors.append(f"channel_types[{ch_str}]:{e}")
    return (not errors, tuple(errors))


__all__ = [
    "STATE_CHANNELS",
    "StateChannel",
    "StateChannelKind",
    "StateShape",
    "validate_channel_types",
    "validate_state_channel",
    "validate_state_shape",
]
