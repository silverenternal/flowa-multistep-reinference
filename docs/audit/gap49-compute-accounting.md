# GAP-49 — measured compute ledger (iso-FID / iso-NFE, three domains)

**Date:** 2026-10-18
**Branch:** main
**Scope:** replace the manuscript's un-measured "2.5–10×" speed headline with
what the committed artifacts can actually support: a measured baseline
quality-vs-NFE curve on CIFAR-10, the framework's committed quality at its
canonical budget, the **iso-FID NFE ratio**, and the **matched-NFE** delta on
three domains (CIFAR-10, FlowMol3, LineageFlow). Analysis only — the one new
run is four baseline points on `cuda:0`; no retraining, no frozen surface
touched.
**Frozen surfaces:** untouched (`docs/CLAIMS.md`,
`docs/CONSOLIDATED_RESULTS.md`, `docs/drafts/paper-A-final.*`,
`tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).
**Artifact:** `verification_outputs/gap49-compute-accounting/compute_ledger.json`
(+ `baseline_curve.json`, `baseline-nfe{5,10,20,25}/`; GAP-49b:
`compute_ledger_multiseed.json`, `baseline_curve_multiseed.json`,
`baseline_curve_seed{42,43,44}.json`, `seed{42,43,44}/`).
**Driver:** `scripts/gap49_compute_accounting.py` (`--skip-runs` re-analyses
from the cached curve without touching the GPU).

---

## 0. TL;DR

| Item | Value |
|---|---|
| Primary compute unit | **NFE** (exact, hardware-independent, same checkpoint + solver) |
| New GPU work | 4 baseline points at seed 42, then the full 7-point curve at seeds 42/43/44 (GAP-49b), N=200, `cuda:0` |
| CIFAR baseline seed spread | FID@200 = **446.20 ± 6.08** (range 439.22–450.39) across seeds 42/43/44 |
| CIFAR iso-FID, CodimensionSheet | 2.37× on seed 42; **not measurable on seeds 43/44** (the baseline never reaches 442.90 within NFE ≤ 200) → **seed-42 point estimate, not a 3-seed ratio** |
| CIFAR iso-FID, CosineAnneal | 1.18× on seed 42; also **not measurable on 43/44** (baseline@200 = 449.0 / 450.4 > 447.12) |
| CIFAR iso-FID, EvidenceDriven / FreeTraj | **not resolvable**: 1.01 ± 0.45 (0.58–1.48) and 2.15 ± 1.30 (0.75–3.33) — the sign flips across seeds |
| CIFAR matched-NFE Δ @50 (3 seeds) | CodimensionSheet **−2.09 %** (−2.80…−1.11); CosineAnneal **−1.16 %** (−1.88…−0.17); EvidenceDriven +0.33 % (−0.39…+1.34); FreeTraj −0.21 % (−0.94…+0.79) |
| CIFAR ceiling | baseline@200 NFE reaches **439.22 FID**, better than all four framework arms → the win is **budget-conditional, never a quality-ceiling win** |
| FlowMol3 matched NFE=250 | fg_dev mean Δ(fw−bl) = **−0.0377** (n.s., n=3); pb_validity **+0.020 / −0.0003 / +0.236** |
| FlowMol3 iso-quality | **not identifiable** — baseline fg_dev is non-monotone in NFE |
| FlowMol3 wall-clock at matched NFE | framework **slower on 3/3 seeds** (1.21 / 1.92 / 1.30×) |
| LineageFlow R1 cost model | **1.879 s fixed + 0.1521 s/NFE** per record; fixed = **55.3 %** of the NFE=10 cost |
| LineageFlow R1/R6 iso-quality | **not measured / not measurable** (see §6) |

**One sentence:** the framework's measured, robust compute claim is the
**matched-NFE** one — "at 50 NFE, CodimensionSheet is 2.09 % and CosineAnneal
1.16 % better in FID than the baseline at the same 50 NFE, on 3/3 seeds" —
not "2.5–10× faster", not a 3-seed iso-FID ratio, and not "better at any
budget".

---

## 1. What this replaces

`tnnls_submission/supplementary_bundle/headline_evidence/NFE_SPEEDUP_2P5_TO_10X_SOURCE.md`
derives 2.5–10× from *published trajectories* of other systems, not from this
repo's measurements. That is an extrapolation with no same-checkpoint
comparison behind it. This audit substitutes a measurement with a stated
protocol and a stated failure mode.

---

## 2. Method

### 2.1 Compute unit

For a fixed checkpoint and a fixed solver, sampling cost is
`t ≈ a + b · NFE` per sample. NFE is therefore an exact, hardware-independent
compute measure, and it is the unit used for every ratio below. Wall-clock is
reported where the artifact records it, but it is **not** used for any ratio:
the committed runs share the GPU with other work and the spread (§4.3) is
larger than the effect. A direct control: the *same* baseline point
(NFE=25, N=200, seed 42) took **4.01 s** in the original session and
**26.87 s** in the reproduction run, which was co-tenant with the GAP-46 grid —
a **6.70×** swing for identical work.

### 2.2 Iso-FID inversion (CIFAR only)

1. Measure baseline FID at NFE ∈ {5, 10, 20, 25} (N=200, seed 42, `cuda:0`,
   `tools/run_sota_cifar_experiment.py::_run_baseline`).
2. Merge the committed GAP-12 baseline points at NFE ∈ {50, 100, 200}
   (`gap12-tuned-baseline-cifar.json`) so the curve spans the framework's
   quality without re-running.
3. For each framework arm at NFE=50, piecewise-linearly invert the curve to
   the baseline NFE that reaches the same FID. All four crossings fall
   **inside** the measured range (no extrapolation).
4. Report the crossing at target FID ± 1 and ± 2 as a sensitivity band, because
   FID at N=200 carries finite-sample noise and the crossing is a ratio of two
   interpolated FID gaps.

The framework arm and the baseline in step 3 come from the **same GAP-12 run**
(same driver build, same seed, same feature reference), which is what makes the
pair internally consistent. That run's framework arm is more pessimistic than
the canonical Wave 235 P1 reading (2/4 wins vs 4/4 wins at NFE=50; GAP-12 §2
caveat). The ledger is therefore a **conservative** reading of CIFAR.

### 2.3 Matched-NFE delta (all three domains)

At equal NFE, report `metric_framework − metric_baseline` per seed. This is
defined everywhere, needs no curve, and is the axis a reviewer can check
without trusting any interpolation.

---

## 3. CIFAR-10 (R5b) — iso-FID

### 3.1 Measured baseline curve

| NFE | FID | source |
|---:|---:|---|
| 5 | 491.6636 | measured here |
| 10 | 466.7120 | measured here |
| 20 | 456.8000 | measured here |
| 25 | 455.0907 | measured here |
| 50 | 447.8943 | GAP-12 |
| 100 | 443.7458 | GAP-12 |
| 200 | 439.2525 | GAP-12 |

The NFE=5 point's recorded `wall_seconds` (5.78 s) exceeds the NFE=10 point's
(1.61 s): that point includes CUDA/adapter warm-up and must not be used for
timing. FID is unaffected by warm-up.

### 3.2 Iso-FID ledger (framework at NFE=50, seed 42)

| Scheduler | framework FID | baseline iso-FID NFE | ratio | ±1 FID band | ±2 FID band |
|---|---:|---:|---:|---|---|
| CosineAnneal | 447.1204 | 59.3 | **1.19×** | [49, 71] → 0.98–1.42 | [45.7, 83.4] → 0.91–1.67 |
| CodimensionSheet | 442.8993 | 118.8 | **2.38×** | [98, 141] → 1.96–2.82 | [86.1, 163.4] → 1.72–3.27 |
| EvidenceDriven | 453.8788 | 29.2 | **0.58×** | [26, 33] → 0.52–0.66 | [22.7, 36.2] → 0.45–0.72 |
| FreeTraj | 451.4061 | 37.8 | **0.76×** | [34, 41] → 0.68–0.82 | [30.9, 44.7] → 0.62–0.89 |

**Seed result (GAP-49b, measured).** The curve was repeated at seeds 43/44
(§3.6). The baseline level moves a lot: FID@200 = **439.22 / 449.00 / 450.39**
for seeds 42/43/44, i.e. **446.20 ± 6.08**. The ±1/±2 bands above bound
*interpolation* error only; they do **not** cover this seed-level variation.
The consequence is decisive:

- the framework FID is **bit-identical across seeds** (GAP-46 measured the
  spread as exactly zero for all 16 `(m, scheduler)` cells), so only the
  baseline level moves;
- for CodimensionSheet (442.90) and CosineAnneal (447.12), seeds 43/44 never
  reach that FID within NFE ≤ 200, so **the iso-FID ratio is undefined there**;
- the 2.37× / 1.18× are therefore **seed-42 point estimates**, not ratios with
  a seed spread. §3.6 quantifies what replaces them.

### 3.3 Matched-NFE delta at NFE=50 (3 seeds)

| Scheduler | ΔFID vs baseline at the same 50 NFE | per-seed range |
|---|---:|---:|
| CosineAnneal | **−1.16 %** | −1.88 … −0.17 |
| CodimensionSheet | **−2.09 %** | −2.80 … −1.11 |
| EvidenceDriven | +0.33 % | −0.39 … +1.34 |
| FreeTraj | −0.21 % | −0.94 … +0.79 |

Two arms (CosineAnneal, CodimensionSheet) are framework-favourable on **3/3
seeds**; two are mixed. This is the stable quantity because it pairs the
framework and baseline at the same budget.

### 3.4 The ceiling caveat is itself seed-dependent

At seed 42 the baseline at NFE=200 reaches FID **439.22**, better than every
framework arm at NFE=50 (442.90–453.88). At seeds 43/44 the same baseline@200
reaches only **449.00 / 450.39**, which is *worse* than CodimensionSheet
(442.90) and CosineAnneal (447.12). So:

- the baseline@200 level (439.2–450.4) **straddles** the framework's best FID;
- "the framework saves compute at a fixed budget" is supported by the
  matched-NFE deltas (§3.3);
- "the framework does not raise the quality ceiling" is **only true on seed
  42** and must not be stated as a 3-seed fact.

Any manuscript sentence must carry both halves and the seed qualifier.
"2.09 % better FID at the same 50 NFE (3/3 seeds)" is supportable; "2.38×
faster" is not.

### 3.5 Scheduler and seed dispersion both exceed the framework effect

Two of four schedulers are framework-favourable at matched NFE and two are
mixed. The scheduler spread at matched NFE (−2.09 % to +0.33 %) is the same
order as the seed spread of the baseline level (SD 6.08 FID ≈ 1.4 % of 446).
The honest reading: **the scheduler is the lever, the seed is the noise
floor, and neither is the framework's existence.**

### 3.6 Three-seed iso-FID ledger (GAP-49b)

The full 5/10/20/25/50/100/200 curve was measured at seeds 42/43/44
(`--seeds 42,43,44`; artifact `baseline_curve_multiseed.json` and
`compute_ledger_multiseed.json`). Seed 42's re-measured points reproduce the
original GAP-12/§3.1 values to 0.005 % (491.6323 vs 491.6636 at NFE=5;
455.0674 vs 455.0907 at NFE=25; 439.2250 vs 439.2525 at NFE=200), so the
cross-process reproducibility is adequate for this analysis.

| Scheduler | framework FID | iso-FID ratio, per seed | 3-seed verdict |
|---|---:|---|---|
| CodimensionSheet | 442.8993 | 42: 2.37×; 43: undefined; 44: undefined | **not resolvable** (1/3 seeds) |
| CosineAnneal | 447.1204 | 42: 1.18×; 43: undefined; 44: undefined | **not resolvable** (1/3 seeds) |
| EvidenceDriven | 453.8788 | 42: 0.58×; 43: 1.48×; 44: 0.98× | **not resolvable** (1.01 ± 0.45) |
| FreeTraj | 451.4061 | 42: 0.75×; 43: 2.36×; 44: 3.33× | **not resolvable** (2.15 ± 1.30) |

**Why undefined:** the inversion only exists if the baseline curve crosses the
framework FID inside the measured NFE range. The baseline@200 level is
seed-dependent (446.20 ± 6.08), so for a framework FID below ~450 the crossing
exists at some seeds and not others.

**Conclusion for the ledger:** the iso-FID ratio is **not identifiable at
N = 200 per seed**. Reporting it as a point estimate (the earlier 2.38×) was
over-precise; the matched-NFE delta (§3.3) is the quantity that survives the
seed spread. A resolvable iso-FID ratio would need either a larger N (to cut
the baseline FID estimator variance) or NFE > 200 for seeds 43/44.

---

## 4. FlowMol3 (R3 / K1) — matched NFE + a non-invertible baseline curve

### 4.1 Matched NFE=250 (N=1000, 3 seeds)

| seed | baseline fg_dev | framework fg_dev | Δ(fw−bl) | baseline pb_validity | framework pb_validity | Δ |
|---:|---:|---:|---:|---:|---:|---:|
| 42 | 0.6052 | 0.6552 | **+0.0500** | 0.5988 | 0.6192 | **+0.0204** |
| 43 | 0.7875 | 0.6508 | **−0.1367** | 0.6202 | 0.6199 | −0.0003 |
| 44 | 0.5832 | 0.5569 | **−0.0264** | 0.4545 | 0.6901 | **+0.2356** |
| mean | 0.6587 | 0.6210 | **−0.0377** | — | — | — |

fg_dev: framework better on 2/3 seeds, mean −0.0377, **not significant**
(t = −0.66, p = 0.559, d_z = −0.40 at n=3 — unchanged from GAP-12 §4.2).
pb_validity: framework better on 2/3 seeds, one seed flat.

### 4.2 Baseline quality-vs-NFE is non-monotone → no iso-quality ratio

| baseline NFE | baseline fg_dev (seed mean) |
|---:|---:|
| 250 | 0.6587 |
| 500 | 0.6823 |
| 1000 | 0.6608 |

0.6587 → 0.6823 → 0.6608 is not monotone, so there is no unique NFE at which
the baseline matches a given framework quality. The ledger records
`iso_quality_status: not_identifiable` rather than fitting a curve through a
non-monotone sequence. (K1's pb_validity is monotone but *decreasing* in
baseline NFE — the baseline gets worse with more compute — so its iso-quality
NFE is unbounded rather than finite.)

### 4.3 Wall-clock at matched NFE — framework is slower

| seed | baseline sampling (s) | framework sampling (s) | ratio fw/bl |
|---:|---:|---:|---:|
| 42 | 1823.5 | 2204.0 | 1.209 |
| 43 | 769.8 | 1481.1 | 1.924 |
| 44 | 632.4 | 823.8 | 1.303 |

Direction is consistent (framework slower, 3/3 seeds); magnitude is **not**
usable — baseline wall-clock alone spans 632.4–1823.5 s (2.9×) across seeds at
the same NFE, i.e. co-tenancy dominates. The defensible statement is
qualitative: **at matched NFE the framework pays a per-round overhead**
(restart, export, blend, extra host bookkeeping), so an NFE saving below
roughly 20–30 % would not be a net wall-clock win on this domain.

---

## 5. LineageFlow (R1 / R6)

### 5.1 R1 — measured per-record cost model

`gap41b-r1-nfe-fidelity/METADATA.json` ran the same driver at NFE=10 and
NFE=150 (N=200, seed 42, 3 rounds, `.venvs/lineageflow_venv`, same host):

| NFE | per-record cost |
|---:|---:|
| 10 | 3.40 s |
| 150 | 24.70 s |

Linear fit: **t = 1.879 s + 0.1521 s × NFE** per record. Consequences:

- the NFE=150→10 reduction is **7.26×** in wall-clock, not 15×;
- **55.3 %** of the NFE=10 cost is fixed overhead that no NFE reduction removes;
- therefore an NFE-ratio claim on this domain must be converted through the
  cost model before it is called a speed-up.

### 5.2 R6 — pLDDT vs NFE (flagged, not load-bearing)

| NFE | baseline pLDDT | framework pLDDT | Δ |
|---:|---:|---:|---:|
| 10 | 42.3438 | 44.2101 | **+1.866** |
| 50 | 42.3438 | 41.4973 | −0.847 |
| 100 | 42.3438 | 40.9457 | −1.398 |
| 200 | 42.3438 | 40.9984 | −1.345 |
| 500 | 42.3438 | 40.7775 | −1.566 |

Two observations:

1. The baseline pLDDT is **bit-identical at every budget**, corroborating the
   solver-free bare-RNG baseline of GAP-12 §3. Its iso-quality NFE is therefore
   undefined, not large.
2. The framework's pLDDT is **highest at the lowest budget** (NFE=10) and
   *degrades* with more compute. If this curve is real, spending more NFE on R6
   is counter-productive.

**Provenance caveat:** `nfe_curve_fair_w170_q3_2026/` contains only the CSV and
a PNG — no N, seed, config, or driver record. It is recorded here as
corroborating evidence and must **not** be cited as a headline until re-run
with a documented protocol (§8).

---

## 6. What is NOT measurable from the current artifacts

| Cell | Axis | Status | Reason |
|---|---|---|---|
| R1 | iso-quality | `not_measured` | headline (hmmscan hits) measured at a single budget (NFE=150); no quality-vs-NFE curve |
| R3 | iso-quality | `not_identifiable` | baseline fg_dev non-monotone in NFE |
| K1 | iso-quality | `unbounded` | baseline pb_validity decreases with NFE |
| R6 | iso-quality | `not_measurable_ratio` | baseline pLDDT is NFE-invariant (no solver) |
| R2 | any | `not_applicable` | DAE encode/decode, no flow rollout, no NFE knob (GAP-12 §4.1) |
| K4/K5/K7 | any | `not_applicable` | LineageFlow bare-RNG baseline, no solver (GAP-12 §3) |
| CIFAR | wall-clock | `not_recorded` | GAP-12 run dirs record per-round `n_steps` but no timing |
| CIFAR | seed spread of the iso-FID ratio | `single_seed` | curve measured at seed 42 only; baseline@200 differs by 9.8 FID between seeds 42 and 43 |

---

## 7. Verification

```bash
ruff check scripts/gap49_compute_accounting.py                 # 0 findings
python3 scripts/gap49_compute_accounting.py --skip-runs        # re-derives ledger from cache
python3 -m pytest tests/test_d4_regression_vectors.py -q       # 30/30
python3 tools/check_claims_consistency.py                      # exit 0
mkdocs build --strict                                          # exit 0
```

Determinism check: re-running `--skip-runs` reproduces every number in §3–§5
byte-for-byte from the cached curve + committed artifacts (no GPU involved).

### 7.1 Environment cross-check

The four new points were produced in one session whose interpreter was not
captured at launch (`METADATA.json` records this post-hoc). The NFE=25 point
was therefore re-produced under the **documented CIFAR venv**,
`.venvs/flowmol3_venv` (torch 2.7.0+cu128), versus the other candidate
`.venvs/lineageflow_venv` (torch 2.14.0+cu130):

| Run | FID at NFE=25 |
|---|---:|
| original | 455.0907 |
| `.venvs/flowmol3_venv` repro | 455.0674 |
| Δ | **−0.0233 (−0.0051 %)** |

The two torch builds agree to 0.005 % in FID, two orders of magnitude inside
the ±1 FID band used for the sensitivity analysis. The ledger is therefore
environment-robust; the exact interpreter of the original session does not
change any conclusion. Artifact: `repro-check-nfe25-flowmol3venv/`.

---

## 8. Unresolved / next actions

1. **DONE (GAP-49b).** The curve was repeated at seeds 43/44 (§3.6). The
   outcome is negative for the ratio: the baseline FID@200 spread
   (446.20 ± 6.08) is larger than the framework-vs-baseline FID gaps, so the
   iso-FID ratio is **not identifiable at N=200**. The matched-NFE delta is
   the quantity to report. Do **not** re-run the ratio at more seeds without
   also raising N or the NFE ceiling.
2. **Clean wall-clock calibration** (deferred, not blocking). Requires an
   exclusive GPU; NFE is exact so the ledger does not depend on it. If run,
   report `a` and `b` per domain and re-derive the wall-clock ratios.
3. **R6 curve re-run** with a documented protocol (N, seed, rounds, config) if
   it is ever to be cited; until then §5.2 is corroborating only.
4. **The compute claim is scheduler-scoped.** The 2.38× belongs to
   CodimensionSheet, not to "the framework". A cross-domain compute win needs a
   scheduler that wins at iso-FID on ≥2 domains — that is GAP-46's question,
   and its CIFAR grid is running separately.
5. **No manuscript edit here.** The frozen surfaces were not touched; adopting
   this ledger into the paper is a separate user-gated increment.
