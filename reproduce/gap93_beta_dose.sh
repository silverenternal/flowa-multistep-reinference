#!/usr/bin/env bash
# GAP-93 — the fresh-noise budget (beta) dose on the converged checkpoint.
#
# Pre-registration: docs/audit/gap93-converged-lever.md. The decision rule is
# fixed there and this script only produces the numbers it reads:
#
#   stage 1  production, NFE=50, beta in {0.15,0.30,0.50,0.70}, seeds 42/43/44
#   stage 2  the beta stage 1 selects, at rungs 100 and 200 (run separately)
#
# The reproduction guard is beta=0.30 / NFE=50 / seed 42, which must match the
# recorded GAP-84 cell (evidence_driven FID 9.914133095545381) to 4 decimals.
# That cell already exists at
# verification_outputs/gap84-mnist-frontier/production_nfe50_s42/ and is reused
# rather than re-run.
#
# Usage:
#   reproduce/gap93_beta_dose.sh [--out DIR] [--jobs N] [--backend torch]
set -euo pipefail
cd "$(dirname "$0")/.."

OUT="verification_outputs/gap93-beta-dose"
JOBS=4
BACKEND=torch
DEVICE=cuda:0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)     OUT="$2"; shift 2 ;;
    --jobs)    JOBS="$2"; shift 2 ;;
    --backend) BACKEND="$2"; shift 2 ;;
    --device)  DEVICE="$2"; shift 2 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$OUT"
{
  echo "start_utc=$(date -u +%FT%TZ)"
  echo "cell=production / MNIST FM / beta dose (GAP-93)"
  echo "n_samples=1000 nfe=50 seeds=42 43 44 betas=0.15 0.30 0.50 0.70"
  echo "backend=$BACKEND device=$DEVICE jobs=$JOBS"
  echo "pre_registration=docs/audit/gap93-converged-lever.md"
  echo "reproduction_guard=beta0.30_nfe50_s42 vs gap84-mnist-frontier/production_nfe50_s42"
} | tee "$OUT/METADATA.txt"

for BETA in 0.15 0.30 0.50 0.70; do
  echo "[gap93] beta=$BETA $(date -u +%FT%TZ)" | tee -a "$OUT/METADATA.txt"
  reproduce/gap84_mnist_frontier.sh \
    --n-samples 1000 --out "$OUT/beta${BETA}" \
    --ckpts production --seeds 42,43,44 --nfes 50 \
    --jobs "$JOBS" --beta "$BETA" \
    --backend "$BACKEND" --torch-device "$DEVICE" \
    >> "$OUT/run.log" 2>&1
done

echo "[gap93] DOSE_DONE $(date -u +%FT%TZ)" | tee -a "$OUT/METADATA.txt"
