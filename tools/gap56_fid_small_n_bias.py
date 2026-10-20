"""Calibrate the small-N bias of the FID estimator used by the R5c driver.

The R5c/MNIST FID is the Fréchet distance between an ``n``-sample projected
feature set and the full 10 000-image reference. That estimator is **biased
upward at small n**, and the bias depends on the sample's own covariance, so it
does not cancel between two arms with different covariance spectra.

This tool measures the bias directly on a case whose true value is known:

* ``X ~ N(0, I_d)`` and a 10 000-sample reference from the same distribution
  have a true FID of 0;
* ``Z ~ N(0, 1.3^2 I_d)`` has a known closed-form FID against the reference,
  ``d * (1.3^2 + 1 - 2*1.3) = d * 0.09``.

Two things are reported:

1. ``E[FID_hat]`` at n in {50, 100, 200, 500, 1000, 2000} versus the true value,
   i.e. the bias of the point estimate;
2. the bootstrap bias, ``E[FID*] - FID_hat``, which is what makes a percentile
   bootstrap interval sit below the point estimate.

The second is the reason ``tools/gap56_r5c_paired_bootstrap.py`` reports a
**basic (pivotal)** interval rather than a percentile one.

Usage::

    python3 tools/gap56_fid_small_n_bias.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.gap56_r5c_paired_bootstrap import _fid_from_stats, _stats  # noqa: E402

D = 128
N_REF = 10_000
SIGMA_Z = 1.3


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dim", type=int, default=D)
    ap.add_argument("--n-ref", type=int, default=N_REF)
    ap.add_argument("--reps", type=int, default=10)
    ap.add_argument("--n-boot", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20261020)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    rng = np.random.default_rng(int(args.seed))
    d = int(args.dim)
    ref = rng.standard_normal((int(args.n_ref), d))
    ref_mu, ref_sigma = _stats(ref)
    true_fid_z = float(d * (SIGMA_Z ** 2 + 1.0 - 2.0 * SIGMA_Z))

    print(f"d={d}, reference n={args.n_ref}, reps={args.reps}. "
          f"True FID: X=0, Z={true_fid_z:.4f}.\n")
    print("| n | E[FID_hat X] | bias X | E[FID_hat Z] | bias Z | "
          "E[boot FID* X] | boot bias X | E[delta_hat] | E[delta*] | delta bias |")
    print("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    rows = []
    for n in (50, 100, 200, 500, 1000, 2000):
        fx, fz, bfx, dlt, bdlt = [], [], [], [], []
        for _ in range(int(args.reps)):
            X = rng.standard_normal((n, d))
            Z = rng.standard_normal((n, d)) * SIGMA_Z
            xm, xs = _stats(X)
            zm, zs = _stats(Z)
            fid_x = _fid_from_stats(xm, xs, ref_mu, ref_sigma)
            fid_z = _fid_from_stats(zm, zs, ref_mu, ref_sigma)
            fx.append(fid_x)
            fz.append(fid_z)
            dlt.append(fid_z - fid_x)
            idx = rng.integers(0, n, size=(int(args.n_boot), n))
            bx = np.mean([_fid_from_stats(*_stats(X[i]), ref_mu, ref_sigma) for i in idx])
            bfx.append(float(bx))
            bdlt.append(float(np.mean([
                _fid_from_stats(*_stats(Z[i]), ref_mu, ref_sigma)
                - _fid_from_stats(*_stats(X[i]), ref_mu, ref_sigma)
                for i in idx
            ])))
        row = {
            "n": n,
            "fid_x_mean": float(np.mean(fx)),
            "fid_x_bias": float(np.mean(fx)),
            "fid_z_mean": float(np.mean(fz)),
            "fid_z_bias": float(np.mean(fz) - true_fid_z),
            "boot_fid_x_mean": float(np.mean(bfx)),
            "boot_fid_x_bias": float(np.mean(bfx) - np.mean(fx)),
            "delta_mean": float(np.mean(dlt)),
            "delta_boot_mean": float(np.mean(bdlt)),
            "delta_boot_bias": float(np.mean(bdlt) - np.mean(dlt)),
        }
        rows.append(row)
        print(f"| {n} | {row['fid_x_mean']:.3f} | {row['fid_x_bias']:+.3f} | "
              f"{row['fid_z_mean']:.3f} | {row['fid_z_bias']:+.3f} | "
              f"{row['boot_fid_x_mean']:.3f} | {row['boot_fid_x_bias']:+.3f} | "
              f"{row['delta_mean']:.3f} | {row['delta_boot_mean']:.3f} | "
              f"{row['delta_boot_bias']:+.3f} |")

    print("\nReading: the point estimate is upward-biased and the bias falls with n, "
          "so a small-n delta is not transferable across n. The bootstrap adds a "
          "second upward shift, which is why the reported interval is basic "
          "(pivotal), not percentile.")

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({
            "dim": d, "n_ref": int(args.n_ref), "reps": int(args.reps),
            "n_boot": int(args.n_boot), "seed": int(args.seed),
            "sigma_z": SIGMA_Z, "true_fid_x": 0.0, "true_fid_z": true_fid_z,
            "rows": rows,
        }, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
