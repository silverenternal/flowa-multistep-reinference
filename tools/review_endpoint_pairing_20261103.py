#!/usr/bin/env python3
"""CPU finite-coupling audit of stored endpoints; not a new sampling method."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment


def pairing(z: np.ndarray, x: np.ndarray) -> tuple[dict, np.ndarray]:
    z, x = np.asarray(z, dtype=np.float64), np.asarray(x, dtype=np.float64)
    if z.shape != x.shape or z.ndim != 2 or len(z) < 2:
        raise ValueError('Two equally shaped finite sample matrices required')
    if not np.isfinite(z).all() or not np.isfinite(x).all():
        raise ValueError('Nonfinite samples')
    n, d = z.shape
    cost = ((x*x).sum(1)[:, None] + (z*z).sum(1)[None, :] - 2*x@z.T)/d
    row, col = linear_sum_assignment(cost)
    identity, optimal = float(np.trace(cost)/n), float(cost[row, col].mean())
    zz = (z*z).sum(1)
    denom = zz[:, None]+zz[None, :]-2*z@z.T
    zx = z@x.T
    numerator = np.diag(zx)[:, None]+np.diag(zx)[None, :]-zx-zx.T
    mask = np.triu(np.ones((n, n), dtype=bool), 1) & (denom > 1e-12)
    # Independent expansion of chord moments checks the sign convention.
    chord = .5*x+.5*z
    refreshed = .5*x+.5*z[col]
    moment_deficit = float(((chord*chord).sum()-(refreshed*refreshed).sum())/n/d)
    expected = .25*(optimal-identity)
    return {'n': n, 'dimension': d, 'identity_cost': identity, 'optimal_cost': optimal,
            'cost_improvement': identity-optimal, 'moved_records': int(np.sum(col != row)),
            'min_pair_ratio': float((numerator[mask]/denom[mask]).min()),
            'convex_gradient_necessary_condition_rejected': identity-optimal > 1e-10,
            'chord_moment_deficit': moment_deficit, 'identity_error': abs(moment_deficit-expected),
            'assignment': col.tolist()}, cost


def controls() -> list[dict]:
    z = np.array([[1.,0.],[0.,1.],[-1.,0.],[0.,-1.]])
    maps = [('SPD', np.diag([.5,2.]), False),
            ('non_gradient_rotation', np.array([[1.,-3.],[3.,1.]]), True)]
    result = []
    for name, matrix, rejected in maps:
        row, _ = pairing(z, z@matrix.T)
        assert row['convex_gradient_necessary_condition_rejected'] == rejected
        if name == 'non_gradient_rotation':
            assert row['min_pair_ratio'] > 0  # Pairwise monotonicity alone misses this.
        result.append({'name': name, **row})
    row, _ = pairing(z, np.roll(z, 1, axis=0))
    assert row['convex_gradient_necessary_condition_rejected']
    result.append({'name': 'permuted_endpoint', **row})
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--max-records', type=int, required=True)
    p.add_argument('--wall-seconds', type=float, required=True)
    args = p.parse_args()
    if args.max_records != 12:
        raise ValueError('Locked12 cells required')
    tick = time.monotonic()
    control_rows = controls()
    rows, matrices = [], {}
    for seed in [42,43,44]:
        initial = np.random.default_rng(seed).standard_normal((1000,3,32,32)).astype(np.float32)
        z = initial[:256].reshape(256,-1)
        for cost in [25,49,99,199]:
            source = args.root/f's{seed}_c{cost}'/'raw_samples.npz'
            with np.load(source) as archive:
                x = archive['baseline_euler'][:256].reshape(256,-1)
            row, matrix = pairing(z, x)
            row.update(seed=seed, cost=cost, source=str(source),
                       source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
            rows.append(row)
            matrices[f's{seed}_c{cost}'] = matrix
            if time.monotonic()-tick > args.wall_seconds:
                raise TimeoutError('CPU cap exceeded; no completion claim')
    args.out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.out/'cost_matrices.npz', **matrices)
    result = {'scope': 'Exploratory finite endpoint pairing; not training coupling, intermediate marginal, population prior kernel, exact neural flow or quality evidence',
              'processed': len(rows), 'skipped': 0, 'planned': 12,
              'wall_seconds': time.monotonic()-tick, 'rows': rows, 'controls': control_rows}
    assert len(rows)==12 and all(r['identity_error'] < 1e-10 for r in rows)
    (args.out/'RESULTS.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'processed':len(rows), 'rejected':sum(r['convex_gradient_necessary_condition_rejected'] for r in rows),
                      'wall_seconds':result['wall_seconds'],'max_identity_error':max(r['identity_error'] for r in rows)}))


if __name__ == '__main__':
    main()
