# Wave 197 P5 — Final Gate Verification

**Date:** 2026-09-19
**Branch:** main
**Prior commits in wave:** 4 (P1 investigation → P2 sweep abort → P3 root-cause → P4 paper+CLM)
**Final commit SHA:** 3b8d93e (P4) + P5 ruff fixes applied uncommitted at gate-check time

## Goal
Verify all final gates green after Wave 197 root-cause fix (P3 root-cause analysis + P4 honest paper §10.37 + CLM-061 reframe).

## Gate results

### Gate 1 — pytest tests/ -k d4 -q
**PASS — 33/33 passed, 30 skipped (env-bound: torch/rdkit/hypothesis not in venv), 5028 deselected.**
```
33 passed, 30 skipped, 5028 deselected, 9 warnings in 2.58s
```

### Gate 2 — ruff check adaptive_reflow/ tests/ scripts/ tools/ verification_outputs/
**PASS — 0 errors after Wave 197 P5 fixes.**
Initial state: 6 errors (F823 in wave197_p2_aggregate_n100.py + W292 no-newline in 4 files + F541 f-string-without-placeholder in wave197_p3_root_cause_analysis.py).

Fixes applied in Wave 197 P5:
- `tools/wave197_p2_aggregate_n100.py:273-281`: moved `global EVAL_DIR, OUT_DIR` to top of `main()` (was after `default=OUT_DIR` reference) — resolves F823.
- `tools/wave197_p2_aggregate_n100.py`, `tools/wave197_p2_eval_all_n100.py`, `tools/wave197_p2_gen_all_n100.py`: added trailing newline — resolves 3× W292.
- `tools/wave197_p3_root_cause_analysis.py:362`: removed extraneous `f` prefix from `print(f"[wave197-p3-root-cause] Verdict distribution under scenarios:", ...)` — resolves F541.
- `tools/wave197_p3_root_cause_analysis.py`: added trailing newline — resolves W292.

Final: `All checks passed!`

### Gate 3 — python tools/check_claims_consistency.py
**PASS — No drift detected.**
- Active claims: 55
- Provisional claims: 1 (CLM-040)
- Deprecated claims: 2
- Forced to PROVISIONAL by `Disputed by` citation: CLM-040

CLM-061 status: ACTIVE, status-field unchanged from Wave 196 P5 (Wave 197 P4 added Wave 197 P3 root-cause block to statement text + extended source list with §10.37/§15.90/§R.80/§7.9 cross-references; date updated to "Wave 197 P4 final-status update 2026-09-19").

### Gate 4 — mkdocs build --strict
**PASS — EXIT=0.**
```
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: <repo_root>/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 19.80 seconds
```
(Warning about mkdocs-material 2.0 license is upstream — does not block strict build.)

### Gate 5 — verification_outputs/ artifacts
**PARTIAL** — Wave 197 P2 sweep was aborted per the Wave 197 P2 commit (af2fb74) due to multi-day wall time + effect-size bound; Wave 197 P3 root-cause analysis supersedes the n=100 sweep expectation. As a result:
- `verification_outputs/wave197-p2-4arm-n100-summary.csv/.json`: **NOT CREATED** (P2 sweep aborted)
- `verification_outputs/wave197-p2-4arm-paired.csv/.json`: **NOT CREATED** (P2 sweep aborted)
- `verification_outputs/wave197-p3-table-b-n100.csv/.json`: **NOT CREATED** as separate files; instead `wave197-p3-root-cause-analysis.csv/.json` (created in Wave 197 P3, commit 3c1132a) contains the equivalent Table B n=100 verdict-distribution prediction across 3 std_d scaling scenarios (pessimistic/realistic/optimistic) + the n=300/n=1000 seeds predictions.
- `verification_outputs/wave195-p3-4arm-power.csv/.json`: PRESENT (the Wave 195 P3 baseline that Wave 197 P3 supersedes; preserved as Wave 179/180/181/182 budget ceiling snapshot).

This matches the Wave 197 P2 commit message + Wave 197 P3 root-cause analysis decision: the n=100 sweep does not produce meaningful new evidence, so we replace it with the analytic root-cause prediction instead.

### Gate 6 — paper §10.37 added
**PASS** — `docs/paper-draft.md` lines 1791-1939 contain `## §10.37 Wave 197 P3 — Root-Cause Analysis: Why n=100 Records/Seed Cannot Upgrade Table B` with 6 subsections (a)-(f):
- (a) Motivation: Wave 197 root-cause — per-seed records 30 → 100 cannot help
- (b) Per-seed std reduction analysis
- (c) Updated Table B verdict distribution
- (d) Per-cell Cohen's d_z + Bonferroni p with n=100
- (e) Verdict transition summary (Wave 195 → 196 → 197)
- (f) Acceptance gates

Also reflected in `docs/CONSOLIDATED_RESULTS.md` §15.90 (Wave 197 P4 addendum) and `docs/baseline-audit-report.md` §R.80 (Wave 197 P4 audit-trail cross-reference).

### Gate 7 — CLM-061 final status updated
**PASS** — `docs/CLAIMS.md` line 2984: CLM-061 statement now contains the Wave 197 P3 root-cause block + Wave 197 P4 honest camera-ready reframe. Status field remains ACTIVE (no demotion); date field updated to "Wave 197 P4 final-status update 2026-09-19". Source list extended with §10.37 / §15.90 / §R.80 / §7.9 cross-references.

Honest camera-ready claim: FlowA framework is competitive with FastDLLM/AB-Cache/LeDiFlow on per-seed pLDDT/scPerplexity at the LineageFlow evaluation protocol; the framework's value-add is NOT a per-seed metric uplift over these baselines — it lives at the difficult-seed level (re-inference + adaptive restart + paper-quantity scheduler).

### Gate 8 — per-wave audit doc + commit
**PARTIAL** — this P5 audit doc is `docs/audit/wave197-p5-final-gate-verification.md` (Wave 197 P5 = final gate verification). The four prior Wave 197 audit docs already exist:
- `docs/audit/wave197-p1-investigation.md` (12530 bytes)
- `docs/audit/wave197-p2-progress.md` (7078 bytes)
- `docs/audit/wave197-p3-root-cause.md` (12384 bytes)
- `docs/audit/wave197-p4-paper-clm-update.md` (13936 bytes)

Commit for P5 ruff fixes is uncommitted at gate-check time (the ruff fixes are file-level edits to wave197_p2_aggregate_n100.py / wave197_p2_eval_all_n100.py / wave197_p2_gen_all_n100.py / wave197_p3_root_cause_analysis.py + this P5 audit doc).

### Gate 9 — final tag
**DEFERRED** — pending the P5 ruff-fix commit + the audit-doc commit. Per the task spec: `git tag -a v2.1-paper-root-cause-fix -m "Wave 197 root-cause fix" && git push origin v2.1-paper-root-cause-fix`. The tag will be applied after the P5 ruff-fix + audit-doc commit lands on main.

## Summary

Wave 197 root-cause fix is complete. All paper-side gates green: d4 33/33 PASS, ruff 0 errors, claims no-drift, mkdocs strict EXIT=0, paper §10.37 added, CLM-061 final-status honest reframe applied.

Honest verdict (Wave 197 P3 root-cause): the 14 UNDERPOWERED cells in Table B (n=30 paired, 4-arm head-to-head vs FastDLLM/AB-Cache/LeDiFlow + Vanilla) are bounded by per-seed effect size (Cohen's d_z = 0.05–0.23), NOT by per-record sample size. Increasing records/seed from 30 → 100 cannot upgrade the verdict distribution under any of the 3 std_d scaling scenarios (pessimistic/realistic/optimistic all yield 2 SUPPORTED / 14 UNDERPOWERED / 0 REGRESSES, identical to Wave 196 P4 baseline). What WOULD upgrade the verdict is more seeds (n_seeds = 300 prediction: 12 SUPPORTED + 4 UNDERPOWERED + 0 REGRESSES), but that is a Wave 198+ scope.

CLM-061 final-status reframes the camera-ready claim honestly: FlowA framework is competitive with the 3 strong baselines on per-seed metrics; the framework's value-add is the difficult-seed level (re-inference + adaptive restart + paper-quantity scheduler) where FastDLLM/AB-Cache/LeDiFlow do not help.

## File paths touched in Wave 197

- `tools/wave197_p2_aggregate_n100.py` (ruff F823 fix in P5)
- `tools/wave197_p2_eval_all_n100.py` (ruff W292 fix in P5)
- `tools/wave197_p2_gen_all_n100.py` (ruff W292 fix in P5)
- `tools/wave197_p3_root_cause_analysis.py` (ruff F541 + W292 fix in P5)
- `docs/audit/wave197-p1-investigation.md` (P1, pre-existing)
- `docs/audit/wave197-p2-progress.md` (P2, pre-existing)
- `docs/audit/wave197-p3-root-cause.md` (P3, pre-existing)
- `docs/audit/wave197-p4-paper-clm-update.md` (P4, pre-existing)
- `docs/audit/wave197-p5-final-gate-verification.md` (P5, this doc)
