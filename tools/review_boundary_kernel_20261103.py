#!/usr/bin/env python3
"""Closed-form Gaussian checks for boundary re-noising; no sampled or learned evidence."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def gaussian_coefficients(
    target_variance: float,
    memory: float,
    *,
    coupling: str = "independent",
    restart_at_zero: bool = False,
) -> tuple[float, float]:
    if (
        not math.isfinite(target_variance)
        or target_variance <= 0
        or not math.isfinite(memory)
        or not 0 < memory < 1
    ):
        raise ValueError(
            "positive finite variance and memory strictly between zero and one required"
        )
    sd = math.sqrt(target_variance)
    if coupling == "independent":
        denominator = math.sqrt(memory * memory * target_variance + (1 - memory) ** 2)
    elif coupling == "deterministic":
        denominator = 1 - memory + memory * sd
    else:
        raise ValueError("unknown training coupling")
    scale = sd if restart_at_zero else sd / denominator
    return memory * scale, (1 - memory) * scale


def variance_after(variance: float, a: float, b: float) -> float:
    return a * a * variance + b * b


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    rows = []
    for variance in [0.25, 1.0, 4.0]:
        for memory in [0.2, 0.5, 0.8, 0.7 ** (1 / 3)]:
            a, b = gaussian_coefficients(variance, memory)
            v = variance_after(variance, a, b)
            assert math.isclose(v, variance, rel_tol=1e-12) and a < 1
            az, bz = gaussian_coefficients(variance, memory, restart_at_zero=True)
            ac, bc = gaussian_coefficients(variance, memory, coupling="deterministic")
            rows.append(
                dict(
                    target_variance=variance,
                    memory=memory,
                    independent_matched=dict(a=a, b=b, variance_after=v),
                    independent_zero_time=dict(
                        a=az, b=bz, variance_after=variance_after(variance, az, bz)
                    ),
                    deterministic_coupling_matched_time=dict(
                        a=ac, b=bc, variance_after=variance_after(variance, ac, bc)
                    ),
                )
            )
    args.out.write_text(
        json.dumps(
            {
                "scope": "algebraic Gaussian identities/counterexamples only; finite parameter checks are not a proof and not new learned-model experimental evidence",
                "rows": rows,
                "zero_field_counterexample": {
                    "source_equals_target": "N(0,I)",
                    "training_coupling": "Y=Z",
                    "exact_velocity": "zero at all times",
                    "baseline_error": 0,
                    "memory": 0.8,
                    "one_step_variance": 0.8**2 + 0.2**2,
                    "stationary_variance": (1 - 0.8) / (1 + 0.8),
                    "state_contraction": 0.8,
                    "mean_preservation": "does not restore the shrunken covariance",
                },
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
