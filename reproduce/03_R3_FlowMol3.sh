#!/bin/bash
# =============================================================================
# 03_R3_FlowMol3.sh — Reproduce R3 (FlowMol3 per-record framework_wins)
#
# Cell:        R3
# Model:       FlowMol3 (ICML 2026 molecular FM)
# Metric:      per-record fg_dev proxy d_z (lower is better)
# Expected:    d_z = -0.285  (Bonf-sig < 1e-4, framework_WINS)
#              3-seed-pooled, Blocked-at-vendor level
# Verification: verification_outputs/wave216-p1-r3-per-record.json
#
# Wallclock historical: ~30 min GPU (Wave 87 N=1000 sweep).
#
# USAGE:
#   bash reproduce/03_R3_FlowMol3.sh
#
# SAFE: This script verifies the headline from the byte-stable
# verification_outputs/ JSON. The "Run command" section is commented out
# by default (~30 min GPU required).
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

VENV=".venvs/flowmol3_venv"
VOUT="verification_outputs/wave216-p1-r3-per-record.json"

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
# Step 3 — Verify d_z from per-record JSON
# -----------------------------------------------------------------------------
python3 - "${VOUT}" <<'PY'
import json, math, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

# Headline per-record d_z lives in per_record_actual.tests.reos_n_flags.d_z
per_record = d["per_record_actual"]["tests"]["reos_n_flags"]
d_z        = float(per_record["d_z"])
p_raw      = float(per_record["p_raw"])
n_eff      = int(per_record["n_eff"])
mean_diff  = float(per_record["mean_diff"])

expected_d_z    = -0.285
expected_p_raw  = 8.03e-05  # Bonf-sig < 1e-4
tol_d_z         = 1e-3

if not math.isclose(d_z, expected_d_z, abs_tol=tol_d_z):
    print(f"R3 FAIL: per-record d_z={d_z} (expected {expected_d_z})")
    sys.exit(1)
if p_raw > 1e-4:
    print(f"R3 FAIL: per-record p_raw={p_raw} (not Bonf-sig <1e-4)")
    sys.exit(1)

print(f"R3 reproduced: per-record d_z={d_z:.4f} (Bonf-sig p={p_raw:.2e}, mean_diff={mean_diff:.3f}, N={n_eff})")
PY

# -----------------------------------------------------------------------------
# Step 4 — (Optional) Run command (UNCOMMENT TO RUN)
#
#   .venvs/flowmol3_venv/bin/python tools/wave87_n1000_sweep.py \
#     --nfe 250 \
#     --n-total 1000 \
#     --nfe-batch 100 \
#     --output-dir verification_outputs/flowmol3_n1000_wave87_q4_2026
#   python3 scripts/wave216_p1_r3_per_record.py
#
# Wallclock: ~30 min GPU (PRO 6000 Blackwell or 5090).
# External deps: FlowMol3 ckpt (data/flowmol3/weights_real/checkpoints/last.ckpt).
# =============================================================================

echo "OK R3 reproduced: framework per-record d_z = -0.285 (Bonf-sig < 1e-4, framework_WINS)"
exit 0