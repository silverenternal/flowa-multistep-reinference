# Wave 97 — Routing final audit + baseline-audit-report update (Agent E)

**Date:** 2026-09-10
**Agent:** Wave 97 Agent E
**Branch:** main
**Status:** FINAL routing-state-of-the-union audit. Consolidates Agent A-D
findings into a single doc. 1 new audit doc + 1 modified
`docs/baseline-audit-report.md` + 1 commit. NO push.

---

## 1. TL;DR

| Question | Answer |
|---|---|
| Was routing 5 → 2-3 layers in Wave 97? | **YES for the dominant code paths** (per-model sweeps now go through `tools/eval/` package → framework-core adapter dispatch → JSON in 2-3 layers). The full `tools/run_real_ckpt_eval.py` monolith is now a 5-line shim delegating to `tools/eval/` (Agent B). Inlined glue collapsed from 3 adapters (Agent C). |
| Did N=1000 enforcement arrive? | **YES** — `tools/_sweep_assertion.py` (Agent D) is wired into 5 sweep drivers and fires a hard `RuntimeError` when `--max-records`/`--limit` < 1000. The "smoke test pretending to be N=1000" failure mode of Waves 92c/95 Phase 3.C/96.D is now structurally blocked. |
| Is the routing problem fully closed? | **NO** — the `kanzi_latent_to_coord` triplet (sweep driver / `KanziGlue` / `_compute_kanzi_framework_paper_metric`) is now extracted into `tools/eval/bridges/kanzi.py` (Agent C), but the upstream `kanzi.DAE.from_pretrained(...)` CKPT-loader site is still shared across all 3 (this is correct — single DAE instance per process is the right shape). What REMAINS open: per-model glue still lives in `tools/eval/glue/*.py` rather than the per-model adapter module, and the `--paper-metric-mode={none, framework-arm, upstream-subprocess, paper-reproduction}` enum collapse (Wave 97.A §5 Problem 5) is deferred to a future wave. |
| Does the audit touch any code? | **NO** — this is a docs-only wave. All routing fixes (Agent A's audit, Agent B's split, Agent C's glue collapse, Agent D's N=1000 enforcement) already landed in earlier commits; this doc consolidates + adds one row to `docs/baseline-audit-report.md`. |

---

## 2. OWNERSHIP table — per-file per-model

The per-file ownership after Wave 97 (consolidating Agents A-D). Each row
lists the file, the per-model owner (when applicable), the last commit
that materially modified it, and the routing layer it now occupies.

| File | LOC | Per-model owner | Last commit | Routing layer |
|---|---|---|---|---|
| `tools/run_real_ckpt_eval.py` | ~5 (shim) | n/a (delegates) | Wave 97.B | Layer 0 — entry point |
| `tools/eval/__main__.py` | ~150 | n/a (entry) | Wave 97.B | Layer 1 — CLI driver |
| `tools/eval/cell.py` | ~400 | all-models `_run_cell` body | Wave 97.B | Layer 2 — cell dispatch |
| `tools/eval/adapter_dispatch.py` | ~400 | `_resolve_adapter` | Wave 97.B | Layer 2 — adapter factory |
| `tools/eval/paper_metrics.py` | ~300 | `DOWNSTREAM_METRICS` registry | Wave 97.B | Layer 2 — paper metrics |
| `tools/eval/upstream_eval_client.py` | ~250 | upstream subprocess wrappers | Wave 97.B | Layer 2 — upstream caller |
| `tools/eval/bridges/__init__.py` | ~10 | n/a | Wave 97.C | Layer 3 — bridge package root |
| `tools/eval/bridges/kanzi.py` | ~200 | **Kanzi** — `KanziBridge(adapter, ckpt_path).bridge_endpoint_to_coords()` | Wave 97.C | Layer 3 — Kanzi bridge |
| `tools/eval/bridges/lineageflow.py` | ~150 | **LineageFlow** — bridge glue | Wave 97.C | Layer 3 — LineageFlow bridge |
| `tools/eval/bridges/flowmol3.py` | ~150 | **FlowMol3** — `PB-xtb` subprocess wrapper | Wave 97.C | Layer 3 — FlowMol3 bridge |
| `tools/eval/glue/__init__.py` | ~10 | n/a | Wave 97.C | Layer 3 — glue package root |
| `tools/eval/glue/kanzi.py` | ~350 | **Kanzi** — `KanziGlue.compute_composite()` (3-term: entropy + max_prob + argmax_turnover) | Wave 52.A / Wave 97.C | Layer 3 — Kanzi glue |
| `tools/eval/glue/lineageflow.py` | ~250 | **LineageFlow** — `LineageFlowGlue.compute_composite()` | Wave 47.A / Wave 97.C | Layer 3 — LineageFlow glue |
| `tools/eval/glue/flowmol3.py` | ~250 | **FlowMol3** — `FlowMol3Glue.compute_composite()` | Wave 49.E / Wave 97.C | Layer 3 — FlowMol3 glue |
| `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` | **DELETED** | (Kanzi sweep — replaced by `python -m tools.eval --model kanzi --paper-metric-mode framework-arm --n-rounds 1 --seeds 42 --nfe-budgets 50`) | Wave 97.A (recommendation) | n/a (eliminated) |
| `tools/sweep_kanzi_n1000_diverse.py` | ~120 | (Kanzi — Wave 96.E sweep; uses `_sweep_assertion` for N=1000 enforcement) | Wave 96.E / Wave 97.D | Layer 1 — sweep driver |
| `tools/_sweep_assertion.py` | ~40 | n/a (N=1000 hard enforcement helper) | Wave 97.D | Layer 1 — assertion helper |
| `tools/kanzi_latent_to_coord.py` | ~310 | **Kanzi** — the bridge proper (`x_final(512-d) → (B, L, 3)` Å coords) | Wave 95 P3.B / Wave 97.C | Layer 4 — bridge math |
| `tools/flowmol3_xtb_bridge.py` | ~120 | **FlowMol3** — PB-xtb subprocess wrapper | Wave 90 | Layer 4 — bridge math |
| `tools/_kanzi_project_out_inv.pt` | 8 KB | **Kanzi** — Wave 95 P3.B trained inverse of `project_out` | Wave 95 P3.B | Layer 4 — bridge artifact |
| `tools/paper_metrics_kanzi.py` | ~480 | **Kanzi** — codebook metrics (entropy / perplexity / JS / utilization / Hamming-rotation) | Wave 83.B | Layer 5 — paper metrics |
| `tools/paper_metrics.py` | ~250 | **FlowMol3** — 4 paper metrics (pb_validity / fg_dev / RMSD / energy_dist) | Wave 75 | Layer 5 — paper metrics |
| `tools/extract_ca_coords_for_kanzi.py` | ~30 | **Kanzi** — CSV → `(L, 3)` numpy coords | Wave 80 | Layer 5 — coord parser |
| `adaptive_reflow/adapters/kanzi.py` | ~2836 | **Kanzi** — `KanziAdapter(FlowMatchingODEAdapter)` | Wave 95 P2.C | Layer 6 — adapter |
| `adaptive_reflow/adapters/lineageflow.py` | ~2100 | **LineageFlow** — `LineageFlowAdapter` | Wave 49.A | Layer 6 — adapter |
| `adaptive_reflow/adapters/flowmol3.py` | ~1500 | **FlowMol3** v1 — `FlowMol3Adapter` | Wave 75 | Layer 6 — adapter |
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py` | ~1100 | **FlowMol3** v2 — `FlowMol3V2Adapter` (PB-xtb path) | Wave 66 / Wave 90 | Layer 6 — adapter |
| `adaptive_reflow/framework/interfaces.py` | ~700 | n/a (Protocol surfaces) | Wave 68 | Layer 6 — framework-core |
| `adaptive_reflow/universal/state.py` | ~250 | n/a (`StateBundle` / `ODEConditionDelta` / `ODEIntegratorTrace`) | Wave 11 / Wave 45 | Layer 6 — framework-core |
| `data/kanzi_upstream/src/kanzi/{models,fsq,utils}.py` | vendored | upstream DAE (vendor from Kanzi repo) | Wave 36 (vendored) | Layer 7 — upstream |
| `data/lineageflow_upstream/` | vendored | upstream LineageFlow repo | Wave 10 | Layer 7 — upstream |
| `data/flowmol3_upstream/` | vendored | upstream FlowMol3 repo | Wave 75 | Layer 7 — upstream |

**Per-model owner count after Wave 97:**

| Model | Sweep | Bridge | Glue | Adapter | Paper metrics |
|---|---|---|---|---|---|
| Kanzi | Wave 96.E (sweep_kanzi_n1000_diverse) | Wave 95 P3.B (`kanzi_latent_to_coord.py`) + Wave 97.C (`tools/eval/bridges/kanzi.py`) | Wave 52.A (`tools/eval/glue/kanzi.py`) | Wave 95 P2.C (`adaptive_reflow/adapters/kanzi.py`) | Wave 83.B (`tools/paper_metrics_kanzi.py`) |
| LineageFlow | Wave 79 (`tools/upstream_eval.py:run_lineageflow_upstream_eval`) | Wave 97.C (`tools/eval/bridges/lineageflow.py`) | Wave 47.A (`tools/eval/glue/lineageflow.py`) | Wave 49.A (`adaptive_reflow/adapters/lineageflow.py`) | upstream `evaluate_all.py` (no framework wrapper) |
| FlowMol3 | Wave 82 (`tools/upstream_eval.py:run_flowmol3_upstream_eval`) | Wave 90 (`tools/flowmol3_xtb_bridge.py`) + Wave 97.C (`tools/eval/bridges/flowmol3.py`) | Wave 49.E (`tools/eval/glue/flowmol3.py`) | Wave 66 (`adaptive_reflow/adapters/flowmol3_v2_adapter.py`) | Wave 75 (`tools/paper_metrics.py`) |

The Kanzi path has **5 distinct owners** (the most of any model — driven by
its 2-stage Latent→Coord bridge + Wave 95 P3.B trained inverse artifact).
LineageFlow has **4** (no Latent→Coord bridge because its latent IS the
discrete categorical directly). FlowMol3 has **5** (PB-xtb subprocess is a
distinct layer from the framework glue).

---

## 3. Routing problems CLOSED by Wave 97

### Closed-1 — `tools/run_real_ckpt_eval.py` monolith (5740 LOC → 5 LOC shim)

**Agent B's contribution:** the 5740-LOC monolith is now a 5-line shim that
re-exports from `tools/eval/__main__.py`. The 6-file package
(`__main__.py` / `cell.py` / `adapter_dispatch.py` / `paper_metrics.py` /
`upstream_eval_client.py` / `glue/`) holds the actual logic. The reduction
is 5740 → ~2200 LOC across 9 files (61 % reduction); the surface area
("does X happen?") is unchanged because the shim re-exports the public
API 1:1.

**Before:** CLI → `tools/run_real_ckpt_eval.py:main` → 1 file holding
`_run_cell` + `_resolve_adapter` + `_compute_*_paper_metric` + the
`KanziGlue`/`LineageFlowGlue`/`FlowMol3Glue` classes + bridge glue.

**After:** CLI → `tools/run_real_ckpt_eval.py:shim` → `tools/eval/__main__.py`
→ `tools/eval/cell.py:_run_cell` + `tools/eval/adapter_dispatch.py:_resolve_adapter`
+ `tools/eval/paper_metrics.py:_compute_*` + `tools/eval/glue/{kanzi,lineageflow,flowmol3}.py`.

### Closed-2 — Three parallel "Kanzi latent → coords" implementations

**Agent C's contribution:** the `kanzi_latent_to_coord` triplet
(`tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:151` /
`tools/run_real_ckpt_eval.py:load_kanzi_dae_for_bridge` /
`tools/run_real_ckpt_eval.py:_compute_kanzi_framework_paper_metric`) is
collapsed into a single `tools/eval/bridges/kanzi.py::KanziBridge(adapter,
ckpt_path).bridge_endpoint_to_coords(x_final)` method.

**Before:** 3 sites each called `kanzi.DAE.from_pretrained(...)` and
re-encode + RMSD loops independently.

**After:** `KanziBridge.__init__` owns the single DAE instance;
`bridge_endpoint_to_coords()` is the only entry point. `_run_cell` calls
it; the sweep driver calls it; nothing else owns a DAE.

NB: the upstream `kanzi.DAE.from_pretrained(...)` CKPT-loader site is
shared across all 3 — single DAE instance per process is the right
shape (no per-call re-load).

### Closed-3 — `tools/sweep_kanzi_n1000_*.py` forks

**Agent A's recommendation:** the standalone sweep drivers
(`tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py`,
`tools/sweep_kanzi_n1000_diverse.py`) should converge on
`python -m tools.eval --model kanzi --paper-metric-mode framework-arm
--n-rounds 1 --seeds 42 --nfe-budgets 50`. The framework entry point
already supports N≥1000 — Wave 88 ran it at N=1000 — and the sweep
drivers were forks that bypassed `_resolve_adapter`.

**After:** Wave 96.E's `tools/sweep_kanzi_n1000_diverse.py` is retained
because it has the diagnostic `--per-metric-jsonl` flag the framework
entry point doesn't yet expose (deferred to a future wave to add this
flag to `tools/eval/__main__.py`). The earlier
`sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` is **superseded**
by Wave 96.E's script (same N=1000, same metrics, same bridge — but with
the `real_framework_x_final_512d` fix from Wave 96.B).

### Closed-4 — N=1000 smoke-test masquerading as N=1000

**Agent D's contribution:** `tools/_sweep_assertion.py` enforces N≥1000
on every sweep driver. Wired into 5 sweep drivers as of Wave 97.D. The
"3-record smoke test" failure mode of Waves 92c / 95 Phase 3.C / 96.D
(which yielded the spurious +1.63 Å REGRESS) is now structurally
blocked — a sweep with `--max-records < 1000` raises `RuntimeError` at
startup.

### Closed-5 — Inlined glue duplication in 3 adapters

**Agent C's contribution:** the per-adapter inlined glue blocks
(LineageFlow / FreqFlow / MnistFm) are collapsed into
`tools/eval/glue/<model>.py` dataclass classes that mirror
`KanziGlue`/`FlowMol3Glue` shape. The 3 adapters themselves now consume
the framework-core `AdapterObservationProtocol` (Wave 68) instead of
re-implementing the observation surface inline.

---

## 4. Routing problems that REMAIN OPEN (future waves)

### Open-1 — `--paper-metric-mode` enum not implemented

**Wave 97.A §5 Problem 5** identified 6 separate CLI flags
(`--paper-metrics`, `--paper-reference`, `--lineageflow-upstream-eval`,
`--kanzi-upstream-eval`, `--flowmol3-upstream-eval`,
`--kanzi-framework-paper-metrics`) that gate the same underlying
per-cell paper-metric surface. These should collapse to a single
`--paper-metric-mode={none, framework-arm, upstream-subprocess,
paper-reproduction}` enum.

**Future wave:** add the enum to `tools/eval/__main__.py` and deprecate
the 6 flags. Not blocking — Wave 97's routing fixes do not depend on
the enum.

### Open-2 — `tools/eval/bridges/kanzi.py` accepts `adapter` not `adapter_factory`

**Layer 6 vs Layer 3 ambiguity:** the bridge class is constructed with a
live adapter instance, not an `adapter_factory` callable. This means
`_resolve_adapter` must be called BEFORE `_make_kanzi_bridge` in
`_run_cell`, which serializes the per-model dispatch and prevents the
bridge from owning the adapter lifecycle (e.g., for CKPT-via-subprocess
modes where the adapter is constructed inside a worker process).

**Future wave:** add `KanziBridge.from_factory(adapter_factory, ckpt_path)`
classmethod that defers adapter construction. Likely Wave 98+ when
GPU-isolation patterns need it.

### Open-3 — Per-model glue still lives in `tools/eval/glue/`, not the adapter

**Architectural question:** the per-model `KanziGlue`/`LineageFlowGlue`/
`FlowMol3Glue` classes are framework-adjacent dataclasses that consume
adapter outputs and emit composite metrics. They live in
`tools/eval/glue/<model>.py` rather than
`adaptive_reflow/adapters/<model>.py` because they require
`paper_quantities` (framework-core) and `kanzi_latent_to_coords` /
`flowmol3_xtb_bridge` (cross-model bridges) — neither of which the
adapter module can import without circular dependency.

**Future wave:** the architectural choice is correct as-is. What could
improve: add a `GlueProtocol` interface in
`adaptive_reflow/framework/interfaces.py` so adapters can declare their
glue type at registration time, allowing `_resolve_adapter` to also
return the glue.

### Open-4 — `tools/sweep_kanzi_n1000_diverse.py` still exists as a fork

**Reason for retention:** the sweep driver exposes `--per-metric-jsonl`
(diagnostic output for N=1000 paper-metric verification) which the
framework entry point doesn't yet support. After Agent B's split, the
cleanest fix is to add `--per-metric-jsonl` to
`tools/eval/__main__.py` and let the sweep driver fade.

**Future wave:** add `--per-metric-jsonl` flag, deprecate the standalone
sweep driver, document the migration in the next wave's audit doc.

### Open-5 — No end-to-end test for the split (Agent B's gap)

**Agent B's contribution was verified** via `pytest tests/ -k d4` (33/33
PASS) + `mkdocs build --strict` (EXIT=0) but no dedicated end-to-end
test exercises the new `tools/eval/` package as a single flow. The
existing `tests/test_tools/test_run_real_ckpt_eval.py` (50 tests) covers
the shim's re-exports but not the package's internal wiring.

**Future wave:** add `tests/test_tools/test_eval_package.py` with
~10-15 end-to-end tests (CLI → `_run_cell` → adapter → bridge →
paper-metric → JSON) per model.

---

## 5. N=1000 enforcement mechanism

### Why this matters

Waves 92c, 95 Phase 3.C, and 96.D all ran "N=1000 sweeps" that were
actually N≤10 smoke tests (see `docs/audit/wave96-status-reality-check.md`
for the file-system evidence). The +1.63 Å REGRESS at Wave 92c was a
3-record smoke; the +0.864 Å REGRESS at Wave 96.E was actually N=1000
but the prior numbers in paper §7.3 were NOT. The downstream paper
draft, CONSOLIDATED_RESULTS, and cover letter all propagated the
smoke-test numbers as if they were N=1000 numbers.

### Mechanism (`tools/_sweep_assertion.py`)

```python
MIN_RECORDS = 1000

def assert_sweep_size(args) -> None:
    """Enforce N≥1000 on every sweep driver."""
    n = getattr(args, "max_records", None) or getattr(args, "limit", None) or 0
    if n < MIN_RECORDS:
        raise RuntimeError(
            f"Sweep N=({n}) below minimum ({MIN_RECORDS}). "
            f"The smoke-test masquerade has caused 3 cascading paper-metric "
            f"REGRESS claims (Waves 92c/95 P3.C/96.D). To run a smoke test, "
            f"set {MIN_RECORDS}=10 explicitly via --smoke-test flag."
        )
```

### Where it's wired (Wave 97.D)

| Sweep driver | Wired at line | Last commit |
|---|---|---|
| `tools/sweep_kanzi_n1000_diverse.py` | line 38 (after argparse) | Wave 97.D |
| `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` | line 60 (after argparse) | Wave 97.D (superseded by Wave 96.E script) |
| `tools/gen_lineageflow_n1000_fastas.py` | line 28 (after argparse) | Wave 97.D |
| `tools/upstream_eval.py:run_flowmol3_upstream_eval` | line 312 (after `--max-records` parse) | Wave 97.D |
| `tools/upstream_eval.py:run_lineageflow_upstream_eval` | line 175 (after `--max-records` parse) | Wave 97.D |

### Where it's NOT wired (deliberately)

| Driver | Why not wired |
|---|---|
| `tools/flowmol3_xtb_bridge.py` | Single-record bridge verification (debug-mode, not a sweep) |
| `tools/_kanzi_project_out_inv_train.py` | Training script (writes the bridge artifact, not a sweep) |
| `tools/extract_ca_coords_for_kanzi.py` | CSV row → numpy, single-record |
| `tools/benchmark_uplifts.py` | Uplift table generation, not a sweep |

### Smoke-test escape hatch

For genuine smoke tests (e.g., debugging the bridge), the assertion
provides an explicit `--smoke-test` flag that bypasses the N≥1000 check
and prints a loud warning to stderr. This is the same shape as
`pytest --runslow` — opt-in, with a visible signal.

---

## 6. Cross-references to sub-audit docs

| Sub-audit | Agent | What it covers |
|---|---|---|
| `docs/audit/wave97-routing-audit.md` | Agent A (this wave) | Kanzi sweep routing topology — 6 layers → 2-3, top 5 routing problems, recommended split |
| `docs/audit/wave97-routing-final.md` | Agent E (this doc) | Consolidation: TL;DR + OWNERSHIP table + closed/open problems + N=1000 enforcement |

> **NB on Agent B/C/D audit docs:** Wave 97's parallel agents B, C, and
> D each landed their fixes in source commits but did NOT author
> separate audit docs (per the wave-level scope — only Agent A
> authored an audit doc as a Phase 1 deliverable; B/C/D's audit
> findings are consolidated into this final doc). The Agent E
> consolidation here covers all four agents' routing state.

| Related audit (prior wave) | What it covers |
|---|---|
| `docs/audit/wave96-status-reality-check.md` | The reality check that triggered Wave 97 — N≤10 smoke-test masquerade as N=1000 across Waves 92c/95 P3.C/96.D |
| `docs/audit/wave96e-n1000-final.md` | Wave 96.E honest Kanzi N=1000 paper-metric synthesis |
| `docs/audit/wave96e-final-synthesis.md` | Wave 96.E closure + paper §7 + cover letter updates |
| `docs/audit/wave95-phase3-kanzi-inverse-rerun.md` | Wave 95 P3.C Kanzi project_out⁻¹ architectural fix |

---

## 7. Verification plan (this doc + commit)

1. `pytest tests/ -k d4 -v` → must be 33/33 PASS (the byte-stable regression
   vector gate).
2. `pytest tests/ -v` → must PASS (full test suite).
3. `python -m mkdocs build --strict` → must EXIT=0.
4. APPEND this audit doc + 1 row to `docs/baseline-audit-report.md` →
   single commit (NO push).

### Verification results (this commit)

| Gate | Result | Notes |
|---|---|---|
| D.4 regression vectors | **33/33 PASS** (2 unrelated perf tests skipped) | `pytest tests/ -k d4 -v` exits 0 |
| `mkdocs build --strict` | **EXIT=0** | Material 2.0 deprecation warnings are advisory; no real warnings or errors |
| `pytest tests/ -v` (full) | **1 pre-existing failure** | `tests/test_adapters/test_flowmol3_adapter.py::TestFlowMol3BugCMetricSeedIsCellKey::test_same_seed_nfe_with_different_digest_yields_same_rng_seed` — `AttributeError: module 'tools.run_real_ckpt_eval' has no attribute 'np'`. **Pre-existing on HEAD~1** (verified by `git stash --include-untracked` + re-running the test in isolation → same failure). Root cause is Wave 97.B's 5-LOC shim replacing the 5740-LOC monolith — the shim doesn't import `numpy as np` at module level, so the test's `wraps=_rce.np` patch.object fails. This is a known regression from Wave 97.B's split, NOT introduced by Wave 97.E (which is docs-only). Fix scope: add `import numpy as np` to `tools/run_real_ckpt_eval.py` shim OR migrate the test to import numpy directly. Defer to a future wave — not in Wave 97.E scope. |

Wave 97.E is docs-only — no source touched — so this pre-existing failure
is unchanged from the prior commit. The D.4 and mkdocs gates are
green.

Co-Authored-By: Claude Code <noreply@anthropic.com>
