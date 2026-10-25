#!/usr/bin/env bash
# GAP-79 — pre-registered dose screen (docs/audit/gap79-r1-family-lever.md §0.4).
#
#   N=200, seed 42, NFE=150, R=3, beta=1.0, T in {0.5, 0.2, 0.1, 0.05, 0.02}
#
# A screen number may choose the dose; it may never be quoted. The confirmation
# arm (N=1000, seeds 42/43/44) is a separate run and only the selected T goes
# there.
#
# Generation runs concurrently — each dose is an independent process with its
# own outdir and its own seed — but scoring is serial, because MMseqs2 shares
# `results/mmseqs_tmp`. `SCORE=0` in gap69_profile_init.sh splits the two.
#
# Cost measured 2026-10-25: N=20 end-to-end 5m41s (both arms + scoring), i.e.
# ~17 s/record, so N=200 is ~55 min per dose. Parallelism 3 keeps the whole
# screen inside one GPU (3 x ~13 GB) and ~2 h wall clock.
set -euo pipefail

cd "$(dirname "$0")/.."

PY=".venvs/lineageflow_venv/bin/python"
SEED=${SEED:-42}
N=${N:-200}
PAR=${PAR:-3}
DOSES=${DOSES:-"0.5 0.2 0.1 0.05 0.02"}
ROOT=${ROOT:-verification_outputs/gap79-r1-temperature}

mkdir -p "$ROOT"
{
  echo "=== command ==="
  echo "bash reproduce/gap79_temperature_screen.sh  # SEED=$SEED N=$N PAR=$PAR"
  echo "=== start_utc ==="
  date -u +%FT%TZ
  echo "=== gpu ==="
  nvidia-smi --query-gpu=index,memory.used,memory.free,utilization.gpu --format=csv
  echo "=== git ==="
  git rev-parse HEAD
  echo "=== design ==="
  echo "seed=$SEED N=$N NFE=150 R=3 beta=1.0 doses=[$DOSES]"
} > "$ROOT/METADATA.txt"

: > "$ROOT/FAILED.txt"

gen_one() {
  local t="$1"
  local out="$ROOT/seed${SEED}_T${t}"
  echo "[gap79] generate T=$t -> $out"
  SEED="$SEED" N="$N" TEMPERATURE="$t" SCORE=0 OUT="$out" \
    bash reproduce/gap69_profile_init.sh > "$out.log" 2>&1 \
    || { echo "T=$t generation failed (see $out.log)" >> "$ROOT/FAILED.txt"; return 1; }
}

export -f gen_one
export ROOT SEED N

# xargs gives the bounded pool without leaving background jobs behind.
printf '%s\n' $DOSES | xargs -P "$PAR" -I{} bash -c 'gen_one {}' || true

# Serial scoring — shared MMseqs2 temp dir.
for t in $DOSES; do
  out="$ROOT/seed${SEED}_T${t}"
  if [[ ! -f "$out/framework.fasta" ]]; then
    echo "[gap79] skip scoring T=$t (no framework.fasta)"
    continue
  fi
  echo "[gap79] score T=$t"
  "$PY" tools/gap55_r1_score_fastas.py \
    --run-dir "$out" --arms baseline framework --length-bias short \
    2>&1 | tee "$out/score.log"
done

echo "[gap79] EXIT=0 $(date -u +%FT%TZ)"
