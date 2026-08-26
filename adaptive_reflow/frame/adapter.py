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

   The molecule-specific channel vocabulary lives in
   :mod:`adaptive_reflow.molecular.channels` and the per-channel domain
   fallback table (for molecule-aware callers) in
   :mod:`adaptive_reflow.molecular.domain`. Universal code MUST NOT
   reach into the molecule layer; each adapter declares its own
   ``AdapterCapabilities.channel_domains`` instead.
"""

from __future__ import annotations

# Canonical home: universal adapter protocol + pure-data carriers.
# NOTE: this module is intentionally molecule-free. The legacy
# ``DOMAIN_BY_CHANNEL`` constant that used to live here was a
# molecule-only fallback table and has been removed; per-channel
# domain resolution is now the adapter's responsibility via
# ``AdapterCapabilities.channel_domains``. Molecule-aware callers may
# consult :data:`adaptive_reflow.molecular.domain.MOLECULE_DOMAIN_BY_CHANNEL`.
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

__all__ = [
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
