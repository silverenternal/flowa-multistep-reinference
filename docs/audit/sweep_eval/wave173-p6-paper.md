# Wave 173 P6 — Paper update + push (2026-09-17)

**Date:** 2026-09-17
**Branch:** main
**Scope:** Wave 173 P6 — APPEND `docs/paper-draft.md` §10.19 (post-fix
NFE-curve ADDITIVE disclosure superseding §10.18 on metric axis) +
`docs/CONSOLIDATED_RESULTS.md` §15.72 (Wave 173 deep fix ledger) +
`docs/baseline-audit-report.md` §R.63 (Wave 173 ledger row). All
ADDITIVE; no prior §10.x / §15.x / §R.x paragraph modified or
retracted.

---

## 1. Recap

Wave 173 P1-P5 identified two latent bugs in the framework's
NFE-handling (full audit trail in `docs/audit/wave173-kanzi-nfe-bug.md`
+ `docs/audit/wave173-restart-over-application.md`), designed +
implemented the unified NFE-adaptive restart-blend fix
(`docs/audit/wave173-fix-design.md` + `docs/audit/wave173-impl.md`,
57 net LOC across 2 files), and verified the fix empirically
(`docs/audit/wave173-p5-results.md`, N = 4 reduced sample):

- **Bug-fix verification (kanzi FASTA NFE-sensitivity): PASS.** 3 / 3
  distinct shas (pre-fix `aa190a39...` invariant → post-fix
  `317a6d83...` NFE=50, `c8698698...` NFE=100, `316a4804...`
  NFE=200).
- **scPerplexity wins everywhere (6 / 6 cells).** ΔscPerp = −1.71 to
  −2.20.
- **pLDDT partial win (4 / 6 cells).** Wins NFE ≥ 100 (+0.15 /
  +0.02); regresses NFE = 50 (−2.10) under reduced N = 4 sample.

P6 is the **paper-update + push** phase that surfaces the post-fix
results in `docs/paper-draft.md` (the camera-ready artifact),
`docs/CONSOLIDATED_RESULTS.md` (the per-wave ledger), and
`docs/baseline-audit-report.md` (the per-wave audit row).

---

## 2. What was added

### 2.1 `docs/paper-draft.md` §10.19

Section §10.19 ADDITIVE paragraph (new) immediately after §10.18:

- 12-cell post-fix NFE curve table (2 models × 3 NFEs × 2 arms) with
  actual P5 N = 4 numbers filled in.
- Bug-fix verification (3 / 3 distinct kanzi shas) + cross-model
  caveat (generator-level comparison due to single generator).
- Honest partial-win reading: `framework_wins_both_metrics_
  everywhere = false` — scPerp wins 6 / 6 cells unconditionally;
  pLDDT wins 4 / 4 cells at NFE ≥ 100 + regresses 2 / 2 cells at
  NFE = 50 under reduced N = 4 sample.
- Scope-reduction disclosure (N = 4 vs Wave 172b N = 30) +
  recommended next-step (N = 30 re-run deferred to follow-up wave).
- Supersede statement: §10.19 supersedes §10.18 on the metric axis
  (uniform-win → conditional-win narrative); the Wave 172b §10.18
  N = 30 cell values are preserved as transition footnotes in
  `docs/audit/wave173-p5-results.md` §4.

### 2.2 `docs/CONSOLIDATED_RESULTS.md` §15.72

Section §15.72 ADDITIVE paragraph (new) immediately after §15.69:

- Wave 173 deep-fix audit trail (P1-P5 references + cross-references
  to verification outputs + per-cell JSON + SHA-256 manifest).
- Honest verdict: fix's load-bearing property PASSES + scPerp
  JMAA Theorem 1 prediction PASSES + pLDDT JMAA Theorem 1
  prediction PARTIALLY PASSES under N = 4 reduced sample.
- Wave 173 acceptance gates: D.4 72/72 PASS + ruff 0 across 4 dirs +
  claims consistency `No drift detected`.
- ADDITIVE guarantee: no prior §15.x paragraph modified or
  retracted; all earlier §15.63-§15.69 + §10.x paragraphs preserved
  verbatim.

### 2.3 `docs/baseline-audit-report.md` §R.63

Section §R.63 ADDITIVE paragraph (new) immediately after §R.60:

- Per-phase Wave 173 ledger table (P1 kanzi NFE-invariance audit +
  P2 lineageflow pLDDT NFE-inversion audit + P3 unified design +
  P4 implementation + P5 empirical verification + P6 this paper-
  update entry).
- Concrete post-fix N = 4 numbers (full 12-cell table).
- Bug-fix verification (3 / 3 distinct kanzi shas).
- All gates preserved: D.4 72/72 PASS + ruff 0 across 4 dirs +
  claims consistency `No drift detected`.
- ADDITIVE guarantee: no prior §R.x entry modified or retracted.

---

## 3. Acceptance gates (Wave 173 P6 verification)

```text
$ pytest tests/ -k "regression_vectors" -q --tb=line | tail -3
72 passed, 30 skipped, 4989 deselected, 9 warnings in 45.90s
```

```text
$ ruff check adaptive_reflow/ tests/ scripts/ tools/
All checks passed!
```

```text
$ python tools/check_claims_consistency.py
**No drift detected.**
```

All gates PASS — Wave 173 P6 is docs-only (no code changes; no
claim text changes), so the gate state is identical to Wave 173 P5.

---

## 4. LOC tally

Wave 173 P6 is **docs-only** — 0 code LOC. The Wave 173 P4 LOC count
(57 net LOC added per `docs/audit/wave173-impl.md` §7) is preserved
unchanged.

Paper-edit LOC: §10.19 (~80 lines / ~3000 chars) + §15.72 (~70 lines
/ ~3500 chars) + §R.63 (~60 lines / ~2800 chars) = ~210 lines of
ADDITIVE paper-text.

---

## 5. Cross-references

- `docs/audit/wave173-kanzi-nfe-bug.md` (P1) — kanzi NFE-invariance
  bug root-cause.
- `docs/audit/wave173-restart-over-application.md` (P2) —
  lineageflow pLDDT NFE-inversion root-cause.
- `docs/audit/wave173-fix-design.md` (P3) — unified NFE-adaptive
  mechanism design.
- `docs/audit/wave173-impl.md` (P4) — implementation (57 net LOC).
- `docs/audit/wave173-p5-results.md` (P5) — empirical verification
  (N = 4 reduced sample).
- `docs/paper-draft.md` §10.19 — paper-canonical post-fix NFE-curve
  disclosure.
- `docs/CONSOLIDATED_RESULTS.md` §15.72 — Wave 173 deep-fix ledger.
- `docs/baseline-audit-report.md` §R.63 — Wave 173 ledger row.
- `verification_outputs/cross_model_real_ckpt_w173_p5_2026/` — 12
  per-cell JSONs + SHA-256 manifest.
- `docs/paper-draft.md` §10.18 (Wave 172b) — superseded on metric
  axis by §10.19; preserved verbatim as transition trail.
