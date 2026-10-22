#!/usr/bin/env bash
# GAP-71 — CIFAR R5b at MATCHED total NFE: the before arm, then the spectral arm.
#
# Pre-registration: docs/audit/gap71-image-spectral.md §0.
#
# Why `--match-nfe sample`: the driver's default (`budget`) allocates steps from
# `n_cap` and does NOT bound the total. Wave 280 ran
# `--baseline-num-steps 2 --n-rounds 2 --match-nfe budget` and got framework
# NFE=3 against baseline NFE=2 — a 50 % over-budget arm. `sample` mode allocates
# exactly `baseline_num_steps` across the rounds, which is the only equal-total
# control the driver has. `--require-matched-nfe` makes a mismatch fatal BEFORE
# FID is computed, so an unmatched number cannot be produced by accident.
#
# Cost: 4 schedulers x 3 seeds x 2 arms x N=1000. This is the deferred GPU run;
# it is NOT executed by the commit that adds this script.
#
# Usage:
#   ARM=before bash reproduce/gap71_cifar_matched_nfe.sh
#   ARM=after  bash reproduce/gap71_cifar_matched_nfe.sh
#   ARM=both   bash reproduce/gap71_cifar_matched_nfe.sh
set -euo pipefail

cd "$(dirname "$0")/.."

# CIFAR RF uses the FlowMol3 sidecar venv (docs/environments.md).
PY=".venvs/flowmol3_venv/bin/python"

ARM=${ARM:-before}
SEEDS=${SEEDS:-"42 43 44"}
N=${N:-1000}
OUTROOT=${OUTROOT:-verification_outputs/gap71-cifar-matched-nfe}
BASELINE_STEPS=${BASELINE_STEPS:-2}
N_ROUNDS=${N_ROUNDS:-2}
SPECTRAL_FRACTION=${SPECTRAL_FRACTION:-0.5}

export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}

mkdir -p "$OUTROOT"

run_arm() {
  local arm="$1" seed="$2" extra=()
  if [[ "$arm" == "after" ]]; then
    extra=(--spectral-band-fraction "$SPECTRAL_FRACTION")
  fi
  local out="$OUTROOT/$arm/seed$seed"
  mkdir -p "$out"
  if [[ -f "$out/summary.json" ]]; then
    echo "[gap71] $arm seed=$seed already has summary.json — skipping"
    return 0
  fi
  echo "[gap71] $arm seed=$seed -> $out"
  WAVE247_SEED="$seed" "$PY" tools/run_sota_cifar_experiment.py \
    --n-samples "$N" \
    --framework-samples "$N" \
    --baseline-num-steps "$BASELINE_STEPS" \
    --framework-max-num-steps "$BASELINE_STEPS" \
    --n-rounds "$N_ROUNDS" \
    --match-nfe sample \
    --require-matched-nfe \
    --solver euler \
    --device cuda \
    --output-dir "$out" \
    "${extra[@]}" 2>&1 | tee "$out/run.log"
}

for seed in $SEEDS; do
  case "$ARM" in
    before) run_arm before "$seed" ;;
    after)  run_arm after  "$seed" ;;
    both)   run_arm before "$seed"; run_arm after "$seed" ;;
    *) echo "ARM must be before|after|both, got $ARM" >&2; exit 2 ;;
  esac
done

echo "[gap71] DONE arm=$ARM $(date -u +%FT%TZ)"
