#!/usr/bin/env bash
# GAP-78 — the kappa dose-response: does the sign of DeltaFID follow the
# realised contraction within ONE checkpoint?
#
# Pre-registration: docs/audit/gap78-dispersion-gate.md §5 step 2.
#
# Why this and not another cross-section: GAP-67 §6.2 showed that comparing
# four different checkpoints confounds the observable with model quality. The
# only admissible identification is to hold the checkpoint fixed, move ONE
# knob (the restart fraction beta, hence m = 1 - beta), and check whether
# DeltaFID tracks kappa = tr(Sigma_restart)/tr(Sigma_base) along that path.
#
# CPU only. MNIST-FM is a NumPy adapter, so this touches no GPU.
#
# Usage:
#   reproduce/gap78_kappa_dose_response.sh [--n-samples N] [--out DIR]
#
# Default is the SCREEN (N=200). Screen numbers are NOT quotable (the MNIST
# projection-FID inflates effect sizes 40-65 % at N=200); they exist to choose
# which m values deserve an N=1000 confirmation.

set -euo pipefail
cd "$(dirname "$0")/.."

N=200
OUT=verification_outputs/gap78-kappa-dose-screen
CKPTS=(production w16e1_5k)
BETAS=(0.3 0.5 0.7)
SEEDS=(42)

while [[ $# -gt 0 ]]; do
  case "$1" in
    --n-samples) N="$2"; shift 2 ;;
    --out)       OUT="$2"; shift 2 ;;
    --ckpts)     IFS=, read -r -a CKPTS <<< "$2"; shift 2 ;;
    --betas)     IFS=, read -r -a BETAS <<< "$2"; shift 2 ;;
    --seeds)     IFS=, read -r -a SEEDS <<< "$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$OUT"
# Append, never truncate: a later invocation with a different --ckpts/--betas
# must not erase the log of an earlier one.
echo "[gap78] n=$N out=$OUT ckpts=${CKPTS[*]} betas=${BETAS[*]} seeds=${SEEDS[*]}" | tee -a "$OUT/run.log"

ckpt_path() {
  case "$1" in
    production) echo data/mnist_fm/production.ckpt.npz ;;
    w16e1_5k)   echo data/mnist_fm/w16e1_5k.ckpt.npz ;;
    w16e1_10k)  echo data/mnist_fm/w16e1_10k.ckpt.npz ;;
    w16e1_60k)  echo data/mnist_fm/w16e1.ckpt.npz ;;
    *) echo "unknown ckpt: $1" >&2; exit 2 ;;
  esac
}

# One seed keeps the legacy cell name; several seeds get an explicit _s<seed>
# suffix so a 3-seed directory can hold the seed-42 cells copied from an earlier
# single-seed run alongside fresh 43/44 cells.
if [[ ${#SEEDS[@]} -gt 1 ]]; then SEED_SUFFIXED=1; else SEED_SUFFIXED=0; fi

for ck in "${CKPTS[@]}"; do
  for b in "${BETAS[@]}"; do
    for sd in "${SEEDS[@]}"; do
      if [[ "$SEED_SUFFIXED" == "1" ]]; then
        cell="$OUT/${ck}_beta${b}_s${sd}"
      else
        cell="$OUT/${ck}_beta${b}"
      fi
      if [[ -f "$cell/sweep_summary.json" ]]; then
        echo "[gap78] skip $cell (already scored)" | tee -a "$OUT/run.log"
        continue
      fi
      echo "[gap78] $ck beta=$b seed=$sd -> $cell" | tee -a "$OUT/run.log"
    # --shared-prior is NOT optional here: without it the baseline and every arm
    # draw their own x0 (batch ids wave191-p3-baseline-s42 vs wave191-p3-<arm>-s42),
    # so the comparison is not paired on the prior and the baseline FID moves by
    # ~18 % (measured 2026-10-23: 11.777 without it vs 9.967 with it, same ckpt,
    # same NFE, same seed). GAP-76 used it; a dose-response without it is not the
    # same experiment.
    python3 scripts/wave191_p3_mnist_sweep.py \
      --ckpt "$(ckpt_path "$ck")" \
      --n-samples "$N" --seed "$sd" \
      --total-nfe 50 --n-rounds 4 \
      --equal-total-nfe --beta-schedule equal_budget \
      --beta-framework "$b" --restart-t0-mode memory \
      --mean-preserve --seed-keyed-prior --shared-prior \
      --output-dir "$cell" >> "$OUT/run.log" 2>&1
    done
  done
done

# kappa and DeltaFID per cell, from the artifacts just written.
python3 - "$OUT" <<'PY'
import json, sys
from pathlib import Path

import numpy as np

out = Path(sys.argv[1])
rows = []
for cell in sorted(p for p in out.iterdir() if p.is_dir()):
    summary = cell / "sweep_summary.json"
    base_npz = cell / "baseline_samples.npz"
    if not summary.exists() or not base_npz.exists():
        continue
    d = json.loads(summary.read_text())
    with np.load(base_npz) as z:
        tr_base = float(np.trace(np.cov(z["samples"], rowvar=False)))
    for arm, payload in d["framework_arms"].items():
        arm_npz = cell / f"{arm}_samples.npz"
        if not arm_npz.exists():
            continue
        with np.load(arm_npz) as z:
            tr_fw = float(np.trace(np.cov(z["samples"], rowvar=False)))
        fid = payload.get("fid_headline", payload.get("fid"))
        rows.append({
            "cell": cell.name,
            "arm": arm,
            "beta": d.get("beta_total", d.get("beta_framework")),
            "kappa": tr_fw / tr_base,
            "delta_pct": (fid - d["baseline_fid"]) / d["baseline_fid"] * 100.0,
        })

rows.sort(key=lambda r: (r["cell"], r["arm"]))
print("| cell | arm | beta | kappa | dFID% |")
print("|---|---|---:|---:|---:|")
for r in rows:
    print(f"| {r['cell']} | {r['arm']} | {r['beta']} | {r['kappa']:.4f} | {r['delta_pct']:+.2f} |")
(out / "kappa_dose.json").write_text(json.dumps(rows, indent=1) + "\n")
print(f"\nwrote {out / 'kappa_dose.json'}")
PY
