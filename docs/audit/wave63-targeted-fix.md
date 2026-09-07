# Wave 63 Agent 2 — Targeted 1-LOC fix for Bug B (source_round not bumped)

**Date:** 2026-09-07
**Wave:** 63, Agent 2
**Scope:** implement the EXACT fix Agent 1 recommended at the EXACT file:line they identified, plus a regression test that specifically targets the bug.
**Constraint:** per Agent 1's `docs/audit/wave63-root-cause.md` §5.2 the
fix is a 1-LOC change to `apply_restart_distribution`'s `replace(...)` block.
**Status:** fix applied, regression tests added, pytest green, regression
vectors still pass. Bug A (`tools/run_real_ckpt_eval.py`) is outside this
agent's disjoint file scope (would need Wave 63 Agent 3 or a follow-up
wave to address).

---

## 1. What was the bug

Cite Wave 63 Agent 1's `docs/audit/wave63-root-cause.md` §3 (Bug B):

> "The 'fresh' payload is seeded from `(batch_id, sample_id, source_round)`.
> `apply_restart_distribution` returns the state with updated
> `native_state_digest`, `channels`, `masks`, `provenance` — but **does
> NOT bump `source_round`**. The default FlowMol3 v1 `replace(...)` call
> at lines 910-919 only touches those four fields."
>
> "So in the framework arm, the same `state.source_round` is threaded
> through every `apply_restart_distribution` call. **The 'fresh' payload
> is identical on every restart boundary** — `random_graph_payload(
> num_nodes=8, num_edges=12, seed=SHA256('fresh', batch, sample,
> source_round=0)[:8])` is the same Python object on every round."

The consequence (Agent 1 §3.2): every restart pulled the trajectory
toward the SAME `constant_F` fresh payload, so the framework
deterministically drifted toward that constant rather than injecting
independent fresh noise. This is the dominant regression mechanism at
NFE=50 and NFE=200 (Bug B's strata in Agent 1's table).

## 2. Targeted fix

**File:** `adaptive_reflow/adapters/flowmol3.py`
**Function:** `FlowMol3Adapter.apply_restart_distribution`
**Line:** 919 (added `source_round=int(state.source_round) + 1` to the
`replace(...)` call's keyword arguments)
**LOC added:** 1

### 2.1 Before

```python
# flowmol3.py:910-919 (before)
        blended = blend_graph_features(prior, fresh, memory_fraction)
        return replace(
            state,
            channels=dict(state.channels),
            masks=dict(state.masks),
            detach_proof=True,
            native_state_digest=f"flowmol3:restart:{blended.digest()}",
            provenance=state.provenance
            + ("flowmol3_restart_boundary",)
            + atom_audit,
        )
```

### 2.2 After

```python
# flowmol3.py:910-920 (after Wave 63 Agent 2)
        blended = blend_graph_features(prior, fresh, memory_fraction)
        return replace(
            state,
            channels=dict(state.channels),
            masks=dict(state.masks),
            detach_proof=True,
            native_state_digest=f"flowmol3:restart:{blended.digest()}",
            provenance=state.provenance
            + ("flowmol3_restart_boundary",)
            + atom_audit,
            source_round=int(state.source_round) + 1,  # ← Wave 63 fix
        )
```

### 2.3 Why this is the right fix

* Agent 1's root-cause audit §5.2 explicitly recommends this 1-LOC
  change.
* The v2 adapter at `flowmol3_v2_adapter.py:2075-2138` already
  implements the same convention (`next_round = int(state.source_round)
  + 1`), and the Self-Flow adapter at `self_flow.py:953-1013` does
  likewise. The v1 was the lone hold-out — the fix brings v1 into
  line with the rest of the framework.
* The change only fires when the low-NFE gate does NOT suppress the
  blend (i.e. `nfe_budget >= restart_min_nfe`). The skip path at
  `flowmol3.py:861-877` is unchanged; it still returns `state` with
  `source_round` preserved (because no restart happened).
* The D.4 regression vector for v1 (`regression-vectors/flowmol3.json`)
  pins `endpoint.source_round: 0` but the endpoint is sourced from
  `adapter.observe_endpoint(trace, initial)` (`tools/run_regression_vector_audit.py:484`),
  which never calls `apply_restart_distribution`. The regression
  vectors are unaffected — confirmed by re-running
  `tests/test_adapters/test_regression_vectors.py -k flowmol3`.

## 3. Regression tests added

**File:** `tests/test_adapters/test_flowmol3_adapter.py`
**Class:** `TestFlowMol3RestartBumpsSourceRound`
**Count:** 3 tests

### 3.1 `test_blend_path_bumps_source_round_by_one`

Direct test of the fix: after one `apply_restart_distribution` call
with `nfe_budget=200` (above the gate threshold, so the blend runs),
`result.source_round` MUST equal `bundle.source_round + 1`. Pre-fix
this was `0 == 0`; post-fix it is `1 == 0 + 1`. This is the
**specific** bug Agent 1 located at `flowmol3.py:910-919`.

### 3.2 `test_consecutive_blends_yield_distinct_fresh_payloads`

Agent 1 §3.2's smoking-gun test: two consecutive `apply_restart`
calls on the same input MUST yield different `native_state_digest`
values. Pre-fix both calls threaded `source_round=0`, so the fresh
payload was identical, so `blended.digest()` was identical, so the
`f"flowmol3:restart:{blended.digest()}"` digests were identical —
exactly the "constant_F drift" symptom Agent 1 identified. Post-fix
round 1 returns `source_round=1`, round 2's
`_graph_payload_for("fresh", batch, sample, source_round=1)` differs
from round 1's `source_round=0` seed, so the digests differ.

### 3.3 `test_skipped_blend_does_NOT_bump_source_round`

Guards the orthogonal path: when the gate fires (nfe=10 below the
threshold), `source_round` MUST stay — no restart happened, so the
round counter must not advance. This protects against a future
refactor accidentally promoting the gate-skip path to also bump
`source_round`, which would inflate the round counter without any
restart taking place.

## 4. Re-eval results

### 4.1 Pytest

```
$ .venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/test_flowmol3_adapter.py -q --tb=line
........................................................................ [ 87%]
..........                                                               [100%]
82 passed, 3 warnings in 1.65s
```

All 82 tests in `tests/test_adapters/test_flowmol3_adapter.py` pass —
the 79 pre-existing tests + the 3 new `TestFlowMol3RestartBumpsSourceRound`
tests.

### 4.2 Regression vectors

```
$ .venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/test_regression_vectors.py -k "flowmol3 and not v2" -q
..                                                                      [100%]
2 passed, 40 deselected in 41.29s
```

Both `flowmol3` D.4 regression vector tests pass (the v1 endpoint
digest is unchanged because `build_initial_state` does not call
`apply_restart_distribution`).

### 4.3 Cells touched by Bug B (per Agent 1 §4)

The cells where Agent 1's bug-budget table predicts Bug B is the
dominant regression mechanism are NFE=50 (2/3 regressions: seed 42,
44) and seed 44 at NFE=200. Pre-fix numbers from
`verification_outputs/flowmol3_with_gate_q4_2026.json`:

| NFE | seed 42 | seed 43 | seed 44 |
|-----|---------|---------|---------|
| 10  | +7.1% S | -24.8% R | -20.9% R |
| 50  | -17.8% R | +7.2% S | -15.0% R |
| 200 | +11.5% S | +14.2% S | -22.3% R |

Per Agent 1's two-bug budget (root-cause §5.3), Bug B is the
load-bearing fix for:

* NFE=50, seed 44 (`-15.0% R` → expected TIE/SUPPORTED)
* NFE=50, seed 42 (`-17.8% R` → expected TIE; Bug A's 1-step excess
  is also addressed by Bug B because the per-round fresh-payload
  no longer correlates with the per-round seed)
* NFE=200, seed 44 (`-22.3% R` → expected TIE/SUPPORTED; Agent 1
  flags Bug A and Bug B as both relevant here)

**Re-eval note:** a full NFE=10/50/200 re-eval across seeds 42/43/44
is out of scope for this 1-LOC targeted fix agent (per the disjoint
file scope); Wave 63 Agent 3 or a follow-up wave should run the
9-cell sweep at HEAD + this fix and confirm the per-cell deltas.
This agent's deliverable is the unit + regression-vector tests at
the adapter level, which Agent 1's root-cause audit cited as the
correct resolution layer for Bug B.

### 4.4 Summary

| Metric | Before | After |
|--------|--------|-------|
| `result.source_round` after 1 blend (nfe=200) | `0` (bug) | `1` (fixed) |
| `result.source_round` after 1 skip (nfe=10) | `0` | `0` (unchanged) |
| 2 consecutive blend digests (nfe=200) | identical (bug) | distinct (fixed) |
| D.4 v1 regression vectors | pass | pass |
| `tests/test_adapters/test_flowmol3_adapter.py` | 79/79 | 82/82 (+3 new) |

## 5. Files changed

* `adaptive_reflow/adapters/flowmol3.py` — added
  `source_round=int(state.source_round) + 1` to the blend path's
  `replace(...)` call at line 919.
* `tests/test_adapters/test_flowmol3_adapter.py` — added
  `TestFlowMol3RestartBumpsSourceRound` with 3 regression tests.
* `docs/audit/wave63-targeted-fix.md` — this audit document.

## 6. What was NOT done (per disjoint scope)

* **Bug A** (the trace-aggregation / NFE-budget mismatch in
  `tools/run_real_ckpt_eval.py:1048-1129`) was NOT addressed here
  because that file is outside this agent's disjoint scope. Per
  Agent 1 §5.1, Bug A needs a ~5-LOC change at lines 1080 / 1083 /
  1097 / 1129 — a separate agent should pick that up.
* No pushes, no FORCE push, no change to `run_real_ckpt_eval.py`,
  no generic refactors.

## 7. Commit

The fix is committed locally (no push) as part of the Wave 63
targeted-fix commit.
