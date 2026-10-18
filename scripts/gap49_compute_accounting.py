#!/usr/bin/env python3
"""GAP-49 — measured compute ledger for the inference framework.

The manuscript's speed headline (2.5-10x) is a published-trajectory
extrapolation, not a measurement (`NFE_SPEEDUP_2P5_TO_10X_SOURCE.md`). This
script replaces it with what the committed artifacts can actually support:

1. a measured **baseline FID-vs-NFE curve** on CIFAR-10 RF (same checkpoint,
   no retraining);
2. the framework's committed FID at its canonical budget (NFE=50, GAP-12);
3. the **iso-FID NFE ratio**: the baseline NFE that matches each framework
   FID, divided by the framework NFE. A ratio > 1 means the framework saves
   compute; < 1 means it costs compute at matched quality.

Cells without a measured curve (R1 HMMER hits, R3 fg_dev) are reported as
``not_measured`` rather than estimated.

Usage::

    CUDA_VISIBLE_DEVICES=0 .venvs/flowmol3_venv/bin/python \\
        scripts/gap49_compute_accounting.py --baseline-nfes 5,10,20,25

``flowmol3_venv`` is the documented CIFAR environment (see
``reproduce/06_R5b_CIFAR_n_rounds1.sh``). The committed curve was produced in
one session whose interpreter was not captured at launch; the NFE=25 point was
re-produced under ``flowmol3_venv`` and agrees to 0.005 % in FID, so the ledger
is environment-robust (``METADATA.json`` §reproducibility_check).

HARD CONSTRAINT: one GPU only (``cuda:0``).
"""
from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "verification_outputs" / "gap49-compute-accounting"
CHECKPOINT = REPO_ROOT / "data" / "rectified_flow_cifar10.pth"
REF_FEATS_NPZ = REPO_ROOT / "data" / "cifar10_inception_features.npz"
GAP12_JSON = REPO_ROOT / "verification_outputs" / "gap12-tuned-baseline-cifar.json"
R6_CURVE = REPO_ROOT / "verification_outputs" / "nfe_curve_fair_w170_q3_2026" / "nfe_curve_fair.csv"
R3_MATCHED = (
    REPO_ROOT
    / "verification_outputs"
    / "r3_n1000_3seed_fixed_q4_2026"
    / "wave338-p5-r3-n1000-paired.json"
)
R3_TUNED_GLOB = "verification_outputs/gap12-r3-tuned-baseline-nfe*/flowmol3_n1000_sweep_wave338_p5_seed*.json"
R1_METADATA = REPO_ROOT / "verification_outputs" / "gap41b-r1-nfe-fidelity" / "METADATA.json"


def _load_w247():
    path = REPO_ROOT / "scripts" / "wave247_p2_r5b_multiseed.py"
    spec = importlib.util.spec_from_file_location("_w247_gap49", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _load_runner():
    path = REPO_ROOT / "tools" / "run_sota_cifar_experiment.py"
    spec = importlib.util.spec_from_file_location("_runner_gap49", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def run_baseline_curve(nfes: list[int], n_samples: int, seed: int) -> dict:
    runner = _load_runner()
    w247 = _load_w247()
    ref_feats = np.load(REF_FEATS_NPZ, allow_pickle=False)["features"].astype(np.float64)
    adapter = runner._make_adapter(
        CHECKPOINT, num_steps=max(nfes), solver="euler", device="cuda"
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    curve: dict[str, dict] = {}
    for nfe in nfes:
        run_dir = OUT_DIR / f"baseline-nfe{nfe}"
        path, wall = runner._run_baseline(
            adapter=adapter,
            n_samples=int(n_samples),
            num_steps=int(nfe),
            seed=int(seed),
            output_dir=run_dir,
        )
        cache = run_dir / "inception_feats_cache"
        feats = w247._load_or_compute_features(cache, "baseline", path)
        fid = float(w247._fid_numpy(feats, ref_feats))
        curve[str(nfe)] = {"fid": fid, "wall_seconds": float(wall), "source": "measured_here"}
        print(f"[gap49] baseline nfe={nfe}: FID={fid:.4f} wall={wall:.1f}s", flush=True)

    # Merge the committed GAP-12 baseline points (NFE 50/100/200) so the
    # iso-FID interpolation spans the full measured range without re-running.
    if GAP12_JSON.exists():
        gap12 = json.loads(GAP12_JSON.read_text())
        for nfe_key, row in gap12.get("per_baseline_nfe", {}).items():
            if nfe_key in curve:
                continue
            curve[nfe_key] = {
                "fid": float(row["baseline_fid"]),
                "wall_seconds": None,
                "source": "gap12_tuned_baseline",
            }
    return {
        "kind": "gap49_baseline_fid_curve",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "checkpoint": str(CHECKPOINT.relative_to(REPO_ROOT)),
        "device": "cuda:0",
        "n_samples": int(n_samples),
        "seed": int(seed),
        "curve": curve,
    }


def _interp_nfe_for_fid(curve: dict[str, dict], target_fid: float) -> float | None:
    """Piecewise-linear NFE at which the baseline reaches ``target_fid``.

    FID decreases with NFE on this checkpoint, so the crossing is unique when
    it exists. Returns ``None`` when the target is outside the measured range.
    """
    pts = sorted((int(k), float(v["fid"])) for k, v in curve.items())
    if not pts:
        return None
    if target_fid <= pts[-1][1] or target_fid >= pts[0][1]:
        return None
    for (n0, f0), (n1, f1) in zip(pts, pts[1:], strict=False):
        lo, hi = min(f0, f1), max(f0, f1)
        if lo <= target_fid <= hi and f0 != f1:
            frac = (target_fid - f0) / (f1 - f0)
            return float(n0 + frac * (n1 - n0))
    return None


def _crossing_sensitivity(curve: dict[str, dict], target_fid: float, delta: float) -> dict:
    """NFE crossings at ``target_fid -/+ delta``.

    FID at N=200 carries finite-sample noise, and the crossing is a ratio of
    two interpolated FID gaps, so the ratio inherits that noise. Reporting the
    crossing at ``target -/+ delta`` bounds how much a ``delta``-FID error
    moves the ledger without pretending the noise is known exactly.
    """
    better = _interp_nfe_for_fid(curve, target_fid - delta)  # lower FID -> more NFE
    worse = _interp_nfe_for_fid(curve, target_fid + delta)
    return {
        f"fid_minus_{delta:g}": better,
        f"fid_plus_{delta:g}": worse,
    }


def _r3_section() -> dict:
    """FlowMol3 (R3 fg_dev / K1 pb_validity) — matched-NFE deltas + sweep.

    The matched protocol is NFE=250 on both arms (``r3_n1000_3seed_fixed``).
    The GAP-12 dirs hold the *same* framework arm (fixed at 250) against a
    baseline given 500 and 1000 NFE, so the baseline quality-vs-NFE curve has
    three points and can be checked for monotonicity before any inversion.
    """
    out: dict = {
        "status": "measured_matched_nfe_only",
        "metric": "fg_dev (lower is better); secondary pb_validity_pct",
        "matched_nfe": 250,
        "n_total_per_arm": 1000,
        "seeds": [42, 43, 44],
        "per_seed": [],
        "baseline_nfe_sweep": {},
    }
    if not R3_MATCHED.exists():
        out["status"] = "artifact_missing"
        return out

    matched = json.loads(R3_MATCHED.read_text())
    ratios = []
    for ps in matched["per_seed"]:
        bl, fw = ps["baseline"], ps["framework"]
        bl_wall = bl.get("wallclock_sampling_s")
        fw_wall = fw.get("wallclock_sampling_s")
        ratio = None if not bl_wall or not fw_wall else float(fw_wall) / float(bl_wall)
        if ratio is not None:
            ratios.append(ratio)
        out["per_seed"].append(
            {
                "seed": int(ps["seed_base"]),
                "nfe_baseline": int(ps["nfe"]),
                "nfe_framework": int(ps["nfe"]),
                "baseline_fg_dev": float(bl["metrics"]["fg_dev"]),
                "framework_fg_dev": float(fw["metrics"]["fg_dev"]),
                "fg_dev_delta_fw_minus_bl": float(fw["metrics"]["fg_dev"]) - float(bl["metrics"]["fg_dev"]),
                "baseline_pb_validity": float(bl["metrics"]["pb_validity_pct"]),
                "framework_pb_validity": float(fw["metrics"]["pb_validity_pct"]),
                "pb_validity_delta_fw_minus_bl": float(fw["metrics"]["pb_validity_pct"]) - float(bl["metrics"]["pb_validity_pct"]),
                "baseline_sampling_s": bl_wall,
                "framework_sampling_s": fw_wall,
                "wall_ratio_fw_over_bl": ratio,
            }
        )
    if ratios:
        out["wall_ratio_fw_over_bl_median"] = sorted(ratios)[len(ratios) // 2]
        out["wall_ratio_note"] = (
            "framework is slower at matched NFE on every seed; the magnitude is not "
            "usable because baseline wall-clock spreads 2.9x across seeds (co-tenancy)"
        )

    by_nfe: dict[int, list[float]] = {}
    for path_str in sorted(glob.glob(str(REPO_ROOT / R3_TUNED_GLOB))):
        doc = json.loads(Path(path_str).read_text())
        nfe = int(doc["baseline_nfe"])
        by_nfe.setdefault(nfe, []).append(float(doc["baseline"]["metrics"]["fg_dev"]))
    out["baseline_nfe_sweep"] = {
        str(nfe): {
            "baseline_fg_dev_per_seed": vals,
            "baseline_fg_dev_mean": sum(vals) / len(vals),
        }
        for nfe, vals in sorted(by_nfe.items())
    }

    curve = [(250.0, _mean([r["baseline_fg_dev"] for r in out["per_seed"]]))]
    curve += [(float(n), sum(v) / len(v)) for n, v in sorted(by_nfe.items())]
    curve.sort()
    monotone = all(b[1] >= a[1] for a, b in zip(curve, curve[1:], strict=False)) or all(
        b[1] <= a[1] for a, b in zip(curve, curve[1:], strict=False)
    )
    out["baseline_curve"] = [{"nfe": n, "fg_dev": v} for n, v in curve]
    out["iso_quality_status"] = "identifiable" if monotone else "not_identifiable"
    out["iso_quality_reason"] = (
        "baseline fg_dev is non-monotone in NFE, so the iso-quality crossing is not unique"
        if not monotone
        else "baseline fg_dev is monotone in NFE"
    )
    return out


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _r1_section() -> dict:
    """LineageFlow (R1) — measured per-record cost model, no quality-vs-NFE curve.

    GAP-41b ran the same driver at NFE=10 and NFE=150 (N=200, seed 42, same
    checkpoint/host) and recorded wall-clock, which yields the fixed and
    marginal per-NFE cost. It does **not** yield an iso-quality NFE ratio:
    R1's headline (hmmscan hits) is only measured at NFE=150, so there is no
    quality axis to invert. The cost model is still the honest answer to
    "does an NFE saving translate into wall-clock saving?" — only partially,
    because a large per-record fixed cost does not shrink with NFE.
    """
    if not R1_METADATA.exists():
        return {"status": "artifact_missing"}
    meta = json.loads(R1_METADATA.read_text())
    cost = meta.get("per_record_cost_s", {})
    if "nfe10" not in cost or "nfe150" not in cost:
        return {"status": "cost_model_missing"}
    c10, c150 = float(cost["nfe10"]), float(cost["nfe150"])
    slope = (c150 - c10) / (150.0 - 10.0)
    intercept = c10 - slope * 10.0
    return {
        "status": "cost_model_measured_no_quality_curve",
        "metric": "hmmscan hits (Pfam family match), measured only at NFE=150",
        "protocol": {
            "n_records": meta.get("config", {}).get("n_records"),
            "seed": meta.get("config", {}).get("seed"),
            "n_rounds": meta.get("config", {}).get("n_rounds"),
            "nfe_values": meta.get("config", {}).get("nfe_values"),
            "device": meta.get("device", {}).get("gpu_name"),
            "venv": meta.get("environment", {}).get("venv"),
        },
        "per_record_cost_s": {"nfe10": c10, "nfe150": c150},
        "cost_model": {
            "fixed_s_per_record": intercept,
            "marginal_s_per_nfe_per_record": slope,
            "form": "t = fixed + marginal * NFE",
        },
        "wall_clock_ratio_150_over_10": c150 / c10,
        "fixed_share_of_nfe10_cost": intercept / c10,
        "iso_quality_status": "not_measured",
        "iso_quality_reason": (
            "no committed quality-vs-NFE curve for R1; the headline is measured at a "
            "single budget (NFE=150), so an iso-quality NFE ratio cannot be formed"
        ),
    }


def analyze(curve_doc: dict) -> dict:
    curve = curve_doc["curve"]
    framework_nfe = 50
    gap12 = json.loads(GAP12_JSON.read_text())
    arms = gap12["per_baseline_nfe"]["200"]["framework_arms"]
    rows = {}
    for arm, row in arms.items():
        fw_fid = float(row["fid_headline"])
        crossing = _interp_nfe_for_fid(curve, fw_fid)
        rows[arm] = {
            "framework_nfe": framework_nfe,
            "framework_fid": fw_fid,
            "baseline_nfe_at_iso_fid": crossing,
            "nfe_ratio_baseline_over_framework": (
                None if crossing is None else crossing / float(framework_nfe)
            ),
            "crossing_sensitivity_fid_pm1": _crossing_sensitivity(curve, fw_fid, 1.0),
            "crossing_sensitivity_fid_pm2": _crossing_sensitivity(curve, fw_fid, 2.0),
            "framework_fid_at_matched_nfe": fw_fid,
            "baseline_fid_at_matched_nfe": float(curve.get(str(framework_nfe), {}).get("fid", float("nan"))),
        }

    # R6 (LineageFlow k6) — committed curve; baseline pLDDT is NFE-invariant,
    # so an iso-quality NFE ratio is undefined rather than large.
    r6 = {
        "status": "not_measurable_ratio",
        "reason": "baseline pLDDT is constant across NFE in the committed curve",
        "provenance": (
            "incomplete: the artifact directory holds only the CSV and a PNG, with no "
            "N / seed / config record; treat as corroborating, not load-bearing"
        ),
        "corroboration": (
            "the baseline pLDDT is bit-identical at every NFE, consistent with the "
            "solver-free bare-RNG baseline documented in GAP-12 §3"
        ),
    }
    if R6_CURVE.exists():
        import csv as _csv

        with R6_CURVE.open() as f:
            r6_rows = list(_csv.DictReader(f))
        r6["curve"] = [
            {
                "nfe": int(r["nfe"]),
                "baseline_plddt": float(r["baseline_n1_plddt"]),
                "framework_plddt": float(r["framework_plddt"]),
            }
            for r in r6_rows
        ]

    return {
        "kind": "gap49_compute_ledger",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "protocol": "same frozen checkpoint, no retraining; FID on data/cifar10_inception_features.npz",
        "cifar_r5b": {
            "baseline_curve": curve,
            "framework_arms": rows,
        },
        "r6_lineageflow_k6": r6,
        "r1_lineageflow": _r1_section(),
        "r3_flowmol3": _r3_section(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline-nfes", default="5,10,20,25")
    ap.add_argument("--n-samples", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--skip-runs", action="store_true")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    curve_path = OUT_DIR / "baseline_curve.json"
    if args.skip_runs and curve_path.exists():
        curve_doc = json.loads(curve_path.read_text())
        # allow re-analysis after extending the NFE list
    else:
        nfes = [int(x) for x in str(args.baseline_nfes).split(",") if x.strip()]
        curve_doc = run_baseline_curve(nfes, args.n_samples, args.seed)
        curve_path.write_text(json.dumps(curve_doc, indent=2) + "\n")

    ledger = analyze(curve_doc)
    out = OUT_DIR / "compute_ledger.json"
    out.write_text(json.dumps(ledger, indent=2) + "\n")

    print("\n" + "=" * 78)
    print("GAP-49 — measured compute ledger (CIFAR-10 RF, framework NFE=50)")
    print("=" * 78)
    for arm, row in ledger["cifar_r5b"]["framework_arms"].items():
        cross = row["baseline_nfe_at_iso_fid"]
        ratio = row["nfe_ratio_baseline_over_framework"]
        cross_s = "outside measured range" if cross is None else f"{cross:.1f}"
        ratio_s = "n/a" if ratio is None else f"{ratio:.2f}x"
        sens = row["crossing_sensitivity_fid_pm1"]
        lo, hi = sens["fid_plus_1"], sens["fid_minus_1"]
        sens_s = "n/a" if lo is None or hi is None else f"[{lo:.0f}, {hi:.0f}]"
        print(
            f"  {arm:28s} FID={row['framework_fid']:.4f} "
            f"baseline iso-FID NFE={cross_s} ratio={ratio_s} "
            f"(+-1 FID -> NFE {sens_s})"
        )
    print(
        "  matched-NFE FID @50: baseline="
        f"{ledger['cifar_r5b']['framework_arms']['CosineAnnealScheduler']['baseline_fid_at_matched_nfe']:.4f}"
    )
    r3 = ledger["r3_flowmol3"]
    if r3.get("per_seed"):
        deltas = [r["fg_dev_delta_fw_minus_bl"] for r in r3["per_seed"]]
        print(
            f"  R3 fg_dev matched NFE=250: mean delta fw-bl={sum(deltas) / len(deltas):+.4f} "
            f"| iso-quality={r3['iso_quality_status']}"
        )
    r1 = ledger["r1_lineageflow"]
    if r1.get("cost_model"):
        cm = r1["cost_model"]
        print(
            f"  R1 cost model: {cm['fixed_s_per_record']:.2f}s fixed + "
            f"{cm['marginal_s_per_nfe_per_record']:.4f}s/NFE per record "
            f"| iso-quality={r1['iso_quality_status']}"
        )
    print(f"  wrote {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
    sys.exit(main())
