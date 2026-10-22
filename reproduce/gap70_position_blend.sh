#!/usr/bin/env bash
# GAP-70 — position-selective restart blend, three arms, seed 42 only.
#
#   A baseline      (no restart)          control/baseline.fasta
#   B scalar blend  (K7's framework arm)  control/framework.fasta
#   C selective     (m_vec = m * w)       treatment/framework.fasta
#
# Both framework arms are generated here, by this commit, from one config, so
# the C-vs-B comparison never crosses a code era. B is additionally checked
# against K7's own 3.7 % as a sanity read, not as an input.
#
# Two novelty readings exist and only one is usable:
#   * the generator's built-in `novelty` searches the 200-sequence
#     `pfam35/pfam_holdout_targetDB` and saturates at 1.0 (the W280 artefact) —
#     never quoted;
#   * the K7 number needs `mmseqs easy-search` against the canonical 63.8 M
#     Pfam-A DB (`-s 7.5 -e 100`), which is what step 5 does.
#
# Pre-registration: docs/audit/gap70-lineageflow-position-blend.md §0.
# One seed (rule 4). Resumable: any finished step is skipped.
set -euo pipefail

cd "$(dirname "$0")/.."

PY=".venvs/lineageflow_venv/bin/python"
MMSEQS=${MMSEQS:-/home/hugo/bin/mmseqs}
PROFILES="verification_outputs/gap69-lineageflow-profile/profiles.json"
PFAM_DB="data/lineageflow_upstream/databases/pfam_canonical/mmseqs_db/pfam_a_targetDB"
SEED=${SEED:-42}
BASE="verification_outputs/gap70-lineageflow-position/seed${SEED}"
CTRL="$BASE/control"
TRT="$BASE/treatment"

export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=8
export CUDA_VISIBLE_DEVICES=0

# Same headroom guard as GAP-69: an OOM'd adapter silently falls back to the
# bare-RNG draw, which would make arm C indistinguishable from arm B.
NEED_MIB=${NEED_MIB:-20000}
WAIT_MAX_S=${WAIT_MAX_S:-14400}

wait_for_gpu() {
  local waited=0 free_mib
  while :; do
    free_mib=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i 0)
    if (( free_mib >= NEED_MIB )); then
      echo "[gap70] gpu0 free=${free_mib} MiB >= ${NEED_MIB} MiB — starting"
      return 0
    fi
    if (( waited >= WAIT_MAX_S )); then
      echo "[gap70] ABORT: gpu0 free=${free_mib} MiB after ${waited}s" >&2
      exit 3
    fi
    echo "[gap70] waiting for gpu0: free=${free_mib} MiB < ${NEED_MIB} MiB (${waited}s)"
    sleep 60
    waited=$(( waited + 60 ))
  done
}

generate() {  # $1 = outdir, $2 = token-keep-weights mode
  local out="$1" mode="$2"
  if [[ -s "$out/framework.fasta" ]]; then
    echo "[gap70] skip generate $out (framework.fasta present)"
    return 0
  fi
  mkdir -p "$out"
  {
    echo "=== command ==="
    echo "bash reproduce/gap70_position_blend.sh  # SEED=$SEED token_keep_weights=$mode"
    echo "=== start_utc ==="
    date -u +%FT%TZ
    echo "=== gpu ==="
    nvidia-smi --query-gpu=index,memory.used,memory.free,utilization.gpu --format=csv
    echo "=== git ==="
    git rev-parse HEAD
    echo "=== design ==="
    echo "token_keep_weights=$mode; N=1000, NFE=10, R=3, restart_min_nfe=5, seed $SEED"
  } > "$out/METADATA.txt"

  local extra=()
  if [[ "$mode" != "off" ]]; then
    extra=(--token-keep-weights "$mode" --profile-json "$PROFILES")
  fi
  "$PY" tools/gen_lineageflow_n1000_fastas.py \
    --seed "$SEED" --n 1000 \
    --upstream-eval-len-bias short \
    --nfe 10 --n-rounds 3 --restart-min-nfe 5 \
    --temperature 1.0 \
    "${extra[@]}" \
    --outdir "$out" 2>&1 | tee "$out/run.log"
}

if [[ ! -f "$PROFILES" ]]; then
  echo "[gap70] ABORT: $PROFILES missing (build it with tools/pfam_profile.py)" >&2
  exit 2
fi
if [[ ! -f "${PFAM_DB}.dbtype" ]]; then
  echo "[gap70] ABORT: canonical Pfam-A DB missing at $PFAM_DB" >&2
  exit 2
fi

wait_for_gpu
generate "$CTRL" off
wait_for_gpu
generate "$TRT" conservation

# Pairing guarantee: the flag only touches the framework arm, so the baseline
# arm must be byte-identical between the two runs.
if ! cmp -s "$CTRL/baseline.fasta" "$TRT/baseline.fasta"; then
  echo "[gap70] ABORT: baseline arms differ — the runs are not record-paired" >&2
  exit 4
fi

# Validity only: hmmscan against Pfam-A. The built-in novelty is skipped on
# purpose (saturated holdout DB, see the header).
for d in "$CTRL" "$TRT"; do
  if [[ -s "$d/upstream_framework/family_validity_per_seq.jsonl" ]]; then
    echo "[gap70] skip validity $d"
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
    echo "[gap70] skip mmseqs $out"
    return 0
  fi
  mkdir -p "$(dirname "$out")"
  "$MMSEQS" easy-search "$fasta" "$PFAM_DB" "$out" "$(dirname "$out")/mmseqs_tmp" \
    -s 7.5 -e 100 --threads 16
}

score_novelty "$CTRL/baseline.fasta"  "$BASE/m8/baseline.m8"
score_novelty "$CTRL/framework.fasta" "$BASE/m8/control.m8"
score_novelty "$TRT/framework.fasta"  "$BASE/m8/treatment.m8"

"$PY" tools/gap70_position_blend_report.py \
  --baseline-m8  "$BASE/m8/baseline.m8" \
  --control-m8   "$BASE/m8/control.m8" \
  --treatment-m8 "$BASE/m8/treatment.m8" \
  --baseline-fasta  "$CTRL/baseline.fasta" \
  --control-fasta   "$CTRL/framework.fasta" \
  --treatment-fasta "$TRT/framework.fasta" \
  --baseline-validity  "$CTRL/upstream_baseline/family_validity_per_seq.jsonl" \
  --control-validity   "$CTRL/upstream_framework/family_validity_per_seq.jsonl" \
  --treatment-validity "$TRT/upstream_framework/family_validity_per_seq.jsonl" \
  --n-total 1000 --seed "$SEED" \
  --out "$BASE/report_seed${SEED}.json" \
  2>&1 | tee "$BASE/report.log"

echo "[gap70] EXIT=0 $(date -u +%FT%TZ)"
