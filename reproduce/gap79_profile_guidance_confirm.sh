#!/usr/bin/env bash
# GAP-79 lever 3 — the §3.5 confirmation run.
#   docs/audit/gap79-r1-family-lever.md §3.5 (bar) + §3.9 (statistic)
#
#   Only the weight the screen selected runs, at N=1000, seeds 42/43/44.
#   Each seed is a full screen-shaped run (control + one dose), so the
#   per-record pairing by qid holds inside a seed.
#
#   No seed top-ups: 42/43/44 are the pre-registered three. If a seed fails
#   to produce framework.fasta the run is INCOMPLETE, not re-drawn.
#
# Cost: 6 cells at N=1000 (2 per seed x 3 seeds). At PAR=2 that is ~2.5 h per
# seed, ~7.5 h wall clock.
set -euo pipefail

cd "$(dirname "$0")/.."

WEIGHT=${WEIGHT:?set WEIGHT to the weight the screen selected}
SEEDS=${SEEDS:-"42 43 44"}
N=${N:-1000}
PAR=${PAR:-2}
BASE=${BASE:-verification_outputs/gap79-r1-guidance/native}

for seed in $SEEDS; do
  echo "=== GAP-79 confirmation: seed $seed, weight $WEIGHT, N=$N ==="
  SEED="$seed" N="$N" PAR="$PAR" WEIGHTS="$WEIGHT" \
    ROOT="$BASE/seed$seed" \
    bash reproduce/gap79_profile_guidance_screen.sh
done

echo "=== GAP-79 confirmation: report ==="
.venvs/lineageflow_venv/bin/python tools/gap79_confirmation_report.py \
  --root "$BASE" --weight "$WEIGHT" --seeds $SEEDS \
  --out "$BASE/confirm_report.json" 2>&1 | tee "$BASE/confirm_report.log"
