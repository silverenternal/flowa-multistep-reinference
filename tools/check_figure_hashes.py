#!/usr/bin/env python3
"""Verify the figure digests quoted in ``tnnls_submission/figures.md``.

``figures.md`` is the editor-facing figure inventory: 37 rows, each naming a
PNG, its SHA-256 and its byte size.  Those digests are the only machine-checkable
statement the package makes about the figure files, and nothing verified them.
``tools/check_artifact_hashes.py`` covers the two root READMEs (three
manuscript artifacts), ``tools/check_submission_manifest.py`` covers the
``tnnls_submission/`` ledgers, and ``tools/check_paper_data_manifest.py``
covers ``paper-data/*/SOURCE.md``; the figure table sat between all three.

The check is a join, not a recomputation of anything: every row's digest and
size must equal the file's real digest and size, and the file must be findable
under one of the four tracked roots.  A row that resolves to nothing is a
failure rather than a skip -- the table's whole purpose is to let an editor
confirm they hold the shipped bytes.

Fail-closed: if the table parses to zero rows, the check reports that and
exits non-zero.  A regex that stops matching must not look like a clean table.

Usage
-----
    python3 tools/check_figure_hashes.py
    python3 tools/check_figure_hashes.py --json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIGURES_MD = REPO_ROOT / "tnnls_submission" / "figures.md"

# Every figure row resolves under one of these.  ``docs/figures`` holds the
# manuscript figures, ``paper-figures/`` the appendix/main renders, and
# ``paper-data/*/`` the per-cell source panels.
SEARCH_ROOTS: tuple[str, ...] = (
    "docs/figures",
    "paper-figures/main",
    "paper-figures/appendix",
    "paper-data",
)

ROW_RE = re.compile(
    r"^\|\s*(?P<idx>\d+)\s*"
    r"\|\s*`(?P<name>[^`]+)`\s*"
    r"\|\s*`(?P<sha>[0-9a-f]{64})`\s*"
    r"\|\s*(?P<size>\d+)\s*\|",
    re.M,
)


class Problem:
    """One row that does not hold."""

    __slots__ = ("index", "name", "kind", "detail")

    def __init__(self, index: str, name: str, kind: str, detail: str) -> None:
        self.index = index
        self.name = name
        self.kind = kind
        self.detail = detail

    def as_dict(self) -> dict[str, str]:
        return {
            "index": self.index,
            "name": self.name,
            "kind": self.kind,
            "detail": self.detail,
        }

    def __str__(self) -> str:
        return f"row {self.index} ({self.name}): {self.kind} -- {self.detail}"


def parse_rows(text: str) -> list[tuple[str, str, str, int]]:
    """Return ``[(index, name, sha256, size)]`` for every digest row."""
    return [
        (m.group("idx"), m.group("name"), m.group("sha"), int(m.group("size")))
        for m in ROW_RE.finditer(text)
    ]


def index_roots(root: Path, roots: tuple[str, ...]) -> dict[str, list[Path]]:
    """Map basename -> every file with that name under the given roots."""
    found: dict[str, list[Path]] = {}
    for rel in roots:
        base = root / rel
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file():
                found.setdefault(path.name, []).append(path)
    return found


def check(
    figures_md: Path = FIGURES_MD,
    *,
    root: Path = REPO_ROOT,
    roots: tuple[str, ...] = SEARCH_ROOTS,
) -> list[Problem]:
    """Return every problem found in ``figures_md``.  Empty list means clean."""
    text = figures_md.read_text(encoding="utf-8")
    rows = parse_rows(text)
    if not rows:
        return [
            Problem(
                "-",
                str(figures_md),
                "unparsed",
                "no digest rows matched; the table format changed, so this "
                "check verified nothing",
            )
        ]

    index = index_roots(root, roots)
    problems: list[Problem] = []
    for idx, name, sha, size in rows:
        candidates = index.get(name, [])
        if not candidates:
            problems.append(
                Problem(idx, name, "missing", f"not found under {', '.join(roots)}")
            )
            continue
        # The same figure is often copied into more than one tracked root
        # (docs/figures plus paper-figures/, or a paper-data cell).  Copies are
        # fine as long as every one of them is the file the table describes;
        # two copies that disagree mean the table pins one of them and the
        # other is a stale duplicate.
        digests = {c: hashlib.sha256(c.read_bytes()).hexdigest() for c in candidates}
        matching = [c for c, d in digests.items() if d == sha]
        if not matching:
            shown = ", ".join(
                f"{c.relative_to(root)}={d[:12]}..." for c, d in digests.items()
            )
            problems.append(
                Problem(idx, name, "hash", f"quoted {sha[:12]}..., on disk {shown}")
            )
            continue
        if len(matching) != len(digests):
            stale = [c for c in digests if c not in matching]
            problems.append(
                Problem(
                    idx,
                    name,
                    "divergent",
                    "stale copy at "
                    + ", ".join(str(c.relative_to(root)) for c in stale),
                )
            )
            continue
        data = matching[0].read_bytes()
        if len(data) != size:
            problems.append(
                Problem(idx, name, "size", f"quoted {size} bytes, file is {len(data)}")
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    parser.add_argument(
        "--figures",
        type=Path,
        default=FIGURES_MD,
        help="figures.md to check (default: tnnls_submission/figures.md)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="repository root the figure roots are resolved against",
    )
    args = parser.parse_args(argv)

    problems = check(args.figures, root=args.root)
    rows = len(parse_rows(args.figures.read_text(encoding="utf-8")))

    if args.json:
        print(json.dumps({"rows": rows, "problems": [p.as_dict() for p in problems]}, indent=2))
    else:
        for p in problems:
            print(f"FAIL  {p}")
        if problems:
            print(f"\nFAIL: {len(problems)} of {rows} figure rows do not hold")
        else:
            print(f"OK: {rows} figure rows match the files on disk")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
