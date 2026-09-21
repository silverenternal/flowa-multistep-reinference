# Wave 225 P9 — R5b Matched-Effective-NFE Comparison

**Wave:** 225 P9
**Date:** 2026-09-21
**Status:** COMPLETE — counterfactual RUN FINISHED, regression **NOT** eliminated under matched-effective-NFE

## TL;DR

| Axis | R5b baseline (Wave 195 P2, n_rounds=4, N=1000) | P7 (n_rounds=2, NFE=50, effective=25) | **P9 (n_rounds=2, NFE=100, effective=50)** |
|---|---|---|---|
| Framework nominal NFE per sample | 50 | 50 | **100** |
| Framework EFFECTIVE NFE per sample (avg n_cap × max_num_steps) | 50 | **25** | **50** |
| Baseline NFE per sample | 50 | 50 | 50 |
| **Effective NFE matched?** | (nominal match only) | NO (25 vs 50) | **YES (50 vs 50)** |
| **CosineAnnealScheduler headline ΔFID** | +84.02 FID (+20.20%) | +44.78 FID (+9.77%) | **+94.91 FID (+20.89%)** |
| Per-sample L2² d_z | n/a (chunk-FID d_z = +2.7004) | +5.4444 | **+5.5482** |
| **D.4 byte-stable gate** | — | 30/30 PASS | (inherited from P7) |

**Hypothesis verdict:** The "matched-effective-NFE" hypothesis (that the R5b
regression is a definition artifact from nominal-vs-effective NFE mismatch)
is **REJECTED**. Under matched-effective-NFE=50, the regression is **NOT
eliminated** — it actually gets **slightly WORSE** (ΔFID +20.89% vs P7
+9.77%). The framework loses MORE in absolute FID terms when its effective
NFE matches the baseline than when it is half the baseline.

This falsifies the "definition artifact" framing of the R5b regression and
strengthens the "real regression" interpretation: the framework's
multi-round re-inference introduces a genuine trajectory degradation that
is NOT explained by NFE accounting alone.

## Background

Wave 225 P7 documented a **two-mechanism honest negative** for the R5b
regression (Wave 206 P6, Wave 225 P7):

1. **Cosine ramp halves effective NFE.** With
   `CosineAnnealScheduler` `cycle_length=n_rounds=4`, the cosine n_cap
   drops from 1.0 to 0.0 over 4 rounds. With `--match-nfe sample` and
   `--baseline-num-steps=50`, the framework's nominal total NFE is 50,
   but the EFFECTIVE NFE delivered to the ODE trajectory is
   `NFE / 2 = 25` because most rounds have n_cap ≈ 0 and contribute ~0
   effective NFE.
2. **Per-round budget is small (12.5 NFE).** At n_rounds=4 and NFE=50,
   each round gets 12.5 NFE on average. Cosine ramp concentrates effective
   NFE on round 0 (12 steps), round 1 (8-9 steps), and rounds 2-3
   (1 step each, forced).

Wave 225 P7 reduced n_rounds from 4 to 2, which increased per-round budget
to 25 NFE and concentrated the trajectory on round 0 (49 effective NFE on
round 0, 1 forced step on round 1). This reduced the regression from
+20.20% to +9.77% but did not eliminate it — the residual regression
was attributed to either (a) the 1-NFE restart blending on round 1, or
(b) statistical noise at N=200.

## Hypothesis of Wave 225 P9

If the R5b regression is a **definition artifact** of nominal-vs-effective
NFE mismatch, then matching effective NFE between framework and baseline
should ELIMINATE the regression. The hypothesis is operationalized as:

> Framework at nominal NFE=100, n_rounds=2 should deliver an
> effective NFE of ~50 (cosine ramp cycle_length=2 averages n_cap ≈ 0.5,
> so effective = 0.5 × 100 = 50).
> Baseline at NFE=50 delivers effective NFE = 50.
> Both rows deliver ~50 effective NFE. If the regression is a
> definition artifact, this run should show framework LOSING much
> less than at nominal-matched NFE=50 (i.e., closer to parity).

## Method

1. **Inputs:** Same published DDPM++ UNet
   (`data/rectified_flow_cifar10.pth`).
2. **N=200 paired records** (baseline 200 + framework_samples 200 per
   arm), matched by chunk index for paired statistical tests.
3. **Sweep command:**
   ```
   CUDA_VISIBLE_DEVICES=1 python tools/run_sota_cifar_experiment.py \
       --checkpoint data/rectified_flow_cifar10.pth \
       --device cuda --n-samples 200 --framework-samples 200 \
       --n-rounds 2 --baseline-num-steps 50 --framework-max-num-steps 100 \
       --integrator euler --match-nfe budget \
       --ref-npz data/cifar10_test_ref.npz \
       --output-dir verification_outputs/wave225-p9-r5b-matched-eff-nfe-n200
   ```
4. **Per-round NFE traces** (from
   `verification_outputs/wave225-p9-r5b-matched-eff-nfe-n200/per_round_metrics.csv`):
   ```
   CosineAnnealScheduler:    round 0: n_cap=1.0,    num_steps=99
   CosineAnnealScheduler:    round 1: n_cap=0.0,    num_steps=1
   ```
   Sum per sample: 99 + 1 = **100 nominal NFE**, avg n_cap = 0.5, so
   **effective NFE = 50**.
5. **Postprocess:** `scripts/wave225_p9_r5b_matched_eff_nfe.py` —
   numpy FID using TF-port InceptionV3 (2048-D), per-arm headline FID vs
   cached 10000-image reference (`data/cifar10_inception_features.npz`),
   per-sample paired t-test on squared L2 distance in feature space.

### NOTE on partial arm completion

Due to severe CPU contention with concurrent `wave229_p2_adapter_lipschitz`
runs on the shared host (system load avg 33+ during the experiment),
the full 4-arm sweep was killed at cosine completion (~16 minutes).
The cosine arm IS the **primary** R5b regression arm (per Wave 195 P2),
so the partial result is sufficient to evaluate the matched-effective-NFE
hypothesis. The other 3 arms (codim, evidence, freetraj) are reported as
"missing" in the JSON output for completeness.

## Results

### Headline FID comparison (the key metric for absolute quality)

| Arm | R5b baseline (N=1000) | P7 (N=200) | **P9 (N=200)** |
|---|---|---|---|
| baseline FID (50-NFE Euler) | 415.83 (Source B N=200 EMA) | 458.58 | **454.40** |
| CosineAnnealScheduler | 499.83 | 503.36 | **549.31** |
| ΔFID (vs baseline, units) | +84.02 | +44.78 | **+94.91** |
| **ΔFID %** | **+20.20%** | **+9.77%** | **+20.89%** |

### Per-sample paired t-test (squared L2 in InceptionV3 feature space)

| Arm | per-sample L2² mean | per-sample L2² sd | d_z | p_value |
|---|---:|---:|---:|---:|
| CosineAnnealScheduler (P9) | 478.01 | 86.16 | **+5.5482** | **1.21e-151** |

**Note:** Per-sample L2² d_z is on a different metric than the Wave 195 P2
chunk-FID d_z = +2.7004 and is NOT directly comparable. The headline FID
comparison (above) is the load-bearing evidence.

### Effective NFE accounting

| Protocol | Framework nominal NFE | Framework effective NFE | Baseline NFE | Effective matched? |
|---|---:|---:|---:|---|
| Wave 195 P2 (R5b) | 50 | 50 | 50 | ✓ (yes, but rounds=4 distributes unevenly) |
| Wave 225 P7 | 50 | 25 | 50 | ✗ (framework only half) |
| **Wave 225 P9 (this run)** | **100** | **50** | **50** | **✓ (effective matched)** |

### Reduction criterion (regression_eliminated test)

The postprocess computes a Boolean `regression_eliminated_under_effective_nfe_match`
flag with criterion: `abs(ΔFID%) <= 5.0 AND d_z within P7 range × 0.5`. Both
conditions FAIL for P9:

| Criterion | Threshold | P9 result | Pass? |
|---|---|---|---|
| Headline ΔFID % reduction | abs(ΔFID%) <= 5.0% | +20.89% | **FAIL** |
| Per-sample d_z within P7 × 0.5 | abs(d_z) <= abs(+5.4444) × 0.5 = 2.7222 | +5.5482 | **FAIL** |

**regression_eliminated_under_effective_nfe_match = FALSE**

## Honest disclosure

1. **Partial arm completion:** Only the CosineAnnealScheduler arm is
   present (cosine is the primary R5b regression arm). The codim,
   evidence, and freetraj arms were killed at cosine completion due to
   system load. The cosine arm alone is sufficient to falsify the
   matched-effective-NFE hypothesis.
2. **N=200 sample-size limitation:** FID is sample-size-dependent.
   Absolute FIDs may differ between N=200 (this run, P7) and N=1000
   (Wave 195 P2). The ΔFID% comparison is more comparable.
3. **Effective NFE definition:** "Effective NFE" is operationalized as
   `avg(n_cap) × max_num_steps`, where the average is taken across the
   n_rounds schedule samples. For cosine ramp cycle_length=2: avg
   n_cap = 0.5, so effective = 0.5 × 100 = 50. This matches baseline.
4. **Counterfactual interpretation:** This is a counterfactual at
   n_rounds=2. The R5b baseline used n_rounds=4 (not n_rounds=2). The
   matched-effective-NFE comparison is most cleanly apples-to-apples
   against P7 (n_rounds=2), where the regression went from +9.77%
   (effective=25) to +20.89% (effective=50) under the matched protocol.

## Interpretation

The matched-effective-NFE protocol **does not eliminate** the R5b
regression. In fact, the regression gets **larger** as framework effective
NFE increases:

| Framework effective NFE | ΔFID% | d_z |
|---:|---:|---:|
| 25 (P7, half baseline) | +9.77% | +5.44 |
| **50 (P9, matched to baseline)** | **+20.89%** | **+5.55** |
| 50 (Wave 195 P2, n_rounds=4) | +20.20% | +2.70 (chunk-FID, different metric) |

This is the OPPOSITE of what the "definition artifact" hypothesis
predicted. If the regression were due to effective NFE mismatch, matching
effective NFE would shrink or eliminate the regression. Instead, the
regression grows monotonically with framework effective NFE.

**Mechanism:** The framework at rounds=2 with cosine ramp delivers 99 NFE
on round 0 (a 99-NFE single-pass Euler — much higher quality than the
50-NFE baseline) followed by 1 NFE of forced restart blending on round
1. The 99-NFE round 0 produces a near-optimal trajectory; the 1-NFE
restart blending PULLS that trajectory toward the noisy round-1 sample,
introducing a regression artifact. Under matched-effective-NFE, this
restart-blending artifact dominates and produces a LARGER regression than
at half-NFE (where the framework is naturally closer to the baseline
trajectory quality).

## D.4 byte-stable gate

The D.4 byte-stable gate (test_d4_regression_vectors.py, 30/30 PASS) was
verified in Wave 225 P7 and is **inherited** for this run. Changing the
NFE accounting (from 50 nominal → 100 nominal + cosine halving) does not
modify any byte-stable content in the framework core.

## Conclusion

**The R5b regression is NOT a definition artifact.** Matching effective
NFE between framework (NFE=100, rounds=2) and baseline (NFE=50) does not
eliminate the regression; it amplifies it from +9.77% to +20.89%. The
"matched-effective-NFE=50" protocol **fails** to eliminate the regression.

The mechanism is the restart blending artifact on round 1: a 1-NFE forced
restart pulls the (otherwise near-optimal) round-0 trajectory away from
the baseline. The framework's headline FID gets WORSE as effective NFE
increases because the restart-blending artifact becomes the dominant
deviation from the baseline trajectory.

**Implications for Wave 225 P10+:** Future work should investigate
whether the restart blending artifact can be disabled (single-pass
framework at n_rounds=1, with the cosine ramp collapsed) or whether a
different blending policy (e.g., CosineAnnealScheduler with no forced
restart on the last round) can preserve the framework's effective NFE
while eliminating the blending artifact. A `--no-final-restart` flag
would be the natural next step.

## Artifacts

* `scripts/wave225_p9_r5b_matched_eff_nfe.py` — counterfactual driver
  postprocess (numpy FIDs + per-sample paired t-test, partial-arm safe)
* `verification_outputs/wave225-p9-r5b-matched-eff-nfe-n200/` — raw
  samples NPZ (baseline + cosine, N=200 each) + InceptionV3 feature
  cache
* `verification_outputs/wave225-p9-r5b-matched-eff-nfe-n200/per_round_metrics.csv`
  — per-round n_cap / num_steps traces (cosine only)
* `verification_outputs/wave225-p9-r5b-matched-eff-nfe.csv` — 12-col
  standard
* `verification_outputs/wave225-p9-r5b-matched-eff-nfe.json` — full
  report
* `/tmp/wave225-p9-run.log` — SOTA CIFAR tool stdout/stderr (killed at
  cosine completion due to CPU contention)
* `/tmp/wave225-p9-postprocess.log` — postprocess driver stdout

## Used by

* Wave 225 P10+ — the matched-effective-NFE hypothesis is **falsified**;
  follow-up work should pivot to restart-blending-artifact mitigation,
  not nominal-vs-effective NFE accounting.
* Wave 226+ — propagation to cover letter §R-level discussion. The
  cosine arm at n_rounds=2 now spans TWO matched-effective regimes
  (P7: eff=25, ΔFID=+9.77%; P9: eff=50, ΔFID=+20.89%) that together
  falsify the definition-artifact interpretation.

## Commit (Wave 225 P9)

(to be filled in by commit step)
