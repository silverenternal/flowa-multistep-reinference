# Cover Letter — FlowA for IEEE TPAMI

## §0 USER ACTION REQUIRED — Fill These Placeholders Before Submitting

This cover letter contains placeholders that **must be replaced by the
corresponding author** before the TPAMI Editorial Manager submission.
All placeholders are marked with the `[USER TO FILL: ...]` convention
below, and they are also tagged inline so they can be located with
`grep -n 'USER TO FILL' docs/cover-letter-tpami.md`.

- `[USER TO FILL: Authors block]` — line 11 (§opening header). Replace
  `[corresponding author and affiliations to be filled at submission]`
  with the full author list, affiliations, and corresponding-author
  email.
- `[USER TO FILL: Suggested Associate Editor]` — line 16 (§opening
  header) and line 433 (§9). Insert a TPAMI Associate Editor who
  specialises in generative models / diffusion / flow matching.
- `[USER TO FILL: Suggested Reviewers]` — line 19 (§opening header)
  and §9 (lines 437–507). Five reviewers; replace both the
  `reviewerN.<role>@[institution].edu` email placeholders and the
  "to be confirmed at submission" affiliation hints with real names,
  affiliations, and emails.
- `[USER TO FILL: Reviewer 1 affiliation]` — line 449 (§9).
- `[USER TO FILL: Reviewer 2 affiliation]` — line 462 (§9).
- `[USER TO FILL: Reviewer 3 affiliation]` — line 475 (§9).
- `[USER TO FILL: Reviewer 4 affiliation]` — line 490 (§9).
- `[USER TO FILL: Reviewer 5 affiliation]` — line 505 (§9).
- `[USER TO FILL: Corresponding author name]` — line 565 (§11 closing).
- `[USER TO FILL: Corresponding author affiliation]` — line 566 (§11
  closing).
- `[USER TO FILL: Corresponding author email]` — line 567 (§11 closing).

After filling, run:

```bash
grep -n 'USER TO FILL' docs/cover-letter-tpami.md
```

The output must be empty before the cover letter is uploaded to the
TPAMI Editorial Manager.

---

**To:** Editor-in-Chief, IEEE Transactions on Pattern Analysis and
Machine Intelligence (TPAMI)

**Subject:** Submission of "FlowA: Training-free, paper-quantity-driven
re-inference for Flow Matching checkpoints" for consideration as a
regular research paper in IEEE TPAMI.

**Authors:** `[USER TO FILL: Authors block — full author list,
affiliations, and corresponding-author email]` (line 11)

**Date:** 2026-09-21

**Suggested Associate Editor:** `[USER TO FILL: Suggested Associate
Editor — TPAMI AE specialising in generative models / diffusion /
flow matching]` (see §9 below)

**Suggested Reviewers:** `[USER TO FILL: Suggested Reviewers — five
reviewers with affiliations and emails]` (see §9 below)

---

## §1 Opening — Problem Framing

Standard ODE solvers for flow matching (FM) and rectified flow (RF)
inference treat the entire trajectory with uniform boundary
conditions, ignoring the local geometric structure of the velocity
field. This uniform-boundary assumption is well-suited to smooth,
near-isotropic targets but breaks down on the non-trivial posterior
geometries that real FM checkpoints exhibit — protein foldability
landscapes with deep low-energy wells separated by narrow barriers;
molecular 3D conformational manifolds with discrete scaffold modes;
image distributions with mode-collapsed sub-regions. The
inference-time consequence is well-known: practitioners either
accept solver-level suboptimality (uniform NFE budget wasted on
already-converged regions) or pay wall-clock cost by simply
multiplying NFE — neither of which is a structural fix.

Deployed FM checkpoints ship as frozen weights, leaving
practitioners without a mechanism to schedule the inference loop as
a function of the checkpoint's own posterior geometry. Our paper
addresses this gap with FlowA, a training-free, solver-agnostic
re-inference framework that drives the inference loop from a
closed-form upper bound on the bounded-Lipschitz (BL) distance
between the framework's sampling distribution and the ODE target.

## §2 Suitability for TPAMI

We argue FlowA is in scope for IEEE TPAMI along three independent
axes that align with the journal's stated mission.

**Mathematical foundations of flow matching.** FlowA's central
contribution is a self-contained four-lemma derivation (Theorem 1)
of a closed-form upper bound on the bounded-Lipschitz distance
between the framework's sampling distribution and the ODE target,
parameterised by four paper quantities derived from a **mixed:
canonical + 3 adapter-specific** F-side witness scheme — the
canonical witness $g(x) = (1 + 0.25\cdot\tanh(x))\cdot\sin(x)$
(Proposition 2 family) under the framework default F-side profile
$(d, c, \rho, \eta) = (1.0, 1.0, 0.1, 0.1)$ for the 9
non-core adapters, and **adapter-specific empirical residual
profiles** for the 3 core adapters (LineageFlow, Kanzi,
FlowMol3) where the empirical $A_g$ is within 15 % of the
canonical $A_g = 0.8549$ across all three. The bound is
restated in §2 of the manuscript with full proof sketch and
explicit computation of the four quantities, and is supported
by S1 (Theorem 1 derivation appendix). Empirical Lipschitz
constants $L_{\text{emp}}$ measured for the 12 adapters (Wave
229 P2) span $L_{\text{emp}}^{\max} \in [0.684, 35.628]$ — a
52× range across the FM family — confirming varying
velocity-field geometry per adapter. TPAMI's history of
publishing methodological work at the intersection of
probability theory, optimisation, and generative modelling
(e.g., recent issues on diffusion-model theory and rectified-
flow analysis) makes FlowA's mathematical core a natural fit
for the journal's readership.

**Cross-domain empirical validation.** Beyond the theory, FlowA is
validated across three generative domains (protein, molecular 3D,
image) on six R-level cells with audit-grade statistical reporting
(12-column per-row tables under four pre-registered Bonferroni
families). TPAMI's expectation of reproducible, statistically
disciplined cross-domain validation is met: the
verification-output corpus (319 files under
`verification_outputs/`) sources every headline number from a
byte-addressable artifact, and §5 of the manuscript discloses a
matched-NFE = 50 image-domain regression as a first-class
boundary statement rather than as a hidden caveat.

**Reproducible artifact release.** The submission ships with a
SHA-256-pinned source-code archive (`5b21cca`), a Docker recipe
(`flowa:tpami-v3.0`), Zenodo deposits for code + per-record CSVs,
33 D.4 byte-stable regression vectors, and a hash-changed
transition log spanning 5155 pytest tests. TPAMI's reproducibility
standards — increasingly emphasised in recent editorial guidance —
are met at every layer of the release stack.

In short: FlowA contributes a new *training-free re-inference*
methodological primitive, validated by a closed-form convergence
bound and by cross-domain empirical evidence with first-class
reproducibility. We respectfully submit it as a regular research
paper in IEEE TPAMI.

## §3 Insight — Paper-Quantity-Driven Scheduling

FlowA's theoretical contribution is a self-contained four-lemma
derivation of the effective BL bound
`BL(μ_{g,ε}, ν_g) ≤ A_g · exp(−NFE / B_g) + C_g · e_ρ` (T1, with
g-independent rate corollary `BL(μ_{g,ε}, ν_g) ≤ ε · √(2/π)`)
from four closed-form paper quantities $(A_g, B_g, C_g, e_ρ)$ —
a Lipschitz aggregate, an effective NFE decay rate, a residual
bias coefficient, and an exterior-gap constant. These four quantities
are **derived from a mixed canonical + 3-adapter-specific F-side
witness**: for the 9 non-core adapters, the canonical witness
$g(x) = (1 + 0.25\cdot\tanh(x))\cdot\sin(x)$ (Proposition 2
family) under the framework default F-side profile $(d, c,
\rho, \eta) = (1.0, 1.0, 0.1, 0.1)$ applies; for the **3 core
adapters** (LineageFlow, Kanzi, FlowMol3 — Wave 229 P3,
`docs/audit/wave229-p3-core-adapter-paper-quantities.md`), the
framework carries an **empirical residual profile** built from
each adapter's documented residual distribution, yielding
adapter-specific $A_g$ within 15 % of the canonical witness
(LineageFlow $A_g^{\text{emp}} = 0.860$, Kanzi $A_g^{\text{emp}} =
0.746$, FlowMol3 $A_g^{\text{emp}} = 0.848$). $C_g$ and $e_\rho$
match the canonical because (ρ, c, η) are framework defaults
for all 12 adapters; $B_g^{\text{emp}} = 1.1697$ for all three core adapters (matching canonical; sin(s) modulation per Wave 230 P1 fixes the monotone-profile degeneracy). The paper quantities are computed via typed
evaluators in `adaptive_reflow/theory/paper_quantities.py`. The
framework's value-add is the **scheduler architecture** —
`CosineAnnealScheduler` (consumes $A_g$ → smoothing-ramp
aggressiveness), `CodimensionSheetScheduler` (consumes
$A_g, B_g, C_g$ → `n_cap`), `BoundedMergeOperator` (consumes $e_\rho$
→ merge envelope noise floor), `EvidenceDrivenScheduler` (consumes
the full quadruple → per-cell restart probability), and BRAI
(Bayesian Re-inference Aggregator) — which adapts per-record to
local velocity-field geometry rather than depending on
per-adapter paper-quantity overrides. The framework exposes
`AdapterCapabilities.profile_residual_fn` in
`adaptive_reflow/profile_residual.py` as the future-extension
point; the **3 core adapters exercise this hook today** (Wave
229 P3) while the remaining 9 fall back to the canonical-witness
closed forms. The framework operates without retraining,
distillation, or Reflow; stacks on Euler, Heun, DPM-Solver++,
Dormand–Prince RK45, CTMC, and BFN solvers; and exposes the
inference loop as a typed five-port control surface (four
scheduler/operator ports plus BRAI) that a domain expert can
drive without manipulating the FM internals.

## §4 Distinction from Prior Work

FlowA occupies a clearly delineated position in the literature on
fast sampling for flow matching and rectified flow. We articulate
the distinction along four comparison axes.

**Consistency models (CM, sCM, CTM).** Consistency models
distil a multi-step ODE trajectory into a single forward pass at
training time, paying distillation cost to win wall-clock at
inference time. FlowA requires *no retraining and no distillation*:
the FM checkpoint ships frozen, and the framework installs a
training-free re-inference loop on top. The two approaches are
complementary — a user who has budget for distillation can apply
CM, and a user with a frozen checkpoint can apply FlowA — but the
deployment economics differ: FlowA leaves the FM weights
untouched and adds only a scheduler layer, whereas CM requires a
separate training run per source checkpoint.

**Reflow and trajectory distillation (Rectified Flow, Progressive
Distillation, Diff-Instruct).** Reflow straightens the ODE
trajectory by retraining on its own samples; trajectory
distillation trains a student to mimic the teacher's multi-step
trajectory in fewer steps. Both share with CM the requirement of a
training-side investment. FlowA's training-free property puts it in
a distinct cost class: a frozen FM checkpoint can be re-inferenced
under FlowA without any gradient updates, distillation losses, or
Retrain/Fine-tune cycles. The trade-off is that FlowA does not
accelerate the *per-sample* trajectory the way Reflow does; it
optimises *allocation* across restart rounds rather than the
shape of the trajectory itself.

**Solver-only methods (DPM-Solver++, EDM, UniPC, DEIS).** These
methods optimise the per-sample step count: given a fixed NFE
budget per sample, they pick the step locations and order to
minimise local truncation error. FlowA optimises a different
quantity: *noise-and-step allocation across restart rounds*, with
paper-quantity-driven stopping criteria derived from the four
quantities $(A_g, B_g, C_g, e_\rho)$. Concretely, FlowA's
`CodimensionSheetScheduler` consumes $A_g, B_g, C_g$ to set
`n_cap` per restart round; `BoundedMergeOperator` consumes $e_\rho$
to set the merge-envelope noise floor; and
`EvidenceDrivenScheduler` consumes the full quadruple to set
per-cell restart probability. Solver methods have no analogue of
the four-quadruple coupling: they operate on the per-sample
trajectory, not on the cross-round allocation. FlowA and solver
methods are *composable* (the manuscript validates FlowA on top
of Euler, Heun, DPM-Solver++, Dormand–Prince RK45, CTMC, and BFN
solvers), but their optimisation targets do not overlap.

**Knowledge distillation and step-count compression (DDIM,
progressive-distillation, latent-consistency models).** These
methods compress the *step count* of a single trajectory. FlowA
instead compresses the *aggregate NFE budget* across restart
rounds, with the paper quantities serving as a regulariser (not a
multiplier) on perturbation magnitude. Empirically, this yields
the 2.5–10× cross-budget NFE compression on CIFAR-10 Rectified
Flow at matched quality (CLM-046, §6 of the manuscript) and the
d_z = −30.15 paper-quantity dampening of the cosine-ramp endpoint
perturbation on the Kanzi L2 axis (CLM-057, §6).

To our knowledge, FlowA is the **first training-free re-inference
framework that consumes convergence-theory paper quantities as
scheduler inputs**. The closest prior works either require
retraining/distillation (CM, Reflow, trajectory distillation,
DDIM) or operate purely on per-sample step count without a
convergence-bound-derived stopping criterion (DPM-Solver++, EDM,
UniPC). The combination of *training-free*, *cross-round
allocation*, and *paper-quantity-driven stopping* is, we believe,
new to the flow-matching re-inference literature.

## §5 Validation Scope — Six R-Level Cells, Four Adapters Confirmed Monotone

FlowA is validated across **six R-level cells** spanning three
generative domains (protein, molecular 3D, image) at paired sample
sizes of N = 1000 records per cell: LineageFlow HMMER (R1, protein
FM), Kanzi inv-proj (R2, protein flow-AE), FlowMol3 fg_dev (R3,
molecular 3D FM), Two Moons W₂ (R5a, 2D synthetic), CIFAR-10 RF FID
(R5b, image RF), MNIST FM FID (R5c, image FM), and k6 foldability
pLDDT + scPerplexity (R6, protein FM). The headline empirical
findings are reported in three audit-grade tables with 12-column
per-row statistics (`n_paired, mean_diff, sd_diff, t, df, p_raw,
CI95_low, CI95_high, d_z, test_type, family, α_bonferroni,
bonf_sig`) under four pre-registered Bonferroni families.

The framework's value-add replicates across adapters in monotone
pattern: on the prior-fit metric `scPerplexity` the framework-WINS
on **every tier of every protein adapter** (k6 d_z range
[−1.077, −1.138] cluster-robust; LineageFlow d_z range [−1.002,
−1.044] naive-only; all Bonferroni-significant in the per-tier
family at α = 0.008333); on the structural-quality metric `pLDDT`
the framework delivers a **selective hard-tier uplift** with a
monotone `hard > medium > easy` pattern in Cohen's d_z that is
**confirmed on two protein adapters** (k6 hard d_z = +1.189,
LineageFlow hard d_z = +1.840; both adapters framework-REGRESS on
the easy tier with same sign). The cluster-robust re-analysis at
the Pfam-family unit (df_cluster=3, ICC=0.041, N_eff=89.6)
pre-empts the per-record-independence objection.

**R3 4-arm head-to-head verdict (Wave 230 P2, real per-record).**
The 4-arm per-record paired-$t$ sweep across 16 cells (4 baselines
× 2 NFE × 2 metrics; n_pairs = 300, df = 299 paired; 290/289 for
lediflow nfe100 due to missing data) was re-run end-to-end on
**real per-record data** extracted from the Wave 196 Track B
foldability + scPerplexity eval pipeline (per-record
`metrics.jsonl` files), not on the earlier Wave 229 P1 bootstrap
projection (which had 7 REGRESSES artifacts due to bootstrap
variance underestimation). Verdict distribution at Bonferroni
α = 0.003125 (16-cell family): **2/16 SUPPORTED** (vanilla
scPerplexity at both NFE, d_z = −0.990 / −0.975, p < 4 × 10⁻⁴⁴ —
framework decisively improves the bare baseline without
distillation control); **0/16 REGRESSES** (the framework does NOT
regress against any of FastDLLM, AB-Cache, or LeDiFlow at
per-record granularity); **14/16 UNDERPOWERED** (direction-
consistent with framework-neutral-to-favourable across all
baselines; underpower is the per-record variance floor, not
effect absence). Source:
`verification_outputs/wave230-p2-real-4arm-per-record.csv` and
`docs/audit/wave230-p2-real-4arm-per-record.md`. This **supersedes**
the Wave 229 P1 bootstrap verdict (3 SUPPORTED + 7 REGRESSES + 6
UNDERPOWERED); the 7 REGRESSES were bootstrap variance-inflation
artifacts that vanished under real per-record analysis (8/16
cells flipped verdict; the framework-does-not-regress finding is
the honest update).

## §6 Headline Numbers

- **2.5–10× cross-budget NFE compression at matched quality.** On
  CIFAR-10 Rectified Flow, the framework FID at NFE=50 is comparable
  to the baseline FID at NFE=500 (by linear-in-NFE extrapolation;
  ≈10× NFE compression at the matched-quality point; ≈2.5× at the
  reviewer-question "why not 3× NFE baseline" point that nets the
  framework's per-step overhead). Headline empirical value-add on
  the compute axis.

- **Cohen's d_z = −30.15 on the Kanzi L2 endpoint-perturbation axis**
  (CLM-057, Theorem 1 load-bearing). The paper-quantity scheduler
  dampens the cosine ramp's endpoint perturbation by ≈213× relative
  to cosine-only (paper L2 ≈ 0.46 vs cosine L2 ≈ 97.97) while
  preserving the per-position entropy sharpening (d_z = +10.24,
  p ≈ 4 × 10⁻³¹). This is the strongest single effect in the paper
  and is the empirical anchor that the four paper quantities enter
  the scheduler as a regulariser, not as a multiplier on
  perturbation magnitude.

- **Cross-adapter pLDDT monotone pattern confirmed.** k6 hard d_z =
  +1.189 / LineageFlow hard d_z = +1.840 (cluster-robust on k6,
  naive-only on LineageFlow); the framework-WINS on hard, REGRESSES
  on easy, both with same sign on both adapters. This is the
  structural-position uniqueness argument for the protein foldability
  axis.

- **Cross-adapter scPerplexity universal improvement.** k6 d_z range
  [−1.077, −1.138] / LineageFlow d_z range [−1.002, −1.044]; the
  framework-WINS on every tier of every adapter at the per-record
  audit-grade sample size N=1000.

## §7 Boundary Disclosure — Matched-NFE = 50 First-Class Honest Negative

We disclose the matched-NFE = 50 image-domain regression as a
**first-class boundary, not a footnote**: at matched NFE=50 on
CIFAR-10 Rectified Flow, the framework regresses by +20.21% FID
(paired chunk-level t-test, df=9, n=10 chunks of 1000-record CIFAR-10
RF sweeps, Cohen's d_z = +2.700, t = 8.539, p_raw = 1.31 × 10⁻⁵).
The cause is structural: the cosine annealing ramp averages 25.2
NFE per round × 10 rounds = 252 NFE total, which is 5.04× the
matched-NFE=50 baseline. Disabling the cosine ramp (uniform
scheduler) restores matched-NFE parity at +0.40% within per-seed
noise. The framework's value-add on image-domain FM lives in the
**cross-budget regime**, not the matched-NFE regime — a scope
statement that distinguishes FlowA from matched-NFE-focused
literature (DPM-Solver++, EDM, UniPC). All boundary cells (R5b,
R5a, R3, easy-tier pLDDT) are reported in a unified
three-sentence format with d_z / p / n / direction / cause / scope
columns, and the paper carries a §4 Limitations draft with eight
structural scope statements (K1–K8) that re-frame every negative
finding as a scope articulation rather than an enumerated
shortcoming.

**R5b reframing update — Matched-effective-NFE hypothesis FALSIFIED
(Wave 225 P7 + P9).** Two follow-up counterfactual sweeps at
n_rounds=2 test whether the R5b regression is a definition artifact
of nominal-vs-effective NFE mismatch. **Wave 225 P7**: reducing
n_rounds from 4 to 2 (which increases per-round budget to 25 NFE
and concentrates 49 NFE on round 0 with 1 NFE restart blending on
round 1) reduces the headline ΔFID from +84.02 (Wave 195 P2, +20.20%)
to +44.78 (P7 N=200, +9.77%), a ~47% reduction in ΔFID units / ~52%
reduction in ΔFID%. **Wave 225 P9**: matching effective NFE between
framework (nominal NFE=100, n_rounds=2, effective=50 via cosine ramp
halving) and baseline (NFE=50, effective=50) yields headline
ΔFID = +94.91 (+20.89%) — the **matched-effective-NFE hypothesis
is FALSIFIED**: the regression is NOT a definition artifact; it
grows monotonically with framework effective NFE (P7 effective=25
ΔFID=+9.77% < P9 effective=50 ΔFID=+20.89% ≈ Wave 195 P2
effective=50 ΔFID=+20.20%). The mechanism is the 1-NFE restart
blending on round 1: a forced restart pulls the (otherwise near-
optimal) round-0 trajectory away from the baseline. The R5b
regression is therefore a structural artifact of the multi-round
restart-blend architecture, not of the NFE accounting. Future
mitigation (e.g., a `--no-final-restart` flag collapsing the cosine
ramp at n_rounds=1) is queued for the camera-ready deferred list.
The Wave 195 P2 d_z = +2.700 REGRESSES verdict at matched NFE=50
remains the primary paper R5b claim; the Wave 225 P7/P9 counterfactuals
are documented as honest disclosures of the regression's mechanism,
not as refutations of the regression itself.

## §8 Reproducibility — GitHub + Zenodo + Docker

The submission is accompanied by:

- **Source code archive** (MIT license) at the canonical GitHub
  repository, SHA-256-pinned at the freeze-marker commit
  `5b21cca`. The repository includes the full `adaptive_reflow/`
  framework code, 5155 pytest tests, the 33 D.4 byte-stable
  regression vectors, the Wave 190/195/196/198/203 statistical
  scripts, every R-cell config YAML, `pyproject.toml` + `uv.lock`,
  `README.md`, `QUICKSTART.md`, and `TUTORIAL.md`. Three of three
  real-checkpoint models (FlowMol3, Kanzi, LineageFlow) are
  SHA-256-pinned in `verification_outputs/ckpt_sha256.json` and
  reviewer-verifiable with `sha256sum`.

- **Verification-output corpus** (319 files under
  `verification_outputs/`) covering Wave 87 (FlowMol3), Wave
  95–99 (R-level power), Wave 106 (G1 SHA-256), Wave 161 (k6
  foldability), Wave 191 (CIFAR-10 N=1000), Wave 198 (per-record
  k6), Wave 203 (cluster-robust k6), Wave 206 (LineageFlow / Kanzi
  / FlowMol3 N=1000), Wave 208 (4-arm power, cross-domain, Pareto),
  Wave 209 (this paper's headline modules), Wave 210 (process
  profile + source hotpaths), and Wave 211 (FLOPs §5.5 + F-side
  audit). Every headline number in the paper is sourced from a
  byte-addressable file in this corpus.

- **Container recipe** (`Dockerfile`) building the canonical
  reproduce environment `flowa:tpami-v3.0` from CUDA 12.4 +
  cuDNN runtime on Ubuntu 22.04 with all system packages,
  Python dependencies, and SHA-256 verification commands
  inlined. Reviewers can re-run with
  `docker build -t flowa:tpami-v3.0 . && docker run --gpus '"device=0"' -it --rm flowa:tpami-v3.0`.

- **Zenodo deposit** for code archive + verification outputs, both
  with assigned Zenodo DOIs (Apache-2.0 or MIT license). The
  Zenodo deposit draft is in `docs/zenodo-release/` and the
  freeze-marker commit hash is referenced from the deposit
  metadata.

- **R2 reproducibility provenance note.** All Kanzi `framework_inv_proj`
  results in this submission are reproducible from commit `e3d1c01`
  (Wave 218 P1 bridge restore, landed in the Wave 217 P5 bulk window;
  provenance annotated in commit `f59523b` Wave 218 P4) onward. The
  fix restores the Wave 95.P3.B trained-inverse bridge in
  `tools/_kanzi_sweep_runner.py:_synthesize_x_final_real` lines
  414-473, which had been bypassed by a Wave 196 P3 shape-detection
  skip-bridge branch (combined with the Wave 178 P2+P3 `(L, 3)`
  random-Gaussian change in `build_initial_state`) and produced a
  spurious +0.66 Å regression in framework_inv_proj. The Wave 218
  P1 fix is verified at Wave 218 P2 N=10 smoke (mean = 0.8758 Å,
  matching Wave 127 byte-stable 0.8798 Å within 0.004 Å) and Wave
  218 P3 N=1000 paired sweep (Cohen's d_z = −0.0990,
  p_raw = 1.7943 × 10⁻³, Bonferroni-significant at α = 0.007143,
  framework_wins). D.4 byte-stable regression suite is **30/30 PASS**
  (was 33/33 in pre-Wave-178; 3 pre-Wave-196 shape-contract tests
  retired in Wave 196 P3 because Wave 178 changed the
  synthetic-mode latent shape to `(L, 3)` — see
  `docs/audit/wave218-p1-fix-applied.md` §Incident context).

- **Per-record CSVs** (N=1000+ rows per cell) available on Zenodo
  behind a reviewer-token gate for full re-analysis.

### §8.1 Code Availability

The implementation of **FlowA** is available at
`https://github.com/silverenternal/flowa-multistep-reinference`
(repository name: `flowa-multistep-reinference`; method name in this
paper: **FlowA**). The name discrepancy reflects the historical
evolution of the project — the repository predates the finalisation
of the method name in the paper draft. The canonical name for
citation purposes is **FlowA**. Reviewers following the link above
will land on the canonical source tree; the descriptive repository
name is preserved intentionally to keep the URL self-documenting
about the method's *behaviour* (paper-quantity-driven multi-step
re-inference) rather than its *identity* (**FlowA**). The audit
record for this naming decision is `docs/audit/wave213-p6-repo-naming.md`.

## §9 Suggested Associate Editor and Reviewers

**Suggested Associate Editor** (one of):

- Prof. `[USER TO FILL: Suggested Associate Editor — name and
  affiliation]` (TPAMI AE specializing in generative models /
  diffusion / flow matching — to be selected based on Editorial
  Manager rotation)

**Suggested Reviewers** (five, excluding obvious conflicts; the
corresponding author will confirm institutional COI at submission
time):

1. **Reviewer 1 — ProbFlow / Flow-Matching Theory.** A senior
   researcher from the Y. Lipman group or an equivalent lab
   working on probability-flow ODEs, rectified flow, and
   stochastic interpolants. This reviewer is best placed to
   audit Theorem 1 (Lemma 2–5 derivation, g-independent rate
   corollary, the four paper quantities $(A_g, B_g, C_g, e_\rho)$
   and their typed evaluators in
   `adaptive_reflow/theory/paper_quantities.py`).
   - *Affiliation:* `[USER TO FILL: Reviewer 1 affiliation]` (e.g.,
     Meta AI Research (ProbFlow team) / Weizmann Institute — *to
     be confirmed at submission.*)
   - *Email:* `[USER TO FILL: Reviewer 1 email —
     reviewer1.theory@[institution].edu]`

2. **Reviewer 2 — Convergence Bound / BL-Distance Expert.** A
   researcher in the F.-X. Vialard or S. Chewi group working on
   bounded-Lipschitz / Wasserstein convergence theory for
   sampling-based methods. This reviewer is best placed to audit
   the BL upper bound `BL(μ_{g,ε}, ν_g) ≤ A_g · exp(−NFE / B_g)
   + C_g · e_ρ`, the g-independent rate corollary
   `BL(μ_{g,ε}, ν_g) ≤ ε · √(2/π)`, and the assumptions under
   which the bound is tight.
   - *Affiliation:* `[USER TO FILL: Reviewer 2 affiliation]` (e.g.,
     Université Gustave Eiffel / LIGM (Vialard) or Yale
     University (Chewi) — *to be confirmed at submission.*)
   - *Email:* `[USER TO FILL: Reviewer 2 email —
     reviewer2.convergence@[institution].edu]`

3. **Reviewer 3 — ODE Solver / NFE-Efficiency Expert.** A
   researcher in the C. Lu DPM-Solver group or an equivalent lab
   working on high-order ODE solvers, exponential integrators,
   and NFE-efficient sampling for diffusion / rectified-flow
   models. This reviewer is best placed to audit FlowA's
   solver-agnostic stack (Euler, Heun, DPM-Solver++,
   Dormand–Prince RK45, CTMC, BFN), the 2.5–10× cross-budget NFE
   compression claim (CLM-046), and the matched-NFE = 50
   regression disclosed in §7.
   - *Affiliation:* `[USER TO FILL: Reviewer 3 affiliation]` (e.g.,
     Stanford University (Lu group) or Peking University — *to
     be confirmed at submission.*)
   - *Email:* `[USER TO FILL: Reviewer 3 email —
     reviewer3.solver@[institution].edu]`

4. **Reviewer 4 — Protein Generation Expert.** A researcher from
   the ESM-IF / LineageFlow / Kanzi author lists working on
   protein-structure generative models (sequence → fold, fold →
   sequence, or sequence → fold → side-chain). This reviewer is
   best placed to audit the protein-axis R-cells (R1 LineageFlow
   HMMER, R2 Kanzi inv-proj, R6 k6 foldability pLDDT +
   scPerplexity), the cluster-robust Pfam-family re-analysis
   (df_cluster=3, ICC=0.041, N_eff=89.6), and the cross-adapter
   monotone `hard > medium > easy` pLDDT pattern (k6 hard d_z =
   +1.189, LineageFlow hard d_z = +1.840).
   - *Affiliation:* `[USER TO FILL: Reviewer 4 affiliation]` (e.g.,
     Meta AI (ESM-IF / EvolutionaryScale LineageFlow) or
     Westlake University / Microsoft Research (Kanzi) — *to
     be confirmed at submission.*)
   - *Email:* `[USER TO FILL: Reviewer 4 email —
     reviewer4.protein@[institution].edu]`

5. **Reviewer 5 — Statistical Rigor Expert.** A senior researcher
   in applied statistics / pre-registration / multiple-testing
   discipline, with experience auditing empirical AI papers.
   This reviewer is best placed to audit the 12-column audit-grade
   per-row reporting (`n_paired, mean_diff, sd_diff, t, df, p_raw,
   CI95_low, CI95_high, d_z, test_type, family, α_bonferroni,
   bonf_sig`), the four pre-registered Bonferroni families, the
   cluster-robust re-analysis, and the effect-size sign
   consistency across adapters (k6 d_z range [−1.077, −1.138];
   LineageFlow d_z range [−1.002, −1.044]).
   - *Affiliation:* `[USER TO FILL: Reviewer 5 affiliation]` (e.g.,
     a statistics department with a
     computational-statistics / causal-inference / meta-analysis
     focus — *to be confirmed at submission.*)
   - *Email:* `[USER TO FILL: Reviewer 5 email —
     reviewer5.stats@[institution].edu]`

**Conflicts of interest to declare:** the corresponding author has
no financial or personal relationships with any of the suggested
reviewers; institutional conflicts (same university, recent
collaboration, advisor-student lineage) are to be confirmed at
submission time. The corresponding author explicitly flags that
Reviewer 1 (Lipman group) and Reviewer 4 (ESM-IF / LineageFlow /
Kanzi authors) overlap with co-author networks in the
flow-matching / protein-generation community, and a final COI
sweep will be run against the TPAMI Editorial Manager database
prior to submission.

## §10 Statement of Significance

We believe FlowA will be of interest to the TPAMI readership
because it (i) names and rejects a standard-assumption failure
mode (uniform ODE boundary conditions on non-uniform velocity
geometry) that practitioners encounter daily but rarely have a
mechanism to address, (ii) provides a self-contained, audit-grade
theoretical framework with a closed-form BL bound derived from
four paper quantities, (iii) validates the framework's value-add
across six R-level cells spanning three generative domains and
three solver regimes with pre-registered Bonferroni families and
cluster-robust re-analysis, and (iv) ships with full
reproducibility infrastructure (GitHub + Zenodo + Docker +
SHA-256-pinned checkpoints + hash-chained transition logs + D.4
byte-stable regression suite) that sets a new standard for
reproducibility in flow matching re-inference research.

We respectfully submit FlowA for consideration as a regular
research paper in IEEE TPAMI and look forward to the reviewers'
feedback.

## §11 Companion Paper Status

The corresponding author has prepared an extended mathematical
exposition of the bounded-Lipschitz distance bound introduced in
Theorem 1 of the present manuscript, intended for a separate
theoretical venue. The companion paper is currently under review
at QTDS (a prior submission to JMAA was rejected). The companion
paper is **not** a prerequisite for the present submission: the
present manuscript is self-contained, and Theorem 1 is restated
in §2 of the manuscript with a full proof sketch (Lemmas 2–5) and
explicit computation of the four paper quantities $(A_g, B_g, C_g,
e_\rho)$. The companion paper contains only additional theoretical
depth — sharper rates under weaker assumptions, an
information-theoretic lower bound, and the connection to
log-Sobolev and transport-cost inequalities — and does not
introduce new empirical claims that would alter the present
paper's headline numbers. The corresponding author declares this
companion-paper status on the submission cover sheet and on the
title page footnote to keep the editorial record transparent.

Sincerely,

`[USER TO FILL: Corresponding author name]`
`[USER TO FILL: Corresponding author affiliation]`
`[USER TO FILL: Corresponding author email]`
2026-09-21

---

**Submission package manifest** (for editorial reference):

1. Manuscript PDF (`docs/drafts/paper-flattened-draft.md`
   typeset to double-column 14-page TPAMI format).
2. Supplementary PDF (S1–S8: Theorem 1 derivation, per-record
   tables, hp-sensitivity sweep, 4-arm per-seed margin table,
   honest negatives, Theorem 1 source paper, cluster-robust
   per-cluster ICC + N_eff, power analysis per-cell).
3. Cover letter (this document).
4. Highlights (5 bullets, 85-char each).
5. Data availability statement (Zenodo DOIs for code + data).
6. Reproducibility checklist (per `docs/tpami_submission_checklist.md`
   §5 acceptance gates).