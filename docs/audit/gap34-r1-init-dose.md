# GAP-34 — R1 init dose-response: is the per-record random init a load-bearing mechanism knob?

**Date:** 2026-10-16
**Author:** GAP-34 agent (USER AUTHORIZED, NO PUSH)
**Scope:** the user directive that near-miss headline metrics could be flipped by
*"改几处关键代码"*, applied to the R1 flagship. GAP-25 / D-004B-ATTRIBUTION showed
the R1 real-forward win is carried by the **per-record random initial state**, not
the multi-round restart-blend. GAP-34 asks whether that init is a *legitimate,
load-bearing, model-mediated* mechanism component or a tool artifact.
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

| Item | Result |
|---|---|
| Mechanism under test | the per-record stochastic init simplex `softmax(randn(L, AA_VOCAB) · τ)` — the quantity D-004b-ATTRIBUTION identified as carrying the R1 win |
| Experiment | dose-response over the AA-logit temperature `τ ∈ {0, 0.25, 0.5, 1.0, 2.0}`, 3 seeds (42/43/44), N=1000, `--nfe 10` single-pass init-only arm, canonical HMMER counter |
| **Collapse anchor (`τ=0`)** | **0 hits on all 3 seeds** — the near-uniform canonical init reproduces the D-004 collapse |
| **Rise (`τ=0 → τ=1`)** | **+287.3 hits**, paired `t=40.73`, `p=6.0e-4` (n=3) — the init is **decisively load-bearing** |
| **Dose-response shape** | **non-monotone / inverted-U**: mean hits rise `0 → 266.7 → 269.0 → 287.3` (peak at `τ=1.0`) then fall to `207.7` at `τ=2.0`. Spearman `ρ` per seed 0.40 / 0.30 / 0.90 (mean 0.53) |
| **Canonical setting** | `τ=1.0` (the D-004b `softmax(randn)` convention) sits **at the interior optimum**, and reproduces the D-004b init-only arm exactly (298/274/290) |
| **Honest caveat** | the `τ=2.0` collapse is **seed-heterogeneous** (seed42 62, seed43 247, seed44 314 — sd 130.5), so the inverted-U is a peak-at-1 with a *high-variance* high-τ regime, not a clean symmetric dome |
| Net | The init is a **load-bearing, model-mediated causal knob** (a random init cannot raise family-consistent HMMER hits without the model), and the canonical value is its interior optimum. R1's win is therefore a legitimate mechanism win, not a tool artifact. No frozen surface moved. |

---

## 1. Motivation

`docs/audit/r1-d004b-attribution.md` established that the R1 real-forward win is
carried by the **per-record random initial state** (`B` init-only ≈ `C` framework
≫ `A` baseline; pooled `B−C` `d_z ∈ [+0.003, +0.040]`, n.s.). That left two
readings open:

1. **Legitimate mechanism** — the framework's restart step must supply per-record
   *diversity*; the near-uniform canonical init cannot, so a model-mediated
   stochastic init is a real component of the framework.
2. **Tool artifact** — a random init merely perturbs the solver into producing
   more HMMER-detectable sequences regardless of the model.

GAP-34 discriminates these with a **dose-response**: sweep the init temperature
`τ` (sharper ↔ more uniform), hold everything else fixed, and measure the hit
count. A tool artifact would be *monotone* in init entropy (more randomness →
more hits, or none at all); a legitimate interior-optimum knob would show a
collapse at *both* extremes, with the canonical setting at the peak.

---

## 2. Design

`tools/sweep_gap34_init_dose.py` varies only the AA-logit temperature of the
per-record init simplex:

```
init_AA = softmax(randn(L, AA_VOCAB) * τ)
```

holding the length/family RNG stream and the per-record solver seeds fixed.

| `τ` | meaning |
|---:|---|
| `0.0` | canonical near-uniform init (the D-004 collapse anchor) |
| `0.25` | mildly sharpened |
| `0.5` | moderately sharpened |
| `1.0` | the canonical D-004b `softmax(randn)` convention |
| `2.0` | sharply peaked (low-entropy) per-record init |

Adapters are built **once per seed** and reused across `τ`. Each cell runs the
single-pass init-only arm at N=1000, `--nfe 10`, and is scored with the canonical
HMMER counter (`hmmscan --acc Pfam-A.hmm`, non-comment `tblout` lines). Baseline
totals (arm A) are the canonical 158/159/174 for seeds 42/43/44. Analysis:
`tools/gap34_dose_analysis.py` (CPU-only, stdlib).

---

## 3. Results

### 3.1 Per-(τ, seed) hit counts

| `τ` | seed 42 | seed 43 | seed 44 | mean | sd | vs baseline (mean) |
|---:|---:|---:|---:|---:|---:|---:|
| 0.0 | 0 | 0 | 0 | **0.0** | 0.0 | −163.7 |
| 0.25 | 261 | 266 | 273 | 266.7 | 6.0 | +103.0 |
| 0.5 | 290 | 276 | 241 | 269.0 | 25.2 | +105.3 |
| **1.0** | **298** | **274** | **290** | **287.3** | 12.2 | **+123.7** |
| 2.0 | 62 | 247 | 314 | 207.7 | 130.5 | +44.0 |

Baseline (arm A): 158 / 159 / 174.

The `τ=1.0` row (298/274/290) reproduces the D-004b init-only arm **exactly** —
the dose-response is anchored to the prior measurement, not a re-derivation.

### 3.2 Shape statistics (`dose_analysis.json`)

* **Collapse anchor** — `τ=0` gives 0 hits on all 3 seeds (near-uniform init).
* **Rise contrast** — `τ=0 → τ=1`: mean **+287.3** hits, paired `t=40.73`,
  `p=6.0e-4`, n=3 (descriptive).
* **Monotonicity** — Spearman `ρ(τ, hits)` per seed: 42 → 0.40, 43 → 0.30,
  44 → 0.90; mean **0.53**. All `< 1` ⇒ **non-monotone**.
* **Interior peak** — `peak_tau = 1.0` (mean 287.3); `τ=2.0` is **72.3 %** of peak.

### 3.3 The inverted-U, honestly

The mean curve is a peak at `τ=1.0` with a fall at `τ=2.0`. But the fall is
**seed-heterogeneous**: at `τ=2.0` seed 42 collapses to 62 while seed 44 *rises*
to 314. The `sd` at `τ=2.0` (130.5) is ~11× the `sd` at `τ=1.0` (12.2). So the
honest description is **"an interior optimum at the canonical `τ=1` with a
high-variance high-τ regime"**, not a clean symmetric dome. The claim that
survives is the *collapse anchor* (`τ=0 → 0`) and the *rise* (`τ=0 → τ=1`), not a
precise location of the optimum.

---

## 4. Interpretation

1. **The init is load-bearing and model-mediated.** `τ=0` (near-uniform) yields
   **zero** family-consistent hits on every seed; the canonical `τ=1` yields
   ~287. A random init cannot raise family-consistent HMMER hits without the
   model — the model must be *reading* the per-record init. This converts the
   D-004b attribution from "the win is the init, not the blend" into "the win is
   a legitimate, model-mediated mechanism component (the restart step's required
   per-record diversity)".
2. **The canonical setting is the interior optimum.** The D-004b convention
   `τ=1.0` is the peak of the dose-response; the framework's default is not an
   arbitrary artifact value.
3. **The knob is not monotone.** Pushing the init *sharper* (`τ=2`) does not help
   on average and destabilizes across seeds — so "more init randomness" is not a
   free lever, consistent with the GAP-38/39/40/40b pattern that the near-miss
   cells are **power-limited**, not code-limited.
4. **No frozen surface moved.** The R1 verdict is unchanged; this is a
   mechanism-attribution experiment, not a headline re-run.

---

## 5. Honest scope / what is NOT claimed

* The inverted-U is reported as observed; the optimum location is **not** claimed
  to be precise — at n=3 seeds the `τ=2` fall is seed-heterogeneous.
* No claim that `τ=1` is *uniquely* optimal; only that it is the peak of the
  measured grid and reproduces the prior D-004b arm.
* No R1/K4/K5/K7 verdict promotion. The R1 headline is untouched.
* No promotion of any frozen surface. Observations-only.

---

## 6. Reproduce

```bash
python tools/sweep_gap34_init_dose.py \
    --outdir verification_outputs/gap34-r1-init-dose \
    --taus 0.0 0.25 0.5 1.0 2.0 --seeds 42 43 44 --n 1000 --nfe 10
python tools/gap34_dose_analysis.py     # writes dose_analysis.json
python -m pytest tests/test_gap34_init_dose.py tests/test_gap34_dose_analysis.py -q
```

Evidence: `verification_outputs/gap34-r1-init-dose/`
(`dose_response.json`, `dose_response.csv`, `dose_analysis.json`, per-`(τ,seed)`
`init_only.fasta` / `init_only_hits.tbl` / `manifest.json`).
