"""SOTA protein-sequence BFN experiment harness - STUB.

TODO(stub): full implementation pending — see
``docs/r4-survey/07-sota-experiment-protocol.md`` for the
canonical seven-step SOTA runbook. The full harness would drive
:class:`adaptive_reflow.adapters.protbfn_abbfn_adapter
.ProtBFNAbBFNAdapter` over the four canonical scheduler wrappers
(default_cosine_scheduler, CodimensionSheetScheduler,
EvidenceDrivenScheduler, FreeTrajScheduler) for ``--n-rounds`` rounds,
producing a per-round metric dict with ``aar``, ``freq_l1``, ``novelty``,
``plddt_mean``, ``n_cap``, ``beta`` fields and the comparison.md 5-row
table.

This stub is a placeholder; calling ``main()`` exits with a TODO
message. The Protocol-conformance tests in
``tests/test_adapters/test_protbfn_abbfn_adapter.py`` exercise the
adapter's eight-method surface end-to-end without invoking the
harness.
"""
from __future__ import annotations

import sys
from pathlib import Path

from adaptive_reflow.adapters.protbfn_abbfn_adapter import (
    default_protbfnabbfn_adapter,
)


def main(argv: list[str] | None = None) -> int:
    """TODO stub - not yet implemented."""
    print(
        "tools/run_sota_protbfn_abbfn_adapter_experiment.py: STUB. "
        "TODO: implement the protein-sequence BFN SOTA harness. "
        "See docs/r4-survey/07-sota-experiment-protocol.md.",
        file=sys.stderr,
    )
    return 0


__all__: list[str] = ["main"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
