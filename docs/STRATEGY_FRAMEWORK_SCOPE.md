# Framework Scope Strategy: SOTA Models vs Toy Validation

**Date:** 2026-09-04
**Status:** Draft for review
**Trigger:** 80GB OOM on FlowMol3 N=5000 paper-parity run (2026-09-04 04:36:57);
re-evaluation of whether SOTA model reproduction is the right validation strategy
for `adaptive_reflow`.

---

## 1. The question

> "As a model inference framework, do we actually NEED to use SOTA models
> to reach SOTA? Feels too resource-intensive."

The short answer: **no — and chasing SOTA reproduction is a poor validation
strategy for a framework**. The long answer is below.

---

## 2. What the framework actually validates

`adaptive_reflow` is a typed-contracts framework for flow matching ODE
re-inference. Its value proposition has five components:

| Component | What it proves | SOTA model required? |
| --- | --- | --- |
| Typed contracts (Protocols, dataclasses) | API surface is sound, types catch errors early | No — any model exposes this |
| Re-inference (custom ODE solver, intermediate state) | Custom solvers give correct trajectories, intermediate state is useful | No — toy model on a small dataset suffices |
| Universal abstractions (`X`, `A`, `C`, `E` channels) | Multi-modal pipeline generalizes | No — even one modality + a synthetic second modality is enough |
| Adapter pattern | Bridge between framework and model-specific code is clean | No — one well-written adapter is enough |
| Eval pipeline | Metrics are computed correctly | No — any SMILES set with a known ground truth is enough |

**None of the five require a SOTA model.** A 100K-parameter flow matching
model on QM9 (or a ZINC subset, or even a synthetic 2D-toy dataset) validates
all five.

---

## 3. The cost of SOTA reproduction

Per-SOTA-model cost (rough, from the FlowMol3 N=5000 experience):

| Item | Cost |
| --- | --- |
| Weight provisioning (HF gated, LFS, etc.) | 0.5-1 day, often blocked on manual approval |
| Env setup (PyTorch + DGL + torch_scatter + RDKit + …) | 1-2 days, frequent OOM / wheel mismatches |
| Data dependencies (GEOM-DRUGS 20GB, UniRef50 75GB, etc.) | 1 day, frequently blocked on TLS egress |
| External tools (GFN2-xTB in conda env, AlphaFold, etc.) | 1 day, separate env from the framework's venv |
| Adapter writing + debugging | 2-3 days |
| Paper-metric axis alignment (vocab, reference set, protocol) | 1-2 days, recurring gaps (e.g. FlowMol3 FG-dev 3 axes diverge from paper) |
| One paper-parity run at scale (N=5000, 5-subset CI) | 1 hour GPU + 5-10 min aggregation |
| Re-run on real data after vocab/ref fix | Another 1 hour + 1 day tooling |

**Total per SOTA model: 1-2 weeks of wall-clock time, plus recurring
infrastructure surprises.** Doing 5 in parallel is impractical; doing them
sequentially is 5-10 weeks of focused work.

The hidden cost is the **axes-of-divergence audit**: every time we compare
to the paper we discover a new axis (vocab vs paper's specific FGs,
normalization raw vs ratio-of-means, reference set NCI proxy vs GEOM-DRUGS,
PB-valid protocol single-conformer vs 5-conformer, energy metrics
missing entirely). Each axis is a small delta but the cumulative cost is
large.

---

## 4. The proposed tiered strategy

### Tier 1: Toy validation (always, low cost)

**Goal:** validate the framework's five components end-to-end with
small, controllable models.

- **Toy molecule model**: a 100K-parameter flow matching model on
  QM9 (or a ZINC-250K subset, or even a synthetic 2D-graph dataset).
  Trained in 1-3 hours on RTX PRO 6000. The architecture mirrors
  FlowMol3's modalities (`X`, `A`, `C`, `E`) at a smaller scale so
  the framework's universal abstractions get exercised, not bypassed.
- **Toy cross-modality model**: a 50K-parameter flow matching model on
  MNIST images (or a synthetic 1D-signal dataset). Proves the
  `universal` abstractions aren't molecule-specific.
- **Toy eval fixtures**: pre-computed SMILES sets with known validity,
  PB-valid, and FG-dev numbers. Validates the eval pipeline.

**Cost:** 1-2 weeks wall-clock. **ROI:** high — every framework
component gets exercised, all unit/integration tests become
real-framework-tests.

### Tier 2: One SOTA model as a "stretch integration" (selective)

**Goal:** prove the framework handles a real, production-scale
codebase end-to-end with paper-comparable numbers.

- **Pick one**, not five. FlowMol3 is the natural pick (we already have
  weights, env, and a partial adapter). The other four
  (ADiT, SemlaFlow, EQGAT-Diff, etc. for molecules; HiDream / Lumina
  for images; ProtBFN for proteins; Wan2.2 for video) stay as
  adapter-skeleton + paper-parity doc only, until Tier 1 is solid.
- **Accept the paper-axis gaps** as known deviations, document them
  in a `paper-parity.md` doc per model, and move on. The framework
  is not validated by the paper number; it's validated by the
  infrastructure that *could* reproduce it (after the user's
  dedicated paper-reproduction effort, not the framework's).

**Cost:** 2-4 weeks for the one SOTA integration. **ROI:** medium —
strong reference example, no claim of "framework is SOTA on 5 models".

### Tier 3: Multi-SOTA benchmarking (only if explicitly asked)

**Goal:** produce a benchmark table that compares the framework
against multiple SOTA baselines.

- **Only if the user wants a community-facing benchmark**, e.g. a
  paper submission or a comparison against another re-inference
  framework. Otherwise skip.
- **Cost:** months. **ROI:** low for the framework's own development.

---

## 5. What we lose and what we gain

### What we lose by stepping back from Tier 3

- The "5 SOTA models paper-parity" headline number in our docs.
- The community signal of "we reproduced these papers exactly".
- Some blog-post / tweet material.

### What we gain

- **Hours-per-iteration** instead of days-per-iteration on the
  framework itself. The 80GB OOM investigation took half a day;
  redoing it for 4 more SOTA models is 2 more days of pain, with
  no framework-level learning.
- **A framework that works on consumer hardware** (toy model +
  RTX 3060). The Tier-1 strategy runs end-to-end on a laptop
  GPU; the Tier-3 strategy requires RTX PRO 6000 + 96GB RAM +
  multi-day env setup.
- **A real test surface.** Tier 1 + Tier 2 give us a CI-runnable
  integration test (toy model + fixtures) plus a manual smoke
  (real SOTA model). Tier 3's "all 5 SOTA" has no CI-runnable
  surface.
- **Honest positioning.** "Our typed-contracts framework runs
  any flow matching model with custom ODEs; here's a 100K-param
  toy on QM9 that runs end-to-end, here's a 6M-param FlowMol3
  paper-comparable run, here's the gap inventory for the other
  4 SOTA models" is more credible than "we claim 5-SOTA parity,
  here's 2 of 6 paper metrics and the other 4 are not yet done".

---

## 6. Recommendation (immediate action)

1. **Defer all paper-parity runs on the 5 SOTA models** until Tier 1
   is done. The paper-parity work is downstream of "is the framework
   sound" — answering the latter first saves wasted work.
2. **Build Tier 1**: pick a toy flow matching model for molecules
   (e.g. a 100K-param variant of FlowMol3's `X`/`A`/`C`/`E` modalities
   on a QM9 or ZINC subset). Build it through the framework's adapter
   pattern, validate contracts and re-inference end-to-end, write
   integration tests.
3. **Pick 1 SOTA model** for Tier 2 (FlowMol3 is the natural pick since
   we already have weights, env, and partial adapter). Document the
   paper-axis gaps (vocab / ref / protocol) and stop trying to close
   them all at once. Other 4 SOTA models stay as adapter-skeletons.
4. **The paper-parity doc** at `docs/r17-survey/flowmol3-paper-parity.md`
   is preserved as the Tier-2 record. The N=5000 + 5-subset CI
   numbers (validity 100%, PB-valid 0.992, REOS 0.455, FG-dev
   8.6256 NCI proxy) stand as the best paper-comparable run to date,
   with the documented deviations (NCI proxy ref, ratio-of-means
   not yet implemented, GFN2-xTB energy metrics missing, 5-conformer
   PB-valid not yet done).

---

## 7. What this doc does NOT change

- The framework's existing typed-contracts and adapter pattern
  remain. Toy models and SOTA models use the same APIs.
- The OOM defenses wired in commit `28e3bf9` (mmap-friendly REOS,
  subprocess+RLIMIT cap, stream-line SMILES loaders, lru_cache
  synthetic weights, circular-import break) remain — they are
  useful regardless of the model scale. P0-3 made the
  ``tools/run_mol_eval_safe.py`` subprocess+RLIMIT wrapper the
  default subprocess entry point for any eval with
  ``n_mols >= 200`` (callers: ``run_sota_graphbfn_experiment.py``,
  ``run_sota_flowmol3_v2_adapter_experiment.py``); opt out via
  ``--no-safe-wrap`` per-call or ``MOL_EVAL_NO_WRAP=1`` globally.
- The FlowMol3 adapter and partial paper-parity record remain —
  they are the Tier-2 evidence, not abandoned.

---

## 8. Open questions for the user

- **Tier 1 scope**: is QM9 the right toy dataset, or should we
  start with a synthetic 2D-toy (faster training, more controlled)?
- **Tier 2 pick**: confirm FlowMol3 is the right single SOTA model,
  or should we pick something else (e.g. a smaller / cleaner codebase
  like SemlaFlow)?
- **The other 4 SOTA adapters**: keep as skeletons (current state) or
  remove entirely?
- **Paper-parity doc**: keep as a "best paper-comparable run to date"
  record, or reframe as a "framework-vs-paper gap inventory"?

These four questions block the next concrete action item.

## Paper grounding

The framework's correctness story (which the tiered strategy in §4
implicitly validates at Tier 1 and Tier 2) rests on the underlying
JMAA paper (Li 2026):

* **Theorem 1** (BL-convergence of `mu_{g,eps}` to `nu_g`,
  `paper section 3.1`) is the per-algorithm correctness target. The
  Tier-1 toy model is the smallest meaningful surface to surface-test
  Theorem 1 — any framework claim that "the framework helps
  convergence" is vacuous without the toy hitting the rate-bound
  constant `rate_bound_C(eps)` from `adaptive_reflow/theory/rate_bound.py`.
* **Proposition 3** (selection-mechanism display, `paper section 4.2`)
  grounds the per-round restart distribution; Tier 1 should exercise
  Proposition 3's BL assembly invariant directly (not bypass it via a
  custom sampler), or the toy is no longer a framework integration.
* **Proposition 6** (escaping-sharpness bound) is the formal justification
  for *not* expecting Tier 3 multi-SOTA improvement — the bound places
  the framework's gain inside a known envelope that 5-SOTA averaging
  can mask.

In short, the tiered strategy is a **soundness/cost trade-off** in
front of Theorem 1's rate bound; Tier 1 cannot be skipped without
giving up paper-grounded validation.
