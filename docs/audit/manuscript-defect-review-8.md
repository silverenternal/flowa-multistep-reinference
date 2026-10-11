# Manuscript defect review #8 — eighth consistency sweep

**Date:** 2026-10-12
**Scope:** Eighth reviewer-facing defect sweep across `docs/drafts/paper-A-final.md` (canonical markdown reading copy) + the submission SHA ledger. This pass closes the two remaining `.md`-only deferred items (**D2** and **D3**) recorded in `docs/audit/manuscript-defect-review-6.md` §4 / `manuscript-defect-review-7.md` §4 and the `SUBMISSION_READINESS.md` §16/§17 "Documented-not-fixed" notes.
**Status:** COMPLETE — 2 deferred items fixed (**`.md`-only**); the `.tex` / PDF are **byte-identical**; ledger SHAs + word count refreshed; 1 item remains reviewed-and-documented (the `(Wave NNN …)` heading labels, D1). **No metric / claim number changed; no status label moved.**

---

## 1. Observed facts (defects + fixes)

Both fixes are in the `.md` reading copy only; the `.tex` build carries neither §6.1's stray heading nor §8.10 (which is a `.md`-only subsection).

| # | Defect | Fix |
|---|---|---|
| D2 | **Stray unnumbered heading.** §6.1 (Framework Properties) carried an unnumbered `### Three formal properties` heading — a section break in the middle of the prose that introduced no navigable subsection (the three properties are enumerated inline in the immediately following paragraph) and was the **only** unnumbered non-back-matter heading in the manuscript. | Removed the heading and merged its text into the paragraph as a bold lead-in: `**Three formal properties.** This section establishes three formal properties of the typed-contracts framework: (i) …` (`.md:436`). §6.1 now flows as a single unit under its numbered heading. |
| D3 | **Stale honest-disclosure item naming a non-existent artifact.** §8.10's first honest-disclosure item read "**`paper.pdf` NOT regenerated post-Wave 356 P1.** … The compiled `paper.pdf` reflects the §7/§8/§9/§10 prose as of Wave 356 P1; regenerating the PDF is held until the user-gated next release …". Two problems: (a) `docs/drafts/paper.pdf` does not exist — the compiled manuscript is `docs/drafts/paper-A-final.pdf`; (b) the PDF **has** been rebuilt since Wave 356 (Wave 384 retitle, Wave 385 two-figure addendum, and the 2026-10-12 consistency sweeps), so the "NOT regenerated" present-tense claim was stale. | Rewrote the item as "**PDF regeneration status (corrected 2026-10-12).**", retained the additive-history enumeration (Wave 356 P2 … Wave 366 P2), and added an explicit `**Correction:**` note that the earlier `paper.pdf` phrasing was inaccurate and that the manuscript is `paper-A-final.pdf`, rebuilt several times since Wave 356. §8.10 remains a `.md`-only subsection not carried into the `.tex` build (`.md:765`). |

## 2. Evidence

- Manuscript SHA (this pass): `sha256sum docs/drafts/paper-A-final.md` → `d83e283bb5467459caa235067f190e203984e716f8c4efaa61664d43a7f0f52a` (212082 bytes, 25576 words; the pass-#6 reading was `9613cb01…` / 211903 bytes / 25564 words). `.tex` → `55e058d5f446a9ea013002a9da13d67369d903cfb65df1e65ef125ea47fda807` (64156 bytes, **unchanged** — pass #8 touched no `.tex` content). `.pdf` → `47f6eb0418d041b0dccdba68bcdf8b794c02e8a710368a8eaebe5e17f89ca732` (446788 bytes, **11 pages, unchanged** — §6.1 and §8.10 are `.md`-only, so the `.tex` build hence the PDF is byte-identical).
- **D2 ground truth:** a fence-aware heading scan of the `.md` reports **no** unnumbered non-back-matter headings after the fix; before the fix `### Three formal properties` was the sole entry. The `**Three formal properties.**` bold lead-in appears once (`.md:436`).
- **D3 ground truth:** `grep -c "NOT regenerated post-Wave 356"` → **1**, and that single occurrence is inside the new `**Correction:**` sentence that *quotes* the retired phrasing (the claim itself no longer stands). `grep -n "paper-A-final.pdf"` confirms the corrected artifact name; `grep -n "PDF regeneration status"` → 1 (`.md:765`).
- **Ledger refresh:** the `.md` SHA `9613cb01…` → `d83e283b…` (size 211903 → 212082) in `README.md` (5 sites) / `README.zh.md` (5 sites) / `todo/STATUS.md` (1) / `todo/WAVES.md` (1) / `tnnls_submission/MANIFEST.md` (md rows ×2 + the `.tex` row's embedded md cross-ref ×1). The word-count metadata `25,564` → `25,576` in `README.md` (2) / `README.zh.md` (2). `docs/README.md` and `todo/INDEX.md` pin only the (unchanged) PDF SHA — no edit. The `.tex` / `.pdf` SHAs are unchanged, so their ledger rows are untouched.
- **MANIFEST post-edit SHA:** `e9928c933daac08cef810067329c39958090fd5a6f93e13e970160dd52770ec1` (72445 bytes). The MANIFEST self-row retains the pre-edit reading per the self-referencing-SHA convention; this audit pins the post-edit value. `SUBMISSION_READINESS.md` post-edit SHA: `15e9cacb3b43884f63326dd5824bede9086d520358120a5437ed20c0b6d5d3c6` (47031 bytes). `submission_checklist.md` post-edit SHA: `218dd9d135fe1d50d93df0017c9901dbbe2c61c1e4d00d44e6650103e400165b` (34139 bytes).

### 2.1 Gate results (acceptance record)

| Gate | Command | Result |
|---|---|---|
| claims consistency | `python3 tools/check_claims_consistency.py` | **PASS** — "No drift detected" |
| docs-against-code | `python3 tools/check_docs_against_code.py` | **PASS** — "OK: 4142 claims verified" |
| ruff | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **PASS** — "All checks passed!" |
| D.4 byte-stable regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **PASS** — 30 passed |
| D.4 (verifier two-file gate) | `tools/verify_submission_readiness.py` gate `d4_72` | **PASS** — 72 passed, 0 failed |
| mkdocs strict | `mkdocs build --strict` | **PASS** — exit 0, zero nav/link warnings |
| mypy strict | `.venvs/flowmol3_venv/bin/python -m mypy adaptive_reflow` | **KNOWN-RED (pre-existing)** — 39 errors in adapter files; environment-dependent and **not touched by this docs-only pass**. Acknowledged in CLM-024. |
| readiness verifier (informational) | `tools/verify_submission_readiness.py` | **NOT_READY** — see §2.2 (two pre-existing failures, both outside this pass's file set) |

### 2.2 Readiness-verifier note

`tools/verify_submission_readiness.py` reports **NOT_READY** on two gates — `k1_rc5` ("K1 §10.4 wording missing sentinel phrases: only RC5") and `drift_33` ("148 unintended 33/33 occurrences"). Both are **pre-existing and entirely outside this pass's file set**:

- `k1_rc5` inspects `docs/paper-draft.md` (the verifier's canonical draft; `verify_submission_readiness.py:117`), **not** `docs/drafts/paper-A-final.md`.
- `drift_33` inspects `docs/audit/engineering/*.md` (e.g. `impl.md:217`, `p5-gates.md:14`).

This pass touched neither `docs/paper-draft.md` nor `docs/audit/engineering/`, and `git diff | grep -c "33/33"` → **0**. All seven other verifier gates are green (`d4_72` OK, `ruff_0` OK, `claims_pass` OK, `paper_warns` OK — 1 warning ≤ 10 budget, `r1_r6_sha` OK — 10/10, `framework_n1000` OK — 2/2; `mypy_0` SKIP — mypy absent from the verifier's sandbox PATH, run separately above). These two failures are recorded here as observed facts, not fixed (they are outside the manuscript-defect scope of this pass).

**Full-suite sweep:** a bare `PYTHONPATH=. pytest tests/ -m "not slow and not benchmark"` was started but did not terminate within ~27 min in this sandbox; it was stopped. The canonical pytest scope for these consistency passes is the D.4 regression gate (30/30 for the single file, 72/72 for the verifier's two-file gate), which is green. The README (`README.md:307`) already documents that the full-suite run is env/ordering-dependent in this environment (25 failed / 5166 passed / 145 skipped / 16 errors), so it is not treated as a reproducible gate. A bare `pytest` from the repo root additionally collects the stray `tools/w196_p3_kanzi_debug_test.py` debug script (filename matches `*_test.py`) and aborts collection — also pre-existing and unrelated (no `tools/` or `tests/` file was modified).

## 3. Interpretation

- D2 is a **structure** defect: an unnumbered heading mid-section introduced a phantom navigation target and broke the §6.1 prose into two blocks. Folding it into a bold lead-in keeps the section a single navigable unit while preserving the exact wording.
- D3 is an **honesty / accuracy** defect: a reproducibility-disclosure item named an artifact (`paper.pdf`) that does not exist and asserted a stale "not regenerated" status. The rewrite keeps the disclosure honest (it now points at the real `paper-A-final.pdf` and states that it *has* been rebuilt) while preserving the additive-provenance enumeration, so the frozen Wave-366-P2 block's intent is intact.

## 4. Unresolved gaps / caveats

- **D1 — `(Wave NNN …)` provenance labels in `.md` headings — reviewed, not changed.** Several `.md` headings carry internal wave-provenance labels (§3.4.2, §3.5.1, §7.8.1, §8.10, §9.4, §9.4.1, Bibliography). These are part of the documented intentional `.md`/`.tex` divergence — the authoritative `.tex`/PDF headings are clean, and the wave labels are referenced by the MANIFEST and the audit trail — so they are recorded rather than stripped. See `docs/audit/manuscript-defect-review-6.md` §4.
- **`.tex`/`.md` structural re-sync (A2)** remains deferred (the `.tex` is a condensed IEEEtran build with no §8.10 / §9 `L1`–`L8` / §10.3 / §7.8.1 subsections). Not a defect — intentionally different builds.
- **R5a ledger-level provenance (C1 / F6)** remains deferred (ledger-wide, not a manuscript defect).
- The historical records — `docs/audit/manuscript-defect-review{,-2,-3,-4,-5,-6,-7}.md`, the MANIFEST pass-#2…#7 blockquotes, and the SUBMISSION_READINESS §12–§17 addenda — retain the superseded `8315f67e…` / `f3d7b9fb…` / `33d3a771…` / `9e40bf68…` / `8323488f…` / `25f256bc…` / `ce0f0461…` / `794c6eae…` / `99638eb0…` / `68b28acd…` / `9613cb01…` readings as provenance (not edited).
