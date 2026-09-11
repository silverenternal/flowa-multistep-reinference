"""Shared preamble for tests/test_claims/test_claim_NNN.py modules.

Each per-claim regression test (Wave 26 traceability structure) previously
re-declared `from __future__ import annotations` plus per-file imports.
This template re-exports the **symbols common to >=4 claim files** so a
per-file import block like::

    from adaptive_reflow.algorithm.scheduler._core import default_cosine_scheduler
    from adaptive_reflow.universal.adapter import AdapterCapabilities
    from adaptive_reflow.universal.state import ChannelName, StateBundle, TensorRef

collapses to::

    from tests.test_claims._claim_template import (
        default_cosine_scheduler, AdapterCapabilities,
        ChannelName, StateBundle, TensorRef,
    )

Per Wave 26 design choice, each CLM-NNN claim still lives in its own
file for traceability; this module is purely a re-export shim.

NOTE: `from __future__ import annotations` is a **parser-level directive**
that must appear at the top of each consumer file -- it CANNOT be
imported. Each per-claim file retains its own `from __future__` line.
"""
from __future__ import annotations

# Frequently-imported framework symbols (>= 4 claim files each). Adding
# a new re-export here is a one-line fan-out, not a 22-file edit.
from adaptive_reflow.algorithm.protocol_registry import registered_families
from adaptive_reflow.algorithm.scheduler._core import default_cosine_scheduler
from adaptive_reflow.universal.adapter import AdapterCapabilities
from adaptive_reflow.universal.state import ChannelName, StateBundle, TensorRef

__all__ = [
    "default_cosine_scheduler",
    "AdapterCapabilities",
    "ChannelName",
    "StateBundle",
    "TensorRef",
    "registered_families",
]
