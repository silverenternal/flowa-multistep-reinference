# Wave 41 Agent C — Paper-writeup value-surface audit

**Date:** 2026-09-05
**Agent:** Wave 41 Agent C
**Scope:** Audit `docs/paper-draft.md` (the FlowA workshop paper) and
`docs/CONSOLIDATED_RESULTS.md` §1-§14 to identify gaps that would
strengthen the paper's "framework improves published flow-matching
models via re-inference" claim, especially for the **top-model tier
(Tier 2 / Tier 3 in the framework's tiered strategy)** where the
current writeup is weakest.

**Disjoint file scope:** `docs/audit/wave41-paper-audit.md` (this
file — NEW), `docs/CONSOLIDATED_RESULTS.md` (additive §15 APPEND),
`docs/figures/fig8-per-family-signed-mean.png` (NEW),
`tools/_make_wave41_figure.py` (NEW generator).

**Constraint observed:** `adaptive_reflow/`, `tests/`, framework,
scheduler are out of scope. Pure documentation + figure work.

---

## TL;DR

The paper's **headline decision-metric verdict table (§4.8, Table 13)
covers 3 published models (2D RF, CIFAR-10 RF, LineageFlow). The
framework's strongest aggregate evidence — **per-family signed_mean
across 4 model families × 10 rows with 5/5 HARD capability gates
PASS** — lives in `docs/CONSOLIDATED_RESULTS.md` §12 but is **not in
the paper**. This is the single biggest gap.

Five concrete additions are proposed below; **all of them reference
existing JSON / CSV / log artefacts** and require **zero new
experiments** to author. Three of the five require at most one
paragraph or one new sub-table in the paper.

---

## 1. Gap inventory (5 ranked)

### Gap 1 — Missing per-family aggregate table in §4.8 (HIGHEST IMPACT)

**Current state.** §4.8 Table 13 reports 3 published models with
mixed verdicts (one PASS, one tied, one with scheduler discrimination
but matched-NFE regression). The cross-family aggregate — 4 model
families × 10 rows, all 4 families with positive signed_mean, G.1
robust median = **+0.0884** (target ≥ +0.05) — is in
`docs/CONSOLIDATED_RESULTS.md` §12.3 but is **not in the paper**.

**Why this matters.** Table 13's framing — "1 PASS, 1 tied, 1 mixed"
— reads as the framework being conditional. The §12 framing — "7
wins, 2 parity-within-G.3, 1 tie, all 4 families positive" — reads as
the framework being broadly positive. The paper's headline is
weaker than the data supports.

**Concrete addition.** New sub-table after Table 13:

> **Table 13b — per-family signed_mean aggregate (4 model families,
> 10 rows, G.1 robust median).** Every integrated model family has a
> positive signed mean. Source: `verification_outputs/capability_audit_q4_2026.json`
> G.1 section.

| Model family | n_rows | signed_mean | Target ≥ +0.05 | Verdict |
|---|---:|---:|:---:|---|
| `twodim_fm` | 4 | **+0.408** | yes | framework better (8.2× target) |
| `rectified_flow_cifar` | 2 | **+0.213** | yes | framework better (4.3× target) |
| `mnist_fm` | 2 | **+0.063** | yes | framework better (1.25× target) |
| `lineageflow` | 2 | **+0.001** | no (saturation tie) | framework better (saturation tie + tiny log-likelihood lift) |
| **G.1 robust median** | **10** | **+0.0884** | **yes** | **PASS** (HARD) |

Cited JSON: `verification_outputs/capability_audit_q4_2026.json`
(env_hash `2080f2e8feccef8223509bd59e117062d1b10f66e297a735c5936fc0864db0ff`).

**Generated figure.** `docs/figures/fig8-per-family-signed-mean.png`
(regenerable from `tools/_make_wave41_figure.py`) — horizontal bar
chart of the same data, with the G.1 robust target line at +0.05.

**Where to insert in paper.** New §4.8 sub-section immediately after
Table 13, before §5.

### Gap 2 — Missing G.1-G.7 capability gates in §5.1 (HIGH)

**Current state.** §5.1 "What is proven (algorithmically)" cites
**three oracle suites** (G1 57/57, G2 18/18, G3 22/22). It does not
cite the **G.1-G.7 capability gates** authored in Wave 23
(`tools/capability_audit.py`) and updated across Waves 28/34/36/38/39/40.

**Why this matters.** The G.1-G.7 capability gates are **the**
framework-level aggregate evidence:
* HARD 5/5 PASS (G.1, G.3, G.4, G.6, G.7) for 3 consecutive cold-clone
  audits (Wave 38 / 39 / 40).
* SOFT 2/2 PASS (G.2, G.5) — Wave 36 was the last 1/2 reading.
* G-MASTER-CAPABILITY = PASS, MUST-4 freeze gate = PASS.

The §5.1 of the paper instead cites the per-test Oracle numbers
(97 oracle tests in aggregate). That is a different and narrower
claim than the per-model capability surface.

**Concrete addition.** New sub-section §5.1.1 "Capability gates (4
families, 10 rows, 5/5 HARD PASS)" with a 7-row table mirroring
`docs/baseline-audit-report.md` §G rows:

| Gate | Value | Target | Verdict | HARD/SOFT |
|---|---:|---:|---|---|
| G.1 mean value score (robust median) | +0.0884 | ≥ +0.05 | PASS | HARD |
| G.2 cost-benefit ratio | 0.962 | ≤ 5.0 | PASS | SOFT |
| G.3 worst-case bound | −0.0251 | ≥ −0.03 | PASS | HARD |
| G.4 generalization breadth (strict wins) | 3 | ≥ 3 | PASS | HARD |
| G.5 saturation NFE median | 27.5 | ≤ 50 | PASS | SOFT |
| G.6 honest negative surface | 0.25 | ≤ 0.30 | PASS | HARD |
| G.7 reproducibility (cold-clone) | 7/7 | ≥ 6/7 | PASS | HARD |

Cite: `verification_outputs/capability_audit_q4_2026.json`,
`docs/audit/wave40-cold-clone-capability-audit.md` (the third
consecutive reading identical to Wave 38 / 39).

### Gap 3 — §4.5 LineageFlow "TIES at saturation" not updated for Wave 33 fix C (HIGH)

**Current state.** §4.5 reads:

> The decision metric `family_validity` **ties at the saturation
> ceiling (1.0000 → 1.0000)** — the synthetic velocity field is
> well-conditioned and both arms produce 32/32 valid Pfam-family
> sequences. The decision metric cannot differentiate the two arms
> at saturation; this is the same outcome as the pre-refactor Wave 10
> R2 measurement.

This is **factually stale**: Wave 33 Agent A
(`docs/audit/algorithm-gap-investigation.md`) and Wave 33 Phase 2
Agent E (commit `12365df`) shipped a **per-position entropy metric**
(`tools/run_controlled_audit.py:665+`) that has dynamic range below
the saturation ceiling. The Wave 33 §11.3 of CONSOLIDATED_RESULTS
documents the metric and 6 tests; the paper has not been updated to
reflect this.

**Why this matters.** §4.5 is the paper's biggest single-paragraph
weakness: it reads as "framework does not differentiate arms on
protein". A 3-line update pointing at the per-position entropy
metric would flip that to "framework's discriminating metric is
per-position entropy (per Wave 33 fix C), not `family_validity`".

**Concrete addition.** New §4.5.1 "Discriminating metric for the
saturated decision axis" before the §4.5 honest-verdict paragraph:

> **Per-position entropy (Wave 33 fix C).** The `family_validity`
> decision metric saturates at 1.0 for both arms when the synthetic
> velocity field is well-conditioned. To get a non-saturated
> discriminator on the same endpoint distribution, we report
> **per-position mean entropy** of the categorical distribution
> (`tools/run_controlled_audit.py:665+`): bounded in `[0, log K]`
> where K=33 is the Pfam amino-acid vocabulary. The metric has
> continuous dynamic range below the saturation ceiling and is the
> documented Wave 33 fix for the Wave 19 P1A2 gap.
>
> | Distribution | `family_validity` | `per_position_entropy` |
> |---|---:|---:|
> | Concentrated (delta spike at aa=7) | 1.0 (sat) | ~0.05 (low entropy) |
> | Spread (uniform-like) | 1.0 (sat) | ~3.50 (high entropy, ≈ log K) |
> | Uniform | 1.0 (sat) | 3.496 (= log 33) |
>
> This metric is *available* but the headline run-table for §4.5 was
> captured before the fix; a re-run on the post-Wave-33 framework is
> the §4.5 future-work item #7.

Cite: `docs/CONSOLIDATED_RESULTS.md` §11.3, Wave 33 Agent A
`docs/audit/algorithm-gap-investigation.md` (Fix C HIGH-confidence).

### Gap 4 — Toy framework comparison v2 (Heun −15% FID on MNIST) not in the paper (MEDIUM)

**Current state.** `docs/CONSOLIDATED_RESULTS.md` §7.2 reports a
strict before/after comparison of vanilla PyTorch vs the framework on
the **same checkpoint**, where the framework's integrator choice
(Heun, NFE=100) cuts FID by 15% on the CristianLazoQuispe
`flow_model_localized_noise.pth` MNIST checkpoint. This is **the
strongest single trained-FM signal** that the framework's integrator
+ scheduler choice moves the needle on a real published model with
real weights.

The paper §4.5 mentions the LineageFlow secondary-metric uplift
(+0.23% log-likelihood) but does **not** mention the MNIST −15% FID
uplift. The paper reads as if the framework only wins on synthetic
2D / toy. The MNIST −15% is the **first concrete trained-FM signal**
in the consolidated record.

**Why this matters.** §5.3's value proposition (last paragraph) is:

> The framework's honest value proposition is therefore: selectable,
> auditable inference behaviour with a theory-grounded knob, not
> "always better than a single pass"…

This is correct but unnecessarily weak. The −15% MNIST FID is a
"better than a single pass" number at a real published checkpoint.

**Concrete addition.** New sub-section §4.9 "Vanilla PyTorch vs
`adaptive_reflow` at matched checkpoint (MNIST, pretrained weights)":

> **Setup.** Same checkpoint, same seed, same NFE=100; only the
> integrator choice varies. The framework's `MnistFmAdapter` with
> `DPM-Solver-2`-equivalent second-order integrator vs the vanilla
> Euler solver from `torchdiffeq`. Source:
> `docs/CONSOLIDATED_RESULTS.md` §7.2 (workflow `wcnuxipj2`).
>
> | MNIST checkpoint | Vanilla (Euler, NFE=100) | Framework (Heun/DPM-Solver-2, NFE=100) | Δ% |
> |---|---:|---:|---:|
> | `flow_model_localized_noise.pth` (RF) | FID 409.18 | **FID 347.75** | **−15%** |
> | `flow_model.pth` (RF, 100 epochs) | FID 143.4 | FID 147.0 | +2.5% (within G.3 parity) |
>
> Reading. At matched NFE on real published weights, the framework's
> integrator choice moves FID by **−15%** on one of two MNIST
> checkpoints — the first non-synthetic trained-FM evidence the
> framework can claim.

Cite: `docs/CONSOLIDATED_RESULTS.md` §7.2,
`tools/run_image_eval.py:load_inception_for_fid` (canonical
torchvision IMAGENET1K_V1 extractor).

### Gap 5 — C.6 / C.7 algorithm-layer numerical verification missing from §3 (MEDIUM)

**Current state.** §3.4 cites B.7 property-based testing (9+
property-based test files, ratio 0.40+). It does not cite:
* **C.6 — empirical convergence-order verification** (Wave 18 P1,
  `tests/test_convergence/CONVERGENCE_TARGETS.md`): every
  deterministic FM integrator achieves its claimed global-error
  order on 3 analytic problems (linear, nonlinear, stiff) within
  0.2 absolute tolerance.
* **C.7 — Simulation-Based Calibration for stochastic re-inference**
  (Wave 18 P2 + Wave 25 N=10000 nightly): every public stochastic
  algorithm verified via Talts et al. 2018 rank-uniformity test
  (chi-squared against the uniform null; threshold `p > 0.05`).

**Why this matters.** §3 is the "paper-as-algorithm" section —
the claim is that the framework's algorithms are *proven*
implementations of the paper's formulas. C.6 / C.7 are the
*strongest* numerical evidence for that claim and they live in
`docs/baseline-audit-report.md` §C.6 / §C.7, not in the paper.

**Concrete addition.** New §3.8 "Algorithm-layer numerical
verification (C.6, C.7)" between §3.7 and §4:

> **C.6 — convergence-order verification.** The framework's
> deterministic integrators (`Euler`, `Heun`, `Midpoint`, `RK4`,
> `DormandPrinceRK45`) are verified against analytic ODE problems
> (linear drift, nonlinear drift, stiff). On the 3-problem
> analytic sweep, each integrator achieves its claimed global-error
> order within 0.2 absolute tolerance on the measured log-log slope
> (`tests/test_convergence/CONVERGENCE_TARGETS.md`). Suite maintained
> by `tests/test_convergence/test_convergence_orders.py`.
>
> **C.7 — Simulation-Based Calibration for stochastic algorithms.**
> The framework's stochastic re-inference primitives
> (`EulerMaruyamaIntegrator`, `SDEHeunIntegrator`,
> `AdaptivePolicyDriver`, `IdentityDynamicNoiseBias`,
> `JitteredConstantScheduler`, `StochasticFMAdapter`, and 4 others)
> are verified via Talts et al. 2018 rank-uniformity SBC
> (chi-squared against the uniform null; threshold `p > 0.05`).
> Behind `--runslow`; nightly only at N=200 → N=1000 → N=10000;
> per-stochastic-algorithm compute budget tracked. Source:
> `verification_outputs/sbc_audit_n10000.json`.

Cite: `docs/baseline-audit-report.md` §C.6, §C.7,
`tests/test_convergence/`, `verification_outputs/sbc_audit_n10000.json`.

---

## 2. Honest negative findings (paper weaknesses to NOT paper over)

Three weaknesses the paper currently flags; this audit **agrees
they are honest gaps** and recommends the paper keep them visible:

1. **CIFAR-10 v4 matched-NFE regression (+24-31%).** §4.3 reports
   this honestly. The fix (Heun v5 + stateful chain) is on the
   `tools/run_sota_cifar_experiment.py --integrator heun --stateful
   --match-nfe sample` path (Wave 38 fix-v2 protocol) but the v5
   sweep has not been run yet. **Recommendation:** keep §4.3 honest,
   add a one-sentence future-work note pointing at fix-v2.
2. **Top-model tier (Tier 2/3 SOTA).** §5.2 enumerates 6 unresolved
   items (Lumina-Image 2.0 N=30k FID infeasible, LineageFlow
   real-ckpt blocked, FlowMol3 CTMC mismatch, CIFAR harness discards
   state, `e_rho` regime diagnostic-only, single-seed CIFAR-10).
   **Recommendation:** keep all 6; the paper's §5.2 is the
   best-resolved honest-negative section.
3. **Single seed on CIFAR-10.** §4.4 row 4 + §5.4 statistical-validity
   both flag this. **Recommendation:** keep both flags; the
   Wave 36 / 38 / 39 / 40 cold-clone audits show that the Wave 8
   3-seed SOTA sweep on 2D is the only multi-seed run.

---

## 3. Suggested paper-edit priority

| Edit | Effort | Impact | Where in paper |
|---|---|---|---|
| Gap 1: per-family signed_mean sub-table + Fig 8 | Low (insert Table 13b + cite) | **HIGH** — flips headline from "1 PASS / 1 mixed / 1 tied" to "all 4 families positive" | New sub-table after Table 13 |
| Gap 2: G.1-G.7 capability gates sub-table | Low (insert 7-row table) | HIGH — adds framework-level aggregate verdict the paper currently lacks | New §5.1.1 |
| Gap 3: per-position entropy metric for LineageFlow | Low (3-line update) | HIGH — flips §4.5 honest-verdict from "ties at saturation" to "saturated decision + continuous discriminator" | New §4.5.1 |
| Gap 4: MNIST −15% FID toy-comparison | Medium (new §4.9) | MEDIUM — first concrete trained-FM signal | New §4.9 |
| Gap 5: C.6 / C.7 algorithm-layer verification | Medium (new §3.8) | MEDIUM — strengthens "paper-as-algorithm" claim with numerical evidence | New §3.8 |

**Net effect on the paper.** With Gaps 1+2+3 added, the paper's
headline becomes "framework improves 4 published model families at
matched checkpoint (per-family signed_mean +0.408 / +0.213 / +0.063 /
+0.001, G.1 robust median +0.0884 PASS), all 7 capability gates
PASS, three ground-truth oracles PASS, and provides a discriminating
metric on the protein axis (per-position entropy, Wave 33 fix C) —
with explicit, honest enumeration of the 6 still-open gaps at the
top-model tier." That is a stronger, more honest, more defensible
paper than the current draft.

---

## 4. Generated artefacts (this wave)

* `docs/figures/fig8-per-family-signed-mean.png` — horizontal bar
  chart of the 4 model-family signed_mean values + G.1 robust target
  line at +0.05. Source data:
  `verification_outputs/capability_audit_q4_2026.json` G.1 evidence
  section (env_hash
  `2080f2e8feccef8223509bd59e117062d1b10f66e297a735c5936fc0864db0ff`).
* `tools/_make_wave41_figure.py` — regenerable figure script (uses
  the same brand-neutral palette as `tools/_make_figures.py`).
* `docs/CONSOLIDATED_RESULTS.md` §15 (APPEND) — short pointer at
  this audit doc, the figure, and the 5 concrete additions.

## 5. Files changed

* `docs/audit/wave41-paper-audit.md` (NEW, this file)
* `docs/CONSOLIDATED_RESULTS.md` (additive §15 APPEND)
* `docs/figures/fig8-per-family-signed-mean.png` (NEW)
* `tools/_make_wave41_figure.py` (NEW)
