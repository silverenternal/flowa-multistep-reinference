#!/usr/bin/env bash
# Wave 112.D-3 — LineageFlow N=1000 GPU framework-vs-baseline sweep wrapper
# (thin launcher — all hardcoded shell constants moved to a YAML profile).
#
# Replaces the Wave 109.B shell wrapper which had 5 hardcoded constants
# (NFE/SEEDS/N_SAMPLES/VENV_PY/timeout). Those now live in
# configs/runs/lineageflow_n1000_gpu.yaml (Profile version 2026-09-11).
#
# Pattern: docs/audit/wave69-phase5-lineageflow-sweep.md §3 (3-shell-call template).
# Underlying wrappers: tools.upstream_eval.run_lineageflow_upstream_eval (Wave 81),
# tools.run_real_ckpt_eval.py (Wave 47 composite), tools._gpu_watchdog (auto-wired).
#
# Positional args (unchanged from Wave 109.B):
#   $1: arm            (baseline | framework)
#   $2: output_dir     (where the JSON goes)
#   $3: log_path       (path passed to caller for tee'd logging)
#
# Flags:
#   --config <yaml>    (default: configs/runs/lineageflow_n1000_gpu.yaml)
#
# The profile is parsed via a tiny inline `python -c yaml.safe_load(...)` so
# the schema validator (tools/eval/config.load_run_profile) is NOT applied
# (the YAML has shell-only keys like venv_py / timeout_s that are out-of-schema).
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "[wave112.d-3] USAGE: $0 <baseline|framework> <output_dir> <log_path> [--config <yaml>]" >&2
  exit 64
fi

ARM="$1"
OUTPUT_DIR="$2"
LOG_PATH="$3"
shift 3

CONFIG_PATH="configs/runs/lineageflow_n1000_gpu.yaml"
if [[ "${1:-}" == "--config" ]]; then
  if [[ $# -lt 2 ]]; then
    echo "[wave112.d-3] USAGE: --config requires a path argument" >&2
    exit 64
  fi
  CONFIG_PATH="$2"
  shift 2
fi

if [[ "$ARM" != "baseline" && "$ARM" != "framework" ]]; then
  echo "[wave112.d-3] ERROR: ARM must be 'baseline' or 'framework' (got '$ARM')" >&2
  exit 64
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Parse the YAML profile via Python (no schema validation; shell-only knobs).
# We extract: nfe_budgets[0] -> NFE, seed -> SEEDS, max_records -> N_SAMPLES,
# venv_py -> VENV_PY, timeout_s -> TIMEOUT. Emits shell assignments.
eval "$("$REPO_ROOT/.venvs/lineageflow_venv/bin/python" -c "
import os, sys, yaml
p = '$CONFIG_PATH'
if not os.path.isabs(p):
    p = os.path.join('$REPO_ROOT', p)
with open(p, encoding='utf-8') as f:
    cfg = yaml.safe_load(f)
print(f'NFE={cfg[\"nfe_budgets\"][0]}')
print(f'SEEDS={cfg[\"seed\"]}')
print(f'N_SAMPLES={cfg[\"max_records\"]}')
print(f'VENV_PY={cfg.get(\"venv_py\", \".venvs/lineageflow_venv/bin/python\")}')
print(f'TIMEOUT={cfg.get(\"timeout_s\", 7200)}')
")"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export PYTHONPATH="${PYTHONPATH:-}:$REPO_ROOT"
RUN_REAL="tools/run_real_ckpt_eval.py"
COMMON_ARGS=(--model lineageflow --seeds "$SEEDS" --nfe-budgets "$NFE"
             --force-mode real --metric-mode real --composite-metric real
             --lineageflow-upstream-eval --upstream-n-samples "$N_SAMPLES")

mkdir -p "$OUTPUT_DIR"
OUT_JSON="$OUTPUT_DIR/lineageflow_n1000_${ARM}_q4_2026_v2.json"

echo "[wave112.d-3] ARM=$ARM OUTPUT_DIR=$OUTPUT_DIR LOG_PATH=$LOG_PATH"
echo "[wave112.d-3] CONFIG_PATH=$CONFIG_PATH"
echo "[wave112.d-3] NFE=$NFE SEEDS=$SEEDS N_SAMPLES=$N_SAMPLES VENV_PY=$VENV_PY TIMEOUT=$TIMEOUT"
echo "[wave112.d-3] OUT_JSON=$OUT_JSON"
echo "[wave112.d-3] COMMON_ARGS=${COMMON_ARGS[*]}"

# Single arm invocation — emits a JSON with both baseline + framework
# (the run_real_ckpt_eval.py CLI doesn't expose an arm-filter; each cell
# runs both arms and the JSON contains both). The arm arg only controls
# the output path naming so the two invocations don't overwrite.
timeout "$TIMEOUT" "$VENV_PY" "$RUN_REAL" "${COMMON_ARGS[@]}" \
  --output "$OUT_JSON"

echo "[wave112.d-3] DONE — see $OUT_JSON"
echo "[wave112.d-3] log_path=$LOG_PATH was the tee target — caller controls"