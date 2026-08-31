# Algorithms Catalog

> **One paragraph per operator.** Pick the scheduler / driver / merge
> operator / blender that matches your task; copy-paste the sample;
> check the paper grounding.

This page catalogs **every** concrete operator in the framework's
algorithm layer (`adaptive_reflow/algorithm/`). Four sections:

1. **[Schedulers](#schedulers)** — 16 classes that decide the per-round
   `n_cap` (or per-round policy) budget.
2. **[Drivers](#drivers)** — 5 classes that translate the schedule's
   `n_cap` into a `beta_by_channel` restart policy.
3. **[Merge operators](#merge-operators)** — 8 classes that combine
   the previous and dynamic restart fractions.
4. **[Blenders](#blenders)** — 6 classes that blend prior endpoint
   with fresh noise on the restart boundary.

If you only ever plug one of these into a custom adapter, the
**default stack** is:

```python
from adaptive_reflow.algorithm.scheduler import CosineAnnealScheduler
from adaptive_reflow.algorithm.policy_driver import ScheduleDerivedPolicyDriver
from adaptive_reflow.algorithm.merge_operator import BoundedMergeOperator
from adaptive_reflow.algorithm.blender import LinearBlender
```

The defaults are byte-equivalent across the four feedback loops and
what every other operator in the catalog reduces to in the trivial
case. For the SOTA claim target, the canonical paper-grounded stack is
the one used in
[`tools/run_sota_2d_experiment.py`](../tools/run_sota_2d_experiment.py):

```python
scheduler = CodimensionSheetScheduler(cycle_length=20)        # ADR-0013
driver    = ScheduleDerivedPolicyDriver()                     # beta = n_cap
merge     = BoundedMergeOperator(cap=0.95, floor=0.05)        # DTB-R3
blender   = DistanceDecayBlender(temperature=1.0)             # content-aware
```

---

## Schedulers

A scheduler is anything that satisfies `SchedulerProtocol` — given a
round index (and sometimes per-round feedback), it returns the per-round
`n_cap` (a float in `[0, 1]`) and the per-round `memory_fraction`
(`= 1 - n_cap`). All 16 implementations live under
[`adaptive_reflow/algorithm/scheduler/`](../adaptive_reflow/algorithm/scheduler/).

### 1. `CosineAnnealScheduler`

**When to use it.** The default; the canonical cosine-annealing
baseline. Use it as the reference run for any ablation. The
ADR-0010 governance decision.

**Paper grounding.** No paper grounding — this is the framework's
default and the comparison baseline for every other scheduler.

**Sample.**

```python
from adaptive_reflow.algorithm.scheduler import CosineAnnealScheduler
from adaptive_reflow.contracts import CosineScheduleConfig

cfg = CosineScheduleConfig(n_rounds=20, n_min=0.0, n_max=1.0)
sched = CosineAnnealScheduler(cfg)
print([sched.n_cap_for_round(r) for r in range(20)])
# -> [1.0, 0.98, 0.93, ..., 0.07, 0.02, 0.0]
```

### 2. `ConstantScheduler`

**When to use it.** When you want a flat budget across all rounds —
the simplest possible sanity check. Use it to verify your adapter
runs end-to-end before adding any schedule-driven complexity.

**Paper grounding.** None.

**Sample.**

```python
from adaptive_reflow.algorithm.scheduler import ConstantScheduler
sched = ConstantScheduler(cycle_length=20, n_cap=0.5)
print([sched.n_cap_for_round(r) for r in range(20)])
# -> [0.5, 0.5, ..., 0.5]
```

### 3. `LinearScheduler`

**When to use it.** Ramp-up or ramp-down baselines. `n_max > n_min`
gives a warm-start ramp; `n_min > n_max` gives a
front-load-exploration-then-refine ramp. Use it to compare a
monotone-linear schedule against cosine.

**Paper grounding.** None.

**Sample.**

```python
from adaptive_reflow.algorithm.scheduler import LinearScheduler
sched = LinearScheduler(cycle_length=20, n_min=0.0, n_max=1.0)
print([sched.n_cap_for_round(r) for r in range(20)])
# -> [0.0, 0.05, 0.10, ..., 0.95, 1.0]
```

### 4. `ExponentialScheduler`

**When to use it.** When you want a schedule that decays (or grows)
exponentially — useful for experiments where the first few rounds
should dominate and later rounds are diminishing-returns refinements.

**Paper grounding.** None.

**Sample.**

```python
from adaptive_reflow.algorithm.scheduler import ExponentialScheduler
sched = ExponentialScheduler(cycle_length=20, n_min=0.0, n_max=1.0, half_life=5)
print([sched.n_cap_for_round(r) for r in range(20)])
# -> [1.0, 0.87, 0.75, ..., 0.03, 0.03]
```

### 5. `PolynomialScheduler`

**When to use it.** When you want a polynomial `t^k` ramp; the
exponent `k` controls the shape (linear at `k=1`, quadratic at `k=2`,
sub-linear at `k<1`). Useful for ablation studies comparing ramp
shapes against cosine.

**Paper grounding.** None.

**Sample.**

```python
from adaptive_reflow.algorithm.scheduler import PolynomialScheduler
sched = PolynomialScheduler(cycle_length=20, exponent=2.0)
print([sched.n_cap_for_round(r) for r in range(20)])
# -> [1.0, 0.997, 0.99, ..., 0.06, 0.0]
```

### 6. `SigmoidScheduler`

**When to use it.** When you want an S-shaped transition — slow
start, fast middle, slow end. Use it when the early and late rounds
should have similar budgets but the middle rounds should differ.

**Paper grounding.** None.

**Sample.**

```python
from adaptive_reflow.algorithm.scheduler import SigmoidScheduler
sched = SigmoidScheduler(cycle_length=20, steepness=10.0)
print([sched.n_cap_for_round(r) for r in range(20)])
# -> [0.0, 0.0, 0.0, 0.5, 0.99, 1.0, ..., 1.0]
```

### 7. `ConvergenceAdaptiveScheduler`

**When to use it.** When the per-round metric is informative enough
to drive the next round's `n_cap`. The scheduler reads
`metrics['W2']` from the last round (or any metric the runner
publishes) and updates `n_cap` toward a target. Use it when you have
a stable, low-noise per-round metric.

**Paper grounding.** Self-reflexive loop (Loop 1 in
[`README.md`](../README.md#the-four-feedback-loops)). No external paper.

**Sample.**

```python
from adaptive_reflow.algorithm.scheduler import ConvergenceAdaptiveScheduler
sched = ConvergenceAdaptiveScheduler(cycle_length=20, target=0.5, learning_rate=0.05)
sched.record_round_feedback(round_index=0, metrics={"W2": 0.42})
print(sched.n_cap_for_round(1))  # 0.025 + ...  -- adapts toward target
```

### 8. `CodimensionSheetScheduler`

**When to use it.** The paper-grounded scheduler. The one to use for
the **paper-claim reproduction** (paper Theorem 1). Reads the four
paper quantities `A_g`, `B_g`, `C_g`, `e_rho` from
`paper_quantities` and produces a sheet-vs-cell `evidence_ratio`
(`= sheet / (sheet + cell)`) per round. Drives `n_cap` via the
canonical cosine baseline; the `evidence_ratio` is exposed via
`last_evidence_ratio` for audit.

**Paper grounding.** Li 2026 — Lemma 2 (sheet evidence `A_g`,
coarea weight `1 / sqrt(1 + g(x)^2)`), Lemma 3 (cell packing `C_g`),
Lemma 4/5 (exterior gap `e_rho`), Theorem 1 (BL-convergence with the
selection mechanism). ADR-0013.

**Sample.**

```python
from adaptive_reflow.algorithm.scheduler import CodimensionSheetScheduler
sched = CodimensionSheetScheduler(cycle_length=20, eps_implicit=0.05)
print([sched.n_cap_for_round(r) for r in range(20)])
print([sched.last_evidence_ratio for r in range(20)])
```

### 9. `EDMScheduler`

**When to use it.** When your model is from the EDM family (Karras et
al. 2022) and the original codebase used an EDM-style sigma schedule.
The scheduler exposes the EDM step-size / sigma progression as a
`n_cap` trajectory so the framework can drive EDM samplers without
re-implementing their noise schedule.

**Paper grounding.** EDM (Karras 2022) — sigma schedule, preconditioner.

**Sample.**

```python
from adaptive_reflow.algorithm.scheduler import EDMScheduler
sched = EDMScheduler(cycle_length=20, sigma_min=0.002, sigma_max=80.0, rho=7.0)
print([sched.n_cap_for_round(r) for r in range(20)])
```

### 10. `AdaptivePIDScheduler`

**When to use it.** When you have a per-round metric that drifts
slowly and you want PID control to keep it on target. Generalises
`ConvergenceAdaptiveScheduler` with P/I/D terms; useful when the
metric has inertia (e.g. a long rolling-average W2).

**Paper grounding.** Self-reflexive loop (Loop 1). No external paper.

**Sample.**

```python
from adaptive_reflow.algorithm.scheduler import AdaptivePIDScheduler
sched = AdaptivePIDScheduler(
    cycle_length=20, target=0.5, kp=0.2, ki=0.05, kd=0.01,
)
sched.record_round_feedback(round_index=0, metrics={"W2": 0.42})
print(sched.n_cap_for_round(1))
```

### 11. `JitteredConstantScheduler`

**When to use it.** When `ConstantScheduler` is too rigid and you
want the same average budget per round with deterministic per-round
jitter — useful for sweeping Monte-Carlo standard error.

**Paper grounding.** None.

**Sample.**

```python
from adaptive_reflow.algorithm.scheduler import JitteredConstantScheduler
sched = JitteredConstantScheduler(cycle_length=20, base_n_cap=0.5, jitter=0.05, seed=42)
print([sched.n_cap_for_round(r) for r in range(20)])
```

### 12. `MultiChannelJitteredConstantScheduler`

**When to use it.** When your adapter exposes multiple channels
(e.g. `coordinate + charge + pair`) and each should have its own
jittered-constant schedule. The `JitteredConstantScheduler` generalised
per-channel.

**Paper grounding.** None.

**Sample.**

```python
from adaptive_reflow.algorithm.scheduler import MultiChannelJitteredConstantScheduler
sched = MultiChannelJitteredConstantScheduler(
    cycle_length=20,
    base_n_cap={"coordinate": 0.5, "charge": 0.3, "pair": 0.7},
    jitter={"coordinate": 0.05, "charge": 0.02, "pair": 0.08},
    seed=42,
)
```

### 13. `EvidenceDrivenScheduler`

**When to use it.** The companion scheduler to
`CodimensionSheetScheduler` — it wraps a `CosineAnnealScheduler` and
adds a small PID-lite offset driven by the per-round
`selection_ratio` (paper Theorem 1 direction). Use it as the
"feedback-driven" arm of the four-scheduler ablation. Requires
`selection_evaluator` in `ReInferenceConfig`.

**Paper grounding.** Li 2026 — Theorem 1's selection mechanism.

**Sample.**

```python
from adaptive_reflow.algorithm.scheduler import EvidenceDrivenScheduler
from adaptive_reflow.contracts import CosineScheduleConfig

sched = EvidenceDrivenScheduler(
    CosineScheduleConfig(n_rounds=20, n_min=0.0, n_max=1.0),
    kp=0.2, ki=0.05, max_step=0.05, target_ratio=1.0, k_eps=0.5,
)
```

### 14. `FreeTrajScheduler`

**When to use it.** When you want a FreeTraj-style schedule
(per-round trajectory-aware substep sizing). The cosine baseline is
modulated by a small additive sinusoidal offset
`substep = amplitude * sin(2π * progress)` so the schedule is *not*
purely monotone — the key FreeTraj insight is that small oscillations
around the cosine baseline improve trajectory coverage without hurting
acceptance. Useful for image-flow models where the per-round
trajectory progress is informative.

**Paper grounding.** FreeTraj (Yan 2024).

**Sample.**

```python
from adaptive_reflow.algorithm.scheduler import FreeTrajScheduler
from adaptive_reflow.contracts import CosineScheduleConfig

sched = FreeTrajScheduler(
    CosineScheduleConfig(n_rounds=20, n_min=0.0, n_max=1.0),
    trajectory_amplitude=0.05, trajectory_period=4,
)
```

### 15. `SequentialScheduler`

**When to use it.** When you want to **compose** two or more
sub-schedulers — e.g. run a `LinearScheduler` for the first 5 rounds
then a `CosineAnnealScheduler` for the remaining 15. Each
sub-scheduler owns its own round range; the `SequentialScheduler`
hands off at the boundary.

**Paper grounding.** None.

**Sample.**

```python
from adaptive_reflow.algorithm.scheduler import (
    SequentialScheduler, SequentialSlot, CosineAnnealScheduler, LinearScheduler,
)
sched = SequentialScheduler(
    slots=(
        SequentialSlot(start=0, end=5, scheduler=LinearScheduler(cycle_length=5)),
        SequentialSlot(start=5, end=20, scheduler=CosineAnnealScheduler(cfg)),
    ),
)
```

### 16. `HandoffSequentialScheduler`

**When to use it.** When you want a `SequentialScheduler` that also
emits a handoff ledger row at each slot boundary — useful when the
audit trail must record that the schedule changed mid-run.

**Paper grounding.** None.

**Sample.**

```python
from adaptive_reflow.algorithm.scheduler import (
    HandoffSequentialScheduler, SequentialSlot, CosineAnnealScheduler, LinearScheduler,
)
sched = HandoffSequentialScheduler(
    slots=(
        SequentialSlot(start=0, end=5, scheduler=LinearScheduler(cycle_length=5)),
        SequentialSlot(start=5, end=20, scheduler=CosineAnnealScheduler(cfg)),
    ),
    handoff_audit_code="scheduler_handoff_v1",
)
```

---

## Drivers

A driver is anything that satisfies `PolicyDriverProtocol` — given
the current `schedule_sample` and `base_policy`, it returns the
per-channel `beta` (the noise coefficient, in `[0, 1]`) to apply for
this round. All 5 implementations live under
[`adaptive_reflow/algorithm/policy_driver.py`](../adaptive_reflow/algorithm/policy_driver.py).

### 1. `ScheduleDerivedPolicyDriver`

**When to use it.** The default. Mirrors the engine's inline
override `beta = n_cap` (so `memory_fraction = 1 - n_cap`). Use it
whenever you want the schedule to drive the restart policy.

**Sample.**

```python
from adaptive_reflow.algorithm.policy_driver import ScheduleDerivedPolicyDriver
driver = ScheduleDerivedPolicyDriver()
beta = driver.compute_policy(schedule_sample, base_policy=base, channel="xy")["xy"]
# beta == schedule_sample.n_cap
```

### 2. `ConstantPolicyDriver`

**When to use it.** When you want a fixed `beta` independent of the
schedule — e.g. you want the schedule to control something else
(per-round `num_steps`) and the restart policy to stay constant.

**Sample.**

```python
from adaptive_reflow.algorithm.policy_driver import ConstantPolicyDriver
driver = ConstantPolicyDriver(beta=0.3)
beta = driver.compute_policy(schedule_sample=None, base_policy=base, channel="xy")["xy"]
# beta == 0.3 for every round
```

### 3. `AdaptivePolicyDriver`

**When to use it.** When the per-round metric should adapt `beta`
toward a target — useful when you want the schedule to set `n_cap`
but `beta` to be controlled by the metric, not the schedule.

**Sample.**

```python
from adaptive_reflow.algorithm.policy_driver import AdaptivePolicyDriver
driver = AdaptivePolicyDriver(target=0.5, learning_rate=0.05, channel="xy")
beta = driver.compute_policy(schedule_sample=None, base_policy=base, channel="xy",
                              prior_endpoint_digest=prior_digest,
                              audit_codes=[], metrics={"W2": 0.42})["xy"]
```

### 4. `MultiChannelConstantPolicyDriver`

**When to use it.** When you have multiple channels and each should
get its own constant `beta` — e.g. `coordinate=0.3, charge=0.1, pair=0.5`.

**Sample.**

```python
from adaptive_reflow.algorithm.policy_driver import MultiChannelConstantPolicyDriver
driver = MultiChannelConstantPolicyDriver(beta_by_channel={"coordinate": 0.3, "charge": 0.1})
beta = driver.compute_policy(schedule_sample=None, base_policy=base, channel="coordinate")["coordinate"]
```

### 5. `DualTargetAdaptivePolicyDriver`

**When to use it.** When two channels each need an adaptive target
(e.g. a `coordinate` target and a `charge` target) and you want the
driver to track both with a single set of gains.

**Sample.**

```python
from adaptive_reflow.algorithm.policy_driver import DualTargetAdaptivePolicyDriver
driver = DualTargetAdaptivePolicyDriver(
    target_by_channel={"coordinate": 0.5, "charge": 0.3},
    learning_rate=0.05,
)
```

---

## Merge operators

A merge operator is anything that satisfies `MergeOperatorProtocol` —
given a previous round's restart fraction (`prev`) and a dynamic
target (`dynamic`), it returns the merged fraction for this round,
respecting a `cap` / `floor` envelope and `delta_cap_up` /
`delta_cap_down` step caps. All 8 implementations live under
[`adaptive_reflow/algorithm/merge_operator.py`](../adaptive_reflow/algorithm/merge_operator.py)
and its companion modules
(`merge_operator_extra.py`, `merge_operator_v3.py`).

### 1. `BoundedMergeOperator`

**When to use it.** The canonical symmetric, capped, floor-aware
merge (DTB-R3). Replaces the legacy `max(prev, dynamic)` operator
with one that can both increase and decrease the prior-round
fraction while respecting the envelope. Use it as the default for
any multi-channel merge.

**Sample.**

```python
from adaptive_reflow.algorithm.merge_operator import BoundedMergeOperator
op = BoundedMergeOperator(cap=0.95, floor=0.05, delta_cap_up=0.1, delta_cap_down=0.1)
result = op.merge(prev=0.3, dynamic=0.7, audit_codes=[])
# result is in [0.05, 0.95] AND in [prev-0.1, prev+0.1]
```

### 2. `IdentityOperator`

**When to use it.** When you want `result = dynamic` — i.e. no
prev-carry. Useful as a baseline to compare bounded merges against.

**Sample.**

```python
from adaptive_reflow.algorithm.merge_operator import IdentityOperator
op = IdentityOperator()
result = op.merge(prev=0.3, dynamic=0.7, audit_codes=[])
# result == 0.7
```

### 3. `EMAOperator`

**When to use it.** When you want exponential smoothing
`result = prev + alpha * (dynamic - prev)`. Use it when the
per-round metric is noisy and you want a smoother convergence.

**Sample.**

```python
from adaptive_reflow.algorithm.merge_operator import EMAOperator
op = EMAOperator(alpha=0.1)
result = op.merge(prev=0.3, dynamic=0.7, audit_codes=[])
# result == 0.3 + 0.1 * (0.7 - 0.3) == 0.34
```

### 4. `MeanFlowMergeOperator`

**When to use it.** When your model is a mean-flow (Geng 2024)
network and the merge should respect the mean-flow displacement
field. Use it for video / interpolation flow models where the
velocity field is time-averaged.

**Paper grounding.** MeanFlow (Geng 2024).

**Sample.**

```python
from adaptive_reflow.algorithm.merge_operator_v3 import MeanFlowMergeOperator
op = MeanFlowMergeOperator(cap=0.95, floor=0.05)
result = op.merge(prev=0.3, dynamic=0.7, audit_codes=[])
```

### 5. `KalmanBoundedMergeOperator`

**When to use it.** When the per-round `dynamic` estimate has a
known measurement noise and you want to use a Kalman-style update
to weight `prev` against `dynamic`. Use it when the per-round
estimator exposes a noise covariance.

**Sample.**

```python
from adaptive_reflow.algorithm.merge_operator_extra import KalmanBoundedMergeOperator
op = KalmanBoundedMergeOperator(cap=0.95, floor=0.05, measurement_noise=0.1)
result = op.merge(prev=0.3, dynamic=0.7, measurement_noise=0.1, audit_codes=[])
```

### 6. `BayesianMergeOperator`

**When to use it.** When you have a per-round Bayesian posterior on
`dynamic` (e.g. from MCMC) and want to combine it with `prev`'s
prior. Use it when the per-round metric has a calibrated posterior.

**Sample.**

```python
from adaptive_reflow.algorithm.merge_operator_extra import BayesianMergeOperator
op = BayesianMergeOperator(cap=0.95, floor=0.05, prior_strength=1.0)
result = op.merge(prev=0.3, dynamic=0.7, posterior={"mean": 0.7, "var": 0.01}, audit_codes=[])
```

### 7. `PIDIdentityOperator`

**When to use it.** When you want a PID-lite controller on top of
the identity merge — i.e. smooth toward the dynamic with P/I/D
terms, but always clamp to `[floor, cap]`.

**Sample.**

```python
from adaptive_reflow.algorithm.merge_operator_extra import PIDIdentityOperator
op = PIDIdentityOperator(cap=0.95, floor=0.05, kp=0.2, ki=0.05, kd=0.01)
result = op.merge(prev=0.3, dynamic=0.7, audit_codes=[])
```

### 8. `ScheduleAwareEMAOperator`

**When to use it.** When the EMA's `alpha` should depend on the
schedule's `n_cap` — e.g. `alpha = 0.1 * (1 + n_cap)`. Use it when
you want the merge to react more aggressively when the schedule
allocates more budget to the round.

**Sample.**

```python
from adaptive_reflow.algorithm.merge_operator_extra import ScheduleAwareEMAOperator
op = ScheduleAwareEMAOperator(cap=0.95, floor=0.05, base_alpha=0.1)
result = op.merge(prev=0.3, dynamic=0.7, schedule_n_cap=0.8, audit_codes=[])
```

---

## Blenders

A blender is anything that satisfies `RestartBlenderProtocol` —
given a prior endpoint, a fresh noise draw, and a `memory_fraction`,
it returns the blended state. All 6 implementations live under
[`adaptive_reflow/algorithm/blender.py`](../adaptive_reflow/algorithm/blender.py)
and its companion module
[`blender_extra.py`](../adaptive_reflow/algorithm/blender_extra.py).

### 1. `LinearBlender`

**When to use it.** The default. `new = m * prior + (1 - m) * fresh`
where `m = memory_fraction`. Use it for any continuous channel.

**Sample.**

```python
from adaptive_reflow.algorithm.blender import LinearBlender
blender = LinearBlender()
blended = blender.blend(prior_state, fresh_state, memory_fraction=0.7, channel="xy")
```

### 2. `DistanceDecayBlender`

**When to use it.** When the prior and fresh samples' distance
should gate the fresh contribution. `new = m * prior + (1 - m) *
fresh * decay_factor` where `decay_factor = sigmoid(-||prior -
fresh|| / temperature)`. Use it when the fresh sample is only useful
when it is close to the prior.

**Sample.**

```python
from adaptive_reflow.algorithm.blender import DistanceDecayBlender
blender = DistanceDecayBlender(temperature=1.0)
blended = blender.blend(prior_state, fresh_state, memory_fraction=0.7, channel="xy")
```

### 3. `OTLinearBlender`

**When to use it.** When the prior and fresh distributions are
empirically distinct and you want an optimal-transport (OT) map
between them before the linear blend. Use it when the prior and
fresh live in different coordinate frames.

**Sample.**

```python
from adaptive_reflow.algorithm.blender_extra import OTLinearBlender
blender = OTLinearBlender()
blended = blender.blend(prior_state, fresh_state, memory_fraction=0.7, channel="xy")
```

### 4. `MultiTemperatureDistanceDecayBlender`

**When to use it.** When the distance-decay should use per-channel
temperatures — e.g. `coordinate` gets `temperature=1.0`,
`charge` gets `temperature=0.5`. Use it when channels have different
distance scales.

**Sample.**

```python
from adaptive_reflow.algorithm.blender_extra import MultiTemperatureDistanceDecayBlender
blender = MultiTemperatureDistanceDecayBlender(
    temperature_by_channel={"coordinate": 1.0, "charge": 0.5},
)
```

### 5. `JointOTLinearBlender`

**When to use it.** When you have multiple channels and the OT map
should be computed **jointly** across them (so the per-channel
transport plans respect cross-channel correlations). Use it for
multi-channel adapters where the channels are correlated.

**Sample.**

```python
from adaptive_reflow.algorithm.blender_extra import JointOTLinearBlender
blender = JointOTLinearBlender()
blended = blender.blend(prior_state, fresh_state, memory_fraction=0.7, channel="coordinate")
```

### 6. `BarycentricBlender`

**When to use it.** When the prior lives in a constrained space
(e.g. a simplex of probabilities) and the blend should respect the
constraint via a barycentric projection. Use it for discrete /
categorical channels.

**Sample.**

```python
from adaptive_reflow.algorithm.blender_extra import BarycentricBlender
blender = BarycentricBlender()
blended = blender.blend(prior_state, fresh_state, memory_fraction=0.7, channel="category")
```

---

## How they wire together

```
SchedulerProtocol.sample(round_index, metrics)
            |
            v
        n_cap  ──── (memory_fraction = 1 - n_cap)
            |
            v
PolicyDriverProtocol.compute_policy(schedule_sample, base_policy, channel)
            |
            v
        beta_by_channel
            |
            v
MergeOperatorProtocol.merge(prev, dynamic, audit_codes)
            |
            v
        merged fraction (cap / floor enforced)
            |
            v
RestartBlenderProtocol.blend(prior_state, fresh_state, memory_fraction, channel)
            |
            v
        StateBundle (ready for next round)
```

The default stack — `CosineAnnealScheduler` + `ScheduleDerivedPolicyDriver`
+ `BoundedMergeOperator` + `LinearBlender` — is byte-equivalent to
the canonical 2D adapter's inline code. Every other operator in this
catalog is an *alternative* at one or more of the four arrows.

For the paper-claim reproduction, swap in `CodimensionSheetScheduler`
at the top arrow and `DistanceDecayBlender` at the bottom arrow; the
middle two stay the same.

---

## See also

- [`ARCHITECTURE.md`](../ARCHITECTURE.md) — the four-layer model and
  the four feedback loops.
- [`TUTORIAL.md`](./TUTORIAL.md) — fast on-ramp (5–10 minutes).
- the **Plug In Your Model** page — bring your own SOTA checkpoint.
- [`ADAPTER_INTERFACE_SPEC.md`](./ADAPTER_INTERFACE_SPEC.md) — the
  eight-method Protocol every adapter must satisfy.