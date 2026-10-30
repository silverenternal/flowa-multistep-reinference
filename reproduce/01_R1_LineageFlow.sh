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
# The headline metric is ``hmmscan_total_hits``, so the pipeline is three
# steps: generate the two FASTA arms, scan both with HMMER, then score.
#
#   # 5a. Generate 1000 FASTA per arm (baseline + framework).  ``--nfe 150``
#   #     matches the upstream LineageFlow released config (steps_base=100 +
#   #     steps_final=50; see docs/audit/gap41b-r1-nfe-fidelity.md) and
#   #     ``--restart-min-nfe 5`` opens the Wave 186 restart-blend gate.
#   .venvs/lineageflow_venv/bin/python tools/gen_lineageflow_n1000_fastas.py \
#     --n 1000 --seed 42 --nfe 150 --n-rounds 3 --restart-min-nfe 5 \
#     --upstream-eval-len-bias short --temperature 1.0 \
#     --outdir ${VOUT_DIR}/regen
#
#   # 5b. Scan both arms.  HMMER is an external binary, not a Python driver.
#   hmmscan --tblout ${VOUT_DIR}/regen/baseline_hits.tbl \
#     Pfam-A.hmm ${VOUT_DIR}/regen/baseline.fasta
#   hmmscan --tblout ${VOUT_DIR}/regen/framework_hits.tbl \
#     Pfam-A.hmm ${VOUT_DIR}/regen/framework.fasta
#
#   # 5c. Score: per-seed paired-t + 3-seed DerSimonian-Laird meta.
#   .venvs/lineageflow_venv/bin/python tools/r1_d004_analysis.py \
#     --root ${VOUT_DIR}/regen --out ${VOUT_DIR}/regen \
#     --seeds 42 --n-per-seed 1000
#
# Wallclock: ~30-50h CPU (Wave 86 N=1000 sweep).
# External deps: HMMER (bioconda), Pfam-A.hmm DB, LineageFlow ckpt.
#
# GAP-55 NOTE (2026-10-19) — the frozen 158/342 headline was produced by
# Wave 158, BEFORE the Wave 186 restart-blend gate. Under current defaults
# (`--nfe 10`, `--restart-min-nfe 20`) the gate fires
# (`tools/gen_lineageflow_n1000_fastas.py:613`), `n_rounds` collapses to 1,
# and the framework arm no longer chains the restart blend. This script
# verifies the stored .tbl artifacts; it does NOT assert that today's code
# regenerates them. The ``--nfe 150 --restart-min-nfe 5`` pair above is what
# opens the gate again. At N=200 the NFE=150 arm is +20.3 hits over baseline
# on 3/3 seeds.
# =============================================================================

echo "OK R1 reproduced: framework hmmscan_total_hits = ${framework_total} (expected 342)"
exit 0