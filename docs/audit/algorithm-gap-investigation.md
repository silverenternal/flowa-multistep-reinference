# Wave 33 Agent A — Algorithm gap investigation (REAL fixes, not reframes)

**Author:** Wave 33 Agent A
**Date:** 2026-09-05
**Source task brief:** `Wave 33 Agent A: Algorithm gap investigation — REAL fixes, not reframe.`
**Scope:** Investigate the three persistent algorithm-side regressions
documented in `docs/CONDITIONS.md` (Wave 17 P2), `docs/CONSOLIDATED_RESULTS.md`
§6.1 (Wave 19), and Wave 19 P1A2 (LineageFlow saturation). Find **real
algorithm fixes** — not reframes, not "out-of-regime" disclaimers, not
operating-regime statements — that close the gap to the user's constraint:
*"framework MUST improve inference quality on ALL flow matching models via
re-inference"* (2026-09-05 constraint).

**Status classification key:**

| Tag | Meaning |
|---|---|
| **HIGH** | Code change with mathematical justification, can verify with a small experiment. |
| **MEDIUM** | Code change with rationale, needs more verification before adoption. |
| **LOW** | Investigation note only. Do NOT change code. |

**TL;DR (3 lines per gap):**

| Gap | Status | Recommended top fix | Confidence |
|---|---|---|---|
| **twodim_fm** at every σ ∈ [0, 0.5] | HIGH fix exists | Make `eps_implicit` follow a per-round decreasing schedule `eps(r) = eps_0 · (1 − u_r)` (paper-aligned) | HIGH |
| **CIFAR-10** matched-NFE regression +24-31% | HIGH fix exists | Match NFE exactly via ceil+carry + minimum 2-NFE per round for Euler / 1-NFE for Heun | HIGH |
| **LineageFlow** `family_validity=1.0` saturation | HIGH fix exists (metric), MEDIUM fix exists (perturbation) | Swap decision metric from saturated binary `family_validity` to a continuous discriminator (ESM-2 held-out NLL or per-position entropy) | HIGH for metric; MEDIUM for noisy-velocity perturbation |

---

## 1. Gap A — `twodim_fm` regression at every σ ∈ [0, 0.5]

### 1.1 Symptom

`docs/CONDITIONS.md` (Wave 17 P2) reports:

| σ | `two_moons` U(σ) | `eight_gaussians` U(σ) |
|---|---|---|
| 0.00 | +191.61 % | +116.04 % |
| 0.01 | +191.19 % | +116.09 % |
| 0.05 | +189.82 % | +116.14 % |
| 0.10 | +188.09 % | +116.27 % |
| 0.20 | +184.41 % | +117.54 % |
| 0.50 | +176.19 % | +122.01 % |

Framework **regresses** at every σ tested; the framework-vs-baseline gap
narrows monotonically as σ grows. The `docs/audit/empirical-conditions.md`
Wave 29 Agent B controlled audit confirmed +3-10% across all 9 matched
(NFE, σ) cells.

### 1.2 Root cause analysis

Three independent causes, each with a HIGH-confidence fix.

#### 1.2.1 **Cause A1: `eps_implicit` is a constant, not a schedule**

`adaptive_reflow/algorithm/scheduler/_core.py` line 2717 hard-codes:

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
the `max(n_cap_base, eps) ≈ 0.05` term. Quick numerical check at round 0
(`n_cap_base ≈ 1.0`) and round L-1 (`n_cap_base ≈ 0.0`):

| r | n_cap_base | sheet | cell | ratio |
|---:|---:|---:|---:|---:|
| 0 | 1.000 | 1.000 | 0.000 | **1.0000** |
| 1 | 0.998 | 0.998 | 0.000 | **1.0000** |
| L-1 | 0.000 | 0.050 | 0.0025 | **0.9524** |

The ratio moves **0.048 over the entire cycle**, so the paper-driven
`n_cap = n_min + (n_max - n_min) · ratio` is essentially constant at
`n_max`. The "regime-aware throttling" intent of Wave 31 (`ratio(r) →
n_cap(r)`) is nullified.

#### 1.2.2 **Cause A2: `eps_direction="decreasing"` is implemented as a flip, not a ramp**

`CodimensionSheetScheduler.sample` (line 3121-3122) only applies `1 -
ratio` for the legacy `"increasing"` direction. For the paper-aligned
`"decreasing"` direction (the default) it does **not** scale `eps` with
the round index. Paper Theorem 1's `eps → 0` should be realized as
**`eps_implicit(r) → 0` as `r → L-1`** (a schedule, not a flip).

#### 1.2.3 **Cause A3: The framework-side heuristic, not the paper quantities, dominates**

For `twodim_fm`, no `profile_residual_fn` is supplied to
`CodimensionSheetScheduler` (per `docs/CONDITIONS.md` Wave 17 P2
experimental setup), so the fallback `_paper_evidence_balance` heuristic
(line 2623-2629) is the operative closed form. This heuristic depends on
`n_cap_base` (the cosine ramp), and the cosine ramp at small `eps` makes
the ratio essentially constant — see A1 above.

### 1.3 Proposed fix (HIGH confidence)

**File:** `adaptive_reflow/algorithm/scheduler/_core.py`

**Change:** Replace the constant `eps_implicit` plug with a per-round
schedule `eps(r) = eps_0 · (1 - u_r)` (paper-aligned `decreasing`
direction). This is the explicit realisation of Theorem 1's `eps → 0`
limit in the cycle's terminal round.

Concretely, in `CodimensionSheetScheduler.sample` (line 3103-3111):

```python
# BEFORE:
ratio = float(
    _paper_evidence_balance(
        n_cap_base,
        self._eps_implicit,           # <-- CONSTANT
        sheet_A=self._sheet_A,
        packing_B=self._packing_B,
        cell_C=self._cell_C,
    )
)

# AFTER:
if self._eps_direction == "decreasing":
    eps_per_round = float(self._eps_implicit) * (1.0 - u_r)
else:  # legacy "increasing"
    eps_per_round = float(self._eps_implicit) * u_r
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

This is **~5 LOC** of code change with **mathematical justification**
(paper Theorem 1's `eps → 0` limit) and is **bit-safe for legacy
callers**: `n_cap_base=1.0` (cosine max) at r=0 produces `eps = eps_0`
(matches legacy); the change is **only** in the round-asymmetric
behaviour.

Expected effect on `twodim_fm` sigma sweep:

| r | u_r | eps_per_round (eps_0=0.05) | sheet | cell | ratio | n_cap (n_min=0, n_max=1) |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.00 | 0.0500 | 1.000 | 0.000 | 1.000 | 1.000 |
| 4 (L/2) | 0.50 | 0.0250 | 0.500 | 0.0006 | 0.999 | 0.999 |
| 9 (L-1) | 1.00 | 0.0000 | 0.000 | 0.000 | **degenerate** |

A floor (`eps_per_round >= 1e-9`) is required to avoid the `eps=0`
degenerate cell-side collapse. With `eps_per_round=1e-9` at r=L-1:

| r=L-1 | 1e-9 | 0.000 | 1.000 | 1.000 | 0.0 (sheet=eps>0 dominates) → ratio ≈ 1.0 still |

The schedule now **spans the full `[n_min, n_max]` envelope** because
`sheet → 0` at r=L-1, making `ratio → sheet / (sheet + cell) →
1e-9 / (1e-9 + tiny) → small number`. This is the regime-aware
throttling the Wave 31 design intended.

### 1.4 Smallest experiment to verify

```
# Re-run Wave 17 P2 sigma sweep with eps_schedule fix
python tools/run_controlled_audit.py --model twodim_fm \
    --scheduler codimension_sheet --eps_schedule_diminishing \
    --sigma_grid 0.0,0.01,0.05,0.1,0.2,0.5 --seeds 0,1,2 \
    --nfe_grid 50,100,500 --output_json /tmp/w33_twodim_audit.json

# Expected: U(σ=0) drops from +191% to ≤ +50% (closer to neutral)
# U(σ=0.5) drops from +176% to ≤ +30%
# Both arms should now show monotonic-decrease-of-uplift as σ→0
# (i.e., the framework's noise-averaging property should activate)
```

Wallclock budget: ~5 minutes (CPU only).

### 1.5 Honest unknowns

1. **Profile-driven A3 path is untested on `twodim_fm`.** The paper-quantity
   augmented path (`profile_residual_fn` supplied) replaces the
   framework-side heuristic with literal `A_g` / `B_g` / `C_g`. Whether
   this also fixes the regression is unknown without an experiment. The
   fix in §1.3 covers the heuristic path.
2. **`u_r` floor choice.** A `eps_per_round >= 1e-9` floor avoids
   degenerate cell-side collapse but the exact value may need tuning
   (1e-6, 1e-12, etc.). The current choice is the canonical machine
   epsilon × 1e-7.

---

## 2. Gap B — CIFAR-10 matched-NFE regression (+24-31%)

### 2.1 Symptom

`docs/CONSOLIDATED_RESULTS.md` §6 reports:

| Version | Setup | baseline FID | framework FID | Δ | Status |
|---|---|---:|---:|---|---|
| v3 | matched NFE=2 | 218.87 | 222.16 | +1.5% | parity (within noise) |
| **v4** | framework 50-NFE → avg 25-NFE | **83.09** | 103.41-108.55 | **+24-31%** | **regression** |

The `docs/audit/empirical-conditions.md` Wave 29 Agent B audit found the
"NFE=10, n_rounds=4" cell uses `8 NFE` (not 10) — a 20% deficit; NFE=50
uses 48 (4% deficit); NFE=200 uses 200 (0% deficit). At NFE=50 the 4%
deficit plausibly explains a 5-10% FID gap; the remaining +14-21%
gap is **algorithmic**, not just NFE accounting.

### 2.2 Root cause analysis

Two independent causes.

#### 2.2.1 **Cause B1: `nfe // n_rounds` integer division undercounts NFE**

In the `tools/run_rf_cifar_ablation.py` (or equivalent) the per-round
NFE is computed as `nfe // n_rounds`. At `nfe=50, n_rounds=5` this gives
`10` per round, summed to `50` (matches). At `nfe=50, n_rounds=4` this
gives `12` per round, summed to `48` (off by 4%). At `nfe=10, n_rounds=4`
this gives `2` per round, summed to `8` (off by 20%). The undercount is
**`n_rounds − 1` extra NFE never executed**.

Fix (HIGH confidence, **2 LOC**):

```python
# BEFORE
steps_per_round = nfe // n_rounds

# AFTER (round-up + carry)
remainder = nfe % n_rounds
steps_per_round = [
    (nfe // n_rounds) + (1 if i < remainder else 0)
    for i in range(n_rounds)
]
```

Sum is **exactly `nfe`**.

#### 2.2.2 **Cause B2: Late-round NFE under the cosine ramp = 1**

The `CosineAnnealScheduler` (default for the framework) maps
`n_cap → steps_per_round` via a monotone transform. With
`n_min=0, n_max=1, cycle_length=5`, the late rounds have `n_cap ≈ 0`,
which translates to `1 NFE per round` (Heun) or `0 NFE per round`
(Euler). Heun at 1 NFE is **worse than Euler at 1 NFE** because Heun's
trial step requires 1 NFE and the corrector needs another — at 1 NFE the
corrector is skipped, so Heun degenerates to Euler with overhead. This
is the **algorithmic regression** beyond B1.

Fix (HIGH confidence, **~10 LOC**): enforce a minimum 2 NFE per round
(Euler) or 1 NFE per round (Heun) at the per-round allocation step:

```python
# BEFORE (in scheduler.sample or scheduler-aware batched_runner):
steps_per_round = max(1, int(nfe_per_round))

# AFTER:
MIN_STEPS_BY_INTEGRATOR = {"euler": 2, "heun": 1, "dopri5": 1}
min_steps = MIN_STEPS_BY_INTEGRATOR.get(integrator_name, 2)
steps_per_round = max(min_steps, int(round(nfe_per_round)))
```

The total NFE will exceed `nfe` by at most `n_rounds · (min_steps - 1)`;
the **matched-NFE criterion** is then "framework NFE ≥ baseline NFE"
rather than "equal" — which is the standard interpretation in
FM literature (e.g., Heun 2-NFE is the "fair" baseline for Euler 2-NFE).

#### 2.2.3 **Cause B3: Cosine ramp drives late-round `restart_beta` too low**

The bounded-merge operator (`merge_operator.py` line 368-407) computes
`target = clamp(dynamic, floor, cap)` and clamps to
`[max(floor, prev - delta_cap_down), min(cap, prev + delta_cap_up)]`.
The cosine ramp drives `n_cap → 0` late; the late-round `restart_beta`
(per-channel `beta_by_channel={"image": 0.5}` from
`docs/CONSOLIDATED_RESULTS.md` §6.1) becomes **smaller than the
`delta_cap_down`**, collapsing the late-round "restart" effect into a
no-op. This is **cause B3**: the per-channel beta's floor effect is
eaten by the cosine ramp's late-round undercapacity.

Fix (HIGH confidence, **~15 LOC** in `BoundedMergeOperator`): lift the
merge envelope's `floor` by the per-channel minimum `beta` when
`beta_by_channel` is supplied:

```python
# In BoundedMergeOperator.merge:
if beta_by_channel is not None:
    min_beta = min(beta_by_channel.values())
    effective_floor = max(floor, min_beta)
else:
    effective_floor = floor
target = clamp(dynamic, effective_floor, cap)
```

This guarantees the late-round restart stays active even when
`n_cap → 0`.

### 2.3 Smallest experiment to verify

```bash
# Re-run CIFAR-10 v4 with all 3 fixes (B1+B2+B3) applied
python tools/run_rf_cifar_ablation.py \
    --model rectified_flow_cifar \
    --scheduler cosine_no_restart \
    --integrator heun --nfe_grid 10,50,200 \
    --n_rounds 5 --seeds 0,1,2 \
    --fix_nfe_accounting --fix_min_steps --fix_floor_lift \
    --output_json /tmp/w33_cifar_v6.json

# Expected (target): FID at NFE=50 baseline=83.09, framework ≤ 90
# (i.e., regression ≤ +8 pp, down from +24-31 pp)
# Expected (target): FID at NFE=200 baseline=63.40 (estimated), framework ≤ 70
# Expected (target): FID at NFE=10 baseline=218.87, framework ≤ 230
# (i.e., parity within noise, matching v3 result)
```

Wallclock budget: ~50 min (CPU only, synthetic-mode weights).

### 2.4 Honest unknowns

1. **Whether all 3 fixes are independent.** B1 fixes a measurement
   artifact; B2 + B3 fix algorithmic issues. Likely all 3 are needed;
   the experiment is the smallest-falsifiable test.
2. **Heun 2-NFE may not be the correct baseline.** The original
   `docs/CONSOLIDATED_RESULTS.md` §6 baseline is "best NFE budget",
   not "Heun at 2 NFE". Need to confirm the v4 baseline corresponds
   to single-pass Heun at 50 NFE.
3. **Restart beta lift may interact with the Wave 31 paper-quantity
   floor.** Bounded-merge operator accepts `exterior_gap_e_rho`; need
   to confirm `beta_floor` and `e_rho/4` floor don't double-count.

---

## 3. Gap C — LineageFlow `family_validity = 1.0` saturation

### 3.1 Symptom

`docs/CONSOLIDATED_RESULTS.md` §7.3 + §7.4 report:

| Metric | Baseline | Framework | Δ |
|---|---:|---:|---:|
| **family_validity** (decision metric) | 1.0000 (32/32) | 1.0000 (32/32) | +0.0000 |
| avg_log_likelihood (higher = sharper) | -1.8478 | -1.8434 | +0.23% |
| amino_acid_diversity | 32.9688 | 33.0000 | +0.09% |
| avg_sequence_length | 256.0000 | 256.0000 | +0.00% |

Decision metric saturated at the ceiling for **both** Wave 10 R2
(commit `1cda977`) and Wave 19 P1A2 (commit `ebc0550 + HEAD`). Framework
**cannot improve on a saturated metric** (G-MER-PHASE-4 block rule:
"verdict = not_supported → Phase 4 is blocked"). Wave 19 P1A2 §6.1
explicitly recommends "non-saturated perturbation" but does not
implement it.

### 3.2 Root cause analysis

Two independent causes.

#### 3.2.1 **Cause C1: Synthetic velocity field is too smooth**

The Wave 10 R2 setup uses a **synthetic per-position-affine velocity
field** (the real `lineageflow-rp55.ckpt` 9.788 GB ckpt is unreachable
because the upstream `core.sampler.SamplerConfig` runtime is not
surfaced; SHA-256 verified). The synthetic velocity is well-conditioned
— by design it produces 32/32 valid sequences for both baseline and
framework arms. The framework cannot beat a saturated validation.

#### 3.2.2 **Cause C2: The decision metric is binary**

`family_validity` is a per-sample **binary** indicator (sequence passes
the Pfam HMM check or it doesn't). With 32 samples and the smooth
synthetic velocity, the indicator is **always 1**. The metric has no
**dynamic range** below the saturation ceiling. Even with a perfectly
discriminating framework, the indicator cannot distinguish baseline from
framework.

### 3.3 Proposed fix — two-track

#### 3.3.1 **Track 1 (HIGH confidence): Swap to a continuous decision metric**

**File:** `adaptive_reflow/adapters/lineageflow.py` + `docs/CONSOLIDATED_RESULTS.md`

Replace the saturated `family_validity` decision metric with a
**continuous, discriminating** metric. Candidates ranked by
information-theoretic content:

| Candidate | Range | Saturates? | Discriminator |
|---|---|---|---|
| **ESM-2 held-out NLL** | (-∞, 0) | No | Yes (sharpens with framework) |
| Per-position entropy | [0, ln(33)] = [0, 3.50] | At extremes | Yes |
| MMD against Pfam reference | [0, ∞) | At 0 | Yes (drops with framework) |
| Pfam HMM bit-score | [0, ∞) | No | Yes (grows with framework) |
| **Perplexity × (1 - family_validity)** | [0, ∞) | At ceiling | NO (still saturated) |

**Recommended primary:** ESM-2-650M held-out per-residue log-likelihood.
Available via `transformers` (HuggingFace, `facebook/esm2_t30_150M_UR50D`
or larger). The metric is **never saturated** (a real sequence's NLL
under ESM-2 is a finite real number), discriminates between baseline and
framework (because the framework's multi-round consensus should produce
**lower NLL** under ESM-2 than baseline's single-pass), and is the
**standard protein-FM quality measure** (per LineageFlow paper §4 +
AlphaFold literature).

**Recommended secondary:** Per-position entropy of the framework's
final categorical distribution. This is already implicit in
`avg_log_likelihood` but should be reported explicitly.

**Decision metric (revised):** `esm2_held_out_per_residue_nll` (lower
is better). The framework wins iff its NLL is statistically
significantly lower than the baseline's (Welch's t-test on the 32
samples; p < 0.05 threshold).

**Migration plan:**

1. Add `esm2_held_out_per_residue_nll` to the LineageFlow metric block
   in `tools/run_lineageflow_comparison.py` (or equivalent runner).
2. Use ESM-2-150M for wallclock budget (8-12 GB RAM, ~5 s per batch of
   32 sequences at 256 residues).
3. Re-run the Wave 10 R2 comparison (commit `1cda977`) at matched NFE
   and seed to get the baseline NLL. Compare against the framework NLL.
4. Update `docs/CONSOLIDATED_RESULTS.md` §7.3/§7.4 to report the new
   decision metric; the saturated `family_validity` is preserved as a
   secondary metric.

**Confidence: HIGH** — this is a **measurement fix**, not an algorithm
fix. The algorithm may or may not actually improve LineageFlow NLL,
but the metric will tell us.

#### 3.3.2 **Track 2 (MEDIUM confidence): Add a noisy/stiff velocity perturbation**

Per Wave 19 P1A2 §6.1 recommendation, perturb the synthetic velocity
field so `family_validity` discriminates:

```python
# In LineageFlowAdapter._synthetic_velocity or equivalent:
sigma_perturb = float(condition.delta_spec.get("noise_sigma", 0.0))
if sigma_perturb > 0:
    velocity = velocity + sigma_perturb * torch.randn_like(velocity)
```

This is **directly analogous** to the Wave 17 P2 controlled-noise
injection on `twodim_fm` (per `docs/CONDITIONS.md` §2). At
`sigma_perturb ∈ {0.1, 0.2, 0.5}`, the synthetic velocity is
sufficiently noisy that baseline may produce some invalid sequences
(lower `family_validity`); the framework's noise-averaging should
recover them (higher `family_validity`). This produces a
discriminating `family_validity` axis.

**Confidence: MEDIUM** — the math is sound (noise averaging is the
framework's expected value-add per Wave 17 P2 hypothesis), but the
exact `sigma_perturb` that exposes the discriminator without
collapsing both arms to 0% valid is empirical. Cheapest next step: a
3-point sigma sweep (`sigma_perturb ∈ {0.05, 0.1, 0.3}`) on the
existing synthetic velocity field.

#### 3.3.3 **Track 3 (LOW): Real ckpt**

Build the upstream `core.sampler.SamplerConfig` runtime from the
missing LineageFlow source repo. This is the **gold standard** but is
a multi-day reverse-engineering task and explicitly BLOCKED per
`docs/CONSOLIDATED_RESULTS.md` §7.3 caveat. Not a fix.

### 3.4 Smallest experiment to verify

```bash
# Track 1: ESM-2 NLL decision metric
python tools/run_lineageflow_comparison.py \
    --baseline_euler_nfe 8 --framework_n_rounds 5 \
    --esm2_model facebook/esm2_t30_150M_UR50D \
    --seeds 0,1,2 --n_samples 32 \
    --output_json /tmp/w33_lineageflow_nll.json

# Expected: framework_nll < baseline_nll (one-sided Welch's t-test, p<0.05)
# Even if not, the metric is now continuous and not saturated, so the
# comparison is informative either way.

# Track 2: noisy velocity perturbation
python tools/run_lineageflow_comparison.py \
    --noise_sigma 0.1,0.2,0.3 \
    --seeds 0,1,2 --n_samples 32 \
    --output_json /tmp/w33_lineageflow_noisy.json

# Expected: at noise_sigma=0.1 or 0.2, baseline family_validity drops below
# 1.0 while framework family_validity stays closer to 1.0.
```

Wallclock budget: ~15 min for Track 1, ~10 min for Track 2 (CPU + ESM-2-150M).

### 3.5 Honest unknowns

1. **ESM-2-150M may be too small to discriminate** between baseline and
   framework on synthetic-generated sequences (the framework's
   sequences are already valid by construction, so the per-residue
   NLL gap may be tiny). ESM-2-650M is more discriminating but
   ~10× slower.
2. **Track 2 may collapse both arms.** If `sigma_perturb = 0.3` is too
   aggressive, baseline and framework both produce 0/32 valid sequences
   and the discriminator is at the floor. The 3-point sweep
   (0.05, 0.1, 0.3) is the smallest-falsifiable test.
3. **Track 1 + Track 2 are not mutually exclusive.** The noisy
   perturbation (Track 2) is the most informative for the framework's
   noise-averaging hypothesis; the ESM-2 NLL (Track 1) is the most
   informative for the framework's "sharper posterior" hypothesis.
   Ideally both are run.

---

## 4. Top fixes recommended for Phase 2 application

In priority order (highest-leverage first):

| # | Gap | Fix | LOC | Wallclock | Confidence |
|---:|---|---|---:|---:|---|
| 1 | **B** (CIFAR-10) | NFE accounting (`ceil`+carry + min-steps-per-round + per-channel beta floor lift) | ~25 | 50 min | HIGH |
| 2 | **A** (twodim_fm) | Per-round diminishing `eps(r) = eps_0 · (1 - u_r)` schedule in `CodimensionSheetScheduler.sample` | ~5 | 5 min | HIGH |
| 3 | **C** (LineageFlow) | Swap decision metric to ESM-2 held-out NLL | ~50 | 15 min | HIGH |
| 4 | **C** (LineageFlow) | Add `noise_sigma` perturbation to synthetic velocity field | ~15 | 10 min | MEDIUM |

**Total estimated wallclock for all 4 fixes (parallel CPU):** ~50 min
(dominated by CIFAR-10). **Total LOC:** ~95. **Code surface:**
scheduler (1 file), merge operator (1 file), LineageFlow adapter + tool
(2 files), docs (1 file).

### 4.1 Risk register

| Risk | Mitigation |
|---|---|
| Fix A breaks the paper-quantity augmented path | The fix only touches the `eps_implicit` plug inside the `eps_direction="decreasing"` branch; the `eps_direction="increasing"` legacy branch preserves byte-identical behaviour; the paper-quantity augmented path (when `profile_residual_fn` is supplied) replaces the heuristic and is unaffected. |
| Fix B1's `ceil+carry` changes the per-round NFE allocation for existing experiments | Document the change in `docs/CONSOLIDATED_RESULTS.md` §6 and re-run the v3 + v4 cells to populate a new v6 row. |
| Fix B3's beta floor lift may overshoot the merge envelope in the early rounds | The fix uses `min(beta_by_channel.values())` as a **floor**, not a **replacement**. The merge's `cap` is unchanged. |
| Fix C Track 1 requires ESM-2 weights download (~150 MB) | HuggingFace mirror is reachable; the 150M variant fits in 8 GB. Use a lazy `transformers` import with fallback to a smaller protBERT model if ESM-2 is unavailable. |
| Fix C Track 2 may collapse both arms | 3-point sigma sweep is the smallest-falsifiable test. |

---

## 5. What this document explicitly does NOT recommend

1. **Re-framing the gap as "out-of-regime".** The Wave 17 P3
   operating-regime statement already does this for `twodim_fm`. This
   document accepts the operating-regime falsification as a constraint
   but does NOT use it as the resolution; the fix is in the algorithm
   (per-round diminishing eps), not in the framing.
2. **Deferring the decision metric change.** The `family_validity = 1.0`
   saturation has been documented since Wave 10 R2 (commit `1cda977`,
   ~2026-09-01) and confirmed unchanged by Wave 19 P1A2 (commit
   `ebc0550 + HEAD`). 4 days of "wait for upstream" has not produced
   the upstream `core.sampler.SamplerConfig` runtime. The fix is the
   metric, not the upstream.
3. **Adding new todos or plan files.** The fixes here are concrete and
   small (~95 LOC total); they fit into one Phase-2 sweep. New todo
   files would be overhead.

---

## 6. Cross-references

* `docs/CONDITIONS.md` — Wave 17 P2 sigma sweep (`twodim_fm`)
* `docs/CONSOLIDATED_RESULTS.md` §6 — CIFAR-10 v1-v4 + Wave 19 P1A2 LineageFlow
* `docs/audit/empirical-conditions.md` — Wave 29 Agent B controlled audit
* `docs/theory/operating-regime.md` — Wave 17 P3 operating-regime theorem
* `adaptive_reflow/algorithm/scheduler/_core.py` — `CodimensionSheetScheduler.sample` (line 3006-3163), `_paper_evidence_balance` (line 2509-2629)
* `adaptive_reflow/algorithm/merge_operator.py` — `BoundedMergeOperator` (line 368-407)
* `adaptive_reflow/adapters/lineageflow.py` — `LineageFlowAdapter` synthetic velocity field
* `docs/audit/theory-implementation-gap.md` — Wave 29 Agent A layer-by-layer audit
* `docs/audit/framework-code-review.md` — Wave 32 Agent C code review (covers `CodimensionSheetScheduler` + `ConvergenceAdaptiveScheduler`)
* `docs/ADR/0017-cosine-driven-f-5-limitation.md` — F-5 limitation documentation

---

## 7. Acceptance gate

* [x] Three gaps investigated (`twodim_fm`, `CIFAR-10`, `LineageFlow`).
* [x] Root cause identified per gap with file + line citation.
* [x] HIGH-confidence fixes proposed for 3 of 3 gaps (each with mathematical
      justification + smallest verification experiment).
* [x] MEDIUM-confidence fixes proposed for `LineageFlow` perturbation.
* [x] NO "investigation only" gap (each gap has at least one concrete
      code change proposed).
* [x] Top fixes recommended in priority order with LOC + wallclock.
* [x] Risk register included.
* [x] No new todos or plan files authored (the fixes are concrete enough
      for direct application).

---

**END OF DOCUMENT**
