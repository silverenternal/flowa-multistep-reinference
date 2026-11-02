#!/usr/bin/env python3
"""Recompute designated full-feature CIFAR scores on CPU; no weights or GPU required."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import scipy

from adaptive_reflow.eval.fid import compute_frechet_distance
from tools.cifar_study_metrics_20261103 import kernel_rows, kernel_score


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repository", type=Path, required=True)
    p.add_argument("--study", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    protocol = json.loads((args.study / "PROTOCOL.json").read_text())
    selection = json.loads((args.study / "REPLAY_SELECTION.json").read_text())
    reference = np.load(args.repository / protocol["reference_path"])["reference"].astype(
        np.float64
    )
    recorded_constant = json.loads(
        (args.repository / protocol["reference_statistics"]).read_text()
    )["reference_self_kernel"]
    constant = float(kernel_rows(reference, reference, self_kernel=True).mean())
    if abs(constant - recorded_constant) > 1e-12:
        raise RuntimeError("reference self-kernel replay mismatch")
    mu, cov = reference.mean(0), np.cov(reference, rowvar=False)
    expected = json.loads((args.study / selection["source_cell"] / "results.json").read_text())[
        "arms"
    ]
    checks = []
    with np.load(args.study / selection["features_file"]) as z:
        for arm in selection["arms"]:
            f = z[arm].astype(np.float64)
            if f.shape != (1000, 2048):
                raise ValueError("wrong feature shape")
            fid = float(
                compute_frechet_distance(
                    mu_s=f.mean(0), sigma_s=np.cov(f, rowvar=False), mu_r=mu, sigma_r=cov
                )
            )
            kid = kernel_score(
                kernel_rows(f, f, self_kernel=True), kernel_rows(f, reference), constant
            )
            fid_error = abs(fid - expected[arm]["fid_tfport"])
            kid_error = abs(kid - expected[arm]["kid_unscaled"])
            if fid_error > 1e-4 or kid_error > 1e-12:
                raise RuntimeError(
                    f"full feature replay mismatch:{arm},FID{fid_error},KID{kid_error}"
                )
            checks.append(
                {
                    "arm": arm,
                    "fid_tfport": fid,
                    "kid_unscaled": kid,
                    "fid_abs_error": fid_error,
                    "kid_abs_error": kid_error,
                }
            )
    args.out.write_text(
        json.dumps(
            {
                "scipy": scipy.__version__,
                "numpy": np.__version__,
                "n_full_feature_pairs": len(checks),
                "reference_kernel_abs_error": abs(constant - recorded_constant),
                "checks": checks,
                "scope": "CPU full-feature metric replay for predetermined designated cell/arms only. All canonical primary scores separately replay from published kernel witnesses.",
            },
            indent=2,
        )
        + "\n"
    )
    print("Full-feature FID/KID replay PASS", len(checks))


if __name__ == "__main__":
    main()
