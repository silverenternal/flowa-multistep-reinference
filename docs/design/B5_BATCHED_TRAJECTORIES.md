# B5 architecture fix — batched trajectories for an endpoint-conditioned evidence metric

**Status:** design only. No code written, no code modified.
**Date:** 2026-08-28.
**Supersedes nothing.** Companion to `docs/review/B5-VERIFICATION.md` (the case-(c)
diagnosis) and ADR-0013.

> **Naming note.** Every class name proposed here is deliberately written in
> **bold**, not in backticks. `tools/check_docs_against_code.py` treats a
> backticked CamelCase token as a verifiable claim that the symbol exists under
> `adaptive_reflow/`; these symbols do not exist yet. Bold keeps the doc linter
> green until Phase A lands. Existing symbols are backticked as usual.

---

## 1. Problem statement

`docs/review/B5-VERIFICATION.md` establishes **case (c)**: the shipped
`selection_ratio` is not the wrong bundle's evidence — it is *nobody's* evidence.

Three facts from that verification, restated as the requirements this design
must satisfy:

1. **The bundle parameter is inert.** `EvidenceScaleGapMetric.oracle` reads
   `bundle` only to type-check it and to derive a provenance label; the
   arithmetic runs in `_compute_metrics(seed=...)`, which never receives the
   bundle (`adaptive_reflow/eval/posterior_selection_evaluator.py:605-626`).
   `_generate_endpoints` (`:628-667`) re-samples `n_gen` fresh endpoints from
   the metric's **own private adapter instance** (constructed at `:466-468`, a
   different object from the runner's adapter). Rewiring the call site to pass a
   round-`r` endpoint bundle is a no-op.
2. **The result is invariant to every algorithm knob.** Two structurally
   unrelated bundles at the same seed give a bit-identical row; two different
   schedulers give an ablation table identical to four decimals
   (`docs/ABLATION.md:58-62`). `cell_evidence` is worse than invariant — it is a
   compile-time constant, a closed form over fixed analytic mode centres with no
   data argument at all (`posterior_selection_evaluator.py:302-323`).
3. **The blocker is architectural, not a wiring bug.** The runner produces
   exactly **one** endpoint per round — a single 2-vector captured into
   `endpoints[r]` at `adaptive_reflow/algorithm/runner.py:497-506`. Sheet
   evidence over `n = 1` is `exp(-x^2/2)` for one sample. B5-VERIFICATION.md §5
   concludes: *"Making this metric meaningful requires the runner to carry a
   batch of trajectories per round, which is a real architectural change to*
   `ReInferenceRunner` *and* `TwoDimFMAdapter` *… not a rewiring."*

That batch is what this document designs.

### 1.1 Measured evidence that a batch fixes it

Two experiments were run against the shipped adapter (read-only, throwaway
scripts; RK4, `two_moons`, coarse 5-step grid) to check that the proposed fix
actually buys a schedule-sensitive metric before any code is committed to.

**Effect size** — endpoint-conditioned ratio as the memory fraction `m` varies,
batch of 2048 endpoints per cell:

| `m` (memory fraction) | sheet evidence | cell evidence | ratio |
|---:|---:|---:|---:|
| 0.00 | 0.595322 | 0.140454 | 0.809108 |
| 0.25 | 0.654612 | 0.140454 | 0.823343 |
| 0.50 | 0.626032 | 0.140454 | 0.816756 |
| 0.75 | 0.517390 | 0.140454 | 0.786494 |
| 1.00 | 0.407367 | 0.140454 | 0.743614 |

**Noise floor** — Monte-Carlo standard error of the ratio at batch size `B`
(endpoint population: mean sheet density 0.594938, std 0.285666, `n = 20000`):

| `B` endpoints/round | ratio std-error |
|---:|---:|
| 1 (today) | 0.074 |
| 16 | 0.0185 |
| **128** (proposed default, 8 x 16) | **0.0065** |
| 1000 | 0.0023 |
| 2048 | 0.0016 |

Three conclusions that shape the rest of this design:

* **The fix works.** The endpoint-conditioned ratio spans ~0.066 across the
  memory-fraction range — a quantity the scheduler, driver, and blender jointly
  control. The current metric spans 0.000.
* **128 endpoints/round is enough.** Effect size 0.066 against a 0.0065 noise
  floor is ~10:1. `B = 1` (today) has a noise floor of 0.074 — *larger than the
  entire effect*, which is exactly why the shipped column looks like flat noise.
* **It is responsive, not convergent.** The ratio is **non-monotone** in `m`
  (peak at `m = 0.25`, minimum at `m = 1.00`). This design therefore does **not**
  license the ADR-0013:139 / :269 claims ("converges to 1", "exceeds 0.95 by
  round 19"). See §5.4 — that contradiction must be resolved in the ADR
  regardless of whether this design is built.

---

## 2. Design constraints

### C1 — Byte-determinism (no randomness without a seed)

Every new entry point takes an explicit `seed` and derives all randomness from
`np.random.default_rng(seed)`, matching `build_initial_state`
(`adaptive_reflow/adapters/twodim_fm.py:417-423`) and
`apply_restart_distribution` (`:518-523`, seed derived from
`(policy_hash, source_round + 1)`).

**A measured caveat that constrains the whole design.** Vectorising RK4 over a
batch axis is *not* bit-identical to the current per-sample loop, because
NumPy's matmul dispatches different kernels and accumulation orders by operand
shape. Measured, comparing per-row endpoints against a single `B = 512`
integration of the same 512 initial conditions:

| batch shape | bit-identical to `B = 512`? | max abs diff |
|---|---|---:|
| `B = 1` | no | 8.88e-16 |
| `B = 2` | no | 8.88e-16 |
| `B = 3` | no | 8.88e-16 |
| `B = 8` | **yes** | 0.0 |
| `B = 17` | no | 4.44e-16 |
| `B = 64` | **yes** | 0.0 |
| `B = 128` | **yes** | 0.0 |

The pattern is BLAS-blocking dependent and non-monotone — it cannot be relied
on. Determinism must therefore be specified in three separate tiers:

* **D1 — reproducibility (required, achievable).** Same config (*including the
  batch shape*), same seed, same BLAS ⇒ bit-identical output. Verified: a
  re-run at fixed shape is bit-identical.
* **D2 — cross-shape invariance (NOT achievable, must not be claimed).**
  Endpoints depend on `trajectories_per_round x endpoints_per_trajectory` at the
  ~1e-15 level. Consequence: the batch shape **must** enter the runner's
  `config_hash` / algorithm-signature payload, and golden files must be keyed to
  a pinned shape. Cross-shape comparisons get a documented `1e-14` tolerance,
  never `assert_array_equal`.
* **D3 — legacy parity (required, achievable).** Measured: a `B = 1` batched
  integration **is** bit-identical to `_integrate_rk4` on the same `x0`, because
  `_velocity_field` already reshapes a 1-D input to `(1, 2)` before the matmul
  (`twodim_fm.py:122-140`). This is the linchpin of Phase C (§6): the legacy
  wrapper is byte-safe **only if** a batch-of-1 request is integrated as a
  literal `B = 1` call and never coalesced with other work.

### C2 — Keep the memory contract intact

The four algorithm protocol surfaces named in the runner's module docstring
(`runner.py:3-6`) are frozen: `SchedulerProtocol`, `PolicyDriverProtocol`,
`MergeOperatorProtocol`, `RestartBlenderProtocol`. Nothing in this design adds,
removes, or changes a method on any of them. All existing implementations keep
working untouched:

| surface | implementations that must keep working |
|---|---|
| `SchedulerProtocol` | `CosineAnnealScheduler`, `ConstantScheduler`, `LinearScheduler`, `ExponentialScheduler`, `PolynomialScheduler`, `SigmoidScheduler`, `ConvergenceAdaptiveScheduler`, `CodimensionSheetScheduler` (8) |
| `PolicyDriverProtocol` | `ScheduleDerivedPolicyDriver`, `ConstantPolicyDriver`, `AdaptivePolicyDriver` (3) |
| `MergeOperatorProtocol` | `BoundedMergeOperator`, `IdentityOperator`, `EMAOperator` (3) |
| `RestartBlenderProtocol` | `LinearBlender`, `DistanceDecayBlender` (2) |

> **Two corrections to the task brief.** (a) The brief says "4 scheduler
> protocols"; there are **4 protocol surfaces** and **8** scheduler
> implementations — the table above is the real inventory. (b) There is no
> **MemoryContract** class anywhere under `adaptive_reflow/`; the name appears
> only in `docs/lean/GAPS.md:283`. "Keep the memory contract intact" is read
> here as: the four protocol surfaces above, plus the capacity → memory
> transform `memory_fraction = 1 - n_cap` (`ScheduleSample.memory_fraction`) and
> the restart-blend semantics `m * prior + (1 - m) * fresh`
> (`_blend_endpoint_with_prior`, `twodim_fm.py:290-299`).

**A pre-existing fact this design must confront.** In the current runner, the
merge operator and the blender are *provenance-only*: `self._merge` and
`self._blender` are referenced nowhere in `run()` except
`_algorithm_signatures` (`runner.py:566-571`). The per-round blend actually
happens inside the adapter's `apply_restart_distribution`, which the engine
calls. So a batched runner that wants the blender to genuinely influence the
batch has two options; §3.3 picks one and says why.

### C3 — Backward compatibility

* `ReInferenceRunner`, `ReInferenceConfig`, `ReInferenceResult` keep their exact
  current signatures and semantics through Phases A and B.
* `EvidenceScaleGapMetric.evaluate` / `.oracle` keep accepting a `StateBundle`
  and returning what they return today. The byte-for-byte equality contract
  between `evaluate` and `oracle` (asserted by tests) is preserved on the legacy
  path.
* No existing golden file, ablation column, or ADR-quoted number changes value
  in Phase A. New behaviour arrives only through new entry points.

---

## 3. Proposed API

### 3.1 Placement

All three new types live in `adaptive_reflow/algorithm/runner.py`, alongside the
existing trio, and are added to that module's `__all__`. The runner module is
the right home because it is already "the only place that decides the
`(scheduler, policy_driver)` composition" (`runner.py:20-25`) — the batch axis
is a composition concern, not an engine concern.

### 3.2 The three types

**BatchedRunnerConfig** — a frozen dataclass that is a superset of
`ReInferenceConfig`, adding exactly two fields plus one determinism field the
brief did not ask for but C1/D2 requires:

* `trajectories_per_round: int = 8`
* `endpoints_per_trajectory: int = 16`
* `integration_chunk_size: int = 0` — `0` means "one matmul over the whole
  round's batch". Non-zero pins the chunk width so D1 survives a memory-driven
  change of chunking. It enters the config hash.

Everything else (`n_rounds`, `outer_cycle_id`, `target_round`, `seed`,
`channels`, `selection_evaluator`) carries over unchanged.

**BatchedTrajectoryRunner** — constructed keyword-only per the brief:
`(*, config, scheduler, policy_driver, blender, evaluator)`.

> **A third correction to the brief.** The brief's signature omits the
> `adapter`, which the runner cannot work without (`ReInferenceRunner.__init__`
> raises `ValueError("adapter_required")` on a missing adapter,
> `runner.py:353-355`), and omits `merge_operator`, which is needed for the
> algorithm-signature payload (`_algorithm_signatures` takes all four
> components). The recommended signature is therefore
> `(*, config, adapter, scheduler=None, policy_driver=None, merge_operator=None,
> blender=None, evaluator=None, engine=None)` — adapter required, the rest
> defaulting exactly as `ReInferenceRunner.__init__` does. Also note the brief
> puts `config` on the constructor while `ReInferenceRunner` takes it on
> `run()`; this design accepts `config` on the constructor **and** keeps
> `run(seed)` per the brief, with `run()` overriding only the seed.

**BatchedTrajectoryResult** — frozen dataclass with the attributes the brief
specifies:

* `per_round_endpoints: list[list[np.ndarray]]` — round → trajectory → array of
  shape `(endpoints_per_trajectory, dim)`.
* `per_round_w2: list[float]` — one genuine per-round W2. Worth noting what this
  fixes: `tools/run_ablation.py:651-668` currently scores round `r` on the
  *cumulative prefix* `endpoints[:r+1]` precisely because one endpoint per round
  is unscoreable. With a batch per round, W2 becomes a real per-round quantity
  and the cumulative-prefix workaround can be retired.
* `per_round_metric: dict[str, list[float]]` — metric name → per-round list.
  Carries `selection_ratio` plus `n_cap`, `memory_fraction`, `beta`, `W2`,
  `coverage`. Note this is the transpose of `ReInferenceResult.per_round_metrics`
  (`dict[int, dict[str, float]]`); the transposed shape is what plotting and
  the ablation renderer want. A `to_legacy_per_round_metrics()` helper converts.
* `evidence_at_round(r, eps) -> tuple[float, float, float]` — see §3.4.
* Plus, for parity with the legacy result: `config`, `round_traces`,
  `final_endpoint_digest`, `algorithm_signatures`.

### 3.3 How a round executes (and how the memory contract stays intact)

Per round `r`, for each of `trajectories_per_round` trajectories `j`:

1. The scheduler is sampled **once per round**, not per trajectory:
   `scheduler.sample(outer_cycle_id, r, target_round + r)`. One capacity per
   round is what makes the round's batch a population under a *single* policy —
   which is the whole point of the metric. Same for `driver.compute_policy`.
2. Each trajectory `j` owns an independent bundle lineage, seeded by
   `sample_id = f"runner-sample-{channel}-r{r}-t{j}"`. Because
   `_seed_from_ids` hashes `(batch_id, sample_id, source_round)`
   (`twodim_fm.py:90-94`), distinct `j` give independent, reproducible `x0`.
3. `Engine.run_round` is called **once per trajectory** with that trajectory's
   bundle. This is the key decision: the batch axis lives in the runner's loop,
   *not* inside the engine. The engine's fail-closed 6-step call order
   (`build_initial_state -> apply_restart_distribution -> compose_condition ->
   solve_ode -> observe_endpoint -> detach_and_validate_endpoint`,
   `frame/engine.py:8-10`) is exercised unchanged per trajectory, so every
   protocol, audit code, and ledger row keeps its current meaning. C2 is
   satisfied by construction rather than by argument.
4. The `endpoints_per_trajectory` axis is served by the adapter's new batched
   surface (§4), not by `endpoints_per_trajectory` separate engine calls. Each
   trajectory's engine round yields one *lineage* endpoint (the one that
   carries provenance forward); the batched integration yields the
   `endpoints_per_trajectory` *population* endpoints that the metric scores.
   Keeping these two distinct is what preserves D3 and keeps round traces
   comparable to the legacy runner's.
5. Feedback: `record_round_feedback(r, metric)` is invoked once per round with
   the round's *aggregated* metric dict, guarded by `hasattr` exactly as today
   (`runner.py:545-546`). Adaptive schedulers therefore see a low-variance W2
   instead of a one-sample W2 — a real improvement in their input signal, and a
   behaviour change that must be called out in the ADR.

On the blender: this design keeps the blend where it is (inside
`apply_restart_distribution`, driven by the policy's `beta`) so that Phase A
changes no numbers. Making the blender a first-class participant in the batch is
a **separate, later** decision, deliberately out of scope here; §7 records it as
an open question rather than smuggling it in.

### 3.4 `evidence_at_round` — and a fourth correction to the brief

The brief asks for `evidence_at_round(r, eps) -> (sheet, cell, ratio)`
"using `_paper_evidence_balance(n_cap[r], eps=current n_cap)`". Two problems:

1. **`_paper_evidence_balance` returns a scalar, not a triple.** Its signature
   is `_paper_evidence_balance(n_cap_base: float, eps_implicit: float) -> float`
   and it returns only `sheet / (sheet + cell)`
   (`adaptive_reflow/algorithm/scheduler.py:1548-1598`). The two terms are local
   variables. To return a triple, either (a) add a sibling helper in
   `scheduler.py` that returns all three and re-express the existing function as
   a projection of it — one authority for the arithmetic, no drift — or (b)
   recompute `sheet = max(n_cap, eps)` and `cell = (1 - n_cap)^2 * eps^2` at the
   call site, duplicating the closed form. **Recommend (a).**
2. **`eps = current n_cap` collapses the two axes.** The closed form already
   treats `eps_implicit` as a noise scale *distinct* from capacity, with
   `sheet = max(n_cap_base, eps)`. Setting `eps = n_cap` gives
   `ratio = 1 / (1 + (1 - n)^2 * n)`, a pure function of `n_cap` — defensible as
   "the round's own capacity is the noise scale", but it silently discards the
   scheduler's configured `eps_implicit`. **Recommend** `eps` default to the
   scheduler's own `eps_implicit` when it exposes one, with the brief's
   `eps = n_cap` available as an explicit opt-in.

**The most important point about this method: it is not the B5 fix.**
`evidence_at_round` is a *closed-form, schedule-conditioned prediction* — it
never looks at an endpoint. The B5 fix is the *empirical, endpoint-conditioned*
ratio in `per_round_metric["selection_ratio"]`. The design carries both, in
deliberately separate namespaces, because comparing them is the actual
falsifiable test:

| quantity | source | conditioned on | key |
|---|---|---|---|
| empirical ratio | the round's endpoint batch | endpoints, hence scheduler/driver/blender | `per_round_metric["selection_ratio"]` |
| closed-form ratio | `_paper_evidence_balance` | `n_cap`, `eps` only | `evidence_at_round(r, eps)` |

Reporting the closed form as if it were a measurement is precisely the error
that produced the ADR-0013 contradiction B5-VERIFICATION.md §4 documents. The
two must never share a column name.

---

## 4. `TwoDimFMAdapter` changes

Both additions are **new methods**; no existing method's behaviour changes.

### 4.1 `batched_integrate`

`batched_integrate(self, x0_batch, *, t_steps=5, seed) -> array of shape
(batch, t_steps + 1, dim)`.

Implementation route: a batched sibling of `_integrate_rk4`
(`twodim_fm.py:143-166`). The existing `_velocity_field` **already accepts
`(n, 2)` input** (`:122-140`), so the only change is that the new integrator
must not reshape `x0` to `(2,)`. Roughly 25 lines. Dormand-Prince is
deliberately **not** batched in Phase A: its step-size controller is per-sample
adaptive (`:235-286`), so batching it requires either lockstep stepping (changes
results) or per-sample loops (no speedup). The batched path is RK4-only and must
raise on a `dormand_prince` adapter rather than silently falling back.

**On the `t_steps=5` default.** The adapter's pinned default is 100
(`TWODIM_FM_NUM_STEPS`, `pinned_num_steps`). Measured difference between a
5-step and a 100-step grid on the same 64 initial conditions:

* endpoints: mean abs diff 1.67e-4, max 5.57e-4;
* `sheet_evidence`: 0.6414466698 (5 steps) vs 0.6414467583 (100 steps) — 7
  matching decimals.

So `t_steps=5` is fine for the **metric population** (a smooth average over
many endpoints absorbs the discretisation error) and **not** fine for anything
that feeds an endpoint digest, W2, or a golden file. Recommendation: keep the
brief's `t_steps=5` default on `batched_integrate` because its caller is the
metric, but the runner's lineage endpoints must continue to use
`condition.delta_spec["num_steps"]` = 100 via `solve_ode`. Document the split;
do not let 5 leak into the lineage path.

### 4.2 `generate_trajectory`

`generate_trajectory(self, *, n_trajectories=8, endpoints_per_trajectory=16,
n_gen=1000, seed) -> array of shape (n_trajectories, endpoints_per_trajectory,
n_gen, dim)`.

Semantics per the brief: for each round, `n_trajectories` independent ODE
integrations; each trajectory emits `endpoints_per_trajectory` endpoint samples;
each endpoint slot carries `n_gen` samples.

**Cost analysis — the default is not affordable as written.** The tensor implies
`8 x 16 x 1000 = 128,000` integrations per round. Measured throughput:

| path | per sample | 128,000/round | x20 rounds |
|---|---:|---:|---:|
| current per-sample loop, 100 steps | 4.37 ms | 9.3 min | 3.1 h |
| batched, 100 steps | 437 us | 55.9 s | 18.6 min |
| batched, 5 steps | 22.5 us | 2.89 s | **0.96 min** |

The ablation matrix is ~10 configurations x 2 targets (the CANONICAL_TARGETS /
CANONICAL_CONFIGURATIONS tuples in `tools/run_ablation.py:115-120` — tool-level
constants, not `adaptive_reflow/` symbols), so multiply the last column by ~20
cells: **~19 min** total at 5 steps, **~6.2 h** at 100 steps,
**~62 h** on the current unbatched path. Batching is a 19x throughput win and is
what makes any of this viable.

But note the noise-floor table in §1.1: `B = 128` already gives a 10:1 SNR.
`n_gen = 1000` buys 40:1 for 1000x the compute. Therefore:

* **Recommend `n_gen = 1` as the shipped default**, with the 4-D shape retained
  exactly as the brief specifies so the axis exists for a variance-audit mode
  (`n_gen > 1` answers "how much of the round-to-round wiggle is Monte-Carlo
  noise?", which is worth being able to ask once, not every run).
* At `n_gen = 1` the round's population is `8 x 16 = 128` endpoints,
  `~2.9 ms/round` at 5 steps — free.
* The 4-D tensor at the brief's defaults is 2.05 MB/round, 41 MB for 20 rounds,
  held live in `per_round_endpoints`. At `n_gen = 1` it is 41 KB. The doc should
  state the memory budget either way; `docs/PERFORMANCE_BUDGETS.md` will need a
  row.

---

## 5. `EvidenceScaleGapMetric` update

### 5.1 New entry point, not a changed one

The brief says "`evaluate()` now takes a batched result instead of a bundle". A
straight signature swap would break the `evaluate`/`oracle` byte-equality tests,
the `_EvaluatorProtocol` duck-type the runner depends on (`runner.py:92-103`),
and every existing caller. Instead:

* **Add** `score_endpoints(endpoints, *, target=None) -> dict[str, float]` — a
  thin wrapper over the *already-pure, already-array-shaped*
  `selection_ratio(endpoints, cells)` helper
  (`posterior_selection_evaluator.py:326-349`). No new math. This is the honest
  minimum: the pure helper needs no change at all, as B5-VERIFICATION.md §5
  already notes.
* **Add** `evaluate_batched(result, *, channel, round_index, seed)` and
  `oracle_batched(...)` returning `ChannelTransferEvidence` and a metric dict
  respectively, preserving the byte-equality contract *within* the new pair.
* **Keep** `evaluate` / `oracle` exactly as they are. They become explicitly
  labelled as the unconditional adapter/target difficulty reference.

### 5.2 Per-round computation

For round `r`: take the round's endpoint population (aggregate over all
`trajectories_per_round` trajectories by default — 128 endpoints beats 16, and
§1.1 shows the noise floor difference matters; per-trajectory scoring stays
available for variance diagnostics). Then

* `sheet = mean(exp(-x^2 / 2))` over the population — `sheet_evidence`, unchanged;
* `cell = sum_j exp(-|z_j|^2 / 2) / (2 pi)` over competing modes — `cell_evidence`, unchanged;
* `ratio = sheet / (sheet + cell)` — `selection_ratio`, unchanged.

### 5.3 The half-fix that must be declared

With the brief's formula, **only the numerator becomes endpoint-conditioned.**
`cell_evidence` takes `cells`, not endpoints; it is a closed form over fixed
analytic mode centres (`:302-323`). §1.1 confirms it empirically: cell evidence
is exactly 0.140454 at every memory fraction.

So "truly endpoint-conditioned" is, under the brief's formula, precisely
half-true, and the doc/ADR wording must say so. The option that would close the
gap — evaluating cell evidence *at the endpoints*, e.g. the endpoint mass
falling within `rho`-neighbourhoods of the cell centres, which is much closer to
paper Lemma 3's `int_{I_z} p_eps` than a density evaluated at a centre — is a
change to the metric's *definition*, not its plumbing. It is listed in §7 as an
open question and deliberately excluded from Phases A–C.

### 5.4 What this does and does not license

It licenses: "the per-round `selection_ratio` responds to the scheduler,
driver, and memory fraction, with a ~10:1 signal-to-noise ratio at the default
batch size."

It does **not** license ADR-0013:139 ("expected to converge to 1 as rounds
progress") or ADR-0013:269 ("exceeds 0.95 by round 19"). The measured ratio is
non-monotone in memory fraction and lives near 0.74–0.82 (§1.1). Landing this
design without amending those two lines would reproduce the exact defect
B5-VERIFICATION.md §4 identifies — the repo asserting convergence and
schedule-independence simultaneously. **The ADR amendment is a required
deliverable of Phase A, not a follow-up.**

---

## 6. Migration path

### Phase A — additive

* Add the three new types to `adaptive_reflow/algorithm/runner.py`; add
  `batched_integrate` + `generate_trajectory` to
  `adaptive_reflow/adapters/twodim_fm.py`.
* `ReInferenceRunner` untouched. Zero existing numbers move; zero golden files
  change.
* New tests: D1 reproducibility at pinned shape; D3 `B = 1` parity against
  `_integrate_rk4` (bit-exact — measured achievable); a shape-sensitivity test
  that *asserts the 1e-14 tolerance* rather than equality, so D2 is encoded as a
  known property instead of discovered later as a flake; a
  scheduler-sensitivity test asserting the ratio differs between two schedulers
  (the test that would have caught B5 originally).
* Amend ADR-0013:139 and :269 per §5.4. Add a `docs/PERFORMANCE_BUDGETS.md` row.
* Also needed: `mkdocs.yml`'s `not_in_nav` list covers `adr/*.md`, `audit/*.md`,
  and `review/*.md` but **not** `design/*.md` (`mkdocs.yml:122-134`), so this
  file will trip the `omitted_files: warn` validation until `design/*.md` is
  added. Not done here — this design touches no configuration.

### Phase B — dual-surface metric

* `EvidenceScaleGapMetric` supports both the legacy `StateBundle` path and the
  new batched-result path, per §5.1. Both live side by side; the legacy pair
  keeps its byte-equality contract.
* `tools/run_ablation.py` grows an opt-in batched cell so the two selection-ratio
  curves (empirical vs closed-form, §3.4) can be rendered next to each other and
  the flat-line claim is refuted with data in the committed table.
* Emission naming: the unconditional reference should be renamed on emission
  (B5-VERIFICATION.md §5 suggests `adapter_selection_ratio_reference`) so no
  reader mistakes a constant for a curve once a real curve exists alongside it.

### Phase C — `ReInferenceRunner` becomes a thin wrapper

Legal only because of D3: `B = 1` is bit-identical to the per-sample path
(measured). Conditions that must hold, and must be asserted by test:

* `trajectories_per_round = 1`, `endpoints_per_trajectory = 1`, `n_gen = 1`;
* the batch=1 request is integrated as a literal `B = 1` call, never coalesced
  with other trajectories (coalescing would silently change results at 1e-15 and
  break golden files);
* the lineage path keeps `num_steps = 100`, never `t_steps = 5`;
* `ReInferenceResult` is reconstructed from the batched result, including the
  `NaN`-sentinel semantics for uncaptured endpoints (`runner.py:436-444`) and the
  untransposed `per_round_metrics` shape.

If any of those cannot be met, **Phase C should be abandoned** and the two
runners left side by side. The value of Phase C is deduplication only; it is not
worth a single changed digit in a published table. This is a genuine
"stop and reassess" gate, not a formality.

---

## 7. Type-signature sketch (pseudocode — no implementation)

The blocks below are illustrative signatures only. None of these symbols exist
under `adaptive_reflow/` yet; bodies are elided.

### 7.1 Runner skeleton — pseudocode

```python
@dataclass(frozen=True)
class BatchedRunnerConfig:
    n_rounds: int = 20
    outer_cycle_id: int = 0
    target_round: int = 0
    seed: int = 42
    channels: tuple[str, ...] = ("xy",)
    selection_evaluator: object | None = None
    # -- new --
    trajectories_per_round: int = 8
    endpoints_per_trajectory: int = 16
    integration_chunk_size: int = 0       # 0 = whole-batch; pinned for D1
    endpoint_t_steps: int = 100           # lineage grid; NOT the metric's 5


@dataclass(frozen=True)
class BatchedTrajectoryResult:
    config: BatchedRunnerConfig
    round_traces: tuple[object, ...]
    final_endpoint_digest: str
    per_round_endpoints: list[list["np.ndarray"]]
    per_round_w2: list[float]
    per_round_metric: dict[str, list[float]]
    algorithm_signatures: dict[str, str]

    def evidence_at_round(
        self,
        r: int,
        eps: float | None = None,
    ) -> tuple[float, float, float]:
        """Closed-form (sheet, cell, ratio); NOT endpoint-conditioned."""

    def endpoints_for_round(self, r: int) -> "np.ndarray":
        """Flatten trajectories -> (n_traj * endpoints_per_traj, dim)."""

    def to_legacy_per_round_metrics(self) -> dict[int, dict[str, float]]:
        """Transpose to ReInferenceResult's metric shape."""


class BatchedTrajectoryRunner:
    def __init__(
        self,
        *,
        config: BatchedRunnerConfig,
        adapter: object,                      # FlowMatchingODEAdapter, required
        scheduler: object | None = None,
        policy_driver: object | None = None,
        merge_operator: object | None = None,
        blender: object | None = None,
        evaluator: object | None = None,
        engine: object | None = None,
    ) -> None: ...

    def run(self, seed: int | None = None) -> BatchedTrajectoryResult: ...
```

### 7.2 Adapter additions — pseudocode

```python
class BatchedTwoDimFMSketch:
    def batched_integrate(
        self,
        x0_batch: "np.ndarray",               # (batch, dim)
        *,
        t_steps: int = 5,
        seed: int,
    ) -> "np.ndarray":                        # (batch, t_steps + 1, dim)
        """RK4 only. Raises on a dormand_prince adapter."""

    def generate_trajectory(
        self,
        *,
        n_trajectories: int = 8,
        endpoints_per_trajectory: int = 16,
        n_gen: int = 1,                       # brief says 1000; see section 4.2
        seed: int,
    ) -> "np.ndarray":
        """(n_trajectories, endpoints_per_trajectory, n_gen, dim)."""
```

### 7.3 Metric additions and closed-form helper — pseudocode

```python
class EvidenceScaleGapSketch:
    def score_endpoints(
        self,
        endpoints: "np.ndarray",              # (n, 2)
        *,
        target: str | None = None,
    ) -> dict[str, float]:
        """Thin wrapper over the existing pure selection_ratio helper."""

    def oracle_batched(
        self,
        result: "BatchedTrajectoryResult",
        *,
        channel: str,
        round_index: int,
        seed: int,
    ) -> dict[str, float]: ...

    def evaluate_batched(
        self,
        result: "BatchedTrajectoryResult",
        *,
        channel: str,
        round_index: int,
        seed: int,
    ) -> object: ...                          # ChannelTransferEvidence


def paper_evidence_balance_terms(
    n_cap_base: float,
    eps_implicit: float,
) -> tuple[float, float, float]:
    """(sheet, cell, ratio) in scheduler.py; the existing scalar helper
    becomes a projection of this so there is one authority."""
```

---

## 8. Open questions (deliberately not decided here)

1. **Cell evidence at endpoints** (§5.3) — the change that would make the metric
   *fully* endpoint-conditioned. Changes the metric's definition; needs its own
   ADR and its own falsification test.
2. **Blender as a first-class batch participant** (§3.3) — today the blender is
   provenance-only on the runner path. Making it drive per-trajectory mixing
   would change numbers and needs a separate decision.
3. **Per-trajectory vs aggregate scoring** (§5.2) — aggregate is the default;
   whether per-trajectory spread is worth emitting as a column is unresolved.
4. **`eps` semantics** (§3.4) — capacity-as-noise-scale vs the scheduler's
   configured `eps_implicit`.
5. **Dormand-Prince batching** (§4.1) — out of scope; the adaptive controller is
   per-sample by construction.

## 9. Complexity estimate

**Medium.** Phase A is ~250–350 LOC of new code (one batched RK4 ~25 LOC, two
adapter methods, three dataclasses, one run loop that is a batched
transliteration of the existing one) plus ~200 LOC of tests, with **no
modifications to existing code paths**. The engineering is bounded and the
prototypes in §1.1/§4.2 already exercise the load-bearing parts.

The cost is not in the lines; it is in three places where care is
non-negotiable: the D2 cross-shape determinism boundary (which must be encoded
as a tolerance test, not discovered as a flake), the `t_steps` split between the
metric population and the lineage endpoints, and the ADR-0013 amendment without
which the fix re-creates the contradiction it exists to remove. Phase C is
optional and should be gated as described in §6.

## Files examined

* `adaptive_reflow/algorithm/runner.py`
* `adaptive_reflow/adapters/twodim_fm.py`
* `adaptive_reflow/eval/posterior_selection_evaluator.py`
* `adaptive_reflow/contracts/paper_quantities.py`
* `adaptive_reflow/contracts/bundle.py` (the task brief cited
  `contracts/evidence.py`; the `ChannelTransferEvidence` contract actually lives
  in `bundle.py:113-132`)
* `adaptive_reflow/algorithm/scheduler.py`
* `adaptive_reflow/algorithm/blender.py`
* `adaptive_reflow/algorithm/merge_operator.py`
* `adaptive_reflow/algorithm/policy_driver.py`
* `adaptive_reflow/frame/engine.py`
* `tools/run_ablation.py`
* `tools/check_docs_against_code.py`
* `docs/review/B5-VERIFICATION.md`
