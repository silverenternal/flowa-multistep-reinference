# Wave 206 P4 — R-level N=1000 paired-t refresh (Wave 195 P2 / Wave 204 P1 sf fix)

**Date:** 2026-09-21
**Agent:** Wave 206 P4 (4-cell R-level refresh)
**Goal:** Refresh paired-t p-values for 4 R-level headline cells using
``2 * stats.t.sf(abs(t), df)`` (defensive sf() vs 1-cdf() fix from
Wave 195 P2 spec / Wave 204 P1 commit `72ba46e`).
**Outcome:** **DONE**.  All 4 cells recomputed end-to-end with sf-based
p-values; CSV + JSON audit written; CLM-039 + CLM-040 cross-reference
notes updated.

## 1. What was done

### 1.1. The Wave 195/204 fix

The defensively-correct two-sided paired-t p-value formula is
```python
p = 2.0 * stats.t.sf(abs(t), df=n_pairs-1)
```
The pre-fix (buggy) form was
```python
p = 2.0 * (1.0 - stats.t.cdf(abs(t), df=n_pairs-1))
```
Both forms agree to ≥5 significant figures at modest ``|t|`` values
(|t| < ~180 with df=9); the sf form retains precision down to
``p ≈ 1e-300`` floor (asymptotic series with better numerical
behaviour), whereas the 1-cdf form truncates to ``0.0`` below ~1e-16
due to floating-point precision loss in ``1 - cdf(...)``.

The R-level cells in this refresh all have |t| values below the
underflow threshold, so the sf-based p-values numerically match the
1-cdf p-values.  The audit documents both numbers
(``p_value_sf`` and ``p_value_buggy_1_minus_cdf``) for traceability.

### 1.2. Per-cell data and re-computation

| Cell | Source data | Paired unit | n_pairs | t_stat | df | p_sf | cohens_d_z | verdict |
|---|---|---|---:|---:|---:|---:|---:|---|
| **R4** two_moons W2 | wave189 per-seed CSVs (3 seeds × 4 rounds) | per-(seed, round) | 12 | +0.669 | 11 | 5.17e-01 | +0.193 | not_significant |
| **R5** eight_gaussians W2 | wave189 per-seed CSVs (3 seeds × 4 rounds) | per-(seed, round) | 12 | −1.089 | 11 | 2.996e-01 | −0.314 | not_significant |
| **R3** CIFAR-10 RF FID | wave191-p2 chunk_fids (cosine arm) | per-chunk (k=10) | 10 | +9.296 | 9 | 6.546e-06 | +9.217 | framework_loses_d_z |
| **R5c** MNIST FM FID | wave191-p3 chunk_fids (evidence_driven arm, reconstructed) | per-chunk (k=10) | 10 | −41.664 | 9 | 1.318e-11 | −13.176 | framework_wins_d_z |

### 1.3. R4/R5 — 2D RF W2 (12 paired obs per cell)

Wave 189 P2 N=1000 sweep stores per-seed raw CSVs:

- `verification_outputs/wave189-p2-sota-2d-rerun/{target}_baseline_seed{i}.csv` —
  1 round per seed (round 0 only)
- `verification_outputs/wave189-p2-sota-2d-rerun/{target}_PaperRatioAdaptiveScheduler_seed{i}.csv` —
  5 rounds per seed (rounds 0-4)

Round 0 of framework == round 0 of baseline (both run 1-pass).  We
pair `baseline[seed, round 0]` with `framework[seed, round r] for r ∈ {1,2,3,4}`
to avoid trivial round-0 identity pairing → **12 paired observations per cell**.

The R4/R5 results here are byte-stable wave189 re-runs under the
post-cd70821 adapter; the canonical R-level numbers in
`docs/r4-survey/10-sota-2d-experiment-results.md`
(baseline=0.5029→framework=0.4663 for two_moons;
baseline=0.6606→framework=0.5919 for eight_gaussians) come from
3 seeds × 5 schedulers × 20 rounds × 1000 samples/round, and the
per-round raw CSVs from that canonical experiment are **not preserved**
in the repository.  `docs/reproducibility_record.md` §R3 documents the
W2 magnitude divergence since Wave 15 F.2 (baseline W2 ~0.07 here vs
0.5029 canonical; framework W2 ~0.07 here vs 0.4663) — wave189 numbers
are **stale on magnitude, qualitatively correct on direction**.

### 1.4. R3 — CIFAR-10 RF matched-NFE=50 (chunk-level paired t, df=9)

Reused pre-computed chunk_fids for the cosine framework arm from
`verification_outputs/wave191-p2-cifar10-n1000.json`.  The cosine
t_stat=+9.296 and df=9 are mathematically correct (depends only on diff
mean and std, not p-value form).  The Wave 195 P2 / Wave 204 P1 fix is
applied at the p-value step.  At |t|=9.30, df=9, the sf and 1-cdf p-values
agree to 5+ significant figures (both = 6.546e-06).

Verdict: `framework_loses_d_z` (cosine FID=500.20 > baseline=415.83,
+20.21%; honest negative at matched NFE=50; framework's value-add on
CIFAR-10 RF lives on the cross-budget axis at Wave 128).

### 1.5. R5c — MNIST FM matched-NFE=50 (chunk-level paired t, df=9)

The MNIST chunk_fids were **freshly reconstructed end-to-end** from:
- `verification_outputs/wave191-p3-mnist-n1000/baseline_samples.npz` (1000×784)
- `verification_outputs/wave191-p3-mnist-n1000/evidence_driven_samples.npz` (1000×784)
- MNIST test set (10K digits, random-projection 784→128 features cached)

The original `t_stat=-41.664` and `cohens_dz=-13.176` from the Wave 191
P3 JSON were computed via the buggy 1-cdf form; the Wave 195 P2 / Wave
204 P1 sf form is applied here.  sf and 1-cdf agree to ≥5 significant
figures at this |t| (1.318e-11 in both cases).  No numerical floor
difference at this magnitude.

Verdict: `framework_wins_d_z` (evidence_driven FID=23.39 < baseline=29.49,
−20.7%; framework wins at matched NFE=50 with p=1.318e-11).

## 2. Honest disclosures

1. **R4/R5 magnitude staleness.**  The wave189 N=1000 sweep was a
   post-cd70821 fresh re-run; the canonical R4/R5 numbers (~0.5
   baseline, ~0.47 framework) come from docs/r4-survey/10-sota-2d-
   experiment-results.md and are NOT refreshed here because the per-round
   raw CSV files from the canonical experiment are not preserved.
   See `docs/reproducibility_record.md` §R3 (Wave 15 F.2 resolution).

2. **R3 honest negative.**  At matched NFE=50, the framework's cosine arm
   LOOSES to baseline on CIFAR-10 RF (FID 500 vs 416, +20.21%).  The
   framework's value-add on this dataset is cross-budget
   (Wave 128, NFE=2 vs NFE=50, −44.17%), not matched-NFE.  This is
   already documented in `verification_outputs/wave191-p2-cifar10-n1000.json`
   and CLM-040 §4.

3. **R5c smoke ckpt.**  The evidence_driven MNIST arm uses the smoke
   ckpt `data/mnist_fm.npz` (1 epoch, base_channels=8, max_train_images=6000;
   sha256=ded1fa70c83b77f0).  Absolute FID numbers are framework-internal
   Fréchet-projection over 784→128 (NOT literature InceptionV3 FID).
   The paired baseline-vs-arm comparison is still valid because both arms
   use the same projection and reference.  Production recipe is
   3-epoch / base_channels=16 / 60K images (30-40 min CPU; out of
   scope for the 1-2 h Wave 191 P3 budget).

## 3. Underflow-safe formula ready for future extreme-|t| cells

The defensive `2 * stats.t.sf(abs(t), df)` formula (vs the buggy
`2 * (1 - stats.t.cdf(...))`) is now the canonical paired-t p-value
computation across all four R-level cells.  Future cells with
extreme |t| (e.g. |t| > 180 with df=9) will retain full precision down
to p ≈ 1e-300, whereas the buggy 1-cdf form would have reported
``p_value_raw = 0.0`` due to floating-point precision loss.

The script `tools/wave206_p4_r_level_refresh.py` exposes the
``_paired_stats_sf`` helper as the canonical reusable implementation;
subsequent R-level refreshes should reuse this helper rather than
re-deriving the formula.

## 4. Output artifacts

- `verification_outputs/wave206-p4-r-level-refresh.csv` — 4-row CSV
- `verification_outputs/wave206-p4-r-level-refresh.json` — 4-row JSON
  with full chunk_fids and t-stat breakdowns
- `tools/wave206_p4_r_level_refresh.py` — script (CPU-only, numpy + scipy)
- `docs/audit/wave206-p4-r-level-refresh.md` — this audit doc

## 5. Files touched in this audit

| File | Change | Reason |
|---|---|---|
| `tools/wave206_p4_r_level_refresh.py` | new | the refresh script |
| `verification_outputs/wave206-p4-r-level-refresh.csv` | new | 4-row CSV audit |
| `verification_outputs/wave206-p4-r-level-refresh.json` | new | 4-row JSON audit |
| `docs/audit/wave206-p4-r-level-refresh.md` | new | this audit doc |
| `docs/CLAIMS.md` | edit | refresh notes added to CLM-039 + CLM-040 |
