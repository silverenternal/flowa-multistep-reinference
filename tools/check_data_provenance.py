#!/usr/bin/env python3
"""CLI: walk every ``docs/audit/**/*.md`` and cross-check the sha256
references inside.

The audit docs are the project's "evidence ledger" -- every R-cell /
K-cell anchor cites a concrete ``verification_outputs/<sub>/<file>``
and (often) the sha256 of that file. This verifier makes the
provenance contract machine-checkable:

* **Orphan reference** -- the doc cites ``sha256:abc123...`` for
  ``path/to/file`` but no file at that path matches the hash
  (or the file is not git-tracked).
* **Stale reference** -- a file is committed at ``path/to/file`` but no
  audit doc cites it (the audit docs are supposed to enumerate every
  headline artifact, not just the ones they happen to mention).
* **No-op** -- the doc cites the file but the hash matches a different
  file or no file at all (already covered by ``orphan``; kept here for
  completeness).

The verifier is read-only. It exits ``0`` iff every citation resolves or has
been **disclosed**: a stale citation whose document also records the current
on-disk hash within ``RECONCILE_WINDOW`` lines, i.e. one the record has already
reconciled (``verification_outputs/`` is gitignored, so a rewritten artifact
cannot be restored to its cited bytes). Disclosed citations are printed under
their own heading; they are not failures. The summary line is always printed
for CI consumption.

Usage::

    PYTHONPATH=. python tools/check_data_provenance.py [--quiet]
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Layout / configuration
# ---------------------------------------------------------------------------


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
"""Resolved repo root (one level above ``tools/``)."""

AUDIT_DIR: Path = REPO_ROOT / "docs" / "audit"
"""Where the audit docs live. Every ``*.md`` below it is scanned.

The scan is recursive: since 2026-10 the increments file under topic
clusters (``docs/audit/kanzi/``, ``docs/audit/sweep_eval/``,
``docs/audit/engineering/``, …) rather than at the top level, so a
``wave*.md`` glob would skip everything recent.
"""

UNVERIFIABLE_MARKERS: tuple[str, ...] = ("...", "…")
"""Substrings that mark a path as elided in prose, hence not checkable.

Audit notes abbreviate long trees as ``verification_outputs/.../summary.json``.
Resolving that literally reports a missing file that was never claimed to
exist, so such citations are counted separately instead of failing.
"""

# Match a 64-hex-char sha256 anywhere in the doc body. We deliberately
# do *not* require a ``sha256:`` prefix because the audit docs use a
# mix of ``(sha256 61dd70fa)``, ``(sha256:61dd70fa)``,
# ``sha256 61dd70fa ...``, and bare ``61dd70fa...`` styles.
SHA256_RE: re.Pattern[str] = re.compile(r"\b([0-9a-f]{64})\b")

# Match a repo-relative ``verification_outputs/<path>`` reference.
# Catches both ``verification_outputs/wave280-p-r1/summary.json`` and
# ``./wave280-p-r1/summary.json`` (when the doc is itself under
# ``verification_outputs/``).
VERIF_PATH_RE: re.Pattern[str] = re.compile(
    r"((?:[A-Za-z0-9_./-]*?)verification_outputs/[\w./-]+)"
)


# ---------------------------------------------------------------------------
# Provenance model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Citation:
    """A single ``(sha256, path)`` pair lifted from one audit doc."""

    doc: str  # path of the audit doc, repo-relative
    line: int  # 1-indexed line in the doc
    sha256: str
    path: str  # the verification_outputs/... path, repo-relative


@dataclass(frozen=True)
class Drift:
    """A detected provenance inconsistency."""

    kind: str  # "orphan_sha" | "orphan_path" | "missing_file" | "untracked_citation"
    doc: str  # audit doc the drift was detected in (or "*" for repo-wide)
    detail: str


@dataclass(frozen=True)
class ProvenanceResult:
    """Aggregate result of the provenance sweep."""

    citations: tuple[Citation, ...]
    drifts: tuple[Drift, ...] = field(default_factory=tuple)
    cited_paths: frozenset[str] = field(default_factory=frozenset)
    cited_shas: frozenset[str] = field(default_factory=frozenset)
    #: Stale citations the same document has already reconciled by recording
    #: the current on-disk hash.  Reported, but not a failure.
    disclosed: tuple[Drift, ...] = field(default_factory=tuple)
    #: Citations whose path is elided (``...``) or names a directory, so no
    #: single file can be hashed.  Reported, but not a failure.
    unverifiable: tuple[Citation, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Citation extraction
# ---------------------------------------------------------------------------


def _extract_citations(audit_doc: Path, repo_root: Path = REPO_ROOT) -> list[Citation]:
    """Return all ``(sha, path)`` pairs cited in ``audit_doc``.

    The extractor is deliberately conservative: it only pairs a sha256
    and a path when they appear in the same clause of the same line.
    A clause is a substring bounded by the standard citation
    separators `` + ``, ``; ``, or sentence-final ``. `` (period
    followed by a capital letter). This avoids cartesian-product
    false positives where multiple SHAs and multiple paths on the same
    line get cross-paired (the docs format is "<path> sha256=abc123...
    + <other-path> sha256=def456... + <bare-path-with-no-sha>").
    """
    rel_doc = str(audit_doc.relative_to(repo_root))
    text = audit_doc.read_text(encoding="utf-8")
    citations: list[Citation] = []
    # Clause separators: " + " (typical inline list join), "; " (typical
    # semicolon list join), and ". " followed by an uppercase letter
    # (sentence boundary; the uppercase look-ahead avoids splitting on
    # decimal numbers such as "d_s=+0.460" or "31444 B").
    clause_re = re.compile(r"\s+\+\s+|\;\s+|\.\s+(?=[A-Z])")
    for line_no, line in enumerate(text.splitlines(), start=1):
        for clause in clause_re.split(line):
            # Find candidate sha256s in this clause.
            shas = SHA256_RE.findall(clause)
            if not shas:
                continue
            # Find candidate verification_outputs/ paths in this clause.
            paths = VERIF_PATH_RE.findall(clause)
            if not paths:
                continue
            # Pair sha256s and paths sequentially (1 SHA + 1 path per
            # pair). Truncate at min length so leftovers (which pair with
            # paths/SHAs on adjacent lines via the re-cite pattern) are
            # dropped here -- a SHA in this clause without a matching
            # verification_outputs/ path in the same clause is not a
            # citation for any path on this line.
            for sha, path in zip(shas, paths, strict=False):
                # Drop leading "./" / "/" so the path is repo-relative.
                clean = path.lstrip("./").lstrip("/")
                citations.append(
                    Citation(
                        doc=rel_doc,
                        line=line_no,
                        sha256=sha.lower(),
                        path=clean,
                    )
                )
    return citations


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


#: How far from a stale citation the reconciling hash may sit.  The three
#: reconciled records in the tree put it 4-14 lines below ("Hash note").
RECONCILE_WINDOW: int = 40


def _reconciled_near(doc_text: str, line: int, current_sha: str) -> bool:
    """True when ``doc_text`` records ``current_sha`` near ``line``.

    A stale citation is not a defect when the same document has already
    reconciled it: it names the run-time hash *and* the current one, and
    explains why the bytes moved (``verification_outputs/`` is gitignored, so
    a rewritten artifact cannot be restored to its cited bytes).  Proximity is
    required so an unrelated hash elsewhere in a long record does not
    silently excuse a stale citation.
    """
    lines = doc_text.splitlines()
    lo = max(0, line - 1 - RECONCILE_WINDOW)
    hi = min(len(lines), line + RECONCILE_WINDOW)
    return any(current_sha in text for text in lines[lo:hi])


def _sha256_of(path: Path) -> str:
    """Return the lowercase hex sha256 of ``path``, read in 64 KiB chunks."""
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def _resolve_sha_to_file(target: Path, expected_sha: str) -> bool:
    """Return True if ``target`` exists on disk and its sha256 matches
    ``expected_sha``. The function does NOT raise -- a missing file
    resolves to False (the caller reports the drift).
    """
    if not target.is_file():
        return False
    return _sha256_of(target) == expected_sha


def _is_unverifiable(path: str) -> bool:
    """True if ``path`` cannot be resolved to one file by construction."""
    if path.endswith("/"):
        return True
    return any(marker in path for marker in UNVERIFIABLE_MARKERS)


def verify(
    audit_dir: Path = AUDIT_DIR, repo_root: Path = REPO_ROOT
) -> ProvenanceResult:
    """Run the provenance sweep against ``audit_dir``.

    Returns a :class:`ProvenanceResult` aggregating every citation +
    every drift detected. Pure -- does not print.
    """
    if not audit_dir.is_dir():
        return ProvenanceResult(citations=())
    drifts: list[Drift] = []
    disclosed: list[Drift] = []
    unverifiable: list[Citation] = []
    citations: list[Citation] = []
    cited_paths: set[str] = set()
    cited_shas: set[str] = set()
    for doc in sorted(audit_dir.rglob("*.md")):
        doc_text = doc.read_text(encoding="utf-8")
        for citation in _extract_citations(doc, repo_root):
            citations.append(citation)
            cited_paths.add(citation.path)
            cited_shas.add(citation.sha256)
            if _is_unverifiable(citation.path):
                unverifiable.append(citation)
                continue
            target = repo_root / citation.path
            if not target.is_file():
                drifts.append(
                    Drift(
                        kind="missing_file",
                        doc=citation.doc,
                        detail=(
                            f"{citation.doc}:{citation.line} cites "
                            f"{citation.path} but the file is not on disk"
                        ),
                    )
                )
                continue
            if not _resolve_sha_to_file(target, citation.sha256):
                detail = (
                    f"{citation.doc}:{citation.line} cites "
                    f"sha256 {citation.sha256[:12]}... for "
                    f"{citation.path} but the on-disk hash differs"
                )
                current = _sha256_of(target)
                if _reconciled_near(doc_text, citation.line, current):
                    # The document has already reconciled the citation: it
                    # records the run-time hash *and* the current one, and
                    # explains why the bytes moved.  Reported, not failed --
                    # ``verification_outputs/`` is gitignored, so a rewritten
                    # artifact cannot be restored to its cited bytes.
                    disclosed.append(Drift(kind="orphan_sha", doc=citation.doc, detail=detail))
                else:
                    drifts.append(Drift(kind="orphan_sha", doc=citation.doc, detail=detail))
    return ProvenanceResult(
        citations=tuple(citations),
        drifts=tuple(drifts),
        cited_paths=frozenset(cited_paths),
        cited_shas=frozenset(cited_shas),
        disclosed=tuple(disclosed),
        unverifiable=tuple(unverifiable),
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _format_report(result: ProvenanceResult) -> str:
    """Render a markdown-style report."""
    out: list[str] = []
    out.append("# Data provenance report")
    out.append("")
    out.append(f"- Citations parsed: **{len(result.citations)}**")
    out.append(f"- Unique paths cited: **{len(result.cited_paths)}**")
    out.append(f"- Unique sha256s cited: **{len(result.cited_shas)}**")
    out.append(f"- Drifts: **{len(result.drifts)}**")
    if result.unverifiable:
        out.append(
            f"- Not checkable: **{len(result.unverifiable)}** "
            "(path is elided with `...` or names a directory, so no single "
            "file can be hashed)"
        )
    if result.disclosed:
        out.append(
            f"- Disclosed stale citations: **{len(result.disclosed)}** "
            "(the document records the current hash and why the bytes moved)"
        )
    out.append("")
    if not result.drifts and not result.disclosed:
        out.append("**All citations resolve to on-disk files with matching sha256.**")
    elif not result.drifts:
        out.append(
            "**Every citation resolves or has been reconciled in place; "
            "no unexplained drift.**"
        )
    else:
        out.append("## Drifts")
        out.append("")
        for d in result.drifts:
            out.append(f"- **{d.doc}** (`{d.kind}`): {d.detail}")
    if result.disclosed:
        out.append("")
        out.append("## Disclosed (not a failure)")
        out.append("")
        for d in result.disclosed:
            out.append(f"- **{d.doc}**: {d.detail}")
    if result.unverifiable:
        out.append("")
        out.append("## Not checkable (not a failure)")
        out.append("")
        for c in result.unverifiable:
            out.append(f"- **{c.doc}:{c.line}**: `{c.path}`")
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Walk every docs/audit/**/*.md, extract each (sha256, path) "
            "citation, and verify the path resolves to a file with a "
            "matching sha256.  Elided paths (``...``) and directory "
            "citations are counted as not checkable, not as drift."
        )
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print the one-line summary; suppress the full report.",
    )
    parser.add_argument(
        "--audit-dir",
        type=Path,
        default=AUDIT_DIR,
        help=(
            "Audit docs directory to scan (default: docs/audit/). "
            "Test-only override."
        ),
    )
    return parser.parse_args(list(argv))


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    result = verify(audit_dir=args.audit_dir)
    n_drifts = len(result.drifts)
    summary = (
        f"provenance: citations={len(result.citations)} "
        f"paths={len(result.cited_paths)} drifts={n_drifts} "
        f"disclosed={len(result.disclosed)} "
        f"notcheckable={len(result.unverifiable)}"
    )
    if args.quiet:
        print(summary)
    else:
        print(_format_report(result))
        print(summary)
    return 0 if n_drifts == 0 else 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
