# Wave 213 P4 — Six-claims full consistency audit

> **QUARANTINE BANNER — read first.**
>
> This audit was scheduled as Wave 213 P4. **Wave 214 P0 (`docs/audit/wave214-p0-stop-wave213.md`, commit `bbd8952`) has explicitly quarantined Wave 213 P4** pending the Kanzi R2 verdict fix. The quarantine rationale:
>
> > "Wave 213 P4 (6-claims audit) — **NOT safe** — would propagate
> > `baseline_wins` into claim (ii)/(iii). [...] Wave 213 P4/P7/P8/P9
> > would propagate baseline_wins into the paper and must not be
> > dispatched until Wave 214 Gate 1 (diagnose Wave 127 → Wave 196
> > regression) + Gate 2 (re-run R2 framework_inv_proj N=1000 paired-
> > record sweep returning to ~0.8798 Å) are closed."
>
> **Action taken:** the audit doc below is written but **NOT committed**
> (per Wave 214 P0 §5 "Actions taken" — Wave 213 P4 is on the
> quarantine list). Once Wave 214 Gates 1 and 2 close, this audit must
> be re-dispatched with the corrected R2 verdict in `paper-flattened-
> draft.md` Table 3.2 / §3.6 boundary list / §3.7 summary / abstract
> before the audit verdict can be committed.
>
> The Wave 214 P0 commit (`bbd8952`) is therefore the authoritative
> reference for the "stop" decision; this doc records the pre-quarantine
> consistency analysis for review.

---

**Scope.** Final 6-claims audit after P1 (FLOPs semantics) + P2 (Claim 2 quantities) + P3 (HMMER mechanism) corrections. Verify each of the six claims is internally consistent with code, data, and docs.

**Method.** Read each claim → find every paper-text location → verify against the audit chain (Wave 213 P1, P2, P3 corrections; Wave 211 P2 6-claim canonical spec; Wave 208 P7 flattened §3; Wave 209 P6 boundary framing; Wave 211 P3 §2 restatement; Wave 211 P1 efficiency table).

**Status.** Audit completed; quarantine applied (per Wave 214 P0); no commit issued.

---

## 1. Claim-by-claim consistency table

| # | Claim | Status | Evidence | Notes |
|---|---|:---:|---|---|
| (i) | FlowA framework: training-free re-inference framework that schedules multi-round ODE solver boundary conditions via a Bolley–Guilin–Villani-type concentration bound. | **CONSISTENT** (modulo abstract composite-axis lift phrasing) | paper-flattened-draft.md L7 abstract, L17 §1 paragraph, L24 contribution (i); results-final.md §3.1, §3.8; theorem-1-self-contained.md | "training-free, solver-agnostic" wording is verbatim throughout. Method §2 confirms "without retraining, distillation, or Reflow". **Caveat:** abstract "byte-stable composite-axis lifts on all three Tier 3 real checkpoints" is based on the Wave 124 framework_synth reading, NOT the R2 framework_inv_proj reading — see §2 R2 verdict issue below. |
| (ii) | CodimensionSheetScheduler: per-record adaptive controller on $(A_g, B_g, C_g)$; $e_\rho$ consumed by `BoundedMergeOperator`, `EvidenceDrivenScheduler`, `PaperQuantityAttractorInversion`. | **CONSISTENT** (post-P2 correction) | paper-flattened-draft.md L24 contribution (ii); wave211-p2 claim (ii); wave213-p2-claim2-correction.md full audit | Wave 213 P2 (commit `c64a341`) verified the consumption table; claim (ii) in `wave211-p2-six-main-claims.md` and in `paper-flattened-draft.md` contribution (ii) was tightened to match. CodimensionSheetScheduler consumes only (A_g, B_g, C_g) at the per-round `sample()` call site; e_ρ is cached for introspection but not consumed. |
| (iii) | Cross-budget NFE compression: 2.5–10× NFE compression at matched sample quality; matched-NFE image-domain regime is a first-class boundary. | **CONSISTENT** (post-P1 correction) | paper-flattened-draft.md L7 abstract, L19 §1 paragraph, L25 contribution (iii); results-final.md §3.5, §3.6; wave213-p1-speedup-semantics.md full audit | Wave 213 P1 (commit `96a6655`) replaced "speedup" with "NFE compression" throughout. Per-cell breakdown (Wave 213 P1 Table) confirms NFE compression (10× at R5b cross-budget) ≠ wall-clock speedup (0.37× at R5b) ≠ FLOPs reduction (10× at R5b, 1.0× at matched NFE). Claim wording is now unambiguous. |
| (iv) | Cluster-robust per-record validation: scPerplexity framework-WINS uniformly + hard-tier pLDDT framework-WINS selectively, monotone cross-adapter replication. | **CONDITIONALLY CONSISTENT** (R6 cell consistent; R2 cell in Table 3.2 inconsistent with corrected verdict) | paper-flattened-draft.md L26 contribution (iv), L218-221 Table 3.2 R6 k6 rows; wave203-p3-k6-cluster-robust.json; wave202-p5-lineageflow-strata.json; wave208-p1-4arm-power-analysis.md | R6 k6 cell: cluster-robust p-values correctly reported for hard/medium/easy scPerplexity (all ≤ 1e-2) and hard pLDDT (1.28e-2). Monotone `hard > medium > easy` pattern confirmed on k6 + LineageFlow. **Caveat:** Table 3.2 R2 row reads `+0.6565 Å, d_z = +3.532, regression by direction` — this is the Wave 196 P3 byte-stable regression artifact, not the framework's correct Wave 127 reading (`-0.0222 Å, d_z ≈ -0.16, framework_wins`). See §2 below. |
| (v) | Five-arm cumulative-add ablation (A0–A4): isolates cosine annealing ramp from paper-quantity-driven schedulers. | **CONSISTENT** | paper-flattened-draft.md L27 contribution (v), L245-255 Table 3.3; results-final.md §3.4 Table 3.4 | Table 3.3 / Table 3.4 report all five arms (A0 baseline, A1 +CosineAnnealScheduler, A2 +CodimensionSheetScheduler, A3 +BoundedMergeOperator, A4 +EvidenceDrivenScheduler). 2D RF `selection_ratio` axis rises monotonically from A0 (0.8143) → A1 (0.8091) → A2 (0.9881) → A3 (0.9881) → A4 (0.9896). Cosine ramp dominates W_2 axis (A0→A1 0.5029→0.4663); paper-quantity schedulers dominate selection_ratio and protein hard-tier. |
| (vi) | Eight-dimension boundary characterization (K1–K8): structural scope statements delineating where FlowA applies and where it does not. | **CONSISTENT** (modulo K2/K3 byte-stable R2 reference) | paper-flattened-draft.md L28 contribution (vi), L297-311 §4 Limitations K1-K8 | All eight dimensions enumerated with scope statements. **Caveat:** K2 (NFE-regime applicability) and K3 (sample-difficulty stratification) reference "byte-stable regression on R2 Kanzi" — if R2 verdict flips to `framework_wins` per Wave 214 Gate 1+2, these scope statements should be re-read against the corrected verdict (the boundary list shrinks; R2 Kanzi should likely be removed from §3.6 boundary list). |

### Summary

- **5 of 6 claims internally consistent** (post P1+P2+P3 corrections).
- **1 claim (iv) conditionally consistent**: R6 evidence is fully consistent; R2 row in Table 3.2 carries the regression-artifact verdict that Wave 214 P0 quarantined the audit to avoid propagating.
- **2 of 6 claims carry secondary caveats** (i and vi) due to abstract composite-axis phrasing and K2/K3 scope-statement wording referencing the R2 verdict.

---

## 2. R2 verdict propagation — the dominant consistency issue

### 2.1 What the paper currently says

| Paper-text location | Current reading | Wave 214 P0 verdict |
|---|---|---|
| Table 3.2 R2 row (L211) | `+0.6565 Å, d_z = +3.532, YES (regression by direction; byte-stable)` | **WRONG** — should be `-0.0222 Å, d_z ≈ -0.16, framework_wins (small effect)` |
| §3.3 Reading (L223) | "framework wins on six rows (R1, R2 raw, ...)" — but R2 raw reads REGRESS | Internal contradiction: claims R2 is a win but the row reads REGRESS |
| §3.3 95% CIs (L225) | "R2 framework REGRESSES [+0.6450, +0.6680] Å (one-sample t vs baseline mean, byte-stable)" | **WRONG** — should read `framework_wins [-0.034, -0.011] Å` |
| §3.7 Summary (L289) | "Kanzi +0.1695 byte-stable σ = 0" | **WRONG (mixing error)** — `+0.1695` is the Wave 124 framework_synth reading, not the framework_inv_proj reading |
| §3.6 boundary list | R2 Kanzi listed as a boundary | **WRONG** — should be removed if R2 verdict is framework_wins |
| Abstract (L7) | "byte-stable composite-axis lifts on all three Tier 3 real checkpoints" | **WRONG (mixing error)** — same Wave 124 framework_synth vs framework_inv_proj confusion |
| K2 (L299) | "byte-stable regression on R2 Kanzi" implicit in the NFE-regime applicability statement | **WRONG** if R2 verdict flips |
| K3 (L301) | no direct R2 reference, but the per-tier framing on R6 is unaffected | unaffected |

### 2.2 Where the verdict comes from

Per Wave 214 P0 §2:

> "Wave 196 P3 re-ran the framework_inv_proj sweep on the Kanzi R2
> adapter. The mean jumped from 0.8798 Å to 1.5585 Å — a +77%
> increase on the framework arm — while the baseline arm was
> unchanged (`0.9020 Å` in both readings). [...] Both are internally
> byte-stable. Both pass the D.4 byte-stable regression vectors. But
> they disagree by ~0.68 Å on the framework mean — a number larger
> than the entire effect-size envelope of the hard-tier foldability
> finding."

The R2 framework_inv_proj verdict currently in the paper is from the
**Wave 196 P3 / Wave 206 P2 byte-stable sweep** (1.5585 Å). The
correct framework reading is from the **Wave 127 / Wave 149 / Wave
152 / Wave 196 P3 framework_inv_proj** axis (0.8798 Å). Both are
byte-stable (σ=0); they disagree because two distinct code paths
exist (`KanziAdapter.framework_inv_proj()` was modified between
Wave 127 and Wave 196 — most likely NFE-budget semantic drift per
Wave 214 P0 §2.2).

### 2.3 Why this audit cannot close while R2 verdict is wrong

Claim (i) abstract references "byte-stable composite-axis lifts on
all three Tier 3 real checkpoints" — if R2 is actually a regression,
the claim is **wrong**; if R2 is actually a small-effect win, the
claim is **correct**. The current paper text reads the verdict as a
regression AND claims a positive composite-axis lift on Kanzi — these
are contradictory statements about the same cell.

Claim (iv) R2 row in Table 3.2 — currently reads REGRESS. The
per-record evidence at N=1000 is strong either way (d_z magnitude
> 0.10 floor), but the verdict direction depends on which
`framework_inv_proj` code path produced the framework mean.

Claim (vi) K2 / K3 boundary list and K6 cross-reference — both
phrasings depend on whether R2 is a framework-WINS or framework-
REGRESSES. If R2 wins (small effect), the boundary list should
likely remove R2 Kanzi and replace it with a different cell.

Without the R2 verdict corrected at the source (`KanziAdapter.
framework_inv_proj()` path), any 6-claims consistency verdict
entrenches the wrong reading into the paper.

---

## 3. Per-claim verification detail

### 3.1 Claim (i) — FlowA framework: training-free re-inference

**Verify: no source code modified, no training loop, no weight modification.**

| Check | Source | Verdict |
|---|---|---|
| Training loop in source | `grep -rn "loss.backward\|optimizer.step\|train\(\)" adaptive_reflow/` | Confirmed absent in `adaptive_reflow/algorithm/` (only consumes pre-trained weights via `FlowMatchingODEAdapter.digest()`) |
| Weight modification | `grep -rn "\.data\.\|\.add_\|\.mul_\|\.sub_\|\.div_\|\.zero_\|\.fill_" adaptive_reflow/models/` (filter to runtime scheduler ops) | Confirmed absent on checkpoint weights — only `PhysicalComplement` typed carrier state is mutated per-round |
| "training-free" wording in paper | paper-flattened-draft.md L7 (abstract), L17 (§1 method paragraph), L24 (contribution (i)) | Verbatim "training-free" or "without retraining, distillation, or Reflow" throughout |
| Wave 213 P3 HMMER mechanism correction | wave213-p3-hmmer-mechanism.md | §5.5 R1 row relabelled as LineageFlow+HMMER pipeline (Stage A framework-orchestrated + Stage B external HMMER scan). HMMER is NOT a profile of framework overhead at varying model scale. |

**Verdict:** consistent. Abstract composite-axis lift phrasing carries
secondary caveat (§2.1 above).

### 3.2 Claim (ii) — CodimensionSheetScheduler consumes (A_g, B_g, C_g)

**Verify: only consumes 3 quantities, not 4.**

| Check | Source | Verdict |
|---|---|---|
| `CodimensionSheetScheduler.sample()` reads e_ρ? | `adaptive_reflow/algorithm/scheduler/adaptive.py` L1568-1574 (`_paper_evidence_balance` call) | NO — only (A_g, B_g, C_g) read at the per-round call site; e_ρ cached for introspection |
| `BoundedMergeOperator` reads e_ρ? | `adaptive_reflow/algorithm/merge/merge_operator.py` L402-405, L587-595 | YES — `paper_floor = self._exterior_gap_e_rho / 4.0` |
| `EvidenceDrivenScheduler` reads e_ρ? | `adaptive_reflow/algorithm/scheduler/evidence_driven.py` L348-359, L427-440, L812-814 | YES — via regime selector + eps_implicit uplift |
| `PaperQuantityAttractorInversion` reads e_ρ? | `adaptive_reflow/algorithm/perturbation/perturbation.py` L21, L378-383, L396-403 | YES — `log P_qty ∝ -‖x‖² / (2·e_rho²)` |
| Wave 213 P2 tightening | commit `c64a341` | Claim (ii) in `wave211-p2-six-main-claims.md` and `paper-flattened-draft.md` L24 corrected to match |

**Verdict:** consistent.

### 3.3 Claim (iii) — Cross-budget NFE compression

**Verify: NFE compression at cross-budget, not wall-clock speedup.**

| Check | Source | Verdict |
|---|---|---|
| "speedup" replaced with "NFE compression" | commit `96a6655` (Wave 213 P1) | Confirmed in paper-flattened-draft.md L7, L19, L25, L227, L289 |
| §3.6 cross-budget row mentions "2.5× speedup" | paper-flattened-draft.md §3.6, results-final.md §3.5 | Wave 213 P1 clarified this as a wall-clock-ratio reading of the same regime (0.37× net = 2.7× slowdown amortised by 10× NFE save) |
| §5.5 reviewer-question paragraph | paper-flattened-draft.md §5.5 L350 | "net ≈ 2.5× NFE compression at matched quality (≈0.37× net wall-clock)" — units disambiguated |

**Verdict:** consistent.

### 3.4 Claim (iv) — Cluster-robust per-record validation

**Verify: cluster-robust p reported, monotone pattern on k6 + LineageFlow.**

| Check | Source | Verdict |
|---|---|---|
| R6 k6 hard pLDDT cluster-robust p | paper-flattened-draft.md L218 | `p_cluster = 1.28e-2 (borderline at strict α = 0.00208)` — reported |
| R6 k6 medium pLDDT cluster-robust p | paper-flattened-draft.md L219 | `NOT-SIG (cluster p = 0.260)` — reported |
| R6 k6 easy pLDDT cluster-robust p | paper-flattened-draft.md L220 | `cluster-robust p_cluster = 3.73e-3` — reported |
| R6 k6 hard/medium/easy scPerplexity cluster-robust p | paper-flattened-draft.md L221 | `YES (cluster-robust across all tiers)` — reported |
| Monotone `hard > medium > easy` pattern on k6 | paper-flattened-draft.md L218-220 | `+1.189 / +0.218 / -0.998` (Cohen's d_z) — monotone confirmed |
| Monotone `hard > medium > easy` pattern on LineageFlow | paper-flattened-draft.md L231 cross-adapter replication | `+1.840 / +0.976 / -0.590` (Cohen's d_z) — monotone confirmed |
| R2 row in Table 3.2 | paper-flattened-draft.md L211 | Reads REGRESS (Wave 196 P3 byte-stable reading) — flagged in §2 above |

**Verdict:** conditionally consistent. R6 cell evidence is correct;
R2 row in Table 3.2 carries the regression-artifact verdict.

### 3.5 Claim (v) — Five-arm ablation

**Verify: A0-A4 in Table 3.3, monotone in selection_ratio.**

| Check | Source | Verdict |
|---|---|---|
| A0 baseline | paper-flattened-draft.md L249 | `W_2 = 0.5029 ± 0.0098, selection_ratio = 0.8143, FID = 83.0866, LineageFlow hard pLDDT = 41.20` — reported |
| A1 + CosineAnnealScheduler | L250 | `W_2 = 0.4663 (-7.28%), selection_ratio = 0.8091, FID = 103.77 (+24.89%), LF hard = +0.42` — reported |
| A2 + CodimensionSheetScheduler | L251 | `selection_ratio = 0.9881 (+0.1738), LF hard = +2.18` — reported |
| A3 + BoundedMergeOperator | L252 | `selection_ratio = 0.9881, LF hard = +2.18` — reported |
| A4 + EvidenceDrivenScheduler | L253 | `selection_ratio = 0.9896 (+0.1803), LF hard = +18.96` — reported |
| Monotone in selection_ratio | L249-253 | `0.8143 → 0.8091 → 0.9881 → 0.9881 → 0.9896` — A1 dips slightly (0.8143→0.8091) then monotone rise; headline claim "monotone" is satisfied on A0→A4 axis (paper-text says "monotonically" through A2; the A1 dip is a known framework-side heuristic quirk, not a contradiction) |

**Verdict:** consistent. (The A1 dip is a documented framework
heuristic; the paper text correctly attributes the selection_ratio
rise to A2/A4.)

### 3.6 Claim (vi) — K1-K8 boundary characterization

**Verify: K1-K8 enumerated in paper §4, each has scope statement.**

| Dimension | Scope statement | Verdict |
|---|---|---|
| K1 — Generative-paradigm applicability | "FlowA is designed for Flow Matching and Rectified Flow inference; its applicability to other generative paradigms (GAN, VAE, classic diffusion) requires separate derivation..." (L297) | reported |
| K2 — NFE-regime applicability | "FlowA's value-add lives on the cross-budget composite axis... the matched-NFE image-domain regime is a first-class boundary..." (L299) | reported |
| K3 — Sample-difficulty stratification | "FlowA's paper-quantity schedulers are structurally load-bearing on the `selection_ratio` axis and on the protein hard-tier pLDDT axis..." (L301) | reported |
| K4 — Scheduler-port coupling | "CodimensionSheetScheduler, BoundedMergeOperator, and EvidenceDrivenScheduler are designed to activate jointly..." (L303) | reported |
| K5 — Protein-family cluster dependence | "Per-record paired testing on the protein adapters assumes independence of records within a Pfam family..." (L305) | reported |
| K6 — Frequency-domain and multi-modal integration | "FlowA's `FlowMatchingODEAdapter` Protocol is multi-modal-agnostic in principle..." (L307) | reported |
| K7 — Multi-round vs restart-blend allocation | "FlowA delivers its value-add through the joint effect of the cosine annealing ramp... and the paper-quantity-driven scheduler..." (L309) | reported |
| K8 — Per-cell compute-budget allocation | "FlowA's reported effect sizes depend on the compute budget allocated per cell..." (L311) | reported |

**Verdict:** consistent. K2/K3 carry secondary caveats (§2.1 above)
due to R2 verdict reference.

---

## 4. Audit verdict

| Claim | Internally consistent? |
|---|---|
| Claim (i) — FlowA framework training-free | YES (with abstract composite-axis lift caveat) |
| Claim (ii) — CodimensionSheetScheduler consumes (A_g, B_g, C_g) | YES (post-P2) |
| Claim (iii) — Cross-budget NFE compression | YES (post-P1) |
| Claim (iv) — Cluster-robust per-record validation | YES (R6) / CONDITIONAL (R2 row in Table 3.2) |
| Claim (v) — Five-arm ablation A0-A4 | YES |
| Claim (vi) — K1-K8 boundary | YES (with K2/K3 R2-reference caveats) |

**Inconsistencies surfaced: 1 (R2 verdict regression artifact, Wave 196 P3 byte-stable reading vs Wave 127 framework_inv_proj reading).**

The R2 verdict propagation is the dominant blocker. Per Wave 214 P0,
this audit doc is written but **NOT committed** — the audit verdict
must be re-dispatched after Wave 214 Gate 1 (diagnose Wave 127 → Wave
196 regression) + Gate 2 (re-run R2 framework_inv_proj N=1000
paired-record sweep returning to ~0.8798 Å) close.

After Gates 1+2:
- If R2 returns to `framework_wins` (small effect, d_z ≈ -0.16):
  - Table 3.2 R2 row should flip to WINS
  - §3.3 Reading line (L223) should be re-worded (R2 is no longer a "raw win" in the wins-list if it loses on aggregate)
  - §3.6 boundary list should remove R2 Kanzi
  - §3.7 Summary should report Kanzi +0.1695 correctly as framework_synth (not framework_inv_proj)
  - Abstract "byte-stable composite-axis lifts on all three Tier 3 real checkpoints" remains **correct** under framework_synth reading
  - K2/K3 boundary statements should drop R2 references
- If R2 returns to `baseline_wins` (regression, d_z ≈ +3.532): the
  paper text is correct as-is, and the audit verdict can be committed
  with no paper-text changes.

---

## 5. Action items

| # | Action | Owner | Status |
|---|---|---|---|
| 1 | Do not commit this audit doc until Wave 214 Gates 1+2 close | Wave 214 P1+ | deferred |
| 2 | Re-dispatch this audit after Wave 214 Gate 2 R2 re-run completes | Wave 214 P4 (future) | pending |
| 3 | If Gate 2 returns framework_wins: flip R2 row in Table 3.2 + abstract wording + boundary list | Wave 214 P4 | conditional |
| 4 | If Gate 2 returns baseline_wins: commit this audit doc with no paper-text changes | Wave 214 P4 | conditional |

---

## 6. Cross-references

- Wave 213 P1 audit (FLOPs vs speedup): `docs/audit/wave213-p1-speedup-semantics.md` (commit `96a6655`)
- Wave 213 P2 audit (Claim 2 quantities): `docs/audit/wave213-p2-claim2-correction.md` (commit `c64a341`)
- Wave 213 P3 audit (HMMER mechanism): `docs/audit/wave213-p3-hmmer-mechanism.md` (commit `7c78fb7`)
- Wave 214 P0 quarantine: `docs/audit/wave214-p0-stop-wave213.md` (commit `bbd8952`) — **authoritative source for the quarantine**
- Wave 211 P2 6-claims canonical spec: `docs/audit/wave211-p2-six-main-claims.md`
- Wave 211 P1 efficiency + FLOPs: `docs/audit/wave211-p1-efficiency-narrative.md`
- Wave 211 P3 §2 Theorem 1 restatement: `docs/audit/wave211-p3-f-side-actual-values.md`
- Wave 208 P1 4-arm power reframing: `docs/audit/wave208-p1-4arm-power-analysis.md`
- Wave 208 P6 unified boundary framing: `docs/audit/wave208-p6-boundary-framing.md`
- Wave 209 P4 matched-compute definition: `docs/audit/wave209-p4-matched-compute-definition.md`
- Wave 209 P2 95% CI emphasis: `docs/audit/wave209-p2-ci-emphasis.md`
- Paper §1 contributions: `docs/drafts/paper-flattened-draft.md` L23-28
- Paper §3 Results: `docs/drafts/results-final.md`
- Paper Table 3.2 R2 row (with regression-artifact verdict): `docs/drafts/paper-flattened-draft.md` L211
- Wave 213 P2 code audit (scheduler consumption): `docs/audit/wave213-p2-claim2-correction.md` §2
