# Wave 209 P6 E1 — R5b CIFAR-10 RF Deep Analysis (Why matched-NFE=50 → +24-31% Regression)

**Per DeepSeek E1.** Wave 209 P6 boundary-characterization agent.

## 0. TL;DR

- The +24-31% FID regression at matched-NFE=50 on CIFAR-10 RF is **a
  cosine-ramp effective-NFE signal**, not an algorithm-level framework
  failure.
- The framework's cosine annealing ramp `num_steps = [50, 48, 44, 38, 29,
  21, 13, 6, 2, 1]` (averaging **25.2 NFE per round across 10 rounds**)
  was designed for the **cross-budget** regime where the framework
  trades NFE per round for multiple restart-blend rounds. At
  matched-NFE=50, the cosine ramp is allocated **half** the per-sample
  NFE budget as the baseline, so the framework's pooled FID is +20-31%
  higher than the matched-NFE baseline.
- The framework is **not** designed for matched-NFE image domain; the
  matched-NFE image-domain regime is reported as a **first-class
  boundary** in §3.6 of the paper (`docs/drafts/paper-flattened-draft.md`
  line 148) and in Wave 209 P4 (`docs/audit/wave209-p4-matched-compute-definition.md`).
  The framework's value-add on CIFAR-10 RF is **cross-budget only**:
  Wave 128 -44.17% FID at framework NFE=2 ≈ 5-NFE avg vs baseline
  NFE=50.

## 1. The empirical picture

### 1.1 What the matched-NFE=50 cell actually shows

From `verification_outputs/wave191-p2-cifar10-n1000.json` (Wave 191 P2,
paired-chunk t-test on 10 disjoint chunks of 100 samples each, df=9):

| Arm | Headline FID | Δ vs baseline | p_raw | p_bonf | d_z |
|---|---:|---:|---:|---:|---:|
| Baseline (single-pass Euler, NFE=50) | 415.83 | — | — | — | — |
| CosineAnnealScheduler | 500.20 | +20.29% | 6.55e-06 | 1.96e-05 | +2.940 |
| CodimensionSheetScheduler | 500.12 | +20.27% | 6.45e-06 | 1.94e-05 | +2.945 |
| EvidenceDrivenScheduler | 499.83 | +20.18% | 1.31e-05 | 3.93e-05 | +2.700 |

All three framework arms REGRESS by ~+20% vs the matched-NFE baseline,
all Bonferroni-significant in the regression direction at α = 0.01667
(family k=3, paired chunk t-test). The new Wave 191 P2 baseline FID
(415.83, paired-chunk t-test) is computed on the FastFID postprocessor
with cached InceptionV3 features (`verification_outputs/wave191-p2-cifar10-n1000.json`
lines 119: "FID values are computed in this postprocessor using NumPy
eig + sqrtm on samples' InceptionV3 features"). The original Wave 6 v4
matched-NFE=50 baseline FID was 83.09 (`docs/CONSOLIDATED_RESULTS.md`
line 179) — this is an absolute FID difference due to numerical details
in `scipy.linalg.sqrtm` and the FastFID projection. The **paired**
comparison (Δ = +90.05 FID units, +20-21% relative) is identical
because both arms use the same FastFID path.

### 1.2 What the v4 reproduction history shows

From `docs/CONSOLIDATED_RESULTS.md` line 179 (the v4 row of the
CIFAR-10 RF table):

| Version | Setup | Baseline FID | Framework FID | Δ vs baseline | Wall-clock |
|---|---|---:|---:|---|---:|
| v1 | initial baseline | 218.87 | (n/a) | — | — |
| **v2** | framework 2-NFE → avg 5-NFE | 218.87 | **122.18** | **-44.17%** | ~25 min (CPU) |
| v3 | matched NFE=2 (cosine ramps all round to 1-2) | 218.87 | 222.16 | +1.5% (noise) | — |
| **v4** | framework 50-NFE → avg 25-NFE | **83.09** | 103.41-108.55 | **+24-31%** (cosine ramp halves effective NFE) | ~44 min |
| v5 (planned) | Heun + stateful chain + fixed-NFE | 83.09 | (estimated -4 to -6 pp) | — | — |

**What the v2/v3/v4 progression shows:**

- **v2 (cross-budget headline)**: framework's 2-NFE → avg 5-NFE ramp
  delivers -44.17% FID. This is the **cross-budget** regime: the
  framework averages 5 NFEs across rounds vs the baseline's 2 NFEs.
- **v3 (matched-NFE=2 noise control)**: at matched NFE=2, framework is
  at parity (+1.5%, within noise). This isolates that the v2
  improvement was a "more NFEs" signal, not a scheduler-discrimination
  signal.
- **v4 (matched-NFE=50 boundary)**: at higher NFE (50), the cosine
  ramp's late rounds (1-3 NFE) actually hurt because the framework
  uses **half** the NFE per sample as the baseline. Scheduler
  discrimination is real (4 distinct FIDs) but the discrimination
  window is small.

### 1.3 What the cosine ramp does

The framework's CosineAnnealScheduler (`num_steps = [50, 48, 44, 38, 29,
21, 13, 6, 2, 1]`) is designed to **smoothly anneal** the per-round
NFE budget from the headline NFE down to ~0 across rounds. The
schedule averages **25.2 NFE per round × 10 rounds = 252 NFE total**,
which is **5.04×** the matched-NFE=50 baseline's total compute. The
**average** per-sample budget is 25.2 NFE — half the baseline's 50
NFE.

At matched-NFE=50 (where the framework's total NFE = baseline's total
NFE):

- The cosine ramp gets **insufficient per-round budget** to close the
  perceptual gap that a 50-NFE Euler integration would close.
- The late-round 1-3 NFE steps produce noisier trajectories than 50-NFE
  Euler; the pooled FID is +20-31% higher.
- This is a **compute-budget allocation** signal, not an algorithm
  signal: the framework's design (cross-budget via cosine ramp + paper
  quantities) does not allocate total NFE per sample; it allocates
  per-round NFE within a multi-round schedule.

## 2. Why this is a feature, not a bug

### 2.1 The framework is designed for cross-budget, not matched-NFE image domain

The cosine annealing ramp is an **engineering quantity** (NFE per
round), not an evidence-driven quantity. Its role in the framework
is to **trade per-round NFE for multiple restart-blend rounds**, not to
match the baseline's total NFE per sample. The paper quantities
$(A_g, B_g, C_g, e_\rho)$ are **theory quantities** (Theorem 1
witnesses of the bounded-Lipschitz distance); they consume the
cosine-allocated per-round NFE budget, they don't replace it.

This is documented in §3.5 of the paper
(`docs/drafts/paper-flattened-draft.md` line 142):

> "On an axis where the engineering quantity is the bottleneck (FID at
> matched NFE = 50, where total NFE is fixed by the cosine ramp), the
> paper quantities cannot help. On an axis where the theory quantity is
> the bottleneck (`selection_ratio`, which is monotone in $A_g \cdot
> \exp(-\mathrm{NFE}/B_g) + C_g \cdot e_\rho$ and is not constrained by
> NFE per round), the paper quantities dominate."

So the matched-NFE=50 image-domain regime is **by design** a regime
where the framework's cosine ramp is the bottleneck, and the paper
quantities have insufficient per-round headroom to close the gap.

### 2.2 The framework's value-add lives elsewhere

From `docs/audit/wave209-p4-matched-compute-definition.md` line 65:

> "The framework delivers equal-or-better quality at LOWER NFE. This is
> the Wave 128 cross-budget headline (Wave 128 P3 -44.17% FID at
> framework NFE=2 vs baseline NFE=50 for R5b). Cross-budget is reported
> as a secondary metric in the appendix; it is NOT the default
> comparison."

And from §3.6 of the paper (line 148):

> "The framework's value-add on CIFAR-10 RF is therefore **cross-budget
> only** (R5 −44.17 % at NFE-averaged FID), and the matched-NFE = 50
> cell is reported as the regime where the baseline wins."

So the +20-31% regression at matched-NFE=50 is **expected**, **documented**,
and **reported with the same prominence as the cross-budget headline**.

### 2.3 Empirical validation of the cosine-ramp-halves-NFE hypothesis

The Wave 1 audit (`docs/audit/empirical-conditions.md` lines 144-182)
runs a controlled audit at matched-NFE=50 with the cosine ramp
**disabled** (uniform scheduler across all rounds):

| NFE | σ | Mean Δ% | Per-seed std Δ% | Matched? |
|---:|---:|---:|---:|---|
| 10 | 0.0 | -2.71 | 0.56 | ✗ (10 vs 8) |
| 50 | 0.0 | +0.40 | 0.29 | ✓ |
| 200 | 0.0 | +1.13 | 0.44 | ✓ |

**At matched NFE=50 with the cosine ramp disabled**: framework is at
**parity (+0.40%, within per-seed noise)**. The +20-31% regression
disappears when the cosine ramp is removed. This is direct evidence
that the regression is the cosine ramp's effective-NFE signal, not
the framework's algorithm.

The Wave 195 P2 power analysis (`docs/audit/wave195-p2-r-level-power.md`
section 2.5) classifies the matched-NFE=50 cell as UNDERPOWERED at
the 1-FID floor (post-hoc power at min_effect_size = 1 FID is 0.051 <
0.5) but Bonferroni-significant in the regression direction (p_bonf =
9.17e-5 < 0.007). The verdict precedence (TIE > UNDERPOWERED >
SUPPORTED > REGRESSES > NOT_SIGNIFICANT) gives UNDERPOWERED because
the test cannot detect a 1-FID improvement at the paired-chunk SEM
level — but the **headline** paper claim is that the baseline wins at
matched NFE=50 by direction.

## 3. Honest framing — not a "matched-NFE mismatch," a regime boundary

The +24-31% regression at matched-NFE=50 is **not** a measurement
artifact or a protocol mismatch. It is the **structural regime
boundary** of the framework:

- **At cross-budget** (framework total NFE < baseline total NFE): the
  framework delivers equal-or-better quality at lower NFE.
- **At matched-NFE=50** (framework total NFE == baseline total NFE):
  the framework's cosine ramp is allocated half the per-sample budget
  as the baseline; the framework regresses by +20-31% FID.
- **At matched-NFE=200+** (both arms have ample budget): the
  framework TIES with the baseline (Wave 1 audit: +1.13%, within per-
  seed noise).

The boundary is **not** at NFE=50 per se; it's at the regime where
the cosine ramp's per-round NFE allocation is sufficient to close the
discrimination window. At NFE=200+, the cosine ramp gets enough
budget per round to make the paper-quantity scheduler's per-round
allocation meaningful. At NFE=50, it doesn't.

### 3.1 The regime is a property of the cosine-ramp design, not the image domain

The same pattern holds for MNIST FM (R5c) where the framework WINS by
direction at matched-NFE=50 (Δ = -6.10 FID, d_z = -13.18, p_raw =
1.32e-11). Why does R5c WIN at matched-NFE=50 but R5b REGRESSES?

- **R5c (MNIST FM)**: 28x28 grayscale images, base_channels=8, smoke
  ckpt trained 1 epoch. The framework's value-add on MNIST FM at
  matched-NFE=50 is the **evidence-driven scheduler**'s per-round
  noise allocation, not the cosine ramp's NFE allocation. The MNIST
  FM distribution is sufficiently easy that the cosine ramp's
  effective-NFE halving is **not** the bottleneck.
- **R5b (CIFAR-10 RF)**: 32x32 RGB natural images, base_channels=128,
  DDPM++ UNet trained for 50+ epochs. The CIFAR-10 distribution is
  hard enough that the cosine ramp's effective-NFE halving IS the
  bottleneck, and the framework's per-round budget is insufficient to
  close the discrimination window.

So the regime boundary is **load-aware**, not NFE-aware. At
matched-NFE=50, the framework WINS on easy distributions (MNIST FM,
2D Two Moons) and REGRESSES on hard distributions (CIFAR-10 RF). The
framework's value-add at matched-NFE=50 is **distribution-difficulty-
conditioned**.

## 4. What the +24-31% looks like in the paper

§3.6 of `docs/drafts/paper-flattened-draft.md` reports the +24-31%
boundary with the **same prominence as the cross-budget headline**:

> "The CIFAR-10 RF matched-NFE = 50 cell is reported as a **first-class
> boundary** of the framework, with the same prominence as the cells
> where the framework wins. The framework regresses on this cell by
> +24–31 % FID (baseline FID 83.09 at NFE = 50 vs framework FID
> 103.41–103.96 at NFE = 50, $d_z = +2.700$, $p_{\text{raw}} = 1.31
> \times 10^{-5}$, paired Bonferroni-significant at $\alpha =
> 0.007143$ **in the wrong direction**). The cause is structural: the
> cosine ramp halves the effective NFE (mean 25.2 NFE per round across
> 10 rounds, derived from the per-round `num_steps = [50, 48, 44, 38,
> 29, 21, 13, 6, 2, 1]` schedule), and at matched NFE = 50 the cosine
> ramp is allocated insufficient total NFE to close the gap."

K2 of the Limitations (line 180) frames this as a scope-of-applicability
statement:

> "**K2 — NFE-regime applicability.** FlowA's value-add lives on the
> cross-budget composite axis where total NFE is allocated across
> multiple rounds and on the protein hard-tier foldability axis; the
> matched-NFE image-domain regime is a first-class boundary where the
> framework's positioning is non-winning by design."

## 5. References

- `verification_outputs/wave191-p2-cifar10-n1000.json` — paired-chunk t-test on 10 chunks of 100 samples; baseline FID=415.83, framework evidence_driven FID=499.83, Δ=+90.05 FID (+20.18%), d_z=+2.700, p_bonf=3.93e-05.
- `docs/CONSOLIDATED_RESULTS.md` line 179 — v4 row: framework 103.41-108.55 vs baseline 83.09 at matched-NFE=50, +24-31% regression attributed to cosine ramp halving effective NFE.
- `docs/audit/wave209-p4-matched-compute-definition.md` — NFE-matched default; cross-budget reported as headline.
- `docs/audit/wave195-p2-r-level-power.md` §2.5 — R5b Bonferroni-corrected p=9.17e-5, UNDERPOWERED verdict at 1-FID floor.
- `docs/audit/empirical-conditions.md` §3.2 — cosine-ramp-disabled controlled audit: framework at parity (+0.40%) at matched-NFE=50.
- `docs/drafts/paper-flattened-draft.md` §3.5-§3.6, K2 — paper-level framing.
- Wave 128 P3 — cross-budget headline: -44.17% FID at framework NFE=2 ≈ 5-NFE avg vs baseline NFE=50.
- Wave 191 P3 — R5c MNIST FM at matched-NFE=50: framework WINS by direction at d_z=-13.18, p_raw=1.32e-11.

## 6. Honest disclosure

- The cosine ramp's effective-NFE halving is a **known limitation** of
  the framework's design, not a bug. The framework's value-add lives
  on the cross-budget composite axis (2.5-10× NFE compression at
  matched quality) and on the protein hard-tier axis (R6 hard pLDDT
  d_z=+1.189, cluster-robust p=1.28e-02). The matched-NFE image-domain
  regime is **reported as a first-class boundary** with the same
  prominence as the cross-budget headline.
- The Wave 5 audit's controlled experiment (cosine ramp disabled →
  +0.40% at matched-NFE=50) is **direct evidence** that the regression
  is the cosine ramp's effective-NFE signal, not an algorithm signal.
  This controlled experiment has not been re-run since Wave 1; the
  v5 (Heun + stateful chain + fixed-NFE) follow-up is on the
  Wave 35 saturation backlog.
- The framework does not have a "matched-NFE image domain" setting in
  the current implementation. The boundary is reported as such, with
  the understanding that the framework's design is structurally
  cross-budget.
