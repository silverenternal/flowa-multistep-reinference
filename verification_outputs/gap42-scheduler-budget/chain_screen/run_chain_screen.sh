#!/usr/bin/env bash
# GAP-42c — R1 endpoint-chain screen. seeds 42/43/44, N=200, NFE=10, cosine.
#   off : default (byte-stable canonical path)
#   on  : --restart-from-endpoint (Eq. 2 chain live)
# Question: once the chain is actually live, does it move the R1 hit rate
# in a direction-consistent way? Screen only — N=200 cannot decide.
# GPU 0 only. Resumable via START=<index> (replays RNG, byte-equivalent).
set -euo pipefail

REPO=/home/hugo/codes/flowa-multistep-reinference
VENV=$REPO/.venvs/lineageflow_venv/bin/python
OUT=/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41b-nfe150/chain_screen
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
  echo "cmd=$0"
} > "$OUT/METADATA.txt"

gen() {  # gen <seed> <tag> [extra args...]
  local seed="$1" tag="$2"; shift 2
  local d="$OUT/seed${seed}_${tag}"
  mkdir -p "$d"
  echo "=== gen seed=$seed $tag n=$N start=$START $(date -u +%FT%TZ) ==="
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_VISIBLE_DEVICES=0 \
    "$VENV" tools/gen_lineageflow_n1000_fastas.py \
    --seed "$seed" --n "$N" --start-index "$START" --upstream-eval-len-bias short \
    --nfe 10 --n-rounds 3 --restart-min-nfe 5 --temperature 1.0 \
    --scheduler cosine "$@" \
    --outdir "$d" > "$d/gen.log" 2>&1
  echo "  done $(date -u +%FT%TZ)"
}

for seed in $SEEDS; do
  gen "$seed" chain_off
  gen "$seed" chain_on --restart-from-endpoint
done

echo "=== sanity: baseline identical across arms / chain liveness ==="
for seed in $SEEDS; do
  if cmp -s "$OUT/seed${seed}_chain_off/baseline.fasta" "$OUT/seed${seed}_chain_on/baseline.fasta"; then
    echo "seed$seed baseline: IDENTICAL across arms (ok)"
  else
    echo "seed$seed baseline: DIFFERS across arms (unexpected)"
  fi
  if cmp -s "$OUT/seed${seed}_chain_off/framework.fasta" "$OUT/seed${seed}_chain_on/framework.fasta"; then
    echo "seed$seed framework: chain has NO effect"
  else
    echo "seed$seed framework: chain is live"
  fi
done

echo "=== HMMER $(date -u +%FT%TZ) ==="
files=()
for seed in $SEEDS; do
  files+=("$OUT/seed${seed}_chain_off/baseline.fasta")
  files+=("$OUT/seed${seed}_chain_off/framework.fasta")
  files+=("$OUT/seed${seed}_chain_on/framework.fasta")
done
"$VENV" "$OUT/count_hits.py" "${files[@]}" > "$OUT/hits.txt" 2>&1
echo "end=$(date -u +%FT%TZ)" >> "$OUT/METADATA.txt"
echo "=== ALL DONE $(date -u +%FT%TZ) ==="
cat "$OUT/hits.txt"
