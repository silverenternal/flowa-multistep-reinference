#!/usr/bin/env bash
# GAP-41b premise test — does NFE move the R1 HMMER metric / the tier lever?
# N=200, seed 42, arms {legacy, tier}, NFE in {10, 150}, gate open, GPU 0 only.
# Resumable: re-run with --start-index 200 --n 1000 to extend the same dir.
set -euo pipefail

REPO=/home/hugo/codes/flowa-multistep-reinference
VENV=$REPO/.venvs/lineageflow_venv/bin/python
OUT=/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41b-nfe150/premise
BASELINE_JSONL=$REPO/verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/foldability.jsonl
N=${N:-200}
START=${START:-0}
cd "$REPO"
export TMPDIR=/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41-tmp TORCHINDUCTOR_CACHE_DIR=/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41-torchinductor
mkdir -p "$TMPDIR" "$TORCHINDUCTOR_CACHE_DIR" "$OUT"
cp /home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41-n1000/count_hits.py "$OUT/" 2>/dev/null || cp /home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap40-n1000-work/count_hits.py "$OUT/"

gen() {  # gen <tag> <nfe> <extra-flags...>
  local tag="$1"; shift
  local nfe="$1"; shift
  local d="$OUT/seed42_${tag}"
  mkdir -p "$d"
  echo "=== gen $tag nfe=$nfe n=$N start=$START $(date -u +%FT%TZ) ==="
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_VISIBLE_DEVICES=0 \
    "$VENV" tools/gen_lineageflow_n1000_fastas.py \
    --seed 42 --n "$N" --start-index "$START" --upstream-eval-len-bias short \
    --nfe "$nfe" --n-rounds 3 --restart-min-nfe 5 --temperature 1.0 \
    "$@" --outdir "$d" > "$d/gen.log" 2>&1
  echo "  done $(date -u +%FT%TZ)"
}

# --- NFE=10 (cheap) ---
gen nfe10_legacy 10
gen nfe10_tier   10 --tier-aware-n-cap 0.5 \
  --tier-aware-baseline-metrics-jsonl "$BASELINE_JSONL"
# --- NFE=150 (upstream budget) ---
gen nfe150_legacy 150
gen nfe150_tier   150 --tier-aware-n-cap 0.5 \
  --tier-aware-baseline-metrics-jsonl "$BASELINE_JSONL"

echo "=== HMMER $(date -u +%FT%TZ) ==="
"$VENV" "$OUT/count_hits.py" \
  "$OUT"/seed42_nfe10_legacy/baseline.fasta \
  "$OUT"/seed42_nfe10_legacy/framework.fasta \
  "$OUT"/seed42_nfe10_tier/framework.fasta \
  "$OUT"/seed42_nfe150_legacy/baseline.fasta \
  "$OUT"/seed42_nfe150_legacy/framework.fasta \
  "$OUT"/seed42_nfe150_tier/framework.fasta \
  > "$OUT/hits.txt" 2>&1
echo "=== ALL DONE $(date -u +%FT%TZ) ==="
cat "$OUT/hits.txt"
