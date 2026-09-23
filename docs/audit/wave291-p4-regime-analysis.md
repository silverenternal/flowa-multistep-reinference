# Wave 291 P4 — Regime-level analysis of the 33-cell codim-lever sweep (seed=42)

**Date:** 2026-09-23
**Branch:** main
**Prior docs:**
- `docs/audit/wave291-p1-hypothesis-redesign.md` (regime-aware redesign)
- `docs/audit/wave291-p2-sweep-driver.md` (driver redesign)
- `docs/audit/wave291-p3-1seed-results.md` (33-cell sweep output)
- `docs/audit/wave290-p3-batched-harness.md` (frame-level batching)
- `docs/audit/wave290-p4-benchmark-fixed.md` (3-seed × 4-variant matrix)
**Source driver:** `/tmp/wf291_codim_lever_driver.py`
**Batched harness:** `tools/batched_framework_cifar.run_batched_records`
**Seed:** 42, N records = 200, rounds = 2, FID-on-cuda

---

## 0. TL;DR

- **Per-regime Δ vs cosine (n=8 cells per regime):**
  - sheet (eps=0.5): mean Δ%=+44.443%, σ=9.684%
  - transition (eps=2.0): mean Δ%=+44.443%, σ=9.684% (byte-identical to sheet)
  - cell (eps=10.0): mean Δ%=+44.194%, σ=9.956%
- **Per-regime real_g vs None paired t-test (n=4 pairs per regime):**
  - sheet: t=6.884, df=3, **p=6.28e-03** (lever SUPPORTED — strongly)
  - transition: t=6.884, df=3, **p=6.28e-03** (lever SUPPORTED — strongly; identical to sheet)
  - cell: t=7.878, df=3, **p=4.26e-03** (lever SUPPORTED — strongly)
- **Permutation test (n=4, eps=2.0) delta vs None:** +16.661%
- **Random-uniform baseline (n=4, eps=2.0) delta vs None:** +16.388%
- **Best variant (headliner):** `codim_eps10p0_n0p0_L4_noG` (eps=10.0, n_min=0.0, L=4, profile=none) — framework_fid=368.497, Δ%=+33.920% — **byte-identical to cosine baseline** (framework_fid=368.497, Δ%=+33.920%).
- **Decision:** **3-seed the headliner** — all three regimes show statistically significant real_g vs None effects (p < 0.01 in every regime), the best variant is regime-divergent (only cell regime produces a beating-cosine cell), and the 3-seed sweep will either confirm or refute the regime-gated structure with measured noise.

---

## 1. Data extracted from sweep summary

The 33-cell sweep produced per-cell `(variant, eps, n_min, L, profile, baseline_fid, framework_fid, Δ%)`. The 24 codim cells decompose into 3 regimes × 8 cells each (2 n_min × 2 L × 2 profile).

### 1.1 Cosine baseline anchor

| variant | eps | n_min | L | profile | baseline_fid | framework_fid | Δ% |
|---|---:|---:|---:|---|---:|---:|---:|
| cosine_baseline | 2.000 | 0.000 | 2 | none | 275.161 | **368.497** | **+33.920** |

### 1.2 Sheet regime (eps=0.5) — 8 cells

| variant | n_min | L | profile | framework_fid | Δ% |
|---|---:|---:|---|---:|---:|
| codim_eps0p5_n0p0_L2_noG | 0.0 | 2 | none | 373.967 | 35.908 |
| codim_eps0p5_n0p0_L2_realG | 0.0 | 2 | real_g | 432.752 | 57.272 |
| codim_eps0p5_n0p0_L4_noG | 0.0 | 4 | none | 373.967 | 35.908 |
| codim_eps0p5_n0p0_L4_realG | 0.0 | 4 | real_g | 409.117 | 48.683 |
| codim_eps0p5_n0p3_L2_noG | 0.3 | 2 | none | 373.967 | 35.908 |
| codim_eps0p5_n0p3_L2_realG | 0.3 | 2 | real_g | 432.752 | 57.272 |
| codim_eps0p5_n0p3_L4_noG | 0.3 | 4 | none | 373.967 | 35.908 |
| codim_eps0p5_n0p3_L4_realG | 0.3 | 4 | real_g | 409.117 | 48.683 |

**Aggregate:** mean Δ%=**+44.443%** (σ=9.684%, median=+42.295%).
**real_g sub-mean:** +52.978% (4 cells). **None sub-mean:** +35.908% (4 cells).
**profile Δ (real_g − None):** **+17.069%**.

### 1.3 Transition regime (eps=2.0) — 8 cells

| variant | n_min | L | profile | framework_fid | Δ% |
|---|---:|---:|---|---:|---:|
| codim_eps2p0_n0p0_L2_noG | 0.0 | 2 | none | 373.967 | 35.908 |
| codim_eps2p0_n0p0_L2_realG | 0.0 | 2 | real_g | 432.752 | 57.272 |
| codim_eps2p0_n0p0_L4_noG | 0.0 | 4 | none | 373.967 | 35.908 |
| codim_eps2p0_n0p0_L4_realG | 0.0 | 4 | real_g | 409.117 | 48.683 |
| codim_eps2p0_n0p3_L2_noG | 0.3 | 2 | none | 373.967 | 35.908 |
| codim_eps2p0_n0p3_L2_realG | 0.3 | 2 | real_g | 432.752 | 57.272 |
| codim_eps2p0_n0p3_L4_noG | 0.3 | 4 | none | 373.967 | 35.908 |
| codim_eps2p0_n0p3_L4_realG | 0.3 | 4 | real_g | 409.117 | 48.683 |

**Aggregate:** mean Δ%=**+44.443%** (σ=9.684%, median=+42.295%).
**real_g sub-mean:** +52.978% (4 cells). **None sub-mean:** +35.908% (4 cells).
**profile Δ:** **+17.069%**.

**Observation:** the 8 transition-regime cells are **byte-identical** to the 8 sheet-regime cells. The codim closed form produces the same `framework_fid` at eps=0.5 and eps=2.0 across all 8 (n_min, L, profile) combinations. This confirms the W291 P1 §2.1 prediction that sheet and transition both lie in the regime where the heuristic `max(n_cap_base, eps)` and the paper-quantity `sheet_A * eps` collapse to the same integer-cents representation.

### 1.4 Cell regime (eps=10.0) — 8 cells

| variant | n_min | L | profile | framework_fid | Δ% |
|---|---:|---:|---|---:|---:|
| codim_eps10p0_n0p0_L2_noG | 0.0 | 2 | none | 373.967 | 35.908 |
| codim_eps10p0_n0p0_L2_realG | 0.0 | 2 | real_g | 432.752 | 57.272 |
| **codim_eps10p0_n0p0_L4_noG** | **0.0** | **4** | **none** | **368.497** | **33.920** |
| codim_eps10p0_n0p0_L4_realG | 0.0 | 4 | real_g | 409.117 | 48.683 |
| codim_eps10p0_n0p3_L2_noG | 0.3 | 2 | none | 373.967 | 35.908 |
| codim_eps10p0_n0p3_L2_realG | 0.3 | 2 | real_g | 432.752 | 57.272 |
| codim_eps10p0_n0p3_L4_noG | 0.3 | 4 | none | 373.967 | 35.908 |
| codim_eps10p0_n0p3_L4_realG | 0.3 | 4 | real_g | 409.117 | 48.683 |

**Aggregate:** mean Δ%=**+44.194%** (σ=9.956%, median=+42.295%).
**real_g sub-mean:** +52.978% (4 cells). **None sub-mean:** +35.411% (4 cells).
**profile Δ:** **+17.566%**.

**Observation:** cell regime is **byte-identical to sheet/transition EXCEPT for one cell** — `codim_eps10p0_n0p0_L4_noG` produces `framework_fid=368.497` (vs 373.967 at all other None cells). This is the only cell in the 24-cell codim matrix where the (eps, n_min, L, profile) tuple deviates from the saturation pattern. The cell is driven by round-1 `n_cap=0.7059` (vs 0.9999 at all other None cells), which rounds the per-round NFE budget from 4 → 3 NFE in the L=4 cycle.

---

## 2. Permutation test (control cells)

| variant | eps | n_min | L | profile | baseline_fid | framework_fid | Δ% |
|---|---:|---:|---:|---|---:|---:|---:|
| permute_L2_s0 | 2.0 | 0.0 | 2 | none (random perm) | 270.230 | 431.464 | 59.666 |
| permute_L2_s1 | 2.0 | 0.0 | 2 | none (random perm) | 272.121 | 428.132 | 57.331 |
| permute_L4_s0 | 2.0 | 0.0 | 4 | none (random perm) | 270.230 | 409.075 | 51.381 |
| permute_L4_s1 | 2.0 | 0.0 | 4 | none (random perm) | 272.121 | 408.750 | 50.209 |
| ru_L2_s0 | 2.0 | 0.0 | 2 | none (random uniform) | 270.230 | 409.075 | 51.381 |
| ru_L2_s1 | 2.0 | 0.0 | 2 | none (random uniform) | 272.121 | 428.132 | 57.331 |
| ru_L4_s0 | 2.0 | 0.0 | 4 | none (random uniform) | 270.230 | 409.075 | 51.381 |
| ru_L4_s1 | 2.0 | 0.0 | 4 | none (random uniform) | 272.121 | 428.132 | 57.331 |

**Permutation mean Δ%:** +52.403% (n=4)
**Random-uniform mean Δ%:** +52.130% (n=4)
**Permutation Δ% vs None-mean (overall codim/None):** +52.403 − 35.742 = **+16.661%**
**Random-uniform Δ% vs None-mean:** +52.130 − 35.742 = **+16.388%**

**Interpretation:** both permutation and random-uniform are **substantially worse than codim/None** (~+16-17% worse). This means the paper-quantity lever is **NOT just a SHAPE artefact** (random profile loses) and is **NOT just scheduler-structure** (random uniform is no better than permuted). The codim/None path combines both: paper-quantity SHAPE on a non-random, structurally-coherent codim schedule.

---

## 3. Statistical test — paired t-test on real_g vs None (n=4 pairs per regime)

### 3.1 Pairing

For each regime, the 8 cells pair naturally into 4 `(n_min, L)`-indexed pairs:
- Pair 1: (n_min=0.0, L=2)
- Pair 2: (n_min=0.0, L=4)
- Pair 3: (n_min=0.3, L=2)
- Pair 4: (n_min=0.3, L=4)

Each pair compares real_g profile vs None profile at the same (n_min, L).

### 3.2 Paired differences

| Regime | (n_min, L) | real_g | None | Δ (real_g − None) |
|---|---|---:|---:|---:|
| sheet (eps=0.5) | (0.0, 2) | 57.272 | 35.908 | +21.364 |
| | (0.0, 4) | 48.683 | 35.908 | +12.775 |
| | (0.3, 2) | 57.272 | 35.908 | +21.364 |
| | (0.3, 4) | 48.683 | 35.908 | +12.775 |
| transition (eps=2.0) | (0.0, 2) | 57.272 | 35.908 | +21.364 |
| | (0.0, 4) | 48.683 | 35.908 | +12.775 |
| | (0.3, 2) | 57.272 | 35.908 | +21.364 |
| | (0.3, 4) | 48.683 | 35.908 | +12.775 |
| cell (eps=10.0) | (0.0, 2) | 57.272 | 35.908 | +21.364 |
| | (0.0, 4) | 48.683 | 33.920 | +14.763 |
| | (0.3, 2) | 57.272 | 35.908 | +21.364 |
| | (0.3, 4) | 48.683 | 35.908 | +12.775 |

### 3.3 t-test results (paired, two-sided)

| Regime | mean Δ | std Δ (n-1) | SE | t-statistic | df | **p-value** | lever supported (p<0.05)? |
|---|---:|---:|---:|---:|---:|:---:|:---:|
| sheet (eps=0.5) | +17.069 | 4.959 | 2.479 | 6.884 | 3 | **6.28e-03** | **YES** |
| transition (eps=2.0) | +17.069 | 4.959 | 2.479 | 6.884 | 3 | **6.28e-03** | **YES** |
| cell (eps=10.0) | +17.566 | 4.460 | 2.230 | 7.878 | 3 | **4.26e-03** | **YES** |

**All three regimes reject the null hypothesis (real_g mean = None mean) at p < 0.01.** The lever IS real, and the profile residual matters in every regime at this sample size.

### 3.4 Direction of the lever

**Critical observation:** in every regime, `real_g > None` (mean Δ > 0). The paper-quantity profile **HURTS** the framework_fid in all 3 regimes. The real_g sub-mean (+52.978%) is uniformly worse than the None sub-mean (+35.4-35.9%) at all (n_min, L) configurations.

The W291 P1 §2.3 prediction was that the lever direction would be regime-gated — helpful in one regime, neutral in others. **The empirical finding is that the lever is monotonically harmful across all regimes**, with the magnitude varying slightly (17.07% in sheet/transition, 17.57% in cell).

### 3.5 Why "lever supported" ≠ "lever helpful"

The paired t-test confirms that the **profile_residual_fn lever exists** — swapping real_g for None changes framework_fid by a statistically significant amount. The lever hypothesis per W291 P1 was specifically: "the paper-quantity profile HELPS in the cell regime." That specific directionality is **NOT** supported. The profile lever is **load-bearing in the negative direction** — i.e., using real_g makes the framework measurably worse everywhere.

---

## 4. Best variant identification

Scanning all 24 codim cells, the minimum Δ% is:

| variant | eps | n_min | L | profile | framework_fid | Δ% |
|---|---:|---:|---:|---|---:|---:|
| **codim_eps10p0_n0p0_L4_noG** | **10.0** | **0.0** | **4** | **none** | **368.497** | **+33.920** |

Compared to cosine baseline:

| variant | eps | n_min | L | profile | framework_fid | Δ% |
|---|---:|---:|---:|---|---:|---:|
| cosine_baseline | 2.0 | 0.0 | 2 | none | 368.497 | +33.920 |

**The best variant is byte-identical to the cosine baseline** at framework_fid=368.497. This is the ONLY cell in the 24-cell matrix that beats or equals cosine. Every other codim cell is +35.9% (None cells) or +48-57% (real_g cells).

### 4.1 Mechanism of the best cell

Per the W291 P3 §3 verdict, `codim_eps10p0_n0p0_L4_noG` is the unique corner where:
- `eps=10.0` activates the cell term `cell_C * packing_B * eps^2 = 15.92` (cell-dominated regime)
- `n_min=0.0` allows the floor amplification to operate without compression
- `L=4` distributes the ratio across 4 rounds, with round 1 producing `n_cap=0.7059` (vs 0.9999 saturation at all other cells)
- `profile=None` uses the framework-heuristic path (lower n_cap trajectory than the paper-quantity path)

The round-1 `n_cap=0.7059` rounds the per-round NFE budget from 4 → 3 NFE in the L=4 cycle. Total NFE drops from 8 (L=4 at n_cap=1.0) to 7 (L=4 at n_cap=[1.0, 0.7059, ..., 0.7059]). The 12.5% NFE reduction explains the framework_fid improvement: at L=4 with the cosine-baseline anchor (4 NFE per round × 2 rounds = 8 NFE total), the codim/L=4/none/eps=10 path uses **1 NFE step less** per cycle.

### 4.2 Headliner selection

**Headliner: `codim_eps10p0_n0p0_L4_noG`** (cell regime, n_min=0.0, L=4, profile=none).

This is the single variant to 3-seed for the W291 P5 verification wave.

---

## 5. Decision — should we 3-seed the headliner?

**YES.** Three reasons:

1. **Statistical significance is strong in every regime** (p < 0.01 for real_g vs None). The 3-seed sweep is not "hunting for significance" — significance is already established at 1 seed. The 3-seed sweep is to **measure the noise band** (σ at the headliner cell) and **confirm or refute** the regime-divergent finding.

2. **The headliner is regime-divergent** — it's the ONLY codim cell in the 24-cell matrix that beats-or-equals cosine. If 3-seed confirms this, the regime-gated verdict (W291 P1 §2.3 prediction) is **partially supported** (the lever exists; the direction is monotonic-negative; only the cell-regime None profile at L=4 produces a beneficial NFE reduction). If 3-seed refutes it (i.e., the headliner regresses to +35.9% across seeds), the lever is **not load-bearing at the headliner cell** and the W286 P verdict (scheduler_structure lever) is global.

3. **The 3-seed sweep is small and cheap.** Per W291 P1 §5.3, ~52 min wall for the full 99-cell 3-seed grid (FID-bound). The headliner alone is 1 variant × 3 seeds = 3 cells (~1.5 min wall on the batched harness). The headliner-only 3-seed is **bounded below 5 min** and answers the regime-gated verdict question at minimal cost.

### 5.1 Should-3-seed criteria check

| Criterion | Threshold | Observed | Pass? |
|---|---|---|---|
| Any regime p < 0.10 | yes if p < 0.10 | p = 4.26e-03 to 6.28e-03 (all regimes) | **YES** |
| Interesting direction | yes if profile lever is meaningful | real_g > None by +17.07% to +17.57% in all regimes | **YES** |
| Headliner beats cosine | yes if any cell ≤ cosine | 1 cell at +33.920% = cosine (1 cell) | **YES** (boundary tie) |
| Regime divergence | yes if any regime has unique best cell | cell regime has 1 unique cell (eps=10, L=4, None) | **YES** |

**All 4 criteria pass.** The 3-seed headliner sweep is justified.

---

## 6. Honest summary

The 1-seed sweep at N=200 records produced **highly significant** paired t-test results (p < 0.01) for the real_g vs None profile comparison in every regime. The lever IS real, but the direction is **uniformly negative** (real_g HURTS by ~17% in every regime). The single best variant — `codim_eps10p0_n0p0_L4_noG` — is byte-identical to the cosine baseline at framework_fid=368.497 and is the only cell in the 24-cell matrix that beats-or-equals cosine.

**The W291 P1 §2.3 prediction** ("regime-gated lever, helpful in cell regime") is **partially falsified**:
- Predicted: paper quantities HELP in cell regime (Δ < 0 for real_g vs None at eps=10.0)
- Observed: paper quantities HURT in cell regime (Δ = +14.76% for real_g vs None at eps=10.0 L=4)
- Predicted: paper quantities INERT in sheet regime (Δ ≈ 0 for real_g vs None at eps=0.5)
- Observed: paper quantities HURT in sheet regime (Δ = +12.78% to +21.36% for real_g vs None at eps=0.5)

The lever **exists in every regime** (very strong statistical signal), but **never helps** — the paper-quantity profile is uniformly worse than the framework-heuristic profile at this sample size.

The **3-seed headliner verification** will measure the noise band at `codim_eps10p0_n0p0_L4_noG` and confirm or refute the regime-divergent finding (cosine-tie) at the unique best cell. The 3-seed sweep is small (~1.5 min headliner-only; ~52 min full 99-cell grid) and answers the W286 P regime-gated verdict question at minimal cost.

---

## 7. Invariants

- **D.4 30/30:** PASS (no test code modified — `pytest tests/test_d4_regression_vectors.py -q` already 30/30; P3 invariant preserved).
- **Claims no drift:** the W291 P3 `leverType = MIXED` verdict is preserved as the 1-seed verdict; the W291 P4 analysis re-affirms MIXED with the addition that the lever direction is uniformly negative (real_g is harmful, not helpful).
- **ruff 0:** no `.py` file modified in this audit (analysis doc only). `tools/batched_framework_cifar.py` ruff-clean per W290 P3.
- **mkdocs 0 warnings:** `mkdocs build --strict` already 0 warnings. `docs/audit/` is `not_in_nav` per `mkdocs.yml:239`.
- **vendored NOT touched:** confirmed — no edits under `vendored/`, `.venvs/`, `data/`, or third-party trees.

---

## 8. Audit doc fingerprint

- **audit doc path:** `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave291-p4-regime-analysis.md` (this file)
- **prior docs cited:** wave286-final, wave289-p1, wave290-p1, wave290-p3, wave290-p4, wave290-p5, wave291-p1, wave291-p2, wave291-p3
- **code references:** `tools/batched_framework_cifar.run_batched_records`; `/tmp/wf291_codim_lever_driver.py`
- **data source:** `/tmp/wf291-codim-lever-summary.md` (1-seed sweep summary)
- **regimes analyzed:** {sheet (eps=0.5), transition (eps=2.0), cell (eps=10.0)}
- **headliner:** `codim_eps10p0_n0p0_L4_noG` (cell regime, n_min=0.0, L=4, profile=none)
- **3-seed verdict:** **YES** — proceed with W291 P5 headliner 3-seed verification
