#!/usr/bin/env python3
"""Verify the SHA-256 rows in ``paper-data/``.

``paper-data/SHA256SUMS`` is the canonical per-file ledger and is checked by
``tools/check_evidence_ledgers.py``.  Two human-readable surfaces duplicate it
and are checked here:

``MANIFEST.md``
    the catalogue reviewers read first, which carries its own hash column.
    It had drifted on five rows (four symlinked artifacts re-written by later
    waves, plus ``headline-evidence/README.md``).
``<cell>/SOURCE.md``
    the per-cell provenance table.  It is a *third* copy of the same facts and
    was missed by the manifest sweep: four rows were stale (``R5b`` one,
    ``R6`` three), all pointing at artifacts that a later wave had rewritten.

This tool resolves every ``| `path` | ... | `sha256` |`` row against the
directory that contains the table, then against the repository root and
``paper-data/``.  A row whose file is absent is a failure too: unlike the
submission package there is no superseded-artifact convention here.

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
SOURCE_ROW_RE = re.compile(r"^\| `([^`]+)` \|.*?`([0-9a-f]{64})`", re.MULTILINE)


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


def check_sources() -> list[tuple[str, str, str]]:
    """Return (source file, artifact, status) for every per-cell SOURCE.md row."""
    out: list[tuple[str, str, str]] = []
    for md in sorted(PKG.glob("*/*.md")):
        if md.name == "MANIFEST.md":
            continue
        for name, sha in SOURCE_ROW_RE.findall(md.read_text(encoding="utf-8")):
            path = next(
                (c for c in (md.parent / name, REPO_ROOT / name, PKG / name) if c.is_file()),
                None,
            )
            rel = str(md.relative_to(REPO_ROOT))
            if path is None:
                out.append((rel, name, "MISSING"))
                continue
            got = hashlib.sha256(path.read_bytes()).hexdigest()
            out.append((rel, name, "ok" if got == sha else f"STALE({got[:12]} != {sha[:12]})"))
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
    sources = check_sources()
    bad_sources = [r for r in sources if r[2] != "ok"]
    if not args.quiet:
        for name, status in rows:
            print(f"{name.ljust(60)}  {status}")
        for rel, name, status in sources:
            print(f"{rel}:{name.ljust(48)}  {status}")
    print(
        f"\nrows={len(rows)} ok={len(rows) - len(bad)} bad={len(bad)} "
        f"sources={len(sources)} source_bad={len(bad_sources)}"
    )
    for name, status in bad:
        print(f"  {status}  {name}", file=sys.stderr)
    for rel, name, status in bad_sources:
        print(f"  {status}  {rel}:{name}", file=sys.stderr)
    return 0 if not bad and not bad_sources else 1


if __name__ == "__main__":
    sys.exit(main())
