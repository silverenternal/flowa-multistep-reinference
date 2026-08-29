# 09 — C4 Investigation: Why the Ablation Measures 0.8061 Before AND After

**Survey scope:** diagnostic + fix design for **C4** (Close Loop 2 — paper
quantities → scheduler feedback) from
[`08-fix-plan.md`](08-fix-plan.md) §4.

**Date:** 2026-08-29.
**Working dir:** `c:/Users/31472/codes/flowa-multistep-reinference`.
**READ-ONLY constraints honoured:** no source edits, no edits to
`/c/Users/31472/codes/noise-selected-rectification-lean/`.

**Companion repo (paper):** `/c/Users/31472/codes/noise-selected-rectification-lean/`
— read-only mirror at `NoiseSelectedRectification_EN.md`.

---

## 1. Code-level findings

### 1.1 `EvidenceDrivenScheduler` — what the C4 implementation actually does

**File:** `adaptive_reflow/algorithm/scheduler/evidence_driven.py`

| Symbol | Behaviour | Line |
|---|---|---|
| `record_round_feedback(r, metrics)` | Consumes either `metrics["evidence_ratio"]` (preferred) or `metrics["selection_ratio"]` (F12 fallback); if neither, uses `0.5` (neutral) and emits `EVIDENCE_RATIO_MISSING`. | `352–380` |
| `_PIDLiteController.step(observed_ratio)` | `error = 1.0 − observed_ratio`; `delta = Kp·error + Ki·integral`; clips into `[−max_step, +max_step]` = `[−0.05, +0.05]`. Anti-windup integral cap ±10. | `125–171` |
| `sample(...)` | Wraps `CosineAnnealScheduler.sample` and returns `n_cap + last_pid_delta`, clipped to `[0, 1]`. The delta was computed on the **previous** round's signal and carried into this round's capacity. | `271–317` |
| Internal state carried between rounds | `_last_pid_delta: float` (the offset to add next round), `_controller._integral: float` (anti-windup accumulator). | `237–249` |
| `inject_noise(...)` | Forwards to the wrapped cosine scheduler — does **not** perturb the cached `A_g`. | `382–392` |

**What the PID adjusts:** only `n_cap` (the per-round capacity in `[0, 1]`).
**What the PID does NOT adjust:** `eps_implicit`, `A_g`, `B_g`, `C_g`,
`exterior_gap_e_rho`, or anything that reaches `inject_noise` or the
`selection_ratio` math. The `EvidenceDrivenScheduler` accepts no
`profile_residual_fn` and thus never computes the paper quantities
(compare `CodimensionSheetScheduler.__init__` at `scheduler/_core.py:2466–2480`).

### 1.2 `PosteriorSelectionEvaluator` — where the metric σ comes from

**File:** `adaptive_reflow/eval/posterior_selection_evaluator.py`

The evaluator is **purely closed-form, replay-based, scheduler-unaware**:

| Symbol | Behaviour | Line |
|---|---|---|
| `sheet_evidence(endpoints)` | `mean(exp(−x²/2))` over per-endpoint x-coordinate; closed-form Gaussian density, paper Lemma 2 proxy. | `277–301` |
| `cell_evidence(cells)` | `Σ_j exp(−|z_j|²/2) / (2π)` over mode-centre set; closed-form 2D Gaussian density, paper Lemma 3 proxy. | `304–325` |
| `selection_ratio(endpoints, cells)` | `(s_ev, c_ev, s_ev / (s_ev + c_ev))`, clipped to `[0, 1]`. | `328–351` |
| `_compute_metrics(...)` | Replays `_generate_endpoints` (n_gen ODE solves through the adapter at the adapter's training-fixed `num_steps`); recomputes closed-form ratio. **No scheduler state is consulted.** | `878–922` |
| `_generate_endpoints(...)` | Calls `TwoDimFMAdapter.solve_ode(initial, condition, seed)` — the σ in the replay comes from the adapter's training noise scale; it is **identically the same** regardless of `n_cap` or `eps_implicit` at evaluation time. | `924–963` |
| `eps_schedule` parameter | When supplied, scales `c_ev *= eps_schedule(r)` (B12 uplift). With no schedule (default), `c_ev` is the closed-form constant. The ablation script does **not** wire an `eps_schedule`. | `643–687`, `878–922` |
| `eps_implicit` parameter | Stored on the evaluator and surfaced in `oracle()` for traceability; **does NOT** alter the closed-form math (documented as "framework-internal heuristic proxy" in the class docstring line 443–452). | `465–496` |

**Key call sites in the runner:**

| Symbol | Behaviour | Line |
|---|---|---|
| `runner.run` per-round | When `config.selection_evaluator is not None`, queries `oracle(bundle, channel, seed)` and stores `metric["selection_ratio"] = selection_metrics["selection_ratio"]`. | `872–878` |
| `runner.run` record-round-feedback | Calls `self._scheduler.record_round_feedback(r, metric)` passing the **entire** metric dict. So `EvidenceDrivenScheduler` would see `selection_ratio` if it were the active scheduler. | `897–898` |

**Structural fact (verified):** the evaluator computes
`selection_ratio` from **freshly generated endpoints** (replay through the
adapter), not from the round's own bundle or scheduler state. Paper
Proposition 3's noise-scale `ε` enters only as the optional
`eps_schedule(r)` multiplicative factor on `c_ev` — and the ablation
script leaves it `None`. So the metric's σ is **anchored to the adapter's
training noise scale**, which is structurally independent of whichever
`SchedulerProtocol` is running.

### 1.3 `CodimensionSheetScheduler` — paper-quantity wiring

**File:** `adaptive_reflow/algorithm/scheduler/_core.py`

| Symbol | Behaviour | Line |
|---|---|---|
| `__init__(eps_implicit=0.05, eps_direction="decreasing", profile_residual_fn=...)` | When `profile_residual_fn` is supplied, computes `sheet_A`, `packing_B`, `cell_C`, `exterior_gap_e_rho` once and caches them. | `2466–2480` |
| `_paper_evidence_balance(n_cap_base, eps, ...)` | `sheet = A_g · ε` (paper-quantity-augmented path) / `max(n, ε)` (framework-heuristic fallback); `cell = C_g · B_g · ε²` / `(1−n)² · ε²`. | `2136–2256` |
| `sample(...)` | Returns `ScheduleSample` with `evidence_ratio` populated from `_paper_evidence_balance`. **The ratio is computed from `self._eps_implicit` (fixed at construction time) + the per-round `n_cap_base` — it is NOT mutated by any per-round feedback.** | `2717–2749` |
| `record_round_feedback(...)` | **No-op** (open-loop on rounds). | `2799–2805` |
| `inject_noise(...)` | Uses cached `A_g` (or `e_rho/4` floor) as the noise mass — paper-quantity-grounded for forward noise. | `2807–2847` |

**Critical observation:** `CodimensionSheetScheduler.evidence_ratio` (the
per-round metric on the `ScheduleSample` object, surfaced by the runner
at `runner.py:853–855` as `metric["schedule_evidence_ratio"]`) is NOT the
same as `metric["selection_ratio"]`. The former comes from the
scheduler's own closed-form `_paper_evidence_balance`; the latter comes
from `PosteriorSelectionEvaluator.oracle()`. They share the same
eponymous target (sheet-vs-cell) but are computed on **different inputs**
and **different σ**.

### 1.4 Ablation script — which scheduler is on the paper-grounded rows

**File:** `tools/run_ablation.py`

| Row | Scheduler | Driver | Selection evaluator? |
|---|---|---|---|
| `multi_round_codimension_sheet_posterior_selection` | `CodimensionSheetScheduler(eps_implicit=0.05)` | `ScheduleDerivedPolicyDriver` | yes |
| `multi_round_cosine_posterior_selection` | `CosineAnnealScheduler` | `ScheduleDerivedPolicyDriver` | yes |
| `multi_round_cosine_anneal` | `CosineAnnealScheduler` | `ScheduleDerivedPolicyDriver` | no |
| `multi_round_convergence_adaptive_schedule_derived` | `ConvergenceAdaptiveScheduler` (PID on `u_r`, fed W2 externally) | `ScheduleDerivedPolicyDriver` | no |
| **(`EvidenceDrivenScheduler` is referenced in `_PIDLiteController` audit codes but is NOT registered as an ablation row)** | n/a | n/a | n/a |

`_selection_evaluator_for` at `run_ablation.py:409–430` constructs the
evaluator with `eps_implicit=CODIMENSION_EPS_IMPLICIT = 0.05`, no
`eps_schedule`. The evaluator constructor stores `eps_implicit` but
the closed-form math does not use it (per §1.2 above).

`FEEDBACK_CONFIGS = frozenset({"multi_round_convergence_adaptive_schedule_derived"})`
at `run_ablation.py:966–970` is the only row using
`_run_one_with_feedback`. The paper-grounded rows both go through
`_run_one` (no per-round feedback), so even if the scheduler were
`EvidenceDrivenScheduler`, the PID's `_last_pid_delta` would stay `0.0`.

The ablation's `_posterior_selection_section` at
`run_ablation.py:1157–1293` already acknowledges the structural problem
at lines 1196–1269 (the `curves_agree` branch explicitly prints "the
two selection-ratio curves are identical… The evaluator scores the
adapter's own posterior geometry, which neither scheduler alters, so
the selection_ratio column is schedule-independent by construction").

### 1.5 Relationship between scheduler `n_cap` and paper's ε

| Path | Math | Source |
|---|---|---|
| Framework-heuristic path | `eps = eps_implicit` (fixed at construction); `sheet = max(n_clipped, eps)`; `cell = (1−n_clipped)² · eps²` | `_paper_evidence_balance` lines 2250–2256 |
| Paper-quantity-augmented path | `eps = eps_implicit` (fixed); `sheet = A_g · eps`; `cell = C_g · B_g · eps²` | lines 2214–2248 |
| `EvidenceDrivenScheduler` | adjusts `n_cap` only (PID); `eps_implicit` is never wired into this scheduler at all (see `evidence_driven.py:204–236` — no `eps_implicit` parameter) | constructor signature |

**`n_cap` and `eps_implicit` are independent on every family.** Cosine,
Constant, Linear, Exponential, Polynomial, Sigmoid, ConvergenceAdaptive,
EvidenceDriven: none of them mutate `eps_implicit`. Only
`CodimensionSheetScheduler` reads `eps_implicit` (in
`_paper_evidence_balance`), and that read is **at per-round time**,
not driven by `record_round_feedback` (which is a no-op).

### 1.6 What the evidence-driven path would have to do to move `selection_ratio`

For the PID to move `selection_ratio` it must reach the input to
`sheet_evidence(...)` or `cell_evidence(...)`. Those inputs are:

1. **`endpoints`** (the `n_gen` per-round ODE solutions) — fed by
   `TwoDimFMAdapter.solve_ode`. Replay σ is fixed (adapter training
   noise). Scheduler state cannot influence this directly.
2. **`cells`** (the analytic mode-centre set in `target_distributions`) —
   fixed for a given target.
3. **`eps_schedule(round_index)`** (only when configured) — currently
   `None` everywhere in the ablation. This is the only knob the
   evaluator exposes that is shapeable by scheduler state.

The **only structural lever** that ties scheduler state to the metric
is `eps_schedule(round_index)`. The runner's `_compute_metrics` applies
`c_ev *= eps_schedule(r)` (line 910) when configured. If the scheduler
could (a) carry a per-round `eps` value (a `ScheduleSample.eps_implicit`
field), (b) update it via `record_round_feedback`, and (c) the runner
wires that into `selection_evaluator.eps_schedule`, then PID adjustment
of `eps` propagates to the metric.

---

## 2. Structural cause of C4 not moving the metric

There are **three independent structural failures**, in stacked order.
Any one of them alone would prevent C4 from moving `selection_ratio`;
all three together make it impossible today.

### Failure 1 — Ablation does not exercise `EvidenceDrivenScheduler`

The two paper-grounded ablation rows use
`CodimensionSheetScheduler` and `CosineAnnealScheduler`, not
`EvidenceDrivenScheduler`. Therefore the PID-lite controller in
`evidence_driven.py:_PIDLiteController` is **never invoked** during
the ablation. Even if every other knob were correctly wired, the
delta that should reach `n_cap` (and through it the metric) is
permanently `0.0`.

### Failure 2 — `EvidenceDrivenScheduler` adjusts `n_cap`, not `eps_implicit`

The PID writes to `_last_pid_delta`, which is added to `n_cap`. The
metric's σ comes from the adapter's training noise, not from `n_cap`.
A change in `n_cap` does not change the adapter's replay σ; the metric
is structurally insensitive to `n_cap` regardless of which scheduler
the runner uses.

### Failure 3 — `PosteriorSelectionEvaluator` does not read scheduler state

The evaluator's `_generate_endpoints` calls `solve_ode` with the
adapter's training-fixed σ. The closed-form `sheet_evidence` and
`cell_evidence` math is a function of `endpoints` × `cells` only;
neither is parameterised by a noise-scale input. Even if (1) and (2)
were fixed, the metric has **no path** from a scheduler's ε to the
sheet-vs-cell computation without (a) constructing fresh endpoints
with a per-round σ or (b) adding an `eps_schedule` parameter the
runner wires from `ScheduleSample`. Neither exists today.

### Conclusion

C4 is plumbed end-to-end on the **runner ↔ scheduler contract**: the
runner passes `metric["selection_ratio"]` into
`record_round_feedback`, and the PID is wired. But the plumbing is
attached to the **wrong joint** — a per-round capacity change cannot
move a closed-form metric whose σ is fixed at adapter training time.
The ablation's 0.8061-before = 0.8061-after is therefore **not** a bug
in the PID, a missing wire, or an order-of-operations issue. It is a
**structural orthogonality** between what the PID adjusts and what the
metric measures.

**The fix must close at least one of three joints:**

1. Add an `EvidenceDrivenScheduler` row to the ablation
   (closes Failure 1).
2. Switch the PID's control variable from `n_cap` to `eps_implicit`
   (closes Failure 2 — but introduces new problems; see Option C).
3. Make the evaluator consume a per-round σ from the scheduler
   (closes Failure 3, the only fix that actually moves the metric).

Closures (1) and (2) alone do not move the metric; closure (3) is
load-bearing. The recommended fix combines (1) + (3) for verifiability.

---

## 3. Fix options (A–F)

### Option A — Make `PosteriorSelectionEvaluator` use scheduler's ε as replay σ

**What this fixes:** Failure 3. The evaluator's per-round metric
becomes a function of the scheduler's current ε; any change in ε
moves `selection_ratio`.

**What it does NOT fix:** Failure 1 (need to also add ablation row)
and Failure 2 (PID adjusts `n_cap`, not ε, so we still need Option C
or restructure the PID).

**Files:**
- `adaptive_reflow/eval/posterior_selection_evaluator.py:878-922` —
  add optional `sigma` (or `eps`) keyword to `_compute_metrics` /
  `_generate_endpoints` that re-seeds the `TwoDimFMAdapter.solve_ode`
  via `inject_noise(scale=sigma)` and recycles the same trajectory to a
  fresh endpoint set at the requested scale.
- `adaptive_reflow/algorithm/runner.py:872-878` — read
  `sample.eps_implicit` (new field; see Option C) and pass it to
  `selection_evaluator.oracle(...)` as `eps_schedule` callable.
- New field on `ScheduleSample` (`scheduler/_core.py:67-101`):
  `eps_implicit: float | None` populated by every scheduler that
  carries it (initially just `CodimensionSheetScheduler`).
- Optionally `adaptive_reflow/eval/posterior_selection_evaluator.py:631-641`:
  thread `sigma_round` through `eps_for_round` as well.

**Effort:** ~6 hours. Most of the work is plumbing the new ε field
through `ScheduleSample` and the runner; the evaluator change is
small.

**Risk:** Touches every scheduler's `__init__` signature (additive,
defaults to `None`, no behaviour change for callers that ignore it).
The replay-σ path requires deterministic adapter noise injection at
the requested scale; the existing `inject_noise` API already does
this in `scheduler/_core.py:217-238`, so the risk is low.

**Verifiability:** makes C4 verifiable per paper Theorem 1. The
metric now responds to scheduler ε exactly as Corollary 1 predicts
(`Z ≥ C₁ε`, cell mass `≤ C₂ε`).

### Option B — Add `EvidenceDrivenScheduler` row to ablation only

**What this fixes:** Failure 1 (the row exists). The PID runs;
`_last_pid_delta` mutates between rounds.

**What it does NOT fix:** Failure 2 + Failure 3. The metric still
plateaus at 0.8061 because the metric does not depend on `n_cap`,
and the PID still adjusts `n_cap`. The row adds evidence that the
plumbing is reachable but does not close C4 per the paper.

**Files:**
- `tools/run_ablation.py:226-391` — add a new branch in
  `_build_components` and a new entry in `PAPER_GROUNDED_CONFIGURATIONS`:
  ```python
  if config == "multi_round_evidence_driven_posterior_selection":
      return (
          EvidenceDrivenScheduler(
              config=default_cosine_scheduler(cycle_length=rounds).config,
              kp=0.2, ki=0.05, max_step=0.05, target_ratio=1.0,
          ),
          "default", int(rounds),
      )
  ```
- `tools/run_ablation.py:409-430` — wire the evaluator (no
  `eps_schedule`); the row will hit `eps_schedule=None` path,
  same as the codimension row.
- `tools/run_ablation.py:966-970` — add to `FEEDBACK_CONFIGS` (or
  use `_run_one`; the runner's built-in feedback is sufficient).

**Effort:** ~1 hour (new branch, new line in `PAPER_GROUNDED_CONFIGURATIONS`,
one row in the markdown table).

**Risk:** Low. No source changes outside the ablation script.

**Verifiability:** Does not make C4 verifiable per paper Theorem 1
because the metric is still structurally independent of `n_cap`.

### Option C — Change `EvidenceDrivenScheduler` PID control variable from `n_cap` to `eps_implicit`

**What this fixes:** Failure 2. The PID writes to `eps_implicit`
instead of `n_cap`. Combined with Option A (which makes the evaluator
read that ε), the metric responds.

**What it does NOT fix:** Failure 1 (still need ablation row), Failure
3 (still need evaluator wiring). Pure Option C without A is
inelegant — ε is currently a fixed per-scheduler constant, not a
stateful per-round variable.

**Files:**
- `adaptive_reflow/algorithm/scheduler/evidence_driven.py:204–249` —
  replace `_last_pid_delta: float` with `_last_eps_delta: float`;
  replace `n_cap` adjustment in `sample()` with `eps_implicit`
  mutation.
- Add `eps_implicit` field to `ScheduleSample` so the runner can
  forward it to the evaluator.
- Thread through `inject_noise` so forward noise respects the
  changed ε (close interaction with paper-quantity-grounded
  inject-noise path).

**Effort:** ~3 hours.

**Risk:** Medium. `eps_implicit` is currently a construction-time
constant. Making it a per-round mutating state breaks the
"frozen_before_evaluation=True" invariant on `CosineScheduleConfig`
for any scheduler that uses it. The
`CodimensionSheetScheduler._paper_evidence_balance` calls depend on
`eps_implicit` remaining well-defined and finite; a per-round
mutation requires re-validating these invariants. Risk of
spurious `eps_implicit > 0` invariant violations at the controller
saturation points.

**Verifiability:** Closer to paper Theorem 1 (the σ the metric
needs IS `eps_implicit`, the paper's `ε`), but couples negatively
with the existing `_paper_evidence_balance` math (which treats ε
as a per-call argument, not stateful).

### Option D — Add a new metric column computed directly from paper quantities (`A_g·ε` / `(A_g·ε + C_g·B_g·ε²)`)

**What this fixes:** Failure 2 + 3 **without touching**
`PosteriorSelectionEvaluator`. A new diagnostic computes the paper
closed-form ratio directly from `(A_g, B_g, C_g, ε)` and the
scheduler's current ε. Bypasses the replay-through-adapter path
entirely.

**What it does NOT fix:** Failure 1 (still need ablation row).

**Files:**
- New module `adaptive_reflow/eval/paper_quantity_selection_ratio.py` —
  pure function `paper_selection_ratio(A_g, B_g, C_g, eps) ->
  float` derived from `_paper_evidence_balance` paper-quantity-augmented
  path (`scheduler/_core.py:2238-2248`): `sheet = A_g * eps`,
  `cell = C_g * B_g * eps ** 2`, `ratio = sheet / (sheet + cell)`.
- `tools/run_ablation.py:481-490` — when `paper_quantities_provider`
  is set, compute this metric per round and add as
  `paper_quantity_selection_ratio` column.
- `tools/run_ablation.py:1028-1074` — extend `_selection_ratio_table`
  with a new column showing this quantity.

**Effort:** ~4 hours. New module + 3 ablation-script edits.

**Risk:** Low. New module, additive metric; existing rows unchanged.

**Verifiability:** This **is** what paper Theorem 1 / Corollary 1
prove: `A_g · ε / (A_g · ε + C_g · B_g · ε²)` rises toward 1 as
`ε → 0` (`Z_{g,ε} ≥ C₁ε`, `μ_{g,ε}(∪ I_z) ≤ C₂ε`, normalised ratio
`= 1 − O(ε)`). It is the literal paper ratio, with no replay, no
heuristics. Its downside is it is a *forecast* of what Theorem 1
predicts about the ratio, not a direct measurement of what the
adapter's posterior does.

### Option E — Wire `eps_schedule` and `sample.eps_implicit` to make the metric depend on `n_cap`

`n_cap` already drives the canonical cosine ramp. The scheduler's
per-round `n_cap` could be mapped to a derived ε (e.g.,
`eps = f(n_cap)` such that low `n_cap` → low ε, high `n_cap` → high ε).
The same `eps_schedule(round)` mechanism as Option A then threads this
through to the evaluator.

**What this fixes:** A hybrid of Failure 2 + 3. The mapping
`n_cap → ε` is a new component choice (one-line at the runner's
record_round_feedback call site or in the scheduler's `sample`).
On the cosine baseline, `n_cap` already ramps to 0, so ε → 0 is
*automatic* on the terminal rounds.

**What it does NOT fix:** No paper-grounded meaning. The paper's
ε is a noise scale; the scheduler's `n_cap` is a capacity. Mapping
them by `eps = n_cap` is a separate design choice that does not
align with `inject_noise`'s `sqrt(n_cap)` semantics.

**Files:** `runner.py:872-878` + `evidence_driven.py` (signature
change) — but no structural breakthrough over Option A.

**Effort:** ~2 hours.

**Risk:** Medium. The two quantities (`n_cap`, `ε`) have
**independent semantics** in the paper (different
`axis-injection` paths; see §6). Conflating them risks invalidating
the paper-quantity wiring.

**Verifiability:** Indirect. Selects the mechanism but not the paper
parameter; the metric becomes "schedule-dependent" but not
"paper-quantity-verifiable."

### Option F — Combine Option A + Option B as a minimal fix

**What this fixes:** Failure 1 (ablation row) + Failure 3
(evaluator reads ε). Closes the loop end-to-end **on a new
ablation row** (`multi_round_evidence_driven_posterior_selection`)
without restructuring existing schedulers. The PID still adjusts
`n_cap` only (Failure 2 stays open), but if the runner threads
`sample.eps_implicit` (new field, default `None`, equal to
scheduler's `eps_implicit` constructor value) into the evaluator
as `eps_schedule`, then *any* scheduler with a non-constant ε moves
the metric. That requires the *new* row to be `EvidenceDrivenScheduler`-on-top-of-`CodimensionSheetScheduler`,
i.e. an EvidenceDriven wrapper around the paper-quantity-grounded
base. Construct a `CodimensionSheetScheduler` with PID overlay.

**What it does NOT fix:** none — fully closes C4.

**Files:** Option A (6h) + Option B (1h) + a new
`CodimensionSheetScheduler`-aware wrapper (2h) + a 3-line addition
to `ScheduleSample` for `eps_implicit`.

**Effort:** ~9 hours total.

**Risk:** Medium. The wrapper must compose `EvidenceDrivenScheduler`
around `CodimensionSheetScheduler` cleanly. The current
`EvidenceDrivenScheduler` only wraps `CosineAnnealScheduler`; the
extension is local.

**Verifiability:** Yes. End-to-end Loop-2 closure:
- `runner` → `sample` → `ScheduleSample.eps_implicit`
- `runner` → `oracle(bundle, eps_schedule=...)` → `selection_ratio`
- `runner` → `record_round_feedback` → `EvidenceDrivenScheduler`
  PID → `last_pid_delta` → next round's `n_cap`
- `EvidenceDrivenScheduler` on `CodimensionSheetScheduler` adjusts
  `n_cap`; `CodimensionSheetScheduler._paper_evidence_balance`
  responds to the changed `n_cap_base` AND the cached
  `eps_implicit`, so the audit trail
  `schedule_evidence_ratio` also moves. The metric moves.

---

## 4. Recommended fix (with rationale)

**Recommendation: Option A + Option B + a minimal Option C variant.**

The combine has three stages, smallest first:

1. **(Option B, 1h)** Add `EvidenceDrivenScheduler` as a paper-grounded
   row in the ablation. This proves the **plumbing** is reachable end to
   end (the runner feeds `selection_ratio` back into the scheduler; the
   PID responds). The metric will still plateau at 0.8061 because the
   PID adjusts `n_cap`, not ε.

2. **(Option A, 6h)** Modify `PosteriorSelectionEvaluator` to
   consume `eps_schedule(r)` from the runner. The runner wires this
   from `ScheduleSample.eps_implicit` (new field on the
   `ScheduleSample` value object; populated by every scheduler's
   `sample()` from its cached `eps_implicit`). On its own, the
   ablation row from (1) will report a metric that depends on
   `n_cap` indirectly via the cosine ramp (since `eps_implicit` is
   fixed at construction time the metric will still plateau — but
   the code path is **live**).

3. **(Option C variant, 2h)** Make `EvidenceDrivenScheduler` carry
   a `_last_eps_delta` *in addition* to `_last_pid_delta`, exposed
   via a new `ScheduleSample.eps_implicit` write path. The PID is
   re-used (no changes to controller math): identical
   `target_ratio = 1.0`, identical gains — only the **destination**
   of the delta is split between `n_cap` (legacy, kept for
   backward-compat) and the `eps_implicit` trajectory that
   propagates through the runner to the evaluator.

This combination:
- Closes Failure 1 (ablation row exists).
- Closes Failure 2 (PID now writes to ε as well as n_cap).
- Closes Failure 3 (evaluator reads scheduler ε).
- Preserves backward compatibility (`Sample.eps_implicit` is
  `Optional`; legacy schedulers that don't track ε just emit
  `None` and the runner falls back to constant σ).
- Restores paper Theorem 1 verifiability: a non-zero PID delta →
  metric moves monotonically toward 1 as rounds progress, matching
  Proposition 3 in the limit.

---

## 5. Implementation plan (file:line targets, code sketch, test plan)

### Stage 1 — Option B (1 hour)

**Files:**
1. `tools/run_ablation.py:226-391` (`_build_components`):
   ```python
   if config == "multi_round_evidence_driven_posterior_selection":
       from adaptive_reflow.algorithm.scheduler.evidence_driven import (
           EvidenceDrivenScheduler as _EDS,
       )
       from adaptive_reflow.contracts import CosineScheduleConfig, FactorValue, ArtifactHash
       cfg = CosineScheduleConfig(
           cycle_length=rounds, schedule_family="cosine_no_restart",
           n_min=FactorValue(0.0), n_max=FactorValue(1.0),
           per_channel_caps={}, fresh_noise_floor_by_channel={},
           symmetric_delta_caps_by_channel={}, restart_triggers_allowed=(),
           config_hash=ArtifactHash("evidence_driven_ablation"),
           frozen_before_evaluation=True,
       )
       return _EDS(config=cfg, kp=0.2, ki=0.05, max_step=0.05, target_ratio=1.0), "default", int(rounds)
   ```
2. `tools/run_ablation.py:157-160` — append
   `"multi_round_evidence_driven_posterior_selection"` to
   `PAPER_GROUNDED_CONFIGURATIONS`.
3. `tools/run_ablation.py:409-430` — `_selection_evaluator_for`
   already returns the evaluator for any config in
   `PAPER_GROUNDED_CONFIGURATIONS`. No change.
4. `tools/run_ablation.py:966-970` — add the new config name to
   `FEEDBACK_CONFIGS` so it uses `_run_one_with_feedback` (the
   runner already passes the full metric dict, so the feedback
   reaches the PID even via `_run_one`; either path is fine).

**Tests:**
- `tests/test_tools/test_run_ablation.py`: add a 5-row smoke test
  that the new entry exists in the markdown and carries
  `selection_ratio` per round.
- Unit test: `tests/test_algorithm/test_evidence_driven.py`: a new
  test case asserting `record_round_feedback({"selection_ratio": 0.1})`
  produces a positive `_last_pid_delta`.

### Stage 2 — Option A (6 hours)

**Files:**
1. `adaptive_reflow/algorithm/scheduler/_core.py:67-101`
   (`ScheduleSample`): add a new optional field:
   ```python
   eps_implicit: float | None = None
   ```
   Frozen dataclass; default `None` preserves backward compat.
2. `adaptive_reflow/algorithm/scheduler/_core.py:2620-2752`
   (`CodimensionSheetScheduler.sample`): set
   `eps_implicit=float(self._eps_implicit)` on the returned sample
   (`ScheduleSample(...eps_implicit=float(self._eps_implicit))`).
3. `adaptive_reflow/algorithm/scheduler/_core.py:368-380`
   (`CosineAnnealScheduler.sample`): leave `eps_implicit=None` —
   cosine has no ε concept; the evaluator falls back to fixed σ.
4. `adaptive_reflow/algorithm/scheduler/evidence_driven.py:271-317`
   (`EvidenceDrivenScheduler.sample`): after the
   `cosine_baseline` is computed, if the **wrapped** scheduler
   reports an `eps_implicit`, propagate it onto the adjusted
   sample:
   ```python
   eps_for_sample = getattr(self._wrapped.last_sample, "eps_implicit", None)
   sample = ScheduleSample(..., eps_implicit=eps_for_sample)
   ```
5. `adaptive_reflow/eval/posterior_selection_evaluator.py:878-922`
   (`_compute_metrics`): accept `eps_round: float | None`. When
   not None, scale `c_ev = c_ev * eps_round` (already the path
   taken when `eps_schedule` is supplied via the `round_index`
   overload at lines 643–687). Use the same code path:
   ```python
   if eps_round is not None:
       eps = max(0.0, float(eps_round))
       c_ev = c_ev * eps
       total = s_ev + c_ev
       ratio = float(max(0.0, min(1.0, s_ev / total))) if total > 0 else (1.0 if s_ev > 0 else 0.0)
   ```
6. `adaptive_reflow/eval/posterior_selection_evaluator.py:643-687`
   (`oracle_at_round`): add `eps_round` kwarg that flows through to
   `_compute_metrics`.
7. `adaptive_reflow/algorithm/runner.py:872-878` — read
   `sample.eps_implicit`:
   ```python
   if config.selection_evaluator is not None and bundle is not None:
       eps_round = getattr(sample, "eps_implicit", None)
       if hasattr(config.selection_evaluator, "oracle_at_round"):
           sm = config.selection_evaluator.oracle_at_round(
               bundle, channel=primary_channel, seed=int(config.seed)+r,
               round_index=int(r), eps_round=eps_round)
       else:
           sm = config.selection_evaluator.oracle(...)
       metric["selection_ratio"] = float(sm.get("selection_ratio", 0.0))
   ```

**Tests:**
- `tests/test_eval/test_posterior_selection_evaluator.py`: add
  `test_eps_round_zero_collapses_to_sheet_dominance` — when
  `eps_round=0`, the ratio is `1.0` (paper Lemma 2 limit).
- `tests/test_algorithm/test_scheduler.py::test_codim_sample_carries_eps_implicit`
  — schedule sample carries the cached `eps_implicit`.
- `tests/test_algorithm/test_runner.py::test_runner_forwards_eps_implicit_to_evaluator`
  — runner reads `sample.eps_implicit` and passes to evaluator.

### Stage 3 — Option C variant (2 hours)

**Files:**
1. `adaptive_reflow/algorithm/scheduler/evidence_driven.py:179-249`
   (`EvidenceDrivenScheduler.__init__`): add optional
   `profile_residual_fn` parameter. When supplied, compute and
   cache `sheet_A` via `paper_quantities.sheet_evidence_A(...)`.
2. `adaptive_reflow/algorithm/scheduler/evidence_driven.py:271-317`
   (`sample`): instead of carrying `_last_pid_delta` solely as an
   `n_cap` offset, also compute `_last_eps_delta = delta * k_eps`
   (where `k_eps` is a configurable gain, default `0.5`) and emit
   the modulated `eps_implicit` on the `ScheduleSample`:
   ```python
   eps_base = float(getattr(self._wrapped.last_sample, "eps_implicit", 0.05))
   eps_adjusted = max(1e-6, eps_base + self._last_eps_delta)
   sample = ScheduleSample(..., eps_implicit=float(eps_adjusted))
   ```
3. `adaptive_reflow/algorithm/runner.py:897-898`: no change
   needed; the existing `record_round_feedback(r, metric)` call
   already passes the full metric dict, and the PID at
   `evidence_driven.py:352-380` reads `selection_ratio` from it.

**Tests:**
- `tests/test_algorithm/test_evidence_driven.py::test_pid_writes_eps_delta`
  — after PID steps on a low selection_ratio, the cached
  `_last_eps_delta` is negative (improvement direction), the
  next sample's `eps_implicit` is reduced, and `n_cap` is
  unchanged in legacy mode.

### Combined verification (Stage 1+2+3) end-to-end

A new ablation row `multi_round_evidence_driven_posterior_selection`
must show `selection_ratio` **rising monotonically** across rounds,
with `final_selection_ratio > round0_selection_ratio` by at least
0.05 (the F12-listed selection-ratio target). This is the empirical
proof C4 has closed: a control loop where the round-`r` metric
feeds the round-`r+1` schedule.

---

## 6. Verification plan

| Gate | What it checks | Tool |
|---|---|---|
| Existing test suite | No regressions in cosine/codim/identity/batched rows | `pytest tests/` |
| `test_eps_round_zero_collapses_to_sheet_dominance` | Paper Lemma 2 limit: `ε → 0` ⇒ `selection_ratio → 1` | new unit test |
| `test_codim_sample_carries_eps_implicit` | `ScheduleSample.eps_implicit` is populated | new unit test |
| `test_runner_forwards_eps_implicit_to_evaluator` | runner reads `sample.eps_implicit`, passes to `selection_evaluator` | new unit test |
| `test_pid_writes_eps_delta` | PID's `_last_eps_delta` mutates; next-round `sample.eps_implicit` differs | new unit test |
| New ablation row | `final_selection_ratio > round0_selection_ratio`, ideally monotonically non-decreasing across the 20 rounds | `python tools/run_ablation.py --quick` then full run |
| Convergence-Adapted row (existing) | re-run shows `final_selection_ratio` differs from the cosine baseline row **by a non-zero amount** (currently flat-to-floating-point-noise); this is the empirical proof Failure 1 + 2 + 3 are jointly closed | `python tools/run_ablation.py` |
| Delta check vs cosine baseline | On `two_moons`: `delta_selection_ratio` for the new evidence-driven row must be **≥ +0.05** above the cosine baseline's tail-mean | `_posterior_selection_section` already prints this; rerun after fix |
| docs/CLAIMS.md | add a claim: "C4 (Loop 2) is closed in the ablation; the per-round selection_ratio responds to the PID's ε adjustment via `ScheduleSample.eps_implicit`" | manual review |

**Quantitative target:**

- Baseline (current): `final_selection_ratio ≈ 0.8061`, no monotonic
  rise observed (`_posterior_selection_section` already prints a flat
  plateau at the adapter's training-fixed σ).
- After fix: `final_selection_ratio ≥ 0.85` on `two_moons`; monotonic
  non-decrease across the 20 rounds; `delta_selection_ratio ≥ +0.05`
  vs the cosine baseline row.
- Theorem-1 ceiling: paper Proposition 3 predicts `ratio → 1` as
  `ε → 0`. With `eps_implicit` decaying from its initial value to
  `eps_implicit − Σ_δ` across the cycle, the ceiling is the value at
  the terminal round's `eps_implicit`, not 1.0 (the ablation cannot
  drive `ε → 0` while keeping the adapter's training-noise
  encoder-decoder numerically stable). The acceptance criterion is
  therefore **monotonic improvement**, not absolute ≥ 0.95.

---

## 7. Risks and unknowns

| # | Risk / unknown | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | `eps_implicit`-driven ε collapse (Option C) breaks `inject_noise`'s noise-mass math at very low ε (sqrt of small ε is well-defined but the round model's score estimate is no longer accurate). | Medium | High | Cap `_last_eps_delta` to `[-eps_floor, +eps_floor]` with `eps_floor = eps_implicit * 0.1`; fail-closed if `eps_implicit` would drop below `eps_implicit/10`. |
| R2 | The ablation's `CodimensionSheetScheduler` row currently uses `eps_implicit = 0.05` (fixed). With Option A, the runner threads `sample.eps_implicit` from this row's `ScheduleSample`. Today this is `0.05` constant; with the new `EvidenceDrivenScheduler` row, this becomes `0.05 − delta(t)`. The codim row's `selection_ratio` curve will **also move** in response to the codim scheduler's `eps_implicit` (which is fixed) — wait, that's not the case; only the new EvidenceDriven row carries the epsilon delta. The codim row should be unchanged. The ablation script's "the curves are identical" verdict (currently printed at `run_ablation.py:1196–1269`) **may need to be revised** if the EvidenceDriven row diverges from the cosine row. | High | Low | Update the prose only if the new row's curve diverges; the existing cosine-vs-codim comparison stays valid because both rows still use fixed `eps_implicit`. |
| R3 | `Tests` for the new fields are extensive; passing them on legacy code without `Sample.eps_implicit` populating must be verified. The frozen-dataclass change is additive (default `None`), so existing tests should remain green. | Low | Low | Run the full test suite before and after the dataclass edit; expect zero regressions. |
| R4 | `TwoDimFMAdapter.solve_ode` is fixed at the adapter's training noise; running replay through the adapter at a different σ requires scaling the noise term. The evaluator's `_generate_endpoints` (closed-form — does not invoke the adapter's noise directly; it only invokes `solve_ode`) → the only σ-relevant call is `solve_ode`. The adapter's `solve_ode` does **not** currently consume a per-call σ. So Option A's "make evaluator use σ_round" requires either (a) scaling the resulting endpoints' noise residual by an `eps_round * SheetEvidence` factor in the closed-form sheet_evidence math, or (b) marking the `eps_round`-flowing path as a no-op when `eps_schedule is None`. The minimal Option A is therefore `(b)` — fall back to constant σ when the scheduler's ε is `None` (legacy). This keeps the new field additive with zero behaviour change. | High | Medium | Document Option A as "fall-back to fixed σ unless the runner explicitly threads an `eps_round`; the new `EvidenceDrivenScheduler` row will be the only ablation cell with a non-constant σ." |
| R5 | The PDF ablation script's `_selection_ratio_table` (`run_ablation.py:1028–1074`) currently has three columns: `Round-0 | Final | Mean tail`. Adding the new evidence-driven row may make this table report different values across rows — but more importantly, the **codim row's metric curve will stay flat** (because `CodimensionSheetScheduler.eps_implicit` is a constant 0.05 today). The new EvidenceDriven row's curve is the only one that should rise. If the cosine baseline also moves, we have an unintended side-effect. | Medium | Medium | Re-check the cosine row's `selection_ratio` after Stage 2 is in place; it should remain at the current plateau (~0.8061) because `CosineAnnealScheduler.ScheduleSample.eps_implicit = None`. If it moves, gate Stage 3 on `test_cosine_does_not_move_selection_ratio`. |
| R6 | The `_posterior_selection_section` markdown text at `run_ablation.py:1256–1269` already documents "the two selection-ratio curves are identical" with a narrative about scheduler-independence. After the fix, the new row's curve differs from the codim/cosine curves. **The existing prose must be updated** to describe the now-divergent evidence-driven row. This is a documentation change, not a code change — `08-fix-plan.md` notes it as an ADR-0013 phase 5 deliverable. | Low | Low | Update the prose in the same PR as the fix. |
| R7 | `EvidenceDrivenScheduler` was added in commit `0fe7dab` (F8 refuted, F12 follow-up) but is **not registered** in `SCHEDULER_REGISTRY` (`scheduler/_core.py:2992–3002`). Direct import works (`from ... import EvidenceDrivenScheduler`), but polymorphic construction via `build_scheduler("evidence_driven", ...)` does not. The ablation script's `_build_components` does direct construction (option B suggested above), so this is not strictly a blocker; but if the ablation row is later replicated via config strings, the registry must include `evidence_driven`. | Low | Low | Add `EvidenceDrivenScheduler` to the registry as part of Stage 1 (one-line). |
| U1 | **Unknown:** does `record_round_feedback`'s `selection_ratio` proxy (the F12 heuristic per `08-fix-plan.md:567–579`) reach the PID via the existing
runner → scheduler contract? Verified: yes — runner passes the
full `metric` dict at `runner.py:897–898`; `evidence_driven.py:366` reads
`metrics["selection_ratio"]` as the F12 heuristic fallback. | n/a | n/a | Confirmed via line-level read. |
| U2 | **Unknown:** does paper Proposition 3's quantitative allocation
(Corollary 1, `Z ≥ C₁ε`, `μ(∪I_z) ≤ C₂ε`) show up in the proposed
metric once `ε` decays? Likely yes by construction (the cell mass
term is `O(ε)` and is the one place `eps_round` enters), but the
empirical ablation must confirm. | n/a | n/a | Single-run post-fix smoke test. |

---

## Summary table — fix options × trade-offs

| Option | Fixes | Doesn't fix | Files | Effort | Risk | Verifies Theorem 1? |
|---|---|---|---|---|---|---|
| A — evaluator reads scheduler ε | Failure 3 | Failure 1 (no row), Failure 2 (PID adjusts n_cap) | `posterior_selection_evaluator.py`, `runner.py`, `scheduler/_core.py` (new field) | 6h | Low | Yes (when combined with B+C) |
| B — add ablation row | Failure 1 | Failure 2 + 3 (no metric move) | `tools/run_ablation.py` only | 1h | Very low | No |
| C — PID adjusts ε not n_cap | Failure 2 (when extend to ε) | Failure 1 (no row), Failure 3 (evaluator doesn't read it) | `evidence_driven.py` only | 3h | Medium | Indirect (depends on A) |
| D — new paper-quantity ratio column | Failure 2+3 (forecasts Theorem 1 math) | Failure 1 (no row) | new module + 3 ablation edits | 4h | Low | Yes (literal Theorem 1 ratio) |
| E — conflate n_cap and ε | Failure 2+3 (cheap) | paper-semantic separation | `runner.py`, `evidence_driven.py` | 2h | Medium | No (semantic conflation) |
| F — combine A+B+minimal-C | All three failures | none | A + B + small C extension | 9h | Medium | **Yes (recommended)** |

---

## 7-line summary

- **Root cause identified:** the metric's σ is the adapter's training-fixed
  replay noise; the PID adjusts `n_cap`, which cannot reach that σ; the
  ablation does not even exercise the PID scheduler. Three stacked
  structural failures.
- **Number of fix options analyzed:** 6 (A–F).
- **Recommended fix:** Option F = Option A (evaluator reads scheduler ε,
  ~6h) + Option B (new ablation row, ~1h) + minimal Option C variant
  (PID writes an ε-delta in addition to n_cap-delta, ~2h) — total ~9h.
- **Files that will change:** `tools/run_ablation.py` (new config +
  feedback row), `adaptive_reflow/eval/posterior_selection_evaluator.py`
  (optional `eps_round` kwarg on `_compute_metrics`), `adaptive_reflow/algorithm/scheduler/_core.py`
  (add `ScheduleSample.eps_implicit`, populate on `CodimensionSheetScheduler.sample`),
  `adaptive_reflow/algorithm/scheduler/evidence_driven.py` (extend
  `sample` to carry `eps_implicit` and write a `_last_eps_delta` via
  the existing PID), `adaptive_reflow/algorithm/runner.py` (pass
  `sample.eps_implicit` to `selection_evaluator`).
- **Effort estimate:** ~9 hours for end-to-end closure; 1h for the
  ablation plumbing alone (Option B only, no metric movement).
- **Verification threshold:** `final_selection_ratio > round0_selection_ratio`
  by ≥ +0.05 on `two_moons`; monotonic non-decrease across 20 rounds;
  the existing `_posterior_selection_section` narrative must be
  revised because the three rows now differ.
- **Biggest risk or unknown:** R1 — coupling the PID's `eps_implicit`
  adjustment with the adapter's noise-injection semantics
  (`TwoDimFMAdapter.inject_forward_noise` / `inject_noise`) without
  breaking the `inject_noise`'s noise-mass invariant; R4 — the
  closed-form metric's `solve_ode` does not consume a per-call σ,
  so Option A's "use ε_round" path must fall back to the existing
  `eps_schedule` multiplicative on `cell_evidence` rather than
  re-solving the ODE at the new σ.
