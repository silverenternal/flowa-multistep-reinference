# Acceptance gates — rendered gate chain

**Date:** 2026-09-05 (master-chain section frozen; refreshed 2026-10-30)
**Source of truth:** `todo.json` — `gate_chain` (the 20 live commands, run
in that order) and `gate_note` (why each entry exists, with the incident
that added it). The `todo/` tree this page used to cite was retired on
2026-10-13 (`bd9055c3`): its thirteen files were consolidated into
`todo.json`, and the parts of the gate definitions that survived are
reproduced below rather than left as a dangling pointer.
**Status:** This page is the surviving record of the historical master
chain (`G-MASTER-*`, `G-FRAMEWORK-HEALTH`, `G-OPS-*`). The **binding**
day-to-day list is `todo.json` → `gate_chain`; the master chain below is
the governance layer it descended from, not a second list to run.

Per user directive (2026-09-05):
> "todo目录下的所有任务都要有验收门槛，没过门槛就禁止进入下一步任务"
> (translation: every task in `todo/` must have an acceptance gate; if a
> gate is not passed, the next task is blocked from starting.)

The directory that directive named is gone; the rule is not. It survives
as `todo.json` → `gate_chain`: every increment must leave all twenty
commands at exit 0 before the next one starts.

A gate is **passed** only when its verification step returns 0; otherwise
the downstream task is **blocked**.

## Master chain (top-level gates)

The canonical master chain (G-MASTER-PHASE-1 through G-MASTER-PAPER,
G-MASTER-CAPABILITY, G-FRAMEWORK-HEALTH, plus cross-cutting
G-OPS-* operational gates) is defined here — this table is now its only
surviving copy.

**Headline gates:**

| Gate | Purpose | Blocking? |
|---|---|---|
| `G-MASTER-PHASE-1` | framework + theory + algorithm is solid | blocks PHASE-2 |
| `G-MASTER-PHASE-2` | per-model analysis complete + ranked | blocks PHASE-3 |
| `G-MASTER-PHASE-3` | glue + adapter + tests per ranked model | blocks PHASE-4 |
| `G-MASTER-PHASE-4` | baseline-vs-framework comparison done per model | blocks paper-writeup |
| `G-MASTER-PAPER` | 6-page workshop paper draft complete | final gate |
| **`G-MASTER-CAPABILITY`** | **framework value-delivery measured from cold clone** | **blocks paper-writeup if any HARD fails** |
| `G-FRAMEWORK-HEALTH` | framework-internal metrics pass | per-wave |
| `G-OPS-PUSH` | unpushed commits released | per-release |
| `G-OPS-CLEAN-WORKING-TREE` | no untracked or modified files | per-release |
| `G-OPS-TODO-LOG-UPDATED` | STATUS.md reflects last wave | per-wave |

## `G-MASTER-CAPABILITY` — the new value-delivery gate

**Pre-condition:** Phase 4 done for ≥ 2 models AND ≥ 3 model families
integrated (protein, image, chemical-graph, latent-diffusion, synthetic-2D).

This gate is **load-bearing for the paper-writeup claim**. Rev 2's audit
metrics measure engineering discipline; this gate measures value
delivery. Per user critique 2026-09-05:

> "全是审计性的指标啊，衡量框架能力的指标没做过吗？"
> (translation: "these are all audit metrics — have you ever measured the
> framework's actual capability?")

The five HARD conditions are:

| Metric | Definition | HARD target |
|---|---|---|
| **G.1** | Mean value score `mean((framework - baseline) / \|baseline\|)` across integrated models × benchmarks | `>= +0.05` (≥ 5% mean improvement) |
| **G.3** | Worst-case bound `max(baseline - framework) / \|baseline\|` | `>= -0.03` (no catastrophic regression > 3%) |
| **G.4** | Generalization breadth: distinct model families where `G.1 >= 0` on ≥ 1 benchmark | `>= 3` families |
| **G.6** | Honest negative surface `count(regressing cells) / count(tested cells)` over `(model, σ_noise)` Pareto cells | `<= 0.30` |
| **G.7** | Reproducibility-of-capability: re-run audit on cold clone | `>= 6/7 metrics reproducible` |

Two SOFT targets are also recorded (do NOT block):

| Metric | Definition | SOFT target |
|---|---|---|
| **G.2** | Cost-benefit ratio `median(cbr / gain)` | `<= 5.0` per 1% gain |
| **G.5** | Saturation point `median(N_min @ 95% quality)` | `<= 50 NFE` |

**Verification:**

```bash
# Run the audit end-to-end on a fresh checkout (cold clone + pinned venv + F.5 env hash)
python tools/capability_audit.py 2>&1 | tee /tmp/cap.log

# Confirm all 5 HARD conditions report PASS in the JSON output
jq '.metrics | {G1: .G1.verdict, G3: .G3.verdict, G4: .G4.verdict, G6: .G6.verdict, G7: .G7.verdict}' \
   verification_outputs/capability_audit_qX_2026.json
```

**Pass condition:** ALL 5 HARD conditions report PASS.

**Block rule:** if any HARD condition fails, `G-MASTER-PAPER` is BLOCKED.

Metric definitions: the five HARD and two SOFT targets are stated in full
in the two tables above, which are the surviving copy. The three
`todo/` files that once expanded them (`framework-capability-metrics.md`,
`framework-internal-metrics-rev3-plan.md` §7.1,
`framework-freeze-checklist.md` MUST-4) were retired with the rest of the
tree on 2026-10-13. The tool they gate is still live:
`tools/capability_audit.py`, with results under
`verification_outputs/capability_audit_*.json`.

## D.4 byte-stable regression vectors (single source of truth)

**Gate:** D.4 pinned regression vectors — **72/72 PASS** at HEAD as of 2026-09-14
(commit `5677cf2`, Wave 149 final close; ruff-frozen code). The total breaks
down as 30 tests in `tests/test_d4_regression_vectors.py` + 42 tests in
`tests/test_adapters/test_regression_vectors.py` = **72** tests, all PASS
per `pytest tests/ -k "d4" -q`.

The per-file split was re-counted with `pytest --collect-only` on 2026-10-30:
30 + 42 = 72. Earlier revisions of this page (and of the constant comment in
`tools/verify_submission_readiness.py`) attributed the same total as 33 + 39;
neither file has changed since `b88b32f6` / `1ce8e3a2`, so that attribution
was a miscount, not a reorganisation. The **total**, which is what the gate
asserts (`D4_EXPECTED_PASS_COUNT = 72`), has been correct throughout.

| Test surface | Test count | Status | Last green |
|---|---:|---|---|
| `tests/test_d4_regression_vectors.py` | 30 | PASS | `--collect-only` 2026-10-30 |
| `tests/test_adapters/test_regression_vectors.py` | 42 | PASS | `--collect-only` 2026-10-30 |
| **Total** | **72** | **PASS** | `--collect-only` 2026-10-30 |

**Verification command:**
```bash
PYTHONPATH=. python -m pytest tests/test_d4_regression_vectors.py \
    tests/test_adapters/test_regression_vectors.py -q
```

**Historical "33/33 PASS" caveat:** The historical "33/33 PASS" figure
(used in cover_letter.md, submission_checklist.md, supplementary.md
S6.3, the README §Tests section, and many downstream docs prior to
Wave 149 Agent 6) referred to the Wave 38-39 first-batch regression
subset ONLY (i.e., just `tests/test_d4_regression_vectors.py`, quoted as
33 tests at the time; it collects 30 — see the correction above). The
current **72/72** figure includes the Wave 32 batches 2/3/4 + Wave 33
batch 2/3 additions (`tests/test_adapters/test_regression_vectors.py`,
42 tests, commit `40d979c` and subsequent). Wave 106.C.3 unified
the wording to "D.4 pinned regression vectors 72/72 PASS" with a
historical caveat for the legacy "33/33" figure; Wave 149 Agent 6
extended this standardization to all 73 non-archived docs/ files
(see `docs/audit/wave149-close.md`).

**D.4 vs full pytest — important distinction:** The full pytest suite
(`pytest tests/ -q`) reported **5610 passed / 180 skipped / 0 failed** on
2026-10-30 (`todo.json` → `gate_note`; the post-Wave-131 ruff-frozen
figures quoted here previously — 5155 collected / 5012 passed — are
superseded). D.4 is the 72-test pinned subset that must stay green on
every change; the full suite is run per change but is not the gate.

The three failures this page used to list as pre-existing are all gone,
and none of them are failures today:

| Formerly listed failure | State on 2026-10-30 |
|---|---|
| `test_exp2_stochastic_fm_w2_ratio_reproduces_25pct_reduction` | **file deleted** in Wave 33 (`9c10d212`, "StochFM delete") — the listing outlived the test |
| `test_check_docs_against_code.py::test_self_test_quiet_mode_returns_zero_exit` | **test no longer exists** in that module |
| `test_check_docs_against_code.py::test_no_false_positives_on_current_repo` | **1 passed** (re-run 2026-10-30) |

`tests/test_tools/test_paper_metrics.py`'s 12 former failures were an
import-order defect in the mock rather than a torch dependency, fixed on
2026-10-30 (`docs/audit/pytest-order-dependence.md`). The Wave 48 record
of the original three remains at `docs/audit/wave48-pytest-pre-push-fixes.md`
as history.

**Wave 149 Agent 6 wording standardization extension** — every non-archived
doc surface (cover letter, submission_checklist, supplementary §S6.3,
README §Tests, baseline-audit-report.md, CONSOLIDATED_RESULTS.md,
INSIGHTS.md, paper-draft.md, paper-final-neurips.md, all audit/*.md from
Wave 100+) now states "D.4 pinned regression vectors 72/72 PASS" with a
historical caveat for the legacy "33/33" figure.

## Cross-cutting operational gates

`G-OPS-PUSH` (the NO-PUSH policy — every agent commits, no agent pushes),
`G-OPS-CLEAN-WORKING-TREE`, and `G-OPS-TODO-LOG-UPDATED` govern release
hygiene. Their verification commands and current policy live in
`todo.json` → `no_push`, `commit_footer` and `recording_policy`.

## Per-task gate references

Every task on the execution order in `todo.json` → `execution_order`
carries the gate it must clear. The cross-reference table that used to
live in `todo/GATES.md` was not carried over when the tree was retired;
`todo.json` → `gate_note` records the incident behind each surviving
gate, which is the part that still has explanatory value.

## Enforcement

The gates are **BINDING**. Before starting any increment, the executor
(agent or human) runs `todo.json` → `gate_chain` in order. If a command
returns non-zero, the increment is blocked and **must not start**.

If a gate fails, the failure mode, the fix and the new gate it revealed
are written into the increment's `docs/audit/<increment>-*.md` note and,
if the gate itself changes, into `todo.json` → `gate_note`.

## See also

- **Live gate list** — `todo.json` → `gate_chain` / `gate_note`
- **Master chain + capability metrics (group G)** — this page, above
  (the `todo/` files that expanded it were retired 2026-10-13)
- **CONSOLIDATED_RESULTS** — `docs/CONSOLIDATED_RESULTS.md` (empirical evidence)
- **CONDITIONS.md** — `docs/CONDITIONS.md` (Pareto plots for G.6 honest-negative surface)

## Paper grounding

The gate chain above (whose live definition is `todo.json` → `gate_chain`)
is ultimately a check on whether the framework's implementations of the
underlying JMAA paper (Li 2026) remain correct across edits. The
load-bearing gates in the chain reference the paper as follows:

* **`G-FRAMEWORK-HEALTH`** includes the E.2 doc cross-reference ratio
  whose machine-checkable anchor matches the `tools/check_doc_paper_refs.py`
  patterns (`Theorem N`, `Lemma N`, `Proposition N`, `paper section X.Y`,
  `arXiv:NNNN.NNNNN`, `JMAA`). When `G-FRAMEWORK-HEALTH` passes, every
  A.0 paper statement has at least one doc anchor.
* **`G-ALGO-RATE-BOUND`** (algorithm-improvement B → C) requires
  `docs/theory/theorem1_rate_bound.md` to exist with a paper-equation
  citation, which is the **Theorem 1** (BL-convergence, `paper section 3.1`)
  gate.
* **`G-ALGO-UPLIFT-ISOLATION`** (algorithm-improvement C → D) requires
  A.7 must-fail fixtures for every theorem surface referenced in the
  rate-bound deliverable AND any additional A.0 entry surfaced during
  task C work. The currently covered surfaces are **Proposition 3**
  (`paper section 4.2`), **Proposition 6** (`paper section 4.3`),
  and the rate-bound cofactor of **Theorem 1**.

In short, a release that passes every gate in this chain has shipped
the paper-anchored correctness story end-to-end.
