#!/usr/bin/env bash
# GAP-42b — R1 endpoint-chain smoke. N=20, seed 42, NFE=10, cosine.
#   off : default (must reproduce the archived GAP-42 cosine arm byte-for-byte)
#   on  : --restart-from-endpoint (Eq. 2 chain live)
set -euo pipefail

REPO=/home/hugo/codes/flowa-multistep-reinference
VENV=$REPO/.venvs/lineageflow_venv/bin/python
OUT=/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41b-nfe150/chain_smoke
N=${N:-20}
cd "$REPO"
export TMPDIR=/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41-tmp TORCHINDUCTOR_CACHE_DIR=/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41-torchinductor
mkdir -p "$TMPDIR" "$TORCHINDUCTOR_CACHE_DIR" "$OUT"
cp /home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41b-nfe150/premise/count_hits.py "$OUT/"

gen() {  # gen <tag> [extra args...]
  local tag="$1"; shift
  local d="$OUT/$tag"
  mkdir -p "$d"
  echo "=== gen $tag n=$N nfe=10 $(date -u +%FT%TZ) ==="
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_VISIBLE_DEVICES=0 \
    "$VENV" tools/gen_lineageflow_n1000_fastas.py \
    --seed 42 --n "$N" --start-index 0 --upstream-eval-len-bias short \
    --nfe 10 --n-rounds 3 --restart-min-nfe 5 --temperature 1.0 \
    --scheduler cosine "$@" \
    --outdir "$d" > "$d/gen.log" 2>&1
  echo "  done $(date -u +%FT%TZ)"
}

gen chain_off
gen chain_on --restart-from-endpoint

echo "=== manifests ==="
for tag in chain_off chain_on; do
  "$VENV" - "$OUT/$tag/manifest.json" "$tag" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
print(sys.argv[2], "restart_from_endpoint=", m.get("restart_from_endpoint"),
      "scheduler=", m.get("scheduler_name"))
PY
done

echo "=== chain_off vs archived GAP-42 cosine arm ==="
ARCH=/home/hugo/codes/flowa-multistep-reinference/verification_outputs/gap42-scheduler-budget/scheduler_ab/nfe10_cosine
md5sum "$OUT/chain_off/framework.fasta" "$ARCH/framework.fasta"
cmp "$OUT/chain_off/framework.fasta" "$ARCH/framework.fasta" \
  && echo "chain_off: BYTE-IDENTICAL to archive (byte-stable default)" \
  || echo "chain_off: DIFFERS from archive (unexpected)"

echo "=== chain_off vs chain_on ==="
cmp "$OUT/chain_off/framework.fasta" "$OUT/chain_on/framework.fasta" \
  && echo "chain_on: BYTE-IDENTICAL (chain has no effect)" \
  || echo "chain_on: DIFFER (chain is live)"

echo "=== HMMER $(date -u +%FT%TZ) ==="
"$VENV" "$OUT/count_hits.py" \
  "$OUT/chain_off/baseline.fasta" \
  "$OUT/chain_off/framework.fasta" \
  "$OUT/chain_on/framework.fasta" \
  > "$OUT/hits.txt" 2>&1
echo "=== ALL DONE $(date -u +%FT%TZ) ==="
cat "$OUT/hits.txt"
