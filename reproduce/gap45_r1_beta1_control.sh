#!/bin/bash
# =============================================================================
# gap45_r1_beta1_control.sh — GAP-45 follow-up: the non-degenerate attribution arm
#
# Why this exists
# ---------------
# GAP-45's pre-registered control was blend-off (--beta-override 0.0). With
# ``blended = m * prior + (1 - m) * fresh`` and ``m = 1 - beta``, beta = 0 means
# ``blended = prior``: the restart injects NO fresh perturbation at all. That is
# the D-004 collapse mode (docs/audit/r1-d004-remeasure.md section 6): the arm
# degenerates to a low-complexity attractor and scores 0 Pfam hits. beta = 0 is
# therefore not a neutral "blend off"; it is a different, broken mechanism.
#
# This script runs the complementary endpoint: beta = 1.0, i.e. ``m = 0`` and
# ``blended = fresh``. The restart keeps the per-record random perturbation but
# carries NO memory of the previous sample, so the final sample is a 50-NFE
# draw from a fresh simplex. Same total NFE (150), same R (3), same seeds.
#
# Everything else matches reproduce/gap45_r1_blend_off.sh exactly.
#
# Output: verification_outputs/gap45-r1-beta1-150/seed<seed>/
#
# USAGE:
#   bash reproduce/gap45_r1_beta1_control.sh
# =============================================================================

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

OUT="verification_outputs/gap45-r1-beta1-150"
mkdir -p "$OUT"

export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=8

fail=0
for seed in 42 43 44; do
  dir="$OUT/seed${seed}"
  mkdir -p "$dir"
  # GPU 1: the GAP-45 generation sweep owns GPU 0. One arm at a time, on a
  # single device, so no two sampling processes ever share a GPU.
  gpu=1
  echo "[gap45-beta1] START seed=${seed} gpu=${gpu}"
  CUDA_VISIBLE_DEVICES="$gpu" .venvs/lineageflow_venv/bin/python \
      tools/gen_lineageflow_n1000_fastas.py \
      --seed "$seed" --n 200 --start-index 0 \
      --upstream-eval-len-bias short \
      --nfe 150 --n-rounds 3 --restart-min-nfe 5 --temperature 1.0 \
      --beta-override 1.0 --outdir "$dir" > "$dir/run.log" 2>&1
  rc=$?
  echo "[gap45-beta1] EXIT=${rc} seed=${seed}"
  [ "$rc" -ne 0 ] && fail=$((fail + 1))
done

echo "[gap45-beta1] done, failures=${fail}"
exit 0
