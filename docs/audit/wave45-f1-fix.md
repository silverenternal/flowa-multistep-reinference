# Wave 45 Agent A — F-1 fix: kanzi.observe_token_indices src_digest

**Date:** 2026-09-07
**Wave:** Wave 45 Agent A
**Mode:** Code fix + regression test + audit doc (no push).
**Scope:** `adaptive_reflow/adapters/kanzi.py` (3 put sites),
`tests/test_adapters/test_kanzi.py` (2 new tests), this doc.

## 1. Symptom (verbatim from `wave45-local-review.md` §3 F-1)

`KanziAdapter.observe_token_indices` (kanzi.py:1623) walks a
native-state chain looking for `discrete_idx`, hopping via the
`src_digest` key:

```python
1680:  src_digest = str(traj_entry.get("src_digest", ""))
1681:  for _ in range(int(KANZI_NATIVE_STATES_MAXSIZE)):
1682:      if not src_digest: break
```

**None of the five `_native_states.put(...)` payloads in the file ever
stored a `src_digest` key.** So line 1680 always read `""`, line 1682
broke on the first iteration, `discrete_idx` stayed `None`, and the
fallback at 1695-1710 (a uniform random draw over `[0, 64)`) was
returned every time.

**Consequence.** Every Kanzi Tier-3 metric since Wave 44 was measuring
noise in BOTH arms — the `tools/run_real_ckpt_eval.py` `_real_protein_sequence_validity_rate`
helper (860-1010) consumes this and labels it a "real" metric.

## 2. Fix

3-LOC adapter-layer fix. Add `"src_digest": str(state.native_state_digest)`
to the three put payloads that are sources of a downstream
`observe_token_indices` chain-walk:

| put site | method | previously stored keys | after F-1 |
| --- | --- | --- | --- |
| 1058 `build_initial_state` | initial | `x0, discrete_idx, source_round, mode, conditioning_hash` | unchanged (root of chain; no `src_digest` needed) |
| **1205 `apply_restart_distribution`** | restart | `x0, discrete_idx, source_round, mode, conditioning_hash` | + `src_digest` |
| **1490 `solve_ode`** | trajectory | `trajectory, t_grid, mode, conditioning_hash` | + `src_digest` (CRITICAL) |
| 1552 `observe_endpoint` | endpoint | `x, t, mode, conditioning_hash` | unchanged (terminal observation; chain walks past it via traj entry) |
| **1755 `inject_forward_noise`** | injected | `x0, discrete_idx, source_round, mode, conditioning_hash` | + `src_digest` |

**The critical site is 1490** (the trajectory entry) — that is the
entry the chain-walk fetches first via `trace.native_state_digest`, and
without `src_digest` it terminates with `discrete_idx = None` and falls
through to random. The 1205 and 1755 additions are defensive: they
let the chain walk past a restart / injected entry to an earlier prior
in case a future protocol change ever drops the `discrete_idx` carry
on those entries.

The `digest_state({...})` payloads already carried `src_digest`
(1192, 1476, 1542). Only the **stored** payloads (which are what the
chain-walk actually fetches) lacked the key.

## 3. Runtime verification

End-to-end check (KanziAdapter, synthetic mode, `seed=42`):

```
traj_entry has src_digest : True
src_digest value          : 6803ce719e9981f78c4cc9b68cda9d5a6ec5a694a1ca2ff7e2b22b26f5bf3d3c
real_idx[:8]              : [58, 17, 43, 1, 21, 2, 19, 50]
observed[:8]              : [58, 17, 43, 1, 21, 2, 19, 50]
MATCHES_REAL_STATE        : True
IS_RANDOM_FALLBACK        : False
```

Compare against the pre-fix runtime in `wave45-local-review.md` §3 F-1
(`IS_RANDOM_FALLBACK : True`, `MATCHES REAL STATE : False`). The
metric axis is now wired correctly.

## 4. Regression tests

Two new tests appended to `tests/test_adapters/test_kanzi.py`:

| Test | Asserts |
| --- | --- |
| `test_observe_token_indices_returns_stored_discrete_idx_not_random` | (a) the trajectory entry carries `src_digest`; (b) it equals `bundle.native_state_digest`; (c) the observed array **equals** the stored AR prior `discrete_idx` (overwhelmingly unlikely for a random draw over `[0, 64)` for length 64, `p ~ 64^{-64}`) |
| `test_observe_token_indices_chain_walk_through_restart` | exercises the second F-1 invariant (restart put at 1205): round 1 restart → round 2 solve_ode, the chain walk must terminate at the original prior's `discrete_idx`, which is preserved untouched by `apply_restart_distribution` |

Both tests would have **failed pre-fix** because:
- The first would have hit the random fallback.
- The second would have hit the random fallback after the restart.

Both pass post-fix.

## 5. Test results

```
$ .venvs/kanzi_venv/bin/python -m pytest tests/test_adapters/test_kanzi.py -q --tb=line
35 passed, 4 warnings in 6.52s

$ .venvs/kanzi_venv/bin/python -m pytest tests/test_framework/test_adapter_observe_token_indices.py -q --tb=line
9 passed, 3 warnings in 5.66s
```

35 kanzi-adapter tests pass (the 33 existing + the 2 new F-1 tests);
the 9 observe_token_indices smoke tests still pass.

## 6. What this does NOT fix (escalation per wave45-local-review.md)

- **F-2** — eval pipeline `export_endpoint(trace)` / `apply_restart_distribution(bundle=, trace=, round_index=)` signature mismatch. Outside this agent's disjoint file scope (`tools/run_real_ckpt_eval.py`). The framework arm still exits the loop after one round; until this is fixed, every Wave 45 Kanzi feature remains unmeasurable.
- **F-3** — `paper_quantities=None` at every call site. Outside this agent's disjoint file scope (same tool). Producer side never wired.
- **1552 `observe_endpoint`** also lacks `src_digest` in its stored payload. Not required for the basic chain walk (the walk starts at the trajectory entry, not the endpoint entry); left unchanged to keep this fix ~3 LOC.

## 7. Constraint compliance

- `framework/`, `scheduler/`, `paper_quantities`, `regression-vectors`, `test_claims`, `_adapter_common`, other adapters, `run_real_ckpt_eval.py` — **untouched**.
- Only `kanzi.py` (3 put sites) and `tests/test_adapters/test_kanzi.py` (2 appended tests) modified.
- Commit (no push) per directive.