#!/bin/bash
# =============================================================================
# 07_R6_MNIST_TierAware.sh — Reproduce R6 (LineageFlow k6 foldability, live tier-aware)
#
# Cell:        R6
# Model:       LineageFlow k6 (protein foldability), NOT MNIST — R5c is MNIST
# Metric:      scPerplexity (lower better) + pLDDT (higher better)
# Expected:    live headline (2026-10-27 refresh, paper-A-final.md §7.2 R6):
#                scPerplexity pooled d_z = -0.8393 (n=3000)
#                pooled pLDDT d_z        = +0.1466 (n=3000, below the +0.2235 bar)
#                hard-tier pLDDT d_z     = +1.1211 (n=990)
#              design-validation counterfactual (not the headline):
#                d_z +0.2235 (Wave 233 P3) -> best grid cell +0.6467 (Wave 235 P3)
# Verification: verification_outputs/gap31-r6-live-uplift/gap31_summary.json
#               verification_outputs/gap30-r6-fresh-tier/as-designed/sweep_summary.json
#               verification_outputs/wave235-p3-r6-uplift.json
#
# NOTE (2026-10-29): this script used to assert ONLY the counterfactual grid cell
# and print it as "the headline", under a wrong "MNIST FM" model label. The
# 2026-10-27 refresh replaced the R6 headline with the live tier-aware run, so
# the live numbers are now checked first and the counterfactual is labelled as
# the design validation it is. No number changed.
#
# Wallclock historical: ~5 min/arm CPU (counterfactual from frozen k6 sweep).
#
# USAGE:
#   bash reproduce/07_R6_MNIST_TierAware.sh
#
# SAFE: This script verifies the headline from the byte-stable
# verification_outputs/ JSON. The "Run command" section is commented out
# by default (counterfactual grid search; runs in <1 min).
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

VENV=".venvs/flowmol3_venv"
VOUT_LIVE="verification_outputs/gap31-r6-live-uplift/gap31_summary.json"
VOUT_TIER="verification_outputs/gap30-r6-fresh-tier/as-designed/sweep_summary.json"
VOUT_CF="verification_outputs/wave235-p3-r6-uplift.json"

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
for f in "${VOUT_LIVE}" "${VOUT_TIER}" "${VOUT_CF}"; do
  test -f "${f}" || { echo "ERROR: missing ${f}"; exit 1; }
done

# -----------------------------------------------------------------------------
# Step 3a — Verify the live headline (scPerplexity + pLDDT)
# -----------------------------------------------------------------------------
python3 - "${VOUT_LIVE}" "${VOUT_TIER}" <<'PY'
import json, math, sys

with open(sys.argv[1]) as f:
    live = json.load(f)
with open(sys.argv[2]) as f:
    tier = json.load(f)

tol = 1e-3

sc = live["scperplexity_live"]["pooled"]
sc_n, sc_dz, sc_diff = int(sc["n"]), float(sc["cohens_d_z"]), float(sc["mean_diff"])
if sc_n != 3000:
    print(f"R6 FAIL [scPerplexity pooled]: n={sc_n} (expected 3000)")
    sys.exit(1)
if not math.isclose(sc_dz, -0.8393, abs_tol=tol):
    print(f"R6 FAIL [scPerplexity pooled d_z]: {sc_dz} (expected -0.8393)")
    sys.exit(1)
if not math.isclose(sc_diff, -3.6823, abs_tol=tol):
    print(f"R6 FAIL [scPerplexity pooled mean_diff]: {sc_diff} (expected -3.6823)")
    sys.exit(1)
if sc_dz >= 0:
    print("R6 FAIL [scPerplexity pooled]: sign must be negative (lower scPerplexity is better)")
    sys.exit(1)

uni = live["plddt_live_uniform_to_as_designed"]["pooled"]["uniform_vs_baseline"]
uni_n, uni_dz = int(uni["n"]), float(uni["cohens_d_z"])
if uni_n != 3000 or not math.isclose(uni_dz, 0.1466, abs_tol=tol):
    print(f"R6 FAIL [pooled pLDDT]: n={uni_n}, d_z={uni_dz} (expected n=3000, +0.1466)")
    sys.exit(1)
if uni_dz >= 0.2235:
    print(f"R6 FAIL [pooled pLDDT]: {uni_dz} reaches the +0.2235 bar; the paper says it does not")
    sys.exit(1)

hard = tier["pooled_per_tier"]["fresh"]["hard"]
h_n, h_dz, h_diff = int(hard["n"]), float(hard["cohens_d_z"]), float(hard["mean_diff"])
if h_n != 990:
    print(f"R6 FAIL [hard-tier pLDDT]: n={h_n} (expected 990)")
    sys.exit(1)
if not math.isclose(h_dz, 1.1211, abs_tol=tol):
    print(f"R6 FAIL [hard-tier pLDDT d_z]: {h_dz} (expected +1.1211)")
    sys.exit(1)
if not math.isclose(h_diff, 15.0065, abs_tol=tol):
    print(f"R6 FAIL [hard-tier pLDDT mean_diff]: {h_diff} (expected +15.0065)")
    sys.exit(1)

print(f"R6 reproduced [LIVE, the headline]: scPerplexity d_z={sc_dz:+.4f} "
      f"(diff {sc_diff:+.4f}, n={sc_n}); pooled pLDDT d_z={uni_dz:+.4f} (n={uni_n}); "
      f"hard-tier pLDDT d_z={h_dz:+.4f} (diff {h_diff:+.4f}, n={h_n})")
PY

# -----------------------------------------------------------------------------
# Step 3b — Verify the design-validation counterfactual (not the headline)
# -----------------------------------------------------------------------------
python3 - "${VOUT_CF}" <<'PY'
import json, math, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

grid = d["grid_results"]
best  = max(grid, key=lambda c: c["d_z"])

expected_d_z_best    = 0.647
expected_d_z_wave233 = float(d["wave233_p3_baseline_d_z"])
tol_d_z              = 1e-3

d_z_best      = float(best["d_z"])
p_value_best  = float(best["p_value"])
bonf_sig_best = bool(best["bonf_sig"])
easy_reg_elim = bool(best["easy_regression_eliminated"])

if not math.isclose(d_z_best, expected_d_z_best, abs_tol=tol_d_z):
    print(f"R6 FAIL: best grid cell d_z={d_z_best} (expected {expected_d_z_best})")
    sys.exit(1)
if not bonf_sig_best:
    print(f"R6 FAIL: best grid cell bonf_sig={bonf_sig_best} (expected True)")
    sys.exit(1)
if not easy_reg_elim:
    print(f"R6 FAIL: easy_regression_eliminated={easy_reg_elim} (expected True)")
    sys.exit(1)

uplift_pct = (d_z_best - expected_d_z_wave233) / expected_d_z_wave233 * 100
if not math.isclose(uplift_pct, 189.0, abs_tol=20.0):
    print(f"R6 WARN: uplift_pct={uplift_pct:.1f}% (headline reads +189%, tolerance +-20pp)")
    # Not a hard fail -- the README rounds to "+189%"
    # but counterfactual grid best is what it is.

print(f"R6 reproduced [design validation, NOT the headline]: pLDDT d_z "
      f"{expected_d_z_wave233:.4f} -> {d_z_best:.4f} "
      f"(uplift {uplift_pct:+.1f}%, Bonf-sig p={p_value_best:.2e}, easy_regression_eliminated={easy_reg_elim})")
PY

# -----------------------------------------------------------------------------
# Step 4 — (Optional) Run command (UNCOMMENT TO RUN)
#
#   .venvs/flowmol3_venv/bin/python scripts/wave235_p3_r6_uplift.py
#
# Wallclock: <1 min CPU (counterfactual grid search over frozen k6 foldability sweep).
# External deps: k6 foldability N=1000 sweep at
#   verification_outputs/k6_foldability_n1000_w161_q3_2026/{baseline,framework}/foldability/.
# =============================================================================

echo "OK R6 reproduced: live scPerplexity d_z=-0.8393 (n=3000), hard-tier pLDDT d_z=+1.1211 (n=990); counterfactual +0.6467 retained as design validation"
exit 0