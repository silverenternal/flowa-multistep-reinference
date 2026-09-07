# Wave 13 — framework-internal-metrics research + improvement

**Status:** done (file `todo/framework-internal-metrics.md` updated to rev 2; verification critical + 4 major issues fixed) (+ Wave 22 Phase 2: adversarial verify of 4 agents; Wave 26-29: rev 3 plan + cold-clone audit; Wave 38: framework-internal-metrics.md §G row updated; Wave 41-54: composite metric layer (Kanzi/LineageFlow/FlowMol3) added to metrics.md)
**Date:** 2026-09-05
**Owner:** framework maintainer
**Goal:** ground framework-internal-metrics.md in literature + similar-project practice; fix 5 critical + 4 most consequential major issues from adversarial verification.

## Background

Per user directive 2026-09-05:
> "我觉得你刚才定义的框架内指标不完善或者说是有问题，缺乏思考与推导，现在启动ultracode,要求做联网调研与参考，看看别人在面对相近任务的时候是怎么定义和设计框架内指标的，改进你刚才添加的内容"

The rev 1 file (`framework-internal-metrics.md`) was based on internal intuition
alone. The user asked for a literature review + reference to community practice.

## What was launched

- **Workflow ID:** `wgzsrhtgt`
- **Script:** `.claude/workflows/wave13-metrics-research.js`
- **Phases:** Research (4 parallel) → Critique + propose → Adversarial verify
- **Total agents:** 6
- **Total tokens:** 329,268
- **Total tool calls:** 81
- **Wall-clock:** ~8.5 min (research dominated by web searches)

## Research outputs

| Agent | Field | Key references |
|---|---|---|
| research:ml-framework-metrics | ML framework internal-quality metrics | PyTorch HUD, JAX public_test_util, scikit-learn check_estimator, HF ModelTesterMixin, Lightning tests/strategies/, ONNX Runtime conformance vectors |
| research:paper-traceability | Paper-to-code traceability in diffusion / flow-matching repos | score_sde_pytorch, NVlabs/edm, facebookresearch/flow_matching, openai/consistency_models, openai/guided-diffusion |
| research:se-ml-reproducibility | SE research on ML reproducibility | Hutson 2018, Sculley 2015 NeurIPS "Hidden Technical Debt", Pineau et al. 2021 JMLR, Ma 2019 TSE DeepGauge, Wang 2018 ASE DeepMutation, He 2021 ASE paper-to-code reproducibility |
| research:sci-compute-metrics | Scientific-computing framework metrics | DifferentialEquations.jl, SciPy testing, NumPy assert_allclose, Hypothesis, Stan SBC, PyMC PPC, AllenNLP registry, Detectron2, airspeed-velocity |

## Critique (5 critical flaws of rev 1)

1. **A.1 "5/5 saturated; maintain"** — textbook saturation gaming; no enumerated denominator.
2. **B.1 test-count floor** — incentivises parametrised near-duplicates (line-coverage gaming).
3. **C.1 "quality > quantity"** — vague; no measurable definition.
4. **F.2 binary reproduction** — conflates three distinct concepts (NASEM 2019 / Pineau 2021); no cold-clone discipline.
5. **All hard gates live in B.2-B.4** — leaves 8 research-supported hard-gate candidates as soft "do-when-convenient"; gate strategy fragile.

## Verification outcome

`is_safe_to_ship = false`. Verdict:
> "Ship after addressing the 5 critical issues + the 4 most consequential majors."

**5 critical issues fixed in rev 2:**
1. C.6 marked HARD but only runs nightly → reclassified SOFT at PR-level, HARD at paper-writeup gate
2. A.7 100% target over-strict for existence/qualitative theorems → narrowed to "constructive content" with LL entries for non-constructive
3. E.1 target mismatch with paper-writeup gate → reconciled to ">= 50 total, >= 70% test-coupled"
4. Phase 4 gate missing C.2 → added C.2 check
5. B.5 opt-in determinism gate pitfall → flipped default (must mark deterministic OR stochastic-with-tolerance)

**4 most consequential majors fixed:**
- A.6 ambiguous "paper component" scope → defined
- F.3/F.4 deferred criteria → inlined tier criteria + 8 required Mitchell/Gebru fields
- B.8 unpinned threshold → pinned at 5%/2%
- F.5 pip-freeze noise → defined env_hash as SHA256 of specific components, NOT full pip freeze

**Other majors addressed:**
- Phase 2 → Phase 3 gate too compressed → split into Phase 2.5 intermediate
- C.6 tolerance too tight (0.05) → relaxed to 0.2 with exception process
- F.6 scope expanded (theory only → theory + integrators + schedulers + adapters)
- C.7 compute budget added (N=200 first then N>=1000)
- C.5 format defined (3 Pareto plots, >= 5 datapoints, log-scale NFE)
- Crosswalk table OLD→NEW IDs (§5)

**Deferred majors (recorded as-is in rev 2 file; would require Wave 14+ work):**
- A.4/A.5 redundancy — merged into single A.5 with sub-metrics would be cleaner; kept as-is for now
- E.4/A.4 overlap — E.4 retained as diff-job, A.4 as density target
- B.4 doctest scope (algorithmic paths vs theory checkers) — kept theory-only per Research 4 pitfall
- Missing citations with URLs — added §8 Acknowledgements but didn't URL every metric source

## Resolved gaps added

From the verifier's "unresolved_gaps" list, the most relevant were incorporated:
- Public API stability → not added (out of scope for typed-contracts framework; framework has explicit Protocol surfaces already)
- Backward-compatibility test → not added (no API stability policy needed yet)
- Continuous-benchmarking → C.6 (nightly) + F.6 (quarterly mutation) cover some of this
- Type-narrowing exhaustiveness → not added (D.2 verified runtime isinstance is close enough)
- Test isolation/independence → implicit in B.1 (acyclic gate) + B.5 (determinism gate)

The other 10+ gaps (data card, energy cost, test pyramid balance, code complexity, etc.) are deferred; framework doesn't need them yet.

## File status

- `todo/framework-internal-metrics.md` — rewritten to rev 2 with all critical + 4 major fixes applied
- This file (`todo/wave13-metrics-research-result.md`) — workflow result record
- `todo/STATUS.md` — needs update with Wave 13 status

## Out of scope

- The 4 research agents each did 6-12 web fetches; URLs and titles are preserved in the workflow output for future reference.
- No production of new metrics outside what the synthesis suggested; the verifier's "unresolved gaps" list was triaged, not all addressed.
- GATES.md unchanged (still references framework-internal-metrics.md as the authoritative source).

## Verification rerun

After applying fixes, the file should re-pass adversarial verification with:
- All 5 critical issues resolved
- 4 most consequential majors resolved
- 4 majors deferred (documented)
- 17 unresolved gaps triaged (7 accepted, 10+ deferred)

## Wave 56 close-out

Status refreshed: framework-internal-metrics.md rev 2 was the Wave 13 baseline. Wave 22 (rev 3 plan), Wave 26-29 (capability audit metrics), Wave 38 (G row update), and Wave 41-54 (composite metric layer additions for Kanzi/LineageFlow/FlowMol3) all extended the metrics spec without breaking the rev 2 contract. Last touched commit: `811ca75` (Wave 55 Agent C: Author todo/INDEX.md master entry point).