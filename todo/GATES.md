# `todo/GATES.md` — Acceptance gates (binding rule per user directive)

**Date:** 2026-09-05
**User directive:** *"todo目录下的所有任务都要有验收门槛，没过门槛就禁止进入下一步任务"*
(translation: every task in `todo/` must have an acceptance gate; if a gate
is not passed, the next task is blocked from starting.)

**Status:** BINDING. This file defines the gate chain. Each per-task file
in `todo/` references these gates in its "Acceptance gate" section. A gate
is **passed** only when its verification step returns 0; otherwise the
downstream task is **blocked**.

## Master chain (top-level gates)

### G-MASTER-PHASE-1: framework + theory + algorithm is solid

- **Pre-condition:** n/a (this is the entry)
- **Verification:**
  - `cd /home/hugo/codes/flowa-multistep-reinference`
  - `git log origin/main..HEAD --oneline` shows 0 unpushed commits intended to be
    released as a "Phase 1 done" mega-PR (i.e. Wave 11 + pending sub-phases)
  - `.venvs/flowmol3_venv/bin/python -m pytest --collect-only -q 2>&1 | tail -3` shows
    **>= 3146 tests, no ImportError**
  - `.venvs/flowmol3_venv/bin/python -m pytest tests/test_framework/test_import_acyclic.py -v`
    shows **4/4 PASS** (a6dffd3 acyclic gate still holds)
  - `.venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/test_adapter_common.py -v`
    shows **9/9 PASS** (byte-stability holds)
  - `mkdocs build --strict` exits 0
  - `docs/CLAIMS.md` has 47+ CLM entries; no CLM marked ACTIVE with `Disputed by`
    pointing to a recent wave's findings
- **Pass condition:** ALL 6 checks pass
- **Fail action:** return to Wave 11 Phase 0 / Phase 3 to fix root cause

### G-MASTER-PHASE-2: per-model analysis is complete and ranked

- **Pre-condition:** G-MASTER-PHASE-1 passed
- **Verification:**
  - `ls todo/models/*.md` shows >= 3 per-model analysis files (besides README.md
    template)
  - Each file has all 7 template sections (A-G) populated (not "pending" or
    "TBD")
  - `todo/models/RANKING.md` exists with all candidate models sorted by
    combined_score
  - Each ranking entry has a "wave" field showing when Phase 4 will integrate it
- **Pass condition:** ALL 3 checks pass
- **Fail action:** continue analyzing models (one at a time, per directive)

### G-MASTER-PHASE-3: glue + adapter + tests for each ranked model

- **Pre-condition:** G-MASTER-PHASE-2 passed
- **Verification (per model `M` in RANKING.md):**
  - `adaptive_reflow/adapters/M.py` exists, registered in `__init__.py`
  - `tests/test_adapters/test_M.py` exists with **>= 22 tests, all PASS**
  - Byte-stability test exists in the test file
  - Synthetic mode default (Protocol surface exercises on CPU without ckpt)
  - `docs/PLUG_IN_YOUR_MODEL.md` has a section for `M`
- **Pass condition:** ALL 5 per-model checks pass for **every** model in RANKING.md
- **Fail action:** fix the missing/broken glue for that model; cannot proceed to
  Phase 4 for that model until its glue is solid

### G-MASTER-PHASE-4: baseline-vs-framework comparison done per model

- **Pre-condition:** G-MASTER-PHASE-3 passed for the model being tested
- **Verification (per model `M`):**
  - The PHASE-4 acceptance metric table is populated for `M` (primary metric,
    secondary metric, improvement bar, saturation check, all 4 columns)
  - A `comparison.md` exists in `todo/PHASE-4-results/M/` with baseline-vs-framework
    numbers
  - The verdict (supported / partially_supported / not_supported / blocked)
    is recorded in `todo/models/M.md` §F
  - If verdict = supported: row added to `docs/CONSOLIDATED_RESULTS.md` §7+
  - If verdict = not_supported: **STOP and return to Phase 1-3 to fix root cause**
    (per user's "如果...实现做错了" hypothesis)
- **Pass condition:** ALL checks pass per model
- **Fail action:** see verdict-specific actions

### G-MASTER-PAPER: 6-page workshop paper draft complete

- **Pre-condition:** G-MASTER-PHASE-4 passed for at least 3 models
- **Verification:**
  - `paper-writeup.md` checklist all items marked done
  - `docs/CONSOLIDATED_RESULTS.md` reflects all 3+ models
  - 6-page draft exists in `docs/paper-draft.md` (or equivalent) with sections
    matching the proposed outline in `paper-writeup.md`
- **Pass condition:** ALL checks pass
- **Fail action:** continue drafting

### G-MASTER-CAPABILITY: framework value-delivery measured from cold clone

**Pre-condition:** Phase 4 done for ≥ 2 models AND ≥ 3 model families
integrated (protein, image, chemical-graph, latent-diffusion, synthetic-2D).

**Verification:**
- `python tools/capability_audit.py 2>&1 | tee /tmp/cap.log` runs end-to-end
  on a fresh checkout (cold clone + pinned venv + F.5 env hash)
- JSON output at `verification_outputs/capability_audit_qX_2026.json`
  enumerates ALL (model, σ_noise, NFE_budget) cells tested
- Each of the 5 HARD capability metrics reports a value + verdict
  (PASS / FAIL / NOT_MEASURED):

  | Metric | Definition | HARD target | Source |
  |---|---|---|---|
  | **G.1** | Mean value score `mean((framework - baseline) / |baseline|)` across integrated models × benchmarks | `>= +0.05` | `todo/framework-capability-metrics.md` §G.1 |
  | **G.3** | Worst-case bound `max(baseline - framework) / |baseline|` | `>= -0.03` (no catastrophic regression > 3%) | §G.3 |
  | **G.4** | Generalization breadth: count of distinct model families where `G.1 >= 0` on ≥ 1 benchmark | `>= 3` families | §G.4 |
  | **G.6** | Honest negative surface `count(regressing cells) / count(tested cells)` over `(model, σ_noise)` Pareto cells in `docs/CONDITIONS.md` | `<= 0.30` | §G.6 |
  | **G.7** | Reproducibility-of-capability: re-run `tools/capability_audit.py` on fresh checkout; compare G.1-G.6 | `>= 6/7 metrics reproducible` from cold clone | §G.7 |

- Two SOFT targets are also recorded (do NOT block):
  - **G.2** cost-benefit ratio `median(cbr / gain)` `<= 5.0` per 1% gain
  - **G.5** saturation point `median(N_min @ 95% quality)` `<= 50 NFE`

- **Cross-references must be live:**
  - Every `(model, σ)` cell counted by G.6 appears in
    `docs/CONDITIONS.md` Pareto plots (no off-ledger cells)
  - Every integrated model appears in `docs/PLUG_IN_YOUR_MODEL.md` and
    `docs/models/M.model_card.md` (F.4 ≥ 7/8 fields populated)
  - `tools/capability_audit.py` is F.5 env-hash-pinned (warm re-runs are
    NOT counted as cold-clone reproduction)

**Pass condition:** ALL 5 HARD conditions report PASS in the JSON output.

**Fail action:**
- If G.1 fails: investigate per-model value deltas; either fix the
  framework regression OR document which models/benchmarks were excluded
  from INTEGRATED set with rationale (a hard inclusion rule applies:
  INTEGRATED set is closed once PHASE-4 RANKING.md is signed off)
- If G.3 fails: identify the catastrophic-regression cell; either fix
  the framework OR remove the offending model from INTEGRATED with LL
  entry (cannot ship "framework helps" claim with G.3 failure)
- If G.4 fails: integrate ≥ 1 more model family from
  `todo/models/RANKING.md` (LineageFlow BLOCKED is the obvious candidate;
  Kanzi protein or MM-FM image-family are alternatives)
- If G.6 fails: tighten the operating-regime claim in
  `docs/theory/operating-regime.md` (Wave 17 P2 already documented the
  twodim_fm regression as falsifying the original hypothesis) OR
  re-document the affected cells as out-of-scope
- If G.7 fails: investigate the non-reproducible metric; usually a
  missing per-cell report in `CONSOLIDATED_RESULTS.md` (the audit tool
  enumerates ALL tested cells, so a missing row IS the failure)

**Block rule (per rev 3 plan §7.1):** if any HARD condition fails, the
**`G-MASTER-PAPER` gate is BLOCKED** — a reviewer cannot be told
"framework helps" if G.3 (worst-case) or G.6 (honest negative surface)
fail. This is the **load-bearing** gate: rev 2's audit metrics measure
engineering discipline; this gate measures value delivery (the user's
core critique 2026-09-05: *"全是审计性的指标啊，衡量框架能力的指标没做过吗？"*).

### G-FRAMEWORK-HEALTH: framework-internal metrics pass

The per-wave **hard gates** (B.2 acyclic, B.3 byte-stability, B.4 mkdocs)
must pass before ANY wave starts work. Soft-gate regressions require an
LL entry but do not block.

Full definition + entry gates for phase transitions: see
`todo/framework-internal-metrics.md`.

- **Pre-condition:** `framework-internal-metrics.md` exists with current
  values populated
- **Verification (per wave):**
  - `pytest tests/test_framework/test_import_acyclic.py -v` shows **13/13 PASS**
    (B.2; a6dffd3 + 28e3bf9 defenses hold)
  - `pytest tests/test_adapters/test_adapter_common.py -v` shows **9/9 PASS**
    (B.3; byte-stability holds)
  - `mkdocs build --strict` exits **0** (B.4)
  - `pytest --collect-only -q` shows **>= 3228 tests** (B.1 floor)
- **Pass condition:** ALL 4 hard gates pass
- **Fail action:** fix the failing hard gate immediately; wave is BLOCKED

## Cross-cutting operational gates

### G-OPS-PUSH: unpushed commits released

- **Verification:**
  - `git log origin/main..HEAD --oneline` returns empty
  - GitHub shows the commits on `main` branch
- **Pass condition:** empty unpushed set
- **Fail action:** `git push origin main` (after user explicit go-ahead)

### G-OPS-CLEAN-WORKING-TREE: no untracked or modified files

- **Verification:**
  - `git status --short` returns empty
  - All `todo.json.bak` files removed (they're created by some agents)
  - All untracked `docs/_benchmark_ablation.md` removed
- **Pass condition:** clean working tree
- **Fail action:** `git checkout -- <file>` or `rm <file>` as appropriate

### G-OPS-TODO-LOG-UPDATED: STATUS.md reflects last wave

- **Verification:**
  - `todo/STATUS.md` "Last completed wave" matches `git log --oneline -1` HEAD's
    first line
- **Pass condition:** STATUS.md is up-to-date
- **Fail action:** update STATUS.md

## Per-task gate references (where to find them)

Each file in `todo/` has an "Acceptance gate" section that references the
master gates above. Cross-references:

| File | Gate references |
|---|---|
| `PHASE-1-framework-and-theory.md` | G-MASTER-PHASE-1 |
| `PHASE-2-model-complexity-analysis.md` | G-MASTER-PHASE-1 (pre), G-MASTER-PHASE-2 (exit), G-FRAMEWORK-HEALTH (per wave) |
| `PHASE-3-glue-layer-improvement.md` | G-MASTER-PHASE-2 (pre), G-MASTER-PHASE-3 (exit), G-FRAMEWORK-HEALTH (per wave) |
| `PHASE-4-model-integration-iteration.md` | G-MASTER-PHASE-3 (pre), G-MASTER-PHASE-4 (exit), G-FRAMEWORK-HEALTH (per wave) |
| `framework-internal-metrics.md` | G-FRAMEWORK-HEALTH (defines per-phase entry gates) |
| `framework-capability-metrics.md` | G-MASTER-CAPABILITY (defines group G HARD + SOFT targets) |
| `framework-freeze-checklist.md` | G-MASTER-CAPABILITY (MUST-4 dependency for freeze) |
| `wave10-result-validation.md` | G-OPS-PUSH, G-OPS-CLEAN-WORKING-TREE |
| `wave11-result-validation.md` | G-MASTER-PHASE-1 |
| `wave12-result-validation.md` | G-MASTER-PHASE-1, G-FRAMEWORK-HEALTH |
| `algo-improvement-planar-bl-repoint.md` | G-ALGO-PLANAR-BL, G-FRAMEWORK-HEALTH (hard gates) |
| `algo-improvement-rate-bound.md` | G-ALGO-RATE-BOUND, G-FRAMEWORK-HEALTH (hard gates) |
| `algo-improvement-uplift-isolation.md` | G-ALGO-UPLIFT-ISOLATION, G-FRAMEWORK-HEALTH (hard gates) |
| `algo-improvement-failure-modes.md` | G-ALGO-FAILURE-MODES, G-FRAMEWORK-HEALTH (hard gates) |
| `algo-improvement-env-hash.md` | G-F5-ENV-HASH, G-FRAMEWORK-HEALTH (hard gates) |
| `algo-improvement-traceability-hardening.md` | G-ALGO-TRACEABILITY-HARDENING, G-FRAMEWORK-HEALTH (hard gates) |
| `algo-improvement-conformance-battery.md` | G-D5-CONFORMANCE-BATTERY, G-FRAMEWORK-HEALTH (hard gates) |
| `algo-improvement-f2-reproduction.md` | G-F2-REPRODUCTION, G-FRAMEWORK-HEALTH (hard gates) |
| `rerun-wave10-with-refactored-framework.md` | G-MASTER-PHASE-1, G-MASTER-PHASE-4 |
| `push-unpushed-commits.md` | G-OPS-PUSH |
| `paper-writeup.md` | G-MASTER-PAPER |
| `models/<model>.md` (per model) | G-MASTER-PHASE-2 (analysis), G-MASTER-PHASE-3 (glue), G-MASTER-PHASE-4 (integration) |
| `STATUS.md` | G-OPS-TODO-LOG-UPDATED (auto-update per wave) |

## Enforcement

This file declares the gates. **Enforcement is manual**: before starting any
per-task work, the executor (Claude or human) must check the gate's
verification commands. If verification fails, the task is blocked and
**must not start**.

If a gate fails, the executor appends to `lessons-learned.md` with the
failure mode + fix + the new gate the failure revealed, so the master
chain evolves.