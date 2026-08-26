"""Adaptive reflow restart memory mixing.

.. deprecated::
   This module is a **back-compat re-export shim**. The canonical home
   for the molecule-specific RMS-preserving coordinate mixer is
   :mod:`adaptive_reflow.molecular.mixer` (and the universal
   :class:`~adaptive_reflow.universal.mixer.RestartMixer` Protocol
   lives in :mod:`adaptive_reflow.universal.mixer`).

   The function ``adaptive_reflow_memory_restart_coords`` is re-exported
   here from the molecule module so legacy callers continue to work.
   New code should import from :mod:`adaptive_reflow.molecular`.
"""

from __future__ import annotations

from adaptive_reflow.molecular.mixer import (  # noqa: F401
    RestartMemoryState,
    RMSPreservingCoordinateMixer,
    adaptive_reflow_memory_restart_coords,
    require_torch,
)

__all__ = [
    "RMSPreservingCoordinateMixer",
    "RestartMemoryState",
    "adaptive_reflow_memory_restart_coords",
    "require_torch",
]
