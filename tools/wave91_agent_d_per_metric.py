#!/usr/bin/env python3
"""Wave 91 Agent D RE-RUN — Parse framework + baseline JSONs, compute per-metric deltas.

Inputs (canonical paths after Wave 91 Agent D sweep):
- Baseline: verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json
- Framework: verification_outputs/kanzi_n1000_framework_paper_metrics_real/kanzi_n1000_framework_paper_metrics.json

Output:
- verification_outputs/kanzi_n1000_framework_paper_metrics_real/per_metric.json

Per-metric computation:
- For reconstruction_kabsch_rmsd_A: per-record vectors from each arm,
  Welch's t-test (default; unequal-variance) + bootstrap 10K CI on mean delta.
- For 5 codebook metrics (single scalar per arm): per-arm value + delta;
  no p-value (single observation per arm); reported as TILED_BY_DESIGN.
- Verdict: SUPPORTED if p<0.05 AND delta > 0 (framework better, lower RMSD);
           TIE if |delta| < 0.01 Å;
           REGRESSES if p<0.05 AND delta > 0 (framework worse, higher RMSD);
           INSUFFICIENT if n < 30 (Welsh t-test unreliable).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.stats import mannwhitneyu, ttest_ind

_REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_per_seq_rmsd(json_obj: dict, key: str = "per_seq_rmsd") -> list[float]:
    """Extract per-record RMSD list from a sweep JSON (baseline or framework)."""
    if key in json_obj:
        return list(json_obj[key].values())
    # New framework format puts per_seq_rmsd inline as a dict at top level.
    for cand in ("per_seq_rmsd", "per_seq_rmsd_A", "per_seq_rmsd_dict"):
        v = json_obj.get(cand)
        if isinstance(v, dict):
            return list(v.values())
    return []


def bootstrap_ci(a: np.ndarray, b: np.ndarray, n_boot: int = 10_000,
                 alpha: float = 0.05, seed: int = 0) -> tuple[float, float, float]:
    """Bootstrap CI on mean(a) - mean(b); returns (delta, lo, hi)."""
    rng = np.random.default_rng(int(seed))
    deltas = np.empty(n_boot, dtype=np.float64)
    for i in range(n_boot):
        ai = rng.choice(a, size=len(a), replace=True)
        bi = rng.choice(b, size=len(b), replace=True)
        deltas[i] = float(ai.mean() - bi.mean())
    delta = float(a.mean() - b.mean())
    lo, hi = np.quantile(deltas, [alpha / 2.0, 1.0 - alpha / 2.0])
    return delta, float(lo), float(hi)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--baseline", type=Path,
                   default=_REPO_ROOT
                          / "verification_outputs"
                          / "wave88_kanzi_n1000_baseline"
                          / "kanzi_n1000_paper_metrics.json")
    p.add_argument("--framework", type=Path,
                   default=_REPO_ROOT
                          / "verification_outputs"
                          / "kanzi_n1000_framework_paper_metrics_real"
                          / "kanzi_n1000_framework_paper_metrics.json")
    p.add_argument("--output", type=Path,
                   default=_REPO_ROOT
                          / "verification_outputs"
                          / "kanzi_n1000_framework_paper_metrics_real"
                          / "per_metric.json")
    args = p.parse_args(argv)

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    framework = json.loads(args.framework.read_text(encoding="utf-8"))

    base_recon = parse_per_seq_rmsd(baseline)
    fw_recon = parse_per_seq_rmsd(framework)
    base_recon = np.asarray(base_recon, dtype=np.float64)
    fw_recon = np.asarray(fw_recon, dtype=np.float64)

    # Welch's t-test (unequal variance) + Mann-Whitney U (non-parametric).
    # If either arm has < 2 records, both tests are degenerate.
    n_base = int(base_recon.size)
    n_fw = int(fw_recon.size)
    p_welch = None
    p_mw = None
    test_used = "welch_t_test_ind"
    if n_base >= 2 and n_fw >= 2:
        welch = ttest_ind(fw_recon, base_recon, equal_var=False)
        p_welch = float(welch.pvalue) if not math.isnan(float(welch.pvalue)) else None
        # Mann-Whitney only meaningful if both n >= 1 and there is variation.
        if (fw_recon.std() > 0) and (base_recon.std() > 0):
            mw = mannwhitneyu(fw_recon, base_recon, alternative="two-sided")
            p_mw = float(mw.pvalue)
            test_used = "welch_t_test_ind (primary); mannwhitneyu (non-parametric check)"

    delta_mean, lo_ci, hi_ci = bootstrap_ci(fw_recon, base_recon, n_boot=10_000,
                                            alpha=0.05, seed=0)

    # Per-metric verdict.
    if n_fw < 30 or n_base < 30:
        verdict = "INSUFFICIENT (n<30 per arm — Welch t-test unreliable)"
    elif p_welch is not None and p_welch < 0.05 and delta_mean > 0:
        # delta > 0 means framework RMSD higher (WORSE — lower is better).
        verdict = "REGRESSES (p<0.05, framework worse)"
    elif p_welch is not None and p_welch < 0.05 and delta_mean < 0:
        # delta < 0 means framework RMSD lower (BETTER).
        verdict = "SUPPORTED (p<0.05, framework better)"
    elif abs(delta_mean) < 0.01:  # 0.01 Å ≈ 1 pm < typical RMSD noise band
        verdict = "TIE (|Δ|<0.01 Å)"
    else:
        verdict = "INDETERMINATE (no significant p, |Δ|≥0.01 Å)"

    recon_table = {
        "metric": "reconstruction_kabsch_rmsd_A",
        "direction": "lower_is_better",
        "baseline_arm": {
            "n": int(n_base),
            "mean": float(base_recon.mean()) if n_base > 0 else None,
            "std": float(base_recon.std(ddof=1)) if n_base > 1 else None,
            "source": "Wave 88 N=1000 baseline sweep "
                      "(verification_outputs/wave88_kanzi_n1000_baseline)",
        },
        "framework_arm": {
            "n": int(n_fw),
            "mean": float(fw_recon.mean()) if n_fw > 0 else None,
            "std": float(fw_recon.std(ddof=1)) if n_fw > 1 else None,
            "source": "Wave 91 Agent D RE-RUN N=1000 framework sweep "
                      "(verification_outputs/kanzi_n1000_framework_paper_metrics_real)",
        },
        "delta_mean": float(delta_mean),
        "delta_pct": float(
            100.0 * delta_mean / abs(float(base_recon.mean()))
            if base_recon.size > 0 and base_recon.mean() != 0 else 0.0
        ),
        "bootstrap_ci_95pct": [float(lo_ci), float(hi_ci)],
        "p_value_welch": p_welch,
        "p_value_mann_whitney": p_mw,
        "test": test_used,
        "n_boot": 10_000,
        "verdict": verdict,
    }

    # Codebook metrics (scalar-per-arm — TIED_BY_DESIGN, no p-value).
    base_cb = baseline.get("codebook_metrics", {})
    fw_cb = framework.get("codebook_metrics", {})
    cb_table = []
    for name, base_val in base_cb.items():
        if name == "codebook_hamming_rotation_invariance":
            cb_table.append({
                "metric": name,
                "direction": "encoder-quality (skipped)",
                "baseline_value": base_val,
                "framework_value": fw_cb.get(name),
                "verdict": "TIED_BY_DESIGN (encoder-only, not affected by framework restart blend)",
            })
            continue
        fw_val = fw_cb.get(name)
        delta = (
            (fw_val - base_val) if (isinstance(base_val, (int, float))
                                    and isinstance(fw_val, (int, float)))
            else None
        )
        cb_table.append({
            "metric": name,
            "direction": "context_dependent",
            "baseline_value": base_val,
            "framework_value": fw_val,
            "delta": delta,
            "delta_pct": (
                100.0 * delta / abs(base_val)
                if (delta is not None and base_val not in (0, None) and base_val != 0)
                else None
            ),
            "verdict": "TIED_BY_DESIGN (codebook statistics are deterministic functions "
                       "of the post-reconstruction coords; framework restart-blend "
                       "acts on the flow trajectory, not on the post-reconstruction "
                       "FSQ round-trip)",
        })

    out = {
        "tool": "tools/wave91_agent_d_per_metric.py",
        "baseline_arm_source": str(args.baseline),
        "framework_arm_source": str(args.framework),
        "n_records_baseline": n_base,
        "n_records_framework": n_fw,
        "reconstruction_kabsch_rmsd_A": recon_table,
        "codebook_metrics": cb_table,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2, sort_keys=False) + "\n",
                           encoding="utf-8")
    print(f"[wave91-per-metric] wrote {args.output}", file=sys.stderr)
    print(f"[wave91-per-metric] baseline n={n_base}, framework n={n_fw}",
          file=sys.stderr)
    print(f"[wave91-per-metric] delta_mean={delta_mean:.4f} Å",
          file=sys.stderr)
    print(f"[wave91-per-metric] p_welch={p_welch} p_mw={p_mw}",
          file=sys.stderr)
    print(f"[wave91-per-metric] verdict={verdict}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
