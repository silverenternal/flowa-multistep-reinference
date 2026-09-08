# Wave 94 (W5) — ICLR 2027 submission package

**Date:** 2026-09-09
**Status:** PLANNED (1 agent, ~2-3h wall-clock, single commit)
**Final step:** ship paper to venue
**Depends on:** Wave 91 + Wave 93 (Wave 92 optional)
**Blocks:** submission

> **Why this matters:** All technical work (W1-W4 close) is done. Wave 94 ships a submission-ready package: anonymized cover letter, final paper §1 abstract, final §7 Tier 3 section, supplementary material with all 3 model audit docs, reproducibility checklist.

---

## 1. Goal

Produce a venue-ready submission package:
1. **Cover letter** (anonymized for double-blind if ICLR main track)
2. **Final paper §1 abstract** (single-paragraph TL;DR)
3. **Final paper §7** (Tier 3 paper-metric section with W93 honest verdict)
4. **Supplementary material** (3 model audit docs + reproducibility checklist)
5. **Submission checklist** (one-pager confirming G1-G4 reviewer-proof guarantees)

---

## 2. Constraints

- **CPU-only** (paper editing; no compute)
- **Single commit** + audit doc
- **D.4 unchanged** (paper-only; no code changes)
- **NO push**
- **Anonymization** — strip author names, institution, ack section for double-blind

---

## 3. Phase 1 — Author cover letter (~30 min)

### File: `cover_letter.md` (NEW, top-level)

### Structure
1. **TL;DR** (3 sentences): framework contribution + key result + evidence quality
2. **Why this fits {venue}** (1 paragraph): scope / rigor / impact match
3. **4 reviewer-proof guarantees** (1 paragraph each):
   - G1: SHA-256 ckpt verification (link to `verification_outputs/ckpt_sha256.json`)
   - G2: upstream default sampling config (cite Wave 75/76/77 audit docs)
   - G3: zero LOC metric code (cite Wave 75-89 paper-metrics tool)
   - G4: vendored upstream snapshot frozen (cite vendored commit hashes)
4. **Honest limitations** (1 paragraph): N=1000 vs N=5000, framework TIE on 6/12 cells, paper-metric mixed result
5. **Comparison to concurrent work** (1 paragraph): how this differs from {2-3 known papers}
6. **Reproducibility statement** (1 paragraph): vendored deps, vendored ckpts, 220+ commits, D.4 33/33 byte-stable

### Length: ~1 page (600-800 words)

---

## 4. Phase 2 — Final paper §1 abstract (~30 min)

### Update: `docs/paper-draft.md` §1 abstract (REPLACE existing)

### Target: 200 words, single paragraph

### Structure
1. **Sentence 1** (problem): inference-time refinement for flow matching is under-explored
2. **Sentence 2** (gap): no principled framework with convergence guarantees
3. **Sentence 3** (contribution): FlowA — restart-blend loop with JMAA Theorem 1
4. **Sentence 4** (rate bound): BL ≤ √(2/π)·ε
5. **Sentence 5** (Tier 1 evidence): 4 toy benchmarks show framework value
6. **Sentence 6** (Tier 3 evidence): 3 SOTA chemistry / protein models, framework wins on 4/12 cells with statistical significance, TIE on 6, no regression on any
7. **Sentence 7** (reproducibility): vendored upstream eval + ckpt SHA-256 + 220+ commits
8. **Sentence 8** (impact): drops in anywhere flow-matching inference is used

---

## 5. Phase 3 — Final paper §7 Tier 3 (~60 min)

### Update: `docs/paper-draft.md` §7.3 / §7.4 / §7.5 / §7.6 (REPLACE Wave 89 wording)

### §7.3 Kanzi
- Wave 91 numbers (6 metrics + verdict per cell)
- Honest caveat: FSQ noise floor on reconstruction_kabsch_rmsd_A

### §7.4 LineageFlow
- Wave 81/92 numbers (4 metrics + verdict)
- Honest caveat: HMMER Pfam version dependency

### §7.5 FlowMol3
- Wave 82/87/90 numbers (4 metrics + verdict)
- Honest caveat: PB-xtb xtb version dependency

### §7.6 Honest verdict (REPLACE per Wave 93 reframe)
- Per-cell 12-row table (or 14 if Kanzi has 6 metrics)
- Bonferroni-corrected p-values
- Post-hoc power per cell
- SUPPORTED / TIE / UNDERPOWERED verdicts
- Final summary: "framework improves 4 cells (Bonferroni p<0.05), ties 6 cells within N=1000 noise floor, no measured regression, 2 cells underpowered (recommend N=5000)"

---

## 6. Phase 4 — Supplementary material (~45 min)

### File: `supplementary.md` (NEW)

### Sections
1. **S1: Theory details** — JMAA Theorem 1 full proof + Lemmas 2-5
2. **S2: Tier 1 toy benchmarks** — 2D Two Moons + CIFAR-10 + MNIST FM details
3. **S3: Kanzi audit** — full Wave 91 audit doc (`docs/audit/wave91-phase5-final.md`)
4. **S4: LineageFlow audit** — full Wave 81 + 92 audit docs
5. **S5: FlowMol3 audit** — full Wave 82 + 87 + 90 audit docs
6. **S6: Reproducibility** — `verification_outputs/ckpt_sha256.json`, vendored commit hashes, D.4 33/33, G-MASTER 7/7
7. **S7: Statistical methodology** — Wave 93 power analysis details

---

## 7. Phase 5 — Submission checklist (~15 min)

### File: `submission_checklist.md` (NEW)

### One-pager confirming:
- [ ] Paper ≤ 9 pages (ICLR limit) excluding refs + supplementary
- [ ] Cover letter ≤ 1 page
- [ ] All 4 reviewer-proof guarantees documented
- [ ] All 12 (model, paper_metric) cells reported with CI + verdict
- [ ] D.4 byte-stable 33/33 PASS
- [ ] G-MASTER 7/7 PASS
- [ ] mkdocs build --strict EXIT=0
- [ ] Anonymized (no author/institution/ack)
- [ ] Supplementary linked
- [ ] Code release URL (HF / GitHub) ready

---

## 8. Phase 6 — Author audit doc + commit (~30 min)

### `docs/audit/wave94-phase6-final.md`

Sections:
1. Final submission package inventory (cover letter + paper + supplementary + checklist)
2. Per-section summary (what changed from Wave 89)
3. Submission deadline / venue status
4. D.4 + G-MASTER + mkdocs verify
5. User next steps: choose venue + push + submit

### Verify
- All 5 files exist + cross-link
- D.4 byte-stable (no code change)
- G-MASTER 7/7
- mkdocs build --strict EXIT=0

### Commit (single, NO push)
**Title:** "Wave 94: ICLR 2027 submission package — cover letter + paper §1/§7 final + supplementary + checklist"

---

## 9. Time budget

- Phase 1 (cover letter): 30 min
- Phase 2 (§1 abstract): 30 min
- Phase 3 (§7 Tier 3): 60 min
- Phase 4 (supplementary): 45 min
- Phase 5 (checklist): 15 min
- Phase 6 (audit + commit): 30 min
- **Total: 3.5-4 hours wall-clock** (CPU-only)

---

## 10. Venue decision (user)

Recommended (per 2026-09-09 analysis):
- **NeurIPS 2026 workshop on Flow Matching**: deadline 2026-09-25, 90%+ accept, no anonymization required
- **ICLR 2027 main track**: deadline 2026-09-?? (TBD), 50-80% accept depending on package, requires anonymization

User picks one or both. Wave 94 produces both formats.

---

## 11. Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Paper > 9 pages after §7 update | P1 | Trim §5 Discussion; move Tier 3 details to supplementary |
| Anonymization leaks (commit author info, etc.) | P1 | Strip git config; use `--anonymize` flag for paper build |
| Missing deadline | P1 | Wave 94 starts immediately after Wave 93; user must approve submit |
| Reviewer attacks §7.6 mixed result | P1 | Wave 93 power analysis pre-empts this; honest narrative |

---

## 12. Open questions

1. **Which venue first?** — User decides (workshop vs main track)
2. **Co-authors for submission?** — User adds (currently single-author by Claude Code)
3. **Code release URL** — User creates / provides (HF or GitHub)
4. **Should we use OpenReview or venue-specific system?** — User handles

---

## 13. Cross-references

- Wave 91 / 92 / 93 plans: `todo/planned/w{2,3,4}-*.md`
- Wave 89 final synthesis: `docs/audit/wave89-phase1-final.md` (what §7.6 currently says)
- Cover letter template (if exists): TBD
- Submission template (if exists): TBD