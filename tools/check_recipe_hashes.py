"""Verify the SHA-256 pins inside the per-cell reproduction recipes.

`paper-data/<cell>/*REPRODUCIBILITY_RECIPE.md` is what a reviewer follows to
re-derive a cell's headline from the frozen artifacts. Each recipe carries a
markdown table of `| path | sha256 |` rows. This tool resolves every row and
recomputes the hash, so a recipe cannot silently point at a file that has since
changed.

Path convention: a row is resolved against the repo root first, then against
`paper-data/` (R2 and R5a write cell-relative paths, the rest write repo-root
paths). Both conventions are accepted; nothing else is.

Known-stale rows are listed in `KNOWN_STALE` with the reason, and
`tests/test_recipe_hashes.py` fails if an exemption outlives the row it covers.

Usage:
    python3 tools/check_recipe_hashes.py [--quiet]
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER_DATA = ROOT / "paper-data"
RECIPE_GLOB = "**/*REPRODUCIBILITY_RECIPE.md"

ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`([0-9a-f]{64})`\s*\|", re.M)

# (recipe file name, path, pinned hash) -> reason
KNOWN_STALE: dict[tuple[str, str, str], str] = {}


def _resolve(path: str) -> Path | None:
    for base in (ROOT, PAPER_DATA):
        candidate = base / path
        if candidate.is_file():
            return candidate
    return None


def collect() -> tuple[list[tuple[str, str, str, Path | None]], list[str]]:
    rows: list[tuple[str, str, str, Path | None]] = []
    problems: list[str] = []
    docs = sorted(PAPER_DATA.glob(RECIPE_GLOB))
    if not docs:
        problems.append(f"no recipe docs found under {PAPER_DATA}")
    for doc in docs:
        for path, sha in ROW.findall(doc.read_text(encoding="utf-8")):
            rows.append((doc.name, path, sha, _resolve(path)))
    return rows, problems


def check() -> tuple[list[str], int, int]:
    """Return (errors, n_rows, n_stale)."""
    rows, problems = collect()
    errors = list(problems)
    stale = 0
    for doc, path, sha, resolved in rows:
        if resolved is None:
            errors.append(f"{doc}: path does not resolve: {path}")
            continue
        actual = hashlib.sha256(resolved.read_bytes()).hexdigest()
        if actual == sha:
            continue
        if (doc, path, sha) in KNOWN_STALE:
            stale += 1
            continue
        errors.append(f"{doc}: {path}: pinned {sha[:12]}, actual {actual[:12]}")
    for doc, path, sha in KNOWN_STALE:
        if not any(d == doc and p == path and s == sha for d, p, s, _ in rows):
            errors.append(f"{doc}: stale exemption no longer matches any row: {path}")
    return errors, len(rows), stale


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    errors, n_rows, n_stale = check()
    if not args.quiet or errors:
        print(f"recipes: rows={n_rows} known_stale={n_stale} unknown={len(errors)}")
        for err in errors:
            print(f"  {err}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
