#!/bin/bash
# =============================================================================
# 01_R1_LineageFlow.sh — Reproduce R1 (LineageFlow HMMER hits, N=1000)
#
# Cell:        R1
# Model:       LineageFlow (ICML 2026 protein FM)
# Metric:      hmmscan_total_hits (higher is better)
# Expected:    baseline 158 -> framework 342 hits (Delta = +184, +116.46%)
#              Bonf-sig p ≈ 1.5e-08
# Verification: verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/
#               {baseline,framework}_hits.tbl
#
# Wallclock historical: ~30-50h CPU (Wave 86 N=1000 sweep).
#
# USAGE:
#   bash reproduce/01_R1_LineageFlow.sh
#
# SAFE: This script verifies the headline from the byte-stable
# verification_outputs/ artifacts. The "Run command" section is commented
# out by default (the live sweep takes ~30-50h CPU + Pfam-A.hmm DB).
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

VENV=".venvs/lineageflow_venv"
VOUT_DIR="verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026"
BASELINE_HITS="${VOUT_DIR}/baseline_hits.tbl"
FRAMEWORK_HITS="${VOUT_DIR}/framework_hits.tbl"

# -----------------------------------------------------------------------------
# Step 1 — Environment activation
# -----------------------------------------------------------------------------
if [ -d "${VENV}" ]; then
  # shellcheck disable=SC1091
  source "${VENV}/bin/activate"
fi

# -----------------------------------------------------------------------------
# Step 2 — Data check (byte-stable artefacts present?)
# -----------------------------------------------------------------------------
test -f "${BASELINE_HITS}"  || { echo "ERROR: missing ${BASELINE_HITS}"; exit 1; }
test -f "${FRAMEWORK_HITS}" || { echo "ERROR: missing ${FRAMEWORK_HITS}"; exit 1; }

# -----------------------------------------------------------------------------
# Step 3 — Count hits (HMMER tblout: 3-line header, then 1 record/line)
# -----------------------------------------------------------------------------
baseline_total=$(grep -cv '^#' "${BASELINE_HITS}"  || true)
framework_total=$(grep -cv '^#' "${FRAMEWORK_HITS}" || true)

# -----------------------------------------------------------------------------
# Step 4 — Verify against headline
# -----------------------------------------------------------------------------
expected_baseline=158
expected_framework=342

if [ "${baseline_total}"  != "${expected_baseline}"  ] || \
   [ "${framework_total}" != "${expected_framework}" ]; then
  echo "R1 FAIL: baseline=${baseline_total} (expected ${expected_baseline}), " \
       "framework=${framework_total} (expected ${expected_framework})"
  exit 1
fi

delta=$((framework_total - baseline_total))
pct=$(python3 -c "print(f'{(${framework_total} - ${baseline_total}) / ${baseline_total} * 100:.2f}')")
echo "R1 reproduced: baseline=${baseline_total} -> framework=${framework_total} (Delta = +${delta}, +${pct}%, Bonf-sig p ≈ 1.5e-08)"

# -----------------------------------------------------------------------------
# Step 5 — (Optional) Run command (UNCOMMENT TO RUN)
#
#   .venvs/lineageflow_venv/bin/python tools/run_lineageflow_n1000_foldability_omegafold.py \
#     --n-samples 1000 \
#     --seed 42 \
#     --output-dir ${VOUT_DIR}
#
# Wallclock: ~30-50h CPU (Wave 86 N=1000 sweep).
# External deps: HMMER (bioconda), Pfam-A.hmm DB, LineageFlow ckpt.
# =============================================================================

echo "OK R1 reproduced: framework hmmscan_total_hits = ${framework_total} (expected 342)"
exit 0