# `todo/STATUS.md` — single source of truth (auto-updated per wave)

**Last updated:** 2026-09-05 (Wave 12 A1 fixes committed; Phase 1 done)

## Current state (one line)

> **Phase 1 (framework + theory) DONE.** Wave 12 closed all 7 A1 audit findings (3 high + 2 medium + 2 low). Wave 10 (LineageFlow) shipped but real-ckpt verdict OPEN. todo/ created with 4 PHASE + 7 per-task + 1 models/lineageflow.md files.

## Last completed wave

- **Wave 12 (2026-09-05)** — A1 audit fixes committed: 3 high (Theorem 1 consolidation, Lemma 2 LHS witness, true BL on R^2), 2 medium (F-side validator, Proposition 6 escaping-sharpness test), 2 low (periodicity-free docstring, rho<d/4 docstring). G-MASTER-PHASE-1 gates re-verified: pytest --collect-only 3228 tests, A1-fix tests 32/32 pass, acyclic gate 13/13 pass, mkdocs --strict exit 0. Phase 1 truly done.
- **Wave 11 (2026-09-05)** — commit `ebc0550`. Theory package + 10 Protocol surfaces + 52 conformance tests.

## Next action (per user "一个一个来")

Per the 4-phase plan just written, the recommended next step is:

- **Phase 2 sub-task**: write `todo/models/lineageflow.md` ✅ (done) + analyze the
  next 1-2 models in ranking order. The LineageFlow analysis captures LL-001
  ("ckpt + upstream source both required") as a reusable pattern.

## Current unblocked / blocked status

- ✅ Wave 10: committed
- ✅ Wave 11: committed (Phase 1 done)
- ✅ Wave 12: committed (all 7 A1 fixes + acceptance gate)
- 🟡 LineageFlow real-ckpt verdict: OPEN (blocked on `core` source)
- 🔴 8+ unpushed commits on local main

## Files in `todo/` (count + status)

| File | Status |
|---|---|
| `README.md` | current |
| `PHASE-1-framework-and-theory.md` | **done** (Wave 12 closed all audit findings) |
| `PHASE-2-model-complexity-analysis.md` | pending (start after Phase 1 done — UNBLOCKED) |
| `PHASE-3-glue-layer-improvement.md` | pending (after Phase 2) |
| `PHASE-4-model-integration-iteration.md` | pending (after Phase 3) |
| `models/README.md` | current (template) |
| `models/lineageflow.md` | current (Wave 10 BLOCKED lesson) |
| `wave10-result-validation.md` | done (Wave 10 done) |
| `wave11-result-validation.md` | done (Wave 11 done) |
| `wave12-result-validation.md` | done (Wave 12 done — all 7 A1 fixes committed) |
| `rerun-wave10-with-refactored-framework.md` | pending |
| `push-unpushed-commits.md` | pending (user explicit go-ahead needed) |
| `paper-writeup.md` | pending (after Phase 4) |
| `lessons-learned.md` | current (LL-001) |
| `decisions.md` | current |
| `add-more-2026-sota-models.md` | **FOLDED into PHASE-2** (delete after this commit) |

## Cross-references to operating state

- `todo.json` (project root) — machine-readable task index
- `git log origin/main..HEAD` — unpushed commits (5+ as of 2026-09-05)
- `docs/CONSOLIDATED_RESULTS.md` — single source of truth for experimental evidence
- `docs/CLAIMS.md` — 47 documented claims
- `docs/reproducibility_record.md` — Wave 6 reproducibility audit
- `docs/ARCHITECTURE.md` (if exists) — framework architecture
