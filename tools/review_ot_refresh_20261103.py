#!/usr/bin/env python3
"""Exact CPU diagnostics for fixed-endpoint refresh on convex-gradient paths.

This is an analytic research diagnostic, not a learned-model sampler or a
novelty certificate. See the linked audit for assumptions and proof.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import time
from pathlib import Path

import numpy as np
from scipy.optimize import brentq, linprog


def finite_w2(x: np.ndarray, p: np.ndarray, y: np.ndarray, q: np.ndarray) -> float:
    """Solve the finite Kantorovich problem independently of the moment bound."""
    n, m = len(p), len(q)
    cost = ((x[:, None, :] - y[None, :, :]) ** 2).sum(axis=2)
    constraints = np.vstack([
        np.kron(np.eye(n), np.ones((1, m))),
        np.kron(np.ones((1, n)), np.eye(m)),
    ])
    result = linprog(cost.ravel(), A_eq=constraints, b_eq=np.r_[p, q],
                     bounds=(0, None), method='highs')
    if not result.success:
        raise RuntimeError(result.message)
    return math.sqrt(max(0.0, float(result.fun)))


def validate_joint(p: np.ndarray, kernel: np.ndarray) -> None:
    if (not np.isfinite(kernel).all() or np.any(kernel < 0)
            or not np.isclose(p.sum(), 1.0) or np.any(p <= 0)
            or not np.allclose(kernel.sum(axis=1), 1, atol=1e-12, rtol=0)
            or not np.allclose(p @ kernel, p, atol=1e-12, rtol=0)):
        raise ValueError('A stochastic kernel preserving the positive prior mass is required')


def nonlinear_case(alpha: float, quartic: float, t: float, kind: str) -> dict:
    if not (alpha > 0 and quartic >= 0 and 0 < t < 1):
        raise ValueError('Strong convexity and an interior path time are required')
    z = np.array([[-1.2, .2], [.1, -.7], [1.1, .4], [.3, 1.3], [-.4, -.1]])
    p = np.full(len(z), 1 / len(z))
    kernels = {'identity': np.eye(len(z)), 'independent': np.tile(p, (len(z), 1)),
               'cyclic': np.roll(np.eye(len(z)), 1, axis=1)}
    kernel = kernels[kind]
    validate_joint(p, kernel)
    i, j = np.nonzero(kernel)
    mass = (p[:, None] * kernel)[i, j]
    target = alpha * z + quartic * z**3
    def potential(a: np.ndarray) -> np.ndarray:
        return (alpha * a**2 / 2 + quartic * a**4 / 4).sum(axis=-1)
    path = (1 - t) * z + t * target
    mixed = t * target[i] + (1 - t) * z[j]
    delta = z[j] - z[i]
    energy = float(np.dot(mass, (delta**2).sum(axis=1)))
    bregman = potential(z[j]) - potential(z[i]) - (target[i] * delta).sum(axis=1)
    defect = float(2 * t * (1 - t) * np.dot(mass, bregman))
    center = p @ path
    radius2 = float(np.dot(p, ((path - center)**2).sum(axis=1)))
    refreshed_radius2 = float(np.dot(mass, ((mixed - center)**2).sum(axis=1)))
    # Invert A_t coordinate-wise using a monotone cubic, not the Bregman identity.
    recovered = np.empty_like(mixed)
    for index, value in np.ndenumerate(mixed):
        bound = max(1.0, abs(value) / ((1 - t) + t * alpha) + 1)
        recovered[index] = brentq(
            lambda a, value=value: ((1 - t) + t * alpha) * a + t * quartic * a**3 - value,
            -bound, bound, xtol=1e-14)
    output = alpha * recovered + quartic * recovered**3
    lower = (math.sqrt(radius2) - math.sqrt(max(0, radius2 - defect))) / (t + (1 - t) / alpha)
    actual = finite_w2(output, mass, target, p)
    row = {'family': 'nonlinear_finite', 'alpha': alpha, 'quartic': quartic,
           't': t, 'kernel': kind, 'refresh_energy': energy, 'bregman_deficit': defect,
           'identity_error': abs(radius2 - refreshed_radius2 - defect),
           'energy_bound_slack': defect - alpha * t * (1 - t) * energy,
           'w2_lower': lower, 'w2_exact': actual, 'w2_slack': actual - lower}
    row['passed'] = (row['identity_error'] < 1e-9 and row['energy_bound_slack'] >= -1e-9
                     and row['w2_slack'] >= -1e-9
                     and (defect > 0 if kind != 'identity' else abs(defect) < 1e-12))
    return row


def isotropic_case(scale: float, t: float, rho: float) -> dict:
    a = 1 - t + t * scale
    radius2 = a * a  # d=1
    refreshed = (t * scale)**2 + (1 - t)**2 + 2*t*scale*(1-t)*rho
    defect = 2*t*(1-t)*scale*(1-rho)
    lower = (math.sqrt(radius2) - math.sqrt(refreshed)) / (t + (1-t)/scale)
    exact = abs(scale - scale/a * math.sqrt(refreshed))
    error = abs(lower - exact)
    return {'family': 'isotropic_gaussian', 'scale': scale, 't': t, 'rho': rho,
            'bregman_deficit': defect, 'identity_error': abs(radius2-refreshed-defect),
            'w2_lower': lower, 'w2_exact': exact, 'sharpness_error': error,
            'passed': error < 1e-10 and abs(radius2-refreshed-defect) < 1e-10}


def spd_case(b: np.ndarray, t: float, label: str) -> dict:
    if not np.allclose(b, b.T) or np.min(np.linalg.eigvalsh(b)) <= 0:
        raise ValueError('Symmetric positive definite transport required')
    rotation = np.array([[0., -1.], [1., 0.]])
    ident = np.eye(2)
    a = (1-t)*ident + t*b
    f = b @ np.linalg.inv(a)
    out_map = f @ (t*b + (1-t)*rotation)
    target_cov = b @ b.T
    out_cov = out_map @ out_map.T
    h = np.linalg.matrix_power(b, 3) @ np.linalg.matrix_power(np.linalg.inv(a), 2)
    delta = rotation-ident
    predicted = float(t*(1-t)*np.trace(h @ delta @ delta.T))
    observed = float(np.trace(target_cov-out_cov))
    eigen = np.linalg.eigvalsh(out_cov-target_cov)
    return {'family': 'anisotropic_gaussian', 'matrix': label, 't': t,
            'predicted_trace_deficit': predicted, 'observed_trace_deficit': observed,
            'identity_error': abs(predicted-observed),
            'max_covariance_difference_eigenvalue': float(eigen[-1]),
            'passed': abs(predicted-observed) < 1e-9 and observed > 0}


def run(max_records: int, wall_seconds: float) -> dict:
    if max_records != 73 or wall_seconds <= 0:
        raise ValueError('Locked protocol requires exactly73 records and a positive wall cap')
    start = time.monotonic()
    rows = []
    def append(row: dict) -> None:
        if time.monotonic()-start > wall_seconds:
            raise TimeoutError('CPU wall cap exceeded; no complete-result claim allowed')
        rows.append(row)
    for alpha in [.5, 1.5]:
        for quartic in [.1, .5]:
            for t in [.2, .5, .8]:
                for kind in ['identity', 'independent', 'cyclic']:
                    append(nonlinear_case(alpha, quartic, t, kind))
    for scale in [.5, 1., 2.]:
        for t in [.2, .5, .8]:
            for rho in [0., .5, .9]:
                append(isotropic_case(scale, t, rho))
    angle = .37
    rotation = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    for label, b in [('diag_0.5_2', np.diag([.5, 2.])), ('diag_1_3', np.diag([1., 3.])),
                     ('rotated_0.4_1.7', rotation @ np.diag([.4, 1.7]) @ rotation.T)]:
        for t in [.2, .5, .8]:
            append(spd_case(b, t, label))
    # Outside convex-gradient assumptions: T=-I, t=.25, exact F=-2I.
    variance = (-2)**2 * (.25**2 + .75**2)
    append({'family': 'outside_assumption', 't': .25, 'output_variance': variance,
            'target_variance': 1., 'passed': variance == 2.5})
    return {'scope': 'Exact CPU theory checks; not model experiments or proof of novelty',
            'planned': 73, 'processed': len(rows), 'skipped': 0,
            'passed': all(r['passed'] for r in rows), 'rows': rows,
            'wall_seconds': time.monotonic()-start,
            'environment': {'python': platform.python_version(), 'numpy': np.__version__,
                            'platform': platform.platform()}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--max-records', type=int, required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--wall-seconds', type=float, required=True)
    args = parser.parse_args()
    result = run(args.max_records, args.wall_seconds)
    result['seed'] = args.seed
    result['seed_scope'] = 'Recorded for protocol compatibility; no random sampling is performed'
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir/'results.json').write_text(json.dumps(result, indent=2)+'\n')
    fields = sorted(set().union(*(r.keys() for r in result['rows'])))
    with (args.output_dir/'results.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(result['rows'])
    print(json.dumps({k: v for k, v in result.items() if k not in ['rows', 'environment']}))
    if not result['passed'] or result['processed'] != result['planned']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
