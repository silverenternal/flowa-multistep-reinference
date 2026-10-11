# Wave 385 — Figure-addendum audit (architecture + evidence-comparison figures)

**Date:** 2026-10-11
**Scope:** `docs/drafts/paper-A-final.{tex,md}`, `docs/figures/fig9_cell_evidence_comparison.png`,
`tools/render_cell_evidence_figure.py`, `tnnls_submission/`, governance surfaces.
**Predecessor:** `docs/audit/wave384-project-audit.md` (project audit + doc refresh).
**User directive:** "画图的话先把架构图和数据对比图画一下，放在论文里合适的位置" — first draw
an architecture diagram and a data-comparison diagram, and place them in appropriate
positions in the paper. Confirmed menu choices: architecture = inline TikZ; data-comparison
= reproducible matplotlib PNG + committed renderer; target both `.tex` and `.md`; uv work
skipped this wave.

---

## 1. TL;DR

- Added **Figure 1 — architecture diagram** (inline TikZ, `paper-A-final.tex` §III Framework):
  three-domain split + four-port control surface + five adapters + shared framework kernel.
- Added **Figure 3 — evidence-comparison diagram** (single-column matplotlib PNG,
  `docs/figures/fig9_cell_evidence_comparison.png`, `paper-A-final.tex` §VII Empirical
  Results via `\includegraphics`): per-cell standardized effect size + eleven-cell verdict
  distribution.
- Synced both into the canonical `.md` source (§3.2 ASCII architecture + §7.2 PNG reference).
- Re-typeset the PDF **10 → 11 pages**, zero fatal LaTeX errors, zero overfull hboxes.
- All acceptance gates PASS: ruff 0 (new renderer), claims no-drift, D.4 30/30,
  mkdocs `--strict` exit 0, vendored `data/` untouched.
- **No metric, claim, or verdict number changed** — both figures transcribe existing
  §III/§VII values verbatim.

---

## 2. What changed (file-by-file)

| File | Change | Kind |
|---|---|---|
| `docs/drafts/paper-A-final.tex` | + `\usetikzlibrary{...calc}`; + Figure 1 TikZ (`figure*`) in §III.A; + Figure 3 `\includegraphics` (`figure`) in §VII.A; + 2 in-text `\ref` sentences | additive |
| `docs/drafts/paper-A-final.md` | + §3.1 architecture pointer; + §3.2 ASCII architecture diagram; + §7.2 evidence-figure reference (`![]()`) + caption paragraph | additive |
| `docs/figures/fig9_cell_evidence_comparison.png` | NEW 300-DPI 2-panel PNG (154826 bytes) | new artifact |
| `tools/render_cell_evidence_figure.py` | NEW reproducible renderer (5921 bytes, ruff-clean) | new artifact |
| `tnnls_submission/MANIFEST.md` | + Wave 385 addendum; refreshed `.md`/`.pdf`/`.tex` rows; + new PNG row; refreshed `README.md`/`cover_letter.md`/`submission_checklist.md`/`supplementary/README.md` rows | refresh |
| `tnnls_submission/{README,submission_checklist,SUBMISSION_READINESS,cover_letter}.md`, `supplementary/README.md` | page count 10 → 11 + PDF SHA refresh | refresh |
| `README.md`, `README.zh.md`, `docs/README.md`, `todo/INDEX.md`, `todo/STATUS.md` | page count + PDF/paper SHA refresh + Wave 385 lineage | refresh |
| `docs/drafts/paper-A-final.{aux,log,out}` | LaTeX build side-effects | build |

---

## 3. Figure design and provenance

### 3.1 Figure 1 — architecture (inline TikZ)

Placed in §III Framework, after the four-port description. Content: the adapter layer
(LineageFlow, Kanzi, FlowMol3, CIFAR-10 RF, MNIST FM wrapping 5 frozen checkpoints with
zero-line edits), the algorithm layer (Engine · 13 schedulers + the four
`*Protocol` ports), the evaluation layer (FID / $W_2$ / coverage evaluators, theorem
checker, Lipschitz diagnostic + PosteriorSelection), and a full-width "Framework kernel"
band (`StateBundle` · typed contracts · SHA-256 hash-chained ledger · byte-stable replay).
Flow arrows carry the typed `StateBundle` and the endpoint trace; dashed arrows show the
downward dependency on the kernel. Vector, no external file, matches the existing
`fig:flowa-mechanism` (now Figure 2) TikZ style.

### 3.2 Figure 3 — evidence comparison (matplotlib PNG)

Renderer `tools/render_cell_evidence_figure.py`, run under `.venvs/flowmol3_venv`
(matplotlib 3.11.1, per the AGENTS.md image-FM venv routing). Two panels:

- **(a)** per-cell standardized effect size `|d|` on a log scale with the `|d| = 0.8`
  STRONG-promotion bar (§7.2). Values transcribed **verbatim** from §7.2:
  R2 `d_z=-0.0990`, R1 `d_z=+0.182`, R6 `d_z=+0.2235` (tier-aware) and `+1.189` (hard
  tier), R3 `d_z=-0.285`, R5a `d_s=+0.460`, R5c `d_z=-13.18`.
- **(b)** the eleven-cell verdict distribution from §7.2 / §7.11:
  4 STRONG + 1 TIE + 2 PARTIAL + 4 SUPP = 11.

R5b (protocol-conditional) and the four K-cells (supplementary) carry no single
standardized effect size and are therefore shown only in panel (b), not (a) — this is
stated in the caption. Byte-stable under repeated invocation
(SHA-256 `4f3224bdb94cbc86cb3ebea6834bc1271cbd3135a54db394d496e754c127b8ae` on
re-render). No randomness, `Agg` backend, fixed style.

---

## 4. Acceptance gates (re-run this wave)

| Gate | Command | Result |
|---|---|---|
| ruff | `.venv/bin/ruff check tools/render_cell_evidence_figure.py` | **All checks passed** |
| claims no-drift | `.venv/bin/python tools/check_claims_consistency.py` | **exit 0** — 61 active, 0 provisional, 2 deprecated, no drift |
| D.4 regression | `.venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q` | **30 passed** |
| mkdocs strict | `.venvs/flowmol3_venv/bin/python -m mkdocs build --strict` | **exit 0** |
| LaTeX build | `pdflatex paper-A-final.tex` ×2 | **11 pages**, 0 fatal errors, 0 overfull hboxes |
| vendored untouched | `git status --short -- data/` | **empty** |

**Environment note (observed fact):** the project venv `.venv` lacks `matplotlib`,
`mkdocs-material`, and (transitively) the docs theme; `matplotlib` is in
`flowmol3_venv`/`kanzi_venv`/`lineageflow_venv`/`geva_venv`, and `mkdocs-material` is in
`flowmol3_venv`. The mkdocs gate was therefore run under `flowmol3_venv`. This is a
pre-existing environment-layout property, not caused by this wave; the uv
project-management follow-up (reconcile `.venv` with `uv.lock` via
`uv sync --extra dev --extra test`) was **skipped** per the user's menu choice.

---

## 5. SHA-256 refresh

| Artifact | Bytes | SHA-256 (Wave 385) |
|---|---|---|
| `docs/drafts/paper-A-final.tex` | 63313 | `ba920254979e9420fe42af20b4f4371792b2cdb028f143c5b25144e8c7800d90` |
| `docs/drafts/paper-A-final.md` | 208159 | `42ff08ac929dcb27b902c87059aa1e48b2e2c99ae9f0a063aecb89bc84eb745a` |
| `docs/drafts/paper-A-final.pdf` | 446705 | `461ee92e80c1e1808c87db3f4645db5c5400eb0bbd25e3c4ccfd3e74bd0ac274` |
| `docs/figures/fig9_cell_evidence_comparison.png` | 154826 | `4f3224bdb94cbc86cb3ebea6834bc1271cbd3135a54db394d496e754c127b8ae` |
| `tools/render_cell_evidence_figure.py` | 5921 | `cca3b2c124e6bcef1782c3eef86926f7c4a35e01a6a882322cd2775ac50ba9b8` |

Superseded (Wave 384): `paper-A-final.tex` `3a54fa7a…`, `.md` `b106ac53…`,
`.pdf` `bd05399b…` (10 pages).

Submission-package rows refreshed in `tnnls_submission/MANIFEST.md`:
`README.md` = `36fcc4f6…`, `cover_letter.md` = `4435866e…`,
`submission_checklist.md` = `cd0db920…`, `supplementary/README.md` = `01354661…`.

---

## 6. Observed / interpretation / gaps

**Observed facts.** Two figures were added; the PDF grew 10 → 11 pages; all gates PASS;
`data/` untouched; the renderer is ruff-clean and byte-stable.

**Interpretation.** The 11-page build remains well within the TNNLS ≤ 14-page limit, so the
figures can be added without violating the page budget. Because the `.tex` had zero
`\includegraphics` before, Figure 3 is the first raster include in the manuscript — the
relative path `../figures/fig9_cell_evidence_comparison.png` resolves from `docs/drafts/`
and the PNG is a committed repo artifact, so the build stays self-contained.

**Unresolved gaps.**
1. **`.md` / `.tex` figure numbering diverges.** The `.md` numbers figures descriptively
   (it already carried "Figure 1 (Wave 349)" for the R5c regime curve and Figures 3–5 for
   the Wave 183 ladder), whereas the `.tex` auto-numbers (Figure 1 = architecture,
   Figure 2 = mechanism, Figure 3 = evidence comparison). The two surfaces are
   content-consistent but not number-consistent; this is the pre-existing dual-surface
   convention, not introduced here.
2. **MANIFEST self-SHA.** The MANIFEST's own row is self-referential by design (the pinned
   value is the pre-edit hash). Current `sha256sum tnnls_submission/MANIFEST.md` after the
   Wave 385 edits is recorded at the end of this doc for reviewer re-hash.
3. **`docs/audit/INDEX.md` not regenerated.** The Wave 384 regeneration (509 files) was not
   re-run for this single new audit doc; the index refresh is deferred.
4. **`figures.md` catalog** was not extended with the new PNG row (avoided the extra SHA
   cascade); the new figure is documented in `MANIFEST.md` instead.

---

## 7. Hard-rule compliance

- **Vendored upstream sacred:** `git status --short -- data/` empty. ✅
- **No destructive edits:** every change is additive (new figure blocks, new renderer,
  new PNG) except page-count/SHA refreshes, which are factual corrections explicitly
  permitted by guardrail #5 ("SHA-256s must be regenerated"). ✅
- **NO-PUSH:** no push performed. ✅
- **Honest uncertainty:** no claim/verdict/number promoted or demoted; both figures
  transcribe existing values verbatim. ✅
- **TNNLS freeze:** numbers did not move; SHAs regenerated. ✅
- **Per-wave audit doc:** this file. ✅
- **Stricter = cleaner:** one new renderer, one new PNG, inline TikZ (no external vector
  file), no changes to `figures.md`/`INDEX.md`. ✅

---

## 8. Cross-references

- Predecessor audit: `docs/audit/wave384-project-audit.md`
- Renderer: `tools/render_cell_evidence_figure.py`
- Figure asset: `docs/figures/fig9_cell_evidence_comparison.png`
- Data source: `docs/drafts/paper-A-final.md` §7.2 / §7.11
- Package manifest: `tnnls_submission/MANIFEST.md` (Wave 385 addendum)
- Renderer precedent: `tools/render_r5c_regime_curve.py` (Wave 349)

**MANIFEST.md post-edit SHA-256:** `f76bb996ff40869d5e1870ae05390e94df72cc67e066c46a53bd6132b53d10a7`
(55862 bytes) — the value pinned inside the MANIFEST is the pre-edit hash by convention;
reviewers should re-hash on receipt.
