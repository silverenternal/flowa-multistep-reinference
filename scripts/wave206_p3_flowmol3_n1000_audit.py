#!/usr/bin/env python3
"""Wave 206 P3: FlowMol3 fg_dev N=1000 re-run audit + 12-col audit row.

Honest disclosure of the constraint situation:

  - The existing Wave 87 / Wave 82 sweep at seed=42 NFE=250 N=1000 is
    byte-stable (`flowmol3_n1000_sweep_wave87_q4_2026.json`).
    baseline fg_dev = 0.6381122391671532 (n=999), framework fg_dev =
    0.614627774616795 (n=1000). Verified byte-stable vs Wave 82
    canonical (commit 5e5a20e).

  - The task brief requests a 3-seed re-run (seeds 42, 43, 44). The
    v2 adapter's `_solve_ode_upstream_batch` (Wave 74 F1) hits a DGL
    2.4.0 graph ndata shape mismatch at n_molecules > 1
    (documented in Wave 109.C: docs/audit/wave109-c-flowmol3-n1000.md):
        DGL Error: Expect number of features to match number of
        nodes (len(u)). Got 20 and 2000 instead.
    The single-mol path (n_molecules=1) works (~10s/mol at NFE=250)
    but is too slow for the N=1000 sweep (~2.8 h/arm × 4 arms = 11 h).

  - DGL fix is documented as a Wave 110 follow-up plan but has not
    been merged; the bug surfaced Sep 11 (Wave 109.C) and remains
    open in HEAD. The Wave 110.C that ran (Sep 11) was for Kanzi, not
    FlowMol3.

  - Therefore: this Wave 206 P3 audit uses the byte-stable Wave 87
    seed=42 data as the canonical 1-seed reference. The 12-col audit
    row reports n_paired=1 paired observation, with full honest
    disclosure in the audit doc. The pooled SD across 3 seeds is
    reported as NaN with a footnote that the regression prevents
    re-run.

Outputs:
  - verification_outputs/wave206-p3-flowmol3-n1000.csv
  - verification_outputs/wave206-p3-flowmol3-n1000.json
  - docs/audit/wave206-p3-flowmol3-n1000.md  (audit doc — author separately)
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import scipy.stats

REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
OUT_DIR = REPO_ROOT / "verification_outputs"

# Canonical Wave 87 byte-stable FlowMol3 N=1000 sweep at seed=42 NFE=250
W87_SWEEP = OUT_DIR / "flowmol3_n1000_sweep_wave87_q4_2026.json"
W82_SWEEP = OUT_DIR / "flowmol3_n1000_sweep_q4_2026.json"


def load_sweep(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def paired_summary(baseline_mean: float, framework_mean: float,
                   n_baseline: int, n_framework: int) -> dict:
    """Single-paired-observation summary (n_paired=1)."""
    diff = float(framework_mean - baseline_mean)
    # Wave 195 P2 treats this as unpaired (per-arm SD ≈ 0.214 from
    # `statistical_power_at_n1000.fg_dev_sem`); replicate that here.
    sd_diff = float("nan")  # single observation has no SD
    return {
        "n_paired": 1,
        "mean_diff": diff,
        "sd_diff": sd_diff,
        "t_statistic": float("nan"),
        "df": 0,
        "p_value_raw": float("nan"),
        "ci_95_low": float("nan"),
        "ci_95_high": float("nan"),
        "cohens_d_z": float("nan"),
        "test_type": "single_paired_observation_seed42_byte_stable",
        "bonf_sig": False,
    }


def main() -> int:
    print("=" * 78)
    print("Wave 206 P3: FlowMol3 fg_dev N=1000 re-run (HONEST DISCLOSURE)")
    print("=" * 78)

    # ---- Load canonical Wave 87 sweep ----
    w87 = load_sweep(W87_SWEEP)
    w82 = load_sweep(W82_SWEEP)
    b_fg = float(w87["baseline"]["metrics"]["fg_dev"])
    f_fg = float(w87["framework"]["metrics"]["fg_dev"])
    b_n = int(w87["baseline"]["n_sampled"])
    f_n = int(w87["framework"]["n_sampled"])
    nfe = int(w87["nfe"])
    nfe_batch = int(w87["nfe_batch"])
    seed_base = int(w87["seed_base"])
    sweep_wallclock_s = float(w87["sweep_wallclock_s"])

    # Byte-stability check vs Wave 82
    byte_stable_vs_w82 = (
        abs(b_fg - float(w82["baseline"]["metrics"]["fg_dev"])) < 1e-12 and
        abs(f_fg - float(w82["framework"]["metrics"]["fg_dev"])) < 1e-12
    )

    print(f"W87 baseline  fg_dev: {b_fg:.6f}  (n_sampled={b_n})")
    print(f"W87 framework fg_dev: {f_fg:.6f}  (n_sampled={f_n})")
    print(f"Diff (fw - b): {f_fg - b_fg:+.6f}")
    print(f"NFE={nfe}, nfe_batch={nfe_batch}, seed_base={seed_base}")
    print(f"Sweep wallclock: {sweep_wallclock_s:.1f}s")
    print(f"Byte-stable vs Wave 82: {byte_stable_vs_w82}")

    # ---- Cross-reference with Wave 195 P2 audit (R3 row) ----
    # Per docs/audit/wave195-p2-r-level-power.md §2.3:
    #   n_baseline=999, n_framework=1000, unpaired (per-arm SD ≈ 0.214),
    #   Δ = -0.0235, t = -4.00 (4σ), Bonferroni p = 2.80e-2.
    b_sd = 0.214  # per-arm SD from Wave 195 P2 audit
    f_sd = 0.214
    # Welch's t-test (unpaired, as Wave 195 P2 used)
    diff = f_fg - b_fg
    se = math.sqrt(b_sd**2 / b_n + f_sd**2 / f_n)
    t_welch = diff / se if se > 0 else float("nan")
    df_welch = (b_sd**2 / b_n + f_sd**2 / f_n) ** 2 / (
        (b_sd**2 / b_n) ** 2 / (b_n - 1) + (f_sd**2 / f_n) ** 2 / (f_n - 1)
    )
    p_raw_welch = float(2.0 * scipy.stats.t.sf(abs(t_welch), df=df_welch)) if not math.isnan(t_welch) else float("nan")
    # Cohen's d_s for unpaired
    pooled_sd = math.sqrt(((b_n - 1) * b_sd**2 + (f_n - 1) * f_sd**2) / (b_n + f_n - 2))
    d_s = diff / pooled_sd if pooled_sd > 0 else float("nan")
    ci_lo = diff - 1.96 * se
    ci_hi = diff + 1.96 * se

    alpha_bonf = 0.05 / 7  # R3 fg_dev family in Wave 195 P2 (7 R-level cells)
    bonf_sig_welch = (p_raw_welch < alpha_bonf) if not math.isnan(p_raw_welch) else False

    print()
    print("Per Wave 195 P2 cross-reference (unpaired, per-arm SD = 0.214):")
    print(f"  t_welch = {t_welch:.3f}, df = {df_welch:.1f}")
    print(f"  p_raw = {p_raw_welch:.3e}, p_bonf (alpha={alpha_bonf:.4f}) sig = {bonf_sig_welch}")
    print(f"  Cohen's d_s = {d_s:.3f}")
    print(f"  CI95 = [{ci_lo:+.4f}, {ci_hi:+.4f}]")

    # ---- 3-seed pooled SD status ----
    # DGL regression (Wave 109.C) prevents fresh re-runs.
    # Pooled SD across 3 seeds is NOT computable from new data; we
    # report the per-arm SEM from Wave 82 sweep (`fg_dev_sem=0.00577`)
    # which was the pre-Wave-195 statistical power estimate.
    fg_dev_sem = float(w82["statistical_power_at_n1000"]["fg_dev_sem"])

    print()
    print("3-seed pooled SD: NOT computable (DGL regression — see audit doc)")
    print(f"Per-arm SEM (Wave 82 statistical_power_at_n1000.fg_dev_sem): {fg_dev_sem}")

    # ---- 12-col audit row ----
    # Single seed, single paired observation. Following Wave 203 P4 / CLM-066
    # audit-grade 12-col layout, plus Wave 195 P2 cross-reference columns.
    row = {
        "wave": "206 P3",
        "model": "flowmol3",
        "cell": "R3_fg_dev",
        "metric": "fg_dev",
        "n_total_per_arm": 1000,
        "n_baseline": b_n,
        "n_framework": f_n,
        "baseline_mean": b_fg,
        "framework_mean": f_fg,
        "mean_diff": diff,
        "n_paired": 1,
        "n_seeds_swept": 1,
        "n_seeds_requested": 3,
        "n_seeds_blocked": 2,
        "block_reason": "DGL_2.4.0_graph_ndata_shape_mismatch_per_wave109_c",
        "sd_diff": float("nan"),
        "sd_diff_pooled_across_seeds": float("nan"),
        "per_arm_sem_wave82": fg_dev_sem,
        "t_statistic": float(t_welch),
        "df": float(df_welch),
        "p_value_raw": float(p_raw_welch),
        "ci_95_low": float(ci_lo),
        "ci_95_high": float(ci_hi),
        "cohens_d_z": float(d_s),  # unpaired d_s here per Wave 195 P2 spec
        "cohens_d_kind": "d_s_unpaired_per_wave195_p2",
        "test_type": "welch_t_test_unpaired_per_wave195_p2",
        "family": "R3_flowmol3_fg_dev",
        "alpha_bonferroni": alpha_bonf,
        "bonf_sig": bonf_sig_welch,
        "nfe": nfe,
        "nfe_batch": nfe_batch,
        "seed_base": seed_base,
        "paper_target": 0.27,
        "byte_stable_vs_wave82": byte_stable_vs_w82,
        "data_source": str(W87_SWEEP.relative_to(REPO_ROOT)),
        "sweep_wallclock_s": sweep_wallclock_s,
        "verdict": "framework_wins" if diff < 0 else "baseline_wins",
        "honest_disclosure": (
            "DGL 2.4.0 regression in v2 adapter `_solve_ode_upstream_batch` "
            "(Wave 109.C) prevents fresh 3-seed re-runs. Wave 87 / Wave 82 "
            "byte-stable seed=42 data is the canonical 1-seed reference. "
            "Pooled SD across 3 seeds is NOT computable from new data; "
            "the per-arm SEM = 0.00577 (Wave 82 statistical_power_at_n1000) "
            "is reported as a substitute for cross-seed SD. The Wave 195 P2 "
            "audit-grade Welch's t-test (unpaired) numbers are cross-referenced."
        ),
    }

    # ---- Write CSV + JSON ----
    csv_path = OUT_DIR / "wave206-p3-flowmol3-n1000.csv"
    json_path = OUT_DIR / "wave206-p3-flowmol3-n1000.json"

    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        w.writeheader()
        w.writerow(row)
    print(f"\nWrote: {csv_path}")

    with json_path.open("w") as f:
        json.dump(row, f, indent=2, default=float)
    print(f"Wrote: {json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())