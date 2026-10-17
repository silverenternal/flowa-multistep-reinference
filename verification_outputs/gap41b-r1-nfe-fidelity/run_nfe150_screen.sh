#!/usr/bin/env bash
# GAP-41b follow-up — n=3 N=200 NFE=150 legacy screen.
# Seeds 43/44 at N=200, NFE=150, legacy arm (seed 42 reused from the premise).
# Question: is the premise's framework-vs-baseline +11 direction-consistent 3/3?
# GPU 0 only. Resumable via --start-index.
set -euo pipefail

REPO=/home/hugo/codes/flowa-multistep-reinference
VENV=$REPO/.venvs/lineageflow_venv/bin/python
OUT=/home/hugo/gap41b-nfe150/nfe150_screen
PREMISE=/home/hugo/gap41b-nfe150/premise
N=${N:-200}
START=${START:-0}
cd "$REPO"
export TMPDIR=/home/hugo/gap41-tmp TORCHINDUCTOR_CACHE_DIR=/home/hugo/gap41-torchinductor
mkdir -p "$TMPDIR" "$TORCHINDUCTOR_CACHE_DIR" "$OUT"
cp "$PREMISE/count_hits.py" "$OUT/"

gen() {  # gen <seed>
  local seed="$1"
  local d="$OUT/seed${seed}_nfe150_legacy"
  mkdir -p "$d"
  echo "=== gen seed=$seed nfe=150 n=$N start=$START $(date -u +%FT%TZ) ==="
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_VISIBLE_DEVICES=0 \
    "$VENV" tools/gen_lineageflow_n1000_fastas.py \
    --seed "$seed" --n "$N" --start-index "$START" --upstream-eval-len-bias short \
    --nfe 150 --n-rounds 3 --restart-min-nfe 5 --temperature 1.0 \
    --outdir "$d" > "$d/gen.log" 2>&1
  echo "  done $(date -u +%FT%TZ)"
}

gen 43
gen 44

echo "=== HMMER $(date -u +%FT%TZ) ==="
"$VENV" "$OUT/count_hits.py" \
  "$PREMISE/seed42_nfe150_legacy/baseline.fasta" \
  "$PREMISE/seed42_nfe150_legacy/framework.fasta" \
  "$OUT/seed43_nfe150_legacy/baseline.fasta" \
  "$OUT/seed43_nfe150_legacy/framework.fasta" \
  "$OUT/seed44_nfe150_legacy/baseline.fasta" \
  "$OUT/seed44_nfe150_legacy/framework.fasta" \
  > "$OUT/hits.txt" 2>&1
echo "=== ALL DONE $(date -u +%FT%TZ) ==="
cat "$OUT/hits.txt"
