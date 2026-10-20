#!/bin/bash
# =============================================================================
# gap57_equal_nfe_ladder.sh — GAP-57 equal-total-NFE regime ladder (MNIST FM)
#
# Question: GAP-35 showed the restart gain is monotone in the model's
# optimisation budget (78-93 steps -> -25..-28 %; 937+ steps -> +3..+10 %).
# Every framework arm in that table, however, ran at the LEGACY per-round cap
# (cosine 25, codim 48, evidence 25 total NFE) against a baseline at 50 NFE
# (GAP-44). So the magnitude of every win is confounded with compute.
#
# This script re-measures the same checkpoint ladder with the SAME total NFE
# (50) on both sides, the mathematically correct restart start time
# (--restart-t0-mode memory: the blend is the path state at t = m), and
# --seed-keyed-prior so the three draws are genuinely independent.
#
# Everything except the checkpoint is held fixed. N=200, seeds 42/43/44,
# OMP_NUM_THREADS=1 (BLAS oversubscription is 12.7x slower here).
#
# Output: verification_outputs/gap57-equal-nfe-ladder/<ckpt>_s<seed>/
#
# USAGE:
#   bash reproduce/gap57_equal_nfe_ladder.sh            # all 12 runs
#   bash reproduce/gap57_equal_nfe_ladder.sh 6          # 6 concurrent workers
# =============================================================================

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

OUT_ROOT="verification_outputs/gap57-equal-nfe-ladder"
JOBS="${1:-6}"
mkdir -p "$OUT_ROOT"

# checkpoint tag -> path. `production` is the canonical R5c ckpt; the other
# three are the GAP-35 ladder anchors (w16e1 == w16e1_60k).
CKPTS=(
  "w16e1_5k:data/mnist_fm/w16e1_5k.ckpt.npz"
  "w16e1_10k:data/mnist_fm/w16e1_10k.ckpt.npz"
  "w16e1_60k:data/mnist_fm/w16e1.ckpt.npz"
  "production:data/mnist_fm/production.ckpt.npz"
)
SEEDS=(42 43 44)

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

run_one() {
  local tag="$1" ckpt="$2" seed="$3"
  local dir="$OUT_ROOT/${tag}_s${seed}"
  mkdir -p "$dir"
  echo "[gap57] START ${tag} seed=${seed} ckpt=${ckpt}"
  python3 scripts/wave191_p3_mnist_sweep.py \
      --ckpt "$ckpt" \
      --n-samples 200 \
      --seed "$seed" \
      --seed-keyed-prior \
      --shared-prior \
      --equal-total-nfe \
      --total-nfe 50 \
      --nfe-allocation scheduler \
      --beta-schedule equal_budget \
      --beta-framework 0.5 \
      --restart-t0-mode memory \
      --n-rounds 4 \
      --output-dir "$dir" \
      --output-json "$dir/sweep_summary.json" \
      > "$dir/run.log" 2>&1
  local rc=$?
  echo "[gap57] EXIT=${rc} ${tag} seed=${seed}"
  return $rc
}

running=0
fail=0
for entry in "${CKPTS[@]}"; do
  tag="${entry%%:*}"
  ckpt="${entry#*:}"
  for seed in "${SEEDS[@]}"; do
    run_one "$tag" "$ckpt" "$seed" &
    running=$((running + 1))
    if [ "$running" -ge "$JOBS" ]; then
      wait -n || fail=$((fail + 1))
      running=$((running - 1))
    fi
  done
done
wait
echo "[gap57] done, failed batches=${fail}"
exit 0
