#!/usr/bin/env python3
"""GAP-79 lever 3 — the confirmation table §3.5 reads.

The screen (``tools/gap79_guidance_screen.py``) chooses a dose; it may never be
quoted. This tool reads the confirmation run — the selected weight at N = 1000
across the pre-registered seeds 42/43/44 — and answers the only question the
audit accepts: does the intended-hit rate rise for **every** family, with the
control family intact and the sample not collapsed?

Inputs are the upstream evaluator's per-record files, so the table is
re-derivable without re-scoring::

    <root>/seed42/control/upstream_framework/family_validity_per_seq.jsonl
    <root>/seed42/W<weight>/upstream_framework/family_validity_per_seq.jsonl
    <root>/seed42/<cell>/framework.fasta          # diversity guard
    ... (seed43, seed44)

Statistics, fixed before the confirmation data exists
-----------------------------------------------------
Records are paired **by ``qid``**: the generator seeds each record, so record
``i`` in the control and record ``i`` in the drift arm share their prior draw
and differ only by the guidance. Two intervals are reported for every family:

* ``record_ci`` — percentile bootstrap over the per-record paired indicator
  (10 000 resamples, stratified by seed). This is the literal reading of §3.5.
* ``seed_ci`` — a t interval across the three per-seed differences
  (``t`` multiplier 4.3027 at df = 2). Records inside a seed share the model
  and the prior, so they are not independent; this is the conservative read.

The verdict uses the **weaker** of the two: a family counts as improved only
if both lower bounds are above zero. Reporting both and taking the weaker one
is the only way to avoid choosing the statistic after seeing the number.

A WIN needs, for every family in ``REQUIRED``: both lower bounds > 0; plus
``GUARD`` not regressing; plus the §3.4 diversity guard at N = 1000.

Usage
-----
    python3 tools/gap79_confirmation_report.py \
        --root verification_outputs/gap79-r1-guidance/native \
        --weight 8 --seeds 42 43 44 \
        --out verification_outputs/gap79-r1-guidance/native/confirm_report.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:  # direct ``python3 tools/...`` invocation
    sys.path.insert(0, str(_REPO_ROOT))

from tools.gap79_dose_screen import load_per_seq  # noqa: E402
from tools.gap79_guidance_screen import diversity, read_fasta  # noqa: E402

SCHEMA = "gap79_guidance_confirmation_v1"
REQUIRED = ("PF00072", "PF02517", "PF00183")
GUARD = "PF00005"
MIN_UNIQUE_FRACTION = 0.95
MIN_ENTROPY_RATIO = 0.5
N_BOOT = 10_000
BOOT_SEED = 20261026


def _family(rec: dict) -> str:
    fam = str(rec.get("intended_family_canon") or rec.get("intended_family"))
    return fam.split(".")[0]


def _index(records: list[dict]) -> dict[str, dict[str, int]]:
    """``qid -> {family: hit}`` so the two arms pair by record."""
    out: dict[str, dict[str, int]] = {}
    for rec in records:
        qid = str(rec.get("qid"))
        if qid in out:
            raise SystemExit(f"duplicate_qid:{qid}")
        out[qid] = {
            "family": _family(rec),
            "hit": int(bool(rec.get("intended_hit_evalue"))),
        }
    return out


def paired_diffs(
    control: list[dict], treatment: list[dict]
) -> dict[str, dict[str, object]]:
    """Per-family ``treatment - control`` hit indicators, paired by ``qid``.

    Returns ``{family: {"diffs": [...], "control_hits": int, "treatment_hits": int}}``.
    """
    ctrl = _index(control)
    treat = _index(treatment)
    if set(ctrl) != set(treat):
        missing = sorted(set(ctrl) ^ set(treat))[:5]
        raise SystemExit(f"qid_sets_differ:{missing}")
    out: dict[str, dict[str, object]] = {}
    for qid, row in ctrl.items():
        fam = row["family"]
        if treat[qid]["family"] != fam:
            raise SystemExit(f"family_mismatch_at:{qid}")
        bucket = out.setdefault(
            fam, {"diffs": [], "control_hits": 0, "treatment_hits": 0}
        )
        bucket["diffs"].append(treat[qid]["hit"] - row["hit"])  # type: ignore[union-attr]
        bucket["control_hits"] = int(bucket["control_hits"]) + row["hit"]
        bucket["treatment_hits"] = int(bucket["treatment_hits"]) + treat[qid]["hit"]
    return out


def _seed_t_ci(per_seed: list[float]) -> dict:
    """t interval across the per-seed differences (df = n - 1)."""
    from scipy import stats

    n = len(per_seed)
    arr = np.asarray(per_seed, dtype=np.float64)
    mean = float(arr.mean())
    if n < 2:
        return {
            "n_seeds": n, "mean": mean, "sd": float("nan"),
            "t": float("nan"), "p": float("nan"),
            "ci_low": float("nan"), "ci_high": float("nan"),
        }
    sd = float(arr.std(ddof=1))
    se = sd / math.sqrt(n)
    t_crit = float(stats.t.ppf(0.975, df=n - 1))
    t_stat = mean / se if se > 0 else float("nan")
    p = (
        float(2.0 * stats.t.sf(abs(t_stat), df=n - 1))
        if t_stat == t_stat else float("nan")
    )
    return {
        "n_seeds": n,
        "mean": mean,
        "sd": sd,
        "se": se,
        "t": t_stat,
        "p": p,
        "ci_low": mean - t_crit * se,
        "ci_high": mean + t_crit * se,
    }


def _record_bootstrap_ci(by_seed: list[list[int]]) -> dict:
    """Percentile bootstrap over records, stratified by seed.

    Resampling records (not seeds) is the literal §3.5 reading; it is reported
    next to the seed interval, never instead of it.
    """
    rng = np.random.default_rng(BOOT_SEED)
    arrays = [np.asarray(v, dtype=np.float64) for v in by_seed]
    stats = np.empty(N_BOOT, dtype=np.float64)
    for b in range(N_BOOT):
        means = []
        for arr in arrays:
            if arr.size == 0:
                continue
            idx = rng.integers(0, arr.size, arr.size)
            means.append(float(arr[idx].mean()))
        stats[b] = float(np.mean(means)) if means else float("nan")
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return {
        "mean": float(np.mean([a.mean() for a in arrays if a.size])),
        "ci_low": float(lo),
        "ci_high": float(hi),
        "n_boot": N_BOOT,
        "stratified_by": "seed",
    }


def build(root: Path, weight: float, seeds: list[int]) -> dict:
    cells = []
    pooled: dict[str, list[list[int]]] = {}
    per_seed_means: dict[str, list[float]] = {}
    diversity_rows = []

    for seed in seeds:
        seed_dir = root / f"seed{seed}"
        ctrl_dir = seed_dir / "control"
        treat_dir = seed_dir / f"W{weight:g}"
        if not ctrl_dir.is_dir() or not treat_dir.is_dir():
            raise SystemExit(f"missing_cell:{ctrl_dir}|{treat_dir}")
        ctrl = load_per_seq(ctrl_dir, "framework")
        treat = load_per_seq(treat_dir, "framework")
        diffs = paired_diffs(ctrl, treat)
        fam_rows = {}
        for fam, bucket in diffs.items():
            values = bucket["diffs"]
            arr = np.asarray(values, dtype=np.float64)
            pooled.setdefault(fam, []).append(values)
            per_seed_means.setdefault(fam, []).append(float(arr.mean()))
            fam_rows[fam] = {
                "n": int(arr.size),
                "control_hits": int(bucket["control_hits"]),
                "treatment_hits": int(bucket["treatment_hits"]),
                "mean_diff": float(arr.mean()),
            }
        ctrl_div = diversity(read_fasta(ctrl_dir / "framework.fasta"))
        treat_div = diversity(read_fasta(treat_dir / "framework.fasta"))
        ratio = (
            treat_div["mean_positional_entropy_bits"]
            / ctrl_div["mean_positional_entropy_bits"]
            if ctrl_div["mean_positional_entropy_bits"] > 0 else 0.0
        )
        diversity_rows.append({
            "seed": seed,
            "control_unique": ctrl_div["unique_fraction"],
            "treatment_unique": treat_div["unique_fraction"],
            "entropy_ratio": ratio,
            "guard_ok": bool(
                treat_div["unique_fraction"] >= MIN_UNIQUE_FRACTION
                and ratio >= MIN_ENTROPY_RATIO
            ),
        })
        cells.append({"seed": seed, "per_family": fam_rows})

    families = {}
    for fam in sorted(pooled):
        by_seed = pooled[fam]
        seed_ci = _seed_t_ci(per_seed_means.get(fam, []))
        rec_ci = _record_bootstrap_ci(by_seed)
        lower = min(seed_ci["ci_low"], rec_ci["ci_low"])
        families[fam] = {
            "n_records_per_seed": [len(v) for v in by_seed],
            "per_seed_mean_diff": per_seed_means.get(fam, []),
            "seed_ci": seed_ci,
            "record_ci": rec_ci,
            "effective_ci_low": lower,
            "improved": bool(lower > 0.0),
        }

    guard = families.get(GUARD, {})
    guard_ok = bool(guard.get("seed_ci", {}).get("ci_low", -1.0) > -1e-12)
    required_ok = all(
        families.get(fam, {}).get("improved", False) for fam in REQUIRED
    )
    diversity_ok = all(row["guard_ok"] for row in diversity_rows)
    win = bool(required_ok and guard_ok and diversity_ok)

    return {
        "schema": SCHEMA,
        "root": str(root),
        "weight": float(weight),
        "seeds": list(seeds),
        "cells": cells,
        "families": families,
        "diversity": diversity_rows,
        "verdict": {
            "required_families_improved": required_ok,
            "guard_family_ok": guard_ok,
            "diversity_ok": diversity_ok,
            "win": win,
        },
        "caveats": [
            "record_ci is the literal §3.5 per-record interval but ignores "
            "within-seed dependence; seed_ci is conservative. The verdict "
            "takes the weaker lower bound, so neither may be quoted alone.",
            "A screen number chose this weight; only this table may be quoted.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, required=True,
                    help="Directory holding seed42/ seed43/ seed44/.")
    ap.add_argument("--weight", type=float, required=True)
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    report = build(args.root, args.weight, [int(s) for s in args.seeds])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")

    print(f"{'family':10s} {'ctrl':>6s} {'treat':>6s} {'diff':>8s} "
          f"{'seed_lo':>9s} {'rec_lo':>9s}  improved")
    for fam, row in report["families"].items():
        n = row["n_records_per_seed"][0]
        ctrl_hits = sum(c["per_family"][fam]["control_hits"] for c in report["cells"])
        treat_hits = sum(c["per_family"][fam]["treatment_hits"] for c in report["cells"])
        print(f"{fam:10s} {ctrl_hits:>6d} {treat_hits:>6d} "
              f"{row['seed_ci']['mean']:+8.4f} "
              f"{row['seed_ci']['ci_low']:+9.4f} "
              f"{row['record_ci']['ci_low']:+9.4f}  {row['improved']} "
              f"(n={n}/seed)")
    v = report["verdict"]
    print(f"WIN={v['win']} (required={v['required_families_improved']}, "
          f"guard={v['guard_family_ok']}, diversity={v['diversity_ok']})")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
