r"""CLI: machine-checkable E.2 -- paper-statement anchor coverage.

E.2 is defined in ``docs/GATES.md`` §"Paper grounding" as:

    ``G-FRAMEWORK-HEALTH`` includes the E.2 doc cross-reference ratio
    whose machine-checkable anchor matches the
    ``tools/check_doc_paper_refs.py`` patterns ... When
    ``G-FRAMEWORK-HEALTH`` passes, every A.0 paper statement has at
    least one doc anchor.

The gate's *meaning* is statement coverage, and that is what decides the
exit code: every numbered statement in the A.0 inventory
(``docs/baseline-audit-report.md`` §A.0) must be anchored by at least one
document outside the inventory itself.

The tool also reports -- informationally, never as a pass/fail -- the
fraction of top-level ``docs/*.md`` pages that cite any anchor.  That
ratio was the original E.2 implementation and it measures the transpose
of the gate: it drops whenever the docs tree gains a page with no theory
content (a release checklist, a config reference), even though no
statement lost its anchor.  It is still printed because it is cheap and
it points at pages that might *deserve* a citation, but it does not gate
unless ``--ratio-gate`` is passed.

Anchors:

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

The statement set is read from the inventory rather than hard-coded, so a
statement added to A.0 enters the check without editing this file.

Usage::

    $ python tools/check_doc_paper_refs.py
    $ python tools/check_doc_paper_refs.py --quiet
    $ python tools/check_doc_paper_refs.py docs/*.md --ratio-gate

Exit codes:

* ``0`` -- every A.0 statement is anchored (E.2 gate MET)
* ``1`` -- at least one A.0 statement has no doc anchor (E.2 gate NOT MET),
  or ``--ratio-gate`` was passed and the doc ratio is below ``--target``
* ``2`` -- invocation error (no inventory, no docs, unreadable file)
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
"""Docs directory whose ``*.md`` files are scanned."""

INVENTORY: Path = DOCS_DIR / "baseline-audit-report.md"
"""Holds the A.0 paper-statement inventory (the statement set's source)."""

INVENTORY_SECTION_PREFIX: str = "### A.0.1"
"""Heading that opens the "implemented statements" table inside A.0.

Only this table's *Statement* column defines the gate.  ``### A.0.2``
lists statements that are deliberately NOT implemented (Proposition 1,
4, 5 are recorded there as gaps G5/G6), so including them would make the
gate demand anchors for statements the project decided not to surface.
"""

E2_TARGET_RATIO: float = 0.9
"""Legacy E.2 doc-coverage target, kept for the ``--ratio-gate`` diagnostic."""

# ---------------------------------------------------------------------------
# Regex
# ---------------------------------------------------------------------------


# Match a numbered paper theorem/lemma/proposition/corollary/remark.
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
# A.0 statement set
# ---------------------------------------------------------------------------


def read_inventory_section(inventory: Path = INVENTORY) -> str:
    """Return the text of the A.0.1 subsection, up to the next heading."""
    if not inventory.is_file():
        raise FileNotFoundError(f"A.0 inventory not found: {inventory}")
    lines = inventory.read_text(encoding="utf-8", errors="replace").splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith(INVENTORY_SECTION_PREFIX):
            start = i
            break
    if start is None:
        raise ValueError(
            f"no {INVENTORY_SECTION_PREFIX!r} heading in {inventory}"
        )
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## ") or lines[j].startswith("### "):
            end = j
            break
    return "\n".join(lines[start:end])


def a0_statements(inventory: Path = INVENTORY) -> list[str]:
    """Return the sorted, de-duplicated numbered statements in A.0.1.

    A.0.1 has 21 rows but they collapse to a smaller set of distinct
    numbered statements (several rows are claims *of* Theorem 1).  The
    set is what the gate needs: each statement must be anchored somewhere,
    not each row.  Only the *Statement* column is read, so a docstring
    quotation in another column (row 17 quotes "Lemma 1") does not leak a
    gap statement into the set.
    """
    section = read_inventory_section(inventory)
    found: set[str] = set()
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not cells[0].isdigit():
            continue
        found.update(m.group(0) for m in PAPER_STATEMENT_RE.finditer(cells[1]))
    return sorted(found, key=_statement_sort_key)


def _statement_sort_key(name: str) -> tuple[int, int]:
    kind, _, num = name.partition(" ")
    order = {"Theorem": 0, "Lemma": 1, "Corollary": 2, "Proposition": 3, "Remark": 4}
    major, _, minor = num.partition(".")
    return (order.get(kind, 9), int(major) * 1000 + int(minor or 0))


def statement_pattern(statement: str) -> re.Pattern[str]:
    """Compile an exact-match pattern for one statement name."""
    return re.compile(r"\b" + re.escape(statement).replace(r"\ ", r"\s+") + r"\b")


# ---------------------------------------------------------------------------
# Corpus
# ---------------------------------------------------------------------------


def doc_corpus(docs_dir: Path = DOCS_DIR) -> list[Path]:
    """Every ``*.md`` under ``docs/`` except the inventory and the archive.

    The inventory is excluded because it names every statement by
    construction -- counting it would make the gate vacuous.  ``ARCHIVE/``
    is excluded because it is a historical record, not a live anchor.
    """
    return sorted(
        p
        for p in docs_dir.rglob("*.md")
        if p.is_file()
        and p.name != INVENTORY.name
        and "ARCHIVE" not in p.parts
    )


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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_doc_paper_refs.py",
        description=(
            "Machine-checkable E.2 metric: every A.0 paper statement must "
            "be anchored by at least one document."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DOCS_DIR],
        help=(
            "Markdown files or directories for the informational doc-ratio "
            "scan (default: docs/). Directories expand to top-level *.md."
        ),
    )
    parser.add_argument(
        "--target",
        type=float,
        default=E2_TARGET_RATIO,
        help=f"Doc-ratio target for the diagnostic (default: {E2_TARGET_RATIO}).",
    )
    parser.add_argument(
        "--ratio-gate",
        action="store_true",
        help=(
            "Also fail when the informational doc ratio is below --target "
            "(the pre-2026-10-30 behaviour)."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print the verdict lines (no per-file table).",
    )
    parser.add_argument(
        "--no-exit-code",
        action="store_true",
        help="Always exit 0.",
    )
    args = parser.parse_args(argv)

    # --- statement coverage (the gate) -------------------------------------
    try:
        statements = a0_statements()
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if not statements:
        print(
            f"ERROR: no numbered statements found in the A.0 section of "
            f"{INVENTORY.relative_to(REPO_ROOT)}.",
            file=sys.stderr,
        )
        return 2

    corpus = doc_corpus()
    if not corpus:
        print(f"ERROR: no markdown files under {DOCS_DIR}", file=sys.stderr)
        return 2

    bodies = [
        (p, p.read_text(encoding="utf-8", errors="replace")) for p in corpus
    ]
    unanchored: list[str] = []
    if not args.quiet:
        print(f"{'A.0 statement':<18}{'anchors':>8}  {'first doc':<52}")
        print(f"{'':-<18}{'':->8}  {'':-<52}")
    for stmt in statements:
        pat = statement_pattern(stmt)
        hits = [(p, len(pat.findall(t))) for p, t in bodies]
        hits = [(p, n) for p, n in hits if n]
        if not hits:
            unanchored.append(stmt)
        if not args.quiet:
            first = (
                str(hits[0][0].relative_to(REPO_ROOT)) if hits else "(none)"
            )
            total = sum(n for _, n in hits)
            print(f"{stmt:<18}{total:>4} in {len(hits):>3}  {first:<52}")

    n_ok = len(statements) - len(unanchored)
    verdict = "PASS" if not unanchored else "FAIL"
    print(
        f"\n{verdict}  E.2 statement coverage {n_ok} / {len(statements)} "
        f"A.0 statements anchored (universe: {len(corpus)} docs, "
        f"ARCHIVE/ and the inventory excluded)"
    )
    if unanchored:
        print(f"\nUnanchored statements ({len(unanchored)}):")
        for s in unanchored:
            print(f"  - {s}")
        print(
            "\nTo close this, cite the statement where the corresponding "
            "mechanism is described (the A.0 row names the code module and "
            "the reference docstring)."
        )

    # --- doc ratio (informational) -----------------------------------------
    docs = _collect_docs(args.paths)
    if docs:
        n_ref = 0
        non_ref: list[str] = []
        for doc in docs:
            ref, _ = doc_references_paper(doc)
            if ref:
                n_ref += 1
            else:
                non_ref.append(doc.name)
        ratio = n_ref / len(docs)
        ratio_ok = ratio >= args.target
        print(
            f"\n[info] doc ratio {ratio:.3f} ({n_ref} / {len(docs)} top-level "
            f"docs cite any anchor; target {args.target:.2f}, "
            f"{'met' if ratio_ok else 'not met'})"
        )
        if non_ref and not args.quiet:
            print(f"[info] no anchor: {', '.join(non_ref)}")
        if not args.quiet:
            print(
                "[info] This ratio is not the gate.  It measures the transpose "
                "of E.2 and falls whenever docs/ gains a page with no theory "
                "content.  Pass --ratio-gate to make it binding."
            )
    else:
        ratio_ok = True

    if args.no_exit_code:
        return 0
    if unanchored:
        return 1
    if args.ratio_gate and not ratio_ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
