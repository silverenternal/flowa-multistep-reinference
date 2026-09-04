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

**Current state**: 12 of 13 audit HARD gates pass (E.1 test-coupled = 0% is NOT MET).
Group G not yet measured (gated as `G-MASTER-CAPABILITY`; see MUST-4).

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
2. **FreqFlow** (Wave 21 F agent) — IN PROGRESS per task list #483-486
3. **MM-FM** (Wave 21 M agent) — PENDING
4. **LineageFlow** — BLOCKED on upstream `core` source (documented in
   `todo/models/lineageflow.md`)

**Acceptance for MUST-2**:
- Kanzi ✓, FreqFlow ✓, MM-FM ✓ (all 3 NEW models pass the 6 per-model checks)
- LineageFlow: documented as BLOCKED is acceptable IF a "BLOCKED-replace-with-X"
  decision is recorded in this checklist (e.g., "use FreqFlow as 4th family proxy")
- **OR**: LineageFlow unblocked via upstream fix / workaround

**Evidence file**: each model's per-model analysis + `docs/PLUG_IN_YOUR_MODEL.md`.

**Current state**: 1/4 (Kanzi) confirmed done; FreqFlow + MM-FM in Wave 21.

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

**Current state**: NOT STARTED. Blocked on Wave 21 completion (need 3 adapters to see patterns).

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
