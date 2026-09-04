r"""CLI: machine-checkable E.2 -- count docs that cross-reference >= 1 paper theorem.

E.2 ("Docs cross-referencing >= 1 paper theorem, machine-checkable via A.5")
in ``todo/framework-internal-metrics.md`` requires a machine-checkable
ratio of top-level ``docs/*.md`` files that mention at least one of the
following paper anchors:

* ``Theorem N`` / ``Theorem N.M`` (e.g. ``Theorem 1``, ``Theorem 2.3``)
* ``Lemma N``  / ``Lemma N.M``
* ``Proposition N``
* ``Corollary N``
* ``Remark N``
* ``paper section X.Y`` (e.g. ``paper section 4.2``)
* ``paper §X.Y`` (e.g. ``paper §3.1``)
* ``paper line N`` (e.g. ``paper line 87``)
* ``JMAA`` (the underlying paper, J. Math. Anal. Appl.)
* ``arXiv:NNNN.NNNNN`` (any arXiv ID)
* ``arXiv:N.NNNNN`` (some refs omit the trailing ``vN``)

The audit script accepts a list of paths (default: every top-level
``docs/*.md`` file) and emits a one-line-per-file report, plus a summary
with the ratio and a verdict (``PASS`` if ``ratio >= 0.9``).

Output is intentionally simple so it can be embedded in CI / pre-merge
checks:

::

    $ python tools/check_doc_paper_refs.py docs/*.md
    PASS  E.2 ratio 0.93 (28 / 30 docs reference a paper theorem)

Exit codes:

* ``0`` -- ratio >= 0.9 (E.2 gate MET) **OR** no docs supplied
* ``1`` -- ratio <  0.9 (E.2 gate NOT MET)
* ``2`` -- invocation error

This is the tool that backs metric ``E.2`` and is the live
machine-checkable replacement for the ad-hoc grep command in
``docs/baseline-audit-report.md`` §E.2.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable
from pathlib import Path

# ---------------------------------------------------------------------------
# Layout / configuration
# ---------------------------------------------------------------------------


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
"""Resolved repo root (one level above ``tools/``)."""

DOCS_DIR: Path = REPO_ROOT / "docs"
"""Top-level docs directory whose ``*.md`` files are scanned."""

E2_TARGET_RATIO: float = 0.9
"""E.2 target ratio per ``framework-internal-metrics.md`` §1.E."""

# ---------------------------------------------------------------------------
# Regex
# ---------------------------------------------------------------------------


# Match a numbered paper theorem/lemma/proposition/corollary/remark.
# Allow whitespace before the number (matches the audit's pattern).
PAPER_STATEMENT_RE = re.compile(
    r"\b(?:Theorem|Lemma|Proposition|Corollary|Remark)\s+\d+(?:\.\d+)?"
)

# Match a paper section / line / §-style reference (e.g. "paper section 4.2",
# "paper §3.1", "paper line 87"). Case-insensitive because authors sometimes
# write "Paper section 4" with a capital P.
PAPER_SECTION_RE = re.compile(
    r"\bpaper\s+(?:section|line)\s+\d+(?:\.\d+)?|\bpaper\s*§\s*\d+(?:\.\d+)?",
    re.IGNORECASE,
)

# Match an arXiv reference (e.g. arXiv:2410.04997 or arXiv:2605.22252).
ARXIV_RE = re.compile(r"\barXiv:\d{4}\.\d{4,5}(?:v\d+)?")

# Match the JMAA paper (J. Math. Anal. Appl.) by acronym.
JMAA_RE = re.compile(r"\bJMAA\b")

# Union of all anchors. A doc is "referencing" if ANY of these match.
PAPER_ANCHOR_RES: tuple[re.Pattern[str], ...] = (
    PAPER_STATEMENT_RE,
    PAPER_SECTION_RE,
    ARXIV_RE,
    JMAA_RE,
)


def doc_references_paper(doc_path: Path) -> tuple[bool, list[str]]:
    """Return (references_any_paper, list_of_matched_anchors).

    Reads the doc as text and runs each of ``PAPER_ANCHOR_RES`` against
    its body. The matched strings are returned so the caller can show
    *what* matched in the verbose report.
    """
    text = doc_path.read_text(encoding="utf-8", errors="replace")
    matched: list[str] = []
    for pat in PAPER_ANCHOR_RES:
        for m in pat.finditer(text):
            matched.append(m.group(0))
    return (len(matched) > 0), matched


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _collect_docs(roots: Iterable[Path]) -> list[Path]:
    """Resolve the input paths to a sorted list of markdown files.

    If a root is a directory, expand it to its top-level ``*.md`` files.
    Files outside ``DOCS_DIR`` are accepted (the tool is intentionally
    agnostic); pass ``docs/*.md`` on the CLI for the standard E.2 scan.
    """
    out: list[Path] = []
    for r in roots:
        if r.is_dir():
            out.extend(sorted(p for p in r.glob("*.md") if p.is_file()))
        elif r.is_file() and r.suffix == ".md":
            out.append(r)
    # Dedup, preserve order
    seen: set[Path] = set()
    deduped: list[Path] = []
    for p in out:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    return deduped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_doc_paper_refs.py",
        description=(
            "Machine-checkable E.2 metric: count docs that reference >=1 "
            "paper theorem/lemma/proposition/section/arXiv/JMAA anchor."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DOCS_DIR],
        help=(
            "Markdown files or directories to scan (default: docs/). "
            "Directories expand to their top-level *.md files."
        ),
    )
    parser.add_argument(
        "--target",
        type=float,
        default=E2_TARGET_RATIO,
        help=f"Pass threshold ratio (default: {E2_TARGET_RATIO}).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print the summary line (no per-file table).",
    )
    parser.add_argument(
        "--no-exit-code",
        action="store_true",
        help="Always exit 0 even if the ratio is below --target.",
    )
    args = parser.parse_args(argv)

    docs = _collect_docs(args.paths)
    if not docs:
        print("ERROR: no markdown files found under the given paths.", file=sys.stderr)
        return 2

    n_total = len(docs)
    n_ref = 0
    non_ref: list[str] = []
    if not args.quiet:
        print(f"{'doc':<55}{'refs?':<8}{'example match'}")
        print(f"{'':-<55}{'':-<8}{'':-<40}")
    for doc in docs:
        ref, matched = doc_references_paper(doc)
        if ref:
            n_ref += 1
            example = matched[0] if matched else "(matched)"
        else:
            non_ref.append(doc.name)
            example = "(no match)"
        if not args.quiet:
            print(f"{doc.name:<55}{('YES' if ref else 'no'):<8}{example}")

    ratio = n_ref / n_total if n_total else 0.0
    verdict = "PASS" if ratio >= args.target else "FAIL"
    print(
        f"\n{verdict}  E.2 ratio {ratio:.3f} ({n_ref} / {n_total} docs reference a paper theorem) "
        f"-- target >= {args.target:.2f}"
    )
    if non_ref:
        print(f"\nNon-referencing docs ({len(non_ref)}):")
        for n in non_ref:
            print(f"  - {n}")
        print(
            "\nTo improve the ratio, add at least one anchor of the form "
            "'Theorem N' / 'Lemma N' / 'Proposition N' / 'paper section X.Y' "
            "/ 'arXiv:NNNN.NNNNN' / 'JMAA' to each non-referencing doc."
        )
    if args.no_exit_code:
        return 0
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())