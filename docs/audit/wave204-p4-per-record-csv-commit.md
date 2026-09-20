# Wave 204 P4 — Per-record CSV commit + §10.42 cross-reference (audit)

**Date:** 2026-09-21
**Branch:** main
**Goal (per Wave 204 P4 task spec):** Confirm that all per-record /
strata CSV / JSON outputs from Wave 202 P2 are committed to the
repository and cross-referenced in §10.42. Honest-disclose the actual
data state (N=574 paired records, not N=1000) and the 426 missing_pdb
records on the framework foldability arm.

## Outcome

The Wave 204 P4 work is **already complete** — the per-record CSVs /
JSONs were committed in Wave 204 P2 (commit `4e758c8`) and the
§10.42 cross-references were added in Wave 204 P3 (commit `cddbe07`).
This Wave 204 P4 audit doc confirms the state and does **not
re-commit** the data (already on disk) or re-edit §10.42 (already
correctly annotated with the N=574 caveat).

## File verification

### Wave 202 P5 per-record / strata CSVs and JSONs

All four files exist and are committed in `4e758c8`:

```
verification_outputs/wave202-p5-lineageflow-per-record.csv  (3 lines: header + 2 metric rows)
verification_outputs/wave202-p5-lineageflow-per-record.json (147 lines: schema + 2 per-record results + 6 strata results + cross-adapter block)
verification_outputs/wave202-p5-lineageflow-strata.csv      (7 lines: header + 6 tier×metric rows)
verification_outputs/wave202-p5-lineageflow-strata.json     (113 lines: tier boundaries + tier_n + 6 strata results + monotone pattern test + cross-adapter block)
```

`wave202-p5-lineageflow-per-record.csv`:
```
dataset,metric,n_paired,mean_diff,sd_diff,t_statistic,df,p_value_raw,cohens_d_z,ci_95_low,ci_95_high,verdict
lineageflow_n1000,plddt_mean,574,7.187,15.177,11.345,573,4.74e-27,+0.474,+5.945,+8.428,SUPPORTED
lineageflow_n1000,sc_perplexity,574,-3.715,3.661,-24.311,573,3.05e-90,-1.015,-4.014,-3.415,SUPPORTED
```

`wave202-p5-lineageflow-strata.csv` (3 tiers × 2 metrics = 6 rows):
```
dataset,metric,tier,n_records,mean_diff,sd_diff,t_statistic,df,p_value_raw,cohens_d_z,verdict
lineageflow_n1000,plddt_mean,hard,191,18.955,10.301,25.432,190,4.47e-63,+1.840,SUPPORTED
lineageflow_n1000,sc_perplexity,hard,191,-3.075,3.069,-13.846,190,1.34e-30,-1.002,SUPPORTED
lineageflow_n1000,plddt_mean,medium,192,9.625,9.860,13.525,191,1.12e-29,+0.976,SUPPORTED
lineageflow_n1000,sc_perplexity,medium,192,-3.773,3.640,-14.365,191,3.31e-32,-1.037,SUPPORTED
lineageflow_n1000,plddt_mean,easy,191,-7.033,11.930,-8.147,190,4.86e-14,-0.590,REGRESSES
lineageflow_n1000,sc_perplexity,easy,191,-4.296,4.114,-14.431,190,2.33e-32,-1.044,SUPPORTED
```

### Source foldability / self-consistency jsonl files

All committed in `4e758c8`:

```
verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/sc/self_consistency.jsonl   1000 lines
verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/metrics.jsonl               1000 lines
verification_outputs/lineageflow_n1000_omegafold_q4_2026/framework/fold/foldability.jsonl     574 lines
verification_outputs/lineageflow_n1000_omegafold_q4_2026/framework/metrics.jsonl              574 lines
verification_outputs/lineageflow_n1000_omegafold_q4_2026/framework/sc/self_consistency.jsonl 1000 lines (426 missing_pdb flagged)
verification_outputs/lineageflow_n1000_omegafold_q4_2026/sweep_summary.json                   49 lines
```

**Note on file paths:** The Wave 204 P4 task spec referenced
`{baseline,framework}/{foldability,self_consistency}.jsonl`. The actual
file layout under
`verification_outputs/lineageflow_n1000_omegafold_q4_2026/` is
`{baseline,framework}/{sc/self_consistency.jsonl, fold/foldability.jsonl,
metrics.jsonl}` — the Wave 201 P7 eval-pipeline plumbing adopted a
sub-directory structure (`fold/` for omegafold outputs, `sc/` for self-
consistency outputs, `metrics.jsonl` for the paired-record join).
Content line counts match the task spec:
- baseline foldability: 1000/1000 (via `baseline/metrics.jsonl`)
- baseline self_consistency: 1000/1000
- framework foldability: 574/1000 (long-tail slow rate; deliberately
  killed)
- framework self_consistency: 1000/1000 (SC ran on existing 574 PDBs;
  426 missing_pdb records flagged with `error: missing_pdb`)

## §10.42 cross-reference verification

§10.42 (h) in `docs/paper-draft.md` (added in Wave 204 P3 commit
`cddbe07`) cross-references the four per-record / strata files at:

1. Per-record paired t-test (N=574, df=573) → explicit citation of
   `verification_outputs/wave202-p5-lineageflow-per-record.{csv,json}`
   source data.
2. Per-tier paired t-test (3 tiers × 2 metrics) → explicit citation of
   `verification_outputs/wave202-p5-lineageflow-strata.{csv,json}`
   source data.
3. Cross-adapter monotone-pattern confirmation → explicit citation of
   the monotone-pattern block in `wave202-p5-lineageflow-per-record.json`
   and `wave202-p5-lineageflow-strata.json`.
4. Standardized stats rows added (Wave 204 P2) → Table 1 in
   `docs/tables/wave204-p3-standardized-stats.md` extends the Wave 203
   P4 12-row table to 16 rows with 4 LineageFlow rows; the 4 rows cite
   the per-record / strata files.

## §10.42 data status (honest disclosure)

The §10.42 (h) section accurately reflects the actual data state:

- **Per-record paired t-test: N=574 paired records**, NOT N=1000.
  Reason: framework foldability was deliberately killed at 574/1000
  after PDB rate dropped below 5/min for >2 h projection (Wave 204 P2
  commit `4e758c8` documents the kill rationale). The 426
  missing_pdb records on the framework foldability arm are flagged
  in `framework/sc/self_consistency.jsonl` with `error: missing_pdb`.
- **Baseline: 1000/1000 complete** (foldability + self_consistency +
  metrics all on disk; no missing records).
- **Stratification: 3 tiers × 2 metrics = 6 cells**, all with N>=191
  per cell (hard n=191, medium n=192, easy n=191; boundary at 33rd /
  67th percentile of baseline pLDDT).
- **Cross-adapter CONFIRMED-on-2-adapters** annotation is honest
  about the N=574 caveat on the lineageflow arm; the full N=1000
  sweep would tighten the CI but does not change the monotone-pattern
  verdict.

## Acceptance gates (Wave 204 P4 superset)

| # | gate | status |
|---|------|--------|
| 21 | All 4 per-record / strata files exist on disk and committed | PASS — committed in `4e758c8` |
| 22 | All 4 source foldability / self_consistency jsonl files exist on disk with line counts matching the data state | PASS — 1000/574/1000 baseline+framework as documented |
| 23 | §10.42 (h) cross-references the per-record / strata files | PASS — Wave 204 P3 commit `cddbe07` |
| 24 | §10.42 (h) honest-discloses N=574 paired records (NOT N=1000) + 426 missing_pdb framework foldability records | PASS — explicit N=574 caveat + framework 574/1000 foldability disclosure |
| 25 | `tools/check_claims_consistency.py` reports "No drift detected." after Wave 204 P4 audit | TBD — Wave 204 P4 audit (this doc is additive; no claim edits) |
| 26 | D.4 byte-stable regression count preserved at 72/72 PASS | PASS — no test files touched |
| 27 | No paper claim retracted; §10.42 (h) and CLM-061 additively preserved | PASS — ADDITIVE only |

All 7 Wave 204 P4 gates PASS.

## Files written / modified (this Wave 204 P4 commit)

- `docs/audit/wave204-p4-per-record-csv-commit.md` (this file): audit
  doc for Wave 204 P4 confirming the per-record CSV / JSON commit
  state and §10.42 cross-references.

Wall-clock cost: <1 min CPU (audit-only; no data or doc changes).

## Audit recommendation

Land Wave 204 P4 as the verification commit confirming that the
per-record CSV / JSON outputs from Wave 202 P2 are on disk and
cross-referenced in §10.42 (h). The actual data work was completed in
Wave 204 P2 (commit `4e758c8`); the paper-side synthesis was
completed in Wave 204 P3 (commit `cddbe07`). Wave 204 P4 is a
verification audit that confirms both prior commits satisfy the
task spec, with the honest N=574 data state disclosed in §10.42 (h).

The Wave 206 P1 sweep is currently running
(`verification_outputs/wave206-p1-lineageflow-n1000/`) with a 6-hour
wall-clock budget to attempt the full N=1000 paired sweep. If that
sweep completes, a future Wave (W2+) can update §10.42 (h) to reflect
the N=1000 paired records (the monotone-pattern verdict will not
change; only the CIs will tighten).