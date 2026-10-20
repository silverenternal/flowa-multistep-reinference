#!/bin/bash
# =============================================================================
# gap45_r1_blend_off.sh — GAP-45 R1 blend-on vs blend-off at NFE=150
#
# Question: R1's canonical win (d = +0.1178 at NFE=150) was attributed to the
# initial condition because the blend-off arm only ever ran at NFE=10, where the
# driver downgraded n_rounds to 1 and the blend never executed (GAP-25). The
# blend has never been tested at any budget.
#
# Design (from docs/audit/gap45-r1-blend-off-wiring.md §4):
#   3 seeds x 2 arms, N=200, NFE=150, n_rounds=3, restart_min_nfe=5,
#   temperature=1.0, upstream-eval-len-bias short.
#   blend-on  = driver default (beta = 0.5 * min(1, 50/150) = 0.1667)
#   blend-off = --beta-override 0.0  (beta = 0, m = 1, identity restart)
#
# All six arms are regenerated in this increment so that every tblout comes
# from the same pipeline. The seed42 blend-on arm is additionally checked
# against the GAP-41b prefix, which is the same configuration, as a
# reproducibility control.
#
# Output: verification_outputs/gap45-r1-blend-off-150/seed<seed>_<arm>/
#
# USAGE:
#   bash reproduce/gap45_r1_blend_off.sh
# =============================================================================

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

OUT="verification_outputs/gap45-r1-blend-off-150"
mkdir -p "$OUT"

export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export CUDA_VISIBLE_DEVICES=0
export OMP_NUM_THREADS=8

fail=0
for seed in 42 43 44; do
  for arm in on off; do
    extra=()
    [ "$arm" = "off" ] && extra=(--beta-override 0.0)
    dir="$OUT/seed${seed}_${arm}"
    mkdir -p "$dir"
    echo "[gap45] START seed=${seed} arm=${arm}"
    .venvs/lineageflow_venv/bin/python tools/gen_lineageflow_n1000_fastas.py \
        --seed "$seed" --n 200 --start-index 0 \
        --upstream-eval-len-bias short \
        --nfe 150 --n-rounds 3 --restart-min-nfe 5 --temperature 1.0 \
        "${extra[@]}" --outdir "$dir" > "$dir/run.log" 2>&1
    rc=$?
    echo "[gap45] EXIT=${rc} seed=${seed} arm=${arm}"
    [ "$rc" -ne 0 ] && fail=$((fail + 1))
  done
done

echo "[gap45] done, failures=${fail}"
exit 0
