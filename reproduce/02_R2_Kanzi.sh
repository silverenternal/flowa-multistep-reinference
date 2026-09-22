#!/bin/bash
# =============================================================================
# 02_R2_Kanzi.sh — Reproduce R2 (Kanzi paper-metric framework_wins, N=1000)
#
# Cell:        R2
# Model:       Kanzi (molecular 3D DAE)
# Metric:      RMSD (lower is better) per-record paired-t
# Expected:    d_z = -0.0990  (Bonf-sig p = 0.0018, framework_WINS)
# Verification: verification_outputs/wave218-p3-kanzi-framework-wins.json
#
# Wallclock historical: ~2 h/arm CPU (Wave 214 + Wave 218 N=1000 sweeps).
#
# USAGE:
#   bash reproduce/02_R2_Kanzi.sh
#
# SAFE: This script verifies the headline from the byte-stable
# verification_outputs/ JSON. The "Run command" section is commented out
# by default (each arm takes ~2h CPU; both arms total ~4h).
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

VENV=".venvs/kanzi_venv"
VOUT="verification_outputs/wave218-p3-kanzi-framework-wins.json"

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
# Step 3 — Verify d_z and Bonf-sig flag from byte-stable JSON
# -----------------------------------------------------------------------------
python3 - "${VOUT}" <<'PY'
import json, math, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

expected_d_z     = -0.0990
expected_p_raw   = 0.0018
expected_verdict = "framework_wins"
expected_bonf    = True
tol_d_z          = 1e-3

d_z          = float(d["d_z"])
p_raw        = float(d["p_raw"])
verdict      = str(d["verdict"])
bonf_sig     = bool(d["bonf_sig"])
n_paired     = int(d["paired_n_records"])

if not math.isclose(d_z, expected_d_z, abs_tol=tol_d_z):
    print(f"R2 FAIL: d_z={d_z} (expected {expected_d_z})")
    sys.exit(1)
if not math.isclose(p_raw, expected_p_raw, abs_tol=1e-4):
    print(f"R2 FAIL: p_raw={p_raw} (expected {expected_p_raw})")
    sys.exit(1)
if verdict != expected_verdict:
    print(f"R2 FAIL: verdict={verdict} (expected {expected_verdict})")
    sys.exit(1)
if bonf_sig is not expected_bonf:
    print(f"R2 FAIL: bonf_sig={bonf_sig} (expected {expected_bonf})")
    sys.exit(1)

print(f"R2 reproduced: d_z={d_z:.4f} (Bonf-sig p={p_raw:.4f}, verdict={verdict}, N={n_paired})")
PY

# -----------------------------------------------------------------------------
# Step 4 — (Optional) Run command (UNCOMMENT TO RUN)
#
#   .venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_framework_paper_metrics.py \
#     --output-dir verification_outputs/wave214-p2-kanzi-framework-inv-proj-n1000
#   .venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_paper_metrics.py \
#     --output-dir verification_outputs/wave218-p3-kanzi-baseline-n1000
#   python3 scripts/wave218_p3_paired_ttest.py
#
# Wallclock: ~4h CPU total (~2h per arm).
# External deps: Kanzi ckpt (vendored at data/kanzi_upstream/).
# =============================================================================

echo "OK R2 reproduced: framework d_z = -0.0990 (Bonf-sig p=0.0018, framework_WINS)"
exit 0