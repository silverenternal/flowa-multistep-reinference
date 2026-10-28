#!/bin/bash
# =============================================================================
# verify_all_headlines.sh — Master one-shot verification of the 7 R-level cells
#
# Runs the per-cell reproduction scripts 01-08 in numeric order (7 cells;
# R6 has a second, recipe-level verifier in 08). Exits non-zero if any cell
# fails; prints per-cell status and a final summary.
#
# USAGE:
#   bash reproduce/verify_all_headlines.sh
#
# EXPECTED OUTPUT:
#   "OK: All 8/8 reproduction checks verified"
#
# This script is safe to invoke in CI; each per-cell script verifies the
# headline from the byte-stable verification_outputs/ artefact and prints
# "OK" or "FAIL" accordingly. The actual re-execution sweep commands are
# commented out inside each per-cell script (cells range from 30min GPU to
# 50h CPU).
# =============================================================================

set -euo pipefail

REPRODUCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${REPRODUCE_DIR}/.."

n_total=0
n_pass=0
n_fail=0
failed=()

echo "================================================================"
echo "  Master R-level headline verification (reproduce/)"
echo "  REPO: $(pwd)"
echo "  Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "================================================================"

# Explicit list: `reproduce/[0-9]*.sh` also matches this master's sibling
# 09_verify_all_cell_recipes.sh (a different master covering the 11 cells),
# which made the count read 8/9 and the "[i/7]" prefix lie.
scripts=(reproduce/0[1-8]_*.sh)
n_scripts=${#scripts[@]}

for script in "${scripts[@]}"; do
  [ -f "${script}" ] || continue
  base=$(basename "${script}")
  n_total=$((n_total + 1))
  printf "\n=== [%d/%d] %s ===\n" "${n_total}" "${n_scripts}" "${base}"
  if bash "${script}"; then
    n_pass=$((n_pass + 1))
  else
    n_fail=$((n_fail + 1))
    failed+=("${base}")
  fi
done

echo
echo "================================================================"
echo "  Summary: ${n_pass}/${n_total} reproduction checks verified (7 R-level cells + the R6 recipe check)"
if [ "${n_fail}" -gt 0 ]; then
  echo "  FAILED cells:"
  for f in "${failed[@]}"; do
    echo "    - ${f}"
  done
  echo "FAIL: ${n_fail} of ${n_total} checks failed verification"
  exit 1
fi
echo "OK: All ${n_pass}/${n_total} reproduction checks verified"
echo "================================================================"
exit 0