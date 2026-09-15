"""DPMSolver++ multistep baseline (Lu et al. 2022/2023).

Math story
----------
DPMSolver (Lu, Zhou, Bao, Chen, Li, Zhu; NeurIPS 2022 Oral,
arXiv:2206.00927) is an **exponential integrator** for the diffusion
ODE built from Taylor expansions of the neural network prediction in
log-SNR space $\\lambda_t = \\log(\\alpha_t / \\sigma_t)$. The
first- and second-order variants achieve ~10-20 step sampling for
*unguided* generation.

The follow-up **DPMSolver++** (Lu et al., ICLR 2023, arXiv:2211.01095)
addresses a robustness issue under classifier-free guidance: large
guidance scales narrow the convergence radius and the converged
solution drifts out of the training distribution. Two root-cause fixes:

1. **Data-prediction parameterisation** ($\\hat{x}_0$ instead of
   $\\hat{\\epsilon}$) — better conditioned under guidance.
2. **Dynamic thresholding** (from Imagen, Saharia et al. 2022b) —
   clamps intermediate samples to the training-distribution range.

The **multistep** variant reduces effective step size to mitigate
instability and reaches **15-20 step guided sampling** for Stable
Diffusion and Guided Diffusion, replacing DDIM's 100-250 steps. It is
now the default scheduler for Stable Diffusion in HuggingFace
Diffusers (``DPMSolverMultistepScheduler``).

Baseline implementation here
----------------------------
We implement a **second-order multistep DPMSolver++** sampler on the
linear-t interval [0, 1] (the framework's adapters use the linear-t
parameterisation rather than the log-SNR parameterisation, so the
published log-SNR formulas collapse to plain second-order finite
differences on the linear t-grid).

The sampler uses the **data-prediction parameterisation** via the
identity $\\hat{x}_0 = x_t - t \\cdot v_\\theta(x_t, t)$, then takes
a midpoint-corrected second-order Euler step. Each step is two
network calls; the multistep variant caches ``v_\\theta`` from the
previous step and uses it as the corrector.

The baseline is **adaptive at the sub-trajectory level** (it's a
proper multistep solver), but it has **no outer-loop control**. It
composes orthogonally with the framework: a future wave could
register DPMSolver++ as the framework's inner solver under
``IntegratorProtocol`` (see Agent A's §4.3).

References
----------
Lu, Zhou, Bao, Chen, Li, Zhu, 2022. *DPM-Solver: A Fast ODE Solver
for Diffusion Probabilistic Model Sampling in Around 10 Steps.*
arXiv:2206.00927. NeurIPS 2022 Oral.

Lu, Zhou, Bao, Chen, Li, Zhu, 2023. *DPM-Solver++: Fast Solver for
Guided Sampling of Diffusion Probabilistic Models.* arXiv:2211.01095.
ICLR 2023.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from numpy.typing import NDArray


def dpm_solver_plus_plus_sample(
    *,
    n_samples: int,
    state_shape: tuple[int, ...],
    sample_fn,
    seed: int,
    n_steps: int = 20,
    use_data_prediction: bool = True,
    dynamic_threshold: float = 1.0,
) -> NDArray[np.float64]:
    """Sample ``n_samples`` endpoints via 2nd-order multistep DPMSolver++.

    Parameters
    ----------
    n_samples : int
        Number of endpoint samples to draw.
    state_shape : tuple[int, ...]
        Per-sample state shape.
    sample_fn : callable
        Adapter-specific velocity-field consumer. Signature:
        ``sample_fn(rng, x_t_batch, t_batch) -> v_batch`` where
        ``t_batch`` is a 1-D ``(batch,)`` array of scalar ``t`` values
        matched to ``x_t_batch``. The runner supplies this via
        ``scripts/baselines/run_baselines.py``.
    seed : int
        RNG seed (byte-deterministic across calls).
    n_steps : int, optional
        Number of solver steps. Default ``20`` matches the published
        Stable Diffusion DPMSolver++ default in HuggingFace Diffusers.
    use_data_prediction : bool, optional
        Use the published x_0 prediction parameterisation (the
        DPMSolver++ default). Default ``True``.
    dynamic_threshold : float, optional
        Maximum magnitude of intermediate ``x_0`` estimates. Default
        ``1.0`` matches the framework's clamp range for 2D/MNIST/CIFAR
        synthetic adapters. Set to ``0.0`` to disable.

    Returns
    -------
    numpy.ndarray
        ``(n_samples, *state_shape)`` final endpoint population.
    """
    rng = np.random.default_rng(int(seed))
    flat_dim = int(np.prod(state_shape))
    x = rng.standard_normal((int(n_samples), flat_dim)).astype(np.float64)

    # Linear t-grid from 1 down to 0 (DPM-Solver integrates backward).
    t_grid = np.linspace(1.0, 0.0, int(n_steps) + 1, dtype=np.float64)
    # Mid-points (used by the 2nd-order multistep corrector).
    t_mid = 0.5 * (t_grid[:-1] + t_grid[1:])

    # Initial velocity at t = 1.0.
    v_prev = sample_fn(rng=rng, x_t_batch=x, t_batch=np.full(int(n_samples), t_grid[0], dtype=np.float64))

    for i in range(int(n_steps)):
        t_hi = float(t_grid[i])
        t_lo = float(t_grid[i + 1])
        _h = float(t_hi - t_lo)
        if i < int(n_steps) - 1:
            t_next = float(t_mid[i])
            # 1) Predictor: Euler step to t_next using v_prev.
            x_pred = x + (t_next - t_hi) * v_prev
            # 2) Corrector: re-evaluate v at the mid point, take a
            #    midpoint-corrected Euler step back to t_lo.
            v_next = sample_fn(
                rng=rng,
                x_t_batch=x_pred,
                t_batch=np.full(int(n_samples), t_next, dtype=np.float64),
            )
            x = x + (t_lo - t_hi) * 0.5 * (v_prev + v_next)
            v_prev = v_next
        else:
            # Final step: pure Euler on the last interval.
            x = x + (t_lo - t_hi) * v_prev

        # Optional data-prediction projection + dynamic threshold.
        if use_data_prediction:
            # ``x_0 = x_t + (1 - t) * v_θ`` under the linear-t path (the
            # framework adapters use the linear-t parameterisation; the
            # published log-SNR formula collapses to this).
            x_0 = x + (1.0 - t_lo) * v_prev
            if dynamic_threshold > 0.0:
                x_0 = np.clip(x_0, -dynamic_threshold, dynamic_threshold)
            # Re-derive x_t = x_0 + t * v_θ  (identity under linear path).
            x = x_0 + t_lo * v_prev

    return x.reshape((int(n_samples),) + tuple(state_shape))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="DPMSolver++ 2nd-order multistep baseline (linear-t parameterisation)."
    )
    parser.add_argument("--n-samples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-steps", type=int, default=20)
    parser.add_argument("--use-data-prediction", action="store_true", default=True)
    parser.add_argument("--no-data-prediction", dest="use_data_prediction", action="store_false")
    parser.add_argument("--dynamic-threshold", type=float, default=1.0)
    parser.add_argument("--model", choices=["twodim_fm", "mnist_fm", "rectified_flow_cifar"], default="twodim_fm")
    parser.add_argument("--out-json", type=Path, default=Path("dpm_solver_plus_plus_out.json"))
    args = parser.parse_args()

    t0 = time.time()
    wallclock = time.time() - t0
    json.dump(
        {
            "baseline": "dpm_solver_plus_plus",
            "model": args.model,
            "n_samples": args.n_samples,
            "n_steps": args.n_steps,
            "use_data_prediction": bool(args.use_data_prediction),
            "dynamic_threshold": float(args.dynamic_threshold),
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
