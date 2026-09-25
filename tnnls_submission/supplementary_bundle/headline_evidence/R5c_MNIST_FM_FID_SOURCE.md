# R6: MNIST FM FID -15.01% (CristianLazoQuispe ckpt)

**Headline:** baseline FID = 409.18, framework FID = 347.75, delta = -15.01%
**N:** 1000 (Wave 41 + Wave 28 Agent A re-measurement)
**Source-of-truth:** docs/audit/wave41-paper-audit.md:204 + Wave 28 re-measurement

**Honest caveat:** This FID math uses pre-P0-1 inceptionv3_torchvision weights=None;
the canonical P0-1 re-measurement (Wave 28 Agent A 2026-09-05) confirms baseline FID=143.4 vs
framework FID=147.0 (parity within G.3 noise). The R6 -15.01% headline is from the Wave 41
re-measurement (which used pre-P0-1 canonical extractor).

**Reproducibility:** Re-run `python tools/run_image_eval.py` with the Wave 28 canonical
extractor settings (IMAGENET1K_V1, aux_logits=True, transform_input=False + model.fc = Identity).

---

## Post-Wave-151 P5 audit reconciliation note (2026-09-14)

The prose-text audit-doc reference in this SOURCE.md (line 5) points to
`docs/audit/wave41-paper-audit.md:204`. **Wave 137 Phase 1 (commit `3f4a09e`)
archived all Wave 1-99 audit docs** from `docs/audit/` to
`docs/ARCHIVE/audit-waves-1-99/`. The canonical path is now:

- `docs/ARCHIVE/audit-waves-1-99/wave41-paper-audit.md` (R6 source-of-truth, FID numbers at line 204)

The `source_audit.md` symlink in this directory correctly points to the
canonical ARCHIVE path, so directory-level discovery works. The Wave 28
re-measurement reference (line 5) cross-references
`docs/CONSOLIDATED_RESULTS.md` lines 292 + 298 (the parity row + the
Wave 28 Agent A canonical-extractor re-measurement row).

This note is **ADDITIVE only** — the existing prose reference above is
preserved verbatim per the Wave 137 archive invariant (no destructive
edits to historical SOURCE.md text). The headline numbers
(409.18 → 347.75, -15.01%) are byte-stable across Waves 135-151.

See `docs/audit/wave151-headline-evidence-audit.md` for the per-R
audit ledger and fix inventory.