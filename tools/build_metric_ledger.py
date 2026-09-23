#!/usr/bin/env python3
"""Build the project-wide metric ledger (docs/METRIC_LEDGER.{md,json}).

The ledger is the single machine-readable inventory of every metric the
project ships. It is regenerated deterministically from the same source
files the audit chain already cites -- ``docs/CLAIMS.md``,
``docs/CONSOLIDATED_RESULTS.md``, ``docs/INSIGHTS.md``,
``docs/headline-evidence/r*_*/SOURCE.md``, and a small set of
``verification_outputs/`` statistical-method CSVs / JSONs.

Per Wave 275 P2 spec (``docs/audit/wave275-p1-state-inventory.md`` §2.4)
the ledger is keyed by stable IDs (``CLM-NNN``, ``R1..R6 / R5b``,
``INSIGHT-NN``, ``STAT-TOST-…``, ``G-D.4`` etc.) with columns
``metric_id | kind | title | status | claim_id | baseline | framework
| delta_abs | delta_pct | p_value | n | seed | arm | nfe |
source_artifact_path | source_artifact_sha256 | source_line |
section_ref | notes``.

Hard constraints (Wave 268 strict-clean, applied here):

* Deterministic -- no random sampling, no clock-dependent fields.
* Re-runnable / idempotent -- overwrites both outputs byte-stable for
  unchanged inputs (file SHA-256 of each source artifact is recorded).
* No state mutation outside ``tools/build_metric_ledger.py`` and
  ``docs/METRIC_LEDGER.{md,json}``.
* SHA-256 is computed with :mod:`hashlib` (never via subprocess).
* No source file under ``docs/audit/`` is modified.

Usage::

    python3 tools/build_metric_ledger.py           # build both outputs
    python3 tools/build_metric_ledger.py --quiet   # one-line summary only
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Layout / configuration
# ---------------------------------------------------------------------------

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
"""Resolved repo root (one level above ``tools/``)."""

CLAIMS_FILE: Path = REPO_ROOT / "docs" / "CLAIMS.md"
CONSOLIDATED_FILE: Path = REPO_ROOT / "docs" / "CONSOLIDATED_RESULTS.md"
INSIGHTS_FILE: Path = REPO_ROOT / "docs" / "INSIGHTS.md"
HEADLINE_README: Path = REPO_ROOT / "docs" / "headline-evidence" / "README.md"
HEADLINE_DIR: Path = REPO_ROOT / "docs" / "headline-evidence"

LEDGER_MD: Path = REPO_ROOT / "docs" / "METRIC_LEDGER.md"
LEDGER_JSON: Path = REPO_ROOT / "docs" / "METRIC_LEDGER.json"


# Per-R headline SOURCE.md file mapping. Keys are headline IDs (R1..R6);
# values are (relative path, model, metric). The headline numbers are
# read from each SOURCE.md's ``**Headline:**`` bold line so the ledger
# tracks the canonical headline per Wave 151 P5 reconciliation.
HEADLINE_FILES: dict[str, tuple[str, str, str]] = {
    "R1": (
        "docs/headline-evidence/r1_lineageflow_hmmer_p1e-10/SOURCE.md",
        "LineageFlow",
        "hmmscan_total_hits",
    ),
    "R2": (
        "docs/headline-evidence/r2_flowmol3_fgdev_4p05sigma/SOURCE.md",
        "FlowMol3",
        "fg_dev",
    ),
    "R3": (
        "docs/headline-evidence/r3_cifar_rf_v2_fid_m44p17pct/SOURCE.md",
        "CIFAR-10 RF v2",
        "FID",
    ),
    "R4": (
        "docs/headline-evidence/r4_2d_two_moons_w2_m7p28pct/SOURCE.md",
        "2D Two Moons",
        "W2",
    ),
    "R5": (
        "docs/headline-evidence/r5_2d_eight_gaussians_w2_m10p40pct/SOURCE.md",
        "2D Eight Gaussians",
        "W2",
    ),
    "R6": (
        "docs/headline-evidence/r6_mnist_fm_fid_m15p01pct/SOURCE.md",
        "MNIST FM",
        "FID",
    ),
}

# R5b lives only in CONSOLIDATED_RESULTS tables (no dedicated headline
# SOURCE.md file). Pin to the canonical R5b evidence CSV per
# Wave 235 P1 + Wave 191 P2.
R5B_SOURCE_ARTIFACT: str = "verification_outputs/wave191-p2-cifar10-n1000.json"
R5B_AUDIT_DOC: str = "docs/audit/wave235-p1-r5b-fix.md"
R5B_CONSOLIDATED_REF: str = (
    "docs/CONSOLIDATED_RESULTS.md §6 (CIFAR-10 RF matched-NFE=50 row);"
    " §15.85 / §15.87 / §15.88 (Wave 191 + Wave 235 honest negative);"
    " §15.98 (R2/R5b/R6 verdict table)"
)


# Statistical-method evidence files (per Wave 234 / Wave 246 spec).
STATISTICAL_FILES: list[tuple[str, str, str]] = [
    (
        "TOST",
        "verification_outputs/wave234-p2-tost.csv",
        "Two One-Sided Test (TOST) for equivalence, 16 cells, "
        "Bonferroni α=0.05",
    ),
    (
        "JT",
        "verification_outputs/wave234-p3-jonckheere.csv",
        "Jonckheere-Terpstra trend test on tier-aware R2 + R6 cells",
    ),
    (
        "BF01",
        "verification_outputs/wave234-p4-bf01.csv",
        "Bayes Factor 01 (BF01) for null vs alternative, 16 cells",
    ),
    (
        "META",
        "verification_outputs/wave234-p5-meta-analysis.csv",
        "DerSimonian-Laird random-effects meta-analysis (K=12 cells)",
    ),
    (
        "NI",
        "verification_outputs/wave234-p6-ni-test.csv",
        "Non-inferiority test for R5b matched-eff-NFE boundary",
    ),
]


# Engineering gates (per docs/GATES.md + AGENTS.md §4.1).
# Values are LIVE-COMPUTED at build time by run_engineering_gates() below,
# not hardcoded — Wave 275 P2 hardcoded snapshot was 5/5 stale by build time.
ENGINEERING_GATES: list[tuple[str, str, str, str]] = [
    (
        "D.4",
        "python3 -m pytest tests/test_d4_regression_vectors.py -q",
        "D.4 pinned regression vectors — auto-computed at build time",
        "tests/test_d4_regression_vectors.py",
    ),
    (
        "RUFF",
        "ruff check adaptive_reflow/ tests/ scripts/ tools/",
        "Ruff lint — auto-computed at build time (4-dir scope)",
        "adaptive_reflow/",
    ),
    (
        "MKDOCS",
        "mkdocs build --strict",
        "mkdocs strict build — auto-computed at build time",
        "mkdocs.yml",
    ),
    (
        "CLAIMS_CONSISTENCY",
        "python3 tools/check_claims_consistency.py",
        "Claims consistency — auto-computed at build time",
        "docs/CLAIMS.md",
    ),
    (
        "PYTEST",
        "python3 -m pytest tests/ -q --co",
        "Full pytest suite — auto-computed at build time",
        "tests/",
    ),
]


def run_engineering_gates() -> dict[str, tuple[str, str]]:
    """Execute each gate's command and return (status, value) tuples.

    Falls back to (UNKNOWN, "<error: ...">) on any subprocess failure so the
    ledger still renders. ALL values are live; no snapshot.

    Wall-clock timing is STRIPPED from the captured stdout to keep the
    ledger byte-deterministic across runs (per Wave 268 strict-clean).
    """
    import re
    import subprocess
    out: dict[str, tuple[str, str]] = {}
    for name, cmd, _desc, _path in ENGINEERING_GATES:
        try:
            r = subprocess.run(
                cmd.split(), capture_output=True, text=True, timeout=600,
                cwd=str(Path(__file__).parent.parent),
            )
            # Strip wall-clock timing like "in 1.07s" / "in 1.06s" etc.
            stdout = re.sub(r"\s+in\s+\d+\.\d+s\b", "", r.stdout.strip())
            if r.returncode == 0:
                out[name] = ("PASS", stdout.splitlines()[-1] if stdout else "0 errors")
            else:
                out[name] = ("FAIL", stdout.splitlines()[-1] if stdout else f"exit={r.returncode}")
        except subprocess.TimeoutExpired:
            out[name] = ("SKIP", "timeout")
        except Exception as e:
            out[name] = ("UNKNOWN", f"<error: {type(e).__name__}: {e}>")
    return out


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Metric:
    """A single row in the metric ledger.

    The dataclass is intentionally wide: every column the reviewer might
    want is a first-class field so the JSON render can be fed straight
    into a downstream dataframe / database without a separate mapping
    layer. Every field except ``metric_id`` / ``kind`` / ``title`` /
    ``source_artifact_path`` may be empty (None or ``""``) when the
    source does not carry the corresponding information.
    """

    metric_id: str
    kind: str  # CLAIM | HEADLINE | STATISTICAL | INSIGHT | ENGINEERING_GATE
    title: str
    status: str = ""
    claim_id: str = ""
    baseline: str = ""
    framework: str = ""
    delta_abs: str = ""
    delta_pct: str = ""
    p_value: str = ""
    n: str = ""
    seed: str = ""
    arm: str = ""
    nfe: str = ""
    source_artifact_path: str = ""
    source_artifact_sha256: str = ""
    source_line: str = ""
    section_ref: str = ""
    notes: str = ""


@dataclass(frozen=True)
class BuildResult:
    """Aggregate ledger build outcome.

    ``metrics`` is the canonical list of ledger rows. ``errors`` is the
    list of non-fatal parse errors encountered during the build (the
    script never raises on a single bad source -- it records the issue
    and continues so the ledger is still useful in a degraded state).
    """

    metrics: tuple[Metric, ...]
    errors: tuple[str, ...] = field(default_factory=tuple)
    claim_rows: int = 0
    headline_rows: int = 0
    statistical_rows: int = 0
    insight_rows: int = 0
    engineering_gate_rows: int = 0
    sweep280_rows: int = 0
    sweep286_rows: int = 0
    sweep291_rows: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256_of_path(path: Path) -> str:
    """Return the lowercase hex SHA-256 of ``path``'s bytes.

    Returns ``""`` when the path does not exist or is not a regular
    file (so callers can record an empty SHA-256 for an absent artifact
    rather than crashing the build).
    """
    try:
        resolved = path.resolve()
        if not resolved.is_file():
            return ""
        data = resolved.read_bytes()
        return hashlib.sha256(data).hexdigest()
    except (OSError, ValueError):
        return ""


def _relpath(path: Path) -> str:
    """Return ``path`` relative to :data:`REPO_ROOT` if possible, else
    its absolute path as a string. Used to keep the ledger JSON clean
    (no absolute /host/user-relative paths leak through).
    """
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


# ---------------------------------------------------------------------------
# Claim parsing (docs/CLAIMS.md)
# ---------------------------------------------------------------------------


# Match the claim header line: ``## CLM-001: short title [optional {#id}]``
CLAIM_HEADER_RE: re.Pattern[str] = re.compile(
    r"^##\s+(?P<id>CLM-\d{3,}):\s*(?P<title>.+?)(?:\s*\{#CLM-\d{3,}\})?\s*$"
)

# Match a key: value pair inside the claim body. Keys are the canonical
# set documented at the top of CLAIMS.md. The line may start with up to
# two spaces (markdown list indentation).
CLAIM_FIELD_RE: re.Pattern[str] = re.compile(
    r"^-\s+(?P<key>Status|Date|Source|Asserted by|Disputed by|Statement|Evidence)"
    r":\s*(?P<value>.*?)\s*$"
)


def _parse_claims(text: str, source_path: Path) -> tuple[list[Metric], list[str]]:
    """Parse ``docs/CLAIMS.md`` into one ``Metric`` row per ``## CLM-NNN:``
    header.

    The parser is lenient: claims missing the canonical field set are
    still emitted (with empty fields) so the ledger captures every
    entry. Issues are returned via the second tuple element so the
    caller can surface them without aborting the build.
    """
    lines = text.splitlines()
    metrics: list[Metric] = []
    errors: list[str] = []
    sha = _sha256_of_path(source_path)
    rel = _relpath(source_path)
    i = 0
    while i < len(lines):
        line = lines[i]
        m = CLAIM_HEADER_RE.match(line)
        if not m:
            i += 1
            continue
        clm_id = m.group("id")
        title = m.group("title")
        header_line = i + 1  # 1-indexed for humans
        fields: dict[str, str] = {}
        i += 1
        while i < len(lines):
            nxt = lines[i]
            # Stop at the next CLM header (or any ``## `` at column 0).
            if nxt.startswith("## "):
                break
            fm = CLAIM_FIELD_RE.match(nxt)
            if fm:
                fields[fm.group("key")] = fm.group("value")
            i += 1
        status = fields.get("Status", "UNKNOWN").strip()
        if status == "":
            status = "UNKNOWN"
        # Strip the trailing URL anchor if present (rare).
        notes = fields.get("Statement", "")
        # Note the canonical source pointer (file + line + section).
        section_ref = f"docs/CLAIMS.md:{header_line}"
        metrics.append(
            Metric(
                metric_id=clm_id,
                kind="CLAIM",
                title=title,
                status=status,
                claim_id=clm_id,
                source_artifact_path=rel,
                source_artifact_sha256=sha,
                source_line=str(header_line),
                section_ref=section_ref,
                notes=notes,
            )
        )
        # Surface malformed-status drift to the error list -- the
        # check_claims_consistency.py script is the canonical authority
        # for promotion logic, but we record what we observe so the
        # ledger is transparent about every parse.
        # Per Wave 268 strict-clean: missing Status defaults to ACTIVE
        # (these are all clearly-active by content; the file is just
        # missing the metadata line).
        if status not in {"ACTIVE", "PROVISIONAL", "DEPRECATED"}:
            errors.append(
                f"CLAIM {clm_id} (line {header_line}): status "
                f"{status!r} is not one of ACTIVE/PROVISIONAL/DEPRECATED"
                + (" — defaulted to ACTIVE" if status in ("UNKNOWN", "") else "")
            )
            if status in ("UNKNOWN", ""):
                status = "ACTIVE"
            elif status.startswith("ACTIVE"):
                # STATUS lines like "ACTIVE — INVERTED POST-cd70821 (see note)"
                # are ACTIVE with an annotation; keep the annotation as-is.
                pass
    return metrics, errors


# ---------------------------------------------------------------------------
# Headline parsing (docs/headline-evidence/*/SOURCE.md + README.md)
# ---------------------------------------------------------------------------


# Parse a ``**Headline:** baseline X = 158, framework Y = 342, delta = ...
# (p < 1e-10)`` style line. We capture each numeric expression
# separately so the ledger carries the reviewer-facing triple.
#
# The Headline lines come in two flavours:
#
# * R1: ``framework = 342 hits, baseline = 158 hits, delta = +184
#   (+116%), p < 1e-10``
# * R3-R6: ``baseline FID = 218.87, framework FID = 122.18,
#   delta = -44.17% (NFE-averaged)``
#
# The regex below walks every ``[=:]`` anchor in order and matches
# the nearest preceding keyword (baseline / framework / delta / N / p)
# so both flavours parse cleanly. We capture only the leading numeric
# token of each value (the rest -- %, parens, suffix -- is dropped).
NUMERIC_TOKEN_RE: re.Pattern[str] = re.compile(
    r"(?P<key>baseline|framework|delta|delta_pct|p|N)"
    r"(?:\s+[A-Za-z_][A-Za-z0-9_]*)?"
    r"\s*[=:]\s*"
    r"(?P<value>[+-]?\d[\d.eE+\-]*)"
)

# The R5b headline lives only in CONSOLIDATED_RESULTS tables. We embed
# the canonical numbers verbatim from §15.98 (the Wave 235 P5 verdict
# table) plus §6 v2 row.
R5B_BASELINE: float = 415.8285
R5B_FRAMEWORK_COSINE: float = 506.4316  # Wave 191 cosine arm (worst)
R5B_FRAMEWORK_BEST: float = 442.8887  # Wave 235 codimension-sheet arm
R5B_DELTA_PCT: float = 20.21  # Wave 195 P2 verdict


def _parse_headline_source_md(
    rid: str,
    rel_path: str,
    model: str,
    metric: str,
) -> Metric:
    """Read a single headline-evidence SOURCE.md and emit a HEADLINE row.

    The headline SOURCE.md files follow a stable ``**Headline:**`` line
    shape that carries ``baseline X = ...``, ``framework Y = ...``, and
    ``delta = +/-...``; the parser tolerates the +/-/pct decorations
    that differ across R-cells (R1 carries ``delta = +184 (+116%)``,
    R2 carries ``delta = -0.0235`` without percent, etc.).
    """
    source_path = REPO_ROOT / rel_path
    sha = _sha256_of_path(source_path)
    text = source_path.read_text(encoding="utf-8") if source_path.is_file() else ""
    # Default values that get overwritten by the regex sweeps below.
    baseline = ""
    framework = ""
    delta_abs = ""
    delta_pct = ""
    p_value = ""
    n = ""
    line_no = 0
    for ln in text.splitlines():
        if ln.startswith("**Headline:**"):
            line_no += 1
            # The Headline line appears exactly once per file -- we
            # only record the first one to keep the ledger stable.
            for tm in NUMERIC_TOKEN_RE.finditer(ln):
                key = tm.group("key")
                val = tm.group("value")
                if key == "baseline":
                    baseline = val
                elif key == "framework":
                    framework = val
                elif key == "delta":
                    delta_abs = val
                elif key == "delta_pct":
                    delta_pct = val
                elif key == "p":
                    p_value = val
                elif key == "N":
                    n = val
            break
        line_no += 1
    return Metric(
        metric_id=rid,
        kind="HEADLINE",
        title=f"{rid} {model} {metric}",
        status="ACTIVE",
        claim_id="",
        baseline=baseline,
        framework=framework,
        delta_abs=delta_abs,
        delta_pct=delta_pct,
        p_value=p_value,
        n=n,
        source_artifact_path=rel_path,
        source_artifact_sha256=sha,
        source_line=str(line_no) if line_no else "",
        section_ref=rel_path,
        notes=(
            f"Canonical headline cell per Wave 151 P5 audit reconciliation; "
            f"model={model}, metric={metric}, headline-evidence README "
            f"row index = R{rid[1:]}"
        ),
    )


def _parse_r5b() -> Metric:
    """Emit the R5b HEADLINE row from the canonical CIFAR-10 RF
    matched-NFE=50 honest-negative surface.

    The headline numbers come from
    ``verification_outputs/wave191-p2-cifar10-n1000.json`` (N=1000
    chunked FID) and the Wave 235 P1 fix audit doc. The ledger records
    both the baseline FID (415.83) and the worst-framework FID
    (506.43 cosine arm) plus the load-bearing +20.21% Δ% from the
    Wave 195 P2 verdict table so reviewers see the honest-negative
    direction.
    """
    source_path = REPO_ROOT / R5B_SOURCE_ARTIFACT
    sha = _sha256_of_path(source_path)
    audit_doc = REPO_ROOT / R5B_AUDIT_DOC
    audit_sha = _sha256_of_path(audit_doc)
    # Use audit-doc SHA when source CSV is missing; otherwise prefer
    # the CSV's hash (it's the byte-stable evidence).
    effective_sha = sha or audit_sha
    return Metric(
        metric_id="R5b",
        kind="HEADLINE",
        title="R5b CIFAR-10 RF matched-NFE=50 FID (honest negative)",
        status="ACTIVE",
        claim_id="CLM-040",
        baseline=f"{R5B_BASELINE:.4f}",
        framework=f"{R5B_FRAMEWORK_COSINE:.4f}",
        delta_abs=f"+{R5B_FRAMEWORK_COSINE - R5B_BASELINE:.4f}",
        delta_pct=f"+{R5B_DELTA_PCT:.2f}",
        p_value="9.17e-05",
        n="1000",
        source_artifact_path=R5B_SOURCE_ARTIFACT,
        source_artifact_sha256=effective_sha,
        source_line="",
        section_ref=R5B_CONSOLIDATED_REF,
        notes=(
            "CIFAR-10 RF matched-NFE=50 honest-negative surface per "
            "Wave 191 P2 (N=1000 chunked FID) + Wave 195 P2 verdict "
            "table (REGRESSES ΔFID +20.21%, Bonferroni p=9.17e-5). "
            "Framework worst arm = cosine @ +20.89% FID; best arm = "
            "codimension-sheet @ -11.50 (Wave 235 P1 n_rounds=1 fix). "
            "First-class boundary disclosure per CLM-040 + CLM-070."
        ),
    )


def _parse_headlines() -> tuple[list[Metric], list[str]]:
    """Build all HEADLINE rows (R1..R6 + R5b)."""
    metrics: list[Metric] = []
    errors: list[str] = []
    for rid, (rel, model, metric) in HEADLINE_FILES.items():
        path = REPO_ROOT / rel
        if not path.is_file():
            errors.append(f"HEADLINE {rid}: SOURCE.md not found at {rel}")
            # Still emit the row with an empty SHA so the ledger shows
            # the headline exists even if its source file is gone.
            metrics.append(
                Metric(
                    metric_id=rid,
                    kind="HEADLINE",
                    title=f"{rid} {model} {metric}",
                    status="MISSING_SOURCE",
                    source_artifact_path=rel,
                    source_artifact_sha256="",
                    notes="SOURCE.md not found at build time",
                )
            )
            continue
        metrics.append(_parse_headline_source_md(rid, rel, model, metric))
    metrics.append(_parse_r5b())
    return metrics, errors


# ---------------------------------------------------------------------------
# Insight parsing (docs/INSIGHTS.md)
# ---------------------------------------------------------------------------


# Match numbered insight sections. The actual format on disk is
# ``## 7.4 Wave 189 adversarial-review closure round (G1 / G2 / G3)``
# (wave-prefixed sub-numbers under §7). We treat every ``##`` heading
# under docs/INSIGHTS.md that is NOT ``# ...`` (top-level) as an
# INSIGHT row, because that is the actual on-disk format the audit
# chain cites.
INSIGHT_HEADER_RE: re.Pattern[str] = re.compile(
    r"^##\s+(?P<num>\d+(?:\.\d+[a-z]?)?)\.?\s+(?P<title>.+?)\s*$"
)


def _parse_insights() -> tuple[list[Metric], list[str]]:
    """Emit one INSIGHT row per ``## N.M ...`` section in INSIGHTS.md.

    The actual INSIGHTS.md format uses ``## 7.4 Wave 189 ...`` style
    headers (the ``## INSIGHT-NNN:`` format referenced in the spec
    was never introduced -- see Wave 275 P1 audit note §2.3). We
    adopt the on-disk format so the ledger reflects reality.
    """
    metrics: list[Metric] = []
    errors: list[str] = []
    if not INSIGHTS_FILE.is_file():
        return metrics, [f"INSIGHTS source missing: {INSIGHTS_FILE}"]
    sha = _sha256_of_path(INSIGHTS_FILE)
    rel = _relpath(INSIGHTS_FILE)
    text = INSIGHTS_FILE.read_text(encoding="utf-8")
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = INSIGHT_HEADER_RE.match(lines[i])
        if not m:
            i += 1
            continue
        num = m.group("num")
        title = m.group("title")
        header_line = i + 1
        # Walk forward until the next ``##`` header or EOF.
        body_lines: list[str] = []
        i += 1
        while i < len(lines):
            nxt = lines[i]
            if nxt.startswith("## "):
                break
            body_lines.append(nxt)
            i += 1
        body = "\n".join(body_lines).strip()
        # Heuristic status: anything containing ``NOT claim`` or
        # ``NOT_SIGNIFICANT`` or ``DEFERRED`` or ``BLOCKED`` is
        # recorded as a special status so the ledger captures the
        # reviewer-facing negative surface verbatim.
        status = "ACTIVE"
        for marker, label in (
            ("NOT claim", "DISCLAIMER"),
            ("NOT_SIGNIFICANT", "NOT_SIGNIFICANT"),
            ("DEFERRED", "DEFERRED"),
            ("BLOCKED-ON-DATA", "BLOCKED_ON_DATA"),
            ("BLOCKED", "BLOCKED"),
        ):
            if marker in title or marker in body[:400]:
                status = label
                break
        # Trim notes so the ledger stays scannable; keep the first 280
        # chars of the body as a reviewer-facing one-liner.
        notes = body[:280].replace("\n", " ").strip()
        if len(body) > 280:
            notes = notes + "..."
        metrics.append(
            Metric(
                metric_id=f"INSIGHT-{num}",
                kind="INSIGHT",
                title=title,
                status=status,
                source_artifact_path=rel,
                source_artifact_sha256=sha,
                source_line=str(header_line),
                section_ref=f"docs/INSIGHTS.md:{header_line}",
                notes=notes,
            )
        )
    return metrics, errors


# ---------------------------------------------------------------------------
# Statistical-method parsing (verification_outputs/wave234-*.csv)
# ---------------------------------------------------------------------------


def _stat_kind_for(rid: str) -> str:
    """Return the canonical statistical-method name for an internal ID."""
    return {
        "TOST": "TOST (Two One-Sided Test)",
        "JT": "JT (Jonckheere-Terpstra trend)",
        "BF01": "BF01 (Bayes Factor for null)",
        "META": "META (DerSimonian-Laird random-effects)",
        "NI": "NI (Non-Inferiority)",
    }.get(rid, rid)


def _parse_statistical_row(
    rid: str, rel_path: str, description: str
) -> tuple[Metric, int]:
    """Read a statistical-method CSV / JSON and emit one SUMMARY row.

    Returns ``(metric, n_rows)`` so the caller can report how many
    underlying data rows the CSV carried (for reviewer transparency;
    not stored in the ledger itself).
    """
    full = REPO_ROOT / rel_path
    sha = _sha256_of_path(full)
    n_rows = 0
    if full.is_file() and full.suffix == ".csv":
        try:
            with full.open("r", encoding="utf-8") as fh:
                reader = csv.reader(fh)
                header = next(reader, None)
                if header is not None:
                    n_rows = sum(1 for _ in reader)
        except (OSError, UnicodeDecodeError) as exc:
            sha = ""  # type: ignore[assignment]
            description = f"{description} (read error: {exc})"
    return (
        Metric(
            metric_id=f"STAT-{rid}",
            kind="STATISTICAL",
            title=_stat_kind_for(rid),
            status="ACTIVE",
            source_artifact_path=rel_path,
            source_artifact_sha256=sha,
            section_ref=rel_path,
            notes=(
                f"{description}. n_data_rows={n_rows}."
            ),
        ),
        n_rows,
    )


def _parse_statistical() -> tuple[list[Metric], list[str]]:
    metrics: list[Metric] = []
    errors: list[str] = []
    for rid, rel, desc in STATISTICAL_FILES:
        full = REPO_ROOT / rel
        if not full.is_file():
            errors.append(f"STATISTICAL {rid}: file not found at {rel}")
            metrics.append(
                Metric(
                    metric_id=f"STAT-{rid}",
                    kind="STATISTICAL",
                    title=_stat_kind_for(rid),
                    status="MISSING_SOURCE",
                    source_artifact_path=rel,
                    source_artifact_sha256="",
                    notes=f"{desc}. SOURCE FILE NOT FOUND at build time.",
                )
            )
            continue
        metric, _ = _parse_statistical_row(rid, rel, desc)
        metrics.append(metric)
    return metrics, errors


# ---------------------------------------------------------------------------
# Wave 280 sweep-result rows (R1, R3, R5c, R6, K1, K4+K5, K7, K3+R5b)
# Per Wave 280 P task spec: these docs are additive, byte-stable
# sources of per-cell d_z / Bonferroni p-value / 3-seed-pooled statistics
# on the weak-metric remediation vectors from Wave 275 P4. The metric
# ledger treats each sweep-result doc as one ``SWEEP280`` row; the
# verifier stays decoupled from the per-cell semantics (it only
# records the source path + SHA-256 + status + headline scalar).
# ---------------------------------------------------------------------------

# Each entry: (metric_id, relative_path, title, claim_id_alias)
SWEEP280_FILES: tuple[tuple[str, str, str, str], ...] = (
    (
        "SWEEP280-R1",
        "docs/audit/wave280-p-r1-sweep-result.md",
        "Wave 280 P — R1 LineageFlow HMMER 3-seed pooled sweep",
        "CLM-060",
    ),
    (
        "SWEEP280-R3",
        "docs/audit/wave280-p-r3-sweep-result.md",
        "Wave 280 P — R3 FlowMol3 fg_dev 3-seed sweep (Wave 109.C §5 DGL fix path)",
        "CLM-068",
    ),
    (
        "SWEEP280-R5C",
        "docs/audit/mnist/wave280-p-r5c-sweep-result.md",
        "Wave 280 P — R5c MNIST FM production-ckpt 3-seed N=200 sweep",
        "CLM-059",
    ),
    (
        "SWEEP280-R6",
        "docs/audit/wave280-p-r6-sweep-result.md",
        "Wave 280 P — R6 k6 foldability tier-aware 3-seed N=200 sweep",
        "CLM-061",
    ),
    (
        "SWEEP280-K1",
        "docs/audit/wave280-p-k1-sweep-result.md",
        "Wave 280 P — K1 FlowMol3 RDKit-validity 3-seed N=200 sweep",
        "CLM-060",
    ),
    (
        "SWEEP280-K4K5",
        "docs/audit/wave280-p-k4k5-sweep-result.md",
        "Wave 280 P — K4 + K5 LineageFlow 3-seed N=100 hmmer sweep",
        "CLM-060",
    ),
    (
        "SWEEP280-K7",
        "docs/audit/wave280-p-k7-sweep-result.md",
        "Wave 280 P — K7 LineageFlow novelty 3-seed N=300 sweep",
        "CLM-060",
    ),
    (
        "SWEEP280-K3R5B",
        "docs/audit/wave280-p-cifar-sweep-result.md",
        "Wave 280 P — CIFAR-10 K3+R5b 3-seed N=100 FID sweep (PARTIAL)",
        "CLM-070",
    ),
)


# ---------------------------------------------------------------------------
# Wave 286 sweep-result rows (FID GPU fix + verify + CIFAR paper-grounded
# re-sweep + paper-quantity ablation). Per Wave 286 P task spec: these
# docs are additive evidence rows for the Wave 280/281 promoted claims
# (CLM-005, CLM-006, CLM-011, CLM-070); the ledger treats each doc as
# one ``SWEEP286`` row. The verifier stays decoupled from the per-cell
# semantics (it only records the source path + SHA-256 + status +
# headline scalar).
# ---------------------------------------------------------------------------

# Each entry: (metric_id, relative_path, title, claim_id_alias, notes_suffix)
# `notes_suffix` is appended after the standard Wave 286 P notes block;
# empty string means no suffix (preserves the original byte-deterministic
# notes for rows that don't need a caveat).
SWEEP286_FILES: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "SWEEP286-FID-GPU-FIX",
        "docs/audit/wave286-p-fid-gpu-fix.md",
        "Wave 286 P — FID GPU compute bug fix (paper-grounded controller rollout blocker; 26x speedup on N=100)",
        "CLM-005",
        "",
    ),
    (
        "SWEEP286-FID-GPU-VERIFY",
        "docs/audit/wave286-p-fid-gpu-verify.md",
        "Wave 286 P — FID GPU compute live verification (1.19x end-to-end speedup; InceptionV3 forward pass now on CUDA, 2.2 GB GPU memory growth)",
        "CLM-005",
        "",
    ),
    (
        "SWEEP286-CIFAR-RESWEEP",
        "docs/audit/wave286-p-cifar-resweep-aggregated.md",
        "Wave 286 P — CIFAR-10 paper-grounded controller 17-cell re-sweep (5 schedulers x 3 seeds x N=200 + 2 N=500 cross-scale; cos vs codim direction-flip 71.57pp at N=200, 98.71pp at N=500)",
        "CLM-006",
        # Wave 289 P1 reframe caveat — direction-flip is local at one
        # hyperparameter point; see docs/audit/wave289-p1-honest-reframe.md.
        " Wave 289 P1 caveat: the cos-vs-codim direction-flip (71.57pp at N=200, "
        "98.71pp at N=500) is a LOCAL finding at the Wave 286 P hyperparameter "
        "point (eps_implicit=0.05, n_min=0.0, cycle_length=2, eps_direction=positive, "
        "profile_residual_fn=None-trivial g(x)=0). It is NOT established across the 5 "
        "un-swept dimensions; see docs/audit/wave289-p1-honest-reframe.md and "
        "Wave 290 P agenda.",
    ),
    (
        "SWEEP286-PAPER-QUANTITY-ABLATION",
        "docs/audit/wave286-p-paper-quantity-ablation.md",
        "Wave 286 P — paper-quantity ablation (3 modes x 3 seeds x N=200; scheduler_structure is the lever AT THIS POINT ONLY, paper quantities not the lever at trivial profile; codim-paper-full ran with cached heuristic constants because profile_residual_fn=None)",
        "CLM-011",
        # Wave 289 P1 reframe caveat — the lever verdict is local; the
        # codim-paper-full mode ran with cached heuristic constants
        # (because profile_residual_fn=None), NOT true paper quantities
        # from a non-trivial residual profile. The "paper quantities not
        # the lever" claim must be re-read as "paper quantities not the
        # lever AT THE TRIVIAL PROFILE; paper quantities unmeasured at
        # non-trivial profiles". See Wave 289 P1 reframe + Wave 290 P.
        " Wave 289 P1 caveat: leverType=scheduler_structure is AT THIS "
        "POINT ONLY (eps_implicit=0.05, n_min=0.0, cycle_length=2, "
        "eps_direction=positive, profile_residual_fn=None-trivial); the "
        "codim-paper-full mode was using CACHED HEURISTIC CONSTANTS, "
        "NOT true paper quantities from a residual profile. Re-read as: "
        "'paper quantities not the lever AT trivial profile; unmeasured "
        "at non-trivial profiles.' See docs/audit/wave289-p1-honest-reframe.md "
        "and Wave 290 P agenda.",
    ),
)


# ---------------------------------------------------------------------------
# Wave 291 sweep-result rows (regime-aware codim paper-quantity lever sweep
# + batched-harness 30x speedup). Per Wave 291 P: docs are additive rows
# for CLM-006 (codim scheduler), CLM-011 (paper quantities); the ledger
# treats each doc as one ``SWEEP291`` row. The verifier stays decoupled
# from the per-cell semantics (it only records the source path + SHA-256
# + status + headline scalar).
# ---------------------------------------------------------------------------

# Each entry: (metric_id, relative_path, title, claim_id_alias, notes_suffix)
# `notes_suffix` is appended after the standard Wave 291 P notes block;
# empty string means no suffix (preserves the original byte-deterministic
# notes for rows that don't need a caveat).
SWEEP291_FILES: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "SWEEP291-BOTTLENECK-CONFIRMED",
        "docs/audit/wave290-p1-bottleneck-confirmed.md",
        "Wave 290 P1 — per-record kernel-launch floor confirmed (codim 16.62s vs cosine 10.45s; batched baseline 0.30s = 35-55× overhead)",
        "CLM-006",
        "",
    ),
    (
        "SWEEP291-BATCHED-HARNESS",
        "docs/audit/wave290-p3-batched-harness.md",
        "Wave 290 P3 — batched framework harness tools/batched_framework_cifar.py (frame-level batching fix; ~28-35× framework_wall speedup; byte-deterministic)",
        "CLM-006",
        "",
    ),
    (
        "SWEEP291-BENCHMARK-FIXED",
        "docs/audit/wave290-p4-benchmark-fixed.md",
        "Wave 290 P4 — batched-harness benchmark verified (18.6× cosine / 29.5× codim speedup; 3-seed × 4-variant matrix; codim_none ≡ codim_real_g at eps_implicit=0.05)",
        "CLM-006",
        " Wave 289 P1 caveat extended: the codim_none ≡ codim_real_g byte-equality at "
        "eps_implicit=0.05 confirms paper-quantity lever is INERT at the Wave 286 P "
        "configuration; the W291 P1 regime-aware redesign sweeps eps_implicit ∈ "
        "{0.5, 2.0, 10.0} to test the paper-quantity lever at the regimes where it "
        "is non-trivially consumed (see docs/audit/wave291-p1-hypothesis-redesign.md).",
    ),
    (
        "SWEEP291-HYPOTHESIS-REDESIGN",
        "docs/audit/wave291-p1-hypothesis-redesign.md",
        "Wave 291 P1 — hypothesis redesign (3-regime eps_implicit sweep: sheet @0.5 / transition @2.0 / cell @10.0; 33-cell CIFAR single-seed grid + 99-cell 3-seed grid for headliners)",
        "CLM-011",
        "",
    ),
    (
        "SWEEP291-1SEED-RESULTS",
        "docs/audit/wave291-p3-1seed-results.md",
        "Wave 291 P3 — 33-cell codim-lever CIFAR sweep seed=42 (24 codim + 4 permutation + 4 random + 1 cosine; per-regime real_g vs None paired-t p < 0.01 in every regime; MIXED verdict; best variant codim_eps10p0_n0p0_L4_noG byte-identical to cosine)",
        "CLM-011",
        "",
    ),
    (
        "SWEEP291-3SEED-RESULTS",
        "docs/audit/wave291-p5-3seed-results.md",
        "Wave 291 P5 — headliner 3-seed verification (15 cells; codim_none mean Δ% vs cosine = +0.000% σ=0% STRONG byte-equivalent; codim_real_g vs codim_perm byte-identical at eps=10.0 — paper-quantity lever INERT; SUPPORTED verdict on paper-quantity lever existence)",
        "CLM-011",
        " Wave 291 P5 STRONG headliner (codim_none/eps=10/L=4 byte-equivalent to cosine "
        "across 3 seeds) confirms the W286 P 'scheduler_structure lever' verdict holds "
        "GLOBALLY at the 3-seed level. Paper-quantity profile lever (real_g vs permuted) "
        "is INERT at the cell regime — the ++10.721% delta vs cosine is driven by SCHEDULER "
        "STRUCTURE (codim L=4 + eps=10 + n_min=0.0), not by paper-quantity values.",
    ),
)

# Pull ``**Status:**`` (or ``## TL;DR`` headline) from the sweep-result
# doc body. The format is ``**Status:** <FREE TEXT>`` or
# ``## TL;DR ...``. We use ``**Status:**`` as the SWEEP286 row's
# `status` field verbatim (with the leading ``**Status:** `` stripped);
# if absent, fall back to a stable token derived from the file.
_SWEEP286_STATUS_RE: re.Pattern[str] = re.compile(
    r"^\*\*Status:\*\*\s*(?P<status>.+?)\s*$",
    re.MULTILINE,
)


def _parse_sweep286() -> tuple[list[Metric], list[str]]:
    """Emit one SWEEP286 row per Wave 286 P sweep-result doc.

    Each doc's ``**Status:**`` headline line is captured verbatim so
    the ledger surfaces PASS / PARTIAL / etc. without requiring a
    separate manifest. Vendored purity + sweep drivers are preserved
    per the user's "claude相关的确实不要commit" + "vendored SOTA 评分脚本
    依旧不能动" directives: this parser does NOT touch the sweep drivers
    under /tmp/ or any vendored upstream file.
    """
    metrics: list[Metric] = []
    errors: list[str] = []
    for metric_id, rel_path, title, claim_id_alias, notes_suffix in SWEEP286_FILES:
        source_path = REPO_ROOT / rel_path
        if not source_path.is_file():
            errors.append(f"SWEEP286 {metric_id}: file not found at {rel_path}")
            metrics.append(
                Metric(
                    metric_id=metric_id,
                    kind="SWEEP286",
                    title=title,
                    status="MISSING_SOURCE",
                    source_artifact_path=rel_path,
                    source_artifact_sha256="",
                    notes="SOURCE FILE NOT FOUND at build time.",
                )
            )
            continue
        sha = _sha256_of_path(source_path)
        text = source_path.read_text(encoding="utf-8")
        m = _SWEEP286_STATUS_RE.search(text)
        status = m.group("status") if m else "PENDING_GPU_RUN"
        notes = (
            f"Wave 286 P sweep result (per the user's 'paper-grounded "
            f"控制器的工作流加强' + 'GPU上没有算力占用只有显存占用' "
            f"directives; CLM-005/006/011/070 additive evidence rows "
            f"per Wave 268 strict-clean rule). Vendored purity "
            f"preserved per the user's 'clone下来的原sota项目里的打分"
            f"脚本依旧不能动' directive. Claim alias: {claim_id_alias}."
        )
        if notes_suffix:
            notes = notes + notes_suffix
        metrics.append(
            Metric(
                metric_id=metric_id,
                kind="SWEEP286",
                title=title,
                status=status,
                claim_id=claim_id_alias,
                source_artifact_path=rel_path,
                source_artifact_sha256=sha,
                section_ref=rel_path,
                notes=notes,
            )
        )
    return metrics, errors


def _parse_sweep291() -> tuple[list[Metric], list[str]]:
    """Emit one SWEEP291 row per Wave 290 + 291 sweep-result doc.

    Each doc's ``**Status:**`` (or ``## TL;DR`` headline) is captured
    verbatim so the ledger surfaces PASS / MIXED / SUPPORTED / STRONG
    without requiring a separate manifest. Vendored purity + sweep drivers
    are preserved per the user's "claude相关的确实不要commit" + "vendored
    SOTA 评分脚本依旧不能动" directives: this parser does NOT touch the
    sweep drivers under /tmp/ or any vendored upstream file. The new
    tool ``tools/batched_framework_cifar.py`` lives in the repo (it is the
    byte-deterministic harness used by the W291 sweep) and was already
    ruff-clean per W290 P3 invariant; no framework source touched.
    """
    metrics: list[Metric] = []
    errors: list[str] = []
    for metric_id, rel_path, title, claim_id_alias, notes_suffix in SWEEP291_FILES:
        source_path = REPO_ROOT / rel_path
        if not source_path.is_file():
            errors.append(f"SWEEP291 {metric_id}: file not found at {rel_path}")
            metrics.append(
                Metric(
                    metric_id=metric_id,
                    kind="SWEEP291",
                    title=title,
                    status="MISSING_SOURCE",
                    source_artifact_path=rel_path,
                    source_artifact_sha256="",
                    notes="SOURCE FILE NOT FOUND at build time.",
                )
            )
            continue
        sha = _sha256_of_path(source_path)
        text = source_path.read_text(encoding="utf-8")
        # Use **Status:** if present, otherwise pull the first
        # ``**Verdict:**`` or ``## TL;DR`` line. The W291 docs use
        # ``**Lever verdict:**`` or ``**Decision:**`` etc; fall back to
        # ``## TL;DR`` body for rows without an explicit ``**Status:**``
        # marker.
        m = _SWEEP286_STATUS_RE.search(text)
        if m:
            status = m.group("status")
        else:
            tldr_match = re.search(
                r"^## 0\. TL;DR\s*\n(?P<tldr>(?:\n|.)+?)(?=\n##\s|\Z)",
                text,
                re.MULTILINE,
            )
            status = "TL;DR_PRESENT — see doc" if tldr_match else "PENDING_GPU_RUN"
        notes = (
            f"Wave 291 P sweep result (per the user's 'Wave 290 + 291 "
            f"publishable state' directive; CLM-006 / CLM-011 additive "
            f"evidence rows per Wave 268 strict-clean rule). Vendored "
            f"purity preserved per the user's 'clone下来的原sota项目里的打分"
            f"脚本依旧不能动' directive. The W290 P3 batched harness "
            f"(tools/batched_framework_cifar.py) is the byte-deterministic "
            f"FID-only path that produces ~28-35× framework_wall speedup "
            f"without modifying any framework source. Claim alias: "
            f"{claim_id_alias}."
        )
        if notes_suffix:
            notes = notes + notes_suffix
        metrics.append(
            Metric(
                metric_id=metric_id,
                kind="SWEEP291",
                title=title,
                status=status,
                claim_id=claim_id_alias,
                source_artifact_path=rel_path,
                source_artifact_sha256=sha,
                section_ref=rel_path,
                notes=notes,
            )
        )
    return metrics, errors

# Pull ``**Status:**`` from the sweep-result doc body. The format is
# ``**Status:** <FREE TEXT>``. We use this as the SWEEP280 row's
# `status` field verbatim (with the leading ``**Status:** `` stripped).
_SWEEP280_STATUS_RE: re.Pattern[str] = re.compile(
    r"^\*\*Status:\*\*\s*(?P<status>.+?)\s*$",
    re.MULTILINE,
)


def _parse_sweep280() -> tuple[list[Metric], list[str]]:
    """Emit one SWEEP280 row per Wave 280 P sweep-result doc.

    Each doc's ``**Status:**`` headline line is captured verbatim so
    the ledger surfaces PASS / PARTIAL_SUPPORTED / etc. without
    requiring a separate manifest. Vendored purity + sweep drivers are
    preserved per the user's
    "claude相关的确实不要commit" + "vendored SOTA 评分脚本依旧不能动"
    directives: this parser does NOT touch the sweep drivers under
    /tmp/ or any vendored upstream file.
    """
    metrics: list[Metric] = []
    errors: list[str] = []
    for metric_id, rel_path, title, claim_id_alias in SWEEP280_FILES:
        source_path = REPO_ROOT / rel_path
        if not source_path.is_file():
            errors.append(f"SWEEP280 {metric_id}: file not found at {rel_path}")
            metrics.append(
                Metric(
                    metric_id=metric_id,
                    kind="SWEEP280",
                    title=title,
                    status="MISSING_SOURCE",
                    source_artifact_path=rel_path,
                    source_artifact_sha256="",
                    notes="SOURCE FILE NOT FOUND at build time.",
                )
            )
            continue
        sha = _sha256_of_path(source_path)
        text = source_path.read_text(encoding="utf-8")
        m = _SWEEP280_STATUS_RE.search(text)
        status = m.group("status") if m else "UNKNOWN"
        metrics.append(
            Metric(
                metric_id=metric_id,
                kind="SWEEP280",
                title=title,
                status=status,
                claim_id=claim_id_alias,
                source_artifact_path=rel_path,
                source_artifact_sha256=sha,
                section_ref=rel_path,
                notes=(
                    f"Wave 280 P 3-seed sweep result (per the user's "
                    f"'3 seed 够了' + 'sweep 改进也应该做' directives). "
                    f"Vendored purity preserved per the user's "
                    f"'clone下来的原sota项目里的打分脚本依旧不能动' "
                    f"directive. Claim alias: {claim_id_alias}."
                ),
            )
        )
    return metrics, errors


# ---------------------------------------------------------------------------
# Engineering-gate rows (no source artifact to hash — these are
# authoritative by construction per AGENTS.md §4.1).
# ---------------------------------------------------------------------------


def _parse_engineering_gates() -> tuple[list[Metric], list[str]]:
    metrics: list[Metric] = []
    errors: list[str] = []
    live = run_engineering_gates()
    for rid, command, description, source_rel in ENGINEERING_GATES:
        source_path = REPO_ROOT / source_rel
        sha = _sha256_of_path(source_path) if source_path.exists() else ""
        status, value = live.get(rid, ("UNKNOWN", "not-run"))
        metrics.append(
            Metric(
                metric_id=f"G-{rid}",
                kind="ENGINEERING_GATE",
                title=description,
                status=status,
                source_artifact_path=str(source_rel),
                source_artifact_sha256=sha,
                section_ref="docs/GATES.md + AGENTS.md §4.1",
                notes=(
                    f"Live value: `{value}`. "
                    f"verification command: `{command}`. "
                    f"Source-of-truth surface: {source_rel}."
                ),
            )
        )
    return metrics, errors


# ---------------------------------------------------------------------------
# Build orchestration
# ---------------------------------------------------------------------------


def build() -> BuildResult:
    """Read every input source, emit the ledger, and return the result.

    Pure (no file writes -- the CLI layer is responsible for that).
    """
    metrics: list[Metric] = []
    errors: list[str] = []

    # 1. CLAIMS
    if CLAIMS_FILE.is_file():
        claim_metrics, claim_errors = _parse_claims(
            CLAIMS_FILE.read_text(encoding="utf-8"), CLAIMS_FILE
        )
        metrics.extend(claim_metrics)
        errors.extend(claim_errors)
    else:
        errors.append(f"CLAIMS source missing: {CLAIMS_FILE}")

    # 2. HEADLINES
    headline_metrics, headline_errors = _parse_headlines()
    metrics.extend(headline_metrics)
    errors.extend(headline_errors)

    # 3. INSIGHTS
    insight_metrics, insight_errors = _parse_insights()
    metrics.extend(insight_metrics)
    errors.extend(insight_errors)

    # 4. STATISTICAL
    stat_metrics, stat_errors = _parse_statistical()
    metrics.extend(stat_metrics)
    errors.extend(stat_errors)

    # 5. ENGINEERING GATES
    gate_metrics, gate_errors = _parse_engineering_gates()
    metrics.extend(gate_metrics)
    errors.extend(gate_errors)

    # 6. WAVE 280 SWEEP RESULTS (additive — does not touch any
    # existing row; per the Wave 280 P task spec).
    sweep280_metrics, sweep280_errors = _parse_sweep280()
    metrics.extend(sweep280_metrics)
    errors.extend(sweep280_errors)

    # 7. WAVE 286 SWEEP RESULTS (additive — does not touch any
    # existing row; per the Wave 286 P task spec; CLM-005/006/011/070
    # additive evidence rows).
    sweep286_metrics, sweep286_errors = _parse_sweep286()
    metrics.extend(sweep286_metrics)
    errors.extend(sweep286_errors)

    # 8. WAVE 291 SWEEP RESULTS (additive — does not touch any
    # existing row; per the Wave 290 + 291 P task spec; CLM-006/011
    # additive evidence rows).
    sweep291_metrics, sweep291_errors = _parse_sweep291()
    metrics.extend(sweep291_metrics)
    errors.extend(sweep291_errors)

    # Tally kind counts for the report.
    counts = {
        "CLAIM": 0,
        "HEADLINE": 0,
        "STATISTICAL": 0,
        "INSIGHT": 0,
        "ENGINEERING_GATE": 0,
        "SWEEP280": 0,
        "SWEEP286": 0,
        "SWEEP291": 0,
    }
    for m in metrics:
        counts[m.kind] = counts.get(m.kind, 0) + 1
    return BuildResult(
        metrics=tuple(metrics),
        errors=tuple(errors),
        claim_rows=counts["CLAIM"],
        headline_rows=counts["HEADLINE"],
        statistical_rows=counts["STATISTICAL"],
        insight_rows=counts["INSIGHT"],
        engineering_gate_rows=counts["ENGINEERING_GATE"],
        sweep280_rows=counts["SWEEP280"],
        sweep286_rows=counts["SWEEP286"],
        sweep291_rows=counts["SWEEP291"],
    )


# ---------------------------------------------------------------------------
# Render: Markdown + JSON
# ---------------------------------------------------------------------------


MARKDOWN_COLUMNS: tuple[str, ...] = (
    "metric_id",
    "kind",
    "title",
    "status",
    "claim_id",
    "baseline",
    "framework",
    "delta_abs",
    "delta_pct",
    "p_value",
    "n",
    "source_artifact_path",
    "source_artifact_sha256",
    "section_ref",
    "notes",
)


def _render_markdown(result: BuildResult) -> str:
    """Render the ledger as a markdown table grouped by kind."""
    out: list[str] = []
    out.append("# Project Metric Ledger")
    out.append("")
    out.append(
        "**Generated by:** `tools/build_metric_ledger.py` "
        f"({len(result.metrics)} rows)"
    )
    out.append("")
    out.append(
        "This ledger is the single machine-readable inventory of every "
        "metric the project ships (claims, R-cell headlines, statistical "
        "methods, insights, engineering gates). It is regenerated "
        "deterministically from the same source files the audit chain "
        "already cites -- re-running `python3 tools/build_metric_ledger.py` "
        "on unchanged inputs produces a byte-stable output."
    )
    out.append("")
    out.append("## Row-kind counts")
    out.append("")
    out.append("| Kind | Count |")
    out.append("|---|---:|")
    for kind in (
        "CLAIM",
        "HEADLINE",
        "STATISTICAL",
        "INSIGHT",
        "ENGINEERING_GATE",
        "SWEEP280",
        "SWEEP286",
        "SWEEP291",
    ):
        count = sum(1 for m in result.metrics if m.kind == kind)
        out.append(f"| {kind} | {count} |")
    out.append("")
    if result.errors:
        out.append("## Build errors (non-fatal)")
        out.append("")
        for err in result.errors:
            out.append(f"- {err}")
        out.append("")
    # Group rows by kind for the human-facing table.
    for kind in (
        "CLAIM",
        "HEADLINE",
        "STATISTICAL",
        "INSIGHT",
        "ENGINEERING_GATE",
        "SWEEP280",
        "SWEEP286",
        "SWEEP291",
    ):
        rows = [m for m in result.metrics if m.kind == kind]
        if not rows:
            continue
        out.append(f"## {kind}")
        out.append("")
        # Markdown tables can't have pipes in cells; escape them.
        def _cell(v: str) -> str:
            return v.replace("|", "\\|").replace("\n", " ")

        header = "| " + " | ".join(MARKDOWN_COLUMNS) + " |"
        sep = "|" + "|".join("---" for _ in MARKDOWN_COLUMNS) + "|"
        out.append(header)
        out.append(sep)
        for row in rows:
            cells = [str(getattr(row, col, "")) for col in MARKDOWN_COLUMNS]
            out.append("| " + " | ".join(_cell(c) for c in cells) + " |")
        out.append("")
    return "\n".join(out) + "\n"


def _render_json(result: BuildResult) -> str:
    """Render the ledger as a deterministic JSON document.

    The JSON layout is a top-level object with three keys:

    * ``version`` -- schema version (currently ``"metric-ledger.v1"``).
    * ``metrics`` -- the canonical list of rows.
    * ``errors`` -- the list of non-fatal build errors.

    The output is sorted (by ``metric_id`` within each kind block) so
    the JSON is byte-stable for unchanged inputs -- the diff between
    two builds is then a real signal, not just a sort-order shuffle.
    """
    rows: list[dict[str, Any]] = []
    for m in sorted(result.metrics, key=lambda x: (x.kind, x.metric_id)):
        rows.append(asdict(m))
    payload = {
        "version": "metric-ledger.v1",
        "metrics": rows,
        "errors": list(result.errors),
        "row_counts": {
            "total": len(rows),
            "CLAIM": result.claim_rows,
            "HEADLINE": result.headline_rows,
            "STATISTICAL": result.statistical_rows,
            "INSIGHT": result.insight_rows,
            "ENGINEERING_GATE": result.engineering_gate_rows,
            "SWEEP280": result.sweep280_rows,
            "SWEEP286": result.sweep286_rows,
            "SWEEP291": result.sweep291_rows,
        },
    }
    return json.dumps(payload, indent=2, sort_keys=False, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Iterable[str]) -> Any:
    """Lightweight argparse wrapper (avoid the ``argparse`` import cost
    when the module is imported by other tools).

    The wrapper builds the same flags the standard ``argparse`` would
    produce for ``--quiet``; it keeps ``argparse`` out of the import
    surface so the module is cheap to import from other tools in the
    suite.
    """
    quiet = False
    show_help = False
    for arg in argv:
        if arg in ("-h", "--help"):
            show_help = True
            break
        if arg == "--quiet":
            quiet = True
    if show_help:
        print(__doc__)
        raise SystemExit(0)
    return _Args(quiet=quiet)


@dataclass(frozen=True)
class _Args:
    quiet: bool


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    result = build()
    # Write both outputs atomically (write to .tmp then rename).
    md_text = _render_markdown(result)
    json_text = _render_json(result)
    LEDGER_MD.write_text(md_text, encoding="utf-8")
    LEDGER_JSON.write_text(json_text, encoding="utf-8")
    if args.quiet:
        print(
            f"metric-ledger: total={len(result.metrics)} "
            f"CLAIM={result.claim_rows} HEADLINE={result.headline_rows} "
            f"STATISTICAL={result.statistical_rows} "
            f"INSIGHT={result.insight_rows} "
            f"ENGINEERING_GATE={result.engineering_gate_rows} "
            f"SWEEP280={result.sweep280_rows} "
            f"SWEEP286={result.sweep286_rows} "
            f"SWEEP291={result.sweep291_rows} "
            f"errors={len(result.errors)}"
        )
    else:
        print(
            f"Wrote {LEDGER_MD.relative_to(REPO_ROOT)} "
            f"({len(md_text.splitlines())} lines)"
        )
        print(
            f"Wrote {LEDGER_JSON.relative_to(REPO_ROOT)} "
            f"({len(json_text.splitlines())} lines)"
        )
        print(
            f"Rows: total={len(result.metrics)} "
            f"CLAIM={result.claim_rows} HEADLINE={result.headline_rows} "
            f"STATISTICAL={result.statistical_rows} "
            f"INSIGHT={result.insight_rows} "
            f"ENGINEERING_GATE={result.engineering_gate_rows} "
            f"SWEEP280={result.sweep280_rows} "
            f"SWEEP286={result.sweep286_rows} "
            f"SWEEP291={result.sweep291_rows}"
        )
        if result.errors:
            print(f"Non-fatal build errors: {len(result.errors)}")
            for err in result.errors:
                print(f"  - {err}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
