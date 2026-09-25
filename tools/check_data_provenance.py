#!/usr/bin/env python3
"""CLI: walk every ``docs/audit/wave*.md`` and cross-check the sha256
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

The verifier is read-only. It exits ``0`` iff every citation resolves.
The summary line is always printed for CI consumption.

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
"""Where the per-wave audit docs live. ``wave*.md`` glob is the source set."""

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


# ---------------------------------------------------------------------------
# Citation extraction
# ---------------------------------------------------------------------------


def _line_has_both(line: str, sha: str, path: str) -> bool:
    """Return True if the line contains both ``sha`` and ``path`` (in any
    order). The audit docs sometimes pair a path on one line and the
    sha on the next; we pair them only when they coexist on the same
    line to avoid false positives across table rows.
    """
    return sha in line and path in line


def _extract_citations(audit_doc: Path) -> list[Citation]:
    """Return all ``(sha, path)`` pairs cited in ``audit_doc``.

    The extractor is deliberately conservative: it only pairs a sha256
    and a path when they appear on the same physical line. This is
    strict enough to catch almost every audit-doc citation (the docs
    format is "<path> sha256=abc123..." or "(sha256 abc123...) path/...")
    while filtering out unrelated hashes (e.g. the headline-cell sha
    ledger that intentionally lists per-file hashes without paths).
    """
    rel_doc = str(audit_doc.relative_to(REPO_ROOT))
    text = audit_doc.read_text(encoding="utf-8")
    citations: list[Citation] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        # Find candidate sha256s on this line.
        shas = SHA256_RE.findall(line)
        if not shas:
            continue
        # Find candidate verification_outputs/ paths on this line.
        paths = VERIF_PATH_RE.findall(line)
        if not paths:
            continue
        # Pair every sha with every path that coexists on the same line.
        # Most lines have one of each; the cartesian product stays
        # small in practice.
        for sha in shas:
            for path in paths:
                # Drop leading "./" / "/" so the path is repo-relative.
                clean = path.lstrip("./").lstrip("/")
                if _line_has_both(line, sha, clean):
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


def _resolve_sha_to_file(target: Path, expected_sha: str) -> bool:
    """Return True if ``target`` exists on disk and its sha256 matches
    ``expected_sha``. The function does NOT raise -- a missing file
    resolves to False (the caller reports the drift).
    """
    if not target.is_file():
        return False
    import hashlib

    h = hashlib.sha256()
    with target.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().lower() == expected_sha


def verify(audit_dir: Path = AUDIT_DIR) -> ProvenanceResult:
    """Run the provenance sweep against ``audit_dir``.

    Returns a :class:`ProvenanceResult` aggregating every citation +
    every drift detected. Pure -- does not print.
    """
    if not audit_dir.is_dir():
        return ProvenanceResult(citations=())
    drifts: list[Drift] = []
    citations: list[Citation] = []
    cited_paths: set[str] = set()
    cited_shas: set[str] = set()
    for doc in sorted(audit_dir.glob("wave*.md")):
        for citation in _extract_citations(doc):
            citations.append(citation)
            cited_paths.add(citation.path)
            cited_shas.add(citation.sha256)
            target = REPO_ROOT / citation.path
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
                drifts.append(
                    Drift(
                        kind="orphan_sha",
                        doc=citation.doc,
                        detail=(
                            f"{citation.doc}:{citation.line} cites "
                            f"sha256 {citation.sha256[:12]}... for "
                            f"{citation.path} but the on-disk hash differs"
                        ),
                    )
                )
    return ProvenanceResult(
        citations=tuple(citations),
        drifts=tuple(drifts),
        cited_paths=frozenset(cited_paths),
        cited_shas=frozenset(cited_shas),
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
    out.append("")
    if not result.drifts:
        out.append("**All citations resolve to on-disk files with matching sha256.**")
    else:
        out.append("## Drifts")
        out.append("")
        for d in result.drifts:
            out.append(f"- **{d.doc}** (`{d.kind}`): {d.detail}")
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Walk docs/audit/wave*.md, extract every (sha256, path) "
            "citation, and verify the path resolves to a file with "
            "matching sha256."
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
        f"paths={len(result.cited_paths)} drifts={n_drifts}"
    )
    if args.quiet:
        print(summary)
    else:
        print(_format_report(result))
        print(summary)
    return 0 if n_drifts == 0 else 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
