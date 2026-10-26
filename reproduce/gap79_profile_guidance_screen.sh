#!/usr/bin/env bash
# GAP-79 lever 3 — pre-registered in-loop profile-drift screen.
#   docs/audit/gap79-r1-family-lever.md §3.4
#
#   N=200, seed 42, NFE=150, R=3, beta=1.0, arm C init (T=1.0)
#   control = arm C without drift
#   doses   = weight in {0.5, 2, 8, 32, 128}, t_start = 0.0
#
# A screen number may choose the dose; it may never be quoted. The
# confirmation arm (N=1000, seeds 42/43/44) is a separate run and only the
# selected weight goes there.
#
# §3.8 (F3) — round 1 pointed the drift at the GAP-69 150-slot *resampled*
# profile. That profile's argmax is a stretched sequence: its own family's HMM
# does not recognise it for any LENG != 150 (PF00072 111, PF00183 518,
# PF02517 93), so round 1 measured an invalid target, not the lever. This
# script now builds a native-length target (``--span 0``) and keeps the init
# prior on the pre-registered 150-slot file.
#
# Generation runs concurrently — each cell is an independent process with its
# own outdir — but scoring is serial, because MMseqs2 shares
# `results/mmseqs_tmp`. Only the `framework` arm is scored: the baseline arm
# is byte-identical across cells (same seed, same N) and is not the control
# for this lever.
#
# Cost, from the temperature screen (2026-10-25): ~17 s/record for both arms
# plus scoring, so ~50 min per cell at N=200; 6 cells at PAR=3 is ~2 h wall
# clock inside one GPU.
set -euo pipefail

cd "$(dirname "$0")/.."

PY=".venvs/lineageflow_venv/bin/python"
SEED=${SEED:-42}
N=${N:-200}
PAR=${PAR:-3}
T0=${T0:-0.0}
WEIGHTS=${WEIGHTS:-"0.5 2 8 32 128"}
ROOT=${ROOT:-verification_outputs/gap79-r1-guidance/native/seed${SEED}}
GUIDANCE_PROFILES=${GUIDANCE_PROFILES:-verification_outputs/gap79-native-profiles/profiles_native.json}
export GUIDANCE_PROFILES

# Native-length target (§3.8). Idempotent: the file is small and derived.
if [[ ! -f "$GUIDANCE_PROFILES" ]]; then
  "$PY" tools/pfam_profile.py \
    --families PF00005 PF00072 PF00183 PF02517 --span 0 \
    --out "$GUIDANCE_PROFILES"
fi

mkdir -p "$ROOT"
{
  echo "=== command ==="
  echo "bash reproduce/gap79_profile_guidance_screen.sh  # SEED=$SEED N=$N PAR=$PAR"
  echo "=== start_utc ==="
  date -u +%FT%TZ
  echo "=== gpu ==="
  nvidia-smi --query-gpu=index,memory.used,memory.free,utilization.gpu --format=csv
  echo "=== git ==="
  git rev-parse HEAD
  echo "=== design ==="
  echo "seed=$SEED N=$N NFE=150 R=3 beta=1.0 init=conservation T=1.0 t_start=$T0 weights=[$WEIGHTS]"
  echo "guidance_profile_json=$GUIDANCE_PROFILES"
} > "$ROOT/METADATA.txt"

: > "$ROOT/FAILED.txt"

gen_one() {
  local tag="$1" w="$2"
  local out="$ROOT/$tag"
  echo "[gap79g] generate $tag (weight=$w) -> $out"
  SEED="$SEED" N="$N" INIT_PROFILE=conservation TEMPERATURE=1.0 \
    GUIDANCE_W="$w" GUIDANCE_T0="$T0" SCORE=0 OUT="$out" \
    bash reproduce/gap69_profile_init.sh > "$out.log" 2>&1 \
    || { echo "$tag generation failed (see $out.log)" >> "$ROOT/FAILED.txt"; return 1; }
}

export -f gen_one
export ROOT SEED N T0

# control first (tag, weight) then each dose; xargs bounds the pool.
{
  echo "control 0"
  for w in $WEIGHTS; do echo "W${w} ${w}"; done
} | xargs -P "$PAR" -L 1 bash -c 'gen_one "$0" "$1"' || true

# Serial scoring — shared MMseqs2 temp dir.
for tag in control $(for w in $WEIGHTS; do echo "W${w}"; done); do
  out="$ROOT/$tag"
  if [[ ! -f "$out/framework.fasta" ]]; then
    echo "[gap79g] skip scoring $tag (no framework.fasta)"
    continue
  fi
  echo "[gap79g] score $tag"
  "$PY" tools/gap55_r1_score_fastas.py \
    --run-dir "$out" --arms framework --length-bias short \
    2>&1 | tee "$out/score.log"
done

echo "[gap79g] EXIT=0 $(date -u +%FT%TZ)"
