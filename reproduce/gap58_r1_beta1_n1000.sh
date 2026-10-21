#!/bin/bash
# =============================================================================
# gap58_r1_beta1_n1000.sh — GAP-58: powered confirmation of the null memory term
#
# GAP-45 section 8 measured beta in {0, 1/6, 1} at N=200 and found that the
# memory term adds nothing measurable: beta=1/6 vs beta=1 is a tie in 3/3 seeds
# (delta -0.010 / +0.055 / +0.055 hits per record, every CI spans 0), while the
# per-record restart perturbation is load-bearing (beta=0 collapses to 0 hits).
#
# N=200 is enough to see a 3/3 tie but not to bound the effect size, so this
# runs the beta=1.0 endpoint at the same N as the canonical R1 headline
# (verification_outputs/gap55-r1-nfe150-n1000): N=1000, NFE=150, R=3.
#
# Everything except beta matches gap55-r1-nfe150-n1000 exactly. All arms run on
# GPU 0 -- the same device as the canonical run -- one at a time, so no two
# sampling processes share a GPU and no cross-device FP difference can enter.
#
# Output: verification_outputs/gap58-r1-beta1-n1000/seed<seed>/
# Resume: a seed whose manifest.json already exists is skipped.
#
# USAGE:
#   bash reproduce/gap58_r1_beta1_n1000.sh
# =============================================================================

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

OUT="verification_outputs/gap58-r1-beta1-n1000"
mkdir -p "$OUT"

export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=8

fail=0
for seed in 42 43 44; do
  dir="$OUT/seed${seed}"
  mkdir -p "$dir"
  if [ -f "$dir/manifest.json" ]; then
    echo "[gap58] SKIP seed=${seed} (manifest exists)"
    continue
  fi
  echo "[gap58] START seed=${seed} $(date -u +%FT%TZ)"
  CUDA_VISIBLE_DEVICES=0 .venvs/lineageflow_venv/bin/python \
      tools/gen_lineageflow_n1000_fastas.py \
      --seed "$seed" --n 1000 --start-index 0 \
      --upstream-eval-len-bias short \
      --nfe 150 --n-rounds 3 --restart-min-nfe 5 --temperature 1.0 \
      --beta-override 1.0 --outdir "$dir" > "$dir/run.log" 2>&1
  rc=$?
  echo "[gap58] EXIT=${rc} seed=${seed} $(date -u +%FT%TZ)"
  [ "$rc" -ne 0 ] && fail=$((fail + 1))
done

echo "[gap58] done, failures=${fail}"
exit 0
