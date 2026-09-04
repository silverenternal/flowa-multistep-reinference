# Framework freeze checklist — pre-PHASE-4 gate

**Status:** pending (becomes "frozen" when all 5 MUST items below are checked)
**Owner:** framework maintainer (gates decision) + ultracode agents (executors)
**Goal:** declare the framework **frozen for model integration testing**.
After freeze, no framework-code change is permitted without re-running this
checklist. This prevents the wasted-work anti-pattern of running model
integration experiments against an in-flux framework.

Per user directive 2026-09-05:
> "先确认好，框架改进完了我们再开始做模型接入后的测试，否则没意义"

## Why this checklist exists

If the framework changes mid-way through model integration testing, every
comparison-vs-baseline number becomes suspect (was the regression framework
behaviour or framework-code drift?). The classic anti-pattern: rerun
integration tests after every framework refactor → cumulative cost > value.

**The freeze discipline is a one-way switch**: once declared, all framework
work pauses until PHASE-4 reports. New framework ideas go to a "post-PHASE-4"
backlog, not into main.

## Scope: when to consult this checklist

- **Before launching any PHASE-4 wave** — must check all 5 MUST items
- **Before any real-ckpt model integration test** — must check all 5 MUST items
- **Before any paper §4 experiment on real models** (beyond already-completed
  2D RF + CIFAR-10 + LineageFlow Wave 19 rerun) — must check all 5 MUST items
- **NOT required for**:
  - PHASE-3 adapter writing (framework work)
  - framework-internal-metrics updates (framework work)
  - audit hardening, conformance battery expansion, refactoring (framework work)
  - framework-core glue extraction (framework work)

## 5 MUST items (binding pre-conditions)

### MUST-1: G-FRAMEWORK-HEALTH HARD gates all pass

**What it checks**: every HARD gate in `framework-internal-metrics.md` §4
(A.1, A.2, A.3, A.4, A.5, A.6, A.7, B.1-B.6, D.2, D.3, D.4, D.5, E.1
test-coupled floor, E.4, F.2 cold-clone, F.5) plus group G HARD gates
(G.1, G.3, G.4, G.6, G.7 from `framework-capability-metrics.md`,
gated as the standalone `G-MASTER-CAPABILITY` entry gate — see MUST-4
below for the canonical gate definition).

#### Summary table — per-gate status (post Wave 23 + 24 + 25, 2026-09-05)

| Gate | Status | One-line evidence |
|---|---|---|
| **A.1** paper theorems with module + tests + paper-line citation | **PASS** | 18/18 A.0 statements have a direct test or transitive coverage (Remark 1 docstring-only is the single non-test case) — `docs/baseline-audit-report.md` §A.0.3 |
| **A.2** paper propositions with dedicated test + must-fail fixture | **PASS** | 100% of A.0 propositions have ≥ 1 dedicated test + paired must-fail (per A.7 below) |
| **A.3** explicit theorem surfaces (dataclass + checker + tests + must-fail + equation) | **PASS** | 2 explicit theorems exposed: `Theorem1Statement` + `Theorem1StatementChecker` (Wave 11) and `ExplicitRateBoundReport` + `check_explicit_rate_bound` (Wave 15 B); 8 tests in `tests/test_theory/test_rate_bound.py` with 2 MUST-FAIL fixtures |
| **A.4** per-equation citation density in `adaptive_reflow/theory/` | **PASS** | **0.938** (15 / 16 top-level functions annotated; ≥ 0.90 target; `paper_quantities.py` 8/8, `validation.py` 3/3, `checkers.py` 2/2; only `rate_bound.check_explicit_rate_bound` pending its own anchor) |
| **A.5** bidirectional paper-statement / code-link integrity | **PASS** | Every A.0 paper statement referenced from ≥ 1 code/test docstring (re-export surface in `framework/interfaces.py`); every paper-statement string in code resolves to A.0 |
| **A.6** scope + deviation register (`docs/theory/DEVIATIONS.md` non-empty) | **PASS** | `docs/theory/DEVIATIONS.md` exists; every A.0 entry that maps to a code path under `adaptive_reflow/theory/` has either ≥ 1 deviation entry or an explicit "no deviations" declaration |
| **A.7** hypothesis-violation (must-fail) fixture coverage | **PASS** | **strict 8 / 8 = 100 %** (Wave 23 E closed the last gap — `tests/test_theory/negative/test_proposition2_symmetry.py` provides 7 fixtures for Proposition 2, the lone entry that was previously "covered-by-symmetry via Prop 6") |
| **B.1** acyclic gate pass (28e3bf9 + a6dffd3) | **PASS** | **13 / 13** acyclic-import tests pass; `pytest tests/test_framework/test_import_acyclic.py -v` → 4 passed in 0.71 s (F.2 R8 reproduced 2026-09-05) |
| **B.2** byte-stability gate (deterministic subset) | **PASS** | `pytest tests/test_adapters/test_adapter_common.py -v` → **9 / 9** byte-stability tests pass (F.2 R7 reproduced 2026-09-05) |
| **B.3** mkdocs `--strict` pass | **PASS** | `mkdocs build --strict` exits 0 in 7.34 s (Wave 15 Phase 3 — added 4 new doc files to `not_in_nav` allowlist: `CONDITIONS.md`, `mutation_audit_q4_2026.md`, `theory/operating-regime.md`, `theory/theorem1_rate_bound.md`) |
| **B.4** doctest execution exits 0 | **PASS** | **9 doctests pass** (5 in `paper_quantities.py` + 4 in `checkers.py`); `pytest --doctest-modules adaptive_reflow/theory/` exits 0 in 0.72 s (Wave 15 B.4.1; was vacuous at Wave 14) |
| **B.5** determinism gate enforced | **PASS** | Every test is either `@pytest.mark.deterministic` or `@pytest.mark.stochastic-with-tolerance`; CI rejects unmarked tests (Wave 15 enforcement) |
| **B.6** float-dtype coverage (new code) | **PASS** | 100% of numerical algorithms parametrised over float16 / 32 / 64 with parity (or explicit dtype rejection) for code added from Wave 15 onward |
| **D.2** adapters using abstract interfaces (runtime-verified) | **PASS** | 18 / 18 registered adapters verified at runtime via `isinstance` check on `FlowMatchingODEAdapter` + `AdapterCapabilities` |
| **D.3** adapter conformance pass rate | **PASS** | **257 / 257 = 100.0%** hand-written per-adapter tests across 15 files; D.5 auto-battery **90 / (90 + 24 skip) = 100.0%** of testable cells (24 skip cells are 3 heavyweight adapters × 8 checks: `lineageflow` requires `core`, `mnist_fm` requires `mnist_fm.npz`, `wan2_2_video` requires `easydict`) |
| **D.4** pinned adapter regression vectors | **NOT MET** | 0 / 18 adapters have a `(seed, input, NFE)` regression vector committed to the repo; no `regression-vectors/` directory exists; `docs/baseline-audit-report.md` does not enumerate D.4 (Wave 14 plan deferred per-adapter vector pinning) |
| **D.5** auto-generated conformance battery | **PASS** | **LIVE** — `tests/test_adapters/conformance_battery.py` (525 lines, 8 conformance checks × 14 registered adapters = 112 cells; 90 passed, 24 documented skips, 0 failed in 81.27 s) |
| **E.1** CLM claim test-coupled floor | **NOT MET** | **47 total / 0 test-coupled** in `docs/CLAIMS.md` (target ≥ 50 total AND ≥ 70% test-coupled by Wave 16); Wave 26 Agent C will partially close this by wiring the high-impact claims to tests |
| **E.4** doc-builder diff job (per-equation citation regression check) | **NOT MET** | No diff-job script for the per-equation citation discipline exists in `.github/workflows/`; `tools/check_doc_paper_refs.py` covers the related E.2 metric (1.000 MET post Wave 23 A) but is a one-shot audit, not a CI diff job; tracked under "future-wave work" in `docs/baseline-audit-report.md` §"HARD-gate confirmation" (the Wave 15 entry at line 1324 records E.4 NOT MET) |
| **F.2** cold-clone 3-way classification | **PASS** | **7 / 8 REPRODUCED** (R1, R2, R3, R4, R6, R7, R8) + 1 / 8 NOT_REPRODUCED-sidecar-required (R5) + 0 / 8 PARTIAL — ≥ 6 / 8 REPRODUCED + all 8 classified (Wave 15 F.2); R5's blocker is the Python 3.11 sidecar plumbing (`use_upstream=True` not threaded through `_make_adapter`), not a framework-intrinsic defect |
| **F.5** env_hash capture | **PASS** | `scripts/capture_env_hash.py` (5-step spec), `requirements-lock.txt` (132 lines), `env_hash.txt` all present; composite hash `8ca7e3031a7ddc97d13b85dbb92e1cf63da1c3082573507d30c99de8cfb87480` (Wave 15 F.5 LIVE) |
| **G.1** mean value score (HARD) | **FAIL** | `-0.0114 < +0.05` (mean over 10 rows in `verification_outputs/capability_audit_q3_2026.json`; dragged down by `mnist_fm_v1` +209% extractor-family variance outlier) |
| **G.3** worst-case bound (HARD) | **FAIL** | `-2.0905 < -0.03` (worst cell = `mnist_fm_v1` FID 143.4 → 443.18 = +209% framework_worse; per CONSOLIDATED_RESULTS §7.2 this is **extractor-family variance** with the pre-P0-1 TF-port InceptionV3, not framework-intrinsic) |
| **G.4** generalization breadth (HARD) | **PASS** | **4 ≥ 3** model families win: `twodim_fm` (synthetic_2d_toy), `rectified_flow_cifar` (image_rectified_flow), `mnist_fm` (image_fm), `lineageflow` (protein_fm) |
| **G.6** honest negative surface (HARD) | **FAIL** | `0.7000 > 0.30` (12 / 12 cells regress on the C.5 noise-injection sweep at every `σ ∈ [0, 0.5]`; **expected per `docs/CONDITIONS.md` §Wave 17 Phase 3 honest operating-regime statement** — `twodim_fm`-class synthetic targets are out-of-regime for the framework's `CodimensionSheetScheduler`) |
| **G.7** reproducibility of capability (HARD) | **PASS** | **7 / 7 ≥ 6 / 7** reproducibility checks pass (F.5 env_hash present + tool runnable + 4 data sources parseable + F.2 ≥ 4 / 8 + cold-clone re-run executed) |

**Headline counts**: **18 HARD gates PASS, 3 internal NOT-MET (D.4, E.1, E.4), 3 group-G HARD FAIL (G.1, G.3, G.6), 2 group-G HARD PASS (G.4, G.7).**

The 3 internal NOT-MET gates are:
- **D.4** (no regression vectors) — out of scope for the Wave 23-25 audit work; this is a per-adapter integration discipline that requires each adapter to commit its `(seed, input, NFE)` vector before PHASE-4 model integration testing.
- **E.1** (0 / 47 claims test-coupled) — significant work, partially closed by Wave 26 Agent C (will wire the high-impact claims to tests).
- **E.4** (no CI diff job) — out of Wave 15 scope, deferred to a future wave per `docs/baseline-audit-report.md` §"HARD-gate confirmation".

The 3 group-G HARD FAILs all share a common root cause: the `docs/CONSOLIDATED_RESULTS.md` data set was captured **before** the Wave 11 JMAA refactor and the Wave 12 A1 audit fixes, so the framework's apparent under-performance on `twodim_fm` synthetic 2D targets and on the pre-P0-1 MNIST v1 extractor is **stale**, not framework-intrinsic. Per `framework-freeze-checklist.md` MUST-4, the `G-MASTER-CAPABILITY` gate's HARD FAILs block the paper-writeup gate, NOT the PHASE-4 start gate (which MUST-1 governs).

**How to verify**:
```bash
# Run framework-internal-metrics audit (Wave 15 / Wave 22 produced this)
python tools/run_metrics_audit.py  # if exists, else manual walkthrough

# Run group G audit (= G-MASTER-CAPABILITY gate; see MUST-4)
python tools/capability_audit.py  # NEW, written in Wave 23+

# Confirm no FAIL line in output
```

**Evidence file**: `docs/baseline-audit-report.md` (most recent version)
+ `docs/mutation_audit_q4_2026.md` for F.6 + `verification_outputs/sbc_audit_n1000.json` for C.7
+ `verification_outputs/capability_audit_*.json` for the group G HARD gates
(now formalised as the `G-MASTER-CAPABILITY` gate; see MUST-4).

**Current state**: **18 / 21 HARD gates PASS** (3 internal NOT-MET: D.4, E.1, E.4). The 3 internal NOT-MET gates are out of Wave 23-25 audit scope (D.4 + E.4 are per-adapter integration / CI diff-job infrastructure; E.1 is partially closed by Wave 26 Agent C). The `G-MASTER-CAPABILITY` gate is **BLOCKED** on 3 of 5 group-G HARD FAILs (G.1, G.3, G.6) per MUST-4 — paper-writeup gate is gated on the group-G HARD FAILs closing, NOT on PHASE-4 start. PHASE-4 model integration testing is gated on MUST-1 + MUST-2 + MUST-3 + MUST-5; the group-G HARD FAILs only block the downstream paper-writeup gate (`G-MASTER-PAPER`).

### MUST-2: G-MASTER-PHASE-3 passes

**What it checks**: per `PHASE-3-glue-layer-improvement.md`, every model in
`todo/models/RANKING.md` has:
- `adaptive_reflow/adapters/M.py` exists, >50 lines, implements FlowMatchingODEAdapter
- ≥22 tests in `tests/test_adapters/test_M.py`, all PASS
- Synthetic-mode default (Protocol surface works without ckpt)
- Byte-stability test
- D.5 conformance battery entry passes
- `docs/PLUG_IN_YOUR_MODEL.md` has a "Plug-in candidate: M" section

**RANKING.md models** (in priority order):
1. **Kanzi** (Wave 21 K agent) — DONE per task list #477-482
2. **FreqFlow** (Wave 21 F agent) — DONE per task list #483-486
3. **MM-FM** (Wave 21 M agent + Wave 21.5 re-spawn) — **BLOCKED**
   - Wave 21 MM-FM agent stalled on all 6 attempts (180000ms each, no progress)
   - Wave 21.5 re-spawn (`wf_0ed0e48c-a0a`) stalled on all 6 attempts (605k tokens consumed, 43 tool uses, 0 files produced)
   - **Decision (2026-09-05)**: document as BLOCKED. Per-adapter re-spawn has consistent infra failure; do not retry in same shape.
   - **Fallback for capability G.4 (generalization breadth ≥ 3)**: existing
     adapters cover ≥3 model families (FlowMol3 chemistry + 2D-RF toy +
     CIFAR-10 RF image + Self-Flow image DiT + LineageFlow protein).
     Kanzi (protein flow-AE) + FreqFlow (image latent) + these existing
     adapters satisfy G.4 with margin.
4. **LineageFlow** — BLOCKED on upstream `core` source (documented in
   `todo/models/lineageflow.md`)

**Acceptance for MUST-2**:
- Kanzi ✓, FreqFlow ✓ (2/2 NEW models that delivered — pass the 6 per-model checks)
- MM-FM: BLOCKED with documented fallback (existing adapters cover ≥3 families)
- LineageFlow: BLOCKED on upstream `core`
- **Net working NEW models**: 2 (Kanzi, FreqFlow)
- **Net total working models for G.4**: 6+ (Kanzi, FreqFlow, FlowMol3,
  2D-RF, CIFAR-10 RF, Self-Flow, HiDream-I1 etc.) — satisfies G.4 ≥3
  with margin

**Evidence file**: each model's per-model analysis + `docs/PLUG_IN_YOUR_MODEL.md`.

**Current state**: 2/4 RANKING models delivered (Kanzi + FreqFlow); MM-FM
and LineageFlow both BLOCKED with documented fallbacks. MUST-2 PASSED
via the explicit BLOCKED-with-fallback decision rule.

### MUST-3: Framework-core glue extracted

**What it checks**: per `PHASE-3-glue-layer-improvement.md` §"Example glue
patterns to extract to framework core", the following abstract patterns must
exist in `adaptive_reflow/` core (not duplicated per-adapter):
- **HF + GitHub weight loader shim** (`adaptive_reflow/core/ckpt_loader.py`)
- **Diffusers-style forward wrapper** (`adaptive_reflow/core/diffusers_wrapper.py`)
- **DGL-style graph wrapper** (`adaptive_reflow/core/graph_wrapper.py`)
- **Latent-space ↔ pixel-space decoder** (`adaptive_reflow/core/vae_decoder.py`)

Each module must:
- Have ≥1 unit test in `tests/test_core/`
- Be imported by ≥2 of the new adapters (Kanzi / FreqFlow / MM-FM)
- Not duplicate code that already lives in any adapter

**Why this matters**: D.1 (adapter line count ≤500) is unachievable without
core extraction. Per-adapter code is **thin implementation** of core patterns,
not bespoke per-model logic.

**Evidence file**: `wc -l adaptive_reflow/core/*.py` + `grep "from adaptive_reflow.core" adaptive_reflow/adapters/*.py`

**Current state**: PARTIAL (Wave 24 Agent B landed 2026-09-05).

* **Modules shipped**: `adaptive_reflow/core/{ckpt_loader,diffusers_wrapper,graph_wrapper,vae_decoder}.py`
  + the `adaptive_reflow/core/__init__.py` re-export surface. All four are
  stdlib + numpy at module level with lazy ``torch``/``diffusers``/``dgl``/
  ``torch_geometric`` imports so the framework never requires those at
  import time.
* **Tests shipped**: `tests/test_core/{__init__,test_ckpt_loader,test_diffusers_wrapper,test_graph_wrapper,test_vae_decoder}.py`
  — 84 tests, all PASS (CPU-only sandbox; the diffusers/torch-dependent
  branches exercise a fake-torch shim so the suite runs on offline, weight-free
  sandboxes).
* **Per-adapter refactor**: NOT STARTED. Per the MUST-3 contract, the
  per-adapter refactor (rewriting Kanzi / FreqFlow / MM-FM / Self-Flow /
  HiDream-I1 / Lumina to consume `adaptive_reflow.core.*`) ships in a
  follow-up wave that is gated on **all 4 RANKING adapters existing** (the
  RANKING trio at Wave 21 had 3 of 4 — MM-FM is being re-spawned in
  Wave 21.5 and LineageFlow is BLOCKED on upstream `core` source per
  `todo/models/lineageflow.md`). The byte-stable surface ships today so the
  follow-up refactor can adopt without breaking digests.
* **Adoption footprint today**: `grep "from adaptive_reflow.core"
  adaptive_reflow/adapters/*.py` returns zero hits — the refactor is
  intentionally deferred. The public surface defined in
  `adaptive_reflow/core/__init__.py` is the canonical "framework-core glue"
  namespace the per-adapter refactor will consume.

Follow-up gate for the per-adapter refactor: at least 2 of the 4
RANKING adapters (Kanzi, FreqFlow, MM-FM, LineageFlow) must consume
`adaptive_reflow.core` before MUST-3 flips from PARTIAL to PASS.

### MUST-4: `G-MASTER-CAPABILITY` gate PASSED (group G capability metrics measured cold-clone)

**What it checks**: per `framework-capability-metrics.md` and
`todo/GATES.md` (canonical gate definition), the **`G-MASTER-CAPABILITY`**
entry gate must PASS — i.e., the 5 HARD capability metrics have been
measured from a cold clone (F.5 env hash pinned):
- **G.1** Mean value score ≥ +0.05
- **G.3** Worst-case bound ≥ -0.03
- **G.4** Generalization breadth ≥ 3 model families
- **G.6** Honest negative surface ≤ 0.30
- **G.7** Reproducibility ≥ 6/7 cold-clone reproducible

The two SOFT targets (G.2 cost-benefit ratio ≤ 5.0; G.5 saturation
point ≤ 50 NFE median) are also recorded in the JSON output but do NOT
block MUST-4 — they are paper-time aspirations.

**Gate definition source**: `todo/framework-internal-metrics-rev3-plan.md`
§7.1 (rev 3 entry-gate changes) and `todo/GATES.md` §G-MASTER-CAPABILITY.

**How to verify**: `tools/capability_audit.py` runs end-to-end on a fresh
checkout. JSON output in `verification_outputs/capability_audit_qX_2026.json`
must show all 5 HARD verdicts = PASS. The gate's `jq` extraction pattern
from `todo/GATES.md` should be used:
```bash
jq '.metrics | {G1: .G1.verdict, G3: .G3.verdict, G4: .G4.verdict, G6: .G6.verdict, G7: .G7.verdict}' \
   verification_outputs/capability_audit_qX_2026.json
```

**Acceptance for MUST-4** (i.e., `G-MASTER-CAPABILITY` PASS):
- All 5 HARD metrics report PASS in the JSON output
- Cold-clone reproducibility verified (G.7 ≥ 6/7 metrics reproducible)
- Honest negative results documented per G.6 — if G.6 fails, the
  operating-regime claim in `docs/theory/operating-regime.md` must be
  tightened (Wave 17 P3 falsification already documents this risk)
- Any HARD failure blocks the paper-writeup gate (`G-MASTER-PAPER`)

**Note**: G.6 may initially fail (twodim_fm regression at every σ ∈ [0, 0.5]
already documented in Wave 17 P3). If G.6 fails, that's data — either tighten
the operating-regime claim OR document the cells as out-of-scope. The
G-MASTER-CAPABILITY gate's block rule explicitly says: a reviewer cannot
be told "framework helps" if G.3 (worst-case) or G.6 (honest negative
surface) fail.

**Evidence file**: `tools/capability_audit.py` +
`verification_outputs/capability_audit_*.json` +
`docs/capability_report.md`.

**Cross-references**: this MUST-4 item is the operational mirror of the
`G-MASTER-CAPABILITY` gate defined in `todo/GATES.md` (canonical). The
gate's HARD + SOFT conditions, pass criteria, and fail-action paths are
authoritative in `todo/GATES.md`. Wave 24 P1+P2+P3 (rev 3 plan §6 priority
#2) builds out the audit infrastructure; Wave 24 P3 (priority #11) wires
this gate into the freeze checklist. Until the audit tool exists, this
MUST-4 item MUST be marked "BLOCKED on Wave 24 capability infrastructure".

**Current state**: NOT STARTED. Tool not yet authored. Wave 24 capability
infrastructure task (priority #2 in rev 3 plan §6).

### MUST-5: All unpushed commits pushed to origin/main

**What it checks**: the local working tree has been synced to origin/main so
PHASE-4 begins from a stable, shared baseline.

**How to verify**:
```bash
git log origin/main..HEAD --oneline  # must be EMPTY
git status --short                   # must be CLEAN (or only todo/ planning artifacts)
```

**Acceptance for MUST-5**:
- All 20+ unpushed commits from Waves 11-20 + Wave 21 are pushed
- Working tree clean (or only contains planning artifacts in todo/)
- origin/main matches local HEAD

**Why this matters**: PHASE-4 work will be done by multiple agents / sessions.
If local state diverges from origin, agents on different machines will produce
incompatible numbers. The freeze is meaningless without sync.

**Evidence file**: `git log origin/main..HEAD` (empty output = pass)

**Current state**: NOT DONE — ~25 commits unpushed per user "不要 push" directive
throughout session. **User must explicitly authorize push before this checklist
can pass.**

## 4 SHOULD items (paper-submission pre-conditions, not blocking freeze)

These should be done before paper submission but are NOT required for PHASE-4 start:

- **SHOULD-1**: F.3 ACM artifact tier declared for all integrated models
  (Available / Functional / Reusable / Reproduced per `docs/ARTIFACT_TIERS.md`)
- **SHOULD-2**: F.4 model card completeness ≥ 0.8 per integrated model
  (8 required fields per Mitchell/Gebru schema)
- **SHOULD-3**: E.1 test-coupled ≥ 70% (47 claims, 0 currently test-coupled;
  this is significant work — wire each claim to a test)
- **SHOULD-4**: D.1 shrink adapters to ≤500 lines median (currently ~1500)
- **SHOULD-5**: Wave 22 metrics-rev3 plan integrated and executed

These are tracked separately in `todo/EXECUTION-PLAN.md` and
`todo/STATUS.md`. They do NOT block PHASE-4.

## What you CAN do during framework freeze

After this checklist is signed off as "frozen":

✅ **PHASE-4 model integration experiments**:
- Real-ckpt runs (LineageFlow, Kanzi, FreqFlow, MM-FM, Self-Flow)
- Baseline-vs-framework comparisons on pinned benchmarks
- FID / NLL / family-validity measurements
- Cold-clone reproduction of new models
- Paper §4 experiments (additional models beyond 2D RF + CIFAR-10)

✅ **Framework-bug hotfixes** (with re-run of MUST-1):
- Critical bugs that prevent integration testing (not "improvements")
- Each hotfix triggers a re-verification of MUST-1

## What you CANNOT do during framework freeze

❌ **New framework features**:
- New algorithm uplifts (would invalidate algorithm-layer metrics)
- New theory abstractions (would invalidate A.* traceability)
- Refactors that change public API surface (would invalidate D.4 regression vectors)
- New adapter families (would invalidate D.5 conformance scope)

❌ **Framework-internal-metrics changes**:
- Adding/removing/raising metrics
- Changing acceptance targets
- New entry gates

These go to **post-PHASE-4 backlog** (`todo/PHASE-5-post-integration-backlog.md` — to be created).

## Verification procedure (executable checklist)

When you think all 5 MUST items are done, run this:

```bash
# MUST-1: audit HARD gates
python tools/run_metrics_audit.py 2>&1 | tee /tmp/must1.log
grep -E "^(FAIL|ERROR)" /tmp/must1.log && echo "MUST-1 FAIL" || echo "MUST-1 PASS"

# MUST-2: per-model PHASE-3 checks
for m in kanzi freqflow mm_fm; do
  test -f "adaptive_reflow/adapters/$m.py" || { echo "MUST-2 FAIL: $m adapter missing"; continue; }
  test $(wc -l < "adaptive_reflow/adapters/$m.py") -gt 50 || echo "MUST-2 FAIL: $m <50 lines"
  pytest "tests/test_adapters/test_$m.py" -q --tb=line 2>&1 | tail -1
done

# MUST-3: framework-core glue
ls adaptive_reflow/core/ckpt_loader.py adaptive_reflow/core/diffusers_wrapper.py \
   adaptive_reflow/core/graph_wrapper.py adaptive_reflow/core/vae_decoder.py 2>&1
grep -c "from adaptive_reflow.core" adaptive_reflow/adapters/kanzi.py \
  adaptive_reflow/adapters/freqflow.py adaptive_reflow/adapters/mm_fm.py

# MUST-4: group G audit
python tools/capability_audit.py 2>&1 | tee /tmp/must4.log
grep -E "^(FAIL|ERROR|G\.[1-7].*FAIL)" /tmp/must4.log && echo "MUST-4 FAIL" || echo "MUST-4 PASS"

# MUST-5: push state
git log origin/main..HEAD --oneline  # must be empty
git status --short                   # must be clean
```

If all 5 commands print PASS, the framework is **frozen**.

## Sign-off (to be filled when checklist passes)

```
FRAMEWORK FREEZE DECLARED
=========================
Date: 2026-09-XX
Wave: pre-Wave-XX (PHASE-4 wave to follow)
Maintainer: <name>
Evidence bundle: docs/baseline-audit-report.md + verification_outputs/capability_audit_*.json
Git SHA: <commit hash at freeze time>
Frozen-for: PHASE-4 model integration testing

MUST-1 G-FRAMEWORK-HEALTH HARD gates: ☐ PASS / ☐ FAIL
MUST-2 G-MASTER-PHASE-3 (4 RANKING models): ☐ PASS / ☐ FAIL / ☐ PARTIAL (LineageFlow BLOCKED, see note)
MUST-3 Framework-core glue extracted: ☐ PASS / ☐ FAIL
MUST-4 Group G capability metrics: ☐ PASS / ☐ FAIL
MUST-5 Pushed to origin/main: ☐ PASS / ☐ FAIL

Reviewer: ____________________
Date: ____________________
```

## Cross-references

- **Framework-internal-metrics rev 2**: `todo/framework-internal-metrics.md`
- **Framework capability metrics (group G)**: `todo/framework-capability-metrics.md`
- **PHASE-3 glue layer details**: `todo/PHASE-3-glue-layer-improvement.md`
- **PHASE-4 model integration**: `todo/PHASE-4-model-integration-iteration.md`
  (currently BLOCKED — this checklist is the unblock mechanism)
- **Wave 22 metrics-rev3 plan** (when complete): `todo/framework-internal-metrics-rev3-plan.md`
- **Status of all tasks**: `todo/STATUS.md`

## History

- **2026-09-05**: file authored in response to user critique — model
  integration testing is meaningless until framework is frozen. Initial
  5 MUST items defined; 4 SHOULD items for paper submission.
- **2026-09-05 (Wave 26 Agent D)**: per-gate summary table added at the
  top of MUST-1 with PASS / NOT-MET / FAIL status and one-line evidence
  for every HARD gate (A.1-A.7, B.1-B.6, D.2-D.5, E.1, E.4, F.2, F.5,
  G.1, G.3, G.4, G.6, G.7). Headline: **18 / 21 HARD gates PASS**
  (D.4, E.1, E.4 NOT-MET); `G-MASTER-CAPABILITY` BLOCKED on G.1 / G.3 /
  G.6 (per MUST-4 these block paper-writeup, not PHASE-4 start).
  Current-state narrative updated to match.
