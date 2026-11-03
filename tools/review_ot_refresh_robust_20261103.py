#!/usr/bin/env python3
"""CPU scope stress test of approximate gradient-transport refresh bounds."""
from __future__ import annotations

import argparse
import csv
import json
import math
import time
from pathlib import Path

import numpy as np


def robust_case(eta: float, angle: float, t: float) -> dict:
    j = np.array([[0., -1.], [1., 0.]])
    ident = np.eye(2)
    s = ident + eta*j
    q = math.cos(angle)*ident + math.sin(angle)*j
    a = (1-t)*ident + t*s
    mixed = t*s + (1-t)*q
    actual = float(np.trace(a@a.T - mixed@mixed.T))
    energy = float(np.sum((q-ident)**2))
    epsilon = math.sqrt(2)*abs(eta)
    analytic = 4*t*(1-t)*(1-math.cos(angle)-eta*math.sin(angle))
    lower = t*(1-t)*(energy-2*epsilon*math.sqrt(energy))
    output_map = s@np.linalg.inv(a)@mixed
    target_var = float(np.trace(s@s.T))
    output_var = float(np.trace(output_map@output_map.T))
    return {'eta': eta, 'angle': angle, 't': t, 'refresh_energy': energy,
            'endpoint_error_l2': epsilon, 'path_moment_deficit': actual,
            'analytic_deficit': analytic, 'robust_lower': lower,
            'identity_error': abs(actual-analytic), 'bound_slack': actual-lower,
            'target_trace': target_var, 'output_trace': output_var,
            'target_minus_output_trace': target_var-output_var,
            'passed': abs(actual-analytic) < 1e-10 and actual-lower >= -1e-10}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--max-records', type=int, required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--wall-seconds', type=float, required=True)
    args = parser.parse_args()
    if args.max_records != 27 or args.wall_seconds <= 0:
        raise ValueError('Locked27-case protocol and a positive wall cap required')
    start = time.monotonic()
    rows = [robust_case(eta, angle, t) for eta in [.05, .2, .5]
            for angle in [.05, .5, 1.5] for t in [.2, .5, .8]]
    result = {'scope': __doc__, 'seed': args.seed, 'seed_scope': 'No Monte Carlo',
              'planned': 27, 'processed': len(rows), 'skipped': 0, 'rows': rows,
              'passed': all(r['passed'] for r in rows), 'wall_seconds': time.monotonic()-start}
    if result['wall_seconds'] > args.wall_seconds:
        raise TimeoutError('CPU wall cap exceeded')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir/'results.json').write_text(json.dumps(result, indent=2)+'\n')
    with (args.output_dir/'results.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
