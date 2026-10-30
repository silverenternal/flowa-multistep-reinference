#!/usr/bin/env python3
"""Resolve every backticked repository path in the reviewer-facing docs.

``tools/check_doc_links.py`` resolves markdown *links* -- ``[text](target)``.
It deliberately ignores inline code spans, because a code span is usually an
example.  But in this project the code span is also how the docs point at
their evidence: ``tools/verify_reproducibility_smoke.py``,
``docs/headline-evidence/composite_axis_byte_stable/SOURCE.md``,
``verification_outputs/wave183-p4-figure-pLDDT-finer.png``.  Nothing checked
those, so a renamed tool or a moved evidence directory left the pointer
dangling while the prose still read as if it resolved.

Scope is the set of documents a reviewer actually reads:

* ``README.md`` / ``README.zh.md`` / ``AGENTS.md``
* ``docs/README.md`` (the documentation map) and ``docs/PAPER-EVIDENCE.md``
  (the cell-level evidence register)
* ``tnnls_submission/*.md`` (the submission package)

Deliberately out of scope, with reasons:

* ``CHANGELOG.md`` -- append-only history; an entry naming a file that was
  later deleted is a true statement about that release.
* ``docs/audit/`` and ``docs/drafts/`` -- audit records and working drafts
  cite artefacts as they stood at the time.  A citation into those trees
  (``docs/audit/wave233-p3-tier-aware.md``) is provenance, not a live pointer,
  so tokens whose path starts with either prefix are skipped.

Usage
-----
    python3 tools/check_reviewer_pointers.py
    python3 tools/check_reviewer_pointers.py --json
    python3 tools/check_reviewer_pointers.py --quiet
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Documents a reviewer reads.  ``docs/PAPER-EVIDENCE.md`` is generated but is
#: still a pointer surface: every cell row names its artefact.
SURFACES: tuple[str, ...] = (
    "README.md",
    "README.zh.md",
    "AGENTS.md",
    "docs/README.md",
    "docs/PAPER-EVIDENCE.md",
)

#: Tokens under these prefixes are historical citations, not live pointers.
EXEMPT_PREFIXES: tuple[str, ...] = ("docs/audit/", "docs/drafts/")

#: Directory prefixes that name a location inside this checkout.
PATH_PREFIXES: tuple[str, ...] = (
    "adaptive_reflow", "configs", "data", "docs", "paper-data", "reproduce",
    "scripts", "tests", "tnnls_submission", "tools", "verification_outputs",
)

#: Extensions that make a bare token a path rather than a symbol.
EXTENSIONS: tuple[str, ...] = (
    "bash", "bib", "cc", "cfg", "ckpt", "cpp", "csv", "go", "h", "hpp",
    "html", "ini", "ipynb", "jpeg", "jpg", "js", "json", "jsonl", "lean",
    "lock", "markdown", "md", "npy", "npz", "pdf", "png", "pt", "pth", "py",
    "pyi", "rst", "rs", "sh", "sql", "svg", "tex", "toml", "ts", "tsv",
    "tsx", "txt", "yaml", "yml",
)

TOKEN_RE: re.Pattern[str] = re.compile(
    r"`(?P<path>(?:" + "|".join(PATH_PREFIXES) + r")/[A-Za-z0-9_./-]+?"
    r"\.(?:" + "|".join(sorted(EXTENSIONS, key=len, reverse=True)) + r"))`"
)


def surfaces() -> list[Path]:
    """Return the documents in scope that exist on disk."""
    out = [REPO_ROOT / name for name in SURFACES]
    out += sorted((REPO_ROOT / "tnnls_submission").glob("*.md"))
    return [p for p in out if p.is_file()]


def collect() -> list[dict[str, str]]:
    """Return one row per dead pointer."""
    rows: list[dict[str, str]] = []
    for doc in surfaces():
        text = doc.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), 1):
            for match in TOKEN_RE.finditer(line):
                raw = match.group("path").rstrip(".,;:")
                if raw.startswith(EXEMPT_PREFIXES):
                    continue
                if (REPO_ROOT / raw).exists():
                    continue
                rows.append({
                    "source": str(doc.relative_to(REPO_ROOT)),
                    "line": str(lineno),
                    "target": raw,
                })
    return rows


def count_pointers() -> int:
    """Return the number of in-scope pointers examined."""
    total = 0
    for doc in surfaces():
        text = doc.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            for match in TOKEN_RE.finditer(line):
                raw = match.group("path").rstrip(".,;:")
                if raw.startswith(EXEMPT_PREFIXES):
                    continue
                total += 1
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    rows = collect()
    checked = count_pointers()

    if args.json:
        print(json.dumps(rows, indent=1))
        print(f"checked={checked} dead={len(rows)}", file=sys.stderr)
    else:
        if not args.quiet:
            for row in rows:
                print(f"{row['source']}:{row['line']}  ->  {row['target']}")
        print(f"checked={checked} dead={len(rows)}")

    if rows:
        print(f"FAIL: {len(rows)} dead pointer(s)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
