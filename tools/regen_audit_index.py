#!/usr/bin/env python3
"""Regenerate ``docs/audit/INDEX.md`` from the on-disk audit tree.

``docs/audit/INDEX.md`` is a topic-cluster map: it groups every audit record
into one of 24 frozen clusters and marks which records a reviewer-facing
surface actually cites.  Until 2026-10-30 the generator lived at
``/tmp/regen_index.py`` and was never committed, so the map could not be
refreshed reproducibly; it had drifted to 484 listed rows against 613 records
on disk, and its own TOTAL row disagreed with the sum of its columns.

This script is that generator, reimplemented from the algorithm documented in
``docs/audit/INDEX_MAINTENANCE.md``:

1. **Pass 1 -- filename keyword scan.**  For each cluster in :data:`CLUSTERS`
   order, check whether any keyword appears in the lowercased *filename*.
   First match wins.  This pass applies to every cluster.
2. **Pass 2 -- content keyword scan.**  Only for ``mode="any"`` clusters: if
   pass 1 found nothing, re-check against the filename plus the first 40
   lines.  Per-model clusters (``mode="fname"``) are excluded so that a body
   mention of "cifar" cannot drag a Kanzi record into the CIFAR cluster.
3. **Fallback.**  ``governance``.

Cluster boundaries and order are frozen for the v3.0-tnnls-ready submission;
do not add, remove, or reorder a cluster without a governance decision.

A placement is sticky: an already-listed record keeps its cluster, so a wrong
placement survives a refresh.  To move one, delete its row from ``INDEX.md``
and re-run -- the keyword passes will place it afresh.

Usage::

    python3 tools/regen_audit_index.py --check   # exit 1 if the index is stale
    python3 tools/regen_audit_index.py           # rewrite docs/audit/INDEX.md
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
AUDIT_DIR = REPO_ROOT / "docs" / "audit"
INDEX = AUDIT_DIR / "INDEX.md"

#: ``(slug, topic label, mode, keywords)`` in display order.  ``mode`` is
#: ``"fname"`` (filename only -- the per-model clusters) or ``"any"``
#: (filename, then the first 40 lines of content).
CLUSTERS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("cifar", "CIFAR-10 RF (Rectified Flow on CIFAR-10)", "fname", ("cifar",)),
    ("kanzi", "Kanzi (protein flow autoencoder)", "fname", ("kanzi",)),
    ("flowmol3", "FlowMol3 (molecular 3D flow matching)", "fname", ("flowmol3",)),
    ("lineageflow", "LineageFlow (protein flow matching, HMMER + foldability + novelty)", "fname",
     ("lineageflow",)),
    ("freqflow", "FreqFlow + MM-FM (frequency / multimodal flow)", "fname",
     ("freqflow", "mm-fm", "mmfm")),
    ("mnist", "MNIST FM (MNIST flow matching)", "fname", ("mnist",)),
    ("brai", "BRAI perturbation (Bounded-Range Adaptive Integration)", "fname", ("brai",)),
    ("2d_toy", "2D toy FM (two-dim flow matching, 8gaussian)", "fname",
     ("2d", "two-moons", "two_moons", "eight-gaussians", "eight_gaussians", "toy")),
    ("self_flow", "Self-Flow ICML 2026 (image FM)", "fname", ("self-flow", "self_flow")),
    ("hidream", "HiDream-I1 (image diffusion)", "fname", ("hidream",)),
    ("graphbfn", "GraphBFN (graph Bayesian flow network)", "fname", ("graphbfn",)),
    ("lumina", "Lumina-Image-2.0 (image generation)", "fname", ("lumina",)),
    ("protbfn_abbfn", "ProtBFN-AbBFN (antibody / protein BFN)", "fname", ("protbfn", "abbfn")),
    ("wan2_2", "Wan2.2 video (video diffusion)", "fname", ("wan2", "wan-2")),
    ("web_research", "Web research 2026 (FM literature surveys)", "any",
     ("web-research", "web_research", "literature-survey")),
    ("engineering", "Engineering hygiene (ruff, mkdocs, pytest, byte-stable, CI, working-tree)", "name",
     ("ruff", "mypy", "mkdocs", "pytest", "ci-", "inventory", "doc-link", "manifest",
      "sha256", "portab", "clone", "readiness", "release-notes", "repo-docs",
      "working-tree", "byte-stable", "docstring")),
    ("reproducibility", "Reproducibility (reproducibility-record, preregistration, reproduce-script)", "name",
     ("preregistration", "reproduce", "reproducibility-record", "recipe")),
    ("data_packaging", "Data packaging + manifest (sha256, csv, metric-ledger)", "any",
     ("packaging", "metric-ledger", "ledger", "csv", "data-linkage", "bundle")),
    ("push_state", "Push state (push-ready, freeze, release, submission)", "name",
     ("push-ready", "push-unblock", "freeze", "submission")),
    ("algorithm_4arm", "Algorithm + 4-arm (Theorem 1, paper-quantity, A/B/C_g, efficiency)", "any",
     ("theorem", "4arm", "four-arm", "algorithm", "scheduler", "efficiency", "codimension",
      "lemma", "mechanism", "restart", "blend", "profile-residual", "dispersion", "covariance")),
    ("sweep_eval", "Sweep / eval / ablation (N=1000/30/64 sweeps, novelty, foldability)", "any",
     ("sweep", "ablation", "n1000", "nfe", "eval", "frontier", "regime", "foldability",
      "novelty", "hmmer", "fasta", "k7", "k6", "k4", "k1", "r5c", "r5a", "r5b")),
    ("stats_method", "Statistical methodology (R5/R6, p-value, bonferroni, TOST)", "any",
     ("tost", "bonferroni", "jonckheere", "p-value", "statistic", "kappa", "meta-analysis",
      "power", "underflow", "variance")),
    ("paper_claims", "Paper + claims (paper packaging, claim audit, paper-update)", "name",
     ("paper", "manuscript", "claims", "cover-letter", "abstract", "tnnls", "figure", "table")),
    ("final_verify", "Final-verify (per-wave close-out, pre-push hygiene)", "name",
     ("final-verify", "final", "close", "verify")),
    ("governance", "Governance (scope, audit, gap, condition, placeholder, cross-cutting)", "name",
     ("governance", "audit-index", "placeholder")),
)

#: Reviewer-facing docs; a record cited from any of these is *Active*.
ACTIVE_SURFACES: tuple[str, ...] = (
    "docs/CLAIMS.md",
    "docs/CONSOLIDATED_RESULTS.md",
    "docs/METRIC_LEDGER.md",
    "docs/INSIGHTS.md",
    "docs/ARCHITECTURE.md",
    "docs/README.md",
    "docs/cover-letter-tnnls.md",
    "docs/push-ready-summary.md",
    "docs/PAPER-EVIDENCE.md",
    "docs/paper-profile.md",
    "docs/baseline-audit-report.md",
    "docs/submission-checklist-final.md",
    "docs/RELEASE-NOTES.md",
    "docs/environments.md",
    "docs/TESTING_STRATEGY.md",
    "docs/code-release-checklist.md",
    "docs/算法实现说明.md",
    "supplementary.md",
)

#: The TNNLS package cites audit records for its data-availability and
#: figure-generation claims, so its files count as surfaces too.
TNNLS_GLOB = "tnnls_submission/*.md"

_GAP_RE = re.compile(r"^gap\d")
_CITATION_RE = re.compile(r"audit/([A-Za-z0-9_.\-/]+\.md)")
_ROW_RE = re.compile(r"^- `([^`]+)`$", re.M)
#: Permissive reader: accepts the size suffix older rows carried.
_ROW_READ_RE = re.compile(r"^- `([^`]+)`(?: \([^)]*\))?$", re.M)
_KIND_RE = re.compile(r"\*\*(Active|Historical)[^*]*\*\*")


def _read_index() -> tuple[dict[str, str], dict[str, bool], dict[str, str]]:
    """Return (cluster by record, active flag by record, description by cluster)."""
    if not INDEX.is_file():
        return {}, {}, {}
    text = INDEX.read_text(encoding="utf-8")
    cluster: dict[str, str] = {}
    active: dict[str, bool] = {}
    description: dict[str, str] = {}

    for block in re.split(r"\n### Cluster: ", text)[1:]:
        slug = block.split("\n", 1)[0].split("`")[1]
        lines = block.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("**Files:"):
                rest = [ln.strip() for ln in lines[i + 1:] if ln.strip()]
                if rest:
                    description[slug] = rest[0]
                break
        kind = None
        for line in block.split("\n"):
            m = _KIND_RE.search(line)
            if m:
                kind = m.group(1)
                continue
            r = _ROW_READ_RE.match(line.strip())
            if r and kind:
                cluster[r.group(1)] = slug
                active[r.group(1)] = kind == "Active"
    return cluster, active, description


def _records() -> list[tuple[str, pathlib.Path]]:
    """Every audit record as (path relative to docs/audit, path), minus the index."""
    return [
        (path.relative_to(AUDIT_DIR).as_posix(), path)
        for path in sorted(AUDIT_DIR.rglob("*.md"))
        if path != INDEX
    ]


def _classify(rel: str, path: pathlib.Path, known: dict[str, str]) -> str:
    """Place one record: reviewed placement first, then the documented scan.

    The previous index is the authority for records it already lists.  The
    keyword passes exist to place records that are new since the last refresh;
    running them over the whole tree instead would reshuffle a map that has
    already been reviewed, and a reading guide that moves under the reader is
    worse than one that lags.
    """
    for key in (rel, path.name):
        if key in known:
            return known[key]

    base = path.name.lower()
    # 1. A per-model cluster wins on the filename, so gap70-kanzi-latent stays
    #    with Kanzi even though it is also a gap record.
    for slug, _label, mode, keywords in CLUSTERS:
        if mode == "fname" and any(kw in base for kw in keywords):
            return slug
    # 2. The gap series (GAP-01 ... GAP-96) is cross-cutting by construction:
    #    one investigation, several model families, no single topic.  The
    #    governance cluster's own scope line names "gap" and "cross-cutting",
    #    so the series is kept together there rather than scattered across
    #    whichever keyword happens to appear in the first 40 lines.
    if _GAP_RE.match(base):
        return "governance"
    # 3. Every other cluster matches on the filename.
    for slug, _label, mode, keywords in CLUSTERS:
        if mode in ("name", "any") and any(kw in base for kw in keywords):
            return slug
    # 4. Content scan, topic clusters only.
    for slug, _label, mode, keywords in CLUSTERS:
        if mode != "any" or not keywords:
            continue
        head = path.read_text(encoding="utf-8", errors="ignore").split("\n")[:40]
        haystack = "\n".join([base] + [line.lower() for line in head])
        if any(kw in haystack for kw in keywords):
            return slug
    return "governance"


def _cited() -> set[str]:
    surfaces = [REPO_ROOT / s for s in ACTIVE_SURFACES if (REPO_ROOT / s).is_file()]
    surfaces += sorted(REPO_ROOT.glob(TNNLS_GLOB))
    cited: set[str] = set()
    for surface in surfaces:
        cited.update(_CITATION_RE.findall(surface.read_text(encoding="utf-8", errors="ignore")))
    return cited


def build() -> str:
    known_cluster, _known_active, descriptions = _read_index()
    cited = _cited()

    grouped: dict[str, list[tuple[str, pathlib.Path, bool]]] = {c[0]: [] for c in CLUSTERS}
    for rel, path in _records():
        slug = _classify(rel, path, known_cluster)
        grouped.setdefault(slug, []).append((rel, path, rel in cited or path.name in cited))
    for rows in grouped.values():
        rows.sort(key=lambda row: row[0])

    order = [c[0] for c in CLUSTERS] + sorted(set(grouped) - {c[0] for c in CLUSTERS})
    titles = {c[0]: c[1] for c in CLUSTERS}
    total = sum(len(grouped[s]) for s in order)
    n_active = sum(1 for s in order for row in grouped[s] if row[2])

    out = [
        "# Project Audit Index",
        "",
        "> **Topic-cluster map of every `docs/audit/*.md` record.** Generated — do not",
        "> hand-edit. Refresh with `python3 tools/regen_audit_index.py`; the algorithm and",
        "> the frozen cluster boundaries are described in",
        "> [`INDEX_MAINTENANCE.md`](INDEX_MAINTENANCE.md). Reviewers can answer *\"what does",
        "> the project claim about X?\"* by reading the cluster summary for X.",
        "",
        f"Records are grouped into {len(CLUSTERS)} frozen topic clusters. A record",
        "under `docs/audit/<cluster>/` is listed by bare filename. Placement is a",
        "filename keyword scan; the five topic clusters may additionally read the",
        "first 40 lines, and the per-model clusters never do. The `GAP-NN` series",
        "goes to `governance` unless its filename names a model. Unmatched records",
        "fall back to `governance`.",
        "",
        f"**Active** = cited by at least one of the {len(ACTIVE_SURFACES)} reviewer-facing",
        "surfaces or any `tnnls_submission/*.md` file. **Historical** = not cited;",
        "preserved for the per-wave audit trail.",
        "",
        "---",
        "",
        "## How to use this index",
        "",
        "1. **Pick the cluster that matches your question** (CIFAR-10, Kanzi,",
        "   LineageFlow, Algorithm / Theorem 1, Statistical methodology, ...).",
        "2. **Read the cluster summary** — one paragraph, written without wave numbers,",
        "   describing what the project claims and where the evidence lives.",
        "3. **Open the active records first** — those are cited by reviewer-facing docs.",
        "4. **Historical records** trace how a result evolved; skip them on a first read.",
        "",
        "---",
        "",
        "## Cluster map",
        "",
        "| Cluster | Topic | Files | Active | Historical |",
        "|---------|-------|------:|------:|-----------:|",
    ]
    for slug in order:
        rows = grouped[slug]
        n_act = sum(1 for row in rows if row[2])
        out.append(f"| `{slug}` | {titles.get(slug, slug)} | {len(rows)} | {n_act} | {len(rows) - n_act} |")
    out += [
        f"| **TOTAL** | — | **{total}** | **{n_active}** | **{total - n_active}** |",
        "",
        "---",
        "",
        "## Cluster details",
    ]

    for slug in order:
        rows = grouped[slug]
        if not rows:
            continue
        n_act = sum(1 for row in rows if row[2])
        out += [
            "",
            f"### Cluster: `{slug}` — {titles.get(slug, slug)}",
            "",
            f"**Files: {len(rows)}** (active: {n_act}, historical: {len(rows) - n_act})",
            "",
            descriptions.get(slug, f"{titles.get(slug, slug)}. Audit records for this topic."),
            "",
        ]
        for label, flag in (("Active", True), ("Historical", False)):
            subset = [row for row in rows if row[2] is flag]
            if not subset:
                continue
            out.append(
                f"**{label} (cited by at least one reviewer-facing surface):**" if flag
                else f"**{label} ({len(subset)} files, not cited by reviewer-facing surfaces):**"
            )
            out.append("")
            for _rel, path, _flag in subset:
                out.append(f"- `{path.name}`")
            out.append("")
        out += ["---"]

    return "\n".join(out).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Regenerate docs/audit/INDEX.md.")
    parser.add_argument("--check", action="store_true", help="exit 1 if the index is stale")
    args = parser.parse_args(argv)

    rendered = build()
    current = INDEX.read_text(encoding="utf-8") if INDEX.is_file() else ""
    if args.check:
        if rendered != current:
            print("STALE: docs/audit/INDEX.md differs from a fresh build")
            return 1
        print(f"OK: docs/audit/INDEX.md is current ({rendered.count(chr(10) + '- `')} records)")
        return 0

    INDEX.write_text(rendered, encoding="utf-8")
    print(f"wrote {INDEX.relative_to(REPO_ROOT)} ({rendered.count(chr(10) + '- `')} records)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
