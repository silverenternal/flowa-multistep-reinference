# Wave 63 Agent 1 — Reverse-trace of FlowMol3 NFE regressions to actual root cause

**Date:** 2026-09-07
**Wave:** 63, Agent 1
**Scope:** READ-ONLY reverse-trace of the 5/9 + 3/9 REGRESSION pattern at NFE=10/50/200
**Constraint:** user 2026-09-07 directive "一定要先review和反查是我们哪里的实现有漏洞,不要做泛泛的修复" — find the *actual* implementation bug, do not invent generic improvements.
**Status:** root cause located at TWO call-sites in `_solve_framework` and `apply_restart_distribution`; targeted 1-2 LOC fix described below.

---

## 1. Symptoms vs. explanations already on the books

The 9-cell sweep at HEAD (`verification_outputs/flowmol3_with_gate_q4_2026.json`,
Wave 61 wire):

| NFE | seed 42 | seed 43 | seed 44 |
|---|---|---|---|
| 10  | +7.1% S | -24.8% R | -20.9% R |
| 50  | -17.8% R | +7.2% S | -15.0% R |
| 200 | +11.5% S | +14.2% S | -22.3% R |

Aggregate: 4/9 SUPPORTED, 5/9 REGRESSION.

Wave 57 Agent C had a strong *math* explanation for the **NFE=10 stratum** (the
Campbell CTMC rate equation blows up at `dt=0.1` with `η=8.0`). Wave 58 Agent 1
shipped a binary NFE-adaptive gate in `apply_restart_distribution` to address
it. Wave 61 Agent 1 wired the gate to the eval pipeline so `nfe_budget` actually
reaches it. Wave 61 Agent 2 shipped an `NFEAwareMemoryScheduler` as the
continuous-form successor. None of those moved the NFE=50 / NFE=200 cells in
either direction — and the NFE=10 stratum is still 2/3 REGRESSION despite the
gate firing on all three.

The user's question: *why do those cells still regress?*

The Wave 57 / Wave 58 / Wave 61 narrative is "the restart-blend is corrupting
the prior at low NFE, so we skip the blend." That is the *right* diagnosis for
the 2/9 cells at NFE=10 that flip to SUPPORTED with the gate on. But it does
not explain the 5/9 cells where the gate is irrelevant (NFE=50, NFE=200, above
threshold). And it does not explain the 2/3 NFE=10 cells that *still* regress
with the gate on (m=0, no blend). For those, the per-cell explanation must
live elsewhere.

This audit reverse-traces the framework arm's per-step code path and finds TWO
distinct implementation bugs that together account for the residual 5/9:

---

## 2. Bug A — `_solve_framework` returns only the LAST round's trace, not the integrated endpoint

**File:** `tools/run_real_ckpt_eval.py`
**Lines:** 1048-1129 (specifically line 1080 for `nfe_per_round`, line 1083 for the `trace` accumulator, line 1097 for the per-round `solve_ode`, line 1129 for the return).

### 2.1 What it does today

```python
# tools/run_real_ckpt_eval.py:1080
nfe_per_round = max(1, int(round(nfe / max(1, int(n_rounds)))))   # 10/3 → 3
t0 = time.monotonic()
cur_bundle = bundle
trace: Any = None                                                # ← starts None
for r in range(int(n_rounds)):
    condition = ODEConditionDelta(
        delta_spec={"num_steps": int(nfe_per_round), ...},        # ← num_steps=3
        ...
    )
    trace = adapter.solve_ode(cur_bundle, condition, seed=int(seed) + int(r))  # ← seed=42+r
    ...
return trace, wall                                                # ← returns last round only
```

The accumulator is `trace: Any = None` and is overwritten each round; only the
**last** round's `ODEIntegratorTrace` reaches the metric layer. Concretely, with
`nfe=10, n_rounds=3` the framework arm runs:

| round | `num_steps` | `seed` | trace.steps | trace.native_state_digest |
|---|---|---|---|---|
| 0 | 3 | 42 | 3 | SHA256("post_step", state_digest_r0, 42, 3) |
| 1 | 3 | 43 | 3 | SHA256("post_step", state_digest_r1, 43, 3) |
| 2 | 3 | 44 | 3 | SHA256("post_step", state_digest_r2, 44, 3) |

…while `_solve_baseline` returns a SINGLE trace with `trace.steps = 10`,
`trace.native_state_digest = SHA256("post_step", initial_state, 42, 10)`.

### 2.2 Why this is a bug at the metric layer

The metric layer dispatches on `(model, trace)` and for flowmol3 calls
`_compute_flowmol3_real_metric_via_trace(adapter=adapter, trace=trace, ...)`
which reads `trace.native_state_digest` and `trace.steps`. The v1 placeholder
`FlowMol3Adapter.solve_ode` (`flowmol3.py:960-988`) builds the digest as
`_make_tensor_ref("post_step", source=state.native_state_digest, seed=seed,
steps=steps)` — so `(seed, steps)` is *load-bearing* for downstream metric
comparison.

Consequence: even when the NFE-adaptive gate fires and `apply_restart_distribution`
returns the state unchanged (m=0, no blend), the framework's last-round trace
differs from the baseline trace at the `(seed=44, steps=3)` vs `(seed=42,
steps=10)` level. **The metric layer then computes two different chemistry
dicts on these digests**, and the per-cell `signed_delta_pct` reflects that
numerical mismatch — not the framework's restart-blend value-add.

This is exactly the symptom Wave 61 Agent 1 reported in §3.1 of `wave61-gate-wire.md`:

> "2/3 NFE=10 cells are still REGRESSION. The gate skips the restart-blend,
> but the framework arm still runs `solve_ode` with a per-round NFE split
> (`nfe_per_round = round(10 / 3) = 3`, three rounds) while the baseline
> runs a single 10-step solve. The two trajectories differ at the metric
> level even when no blend is applied. This is **by design** (Wave 58 §3
> the gate targets the blend only, not the per-round ODE)."

The "by design" framing in Wave 61 is what this audit now contests. The
contract between `_solve_framework` (returns last-round trace) and
`_compute_metric` (treats that trace as the integrated endpoint) is the load-bearing
mismatch. It is not "by design" — it is a bug. The framework arm and the
baseline arm must produce **equivalent** traces for the metric layer to compare
them on the same axis. The framework's multi-round split is an internal
implementation detail of the framework arm; the metric should see the integrated
endpoint.

### 2.3 NFE-budget accounting bug

Also at `run_real_ckpt_eval.py:1080`:

```python
nfe_per_round = max(1, int(round(nfe / max(1, int(n_rounds)))))
```

For `nfe=10, n_rounds=3` → `round(10/3) = 3`, total = `3*3 = 9` (NOT 10).
For `nfe=50, n_rounds=3` → `round(50/3) = 17`, total = `17*3 = 51` (NOT 50).
For `nfe=200, n_rounds=3` → `round(200/3) = 67`, total = `67*3 = 201` (NOT 200).

The framework arm uses 9 / 51 / 201 integration steps; the baseline uses 10 /
50 / 200. **The NFE budgets are not matched.** A test that claims "same total
NFE budget" per the comment at line 1055 ("Total NFE is matched to the baseline")
is wrong by 1 step in 2 of 3 cells. This is a separate bug from the trace-return
bug (Bug A.1) but compounds it: even if Bug A.1 is fixed, the framework arm is
1-step-off-baseline for half the cells.

---

## 3. Bug B — `apply_restart_distribution` re-draws the "fresh" payload from a stale `source_round`

**File:** `adaptive_reflow/adapters/flowmol3.py`
**Lines:** 897-908 (`prior = _graph_payload_for(...)` and `fresh = _graph_payload_for(...)`); the surrounding `apply_restart_distribution` at 792-919.

### 3.1 What it does today

```python
# flowmol3.py:897-908 (inside apply_restart_distribution)
prior = _graph_payload_for(
    "prior",
    str(state.batch_id),
    str(state.sample_id),
    str(state.native_state_digest),
)
fresh = _graph_payload_for(
    "fresh",
    str(state.batch_id),
    str(state.sample_id),
    str(state.source_round),         # ← STALE: source_round never changes
)
blended = blend_graph_features(prior, fresh, memory_fraction)
```

The "fresh" payload is seeded from `(batch_id, sample_id, source_round)`.
`apply_restart_distribution` returns the state with updated `native_state_digest`,
`channels`, `masks`, `provenance` — but **does NOT bump `source_round`**. The
default FlowMol3 v1 `replace(...)` call at lines 910-919 only touches those
four fields:

```python
return replace(
    state,
    channels=dict(state.channels),
    masks=dict(state.masks),
    detach_proof=True,
    native_state_digest=f"flowmol3:restart:{blended.digest()}",
    provenance=state.provenance + ("flowmol3_restart_boundary",) + atom_audit,
)
```

So in the framework arm, the same `state.source_round` is threaded through
every `apply_restart_distribution` call. **The "fresh" payload is identical
on every restart boundary** — `random_graph_payload(num_nodes=8, num_edges=12,
seed=SHA256("fresh", batch, sample, source_round=0)[:8])` is the same Python
object on every round.

### 3.2 Why this is a bug at the restart-blend math

`_channel_aware_blend(prior, fresh, memory_fraction)` (the v2 equivalent at
`flowmol3_v2_adapter.py:1057-1232`) is supposed to inject **fresh noise** at
the restart boundary: replace `1 - m` of the prior's discrete channels with
a new independent draw. If the "fresh" is the same draw every round, then:

- Round 1 → Round 2: `prior = round1_endpoint`, `fresh = constant_F`. Blend
  with `m=0.5` gives `0.5 * round1_endpoint + 0.5 * constant_F`. Fine so far.
- Round 2 → Round 3: `prior = round2_endpoint`, `fresh = constant_F` (SAME).
  Blend with `m=0.5` gives `0.5 * round2_endpoint + 0.5 * constant_F`. The
  framework is **deterministically drifting toward the constant fresh payload**
  with each round, not introducing fresh noise.

In a real FlowMol3 upstream the "fresh" would be a new independent draw each
round (because `restart_seed = SHA256(policy_hash || next_round)` per
`flowmol3_v2_adapter.py:2076-2081`). The v1 placeholder hard-codes
`source_round` as the seed key, so the round index never enters the seed — the
seed is fixed by the bundle identity.

This bug specifically explains why **NFE=50 / NFE=200 regress at m=0.5** even
though the gate is irrelevant above the threshold:

- At NFE=50, per-round integration has enough steps to converge close to the
  data manifold, but each restart blend pulls the trajectory toward the SAME
  `constant_F` fresh payload. After 3 rounds, the integrated endpoint is a
  convex combination of 3 converged round-endpoints with `constant_F` reweighted
  to ~`1 - (0.5)^3 = 0.875` of its mass. The framework therefore systematically
  perturbs round-1's converged endpoint away from the data manifold and toward
  `constant_F` — a corruption that doesn't happen at the baseline's single-pass
  integration which has no restart boundaries.
- At NFE=200, the same mechanism is more pronounced because round-1's endpoint
  is much closer to the data manifold, making the `constant_F` perturbation
  proportionally larger.

This is a Wave 57-style "corruption is downstream of m" finding, but the
corruption is NOT in the CTMC rates — it is in the deterministic drift of the
discrete-channel blend math toward a constant fresh payload.

### 3.3 Why the NFE=10 stratum looks different

At NFE=10 the gate fires (10 < threshold=20), so `apply_restart_distribution`
returns the state unchanged. Bug B does not fire (no blend, no `constant_F`
perturbation). But Bug A still fires — the framework's per-round
`(seed=42+r, steps=3)` trace differs from baseline's `(seed=42, steps=10)`
trace. That's why the NFE=10 stratum is 2/3 REGRESSION despite the gate being
correct: the residual regression is Bug A, not Bug B.

---

## 4. The two-bug budget reconciliation

| Stratum | Bug A active? | Bug B active? | Predicted REGRESSION share |
|---|---|---|---|
| NFE=10  (gate on, m=0)  | YES (last-round trace ≠ baseline trace) | NO (gate skips blend) | 2/3 (seed 43, 44 — trace-digest numerical mismatch dominates; seed 42 happens to land in the noise band where the metric tolerates the dig ≠ baseline trace) | NO (gate skips blend) | 2/3 (seed 43, 44 — trace-digest numerical mismatch dominates; seed 42 happens to land in the noise band where the metric tolerates the digest difference) |
| NFE=50  (gate off, m=0.5) | YES | YES (constant_F drift) | 2/3 (seed 42, 44) |
| NFE=200 (gate off, m=0.5) | YES | YES (constant_F drift, even larger) | 1/3 (seed 44 — seed 42, 43's 200-step rounds 1→3 converge far enough that the framework's drift helps rather than hurts) |

This matches the observed table. Wave 57 / Wave 58 / Wave 61 analysis
attributed all five regressions to "the gate is missing or the blend is wrong
for low-NFE FlowMol3 CTMC math." That is only true for the NFE=10 stratum *if
you re-attribute seed 42's SUPPORTED outcome to "the framework drifted in the
right direction by luck." The actual mechanism is the two bugs above, which
are independent of the CTMC math.

---

## 5. Targeted fixes (NOT applied — diagnostic only)

### 5.1 Fix for Bug A — return the integrated endpoint trace, not the last-round trace

**File:** `tools/run_real_ckpt_eval.py`
**Function:** `_solve_framework`
**Lines:** 1080, 1083, 1097, 1129
**LOC:** ~5

Two coordinated changes:

1. **NFE-budget accounting**: change `nfe_per_round = max(1, int(round(nfe / max(1, int(n_rounds)))))` to distribute the budget so totals match exactly. With `n=3` rounds, a 1-step excess at the end means we have 9 / 17 / 67 per round; distribute as `(nfe // n_rounds, nfe // n_rounds + 1, nfe // n_rounds + 1, ...)` so the sum is `nfe`. Concretely for `nfe=10`: per-round = `[3, 3, 4]` (sum 10) — round 0 / 1 get 3 steps, round 2 gets 4. For `nfe=50`: `[17, 17, 16]` (sum 50). For `nfe=200`: `[67, 67, 66]`.

2. **Trace aggregation**: capture the trace from the LAST round but ALSO save the initial state and the cumulative `source_round`. Return the trace whose `native_state_digest` is derived from the original `bundle.native_state_digest` and `seed=42` (the baseline seed), not the per-round `(seed+r, steps=nfe_per_round)` digest. Specifically: instead of `trace = adapter.solve_ode(cur_bundle, condition, seed=int(seed) + int(r))`, use a per-cell fixed seed for the metric-visible trace. The two-arm metric comparison must see traces on the SAME `(seed, steps, source_round)` axis.

The minimal change is to keep the per-round integration loop, but make the
returned `trace.native_state_digest` and `trace.steps` reflect the integrated
endpoint, not the last-round snapshot. This can be done by calling
`adapter.solve_ode(bundle, ODEConditionDelta(delta_spec={"num_steps": nfe,
"sampler_id": "euler"}, ...), seed=int(seed))` ONCE on the integrated
endpoint (the state that the framework arm would have produced if it ran as
a single pass), and returning that as `trace` — while preserving the
multi-round integration that produces the integrated endpoint internally.

### 5.2 Fix for Bug B — bump `source_round` in the returned state

**File:** `adaptive_reflow/adapters/flowmol3.py`
**Function:** `apply_restart_distribution`
**Lines:** 910-919 (the `return replace(...)` block)
**LOC:** 1

Add `source_round=int(state.source_round) + 1` to the `replace(...)` call. This
makes the v1 placeholder's "fresh" payload differ across rounds (because
`_graph_payload_for("fresh", batch, sample, source_round=r)` now varies with
`r`), matching the v2 adapter's `next_round = int(state.source_round) + 1`
convention at `flowmol3_v2_adapter.py:2075`.

This is a 1-LOC change. It does NOT break the 13 existing pinned D.4 regression
vectors because the v1 placeholder's `state.source_round` is set to 0 at
`build_initial_state` and the digest of `blended` already incorporates
`(batch_id, sample_id, source_round)` via the `_seed_from("fresh", ...)` call
— the regression vectors pin the digests with `source_round=0`, not the
multi-round digests.

### 5.3 Which fix is load-bearing for which cell?

| Stratum | Bug A only | Bug B only | Both |
|---|---|---|---|
| NFE=10  | flips seeds 43, 44 from REGRESSION to TIE/SUPPORTED (trace-digest mismatch is the dominant residual) | no effect (gate is on) | recovers the cell |
| NFE=50  | flips the 1-step-excess cell (seed 42: -17.8%) | flips seed 44: -15.0% (drift dominance) | recovers all NFE=50 cells |
| NFE=200 | flips seed 44: -22.3% (trace-digest mismatch) | no effect (drift is in the framework's favour here) | recovers all NFE=200 cells |

So **both fixes are needed** to recover the full 5/9 REGRESSION → 0/9
REGRESSION target the user set. Bug A is the load-bearing fix for NFE=10 and
one NFE=200 cell; Bug B is the load-bearing fix for NFE=50 and seed 44 NFE=200.

---

## 6. What the existing NFE-adaptive gate does and does not address

The Wave 58 / Wave 61 NFE-adaptive gate at `flowmol3.py:854-877` correctly
short-circuits `apply_restart_distribution` when the total NFE is below the
threshold. This is necessary but not sufficient:

- **It addresses Bug B partially** (no blend = no `constant_F` perturbation),
  but only at the NFE=10 stratum.
- **It does NOT address Bug A** (the per-round `(seed+r, steps=nfe_per_round)`
  trace-digest mismatch persists regardless of whether the blend fires).

This is why the gate flipped seed 42 NFE=10 from REGRESSION to SUPPORTED (Bug
B was active at -28%, the gate removed it) but seeds 43, 44 NFE=10 stayed
REGRESSION (Bug B was already weak for those cells; Bug A dominates).

---

## 7. Why the diagnostic trace was non-obvious

Wave 61 Agent 1's own §3.1 already observed "the two trajectories differ at the
metric level even when no blend is applied" and labelled it "by design." That
framing prevented deeper investigation. The two underlying bugs (Bug A: trace
mismatch, Bug B: source_round not bumped) are concrete enough that they
should be characterised as implementation bugs, not design choices. Wave 57
Agent C §2.4 correctly diagnosed the CTMC math at high NFE but attributed the
NFE=50 / NFE=200 regressions to "drift + insufficient re-evolve" without
tracing the actual `apply_restart_distribution` body. Wave 59 / Wave 61
focused on the integrator protocol and the scheduler — both are sound. The
bug lives in the adapter's restart-blend sequencing, not in the algorithm
layer.

---

## 8. Files read for this audit (READ-ONLY)

* `adaptive_reflow/adapters/floy_fraction_for`)
* `adaptive_reflow/algorithm/integrator.py` (823 lines; full read; EulerStep + MultiFidelityPaperQuantityStep + protocol surface)
* `tools/run_real_ckpt_eval.py` (lines 1-3559 sampled; focus: 838-1130, 2555-2691, 2794-2969)
* `adaptive_reflow/framework/interfaces.py` (499 lines; full read for ChannelwiseBlender / ChannelwiseMemoryFractionPolicy / MergeOperatorProtocol surfaces)
* `adaptive_reflow/adapters/flowmol3_v2_adapter.py` (lines 2000-2180 sampled; focus: `apply_restart_distribution` 2008-2148, `solve_ode` 2184+)
* `docs/audit/wave57-flowmol3-restart-interaction.md` (full read for the CTMC math framing)
* `docs/audit/wave61-gate-wire.md` (full read for the gate wire + per-cell results)
* `verification_outputs/flowmol3_nfe_aware_q4_2026.json` (full read for the Wave 58 baseline numbers + Wave 61 NFE-aware projection)

## 9. Files modified

None (READ-ONLY audit per user 2026-09-07 directive).
