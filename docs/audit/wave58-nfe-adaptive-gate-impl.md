# Wave 58 Agent 1 — NFE-adaptive restart gate (FlowMol3 v1 adapter)

**Date:** 2026-09-07
**Scope:** `adaptive_reflow/adapters/flowmol3.py`,
`adaptive_reflow/adapters/_adapter_common.py`,
`tests/test_adapters/test_flowmol3_adapter.py`
**Status:** implemented, tested, **not yet wired into the eval pipeline**
(see §6 — that is a Wave 59 step, `tools/run_real_ckpt_eval.py` was
out of this agent's file scope)

> **Commit-trail note.** This change landed split across two commits, not
> by intent. A concurrent Wave 58 agent committed with a whole-tree `git
> add`/`git commit -a` while these files were staged, so `c3eac21`
> ("docs(todo): correct §10 novelty table") carries the bulk of the gate
> code and `db01e28` carries the remainder plus this document and the
> full descriptive message. Nothing was lost — the complete change is
> present at `db01e28` — but `git log -- adaptive_reflow/adapters/flowmol3.py`
> will attribute most of it to a docs commit. History was **not**
> rewritten: other agents were committing to this branch concurrently,
> and a rebase risked destroying their work. Coordination lesson for
> parallel waves: commit with explicit pathspecs, never `-a`/`-A`.

---

## 1. What was implemented

When the effective **total** NFE budget for a cell is below a threshold,
`FlowMol3Adapter.apply_restart_distribution` now returns the input state
with its payload unchanged and stamps an audit code, instead of running
the `blended = m * prior + (1 - m) * fresh` graph blend.

| Knob | Value | Where |
|---|---|---|
| Threshold constant | `FLOWMOL3_RESTART_MIN_NFE = 20` | `flowmol3.py` |
| Per-adapter override | `FlowMol3Adapter(restart_min_nfe=...)`, `0` disables | constructor |
| Budget input | `FlowMol3Adapter(nfe_budget=...)` / `apply_restart_distribution(..., nfe_budget=...)` / duck-typed `policy.nfe_budget` | see §3 |
| Audit code | `flowmol3adapter_restart_skipped_low_nfe:nfe=<N>:min_nfe=<M>` | appended to `provenance` |
| Shared helpers | `low_nfe_restart_gate`, `coerce_nfe_budget` | `_adapter_common.py` |

Diff size: **+536 / −1** across the three files (68 lines of shared
helper, 153 lines of adapter, 316 lines of test).

### 1.1 What "state unchanged" means precisely

The returned bundle preserves `channels`, `masks`, `source_round`,
`detach_proof` and — the load-bearing one — `native_state_digest`, which
on the blended path is rewritten to `flowmol3:restart:<blended digest>`.
Only `provenance` grows, by exactly one entry.

Two audit codes that the blend path stamps are deliberately **absent**
on a gated round: `flowmol3_restart_boundary` and (when the Wave 49
atom-type-entropy policy is wired)
`flowmol3_atom_type_entropy_restart`. A gated round did not restart, and
a downstream eval reading provenance must not be told that it did.

## 2. Why — and what the gate does *not* fix

Wave 57 Agent C traced FlowMol3's `framework_improves=False` to this
blend: at the paper-default `m = 0.5` it replaces half the state with
uniform fresh noise, and with too few remaining integration steps the
CTMC chain cannot re-absorb it.

**This gate is Wave 57 Agent D's backup path B1, not its P0
recommendation.** The synthesis (`docs/audit/wave57-synthesis-design.md`
§6) ranks the masked-prior fix (P0) above it and records three specific
reservations, which this agent did not resolve and which any writeup of
this change must carry:

1. **It leaves half the regressions untouched.** Agent B found 3 of 6
   regressions sit at NFE 50 and 200 — above any plausible threshold. A
   gate at NFE&nbsp;<&nbsp;20 flattens the NFE=10 stratum to
   "≡ baseline" and does nothing for the rest.
2. **The threshold rests on n=3 per stratum.** 20 is an interpolation
   between Agent A's literature read and Agent B's 9-cell v3 grid, which
   cannot reach α=0.05. It is not a measured changepoint, and no
   monotonicity in NFE was established. Hence the constructor kwarg
   (§3): recalibrate on the 18-cell v4 grid, do not treat 20 as found.
3. **No 2025/2026 paper endorses switching refinement off at low NFE.**
   Agent A's survey (A-FloPS, ASFM, Instance-Aware, Adaptive Sparse
   Sampling) is uniformly about *smarter allocation*; three of those
   papers win specifically in the low-NFE regime this gate abandons.
   Agent D's B2 — scaling β with NFE rather than switching the blend
   off, of which this gate is the `m = 0` corner — is the strictly more
   expressive option and remains the better long-run answer.

Shipping B1 first is defensible as the cheap, legible, fully-reversible
step (one constant, one kwarg, no state-shape change, `restart_min_nfe=0`
restores prior behaviour exactly). It is not defensible as the claim
"we identified an NFE threshold below which re-inference hurts".

## 3. Budget resolution — and the per-round trap

`apply_restart_distribution` resolves the budget from three sources, in
priority order:

1. the `nfe_budget=` keyword argument to the call;
2. a duck-typed `policy.nfe_budget` attribute;
3. the adapter's `nfe_budget` constructor kwarg.

**Unknown budget fails open.** If none resolves, the gate does not fire
and the blend proceeds. This is what keeps every pre-Wave-58 caller —
the engine, and the pinned D.4 vectors in
`regression-vectors/flowmol3.json` — byte-identical; a gate that fired
on an unknown budget would silently flatten the framework arm everywhere.

**The gate keys on the TOTAL NFE, never the per-round NFE.** This is the
trap worth recording. `tools/run_real_ckpt_eval.py:_solve_framework`
splits the budget as `nfe_per_round = round(nfe / n_rounds)` and passes
*that* into each round's `ODEConditionDelta.delta_spec["num_steps"]`. At
the FlowMol3 paper default (`nfe=50`, `n_rounds=3`) the per-round count
is **17** — below a threshold of 20. So an implementation that took the
budget from the condition delta it already receives would gate the
NFE=50 stratum, which is exactly where 3 of the 9 v3 cells are
**SUPPORTED**. It would have destroyed the only cells that currently
work, and the 9-cell grid would have shown it as "the gate helped at
NFE=10 and broke NFE=50" with no obvious cause. `low_nfe_restart_gate`
carries this contract in its docstring for the Wave 59+ generalisation.

Two further deliberate asymmetries:

* **Explicit budgets fail closed; discovered ones fail open.** A typed
  `nfe_budget="fifty"` / `0` / `1` / `17.5` raises (a caller bug must
  surface; truncating 17.5 to 17 would hide one). An unusable
  `policy.nfe_budget` is ignored — it is *discovered* on a third-party
  policy object, and a same-named field meaning something else must not
  crash a restart round.
* Budgets `<= 1` are rejected outright: a budget that cannot be split
  across restart rounds is not a budget.

## 4. Verification

| Check | Result |
|---|---|
| `tests/test_adapters/` (whole suite, all 14 adapters) | **1111 passed, 4 failed, 70 skipped** — the 4 are the pre-existing ones below; no other adapter regressed |
| `tests/test_adapters/test_flowmol3_adapter.py` | **75 passed, 4 failed** |
| — of which Wave 58 gate tests | **30 passed** (`-k NfeAdaptive`) |
| — the 4 failures | **pre-existing at HEAD** (`torch_not_installed`; `TestFlowMol3ForceModeFactory` needs the torch sidecar). Verified by re-running the suite with the three changed files stashed: identical 4 failures, 45 passed. |
| `tests/test_d4_regression_vectors.py` + `tests/test_adapters/test_regression_vectors.py` | **72 passed** — B.2 byte-stability holds |
| Byte-stability, directly | the `nfe_budget=200` bundle is digest- and provenance-identical to the no-budget bundle (asserted by `test_unknown_nfe_budget_is_byte_identical_to_pre_wave58`) |
| `ruff check` on the 3 files | 6 findings, **all pre-existing at HEAD** (`W292`×2, `F841 log_K`, `UP012`, `I001`, `B017`); zero new. Left alone rather than opportunistically fixed — this adapter's digests are load-bearing. |
| `tools/check_docs_against_code.py` | 1 failure, pre-existing and unrelated (`paper-draft.md:763` `OracleAtRound`) |
| `mypy --strict` | **not run** — mypy is not installed in the active interpreter (`python3.14`, no venv module). Types were written to the file's existing strict-clean style but are unverified. |

### 4.1 Test coverage of the gate (30 tests)

Beyond the two cases the brief asked for (`nfe_budget=10` skips and
leaves state unchanged; `nfe_budget=200` blends normally):

* byte-identity of the unknown-budget path against the blended path;
* threshold boundary is exclusive (`20` blends, `19` skips);
* the audit code carries both `nfe` and `min_nfe`;
* each of the three budget sources drives the gate independently, and
  the documented priority order holds;
* `restart_min_nfe=0` disables the gate; a custom threshold is honoured;
* a gated round emits no blend-side audit code even with the Wave 49
  atom-type policy wired;
* explicit bad budgets raise at both entry points (parametrised over
  `"fifty"`, `0`, `1`, `-5`, `17.5`, `True`, `object()`);
* junk `policy.nfe_budget` falls through without raising;
* `restart_min_nfe` rejects `-1`, `"20"`, `20.0`, `True`, `None`;
* the factory threads both knobs, and its default leaves the gate inert.

## 5. Not done in this wave (by scope)

* **`tools/run_real_ckpt_eval.py` is untouched** (explicit constraint),
  so the eval pipeline never supplies a budget and **the gate is inert
  in every current sweep**. No v3/v4 number changes as a result of this
  commit. Wiring is one line at the `_resolve_adapter` factory call
  (`nfe_budget=nfe`) or at the `apply_restart_distribution` call site.
* **FlowMol3 v1 only.** `flowmol3_v2_adapter.py` (the adapter that
  actually runs the real ckpt through the CTMC) is untouched, as are the
  other 13 adapters. Generalising via `low_nfe_restart_gate` is Wave 59+.
* **The threshold was not calibrated.** It is the inherited 20.
* **No CLI override** (Agent D's B1 note asks for one) — that lives in
  `run_real_ckpt_eval.py`, out of scope.

## 6. Wave 59 follow-ups, in order

1. Thread `nfe_budget=nfe` (the **total**, per §3) from
   `run_real_ckpt_eval.py` into the FlowMol3 adapter, plus a
   `--restart-min-nfe` CLI override.
2. Re-run the grid at **6 seeds × 3 NFE = 18 cells** (Agent B §6.3: n=3
   cannot reach α=0.05) and report per-stratum mean, sign test and
   Wilcoxon W+, so v3 and v4 stay comparable.
3. Calibrate the threshold on that grid; if the NFE=10 stratum is
   already fixed by the P0 masked-prior work, **remove this gate**
   rather than stacking both.
4. Prefer Agent D's B2 (β as a function of NFE) over keeping the hard
   switch; this gate is its `m = 0` corner and should be replaced by it,
   not extended.
5. Any paper text must say what §2 says: a backup path shipped on weak
   evidence, contrary to the 2026 consensus, that addresses at most 3 of
   6 regressions.

## 7. Sources

* `docs/audit/wave57-synthesis-design.md` §6 (B1 specification and its
  three reservations), §5 (risk register)
* `docs/audit/wave57-nfe-adaptive-research.md` (Agent A — 2026 literature)
* `docs/audit/wave57-pattern-investigation.md` (Agent B — 9-cell v3 grid)
* `docs/audit/wave57-flowmol3-restart-interaction.md` (Agent C — CTMC
  mechanism)
* `docs/audit/wave41-flowmol3-shrink.md` (the restart boundary's move
  onto the framework-core graph glue, which this gate sits in front of)
