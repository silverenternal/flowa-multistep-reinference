"""Molecule channel vocabulary — concrete channel names + opaque handles.

This module declares the *concrete* molecule channel vocabulary for the
pocket-conditioned 3D flow matching adapter (FlowMol3-class). It is the
molecule-specific counterpart to the universal ``ChannelName`` NewType in
:mod:`adaptive_reflow.universal.state`. The universal layer carries no
canonical channel-name list; channels are per-adapter.

Module boundary
---------------

* ``MOLECULE_CHANNELS`` is the canonical 4-tuple of molecule channel
  names. It replaces the legacy ``contracts.types.CHANNEL_NAMES`` literal
  set (Phase 2 of the refactor plan).
* The four ``*ChannelRef`` aliases are concrete ``NewType`` wrappers over
  ``Mapping[str, Any]`` so a molecule-aware caller can declare a more
  specific handle type. They were previously declared in
  ``contracts.types`` and are re-exported here for back-compat.
* Stdlib-only. No torch, no I/O.

Public surface
--------------

NewType aliases
    :data:`CoordinateChannelRef`
    :data:`ChargeChannelRef`
    :data:`RawPairChannelRef`
    :data:`ProjectedPairChannelRef`

Constants
    :data:`MOLECULE_CHANNELS`
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum, StrEnum
from typing import Any, NewType

# ---------------------------------------------------------------------------
# NewType aliases
# ---------------------------------------------------------------------------


CoordinateChannelRef = NewType("CoordinateChannelRef", Mapping[str, Any])
"""Opaque handle to the coordinate channel payload (atom 3D positions).

Concrete shape is owned by the adapter (FlowMol3); the universal layer
treats this as ``Mapping[str, Any]``.
"""


ChargeChannelRef = NewType("ChargeChannelRef", Mapping[str, Any])
"""Opaque handle to the charge channel payload (formal / partial charges)."""


RawPairChannelRef = NewType("RawPairChannelRef", Mapping[str, Any])
"""Opaque handle to the raw (unprojected) pair topology channel payload."""


ProjectedPairChannelRef = NewType("ProjectedPairChannelRef", Mapping[str, Any])
"""Opaque handle to the projected pair topology channel payload."""


# ---------------------------------------------------------------------------
# Canonical channel vocabulary
# ---------------------------------------------------------------------------


MOLECULE_CHANNELS: tuple[str, ...] = (
    "coordinate",
    "charge",
    "raw_pair",
    "projected_pair",
)
"""Canonical molecule channel vocabulary for FlowMol3-class adapters.

A non-molecular adapter (graph-flow, image-flow, sequence-flow) does not
import this tuple; it advertises its own channels via
``AdapterCapabilities.supported_channels``.
"""


class MoleculeChannel(StrEnum):
    """Closed enum of molecule channel names.

    The values are the same string keys as :data:`MOLECULE_CHANNELS`.
    Useful where a type-checked enum is preferred over a bare string.
    """

    COORDINATE = "coordinate"
    CHARGE = "charge"
    RAW_PAIR = "raw_pair"
    PROJECTED_PAIR = "projected_pair"


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "MOLECULE_CHANNELS",
    # NewType aliases
    "CoordinateChannelRef",
    "ChargeChannelRef",
    "ProjectedPairChannelRef",
    "RawPairChannelRef",
    # Closed enum
    "MoleculeChannel",
]
