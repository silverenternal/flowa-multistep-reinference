#!/usr/bin/env python3
"""Exact Gaussian coupling sensitivity; analytic diagnostics, no GPU or fitted model."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def coupling_diagnostic(target_sd: float, memory: float, correlation: float) -> dict:
    if not (math.isfinite(target_sd) and target_sd > 0 and 0 < memory < 1 and -1 <= correlation <= 1):
        raise ValueError('positive finite target sd, interior memory and valid correlation required')
    m, s, rho = memory, target_sd, correlation
    variance_path = (m*s)**2 + (1-m)**2 + 2*m*(1-m)*rho*s
    if variance_path <= 1e-14:
        raise ValueError('degenerate intermediate marginal has no invertible scalar flow')
    scale = s / math.sqrt(variance_path)
    naive_target_variance_ratio = ((m*s)**2 + (1-m)**2) / variance_path
    coefficient = scale*(m+(1-m)*rho/s)
    innovation = scale*(1-m)*math.sqrt(max(0., 1-rho*rho))
    conditional_variance = coefficient**2*s*s + innovation**2
    return {
        'target_sd': s, 'memory': m, 'training_correlation': rho,
        'path_variance': variance_path,
        'independent_refresh_target_variance_ratio': naive_target_variance_ratio,
        'conditional_refresh_state_coefficient': coefficient,
        'conditional_refresh_noise_coefficient': innovation,
        'conditional_refresh_target_variance': conditional_variance,
        'scope': 'conditional refresh uses the true Gaussian training conditional Z|Y, not available from an arbitrary velocity field',
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    rows = [coupling_diagnostic(s, m, rho) for s in [.5, 1., 2.] for m in [.2, .5, .8] for rho in [-.5, 0., .5, 1.]]
    for row in rows:
        assert math.isclose(row['conditional_refresh_target_variance'], row['target_sd']**2, rel_tol=1e-12)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        'scope': '36 exact scalar Gaussian parameter checks; not learned-model validation, a novelty claim, or a generic deployable repair',
        'rows': rows,
        'interpretation': 'Independent refreshing shrinks target variance for positive training correlation and expands it for negative correlation. True conditional refreshing preserves the target; at rho=1 it becomes deterministic identity and provides no new randomness.'
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
