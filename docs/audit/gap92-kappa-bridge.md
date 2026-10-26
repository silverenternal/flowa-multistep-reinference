# GAP-92 — the measured contraction orders the plateau gain (κ bridge)

**Status:** EXECUTED 2026-10-27. No GPU, no new sampling: this is a re-analysis
of two artifacts that already existed, plus a manuscript insertion.
**Question:** the manuscript says the two theorems do not determine the sign of
an FID change. True — but is there a *measured* quantity that does order it?

---

## 1. Why this exists

`paper-A-final.tex` §VI states, correctly, that conditional contraction and the
exact blend identity do not predict the sign of an FID change. A reviewer reads
that sentence as "the theory is decorative", and the paper does nothing to
contradict the reading.

But `GAP-78` measured a contraction `κ` on the same checkpoints under the same
flags, and `GAP-84` measured the frontier on those checkpoints. Nobody had put
the two next to each other. This document does.

## 2. What κ is

`tools/gap78_observable_screen.py:126`:

```python
# kappa: the realised contraction of the restart, tr(Sigma_fw)/tr(Sigma_base).
kappa = tr_fw / (tr_ref * rho)
```

`tr_fw` is the trace of the framework arm's projected feature covariance,
`tr_ref` the reference covariance trace, `ρ` the baseline's own dispersion
ratio. κ < 1 means the framework's output distribution is contracted relative
to the reference, scaled by the baseline's dispersion. It is computable at
inference time **without reference data**, which is what makes it a usable
diagnostic rather than another metric.

**Same protocol, different rung — stated, not glossed.** GAP-78 and GAP-84 share
the checkpoint set, the seeds (42/43/44), `N=1000`, `beta=0.3` and the
four-round equal-budget schedule (`--equal-total-nfe --beta-schedule
equal_budget --restart-t0-mode memory --mean-preserve --seed-keyed-prior
--shared-prior --n-rounds 4`). They do **not** share the budget: κ is computed
on the `NFE=50` runs (per-round `[25, 18, 6, 1]`), while the delta in the table
is the plateau over rungs 100 and 200. At `NFE=50` GAP-84's own rung reproduces
GAP-78's schedule exactly, so the two artifacts describe the same *protocol*
measured at two different *budgets*.

§3.1 is the check that this does not matter for the ordering: the same table
built on the `NFE=50` delta gives the same 2/2 split.

## 3. The table

κ averaged over the nine runs per checkpoint (3 seeds × 3 arms); the plateau
delta is GAP-84's, seven rungs, N=1000, seeds 42/43/44, floor rule 1 FID.

| checkpoint | opt steps | κ (mean ± sd) | 1 − κ | plateau Δ FID | Δ% | verdict |
|---|---:|---:|---:|---:|---:|---|
| `w16e1_5k` | 78 | 0.6666 ± 0.0010 | 0.3334 | −3.1206 | −12.75% | **WIN** |
| `w16e1_10k` | 156 | 0.7384 ± 0.0014 | 0.2616 | −1.0036 | −5.92% | TIE |
| `w16e1_60k` | 937 | 0.8931 ± 0.0041 | 0.1069 | +0.0150 | +0.13% | TIE |
| `production` | 2,811 | 0.9585 ± 0.0048 | 0.0415 | −0.0335 | −0.34% | TIE |

### 3.1 Same-budget cross-check

κ is measured at `NFE=50`; the plateau delta above is at `NFE` 100–200. To show
the ordering is not an artifact of that pairing, here is the same table built on
the `NFE=50` delta (GAP-78's own `evidence_driven` arm):

| checkpoint | κ | Δ FID @ NFE=50 | 95% CI @ NFE=50 | split |
|---|---:|---:|---|---|
| `w16e1_5k` | 0.667 | −12.7255 | [−12.9177, −12.5333] | gain |
| `w16e1_10k` | 0.738 | −5.9112 | [−6.2571, −5.5654] | gain |
| `w16e1_60k` | 0.893 | +0.1397 | [−0.1487, +0.4282] | floor |
| `production` | 0.959 | −0.3648 | [−0.7237, −0.0059] | floor |

The 2/2 split is identical at both budgets. Two details are worth recording
because they cut against a cleaner story:

* The `production` point is a *strict* gain at `NFE=50` (CI excludes 0) but sits
  inside the 1-FID floor, so it is a TIE under the paper's rule. The same
  checkpoint is `−0.03` at the plateau. The gain decays with budget; it does not
  reverse sign.
* Within the floor pair the ordering **inverts**: `w16e1_60k` is worse than
  baseline at both budgets (+0.14, +0.02) while `production` is better at both
  (−0.36, −0.03), even though κ says 60k < production. κ therefore separates
  "moves the plateau" from "does not"; it does not order the two within the
  floor, and the paper's sentence is written to claim only the former.

## 4. What the numbers say

**The ordering is exact.** κ sorts the four checkpoints into "gain" and "no
gain" with no error: the two below κ = 0.74 both move the plateau, the two above
κ = 0.89 both sit inside the floor. A practitioner could use κ as a gate.

**The ordering is not a correlation result.** Spearman ρ = 0.8 on n = 4,
which is not significant; with four points and a 2/2 split there are only six
possible splits, so a perfect sort has a 1-in-6 chance under a random ordering.
The honest claim is *consistent with a threshold*, not *establishes one*.

**The threshold is not identified.** The gap between κ = 0.7384 and κ = 0.8931
is where the boundary lies; nothing in this table locates it more precisely.

**κ is monotone in optimizer steps too.** 0.667 / 0.738 / 0.893 / 0.959 against
78 / 156 / 937 / 2,811. So κ and optimizer steps are collinear on this family,
and this table cannot say which one is doing the work. GAP-90 is what
disentangles them, because it adds a checkpoint (`w8e3`) whose optimizer-step
budget is identical to production's while its width differs.

## 5. What goes in the manuscript

A new subsection at the end of §VI, one small table, and one paragraph. The
paragraph must satisfy three constraints:

1. it must not claim the theorem predicts FID — only that a *measured* κ orders
   the observed deltas on this family;
2. it must state n = 4 and that the ordering is not significant;
3. it must not present the threshold as identified.

Draft text (inserted as §VI-D):

> **D. From the contraction diagnostic to a measured gate.** The theorems bound
> the composite map's contraction and the blend's squared error; neither fixes
> the sign of an FID change. A *measured* contraction, however, orders the
> observed deltas on the MNIST family. Table~\ref{tab:kappa-gate} reports κ —
> the trace ratio of the framework arm's projected covariance to the
> reference-scaled baseline dispersion, computed at NFE=50 without reference
> data — against the seven-rung plateau delta of the same four checkpoints under
> the same protocol. The two checkpoints with κ below 0.74 move the plateau; the
> two with κ above 0.89 sit inside the one-FID floor, and the same 2/2 split
> holds on the NFE=50 delta itself. With four points the ordering is consistent
> with a threshold but does not establish one, and κ is collinear with the
> optimizer-step budget on this family, so the table is a diagnostic and not an
> identification. It does mean the theory section is not decorative: the
> quantity the theorem bounds is measurable, and on this family it sorts the
> outcomes.

## 6. Artifacts

| file | role |
|---|---|
| `verification_outputs/gap78-kappa-dose-n1000-3seed/kappa_dose.json` | κ per cell/arm/seed (36 rows) |
| `verification_outputs/gap78-kappa-dose-n1000-3seed/r5c_report.json` | per-arm FID statistics |
| `verification_outputs/gap84-mnist-frontier/frontier_*.json` | plateau deltas |
| `tools/gap78_observable_screen.py` | κ definition |

No new artifact tree was created; the analysis is reproducible from the three
files above with the aggregation in §3.

## 7. Unresolved

1. **κ is collinear with optimizer steps** on this family (both monotone across
   the same four checkpoints). GAP-90's `w8e3` point — same steps as
   production, half the width — is the only available disambiguation.
2. **The threshold is a two-point boundary.** 0.74 < κ* < 0.89 is all the data
   support.
3. **κ has not been computed for any non-MNIST cell**, so nothing here says the
   gate transfers to protein or molecular adapters.
4. **κ is measured at one budget (NFE=50) while the delta is at the plateau.**
   §3.1 shows the 2/2 split survives at NFE=50, but κ at NFE=100/200 was never
   computed. If κ moves with budget, the gate would need a budget-specific
   threshold; nothing here rules that out.
5. **κ does not order the two floor checkpoints.** `w16e1_60k` (κ=0.893) is
   worse than baseline at both budgets while `production` (κ=0.959) is better.
   The paper claims only the gain/floor split for this reason.
