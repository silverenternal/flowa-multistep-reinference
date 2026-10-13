#!/usr/bin/env bash
# GAP-12 tuned-baseline for R3 / K1 (FlowMol3 fg_dev + RDKit validity).
#
# The canonical R3/K1 pipeline (`scripts/wave338_p5_r3_n1000_paired.py`) applies
# one NFE budget to BOTH arms. GAP-12 asks whether the framework's fg_dev /
# validity edge survives a *tuned* baseline, so the baseline arm is re-run at
# 2x (NFE=500) and 4x (NFE=1000) the matched budget while the framework arm
# stays at the matched NFE=250.
#
# Cost is the reason this is launched by hand and not from pytest: each budget
# is 3 seeds x N=1000 x (baseline + framework) via the real upstream FlowMol3
# checkpoint.
#
# Usage:  CUDA_VISIBLE_DEVICES=<gpu> bash scripts/gap12_r3_tuned_baseline.sh
# HARD CONSTRAINT: one GPU only (the adapter pins a single device).
set -euo pipefail

cd "$(dirname "$0")/.."
REPO="$PWD"
PY="$REPO/.venvs/flowmol3_venv/bin/python"
DEV="${CUDA_VISIBLE_DEVICES:-1}"

export CUDA_VISIBLE_DEVICES="$DEV"
export PYTHONPATH="$REPO"

echo "[gap12-r3] start $(date -u +%FT%TZ) CUDA_VISIBLE_DEVICES=$DEV"
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv > /tmp/gap12_r3_meta.gpu

for BN in 500 1000; do
  OUT="verification_outputs/gap12-r3-tuned-baseline-nfe${BN}"
  echo "[gap12-r3] baseline NFE=$BN -> $OUT  $(date -u +%FT%TZ)"
  "$PY" scripts/wave338_p5_r3_n1000_paired.py \
      --n-total 1000 --nfe 250 --baseline-nfe "$BN" \
      --seeds 42 43 44 --device cuda:0 \
      --output-dir "$OUT" \
      > "verification_outputs/_gap04-logs/gap12-r3-baseline-nfe${BN}.log" 2>&1
  echo "[gap12-r3] baseline NFE=$BN done  $(date -u +%FT%TZ)"
done

echo "[gap12-r3] all done $(date -u +%FT%TZ)"
