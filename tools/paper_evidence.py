"""Validate and render the single paper evidence register.

The register (`docs/paper-evidence.json`) is the one place that maps a paper
cell to its current verdict, its artifact, and its audit record. The markdown
surface (`docs/PAPER-EVIDENCE.md`) is generated from it so the two cannot
drift.

Rules enforced here, not in prose:

* every referenced artifact / audit path exists;
* every row carries a quote that occurs in its artifact or audit;
* a cell is `WIN` only when the point reading is `WIN` **and** the frontier
  reading is `WIN` (the `todo.json` win definition);
* a cell whose frontier is `UNMEASURED` cannot be `WIN`;
* ids are unique and the summary counts match the rows.

Usage:
    python3 tools/paper_evidence.py --check
    python3 tools/paper_evidence.py --render
    python3 tools/paper_evidence.py --render --out docs/PAPER-EVIDENCE.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "docs" / "paper-evidence.json"
DEFAULT_MD = ROOT / "docs" / "PAPER-EVIDENCE.md"

POINT_VERDICTS = {
    "WIN",
    "WIN_SINGLE_SEED",
    "TIE",
    "LOSS",
    "MIXED",
    "POWERED",
    "NOT_SIGNIFICANT",
    "UNDERPOWERED",
    "UNMEASURED",
}
FRONTIER_VERDICTS = {"WIN", "TIE", "LOSS", "INCOMPLETE", "UNMEASURED"}
CELL_VERDICTS = {"WIN", "OPEN", "BLOCKED", "SUPP"}
REQUIRED_CELL_KEYS = {
    "id",
    "name",
    "model",
    "metric",
    "direction",
    "protocol",
    "point",
    "frontier",
    "cell_verdict",
    "scope",
    "next",
    "paper_anchor",
    "claim",
}


def load(path: Path = DEFAULT_JSON) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def validate(register: dict[str, Any], root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    if register.get("schema") != "paper_evidence_register.v1":
        errors.append(f"schema: expected paper_evidence_register.v1, got {register.get('schema')!r}")
    for key in ("as_of", "basis", "canonical_taxonomy", "taxonomy_map", "cells", "summary"):
        if key not in register:
            errors.append(f"missing top-level key: {key}")
    cells = register.get("cells", [])
    if not isinstance(cells, list) or not cells:
        errors.append("cells: must be a non-empty list")
        return errors

    seen: set[str] = set()
    counts = {"WIN": 0, "OPEN": 0, "BLOCKED": 0, "SUPP": 0}
    for cell in cells:
        cid = cell.get("id", "<missing>")
        if cid in seen:
            errors.append(f"{cid}: duplicate id")
        seen.add(cid)
        missing = REQUIRED_CELL_KEYS - set(cell)
        if missing:
            errors.append(f"{cid}: missing keys {sorted(missing)}")
            continue

        point = cell["point"]
        frontier = cell["frontier"]
        if point.get("verdict") not in POINT_VERDICTS:
            errors.append(f"{cid}: bad point verdict {point.get('verdict')!r}")
        if frontier.get("verdict") not in FRONTIER_VERDICTS:
            errors.append(f"{cid}: bad frontier verdict {frontier.get('verdict')!r}")
        if cell["cell_verdict"] not in CELL_VERDICTS:
            errors.append(f"{cid}: bad cell verdict {cell['cell_verdict']!r}")
        counts[cell["cell_verdict"]] = counts.get(cell["cell_verdict"], 0) + 1

        both_win = point.get("verdict") == "WIN" and frontier.get("verdict") == "WIN"
        if cell["cell_verdict"] == "WIN" and not both_win:
            errors.append(f"{cid}: cell WIN requires point WIN and frontier WIN")
        if cell["cell_verdict"] == "OPEN" and both_win:
            errors.append(f"{cid}: both halves WIN but cell_verdict is OPEN")
        if frontier.get("verdict") == "UNMEASURED" and cell["cell_verdict"] == "WIN":
            errors.append(f"{cid}: unmeasured frontier cannot be WIN")

        for half in ("point", "frontier"):
            block = cell[half]
            for key in ("artifact", "audit", "quote"):
                if not block.get(key):
                    errors.append(f"{cid}.{half}: missing {key}")
                    continue
                if key in {"artifact", "audit"}:
                    path = root / block[key]
                    if not path.exists():
                        errors.append(f"{cid}.{half}.{key}: path does not exist: {block[key]}")
            quote = block.get("quote")
            if quote:
                haystack = _read(root / block["artifact"]) + "\n" + _read(root / block["audit"])
                if quote not in haystack:
                    errors.append(f"{cid}.{half}: quote not found in artifact or audit: {quote!r}")

    summary = register.get("summary", {})
    if summary.get("cells") != len(cells):
        errors.append(f"summary.cells={summary.get('cells')} but {len(cells)} rows")
    for verdict, count in counts.items():
        key = verdict.lower()
        if summary.get(key) != count:
            errors.append(f"summary.{key}={summary.get(key)} but {count} rows")
    return errors


def _cell_table(register: dict[str, Any]) -> list[str]:
    lines = [
        "| cell | model | metric | point | frontier | cell verdict | scope |",
        "|---|---|---|---|---|---|---|",
    ]
    for cell in register["cells"]:
        point = cell["point"]["verdict"]
        frontier = cell["frontier"]["verdict"]
        lines.append(
            f"| **{cell['id']}** | {cell['model']} | `{cell['metric']}` | {point} | "
            f"{frontier} | **{cell['cell_verdict']}** | {cell['scope']} |"
        )
    return lines


def _taxonomy_table(register: dict[str, Any]) -> list[str]:
    lines = [
        "| canonical | Wave-135 alias | `paper-data/` directory | model | metric |",
        "|---|---|---|---|---|",
    ]
    for row in register["taxonomy_map"]:
        lines.append(
            f"| **{row['canonical']}** | {row['wave135']} | {row['paper_data']} | "
            f"{row['model']} | `{row['metric']}` |"
        )
    return lines


def _quotable(register: dict[str, Any]) -> list[str]:
    wins = [c for c in register["cells"] if c["cell_verdict"] == "WIN"]
    point_wins = [
        c
        for c in register["cells"]
        if c["point"]["verdict"] in {"WIN", "WIN_SINGLE_SEED"} and c["cell_verdict"] == "OPEN"
    ]
    supp = [c for c in register["cells"] if c["cell_verdict"] == "SUPP"]
    lines = ["### Quotable as a cell win", ""]
    if not wins:
        lines.append("_None._")
    for cell in wins:
        lines.append(
            f"- **{cell['id']} — {cell['name']}.** {cell['point']['effect']}. "
            f"Frontier: {cell['frontier']['verdict']} over {cell['frontier']['grid']}. "
            f"Scope: {cell['scope']}"
        )
    lines += ["", "### Point reading measured, frontier half missing", ""]
    if not point_wins:
        lines.append("_None._")
    for cell in point_wins:
        lines.append(
            f"- **{cell['id']} — {cell['name']}** ({cell['point']['verdict']}). "
            f"{cell['point']['effect']}. Next: {cell['next']}"
        )
    lines += ["", "### Supplementary axes (not R-level win claims)", ""]
    if not supp:
        lines.append("_None._")
    for cell in supp:
        lines.append(f"- **{cell['id']} — {cell['name']}.** {cell['point']['effect']}.")
    return lines


def render(register: dict[str, Any]) -> str:
    summary = register["summary"]
    lines = [
        "# Paper evidence register",
        "",
        f"**As of:** {register['as_of']}  ",
        "**Machine-readable source:** [`paper-evidence.json`](paper-evidence.json)  ",
        "**Generated by:** `python3 tools/paper_evidence.py --render` — do not hand-edit this file.",
        "",
        "## What this page is",
        "",
        "One row per paper cell, with the current verdict, the artifact that carries",
        "the number, and the audit that records how it was produced. It replaces the",
        "four competing evidence tables that had accumulated (the frozen manuscript,",
        "`CLAIMS.md`, the 2026-10-19 evidence-grade table, and `todo.json`). Where this",
        "page disagrees with a frozen surface, **this page is current and the frozen",
        "surface is historical**.",
        "",
        "**Win rule.** " + register["basis"],
        "",
        "**Canonical numbering.** " + register["canonical_taxonomy"],
        "",
        "## Status at a glance",
        "",
        f"- Cells: **{summary['cells']}** — {summary['win']} WIN, {summary['open']} OPEN, "
        f"{summary['blocked']} BLOCKED, {summary['supp']} SUPP.",
        f"- Frontier coverage: **{summary['frontier_measured_r_cells']} of "
        f"{summary['frontier_r_cells']} R-level cells** have a complete (quality, NFE) grid.",
        f"- {summary['note']}",
        "",
        "## Cell register",
        "",
        *_cell_table(register),
        "",
        "## What the paper can quote today",
        "",
        *_quotable(register),
        "",
        "## Cell numbering across the historical surfaces",
        "",
        "The same cell has carried up to three names. The canonical column is the",
        "Wave-310 numbering used by the manuscript and `CLM-060`; the other two are",
        "kept only so old records remain traceable.",
        "",
        *_taxonomy_table(register),
        "",
        "## Per-cell detail",
        "",
    ]
    for cell in register["cells"]:
        point = cell["point"]
        frontier = cell["frontier"]
        lines += [
            f"### {cell['id']} — {cell['name']}",
            "",
            f"- **Protocol:** {cell['protocol']}",
            f"- **Point ({point['verdict']}):** {point['effect']}; CI {point['ci95']}; p {point['p']}.",
            f"- **Frontier ({frontier['verdict']}):** "
            f"{('grid ' + str(frontier['grid'])) if frontier['grid'] else 'no grid measured'}.",
            f"- **Cell verdict:** {cell['cell_verdict']} — {cell['scope']}",
            f"- **Next:** {cell['next']}",
            f"- **Artifact:** {point['artifact']}; **audit:** {point['audit']}.",
            f"- **Paper anchor:** {cell['paper_anchor']}; **claim:** {cell['claim']}.",
            "",
        ]
        if point.get("caveat"):
            lines += [f"> Caveat: {point['caveat']}", ""]
    lines += [
        "## Verification",
        "",
        "```bash",
        "python3 tools/paper_evidence.py --check",
        "python3 -m pytest tests/test_paper_evidence.py -q",
        "```",
        "",
        "_Frozen surfaces (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,",
        "`docs/drafts/paper-A-final.*`, `tnnls_submission/**`) are not edited by this",
        "register. Applying a row to the manuscript is a separate, user-gated step._",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate the register")
    parser.add_argument("--render", action="store_true", help="render the markdown surface")
    parser.add_argument("--json", default=str(DEFAULT_JSON), help="register path")
    parser.add_argument("--out", default=str(DEFAULT_MD), help="markdown output path")
    args = parser.parse_args(argv)

    register = load(Path(args.json))
    errors = validate(register)
    if args.check:
        for error in errors:
            print(f"FAIL {error}")
        if not errors:
            print(f"OK {args.json}: {len(register['cells'])} cells, all paths and quotes verified")
        return 1 if errors else 0

    if args.render:
        if errors:
            for error in errors:
                print(f"FAIL {error}")
            return 1
        Path(args.out).write_text(render(register), encoding="utf-8")
        print(f"wrote {args.out}")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
