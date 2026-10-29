#!/usr/bin/env python3
"""Verify the SHA-256 rows in ``paper-data/MANIFEST.md``.

``paper-data/SHA256SUMS`` is the canonical per-file ledger and is checked by
``tools/check_evidence_ledgers.py``.  ``MANIFEST.md`` is the human-readable
catalogue that reviewers read first, and it carries its own hash column — a
second copy of the same facts, which had drifted on five rows (four symlinked
artifacts re-written by later waves, plus ``headline-evidence/README.md``).

This tool resolves every ``| `path` | `sha256` |`` row against
``paper-data/`` and fails on any mismatch.  A row whose file is absent is a
failure too: unlike the submission package there is no superseded-artifact
convention here.

Usage
-----
    python3 tools/check_paper_data_manifest.py
    python3 tools/check_paper_data_manifest.py --quiet
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PKG = REPO_ROOT / "paper-data"
MANIFEST = PKG / "MANIFEST.md"

ROW_RE = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$", re.MULTILINE)


def check() -> list[tuple[str, str]]:
    """Return (name, status) for every row."""
    out: list[tuple[str, str]] = []
    for name, sha in ROW_RE.findall(MANIFEST.read_text(encoding="utf-8")):
        path = PKG / name
        if not path.is_file():
            out.append((name, "MISSING"))
            continue
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        out.append((name, "ok" if got == sha else f"STALE({got[:12]} != {sha[:12]})"))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    if not MANIFEST.is_file():
        print(f"missing {MANIFEST}", file=sys.stderr)
        return 2

    rows = check()
    bad = [r for r in rows if r[1] != "ok"]
    if not args.quiet:
        for name, status in rows:
            print(f"{name.ljust(60)}  {status}")
    print(f"\nrows={len(rows)} ok={len(rows) - len(bad)} bad={len(bad)}")
    for name, status in bad:
        print(f"  {status}  {name}", file=sys.stderr)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
