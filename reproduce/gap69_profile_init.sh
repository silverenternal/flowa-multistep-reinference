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
OUT="verification_outputs/gap69-lineageflow-profile/seed42"

if [[ ! -f "$PROFILES" ]]; then
  echo "[gap69] building Pfam profiles"
  python3 tools/pfam_profile.py \
    --families PF00005 PF00072 PF00183 PF02517 --span 150 --out "$PROFILES"
fi

export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=8
export CUDA_VISIBLE_DEVICES=0

mkdir -p "$OUT"
{
  echo "=== command ==="
  echo "bash reproduce/gap69_profile_init.sh"
  echo "=== start_utc ==="
  date -u +%FT%TZ
  echo "=== gpu ==="
  nvidia-smi --query-gpu=index,memory.used,memory.free,utilization.gpu --format=csv
  echo "=== git ==="
  git rev-parse HEAD
  echo "=== design ==="
  echo "init_profile=conservation; beta=1.0 (m=0); N=1000, NFE=150, R=3, seed 42"
} > "$OUT/METADATA.txt"

"$PY" tools/gen_lineageflow_n1000_fastas.py \
  --seed 42 --n 1000 \
  --upstream-eval-len-bias short \
  --nfe 150 --n-rounds 3 --restart-min-nfe 5 \
  --temperature 1.0 --beta-override 1.0 \
  --init-profile conservation --profile-json "$PROFILES" \
  --outdir "$OUT" 2>&1 | tee "$OUT/run.log"

# MMseqs2 uses a shared relative temp dir (results/mmseqs_tmp) — score serially.
"$PY" tools/gap55_r1_score_fastas.py \
  --run-dir "$OUT" --arms baseline framework --length-bias short \
  2>&1 | tee "$OUT/score.log"

echo "[gap69] EXIT=0 $(date -u +%FT%TZ)"
