"""Public Flow Matching ODE re-inference adapter contract (DTB-G1).

.. deprecated::
   This module is a **back-compat re-export shim**. The canonical home for
   the universal adapter protocol and its pure-data carriers is
   :mod:`adaptive_reflow.universal`. New code should import from there
   directly:

       from adaptive_reflow.universal import (
           FlowMatchingODEAdapter,
           AdapterCapabilities,
           StateBundle,
           ODEConditionDelta,
           ODEIntegratorTrace,
           TensorRef,
           RestartPolicy,
           CapabilityMissingError,
           CapabilityMismatchError,
           NORMALIZATION_KINDS,
           REFERENCE_FRAMES,
       )

   The four molecule-specific channel aliases (``coordinate`` / ``charge``
   / ``raw_pair`` / ``projected_pair``) and the per-channel domain table
   live in :mod:`adaptive_reflow.molecular.channels` and
   :mod:`adaptive_reflow.molecular.domain` respectively.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Back-compat molecule-channel domain table
# ---------------------------------------------------------------------------
# The original ``DOMAIN_BY_CHANNEL`` literal mapped the four molecule
# channel names to their ``continuous`` / ``discrete`` domain kind. The
# canonical source of truth at the universal layer is now each adapter's
# own ``AdapterCapabilities.channel_domains`` declaration; the molecule
# table lives in :mod:`adaptive_reflow.molecular.domain` and is re-exported
# here for callers that have not yet migrated.
from adaptive_reflow.molecular.domain import MOLECULE_DOMAIN_BY_CHANNEL

# Canonical home: universal adapter protocol + pure-data carriers.
from adaptive_reflow.universal.adapter import (
    AdapterCapabilities,
    CapabilityMismatchError,
    CapabilityMissingError,
    ChannelDomain,
    FlowMatchingODEAdapter,
    RestartPolicy,
    validate_capabilities,
)
from adaptive_reflow.universal.state import (
    NORMALIZATION_KINDS,
    REFERENCE_FRAMES,
    ODEConditionDelta,
    ODEIntegratorTrace,
    StateBundle,
    TensorRef,
    validate_condition_delta,
    validate_integrator_trace,
    validate_state_bundle,
)

# Preserve the historical name; the molecule table exposes a richer
# per-channel dict (without the legacy ``.continuous`` / ``.discrete``
# suffix-duplicate keys).
DOMAIN_BY_CHANNEL = MOLECULE_DOMAIN_BY_CHANNEL

__all__ = [
    "DOMAIN_BY_CHANNEL",
    "NORMALIZATION_KINDS",
    "REFERENCE_FRAMES",
    "AdapterCapabilities",
    "CapabilityMismatchError",
    "CapabilityMissingError",
    "ChannelDomain",
    "FlowMatchingODEAdapter",
    "ODEConditionDelta",
    "ODEIntegratorTrace",
    "RestartPolicy",
    "StateBundle",
    "TensorRef",
    "validate_capabilities",
    "validate_condition_delta",
    "validate_integrator_trace",
    "validate_state_bundle",
]
