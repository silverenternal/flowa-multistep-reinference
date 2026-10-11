# Manuscript defect review #7 — seventh consistency sweep

**Date:** 2026-10-12
**Scope:** Seventh reviewer-facing defect sweep across `docs/drafts/paper-A-final.{md,tex}` + the submission SHA ledger, after the user request *"你现在看看写好的论文还有没有什么毛病，之前修复计划里没修完的任务你再看看，能做的现在都做好"*. Unlike passes #5 and #6 (markdown-source-dominant), this pass focused on the `.tex` IEEEtran build — which had received less scrutiny — plus a fresh read of both surfaces.
**Status:** COMPLETE — 3 defect groups fixed (**`.tex`-only**); the PDF was **rebuilt** (still 11 pages); ledger SHAs refreshed; 1 further item reviewed-and-documented (no change). **No metric / claim number changed; no status label moved.**

---

## 1. Observed facts (defects + fixes)

A scripted scan of the `.tex` (markdown-artifact detection: `**` / `](` / backticks; `\texttt{}` underscore escaping; `\ref`/`\label` balance; float-vs-citation inventory) plus a fresh read of both surfaces surfaced three `.tex`-only defect groups. All three are fixed this pass.

| # | Defect | Fix |
|---|---|---|
| J1 | **Markdown backticks leaked into the `.tex`.** §7.4's 13-column audit-row tuple was wrapped in Markdown code-span backticks — `` `(n\_paired, mean\_diff, …)` `` — which render as **literal backtick characters** in the PDF. This was the only backtick occurrence in the entire `.tex`; the rest of the file uses `\texttt{…}`. | Replaced the backticks with `\texttt{(n\_paired, mean\_diff, sd\_diff, t, df, p\_raw, CI\_95\_low, CI\_95\_high, d\_z, test\_type, family, alpha\_bonferroni, bonf\_sig)}` (`.tex:475`). |
| J2 | **Duplicated "as … as …" clause.** §7.4 read "FDR-BH sensitivity at $q = 0.05$ is reported as a reviewer-facing sensitivity check **as** a sensitivity analysis for the reported cells." — a garbled double-`as` construction. | Reduced to "…is reported as a reviewer-facing sensitivity analysis for the reported cells." (`.tex:485`). |
| J3 | **Three of the six floats were uncited.** `\label`/`\ref` inventory showed only 3 references for 6 floats: **Figure 2** (`fig:flowa-mechanism`) and the two unlabeled tables — the §III.2 "Mechanism-to-evidence map" and the §VII.1 "Main-cell evidence" table — carried no `\ref` anywhere in the text. | Added `\label{tab:mechanism-evidence}` and `\label{tab:main-cell-evidence}`, and cited all three in text: `Figure~\ref{fig:flowa-mechanism}` + `Table~\ref{tab:mechanism-evidence}` in §III.2, and `Table~\ref{tab:main-cell-evidence}` in §VII.1. Every float now carries a label **and** an in-text reference. |

## 2. Evidence

- Manuscript SHA (this pass): `sha256sum docs/drafts/paper-A-final.tex` → `55e058d5f446a9ea013002a9da13d67369d903cfb65df1e65ef125ea47fda807` (64156 bytes; the pass-#5 reading was `99638eb0…` / 63879 bytes). `.pdf` → `47f6eb0418d041b0dccdba68bcdf8b794c02e8a710368a8eaebe5e17f89ca732` (446788 bytes, **11 pages**, rebuilt with two `pdflatex` passes; zero fatal errors, zero overfull hboxes, zero undefined references). `.md` → `9613cb012cde93ca417b59fd87adde7eaeca5306aaa3dbf3d94f7fc8fa02d39a` (211903 bytes, **unchanged** — pass #7 touched no `.md` content).
- **J1 ground truth:** a backtick count of `paper-A-final.tex` → **1** before the fix (`.tex:475`), **0** after. No `**` or `](` markdown artifacts were found anywhere in the `.tex`.
- **J2 ground truth:** the `.tex` sentence and the `.md` §7.4 sentence had diverged (`.md`: "…is reported as a reviewer-facing sensitivity check **and agrees with the Bonferroni verdict on every cell**"); the `.tex`'s own clause was grammatically broken independently of that divergence, so only the duplicated `as … as …` was reduced (the `.tex`'s meaning — "a sensitivity analysis for the reported cells" — was preserved).
- **J3 ground truth:** before the fix the `.tex` had 6 float environments (`figure*` ×1, `figure` ×2, `table` ×2, `table*` ×1) but only 3 `\ref`s (`fig:flowa-architecture`, `tab:mechanism-map`, `fig:cell-evidence`); `\ref{fig:flowa-mechanism}` count was **0**. After the fix: 6 labels + 6 refs, one per float.
- **Build verification:** two `pdflatex -interaction=nonstopmode -halt-on-error` passes, both exit 0; `pdfinfo` → `Pages: 11`; `grep -c 'Overfull \\hbox'` → **0**; `grep -iE 'undefined|Warning: Reference|Warning: Citation'` → empty. The `.aux`/`.log` build side-effects were reverted via `git checkout --` (per the established convention), so only `.tex` + `.pdf` changed on disk.
- **Ledger refresh:** the `.tex` SHA `99638eb0…` → `55e058d5…` and the `.pdf` SHA `68b28acd…` → `47f6eb04…` (size 446895 → 446788) in `README.md` (pdf ×4) / `README.zh.md` (pdf ×4) / `docs/README.md` (pdf ×1) / `todo/INDEX.md` (pdf ×1) / `todo/STATUS.md` (pdf + tex) / `todo/WAVES.md` (pdf + tex) / `tnnls_submission/MANIFEST.md` (pdf rows ×2 + tex rows ×2). The `.md` SHA is unchanged, so the `README` markdown-SHA rows and word-count metadata are unchanged.
- **MANIFEST post-edit SHA:** `b028fb6090e374f27f93e42f91d2088e9019ae05b10128a02526b0a4a3273205` (70178 bytes). The MANIFEST self-row retains the pre-edit reading per the self-referencing-SHA convention; this audit pins the post-edit value. `SUBMISSION_READINESS.md` post-edit SHA: `04ca6acad06ba70328518fc47aad5540c8653c4a177ec07a92668c1dba16d246` (45104 bytes). `submission_checklist.md` post-edit SHA: `780d0e2ab13ba397c4b1b6e9690e3d616dcecee61f53e3f8851ea02f5714b4b0` (33941 bytes).

### 2.1 Gate results (acceptance record)

| Gate | Command | Result |
|---|---|---|
| claims consistency | `python3 tools/check_claims_consistency.py` | **PASS** — "No drift detected" |
| docs-against-code | `python3 tools/check_docs_against_code.py` | **PASS** — "OK: 4142 claims verified" |
| ruff | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **PASS** — "All checks passed!" |
| D.4 byte-stable regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **PASS** — 30 passed |
| mkdocs strict | `mkdocs build --strict` | **PASS** — exit 0, zero nav/link warnings |
| PDF build | `pdflatex … paper-A-final.tex` ×2 | **PASS** — exit 0, 11 pages, 0 overfull hboxes, 0 undefined refs |
| mypy strict | `.venvs/flowmol3_venv/bin/python -m mypy adaptive_reflow` | **KNOWN-RED (pre-existing)** — 39 errors in adapter files; environment-dependent and **not touched by this docs-only pass**. Acknowledged in CLM-024. |

## 3. Interpretation

- J1 is a **rendering** defect: a Markdown code-span delimiter had leaked into the LaTeX, so the PDF displayed literal backticks around the audit-row tuple. Replacing it with the file's own `\texttt{}` convention fixes both the rendering and the inconsistency.
- J2 is a **wording** defect (a duplicated `as … as …` clause). The fix is grammatical only; the `.tex`'s own claim is unchanged.
- J3 is a **submission-standards** defect: three floats appeared in the PDF with no in-text citation. Adding labels + refs makes every float discoverable from the prose, as journals require.

## 4. Unresolved gaps / caveats

- **`.tex`/`.md` structural re-sync** remains deferred (the `.tex` is a condensed IEEEtran build with no §8.10 / §9 `L1`–`L8` / §10.3 / §7.8.1 subsections). Not a defect — intentionally different builds.
- **§8.10 honest-disclosure item #1 — reviewed, not changed.** The `.md` §8.10 block reads "**`paper.pdf` NOT regenerated post-Wave 356 P1.** … The compiled `paper.pdf` reflects the §7/§8/§9/§10 prose as of Wave 356 P1". Two issues: (a) `docs/drafts/paper.pdf` does not exist (the artifact is `paper-A-final.pdf`), and (b) the PDF has been rebuilt several times since Wave 356 (Wave 384, Wave 385, and this pass), so the "not regenerated" present-tense claim is stale. It is a frozen **Wave-366-P2 ADDITIVE** block whose own text asserts additive-only provenance ("0 lines of prior §8.1–§8.9 prose modified"), so it is recorded here rather than reworded — editing it would require an explicit maintainer decision to reopen a frozen disclosure block.
- **`(Wave NNN …)` provenance labels in `.md` headings** (pass-#6 item) and the unnumbered `### Three formal properties` lead-in remain as documented in `docs/audit/manuscript-defect-review-6.md` §4 (reviewed, not changed).
- The historical records — `docs/audit/manuscript-defect-review{,-2,-3,-4,-5,-6}.md`, the MANIFEST pass-#2…#6 blockquotes, and the SUBMISSION_READINESS §12–§16 addenda — retain the superseded `8315f67e…` / `f3d7b9fb…` / `33d3a771…` / `9e40bf68…` / `8323488f…` / `25f256bc…` / `ce0f0461…` / `794c6eae…` / `99638eb0…` / `68b28acd…` readings as provenance (not edited).
