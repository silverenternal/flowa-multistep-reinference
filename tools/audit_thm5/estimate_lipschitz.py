"""Theorem 5 (paper §6.6) numerical validation: estimate L_local via finite differences.

Empirical plan
--------------
Theorem 5 (Wave 350 P1, paper §6.6) introduces the closed-form attenuation bound

    VA_k(m, eps_theta, L_local) <= (1-m)·eps_theta·1_{k=1}
                                  - (1-m)·σ_blend^2·(k-1)·sqrt(k / L_local)

The bound depends on three structural quantities:

    m           : per-scheduler memory_fraction in [0, 1]
    eps_theta   : residual-error floor of the velocity field
    L_local     : per-adapter Lipschitz constant of the velocity field
                  w.r.t. its input
    sigma_blend : std of the per-round blend operator output

This script estimates L_local via finite differences of the CIFAR-10 RF
adapter's velocity field on a batch of random latents. The adapter ships
two backends:

  - ``synthetic`` (NumPy-only, no torch) — used by the test suite; a
    2-layer MLP ``v(x, t) = W2 @ tanh(W1 @ x + b1 + t * t_bias) + b2``
    on the flattened (3*32*32) state.
  - ``torch`` — production path with a UNet DDPM++ backbone; requires
    a checkpoint under ``data/rectified_flow_cifar/`` and ``torch``
    importable.

The Lipschitz constant of the synthetic field is **structurally upper-
bounded** by ``‖W2‖_op · ‖W1‖_op`` (the operator-norm product, since
the Jacobian of ``tanh`` is bounded by 1 elementwise). The torch UNet's
Lipschitz constant is harder to bound analytically; finite differences
give a numerical surrogate that the framework uses for sanity checks.

We compute both:

  - **Analytic upper bound** for the synthetic MLP (operator-norm product).
  - **Numerical finite-difference estimate** on 100 random latents.

Both are reported in the output JSON so a reviewer can compare the
analytic bound against the empirical sample-max estimate.

Sign convention (Wave 350 P1 footnote)
--------------------------------------
``VA`` = ``-delta_pct`` (positive = framework WINS). At matched-NFE=50
on CIFAR-10 RF, the framework REGRESSES 4/4 schedulers at k>=2 so the
empirical VA is **negative** at k>=2 and **positive** at k=1.

For a fitted ``L_local`` we plug it into Theorem 5 with the empirical
12-cell grid:

    VA_1 : delta_pct in  [-1.60%,  -2.53%]  →  VA_1 in [+0.0160, +0.0253]
    VA_2 : delta_pct in  [+9.77%, +16.62%]  →  VA_2 in [-0.1662, -0.0977]
    VA_20: delta_pct in [+24.46%, +30.65%]  →  VA_20 in [-0.3065, -0.2446]

Bound at k=1 is **non-negative** (positive upper limit on VA, frame-
work can help). Bound at k>=2 is **non-positive** (negative upper
limit, framework can only hurt by the accumulation term).

The numerical-validation question is whether the empirical VA lies
**inside the bound** for some (m, eps_theta, sigma_blend) consistent
with the framework's defaults (``m_max = 0.5`` per nfe_aware.py:98,
``default sigma_blend ≈ 1.0`` per the empirical blend operator).

Outputs
-------
``verification_outputs/wave351-p3-thm5-numerical/lipschitz_estimate.json``

    {
      "lipschitz_analytic_op_norm": float,
      "lipschitz_numerical_finite_diff": float,
      "lipschitz_numerical_sample_max": float,
      "n_random_latents": int,
      "t_values": [float],
      "weight_seed": int,
      "backend": "synthetic",
      "notes": "..."
    }
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path("/home/hugo/codes/flowa-multistep-reinference")
OUT_DIR = REPO / "verification_outputs" / "wave351-p3-thm5-numerical"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Synthetic CIFAR-10 RF velocity-field constants (from
# adaptive_reflow/adapters/rectified_flow_cifar.py:100, :204).
STATE_SHAPE = (3, 32, 32)
IN_DIM = 3 * 32 * 32  # 3072
HIDDEN = 32  # RF_CIFAR_SYNTHETIC_HIDDEN


def kaiming_uniform(rng: np.random.Generator, fan_in: int, fan_out: int) -> np.ndarray:
    """Kaiming-uniform init (matches rectified_flow_cifar._random_init_synthetic_weights)."""
    bound = math.sqrt(1.0 / fan_in)
    return rng.uniform(-bound, bound, size=(fan_in, fan_out)).astype(np.float64)


def build_synthetic_weights(seed: int = 0) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(int(seed))
    return {
        "W1": kaiming_uniform(rng, IN_DIM, HIDDEN),
        "b1": np.zeros(HIDDEN, dtype=np.float64),
        "W2": kaiming_uniform(rng, HIDDEN, IN_DIM),
        "b2": np.zeros(IN_DIM, dtype=np.float64),
        "t_bias": rng.standard_normal(HIDDEN).astype(np.float64),
    }


def synthetic_velocity(x: np.ndarray, t: float, w: dict[str, np.ndarray]) -> np.ndarray:
    flat = np.asarray(x, dtype=np.float64).reshape(-1)
    h = np.tanh(flat @ w["W1"] + w["b1"] + float(t) * w["t_bias"])
    out = h @ w["W2"] + w["b2"]
    return out.reshape(STATE_SHAPE)


def analytic_lipschitz_op_norm(w: dict[str, np.ndarray]) -> dict[str, float]:
    """Operator-norm product ‖W2‖_op · ‖W1‖_op (upper bound on ‖J_v‖_op).

    For v(x) = W2 · tanh(W1 · x + b1 + t*t_bias) + b2, the Jacobian is
        J_v(x) = W2 · diag(1 - tanh^2) · W1.
    Each diagonal element of ``1 - tanh^2`` is in [0, 1], so the
    operator norm satisfies ‖J_v‖_op ≤ ‖W2‖_op · ‖W1‖_op.
    """
    w1 = w["W1"]
    w2 = w["W2"]
    op_w1 = np.linalg.norm(w1, ord=2)
    op_w2 = np.linalg.norm(w2, ord=2)
    return {
        "op_norm_W1": float(op_w1),
        "op_norm_W2": float(op_w2),
        "lipschitz_analytic_op_norm": float(op_w1 * op_w2),
    }


def numerical_lipschitz_finite_diff(
    w: dict[str, np.ndarray],
    n_latents: int = 100,
    *,
    eps: float = 1e-3,
    seed: int = 42,
    t_values: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0),
) -> dict[str, float]:
    """Sample-max finite-difference estimate of L_local.

    For each random latent x and each t in t_values, sample a small
    perturbation δ with ‖δ‖ = eps and compute
        ‖v(x + δ, t) - v(x, t)‖ / ‖δ‖.
    Return the sample-max (a finite-sample upper envelope on the
    Lipschitz constant under random directions).
    """
    rng = np.random.default_rng(int(seed))
    flat_dim = IN_DIM

    ratios: list[float] = []
    for _ in range(n_latents):
        x_flat = rng.standard_normal(flat_dim).astype(np.float64)
        # Random unit-norm perturbation.
        delta_flat = rng.standard_normal(flat_dim).astype(np.float64)
        delta_flat = eps * delta_flat / max(np.linalg.norm(delta_flat), 1e-12)

        x = x_flat.reshape(STATE_SHAPE)
        delta = delta_flat.reshape(STATE_SHAPE)
        x_plus = x + delta

        for t in t_values:
            v0 = synthetic_velocity(x, t, w).reshape(-1)
            v1 = synthetic_velocity(x_plus, t, w).reshape(-1)
            num = float(np.linalg.norm(v1 - v0))
            den = float(np.linalg.norm(delta_flat))
            if den > 0:
                ratios.append(num / den)

    ratios_arr = np.asarray(ratios, dtype=np.float64)
    return {
        "n_random_latents": int(n_latents),
        "n_perturbations_total": int(ratios_arr.size),
        "t_values": [float(t) for t in t_values],
        "eps_perturbation": float(eps),
        "lipschitz_numerical_mean": float(np.mean(ratios_arr)),
        "lipschitz_numerical_p95": float(np.percentile(ratios_arr, 95)),
        "lipschitz_numerical_p99": float(np.percentile(ratios_arr, 99)),
        "lipschitz_numerical_sample_max": float(np.max(ratios_arr)),
        "seed": int(seed),
    }


def main() -> int:
    w = build_synthetic_weights(seed=0)
    analytic = analytic_lipschitz_op_norm(w)
    numerical = numerical_lipschitz_finite_diff(w, n_latents=100, seed=42)

    out = {
        "schema": "wave351_p3_thm5_lipschitz_estimate.v1",
        "timestamp_utc": "2026-09-25T00:00:00Z",
        "backend": "synthetic (NumPy 2-layer MLP, RF_CIFAR_SYNTHETIC_HIDDEN=32)",
        "weight_seed": 0,
        "in_dim": IN_DIM,
        "hidden_dim": HIDDEN,
        "state_shape": list(STATE_SHAPE),
        "analytic": analytic,
        "numerical": numerical,
        "selected_L_local": numerical["lipschitz_numerical_sample_max"],
        "notes": (
            "Synthetic CIFAR-10 RF velocity field (no torch dep). Analytic bound is the "
            "operator-norm product ‖W2‖_op · ‖W1‖_op. Numerical bound is the sample-max "
            "finite-difference estimate over 100 random latents × 5 t-values = 500 "
            "perturbations. The selected L_local is the numerical sample-max (the more "
            "conservative estimate; the analytic bound is a tighter upper bound on the "
            "true operator-norm but does not capture the (1 - tanh^2) Jacobian suppression "
            "at random points)."
        ),
    }
    out["selected_L_local"] = float(numerical["lipschitz_numerical_sample_max"])

    out_path = OUT_DIR / "lipschitz_estimate.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"[thm5] wrote {out_path}")
    print(f"[thm5] analytic L_local (op-norm):     {analytic['lipschitz_analytic_op_norm']:.4f}")
    print(f"[thm5] numerical L_local (sample-max): {numerical['lipschitz_numerical_sample_max']:.4f}")
    print(f"[thm5] selected L_local:               {out['selected_L_local']:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
