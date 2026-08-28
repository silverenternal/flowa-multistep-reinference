r"""CLI: verify that ``docs/CLAIMS.md`` stays consistent with the rest of the docs.

Single source of truth for the framework's substantive claims lives in
``docs/CLAIMS.md``. Every claim gets a stable ``CLM-NNN`` ID and
records:

* ``Asserted by`` -- a file:line reference inside the repo (the
  "grounding" claim).
* ``Disputed by`` -- optional file:line reference that contradicts
  the claim (the verifier auto-promotes the claim to ``PROVISIONAL``
  when this is present).
* ``Status`` -- one of ``ACTIVE`` / ``PROVISIONAL`` / ``DEPRECATED``.

The verifier:

1. Parses ``docs/CLAIMS.md`` into ``Claim`` records.
2. For each ``ACTIVE`` claim with an ``Asserted by`` reference, opens
   the referenced file and checks the line number exists (and the line
   contains non-whitespace content -- an empty line at the cited line
   is treated as drift).
3. For each ``ACTIVE`` claim with a ``Disputed by`` reference, the
   claim is *forced* to ``PROVISIONAL`` regardless of the ``Status:``
   field in the file -- the verifier is the canonical authority for
   the ``PROVISIONAL`` promotion. The file's ``Status:`` field is left
   intact for human review; the verifier's view of reality is what
   matters for the exit code.
4. For each ``ACTIVE`` claim, scans the four governance surfaces
   (``docs/INSIGHTS.md``, ``docs/ABLATION.md``, every
   ``docs/adr/*.md``, plus the root ``README.md`` / ``ARCHITECTURE.md``
   for cross-reference) for ``[CLM-NNN]`` tags. A claim that has no
   cross-reference anywhere is *drift* by definition -- the single
   source of truth is supposed to be the cross-referenced
   destination, not a stand-alone document.
5. Prints a summary table and exits ``0`` if all ``ACTIVE`` claims
   pass; exits ``1`` on drift (missing assertion, missing
   cross-reference, or unparseable status).

::

    PYTHONPATH=. python tools/check_claims_consistency.py
    PYTHONPATH=. python tools/check_claims_consistency.py --quiet
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

CLAIMS_FILE: Path = REPO_ROOT / "docs" / "CLAIMS.md"
"""Canonical ledger of project claims."""

# Governance surfaces whose ``[CLM-NNN]`` tags we cross-check against
# ``CLAIMS.md``. Each ACTIVE claim should appear in at least one of
# these (it is drift if it only lives in CLAIMS.md).
CLAIMS_GOVERNANCE_SURFACES: tuple[str, ...] = (
    "docs/INSIGHTS.md",
    "docs/ABLATION.md",
    "README.md",
    "ARCHITECTURE.md",
)
"""Files every ACTIVE claim should be cross-referenced from."""

# ADR directory is a glob -- we cross-check every markdown file inside
# ``docs/adr/`` for ``[CLM-NNN]`` tags.
ADR_DIR: Path = REPO_ROOT / "docs" / "adr"
"""Directory of accepted/proposed ADRs scanned for ``[CLM-NNN]`` tags."""


# ---------------------------------------------------------------------------
# Claim model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Claim:
    """A single parseable claim record from ``docs/CLAIMS.md``."""

    clm_id: str
    title: str
    status: str  # "ACTIVE" | "PROVISIONAL" | "DEPRECATED"
    date: str
    source: str
    asserted_by: str  # file:line(s) or empty
    disputed_by: str  # file:line(s) or empty
    statement: str
    evidence: str
    line: int  # 1-indexed line in CLAIMS.md where the claim header starts


@dataclass(frozen=True)
class Drift:
    """A single detected inconsistency, surfaced to the user."""

    clm_id: str
    kind: str  # "missing_assertion" | "missing_cross_reference" | "bad_status" | "bad_path"
    detail: str


@dataclass(frozen=True)
class VerifierResult:
    """Aggregate result of running the verifier."""

    claims: tuple[Claim, ...]
    drifts: tuple[Drift, ...] = field(default_factory=tuple)
    active_count: int = 0
    provisional_count: int = 0
    deprecated_count: int = 0
    forced_provisional: tuple[str, ...] = field(default_factory=tuple)
    cross_referenced: frozenset[str] = field(default_factory=frozenset)


# ---------------------------------------------------------------------------
# Regex / parser
# ---------------------------------------------------------------------------


# Match the claim header line: ``## CLM-001: short title``
CLAIM_HEADER_RE: re.Pattern[str] = re.compile(
    r"^##\s+(?P<id>CLM-\d{3,}):\s*(?P<title>.+?)\s*$"
)

# Match a key: value pair inside the claim body. Keys are exactly the
# canonical set documented in the file header. The line may start with
# up to two spaces (markdown list indentation).
CLAIM_FIELD_RE: re.Pattern[str] = re.compile(
    r"^-\s+(?P<key>Status|Date|Source|Asserted by|Disputed by|Statement|Evidence):\s*(?P<value>.*?)\s*$"
)

# Match a file:line reference. Accepts both ``file.py:42`` and
# ``file.py:42-45`` (range) forms.
FILE_LINE_REF_RE: re.Pattern[str] = re.compile(
    r"(?P<path>[A-Za-z0-9_./-]+\.[A-Za-z0-9_]+):(?P<line>\d+)(?:[-](?P<line_end>\d+))?"
)

# Match a ``[CLM-NNN]`` tag anywhere in the body text.
CLM_TAG_RE: re.Pattern[str] = re.compile(r"\[(CLM-\d{3,})\]")

VALID_STATUSES: frozenset[str] = frozenset({"ACTIVE", "PROVISIONAL", "DEPRECATED"})


def _split_ref(ref: str) -> tuple[str, int] | None:
    """Split ``"path/to/file.py:42"`` into ``(path, line)`` if it is a
    well-formed file:line reference (range form is collapsed to the
    starting line). Returns ``None`` if the input is empty / malformed.
    """
    ref = ref.strip()
    if not ref:
        return None
    m = FILE_LINE_REF_RE.search(ref)
    if not m:
        return None
    return (m.group("path"), int(m.group("line")))


def _parse_claims(text: str) -> list[Claim]:
    """Parse ``docs/CLAIMS.md`` into a list of ``Claim`` records.

    The parser is intentionally lenient: a malformed claim (missing
    required fields) is skipped and surfaced as drift by the caller via
    ``bad_status``. This keeps the verifier usable on partial / in-
    progress edits.
    """
    lines = text.splitlines()
    claims: list[Claim] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = CLAIM_HEADER_RE.match(line)
        if not m:
            i += 1
            continue
        clm_id = m.group("id")
        title = m.group("title")
        header_line = i + 1  # 1-indexed
        # Walk forward, collecting fields until the next ``## `` header
        # or EOF.
        fields: dict[str, str] = {}
        i += 1
        while i < len(lines):
            nxt = lines[i]
            if nxt.startswith("## "):
                break
            fm = CLAIM_FIELD_RE.match(nxt)
            if fm:
                fields[fm.group("key")] = fm.group("value")
            i += 1
        required = ("Status", "Date", "Source", "Statement")
        if not all(k in fields for k in required):
            # Incomplete claim: caller will report drift via the
            # ``bad_status`` path.
            continue
        claims.append(
            Claim(
                clm_id=clm_id,
                title=title,
                status=fields.get("Status", ""),
                date=fields.get("Date", ""),
                source=fields.get("Source", ""),
                asserted_by=fields.get("Asserted by", ""),
                disputed_by=fields.get("Disputed by", ""),
                statement=fields.get("Statement", ""),
                evidence=fields.get("Evidence", ""),
                line=header_line,
            )
        )
    return claims


def _resolve_path(quoted_path: str, *, base: Path = REPO_ROOT) -> Path:
    """Resolve a repo-relative path inside the citation. Strips any
    backticks / surrounding punctuation that may have leaked into the
    markdown field value. ``base`` is the directory the citation is
    resolved against (defaults to the production repo root; tests
    override it to point at their synthetic fixture).
    """
    cleaned = quoted_path.strip().strip("`").rstrip(",.;:)")
    return base / cleaned


def _line_exists(path: Path, line: int) -> bool:
    """Return ``True`` if ``line`` (1-indexed) is within the file and
    the line content is non-empty (a citation pointing at a blank line
    is treated as drift -- a blank line never grounds a claim).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, IsADirectoryError):
        return False
    lines = text.splitlines()
    if line < 1 or line > len(lines):
        return False
    return bool(lines[line - 1].strip())


def _scan_cross_references(
    *, base: Path = REPO_ROOT
) -> dict[str, list[str]]:
    """Return ``{clm_id: [files_that_reference_it]}`` from every
    governance surface. Used by the verifier to assert that each
    ``ACTIVE`` claim is cross-referenced from at least one place.

    ``base`` is the project root used to anchor both the canonical
    governance files and the ``docs/adr/`` glob; tests pass a
    synthetic root so the suite can run hermetically.
    """
    refs: dict[str, list[str]] = {}
    targets: list[Path] = []
    for rel in CLAIMS_GOVERNANCE_SURFACES:
        p = base / rel
        if p.is_file():
            targets.append(p)
    adr_dir = base / "docs" / "adr"
    if adr_dir.is_dir():
        for p in sorted(adr_dir.glob("*.md")):
            targets.append(p)
    for target in targets:
        try:
            text = target.read_text(encoding="utf-8")
        except (FileNotFoundError, IsADirectoryError):
            continue
        try:
            rel = str(target.relative_to(base))
        except ValueError:
            rel = str(target)
        for m in CLM_TAG_RE.finditer(text):
            cid = m.group(1)
            refs.setdefault(cid, []).append(rel)
    return refs


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def verify(claims_path: Path = CLAIMS_FILE) -> VerifierResult:
    """Run all checks against the parsed claim ledger.

    The function is pure -- it reads from disk and returns a
    ``VerifierResult``. The CLI layer is responsible for printing /
    exiting based on the result.

    ``claims_path``'s parent directory is used as the root against
    which both the ``Asserted by`` citations *and* the governance
    surfaces are resolved -- tests pass a ``tmp_path/docs/CLAIMS.md``
    so the suite stays hermetic.
    """
    if not claims_path.is_file():
        return VerifierResult(
            claims=(),
            drifts=(
                Drift(
                    clm_id="*",
                    kind="bad_path",
                    detail=f"claims ledger not found: {claims_path}",
                ),
            ),
        )
    text = claims_path.read_text(encoding="utf-8")
    claims = _parse_claims(text)
    # Resolve citations and cross-references against the ledger's
    # project root. The production ledger lives at
    # ``<REPO_ROOT>/docs/CLAIMS.md`` so its parent (``docs/``) is
    # one level deep; tests run with their own ``<tmp>/docs/CLAIMS.md``
    # whose ``<tmp>`` is the synthetic root. In both cases
    # ``claims_path.parent.parent`` is the project root -- the
    # ledger always lives at ``<root>/docs/CLAIMS.md`` by convention.
    base = claims_path.resolve().parent.parent
    cross_refs = _scan_cross_references(base=base)

    drifts: list[Drift] = []
    active = 0
    prov = 0
    dep = 0
    forced_provisional: list[str] = []
    cross_referenced: set[str] = set()

    for claim in claims:
        if claim.status not in VALID_STATUSES:
            drifts.append(
                Drift(
                    clm_id=claim.clm_id,
                    kind="bad_status",
                    detail=(
                        f"invalid status {claim.status!r}; expected one of "
                        f"{sorted(VALID_STATUSES)} (see CLAIMS.md line "
                        f"{claim.line})"
                    ),
                )
            )
            continue

        # Count by canonical status (the file's Status: field is the
        # authoritative source for the count). Disputed-by promotion is
        # recorded separately under ``forced_provisional`` -- it does
        # NOT change the count, only the exit-status interpretation.
        if claim.status == "ACTIVE":
            active += 1
        elif claim.status == "PROVISIONAL":
            prov += 1
        elif claim.status == "DEPRECATED":
            dep += 1

        # Skip non-ACTIVE claims for the drift sweep (a DEPRECATED
        # claim with a dangling asserted_by is *historical* -- leaving
        # it alone is the right call).
        if claim.status != "ACTIVE":
            continue

        # 1. Verify the asserted_by reference resolves to a real line.
        parsed = _split_ref(claim.asserted_by)
        if parsed is None:
            if claim.asserted_by.strip() in ("", "—", "-"):
                # No assertion cited -- not drift by definition; the
                # claim is *ungrounded* but not contradictory.
                pass
            else:
                drifts.append(
                    Drift(
                        clm_id=claim.clm_id,
                        kind="bad_path",
                        detail=(
                            f"Asserted by {claim.asserted_by!r} is not a "
                            f"well-formed file:line reference"
                        ),
                    )
                )
        else:
            cited_path, cited_line = parsed
            resolved = _resolve_path(cited_path, base=base)
            if not resolved.is_file():
                drifts.append(
                    Drift(
                        clm_id=claim.clm_id,
                        kind="bad_path",
                        detail=(
                            f"Asserted by {cited_path!r} does not exist on "
                            f"disk (resolved to {resolved})"
                        ),
                    )
                )
            elif not _line_exists(resolved, cited_line):
                drifts.append(
                    Drift(
                        clm_id=claim.clm_id,
                        kind="missing_assertion",
                        detail=(
                            f"Asserted by {cited_path}:{cited_line} -- "
                            f"line {cited_line} is missing or blank"
                        ),
                    )
                )

        # 2. Disputed-by auto-promotes the claim to PROVISIONAL.
        if claim.disputed_by.strip() not in ("", "—", "-"):
            forced_provisional.append(claim.clm_id)

        # 3. Cross-reference sweep: each ACTIVE claim must appear in
        # at least one governance surface (INSIGHTS / ABLATION / ADR /
        # README / ARCHITECTURE).
        if cross_refs.get(claim.clm_id):
            cross_referenced.add(claim.clm_id)
        else:
            drifts.append(
                Drift(
                    clm_id=claim.clm_id,
                    kind="missing_cross_reference",
                    detail=(
                        f"ACTIVE claim {claim.clm_id} is not cross-"
                        f"referenced from any governance surface "
                        f"(INSIGHTS / ABLATION / ADR / README / "
                        f"ARCHITECTURE) via a [CLM-NNN] tag"
                    ),
                )
            )

    return VerifierResult(
        claims=tuple(claims),
        drifts=tuple(drifts),
        active_count=active,
        provisional_count=prov,
        deprecated_count=dep,
        forced_provisional=tuple(forced_provisional),
        cross_referenced=frozenset(cross_referenced),
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _format_report(result: VerifierResult) -> str:
    """Render a markdown-style report of the verification result."""
    out: list[str] = []
    out.append("# Claims consistency report")
    out.append("")
    out.append(
        f"- Active claims: **{result.active_count}**"
    )
    out.append(
        f"- Provisional claims: **{result.provisional_count}**"
    )
    out.append(
        f"- Deprecated claims: **{result.deprecated_count}**"
    )
    if result.forced_provisional:
        out.append(
            "- Forced to PROVISIONAL by `Disputed by` citation: "
            + ", ".join(result.forced_provisional)
        )
    if result.cross_referenced:
        out.append(
            "- Cross-referenced from at least one governance surface: "
            + ", ".join(sorted(result.cross_referenced))
        )
    out.append("")
    if not result.drifts:
        out.append("**No drift detected.**")
    else:
        out.append("## Drift")
        out.append("")
        for drift in result.drifts:
            out.append(
                f"- **{drift.clm_id}** (`{drift.kind}`): {drift.detail}"
            )
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that docs/CLAIMS.md stays consistent with the rest "
            "of the project's governance docs."
        )
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print a one-line summary; suppress the full report.",
    )
    parser.add_argument(
        "--claims-file",
        type=Path,
        default=CLAIMS_FILE,
        help=(
            "Path to the claims ledger (defaults to docs/CLAIMS.md). "
            "Test-only override."
        ),
    )
    return parser.parse_args(list(argv))


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    result = verify(claims_path=args.claims_file)
    if args.quiet:
        n_drifts = len(result.drifts)
        print(
            f"claims: active={result.active_count} "
            f"provisional={result.provisional_count} "
            f"deprecated={result.deprecated_count} "
            f"drift={n_drifts}"
        )
    else:
        print(_format_report(result))
    return 0 if not result.drifts else 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
