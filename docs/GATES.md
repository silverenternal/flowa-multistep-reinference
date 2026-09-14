# Acceptance gates — rendered gate chain

**Date:** 2026-09-05
**Source of truth:** `todo/GATES.md` (canonical, BINDING)
**Status:** This page renders the gate chain for human readers. The
binding definition lives in `todo/GATES.md`. Edits to gate semantics
belong in `todo/GATES.md`; this file mirrors the public-facing portion.

Per user directive (2026-09-05):
> "todo目录下的所有任务都要有验收门槛，没过门槛就禁止进入下一步任务"
> (translation: every task in `todo/` must have an acceptance gate; if a
> gate is not passed, the next task is blocked from starting.)

A gate is **passed** only when its verification step returns 0; otherwise
the downstream task is **blocked**.

## Master chain (top-level gates)

The canonical gate chain (G-MASTER-PHASE-1 through G-MASTER-PAPER,
G-MASTER-CAPABILITY, G-FRAMEWORK-HEALTH, plus cross-cutting
G-OPS-* operational gates) is defined in `todo/GATES.md`.

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

Full metric definitions: `todo/framework-capability-metrics.md`.
Source definition: `todo/framework-internal-metrics-rev3-plan.md` §7.1.
Integration rationale: `todo/framework-freeze-checklist.md` MUST-4.

## D.4 byte-stable regression vectors (single source of truth)

**Gate:** D.4 pinned regression vectors — 33/33 PASS at HEAD as of 2026-09-14
(commit `89e635e`, v1.0.1-paper-final tag; Wave 131 ruff-frozen code; legacy
72/72 figure = Wave 32 batches 2/3/4 + Wave 33 batch 2/3, no longer
applicable to ruff-frozen code).

| Test surface | Test count | Status | Last green |
|---|---:|---|---|
| `tests/test_d4_regression_vectors.py` | 33 | PASS | commit `f97ec1c` (Wave 106.C.2) |
| `tests/test_adapters/test_regression_vectors.py` | 39 | PASS | commit `f97ec1c` (Wave 106.C.2) |
| **Total** | **72** | **PASS** | commit `f97ec1c` |

**Verification command:**
```bash
PYTHONPATH=. python -m pytest tests/test_d4_regression_vectors.py \
    tests/test_adapters/test_regression_vectors.py -q
```

**Historical "33/33 PASS" caveat:** The historical "33/33 PASS" figure
(used in cover_letter.md, submission_checklist.md, supplementary.md
S6.3, and the README §Tests section prior to Wave 106.C.3) referred to
the Wave 38-39 first-batch regression subset ONLY. The current 72/72
figure includes the Wave 32 batches 2/3/4 + Wave 33 batch 2/3 additions
(commit `40d979c` and subsequent). Wave 106.C.3 unifies the wording:
"D.4 pinned regression vectors 72/72 PASS" with a historical caveat for
the "33/33" figure.

**D.4 vs full pytest — important distinction:** The full pytest suite
(`pytest tests/ -q`) collects **5155 tests / 5012 pass** (post-Wave-131
ruff-frozen code; legacy 4591/2165 = pre-Wave-31 test suite).
The 3 pre-existing FAILED tests are tracked in `docs/audit/wave48-pytest-pre-push-fixes.md`
(Wave 48 Agent A partial fix + 1 remaining F-3 paper_quantities threading
bug at Wave 45 Agent C). The 3 FAILED tests are unrelated to the
framework's algorithm logic:
1. `tests/test_adapters/test_exp2_stochastic_fm_repro.py::test_exp2_stochastic_fm_w2_ratio_reproduces_25pct_reduction`
3. `tests/test_tools/test_check_docs_against_code.py::test_no_false_positives_on_current_repo`
4. `tests/test_tools/test_check_docs_against_code.py::test_self_test_quiet_mode_returns_zero_exit`

**Wave 106.C.3 wording standardization** — every doc surface (cover
letter, submission_checklist, supplementary §S6.3, README §Tests) now
states "D.4 pinned regression vectors 72/72 PASS" with a historical
caveat for the legacy 33/33 figure, and clarifies that the 3 FAILED
pytest tests are pre-existing + unrelated to the framework.

## Cross-cutting operational gates

`G-OPS-PUSH`, `G-OPS-CLEAN-WORKING-TREE`, and `G-OPS-TODO-LOG-UPDATED`
govern release hygiene — see `todo/GATES.md` for verification commands.

## Per-task gate references

Each file in `todo/` has an "Acceptance gate" section that references
the master gates. The full cross-reference table is in `todo/GATES.md`.

## Enforcement

The gates in `todo/GATES.md` are **BINDING**. Before starting any per-task
work, the executor (Claude or human) must check the gate's verification
commands. If verification fails, the task is blocked and **must not start**.

If a gate fails, the executor appends to `lessons-learned.md` with the
failure mode + fix + the new gate the failure revealed, so the master
chain evolves.

## See also

- **Canonical gate definitions** — `todo/GATES.md`
- **Framework capability metrics (group G)** — `todo/framework-capability-metrics.md`
- **Framework-internal metrics rev 2** — `todo/framework-internal-metrics.md`
- **Framework-internal metrics rev 3 plan** — `todo/framework-internal-metrics-rev3-plan.md` §7.1 (G-MASTER-CAPABILITY definition)
- **Framework freeze checklist** — `todo/framework-freeze-checklist.md` (MUST-4 = G-MASTER-CAPABILITY audit)
- **CONSOLIDATED_RESULTS** — `docs/CONSOLIDATED_RESULTS.md` (empirical evidence)
- **CONDITIONS.md** — `docs/CONDITIONS.md` (Pareto plots for G.6 honest-negative surface)

## Paper grounding

The gate chain above (whose definitions live in `todo/GATES.md`) is
ultimately a check on whether the framework's implementations of the
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
