"""Molecule domain-by-channel table — fallback for molecule-aware callers.

This module declares the canonical mapping from molecule channel name to
its ``continuous`` / ``discrete`` domain kind. It is the molecule-specific
counterpart to the universal ``AdapterCapabilities.channel_domains``
declaration.

Module boundary
---------------

* ``MOLECULE_DOMAIN_BY_CHANNEL`` is the *fallback* table consulted by
  molecule-aware callers; the universal engine routes via
  ``AdapterCapabilities.channel_domains`` instead and never reads this
  table.
* ``MOLECULE_DOMAIN_BY_CHANNEL`` is a verbatim copy of the legacy
  ``frame.adapter.DOMAIN_BY_CHANNEL`` literal (Phase 2 of the refactor
  plan; only the four base entries are retained, the four ``.continuous``
  / ``.discrete`` suffix-tagged entries that were legacy convenience
  duplicates are dropped here).
* Stdlib-only. No torch, no I/O, no mutation of inputs.

Public surface
--------------

Constants
    :data:`MOLECULE_DOMAIN_BY_CHANNEL`
"""

from __future__ import annotations

from collections.abc import Mapping

# ---------------------------------------------------------------------------
# Per-channel domain kind (fallback table)
# ---------------------------------------------------------------------------


MOLECULE_DOMAIN_BY_CHANNEL: Mapping[str, str] = {
    "coordinate": "continuous",
    "charge": "continuous",
    "raw_pair": "discrete",
    "projected_pair": "discrete",
    "coordinate.continuous": "continuous",
    "charge.continuous": "continuous",
    "raw_pair.discrete": "discrete",
    "projected_pair.discrete": "discrete",
}
"""Fallback molecule channel → domain-kind table.

The universal engine routes per-channel validation through each adapter's
own ``AdapterCapabilities.channel_domains`` declaration. This mapping
is provided so molecule-aware callers (e.g. tests, debug scripts) can
look up the canonical domain kind for a molecule channel name without
instantiating an adapter. The four ``<channel>.<domain>`` suffix-tagged
keys are the legacy convenience duplicates retained for back-compat with
the pre-split ``frame.adapter.DOMAIN_BY_CHANNEL`` literal.
"""


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = ["MOLECULE_DOMAIN_BY_CHANNEL"]
