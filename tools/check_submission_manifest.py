#!/usr/bin/env python3
"""Verify the SHA-256 / size rows in ``tnnls_submission/MANIFEST.md``.

The manifest is the reviewer's integrity anchor: each row names a file, its
byte size and its SHA-256.  This script resolves every row against the tree
and reports ``ok`` / ``STALE`` / ``MISSING``.

Two exceptions are understood by the checker:

* Rows whose description says ``SUPERSEDED`` or ``archived for historical``
  are historical artifacts that are allowed to be absent.
* ``MANIFEST.md`` cannot carry its own hash (writing the hash changes the
  file), so that row is reported separately and never counted as drift.

``KNOWN_STALE`` lists the rows that are currently out of date and are
documented in ``docs/audit/manifest-hash-staleness.md``.  They do not fail
the run while the frozen package awaits an authorised refresh; anything
else does.

The 2026-10-27 packaging addendum at the top of the manifest declares the
current hashes of the three manuscript artifacts.  Those three are checked
against the addendum rather than the (older) table row, because the
addendum states that it supersedes every reading that differs.

Usage
-----
    python3 tools/check_submission_manifest.py
    python3 tools/check_submission_manifest.py --quiet
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PKG = REPO_ROOT / "tnnls_submission"
MANIFEST = PKG / "MANIFEST.md"

#: Rows that are stale today and await an authorised refresh of the frozen
#: manifest.  Delete an entry once the row matches again.
KNOWN_STALE: frozenset[str] = frozenset({
    "README.md",
    "cover_letter.md",
    "highlights.md",
    "tables.md",
    "figures.md",
    "submission_checklist.md",
    # The table rows for the three manuscript artifacts predate the
    # 2026-10-27 packaging addendum; the addendum is authoritative and is
    # checked separately below.
    "../docs/drafts/paper-A-final.md",
    "../docs/drafts/paper-A-final.tex",
    "../docs/drafts/paper-A-final.pdf",
})

#: (path relative to the repo root, sha256, bytes) from the packaging addendum.
CURRENT_ARTIFACTS: tuple[tuple[str, str, int], ...] = (
    ("docs/drafts/paper-A-final.md",
     "b66ea07a70a9ddae7a9d43e708625b2320424c4a3d4957b79862454e5b22b97a", 226324),
    ("docs/drafts/paper-A-final.tex",
     "0847cd1e394387b05514b061c0657214e2deeba148d0fc5842607df050153309", 74254),
    ("docs/drafts/paper-A-final.pdf",
     "8b94570ccb9a8a8619e90039b7563b5028d53c9d47130cd2df3b401dde418e9d", 615789),
)

ROW_RE = re.compile(r"^\| `([^`]+)` \| (\d+) \| `([0-9a-f]{64})` \| (.*?) \|$", re.M)


def _sha(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def check_rows() -> list[tuple[str, str]]:
    """Return (name, status) for every manifest row."""
    out: list[tuple[str, str]] = []
    for name, size, sha, desc in ROW_RE.findall(MANIFEST.read_text()):
        path = (PKG / name).resolve()
        if not path.is_file():
            status = ("superseded" if ("SUPERSEDED" in desc or
                                       "archived for historical" in desc)
                      else "MISSING")
        else:
            got, nbytes = _sha(path)
            if got == sha and nbytes == int(size):
                status = "ok"
            elif name == "MANIFEST.md":
                status = "self-reference"
            else:
                status = f"STALE({nbytes} vs {size} bytes)"
        out.append((name, status))
    return out


def check_artifacts() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for rel, sha, size in CURRENT_ARTIFACTS:
        path = REPO_ROOT / rel
        if not path.is_file():
            out.append((rel, "MISSING"))
            continue
        got, nbytes = _sha(path)
        if got == sha and nbytes == size:
            out.append((rel, "ok"))
        else:
            out.append((rel, f"DRIFT({nbytes} vs {size} bytes)"))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    if not MANIFEST.is_file():
        print(f"missing {MANIFEST}", file=sys.stderr)
        return 2

    rows = check_rows()
    arts = check_artifacts()

    unknown: list[tuple[str, str]] = []
    stale = 0
    for name, status in rows:
        if status.startswith("STALE"):
            if name in KNOWN_STALE:
                stale += 1
            else:
                unknown.append((name, status))
        elif status in ("MISSING",):
            unknown.append((name, status))
        if not args.quiet:
            tag = ("known-stale" if name in KNOWN_STALE and status.startswith("STALE")
                   else status)
            print(f"{name.ljust(46)}  {tag}")

    if not args.quiet:
        print()
        for rel, status in arts:
            print(f"{rel.ljust(46)}  {status}  (packaging addendum)")

    art_bad = [a for a in arts if a[1] != "ok"]
    print(f"\nrows={len(rows)} known_stale={stale} unknown={len(unknown)} "
          f"addendum_drift={len(art_bad)}")
    for name, status in unknown:
        print(f"  {status}  {name}", file=sys.stderr)
    for rel, status in art_bad:
        print(f"  addendum {status}  {rel}", file=sys.stderr)
    return 0 if not unknown and not art_bad else 1


if __name__ == "__main__":
    sys.exit(main())
