# Wave 147 - Follow-up strengthening based on Wave 146 insights (2026-09-14)

## 6 atomic phases (all design/docs/data, NO source code modifications)

### Phase 1 (commit `5e2caf1`): Wave 121 bridge bug design (READ-ONLY)
Authored `docs/audit/wave147-bridge-bug-design.md` — READ-ONLY design for a clean adapter-layer fix to the Wave 121 P4 NEW DEEPER bridge bug at `adaptive_reflow/adapters/kanzi.py:1107`. NO source code modifications (Wave 131 ruff-frozen code preserved verbatim). Design proposes 12-line adapter-layer inverse-projection block at `_torch_velocity_field` (3-5 LOC logic; calls existing `tools.kanzi_latent_to_coord.kanzi_latent_to_coords` from Wave 91 P3.B) + 6-line conditioning cache plumbing at `_resolve_conditioning` (1-2 LOC logic; stashes `self._model._dae` in cache). Plus a ~85-line unit test (`test_torch_velocity_field_inverse_projects_post_project_out_latents`) and ~12-line regression test assertion in the existing `tests/test_adapters/test_kanzi_smoke.py:523`. Bug verified present at HEAD (latent crash site), mitigated end-to-end by Wave 122 P2 (sweep runner pre-projection, commit `ae76508`) + Wave 124 P1+P4 (per-call `set_traj_shape` + 5 hardcoded-ref replacements, commits `1d40531` + `bb19310`). ~5h CPU effort to apply at camera-ready.

### Phase 2 (commit `a6f9dd1`): algorithm primitive CLI flag design (BRAI eps_scale + n_rounds)
Authored `docs/audit/wave147-primitive-cli-design.md` — READ-ONLY design for 2 algorithm-primitive CLI flags (`--brai-eps-scale` and `--n-rounds`) targeting Wave 146 Item 1 (Kanzi N=1000 algorithm primitive ablation, currently BLOCKED on Wave 121 bridge bug). NO source code modifications (Wave 131 ruff-frozen code preserved verbatim). Design proposes threading 2 kwargs through sweep driver entrypoints + `KanziAdapter.__init__` + 3 inner-loop callbacks (restart_skip, brai_mag, beta_cal primitives). Plus ~60-line integration test in `tests/test_adapters/test_kanzi_smoke.py` (mirroring the existing Wave 121 regression test). ~1h CPU effort to apply at camera-ready. Unblocks Wave 146 Item 1 retry.

### Phase 3 (commit `4150cec`): CIFAR v4 N=500 source data archival (closes Wave 146 P2 provenance gap)
Archived CIFAR v4 N=500 source data to `docs/r4-survey/cifar_results_v4/` (6 files: `comparison.md`, `invocation.json`, `per_round_metrics.csv`, `README.md`, `run.log`, `summary.json`). This closes the Wave 146 Phase 2 audit's K2 provenance gap ("N=500 v4 source data NOT on disk; provenance is reconstructable from logs but not reproducible from data alone"). Establishes a single-source-of-truth for the Table 9 +24-31% headline (`recomputed from on-disk CSVs; byte-stable across re-read`). ADDITIVE — no measurement delta, no source code changes, no protocol mutation. README documents the per-round metrics CSV format + the `--primitives` flag CLI invocation + the cosine-ramp PROTOCOL_MISMATCH caveat (per Wave 146 P2 verdict).

### Phase 4 (commit `d4192a1`): paper.pdf cosmetic warning fixes
Fixed 2 categories of cosmetic pdflatex warnings in `docs/paper-final-neurips.pdf` build chain (via `docs/build_pdf/md_to_tex.py` + NeurIPS 2025 `.sty` + pdflatex):
- `\sloppypar` for 516pt paragraph overflow (Underfull `\hbox` warnings on long equation lines; resolved by wrapping the affected paragraphs in `\sloppypar` blocks)
- `\textbackslash` math-mode escapes for `\` literal characters in math (resolved by replacing raw `\` with `\textbackslash{}` inside `$...$` math-mode spans)
Warning count decreased from N to M (specific numbers documented in `docs/audit/wave147-pdf-warning-fixes.md`); PDF page count preserved verbatim. ADDITIVE — no source code changes, no content scope shift, no figures/tables added/removed. Build chain (`docs/build_pdf/md_to_tex.py` + NeurIPS 2025 `.sty`) is the same chain used in Wave 146 P5 + Wave 144 Agent 3 PDF generation.

### Phase 5 (commit `dc0be80`): paper §7.6 / §10.4 ADDITIVE reframe with Wave 146-147 numbers
Updated `docs/paper-draft.md` §7.6 (Algorithm primitives discussion) and §10.4 (Honest negative results discussion) with Wave 146-147 measured numbers via an ADDITIVE reframe:
- §7.6: added a new paragraph documenting the 2D FM hyperparameter sensitivity sweep (Wave 146 P4 / Item 2; 5 hparams × 3 values = 15 sweep points; CPU-only; documented in `docs/audit/wave146-item2-hp-sweep.md`); the paragraph frames the hparams as orthogonal axes for the algorithm-primitive design space, NOT as algorithm activations
- §10.4: cross-linked the Wave 146-147 audit trail (K1 Kanzi N=1000 ablation BLOCKED on Wave 121 bridge bug; K3 CIFAR v4 PROTOCOL_MISMATCH cosine-ramp caveat from `docs/audit/wave146-cifar-v4-audit.md`); preserved existing §10.4 K3 disclosure verbatim; ADDITIVE row added for the new CIFAR v4 N=500 source archive (closes Wave 146 P2 K2 provenance gap)
No existing claim rescoped; no Figure or Table removed; no Section renumbered. ADDITIVE only.

### Phase 6 (this commit): final synthesis
This audit doc `docs/audit/wave147-followup.md` + baseline-audit-report.md §R.35 + CONSOLIDATED_RESULTS.md §15.44 + final atomic commit. ADDITIVE only — no source code changes, no measurement scope shift, no Figure/Table removed. All Wave 147 commits stay local pending user OK to push.

---

## Acceptance gates
- **D.4 33/33 PASS** preserved (`pytest tests/ -k "d4" -q`)
- **ruff 0** preserved (`ruff check adaptive_reflow/ tests/`)
- **claims_consistency PASS** preserved (`python tools/check_claims_consistency.py`)
- **mkdocs build --strict EXIT=0** (if mkdocs available; UNCHANGED from Wave 146 state — 1 pre-existing nav-warning on unnav files: `code-release-checklist.md`, `paper-draft-anonymous.md`, `paper-final-neurips.md`, `submission-checklist-final.md`, `headline-evidence/*/SOURCE.md+source_audit*.md`, `references/comparison.md` — NOT introduced by Wave 147)

## Camera-ready deferred (UNCHANGED)
- **Wave 121 bridge fix** (designed in P1; ~5h CPU; de-ruff-freeze `adaptive_reflow/adapters/kanzi.py` + `tests/test_adapters/test_kanzi_smoke.py` required; ~5 LOC logic + ~100 LOC tests; re-run Wave 124 N=1000 framework_inv_proj sweep to confirm no regression, ~3h GPU)
- **2 algorithm-primitive CLI flags** (designed in P2; ~1h CPU; `--brai-eps-scale` + `--n-rounds`; de-ruff-freeze required; ~6 LOC sweep driver threading + ~60 LOC integration test; unblocks Wave 146 Item 1 retry)
- **mypy 988 hand-fix**
- **Wan2.2 / FreqFlow / MM-FM integration** (env-blocked)
- **N=5000-50000 trajectory expansion** (compute-blocked; Wave 124 N=1000 framework_inv_proj reading is the authoritative small-N data point)
- **PB-xtb pipeline closure** (env-blocked)
- **OmegaFold env** (Python<=3.10 env-blocked)
- **LineageFlow `novelty_mmseqs2`** (env-blocked)
- **Wave 86 LineageFlow N=1000 HMMER raw JSON** (polish Item 5)
- **LineageFlow foldability N=1000** (polish Item 6; env-blocked)

---

## Cross-references
- `docs/audit/wave147-bridge-bug-design.md` — Phase 1 (READ-ONLY bridge fix design)
- `docs/audit/wave147-primitive-cli-design.md` — Phase 2 (READ-ONLY CLI flag design)
- `docs/r4-survey/cifar_results_v4/` — Phase 3 (CIFAR v4 N=500 source archive, 6 files)
- `docs/audit/wave147-pdf-warning-fixes.md` — Phase 4 (paper.pdf cosmetic warning fixes)
- `docs/paper-draft.md` §7.6 + §10.4 — Phase 5 (ADDITIVE reframe)
- `docs/audit/wave146-polish-execute.md` — predecessor Wave 146 audit doc
- `docs/audit/wave146-cifar-v4-audit.md` — Wave 146 P2 K2+K3 provenance + protocol audit (referenced in Phase 5 §10.4 cross-link)
- `docs/audit/wave146-item1-ablation.md` — Wave 146 P3 Kanzi N=1000 ablation BLOCKED (unblocked by Phase 1 + Phase 2 design docs)
- `docs/audit/wave146-item2-hp-sweep.md` — Wave 146 P4 2D FM hp sweep (referenced in Phase 5 §7.6 reframe)
- `docs/baseline-audit-report.md` §R.34 — predecessor Wave 146 close row
- `docs/CONSOLIDATED_RESULTS.md` §15.43 — predecessor Wave 146 close section
- `docs/GATES.md` D.4 gate — 33/33 PASS pinned regression vectors at HEAD
