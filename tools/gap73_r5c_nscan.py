"""GAP-73: is the R5c paired chunk statistic measuring quality or dispersion?

Why this exists
---------------
Every R5c (MNIST-FM projection-FID) number in the paper comes from
``scripts/wave191_p3_mnist_sweep.py``'s paired test: split both arms into 10
disjoint chunks of 100 samples, score each chunk against a 100-sample slice of
the reference, and run a paired t-test over the 10 chunk deltas.

That statistic lives at n=100 on BOTH sides. The Fréchet estimator is biased
upward at small n, and the bias scales with ``tr(S_g)`` -- so the arm with the
smaller sample dispersion is scored *lower* for a reason that has nothing to do
with quality. GAP-67 measured the symptom directly
(``docs/audit/gap67-covariance-preservation.md`` §2.2): on ``w16e1_10k`` the
chunk test reports −11.37 % (framework wins) while the N=1000 headline reports
+2.47 % (framework loses) -- a sign flip on the same samples.

What this tool measures
-----------------------
For each checkpoint and each (baseline, arm) pair:

1. ``Delta(N)`` for N in {100, 200, 500, 1000}, with the reference subsampled
   to the same N and with the SAME sample indices used for both arms. Averaged
   over ``--reps`` random draws at each N. If ``Delta(100)`` and ``Delta(1000)``
   differ in sign, the chunk statistic is not an estimate of the headline.
2. A paired bootstrap at N=1000 (B draws, same resampled indices for both
   arms, reference fixed at 10K) giving a 95 % CI for the headline delta. This
   is the statistic the chunk test should have been.
3. The exact chunk test, reproduced, so the two are on the same page.

Reads only frozen ``*_samples.npz`` artifacts. No GPU.

Example
-------
    python tools/gap73_r5c_nscan.py \
        --out verification_outputs/gap73-r5c-statistic/nscan.json
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
GAP57 = _REPO_ROOT / "verification_outputs" / "gap57-equal-nfe-ladder-n1000"
NS = (100, 200, 500, 1000)


def _load(path: Path) -> np.ndarray | None:
    if not path.exists():
        return None
    with np.load(path) as z:
        key = "samples" if "samples" in z.files else z.files[0]
        return np.asarray(z[key], dtype=np.float64)


def _delta_pct(base: np.ndarray, arm: np.ndarray, ref: np.ndarray) -> float:
    fb = _frechet_distance(base, ref)
    fa = _frechet_distance(arm, ref)
    return 100.0 * (fa - fb) / fb


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache-dir", type=Path,
                    default=_REPO_ROOT / "data" / "mnist_fm_train_cache")
    ap.add_argument("--reps", type=int, default=30,
                    help="random subsample draws per (checkpoint, N)")
    ap.add_argument("--bootstrap", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    ev = MnistFrechetProjectionEvaluator(cache_dir=Path(args.cache_dir))
    projection = ev._projection
    ref_all = np.asarray(ev._ref_features, dtype=np.float64)
    rng = np.random.default_rng(int(args.seed))

    out: dict[str, object] = {
        "reps": int(args.reps),
        "bootstrap": int(args.bootstrap),
        "seed": int(args.seed),
        "reference_n": int(ref_all.shape[0]),
        "cells": [],
    }

    for label in LABELS:
        d57 = GAP57 / f"{label}_s42"
        base = _load(d57 / "baseline_samples.npz")
        if base is None:
            print(f"[gap73] skip {label}: no baseline")
            continue
        fb = base @ projection
        arms = {"cosine": _load(d57 / "cosine_samples.npz")}

        for arm_name, arm_samples in arms.items():
            if arm_samples is None:
                continue
            fa = arm_samples @ projection
            n_max = min(fb.shape[0], fa.shape[0])

            # --- 1. Delta(N), chunk-style (gen N, reference N) ------------
            # The chunk test scores n=100 generated against n=100 reference.
            # Holding the reference at the same N isolates the small-N
            # estimator bias from the sample-size effect on the generated
            # side alone.
            scan: list[dict] = []
            for n in NS:
                if n > n_max:
                    continue
                deltas = []
                for _ in range(int(args.reps)):
                    gi = rng.choice(n_max, size=n, replace=False)
                    ri = rng.choice(ref_all.shape[0], size=n, replace=False)
                    deltas.append(_delta_pct(fb[gi], fa[gi], ref_all[ri]))
                arr = np.asarray(deltas, dtype=np.float64)
                scan.append({
                    "n": int(n),
                    "delta_pct_mean": float(arr.mean()),
                    "delta_pct_sd": float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
                    "n_draws": int(arr.size),
                })

            # --- 2. paired bootstrap at N=1000, reference fixed -----------
            boot = []
            for _ in range(int(args.bootstrap)):
                idx = rng.integers(0, n_max, size=n_max)
                boot.append(_delta_pct(fb[idx], fa[idx], ref_all))
            boot_arr = np.asarray(boot, dtype=np.float64)
            headline = _delta_pct(fb[:n_max], fa[:n_max], ref_all)

            # --- 3. exact chunk test reproduction ------------------------
            k = 10
            chunk = n_max // k
            perm = np.random.default_rng(int(args.seed) + 99).permutation(
                ref_all.shape[0])
            cd: list[float] = []
            for c in range(k):
                rc = ref_all[perm[c * chunk:(c + 1) * chunk]]
                sl = slice(c * chunk, (c + 1) * chunk)
                cd.append(_delta_pct(fb[sl], fa[sl], rc))
            cd_arr = np.asarray(cd, dtype=np.float64)
            se = float(cd_arr.std(ddof=1) / np.sqrt(k))
            from scipy import stats as _st
            t_stat = float(cd_arr.mean() / se) if se > 0 else float("inf")
            p_chunk = float(2.0 * _st.t.sf(abs(t_stat), df=k - 1))

            cell = {
                "checkpoint": label,
                "arm": arm_name,
                "n_max": int(n_max),
                "headline_delta_pct": float(headline),
                # Bootstrap CI: flagged in the audit as biased, because
                # resampling with replacement creates duplicate points and
                # the Fréchet covariance shrinks with ties, so the bootstrap
                # distribution is not centred on the point estimate.
                "bootstrap_ci95": [float(np.percentile(boot_arr, 2.5)),
                                   float(np.percentile(boot_arr, 97.5))],
                "bootstrap_note": "biased: duplicate points shrink the "
                                  "resampled covariance; use the subsample sd",
                # Conservative SE from 30 independent draws at N=1000
                # (matched-N reference, so it includes reference noise).
                "subsample_sd_at_1000": (
                    float([s for s in scan if s["n"] == n_max][0]["delta_pct_sd"])
                    if any(s["n"] == n_max for s in scan) else float("nan")
                ),
                "chunk_delta_pct": float(cd_arr.mean()),
                "chunk_p": p_chunk,
                "scan": scan,
            }
            sd1000 = cell["subsample_sd_at_1000"]
            cell["conservative_ci95"] = [float(headline - 1.96 * sd1000),
                                         float(headline + 1.96 * sd1000)]
            out["cells"].append(cell)

            print(f"[gap73] {label:12s} {arm_name:16s} "
                  f"headline={headline:+6.2f}% "
                  f"CI[{cell['conservative_ci95'][0]:+.2f},"
                  f"{cell['conservative_ci95'][1]:+.2f}] "
                  f"chunk={cd_arr.mean():+6.2f}% (p={p_chunk:.2g}) | "
                  + " ".join(f"N{s['n']}={s['delta_pct_mean']:+.1f}" for s in scan),
                  flush=True)

    if args.out is not None:
        p = args.out if args.out.is_absolute() else _REPO_ROOT / args.out
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, indent=1))
        print(f"[gap73] wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
