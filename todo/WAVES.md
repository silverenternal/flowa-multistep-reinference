# `todo/WAVES.md` — consolidated project state and history

**Date:** 2026-10-11 (post-push governance refresh)
**Status:** living document (single governance surface)
**Purpose:** one self-contained record of *where the project is*, *how it got
here*, *what the evidence says*, and *what remains* — written at the level of
**project phases**, not individual work increments.

This document supersedes the per-increment bookkeeping that used to be spread
across the `todo/` folder (`STATUS.md`, `INDEX.md`, `README.md`, `TIMELINE.md`,
`LOOP.md`, `GATES.md`, `decisions.md`, `lessons-learned.md`, `RISK-REGISTER.md`,
`PUSH-READY.md`, and the historical venue plan). Those files are **retained
verbatim** for traceability, but this file is the authoritative summary and the
recommended first read. It is deliberately written **without increment numbers**
so that it stays stable as work continues.

---

## 0. How to read this document

1. **§1 Current state** — the one-screen status: repo, gates, manuscript, venue.
2. **§2 Project evolution** — the phase narrative (why each phase exists).
3. **§3 Evidence ledger** — the R-level claims and their current verdicts.
4. **§4 Gate chain** — the binding acceptance gates.
5. **§5–§7** — decision log, lessons learned, risk register (condensed).
6. **§8–§9** — deferred scope and user-gated actions.
7. **§10** — cross-references and reading order.

For the granular audit trail behind any statement here, see the per-increment
records preserved under `docs/audit/` and `docs/ARCHIVE/` (indexed by topic in
`docs/audit/INDEX.md`). Those records carry increment identifiers; this document
does not.

---

## 1. Current state (as of 2026-10-11)

### 1.1 Repository

- **Branch:** `main`. **HEAD:** `0209002` ("Push unblock: purge 147.1 MB supplementary_bundle.zip from history + gitignore").
- **Ahead of `origin/main`:** **0** commits. The 192-commit backlog was pushed on
  2026-10-11 (user-authorized; the first push since the Wave 325 NO-PUSH policy).
  Pushing remains **user-gated** — agents commit locally but never push.
- **Tags (local, unpushed):** `v3.0-tnnls-ready`, `v3.1-tnnls-with-figure` (the tag
  push stays user-gated).

### 1.2 Acceptance gates (snapshot)

| Gate | Result | Command |
|---|---|---|
| D.4 byte-stable regression vectors | **30/30 PASS** | `pytest tests/test_d4_regression_vectors.py -q` |
| Ruff | **0 findings** in scope | `ruff check adaptive_reflow/ tests/ scripts/ tools/` |
| Mkdocs `--strict` | **PASS** (exit 0) | `mkdocs build --strict` (theme `material` lives in `flowmol3_venv`) |
| Checkpoint SHA-256 | **4/4 PASS** | pinned ckpt hashes |
| Claims consistency | **PASS, no drift** | `python tools/check_claims_consistency.py` |
| Import acyclic | **PASS** | `pytest tests/test_framework/test_import_acyclic.py -v` |
| Vendored repos | **byte-identical** | `data/` untouched |

**Gate results (re-verified 2026-10-11):**

- **Pytest (CI subset `-m "not slow and not benchmark"`):** `5055 passed / 171
  skipped / 50 deselected / 12 xfailed / 0 failed`. The earlier "25 failed /
  5166 passed" reading was environment/ordering-dependent and is resolved; the
  long-cited "5155 passed / 196 skipped" figure is a historical freeze baseline.
- **Mypy:** `mypy --strict adaptive_reflow` → **0 errors in 230 files** (the prior
  988-error camera-ready deferral was closed).
- **Ruff:** 0 findings in scope.

### 1.3 Manuscript

- **Title:** *"FlowA: Geometry-Aware State-Intervention Reformulation for Frozen
  Flow-Matching Checkpoints."*
- **Artifacts:**
  - `docs/drafts/paper-A-final.pdf` — **11 pages**, 446705 bytes,
    SHA-256 `461ee92e…` (IEEEtran-journal, double-column, embedded fonts).
  - `docs/drafts/paper-A-final.md` — canonical markdown source,
    SHA-256 `42ff08ac…`.
  - `docs/drafts/paper-A-final.tex` — build source for the PDF,
    SHA-256 `ba920254…`.
  - `docs/figures/fig9_cell_evidence_comparison.png` — evidence-comparison
    figure, SHA-256 `4f3224bd…` (rendered by `tools/render_cell_evidence_figure.py`).
- **Figures:** the manuscript carries (i) an inline TikZ architecture diagram
  (three-domain split + four-port control surface + five adapters + shared
  kernel band) and (ii) a mechanism figure, plus the matplotlib evidence figure
  above. Table handling uses `booktabs`.
- **Internal consistency:** the `.tex` uses LaTeX auto-numbering (so cross-references
  cannot drift); the `.md` uses explicit section numbers, which are kept in sync
  by hand.

### 1.4 Venue

- **Primary target:** IEEE TNNLS (Transactions on Neural Networks and Learning
  Systems). Switched from TPAMI during the venue-consolidation phase.
- **Backups (in order):** TIP → Pattern Recognition → Neural Networks → EAAI.

### 1.5 Claims ledger

- `docs/CLAIMS.md`: **61 active claims**, 2 deprecated, 0 provisional
  (CLM-001 … CLM-069 range). `CLM-040` is held provisional by a `Disputed by`
  citation. No drift detected by the consistency checker.

---

## 2. Project evolution (phase narrative)

The project was executed as a sequence of phases. Each phase below states
**what it did**, **why it was needed**, and **what it produced**.

### 2.1 Foundation — framework, theory, algorithm

Established the training-free, solver-agnostic "re-inference" framework: a
frozen flow-matching checkpoint is wrapped and re-run under a typed control
surface, without touching the model internals. Delivered:

- the **typed four-port control surface** (`SchedulerProtocol`,
  `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`),
  realised across three architectural domains (algorithm / evaluation / adapter);
- the **framework kernel** — `StateBundle`, typed contracts, a SHA-256
  hash-chained ledger, and byte-stable replay;
- the **theory** — the inference-dynamics reformulation plus the formal
  properties/lemmas/theorems carried in the manuscript (§2.2 and §6 of the
  paper).

**Why:** everything downstream (adapters, comparisons, packaging) depends on a
stable interface and a falsifiable theory. *Outcome:* the import-acyclic and
byte-stability gates became binding from this phase onward.

### 2.2 Candidate analysis and ranking

Surveyed candidate flow-matching models (protein, molecule, image, toy),
assessed each for integrability (checkpoint *and* upstream source both
available), size/fit, and metric headroom, and ranked them.

**Why:** an early integration attempt failed because the upstream source was
unreachable — a per-candidate "is this even runnable?" step prevents spending
effort on non-shippable models. *Outcome:* a ranked candidate list and the
standing rule that a model without a public source repo is "design-only."

### 2.3 Adapters and the typed control surface

Wrote per-model adapters that expose each frozen checkpoint through the
four-port surface, each with a byte-stability test and a synthetic-mode default
that exercises the protocol on CPU without a checkpoint.

**Why:** the framework's value proposition is *solver-agnosticism* — it must
wrap heterogeneous models without per-model core edits. *Outcome:* the adapter
conformance suite and the byte-stable replay guarantee.

### 2.4 Baseline-vs-framework comparisons

Ran baseline (single-pass) versus framework (multi-round re-inference) for each
integrated model on a per-model acceptance metric, with an explicit
saturation check.

**Why:** the headline claim ("a frozen flow-matching checkpoint improves when
wrapped") must be falsifiable per model. *Outcome:* the R-level evidence ledger
in §3. A saturated metric forces a **TIE**, not a win.

### 2.5 Scale-up to N=1000

Re-ran the load-bearing cells at N=1000 with matched-NFE accounting across the
supported models.

**Why:** small-N results were not defensible against a reviewer's sample-size
scrutiny. *Outcome:* the N=1000 evidence that the ledger's verdicts rest on.

### 2.6 Ablation and control experiments

Per-component ablations (5-arm), fixed-threshold controls, random/uniform
controls, single-scheduler controls, and a tier-aware scheduler variant.

**Why:** a reviewer asks "which component actually causes the effect?" *Outcome:*
component attribution, and the disclosure that most cells use a cosine-anneal
scheduler while one headline cell uses a tier-aware sheet scheduler.

### 2.7 Efficiency, NFE accounting, Pareto

Measured wall-clock, memory, and NFE cost; built the NFE Pareto frontier; added
CUDA-graph capture.

**Why:** the framework must not buy quality with unbounded compute. *Outcome:*
the efficiency section of the paper and the cost/benefit framing.

### 2.8 Statistical rigor

Standardized effect sizes, Bonferroni families, cluster-robust standard errors,
FDR-BH correction, TOST-style equivalence checks, and the 12-column audit table.

**Why:** claims must survive multiple-comparison scrutiny. *Outcome:* several
verdicts were **downgraded honestly** here — see §3 (R1 demotion, R5a TIE,
R5b conditional, R5c direction-flip).

### 2.9 Reproducibility and packaging

Byte-stable replay, environment-hash pinning, per-cell reproducibility recipes,
a cold-clone capability audit, a metric ledger, and a machine-readable manifest
with pinned SHA-256s.

**Why:** the framework's central promise is *reproducible* re-inference.
*Outcome:* the reproducibility gate and the reviewer-facing evidence bundle.

### 2.10 Venue consolidation and submission package

Switched the target from TPAMI to TNNLS, consolidated the submission-readiness
state into one document, assembled the `tnnls_submission/` package (8 files plus
a supplementary bundle), refreshed cross-document links, and pinned artifact
hashes.

**Why:** the package must present one consistent story to editors and reviewers.
*Outcome:* `tnnls_submission/SUBMISSION_READINESS.md` and the MANIFEST ledger.

### 2.11 Manuscript restructure and figures

Retitled the paper to its current *"Geometry-Aware State-Intervention
Reformulation"* framing, added the inference-dynamics reformulation section and
the formal properties, compressed the abstract, relocated the mechanism figure,
and re-typeset to the current 11-page build. Added the architecture diagram and
the evidence-comparison figure.

**Why:** the mechanism-centered framing is what distinguishes the contribution
from prior solver-swapping work. *Outcome:* the current manuscript (§1.3).

---

## 3. R-level evidence ledger (current verdicts)

Load-bearing for the manuscript's empirical sections. Verdicts are current as
of this document's date; the full per-cell audit rows and the power-disclosure
index live in the paper and in `docs/CONSOLIDATED_RESULTS.md`.

| # | Model | Metric | Baseline | Framework | Δ | N | Verdict |
|---|---|---|---:|---:|---:|---:|---|
| R1 | LineageFlow | HMMER hits | 158 | **342** | **+116%** | 1000 (single seed) | PARTIAL — single-seed-disclosed |
| R2 | Kanzi | RMSD (medium tier) | 0.6146 | **0.5919** | **−0.0227** | 1000 | SUPPORTED |
| R3 | CIFAR-10 RF v2 | FID | 218.87 | **122.18** | **−44.17%** | 1000 | NFE-averaged (3-seed blocked at vendor level) |
| R4 | 2D Two Moons | W₂ | 0.5029 | **0.4663** | **−7.28%** | 1000 | matched |
| R5 | 2D Eight Gaussians | W₂ | 0.6606 | **0.5919** | **−10.40%** | 1000 | matched |
| R5b | CIFAR-10 RF | FID (matched NFE=50) | 218.87 / 454.39 | 122.18 / conditional | −1.60% to −2.53% at `n_rounds=1`; **regresses** at `n_rounds≥2` | 200/1000 | SUPPORTED **conditional on `n_rounds=1`** |
| R5c | MNIST FM | FID (matched NFE=50) | smoke / production | framework wins −28.43% (smoke) / **baseline wins +10.37%** (production) | direction-flip | 1000 / 200×3 | SUPPORTED smoke / **baseline-wins production** (both paths documented) |
| R6 | LineageFlow | pLDDT / scPerp | 42.07 / 17.88 | **43.20 / 13.96** | **+1.12 / −3.92** | 1000 | PARTIAL_SUPPORTED — tier-aware; hard tier SUPPORTED 3/3, easy tier regresses 3/3 |

**Verdict distribution (11 cells):** 4 STRONG (R2, R5b conditional, R5c smoke,
R6) + 1 TIE (R5a) + 6 PARTIAL/SUPPLEMENTARY (R1, R3, and four supplementary
K-cells).

**Key honest corrections retained:**

- **R1 demoted** from a 3-seed STRONG to single-seed-disclosed: the extra seeds
  were contaminated by a framework fallback path.
- **R5b is conditional:** a genuine win at a single round, a genuine regression
  at two or more rounds. Only 2 of 4 schedulers win at N=1000.
- **R5c flips direction** between the smoke checkpoint (framework wins) and the
  production checkpoint (baseline wins); both are reported.
- **R5a is a TIE:** the effect sits below the strict equivalence floor.

These corrections are the project's main credibility asset — the ledger reports
what the numbers actually say, not a uniform "framework always wins" story.

---

## 4. Acceptance gate chain (binding)

Per the standing directive, **every task must have an acceptance gate; a failed
gate blocks the next task.** The chain:

- **Foundation gate** — framework + theory + algorithm solid: import-acyclic,
  adapter byte-stability, mkdocs strict, no ACTIVE claim disputed.
- **Analysis gate** — ≥3 candidates analyzed and ranked.
- **Adapter gate** — per-model adapter + conformance tests + byte-stability +
  synthetic default + plug-in doc section.
- **Comparison gate** — per-model acceptance table populated + comparison
  recorded + verdict logged; a regression stops and returns to foundation.
- **Capability gate** — cold-clone capability audit: mean value ≥ +0.05,
  worst-case ≥ −3%, ≥3 model families, honest-negative surface ≤ 30%,
  ≥6/7 metrics reproducible. This is the **load-bearing** gate: it measures
  value delivery, not engineering hygiene.
- **Paper gate** — manuscript complete and consistent with the evidence.
- **Operational gates** — push released (user-gated); clean working tree;
  status log updated.

Per-increment hard gates (import-acyclic, byte-stability, mkdocs strict) must
pass before any work starts.

---

## 5. Architecture decision log (condensed)

- **D-001 — Phased plan over one big push.** A per-candidate analysis step is
  mandatory before integration, because an early integration failed on an
  unreachable upstream source that analysis would have caught.
- **D-002 — Falsifiable per-model acceptance metric.** Each model gets a primary
  metric, a secondary metric, an improvement bar, and a saturation check;
  a saturated metric yields a TIE, not a win.
- **D-003 — Two-track tracking.** A machine-readable task index alongside
  human-readable markdown.
- **D-004 — No re-runs on synthetic shims.** A synthetic-only re-run produces no
  new signal; either unblock the real forward pass or classify the model as
  design-only.

---

## 6. Lessons learned (condensed)

- **LL-001 — A shippable model needs both a checkpoint *and* accessible source.**
  A verified checkpoint with an unreachable source repo cannot be unpickled;
  treat it as design-only.
- **LL-002 — Metric saturation invalidates a comparison.** If the baseline is at
  the metric ceiling, the comparison is a TIE; pick a metric with headroom.
- **LL-003 — Research estimates are not measurements.** Verify file sizes and
  loadability directly; compute a fit margin before committing to a model. A
  failed integration is evidence of an implementation problem first, not
  evidence against the framework.

---

## 7. Risk register (condensed)

Forward-looking risks and their standing mitigations. (Distinct from the
lessons, which are retrospective.)

| ID | Risk | Mitigation |
|---|---|---|
| R-001 | HuggingFace rate-limit/block during download | pinned hashes; retry/backoff; vendored copies |
| R-002 | Upstream source repo unreachable | verify source availability before integrating |
| R-003 | Checkpoint far larger than estimated | verify size; compute fit margin |
| R-004 | Upstream `core` source unpublished | classify as design-only |
| R-005 | Metric saturation → TIE | saturation check in the acceptance table |
| R-006 | Dependency unavailable on the target Python | pinned venvs per model |
| R-007 | Optional accelerated kernel not installable | CPU/synthetic fallback |
| R-008 | Paper-axis mismatch (vocab/metric/protocol) | per-cell provenance ledger |
| R-009 | Library version incompatibility | pinned lockfiles |
| R-010 | Mkdocs strict warnings on doc edits | build strict before committing docs |
| R-011 | Dirty working tree at close | operational clean-tree gate |
| R-012 | User direction changes scope | pause and re-plan |
| R-013 | Sandbox vs `main` divergence | commit locally, push user-gated |
| R-014 | OOM on long runs | memory guards; batched harness |
| R-015 | Honest reporting suppressed by "make it work" pressure | honest-negative surface tracked as a gate |
| R-016 | A batched-path library defect (multi-increment) | defensive patch; documented |
| R-017 | Vendored upstream defensive-patch revert | pin vendored repos byte-identical |
| R-018 | Scheduler-attribution disclosure gap | disclose scheduler per cell |
| R-019 | Venue switch (TPAMI → TNNLS) | re-target package; keep backups |
| R-020 | R5b regression ↔ conditional-win reversal | report both regimes |
| R-021 | R5c smoke ↔ production direction-flip | report both checkpoints |
| R-022 | Deep-audit finding cluster | resolved into the ledger corrections (§3) |

---

## 8. Deferred / out of scope

- Mypy repair and the remaining non-auto-fixable ruff findings (camera-ready).
- Integrating models with no upstream checkpoint / no shipped adapter.
- The blocked 3-seed N=1000 sweeps for R3 and R1 (blocked at vendor level /
  invalidated by fallback contamination); the single-seed / byte-stable
  evidence is load-bearing instead.
- Live-GPU replication of R6 (the counterfactual grid-search result is the
  load-bearing evidence).
- Paired-t replication for R2 and resolution of the R5a TIE (no confirmation
  above the equivalence floor).
- Push to `origin/main` (user-gated).
- Reintroducing deprecated back-compat aliases (canonical names only).

---

## 9. Submission readiness and user-gated actions

The submission package (`tnnls_submission/`) contains the manuscript pointer,
cover letter, checklist, data-availability and highlights statements, tables,
figures, and a supplementary bundle, with pinned SHA-256s in `MANIFEST.md`.
Readiness is consolidated in `tnnls_submission/SUBMISSION_READINESS.md`.

**Actions only the user can perform:**

1. Fill the `[USER TO FILL]` placeholders in `tnnls_submission/cover_letter.md`
   (guide: `tnnls_submission/FILL_GUIDE.md`).
2. ~~`git push` to `origin/main`~~ — **DONE 2026-10-11** (`origin/main` = `0209002`;
   the 192-commit backlog was pushed after the 147.1 MB supplementary-bundle blob
   was purged from history + gitignored).

---

## 10. Cross-references and reading order

**Recommended reading order for a new reader:**

1. This file (`todo/WAVES.md`).
2. `docs/CLAIMS.md` — the claims ledger with provenance.
3. `docs/CONSOLIDATED_RESULTS.md` — single source of truth for experimental evidence.
4. `docs/METRIC_LEDGER.md` — per-metric provenance.
5. `docs/ARCHITECTURE.md` — the three-domain / four-port architecture.
6. `docs/drafts/paper-A-final.md` — canonical manuscript source.
7. `tnnls_submission/SUBMISSION_READINESS.md` — submission-readiness consolidation.

**Branch by interest:**

- **Statistics:** `docs/tables/` standardized-stats tables.
- **Mechanism validation:** paper §6 (formal properties + lemmas/theorems).
- **Efficiency / Pareto:** paper §7.7 and `verification_outputs/`.
- **Reproducibility:** `reproduce/` and `paper-data/<cell>/REPRODUCIBILITY_RECIPE.md`.
- **Decision / risk history:** the retained `todo/` files named in the header.

---

## Appendix A — Legacy granular bookkeeping (retained, not maintained here)

The earlier per-increment records are **kept in place** for verification and
provenance: the topic-clustered audit records under `docs/audit/` (catalogued in
`docs/audit/INDEX.md`), the archived audit records under `docs/ARCHIVE/`, and the
original `todo/` governance files. They carry increment identifiers and are
useful for tracing how a specific result evolved; they are **not** the
management surface. New management-level information belongs in this file.
