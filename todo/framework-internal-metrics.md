# Framework-internal metrics + continuous optimization plan + entry gates

**Status:** defined (2026-09-05; revision 2 — research-aligned + verification fixes)
**Owner:** framework maintainer
**Goal:** establish + continuously optimize framework-internal quality
metrics so that the framework's health is measurable **before** any model
is integrated. Provide entry gates for subsequent task progression.

Per user directive (2026-09-05):
> "我们要建立框架在接入模型之前的框架内指标，并且要有这些指标的持续优化计划以及后续任务推进的准入门槛"

Rev 2 (2026-09-05) was produced by a 6-agent ultracode (4 parallel
research + synthesis + adversarial verify); see
`todo/wave13-metrics-research-result.md` for the workflow record. This
file incorporates the verifier's 5 critical + 4 most consequential
major fixes (C.6 hard/nightly contradiction; A.7 100% over-strict for
existence theorems; E.1 target mismatch; Phase 4 missing C.2; B.5
opt-in pitfall; A.6 ambiguous scope; F.3/F.4 deferred criteria; B.8
unpinned threshold).

## 1. Metrics (definitions + current values + targets)

### A. Theory-to-implementation traceability

| ID | Definition | Current | Target | Hard? |
|---|---|---|---|---|
| A.0 | Enumerated paper-statement inventory (Thm / Lemma / Prop / Cor / Rem with paper line numbers + paper version hash) | partial | complete + re-enumerated on paper version change | n/a (input) |
| A.1 | Paper theorems (A.0 entries) with framework module/class + tests + paper-line citation in test docstring | partial | 100% of A.0 with paper-line citation in test docstring | **HARD** |
| A.2 | Paper propositions with dedicated test cases AND >= 1 must-fail fixture per proposition | 2 | 100% of A.0 propositions by Wave 14 | **HARD** |
| A.3 | Explicit theorems exposed as framework surface (dataclass + checker + tests + must-fail fixture + equation citation) | 1 | 2 by Wave 13 B (rate bound adds second) | **HARD** |
| A.4 | Per-equation citation density: fraction of functions in `adaptive_reflow/theory/` whose docstrings cite paper equation/section | 0 | >= 0.9 by Wave 14 | **HARD** |
| A.5 | Bidirectional paper-statement / code-link integrity: every paper-statement string in code resolves to A.0; every A.0 entry is referenced from >= 1 code/test docstring | unverified | 100% match | **HARD** |
| A.6 | Scope and deviation register (`docs/theory/DEVIATIONS.md` non-empty): each A.0 entry that maps to a code path under `adaptive_reflow/theory/` has either (a) >= 1 deviation entry OR (b) explicit "no deviations" declaration | no | complete coverage by Wave 13 | **HARD** |
| A.7 | Hypothesis-violation (must-fail) coverage: count of A.0 entries with >= 1 paired negative fixture; **target applies only to entries with constructive content (excludes pure existence / qualitative theorems)**, with an LL entry per non-constructive entry explaining the gap | 0 | 100% of A.0 *constructive* entries by Wave 16 | **HARD** (new entries from Wave 15 onward) |

### B. Test health

| ID | Definition | Current | Target | Hard? |
|---|---|---|---|---|
| B.1 | Acyclic gate pass (28e3bf9 + a6dffd3) | 13/13 | 13/13 | **HARD** |
| B.2 | Byte-stability gate (deterministic subset) | pass | pass | **HARD** |
| B.3 | mkdocs --strict pass | pass | pass | **HARD** |
| B.4 | Doctest execution: `pytest --doctest-modules adaptive_reflow/theory/` exits 0 | not running | pass by Wave 13 | **HARD** |
| B.5 | Determinism gate: **every test is EITHER marked `@pytest.mark.deterministic` (must produce identical output across 2 consecutive runs) OR `@pytest.mark.stochastic-with-tolerance` (must pass a relaxed check with documented atol); unmarked tests fail CI** | not running | enforced by Wave 14 | **HARD** |
| B.6 | Float-dtype coverage: numerical algorithms parametrised over float16/32/64 with parity (or explicit dtype rejection) | 0% | 100% of new code from Wave 15; 100% of public numerical algorithms by Wave 16 | **HARD** (new code); **HARD** for all (Wave 16) |
| B.7 | Property-based test coverage: fraction of public deterministic algorithm modules with >= 1 Hypothesis-style `@given` test with explicit seed pin | **0.769 (10 / 13)** | >= 0.4 by Wave 16 | no |
| B.8 | Flakiness tagging + quarantine: per-test 7-day failure-rate dashboard; **auto-quarantine at >5% 7-day failure rate; manual review at >2%** | none | dashboard live by Wave 14; 0 quarantined tests above threshold | no |
| ~~B.1 (rev 1)~~ | ~~Total test count~~ | ~~3228~~ | REMOVED — see §5 | n/a |

### C. Algorithm layer

| ID | Definition | Current | Target | Hard? |
|---|---|---|---|---|
| C.1 | Measured algorithm uplifts (in `docs/benchmark-uplifts.md`) tagged `witness` / `inequality` / `identity` (smoke-only excluded) | 36 (untagged) | >= 36 tagged; >= 70% witness/inequality/identity | no |
| C.2 | Isolation tests per uplift, with assertion-strength tag (witness/inequality/identity only; smoke-only excluded) | 0 | 36 by Wave 14 (tagged) | no |
| C.3 | Top-10 strength ranking exists, with tied accuracy-vs-NFE Pareto fronts | no | yes by Wave 14 | no |
| C.5 | Failure-mode characterisation table: **at least 3 (model, NFE-budget) Pareto plots in `docs/CONDITIONS.md`, each with >= 5 datapoints, accuracy axis = NLL or FID, NFE axis on log scale, with a Pareto-front identifier** | no | yes by Wave 14 (twodim_fm first) | no |
| C.6 | Empirical convergence-order verification: every **deterministic** FM integrator achieves its claimed global-error order within **0.2 absolute tolerance** on 3 analytic problems (linear drift, nonlinear drift, stiff); **stochastic integrators (SDE-style) instead verified under C.7 SBC**; **behind `--runslow` marker, nightly only, not per-PR** | 4/4 in-scope integrators pass (Heun order 2, RK4 order 4, Midpoint order 2, Euler order 1); 5 additional integrators excluded with documented exceptions (DOPRI5 known-broken — separate wave; DPM-Solver / DPM-Solver++ / UniPC specialised diffusion-ODE solvers; SymplecticLeapfrog symplectic energy-bound test); see `tests/test_convergence/CONVERGENCE_TARGETS.md` | 100% of public deterministic integrators by Wave 16 (nightly CI); C.6 PARTIAL at Wave 18 P1 (4/4 in-scope pass; 5 out-of-scope documented) | no (SOFT at PR-level; HARD at paper-writeup gate) |
| C.7 | Simulation-Based Calibration (SBC) for stochastic re-inference: rank histogram approximately uniform at N>=1000 samples; **behind `--runslow`; parallelisable across stochastic algorithms; N=200 first then N>=1000 if compute budget allows**; per-stochastic-algorithm compute budget tracked | 6/6 algorithms pass at N=200 (p>=0.078); 6/6 pass at N=1000 (p>=0.095): `jittered_constant_scheduler`, `adaptive_policy_driver`, `euler_maruyama_sde_step`, `sde_heun_sde_step`, `identity_dynamic_noise_bias`, `cosine_inject_noise`. The Theorem1DynamicNoiseBias (paper-quantity-driven) is verified for *structural correctness* (eps envelope closed form) but not via chi-squared SBC because the noise scale depends on the prior draw (sheet_A) and produces a boundary-bin excess that the chi-squared test cannot distinguish from genuine miscalibration. Runner: `tools/run_sbc_audit.py`; per-algorithm runtime < 0.2 s at N=1000. Reports: `verification_outputs/sbc_audit_n200.json`, `verification_outputs/sbc_audit_n1000.json` | 100% of public stochastic algorithms by Wave 18 (nightly only) | no |
| C.8 | Re-inference predictive checks (PPC analogue): FID/MMD within tolerance on pinned reference model + dataset | none | >= 1 model passes by Wave 16 | no |

### D. Adapter quality

| ID | Definition | Current | Target | Hard? |
|---|---|---|---|---|
| D.1 | Adapter line count median | ~1500 (across 18) | <= 500 by Wave 16 (shrink task) | no |
| D.2 | Adapters using abstract interfaces (SchedulerProtocol etc.) — verified at runtime (`isinstance` check) | 18/18 declared | 18/18 verified | **HARD** |
| D.3 | Adapters passing conformance tests — auto-generated conformance battery (D.5) | hand-written | 18/18 against D.5 by Wave 14 | **HARD** (after D.5 live) |
| D.4 | Pinned adapter regression vectors: fixed (seed, input, NFE) tuple per adapter, hash compared in CI | none | 18/18 by Wave 14 | **HARD** |
| D.5 | Plugin/strategy auto-generated conformance battery (single source of truth, `tests/test_adapters/conformance_battery.py`) | none | live by Wave 14; per-check pass/fail aggregated | **HARD** (when live) |

### E. Documentation

| ID | Definition | Current | Target | Hard? |
|---|---|---|---|---|
| E.1 | CLM claim count in `docs/CLAIMS.md` — split into **total count** + **test-coupled count** | 47 total, ~0 test-coupled | **>= 50 total, >= 70% test-coupled by Wave 16** | **HARD** (test-coupled floor; reconciled with paper-writeup gate) |
| E.2 | Docs cross-referencing >= 1 paper theorem, machine-checkable via A.5 | ? | >= 0.9 by Wave 14 | **HARD** |
| E.3 | CONSOLIDATED_RESULTS sections per integrated model | 7+ | >= 10 by Wave 16 | no |
| E.4 | Doc-builder diff job: per-equation citation check fails if a refactor drops paper equation/section reference from a public function | not running | live by Wave 13 | **HARD** |

### F. Reproducibility

| ID | Definition | Current | Target | Hard? |
|---|---|---|---|---|
| F.1 | Honest negative results documented, with root-cause classification | 3 (2D RF, FlowMol3 CTMC, LineageFlow BLOCKED) | >= 3 (don't lose); >= 5 by Wave 16 | no |
| F.2 | Three-way reproduction rate (from cold clone, env_hash pinned): REPRODUCED / PARTIAL / NOT_REPRODUCED; measured from a fresh `git clone` + pinned virtualenv + `env_hash.txt` capture (NOT from warm re-run) | 5/8 (REPRODUCED, unclassified) | >= 6/8 REPRODUCED by Wave 14; all 8 classified | **HARD** (cold-clone discipline) |
| F.3 | ACM-style artifact-badging tier per integrated model (**Available / Functional / Reusable / Reproduced** — explicit criteria in `docs/ARTIFACT_TIERS.md` which must exist by Wave 14) | none | >= 1 "Reproduced" by Wave 16; >= 50% at "Reusable" or above | no |
| F.4 | Model-card completeness (Mitchell/Gebru schema): fraction of **8 required fields** populated per model — **(1) intended use, (2) training data, (3) evaluation data, (4) quantitative analyses, (5) ethical considerations, (6) caveats, (7) paper-equation provenance, (8) known failure modes** | none | >= 0.8 per model (>= 7/8 fields) by Wave 16 | no |
| F.5 | Environment-fingerprint reproducibility: `env_hash.txt` shipped with every reproduction; `env_hash = SHA256( requirements-lock.txt + python --version + torch.__version__ + torch.version.cuda + adapter-specific dependency versions )`; **NOT full pip freeze** (sensitive to install order, --extra-index-url, OS package mgr artifacts) | none | 100% of reproductions by Wave 14; mismatched-hash auto-classified PARTIAL or NOT_REPRODUCED | **HARD** |
| F.6 | ML-aware mutation score (MuNN/DeepMutation operators, quarterly): **scope = theory checkers + integrators + schedulers + adapters (one representative per family); report per-subsystem scores so theory-checker score doesn't mask algorithmic gaps** | none | >= 0.6 aggregate AND >= 0.4 per-subsystem by Wave 18 | no |

## 2. Continuous optimization plan

| Metric group | Cadence | Owner | Improvement path |
|---|---|---|---|
| A.0 / A.1 / A.4 / A.5 / A.6 / A.7 | per wave (when theory work happens) | Claude | enumerated inventory `docs/theory/PAPER_INVENTORY.md`; bidirectional link checker `scripts/check_paper_links.py`; A.7 must-fail fixture generator |
| A.2 / A.3 | per wave | Claude | paired must-fail fixtures + equation citations |
| B.1-B.8 | per wave verify (must not regress) | Claude | pytest + mkdocs + `--doctest-modules` + determinism-gate + dtype-parametrize + property-based tests + flakiness dashboard in `G-MASTER-PHASE-1` verify step; per Research 1 pitfall, test-count floor (B.1 rev 1) REMOVED — count-based metrics incentivise parametrised near-duplicates |
| C.1-C.8 | per algorithm-improvement wave | Claude | tasks A/B/C/D in `todo/algo-improvement-*.md`; C.6 behind `--runslow`; C.7 nightly only; C.8 PPC pattern from PyMC/arviz |
| D.1-D.5 | per model integration | Claude | Phase 3 work + shrink-adapters task (D.1); D.5 auto-battery is the single source of truth (Research 1: scikit-learn `check_estimator` + Lightning `tests/strategies/`) |
| E.1-E.4 | per wave | Claude | docs updates in `docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`; E.4 enforces per-equation docstring citations via diff job |
| F.1-F.6 | per reproducibility-audit wave | Claude | Wave N reproducibility audit; F.2 3-way classification; F.6 quarterly (Research 1 pitfall: full mutation testing per-PR is prohibitively expensive) |

**Reporting cadence:**
- Per wave: hard-gate metrics (A.1, A.2, A.3, A.4, A.5, A.6, A.7 [new entries], B.1-B.6, D.2-D.5 [when live], E.4, F.2-cold-clone, F.5) verified; recorded in wave verify step.
- Per model integration: D.* updated for the new adapter (D.4 vectors + D.5 battery + F.4 model card + F.5 env hash + F.3 tier).
- Per 4 waves: full metrics audit; appendix in `todo/STATUS.md` "framework health" section.
- Per phase transition: full metrics report BEFORE gate verification.

**Where metrics live:**
- A.0: `docs/theory/PAPER_INVENTORY.md` (with paper version hash)
- A.1-A.7: `adaptive_reflow/theory/checkers.py` + `tests/test_theory/` + `tests/test_theory/negative/` (A.7) + `docs/theory/DEVIATIONS.md` (A.6)
- B.1-B.8: pytest + mkdocs + `--doctest-modules` + determinism-gate + flakiness dashboard outputs (CI-grade)
- C.1-C.8: `docs/benchmark-uplifts.md` + `docs/CONDITIONS.md` + `tests/test_convergence/` (C.6) + `tests/test_sbc/` (C.7) + `tests/test_ppc/` (C.8)
- D.1-D.5: `wc -l adaptive_reflow/adapters/*.py` + `tests/test_adapters/conformance_battery.py` (D.5) + `regression-vectors/` (D.4)
- E.1-E.4: `docs/CLAIMS.md` + `docs/CONSOLIDATED_RESULTS.md` + diff job script
- F.1-F.6: `todo/lessons-learned.md` + `docs/reproducibility_record.md` + `env_hash.txt` (F.5) + `docs/ARTIFACT_TIERS.md` (F.3) + `docs/models/M.model_card.md` (F.4) + quarterly mutation report (F.6)

**Process metric (not a content metric):** per-shard CI dashboard with last-green timestamp + 7-day failure rate, exposed on internal URL (Research 1: PyTorch HUD pattern). Living dashboard; not gated as a content metric.

## 3. Entry gates for subsequent task progression

These gates sit **in front of** the phase transitions in `LOOP.md` and
**between algorithm-improvement tasks**. They are independent of the
per-model lifecycle gates in `GATES.md`.

### Gate: framework ready for Phase 2 (per-model analysis)

**Pre-condition:** G-MASTER-PHASE-1 passed AND ALL of:
- [ ] **A.0** inventory complete + paper version hash pinned
- [ ] **A.1 = 100%** of A.0 with paper-line citation in test docstring (HARD)
- [ ] **A.2** = each proposition has >= 1 must-fail fixture (HARD)
- [ ] **A.4 >= 0.9** per-equation citation density (HARD)
- [ ] **A.5 = 100%** bidirectional link integrity (HARD)
- [ ] **A.6 = yes** (deviation register complete coverage) (HARD)
- [ ] **B.1, B.2, B.3, B.4, B.5** all pass (HARD)
- [ ] C.1 >= 36 with >= 70% tagged witness/inequality/identity
- [ ] **D.2 = 18/18 verified** (runtime isinstance, not just declared) (HARD)
- [ ] **D.5** conformance battery exists (even if not yet 18/18 pass)

**Pass:** yes → Phase 2 can start (per-model analysis loop)
**Fail:** fix the failing metric; cannot move to Phase 2

### Gate: framework ready for Phase 2.5 (pre-glue intermediate)

**Pre-condition:** Phase 2 file (`todo/models/M.md`) for the model exists AND:
- [ ] **A.3 >= 1** with must-fail fixture (A.7) (HARD)
- [ ] **B.1, B.2, B.3, B.4, B.5** all pass (HARD)
- [ ] **D.5** conformance battery live (HARD)
- [ ] **F.5** env-fingerprint pipeline shipped (HARD)

This is the intermediate gate that allows per-model analysis to begin
before the full Phase 3 infrastructure is complete. Per-model glue work
on the model-under-integration can start once Phase 2.5 passes for
*that specific model*, even if other models have not yet passed.

### Gate: framework ready for Phase 3 (per-model glue)

**Pre-condition:** Phase 2.5 passed AND:
- [ ] **D.3 = 18/18** against D.5 auto-battery (HARD)
- [ ] **D.4** pinned regression vectors live for the model under integration (HARD)

### Gate: framework ready for Phase 4 (per-model comparison)

**Pre-condition:** Phase 3 complete AND:
- [ ] **A.3 >= 2** with must-fail fixtures (HARD)
- [ ] **B.1, B.2, B.3, B.4, B.5** all pass (HARD)
- [ ] **D.5** auto-battery 18/18 pass (HARD)
- [ ] **D.4** pinned regression vectors for the model under integration (HARD)
- [ ] **C.2 = 36** with assertion-strength tags (witness/inequality/identity only) — same as the Wave 14 metric target; reconciled per rev 2 verification
- [ ] **F.4** model-card completeness >= 0.8 for the model under integration
- [ ] **F.5** env-fingerprint shipped for the model under integration (HARD)

### Gate: framework ready for paper-writeup

**Pre-condition:** Phase 4 done for >= 3 models AND:
- [ ] **A.3 >= 2** with must-fail fixtures (HARD)
- [ ] **C.3 = yes** + **C.6** convergence-order verified for all public deterministic integrators (HARD at this gate, SOFT at PR-level per §1)
- [ ] **C.5 = yes** + tied to **F.2** 3-way reproduction
- [ ] **E.1 >= 50** total AND >= 70% test-coupled (HARD test-coupled floor)
- [ ] **F.1 >= 4** + **F.2 (3-way) >= 6/8 REPRODUCED** + all 8 classified (HARD cold-clone)
- [ ] **F.3** ACM-tier declared for all integrated models
- [ ] **F.6** mutation score >= 0.6 aggregate AND >= 0.4 per-subsystem

### Gate: algorithm-improvement A → B

**Pre-condition:** G-ALGO-PLANAR-BL passed AND:
- [ ] **A.3 >= 1** with must-fail fixture (A.7) (HARD)
- [ ] **B.1, B.2, B.3, B.4, B.5** all pass (HARD)
- [ ] **A.6** deviation register complete coverage (HARD)

### Gate: algorithm-improvement B → C

**Pre-condition:** G-ALGO-RATE-BOUND passed AND:
- [ ] **A.3 = 2** with must-fail fixtures (A.7) (HARD)
- [ ] `docs/theory/theorem1_rate_bound.md` exists with paper equation citation (A.4)
- [ ] **B.1, B.2, B.3, B.4, B.5** all pass (HARD)
- [ ] **A.6** includes the rate bound's known approximations (HARD)

### Gate: algorithm-improvement C → D

**Pre-condition:** G-ALGO-UPLIFT-ISOLATION passed AND:
- [ ] **C.2 = 36** with assertion-strength tag (witness/inequality/identity only; smoke-only excluded)
- [ ] **C.3 = yes** (top-10 ranked, Pareto-style)
- [ ] **C.6** convergence-order verified for >= 1 deterministic integrator family (HARD at this gate)
- [ ] **B.1, B.2, B.3, B.4, B.5** all pass (HARD)
- [ ] **A.7** must-fail fixtures for every theorem surface referenced in
      the algorithm-improvement B deliverable (`docs/theory/theorem1_rate_bound.md`)
      AND any additional A.0 entry surfaced during task C work (HARD); each
      missing fixture blocks with an explicit "missing must-fail fixture
      for <A.0 entry>" error

## 4. Acceptance gate

**Gate name:** `G-FRAMEWORK-HEALTH` (defined here)

**Pre-condition:** this file exists with current values populated
**Pass conditions (per wave verify):**
- [ ] All hard-gate metrics pass: A.1, A.2, A.3 (with must-fail fixtures), A.4, A.5, A.6, A.7 (new entries), B.1-B.6, D.2, D.3 (after D.5 live), D.4 (when applicable), D.5, E.1 (test-coupled floor), E.4, F.2 (cold-clone), F.5
- [ ] No soft-gate metric has regressed without an LL entry explaining why
- [ ] `todo/STATUS.md` "framework health" section updated with current snapshot

**Block rule:** if any hard gate fails, the next wave is BLOCKED. Append
to `lessons-learned.md` with the failure mode + fix.

## 5. Removed metrics (with rationale)

| ID (rev 1) | Status | Reason |
|---|---|---|
| B.1 (rev 1) "Total test count" | REMOVED as gate | Per Research 1 + Research 2: count-based metrics incentivise parametrised near-duplicates (line-coverage gaming); test count is now informational only in `B.1` table (the renamed slot is the acyclic gate). Property-based coverage (B.7) and assertion-strength tags (C.1) replace this as the actual test-quality signal. |
| F.2 (rev 1) "5/8 reproduced" | MERGED into F.2 (rev 2) | Per Research 3 NASEM 2019 / Pineau et al. 2021: binary reproduction conflates three distinct concepts. Replaced with 3-way classification (REPRODUCED / PARTIAL / NOT_REPRODUCED) and cold-clone discipline. |
| A.1 (rev 1) "5/5 saturated; maintain" | MERGED into A.1 (rev 2) | Self-selected numerator with no denominator is exactly the saturation-gaming anti-pattern Research 2 warns about. Replaced with 100% of an *enumerated* A.0 inventory + paper-line citation requirement; A.0 must be re-enumerated on paper version change. |

### Crosswalk: OLD IDs → NEW IDs (for diff with rev 1)

| OLD ID (rev 1) | NEW ID (rev 2) | Meaning shift |
|---|---|---|
| B.1 | (removed as gate; see §5) | test-count floor removed (anti-pattern) |
| B.2 | B.1 | acyclic gate (unchanged meaning, new position) |
| B.3 | B.2 | byte-stability (unchanged meaning, new position) |
| B.4 | B.3 | mkdocs --strict (unchanged meaning, new position) |
| F.2 | F.2 (rewritten) | binary → 3-way + cold-clone (substantive change) |
| A.1 | A.1 (rewritten) | self-selected "5/5" → 100% of enumerated A.0 |

## 6. Initial current-value audit (2026-09-05)

All 9 audits completed in Wave 14. Full report: `docs/baseline-audit-report.md` (524 lines). Summary:

| Metric | Current | Rev 2 target | Gap | Status |
|---|---|---|---|---|
| A.0 | 20 paper statements + 7 gaps documented; 141 paper-reference hits | parity | none blocking (G4 = Task #360, G7 = Prop 6 positive dir) | **MET** |
| A.4 | 0.171 (14/82 public functions annotated) | ≥ 0.90 | -0.729 (~+60 annotated functions) | **GAP** |
| A.7 | 75% strict / 87.5% broad | 100% constructive | -25pp strict | **GAP** |
| B.4 | vacuous pass (0 doctests collected) | 0 failures | MET vacuously; add doctests + CI wire | **MET vacuous** |
| D.3 | 226/226 = 100% hand-written (13 adapter files) | 18/18 against D.5 | need D.5 (MISSING) | **GAP** |
| D.5 | MISSING | live by Wave 14 | 1 file missing | **GAP** |
| E.2 | 0.571 (16/28 docs) | ≥ 0.9 | -0.329 (~+9 docs) | **GAP** |
| F.2 | 4/8 REPRODUCED, 1/8 PARTIAL, 3/8 NOT_REPRODUCED | ≥ 6/8 REPRODUCED | -2 rows | **GAP** |
| F.5 | MISSING (4 artifacts: scripts/capture_env_hash.py, requirements-lock.txt, env_hash.txt, per-adapter dep list) | HARD gate | 4 artifacts missing + uv drift | **GAP (HARD gate blocker)** |

### Next-action priorities (from audit report)

1. **F.5 env_hash infrastructure** (HARD gate blocker) → `todo/algo-improvement-env-hash.md`
2. **D.5 conformance battery** → `todo/algo-improvement-conformance-battery.md`
3. **A.4 + A.7 + B.4 paper-traceability hardening** → `todo/algo-improvement-traceability-hardening.md`
4. **F.2 flip NOT_REPRODUCED → REPRODUCED** → `todo/algo-improvement-f2-reproduction.md`

## 7. Out of scope

- Cross-framework comparison benchmarks (e.g., vs diffusers / torchcfm throughput) — separate task.
- Per-model metrics (those are in `todo/models/M.md` §F).
- Theoretical analysis of WHY the framework helps at certain noise levels (the failure-mode characterisation is empirical; a separate task could derive bounds from the rate bound theorem).
- Per-PR mutation testing (F.6 is quarterly by design; per-PR mutation testing is prohibitively expensive per Research 1 pitfall).

## 8. Acknowledgements (research sources, rev 2)

This revision was produced by a 6-agent ultracode. Key references:

- **ML frameworks** (PyTorch HUD, JAX public_test_util, scikit-learn
  `check_estimator`, HuggingFace ModelTesterMixin, Lightning
  `tests/strategies/`, ONNX Runtime conformance vectors) — see
  `todo/wave13-metrics-research-result.md` §"Research outputs"
- **Paper-code traceability** (score_sde_pytorch, NVlabs/edm,
  facebookresearch/flow_matching, openai/consistency_models,
  openai/guided-diffusion) — same source
- **SE research** (Hutson 2018 Science; Sculley 2015 NeurIPS "Hidden
  Technical Debt"; Pineau et al. 2021 JMLR NeurIPS reproducibility
  checklist; Ma et al. 2019 TSE DeepGauge; Wang et al. 2018 ASE
  DeepMutation; He et al. 2021 ASE paper-to-code reproducibility)
- **Scientific computing** (DifferentialEquations.jl test_convergence;
  SciPy testing; NumPy assert_allclose; Hypothesis; Stan SBC; PyMC PPC;
  AllenNLP registry; Detectron2 multi-config; airspeed-velocity
  benchmarking)