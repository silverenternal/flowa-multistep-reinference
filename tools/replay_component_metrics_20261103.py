#!/usr/bin/env python3
"""CPU replay of all 36 metric pairs from published fixed features; no model execution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from adaptive_reflow.eval.mnist_fid import _frechet_distance
from tools.component_study_20261103 import kid_unbiased


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    protocol = json.loads((args.root / "PROTOCOL.json").read_text())
    with np.load(args.root / "w16e1_5k_s42/reference_features.npz") as z:
        ref = z["reference"]
        indices = z["kid_indices"]
    checks = []
    for ck in protocol["checkpoints"]:
        for seed in protocol["seeds"]:
            base = args.root / f"{ck}_s{seed}"
            recorded = json.loads((base / "results.json").read_text())
            with np.load(base / "features_and_preselected_images.npz") as z:
                for arm in protocol["arms"]:
                    fid = float(_frechet_distance(z[arm], ref))
                    kid = kid_unbiased(z[arm], ref[indices])
                    old = recorded["arms"][arm]
                    error = max(abs(fid - old["projection_fid"]), abs(kid - old["projection_kid"]))
                    checks.append(
                        dict(
                            checkpoint=ck, seed=seed, arm=arm, fid=fid, kid=kid, max_abs_error=error
                        )
                    )
                    if error > 1e-6:
                        raise RuntimeError(f"metric replay mismatch: {ck}, {seed}, {arm}")
    args.out.write_text(
        json.dumps(dict(n_metric_pairs=len(checks), n_failures=0, checks=checks), indent=2) + "\n"
    )
    print("PASS: 36 saved-feature FID/KID pairs")


if __name__ == "__main__":
    main()
