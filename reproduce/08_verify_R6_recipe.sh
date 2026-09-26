#!/bin/bash
# =============================================================================
# 08_verify_R6_recipe.sh — Verify the R6 LineageFlow k6 foldability recipe
#
# Cell:        R6 (LineageFlow k6 foldability)
# Source doc:  paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md
# Audit doc:   docs/audit/wave362-p1-r6-recipe.md
#
# Verifies (in order):
#   1. SHA-256 of Wave 161 frozen substrate (baseline + framework foldability.jsonl)
#   2. SHA-256 of Wave 233 P3 tier-aware counterfactual JSON
#   3. SHA-256 of Wave 235 P3 grid-search uplift JSON
#   4. Python snippet reproduces Wave 233 P3 d_z = +0.2235 (to +/-1e-4)
#   5. Wave 235 P3 best cell matches (cell_idx=3, easy_factor=0.0, hard_intensity=3.0,
#      d_z=0.6467, bonf_sig=true, easy_regression_eliminated=true)
#
# USAGE:
#   bash reproduce/08_verify_R6_recipe.sh
#
# EXPECTED OUTPUT (last line):
#   "OK: R6 recipe verified — SHA-256 chain + Wave 233 P3 d_z + Wave 235 P3 best cell"
#
# SAFE: This script verifies byte-stable JSONL/JSON artefacts only.
# No GPU required. No destructive edits. Counterfactual methodology preserved.
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

VOUT_W161="verification_outputs/k6_foldability_n1000_w161_q3_2026"
VOUT_W233="verification_outputs/wave233-p3-tier-aware-r6.json"
VOUT_W235="verification_outputs/wave235-p3-r6-uplift.json"

# -----------------------------------------------------------------------------
# Step 1 — Wave 161 frozen substrate SHA-256 (per-record foldability.jsonl)
# -----------------------------------------------------------------------------
echo "Step 1: verify Wave 161 frozen substrate SHA-256..."
test -f "${VOUT_W161}/baseline/foldability/foldability.jsonl" \
  || { echo "ERROR: missing ${VOUT_W161}/baseline/foldability/foldability.jsonl"; exit 1; }
test -f "${VOUT_W161}/framework/foldability/foldability.jsonl" \
  || { echo "ERROR: missing ${VOUT_W161}/framework/foldability/foldability.jsonl"; exit 1; }

EXPECTED_BASELINE_SHA="164825057a413af6f4d27a53b3ca519484f5c36019dafaa6c14e33dc823e4261"
EXPECTED_FRAMEWORK_SHA="b608edfb0f13a39bde5a06c3d16ccc94aa98f90db5434411cefe2f647574fc85"

ACTUAL_BASELINE_SHA="$(sha256sum < "${VOUT_W161}/baseline/foldability/foldability.jsonl" | awk '{print $1}')"
ACTUAL_FRAMEWORK_SHA="$(sha256sum < "${VOUT_W161}/framework/foldability/foldability.jsonl" | awk '{print $1}')"

if [ "${ACTUAL_BASELINE_SHA}" != "${EXPECTED_BASELINE_SHA}" ]; then
  echo "R6 FAIL: baseline foldability.jsonl SHA mismatch"
  echo "  expected: ${EXPECTED_BASELINE_SHA}"
  echo "  actual:   ${ACTUAL_BASELINE_SHA}"
  exit 1
fi
if [ "${ACTUAL_FRAMEWORK_SHA}" != "${EXPECTED_FRAMEWORK_SHA}" ]; then
  echo "R6 FAIL: framework foldability.jsonl SHA mismatch"
  echo "  expected: ${EXPECTED_FRAMEWORK_SHA}"
  echo "  actual:   ${ACTUAL_FRAMEWORK_SHA}"
  exit 1
fi
echo "  OK: baseline + framework foldability.jsonl SHA-256 verified"

# -----------------------------------------------------------------------------
# Step 2 — Wave 233 P3 tier-aware counterfactual JSON SHA-256
# -----------------------------------------------------------------------------
echo "Step 2: verify Wave 233 P3 tier-aware counterfactual SHA-256..."
test -f "${VOUT_W233}" || { echo "ERROR: missing ${VOUT_W233}"; exit 1; }
EXPECTED_W233_SHA="9a0c3eacc847c29a2844fb2ce4dc36f94def244ecbd4b4978fc0c1deeaf15851"
ACTUAL_W233_SHA="$(sha256sum < "${VOUT_W233}" | awk '{print $1}')"
if [ "${ACTUAL_W233_SHA}" != "${EXPECTED_W233_SHA}" ]; then
  echo "R6 FAIL: wave233-p3-tier-aware-r6.json SHA mismatch"
  echo "  expected: ${EXPECTED_W233_SHA}"
  echo "  actual:   ${ACTUAL_W233_SHA}"
  exit 1
fi
echo "  OK: wave233-p3-tier-aware-r6.json SHA-256 verified"

# -----------------------------------------------------------------------------
# Step 3 — Wave 235 P3 grid-search uplift JSON SHA-256
# -----------------------------------------------------------------------------
echo "Step 3: verify Wave 235 P3 grid-search uplift SHA-256..."
test -f "${VOUT_W235}" || { echo "ERROR: missing ${VOUT_W235}"; exit 1; }
EXPECTED_W235_SHA="9a9dff1867efa54c8f542c86dfdb7f12fb18dd2998827b82fbd52769c3cc4030"
ACTUAL_W235_SHA="$(sha256sum < "${VOUT_W235}" | awk '{print $1}')"
if [ "${ACTUAL_W235_SHA}" != "${EXPECTED_W235_SHA}" ]; then
  echo "R6 FAIL: wave235-p3-r6-uplift.json SHA mismatch"
  echo "  expected: ${EXPECTED_W235_SHA}"
  echo "  actual:   ${ACTUAL_W235_SHA}"
  exit 1
fi
echo "  OK: wave235-p3-r6-uplift.json SHA-256 verified"

# -----------------------------------------------------------------------------
# Step 4 — Python snippet: reproduce Wave 233 P3 d_z = +0.2235
# -----------------------------------------------------------------------------
echo "Step 4: reproduce Wave 233 P3 tier-aware d_z = +0.2235..."
python3 - "${VOUT_W161}" <<'PY'
import json, math, sys

SUBSTRATE = sys.argv[1]
REDUCED_INTENSITY_FACTOR = 0.5  # Wave 209 P1 A3 / Wave 225 P4 canonical
TIER_LOW, TIER_HIGH = 34.560125471956226, 46.129279241102346  # Wave 198 P3

def load(path):
    out = {}
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            out[r["qid"]] = r["plddt_mean"]
    return out

baseline = load(f"{SUBSTRATE}/baseline/foldability/foldability.jsonl")
framework = load(f"{SUBSTRATE}/framework/foldability/foldability.jsonl")
qids = sorted(baseline.keys())
diffs = [framework[q] - baseline[q] for q in qids]
baselines = [baseline[q] for q in qids]

def tier_of(b):
    return "hard" if b < TIER_LOW else ("medium" if b < TIER_HIGH else "easy")
tiers = [tier_of(b) for b in baselines]

# Apply REDUCED_INTENSITY_FACTOR counterfactual on easy tier (Wave 225 P4)
# Per Wave 209 P1 A3 / Wave 225 P4: add a CONSTANT offset to each easy-tier diff,
# shifting the easy-tier mean toward zero by REDUCED_INTENSITY_FACTOR * |uniform_mean|.
# This preserves per-record variance (constant shift does not change sd).
easy_idx = [i for i, t in enumerate(tiers) if t == "easy"]
uniform_easy_mean = sum(diffs[i] for i in easy_idx) / len(easy_idx)
offset = -REDUCED_INTENSITY_FACTOR * uniform_easy_mean  # negative-uniform_easy_mean is +|mean|
adj = list(diffs)
for i in easy_idx:
    adj[i] = diffs[i] + offset

n = len(diffs)
mean_d = sum(adj) / n
sd_d = math.sqrt(sum((d - mean_d) ** 2 for d in adj) / (n - 1))
d_z = mean_d / sd_d
expected = 0.22346278288686192
print(f"  reproduced d_z = {d_z:.6f}  (expected +0.223463)")
if not math.isclose(d_z, expected, abs_tol=1e-4):
    print(f"R6 FAIL: Wave 233 P3 d_z mismatch (got {d_z:.6f}, expected {expected:.6f})")
    sys.exit(1)
print("  OK: Wave 233 P3 tier-aware d_z reproduced (+/-1e-4)")
PY

# -----------------------------------------------------------------------------
# Step 5 — Wave 235 P3 best cell matches (cell_idx=3, easy_factor=0.0,
#          hard_intensity=3.0, d_z=0.6467, bonf_sig=true, easy_regression_eliminated=true)
# -----------------------------------------------------------------------------
echo "Step 5: verify Wave 235 P3 best grid cell..."
python3 - "${VOUT_W235}" <<'PY'
import json, math, sys

with open(sys.argv[1]) as f:
    d = json.load(f)

best = d["best_overall_no_constraint"]
expected = {
    "cell_idx": 3,
    "easy_factor": 0.0,
    "hard_intensity": 3.0,
    "d_z": 0.6467183780093474,
    "bonf_sig": True,
    "easy_regression_eliminated": True,
}

for k, v in expected.items():
    actual = best[k]
    if isinstance(v, float):
        ok = math.isclose(actual, v, abs_tol=1e-4)
    else:
        ok = (actual == v)
    if not ok:
        print(f"R6 FAIL: Wave 235 P3 best cell field {k!r} mismatch (got {actual}, expected {v})")
        sys.exit(1)
print(f"  OK: Wave 235 P3 best cell verified (cell_idx=3, easy_factor=0.0, hard_intensity=3.0, d_z={best['d_z']:.6f})")
PY

echo ""
echo "OK: R6 recipe verified — SHA-256 chain + Wave 233 P3 d_z + Wave 235 P3 best cell"
exit 0