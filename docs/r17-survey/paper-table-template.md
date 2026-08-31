# Paper Section 4 (Experiments): Comparison Table Template

> **Status: TEMPLATE. No numbers below are paper-comparable yet.** Every
> cell in §1 is a `--` placeholder awaiting a real harness run. The
> companion docs `mol-comparison.md`, `img-comparison.md`, and
> `prot-comparison.md` track per-modality run state; once each harness
> lands real numbers, this template is populated row-by-row and lifted
> into the paper PDF.
>
> **Scope of this document.** Define the columns the paper will report,
> enumerate the placeholder rows per modality, lock the
> statistical-significance protocol (paired t-test + bootstrap CI +
> Cohen d + per-model alpha), and enumerate the failure modes that would
> falsify the headline claim. This is a *survey-only* artefact: the
> parallel harness-impl workflow owns the row values when they land.
>
> **Companion documents.**
> - `docs/r17-survey/mol-comparison.md` -- FlowMol3 / GraphBFN per-arm rows.
> - `docs/r17-survey/img-comparison.md` -- HiDream-I1-Dev / Lumina-Image 2.0 per-arm rows.
> - `docs/r17-survey/prot-comparison.md` -- ProtBFN / AbBFN per-arm rows.
> - `docs/r17-survey/image-eval-plan.md` -- FID / CLIPScore / GenEval / DPG-Bench eval-layer reference.
> - `docs/r17-survey/data-weights-inventory.md` -- on-disk weight reality for every model.
>
> **Modality coverage.** Five models: FlowMol3, Lumina-Image 2.0,
> HiDream-I1-Dev, ProtBFN, AbBFN. GraphBFN is excluded from this paper
> table (weights unavailable; see `mol-comparison.md` §3 honest caveat).

---

## 1. Comparison table

**Schema (one row per `model x variant x metric` triple).** Columns:

| Column | Meaning |
|---|---|
| **Model** | Adapter name (matches `adaptive_reflow/adapters/`). |
| **Variant** | Config id (`dev`, `full`, `unconditional`, `geom`, `qm9`, `cath-s40`, `oas-vh`, ...). |
| **Baseline metric** | Metric value under fixed-NFE baseline (matched compute, no re-inference scheduler). Mean over seeds; see §2 for CI/Cohen d. |
| **Framework metric** | Metric value under FlowA re-inference scheduler at the same wall-clock budget. |
| **Paired delta** | `framework - baseline`, sign reversed for `lower-is-better` metrics (FID, SA, FCD, freq_l1) so a positive value always = framework wins. |
| **p-value (paired t-test)** | Two-sided paired t-test on the per-seed metric vector; see §2.4 for the per-model alpha. |
| **n_samples** | Number of samples drawn per seed (`--n-mols`, `--n-samples`, `--n-prompts`). |
| **wall_clock** | Per-arm wall-clock in seconds (single seed, single device). |
| **NFE** | Baseline NFE | framework per-round NFE x n_rounds; total NFE held constant within `(model, variant)` (matched compute). |
| **Notes** | Free text: which paper Table the row cross-references, which eval split, caveats, dependency blockers. |

> **Matched-compute rule.** Within each `(model, variant)` block, baseline
> NFE and framework NFE are equal in aggregate. E.g. baseline `250 NFE`
> vs framework `2 x 125 NFE` or `3 x 83 NFE` -- never a free-NFE
> comparison. This is enforced at the harness layer
> (`tools/run_sota_*_experiment.py`); see §2 for the alpha rule that
> governs any reported NFE reduction.

### 1.1 Molecular rows (FlowMol3, 3D small-molecule flow matching, GEOM-DRUGS)

| Model | Variant | Baseline metric | Framework metric | Paired delta | p-value (paired t-test) | n_samples | wall_clock | NFE | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| FlowMol3 | geom / ctmc / unconditional | -- | -- | -- | -- | 1000 | -- | 250 = 2 x 125 | validity; higher is better. RDKit sanitization; ref: paper §5 / Table. |
| FlowMol3 | geom / ctmc / unconditional | -- | -- | -- | -- | 1000 | -- | 250 = 2 x 125 | QED (Bickerton 2012); higher is better. Computed per valid mol. |
| FlowMol3 | geom / ctmc / unconditional | -- | -- | -- | -- | 1000 | -- | 250 = 2 x 125 | SA score (Ertl & Schuffenhauer 2009); lower is better. |
| FlowMol3 | geom / ctmc / unconditional | -- | -- | -- | -- | 1000 | -- | 250 = 2 x 125 | logP (penalised); neutral/raw. Paper Table reports range; sign-reverse before claiming "wins". |
| FlowMol3 | geom / ctmc / unconditional | -- | -- | -- | -- | 1000 | -- | 250 = 2 x 125 | FCD (Preuer 2018); lower is better. Requires `fcd` package + GEOM-DRUGS reference `.npz` (see `mol-comparison.md` §3). |

### 1.2 Image rows (HiDream-I1-Dev + Lumina-Image 2.0)

#### 1.2.a HiDream-I1-Dev (17B MoE distilled, 28 NFE canonical)

| Model | Variant | Baseline metric | Framework metric | Paired delta | p-value (paired t-test) | n_samples | wall_clock | NFE | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| HiDream-I1-Dev | dev / 28-NFE distill | -- | -- | -- | -- | 8 (smoke) / 30000 (FID split) | -- | 28 = 2 x 14 | FID (MS-COCO-30K); lower is better. InceptionV3 pool3; ref stats path: `data/mscoco30k_inception_stats.npz`. |
| HiDream-I1-Dev | dev / 28-NFE distill | -- | -- | -- | -- | 8 (smoke) / 30000 (FID split) | -- | 28 = 2 x 14 | CLIPScore (Hessel 2021, 100x cosine); higher is better. CLIP-ViT-B/32 vs prompt set; ref: `image-eval-plan.md` §1 caveat. |

#### 1.2.b Lumina-Image 2.0 (Gemma2 + flow-matching, ~52.65 GB)

| Model | Variant | Baseline metric | Framework metric | Paired delta | p-value (paired t-test) | n_samples | wall_clock | NFE | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| Lumina-Image 2.0 | full / CFG 4.0 / 50 steps | -- | -- | -- | -- | 8 (smoke) / 30000 (FID split) | -- | 50 = 2 x 25 | FID (MS-COCO-30K or MJHQ-30K partition); lower is better. Pick one and freeze for the paper Table. |
| Lumina-Image 2.0 | full / CFG 4.0 / 50 steps | -- | -- | -- | -- | 8 (smoke) / 30000 (FID split) | -- | 50 = 2 x 25 | CLIPScore; higher is better. Caveat: paper CLIP-T uses paper-specific prompt subset; reconcile prompt source before quoting both side-by-side. |

### 1.3 Protein rows (ProtBFN + AbBFN)

#### 1.3.a ProtBFN (650M, unconditional protein-sequence BFN)

| Model | Variant | Baseline metric | Framework metric | Paired delta | p-value (paired t-test) | n_samples | wall_clock | NFE | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| ProtBFN | unconditional / cath-s40 | -- | -- | -- | -- | 1000 | -- | 100 = 2 x 50 | perplexity (perplexity under autoregressive teacher or BFN-native `log p(x)` estimator); lower is better. |
| ProtBFN | unconditional / cath-s40 | -- | -- | -- | -- | 1000 | -- | 100 = 2 x 50 | novelty (mean pairwise % identity to CATH-S40 training split); higher is better. |
| ProtBFN | unconditional / cath-s40 | -- | -- | -- | -- | 1000 | -- | 100 = 2 x 50 | TM-score (Zhang 2004, ESMFold-folded structure vs nearest CATH-S40 reference); higher is better. Optional if ESMFold venv unavailable. |

#### 1.3.b AbBFN (ProtBFN fine-tuned on antibody VH chains)

| Model | Variant | Baseline metric | Framework metric | Paired delta | p-value (paired t-test) | n_samples | wall_clock | NFE | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| AbBFN | antibody-vh / oas | -- | -- | -- | -- | 1000 | -- | 100 = 2 x 50 | perplexity; lower is better. Same metric def as ProtBFN row. |
| AbBFN | antibody-vh / oas | -- | -- | -- | -- | 1000 | -- | 100 = 2 x 50 | novelty (mean pairwise % identity to OAS VH training split); higher is better. Different reference set than ProtBFN -- do NOT pool. |
| AbBFN | antibody-vh / oas | -- | -- | -- | -- | 1000 | -- | 100 = 2 x 50 | TM-score (ESMFold vs nearest OAS VH reference); higher is better. |

> **Row count audit.** §1.1 = 5 placeholder rows, §1.2.a = 2,
> §1.2.b = 2, §1.3.a = 3, §1.3.b = 3 -- **15 placeholder rows total**.
> Each becomes one final paper row after the harness lands real numbers.

---

## 2. Statistical-significance protocol

This subsection is normative: any row in §1 that ships in the paper PDF
*must* satisfy these constraints. The paper's headline claim (FlowA's
re-inference scheduler matches or beats a fixed-NFE baseline at matched
compute) only survives review if every cell carries the CI/Cohen d/alpha
sign-off described here.

### 2.1 Seed sweep

- **Minimum seed count: 5.** `--seed 0 1 2 3 4` minimum; 10 is the
  target (gives `df = 9` for the paired t-test, which is the threshold
  below which the t-distribution's tails thicken materially).
- Each seed produces one `baseline_metrics.json` and one
  `framework_metrics.json`. The harness writes per-seed JSON, then a
  separate `aggregate.py` step collapses the seed sweep into the
  `summary.json` consumed by this table.
- Seed-draw semantics: identical `(seed, prompt_set, weight_backend)`
  triple across baseline and framework arms. **No reuse of pre-computed
  baseline outputs across seeds** -- each seed is a fresh draw.

### 2.2 Bootstrap 95% confidence intervals

- **Method:** non-parametric percentile bootstrap, 10 000 resamples,
  resampling at the per-sample level (one resample = one synthetic seed
  draw from the 5+ per-sample vectors).
- **Reported quantity:** `(mean_delta, ci_low, ci_high)` where
  `ci_low` / `ci_high` are the 2.5 / 97.5 percentile of the bootstrap
  distribution of `framework - baseline` (already sign-reversed for
  `lower-is-better` metrics).
- **Decision rule:** if `ci_low > 0` the framework wins with 95%
  confidence; if `ci_high < 0` it loses; otherwise the row is
  *inconclusive* and the paper must NOT claim a win.
- **Implementation:** `numpy.random.Generator(bit_generator="pcg64")`
  with `seed = base_seed` for reproducibility across reruns. The
  harness must pin the seed -- bootstrap CIs that drift across reruns
  are not publishable.

### 2.3 Effect size (Cohen d)

- **Definition:** `d = mean_delta / sd_delta` where `mean_delta` and
  `sd_delta` are computed on the paired-delta vector (5+ entries).
- **Interpretation thresholds (Cohen 1988):** `|d| < 0.2` negligible,
  `0.2 <= |d| < 0.5` small, `0.5 <= |d| < 0.8` medium, `|d| >= 0.8`
  large.
- **Reporting rule:** every row in §1 carries a `Cohen d` cell in the
  supplementary table (not in the main paper Table for space; the main
  Table carries the sign + CI). Rows with `|d| < 0.2` MUST be footnoted
  as "negligible effect size" even if p < alpha.

### 2.4 Per-model alpha (significance threshold)

- **Default alpha = 0.01.** Stricter than the conventional 0.05 because
  the paper compares five models x multiple metrics (a
  multiple-comparisons burden); Bonferroni across 15 rows would force
  `alpha = 0.05 / 15 ~ 0.003`, but we hold at `0.01` because the seed
  sweep + bootstrap CI + Cohen d are already a multi-pronged gate
  (alpha + effect-size + CI consistency; the p-value alone never settles
  a row).
- **Per-model adjustments.** If a particular model ships with fewer
  than 5 effective seeds (e.g. a 28-NFE HiDream-I1 run that runs out
  of GPU-hours), the per-row alpha relaxes to `0.05` and the row is
  footnoted "low seed count; alpha relaxed". The paper must be
  transparent about which rows used which alpha.
- **Pre-registration.** The seed list, alpha table, and CI seed MUST be
  recorded in `docs/r17-survey/protocol-lock.json` *before* the
  runbook executes. Post-hoc alpha tweaks are a paper-rejection trigger.

### 2.5 Combined reporting rule (the gate a row must pass)

A row in §1 is **publishable** iff **all** of the following hold:

1. `n_seeds >= 5` (or `>= 3` with the alpha-relaxation footnote).
2. `p_value < alpha` where `alpha` is the per-model threshold from §2.4.
3. The bootstrap 95% CI for `mean_delta` does not contain zero (in the
   `framework-wins` direction).
4. `|Cohen d| >= 0.2` (small effect size or larger).

A row that fails any of (1)-(4) is reported in the paper Table with a
`!` footnote and is NOT counted as a "framework wins" datum in the
abstract's headline count. The supplementary table carries the full
`(p, CI, d)` triple for transparency.

---

## 3. What would falsify the headline claim

The paper's headline claim is that **FlowA's re-inference scheduler
maintains (or improves) sample quality at matched compute, across
modality-diverse base models (3D molecules, T2I images, protein
sequences)**. The following failure modes would falsify -- or
materially weaken -- that claim. Each is anticipated, monitored for,
and footnoted in the paper if it triggers.

### 3.1 Framework regresses on at least one metric per modality

- **What it looks like:** FlowA *wins* on average FID / validity /
  perplexity but *loses* on diversity (novelty / CLIPScore / SA). A
  metric-by-metric split where the framework is Pareto-dominated by the
  baseline on at least one metric per modality.
- **Falsification trigger:** >= 1 metric per modality shows
  `framework < baseline` with `p < alpha` AND `|d| >= 0.2`. If this
  fires, the paper must caveat the headline claim as "average quality
  at the cost of diversity on modality X" -- not the clean monotonic-gain
  framing of the abstract.
- **Mitigation already in place:** the `Notes` column in §1 carries a
  `Direction` discipline (higher-is-better vs lower-is-better), and
  paired-delta sign-reversal is mandatory so a "win" always reads in the
  same direction.

### 3.2 Gains vanish under stricter alpha

- **What it looks like:** at `alpha = 0.05` five metrics per modality
  show `p < 0.05`, but at the per-model alpha of `0.01` (or the
  Bonferroni-corrected `0.003`) only one or two survive.
- **Falsification trigger:** the count of `p < alpha` rows drops by
  more than 50% when moving from `alpha = 0.05` to the locked
  `alpha = 0.01` per-model threshold. The paper must be transparent
  about which threshold each row used.
- **Mitigation:** §2.4 fixes `alpha = 0.01` *up-front*; alpha is not
  tuned after seeing the results.

### 3.3 Effect size is consistently negligible

- **What it looks like:** many rows show `p < alpha` but `|d| < 0.2`
  (statistically detectable, practically irrelevant).
- **Falsification trigger:** >= 50% of the §1 rows show `|d| < 0.2`
  *and* pass the §2.5 gate purely on `p < alpha`. This pattern would
  indicate that the framework's gains are real but tiny -- not a paper
  rejection by itself, but the abstract's framing must soften from
  "framework improves X" to "framework does not regress on X".
- **Mitigation:** §2.5 requires `|d| >= 0.2` alongside `p < alpha` for
  a "framework wins" call.

### 3.4 Wall-clock overhead erases the matched-compute assumption

- **What it looks like:** the scheduler wrapper adds Python overhead
  (orchestrator dispatch, adapter re-init per round, optional re-noising
  pass) such that `wall_clock(framework) > wall_clock(baseline)` even
  though `NFE(framework) == NFE(baseline)`. The matched-compute rule
  in §1 collapses if wall-clock is the binding constraint.
- **Falsification trigger:** per-arm wall-clock ratio
  `framework / baseline > 1.2` for any `(model, variant)` block. The
  paper must either (a) report the ratio and re-frame the claim as
  "matched NFE, not matched wall-clock", or (b) re-tune the framework
  to bring wall-clock back inside 1.2x.
- **Mitigation:** the harness `tools/run_sota_*_experiment.py` already
  writes per-arm wall-clock; the §1 template captures it in its own
  column so the ratio is auditable per row.

### 3.5 Sample-size collapse on a single modality

- **What it looks like:** molecule + protein arms finish with
  `n_samples = 1000` per seed as designed, but the HiDream-I1-Dev arm
  tops out at `n_samples = 300` because of GPU-hour budget. The
  paper-table imbalance would let a reader dismiss the image-arm gains
  as "could be a single-prompt artefact".
- **Falsification trigger:** any single modality ships with `n_samples
  < 100` per seed, or fewer than 3 seeds. The headline claim then has
  to be downgraded to "evidence is strongest on molecule + protein;
  image-arm findings are preliminary pending a full seed sweep".
- **Mitigation:** the seed sweep is pre-flight-checked against
  available GPU-hours before the runbook executes; if the image arm
  cannot hit `n_seeds = 5`, the paper defers the image row to
  supplementary.

### 3.6 Metric-dependence on missing packages (fcd, ESMFold, MiniCPM-V)

- **What it looks like:** the FCD row in §1.1 stays `NaN` because the
  `fcd` Python package is unavailable in the framework venv; the
  TM-score row in §1.3 stays `NaN` because ESMFold is in an isolated
  venv and not wired into the harness; the DPG-Bench row stays at the
  `external` stub marker because MiniCPM-V 2.6 is not self-hosted.
- **Falsification trigger:** any row ships as `NaN` or `--` in the
  paper Table. The reader cannot verify the claim; the paper must
  either (a) install the dependency and re-run, or (b) explicitly
  remove the row and footnote "metric unavailable in this revision;
  see supplementary for the synthetic-weights smoke row".
- **Mitigation:** dependency installs (`uv pip install fcd`,
  ESMFold venv wiring, MiniCPM-V 2.6 self-host) are tracked as
  pre-flight boxes in `image-eval-plan.md` §3 and `mol-comparison.md`
  §1.1.b caveat. The `Notes` column in §1 is the visible record of
  which dependency gates each row.

### 3.7 Scheduler-specific pathology (re-noising destroys mode coverage)

- **What it looks like:** the framework arm concentrates probability
  mass on a small set of high-reward modes (the re-inference scheduler
  pushes samples toward regions the reward / verifier model scores
  highly). Validity / QED / novelty / CLIPScore all go *up*, but the
  generated set collapses onto a few exemplars (effective uniqueness
  drops).
- **Falsification trigger:** paired `uniqueness` or `intra-set
  Tanimoto` falls below baseline with `p < alpha` for >= 1 metric per
  modality. The paper must caveat "quality gains come with diversity
  loss" rather than the clean monotonic-gain framing.
- **Mitigation:** the §1 template forces one diversity-style metric per
  modality (FID, novelty, CLIPScore) and the harness writes the full
  per-sample set, not just the mean -- a collapse is visible in the
  per-sample distribution even if the mean holds.

---

## 4. Open questions to resolve before population

These items are not failure modes per se, but they must be settled
before the §1 cells can be lifted into the paper PDF:

1. **FID split for HiDream-I1-Dev.** HiDream-I1 paper does not report
   FID (favours human-preference metrics). Pick MS-COCO-30K or GenEval
   partition; document choice in the supplementary. See
   `image-eval-plan.md` §2.
2. **Prompt-set reconciliation for Lumina CLIPScore.** The paper's
   CLIP-T row uses a paper-specific prompt subset not reproduced
   verbatim in appendix. Reconcile prompt sources before quoting both
   side-by-side (per `image-eval-plan.md` §2 Lumina row).
3. **FCD reference statistics.** The GEOM-DRUGS reference `.npz` for
   the `fcd` package is not bundled with `data/flowmol3/`. Decide
   between (a) generating reference stats in-harness from a held-out
   split, or (b) downloading a published reference set.
4. **TM-score for proteins.** ESMFold is heavy (~3 GB params, ~5
   s/sequence on CPU). Either install in an isolated venv and amortise
   across seeds, or drop TM-score from §1.3 and footnote "structure
   metric deferred".
5. **GenEval / DPG-Bench rows.** The current eval layer marks these as
   `external` stubs. Either self-host MiniCPM-V 2.6 / `geva` (Tier 2)
   or pay for GPT-4V judging (Tier 1). The paper can ship without
   these rows (FID + CLIPScore suffice for the headline claim) but the
   supplementary Table would be stronger with them.

---

## 5. Repro contract (when the harness lands)

When the §1 cells are populated, the paper PDF's Table 4 (or wherever
Section 4 lands the comparison) is regenerated from this template by:

1. Each per-modality harness (`tools/run_sota_*_experiment.py`) writes
   its own `comparison.md` with real numbers; the survey-level docs
   (`mol-comparison.md`, `img-comparison.md`, `prot-comparison.md`)
   consolidate those per-arm tables.
2. The §1 template is filled by reading each `summary.json` and pulling
   the `(baseline, framework, paired_delta, p_value, n_samples,
   wall_clock, NFE, notes)` block per `(model, variant, metric)`
   triple.
3. The §2 statistical-significance gate is run per row; rows that fail
   §2.5 are footnoted with `!` and excluded from the abstract's
   headline count.
4. The §3 falsification checklist is ticked; any triggered failure mode
   is added to the paper's "Limitations" subsection with the matching
   data.

The template, protocol, and falsification list are locked at this
revision; the only thing that changes as the harness lands is the cell
values in §1.