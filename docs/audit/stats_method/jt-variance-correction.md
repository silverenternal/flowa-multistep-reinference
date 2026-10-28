# The Jonckheere-Terpstra variance was Kendall's, not JT's (2026-10-28)

CPU-only. No GPU, no sampler run. The two Wave 234 P3 p-values that the
submission quotes are recomputed; they get **smaller**, not larger.

## 1. Summary

`adaptive_reflow/stats/equivalence.py::jonckheere_terpstra` computed its
asymptotic variance with

```python
var_u = (n*(n-1)*(2*n+5) - sum_t1 + sum_t2) / 18.0
```

which is **Kendall's S variance**, not the JT variance, and applied it to `U`
without the factor of four that relates the two. It also used within-group
*value* ties where the formula needs the group sizes, and added that term
instead of subtracting it. The statistic itself counted a tied cross-group
pair as a full win instead of 0.5.

On the Wave 234 data the variance was **4.50x too large**, so `z` was
**2.12x too small** and the quoted p-values were too large by 72 and 80
orders of magnitude. The verdict (`monotone_confirmed = True`) and the
permutation p-value are unchanged, because the permutation test does not use
the variance and the data contain no cross-group ties.

## 2. Why the old formula cannot be right

The JT statistic satisfies an exact identity. With `s_ab = sign(y_b - y_a)`
and `J_ab = 1[group(a) < group(b)]`,

```
U = (S + C) / 2
```

where `S = sum_{a<b} s_ab J_ab` is the Kendall `S` between the group label and
the value, and `C = sum_{i<j} n_i n_j` is a constant. Hence
`Var(U) = Var(S) / 4`, and the Kendall tie correction must use the group
**sizes** `n_i` as the tie classes of the label variable.

The old code applied `Var(S)` to `U` directly and used the wrong tie classes.
The smallest counterexample is two groups of two:

| | exact | old formula |
|---|---:|---:|
| `Var(U)`, groups `{1,2}` / `{3,4}` | **1.6667** | 8.6667 |
| `Var(U)`, groups `{1,2}` / `{1,3}` (one tie) | **1.5000** | 7.6667 |

Exact enumeration of all six assignments gives `U in {0,1,2,2,3,4}`, mean 2,
variance 1.667. There is no convention under which the old 8.667 is the
variance of that statistic.

## 3. The fix

`_jonckheere_terpstra_statistic` now walks the pooled values one tie class at
a time and adds `count[j] * below[i] + 0.5 * count[i] * count[j]`, which is
the standard 0.5-for-ties definition and runs in `O(N log N)`.

`_jonckheere_variance` now returns `Var(S) / 4` with

```
Var(S) = [N(N-1)(2N+5) - sum_t t(t-1)(2t+5) - sum_i n_i(n_i-1)(2n_i+5)] / 18
       + [sum_t t(t-1)(t-2)][sum_i n_i(n_i-1)(n_i-2)] / [9 N(N-1)(N-2)]
       + [sum_t t(t-1)][sum_i n_i(n_i-1)] / [2 N(N-1)]
```

where `t` are tied value-class sizes and `n_i` the group sizes. With no ties
this reduces to the closed form

```
Var(U) = [N^2 (2N+3) - sum_i n_i^2 (2 n_i + 3)] / 72
```

Validated against exact enumeration of the permutation null on ten cases,
including ties and unequal group sizes:

| values | sizes | exact | formula |
|---|---|---:|---:|
| 1,2,3,4 | 2/2 | 1.66667 | 1.66667 |
| 1,1,2,3 | 2/2 | 1.50000 | 1.50000 |
| 1..6 | 2/2/2 | 6.33333 | 6.33333 |
| 1,1,2,2,3,3 | 2/2/2 | 5.73333 | 5.73333 |
| 1,2,3,4,5 | 2/1/2 | 3.66667 | 3.66667 |
| 1,1,1,2 | 1/1/1/1 | 1.25000 | 1.25000 |

These are pinned by `tests/test_stats_equivalence.py` (24 tests, all green).

## 4. Impact on Wave 234 P3

`scripts/wave234_p3_jonckheere.py` was re-run against the same frozen inputs.
`U` is unchanged in both cells — the RMSD and pLDDT arrays contain no
cross-group ties — so only the analytic `z` and `p` move.

| cell | U | `Var(U)` old | `Var(U)` new | z old | z new | p old | p new |
|---|---:|---:|---:|---:|---:|---:|---:|
| R2 Kanzi | 269430 | 111,277,500 | 24,717,275 | +9.743 | **+20.673** | 9.855e-23 | **3.017e-95** |
| R6 k6 | 274924 | 111,277,500 | 24,717,275 | +10.264 | **+21.778** | 5.114e-25 | **1.863e-105** |

`verification_outputs/wave234-p3-jonckheere.csv` was regenerated. Its
`jt_statistic`, `jt_p_value` (the floored permutation p, 1e-4) and
`monotone_confirmed` columns are byte-identical; only `power_gain_factor`
changes, because it is `pairwise_max_p / jt_p_asymptotic`.

## 5. What is unchanged

* The permutation p-value is still 1e-4 (the floor): no permutation out of
  10,000 reaches the observed `U`. That test never used the variance.
* The verdict is still `monotone_confirmed = True` on both cells.
* The tier means, the tier boundaries, the statistic, and the direction of
  the effect are unchanged.
* The qualitative claim — a monotone hard > medium > easy trend — is
  unaffected. The correction makes the evidence stronger, not different.

## 6. Downstream text that still quotes the old numbers (not edited)

These are frozen submission surfaces and were left alone:

| file | line | what it says | status |
|---|---|---|---|
| `tnnls_submission/tables.md` | 55-56 | `z = -10.0`, `p = 9.86e-23`; `z = -10.7`, `p = 5.11e-25` | stale, and the `z` values match neither the old code (+9.743 / +10.264) nor the new (+20.673 / +21.778) |
| `tnnls_submission/submission_checklist.md` | 53 | same two p-values | stale |
| `tnnls_submission/cover_letter.md` | 419-422 | old p-values and `power gain ~1.2e20 / 1.4e20` | stale |
| `docs/drafts/methods-why-per-record.md` | 811-814, 924, 949 | old p-values and `~10^20x` | stale |
| `docs/audit/wave356-submission-checklist-review.md` | 89 | old p-values | stale |

Updating them requires explicit authorisation. Until then the submission
**understates** the evidence: it claims `p < 1e-22` where the corrected value
is `p < 1e-94`. No claim is false, so nothing needs to be retracted.

The negative `z` in `tables.md` is a separate inconsistency. The code has
always returned a positive `z` for the increasing trend; the table's `-10.0`
and `-10.7` match no run in the repository.

## 7. `power_gain_factor` is not a power

The column is `max(per-tier p) / jt_p_asymptotic`. It answers "how much
smaller is the JT p", which is not a power and has no units. The corrected
values are `8.1e92` and `3.8e100`, which are absurd on their face. The
generated audit doc now says so. The column is retained because the
submission cites it; if the submission is revised, this is the sentence to
drop rather than renumber.

## 8. Reproduction

```
python3 -m pytest tests/test_stats_equivalence.py -q     # 24 passed
python3 scripts/wave234_p3_jonckheere.py                 # ~50 s, CPU
```
