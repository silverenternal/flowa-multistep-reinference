# Wave 209 P7 — Six Main Claims (DeepSeek F1-F2 Reduction)

**Scope.** Reduce the prior 64-claim ACTIVE set to six main claims
following the DeepSeek F1-F2 spec. Each claim is grounded in a
concrete evidence stream, uses an approved verb from the
"propose / introduce / establish / validate / provide / characterize"
set, and is reported as a single sentence in §1 Contributions of
`docs/drafts/paper-flat-flattened.md`.

**Status.** Complete; six claims finalised below and already written
into `docs/drafts/paper-flat-flattened.md` §1 Contributions.

---

## 1. The six main claims

| # | Claim | Evidence | Verb |
|---|---|---|---|
| (i) | **FlowA framework.** We propose FlowA, a training-free re-inference framework that schedules multi-round ODE solver boundary conditions via a closed-form concentration bound through four paper quantities $(A_g, B_g, C_g, e_\rho)$ — replacing the uniform-boundary assumption of standard ODE solvers with per-record posterior-geometry-driven scheduling. | Theorem 1 (four-lemma derivation), the four closed-form quantities in §1; byte-stable `adaptive_reflow/theory/paper_quantities.py` evaluators | "propose" |
| (ii) | **CodimensionSheetScheduler.** We introduce the CodimensionSheetScheduler, a per-record adaptive controller that consumes the four paper quantities $(A_g, B_g, C_g, e_\rho)$ directly as scheduler inputs to close the gap between heuristic alpha-blending and convergence-theory-driven re-inference. | §3.4 Table 3.3 A2 row; Corollary 1 closed form `n_cap = n_min + (n_max − n_min) · A_g · ε / (A_g · ε + C_g · B_g · ε²)` | "introduce" |
| (iii) | **Cross-budget NFE compression.** We establish cross-budget NFE compression of 2.5–10× at matched sample quality (framework NFE = 50 ≈ baseline NFE = 500 across the R5 cells), alongside the matched-NFE image-domain regime as a first-class boundary where the framework does not win. | §3.6 cross-budget curve; §3.6 efficiency narrative Table 5.5.1; §3.6 boundary cell R5b | "establish" |
| (iv) | **Cluster-robust per-record validation.** We validate the framework by cluster-robust per-record testing on the protein foldability cell, demonstrating scPerplexity framework-WINS uniformly across all tiers (R6 overall d_z = −1.077, p = 2.74 × 10⁻¹⁶⁹, cluster-robust p = 4.02 × 10⁻³) and hard-tier pLDDT framework-WINS selectively (R6 hard d_z = +1.189, monotone `hard > medium > easy` replicated on a second adapter). | §3.3 Tables 3.2 R6 rows; §3.4 cross-adapter replication | "validate" |
| (v) | **Five-arm cumulative-add ablation.** We provide a five-arm cumulative-add ablation (A0–A4) on the 2D RF + CIFAR-10 RF + LineageFlow axes that isolates the cosine annealing ramp from the paper-quantity-driven schedulers (CodimensionSheetScheduler, BoundedMergeOperator, EvidenceDrivenScheduler), attributing the protein hard-tier uplift to the paper-quantity schedulers (+18.54 pLDDT above cosine-ramp baseline) and the 2D-quality reduction to the cosine ramp. | §3.4 Table 3.3 | "provide" |
| (vi) | **Eight-dimension boundary characterization.** We characterize the method boundary along eight dimensions (K1–K8), phrased as structural scope statements that delineate where FlowA applies and where it does not, including flow-matching-only applicability, NFE-regime applicability, and protein-family cluster dependence. | §4 Limitations (K1–K8) | "characterize" |

---

## 2. Reduction rationale (from 64 ACTIVE → 6 main)

The prior ACTIVE claim set (Wave 207 P6 + Wave 208 P7) contained
approximately 64 paper-internal claims spanning solver-level,
trajectory-level, re-inference alpha-blending, Theorem 1 layer,
scheduler-port coupling, byte-stable determinism, cluster-robust
analysis, cross-adapter replication, five-arm ablation, NFE-matched
boundary, FLOPs / wall-clock efficiency, and per-tier framing. The
six-claim reduction collapses these into six reviewer-legible
headline claims by grouping sub-claims under one headline per
contribution category:

- **Theoretical contribution (claim i):** the framework as a whole
  (Theorem 1 + the four quantities + the three scheduler/operator
  components) is one contribution. The sub-claims about
  Bolley–Guilin–Villani concentration, the four-lemma derivation,
  and the byte-stable evaluators are subsumed under the headline
  theorem-driven interface.
- **Algorithmic contribution (claim ii):** the
  CodimensionSheetScheduler is the representative per-record
  controller; the BoundedMergeOperator and EvidenceDrivenScheduler
  are reported jointly as the "paper-quantity schedulers" (they are
  unpacked in §3.4 Table 3.3 and §3.5 but not as separate
  contributions).
- **Empirical efficiency contribution (claim iii):** the 2.5–10×
  NFE compression figure is the headline empirical result. The
  matched-NFE boundary is paired with this claim because the same
  cell (R5b) is the boundary characterization.
- **Empirical validation contribution (claim iv):** the
  cluster-robust per-record validation collapses the prior
  "validate on six R-level cells" procedure claim into a result
  claim ("scPerplexity universal + hard-tier pLDDT selective"). The
  cross-adapter replication on LineageFlow is part of the headline
  finding.
- **Ablation contribution (claim v):** the five-arm ablation is
  unchanged as a contribution; the cosine-ramp-vs-paper-quantity
  attribution is the empirical content.
- **Boundary contribution (claim vi):** the eight-dimension
  boundary characterization is the honest-negative surface of the
  paper, phrased as scope statements rather than as enumerated
  shortcomings.

The remaining 58 ACTIVE claims are preserved as paper-internal
results (Tables 3.1, 3.2, 3.3; §3.4 cross-adapter replication;
§3.5 efficiency table; §3.6 boundary characterization; §3.7
headline summary; §4 K1–K8) but are not surfaced as headline
contributions.

---

## 3. Why six (vs three or twelve)

The DeepSeek F1-F2 spec asked for "5-6 main" claims; six was chosen
over three because three would force one of the following collapses:

- (i) + (ii) → "the framework + the controller" (loses the
  four-quantity consumption claim).
- (iii) + (vi) → "the cross-budget headline + the boundary" (loses
  the matched-NFE regime specificity).
- (iv) + (v) → "the validation + the ablation" (loses the
  cluster-robust framing).

Three would also collapse the theoretical contribution into the
algorithmic contribution, which conflates the *what* (Theorem 1 +
four quantities) with the *how* (CodimensionSheetScheduler).

Six was chosen over twelve because the prior 64-claim set had
considerable redundancy. Six headline claims provide one claim per
contribution category (theoretical, algorithmic, empirical
efficiency, empirical validation, ablation, boundary) without
redundancy, and the twelve-claim variant would re-introduce the
prior Wave 207 P6 sub-claim structure that was perceived as
"contribution-list inflation" by the DeepSeek F1-F2 reviewer.

---

## 4. Where the six claims appear

The six claims are written into `docs/drafts/paper-flat-flattened.md`
§1 Contributions as a bulleted list, each bullet beginning with the
approved verb ("propose / introduce / establish / validate / provide /
characterize"). The §1 paragraph on Theorem 1 grounds claim (i);
the §3.4 Table 3.3 grounds claims (ii) and (v); the §3.3 Tables 3.1
and 3.2 + §3.4 cross-adapter replication ground claim (iv); the
§3.6 cross-budget curve grounds claim (iii); and the §4 Limitations
draft grounds claim (vi).

---

## 5. Cross-references

- **DeepSeek F1-F2 spec:** §1 contributions reduction (5–6 main
  claims, approved verb set, single-sentence formulation).
- **Prior 64-claim ACTIVE set:** Wave 207 P6 §1 contributions (six
  bullets, plus internal sub-claims in §3 and §4) +
  Wave 208 P7 §3 results drafting (cross-adapter replication,
  five-arm ablation, cluster-robust re-analysis, per-tier framing).
- **Complementary audit docs:**
  - `docs/audit/wave211-p2-six-main-claims.md` (Wave 211 P2
    refinement of the same six claims; the Wave 209 P7 set is the
    equivalent at the Flattening wave marker).
  - `docs/audit/wave209-p7-signature-ordering.md` (companion doc for
    the §3 finding-ordering rationale).
  - `docs/audit/wave209-p7-4arm-reframing.md` (companion doc for
    the 4-arm reframing of the per-seed analysis power).
- **Theorem 1 source:** `docs/theory/theorem-1-self-contained.md`
  (the four quantities, the four-lemma derivation, and the
  closed-form expressions cited in claim (i)).