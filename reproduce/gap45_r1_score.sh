#!/bin/bash
# =============================================================================
# gap45_r1_score.sh — score the six GAP-45 FASTA pairs with the upstream pipeline
#
# Scores an already-generated set of FASTA pairs; it never regenerates samples
# and never touches a prior ``upstream_*/`` directory.
#
# Output: verification_outputs/gap45-r1-blend-off-150/seed<seed>_<arm>/
#           upstream_baseline/, upstream_framework/, upstream_eval.json, score.log
#
# USAGE:
#   bash reproduce/gap45_r1_score.sh
# =============================================================================

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

OUT="verification_outputs/gap45-r1-blend-off-150"

export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export CUDA_VISIBLE_DEVICES=0

fail=0
for seed in 42 43 44; do
  for arm in on off; do
    dir="$OUT/seed${seed}_${arm}"
    if [ ! -f "$dir/framework.fasta" ] || [ ! -f "$dir/baseline.fasta" ]; then
      echo "[gap45-score] SKIP seed=${seed} arm=${arm} (missing fasta)"
      fail=$((fail + 1))
      continue
    fi
    echo "[gap45-score] START seed=${seed} arm=${arm}"
    .venvs/lineageflow_venv/bin/python tools/gap55_r1_score_fastas.py \
        --run-dir "$dir" --length-bias short > "$dir/score.log" 2>&1
    rc=$?
    echo "[gap45-score] EXIT=${rc} seed=${seed} arm=${arm}"
    [ "$rc" -ne 0 ] && fail=$((fail + 1))
  done
done

echo "[gap45-score] done, failures=${fail}"
exit 0
