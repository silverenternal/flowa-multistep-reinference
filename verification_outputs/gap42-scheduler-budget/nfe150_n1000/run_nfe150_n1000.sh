#!/usr/bin/env bash
# GAP-42f — decisive canonical R1 N=1000 3-seed run at NFE=150 with the
# endpoint chain live (gate open: 150 >= restart_min_nfe=20 -> 3 rounds).
#
# Configuration is identical to GAP-42d (N=1000, chain_on) except
#   * --nfe 150 (was 10)  => the restart-blend gate opens,
#                            effective_n_rounds = 3 (was 1).
# Everything else (scheduler=cosine, temperature=1.0, restart_min_nfe=20,
# upstream_eval_len_bias=short, n_rounds=3) is canonical.
#
# Engineering note (see docs/audit/gap42-scheduler-budget.md §9):
#   A single process leaves the RTX PRO 6000 at ~30-40% SM utilisation
#   because the per-step cost is dominated by the *vendored* pure-Torch
#   incomplete-beta loop (data-dependent `torch.all` sync every iteration,
#   ~69% of step time) and the ESM-2 forward (~29%).  Neither can be
#   rewritten without changing numerics (vendored upstream is frozen;
#   TorchScript/compile variants measured 1e-11..1e-10 drift).  The three
#   seeds are independent, so we run one process per seed concurrently on
#   cuda:0: measured 22.1 s/record solo vs 30.0 s/record at 3-way
#   (2.2x aggregate throughput) with SM utilisation ~100%.  No per-record
#   arithmetic changes, so outputs stay byte-identical.
#
# GPU 0 only.  Resumable per seed via START=<index> (replays RNG).
set -euo pipefail

REPO=/home/hugo/codes/flowa-multistep-reinference
VENV=$REPO/.venvs/lineageflow_venv/bin/python
OUT=${OUT:-/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap42f-nfe150-n1000}
PREMISE=/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41b-nfe150/premise
N=${N:-1000}
NFE=${NFE:-150}
START=${START:-0}
SEEDS=${SEEDS:-"42 43 44"}
PARALLEL=${PARALLEL:-1}
cd "$REPO"
export TMPDIR=/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41-tmp TORCHINDUCTOR_CACHE_DIR=/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41-torchinductor
mkdir -p "$TMPDIR" "$TORCHINDUCTOR_CACHE_DIR" "$OUT"
[ -f "$OUT/count_hits.py" ] || cp "$PREMISE/count_hits.py" "$OUT/"

nvidia-smi > "$OUT/METADATA.gpu" 2>&1 || true
{
  echo "start=$(date -u +%FT%TZ)"
  echo "cell=R1 hmmscan_total_hits"
  echo "N=$N nfe=$NFE n_rounds=3 restart_min_nfe=20 scheduler=cosine temperature=1.0"
  echo "upstream_eval_len_bias=short restart_from_endpoint=TRUE"
  echo "seeds=$SEEDS start_index=$START parallel=$PARALLEL"
  echo "canonical comparison: NFE=10 chain_on 280/281/259; NFE=10 chain_off 275/272/259; baseline 158/159/174"
  echo "expected_effective_n_rounds=3 (gate open at NFE>=20)"
  echo "gpu0_only=TRUE"
} > "$OUT/METADATA.txt"

gen_one() {
  local seed="$1"
  local d="$OUT/seed${seed}"
  mkdir -p "$d"
  echo "=== gen seed=$seed chain_on n=$N nfe=$NFE start=$START $(date -u +%FT%TZ) ==="
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_VISIBLE_DEVICES=0 \
    "$VENV" tools/gen_lineageflow_n1000_fastas.py \
    --seed "$seed" --n "$N" --start-index "$START" --upstream-eval-len-bias short \
    --nfe "$NFE" --n-rounds 3 --restart-min-nfe 20 --temperature 1.0 \
    --scheduler cosine --restart-from-endpoint \
    --outdir "$d" > "$d/gen.log" 2>&1
  echo "  done seed=$seed $(date -u +%FT%TZ)"
  date -u +%FT%TZ > "$d/DONE"
}

if [ "$PARALLEL" = "1" ]; then
  for seed in $SEEDS; do
    gen_one "$seed" &
  done
  wait
else
  for seed in $SEEDS; do
    gen_one "$seed"
  done
fi

echo "=== HMMER $(date -u +%FT%TZ) ==="
files=()
for seed in $SEEDS; do
  files+=("$OUT/seed${seed}/baseline.fasta")
  files+=("$OUT/seed${seed}/framework.fasta")
done
"$VENV" "$OUT/count_hits.py" "${files[@]}" > "$OUT/hits.txt" 2>&1
for seed in $SEEDS; do
  cp "$OUT/seed${seed}/baseline.tblout" "$OUT/seed${seed}/baseline_hits.tbl"
  cp "$OUT/seed${seed}/framework.tblout" "$OUT/seed${seed}/framework_hits.tbl"
done

echo "=== canonical baseline identity check (expect 158/159/174) ==="
grep "baseline.fasta" "$OUT/hits.txt" || true

N_SEEDS=$(echo $SEEDS | wc -w)
if [ "$N_SEEDS" -ge 2 ]; then
  echo "=== paired-t + DL meta (canonical tool) $(date -u +%FT%TZ) ==="
  "$VENV" tools/r1_d004_analysis.py \
    --root "$OUT" --out "$OUT" --seeds $SEEDS --n-per-seed "$N" \
    > "$OUT/analysis.log" 2>&1 || true
  tail -40 "$OUT/analysis.log"
else
  echo "=== single-seed smoke: skipping DL meta (k<2) ==="
fi

echo "end=$(date -u +%FT%TZ)" >> "$OUT/METADATA.txt"
echo "=== ALL DONE $(date -u +%FT%TZ) ==="
cat "$OUT/hits.txt"
