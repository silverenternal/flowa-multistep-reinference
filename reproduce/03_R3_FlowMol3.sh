#!/bin/bash
# =============================================================================
# 03_R3_FlowMol3.sh — Reproduce R3 (FlowMol3 fg_dev, PARTIAL)
#
# Cell:        R3
# Model:       FlowMol3 (ICML 2026 molecular FM)
# Metric:      fg_dev, paired per-record analysis (lower is better)
# Expected:    canonical 3-seed test: mean diff -0.0377, t=-0.695, df=2,
#              p_raw=0.559, d_z=-0.401 -> direction-consistent, NOT significant
#              (PARTIAL per paper-A-final.md §7.2)
#              retired N=200 REOS proxy: d_z=-0.285, p=8.03e-05 (audit-trail
#              check only; the paper reports it as a retired proxy, not a headline)
# Verification: verification_outputs/r3_n1000_3seed_fixed_q4_2026/wave338-p5-r3-n1000-paired.json
#               verification_outputs/wave216-p1-r3-per-record.json
#
# NOTE (2026-10-29): this script used to assert ONLY the N=200 REOS proxy and
# print "Bonf-sig < 1e-4, framework_WINS". The paper retired that proxy at
# Wave 338 and R3 is PARTIAL on the three-seed fg_dev test, so the old check
# green-lit a verdict the manuscript does not claim. Canonical test first now.
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
VOUT_CANON="verification_outputs/r3_n1000_3seed_fixed_q4_2026/wave338-p5-r3-n1000-paired.json"
VOUT_PROXY="verification_outputs/wave216-p1-r3-per-record.json"

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
test -f "${VOUT_CANON}" || { echo "ERROR: missing ${VOUT_CANON}"; exit 1; }
test -f "${VOUT_PROXY}" || { echo "ERROR: missing ${VOUT_PROXY}"; exit 1; }

# -----------------------------------------------------------------------------
# Step 3 — Verify the canonical 3-seed fg_dev test, then the retired proxy
# -----------------------------------------------------------------------------
python3 - "${VOUT_CANON}" "${VOUT_PROXY}" <<'PY'
import json, math, sys

with open(sys.argv[1]) as f:
    canon = json.load(f)
with open(sys.argv[2]) as f:
    proxy = json.load(f)

tol = 1e-3

# --- canonical: three-seed paired fg_dev test (the paper's R3 reading) -------
ps = canon["paired_summary"]
mean_diff = float(ps["mean_diff"])
t_stat    = float(ps["t_statistic"])
p_raw     = float(ps["p_value_raw"])
d_z       = float(ps["cohens_d_z"])
df        = int(ps["df"])
bonf_sig  = bool(ps["bonf_sig"])

for name, got, exp in (("mean_diff", mean_diff, -0.0377),
                       ("t_statistic", t_stat, -0.695),
                       ("cohens_d_z", d_z, -0.4014)):
    if not math.isclose(got, exp, abs_tol=tol):
        print(f"R3 FAIL [{name}]: {got} (expected {exp})")
        sys.exit(1)
if not math.isclose(p_raw, 0.5589, abs_tol=1e-3):
    print(f"R3 FAIL [p_value_raw]: {p_raw} (expected 0.5589)")
    sys.exit(1)
if df != 2 or int(canon["n_seeds_completed"]) != 3:
    print(f"R3 FAIL: expected 3 seeds / df=2, got {canon['n_seeds_completed']} seeds / df={df}")
    sys.exit(1)
if bonf_sig:
    print("R3 FAIL: bonf_sig=True, but the paper reports R3 as PARTIAL / not significant")
    sys.exit(1)

print(f"R3 reproduced [canonical 3-seed fg_dev, PARTIAL]: "
      f"mean_diff={mean_diff:+.4f}, t={t_stat:.3f}, df={df}, "
      f"p_raw={p_raw:.3f}, d_z={d_z:+.4f}, bonf_sig={bonf_sig}")

# --- retired proxy: kept so the audit trail stays byte-checkable -------------
per_record = proxy["per_record_actual"]["tests"]["reos_n_flags"]
p_d_z      = float(per_record["d_z"])
p_p        = float(per_record["p_raw"])
p_n        = int(per_record["n_eff"])

if not math.isclose(p_d_z, -0.285, abs_tol=tol):
    print(f"R3 FAIL [retired proxy d_z]: {p_d_z} (expected -0.285)")
    sys.exit(1)
if not math.isclose(p_p, 8.03e-05, rel_tol=1e-2):
    print(f"R3 FAIL [retired proxy p_raw]: {p_p} (expected 8.03e-05)")
    sys.exit(1)

print(f"R3 audit trail [RETIRED N=200 REOS proxy, NOT a headline]: "
      f"d_z={p_d_z:+.4f}, p={p_p:.2e}, N={p_n}")
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

echo "OK R3 reproduced: canonical 3-seed fg_dev mean_diff=-0.0377, p=0.559, d_z=-0.401 (PARTIAL, not significant)"
exit 0