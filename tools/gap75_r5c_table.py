"""GAP-75: the corrected R5c table — N=1000 headline, 3 seeds, 3 arms.

GAP-73 showed that the paired chunk test every R5c number was built on is an
n=100 statistic whose bias scales with ``tr(S_g)``, so it rewards the shrunk
arm; on ``w16e1_10k`` it reverses the sign of the N=1000 comparison
(``docs/audit/gap73-r5c-statistic.md``).

This tool rebuilds the R5c cell from the samples that already exist:
``verification_outputs/gap57-equal-nfe-ladder-n1000/<ckpt>_s<seed>/`` holds
4 checkpoints x 3 seeds x (baseline + 3 arms) at N=1000, matched NFE=50, with
a seed-keyed prior so the three seeds are independent draws.

For each cell it reports the N=1000 headline delta against the full 10 000
reference, a within-seed SE from 30 paired N=500 subsamples (scaled by
sqrt(500/1000)), the across-seed mean and t-CI (df=2), sign agreement, and a
verdict using the paper's own vocabulary and its 1-FID-unit minimum effect.

No sampling. CPU only.

Example
-------
    python tools/gap75_r5c_table.py \
        --out verification_outputs/gap75-r5c-table/table.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from adaptive_reflow.eval.mnist_fid import (  # noqa: E402
    MnistFrechetProjectionEvaluator,
    _frechet_distance,
)

LABELS = ("production", "w16e1_10k", "w16e1_60k", "w16e1_5k")
SEEDS = (42, 43, 44)
ARMS = ("cosine", "codimension_sheet", "evidence_driven")
ROOT = _REPO_ROOT / "verification_outputs" / "gap57-equal-nfe-ladder-n1000"
MIN_EFFECT_FID = 1.0
T_CRIT_DF2 = 4.302653  # two-sided 95 %


def _load(path: Path) -> np.ndarray | None:
    if not path.exists():
        return None
    with np.load(path) as z:
        key = "samples" if "samples" in z.files else z.files[0]
        return np.asarray(z[key], dtype=np.float64)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache-dir", type=Path,
                    default=_REPO_ROOT / "data" / "mnist_fm_train_cache")
    ap.add_argument("--reps", type=int, default=30,
                    help="paired N=500 subsamples used for the within-seed SE")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    ev = MnistFrechetProjectionEvaluator(cache_dir=Path(args.cache_dir))
    projection = ev._projection
    ref = np.asarray(ev._ref_features, dtype=np.float64)
    rng = np.random.default_rng(int(args.seed))

    cells: list[dict] = []
    for label in LABELS:
        for arm in ARMS:
            per_seed: list[dict] = []
            for seed in SEEDS:
                d = ROOT / f"{label}_s{seed}"
                base = _load(d / "baseline_samples.npz")
                arm_s = _load(d / f"{arm}_samples.npz")
                if base is None or arm_s is None:
                    continue
                fb = base @ projection
                fa = arm_s @ projection
                n = min(fb.shape[0], fa.shape[0])
                fid_b = _frechet_distance(fb[:n], ref)
                fid_a = _frechet_distance(fa[:n], ref)
                # within-seed SE: paired N=500 subsamples, matched-N reference,
                # scaled to N=1000 by 1/sqrt(N).
                sub = 500 if n >= 500 else n
                deltas = []
                for _ in range(int(args.reps)):
                    gi = rng.choice(n, size=sub, replace=False)
                    ri = rng.choice(ref.shape[0], size=sub, replace=False)
                    fb_i = _frechet_distance(fb[gi], ref[ri])
                    fa_i = _frechet_distance(fa[gi], ref[ri])
                    deltas.append(fa_i - fb_i)
                se = float(np.std(deltas, ddof=1) * np.sqrt(sub / n))
                per_seed.append({
                    "seed": int(seed),
                    "fid_baseline": float(fid_b),
                    "fid_arm": float(fid_a),
                    "delta_fid": float(fid_a - fid_b),
                    "delta_pct": float(100.0 * (fid_a - fid_b) / fid_b),
                    "within_seed_se": se,
                })

            if not per_seed:
                continue
            arr = np.asarray([p["delta_fid"] for p in per_seed], dtype=np.float64)
            pct = np.asarray([p["delta_pct"] for p in per_seed], dtype=np.float64)
            mean = float(arr.mean())
            sd = float(arr.std(ddof=1)) if arr.size > 1 else float("nan")
            se_seed = sd / np.sqrt(arr.size) if arr.size > 1 else float("nan")
            ci = [mean - T_CRIT_DF2 * se_seed, mean + T_CRIT_DF2 * se_seed] \
                if arr.size > 1 else [float("nan")] * 2
            signs_agree = bool(np.all(arr > 0) or np.all(arr < 0))

            if not signs_agree:
                verdict = "UNDERPOWERED"
                why = "seed sign disagreement"
            elif abs(mean) < MIN_EFFECT_FID:
                verdict = "TIE"
                why = f"|mean| < {MIN_EFFECT_FID} FID"
            elif ci[0] > 0:
                verdict = "REGRESSES"
                why = "CI excludes 0, framework worse"
            elif ci[1] < 0:
                verdict = "SUPPORTS"
                why = "CI excludes 0, framework better"
            else:
                verdict = "UNDERPOWERED"
                why = "CI includes 0"

            # Two verdicts: the paper's effect-floor rule (|mean| >= 1 FID)
            # and the strict rule (the 3-seed CI excludes 0). They differ on
            # cells that are statistically clear but under one FID unit.
            if ci[0] > 0:
                strict = "REGRESSES"
            elif ci[1] < 0:
                strict = "SUPPORTS"
            elif abs(mean) < MIN_EFFECT_FID:
                strict = "TIE"
            else:
                strict = "UNDERPOWERED"

            cell = {
                "checkpoint": label,
                "arm": arm,
                "n_seeds": len(per_seed),
                "per_seed": per_seed,
                "mean_delta_fid": mean,
                "mean_delta_pct": float(pct.mean()),
                "sd_across_seeds": sd,
                "ci95_fid": ci,
                "signs_agree": signs_agree,
                "verdict": verdict,
                "verdict_reason": why,
                "strict_verdict": strict,
            }
            cells.append(cell)
            seed_str = " ".join("{:+.1f}".format(p["delta_fid"]) for p in per_seed)
            print(f"[gap75] {label:12s} {arm:18s} "
                  f"mean={mean:+7.3f} FID ({cell['mean_delta_pct']:+6.2f}%) "
                  f"CI[{ci[0]:+.2f},{ci[1]:+.2f}] "
                  f"seeds=[{seed_str}] "
                  f"-> {verdict} (strict {strict})", flush=True)

    summary: dict[str, int] = {}
    strict_summary: dict[str, int] = {}
    for c in cells:
        summary[c["verdict"]] = summary.get(c["verdict"], 0) + 1
        strict_summary[c["strict_verdict"]] = strict_summary.get(c["strict_verdict"], 0) + 1
    print(f"[gap75] effect-floor verdicts ({len(cells)} cells): {summary}")
    print(f"[gap75] strict (CI) verdicts ({len(cells)} cells): {strict_summary}")

    if args.out is not None:
        p = args.out if args.out.is_absolute() else _REPO_ROOT / args.out
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "min_effect_fid": MIN_EFFECT_FID,
            "n_seeds": len(SEEDS),
            "arms": list(ARMS),
            "verdict_distribution_effect_floor": summary,
            "verdict_distribution_strict": strict_summary,
            "cells": cells,
        }, indent=1))
        print(f"[gap75] wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
