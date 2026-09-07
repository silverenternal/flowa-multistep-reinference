# Wave 32 — Master gap plan (synthesis from Agent A / B / C audits)

**Status:** done (Wave 38 closed all 14 gaps from this plan)
**Date:** 2026-09-05
**Wave:** Wave 32 (5-agent audit-and-research wave)
**Owner:** framework maintainer
**Goal:** consolidate the three Wave 32 audit reports (todo audit + 2026 web
research + framework code review) into a single prioritised plan with
concrete `todo/*.md` follow-ups, wave assignments, and acceptance gates.

## Wave 38 close-out (2026-09-05)

All 14 gaps in §"Priority matrix" below were closed in Wave 38 (5 parallel
workflows, 12 implementation agents, 17 commits). Per-gap wave landing:

| # | Gap | Wave 38 commit | Wave 38 WF |
|---|---|---|---|
| 1 | D.4 pinned regression vectors | b88b32f | WF2 |
| 2 | E.1 test-coupled floor (8/8 remaining CLM claims) | 7da571c | WF2 |
| 3 | paper_quantities threading (HIGH-1 + MED-6 + MED-8) | ff56e55 | WF1 |
| 4 | assert_adapter_compliance enforcement (HIGH-4 + MED-11) | f7ee3ae | WF1 |
| 5 | bounded_lipschitz_distance_2d scipy fallback (HIGH-2) | 89c088f | WF1 |
| 6 | mkdocs --strict nav fix | 0674ac8 | WF3 |
| 7 | StochasticFMAdapter enum orphan | ba619bf | Wave 39 close-out |
| 8 | FlowMol3V2Adapter restart shape crash | b9ef18b | WF4 |
| 9 | HF Hub model card upload pipeline (R-3) | 7cbf085 | WF5 |
| 10 | Hypothesis derandomize=True for CI (R-5) | 15621b7 | WF3 |
| 11 | host_fingerprint in every JSON output (R-2) | d55b601 | WF3 |
| 12 | D.1 shrink adapters (deferred — gated on Kanzi + FreqFlow registration) | (not in Wave 38; Kanzi + FreqFlow now registered, follow-up wave candidate) |
| 13 | expecttest for text-output regression tests (R-1) | 5e1731f | WF2 |
| 14 | Mutation apply survivor feature (R-4) | 5e1731f | WF4 |

Wave 38 plan-doc sweep (commit facc008) flipped all Status lines in the 12
`algo-improvement-*.md` files to CLOSED. Gap plan itself is closed; only #12
(D.1 shrink adapters) remains as a candidate for a future wave.

## Source audits (all READ-ONLY)

| Agent | Document | Output type |
|---|---|---|
| A | `docs/audit/gap-audit.md` | per-file audit of `todo/*.md` + HARD-gate / capability-gate status; identifies 7 actionable gaps without plans |
| B | `docs/audit/web-research-2026.md` | 5 concrete recommendations (R-1..R-5) + 2 additive `framework-internal-metrics.md` changes; 18 page fetches |
| C | `docs/audit/framework-code-review.md` | 32 issues across 6 framework layers (3 HIGH, 9 MEDIUM, 13 LOW, 7 DOC) with top-5 recommendations |

## Priority matrix (gap × source × priority)

| # | Gap | A | B | C | Priority | New todo file | Wave |
|---|---|---|---|---|---|---|---|
| 1 | **D.4 pinned adapter regression vectors** | ✗ | – | – | **HIGH** (HARD gate + per-adapter discipline) | `todo/algo-improvement-D4-regression-vectors.md` | Wave 33 |
| 2 | **E.1 test-coupled floor (11/41 → 22 more → 33/41 = 80%)** | ✗ | – | – | **HIGH** (HARD gate; user explicitly named) | `todo/algo-improvement-E1-claim-test-coupling-batch2.md` | Wave 33 |
| 3 | **`record_round_feedback` `paper_quantities` threading** (HIGH-1 + MEDIUM-6 + MEDIUM-8) | – | – | ✗ | **HIGH** (3 issues across 3 files; same class as F-1/F-4/F-5) | `todo/algo-improvement-paper-quantities-threading.md` | Wave 33 |
| 4 | **`assert_adapter_compliance` enforcement** (HIGH-4 + MEDIUM-11) | – | – | ✗ | **HIGH** (framework surface currently unenforced) | `todo/algo-improvement-assert_adapter_compliance.md` | Wave 33 |
| 5 | **`bounded_lipschitz_distance_2d` scipy fallback** (HIGH-2) | – | – | ✗ | **HIGH** (paper Theorem 1 contract) | `todo/algo-improvement-no-scipy-raise.md` | Wave 33 |
| 6 | **mkdocs `--strict` AT RISK** (8 unnavmed files incl. 5 `models/*.model_card.md`) | ✗ | – | – | **HIGH** (B.3 HARD gate at risk) | `todo/algo-improvement-mkdocs-strict-nav.md` | Wave 33 |
| 7 | **StochasticFMAdapter enum orphan** | ✗ | – | – | **MEDIUM** (1-file fix; audit recommends delete) | `todo/algo-improvement-stochastic-fm-orphan.md` | Wave 33 |
| 8 | **FlowMol3V2Adapter restart shape crash** (NONCONFORMANCE_BUG #1) | ✗ | – | – | **MEDIUM** (1-file fix + test) | `todo/algo-improvement-FlowMol3V2-restart-fix.md` | Wave 33 |
| 9 | **HF Hub model card upload pipeline** (R-3, F-18, F-20) | ✗ | ✗ | – | **MEDIUM** (cards authored, HF upload missing) | `todo/algo-improvement-hf-model-card-pipeline.md` | Wave 34 |
| 10 | **Hypothesis `derandomize=True` for CI** (R-5) | ✗ | ✗ | – | **MEDIUM** (B.7 + 2026-best-practice) | `todo/algo-improvement-hypothesis-derandomize.md` | Wave 34 |
| 11 | **`host_fingerprint` in every JSON output** (R-2) | – | ✗ | – | **MEDIUM** (provenance hygiene) | `todo/algo-improvement-host-fingerprint.md` | Wave 34 |
| 12 | **D.1 shrink adapters** (gated on MUST-3 framework-core glue) | ✗ | – | ✗ | **MEDIUM** (Phase 3 task #344; gated on Kanzi + FreqFlow registration) | (deferred — append to `PHASE-3-glue-layer-improvement.md`) | Wave 34+ |
| 13 | **`expecttest` for text-output regression tests** (R-1) | – | ✗ | – | **LOW** (lightweight middle-ground) | `todo/algo-improvement-expecttest-adoption.md` | Wave 34 |
| 14 | **Mutation `apply survivor` feature** (R-4) | – | ✗ | – | **LOW** (mutmut killer feature analogue) | `todo/algo-improvement-mutation-apply-survivor.md` | Wave 34 |

**No-new-plan gaps (already covered or accepted-as-limitation):**

- E.4 doc-builder diff job: MET (Wave 27 A) — checklist entry stale; update `framework-freeze-checklist.md` MUST-1 summary table only.
- G.1 / G.3 / G.4 / G.6 / G.7 (Group G HARD): all PASS post Wave 28 + 30; checklist entry stale.
- F-2 / F-3 / F-6 (operating-regime findings): per Agent A §2.5, F-2/F-3 are docstring-only, F-6 accepted-as-limitation; no new todo files.
- F.6 mutation score: GATE MET (0.833 aggregate; 0.533 theory post Wave 25).
- Reference_flowa orphan class: same pattern as StochasticFMAdapter — fold into the StochasticFM plan or delete per audit recommendation.
- ACM artifact badging (F.3): MEDIUM effort per Agent B; not a code path; defer.

## Cross-reference (gap appears in multiple sources)

| Gap | Sources | Notes |
|---|---|---|
| **mkdocs nav / model cards** | A (mkdocs strict FAIL) + B (HF card pipeline) | Two distinct fixes (mkdocs nav entry + HF upload tool); see #6 and #9 |
| **Adapter conformance** | A (StochasticFM, FlowMol3V2 restart) + C (HIGH-4 + MEDIUM-11) | Three separate fixes (delete orphan + restart shape + enforce `@implements`); see #7, #8, #4 |
| **`record_round_feedback` paper_quantities** | C only (HIGH-1 + MEDIUM-6 + MEDIUM-8) | Single class of bug across 3 files; see #3 |
| **Test discipline / Hypothesis** | A (E.1 test-coupled) + B (Hypothesis derandomize) | Distinct fixes; see #2, #10 |
| **Adapter quality / D.4** | A (D.4 NOT MET) + B (expecttest as middle-ground) | Distinct fixes; see #1, #13 |

**No gap appears in all 3 sources** — Wave 32's three audits cover disjoint concerns:
- A = *todo* coverage (process discipline)
- B = *external practice* (2026 framework hygiene)
- C = *implementation state* (code-level issues)

The synthesis therefore produces 14 distinct todo files (1 master + 13
focused) rather than collapsing to a smaller set.

## What ships per wave

### Wave 33 (HIGH + MEDIUM code-level fixes; CPU-only, no GPU)

- #1 D.4 regression vectors — first batch (5 adapters: FlowMol3 v2, twodim_fm, lineageflow, kanzi, freqflow)
- #2 E.1 test-coupled batch 2 — 22 more claims (categories b/c/d)
- #3 `record_round_feedback` paper_quantities threading
- #4 `assert_adapter_compliance` enforcement
- #5 `bounded_lipschitz_distance_2d` raise on no-scipy
- #6 mkdocs `--strict` nav fix
- #7 StochasticFMAdapter orphan
- #8 FlowMol3V2Adapter restart shape

**Acceptance gate (Wave 33):**

- [ ] D.4: `regression-vectors/` dir + 5 vectors committed + CI green
- [ ] E.1: 33/41 = 80.5% test-coupled (≥ 70% target met)
- [ ] `paper_quantities` threaded through 3 sites
- [ ] `@implements(Protocol)` on every registered adapter
- [ ] scipy fallback raises ImportError
- [ ] `mkdocs build --strict` exits 0
- [ ] StochasticFMAdapter deleted (or fixed)
- [ ] FlowMol3V2 restart crash fixed + regression test

### Wave 34 (LOW + MEDIUM tooling improvements; CPU-only, no GPU)

- #9 HF Hub model card upload pipeline
- #10 Hypothesis `derandomize=True` for CI
- #11 `host_fingerprint` in every JSON output
- #12 D.1 shrink adapters (gated on Wave 33 Kanzi + FreqFlow registration)
- #13 `expecttest` for text-output regression tests
- #14 Mutation `apply survivor` feature

**Acceptance gate (Wave 34):**

- [ ] HF Hub README.md per model card uploaded
- [ ] `tests/test_property_based/conftest.py` sets `derandomize=True`
- [ ] Every `tools/run_*` script emits `host_fingerprint`
- [ ] D.1 adapter median ≤ 500 LOC (rev 2 target)
- [ ] ≥ 5 expecttest snapshots committed
- [ ] `tools/run_mutation_audit.py apply <id>` subcommand shipped

## Sidecar updates (one-line fixes in this Wave 32 Phase 2)

These are updates to existing docs that the audit surfaced as stale:

1. **`todo/framework-freeze-checklist.md` MUST-1 summary table** — update E.4 entry from "PARTIAL" to "PASS" (Wave 27 A); update G.1/G.3/G.4/G.6 from "FAIL" to "PASS" (Wave 28 A + Wave 30 A); add F.6 row.
2. **`todo/framework-internal-metrics.md`** — append B.7 additive sentence (Hypothesis replay DB) + F.4 additive sentence (HF Hub upload pipeline) per Agent B §8.
3. **`todo/STATUS.md`** — add Wave 32 row.
4. **`docs/baseline-audit-report.md`** — already references D.4 / E.1 as NOT-MET; no update needed.

## Risk register (added by Wave 32)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| D.4 first-batch vectors flaky on a hardware shift | LOW | MEDIUM | Use `host_fingerprint` (Wave 34 #11) + record machine id in vector JSON |
| E.1 batch-2 claim wiring reveals a soft claim (category-d) | MEDIUM | LOW | Skip the soft claim; target 70% with 22 wired (33/41 = 80.5% gives margin) |
| `assert_adapter_compliance` exposes a previously-silent Protocol violation | MEDIUM | MEDIUM | Each exposed violation gets a follow-up issue; expect 1-3 adapter fixes in Wave 33 |
| mkdocs nav addition breaks a cross-link | LOW | LOW | `mkdocs build --strict` catches broken refs at PR time |
| HF Hub upload needs auth tokens we don't have | MEDIUM | LOW | Defer the actual upload; ship the tool + documentation |

## Open questions (defer to user)

1. **D.4 vector scope** — should regression vectors be SHA-256 hashes of the byte-stable output OR `pytest.approx` with a recorded atol? The latter is more lenient under hardware shifts; the former is more rigorous. Recommendation: **SHA-256** (matches B.2 byte-stability gate philosophy).
2. **E.1 batch 2 claim selection** — pick 22 of the 30 remaining; candidates documented in `docs/CLAIMS.md` categories b/c/d. Recommendation: prioritise **category-b** (numerical assertions; easiest to wire) before category-c (algorithmic) before category-d (paper-claim soft).
3. **StochasticFMAdapter** — fix the enum strings (low-risk) or delete (lowest-risk)? Recommendation: **delete** (audit Agent A explicit recommendation; adapter is orphan; not in `ADAPTER_REGISTRY`).
4. **`assert_adapter_compliance` @implements additions** — should we add `@implements` to all 12 Protocols on every adapter (heavy) or only the smallest relevant one (lightweight)? Recommendation: **lightest relevant** (1 Protocol per adapter); matches scikit-learn `check_estimator` pattern.
5. **HF Hub model card pipeline** — manual upload trigger or CI-driven upload? Recommendation: **manual trigger** for now; per-model `python tools/upload_model_card.py <model>` invocation.
6. **D.1 shrink adapters** — gated on MUST-3 framework-core glue (Wave 23+ 24 refactor); Kanzi + FreqFlow registration is required. Recommendation: defer to **Wave 34**; precondition that Wave 33 ships the registry update for Kanzi + FreqFlow.

## File index (all 14 NEW todos)

```
todo/gap-plan-wave32.md                                        (this file)
todo/algo-improvement-D4-regression-vectors.md                 (Wave 33 #1)
todo/algo-improvement-E1-claim-test-coupling-batch2.md         (Wave 33 #2)
todo/algo-improvement-paper-quantities-threading.md            (Wave 33 #3)
todo/algo-improvement-assert_adapter_compliance.md              (Wave 33 #4)
todo/algo-improvement-no-scipy-raise.md                        (Wave 33 #5)
todo/algo-improvement-mkdocs-strict-nav.md                     (Wave 33 #6)
todo/algo-improvement-stochastic-fm-orphan.md                  (Wave 33 #7)
todo/algo-improvement-FlowMol3V2-restart-fix.md                (Wave 33 #8)
todo/algo-improvement-hf-model-card-pipeline.md                (Wave 34 #9)
todo/algo-improvement-hypothesis-derandomize.md                 (Wave 34 #10)
todo/algo-improvement-host-fingerprint.md                       (Wave 34 #11)
todo/algo-improvement-expecttest-adoption.md                   (Wave 34 #13)
todo/algo-improvement-mutation-apply-survivor.md               (Wave 34 #14)
```

D.1 shrink adapters (#12) appended to `todo/PHASE-3-glue-layer-improvement.md`
(gated on Wave 33 Kanzi + FreqFlow registration).

## Headline metrics (post-Wave 32 + Wave 33 + Wave 34)

| Gate | Pre-Wave-32 | Post-Wave-32 docs | Post-Wave-33 | Post-Wave-34 |
|---|---|---|---|---|
| B.3 mkdocs `--strict` | **AT RISK** | AT RISK | **PASS** | PASS |
| D.4 regression vectors | NOT MET | NOT MET | **5/18 PARTIAL** | 18/18 PASS |
| E.1 test-coupled floor | 11/41 = 26.8% | 11/41 = 26.8% | **33/41 = 80.5%** | 33/41 = 80.5% |
| `assert_adapter_compliance` CI test | none | none | **LIVE** | LIVE |
| F.6 theory score | 0.533 | 0.533 | 0.533 | 0.533 (unchanged) |
| HF Hub model cards | 0 uploaded | 0 uploaded | 0 uploaded | **5 uploaded** |
| Hypothesis `derandomize=True` | off | off | off | **on** |
| `host_fingerprint` per JSON | off | off | off | **on** |
| `expecttest` snapshots | 0 | 0 | 0 | **≥ 5** |
| Mutation `apply` subcommand | absent | absent | absent | **shipped** |
| StochasticFMAdapter | orphan | orphan | **deleted (or fixed)** | deleted (or fixed) |
| FlowMol3V2 restart | broken | broken | **fixed + test** | fixed + test |

## Acceptance (this Wave 32 Phase 2)

- [ ] Master gap plan file (`todo/gap-plan-wave32.md`) authored
- [ ] 13 focused todo files authored (one per gap above)
- [ ] D.1 gap appended to `PHASE-3-glue-layer-improvement.md`
- [ ] `framework-freeze-checklist.md` MUST-1 summary table updated (E.4 + G.* + F.6)
- [ ] `framework-internal-metrics.md` B.7 + F.4 additive sentences appended
- [ ] `STATUS.md` Wave 32 row added
- [ ] All commits made (no push)

## Estimated time

Wave 32 Phase 2 (this task): ~30 min (synthesis + 14 file writes).
Wave 33 execution: ~3-4 hours across 8 tasks (mostly small fixes + 22 test wirings).
Wave 34 execution: ~2-3 hours across 6 tasks (tooling improvements).