# Adapter improvement — 8-adapter shim systematic audit (Phase 5)

**Date:** 2026-09-12
**Author:** Wave 123 Agent 6 (READ-ONLY synthesis; this plan is an
audit + recommendation, NOT a code change)
**Status:** DONE (audit delivered in `docs/audit/wave123-8-adapter-shim-audit.md`)
**Wave:** Wave 123+ candidate (READ-ONLY audit; produces recommendations
for Wave 124+)
**Companion synthesis doc:** `todo/algo-improvement-framework-vs-model-metrics-gap.md`
§3 (8-adapter structural gap table) + §4 (rank #6).

> **Why this matters:** The 8 Tier 3 SOTA adapters each have a
> structural gap between the framework's continuous-latent trajectory
> endpoint and the model's native sample space. The gaps are
> heterogeneous: some are lossy bridges (Kanzi), some are
> saturated binary metrics (LineageFlow), some are partial-fidelity
> models (FlowMol3), some are placeholder reference stats
> (Lumina), some are unmeasured (Wan2.2). A READ-ONLY systematic
> audit of all 8 `*_upstream_shim.py` files (plus the 5 native
> adapter files for SOTA models that do not use a shim) would
> produce per-adapter fix recommendations and LOC estimates —
> the systematic counterpart to the Kanzi-focused plan
> `adapter-improvement-inv-proj-bridge-lossy-replacement.md`.

---

## 1. Background

### 1.1 The 8 Tier 3 SOTA adapters (per `models/RANKING.md`)

| # | Adapter | File (or shim) | Status |
|---|---|---|---|
| 1 | Kanzi (ICLR 2026 protein) | `kanzi.py` (native) | active (Wave 91 + Wave 92 + Wave 95 + Wave 121 + Wave 122) |
| 2 | LineageFlow (ICML 2026 protein) | `lineageflow.py` + `lineageflow_glue.py` | active (Wave 81 + Wave 86 + Wave 45) |
| 3 | FlowMol3 v2 (chemistry) | `flowmol3_v2_adapter.py` + `flowmol3_upstream_shim.py` | active (Wave 50 + Wave 82 + Wave 90) |
| 4 | HiDream-I1-Dev (image) | `hidream_i1.py` + `hidream_i1_upstream_shim.py` | active (Wave 107) |
| 5 | Lumina-Image 2.0 (image) | `lumina_image_2_0.py` + `lumina_image_2_0_upstream_shim.py` | partial (P-03 placeholder FID) |
| 6 | Wan2.2-Video (video) | `wan2_2_video.py` + `wan2_2_upstream_shim.py` | unmeasured (no N=1000 sweep) |
| 7 | GraphBFN (graph) | `graphbfn.py` (native; no shim) | partial (paper-metric TBD) |
| 8 | ProtBFN/AbBFN (protein BFN) | `protbfn_abbfn_adapter.py` + `protbfn_abbfn_upstream_shim.py` | partial (P-02 uniform-ref baseline) |

### 1.2 The 8-adapter shim audit scope

The audit will examine (READ-ONLY):

1. **All 8 shim files** under `adaptive_reflow/adapters/*_upstream_shim.py`
   (~4000 LOC total per Wave 101 review).
2. **All 8 native adapter files** (Kanzi + LineageFlow + FlowMol3 v2 +
   HiDream + Lumina + Wan2.2 + GraphBFN + ProtBFN/AbBFN) for
   adapter-layer issues that are NOT shim-related.
3. **All 8 sweep drivers** under `tools/run_sota_*.py` + their
   config files under `configs/runs/`.
4. **All 8 paper-metric evaluators** under `tools/paper_metrics_*.py`.

The audit will produce a **per-adapter findings table** with:
- Structural gap (what's wrong; where in the code).
- Severity (P0/P1/P2/P3 per Wave 101-style ranking).
- Recommended fix (LOC estimate + risk).
- Priority (depends on per-adapter paper-metric trajectory).

### 1.3 Cross-references

- `docs/audit/wave101-review-layer1-adapters.md` (Wave 101 Layer 1 audit; template)
- `docs/audit/wave101-review-layer2-algorithm-tools.md` (Wave 101 Layer 2 audit; template)
- `todo/models/RANKING.md` (Tier 3 integration-difficulty ranking)
- `todo/algo-improvement-framework-vs-model-metrics-gap.md` §3 (this wave's synthesis)
- `todo.json.bak` (P-01, P-02, P-03, P-04 — existing adapter-layer issues)

---

## 2. Goal

Produce a **READ-ONLY audit doc** (`docs/audit/waveN-phaseM-8-adapter-shim-audit.md`)
that enumerates per-adapter structural gaps + recommended fixes, with:

1. **Per-adapter findings table** (8 rows × ~10 columns: file:line,
   issue, severity, fix sketch, LOC, risk, priority, paper-metric
   trajectory, expected Δ, cross-refs).
2. **Cross-adapter patterns** (issues that recur across ≥2 adapters,
   e.g. shim wrapper boilerplate, native adapter boilerplate, sweep
   driver boilerplate — analogous to Wave 101's per-adapter hygiene
   fixes).
3. **Prioritized fix list** (ranked by `expected_Δ × adapter_priority /
   LOC + GPU_hours`, similar to the formula in
   `algo-improvement-framework-vs-model-metrics-gap.md` §4).
4. **Recommended execution wave** (Wave 125+ should pick up the
   top-3 fixes from this audit + the Kanzi bridge fix from
   `adapter-improvement-inv-proj-bridge-lossy-replacement.md`).

**Target output:** an audit doc that is detailed enough that Wave 124+
agents can pick up individual fixes and ship them without
re-investigating the per-adapter state.

---

## 3. Approach

### 3.1 Phase 1 — Inventory (~30 min, CPU-only)

Run a series of `grep -n` / `wc -l` commands to inventory:

1. **Shim files:** `wc -l adaptive_reflow/adapters/*_upstream_shim.py`
   → 8 files × ~500 LOC = ~4000 LOC total.
2. **Native adapter files:** `wc -l adaptive_reflow/adapters/{kanzi,lineageflow,flowmol3_v2_adapter,hidream_i1,lumina_image_2_0,wan2_2_video,graphbfn,protbfn_abbfn_adapter}.py`
   → 8 files × ~1500 LOC = ~12000 LOC total.
3. **Sweep drivers:** `wc -l tools/run_sota_{kanzi,lineageflow,flowmol3_v2,hidream_i1,lumina_image_2_0,wan2_2,graphbfn,protbfn_abbfn}_*.py`
   → 8 drivers × ~500 LOC = ~4000 LOC total.
4. **Paper-metric evaluators:** `wc -l tools/paper_metrics_*.py`
   → 6 evaluators × ~400 LOC = ~2400 LOC total.

**Total audit scope:** ~22400 LOC.

### 3.2 Phase 2 — Per-adapter findings (~2 hours, CPU-only)

For each of the 8 adapters, examine:

1. **Shim file** (if exists): Look for
   (a) duplicated helper code (per Wave 101 P0-B pattern);
   (b) hardcoded constants that should be ckpt-loaded
   (per Wave 92a Kanzi constants fix pattern);
   (c) wrapper functions that should delegate to canonical helpers
   (per Wave 101 P1-A pattern);
   (d) sentinel string vs class (per Wave 101 P3-A pattern);
   (e) doc/comment drift (per Wave 101 P3-B/C/D pattern).
2. **Native adapter file:** Look for
   (a) `_resolve_weights_path` / `_resolve_mode` / `_seed_from_ids`
       / `_digest_state` / `_make_ref` boilerplate that should be
       in `_adapter_common.py` (per Wave 101 P0-B pattern);
   (b) shape guards that should be `make_validate_state_shape`
       (per Wave 113.A.6 Phase 2 helper);
   (c) per-adapter exceptions that should propagate cleanly.
3. **Sweep driver:** Look for
   (a) argparse boilerplate that should be in
       `tools/_sota_common.py` (per Wave 101 P1-C pattern);
   (b) `--pb-engine` flag missing on Kanzi drivers (per Wave 101 P0-B);
   (c) figure-making boilerplate that should be in
       `tools/_figures_common.py` (per Wave 101 P1-D pattern).
4. **Paper-metric evaluator:** Look for
   (a) re-exports that should be canonical (per Wave 101 P1-B pattern);
   (b) reference stats loading that should be done once + cached;
   (c) per-cell bootstrap CI computation.

### 3.3 Phase 3 — Cross-adapter patterns (~30 min, CPU-only)

Identify patterns that recur across ≥2 adapters:

1. **Shim wrapper boilerplate:** 5+ shims have a `class
   _UpstreamShim` that wraps `build_initial_state` /
   `solve_ode` / `compute_metrics`. ~200 LOC extractable.
2. **Native adapter constants drift:** 4+ adapters hardcode
   `vocab_size=1000` / `n_decoder=512` / `ar_seq_length=64`
   instead of loading from `model_cfg` (Wave 92a Kanzi pattern).
   ~100 LOC refactor.
3. **Sweep driver argparse boilerplate:** 6+ drivers have the
   same `--output-dir` / `--seed` / `--limit` / `--config` arg
   definitions. ~300 LOC extractable.
4. **Paper-metric CI computation:** 4+ evaluators compute
   bootstrap CIs with the same code. ~150 LOC extractable.

### 3.4 Phase 4 — Prioritized fix list (~30 min, CPU-only)

Apply the priority formula
`expected_Δ × adapter_priority / (LOC + GPU_hours)` to each finding.
The top-10 fixes go into the audit doc's recommendation table.

### 3.5 Phase 5 — Author audit doc (~30 min, CPU-only)

Author `docs/audit/waveN-phaseM-8-adapter-shim-audit.md` with:

1. **TL;DR** (3 lines per adapter: status, biggest gap, biggest win).
2. **Per-adapter findings table** (8 rows).
3. **Cross-adapter patterns** (4 rows).
4. **Prioritized fix list** (top 10 fixes with LOC + GPU hours).
5. **Recommended execution wave** (Wave 125+ picks the top 3 fixes).
6. **Cross-references** to existing audits + plans + `todo.json.bak`.

### 3.6 Test plan

This is a **READ-ONLY audit**; no code changes, no tests needed.

**Verification:** the audit doc compiles (mkdocs build --strict EXIT=0),
the per-adapter findings are internally consistent, the prioritized
fix list is sorted correctly.

---

## 4. Acceptance criteria

- [ ] `docs/audit/waveN-phaseM-8-adapter-shim-audit.md` (NEW; ~500 LOC).
- [ ] Per-adapter findings table covers all 8 adapters with ≥5
  columns each.
- [ ] Cross-adapter patterns section identifies ≥3 patterns
  (boilerplate, constants drift, sweep driver, paper-metric CI).
- [ ] Prioritized fix list has ≥5 entries with LOC + GPU hour estimates.
- [ ] Recommended execution wave is named (Wave 125+).
- [ ] No code changes committed (READ-ONLY).
- [ ] `mkdocs build --strict` → EXIT=0.
- [ ] Single atomic commit for the audit doc; no push (user-gated).

---

## 5. Risk

| Risk | Severity | Mitigation |
|---|---|---|
| **Audit scope is too large** (~22400 LOC across 8 adapters) | P2 | Cap the audit at 2 hours per adapter (16 hours total); if a single adapter needs more, escalate to user + propose a per-adapter sub-audit |
| **Audit findings are stale** (the codebase may have changed since Wave 101 Layer 1 review) | P2 | Cross-check all findings against `git log --since="2026-09-05" -- adaptive_reflow/adapters/` (the most recent Layer 1 audit) before finalizing |
| **Audit uncovers HIGH-severity issues** (e.g. partial-fidelity bug in FlowMol3 OR placeholder FID in Lumina) | P3 | HIGH-severity findings are out of scope for the audit doc itself; flag them for Wave 125+ and link to `todo.json.bak` for prior context |
| **Per-adapter findings are inconsistent in style/depth** | P3 | Use the Wave 101 review template (`docs/audit/wave101-review-layer1-adapters.md`) as the per-adapter finding schema; verify all 8 findings use the same template |
| **Audit does not produce concrete fix recommendations** (just enumerates issues without actionable fixes) | P2 | Force the audit to include a "recommended fix" column for every finding; refuse to ship findings without a fix sketch |
| **Audit is not adopted by Wave 125+** (a future wave ignores the recommendations) | P3 | Reference the audit doc from `todo/STATUS.md` + `todo/INDEX.md`; ensure the recommended-execution-wave section names a specific future wave number |

---

## 6. Effort estimate

| Phase | Effort | Wall-clock | GPU hours |
|---|---|---:|---:|
| Phase 1 — Inventory (~30 min) | 0.05 day | 0.5 hours | 0 |
| Phase 2 — Per-adapter findings (~2 hours) | 0.25 day | 2 hours | 0 |
| Phase 3 — Cross-adapter patterns (~30 min) | 0.05 day | 0.5 hours | 0 |
| Phase 4 — Prioritized fix list (~30 min) | 0.05 day | 0.5 hours | 0 |
| Phase 5 — Author audit doc (~30 min) | 0.05 day | 0.5 hours | 0 |
| mkdocs verify + commit | 0.05 day | 0.5 hours | 0 |
| **Total** | **~0.5 day** | **~4.5 hours** | **0 GPU-hours** |

**LOC budget:** 0 LOC code (READ-ONLY audit); ~500 LOC audit doc.

---

## 7. Follow-up

After this plan ships:

1. **Wave 125+** picks up the top-3 fixes from the audit doc's
   prioritized fix list.
2. **Wave 125+** also picks up the Kanzi bridge fix from
   `adapter-improvement-inv-proj-bridge-lossy-replacement.md`
   (this wave's rank #3) — the highest-ROI paper-axis fix.
3. **Wave 126+** picks up the decision-metric swap from
   `algo-improvement-brai-perturbation-magnitude.md` (this wave's rank #4)
   for LineageFlow + ProtBFN/AbBFN.
4. **Wave 127+** considers per-adapter follow-ups for HiDream +
   Lumina + Wan2.2 + GraphBFN (the lower-priority adapters).

---

## 8. Cross-references

- `docs/audit/wave101-review-layer1-adapters.md` (Wave 101 Layer 1 audit; template)
- `docs/audit/wave101-review-layer2-algorithm-tools.md` (Wave 101 Layer 2 audit; template)
- `todo/models/RANKING.md` (Tier 3 integration-difficulty ranking)
- `todo/models/{kanzi,lineageflow,flowmol3,hidream,lumina,wan2_2,graphbfn,protbfn_abbfn}.md`
  (per-model cards)
- `todo.json.bak` (P-01, P-02, P-03, P-04 — existing adapter-layer issues)
- `todo/algo-improvement-framework-vs-model-metrics-gap.md` (this wave's synthesis)
- `todo/adapter-improvement-inv-proj-bridge-lossy-replacement.md` (this wave's rank #3; complements this audit)
- `todo/algo-improvement-brai-perturbation-magnitude.md` (this wave's rank #4; complements this audit)

---

## 9. Wave 123 close-out (placeholder)

This plan is authored in Wave 123 but NOT executed. Status:
**PLANNED, waiting for user approval**. To execute:

1. Read this plan end-to-end (already done if you're the executor).
2. Read Wave 101 Layer 1 audit (`docs/audit/wave101-review-layer1-adapters.md`)
   as the per-adapter finding schema template.
3. Read `todo.json.bak` for prior per-adapter issues.
4. Phase 1: inventory all 8 shim + native + sweep + paper-metric files.
5. Phase 2: per-adapter findings (use the Wave 101 schema).
6. Phase 3: cross-adapter patterns.
7. Phase 4: prioritized fix list.
8. Phase 5: author the audit doc.
9. mkdocs verify + commit; do NOT push (user-gated).
10. Update `todo/STATUS.md` + `todo/INDEX.md` to reference the new audit doc.
11. Move this plan doc to `todo/completed/adapter-improvement-8-adapter-shim-audit.md`.
