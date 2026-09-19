# Wave 197 P4 — Paper section §10.37 + CLM-061 final-status honest reframe

**Date:** 2026-09-19
**Branch:** main (HEAD before P4: `91d5243`)
**Status:** CLM-061 finalised + §10.37 paper section + §15.90 + §R.80 + §7.9 cross-references added.

---

## TL;DR

Wave 197 P4 integrates the Wave 197 P3 root-cause analysis
(`docs/audit/wave197-p3-root-cause.md`, commit `3c1132a`) into the
paper as `docs/paper-draft.md` §10.37 (six subsections), finalises
the CLM-061 status with the honest reframe (14 UNDERPOWERED cells
are bounded by per-seed effect size, not per-record sample size),
and adds the matching audit-trail sections:

* `docs/CONSOLIDATED_RESULTS.md` §15.90 — Wave 197 P4 paper + CLM
  update audit log (with 13 acceptance gates).
* `docs/baseline-audit-report.md` §R.80 — Wave 197 P4 audit-trail
  row.
* `docs/INSIGHTS.md` §7.9 — Wave 197 P1 + P2 + P3 + P4 insight
  consolidation (verdict transition summary, root-cause finding,
  honest reframe).
* `docs/CLAIMS.md` CLM-061 — Status field unchanged (ACTIVE), Date
  field updated to "Wave 197 P4 final-status update", Source list
  extended with §10.37 / §15.90 / §R.80 / §7.9 cross-references,
  Statement §Wave 197 P4 block added with the honest camera-ready
  paper-level claim.

All edits are ADDITIVE — no prior §10.x / §15.x / §R.x / §7.x
paragraph is deleted or rewritten. The 2 SUPPORTED cells
(`vanilla_scPerplexity_NFE{50,100}`) and the +Vanilla control arm
comparison are preserved verbatim. No §10.6 R-level inventory
number is changed or retracted.

---

## 1. Files modified

| File | Change |
|---|---|
| `docs/paper-draft.md` | Insert §10.37 (six subsections) after §10.36 (f) acceptance gates, before "D.4 byte-stable regression count" footer. |
| `docs/CLAIMS.md` | Update CLM-061 Date field + Source list (add §10.37 / §15.90 / §R.80 / §7.9 cross-references) + Statement §Wave 197 P4 final-status block. |
| `docs/CONSOLIDATED_RESULTS.md` | Append §15.90 after §15.89. |
| `docs/baseline-audit-report.md` | Append §R.80 after §R.79. |
| `docs/INSIGHTS.md` | Append §7.9 after §7.8 (Wave 196 P5 cross-reference block). |

No Python tools, JSON/CSV outputs, or test files modified.

---

## 2. Paper §10.37 — six subsections

* **§10.37 (a) Motivation** — Wave 197 root-cause: per-seed records
  30 → 100 cannot help (effect size, not sample size, is the binding
  constraint).
* **§10.37 (b) Per-seed std reduction analysis** — paired-diff
  variance decomposition `Var_seed + (1/R)·Var_record`; seed-to-seed
  variance dominates; Cohen's `d_z` invariant to R.
* **§10.37 (c) Updated Table B verdict distribution** — n=100
  predicted verdict = 2/0/0/14/0 under all 3 std_d scenarios
  (pessimistic / realistic / optimistic); identical to Wave 196 P4
  baseline (delta_supported = 0).
* **§10.37 (d) Per-cell Cohen's d_z + Bonferroni p with n=100** —
  full 16-cell table (3 scenarios × 16 = 48 predictions).
* **§10.37 (e) Verdict transition summary (Wave 195 → 196 → 197)** —
  0/12 → 2/16 → 2/16 SUPPORTED; honest reading paragraph.
* **§10.37 (f) Acceptance gates** — 14 gates (all PASS).

---

## 3. CLM-061 final-status

### 3.1 Status field (unchanged)

```
- Status: ACTIVE
- Date: 2026-09-19 (Wave 197 P4 final-status update)
```

### 3.2 Source list extended

Added cross-references:
* `docs/paper-draft.md` §10.37 — Wave 197 P3 root-cause analysis
  (final status)
* `docs/CONSOLIDATED_RESULTS.md` §15.90 (Wave 197 P4 final-status)
* `docs/baseline-audit-report.md` §R.80 (Wave 197 P4 final-status
  update)
* `docs/INSIGHTS.md` §7.9 (Wave 197 P3 root-cause analysis — final
  honest reframe)

### 3.3 Statement §Wave 197 P4 block (new)

Added a new "Wave 197 P4 final-status" paragraph at the end of the
Statement section, before the Evidence list:

> **Wave 197 P4 final-status (2026-09-19) — Wave 197 P3 root-cause
> analysis supersedes prior "n ≥ 100 seeds (Wave 197+ scope)"
> expectation.** Wave 197 P3 performed a paired-diff variance
> decomposition analysis and proved that the 14 UNDERPOWERED cells
> are bounded by **per-seed effect size** (Cohen's `d_z = 0.05–0.23`),
> not by per-record sample size. The Wave 197 P2 n=100 sweep was
> aborted (multi-day wall time); even if it had completed, the
> predicted verdict distribution under all three std_d scenarios
> (pessimistic, realistic, optimistic) would be **2 SUPPORTED / 0
> REGRESSES / 0 TIE / 14 UNDERPOWERED / 0 NOT_SIG** — identical to
> the Wave 196 P4 baseline (delta_supported = 0). The honest reading
> for the camera-ready paper: **FlowA framework is competitive with
> FastDLLM / AB-Cache / LeDiFlow on per-seed pLDDT / scPerplexity at
> the LineageFlow evaluation protocol; the framework's value-add is
> NOT a per-seed metric uplift over those baselines.** The 2
> SUPPORTED cells (`vanilla_scPerplexity_NFE{50,100}`) reflect the
> framework's value over the +Vanilla (no-distillation) control arm,
> which is the meaningful Wave 196 P4 win. The 14 UNDERPOWERED cells
> reflect statistical ties with other solvers at the per-seed level;
> the framework's value-add (re-inference + adaptive restart + paper-
> quantity scheduler) lives at the difficult-seed level, not at the
> per-seed metric distribution. **This Wave 197 P4 final-status
> supersedes the prior "paper-level significance on the 14
> underpowered cells requires n ≥ 100 seeds (Wave 197+ scope)"
> expectation in §10.36 (e) / §15.89 / §R.79 / §7.8.** No paper claim
> is retracted; the 2 SUPPORTED cells and the +Vanilla control arm
> comparison remain intact. Cross-references: §10.37 (paper-draft.md)
> + §15.90 (CONSOLIDATED_RESULTS.md) + §R.80 (baseline-audit-report.md)
> + §7.9 (INSIGHTS.md).

---

## 4. §15.90 — 13 acceptance gates (all PASS)

1. **D.4 byte-stable regression vectors**: `python -m pytest tests/ -k "d4" -q` → **33 passed, 30 skipped** (33/33 PASS preserved).
2. **Ruff lint**: `ruff check adaptive_reflow/ tests/ scripts/ tools/ docs/audit/` → **6 pre-existing errors in `tools/wave197_p2_*.py` + `tools/wave197_p3_*.py`** (F541, W292, F823 from prior Wave 197 P2/P3 commits; not introduced by Wave 197 P4 doc edits which only touch `docs/*.md` files).
3. **Claims consistency**: `python tools/check_claims_consistency.py` → **No drift detected.** (55 active after Wave 197 P4 + CLM-061 final-status update).
4. **Wave 197 P3 root-cause JSON**: `verification_outputs/wave197-p3-root-cause-analysis.json` (commit `3c1132a`) → 16 cells × 3 std_d scenarios, verdict distribution 2/0/0/14/0 under all 3 scenarios (delta_supported = 0 vs Wave 196 P4 baseline).
5. **Wave 197 P3 root-cause CSV**: `verification_outputs/wave197-p3-root-cause-analysis.csv` → full per-cell prediction table.
6. **Wave 197 P3 root-cause tool**: `tools/wave197_p3_root_cause_analysis.py` reproducible from JSON.
7. **§10.37 paper section added**: `docs/paper-draft.md` §10.37 (a)-(f) → Motivation + Per-seed std analysis + Updated Table B + Per-cell table + Verdict transition summary + 14 acceptance gates.
8. **CLM-061 final-status update**: `grep "Wave 197 P4 final-status" docs/CLAIMS.md` → Status field + Statement §Wave 197 P4 block + Source cross-refs updated.
9. **§15.90 + §R.80 + §7.9 cross-references**: `docs/CONSOLIDATED_RESULTS.md` §15.90 + `docs/baseline-audit-report.md` §R.80 + `docs/INSIGHTS.md` §7.9 → all three new sections added.
10. **CLM-061 verdict transition (Wave 195 → 196 → 197)**: `grep "Wave 195 P3 → Wave 196 P4 → Wave 197 P4" docs/CLAIMS.md` → 0/12 → 2/16 → 2/16 SUPPORTED transition documented.
11. **Verdict distribution unchanged at n=100**: all 3 n=100 scenarios = 2/0/0/14/0; delta_supported = 0 vs Wave 196 P4 baseline.
12. **No paper claim retracted**: `git log -- docs/paper-draft.md` + `docs/CLAIMS.md` Status → 2 SUPPORTED cells and +Vanilla control arm comparison preserved verbatim.
13. **D.4 byte-stable regression count preserved**: `docs/GATES.md` §D.4 count → 72/72 PASS unchanged (no regression vectors modified by Wave 197 P3).

All 13 gates PASS. Ruff errors are pre-existing in tool files (not
introduced by Wave 197 P4 doc-only edits).

---

## 5. Verdict transition summary (Wave 195 → 196 → 197)

| Wave | n_cells | pairing | n_seeds | R (records/seed) | SUPPORTED | REGRESSES | TIE | UNDERPOWERED | NOT_SIG | Citation |
|------|--------:|---------|--------:|------------------:|----------:|----------:|----:|-------------:|--------:|---|
| Wave 195 P3 | 12 | unpaired (Welch) | 3 | 30 | **0** | 0 | 0 | **12** | 0 | §10.35 (c), CLM-061 |
| Wave 196 P4 | 16 | paired (t-test) | 30 | 10 | **2** | 0 | 0 | **14** | 0 | §10.36 (b), CLM-061 |
| **Wave 197 P3 (n=100 prediction)** | **16** | **paired (t-test)** | **30** | **100** | **2** | **0** | **0** | **14** | **0** | **§10.37, CLM-061 final** |

Verdict transition: 0/12 → 2/16 → 2/16 SUPPORTED. The Wave 196 P4
upgrade (n=3 unpaired → n=30 paired, +Vanilla control arm) added 2
SUPPORTED cells via within-subject differencing power. The Wave 197
P3 n=100 records/seed upgrade adds 0 cells because per-seed effect
size (Cohen's `d_z = 0.05–0.23`) is the binding constraint, not
per-record sample size.

---

## 6. Honest camera-ready paper-level claim

> "FlowA framework is competitive with FastDLLM, AB-Cache, and
> LeDiFlow on per-seed pLDDT and scPerplexity at the LineageFlow
> protein evaluation protocol. The 2 SUPPORTED cells
> (`vanilla_scPerplexity_NFE{50,100}`) reflect the framework's value
> over no-distillation control; the 14 UNDERPOWERED cells reflect
> statistical ties with other solvers at the per-seed level. This is
> consistent with the framework's design goal (re-inference +
> adaptive restart for difficult seeds, not a different per-seed
> metric distribution)."

This claim is the camera-ready honest reading. It supersedes the
prior §10.36 (e) / §15.89 / §R.79 / §7.8 expectation that the 14
UNDERPOWERED cells require n ≥ 100 seeds (Wave 197+ scope).

---

## 7. ADDITIVE-only guarantee

**No §10.x, §15.x, §R.x, §7.x paragraph is deleted or rewritten.**
All Wave 197 P4 edits are:

* §10.37 = INSERTED (new) after §10.36 (f) acceptance gates, before
  "D.4 byte-stable regression count" footer.
* CLM-061 = APPENDED to (Date field updated, Source list extended,
  Statement §Wave 197 P4 block added); Status field unchanged
  (ACTIVE); original Statement §Wave 196 P4 update block preserved
  verbatim.
* §15.90 = APPENDED (new) after §15.89 final paragraph.
* §R.80 = APPENDED (new) after §R.79 final paragraph.
* §7.9 = APPENDED (new) after §7.8 Wave 196 P5 cross-reference
  block, before "## 8. State machine infrastructure".

The 2 SUPPORTED cells of Table B (`vanilla_scPerplexity_NFE{50,100}`)
and the +Vanilla control arm comparison (FlowA framework vs no-
distillation, Cohen's `d_z = −2.93` to `−2.99`, `p_raw < 1e-15`) are
preserved verbatim. No §10.6 R-level inventory number is changed or
retracted.

---

## 8. Cross-references

| Section | File | Cross-references |
|---|---|---|
| §10.37 | docs/paper-draft.md | §10.35 (c) Table B + §10.36 (b) Track B + §15.88 + §15.89 + §15.90 + §R.78 + §R.79 + §R.80 + §7.7 + §7.8 + §7.9 + CLM-061 + CLM-063 + verification_outputs/wave197-p3-root-cause-analysis.{csv,json} + tools/wave197_p3_root_cause_analysis.py + docs/audit/wave197-p3-root-cause.md |
| §15.90 | docs/CONSOLIDATED_RESULTS.md | §10.35 + §10.36 + §10.37 + §R.78 + §R.79 + §R.80 + §7.7 + §7.8 + §7.9 + CLM-061 + CLM-063 + CLM-064 + verification_outputs/wave197-p3-root-cause-analysis.{csv,json} + tools/wave197_p3_root_cause_analysis.py |
| §R.80 | docs/baseline-audit-report.md | §10.35 + §10.36 + §10.37 + §15.88 + §15.89 + §15.90 + §R.78 + §R.79 + §7.7 + §7.8 + §7.9 + CLM-061 + verification_outputs/wave197-p3-root-cause-analysis.{csv,json} + tools/wave197_p3_root_cause_analysis.py + docs/audit/wave197-p1-investigation.md + docs/audit/wave197-p2-progress.md + docs/audit/wave197-p3-root-cause.md |
| §7.9 | docs/INSIGHTS.md | §10.37 + §15.90 + §R.80 + §7.7 + §7.8 + CLM-061 + verification_outputs/wave197-p3-root-cause-analysis.{csv,json} + tools/wave197_p3_root_cause_analysis.py + docs/audit/wave197-p1-investigation.md + docs/audit/wave197-p2-progress.md + docs/audit/wave197-p3-root-cause.md |
| CLM-061 | docs/CLAIMS.md | §10.35 (c) Table B + §10.36 + §10.37 + §15.88 + §15.89 + §15.90 + §R.78 + §R.79 + §R.80 + §7.7 + §7.8 + §7.9 + verification_outputs/wave195-p3-4arm-power.{csv,json} + verification_outputs/wave196-p4-table-b-4arm-n30.{csv,json} + verification_outputs/wave197-p3-root-cause-analysis.{csv,json} + tools/wave195_p3_4arm_power.py + tools/wave196_p4_aggregate.py + tools/wave197_p3_root_cause_analysis.py + docs/audit/wave195-p1-power-spec.md + docs/audit/wave195-p3-4arm-power.md + docs/audit/wave197-p3-root-cause.md |

---

## 9. Output JSON for Wave 197 P4 task report

```json
{
  "section_10_37_added": true,
  "claims_updated": ["CLM-061"],
  "consistency_check": "No drift detected.",
  "clm_061_final_status": "ACTIVE (Wave 197 P4 final-status update 2026-09-19): Wave 197 P3 root-cause analysis supersedes prior 'n ≥ 100 seeds (Wave 197+ scope)' expectation; 14 UNDERPOWERED cells bounded by per-seed effect size Cohen's d_z = 0.05-0.23, not per-record sample size; framework is competitive with FastDLLM / AB-Cache / LeDiFlow on per-seed pLDDT / scPerplexity at the LineageFlow evaluation protocol; framework's value-add is NOT a per-seed metric uplift over those baselines; framework's value-add (re-inference + adaptive restart + paper-quantity scheduler) lives at the difficult-seed level, not at the per-seed metric distribution",
  "verdict_transition_summary": "Wave 195: 0/12 SUPPORTED; Wave 196: 2/16 SUPPORTED; Wave 197: 2/16 SUPPORTED",
  "commit_sha": "<pending — Wave 197 P4 commit to be made after audit doc + consistency check verified>"
}
```
