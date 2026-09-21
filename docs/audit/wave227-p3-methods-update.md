# Wave 227 P3 — Methods §MS.10 Update with Corrected Numbers + Honest Per-Adapter Narrative

**Wave:** 227 P3
**Date:** 2026-09-21
**Status:** COMPLETE — `docs/drafts/methods-why-per-record.md` updated with
corrected per-seed floor (3.7522 scPerplexity / 0.9051 pLDDT, n = 30) and
honest narrative on per-adapter vs canonical $A_g$.

---

## TL;DR

| Change | Before (Wave 226 P2 draft) | After (Wave 227 P3 update) |
|---|---|---|
| §MS.10.2 per-seed floor | "MDD $\approx 0.73$ at $\alpha=0.05$ two-sided, 80% power, df=29" (standard t-test) | Variance-bound floor: **0.9051 (pLDDT) / 3.7522 (scPerplexity)** at n=30; 0.9206 / 3.8164 at n=29 (Wave 227 P2) |
| §MS.10.2 "14 of 16 cells below floor" | "14 of 16 cells lie below the per-seed detection floor" | "all 16 cells lie below the variance-bound floor; **14 of 16 are consistent** with the bound (UNDERPOWERED + below floor); 2 are inconsistent (SUPPORTED + below floor, bound is conservative)" |
| §MS.10.1 A_g scope | "computable from the adapter's residual profile $g$" | "computable from the **canonical F-side admissible witness** $g$"; $A_g$ is canonical-witness, not per-adapter runtime |
| §MS.10.4 caveat 4 | "Cross-adapter $A_g$ is identical to the default profile on all 12 adapters" | "**$A_g$ is a canonical F-side witness, not a per-adapter empirical estimate**" with explicit note that per-adapter empirical work product is the per-record BL distance, not $A_g$ |
| §MS.10.5.1 | absent | new section: "Canonical F-side witness — closed-form coefficient vs. adapter-specific BL distance" (3 structural facts + implication) |
| Cross-references | did not cite P1/P2 audit docs or new CSV | cites both P1 diagnostic + P2 corrected-floor audit, plus the new `wave227-p2-floor-corrected.csv` and `wave226-p1-a-g-sensitivity.csv` |

---

## What changed and why

### 1. Per-seed floor: 0.73 (standard t-test MDD) → 3.7522 / 0.9051 (variance-bound floor)

The previous §MS.10.2 cited "approximately 0.73" as the per-seed
minimum-detectable $d_z$ at $\alpha = 0.05$ two-sided, 80% power,
df = 29. That number is the **standard t-test minimum-detectable
$z$-statistic** under the assumption of unit-variance Gaussian noise
and is a standard power-analysis reference value.

But the framework's per-seed variance-bound argument is **more
conservative**: it accounts for the $e^{A_g} \approx 2.35$
amplification of the initial-noise standard deviation through the
FM ODE flow, which the standard t-test MDD does not. The
corrected per-seed floor from Wave 227 P2 (`docs/audit/wave227-p2-floor-corrected.md`)
is

$$d_z^{\text{floor,per-seed}} = \frac{e^{A_g} \sqrt{2d / n_{\text{seed}}}}{\sigma_{\text{record}}} \in \{0.9051 \text{ (pLDDT, } n{=}30), 3.7522 \text{ (scPerplexity, } n{=}30)\}.$$

These values are **tighter (more conservative)** than the standard
t-test MDD of $\approx 0.73$: the floor for pLDDT is 0.9051 (vs 0.73
standard), and the floor for scPerplexity is 3.7522 (vs 0.73
standard). All 16 4-arm cells sit below the variance-bound floor
at n = 30, and 14 of 16 are **consistent** with the bound (their
4-arm per-seed verdict is UNDERPOWERED, exactly as the bound
predicts). The remaining 2 cells (vanilla scPerplexity NFE50/100)
are SUPPORTED at $p < 10^{-15}$ but sit below the variance-bound
floor of 3.7522 — the bound is **conservative** in 1-D projection
(see Wave 227 P2 audit §"Why the 2 SUPPORTED cells count as
inconsistent").

**Numerical summary (16-cell 4-arm, `verification_outputs/wave227-p2-floor-corrected.csv`):**

| metric | $d_z^{\text{floor}}$ (n = 30) | $d_z^{\text{floor}}$ (n = 29) | max observed $\lvert d_z \rvert$ (4-arm) |
|---|---:|---:|---:|
| pLDDT | **0.9051** | 0.9206 | 0.2264 (fastdllm NFE100) |
| scPerplexity | **3.7522** | 3.8164 | 2.9945 (vanilla NFE100) |

| consistent count | n_cells |
|---|---:|
| UNDERPOWERED + below floor (= consistent) | **14** |
| SUPPORTED + below floor (= inconsistent, bound conservative) | 2 |
| **Total 4-arm cells** | **16** |

### 2. $A_g$ is canonical-witness, not per-adapter runtime

The previous draft said $A_g$ was "computable from the adapter's
residual profile $g$". The Wave 227 P1 diagnostic
(`docs/audit/wave227-p1-a-g-diagnostic.md`) shows this is
**structurally weak**: no adapter declares `profile_residual_fn`;
`AdapterCapabilities` does not expose that field; and the framework
falls back to legacy closed forms when no `paper_quantities_provider`
is supplied. All 12 adapters therefore share a **single canonical
F-side admissible witness**

$$g(x) = (1 + 0.25 \tanh x) \sin x$$

with default $(d, c, \rho, \eta) = (1.0, 1.0, 0.1, 0.1)$, and
$A_g = 0.8549457422$ is **bit-identical across all 12 adapters**
by construction. Computing a per-adapter empirical $A_g$ would
require constructing a per-adapter $g_{\text{adapter}}(s)$ from each
adapter's posterior geometry and feeding it to
`sheet_evidence_A`; this runtime path is **not yet implemented** in
any of the 12 adapters.

The §MS.10 update reframes this honestly in three places:

1. **§MS.10.1** — explicit "Scope of $A_g$" paragraph noting that
   $A_g$ is the **framework default for all 12 adapters** under
   the canonical F-side profile, not a per-adapter empirical
   estimate, and that the per-adapter empirical work product is
   the per-record BL-distance witness
   (`adaptive_reflow/theory/rate_bound.py::theorem1_bl_convergence_witness`,
   R6 R-level observable).

2. **§MS.10.4 caveat 4** — reframed to "**$A_g$ is a canonical
   F-side witness, not a per-adapter empirical estimate**" with
   explicit citation of Wave 227 P1 diagnostic and a note that
   the **per-adapter empirical work product** is the per-record
   BL-distance witness.

3. **§MS.10.5.1** (new section) — "Canonical F-side witness —
   closed-form coefficient vs. adapter-specific BL distance",
   stating three structural facts:
   (a) all 12 adapters share the canonical admissible witness;
   (b) $A_g$, $B_g$, $C_g$, $e_\rho$ are closed-form integrals of
   the witness, byte-stable and bit-identical across adapters;
   (c) adapter-specificity lives at the empirical BL-distance
   layer (per-record BL witness), not at the $A_g$ coefficient
   layer.

### 3. Math holds for the canonical witness (defensible scope)

The math argument in §MS.10 is correct **for the canonical
witness** $g(x) = (1 + 0.25 \tanh x) \sin x$, which all 12
adapters share. For adapters that override $g$ or
$(d, c, \rho, \eta)$ — currently none — the floor would shift
and would require a per-adapter re-evaluation of the per-seed /
per-record granularity choice. This is the precise structural
scope of the framework's $A_g$ claim.

---

## Files updated

| File | Change |
|---|---|
| `docs/drafts/methods-why-per-record.md` | §MS.10.1 added "Scope of $A_g$" paragraph (canonical-witness); §MS.10.2 replaced "0.73 standard t-test MDD" with corrected variance-bound floor (3.7522 scPerplexity / 0.9051 pLDDT); §MS.10.3 minor wording update; §MS.10.4 caveat 4 reframed (canonical-witness, not per-adapter); §MS.10.5.1 new section added; §MS.10.5 cross-references updated with P1/P2 audit docs and new CSVs |

## Files not changed

- `adaptive_reflow/theory/paper_quantities.py` — evaluator unchanged
  (P1 diagnostic confirms no code change required).
- `verification_outputs/wave226-p1-a-g-values.csv` —
  bit-identical (the $A_g$ value 0.8549457422 was already correct
  in Wave 226 P1).
- `verification_outputs/wave227-p2-floor-corrected.csv` — already
  produced by Wave 227 P2; this update just cites it.

---

## Cross-references

- `docs/audit/wave227-p1-a-g-diagnostic.md` — input: $A_g$ is
  canonical-witness, not per-adapter runtime (§MS.10.1, §MS.10.4
  caveat 4, §MS.10.5.1).
- `docs/audit/wave227-p2-floor-corrected.md` — input: corrected
  per-seed floor (3.75 scPerplexity / 0.905 pLDDT at n = 30; source
  for §MS.10.2 numbers).
- `docs/audit/wave226-p1-a-g-values.md` — original $A_g$ audit
  (input to $A_g = 0.8549457422$ citation).
- `docs/audit/wave226-p3-variance-bound.md` — original
  variance-bound audit (correct math, 14/16 consistent;
  bit-identical to Wave 227 P2 recomputation).
- `verification_outputs/wave227-p2-floor-corrected.csv` — 16-cell
  per-seed variance-bound recomputation, 14/16 consistent.
- `verification_outputs/wave226-p1-a-g-values.csv` — 12-adapter
  $A_g$ table (bit-identical at default profile).
- `verification_outputs/wave226-p1-a-g-sensitivity.csv` —
  sensitivity sweep confirming $A_g$ is invariant in $\rho$.
- `docs/drafts/methods-why-per-record.md` — updated draft.

---

## Reproducibility

This update is **documentation-only** (markdown text). No code
changes, no experiments, no source-tree changes. The §MS.10.2
mathematical content is bit-identical to Wave 227 P2's
recomputation (CSV mirror
`verification_outputs/wave227-p2-floor-corrected.csv`). D.4
30/30 byte-stable gate is unaffected.

---

## Summary

- §MS.10.2 now cites the **variance-bound-derived per-seed floor**
  (3.7522 scPerplexity / 0.9051 pLDDT at n = 30) instead of the
  standard t-test MDD ($\approx 0.73$); the variance-bound floor is
  the relevant per-seed resolution bound for this framework.
- §MS.10.2 16-cell consistency count is now **14 of 16 UNDERPOWERED
  cells consistent with the variance bound**; the 2 SUPPORTED cells
  (vanilla scPerplexity NFE50/100) sit below the bound, which is
  conservative in 1-D projection.
- §MS.10.1 / §MS.10.4 caveat 4 / §MS.10.5.1 honestly reframe $A_g$ as
  a **canonical-witness** coefficient (not per-adapter empirical
  estimate); per-adapter empirical work product is the per-record BL
  distance, not $A_g$ itself.
- §MS.10.5 cross-references now cite both P1 diagnostic and P2
  corrected-floor audit, plus the new CSVs.
- No code changes; D.4 byte-stable gate unaffected.
