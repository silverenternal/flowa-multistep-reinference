#!/usr/bin/env bash
# AST-based mutation-testing runner (Bash).
#
# Windows-compatible replacement for tools/mutate/run_mutmut.sh: mutmut itself
# refuses to run on native Windows (upstream boxed/mutmut#397), so this wrapper
# drives tools/mutate/ast_mutator.py instead. See WINDOWS_LIMITATION.md.
#
# What it does:
#   a. runs ast_mutator.py against the six adaptive_reflow package directories
#   b. evaluates every generated mutant with `pytest tests/ -x --tb=no -q`
#      (pytest passes -> the mutant survived; pytest fails -> it was killed)
#   c. aggregates the verdicts into mutmut_results.json
#   d. regenerates tools/mutate/mutation_baseline.json with the real numbers
#   e. prints a summary and enforces the S-tier thresholds
#
# Usage:
#   bash tools/mutate/run_ast_mutation.sh                 # full sweep
#   bash tools/mutate/run_ast_mutation.sh --quick         # 4 critical modules
#   JOBS=8 bash tools/mutate/run_ast_mutation.sh          # more parallelism
#   bash tools/mutate/run_ast_mutation.sh adaptive_reflow/frame/merge.py
#
# Any positional arguments are treated as explicit --target values and
# override the default sweep.

set -u
set -o pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT" || exit 1

RESULTS_JSON="${RESULTS_JSON:-$REPO_ROOT/mutmut_results.json}"
JOBS="${JOBS:-4}"
TIMEOUT="${TIMEOUT:-300}"

# ---------------------------------------------------------------------------
# Locate an interpreter. The repo's venv is preferred; the layout differs
# between Windows (Scripts/python.exe) and POSIX (bin/python).
# ---------------------------------------------------------------------------
if [ -n "${PYTHON:-}" ]; then
    PY="$PYTHON"
elif [ -x "$REPO_ROOT/.venv/Scripts/python.exe" ]; then
    PY="$REPO_ROOT/.venv/Scripts/python.exe"
elif [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    PY="$REPO_ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PY="python3"
else
    PY="python"
fi

# ---------------------------------------------------------------------------
# Target selection.
# ---------------------------------------------------------------------------
QUICK_TARGETS=(
    "adaptive_reflow/frame/merge.py"
    "adaptive_reflow/frame/channel_rule.py"
    "adaptive_reflow/eval/claim_gate.py"
    "adaptive_reflow/schedule/cosine.py"
)

FULL_TARGETS=(
    "adaptive_reflow/contracts"
    "adaptive_reflow/universal"
    "adaptive_reflow/frame"
    "adaptive_reflow/eval"
    "adaptive_reflow/policy"
    "adaptive_reflow/schedule"
)

TARGET_ARGS=()
if [ "$#" -gt 0 ] && [ "${1:-}" = "--quick" ]; then
    shift
    for t in "${QUICK_TARGETS[@]}"; do
        TARGET_ARGS+=(--target "$t")
    done
elif [ "$#" -gt 0 ]; then
    for t in "$@"; do
        TARGET_ARGS+=(--target "$t")
    done
else
    for t in "${FULL_TARGETS[@]}"; do
        TARGET_ARGS+=(--target "$t")
    done
fi

echo "[run_ast_mutation] starting at $(date -Iseconds 2>/dev/null || date)"
echo "[run_ast_mutation] repo:        $REPO_ROOT"
echo "[run_ast_mutation] interpreter: $PY"
echo "[run_ast_mutation] jobs:        $JOBS"
echo "[run_ast_mutation] results:     $RESULTS_JSON"

# ---------------------------------------------------------------------------
# (a)-(d) Mutate, evaluate, aggregate, and regenerate the baseline.
# ---------------------------------------------------------------------------
"$PY" tools/mutate/ast_mutator.py run \
    "${TARGET_ARGS[@]}" \
    --output "$RESULTS_JSON" \
    --jobs "$JOBS" \
    --timeout "$TIMEOUT" \
    --baseline
RUN_RC=$?

if [ "$RUN_RC" -ne 0 ]; then
    echo "[run_ast_mutation] FAIL: mutation run exited $RUN_RC" >&2
    exit "$RUN_RC"
fi

# ---------------------------------------------------------------------------
# (e) Summary + S-tier gate.
# ---------------------------------------------------------------------------
"$PY" tools/mutate/ast_mutator.py summary "$RESULTS_JSON"

"$PY" tools/mutate/ast_mutator.py gate "$RESULTS_JSON"
GATE_RC=$?

if [ "$GATE_RC" -ne 0 ]; then
    echo "[run_ast_mutation] FAIL: mutation-score gate rejected the run" >&2
    exit "$GATE_RC"
fi

echo "[run_ast_mutation] PASS"
exit 0
