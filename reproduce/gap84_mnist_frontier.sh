#!/usr/bin/env bash
# GAP-84 — the MNIST (quality, NFE) frontier grid.
#
# Pre-registration: docs/audit/gap84-inference-frontier.md §0.2 (grid),
# §0.3 (N, seeds, pairing), §0.5 (margin = the cell's ledger floor).
#
# Canonical arm: the GAP-78 configuration, because that is the arm the paper's
# R5c cell now reports — equal total NFE across 4 rounds, beta = 0.3, memory
# restart, mean-preserving blend, shared prior. Only the total NFE changes
# between rungs; everything else is held fixed, which is what makes the x-axis
# a frontier rather than a sweep of several knobs.
#
# --shared-prior is mandatory: without it the baseline and the framework arms
# draw independent x0 (batch ids wave191-p3-baseline-s42 vs -<arm>-s42) and the
# baseline FID moves ~18 % (measured 2026-10-23: 11.777 vs 9.967, same ckpt /
# NFE / seed). A frontier on unpaired priors is not the same experiment.
#
# Each cell is one (checkpoint, seed, NFE) run of 4 arms (baseline + cosine +
# codimension_sheet + evidence_driven). Resume key: sweep_summary.json.
#
# Cost: generation scales linearly in NFE (~8.7 s per 1000 samples per NFE
# unit per arm on this host). The default grid over 4 ckpts x 3 seeds is ~45 h
# of CPU; --jobs runs independent cells concurrently at 1 BLAS thread each.
#
# The lowest rung is 4, not 3: the 4-round equal-budget allocator enforces one
# step per round, so a requested 3 is realised as 4 on the framework arms while
# the baseline runs 3 — not a matched-NFE point. See
# docs/audit/gap84-inference-frontier.md §0.2b.
#
# Usage:
#   reproduce/gap84_mnist_frontier.sh [--n-samples N] [--out DIR]
#       [--ckpts a,b,c] [--seeds 42,43] [--nfes 3,10,50] [--jobs 4] [--beta 0.3]
#       [--min-steps-per-round K]   # GAP-84b cap; default 1 = legacy allocation

set -euo pipefail
cd "$(dirname "$0")/.."

N=1000
OUT="verification_outputs/gap84-mnist-frontier"
CKPTS=(production w16e1_5k w16e1_10k w16e1_60k)
SEEDS=(42 43 44)
NFES=(4 5 10 25 50 100 200)
JOBS=4
BETA=0.3
# GAP-84b/§8 policy: cap the round count so every round keeps >= this many
# steps. Default 1 is the pre-GAP-84b allocation, bit-identical.
MIN_STEPS=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --n-samples) N="$2"; shift 2 ;;
    --out)       OUT="$2"; shift 2 ;;
    --ckpts)     IFS=, read -r -a CKPTS <<< "$2"; shift 2 ;;
    --seeds)     IFS=, read -r -a SEEDS <<< "$2"; shift 2 ;;
    --nfes)      IFS=, read -r -a NFES <<< "$2"; shift 2 ;;
    --jobs)      JOBS="$2"; shift 2 ;;
    --beta)      BETA="$2"; shift 2 ;;
    --min-steps-per-round) MIN_STEPS="$2"; shift 2 ;;
    -h|--help)   sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$OUT"
{
  echo "start_utc=$(date -u +%FT%TZ)"
  echo "n_samples=$N out=$OUT ckpts=${CKPTS[*]} seeds=${SEEDS[*]} nfes=${NFES[*]} jobs=$JOBS beta=$BETA min_steps=$MIN_STEPS"
  echo "nproc=$(nproc) load=$(cut -d' ' -f1-3 /proc/loadavg)"
  echo "flags=--equal-total-nfe --beta-schedule equal_budget --restart-t0-mode memory --mean-preserve --seed-keyed-prior --shared-prior --n-rounds 4 --min-steps-per-round $MIN_STEPS"
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
  local ck="$1" sd="$2" nfe="$3"
  local cell="$OUT/${ck}_nfe${nfe}_s${sd}"
  if [[ -f "$cell/sweep_summary.json" ]]; then
    echo "[gap84] skip $cell (already scored)"
    return 0
  fi
  mkdir -p "$cell"
  echo "[gap84] start $cell $(date -u +%FT%TZ)"
  if OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    python3 scripts/wave191_p3_mnist_sweep.py \
      --ckpt "$(ckpt_path "$ck")" \
      --n-samples "$N" --seed "$sd" \
      --total-nfe "$nfe" --n-rounds 4 \
      --equal-total-nfe --beta-schedule equal_budget \
      --beta-framework "$BETA" --restart-t0-mode memory \
      --min-steps-per-round "$MIN_STEPS" \
      --mean-preserve --seed-keyed-prior --shared-prior \
      --output-dir "$cell" > "$cell/run.log" 2>&1; then
    echo "[gap84] done  $cell $(date -u +%FT%TZ)"
  else
    echo "[gap84] FAIL  $cell (see $cell/run.log)" >&2
    echo "$cell" >> "$OUT/FAILED.txt"
    return 1
  fi
}
export -f run_one
export -f ckpt_path
export OUT N BETA MIN_STEPS

: > "$OUT/jobs.txt"
for ck in "${CKPTS[@]}"; do
  for sd in "${SEEDS[@]}"; do
    for nfe in "${NFES[@]}"; do
      printf '%s %s %s\n' "$ck" "$sd" "$nfe" >> "$OUT/jobs.txt"
    done
  done
done
echo "[gap84] $(wc -l < "$OUT/jobs.txt") cells, $JOBS concurrent" | tee -a "$OUT/METADATA.txt"

# xargs drives the pool; a failing cell is recorded and does not stop the grid.
xargs -P "$JOBS" -n 3 bash -c 'run_one "$0" "$1" "$2"' < "$OUT/jobs.txt" \
  2>&1 | tee -a "$OUT/run.log" || true

echo "[gap84] GRID_DONE $(date -u +%FT%TZ) failed=$( [[ -f "$OUT/FAILED.txt" ]] && wc -l < "$OUT/FAILED.txt" || echo 0 )" \
  | tee -a "$OUT/METADATA.txt"
