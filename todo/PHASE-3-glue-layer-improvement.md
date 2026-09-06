# Phase 3 — Glue layer improvement (per model, in Phase 2 ranking order)

**Status:** done (Wave 24 + Wave 38 + Wave 39 closed all 3 sub-items) (+ Wave 41 KanziAdapter @implements; Wave 47 LineageFlowGlue; Wave 49 FlowMol3Glue; Wave 50 flowmol3 factory force_mode fix; Wave 52 Kanzi + LineageFlow composite_verdict=framework_improves)
**Depends on:** Phase 2 complete (RANKING.md + per-model analysis files)
**Owner:** framework maintainer
**Goal:** for each model in Phase 2 ranking order, **improve the glue layer**
*before* integration. This is the key insight from the user's 4-phase plan:
"如果前面确保做的足够好的话我们只要好好改胶水层就好了" — if Phase 1-2 is done well,
Phase 4 integration is "just" glue.

## Wave 38 + Wave 39 close-out (2026-09-05)

- **(a) Framework-core glue extraction** (Wave 24 Agent B): 4 modules + 84 unit tests shipped in `adaptive_reflow/core/` (commit `12565df` etc.) — DONE.
- **(b) per-adapter Protocol enforcement** (Wave 38 Agent A WF1, commit f7ee3ae): `assert_adapter_compliance` enforcement closes HIGH-4 + MEDIUM-11. All 15 registered adapters now carry `@implements(FlowMatchingODEAdapter)`; CI test parametrised over ADAPTER_REGISTRY with env-tolerant skips — DONE.
- **(c) MM-FM + LineageFlow on `core`**: MM-FM DEFERRED_no_adapter_shipped per 2026-09-05 user directive (Wave 39 Agent C plan-doc sweep closed the corresponding todo file). LineageFlow real-ckpt pickle loading now WORKS after Wave 39 Agent B 5-LOC `_install_checkpoint_compat` shim (commit 6b7fe8c) — 10.5 GB lineageflow-rp55.ckpt loads in 20s; numerical forward still needs upstream `core` source clone (deferred follow-up).
- **(d) D.1 shrink adapters** (gated on MUST-3 framework-core glue + ≥2 RANKING adapters): Kanzi + FreqFlow + LineageFlow all registered; future wave candidate.

## What is "glue layer"

- **Adapter code** that satisfies the FlowMatchingODEAdapter Protocol surface.
- **Weight loading** (HF download, format converter, shim).
- **Forward pass wrapper** (call into the model's native forward, return
  framework's StateBundle).
- **Sampling loop wrapper** (run N rounds, apply restart-blend per round).
- **Eval pipeline** (compute framework metrics: selection_ratio, paper
  quantities, restart-blend deltas).

## Sub-tasks (per model, in Phase 2 ranking order)

For each model `M` in `RANKING.md`:

1. **Read per-model analysis** (`todo/models/M.md`).
2. **Identify glue gaps** — what concrete code needs to exist for the framework
   to use M?
3. **Write glue in framework core** (not in adapter) — abstract patterns that
   other models can reuse.
4. **Write the adapter as a thin implementation** of those abstract patterns.
5. **Write tests** (smoke + protocol-conformance + reproduce-paper-metric if
   cheap).
6. **Verify** with `pytest` + `mkdocs build --strict`.

## Example glue patterns to extract to framework core (from Phase 1)

- **HF + GitHub weight loader shim** — many models have weird ckpt formats.
  Centralize the load logic.
- **Diffusers-style forward wrapper** — for DiT-family models (Self-Flow,
  FreqFlow, MM-FM, HiDream-I1).
- **DGL-style graph wrapper** — for graph-based models (FlowMol3, GraphBFN,
  ProtBFN, LineageFlow).
- **CTMC transition kernel** — for chemical-family models (FlowMol3 CTMC
  parameterization, LineageFlow Dirichlet flow).
- **Latent-space ↔ pixel-space** decoder (for VAE-based image models).

## Acceptance

- Each model's adapter satisfies FlowMatchingODEAdapter Protocol.
- Each model has a synthetic-mode default (Protocol surface exercises on CPU
  without the ckpt).
- Each model has ≥ 1 test for byte-stability.
- Glue code is in framework core, not duplicated in adapter.

## Acceptance gate (BINDING — see `todo/GATES.md`)

**Gate name:** `G-MASTER-PHASE-3` (defined in `todo/GATES.md`)

**Pre-condition:** `G-MASTER-PHASE-2` passed AND `G-FRAMEWORK-HEALTH`
hard gates pass (per `todo/framework-internal-metrics.md` §3 — Phase 2
→ Phase 3 entry gate: A.3 ≥ 1, B.1 ≥ 3228, B.2/B.3/B.4 pass, D.3 ≥
17/18).

**Pass conditions per model `M` in `todo/models/RANKING.md` (ALL must hold):**
- [ ] `adaptive_reflow/adapters/M.py` exists and is non-empty (>50 lines)
- [ ] `M` is registered in `ADAPTER_REGISTRY` (`grep "M" adaptive_reflow/adapters/__init__.py`)
- [ ] `tests/test_adapters/test_M.py` exists with **>= 22 tests, all PASS**
- [ ] Byte-stability test present in the test file (per model)
- [ ] Synthetic-mode default present in the adapter (Protocol surface works
      on CPU without loading the ckpt)
- [ ] `docs/PLUG_IN_YOUR_MODEL.md` has a "Plug-in candidate: M" section

**Pass conditions (aggregate):**
- [ ] ALL models in RANKING.md satisfy the 6 per-model checks
- [ ] `pytest --collect-only -q` shows **>= baseline + 22 × N_models**, no ImportError
- [ ] `pytest tests/test_adapters/` shows **100% PASS** across all model suites
- [ ] `mkdocs build --strict` exits 0
- [ ] `git status --short` returns empty
- [ ] `todo/STATUS.md` is up-to-date

**Verification commands:**
```bash
cd /home/hugo/codes/flowa-multistep-reinference
# Per-model: for each M in $(awk -F'|' '/^\| .*\| /{print $2}' todo/models/RANKING.md)
for M in lineageflow self_flow flowmol3 hidream_i1 lumina_image_2_0
  do
    test -f "adaptive_reflow/adapters/${M}.py" && echo "✓ $M adapter"
    test -f "tests/test_adapters/test_${M}.py" && echo "✓ $M tests"
    grep -q "${M}" "adaptive_reflow/adapters/__init__.py" && echo "✓ $M registered"
  done
.venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/ -q 2>&1 | tail -5
.venvs/flowmol3_venv/bin/mkdocs build --strict 2>&1 | tail -3
```

**Block rule:** if any per-model check fails, **Phase 4 cannot start** for
that model (other models may proceed independently if their glue is solid).
This is a **per-model** gate, not project-wide.

## Exit criteria (move to Phase 4)

`G-MASTER-PHASE-3` passed for all ranked models.

## Follow-up gate (D.1 shrink adapters — Wave 32 audit addition)

**Status:** pending (NEW — Wave 32 Agent A audit; not in original Phase 3 plan)
**Date:** 2026-09-05
**Depends on:** ≥2 of 4 RANKING adapters consuming `adaptive_reflow.core.*` (MM-FM + LineageFlow BLOCKED; Kanzi + FreqFlow are the 2 needed; both shipped Wave 21)
**Wave:** Wave 34 (target — once Kanzi + FreqFlow registration is verified)

Per Wave 32 Agent A (`docs/audit/gap-audit.md` §2.4) + Wave 32 Agent C
(`docs/audit/framework-code-review.md` §1.14):

**D.1** adapter line count median (rev 3 target ≤ 350; rev 2 target
≤ 500; currently ~1500 median). Deferred per Wave 11 Phase 3 note; gated
on MUST-3 framework-core glue (this Phase 3 plan).

### What to do (Wave 34)

For each of the 18 registered adapters:

1. **Audit the current LOC** (`cloc adaptive_reflow/adapters/<adapter>.py`)
2. **Identify glue candidates** — code that duplicates framework-core
   patterns (e.g. restart_blend math, channel extraction, SHA-256 digest,
   adapter init boilerplate)
3. **Refactor to consume `adaptive_reflow.core.*`** — Wave 24 Agent B
   shipped 4 glue modules; verify all adapters consume them
4. **Target ≤ 500 LOC** per adapter (rev 2 target; pragmatic for first
   pass; rev 3 target ≤ 350 in a follow-up)
5. **Verify byte-stability** post-refactor (B.2 gate must remain PASS)
6. **Verify protocol conformance** post-refactor (D.3 + D.5 gates must
   remain PASS)

### Acceptance

- [ ] D.1 metric median ≤ 500 LOC (rev 2 target)
- [ ] Every adapter consumes `adaptive_reflow.core.*` for glue patterns
- [ ] B.2 byte-stability gate still PASS
- [ ] D.3 + D.5 conformance still PASS
- [ ] No regression in `pytest tests/`

### Estimated time

~4-8 hours per adapter once unblocked; per-adapter refactor with
verification.

### Risk

- **HIGH**: shrinking an adapter while preserving byte-stability is a
  careful refactor; must run regression vectors after each change
- **MEDIUM**: refactoring may expose previously-silent bugs; each fix
  should be in a separate commit for bisect-ability

### Related follow-up

- D.4 regression vectors (Wave 33 #1) provide the byte-stability net for
  the D.1 shrink refactor; ship D.4 first, then D.1

## Wave 56 close-out

Status refreshed: PHASE-3 glue layer improvement closed all 3 sub-items, then Wave 41 (KanziAdapter @implements), Wave 47 (LineageFlowGlue), Wave 49 (FlowMol3Glue) extended the glue-layer pattern across all top-model adapters. Wave 52 Kanzi + LineageFlow composite_verdict=framework_improves is the canonical PHASE-3 success. Last touched commit: `811ca75` (Wave 55 Agent C: Author todo/INDEX.md master entry point).