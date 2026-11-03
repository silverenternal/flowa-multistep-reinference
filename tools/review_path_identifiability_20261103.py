"""Bounded CPU controls for endpoint-indistinguishable, different marginal paths."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import platform
import time
from pathlib import Path

import numpy as np
import scipy
from scipy.integrate import solve_ivp
from scipy.optimize import linear_sum_assignment


def parameters(m: float, sigma: float, rho: float) -> tuple[float, float]:
    if not (0 < m < 1 and sigma > 0 and -1 <= rho <= 1):
        raise ValueError("Interior time, positive output scale and valid correlation required")
    variance = m * m + (1 - m) ** 2 + 2 * m * (1 - m) * rho
    if variance <= 0:
        raise ValueError("Nondegenerate refreshed Gaussian required")
    radius = math.sqrt(variance) / sigma
    return variance, math.log(radius) / math.sin(math.pi * m)


def flow(t: float, amplitude: float, rotation: float) -> np.ndarray:
    phase = math.sin(math.pi * t)
    angle = rotation * phase
    matrix = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    return math.exp(amplitude * phase) * matrix


def integrate(start: float, stop: float, amplitude: float, rotation: float) -> np.ndarray:
    generator = np.array([[0.0, -1.0], [1.0, 0.0]])

    def rhs(t: float, state: np.ndarray) -> np.ndarray:
        multiplier = math.pi * math.cos(math.pi * t)
        velocity = multiplier * (amplitude * np.eye(2) + rotation * generator)
        return (velocity @ state.reshape(2, 2)).ravel()

    result = solve_ivp(
        rhs, (start, stop), np.eye(2).ravel(), method="DOP853", rtol=1e-11, atol=1e-12
    )
    if not result.success:
        raise RuntimeError(result.message)
    return result.y[:, -1].reshape(2, 2)


def gaussian_w2_to_identity(covariance: np.ndarray) -> float:
    eigenvalues = np.linalg.eigvalsh(covariance)
    if np.any(eigenvalues < 0):
        raise ValueError("Positive semidefinite covariance required")
    return float(np.linalg.norm(np.sqrt(eigenvalues) - 1))


def case(m: float, sigma: float, rotation: float, rho: float) -> dict:
    variance, amplitude = parameters(m, sigma, rho)
    mid = flow(m, amplitude, rotation)
    after = np.linalg.inv(mid)
    full_numeric = integrate(0, 1, amplitude, rotation)
    after_numeric = integrate(m, 1, amplitude, rotation)
    out_cov = variance * after @ after.T
    numeric_cov = variance * after_numeric @ after_numeric.T
    q = math.exp(amplitude * math.sin(math.pi * m))
    intermediate_distance = math.sqrt(2) * abs(math.sqrt(variance) - q)
    output_distance = gaussian_w2_to_identity(out_cov)
    # This diagonal assignment test sees exactly the same endpoints in every case.
    source = np.array([[-1.0, 0.0], [0.0, -2.0], [1.0, 0.0], [0.0, 2.0], [0.3, 0.4]])
    endpoint = source @ flow(1, amplitude, rotation).T
    costs = np.square(endpoint[:, None, :] - source[None, :, :]).sum(axis=2) / 2
    row_index, column_index = linear_sum_assignment(costs)
    gain = float(np.trace(costs) - costs[row_index, column_index].sum()) / len(source)
    endpoint_error = float(np.max(np.abs(full_numeric - np.eye(2))))
    continuation_error = float(np.max(np.abs(after_numeric - after)))
    covariance_error = float(np.max(np.abs(numeric_cov - sigma**2 * np.eye(2))))
    distance_error = abs(output_distance - intermediate_distance / q)
    row = dict(
        m=m,
        sigma=sigma,
        rotation=rotation,
        rho=rho,
        amplitude=amplitude,
        refresh_variance=variance,
        true_midpoint_scale=q,
        endpoint_assignment_gain=gain,
        output_variance=float(np.trace(out_cov) / 2),
        intermediate_W2=intermediate_distance,
        output_W2=output_distance,
        endpoint_numeric_error=endpoint_error,
        continuation_numeric_error=continuation_error,
        covariance_numeric_error=covariance_error,
        W2_relation_error=distance_error,
        outcome="preserve" if sigma == 1 else "shrink" if sigma < 1 else "expand",
    )
    row["passed"] = (
        endpoint_error < 1e-8
        and continuation_error < 1e-8
        and covariance_error < 1e-8
        and distance_error < 1e-10
        and abs(gain) < 1e-12
    )
    return row


def run(max_records: int, wall_seconds: float) -> dict:
    if max_records != 36 or wall_seconds <= 0:
        raise ValueError("Locked protocol requires36 records and positive CPU wall cap")
    start = time.monotonic()
    rows = []
    for values in itertools.product([0.2, 0.5, 0.8], [0.5, 1.0, 2.0], [0.0, 0.7], [0.0, 0.7]):
        if time.monotonic() - start > wall_seconds:
            raise TimeoutError("Incomplete sweep cannot be reported as complete")
        rows.append(case(*values))
    return dict(
        planned=36,
        processed=len(rows),
        skipped=0,
        passed=all(row["passed"] for row in rows),
        rows=rows,
        CPU_wall_seconds=time.monotonic() - start,
        GPU_added_seconds=0,
        environment=dict(
            python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__
        ),
        scope="Exact Gaussian controls with independent ODE integration; no model training, images, novelty certification or causal attribution to CIFAR",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-records", type=int, required=True)
    parser.add_argument("--wall-seconds", type=float, required=True)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    result = run(args.max_records, args.wall_seconds)
    result["seed"] = args.seed
    result["seed_scope"] = (
        "Protocol identifier; all computations deterministic, no Monte Carlo samples"
    )
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "RESULTS.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}))
    if not result["passed"] or result["processed"] != result["planned"]:
        raise SystemExit(1)
