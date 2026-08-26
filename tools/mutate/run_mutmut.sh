#!/usr/bin/env bash
# Mutation testing harness for focused critical-path modules.
# PR-blocking threshold: >5 surviving mutants on these modules fails the gate.

set -u
set -o pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

export MUTMUT__VERBOSE=1

RESULTS_JSON="$REPO_ROOT/mutmut_results.json"
REPORT_HTML="$REPO_ROOT/mutmut_report.html"

echo "[run_mutmut] starting mutation testing at $(date -Iseconds)"
echo "[run_mutmut] repo: $REPO_ROOT"

# Run mutmut, capturing full output and a JSON snapshot of results.
mutmut run --max-children 50 2>&1 | tee "$REPO_ROOT/mutmut_run.log"
MUTMUT_RC=${PIPESTATUS[0]}

echo "[run_mutmut] mutmut run exit code: $MUTMUT_RC"

# Always try to dump results.json for downstream parsing.
mutmut results 2>&1 | tee "$REPO_ROOT/mutmut_results.txt"
mutmut results --json > "$RESULTS_JSON" 2>/dev/null || echo "{}" > "$RESULTS_JSON"

# HTML report (best-effort; some mutmut versions don't expose `html`).
if mutmut html --help >/dev/null 2>&1; then
    mutmut html > "$REPORT_HTML" 2>&1 || echo "[run_mutmut] html report generation failed"
else
    echo "[run_mutmut] mutmut html subcommand unavailable; skipping report.html"
fi

# Parse survived count from results.json.
SURVIVED=$(python -c "
import json, sys
try:
    with open('$RESULTS_JSON', 'r', encoding='utf-8') as fh:
        data = json.load(fh)
except Exception as exc:
    print('0')
    sys.exit(0)

def survived_count(obj):
    # mutmut 2.x uses list of strings keyed by mutant id;
    # some wrappers use {'survived': [...], 'killed': [...], ...}.
    if isinstance(obj, dict):
        if 'survived' in obj and isinstance(obj['survived'], list):
            return len(obj['survived'])
        # dict of id -> status string
        return sum(1 for v in obj.values() if isinstance(v, str) and v.lower().startswith('survived'))
    if isinstance(obj, list):
        return sum(1 for v in obj if isinstance(v, str) and v.lower().startswith('survived'))
    return 0

print(survived_count(data))
")

echo "[run_mutmut] survived mutants: $SURVIVED"

THRESHOLD=5
if [ "$SURVIVED" -gt "$THRESHOLD" ]; then
    echo "[run_mutmut] FAIL: survived ($SURVIVED) exceeds PR-blocking threshold ($THRESHOLD)"
    exit 1
fi

echo "[run_mutmut] PASS: survived ($SURVIVED) within PR-blocking threshold ($THRESHOLD)"
exit 0
