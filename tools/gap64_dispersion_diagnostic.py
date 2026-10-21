"""GAP-64c: dispersion diagnostic for the R5c restart blend.

Why this exists
---------------
The R5c (MNIST-FM projection-FID) cell regresses under every recorded
framework configuration (``tools/gap64_r5c_census.py``: 35 configs, +4.2% to
+39.9%). The NFE ladder (``tools/gap64_nfe_headroom.py``) shows the cell has
no integration headroom at all: the single-pass baseline FID is flat from
NFE=3 to NFE=100. So the regression cannot be "the framework fails to fix
integration error" -- there is none to fix.

This tool tests the alternative mechanism: the restart blend

    x_{t=m} = m * x1_hat + (1 - m) * x0,     m = 1 - beta

is a **variance-shrinkage operator** on the model's output distribution. It
reduces total sample dispersion. That is helpful exactly when the base model
is over-dispersed relative to the data, and harmful when it is already
under-dispersed.

Diagnostic
----------
For each (checkpoint, arm) we project the saved samples through the same
128-dim random projection the FID uses and report

    rho = tr(Sigma_generated) / tr(Sigma_reference)

i.e. the total variance ratio. ``rho < 1`` = under-dispersed (shrinkage
costs fidelity); ``rho >= 1`` = at-or-above the data dispersion (shrinkage
can pay).

This reads only recorded ``*_samples.npz`` artifacts -- no GPU, no sampling.
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

from adaptive_reflow.eval.mnist_fid import MnistFrechetProjectionEvaluator  # noqa: E402

ARMS = ("baseline", "cosine", "codimension_sheet", "evidence_driven")


def _load_samples(path: Path) -> np.ndarray:
    with np.load(path) as z:
        key = "samples" if "samples" in z.files else z.files[0]
        return np.asarray(z[key], dtype=np.float64)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", nargs="+", required=True,
                    help="RUN_DIR:LABEL pairs, e.g. "
                         "verification_outputs/.../production_s42:production")
    ap.add_argument("--cache-dir", type=Path,
                    default=_REPO_ROOT / "data" / "mnist_fm_train_cache")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    ev = MnistFrechetProjectionEvaluator(cache_dir=Path(args.cache_dir))
    projection = ev._projection
    ref = ev._ref_features
    mu_ref = ref.mean(0)
    tr_ref = float(np.trace(np.cov(ref, rowvar=False)))

    rows: list[dict] = []
    for spec in args.runs:
        run_s, _, label = spec.rpartition(":")
        run = Path(run_s)
        for arm in ARMS:
            p = run / f"{arm}_samples.npz"
            if not p.exists():
                continue
            feats = _load_samples(p) @ projection
            tr_gen = float(np.trace(np.cov(feats, rowvar=False)))
            rho = tr_gen / tr_ref
            rows.append({
                "label": label, "arm": arm, "rho": rho,
                "mean_shift": float(np.linalg.norm(feats.mean(0) - mu_ref)),
                "n": int(feats.shape[0]),
            })

    print("| ckpt | arm | rho = tr(S_g)/tr(S_ref) | mean shift |")
    print("|---|---|---:|---:|")
    for r in rows:
        print(f"| {r['label']} | {r['arm']} | {r['rho']:.4f} | {r['mean_shift']:.4f} |")

    print()
    print("Sign rule: shrinkage is predicted to *help* FID iff the **baseline**")
    print("rho >= 1 (the model's samples are at least as dispersed as the data).")
    print()
    print("| ckpt | rho_baseline | predicted |")
    print("|---|---:|:--:|")
    for r in rows:
        if r["arm"] == "baseline":
            print(f"| {r['label']} | {r['rho']:.4f} | "
                  f"{'shrink helps' if r['rho'] >= 1.0 else 'shrink hurts'} |")

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({
            "tr_reference": tr_ref,
            "rows": rows,
        }, indent=1))
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
