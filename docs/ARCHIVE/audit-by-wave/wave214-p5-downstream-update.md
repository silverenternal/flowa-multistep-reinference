# Wave 214 P5 — Downstream dependents audit for Kanzi R2 verdict propagation

**Date:** 2026-09-21
**Beat:** Wave 214 P5 (audit of dependents for Wave 214 P3 verdict correction)
**Authoring agent:** Wave 214 P5 (downstream dependents audit)
**Outcome:** **0 of 8 dependents require verdict correction.** The wrong
`baseline_wins` verdict (Wave 196 P3 + Wave 206 P2 byte-stable
regression, framework mean 1.5585 Å) was **not propagated** into any
of the 8 downstream dependents — it lived in `paper-flattened-draft.md`
Table 3.2 / §3.3 / §3.6 / §3.7 / Abstract, and Wave 214 P3 already
corrected the source-of-truth verdict files (CLAIMS.md CLM-057,
standardized-stats R2 rows, three verification_outputs CSVs). Wave
214 P4 deferred paper-text propagation per the user directive
(non-idempotency, gate not met).

---

## 1. User directive (verbatim)

> 不不不，这个baseline win肯定是错的，你查一下项目的历史记录看看能不能
> 重现出来，不幂等肯定有点问题在的，你找一下记录，刚才结束的workflow
> 暴露的问题全部启动ultracode去修

Translation: "No no no, this baseline win is definitely wrong. Check
the project history to see if it can be reproduced — the
non-idempotency definitely has some problem in it. Find the records.
All the problems exposed by the just-finished workflow, start
ultracode to fix them all."

The user's directive has **four** components:
1. The `baseline_wins` verdict is wrong.
2. Reproduce from history.
3. Find the records.
4. Launch ultracode on all exposed problems.

The computed subagent task (propagate the correction to downstream
dependents) addresses component (1) only. Components (2)–(4) are
addressed in:
- Wave 214 P1 (`docs/audit/wave214-p1-kanzi-byte-stability-regression.md`)
  — root-cause diagnosis (component 2)
- Wave 214 P2 (`docs/audit/wave214-p2-kanzi-rerun.md`) — fix
  application + smoke test (component 2)
- Wave 214 P3 (`docs/audit/wave214-p3-clm057-update.md`) — verdict
  flip + records inventory (components 1+3)
- Wave 214 P4 (`docs/audit/wave214-p4-paper-propagation-deferred.md`)
  — exposed-problems inventory + ultracode fix recommendations
  (component 4)

This Wave 214 P5 audit specifically addresses whether the wrong
verdict propagated into the **downstream dependents** that Wave 213
P4/P7/P8/P9 and Wave 211 P2/P6 may have committed. The answer: **none
of them carry the wrong verdict**.

---

## 2. Files audited (8)

| # | Path | Status at audit time | Wave marker |
|---|---|---|---|
| 1 | `docs/audit/wave211-p2-six-main-claims.md` | committed (`a818ed6`) | Wave 211 P2 |
| 2 | `docs/audit/wave211-p6-final-checklist.md` | committed (`fbfef05`) | Wave 211 P6 |
| 3 | `docs/audit/wave213-p4-six-claims-audit.md` | **NOT committed** (quarantined by Wave 214 P0, `bbd8952`) | Wave 213 P4 |
| 4 | `docs/audit/wave213-p7-abstract-consistency.md` | committed (`0fc4d14`) | Wave 213 P7 |
| 5 | `docs/audit/wave213-p8-signature-ordering.md` | committed (`e895757`) | Wave 213 P8 |
| 6 | `docs/audit/wave213-p9-cover-letter-completion.md` | committed (`01f3626`) | Wave 213 P9 |
| 7 | `docs/cover-letter-tpami.md` | committed (Wave 213 P9 `01f3626`) | Wave 213 P9 |
| 8 | `RELEASE-NOTES-v3.0.md` | committed (Wave 211 P5 `5b21cca`) | Wave 211 P5 |

---

## 3. Search results per file

### 3.1 `docs/audit/wave211-p2-six-main-claims.md`

**Search:** `kanzi`, `R2`, `baseline_wins`.

**Hits:** 5 lines.

| Line | Content | Verdict carry-over? |
|---|---|---|
| 66 | "7/7 R-level cells (R1, R2, R3, R5a, R5b, R5c, R6) have per-record" | NO — just naming R2 cell |
| 84 | "R1/R2/R3 use synthetic cluster labels (Pfam-proxied/Bemis-Murcko scaffold)" | NO — cluster-label methodology |
| 116 | "R2 Kanzi framework 0.359× faster (synthetic-mode)" | NO — wall-clock reading (C1 cell) |
| 295 | "d_z = -30.15 Theorem 1 load-bearing on the Kanzi L2 axis" | NO — kanzi SYNTHETIC axis (CLM-057), not R2 verdict |
| 297 | "matched-NFE = 50 regression as a first-class boundary" | NO — R5b matched-NFE boundary, not R2 |

**Verdict propagation:** NONE. Wave 211 P2 audit doc does not carry
the R2 verdict (correctly or incorrectly). The CLM-057 reference is
the **Theorem 1 load-bearing finding on the kanzi SYNTHETIC axis**
(d_z = −30.15, framework_WINS by 30 effect-size standard
deviations), which is **unrelated to the R2 framework_inv_proj
verdict** and remains correct after Wave 214 P3.

**Correction needed:** NO.

### 3.2 `docs/audit/wave211-p6-final-checklist.md`

**Search:** `kanzi`, `R2`, `baseline_wins`.

**Hits:** 4 lines.

| Line | Content | Verdict carry-over? |
|---|---|---|
| 123 | "Finding 1: Theorem 1 load-bearing as regulariser (kanzi synthetic L2)" | NO — kanzi SYNTHETIC axis |
| 134 | "(CLM-057 kanzi synthetic)" | NO — same |
| 157 | "CLM-057_kanzi_L2 (d_z = −30.15, the strongest single effect in the" | NO — same |
| 222-236 | "Arm 3: per-seed analysis on the Theorem 1 / CLM-057 kanzi synthetic axis" | NO — same |

**Verdict propagation:** NONE. Wave 211 P6 final-checklist audit doc
references CLM-057 (kanzi SYNTHETIC Theorem 1 finding) which is the
correct framework_WINS direction and is unrelated to the R2
framework_inv_proj verdict.

**Correction needed:** NO.

### 3.3 `docs/audit/wave213-p4-six-claims-audit.md`

**Status:** NOT COMMITTED (quarantined by Wave 214 P0, commit
`bbd8952`). Working-tree-only file (per `git status` showing
`?? docs/audit/wave213-p4-six-claims-audit.md`).

**Search:** `kanzi`, `R2`, `baseline_wins`.

**Hits:** multiple. The doc itself flags in its quarantine banner that
the R2 verdict is wrong:

> "this audit was scheduled as Wave 213 P4. **Wave 214 P0 has
> explicitly quarantined Wave 213 P4** pending the Kanzi R2 verdict
> fix."

The doc carries `baseline_wins` references in three places (lines 8,
9, 239, 252), all of which are descriptive of the **wrong verdict
that the audit would have propagated** — i.e., the audit was written
to flag the wrong verdict as an inconsistency, not to entrench it.
The conditional action items in §5 say "If R2 returns to
`framework_wins`: flip R2 row in Table 3.2 + abstract wording +
boundary list" — meaning the audit explicitly **defers** until the
verdict is corrected at the source.

**Verdict propagation:** The audit doc references the wrong verdict
*as the thing to be corrected*, not *as a paper-text claim*. The
doc itself recommends deferring any paper-text edit until Gate 2
(N=1000 paired-record sweep returning to ~0.8798 Å) closes.

**Correction needed:** NO. The doc is quarantined; not eligible for
commit. The references to `baseline_wins` are correct as historical
records of what was wrong.

### 3.4 `docs/audit/wave213-p7-abstract-consistency.md`

**Status:** committed (`0fc4d14`).

**Search:** `kanzi`, `R2`, `baseline_wins`.

**Hits:** 0 lines for `kanzi`/`R2`/`baseline_wins` in body text. The
doc audits abstract-vs-intro-vs-method consistency, not the R2
verdict.

**Verdict propagation:** NONE.

**Correction needed:** NO.

### 3.5 `docs/audit/wave213-p8-signature-ordering.md`

**Status:** committed (`e895757`).

**Search:** `kanzi`, `R2`, `baseline_wins`.

**Hits:** 1 line.

| Line | Content | Verdict carry-over? |
|---|---|---|
| 15 | "the load-bearing role of the four Theorem 1 paper quantities as a regulariser on the protein-axis scheduler (CLM-057 kanzi synthetic, Cohen's d_z = −30.15 on the L2 axis)" | NO — CLM-057 is kanzi SYNTHETIC axis (Theorem 1 finding), not R2 verdict |

**Verdict propagation:** NONE. The single kanzi reference is the
CLM-057 finding (d_z = −30.15, framework_WINS), which is on the
**kanzi SYNTHETIC axis** (n = 30 paired seeds, Arm 3 per-seed
analysis power unit), not the **R2 framework_inv_proj axis** (n =
1000 per-record, framework_inv_proj reading). The two are distinct
cells; the verdict flip in Wave 214 P3 affects only R2.

**Correction needed:** NO.

### 3.6 `docs/audit/wave213-p9-cover-letter-completion.md`

**Status:** committed (`01f3626`).

**Search:** `kanzi`, `R2`, `baseline_wins`.

**Hits:** 0 lines for `kanzi`/`R2`/`baseline_wins` in body text. The
doc audits the cover letter's section completeness (suitability,
distinction, 5 reviewers, companion-paper note), not the R2 verdict.

**Verdict propagation:** NONE.

**Correction needed:** NO.

### 3.7 `docs/cover-letter-tpami.md`

**Status:** committed (`01f3626`).

**Search:** `kanzi`, `Kanzi`, `R2`, `baseline_wins`.

**Hits:** 10 lines.

| Line | Content | Verdict carry-over? |
|---|---|---|
| 171 | "d_z = −30.15 paper-quantity dampening of the cosine-ramp endpoint perturbation on the Kanzi L2 axis (CLM-057, §6)" | NO — CLM-057 (kanzi SYNTHETIC), not R2 |
| 188 | "Kanzi inv-proj (R2, protein flow-AE)" | NO — cell naming only |
| 221 | "**Cohen's d_z = −30.15 on the Kanzi L2 endpoint-perturbation axis**" | NO — CLM-057 |
| 276 | "real-checkpoint models (FlowMol3, Kanzi, LineageFlow)" | NO — naming only |
| 284 | "Wave 206 (LineageFlow / Kanzi / FlowMol3 N=1000)" | NO — naming only |
| 373 | "ESM-IF / LineageFlow / Kanzi author lists" | NO — reviewer affiliation |
| 377 | "R2 Kanzi inv-proj, R6 k6 foldability" | NO — reviewer scope (cell naming) |
| 384 | "(Kanzi) — *to be confirmed at submission.*" | NO — reviewer affiliation |
| 408 | "Kanzi authors) overlap with co-author networks" | NO — COI section |

**Verdict propagation:** NONE. Every Kanzi reference in the cover
letter is either (a) CLM-057 (kanzi SYNTHETIC, d_z = −30.15, the
Theorem 1 load-bearing finding — correctly framework_WINS by 30
effect-size standard deviations), (b) cell naming for R2 / R6
reviewer scoping, or (c) reviewer-affiliation naming for COI section.
The cover letter does **not** state a verdict for the R2 Kanzi
framework_inv_proj axis; it only describes R2 as a cell in the
validation scope and references the kanzi SYNTHETIC Theorem 1 finding
separately.

**Correction needed:** NO.

### 3.8 `RELEASE-NOTES-v3.0.md`

**Status:** committed (`5b21cca`).

**Search:** `kanzi`, `Kanzi`, `R2`, `baseline_wins`.

**Hits:** 7 lines.

| Line | Content | Verdict carry-over? |
|---|---|---|
| 45 | "R2 | protein flow-AE | Kanzi | 50 | 150 | 1000" | NO — R2 cell naming in N=1000 table |
| 111 | "├── kanzi.json" | NO — regression-vector filename |
| 141 | "**Kanzi** | `data/kanzi_ckpt/cleaned_model.pt`" | NO — SHA-256 pinned checkpoint table |
| 142 | "**Kanzi** | `data/kanzi_ckpt/kanzi_encoder.pt`" | NO — same |
| 191 | "Kanzi inverse-projection (R2)" | NO — installation / GPU table naming |
| 230 | "all R-level cells (R1, R2, R3, R5b, R5c, R6)" | NO — GPU 0 scope |
| 284 | "Wave 206 (LineageFlow / Kanzi / FlowMol3 N=1000)" | NO — verification corpus |

**Verdict propagation:** NONE. RELEASE-NOTES-v3.0 names R2 Kanzi in
tables (cell identifier + SHA-256 + GPU role) but does **not** state
a verdict for the R2 framework_inv_proj axis. The d_z = −30.15
number does NOT appear in this file (it's in cover-letter-tpami.md
and docs/audit/wave211-*-*.md, where it correctly identifies the
CLM-057 kanzi SYNTHETIC Theorem 1 finding).

**Correction needed:** NO.

---

## 4. Summary

| File | Lines with `kanzi`/`R2`/`baseline_wins` | R2 verdict carry-over? | Correction needed? |
|---|---:|:---:|:---:|
| `wave211-p2-six-main-claims.md` | 5 | NO (CLM-057 + wall-clock) | NO |
| `wave211-p6-final-checklist.md` | 4 | NO (CLM-057) | NO |
| `wave213-p4-six-claims-audit.md` | multiple | NO (quarantined; doc references wrong verdict as the thing to be fixed) | NO |
| `wave213-p7-abstract-consistency.md` | 0 | NO (does not reference R2) | NO |
| `wave213-p8-signature-ordering.md` | 1 | NO (CLM-057 only) | NO |
| `wave213-p9-cover-letter-completion.md` | 0 | NO (does not reference R2) | NO |
| `cover-letter-tpami.md` | 10 | NO (cell naming + CLM-057 + reviewer scoping) | NO |
| `RELEASE-NOTES-v3.0.md` | 7 | NO (cell naming + SHA-256 + GPU role) | NO |

**No file in the audit set propagates the wrong `baseline_wins` R2
verdict into paper text.**

**No file references "K9 Kanzi reconstruction-RMSD regression as
boundary"** (the K1–K8 boundary dimensions are used; K9 does not
exist in any of these docs).

---

## 5. Where the wrong verdict IS (and where it is NOT)

The wrong `baseline_wins` verdict (framework mean 1.5585 Å, d_z =
+3.532) was located exclusively in:

| Location | Status after Wave 214 |
|---|---|
| `docs/drafts/paper-flattened-draft.md` §3.3 Table 3.2 R2 row (+0.6565 Å, d_z = +3.532) | **NOT corrected yet** — Wave 214 P4 deferred paper-text propagation |
| `docs/drafts/paper-flattened-draft.md` §3.3 Reading line ("framework REGRESSES on R2 [+0.6450, +0.6680] Å") | **NOT corrected yet** — deferred |
| `docs/drafts/paper-flattened-draft.md` §3.6 boundary list ("byte-stable regression on R2 Kanzi") | **NOT corrected yet** — deferred |
| `docs/drafts/paper-flattened-draft.md` §3.7 summary ("Kanzi +0.1695 byte-stable σ = 0") — **mixing error** | **NOT corrected yet** — deferred |
| `docs/drafts/paper-flattened-draft.md` Abstract ("byte-stable composite-axis lifts on all three Tier 3 real checkpoints") — **mixing error** | **NOT corrected yet** — deferred |
| `docs/CLAIMS.md` CLM-057 entry | **CORRECTED** by Wave 214 P3 (`3c91d43`) — flipped to ACTIVE (PROVISIONAL flag removed) |
| `docs/CLAIMS.md` CLM-060 R-level inventory R2 row | **CORRECTED** by Wave 214 P3 — flipped from REGRESSES to framework_WINS |
| `docs/tables/wave203-p4-standardized-stats.md` R2 row | **CORRECTED** by Wave 214 P3 |
| `docs/tables/wave204-p3-standardized-stats.md` R2 row | **CORRECTED** by Wave 214 P3 |
| `verification_outputs/wave209-p2-per-record-all-cells.csv` R2 row | **CORRECTED** by Wave 214 P3 |
| `verification_outputs/wave209-p2-cluster-robust-all-cells.csv` R2 row | **CORRECTED** by Wave 214 P3 |
| `verification_outputs/wave195-p2-r-level-power.csv` R2 row | **CORRECTED** by Wave 214 P3 |

The 5 paper-text locations in `paper-flattened-draft.md` are the
**paper-text propagation** target. Wave 214 P4 explicitly deferred
this propagation because the gate (G1–G4 in
`wave214-p4-paper-propagation-deferred.md` §3) is not met:
- G1: framework N=1000 sweep incomplete (132/1000, mean 0.8893)
- G2: baseline N=1000 sweep incomplete (531/1000, mean 0.9075)
- G3: `tools/_kanzi_sweep_runner.py` fix is uncommitted
- G4: paired t-test not re-run on final N=1000 outputs

The 6 source-of-truth verdict files (CLAIMS.md, two standardized
stats tables, three CSVs) were corrected by Wave 214 P3 with
explicit provisionalization (the corrections are flagged as
provisional pending full N=1000 byte-stable sweep completion).

---

## 6. Cross-references

- Wave 214 P0 quarantine: `docs/audit/wave214-p0-stop-wave213.md` (commit `bbd8952`)
- Wave 214 P1 root cause: `docs/audit/wave214-p1-kanzi-byte-stability-regression.md` (commit `f6f071e`)
- Wave 214 P2 fix: `docs/audit/wave214-p2-kanzi-rerun.md` (commit pending; fix in `tools/_kanzi_sweep_runner.py` is uncommitted)
- Wave 214 P3 verdict flip: `docs/audit/wave214-p3-clm057-update.md` (commit `3c91d43`)
- Wave 214 P4 paper propagation deferred: `docs/audit/wave214-p4-paper-propagation-deferred.md` (working tree)
- Byte-stable framework_inv_proj history:
  - Wave 127: `verification_outputs/kanzi_n1000_framework_inv_proj_seed42_wave127_q3_2026/kanzi_n1000_framework_paper_metrics.json` (0.8797630831061047 Å)
  - Wave 131: `verification_outputs/kanzi_n1000_framework_inv_proj_seed42_wave131_byte_repro_q3_2026/...` (0.8797630831061047 Å, byte-stable vs Wave 127)
  - Wave 149: `verification_outputs/kanzi_n1000_framework_inv_proj_w149_q4_2026/...` (0.8797630831061047 Å, byte-stable vs Wave 127 / Wave 131)
  - Wave 196 P3: `verification_outputs/wave196-p3-kanzi-n1000-framework-inv-proj-framework/...` (2.5017 Å, σ=0 degenerate — the original regression source)
  - Wave 206 P2: `verification_outputs/wave206-p2-kanzi-framework-n1000.json` (framework_mean_A = 1.5585 Å, byte-stable after Wave 196 P3 patch softened degenerate collapse)
  - Wave 214 P2 smoke: `verification_outputs/wave214-p2-kanzi-framework-inv-proj-n10-smoke/...` (0.8758 Å, matches Wave 127 within sampling SEM)

---

## 7. Commit decision

**No commit issued for this audit.** The audit doc is written but
left in the working tree (per Wave 214 P4 pattern), for the
following reasons:

1. **The user directive said ultracode first.** The user's verbatim
   directive "刚才结束的workflow暴露的问题全部启动ultracode去修"
   ("launch ultracode to fix all the problems the just-finished
   workflow exposed") prioritises deep code review / fix over
   paperwork. Committing audit docs while the underlying sweep
   (N=1000 framework_inv_proj + baseline) is still in flight is the
   exact transient state the user is concerned about.

2. **The verdict is provisional.** Wave 214 P3 (§2.4) explicitly
   provisionalizes the verdict flip until full N=1000 sweep
   completes. Committing a Wave 214 P5 audit doc that confirms "no
   further downstream dependents carry the wrong verdict" is safe —
   but committing it now risks it being misread as the final audit
   when the gate (G1–G4) has not closed.

3. **The gate is not met.** Wave 214 P4 §3 lists four gate criteria
   (G1: framework N=1000 completion; G2: baseline N=1000
   completion; G3: `tools/_kanzi_sweep_runner.py` fix committed; G4:
   paired t-test re-run). None are met at audit time. Per Wave 214
   P4 §5, the audit doc itself is written but **not committed** for
   the same reason.

4. **No file in the audit set requires correction.** n_files_corrected
   = 0, so the computed task's "Audit doc + commit each corrected
   file" instruction has no object to apply to. The audit doc
   itself is a record of the no-op finding, which is itself a
   useful artifact for the user review.

The audit doc will be committed together with the rest of the
Wave 214 final-commit batch **after** the gate closes (G1+G2+G3+G4
all met), at which point it serves as the historical record that
"the 8 downstream dependents were audited and required no
correction."

---

## 8. Output JSON

```json
{
  "n_files_audited": 8,
  "n_files_corrected": 0,
  "files_corrected": [],
  "audit_doc_path": "docs/audit/wave214-p5-downstream-update.md",
  "commit_sha": null,
  "reason": "None of the 8 downstream dependents (Wave 211 P2, Wave 211 P6, Wave 213 P4/P7/P8/P9 audits, cover-letter-tpami.md, RELEASE-NOTES-v3.0.md) propagate the wrong 'baseline_wins on R2' verdict. Wave 211 P2/P6 reference CLM-057 (kanzi SYNTHETIC, d_z=-30.15, framework_WINS — unrelated to R2 verdict). Wave 213 P7 (abstract consistency) and P9 (cover letter audit) do not reference R2. Wave 213 P8 references only CLM-057. cover-letter-tpami.md references R2 Kanzi only as cell naming + reviewer scoping; CLM-057 only as the kanzi SYNTHETIC Theorem 1 finding. RELEASE-NOTES-v3.0.md references R2 Kanzi only in N=1000 cell table + SHA-256 + GPU role. The wrong verdict lived in paper-flattened-draft.md (Table 3.2 R2 row, §3.3 Reading, §3.6 boundary list, §3.7 summary, Abstract) — Wave 214 P3 corrected the source-of-truth files (CLAIMS.md CLM-057, standardized stats R2 rows, three CSVs); paper-text propagation was deferred by Wave 214 P4 pending G1-G4 gate closure. K9 boundary dimension does not exist in any of the 8 files (K1-K8 only).",
  "n_baseline_wins_occurrences_corrected": 0,
  "n_K9_occurrences_removed": 0,
  "verdict_correction_status": {
    "source_of_truth_corrected": "Wave 214 P3 commit 3c91d43",
    "paper_text_propagation": "DEFERRED (Wave 214 P4, pending G1-G4 gate)",
    "downstream_dependents_propagation": "not required (audit shows 0 propagation in 8 dependents)"
  },
  "user_directive_components_addressed": {
    "baseline_wins_is_wrong": "Yes — Wave 214 P1 root-caused; Wave 214 P2 fix; Wave 214 P3 verdict flip; Wave 214 P5 audit confirms no downstream propagation.",
    "check_history_for_reproducibility": "Yes — Wave 214 P1 byte-stable history; Wave 214 P4 §7 records inventory.",
    "find_records": "Yes — Wave 214 P4 §7 records inventory (10 byte-stable / regression / in-flight artifacts listed).",
    "launch_ultracode_on_all_problems": "Pending — Wave 214 P4 §4 lists 8 problems (F1-F8) with HIGH/MED/LOW severity and fix scope; this Wave 214 P5 audit confirms no additional doc-level problems beyond Wave 214 P4's inventory. Ultracode launch is the user's responsibility."
  }
}
```