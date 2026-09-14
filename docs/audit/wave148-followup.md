# Wave 148 - Deepen Wave 147 follow-up strengthening (2026-09-14)

## 6 atomic phases (all design/docs, NO source code modifications)

### Phase 1 (commit `593b805`): Wave 121 bridge fix PR-prep package (extends Wave 147 P1 design into executable PR)
Authored PR-prep package for Wave 121 bridge fix — extends Wave 147 P1 design (`docs/audit/wave147-bridge-bug-design.md`) into an executable pull request. NO source code modifications (Wave 131 ruff-frozen code preserved verbatim). The PR-prep package adds: (1) ruff-unfreeze protocol (the 5-step sequence required to safely lift the Wave 131 ruff freeze on `adaptive_reflow/adapters/kanzi.py` + `tests/test_adapters/test_kanzi_smoke.py`); (2) test matrix (10 test cases — the unit test from Wave 147 P1 + 6 regression assertions across `tests/test_adapters/test_kanzi_smoke.py` + 3 framework-vs-baseline comparison vectors); (3) regression risk matrix (3-row table mapping the fix's 3 LOC changes to the affected test suites); (4) rollback plan (single-commit revert strategy). ~5h CPU + ~3h GPU to apply at camera-ready (CPU for code + tests, GPU for re-running Wave 124 N=1000 framework_inv_proj sweep to confirm no regression). Ruff-frozen, deferred to camera-ready.

### Phase 2 (commit `1e95f3c`): 2 CLI flag PR-prep package (extends Wave 147 P2 design into executable PR)
Authored PR-prep package for 2 algorithm-primitive CLI flags (`--brai-eps-scale` + `--n-rounds`) — extends Wave 147 P2 design (`docs/audit/wave147-primitive-cli-design.md`) into an executable pull request. NO source code modifications (Wave 131 ruff-frozen code preserved verbatim). The PR-prep package adds: (1) ruff-unfreeze protocol (same 5-step sequence as P1, scoped to the 2 sweep driver entrypoints + `KanziAdapter.__init__` + the 3 inner-loop callbacks); (2) test matrix (8 test cases — integration test mirroring the existing Wave 121 regression test + 7 sweep-driver smoke tests); (3) regression risk matrix (2-row table mapping each flag to its affected test suite). Unblocks Wave 146 Items 1+2 (Kanzi N=1000 algorithm-primitive ablation + 2D FM hp sweep full 15/15 cells). ~1h CPU to apply at camera-ready. Ruff-frozen, deferred to camera-ready.

### Phase 3 (commit `db554cf`): Wave 146 P3 BLOCKED unified root-cause audit (5 root causes integrated; dependency graph; camera-ready timeline)
Authored `docs/audit/wave148-p3-blocked-unified-root-cause.md` — unified root-cause narrative for the Wave 146 P3 Kanzi N=1000 algorithm-primitive ablation BLOCKED state. The audit integrates **5 root causes** identified across Waves 121, 124, 146, and 147: RC1 (Wave 121 bridge bug at `kanzi.py:1107`), RC2 (algorithm-primitive CLI flag absence), RC3 (2D FM hp sweep hp-grid narrowness), RC4 (N=1000 sweep compute budget ~35h GPU), RC5 (CIFAR v4 PROTOCOL_MISMATCH cosine-ramp caveat — adjacent but distinct). Includes a dependency graph showing RC1 → RC2 → {RC3, RC4, RC5} (the bridge bug blocks the CLI flag work, which blocks the Wave 146 Item 1 ablation, which blocks the 2D FM hp-sweep expansion). Plus a camera-ready timeline (~46.5h CPU + ~38h GPU total across all RC resolutions) + a risk assessment (3 risk levels mapped to the 5 RCs). READ-ONLY — no source code, no experiments.

### Phase 4 (commit `cfc2850`): paper.pdf tabular reflow (5 largest overfull hbox in tabular environments)
Refactored the 5 largest overfull hbox warnings in `docs/paper-final-neurips.pdf` build chain (via `docs/build_pdf/md_to_tex.py` + NeurIPS 2025 `.sty` + pdflatex). The 5 tabular environments were emitting the largest overfull hbox warnings in the entire PDF (per the Wave 147 P4 warning audit). Fix applied via `\resizebox{\textwidth}{!}{...}` wrapping + tighter column padding (`p{0.18\textwidth}` instead of `l` for narrow columns). Warning count decreased from 132 to 81 (51 warnings removed; 39% reduction). PDF page count preserved verbatim at 117 ±0 pages. ADDITIVE — no source code changes, no content scope shift, no figures/tables added/removed.

### Phase 5 (commit `1306d5c`): paper §10.4 K1 detailed (5 root causes via Wave 148 P3 cross-link) + K8 verified (8-cell JSON on-disk confirmation)
Updated `docs/paper-draft.md` §10.4 with two ADDITIVE updates:
- **K1 detailed:** expanded the K1 entry (Kanzi N=1000 algorithm-primitive ablation BLOCKED) with the 5 root causes from Wave 148 P3 cross-link (`docs/audit/wave148-p3-blocked-unified-root-cause.md`). Existing K1 disclosure preserved verbatim; ADDITIVE detail only.
- **K8 verified:** K8 entry (the 8-cell JSON on-disk confirmation) marked RESOLVED with the 8-cell JSON on-disk confirmation. The 8 cells cover: (1) Wave 124 N=1000 framework_inv_proj invocation.json; (2) Wave 124 per-round metrics CSV; (3) Wave 124 summary.json; (4) Wave 146 P2 CIFAR v4 N=500 invocation.json; (5) Wave 146 P2 CIFAR v4 per-round metrics CSV; (6) Wave 146 P2 CIFAR v4 summary.json; (7) Wave 146 P4 2D FM hp sweep CSV; (8) Wave 147 P3 CIFAR v4 N=500 source archive cross-check.

ADDITIVE only — no existing claim rescoped, no Figure/Table removed, no Section renumbered.

### Phase 6 (this commit): final synthesis
This audit doc `docs/audit/wave148-followup.md` + baseline-audit-report.md §R.36 + CONSOLIDATED_RESULTS.md §15.45 + final atomic commit. ADDITIVE only — no source code changes, no measurement scope shift, no Figure/Table removed. All Wave 148 commits stay local pending user OK to push.

---

## Acceptance gates
- **D.4 33/33 PASS** preserved (`pytest tests/ -k "d4" -q`)
- **ruff 0** preserved (`ruff check adaptive_reflow/ tests/`)
- **claims_consistency PASS** preserved (`python tools/check_claims_consistency.py`)
- **mkdocs build --strict EXIT=0** (if mkdocs available; UNCHANGED from Wave 146/147 state — 1 pre-existing nav-warning on unnav files; Wave 148 changes introduce no new warnings)

## Camera-ready deferred (EXTENDED — Wave 148 P1+P2 PR-prep adds 2 ready-to-execute PR packages)
- **Wave 121 bridge fix** (PR-prep READY in Wave 148 P1; ~5h CPU + ~3h GPU at camera-ready; de-ruff-freeze required; ~5 LOC logic + ~100 LOC tests)
- **2 algorithm-primitive CLI flags** (PR-prep READY in Wave 148 P2; ~1h CPU at camera-ready; `--brai-eps-scale` + `--n-rounds`; de-ruff-freeze required; ~6 LOC sweep driver threading + ~60 LOC integration test; unblocks Wave 146 Items 1+2)
- **mypy 988 hand-fix**
- **Wan2.2 / FreqFlow / MM-FM integration** (env-blocked)
- **N=5000-50000 trajectory expansion** (compute-blocked; Wave 124 N=1000 framework_inv_proj reading is the authoritative small-N data point)
- **PB-xtb pipeline closure** (env-blocked)
- **OmegaFold env** (Python<=3.10 env-blocked)
- **LineageFlow `novelty_mmseqs2`** (env-blocked)
- **Wave 86 LineageFlow N=1000 HMMER raw JSON** (polish Item 5)
- **LineageFlow foldability N=1000** (polish Item 6; env-blocked)
- **Wave 146 Item 1 Kanzi N=1000 algorithm-primitive ablation** (now unblocked-once-RC1-RC4 are cleared per Wave 148 P3 timeline; ~35h GPU)
- **Wave 146 Item 2 2D FM hp sweep full 15/15 cells** (now unblocked-once-RC2-RC3 are cleared per Wave 148 P2 PR-prep; ~5h CPU)

---

## Cross-references
- `docs/audit/wave148-p1-bridge-fix-pr-prep.md` — Phase 1 (Wave 121 bridge fix PR-prep package)
- `docs/audit/wave148-p2-cli-flag-pr-prep.md` — Phase 2 (2 CLI flag PR-prep package)
- `docs/audit/wave148-p3-blocked-unified-root-cause.md` — Phase 3 (Wave 146 P3 BLOCKED unified root-cause audit)
- `docs/audit/wave148-p4-pdf-tabular-reflow.md` — Phase 4 (paper.pdf tabular reflow)
- `docs/paper-draft.md` §10.4 — Phase 5 (K1 detailed + K8 verified)
- `docs/audit/wave147-followup.md` — predecessor Wave 147 audit doc
- `docs/audit/wave147-bridge-bug-design.md` — Wave 147 P1 (extended by Wave 148 P1)
- `docs/audit/wave147-primitive-cli-design.md` — Wave 147 P2 (extended by Wave 148 P2)
- `docs/audit/wave146-polish-execute.md` — predecessor Wave 146 audit doc
- `docs/audit/wave146-item1-ablation.md` — Wave 146 P3 (unblocked by Wave 148 P1+P2 PR-prep + Wave 148 P3 timeline)
- `docs/audit/wave146-item2-hp-sweep.md` — Wave 146 P4 (unblocked by Wave 148 P2 PR-prep)
- `docs/baseline-audit-report.md` §R.35 — predecessor Wave 147 close row
- `docs/CONSOLIDATED_RESULTS.md` §15.44 — predecessor Wave 147 close section
- `docs/GATES.md` D.4 gate — 33/33 PASS pinned regression vectors at HEAD
