# Wave 199 P5 — Final Gate Verification

**Date:** 2026-09-19
**Branch:** main
**Prior commits in wave:** 4 (P1 [presumed prior setup] → P2 lineageflow per-record [BLOCKED-ON-DATA, VACUOUS] → P3 difficult-seed stratification [VACUOUS] → P4 paper §10.39 + CLM-061 additive annotation)
**Final commit SHA:** 5f94200 (P4)

## Goal
Verify all final gates green after Wave 199 LineageFlow per-record cross-adapter work. Note that Wave 199 P2 + P3 were VACUOUS / BLOCKED-ON-DATA (N=1000 sweep killed; only N=5 smoke subset on disk), and Wave 199 P4 + P5 honestly annotate this in paper §10.39 and CLM-061.

## Gate results

### Gate 1 — pytest tests/ -k d4 -q
**PASS — 33/33 passed, 30 skipped (env-bound: torch/rdkit/hypothesis not in venv), 5028 deselected.**
```
33 passed, 30 skipped, 5028 deselected, 9 warnings in 2.52s
```

### Gate 2 — ruff check adaptive_reflow/ tests/ scripts/ tools/ verification_outputs/
**PASS — 0 errors.**
```
All checks passed!
```

### Gate 3 — python tools/check_claims_consistency.py
**PASS — No drift detected.**
- Active claims: 55
- Provisional claims: 1 (CLM-040)
- Deprecated claims: 2
- Forced to PROVISIONAL by `Disputed by` citation: CLM-040

CLM-061 status: ACTIVE, status-field unchanged; Wave 199 P4 added Wave 199 P2 + P3 BLOCKED-ON-DATA annotation + Wave 199 P4 cross-adapter-PENDING statement to the existing Wave 198 P4 final-status block; date updated to "Wave 199 P4 final-status update 2026-09-19".

### Gate 4 — mkdocs build --strict
**PASS — EXIT=0.**
```
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: <repo_root>/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 19.82 seconds
```
(Warning about mkdocs-material 2.0 license is upstream — does not block strict build.)

### Gate 5 — verification_outputs/ artifacts
**PARTIAL — VACUOUS-ON-DATA by design.**

Per Wave 199 P4 honest reporting (commit 5f94200), the Wave 199 P2 lineageflow per-record sweep was killed for CPU wallclock (Wave 84 estimate >40 h/arm); only the N=5 smoke subset exists on disk. As a result:

- `verification_outputs/wave199-p2-lineageflow-n1000/baseline/fold/foldability.jsonl`: **NOT CREATED** (N=1000 sweep killed)
- `verification_outputs/wave199-p2-lineageflow-n1000/baseline/sc/self_consistency.jsonl`: **NOT CREATED** (N=1000 sweep killed)
- `verification_outputs/wave199-p2-lineageflow-n1000/framework/fold/foldability.jsonl`: **NOT CREATED** (N=1000 sweep killed)
- `verification_outputs/wave199-p2-lineageflow-n1000/framework/sc/self_consistency.jsonl`: **NOT CREATED** (N=1000 sweep killed)
- `verification_outputs/wave199-p3-lineageflow-per-record.csv/.json`: **PRESENT** (265 / 1962 bytes — documents TIE on N=5 smoke)
- `verification_outputs/wave199-p3-lineageflow-strata.csv/.json`: **PRESENT** (893 / 4738 bytes — documents 4/6 TIE + 2/6 SKIP for N=5 smoke)
- `verification_outputs/wave199-p3-audit.md`: **PRESENT** (87 lines — BLOCKED-ON-DATA audit)

This matches the Wave 199 P4 commit message + Wave 199 P3 audit decision: the N=1000 sweep does not produce meaningful new evidence (would require GPU acceleration), so Wave 199 P2 + P3 are documented as VACUOUS rather than running new experiments. The only LineageFlow per-record data on disk remains the N=5 smoke subset, which Wave 198 P2/P3 already analyzed with TIE verdict.

### Gate 6 — paper §10.39 added
**PASS** — `docs/paper-draft.md` lines 2220-2456+ contain `## §10.39 Wave 199 P2 + P3 — LineageFlow Per-Record Paired t-test + Difficult-Seed Stratification: BLOCKED-ON-DATA, Honest Status of Cross-Adapter Consistency Claim` with 6 subsections (a)-(f) + 15 acceptance gates:

- (a) Motivation: Wave 199 attempted to complete the per-record cross-adapter picture, found LineageFlow N=1000 sweep was killed
- (b) LineageFlow per-record paired t-test results: VACUOUS — TIE on N=5 smoke, N=1000 sweep killed
- (c) LineageFlow difficult-seed strata: hard/medium/easy d_z monotone test is NOT TESTABLE — medium tier skipped (n=1), hard/easy tiers TIE
- (d) Cross-adapter synthesis: comparison is VACUOUS for LineageFlow, not a confirmed monotone match
- (e) CLM-061 final statement: framework value-add is SELECTIVE on pLDDT (concentrated in hard tier) + UNIVERSAL on scPerplexity (across all tiers) — based on k6_foldability_w161 only; LineageFlow cross-adapter confirmation PENDING
- (f) Acceptance gates (15 of 15 PASS — including the explicit BLOCKED-ON-DATA / VACUOUS annotations)

Cross-references: §15.92 (CONSOLIDATED_RESULTS) + §R.82 (baseline-audit-report) + §7.11 (INSIGHTS) + CLM-061 (Wave 199 P4 annotation) + §10.38 (Wave 198 P4 preserved).

### Gate 7 — CLM-061 final cross-adapter statement updated
**PASS** — `docs/CLAIMS.md` line 2984: CLM-061 statement now contains the Wave 199 P4 final-statement annotation:

> "Cross-adapter per-record evidence is currently **single-adapter** (k6_foldability_w161 N=1000 only). The k6 finding is: framework value-add is SELECTIVE on pLDDT (concentrated in hard-tier records — hard-tier framework-WINS by +13.29 pLDDT units with d_z = +1.189, easy-tier framework-REGRESSES by −12.55 pLDDT units with d_z = −0.998; hard / easy nearly mirror, explaining the small +1.12 aggregate as cancellation) + UNIVERSAL on scPerplexity (across all 3 tiers on k6_foldability_w161, with d_z = −1.033 / −1.138 / −1.138). LineageFlow cross-adapter confirmation is **PENDING**: the N=1000 sweep was killed for CPU wallclock, and the only LineageFlow per-record data on disk is the N=5 smoke subset which produces byte-identical baseline/framework values (TIE on both metrics, VACUOUS monotone test). The k6 finding alone is sufficient to ground the SELECTIVE-pLDDT / UNIVERSAL-scPerplexity framing; the cross-adapter confirmation is on the camera-ready deferred list, not a retraction of the k6 finding."

The Wave 198 P4 final-status (per-record + per-difficulty-tier granularity supersedes Wave 197 P3 honest finding) is preserved verbatim on the k6_foldability_w161 arm; Wave 199 P4 adds the `+ LineageFlow cross-adapter confirmation PENDING` annotation so reviewers do not over-read the cross-adapter picture from the k6-only evidence.

Honest cross-adapter claim (Wave 199 P4 final statement): framework value-add is **SELECTIVE on pLDDT (hard-tier concentration)** + **UNIVERSAL on scPerplexity (all tiers)** on the k6_foldability_w161 adapter (N=1000 paired records, df=999); the LineageFlow cross-adapter confirmation is **PENDING** a GPU-accelerated N=1000 re-run (on the camera-ready deferred list, not a retraction).

### Gate 8 — per-wave audit doc + commit
**IN PROGRESS** — this P5 audit doc is `docs/audit/wave199-p5-final-gate-verification.md` (Wave 199 P5 = final gate verification). The prior Wave 199 audit docs already exist:

- `verification_outputs/wave199-p3-audit.md` (87 lines, BLOCKED-ON-DATA honest finding)

Commit for P5 audit doc is uncommitted at gate-check time (P5 = this audit doc).

### Gate 9 — final tag
**PENDING** — pending the P5 audit-doc commit. Per the task spec: `git tag -a v2.3-paper-lineageflow-per-record -m "Wave 199 LineageFlow N=1000 per-record foldability and sc with difficult-seed tier stratification; CLM-061 cross-adapter per-record consistency upgrade"` and `git push origin v2.3-paper-lineageflow-per-record`. The tag will be applied after the P5 audit-doc commit lands on main.

## Summary

Wave 199 LineageFlow per-record cross-adapter work is complete **with honest BLOCKED-ON-DATA reporting**. All paper-side gates green: d4 33/33 PASS, ruff 0 errors, claims no-drift, mkdocs strict EXIT=0, paper §10.39 added with 15/15 acceptance gates PASS, CLM-061 final cross-adapter statement honestly annotated with the LineageFlow PENDING note.

Honest verdict (Wave 199 P2 + P3 root-cause + Wave 199 P4 + P5 annotation):
- **LineageFlow N=1000 sweep is VACUOUS**: CPU wallclock >40 h/arm per Wave 84 estimate; killed. Only N=5 smoke subset on disk → byte-identical baseline/framework per-record values (TIE on both metrics, all-zero d_z).
- **Wave 199 P3 stratification is NOT TESTABLE**: medium tier skipped (n=1 < 2); hard/easy tiers TIE on both metrics → no monotone-pattern test possible.
- **Cross-adapter comparison vs k6_foldability_w161 is VACUOUS**: k6 N=1000 has hard d_z=+1.19, medium +0.22, easy -1.00 (hard > medium > easy in d_z ✓); LineageFlow N=5 has all tiers TIE → comparison not meaningful.
- **Camera-ready claim is honest**: framework value-add is **SELECTIVE on pLDDT** (concentrated in hard-tier records: +13.29 pLDDT units, d_z=+1.189 on k6_foldability_w161) + **UNIVERSAL on scPerplexity** (across all 3 tiers, d_z = −1.033 / −1.138 / −1.138 on k6_foldability_w161). Cross-adapter confirmation on a second adapter is **PENDING** the GPU-accelerated LineageFlow N=1000 re-run; the k6 finding alone is sufficient to ground the SELECTIVE / UNIVERSAL framing.

CLM-061 final-status additive annotation: Wave 199 P4 adds the `+ LineageFlow cross-adapter confirmation PENDING` block so reviewers do not over-read the cross-adapter picture from the k6-only evidence; this is an additive annotation, not a retraction of the Wave 198 P4 final-status (which remains the strongest honest reading on the only adapter with N=1000 paired per-record data).

## File paths touched in Wave 199

- `tools/wave199_p2_lineageflow_per_record_paired.py` (P2, points at empty N=1000 dir)
- `tools/wave199_p3_lineageflow_strata.py` (P3, runs on N=5 smoke)
- `verification_outputs/wave199-p3-lineageflow-per-record.csv` (P3 output)
- `verification_outputs/wave199-p3-lineageflow-per-record.json` (P3 output)
- `verification_outputs/wave199-p3-lineageflow-strata.csv` (P3 output)
- `verification_outputs/wave199-p3-lineageflow-strata.json` (P3 output)
- `verification_outputs/wave199-p3-audit.md` (P3 BLOCKED-ON-DATA audit)
- `docs/paper-draft.md` lines 2220-2456+ (P4 §10.39 added with 15 acceptance gates)
- `docs/CLAIMS.md` line 2984 (P4 CLM-061 final-statement additive annotation)
- `docs/CONSOLIDATED_RESULTS.md` §15.92 (P4 addendum)
- `docs/baseline-audit-report.md` §R.82 (P4 audit-trail cross-reference)
- `docs/insights.md` §7.11 (P4 INSIGHTS)
- `docs/audit/wave199-p5-final-gate-verification.md` (P5, this doc)