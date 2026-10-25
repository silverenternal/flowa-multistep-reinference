#!/usr/bin/env bash
# GAP-84c — the round-count dose at a fixed total NFE.
#
# Pre-registration: docs/audit/gap84-inference-frontier.md §9. The cap in §8
# showed that R matters at NFE = 4 (4 -> 2 is worth 2.39 FID). It said nothing
# about R above the cap. This grid holds total NFE = 25 and moves R only:
#
#   R in {2, 4, 6, 8, 12}, min_steps_per_round = 2 -> R_eff = R for every level
#   (25 // 2 = 12, so the cap never bites here; the dose is clean)
#
# R = 4 is the in-grid reference: it is the value every rung of §7 used. The
# allocation at NFE = 25 is [13,12] / [7,6,6,6] / [5,4,4,4,4,4] / ... — every
# round keeps >= 2 Euler steps, which is the condition §8 established.
#
# Everything else is the canonical arm of reproduce/gap84_mnist_frontier.sh
# (equal total NFE, beta = 0.3, memory restart, mean-preserving blend, shared
# prior). Only R changes, so the x-axis is a dose and not a sweep of knobs.
#
# Decision rule (fixed before the run, §9): monotone rise in the paired
# improvement as R grows -> the lever is live; interior optimum at R <= 4 ->
# saturated; flat -> R does not enter the effect above the cap.
#
# Cost: ~8.7 s per 1000 samples per NFE unit per arm, so ~15 min per cell at
# 25 NFE x 4 arms x 1 thread. 15 cells.
#
# Usage:
#   reproduce/gap84c_round_dose.sh [--n-samples N] [--out DIR]
#       [--ckpts a,b] [--seeds 42,43] [--rounds 2,4,6,8,12] [--nfe 25] [--jobs 3]

set -euo pipefail
cd "$(dirname "$0")/.."

N=1000
OUT="verification_outputs/gap84c-round-dose"
CKPTS=(production)
SEEDS=(42 43 44)
ROUNDS=(2 4 6 8 12)
NFE=25
JOBS=3
BETA=0.3
MIN_STEPS=2

while [[ $# -gt 0 ]]; do
  case "$1" in
    --n-samples) N="$2"; shift 2 ;;
    --out)       OUT="$2"; shift 2 ;;
    --ckpts)     IFS=, read -r -a CKPTS <<< "$2"; shift 2 ;;
    --seeds)     IFS=, read -r -a SEEDS <<< "$2"; shift 2 ;;
    --rounds)    IFS=, read -r -a ROUNDS <<< "$2"; shift 2 ;;
    --nfe)       NFE="$2"; shift 2 ;;
    --jobs)      JOBS="$2"; shift 2 ;;
    --beta)      BETA="$2"; shift 2 ;;
    -h|--help)   sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$OUT"
{
  echo "start_utc=$(date -u +%FT%TZ)"
  echo "n_samples=$N out=$OUT ckpts=${CKPTS[*]} seeds=${SEEDS[*]} rounds=${ROUNDS[*]} nfe=$NFE jobs=$JOBS beta=$BETA"
  echo "nproc=$(nproc) load=$(cut -d' ' -f1-3 /proc/loadavg)"
  echo "flags=--equal-total-nfe --beta-schedule equal_budget --restart-t0-mode memory --mean-preserve --seed-keyed-prior --shared-prior --min-steps-per-round $MIN_STEPS"
  echo "resume_key=sweep_summary.json"
} | tee "$OUT/METADATA.txt"

ckpt_path() {
  case "$1" in
    production) echo data/mnist_fm/production.ckpt.npz ;;
    w16e1_5k)   echo data/mnist_fm/w16e1_5k.ckpt.npz ;;
    w16e1_10k)  echo data/mnist_fm/w16e1_10k.ckpt.npz ;;
    w16e1_60k)  echo data/mnist_fm/w16e1.ckpt.npz ;;
    *) echo "unknown ckpt: $1" >&2; exit 2 ;;
  esac
}

run_one() {
  local ck="$1" sd="$2" r="$3"
  local cell="$OUT/${ck}_nfe${NFE}_r${r}_s${sd}"
  if [[ -f "$cell/sweep_summary.json" ]]; then
    echo "[gap84c] skip $cell (already scored)"
    return 0
  fi
  mkdir -p "$cell"
  echo "[gap84c] start $cell $(date -u +%FT%TZ)"
  if OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    python3 scripts/wave191_p3_mnist_sweep.py \
      --ckpt "$(ckpt_path "$ck")" \
      --n-samples "$N" --seed "$sd" \
      --total-nfe "$NFE" --n-rounds "$r" --min-steps-per-round "$MIN_STEPS" \
      --equal-total-nfe --beta-schedule equal_budget \
      --beta-framework "$BETA" --restart-t0-mode memory \
      --mean-preserve --seed-keyed-prior --shared-prior \
      --output-dir "$cell" > "$cell/run.log" 2>&1; then
    echo "[gap84c] done  $cell $(date -u +%FT%TZ)"
  else
    echo "[gap84c] FAIL  $cell (see $cell/run.log)" >&2
    echo "$cell" >> "$OUT/FAILED.txt"
    return 1
  fi
}
export -f run_one
export -f ckpt_path
export OUT N BETA NFE MIN_STEPS

: > "$OUT/jobs.txt"
for ck in "${CKPTS[@]}"; do
  for sd in "${SEEDS[@]}"; do
    for r in "${ROUNDS[@]}"; do
      printf '%s %s %s\n' "$ck" "$sd" "$r" >> "$OUT/jobs.txt"
    done
  done
done
echo "[gap84c] $(wc -l < "$OUT/jobs.txt") cells, $JOBS concurrent" | tee -a "$OUT/METADATA.txt"

xargs -P "$JOBS" -n 3 bash -c 'run_one "$0" "$1" "$2"' < "$OUT/jobs.txt" \
  2>&1 | tee -a "$OUT/run.log" || true

echo "[gap84c] DOSE_DONE $(date -u +%FT%TZ) failed=$( [[ -f "$OUT/FAILED.txt" ]] && wc -l < "$OUT/FAILED.txt" || echo 0 )" \
  | tee -a "$OUT/METADATA.txt"
