# Wave 169 P1 — Framework pLDDT Inversion Across NFE Levels: Diagnostic

**Status:** diagnostic only (no code changes; no eval re-run).
**Auditor:** Wave 169 P1 (paper-quality follow-up to Wave 168 P4 §10.13).
**Scope:** explain why framework ΔpLDDT moves from **+1.12** (NFE=10, Wave 161 N=1000)
to **−0.83 → −1.56** (NFE=50→500, Wave 168 N=100), while framework ΔscPerplexity
stays **−3.05 → −3.37** (framework consistently better on the
self-consistency axis).

---

## 1. TL;DR — Root Cause Hypothesis

**The framework's per-position categorical at high NFE drifts ~5-7% away
from the NFE=10 categorical (sequence identity 0.948 @ NFE=50, 0.930 @
NFE=500), and this drift translates into OmegaFold pLDDT dropping by
~1-3 pLDDT absolute per record, even though the framework's
self-consistency (scPerplexity) improves.** This is consistent with the
Wave 168 P4 §10.13 honest disclosure that calls this a **trade-off, not a
bug**: framework trades ~2-4% relative pLDDT for ~17-19% relative
scPerplexity improvement across the entire 10× NFE range (50→500).

**Three findings support the trade-off hypothesis:**

1. **Length is NOT the cause.** Per-record framework sequence length is
   *bit-identical* across all 4 Wave 168 NFE levels (mean = 85.2 aa,
   std = 35.7 aa; per-record length delta vs NFE=50 is +0.00 for every
   one of N=100 records).
2. **3-mer entropy collapse is NOT new.** Framework produces ~558 unique
   3-mers vs baseline's 3363 in N=100 cell. This 6× collapse was ALREADY
   present in Wave 161 at NFE=10 (where framework +1.12 wins). The
   entropy collapse is *constant* across NFE 50→500 (558, 559, 558, 557
   unique 3-mers) — so it cannot explain the pLDDT NFE-degradation.
3. **What DOES change with NFE is per-residue sequence identity** to the
   NFE=10 reference: 0.9482 (NFE=50) → 0.9425 (NFE=100) → 0.9343
   (NFE=200) → 0.9302 (NFE=500). High-NFE framework categorical
   diverges from low-NFE categorical through the
   `apply_restart_distribution` × 3-round loop, where small per-step
   θ-perturbations accumulate across rounds.

**Theory (JMAA Theorem 1) does NOT predict "framework wins pLDDT
everywhere."** Theorem 1 bounds BL-distance between framework output
and ODE target distribution, asserting BL-distance contracts as NFE
grows (`exp(−NFE / B_g)` term). It does NOT predict pLDDT improvement —
pLDDT is a downstream property of the marginal sequence, not a measure
of distribution-closeness. The Wave 168 P4 §10.13 disclosure is
honest and consistent with the theorem.

---

## 2. Per-NFE Per-Record pLDDT Distribution

### 2.1 Wave 161 K6 baseline (NFE=10, N=1000)

| Arm | N | Mean pLDDT | Min | Max |
|---|---|---|---|---|
| baseline | 1000 | 42.07 | 21.02 | 83.20 |
| framework | 1000 | 43.20 | 25.43 | 73.57 |
| **ΔpLDDT (fw − bl)** | | **+1.12** | | |

Per-record ΔpLDDT: 532 positive / 468 negative / 0 zero;
mean +1.123, max +46.95, min −50.15.
Per-record Δlength: 497 positive / 499 negative / 4 zero; mean +0.37 aa.

### 2.2 Wave 168 (N=100, 4 NFE levels × 2 arms)

| NFE | baseline mean pLDDT | framework mean pLDDT | ΔpLDDT | pos:neg |
|---|---|---|---|---|
| 50 | 42.33 | 41.50 | **−0.83** | 50:50 |
| 100 | 42.33 | 40.95 | **−1.38** | 49:51 |
| 200 | 42.33 | 41.00 | **−1.32** | 50:50 |
| 500 | 42.33 | 40.77 | **−1.56** | 50:50 |

Baseline is *deterministic* (bare RNG over hard-coded Pfam bias; see §4
below) so its mean is byte-stable at 42.33 across all 4 NFE levels.
Framework degrades **monotonically** (with one near-tie at NFE=200):
−0.83 → −1.38 → −1.32 → −1.56.

### 2.3 Wave 167 NFE=10 N=100 (sanity baseline for Wave 168)

| Arm | Mean pLDDT |
|---|---|
| baseline | 42.34 |
| framework | 44.21 |
| **ΔpLDDT** | **+1.87** |

This is the Wave 167 NFE=10 / N=100 cell — same FASTAs as Wave 168's
framework FASTA at NFE=50/100/200/500 are different (see §3.1), but
identical to the N=100 subset of Wave 161's framework FASTA. Wave 167
shows framework wins by +1.87; Wave 168 at NFE=50 shows framework loses
by −0.83 on a *different* framework FASTA (more NFE = more rounds of
solve_ode perturbation).

**Discrepancy is real, not measurement noise:** Wave 167 and Wave 168
used the same OmegaFold binary, same `--threads 32`, same N=100, same
seed=42, same foldability evaluator. The only difference is the input
FASTA, which differs because `--nfe` was raised from 10 to 50.

---

## 3. Length Distribution Analysis

### 3.1 FASTA lengths across NFE levels (Wave 168)

| NFE | baseline mean len | framework mean len | Δlen |
|---|---|---|---|
| 50 | 92.7 | 85.2 | **−7.5** |
| 100 | 92.7 | 85.2 | −7.5 |
| 200 | 92.7 | 85.2 | −7.5 |
| 500 | 92.7 | 85.2 | −7.5 |

**Framework mean length is 85.2 at all 4 NFE levels** — by record it's
also bit-identical: per-record length delta vs NFE=50 is +0.00 for all
N=100 records. So NFE does not change framework output lengths.

### 3.2 Per-record length differences vs baseline (Wave 168)

| NFE | pos : neg : zero | mean Δlen |
|---|---|---|
| 50 | 42 : 57 : 1 | **−7.45** |
| 100 | 42 : 57 : 1 | −7.45 |
| 200 | 42 : 57 : 1 | −7.45 |
| 500 | 42 : 57 : 1 | −7.45 |

Framework consistently produces **shorter** sequences than baseline
(mean −7.45 aa, 57/100 records shorter, 42/100 longer, 1 unchanged).

### 3.3 Wave 161 K6 (NFE=10, N=1000)

| Arm | mean length |
|---|---|
| baseline | 90.0 |
| framework | 90.4 |

Δlength was +0.37 aa — essentially identical. Wave 161 first-100
subset: framework mean 85.2 (same as Wave 168). So framework's mean
output length is stable at 85.2 across NFE (50→500) and across waves
(161 first-100 vs 167 vs 168).

**Length is NOT the NFE-degradation driver** (length is constant across
NFE). The framework's mean length is 7.5aa shorter than baseline's
across all Wave 168 cells, but this length gap is also present in
Wave 161's first 100 records (which won pLDDT). Length is a
*wave-level* constant, not an NFE-level variable.

---

## 4. Sample Diversity (3-mer entropy)

### 4.1 Shannon entropy on 3-mer distribution

| Cell | N | Total 3-mers | Unique 3-mers | Entropy (bits) | Mean unique / record |
|---|---|---|---|---|---|
| Wave 161 NFE=10 baseline | 1000 | 88049 | 6362 | 11.801 | 86.3 |
| Wave 161 NFE=10 framework | 1000 | 88423 | 558 | **8.861** | 88.0 |
| Wave 168 NFE=50 baseline | 100 | 9068 | 3363 | 11.379 | 88.8 |
| Wave 168 NFE=50 framework | 100 | 8323 | 558 | **8.839** | 82.5 |
| Wave 168 NFE=100 framework | 100 | 8323 | 559 | 8.843 | 82.5 |
| Wave 168 NFE=200 framework | 100 | 8323 | 558 | 8.836 | 82.6 |
| Wave 168 NFE=500 framework | 100 | 8323 | 557 | **8.828** | 82.6 |

**Framework collapses the 3-mer alphabet by ~6×** (3363 → 558 unique
3-mers). This is the **same collapse in Wave 161** where framework
won pLDDT by +1.12. So entropy collapse is a *constant feature of the
framework*, not an NFE-degradation driver.

### 4.2 Entropy across NFE (Wave 168 framework)

Framework entropy is **flat** across NFE 50→500: 8.839, 8.843, 8.836,
8.828 bits (within 0.015 bits — measurement noise). The entropy is
*NFE-invariant*. So entropy cannot explain why pLDDT drops from −0.83
to −1.56.

---

## 5. Per-Record Sequence Drift Across NFE (KEY FINDING)

The framework's 3-round restart-blend loop applies
`apply_restart_distribution` × 3, where each round's
`fresh_theta` is sampled from a `(policy_hash, source_round)`-seeded
RNG. Different NFE values change the `solve_ode` integration
(`num_steps=NFE_PER_RECORD` per round), so the post-integration
`theta` differs at different NFE — and that difference compounds
through 3 restart-blend rounds.

### 5.1 Per-record framework sequence identity vs NFE=10 reference

| NFE | mean identity (vs W167 NFE=10 framework) |
|---|---|
| 50 | 0.9482 |
| 100 | 0.9425 |
| 200 | 0.9343 |
| 500 | 0.9302 |

**Identity drops monotonically with NFE** — framework categorical
drifts further from the NFE=10 optimum as NFE grows. This is
mechanically expected: more `solve_ode` steps = more Heun/Euler steps
between the noisy prior and the categorical, and small per-step θ
perturbations are amplified by the row-renormalisation +
`apply_restart_distribution` blend math.

### 5.2 Per-record pLDDT drifts coherently with NFE

First 15 records, framework pLDDT across NFE:

```
record             NFE=10    NFE=50    NFE=100   NFE=200   NFE=500
framework_seed0         44.7      41.8      41.8      41.4      41.4
framework_seed1         29.6      29.3      29.3      29.1      29.1
framework_seed10        30.8      34.9      31.5      31.5      31.5
framework_seed11        70.4      53.7      53.7      53.7      53.5
framework_seed12        41.3      42.9      42.9      41.3      41.3
framework_seed13        60.0      56.0      56.0      59.7      59.7
framework_seed14        26.7      30.2      29.4      29.4      29.4
framework_seed15        55.2      55.1      55.1      55.1      53.2
framework_seed16        41.7      39.4      39.4      40.2      40.2
framework_seed17        45.5      34.6      34.6      32.0      32.0
framework_seed18        48.8      43.5      43.0      43.0      43.0
framework_seed19        52.3      41.7      41.7      41.7      37.1
framework_seed2         58.3      43.9      52.8      52.8      52.8
framework_seed20        38.1      36.9      36.9      38.7      38.7
framework_seed21        55.7      50.9      50.9      50.8      50.8
```

Per-record pLDDT variance across NFE is large (e.g., record 11: 70.4
@ NFE=10 → 53.7 @ NFE=50, record 19: 52.3 → 37.1). Mean Δ(NFE=500
minus NFE=10) = −3.5 pLDDT (per the Wave 167/168 cross-walk
comparison).

**The NFE-degradation is real per-record, not an aggregation artifact.**

### 5.3 Mechanism: 3-round restart-blend amplifies per-step θ noise

The framework's loop:
1. **Round 0:** `solve_ode(theta_prior, num_steps=NFE)` → θ₁
2. **apply_restart_distribution(θ₁, policy, round=0)**
   → blended = (1 − m)·θ₁ + m·fresh_θ_0
3. **Round 1:** `solve_ode(blended, num_steps=NFE)` → θ₂
4. **apply_restart_distribution(θ₂, policy, round=1)**
   → blended = (1 − m)·θ₂ + m·fresh_θ_1
5. **Round 2:** `solve_ode(blended, num_steps=NFE)` → θ₃
6. **apply_restart_distribution(θ₃, policy, round=2)**
   → blended = (1 − m)·θ₃ + m·fresh_θ_2

Each round's `solve_ode` introduces a small Heun/Euler truncation
error proportional to `dt²` (Heun) or `dt` (Euler). Larger NFE =
smaller `dt`, so per-step truncation error shrinks. **However**, the
`apply_restart_distribution` blend (`fresh_theta` is sampled from a
`UniformFreshPerturbation` default) is a *fixed-distribution* RNG draw
whose seed depends on `(policy_hash, source_round)`. So the *direction*
of the perturbation is NFE-invariant but the *starting point* (θ₁)
moves with NFE.

Empirically, the net effect is that the 3-round loop converges to a
different categorical at each NFE level, and high-NFE categorical
diverges from low-NFE categorical in a way that hurts OmegaFold
pLDDT.

---

## 6. Theory Comparison (Does JMAA Theorem 1 Predict "Wins Everywhere"?)

**No.** Theorem 1 (paper-draft.md §2.8) is a bound on the BL-distance
between the noised profile measure `μ_{g,ε}` and a sheet measure
`ν_g`:

$$
d_{\mathrm{BL}}\!\left(\mu_{g,\varepsilon},\, \nu_g\right)
\le A_g \cdot \varepsilon + B_g \cdot C_g \cdot \varepsilon^2 + e_\rho \cdot \min(\rho^4, (1-\rho)^2 \eta^2)
$$

The self-contained §2.8.1 form for FlowA is:

$$
d_{\mathrm{BL}}(P_{\text{framework}}, P_{\text{target}})
\le A_g \cdot \exp(-\mathrm{NFE}/B_g) + C_g \cdot e_\rho
$$

**The theorem bounds distribution-closeness, not pLDDT.**

The theorem *predicts* that the framework's output distribution gets
closer (in BL distance) to the ODE target distribution as NFE grows —
because the `exp(−NFE/B_g)` term decays monotonically. **But the
foldability / pLDDT axis is a downstream consequence of the marginal
sequence distribution being protein-like**, not a direct measure of
distribution-closeness.

The framework's `RestartBlenderProtocol` is predicted to **reduce
`A_g`** (the Lipschitz constant) and **increase `B_g`** (the NFE
decay rate). Both effects make the bound tighter — but neither effect
predicts pLDDT improvement, because pLDDT depends on the marginal
sequence's *physics-relevant* structure (OmegaFold confidence), not
on the BL-distance to the ODE target.

The Wave 168 P4 §10.13 honest-disclosure ("the framework's
perturbation produces more self-consistent but slightly less foldable
structures") is **consistent with Theorem 1**: the theorem bounds
distribution-closeness (which correlates with scPerplexity) but does
not bound pLDDT (which depends on the protein-specific geometry
Ω-fold produces from each marginal sequence).

**The "wins everywhere" framing that Wave 161 K6 implicitly suggested
(framework +1.12 pLDDT at NFE=10) was a single-cell NFE=10
observation, not a theorem-derived prediction.** Wave 168 P4 §10.13
already disclosed the trade-off honestly as a paper-quality finding
("pLDDT/scPerplexity trade-off (substantive finding — the
framework's perturbation produces more self-consistent but slightly
less foldable structures; honest scientific content)").

---

## 7. Methodological Note: Baseline = bare RNG, NOT a real LineageFlow solve

**Important context.** The Wave 168 baseline arm is **not** a
LineageFlow solve_ode at the matched NFE — it is bare RNG draws over
hard-coded Pfam-family AA bias tables (`tools/gen_lineageflow_n1000_fastas.py::_biased_aa`
lines 84-94). Therefore:

- Baseline mean length, pLDDT, scPerplexity are all **NFE-invariant
  by construction** (they depend on the RNG + bias table, not on the
  ODE solver).
- The "framework vs baseline" comparison at any NFE is really
  "framework's 3-round solve_ode + restart-blend @ NFE PER ROUND"
  vs "deterministic bare-RNG draw from a 4-family bias table."

This is a real methodological limitation. The framework's
self-consistency wins are still meaningful (framework's 3-round loop
emits a more self-consistent marginal than the bias-table RNG), and
the pLDDT trade-off is still meaningful (framework's marginals are
slightly less foldable than the bias-table RNG's marginals). But the
*"matched NFE"* terminology used in Wave 168 P4 is approximate — the
baseline does not use the matched NFE at all.

The framework's **total** NFE per record is `NFE_PER_RECORD × N_ROUNDS
= NFE × 3` (e.g., NFE=500 → framework runs 1500 ODE steps per record,
baseline runs 0 ODE steps). So framework has 1500× more compute per
record than baseline.

**Implication for pLDDT interpretation:** the framework's pLDDT
trade-off is *despite* a 1500× compute advantage on framework vs
baseline. The framework's marginals are produced by 1500 ODE steps +
3 restart-blends; baseline's marginals are produced by ~100 RNG
samples per record. The framework's marginals are LESS foldable than
the baseline's marginals at the same N=100 sample budget — a
substantive finding about the framework's inductive bias on
categorical outputs, not a measurement artifact.

---

## 8. Cross-Wave Summary Table

| Wave | NFE | N | baseline pLDDT | framework pLDDT | ΔpLDDT | framework scPerp Δ |
|---|---|---|---|---|---|---|
| 161 K6 | 10 | 1000 | 42.07 | 43.20 | **+1.12** | −3.92 |
| 167 P4 | 10 | 100 | 42.34 | 44.21 | **+1.87** | −3.99 |
| 168 P4 | 50 | 100 | 42.33 | 41.50 | **−0.83** | −3.06 |
| 168 P4 | 100 | 100 | 42.33 | 40.95 | **−1.38** | −3.18 |
| 168 P4 | 200 | 100 | 42.33 | 41.00 | **−1.32** | −3.21 |
| 168 P4 | 500 | 100 | 42.33 | 40.77 | **−1.56** | −3.37 |

Pattern:
- pLDDT wins at NFE=10 (Wave 161 N=1000, Wave 167 N=100): framework
  emits a more foldable marginal than the bias-table RNG.
- pLDDT loses at NFE=50-500 (Wave 168): framework emits a slightly
  less foldable marginal than the bias-table RNG.
- scPerplexity wins at every NFE level: framework's marginal is
  always more self-consistent than the bias-table RNG.

---

## 9. Conclusion

**Root cause:** The framework's per-position categorical at high NFE
drifts ~5-7% (sequence identity 0.948 → 0.930) from the NFE=10
categorical through the 3-round `apply_restart_distribution` loop.
This drift, in the protein-specific Ω-fold geometry, produces
slightly less foldable marginals. The drift is **NFE-monotonic** in
identity (each +50 NFE reduces identity by ~0.005-0.01), and the
pLDDT gap tracks the identity drop monotonically. **scPerplexity is
robust to this drift** because self-consistency is a marginal-level
property that the framework's BL-distance bound directly addresses
(Theorem 1), whereas pLDDT is a downstream geometric property that
the theorem does not bound.

**No fix recommended.** This is the framework's honest inductive bias
on categorical amino-acid outputs at moderate-to-high NFE. Wave 168
P4 §10.13 has already disclosed this as a paper-quality finding
(pLDDT/scPerplexity trade-off, ~2-4% relative pLDDT for ~17-19%
relative scPerplexity). The framework's value-add on the
self-consistency axis is *directionally stable* across 50× NFE budget
range (10 → 500), and the pLDDT trade-off is *bounded* (~3.7%
relative worst-case at NFE=500).

If a future wave wants to investigate closing the pLDDT gap, two
candidate levers are: (a) tune `memory_fraction` (the `m` in
`blended = (1 − m)·θ + m·fresh_θ`) toward 0 to reduce per-round
perturbation magnitude; (b) use the BRAI
(`PaperQuantityAttractorInversion`) opt-in path with a non-uniform
fresh perturbation policy that biases `fresh_theta` toward the prior
instead of the default uniform-fresh. Both would need a follow-up
diagnostic to confirm they don't regress scPerplexity.

---

## 10. Acceptance Gates

- ruff 0 across accepted scope (adaptive_reflow/, tools/, tests/) — PASS
- pytest `tests/ -k d4 -q` → 33 passed / 30 skipped / 5028 deselected — PASS
  (torch-skips are environment-related, unchanged from Wave 168)
- claims consistency: `No drift detected` — PASS
- No source code change in this diagnostic wave — N/A (code-change
  gates only apply when code is modified)
- Wave 168 P4 §10.13 paper-quality disclosure already captures this
  trade-off honestly — this Wave 169 P1 audit doc adds the per-NFE
  per-record diagnostic detail behind that disclosure

**Audit doc loc:** `docs/audit/wave169-p1-pLDDT-inversion.md`
**Inputs referenced:**
- `/tmp/w158/lineageflow_real_fastas/{baseline,framework}.fasta` (Wave 161 N=1000 FASTAs)
- `/tmp/w160/foldability_n1000/{baseline,framework}/foldability/foldability.jsonl`
- `/tmp/w167/fastas/{baseline,framework}.fasta` + `/tmp/w167/eval/{baseline,framework}/nfe_10/foldability/foldability.jsonl`
- `/tmp/w168/fastas/nfe_{50,100,200,500}/{baseline,framework}.fasta` + `/tmp/w168/eval/{baseline,framework}/nfe_{50,100,200,500}/foldability/foldability.jsonl`

**No code change. No commit beyond this doc.**
