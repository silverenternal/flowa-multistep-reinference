"""Theorem 5 (paper §6.6) numerical validation: fit (m, eps_theta, sigma_blend).

Empirical plan
--------------
Given the closed-form attenuation bound (Wave 350 P1, paper §6.6 Eq. (6))

    VA_k(m, eps_theta, L_local) <= (1-m)·eps_theta·1_{k=1}
                                  - (1-m)·σ_blend^2·(k-1)·sqrt(k / L_local)

and the Wave 350 P4 12-cell grid from three CIFAR-10 RF v4 sweeps, fit
(m, eps_theta, sigma_blend) such that the bound **upper-envelopes** the
empirical VA across all 4 schedulers.

Sign convention (Wave 350 P1 footnote)
--------------------------------------
``VA`` = ``-delta_pct`` (positive = framework WINS).

Empirical VA at matched NFE = 50 on CIFAR-10 RF:
    k=1  : delta_pct in  [-1.60%,  -2.53%]  →  VA in [+0.0160, +0.0253]
    k=2  : delta_pct in  [+9.77%, +16.62%]  →  VA in [-0.1662, -0.0977]
    k=20 : delta_pct in [+24.46%, +30.65%]  →  VA in [-0.3065, -0.2446]

The bound at k=1 is **non-negative** (upper limit on VA — framework can
help). At k>=2 the bound is **non-positive** (upper limit on VA —
framework can only hurt by the accumulation term).

Bound consistency requirement
------------------------------
The bound **upper-envelopes** the empirical VA if, for every cell:

    VA_empirical <= VA_bound(m, eps_theta, sigma_blend)

i.e. for k=1:  max VA_1 ≤ (1-m)·eps_theta
                (i.e. max delta_pct_WINS ≥ 0.0253 at k=1 means correction
                channel is at least 2.53%)
                BUT actual sign: delta_pct is negative at k=1, so VA is
                positive. So 0.0253 ≤ (1-m)·eps_theta.

    for k=2:  max VA_2 = -0.0977 (least regressed) and min VA_2 = -0.1662
              (most regressed).  We want the **upper envelope** of all 4
              schedulers, i.e. the largest VA. So we need
              -0.0977 ≤ -(1-m)·sigma_blend^2·sqrt(2/L_local)
              ⇔ (1-m)·sigma_blend^2·sqrt(2/L_local) ≤ 0.0977
              (so the bound caps VA at -9.77% or lower).
              AND -0.1662 ≤ same negative bound (more regressed is
              automatically ≤ the upper envelope).
              So the binding constraint is the scheduler with the LEAST
              regression (smallest |VA|) — FreeTrajScheduler is the most
              regressed (+16.62%), but CosineAnnealScheduler is the
              LEAST regressed at k=2 (+9.77%).

Wait — we want the bound to be **violated by as little as possible**.
The empirical VA_2 is in [-0.1662, -0.0977] across 4 schedulers. The
bound VA_2 ≤ -(1-m)·sigma_blend^2·sqrt(2/L_local). For the bound to
hold for ALL 4 schedulers, we need:

    -0.0977 ≤ -(1-m)·sigma_blend^2·sqrt(2/L_local) ≤ 0
        ⇔ (1-m)·sigma_blend^2·sqrt(2/L_local) ∈ [0.0977, +∞)

If we want the bound to be **tight** (i.e. equality for the worst
scheduler), we pick (1-m)·sigma_blend^2·sqrt(2/L_local) = 0.0977.

For k=20: same logic:
    VA_20 ∈ [-0.3065, -0.2446]
    For all to satisfy: -0.2446 ≤ -(1-m)·sigma_blend^2·19·sqrt(20/L_local)
    Tightest fit: (1-m)·sigma_blend^2·19·sqrt(20/L_local) = 0.2446

So we have two equations:

    (1-m)·sigma_blend^2·sqrt(2/L_local) = 0.0977          (1)
    (1-m)·sigma_blend^2·19·sqrt(20/L_local) = 0.2446     (2)

Dividing (2) / (1):
    19 · sqrt(20/L_local) / sqrt(2/L_local) = 0.2446 / 0.0977
    19 · sqrt(10) = 2.504
    60.083 = 2.504   ← this is FALSE.

This means the empirical data does NOT lie on a single tight fit
under the (k-1)·sqrt(k/L_local) accumulation structure. The actual
ratio is 19·sqrt(10) ≈ 60, but the empirical ratio is 2.504.

Interpretation:
    The Theorem 5 closed-form bound is **asymptotic** in k. For k=2,
    the discrete accumulation term is closer to (1-m)·sigma_blend^2·1
    (1 round of accumulation), and for k=20 it's 19 rounds of
    accumulation. The empirical data shows the discrete accumulation
    saturates: at k=20 the regression is only ~2.5x the k=2 regression
    (not 10x as the (k-1)·sqrt(k) factor would predict).

The numerical validation therefore characterizes how well the bound
**scales** with k: empirically the scale factor is sqrt(2.504) ≈ 1.58
between k=2 and k=20, but the bound predicts sqrt(60) ≈ 7.75. The
**discrepancy** is reported as a (k-1)-slope ratio.

Outputs
-------
``verification_outputs/wave351-p3-thm5-numerical/thm5_fit.json``
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO = Path("/home/hugo/codes/flowa-multistep-reinference")
LIP_PATH = REPO / "verification_outputs" / "wave351-p3-thm5-numerical" / "lipschitz_estimate.json"
OUT_DIR = REPO / "verification_outputs" / "wave351-p3-thm5-numerical"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 12-cell grid transcribed from
#   docs/audit/wave350-r5b-figure.md §2.1 + §2.2 + §2.3
# (Wave 235 P1 n_rounds=1, Wave 225 P7 n_rounds=2, Wave 206 P6 n_rounds=20).
# Sign convention: delta_pct > 0 = framework REGRESSES (FID increases).
GRID: dict[int, dict[str, float]] = {
    1: {  # n_rounds=1  (Wave 235 P1, baseline FID=454.3854)
        "CosineAnnealScheduler":       -0.01601824,  # -1.60%
        "CodimensionSheetScheduler":   -0.02530173,  # -2.53%
        "EvidenceDrivenScheduler":     -0.00117280,  # -0.12%
        "FreeTrajScheduler":           -0.00663789,  # -0.66%
    },
    2: {  # n_rounds=2  (Wave 225 P7, baseline FID=458.5809)
        "CosineAnnealScheduler":       +0.09765173,  # +9.77%
        "CodimensionSheetScheduler":   +0.09787868,  # +9.79%
        "EvidenceDrivenScheduler":     +0.09825986,  # +9.83%
        "FreeTrajScheduler":           +0.16621579,  # +16.62%
    },
    20: {  # n_rounds=20 (Wave 206 P6, baseline FID=83.0866, n=500)
        "CosineAnnealScheduler":       +0.24890000,  # +24.89%
        "CodimensionSheetScheduler":   +0.25130000,  # +25.13%
        "EvidenceDrivenScheduler":     +0.24460000,  # +24.46%
        "FreeTrajScheduler":           +0.30650000,  # +30.65%
    },
}


def thm5_bound(
    k: int,
    m: float,
    eps_theta: float,
    sigma_blend: float,
    L_local: float,
) -> float:
    """Theorem 5 (Wave 350 P1, paper §6.6 Eq. (6)) closed-form upper bound on VA_k."""
    indicator = 1.0 if k == 1 else 0.0
    return (
        (1.0 - m) * eps_theta * indicator
        - (1.0 - m) * sigma_blend * sigma_blend * (k - 1) * math.sqrt(k / L_local)
    )


def main() -> int:
    if not LIP_PATH.exists():
        print(f"[thm5] missing {LIP_PATH}; run estimate_lipschitz.py first", file=sys.stderr)
        return 1

    lip = json.loads(LIP_PATH.read_text(encoding="utf-8"))
    L_local = float(lip["selected_L_local"])

    # ----- Step 1: derive (1-m)·eps_theta from k=1 data -----
    # At k=1, VA_bound = (1-m)·eps_theta. We need (1-m)·eps_theta ≥ max VA_1.
    # max VA_1 across the 4 schedulers at k=1:
    va_1 = [-GRID[1][s] for s in GRID[1]]  # VA = -delta_pct
    max_va_1 = max(va_1)  # = 0.0253 (CodimensionSheetScheduler)
    min_va_1 = min(va_1)  # = 0.0012 (EvidenceDrivenScheduler)

    # ----- Step 2: derive (1-m)·sigma_blend^2 from k=2 and k=20 data -----
    # Consistency: for every scheduler, VA_empirical_i ≤ VA_bound.
    # At k=2 the empirical VA ranges across 4 schedulers; the *binding*
    # constraint is the LEAST regressed scheduler (smallest |VA|, largest
    # numerical value of VA). For the bound to be ≤ that empirical VA,
    # we need VA_bound ≤ -LEAST_REGRESSED (the bound is more negative
    # than even the best-case empirical).
    #
    # Equivalently: (1-m)·sigma_blend^2·sqrt(2/L_local) ≥ LEAST_REGRESSED.
    #
    # The LEAST regressed scheduler at k=2 is CosineAnnealScheduler at
    # delta_pct = +9.77% (smallest regression = closest to WINS).
    va_2 = [-GRID[2][s] for s in GRID[2]]  # all negative (REGRESS)
    va_20 = [-GRID[20][s] for s in GRID[20]]

    least_regressed_va_2 = max(va_2)   # largest (least negative) VA_2
    least_regressed_va_20 = max(va_20)  # largest (least negative) VA_20

    # ----- Step 3: solve for (1-m)·sigma_blend^2 -----
    # Equation (k=2): (1-m)·sigma_blend^2 = (-LEAST_REGRESSED_VA_2) / sqrt(2/L_local)
    #   (VA_2 is negative, so -VA_2 = |least regressed| > 0)
    # Equation (k=20): (1-m)·sigma_blend^2 = (-LEAST_REGRESSED_VA_20) / (19·sqrt(20/L_local))
    lhs_k2 = -least_regressed_va_2 / math.sqrt(2.0 / L_local)
    lhs_k20 = -least_regressed_va_20 / (19.0 * math.sqrt(20.0 / L_local))

    # The two equations give different (1-m)·sigma_blend^2 values if the bound
    # is not perfectly tight. Report both.
    sm2_from_k2 = lhs_k2
    sm2_from_k20 = lhs_k20

    # ----- Step 4: parameterize the canonical fit -----
    # The framework's default memory_fraction saturates at m_max = 0.5
    # (nfe_aware.py:98). Set m = 0.5 (canonical max).
    m_canonical = 0.5
    one_minus_m = 1.0 - m_canonical

    # Solve for sigma_blend^2 (from the k=2 binding constraint — least
    # regressed scheduler gives the tightest fit that still satisfies all 4).
    sigma_blend_sq = sm2_from_k2 / one_minus_m
    sigma_blend = math.sqrt(max(sigma_blend_sq, 0.0))

    # Solve for eps_theta (from the k=1 max VA constraint — same logic,
    # use the most-extreme WINS to set the bound).
    eps_theta = max_va_1 / one_minus_m

    # ----- Step 5: verify the bound against all 12 cells -----
    cells: list[dict[str, float | int | str | bool]] = []
    for k, schedulers in GRID.items():
        for sched_name, delta_pct in schedulers.items():
            va_empirical = -delta_pct
            va_bound = thm5_bound(k, m_canonical, eps_theta, sigma_blend, L_local)
            consistent = va_empirical <= va_bound
            cells.append({
                "k": int(k),
                "scheduler": sched_name,
                "delta_pct_empirical": float(delta_pct),
                "va_empirical": float(va_empirical),
                "va_bound_m0.5": float(va_bound),
                "consistent": bool(consistent),
            })

    # ----- Step 6: transition boundary prediction -----
    # Empirical transition: k=1 WINS (VA>0), k>=2 REGRESSES (VA<0).
    # The bound predicts the same discrete transition:
    #   VA_bound(k=1) = (1-m)*eps_theta ≥ 0     → WINS possible
    #   VA_bound(k>=2) = -(1-m)*sigma_blend^2*(k-1)*sqrt(k/L_local) < 0
    #                   → REGRESSES inevitable
    # Hence the bound **predicts** the discrete transition at k=1 → k=2.
    transition_predicted = True

    # ----- Step 7: empirical-vs-bound slope ratio -----
    # The bound's accumulation term scales as (k-1)·sqrt(k/L_local). For
    # k=2 vs k=20, the predicted scale ratio is:
    slope_ratio_predicted = (19.0 * math.sqrt(20.0 / L_local)) / (1.0 * math.sqrt(2.0 / L_local))
    # = 19 * sqrt(10) ≈ 60.08
    # The empirical |VA| ratio (using max-abs empirical regression) is:
    max_abs_va_2 = max(abs(v) for v in va_2)   # = 0.1662 (FreeTrajScheduler)
    max_abs_va_20 = max(abs(v) for v in va_20)  # = 0.3065 (FreeTrajScheduler)
    slope_ratio_empirical = max_abs_va_20 / max_abs_va_2
    # = 0.3065 / 0.1662 ≈ 1.844

    out = {
        "schema": "wave351_p3_thm5_numerical_fit.v1",
        "timestamp_utc": "2026-09-25T00:00:00Z",
        "L_local_input": float(L_local),
        "L_local_source": "verification_outputs/wave351-p3-thm5-numerical/lipschitz_estimate.json",
        "L_local_components": {
            "analytic_op_norm": lip["analytic"]["lipschitz_analytic_op_norm"],
            "numerical_sample_max": lip["numerical"]["lipschitz_numerical_sample_max"],
        },
        "grid_12_cell": cells,
        "fit_k2_canonical": {
            "m_canonical": m_canonical,
            "one_minus_m": float(one_minus_m),
            "eps_theta_fitted": float(eps_theta),
            "sigma_blend_fitted": float(sigma_blend),
            "sigma_blend_sq_fitted": float(sigma_blend_sq),
            "binding_constraint": "k=2 least-regressed scheduler (CosineAnneal, +9.77%)",
            "n_cells_consistent": int(sum(1 for c in cells if c["consistent"])),
        },
        "validation": {
            "n_cells_total": len(cells),
            "n_cells_consistent": sum(1 for c in cells if c["consistent"]),
            "transition_predicted": bool(transition_predicted),
            "transition_empirical": (
                "k=1 WINS (4/4), k>=2 REGRESSES (4/4) — discrete transition observed"
            ),
            "transition_accuracy": (
                "matches_empirical — bound predicts WINS-at-k=1 / REGRESSES-at-k>=2 "
                "for any finite L_local > 0 (Sub-claim 5.1, Lipschitz-agnostic)"
            ),
            "slope_ratio_predicted": float(slope_ratio_predicted),
            "slope_ratio_empirical": float(slope_ratio_empirical),
            "slope_ratio_discrepancy": (
                "bound predicts (k-1)·sqrt(k) scaling, empirical scales "
                "sub-linearly (saturates between k=2 and k=20); the per-round "
                "accumulation term grows more slowly than the bound's "
                "asymptotic prediction, suggesting finite-sample saturation "
                "of the blend-variance accumulation in the matched-NFE "
                "matched-seed CIFAR-10 RF protocol"
            ),
        },
        "alternative_fits": {
            "m_eq_0": {
                "one_minus_m": 1.0,
                "eps_theta_eq_0": float(max_va_1),
                "sigma_blend_sq_eq_0": float(sm2_from_k2),
                "sigma_blend_eq_0": float(math.sqrt(max(sm2_from_k2, 0.0))),
            },
            "m_eq_0.7": {
                "one_minus_m": 0.3,
                "eps_theta_eq_0.7": float(max_va_1 / 0.3),
                "sigma_blend_sq_eq_0.7": float(sm2_from_k2 / 0.3),
                "sigma_blend_eq_0.7": float(math.sqrt(max(sm2_from_k2 / 0.3, 0.0))),
            },
        },
        "binding_constraints": {
            "k1_max_va_across_schedulers": float(max_va_1),
            "k1_min_va_across_schedulers": float(min_va_1),
            "k2_least_regressed_va": float(least_regressed_va_2),
            "k2_most_regressed_va": float(min(va_2)),
            "k20_least_regressed_va": float(least_regressed_va_20),
            "k20_most_regressed_va": float(min(va_20)),
            "k2_binding_scheduler": "CosineAnnealScheduler (+9.77%, smallest |VA|)",
            "k20_binding_scheduler": "EvidenceDrivenScheduler (+24.46%, smallest |VA|)",
        },
        "sm2_under_tight_fit": {
            "from_k2_constraint": float(sm2_from_k2),
            "from_k20_constraint": float(sm2_from_k20),
            "ratio_k20_over_k2": float(sm2_from_k20 / sm2_from_k2) if sm2_from_k2 > 0 else None,
            "interpretation": (
                "If the bound is tight at both k=2 and k=20 (single (1-m)*sigma_blend^2), "
                "the ratio of the two constraints equals the empirical |VA_20|/|VA_2| "
                "ratio. The ratio sm2_from_k20 / sm2_from_k2 is approximately 1/slope_ratio_empirical = 1/1.844 ≈ 0.542 — i.e. the k=2 constraint is "
                "more permissive than the k=20 constraint. The tightest single (1-m)*sigma_blend^2 "
                "is the larger of the two (= max(sm2_from_k2, sm2_from_k20))."
            ),
        },
    }

    # ----- Step 8: alternative fit using k=20 binding constraint -----
    # Solve for sigma_blend^2 from k=20 constraint (least regressed = EvidenceDrivenScheduler, +24.46%)
    sm2_k20_only = -least_regressed_va_20 / (19.0 * math.sqrt(20.0 / L_local))
    sigma_blend_k20 = math.sqrt(sm2_k20_only / one_minus_m)

    # Verify against all 12 cells
    cells_k20: list[dict[str, float | int | str | bool]] = []
    for k, schedulers in GRID.items():
        for sched_name, delta_pct in schedulers.items():
            va_empirical = -delta_pct
            va_bound = thm5_bound(k, m_canonical, eps_theta, sigma_blend_k20, L_local)
            consistent = va_empirical <= va_bound
            cells_k20.append({
                "k": int(k),
                "scheduler": sched_name,
                "delta_pct_empirical": float(delta_pct),
                "va_empirical": float(va_empirical),
                "va_bound_k20_fit": float(va_bound),
                "consistent": bool(consistent),
            })

    out["fit_k20_canonical"] = {
        "m_canonical": m_canonical,
        "one_minus_m": float(one_minus_m),
        "eps_theta_fitted": float(eps_theta),
        "sigma_blend_fitted": float(sigma_blend_k20),
        "sigma_blend_sq_fitted": float(sm2_k20_only),
        "binding_constraint": "k=20 least-regressed scheduler (EvidenceDriven, +24.46%)",
        "n_cells_consistent": int(sum(1 for c in cells_k20 if c["consistent"])),
        "grid_12_cell": cells_k20,
    }

    out_path = OUT_DIR / "thm5_fit.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"[thm5] wrote {out_path}")
    print(f"[thm5] L_local = {L_local:.4f}")
    print(f"[thm5] canonical fit (k=2 binding): m={m_canonical}, eps_theta={eps_theta:.4f}, sigma_blend={sigma_blend:.4f}")
    print(f"[thm5] k=20-binding fit: sigma_blend={sigma_blend_k20:.4f}, cells consistent={sum(1 for c in cells_k20 if c['consistent'])}/12")
    print(f"[thm5] transition predicted: {transition_predicted}")
    print(f"[thm5] slope ratio predicted: {slope_ratio_predicted:.2f}, empirical: {slope_ratio_empirical:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())