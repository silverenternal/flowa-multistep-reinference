# Phase 3 — Glue layer improvement (per model, in Phase 2 ranking order)

**Status:** partial (Wave 24 Agent B: 4 framework-core glue modules + 84 unit tests shipped in `adaptive_reflow/core/`; per-adapter refactor deferred per MUST-3 follow-up gate — gated on ≥2 of 4 RANKING adapters existing; MM-FM BLOCKED, LineageFlow BLOCKED on `core`)
**Depends on:** Phase 2 complete (RANKING.md + per-model analysis files)
**Owner:** framework maintainer
**Goal:** for each model in Phase 2 ranking order, **improve the glue layer**
*before* integration. This is the key insight from the user's 4-phase plan:
"如果前面确保做的足够好的话我们只要好好改胶水层就好了" — if Phase 1-2 is done well,
Phase 4 integration is "just" glue.

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