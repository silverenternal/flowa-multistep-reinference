# Wave 35 Agent A — Algorithm saturation-speed review

**Date:** 2026-09-05
**Wave:** Wave 35 Agent A
**Scope:** Why does the framework saturate at 275 NFE instead of
the target ≤ 50 NFE on the `twodim_fm`-class regime?
**Files audited:** 6 (see §7)
**Lens:** "what code path forces the framework to use the full NFE
budget even when earlier rounds have already converged?"

The headline numbers (`G.5 saturation point = 275 NFE, target ≤ 50 NFE`)
come from the matched-NFE baseline-vs-framework comparison grid run
under `tools/run_controlled_audit.py`. The hypothesis we test here is
the framework's documented "framework needs full NFE budget to deliver
95% quality" — i.e. there is no engine-level early-termination
signal, and several layers actively *prevent* NFE savings.

The short answer is: **the framework is structurally open-loop on
round count, structurally uniform in per-round NFE allocation, and
its merge operator's late-round floor actively forces the inner
solver to keep running**. None of these properties is a bug; they
are deliberate choices in the algorithm-layer / runner contract.
Closing the saturation gap requires engine-level convergence
detection (or a hard NFE ceiling with adaptive round skipping),
both of which currently exist as no-op paths.

---

## 1. `adaptive_reflow/algorithm/scheduler/_core.py` (4511 LOC)

The scheduler module exposes 10+ scheduler families. Three of them
are the candidates that should plausibly drive "convergence-aware"
NFE savings. None does.

### 1.1 `CodimensionSheetScheduler` (lines 2763-3480) — primary driver

* **Open-loop on rounds.** `sample()` is a pure closed-form
  ``n_cap = n_min + (n_max - n_min) * ratio`` driven by the
  per-round `eps_per_round` and the cached paper quantities
  `A_g / B_g / C_g / e_rho` (line 3282). The method does not
  inspect prior rounds' `evidence_ratio` history, the W2 trend, or
  any convergence signal — it returns the same monotonic ramp
  regardless of whether the round is the 1st or the 20th.
* **`record_round_feedback` is a no-op.** Line 3373: ``Default no-op:
  the codimension scheduler is open-loop on rounds.`` — explicitly
  documented. This means even if the runner has a W2 trend that
  has plateaued, the scheduler cannot react.
* **`cycle_length` is fixed at construction.** Default ``20``
  (line 2844). No method on the class shortens it; no signal on
  the class could shorten it (no `record_round_feedback`, no
  `should_terminate_round`).
* **`cycle_length == 1` is degenerate but legal** (line 3211): the
  scheduler will happily serve a 1-round cycle if asked. Nothing
  in the *engine* wiring asks for it.
* **`eps_per_round` floor is `1e-9`** (line 3244): the per-round
  ``eps`` is floored to ``max(eps_per_round, 1e-9)`` so the cell-
  side collapse is avoided. This is paper-aligned, but it means
  the terminal round still receives a *non-zero* `eps` → a non-
  zero `ratio` < 1 (because `n_cap_base = n_max` at `cycle_length=1`
  → `n_cap = n_max` → terminal capacity is **maximal**, not
  minimal).

### 1.2 `PaperRatioAdaptiveScheduler` (lines 3518-3927)

* **Wraps `CodimensionSheetScheduler` but cannot shorten rounds.**
  `sample()` adds a `shift` (in `n_cap` units) to the wrapped base's
  `n_cap` (line 3727). The shift is bounded by `shift_max=0.15`
  (line 3617), so even at maximum shift the round's effective
  `n_cap` is in `[n_min - 0.15, n_max + 0.15]` — the scheduler can
  nudge capacity but cannot exit a round early.
* **Closes the loop only via `record_round_feedback`** (line 3826),
  which consumes a `paper_quantities` dict. The shift update is a
  single additive offset (`shift += kp * (1-sheet_ratio) - kd *
  sheet_delta`, line 3906). There is **no termination criterion**
  and **no per-round NFE scaling**.
* **PID shift_max is documented as 0.15** (default). At `cycle_length=20`,
  the effective `u_r` can move at most ±0.15 — i.e. the scheduler
  effectively compresses or stretches the cycle by ~3 rounds, not
  by 18.

### 1.3 `ConvergenceAdaptiveScheduler` (lines 1883-2633)

* **W2-driven shift of `u_r`.** `sample()` shifts `u_r` by
  `self._shift` (line 2235) before re-deriving `n_cap` via the
  cosine closed form (line 2248). The shift is bounded by
  `shift_max=0.15` (line 1972) — same 3-round compression ceiling.
* **No termination path.** The class has 5 mutable state attributes
  (`_w2_history`, `_smoothed_w2`, `_shift`, `_paper_quantity_*`),
  but none of them feeds a `should_terminate` or `nfe_budget_remaining`
  signal.
* **EMA smoothing `ema=0.3`** (line 1977) means each round's W2
  contributes only 30% to the smoothed signal. With 5 rounds, the
  EMA has barely converged by `cycle_length - 1`; the shift is
  near-zero for the rounds that matter most (terminal refinement).

### 1.4 Scheduler-level summary

| Scheduler | Round count adaptive? | NFE-per-round adaptive? | Convergence detection? |
|---|---|---|---|
| `CodimensionSheetScheduler` | NO (fixed at construction) | NO (caller passes `nfe_per_round`) | NO (`record_round_feedback` is no-op) |
| `PaperRatioAdaptiveScheduler` | NO (inherits from base) | NO (only shifts `n_cap` ±0.15) | NO (only shifts `n_cap`) |
| `ConvergenceAdaptiveScheduler` | NO | NO (only shifts `u_r` ±0.15) | PARTIAL (PID reads W2 history, but does NOT terminate) |
| `SequentialScheduler` | NO (`total_rounds` is sum of slot lengths) | NO | NO (no slot transition trigger) |
| `ExponentialScheduler` | NO | NO | NO |
| `ConstantScheduler` | NO | NO | NO |

**Finding 1 — HIGH:** No scheduler exposes a "this round has converged,
skip the remaining rounds" or "this round needs < N NFE" interface.
The `SchedulerProtocol` (line 177) does not even reserve a method
name for it. The framework's only way to shorten its NFE budget
is for the *caller* to set a shorter `cycle_length` or to terminate
the runner loop externally — neither of which the engine does
today.

**Finding 2 — MEDIUM:** `CodimensionSheetScheduler.record_round_feedback`
is documented as a no-op (line 3373). Wiring it to the same W2-EMA
+ ratio-EMA signals that `ConvergenceAdaptiveScheduler` consumes
would let the paper-quantity-driven scheduler participate in the
convergence detection that `BatchedTrajectoryRunner` already feeds
back (line 884). This is **architecturally free** — the feedback
dict is already routed to the scheduler; the no-op just drops it.

**Finding 3 — LOW:** `shift_max = 0.15` (PID compression ceiling)
is the same for both adaptive schedulers. A 0.30 or 0.50 shift_max
would let the adaptive schedulers compress the cycle by ~6-10
rounds at the boundary — but this still does not terminate rounds,
it just relocates them in `u_r` space.

---

## 2. `adaptive_reflow/algorithm/merge_operator.py` (937 LOC)

The bounded merge is the only piece of the algorithm layer that
sees the round-to-round *envelope* (`prev`, `dynamic`, `cap`,
`floor`, `delta_cap_up/down`). Three properties matter for
saturation speed.

### 2.1 `BoundedMergeOperator.merge` (lines 500-685)

* **Empty-interval collapse returns the floor (line 681):**
  ``if hi < lo: return floor_f``. This is the documented fail-closed
  path. **When the envelope collapses, the merge produces a value
  that the next round's `prev` becomes** — i.e. the merge's
  output is *constant* across rounds, breaking the convergence
  signal in `BatchedTrajectoryRunner.record_round_feedback`.
* **Late-round envelope collapse is the normal case.** When the
  codimension scheduler drives `n_cap → 0` (terminal round),
  `cap = n_cap ≈ 0` and `floor = max(beta_floor, e_rho/4) > 0`.
  The per-round delta interval `[-delta_cap_down, +delta_cap_up]`
  is centred on the previous `prev` (which is itself `≈ 0` from
  the prior round's collapse). Result: the interval collapses to
  `[floor, floor]` for every subsequent round. **The framework is
  paying full NFE per round to recompute a value it already
  knows.**

### 2.2 `BoundedMergeOperator` paper-quantity floor (lines 587-596)

* **`e_rho / 4` floor lift.** When `exterior_gap_e_rho` is supplied,
  the floor lifts to ``max(floor, e_rho / 4)``. This is paper-
  aligned (Lemma 5) and is the right call *for the algorithm* —
  but for *saturation speed* it forces the merge to never go
  below `e_rho / 4`, which means the framework's "memory"
  `1 - n_cap` can never be `> 1 - e_rho/4`. With the default
  `e_rho = 1e-4` (`PAPER_UPLIFT_27_DEFAULT_E_RHO`, line 123), the
  floor is `2.5e-5` — small but not zero.

### 2.3 `EMAOperator` alpha modulation (lines 862-877)

* **Alpha modulated by `n_cap`** (line 876):
  ``alpha = alpha * (1 + schedule_weight * (n_cap_c - 0.5))``.
  When `n_cap_c ≈ 0` (terminal round under the codimension
  ramp), `alpha` is *halved*. The merge step becomes a tiny
  increment that the bounded merge envelope then collapses. This
  is a **double penalty**: low `n_cap` → low alpha → small step
  → envelope collapse → floor. The runner keeps paying NFE for
  the ODE integration, but the merge contributes almost nothing.

### 2.4 `IdentityOperator` (lines 693-763)

* **Returns `dynamic` verbatim**, ignoring the envelope entirely.
  This is the only operator that does NOT collapse at late rounds,
  but it is also the only one that bypasses the bounded semantics
  — and the `BatchedTrajectoryRunner` does not default to it.

### 2.5 Merge-operator summary

**Finding 4 — HIGH:** `BoundedMergeOperator.merge` collapses to the
floor when the envelope interval is empty (lines 669-681), and the
runner keeps paying full NFE per round even though the merged
value is **constant across all collapsed rounds**. The audit
tool's `framework_nfe` field counts every round's NFE (line 305),
so 5 collapsed rounds cost `5 * nfe_per_round` despite producing
zero new information. The cheapest fix is a *return signal* (a
sentinel value or a side-channel) so the runner can detect
"merge collapsed, skip next round".

**Finding 5 — MEDIUM:** The paper-quantity floor lift
(`e_rho / 4`, line 587) interacts with the codimension ramp's
late-round `n_cap → 0` to force the envelope into the collapse
regime. This is paper-aligned but is the proximate cause of the
saturation behaviour at small NFE: the engine cannot reach a
"degenerate identity" regime (where `prev = dynamic = cap = floor`,
so every merge is a no-op) without breaking the floor contract.

---

## 3. `adaptive_reflow/algorithm/batched_runner.py` (949 LOC)

The `BatchedTrajectoryRunner` is the *outer loop* that consumes
the scheduler's `n_cap` and dispatches `T * K` trajectories per
round. It is the natural place to enforce an NFE ceiling, but it
does not.

### 3.1 `run()` loop (line 744)

```python
for r in range(int(cfg.cycle_length)):
    sample = scheduler.sample(int(cfg.outer_cycle_id), r, r)
    n_cap_r = float(sample.n_cap)
    ...
```

* **Hard-coded loop bound.** `range(int(cfg.cycle_length))` —
  no `break`, no `return`, no early termination. The runner runs
  every round regardless of W2 trend, selection_ratio trend, or
  the `n_cap` value (which can be `≈ 0` for the codimension
  scheduler at terminal rounds).
* **No NFE-budget check.** The runner has no `nfe_budget` config
  field. The runner does not know how many total NFE it has
  consumed; it only knows the per-round NFE (`nfe_per_round`)
  baked into the adapter's `num_steps` at construction.
* **No `n_cap`-driven per-round NFE scaling.** Even though
  `n_cap_r` is computed (line 746), it is *not* used to scale
  the round's `num_steps` (which is fixed by the adapter's
  constructor). The codimension scheduler's `evidence_ratio` is
  read by `cfg.selection_evaluator` (line 836) but is **not
  read** to decide whether the round is worth running.
* **`scheduler.record_round_feedback` is the only convergence
  signal** (line 884): ``if hasattr(scheduler, "record_round_feedback"):``
  — but `CodimensionSheetScheduler.record_round_feedback` is a
  no-op (see Finding 2). The signal is *routed but discarded*.

### 3.2 Per-round seeds (lines 757-764)

* **Seeds depend on `n_cap_r`** (``+ int(round(n_cap_r * 1_000_000))``).
  This is the right call for *provenance* (two schedulers with
  different `n_cap` ramps produce disjoint seed spaces), but it
  means the **seed space grows quadratically** with cycle_length
  even when the codimension ramp produces `n_cap_r ≈ 0` for many
  consecutive rounds. Seed-space is not the NFE bottleneck, but it
  is correlated: collapsed-round seeds are still drawn.

### 3.3 `merge_operator` threading (lines 818-833)

* **The runner threads `prev = per_round_metric["merged_beta"][r-1]`
  on round r > 0** (line 822). When the bounded merge collapses
  to the floor (Finding 4), every subsequent round's `prev` is
  the same constant — the runner's W2 signal therefore does NOT
  detect convergence, because the merged beta is *not* a fresh
  measurement.
* **The runner only exercises the merge operator path when
  `cfg.merge_operator is not None`** (line 818). The default
  `None` path emits no `merged_beta` key at all (line 718-719)
  — the audit tool's `_run_twodim_fm` and `_run_lineageflow`
  (in `tools/run_controlled_audit.py`) do NOT pass a merge
  operator, so they are exercising the no-merge path. The
  framework-vs-baseline gap is therefore *purely scheduler-
  driven* on these audit cells.

### 3.4 BatchedRunnerConfig (lines 181-301)

* **No `nfe_budget`, `min_rounds`, `max_rounds`, `convergence_window`,
  or `early_termination_threshold` config fields.** The config
  exposes `cycle_length`, `trajectories_per_round`,
  `endpoints_per_trajectory`, `seed`, `outer_cycle_id`, and the
  optional toggles `forward_noise`, `merge_operator`, `ledger_chain`,
  `w2_family`, `w2_kwargs`, `vectorised`. None of these lets the
  caller say "stop early if W2 has not improved by >0.1% in the last
  2 rounds".
* **Policy-driver and blender slots are deprecated** (line 282,
  292): the runner operates entirely outside the engine's policy-
  driver / blender surface, so the convergence signals those slots
  might provide are **not threaded**.

### 3.5 BatchedRunner summary

**Finding 6 — HIGH:** `BatchedTrajectoryRunner.run()` runs every
round of `cycle_length` unconditionally. There is no early-termination
hook, no NFE budget check, no convergence-window detection. The
runner is structurally unable to deliver NFE savings < `cycle_length
* nfe_per_round`.

**Finding 7 — HIGH:** The runner's `scheduler.record_round_feedback`
call (line 884) is the only convergence signal, but `CodimensionSheetScheduler`
records no feedback (no-op method). The signal is **routed but
discarded at the scheduler layer**. Wiring
`CodimensionSheetScheduler.record_round_feedback` to consume
`{"W2": w2, "selection_ratio": ratio, "paper_quantities": pq}`
would close the loop at zero architectural cost.

**Finding 8 — MEDIUM:** When the bounded merge collapses to the
floor (Finding 4), `prev` becomes a constant for the remaining
rounds. The runner's W2 series (which is computed from the
*endpoint* population, not the merge value) is unaffected, but
the merge value's constancy is a **free convergence signal** that
the runner does not consume. Adding a `merged_beta_collapsed`
audit code would surface this signal at the runner layer.

**Finding 9 — MEDIUM:** `BatchedRunnerConfig` has no NFE-budget
or convergence-window field. The smallest experiment to validate
that such a config field would help is to add an optional
`nfe_budget: int | None` and let the runner terminate when
`sum(nfe_per_round[:r+1]) >= nfe_budget` — but only on the
*schedulers that can report "this round converged"*. Without the
scheduler-side support (Finding 1), this is just an early-exit
hack that terminates before the algorithm has decided to stop.

---

## 4. `adaptive_reflow/algorithm/sequential.py` (521 LOC)

The `SequentialScheduler` chains sub-schedulers by round range
(mirroring `torch.optim.lr_scheduler.SequentialLR`). It is
relevant to saturation speed because **multi-family chains could
plausibly express "stop early at family boundary"**, but the
implementation does not.

### 4.1 `_resolve_slot` (lines 214-240)

* **Round-to-slot mapping is rigid.** `round_in_cycle` is resolved
  to a slot via cumulative offsets; there is no "skip to next slot
  early" path.
* **The chain's `total_rounds` is the sum of slot lengths**
  (line 160). It is fixed at construction.

### 4.2 `record_round_feedback` forwarding (lines 314-365)

* **Feedback is forwarded to every slot** (line 356), not just
  the active one. The A8 uplift explicitly enables chained
  adaptive schedulers to *warm up* before their slot starts.
  But the slot-relative round is clamped to `[0, n_rounds - 1]`
  (line 360), so **feedback-driven slot transitions are not
  supported** — a slot always runs exactly `n_rounds` rounds.

### 4.3 `sample` (lines 244-288)

* **Sub-round translation preserves the slot's own cycle math**
  (line 259). A sub-scheduler with `cycle_length=4` running in a
  slot of length 4 gets `round_in_cycle = 0..3` exactly; if the
  slot has length 8, the sub-scheduler wraps around. Neither case
  shortens the chain.

### 4.4 Sequential summary

**Finding 10 — MEDIUM:** `SequentialScheduler.record_round_feedback`
forwards to every slot (line 356) but does not consume the
feedback to trigger a slot transition. The architecture is **one
line of code away** from supporting "early transition to slot i+1
when W2 plateau is detected": add a `should_advance_slot` method
that callers can query, or check `len(self._w2_history)` and
trigger a slot hop when it stops growing. This is a low-risk
enhancement and would let `codimension_sheet(cycle=10) →
no_op` chains converge in fewer than 20 rounds.

**Finding 11 — LOW:** Sequential chains always run `total_rounds`.
The smallest-experiment validation would be a chain of
`[(CosineAnnealScheduler(cycle_length=5), 5),
(IdentityScheduler(cycle_length=0), 0)]` and verify that the
runner can consume the chain's `cycle_length() == 5` correctly.

---

## 5. `adaptive_reflow/algorithm/evidence_driver.py` (574 LOC)

`EvidenceDrivenScheduler` is the wrapper that modulates an inner
scheduler's `n_cap` by the per-round evidence ratio. Its design
has a **counter-productive effect on saturation speed** that
should be flagged.

### 5.1 `EvidenceDrivenScheduler.sample` (lines 170-195)

* **Formula** (line 186):
  ``driven = float(base.n_cap) * ((1 - strength) + strength * r)``
  where `r = evidence_ratio ∈ [0, 1]`.
* **At terminal round under codimension**, `evidence_ratio → 1`
  (paper Theorem 1's `eps → 0` sheet dominance). `driven ≈
  base.n_cap * 1.0 = base.n_cap`. So the wrapper is identity
  at terminal — fine.
* **At mid-cycle (eps > 0)**, `evidence_ratio` is < 1 (cell side
  contributes), so `driven < base.n_cap`. **This means the
  evidence-driven scheduler REQUIRES less capacity per round** —
  but the bounded merge's envelope is keyed on `n_cap` (via the
  cap / floor arguments), so the merge envelope **shrinks** when
  the wrapper drives `n_cap` down. Net effect: the merge
  collapses to the floor (Finding 4) earlier in the cycle, and
  the merge value is constant for the remaining rounds. The
  framework *appears* to converge faster (per-round memory
  fraction rises faster) but is in fact **terminating the
  algorithm's contribution** earlier.

### 5.2 Strength = 1.0 (default, line 137)

* **Full multiplicative drive** (``n_cap * evidence_ratio``) is
  the canonical paper-aligned mode (Theorem 1 fixed at 1.0 per
  `derive_default_strength`, line 565). The `strength=0` identity
  fallback is bit-identical to the inner scheduler.

### 5.3 Heuristic-mode diagnostic (lines 331-417)

* `check_evidence_mode` flags configurations where the framework
  is using the **heuristic** evidence balance (no `profile_residual_fn`)
  at `eps_implicit < 1e-3`. This is a correctness check, not a
  saturation-speed check — but it intersects saturation speed:
  the heuristic mode keeps `n_cap ≈ n_max` throughout the cycle
  (because `n_cap_base` from the cosine ramp dominates `eps` at
  `eps=0.05` default). The framework thus cannot benefit from
  late-round `n_cap → 0` because `n_cap` is *never* near 0 under
  the heuristic.

### 5.4 Evidence-driver summary

**Finding 12 — MEDIUM:** `EvidenceDrivenScheduler` (with `strength=1.0`)
shrinks `n_cap` mid-cycle and converges the merge to the floor
*earlier* than the codimension scheduler alone. The framework
arm's per-round W2 trend therefore plateaus sooner, but the
plateau is a **constant-floor plateau**, not a true convergence.
The audit tool reports this as "framework converged", but the
trajectory population is **not** the late-round constant it would
be at full NFE — the audit tool's `_per_position_entropy` and
W2 metrics *do* detect this (the W2 series flattens but the
endpoints change), but only on the LineageFlow arm where the
metric is continuous. On twodim_fm the W2 change is real but
small relative to the saturation noise floor.

**Finding 13 — LOW:** `EvidenceDrivenScheduler` is **not** wired
into the `BatchedTrajectoryRunner.run()` loop by default. The
audit tool's `_run_twodim_fm` and `_run_lineageflow` do not pass
a wrapped scheduler. The framework's default
(`CodimensionSheetScheduler`) is paper-quantity-driven but
*without* the evidence-modulation wrapper, so the merge envelope
collapse described in §2 happens naturally at late rounds under
the codimension ramp — but the merge operator is *also* not
wired into the audit tool's framework arms.

---

## 6. `tools/run_controlled_audit.py` (1054 LOC)

The audit tool is the experiment harness behind the saturation
measurement. It is *itself* a constraint on what can be measured.

### 6.1 `_nfe_steps_per_round` (lines 578-599)

```python
base, remainder = divmod(nfe, n_rounds)
return [base + (1 if i < remainder else 0) for i in range(n_rounds)]
```

* **Uniform per-round NFE.** First round gets the same NFE as the
  last round. For `(nfe=50, n_rounds=5)` this is `[10, 10, 10,
  10, 10]`. For `(nfe=275, n_rounds=5)` it is `[55, 55, 55, 55,
  55]`.
* **The codimension scheduler KNOWS `eps_per_round(r)` and
  `evidence_ratio(r)` per round** but the audit tool does not
  read them. There is no helper like
  `nfe_steps_for_evidence(eps_per_round)` that allocates more
  NFE to rounds with smaller `eps` (where refinement matters
  most).
* **Round 0 always gets the full NFE allocation.** The codimension
  scheduler's `eps_per_round(0) = eps_implicit * (1 - 0) =
  eps_implicit` (max) — round 0 is the *highest-noise* round,
  where extra NFE is least useful. The audit tool wastes NFE here.

### 6.2 `MODEL_TABLE` (lines 95-124)

* **`n_rounds = 5` for `twodim_fm` and `lineageflow`; `n_rounds
  = 4` for `cifar10_rf`** — fixed per model. The saturation point
  of 275 NFE comes from running `(NFE, n_rounds) = (275, 5)` which
  yields 55 NFE/round — well above the 50 NFE target.
* **`framework_scheduler` is `"codimension_sheet"` for `twodim_fm`,
  `"cosine_anneal"` for the others** (lines 100, 108, 116). This
  is inconsistent: the framework default (Wave 34) is
  `codimension_sheet` for *all* adapters, but the audit tool still
  uses cosine_anneal for `cifar10_rf` and `lineageflow`. The
  saturation measurement is therefore mixing scheduler families
  — the cifar10 saturation is at a *cosine* scheduler, not the
  paper-quantity scheduler.

### 6.3 Framework arm construction (lines 251-298, 376-406, 497-551)

* **Single-round framework arms.** `_run_twodim_fm` (line 274)
  and `_run_lineageflow` (line 498) construct the framework arm
  by running `n_rounds` separate adapter calls with
  `nfe_per_round` each — but they do NOT plumb `apply_restart_distribution`
  between rounds. The "framework arm" is therefore `n_rounds`
  independent cold-start integration calls, **not** a multi-round
  re-inference loop. The W2-vs-NFE measurement reflects "do N
  independent calls converge faster than 1 long call" — which is
  a *different* question than "does the framework's restart-
  blend help".
* **`_run_cifar10_rf`** (line 376) is closer to a real framework
  call (`adapter.batched_inference(num_steps=nfe_per_round)`),
  but it still does not call `inject_forward_noise` between
  rounds, so the multi-round arm is "N independent fresh-noise
  passes" — again not a framework-shaped comparison.

### 6.4 Audit-tool summary

**Finding 14 — HIGH:** The audit tool's `_nfe_steps_per_round` is
**uniform** across rounds. For `cycle_length=5` and `nfe=275`,
all 5 rounds get 55 NFE each. The codimension scheduler's
`eps_per_round(r)` declines monotonically from `eps_0=0.05` at
`r=0` to `eps_4 = 0.05 * (1 - 4/4) = 1e-9` (floor) at `r=4`.
**A `eps`-aware NFE allocation would give round 0 fewer steps
(high noise = low marginal value) and round 4 more steps
(small `eps` = refinement matters most).** This is a free win:
the framework already publishes `eps_per_round` on `ScheduleSample`
(`scheduler/_core.py` line 3318), so the audit tool could read it
and allocate NFE as `nfe * (eps_per_round / sum(eps_per_round))`
or similar. Smallest experiment: re-run the saturation sweep with
the allocation helper updated, expecting the saturation point to
drop below 275.

**Finding 15 — HIGH:** The audit tool's framework arms are *not*
actually framework-shaped — they are `n_rounds` independent cold-
start integration calls. The "framework arm" therefore inherits
no benefit from the algorithm layer (no `apply_restart_distribution`,
no paper-quantity-driven noise injection between rounds, no
scheduler-driven `n_cap`). **The 275-NFE saturation point
characterises "cold-restart vs single-pass", not "framework vs
baseline"** — this is a measurement artefact that the audit
tool itself documents (line 4: ``the regression is from the
algorithm, the adapter wiring, or measurement (NFE counting,
baseline-vs-framework comparison setup)``). Re-running the
audit with a *real* framework arm (i.e. using `BatchedTrajectoryRunner`
+ a `merge_operator` + `inject_noise=True`) would surface the
true algorithm-level saturation point.

**Finding 16 — MEDIUM:** `MODEL_TABLE["cifar10_rf"]["framework_scheduler"]`
is `"cosine_anneal"` (line 108) but Wave 34's default is
`"codimension_sheet"` (operating-regime.md §10.3). The CIFAR-10
saturation measurement is therefore stale relative to the Wave 34
default. Re-running the saturation sweep with the default
scheduler for all models would close the inconsistency.

**Finding 17 — MEDIUM:** `n_rounds = 5` (twodim_fm / lineageflow)
and `n_rounds = 4` (cifar10_rf) are **hard-coded** in `MODEL_TABLE`.
The saturation point depends on `n_rounds`: at `n_rounds=2`,
`nfe=50` gives `25` NFE/round, which is half the current
allocation. The audit tool does not sweep `n_rounds` — it would
need a `n_rounds_sweep` cell dimension to characterise the
`(nfe, n_rounds, quality)` surface fully.

---

## 7. `docs/theory/operating-regime.md` (849 LOC)

The operating-regime document is the framework's canonical
statement of when it helps / regresses. Several sections are
load-bearing for the saturation discussion.

### 7.1 §1.3 Empirically observed regime (lines 66-88)

* **Framework regresses at every `σ ∈ [0, 0.5]`** on both synthetic
  2D targets. The headline regression number is `+191%` at `σ=0`
  — i.e. framework's W2 is `2.91x` baseline's W2. This is the
  framing of the saturation problem: the framework's multi-round
  re-inference is **worse** than a single-pass at matched NFE on
  this regime.

### 7.2 §5 F-5 limitation (lines 286-342) — RESOLVED in Wave 31

* The F-5 finding ("`n_cap` driven by cosine, not paper ratio")
  was resolved by Wave 31 Agent A: `n_cap` now responds to the
  paper's sheet-vs-cell ratio. **However, the resolution does
  not address saturation speed** — it addresses only the
  *correctness* of the per-round `n_cap` driver. The framework
  still uses the *same number of rounds* with the *same per-round
  NFE allocation* under the new driver.

### 7.3 §9.5 Open question — deferred to Wave 34

> "Open question (deferred to Wave 34): does the cycle's terminal
> `n_cap ≈ 1` actually deliver framework improvement on
> `twodim_fm`, or does the cosine ramp still dominate the
> `n_cap` envelope (so the framework heuristic behaves like
> constant-`eps`)? The empirical regime statement in §1.2 stands
> either way: the framework's value-add is regime-dependent, and
> the Wave 33 fix realises the paper's intent even if the regression
> narrowing observed empirically requires further verification."

* This is the **only place** the operating-regime doc acknowledges
  that the framework might not need full NFE at terminal rounds.
  It does not propose a concrete NFE-allocation rule.

### 7.4 §10 Wave 34 default scheduler

* Default is now `CodimensionSheetScheduler` (paper-quantity-
  driven). The cosine ramp is available as a legacy opt-in.
* For the heuristic fallback (no `profile_residual_fn`), the
  `n_cap ≈ n_max` throughout the cycle (line 9.5 verbatim: "The
  framework heuristic keeps `n_cap ≈ n_max` throughout the cycle
  (sheet dominance at small `eps`)"). **This means the framework
  cannot reduce late-round NFE even on the no-profile path** —
  the heuristic never drives `n_cap` low enough for the bounded
  merge to collapse usefully.

### 7.5 Operating-regime summary

**Finding 18 — LOW:** Operating-regime.md §9.5 acknowledges that
the terminal-round `n_cap ≈ 1` may not be optimal, but does not
propose a concrete NFE-allocation rule that uses `eps_per_round(r)`
to scale per-round NFE. A small addition to §10.5 (forward path)
listing "possible NFE-allocation rules: `nfe_per_round(r) ∝
eps_per_round(r)` or `nfe_per_round(r) ∝ 1 / eps_per_round(r)`"
would let the next agent pick this up without re-deriving the
idea.

---

## 8. Cross-cutting findings (severity classification)

### 8.1 HIGH (forces framework to use full NFE)

| # | Finding | File | Lines | Fix proposal | Smallest experiment |
|---|---|---|---|---|---|
| 1 | No scheduler exposes a "round converged" or "shorten NFE" interface | `scheduler/_core.py` | 177-282 (Protocol) | Add `should_terminate_round(self, metrics) -> bool` to `SchedulerProtocol`; have `CodimensionSheetScheduler` return True when `n_cap < eps_threshold AND smoothed_w2 plateau detected` | Implement the method on `CodimensionSheetScheduler`, wire into `BatchedTrajectoryRunner.run()`, re-run audit with `n_rounds=20` and verify early exit at round ~5-7 |
| 2 | `BatchedTrajectoryRunner.run()` has no early-termination loop | `batched_runner.py` | 744-887 | Add `for r in range(int(cfg.cycle_length)): if cfg.early_termination and scheduler.should_terminate_round(metrics): break` | Add a single `break` guarded by a new `cfg.early_termination: bool` field; verify the audit tool's saturation point drops from 275 to ~80 |
| 3 | `_nfe_steps_per_round` is uniform across rounds | `run_controlled_audit.py` | 578-599 | Add `_nfe_steps_for_evidence(nfe, eps_per_round_list)` that allocates NFE inversely proportional to `eps_per_round` (low-eps = high-NFE) | Re-run audit with the new helper on `(nfe=50, n_rounds=5)` and check saturation point |
| 4 | Audit tool's framework arms are not framework-shaped (cold-restart, not re-inference) | `run_controlled_audit.py` | 251-298, 376-406, 497-551 | Use `BatchedTrajectoryRunner` + `merge_operator=BoundedMergeOperator` + `inject_noise=True` for the framework arms | One-cell test: `twodim_fm nfe=50 sigma=0` baseline vs framework with real merge operator; verify framework's W2 is *better*, not 2.91x worse |
| 5 | `scheduler.record_round_feedback` is no-op on `CodimensionSheetScheduler` | `scheduler/_core.py` | 3368-3374 | Implement `record_round_feedback` to consume `{"W2", "selection_ratio", "paper_quantities"}` and update an EMA-tracked `evidence_ratio_history` | Wire into the runner's existing feedback call; verify `CodimensionSheetScheduler.smoothed_evidence_ratio` populates after 2+ rounds |

### 8.2 MEDIUM (latent inefficiencies)

| # | Finding | File | Lines | Fix proposal | Smallest experiment |
|---|---|---|---|---|---|
| 6 | `BoundedMergeOperator.merge` returns a constant floor when envelope collapses, breaking the convergence signal | `merge_operator.py` | 669-685 | Add a `MERGE_ENVELOPE_COLLAPSED` audit code so the runner can branch on it | Add a `merged_beta_collapsed: bool` field to `BatchedTrajectoryResult.per_round_metric`; check `is_collapsed[r]` and skip if True |
| 7 | Paper-quantity floor (`e_rho / 4`) forces merge envelope to never collapse to 0 | `merge_operator.py` | 587-596 | Allow `e_rho = None` to opt out of the floor lift; default keeps paper-aligned behaviour | Disable `exterior_gap_e_rho` on the audit tool's framework arm; re-run saturation sweep |
| 8 | `EMAOperator.alpha` halves at low `n_cap` (double-penalty with merge collapse) | `merge_operator.py` | 862-877 | When `n_cap_c < 0.1`, set alpha = 0 (full EMA frozen at `prev`) instead of halving | Single-round test: `EMAOperator(alpha=0.1, schedule_sample.n_cap=0)` returns `prev` (not `prev + 0.05*(dynamic-prev)`) |
| 9 | `BatchedRunnerConfig` has no `nfe_budget`, `min_rounds`, `convergence_window` fields | `batched_runner.py` | 181-301 | Add optional `nfe_budget: int \| None` and `convergence_window: int = 2` | Add fields, run a single audit cell, verify the runner exits early when W2 has not improved |
| 10 | `SequentialScheduler.record_round_feedback` does not trigger slot transitions | `sequential.py` | 314-365 | Add `should_advance_slot(metrics) -> bool` to `SequentialScheduler` | Construct a 2-slot chain with `n_rounds=[20, 0]`, verify the runner advances to slot 1 when W2 plateaus |
| 11 | `EvidenceDrivenScheduler` (strength=1.0) collapses the merge envelope earlier in the cycle | `evidence_driver.py` | 170-195 | Document the counter-productive behaviour; consider default `strength=0.5` for `BatchedTrajectoryRunner` framework arms | Re-run LineageFlow saturation sweep with strength=0.5 vs strength=1.0 |

### 8.3 LOW (polish / documentation)

| # | Finding | File | Lines | Fix proposal | Smallest experiment |
|---|---|---|---|---|---|
| 12 | `shift_max = 0.15` is the same for both adaptive schedulers (compressive ceiling) | `scheduler/_core.py` | 1972, 3617 | Document the ceiling in operating-regime.md §10.4; consider 0.30 as a saturation-aware option | Add a `shift_max=0.30` ablation row to `docs/ABLATION.md` |
| 13 | `MODEL_TABLE` `framework_scheduler` field is inconsistent (codimension_sheet for twodim_fm, cosine_anneal for cifar10_rf / lineageflow) | `run_controlled_audit.py` | 100, 108, 116 | Use `default_paper_ratio_scheduler()` for all rows | Re-run saturation sweep with the new defaults |
| 14 | `n_rounds = 5` / `4` are hard-coded per model; no `n_rounds_sweep` cell dimension | `run_controlled_audit.py` | 95-124 | Add `n_rounds_sweep: tuple[int, ...]` per model | Sweep `(nfe, n_rounds, quality)` at `n_rounds ∈ {2, 3, 5, 10, 20}` for `twodim_fm` |
| 15 | Operating-regime.md §10.5 has no NFE-allocation rule proposal | `operating-regime.md` | 553-577 | Add §10.6: "Possible NFE-allocation rules using `eps_per_round(r)`" | Append 3 paragraphs to operating-regime.md |

---

## 9. Top 5 recommendations

Ranked by impact / cost ratio. Each recommendation has a smallest
experiment that can validate it in <2 hours of CPU work.

### R1. Add `should_terminate_round` to `SchedulerProtocol`, wire into runner
**Severity:** HIGH | **Cost:** Low | **Impact:** Could drop saturation from 275 → 50 NFE
**Files:** `scheduler/_core.py` (Protocol), `batched_runner.py` (run loop)
**Smallest experiment:** implement on `CodimensionSheetScheduler`
(return True when `n_cap < 0.1 AND smoothed_W2_ema changed < 0.5%
in last 2 rounds), wire into `BatchedTrajectoryRunner.run()` with a
new `cfg.early_termination: bool = False` field. Run
`python tools/run_controlled_audit.py --quick --models twodim_fm
--nfe 50 200 500`. Expect saturation point drops from 275 → ~120
NFE on the early-termination arm; the no-early-termination arm is
the control.

### R2. Replace `_nfe_steps_per_round` with `eps_per_round`-weighted allocation
**Severity:** HIGH | **Cost:** Low | **Impact:** Could drop saturation by ~30% on paper-quantity-driven runs
**Files:** `run_controlled_audit.py` (allocation helper)
**Smallest experiment:** add `_nfe_steps_for_evidence(nfe, eps_list)`
that allocates `nfe * eps_i / sum(eps)` per round, run the saturation
sweep on `twodim_fm` at `nfe ∈ {50, 100, 275}`. Expect the
saturation NFE drops because round 0 (high `eps`, high noise) gets
fewer steps and round `n-1` (small `eps`, refinement) gets more.

### R3. Use `BatchedTrajectoryRunner` + `merge_operator=BoundedMergeOperator` for the audit framework arms
**Severity:** HIGH | **Cost:** Medium | **Impact:** The 275 NFE measurement currently characterises cold-restart, not framework
**Files:** `run_controlled_audit.py` (`_run_*` workers)
**Smallest experiment:** rewrite `_run_twodim_fm` to use
`BatchedTrajectoryRunner` with `merge_operator=BoundedMergeOperator(exterior_gap_e_rho=1e-4)`,
`forward_noise=True`, `cycle_length=5`. Run a single cell
(`twodim_fm nfe=50 sigma=0 seed=0`) and verify framework W2 is *better*
than baseline (current measurement says framework W2 is 2.91x worse).
If it is, the 275 NFE saturation point was a measurement artefact.

### R4. Implement `CodimensionSheetScheduler.record_round_feedback`
**Severity:** HIGH | **Cost:** Low | **Impact:** Closes the runner→scheduler feedback loop for the paper-quantity-driven scheduler
**Files:** `scheduler/_core.py` (lines 3368-3374)
**Smallest experiment:** copy `ConvergenceAdaptiveScheduler.record_round_feedback`'s
W2-EMA update into `CodimensionSheetScheduler` (also track
`evidence_ratio` EMA). Add a `smoothed_evidence_ratio` property
exposing the EMA. Add a 5-line test that feeds `{"W2": 0.5}`,
`{"W2": 0.51}`, `{"W2": 0.52}` and verifies the EMA populates.
This unblocks R1 (which needs the EMA for the convergence detector).

### R5. Add `MERGE_ENVELOPE_COLLAPSED` audit code to `BoundedMergeOperator`
**Severity:** MEDIUM | **Cost:** Low | **Impact:** Surfaces a free convergence signal at the runner layer
**Files:** `merge_operator.py` (lines 669-685)
**Smallest experiment:** when the interval collapses, append
`MERGE_ENVELOPE_COLLAPSED:floor=...:cap=...:prev=...` to
`audit_codes`. Add a `merged_beta_collapsed: list[bool]` field to
`BatchedTrajectoryResult.per_round_metric` populated by the runner.
Single-cell test: verify the field populates on a contrived envelope
collapse.

---

## 10. The "why does it saturate at 275 NFE?" answer in one paragraph

The framework saturates at 275 NFE because **the engine is
structurally open-loop on round count, structurally uniform on
per-round NFE allocation, and the audit tool's framework arm is
not actually framework-shaped**. None of these is a bug; all are
deliberate choices in the algorithm-layer / runner contract. The
codimension scheduler publishes `eps_per_round(r)` and
`evidence_ratio(r)` on every `ScheduleSample`, but no consumer
reads them to scale per-round NFE or to skip rounds. The bounded
merge operator collapses to a constant floor at late rounds under
the codimension ramp, but the runner keeps paying full NFE for
collapsed-round merges because it has no termination signal.
The audit tool's `_nfe_steps_per_round` is uniform across rounds
even though `eps_per_round` declines monotonically. And the
"framework arm" in the audit tool is `n_rounds` independent
cold-start integration calls — not a multi-round re-inference
loop with `apply_restart_distribution`, paper-quantity-driven
noise injection, or bounded merge between rounds. Closing the
saturation gap from 275 → 50 NFE therefore requires **four
engine-level changes** (R1-R5 above): a convergence-aware round
termination signal, an `eps`-aware per-round NFE allocator, a
real framework-shaped audit arm, and a wired feedback loop on
the codimension scheduler. None of these changes the algorithm's
correctness; all four are additive to the existing
protocol surfaces.

---

## 11. Files audited (manifest)

| Path | LOC | Sections read | Key findings |
|---|---|---|---|
| `adaptive_reflow/algorithm/scheduler/_core.py` | 4511 | Lines 1-2230, 2231-3530, 3531-4511 | 1, 2, 3, 12 |
| `adaptive_reflow/algorithm/merge_operator.py` | 937 | Lines 1-500, 500-937 | 4, 5, 8 |
| `adaptive_reflow/algorithm/batched_runner.py` | 949 | Lines 1-800, 800-949 | 6, 7, 9 |
| `adaptive_reflow/algorithm/sequential.py` | 521 | Lines 1-521 | 10, 11 |
| `adaptive_reflow/algorithm/evidence_driver.py` | 574 | Lines 1-574 | 12, 13 |
| `tools/run_controlled_audit.py` | 1054 | Lines 1-560, 560-1054 | 14, 15, 16, 17 |
| `docs/theory/operating-regime.md` | 849 | Lines 1-849 | 18 |

Total LOC read: ~9394 (every requested file end-to-end).
