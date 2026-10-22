#!/usr/bin/env bash
# GAP-69 — R1 profile-aware perturbation (arm C) at the pre-registered config.
#
#   seed 42, N=1000, NFE=150, R=3, beta=1.0 (m=0, no memory), same prior.
#
# The baseline arm is generated in the same run and must stay byte-identical to
# `verification_outputs/gap58-r1-beta1-n1000/seed42/baseline.fasta` (the
# `--init-profile` flag only touches the framework arm's fresh-restart state),
# so the arms stay record-paired with the existing init-only run.
#
# Pre-registration: docs/audit/gap69-lineageflow-profile.md §0.
# Only seed 42 runs unless §0.4 rule 1 fires. No seed shopping.
set -euo pipefail

cd "$(dirname "$0")/.."

PY=".venvs/lineageflow_venv/bin/python"
PROFILES="verification_outputs/gap69-lineageflow-profile/profiles.json"

# Defaults reproduce the pre-registered seed-42 arm C exactly. The same script
# is reused for the seeds 43/44 escalation (SEED=43 TAG=_init_only INIT_PROFILE=off
# produces arm B on the same config) so there is one code path, not two.
SEED=${SEED:-42}
INIT_PROFILE=${INIT_PROFILE:-conservation}
TAG=${TAG:-}
OUT=${OUT:-verification_outputs/gap69-lineageflow-profile/seed${SEED}${TAG}}

if [[ ! -f "$PROFILES" ]]; then
  echo "[gap69] building Pfam profiles"
  python3 tools/pfam_profile.py \
    --families PF00005 PF00072 PF00183 PF02517 --span 150 --out "$PROFILES"
fi

export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=8
export CUDA_VISIBLE_DEVICES=0

# GAP-69 — GPU headroom pre-flight. The 2026-10-22 attempt OOM'd on a shared
# cuda:0 (three ~21.6 GB neighbours) and `_write_framework_arm` silently
# substituted the bare-RNG draw for 1000/1000 records. The generator now fails
# closed on any fallback, but that still wastes a multi-hour run — so wait for
# the memory first. `NEED_MIB` covers the observed ~13 GB peak plus slack.
NEED_MIB=${NEED_MIB:-20000}
WAIT_MAX_S=${WAIT_MAX_S:-14400}
waited=0
while :; do
  free_mib=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i 0)
  if (( free_mib >= NEED_MIB )); then
    echo "[gap69] gpu0 free=${free_mib} MiB >= ${NEED_MIB} MiB — starting"
    break
  fi
  if (( waited >= WAIT_MAX_S )); then
    echo "[gap69] ABORT: gpu0 free=${free_mib} MiB after ${waited}s" >&2
    exit 3
  fi
  echo "[gap69] waiting for gpu0: free=${free_mib} MiB < ${NEED_MIB} MiB (${waited}s)"
  sleep 60
  waited=$(( waited + 60 ))
done

mkdir -p "$OUT"
{
  echo "=== command ==="
  echo "bash reproduce/gap69_profile_init.sh  # SEED=$SEED INIT_PROFILE=$INIT_PROFILE TAG=$TAG"
  echo "=== start_utc ==="
  date -u +%FT%TZ
  echo "=== gpu ==="
  nvidia-smi --query-gpu=index,memory.used,memory.free,utilization.gpu --format=csv
  echo "=== git ==="
  git rev-parse HEAD
  echo "=== design ==="
  echo "init_profile=$INIT_PROFILE; beta=1.0 (m=0); N=1000, NFE=150, R=3, seed $SEED"
} > "$OUT/METADATA.txt"

PROFILE_ARGS=()
if [[ "$INIT_PROFILE" != "off" ]]; then
  PROFILE_ARGS=(--init-profile "$INIT_PROFILE" --profile-json "$PROFILES")
fi

"$PY" tools/gen_lineageflow_n1000_fastas.py \
  --seed "$SEED" --n 1000 \
  --upstream-eval-len-bias short \
  --nfe 150 --n-rounds 3 --restart-min-nfe 5 \
  --temperature 1.0 --beta-override 1.0 \
  "${PROFILE_ARGS[@]}" \
  --outdir "$OUT" 2>&1 | tee "$OUT/run.log"

# MMseqs2 uses a shared relative temp dir (results/mmseqs_tmp) — score serially.
"$PY" tools/gap55_r1_score_fastas.py \
  --run-dir "$OUT" --arms baseline framework --length-bias short \
  2>&1 | tee "$OUT/score.log"

echo "[gap69] EXIT=0 $(date -u +%FT%TZ)"
