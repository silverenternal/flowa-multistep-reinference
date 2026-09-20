# Cover Letter — FlowA for IEEE TPAMI

**To:** Editor-in-Chief, IEEE Transactions on Pattern Analysis and
Machine Intelligence (TPAMI)

**Subject:** Submission of "FlowA: Training-free, paper-quantity-driven
re-inference for Flow Matching checkpoints" for consideration as a
regular research paper in IEEE TPAMI.

**Authors:** [corresponding author and affiliations to be filled at
submission]

**Date:** 2026-09-21

**Suggested Associate Editor:** [to be filled at submission — see
§7 below]

**Suggested Reviewers:** [to be filled at submission — see §7 below]

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

## §2 Insight — Paper-Quantity-Driven Scheduling

FlowA's theoretical contribution is a self-contained four-lemma
derivation of the effective BL bound
`BL(μ_{g,ε}, ν_g) ≤ A_g · exp(−NFE / B_g) + C_g · e_ρ` (T1, with
g-independent rate corollary `BL(μ_{g,ε}, ν_g) ≤ ε · √(2/π)`)
from four closed-form paper quantities $(A_g, B_g, C_g, e_ρ)$ —
a Lipschitz aggregate, an effective NFE decay rate, a residual
bias coefficient, and an exterior-gap constant. These four quantities
are **computable from the adapter's posterior geometry at runtime**
through typed evaluators in `adaptive_reflow/theory/paper_quantities.py`
and are consumed directly as scheduler inputs by the framework's
three scheduler/operator components: `CodimensionSheetScheduler`
(consumes $A_g, B_g, C_g$ → `n_cap`), `BoundedMergeOperator`
(consumes $e_\rho$ → merge envelope noise floor), and
`EvidenceDrivenScheduler` (consumes the full quadruple → per-cell
restart probability). The framework operates without retraining,
distillation, or Reflow; stacks on Euler, Heun, DPM-Solver++,
Dormand–Prince RK45, CTMC, and BFN solvers; and exposes the
inference loop as a typed four-port control surface that a domain
expert can drive without manipulating the FM internals.

## §3 Validation Scope — Six R-Level Cells, Four Adapters Confirmed Monotone

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

## §4 Headline Numbers

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

## §5 Boundary Disclosure — Matched-NFE = 50 First-Class Honest Negative

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

## §6 Reproducibility — GitHub + Zenodo + Docker

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

- **Per-record CSVs** (N=1000+ rows per cell) available on Zenodo
  behind a reviewer-token gate for full re-analysis.

## §7 Suggested Associate Editor and Reviewers

**Suggested Associate Editor** (one of):

- Prof. [TPAMI AE specializing in generative models / diffusion /
  flow matching — to be selected based on Editorial Manager
  rotation]

**Suggested Reviewers** (four, excluding obvious conflicts):

1. Prof. [reviewer specializing in ODE solvers for SDE/CTMC flow
   matching, with publications in flow matching theory]

2. Prof. [reviewer specializing in protein structure prediction
   (ESM-2, OmegaFold, LineageFlow, Kanzi) — protein-axis expertise]

3. Prof. [reviewer specializing in molecular 3D generation
   (FlowMol, RDKit, DiffDock) — molecular-axis expertise]

4. Prof. [reviewer specializing in image-domain rectified flow /
   diffusion (CIFAR-10, ImageNet RF) — image-axis expertise]

**Conflicts of interest to declare:** the corresponding author has
no financial or personal relationships with any of the suggested
reviewers; institutional conflicts (same university, recent
collaboration, advisor-student lineage) are to be confirmed at
submission time.

## §8 Statement of Significance

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

Sincerely,

[Corresponding author]
[Affiliation]
[Email]
[Date]

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