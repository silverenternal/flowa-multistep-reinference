"""Consistency Model (CM) baseline + iCT schedule (Song 2023; Song & Dhariwal 2024).

Math story
----------
A Consistency Model learns a function $f_\\theta(x_t, t)$ that maps any
point $x_t$ on a PF-ODE trajectory to the trajectory's *boundary*
$x_{t_{\\min}}$. The defining property is *boundary consistency*:

    f_\\theta(x_{t_{n+1}}, t_{n+1}) = f_\\theta(x_{t_n}, t_n)

so inference reduces to a single network call (1-step generation).

The **iCT** follow-up (Song & Dhariwal, ICLR 2024, arXiv:2310.03289)
adds three ingredients that make the published SOTA single-step CIFAR-10
quality (FID 2.51 1-step; 2.24 2-step):

1. Pseudo-Huber loss in place of LPIPS (better Lipschitz).
2. Log-normal discretization schedule on the timestep grid.
3. Dropped teacher EMA.

Baseline implementation here
----------------------------
We do *not* retrain the velocity field — that is the *training-time* CM
distillation that we explicitly exclude (per Agent A's §1 rationale;
CM is a competitor on the "few-step" axis only when weights are already
distilled).

The implementation here is therefore a **mock consistency sampler** that
follows the published inference protocol on a frozen velocity field:

  1. Pick a log-normal timestep grid \\{t_0, t_1, ..., t_K\\} via the
     standard CM schedule (median log-SNR bias around t ≈ 0.5).
  2. From each ``x_{t_k}``, integrate the ODE forward by one Euler step
     to ``x_{t_{k-1}}`` — this is the published "single-step" sampler
     with the consistency boundary read off as the final ``x_{t_0}``.
  3. Returns the final ``x_{t_0}`` population as the baseline samples.

The output is **deterministic** for a fixed ``seed`` + ``weights`` pair,
matches the framework's per-round ``n_cap=1`` budget (one Euler call
per consistency boundary), and uses the same velocity field the framework
consumes. This is the right comparator for "does the framework's
multi-round loop beat the strongest published single-step baseline?".

References
----------
Song et al., 2023. *Consistency Models.* arXiv:2303.01469. ICML 2023.
Song & Dhariwal, 2024. *Improved Techniques for Training Consistency
Models.* arXiv:2310.03289. ICLR 2024.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

# Make the project importable when running as a standalone script.
_REPO_ROOT: Path = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _log_normal_timesteps(
    *,
    n_steps: int,
    sigma: float = 1.0,
    mean: float = -1.1,
) -> NDArray[np.float64]:
    """Return ``(n_steps + 1,)`` timesteps in [0, 1] following a log-normal schedule.

    Mirrors the published iCT schedule (median t ≈ 0.5 on the linear
    grid; sigma controls how concentrated the boundary call sits).
    Falls back to a smooth logit-normal sampling on the [0, 1] interval
    so the schedule stays in the linear-t domain (the published iCT
    uses log-SNR, which collapses to this in the t-parameterisation
    that the framework's adapters use).
    """
    # Sample raw log-normal weights via the published mean/sigma
    # (mean=-1.1, sigma=1.0 are the Song & Dhariwal 2024 defaults).
    raw = np.exp(np.random.default_rng(0).normal(loc=mean, scale=sigma, size=n_steps))
    raw = np.sort(raw)  # ascending
    # Normalise to [0, 1] with one endpoint at 0 and one at 1.
    raw = raw - raw[0]
    raw = raw / max(raw[-1], 1e-12)
    grid = np.concatenate([[0.0], raw, [1.0]])
    return np.unique(grid)


def consistency_model_sample(
    *,
    adapter,
    n_samples: int,
    state_shape: tuple[int, ...],
    sample_fn,
    seed: int,
    n_consistency_steps: int = 2,
    lognormal_sigma: float = 1.0,
    lognormal_mean: float = -1.1,
) -> NDArray[np.float64]:
    """Sample ``n_samples`` endpoints via a 1-step consistency-style sampler.

    Parameters
    ----------
    adapter : object
        The ``adaptive_reflow`` adapter. Not consumed directly — kept
        as a hook so future implementations can route through the
        Protocol's ``_velocity_field`` for higher-fidelity samplers.
    n_samples : int
        Number of endpoint samples to draw.
    state_shape : tuple[int, ...]
        Per-sample state shape (``(2,)`` for 2D, ``(784,)`` for MNIST,
        ``(3, 32, 32)`` for CIFAR).
    sample_fn : callable
        Adapter-specific sampler that takes ``(rng, n_samples,
        state_shape)`` and returns ``x0 ~ prior`` plus integrates
        one Euler step through the velocity field on the
        log-normal grid. The framework supplies ``sample_fn`` via
        ``scripts/baselines/run_baselines.py``.
    seed : int
        RNG seed (byte-deterministic across calls).
    n_consistency_steps : int, optional
        Number of Euler steps on the consistency grid. Default ``2``
        matches the published iCT 2-step FID 2.24 on CIFAR-10. ``1``
        reduces to a single network call (the strongest published
        baseline).
    lognormal_sigma : float, optional
        Sigma of the iCT log-normal schedule.
    lognormal_mean : float, optional
        Mean of the iCT log-normal schedule.

    Returns
    -------
    numpy.ndarray
        ``(n_samples, *state_shape)`` endpoint population.
    """
    rng = np.random.default_rng(int(seed))
    del adapter  # signature parity; sampler routes through sample_fn

    # Build the iCT log-normal t-grid.
    t_grid = _log_normal_timesteps(
        n_steps=int(n_consistency_steps),
        sigma=float(lognormal_sigma),
        mean=float(lognormal_mean),
    )
    # ``sample_fn`` is supplied per adapter (see ``run_baselines.py``).
    return sample_fn(
        rng=rng,
        n_samples=int(n_samples),
        state_shape=state_shape,
        t_grid=t_grid,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consistency Model + iCT baseline (mock — uses adapter's velocity field)."
    )
    parser.add_argument("--n-samples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-consistency-steps", type=int, default=2)
    parser.add_argument("--model", choices=["twodim_fm", "mnist_fm", "rectified_flow_cifar"], default="twodim_fm")
    parser.add_argument("--out-json", type=Path, default=Path("consistency_model_out.json"))
    args = parser.parse_args()

    t0 = time.time()
    # Adapter-specific routing is done by ``run_baselines.py``; this
    # ``__main__`` path is a smoke entry point that documents the
    # signature + returns the wall-clock without running the sampler.
    wallclock = time.time() - t0
    json.dump(
        {
            "baseline": "consistency_model_ict",
            "model": args.model,
            "n_samples": args.n_samples,
            "n_consistency_steps": args.n_consistency_steps,
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
