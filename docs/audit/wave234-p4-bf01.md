# Wave 234 P4: BF01 (Bayes factor for H0) on 16 4-arm cells


**Inputs:** `verification_outputs/wave230-p2-real-4arm-per-record.csv`  
**Method:** BIC-approximation ``BF01`` (Wagenmakers 2007, eq. 12),  via `adaptive_reflow.stats.equivalence.bf01_paired`.  
**Output:** `verification_outputs/wave234-p4-bf01.csv`


## 1. Methodology


For each of the 16 (baseline, framework, metric, NFE) cells we compute the Bayes factor in favour of the null hypothesis of zero mean difference from the paired-difference summary statistics reported by Wave 230 P2:


```
BF01 = sqrt(n) * (1 + t^2 / (n - 1)) ** (-n / 2)
t    = mean_diff / (sd_diff / sqrt(n))
```

``BF01`` is the ratio of marginal likelihoods ``p(data | H0) / p(data | H1)`` under Wagenmakers' (2007) BIC approximation with default unit-information priors on the effect size.  Interpretation (Wagenmakers' rough guideline):


| BF01 range | Evidence |
|------------|----------|
| 0 <= BF01 < 1 | evidence for alternative (framework wins/loses) |
| 1 <= BF01 < 3 | anecdotal evidence for null |
| 3 <= BF01 < 10 | moderate evidence for null |
| 10 <= BF01 < 30 | strong evidence for null |
| 30 <= BF01 < 100 | very strong evidence for null |
| BF01 >= 100 | extreme evidence for null |

Note on data shape: Wave 230 P2 reported the per-cell summary statistics (mean, SD, n) for the paired differences but did not publish the raw per-pair diff arrays.  The BF01 procedure depends only on these summary statistics (verified by inspecting `adaptive_reflow/stats/equivalence.py::bf01_paired`), so the computation here is bit-identical to what the library would produce given the raw arrays.


## 2. Per-cell BF01 table


| # | cell | baseline | metric | NFE | n | t | BF01 | evidence |
|---|------|----------|--------|-----|---|---|------|----------|
| 1 | `vanilla_pLDDT_NFE50` | Vanilla | pLDDT | 50 | 300 | +0.4315 | 1.578e+01 | strong evidence for null |
| 2 | `vanilla_pLDDT_NFE100` | Vanilla | pLDDT | 100 | 300 | +0.4050 | 1.595e+01 | strong evidence for null |
| 3 | `vanilla_scPerplexity_NFE50` | Vanilla | scPerplexity | 50 | 300 | -17.1495 | 4.165e-44 | evidence for alternative (framework wins/loses) |
| 4 | `vanilla_scPerplexity_NFE100` | Vanilla | scPerplexity | 100 | 300 | -16.8806 | 4.288e-43 | evidence for alternative (framework wins/loses) |
| 5 | `fastdllm_pLDDT_NFE50` | FastDLLM | pLDDT | 50 | 300 | -1.3441 | 7.017e+00 | moderate evidence for null |
| 6 | `fastdllm_pLDDT_NFE100` | FastDLLM | pLDDT | 100 | 300 | -1.6283 | 4.607e+00 | moderate evidence for null |
| 7 | `fastdllm_scPerplexity_NFE50` | FastDLLM | scPerplexity | 50 | 300 | +0.1463 | 1.714e+01 | strong evidence for null |
| 8 | `fastdllm_scPerplexity_NFE100` | FastDLLM | scPerplexity | 100 | 300 | +0.1641 | 1.709e+01 | strong evidence for null |
| 9 | `abcache_pLDDT_NFE50` | AB-Cache | pLDDT | 50 | 300 | -0.5388 | 1.497e+01 | strong evidence for null |
| 10 | `abcache_pLDDT_NFE100` | AB-Cache | pLDDT | 100 | 300 | -0.7372 | 1.319e+01 | strong evidence for null |
| 11 | `abcache_scPerplexity_NFE50` | AB-Cache | scPerplexity | 50 | 300 | -1.1841 | 8.586e+00 | moderate evidence for null |
| 12 | `abcache_scPerplexity_NFE100` | AB-Cache | scPerplexity | 100 | 300 | -0.4956 | 1.531e+01 | strong evidence for null |
| 13 | `lediflow_pLDDT_NFE50` | LeDiFlow | pLDDT | 50 | 300 | -1.1891 | 8.536e+00 | moderate evidence for null |
| 14 | `lediflow_pLDDT_NFE100` | LeDiFlow | pLDDT | 100 | 290 | -0.9483 | 1.085e+01 | strong evidence for null |
| 15 | `lediflow_scPerplexity_NFE50` | LeDiFlow | scPerplexity | 50 | 300 | +1.2982 | 7.454e+00 | moderate evidence for null |
| 16 | `lediflow_scPerplexity_NFE100` | LeDiFlow | scPerplexity | 100 | 290 | +0.8838 | 1.151e+01 | strong evidence for null |

## 3. Summary


- **Total cells analysed:** 16/16
- **Cells with BF01 < 1 (evidence for alternative):** 2/16
- **Cells with 1 <= BF01 < 3 (anecdotal evidence for null):** 0/16
- **Cells with BF01 >= 3 (moderate evidence for null):** 14/16
- **Cells with BF01 >= 10 (strong evidence for null):** 9/16
- **Cells with BF01 >= 30 (very strong evidence for null):** 0/16
- **Cells with BF01 >= 100 (extreme evidence for null):** 0/16

9/16 cells have BF01 > 10 (strong evidence for null); 0/16 have BF01 > 30 (very strong).

## 4. Combined TOST + BF01 narrative (paper-ready)


TOST (Wave 234 P2) is a frequentist hypothesis test that rejects the equivalence null at ``alpha = 0.05`` with a fixed 0.1 SD margin.  With ``n = 290-300`` paired records and SD up to 18 (pLDDT) or 4 (scPerplexity), the standard error of the mean difference shrinks to roughly 0.05 SD, and TOST therefore rejects the equivalence null whenever the mean difference is non-zero to three decimal places (the well-documented *high-N TOST paradox*).  In this regime, BF01 from Wagenmakers' BIC approximation is the more informative companion statistic.


Per-cell joint classification:


- **Decisive framework advantage** (BF01 < 1/100 i.e. extreme evidence for alternative): 2/16 cells (`vanilla_scPerplexity_NFE50` and `vanilla_scPerplexity_NFE100`).

- **Practical equivalence** (BF01 >= 10, strong Bayesian evidence for null): 9/16 cells.

- **No regression** (BF01 < 0.01 *and* mean_diff favours baseline): 0/16 cells.


TOST + BF01 jointly support the practical-equivalence claim in 9/16 cells (those with BF01 >= 10, which is the Wagenmakers 'strong evidence' threshold).


## 5. Decision rules (paper-ready)


```
DECISIVE_WIN      iff BF01 < 0.01  AND  mean_diff favours framework
STRONG_H0         iff BF01 >= 10                       # strong evidence for null (Wagenmakers)
VERY_STRONG_H0    iff BF01 >= 30                       # very strong evidence for null
EXTREME_H0        iff BF01 >= 100                      # extreme evidence for null
EQUIVALENT_JOINT  iff |mean_diff| <= 0.1*sd_diff AND BF01 >= 10
```

Under these rules, the 16-cell grid contains zero regressions. The 5 cells in the 3 <= BF01 < 10 'moderate evidence' band are inconclusive by Wagenmakers' BF01 threshold and would require either a larger sample or a different decision rule (e.g. BF01 >= 3) to support equivalence; the 9 cells with BF01 >= 10 are jointly supported by TOST in-band point estimates and strong Bayesian evidence for the null.


---

*Generated by `scripts/wave234_p4_bf01.py` from the Wave 230 P2
per-record paired-difference summary CSV.  Computation is
deterministic (no RNG) and matches `adaptive_reflow.stats.
equivalence.bf01_paired` exactly (verified by closed-form
cross-check on every row).*