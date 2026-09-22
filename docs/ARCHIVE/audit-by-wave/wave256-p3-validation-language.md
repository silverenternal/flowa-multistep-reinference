# Wave 256 P3 — DATA_PRESENTATION.md validation-language revision

**Date:** 2026-09-22
**Agent:** Wave 256 P3
**Scope:** `DATA_PRESENTATION.md` (revise data-validation language + finalize R4/R5 honest disclosure + add R2 section-level disclaimer)

## 1. Motivation / 动机

Per Wave 256 P1 R2 Kanzi paper number consistency fix (`b2662dc`), the paper §7.6.2 (CLM-073) cites `d_z = −0.0990` (deployed paired-t) as primary value-add; the +0.3927 counterfactual grid search is reported separately in §3.5 as sensitivity analysis.

This wave finalizes the data-validation language in `DATA_PRESENTATION.md` so that the document does NOT mislead readers into believing all numbers are ACTUAL MEASUREMENTS, and explicitly labels counterfactual and projected numbers.

Additionally, the original Cohen's `d_z = −2.93` (R4) and `d_z = −3.13` (R5) cited in paper §7.6.4 / §7.6.5 had no source support — those numbers are now formally REMOVED and replaced with the 2D FM ablation framework_WINS verdict.

## 2. Changes applied / 变更内容

### 2.1 §0 "Read-time metadata" + "Data integrity" language (§0 line 7)

**Before:**
> 数据校验/Data integrity: 所有数字直接读取自 verification_outputs/ 下的字节级 artifact,不可更改 / All numbers read directly from byte-addressable verification_outputs/ artifacts, immutable

**After:**
> 数据校验/Data integrity: 所有 **ACTUAL MEASUREMENTS (实测)** 数字直接读取自 verification_outputs/ 下的字节级 artifact,不可更改 (immutable);counterfactual (反事实) 和 projected (投影) 数字明确标注,例如 Wave 235 P2 grid search uplift d_z=+0.3927、Wave 216 P1 projected N=1000 paired-t p=1.07e-18. / All **ACTUAL MEASUREMENTS** are read directly from byte-addressable verification_outputs/ artifacts (immutable). Counterfactual and projected numbers are explicitly labeled as such (e.g., Wave 235 P2 grid search uplift d_z=+0.3927, Wave 216 P1 projected N=1000 paired-t p=1.07e-18).

**Reasoning:** Avoids misleading teacher / grad-student reader into believing every number is an actual measurement. Counterfactual (e.g., Wave 225 P5 Kanzi tier-aware uplift +0.0465) and projected (e.g., Wave 216 P1 R3 FlowMol3 N=1000 paired-t p=1.07e-18) numbers are explicitly labeled.

### 2.2 §2.2 R2 section-level disclaimer (new blockquote at top of §2.2)

> **Section-level disclaimer (Wave 256 P3):** **R2 has FOUR readings (deployed paired-t, counterfactual uplift, grid search best, PQ-weight-tuned); the paper §7.6.2 cites the deployed paired-t (−0.0990) as primary value-add; the +0.3927 counterfactual is sensitivity analysis only.**

**Reasoning:** R2 has four readings, and a reader skimming §2.2 might be confused. The blockquote at the top makes the four-reading structure explicit and tells the reader that the paper uses the deployed arm as primary.

### 2.3 §2.4 R4 honest-disclosure expansion (line ~131)

**Before:**
> Honest disclosure (per Wave 255 P1 re-audit): DATA_PRESENTATION.md R4 now uses the 2D FM ablation source … Original Cohen's d_z = −2.93 cited in paper §7.6.4 is REMOVED (no source supports that effect-size value) — original d_z value may need re-verification in a future wave.

**After:**
> Honest disclosure (per Wave 256 P3 — R4 honest-disclosure expansion): **Original Cohen's d_z = −2.93 cited in paper §7.6.4 is REMOVED (no source supports that effect-size value); the 2D RF SOTA TIE verdict is replaced with the 2D FM ablation framework_WINS verdict (baseline 2.85 → framework 0.62, Δ = −78.25% on R4; baseline 2.31 → framework 0.76, Δ = −67.10% on R5).** DATA_PRESENTATION.md R4 now uses the 2D FM ablation source … [rest preserved verbatim]

**Reasoning:** Bolded the headline disclosure (REMOVED + replacement) at the top of the paragraph. Reader who only skims §2.4 sees the headline; reader who reads in full gets the full historical context (2D RF SOTA Liu 2022 numbers coexisting with 2D FM ablation, both honest).

### 2.4 §2.5 R5 honest-disclosure expansion (line ~152)

**Before:**
> Honest disclosure (per Wave 255 P1 re-audit): DATA_PRESENTATION.md R5 now uses the 2D FM ablation source … Original Cohen's d_z = −3.13 cited in paper §7.6.5 is REMOVED (no source supports that effect-size value) — original d_z value may need re-verification in a future wave.

**After:**
> Honest disclosure (per Wave 256 P3 — R5 honest-disclosure expansion): **Original Cohen's d_z = −3.13 cited in paper §7.6.5 is REMOVED (no source supports that effect-size value); the 2D RF SOTA TIE verdict is replaced with the 2D FM ablation framework_WINS verdict (baseline 2.85 → framework 0.62, Δ = −78.25% on R4; baseline 2.31 → framework 0.76, Δ = −67.10% on R5).** DATA_PRESENTATION.md R5 now uses the 2D FM ablation source … [rest preserved verbatim]

**Reasoning:** Same as R4 — bolded the headline disclosure at the top.

## 3. Hard rules preserved

- **D.4 byte-stable regression:** 30/30 PASS (no source files modified, only doc-level edits)
- **mkdocs build --strict:** 0 warnings (no new doc cross-references introduced)
- **claims consistency:** no drift (no CLM-### edits)
- **No framework source code touched**
- **No Wave 242 GPU task touched**

## 4. Future work / 后续

- If a future wave re-derives the R4 / R5 d_z values via a paired-t with df ≥ 30, those numbers can be re-introduced as ACTUAL MEASUREMENTS (currently the 2D FM ablation framework_WINS verdict is at the raw-delta level only).
- R2 has FOUR readings explicitly; if any future wave produces a live-GPU paired-t with stronger effect size (Wave 255 P2 confirmed none found at that time), it would become the new primary paper §7.6.2 number.

## 5. References / 引用

- `DATA_PRESENTATION.md` (revised §0 + §2.2 + §2.4 + §2.5)
- `verification_outputs/wave218-p3-kanzi-framework-wins.json` (R2 deployed arm source)
- `verification_outputs/wave235-p2-r2-uplift.json` (R2 counterfactual grid search best cell d_z=+0.3927)
- `verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation` (R4 framework_WINS source)
- `verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_eight_gaussians` (R5 framework_WINS source)
- `docs/audit/wave255-p1-restore-r4-r5.md` (Wave 255 P1 re-audit narrative — foundation for R4/R5 disclosures)
- `docs/audit/wave255-p2-r2-re-audit.md` (Wave 255 P2 R2 re-audit — confirmed no stronger live-GPU reading found)
- Commit `b2662dc` (Wave 256 P1 R2 paper number consistency fix)
- Commit `7fbd0ab` (Wave 256 P2 paper number-source audit — every §3.3-§3.7 + §7.6 number has a source; R4/R5 d_z = -2.93 / -3.13 confirmed REMOVED)
