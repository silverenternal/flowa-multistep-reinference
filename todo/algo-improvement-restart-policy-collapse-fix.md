# Algorithm improvement — Restart-policy collapse fix (Phase 2 H1: A1+A2)

**Date:** 2026-09-12
**Author:** Wave 123 Agent 6 (READ-ONLY synthesis; no implementation in Wave 123)
**Status:** SHIPPED (Wave 125 — code landed `4fbf135`); camera-ready only — twodim/CIFAR acceptance deferred
**Wave:** Wave 123+ candidate (this plan is detailed enough that a future
wave can pick it up and ship)
**Closes:** Wave 33 audit A1+A2 (`docs/audit/algorithm-gap-investigation.md`
§1.2.1 + §1.2.2) — `eps_implicit` is a constant, not a schedule; the
`eps_direction="decreasing"` flag is implemented as a flip, not a ramp.
**Companion synthesis doc:** `todo/algo-improvement-framework-vs-model-metrics-gap.md` §2
(hypothesis H3) + §4 (rank #2).

> **Why this matters:** The framework's load-bearing scheduler
> (`CodimensionSheetScheduler`) claims to honor JMAA Theorem 1's
> `eps → 0` limit by routing `eps_implicit` through a closed-form
> `paper_evidence_balance` ratio. In practice `eps_implicit=0.05` is
> a **constant** that drives the ratio to move <0.05 over an entire
> cycle, nullifying the paper's diminishing-noise semantic. Every
> downstream consumer (per-round NFE allocation, restart merge,
> paper-quantity signal propagation) inherits this collapse. Fixing
> it is the cheapest way to materially change the framework's
> behavior on twodim_fm + CIFAR-10 + (potentially) Kanzi/LineageFlow.

---

## 1. Background

### 1.1 Root cause A1: `eps_implicit` is hardcoded to 0.05

`adaptive_reflow/algorithm/scheduler/_core.py` line 2717:

```python
eps_implicit: float = 0.05
```

in `CodimensionSheetScheduler.__init__`. The scheduler then plugs this
**constant** into `_paper_evidence_balance` (line 2509) at every round:

```python
sheet = max(n_cap_base, eps)               # eps = 0.05 CONSTANT
cell  = (1 - n_cap_base) ** 2 * eps ** 2   # eps = 0.05 CONSTANT
ratio = sheet / (sheet + cell)
```

Paper Theorem 1 (line 87-92 of `NoiseSelectedRectification_EN.md`) makes
its claim **in the limit `eps → 0`**. The implementation treats `eps` as a
fixed scale and not as a diminishing schedule. Consequence: the
closed-form `ratio` is **near-constant across rounds** because the
`(1 - n_cap_base)²` term multiplied by `eps² = 0.0025` can never dominate
the `max(n_cap_base, eps) ≈ 0.05` term. Quick numerical check:

| r | n_cap_base | sheet | cell | ratio |
|---:|---:|---:|---:|---:|
| 0 | 1.000 | 1.000 | 0.000 | **1.0000** |
| 1 | 0.998 | 0.998 | 0.000 | **1.0000** |
| L-1 | 0.000 | 0.050 | 0.0025 | **0.9524** |

The ratio moves **0.048 over the entire cycle**; the paper-driven
`n_cap = n_min + (n_max - n_min) · ratio` is essentially constant at
`n_max`.

### 1.2 Root cause A2: `eps_direction="decreasing"` is a flip, not a ramp

`CodimensionSheetScheduler.sample` (line 3121-3122) only applies `1 -
ratio` for the legacy `"increasing"` direction. For the paper-aligned
`"decreasing"` direction (the default) it does **not** scale `eps` with
the round index. Paper Theorem 1's `eps → 0` should be realized as
**`eps_implicit(r) → 0` as `r → L-1`** (a schedule, not a flip).

### 1.3 Cross-references

- `docs/audit/algorithm-gap-investigation.md` §1.2.1 (A1) + §1.2.2 (A2)
- `docs/audit/saturation-improvement-plan.md` §1 T2 (convergence-aware
  round termination — partially addresses the same root cause via
  `should_terminate_round`; orthogonal fix)
- `docs/CONSOLIDATED_RESULTS.md` §6 (twodim_fm +176-191% regression)
- `docs/CONSOLIDATED_RESULTS.md` §6.1 (CIFAR-10 +24-31% regression)

---

## 2. Goal

Replace the constant `eps_implicit` plug in
`CodimensionSheetScheduler.sample` with a **per-round decreasing
schedule** `eps(r) = eps_0 · (1 - u_r)` where `u_r = r / (L - 1)` is the
round-index fraction. Realize Paper Theorem 1's `eps → 0` limit as a
proper schedule, not a flip.

**Target metric improvement:**
- `twodim_fm` regression at σ ∈ [0, 0.5]: from +176-191% to TIE or
  framework_improves (-5 to -15% relative to baseline).
- `rectified_flow_cifar` matched-NFE regression: partial closure (B1+B2
  is the dominant fix; this fix adds -1 to -3% on top).
- **Caveat:** Kanzi/LineageFlow framework-vs-baseline gap is not
  directly driven by `eps_implicit` (they have their own
  adapter-layer gaps — see `adapter-improvement-inv-proj-bridge-lossy-replacement.md`).
  This fix primarily moves the **synthetic-toy** + **CIFAR-10** verdict.

---

## 3. Approach

### 3.1 Code change (~10 LOC)

**File:** `adaptive_reflow/algorithm/scheduler/_core.py`

**Change site:** `CodimensionSheetScheduler.sample` line 3103-3111
(replace the constant `eps_implicit` plug with a per-round schedule).

**Pseudocode (BEFORE):**

```python
ratio = float(
    _paper_evidence_balance(
        n_cap_base,
        self._eps_implicit,           # <-- CONSTANT
        sheet_A=self._sheet_A,
        packing_B=self._packing_B,
        cell_C=self._cell_C,
    )
)
```

**Pseudocode (AFTER):**

```python
# Wave 123+ Plan #2: per-round decreasing schedule eps(r) = eps_0 * (1 - u_r)
# Realizes Paper Theorem 1's `eps -> 0` limit as a schedule, not a flip.
# (Wave 33 audit A1+A2: docs/audit/algorithm-gap-investigation.md §1.2.1+1.2.2)
u_r = round_idx / max(self.cycle_length - 1, 1)  # avoid /0
if self._eps_direction == "decreasing":
    eps_per_round = float(self._eps_implicit) * (1.0 - u_r)
elif self._eps_direction == "increasing":
    eps_per_round = float(self._eps_implicit) * u_r
else:  # legacy "constant"
    eps_per_round = float(self._eps_implicit)
ratio = float(
    _paper_evidence_balance(
        n_cap_base,
        max(eps_per_round, 1e-9),     # paper-aligned diminishing eps
        sheet_A=self._sheet_A,
        packing_B=self._packing_B,
        cell_C=self._cell_C,
    )
)
```

### 3.2 Config plumbing (optional, ~5 LOC)

If `eps_direction` is exposed in `to_config()` / `config_hash()`, add a
new field `"eps_schedule": "decreasing"`. If not, leave the default
`"decreasing"` behavior implicit (Wave 33 audit says this is the
paper-aligned default; no breaking change for legacy users).

### 3.3 Test plan

Add 3 unit tests to `tests/test_algorithm/test_codimension_scheduler.py`
(or equivalent — locate via `grep -rn "CodimensionSheetScheduler" tests/`):

1. **Test 1 — schedule is monotone**: with `eps_direction="decreasing"`,
   `eps_per_round` is strictly decreasing in `round_idx` (except for
   the `u_r=0` boundary case which is fine).
2. **Test 2 — boundary**: at `round_idx = cycle_length - 1`,
   `eps_per_round <= eps_implicit * 1e-9` (the `max(..., 1e-9)` clamp
   prevents underflow to 0).
3. **Test 3 — legacy "constant" preserved**: with `eps_direction="constant"`,
   `eps_per_round == eps_implicit` for all `round_idx` (legacy behavior
   is byte-stable for users who set the constant flag explicitly).

### 3.4 Verification sweeps

After the code change + unit tests pass, run two verification sweeps:

1. **`twodim_fm` N=100 audit** at σ ∈ {0.0, 0.1, 0.5}: should move from
   +176-191% regression to TIE or framework_improves (-5 to -15%).
   CPU-only, ~10 minutes.
2. **`rectified_flow_cifar` N=200 audit** at matched NFE=50: should
   see FID drift improve by -1 to -3%. GPU, ~30 minutes.

The D.4 byte-stable regression vector must NOT change (`pytest tests/ -k "d4" -q` → 33/33 PASS).

---

## 4. Acceptance criteria

- [ ] `eps_implicit` constant plug replaced with per-round schedule in
  `adaptive_reflow/algorithm/scheduler/_core.py:sample` line 3103-3111
  (or equivalent location post-Wave 35 saturation plan).
- [ ] Unit tests pass (3 new tests added; existing tests unchanged).
- [ ] `pytest tests/ -k "d4" -q` → 33/33 PASS (byte-stable preserved).
- [ ] `twodim_fm` N=100 σ=0.0 framework_improves by ≥ 5% relative to
  baseline (currently +191% regression).
- [ ] `twodim_fm` N=100 σ=0.5 framework_improves by ≥ 5% relative to
  baseline (currently +176% regression).
- [ ] `rectified_flow_cifar` matched NFE=50 framework FID drift within
  ±5% of baseline (currently +24-31% regression — partial closure; the
  bulk of that fix comes from plan #1 `algo-improvement-paper-quantity-beta-calibration.md`).
- [ ] `mkdocs build --strict` → EXIT=0.
- [ ] Single atomic commit, no push (user-gated).

---

## 5. Risk

| Risk | Severity | Mitigation |
|---|---|---|
| **D.4 byte-stable regression vectors change** (the `config_hash()` may shift because the per-round `eps_per_round` differs from constant `eps_implicit`) | P1 | Keep the constant-plug code path as a legacy `"constant"` direction; verify `config_hash()` byte-stable; if not, add `eps_schedule` to `to_config()` and update D.4 vectors |
| **Twodim_fm regression worse, not better** (the schedule may over-correct the cosine ramp and produce smaller `n_cap` than the baseline) | P2 | Pre-flight check: run N=20 smoke before N=100; if smoke regresses, roll back and investigate the closed-form math |
| **CIFAR-10 NFE accounting drift** (the per-round `eps_per_round` changes `n_cap`, which changes `steps_per_round`, which may invalidate the matched-NFE contract) | P1 | Verify `BatchedRunnerConfig.total_nfe == sum(steps_per_round)` after the change; if not, pair this fix with plan #1's `ceil+carry` (B1) |
| **Wave 35 saturation plan FIX-1/2/3 already touches the same scheduler** (Wave 35 added `record_round_feedback` + `should_terminate_round` to the same file) | P2 | Read Wave 35 commits before applying; check for merge conflicts; if conflicts, escalate to user |
| **Untested on Kanzi/LineageFlow** (the per-round schedule may *worsen* the Kanzi +0.86 Å regression because `eps_per_round=0` at the last round may collapse the framework's contribution to zero) | P3 | Run a N=10 Kanzi smoke after the change; if the +0.86 Å regression worsens, document and defer Kanzi-specific tuning |

---

## 6. Effort estimate

| Phase | Effort | Wall-clock | GPU hours |
|---|---|---:|---:|
| Code change (10 LOC) + config plumbing (5 LOC) | 0.5 day | 4 hours | 0 |
| Unit tests (3 new) | 0.25 day | 2 hours | 0 |
| `twodim_fm` N=100 audit (CPU-only) | 0.1 day | 1 hour | 0 |
| `rectified_flow_cifar` N=200 audit (GPU) | 0.2 day | 1.5 hours | 1 |
| D.4 + mkdocs + commit | 0.1 day | 1 hour | 0 |
| **Total** | **~1.15 days** | **~10 hours** | **1 GPU-hour** |

**LOC budget:** ~15 LOC code + ~30 LOC tests = ~45 LOC total.

---

## 7. Follow-up

After this plan ships:

1. Pair with `algo-improvement-paper-quantity-beta-calibration.md`
   (rank #1, same commit or adjacent commit) to close the bulk of
   `twodim_fm` + `CIFAR-10` regression.
2. Re-run Wave 99.B Kanzi N=10 framework paper-metric to verify the
   per-round schedule does not worsen the +0.86 Å regression on
   Kanzi (which has its own adapter-layer gap; orthogonal fix path).
3. Update `docs/CONSOLIDATED_RESULTS.md` §6 + §6.1 with the new
   twodim_fm + CIFAR-10 numbers (additive).
4. Update `docs/paper-draft.md` §7 (Algorithm section) to reflect the
   per-round schedule as the paper-aligned default.

---

## 8. Cross-references

- `docs/audit/algorithm-gap-investigation.md` §1.2.1 + §1.2.2 (Wave 33 audit A1+A2)
- `docs/audit/saturation-improvement-plan.md` §1 (Wave 35 saturation plan — orthogonal fix via `should_terminate_round`)
- `docs/CONSOLIDATED_RESULTS.md` §6 + §6.1 (twodim_fm + CIFAR-10 baselines)
- `todo/algo-improvement-framework-vs-model-metrics-gap.md` (this wave's synthesis; rank #2)
- `todo/algo-improvement-paper-quantity-beta-calibration.md` (this wave's rank #1; pairs with this plan)
- `todo/completed/algo-improvement-rate-bound.md` (Wave 15 B: rate bound; orthogonal)

---

## 9. Wave 123 close-out (placeholder)

This plan is authored in Wave 123 but NOT executed. Status:
**Execution authorized; remaining work is experiment-gated.** To execute:

1. Read this plan end-to-end (already done if you're the executor).
2. Read Wave 35 saturation plan + Wave 33 audit to understand the
   current state of `CodimensionSheetScheduler`.
3. Apply the code change in a feature branch (NOT main) + run the
   unit tests + D.4 verify + the 2 verification sweeps.
4. Commit atomically; do NOT push (user-gated).
5. Author `docs/audit/waveN-phaseM-plan2-restart-policy.md` audit doc
   with the before/after numbers.
6. Update `todo/STATUS.md` + `docs/CONSOLIDATED_RESULTS.md` + `docs/paper-draft.md`
   (additive only).
7. Move this plan doc to `todo/completed/algo-improvement-restart-policy-collapse-fix.md`
   per the existing convention.
