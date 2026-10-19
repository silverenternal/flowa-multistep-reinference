#!/usr/bin/env bash
# GAP-42 — equal-NFE scheduler A/B smoke: cosine vs codimension_sheet.
# N=20, seed 42, NFE=10, gate-open. After the per-round budget-conservation
# fix both arms spend exactly 10 Euler steps (cosine [3,3,4] vs codim [4,3,3]).
# Purpose: measure whether the math scheduler produces any real signal on R1
# before committing to the N=200 screen.
set -euo pipefail

REPO=/home/hugo/codes/flowa-multistep-reinference
VENV=$REPO/.venvs/lineageflow_venv/bin/python
OUT=/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41b-nfe150/scheduler_ab
N=${N:-20}
cd "$REPO"
export TMPDIR=/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41-tmp TORCHINDUCTOR_CACHE_DIR=/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41-torchinductor
mkdir -p "$TMPDIR" "$TORCHINDUCTOR_CACHE_DIR" "$OUT"
cp /home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41b-nfe150/premise/count_hits.py "$OUT/"

gen() {  # gen <scheduler>
  local sched="$1"
  local d="$OUT/nfe10_${sched}"
  mkdir -p "$d"
  echo "=== gen scheduler=$sched n=$N nfe=10 $(date -u +%FT%TZ) ==="
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_VISIBLE_DEVICES=0 \
    "$VENV" tools/gen_lineageflow_n1000_fastas.py \
    --seed 42 --n "$N" --start-index 0 --upstream-eval-len-bias short \
    --nfe 10 --n-rounds 3 --restart-min-nfe 5 --temperature 1.0 \
    --scheduler "$sched" \
    --outdir "$d" > "$d/gen.log" 2>&1
  echo "  done $(date -u +%FT%TZ)"
}

gen cosine
gen codimension_sheet

echo "=== manifest check ==="
for sched in cosine codimension_sheet; do
  "$VENV" - "$OUT/nfe10_${sched}/manifest.json" "$sched" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
print(sys.argv[2], "scheduler_name=", m.get("scheduler_name"),
      "nfe_per_record=", m.get("nfe_per_record"),
      "n_rounds=", m.get("n_rounds"))
PY
done

echo "=== byte compare (baseline should be identical; framework should differ) ==="
cmp "$OUT/nfe10_cosine/baseline.fasta" "$OUT/nfe10_codimension_sheet/baseline.fasta" \
  && echo "baseline: BYTE-IDENTICAL" || echo "baseline: DIFFER (unexpected)"
cmp "$OUT/nfe10_cosine/framework.fasta" "$OUT/nfe10_codimension_sheet/framework.fasta" \
  && echo "framework: BYTE-IDENTICAL" || echo "framework: DIFFER"

echo "=== HMMER $(date -u +%FT%TZ) ==="
"$VENV" "$OUT/count_hits.py" \
  "$OUT/nfe10_cosine/baseline.fasta" \
  "$OUT/nfe10_cosine/framework.fasta" \
  "$OUT/nfe10_codimension_sheet/framework.fasta" \
  > "$OUT/hits.txt" 2>&1
echo "=== ALL DONE $(date -u +%FT%TZ) ==="
cat "$OUT/hits.txt"
