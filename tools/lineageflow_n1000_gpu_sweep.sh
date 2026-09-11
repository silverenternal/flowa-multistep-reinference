#!/usr/bin/env bash
# Wave 108.C — LineageFlow N=1000 GPU framework-vs-baseline sweep wrapper
# REUSE-2: chains 3 existing scripts into a single entry point.
# Pattern: docs/audit/wave69-phase5-lineageflow-sweep.md §3 (3-shell-call template).
# Underlying wrappers: tools.upstream_eval.run_lineageflow_upstream_eval (Wave 81),
# tools.run_real_ckpt_eval.py (Wave 47 composite), tools._gpu_watchdog (auto-wired).
# Inputs: data/lineageflow_n1000/{baseline,framework}.fasta (1000 records each, Wave 86).
# Outputs: <output_dir>/lineageflow_n1000_<arm>_q4_2026_v2.json
# Optional Phase C: requires .venvs/omegafold_venv/bin/python (Wave 84 sidecar).
#
# Wave 109.B — accepts 3 positional args:
#   $1: arm            (baseline | framework)
#   $2: output_dir     (where the JSON goes)
#   $3: log_path       (path passed to caller for tee'd logging)
#
# Sets --upstream-n-samples 1000 explicitly (the Wave 108.C default was 1000
# implicitly via the CLI default; making it explicit so the value is obvious
# from the wrapper invocation). Uses --lineageflow-upstream-eval so the cell
# invokes tools/upstream_eval.run_lineageflow_upstream_eval as a subprocess
# (per-record HMMER hmmscan + MMseqs2 novelty against Pfam-A.hmm).
#
# NOTE on arm semantics: each invocation runs the FULL cell (baseline +
# framework ODE) and emits one JSON containing both arms. The arm arg only
# controls the OUTPUT path naming so the two invocations can be written to
# separate directories (no overwrites). Downstream code reads the same arm
# out of each JSON when comparing.
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "[wave109.b] USAGE: $0 <baseline|framework> <output_dir> <log_path>" >&2
  exit 64
fi

ARM="$1"
OUTPUT_DIR="$2"
LOG_PATH="$3"

if [[ "$ARM" != "baseline" && "$ARM" != "framework" ]]; then
  echo "[wave109.b] ERROR: ARM must be 'baseline' or 'framework' (got '$ARM')" >&2
  exit 64
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export PYTHONPATH="${PYTHONPATH:-}:$REPO_ROOT"
VENV_PY=".venvs/lineageflow_venv/bin/python"
RUN_REAL="tools/run_real_ckpt_eval.py"
NFE=250
SEEDS=42
N_SAMPLES=1000
COMMON_ARGS=(--model lineageflow --seeds "$SEEDS" --nfe-budgets "$NFE"
             --force-mode real --metric-mode real --composite-metric real
             --lineageflow-upstream-eval --upstream-n-samples "$N_SAMPLES")

mkdir -p "$OUTPUT_DIR"
OUT_JSON="$OUTPUT_DIR/lineageflow_n1000_${ARM}_q4_2026_v2.json"

echo "[wave109.b] ARM=$ARM OUTPUT_DIR=$OUTPUT_DIR LOG_PATH=$LOG_PATH"
echo "[wave109.b] OUT_JSON=$OUT_JSON"
echo "[wave109.b] COMMON_ARGS=${COMMON_ARGS[*]}"

# Single arm invocation — emits a JSON with both baseline + framework
# (the run_real_ckpt_eval.py CLI doesn't expose an arm-filter; each cell
# runs both arms and the JSON contains both). The arm arg only controls
# the output path naming so the two invocations don't overwrite.
timeout 7200 "$VENV_PY" "$RUN_REAL" "${COMMON_ARGS[@]}" \
  --output "$OUT_JSON"

echo "[wave109.b] DONE — see $OUT_JSON"
echo "[wave109.b] log_path=$LOG_PATH was the tee target — caller controls"