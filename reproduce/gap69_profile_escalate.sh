#!/usr/bin/env bash
# GAP-69 — confirmatory escalation to seeds 43/44.
#
# Pre-registered trigger: docs/audit/gap69-lineageflow-profile.md §0.4 rule 1.
# At seed 42 the conservation arm scored H_C = 2329 vs the init-only arm's
# H_B = 284 (8.20x), with a paired per-record bootstrap CI on H_C - H_B of
# [+1.744, +2.354] hits/record. Rule 1 therefore fired, and only then does
# this script exist.
#
# Each seed needs TWO generations because arm B (init-only) was only ever run
# at seed 42 on this config (the D-004b attribution runs are NFE=10 and are not
# comparable). Both runs emit a baseline arm; those must stay byte-identical to
# each other, which is asserted below and is the record-pairing guarantee.
#
# Cost: ~7.5 h generation + ~14 min scoring per run, 4 runs, serial on cuda:0.
# Serial is deliberate — MMseqs2 writes into a shared relative temp dir.
#
# Resumable: a step whose upstream_eval.json already exists is skipped, so a
# restart never re-spends a 7.5 h generation.
set -euo pipefail

cd "$(dirname "$0")/.."

SEEDS=${SEEDS:-"43 44"}
OUTROOT="verification_outputs/gap69-lineageflow-profile"

for seed in $SEEDS; do
  for variant in "off:_init_only" "conservation:"; do
    init_profile=${variant%%:*}
    tag=${variant#*:}
    dir="$OUTROOT/seed${seed}${tag}"
    if [[ -f "$dir/upstream_eval.json" ]]; then
      echo "[gap69] seed=$seed init_profile=$init_profile — already scored, skipping"
      continue
    fi
    echo "[gap69] seed=$seed init_profile=$init_profile -> $dir"
    SEED="$seed" INIT_PROFILE="$init_profile" TAG="$tag" \
      bash reproduce/gap69_profile_init.sh
  done

  # Record pairing: the baseline arm must not depend on --init-profile.
  if ! cmp -s "$OUTROOT/seed${seed}_init_only/baseline.fasta" \
              "$OUTROOT/seed${seed}/baseline.fasta"; then
    echo "[gap69] FATAL: seed $seed baseline arm differs between the two runs" >&2
    exit 4
  fi
  echo "[gap69] seed $seed baseline arms are byte-identical (pairing ok)"
done

echo "[gap69] ESCALATION_DONE $(date -u +%FT%TZ)"
