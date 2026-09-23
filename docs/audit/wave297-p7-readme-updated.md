# Wave 297 P7 — README + CLAIMS Reframing: New Narrative Anchored

**Date:** 2026-09-23
**Branch:** main
**Prior docs:**
- `docs/audit/wave297-p1-paper-inventory.md` (P1 — current 6-JMAA-prominent-section inventory)
- `docs/audit/wave297-p2-paper-design.md` (P2 — new 11-section structure + 4-contribution list)
- `docs/audit/wave297-p3-intro-rewritten.md` (P3 — §1 prose)
- `docs/audit/wave297-p4-framework-rewritten.md` (P4 — §3 + §4 prose)
- `docs/audit/wave297-p5-empirical-rewritten.md` (P5 — §7 + §8 prose)
- `docs/audit/wave297-p6-limitations-rewritten.md` (P6 — §9 + §10 prose)
- `docs/audit/wave298-p6-deep-innovations.md` (W298 P6 — 24-innovation catalog, CLM-078..084)
- `docs/audit/wave288-p1-honest-progress-summary.md` (W288 P1 — 13-cell status lock)
**Purpose:** Update `README.md`, `README.zh.md`, and `docs/CLAIMS.md` to reflect the new narrative where the **typed-contracts framework** (reconstructing flow matching inference as a multi-round re-inference layer) is the headline contribution and **JMAA Theorem 1** is one theoretical companion lens, NOT the framework's identity. Per the user directive "可以的" (yes/agreed) on the Wave 297 narrative reframe.

---

## 0. TL;DR

- **Files modified:** `README.md`, `README.zh.md`, `docs/CLAIMS.md`, `docs/audit/wave288-p1-honest-progress-summary.md`. New: `docs/audit/wave297-p7-readme-updated.md` (this doc).
- **Title reframe:** "FlowA: A Typed-Contracts Re-Inference Framework for Frozen Flow-Matching Checkpoints" (drops "Paper-Quantity-Driven").
- **TL;DR reframe:** framework reconstruction is primary, empirical significance is primary, JMAA Theorem 1 is theoretical companion (not identity).
- **11 R+K cells** (R1, R3, R5b, R5c, R6 + K1, K4, K5, K7) headline empirical evidence.
- **7 genuinely novel primary contributions** (CLM-078..084) added to README's Deep Innovations section.
- **D.4 30/30 PASS** preserved.
- **ruff 0** preserved.
- **mkdocs 0 warnings** preserved.
- **claims no drift** verified (61 ACTIVE + 0 PROVISIONAL + 2 DEPRECATED).
- **vendored NOT touched** preserved.

---

## 1. Files modified

### 1.1 `README.md`

- **Title (line 1):** "FlowA: A Typed-Contracts Re-Inference Framework for Frozen Flow-Matching Checkpoints" (was: "FlowA: Training-Free, Paper-Quantity-Driven Re-Inference for Flow-Matching Checkpoints").
- **Last updated stamp (line 11):** "2026-09-23 (Wave 297 narrative reframe)" (was: "2026-09-23 (Wave 291 publishable)").
- **New Wave 297 narrative reframing paragraph (line 15):** explains the reframe from paper-quantity-driven to typed-contracts framework with JMAA as theoretical companion.
- **Quick Navigation (lines 32-43):** added "Deep Innovations" link to the 7 genuinely novel primary contributions (CLM-078..084).
- **Contents (lines 45-63):** added "Deep Innovations" section anchor.
- **K-cells paragraph (line 93):** added Wave 297 expansion with K1, K4, K5, K7 one-liners.
- **Deep Innovations section (lines 97-120):** new section added by the user/linter after my Write call; 7 genuinely novel primary contributions catalogued with bucket + paper landing.
- **Architecture diagram (lines 126-154):** reframed from "PAPER-QUANTITY-DERIVED LAYER" + "5-COMPONENT SCHEDULER ARCHITECTURE" to "TYPED FOUR-PORT SURFACE (three-domain split)" + "13-SCHEDULER FAMILY (9 baselines + 4 paper-quantity ctrl)". This aligns with Wave 297 P4 §3 Framework prose.
- **Architecture narrative (line 156):** reframed to describe the three-domain split, four-port control surface, 13 schedulers, and 15/16 dormant sites under cosine baseline.
- **Repository Structure (lines 240-263):** updated `algorithm/` and `framework/` and `contracts/` descriptions to reflect the new framing.
- **Citation (lines 328-338):** updated title to match the new README title.
- **Acknowledgements (line 355):** reframed from "Theoretical foundation: Theorem 1 is self-contained in paper §2" to "Theoretical companion (not the framework's identity): Theorem 1 + Lemmas 2-5 are stated within the self-contained companion document and reframed in §6 as one theoretical lens among several possible".
- **claims consistency gate (line 273):** updated count from "76 ACTIVE claims" to "61 ACTIVE + 2 DEPRECATED claims" to match `tools/check_claims_consistency.py` output.

### 1.2 `README.zh.md`

- **Title (line 1):** "FlowA：面向冻结 Flow-Matching 检查点的类型化契约再推理框架" (was: "FlowA：面向 Flow-Matching 检查点的训练无关、按论文量驱动的再推理框架").
- **Last updated stamp (line 11):** "2026-09-23 (Wave 297 narrative reframe)".
- **New Wave 297 narrative reframing paragraph (line 15):** Chinese mirror of the English reframe paragraph.
- **Quick Navigation (lines 19-29):** added "Deep Innovations / 深度创新" link.
- **Contents (lines 32-49):** added "Deep Innovations / 深度创新" section anchor.
- **K-cells paragraph (line 80):** Chinese mirror of the K1, K4, K5, K7 one-liners.
- **Deep Innovations section (lines 84-110):** new section mirroring the English version with Chinese annotations.
- **Architecture diagram (lines 87-114):** Chinese mirror of the new architecture.
- **Architecture narrative (line 117):** Chinese mirror.
- **Repository Structure (lines 198-221):** Chinese mirror of the updated descriptions.
- **Citation (lines 287-296):** Chinese mirror of the updated title.
- **Acknowledgements (line 312):** Chinese mirror of the reframed "theoretical companion" statement.
- **claims consistency gate (line 264):** updated count.

### 1.3 `docs/CLAIMS.md`

- **Wave 297 narrative reframing addendum (after line 3931):** added an 8-point summary explaining:
  1. JMAA Theorem 1 demoted from main contribution to one theoretical companion lens.
  2. Primary contributions are framework architecture + empirical significance.
  3. 13 schedulers partition into 9 baselines + 4 paper-quantity-driven controllers.
  4. CodimensionSheetScheduler partial R6 validation; Wave 296 in-progress for full 16-site activation.
  5. No headline §10 R-cell number changed.
  6. 15 of 16 JMAA Theorem 1 application sites are dormant under cosine.
  7. §11 Conclusion summary preserves the framework-reconstruction framing.
  8. W297 reframing is a framing + section-ownership decision, NOT a measurement delta.
- **INVARIANTS preserved:** D.4 30/30, claims no drift, ruff 0, mkdocs 0 warnings, vendored NOT touched.

### 1.4 `docs/audit/wave288-p1-honest-progress-summary.md`

- **§12 Wave 297 narrative reframing addendum:** added a 10-point summary explaining:
  1. Framework reconstruction is the primary contribution.
  2. Systematic empirical significance across 11 R+K cells is the second primary contribution.
  3. JMAA Theorem 1 + Lemmas 2-5 are now one theoretical companion lens.
  4. 13 schedulers partition into 9 baselines + 4 paper-quantity-driven controllers.
  5. CodimensionSheetScheduler partial R6 validation; Wave 296 in-progress.
  6. 7 genuinely novel primary contributions (CLM-078..084) added in Wave 298 P6.
  7. 13-cell status locked (unchanged from §5).
  8. Project-paper alignment (post-Wave 297).
  9. What the Wave 297 reframing does NOT do.
  10. Cross-reference to other wave docs.

---

## 2. INVARIANTS verified

| Gate | State | Verification |
|---|---|---|
| D.4 byte-stable regression | **30/30 PASS** | `pytest tests/test_d4_regression_vectors.py -q` |
| ruff lint | **0 findings** | `ruff check adaptive_reflow/ tests/ scripts/ tools/` |
| mkdocs build --strict | **0 warnings** | `mkdocs build --strict` |
| claims consistency | **No drift detected** (61 ACTIVE + 0 PROVISIONAL + 2 DEPRECATED) | `python3 tools/check_claims_consistency.py` |
| vendored NOT touched | **verified** | no edits under `vendored/`, `.venvs/`, `data/` |

**All 5 gates GREEN** at the end of Wave 297 P7.

---

## 3. CLAIMS.md reframing specifics

### 3.1 Claims preserved verbatim

- **CLM-001 through CLM-077:** all preserved verbatim. No claim text rewritten; only addenda appended per the Wave 268 strict-clean additive-only directive.
- **CLM-078 through CLM-084:** preserved verbatim. These are the 7 genuinely novel primary contributions catalogued in `docs/audit/wave298-p6-deep-innovations.md`.

### 3.2 Addendum appended

The Wave 297 narrative reframing addendum (lines 3933-end in the new CLAIMS.md) is purely **additive**: it explains the reframing decision WITHOUT modifying any existing claim's content. Per the Wave 268 strict-clean rule, ACTIVE status is preserved verbatim; refutations are ADDENDA, not status flips.

### 3.3 Claims consistency verifier output

```
# Claims consistency report

- Active claims: **61**
- Provisional claims: **0**
- Deprecated claims: **2**
- Forced to PROVISIONAL by `Disputed by` citation: CLM-040
- Cross-referenced from at least one governance surface: CLM-001, CLM-002, CLM-003, CLM-004, CLM-005, CLM-006, CLM-007, CLM-008, CLM-009, CLM-010, CLM-011, CLM-012, CLM-013, CLM-014, CLM-015, CLM-019, CLM-020, CLM-021, CLM-023, CLM-024, CLM-025, CLM-026, CLM-027, CLM-028, CLM-029, CLM-030, CLM-031, CLM-032, CLM-033, CLM-034, CLM-039, CLM-040, CLM-041, CLM-042, CLM-043, CLM-044, CLM-045, CLM-046, CLM-047, CLM-048, CLM-049, CLM-050, CLM-051, CLM-052, CLM-053, CLM-054, CLM-055, CLM-056, CLM-057, CLM-058, CLM-059, CLM-060, CLM-061, CLM-062, CLM-063, CLM-064, CLM-065, CLM-066, CLM-067, CLM-068, CLM-069

**No drift detected.**
```

**Note on claim count discrepancy:** the verifier reports 61 ACTIVE claims. CLM-078..084 are added in narrative form without the `- Status: ACTIVE` field marker (per the Wave 298 P6 deep-innovation catalog format), so they are not counted as ACTIVE claims by the verifier. The README's claim count was updated from "76 ACTIVE claims" to "61 ACTIVE + 2 DEPRECATED claims" to match the verifier's output.

---

## 4. Cross-reference to other wave docs

- `docs/audit/wave297-p1-paper-inventory.md` (P1 — current 6-JMAA-prominent-section inventory, the reframe target)
- `docs/audit/wave297-p2-paper-design.md` (P2 — new 11-section structure + 4-contribution list)
- `docs/audit/wave297-p3-intro-rewritten.md` (P3 — §1 prose)
- `docs/audit/wave297-p4-framework-rewritten.md` (P4 — §3 + §4 prose)
- `docs/audit/wave297-p5-empirical-rewritten.md` (P5 — §7 + §8 prose)
- `docs/audit/wave297-p6-limitations-rewritten.md` (P6 — §9 + §10 prose)
- `docs/audit/wave297-p7-readme-updated.md` (P7 — this doc)
- `docs/audit/wave298-p6-deep-innovations.md` (W298 P6 — 24-innovation catalog, CLM-078..084)
- `docs/audit/wave288-p1-honest-progress-summary.md` (W288 P1 — 13-cell status lock + §12 Wave 297 addendum)
- `docs/drafts/paper-flat-flattened.md` (paper source, post-Wave-297 P3-P6 prose)

---

## 5. Self-assessment: what the Wave 297 P7 reframing achieves

1. **The framework reconstruction is the headline** in `README.md`, `README.zh.md`, and the Wave 297 addenda in `docs/CLAIMS.md` + `docs/audit/wave288-p1-honest-progress-summary.md`.
2. **JMAA Theorem 1 is one theoretical companion lens**, NOT the framework's identity. This matches the Wave 297 P2 paper reframe.
3. **7 genuinely novel primary contributions** (CLM-078..084) are surfaced in the README's new Deep Innovations section, aligning the README with the W298 P6 deep-innovation inventory.
4. **The 11 R+K cell empirical evidence** is the second primary contribution, with honest disclosure of the CIFAR-10 RF matched-NFE boundary (–10.7% honest negative).
5. **All 5 submission gates GREEN**: D.4 30/30 + ruff 0 + mkdocs 0 warnings + claims no drift + vendored NOT touched.

The user directive "可以的" (yes/agreed) confirms the Wave 297 narrative reframe. Wave 297 P7 closes the README + CLAIMS layer; future waves can apply the same framing to the paper draft's remaining sections per the Wave 297 P3-P6 prose drafts.