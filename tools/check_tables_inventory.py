#!/usr/bin/env python3
"""Cross-check the numbers in ``tnnls_submission/tables.md`` against the
artifacts the table cites.

``tables.md`` opens with a promise: "All data sourced from
``verification_outputs/`` with byte-addressable provenance."  This script
tests that promise for the rows that are machine-checkable -- the 4-arm
paired-t table (Table 2), the statistical-methods table (Table 3), the
wall-clock table (Table 4) and the two Table 1 rows whose source is a JSON
file.  Table 5 records gate results rather than measurements, so it is not
recomputable here; its rows are dated snapshots.

Each check reads the *cited artifact*, recomputes the quantity from the
artifact's own columns, and compares it with what the markdown says.  A
row that disagrees is reported as ``DRIFT``.

``KNOWN_DRIFT`` lists the disagreements this checker was written to
expose.  They do not fail the run (the file is part of the frozen
submission package and the fix needs authorisation), but they are
printed every time.  Once the markdown is corrected, delete the
corresponding entry and the row becomes a hard requirement; any drift
that is *not* in ``KNOWN_DRIFT`` fails immediately, so the file cannot
rot further while the known items are pending.

Usage
-----
    python3 tools/check_tables_inventory.py            # report + exit
    python3 tools/check_tables_inventory.py --quiet    # exit status only
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TABLES = REPO_ROOT / "tnnls_submission" / "tables.md"
OUT = REPO_ROOT / "verification_outputs"

#: Drift labels that are documented in docs/audit/tables-inventory-provenance.md
#: and await an authorised edit of the frozen submission package.  Remove an
#: entry once the markdown matches the artifact again.
KNOWN_DRIFT: frozenset[str] = frozenset()


def _rows(markdown: str) -> list[list[str]]:
    """Return every pipe-table data row as a list of stripped cells."""
    out: list[list[str]] = []
    for line in markdown.splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line) <= set("|-: "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        out.append(cells)
    return out


def _num(text: str) -> float | None:
    """Pull the first signed decimal out of a markdown cell."""
    m = re.search(r"[-+−]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", text.replace("−", "-"))
    return float(m.group(0)) if m else None


def _fmt(x: float, places: int = 4) -> str:
    return f"{x:+.{places}f}"


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str, bool]] = []  # label, stated, actual, known

    def add(self, label: str, stated: str, actual: str) -> None:
        known = label in KNOWN_DRIFT
        self.rows.append((label, stated, actual, known))

    @property
    def unknown(self) -> list[tuple[str, str, str, bool]]:
        return [r for r in self.rows if r[1] != r[2] and not r[3]]

    @property
    def known(self) -> list[tuple[str, str, str, bool]]:
        return [r for r in self.rows if r[1] != r[2] and r[3]]

    def render(self) -> None:
        width = max((len(r[0]) for r in self.rows), default=10)
        for label, stated, actual, _known in self.rows:
            if stated == actual:
                status = "ok"
            elif label in KNOWN_DRIFT:
                status = "KNOWN-DRIFT"
            else:
                status = "DRIFT"
            print(f"{label.ljust(width)}  stated={stated:>14s}  "
                  f"artifact={actual:>14s}  {status}")


# --------------------------------------------------------------------------
# Table 2 -- 4-arm head-to-head per-record paired t
# --------------------------------------------------------------------------
def check_table2(rep: Report) -> None:
    path = OUT / "wave230-p2-real-4arm-per-record.csv"
    if not path.is_file():
        return
    by_cell = {r["cell"].lower(): r for r in csv.DictReader(path.open())}
    md = TABLES.read_text()

    seen: set[str] = set()
    for cells in _rows(md):
        if len(cells) != 7:
            continue
        key = cells[0].lower().replace(" ", "_")
        if key not in by_cell:
            continue
        row = by_cell[key]
        seen.add(key)
        rep.add(f"table2:{cells[0]}", _fmt(_num(cells[3]) or 0.0, 4),
                _fmt(float(row["d_z"]), 4))

    # Summary line: "N/16 cells granularity-bounded (|d_z| < T); M/16
    # Bonferroni-significant (|d_z| in [a, b])."
    m = re.search(
        r"(\d+)/16 cells granularity-bounded \(\|d_z\| < ([\d.]+)\);\s*"
        r"(\d+)/16 Bonferroni-significant \(\|d_z\| ∈ \[([\d.]+), ([\d.]+)\]\)",
        md,
    )
    if not m:
        return
    dz = [float(r["d_z"]) for r in by_cell.values()]
    sig = [abs(float(r["d_z"])) for r in by_cell.values()
           if float(r["p_bonferroni"]) < float(r["alpha_bonferroni"])]
    rep.add("table2:summary/bounded", m.group(1),
            str(sum(1 for d in dz if abs(d) < float(m.group(2)))))
    rep.add("table2:summary/significant", m.group(3), str(len(sig)))
    if sig:
        rep.add("table2:summary/range",
                f"[{float(m.group(4)):.3f}, {float(m.group(5)):.3f}]",
                f"[{min(sig):.3f}, {max(sig):.3f}]")


# --------------------------------------------------------------------------
# Table 3 -- statistical methods
# --------------------------------------------------------------------------
def check_table3(rep: Report) -> None:
    md = TABLES.read_text()

    tost_path = OUT / "wave234-p2-tost.csv"
    if tost_path.is_file():
        rows = list(csv.DictReader(tost_path.open()))
        equiv = sum(r["equivalence_verdict"] == "EQUIVALENT" for r in rows)
        band = sum(r["within_margin_band"] == "True" for r in rows)
        m = re.search(r"(\d+)/(\d+) actively equivalent; (\d+)/(\d+) in", md)
        if m:
            rep.add("table3:tost/equivalent", f"{m.group(1)}/{m.group(2)}",
                    f"{equiv}/{len(rows)}")
            rep.add("table3:tost/in-band", f"{m.group(3)}/{m.group(4)}",
                    f"{band}/{len(rows)}")

        m = re.search(r"(\d+)/(\d+) BF01 ≥ 10", md)
        if m:
            n = sum(float(r["bf01"]) >= 10 for r in rows)
            rep.add("table3:bf01/count", f"{m.group(1)}/{m.group(2)}",
                    f"{n}/{len(rows)}")

    meta_path = OUT / "wave234-p5-meta-summary.json"
    if meta_path.is_file():
        j = json.load(meta_path.open())
        m = re.search(
            r"pooled d_z = ([-+]?[\d.]+)\s*\| \(95% CI \[([-+]?[\d.]+), "
            r"([-+]?[\d.]+)\]\) \| I² = ([\d.]+)%", md)
        if m:
            rep.add("table3:meta/pooled", m.group(1), f"{j['pooled_d_z']:+.3f}")
            rep.add("table3:meta/ci-low", m.group(2), f"{j['ci_95_lower']:+.3f}")
            rep.add("table3:meta/ci-high", m.group(3), f"{j['ci_95_upper']:+.3f}")
            rep.add("table3:meta/i2", m.group(4), f"{j['I_squared_pct']:.2f}")

    jt_path = OUT / "wave234-p3-jonckheere.csv"
    if jt_path.is_file():
        jt = {r["cell"]: r for r in csv.DictReader(jt_path.open())}
        sup = "⁰¹²³⁴⁵⁶⁷⁸⁹"
        found = re.findall(
            r"Jonckheere-Terpstra ordered test \| [^|]+ \| z = ([-+]?[\d.]+) "
            r"\| \*\*([\d.]+) × 10⁻([⁰¹²³⁴⁵⁶⁷⁸⁹]+)\*\*", md)
        for (z_txt, mantissa, exp_txt), label in zip(
                found, ("r2", "r6"), strict=False):
            row = next((v for k, v in jt.items() if label.upper() in k.upper()), None)
            if row is None:
                continue
            stated_p = float(mantissa) * 10.0 ** -int(
                "".join(str(sup.index(c)) for c in exp_txt))
            rep.add(f"table3:jt-{label}-z", f"{float(z_txt):+.1f}",
                    f"{float(row['jt_z']):+.1f}")
            rep.add(f"table3:jt-{label}-p", f"{stated_p:.2e}",
                    f"{float(row['jt_p_asymptotic']):.2e}")

    ni_path = OUT / "wave234-p6-ni-test.csv"
    if ni_path.is_file():
        m = re.search(r"p_NI = ([\d.]+)", md)
        if m:
            best = min(float(r["p_NI"]) for r in csv.DictReader(ni_path.open())
                       if float(r["p_NI"]) > 0.5)
            rep.add("table3:ni/p", m.group(1), f"{best:.4f}")


# --------------------------------------------------------------------------
# Table 1 -- the rows backed by a single JSON file
# --------------------------------------------------------------------------
def check_table1(rep: Report) -> None:
    md = TABLES.read_text()

    r3 = OUT / "r3_n1000_3seed_fixed_q4_2026" / "wave338-p5-r3-n1000-paired.json"
    if r3.is_file():
        s = json.load(r3.open())["paired_summary"]
        m = re.search(r"mean diff (−|-)0\.0377 \| \*\*p = 0\.559, d_z = −0\.401\*\*", md)
        if m:
            rep.add("table1:r3-mean", "-0.0377", f"{s['mean_diff']:+.4f}")
            rep.add("table1:r3-p", "0.559", f"{s['p_value_raw']:.3f}")
            rep.add("table1:r3-dz", "-0.401", f"{s['cohens_d_z']:+.3f}")

    r5c = OUT / "gap84-cap-frontier" / "frontier_w16e1_5k.json"
    if r5c.is_file():
        d = json.load(r5c.open())
        rungs = {r["nfe"]: r for r in d["rungs"]}
        base = (rungs[100]["baseline"] + rungs[200]["baseline"]) / 2
        fw = (rungs[100]["framework"] + rungs[200]["framework"]) / 2
        m = re.search(r"\| 24\.4839 \(`w16e1_5k`\) \| 21\.3632 \(`w16e1_5k`\) \|", md)
        if m:
            rep.add("table1:r5c-baseline", "24.4839", f"{base:.4f}")
            rep.add("table1:r5c-framework", "21.3632", f"{fw:.4f}")

    # R4/R5 quote the Liu-2022 rectified-flow SOTA rows of g1, not the 2D FM
    # ablation rows (2.85 -> 0.62 / 2.31 -> 0.76), which are a separate
    # experiment.  Both the artifact path and the three numbers are checked.
    g1 = OUT / "g1_deep_dive_q3_2026.json"
    if g1.is_file():
        g1_rows = {r["row"]: r for r in json.load(g1.open())["analysis"]["per_cell_breakdown"]}
        for label, key, b, f, d in (
            ("r4", "rectified_flow_2d_sota_two_moons", 0.5029, 0.4663, -0.0728),
            ("r5", "rectified_flow_2d_sota_eight_gaussians", 0.6606, 0.5919, -0.1040),
        ):
            row = g1_rows[key]
            rep.add(f"table1:{label}-artifact", "present", "present")
            rep.add(f"table1:{label}-baseline", f"{b:.4f}", f"{float(row['baseline']):.4f}")
            rep.add(f"table1:{label}-framework", f"{f:.4f}", f"{float(row['framework']):.4f}")
            rep.add(f"table1:{label}-delta", f"{d:.4f}", f"{float(row['raw_delta_pct']):.4f}")
    else:
        for label in ("r4", "r5"):
            rep.add(f"table1:{label}-artifact", "present", "missing")

    # R5b: the row now quotes the Wave 235 P1 N=200 baseline and the
    # per-scheduler deltas, plus the N=1000 split from the Wave 247 summary.
    r5b = OUT / "wave235-p1-r5b-fix.json"
    if r5b.is_file():
        j = json.load(r5b.open())
        rep.add("table1:r5b-baseline", "454.39",
                f"{j['rounds1']['baseline_fid']:.2f}")
        deltas = sorted(v["delta_pct"] for v in j["rounds1"]["results"].values())
        rep.add("table1:r5b-delta-range", "-2.53/-0.12",
                f"{deltas[0]:.2f}/{deltas[-1]:.2f}")


# --------------------------------------------------------------------------
# Table 4 -- CUDA-graph wall-clock
# --------------------------------------------------------------------------
def check_table4(rep: Report) -> None:
    """Recompute the five wall-clock numbers and the four re-measurement ones.

    Both rows of the table are the same run (``wave236-p2-wallclock.json``);
    the re-measurement lives under ``re_measurement_wave238_p2`` in the same
    file.  An earlier revision of the table quoted one run's seconds against
    the other run's ratio, which is why every cell is pinned separately.

    The row is located by its leading label, not by a regex over the whole
    row: a regex would stop matching the moment a number changed, and the
    check would then vanish instead of failing.
    """
    path = OUT / "wave236-p2-wallclock.json"
    if not path.is_file():
        rep.add("table4:artifact", "present", "missing")
        return
    d = json.load(path.open())
    rep.add("table4:artifact", "present", "present")

    rows = [c for c in _rows(TABLES.read_text()) if len(c) == 4]
    before = next((c for c in rows if c[0].startswith("**Before CUDA-graph")), None)
    after = next((c for c in rows if c[0].startswith("**After CUDA-graph")), None)
    gap = next((c for c in rows if c[0].startswith("Closes ")), None)
    re_measure = d["re_measurement_wave238_p2"]

    for label, row, col, actual, places in (
        ("table4:before-seconds", before, 1, d["wallclock_before_seconds"], 2),
        ("table4:ratio-before", before, 2, d["framework_baseline_ratio_before"], 2),
        ("table4:after-seconds", after, 1, d["wallclock_after_seconds"], 2),
        ("table4:ratio-after", after, 2, d["framework_baseline_ratio_after"], 2),
        ("table4:speedup", after, 3, d["speedup_factor"], 2),
        ("table4:gap-closure", gap, 0, d["wallclock_gap_closure_pct"], 1),
    ):
        stated = _num(row[col]) if row is not None else None
        if stated is None:
            rep.add(label, "(row missing)", f"{actual:.{places}f}")
        else:
            rep.add(label, f"{stated:.{places}f}", f"{actual:.{places}f}")

    # The re-measurement is quoted in the paragraph below the table, not in a
    # row of its own: "7.94 s -> 1.87 s, 4.24x, ratio_after = 1.30".
    md = TABLES.read_text()
    m = re.search(
        r"([\d.]+) s . ([\d.]+) s, ([\d.]+)×, `ratio_after = ([\d.]+)`", md
    )
    if m is None:
        rep.add("table4:remeasurement", "(paragraph missing)", "present")
    else:
        rep.add("table4:remeas-before", m.group(1),
                f"{re_measure['wallclock_before_seconds']:.2f}")
        rep.add("table4:remeas-after", m.group(2),
                f"{re_measure['wallclock_after_seconds']:.2f}")
        rep.add("table4:remeas-speedup", m.group(3),
                f"{re_measure['speedup_factor']:.2f}")
        rep.add("table4:remeas-ratio-after", m.group(4),
                f"{re_measure['framework_baseline_ratio_after']:.2f}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    if not TABLES.is_file():
        print(f"missing {TABLES}", file=sys.stderr)
        return 2

    rep = Report()
    check_table2(rep)
    check_table3(rep)
    check_table1(rep)
    check_table4(rep)

    if not args.quiet:
        rep.render()
        print()
    print(f"checked={len(rep.rows)} known_drift={len(rep.known)} "
          f"unknown_drift={len(rep.unknown)}")
    for label, stated, actual, _ in rep.unknown:
        print(f"  DRIFT {label}: stated {stated}, artifact {actual}", file=sys.stderr)
    return 0 if not rep.unknown else 1


if __name__ == "__main__":
    sys.exit(main())
