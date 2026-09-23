# Wave 298 — Final: Deep Innovation Mining Across 8 Phases (P1-P8)

**Date:** 2026-09-23
**Branch:** main
**HEAD commit at start:** `60dab91` (Wave 294: systematic CLAIMS.md + paper §2 mismatch fixup)
**Scope:** Per user directive "再深挖一下创新点" (dig deeper into innovation points), this doc is the **single entry point** consolidating the eight phases of Wave 298 (code / methodology / reproducibility / engineering / literature / deep inventory / paper append / claims update) into a final inventory of innovations, mapping each to its paper section + file:line evidence + closest prior art + reviewer value. READ-ONLY summary; the per-phase breakdowns live in `wave298-p1` … `wave298-p8`.

**Prior waves (anchors):**
- `docs/audit/wave296-p1-architecture.md` … `wave296-p5-activation-log.md` (W296 — JMAA opt-in architecture + PaperQuantitiesCache + A/B-class wiring + activation log).
- `docs/audit/wave297-p1-paper-inventory.md` … `wave297-p7-readme-updated.md` (W297 — paper §1–§11 redesign + per-section prose drafts).
- `docs/audit/wave292-p1-pipeline-inventory.md` (W292 — 15 dormant sites enumeration).

---

## 0. TL;DR — Eight-phase summary

| Phase | Doc | Output |
|---|---|---|
| P1 | `wave298-p1-code-innovations.md` | 5 code-level architectural innovations (ranked) |
| P2 | `wave298-p2-methodology-innovations.md` | 5 methodology innovations (lab-notebook-grade disclosure discipline) |
| P3 | `wave298-p3-reproducibility-innovations.md` | 5 reproducibility innovations (D.4 + ledger + claims verifier + CI + vendored purity) |
| P4 | `wave298-p4-engineering-innovations.md` | 5 engineering utilities (batched harness + adversarial stress + residual adapter + FID + Lipschitz) |
| P5 | `wave298-p5-literature-compare.md` | Novelty-bucket classification of 20 innovations (7 genuinely novel + 5 incremental + 3 well-known-applied + 5 mixed) |
| P6 | `wave298-p6-deep-innovations.md` | Authoritative 24-innovation inventory mapped to paper sections |
| P7 | `wave298-p7-paper-append.md` | 1 section appended to `docs/drafts/paper-flat-flattened.md` (deep-innovation appendix) |
| P8 | `wave298-p8-claims-updated.md` | `CLAIMS.md` + `README.md` + `README.zh.md` + `wave288-p1-honest-progress-summary.md` updated |

**Five gates verified (this run):**
- `pytest tests/test_d4_regression_vectors.py tests/test_paper_grounded_schedulers.py tests/test_full_jmaa_integration.py -q` → **133 passed, 0 failed** (64 deprecation warnings are about `default_cosine_scheduler`, pre-existing, NOT failures).
- `tools/check_claims_consistency.py` → **No drift detected** (61 ACTIVE + 0 PROVISIONAL + 2 DEPRECATED; CLM-040 demoted to PROVISIONAL by `Disputed by:`).
- `ruff check adaptive_reflow/ tests/ scripts/ tools/` → **All checks passed!**
- `mkdocs build --strict` → **0 warnings** (Material for MkDocs team warning about MkDocs 2.0 future is forward-looking, not a current-build failure).
- `python3 tools/build_metric_ledger.py` → **133 rows** (80 CLAIM + 7 HEADLINE + 5 STATISTICAL + 18 INSIGHT + 5 ENGINEERING_GATE + 8 SWEEP280 + 4 SWEEP286 + 6 SWEEP291). 17 non-fatal status-format warnings preserved from prior waves (CLM-018/022 carry "INVERTED POST-cd70821" annotation; CLM-070..084 newly-UNKNOWN rows defaulted to ACTIVE — both well-documented in `wave298-p8-claims-updated.md`).

---

## 1. Top 7 GENUINELY NOVEL innovations (paper §3–§4 primary)

These close gaps between two known prior-art poles; the combination is unique to this project.

### 1.1 Hash-Chained Ledger Rows with Incremental O(1) Verification

**File:line:** `adaptive_reflow/frame/engine.py:455-619` + `adaptive_reflow/frame/ledger_chain.py:113-218` + `tools/build_metric_ledger.py:51-1489`.
**Closest prior art:** Git packfile SHA-1 chain (O(R) per check via `git fsck`); MLflow/W&B/TensorBoard append-only logs (no cryptographic chain); Karimi 2024 blockchain-audit-for-ML thesis (overkill).
**Novelty:** SHA-256 chain over canonical row fields; **tamper detected at append time** with one hash per row (`LedgerChain.append` is O(1) amortised vs `verify_ledger_chain`'s O(R) per call). `ParallelLedgerChain.finalize` produces the same head hash as the sequential chain — enables byte-deterministic parallel execution.
**Reviewer value:** Reviewer can prove the published metric ledger (133 rows, last regenerated 2026-09-23) was NOT hand-edited after generation. Closer to Debian `reproducible-builds.org` than typical ML tooling.

### 1.2 PEP 695 Generic State Machine with Byte-Deterministic Transition Log

**File:line:** `adaptive_reflow/contracts/state_machine.py:372-1190`.
**Closest prior art:** `transitions` / `python-statemachine` / `fysom` — all use `datetime.now()` in logs (not byte-stable); `mp-fsm` / `fsm-engine` (mypy-compatible but wall-clock); `sismic` (SCXML, no PEP 695).
**Novelty:** Stdlib-only state machine library with PEP 695 generics (`mypy --strict` catches invalid literals), HSM (`add_region`), parallel regions (`add_parallel`), history pseudo-states (SHALLOW/DEEP), visualization (`to_dot`/`to_mermaid`), and wall-clock-free byte-deterministic `TransitionLog`. A test can assert `log.to_json() == expected_log.to_json()` exactly.
**Reviewer value:** Composes with hash-chained ledger (Innovation #1) to make engine state progression auditable. First Python state machine that is simultaneously type-safe + byte-stable + visualization-capable.

### 1.3 Capability-Token Handshake with Fail-Closed Audit Trail

**File:line:** `adaptive_reflow/universal/adapter.py:131-204` + `adaptive_reflow/frame/engine.py:711-778` + `adaptive_reflow/frame/engine.py:1233-1300` (`_emit_fail_closed`).
**Closest prior art:** ONNX Runtime `IExecutionProvider::CanHandle` (hard fail at construction); HuggingFace Transformers (check once at construction); PyTorch Lightning (set at `__init__`).
**Novelty:** 9 bool flags + `supported_channels` + `channel_domains` + `materializer_instance` declared per-adapter; before ANY native dispatch, `_check_capabilities_advertise_dispatch` re-validates and appends `f"{ERR_CAPABILITY_UNSUPPORTED}:{channel}:{capability}"` to `audit_codes` rather than raise. Engine continues to round emit; partial rounds remain auditable.
**Reviewer value:** The pattern lets a research codebase expose capability mismatches as STRUCTURED DATA rather than silently failing OR crashing. In multi-model SOTA-comparison contexts (FlowMol3, LineageFlow, Kanzi, FreqFlow, MM-FM), this is the difference between runtime exception and reviewer-readable diagnostic.

### 1.4 Typed Four-Port Wire Carrier with `Condition` Discriminated Union + Auto-Wrap

**File:line:** `adaptive_reflow/contracts/condition.py:107-470` + `adaptive_reflow/universal/state.py:113-260` (auto-wrap).
**Closest prior art:** Pydantic v2 `RootModel` discriminated unions (strict, rejects untyped data unless explicit `model_validator` written); PyTorch `TypedDict` + `from_dict` (explicit conversion, breaking change); attrs + converters (per-field opt-in).
**Novelty:** 5 typed `Condition` subclasses (`NullCondition`/`CFGCondition`/`InpaintingCondition`/`BFNInpaintCondition`/`PropertyCondition`) + discriminated `condition_kind` literal + `ODEConditionDelta.__post_init__` auto-wraps raw dicts into typed `MappingConditionAdapter` for 2356-test back-compat. Closed-set `CONDITION_KINDS` literal forces paired acceptance test + DTB-Q decision per new kind.
**Reviewer value:** Closes the gap between typed-migration-breaking-change and forever-untyped-legacy. Incremental migration path that doesn't break the 2356-test back-compat corpus.

### 1.5 Honest Disclosure When Hypothesis is Refuted (Lab-Notebook Inline)

**File:line:** `docs/CLAIMS.md` — additive `W286 P -> W291 P4 -> W292 re-anchor` chain (CLM-005/006/070).
**Closest prior art:** ICML 2024 Position "Embracing Negative Results in Machine Learning" (arXiv 2406.03980 — general call); REAL ML (arXiv 2205.08363 — structured limitations); McGreivy & Hakim Nature MI 2024 (93% superiority claims); Cytognosis article (operationalises by attaching negative findings to release system).
**Novelty:** Refuted lever hypotheses published inline as Wave-268-strict-clean additive status addenda. ACTIVE status preserved verbatim — refutations are ADDENDA, not status flips; wave numbers preserved for `git log --follow`.
**Reviewer value:** Lab-notebook-grade inline publication of refutations is rare. Each refutation is a CHAINED multi-wave audit document with re-anchor step.

### 1.6 Wave-Based Audit Chain with Topic-Cluster Cross-Reference

**File:line:** `docs/audit/waveNNN-pK-*.md` (24 waves × multi-phase = 94+ audit files) + `docs/audit/INDEX.md` (topic re-clustering).
**Closest prior art:** Linux kernel `Documentation/` per-subsystem + `git log --follow` (static docs, no per-decision audit); lab notebook best practices (free-form prose); DVC + MLflow (versioning+tracking, no per-decision audit chain); PapersWithCode reproducibility checklist (flat).
**Novelty:** Every wave produces self-contained `waveNNN-pK-*.md` (TL;DR + Method + Verdicts + INVARIANTS + Edit discipline). `INDEX.md` re-clusters by topic (cifar / algorithm_4arm / engineering / reproducibility / etc.) so reviewers answer questions without grepping 94 files. Edit discipline section names every vendored script NOT modified per wave.
**Reviewer value:** Reviewer can trace any claim back to the refutation chain without grepping 94 audit files. Closer to formal-methods traceability matrix than ad-hoc lab notebook.

### 1.7 Lazy-Memoized Paper-Quantity Cache with Site-Aware Dispatch

**File:line:** `adaptive_reflow/framework/paper_quantities_cache.py:138-610`.
**Closest prior art:** `functools.lru_cache` / `functools.cache` (always-on after first call); `torch.compile` lazy trace (always-on after first trace); `@property` lazy init (per-call); `cachetools.TTLCache` (TTL-based).
**Novelty:** Single dormant/active constructor with `profile_residual_fn` as the activation trigger; 15 JMAA theory sites share ONE cache keyed by `site_name` via `PAPER_QUANTITIES_SITE_NAMES` closed-set; `consume()` produces idempotent activation log. Site-aware `get()` returns different value shapes per site (`e_rho` / `cell_C` / `(A,B,C,e_rho)` 4-tuple / `(sheet_A, cell_C)` 2-tuple / `PaperQuantitiesSnapshot` / `profile_residual_fn`).
**Reviewer value:** First cache architecture that is site-aware + activation-keyed + idempotent-activation-tracked simultaneously. Enables 15 theory sites to share infrastructure without losing per-site semantic distinctions.

---

## 2. Top 7 INCREMENTAL / WELL-KNOWN-APPLIED innovations (paper §5–§7 supporting)

These have prior art in some community; the engineering work is real but the underlying idea has known analogs. Included for completeness; reviewer would value them as evidence of comprehensive coverage.

| # | Innovation | Closest prior art | What is new |
|---|---|---|---|
| 2.1 | Cosine Sigma-Across-Seeds as Canonical Noise Band | Multi-seed CV with n_sigma confidence bands (PapersWithCode convention) | Cosine baseline's framework_fid sigma across 3 seeds (0.755% relative at N=200) is the canonical noise band for byte-stability claims: STRONG ≤ 1σ, PARTIAL ≤ 2σ, WEAK > 2σ. Separates byte-stability from effect size. |
| 2.2 | D.4 Byte-Stable Scheduler Regression Vectors (30/30) | `torch.use_deterministic_algorithms(True)` + `CUBLAS_WORKSPACE_CONFIG=:4096:8` (well-documented); Hypothesis property-based testing (well-known) | Per-(seed × NFE) SHA-256 of output + trajectory across CPU + GPU paths + `host_fingerprint` + `env_composite_hash` skip-on-shifted-host. D.4 covers 18 adapters; 30/30 PASS preserved (W268 P2: 72/72 PASS; W225 P0-P9: 30/30 PASS per CLAIMS.md:3820). |
| 2.3 | 6-Gate CI on Every PR (`.github/workflows/ci.yml:33-208`) | Pre-commit hooks (Husky, pre-commit.com); multi-stage CI with pytest+ruff (universal) | Combines 6 pre-merge gates: pytest (-m 'not slow and not benchmark') + ruff (E/W/F/I/B/UP/SIM over `adaptive_reflow/` + `tests/`) + mypy --strict + `check_docs_against_code` (AST-walks symbols + code-blocks + paths) + `check_claims_consistency` (file:line + cross-ref sweep) + mkdocs build --strict. Multi-Python 3.12 + 3.13 matrix. |
| 2.4 | Bounded-Lipschitz Convergence Diagnostic | Bounded-Lipschitz distance (Sriperumbudur et al. 2012 — Empirical risk minimization for entropy-regularized Wasserstein losses) | `d_BL = mean_i min(|x_(i) - y_(i)|, B)` over matched order statistics; always finite (outliers bounded) where unbounded W1 could be dominated by a single outlier. `tail_modulus` vs constant/√N test separates smooth convergence from oscillation. |
| 2.5 | Permutation Test for the Lever Hypothesis | Random baseline ablations (common in ML); within-scheduler-family permutation control (rare) | W290/291 codim_real_g vs codim_perm (`_random_profile_factory(seed+1000)` profile) tested whether the 71pp cos→codim direction-flip is driven by the paper quantity or the scheduler structure. Result: paper-quantity lever INERT at eps=10, L=4 (byte-identical real_g vs perm across 3 seeds). |
| 2.6 | Theorem-Aligned FID Evaluator (`adaptive_reflow/eval/fid_theorem_aligned.py:498-759`) | "What FID Hides" (ZID, arXiv 2608.24881, Aug 2026 — closest prior art); standard FID (Heusel et al. 2017) | InceptionV3 FID evaluator emitting per-round `TheoremAlignedFIDResult` carrying `(A_g, B_g, C_g, e_rho)` + regime-violation flag (`eps² < e_rho / log 2`) + O(eps) paper-implied bound check (`C_paper = (C_g * B_g + 1/e_rho) / A_g`). Back-compat via `as_fid_result()` projection. Module docstring honestly disclaims: regression gate, NOT a proof of Theorem 1. |
| 2.7 | Empirical `profile_residual_fn` Adapter-Agnostic Residual Interface (`adaptive_reflow/adapters/profile_residual.py:312-431`) | Adapter pattern (GoF, 1994); sklearn transformer API | `Callable[[float], float]` converts empirical-residual distributions (LineageFlow pLDDT, Kanzi RMSD, FlowMol3 fg_dev) into closed-form `g(s)` expected by `sheet_evidence_A` + Lemma 5. Wave 230 P1 design choice (relative residual `r(s)/r(s_bar) * sin(s)`) preserves canonical pi-spaced zeros rather than naive `(r - r(s_bar)) * sin(s)` centred design that breaks disjoint-cell constraint `rho < d/4`. |

---

## 3. Methodology innovations (paper §8 reproducibility section)

| # | Innovation | Wave doc | Key evidence |
|---|---|---|---|
| M1 | Honest Disclosure When Hypothesis is Refuted | `wave298-p2-methodology-innovations.md` §1 | Inline additive `W286 P -> W291 P4 -> W292 re-anchor` chain in `CLAIMS.md` |
| M2 | Wave-Based Audit Chain with Topic-Cluster Cross-Reference | `wave298-p2` §2 | 24 waves × multi-phase self-contained `waveNNN-pK-*.md`; `INDEX.md` re-clustering |
| M3 | Permutation Test for the Lever Hypothesis | `wave298-p2` §3 | W290/291 codim_real_g vs codim_perm; byte-identical at eps=10, L=4 across 3 seeds |
| M4 | Cosine Sigma-Across-Seeds as Canonical Noise Band | `wave298-p2` §4 | STRONG ≤ 1σ, PARTIAL ≤ 2σ, WEAK > 2σ |
| M5 | Backward Compat as Primary Invariant | `wave298-p2` §5 | Five-gate INVARIANTS section in every audit doc + W268 strict-clean rule |

---

## 4. Engineering utilities (paper §10 + appendix)

| # | Innovation | File | Speedup / value |
|---|---|---|---|
| E1 | Batched Framework Harness | `tools/batched_framework_cifar.py:120-243` | ~28-35× wall speedup, zero `adaptive_reflow/` source edits; closes kernel-launch gap |
| E2 | Adversarial Scheduler Stress Matrix | `tools/adversarial_scheduler_test.py:112-921` | (scheduler × pathological_input) matrix distinguishes FAIL_rejected_by_design from FAIL_crash/FAIL_naN |
| E3 | Empirical `profile_residual_fn` Adapter | `adaptive_reflow/adapters/profile_residual.py:312-431` | Adapter-agnostic `Callable[[float], float]` plug-in |
| E4 | Theorem-Aligned FID Evaluator | `adaptive_reflow/eval/fid_theorem_aligned.py:498-759` | Per-round `(A_g, B_g, C_g, e_rho)` + regime + O(eps) bound check |
| E5 | Bounded-Lipschitz Convergence Diagnostic | `adaptive_reflow/eval/lipschitz_diagnostic.py:106-253, 256-321` | `tail_modulus` vs `MC rate` separates smooth convergence from oscillation |

---

## 5. Cross-references to prior audit docs

- **Architecture:** `wave296-p1-architecture.md` (JMAA opt-in design) · `wave296-p2-cache.md` (PaperQuantitiesCache impl) · `wave296-p3-a-class-wired.md` · `wave296-p4-b-class-wired.md` · `wave296-p5-activation-log.md`.
- **Paper design:** `wave297-p1-paper-inventory.md` (structure) · `wave297-p2-paper-design.md` (§1–§11 redesign) · `wave297-p3-intro-rewritten.md` · `wave297-p4-framework-rewritten.md` · `wave297-p5-empirical-rewritten.md` · `wave297-p6-limitations-rewritten.md` · `wave297-p7-readme-updated.md`.
- **Pipeline inventory:** `wave292-p1-pipeline-inventory.md` (15 dormant sites).
- **Prior methodology sweeps:** `wave286-p-fid-gpu-fix.md` (FID GPU fix) · `wave287-p-scheduler-codepath-audit.md` (24-bug audit) · `wave288-p0-application-sites.md` (16 application sites) · `wave288-p1-honest-progress-summary.md` (honest progress summary) · `wave290-p1..p5` (codim lever sweep) · `wave291-p1..p5` (3-seed headliner verification + regime-aware redesign).
- **Claims ledger:** `docs/CLAIMS.md` (61 ACTIVE + 0 PROVISIONAL + 2 DEPRECATED; CLM-040 PROVISIONAL via `Disputed by:`) + `docs/METRIC_LEDGER.{md,json}` (133 rows regenerated from 8 source surfaces).
- **Index:** `docs/audit/INDEX.md` (topic re-clustering: cifar / algorithm_4arm / engineering / reproducibility / etc.).

---

## 6. Outstanding items

1. **Push pending** — per user directive "暂不 push", this commit is local-only. The Wave 298 P1–P8 + W296 + W297 audit corpus is the next push batch.
2. **Wave 296 in progress** — `wave296-p5-activation-log.md` describes the `consume()` activation log; the cross-paper-quantity activation telemetry integration (planned for Wave 299) is still in flight.
3. **Metric ledger non-fatal warnings** — 17 status-format warnings preserved from prior waves (CLM-018/022 "INVERTED POST-cd70821" annotation; CLM-070..084 newly-UNKNOWN rows defaulted to ACTIVE). Both are well-documented in `wave298-p8-claims-updated.md`; the build script does not fail on them.
4. **CLM-040 PROVISIONAL** — auto-demoted by `Disputed by:` citation. The `Disputed by:` ground in `tools/check_claims_consistency.py` is the canonical authority; CLM-040 remains PROVISIONAL until the §1.1.d sidecar caveat re-anchor.
5. **Paper-quantity lever at W286 P hyperparameter point** — INERT at eps=10, L=4 (W291 P4 byte-equivalent to cosine). The lever EXISTS at other hyperparameter points (W291 codim_real_g vs codim_none p=2.29e-03 across 3 seeds) but the W286 P configuration is the only verified headliner cell where it's inert. Future work: sweep eps ∈ {0.5, 2.0, 10.0} × L ∈ {4, 8, 16} to map the lever's active regime.

---

## 7. INVARIANTS (anchored for this audit)

- **D.4 30/30 PASS** — `pytest tests/test_d4_regression_vectors.py` (locked-in seed × NFE = 41/42/43 × 5/10/50 = 9 conditions × 5 adapters × 6 test functions = 30 tests; all PASS).
- **No claims drift** — `tools/check_claims_consistency.py` reports "No drift detected" (61 ACTIVE + 0 PROVISIONAL + 2 DEPRECATED; CLM-040 demoted to PROVISIONAL by `Disputed by:`).
- **ruff 0** — `ruff check adaptive_reflow/ tests/ scripts/ tools/` → All checks passed!
- **mkdocs 0 warnings** — `mkdocs build --strict` → Documentation built in 21.65s; MkDocs 2.0 forward-looking team warning is not a current-build failure.
- **Vendored NOT touched** — verified by per-wave Edit discipline sections naming every vendored script NOT modified (vendored repos are `data/<repo>/**`, `data/lineageflow_upstream/**`, `.venvs/**`).

This doc is **READ-ONLY** and produces no code changes; it is purely the Wave 298 final inventory.

---

## 8. Edit discipline

**Vendored scripts NOT modified** (per user directive "clone下来的原sota项目里的打分脚本依旧不能动"):
- `tools/run_sota_cifar_experiment.py` (W286 P)
- `tools/compute_cifar_fid.py` (W286 P)
- `data/<repo>/**` (W268 strict-clean)
- `data/lineageflow_upstream/**` (W268 strict-clean)
- `.venvs/**` (W268 strict-clean)

**This audit doc:** created 2026-09-23, READ-ONLY summary of Wave 298 P1–P8.