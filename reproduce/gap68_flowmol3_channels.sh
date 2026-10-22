#!/bin/bash
# =============================================================================
# gap68_flowmol3_channels.sh — GAP-68: per-channel restart on R3/FlowMol3
#
# Hypothesis (docs/audit/gap68-flowmol3-channels.md §0): the restart arm
# resamples the bond channel at the same rate as the coordinates, which puts
# the trajectory off-manifold. Locking the topology (m_pair = 1.0) should beat
# the all-channels-free arm by >= 0.5 sd on fg_dev.
#
#   A0  baseline                 (the driver's own baseline, shared prior)
#   A1  restart, all channels    --real-restart-blend --restart-memory-fraction 0.5
#   A2  restart, topology locked A1 + --restart-memory-fraction-pair 1.0
#   A3  restart, coord locked    A1 + --restart-memory-fraction-coordinate 1.0
#
# A3 runs at seed 42 only (interpretation aid, not confirmatory).
#
# Every cell is N=1000, NFE=250, nfe_batch=100, --shared-prior, seeds 42/43/44,
# cuda:0. The baseline arm is rebuilt inside each call; because the prior key is
# arm-independent under --shared-prior, every A0 is byte-identical across A1/A2,
# which is the pairing check.
#
# Output: verification_outputs/gap68-flowmol3-channels/<arm>/seed<seed>/
# Resume: a cell whose sweep JSON exists is skipped.
#
# USAGE:
#   bash reproduce/gap68_flowmol3_channels.sh              # all arms, all seeds
#   SEEDS="42" ARMS="a1 a2" bash reproduce/gap68_flowmol3_channels.sh
# =============================================================================

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

OUT="verification_outputs/gap68-flowmol3-channels"
PY=".venvs/flowmol3_venv/bin/python"
SEEDS="${SEEDS:-42 43 44}"
ARMS="${ARMS:-a1 a2 a3}"

declare -A ARM_FLAGS=(
  [a1]="--real-restart-blend --restart-memory-fraction 0.5"
  [a2]="--real-restart-blend --restart-memory-fraction 0.5 --restart-memory-fraction-pair 1.0"
  [a3]="--real-restart-blend --restart-memory-fraction 0.5 --restart-memory-fraction-coordinate 1.0"
)

fail=0
for arm in $ARMS; do
  for seed in $SEEDS; do
    # A3 is a seed-42 diagnostic only.
    if [ "$arm" = "a3" ] && [ "$seed" != "42" ]; then continue; fi
    dir="$OUT/$arm/seed$seed"
    mkdir -p "$dir"
    if compgen -G "$dir/*sweep*.json" > /dev/null; then
      echo "[gap68] SKIP $arm seed$seed (sweep exists)"
      continue
    fi
    echo "[gap68] START $arm seed$seed $(date -u +%FT%TZ)"
    # shellcheck disable=SC2086
    CUDA_VISIBLE_DEVICES=0 "$PY" scripts/wave338_p5_r3_n1000_paired.py \
        --n-total 1000 \
        --nfe 250 \
        --nfe-batch 100 \
        --seeds "$seed" \
        --shared-prior \
        ${ARM_FLAGS[$arm]} \
        --output-dir "$dir" \
        > "$dir/run.log" 2>&1
    rc=$?
    echo "[gap68] EXIT=${rc} $arm seed$seed $(date -u +%FT%TZ)"
    [ "$rc" -ne 0 ] && fail=$((fail + 1))
  done
done

echo "[gap68] done, failures=${fail}"
exit 0
