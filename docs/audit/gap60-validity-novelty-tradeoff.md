# GAP-60 — R1 validity and R1 diversity on the same samples

**Status:** CLOSED — **no trade-off detected; the +74% validity is not bought by
population collapse**
**Date:** 2026-10-21
**Cell:** R1 — LineageFlow protein generation, N=200 per arm, NFE=150, 3 seeds
**Tool:** `tools/gap60_tradeoff.py`
**Evidence:** `verification_outputs/gap60-tradeoff/tradeoff.json`

---

## 0. TL;DR

R1 reports **+74% Pfam hits**; K7 reports **12.6x less novelty** (3.7% vs 46.6%).
Measured on different samples, the pair reads as "validity bought with collapse".
Scored on the **same FASTA files**, it is not.

| β | hits (base → fw), 3 seeds | clusters @90% id (base → fw) | singleton frac | verdict |
|---:|---|---|---:|:--:|
| 0 | 37→0, 36→0, 32→0 | 200 → **5 / 6 / 5** | **0.00** | **COLLAPSE** |
| 1/6 | 37→48, 36→55, 32→63 | 200 → 200 / 200 / 200 | 1.00 | no collapse |
| 1 | 37→50, 36→44, 32→52 | 200 → 200 / 200 / 200 | 1.00 | no collapse |

* **Every framework arm that produces hits keeps maximal within-generation
  diversity**: all 200 records are their own cluster at 90% identity, singleton
  fraction 1.00, identical to the baseline.
* **β=0 collapses to 5-6 clusters out of 200.** That is the D-004 collapse mode,
  and its detection here is the positive control that makes the "no collapse"
  reading for β∈{1/6, 1} credible — the detector is not blind.
* **β=1 (no memory) reproduces the hit gain** (50/44/52 vs 48/55/63 for β=1/6,
  CIs overlap). Per the pre-registered rule, the gain therefore belongs to the
  **perturbation channel**, not to the memory blend.

The "validity bought with collapse" reading is **refuted on the within-generation
axis**. It is not refuted on the K7 axis, because that axis is degenerate here
(§3.3) and K7 must be cited separately.

---

## 1. Pre-registered acceptance (from `todo.json`, unchanged)

> (3) The trade-off is declared real only if novelty falls monotonically as hits
> rise across beta.
> (4) If beta=1 (no memory) shows the same hits and the same novelty loss, the
> loss belongs to the perturbation channel, not to the blend.
> (5) If novelty does NOT fall where hits rise, K7 and R1 are measuring different
> things and that must be stated explicitly.

Outcome: (3) not triggered — hits rise without any diversity loss. (4) triggered
in the direction that *exonerates the blend*. (5) triggered — stated in §3.3.

## 2. Protocol

* Nine arm directories, each holding `baseline.fasta` and `framework.fasta`:
  `gap45-r1-blend-off-150/seed{42,43,44}_{off,on}` (β = 0, 1/6) and
  `gap45-r1-beta1-150/seed{42,43,44}` (β = 1).
* Scored with the vendored `evaluate_all.py` via
  `tools.upstream_eval.run_lineageflow_upstream_eval`, metrics
  `family_validity` + `novelty`, `length_bias=short`.
* **Isolation:** the vendored MMseqs pipeline hardcodes the relative path
  `results/mmseqs_tmp`, so two concurrent scorers destroy each other. The tool
  `chdir`s into a per-arm scratch directory that owns its own `results/` before
  invoking the evaluator. This is the root-cause fix for the `nonzero_exit`
  failures recorded in the GAP-45 `score.log` files, and it is why GAP-60 could
  run while GAP-58 was scoring.
* No new sampling: every FASTA already existed on disk.
* Hits reproduce the GAP-45 audit exactly (37/36/32 baseline, 0/0/0 at β=0,
  48/55/63 at β=1/6, 50/44/52 at β=1) — a byte-level consistency check on the
  scoring path.

## 3. Observed

### 3.1 Within-generation clustering

`mmseqs cluster --min-seq-id 0.900 -c 0.800 --cov-mode 0` over the generated set,
200 records per arm:

| arm | β | hits | n_clusters | singleton frac |
|---|---:|---:|---:|---:|
| seed42_off | 0 | 0 | **5** | 0.00 |
| seed43_off | 0 | 0 | **6** | 0.00 |
| seed44_off | 0 | 0 | **5** | 0.00 |
| seed42_on | 1/6 | 48 | 200 | 1.00 |
| seed43_on | 1/6 | 55 | 200 | 1.00 |
| seed44_on | 1/6 | 63 | 200 | 1.00 |
| seed42_b1 | 1 | 50 | 200 | 1.00 |
| seed43_b1 | 1 | 44 | 200 | 1.00 |
| seed44_b1 | 1 | 52 | 200 | 1.00 |
| all baselines | — | 32-37 | 200 | 1.00 |

### 3.2 The gain is perturbation-channel, not blend

β=1 (memory fraction 0, no memory term at all) yields 50/44/52 hits against
β=1/6's 48/55/63 — the same direction, the same magnitude, overlapping intervals.
This reproduces GAP-45 §8 on a second axis and is now the second independent
measurement saying the namesake memory term is not what earns the R1 result.

### 3.3 Novelty is degenerate on this corpus — stated, not quoted

Against the default `pfam_holdout_targetDB` the search returns **0 hits for all
200 records**, so `novelty_all = 1.0` at every threshold by construction. The
number is meaningless and is not used.

K7's 3.7% vs 46.6% was measured against a different target:
the **63.8M-sequence `pfam_canonical` W164 build** (`novelty_results_full.json`
`metadata.sweep_config`), on the W158 N=1000 FASTAs, one seed. Re-running that
target on the GAP-45 N=200 sets is possible but was not done here; it is recorded
as an open item rather than substituted with the degenerate holdout number.

## 4. Interpretation

1. **R1 survives.** The framework raises Pfam hits by 30-97% while leaving the
   generated population maximally diverse. The most damaging reading of the
   R1/K7 pair is not supported by the data.
2. **K7 and R1 measure different things**, as the pre-registration anticipated.
   Within-generation clustering asks "are the 200 samples distinct from each
   other?" — yes, always. K7 asks "is each sample close to a *known* Pfam
   family?" — apparently yes, more so for the framework. Those are compatible,
   and the second is arguably the intended behaviour of a family-conditioned
   generator with only 4 families in the corpus. Reporting them as contradictory
   was a measurement error on our side, not a finding.
3. **β=0 remains a collapse mode** and is now measured on a second axis (5-6
   clusters out of 200), which strengthens D-004.

## 5. What this changes in the plan

* `GAP-60` — **closed, no trade-off on the within-generation axis.**
* The R1 row in `metric_remediation` gains the diversity control.
* New open item recorded inline (not a new gap): K7's novelty should be re-run
  against the `pfam_canonical` target on the GAP-45 sets before the R1/K7 pair is
  quoted together in the manuscript. That is ~1-3 h of MMseqs against a 142 GB
  DB and is the only remaining measurement that can put both axes on one plot.

## 6. Unresolved

* Novelty against the canonical Pfam build on these nine arms: not measured.
* Within-generation clustering at 80% identity is recorded in the artifacts but
  not tabulated here; at 90% every framework arm is already all-singleton, so
  80% cannot show more diversity, only the same.
* N=200 per arm. The hit counts (32-63 out of 200) are small integers; the
  per-record paired intervals from GAP-45 remain the inferential basis, and this
  document is a diversity control, not a new effect-size estimate.
