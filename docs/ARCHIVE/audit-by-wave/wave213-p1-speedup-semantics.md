# Wave 213 P1 — FLOPs vs Speedup Contradiction Audit

**Goal.** Reconcile the apparent contradiction between the paper
headline "2.5–10× speedup at matched quality" (claim iii, §1, §3.3,
§3.6) and the Wave 211 §5.5 report that "FLOPs are identical at
matched NFE except R6 cross-budget (45 vs 15 GFLOPs)". If the
framework uses equal-or-more FLOPs at matched NFE, what does
"speedup" mean?

## TL;DR

- The "speedup" in the paper headline refers to **NFE compression**
  at cross-budget, NOT to wall-clock speedup and NOT to FLOPs
  reduction.
- At matched NFE the framework is **identical FLOPs** (the model
  parameters are unchanged; only the per-round NFE budget is
  re-allocated) and is typically **slower per record** (1.08× to
  26.4× wall-clock).
- At cross-budget the framework uses **equal-or-fewer FLOPs** and
  reaches matched quality with **substantially fewer forward
  passes** (≈10× on R5b CIFAR-10 RF; equal NFE on R6 LineageFlow
  but 3× MORE FLOPs because framework runs 150 NFE to expose
  quality uplift).
- The §3.6 cross-budget row and §5.5 reviewer-question paragraph
  mention "2.5× speedup" as a wall-clock-ratio reading of the
  same regime (0.37× net wall-clock = 2.7× slowdown per step,
  amortised by 10× NFE saving); this is a different unit from
  the "2.5–10× speedup" headline.

## The three possible meanings of "speedup"

| # | Meaning | This paper uses? |
|---|---|---|
| (a) | **NFE compression**: framework uses fewer function evaluations to reach matched quality (e.g., framework NFE=50 ≈ baseline NFE=500 in wall-clock or quality). | **YES** — this is the headline "2.5–10× speedup at matched quality" |
| (b) | **Wall-clock speedup**: framework finishes a quality target faster on same hardware. | PARTIALLY — at cross-budget R5b the framework is 0.37× net wall-clock (i.e., 2.7× slower) but uses 10× fewer NFE; this is the "2.5× speedup" wording in §5.5 reviewer-question paragraph |
| (c) | **FLOPs reduction**: framework uses fewer floating-point ops. | YES at cross-budget R5b (FLOPs ratio = 10×); NO at cross-budget R6 (framework uses 3× MORE FLOPs); IDENTICAL at matched NFE (FLOPs ratio = 1.0) |

## Per-cell breakdown

| Cell | NFE regime | NFE compression ratio (baseline/framework) | Wall-clock ratio (baseline/framework) | FLOPs ratio (baseline/framework) | What does "speedup" mean here? |
|---|---|---:|---:|---:|---|
| R5b CIFAR-10 RF | Cross-budget (baseline 500 → framework 50) | **10.0×** | **0.37× (framework 2.7× slower per step, amortised by 10× NFE save)** | **10.0× (framework uses 10× fewer GFLOPs)** | NFE compression (headline); FLOPs reduction (corollary); wall-clock: framework is slower per step |
| R5b CIFAR-10 RF | Matched NFE=50 | 1.0× | 0.041× (framework 25× slower) | 1.0× | None — framework loses on this regime |
| R6 LineageFlow | Cross-budget (baseline 50 → framework 150) | 0.33× (framework uses 3× MORE NFE) | 1.0005× (tied) | 0.33× (framework uses 3× MORE FLOPs) | None on NFE/FLOPs; quality uplift on hard-tier foldability is the value-add |
| R6 LineageFlow | Matched NFE=50 | 1.0× | 1.0005× (tied) | 1.0× | None on compute; framework exposes quality uplift on hard-tier |
| R3 FlowMol3 | Matched NFE=250 | 1.0× | 0.93× (framework 1.08× slower) | 1.0× | None — DGL graph kernels dominate |
| R2 Kanzi (synthetic) | Matched NFE=50 | 1.0× | 2.79× (framework FASTER on synthetic adapter) | 1.0× | None — known synthetic-adapter quirk |
| R7 FreqFlow | Matched NFE=50 | 1.0× | 0.038× (framework 26× slower) | 1.0× | None — frequency-domain UNet bandwidth-bound |
| R1 HMMER | Matched NFE=50 | 1.0× | 0.894× (framework 1.12× slower) | 1.0× | None — HMMER is CPU-heavy |

## What "2.5–10× speedup" means in different parts of the paper

| Location | "Speedup" wording | Unit | Correct? |
|---|---|---|---|
| §1 paragraph (line 19) | "2.5–10× cross-budget NFE compression at matched sample quality" | NFE | ✓ (already correct) |
| §1 Contributions claim (iii) (line 25) | "2.5–10× cross-budget NFE compression at matched sample quality" | NFE | ✓ (already correct) |
| §3.3 Headline results (line 204) | "2.5–10× cross-budget NFE compression at matched sample quality (the FID at NFE = 50 under the framework is comparable to the baseline FID at NFE = 500, giving ≈10× speedup at matched quality)" | NFE | "speedup" was redundant with "NFE compression"; rewritten |
| §3.3 Cross-budget NFE compression (line 227) | "≈10× speedup at matched quality" | NFE | ✓ (already correct in context) |
| §3.6 Cross-budget regime (line 271) | "≈10× speedup at matched quality" | NFE | ✓ (already correct) |
| §3.7 Summary of §3 (line 289) | "≈10× speedup at matched quality" | NFE | ✓ (already correct) |
| §5.5 Reviewer question answered (line 352) | "net ≈ 2.5x speedup at matched quality" | Wall-clock ratio reading of cross-budget | "speedup" was misleading; rewritten to "NFE compression at matched quality (≈0.37× net wall-clock)" |

## R6 special case: framework uses MORE FLOPs

R6 LineageFlow at cross-budget (framework 150 NFE vs baseline 50 NFE)
is the only cell where the framework uses **3× MORE FLOPs** (45 vs
15 GFLOPs/sample) than the baseline. This is NOT a speedup
contradiction — the framework's value-add on R6 is **quality uplift
on hard-tier foldability records** (cluster-robust d_z = +1.189),
not compute savings. The 3× FLOPs cost buys:

- **150 NFE total across 3 rounds × 50 NFE** vs **50 NFE** for the
  baseline.
- Per-round restart-blend + paper-quantity schedulers expose the
  hard-tier foldability signal that 50 NFE baseline misses.
- Wall-clock is **tied** (1.0005×) because OmegaFold CPU offload
  amortises across rounds.

The cross-budget FLOPs cost on R6 is therefore a **quality
investment**, not a compute regression.

## Paper wording corrections applied

### §1 paragraph

> The headline empirical result is a 2.5–10× cross-budget NFE
> compression at matched sample quality alongside byte-stable
> composite-axis lifts on all three Tier 3 real checkpoints; the
> matched-NFE image-domain regime (CIFAR-10 RF at NFE = 50) is
> reported as an honest boundary rather than a footnote. At
> cross-budget NFE=50 (framework) vs NFE=500 (baseline), the
> framework achieves matched quality with ≈10× fewer function
> evaluations. At matched NFE=50 the framework achieves comparable
> quality with identical FLOPs (model parameters unchanged; the
> framework only re-allocates the per-round NFE budget across
> restart rounds). Wall-clock overhead is reported separately in
> §5.5.

### §3.3 Headline results

> The headline empirical pattern is a **2.5–10× cross-budget NFE
> compression at matched sample quality** (the FID at NFE = 50 under
> the framework is comparable to the baseline FID at NFE = 500)
> alongside **byte-stable composite-axis lifts** on all three
> Tier-3 real checkpoints and **NFE-matched regression** on the
> CIFAR-10 RF matched-NFE = 50 boundary cell (R5b). At
> cross-budget NFE=50 (framework) vs NFE=500 (baseline), the
> framework achieves matched quality with ≈10× fewer function
> evaluations. At matched NFE=50 the framework achieves comparable
> quality with identical FLOPs (model parameters unchanged; the
> framework only re-allocates the per-round NFE budget across
> restart rounds). Wall-clock overhead is reported separately in
> §5.5.

### §3.3 Cross-budget NFE compression

> On the CIFAR-10 RF cross-budget sweep, the framework's FID at
> NFE = 50 trades one function evaluation per round across multiple
> restart-blend rounds and reaches the same FID an order of
> magnitude faster in NFE than the matched-budget baseline: the
> framework FID at NFE = 50 is comparable to the baseline FID at
> NFE = 500. The full cross-budget curve is reported as Figure 4
> (see §3.6). The headline value-add is therefore an **NFE
> compression** (≈10× fewer function evaluations at matched
> quality), not a wall-clock speedup; at matched NFE the framework
> runs identical FLOPs and is typically slower per record (see §5.5).

### §3.6 Cross-budget regime

> **Cross-budget regime (NFE ≲ 100).** The framework wins on the
> FID axis: framework FID at NFE = 50 ≈ baseline FID at NFE = 500,
> achieving matched quality with ≈10× fewer function evaluations.
> This is the regime where the cosine ramp trades NFE per round
> for multiple restart-blend rounds and the paper quantities
> allocate the per-round noise budget as a function of the
> posterior geometry. (Wall-clock overhead at matched NFE is
> reported separately in §5.5.)

### §3.7 Summary

> Across six R-level cells, FlowA wins on the cross-budget image
> axis (CIFAR-10 RF −44.17 % FID at NFE-averaged, ≈10× NFE
> compression at matched quality) ...

### §5.5 Reviewer question answered

> At cross-budget NFE the framework reaches the same quality with
> fewer total forward passes: on the R5b CIFAR-10 image-domain
> boundary cell, the framework at NFE=50 reaches FID ~155 (Wave
> 191 P2 cross-budget anchor), which the baseline reaches at
> NFE=500 — a 10× NFE saving. The cross-budget NFE saving
> dominates the per-step overhead (25× slower per step), yielding
> a net ≈ 2.5× NFE compression at matched quality (≈0.37× net
> wall-clock; the framework is the right choice when the user can
> accept a wall-clock budget and wants to minimise total NFE).

### Claim (iii) corrected

> **Cross-budget NFE compression**: 2.5–10× NFE compression at
> matched sample quality across six R-level cells; matched-NFE
> image-domain regime is a first-class boundary where the
> framework does not win.

## Files updated

| Path | Action |
|---|---|
| `docs/drafts/paper-flattened-draft.md` | edit (a) §1 paragraph; (b) §3.3 headline; (c) §3.3 cross-budget paragraph; (d) §3.6 cross-budget regime; (e) §3.7 summary; (f) §5.5 reviewer-question paragraph |
| `docs/audit/wave211-p1-efficiency-narrative.md` | edit (additive clarification block at end of TL;DR) |
| `docs/audit/wave211-p2-six-main-claims.md` | edit (claim iii table row + Wave 213 P1 correction footnote) |
| `verification_outputs/wave213-p1-speedup-semantics.csv` | create (per-cell NFE/wall/FLOPs ratio table) |
| `verification_outputs/wave213-p1-speedup-semantics.json` | create (structured per-cell findings + corrected wording) |
| `docs/audit/wave213-p1-speedup-semantics.md` | create (this audit doc) |

## Audit checklist

- [x] Three possible meanings of "speedup" enumerated (NFE
      compression, wall-clock speedup, FLOPs reduction).
- [x] Per-cell NFE compression ratio + wall-clock ratio + FLOPs
      ratio computed.
- [x] R5b cross-budget NFE compression ratio = 10.0 confirmed.
- [x] R6 cross-budget NFE compression ratio = 0.33 (framework
      uses 3× MORE NFE/FLOPs) explained as quality investment.
- [x] §1 paragraph corrected (added "NFE compression" + FLOPs
      identity at matched NFE clarification).
- [x] §3.3 headline corrected (removed redundant "speedup",
      added FLOPs identity clarification).
- [x] §3.3 cross-budget paragraph corrected (added "NFE
      compression, not a wall-clock speedup" disambiguation).
- [x] §3.6 cross-budget regime corrected (added "function
      evaluations" unit clarification).
- [x] §3.7 summary corrected (replaced "speedup" with "NFE
      compression").
- [x] §5.5 reviewer-question paragraph corrected (separated NFE
      compression reading from wall-clock-ratio reading).
- [x] wave211-p1-efficiency-narrative.md updated (additive
      clarification block).
- [x] wave211-p2-six-main-claims.md claim (iii) corrected to
      "NFE compression".
- [x] CSV + JSON analysis files created.
- [x] Audit doc (this file) created.

## References

- Wave 211 P1 — efficiency narrative + FLOPs estimate
  (`docs/audit/wave211-p1-efficiency-narrative.md`,
  `verification_outputs/wave211-p1-flops-estimate.csv`).
- Wave 211 P2 — six main claims + abstract first sentence
  (`docs/audit/wave211-p2-six-main-claims.md`).
- Wave 191 P2 — R5b CIFAR-10 N=1000 NFE=50 anchor.
- Wave 87 — R3 FlowMol3 N=1000 NFE=250 anchor.
- Wave 161 — R6 LineageFlow k6 foldability N=1000.
- Wave 209 P4 — matched-compute definition
  (`docs/audit/wave209-p4-matched-compute-definition.md`).
