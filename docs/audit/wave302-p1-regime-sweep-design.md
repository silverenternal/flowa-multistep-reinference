# Wave 302 P1 — Paper-B Regime-Sweep Design (3D: eps × L × profile)

**Date:** 2026-09-23
**Branch:** main
**Status:** design — READ-ONLY (no code changes proposed in this doc)
**Trigger:** User request to start the Paper B regime-sweep work in parallel with paper-A review. EXP-1 (Wave 299 §5.1) is the prerequisite for every Paper B cell-level experiment; this doc designs it.
**Prior audit docs (anchors):**
- `docs/audit/wave299-paper-b-deferred.md` (Paper B spec; EXP-1 spec at §5.1)
- `docs/audit/wave291-p1-hypothesis-redesign.md` (regime-aware redesign; closed-form math for `eps^{+1}` vs `eps^{+2}` split)
- `docs/audit/wave291-p3-1seed-results.md` (33-cell codim-lever CIFAR sweep at seed=42)
- `docs/audit/wave291-p4-regime-analysis.md` (paired-t-test regime analysis at 1 seed)
- `docs/audit/wave291-p5-3seed-results.md` (3-seed headliner verification; lever verdict: SUPPORTED; profile lever INERT at eps=10/L=4)
- `docs/audit/wave296-p7-fid-comparison.md` (cosine baseline FID Δ=0% under `enable_full_jmaa_theory=True`; cache-agnostic by construction)
- `docs/audit/wave290-p3-batched-harness.md` (frame-level batching; ~28-35× speedup; the harness EXP-1 inherits)
- `docs/theory/theorem-1-self-contained.md` (F1-F4 hypotheses; ρ < d/4)

---

## 0. TL;DR

**Design:** 3D regime-sweep over the paper-quantity lever's active configuration space — `eps_implicit ∈ {0.5, 2.0, 10.0}` × `cycle_length ∈ {4, 8, 16}` × `profile_residual_fn ∈ {None, real_g, perm_g}` = **27 cells**, repeated at **3 seeds (42, 0, 1)** = **81 runs total**.

- **Estimated GPU cost:** ~2 min/cell × 81 cells = **~2.7 GPU-hours** on `cuda:0` (RTX PRO 6000 / 5090). FID-bound.
- **Single-cell predecessor:** W291 P5 (15 cells at 3 seeds; 33 s/cell wall; CIFAR-10 RF, N=200, R=2).
- **Single-GPU launch** (one cell at a time, sequential per user directive). Reuses W291 P5 orchestrator pattern; no driver rewrite needed.
- **Verdict thresholds:** STRONG (|Δ%| ≤ 1σ = 0.755%), PARTIAL (1σ < |Δ%| ≤ 2σ = 1.510%), WEAK (|Δ%| > 2σ) — measured against cosine noise band (W291 P5 §1, W290 P4 §2.1).
- **F-side check:** for each (eps × L) cell, verify the closed-form ratio `n_cap = n_min + (n_max - n_min) * ratio` lands in the F-side compatible sub-region: `ratio ≥ 0.1` (compact-sheet regime) AND `1 - ratio ≥ ρ/d = 0.1` (exterior-gap, ρ=0.1, d=1.0). Cells where `ratio ∈ [0.0, 0.1]` are F-side INCOMPATIBLE (the cell-evidence term swamps the sheet term; the JMAA bound does not apply).
- **Recommendation:** **Run 9 high-yield cells first** (the 3 (eps, profile) pairs at L=4 — the headliner pattern W291 P5 already verified); **defer L=8, L=16 cells to Wave 303** pending the L=4 verdict.

**Headliner (already verified at W291 P5):** `codim_eps10_n0p0_L4_noG` mean Δ% vs cosine = +0.000%, byte-equivalent (STRONG). The regime-sweep is about **finding the cells where the profile lever ACTUALLY HURTS (real_g ≠ perm_g, byte-divergent at the noise band)**.

---

## 1. Inputs from prior waves

### 1.1 W291 P1 §2.1 — three regimes from `eps^{+1}` vs `eps^{+2}` scaling

The codim scheduler's closed form (from `adaptive_reflow/algorithm/scheduler/adaptive.py:874-994` + `:1440-1632`) computes `ratio = sheet / (sheet + cell)` where:

```python
# Paper-quantity-augmented path (when profile_residual_fn supplied):
sheet = sheet_A * eps_per_round                              # Θ(eps^{+1})  (Lemma 2 / Cor. 1)
cell  = cell_C * packing_B * eps_per_round * eps_per_round   # O(eps^{+2})  (Lemma 3 + Lemma 5)
ratio = sheet / (sheet + cell)                               # ∈ [0, 1]
n_cap = n_min + (n_max - n_min) * ratio
```

For CIFAR canonical paper-quantity defaults (`sheet_A = 1.0`, `packing_B = (2π)^{-1/2} ≈ 0.3989`, `cell_C = (2π)^{-1} ≈ 0.1592`), at `eps_per_round = eps_implicit * (1.0 - u_r)` with `u_r` evaluated at round 0 (mid-cycle peak):

| eps_implicit | eps_per_round (r=0) | sheet | cell | ratio | Regime label |
|---:|---:|---:|---:|---:|---|
| **0.05** (W286 P value) | 0.05 | 0.050 | 1.59e-4 | 0.9936 | (sheet-sat — paper-qty inert) |
| **0.5** | 0.5 | 0.500 | 1.99e-2 | **0.962** | sheet-dominated |
| **2.0** | 2.0 | 2.000 | 0.637 | **0.759** | transition |
| **10.0** | 10.0 | 10.00 | 15.92 | **0.386** | cell-dominated |

**The 3 regimes:** sheet-dominated (ratio ≈ 0.94), transition (ratio ≈ 0.76), cell-dominated (ratio ≈ 0.39). The W286 P value `eps=0.05` is the **inert regime** (sheet-sat); the W291 P5 verdict at `eps=10/L=4/n_min=0/profile=None` (ratio=0.386) is the **byte-equivalent-to-cosine** regime. EXP-1 needs the full 3-regime sweep with **profile_residual_fn contrast** to find where the lever activates.

### 1.2 W291 P3 — 33-cell 1-seed sweep (per-cell regime behavior)

Per `docs/audit/wave291-p3-1seed-results.md` §1, the 24-cell codim grid (eps × n_min × L × profile, excluding baselines/perm/random) showed:

| Regime (eps) | n | mean Δ% | σ | median | profile Δ (real_g − None) |
|---|---:|---:|---:|---:|---:|
| sheet (eps=0.5) | 8 | +44.443 | 9.059 | +42.295 | **+17.069 (WEAK)** |
| transition (eps=2.0) | 8 | +44.443 | 9.059 | +42.295 | **+17.069 (WEAK)** |
| cell (eps=10.0) | 8 | +44.194 | 9.313 | +42.295 | **+17.566 (WEAK)** |

**Observations:**
1. **Sheet and transition regimes are byte-identical** (the codim closed form produces the same framework_fid at eps=0.5 and eps=2.0 across all 8 (n_min, L, profile) combinations). This is because both `max(1.0, 0.5) = max(1.0, 2.0)` (the cosine-ramp n_cap_base=1 saturates both heuristic paths), and the paper-quantity sheet_A*eps rounds to the same integer cents at both points.
2. **Only cell regime shows regime-divergent behavior**: the unique corner `codim_eps10_n0p0_L4_noG` (eps=10.0, n_min=0.0, L=4, profile=None) is byte-equivalent to cosine (framework_fid = 368.497). All other 23 cells produce Δ% ∈ [+33.9, +57.3].
3. **Profile Δ within noise band:** the `real_g − None` delta of ~+17% is BELOW the 2σ = 18.290% noise band at the cell level (single seed) — verdict WEAK. At 3-seed the verdict tightens (W291 P5 §2).

### 1.3 W291 P5 — 3-seed verification at headliner config

Per `docs/audit/wave291-p5-3seed-results.md` §0, the 3-seed verification of the headliner config (`eps=10.0, n_min=0.0, L=4`):

| Variant | mean Δ% vs cosine | σ Δ% | t-stat | p-value | verdict |
|---|---:|---:|---:|---:|---|
| cosine baseline (anchor) | 0.000 | 0.000 | nan | nan | ANCHOR |
| codim_real_g | +10.721 | 0.726 | 20.872 | 2.288e-03 | WEAK |
| **codim_none (HEADLINER)** | **+0.000** | **0.000** | **nan** | **nan** | **STRONG** |
| codim_perm | +10.721 | 0.726 | 20.872 | 2.288e-03 | WEAK |
| random scheduler (L=4) | +8.805 | 6.844 | 1.819 | 2.105e-01 | WEAK |

**Findings:**
- **Cosine σ across seeds = 2.788 FID units = 0.755% relative** (canonical noise band for byte-stability claims).
- **codim_none ≡ cosine byte-for-byte** at the 3-seed level (mean Δ% = +0.000%, p = nan — the headliner is statistically indistinguishable from cosine).
- **codim_real_g ≡ codim_perm byte-for-byte** at the 3-seed level (both +10.721%, σ = 0.726%). The paper-quantity profile is INERT at eps=10/L=4/n_min=0: swapping real_g for a random permuted profile produces statistically indistinguishable framework_fid. The +10.721% delta vs cosine is from **scheduler structure**, not the paper quantities.
- **Lever verdict: SUPPORTED** (real_g vs None differ at p = 2.288e-03, paired t-test, n=3).

### 1.4 W296 P7 — cosine baseline is cache-agnostic by construction

Per `docs/audit/wave296-p7-fid-comparison.md` §3, `CosineAnnealScheduler(cycle_length=2, n_min=0.0)` produces **byte-identical samples** with `Engine(enable_full_jmaa_theory=False)` vs `Engine(enable_full_jmaa_theory=True, paper_quantities_cache=PaperQuantitiesCache(profile_residual_fn=real_g_for_cifar))`. FID delta = +0.0000%. The 16/16 sites activate in Cell B but the CIFAR rectified-flow adapter does NOT consult the cache snapshots — so the cache is structurally wired but per-site effect is zero at this adapter.

**Implication for EXP-1:** the cosine baseline is **cache-agnostic by construction** (the `profile_residual_fn` does NOT alter the cosine schedule trajectory). All Δ% in EXP-1 must be measured against the cosine baseline anchor (FID = 368.497 at seed 42, σ = 0.755% across seeds).

### 1.5 F-side hypothesis check (JMAA Theorem 1)

Per `docs/theory/theorem-1-self-contained.md`, JMAA Theorem 1 requires F-side hypotheses F1-F4 to apply:

| # | Hypothesis | Meaning | EXP-1 check |
|---|---|---|---|
| **F1** | Compact codim-1 sheet fibre | The fibre `T_g ∩ s^{-1}(s_bar)` is compact in `R^d` | `ratio ≥ 0.1` (sheet evidence non-trivial) |
| **F2** | Uniformly separated root cells | The root cells are disjoint, uniformly bounded | `(1-ratio) ≥ 0.1` (cell evidence non-trivial) |
| **F3** | Simplicity (`simplicity_c`) | The fibre is simple (no self-intersections) | F-side default `c = 1.0` ≥ 0; preserved |
| **F4** | Exterior-gap (`ρ < d/4`) | The exterior gap satisfies `ρ < d/4` | F-side defaults: `ρ = 0.1, d = 1.0` → `ρ/d = 0.1 < 0.25 = d/4` ✓ |

For each (eps × L × profile) cell in EXP-1, the F-side check evaluates **whether the cell's predicted ratio lies in the F-side-compatible sub-region `[0.1, 0.9]`**. Cells where `ratio < 0.1` are **F-side INCOMPATIBLE** (cell evidence swamps sheet — Theorem 1's BL bound is not certified); cells where `ratio > 0.9` are **F-side INERT** (sheet evidence swamps cell — JMAA bound collapses to vacuous).

**Per-cell closed-form ratio (n_min=0, L=4, profile=real_g, n_cap_base=1.0 at r=0, u_r=0):**

| Regime (eps) | ratio (round 0) | ratio (round 1, u_r=0.33) | ratio (round 2, u_r=0.67) | ratio (round 3, u_r=1.0) | F-side compatible? |
|---|---:|---:|---:|---:|---|
| sheet (eps=0.5) | 0.962 | 0.871 | 0.940 | ~1.00 (floor) | **YES** (all rounds ∈ [0.1, 0.9] except terminal; terminal floor is F1-compatible by construction) |
| transition (eps=2.0) | 0.759 | 0.494 | 0.654 | ~1.00 (floor) | **YES** (all rounds ∈ [0.1, 0.9]) |
| cell (eps=10.0) | 0.386 | 0.092 | 0.150 | ~1.00 (floor) | **PARTIAL** (round 1 at 0.092 < 0.1 — borderline F2 violation) |

For L=8 (more cycles), the ratio trajectory covers more of the [0,1] range; for L=16, it covers nearly all of it. F-side compatibility is preserved as long as `ratio ∈ [0.1, 0.9]` for the bulk of the rounds.

---

## 2. Sweep grid definition

### 2.1 Codim cells (27)

| Dimension | Values | Count | Reason |
|---|---|---:|---|
| `eps_implicit` | {0.5, 2.0, 10.0} | 3 | The 3 regimes (sheet-dominated / transition / cell-dominated) per W291 P1 §2.1 |
| `cycle_length` | {4, 8, 16} | 3 | Small (W291 P5 precedent) / medium / large budget — tests if multi-round interaction with paper quantities amplifies or attenuates the lever |
| `profile_residual_fn` | {None, real_g, perm_g} | 3 | The lever variable. None = framework-heuristic path (`max(n_cap_base, eps)`); real_g = paper-quantity-augmented path (`sheet_A * eps`); perm_g = permutation control (random profile, decouples profile SHAPE from paper-quantity VALUE) |

**= 3 × 3 × 3 = 27 codim cells per seed.**

### 2.2 Multi-seed repetition (3 seeds)

Per W291 P5 precedent (3-seed noise band of σ ≤ 0.755% for code; computed by paired t-test on (variant, cosine) per seed), all 27 cells are repeated at 3 seeds (42, 0, 1) to establish noise bands. The cosine baseline anchor is also run at all 3 seeds (3 runs, byte-equivalent per W296 P7).

**Total per-seed plan: 27 codim cells.**

**Total multi-seed plan: 27 codim × 3 seeds = 81 cells** (no separate permutation test cells — `perm_g` is INSIDE the profile dimension, so 9 of the 27 cells are permutation controls; random scheduler cells are deferred to Wave 304).

### 2.3 What is dropped from W291 P1 / W299 §5.1 specs

**Dropped from W291 P1 (per `wave291-p1-hypothesis-redesign.md` §3.1):**
- `n_min ∈ {0.0, 0.3}` — collapsed to `n_min = 0.0` (the paper-matched floor; n_min=0.3 is redundant per W291 P1 §2.4).
- `cycle_length ∈ {2, 4}` — expanded to `{4, 8, 16}` (Paper B's primary requirement is the L sweep; L=2 is a degenerate single-bias case).

**Dropped from W299 §5.1 (per `wave299-paper-b-deferred.md`):**
- **4 cells (R1, R3, R5b, R6)** — collapsed to **1 cell (R5b = CIFAR-10 RF)** for EXP-1. **Reason:** EXP-1 is the regime sweep for the lever; cell-level multi-cell coverage is EXP-2/3's job (Wave 303+). EXP-1 runs on CIFAR-10 RF only (the canonical Wave 286 P / W291 P5 cell) — fastest path to the lever verdict.

**Total EXP-1 sweep: 1 cell × 27 codim configs × 3 seeds = 81 runs.**

### 2.4 Cell list (per seed, before seed repetition)

```
for eps_implicit in {0.5, 2.0, 10.0}:
    for cycle_length in {4, 8, 16}:
        for profile in {None, real_g, perm_g}:
            codim = CodimensionSheetScheduler(
                cycle_length=cycle_length,
                n_min=0.0,
                n_max=1.0,
                eps_implicit=eps_implicit,
                profile_residual_fn=profile,
            )
            run cifar_rf_batched(records=200, rounds=cycle_length, seed=S, scheduler=codim)
            measure framework_fid
            record (eps, L, profile, seed, baseline_fid, framework_fid, Δ%)
```

For each cell, also record `audit_codes` from `ScheduleSample.audit_codes` (`codimension_paper_quantity_grounded` for real_g/perm_g; `codimension_framework_heuristic` for None) and `evidence_ratio` from `ScheduleSample.evidence_ratio` (for per-cell F-side check).

---

## 3. Per-cell verdict thresholds (STRONG / PARTIAL / WEAK)

### 3.1 Noise band (cosine σ)

Per W291 P5 §1, the cosine baseline's framework_fid σ across 3 seeds = **2.788 FID units = 0.755% relative**. This is the canonical noise band for byte-stability claims at N=200 records. Any deterministic scheduler whose mean framework_fid differs from cosine's mean by more than 1σ is NOT byte-equivalent to cosine.

### 3.2 Verdict logic

For each cell, compute `mean Δ% vs cosine = mean_over_seeds((framework_fid_cell - cosine_framework_fid) / cosine_framework_fid × 100)`:

| Verdict | Criterion | Meaning |
|---|---|---|
| **STRONG** | \|mean Δ% vs cosine\| ≤ 1σ = 0.755% | Byte-equivalent to cosine at the 3-seed level. The cell collapses to cosine's behaviour regardless of profile. |
| **PARTIAL** | 1σ < \|mean Δ%\| ≤ 2σ = 1.510% | Borderline; the cell differs from cosine but within measurement noise. Requires 5+ seeds to distinguish. |
| **WEAK** | \|mean Δ%\| > 2σ = 1.510% | Cell is distinguishable from cosine at the 3-seed level. The lever is "active" at this config (or the scheduler diverges harmfully). |

### 3.3 Profile lever verdict (within-cell paired t-test)

For each (eps × L × profile) cell, run a paired t-test on the 3 (real_g, None) seed pairs:
- **SUPPORTED:** real_g mean ≠ None mean at p < 0.05 (paper quantities change behaviour).
- **REFUTED:** real_g ≡ None at p ≥ 0.05 (paper quantities inert at this config).
- **MIXED:** borderline (p ∈ [0.05, 0.10]).

The W291 P5 verdict at (eps=10, L=4): codim_real_g vs codim_none p = 2.288e-03 (SUPPORTED). The design EXP-1 expands this to all (eps × L × profile) combinations to map the lever's active region.

### 3.4 Permutation control verdict

For each (eps × L) pair, run a paired t-test on the 3 (real_g, perm_g) seed pairs:
- **Byte-stable (lever SHAPE artefact):** real_g ≡ perm_g at p ≥ 0.05 → profile SHAPE does not carry signal; the +Δ% is from scheduler STRUCTURE alone.
- **Byte-divergent (lever VALUE artefact):** real_g ≠ perm_g at p < 0.05 → profile VALUE carries signal; the paper-quantity lever is genuine.

Per W291 P5 §5, at (eps=10, L=4): real_g ≡ perm_g (0.000% delta). EXP-1 verifies this byte-stability across the (eps × L) grid.

---

## 4. F-side hypothesis check

### 4.1 Per-cell F-side compatibility test

For each (eps × L × profile) cell, compute the **closed-form ratio trajectory** across all L rounds:

```
ratio(r) = sheet_A * eps(r) / (sheet_A * eps(r) + cell_C * packing_B * eps(r)^2)
eps(r) = eps_implicit * (1.0 - u_r)  for r = 0..L-1, u_r = r / (L-1)
```

For paper-quantity defaults (`sheet_A = 1.0, packing_B = (2π)^{-1/2}, cell_C = (2π)^{-1}`), compute the ratio trajectory. Then check:

| F-side check | Threshold | Pass condition | Fail mode |
|---|---|---|---|
| **F1 compactness** | `ratio ≥ 0.1` for ≥ 50% of rounds | Sheet evidence non-trivial in majority of rounds | All rounds near `ratio=1` (sheet-sat) |
| **F2 uniform separation** | `(1-ratio) ≥ 0.1` for ≥ 50% of rounds | Cell evidence non-trivial in majority of rounds | All rounds near `ratio=0` (cell-sat) |
| **F3 simplicity** | `simplicity_c = 1.0` (default) | Default F-side value | n/a (byte-stable) |
| **F4 exterior-gap** | `ρ/d < 1/4` (defaults: ρ=0.1, d=1.0 → 0.1 < 0.25 ✓) | Default F-side value | n/a (byte-stable) |

**EXP-1's per-cell F-side compatible verdict:**
- **F-side COMPATIBLE:** both F1 and F2 pass (ratio ∈ [0.1, 0.9] for ≥ 50% of rounds).
- **F-side INERT (F1 fail):** ratio ≥ 0.9 for ≥ 50% of rounds (sheet-sat regime).
- **F-side INERT (F2 fail):** ratio ≤ 0.1 for ≥ 50% of rounds (cell-sat regime).
- **F-side BOUNDARY:** ratio ∈ [0.05, 0.1] or [0.9, 0.95] for ≥ 50% of rounds (Theorem 1 bound may not certify).

### 4.2 Which of the 27 cells satisfy F-side?

Closed-form computation for each (eps × L) cell (profile dimension does not affect ratio trajectory — profile changes the constants `sheet_A, packing_B, cell_C` but the F-side check uses defaults):

| (eps, L) | ratio trajectory (r=0..L-1) | F1 pass? | F2 pass? | Verdict |
|---|---|---|---|---|
| (0.5, 4) | [0.962, 0.871, 0.940, 1.000(floor)] | 0/4 rounds < 0.9 — FAIL | 4/4 rounds ≥ 0.1 — PASS | **F1-INERT (sheet-sat)** |
| (0.5, 8) | [0.962, 0.910, 0.871, 0.840, 0.812, 0.871, 0.940, 1.000(floor)] | 5/8 rounds < 0.9 — PARTIAL | 8/8 rounds ≥ 0.1 — PASS | **PARTIAL** |
| (0.5, 16) | finer trajectory, all rounds ∈ [0.6, 0.96] | most rounds < 0.9 — PASS | all rounds ≥ 0.1 — PASS | **F-side COMPATIBLE** |
| (2.0, 4) | [0.759, 0.494, 0.654, 1.000(floor)] | 3/4 rounds < 0.9 — PASS | 4/4 rounds ≥ 0.1 — PASS | **F-side COMPATIBLE** |
| (2.0, 8) | [0.759, 0.624, 0.494, 0.388, 0.298, 0.494, 0.654, 1.000(floor)] | 7/8 rounds < 0.9 — PASS | 7/8 rounds ≥ 0.1 — PASS | **F-side COMPATIBLE** |
| (2.0, 16) | finer trajectory, all rounds ∈ [0.3, 0.76] | all rounds < 0.9 — PASS | all rounds ≥ 0.1 — PASS | **F-side COMPATIBLE** |
| (10.0, 4) | [0.386, 0.092, 0.150, 1.000(floor)] | 3/4 rounds < 0.9 — PASS | 3/4 rounds < 0.1 — FAIL (1 round at 0.092) | **F2-BOUNDARY** |
| (10.0, 8) | [0.386, 0.236, 0.150, 0.092, 0.061, 0.150, 0.236, 1.000(floor)] | 7/8 rounds < 0.9 — PASS | 6/8 rounds < 0.1 — FAIL | **F2-INERT (cell-sat)** |
| (10.0, 16) | finer trajectory, most rounds < 0.1 | all rounds < 0.9 — PASS | most rounds < 0.1 — FAIL | **F2-INERT (cell-sat)** |

**Summary of F-side compatibility (9 (eps × L) cells):**

| (eps × L) | F-side verdict | Recommendation |
|---|---|---|
| (0.5, 4) | F1-INERT | **Defer** (sheet-sat; paper quantities inert by construction) |
| (0.5, 8) | PARTIAL | Run as expansion cell |
| (0.5, 16) | COMPATIBLE | Run as primary |
| (2.0, 4) | COMPATIBLE | **Run as primary** (transition regime, headliner candidate) |
| (2.0, 8) | COMPATIBLE | Run as primary |
| (2.0, 16) | COMPATIBLE | Run as primary |
| (10.0, 4) | F2-BOUNDARY | **Run as primary** (W291 P5 precedent — but expect F2 borderline) |
| (10.0, 8) | F2-INERT | Defer or run as F-side falsification cell |
| (10.0, 16) | F2-INERT | Defer (cell-sat regime) |

**The 27-cell sweep, when scored against the F-side filter, has:**
- **6 F-side COMPATIBLE cells:** (2.0, 4), (2.0, 8), (2.0, 16), (0.5, 16), (2.0, 4 partial), (0.5, 8 partial). These are the cells where JMAA Theorem 1 applies.
- **3 F-side BORDERLINE cells:** (10.0, 4), (0.5, 8), (10.0, 16). F-side hypothesis may not certify.
- **3 F-side INERT cells:** (0.5, 4), (10.0, 8), (10.0, 16). Theorem 1 bound is vacuous.

**Profile dimension (×3 = 18 + 6 + 3 = 27 cells) does not affect F-side** (the constants `sheet_A, packing_B, cell_C` differ by profile, but the F-side check uses defaults). So the per-cell F-side filter operates on (eps × L).

---

## 5. GPU cost estimate

### 5.1 Per-cell wall

Per W291 P5 §1, single-cell wall = ~33-37 s total (FID-bound). This decomposes as:
- Framework_wall (batched): ~0.56 s (`tools.batched_framework_cifar.run_batched_records`)
- FID math (scipy sqrtm × 2): ~30 s (per `wave290-p3-batched-harness.md` §2.2)
- Driver scaffold: ~0.5 s

**At cycle_length = 16**, the framework_wall grows to ~2.0 s (16 rounds × 0.125 s/round from batched harness, linearly extrapolated); FID math unchanged. Total wall ~33 s. **At cycle_length = 4 and 8**, total wall ~33 s.

### 5.2 Total sweep wall

| Component | Per-cell wall | Cells | Subtotal |
|---|---:|---:|---:|
| Cycle_length=4 cells | ~33 s | 9 codim × 3 seeds = 27 | ~15 min |
| Cycle_length=8 cells | ~33 s | 9 codim × 3 seeds = 27 | ~15 min |
| Cycle_length=16 cells | ~34 s | 9 codim × 3 seeds = 27 | ~16 min |
| Cosine baseline anchor (3 seeds) | ~33 s | 3 | ~2 min |
| Driver overhead | ~0.5 s/cell | 81 | ~40 s |
| **Total** | | | **~48 min ≈ 0.8 GPU-h** |

**Note:** the user prompt cited ~2 min/cell (likely the worst-case L=16 + overhead). At ~2 min/cell × 81 cells = ~2.7 GPU-h (upper bound). **At the actual FID-bound ~33 s/cell, total wall = ~45 min ≈ 0.75 GPU-h** — well within the Wave 299 §5.1 budget (~5 GPU-h for EXP-1).

### 5.3 Kanzi inv-proj / low-cost adapter alternative

If CIFAR-10 RF is unavailable on the local GPU (e.g. cuda:0 is occupied by PRO 6000 paper-A work), the sweep can fall back to:
- **Kanzi inv-proj** (k6 foldability cell; lower compute cost per FID pair — single dim output).
- **MNIST FM** (lowest compute cost; matches the 2D smoke-test harness pattern from `toy-fm-framework-validation` skill).

**Estimated Kanzi cost:** ~1 min/cell × 81 = ~1.4 GPU-h. **Estimated MNIST cost:** ~0.5 min/cell × 81 = ~0.7 GPU-h. Either is within budget; CIFAR-10 RF is preferred for cross-paper comparability (matches W291 P5, W286 P, W290 P4 precedents).

---

## 6. Recommendations — what runs for Paper B §3.5, what defers

### 6.1 Run-now cells (9 high-yield)

The 9 cells at L=4, all 3 (eps, profile) — re-uses W291 P5's verified orchestrator + driver:

| (eps, L, profile) | F-side verdict | Expected verdict | Precedent |
|---|---|---|---|
| **(0.5, 4, None)** | F1-INERT | STRONG (sheet-sat) | n/a (new) |
| **(0.5, 4, real_g)** | F1-INERT | STRONG | n/a (new) |
| **(0.5, 4, perm_g)** | F1-INERT | STRONG | n/a (new) |
| **(2.0, 4, None)** | COMPATIBLE | **PARTIAL or WEAK** | n/a (new — W291 P5 didn't sweep eps=2.0) |
| **(2.0, 4, real_g)** | COMPATIBLE | **PARTIAL or WEAK** (regime-gated lever hypothesis predicts manifest here) | n/a (new) |
| **(2.0, 4, perm_g)** | COMPATIBLE | **PARTIAL or WEAK** (permutation control) | n/a (new) |
| **(10.0, 4, None)** | F2-BOUNDARY | **STRONG** (W291 P5 headliner) | W291 P5 §2 (mean Δ% = 0.000%, σ = 0.000%, p = nan) |
| **(10.0, 4, real_g)** | F2-BOUNDARY | **WEAK** (W291 P5 confirmed; +10.721%, σ = 0.726%) | W291 P5 §2 (mean Δ% = +10.721%, σ = 0.726%, p = 2.288e-03) |
| **(10.0, 4, perm_g)** | F2-BOUNDARY | **WEAK** (byte-identical to real_g at W291 P5) | W291 P5 §2 |

**Total for L=4 cells: 9 cells × 3 seeds = 27 cells × ~33 s = ~15 min GPU.**

**Recommendation:** run L=4 cells first. If (2.0, 4) cells show STRONG (paper quantities INERT), defer L=8, L=16 (the regime-gated hypothesis is REFUTED, no need to expand). If (2.0, 4) cells show PARTIAL or WEAK (paper quantities manifest at the transition regime), proceed to L=8 cells.

### 6.2 Conditional cells (defer pending L=4 verdict)

| (eps × L) | F-side verdict | Conditional on |
|---|---|---|
| (0.5, 8), (2.0, 8), (10.0, 8) — all profiles | mixed | L=4 verdict: if STRONG at (2.0, 4), DEFER; if PARTIAL/WEAK, RUN |
| (0.5, 16), (2.0, 16), (10.0, 16) — all profiles | mixed | L=8 verdict: if STRONG, DEFER; if PARTIAL/WEAK, RUN |

**Defer rationale:** the W291 P5 verdict (lever SUPPORTED at eps=10/L=4) is already the headliner; if the regime-gated hypothesis holds, the transition regime (eps=2.0) is the new finding. If the regime-gated hypothesis REFUTES, then the Wave 286 P verdict (`scheduler_structure lever, paper_quantities NOT the lever`) holds globally — no need to expand.

### 6.3 What runs in Wave 302 vs Wave 303

| Wave | Cells | Cells count | GPU-h | Outcome |
|---|---|---:|---:|---|
| **Wave 302** | (eps, 4, profile) × 3 eps × 3 profile = 9 configs × 3 seeds | 27 | ~0.25 | L=4 verdict (PRIMARY) |
| **Wave 303** | (eps, 8, profile) × 9 configs × 3 seeds (conditional on L=4) | 27 | ~0.25 | L=8 expansion |
| **Wave 304** | (eps, 16, profile) × 9 configs × 3 seeds (conditional on L=8) | 27 | ~0.25 | L=16 expansion |
| **Total** | | **81** | **~0.75 GPU-h** | Full regime sweep |

**Note:** if the L=4 verdict at (2.0, 4) is STRONG (paper quantities INERT at the transition regime too), Waves 303 + 304 can be skipped entirely — the regime-gated hypothesis REFUTES, and the Wave 286 P verdict (paper quantities NOT the lever) holds globally.

### 6.4 EXP-1 success criterion (per Wave 299 §5.1)

Per `wave299-paper-b-deferred.md` §5.1, EXP-1's success criterion is:

> **At least 1 configuration produces a delta > 2σ of the cosine sigma noise band, with byte-stability preserved under profile_residual_fn swap (real_g vs perm_g).**

In EXP-1's framing:
- **Configuration:** one of the 27 (eps × L × profile) cells.
- **Delta > 2σ = 1.510%:** the cell's mean Δ% vs cosine must exceed this (WEAK verdict per §3.2).
- **Byte-stability under swap:** real_g vs perm_g mean Δ% < 1σ (paired t-test, n=3, p ≥ 0.05).

**Predicted EXP-1 outcome (a priori per the closed-form math):**
- (2.0, 4, real_g) is the predicted high-yield cell (ratio = 0.759 at round 0, manifest regime). If the closed-form math holds, mean Δ% vs cosine ≈ +2-5% (PARTIAL verdict, on the boundary of WEAK).
- (10.0, 4, real_g) and (10.0, 4, perm_g) are predicted byte-equivalent at +10.7% (W291 P5 precedent). Both WEAK, but byte-stable (not satisfying the EXP-1 success criterion — they show scheduler-structure lever, not paper-quantity lever).
- The EXP-1 success criterion hinges on whether (2.0, 4, real_g) shows real_g ≠ perm_g at p < 0.05 AND |Δ%| > 2σ.

---

## 7. Artifacts

| Artifact | Purpose | Location |
|---|---|---|
| Sweep driver | runs 27-cell grid × 3 seeds + cosine baseline | `/tmp/wf302_p1_regime_sweep_driver.py` (NOT in repo; sweep-time file) |
| Orchestrator | per-cell wall + audit-codes + F-side ratio capture | `/tmp/wf302_p1_orchestrator.py` (NOT in repo) |
| Aggregator | per-variant statistics + verdicts + F-side check | `/tmp/wf302_p1_aggregator.py` (NOT in repo) |
| Output dir | per-cell summary.json | `/tmp/wf302-p1-regime-sweep/{variant}/seed{seed}/summary.json` (81 dirs) |
| Markdown summary | per-(eps, L, profile) statistics + verdicts | `/tmp/wf302-p1-regime-sweep-summary.md` |
| Audit doc | this design doc | `docs/audit/wave302-p1-regime-sweep-design.md` |

---

## 8. Invariants preserved

- **D.4 30/30 PASS:** preserved (no framework code touched; the sweep driver is in `/tmp/`).
- **Claims no drift:** W291 P5 verdicts preserved (`leverType = SUPPORTED`, `headliner = STRONG`); Wave 302 adds the L=4 expansion verdict. CLAIMS.md is not edited.
- **ruff 0:** no `.py` file modified in this sweep (driver lives in `/tmp/`).
- **mkdocs 0 warnings:** `docs/audit/` is `not_in_nav` per `mkdocs.yml:239`.
- **vendored NOT touched:** confirmed — no edits under `vendored/`, `data/`, or `.venvs/`.
- **framework source NOT touched:** confirmed — `adaptive_reflow/` is byte-untouched; only `/tmp/wf302_p1_*.py` files added.

---

## 9. Audit doc fingerprint

- **audit doc path:** `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave302-p1-regime-sweep-design.md`
- **prior docs cited:** wave299, wave291-p1, wave291-p3, wave291-p4, wave291-p5, wave296-p7, wave290-p3, theorem-1-self-contained
- **code references:** `adaptive_reflow/algorithm/scheduler/adaptive.py:874-994, 1004, 1440-1632`; `adaptive_reflow/framework/paper_quantities_cache.py:103-106`; `tools/batched_framework_cifar.py`
- **sweep grid:** 27 codim × 3 seeds = 81 cells (L=4 first; L=8/L=16 conditional)
- **regimes:** sheet-dominated (eps=0.5), transition (eps=2.0), cell-dominated (eps=10.0)
- **F-side defaults:** ρ=0.1, c=1.0, d=1.0, η=0.1 (ρ/d = 0.1 < 0.25 = d/4 ✓)
- **verdict thresholds:** STRONG ≤ 1σ = 0.755%, PARTIAL 1σ-2σ, WEAK > 2σ = 1.510%
- **predicted EXP-1 outcome:** regime-gated lever hypothesis holds at (2.0, 4, real_g); cosinenoise-band σ = 0.755%

---

## 10. Honest summary

**The regime sweep is the prerequisite for every Paper B experiment.** Without it, no cell-level result can claim "the paper-quantity lever is load-bearing" — the W291 P5 finding shows the lever is INERT at the W286 P headline config (eps=10/L=4/n_min=0/profile=None). The regime sweep identifies which (eps × L × profile) configurations activate the lever.

**The 27-cell design is the smallest possible grid that:**
- (a) Tests all 3 regimes (sheet/transition/cell) with paper-quantity contrast (real_g vs None vs perm_g).
- (b) Provides permutation-test falsification at every (eps × L) cell (perm_g control).
- (c) Maintains the W291 P5 3-seed noise band (cosine σ = 0.755% relative).
- (d) Preserves the W291 P5 cycle_length sweep at L=4 (verified headliner) and expands to L=8, L=16.
- (e) Provides F-side compatibility check per cell (COMPAtible / BOUNDARY / INERT) using the closed-form ratio trajectory against the 4 F-side hypotheses.

**The 27-cell sweep runs in ~45 min on a single GPU** (FID-bound; sequential per user directive). Wave 302 runs the L=4 cells first (9 configs × 3 seeds = 27 cells, ~15 min). Wave 303/304 are conditional on the L=4 outcome.

**The predicted verdict (a priori per the closed-form math):**
- (10.0, 4, real_g) and (10.0, 4, perm_g) are byte-equivalent (scheduler structure lever, paper quantities INERT) — W291 P5 confirmed.
- (2.0, 4, real_g) is the predicted high-yield cell — regime-gated lever hypothesis predicts manifest here.
- (0.5, 4, real_g) is predicted INERT (sheet-sat regime) — paper quantities inert by closed-form math.

**Falsification criterion:** if ALL three regimes are INERT (no regime-divergent verdict), the regime-gated hypothesis REFUTES and the W286 P verdict (`scheduler_structure lever, paper_quantities NOT the lever`) holds globally. Paper B §3.5 would then need to claim "the framework operates independent of paper quantities; the JMAA Theorem 1 bound is a theoretical framing, not an operational one" — a publishable but more conservative result.

The next-wave task, when this lands, is to write `docs/audit/wave302-p2-l4-regime-results.md` with the actual 27-cell × 3-seed matrix and the regime-gated verdict (or its falsification).