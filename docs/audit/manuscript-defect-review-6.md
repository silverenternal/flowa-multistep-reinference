# Manuscript defect review #6 — sixth consistency sweep

**Date:** 2026-10-12
**Scope:** Sixth reviewer-facing defect sweep across `docs/drafts/paper-A-final.{md,tex}` + the submission SHA ledger, after the user request *"你现在看看写好的论文还有没有什么毛病，之前修复计划里没修完的任务你再看看，能做的现在都做好"* — i.e. a fresh read of the finished manuscript plus a revisit of every still-open item from the prior repair plans (`docs/audit/manuscript-defect-review{,-2,-3,-4,-5}.md`).
**Status:** COMPLETE — 2 defect groups fixed (**markdown-source only**); **the `.tex` build and PDF are byte-identical**; ledger SHAs refreshed; 2 further items reviewed-and-documented (no change). **No metric / claim number changed; no status label moved; no number change in §7.8.**

---

## 1. Observed facts (defects + fixes)

A fresh read of all 1029 lines of `docs/drafts/paper-A-final.md` plus a scripted markdown-structure scan (backtick balance, code-span contents, `**` balance, heading outline, table-column consistency, `§N.M` reference resolution, placeholder tokens), cross-checked against the `.tex` build, surfaced two defect groups. Both are fixed this pass. Two further candidate groups were reviewed and are documented as intentional (below).

| # | Defect | Fix |
|---|---|---|
| I1 | **§7.8.1 backtick-wrapped inline math (only section in the manuscript to do so).** The Wave-183 finer-NFE figure appendix wrapped every `$…$` expression in code spans, rendering math as literal code. Worse, on the `ΔpLDDT + ΔscPerplexity` bullet the bold title interleaved the `**` emphasis markers with backticked math, leaving an **odd** number of backticks on the line; the code spans then mis-nested, swallowing the bold title, the `[` link-opener, and the `band — kanzi` fragment into code spans and **breaking that figure's `[…](…)` hyperlink**. A repo-wide scan confirmed the backtick-math convention appears **nowhere else** in the 1029-line file (bare `$…$` + backticked identifiers everywhere else). See the §2 before/after block. | Normalized the four §7.8.1 lines (`L630` `$\{50,100\}$`, `L632` `ΔpLDDT = fw − baseline`, `L634` title + body, `L636` five expressions) to bare `$…$` math; identifiers/paths/SHAs stay backticked. The odd-backtick mis-nesting and the broken link are repaired. |
| I2 | **Appendix A heading-level skip.** Appendix A's subsections were `#### A.1` / `#### A.2` / `#### A.3` sitting directly under `## Appendix A: Derivations` — a `##`→`####` level skip (no intermediate `###`). | Promoted the three headings to `### A.1` / `### A.2` / `### A.3`. GitHub/mkdocs anchor slugs are unchanged (`#a1-proof-of-theorem-4` etc. depend only on the heading text), so no cross-reference is affected. |

## 2. Evidence

- Manuscript SHA (this pass): `sha256sum docs/drafts/paper-A-final.md` → `9613cb012cde93ca417b59fd87adde7eaeca5306aaa3dbf3d94f7fc8fa02d39a` (211903 bytes; the pass-#5 reading was `794c6eae…` / 211927 bytes). `.tex` → `99638eb09ac930ab37df5a0ea67029287bf82e7ad67f78fd558df73d976d50bf` (63879 bytes, **unchanged**). `.pdf` → `68b28acda286a394cabe17a92f67d715f09208cf19b10385f29fd67b732d0238` (446895 bytes, **11 pages, unchanged**). Both fixes are `.md`-only: §7.8.1 is a markdown-only figure appendix (the `.tex` carries no §7.8.1 / `wave183` / `finer` token), and Appendix A is likewise `.md`-only.
- **I1 ground truth:** a scripted scan of every non-fenced line for code spans whose content contains `$` reported **7** such spans, all on `L630/632/634/636` (§7.8.1) and **zero elsewhere** in the file. Exactly one line (`L634`) had an **odd** backtick count (19), and its code-span pairing swallowed the fragments `' (standalone figure, not in the IEEEtran build)** (['` and `'](https://…wave183-p4-figure-deltas-finer.png'`. After the fix: 0 code-spans-containing-`$`, 0 odd-backtick lines. The pre/post §7.8.1 `L634` bullet:

```
# BEFORE (19 backticks, odd — code spans mis-nested, link broken):
- **`$\Delta$pLDDT + `$\Delta$scPerplexity` (standalone figure, not in the IEEEtran build)** ([`verification_outputs/wave183-p4-figure-deltas-finer.png`](https://…))

# AFTER (bare math inside the bold title; backticks only around identifiers/paths):
- **$\Delta$pLDDT + $\Delta$scPerplexity (standalone figure, not in the IEEEtran build)** ([`verification_outputs/wave183-p4-figure-deltas-finer.png`](https://…))
```
- **I2 ground truth:** a fence-aware heading outline reported the sole level jump as `L950 ## Appendix A: Derivations` → `L954 #### A.1 Proof of Theorem 4`. After the fix: 0 heading-level jumps.
- **Cross-reference check:** a scripted `§N.M` resolution scan (63 distinct references) resolves every in-paper reference; the only non-heading `§` references are the cross-doc `docs/CONSOLIDATED_RESULTS.md` pointers (`§13`, `§15`, `§15.29/30/53/54/55/98/103/104/105`), which are expected.
- **MANIFEST post-edit SHA:** `6b4e2e78d98864e0a1d6e241d5c67ef46c3d0f9a5424821d42cecb34d69e34b2` (68433 bytes). The MANIFEST self-row retains the pre-edit reading per the self-referencing-SHA convention; this audit pins the post-edit value. `SUBMISSION_READINESS.md` post-edit SHA: `ac92dabbc54051a92aefbbbb9cfa8fffb058a7ff72731478b58fdd8f6b212791` (43078 bytes). `submission_checklist.md` post-edit SHA: `0adecfb87987bee19d5dad10725b235e6c3dc22172ea764d449d6f0bd2ab5225` (33789 bytes).
- **Ledger refresh:** the `.md` SHA `794c6eae…` → `9613cb01…` in `README.md` (5 sites) / `README.zh.md` (5 sites) / `todo/STATUS.md` (1) / `todo/WAVES.md` (1) / `tnnls_submission/MANIFEST.md` (md rows ×2 + the `.tex` row's embedded md cross-ref ×1). `docs/README.md` pins only the PDF SHA (unchanged) — no edit. `todo/INDEX.md` pins only the PDF SHA — no edit. The word count is unchanged (`25,564`), so the README word-count metadata is unchanged.

### 2.1 Gate results (acceptance record)

| Gate | Command | Result |
|---|---|---|
| claims consistency | `python3 tools/check_claims_consistency.py` | **PASS** — "No drift detected" (61 active / 2 deprecated / 1 forced-provisional) |
| docs-against-code | `python3 tools/check_docs_against_code.py` | **PASS** — "OK: 4142 claims verified" |
| ruff | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **PASS** — "All checks passed!" |
| D.4 byte-stable regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **PASS** — 30 passed, 3 warnings |
| mkdocs strict | `mkdocs build --strict` | **PASS** — exit 0, zero nav/link warnings |
| mypy strict | `.venvs/flowmol3_venv/bin/python -m mypy adaptive_reflow` | **KNOWN-RED (pre-existing)** — 39 errors in adapter files; environment-dependent (sidecar-venv stubs) and **not touched by this docs-only pass**. Acknowledged in CLM-024. |

## 3. Interpretation

- I1 is a **rendering** defect with a real functional consequence: the odd backtick count mis-nested the code spans on the `ΔpLDDT + ΔscPerplexity` bullet and broke its hyperlink, and the whole section rendered `$…$` math as literal code. Normalizing to the manuscript-wide convention (bare math + backticked identifiers) both restores the rendering and removes the section's isolation.
- I2 is a **markdown-hierarchy** defect (a level skip), fixed by promoting the appendix subsections one level. Anchor slugs are level-independent, so nothing downstream moved.

## 4. Unresolved gaps / caveats

- **`.tex`/`.md` structural re-sync** remains deferred (the `.tex` is a condensed IEEEtran build carrying no §7.8.1 figure appendix, no Appendix-A markdown subsections, no PEP-695 / §8.10 / §9 `L1`–`L8` / §10.3 subsections). Per the established scope decision, only cross-references and labels are kept self-consistent per surface. This is **not** a defect — the two surfaces are intentionally different builds.
- **Internal process labels in `.md` headings — reviewed, not changed.** The `.md` reading copy still carries `(Wave NNN …)` provenance labels in eight headings (§3.4.2 `Wave 355`, §3.5.1 `Wave 349`, §7.8.1 `Wave 353`, §8.10 `Wave 366`, §9.4 `Wave 353`, §9.4.1 `Wave 357`, and the `## Bibliography (ADDITIVE — Wave 364 G15)` heading; plus two `#`-prefixed lines inside a §8.10 fenced bash block, which are code comments, not headings). The authoritative `.tex`/PDF headings are clean. These labels are **load-bearing provenance**: this MANIFEST and the audit trail reference the same wave IDs, so stripping them from the `.md` would dangle those cross-references. They are part of the documented intentional `.md`/`.tex` divergence and are recorded here rather than changed.
- **Unnumbered lead-in heading — reviewed, not changed.** §6 carries one unnumbered `### Three formal properties` heading between the numbered `### 6.1` and `### 6.2`; it is a section lead-in for the Lemmas/Theorems (`.md`-only — the `.tex` §6 has no such heading). Renumbering it would cascade the §6.2–§6.7 cross-references (referenced by §7.2, §6.5, §6.6 and the appendix), so it is left as an editorial lead-in and recorded here.
- **`## References (placeholder keys)`** was checked and is **accurate**, not a leftover: the `[N]` / `[M]` BGV12 / Villani keys are literally placeholder (letter) keys, expanded in the additive `Bibliography` section below. No change.
- The historical records — `docs/audit/manuscript-defect-review{,-2,-3,-4,-5}.md`, the MANIFEST pass-#2/#3/#4/#5 blockquotes, and the SUBMISSION_READINESS §12/§13/§14/§15 addenda — retain the superseded `8315f67e…` / `f3d7b9fb…` / `33d3a771…` / `9e40bf68…` / `8323488f…` / `25f256bc…` / `ce0f0461…` / `794c6eae…` readings as provenance (not edited).
