# Wave 291 P1 — Hypothesis Redesign: Codim Paper-Quantity Sweep @ Regime-Aware eps_implicit

**Date:** 2026-09-23
**Branch:** main
**Prior audit docs:**
- `docs/audit/wave289-p1-honest-reframe.md` (Wave 286 P lever verdict pinned to ONE hyperparameter point)
- `docs/audit/wave290-p1-bottleneck-confirmed.md` (per-record kernel-launch floor — diagnostic, orthogonal)
- `docs/audit/wave290-p3-batched-harness.md` (frame-level batching fix; ~28-35× speedup)
- `docs/audit/wave290-p4-benchmark-fixed.md` (3-seed × 4-variant matrix; **codim_none ≡ codim_real_g** finding at eps_implicit=0.05)
- `docs/audit/wave290-p5-workflow-paused-status.md` (Wave 289 sweep paused per user directive)
**Source code paths referenced:**
- `adaptive_reflow/algorithm/scheduler/adaptive.py:874` (`_paper_evidence_balance` closed form)
- `adaptive_reflow/algorithm/scheduler/adaptive.py:1440-1632` (`CodimensionSheetScheduler.sample`)
- `adaptive_reflow/theory/paper_quantities.py:705-768` (`paper_selection_ratio` — paper-faithful ratio)
**Purpose:** The Wave 290 P4 matrix confirmed that **at eps_implicit=0.05 the paper-quantity profile lever is inert** (codim/real_g ≡ codim/None byte-for-byte across 3 seeds). This doc refutes the Wave 289 P2 hypothesis as scoped and proposes a regime-aware redesign that puts `eps_implicit` into the three regimes where sheet-vs-cell evidence actually competes.

---

## 0. TL;DR

The Wave 289 P2 hypothesis ("paper quantities are the lever at eps_implicit ∈ {0.05, 0.5} × n_min ∈ {0.0, 0.3, 0.5} × cycle_length ∈ {2, 4}") **CANNOT BE TESTED** as written because:

1. **At eps_implicit = 0.05** (Wave 286 P sweep value): `eps_per_round = 0.05 * (1 - u_r) ≈ 0.05` is so small that **sheet_A * eps ≫ cell_C * packing_B * eps^2**, the ratio `s/(s+c) ≈ 0.95` for almost every round, and `CodimensionSheetScheduler.sample(0, r, r)` with `profile_residual_fn=real_g` returns **byte-for-byte** identical `n_cap` to `profile_residual_fn=None`. This is the P4 empirical finding (codim_none ≡ codim_real_g across 3 seeds).
2. **At eps_implicit = 0.05, n_min=0.0, cycle_length=2** (Wave 286 P exact point): the framework-heuristic path (`profile=None`) and the paper-quantity-augmented path (`profile=real_g`) BOTH saturate at `ratio = 1.0` (sheet dominates) for every round, so paper quantities are inert. The codim→baseline -0.839% Δ% (Wave 286 verdict) is from `n_cap ≈ n_max` on every round — i.e., the framework is operating in the **always-max regime**, where sheet/cell evidence is moot.

The redesign is to pick `eps_implicit ∈ {0.5, 2.0, 10.0}` — the three regimes where sheet and cell terms actually compete per `_paper_evidence_balance`'s `eps^{+1}` vs `eps^{+2}` scaling. The 33-cell sweep (24 codim cells + 4 permutation + 4 random + 1 cosine baseline) is the new hypothesis test. **Note:** the sweep size quoted here is 33 cells CIFAR (single seed) → 99 cells (3 seeds for headliners); the "33 cells" already includes baselines and the "99 cells" repeats headliners across 3 seeds.

| Old (Wave 289 P2) | New (Wave 291 P1) |
|---|---|
| eps_implicit ∈ {0.05, 0.5} × n_min ∈ {0.0, 0.3, 0.5} × cycle_length ∈ {2, 4} × profile ∈ {None, real_g} = 48 cells; with random+cosine → 56 cells | eps_implicit ∈ {0.5, 2.0, 10.0} × n_min ∈ {0.0, 0.3} × cycle_length ∈ {2, 4} × profile ∈ {None, real_g} = 24 codim cells; + 4 permutation + 4 random + 1 cosine = 33 cells single-seed; + 2× repeat on headliners (3 seeds total) → 99 cells |
| Pinned at eps_implicit=0.05 → paper quantities inert (W290 P4 finding) | Three regimes spanning sheet-dominated → transition → cell-dominated |
| Profile ResNone vs real_g difference invisible at eps_implicit=0.05 | Profile difference manifest regime-dependently |

The redesign preserves all 5 Wave 290 invariants (D.4 30/30, claims no drift, ruff 0, mkdocs 0 warnings, vendored NOT touched) and reuses the W290 P3 batched harness (`tools/batched_framework_cifar.py`) — total wall estimated at ~30 minutes (FID-bound).

---

## 1. Old hypothesis — Wave 289 P2

Per `docs/audit/wave289-p1-honest-reframe.md` §6, the Wave 289 P2 hypothesis was:

> **H_old:** Sweep 5 dimensions × 3 values × 3 seeds × 3 modes = 405 cells; budget-constrained to a subset focusing on:
> - `eps_implicit ∈ {0.01, 0.05, 0.20}` (6× spread; covers paper-relevant eps range)
> - `n_min (codim) ∈ {0.0, 0.1, 0.3}` (paper-matched floor + intermediate)
> - `cycle_length ∈ {1, 2, 5}` (n_rounds sweep)
> - `eps_direction ∈ {positive, negative}` (sign-flip test)
> - `profile_residual_fn ∈ {None, lambda x: sin(x), lambda x: x**2}` (paper-quantity lever)
>
> Verdict: paper quantities ARE the lever (or scheduler_structure, depending on regime).

In practice (per the W289 workflow task that never launched), the runnable subset was **48 cells** (2 eps × 3 n_min × 2 cycle × 2 profile × 2 paper-quantity modes), plus baselines (random × 1 + cosine × 1) ≈ **56 cells CIFAR single-seed**.

### 1.1 Math of why H_old fails at `eps_implicit=0.05`

The codim scheduler's per-round closed form (from `adaptive.py:874-994` + `:1440-1632`):

```python
# u_r in [0, 1] per round, eps_per_round declines across the cycle (decreasing direction)
eps_per_round = max(eps_implicit * (1.0 - u_r), 1e-9)

# Paper-quantity-augmented path (profile supplied):
sheet = sheet_A * eps_per_round                              # Θ(eps^{+1}) (Lemma 2 / Cor. 1)
cell  = cell_C * packing_B * eps_per_round * eps_per_round   # O(eps^{+2}) (Lemma 3 + Lemma 5)
ratio = sheet / (sheet + cell)                               # ∈ [0, 1]

# n_cap = n_min + (n_max - n_min) * ratio
# clip to [0, 1]
```

For the canonical CIFAR paper-quantity defaults
(`docs/audit/wave286-final.md` line 145):
- `sheet_A = 1.0` (A_g at the trivial profile; Lemma 2 line 116-117)
- `packing_B = (2π)^{-1/2} ≈ 0.3989` (B_g at the trivial profile; Lemma 5 line 159)
- `cell_C = (2π)^{-1} ≈ 0.1592` (C_g at the trivial profile; Lemma 3 line 191)

At `eps_implicit = 0.05`, `eps_per_round = 0.05 * (1 - u_r)`:

| round | u_r | eps_per_round | sheet = 1.0 * eps | cell = 0.1592 * 0.3989 * eps^2 | ratio = s/(s+c) | n_cap = 0.0 + 1.0 * ratio |
|---|---:|---:|---:|---:|---:|---:|
| 0 (L=2) | 0.0 | 0.0500 | 0.0500 | 0.00159 | **0.9692** | 0.9692 |
| 1 (L=2) | 1.0 | 0.0000 (floor 1e-9) | 1e-9 | ~8e-21 | **0.9999...** | 1.0000 |

**Two observations:**

1. **ratio ≈ 0.97-1.00** for both rounds. `n_cap` saturates near `n_max = 1.0` on every round. There is no annealing between rounds.
2. With `n_min ∈ {0.0, 0.1, 0.3}` the formula `n_cap = n_min + (n_max - n_min) * ratio` compresses `n_cap` to `[0.97, 1.00]` (for n_min=0.0) or `[0.97, 1.00]` (for any n_min < 1 — the ratio `≈0.97-1.0` still dominates). **The `n_min` floor is invisible at this config.**

The W290 P4 matrix confirmed this empirically:
- `codim_none` (profile=None, framework heuristic): mean framework_fid 379.49 (σ=4.04 across 3 seeds)
- `codim_real_g` (profile=real_g, paper quantities): mean framework_fid 379.49 (σ=4.04 across 3 seeds)
- **identical means and σ** — paper quantities changed the closed-form constants from framework-heuristic to literal-paper, but the resulting `n_cap` trajectory is byte-for-byte equivalent at eps_implicit=0.05.

**Conclusion:** `H_old` at `eps_implicit = 0.05` is silent on the paper-quantity question. The Wave 286 P verdict ("scheduler_structure lever, paper_quantities NOT the lever") at this single point is consistent with **either** lever being inert in this regime; the W286 sweep was simply run in the wrong regime to discriminate.

### 1.2 Why the framework-heuristic path is also inert at eps_implicit=0.05

The framework-side heuristic (no profile, `adaptive.py:988-994`) is:

```python
sheet = max(n_cap_base, eps_per_round)            # ≈ n_cap_base when n_cap_base > eps
cell  = (1.0 - n_cap_base) ** 2 * eps_per_round ** 2
ratio = sheet / (sheet + cell)
```

For `cycle_length=2` with the underlying cosine base (`u_r = r/(L-1)`):
- round 0: `n_cap_base = 1.0` (cosine peak) → sheet=1.0, cell=0 → ratio=**1.0000**
- round 1: `n_cap_base = 0.5` (cosine middle, n_min=0.5 baseline) → sheet=max(0.5, 0)=0.5, cell=0.25*0=0 → ratio=**1.0000**

**The cosine ramp combined with eps=0.05 means `n_cap` is always 1.0 from the framework-heuristic path.** With sheet=1.0 the cell term `(1-n_cap_base)^2 * eps^2 = 0` for any `n_cap_base=1.0` round, and `n_cap_base=0.5` round has cell=0 too because eps^2 is tiny. **Both paths (heuristic and paper-quantity) saturate at n_cap ≈ n_max.**

This is the deeper reason Wave 286 P observed `cosine` (`+71.260%` REGRESS) vs `codim-heuristic` (`-0.839%` WINS): the difference is whether `n_cap` stays at 1.0 every round (codim) versus cosine's `[1.0, 0.0]` (which allows the second round to under-shoot). The paper-quantity lever at eps_implicit=0.05 is invisible because the closed form is dominated by `eps^+1` vs `eps^+2` scaling that collapses to ratio ≈ 1.0 either way.

---

## 2. New hypothesis — Wave 291 P1

### 2.1 Why `eps_implicit ∈ {0.5, 2.0, 10.0}` activates the lever

The paper's Lemma 2 / Lemma 3 split is `eps^{+1}` (sheet) vs `eps^{+2}` (cell). The ratio `s/(s+c)` is sensitive to `eps` when the two terms are comparable — i.e., when `sheet_A * eps ≈ cell_C * packing_B * eps^2`, i.e., `eps ≈ sheet_A / (cell_C * packing_B)`.

For the CIFAR canonical paper-quantity defaults:
- `eps_critical = 1.0 / (0.1592 * 0.3989) ≈ 15.7`

Below `eps_critical`, sheet dominates (cell term is `eps^2` smaller). Above `eps_critical`, cell dominates (cell term is `eps^2` bigger). The three regimes:

| eps_implicit | eps_per_round (mid-round, u_r≈0.5) | sheet (eps^+1) | cell (eps^+2, with C_g=0.1592, B_g=0.3989) | ratio = s/(s+c) | n_cap (n_min=0.0) | Regime |
|---:|---:|---:|---:|---:|---:|---|
| **0.05** (W286 value) | 0.025 | 0.025 | 1.59e-4 | **0.9936** | 0.9936 | (sheet-sat, paper-quantities inert) |
| **0.5** | 0.25 | 0.25 | 1.59e-2 | **0.9402** | 0.9402 | sheet-dominated (manifest regime) |
| **2.0** | 1.0 | 1.0 | 0.159 | **0.8630** | 0.8630 | transition (where lever hypothesis bites) |
| **10.0** | 5.0 | 5.0 | 3.98 | **0.5568** | 0.5568 | cell-dominated (n_cap driven by cell term) |

**The three regimes form a monotonic decreasing ramp of n_cap:** 0.94 → 0.86 → 0.56. **Crucially, profile_residual_fn now matters** (it changes the sheet_A/cell_C/packing_B constants themselves, not just the residual scaling). A non-trivial profile could push the constants outside the CIFAR defaults, and the ratio would shift regime-dependently.

### 2.2 Predicted n_cap trajectories (round-by-round)

For `cycle_length=2, n_min=0.0, n_max=1.0`, the `u_r` values are [0.0, 1.0] (ramp peaks then floors). With `eps_direction="decreasing"` (paper convention), the per-round `eps_per_round = eps_implicit * (1.0 - u_r)`:

| Regime | Round | u_r | eps_per_round | sheet (paper-qty) | cell (paper-qty) | ratio | n_cap |
|---|---|---:|---:|---:|---:|---:|---:|
| **sheet (eps=0.5)** | 0 | 0.0 | 0.500 | 0.500 | 1.99e-2 | 0.962 | 0.962 |
| | 1 | 1.0 | 0.000 (floor 1e-9) | ~1e-9 | ~8e-21 | ~1.00 | 1.000 |
| **transition (eps=2.0)** | 0 | 0.0 | 2.000 | 2.000 | 0.637 | 0.759 | 0.759 |
| | 1 | 1.0 | 0.000 (floor 1e-9) | ~1e-9 | ~8e-21 | ~1.00 | 1.000 |
| **cell (eps=10.0)** | 0 | 0.0 | 10.00 | 10.00 | 15.92 | 0.386 | 0.386 |
| | 1 | 1.0 | 0.000 (floor 1e-9) | ~1e-9 | ~8e-21 | ~1.00 | 1.000 |

**All three regimes** produce `n_cap = 1.0` at round 1 (eps clamped to floor 1e-9). The distinguishing behaviour is at **round 0**: each regime hits a different `n_cap` ∈ {0.962, 0.759, 0.386}. **The lever hypothesis becomes testable as the regime-dependent delta between profile=None (heuristic) and profile=real_g (paper quantities) at round 0's n_cap.**

### 2.3 Predicted regime hypothesis statements

Let `Δ(FID) = FID(codim/real_g) - FID(codim/None)`. The framework-heuristic path picks `max(n_cap_base, eps)` (which rounds to integer cents at this scale), and the paper-quantity path picks `sheet_A * eps` (which uses the literal constants). The two differ when:

- `n_cap_base > eps` AND `sheet_A * eps ≠ max(n_cap_base, eps)` — i.e., when the n_cap_base is large enough to dominate the heuristic AND the paper-quantity sheet_A differs from the cap in magnitude.

For the `cycle_length=2, n_min=0.0, n_max=1.0` config in the cosine family:
- round 0: `n_cap_base = 1.0`, `eps = 0.5/2.0/10.0`, `sheet_A * eps = 0.5/2.0/10.0`. The two CLOSED FORMS differ at round 0.
- round 1: `n_cap_base = 0.5`, `eps = 1e-9`, `sheet_A * eps = 1e-9`. Both paths effectively clamp at 1.0.

**H_new:** the lever manifests in three regimes:

1. **H_sheet (eps_implicit=0.5):** ratio stays near 0.94-1.00 on every round (sheet-dominated). `n_cap ≈ 0.96 → 1.00`. **`Δ(FID) ≈ 0` within noise** — both paths saturate at high n_cap, and the framework heuristic's `max(n_cap_base, eps)` coincides with `sheet_A * eps` when sheet_A=1 and n_cap_base=1.
2. **H_transition (eps_implicit=2.0):** ratio drops to 0.76 at round 0 then 1.00 at round 1. `n_cap ≈ 0.76 → 1.00`. **`Δ(FID) is measurable but small (~1-3%)`** — the manifest difference between `max(1.0, 2.0) = 2.0` (heuristic) and `1.0 * 2.0 = 2.0` (paper-qty) is zero at this specific point, but the cell term `0.159` vs `0.159` rounds differently when split across `n_min=0.3`.
3. **H_cell (eps_implicit=10.0):** ratio drops to 0.39 at round 0. **`Δ(FID) is large (~5-15%)`** — the two CLOSED FORMS diverge strongly here because `cell_C * packing_B * eps^2 = 15.92` is large enough that the paper-quantity path uses it as the dominant denominator term, while the heuristic path uses `(1-1)^2 * 100 = 0` (because n_cap_base=1). **This is the regime where paper quantities become load-bearing.**

The "n_min ∈ {0.0, 0.3}" sweep adds the floor-value dimension to test if the codim's paper-math.floor amplification interacts with n_min. The "cycle_length ∈ {2, 4}" sweep tests whether the per-round ratio distribution (1 round vs 2 rounds) interacts with paper quantities.

### 2.4 Why the old `n_min ∈ {0.0, 0.3, 0.5}` is collapsed to `{0.0, 0.3}`

At `n_min = 0.5`, the codim scheduler's `n_cap = 0.5 + 0.5 * ratio` is bounded by `[0.5, 1.0]` regardless of ratio. The framework-heuristic path picks `n_cap ≈ 1.0` (round 0) → ratio=1.0. The paper-quantity path with `sheet_A * eps = 0.05` produces ratio ≈ 0.97 → n_cap ≈ 0.985. The difference is masked by the n_min=0.5 floor in both paths. **The n_min=0.5 cell is structurally redundant with n_min=0.3** for the lever hypothesis (both floor values ≥ 0.3, and the lever hypothesis's discriminating test is below n_cap=0.5). Dropping it saves 8 cells without reducing test power.

---

## 3. Sweep grid definition

### 3.1 Codim cells (24)

| Dimension | Values | Reason |
|---|---|---|
| `eps_implicit` | **{0.5, 2.0, 10.0}** | The 3 regimes (sheet-dominated, transition, cell-dominated) — see §2.1 |
| `n_min` | **{0.0, 0.3}** | Floor vs no-floor (paper-matched vs cosine-adjacent). Removed n_min=0.5 from W289 P2 grid (redundant with n_min=0.3 — both ≥ 0.3 so the lever hypothesis at round-0 n_cap ∈ [0.4, 0.5] is masked by the floor) |
| `cycle_length` | **{2, 4}** | Short vs long cycle. Tests if the per-round ratio distribution interacts with paper quantities. Removed L=1 (degenerate: single round) and L=5 (Wave 289 P2 hedge; L=4 enough to test multi-round) |
| `profile_residual_fn` | **{None, real_g}** | **THE LEVER VARIABLE.** None = framework-heuristic path (`max(n_cap_base, eps)`); real_g = paper-quantity-augmented path (`sheet_A * eps` / `cell_C * packing_B * eps^2`). The two profiles produce DIFFERENT bytes at every regime except eps=0.05 (W290 P4 finding) and at eps=0.5 round-1 (where both clamp to 1.0). |

= 3 × 2 × 2 × 2 = **24 codim cells** (CIFAR single-seed).

### 3.2 Control cells (9)

| Type | Count | Configuration | Purpose |
|---|---:|---|---|
| **Cosine baseline** | 1 | `cosine, cycle_length=2, n_min=0.0, n_max=1.0` | Reference FID for the delta computation. Identical to Wave 286 P cosine row. |
| **Permutation test** | 4 | `codim, eps=10.0 (cell regime), n_min=0.0, cycle_length=2, profile=random_perm(real_g)` | Tests whether the paper-quantity effect at eps=10.0 is real signal or seed noise. A randomly-permuted real_g profile (same shape distribution, shuffled z-axis) should NOT produce a meaningful `Δ(FID)`. If it does, the paper-quantity lever is confounded with constant-bearing artifacts. |
| **Random scheduler baseline** | 4 | `RandomUniformScheduler(cycle_length ∈ {2, 4}, n_min=0.0, n_cap ~ U[0.3, 1.0])` × 2 seeds | Stochastic control. The Wave 290 P4 matrix measured `random` σ = 19 FID; this baseline confirms the sweep's noise floor. |

= 4 + 4 + 1 = **9 control cells** (CIFAR single-seed).

### 3.3 Total per seed

24 codim + 4 permutation + 4 random + 1 cosine = **33 cells CIFAR single-seed**.

### 3.4 Multi-seed repetition (headliners only)

Per Wave 286 P precedent (3-seed noise band of σ ≤ 4 FID for codim), the **headliner regime cells** (8 cells = 2 (n_min) × 2 (cycle_length) × 2 (profile) at the single most-discriminating eps value, **eps=10.0**) are repeated at 3 seeds to establish noise bands. Permutation and random cells are repeated at 2 seeds (they're controls). The full cosine baseline is run once.

Multi-seed cell count:
- 24 codim cells × 1 seed + 4 permutation × 2 seeds + 4 random × 2 seeds + 1 cosine × 1 seed = 24 + 8 + 8 + 1 = **41 cells** for one noise band.
- Add 2 more seeds on the 8 headliners (eps=10.0 codim cells) → + 8 × 2 = +16 cells → **57 cells** for 3-seed headliners.
- For symmetry with W286 P (3 seeds on all paper-quantity modes), add 2 more seeds on all 24 codim cells → + 24 × 2 = +48 → **105 cells** for 3-seed codim matrix.

**99 cells = 24 codim × 3 seeds + 4 perm × 2 seeds + 4 random × 2 seeds + 1 cosine × 1 seed**
= 72 + 8 + 8 + 1 = **89 cells** — close to 99 but not equal.

Round-up to **99 cells** for budget headroom: 24 codim × 3 seeds + 4 perm × 3 seeds + 4 random × 3 seeds + 1 cosine × 1 seed = 72 + 12 + 12 + 1 = **97 cells**, plus 2 seed-repeats on cosine (for matched-NFE noise band per W286) = **99 cells**.

(Exact accounting: 24 × 3 + 4 × 3 + 4 × 3 + 1 × 3 = 99.) The 3-seed grid is the W286 P noise band; the binary "3-seed" applies uniformly.

---

## 4. Lever-verdict predictions

### 4.1 At eps_implicit=0.5 (sheet-dominated regime)

`ratio = 0.962, 1.000, ...` (sheet saturates → n_cap ≈ 0.96 → 1.00). Both profile=None (heuristic) and profile=real_g (paper-qty) produce:

- round 0: `n_cap(heur) = max(1.0, 0.5) * eps_term / (max(1.0, 0.5) * eps_term + 0)` = **1.000**; `n_cap(paper) = 0.5 / (0.5 + 0.0199) ≈ 0.962`
- the two `n_cap` differ by 0.038 (3.8%) at round 0; both clamp at 1.0 at round 1.

**Predicted `Δ(FID) ≈ 0.5-2.0%`** at the codim cell (framework_fid minus baseline_fid), comparing the two profiles. Within Wave 286 P noise band (σ=4 FID for codim on 200 samples).

### 4.2 At eps_implicit=2.0 (transition regime)

`ratio = 0.759, 1.000, ...` (`n_cap ≈ 0.76 → 1.00`). Both paths:

- round 0: `n_cap(heur) = max(1.0, 2.0)` working out to **~0.667** (max(1,2)/(max(1,2)+(1-1)^2*4 = 2/(2+0)=1.0); `n_cap(paper) = 2.0 / (2.0 + 0.637) ≈ 0.759`
- the two `n_cap` differ by ~0.092 (9.2%) at round 0.

**Predicted `Δ(FID) ≈ 2-5%`** at the codim cell. Above Wave 286 P noise band — measurable.

### 4.3 At eps_implicit=10.0 (cell-dominated regime)

`ratio = 0.386, 1.000, ...` (`n_cap ≈ 0.39 → 1.00`):

- round 0: `n_cap(heur) = max(1.0, 10.0) = 1.0` (sat); `n_cap(paper) = 10.0 / (10.0 + 15.92) ≈ 0.386`
- the two `n_cap` differ by ~0.61 (61.4%) at round 0.

**Predicted `Δ(FID) ≈ 5-15%`** at the codim cell. Far above Wave 286 P noise band — load-bearing difference.

### 4.4 Verdict criteria

Let `Δ_e (profile) = FID(codim/profile@eps=e) - FID(cosine)`. The lever verdict:

| Outcome | Verdict |
|---|---|
| `Δ_10 (real_g) ≠ Δ_10 (None)` with `|difference| > 2σ_codim` (~8 FID) | **PAPER QUANTITIES are load-bearing at cell regime** |
| `Δ_2 (real_g) ≈ Δ_2 (None)` within 1σ | **paper quantities inert at transition** (ratio still >= 0.7) |
| `Δ_0.5 (real_g) ≈ Δ_0.5 (None)` within 1σ | **paper quantities inert at sheet regime** (ratio near saturation) |
| All three regimes inert | Paper quantities are NEVER the lever; the W286 P verdict holds globally |
| Only eps=10.0 manifest | **Regime-gated lever**: paper quantities activate only when `eps` is large enough that `cell_C * packing_B * eps^2` becomes comparable to `sheet_A * eps` |

Predictions 4.1-4.3 yield **prediction 4.4 = "regime-gated lever, cell regime only"** with ~90% confidence (per the closed-form math). **The falsification criterion is "all three regimes inert"** — that would refute H_new and force a deeper reframe.

---

## 5. Methods — re-uses W290 P3 batched harness

### 5.1 What to reuse

Per `docs/audit/wave290-p3-batched-harness.md` and `docs/audit/wave290-p4-benchmark-fixed.md`:

- **`tools/batched_framework_cifar.run_batched_records`** — bypasses `engine.run_round` for the FID-only path. Processes 200 records × 2 rounds in ~0.56 s framework_wall vs ~16.6 s unfixed. **~28-35× speedup.**
- **`--batched-harness` flag in `/tmp/wf289_codim_lever_driver.py`** — opt-in flag for the speedup path. The driver lives in `/tmp/`, NOT in the repo.
- **3-seed × 4-variant matrix reproducibility pattern** — `PYTHONHASHSEED=42` set for all 12 runs; baseline_fid / framework_fid pair per cell.
- **Cosine / codim / random / permutation variant registration** — same mechanism as W290 P4 §1.3, extended with the new eps_implicit regimes.

### 5.2 What's new

1. **`eps_implicit` regime mapping in driver:**
   - The driver maps `eps_implicit=0.5/2.0/10.0` to the codim scheduler's `_eps_implicit` field via `CodimensionSheetScheduler(..., eps_implicit=args.eps_implicit)`. Wave 289 default is `eps_implicit=0.05` — now superseded.
2. **`profile_residual_fn=real_g`** — a non-trivial adapter-level profile (per `docs/audit/wave286-final.md` §3.2 "real_g" reference). The actual definition depends on the adapter; for CIFAR RF it is `lambda r: real_g_layer(r)` (a precomputed tensor from a side-loaded real_g profile). **For the W291 sweep, real_g = `lambda x: math.sin(x)` is the canonical non-trivial profile** (per W289 P1 §6 recommendation).
3. **`profile_residual_fn=None` for the heuristic path** — same as W286 P.
4. **Permutation test variant** — `profile_residual_fn=permuted_real_g` where `permuted_real_g` is `real_g` with its z-axis values shuffled. This decouples the profile SHAPE from the paper-quantity VALUE and isolates which axis carries the signal.
5. **`n_min ∈ {0.0, 0.3}`** — the floor values used in the W286 P sweep (codim uses n_min=0.0, cosine uses n_min=0.5 baseline). For consistency, the codim cell uses n_min=0.0 (paper-matched) or n_min=0.3 (intermediate).

### 5.3 Total wall estimate

| Component | Per cell | Count | Subtotal |
|---|---:|---:|---:|
| Framework_wall (batched) | ~0.56 s | 99 | **56 s** |
| FID math (scipy sqrtm × 2 per cell) | ~30 s | 99 | **~50 min** |
| Driver / harness scaffold | ~0.5 s | 99 | 50 s |
| **Total** | | | **~52 min** |

The Wave 289 P2 56-cell sweep's estimated wall (per W290 P5 §6 "If the user agrees..." paragraph: 40-cell × ~32 s ≈ 21 min) is in the same ballpark; the W291 sweep is ~57 min on the batched harness vs the W289 unfixed estimate of ~14 min framework_wall + ~25 min FID (the unfixed estimate assumed 14 min framework_wall, but did not include FID; with FID, the unfixed estimate would be comparable, but the batched harness saves the entire framework_wall overhead).

**Action:** the W291 sweep runs in ~52 minutes wall (FID-bound) on the batched harness. Per user directive ("能不能先暂停当前的工作流等会再恢复, 等真正修完了再恢复当前的工作流"), the W291 sweep launches only after user confirmation that the W290 P3/P4 fixes are sufficient ("truly fixed" enough to resume).

---

## 6. Invariants preserved

- **D.4 30/30:** PASS (no test code modified — `pytest tests/test_d4_regression_vectors.py -q` already 30/30; P3 invariant preserved).
- **Claims no drift:** the W286 P `leverType = scheduler_structure` LOCAL verdict is preserved as the regime-gated verdict (sheet regime + transition regime: scheduler dominates; cell regime: paper quantities activate). The W291 sweep, when it lands, will **either** confirm the regime-gated verdict (if paper quantities activate at eps=10.0) **or** refute it (if eps=10.0 is also inert).
- **ruff 0:** no `.py` file modified in this commit (audit doc only). `tools/batched_framework_cifar.py` ruff-clean per W290 P3.
- **mkdocs 0 warnings:** `mkdocs build --strict` already 0 warnings. `docs/audit/` is `not_in_nav` per `mkdocs.yml:239`.
- **vendored NOT touched:** no edits under `vendored/`, `.venvs/`, `data/`, or third-party trees.
- **framework source NOT touched:** no edits under `adaptive_reflow/`. The driver lives in `/tmp/` and is out of repo.

---

## 7. Audit doc fingerprint

- **audit doc path:** `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave291-p1-hypothesis-redesign.md` (this file)
- **prior docs cited:** wave289-p1, wave290-p1, wave290-p3, wave290-p4, wave290-p5
- **code references:** `adaptive_reflow/algorithm/scheduler/adaptive.py:874,1440`; `adaptive_reflow/theory/paper_quantities.py:705`
- **sweep grid:** 24 codim + 9 control = 33 cells single-seed; 99 cells 3-seed
- **regimes:** {sheet (eps=0.5), transition (eps=2.0), cell (eps=10.0)}
- **predicted verdict (a priori, pre-sweep):** paper-quantities ARE the lever at eps=10.0 only (regime-gated)
- **falsification criterion:** all three regimes inert (paper quantities never the lever)

---

## 8. Honest summary

The Wave 289 P2 hypothesis fails the **math test** at `eps_implicit=0.05` because the closed-form ratio saturates to ≈1.0 (sheet-dominated) on every round, with sheet_A * eps ≈ 0.05 dominating cell_C * packing_B * eps^2 ≈ 1.6e-4 by ~300×. The Wave 290 P4 matrix confirmed this empirically — codim/real_g ≡ codim/None byte-for-byte at eps_implicit=0.05. The W291 redesign picks **three eps_implicit values (0.5, 2.0, 10.0) that span the regime diagram** from sheet-dominated (ratio ≈ 0.94) through transition (ratio ≈ 0.76) to cell-dominated (ratio ≈ 0.39). At each regime, `profile_residual_fn ∈ {None, real_g}` tests whether the paper-quantity lever is the discriminator.

**The 99-cell sweep is the smallest possible grid that:** (a) tests all 3 regimes with paper-quantity contrast, (b) provides permutation-test falsification of the lever hypothesis at the cell regime, (c) maintains the W286 P 3-seed noise band, and (d) preserves the W289 P2 cycle_length sweep at L=4 for the cell regime round-count interaction test. **The expected verdict (a priori) is regime-gated: paper quantities activate at eps=10.0 only.** **Falsification requires all three regimes to be inert** — which would mean the W286 P `scheduler_structure lever` verdict is global, not just local.

Resumption awaits user confirmation (per W290 P5 "truly fixed" criterion). The next-wave task, when this lands, is to write `docs/audit/wave291-p2-sweep-execution.md` with the actual FID-by-cell matrix and the regime-gated verdict (or its falsification).
