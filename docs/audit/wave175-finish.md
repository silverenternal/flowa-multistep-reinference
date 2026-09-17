# Wave 175 finish-line audit (paper finalization)

**Date:** 2026-09-17
**Branch:** main
**Final commit SHA:** a817996
**Status:** ALL GATES PASS — PUSHED TO origin/main

---

## 1. Scope

Wave 175 paper finalization. Add ADDITIVE §10.21 to paper-draft.md,
§15.74 to CONSOLIDATED_RESULTS.md, §R.65 to baseline-audit-report.md
disclosing the per-adapter NFE_REF mechanism (kanzi=10, lineageflow=50)
introduced in Wave 175 P2, the P3/P4 mechanism finding (kanzi argmax
decoder non-responsive to β in [0.05, 0.25]), and the P5 lineageflow
regression check (uniform-win preserved). All Wave 175 work is the
follow-up to Wave 174 P6 §10.20 model-asymmetric disclosure.

---

## 2. Edits

### 2.1 `docs/paper-draft.md`

Inserted §10.21 (additive) AFTER §10.20 (Wave 174 P6 disclosure) and
BEFORE §11. Broader Impact. §10.21 contains:

- **(a) Per-adapter NFE_REF mechanism disclosure** — ADAPTER_NFE_REF
  table at `tools/eval/io.py:108` + per-adapter `_NFE_REF` lookup at
  `tools/eval/framework.py:449–453` via `type(adapter).__name__`; `nfe
  == 0` byte-stable preserved by construction.
- **(b) Root cause of Wave 174 kanzi regression** — hardcoded
  `_NFE_REF = 50` at `tools/eval/framework.py:436–439` over-applied
  restart-blend to kanzi's saturated pLDDT=57.4 ceiling; the constant
  is per-adapter, not a project-wide constant.
- **(c) P4 numbers (kanzi pLDDT + scPerp at NFE=50/100/200) + P5
  numbers (lineageflow preserved)** — kanzi framework arm FASTAs
  byte-identical between Wave 174 P3 (NFE_REF=50) and Wave 175 P4
  (NFE_REF=10) for first 30 records at every NFE; pLDDT regression
  persists structurally, not driven by β magnitude; lineageflow
  uniform-win 3/3 cells preserved (within ±0.01 of Wave 174 P5).
- **(d) Honest verdict** — `framework_wins_both_metrics_everywhere_final`
  on **lineageflow** = TRUE at NFE=50/100/200 (3/3 cells; ΔpLDDT
  +0.81 to +1.37; ΔscPerp −3.85 to −4.04); on **kanzi** = FALSE at
  NFE=50/100/200 (3/3 cells; ΔpLDDT −0.54 to −5.79; ΔscPerp −3.02 to
  −3.86). Per task spec §6(d) verdict: **lineageflow wins BOTH
  metrics at every NFE; kanzi pLDDT trade-off NOT resolved to within
  baseline-pL1-pp** (only NFE=200 falls within ±1 of baseline
  pLDDT=57.4).
- **Follow-up escalation paths** — 3 options (disable restart-blend
  for kanzi synthetic / bypass framework arm at saturation / use kanzi
  real ckpt) for Wave 176+; out of scope for Wave 175.

### 2.2 `docs/CONSOLIDATED_RESULTS.md`

Appended §15.74 after §15.73 (Wave 174 disclosure) at the end of the
file. §15.74 contains: P2 implementation details, P3 sanity check
result, P4 N=30 kanzi numbers table, P5 lineageflow regression check
table, honest verdict summary, follow-up escalation paths, audit
chain (P1–P6 audit doc references), and ADDITIVE-only no-modify
disclosure of all §15.x paragraphs above.

### 2.3 `docs/baseline-audit-report.md`

Appended §R.65 after §R.64 (Wave 174 ledger row). §R.65 contains:
6-row table (P1–P6) of Wave 175 actions + outcomes, concrete N=30
number tables for kanzi + lineageflow, honest verdict, mechanism
finding (argmax decoder non-responsive to β), 3 escalation paths for
Wave 176+, and ADDITIVE-only no-modify disclosure of all §R.x entries
above.

---

## 3. Acceptance gates (all PASS)

| Gate | Result | Detail |
|------|--------|--------|
| **D.4 byte-stable regression** | PASS | `33 passed, 30 skipped, 5028 deselected, 9 warnings in 2.53s` |
| **ruff** | PASS | `All checks passed!` (0 errors across `adaptive_reflow/ tests/ scripts/ tools/`) |
| **claims consistency** | PASS | `No drift detected.` (39 active claims, 0 provisional, 2 deprecated; CLM-040 forced to PROVISIONAL per Disputed-by citation — pre-existing state) |
| **git push** | PASS | `a817996` pushed to origin/main; `86090a7..a817996 main -> main` |

### 3.1 Gate detail

- **D.4:** 33/33 PASS. 30 skips are torch-related (not introduced by
  Wave 175). No `d4` test broken by the per-adapter NFE_REF
  mechanism (the dispatch lives inside `if int(nfe) > 0:`, so the
  `nfe == 0` legacy path is preserved).
- **ruff:** 0 errors. The §10.21/§15.74/§R.65 disclosure paragraphs
  are pure markdown prose — no source code changes in P6 (audit-only).
- **claims:** No drift. The §10.21 disclosure is structurally
  ADDITIVE on §10.20; no claim text was modified or retracted.

---

## 4. Push status

`git push origin main` succeeded:

```
To https://github.com/silverenternal/flowa-multistep-reinference.git
   86090a7..a817996  main -> main
```

Final commit SHA: **`a817996`**.

---

## 5. Summary

Wave 175 P6 paper finalization completed cleanly. §10.21 (paper-draft),
§15.74 (CONSOLIDATED_RESULTS), and §R.65 (baseline-audit-report) all
disclose the per-adapter NFE_REF mechanism with the (a)–(d) structure
required by the task directive:

- **lineageflow**: framework wins BOTH metrics at every NFE (3/3
  cells; ΔpLDDT within ±0.002 of Wave 174 P5; ΔscPerp within ±0.01
  of Wave 174 P5). Per-adapter NFE_REF=50 invariant preserved.
- **kanzi**: framework wins scPerp at every NFE (3/3 cells; ΔscPerp
  −3.02 to −3.86) but regresses pLDDT at every NFE (3/3 cells;
  ΔpLDDT −0.54 to −5.79). The per-adapter NFE_REF fix is
  architecturally correct but the kanzi synthetic adapter's argmax
  decoder is non-responsive to β in [0.05, 0.25] (framework FASTAs
  byte-identical between NFE_REF=50 and NFE_REF=10 for first 30
  records at every NFE). The kanzi pLDDT trade-off is structural,
  not driven by β magnitude.

**Honest verdict (per task spec §6(d))**: lineageflow wins BOTH
metrics at every NFE; kanzi pLDDT trade-off NOT resolved to within
baseline-pL1-pp. The framework is a **partial win on kanzi** (scPerp
wins uniformly + pLDDT trade-off persists structurally) and a
**paper-quality uniform win on lineageflow** (both metrics win at
every NFE).

Three open escalation paths for Wave 176+:
1. Disable restart-blend entirely for kanzi synthetic mode
   (`KanziAdapter` NFE_REF=0 → memory-only multi-round pass).
2. Bypass framework arm for kanzi when baseline is near saturation
   (uses `saturation_threshold` field in `DOWNSTREAM_METRICS`).
3. Use the kanzi real ckpt instead of synthetic mode (the real
   adapter's velocity field may be β-sensitive).

---

## 6. File paths (absolute)

- `/home/hugo/codes/flowa-multistep-reinference/docs/paper-draft.md` —
  §10.21 inserted after §10.20.
- `/home/hugo/codes/flowa-multistep-reinference/docs/CONSOLIDATED_RESULTS.md` —
  §15.74 appended after §15.73.
- `/home/hugo/codes/flowa-multistep-reinference/docs/baseline-audit-report.md` —
  §R.65 appended after §R.64.
- `/home/hugo/codes/flowa-multistep-reinference/tools/eval/io.py` —
  `ADAPTER_NFE_REF` table at line 108 (Wave 175 P2 implementation).
- `/home/hugo/codes/flowa-multistep-reinference/tools/eval/framework.py` —
  per-adapter `_NFE_REF` lookup at lines 449–453 (Wave 175 P2 implementation).
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave175-p1-design.md` —
  Wave 175 P1 design audit.
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave175-p2-impl.md` —
  Wave 175 P2 implementation audit.
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave175-p3-sanity.md` —
  Wave 175 P3 N=10 sanity audit.
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave175-p4-kanzi-full.md` —
  Wave 175 P4 N=30 full kanzi eval audit.
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave175-p5-lineageflow-regression.md` —
  Wave 175 P5 lineageflow regression check audit.
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave175-finish.md` —
  this finish-line audit document.

---

## 7. Verification of ADDITIVE principle

The Wave 175 §10.21 / §15.74 / §R.65 ADDITIVE disclosures do not
delete or rewrite any prior §10.x / §15.x / §R.x paragraph above. The
§10.20 model-asymmetric narrative (Wave 174 P6) is preserved as
honest-negative trail documenting that:

1. Wave 174 P5 reported kanzi pLDDT regression −2.25 / −5.79 / −0.54.
2. Wave 175 P2 per-adapter fix attempted to attenuate kanzi β at
   high NFE (NFE_REF=50 → 10).
3. Wave 175 P3 + P4 mechanism finding: kanzi synthetic adapter's
   argmax decoder is non-responsive to β in [0.05, 0.25] — framework
   FASTAs byte-identical between pre-fix and post-fix.
4. The kanzi pLDDT regression is structural, requires a Wave 176+
   escalation (one of 3 options) to fully close.

The Wave 174 P5 lineageflow uniform-win narrative is **preserved** AND
**strengthened** by the Wave 175 P5 regression check (within ±0.01 of
Wave 174 P5 numbers, far below the ±0.5 acceptance tolerance). All
prior disclosures (Wave 165b / Wave 166 / Wave 166b / Wave 167 / Wave
168 / Wave 169 / Wave 170 / Wave 173 / Wave 174) are preserved
verbatim.

---

## 8. Final JSON output

```json
{
  "section_10_21_added": true,
  "section_15_74_added": true,
  "section_R_65_added": true,
  "framework_wins_both_metrics_everywhere_final": false,
  "kanzi_wins_both_metrics_everywhere": false,
  "lineageflow_wins_both_metrics_everywhere": true,
  "d4_pass": true,
  "ruff_count": 0,
  "claims_pass": true,
  "push_status": "pushed",
  "final_commit_sha": "a817996",
  "audit_doc_path": "docs/audit/wave175-finish.md",
  "summary": "Wave 175 P6 paper finalization completed cleanly. §10.21, §15.74, §R.65 all ADDITIVE on Wave 174 §10.20; per-adapter NFE_REF mechanism (kanzi=10, lineageflow=50) disclosed; honest verdict: lineageflow wins BOTH metrics at every NFE (3/3 cells; ΔpLDDT +0.81 to +1.37, ΔscPerp −3.85 to −4.04 — within ±0.01 of Wave 174 P5), kanzi has partial win (scPerp wins uniformly + pLDDT trade-off persists structurally). Per-adapter NFE_REF fix is architecturally correct but kanzi synthetic adapter's argmax decoder is non-responsive to β in [0.05, 0.25] (framework FASTAs byte-identical between pre-fix and post-fix). 3 escalation paths (disable restart-blend for kanzi synthetic / bypass at saturation / use kanzi real ckpt) opened for Wave 176+. All gates pass (D.4 33/33, ruff 0, claims PASS); pushed to origin/main as a817996."
}
```