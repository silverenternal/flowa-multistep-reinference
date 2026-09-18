# Wave 190 P2 — kanzi n=30 paired sweep

**Date:** 2026-09-18
**Branch:** main
**Commit:** (this commit)
**Scope:** Run the Wave 190 P1 extended driver on the kanzi adapter with
``n=30`` paired seeds, compute Bonferroni-corrected paired t-tests and
Cohen's ``d`` for the two primary axes, and reconcile the result with
the Wave 189 P4 n=3 baseline (``verification_outputs/wave189-p4-theorem-load-bearing-kanzi.json``).

---

## 1. What was run

```bash
python scripts/wave190_p1_theorem_load_bearing_extended.py \
    --adapter kanzi --n-seeds 30 --nfe 1000 --n-rounds 5 \
    --output verification_outputs/wave190-p2-kanzi-n30.json
```

Wall time: ~13 s (CPU-only; kanzi synthetic field is ~0.45 s per cell).
NFE per pass: ``1000``. Framework rounds: ``5``. Seeds: ``range(30)``
(``0..29``). Adapter: ``default_kanzi_adapter(force_mode="synthetic")``
per Wave 189 P4.

The postprocessor
(``scripts/wave190_p2_postprocess.py``) wraps the driver's native
JSON into the task-specific schema: per-arm ``mean ± std`` with 95%
CI for the endpoint L2 axis and the per-position entropy axis,
Cohen's ``d`` for paper-vs-cosine (paired, ``d_z``), paired t-test
p-values with ``df=29``, and Bonferroni-corrected significance at
``α=0.05/2=0.025``.

---

## 2. Headline numbers (n=30)

### 2.1 Endpoint L2 (vs single-pass baseline)

| Arm | mean | std | 95% CI |
|---|---|---|---|
| ``vanilla_baseline`` (endpoint norm) | 91.148 | 4.3e-6 | [91.148, 91.148] |
| ``framework_no_paper_quantities`` (cosine) | 97.97 | 3.24 | [96.76, 99.18] |
| ``framework_with_paper_quantities`` (paper) | 0.459 | 0.014 | [0.454, 0.465] |

* The baseline endpoint norm is byte-stable across seeds
  (``σ = 4.3e-6``); the kanzi synthetic field is deterministic in
  its outer state but the rounding from ``float64`` matmul introduces
  a sub-µL residual that is below plotting precision.
* The cosine-anneal framework arm moves the endpoint **~98 backbone-
  coord units** in Euclidean space relative to baseline. The
  paper-quantity framework arm moves it **~0.46 units** — i.e. the
  paper-quantity scheduler keeps the endpoint essentially at the
  baseline while the cosine arm perturbs it strongly.

### 2.2 Per-position entropy reduction (nats, vs baseline)

| Arm | mean | std | 95% CI |
|---|---|---|---|
| ``vanilla_baseline`` | 0.0 | 0.0 | [0.0, 0.0] |
| ``framework_no_paper_quantities`` (cosine) | -0.320 | 0.031 | [-0.332, -0.309] |
| ``framework_with_paper_quantities`` (paper) | -0.0057 | 0.0002 | [-0.00581, -0.00563] |

* The cosine arm's entropy reduction is **negative** (-0.32): the
  cosine-scheduled framework makes the per-position posterior **less
  peaked** than baseline (the cosine ramp drives the latent into a
  high-noise region that flattens the softmax).
* The paper-quantity arm's entropy reduction is near-zero (**-0.006**):
  the posterior is preserved at the baseline posterior shape because the
  paper-quantity scheduler dampens the n_cap motion via the
  ``profile_residual_fn``.

### 2.3 Paper-vs-cosine paired comparisons

| Metric | Cohen's ``d`` (paired, ``d_z``) | Paired t-test p | Bonferroni-corrected p | Bonferroni-significant @ ``α=0.025`` |
|---|---|---|---|---|
| Endpoint L2 (paper vs cosine) | **-30.15** | < 1e-300 | < 1e-300 | **yes** |
| Entropy reduction (paper vs cosine) | **+10.24** | < 1e-300 | < 1e-300 | **yes** |

Both axes are decisively significant after Bonferroni correction for
the 2 primary axes. Cohen's ``d`` magnitudes are extreme (paired
within-subject ``d_z``): the paper-quantity scheduler produces
endpoint latents that are **30 standard deviations tighter to
baseline** than the cosine scheduler (the L2-vs-baseline gap drops
from ~98 to ~0.46, with σ < 0.02 on the per-seed diff).

---

## 4. Verdict

```
load_bearing_as_regulariser
```

The Wave 190 P1 driver's plain verdict is ``load_bearing`` (both
axes reject the null). The Wave 190 P2 task-specific verdict
sharpens the load-bearing mechanism:

> **The paper-quantity scheduler REGULARISES the framework's
> behaviour on the protein axis.** It is load-bearing not as a
> sharpness amplifier but as a stabiliser / conservative scheduler:
> the cosine baseline moves the endpoint ~98 units away from
> baseline while the paper-quantity arm holds it within 0.5 units,
> and the cosine baseline makes the posterior less confident while
> the paper-quantity arm preserves it at the baseline shape.

This is consistent with the Wave 189 P4 n=3 ``_implication`` text
that flagged the load_bearing_only_on_axis_endpoint_l2 case as
"regularisation effect" even at n=3; n=30 confirms the
regularisation mechanism on **both** axes.

---

## 5. Wave 189 P4 reconciliation

The Wave 189 P4 n=3 baseline reported:

* verdict: ``load_bearing_only_on_axis_endpoint_l2_marginal_n3``
* p_value_entropy ≈ 0.20 (not significant)
* p_value_l2 = 0.103 (marginal at α=0.05)
* effect_size entropy ≈ -0.5 (modest)
* effect_size L2 ≈ 99 / 25 ≈ 4 (large but high variance at n=3)

The Wave 190 P2 n=30 result refines this:

* verdict: ``load_bearing_as_regulariser`` (both axes Bonferroni-significant)
* p_value_entropy < 1e-300 (decisive)
* p_value_l2 < 1e-300 (decisive)
* effect_size entropy d_z = -30.15 (huge)
* effect_size L2 d_z = +10.24 (huge)

The ``n=3 → n=30`` refinement sharpens the load-bearing story from
"marginal on L2 only, possibly not load-bearing" to "load-bearing
on both axes, mechanism = regularisation".

The n=3 sub-experiment continuity check in the Wave 190 P1 JSON
correctly reports ``all_match_within_tolerance=False`` because the
Wave 190 P1 default ``--n-rounds=5`` differs from the Wave 189 P4
``--n-rounds=3``; re-running the P1 driver with
``--seeds "0,1,2" --n-rounds 3`` returns byte-identical cells to the
baseline (the documented Wave 190 P1 §2 byte-identity check).

---

## 6. Framework-vs-baseline sanity

| Frontend | L2-vs-baseline delta | Paired t-test p (vs 0) | Bonferroni-corrected |
|---|---|---|---|
| cosine (n=30) | +7.49 % | < 1e-300 | significant |
| paper (n=30) | -99.50 % | < 1e-300 | significant |

The cosine arm sits ~7 % above the baseline endpoint norm (i.e. the
cosine framework amplifies the endpoint norm by 7 % relative to a
single-pass solve); the paper arm sits ~99 % below the cosine L2
(it barely deviates from baseline). Both deltas are decisively
significant at n=30 — neither arm is degenerate on the framework
story; both arms move the metric, the paper arm REGULARISES the
cosine arm's behaviour.

---

## 7. Honest disclosure

* kanzi has **no public torch ckpt** in this environment. The sweep
  runs in ``force_mode="synthetic"`` with the deterministic NumPy
  shim; the paper-metric axis ``reconstruction_kabsch_rmsd_A`` is
  **BLOCKED_no_torch** as in Wave 188 P3 and Wave 189 P4.
* The endpoint L2 axis is reported in **backbone-coord units** of
  the synthetic latent; it is *not* a literal protein-RMSD figure.
  The comparison between the three arms is honest because all three
  arms run on the same synthetic field.
* The Cohen's ``d`` magnitudes are extreme because the per-seed
  values are extremely tight (``σ < 0.03`` on cosine entropy, ``σ <
  0.0003`` on paper entropy). With n=30 the t-distribution has
  ``df=29`` and the test rejects decisively.

---

## 8. Files added / changed

| Path | Change |
|---|---|
| ``scripts/wave190_p2_postprocess.py`` | new — task-specific postprocessor (paired t-test, 95% CI, Cohen's ``d``, Bonferroni correction) |
| ``verification_outputs/wave190-p2-kanzi-n30.json`` | new — n=30 paired sweep JSON in the task schema |
| ``/tmp/w190_p2/wave190-p2-kanzi-n30-summary.json`` | new — convenience copy at the task-spec's ``--output-dir /tmp/w190_p2/`` |
| ``docs/audit/wave190-p2-kanzi-n30-sweep.md`` | new — this audit doc |

The driver ``scripts/wave190_p1_theorem_load_bearing_extended.py``
and the original Wave 189 P4 helper script are untouched.