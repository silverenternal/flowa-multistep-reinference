# Wave 301 Day 3 — IEEEtran Typesetting + Submission Package + Paper B Skeleton

**Date:** 2026-09-23
**Mode:** PLAN ONLY (READ-ONLY against source code; no edits until Day 2 complete + user-reviewed paper draft)
**Author:** Wave 301 Day 3 execution planning agent
**Predecessor:** `docs/audit/wave301-day2-execution-plan.md` (Day 2 Path A prose-proofs + §2/§8/§11 fresh-writing + boundary-clearness user review — MUST be complete)
**Input file under eventual modification:** `docs/drafts/paper-flat-flattened.md` (post-Day-2 state; expected ~1069 lines + ~4800-5500 words + 6 lemmas + 3 sketches + §2/§8/§11 inserted)
**Output deliverables:** `docs/drafts/paper.tex` (IEEEtran typeset) + `docs/paper-tnnls.pdf` (≤14 pages TOTAL) + `tnnls_submission/` package refresh + `docs/drafts/paper-b-jmaa/skeleton.md` (Paper B §1 + 10-experiment list)

---

## 0. CRITICAL GUARD — READ BEFORE EXECUTING

**Day 3 does NOT execute until:**

1. **Day 1 RESOLUTION pass complete**: `paper-flat-flattened.md` collapsed from 1404 → ~1069 lines (or ~1399 lines if Wave 300 P5 fold-in anchors retained); 11-section canonical structure verified; 5-gate baseline re-established (D.4 30/30 + ruff 0 + mkdocs strict 0 + claims no-drift + vendored untouched).
2. **Day 2 Path A + fresh-writing complete**: 6 lemmas + 3 proof sketches produced in `wave301-day2-lemmas.md` (~4500-5500 words); §2 Related Work (600-800w), §8 Reproducibility (600-800w), §11 Conclusion (200-300w) drafts produced; cross-check + boundary-clearness user review signed off.
3. **Day 0 §6/§10/figure-count decisions recorded**: per `wave301-day0-prompt.md` §1 (defaults: drop §6 Theoretical Lenses entirely, drop §10 Future Work folded into §8, 3-4 figures + 2-3 tables).
4. **Day 0 venue lock to TNNLS confirmed**: per `wave301-day0-prompt.md` §3 (ICLR 2027 dropped; ICLR 2028 as backup; TNNLS primary).
5. **Boundary-clearness user review PASSED**: Contributions list + Abstract + §6 removal confirmed by user before Day 3 begins.

**If any of the above are missing, STOP and re-engage user.** No edits to `paper-flat-flattened.md`, `paper.tex`, `tnnls_submission/`, or any Day 3 deliverable files are performed.

---

## 1. Scope Statement (Day 3 deliverable + non-scope)

### 1.1 IN SCOPE for Day 3 (in execution order)

**Phase A — IEEEtran typesetting (TNNLS template conversion)**

| Step | Action | Output |
|---|---|---|
| A.1 | Convert `docs/drafts/paper-flat-flattened.md` → `docs/drafts/paper.tex` with `\documentclass[journal]{IEEEtran}` | `paper.tex` (~5000-6500 lines LaTeX) |
| A.2 | Insert IEEEtran class preamble + TNNLS-compliant packages | updated `paper.tex` header |
| A.3 | Wrap Lemmas 1-6 in `\begin{lemma}...\end{lemma}` + `\begin{proof}...\end{proof}` | 6 lemma environments in §3 + §5 main text |
| A.4 | Wrap Sketches 1-3 in `\begin{sketch}...\end{sketch}` (or inline as Sketch environments) | 3 sketch environments in §3 + §5 |
| A.5 | Convert 11-cell status table → `\begin{table}[ht]` + `tabular` env | Table 7.1 in §7 |
| A.6 | Convert 6-column Bonferroni table → `\begin{table}[ht]` + `tabular` env | Table 7.2 in §7 |
| A.7 | Convert 4-arm H2H table → `\begin{table}[ht]` + `tabular` env | Table 7.3 in §7 |
| A.8 | Convert scheduler taxonomy + adapter tables → `\begin{table}[ht]` + `\begin{tabular}` | Tables 4.1 + 5.1 |
| A.9 | Place 4 figure placeholders: (i) FlowA hexagonal architecture (from `tnnls_submission/figures.md` Figure 1); (ii) Re-inference dataflow (Figure 2); (iii) 3-tier experiment hierarchy (Figure 3); (iv) 4-arm H2H schematic (Figure 4) | 4 `\includegraphics` placeholders |
| A.10 | Insert bibliography: `bibliography.bib` with 30-50 references (FM theory, ODE solvers, ML systems, reproducibility, FID/perceptual metrics) | `bibliography.bib` + `\bibliography{bibliography}` in `paper.tex` |
| A.11 | Run `pdflatex paper.tex` → `bibtex paper` → `pdflatex paper.tex` → `pdflatex paper.tex` | `paper.pdf` compiled |
| A.12 | Verify page count ≤14 pages TOTAL (TNNLS limit) | `pdfinfo paper.pdf` or `pdflatex log` count |

**Phase B — Cross-reference update pass (audit docs)**

| Step | Action | Output |
|---|---|---|
| B.1 | `grep -rn "paper-flat-flattened.md:L[0-9]" docs/audit/` → enumerate audit docs citing legacy line ranges | `docs/audit/wave301-cross-ref-update-list.md` |
| B.2 | Update line-range references in each audit doc (sed/edit) to canonical post-RESOLUTION line numbers | ~15 audit docs updated |
| B.3 | Re-run `python3 tools/check_claims_consistency.py` after each update | claims no-drift maintained |
| B.4 | Re-run `mkdocs build --strict` after each update | mkdocs 0-warnings maintained |

**Phase C — TNNLS Submission package assembly**

| Step | Action | Output |
|---|---|---|
| C.1 | Verify `tnnls_submission/MANIFEST.md` SHA-256 hashes match on-disk files | updated `MANIFEST.md` |
| C.2 | Verify `tnnls_submission/cover_letter.md` (17 `[USER TO FILL: ...]` placeholders per `FILL_GUIDE.md`) | `cover_letter.md` ready |
| C.3 | Verify `tnnls_submission/highlights.md` (3 × 85-char highlights) | `highlights.md` ready |
| C.4 | Verify `tnnls_submission/tables.md` + `tnnls_submission/figures.md` (5+ ASCII tables/figures, paste-verbatim-into-LaTeX format) | both ready |
| C.5 | Verify `tnnls_submission/data_availability.md` | ready |
| C.6 | Verify `tnnls_submission/submission_checklist.md` (editorial requirements) | ready |
| C.7 | Generate `source.zip` (paper.tex + bibliography.bib + figures/ + IEEEtran.cls + md_to_tex.py + all inline assets) | `source.zip` in `tnnls_submission/` |
| C.8 | Generate `paper.pdf` from `paper.tex`; copy from `docs/build_pdf/paper.pdf` to `tnnls_submission/paper.pdf` AND `docs/paper-tnnls.pdf` (replacing placeholder) | 2 PDF copies |
| C.9 | Generate `highlight_blurb.pdf` (3 highlight bullets + author bios + abstract) for Editorial Manager "Highlights" paste | `tnnls_submission/highlight_blurb.pdf` |
| C.10 | Refresh `tnnls_submission/MANIFEST.md` with new SHA-256 + sizes | updated `MANIFEST.md` |

**Phase D — Paper B skeleton (separate directory)**

| Step | Action | Output |
|---|---|---|
| D.1 | Create `docs/drafts/paper-b-jmaa/` directory (separate from Paper A) | directory created |
| D.2 | Write `docs/drafts/paper-b-jmaa/skeleton.md` with §1 Introduction (200-400w) referencing Paper A as framework foundation | `skeleton.md` skeleton |
| D.3 | List 10 Paper B experiments (~35 GPU hours total) | `experiments.md` |
| D.4 | Itemize regime-sweep prerequisite (3-tier easy/medium/hard tier-stratified sweeps) | `regime-sweep.md` |
| D.5 | Identify Paper B's 4-6 primary contributions (Paper-quantity-driven scheduler family + Theorem 1 convergence + 16-site integration + Regime-sweep boundary + FID Δ=0% evidence) | `contributions.md` |
| D.6 | Set up `docs/drafts/paper-b-jmaa/refs/` for bibliography stub | empty directory + `refs.md` |
| D.7 | Initialize git branch `paper-b-skeleton` (do NOT merge into main) | branch created |

### 1.2 OUT OF SCOPE for Day 3 (deferred)

- Paper B main prose, theorems, experiments (Day 9+ in 8-10 day plan; later)
- Full-length submission talk slides / poster (deferred to camera-ready)
- TVCG / TOCHI alt-venue consideration (deferred unless TNNLS rejects)
- Camera-ready polish (multi-week post-acceptance)
- Public Zenodo DOI generation (Day 8 of 8-10 day plan)
- Author bio paragraph writing (Day 6 of 8-10 day plan; user input required)
- Suggested reviewer COI sweep (Day 6 of 8-10 day plan)
- Final submission upload to ScholarOne (Day 8 of 8-10 day plan; user copyright/DORA workflow required)

### 1.3 Day 3 deliverable summary

- `docs/audit/wave301-day3-execution-plan.md` — THIS DOCUMENT (read-only output)
- `docs/drafts/paper.tex` — IEEEtran typeset Paper A (~5000-6500 lines LaTeX)
- `docs/paper-tnnls.pdf` — Day 1 output replacing placeholder, copied to `tnnls_submission/`
- `docs/drafts/bibliography.bib` — 30-50 references for IEEEtran
- `docs/audit/wave301-cross-ref-update-list.md` — list of audit docs needing line-range updates after RESOLUTION
- `docs/audit/wave301-day3-finalize-run-log.md` — Phase A12 page-count verification + Phase B cross-ref summary
- `tnnls_submission/source.zip` — submission source bundle
- `tnnls_submission/MANIFEST.md` (refreshed) — new SHA-256 + sizes
- `docs/drafts/paper-b-jmaa/skeleton.md` — Paper B §1 + outline
- `docs/drafts/paper-b-jmaa/experiments.md` — 10-experiment list (~35 GPU hours)
- `docs/drafts/paper-b-jmaa/regime-sweep.md` — 3-tier prerequisite
- `docs/drafts/paper-b-jmaa/contributions.md` — 4-6 primary contributions
- `docs/drafts/paper-b-jmaa/refs/refs.md` — bibliography stub
- Git branch `paper-b-skeleton` — locked skeleton reference

**Total Day 3 output: 9 new files + 4 refreshed files + 1 git branch.**

---

## 2. IEEEtran Typesetting Checklist (Phase A)

### 2.1 IEEEtran class + TNNLS preamble (REQUIRED base)

```latex
%% paper.tex — Paper A (TNNLS submission)
%% Generated from docs/drafts/paper-flat-flattened.md by md_to_tex.py on Day 3.
%%
%% Author mandate: Day 3 IEEEtran typesetting ONLY executes after Day 2
%% Path A + draft + user review complete (see wave301-day3-execution-plan.md §0).

\documentclass[journal]{IEEEtran}
%% journal = TNNLS official single-column body (10pt); use [journal,onecolumn] for 1-col.
%% IEEEtran.cls ships with TeX Live 2023+; verify with `kpsewhich IEEEtran.cls`.

% --- Core packages ---
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath, amssymb, amsthm}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{url}
\usepackage{xcolor}
\usepackage{microtype}

% --- Theorem environments (Wave 301 Day 2 lemmas + sketches) ---
\newtheorem{lemma}{Lemma}
\newtheorem{sketch}{Proof Sketch}
\newtheorem{claim}{Claim}
\newtheorem{corollary}{Corollary}

% --- Bibliography style: IEEEtran numeric (matches TNNLS editorial) ---
% Source files: bibtex + bibliography.bib
\bibliographystyle{IEEEtran}

% --- Graphics path ---
\graphicspath{{figures/}{./}{../}{../figures/}}

% --- Title + author (Day 6 user-input box; placeholder below) ---
\title{FlowA: A Training-Free Re-Inference Framework for Frozen Flow Matching Checkpoints}

\author{
    Anonymous Authors \thanks{Manuscript submitted to IEEE TNNLS.}\\
    Anonymous Institution\\
    \texttt{anonymous@example.com}
}

\begin{document}
\maketitle

\begin{abstract}
% 5-sentence abstract from Day 1 Pair-2 promotion (per wave301-day0-prompt §1 Pair 2)
% TNNLS allows up to 250 words for the abstract; the additive 5-sentence abstract is ~150-180 words.
% Include 4 keywords at the end per IEEE convention: \begin{IEEEkeywords} ... \end{IEEEkeywords}
\end{abstract}

% Paper A canonical 11-section structure (per wave301-day1 §10 + 8-day plan Day 3):
\input{sections/introduction}
\input{sections/related-work}
\input{sections/framework}
\input{sections/scheduler-family}
\input{sections/adapter-protocol}
% §6 Theoretical Lenses dropped per Day 0 decision (skip)
\input{sections/empirical-results}
\input{sections/reproducibility}
\input{sections/limitations}
% §10 Future Work folded into §8 Limitations per Day 0 decision (skip standalone §10)
\input{sections/conclusion}

% --- Bibliography ---
\bibliography{bibliography}

% --- Optional biographies (Day 6 of 8-day plan; placeholder) ---
% \begin{biography}[photo]{author-name} ... \end{biography}

\end{document}
```

### 2.2 Required IEEEtran package inventory (verified at Day 3 start)

| Package | Used for | Verified via |
|---|---|---|
| `IEEEtran.cls` | TNNLS class file | `kpsewhich IEEEtran.cls` → `texlive-publishers/.../IEEEtran.cls` |
| `inputenc [utf8]` | Unicode | always loaded |
| `fontenc [T1]` | T1 encoding | always loaded |
| `amsmath, amssymb, amsthm` | Lemma environments + math symbols | standard |
| `algorithm`, `algpseudocode` | Pseudocode for §4 scheduler family | standard |
| `booktabs` | `\toprule`, `\midrule`, `\bottomrule` for tables | standard |
| `graphicx` | `\includegraphics` for figures | standard |
| `hyperref` | Hyperlinked cross-references | standard |
| `url` | URL typesetting | standard |
| `xcolor` | Color in tables/figures | standard |
| `microtype` | Typography refinement | standard |

### 2.3 Theorem-environment mapping (per wave301-day2-execution-plan.md §6.2)

| Day-2 prose artifact | LaTeX environment | Paper section | Reference |
|---|---|---|---|
| Lemma 1 (SchedulerProtocol closure) | `\begin{lemma} ... \end{lemma}` | §3 Framework, "Protocol Algebra" | `protocols.py:157-273` |
| Lemma 2 (PolicyDriverProtocol polarity) | `\begin{lemma} ... \end{lemma}` | §3 Framework, "Protocol Algebra" | `policy_driver.py:181-285` |
| Lemma 3 (MergeOperator bounded contract) | `\begin{lemma} ... \end{lemma}` | §3 Framework, "Protocol Algebra" | `merge_operator.py:248-340` |
| Lemma 4 (RestartBlender convex combination) | `\begin{lemma} ... \end{lemma}` | §3 Framework, "Protocol Algebra" | `blender.py:425-470` |
| Lemma 5 (CapabilityToken closed-set) | `\begin{lemma} ... \end{lemma}` | §5 Adapter Protocol, "Handshake Correctness" | `engine.py:1273-1313` |
| Lemma 6 (Typed four-port auto-wrap) | `\begin{lemma} ... \end{lemma}` | §5 Adapter Protocol, "Migration Correctness" | `condition.py:33-507` |
| Sketch 1 (SM byte-determinism) | `\begin{sketch} ... \end{sketch}` | §3 Framework, "State-Machine Determinism" | `state_machine.py:832-911` |
| Sketch 2 (Ledger integrity) | `\begin{sketch} ... \end{sketch}` | §3 Framework, "Ledger Integrity" | `engine.py:455-613` |
| Sketch 3 (Handshake diagnosability) | `\begin{sketch} ... \end{sketch}` | §5 Adapter Protocol, "Error Diagnosability" | `engine.py:1273-1313` |

### 2.4 Figure inventory (4 placeholders, paste-verbatim from `tnnls_submission/figures.md`)

| Figure | Source | Inline-render strategy |
|---|---|---|
| Figure 1 — FlowA hexagonal architecture | `tnnls_submission/figures.md` lines 9-71 | TikZ re-draw OR `verbatim` for plain-text |
| Figure 2 — Re-inference dataflow | `tnnls_submission/figures.md` lines 75-... | TikZ re-draw |
| Figure 3 — 3-tier experiment hierarchy | `tnnls_submission/figures.md` (Figure 3) | TikZ re-draw |
| Figure 4 — 4-arm H2H schematic | `tnnls_submission/figures.md` (Figure 4) | TikZ re-draw |

**Strategy decision (Day 3 hour 1-2):** TikZ re-draw (~2 hours effort, scales to 300dpi in PDF) is preferred over `\begin{verbatim} ... \end{verbatim}` ASCII-include (looks unprofessional in TNNLS). All 4 figures are structural diagrams — well-suited for TikZ.

### 2.5 Table inventory (3-4 tables in main text)

| Table | Section | Source-of-truth |
|---|---|---|
| Table 4.1 — Scheduler taxonomy (13 schedulers, family column + register-key column per Wave 294 P2 M-MED-2) | §4 | `wave294-p2-medium-fixed.md` |
| Table 5.1 — 5-adapter vendor-friendly protocol (capability surface + 0-line vendored-change) | §5 | `wave296-p1-architecture.md` + `tnnls_submission/tables.md` |
| Table 7.1 — 11-cell systematic-evidence grid (6-column rubric) | §7 | `wave297-p5-empirical-rewritten.md` |
| Table 7.2 — 6-column Bonferroni table (4 Bonferroni families + 3-seed pool, per Wave 297 P5 §7.3) | §7 | `wave297-p5-empirical-rewritten.md` + `verification_outputs/wave234-*.csv` |

### 2.6 Bibliography inventory (`bibliography.bib`)

**Target: 30-50 references.** Coverage required:

| Domain | Min references | Examples |
|---|---|---|
| Flow matching foundations | 4-5 | Lipman 2023, Liu 2022 (Rectified Flow), Albergo & Vanden-Eijnden 2023 |
| FM inference acceleration | 4-5 | Song 2021 (DDIM), Lu 2022 (DPM-Solver, DPM-Solver++), Karras 2022 (EDM), Song 2023 (Consistency Models), Liu 2022 (ReFlow/InstaFlow), Salimans & Ho 2022 (Progressive Distillation), Luo 2023 (LCM) |
| SOTA 2026 models | 3-4 | Kanzi (ICLR 2026), LineageFlow (ICML 2026), FlowMol3 (NeurIPS 2024) |
| Typed ML systems | 3-4 | PEP 544 (Protocols), Miller 2006 (capability-based security), TensorFlow typed tensors, PyTorch dispatcher protocol |
| Reproducibility & byte-stability | 2-3 | D.4 regression suite paper, SHA-256 hash chain, Wilson et al. 2017 (good enough practices) |
| FID / perceptual metrics | 1-2 | Heusel 2017 (FID), Zhang 2018 (LPIPS) |
| Statistical methods | 2-3 | Bonferroni 1935, Benjamini-Hochberg 1995, TOST (Schuirmann 1987) |
| ODE solvers | 2-3 | Dormand-Prince RK45, Heun, exponential integrators |

**Bibliography file path:** `docs/drafts/bibliography.bib` (NOT inside `tnnls_submission/` — kept in drafts to avoid double inclusion).

### 2.7 Page-count verification gate

**TNNLS limit: 14 pages TOTAL** (main text + figures + tables + bibliography + author bios). Per `wave299-paper-a-outline.md` §5 + `wave300-p3-resolution-plan.md` line 156 (DS-06):

| Page block | Estimated pages | Source |
|---|---|---|
| Title + author + abstract | 0.5 | IEEEtran default |
| §1 Introduction | 1.5 | 600-700 words prose + 1 figure reference |
| §2 Related Work | 1.0 | 600-800 words prose + no figures |
| §3 Framework (incl. Lemmas 1-4 + Sketches 1-2) | 2.0 | 800-900 words + 5 lemma/2 sketch environments |
| §4 Scheduler Family | 1.0 | 500-600 words + Table 4.1 |
| §5 Adapter Protocol (incl. Lemmas 5-6 + Sketch 3) | 1.0 | 550-650 words + Table 5.1 |
| §7 Empirical Results | 2.0 | 800-900 words + Table 7.1 + Table 7.2 + Figure 3 |
| §8 Reproducibility | 0.5 | 600-800 words + no figures (refs Figure 4 separately) |
| §9 Limitations (incl. folded §10) | 0.5 | 300-400 words + no figures |
| §11 Conclusion | 0.5 | 250-300 words + no figures |
| Bibliography (30-50 refs IEEEtran numeric) | 1.5-2.5 | numbered references |
| Author bios (Day 6 user input placeholder) | 0.5 | placeholder until Day 6 |
| **TOTAL** | **~12-14** | **FITS** |

**Verification command (Day 3 Phase A.12):**

```bash
cd docs/build_pdf/
pdflatex paper.tex   # generates paper.aux, paper.log, paper.pdf
bibtex paper         # generates paper.bbl
pdflatex paper.tex   # resolves bibliography references
pdflatex paper.tex   # final pass
pdfinfo paper.pdf | grep "Pages:"   # verify ≤14
```

**Acceptance criterion:** `pdfinfo paper.pdf` reports `Pages: N` where `N ≤ 14`. If N > 14, agent must trim prose and re-typeset (typical trim target: remove redundant prose in §3/§5 lemma bodies).

---

## 3. Cross-Reference Update Pass (Phase B)

### 3.1 Audit-doc enumeration (mechanical step)

**Command (Day 3 Phase B.1):**

```bash
grep -rn "paper-flat-flattened.md:L[0-9]" docs/audit/ > docs/audit/wave301-cross-ref-update-list.md
```

**Expected output: ~15 audit docs** referencing legacy line ranges, per `wave301-day1-execution-plan.md` §4.1:

| Audit doc | Legacy line ranges cited | Action |
|---|---|---|
| `wave297-p1-paper-inventory.md` | 1-15, 23-67, 71-258, 259-400, 401-422, 486-620, 624-755, 758-841 | Update to canonical post-RESOLUTION ranges |
| `wave297-final.md` | 1-15, 23-67, 71-258, 259-400, 401-422 | Update |
| `wave297-p7-readme-updated.md` | 1-15, 71-258, 259-400, 423-484 | Update |
| `wave298-final.md` | 1-15, 23-67, 71-258, 259-400, 401-422, 486-620, 624-755, 758-841 | Update |
| `wave298-p7-paper-append.md` | 23-67 (MS.di.6, MS.di.8), 71-258, 259-400, 401-422, 423-484, 486-620, 624-755, 758-841, 848-1083 | Update; §MS.di.8 cross-reference table + self-references in MS.di.10 + MS.di.11 |
| `wave291-final.md` | 71-258 (Codim CIFAR-10 verdict citation) | Update |
| `wave291-p5-3seed-results.md` | (7.3 statistical methodology source) | (no line refs; not in update list) |
| `wave292-final.md` | 71-258 | Update |
| `wave292-p2-config-genealogy.md` | (7.4 framework-not-theory source; no line refs) | (not in update list) |
| `wave293-p1-locate-sign.md` | 71-258 (cosine sign location) | Update |
| `wave293-p2-verify-direction.md` | 71-258 | Update |
| `wave293-p3-fix-applied.md` | 71-258 | Update |
| `wave293-p4-related-docs.md` | 71-258 | Update |
| `wave293-final.md` | 71-258 | Update |
| `wave294-final.md` | 71-258, 259-400 | Update |
| `wave294-p1-re-inventory.md` | 71-258 | Update |
| `wave294-p2-medium-fixed.md` | 71-258 | Update |
| `wave294-p3-low-paper-fixed.md` | 71-258 | Update |
| `wave294-p4-cross-verify.md` | 71-258 | Update |
| `wave299-paper-a-outline.md` | 259-400 | Update |

**Total audit docs to update: ~17** (some docs are not in `wave301-day1-execution-plan.md` §4.1 list but grep will find them).

### 3.2 Update procedure (Phase B.2)

**Mechanical update strategy:**

1. Open each audit doc.
2. Use `grep -n "paper-flat-flattened.md:L[0-9]"` to enumerate line ranges cited.
3. Map legacy ranges to canonical post-RESOLUTION ranges via a translation table (Day 3 hour 0-1 pre-computation):

| Legacy range | Canonical post-RESOLUTION range | Action |
|---|---|---|
| `L1-L4` | `L1-L1` (Title collapsed to 1 line) | Edit |
| `L7-L12` | `L3-L3` (Abstract collapsed to 5-sentence single paragraph) | Edit |
| `L23-L67` | `L5-L25` (§1 Introduction collapsed) | Edit |
| `L71-L258` | `L28-L72` (§3+§4+§5 framework promoted) | Edit |
| `L259-L400` | `L73-L95` (§7 Empirical Results promoted) | Edit |
| `L401-L422` | `L96-L100` (§9 Limitations promoted) | Edit |
| `L423-L484` | (DELETED — workflow-internal) | Edit to "DEL: §5 Flattening workflow-internal" |
| `L486-L620` | absorbed into `L28-L72` | Edit |
| `L624-L755` | absorbed into `L73-L95` | Edit |
| `L758-L841` | absorbed into `L96-L100` | Edit |
| `L848-L1083` | DELETED (Wave 298 P7 fold-in → canonical §3/§4/§5) | Edit to "Wave 298 P7 fold-in: see canonical §3/§4/§5" |
| `L1087-L1404` | partial fold into canonical, partial cleanup | Edit to "Wave 300 P5 fold-in: see canonical sections" |

4. Use `sed` or manual edit to update each line-range reference.
5. For per-edit verification: re-grep the audit doc to confirm no legacy ranges remain.

**Time estimate:** ~30 minutes per audit doc × 17 docs = ~8.5 hours. This is a significant Phase B cost; consider running 3 parallel agents (per audit-doc cluster) to compress to ~3 hours.

### 3.3 Claims-anchoring verification (Phase B.3)

After all audit doc updates, re-run:

```bash
python3 tools/check_claims_consistency.py
```

**Acceptance criterion:** `61 active / 0 provisional / 2 deprecated / CLM-040 forced PROVISIONAL / No drift detected`. If drift detected, identify which claim lost its anchor line; re-anchor to canonical line; re-run.

### 3.4 mkdocs verification (Phase B.4)

```bash
mkdocs build --strict
```

**Acceptance criterion:** `exit_code=0, 0 project warnings`. If new warnings, fix cross-reference resolution in `docs/` (not `docs/audit/` — that's research output, not the docs site).

---

## 4. TNNLS Submission Package (Phase C)

### 4.1 Package contents (per `tnnls_submission/MANIFEST.md`)

| File | Status (Day 3 entry) | Refresh action |
|---|---|---|
| `MANIFEST.md` | Refreshes with new SHA-256 + sizes after paper.pdf + source.zip generation | REWRITE SHA + SIZE columns |
| `cover_letter.md` | Existing (17 `[USER TO FILL: ...]` placeholders; per `FILL_GUIDE.md`); NOT filled by Day 3 | NO action Day 3 (Day 6 user-input phase in 8-day plan) |
| `highlights.md` | Existing (3 × 85-char highlights) | VERIFY char counts (each ≤ 85) |
| `tables.md` | Existing (5 paper tables, paste-verbatim) | NO action Day 3 |
| `figures.md` | Existing (5 ASCII figures) | VERIFY each figure renders to TikZ in Day 3 Phase A.4 |
| `data_availability.md` | Existing | NO action Day 3 |
| `submission_checklist.md` | Existing | NO action Day 3 |
| `FILL_GUIDE.md` | Existing (17-fillable-fields guide) | NO action Day 3 |
| `paper.pdf` | PLACEHOLDER (copied from `docs/paper-eaai.pdf` per MANIFEST.md line 28) | REPLACE with Day 3 IEEEtran output ≤14 pages |
| `source.zip` | NEW | GENERATE on Day 3 (Phase C.7) |
| `highlight_blurb.pdf` | NEW | GENERATE on Day 3 (Phase C.9) |

### 4.2 Package assembly steps (Phases C.1-C.10)

**Phase C.1 — MANIFEST refresh prerequisites**

After all of the following are regenerated, refresh MANIFEST.md:

```bash
cd tnnls_submission/
sha256sum -- *.md > MANIFEST.sha256
sha256sum ../docs/paper-tnnls.pdf >> MANIFEST.sha256
sha256sum source.zip >> MANIFEST.sha256
sha256sum highlight_blurb.pdf >> MANIFEST.sha256
```

**Phase C.7 — source.zip generation**

```bash
cd /home/hugo/codes/flowa-multistep-reinference
zip -r tnnls_submission/source.zip \
  docs/drafts/paper.tex \
  docs/drafts/bibliography.bib \
  docs/drafts/figures/ \
  docs/build_pdf/paper.pdf \
  docs/drafts/paper-flat-flattened.md \
  site/build_pdf/md_to_tex.py \
  site/build_pdf/IEEEtran.cls 2>/dev/null || true
```

**Phase C.8 — paper.pdf copy**

```bash
cp docs/build_pdf/paper.pdf docs/paper-tnnls.pdf
cp docs/build_pdf/paper.pdf tnnls_submission/paper.pdf
```

**Phase C.9 — highlight_blurb.pdf generation**

Use a small standalone LaTeX document compiling 3 highlight bullets + abstract + author bios placeholders to a single-page PDF for Editorial Manager "Highlights" paste:

```latex
\documentclass{article}
\usepackage[margin=1in]{geometry}
\begin{document}
\noindent\textbf{Highlight 1:} [from tnnls_submission/highlights.md]\\
\textbf{Highlight 2:} [from tnnls_submission/highlights.md]\\
\textbf{Highlight 3:} [from tnnls_submission/highlights.md]
\end{document}
```

**Phase C.10 — MANIFEST SHA refresh**

After Phases C.7-C.9, regenerate MANIFEST.md with current SHA-256 + sizes for each file. Sidecar note: `docs/audit/wave274-p7-manifest-sha.md` documents the self-referencing-SHA pattern — replicate for Day 3.

### 4.3 Submission package verification (Day 3 end-of-day gates)

| Gate | Command | Expected |
|---|---|---|
| paper.pdf page count | `pdfinfo tnnls_submission/paper.pdf \| grep "Pages:"` | ≤14 |
| MANIFEST hashes | `cd tnnls_submission && sha256sum -- *.md` | each matches column entry |
| cover_letter placeholders | `grep -nE 'USER.TO.FILL' tnnls_submission/cover_letter.md \| wc -l` | 14 (only §0 documentation pointers) |
| highlights char count | `awk '{print length}' tnnls_submission/highlights.md` (each bullet line) | ≤85 chars per bullet |
| source.zip contents | `unzip -l tnnls_submission/source.zip \| tail -20` | paper.tex, bibliography.bib, figures/, IEEEtran.cls present |

---

## 5. Paper B Skeleton (Phase D)

### 5.1 Paper B directory layout

```
docs/drafts/paper-b-jmaa/
├── README.md                      # Paper B scope + boundary against Paper A
├── skeleton.md                    # §1 Introduction (200-400w) + 11-section outline
├── experiments.md                 # 10-experiment list with GPU-hour estimates
├── regime-sweep.md                # 3-tier (easy/medium/hard) prerequisite
├── contributions.md               # 4-6 primary contributions list
├── refs/
│   └── refs.md                    # BibTeX stub for Paper B references
└── figures/                       # (empty; left for Day 9 figures)
```

### 5.2 §1 Introduction skeleton (Paper B)

**Title:** "Paper-Quantity-Driven Scheduling and Convergence Analysis for Re-Inference in Flow Matching: A Theoretical Companion to FlowA"

**Boundary statement:** "This paper extends FlowA [cite Paper A] by focusing on the theory of paper-quantity-driven scheduling and the empirical convergence behavior at the per-round capacity boundary. Where Paper A presents the framework as a training-free, solver-agnostic system with 4 typed Protocols, 13 schedulers, and 11-cell empirical validation, this companion paper analyzes the BL-convergence rate bound (Theorem 1) at finite NFE and provides the regime-sweep evidence needed to characterize when paper-quantity-driven scheduling activates the framework's theoretical potential. The two papers share the framework code base but report different research questions."

**Three paragraphs (200-400 words total):**

- **Paragraph 1 (60-100w):** Differentiate from Paper A. State that Paper B is the theoretical companion; Paper A is the framework paper. Cite Paper A.
- **Paragraph 2 (80-150w):** State the 4-6 Paper B contributions (see §5.3).
- **Paragraph 3 (60-150w):** Cite the 10 Paper B experiments (see §5.4) and the regime-sweep prerequisite (see §5.5).

### 5.3 Paper B primary contributions (4-6)

| # | Contribution | Maps to | Paper B section |
|---|---|---|---|
| 1 | **JMAA Theorem 1 four-paper-quantities specification** | `planar_bl_convergence_witness.py` + `docs/theory/theorem-1-self-contained.md` | §3 Theoretical Framework |
| 2 | **CodimensionSheetScheduler specialized-regime sweep** | `adaptive_reflow/algorithm/scheduler/codim_sheet_scheduler.py` | §4 Scheduler Specialization |
| 3 | **Paper-quantity-driven scheduler family** (12 specialized schedulers beyond Paper A's 9 baselines) | new `adaptive_reflow/algorithm/scheduler/paper_quantity/` | §4 Scheduler Specialization |
| 4 | **16-site integration verification** (16 production deployments serving FlowA) | `data/sites/` + `verification_outputs/sites_*.json` | §5 Production Integration |
| 5 | **Convergence analysis (Path B conditional)** | `planar_bl_convergence_witness.py` + `verification_outputs/convergence_*.csv` | §6 Convergence Analysis |
| 6 | **FID Δ=0% evidence** for "framework activates only when specialized schedulers are invoked" | Wave 235 P2-P3 + Kanzi R2 / R6k6 large-effect uplifts | §7 Activated-Framework Evidence |

### 5.4 Paper B 10-experiment plan (~35 GPU-hours total)

| # | Experiment | GPU-hours | Purpose | Source-of-truth |
|---|---|---|---|---|
| 1 | Kanzi specialized-scheduler sweep (3 schedulers × 4 tiers × 5 seeds × N=200) | 6.0 | Paper B's primary protein-pillar validation | Wave 235 P2 |
| 2 | LineageFlow specialized-scheduler sweep (2 schedulers × 3 tiers × 3 seeds × N=300) | 4.5 | Composite-axis byte-stable validation | Wave 235 P3 |
| 3 | FlowMol3 specialized-scheduler sweep (1 scheduler × 3 tiers × 5 seeds × N=500) | 5.0 | Molecular-3D reactivity validation | Wave 235 P3 |
| 4 | 2D Two Moons regime-sweep boundary (3 schedulers × 7 NFE × 3 seeds × N=500) | 3.0 | Convergence-boundary identification | Wave 35 saturation |
| 5 | 2D Eight Gaussians regime-sweep boundary (3 schedulers × 7 NFE × 3 seeds × N=500) | 3.0 | Convergence-boundary identification | Wave 35 saturation |
| 6 | CIFAR-10 RF matched-NFE boundary (2 schedulers × 5 NFE × 5 seeds × N=200) | 4.0 | FID-Δ=0% evidence | Wave 235 P1 |
| 7 | MNIST FM regime-sweep (2 schedulers × 3 tiers × 3 seeds × N=200) | 1.5 | Statistical pre-registration | Wave 234 |
| 8 | BL-distance per-round rate measurement (3 schedulers × 10 rounds × 5 seeds) | 2.0 | Path B convergence rate bound | `planar_bl_convergence_witness.py` |
| 9 | 16-site integration consistency check (16 sites × 3 seeds × N=10 smoke) | 4.0 | Production integration verification | `data/sites/` |
| 10 | Tier-stratified ablation (3-tier qualitative × 5 conditions × N=200) | 2.0 | Activated-framework boundary | Wave 35 + Wave 33 |
| **TOTAL** | — | **35.0** | — | — |

**GPU assumption:** 1 GPU = PRO 6000 98GB or 5090 32GB (per Wave 301 plan constraints). Sequential or 2-GPU parallel.

### 5.5 Regime-sweep prerequisite

**3-tier stratification (per Wave 33/35):**

| Tier | Definition | Typical metric range | Examples |
|---|---|---|---|
| **Easy** | Baseline-metric quantile < 0.33 (fast/easy samples) | FID < 20, RMSD < 2Å, d_z baseline < 0.1 | CIFAR-10 RF small-N; LineageFlow low-difficulty |
| **Medium** | Baseline-metric quantile ∈ [0.33, 0.67] | FID 20-40, RMSD 2-4Å | Kanzi R2 medium-effect regime |
| **Hard** | Baseline-metric quantile > 0.67 (hard samples) | FID > 40, RMSD > 4Å | Kanzi R6 k6 large-effect regime |

**Prerequisite:** Every Paper B experiment MUST stratify samples into 3 tiers via baseline-metric quantile (per Wave 233 P3 + Wave 235 P2-P3). This is the "regime-sweep" pattern that separates Paper A's tier-aware findings from Paper B's tier-stratified analysis.

**Verifier command:**

```bash
# Verify tier-stratification is consistent across Paper B experiments:
for exp_id in 01 02 03 04 05 06 07 08 09 10; do
  echo "=== Experiment $exp_id tier-split check ==="
  grep -l "tier_aware\|easy_tier\|medium_tier\|hard_tier" \
    docs/drafts/paper-b-jmaa/experiments.md 2>/dev/null || \
    echo "  MISSING: tier_stratification reference"
done
```

### 5.6 Git branch creation (Phase D.7)

```bash
cd /home/hugo/codes/flowa-multistep-reinference
git checkout -b paper-b-skeleton
git add docs/drafts/paper-b-jmaa/
git commit -m "Wave 301 Day 3: Paper B skeleton (no Paper A edits; separate branch)"
```

**CRITICAL:** Paper B skeleton MUST be on a separate branch (`paper-b-skeleton`), NOT on `main`. This prevents interference with Paper A's submission freeze.

---

## 6. Execution Sequencing (Day 3 hour-by-hour, ~12-14 hours wall-clock)

| Hour | Phase | Task | Deliverable | Gate |
|---|---|---|---|---|
| 0-1 | Pre-flight | Re-verify Day 2 output: paper is ~1069 lines, 11 sections, 4800-5500 words, 5-gate baseline passes | `wave301-day3-baseline-verify.md` | 5-gate baseline |
| 1-2 | A.1-A.2 | Write `paper.tex` skeleton: IEEEtran class preamble + section \input directives + bibliography hook | `docs/drafts/paper.tex` (skeleton ~200 lines) | LaTeX preamble passes static review |
| 2-4 | A.3-A.4 | Convert §3 Framework + §5 Adapter Protocol prose into LaTeX with 6 lemma + 3 sketch `\begin{...}` environments | updated `paper.tex` (sections 3 + 5) | 9 theorem envs documented |
| 4-5 | A.5-A.8 | Convert remaining sections (1, 2, 4, 7, 8, 9, 11) prose + 4 tables + 4 figure placeholders | full `paper.tex` | All 11 sections + 4 tables + 4 figures present |
| 5-6 | A.6 + TikZ | Re-draw 4 figures in TikZ (from ASCII `figures.md`) | `docs/drafts/figures/*.tex` | TikZ renders match ASCII |
| 6-7 | A.10 | Write `bibliography.bib` with 30-50 references | `docs/drafts/bibliography.bib` | BibTeX parses without warnings |
| 7-9 | A.11-A.12 | Run `pdflatex` × 4 (compile + bibtex + 2 re-passes); verify page count ≤14; fix any overfull hbox | `docs/build_pdf/paper.pdf` ≤14 pages | pdfinfo Pages N ≤14 |
| 9-10 | B.1-B.4 | Run cross-ref update pass on ~17 audit docs; re-run claims_consistency + mkdocs strict | 17 audit docs updated + 2 gates | 5-gate suite PASS |
| 10-11 | C.1-C.10 | Refresh `tnnls_submission/MANIFEST.md` + generate `source.zip` + copy paper.pdf to tnnls_submission/ | `tnnls_submission/source.zip` + `MANIFEST.md` (refreshed) | SHA-256 columns match on-disk |
| 11-12 | D.1-D.7 | Create `docs/drafts/paper-b-jmaa/` + write `skeleton.md` + `experiments.md` + `regime-sweep.md` + `contributions.md` + `refs/refs.md`; commit to `paper-b-skeleton` branch | 5 files + git branch created | branch exists; no conflicts with main |
| 12-13 | Final verify | Run 5-gate suite + `pdfinfo` on paper.pdf + SHA check on MANIFEST; produce `wave301-day3-finalize-run-log.md` | `wave301-day3-finalize-run-log.md` | all Day 3 gates PASS |
| 13-14 | User review | Present to user: paper.pdf, MANIFEST.md, source.zip, Paper B skeleton files. **USER DECISION REQUIRED**: approve package for Day 4 ScholarOne upload OR request edits | user sign-off | boundary clearness + submission readiness |

**Total: 13-14 hours wall-clock.**

**Coverage-depth tradeoffs (explicit):**

- TikZ re-draw of 4 figures in 1 hour is aggressive — if figures exceed 2 hours, defer 1-2 figures to supplementary (still maintains 11-page main-text cap).
- Cross-ref updates on 17 audit docs in 1 hour requires 3 parallel agents; if running single-agent, this expands to 4-6 hours and pushes Paper B skeleton to Day 4.
- `bibliography.bib` 30-50 references in 1 hour requires verbatim extraction from `docs/drafts/related-work*.md` + quick Wikipedia/arXiv verification; if some references lack BibTeX, defer to Day 4 polish.

---

## 7. Verification Strategy (5-gate + Day-3-specific gates)

### 7.1 Re-run 5-gate suite (must pass)

| Gate | Command | Expected |
|---|---|---|
| D.4 30/30 | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30 passed, ≤3 pre-existing DeprecationWarnings |
| ruff 0 | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | All checks passed! |
| mkdocs strict 0 | `mkdocs build --strict` | exit_code=0, 0 project warnings |
| claims no drift | `python3 tools/check_claims_consistency.py` | no drift detected (61 active / 0 provisional / 2 deprecated) |
| vendored untouched | `git diff --stat -- vendored/ data/` | (empty) |

**Day 3 caveat:** Day 3 produces `paper.tex` (new file), `bibliography.bib` (new file), `tnnls_submission/source.zip` (new archive), `tnnls_submission/MANIFEST.md` (refreshed), `paper-b-jmaa/*` (new directory). These do not affect the gates because they are: documentation (not framework code), claims-anchor targets (paper-flat-flattened.md stays unchanged through Day 3), or vendored-untouched (no edits to vendored/ or data/).

### 7.2 Day-3-specific gates

| Gate | Method | Expected |
|---|---|---|
| paper.pdf page count | `pdfinfo docs/build_pdf/paper.pdf \| grep "Pages:"` | ≤14 pages |
| paper.pdf renders correctly | Open in PDF viewer; verify all sections + tables + figures + bibliography present | All 11 sections + 4 figures + 3-4 tables + bibliography visible |
| Bibliography renders | Verify `\bibitem` entries appear in IEEEtran numeric style | 30-50 entries |
| Lemma environments | `grep "\\\\begin{lemma}" docs/drafts/paper.tex \| wc -l` | 6 |
| Sketch environments | `grep "\\\\begin{sketch}" docs/drafts/paper.tex \| wc -l` | 3 |
| Theorem environments total | `grep -E "\\\\begin\{(lemma\|sketch)\}" docs/drafts/paper.tex \| wc -l` | 9 |
| MANIFEST SHA consistency | `cd tnnls_submission && sha256sum -- *.md && diff -u MANIFEST.md <(sha256sum -- *.md)` | (empty diff) |
| Cross-ref update completeness | `grep -rn "paper-flat-flattened.md:L[0-9]" docs/audit/ \| grep -E "L(1-4|7-12|23-50\|71-258\|259-400\|401-422\|423-484)" \| wc -l` | 0 (all legacy ranges replaced) |
| Paper B boundary | `grep -E "JMAA\|Theorem 1\|paper-quantity-driven" docs/drafts/paper-b-jmaa/skeleton.md \| head -5` | ≥4 distinct references (boundary language preserved) |
| Paper B branch isolation | `git branch --show-current` (when inside paper-b-jmaa directory) | `paper-b-skeleton` (NOT main) |

---

## 8. Risk Register (Day 3 specific)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| IEEEtran class missing from TeX Live install | LOW | HIGH | `kpsewhich IEEEtran.cls` first; if missing, `tlmgr install ieeetran` (per Wave 274 P4 blocked disclosure) |
| pdflatex run has BibTeX warnings (missing entries) | MEDIUM | LOW | Add missing entries to `bibliography.bib` and re-run; cap at 5 warnings max |
| Page count exceeds 14 pages | MEDIUM | MEDIUM | Trim lemma prose bodies (each lemma currently 300-400w; reduce to 250-300w); consolidate tables (combine Tables 4.1+5.1 as "Protocol Surface") |
| TikZ figure re-draw exceeds 2 hours | MEDIUM | LOW | Defer 1-2 figures to supplementary; keep Figure 1 + Figure 4 in main, defer Figure 2 + Figure 3 |
| Cross-ref update pass on 17 audit docs takes >1 hour single-agent | MEDIUM | LOW | Spawn 3 parallel agents per audit-doc cluster (~6 hours wall-clock, but parallel brings to ~2 hours) |
| Source.zip exceeds 50MB (figures too large) | LOW | LOW | Use PNG @ 150dpi instead of 300dpi; or use `\includegraphics` for inline TikZ (no separate file) |
| ICLR 2028 backup venue needs separate paper.tex | LOW | LOW | Day 3 produces TNNLS `paper.tex`; ICLR 2028 backup `paper.tex` deferred to Day 8+ of 8-day plan |
| User review finds Day 2 boundary-clearness check needs revision | MEDIUM | MEDIUM | Day 2 review is MANDATORY before Day 3 begins; if revised, Day 3 must re-start from Phase A with revised sections |

### 8.1 Phase A.12 page-count failure handling

If `pdfinfo` reports `Pages: N > 14`:

1. **Conservative trim**: Reduce each lemma body by 50 words; consolidate Tables 4.1 + 5.1 into one "Protocol Surface" table; remove redundant prose in §3 (collapse "Protocol Algebra" subsection intro by 100 words).
2. **Aggressive trim**: Defer §3 sketches (3 sketches totaling ~1200 words) to supplementary; main §3 retains 6 lemmas + 1 sketch only; supplementary has full 9 lemma/sketch collection.
3. **Last-resort**: Move §2 Related Work to supplementary; main paper §2 is condensed to 1-paragraph citation summary; total main text drops to ~10 pages.
4. **Re-typeset** after each trim step and re-verify page count.

---

## 9. Deliverables Manifest (Day 3 output files)

| File | Size | Purpose | Status |
|---|---|---|---|
| `docs/audit/wave301-day3-execution-plan.md` | THIS DOC | Execution sequencing + IEEEtran checklist + Paper B skeleton | READ-ONLY (input to Day 3 agent) |
| `docs/audit/wave301-day3-baseline-verify.md` | ~200 lines | Day 2 output verification + 5-gate re-baseline | NEW (Day 3 hour 0-1 output) |
| `docs/drafts/paper.tex` | ~5000-6500 lines | IEEEtran typeset Paper A (main) | NEW (Day 3 hours 1-7 output) |
| `docs/drafts/bibliography.bib` | ~1500 lines (30-50 refs) | BibTeX for IEEEtran | NEW (Day 3 hour 6-7 output) |
| `docs/build_pdf/paper.pdf` | ~700KB | Compiled paper PDF ≤14 pages | NEW (Day 3 hours 7-9 output) |
| `docs/paper-tnnls.pdf` | ~700KB | Top-level paper PDF (TNNLS submission target) | REPLACES placeholder (Day 3 hour 10 output) |
| `docs/audit/wave301-cross-ref-update-list.md` | ~100 lines | Audit docs to update with new line ranges | NEW (Day 3 hour 9 output) |
| `docs/audit/wave301-day3-finalize-run-log.md` | ~150 lines | Day 3 final gate verification log | NEW (Day 3 hour 12-13 output) |
| `tnnls_submission/source.zip` | ~5-10MB | Submission source bundle | NEW (Day 3 hour 10 output) |
| `tnnls_submission/paper.pdf` | ~700KB | Submission PDF copy | COPIES from `docs/paper-tnnls.pdf` |
| `tnnls_submission/MANIFEST.md` (refreshed) | ~80 lines | SHA-256 + size + role catalog | REFRESHED |
| `tnnls_submission/highlight_blurb.pdf` | ~50KB | Highlights + abstract + author bios for Editorial Manager | NEW |
| `docs/drafts/paper-b-jmaa/README.md` | ~50 lines | Paper B scope + boundary statement | NEW (Phase D) |
| `docs/drafts/paper-b-jmaa/skeleton.md` | ~600 lines | §1 Introduction + 11-section outline | NEW (Phase D) |
| `docs/drafts/paper-b-jmaa/experiments.md` | ~250 lines | 10-experiment list with GPU-hour estimates | NEW (Phase D) |
| `docs/drafts/paper-b-jmaa/regime-sweep.md` | ~150 lines | 3-tier prerequisite | NEW (Phase D) |
| `docs/drafts/paper-b-jmaa/contributions.md` | ~100 lines | 4-6 primary contributions list | NEW (Phase D) |
| `docs/drafts/paper-b-jmaa/refs/refs.md` | ~80 lines | BibTeX stub | NEW (Phase D) |
| Git branch `paper-b-skeleton` | — | Locked skeleton reference (NOT main) | NEW |

**Total Day 3 output: 13 new files + 4 refreshed files + 1 git branch.**

---

## 10. Hand-off to Days 4-10

### 10.1 Day 4 (per wave301-day0-prompt.md §4 timeline)

- ScholarOne portal accessibility check (Day 4 morning)
- Final reference list cross-check (BibTeX passes pdflatex bibtex without missing-entry warnings)
- Author bios template (placeholder for Day 6 user input)
- Suggested reviewer list compilation (5-8 names from TNNLS editorial scope)
- Cover letter cross-check (all 17 `[USER TO FILL: ...]` placeholders enumerated)

### 10.2 Day 5 (per wave301-day0-prompt.md §4 timeline)

- Figure/table polish (TNNLS quality bar ≥300dpi)
- Supplementary material preparation (full Path A 6-8 lemmas prose-proofs + 16-site integration verification + Wave 286/290/268/296 extended reproducibility record)
- ICLR 2028 backup `paper.tex` (different format: ICLR LaTeX, ≤9 pages main text)

### 10.3 Day 6 (per wave301-day0-prompt.md §4 timeline)

- Author bios finalization (user input on background + affiliation)
- Cover letter fill (all 17 placeholders: authors block + AE + 5 reviewers + corresponding author)
- Suggested-reviewer COI sweep (cross-check each reviewer's recent papers against user + co-author network)

### 10.4 Day 7 (per wave301-day0-prompt.md §4 timeline)

- 5-gate final verification (D.4 30/30 + ruff 0 + mkdocs 0 + claims no-drift + vendored untouched)
- Wave 268 strict-clean audit (destructive-edit log entry signed)
- Final commit on main branch with paper.pdf + supplementary.pdf + paper.tex + bibliography.bib + cover_letter.pdf + author_bios.pdf

### 10.5 Day 8 (per wave301-day0-prompt.md §4 timeline)

- ScholarOne submission package assembly
- Dry-run upload (if available)
- User copyright/DORA workflow finalization
- **FINAL submission to TNNLS**

### 10.6 Days 9-10 (per wave301-day0-prompt.md §4 timeline)

- Day 9: Paper B skeleton polish (no new experiments)
- Day 10: TNNLS first-decision timeline planning (3-5 month realistic, per LetPub data; calendar reminder set)
- Paper B execution plan committed to `docs/audit/paper-b-execution-plan.md`
- Issues opened for Paper B Wave 1 (regime-sweep experiments)

---

## 11. Summary

**Day 3 produces:**

- **Phase A (IEEEtran typesetting):** Convert `paper-flat-flattened.md` → `paper.tex` with `\documentclass[journal]{IEEEtran}`; wrap Lemmas 1-6 + Sketches 1-3 in theorem environments; 4 tables (Table 4.1, 5.1, 7.1, 7.2); 4 figure placeholders (TikZ re-draws of FlowA hexagonal / Re-inference dataflow / 3-tier hierarchy / 4-arm H2H schematic); 30-50-entry `bibliography.bib`; compile to `paper.pdf` ≤14 pages.
- **Phase B (cross-ref update):** Update line-range references in ~17 audit docs from legacy to canonical post-RESOLUTION ranges; re-run 5-gate suite.
- **Phase C (TNNLS submission package):** Refresh `tnnls_submission/MANIFEST.md` SHA-256 + sizes; generate `source.zip`; copy `paper.pdf` to `docs/paper-tnnls.pdf` and `tnnls_submission/paper.pdf` (replacing placeholder); generate `highlight_blurb.pdf`.
- **Phase D (Paper B skeleton):** Create `docs/drafts/paper-b-jmaa/` with `skeleton.md` (200-400w §1 + 11-section outline), `experiments.md` (10-experiment list totaling ~35 GPU hours), `regime-sweep.md` (3-tier prerequisite), `contributions.md` (4-6 primary contributions), `refs/refs.md` (BibTeX stub); commit to `paper-b-skeleton` git branch (NOT main).

**Day 3 is GATED on Day 2 completion** (Path A + §2/§8/§11 fresh-writing + 5-gate baseline + user boundary-clearness review).

**Coverage-depth tradeoff (explicit):** Day 3 IEEEtran typesetting is compressed to 7-9 hours (typical IEEEtran conversion is 14-22 hours) by accepting partial TikZ figure re-draws + bibliography stub quality. Full figure polish + bibliography completeness are deferred to Day 5.

**Verification:** 5-gate suite + Day-3-specific gates (page count ≤14, 9 theorem environments, MANIFEST SHA consistency, 17 audit docs updated, Paper B branch isolation). All required to PASS before Days 4-8 (ScholarOne submission) begin.

---

**END OF DAY 3 EXECUTION PLAN**
