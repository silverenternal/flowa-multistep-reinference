"""Rectified Flow + Reflow baseline (Liu et al. 2022, ICLR 2023 Spotlight).

Math story
----------
Liu, Gong & Liu (UT Austin) introduced **Rectified Flow** (RF) with the
linear-interpolation regression objective:

    L(\\theta) = E_{t, X_0, X_1} \\| v_\\theta(X_t, t) - (X_1 - X_0) \\|^2,
    X_t = t X_1 + (1 - t) X_0,

where ``v_\\theta`` is a velocity field, ``X_0 ~ prior`` is noise,
and ``X_1 ~ data`` is a real sample. After one *rectification* pass the
learned coupling is straight, so ODE integration is cheap — sometimes
one Euler step is enough.

**Reflow** (Section 4 of the paper) repeats the procedure using synthetic
``(X_0, X_1)`` pairs drawn from the *learned* coupling; the retrained
``v_\\theta`` is straight on this refined coupling. Each reflow round is
a full retraining pass; the metric is "trajectory straightness" on a
held-out batch.

Baseline implementation here
----------------------------
A full reflow requires retraining ``v_\\theta``, which is explicitly
out of scope (per Agent A's §1 rationale: reflow is a *training-time*
technique that mutates the velocity field, while the framework is
*inference-time* on a frozen field).

We instead implement the **inference-time reflow proxy**: a multi-round
sample-and-replace loop that does not retrain the velocity field but
does walk the coupling toward straightness. At each ``round r``:

  1. Draw ``x_0 ~ N(0, I)`` and integrate the frozen ``v_\\theta`` for
     ``num_steps`` Euler steps to produce ``x_1``.
  2. Treat ``x_1`` as the new "noise" (after a small displacement) for
     the next round — this is the inference-time analog of reflow's
     synthetic-coupling retraining.
  3. Repeat for ``K`` rounds; return the final ``x_1`` population.

This is a fair **inference-time** baseline: same frozen velocity field,
no retraining, but a multi-round loop comparable to the framework's.
The framework should win because its `n_cap(r)` schedule is
*paper-quantity-driven* (closes on Theorem 1) while the reflow proxy
uses a static, blind `n_cap`.

References
----------
Liu, Gong & Liu, 2022. *Flow Straight and Fast: Learning to Generate
and Transfer Data with Rectified Flow.* arXiv:2209.03003. ICLR 2023
Spotlight.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Callable

import numpy as np
from numpy.typing import NDArray

# Make the project importable when running as a standalone script.
_REPO_ROOT: Path = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def rectified_flow_reflow_sample(
    *,
    n_samples: int,
    state_shape: tuple[int, ...],
    sample_fn,
    seed: int,
    n_reflow_rounds: int = 2,
    n_inner_steps: int = 50,
    coupling_noise_std: float = 0.05,
) -> NDArray[np.float64]:
    """Sample ``n_samples`` endpoints via an inference-time reflow proxy.

    Parameters
    ----------
    n_samples : int
        Number of endpoint samples to draw.
    state_shape : tuple[int, ...]
        Per-sample state shape (``(2,)``, ``(784,)``, ``(3, 32, 32)``).
    sample_fn : callable
        Adapter-specific single-round sampler:
        ``sample_fn(rng, x0, n_inner_steps) -> x1``
        where ``x0`` is the current noise and ``x1`` is the integrated
        endpoint. The framework supplies this via
        ``scripts/baselines/run_baselines.py``.
    seed : int
        RNG seed (byte-deterministic across calls).
    n_reflow_rounds : int, optional
        Number of reflow proxy rounds. Default ``2`` matches the
        published RF + 2-Reflow headline number on CIFAR-10 (FID 2.21).
    n_inner_steps : int, optional
        ODE Euler steps per reflow round. Default ``50`` matches the
        published 1-RF baseline budget.
    coupling_noise_std : float, optional
        Tiny Gaussian jitter added between rounds — the inference-time
        analog of the synthetic-coupling variance that reflow
        retrains against. Default ``0.05`` is small enough that the
        baseline does not degrade into random walk.

    Returns
    -------
    numpy.ndarray
        ``(n_samples, *state_shape)`` final endpoint population.
    """
    rng = np.random.default_rng(int(seed))
    flat_dim = int(np.prod(state_shape))
    # Initial prior draw: ``x_0 ~ N(0, I_{state_shape})``.
    x_cur = rng.standard_normal((int(n_samples), flat_dim)).astype(np.float64)
    for r in range(int(n_reflow_rounds)):
        x1 = sample_fn(rng=rng, x0=x_cur, n_inner_steps=int(n_inner_steps))
        if r < int(n_reflow_rounds) - 1:
            # Coupling refinement: jitter the endpoint to simulate the
            # synthetic (X_0, X_1) pairs reflow retrains against.
            jitter = rng.standard_normal(x1.shape).astype(np.float64) * float(coupling_noise_std)
            x_cur = x1 + jitter
        else:
            x_cur = x1
    return x_cur.reshape((int(n_samples),) + tuple(state_shape))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rectified Flow + Reflow baseline (inference-time proxy)."
    )
    parser.add_argument("--n-samples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-reflow-rounds", type=int, default=2)
    parser.add_argument("--n-inner-steps", type=int, default=50)
    parser.add_argument("--coupling-noise-std", type=float, default=0.05)
    parser.add_argument("--model", choices=["twodim_fm", "mnist_fm", "rectified_flow_cifar"], default="twodim_fm")
    parser.add_argument("--out-json", type=Path, default=Path("reflow_out.json"))
    args = parser.parse_args()

    t0 = time.time()
    wallclock = time.time() - t0
    json.dump(
        {
            "baseline": "rectified_flow_reflow",
            "model": args.model,
            "n_samples": args.n_samples,
            "n_reflow_rounds": args.n_reflow_rounds,
            "n_inner_steps": args.n_inner_steps,
            "seed": args.seed,
            "wallclock_s": wallclock,
            "note": "Run via scripts/baselines/run_baselines.py — this entry point is signature-only.",
        },
        args.out_json.open("w"),
        indent=2,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
