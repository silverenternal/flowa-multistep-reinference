#!/bin/bash
# =============================================================================
# gap76_mean_preserving.sh — GAP-76: centroid-anchored restart on R5c
#
# GAP-77 (docs/audit/gap77-restart-mechanism.md) split the Fréchet distance
# over the frozen gap57 ladder and found the restart moves the batch mean away
# from the reference in 36/36 cells and contracts the covariance in 36/36.
# Removing the mean term arithmetically moves the mean dFID from +7.97% to
# -3.33% (4/36 -> 18/36 wins).
#
# This script runs the SOURCE-level version of that removal. `--mean-preserve`
# translates each framework arm's final cloud so its batch centroid equals the
# round-0 centroid of the same run. A translation leaves the covariance
# untouched, so the contraction channel survives and only the first moment
# moves. No reference or test statistic is used.
#
# Everything else is pinned to the gap57 equal-NFE ladder config so the
# before/after is a like-for-like comparison:
#   N=1000, NFE=50 total, R=4, beta_total=0.5, equal_budget, t0=memory,
#   scheduler allocation, shared prior, seed-keyed prior.
#
# Device: the MNIST FM adapter is NumPy on CPU; no GPU is used (cuda:0 is
# untouched). Wall clock is ~27 min per (checkpoint, seed) cell.
#
# Output: verification_outputs/gap76-mean-preserving/<ckpt>_s<seed>/
# Resume: a cell whose sweep_summary.json exists is skipped.
#
# USAGE:
#   bash reproduce/gap76_mean_preserving.sh            # all seeds, in order
#   SEEDS="42" bash reproduce/gap76_mean_preserving.sh # one seed
# =============================================================================

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

OUT="verification_outputs/gap76-mean-preserving"
mkdir -p "$OUT"

# checkpoint label -> file. `w16e1_60k` is the `w16e1.ckpt.npz` file used by
# the gap57 ladder cell of the same name (see its run.log line 1).
declare -A CKPT=(
  [production]="data/mnist_fm/production.ckpt.npz"
  [w16e1_5k]="data/mnist_fm/w16e1_5k.ckpt.npz"
  [w16e1_10k]="data/mnist_fm/w16e1_10k.ckpt.npz"
  [w16e1_60k]="data/mnist_fm/w16e1.ckpt.npz"
)
ORDER=(production w16e1_5k w16e1_10k w16e1_60k)
SEEDS="${SEEDS:-42 43 44}"

fail=0
for seed in $SEEDS; do
  for ck in "${ORDER[@]}"; do
    dir="$OUT/${ck}_s${seed}"
    mkdir -p "$dir"
    if [ -f "$dir/sweep_summary.json" ]; then
      echo "[gap76] SKIP ${ck}_s${seed} (summary exists)"
      continue
    fi
    echo "[gap76] START ${ck}_s${seed} $(date -u +%FT%TZ)"
    python3 scripts/wave191_p3_mnist_sweep.py \
        --n-samples 1000 \
        --seed "$seed" \
        --ckpt "${CKPT[$ck]}" \
        --output-dir "$dir" \
        --output-json "$dir/sweep_summary.json" \
        --shared-prior \
        --equal-total-nfe \
        --beta-schedule equal_budget \
        --restart-t0-mode memory \
        --seed-keyed-prior \
        --mean-preserve \
        > "$dir/run.log" 2>&1
    rc=$?
    echo "[gap76] EXIT=${rc} ${ck}_s${seed} $(date -u +%FT%TZ)"
    [ "$rc" -ne 0 ] && fail=$((fail + 1))
  done
done

echo "[gap76] done, failures=${fail}"
exit 0
