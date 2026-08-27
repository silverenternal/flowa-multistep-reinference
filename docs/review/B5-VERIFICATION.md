# B5 verification — "selection_ratio computed on source bundle, not the round's endpoint"

**Status:** reviewer's symptom confirmed, reviewer's mechanism **wrong**. The
true defect is **strictly worse** than claimed. Verdict: **case (c)**.

**Verified:** 2026-08-28. No code modified.

---

## 1. The call site

`adaptive_reflow/algorithm/runner.py:528-538` — inside the per-round loop of
`ReInferenceRunner.run`:

```python
# Optional paper-Theorem-1 (ADR-0013) selection metric. The
# ``PosteriorSelectionEvaluator`` measures the round's
# sheet-vs-cell evidence ratio; paper Proposition 3 predicts
# it rises toward 1 as the fresh-noise scale shrinks.
if config.selection_evaluator is not None and bundle is not None:
    selection_metrics = config.selection_evaluator.oracle(
        bundle, channel=primary_channel, seed=int(config.seed) + r
    )
    metric["selection_ratio"] = float(
        selection_metrics.get("selection_ratio", 0.0)
    )
```

First correction to the review: the runner calls **`.oracle(...)`**, not
`.evaluate(...)`. The review names a method the runner never invokes on this
object. `evaluate()` is dead code on this path.

## 2. Signature of the evaluator surface

`adaptive_reflow/eval/posterior_selection_evaluator.py:487-493`:

```python
def oracle(
    self,
    bundle: StateBundle,
    *,
    channel: ChannelName,
    seed: int,
) -> dict[str, float]:
```

and `posterior_selection_evaluator.py:422-428` for the sibling:

```python
def evaluate(
    self,
    bundle: StateBundle,
    *,
    channel: ChannelName,
    seed: int,
) -> ChannelTransferEvidence:
```

Both take a `StateBundle`. Neither takes an endpoints array or a source-round
id. So far, consistent with the review's framing.

## 3. Which object is actually passed — and what is actually measured

### 3a. The variable binding (reviewer's claim, narrowly correct)

At `runner.py:534` the name `bundle` holds:

- **round 0** — the fresh initial state from `runner.py:474-478`
  (`build_initial_state`, `source_round=0`);
- **round r > 0** — the value assigned at the *end of the previous iteration*,
  `runner.py:551-555`:

```python
# Carry the detached endpoint forward as the next source bundle.
if trace.integrator_trace is not None and bundle is not None:
    bundle = self._adapter.observe_endpoint(
        trace.integrator_trace, bundle
    )
```

That assignment sits at line 552, **after** the metric block at line 532. So at
round `r` the variable holds round `r-1`'s endpoint — i.e. round `r`'s *source*,
with `bundle.source_round == r` (`twodim_fm.py:702`, `next_round = source_round + 1`).
The review is right that the object in scope is the source bundle.

### 3b. What the evaluator does with it — the decisive fact

**It ignores it.** `oracle()` reads `bundle` only to type-check the parameter;
the arithmetic is delegated to `_compute_metrics(seed=...)`, which never
receives the bundle. `posterior_selection_evaluator.py:549-570`:

```python
def _compute_metrics(
    self,
    *,
    seed: int,
) -> tuple[float, float, float, float, float]:
    ...
    endpoints = self._generate_endpoints(seed=int(seed))
    _sheet_arr, cells_arr = sheet_cell_centers(self._target)
    s_ev, c_ev, ratio = selection_ratio(endpoints, cells_arr)
```

and `_generate_endpoints` (`posterior_selection_evaluator.py:594-611`) throws
away all loop state and re-samples from scratch against the evaluator's *own
private adapter instance* (constructed at `posterior_selection_evaluator.py:410-412`,
a different object from the runner's adapter):

```python
for i in range(n_gen):
    sample_id = (
        f"posterior_selection::{self._target}::seed{seed}::idx{i}"
    )
    initial = self._adapter.build_initial_state(
        batch_id=_INTERNAL_BATCH_ID,
        sample_id=sample_id,
    )
    trace = self._adapter.solve_ode(initial, condition, seed=int(seed))
```

`bundle` appears exactly once in the whole class body outside a signature:
`_derive_bundle_id` (`posterior_selection_evaluator.py:613-624`), which is used
by `evaluate()` for a provenance label only — and `evaluate()` is not on the
runner path at all.

### 3c. Empirical confirmation

Two structurally unrelated bundles, same seed, produce a bit-identical row:

```
SAME SEED, DIFFERENT BUNDLES:
  b1 (batch='B1', sample='S1')                  selection_ratio = 0.8102482213565426
  b2 (batch='TOTALLY-DIFFERENT', sample='XYZ-999') selection_ratio = 0.8102482213565426
  IDENTICAL: True
```

Across rounds as the runner drives it (`seed = 42 + r`, `n_gen=200`):

```
r=0  sel=0.804649  sheet=0.578526  cell=0.140454
r=1  sel=0.811001  sheet=0.602693  cell=0.140454
r=2  sel=0.807762  sheet=0.590169  cell=0.140454
r=3  sel=0.803144  sheet=0.573032  cell=0.140454
r=4  sel=0.809911  sheet=0.598431  cell=0.140454
r=5  sel=0.806825  sheet=0.586628  cell=0.140454
r=6  sel=0.807320  sheet=0.588495  cell=0.140454
r=7  sel=0.811363  sheet=0.604117  cell=0.140454
```

`cell_evidence` is a **compile-time constant** — `cell_evidence()`
(`posterior_selection_evaluator.py:270-288`) is a closed form over the fixed
analytic mode centres and has no data argument at all. `sheet_evidence` is the
mean of `exp(-x^2/2)` over 200 i.i.d. fresh draws. The per-round variation is
pure Monte-Carlo noise of order `1/sqrt(n_gen)` around a fixed population value.
There is no trend and no mechanism by which a trend could arise.

The existing test suite ratifies this: `tests/test_eval/test_posterior_selection_evaluator.py:112`
builds bundles via `_make_state_bundle(digest)` with arbitrary digests such as
`"posterior-selection-two-moons"` that are **not present in any adapter's
`_native_states` map**. A bundle that cannot be resolved to any state still
yields a passing evidence row — only possible because the bundle is never read.

### 3d. Verdict

**Case (c).** Not (a) and not (b). The measured quantity is neither the source
bundle's evidence nor the round-`r` endpoint's evidence — it is a fresh
`n_gen`-sample replay of the adapter's *unconditional prior-to-target map*,
computed on a separate adapter instance, with `seed` as the only round-varying
input. The metric is invariant to `beta`, `n_cap`, `memory_fraction`, the merge
operator, the blender, the scheduler, and every bundle the loop produces.

The reviewer diagnosed a wiring error ("wrong bundle passed"). The actual defect
is that the parameter is inert, so **no choice of bundle would change the
output**. Rewiring line 534 to pass a round-`r` endpoint bundle would be a
no-op — a fix that appears to address B5 while changing nothing.

## 4. Impact on the paper claim

The `selection_ratio` column cannot support any convergence claim.

Claims currently resting on it:

- `docs/adr/0013-posterior-selection-drives-algorithm.md:139` — "*is expected to
  converge to 1 as rounds progress*"
- `docs/adr/0013-posterior-selection-drives-algorithm.md:269` — "*the per-round
  `selection_ratio` exceeds 0.95 by round 19*"
- `docs/ABLATION.md:56` — "*Paper Proposition 3 predicts the ratio converges to 1
  as the noise scale shrinks*"

The committed ablation table (`docs/ABLATION.md:58-62`) is the falsification:

| Config | Round-0 | Final | Mean (last 5) |
|---|---:|---:|---:|
| multi_round_codimension_sheet_posterior_selection | 0.8061 | 0.8169 | 0.8088 |
| multi_round_cosine_posterior_selection | 0.8061 | 0.8169 | 0.8088 |

Two different schedulers, identical to four decimal places in every column. The
`+0.0108` round-0-to-final drift is sampling noise, not convergence, and it is
below the noise floor demonstrated in 3c.

The theory point in the task brief holds and sharpens the finding: paper
Theorem 1 is about concentration of the **endpoint** posterior on the sheet.
Measuring a fixed unconditional replay estimates a static property of the
`(adapter weights, target)` pair — a *difficulty* constant — and can never
exhibit the round-indexed concentration Proposition 3 describes.

### Prior art in-repo — this is partially known

`docs/ABLATION.md:133` already records it, and records it accurately:

> **The two selection-ratio curves are identical.** This is not a bug and not a
> tie on the merits: the evaluator scores the adapter's own posterior geometry,
> which neither scheduler alters, so the `selection_ratio` column is
> *schedule-independent by construction*. [...] Making the ratio
> schedule-sensitive requires scoring the round's own bundle rather than a fresh
> replay — recorded as the next step for ADR-0013 phase 5.

So the *behaviour* is documented. What is **not** reconciled is that ADR-0013
(lines 139, 269) still asserts convergence-to-1 as a live prediction of the
shipped metric. The repo simultaneously documents "schedule-independent by
construction" and "expected to converge to 1 as rounds progress." Those cannot
both be true. That contradiction, not the wiring, is the real defect surface.

Also minor doc drift: ADR-0013:187 specifies emission into
`RoundTrace.extras["selection_ratio"]`; the runner instead writes
`per_round_metrics[r]["selection_ratio"]` (`runner.py:536`).

## 5. Recommendation

**Document now; fix only behind a deliberate design decision.** Reasons:

1. The narrow "pass the other bundle" fix implied by the review is a no-op
   (see 3d) and would be actively harmful — it would close B5 while leaving the
   metric exactly as inert, with a commit message claiming otherwise.
2. `docs/ABLATION.md:133` already states the correct interpretation. The cheap,
   correct, immediate action is to make ADR-0013 agree with it.

### Immediate (documentation, no code)

- Amend `docs/adr/0013-posterior-selection-drives-algorithm.md:139` and `:269`:
  demote "expected to converge to 1" / "exceeds 0.95 by round 19" from claims
  about the shipped metric to *predictions about a future endpoint-conditioned
  metric that is not yet implemented*.
- State plainly in the ADR that the shipped `selection_ratio` is an
  **unconditional adapter/target difficulty constant**, invariant to loop state
  by construction, and is not evidence for Proposition 3.
- Rename on emission to something non-misleading — e.g.
  `adapter_selection_ratio_reference` — so no downstream reader mistakes a
  constant for a convergence curve. (`tools/run_ablation.py:739-774` renders it
  under a heading that invites exactly that misreading.)

### If the endpoint-conditioned metric is actually wanted (real fix)

The runner already has the round-`r` endpoint in hand *before* the metric block:
it is captured into `endpoints[r]` at `runner.py:497-506`, 26 lines above the
call site. The fix is therefore cheap in plumbing but has a genuine statistical
obstacle:

- Add an endpoints-array entry point to the evaluator, e.g.
  `score_endpoints(endpoints: NDArray) -> dict[str, float]`, reusing the
  existing pure `selection_ratio(endpoints, cells)` helper
  (`posterior_selection_evaluator.py:291-309`) — which already takes an array
  and needs no change.
- **Blocker to resolve first:** the runner produces exactly **one** endpoint per
  round (a single 2-vector, `runner.py:505-506`). `sheet_evidence` over `n=1` is
  `exp(-x^2/2)` for a single sample — variance far too high to read a trend
  from. Making this metric meaningful requires the runner to carry a *batch* of
  trajectories per round, which is a real architectural change to
  `ReInferenceRunner` and `TwoDimFMAdapter` (both are currently single-sample:
  `build_initial_state` draws `rng.standard_normal(2)`, `twodim_fm.py:423`),
  not a rewiring.

That scope is why "document now" is the right call, and why the review's
severity ranking (highest-impact, implying a quick high-value fix) is
misleading: the finding is real and its blast radius on the paper claims is
large, but there is no small correct code fix available.

## Files examined

- `C:\Users\31472\codes\flowa-multistep-reinference\adaptive_reflow\algorithm\runner.py`
- `C:\Users\31472\codes\flowa-multistep-reinference\adaptive_reflow\eval\posterior_selection_evaluator.py`
- `C:\Users\31472\codes\flowa-multistep-reinference\adaptive_reflow\adapters\twodim_fm.py`
- `C:\Users\31472\codes\flowa-multistep-reinference\tests\test_eval\test_posterior_selection_evaluator.py`
- `C:\Users\31472\codes\flowa-multistep-reinference\docs\ABLATION.md`
- `C:\Users\31472\codes\flowa-multistep-reinference\docs\adr\0013-posterior-selection-drives-algorithm.md`
- `C:\Users\31472\codes\flowa-multistep-reinference\tools\run_ablation.py`
