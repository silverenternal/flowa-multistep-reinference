#!/usr/bin/env bash
# GAP-70 round 2 — the tempered restart draw, one dose grid, seed 42.
#
#   fresh = (1 - lam) * state + lam * softmax(randn)
#
#   lam = 0  the no-restart end (the draw returns the state unchanged)
#   lam = 1  the shipped D-004b draw (K7's framework arm)
#
# Pre-registration: docs/audit/gap70-r2-tempered-draw.md. Every lam is a point
# on the segment between two already-measured arms, so an interior lam can only
# win if the (novelty, validity) frontier bulges above the chord. The report
# prints the chord residual for exactly that test.
#
# Config is pinned to the K7 measurement (NFE=10, R=3, restart_min_nfe=5,
# temperature 1.0, N=1000, seed 42), not to the GAP-69 config: a different
# config would produce a number that cannot be compared with 3.7 % / 46.6 %.
#
# Novelty is mmseqs against the canonical 63.8 M Pfam-A DB (-s 7.5 -e 100).
# The generator's built-in novelty searches a 200-sequence holdout DB and
# saturates at 1.0 — never quoted.
#
# Resumable: any finished step is skipped.
set -euo pipefail

cd "$(dirname "$0")/.."

PY=".venvs/lineageflow_venv/bin/python"
MMSEQS=${MMSEQS:-/home/hugo/bin/mmseqs}
PFAM_DB="data/lineageflow_upstream/databases/pfam_canonical/mmseqs_db/pfam_a_targetDB"
SEED=${SEED:-42}
N=${N:-1000}
LAMS=${LAMS:-"0 0.1 0.2 0.35 0.5 0.75 1"}
BASE=${BASE:-verification_outputs/gap70-tempered-draw/seed${SEED}}

export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=8
export CUDA_VISIBLE_DEVICES=0

# Same headroom guard as GAP-69/GAP-70: an OOM'd adapter silently falls back to
# the bare-RNG draw, which would make every lam indistinguishable.
NEED_MIB=${NEED_MIB:-20000}
WAIT_MAX_S=${WAIT_MAX_S:-14400}

wait_for_gpu() {
  local waited=0 free_mib
  while :; do
    free_mib=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i 0)
    if (( free_mib >= NEED_MIB )); then
      echo "[gap70r2] gpu0 free=${free_mib} MiB >= ${NEED_MIB} MiB — starting"
      return 0
    fi
    if (( waited >= WAIT_MAX_S )); then
      echo "[gap70r2] ABORT: gpu0 free=${free_mib} MiB after ${waited}s" >&2
      exit 3
    fi
    echo "[gap70r2] waiting for gpu0: free=${free_mib} MiB < ${NEED_MIB} MiB (${waited}s)"
    sleep 60
    waited=$(( waited + 60 ))
  done
}

generate() {  # $1 = lam
  local lam="$1" out="$BASE/lam$1"
  if [[ -s "$out/framework.fasta" ]]; then
    echo "[gap70r2] skip generate lam=$lam (framework.fasta present)"
    return 0
  fi
  mkdir -p "$out"
  {
    echo "=== command ==="
    echo "bash reproduce/gap70_tempered_draw.sh  # SEED=$SEED LAM=$lam"
    echo "=== start_utc ==="
    date -u +%FT%TZ
    echo "=== gpu ==="
    nvidia-smi --query-gpu=index,memory.used,memory.free,utilization.gpu --format=csv
    echo "=== git ==="
    git rev-parse HEAD
    echo "=== design ==="
    echo "restart_draw_lambda=$lam; N=$N, NFE=10, R=3, restart_min_nfe=5, seed $SEED"
  } > "$out/METADATA.txt"
  "$PY" tools/gen_lineageflow_n1000_fastas.py \
    --seed "$SEED" --n "$N" \
    --upstream-eval-len-bias short \
    --nfe 10 --n-rounds 3 --restart-min-nfe 5 \
    --temperature 1.0 \
    --restart-draw-lambda "$lam" \
    --outdir "$out" 2>&1 | tee "$out/run.log"
}

if [[ ! -f "${PFAM_DB}.dbtype" ]]; then
  echo "[gap70r2] ABORT: canonical Pfam-A DB missing at $PFAM_DB" >&2
  exit 2
fi

for lam in $LAMS; do
  wait_for_gpu
  generate "$lam"
done

# Pairing guarantee: the flag only touches the framework arm, so every arm's
# baseline must be byte-identical.
first=""
for lam in $LAMS; do
  if [[ -z "$first" ]]; then first="$BASE/lam$lam/baseline.fasta"; continue; fi
  if ! cmp -s "$first" "$BASE/lam$lam/baseline.fasta"; then
    echo "[gap70r2] ABORT: baseline arm differs at lam=$lam — not record-paired" >&2
    exit 4
  fi
done

# Validity: hmmscan against Pfam-A. The built-in novelty is skipped on purpose.
for lam in $LAMS; do
  d="$BASE/lam$lam"
  if [[ -s "$d/upstream_framework/family_validity_per_seq.jsonl" ]]; then
    echo "[gap70r2] skip validity lam=$lam"
    continue
  fi
  "$PY" tools/gap55_r1_score_fastas.py \
    --run-dir "$d" --arms baseline framework --length-bias short \
    --metrics family_validity \
    2>&1 | tee "$d/score.log"
done

# Canonical-DB novelty (the K7 definition). Serial: mmseqs uses one tmp dir.
score_novelty() {  # $1 = fasta, $2 = out.m8
  local fasta="$1" out="$2"
  if [[ -s "$out" ]]; then
    echo "[gap70r2] skip mmseqs $out"
    return 0
  fi
  mkdir -p "$(dirname "$out")"
  "$MMSEQS" easy-search "$fasta" "$PFAM_DB" "$out" "$(dirname "$out")/mmseqs_tmp" \
    -s 7.5 -e 100 --threads 16
}

score_novelty "$BASE/lam0/baseline.fasta" "$BASE/m8/baseline.m8"
for lam in $LAMS; do
  score_novelty "$BASE/lam$lam/framework.fasta" "$BASE/m8/lam$lam.m8"
done

"$PY" tools/gap70_tempered_report.py \
  --root "$BASE" --lams "$LAMS" --n-total "$N" --seed "$SEED" \
  --out "$BASE/report_seed${SEED}.json" 2>&1 | tee "$BASE/report.log"

echo "[gap70r2] EXIT=0 $(date -u +%FT%TZ)"
