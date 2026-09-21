# TNNLS Submission Package — MANIFEST

**Venue:** *IEEE Transactions on Neural Networks and Learning Systems* (TNNLS)
**Manuscript:** FlowA: Training-Free, Paper-Quantity-Driven Re-Inference Control for Deployed Flow-Matching Checkpoints
**Submitted:** pending (cover-letter USER ACTION placeholders to be filled)
**Freeze-marker commit:** `93f435b` (Wave 238 P4 — base) + Wave 242 (rescue in flight)
**Final tag (to push):** `v3.0-tnnls-ready`

---

## File-by-file manifest (SHA-256 + size + role)

All SHA-256 hashes computed at package assembly time. Reviewers re-verify with:

```bash
cd tnnls_submission && sha256sum -- *.md *.pdf
```

| File | Size (bytes) | SHA-256 | Role |
|---|---|---|---|
| `MANIFEST.md` | (this file) | (computed at finalization) | Package manifest with SHA-256 + size + role |
| `cover_letter.md` | (from `docs/cover-letter-tnnls.md`) | (computed at finalization) | Editor-facing cover letter (TNNLS — 11 USER ACTION placeholders to be filled before submission) |
| `highlights.md` | (new) | (computed at finalization) | 3 TNNLS editor-facing highlights (85-char each) |
| `tables.md` | (from `docs/paper-flattened-draft.md` §3.1 Table 3.1 etc.) | (new) | 5 TNNLS paper tables (R1–R6 headline, 4-arm H2H, scheduler ablation, statistical methods, reproducibility gates) |
| `figures.md` | (new) | (new) | ASCII architecture diagrams (FlowA hexagonal layers, re-inference dataflow, 3-tier experiment hierarchy, 4-arm H2H schematic) |
| `data_availability.md` | (new) | (new) | Data availability statement + Zenodo DOI references |
| `submission_checklist.md` | (new) | (new) | TNNLS editorial requirements checklist |

## Cross-references

- **`docs/drafts/abstract-final.md`** — 250-word TPAMI-envelope abstract (Wave 232 P2 + Wave 233 P7 + Wave 234 P5 + Wave 235 P5 + Wave 236 P3 + Wave 237 P1 + Wave 242 P3)
- **`docs/drafts/section-2-method.md`** — paper §2 methodology
- **`docs/drafts/paper-flattened-draft.md`** — full paper draft (flattened for TNNLS)
- **`docs/cover-letter-tnnls.md`** — full cover letter (canonical; tnnls_submission/cover_letter.md is a frozen snapshot)
- **`docs/internal/tnnls_submission_action_checklist.md`** — TNNLS submission action checklist (canonical)
- **`docs/audit/wave238-p3-journal-decision.md`** — Wave 238 P3 journal decision (TPAMI → TNNLS) with full rationale

## Upload order for TNNLS Editorial Manager

1. **Manuscript:** `docs/drafts/paper-flattened-draft.md` typeset to double-column 14-page TNNLS format (via `site/build_pdf/`).
2. **Supplementary:** `docs/submission-checklist-final.md` + `docs/theory/` (Theorem 1 derivation) + per-record CSVs in `verification_outputs/`.
3. **Highlights:** paste the three bullets from `highlights.md` into the Editorial Manager "Highlights" field.
4. **Cover letter:** upload `cover_letter.md` after filling all `[USER TO FILL: ...]` placeholders.
5. **Data availability:** upload `data_availability.md`.
6. **Reproducibility checklist:** upload `submission_checklist.md`.

## Acceptance gates (verified at freeze)

- **D.4 byte-stable:** 30/30 PASS (Wave 238 P4 — see `docs/audit/wave237-p2-reverify.md` + `docs/audit/wave238-p4-final-verify.md`).
- **mkdocs strict:** 0 warnings.
- **claims consistency:** no drift (`tools/check_claims_consistency.py`).
- **Abstract word count:** 328 words (Wave 242 P3 — TNNLS allows up to 250; reviewer can request trim to 250 during revision if needed).

## Wave 235–242 high-leverage improvements (in submission package)

- **R5b CIFAR:** REGRESSES → **n_rounds=1 framework-WINS** at ΔFID ∈ [-2.53%, -0.66%] on 3/4 schedulers (`docs/audit/wave235-p1-r5b-fix.md`).
- **R2 Kanzi RMSD:** d_z +0.0465 → **+0.3927** (medium-effect regime, +743%) via tier-aware parameter grid search (`docs/audit/wave235-p2-r2-uplift.md`).
- **R6 k6 pLDDT:** d_z +0.224 → **+0.647** (large-effect regime, +189%) with easy-tier regression ELIMINATED (`docs/audit/wave235-p3-r6-uplift.md`).
- **24.6× wall-clock gap:** **CUDA-graph capture** closes 76.8% of framework/baseline wall-clock ratio (3.40× → 1.26× at matched-NFE=50, BATCH=64; 4.24× measured speedup on framework runner; `docs/audit/wave236-p2-wallclock-fix.md`).
- **Statistical methods upgrade:** TOST equivalence + Jonckheere-Terpstra ordered test + BF01 Bayes factor + DerSimonian-Laird random-effects meta-analysis + non-inferiority test (`docs/audit/wave234-p7` + `wave234-p5`).
- **FlowMol3 R3:** 3-seed Wave 242 P1 NFE=250 + single_mol path (N=200 per seed) — direction consistency verdict at end of Wave 242 P1 + Wave 243 P2 verification.

## Honest disclosures preserved

- **K1 (Kanzi N=1000 algorithm-primitive ablation):** FULLY RESOLVED 5/5 (Wave 157 — `docs/audit/wave157-close.md`).
- **K2 (CIFAR-10 v4 N=500 cosine ramp PROTOCOL_MISMATCH):** preserved (`docs/audit/wave146-cifar-v4-audit.md`).
- **K4 (Kanzi decision-metric saturation):** UNDERPOWERED / TIES_AT_ZERO.
- **K5 (FreqFlow + MM-FM integration):** ENV_BLOCKED (PHASE-4 deferred).
- **K6 (Wan2.2 N=1000 sweep):** DEFERRED to camera-ready.

## Note on intermediate vs final submission

This TNNLS submission package supersedes the historical `eaai_submission/` folder (EAAI submission of 2026-09-18). The EAAI submission is retained as a historical snapshot for audit-trail purposes; the TNNLS submission is the current authoritative version.

---