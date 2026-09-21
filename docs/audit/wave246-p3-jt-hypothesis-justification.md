# Wave 246 P3 — Jonckheere-Terpstra Hypothesis Justification

## TL;DR

The Jonckheere-Terpstra (JT) trend test's ordered alternative
`hard > medium > easy` (in framework uplift) was **NOT pre-registered**.
The ordering was **chosen post-hoc** after observing the Wave 198 P2 R6
scPerplexity monotone pattern, and was **NOT documented in any
§15.X** Wave pre-registration section before Wave 234 P3 ran the test.

This is an honest disclosure: the JT hypothesis ordering is
**exploratory**, not confirmatory. The strong monotone pattern the
test confirms (R2 Kanzi p ≈ 10⁻²³, R6 k6 p ≈ 10⁻²⁵) is **likely real
** given cross-adapter Wave 204 P2 confirmation, but the JT *test
itself* was motivated by the data, not by an a-priori theoretical
prediction. Future work should pre-register the JT ordering before
data collection.

## 1. JT hypothesis statement

The Wave 234 P3 audit doc (`docs/audit/wave234-p3-jonckheere.md`)
states the JT alternative as:

> `mean(easy) <= mean(medium) <= mean(hard)` (i.e. hard > medium >
> easy for framework uplift)

This ordering is **direction-equivalent across metrics with different
polarity**: for RMSD (lower=better) the framework_minus_baseline is
NEGATIVE on easy and POSITIVE on hard (Wave 198 P3 k6 RMSD analogue);
for pLDDT (higher=better) the framework_minus_baseline is POSITIVE on
hard and NEGATIVE on easy (Wave 198 P3 R6); both give the SAME
monotone shape `framework_minus_baseline increases easy -> hard`.

## 2. Pre-registration search

Searched `docs/CONSOLIDATED_RESULTS.md` for §15.X sections discussing the
JT hypothesis ordering, the monotone `hard > medium > easy` pattern,
or any pre-registration note.

**Result: NO pre-registration found.** The monotone `hard > medium >
easy` pattern first appears in the §15.91 / §15.95 (Wave 198 P2 / P4)
empirical stratification tables (Wave 198 P3 per-tier results table
showing hard d_z = +1.189, medium = +0.218, easy = −0.998 for
plddt_mean). This is a **post-hoc observation**, not a pre-registered
hypothesis.

The Wave 234 P3 audit doc (`docs/audit/wave234-p3-jonckheere.md` §1,
"Methodology") states the tier labelling follows Wave 233 P3, which
itself was motivated by Wave 225 P5 / P4 — the per-tier boundaries
(33rd / 67th percentile of baseline_metric) and the monotone-shape
ordering **emerged from Wave 198 P2 data analysis**, not from a
pre-registered theoretical prediction.

## 3. Data observation that motivated the ordering

The monotone `hard > medium > easy` pattern was first surfaced by
**Wave 198 P2 R6 k6 scPerplexity** (commit `ef7d18e`, documented in
`docs/CONSOLIDATED_RESULTS.md` §15.91):

| Tier | n | plddt_mean mean_diff | plddt_mean d_z | verdict |
|------|---:|---------------------:|-------------------:|---------|
| hard | 330 | +13.287 | +1.189 | SUPPORTED |
| medium | 340 | +2.585 | +0.218 | SUPPORTED |
| easy | 330 | -12.547 | -0.998 | REGRESSES |

The pattern was **reinforced** by Wave 204 P2 (commit 4e758c8,
§15.96 in `docs/CONSOLIDATED_RESULTS.md`) on a *second adapter*
(LineageFlow N=574):

> "the monotone `hard > medium > easy` pattern in pLDDT d_z is
> identical on both adapters: k6 hard/medium/easy = +1.189 / +0.218 /
> -0.998 (Wave 198 P3); lineageflow hard/medium/easy = +1.840 /
> +0.976 / -0.590 (Wave 204 P2)"

This **cross-adapter confirmation on 2 adapters** is the data
observation that motivated the Wave 233 P3 tier-aware scheduler
design and the Wave 234 P3 JT test.

## 4. Is the monotone pattern biologically motivated?

**Partially yes**, but the direction of the monotone is NOT a-priori
obvious:

- **A-priori argument for "framework helps more on harder records":**
  Adaptive inference schedules have more headroom to improve on
  records where the baseline struggles (low baseline_metric) than on
  records where the baseline already succeeds (high baseline_metric).
  This argues for the monotone `framework_uplift increases with
  baseline_difficulty` (equivalently, `framework_uplift DECREASES as
  baseline_metric improves`).
- **Counterargument (also a-priori):** Framework overhead may dominate
  on records where the baseline already does well, producing a
  REGRESSION on easy records. The framework-vs-baseline arms might
  even TIE on average.

The actual pattern — `framework_uplift positive on hard, near zero
on medium, negative on easy` — is consistent with the first argument
PLUS a regression-on-easy effect (likely due to the framework's
restart-blend prior-perturbation over-perturbing easy records where
the baseline is already converged). The Wave 235 P2 / P3 tier-aware
scheduler amplifies the easy reduction + hard amplification to
**convert the easy-tier regression into a near-zero uplift** without
hurting the hard-tier improvement.

**Conclusion.** The `hard > medium > easy` ordering has a defensible
post-hoc biological motivation (adaptive inference has more headroom
on hard records; restart-blend over-perturbs easy records). But the
**JT test as designed** (Wave 234 P3) **is exploratory** because:
(a) the ordering was chosen after seeing Wave 198 P2 R6 scPerplexity;
(b) no §15.X section pre-registered the ordering before Wave 234 P3.

## 5. Pre-registration verdict

`jt_hypothesis_pre_registered = False`

The JT test's ordered alternative was NOT pre-registered. It was
chosen post-hoc after observing the Wave 198 P2 R6 scPerplexity
monotone pattern. The Wave 234 P3 test confirms a real cross-adapter
monotone (Wave 204 P2 LineageFlow confirmation), but the **JT test
itself should be interpreted as exploratory**. Future work should
pre-register the JT ordering (e.g. "framework uplift is monotone
non-decreasing in baseline difficulty") before data collection.

## 6. Mitigation

The paper draft (`docs/drafts/section-2-method.md` §2.8) is being
updated (Wave 246 P3 §2.12.X) to explicitly label TOST, BF01, JT as
**exploratory / post-hoc** statistical methods chosen after Wave 198
P2 R6 scPerplexity observation, with a Limitations sentence stating:

> "These post-hoc analyses should be interpreted as exploratory;
> future work should pre-register these tests before data collection."

The honest reading of the JT test is:

1. **Structural finding:** framework uplift varies monotonically with
   baseline difficulty across the 3-tier stratification (R2 Kanzi
   Bonferroni-sig at p ≈ 10⁻²³; R6 k6 Bonferroni-sig at p ≈ 10⁻²⁵).
2. **Mechanism:** the monotone is likely a combination of (a) headroom
   for adaptive improvement on hard records + (b) over-perturbation
   on easy records. Wave 235 P2 / P3 tier-aware scheduler designs
   explicitly materialise the easy-reduction axis.
3. **Generalisability:** the monotone holds cross-adapter (Wave 198
   P3 k6 + Wave 204 P2 LineageFlow), so the finding is not
   adapter-specific.
4. **Pre-registration status:** NOT pre-registered; should be
   pre-registered in future work.

## 7. Cross-references

- `docs/audit/wave234-p3-jonckheere.md` — Wave 234 P3 audit doc that
  runs the JT test on R2 Kanzi + R6 k6.
- `docs/CONSOLIDATED_RESULTS.md` §15.91 (Wave 198 P4) — original
  observation of the monotone `hard > medium > easy` pattern on
  R6 k6 per-tier plddt_mean.
- `docs/CONSOLIDATED_RESULTS.md` §15.96 (Wave 204 P3) — cross-adapter
  confirmation of the monotone on LineageFlow.
- `docs/CONSOLIDATED_RESULTS.md` §15.97 / §15.98 — Wave 208 P4
  cross-adapter paper-quantity-vs-cosine ablation documenting
  framework-vs-baseline direction consistency.
- `scripts/wave234_p3_jonckheere.py` — JT test implementation.
- `adaptive_reflow/stats/equivalence.py::jonckheere_terpstra` — JT
  implementation.

---

*Generated by Wave 246 P3 audit doc.*