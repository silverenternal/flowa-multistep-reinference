# Algorithm improvement — Paper-quantity-driven `restart_beta` calibration (Phase 2 H1: B3 + B1+B2 partial)

**Date:** 2026-09-12
**Author:** Wave 123 Agent 6 (READ-ONLY synthesis; no implementation in Wave 123)
**Status:** IN PROGRESS (target-threshold code landed; CIFAR/twodim acceptance sweeps unmet)
**Wave:** Wave 123+ candidate (this plan is detailed enough that a future
wave can pick it up and ship)
**Closes:** Wave 33 audit Gap A Cause B3 (cosine ramp drives late-round
`restart_beta` too low) + B1 (NFE `//` integer division undercounts) +
B2 (late-round NFE under cosine ramp = 1 NFE for Heun degenerates).
**Companion synthesis doc:** `todo/algo-improvement-framework-vs-model-metrics-gap.md` §2
(hypothesis H1 + H4) + §4 (rank #1).

> **Why this matters:** The framework's `restart_beta` (the per-channel
> weight on the restart-blend operator) is the primary mechanism by
> which the framework injects its re-inference value-add into the
> trajectory. When the cosine ramp drives `n_cap → 0` in late rounds,
> the late-round `restart_beta` becomes **smaller than the merge
> envelope's `delta_cap_down`**, collapsing the late-round "restart"
> effect into a no-op. This is the **dominant** algorithmic cause
> of the `twodim_fm` +176-191% regression and the `rectified_flow_cifar`
> +24-31% regression. Fixing B3 alone is the highest-ROI code change
> in this entire analysis (rank #1 by the priority formula).

---

## 1. Background

### 1.1 Root cause B3: cosine ramp drives late-round `restart_beta` too low

`BoundedMergeOperator.merge` (`adaptive_reflow/algorithm/merge/merge_operator.py`
line 368-407) computes `target = clamp(dynamic, floor, cap)` and
clamps to `[max(floor, prev - delta_cap_down), min(cap, prev + delta_cap_up)]`.
The cosine ramp drives `n_cap → 0` late; the late-round `restart_beta`
(per-channel `beta_by_channel={"image": 0.5}` from
`docs/CONSOLIDATED_RESULTS.md` §6.1) becomes **smaller than the
`delta_cap_down`**, collapsing the late-round "restart" effect into
a no-op.

### 1.2 Root cause B1: NFE integer division undercounts NFE

In `tools/run_rf_cifar_ablation.py` (or equivalent), the per-round
NFE is computed as `nfe // n_rounds`. At `nfe=50, n_rounds=5` this
gives `10` per round, summed to `50` (matches). At `nfe=50, n_rounds=4`
this gives `12` per round, summed to `48` (off by 4%). At `nfe=10,
n_rounds=4` this gives `2` per round, summed to `8` (off by 20%).
The undercount is **`n_rounds − 1` extra NFE never executed**.

### 1.3 Root cause B2: late-round NFE under cosine ramp = 1 (Heun degenerates)

The `CosineAnnealScheduler` (default for the framework) maps
`n_cap → steps_per_round` via a monotone transform. With
`n_min=0, n_max=1, cycle_length=5`, the late rounds have `n_cap ≈ 0`,
which translates to `1 NFE per round` (Heun) or `0 NFE per round`
(Euler). Heun at 1 NFE is **worse than Euler at 1 NFE** because Heun's
trial step requires 1 NFE and the corrector needs another — at 1 NFE the
corrector is skipped, so Heun degenerates to Euler with overhead.

### 1.4 Cross-references

- `docs/audit/algorithm-gap-investigation.md` §2.2.1 (B1) + §2.2.2 (B2) + §2.2.3 (B3)
- `docs/audit/saturation-improvement-plan.md` FIX-3a (Wave 35 evidence-weighted NFE allocation; partial fix)
- `docs/CONSOLIDATED_RESULTS.md` §6.1 (CIFAR-10 +24-31% regression)
- `docs/CONSOLIDATED_RESULTS.md` §6 (twodim_fm +176-191% regression)

---

## 2. Goal

Three independent fixes that, together, are predicted to close the
`twodim_fm` +176-191% regression to TIE-or-framework_improves and
the `rectified_flow_cifar` +24-31% FID regression to TIE-or-framework_improves:

1. **B3 fix** (highest impact): lift `BoundedMergeOperator`'s
   `floor` by the per-channel minimum `beta` when `beta_by_channel`
   is supplied (~15 LOC in `merge_operator.py`).
2. **B1 fix** (NFE accounting): replace `nfe // n_rounds` with
   `ceil + carry` per-round NFE allocation that sums **exactly** to
   `nfe` (~10 LOC in `tools/run_rf_cifar_ablation.py` and any other
   affected driver).
3. **B2 fix** (Heun degeneration): enforce a minimum per-round NFE
   of 2 for Euler / 1 for Heun / 1 for Dopri5 (~10 LOC in the
   scheduler or batched_runner).

**Target metric improvement:**
- `rectified_flow_cifar` matched NFE=50: FID regression +24-31% → TIE
  (-1 to +3%).
- `rectified_flow_cifar` matched NFE=10: FID regression (currently
  noisier because of the 20% NFE deficit) → parity.
- `twodim_fm` at σ ∈ [0, 0.5]: +176-191% → TIE or framework_improves
  (B3 is the dominant fix for the synthetic case; pairs with
  `algo-improvement-restart-policy-collapse-fix.md` for full closure).

---

## 3. Approach

### 3.1 B3 fix: per-channel `beta` floor lift in `BoundedMergeOperator`

**File:** `adaptive_reflow/algorithm/merge/merge_operator.py` line 368-407
(`merge` method)

**Pseudocode (BEFORE):**

```python
def merge(
    self,
    dynamic: float,
    prev: float,
    beta_by_channel: dict[str, float] | None = None,
    ...
) -> float:
    target = clamp(dynamic, floor, cap)
    # Clamp to envelope [max(floor, prev - delta_cap_down), min(cap, prev + delta_cap_up)]
    target = max(target, prev - self.delta_cap_down)
    target = min(target, prev + self.delta_cap_up)
    target = max(target, self.floor)
    target = min(target, self.cap)
    return target
```

**Pseudocode (AFTER):**

```python
def merge(
    self,
    dynamic: float,
    prev: float,
    beta_by_channel: dict[str, float] | None = None,
    ...
) -> float:
    # Wave 123+ Plan #1 B3 fix: lift the merge envelope's `floor` by the
    # per-channel minimum `beta` when `beta_by_channel` is supplied.
    # Prevents the cosine-ramp's late-round `restart_beta` from collapsing
    # below the per-channel minimum (which collapses the restart into a no-op).
    # (Wave 33 audit B3: docs/audit/algorithm-gap-investigation.md §2.2.3)
    effective_floor = self.floor
    if beta_by_channel is not None:
        min_beta = min(beta_by_channel.values())
        effective_floor = max(self.floor, min_beta)
    target = clamp(dynamic, effective_floor, self.cap)
    target = max(target, prev - self.delta_cap_down)
    target = min(target, prev + self.delta_cap_up)
    target = max(target, effective_floor)
    target = min(target, self.cap)
    return target
```

### 3.2 B1 fix: `ceil + carry` NFE allocation

**File:** `tools/run_rf_cifar_ablation.py` (and any other affected
driver — search for `nfe // n_rounds` via `grep -rn`).

**Pseudocode (BEFORE):**

```python
steps_per_round = nfe // n_rounds
```

**Pseudocode (AFTER):**

```python
# Wave 123+ Plan #1 B1 fix: ceil+carry so the per-round NFE sums
# exactly to `nfe`. (Wave 33 audit B1: docs/audit/algorithm-gap-investigation.md §2.2.1)
remainder = nfe % n_rounds
steps_per_round = [
    (nfe // n_rounds) + (1 if i < remainder else 0)
    for i in range(n_rounds)
]
assert sum(steps_per_round) == nfe, f"NFE accounting bug: {sum(steps_per_round)} != {nfe}"
```

### 3.3 B2 fix: minimum per-round NFE

**File:** `adaptive_reflow/algorithm/runner/batched_runner.py` (or
the per-scheduler `sample` method).

**Pseudocode:**

```python
# Wave 123+ Plan #1 B2 fix: enforce minimum per-round NFE by integrator.
# Heun at 1 NFE degenerates to Euler (corrector skipped); Euler at 0 NFE
# is undefined. (Wave 33 audit B2: docs/audit/algorithm-gap-investigation.md §2.2.2)
MIN_STEPS_BY_INTEGRATOR = {"euler": 2, "heun": 1, "dopri5": 1}
integrator_name = self.integrator.__class__.__name__.lower()
min_steps = MIN_STEPS_BY_INTEGRATOR.get(integrator_name, 2)
steps_per_round = max(min_steps, int(round(nfe_per_round)))
```

### 3.4 Test plan

Add 4 unit tests to `tests/test_algorithm/test_bounded_merge_operator.py`
(or equivalent):

1. **Test 1 — B3 floor lift**: when `beta_by_channel={"image": 0.5}` is
   supplied and `floor=0.1`, the effective floor is `0.5` (not `0.1`).
2. **Test 2 — B1 exact sum**: for `nfe=50, n_rounds=4`, the
   `steps_per_round` list sums to exactly 50.
3. **Test 3 — B2 minimum steps**: with Euler integrator and
   `nfe_per_round=0.5`, the resulting `steps_per_round` is 2
   (the minimum).
4. **Test 4 — combined B1+B2+B3**: the integration test from
   `tests/test_algorithm/test_paper_quantities_orchestration.py`
   shows the matched-NFE criterion now passes for nfe=50, n_rounds=4
   (sum=50, no early-termination needed).

### 3.5 Verification sweeps

After the code change + unit tests pass, run three verification sweeps:

1. **`rectified_flow_cifar` N=200 matched NFE=50**: FID regression
   +24-31% → TIE-or-framework_improves (predicted Δ FID = -3 to -8).
   GPU, ~30 minutes.
2. **`rectified_flow_cifar` N=200 matched NFE=10**: parity (no
   regression, no improvement). GPU, ~15 minutes.
3. **`twodim_fm` N=100 at σ=0.0**: regression +191% → TIE-or-framework_improves.
   CPU-only, ~10 minutes.

The D.4 byte-stable regression vector must NOT change (`pytest tests/ -k "d4" -q` → 33/33 PASS).

---

## 4. Acceptance criteria

- [ ] `BoundedMergeOperator.merge` lifts the effective floor by
  per-channel minimum `beta` when `beta_by_channel` is supplied.
- [ ] `nfe // n_rounds` replaced with `ceil + carry` in all affected
  drivers (grep -rn `nfe // n_rounds` returns zero matches; the
  ceil+carry idiom is used everywhere).
- [ ] Minimum per-round NFE enforced by integrator in
  `BatchedRunner` / scheduler `sample`.
- [ ] Unit tests pass (4 new tests; existing tests unchanged).
- [ ] `pytest tests/ -k "d4" -q` → 33/33 PASS (byte-stable preserved).
- [ ] `rectified_flow_cifar` matched NFE=50 framework FID drift
  within ±5% of baseline (currently +24-31% regression).
- [ ] `rectified_flow_cifar` matched NFE=10 framework FID drift
  within ±5% of baseline (currently noisier because of NFE deficit).
- [ ] `twodim_fm` N=100 σ=0.0 framework_improves by ≥5% relative to
  baseline (currently +191% regression).
- [ ] `mkdocs build --strict` → EXIT=0.
- [ ] Single atomic commit, no push (user-gated).

---

## 5. Risk

| Risk | Severity | Mitigation |
|---|---|---|
| **B3 floor lift breaks the `merge_envelope_collapse` audit** (some configurations may rely on `floor=0` to allow the envelope to fully collapse) | P1 | Default `beta_by_channel=None` keeps the legacy `floor` behavior; the lift only applies when `beta_by_channel` is explicitly supplied |
| **B1 ceil+carry changes the matched-NFE grid** (the previous `nfe // n_rounds` was a deliberate simplification; the new sum-exact version may produce different per-round allocations that change published numbers) | P1 | Document the change in `docs/CONSOLIDATED_RESULTS.md` §6.1 as a Wave 123 additive update; do not retroactively change prior numbers |
| **B2 minimum NFE means `total_nfe > nfe`** (the matched-NFE criterion becomes "framework NFE ≥ baseline NFE" rather than "equal") | P2 | Document the change as a slight convention shift; Heun 2-NFE is the "fair" baseline for Euler 2-NFE per FM literature (per Wave 33 audit §2.2.2) |
| **D.4 byte-stable regression vectors change** (the per-round NFE allocation differs from the legacy `nfe // n_rounds` even with `ceil+carry` if `nfe % n_rounds != 0`) | P1 | Verify `BatchedRunnerConfig.config_hash()` is byte-stable (it should be; the `ceil+carry` is deterministic from `(nfe, n_rounds)`); if not, update D.4 vectors |
| **Wave 35 saturation plan FIX-3a already touches NFE allocation** (`tools/run_controlled_audit.py` has a `--nfe-allocation {uniform,evidence}` flag) | P2 | Read Wave 35 commits before applying; check for merge conflicts; pair the change with Wave 35's `evidence` allocation if possible |

---

## 6. Effort estimate

| Phase | Effort | Wall-clock | GPU hours |
|---|---|---:|---:|
| B3 code change (~15 LOC) + unit test (~20 LOC) | 0.25 day | 2 hours | 0 |
| B1 ceil+carry (~10 LOC across N drivers) + unit test (~15 LOC) | 0.25 day | 2 hours | 0 |
| B2 minimum NFE (~10 LOC) + unit test (~10 LOC) | 0.25 day | 2 hours | 0 |
| `rectified_flow_cifar` N=200 matched NFE=50 sweep (GPU) | 0.25 day | 2 hours | 1 |
| `rectified_flow_cifar` N=200 matched NFE=10 sweep (GPU) | 0.15 day | 1 hour | 0.5 |
| `twodim_fm` N=100 σ=0.0 audit (CPU-only) | 0.1 day | 1 hour | 0 |
| D.4 + mkdocs + commit + docs update | 0.1 day | 1 hour | 0 |
| **Total** | **~1.35 days** | **~11 hours** | **1.5 GPU-hours** |

**LOC budget:** ~35 LOC code + ~45 LOC tests + ~30 LOC docs = ~110 LOC total.

---

## 7. Follow-up

After this plan ships:

1. Pair with `algo-improvement-restart-policy-collapse-fix.md`
   (rank #2, same commit or adjacent commit) to close the bulk of
   `twodim_fm` + `CIFAR-10` regression (this plan closes the
   algorithmic core; the per-round `eps` schedule adds incremental
   refinement).
2. Update `docs/CONSOLIDATED_RESULTS.md` §6 + §6.1 with the new
   CIFAR-10 numbers (additive only; do not retroactively change
   prior numbers).
3. Update `docs/paper-draft.md` §6 (Algorithm section) to describe
   the per-channel `beta` floor lift as a paper-quantity-driven
   calibration.
4. Consider extending the same floor-lift pattern to other envelope
   operators (`BoundedRestartEnvelope`, `RestartDecaySchedule`) if
   they exhibit the same cosine-ramp collapse.

---

## 8. Cross-references

- `docs/audit/algorithm-gap-investigation.md` §2.2.1 + §2.2.2 + §2.2.3 (Wave 33 audit B1+B2+B3)
- `docs/audit/saturation-improvement-plan.md` FIX-3a (Wave 35 evidence-weighted NFE; orthogonal)
- `docs/CONSOLIDATED_RESULTS.md` §6 + §6.1 (twodim_fm + CIFAR-10 baselines)
- `todo/algo-improvement-framework-vs-model-metrics-gap.md` (this wave's synthesis; rank #1)
- `todo/algo-improvement-restart-policy-collapse-fix.md` (this wave's rank #2; pairs with this plan)
- `todo/completed/algo-improvement-convergence-order.md` (Wave 18 C.6 + Wave 20; orthogonal)
- `todo/completed/algo-improvement-D4-regression-vectors.md` (Wave 38; covers D.4 byte-stable)

---

## 9. Wave 123 close-out (placeholder)

This plan is authored in Wave 123 but NOT executed. Status:
**Execution authorized; remaining work is experiment-gated.** To execute:

1. Read this plan end-to-end (already done if you're the executor).
2. Read Wave 33 audit §2.2 + Wave 35 saturation plan FIX-3a to
   understand the prior recommendations.
3. Pre-flight check: confirm `BoundedMergeOperator` is the
   canonical merge envelope; confirm `tools/run_rf_cifar_ablation.py`
   is the canonical CIFAR-10 ablation driver; confirm `BatchedRunner`
   is the canonical runner.
4. Apply the 3 code changes + 4 unit tests in atomic commits (one
   per fix for safety: B3 → B1 → B2; each with D.4 verify).
5. Run the 3 verification sweeps.
6. Single atomic commit combining all 3 fixes; do NOT push (user-gated).
7. Author `docs/audit/waveN-phaseM-plan1-paper-quantity-beta.md` audit doc.
8. Update `todo/STATUS.md` + `docs/CONSOLIDATED_RESULTS.md` + `docs/paper-draft.md`.
9. Move this plan doc to `todo/completed/algo-improvement-paper-quantity-beta-calibration.md`.
