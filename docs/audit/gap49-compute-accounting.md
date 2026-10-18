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
(+ `baseline_curve.json`, `baseline-nfe{5,10,20,25}/`).
**Driver:** `scripts/gap49_compute_accounting.py` (`--skip-runs` re-analyses
from the cached curve without touching the GPU).

---

## 0. TL;DR

| Item | Value |
|---|---|
| Primary compute unit | **NFE** (exact, hardware-independent, same checkpoint + solver) |
| New GPU work | 4 baseline points, N=200, seed 42, `cuda:0` |
| CIFAR iso-FID, CodimensionSheet | baseline needs **118.8 NFE** to match framework@50 → **2.38×** (interpolation band 1.96–2.82 at ±1 FID; **seed 42 only**) |
| CIFAR iso-FID, CosineAnneal | 59.3 NFE → **1.19×** (fragile: 0.98–1.42 at ±1 FID) |
| CIFAR iso-FID, EvidenceDriven / FreeTraj | **0.58× / 0.76×** — framework *costs* compute at matched quality |
| CIFAR ceiling | baseline@200 NFE = **439.25 FID**, better than all four framework arms → the win is **budget-conditional, never a quality-ceiling win** |
| FlowMol3 matched NFE=250 | fg_dev mean Δ(fw−bl) = **−0.0377** (n.s., n=3); pb_validity **+0.020 / −0.0003 / +0.236** |
| FlowMol3 iso-quality | **not identifiable** — baseline fg_dev is non-monotone in NFE |
| FlowMol3 wall-clock at matched NFE | framework **slower on 3/3 seeds** (1.21 / 1.92 / 1.30×) |
| LineageFlow R1 cost model | **1.879 s fixed + 0.1521 s/NFE** per record; fixed = **55.3 %** of the NFE=10 cost |
| LineageFlow R1/R6 iso-quality | **not measured / not measurable** (see §6) |

**One sentence:** the framework's measured, robust compute claim is
"at a fixed 50-NFE budget, one scheduler matches a baseline that needs ~2.4×
the NFE" — not "2.5–10× faster", and not "better at any budget".

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

### 3.2 Iso-FID ledger (framework at NFE=50)

| Scheduler | framework FID | baseline iso-FID NFE | ratio | ±1 FID band | ±2 FID band |
|---|---:|---:|---:|---|---|
| CosineAnneal | 447.1204 | 59.3 | **1.19×** | [49, 71] → 0.98–1.42 | [45.7, 83.4] → 0.91–1.67 |
| CodimensionSheet | 442.8993 | 118.8 | **2.38×** | [98, 141] → 1.96–2.82 | [86.1, 163.4] → 1.72–3.27 |
| EvidenceDriven | 453.8788 | 29.2 | **0.58×** | [26, 33] → 0.52–0.66 | [22.7, 36.2] → 0.45–0.72 |
| FreeTraj | 451.4061 | 37.8 | **0.76×** | [34, 41] → 0.68–0.82 | [30.9, 44.7] → 0.62–0.89 |

**Seed caveat (load-bearing).** The whole curve and all four arms are
**seed 42 only**. The baseline FID at a fixed NFE is itself seed-sensitive: the
GAP-46 grid measures baseline@200 NFE at **439.2569 (seed 42)** and
**449.0180 (seed 43)**, a 9.8-FID spread. The ±1/±2 bands above bound
*interpolation* error only; they do **not** cover seed-level variation. The
defence is that the framework and baseline arms come from the same seed, so
the *difference* (CodimensionSheet −5.0 FID at NFE=50) should be more stable
than the level — but that is an argument, not a measurement. Until the curve
is repeated at seeds 43/44, the 2.38× must be read as a **seed-42 estimate**
(see §8, action 1).

### 3.3 Matched-NFE delta at NFE=50

| Scheduler | ΔFID vs baseline (same NFE) |
|---|---:|
| CosineAnneal | −0.17 % |
| CodimensionSheet | −1.12 % |
| EvidenceDriven | +1.34 % |
| FreeTraj | +0.78 % |

### 3.4 The ceiling that must be stated

The baseline at NFE=200 reaches FID **439.2525**, which is better than every
framework arm at NFE=50 (442.90–453.88). So:

- the framework **saves compute at a fixed budget** (CodimensionSheet: 2.38×);
- the framework **does not raise the quality ceiling** — give the baseline 4×
  the NFE and it wins on all four schedulers (GAP-12 §2, `0/4` wins).

Any manuscript sentence must carry both halves. "2.38× fewer NFE at matched
quality, in the ≤50-NFE regime" is supportable; "2.38× faster" is not.

### 3.5 Scheduler dispersion is larger than the framework effect

Two of four schedulers *cost* compute at matched quality (0.58×, 0.76×) while
one saves 2.38×. The spread across schedulers (0.58×–2.38×) dwarfs the
framework-vs-baseline difference at fixed NFE (−1.12 % to +1.34 % FID). The
honest reading: **the scheduler is the lever, not the framework's existence.**

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

1. **Repeat the curve at seeds 43/44** (8 points, ~15 min on an exclusive
   GPU). This is the highest-value follow-up: it converts the only positive
   compute number (2.38×) from a seed-42 estimate into a 3-seed estimate with
   a real seed spread. Deferred only because `cuda:0` is held by the GAP-46
   grid.
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
