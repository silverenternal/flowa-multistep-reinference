#!/usr/bin/env bash
# Wave 108.C — LineageFlow N=1000 GPU framework-vs-baseline sweep wrapper
# REUSE-2: chains 3 existing scripts into a single entry point.
# Pattern: docs/audit/wave69-phase5-lineageflow-sweep.md §3 (3-shell-call template).
# Underlying wrappers: tools.upstream_eval.run_lineageflow_upstream_eval (Wave 81),
# tools.run_real_ckpt_eval.py (Wave 47 composite), tools._gpu_watchdog (auto-wired).
# Inputs: data/lineageflow_n1000/{baseline,framework}.fasta (1000 records each, Wave 86).
# Outputs: verification_outputs/lineageflow_n1000_{baseline,framework}_q4_2026_v2.json
# Optional Phase C: requires .venvs/omegafold_venv/bin/python (Wave 84 sidecar).
# DO NOT run from this commit; user invokes via `bash tools/lineageflow_n1000_gpu_sweep.sh`.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
VENV_PY=".venvs/lineageflow_venv/bin/python"
RUN_REAL="tools/run_real_ckpt_eval.py"
NFE=250
SEEDS=42
COMMON_ARGS=(--model lineageflow --seeds "$SEEDS" --nfe-budgets "$NFE"
             --force-mode real --metric-mode real --composite-metric real)
for ARM in baseline framework; do
  echo "[wave108.c] Phase ${ARM}: upstream eval (family_validity + novelty)"
  timeout 3600 "$VENV_PY" "$RUN_REAL" "${COMMON_ARGS[@]}" \
    --output "verification_outputs/lineageflow_n1000_${ARM}_q4_2026_v2.json"
done
OMEGA_PY=".venvs/omegafold_venv/bin/python"
if [[ -x "$OMEGA_PY" ]]; then
  echo "[wave108.c] Phase C: OmegaFold foldability + self_consistency (Python 3.10 sidecar)"
  timeout 7200 "$OMEGA_PY" tools/run_lineageflow_n1000_foldability_omegafold.py \
    --baseline-fasta data/lineageflow_n1000/baseline.fasta \
    --framework-fasta data/lineageflow_n1000/framework.fasta \
    --output-dir verification_outputs/lineageflow_n1000_foldability_q4_2026_v2 \
    --max-seqs 1000
else
  echo "[wave108.c] Phase C SKIPPED: $OMEGA_PY not found (foldability blocked)"
fi
echo "[wave108.c] DONE — see verification_outputs/lineageflow_n1000_*_q4_2026_v2.json"
