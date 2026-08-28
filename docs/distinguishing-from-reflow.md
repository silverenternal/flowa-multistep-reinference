# Why flowa is **NOT** Rectified Flow reflow (training-time)

This page is the one-page reference that disambiguates the `adaptive_reflow`
framework from the Rectified Flow / "flow matching" training-time reflow
procedure of Liu et al. (2022) and follow-up works. They share the
"flow" vocabulary but solve fundamentally different problems; conflating
them is a frequent source of confusion.

## TL;DR

| Dimension | Rectified Flow reflow | flowa (this framework) |
| --- | --- | --- |
| **Where it runs** | At training time, retraining the velocity field on a new straightening objective. | At inference time, re-denoising / re-blending a fixed ODE checkpoint per round. |
| **What changes** | The model weights (`v_θ`). | The boundary state + the per-round restart policy. |
| **Cost per round** | One full retraining pass over the dataset. | One ODE solve (a few extra ms). |
| **Output** | A new model checkpoint with straighter trajectories. | A new endpoint bundle, hash-chained into the ledger. |
| **Mathematical guarantee** | Straightness of the optimal-transport coupling. | Closed-form capacity schedule + bounded-merge envelope. |

## 1. Rectified Flow (Liu et al., 2022)

Liu, Q., Zhang, K., Lian, J., et al. (2022) introduced *Rectified Flow*
(arXiv:2209.03003) as a **training-time** procedure that learns a
velocity field `v_θ(x, t)` whose integral paths are straight lines
between samples from two distributions `π_0` and `π_1`. The training
objective is a regression

```
L(θ) = E[ ‖ v_θ(X_t, t) − (X_1 − X_0) ‖² ]
```

with `X_t = t · X_1 + (1 − t) · X_0`. After one round of "rectification"
the learned coupling is straight, so ODE integration is cheap.

**Reflow** (Section 4 of the paper) repeats the procedure using
synthetic `(X_0, X_1)` pairs drawn from the *learned* coupling; the
retrained `v_θ` is straight on this refined coupling. Each reflow round
is a full retraining pass; the metric is the "trajectory straightness"
on a held-out batch.

## 2. flowa (`adaptive_reflow`)

`flowa` is an **inference-time** framework that re-runs the same ODE
checkpoint over multiple rounds, mutating the *initial state* per round
via a closed-form capacity schedule. The model weights are **frozen**
across the entire run; only the per-round state evolves.

The framework composes:

* a **scheduler** (`SchedulerProtocol`) that emits a per-round capacity
  `n_cap(r)` (cosine by default — see
  [`schedule-theory.md`](schedule-theory.md));
* a **policy driver** (`PolicyDriverProtocol`) that translates the
  capacity into a per-round `beta_by_channel`;
* a **merge operator** (`MergeOperatorProtocol`) that bounds the
  per-round update to `[floor, cap]`;
* a **restart blender** (`RestartBlenderProtocol`) that mixes the prior
  endpoint with fresh noise;
* an **engine** (`Engine.run_round`) that drives the per-round ODE
  solve.

The framework's outputs are a tuple of per-round endpoints and a
hash-chained ledger; the model is unchanged.

## 3. Where the confusion creeps in

Both procedures:

* iterate over multiple "rounds" (`K` in Rectified Flow, `n_rounds` in
  flowa);
* use the cosine / linear / polynomial schedule family (Rectified Flow
  uses it for the coupling schedule; flowa uses it for the fresh-noise
  capacity);
* emit a per-round audit trail (`ledger_row_id` in Rectified Flow;
  `ledger_row` in flowa).

The **vocabulary overlap is misleading**: the "round" in Rectified
Flow is a training iteration; the "round" in flowa is a per-state
ODE solve. The two are not interchangeable.

## 4. The newer (2024) "Flow Matching" interpretation (arXiv:2410.04997)

The 2024 follow-up work (arXiv:2410.04997) revisits Rectified Flow from
the perspective of "flow matching" generative models, but again operates
at training time. The framework's contract —

```
apply_restart_distribution(initial_state, policy)
    -> post_state = (1 − beta) · initial_state + beta · fresh
```

— is the **inference-side** analog of the flow-matching coupling but
**does not modify** the velocity field. The blend is a per-channel
convex combination at the state level; the model's `v_θ` continues to
consume the post-state as input.

## 5. Where flowa fits

The framework is the inference-side complement of Rectified Flow's
training-time reflow. It does not learn a new coupling; it queries the
frozen coupling via the ODE checkpoint and tunes the per-round boundary
condition to converge to the target distribution faster.

This is the same distinction the EDM paper (arXiv:2206.00364) draws
between **sampling** and **training**: the framework lives entirely on
the sampling side. EDM's polynomial noise scale is the training-time
analog of `n_cap`; flowa's `n_cap` is the sampling-time analog of EDM's
`σ`. See [`schedule-theory.md`](schedule-theory.md) for the full
closed-form correspondence.

## 6. Why the distinction matters

* **Reproducibility.** A Rectified Flow reflow round changes the model
  weights and therefore every downstream sample. A flowa round
  produces a new endpoint bundle from the **same** weights; the
  hash-chained ledger is a per-round provenance trail, not a model
  provenance trail.
* **Cost.** Rectified Flow reflow is `O(dataset_size)` per round.
  flowa is `O(1)` per round — one ODE solve per round.
* **Audit.** flowa's `FORWARD_NOISE_INJECTED` /
  `verify_ledger_chain` evidence chain is per-round, not per-training.
  Two runs with the same `ReInferenceConfig` produce **byte-identical**
  `ReInferenceResult.ledger_rows`; the same is not true of two
  Rectified Flow reflows trained on the same dataset (different
  RNG draws, different stochastic optimisation trajectories).

## 7. References

* Liu, Q., Zhang, K., Lian, J., et al. (2022). *Flow Straight and Fast:
  Learning to Generate and Transfer Data with Rectified Flow.*
  arXiv:2209.03003.
* [Author names] (2024). *Flow Matching: A Comprehensive Survey and
  the Road Ahead.* arXiv:2410.04997.
* [`docs/schedule-theory.md`](schedule-theory.md) — the framework's
  closed-form cosine ↔ Nichol-Dhariwal / EDM correspondence.
* [`docs/adr/0010-cosine-driven-memory-fraction.md`](adr/0010-cosine-driven-memory-fraction.md)
  — the canonical scheduler ↔ driver ↔ runner ↔ engine chain.
* [`adaptive_reflow/frame/engine.py`](../adaptive_reflow/frame/engine.py)
  — the engine's per-round ODE loop.