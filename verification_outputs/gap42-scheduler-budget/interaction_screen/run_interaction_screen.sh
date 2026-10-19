#!/usr/bin/env bash
# GAP-42e — 2x2 interaction screen: tier-aware n_cap  x  endpoint chain.
#
#   tier_off : --tier-aware-n-cap 0.5 (+ baseline pLDDT jsonl), chain off
#   tier_on  : same tier flags, chain ON (--restart-from-endpoint)
#
# The chain-off / chain-on *legacy* cells already exist in the GAP-42c screen
# (same seeds, same config), so this run only adds the two tier cells.
# Config matches GAP-41's screen exactly (gate-open: restart_min_nfe=5).
#
# Question: does the tier-aware n_cap lever become load-bearing *given* a live
# chain? (GAP-42d refuted the chain alone; this tests the interaction.)
#
# GPU 0 only. Resumable via START=<index>.
set -euo pipefail

REPO=/home/hugo/codes/flowa-multistep-reinference
VENV=$REPO/.venvs/lineageflow_venv/bin/python
OUT=/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap42e-interaction
BASELINE_JSONL=$REPO/verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/foldability.jsonl
PREMISE=/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41b-nfe150/premise
N=${N:-200}
START=${START:-0}
SEEDS=${SEEDS:-"42 43 44"}
cd "$REPO"
export TMPDIR=/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41-tmp TORCHINDUCTOR_CACHE_DIR=/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41-torchinductor
mkdir -p "$TMPDIR" "$TORCHINDUCTOR_CACHE_DIR" "$OUT"
cp "$PREMISE/count_hits.py" "$OUT/"

nvidia-smi > "$OUT/METADATA.gpu" 2>&1 || true
{
  echo "start=$(date -u +%FT%TZ)"
  echo "N=$N nfe=10 n_rounds=3 restart_min_nfe=5 scheduler=cosine temperature=1.0"
  echo "seeds=$SEEDS start_index=$START"
  echo "tier_aware_n_cap=0.5 baseline_metrics=$BASELINE_JSONL"
  echo "reused cells: chain_screen/seed*_chain_{off,on} (legacy n_cap)"
} > "$OUT/METADATA.txt"

gen() {  # gen <seed> <tag> <chain:0|1>
  local seed="$1" tag="$2" chain="$3"
  local d="$OUT/seed${seed}_${tag}"
  mkdir -p "$d"
  local extra=()
  if [ "$chain" = "1" ]; then extra+=(--restart-from-endpoint); fi
  echo "=== gen seed=$seed $tag n=$N start=$START $(date -u +%FT%TZ) ==="
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_VISIBLE_DEVICES=0 \
    "$VENV" tools/gen_lineageflow_n1000_fastas.py \
    --seed "$seed" --n "$N" --start-index "$START" --upstream-eval-len-bias short \
    --nfe 10 --n-rounds 3 --restart-min-nfe 5 --temperature 1.0 \
    --scheduler cosine \
    --tier-aware-n-cap 0.5 \
    --tier-aware-baseline-metrics-jsonl "$BASELINE_JSONL" \
    "${extra[@]}" \
    --outdir "$d" > "$d/gen.log" 2>&1
  echo "  done $(date -u +%FT%TZ)"
}

for seed in $SEEDS; do
  gen "$seed" tier_off 0
  gen "$seed" tier_on 1
done

echo "=== sanity ==="
for seed in $SEEDS; do
  if cmp -s "$OUT/seed${seed}_tier_off/framework.fasta" "$OUT/seed${seed}_tier_on/framework.fasta"; then
    echo "seed$seed tier: chain has NO effect"
  else
    echo "seed$seed tier: chain is live"
  fi
done
# GAP-41's archived seed-42 tier_a arm must be reproduced byte-for-byte.
ARCH=$REPO/verification_outputs/gap41-r1-tier-aware-ncap/n200_screen
if [ -f "$ARCH/tier_a_framework.fasta" ]; then
  cmp -s "$OUT/seed42_tier_off/framework.fasta" "$ARCH/tier_a_framework.fasta" \
    && echo "seed42 tier_off: BYTE-IDENTICAL to GAP-41 archived tier_a" \
    || echo "seed42 tier_off: differs from GAP-41 archive"
else
  echo "seed42 tier_off: GAP-41 archived FASTA not present (tblout-only archive)"
fi

echo "=== HMMER $(date -u +%FT%TZ) ==="
files=()
for seed in $SEEDS; do
  files+=("$OUT/seed${seed}_tier_off/baseline.fasta")
  files+=("$OUT/seed${seed}_tier_off/framework.fasta")
  files+=("$OUT/seed${seed}_tier_on/framework.fasta")
done
"$VENV" "$OUT/count_hits.py" "${files[@]}" > "$OUT/hits.txt" 2>&1
echo "end=$(date -u +%FT%TZ)" >> "$OUT/METADATA.txt"
echo "=== ALL DONE $(date -u +%FT%TZ) ==="
cat "$OUT/hits.txt"
