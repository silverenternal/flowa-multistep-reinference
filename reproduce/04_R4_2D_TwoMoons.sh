#!/bin/bash
# =============================================================================
# 04_R4_2D_TwoMoons.sh — Reproduce R4 (2D FM ablation, Two Moons)
#
# Cell:        R4 (Wave-135 numbering; canonical Wave-310 cell = R5a)
# Model:       2D rectified flow (Liu 2022) + 2D FM ablation (synthetic)
# Metric:      Wasserstein-2 (W2, lower is better)
# Expected:    RF SOTA   baseline 0.5029 -> framework 0.4663 (Delta = -7.28%)
#              2D ablate  baseline 2.85   -> framework 0.62   (Delta = -78.25%)
# Verification: verification_outputs/g1_deep_dive_q3_2026.json
#               rows: rectified_flow_2d_sota_two_moons + twodim_fm_2d_ablation
#
# NOTE (2026-10-29): this script used to assert ONLY the ablation row
# (2.85 -> 0.62). That is the separate experiment paper-A-final.md §7.2 R5a
# calls out, not the CLM-039 headline, so the canonical -7.28% went unverified.
# Both rows are now asserted; neither number changed.
#
# Wallclock historical: ~1 min/arm CPU.
#
# USAGE:
#   bash reproduce/04_R4_2D_TwoMoons.sh
#
# SAFE: This script verifies the headline from the byte-stable
# verification_outputs/ JSON. The "Run command" section is commented out
# by default (~1 min/arm CPU is fast, but the script is in print-plan mode).
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
# Step 3 — Verify R4 row from g1_deep_dive JSON
# -----------------------------------------------------------------------------
python3 - "${VOUT}" <<'PY'
import json, math, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

rows = {row["row"]: row for row in d["analysis"]["per_cell_breakdown"]}
tol  = 1e-3

# Two distinct two_moons experiments live in this JSON and the paper cites both:
#   * the load-bearing CLM-039 headline (Liu 2022 RF SOTA, EvidenceDrivenScheduler)
#     -> -7.28%, and
#   * the 2D FM ablation that paper-A-final.md §7.2 R5a calls out explicitly as a
#     SEPARATE experiment (-78.25%).
# Checking only the ablation, as this script used to, leaves the canonical
# -7.28% unverified; checking only the SOTA row would drop the ablation. Both.
checks = [
    ("rectified_flow_2d_sota_two_moons", "RF SOTA (CLM-039 canonical)",
     0.5029, 0.4663, -0.0728),
    ("twodim_fm_2d_ablation", "2D FM ablation (separate experiment)",
     2.85, 0.62, -0.7825),
]

for key, label, exp_b, exp_f, exp_d in checks:
    if key not in rows:
        print(f"R4 FAIL: row {key!r} missing from {sys.argv[1]}")
        sys.exit(1)
    row = rows[key]
    baseline  = float(row["baseline"])
    framework = float(row["framework"])
    delta_pct = float(row["raw_delta_pct"])
    fw_wins   = bool(row["framework_wins"])

    if not math.isclose(baseline, exp_b, abs_tol=tol):
        print(f"R4 FAIL [{label}]: baseline={baseline} (expected {exp_b})")
        sys.exit(1)
    if not math.isclose(framework, exp_f, abs_tol=tol):
        print(f"R4 FAIL [{label}]: framework={framework} (expected {exp_f})")
        sys.exit(1)
    if not math.isclose(delta_pct, exp_d, abs_tol=tol):
        print(f"R4 FAIL [{label}]: raw_delta_pct={delta_pct} (expected {exp_d})")
        sys.exit(1)
    if not fw_wins:
        print(f"R4 FAIL [{label}]: framework_wins={fw_wins} (expected True)")
        sys.exit(1)

    print(f"R4 reproduced [{label}]: W2 {baseline} -> {framework} "
          f"(Delta = {delta_pct*100:.2f}%, framework_WINS)")
PY

# -----------------------------------------------------------------------------
# Step 4 — (Optional) Run command (UNCOMMENT TO RUN)
#
#   .venvs/flowmol3_venv/bin/python tools/materialize_twodim_fm.py
#   .venvs/flowmol3_venv/bin/python tools/run_sota_2d_experiment.py \
#     --target two_moons \
#     --n-seeds 3
#
# Wallclock: ~1 min/arm CPU (synthetic 2D, no external data).
# =============================================================================

echo "OK R4 reproduced: RF SOTA W2 0.5029 -> 0.4663 (-7.28%) and ablation 2.85 -> 0.62 (-78.25%)"
exit 0