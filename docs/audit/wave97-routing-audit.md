# Wave 97 Agent A — Kanzi sweep routing audit (READ-ONLY)

**Date:** 2026-09-10
**Agent:** Wave 97 Agent A
**Branch:** main
**Status:** READ-ONLY routing topology audit. No source modified, no test
re-run, no commit. Audit doc + 1 commit only.

---

## 1. TL;DR

| Question | Answer |
|---|---|
| CLI the user runs | `.venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py --max-records 1000 --output-dir /tmp/test_kanzi_sweep/` (note: actual flag is `--limit`, not `--max-records`) |
| Layers traversed (CLI → JSON) | **6 layers**: CLI driver, sweep loop, adapter (KanziAdapter), bridge (`kanzi_latent_to_coord`), upstream DAE round-trip, paper metrics. Target = 2-3. |
| Most-affected monolith | `tools/run_real_ckpt_eval.py` (5740 LOC) — contains the parallel `KanziGlue`, `load_kanzi_dae_for_bridge`, `_compute_kanzi_framework_paper_metric`, `_compute_kanzi_real_metric`, `_compute_kanzi_composite`, and `_run_cell`'s `kanzi_framework_paper_metrics` block. |
| Test coverage of Kanzi path | `tests/test_tools/test_kanzi_latent_to_coord.py` (12 tests) — PASS. `test_run_real_ckpt_eval.py` (50 tests) — covers inline glue via `_run_cell` paths. **Gap**: the sweep driver itself has no test file. |
| Worst routing problem | Three parallel "Kanzi latent → coords" implementations (sweep driver, `kanzi_latent_to_coord.kanzi_latent_to_coords`, `KanziGlue.with_bridge`+`load_kanzi_dae_for_bridge`) — three files, three CKPT-loader sites, three extraction paths. |

The framework-vs-baseline gap on the **paper-metric reconstruction axis** is
honestly measured as **+0.864 Å** (Wave 96.E). Closing it further requires a
*model-side* change (not a sweep fix), but the **routing topology itself is
inflated** by 2-3× over what it should be, and that's the Wave 97.A finding
this doc catalogs.

---

## 2. The 6 layers the Kanzi N=1000 sweep actually traverses

Each entry is `file:line-range` → function/symbol → what it does → what
calls it.

### Layer 1 — CLI driver (sweep script)

| File:line | Symbol | What it does |
|---|---|---|
| `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:134-374` | `main(argv)` | argparse → loads upstream `DAE` → constructs `KanziAdapter` → sweep loop → writes JSON |
| `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:68-76` | `parse_record(line)` | CSV → `(L, 3)` coords numpy array (in-process; not delegated to `tools/extract_ca_coords_for_kanzi.py`) |
| `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:79-95` | `synthesize_x_final_512d(record_idx, *, seed=42, codebook_dim=512)` | **DEPRECATED** σ=1e-3 noise (Wave 96.A collapse root-cause); kept in source for provenance but never called by main |
| `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:98-131` | `real_framework_x_final_512d(adapter, record_idx, *, seed=42)` | **Wave 96.B fix** — returns `trajectory[-1]` from real `KanziAdapter.solve_ode` |
| `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:151` | `dae = DAE.from_pretrained(str(args.ckpt)).eval()` | upstream `DAE` instance (vendored at `data/kanzi_upstream/src/kanzi/`) |
| `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:167-170` | `kanzi_adapter = default_kanzi_adapter(weights_path=args.ckpt, force_mode="torch", num_steps=50, solver="euler")` | `KanziAdapter` factory (sidesteps `_resolve_adapter` in `tools/run_real_ckpt_eval.py:877`) |

### Layer 2 — KanziAdapter (model-side layer)

| File:line | Symbol | What it does |
|---|---|---|
| `adaptive_reflow/adapters/kanzi.py:1154-2748` | `class KanziAdapter(FlowMatchingODEAdapter)` | the 2836-LOC adapter — owns the GPT-prior restart policy, native-state LRU cache, integration dispatch |
| `adaptive_reflow/adapters/kanzi.py:1532-1991` | `def build_initial_state(batch_id, sample_id)` | constructs the bundle |
| `adaptive_reflow/adapters/kanzi.py:1991-2150` | `def solve_ode(state, condition, *, seed)` | runs the integrator (Euler/Heun) and populates `_native_states[digest]['trajectory']` |
| `adaptive_reflow/adapters/kanzi.py:2151-2259` | `def observe_endpoint(trace, state)` | typed `ENDPOINT_BUNDLE` observation (Wave 68 surface) |
| `adaptive_reflow/adapters/kanzi.py:2362-2526` | `def observe_entropy_reduction(trace, paper_quantities, *, reference_theta=None)` | per-position Mahalanobis reduction (Wave 95 Phase 2.C); **NOT called by sweep driver** |
| `adaptive_reflow/adapters/kanzi.py:2532-2748` | `def observe(trace, state, paper_quantities, *, strategies, theta_before, theta_after)` | unified `AdapterObservationProtocol` (Wave 68 Phase 2) — returns tuple of `ObservationResult`; **NOT called by sweep driver** |
| `adaptive_reflow/adapters/kanzi.py:2757-2784` | `def default_kanzi_adapter(*, weights_path, force_mode, num_steps, family_id, solver)` | factory |
| `adaptive_reflow/universal/state.py:110-250` | `StateBundle`, `ODEConditionDelta`, `ODEIntegratorTrace` | the 3 framework-core state types the adapter consumes |

### Layer 3 — sweep loop (per-record)

| File:line | Symbol | What it does |
|---|---|---|
| `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:181-264` | (inline in `main`) | reads `--input` CSV, for each record: calls Layer 1 (`real_framework_x_final_512d`), then Layer 4 (bridge), then re-encode (Layer 5) |
| `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:198-208` | (try/except for `kanzi_latent_to_coords`) | bridge-failure capture: `n_skipped += 1; skip_reasons[reason] += 1` |
| `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:217-228` | `dae.encode(coords_BLD, preprocess=False)` | re-encode round-trip for codebook metrics |
| `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:231-244` | `dae.decode(idx_BL)` + `kabsch_rmsd(pred, recon)` | reconstruction RMSD (round-trip identity) |

### Layer 4 — bridge (`kanzi_latent_to_coord`)

| File:line | Symbol | What it does |
|---|---|---|
| `tools/kanzi_latent_to_coord.py:72-238` | `def kanzi_latent_to_coords(latent, decoder, fsq_quantizer, *, n_steps=100, noise_weight=0.45, cfg_weight=1.0, score_weight=1.0, seed=0)` | **THE BRIDGE** — `x_final(512-d)` → `(B, L, 3)` Å coords |
| `tools/kanzi_latent_to_coord.py:189-235` | `with torch.no_grad(): implicit_codebook = fsq_quantizer.implicit_codebook; _apply_project_out_inv(x_flat); torch.cdist(x_4d, codes_4d); decoder.decode(idx_BL, ...)` | 4-line pipeline (in this file) |
| `tools/kanzi_latent_to_coord.py:246-286` | `def _load_project_out_inv()` | lazy-loads `tools/_kanzi_project_out_inv.pt` (8 KB Wave 95 P3.B trained inverse of `project_out`) |
| `tools/kanzi_latent_to_coord.py:289-308` | `def _apply_project_out_inv(x_t)` | `torch.nn.functional.linear(x_t, weight, bias)` |
| `tools/kanzi_latent_to_coord.py:68-69` | `_PROJECT_OUT_INV_PATH`, `_PROJECT_OUT_INV_CACHE` | module-level cache |

### Layer 5 — upstream DAE round-trip (vendored at `data/kanzi_upstream/src/`)

| File:line | Symbol | What it does |
|---|---|---|
| `data/kanzi_upstream/src/kanzi/models.py:353-429` | `class DAE.encode`, `DAE.decode` | the upstream flow autoencoder; `encode(coords) → (mu, log_var, idx)`, `decode(idx) → coords` (nm scale) |
| `data/kanzi_upstream/src/kanzi/fsq.py:89-120` | `class FSQ.implicit_codebook`, `FSQ.codes_to_indices` | 1000-entry codebook `(1000, codebook_dim=4)` |
| `data/kanzi_upstream/src/kanzi/utils.py:3-30` | `kabsch_rmsd(a, b)` | alignment-invariant RMSD |
| `kanzi` import in script line 49 | `from kanzi import DAE, kabsch_rmsd` | vendored package on `sys.path` (script line 46-47 inserts `data/kanzi_upstream/src`) |

### Layer 6 — paper metrics + JSON

| File:line | Symbol | What it does |
|---|---|---|
| `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:287-288` | `compute_codebook_entropy(idx_concat, vocab_size=1000)` | Shannon entropy over all N×L indices (bits) |
| `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:289-290` | `compute_codebook_perplexity(idx_concat, vocab_size=1000)` | `2 ** entropy` |
| `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:291-292` | `compute_codebook_utilization(idx_concat, vocab_size=1000)` | fraction of codebook used |
| `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:296-297` | `compute_codebook_js_distance(idx_pair, vocab_size=1000)` | JS between records 0 and 1 |
| `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:301-363` | `output = {...}` dict | aggregate the 6 metrics into a flat dict |
| `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:365-367` | `out_path.write_text(json.dumps(output, indent=2, sort_keys=False) + "\n", encoding="utf-8")` | **THE JSONL OUTPUT** (single .json file, NOT a per-record jsonl) |
| `tools/paper_metrics_kanzi.py:226-310, 326-396, 398-442, 481-590, 615-694` | `compute_codebook_entropy`, `compute_codebook_perplexity`, `compute_codebook_js_distance`, `compute_codebook_utilization`, `compute_codebook_hamming_rotation_invariance`, `compute_all_codebook_metrics` | the helpers; called by both this script AND by `_compute_kanzi_framework_paper_metric` in `tools/run_real_ckpt_eval.py:3634` |

### Cross-cutting — `tools/run_real_ckpt_eval.py` parallel path

When the user runs `tools/run_real_ckpt_eval.py --kanzi-framework-paper-metrics`
instead of the standalone sweep, the layers map to the same 6, but Layer 1 is
split between the run_real_ckpt_eval main loop (`tools/run_real_ckpt_eval.py:5655-5700`)
and the `_run_cell` body (line 4578-5254), with the Kanzi-specific glue
additionally routing through:

| File:line | Symbol | What it does |
|---|---|---|
| `tools/run_real_ckpt_eval.py:3028-3096` | `def load_kanzi_dae_for_bridge(ckpt_path, *, device="cpu")` | the run_real_ckpt_eval-side bridge loader (parallel to script line 151) |
| `tools/run_real_ckpt_eval.py:3100-3450` | `class KanziGlue` | the Wave 52 composite-metric glue class (frozen dataclass, holds adapter + bridge tuple) |
| `tools/run_real_ckpt_eval.py:3149-3176` | `def with_bridge(self, ckpt_path)` | lazy `KanziGlue` re-construction with `bridge` populated |
| `tools/run_real_ckpt_eval.py:3178-3450` | `def compute_composite(baseline_trace, framework_trace, *, weights, seed, nfe)` | 3-term composite (φ1 entropy + φ2 max_prob + φ3 argmax_turnover) |
| `tools/run_real_ckpt_eval.py:3474-3700+` | `def _compute_kanzi_framework_paper_metric(*, adapter, baseline_trace, framework_trace, seed, nfe, ckpt_path, n_steps=20)` | the run_real_ckpt_eval-side per-cell paper-metric helper (parallels the sweep driver loop at line 181-264) |
| `tools/run_real_ckpt_eval.py:1589-1750` | `def _compute_kanzi_real_metric(...)` | the protein-validity-rate helper (NOT in the sweep driver path) |
| `tools/run_real_ckpt_eval.py:5163-5207` | `_run_cell` body — `if kanzi_framework_paper_metrics and model == "kanzi":` block | the per-cell paper-metric invocation |
| `tools/run_real_ckpt_eval.py:252-330` | `DOWNSTREAM_METRICS["kanzi"]` | the per-model metric registry (Kanzi entry uses adapter_factory `"adaptive_reflow.adapters.kanzi:default_kanzi_adapter"`) |
| `tools/run_real_ckpt_eval.py:877-1070` | `def _resolve_adapter(model, *, force_mode, restart_min_nfe, nfe_budget)` | the framework's adapter dispatch (the sweep driver at line 167 bypasses this) |
| `tools/run_real_ckpt_eval.py:1037` | `"kanzi": {"real": "torch"}` | the force_mode→ckpt-table |

---

## 3. Per-layer ownership, last commit, dependencies, glue, test coverage

| # | File:line | OWNER (Wave / agent) | LAST_MODIFIED (commit + date) | DEPENDENCIES (calls into) | INLINED_GLUE (duplicates framework-core) | TEST_COVERAGE |
|---|---|---|---|---|---|---|
| 1 | `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:134-374` | **Wave 96.B Agent B** (`1f26bf6`) | `1f26bf6` 2026-09-10 "Wave 96.B: fix Kanzi framework endpoint collapse root cause" | `kanzi.DAE`, `kanzi_latent_to_coords`, `paper_metrics_kanzi.compute_*`, `default_kanzi_adapter` | YES — reimplements its own `DAE` load (line 151) AND its own `KanziAdapter` construction (line 167) instead of using `tools/run_real_ckpt_eval.py:_resolve_adapter` | **NONE** — no test file for this script; only `test_kanzi_latent_to_coord.py` covers the bridge |
| 1a | `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:68-76` `parse_record` | **Wave 95 Phase 3.C** | `1f26bf6` 2026-09-10 | stdlib only | YES — duplicates `tools/extract_ca_coords_for_kanzi.py:1-30` | NONE |
| 2 | `adaptive_reflow/adapters/kanzi.py:1154-2748` `KanziAdapter` | **Wave 95 Phase 2.C** (A.3) — `b5c954b` | `b5c954b` 2026-09-10 "Wave 95 Phase 2.C: Kanzi observe_entropy_reduction via per-position Mahalanobis (A.3)" | `FlowMatchingODEAdapter` (universal), `_native_states` (own LRU), upstream Kanzi DAE | partial — `observe_token_indices` (line 2259), `observe_endpoint` (line 2151), `observe_entropy_reduction` (line 2362) coexist with `observe` (line 2532) | **YES** — `tests/test_adapters/test_kanzi.py` (22 tests, Wave 21); `tests/test_tools/test_kanzi_latent_to_coord.py` (12 tests, Wave 91) |
| 3 | `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:181-264` (sweep loop) | **Wave 96.B** | `1f26bf6` 2026-09-10 | `kanzi_latent_to_coords`, `kanzi.DAE`, `kanzi.kabsch_rmsd` | YES — duplicates the `_run_cell` arm of `tools/run_real_ckpt_eval.py:5163-5207` | NONE |
| 4 | `tools/kanzi_latent_to_coord.py:72-308` | **Wave 95 Phase 3.B** (`378dc4a`) | `378dc4a` 2026-09-10 "Wire project_out⁻¹ into kanzi_latent_to_coord.py" | `kanzi.DAE`, `kanzi.FSQ.implicit_codebook`, `torch.cdist` | NO — this IS the bridge (no upstream framework helper to delegate to) | **YES** — `tests/test_tools/test_kanzi_latent_to_coord.py` (12 tests) |
| 4a | `tools/_kanzi_project_out_inv.pt` (8 KB ckpt) | **Wave 95 Phase 3.B** (`378dc4a`) | `378dc4a` 2026-09-10 | trained by `tools/_kanzi_project_out_inv_train.py` | NO (artifacts are not inlined glue) | indirect — covered by `test_kanzi_latent_to_coord.py` |
| 5 | `data/kanzi_upstream/src/kanzi/{models,fsq,utils}.py` | upstream vendored (Wave 36 Agent A) | (vendored; not modified by W91-96) | vendored package | NO (vendored upstream) | NONE (vendored) |
| 6 | `tools/paper_metrics_kanzi.py:226-694` | **Wave 83 Agent B** (`50107eb`) | `50107eb` 2026-09-08 "Wave 83: Kanzi 5 codebook metrics wrapper + regression tests" | numpy stdlib | NO — paper-metric layer is independent of framework-core | **YES** — `tests/test_tools/test_paper_metrics_kanzi.py` |
| 6a | `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:301-368` (JSON output) | **Wave 95 Phase 3.C** | `1f26bf6` 2026-09-10 | stdlib `json` | NO (output assembly is local) | NONE |
| 7 | `tools/run_real_ckpt_eval.py:3028-3096` `load_kanzi_dae_for_bridge` | **Wave 91 Phase 3 (retry)** (`8c5eaaf`) | `702b253` 2026-09-10 "Wave 95 Phase 1.D: widen shift_max default + thread weights_path" | `kanzi.DAE`, `sys.path.insert` | YES — duplicates sweep script line 151 `DAE.from_pretrained(...).eval()` | covered indirectly by `tests/test_tools/test_run_real_ckpt_eval.py` |
| 8 | `tools/run_real_ckpt_eval.py:3100-3450` `KanziGlue` | **Wave 52 Agent A** (`4f2f05d` / `8c5eaaf`) | `8c5eaaf` 2026-09-10 "Wave 91 Phase 3 (retry): wire --kanzi-framework-paper-metrics" | `KanziAdapter._native_states`, numpy softmax | YES — re-implements the 3-term composite logic that the framework-core `LineageFlowGlue.compute_composite` already has (Wave 47) | covered indirectly by `tests/test_tools/test_run_real_ckpt_eval.py` |
| 9 | `tools/run_real_ckpt_eval.py:3474-3700+` `_compute_kanzi_framework_paper_metric` | **Wave 91 Phase 3 (retry)** | `702b253` 2026-09-10 | `KanziGlue`, `kanzi_latent_to_coords`, `kanzi.DAE.encode`, `kanzi.kabsch_rmsd`, `paper_metrics_kanzi.compute_*` | YES — duplicates the entire sweep script loop body (script line 181-264) | covered indirectly by `tests/test_tools/test_run_real_ckpt_eval.py` (50 tests) |
| 10 | `tools/run_real_ckpt_eval.py:4578-5254` `_run_cell` | **Wave 75 Agent 2** + Wave 91 Phase 3 | `702b253` 2026-09-10 | `_resolve_adapter`, `_solve_baseline`, `_solve_framework`, `_compute_kanzi_real_metric`, `_compute_kanzi_framework_paper_metric`, `KanziGlue.compute_composite` | NO — this is the framework entry point | **YES** — `tests/test_tools/test_run_real_ckpt_eval.py` (50 tests) |
| 11 | `tools/upstream_eval.py:450-619` `run_kanzi_upstream_eval` | **Wave 79 Agent 2 + Wave 92b** (`60dcbb7`) | `60dcbb7` 2026-09-10 "Wave 92b: Kanzi upstream N-samples patch" | subprocess `kanzi` driver, `paper_metrics_kanzi` | YES — duplicates the re-encode + RMSD loop from sweep script line 217-244 (the upstream driver IS the bridge) | **YES** — `tests/test_tools/test_upstream_eval.py` (16 tests) |
| 12 | `adaptive_reflow/framework/interfaces.py:545-643` `AdapterObservationProtocol` | **Wave 68** | `56aeb45` 2026-09-07 "Wave 54 Phase 2: v1 first-class Protocol" | (Protocol-only) | NO (declarative Protocol) | conformance tests in `tests/test_adapters/` |
| 13 | `adaptive_reflow/universal/state.py:110-250` `StateBundle`, `ODEConditionDelta`, `ODEIntegratorTrace` | **Wave 11 / Wave 45** | (touched by many waves) | (universal) | NO (framework-core) | YES |

---

## 4. OWNERSHIP table — per-model owner for sweep / bridge / metric / paper-write

| Per-model owner | sweep script | bridge | paper-metric helper | metric helper | paper-write |
|---|---|---|---|---|---|
| **Kanzi** | Wave 95 P3.C / Wave 96.B (`1f26bf6`) | Wave 91 P2 (`dfe0f4e`) + Wave 95 P3.B (`378dc4a`) | Wave 83 B (`50107eb`) | Wave 52 A (`4f2f05d`) — `KanziGlue` | Wave 89 (final synthesis) + Wave 96.E (closure) |
| **LineageFlow** | Wave 86 + Wave 92b — `tools/upstream_eval.py:157-322` `run_lineageflow_upstream_eval` | (none — LineageFlow has no Latent→Coord bridge because its latent is the discrete categorical directly) | (no paper-metric wrapper; metrics computed in upstream `evaluate_all.py`) | Wave 47 — `LineageFlowGlue` (in `tools/run_real_ckpt_eval.py`) | Wave 84 B + Wave 89 |
| **FlowMol3** | Wave 79 + Wave 82 + Wave 87 — `tools/upstream_eval.py:688-810` `run_flowmol3_upstream_eval` | `tools/flowmol3_xtb_bridge.py` (Wave 90 — subprocess only) | Wave 75 Agent 2 — `tools/paper_metrics.py` (FlowMol3 only) | Wave 49 E — `FlowMol3Glue` | Wave 74 + Wave 89 |

The **Kanzi path has 5 owners across 4 waves**, the LineageFlow path has
4 owners across 4 waves, and the FlowMol3 path has 5 owners across 5 waves.
Kanzi is unique in that it has **a Wave 95 Phase 3.B trained-inverse bridge
artifact** (`tools/_kanzi_project_out_inv.pt`) that no other model needs.

---

## 5. Top 5 routing problems

### Problem 1 — Six layers instead of three

The user's CLI hits 6 distinct files (sweep driver → adapter → sweep loop →
bridge → upstream DAE → paper metrics). A clean shape would be:

```
CLI driver  →  framework-core adapter dispatch  →  JSON
                (single helper class)
```

i.e. `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` could be
**20-30 LOC** (just `argparse` + a loop over `_run_cell(model="kanzi",
n_records=1000, ...)`). The 5740-LOC `run_real_ckpt_eval.py` already does
most of the work; the sweep driver is a fork.

**Fix:** delete the sweep driver. Run `tools/run_real_ckpt_eval.py
--model kanzi --seeds 42 --nfe-budgets 50 --n-rounds 1
--kanzi-framework-paper-metrics` instead. The framework already supports
N≥1000 — Wave 88 ran it at N=1000.

### Problem 2 — `tools/run_real_ckpt_eval.py` is 5740 LOC (the worst offender)

Roughly half the file (lines 1530-3700, lines 4570-5700) is **Kanzi glue**:

| Range | What lives there | LOC |
|---|---|---|
| 1537-1750 | `_load_kanzi_dae`, `_decode_kanzi_idx_to_aa`, `_compute_kanzi_real_metric` | ~210 |
| 2025-2026 | per-cell `from adaptive_reflow.adapters.kanzi import ...` | 2 |
| 2246-2265 | `if model == "kanzi": _decode_kanzi_idx_to_aa(idx_2d)` block | ~20 |
| 2518 | `"kanzi": ObservationKind.DISCRETE_TOKENS` dispatch | 1 |
| 2545-2700+ | `_compute_kanzi_real_metric_via_trace` | ~160 |
| 3023-3096 | `KANZI_BRIDGE_DEFAULT_CKPT`, `load_kanzi_dae_for_bridge` | ~70 |
| 3099-3450 | `class KanziGlue` + `with_bridge` + `compute_composite` + `_compute_kanzi_composite` | ~350 |
| 3452-3700+ | `_compute_kanzi_framework_paper_metric` | ~250 |
| 5163-5207 | `_run_cell` body — `if kanzi_framework_paper_metrics and model == "kanzi":` block | ~45 |

Total: **~1100 LOC** of Kanzi-specific glue inside the 5740-LOC monolith
(19%). The same pattern exists for LineageFlow (~600 LOC) and FlowMol3
(~400 LOC); the rest is the framework-core dispatch.

**Fix (recommended split):** see §6 below.

### Problem 3 — Three parallel "Kanzi latent → coords" implementations

| Path | Where | What |
|---|---|---|
| (a) Sweep driver | `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:151, 199` | in-script `DAE.from_pretrained(...).eval()` + `kanzi_latent_to_coords(...)` |
| (b) `run_real_ckpt_eval.py` | `tools/run_real_ckpt_eval.py:3028-3096, 3474-3700+` | `load_kanzi_dae_for_bridge` + `_compute_kanzi_framework_paper_metric` |
| (c) KanziGlue | `tools/run_real_ckpt_eval.py:3149-3176` | `KanziGlue.with_bridge(ckpt_path)` (delegates to (b)) |

All three call the same upstream `kanzi.DAE.from_pretrained` + `kanzi.DAE.decode`
and read the same `tools/_kanzi_project_out_inv.pt`. The CKPT-loader site is
duplicated; the re-encode + RMSD loop is duplicated; the per-record skip-handling
is duplicated. **The bridge proper** (`tools/kanzi_latent_to_coord.py`) is
correctly factored — it's the wrappers that aren't.

**Fix:** move all three into `tools/kanzi_bridge.py` (or similar) with a single
`KanziBridge(adapter, ckpt_path)` class that exposes one method:
`bridge_endpoint_to_coords(x_final) → coords_Å`. The sweep driver and
`_compute_kanzi_framework_paper_metric` both call it.

### Problem 4 — Sweep driver bypasses framework-core dispatch

The sweep driver at `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:167`
constructs `kanzi_adapter = default_kanzi_adapter(weights_path=args.ckpt,
force_mode="torch", num_steps=50, solver="euler")` directly. The
framework-core dispatch in `tools/run_real_ckpt_eval.py:_resolve_adapter`
(line 877) is what the rest of the codebase uses (it reads the
`DOWNSTREAM_METRICS["kanzi"]["adapter_factory"]` entry, threads `nfe_budget`,
handles the `force_mode → real/torch/synthetic` table at line 1037, and
respects `restart_min_nfe`).

The sweep driver **does not** thread `nfe_budget` and **does not** check
`restart_min_nfe`. It also doesn't reuse the `_capture_env_hash_lightweight()`
(line 5678) the framework uses for F.5 env-hash reproducibility tagging.

**Fix:** route the sweep driver through `tools.run_real_ckpt_eval._resolve_adapter`
(or its `_solve_baseline`/`_solve_framework` pair). The whole sweep driver
shrinks from 379 LOC to ~40 LOC.

### Problem 5 — `run_real_ckpt_eval.py:5163-5207` only fires when
`--kanzi-framework-paper-metrics` flag is set, AND the per-cell marker
plumbing is duplicated

The `_run_cell` body checks
`if kanzi_framework_paper_metrics and model == "kanzi":` (line 5176) — meaning
without the flag, the framework arm silently produces zero paper-metric output
even though the plumbing exists. The same flag pattern exists for
`--kanzi-upstream-eval` (line 5590) and `--flowmol3-upstream-eval` (line 5626).

The 5 paper-metric flags (`--paper-metrics`, `--paper-reference`,
`--lineageflow-upstream-eval`, `--kanzi-upstream-eval`,
`--flowmol3-upstream-eval`, `--kanzi-framework-paper-metrics`) are 6
command-line gates on **the same per-cell paper-metric surface** — the
framework treats "upstream" vs "in-process" vs "framework-arm" as
3 orthogonal opt-ins when they should be 3 modes of the same metric.

**Fix:** replace the 6 flags with a single `--paper-metric-mode={none,
framework-arm, upstream-subprocess, paper-reproduction}` enum. The
underlying metric surface is the same; the difference is the bridge path.

---

## 6. Recommended split for `tools/run_real_ckpt_eval.py` (5740 → 6 modules)

| New module | LOC estimate | Owns |
|---|---|---|
| `tools/run_real_ckpt_eval/__main__.py` | ~150 | argparse + entry point only |
| `tools/run_real_ckpt_eval/cell.py` | ~400 | `_run_cell` body — model dispatch + verdict + saturation |
| `tools/run_real_ckpt_eval/adapter_dispatch.py` | ~400 | `_resolve_adapter`, force_mode table, `_solve_baseline`, `_solve_framework` |
| `tools/run_real_ckpt_eval/paper_metrics.py` | ~300 | `DOWNSTREAM_METRICS` registry + `_compute_*_composite` helpers |
| `tools/run_real_ckpt_eval/glue/` (package) | ~700 | `LineageFlowGlue`, `KanziGlue`, `FlowMol3Glue` (3 files) |
| `tools/run_real_ckpt_eval/upstream_eval_client.py` | ~250 | client wrapper around `tools/upstream_eval.py` subprocess calls |
| **Subtotal** | **~2200** | (down from 5740) |
| `tools/kanzi_bridge.py` (extracted from monolith) | ~200 | `KanziBridge(adapter, ckpt_path).bridge_endpoint_to_coords()` (replaces path (a)/(b)/(c) from Problem 3) |
| `tools/lf_bridge.py` (extracted) | ~150 | LineageFlow bridge glue (mirrors kanzi_bridge) |
| `tools/fm3_bridge.py` (extracted) | ~150 | FlowMol3 bridge glue (mirrors kanzi_bridge) |
| **Grand total** | **~2700** | (53% reduction, eliminates 3-path duplication) |

LOC counts are conservative upper bounds; the actual savings come from
removing the duplicated CKPT-loader sites, the duplicated re-encode loops,
and the duplicated skip-handling.

**Migration recipe:**

1. Create `tools/run_real_ckpt_eval/__init__.py` + 6 module files above.
2. Move `KanziGlue` (lines 3099-3450) to `tools/run_real_ckpt_eval/glue/kanzi.py`.
3. Move `_compute_kanzi_framework_paper_metric` (lines 3474-3700+) + `load_kanzi_dae_for_bridge` (lines 3023-3096) to `tools/kanzi_bridge.py`.
4. Move the `if kanzi_framework_paper_metrics and model == "kanzi":` block
   (lines 5163-5207) to `tools/run_real_ckpt_eval/cell.py`.
5. Re-export the public API from `tools/run_real_ckpt_eval/__main__.py` for
   backward compat (`tools/run_real_ckpt_eval.py` becomes a 5-line shim).
7. Delete `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` —
   `run_real_ckpt_eval.py --model kanzi --kanzi-framework-paper-metrics
   --n-rounds 1 --seeds 42 --nfe-budgets 50` does the same job in 1 command.

After the split:
* `tools/run_real_ckpt_eval.py` is a 5-line shim.
* `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` is deleted.
* The Kanzi sweep path traverses **3 layers**: CLI → adapter dispatch → bridge → JSON
  (vs. the current 6).

---

## 7. What this audit does NOT cover

* The LineageFlow and FlowMol3 routing topologies (parallel problem spaces;
  see Wave 47 / Wave 49 audit docs).
* The internal sweep loop of `tools/upstream_eval.py:run_kanzi_upstream_eval`
  (the upstream-subprocess variant — a different routing tree).
* The protocol-level dispatch in `adaptive_reflow/framework/interfaces.py`
  (Wave 68 `AdapterObservationProtocol` is the correct shape; the inline
  per-model helpers in `run_real_ckpt_eval.py` should be migrated to use
  `adapter.observe(...)` directly).

---

## 8. One-line verdict

> The Kanzi sweep path traverses 6 layers (CLI driver → adapter → sweep loop
> → bridge → upstream DAE → paper metrics → JSON) with **3 parallel
> "latent → coords" implementations** and **~1100 LOC of Kanzi-specific glue
> inside a 5740-LOC monolith**. Splitting `run_real_ckpt_eval.py` into 6
> modules + extracting `tools/kanzi_bridge.py` reduces the layer count to
> 3 and the LOC to ~2700.

Co-Authored-By: Claude Code <noreply@anthropic.com>