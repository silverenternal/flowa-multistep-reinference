#!/bin/bash
# =============================================================================
# verify_all_headlines.sh — Master one-shot verification of all 7 R-level cells
#
# Runs every per-cell reproduction script in numeric order. Exits non-zero
# if any cell fails; prints per-cell status (PASS/FAIL) and a final summary.
#
# USAGE:
#   bash reproduce/verify_all_headlines.sh
#
# EXPECTED OUTPUT:
#   "OK: All 7/7 R-level headlines verified"
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

for script in reproduce/[0-9]*.sh; do
  [ -f "${script}" ] || continue
  base=$(basename "${script}")
  n_total=$((n_total + 1))
  printf "\n=== [%d/7] %s ===\n" "${n_total}" "${base}"
  if bash "${script}"; then
    n_pass=$((n_pass + 1))
  else
    n_fail=$((n_fail + 1))
    failed+=("${base}")
  fi
done

echo
echo "================================================================"
echo "  Summary: ${n_pass}/${n_total} R-level cells verified"
if [ "${n_fail}" -gt 0 ]; then
  echo "  FAILED cells:"
  for f in "${failed[@]}"; do
    echo "    - ${f}"
  done
  echo "FAIL: ${n_fail} of ${n_total} cells failed verification"
  exit 1
fi
echo "OK: All ${n_pass}/${n_total} R-level headlines verified"
echo "================================================================"
exit 0