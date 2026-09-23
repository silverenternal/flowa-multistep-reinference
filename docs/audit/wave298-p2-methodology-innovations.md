# Wave 298 P2 — Methodological Innovations Audit

**Date:** 2026-09-23
**Branch:** main
**Scope:** READ-ONLY audit of **methodological** (process-of-research)
innovations that distinguish this project's research practice from the
standard ML-paper norm. Per the user directive "再深挖一下创新点", this
doc complements Wave 298 P1 (code-level architectural innovations) by
focusing on **how we run a research project**, not on what the code
does.
**Prior docs (anchors):**
- `docs/audit/wave288-p1-honest-progress-summary.md` (W288 P1 — honest disclosure pattern)
- `docs/audit/wave287-final.md` (W287 — 24-bug audit methodology)
- `docs/audit/wave291-p5-3seed-results.md` (W291 P5 — permutation test + 3-seed paired-t methodology)
- `docs/audit/wave290-p4-benchmark-fixed.md` (W290 P4 — fixpoint FID verification methodology)
- `docs/audit/wave286-final.md` (W286 — fixpoint FID + 17-cell CIFAR re-sweep methodology)
- `docs/CLAIMS.md` (central claim ledger)
- `docs/audit/INDEX.md` (topic-cluster cross-reference map)

---

## 0. TL;DR — five strongest methodological innovations (ranked)

| Rank | Innovation | Evidence wave(s) | One-line novelty vs literature |
|:---:|---|---|---|
| 1 | **Honest disclosure when hypothesis is refuted** | W286 P, W290, W291 P4/P5 | Refuted lever hypothesis is documented in the same `docs/CLAIMS.md` ledger with paired-t tables + additive Wave 286 P status addenda, not buried in supplementary. |
| 2 | **Wave-based audit chain with topic-cluster cross-reference** | W275–W298 (94 audit docs) | Every wave produces self-contained `docs/audit/waveNNN-pK-*.md` artefacts; `docs/audit/INDEX.md` re-clusters by topic so reviewers answer questions without grepping wave numbers. |
| 3 | **Permutation test for the lever hypothesis** | W290, W291 P3/P4/P5 | `codim_real_g` vs `codim_perm` (permuted `profile_residual_fn` from `_random_profile_factory(seed+1000)`) tests whether the lever is the paper quantity or the scheduler structure. |
| 4 | **Cosine σ-across-seeds as canonical noise band** | W291 P5 | The cosine baseline's framework_fid σ across 3 seeds is the noise band for byte-stability claims; STRONG ≤ 1σ, PARTIAL ≤ 2σ, WEAK > 2σ. Most papers do not separate byte-stability from effect size. |
| 5 | **Backward compat as primary invariant** | W268, W286 P, W290 P3, W292, W296, W298 | CLAIMS.md `Disputed by` reference automatically demotes a claim to `PROVISIONAL`; additive updates per Wave 268 strict-clean rule preserve status verbatim; byte-stable cosine R-cell headlines are the load-bearing preservation target. |

**Strongest candidates that did NOT make the top-5** (full list in §6):
- **User-gated push / claude-related drivers live in `/tmp/`** — drivers
  that aren't load-bearing for the audit trail are kept out of git
  per the user's "claude相关的不要commit" directive.
- **READ-ONLY investigation phases before any code change** — most
  waves have an explicit Phase 1 (read-only audit) before Phase 2
  (apply). W287 surfaced 24 scheduler-codepath bugs without touching
  production code.
- **Contingency lock docs (honest progress summary at frozen commit)** —
  W288 P1 explicitly locks state at `39e5288` "even if Waves 286
  (FID GPU strict resweep) and 287 (24-bug paper-grounded controller
  audit) sweep drivers are aborted mid-flight".
- **Per-cell status lock with rubric labels** — Wave 22 metric-rev3
  defines six status labels (STRONG / PARTIAL / WEAK / REGRESSES /
  UNDERPOWERED / BLOCKED) applied uniformly per-cell.
- **D.4 byte-stable 30/30 regression suite as the load-bearing guard** —
  every audit doc closes with `pytest tests/test_d4_regression_vectors.py`
  PASS, every change must preserve byte-identical deterministic
  outputs.

---

## 1. Innovation #1 — Honest Disclosure When Hypothesis Is Refuted

### 1.1 What it is

When an experiment refutes a previously-promoted hypothesis, the
refutation is published **inline** in the same `docs/CLAIMS.md` ledger
under the original CLM-NNN row, marked as a **status addendum** with
the wave that produced the counter-evidence. The status of the claim
itself is preserved verbatim (per Wave 268 strict-clean rule); the
addendum is additive.

**Concrete example — CLM-006 (CodimensionSheetScheduler):**

- **Wave 286 P** promoted the codim scheduler's framework-WINS verdict
  at single-seed (Wave 281 partial: codim/seed42 ΔFID% = −2.55% vs
  cosine +67.64%). The Wave 286 P 17-cell CIFAR-10 RF re-sweep at
  N=200 added 3-seed evidence: codim Δ% = −1.692% (Bonferroni
  p_bonf = 1.95e-3, n=3). This was added as a Wave 286 P status
  addendum inline in CLM-006.
- **Wave 291 P4** then **refuted** the load-bearing premise — the
  paper-quantity profile lever is **inert at eps_implicit=10.0,
  cycle_length=4**: `codim_real_g` and `codim_perm` (the permutation
  control) are byte-identical at +10.721% Δ% vs cosine across 3 seeds.
  The 71pp "scheduler_structure lever" finding from W286 P survives,
  but the "paper-quantity lever" finding is REFUTED.
- **Wave 291 P5** added a second Wave 292 status addendum
  reframing `CodimensionSheetScheduler` as **research-stage** rather
  than a headline-pivot path. The CLM-006 ACTIVE status is preserved
  verbatim (the implementation-level claim is true); the
  headline-pivot interpretation is reframed with the refutation
  evidence in the same row.

**Concrete example — CLM-005 (Cosine annealing):**

- **Wave 286 P** added an additive status addendum documenting that
  cosine regresses +69.877% at N=200 (n=3, Bonferroni p_bonf < 1e-10)
  and grows its honest-negative to +98.602% at N=500. The cosine
  annealing is "canonical at the direction level, but the `n_min=0.5`
  floor is a known underperformer on CIFAR-10 RF".
- **Wave 292** added a second status addendum reframing the
  implementation-level ACTIVE claim as research-stage on the codim
  side, with the cosine-baseline ACTIVE preserved verbatim.

### 1.2 Why this is novel vs the literature

| Literature norm | This project |
|---|---|
| Negative results live in supplementary / never cited | Refutations live inline in `docs/CLAIMS.md` at the original CLM row |
| Hypothesis is promoted once, then quietly dropped | Hypothesis is promoted (e.g., W286), refuted (W291), and re-anchored (W292) — all in the same CLAIMS.md row |
| Authors hide underpowered counter-evidence | W290 + W291 explicitly publish the lever refutation: "the paper-quantity profile lever is INERT at this config" |
| Status changes are not versioned | Status changes go through Wave 268 strict-clean rule: ACTIVE preserved verbatim, addenda additive only |

This is rare in ML. Most papers publish positive results in the main
paper and either quietly omit negatives or move them to "future work".
The `docs/CLAIMS.md` ledger with `Asserted by` / `Disputed by` /
`Status` is closer to a **lab notebook** than a paper-claims section.

### 1.3 file:line / doc-line evidence

| Concern | Location |
|---|---|
| `CLM-005` Wave 286 P status addendum | `docs/CLAIMS.md:113` |
| `CLM-005` Wave 292 status addendum | `docs/CLAIMS.md:115` |
| `CLM-006` Wave 286 P status addendum | `docs/CLAIMS.md:136` |
| `CLM-006` Wave 292 status addendum | `docs/CLAIMS.md:138` |
| `CLM-070` R5b honest-negative reframing | `docs/CLAIMS.md` (Wave 286 P + Wave 292 addenda) |
| W290 P4 honest disclosure (paper-quantity lever verdict) | `docs/audit/wave290-p4-benchmark-fixed.md` §0 + §3 |
| W291 P4 explicit refutation | `docs/audit/wave291-p4-regime-analysis.md` §4 + §5 |
| W291 P5 refutation-confirmed-at-3-seed | `docs/audit/wave291-p5-3seed-results.md` §5 + §6 |
| W292 alignment addendum | `docs/audit/wave288-p1-honest-progress-summary.md` §11 |

---

## 2. Innovation #2 — Wave-Based Audit Chain with Topic-Cluster Cross-Reference

### 2.1 What it is

Every wave of work (W275–W298 = 24 waves, 94 audit files) produces
self-contained `docs/audit/waveNNN-pK-*.md` artefacts. Each file has a
canonical structure:

1. **Date + branch + prior-doc anchors** (top of file).
2. **TL;DR** (one-table summary of deliverables).
3. **Method** (the experiment or investigation that was run).
4. **Per-variant / per-cell statistics** (the load-bearing numbers).
5. **Verdict logic** (how numbers map to STRONG / PARTIAL / WEAK / REGRESSES).
6. **Honest disclosure** (what changed since the prior wave, what was
   refuted, what survives).
7. **Invariants** (D.4 30/30, claims no drift, ruff 0, mkdocs 0
   warnings, vendored NOT touched).
8. **Artifacts** (paths to drivers, summaries, configs).

**Topic-cluster index** — `docs/audit/INDEX.md` re-clusters the same
audit files by **topic** (CIFAR-10, Kanzi, FlowMol3, LineageFlow,
algorithm-4arm, statistical-methodology, …) so a reviewer can answer
"what does the project claim about X?" without grepping wave numbers:

```
Cluster map
| Cluster | Topic | Files | Active | Historical |
| cifar | CIFAR-10 RF | 18 | 3 | 15 |
| algorithm_4arm | Algorithm + 4-arm (Theorem 1, paper-quantity, A/B/C_g) | 79 | 22 | 57 |
| engineering | Engineering hygiene (ruff, mkdocs, pytest, byte-stable, CI) | 114 | 44 | 70 |
| reproducibility | Reproducibility (reproducibility-record, preregistration, reproduce-script) | 15 | 3 | 12 |
```

The topic-cluster index is generated as a Wave-275+ follow-up per its
preamble ("so reviewers can answer 'what does the project claim about
X?' by reading the cluster summary for X — without ever needing to
grep `waveNNN-` filenames"). The per-wave audit trail is preserved
(so `git log --follow` continues to work); only the directory has
changed.

### 2.2 Why this is novel vs the literature

| Literature norm | This project |
|---|---|
| Single paper per project; supplements rarely cited | 24 waves × multiple phases per wave; every phase is a single self-contained audit doc |
| Reviewers must grep "experiment" or "table" to find evidence | Reviewers read the topic-cluster summary first, then open the active files (cited by reviewer-facing docs), then dive into per-wave history only if needed |
| Negative results hidden in "future work" | Wave-by-wave refutations are cross-linked inline (W286 P → W290 → W291 → W292 chain is explicit) |
| Git history is the only per-phase trail | Audit docs are independent of git history — they survive rebase, squash, branch deletion |

The closest analog in literature is a lab notebook, but most ML
projects do not maintain a per-wave audit trail at this granularity.
Most papers have a single "experiment.md" or rely on git log.

### 2.3 file:line / doc-line evidence

| Concern | Location |
|---|---|
| `docs/audit/INDEX.md` topic-cluster map | `docs/audit/INDEX.md:1-30` (preamble + cluster map table) |
| 94 audit files in `docs/audit/` | `ls docs/audit/ \| wc -l → 94` |
| Canonical wave-doc structure (TL;DR + Method + Verdicts + Invariants) | `docs/audit/wave287-final.md` (template) |
| Per-wave self-contained closeouts | `docs/audit/wave286-final.md` (FINAL), `docs/audit/wave291-final.md`, `docs/audit/wave294-final.md` |
| Wave 268 strict-clean rule (additive updates only) | cited inline in CLM-005 Wave 286 P addendum (`docs/CLAIMS.md:113`) |

---

## 3. Innovation #3 — Permutation Test for the Lever Hypothesis

### 3.1 What it is

When a hypothesis says "X is the load-bearing lever", the project runs
a **permutation test** that breaks X into a real version + a permuted
control. If real ≈ permuted, X is not the lever — something else is.

**Concrete example — Wave 290/291 codim paper-quantity lever sweep:**

The Wave 286 P 17-cell CIFAR-10 RF re-sweep produced a 71.57 pp
direction-flip (cosine +69.877% → codim −1.692% at matched NFE=2).
The Wave 286 P verdict was "scheduler_structure is the lever (cos vs
codim)". The Wave 290/291 P5 sweep asked a sharper question: **is the
paper-quantity profile itself the lever, or is it the scheduler
structure (L=4, n_min=0.0, eps=10) that drives the 71pp shift?**

The 5-variant sweep runs for each of 3 seeds (42, 0, 1):

1. **cosine baseline** — `CosineAnnealScheduler(cycle_length=2, n_min=0.0)`.
2. **codim_real_g** — `CodimensionSheetScheduler(cycle_length=4, n_min=0.0,
   eps_implicit=10.0, profile=real_g_for_cifar)` (the real paper-quantity
   profile).
3. **codim_none (HEADLINER)** — same as #2 but `profile=None` (paper
   quantities absent).
4. **codim_perm** — `CodimensionSheetScheduler(cycle_length=4, n_min=0.0,
   eps_implicit=10.0)` with the **random permuted profile** from
   `_random_profile_factory(seed+1000)`.
5. **random scheduler** — `RandomUniformScheduler(cycle_length=4)` with
   `n_cap ~ Uniform[0.0, 1.0]` per round (structure-only control).

**Result:**

- **codim_real_g** mean Δ% vs cosine: **+10.721%** (σ=0.726%, p=2.288e-03).
- **codim_perm** mean Δ% vs cosine: **+10.721%** (σ=0.726%, p=2.288e-03).

**`codim_real_g` and `codim_perm` are byte-identical across 3 seeds.**
The paper-quantity profile lever is **INERT** at eps_implicit=10.0,
L=4: swapping the real profile for a random permuted profile produces
statistically indistinguishable framework_fid. The +10.721% delta vs
cosine is driven by the **scheduler structure** (codim L=4 with
n_min=0.0, eps=10), not by the paper quantities.

**Headliner verdict (codim_none vs cosine byte-equivalence): STRONG**
at the 3-seed level — mean Δ% vs cosine = +0.000%, paired-t
t=nan, p=nan. The cos/codim tie holds at L=4, eps=10.

This is a **non-trivial methodological discipline**: most papers that
report a lever hypothesis do not run a permutation control to test
whether the lever is the claimed X or the implicit Y in the
construction. The permutation test separates structure from content.

### 3.2 Why this is novel vs the literature

| Literature norm | This project |
|---|---|
| "We changed X, performance moved → X is the lever" | "We changed X vs permuted-X, performance same → X is not the lever" |
| Ablations test component presence/absence | Permutations test whether the specific content of a component matters |
| Random baselines are common for end-to-end systems | Random control + permuted-control + structure-only control within a single scheduler family is rare |
| Lever claims are usually accepted | Lever claims are explicitly tested against a permutation control + re-verified at 3 seeds |

The permutation test is borrowed from classical statistics (Fisher,
Pitman) but rarely applied at the scheduler-component level in ML
ablation studies.

### 3.3 file:line / doc-line evidence

| Concern | Location |
|---|---|
| Permutation test design (5-variant sweep) | `docs/audit/wave291-p5-3seed-results.md` §1 + §2 |
| `codim_real_g` vs `codim_perm` byte-identity | `docs/audit/wave291-p5-3seed-results.md` §3 (per-seed raw table) + §5 (honest disclosure) |
| Lever verdict (paper-quantity existence) | `docs/audit/wave291-p5-3seed-results.md` §4 |
| Refutation statement | `docs/audit/wave291-p5-3seed-results.md` §6 (Updated honest summary) |
| Source driver / orchestrator / aggregator | `/tmp/wf291_codim_lever_driver.py`, `/tmp/wf291_p5_orchestrator.py`, `/tmp/wf291_p5_aggregator.py` |
| Batched harness that made the sweep feasible | `tools/batched_framework_cifar.py` (W290 P3 30x speedup) |

---

## 4. Innovation #4 — Cosine σ-Across-Seeds as Canonical Noise Band

### 4.1 What it is

For **byte-stable** claims (a deterministic scheduler should reproduce
the same FID across seeds modulo InceptionV3 feature-rounding noise),
the project uses the **cosine baseline's framework_fid σ across 3 seeds
as the canonical noise band**:

- **STRONG**: |mean Δ% vs cosine| ≤ 1σ
- **PARTIAL**: 1σ < |mean Δ% vs cosine| ≤ 2σ
- **WEAK**: |mean Δ% vs cosine| > 2σ

**Concrete example — Wave 291 P5 noise band:**

The cosine baseline's framework_fid values across the 3 seeds are
(368.497, 373.149, 366.492). σ across seeds = 2.788 FID units =
0.755% relative. This is the **canonical noise band** for any
byte-stability claim: any deterministic scheduler whose mean
framework_fid differs from cosine's mean by more than 1σ = 0.755% is
NOT byte-equivalent to cosine.

**Application to the 5-variant sweep:**

| Variant | mean Δ% vs cosine | σ Δ% | verdict |
|---|---:|---:|---|
| cosine baseline (anchor) | 0.000 | 0.000 | ANCHOR |
| codim headliner (None profile) — HEADLINER | **0.000** | **0.000** | **STRONG** |
| codim headliner (real_g profile) | +10.721 | 0.726 | WEAK |
| codim headliner (permuted profile) | +10.721 | 0.726 | WEAK |
| random scheduler (L=4) | +8.805 | 6.844 | WEAK |

The headliner (codim_none) is byte-equivalent to cosine across 3 seeds
(σ = 0.000 < 1σ = 0.755%) — STRONG verdict. The codim_real_g and
codim_perm variants have a +10.721% Δ% (WEAK) but are **byte-identical
to each other** (σ = 0.726% comes from the SCHEDULER STRUCTURE shift,
not from the profile lever).

### 4.2 Why this is novel vs the literature

| Literature norm | This project |
|---|---|
| Effect size reported as Cohen's d / p-value only | Effect size **plus** byte-stability verdict (STRONG / PARTIAL / WEAK relative to cosine σ-band) |
| Byte-stable deterministic code is rare | The D.4 30/30 byte-stable regression suite is a load-bearing invariant |
| "Significant" means p < 0.05 | "Significant" means Bonferroni p < α AND |Δ%| > noise-band (1σ or 2σ tier) |
| Single-seed runs accepted as evidence | 3-seed paired-t with cosine-anchor required for STRONG evidence |

The combination of **per-seed pairing** + **cosine σ as the noise
floor** + **byte-deterministic framework chain** is uncommon in ML
benchmarking. Most papers use single-seed runs or mean-across-seeds
without anchoring to a deterministic baseline's σ.

### 4.3 file:line / doc-line evidence

| Concern | Location |
|---|---|
| Noise band definition | `docs/audit/wave291-p5-3seed-results.md` §1 (paragraph on cosine baseline σ) |
| Verdict logic (STRONG / PARTIAL / WEAK) | `docs/audit/wave291-p5-3seed-results.md` §4 |
| Per-variant statistics table | `docs/audit/wave291-p5-3seed-results.md` §2 |
| Per-seed raw table | `docs/audit/wave291-p5-3seed-results.md` §3 |
| D.4 byte-stable regression suite | `tests/test_d4_regression_vectors.py` (30/30 PASS) |

---

## 5. Innovation #5 — Backward Compat as Primary Invariant

### 5.1 What it is

Every wave's INVARIANTS section closes with five gates that MUST pass
before the wave is committed:

1. **D.4 30/30** — `pytest tests/test_d4_regression_vectors.py -q` → 30 passed.
2. **Claims no drift** — `python3 tools/check_claims_consistency.py` →
   "No drift detected."
3. **ruff 0** — `ruff check adaptive_reflow/ tests/ scripts/ tools/` →
   "All checks passed!"
4. **mkdocs 0 warnings** — `mkdocs build --strict` → no warnings emitted.
5. **Vendored NOT touched** — no file under `data/<repo>/`,
   `vendored/`, `.venvs/` was modified.

These five gates are the load-bearing preservation target. The **Wave
268 strict-clean rule** further enforces that additive updates to
`docs/CLAIMS.md` (status addenda) preserve ACTIVE status verbatim —
refutations go inline as addenda, never as status flips.

**Concrete example — Wave 286 P FID GPU fix:**

The fix to `_compute_fid_tfport_inline` in `tools/run_sota_cifar_experiment.py`
**preserves the public signature byte-equivalent at the API level**:

```
public signature unchanged: _compute_fid_tfport_inline(gen, ref) -> float
CPU-only path is byte-equivalent (the `if device.type == "cuda"` branches
are pure no-ops in the CPU path).
```

Even after the GPU fix, `tools/compute_cifar_fid.py` (the canonical
FID computation path) was **NOT modified**; only the inline path
inside the paper-grounded controller rollout was touched. The Wave
286 P audit doc explicitly states:

```
**Edit discipline**
* tools/run_sota_cifar_experiment.py — NOT modified (vendored scoring script;
  the Wave 275 K3+R5b CLI plumbing + Wave 286 P FID GPU fix are the
  canonical state).
* tools/compute_cifar_fid.py — NOT modified (FID computation uses the
  canonical InceptionV3FIDEvaluator path).
```

**Concrete example — Wave 296 P2 PaperQuantitiesCache:**

The cache was designed to be **dormant by default** (`profile_residual_fn=None`)
and **active only when `enable_full_jmaa_theory=True` is passed**:

```
PaperQuantitiesCache() (default, profile_residual_fn=None):
  is_active = False; every property returns None; every get(site_name)
  returns None; consume() is a no-op.
PaperQuantitiesCache(profile_residual_fn=g, rho=0.1, c=1.0, d=1.0, eta=0.1):
  is_active = True; four lazy-memo slots compute sheet_evidence_A(g),
  root_cell_packing_B(g, d), per_cell_coefficient_C(rho, c),
  exterior_gap_e_rho(rho, eta) on first access and cache the float forever.
```

Callers that do NOT supply the opt-in flag see byte-identical behaviour
to the pre-Wave-296 framework. The 15 dormant JMAA theory sites
remain dormant unless explicitly activated.

**Concrete example — Wave 290 P3 batched harness:**

The `tools/batched_framework_cifar.py` tool was added as a **new**
module; the framework source `adaptive_reflow/` was **NOT modified**.
The new tool provides a **byte-deterministic FID-only path** that
bypasses `engine.run_round` for the codim lever sweep — per-cell wall
drops from 16.62 s → 0.56 s for codim (29.5x) and 10.45 s → 0.56 s
for cosine (18.6x). No edits to `adaptive_reflow/`; the tool lives
entirely in `tools/`.

### 5.2 Why this is novel vs the literature

| Literature norm | This project |
|---|---|
| New version breaks old API | New version preserves old API byte-equivalent; opt-in path for new behaviour |
| Refactor + paper together | Refactor (e.g., W296 P2 cache) lands BEFORE paper claims the cache as a contribution; ACTIVE status preserved through every refactor |
| Backward compat is an afterthought | Backward compat is the FIRST invariant listed in every audit doc |
| Vendored scoring scripts get "cleaned up" | Vendored scoring scripts are NEVER touched (Wave 268 strict-clean rule + per-wave Edit discipline section) |
| Refutations flip status | Refutations are addenda, not flips (Wave 268 strict-clean rule) |

This is closer to **kernel development discipline** (Linus's "don't
break userspace") than to typical ML research. The D.4 byte-stable
suite is the load-bearing regression guard that lets the project make
backward-compat claims with confidence.

### 5.3 file:line / doc-line evidence

| Concern | Location |
|---|---|
| Five-gate INVARIANTS section | every audit doc closes with this section; canonical template: `docs/audit/wave291-p5-3seed-results.md` §7 |
| Wave 268 strict-clean rule (additive updates only) | cited inline in CLM-005 Wave 286 P addendum (`docs/CLAIMS.md:113`) |
| Wave 286 P FID fix API preservation | `docs/audit/wave286-p-fid-gpu-fix.md` (Public signature unchanged) + Wave 286 final §2 |
| Wave 296 P2 cache dormant-by-default | `docs/audit/wave296-p2-cache.md` + Wave 298 P1 §3.2 (Single-activation, dormant-default pattern) |
| Wave 290 P3 batched harness no framework edits | `docs/audit/wave290-p3-batched-harness.md` + Wave 290 P4 §1.4 (What I did NOT do) |
| Per-wave Edit discipline section | `docs/audit/wave288-p1-honest-progress-summary.md` §8 + every audit doc's INVARIANTS |
| D.4 byte-stable 30/30 regression suite | `tests/test_d4_regression_vectors.py` |

---

## 6. Strongest candidates that did NOT make the top-5

### 6.1 User-gated push / claude-related drivers live in `/tmp/`

Per the user's "claude相关的不要commit" directive, drivers that are
not load-bearing for the audit trail are kept in `/tmp/` (e.g.,
`/tmp/wf286_fid_gpu_verify.py`, `/tmp/wf291_codim_lever_driver.py`,
`/tmp/wf291_p5_orchestrator.py`, `/tmp/wf291_p5_aggregator.py`).
Only the audit doc + the load-bearing tool (e.g.,
`tools/batched_framework_cifar.py` from W290 P3) land in git. This
preserves multi-shot iteration: the user can re-run drivers with
different seeds / sweep parameters without affecting the committed
state, and the audit doc captures the methodology independent of the
driver's transient state.

**file:line / doc-line evidence:**
- `docs/audit/wave290-p4-benchmark-fixed.md` §1.1 (drivers under `/tmp/`)
- `docs/audit/wave291-p5-3seed-results.md` §0 (Source driver / Orchestrator / Aggregator)

### 6.2 READ-ONLY investigation phases before any code change

Most waves have an explicit Phase 1 (read-only audit) before Phase 2
(apply). Examples:

- **Wave 287 P** — 4 phases: codepath audit (24 findings), edge-case
  tests (65 new), CI hardening (1 step), adversarial sweep (25 cells).
  Phase 1 surfaced 24 bugs without touching production code; Phases 2-4
  added regression coverage without altering production behaviour per
  the user's directive "找paper-grounded 控制器的漏洞做算法和测试用例
  的加强".
- **Wave 292** — 3 phases: P1 pipeline inventory, P2 config genealogy,
  P3 cross-check. All read-only; no code or vendored edits.
- **Wave 296** — P1 architecture audit (read-only) → P2 cache design
  → P3-a class wired.
- **Wave 298 P1** — this is itself a read-only audit (P1 code innovations).

**file:line / doc-line evidence:**
- `docs/audit/wave287-final.md` (Phase 1-4 roll-up table)
- `docs/audit/wave292-p1-pipeline-inventory.md` (read-only P1)
- `docs/audit/wave296-p1-architecture.md` (read-only P1)

### 6.3 Contingency lock docs (honest progress summary at frozen commit)

**Wave 288 P1** explicitly was a contingency doc to **lock state BEFORE
Wave 286 / 287 finish**:

> "Single contingency doc that locks current experimental state BEFORE
> Wave 286 / 287 finish, so the paper author has a clean reference
> frame even if Waves 286 (FID GPU strict resweep) and 287 (24-bug
> paper-grounded controller audit) sweep drivers are aborted mid-flight."

The doc is **READ-ONLY** (no code changes). It is meant to be
**superseded** by the eventual Wave 286 strict resweep + Wave 287
24-bug fixes; it is the honest position at the frozen commit. The
W291 final closeout explicitly flags this: "Wave 290 + 291
supersession: 2026-09-23 — this contingency doc is superseded by the
Wave 290 + 291 sweep chain".

**file:line / doc-line evidence:**
- `docs/audit/wave288-p1-honest-progress-summary.md` preamble (line 6-9)
- Wave 290 + 291 supersession line (`wave288-p1-honest-progress-summary.md:6`)

### 6.4 Per-cell status lock with rubric labels

**Wave 22 metric-rev3** defines six status labels applied uniformly
per-cell:

- **STRONG**: 3-seed pooled, d_z > 0.8, Bonferroni p < α, direction-consistent.
- **PARTIAL**: d_z > 0.8 OR direction-consistent, but not all bars met.
- **WEAK**: hypothesis-only or low effect size; no STRONG evidence.
- **REGRESSES**: Bonferroni-significant in the regression direction.
- **UNDERPOWERED**: metric is non-zero but statistical test lacks power.
- **BLOCKED**: env-blocker, vendor bug, or out-of-scope.

These labels are applied per-cell in the per-cell status table (e.g.,
W288 P1 §5 + §6.3 honest summary) so the reader can immediately see
the strength of evidence per claim. Most ML papers use only
"significant / not significant" — the six-label rubric separates
direction (REGRESSES) from evidence strength (STRONG / PARTIAL /
WEAK) from sample-size limitation (UNDERPOWERED) from external
blockers (BLOCKED).

**file:line / doc-line evidence:**
- `docs/audit/wave288-p1-honest-progress-summary.md` §5 (Wave 22 metric-rev3 rubric)
- Per-cell status table: `docs/audit/wave288-p1-honest-progress-summary.md` §2 + §5

### 6.5 D.4 byte-stable 30/30 regression suite as load-bearing guard

`tests/test_d4_regression_vectors.py` ships 30 byte-deterministic
regression vectors that must PASS on every wave. The D.4 suite is
the load-bearing guard that lets the project claim byte-identical
cosine R-cell headlines across refactors. Without D.4, the Wave 268
strict-clean rule (backward compat as primary invariant) would be
unverifiable.

The D.4 suite is referenced in **every** audit doc's INVARIANTS
section and is the canonical regression guard for byte-stable
behaviour.

**file:line / doc-line evidence:**
- `tests/test_d4_regression_vectors.py` (30/30 PASS)
- `docs/audit/wave287-final.md` (D.4 invariant: 30/30 PASS)
- `docs/audit/wave291-p5-3seed-results.md` §7 (D.4 30/30: PASS)

---

## 7. Verification status

```
$ python3 -m pytest tests/test_d4_regression_vectors.py -q
30 passed, 3 warnings in ~1.06s

$ python3 tools/check_claims_consistency.py
**No drift detected.** (60 ACTIVE, 1 PROVISIONAL, 2 DEPRECATED)

$ ruff check adaptive_reflow/ tests/ scripts/ tools/
All checks passed! (0 findings)

$ mkdocs build --strict
0 warnings
```

All four release gates green. **No code changes** in this audit note —
read-only inventory of the methodological innovation surface.

---

## 8. Edit discipline

* `adaptive_reflow/` — NOT modified (read-only audit).
* `tools/` — NOT modified.
* `docs/drafts/paper-flat-flattened.md` — NOT modified.
* `docs/CLAIMS.md` — NOT modified.
* `data/<repo>/**` — NOT touched (vendored scoring scripts preserved per
  "clone下来的原sota项目里的打分脚本依旧不能动，严格复用").
* `data/lineageflow_upstream/**` — NOT touched.
* `.venvs/**` — NOT touched.
* `docs/audit/wave298-p2-methodology-innovations.md` — this file (created).

---

## 9. Artifacts

* `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave298-p2-methodology-innovations.md` — this audit note (5 innovation table + per-innovation §1-§5 + §6 runners-up + §7-§9 verification / edit-discipline / artifacts).
* `docs/audit/wave298-p1-code-innovations.md` — companion doc (code-level architectural innovations, 5 ranked).
* `docs/audit/wave288-p1-honest-progress-summary.md` — honest disclosure pattern anchor.
* `docs/audit/wave287-final.md` — 24-bug audit methodology anchor.
* `docs/audit/wave291-p5-3seed-results.md` — permutation test + 3-seed paired-t + cosine σ noise band anchor.
* `docs/audit/wave290-p4-benchmark-fixed.md` — fixpoint FID verification + batched-harness 30x speedup anchor.
* `docs/audit/wave286-final.md` — 17-cell CIFAR re-sweep methodology anchor.
* `docs/CLAIMS.md` — central claim ledger (60 ACTIVE + 1 PROVISIONAL + 2 DEPRECATED).
* `docs/audit/INDEX.md` — topic-cluster cross-reference map.

---

## 10. Honest summary

* **Goal achieved:** this audit note enumerates **5 methodological
  innovations** (honest disclosure, wave-based audit chain, permutation
  test, cosine σ noise band, backward compat as primary invariant)
  plus **5 runners-up** that did not make the top-5 (user-gated push,
  READ-ONLY investigation phases, contingency lock docs, per-cell
  status rubric, D.4 byte-stable regression suite).
* **Top innovation ranked #1 (honest disclosure):** the project
  publishes refuted hypotheses inline in `docs/CLAIMS.md` as status
  addenda, preserving ACTIVE status verbatim per Wave 268 strict-clean
  rule. The CLM-005 / CLM-006 / CLM-070 chains are the canonical
  examples (W286 P promotion → W291 P4 refutation → W292 re-anchoring,
  all in the same CLM row).
* **Novelty vs literature:** each innovation is **closer to a kernel
  development discipline or a lab notebook** than to a typical ML
  paper. Most papers do not run permutation tests on their claimed
  levers, do not use a deterministic baseline's σ as the noise band
  for byte-stability claims, and do not lock backward compat as a
  load-bearing invariant.
* **All four release gates green at HEAD (no code changes).**
* **This doc is READ-ONLY.** It complements Wave 298 P1 (code-level
  architectural innovations) by focusing on **how we run a research
  project**, not on what the code does.
