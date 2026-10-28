"""Verify every SHA256SUMS ledger in the evidence bundles.

The submission points reviewers at `sha256sum --check` over the frozen
artifacts. That only works if each ledger is (a) actually a checksum file and
(b) current. This tool runs every ledger under `paper-data/` and
`verification_outputs/` and classifies what it finds:

* ``ok``          — every line matches;
* ``self``        — the only failure is the ledger's own line, which is
  expected (writing a hash of the file into the file changes the file) and is
  documented per-ledger in the recipe docs;
* ``real``        — a listed artifact no longer matches its pinned hash;
* ``not_a_ledger`` — the file is named SHA256SUMS but holds prose.

Real failures and misnamed ledgers are listed in `KNOWN_ISSUES` with the
reason. `tests/test_evidence_ledgers.py` fails on any unlisted problem and on
an exemption that outlives the issue it covers.

Usage:
    python3 tools/check_evidence_ledgers.py [--quiet]
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEARCH_ROOTS = ("paper-data", "verification_outputs")
LEDGER_NAME = "SHA256SUMS"

LINE = re.compile(r"^([0-9a-f]{64})\s+\*?(.+)$")

# (ledger path relative to repo root, kind, subject) -> reason
KNOWN_ISSUES: dict[tuple[str, str, str], str] = {
    (
        "paper-data/SHA256SUMS",
        "real",
        "headline-evidence/README.md",
    ): (
        "the ledger was frozen at the Wave 328 packaging commit and the README "
        "was rewritten in the same commit without regenerating it. The README "
        "carries no number the paper uses; regenerating the ledger is the fix."
    ),
    (
        "verification_outputs/r3_n1000_3seed_fixed_q4_2026/SHA256SUMS",
        "real",
        "wave338-p5-r3-n1000-paired.json",
    ): (
        "commit 40d6bb55 (GAP-27-R3-POWER, seed-level CI defect fix) rewrote the "
        "paired JSON after the ledger was written. The JSON on disk is the "
        "corrected one and is what reproduce/03_R3_FlowMol3.sh verifies; the "
        "ledger line is stale, not the artifact."
    ),
    (
        "verification_outputs/wave349-r1-3seed-gpu/SHA256SUMS",
        "not_a_ledger",
        "",
    ): (
        "the file is a markdown evidence note, not a checksum list: "
        "`sha256sum --check` answers 'no properly formatted checksum lines "
        "found'. Its two manifest hashes do match; the file should be renamed "
        "(e.g. EVIDENCE.md) and a real ledger added."
    ),
}


def _verify(ledger: Path) -> tuple[str, int, list[str]]:
    """Return (kind, n_entries, failing_subjects)."""
    entries: list[tuple[str, str]] = []
    for raw in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
        match = LINE.match(raw)
        if match:
            entries.append((match.group(1), match.group(2).strip()))
    if not entries:
        return "not_a_ledger", 0, []

    failing: list[str] = []
    self_only = False
    for sha, rel in entries:
        target = ledger.parent / rel
        if not target.is_file():
            failing.append(rel)
            continue
        if hashlib.sha256(target.read_bytes()).hexdigest() != sha:
            if Path(rel).name == LEDGER_NAME:
                self_only = True
            else:
                failing.append(rel)
    if not failing and self_only:
        return "self", len(entries), []
    if not failing:
        return "ok", len(entries), []
    return "real", len(entries), failing


def check() -> tuple[list[str], dict[str, int], int]:
    errors: list[str] = []
    counts: dict[str, int] = {}
    n_known = 0
    seen: set[tuple[str, str, str]] = set()

    ledgers = sorted(
        p
        for base in SEARCH_ROOTS
        for p in (ROOT / base).rglob(LEDGER_NAME)
        if p.is_file()
    )
    if not ledgers:
        errors.append(f"no {LEDGER_NAME} found under {SEARCH_ROOTS}")

    for ledger in ledgers:
        rel = ledger.relative_to(ROOT).as_posix()
        kind, n_entries, failing = _verify(ledger)
        counts[kind] = counts.get(kind, 0) + 1
        if kind in ("ok", "self"):
            continue
        if kind == "not_a_ledger":
            key = (rel, kind, "")
            seen.add(key)
            if key in KNOWN_ISSUES:
                n_known += 1
            else:
                errors.append(f"{rel}: named {LEDGER_NAME} but holds no checksum lines")
            continue
        for subject in failing:
            key = (rel, kind, subject)
            seen.add(key)
            if key in KNOWN_ISSUES:
                n_known += 1
            else:
                errors.append(f"{rel}: {subject}: hash does not match")

    for key in KNOWN_ISSUES:
        if key not in seen:
            errors.append(
                f"{key[0]}: exemption no longer matches a live issue ({key[1]}: {key[2]!r})"
            )
    return errors, counts, n_known


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    errors, counts, n_known = check()
    if not args.quiet or errors:
        summary = " ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        print(f"ledgers: {summary} known={n_known} unknown={len(errors)}")
        for err in errors:
            print(f"  {err}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
