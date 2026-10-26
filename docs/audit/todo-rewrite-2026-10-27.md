# 2026-10-27 — todo.json rewritten around acceptance

**Increment:** `todo-rewrite-2026-10-27`
**Scope:** management surface only. No experiment was run, no measurement was
taken, and no claim, number or status label in any evidence surface changed.

**Trigger:** user instruction — *"直接把旧的todo.json删除，写新的todo.json用来规划
你提到的这些内容"* — after a discussion of the paper's acceptance estimate at a
CAS tier-1 venue.

---

## 1. What was retired

| | |
|---|---|
| file | `todo.json` (v7, `flowa-state-v7`) |
| bytes | 41,226 |
| SHA-256 | `0d80e4219d6b4f74a8518e16b2bfadb1f5ebdd0d9a8695f6bf24f01c714d6dd6` |
| archive | `docs/audit/todo-archive-2026-10-27.json` (byte-identical, verified) |

Order of operations followed AGENTS.md §3 guardrail 2 (additive first): the
archive was written and hashed, then a §25 record was appended to
`docs/audit/todo-history.md`, and only then was `todo.json` replaced.

## 2. What was preserved verbatim

Eleven constitution fields were copied byte-for-byte and re-verified against
the archive after the write:

`objective`, `win_definition`, `frontier_protocol`, `no_push`,
`commit_footer`, `recording_policy`, `decision_rule`, `research_protocol`,
`gate_chain`, `deferred`, `history`.

The win definition (point win AND frontier dominance, a TIE is a loss) and the
decision rule (no seed top-ups, one pre-registered confirmatory measurement,
change the mechanism rather than buy confidence) are unchanged. The rewrite
changes *ordering*, not *standards*.

## 3. What changed

The v7 file was a cell-by-cell mechanism ledger: eleven cells, each with an
open gap whose acceptance test was "this cell wins". The v8 file is a
submission plan ordered by how much each item moves an acceptance decision.

Nine items, in order:

| # | id | why it is at this position |
|---|---|---|
| 1 | `GAP-90-EPOCH-DOSE-CONTROLLED` | the only experiment that converts the paper's central claim from a four-point cross-section into an identification |
| 2 | `GAP-91-FLOOR-DISTANCE-LAW` | turns the GAP-84 description into an out-of-sample predictor, or rejects it |
| 3 | `GAP-92-KAPPA-BRIDGE-INTO-PAPER` | zero GPU; the manuscript says the theory predicts nothing, while GAP-78 measured a contraction that orders the sign 12/12 |
| 4 | `GAP-93-CONVERGED-CHECKPOINT-LEVER` | production is a near-miss (−0.50 FID, CI [−0.9996, +0.0025]), not a wall |
| 5 | `GAP-94-STANDARD-BENCHMARK` | user gate; the one objection that no writing can close |
| 6 | `GAP-95-FRONTIER-GRIDS-REMAINING` | each cell gets a grid or a measured reason it cannot have one |
| 7 | `GAP-96-MANUSCRIPT-COMPRESSION` | make room for items 1 and 3; hold 12 pages |
| 8 | `GAP-15-VENUE-AND-TIMING` | submit now vs run GAP-90 first |
| 9 | `GAP-20-COVERLETTER-PLACEHOLDERS` | 17 identity fields, user only |

Seven live items were carried over with their status strings intact
(`GAP-79`, `GAP-81`, `GAP-71`, `GAP-70`, `GAP-47`, `GAP-50`, `GAP-51`), so no
in-flight work was silently dropped. `GAP-29-MANUSCRIPT` is folded into
`GAP-96`; `GAP-15-VENUE` is folded into `GAP-15-VENUE-AND-TIMING`;
`GAP-74` and `GAP-80` were already `DONE` and remain only in the history.

## 4. Observed facts behind the ordering

1. **GAP-84 already measured the relation the paper needs.** Its §24 record
   states: *the framework's gain is the baseline's distance to its own floor*,
   with −12.75% at baseline 24.48, −5.92% at 16.95, and ±0.3% at 11.38 / 9.99.
   The relation exists; what it lacks is a controlled axis.
2. **The four checkpoints are confounded.** They differ in architecture,
   training-set size and training time simultaneously, which is why the
   manuscript correctly calls the regime reading a hypothesis.
3. **GAP-78 already measured a sign-ordering contraction.** `kappa` at
   β = 0.3 gives 12/12 weak dominance on the floor rule
   (`verification_outputs/gap78-kappa-dose-n1000-3seed/r5c_report.json`). The
   manuscript's sentence "neither theorem determines the sign of Inception FID"
   is true of the theorems and understates the evidence the repository holds.
4. **Production is movable.** In the same artifact, `codimension_sheet` at
   β = 0.3 moves production by −0.4985 FID with CI [−0.9996, +0.0025] — a
   near-miss, not a converged wall. The headline arm is the wrong arm there.
5. **Four artifacts that look like frontier grids are degenerate** and are
   named in `GAP-95` so they are not reused: `kanzi_nfe_scan_q4_2026` (validity
   1.0 on both arms at every rung), `flowmol3_fine_nfe_q4_2026` (0.0734 on both
   arms at every rung), `lineageflow_nfe_scan_paper_metric_q3_2026` (n = 8,
   8/8 ties at saturation), `nfe_curve_fair_w170_q3_2026.csv` (constant
   baseline across rungs).

## 5. Interpretation

The rewrite does not claim the paper is weak. It records that the paper's
**evidence ordering** was inherited from a period when the goal was "every cell
wins", and that the current bottleneck is different: three cells already win,
and the question a reviewer asks is not "did you win" but "would this help a
checkpoint anyone would deploy".

`GAP-90` is placed first because it answers that question with a measurement
rather than a paragraph, and because it is cheap: one architecture, one
dataset, five epoch levels, one GPU, two days. `GAP-92` is placed third because
it costs no GPU at all and removes a self-inflicted weakness (a paper that
declares its own theory non-predictive while holding a predictive measurement).

## 6. Gates

| gate | result |
|---|---|
| `python3 -c "json.load(open('todo.json'))"` | valid JSON, 21 keys |
| constitution-field equality vs archive | 11/11 identical |
| CI P-NN check (`todo.get("tasks", todo.get("problems", []))`) | vacuously passes — v8 declares neither key, so no unreferenced P-NN ids |
| `python3 tools/check_claims_consistency.py` | no drift |
| `python3 tools/verify_submission_readiness.py` | `READY_WITH_SKIPS: mypy_0` |

## 7. Unresolved

1. **No decision yet on GAP-15.** The file records both options and the
   estimate; it does not choose. The estimate in `venue_assessment` is a
   judgment, not a measurement, and is labelled as such in the file.
2. **GAP-90 has no pre-registration document yet.** The acceptance test is
   written into `todo.json`, but `docs/audit/gap90-epoch-dose.md` does not
   exist. Under the decision rule the pre-registration must be committed
   before the first sample, not before the first run.
3. **The epoch grid is not pinned.** `E ∈ {1,2,5,10,20}` is a proposal; the
   actual choice has to be made against what the existing `w16e1_*` checkpoints
   already are, so that the new family is comparable rather than merely
   parallel.
