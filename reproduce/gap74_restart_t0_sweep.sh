#!/bin/bash
# =============================================================================
# gap74_restart_t0_sweep.sh — GAP-74: rho contraction vs (1 - m) at fixed t0
#
# Pre-registration: docs/audit/gap74-conditional-mean-bound.md §0.
#
# The current design ties t0 = 1 - beta = m, so sweeping m also moves the
# integration interval [t0, 1]. `--restart-t0` pins t0 for every restart round
# (round 0 always starts at 0), which is the only way to attribute a monotone
# rho(m) to the amount of fresh noise rather than to the interval length.
#
# Grid (fixed before the run):
#   checkpoints  production, w16e1_5k   (GAP-76's opposite ends)
#   m            {0.9, 0.7, 0.5, 0.3, 0.1}  -> beta = 1 - m
#   t0           0.5 fixed
#   seeds        42 43 44, N=1000, equal total NFE
#
# Device: the MNIST FM adapter is NumPy on CPU; cuda:0 is untouched.
#
# Output: verification_outputs/gap74-restart-t0/<ckpt>_m<m>_s<seed>/
# Resume: a cell whose sweep_summary.json exists is skipped.
#
# USAGE:
#   bash reproduce/gap74_restart_t0_sweep.sh            # full 30-cell grid
#   SEEDS="42" bash reproduce/gap74_restart_t0_sweep.sh # smoke
# =============================================================================

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

OUT="verification_outputs/gap74-restart-t0"
mkdir -p "$OUT"

declare -A CKPT=(
  [production]="data/mnist_fm/production.ckpt.npz"
  [w16e1_5k]="data/mnist_fm/w16e1_5k.ckpt.npz"
)
ORDER=(production w16e1_5k)
MS=(0.9 0.7 0.5 0.3 0.1)
SEEDS="${SEEDS:-42 43 44}"
T0="${T0:-0.5}"

# Parallelism only: the per-cell command, config and ordering are unchanged.
# PAR=1 reproduces the original serial run exactly.
PAR="${PAR:-1}"

run_one() {  # $1 = checkpoint key, $2 = m, $3 = seed
  local ck="$1" m="$2" seed="$3"
  local beta dir
  beta=$(python3 -c "print(round(1.0 - float('$m'), 6))")
  dir="$OUT/${ck}_m${m}_s${seed}"
  mkdir -p "$dir"
  if [ -f "$dir/sweep_summary.json" ]; then
    echo "[gap74] SKIP ${ck}_m${m}_s${seed} (summary exists)"
    return 0
  fi
  echo "[gap74] START ${ck}_m${m}_s${seed} t0=${T0} beta=${beta} $(date -u +%FT%TZ)"
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python3 scripts/wave191_p3_mnist_sweep.py \
      --n-samples 1000 \
      --seed "$seed" \
      --ckpt "$CKPT_PATH" \
      --output-dir "$dir" \
      --output-json "$dir/sweep_summary.json" \
      --shared-prior \
      --equal-total-nfe \
      --beta-schedule equal_budget \
      --restart-t0-mode memory \
      --restart-t0 "$T0" \
      --beta-framework "$beta" \
      --seed-keyed-prior \
      > "$dir/run.log" 2>&1
  local rc=$?
  echo "[gap74] EXIT=${rc} ${ck}_m${m}_s${seed} $(date -u +%FT%TZ)"
  [ "$rc" -ne 0 ] && echo "${ck}_m${m}_s${seed}" >> "$OUT/FAILED.txt"
  return 0
}
export -f run_one
export OUT T0

: > "$OUT/jobs.txt"
for seed in $SEEDS; do
  for ck in "${ORDER[@]}"; do
    for m in "${MS[@]}"; do
      printf '%s %s %s\n' "$ck" "$m" "$seed" >> "$OUT/jobs.txt"
    done
  done
done

# xargs runs one cell per bash subshell; the checkpoint path is looked up there
# so the associative array never has to cross a process boundary.
CKPT_PATH_MAP="$(
  for k in "${!CKPT[@]}"; do printf '%s=%s\n' "$k" "${CKPT[$k]}"; done
)"
export CKPT_PATH_MAP

xargs -P "$PAR" -n 3 bash -c '
  for kv in $CKPT_PATH_MAP; do
    case "$kv" in "$0="*) CKPT_PATH="${kv#*=}" ;; esac
  done
  export CKPT_PATH
  run_one "$0" "$1" "$2"
' < "$OUT/jobs.txt"

fail=$( [ -f "$OUT/FAILED.txt" ] && wc -l < "$OUT/FAILED.txt" || echo 0 )
echo "[gap74] done, failures=${fail}"

python3 tools/gap74_rho_report.py \
    --root "$OUT" \
    --seeds $SEEDS \
    --out "$OUT/report.json" 2>&1 | tee "$OUT/report.log"

exit 0
