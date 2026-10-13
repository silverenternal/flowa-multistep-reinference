# GAP-27 — R3 power: a bounded-marginal cell, and a CI defect fixed

**Date:** 2026-10-13
**Branch:** main
**Base commit:** `630e9ea9`
**Scope:** determine the power R3 needs for a definitive verdict, bound the
effect at feasible n, and fix a seed-level CI defect found along the way.
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

| Item | Value |
|---|---|
| R3 seed-level test | n = 3 seeds, df = 2, mean −0.0377 fg_dev, t = −0.695, **p = 0.559**, `d_z = −0.401` |
| Power requirement | **~49 seeds** for 80 % power (two-sided α = 0.05); ~30 seeds to reach p < 0.05 at the observed effect |
| Cost | ~16 min/seed → ~13 GPU-hours for 49 seeds — infeasible here |
| CI defect found | the driver used a **normal 1.96** multiplier at **df = 2** (correct t = 4.303) → the recorded CI was ~2.2× too narrow |
| Material consequence | the baseline-NFE = 500 CI `[−0.117, −0.005]` **excluded 0** (false significance) while its p was 0.165; corrected to `[−0.184, +0.062]` (includes 0) |
| Verdict | R3 is a **bounded-marginal** cell (GAP-24 law regime C3): point estimate framework-favoured, not resolvable at feasible n; the corrected CIs include 0 at all three budgets |
| Acceptance | met via "clearly-bounded null (state the seeds needed)" — **~49 seeds** |

---

## 1. The seed-level test

R3 (`fg_dev`, lower is better) is a 3-seed N = 1000 paired sweep
(`scripts/wave338_p5_r3_n1000_paired.py`, real production FlowMol3 ckpt).
`verification_outputs/r3_n1000_3seed_fixed_q4_2026/wave338-p5-r3-n1000-paired.json`:

```
n_seeds = 3, mean_diff = -0.037687, sd_diff = 0.093899, se = 0.054213,
t = -0.695175, df = 2, p_raw = 0.558854, d_z = -0.401360
```

The direction is framework-favoured and consistent (it holds in sign at baseline
NFE = 500 and 1000 — `docs/audit/gap12-tuned-baseline.md` §4.2), but the
seed-level test is underpowered: the unit is the **seed** (n = 3), not the
record.

---

## 2. Power analysis

With the observed seed-level effect `d_z = −0.401`, the required sample size for
80 % power at two-sided α = 0.05 is

```
n = (z_{0.975} + z_{0.80})^2 / d_z^2 = (1.9600 + 0.8416)^2 / 0.4014^2 = 48.7  ->  49 seeds
```

The trajectory (projecting the current mean/SD):

| n seeds | SE | t | p (approx) | 95 % CI (t-based) |
|---:|---:|---:|---:|---|
| 3 (actual) | 0.0542 | −0.70 | 0.49 | [−0.271, +0.196] |
| 7 | 0.0355 | −1.06 | 0.29 | [−0.125, +0.049] |
| 10 | 0.0297 | −1.27 | 0.20 | [−0.105, +0.030] |
| 30 | 0.0171 | −2.20 | 0.03 | [−0.073, −0.003] |
| 49 | 0.0134 | −2.81 | 0.005 | [−0.065, −0.011] |

**Reading.** Even 10 seeds leaves the CI including 0; a definitive R3 verdict
needs **~30–49 seeds**. R3 is therefore a genuinely **marginal** cell — exactly
the GAP-24 law's regime **C3** (`1 < q < q*(m)`: the blend helps by a shrinking
margin). No feasible sweep resolves it; the honest outcome is a bounded null.

---

## 3. CI defect found and fixed

The driver's `_paired_summary` computed the seed-level CI with a hard-coded
**normal** multiplier:

```python
ci_low = mean - 1.96 * se     # df = n_seeds - 1 is reported, but 1.96 ignores it
```

At n = 3 (df = 2) the correct multiplier is `t_{0.975,2} = 4.3027`, so the
recorded CI was ~2.2× too narrow. The defect was **material**: at baseline
NFE = 500 the recorded CI `[−0.117, −0.005]` *excluded zero* — implying
significance — while the same record's `p_raw = 0.165` said otherwise.

Fixed in `scripts/wave338_p5_r3_n1000_paired.py` (uses
`scipy.stats.t.ppf(0.975, df=df)`, records `ci_95_t_crit`), and the three
committed paired JSONs were re-derived **without a GPU run** by
`tools/r3_reaggregate_paired_ci.py`:

| budget | old CI (1.96) | corrected CI (t, df = 2) |
|---|---|---|
| matched NFE = 250 | [−0.1439, +0.0686] | **[−0.2709, +0.1956]** |
| baseline NFE = 500 | [−0.1174, −0.0053] | **[−0.1844, +0.0616]** |
| baseline NFE = 1000 | [−0.1772, +0.0975] | **[−0.3413, +0.2616]** |

All three corrected CIs **include 0**, consistent with the p-values. No point
estimate, t, p, or verdict changed. Corrective addenda were added to the two
docs that had quoted the old CI (`r3-env-investigation.md`,
`gap02-r3-n1000-resolved.md`).

---

## 4. Verdict

GAP-27 acceptance ("R3 powered to significance, OR a clearly-bounded null
(state the seeds/molecules needed)") → **met via the second branch**.

* R3 is a **bounded-marginal** cell: the effect is framework-favoured but small
  (`d_z = −0.401`), and a definitive verdict needs **~49 seeds** (~13 GPU-hours).
* At the canonical n = 3 the effect is bounded within the corrected 95 % CI
  `[−0.271, +0.196]` fg_dev — consistent with zero.
* The CI defect that made R3 look closer to significance than it is has been
  fixed and the evidence corrected.

No frozen surface was changed; R3's PARTIAL / not-significant label is unchanged.

---

## 5. Guardrail compliance

| Guardrail (AGENTS.md §3) | Status |
|---|---|
| #1 vendored upstream byte-identical | ✅ untouched |
| #2 additive is the rule | ✅ driver CI fix + re-aggregation tool + audit; no point estimate/verdict changed; two docs got additive corrective addenda |
| #3 NO-PUSH | ✅ commit only |
| #4 honest uncertainty | ✅ the CI defect (which had *narrowed* the interval) is disclosed and corrected |
| #5 TNNLS freeze | ✅ no `tnnls_submission/` number moved |
| #6 per-increment audit doc | ✅ this file |
| #7 stricter = cleaner | ✅ the CI now uses the correct t multiplier |

---

## 6. Verification

| Gate | Result |
|---|---|
| `python tools/r3_reaggregate_paired_ci.py` | 3 JSONs corrected; all CIs now include 0 |
| `python -m pytest tests/test_d4_regression_vectors.py -q` | 30 passed |
| `ruff check scripts/ tools/` | All checks passed |
| `python tools/check_docs_against_code.py` | OK 4143 claims |
| `mkdocs build --strict` | exit 0 |

---

## 7. Unresolved / noted

- **The ~49-seed sweep is not run.** It is ~13 GPU-hours for a cell the law
  already classifies as marginal (C3); recorded as the concrete next step if a
  definitive R3 verdict is ever needed.
- **The per-record unit.** R3's `fg_dev` is aggregated per seed in this
  pipeline; a per-molecule paired test (if the metric were per-molecule) would
  carry far more power, but that is a metric-pipeline change, not a seed count.
