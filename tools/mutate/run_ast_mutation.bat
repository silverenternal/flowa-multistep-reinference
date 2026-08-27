@echo off
REM AST-based mutation-testing runner (Windows batch).
REM
REM Native-Windows counterpart to tools/mutate/run_ast_mutation.sh. mutmut
REM refuses to run on Windows at all (upstream boxed/mutmut#397), so this
REM wrapper drives tools/mutate/ast_mutator.py. See WINDOWS_LIMITATION.md.
REM
REM What it does:
REM   a. runs ast_mutator.py against the six adaptive_reflow package dirs
REM   b. evaluates every mutant with `pytest tests\ -x --tb=no -q`
REM      (pytest passes -> mutant survived; pytest fails -> mutant killed)
REM   c. aggregates the verdicts into mutmut_results.json
REM   d. regenerates tools\mutate\mutation_baseline.json with the real numbers
REM   e. prints a summary and enforces the S-tier thresholds
REM
REM Usage:
REM   tools\mutate\run_ast_mutation.bat                     full sweep
REM   tools\mutate\run_ast_mutation.bat --quick             4 critical modules
REM   tools\mutate\run_ast_mutation.bat adaptive_reflow\frame\merge.py
REM
REM Environment overrides: PYTHON, JOBS, TIMEOUT, RESULTS_JSON

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%" || exit /b 1

if not defined RESULTS_JSON set "RESULTS_JSON=%REPO_ROOT%\mutmut_results.json"
if not defined JOBS set "JOBS=4"
if not defined TIMEOUT set "TIMEOUT=300"

REM ---------------------------------------------------------------------
REM Locate an interpreter: repo venv first, then PATH.
REM ---------------------------------------------------------------------
if defined PYTHON (
    set "PY=%PYTHON%"
) else if exist "%REPO_ROOT%\.venv\Scripts\python.exe" (
    set "PY=%REPO_ROOT%\.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

REM ---------------------------------------------------------------------
REM Target selection. Positional args override the default sweep.
REM ---------------------------------------------------------------------
set "TARGET_ARGS="
if "%~1"=="--quick" (
    set "TARGET_ARGS=--target adaptive_reflow/frame/merge.py --target adaptive_reflow/frame/channel_rule.py --target adaptive_reflow/eval/claim_gate.py --target adaptive_reflow/schedule/cosine.py"
) else if not "%~1"=="" (
    for %%A in (%*) do set "TARGET_ARGS=!TARGET_ARGS! --target %%A"
) else (
    set "TARGET_ARGS=--target adaptive_reflow/contracts --target adaptive_reflow/universal --target adaptive_reflow/frame --target adaptive_reflow/eval --target adaptive_reflow/policy --target adaptive_reflow/schedule"
)

echo [run_ast_mutation] repo:        %REPO_ROOT%
echo [run_ast_mutation] interpreter: %PY%
echo [run_ast_mutation] jobs:        %JOBS%
echo [run_ast_mutation] results:     %RESULTS_JSON%

REM ---------------------------------------------------------------------
REM (a)-(d) Mutate, evaluate, aggregate, regenerate the baseline.
REM ---------------------------------------------------------------------
"%PY%" tools\mutate\ast_mutator.py run !TARGET_ARGS! --output "%RESULTS_JSON%" --jobs %JOBS% --timeout %TIMEOUT% --baseline
if errorlevel 1 (
    echo [run_ast_mutation] FAIL: mutation run failed >&2
    exit /b 1
)

REM ---------------------------------------------------------------------
REM (e) Summary + S-tier gate.
REM ---------------------------------------------------------------------
"%PY%" tools\mutate\ast_mutator.py summary "%RESULTS_JSON%"

"%PY%" tools\mutate\ast_mutator.py gate "%RESULTS_JSON%"
if errorlevel 1 (
    echo [run_ast_mutation] FAIL: mutation-score gate rejected the run >&2
    exit /b 1
)

echo [run_ast_mutation] PASS
exit /b 0
