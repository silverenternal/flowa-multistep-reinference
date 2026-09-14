# Wave 132 — Tier-1 SCI polish

**Date:** 2026-09-14
**Author:** Wave 132 Agent 4 (final close)
**Scope:** 4 atomic Phases (B + C + E by prior agents + this Phase 4 final synthesis)
**Constraint:** NO push. NO source code changes. ADDITIVE only.

> **Why this exists:** Wave 132 is the **Tier-1 SCI polish** that takes the Wave 131 ruff-0 / D.4 72/72 PASS / claims_consistency PASS / mkdocs strict EXIT=0 freeze-marker and aligns the paper submission package to the **NeurIPS camera-ready template** — section structure + references + supplementary TOC (Phase B), the four camera-ready §9-§12 sections (Phase C: Discussion + Limitations + Broader Impact + Conclusion), and a Tier-1 SCI cover_letter.md reframe (Phase E: R1-R6 explicit + byte-frozen reproducibility + scope of submission). This audit doc closes Wave 132 by Agent 4 final synthesis. **No measurement delta. No algorithm activation. No end-to-end N>=1000 framework_inv_proj sweep beyond the Wave 128 N=1000 reading already published.** The freeze-marker established by Wave 131 is preserved.

---

## Phase B ledger — NeurIPS template alignment (section structure + references + supplementary TOC)

**Commit:** `9530250` — "Wave 132 Phase B: NeurIPS template alignment (section structure + references + supplementary TOC)"

**Paper-draft.md changes (33 lines ADDITIVE):**

- Section numbering aligned to the NeurIPS camera-ready template (no renumbering; ADDITIVE bridging paragraphs that tie the existing Wave 47-110 §1-§8 sections to the NeurIPS §1-§12 pattern).
- References section header added/aligned to the NeurIPS bibliography template (preserve all existing Wave 119 references verbatim; ADDITIVE template header).
- All references preserved verbatim; no citation drop, no citation reorder beyond NeurIPS author-year order convention.

**Supplementary.md changes (22 lines ADDITIVE):**

- "NeurIPS Supplementary Template Index" added at the top of `supplementary.md` (an ADDITIVE TOC that links S1-S7 by section name + line range, matching the NeurIPS supplementary index convention).
- All existing S1-S7 content preserved verbatim; no section drop, no section reorder.

**Verdict:** the paper submission package now matches the NeurIPS camera-ready section structure (paper §1-§12 + supplementary S1-S7 + bibliography). No semantic content change; purely template alignment.

---

## Phase C ledger — Camera-ready Discussion + Limitations + Broader Impact + Conclusion sections

**Commit:** `86f011b` — "Wave 132 Phase C: Camera-ready discussion + limitations + broader impact + conclusion sections"

**Paper-draft.md changes (207 lines ADDITIVE):**

- **`§9. Discussion (camera-ready)`** — 87 lines ADDITIVE. Frames the framework's value-add against the Wave 93 R1-R6 Bonf-sig framework_improves cells, the internal composite axis improvements on all 3 Tier 3 models, and the 2.5-10x NFE speedup; cross-references CONSOLIDATED §15.15.1 12-row table.
- **`§10. Limitations (camera-ready)`** — 48 lines ADDITIVE. Honest accounting of: FlowMol3 `pb_validity_pct` -9.95pp regression (UFF-vs-xtb definitional gap in PB 0.6.5); CIFAR-10 RF at matched NFE=50 +24-31% regression (cosine ramp halves effective NFE); Kanzi `reconstruction_kabsch_rmsd_A` +0.86 Å architectural cost (framework's continuous-latent endpoint through the latent→coord bridge).
- **`§11. Broader Impact (camera-ready)`** — 24 lines ADDITIVE. Training-free inference-time control for frozen SOTA checkpoints: no additional training compute, no solver-level coupling, composes with any ODE solver; impact-positive for flow-matching researchers and practitioners.
- **`§12. Conclusion (camera-ready)`** — 40 lines ADDITIVE. Summary of framework contribution + R1-R6 Bonf-sig claims + freeze-marker reproducibility guarantee; ties to cover_letter R1-R6 narrative.

**Verdict:** the paper now has the four NeurIPS-camera-ready sections (§9-§12) that Tier-1 SCI reviewers expect. No semantic change to §1-§8 (Wave 131 §7.6 + Abstract + cover_letter reframe preserved); §9-§12 are ADDITIVE new sections.

---

## Phase E ledger — cover_letter.md Tier-1 SCI update (R1-R6 explicit + byte-frozen reproducibility + scope of submission)

**Commit:** `fac08d0` — "Wave 132 Phase E: cover_letter.md Tier-1 SCI update (R1-R6 explicit + byte-frozen reproducibility + scope of submission)"

**cover_letter.md changes (33 lines ADDITIVE):**

- R1-R6 Bonf-sig framework_improves cells made **explicit** in the cover letter (was implicit in Wave 131 §7.6 + Abstract reframe; now made explicit in the submission cover letter as the primary TL;DR claim).
- Byte-frozen reproducibility statement added: "all headline numbers are byte-stable reproducible (D.4 72/72 PASS) on the freeze-marker commit HEAD at the time of submission; ckpt SHA-256 verified for all 3 Tier 3 models."
- Scope of submission made explicit: "Tier-1 SCI submission (NeurIPS / ICML / ICLR camera-ready); target venue: NeurIPS Flow-Matching Workshop or ICLR 2027 deep-generative-models track."

**Verdict:** cover_letter.md now leads with the R1-R6 Bonf-sig framework_improves claim, the byte-frozen reproducibility guarantee, and the explicit Tier-1 SCI venue scope. ADDITIVE only — pre-Wave-132 cover_letter content preserved verbatim in the "Prior TL;DR" section.

---

## Phase 4 ledger — this final synthesis (audit doc + baseline-audit §R.21 + CONSOLIDATED §15.30)

**Commit (this commit):** "Wave 132: tier-1 polish close — audit doc + baseline R.21 + CONSOLIDATED 15.30"

**Audit-doc changes:**

- 1 NEW audit doc `docs/audit/wave132-tier1-polish.md` (this file).

**Baseline-audit-report.md changes:**

- 1 NEW §R.21 section appended after §R.20 (Wave 131).

**CONSOLIDATED_RESULTS.md changes:**

- 1 NEW §15.30 section appended after §15.29 (Wave 131).

**No source code changes.** **No experiments.** **No new measurements.** **Single atomic commit by Agent 4.**

---

## Wave 132 acceptance gates

- `pytest tests/ -k "d4" -q` → **72/72 PASS** preserved (Wave 131 freeze; Phase B/C/E only touched .md files, so D.4 is byte-stable preserved)
- `ruff check adaptive_reflow/ tests/` → **All checks passed!** (Wave 131 freeze; ruff 0 on the freeze-marker source tree preserved)
- `ruff check .` → **288 findings** (NOT a Wave 132 regression — these are pre-existing in `tools/` + `examples/` `.ipynb` cells; outside the Wave 131 freeze scope)
- `mkdocs build --strict` → **EXIT=0** (verified at Wave 132 close; 21.3 s build time)
- `python tools/check_claims_consistency.py` → **PASS** ("No drift detected." — 39 active, 0 provisional, 2 deprecated; CLM-040 forced to PROVISIONAL by `Disputed by` citation)
- All **R1-R6** source paths referenced from the cover_letter R1-R6 explicit statement → present in `docs/baseline-audit-report.md` (Wave 93 §15.15.1 12-row table) + `docs/CONSOLIDATED_RESULTS.md` §15.15.1 + paper §7.6 + this audit doc §Phase E

---

## Camera-ready deferred (UNCHANGED from Wave 131 STATUS.md)

- **mypy 988 hand-fix** — CLM-024 acknowledges; the 988 mypy errors are deferred until the next post-camera-ready wave.
- **Wan2.2 / FreqFlow / MM-FM** — PHASE-4 DEFERRED; not in scope for the Tier-1 SCI submission.
- **N=5000-50000 trajectory expansion** — deferred; the Wave 128 N=1000 framework_inv_proj reading is the canonical Tier-1 SCI measurement.
- **PB-xtb pipeline closure** — deferred; the FlowMol3 `pb_validity_pct` -9.95pp regression is documented in §10 Limitations as an UFF-vs-xtb definitional gap in PB 0.6.5, not a framework bug.
- **OmegaFold env** — LineageFlow foldability / self_consistency N=1000 deferred (OmegaFold requires Python<=3.10, not the local venv).

---

## HARD RULES honored

- **NO push** (Wave 11+ user-gated).
- **ADDITIVE only** — all 3 prior-agent commits (Phase B paper + supplementary; Phase C §9-§12; Phase E cover_letter) preserve pre-Wave-132 content; this Agent 4 final synthesis is ADDITIVE audit + appendix rows.
- **NO source code changes** — Wave 132 is a docs-only wave (paper-draft.md + supplementary.md + cover_letter.md + 2 audit-doc appends).
- **NO experiments** — no measurement delta, no algorithm activation, no new N>=1000 sweep.
- **D.4 72/72 PASS preserved** — byte-stable through Wave 132 close (verified via `pytest tests/ -k "d4" -q`).
- **ruff 0 preserved** (on adaptive_reflow/ + tests/) — Wave 131 freeze marker preserved through Wave 132 close.
- **mkdocs strict EXIT=0** — verified at Wave 132 close.
- **claims_consistency PASS** — verified at Wave 132 close.
- **Single atomic Agent 4 commit** titled "Wave 132: tier-1 polish close — audit doc + baseline R.21 + CONSOLIDATED 15.30".

---

See `docs/baseline-audit-report.md` §R.21 (Wave 132 ledger) + `docs/CONSOLIDATED_RESULTS.md` §15.30 + paper §9-§12 (Phase C) + paper §1-§8 NeurIPS template alignment (Phase B) + supplementary.md NeurIPS Supplementary Template Index (Phase B) + cover_letter.md R1-R6 explicit reframe (Phase E).

---

**Wave 149 D.4 drift fix (2026-09-14):** The historical "33/33 PASS" wording used in this document referred to the Wave 38-39 first-batch regression subset ONLY. The current authoritative D.4 count is **72/72 PASS** (33 tests in `tests/test_d4_regression_vectors.py` + 39 tests in `tests/test_adapters/test_regression_vectors.py` = 72 total, per `docs/GATES.md` §D.4 + Wave 106.C.3 standardization). The 72/72 figure includes Wave 32 batches 2/3/4 + Wave 33 batch 2/3 additions (commit `40d979c` and subsequent). This drift fix is the Wave 149 Agent 6 contribution; see `docs/audit/wave149-close.md` for the Wave 149 audit trail.
