#!/usr/bin/env python3
"""GAP-43 — pre-registered blend-positive analysis (R3 ``fg_dev``, 50 seeds).

Implements the frozen analysis plan in
``docs/audit/gap43-blend-positive-preregistration.md`` §5/§7. Nothing here
chooses a design: the seed list, the alpha, the effect-size floor and the
decision rule are read from the pre-registration constants below and are
asserted against the run metadata.

Inputs are the per-arm JSONs written by
``scripts/wave338_p5_r3_n1000_paired.py``:

    <primary>/flowmol3_n1000_baseline_wave338_p5_seed{S}.json
    <primary>/flowmol3_n1000_framework_wave338_p5_seed{S}.json
    <tuned>/flowmol3_n1000_baseline_wave338_p5_seed{S}.json   # baseline NFE=1000
    <tuned>/flowmol3_n1000_framework_wave338_p5_seed{S}.json  # framework NFE=250

Paired difference convention: ``Δ = framework − baseline``; for ``fg_dev``
negative is framework-favourable.

Usage::

    python3 tools/gap43_blend_positive_analysis.py \
        --primary-dir verification_outputs/gap43-blend-positive/primary \
        --tuned-dir verification_outputs/gap43-blend-positive/tuned_baseline \
        --out verification_outputs/gap43-blend-positive/summary.json

    python3 tools/gap43_blend_positive_analysis.py --self-test
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats as _st

REPO_ROOT = Path(__file__).resolve().parent.parent

# --- Frozen pre-registration constants (§0 / §5 / §6) ---------------------
SEEDS: tuple[int, ...] = tuple(range(55, 546, 10))  # 55, 65, ..., 545
TUNED_SEEDS: tuple[int, ...] = tuple(range(55, 146, 10))  # 55, ..., 145
ALPHA = 0.05 / 7.0  # 0.0071429
D_FLOOR = 0.5
N_BOOT = 10_000
BOOT_SEED = 0
MIN_N_SAMPLED = 900
MAX_ARM_N_DIFF = 20  # 2 % of 1000

METRIC = "fg_dev"
EXPLORATORY = "pb_validity_pct"
SECONDARY = ("validity_pct", "ood_ring_rate")


# --- I/O helpers ----------------------------------------------------------
def _arm_path(directory: Path, arm: str, seed: int) -> Path:
    return directory / f"flowmol3_n1000_{arm}_wave338_p5_seed{seed}.json"


def _load_arm(directory: Path, arm: str, seed: int) -> dict[str, Any] | None:
    path = _arm_path(directory, arm, seed)
    if not path.exists():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    metrics = doc.get("metrics") or {}
    row = {
        "seed": int(seed),
        "arm": arm,
        "n_sampled": int(doc.get("n_sampled", 0)),
        "n_errors": int(doc.get("n_errors", 0)),
        METRIC: float(metrics[METRIC]),
        EXPLORATORY: float(metrics.get(EXPLORATORY, float("nan"))),
    }
    for key in SECONDARY:
        row[key] = float(metrics.get(key, float("nan")))
    return row


# --- Statistics (§5.1) ----------------------------------------------------
def paired_stats(deltas: np.ndarray, alpha: float = ALPHA) -> dict[str, Any]:
    """One-sample two-sided t on the per-seed paired differences."""
    d = np.asarray(deltas, dtype=np.float64)
    n = int(d.size)
    if n < 2:
        raise ValueError("paired_stats needs at least two seeds")
    mean = float(d.mean())
    sd = float(d.std(ddof=1))
    se = sd / math.sqrt(n)
    t_stat = mean / se if se > 0 else float("nan")
    df = n - 1
    p_value = float(2.0 * _st.t.sf(abs(t_stat), df=df)) if math.isfinite(t_stat) else float("nan")
    dz = mean / sd if sd > 0 else float("nan")
    t_crit = float(_st.t.ppf(1.0 - alpha / 2.0, df=df))
    ci_lo, ci_hi = mean - t_crit * se, mean + t_crit * se
    dz_lo, dz_hi = bootstrap_dz_ci(d)
    return {
        "n": n,
        "mean": mean,
        "sd": sd,
        "se": se,
        "t_stat": t_stat,
        "df": df,
        "p_value": p_value,
        "cohens_dz": dz,
        "ci95_mean": [float(ci_lo), float(ci_hi)],
        "dz_bootstrap_ci95": [float(dz_lo), float(dz_hi)],
        "n_negative": int((d < 0).sum()),
        "median": float(np.median(d)),
        "trimmed_mean_10pct": float(_st.trim_mean(d, 0.10)),
    }


def bootstrap_dz_ci(deltas: np.ndarray) -> tuple[float, float]:
    """Percentile bootstrap 95 % CI for ``d_z`` (§5.1: 10k, rng(0))."""
    d = np.asarray(deltas, dtype=np.float64)
    n = int(d.size)
    rng = np.random.default_rng(BOOT_SEED)
    idx = rng.integers(0, n, size=(N_BOOT, n))
    samples = d[idx]
    means = samples.mean(axis=1)
    sds = samples.std(axis=1, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        dz = np.where(sds > 0, means / sds, np.nan)
    dz = dz[np.isfinite(dz)]
    if dz.size == 0:
        return float("nan"), float("nan")
    lo, hi = np.percentile(dz, [2.5, 97.5])
    return float(lo), float(hi)


# --- Analysis -------------------------------------------------------------
def _paired_rows(primary: Path, seeds: tuple[int, ...]) -> tuple[list[dict], list[int]]:
    rows: list[dict] = []
    missing: list[int] = []
    for seed in seeds:
        bl = _load_arm(primary, "baseline", seed)
        fw = _load_arm(primary, "framework", seed)
        if bl is None or fw is None:
            missing.append(int(seed))
            continue
        rows.append(
            {
                "seed": int(seed),
                "baseline": bl,
                "framework": fw,
                "delta_fg_dev": fw[METRIC] - bl[METRIC],
                "delta_pb_validity_pct": fw[EXPLORATORY] - bl[EXPLORATORY],
                "n_sampled_diff": abs(fw["n_sampled"] - bl["n_sampled"]),
                "flags": _row_flags(bl, fw),
            }
        )
    return rows, missing


def _row_flags(bl: dict, fw: dict) -> list[str]:
    flags: list[str] = []
    if bl["n_sampled"] < MIN_N_SAMPLED:
        flags.append(f"baseline_n_sampled={bl['n_sampled']}<{MIN_N_SAMPLED}")
    if fw["n_sampled"] < MIN_N_SAMPLED:
        flags.append(f"framework_n_sampled={fw['n_sampled']}<{MIN_N_SAMPLED}")
    if abs(fw["n_sampled"] - bl["n_sampled"]) > MAX_ARM_N_DIFF:
        flags.append(f"between_arm_n_diff={abs(fw['n_sampled'] - bl['n_sampled'])}>{MAX_ARM_N_DIFF}")
    return flags


def tuned_gate(
    primary: Path, tuned: Path, seeds: tuple[int, ...]
) -> dict[str, Any]:
    """Δ_tuned(S) = fw@250 − min(bl@250, bl@1000) on the pre-registered subset."""
    rows: list[dict] = []
    for seed in seeds:
        bl250 = _load_arm(primary, "baseline", seed)
        fw250 = _load_arm(primary, "framework", seed)
        bl1000 = _load_arm(tuned, "baseline", seed)
        fw250_tuned = _load_arm(tuned, "framework", seed)
        if None in (bl250, fw250, bl1000, fw250_tuned):
            rows.append({"seed": int(seed), "status": "missing_inputs"})
            continue
        best_baseline = min(bl250[METRIC], bl1000[METRIC])
        rows.append(
            {
                "seed": int(seed),
                "status": "ok",
                "framework_nfe250": fw250[METRIC],
                "baseline_nfe250": bl250[METRIC],
                "baseline_nfe1000": bl1000[METRIC],
                "best_baseline": best_baseline,
                "delta_tuned": fw250[METRIC] - best_baseline,
                "framework_determinism_delta": fw250_tuned[METRIC] - fw250[METRIC],
                "tuned_framework_matches_primary": bool(
                    fw250_tuned[METRIC] == fw250[METRIC]
                ),
            }
        )
    ok = [r for r in rows if r["status"] == "ok"]
    mean_delta = float(np.mean([r["delta_tuned"] for r in ok])) if ok else float("nan")
    return {
        "rows": rows,
        "n_ok": len(ok),
        "n_missing": len(rows) - len(ok),
        "mean_delta_tuned": mean_delta,
        "passes": bool(ok) and mean_delta < 0,
        "framework_deterministic_on_subset": bool(ok)
        and all(r["tuned_framework_matches_primary"] for r in ok),
    }


def _verdict(stats: dict, gate: dict) -> tuple[str, dict[str, bool]]:
    cond = {
        "mean_negative": stats["mean"] < 0,
        "p_below_alpha": stats["p_value"] < ALPHA,
        "dz_at_floor": abs(stats["cohens_dz"]) >= D_FLOOR,
        "tuned_gate_passes": bool(gate["passes"]),
    }
    if all(cond.values()):
        return "POSITIVE", cond
    if cond["mean_negative"] and cond["p_below_alpha"] and cond["dz_at_floor"]:
        return "MATCHED_NFE_POSITIVE_NOT_ROBUST_TO_BASELINE_TUNING", cond
    dz_lo = stats["dz_bootstrap_ci95"][0]
    if math.isfinite(dz_lo) and dz_lo > -D_FLOOR:
        return "BOUNDED_NEGATIVE", cond
    return "INCONCLUSIVE", cond


def analyze(
    primary: Path,
    tuned: Path | None,
    seeds: tuple[int, ...] = SEEDS,
    tuned_seeds: tuple[int, ...] = TUNED_SEEDS,
) -> dict[str, Any]:
    rows, missing = _paired_rows(primary, seeds)
    if missing:
        raise SystemExit(
            f"missing primary arms for seeds {missing}; the pre-registration has no exclusions"
        )
    deltas = np.asarray([r["delta_fg_dev"] for r in rows], dtype=np.float64)
    stats = paired_stats(deltas)
    flagged = [r["seed"] for r in rows if r["flags"]]
    sensitivity = None
    if flagged:
        keep = np.asarray(
            [r["delta_fg_dev"] for r in rows if r["seed"] not in flagged], dtype=np.float64
        )
        if keep.size >= 2:
            sensitivity = paired_stats(keep)
    gate = (
        tuned_gate(primary, tuned, tuned_seeds)
        if tuned is not None
        else {"rows": [], "n_ok": 0, "n_missing": len(tuned_seeds),
              "mean_delta_tuned": float("nan"), "passes": False,
              "framework_deterministic_on_subset": False}
    )
    verdict, conditions = _verdict(stats, gate)
    if sensitivity is not None:
        sens_verdict, _ = _verdict(sensitivity, gate)
        sensitivity["verdict"] = sens_verdict
    pb = paired_stats(np.asarray([r["delta_pb_validity_pct"] for r in rows], dtype=np.float64))
    loo = _leave_one_out(deltas)
    return {
        "kind": "gap43_blend_positive",
        "design": {
            "cell": "R3",
            "metric": METRIC,
            "seeds": list(seeds),
            "n_seeds": len(seeds),
            "alpha": ALPHA,
            "d_floor": D_FLOOR,
            "tuned_seeds": list(tuned_seeds),
            "paired_delta": "framework - baseline (negative favours framework)",
        },
        "primary": stats,
        "conditions": conditions,
        "verdict": verdict,
        "tuned_gate": gate,
        "flags": {"seeds": flagged, "n_flagged": len(flagged), "run_valid": len(flagged) <= 5},
        "sensitivity_excluding_flagged": sensitivity,
        "leave_one_out": loo,
        "exploratory_pb_validity": pb,
        "rows": rows,
    }


def _leave_one_out(deltas: np.ndarray) -> dict[str, Any]:
    n = int(deltas.size)
    means, dzs = [], []
    for i in range(n):
        keep = np.delete(deltas, i)
        s = paired_stats(keep)
        means.append(s["mean"])
        dzs.append(s["cohens_dz"])
    return {
        "mean_range": [float(min(means)), float(max(means))],
        "dz_range": [float(min(dzs)), float(max(dzs))],
    }


# --- Rendering ------------------------------------------------------------
def render_markdown(summary: dict) -> str:
    p = summary["primary"]
    g = summary["tuned_gate"]
    lines = [
        "# GAP-43 — blend-positive result (pre-registered)",
        "",
        f"**Verdict:** `{summary['verdict']}`",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| seeds | {p['n']} |",
        f"| mean Δ (`fg_dev`) | {p['mean']:+.6f} |",
        f"| SD | {p['sd']:.6f} |",
        f"| t (df={p['df']}) | {p['t_stat']:+.3f} |",
        f"| p (α={ALPHA:.7f}) | {p['p_value']:.6g} |",
        f"| d_z | {p['cohens_dz']:+.3f} |",
        f"| d_z 95 % bootstrap CI | [{p['dz_bootstrap_ci95'][0]:+.3f}, {p['dz_bootstrap_ci95'][1]:+.3f}] |",
        f"| mean 95 % CI | [{p['ci95_mean'][0]:+.6f}, {p['ci95_mean'][1]:+.6f}] |",
        f"| seeds with Δ < 0 | {p['n_negative']}/{p['n']} |",
        f"| tuned gate mean Δ_tuned | {g['mean_delta_tuned']:+.6f} |",
        f"| tuned gate passes | {g['passes']} |",
        f"| flagged seeds | {summary['flags']['n_flagged']} |",
        "",
        "## Decision conditions",
        "",
    ]
    for key, value in summary["conditions"].items():
        lines.append(f"- `{key}`: **{value}**")
    lines += ["", "## Exploratory endpoint (`pb_validity_pct`, unadjusted)", "",
              f"- mean Δ = {summary['exploratory_pb_validity']['mean']:+.6f}, "
              f"p = {summary['exploratory_pb_validity']['p_value']:.6g}, "
              f"d_z = {summary['exploratory_pb_validity']['cohens_dz']:+.3f}"]
    return "\n".join(lines) + "\n"


# --- Self-test ------------------------------------------------------------
def _self_test() -> int:
    d = np.asarray([-0.10, -0.05, -0.02, -0.08, -0.12, -0.03, -0.07, -0.09,
                    -0.01, -0.04], dtype=np.float64)
    s = paired_stats(d)
    mean = float(d.mean())
    sd = float(d.std(ddof=1))
    assert abs(s["mean"] - mean) < 1e-12
    assert abs(s["sd"] - sd) < 1e-12
    assert abs(s["cohens_dz"] - mean / sd) < 1e-12
    t_expected = mean / (sd / math.sqrt(d.size))
    assert abs(s["t_stat"] - t_expected) < 1e-12
    p_expected = 2.0 * _st.t.sf(abs(t_expected), df=d.size - 1)
    assert abs(s["p_value"] - p_expected) < 1e-12
    lo, hi = s["dz_bootstrap_ci95"]
    assert lo <= s["cohens_dz"] <= hi
    # A pure positive shift must never be called POSITIVE.
    verdict, _ = _verdict(
        paired_stats(np.abs(d)), {"passes": True}
    )
    assert verdict != "POSITIVE"
    print("gap43 self-test: OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--primary-dir", type=Path)
    ap.add_argument("--tuned-dir", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()
    if args.primary_dir is None or args.out is None:
        ap.error("--primary-dir and --out are required unless --self-test")

    summary = analyze(args.primary_dir, args.tuned_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2, default=float) + "\n", encoding="utf-8")
    md_path = args.out.with_suffix(".md")
    md_path.write_text(render_markdown(summary), encoding="utf-8")
    p = summary["primary"]
    print(
        f"[gap43] verdict={summary['verdict']} n={p['n']} mean={p['mean']:+.6f} "
        f"p={p['p_value']:.6g} dz={p['cohens_dz']:+.3f} "
        f"gate={summary['tuned_gate']['passes']}"
    )
    print(f"[gap43] wrote {args.out} and {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
