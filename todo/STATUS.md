# `todo/STATUS.md` — single source of truth (auto-updated per wave)

**Last updated:** 2026-09-05 (Wave 32 Phase 2 — author `todo/gap-plan-wave32.md` (master plan) + 13 focused `todo/algo-improvement-*.md` plans covering D.4 + E.1 + paper_quantities threading + assert_adapter_compliance + no-scipy + mkdocs nav + stochastic-fm orphan + FlowMol3V2 restart + HF model card pipeline + host_fingerprint + expecttest + Hypothesis derandomize + mutation apply-survivor; appended D.1 shrink to PHASE-3-glue-layer-improvement.md; updated `framework-freeze-checklist.md` MUST-1 summary with Wave 33 plan pointers; updated `framework-internal-metrics.md` B.7 + F.4 additive sentences with plan pointers)

**Previous update:** 2026-09-05 (Wave 32 Agent A — todo audit + gap analysis; **mkdocs --strict FAILING** with 8 unnavmed files; freeze-checklist MUST-1 stale: E.4 + F.6 + G.1 + G.3 + G.6 all flipped PASS since last update)

## Current state (one line)

> **Phase 1 (framework + theory) DONE. Wave 15 MASSIVE HARDENING + Wave 17-18-19-20 framework-depth + Wave 20 DPK45 bug fix + Wave 27 E.4 doc-citation-diff LIVE + Wave 25 F.6 theory 0.533 + Wave 28 G.3 extractor-variance fix + Wave 30 G.1/G.6/G.4 spec-only + Wave 31 F-5 ratio-driven n_cap ALL landed.** Wave 32 Agent A authored `docs/audit/gap-audit.md` (per-task audit of 38 todo files + 11 gaps identified, 7 without plan files).

## Last completed wave (Wave 20, 2026-09-05, NOT YET PUSHED)

2 commits: DPK45 step assembly fix (53e5d52) + Wave 16 Agent C retry (b8ef197).

### Wave 19 (2026-09-05, NOT YET PUSHED) — paper-readiness

3 commits: PHASE-2 (a6e574d) + rerun-wave10 (a37476b) + paper-writeup (2f436f1).

### Wave 18 (2026-09-05, NOT YET PUSHED) — verification rigor

3 commits: C.6 convergence-order (d7cd65b) + C.7 SBC (c0e2fe2) + F.6 mutation testing (6ec3385). **NEW framework bug discovered:** DormandPrinceRK45 claims order 5 but actually O(dt) signature.

### Wave 17 (2026-09-05, NOT YET PUSHED) — algorithmic trio

3 commits: B.7 property-based + Algo D controlled noise injection + operating-regime theory (CRITICAL gap closed).

### Wave 16 (2026-09-05, NOT YET PUSHED) — docs organize

3 exec agents (A=ARCHIVE/figures, B=adr/governance/audit, C=top-level docs). All 16 actions executed.

## Last completed wave (Wave 15, 2026-09-05, NOT YET PUSHED)

7 commits:

| SHA | Subject | Key results |
|---|---|---|
| `43b862d` | Phase 1: F.5 env_hash infra + W3 rescue + mkdocs nav | env_hash.txt + requirements-lock.txt (132 lines) + capture_env_hash.py + adapter-dependencies.md + mkdocs strict passes; W3 37/37 tests pass |
| `a1f8650` | Wave 14 C: 36-uplift isolation tests | 1385-line test_uplifts.py + conftest.py; 36 parametrized tests |
| `04f892c` | Wave 14 C: ABLATION.md v2 | isolation + interaction + cumulative tables |
| `f9d34e1` | B: explicit rate bound theorem | rate_bound.py + theorem1_rate_bound.md + 8 tests (2 must-fail); A.0 statement 21 closes G4 |
| `3ead25f` | A: A.4 + A.7 + B.4 traceability hardening | A.4: 0.171 → **0.938**; A.7: 75% → **87.5%**; B.4: 5 doctests added |
| `4d30f41` | C: D.5 conformance battery + D.3 + importlib hack fix | D.5 LIVE: 90 passed/0 failed; D.3: 13 → 15 adapter files; **importlib hack REMOVED via PEP 562 lazy loader** |
| `e397528` | F: F.2 reproduction flip | F.2: 4/8 → **7/8 REPRODUCED**; Python 3.11 sidecar at /home/hugo/.venv-flowmol311; R6 mirror tool; 4 env_hash_*.txt captured |

## Prior pushed waves

- **Wave 14 (2026-09-05, commit `6d12744`, PUSHED)** — A: re-point Theorem1StatementChecker
- **Wave 12 (2026-09-05, commit `e0238ab`, PUSHED)** — 7 A1 audit fixes + PLANAR_BL_CONSTANT
- **Wave 11 (2026-09-05, commit `ebc0550`, PUSHED)** — JMAA theory refactor + 52 conformance tests

## Next actions (per user "framework depth not enough" 2026-09-05 directive)

5 NEW framework-depth tasks (no overlap with Wave 15):

1. **B.7 property-based testing** — `algo-improvement-property-based-testing.md` — 0% → ≥40% by Wave 16; CPU; ~2-4 hours
2. **C.6 convergence-order verification** — `algo-improvement-convergence-order.md` — SciML test_convergence pattern; GPU; ~4-6 hours
3. **C.7 Simulation-Based Calibration** — `algo-improvement-sbc.md` — Talts et al. 2018; GPU; ~6-12 hours
4. **F.6 ML-aware mutation testing** — `algo-improvement-mutation-testing.md` — quarterly; ~8-24 hours compute
5. **Operating-regime theoretical analysis** — `algo-improvement-operating-regime.md` — **CRITICAL** (framework's core claim); 1-2 weeks math + 1-3 days GPU + 2-4 hours docs

Plus deferred from earlier:
6. **D** `algo-improvement-failure-modes.md` — pending, GPU

## Current unblocked / blocked status

- [DONE] Wave 10: committed, pushed
- [DONE] Wave 11: committed, pushed (Phase 1 done)
- [DONE] Wave 12: committed, pushed (all 7 A1 fixes + acceptance gate)
- [DONE] Wave 13 (2026-09-05): framework-internal-metrics rev 2 (research + ship-ready)
- [DONE] Wave 14 (2026-09-05): A (commit `6d12744`, pushed) + 9 baseline audits
- [DONE] Wave 15 (2026-09-05): 7 commits landed (NOT YET PUSHED)
  - F.5 infra DONE; A.4 sweep DONE (0.171 → 0.938); A.7 fixtures DONE (75% → 87.5%)
  - B.4 doctests DONE; D.5 LIVE; D.3 missing adapters DONE
  - importlib hack REMOVED (real fix)
  - Algo B rate bound theorem DONE (closes G4)
  - F.2 reproduction DONE (4/8 → 7/8 REPRODUCED)
- [IN PROGRESS] Wave 15 Phase 3 verify (re-run baseline audit + confirm all HARD gates)
- [PENDING] 5 NEW framework-depth tasks (B.7, C.6, C.7, F.6, operating-regime)
- [PENDING] Algo D (controlled noise injection; GPU)
- [OPEN] LineageFlow real-ckpt verdict: blocked on `core` source (R5 in F.2)
- [DONE] Wave 27 Agent A: E.4 doc-builder diff job LIVE (`tools/check_doc_paper_refs_diff.py` + `.github/workflows/doc-citation-diff.yml`; 458 functions checked)
- [DONE] Wave 25 Agent B: F.6 theory 0.500 → 0.533 (16/30 killed)
- [DONE] Wave 28 Agent A: G.3 extractor-family variance fix (canonical-extractor reading on MNIST v1 row)
- [DONE] Wave 30 Agent A: G.1/G.6/G.4 spec-only close 3 HARD gates
- [DONE] Wave 30 commit 8944a09: F-1 (sheet_tube_evidence residual) + F-4 (selection_ratio → sheet_vs_cells_proxy) fixed
- [DONE] Wave 31 commit 64429c9: F-5 removed (PaperRatioAdaptiveScheduler + ratio-driven n_cap in CodimensionSheetScheduler)
- [NEW GAP] Wave 32 Agent A: mkdocs --strict FAILING with 8 unnavmed files (5 model_cards + capability_g1_analysis.md + theory/DEVIATIONS.md + 1 other) — B.3 HARD gate at risk; no plan file
- [NEW GAP] Wave 32 Agent A: D.4 (regression vectors) + E.1 (test-coupled 70%) + StochasticFMAdapter enum bug + FlowMol3V2 restart shape — 4 NOT-MET gaps without plan files
- [AUDIT DOC] `docs/audit/gap-audit.md` (Wave 32 Agent A, 2026-09-05): per-task audit + 11-gap table + plan coverage matrix + mkdocs surface
- [WAVE 32 PHASE 2] 2026-09-05: Authored `todo/gap-plan-wave32.md` master plan + 13 focused `todo/algo-improvement-*.md` files covering the 13 gaps identified across Wave 32 Agent A/B/C audits. D.1 shrink appended to PHASE-3-glue-layer-improvement.md. Sidecar updates to `framework-freeze-checklist.md` (MUST-1 summary) + `framework-internal-metrics.md` (B.7 + F.4 additive). All 14 plans include scope, tasks, acceptance, gate, estimated time, risk, and Wave assignment. Wave 33 plans (#1-8): code-level fixes (CPU-only, no GPU). Wave 34 plans (#9-14): tooling improvements (CPU-only, no GPU).

## Files in `todo/` (count + status)

See `todo/README.md` for the full directory tree. Key new files in Wave 15 era:

| File | Status |
|---|---|
| `wave14-result-validation.md` | done |
| `wave15-result-validation.md` | pending (will be created when Phase 3 verify lands) |
| `framework-internal-metrics.md` | rev 2 ship-ready |
| `algo-improvement-env-hash.md` | **done** (Wave 15 Phase 1; commit 43b862d) |
| `algo-improvement-traceability-hardening.md` | **done** (Wave 15 A; commit 3ead25f) |
| `algo-improvement-conformance-battery.md` | **done** (Wave 15 C; commit 4d30f41) |
| `algo-improvement-f2-reproduction.md` | **done** (Wave 15 F; commit e397528) |
| `algo-improvement-rate-bound.md` | **done** (Wave 15 B; commit f9d34e1) |
| `algo-improvement-uplift-isolation.md` | **done** (Wave 15 rescue; commit a1f8650) |
| `algo-improvement-planar-bl-repoint.md` | **done** (Wave 14 A; commit 6d12744) |
| `algo-improvement-failure-modes.md` | **done** (Wave 17 P2 = Algo D; noise_sigma in twodim_fm + docs/CONDITIONS.md) |
| `algo-improvement-property-based-testing.md` | **done** (Wave 17 P1 = B.7; tests/test_property_based/) |
| `algo-improvement-convergence-order.md` | **done** (Wave 18 C.6 + Wave 20 P1 DPK45 fix; 5/5 integrators pass) |
| `algo-improvement-sbc.md` | **done** (Wave 18 C.7; 6/6 stochastic algorithms pass chi-squared) |
| `algo-improvement-mutation-testing.md` | **done** (Wave 18 F.6; first Q4 2026 audit; theory 0.500) |
| `algo-improvement-operating-regime.md` | **done** (Wave 17 P3; CRITICAL gap closed) |
| `PHASE-2-model-complexity-analysis.md` | **done** (Wave 19 P1A1; 3 models + RANKING.md) |
| `paper-writeup.md` | **done** (Wave 19 P2; 990 lines, 6 sections, 13 tables, 3 figures) |
| `rerun-wave10-with-refactored-framework.md` | **done** (Wave 19 P1A2; verdict=not_supported; decision metric saturated) |

## Cross-references to operating state

- `todo.json` (project root) — machine-readable task index
- `git log origin/main..HEAD` — empty (Wave 6-14 pushed); Wave 15 still local
- `docs/CONSOLIDATED_RESULTS.md` — single source of truth for experimental evidence
- `docs/CLAIMS.md` — 47 documented claims
- `docs/baseline-audit-report.md` — 9 metrics + Wave 15 re-audit
- `docs/theory/theorem1_rate_bound.md` — NEW (Wave 15 B)
- `env_hash.txt` — NEW (Wave 15 Phase 1)
- `requirements-lock.txt` — NEW (Wave 15 Phase 1)
- `scripts/capture_env_hash.py` — NEW (Wave 15 Phase 1)
- `tests/test_adapters/conformance_battery.py` — NEW (Wave 15 C)
- `tests/test_theory/negative/` — NEW (Wave 15 A; must-fail fixtures)
- `/home/hugo/.venv-flowmol311/` — NEW (Wave 15 F; FlowMol3 §1.1.d sidecar)