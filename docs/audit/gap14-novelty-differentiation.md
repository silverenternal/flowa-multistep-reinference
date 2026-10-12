# GAP-14 — Novelty-differentiation paragraph (predictor–corrector / restart / training-free acceleration)

**Date:** 2026-10-12
**Increment:** GAP-14 (from `todo/SUBMISSION-GAP-CHECKLIST.md`)
**Status:** RESOLVED

---

## 1. Observed facts

1. **The manuscript surveyed the three acceleration families but did not
   differentiate at the mechanism level.** §2.1 already named solver-level
   (DPM-Solver++ [3], EDM [4], UniPC [5]), trajectory-level (Consistency Models
   [8], LCM-LoRA [9], Reflow [2]), and re-inference α-blending (Sabour et al.
   2024, Fast-DLLM [6], AB-Cache, LeDiFlow [7]) methods, and §2.2 closed with a
   one-sentence "fourth position" statement.
2. **`predictor–corrector` and the restart-sampling literature were not
   mentioned at all.** `grep -iE "predictor|corrector|Heun|Langevin"` over
   `paper-A-final.md` returned **zero** hits, even though UniPC [5] is titled
   "A Unified Predictor-Corrector Framework" and EDM [4] uses a Heun +
   Langevin corrector. The word "restart" (59 occurrences) always referred to
   FlowA's own restart blend, never to restart-sampling baselines.
3. **The `.tex` §2.1 was the same paragraph minus the closing "fourth position"
   sentence**, so the reviewer-facing PDF (built from the `.tex`) carried the
   least explicit version of the differentiation.

## 2. Interpretation

The GAP-14 acceptance criterion is that "the re-inference / restart blend
contribution is clearly distinct from existing restart / predictor-corrector /
training-free acceleration." The manuscript's family taxonomy was present, but a
reviewer could reasonably ask "isn't this just a predictor–corrector / restart
scheme with extra engineering?" — the text did not answer that directly. The
cleanest additive fix is one explicit differentiation paragraph, mirroring the
existing taxonomy and citing only the already-present reference keys.

## 3. Changes

| File | Change |
|---|---|
| `docs/drafts/paper-A-final.md` | §2.1 gains a "**Explicit differentiation from adjacent mechanisms.**" paragraph (after the three-family survey): predictor–corrector samplers act *within one trajectory* with no cross-round/outcome-conditioned feedback; trajectory-level distillation changes $v_\theta$; re-inference α-blending uses a hand-set/ramp β (discrete-token caching for Fast-DLLM; a learned prior-shift for LeDiFlow). FlowA is distinguished on three axes (frozen $v_\theta$; outcome-conditioned initial-condition blend $B_m$; convergence analysis of $G$). Additive. |
| `docs/drafts/paper-A-final.tex` | Same paragraph in LaTeX (cross-refs use the `.tex` numbering: `\S2.2`, `\S6.2`, `\S3`). |
| `docs/drafts/paper-A-final.pdf` | Rebuilt (`pdflatex` × 3, exit 0; still 11 pages). |

No metric, claim number, per-cell status label, theorem, or verdict changed.

## 4. Gates (run after the edits)

| Gate | Command | Result |
|---|---|---|
| PDF build | `pdflatex` × 3 in `docs/drafts/` | exit 0; 0 fatal errors; 0 Overfull; 11 pages |
| paragraph renders | `pdftotext paper-A-final.pdf -` | "Explicit differentiation from adjacent mechanisms" present |
| D.4 byte-stable (combined) | `python -m pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py -q` | 72 passed |
| claims consistency | `python tools/check_claims_consistency.py` | no drift |
| docs-against-code | `python tools/check_docs_against_code.py` | OK |
| mkdocs strict | `mkdocs build --strict` | exit 0 |
| readiness verifier | `python tools/verify_submission_readiness.py` | READY_WITH_SKIPS: mypy_0 |

## 5. Digests (SHA-256)

| File | Pre-edit | Post-edit |
|---|---|---|
| `docs/drafts/paper-A-final.md` | `49e8880e…` (211553 B, 25,521 words) | `9943fffbb688f7861602df9d4f1c4bd73710fd82d02e93d6bf6412526aca2a54` (213273 B, 25,763 words) |
| `docs/drafts/paper-A-final.tex` | `55e058d5…` (64156 B) | `46f1612e7091c510687af52d2b9926fbf316a1f47f7eb3be557de003ae9c3b31` (65903 B) |
| `docs/drafts/paper-A-final.pdf` | `47f6eb04…` (446788 B, 11 pp) | `747d0501cbcfc57cfad74a918fa60411aa78a26c093830f5592e1bc13662fe8c` (448382 B, 11 pp) |
| `tnnls_submission/MANIFEST.md` | `cc640412…` (73488 B) | `b61f8fb79b013db7d2837fd194c3bd12f0369fb0fa8624b98ad736fed4f49a10` (74117 B) |

**Self-referencing-SHA note.** MANIFEST row 47 displays the hash of the file
*before* the current edit (`cc640412…`, 73488 B); the post-edit actual is
`b61f8fb79b013db7d2837fd194c3bd12f0369fb0fa8624b98ad736fed4f49a10` (74117 B),
recorded here per the established convention.

## 6. Caveats

- The `.md`/`.tex` divergence is intentional and preserved: the `.md` cites
  `(§2.2, Eq. 2)` / `(§6.5)` / `(§3)`, while the `.tex` cites `(\S2.2)` /
  `(\S6.2)` / `(\S3)` per its own section numbering.
- The paragraph cites only already-present reference keys ([3]–[9]); no new
  bibliography entry was added, so the reference list is unchanged.
