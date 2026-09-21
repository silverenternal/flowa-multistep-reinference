# Wave 256 P1 — R2 Kanzi paper number consistency fix

**Date:** 2026-09-22
**Agent:** Wave 256 P1
**Trigger:** DeepSeek review feedback (`docs/drafts/section-2-method.md` + DATA_PRESENTATION.md + paper narrative) flagged a 4× magnitude difference between R2 Kanzi +743% / d_z=+0.3927 (counterfactual) and the deployed-arm d_z=−0.0990 (direct paired-t) — a reviewer-facing inconsistency.

## Scope of fix

The R2 Kanzi section in three documents was updated to:
1. Make the deployed-arm `d_z = -0.0990` (Wave 218 P3 N=1000 paired-t) the **primary §7.6.2 R2 Kanzi value-add number**.
2. Add an **explicit disclosure paragraph** that distinguishes the deployed arm from the counterfactual grid-search reading.
3. Keep the +0.3927 counterfactual reading as a **separate §3.5 paragraph** (sensitivity analysis under counterfactual scheduler knob), NOT as the primary §7.6.2 number.

## Files updated

### 1. `docs/drafts/paper-flattened-draft.md`

**§7.6.2 added (new section).** A new `## 7 Honest disclosures (Wave 256 P1 — R2 Kanzi paper number consistency)` section was added at the end of the paper with three subsections:
- `§7.6.1 Scope and motivation` — explains the pre-Wave-256 inconsistency and the 4× magnitude difference.
- `§7.6.2 R2 Kanzi — deployed-arm primary value-add and explicit disclosure (Wave 256 P1)` — states the deployed arm `d_z = -0.0990` as the primary §7.6.2 number, adds the explicit disclosure paragraph distinguishing deployed from counterfactual (+0.3927, +0.0465, −0.396), and explains why the deployed arm is reported as primary.
- Cross-references §3.5 for the +0.3927 counterfactual paragraph and DATA_PRESENTATION.md §2.2 for the sensitivity-analysis framing.

**§3.5 R2 Kanzi counterfactual grid-search reading (separate paragraph).** A new paragraph was added to §3.5 that reports the Wave 235 P2 20-cell grid-search best cell `(easy_factor=0.0, hard_intensity=2.0)` → `d_z = +0.3927`, `p = 4.933 × 10⁻³³`, medium-effect, with explicit notation that this is a **sensitivity analysis under a counterfactual scheduler knob**, NOT the deployed-arm reading. The paragraph ends with: *"The deployed-arm primary §7.6.2 number is `d_z = -0.0990` (paired-t, N=1000, Wave 218 P3) — see §7.6.2 for the explicit disclosure paragraph and cross-reference."*

### 2. `DATA_PRESENTATION.md` §2.2

The "Honest disclosure" paragraph at the end of §2.2 was updated. The new wording starts with: *"Paper §7.6.2 cites −0.0990 (deployed paired-t) as the primary R2 value-add number. The +0.3927 counterfactual grid search is reported separately in §3.5 as a sensitivity analysis (NOT as the primary §7.6.2 number)."* Full provenance preserved: Wave 218 P3 N=1000 paired sweep, `p_raw = 1.7943 × 10⁻³`, Bonferroni-significant at α=0.05/7=0.007143, lower-is-better ⇒ framework-WINS, byte-stable Wave 127 framework `mean_rmsd_Å = 0.8798` vs Wave 88 baseline `mean_rmsd_Å = 0.9020`, Δ = −0.022 Å.

### 3. `docs/CLAIMS.md` CLM-073

The CLM-073 heading was updated from "R2 Kanzi RMSD medium-effect uplift (d_z +0.0465 → +0.3927)" to "R2 Kanzi RMSD medium-effect uplift (d_z +0.0465 → +0.3927 **counterfactual**)" to flag the counterfactual nature in the heading itself. The body of CLM-073 now opens with a Wave 256 P1 wording update paragraph that explicitly states the deployed-arm `d_z = -0.0990` is the primary §7.6.2 number and the +0.0465 → +0.3927 uplift is a sensitivity analysis in §3.5 (NOT the primary §7.6.2 number).

## What did NOT change

- **`docs/drafts/section-2-method.md`** §2.12.2 was NOT changed. The §2.12.2 section already explicitly labels the +0.3927 reading as a "counterfactual grid search" with full provenance. The R2 +0.3927 / +743% narrative remains in §2.12.2 as a §2 method-level counterfactual disclosure; the §7.6.2 paper section now clarifies that the deployed-arm primary number is d_z = −0.0990.
- **`docs/ARCHITECTURE.md`** line 1620 and **`docs/RELEASE-NOTES.md`** lines 23, 32 still reference +743% — these are historical RELEASE-NOTES entries and ARCHITECTURE narrative references that predate the Wave 256 P1 clarification; they are NOT modified in this commit.
- **All numerical values** (d_z, p-values, Bonferroni α, byte-stable framework/baseline RMSD values) are unchanged from the source-of-truth verification_outputs files.

## Provenance (real numbers only)

| Reading | Value | Source file | Status |
|---|---|---|---|
| Deployed paired-t | d_z = −0.0990, p_raw = 1.7943 × 10⁻³, N=1000 | `verification_outputs/wave218-p3-kanzi-framework-wins.json` | **PRIMARY §7.6.2 number** (deployed arm) |
| Deployed byte-stable | Wave 127 framework `mean_rmsd_Å = 0.8798` vs Wave 88 baseline `mean_rmsd_Å = 0.9020` (Δ = −0.022 Å) | `verification_outputs/kanzi_n1000_framework_inv_proj_w149_q4_2026/` | Byte-stable confirmation of deployed arm |
| Wave 225 P5 tier-aware | d_z = +0.0465, p=0.1415 (NOT Bonf-sig) | `verification_outputs/wave225-p5-kanzi-tier-aware.json` | §3.5 sensitivity analysis |
| Wave 235 P2 grid-search best | d_z = +0.3927, p=4.933 × 10⁻³³, easy_factor=0.0, hard_intensity=2.0 | `verification_outputs/wave235-p2-r2-uplift.json#best` | §3.5 sensitivity analysis |
| Wave 225 P8 PQ-weight-tuned | d_z = −0.396 (sign-flipped lower-is-better) | `verification_outputs/wave225-p8-pq-weight-tuned.json` | §3.5 sensitivity analysis |

## Audit-doc acceptance gates

- **D.4 30/30 PASS preserved.** No source code change; doc-only edits.
- **mkdocs 0 warnings preserved.** No new cross-reference failures introduced (§7.6.2 self-references the §3.5 paragraph; §3.5 cross-references §7.6.2).
- **CLAIMS consistency no drift.** CLM-073 wording updated in-place; no claim removed or added; the deployed-arm primary number (`d_z = -0.0990`) is now consistent with Table 3.2 (paper-flattened-draft.md line 245) and DATA_PRESENTATION.md §2.2.

## Reviewer-facing summary

A reviewer asking "which R2 Kanzi number is the deployed-arm value-add?" receives a single answer from §7.6.2: **d_z = −0.0990 (deployed Wave 218 P3 N=1000 paired-t, Bonferroni-significant, byte-stable)**. The +0.3927 / +743% reading from Wave 235 P2 is reported in §3.5 as a sensitivity analysis under a counterfactual scheduler knob (20-cell grid-search best cell), NOT as the primary §7.6.2 number. The 4× magnitude difference between deployed (d_z = −0.0990) and counterfactual (d_z = +0.3927) is honest and reflects different baselines (deployed Wave 218 P3 uniform vs counterfactual `easy_factor=0.0, hard_intensity=2.0` grid search); reviewers should not conflate the two readings.

## Files in this commit (Wave 256 P1)

- `docs/drafts/paper-flattened-draft.md` — added §7.6.2 + §3.5 R2 Kanzi counterfactual paragraph
- `DATA_PRESENTATION.md` — §2.2 honest disclosure paragraph updated to deployed-arm-as-primary
- `docs/CLAIMS.md` — CLM-073 heading + body updated to reflect deployed-arm-as-primary
- `docs/audit/wave256-p1-r2-paper-number-fix.md` — this audit doc

## No source code changes

This commit is doc-only. The framework source code (`adaptive_reflow/`), the scheduler (`TierAwareCodimensionSheetScheduler`), the verification outputs (`verification_outputs/wave218-p3-*`, `wave225-*`, `wave235-p2-*`), and the experiment scripts (`tools/wave218_p3_*`, `tools/wave225_*`, `tools/wave235_p2_*`) are unchanged. D.4 byte-stable regression suite 30/30 PASS preserved.
