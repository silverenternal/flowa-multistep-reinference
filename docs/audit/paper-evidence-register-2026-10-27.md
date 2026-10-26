# Paper evidence register — one cell table, generated, current as of 2026-10-27

**Date:** 2026-10-27
**Author:** paper-evidence agent (USER AUTHORIZED, NO PUSH)
**Scope:** consolidation only. No experiment was run; no number was changed;
no frozen surface (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`) was edited.

---

## 1. What was wrong

The same eleven cells carried four different verdict tables:

| surface | date | why it disagreed |
|---|---|---|
| `docs/drafts/paper-A-final.*` | 2026-10-18 | frozen at v3.1; predates GAP-79/80/81/84 |
| `docs/CLAIMS.md` / `CONSOLIDATED_RESULTS.md` | 2026-10-12 | older still; R5c still on the smoke checkpoint |
| `docs/audit/gap50-evidence-grade-table.md` | 2026-10-19 | R5c → REGRESSES, R6 counterfactual retired; predates GAP-79/84 |
| `todo.json` | 2026-10-26 | WIN-everywhere objective + the new gap results |

The cell numbering was also split three ways (`docs/headline-evidence/` uses
Wave-135, the manuscript uses Wave-310, `paper-data/` uses a third set of
directory names). A reader could not tell which R2 was meant without opening
three files.

## 2. What landed

| file | role |
|---|---|
| `docs/paper-evidence.json` | single source of truth: 11 cells, each with protocol, point reading, frontier reading, artifact, audit, quote, verdict, next lever |
| `docs/PAPER-EVIDENCE.md` | generated table (never hand-edited) |
| `tools/paper_evidence.py` | `--check` (paths, quotes, verdict logic, summary counts) and `--render` |
| `tests/test_paper_evidence.py` | 7 tests: repository validity, WIN-requires-both, unmeasured-frontier guard, duplicate id, missing artifact, quote presence, render determinism |

The win rule is `todo.json`'s, applied mechanically: a cell is `WIN` only if
the point reading is `WIN` **and** the frontier reading is `WIN`. A tie is not
a win; a missing grid cannot be a win.

## 3. Current state (observed, not interpreted)

| cell | point | frontier | cell |
|---|---|---|---|
| R1 LineageFlow hits | WIN_SINGLE_SEED (+117 hits, +74.1%) | UNMEASURED | OPEN |
| R2 Kanzi RMSD | WIN (d_z −0.0990, p 0.0018) | UNMEASURED | OPEN |
| R3 FlowMol3 fg_dev | NOT_SIGNIFICANT (3 seeds, p 0.559) | UNMEASURED | OPEN |
| R5a 2D W2 | TIE (0.0844 vs 0.0783, p 0.287) | UNMEASURED | OPEN |
| R5b CIFAR FID | MIXED (2/4 arms improve) | INCOMPLETE (2 rungs) | OPEN |
| R5c MNIST FID | WIN on w16e1_5k (−12.75%) | WIN (7 rungs) | **WIN** |
| R6 k6 foldability | WIN (scPerp d_z −0.8393) | UNMEASURED | OPEN |
| K1 PoseBusters validity | NOT_SIGNIFICANT (p 0.252) | UNMEASURED | BLOCKED |
| K4 long-bias hits | POWERED | UNMEASURED | SUPP |
| K5 uniform-prior delta | NOT_SIGNIFICANT (p 0.184) | UNMEASURED | SUPP |
| K7 novelty | LOSS (12.6× less novel) | UNMEASURED | OPEN |

Distribution: **1 WIN, 7 OPEN, 1 BLOCKED, 2 SUPP**. Frontier coverage:
**1 of 7 R-level cells** (R5c). That coverage number is the single largest
gap between the evidence base and the two-part win definition — not a
statement that the other cells are null.

## 4. Documentation convergence (additive)

- `docs/README.md`: header now points at the register; §4 gains the register
  row; §7 adds the "one register, no parallel tables" rule.
- `AGENTS.md`: dead `todo/WAVES.md` / `todo/PUSH-READY.md` references replaced
  with `todo.json`; register added to the paper-evidence skill's read list and
  ownership; repo map updated.
- Banners (no content deleted): `docs/headline-evidence/README.md` (Wave-135
  numbering), `paper-data/MANIFEST.md` (2026-09-23 freeze), `docs/audit/gap50-evidence-grade-table.md`
  (superseded snapshot), `docs/audit/paper-v32-data-refresh.md` (checklist, not entry point).
- `docs/drafts/ARCHIVE_INDEX.md`: stale canonical hashes refreshed; the two
  flattened paper drafts carry a "not the manuscript" banner.
- `todo.json`: GAP-50 marked refreshed; the execution-order row points at the
  register. Manuscript insertion remains user-gated.

## 5. Gates

| gate | result |
|---|---|
| D.4 regression | 30/30 PASS |
| claims consistency | exit 0, no drift |
| ruff (`adaptive_reflow/ tests/ scripts/ tools/`) | 0 findings |
| `mkdocs build --strict` | exit 0, 0 warnings |
| `tools/check_docs_against_code.py` | 3371 claims verified |
| `pytest tests/test_paper_evidence.py` | 7/7 PASS |
| `pytest tests/` | 5491 passed, 177 skipped, 15 failed — 13 pass in isolation (ordering/env), 2 are a pre-existing stub mismatch at `tools/eval/sweep.py:191` (`classifier_aware_restart` not accepted by the test stub), unrelated to this change |
| mypy | SKIP — not installed in the system interpreter (CLM-024) |

## 6. What this does not do

- It does not apply any row to the manuscript. That is the v3.2 refresh,
  still user-gated.
- It does not re-run or re-measure anything.
- It does not change a verdict by wording. The register is derived from the
  artifacts and audits listed in each row.

## 7. Smallest next actions

1. GAP-79 confirmation (R1) when the GPU frees.
2. GAP-81 sigma screen (R3).
3. For R2/R6, build the missing (quality, NFE) grid — the point win already
   exists, so the frontier is the only missing half.
