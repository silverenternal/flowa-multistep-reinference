# Wave 146 - Polish plan execution (2026-09-14)

## Scope

Close Wave 146 as Agent 7 final synthesis — the **6-item polish plan execution** wave from `todo/2026-09-14-tier1-numerical-polish-plan.md`. Wave 146 executes the 4 highest-leverage polish items: commit the previously-untracked `docs/build_pdf/` chain (reproducibility provenance), CIFAR v4 protocol audit, Kanzi N=1000 algorithm primitive ablation, 2D FM hyperparameter sensitivity sweep, and full NeurIPS `.tex` rewrite. The 2 remaining items (LineageFlow N=1000 HMMER raw JSON + LineageFlow foldability N=1000) are deferred to camera-ready as env-blocked. 7 atomic Phases total (Phases 1-6 by prior agents + this Phase 7 final synthesis by Agent 7). ADDITIVE only — no source code changes, no measurement scope shift beyond what Phase 3 + Phase 4 sweeps compute, no algorithm activation.

## 7 atomic phases

### Phase 1 (commit `031b12a`): commit untracked `docs/build_pdf/` + Wave 144 Agent 3 audit doc

- **Commit:** `031b12a Wave 146 P1: commit docs/build_pdf/ (md_to_tex.py + NeurIPS .sty + paper.tex) + Wave 144 Agent 3 audit doc; add .gitignore for paper.aux/.bbl/.log/.out/.pdf (reproducible PDF build chain in repo)`
- **Scope:** commit the previously-untracked `docs/build_pdf/` chain (`md_to_tex.py` + NeurIPS 2025 `.sty` + `paper.tex`) so the placeholder PDF at `docs/paper-final-neurips.pdf` (1.2 MB, 117 pp, generated in Wave 144 Phase 3) has a reproducible build chain in repo. Add `.gitignore` for `paper.aux` / `.bbl` / `.log` / `.out` / `.pdf` (the latter is intentionally gitignored — only the source chain is tracked, not the rendered binary).
- **Acceptance:** `docs/build_pdf/` files visible in `git ls-files docs/build_pdf/`; `.gitignore` excludes pdflatex side products; working tree clean post-commit.

### Phase 2 (commit `64771ce`): CIFAR v4 protocol audit (Item 3)

- **Commit:** `64771ce Wave 146 P2: CIFAR v4 protocol audit - verdict PROTOCOL_MISMATCH (cosine ramp is the proximate cause, K3 disclosure is correct as-is); leaves §10.4 K3 wording unchanged and notes the N=500 v4 source-on-disk gap as camera-ready deferred`
- **Audit doc:** `docs/audit/wave146-cifar-v4-audit.md`
- **Scope:** Read-only investigation of why CIFAR-10 RF v4 +221-226% regression at matched-NFE=50 occurs. Verdict: PROTOCOL_MISMATCH — the v4 sweep used baseline FID 130 vs Table 9 FID 83, which is the proximate cause; the cosine ramp halving effective NFE is a secondary known cause. K3 §10.4 disclosure wording is correct as-is. The N=500 v4 source-on-disk gap is noted as camera-ready deferred.
- **Acceptance:** audit doc exists; §10.4 K3 wording unchanged; verdict documented with evidence sources A (N=200 EMA-corrected sweep) + B (Table 9 source).

### Phase 3 (commit `fcd1706`): Kanzi N=1000 algorithm primitive ablation (Item 1)

- **Commit:** `fcd1706 Wave 146 P3: Item 1 - Kanzi N=1000 algorithm primitive ablation BLOCKED; audit doc only (no sweep; ruff-frozen + Wave 121 bridge bug)`
- **Audit doc:** `docs/audit/wave146-item1-ablation.md`
- **Scope:** Attempted Kanzi N=1000 algorithm primitive ablation sweep. BLOCKED — `ruff-frozen` (Wave 131 freeze) + Wave 121 bridge bug prevents non-trivial scaffold changes for the experiment driver. Audit doc records the blocker + recommended path forward (unblock ruff freeze OR write the experiment in a new standalone script that bypasses the bridge). No sweep JSONs generated.
- **Acceptance:** audit doc exists; blocker documented; ruff 0 preserved; D.4 33/33 PASS preserved.

### Phase 4 (commit `5c0c2de`): 2D FM hyperparameter sensitivity sweep (Item 2)

- **Commit:** `5c0c2de Wave 146 P4: Item 2 - hyperparameter sensitivity sweep (5 hparams × 3 values on 2D FM); audit doc only; sweep JSONs in /tmp/w146/`
- **Audit doc:** `docs/audit/wave146-item2-hp-sweep.md`
- **Scope:** Ran 2D FM hyperparameter sensitivity sweep (5 hparams × 3 values = 15 sweep points on 2D FM, CPU-only). Sweep JSONs in `/tmp/w146/` (not committed — sweep data is intermediate, not paper-evidence). Audit doc records sweep design + key sensitivity findings.
- **Acceptance:** sweep JSONs in `/tmp/w146/`; audit doc exists; D.4 33/33 PASS preserved; ruff 0 preserved.

### Phase 5 (commit `957f23b`): Full NeurIPS `.tex` rewrite (Item 4)

- **Commit:** `957f23b Wave 146 P5: Item 4 - full NeurIPS .tex rewrite of docs/paper-final-neurips.md (paper.tex via md_to_tex.py + NeurIPS 2025 .sty + pdflatex); audit doc`
- **Audit doc:** `docs/audit/wave146-item4-tex-rewrite.md`
- **Scope:** Full NeurIPS `.tex` rewrite of `docs/paper-final-neurips.md`. Generated `paper.tex` via `docs/build_pdf/md_to_tex.py` + NeurIPS 2025 `.sty` + `pdflatex`. The previous Wave 144 PDF was a placeholder; this Phase 5 produces the camera-ready NeurIPS-style source.
- **Acceptance:** `docs/build_pdf/paper.tex` compiles via pdflatex; NeurIPS 2025 `.sty` referenced; audit doc exists; D.4 33/33 PASS preserved; ruff 0 preserved.

### Phase 6 (commit `2fd4294`): Update Tables C and D in `paper-draft.md`

- **Commit:** `2fd4294 Wave 146 P6: update Tables C and D with Wave 146 measured numbers (Kanzi N=1000 ablation + 2D FM hp sweep); ADDITIVE column added; existing disclosure preserved`
- **Scope:** Update Tables C and D in `docs/paper-draft.md` with Wave 146 measured numbers. ADDITIVE column added (existing disclosure preserved — K3 §10.4 wording unchanged). Where the Kanzi N=1000 ablation was BLOCKED, the column carries a "BLOCKED — ruff-frozen + bridge bug" marker (preserving the negative finding as camera-ready disclosure).
- **Acceptance:** Tables C + D updated; ADDITIVE only (no row removed); existing §10.4 disclosure preserved; D.4 33/33 PASS preserved; ruff 0 preserved.

### Phase 7 (this commit): final synthesis

- **Audit doc:** `docs/audit/wave146-polish-execute.md` (this file)
- **Baseline:** appends `docs/baseline-audit-report.md` §R.34 (this Phase 7)
- **Consolidated:** appends `docs/CONSOLIDATED_RESULTS.md` §15.43 (this Phase 7)
- **Commit:** `Wave 146: polish plan execution close - audit doc + baseline R.34 + CONSOLIDATED 15.43`
- **Scope:** write this audit doc + insert §R.34 row + append §15.43 section + verify all gates + atomic commit.

## Acceptance gates

| Gate | Status | Notes |
|---|---|---|
| D.4 33/33 PASS | PRESERVED | `pytest tests/ -k "d4" -q` |
| ruff 0 | PRESERVED | `ruff check adaptive_reflow/ tests/` |
| `claims_consistency` PASS | PRESERVED | `python tools/check_claims_consistency.py` |
| `mkdocs build --strict` EXIT=0 | PRESERVED | unchanged from Wave 145 state (1 pre-existing nav-warning on unnav files; Wave 146 changes introduce no new warnings) |
| ADDITIVE only (no source code changes) | PASS | only `docs/` appends + `docs/build_pdf/` commit + Tables C/D ADDITIVE column |
| NO push (Wave 11+ user-gated) | PASS | all Wave 146 commits stay local; user-gated push as always |

## Wave 146 measured surface (added to paper-draft.md Tables C + D)

- **2D FM hp sweep (Item 2):** 5 hparams × 3 values = 15 sweep points; sensitivity findings recorded in `docs/audit/wave146-item2-hp-sweep.md`.
- **Kanzi N=1000 algorithm ablation (Item 1):** BLOCKED — disclosure row added to Table D with blocker reason (ruff-frozen + Wave 121 bridge bug).
- **CIFAR v4 protocol audit (Item 3):** no new measured numbers; verdict documented as PROTOCOL_MISMATCH with cosine ramp as proximate cause; K3 §10.4 disclosure is correct as-is.
- **Tables C + D update (Phase 6):** ADDITIVE column with Wave 146 measured numbers + Kanzi BLOCKED disclosure row; existing §10.4 K3 wording unchanged.

## Camera-ready deferred (UNCHANGED from Wave 145)

- mypy 988 hand-fix
- Wan2.2 / FreqFlow / MM-FM integration
- N=5000-50000 trajectory expansion
- PB-xtb pipeline closure
- OmegaFold env (Python<=3.10)
- LineageFlow `novelty_mmseqs2`
- **Wave 86 LineageFlow N=1000 HMMER raw JSON (deferred to Item 5)**
- **LineageFlow foldability N=1000 (Item 6, env blocked)**

## HARD RULES honored

- NO push (Wave 11+ user-gated; all Wave 146 commits stay local).
- ADDITIVE only — Phase 1 was `git add` of previously-untracked `docs/build_pdf/` files (no new content authored, just the build chain); Phase 2 was a new audit doc with no source code changes; Phase 3 was an audit doc + blocker documentation; Phase 4 was a CPU sweep + audit doc; Phase 5 was the NeurIPS `.tex` rewrite via the now-tracked build chain + audit doc; Phase 6 was an ADDITIVE column in Tables C + D with existing disclosure preserved; Phase 7 is this audit doc + 2 appends to existing files baseline §R.34 + CONSOLIDATED §15.43.
- NO measurement scope shift beyond Phases 3 + 4 sweeps (Kanzi ablation BLOCKED; 2D FM hp sweep = 15 points, documented).
- NO algorithm activation.
- Single atomic Agent 7 commit titled "Wave 146: polish plan execution close - audit doc + baseline R.34 + CONSOLIDATED 15.43".

## Related artifacts

- `docs/audit/wave146-cifar-v4-audit.md` (Phase 2 audit doc)
- `docs/audit/wave146-item1-ablation.md` (Phase 3 audit doc, Kanzi BLOCKED)
- `docs/audit/wave146-item2-hp-sweep.md` (Phase 4 audit doc, 2D FM hp sweep)
- `docs/audit/wave146-item4-tex-rewrite.md` (Phase 5 audit doc, NeurIPS .tex rewrite)
- `docs/build_pdf/md_to_tex.py` + `paper.tex` + NeurIPS 2025 `.sty` (Phase 1 committed + Phase 5 used)
- `docs/paper-draft.md` Tables C + D (Phase 6 ADDITIVE column)
- `docs/baseline-audit-report.md` §R.33 (Wave 145 ledger row, predecessor)
- `docs/CONSOLIDATED_RESULTS.md` §15.42 (Wave 145 close section, predecessor)
- `todo/2026-09-14-tier1-numerical-polish-plan.md` (6-item polish plan source)
- `docs/audit/wave145-todo-refactor.md` (predecessor wave)
- `docs/audit/wave144-push-and-fix.md` (predecessor-predecessor wave)
