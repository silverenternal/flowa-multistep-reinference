"""Tests for ``tools.check_claims_consistency``.

The verifier is the project's "is my docs ledger still accurate?"
gate: it parses ``docs/CLAIMS.md`` (the single source of truth for
substantive claims), walks every ``Asserted by`` file:line reference,
auto-promotes ``Disputed by`` references to ``PROVISIONAL``, and
checks that each ACTIVE claim is cross-referenced from at least one
governance surface via a ``[CLM-NNN]`` tag.

Tests here cover three contracts:

* the parser correctly extracts every claim and surfaces malformed
  status fields as drift;
* ``verify()`` catches the three drift shapes: a missing
  ``Asserted by`` file:line, a cross-reference drift between
  ``INSIGHTS.md`` and the ledger, and a clean ledger passes;
* the CLI exits ``0`` on clean and ``1`` on drift.

The test suite is stdlib + pytest only -- no parallelising, no
networking, no third-party imports. Tests build their own synthetic
repos (CLAIMS.md + a stub ``adaptive_reflow/`` for the citation
target) so the suite is hermetic and does not depend on the current
state of the production ledger.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools import check_claims_consistency as checker

# ---------------------------------------------------------------------------
# Fixtures: synthetic ledger + governance surfaces
# ---------------------------------------------------------------------------


_CLAIM_TEMPLATE = """\
# Project Claims (test fixture)

{body}
"""

# A canonical ACTIVE claim template; the test rewrites the path /
# line / cross-reference text to drive each scenario.
_CLAIM_BODY = """\
## CLM-001: short title
- Status: ACTIVE
- Date: 2026-08-28
- Source: paper Theorem 1
- Asserted by: {asserted}
- Disputed by: {disputed}
- Statement: a synthetic claim used by the test suite.
- Evidence: synthetic evidence.
"""


def _write_claims(tmp_path: Path, body: str) -> Path:
    """Write a synthetic ``CLAIMS.md`` to ``tmp_path/docs/`` and
    return its path."""
    docs = tmp_path / "docs"
    docs.mkdir(exist_ok=True)
    claims = docs / "CLAIMS.md"
    claims.write_text(_CLAIM_TEMPLATE.format(body=body), encoding="utf-8")
    return claims


def _write_citation_target(tmp_path: Path, name: str, content: str) -> Path:
    """Drop a stub ``adaptive_reflow/<name>.py`` so the ledger's
    ``Asserted by`` reference can resolve to a real file:line."""
    pkg = tmp_path / "adaptive_reflow"
    pkg.mkdir(exist_ok=True)
    target = pkg / name
    target.write_text(content, encoding="utf-8")
    return target


def _write_governance_surface(
    tmp_path: Path, rel_path: str, body: str
) -> Path:
    """Drop a governance doc (``docs/INSIGHTS.md``,
    ``docs/ABLATION.md``, ``docs/adr/0013-foo.md``, etc.) carrying
    ``[CLM-NNN]`` tags so the verifier's cross-reference scan sees
    it.
    """
    path = tmp_path / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


@pytest.fixture()
def ledger_path(tmp_path: Path) -> Path:
    """Write a single-claim ledger whose citation target and cross-
    reference surface both resolve cleanly. Used by
    ``test_passes_on_clean_state``.
    """
    _write_citation_target(
        tmp_path, "evidence.py", "# header line\n# cited line\n"
    )
    body = _CLAIM_BODY.format(
        asserted="adaptive_reflow/evidence.py:2", disputed="—"
    )
    claims = _write_claims(tmp_path, body)
    _write_governance_surface(
        tmp_path,
        "docs/INSIGHTS.md",
        "A claim is recorded here [CLM-001] for the test suite.\n",
    )
    return claims


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def test_parse_claims_extracts_status_date_source_statement() -> None:
    """The parser pulls ``Status``, ``Date``, ``Source``,
    ``Asserted by``, ``Disputed by``, ``Statement``, and ``Evidence``
    fields out of a canonical claim body.
    """
    text = (
        "## CLM-042: parser smoke test\n"
        "- Status: ACTIVE\n"
        "- Date: 2026-08-28\n"
        "- Source: synthetic source\n"
        "- Asserted by: synthetic/path.py:10\n"
        "- Disputed by: —\n"
        "- Statement: a single sentence.\n"
        "- Evidence: synthetic evidence.\n"
    )
    claims = checker._parse_claims(text)
    assert len(claims) == 1
    claim = claims[0]
    assert claim.clm_id == "CLM-042"
    assert claim.title == "parser smoke test"
    assert claim.status == "ACTIVE"
    assert claim.date == "2026-08-28"
    assert claim.source == "synthetic source"
    assert claim.asserted_by == "synthetic/path.py:10"
    assert claim.disputed_by == "—"
    assert claim.statement == "a single sentence."
    assert claim.evidence == "synthetic evidence."
    assert claim.line == 1


def test_parse_claims_handles_multiple_claims_in_order() -> None:
    """A ledger with two claim blocks parses them in source order and
    records each claim's 1-indexed header line.
    """
    text = (
        "## CLM-001: first\n"
        "- Status: ACTIVE\n"
        "- Date: 2026-08-28\n"
        "- Source: src\n"
        "- Statement: one.\n"
        "\n"
        "## CLM-002: second\n"
        "- Status: DEPRECATED\n"
        "- Date: 2026-08-28\n"
        "- Source: src\n"
        "- Statement: two.\n"
    )
    claims = checker._parse_claims(text)
    assert [c.clm_id for c in claims] == ["CLM-001", "CLM-002"]
    assert [c.line for c in claims] == [1, 7]


# ---------------------------------------------------------------------------
# Drift detection
# ---------------------------------------------------------------------------


def test_detects_missing_asserted_by_reference(tmp_path: Path) -> None:
    """When ``Asserted by`` points at a line that does not exist on
    disk (or is blank), ``verify()`` reports a
    ``missing_assertion`` drift for that claim.
    """
    # Citation target exists but has only one line; the claim
    # references line 99 -- the verifier must flag it as drift.
    _write_citation_target(tmp_path, "stub.py", "only one line\n")
    body = _CLAIM_BODY.format(
        asserted="adaptive_reflow/stub.py:99", disputed="—"
    )
    claims = _write_claims(tmp_path, body)
    _write_governance_surface(
        tmp_path,
        "docs/INSIGHTS.md",
        "A claim is recorded here [CLM-001] for the test suite.\n",
    )

    result = checker.verify(claims_path=claims)
    kinds = [d.kind for d in result.drifts]
    assert "missing_assertion" in kinds
    drift = next(d for d in result.drifts if d.kind == "missing_assertion")
    assert drift.clm_id == "CLM-001"
    assert "stub.py:99" in drift.detail


def test_detects_drift_between_insights_and_claims(tmp_path: Path) -> None:
    """An ACTIVE claim that is NOT cross-referenced from any
    governance surface (``INSIGHTS.md``, ``ABLATION.md``,
    ``docs/adr/*.md``, ``README.md``, ``ARCHITECTURE.md``) is drift
    by definition -- the ledger is supposed to be the cross-
    referenced destination, not a stand-alone document.
    """
    _write_citation_target(
        tmp_path, "ok.py", "# header line\n# cited line\n"
    )
    body = _CLAIM_BODY.format(
        asserted="adaptive_reflow/ok.py:2", disputed="—"
    )
    claims = _write_claims(tmp_path, body)
    # Note: NO governance surface references [CLM-001].
    _write_governance_surface(
        tmp_path,
        "docs/INSIGHTS.md",
        "INSIGHTS exists but does not reference CLM-001.\n",
    )

    result = checker.verify(claims_path=claims)
    kinds = [d.kind for d in result.drifts]
    assert "missing_cross_reference" in kinds
    drift = next(
        d for d in result.drifts if d.kind == "missing_cross_reference"
    )
    assert drift.clm_id == "CLM-001"


def test_detects_bad_status_field(tmp_path: Path) -> None:
    """An unknown ``Status`` value surfaces as a ``bad_status`` drift
    so a typo (``ACTIV`` instead of ``ACTIVE``) is caught at verify
    time rather than silently slipping through.
    """
    _write_citation_target(
        tmp_path, "ok.py", "# header line\n# cited line\n"
    )
    body = (
        "## CLM-001: short title\n"
        "- Status: ACTIV\n"
        "- Date: 2026-08-28\n"
        "- Source: synthetic\n"
        "- Asserted by: adaptive_reflow/ok.py:2\n"
        "- Disputed by: —\n"
        "- Statement: synthetic.\n"
        "- Evidence: synthetic.\n"
    )
    claims = _write_claims(tmp_path, body)
    _write_governance_surface(
        tmp_path,
        "docs/INSIGHTS.md",
        "A claim is recorded here [CLM-001] for the test suite.\n",
    )

    result = checker.verify(claims_path=claims)
    kinds = [d.kind for d in result.drifts]
    assert "bad_status" in kinds


def test_disputed_by_forces_provisional(tmp_path: Path) -> None:
    """An ACTIVE claim with a non-empty ``Disputed by`` reference is
    reported under ``forced_provisional`` even when the rest of the
    ledger is clean -- the verifier is the canonical authority for
    the ``PROVISIONAL`` promotion.
    """
    _write_citation_target(
        tmp_path, "ok.py", "# header line\n# cited line\n"
    )
    _write_citation_target(
        tmp_path, "dispute.py", "# disputed line\n"
    )
    body = _CLAIM_BODY.format(
        asserted="adaptive_reflow/ok.py:2",
        disputed="adaptive_reflow/dispute.py:1",
    )
    claims = _write_claims(tmp_path, body)
    _write_governance_surface(
        tmp_path,
        "docs/INSIGHTS.md",
        "A claim is recorded here [CLM-001] for the test suite.\n",
    )

    result = checker.verify(claims_path=claims)
    # The claim is still counted as ACTIVE (the file's Status: field
    # is authoritative for the count) but the verifier flags it as
    # forced-to-PROVISIONAL.
    assert "CLM-001" in result.forced_provisional
    assert result.active_count == 1
    assert result.provisional_count == 0


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_passes_on_clean_state(ledger_path: Path) -> None:
    """A fixture ledger with a real ``Asserted by`` citation and a
    real ``[CLM-001]`` cross-reference in ``docs/INSIGHTS.md`` passes
    with zero drift.
    """
    result = checker.verify(claims_path=ledger_path)
    assert result.drifts == ()
    assert result.active_count == 1
    assert result.provisional_count == 0
    assert result.deprecated_count == 0
    assert "CLM-001" in result.cross_referenced


# ---------------------------------------------------------------------------
# CLI exit code
# ---------------------------------------------------------------------------


def test_cli_exits_zero_on_clean(
    ledger_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``main()`` returns ``0`` when the ledger is clean."""
    monkeypatch.setattr(
        "sys.argv", ["check_claims_consistency.py", "--quiet"]
    )
    rc = checker.main(["--quiet"])
    # Re-run with the synthetic ledger path so the CLI sees it
    # directly; the default REPO_ROOT-based path resolves to the
    # production ledger which may or may not be clean.
    rc = checker.main(["--quiet", "--claims-file", str(ledger_path)])
    assert rc == 0


def test_cli_exits_one_on_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``main()`` returns ``1`` when drift is detected."""
    _write_citation_target(tmp_path, "stub.py", "only one line\n")
    body = _CLAIM_BODY.format(
        asserted="adaptive_reflow/stub.py:99", disputed="—"
    )
    claims = _write_claims(tmp_path, body)
    _write_governance_surface(
        tmp_path,
        "docs/INSIGHTS.md",
        "A claim is recorded here [CLM-001] for the test suite.\n",
    )
    rc = checker.main(["--quiet", "--claims-file", str(claims)])
    assert rc == 1
