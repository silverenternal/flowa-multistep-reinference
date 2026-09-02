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

## Hyperparameter-Free Framework Principle (DERIV-001)

The framework's `memory_fraction` (the per-round blend weight
passed to every `RestartBlenderProtocol.blend()` call) is
**derived**, not hand-set, by the canonical ADR-0010 cosine
transform `m = 1 - n_cap`. DERIV-001 extends that commitment:
every framework hyperparameter SHOULD trace to one (or more) of
five authorized sources — a JMAA paper quantity
(`A_g` / `B_g` / `C_g` / `e_rho`), a local curvature estimate
(Lipschitz constant `L_e`), a mathematical invariant of the
algorithm family (variance-preserving noise schedule, OT path,
BL-convergence Theorem 1), an information-geometry identity
(natural-gradient / Fisher-information over the algorithm
posterior), or a generic convergence-theorem quantity (Polyak
step size, Dormand-Prince adaptive `h_t`). Hand-set engineering
constants stay as **named provenance** with documented empirical
origin and are the documented exception, not the rule.

The principle is operationalized by an abstract
`DerivationRule` protocol and a closed-form concrete
`PolyakMemoryFraction` derivation that lives in
[`adaptive_reflow/algorithm/_derivation.py`](../adaptive_reflow/algorithm/_derivation.py)
and is re-exported through `blender_extra.derive_default_memory_fraction`.
The dispatcher is **strict DAG**: a derivation reads paper
quantities, scheduler state, OT metrics, or local curvature —
but never writes back into the quantities it derives from. The
Fisher-on-algorithm-posterior namespace is isolated from
Fisher-on-model-parameters by the `NAMESPACE_ALGORITHM_POSTERIOR`
constant. Every concrete derivation MUST declare
`derivation_source`, `derivation_formula`, and
`academic_precedent` class-level attributes so the docs verifier
(`tools/check_docs_against_code.py`) can attribute every derived
value to an authorized source.

### The five authorized sources

1. **Paper quantity** — derive from `A_g`, `B_g`, `C_g`, or
   `e_rho`. Example: `eps_threshold := e_rho` (JMAA Lemma 5
   exterior gap floor), `eps_implicit := e_rho / 4`.
2. **Local curvature** — derive from a Lipschitz constant
   `L_e`. Example: `eps_degenerate := machine_eps * |t - s|`
   (Hairer-Norsett-Wanner 1993 §II.3 Theorem 3.4).
3. **Mathematical invariant** — derive from a closed-form
   algorithm-family invariant (variance-preserving schedule,
   OT path, BL convergence). Example: `n_cap_max := 1 - 0`
   (cosine-driven memory fraction; Lipman et al. 2023 OT
   midpoint).
4. **Information-geometry identity** — derive from
   natural-gradient / Fisher-information over the algorithm
   posterior. Example: `alpha_grad := exp(-e_rho)` (Amari 1998
   Fisher-decay weighting).
5. **Generic convergence theorem** — derive from Polyak step
   size, Dormand-Prince adaptive `h_t`, or Adam-style time
   constant. Example: `tolerance_t := base_tol * n_min / n_cap_t`
   (Polyak 1969).

### Minimal proof: `PolyakMemoryFraction`

The current DERIV-001 application instantiates the principle on
the canonical restart blend's `memory_fraction`:

```text
m_t := W2_round_t / (W2_round_0 + W2_round_t)
```

This is the closed-form Polyak step applied to the
Wasserstein-gap ratio (Polyak 1969; s1 Principle 3, s3
refinement). When the round's residual profile matches the
round-0 baseline (`W2_round_t ≈ W2_round_0`), the fraction is
near 0.5 — neither prior nor fresh dominates. As the residual
profile sharpens (`W2_round_t → 0`), `m_t → 0` (memory fades;
fresh noise allowed to dominate). As the residual profile
grows (`W2_round_t > W2_round_0`), `m_t → 1` (prior dominates
because fresh is uninformative).

### Backward compatibility

The dispatcher falls back to the documented ADR-0010
cosine-driven `1 - n_cap` whenever the supplied derivation
context is missing the inputs the rule needs. The fallback is
fail-closed: a buggy W2 estimator that supplies negative or
non-finite values raises `ValueError`, which the dispatcher
catches and converts to the ADR-0010 fallback rather than
crashing the engine. Existing callers that do not pass a
context keep getting `1 - n_cap` verbatim, so the existing
2356+15 test suite remains green while the parameter-free
regime is opt-in.

### Sample

```python
from adaptive_reflow.algorithm.blender_extra import (
    derive_default_memory_fraction,
    make_derivation_context,
)

# Fallback path (legacy callers).
m = derive_default_memory_fraction(n_cap=0.4)  # m = 0.6

# Parameter-free derivation path (engine with W2 estimator).
ctx = make_derivation_context(
    n_cap=0.4, w2_round_t=0.25, w2_round_0=1.0
)
m = derive_default_memory_fraction(context=ctx)  # m = 0.2
```

### DAG / namespace discipline

The principle's strict-DAG rule says a derivation reads paper
quantities, scheduler state, OT metrics, or local curvature —
never writes back into the quantities it derives from. The
`Fisher-on-algorithm-posterior` namespace is isolated from
`Fisher-on-model-parameters` so a future FisherMemoryFraction (planned, not yet implemented)
derivation cannot accidentally share state with model-level
optimizers. The `DerivationCycleError` exception type enforces
runtime checks for the small set of concrete derivations that
participate in the cross-derivation DAG.

### See also

- [`adaptive_reflow/algorithm/_derivation.py`](../adaptive_reflow/algorithm/_derivation.py)
  — the abstract `DerivationRule` protocol + `PolyakMemoryFraction`
  concrete.
- [`tests/test_algorithm/test_derivation.py`](../tests/test_algorithm/test_derivation.py)
  — the regression tests for the protocol, the closed-form, the
  fallback, and the dispatcher.
- [`docs/adr/0010-cosine-driven-memory-fraction.md`](./adr/0010-cosine-driven-memory-fraction.md)
  — the ADR-0010 cosine-driven memory fraction preserved as the
  documented back-compat fallback.
- **[`docs/r17-survey/algorithm-correctness-evidence.md`](./r17-survey/algorithm-correctness-evidence.md)**
  — the *evidence chain* document. The hyperparameter-free principle
  above is verified end-to-end as **Gate 3 (P-19)**: 22 PASS tests across
  2 files (`tests/test_algorithm/test_hparam_derived_2d_oracle.py`,
  `tests/test_algorithm/test_hparam_derived_end_to_end.py`); 5
  derivation rules match closed-form on the 2D oracle; framework
  trajectory converges monotonically under derived hyperparameters.
  The full evidence chain (3 gates, 97 PASS tests, paper Section 4
  skeleton 4.1-4.5) lives in that document. **See also:
  docs/r17-survey/algorithm-correctness-evidence.md.**

### Full 23-hparam coverage map (P-18 + P-19)

The framework's algorithm layer exposes 23 hyperparameters
across the scheduler / merge / blender / evidence-driver surface.
Each is sourced from one of the five authorized categories
(paper quantity, local curvature, mathematical invariant,
information-geometry identity, generic convergence theorem) —
the source is encoded as `derivation_source` on the
`DerivationRule` class. The table below enumerates every entry
with its derivation source, the closed-form formula, the
hand-set back-compat fallback (preserved verbatim so legacy
callers keep getting the same value when the context is
missing), and the academic citation.

| # | Hyperparameter | Source | Closed-form | Fallback (back-compat) | Citation |
|---|---|---|---|---|---|
| 1 | `eps_threshold` (BL-convergence) | paper_quantities | `sqrt(e_rho * delta_t)` | `1e-3` | BLConvergenceEpsilonSchedule (P-18) |
| 2 | `EvidenceDrivenScheduler.strength` | bl_convergence | `1.0` (Theorem 1 fixed) | `1.0` | MeanFlowFixedStrengthRule (P-19) |
| 3 | `eps_implicit` (codimension sheet) | paper_quantities | `eps_0 * (1 + C_g * t)` | `0.05` | OTEpsilonSchedule (P-18) |
| 4 | `BoundedMergeOperator.e_rho/4` floor | paper_quantities | `e_rho / 4` (divisor IS derivation) | `4.0` | BoundedMergeFloorRule (P-19, named provenance) |
| 5 | `MeanFlowMergeOperator.{t, s}` | other (boundary) | `t=1.0, s=0.0` (Theorem fixed) | `(1.0, 0.0)` | BoundaryConditionRule (P-19) |
| 6 | `MeanFlowMergeOperator.alpha_grad` | fisher | `exp(-e_rho) * m_Fisher` | `0.5` | FisherMemoryFraction (P-18) |
| 7 | `MeanFlowMergeOperator.tolerance` | polyak | `base_tol * n_min / n_cap_t` | `1e-9` | MeanFlowToleranceRule (P-19) |
| 8 | `MeanFlowMergeOperator.degenerate_eps` | lipschitz | `machine_eps * |t - s|` | `1e-12` | MachineEpsilonRule (P-19) |
| 9 | `EMAOperator.alpha` (ScheduleAwareEMAOperator) | polyak | `1 / (1 + grad_var / grad_mean^2)` | `0.1` | EMAInverseVarianceRule (P-19) |
| 10 | `DEFAULT_DISTANCE_DECAY_TEMPERATURE` | lipschitz | `1 / sqrt(L_local * n_rounds)` | `1.0` | LipschitzTemperatureRule (P-19) |
| 11 | `DEFAULT_MIN_GUMBEL_TEMP` | paper_quantities | `e_rho / 4` | `1e-3` | MinGumbelTempRule (P-19) |
| 12 | `EPS_LOG` (CategoricalAwareBlender) | paper_quantities | `e_rho / 8` | `1e-30` | EpsLogRule (P-19) |
| 13 | `ExponentialScheduler.alpha` | variance_preserving | `ln(n_max / n_min) / (cycle_length - 1)` | `0.1` | ExponentialAlphaRule (P-19) |
| 14 | `PolynomialScheduler.power` | variance_preserving | `2 * L / (L + 1)` | `2.0` | PolynomialPowerRule (P-19) |
| 15 | `SigmoidScheduler.{midpoint, steepness}` | information_geometry | `(n_min + n_max) / 2`; `1 / I_F(W2)` | `(0.5, 10.0)` | SigmoidMidpointSteepnessRule (P-19) |
| 16 | `ConvergenceAdaptiveScheduler.{kp, kd, shift_max, ema}` | polyak | `kp = 0.10 * W2-ratio`; `kd = 0.05 * (1-W2-ratio)`; `shift_max = 3*W2-ratio^2`; `ema = 1 / (1 + L/β_1)` | `(0.10, 0.05, 0.15, 0.3)` | ConvergenceAdaptivePolyRule (P-19) |
| 17 | `DEFAULT_FEEDBACK_METRIC_WEIGHTS` | fisher | `1 / Var_m` per metric | `{W2: 1.0, coverage: 0.3, selection_ratio: 0.5}` | MetricWeightRule (P-19) |
| 18 | `JitteredConstantScheduler.jitter_std` | variance_preserving | `sqrt(n_cap * (1 - n_cap) / n_rounds)` | `0.05` | VariancePreservingJitterRule (P-19) |
| 19 | `HandoffSequentialScheduler.handoff_window` | lipschitz | `round(1 / L_e)` | `0` | LipschitzStepSize (P-18, handoff subdispatch) |
| 20 | `DEFAULT_CONSTANT_BETA` / `DEFAULT_ADAPTIVE_TARGET_ESTIMATE` | ot | `(n_min + n_max) / 2` | `0.5` | MidpointBetaRule (P-19) |
| 21 | `memory_fraction` (blender_extra) | ot | `W2_t / (W2_0 + W2_t)` | `1 - n_cap` (ADR-0010) | PolyakMemoryFraction (P-18) |
| 22 | EDM `sigma_min/sigma_max/rho` | paper_quantities | Karras EDM Table 1 (already derived) | `(0.002, 80.0, 7.0)` | Karras 2022 EDM preconditioner (NO-OP) |
| 23 | `nfe/num_steps` (adapter-layer) | lipschitz | Dormand-Prince adaptive `h_t` | adapter default | LipschitzStepSize (P-18, **deferred to FM-LCM**) |

#### Source-category legend

* `paper_quantities` — Derive from JMAA Lemmas 2–5 (`A_g`, `B_g`, `C_g`, `e_rho`).
* `local_curvature` (alias `lipschitz`) — Derive from a Lipschitz constant `L_e`.
* `mathematical invariant` (alias `variance_preserving` / `ot` / `bl_convergence` / `other`) — Derive from a closed-form algorithm-family invariant.
* `information-geometry identity` (alias `fisher`) — Derive from natural-gradient / Fisher-information over the algorithm posterior.
* `generic convergence theorem` (alias `polyak`) — Derive from Polyak step size, Dormand-Prince adaptive `h_t`, Adam-style time constant.

The 22 active `default_*` entry points plus 1 named-provenance
divisor (P-19 #4) total **23 algorithm-layer hyperparameters**
fully covered by DERIV-001 — `nfe/num_steps` (P-19 #23) is the
adapter-layer FM-LCM territory deferred per P-18 task statement.

#### Wiring pattern

Every entry point lives in the algorithm module that owns the
hyperparameter (e.g. `merge_operator_v3.py::derive_default_alpha_grad`,
`evidence_driver.py::derive_default_eps_threshold`,
`scheduler/_core.py::derive_default_eps_implicit`,
`handoff.py::derive_default_handoff_window`,
`blender_extra.py::derive_default_memory_fraction`) and is
re-exported from `adaptive_reflow.algorithm._derivation` via
the canonical `default_X` dispatcher for cross-module use. The
`adaptive_reflow/algorithm/_derivation.py` module carries the
abstract `DerivationRule` protocol plus the 18 P-19 concrete
subclasses; the 5 P-18 subclasses (PolyakMemoryFraction,
OTEpsilonSchedule, BLConvergenceEpsilonSchedule,
LipschitzStepSize, FisherMemoryFraction) were already in
place. Tests in
`tests/test_algorithm/test_hparam_derived_2d_oracle.py` and
`tests/test_algorithm/test_hparam_derived_end_to_end.py`
exercise every rule on the canonical 2D Gaussian-mixture
oracle (P-13) under both closed-form and fallback paths.

---

## See also

- [`ARCHITECTURE.md`](../ARCHITECTURE.md) — the four-layer model and
  the four feedback loops.
- [`TUTORIAL.md`](./TUTORIAL.md) — fast on-ramp (5–10 minutes).
- the **Plug In Your Model** page — bring your own SOTA checkpoint.
- [`ADAPTER_INTERFACE_SPEC.md`](./ADAPTER_INTERFACE_SPEC.md) — the
  eight-method Protocol every adapter must satisfy.