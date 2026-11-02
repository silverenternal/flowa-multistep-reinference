#!/usr/bin/env python3
"""Exploratory cross-batch generated-kernel estimate, avoiding within-batch iid assumptions."""

from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path

import numpy as np

from tools.cifar_study_metrics_20261103 import kernel_rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if not json.loads((args.root / "RUN_LEDGER.json").read_text()).get("complete"):
        raise ValueError("all canonical jobs must finish first")
    protocol = json.loads((args.root / "PROTOCOL.json").read_text())
    reference_self = json.loads((args.root / "REFERENCE_STATISTICS.json").read_text())[
        "reference_self_kernel"
    ]
    rows = []
    for cost in protocol["cost_grid"]:
        features = []
        xy = []
        within = []
        for seed in protocol["seeds"]:
            cell = args.root / f"s{seed}_c{cost}"
            with np.load(cell / "features.npz") as z:
                features.append({arm: z[arm].astype(np.float64) for arm in protocol["arms"]})
            with np.load(cell / "kid_witness.npz") as z:
                xy.append({arm: float(z[f"{arm}_xy"].mean()) for arm in protocol["arms"]})
                within.append({arm: float(z[f"{arm}_xx"].mean()) for arm in protocol["arms"]})
        for arm in protocol["arms"]:
            pairs = [
                {
                    "seeds": [protocol["seeds"][i], protocol["seeds"][j]],
                    "mean_kernel": float(kernel_rows(features[i][arm], features[j][arm]).mean()),
                }
                for i, j in combinations(range(3), 2)
            ]
            generated_self = float(np.mean([x["mean_kernel"] for x in pairs]))
            crossref = float(np.mean([x[arm] for x in xy]))
            within_self = float(np.mean([x[arm] for x in within]))
            rows.append(
                {
                    "cost": cost,
                    "arm": arm,
                    "cross_batch_pairs": pairs,
                    "cross_batch_kid": generated_self + reference_self - 2 * crossref,
                    "mean_primary_within_batch_kid": within_self + reference_self - 2 * crossref,
                    "cross_minus_within_self_term": generated_self - within_self,
                }
            )
    args.out.write_text(
        json.dumps(
            {
                "status": "EXPLORATORY",
                "scope": "Three independent generated batches; cross-batch self-kernel estimates the product of the per-output marginal even when centroid processing couples samples within a batch. Same fixed empirical reference, only3 batches; no added tests/CIs or replacement of registered primary scores.",
                "rows": rows,
            },
            indent=2,
        )
        + "\n"
    )
    print("20 cross-batch diagnostic rows; no new p-values")


if __name__ == "__main__":
    main()
