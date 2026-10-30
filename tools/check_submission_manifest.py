#!/usr/bin/env python3
"""Verify the SHA-256 / size rows in ``tnnls_submission/MANIFEST.md``.

The manifest is the reviewer's integrity anchor: each row names a file, its
byte size and its SHA-256.  This script resolves every row against the tree
and reports ``ok`` / ``STALE`` / ``MISSING``.

Two exceptions are understood by the checker:

* Rows whose description says ``SUPERSEDED`` or ``archived for historical``
  are historical artifacts that are allowed to be absent.
* ``MANIFEST.md`` cannot carry its own hash (writing the hash changes the
  file).  Its row is deliberately hash-free and points at the sibling
  ``SHA256SUMS`` ledger, which the checker verifies separately.

``KNOWN_STALE`` lists rows that are out of date and awaiting an authorised
refresh.  It is empty as of 2026-10-29; anything stale now fails the run.

The 2026-10-27 packaging addendum at the top of the manifest declares the
current hashes of the three manuscript artifacts.  Those three are checked
against the addendum as well as against their table rows, so an addendum
that drifts from the table is reported rather than silently preferred.

``SHA256SUMS`` is the authoritative ledger (a file cannot carry its own
hash).  The checker requires it to cover ``MANIFEST.md`` and every table row,
and to agree with the working tree.

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
KNOWN_STALE: frozenset[str] = frozenset()

#: Rows naming an artifact the repository deliberately does not carry, so a
#: fresh clone cannot hash them.  The row still records the hash the packaging
#: step must reproduce; the checker reports it as ``packaging-output`` rather
#: than ``MISSING`` so the gate stays honest on a clone instead of going red.
#:
#: * ``supplementary_bundle.zip`` -- 148 MB archive built from ``paper-data/``
#:   plus the sidecar ``SHA256SUMS``.  ``.gitignore`` keeps it out of the tree
#:   (see its comment at line 93).  Verify it locally after rebuilding.
KNOWN_ABSENT: frozenset[str] = frozenset({"supplementary_bundle.zip"})

#: (path relative to the repo root, sha256, bytes) from the packaging addendum.
CURRENT_ARTIFACTS: tuple[tuple[str, str, int], ...] = (
    ("docs/drafts/paper-A-final.md",
     "417f31836240760b60ceae7e274c9b3c705b661b395f258b64b18f605d6a3ea4", 224429),
    ("docs/drafts/paper-A-final.tex",
     "e28dca14db086d0e235f167aaacd909d6d3a67a12978726bbf48604301c998df", 74243),
    ("docs/drafts/paper-A-final.pdf",
     "ef9b401d664c2d911b233178296060b598b4fa6f5a87a516b42f893ee51d8e3c", 615789),
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
            if name in KNOWN_ABSENT:
                status = "packaging-output"
            else:
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


def check_ledger() -> list[tuple[str, str]]:
    """Verify ``tnnls_submission/SHA256SUMS`` against the tree.

    A file cannot carry its own hash, so ``MANIFEST.md`` is pinned only here.
    Every other row that has a hash in the manifest must also appear in the
    ledger, otherwise the two surfaces can drift apart.
    """
    ledger = PKG / "SHA256SUMS"
    if not ledger.is_file():
        return [("SHA256SUMS", "MISSING")]
    out: list[tuple[str, str]] = []
    covered: set[str] = set()
    for line in ledger.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        sha, _, name = line.partition("  ")
        name = name.strip()
        if not name:
            out.append((line, "MALFORMED"))
            continue
        covered.add(name)
        path = (PKG / name).resolve()
        if not path.is_file():
            out.append((name, "packaging-output" if name in KNOWN_ABSENT
                        else "MISSING"))
            continue
        got, _ = _sha(path)
        out.append((name, "ok" if got == sha else "DRIFT"))
    if "MANIFEST.md" not in covered:
        out.append(("MANIFEST.md", "NOT_IN_LEDGER"))
    for name, status in check_rows():
        if status == "ok" and name not in covered:
            out.append((name, "NOT_IN_LEDGER"))
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
    ledger = check_ledger()

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
    ledger_bad = [a for a in ledger if a[1] not in ("ok", "packaging-output")]
    print(f"\nrows={len(rows)} known_stale={stale} unknown={len(unknown)} "
          f"addendum_drift={len(art_bad)} ledger_drift={len(ledger_bad)}")
    for name, status in unknown:
        print(f"  {status}  {name}", file=sys.stderr)
    for rel, status in art_bad:
        print(f"  addendum {status}  {rel}", file=sys.stderr)
    for name, status in ledger_bad:
        print(f"  ledger {status}  {name}", file=sys.stderr)
    return 0 if not unknown and not art_bad and not ledger_bad else 1


if __name__ == "__main__":
    sys.exit(main())
