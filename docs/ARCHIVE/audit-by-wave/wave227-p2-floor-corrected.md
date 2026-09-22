# Wave 227 P2 — Per-Seed d_z Floor: Correct Math Audit

**Wave:** 227 P2
**Date:** 2026-09-21
**Status:** COMPLETE — correct math (per DeepSeek) reproduces the Wave 226 P3
values bit-identically. Wave 226 P3's `d_z_upper_bound` column was already
correct (3.7522 scPerplexity / 0.9051 pLDDT). The "2.21 / 0.53" claim
attributed to Wave 226 P3 is not present in either the CSV or audit doc.

---

## TL;DR

| Quantity | Value | Source |
|---|---:|---|
| $A_g$ (default profile, all 12 adapters) | 0.8549457422 | `verification_outputs/wave226-p1-a-g-values.csv` |
| $e^{A_g}$ | 2.3512468036 | derived |
| $d$ (data dimension, representative protein-FM) | 512 | `docs/audit/wave226-p2-methods-paragraph.md` (`n_channels_decoder`) |
| $\sigma_{\text{record}}$ (pLDDT, LineageFlow n=574) | 15.177 | `verification_outputs/wave202-p5-lineageflow-per-record.csv` |
| $\sigma_{\text{record}}$ (scPerplexity, LineageFlow n=574) | 3.661 | same file |
| Noise floor (n=30) | 13.7369 | $e^{A_g}\cdot\sqrt{2\cdot 512/30}$ |
| Noise floor (n=29) | 13.9717 | $e^{A_g}\cdot\sqrt{2\cdot 512/29}$ |
| $d_z^{\text{floor}}$ pLDDT (n=30) | **0.9051** | 13.7369 / 15.177 |
| $d_z^{\text{floor}}$ pLDDT (n=29) | **0.9206** | 13.9717 / 15.177 |
| $d_z^{\text{floor}}$ scPerplexity (n=30) | **3.7522** | 13.7369 / 3.661 |
| $d_z^{\text{floor}}$ scPerplexity (n=29) | **3.8164** | 13.9717 / 3.661 |

| Counter | Value |
|---|---:|
| n_cells_total | 16 |
| n_cells_floor_calculated | 16 |
| **n_cells_consistent_with_bound_corrected** | **14** |
| n_cells_inconsistent | 2 (vanilla scPerplexity NFE50 / NFE100 — SUPPORTED but bound-underpowered) |
| n_cells_consistent_in_wave_226_P3 (correct math, same) | 14 |
| n_cells_consistent_under_hypothetical_incorrect_floor_2.21_0.53 | 14 (same set) |

---

## What DeepSeek flagged vs. what Wave 226 P3 actually reports

DeepSeek's flag (per task description): "Wave 226 P3 reports per-seed d_z floor
= 2.21 (scPerplexity) and 0.53 (pLDDT) but correct math gives 3.75
(scPerplexity) and 0.904 (pLDDT)."

Inspection of `verification_outputs/wave226-p3-per-seed-variance-bound.csv`
and `docs/audit/wave226-p3-variance-bound.md` shows the Wave 226 P3 output
already uses the correct math:

| metric | n_seed | Wave 226 P3 `d_z_upper_bound` | Correct math | Match |
|---|---:|---:|---:|---|
| pLDDT | 30 | 0.9051 | 0.9051 | YES |
| pLDDT | 29 | 0.9206 | 0.9206 | YES |
| scPerplexity | 30 | 3.7522 | 3.7522 | YES |
| scPerplexity | 29 | 3.8164 | 3.8164 | YES |

The "2.21 / 0.53" numbers do not appear anywhere in
`verification_outputs/wave226-p3-*` or `docs/audit/wave226-p3-*.md`. The
flag is therefore either a transcription error in the upstream message or a
reference to a different artifact. This audit recomputes the floor from
the correct formula independently and confirms the Wave 226 P3 values
are bit-identical to the correct math.

---

## Method (Step 5 of the "Why Per-Record Analysis" argument)

For each of 16 cells in the 4-arm Table B:

$$
d_z^{\text{floor}}
   \;=\; \frac{e^{A_g}\cdot\sqrt{2d/n_{\text{seed}}}}{\sigma_{\text{record}}}
$$

A cell is **bound-underpowered** if $|d_z_{observed}| < d_z^{floor}$, else
**bound-powered**. A 4-arm **underpowered** cell whose bound is also
underpowered is "consistent with the bound" — the bound *predicts* the
empirical underpower verdict. A 4-arm **underpowered** cell whose bound is
powered is "inconsistent" — the bound cannot explain the underpower.

For this audit:

```
consistent = (|d_z_observed| < d_z_floor) AND (verdict_per_seed = UNDERPOWERED)
```

The "AND" rule captures the specific mathematical claim: the bound
*predicts* underpower AND the per-seed test confirms underpower. The
2 SUPPORTED vanilla cells therefore count as "inconsistent" because
their per-seed verdict is SUPPORTED — even though they sit below the
worst-case d-dim bound (see §"Why the 2 SUPPORTED cells count as
inconsistent" below).

### Inputs

| Input | Value | Source |
|---|---|---|
| $A_g$ | 0.8549457422 | `verification_outputs/wave226-p1-a-g-values.csv` (identical across all 12 adapters) |
| $e^{A_g}$ | 2.3512468036 | derived |
| $d$ | 512 | `docs/audit/wave226-p2-methods-paragraph.md` (`d = n_channels_decoder`, representative protein-FM dimension) |
| $\sigma_{\text{record}}$ (pLDDT) | 15.177 | `verification_outputs/wave202-p5-lineageflow-per-record.csv` row `plddt_mean` (sd_diff at n_paired=574 records) |
| $\sigma_{\text{record}}$ (scPerplexity) | 3.661 | same file, row `sc_perplexity` |
| per-seed $d_z$, $n_{\text{seed}}$ | per cell | `verification_outputs/wave196-p2-4arm-paired.csv` (16 cells) |

The choice of $\sigma_{\text{record}}$ from the LineageFlow n=574 per-record
analysis (Wave 202 P5) matches the Wave 226 P3 audit convention; the k6
per-record source (`wave198-p2-per-record-paired.csv`, sd_diff=15.8801
pLDDT / 3.6377 scPerplexity) is consistent to within ~5% and does not
flip any verdict.

### Why $d = 512$

Wave 226 P2 establishes the convention $d = n_{\text{channels\_decoder}}
= 512$ as the representative protein-FM data dimension. The variance
bound $E\|\Phi_1(x_0) - \Phi_1(x'_0)\|^2 \leq e^{2A_g}\cdot 2d \approx 5659$
is the headline number cited in the §MS.10.2 insert, and we keep the
same convention here so the two artifacts cross-reference cleanly.
LineageFlow's `hidden_size=1280` would give a larger noise floor
(×1.58), but the qualitative verdict is the same: all 16 cells are
bound-underpowered under either convention.

---

## Results — full 16-cell table

| cell | metric | n_seed | d_z_obs | \|d_z\| | σ_record | noise_floor | d_z_floor | 4-arm verdict | below_floor | consistent |
|---|---|---:|---:|---:|---:|---:|---:|---|---|---|
| vanilla_pLDDT_NFE50 | pLDDT | 30 | +0.0563 | 0.0563 | 15.177 | 13.7369 | 0.9051 | UNDERPOWERED | TRUE | **YES** |
| vanilla_pLDDT_NFE100 | pLDDT | 30 | +0.0528 | 0.0528 | 15.177 | 13.7369 | 0.9051 | UNDERPOWERED | TRUE | **YES** |
| vanilla_scPerplexity_NFE50 | scPerplexity | 30 | -2.9316 | 2.9316 | 3.661 | 13.7369 | 3.7522 | SUPPORTED | TRUE | NO |
| vanilla_scPerplexity_NFE100 | scPerplexity | 30 | -2.9945 | 2.9945 | 3.661 | 13.7369 | 3.7522 | SUPPORTED | TRUE | NO |
| fastdllm_pLDDT_NFE50 | pLDDT | 30 | -0.1885 | 0.1885 | 15.177 | 13.7369 | 0.9051 | UNDERPOWERED | TRUE | **YES** |
| fastdllm_pLDDT_NFE100 | pLDDT | 30 | -0.2264 | 0.2264 | 15.177 | 13.7369 | 0.9051 | UNDERPOWERED | TRUE | **YES** |
| fastdllm_scPerplexity_NFE50 | scPerplexity | 30 | +0.0202 | 0.0202 | 3.661 | 13.7369 | 3.7522 | UNDERPOWERED | TRUE | **YES** |
| fastdllm_scPerplexity_NFE100 | scPerplexity | 30 | +0.0245 | 0.0245 | 3.661 | 13.7369 | 3.7522 | UNDERPOWERED | TRUE | **YES** |
| abcache_pLDDT_NFE50 | pLDDT | 30 | -0.0782 | 0.0782 | 15.177 | 13.7369 | 0.9051 | UNDERPOWERED | TRUE | **YES** |
| abcache_pLDDT_NFE100 | pLDDT | 30 | -0.1062 | 0.1062 | 15.177 | 13.7369 | 0.9051 | UNDERPOWERED | TRUE | **YES** |
| abcache_scPerplexity_NFE50 | scPerplexity | 30 | -0.1950 | 0.1950 | 3.661 | 13.7369 | 3.7522 | UNDERPOWERED | TRUE | **YES** |
| abcache_scPerplexity_NFE100 | scPerplexity | 30 | -0.0829 | 0.0829 | 3.661 | 13.7369 | 3.7522 | UNDERPOWERED | TRUE | **YES** |
| lediflow_pLDDT_NFE50 | pLDDT | 30 | -0.1915 | 0.1915 | 15.177 | 13.7369 | 0.9051 | UNDERPOWERED | TRUE | **YES** |
| lediflow_pLDDT_NFE100 | pLDDT | 29 | -0.1633 | 0.1633 | 15.177 | 13.9717 | 0.9206 | UNDERPOWERED | TRUE | **YES** |
| lediflow_scPerplexity_NFE50 | scPerplexity | 30 | +0.1915 | 0.1915 | 3.661 | 13.7369 | 3.7522 | UNDERPOWERED | TRUE | **YES** |
| lediflow_scPerplexity_NFE100 | scPerplexity | 29 | +0.1224 | 0.1224 | 3.661 | 13.9717 | 3.8164 | UNDERPOWERED | TRUE | **YES** |

CSV mirror: `verification_outputs/wave227-p2-floor-corrected.csv`

---

## Interpretation

### 14/16 UNDERPOWERED cells are consistent with the variance bound (corrected)

Every cell whose 4-arm per-seed paired-t verdict is UNDERPOWERED is *also*
bound-underpowered under the corrected formula. The bound predicts
underpower for the 4-arm cells in the observed $|d_z| \in [0.020, 0.226]$
range: the variance floor $e^{A_g}\sqrt{2d/n_{\text{seed}}}$ (= 13.74 in
raw metric units, or equivalently $d_z^{\text{floor}} \in [0.91, 3.82]$
after normalizing by $\sigma_{\text{record}}$) exceeds every observed
$|d_z|$ in the 4-arm. The bound therefore *mathematically predicts* the
empirical underpower pattern: with $n_{\text{seed}} = 30$ and the
per-record noise floor fixed by $A_g$ and $\sigma_{\text{record}}$, no d_z
in [0.02, 0.23] can clear the 80%-power threshold.

### Why the 2 SUPPORTED cells count as inconsistent

The vanilla scPerplexity NFE50 / NFE100 cells have $|d_z| = 2.93 / 2.99$,
both *below* the corrected floor $d_z^{\text{floor}} = 3.75$. The bound
predicts BOUND-UNDERPOWERED for both, but the 4-arm verdict is SUPPORTED
with $p < 10^{-15}$.

Under the strict definition
`consistent = (|d_z| < d_z_floor) AND (verdict_per_seed = UNDERPOWERED)`,
the "AND" fails because `verdict_per_seed = SUPPORTED`. These two cells
are therefore counted as **inconsistent** — even though their
`|d_z| < d_z_floor` is TRUE.

This is *not* a contradiction of the bound: the bound is a **worst-case**
upper bound on per-seed output variance in the full d-dim latent space,
whereas scPerplexity is a 1-D projection of the output. In the specific
1-D projection the seed-to-seed noise is far below the d-dim worst case.
The bound is therefore **conservative** for these cells — the bound says
"underpowered in the worst case", but in the realized projection the
effect is detectable. See `docs/audit/wave226-p3-variance-bound.md` §
"2 SUPPORTED cells: bound is conservative" for the original argument.

### Counterfactual: would the hypothetical incorrect floor (2.21 / 0.53) flip the verdict?

| metric | n | hypothetical floor (2.21 / 0.53) | max \|d_z\| (4-arm) | would below_floor flip? |
|---|---:|---:|---:|---|
| pLDDT | 30 | 0.53 | 0.226 | FALSE — all 8 cells still below floor |
| pLDDT | 29 | 0.53 | 0.163 | FALSE — all 8 cells still below floor |
| scPerplexity | 30 | 2.21 | 2.99 (vanilla NFE100) | TRUE — 2 vanilla cells now ABOVE floor |
| scPerplexity | 29 | 2.21 | 0.191 | FALSE |

Even under the hypothetical incorrect floor, the **consistent** count
remains 14: all 8 pLDDT cells are still below floor (and all
UNDERPOWERED → consistent), 6 of 8 scPerplexity cells are still below
floor (and all UNDERPOWERED → consistent), and the 2 vanilla scPerplexity
cells flip to above-floor but remain inconsistent because their per-seed
verdict is SUPPORTED. So the corrected math gives **14 consistent** and
the hypothetical incorrect math also gives **14 consistent** — the
verdict set is robust to the transcription-error hypothesis.

(The incorrect floor would change the `verdict_pair` classification:
the 2 vanilla cells would be `SUPPORTED+POWERED` (both agree effect is
detectable) instead of `SUPPORTED+UNDERPOWERED`. The qualitative
narrative shifts from "bound is conservative" to "bound is
calibrated-to-projection" but the count of consistent cells is
unchanged.)

---

## Cross-references

- `verification_outputs/wave196-p2-4arm-paired.csv` — 4-arm per-seed
  Table B (16 cells, 4 baselines × 2 NFE × 2 metrics, paired t-tests
  with df=29 or df=28).
- `verification_outputs/wave226-p1-a-g-values.csv` — A_g table for 12
  adapters (all identical at the default profile).
- `verification_outputs/wave202-p5-lineageflow-per-record.csv` —
  LineageFlow per-record paired-t on 574 records, the source for
  $\sigma_{\text{record}}$.
- `verification_outputs/wave226-p3-per-seed-variance-bound.csv` —
  Wave 226 P3 output (correct math, bit-identical to this audit).
- `verification_outputs/wave227-p2-floor-corrected.csv` — this audit's
  recomputation, bit-identical to Wave 226 P3.
- `docs/audit/wave226-p1-a-g-values.md` — A_g audit doc, supplies
  $A_g = 0.8549457422$.
- `docs/audit/wave226-p2-methods-paragraph.md` — Methods §MS.10
  audit doc, establishes the $d = 512$ convention.
- `docs/audit/wave226-p3-variance-bound.md` — original variance-bound
  audit (correct math, 14/16 consistent).
- `docs/audit/wave227-p1-a-g-diagnostic.md` — Wave 227 P1 audit on
  why A_g is canonical-witness, not per-adapter.

---

## Reproducibility

The computation is a pure formula evaluation against 4 inputs. No new
experiments, no source-code changes, no byte-stability risk. D.4 30/30
byte-stable gate unaffected (this audit is documentation + a CSV).

Script: `scripts/wave227_p2_floor_corrected.py`

```python
import math, csv

A_G = 0.8549457422
EXP_A_G = 2.3512468036
D = 512  # n_channels_decoder, protein-FM representative
SIGMA_RECORD = {"pLDDT": 15.177, "scPerplexity": 3.661}

for row in wave196_p2_4arm_paired_csv:
    n_seed = int(row["n_pairs"])
    d_z_obs = abs(float(row["cohens_d_z"]))
    sigma_record = SIGMA_RECORD[row["metric"]]
    noise_floor = EXP_A_G * math.sqrt(2 * D / n_seed)
    d_z_floor = noise_floor / sigma_record
    bound_verdict = "UNDERPOWERED" if d_z_obs < d_z_floor else "POWERED"
    consistent = (bound_verdict == "UNDERPOWERED") and (row["verdict"] == "UNDERPOWERED")
```

---

## Summary

- **n_cells_total = 16**, all 16 floors calculated.
- **n_cells_consistent_with_bound_corrected = 14** (the 14
  4-arm UNDERPOWERED cells are also BOUND-UNDERPOWERED).
- **n_cells_inconsistent = 2** (vanilla scPerplexity NFE50 / NFE100
  — SUPPORTED but bound-underpowered; bound is conservative in 1-D
  projection).
- **n_cells_consistent_in_wave_226_P3 (correct math, same as this
  audit) = 14**.
- **n_cells_consistent_under_hypothetical_incorrect_floor_2.21_0.53 = 14**
  (verdict set is robust to the transcription-error hypothesis).
- The variance bound mathematically *predicts* the empirical 14/16
  4-arm underpower pattern. Per-seed analysis at $n_{\text{seed}} = 30$
  is genuinely underpowered: the noise floor
  $e^{A_g}\sqrt{2d/n_{\text{seed}}} = 13.74$ (in metric units) exceeds
  every observed per-seed mean-difference in the 4-arm cells with
  $|d_z| < 0.23$.
- No code changes; D.4 byte-stable gate unaffected.
- Wave 226 P3's CSV and audit doc were already correct (3.7522 / 0.9051);
  this audit confirms the math from independent recomputation.
