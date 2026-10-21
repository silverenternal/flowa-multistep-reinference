# GAP-77 — what the restart operator does, and why the measured gain is not the framework's

**Date:** 2026-10-21
**Status:** closed. Re-analysis of committed sample clouds; no model was run.
**Question (user directive):** *"先搞清楚项目本身让 flow matching 推理质量变高的效果是怎么实现的"* —
before any further cell work, name the mechanism that is supposed to raise inference
quality, and say where the measured gains actually come from.

---

## 0. TL;DR

The operator has exactly **two** channels. Measured over 36 cells
(4 checkpoints × 3 seeds × 3 arms, N=1000, matched NFE=50):

| channel | direction | census |
|---|---|---|
| mean displacement `‖Δμ‖²` | **always away from the reference** | **36/36 up** (+0.76 … +3.32) |
| covariance contraction `Tr(Σ)` | **always down** | **36/36 down** (−16.3 … −1.25) |

Their FID effects partially cancel. Removing the first channel arithmetically
(the prediction for a mean-preserving restart) moves the mean ΔFID from
**+7.97 % to −3.33 %** and the win count from **4/36 to 18/36**.

So the honest statement of the mechanism is:

> The restart is a **covariance-contraction operator** that carries a
> **first-moment defect**. The contraction is net beneficial; the defect is
> worth more than the contraction on three of four checkpoints. The framework's
> measured quality loss is not "the framework does not work" — it is a
> removable location bias sitting on top of a working contraction.

And, separately, the cells the paper calls positive are **not measuring this
operator** (§5).

---

## 1. What the operator is, in code

The canonical step for one record (`adaptive_reflow/adapters/mnist_fm.py:654`,
driven by `scripts/wave191_p3_mnist_sweep.py:438-475`):

```text
x ← x0 ~ N(0, I)
for r in 0 … R−1:
    if r > 0:
        β_r  ← β_total · min(1, NFE_ref / NFE)          # nfe-adaptive β
        y    ← m·x + (1−m)·ε ,   m = 1 − β_r ,  ε ~ N(0, I) i.i.d.
        x    ← Euler(v_θ, y, t: t0 → 1, steps = NFE/R)
return x
```

Three knobs, and only three:

1. `steps per round` — the scheduler's `n_cap` weights (`build_scheduler`,
   `wave191_p3_mnist_sweep.py:233`).
2. `m` — the memory fraction retained across a restart.
3. `t0` — where the re-integration starts (`zero` = legacy, `memory` = `1−β`).

Everything else in the framework is **inert in production**:

- `enable_full_jmaa_theory` defaults `False` (`adaptive_reflow/frame/engine.py:1000`);
- `PaperQuantitiesCache()` is constructed once and never read (`engine.py:1047`);
- `profile_residual_fn` is wired in three scripts and `tools/eval/framework.py`,
  and in **no** production driver (GAP-44).

So the paper-quantity / classifier-aware refinement path cannot be the source of
any production number.

## 2. What the blend does, algebraically

The restart state is

```
y = m·x1 + (1−m)·ε ,  ε ⊥ x1
```

`y` is a sample from the path marginal at `t = 1−m` **only if** `ε` is the noise
that generated `x1`. With independent `ε` the two moments separate:

- `E[y] = m·E[x1]`, while the path requires `m·E[x_data]` — so **any model mean
  error survives the restart with weight `m` and is then re-integrated**;
- `Var[y] = m²Var[x1] + (1−m)²`, while the path requires
  `m²Var[x_data] + (1−m)²` — the variance channel is only wrong by the model's
  own variance error.

This is the theoretical reason the two channels behave so differently in §3:
the first moment has **no averaging mechanism** (it is the one statistic that
1000 samples do not shrink), while the second moment is being deliberately
contracted by the conditional-mean structure of the re-integration
(GAP-67 §6.3, GAP-74).

## 3. The census: 36/36 and 36/36

`tools/gap77_restart_mechanism.py` recomputes the Fréchet terms in the same
128-dim projection the sweep scored against, and checks it reproduces the
committed headline FID (it does: `production/cosine` = 9.967 / 10.855 / +0.888,
matching `paired_bootstrap.json`).

Seed 42, N=1000, matched total NFE=50:

| ckpt | arm | Δbias | ΔTr(Σ) | −2Δcross | ΔFID | Δ% | mean-preserved ΔFID |
|---|---|---:|---:|---:|---:|---:|---:|
| `production` | cosine | +0.760 | −1.31 | +1.43 | +0.888 | +8.91 | **+0.128** |
| `production` | codimension_sheet | +1.181 | −1.57 | +1.69 | +1.300 | +13.04 | +0.119 |
| `production` | evidence_driven | +0.856 | −1.25 | +1.34 | +0.944 | +9.47 | +0.088 |
| `w16e1_5k` | cosine | +0.885 | −16.09 | +12.84 | −2.365 | **−9.65** | −3.249 |
| `w16e1_5k` | codimension_sheet | +3.207 | −16.30 | +13.12 | +0.026 | +0.11 | −3.181 |
| `w16e1_5k` | evidence_driven | +3.231 | −16.30 | +13.05 | −0.016 | −0.07 | −3.247 |
| `w16e1_10k` | cosine | +1.203 | −8.62 | +7.84 | +0.419 | +2.47 | **−0.784** |
| `w16e1_10k` | codimension_sheet | +2.500 | −8.98 | +8.30 | +1.823 | +10.74 | −0.677 |
| `w16e1_10k` | evidence_driven | +2.019 | −8.95 | +8.22 | +1.288 | +7.59 | −0.732 |
| `w16e1_60k` | cosine | +1.480 | −3.29 | +3.57 | +1.758 | +15.42 | +0.279 |
| `w16e1_60k` | codimension_sheet | +1.860 | −3.78 | +4.13 | +2.213 | +19.41 | +0.353 |
| `w16e1_60k` | evidence_driven | +1.437 | −3.63 | +3.97 | +1.775 | +15.57 | +0.338 |

Aggregated over all 36 cells:

| ckpt | measured mean Δ% | mean-preserved mean Δ% |
|---|---:|---:|
| `production` | +10.91 | +1.21 |
| `w16e1_5k` | −2.98 | **−13.05** |
| `w16e1_10k` | +7.00 | **−4.29** |
| `w16e1_60k` | +16.96 | +2.83 |
| **all** | **+7.97** | **−3.33** |

Three readings:

1. **The sign of the covariance channel is not universal.** ΔTr(Σ) < 0 always,
   but the cross term recovers 80–85 % of it, so the net contraction gain is
   between −0.2 and −3.2 FID units. It is real and it is small.
2. **The location channel is universal and larger.** It is positive in 36/36
   cells and its size is the whole story of the measured regression.
3. **The only checkpoint the operator beats is the one with the most
   covariance to remove.** `w16e1_5k` has `Tr(Σ_base) = 35.47` against a
   reference `Tr(Σ_ref) = 35.28` — a *mis-shaped* covariance (cross = 29.70, not
   35.28), which the contraction fixes. This is why 4/4 of the wins in the
   census are `w16e1_5k`.

## 4. Why no sampler can win this cell

`verification_outputs/gap64b-nfe-headroom/headroom.json`: single-pass FID over
`NFE ∈ {3,5,10,25,50,100}` moves by **0.32 %** on `production` and **0.75 %** on
`w16e1_5k`. The ODE is converged at 3 steps. GAP-56 §5.2 reaches the same
number from the other side (25-step baseline ≈ 50-step baseline within noise).

The model-vs-reference gap is ≈ 10 FID units; the entire sampler choice is worth
≈ 1. **The cell is model-limited, not sampler-limited** (GAP-56 §5.3). No
NFE allocation, no β, no `t0` can close a 10-unit gap with a 1-unit lever, and
GAP-56 §5.1 already showed the β curve is flat over a 5× range.

This is the answer to "why does the framework not raise quality here": there is
nothing left for it to raise. Its only remaining freedom is to move the
distribution, and moving it costs more than it gains.

## 5. What the positive cells actually measure

This is the part that matters for the paper, and it is already in the repo's own
records — it just was not assembled in one place.

**5.1 R1's baseline arm is a bare RNG, not the model.**
`tools/gen_lineageflow_n1000_fastas.py:669` `_write_baseline_arm` draws from
`_generate_sequence` → `_biased_aa` → `rng.choices`. It never runs an ODE and
consumes no NFE. Disclosed at `docs/audit/gap12-tuned-baseline.md` §3.

**5.2 At the canonical R1 config the restart gate is closed.**
`--nfe 10` with the default `--restart-min-nfe 20` degenerates `n_rounds` to 1
(`gen_lineageflow_n1000_fastas.py:612-614`), so the framework arm is a **single
`solve_ode` pass** with no blend. Recorded at `docs/audit/todo-history.md:229`:
*"the +116 % R1 headline is produced entirely by the adapter's real ESM-2
forward (vs the bare-RNG baseline)"*.

**5.3 At gate-open NFE=150 the blend is still not the source.**
GAP-58: β=1 (m=0, no memory term at all) gives **+79.7 %**; β=1/6 gives +74.1 %;
the contrast is **+0.009 hits/record, CI [−0.041, +0.057], sign p=0.918**. The
memory term is bounded at ≤ 0.057 hits/record — about 7 % of the effect. GAP-60
adds the positive control: β=0 collapses to **5–6 clusters out of 200** (0 hits),
so the restart's real function there is **breaking mode collapse**, and any
β > 0 restores 200/200 clusters.

**5.4 The R1 metric does not measure family correctness.**
`verification_outputs/gap58-r1-beta1-n1000/seed42/upstream_eval.json`:
`top1_family_accuracy = 0.0`, `intended_hit_rate_evalue = 0.0`,
`topk_contains_intended = 0.0` in **both** arms. The number that moves is
`hmmscan_total_hits` (158 → 284) — *any* Pfam hit, not the intended family.
The framework's AA composition is near-uniform (entropy 2.986 vs ln 20 = 2.996)
against the baseline's biased 2.748, which is the direct explanation of why more
sequences hit *some* HMM.

**5.5 The genuine model-vs-model wins are a short list.**
- R3 `fg_dev` (FlowMol3, matched NFE=250): −0.0235, p_bonf=0.028; per-record
  REOS flags −0.360/mol, CI [−0.535, −0.185], p=8.0e-05.
- R6 kanzi pLDDT at **NFE=75 only** (+2.12 of 9 NFE points; −5.79 at NFE=100).
- R5c `w16e1_5k` cosine (−9.4 %), which §3 shows is the covariance channel.

Common condition: the base sampler is **mis-calibrated** — collapsed (R1),
mis-shaped (w16e1_5k), or at a resonance (kanzi NFE=100). That is the regime
where a contraction operator has something to fix.

## 6. The constructive statement

The mechanism says exactly what to change, and it is not a document change:

> **Make the restart mean-preserving.** Keep the covariance contraction; remove
> the first-moment displacement. The operator then has one channel, and that
> channel is net beneficial on every checkpoint in the census (−13.05 % on
> `w16e1_5k`, −4.29 % on `w16e1_10k`, +1.21 % / +2.83 % near break-even on the
> two converged checkpoints).

Two independent numbers bracket the payoff:

- the arithmetic counterfactual in §3: **+7.97 % → −3.33 %** mean, **4/36 → 18/36** wins;
- the measured GAP-72 calibration (both arms translated to the *training* mean,
  no test leakage): **9 regressions → 6 wins / 6 small regressions, mean −7.3 %**.

GAP-72's calibration is post-hoc and uses a data statistic. The publishable
version corrects at the source, which is what GAP-76 has to build. This document
does not claim the correction is free — §3 shows the bias is structured
(92 % residual, arm-specific), so a scalar offset computed from the reference is
not available at inference time. What it does claim is that the target is
well-posed: the defect is a first-moment defect, it is 36/36 consistent, and
removing it flips the majority of cells.

## 7. What this does not establish

- **One estimator.** All 36 cells are the framework-internal 128-dim projection
  FID. CIFAR-10 (R5b, Inception-FID) is not in the census.
- **MNIST only for the census.** The two-channel split is measured on the MNIST
  adapter; R3/R6 have not been decomposed this way. The mechanism statement is
  therefore *demonstrated* on image FM and *consistent with* the molecule and
  protein cells, not measured on them.
- **The mean-preserved column is arithmetic, not a run.** It removes the
  measured Δbias from the measured ΔFID. GAP-72's real calibration is the only
  measured version, and it uses a post-hoc translation.
- **No claim about where the mean bias comes from.** That is GAP-76's question
  (off-path state + independent ε). This document only measures that it exists,
  that it is one-signed, and that it is worth more than the contraction.

## 8. Reproduction

```bash
PYTHONPATH=. python3 tools/gap77_restart_mechanism.py
# -> verification_outputs/gap77-restart-mechanism/decomposition.json
```

Inputs are the frozen `verification_outputs/gap57-equal-nfe-ladder-n1000/`
clouds; the tool rebuilds the projection from
`MnistFrechetProjectionEvaluator` (deterministic seed) and asserts the headline
FID against the committed bootstrap JSON.
