#!/bin/bash
# =============================================================================
# 06_R5b_CIFAR_n_rounds1.sh — Reproduce R5b (CIFAR-10 RF n_rounds=1, 4 schedulers)
#
# Cell:        R5b
# Model:       CIFAR-10 Rectified Flow (n_rounds=1)
# Metric:      FID (lower is better)
# Expected:    framework_WINS on all 4 schedulers at n_rounds=1
#                cosineanneal     Delta FID = -1.60%, d_z = +4.37
#                codimensionsheet Delta FID = -2.53%, d_z = +4.73
#                evidencedriven   Delta FID = -0.12%, d_z = +4.63
#                freetraj         Delta FID = -0.66%, d_z = +4.51
#              headline Delta FID range: -2.53% to -0.12%
#              AND the reversal at n_rounds>=2 that makes the cell CONDITIONAL:
#                n_rounds=10 cosineanneal Delta FID = +30.19% (framework WORSE)
# Verification: verification_outputs/wave235-p1-r5b-fix.json
#               keys: rounds1 (the win) + no_final_restart_n10 (the reversal)
#
# Wallclock historical: ~30 min GPU (3 seeds x 4 schedulers).
#
# USAGE:
#   bash reproduce/06_R5b_CIFAR_n_rounds1.sh
#
# SAFE: This script verifies the headline from the byte-stable
# verification_outputs/ JSON. The "Run command" section is commented out
# by default.
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

VENV=".venvs/flowmol3_venv"
VOUT="verification_outputs/wave235-p1-r5b-fix.json"

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
# Step 3 — Verify all 4 schedulers under n_rounds=1
# -----------------------------------------------------------------------------
python3 - "${VOUT}" <<'PY'
import json, math, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

cell = d["rounds1"]
n_rounds = int(cell["n_rounds"])
if n_rounds != 1:
    print(f"R5b FAIL: n_rounds={n_rounds} (expected 1)")
    sys.exit(1)

# Per-scheduler expected (delta_pct, d_z) from README headline table
EXPECTED = {
    "cosineanneal":      (-1.60, 4.37),
    "codimensionsheet":  (-2.53, 4.73),
    "evidencedriven":    (-0.12, 4.63),
    "freetraj":          (-0.66, 4.51),
}

tol_pct = 0.05   # percentage points
tol_dz  = 0.05   # d_z units

results = cell["results"]
delta_pcts = []
dz_list   = []
for sched, (exp_pct, exp_dz) in EXPECTED.items():
    if sched not in results:
        print(f"R5b FAIL: missing scheduler '{sched}' in JSON results")
        sys.exit(1)
    delta_pct = float(results[sched]["delta_pct"])
    d_z       = float(results[sched]["d_z"])
    if not math.isclose(delta_pct, exp_pct, abs_tol=tol_pct):
        print(f"R5b FAIL: {sched} delta_pct={delta_pct} (expected {exp_pct})")
        sys.exit(1)
    if not math.isclose(d_z, exp_dz, abs_tol=tol_dz):
        print(f"R5b FAIL: {sched} d_z={d_z} (expected {exp_dz})")
        sys.exit(1)
    delta_pcts.append(delta_pct)
    dz_list.append(d_z)

# Verify "framework_WINS on all 4 schedulers" -- all delta_pct should be < 0
if not all(p < 0 for p in delta_pcts):
    print(f"R5b FAIL: not all schedulers framework_WINS: delta_pcts={delta_pcts}")
    sys.exit(1)

pct_min, pct_max = min(delta_pcts), max(delta_pcts)
dz_min, dz_max   = min(dz_list), max(dz_list)
print(f"R5b reproduced: n_rounds=1 framework_WINS on 4/4 schedulers "
      f"(Delta FID range {pct_min:.2f}% to {pct_max:.2f}%; d_z range {dz_min:.2f} to {dz_max:.2f})")

# --- the reversal that makes R5b CONDITIONAL, not STRONG ---------------------
# paper-A-final.md §7.2: the strong reading holds only at n_rounds=1 and
# reverses for n_rounds>=2. That reversal is what the label rests on, so it is
# asserted here rather than left to prose.
rev = d["no_final_restart_n10"]
rev_pct = float(rev["results"]["cosineanneal"]["delta_pct"])
rev_rounds = int(rev["n_rounds"])
if rev_rounds < 2:
    print(f"R5b FAIL: reversal arm has n_rounds={rev_rounds} (expected >=2)")
    sys.exit(1)
if rev_pct <= 0:
    print(f"R5b FAIL: reversal arm delta_pct={rev_pct} is not a regression; "
          f"R5b would not be CONDITIONAL")
    sys.exit(1)
if not math.isclose(rev_pct, 30.19, abs_tol=0.05):
    print(f"R5b FAIL: reversal arm delta_pct={rev_pct} (expected +30.19)")
    sys.exit(1)
print(f"R5b reproduced [CONDITIONAL basis]: n_rounds={rev_rounds} cosineanneal "
      f"reverses to {rev_pct:+.2f}% (framework WORSE), so the n_rounds=1 win "
      f"is protocol-conditional")
PY

# -----------------------------------------------------------------------------
# Step 4 — (Optional) Run command (UNCOMMENT TO RUN)
#
# ``run_sota_cifar_experiment.py`` threads the seed through the ``WAVE247_SEED``
# environment variable (it has no ``--n-seeds`` flag: one process is one seed),
# so the 3-seed sweep is a shell loop.
#
#   for s in 42 43 44; do
#     WAVE247_SEED="${s}" .venvs/flowmol3_venv/bin/python \
#       tools/run_sota_cifar_experiment.py \
#       --n-rounds 1 \
#       --output-dir verification_outputs/r5b_cifar_nrounds1_seed${s}
#   done
#
# The reversal arm is the same call with ``--n-rounds 10 --no-final-restart``.
# Wallclock: ~30 min GPU (3 seeds x 4 schedulers x n_rounds=1).
# External deps: CIFAR-10 reference features (data/rf_reference_features/).
# =============================================================================

echo "OK R5b reproduced: n_rounds=1 framework_WINS on 4/4 schedulers (Delta FID -2.53% to -0.12%); n_rounds=10 reverses to +30.19% (CONDITIONAL)"
exit 0