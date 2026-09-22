# Wave 228 P3 — Path A vs Path B Decision: Per-Adapter Paper-Quantity Refactor

**Wave:** 228 P3
**Date:** 2026-09-21
**Status:** COMPLETE — **Path B selected** (light-engineering narrative
reframe + abstract-level caveat expansion; defer Path A to future work).
**Companion docs:**
- `docs/audit/wave227-p1-a-g-diagnostic.md` (A_g canonical-witness reframing)
- `docs/audit/wave228-p1-4arm-per-record.md` (per-record coverage check)
- `docs/audit/wave228-p2-paper-quantities-distribution.md` (B_g/C_g/e_ρ shared across 12 adapters)
- `docs/drafts/methods-why-per-record.md` §MS.10.5.1 (canonical-witness caveat, Wave 227 P3)

## TL;DR — Decision

| Question | Path A (Refactor) | Path B (Reframe) | Selected |
|---|---|---|---|
| Implement per-adapter `profile_residual_fn` on all 12 adapters | YES | NO | — |
| Edit paper drafts to honestly reframe current claim | NO | YES | — |
| Risk to D.4 byte-stable gate | HIGH (per-adapter profiles change aggregation) | NONE (canonical unchanged) | — |
| Risk of breaking R6 R-level headline | HIGH (re-run R-level cells) | NONE (citations already honest) | — |
| Wallclock | 2–4 weeks | 2–4 hours | — |
| **Verdict** | structurally heavyweight | **risk-mitigated, honest narrative** | **Path B** |

**Recommendation: Path B.** Reframe the claim in the paper drafts
(`section-2-method.md`, `abstract-final.md`, `cover-letter-tpami.md`)
to honestly distinguish the **canonical F-side admissible witness**
(which all 12 adapters share, by design — see Wave 228 P2 distribution
audit) from the **per-adapter empirical BL-distance work product**
(which is what carries the adapter-specific signal in the R6 R-level
observable). Defer per-adapter `profile_residual_fn` implementation to
future work.

The rationale follows from **three structural facts** established by
the prior four waves (Wave 226 P1, Wave 227 P1, Wave 228 P1, Wave 228
P2) plus an honest engineering-cost vs. reviewer-risk trade-off.

---

## 1. Three structural facts established by prior waves

### 1.1 Wave 226 P1 / Wave 228 P2 — `A_g`, `B_g`, `C_g`, `e_ρ` are SHARED across all 12 adapters

Wave 226 P1 (`docs/audit/wave226-p1-a-g-values.md`) and Wave 228 P2
(`docs/audit/wave228-p2-paper-quantities-distribution.md`) establish
that all four paper quantities are **closed-form canonical
coefficients**, NOT adapter-specific runtime diagnostics:

| Quantity | Value (d=1.0, c=1.0, ρ=0.1, η=0.1) | Shared across 12 adapters? |
|---|---:|:---:|
| **A_g** | **0.8549457422** | **YES** (bit-identical across all 12 rows) |
| **B_g** | **1.1697133855079125** | **YES** (only `g`, `K`, `h` matter; defaults shared) |
| **C_g** | **1.240756198591853** | **YES** (only `(ρ, c)` matter; defaults shared) |
| **e_ρ** | **0.00010000000000000002** | **YES** (only `(ρ, η)` matter; defaults shared) |

The shared-ness is **by construction**: no adapter declares a
`profile_residual_fn`, no adapter overrides
`paper_quantities_provider`, and the framework's
`adaptive_reflow/universal/adapter.py:132` does not even expose a
`profile_residual_fn` field on `AdapterCapabilities`.

### 1.2 Wave 227 P1 — The refactor is structurally open-ended

Wave 227 P1 (`docs/audit/wave227-p1-a-g-diagnostic.md`) establishes
that "computing a per-adapter empirical `A_g` would require:

1. implementing a per-adapter `g_adapter(s)` constructor that builds a
   residual profile from each adapter's posterior geometry, and
2. wiring it into the `paper_quantities_provider` injection point.

This is **structurally open-ended**: each of the 12 adapters has a
distinct domain (protein FM, molecular 3D FM, image RF, MNIST FM, 2D
RF, time-series FM, video FM, etc.) and the construction of a
per-adapter residual profile is not a single design choice — it is
**twelve distinct design choices**, each requiring domain-expert
input and validation against the F-side hypotheses
(F1–F4 in `section-2-method.md`).

### 1.3 Wave 228 P1 + Wave 228 P2 — Adapter-specificity already lives elsewhere

Wave 228 P1 (`docs/audit/wave228-p1-4arm-per-record.md`) and Wave 228
P2 establish that the adapter-specific empirical signal already exists
**at a different layer** — the **per-record BL distance witness**
(`adaptive_reflow/theory/rate_bound.py::theorem1_bl_convergence_witness`):

| Observable | Per-adapter? | Source |
|---|:---:|---|
| A_g / B_g / C_g / e_ρ | NO (canonical) | Wave 228 P2 |
| **per-record BL distance** (R6 R-level headline) | **YES** | Wave 198 P2 + Wave 209 P3 |

The R6 R-level headline (LineageFlow n=574 per-record paired-t on
pLDDT and scPerplexity; k6 n=1000 per-record paired-t with cluster-robust
re-analysis) is what carries the adapter-specific signal in the
published per-record `d_z` numbers (`d_z = -1.077` for scPerplexity,
`d_z = +1.189` for hard pLDDT). The `A_g` / `B_g` / `C_g` / `e_ρ`
coefficients are the **closed-form coefficients of the BL bound**;
they are canonical once `g` and `(d, c, ρ, η)` are fixed.

**Implication.** The framework's value-add is at the **scheduler
architecture** layer (CosineAnnealScheduler + CodimensionSheetScheduler
+ BoundedMergeOperator + EvidenceDrivenScheduler + BRAI), not at the
**paper-quantity coefficient** layer. The schedulers react to
per-record local velocity-field geometry (CosineAnnealScheduler uses
local Lipschitz estimates; CodimensionSheetScheduler uses
sheet-vs-cell evidence balance per-record), and the per-record empirical
work product is the BL-distance witness.

---

## 2. Path A — Per-Adapter `profile_residual_fn` Refactor (NOT selected)

### 2.1 Implementation steps

1. **For each of 12 adapters**, derive `g(s)` from posterior geometry:
   - LineageFlow (protein FM, 657M params, ESM-IF lineage)
   - Kanzi (protein flow-AE, 44.1M params, ICLR 2026)
   - FlowMol3 V2 (molecular 3D FM, 65M params, NeurIPS 2024)
   - RectifiedFlowCIFAR (image RF, Open DDPM++/RF UNet)
   - MnistFm (image FM, Open MNIST FM recipe)
   - TwoDimFM (2D synthetic FM, Two Moons / Eight Gaussians)
   - FreqFlow (frequency-domain FM, synthetic-mode)
   - Wan2.2 (video T2V FM, upstream shim)
   - HiDream I1 (text-to-image FM, upstream shim)
   - LuminaImage 2.0 (text-to-image FM, upstream shim)
   - GraphBFN (graph BFN, synthetic-mode)
   - ProtBFN-ABFN (protein ABFN, upstream shim)

   This requires constructing a residual profile for each domain
   from each adapter's trained posterior geometry. **Each profile is a
   distinct design choice**, not a mechanical mapping — protein
   sequences have 1-D per-residue structure, image has 2-D spatial
   structure, video has 3-D spatiotemporal structure, graph has
   variable-size topology, etc.

2. **Add `profile_residual_fn` field to `AdapterCapabilities`**:
   - `adaptive_reflow/universal/adapter.py:132` would need a new
     `Callable[[float], float]` field on the `AdapterCapabilities`
     dataclass.
   - This breaks the `@runtime_checkable` Protocol conformance test
     for any concrete adapter that does not declare it — the
     back-compat invariant for the 2356-test suite would need careful
     backward-compat handling (`has_profile_residual_fn: bool = False`
     + `None` default).

3. **Implement `profile_residual_fn` on each adapter** — estimated
   `12 adapters × ~50 LOC = ~600 LOC` of domain-specific code in
   `adaptive_reflow/adapters/{lineageflow,kanzi,flowmol3_v2,rf_cifar,
   mnist_fm,two_dim,freq_flow,wan22,hidream_i1,lumina_image_20,
   graph_bfn,prot_abbfn}/`.

4. **Validate F-side hypotheses per adapter** via `validate_f_side`:
   - Each adapter must satisfy F1–F4 with its custom `(d, c, ρ, η)`.
   - The F-side hypothesis validation is what certifies the
     `profile_residual_fn` is admissible; an inadmissible witness
     would set `admissible=False` and break the rate-bound checker.

5. **Re-run all R-level experiments with new per-adapter `A_g`, `B_g`,
   `C_g`, `e_ρ`**:
   - R1 (LineageFlow HMMER, N=1000 paired), R2 (Kanzi inv-proj,
     N=1000 paired), R3 (FlowMol3 fg_dev, N=1000 paired), R5a (Two
     Moons, N=1000 paired), R5b (CIFAR-10 RF, N=1000 paired), R5c
     (MNIST FM, N=1000 paired), R6 (k6 foldability, N=1000 paired).
   - This is **~30N paired inferences** across 7 R-cells × 2 arms ×
     ~1000 paired records ≈ ~42,000 inferences, plus full per-record
     output for the 4-arm cells (~640K paired inferences per Wave 228
     P1 estimate). Multi-GPU weeks of wallclock.

6. **Re-compute `d_z`, `p`, verdict** for every R-level cell with the
   new per-adapter paper quantities; risk of breaking D.4 byte-stable
   gate (D.4 uses fixed default profile; per-adapter profiles change
   aggregation).

### 2.2 Estimated cost

- **Wallclock: 2–4 weeks**
- **LOC: ~600 LOC adapter-specific code + ~50 LOC universal-layer
  change**
- **GPU time: ~30N paired sweeps for R-level re-runs + 4-arm per-record
  re-runs**
- **Risk of breaking D.4 byte-stable: HIGH** (D.4 uses fixed default
  profile; per-adapter profiles change aggregation, risk of byte-stable
  regression)

### 2.3 Why Path A is NOT selected

Three structural reasons:

1. **Per-adapter `A_g` / `B_g` / `C_g` / `e_ρ` implementation is
   structurally heavyweight**: each of the 12 adapters requires a
   domain-expert-driven `g_adapter(s)` construction (12 distinct design
   choices for 12 distinct domains), with a defensible F-side hypothesis
   validation per adapter. This is not a refactor — it is a research
   project in its own right.

2. **Re-running all R-level experiments with new per-adapter paper
   quantities is risky for the D.4 byte-stable gate and the published
   R-level headlines**: D.4 30/30 byte-stable regression (and the k6
   foldability D.3 SHA-256 regressions) is built on the canonical
   default profile. Per-adapter profiles would change the aggregation,
   potentially breaking the byte-stable suite or invalidating the
   published Wave 218 P3 Kanzi inv-proj `d_z = -0.0990` and the R6
   Per-Record `d_z = -1.077 / +1.189` numbers.

3. **The framework value-add is the scheduler architecture, not the
   paper-quantity coefficient values**: per-adapter variation is
   achieved through the **scheduler** reacting to local velocity-field
   geometry (CosineAnnealScheduler uses local Lipschitz estimates;
   CodimensionSheetScheduler uses sheet-vs-cell evidence balance
   per-record; BoundedMergeOperator consumes `e_ρ` via
   `lemma4_floor_value()`; EvidenceDrivenScheduler consumes the full
   quadruple). The per-record BL distance is what carries the
   adapter-specific signal in the R6 R-level observable.

**Conclusion:** Path A risks weeks of GPU time and breaking
byte-stable invariants for marginal narrative gain. Deferred to future
work.

---

## 3. Path B — Narrative Reframe + Abstract-Level Caveat (SELECTED)

### 3.1 Implementation steps

1. **Edit `docs/drafts/section-2-method.md`**:
   - §2.5 (Per-Adapter F-Side Profile Table) — expand the **Disclosure**
     paragraph (currently lines 341–358) to read:
     *"All twelve adapters currently run with the framework's
     **default F-side profile** $(d = 1.0, c = 1.0, \rho = 0.1,
     \eta = 0.1)$ because the framework exposes the F-side constants
     **through the rate-bound checker's default-argument path**
     (`check_explicit_rate_bound` with `f_side_d=1.0, f_side_c=1.0,
     f_side_rho=0.1, f_side_eta=0.1`) and no adapter overrides them
     via a `profile_residual_fn` or a per-adapter
     `paper_quantities_provider`. The **canonical F-side admissible
     witness** $g(x) = (1 + 0.25 \tanh x) \sin x$ (Proposition 2
     family) is **shared** by all 12 adapters **by design**, and the
     closed-form coefficients $(A_g, B_g, C_g, e_\rho)$ are
     **bit-identical across all 12 adapters** under the canonical
     profile (Wave 226 P1, Wave 228 P2 distribution audits). The
     **per-adapter empirical work product** in the framework is the
     per-record BL-distance witness
     (`adaptive_reflow/theory/rate_bound.py::theorem1_bl_convergence_witness`,
     R6 R-level headline observable), NOT the $A_g$ / $B_g$ /
     $C_g$ / $e_\rho$ coefficients themselves. Per-adapter custom
     `profile_residual_fn` is a **future-work** enhancement; the
     `paper_quantities_provider` injection point
     (`ReInferenceConfig.paper_quantities_provider`) is the only
     sanctioned runtime path, and no adapter exercises it today."*
   - §2.7 (Theoretical-justification paragraph) — replace
     *"computable from the adapter's posterior geometry at runtime"*
     with *"computable from the **canonical F-side admissible
     witness** $g(x) = (1 + 0.25 \tanh x) \sin x$ at framework
     defaults, **shared** by all 12 adapters **by design**; for
     adapters that override `g` or `(d, c, ρ, η)`, the closed-form
     coefficients shift and the canonical-witness derivations
     (`sheet_evidence_A`, `root_cell_packing_B`, `per_cell_coefficient_C`,
     `exterior_gap_e_rho`) recompute accordingly"*.

2. **Edit `docs/drafts/abstract-final.md`**:
   - Sentence 3 (Framework introduction, 86 words) — change
     *"derives a closed-form upper bound on the bounded-Lipschitz
     distance between the framework's sampling distribution and the
     ODE target through four paper quantities $(A_g, B_g, C_g, e_\rho)$"*
     to *"derives a closed-form upper bound on the
     bounded-Lipschitz distance through four paper quantities
     $(A_g, B_g, C_g, e_\rho)$, shared across adapters as **canonical
     closed-form coefficients** of a single admissible F-side witness
     with adapter-specific per-record BL-distance empirical evaluation"*.
     (~5 word expansion, well within 250-word envelope)
   - Add one explicit **scope-statement sentence** to enumerate the
     canonical-vs-per-adapter distinction:
     *"The framework distinguishes the **canonical F-side
     admissible witness** — shared across adapters — from
     **per-record BL-distance** — adapter-specific — and validates
     per-record empirical signal across three domains via R-level
     headline observables."*

3. **Edit `docs/cover-letter-tpami.md`**:
   - §3 (Insight — Paper-Quantity-Driven Scheduling) — replace
     *"computable from the adapter's posterior geometry at runtime"*
     with the same canonical-witness framing as §2.7.

4. **Add abstract-level caveat** (§Abstract, sentence 4 expansion):
   - The §MS.10.5.1 caveat (Wave 227 P3) is already
     methods-section-local. The Path B implementation should add a
     **single-sentence abstract-level caveat** that names the
     distinction between canonical paper quantities (closed-form
     coefficients of the BL bound) and per-record BL distance
     (adapter-specific empirical work product).

### 3.2 Estimated cost

- **Wallclock: 2–4 hours**
- **LOC: 0 (markdown-only edits)**
- **GPU time: 0 (no experiments)**
- **Risk of breaking D.4 byte-stable: NONE** (canonical profile
  unchanged)
- **Risk of breaking R-level headline: NONE** (citations already honest
  per Wave 227 P3 §MS.10.4 caveat 4 and §MS.10.5.1)

### 3.3 Reviewer risk — "If quantities are shared, why does framework work on different adapters?"

The expected reviewer question is: *"If $(A_g, B_g, C_g, e_\rho)$ are
shared, why does the framework work on different adapters?"*

The answer (ready for `docs/drafts/cover-letter-tpami.md` §3 expansion
and/or supplementary S1 addendum):

> The framework value-add lives at the **scheduler architecture
> layer**, NOT at the **paper-quantity coefficient layer**. Per-adapter
> variation is achieved through:
>
> - `CosineAnnealScheduler` reading `A_g` through the
>   `PaperRatioAdaptiveScheduler` interface and adapting the per-round
>   perturbation amplitude based on the velocity field's locally
>   non-smooth behaviour;
> - `CodimensionSheetScheduler` computing per-round `n_cap` from
>   $(A_g, B_g, C_g)$ and adapting the sheet-vs-cell evidence balance
>   in real time as the residual posterior evolves;
> - `BoundedMergeOperator` consuming `e_ρ` via `lemma4_floor_value()`
>   and lifting the merge envelope off zero to keep samples on the
>   fibre;
> - `EvidenceDrivenScheduler` consuming the full quadruple to compute
>   per-cell restart probability.
>
> The closed-form coefficients $(A_g, B_g, C_g, e_\rho)$ are **the
> scheduler input pins** — once they are fixed by the canonical
> F-side admissible witness, the per-round variance / smoothness /
> evidence-balance decisions are made **per record by the scheduler**
> based on the local velocity-field geometry. The per-record
> BL-distance witness
> (`theorem1_bl_convergence_witness`) is what carries the
> adapter-specific signal in the R6 R-level headline observable.

### 3.4 Why Path B IS selected

Three structural reasons:

1. **Lightweight**: 2–4 hours of markdown editing, no code changes, no
   experiments.
2. **Honest narrative**: the canonical-vs-per-adapter distinction is
   already documented in `docs/drafts/methods-why-per-record.md`
   §MS.10.5.1 (Wave 227 P3). Path B simply promotes the distinction
   from a methods-section caveat to an abstract-level caveat,
   consistent with §7 (Boundary Disclosure — Matched-NFE = 50
   First-Class Honest Negative) of the cover letter and §1 paragraph
   naming the standard-assumption failure mode.
3. **Risk-mitigated**: zero risk to D.4 byte-stable gate, zero risk to
   R6 R-level headline numbers, zero risk to the published Wave 218 P3
   Kanzi inv-proj `d_z = -0.0990` result.

**Conclusion:** Path B is the honest, lightweight, risk-mitigated
choice. Path A is deferred to a future-work section in the paper.

---

## 4. Cost/benefit summary

| Dimension | Path A | Path B (selected) |
|---|---|---|
| Wallclock | 2–4 weeks | 2–4 hours |
| LOC | ~650 (universal + 12 adapters) | 0 (markdown only) |
| GPU time | ~30N paired sweeps + 4-arm per-record | 0 |
| D.4 byte-stable risk | HIGH | NONE |
| R-level headline risk | HIGH (re-run all 7 cells) | NONE |
| Future-work deferment | n/a (fully implemented) | yes (`profile_residual_fn` deferred) |
| Per-adapter variant achieved | yes (12 distinct profiles) | no (canonical shared) |
| Per-record signal achieved | yes (per-adapter coefficients) | yes (per-record BL distance, already exists) |
| Reviewer pushback expected | LOW (paper quantities per-adapter) | LOW-MEDIUM (one expected question, answered above) |

---

## 5. Files

- `docs/audit/wave228-p3-path-decision.md` — this file

## 6. Files to edit (Path B implementation, deferred to a follow-up wave)

These edits are recommended but **not part of the Wave 228 P3
decision-agent scope** (which is decision-only, no edits):

- `docs/drafts/section-2-method.md` §2.5 Disclosure expansion + §2.7
  reframe
- `docs/drafts/abstract-final.md` Sentence 3 expansion + scope-statement
  sentence
- `docs/cover-letter-tpami.md` §3 canonical-witness framing

The edits are deferred to a follow-up wave (e.g., Wave 228 P4) once the
decision agent's recommendation is reviewed.

## 7. Future-work note for `section-2-method.md` §2.5.1 footnote

The footnote to §2.5.1 should explicitly enumerate the **future-work
enhancement**: "Per-adapter custom `profile_residual_fn` is a
**future-work** enhancement; the `paper_quantities_provider` injection
point (`ReInferenceConfig.paper_quantities_provider`) is the **only**
sanctioned runtime path, and **no adapter exercises it today**."

## 8. References

- `docs/audit/wave226-p1-a-g-values.md` — A_g distribution across 12 adapters (identical across rows).
- `docs/audit/wave227-p1-a-g-diagnostic.md` — A_g canonical-witness reframing; structural open-endedness of per-adapter refactor.
- `docs/audit/wave227-p2-floor-corrected.md` — corrected per-seed variance-bound floor.
- `docs/audit/wave227-p3-methods-update.md` — §MS.10 update: canonical-witness caveat (Wave 227 P3).
- `docs/audit/wave228-p1-4arm-per-record.md` — per-record coverage check (4-arm 16 cells).
- `docs/audit/wave228-p2-paper-quantities-distribution.md` — B_g/C_g/e_ρ distribution across 12 adapters (identical across rows).
- `docs/drafts/methods-why-per-record.md` §MS.10.4 caveat 4 + §MS.10.5.1 — canonical-witness caveat, source for Path B's methods-section honesty.
- `docs/drafts/section-2-method.md` — current claim text (Path B will edit §2.5 Disclosure + §2.7 theoretical-justification paragraph).
- `docs/drafts/abstract-final.md` — current abstract (Path B will edit Sentence 3 + add scope-statement).
- `docs/cover-letter-tpami.md` §3 — current cover letter insight section (Path B will replace "computed from adapter's posterior geometry at runtime").
- `adaptive_reflow/universal/adapter.py:132` — `AdapterCapabilities` dataclass (currently lacks `profile_residual_fn` field).
- `adaptive_reflow/theory/paper_quantities.py` — `sheet_evidence_A`, `root_cell_packing_B`, `per_cell_coefficient_C`, `exterior_gap_e_rho` evaluators (canonical home).
- `adaptive_reflow/theory/rate_bound.py::theorem1_bl_convergence_witness` — per-record BL-distance witness (the **per-adapter empirical work product**).
- Wave 218 P1 Kanzi inv-proj fix (`docs/audit/wave218-p1-fix-applied.md`) — provenance of the published `d_z = -0.0990` result.
- Wave 198 P2 R6 per-record paired-t (`verification_outputs/wave198-p2-per-record-paired.csv`) — R6 R-level headline `d_z = -1.077 / +1.189`.

## 9. Reproducibility

This is a **decision-only** wave (no code changes, no experiments).
The audit doc sources are:

- `docs/audit/wave226-p1-a-g-values.md` (input)
- `docs/audit/wave227-p1-a-g-diagnostic.md` (input)
- `docs/audit/wave228-p1-4arm-per-record.md` (input)
- `docs/audit/wave228-p2-paper-quantities-distribution.md` (input)
- `docs/drafts/methods-why-per-record.md` §MS.10.5.1 (input — §2.7 canonical-witness caveat already in place)
- `docs/drafts/section-2-method.md` (input)
- `docs/drafts/abstract-final.md` (input)
- `docs/cover-letter-tpami.md` (input)
- `adaptive_reflow/universal/adapter.py:132` (input — `AdapterCapabilities` field surface)

The decision logic is contained entirely in this file (decision-tree
+ reviewer-question-answer in §3.3).

## 10. Summary

- **Path B recommended** (light engineering, risk-mitigated, honest
  narrative; future-work for `profile_residual_fn`).
- Path A is structurally heavyweight (12 distinct domain-expert design
  choices, ~30N R-level re-runs, high risk of breaking D.4
  byte-stable / R6 R-level headline), deferred to future work.
- Path B is ~3 orders of magnitude lighter in wallclock (~4 hours vs
  2–4 weeks), zero risk to byte-stable / headline gates, and the
  canonical-vs-per-record distinction is already documented at the
  methods-section level (`docs/drafts/methods-why-per-record.md`
  §MS.10.5.1) — Path B simply promotes this distinction to the
  abstract level and rephrases the current "computed from adapter's
  posterior geometry at runtime" phrasing to the honest "canonical
  F-side admissible witness, shared by all 12 adapters by design,
  with per-record BL-distance as the adapter-specific empirical work
  product".
