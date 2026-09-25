#!/usr/bin/env python3
"""CLI: smoke-check the existence of the headline-evidence artifact set.

The ``verification_outputs/`` tree carries 530+ directories; the headline
11-cell evidence lives in a small, fixed set of artifacts that the
paper / submission package relies on. This verifier checks that all
twelve of those artifacts exist on disk and (when their parent ships a
``SHA256SUMS`` ledger) that they are recorded in the ledger.

The set is the canonical anchor list for the Wave 326 final-metrics
table; a paper-submission push must see all twelve present.

Usage::

    PYTHONPATH=. python tools/verify_reproducibility_smoke.py [--quiet]

Exit code is ``0`` iff every required artifact exists; ``1`` on any
missing artifact or ledger-entry mismatch.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Layout / configuration
# ---------------------------------------------------------------------------


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
"""Resolved repo root (one level above ``tools/``)."""

VERIF_ROOT: Path = REPO_ROOT / "verification_outputs"
"""Artifact root. Every required path is expressed relative to this."""


# The headline-evidence artifact set. Each entry is the *exact* repo-
# relative path under ``verification_outputs/`` that must exist before
# the paper can be submitted. The ordering matches the headline table
# (R1, R2, R3, R5a/R5b/R5c, R6, K1, K4+K5, K7) so a missing artifact
# can be identified by its row position in the report.
REQUIRED_ARTIFACTS: tuple[str, ...] = (
    "wave218-p3-kanzi-framework-wins.json",                        # R2 canonical
    "wave191-p3-mnist-n1000.json",                                 # R5c smoke
    "wave233-p3-tier-aware-r6.json",                               # R6 tier-aware
    "wave247-p3-r5b-n1000-n1/summary.json",                        # R5b n_rounds=1
    "lineageflow_hmmer_real_n1000_w158_q3_2026/baseline_hits.tbl", # R1 hits
    "lineageflow_hmmer_real_n1000_w158_q3_2026/framework_hits.tbl",# R1 hits
    "novelty_pctid_w166_q3_2026/novelty_results_full.json",        # K7 direction
    "wave280-p-r1/summary.json",                                   # R1 3-seed summary
    "wave280-p-r5c/aggregate.json",                                # R5c production
    "wave280-p-k1/summary.json",                                   # K1
    "wave280-k7/summary.json",                                     # K7
    "wave280-p-k4k5/summary_n100.json",                            # K4+K5
)


# ---------------------------------------------------------------------------
# Smoke result model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Missing:
    """One required artifact that was not found on disk."""

    path: str
    reason: str  # "absent" | "ledger_unlisted"


@dataclass(frozen=True)
class SmokeResult:
    """Aggregate smoke-check result."""

    required: int
    present: int
    missing: tuple[Missing, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def _ledger_contains(verif_root: Path, rel: str) -> bool:
    """Return True if the ``SHA256SUMS`` ledger (if any) of the parent
    directory lists ``rel`` as a tracked file. A file without a parent
    ledger (or whose parent does not exist) is considered unverified --
    not missing -- because no ledger was expected to cover it.
    """
    target = verif_root / rel
    if not target.exists():
        # No ledger can cover a non-existent file; the caller will
        # report this as ``absent`` (not ``ledger_unlisted``).
        return True
    parent = target.parent
    ledger = parent / "SHA256SUMS"
    if not ledger.is_file():
        return True  # no ledger to violate
    # Parse the ledger and check ``rel`` (the path the ledger uses is
    # the parent-relative one with a leading ``./``).
    rel_to_parent = "./" + target.name
    for line in ledger.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        # Same split heuristic as ``check_data_integrity``: tolerate
        # both single- and double-space separators.
        parts = s.split(maxsplit=1) if "  " not in s else s.split("  ", 1)
        if len(parts) != 2:
            continue
        _sha, listed_rel = parts[0].strip(), parts[1].strip()
        if listed_rel == rel_to_parent:
            return True
    return False


def verify(verif_root: Path = VERIF_ROOT) -> SmokeResult:
    """Run the smoke check against ``verif_root``.

    Returns a :class:`SmokeResult`. Pure -- does not print.
    """
    missing: list[Missing] = []
    present = 0
    for rel in REQUIRED_ARTIFACTS:
        target = verif_root / rel
        if not target.is_file():
            missing.append(Missing(path=rel, reason="absent"))
            continue
        present += 1
        if not _ledger_contains(verif_root, rel):
            missing.append(
                Missing(path=rel, reason="ledger_unlisted")
            )
    return SmokeResult(
        required=len(REQUIRED_ARTIFACTS),
        present=present,
        missing=tuple(missing),
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _format_report(result: SmokeResult) -> str:
    """Render a markdown-style report."""
    out: list[str] = []
    out.append("# Reproducibility smoke report")
    out.append("")
    out.append(
        f"- Required artifacts: **{result.required}**"
    )
    out.append(
        f"- Present on disk: **{result.present}**"
    )
    out.append(
        f"- Missing / mis-listed: **{len(result.missing)}**"
    )
    out.append("")
    if not result.missing:
        out.append("**All 12 headline-evidence artifacts present.**")
    else:
        out.append("## Missing")
        out.append("")
        for m in result.missing:
            out.append(f"- `{m.path}` ({m.reason})")
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Smoke-check the 12 headline-evidence artifacts under "
            "verification_outputs/ (paper-submission gate)."
        )
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print the one-line summary; suppress the full report.",
    )
    parser.add_argument(
        "--verif-root",
        type=Path,
        default=VERIF_ROOT,
        help=(
            "verification_outputs/ root (default: <repo>/verification_outputs). "
            "Test-only override."
        ),
    )
    return parser.parse_args(list(argv))


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    result = verify(verif_root=args.verif_root)
    n_missing = len(result.missing)
    summary = (
        f"smoke: required={result.required} "
        f"present={result.present} missing={n_missing}"
    )
    if args.quiet:
        print(summary)
    else:
        print(_format_report(result))
        print(summary)
    return 0 if n_missing == 0 else 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
