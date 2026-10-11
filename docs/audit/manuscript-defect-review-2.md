# Manuscript defect review #2 — second `.tex`/`.md` consistency pass

**Date:** 2026-10-12
**Scope:** Second reviewer-facing defect sweep across `docs/drafts/paper-A-final.{md,tex}` + the submission SHA ledger, after the user request *"你现在看看写好的论文还有没有什么毛病，之前修复计划里没修完的任务你再看看，能做的现在都做好"* — i.e. re-inspect the finished manuscript and close every still-open item from the prior repair plan (`docs/audit/manuscript-defect-review.md`).
**Status:** COMPLETE — 7 defect groups fixed; manuscript SHAs refreshed; PDF rebuilt; **no metric / claim number changed; no status label moved.**

---

## 1. Observed facts (defects + fixes)

All edits are **wording/structure/additive** (guardrail §3.4 honest-uncertainty + §3.5 freeze + §3.7 stricter=cleaner). The prior pass (`manuscript-defect-review.md`) left two items explicitly open: (a) the stale `CLAIMS.md` CLM-060 R2 disclosure, and (b) the `.tex`/`.md` structural re-sync. This pass closes (a) additively and records the remaining defects found in the fresh read; (b) stays deferred per the prior audit's scope decision.

| # | Defect | Fix |
|---|---|---|
| 1 | §2.3 citation keys off by three: the ICML-2024 negative-results position paper, REAL ML, and McGreivy–Hakim were cited in-text as `[13]`/`[14]`/`[15]`, but the reference list places them at `[10]`/`[11]`/`[12]` (`[13]`=LineageFlow, `[14]`=Kanzi, `[15]`=FlowMol3). | `.md:66` `[13]`→`[10]`, `[14]`→`[11]`; `.tex:80` `[13]`→`[10]`, `[14]`→`[11]`, McGreivy `[15]`→`[12]`. |
| 2 | Raw p-values mislabelled as "Bonferroni-corrected $p$" — the value shown is the **raw** p, not the corrected one. Affects R5a (`0.604`) and R1 (`1.25e-8`) in both surfaces, plus the `.tex` R2 row (`1.79e-3`). | Relabelled to name the raw value and separately state Bonferroni significance at the family α: `.md:548/558`, `.tex:448/450/458`. Numbers unchanged. |
| 3 | Two inline-code glitches in `.md`: an unclosed backtick + stray `$` (`easy_tier_nfe_reduction_factor = 0.5$`), and stray `$` inside `` `d_z = +\text{Inf}` `` at two sites. | `.md:554`, `.md:792`, `.md:858` — removed the stray `$`; code spans now render literally. |
| 4 | §7.11 R5c row carried a stray `CONSOLIDATED_RESULTS §15.104 (Wave 352 P5 R5a …)` prefix — a copy-paste from the R5a row (`§15.104` is an R5a section, not R5c). | `.md:669` — removed the `§15.104 … + ` prefix; kept only `§15.103 (Wave 326 11-cell snapshot pointer)`. |
| 5 | §7.9 referenced a dangling `§10.8(i)` sub-item that does not exist. | `.md:652` — `§10.8(i)` → `§10.8`; reworded to quote the §10.8 future-work item verbatim. |
| 6 | `docs/CLAIMS.md` CLM-060 Statement block still describes the **pre-bridge** Wave 91 synthesis path (`x_final ~ N(0, 1e-3)`, "no ODE rollout"), which contradicts the **currently deployed** R2 measurement (Wave 218 P3 `framework_inv_proj`, which feeds the real 512-d trajectory endpoint through the trained `project_out⁻¹` bridge and runs the adapter's 50-step Euler rollout). The prior audit flagged this as out-of-scope for a paper-only pass. | Added an **additive** "Manuscript-consistency addendum (R2 deployed-path basis clarification)" bullet to CLM-060 (immediately before its `Date:` line), preserving the original disclosure verbatim as the Wave 195 P2 status-history entry. **No CLM-060 number changed.** `Date:` line extended with `; R2 deployed-path basis clarification appended 2026-10-12`. |
| 7 | `.tex` R2 row lacked the synthetic-input-coordinate disclosure that the `.md` R2 row already carried. | `.tex:448` — appended the `\emph{Measurement basis:}` sentence (4 PDB backbones × 250 Gaussian perturbations, σ=0.10 Å; bridge fed the real 512-d trajectory endpoint; Δ is a framework-internal reconstruction RMSD). |
| 8 | PDF rebuilt after the `.tex` edits; SHA ledger refreshed. | `paper-A-final.pdf` → 11 pp / 447018 B / `33d3a771…`; `.md` → `8315f67e…` (210899 B); `.tex` → `f3d7b9fb…` (63970 B); MANIFEST (manuscript rows + `submission_checklist` row + new "Manuscript-consistency pass (2026-10-12)" addendum), `SUBMISSION_READINESS.md` §12, `submission_checklist.md` G38 annotation, `README{,.zh}.md`, `docs/README.md`, `todo/{STATUS,INDEX,WAVES}.md` refreshed. |

## 2. Evidence

- Manuscript SHAs: `sha256sum docs/drafts/paper-A-final.{md,tex,pdf}` → `8315f67e15d38b3ab8f4e15becbda7df9feb133f3c862564671bc0f3bcf1672f` / `f3d7b9fbdad1100b498887ff352cf225b7c20cb2442d257ccfa88a76a4a514b4` / `33d3a771fc6ea0cd4cd8a685058f4d9237417696351aa6e816388af613444916`.
- PDF: `pdflatex` ×3 passes, zero undefined references, zero LaTeX errors; 11 pages.
- §2.3 citation keys: `.md:66` + `.tex:80` now cite `[10]` (ICML 2024) / `[11]` (REAL ML) / `[12]` (McGreivy–Hakim), matching the reference list at `.md:908-912` / `.tex:560-562`.
- Raw-p relabel: `.md:548` (R5a `Raw $p = 0.604$`), `.md:558` (R1 `Raw $p = 1.25 \times 10^{-8}$`), `.tex:448` (R2 `Raw $p = 1.79 \times 10^{-3}$`), `.tex:450` (R5a), `.tex:458` (R1). Canonical raw values: CLAIMS CLM-060 (`p_raw = 1.7943e-3`).
- R2 deployed path: `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:5-13` + `docs/audit/kanzi/p3-kanzi-n1000-framework-inv-proj.md`; `docs/CLAIMS.md` CLM-060.
- R5c pointer: `.md:669` R5c row now cites only `CONSOLIDATED_RESULTS §15.103`; the R5a row (`.md:667`) retains `§15.104`.
- **MANIFEST post-edit SHA:** `848cec73db991f8f573b913c348b190b4500caca020156fb0229ac16facbb563` (58748 bytes). The MANIFEST self-row retains the pre-edit `d1fc6d40…` per the self-referencing-SHA convention; this audit pins the post-edit value. `SUBMISSION_READINESS.md` post-edit SHA: `ab8e961513998b9dd28a2ccd2d624838ae48f70fe9f4bff106f29f3f31daf8ea` (35569 bytes). `submission_checklist.md` post-edit SHA: `35c2814ab19ddc538845b4852b993444cea6a1fa468bdd85027d6aac2cebaef4` (33589 bytes).

### 2.1 Gate results (acceptance record)

| Gate | Command | Result |
|---|---|---|
| claims consistency | `python3 tools/check_claims_consistency.py` | **PASS** — "No drift detected" (61 active / 0 provisional / 2 deprecated) |
| docs-against-code | `python3 tools/check_docs_against_code.py` | **PASS** — "OK: 4142 claims verified" |
| ruff | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **PASS** — "All checks passed!" |
| D.4 byte-stable regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **PASS** — 30 passed, 3 warnings in 4.25s |
| mkdocs strict | `mkdocs build --strict` | **PASS** — built in 26.65s, zero nav/link warnings |
| mypy strict | `.venvs/flowmol3_venv/bin/python -m mypy adaptive_reflow` | **KNOWN-RED (pre-existing)** — 39 errors in 13 files (all adapter files: `hidream_i1.py`, `_hidream_i1_upstream_shim.py`, `flowmol3_v2_adapter.py`, `kanzi.py`); environment-dependent (sidecar-venv diffusers/torch stubs) and **not touched by this docs-only pass**. Current state acknowledged in CLM-024; target remains 0 errors. |

## 3. Interpretation

- The §2.3 citation-key mismatch was a **stale-number** defect: the reference list was renumbered in an earlier pass but the in-text keys were not propagated. The fix restores `[n]`→bibliography consistency without touching any bibliography entry.
- The "Bonferroni-corrected $p$" label was a **naming** defect, not a wrong number: the displayed value is the raw per-cell p. Naming the raw value and stating Bonferroni significance separately is the honest form (guardrail §3.4) and leaves the number untouched.
- The CLM-060 R2 item was the last still-open task from the prior repair plan. It is a **basis clarification**, not a status change: the R2 cell remains `SUPPORTED`; the addendum only records that the deployed measurement path differs from the historical Wave 91 synthesis path described in the frozen Statement block, per the Wave 268 strict-clean additive-history rule.

## 4. Unresolved gaps / caveats

- **`.tex`/`.md` structural re-sync** remains deferred (the `.tex` has no PEP-695 / honest-disclosure / hash-chained-ledger subsections). Per user direction only cross-references and labels are kept self-consistent per surface; a full structural re-sync is out of scope.
- **R5c "Bonferroni $p = 3.95 \times 10^{-11}$" label** (`docs/CLAIMS.md` R5c row; `.md:669` / `.tex` R5c row) is a **doc-wide canonical label** (per-3-arm-count $k = 3$) and was intentionally left as-is in this pass — relabelling it is a ledger-wide change that must not be bundled with a manuscript-surface pass.
- **`.tex` "12-column audit row"** wording (which lists 13 columns) is a doc-wide canonical label carried from the CLAIMS R3 row and was left as-is for the same reason.
- `docs/audit/manuscript-defect-review.md` and the MANIFEST 2026-10-11 addendum retain the superseded `c88d6069…` / `cca0be6f…` / `8bc37858…` readings as historical record (not edited).
