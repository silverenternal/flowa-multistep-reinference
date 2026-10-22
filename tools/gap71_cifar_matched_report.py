#!/usr/bin/env python3
"""GAP-71 — matched-NFE CIFAR report: BEFORE vs AFTER, with the seed check.

Pre-registration: ``docs/audit/gap71-image-spectral.md`` §0.4.

Reads ``<root>/<arm>/seed<k>/summary.json`` written by
``tools/run_sota_cifar_experiment.py`` and reports, per (arm, seed, scheduler):

* ``delta_pct`` — ``(fid_framework - fid_baseline) / fid_baseline * 100``;
* ``nfe_matched`` — a cell that is not matched is **excluded**, not averaged;
* the effective seed count — rule 3: a framework arm whose samples are
  byte-identical across seeds is reported as **n = 1** however many seeds were
  launched (Wave 280's failure: two seeds, one draw, md5 ``dded5996…``).

Then applies rules 1/2 and emits one verdict.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any

RETRACTION_THRESHOLD_PCT = 5.0  # §0.4 rule 1
SPECTRAL_HALVING = 0.5  # §0.4 rule 2


def _md5(path: Path) -> str:
    h = hashlib.md5()  # noqa: S324 — identity check, not security
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_cell(cell_dir: Path) -> dict[str, Any] | None:
    path = cell_dir / "summary.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text())


def _cell_deltas(cell: dict[str, Any]) -> dict[str, float]:
    rows = cell.get("rows") or []
    if not rows or rows[0].get("name") != "baseline":
        raise ValueError("summary.json rows[0] is not the baseline row")
    base = float(rows[0]["fid"])
    return {
        str(r["name"]): (float(r["fid"]) - base) / base * 100.0
        for r in rows[1:]
        if base > 0.0
    }


def _effective_n(arm_dir: Path, scheduler: str, seeds: list[int]) -> int:
    """Distinct sample files across seeds (rule 3)."""
    hashes = set()
    for seed in seeds:
        npz = arm_dir / f"seed{seed}" / f"{scheduler}_samples.npz"
        if npz.is_file():
            hashes.add(_md5(npz))
    return len(hashes) if hashes else 0


def _collect(
    root: Path, arm: str, seeds: list[int]
) -> tuple[dict[str, list[float]], dict[str, Any]]:
    """``{scheduler: [delta_pct, ...]}`` plus the per-cell audit trail."""
    deltas: dict[str, list[float]] = {}
    trail: dict[str, Any] = {"cells": {}, "excluded_unmatched": [],
                             "excluded_missing": [], "effective_n": {}}
    for seed in seeds:
        cell_dir = root / arm / f"seed{seed}"
        cell = _load_cell(cell_dir)
        if cell is None:
            trail["excluded_missing"].append(f"{arm}/seed{seed}")
            continue
        if not bool(cell.get("nfe_matched", False)):
            trail["excluded_unmatched"].append(f"{arm}/seed{seed}")
            continue
        trail["cells"][f"seed{seed}"] = {
            "n_samples": cell.get("n_samples"),
            "baseline_num_steps": cell.get("baseline_num_steps"),
            "match_nfe": cell.get("match_nfe"),
            "nfe_mismatch": cell.get("nfe_mismatch"),
            "spectral_band_fraction": cell.get("spectral_band_fraction"),
            "deltas": _cell_deltas(cell),
        }
        for name, value in trail["cells"][f"seed{seed}"]["deltas"].items():
            deltas.setdefault(name, []).append(float(value))

    for scheduler in deltas:
        trail["effective_n"][scheduler] = _effective_n(
            root / arm, scheduler, seeds
        )
    return deltas, trail


def _mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def _verdict(
    before_mean: float | None, after_mean: float | None
) -> tuple[str, list[str]]:
    notes: list[str] = []
    if before_mean is None:
        return "INCONCLUSIVE", ["no matched-budget BEFORE cell"]
    rule1 = before_mean < RETRACTION_THRESHOLD_PCT
    if rule1:
        notes.append(
            f"rule 1 fired: matched-budget BEFORE delta {before_mean:+.3f}% "
            f"< +{RETRACTION_THRESHOLD_PCT:.1f}% — the published magnitudes "
            "(gap46 +18..+23%, wave280 +52.33%) are retracted; the sign is not"
        )
    else:
        notes.append(
            f"rule 1 did not fire: matched-budget BEFORE delta "
            f"{before_mean:+.3f}% >= +{RETRACTION_THRESHOLD_PCT:.1f}%"
        )
    if after_mean is None:
        notes.append("no matched-budget AFTER cell")
        return ("RETRACTION_ONLY" if rule1 else "REGRESSION_REPLICATES"), notes
    rule2 = after_mean <= SPECTRAL_HALVING * before_mean
    notes.append(
        f"rule 2 {'holds' if rule2 else 'fails'}: AFTER {after_mean:+.3f}% vs "
        f"{SPECTRAL_HALVING:g} x BEFORE = {SPECTRAL_HALVING * before_mean:+.3f}%"
    )
    if rule1 and rule2:
        return "BAND_STRUCTURE_CONFIRMED", notes
    if rule1:
        return "BAND_STRUCTURE_NOT_THE_LEVER", notes
    return "REGRESSION_REPLICATES", notes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True,
                    help="verification_outputs/gap71-cifar-matched-nfe")
    ap.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    before, before_trail = _collect(args.root, "before", args.seeds)
    after, after_trail = _collect(args.root, "after", args.seeds)

    before_mean = _mean([v for vs in before.values() for v in vs])
    after_mean = _mean([v for vs in after.values() for v in vs])
    verdict, notes = _verdict(before_mean, after_mean)

    # Rule 3 is a reporting rule, so it fires per scheduler, not on the mean.
    collapsed = sorted(
        name
        for trail in (before_trail, after_trail)
        for name, n in trail["effective_n"].items()
        if n <= 1
    )

    payload = {
        "spec": "docs/audit/gap71-image-spectral.md §0.4",
        "root": str(args.root),
        "seeds": list(args.seeds),
        "before": {
            "mean_delta_pct": before_mean,
            "per_scheduler": {k: _mean(v) for k, v in before.items()},
            "per_seed": {k: _mean(list(v["deltas"].values()))
                         for k, v in before_trail["cells"].items()},
            "trail": before_trail,
        },
        "after": {
            "mean_delta_pct": after_mean,
            "per_scheduler": {k: _mean(v) for k, v in after.items()},
            "per_seed": {k: _mean(list(v["deltas"].values()))
                         for k, v in after_trail["cells"].items()},
            "trail": after_trail,
        },
        "rules": {
            "retraction_threshold_pct": RETRACTION_THRESHOLD_PCT,
            "spectral_halving": SPECTRAL_HALVING,
        },
        "seed_invariance_collapsed": collapsed,
        "verdict": verdict,
        "notes": notes,
    }
    if collapsed:
        payload["notes"].append(
            "rule 3: byte-identical framework samples across seeds for "
            f"{collapsed} — those cells are n = 1, not n = {len(args.seeds)}"
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2))
    print(json.dumps({k: payload[k] for k in ("verdict", "notes")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
