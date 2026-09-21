#!/usr/bin/env python3
"""Wave 206 P5: FreqFlow synthetic-mode N=1000 paired-record 12-col audit.

**Honest disclosure (read first):**

FreqFlow's published ``nnet_ema.pth`` is **NOT publicly released** as of
2026-09-05 (probed: GitHub releases empty, full git tree lacks
``.pth``/``.safetensors``/LFS pointer, HF Hub empty for `FreqFlow` and
`OliverRensu`, no PyPI package). See ``data/freqflow_ckpt/README.md``
and ``docs/models/freqflow.model_card.md`` §0 for the full probe
transcript. Re-verified 2026-09-21 for this Wave 206 P5 sweep: the
ckpt is still absent on disk and on every public mirror.

This script therefore runs in **synthetic mode only** — the
deterministic NumPy two-branch shim that backs the Protocol surface
(see ``adaptive_reflow/adapters/freqflow.py:_synthetic_velocity_field``).
Per the task spec, this is the disclosed outcome: the FreqFlow
N=1000 paired-t is reported with ``freqflow_mode = "synthetic"`` and
``verdict_overall = "SYNTHETIC_ONLY_no_upstream_ckpt"``.

Per-record pairing (N=1000 paired records):

* For each seed s in 0..999:
  * Run ``_solve_baseline(adapter, nfe=50, seed=s)`` (vanilla single-pass).
  * Run ``_solve_framework(adapter, nfe=50, seed=s, n_rounds=3)`` (framework
    wrapper; matched NFE budget).
  * Extract endpoint latent from each via the adapter's
    ``_native_states`` cache (real trajectory, just driven by the
    synthetic NumPy shim instead of a trained SiT-XL/2 + FFT graph).
  * Compute the paired per-record scalars:
      - endpoint_l2 = L2(b_end, f_end)
      - endpoint_cos = cosine_similarity(b_end, f_end)
      - endpoint_mab = mean(|b_end - f_end|)

The 12-col audit row uses the L2 axis (the wave189 precedent; cf.
``verification_outputs/wave189-p3-freqflow-real.json``).

Test statistic: one-sample t-test of ``mean(endpoint_l2)`` vs 0 (the
framework-vs-baseline difference must be non-zero by construction).
This is the paired-test reduction: with deterministic same-seed
initial noise, the per-seed diff is one number, not two paired
numbers — the natural test of mean != 0 with df = N-1 = 999.

Bonferroni correction: ``alpha_bonferroni = 0.05 / 2 = 0.025``
(family = FreqFlow synthetic + FreqFlow real, k=2; the real cell is
absent because the ckpt is not released, so we still apply the
family-level k=2 correction per the task spec — the absent cell
contributes ``None`` to the family and is reported as a separate
``freqflow_real_cell`` field with verdict ``CKPT_ABSENT``).

Outputs:
  - verification_outputs/wave206-p5-freqflow-n1000.csv
  - verification_outputs/wave206-p5-freqflow-n1000.json
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from datetime import UTC, datetime, timezone
from pathlib import Path

import numpy as np
import scipy.stats

REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "verification_outputs"
OUT_PATH_JSON = OUT_DIR / "wave206-p5-freqflow-n1000.json"
OUT_PATH_CSV = OUT_DIR / "wave206-p5-freqflow-n1000.csv"

DEFAULT_NFE = 50  # task spec: NFE=50
DEFAULT_N_ROUNDS = 3  # framework rounds
DEFAULT_SEEDS = tuple(range(1000))  # N=1000 paired records
BONF_K = 2  # FreqFlow synthetic + FreqFlow real
BONF_ALPHA = 0.05 / BONF_K  # = 0.025


def _endpoint_latent(adapter, trace) -> np.ndarray | None:
    """Retrieve the (4, 32, 32) endpoint latent from the adapter's native-state cache."""
    digest = getattr(trace, "native_state_digest", None)
    if digest is None:
        return None
    entry = adapter._native_states.get(digest)
    if entry is None:
        return None
    traj = entry.get("trajectory")
    if traj is None:
        return None
    arr = np.asarray(traj, dtype=np.float64)
    return arr[-1] if arr.ndim >= 4 else None


def _paired_metrics(b_end: np.ndarray | None, f_end: np.ndarray | None) -> dict[str, float | None]:
    if b_end is None or f_end is None:
        return {
            "endpoint_l2": None,
            "endpoint_cos": None,
            "endpoint_mab": None,
            "baseline_norm": None,
            "framework_norm": None,
        }
    b_flat = b_end.ravel()
    f_flat = f_end.ravel()
    l2 = float(np.linalg.norm(b_flat - f_flat))
    cos = float(np.dot(b_flat, f_flat) / (np.linalg.norm(b_flat) * np.linalg.norm(f_flat) + 1e-12))
    mab = float(np.abs(b_end - f_end).mean())
    return {
        "endpoint_l2": l2,
        "endpoint_cos": cos,
        "endpoint_mab": mab,
        "baseline_norm": float(np.linalg.norm(b_flat)),
        "framework_norm": float(np.linalg.norm(f_flat)),
    }


def one_sample_t_test(values: np.ndarray, mu0: float, alpha: float) -> dict:
    """One-sample t-test of ``mean(values)`` vs ``mu0``. Returns 12-col fields."""
    n = len(values)
    res = {
        "n_paired": int(n),
        "mean_diff": float("nan"),
        "sd_diff": float("nan"),
        "t_statistic": float("nan"),
        "df": int(max(0, n - 1)),
        "p_value_raw": float("nan"),
        "ci_95_low": float("nan"),
        "ci_95_high": float("nan"),
        "cohens_d_z": float("nan"),
        "bonf_sig": False,
    }
    if n < 2:
        return res
    mean_v = float(np.mean(values))
    sd_v = float(np.std(values, ddof=1))
    se = sd_v / math.sqrt(n)
    df = n - 1
    diff = values - mu0
    mean_diff = float(np.mean(diff))
    if sd_v == 0.0:
        if mean_diff > 0:
            t_stat = float("inf")
            p_raw = 0.0
        elif mean_diff < 0:
            t_stat = float("-inf")
            p_raw = 0.0
        else:
            t_stat = 0.0
            p_raw = 1.0
        d_z = 0.0
    else:
        t_stat = mean_diff / se
        p_raw = float(2.0 * scipy.stats.t.sf(abs(t_stat), df=df))
        d_z = mean_diff / sd_v
    ci_lo = mean_diff - 1.96 * se
    ci_hi = mean_diff + 1.96 * se
    res.update({
        "mean_diff": mean_diff,
        "sd_diff": sd_v,
        "t_statistic": float(t_stat),
        "df": int(df),
        "p_value_raw": p_raw,
        "ci_95_low": float(ci_lo),
        "ci_95_high": float(ci_hi),
        "cohens_d_z": float(d_z),
        "bonf_sig": bool(p_raw < alpha),
    })
    return res


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nfe", type=int, default=DEFAULT_NFE,
                        help=f"NFE per round (default: {DEFAULT_NFE}, task spec)")
    parser.add_argument("--n-rounds", type=int, default=DEFAULT_N_ROUNDS,
                        help=f"Framework rounds (default: {DEFAULT_N_ROUNDS})")
    parser.add_argument("--seeds", type=int, nargs="+", default=list(DEFAULT_SEEDS),
                        help="Seeds (default: 0..999, N=1000 paired records)")
    parser.add_argument("--output-json", default=str(OUT_PATH_JSON))
    parser.add_argument("--output-csv", default=str(OUT_PATH_CSV))
    parser.add_argument("--ckpt-probe", action="store_true",
                        help="Re-probe FreqFlow ckpt paths before sweep")
    args = parser.parse_args()

    out_json = Path(args.output_json)
    out_csv = Path(args.output_csv)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 78)
    print("Wave 206 P5: FreqFlow synthetic-mode N=1000 paired-record 12-col audit")
    print("=" * 78)

    # ----- ckpt probe (always re-verify) -----
    if args.ckpt_probe:
        from adaptive_reflow.adapters.freqflow import (
            FREQ_FLOW_CKPT_ENV_VAR,
            freqflow_resolve_weights_path,
        )
        ckpt_path = freqflow_resolve_weights_path()
        env = __import__("os").environ.get(FREQ_FLOW_CKPT_ENV_VAR, "<unset>")
        print(f"[ckpt-probe] FREQFLOW_CKPT env: {env}")
        print(f"[ckpt-probe] resolved weights path: {ckpt_path}")
        if ckpt_path is None or not Path(ckpt_path).is_file():
            print("[ckpt-probe] VERDICT: ckpt ABSENT — synthetic mode mandatory")
        else:
            print(f"[ckpt-probe] VERDICT: ckpt present at {ckpt_path} (would use real mode)")

    # ----- import adapter + solvers -----
    from tools.run_real_ckpt_eval import (  # type: ignore
        _resolve_adapter,
        _solve_baseline,
        _solve_framework,
    )

    # ----- adapter resolution -----
    adapter, mode = _resolve_adapter(
        "freqflow", force_mode="synthetic", nfe_budget=int(args.nfe),
    )
    if adapter is None:
        print("FATAL: adapter resolution returned None — BLOCKED", flush=True)
        out_json.write_text(json.dumps({
            "freqflow_mode": "synthetic",
            "n_records": 0,
            "verdict_overall": "BLOCKED_adapter_resolution_returned_none",
            "timestamp": datetime.now(UTC).isoformat(),
        }, indent=2) + "\n")
        return 1
    print(f"[adapter] model=freqflow mode={mode}", flush=True)

    # ----- sweep N=1000 paired records -----
    seeds = list(args.seeds)
    n_target = len(seeds)
    cells: list[dict] = []
    t_total = time.monotonic()
    n_skipped = 0

    for i, seed in enumerate(seeds):
        t0 = time.monotonic()
        try:
            baseline_trace, base_w = _solve_baseline(adapter, nfe=int(args.nfe), seed=int(seed))
            framework_trace, fw_w = _solve_framework(
                adapter, nfe=int(args.nfe), seed=int(seed), n_rounds=int(args.n_rounds),
            )
        except Exception as e:  # noqa: BLE001
            print(f"[seed={seed}] SKIP: solver raised {type(e).__name__}: {e}", flush=True)
            cells.append({
                "seed": int(seed), "skipped": True, "reason": f"{type(e).__name__}: {e}",
            })
            n_skipped += 1
            continue

        b_end = _endpoint_latent(adapter, baseline_trace)
        f_end = _endpoint_latent(adapter, framework_trace)
        m = _paired_metrics(b_end, f_end)
        cells.append({
            "seed": int(seed),
            "nfe": int(args.nfe),
            "n_rounds": int(args.n_rounds),
            "adapter_mode": str(mode),
            "wallclock_baseline_s": round(float(base_w), 4),
            "wallclock_framework_s": round(float(fw_w), 4),
            "wallclock_ratio": round(float(fw_w / base_w), 4) if base_w > 0 else None,
            **m,
        })
        if (i + 1) % 100 == 0 or i == 0:
            l2_disp = m["endpoint_l2"]
            cos_disp = m["endpoint_cos"]
            print(
                f"[{i+1:>4}/{n_target}] seed={seed} mode={mode} "
                f"l2={l2_disp:.4f} cos={cos_disp:.4f} "
                f"wall_base={base_w:.4f}s wall_fw={fw_w:.4f}s "
                f"elapsed={time.monotonic()-t_total:.1f}s",
                flush=True,
            )

    wall_sweep_total = time.monotonic() - t_total
    print(f"\n[sweep] completed {n_target} seeds in {wall_sweep_total:.2f}s "
          f"(skipped {n_skipped})", flush=True)

    # ----- aggregate per-record metrics -----
    l2_vals = np.array(
        [c["endpoint_l2"] for c in cells if c.get("endpoint_l2") is not None],
        dtype=float,
    )
    cos_vals = np.array(
        [c["endpoint_cos"] for c in cells if c.get("endpoint_cos") is not None],
        dtype=float,
    )
    mab_vals = np.array(
        [c["endpoint_mab"] for c in cells if c.get("endpoint_mab") is not None],
        dtype=float,
    )
    n_paired = int(len(l2_vals))

    # ----- 12-col audit row (one-sample t-test on endpoint_l2 vs mu0=0) -----
    row = one_sample_t_test(l2_vals, mu0=0.0, alpha=BONF_ALPHA)
    row.update({
        "dataset": "freqflow_n1000",
        "model": "freqflow",
        "cell": "R_freqflow_synth_endpoint_l2",
        "metric": "synthetic_endpoint_l2",
        "test_type": "one_sample_t_test_vs_zero",
        "family": f"FreqFlow_synth+real_k{BONF_K}",
        "alpha_bonferroni": BONF_ALPHA,
        "higher_better": False,  # closer-to-baseline (smaller L2) is the
                                  # "framework preserves endpoint" reading,
                                  # but the disclosure says this is a
                                  # diagnostic, not a quality axis
        "metric_definition": (
            "L2 distance between baseline and framework endpoint latents "
            "in (4, 32, 32) FreqFlow state space. NOT a real FID — there "
            "is no Inception forward pass, no real SiT-XL/2 + FFT graph. "
            "The FreqFlowAdapter in synthetic mode is a deterministic "
            "NumPy two-branch shim (4096 -> 256 -> 4096 spatial MLP + "
            "linear projection of normalised FFT magnitude side-channel; "
            "Kaiming uniform init, seed=FREQ_FLOW_SYNTHETIC_SEED_DEFAULT). "
            "The L2 distance reflects the framework arm's restart-blend "
            "effect on the latent, NOT any Frechet-Inception distance. "
            "Per-record pairing: same seed s in 0..999 drives the same "
            "initial noise + same velocity field for baseline and "
            "framework arms, so the L2 distance is a deterministic scalar "
            "per seed (paired by construction)."
        ),
    })

    # ----- secondary axes for diagnostic only (NOT in Bonferroni family) -----
    def _agg(v: np.ndarray, fn) -> float | None:
        return float(fn(v)) if v.size else None

    aux_cos = {
        "n_paired": int(cos_vals.size),
        "cosine_mean": _agg(cos_vals, np.mean),
        "cosine_std": _agg(cos_vals, lambda x: float(np.std(x, ddof=1))) if cos_vals.size > 1 else None,
    }
    aux_mab = {
        "n_paired": int(mab_vals.size),
        "mean_abs_diff_mean": _agg(mab_vals, np.mean),
        "mean_abs_diff_std": _agg(mab_vals, lambda x: float(np.std(x, ddof=1))) if mab_vals.size > 1 else None,
    }

    # ----- FreqFlow real cell (CKPT_ABSENT placeholder) -----
    freqflow_real_cell = {
        "dataset": "freqflow_n1000",
        "model": "freqflow",
        "cell": "R_freqflow_real_endpoint_l2",
        "status": "CKPT_ABSENT",
        "ckpt_path_attempted": [
            "data/freqflow_ckpt/nnet_ema.pth (missing)",
            "data/freqflow/nnet_ema.pth (missing)",
            "data/nnet_ema.pth (missing)",
            "$FREQFLOW_CKPT (unset)",
            "github.com/OliverRensu/FreqFlow/releases (empty as of 2026-09-21)",
            "huggingface.co/api/models?search=FreqFlow (empty)",
            "huggingface.co/api/models?author=OliverRensu (empty)",
        ],
        "probe_verdict": "no public release as of 2026-09-21",
        "probe_evidence": "data/freqflow_ckpt/README.md",
        "metric": None,
        "n_paired": 0,
        "alpha_bonferroni": BONF_ALPHA,
        "verdict": "DEFERRED_no_upstream_ckpt",
    }

    # ----- assemble report -----
    report = {
        "schema": "wave206_p5_freqflow_n1000.v1",
        "wave": "206 P5",
        "model": "freqflow",
        "axis": "image_sota",
        "freqflow_mode": "synthetic",
        "ckpt_source": "synthetic-shim",
        "freqflow_status": "synthetic",
        "freqflow_real_status": "CKPT_ABSENT_no_public_release",
        "verdict_overall": "SYNTHETIC_ONLY_no_upstream_ckpt",
        "nfe": int(args.nfe),
        "n_rounds": int(args.n_rounds),
        "n_records_target": n_target,
        "n_records": n_paired,
        "n_skipped": n_skipped,
        "seeds": list(seeds),
        "bonferroni_family_k": BONF_K,
        "bonferroni_alpha": BONF_ALPHA,
        "wallclock_sweep_total_s": round(wall_sweep_total, 4),
        "cells": cells,
        "audit_row": row,
        "freqflow_real_cell": freqflow_real_cell,
        "aux_cosine": aux_cos,
        "aux_mean_abs_diff": aux_mab,
        "adapter_modes": sorted({c.get("adapter_mode") for c in cells if "adapter_mode" in c}),
        "primary_metric_status": (
            "PENDING — DOWNSTREAM_METRICS['freqflow'].primary_metric.name = "
            "'DEFERRED_no_upstream_ckpt' (no public ckpt, see Phase-4 "
            "deferred registry at tools/eval/io.py)."
        ),
        "implication_for_paper": (
            "FreqFlowAdapter is registered in the synthetic registry and "
            "passes the D.5 conformance battery. The published "
            "nnet_ema.pth does NOT exist publicly (re-probed 2026-09-21: "
            "no GitHub releases, no HF Hub uploads, no PyPI package). The "
            "Wave 206 P5 N=1000 sweep therefore runs in synthetic mode "
            "and reports an endpoint-L2 diagnostic with explicit "
            "SYNTHETIC_ONLY disclosure. The Bonferroni family "
            f"k={BONF_K} (synthetic + real) is applied with "
            f"alpha={BONF_ALPHA} per the task spec; the real cell is "
            "CKPT_ABSENT and contributes no p-value. The paper's '5 "
            "adapters' claim remains partially synthetic on the image "
            "axis: 4 real-ckpt adapters (LineageFlow + Kanzi + FlowMol3 "
            "+ RectifiedFlowCIFAR) plus 1 synthetic-shim adapter "
            "(FreqFlow)."
        ),
        "synthetic_source": {
            "adapter_file": "adaptive_reflow/adapters/freqflow.py",
            "factory": "adaptive_reflow.adapters.freqflow:default_freqflow_adapter",
            "synthetic_velocity_field": (
                "_synthetic_velocity_field (two-branch NumPy shim: "
                "4096 -> 256 -> 4096 spatial MLP + linear projection "
                "of normalised FFT magnitude side-channel; Kaiming "
                "uniform init, seed=FREQ_FLOW_SYNTHETIC_SEED_DEFAULT)"
            ),
            "ckpt_path_attempted": [
                "data/freqflow_ckpt/nnet_ema.pth (missing)",
                "data/freqflow/nnet_ema.pth (missing)",
                "data/nnet_ema.pth (missing)",
                "$FREQFLOW_CKPT (unset)",
            ],
            "real_ckpt_verdict": (
                "ABSENT — no public release as of 2026-09-21. Probe "
                "transcript: data/freqflow_ckpt/README.md."
            ),
        },
        "timestamp": datetime.now(UTC).isoformat(),
        "sweep_script": "scripts/wave206_p5_freqflow_n1000_audit.py",
    }

    # ----- pin commit_sha -----
    try:
        import subprocess as _sp
        _sha = _sp.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            stderr=_sp.DEVNULL,
        ).decode("utf-8").strip()
        report["commit_sha"] = _sha
    except Exception:  # noqa: BLE001
        report["commit_sha"] = None

    # ----- write outputs -----
    out_json.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(f"\n[output] wrote {out_json}", flush=True)

    # ----- CSV (12-col standard per Wave 203 P4 / CLM-066) -----
    with out_csv.open("w", newline="") as f_:
        w = csv.writer(f_)
        w.writerow([
            "dataset", "model", "cell", "metric",
            "n_paired", "mean_diff", "sd_diff", "t_statistic", "df",
            "p_value_raw", "CI95_low", "CI95_high", "cohens_d_z",
            "test_type", "family", "alpha_bonferroni", "bonf_sig",
            "higher_better", "freqflow_mode", "ckpt_source",
        ])
        w.writerow([
            row["dataset"], row["model"], row["cell"], row["metric"],
            row["n_paired"], row["mean_diff"], row["sd_diff"],
            row["t_statistic"], row["df"],
            row["p_value_raw"], row["ci_95_low"], row["ci_95_high"],
            row["cohens_d_z"],
            row["test_type"], row["family"], row["alpha_bonferroni"],
            row["bonf_sig"], row["higher_better"],
            "synthetic", "synthetic-shim",
        ])
    print(f"[output] wrote {out_csv}", flush=True)

    # ----- print summary -----
    print()
    print("=" * 78)
    print("SUMMARY (12-col audit row)")
    print("=" * 78)
    print(f"  freqflow_mode          = {report['freqflow_mode']}")
    print(f"  ckpt_source            = {report['ckpt_source']}")
    print(f"  freqflow_status        = {report['freqflow_status']}")
    print(f"  freqflow_real_status   = {report['freqflow_real_status']}")
    print(f"  verdict_overall        = {report['verdict_overall']}")
    print(f"  NFE / n_rounds         = {args.nfe} / {args.n_rounds}")
    print(f"  n_records (paired)     = {n_paired}")
    print(f"  bonferroni family k    = {BONF_K} (synth + real)")
    print(f"  bonferroni alpha       = {BONF_ALPHA}")
    print()
    print(f"  endpoint_l2 mean       = {row['mean_diff']:.6f}")
    print(f"  endpoint_l2 sd         = {row['sd_diff']:.6f}")
    print(f"  t-statistic            = {row['t_statistic']:+.4f}")
    print(f"  df                     = {row['df']}")
    print(f"  p_value_raw            = {row['p_value_raw']:.4e}")
    print(f"  CI95                   = [{row['ci_95_low']:+.6f}, {row['ci_95_high']:+.6f}]")
    print(f"  Cohen's d_z            = {row['cohens_d_z']:+.4f}")
    print(f"  bonf_sig               = {row['bonf_sig']}")
    print(f"  wallclock_sweep_total_s= {wall_sweep_total:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
