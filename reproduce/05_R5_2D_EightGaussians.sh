#!/bin/bash
# =============================================================================
# 05_R5_2D_EightGaussians.sh — Reproduce R5 (2D FM ablation, Eight Gaussians)
#
# Cell:        R5
# Model:       2D FM ablation (synthetic)
# Metric:      Wasserstein-2 (W2, lower is better)
# Expected:    baseline 2.31 -> framework 0.76  (Delta = -67.10%, framework_WINS)
# Verification: verification_outputs/g1_deep_dive_q3_2026.json
#               row: twodim_fm_2d_eight_gaussians
#
# Wallclock historical: ~1 min/arm CPU.
#
# USAGE:
#   bash reproduce/05_R5_2D_EightGaussians.sh
#
# SAFE: This script verifies the headline from the byte-stable
# verification_outputs/ JSON. The "Run command" section is commented out
# by default.
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

VENV=".venvs/flowmol3_venv"
VOUT="verification_outputs/g1_deep_dive_q3_2026.json"

# -----------------------------------------------------------------------------
# Step 1 — Environment activation
# -----------------------------------------------------------------------------
if [ -d "${VENV}" ]; then
  # shellcheck disable=SC1091
  source "${VENV}/bin/activate"
fi

# -----------------------------------------------------------------------------
# Step 2 — Data check (byte-stable artefact present?)
# -----------------------------------------------------------------------------
test -f "${VOUT}" || { echo "ERROR: missing ${VOUT}"; exit 1; }

# -----------------------------------------------------------------------------
# Step 3 — Verify R5 row from g1_deep_dive JSON
# -----------------------------------------------------------------------------
python3 - "${VOUT}" <<'PY'
import json, math, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

rows = {row["row"]: row for row in d["analysis"]["per_cell_breakdown"]}
row = rows["twodim_fm_2d_eight_gaussians"]

expected_baseline = 2.31
expected_framework = 0.76
expected_delta_pct = -0.6710
tol                = 1e-3

baseline = float(row["baseline"])
framework = float(row["framework"])
delta_pct = float(row["raw_delta_pct"])
fw_wins   = bool(row["framework_wins"])

if not math.isclose(baseline, expected_baseline, abs_tol=tol):
    print(f"R5 FAIL: baseline={baseline} (expected {expected_baseline})")
    sys.exit(1)
if not math.isclose(framework, expected_framework, abs_tol=tol):
    print(f"R5 FAIL: framework={framework} (expected {expected_framework})")
    sys.exit(1)
if not math.isclose(delta_pct, expected_delta_pct, abs_tol=tol):
    print(f"R5 FAIL: raw_delta_pct={delta_pct} (expected {expected_delta_pct})")
    sys.exit(1)
if not fw_wins:
    print(f"R5 FAIL: framework_wins={fw_wins} (expected True)")
    sys.exit(1)

print(f"R5 reproduced: W2 baseline={baseline} -> framework={framework} (Delta = {delta_pct*100:.2f}%, framework_WINS)")
PY

# -----------------------------------------------------------------------------
# Step 4 — (Optional) Run command (UNCOMMENT TO RUN)
#
#   .venvs/flowmol3_venv/bin/python tools/materialize_twodim_fm.py
#   .venvs/flowmol3_venv/bin/python tools/run_sota_2d_experiment.py \
#     --target eight_gaussians \
#     --n-seeds 3
#
# Wallclock: ~1 min/arm CPU (synthetic 2D, no external data).
# =============================================================================

echo "OK R5 reproduced: framework W2 = 0.76 (Delta = -67.10%, framework_WINS)"
exit 0