# Wave 69 Phase 3 — FlowMol3 Sweep Re-run After Agent 2 Fix

**Date:** 2026-09-07
**Wave:** 69, Agent 3
**Phase 1 root cause:** `docs/audit/wave69-phase1-audit.md` (chemistry stub at `tools/run_real_ckpt_eval.py:3122-3127`)
**Phase 2 fix:** `docs/audit/wave69-phase2-fix.md` (interface-first `sampled_molecules` kwarg + `marker="degraded_chemistry"`)
**Constraint:** NO commit. NO push. Honest evidence report.

---

## 1. Sweep execution

### 1.1 Environment

| Item | Value |
|------|-------|
| GPU | RTX PRO 6000 97 GB (`CUDA_VISIBLE_DEVICES=0`) |
| Python venv | `.venvs/flowmol3_venv` (PyTorch 2.7.0 + CUDA 12.8) |
| `xtb` binary | **NOT FOUND** — geometry axis (`neg_med_rmsd_after_xtb`) correctly drops to `null` and chemistry weights renormalise |
| Force mode | `real` |
| Metric mode | `real` |
| Composite-metric | `real` |
| Seeds | 42, 43, 44 |
| NFE budgets | 10, 50, 200 |
| Output | `verification_outputs/flowmol3_v2_q4_2026.json` |
| Wallclock total | 9 cells in <1 s wallclock → confirms v2 adapter is NOT doing a real ckpt forward |

### 1.2 Agent 2 fix verification (before sweep)

```bash
$ grep -n "sampled_molecules" tools/run_real_ckpt_eval.py | head -8
3052:    sampled_molecules: Sequence[Any] | None = None,
3082:       ``sampled_molecules`` is supplied (interface-first kwarg; default
3088:       ``sampled_molecules`` is ``None`` (legacy callers / Phase-3B
3132:    # ``sampled_molecules`` is supplied (interface-first kwarg, default
3136:    # a hard-coded neutral-0 stub. When ``sampled_molecules`` is
3162:    if sampled_molecules is not None:
3166:                list(sampled_molecules),

$ python -m pytest tests/test_adapters/test_flowmol3_v2_adapter.py \
                     tests/test_tools/test_run_real_ckpt_eval.py \
                     -q --tb=line
......................................................                   [100%]
54 passed, 3 warnings in 3.76s
```

The Phase 2 fix is in place and the regression tests pass (54/54). The fix:

1. Added `sampled_molecules: Sequence[Any] | None = None` to `_compute_flowmol3_composite(...)` signature.
2. When `sampled_molecules is not None`, instantiates `FlowMol3Glue(adapter=adapter)` and calls
   `glue.compute_chemistry_metrics(list(sampled_molecules), ...)`, merging upstream readings into
   the chemistry stub.
3. Returns `marker="degraded_chemistry"` when the chemistry dict is still the neutral-0 stub
   (either caller did not supply molecules OR `compute_chemistry_metrics` returned empty).
4. Added additive debug fields: `chemistry_input_source`,
   `chemistry_compute_keys`, `chemistry_compute_error`, `composite_marker`.

---

## 2. Sweep results

### 2.1 Aggregate verdict

```json
{
  "n_cells": 9,
  "n_supported": 0,
  "n_tie": 9,
  "n_regression": 0,
  "n_pending": 0,
  "n_blocked": 0,
  "n_run_error": 0,
  "n_real_computed": 9,
  "n_synthetic_fallback": 0,
  "composite_median": 0.0,
  "composite_verdict": "no_signal",
  "n_composite_computed": 0,
  "n_composite_blocked": 0,
  "verdict_overall": "TIE_AT_SATURATION"
}
```

Composite is **still 0.0** for all 9 cells. The Phase 2 fix did NOT change the composite value.
It did, however, correctly surface the marker as `degraded_chemistry` (was `computed` in the
closure sweep). This is an honest improvement in the debug surface — the eval tool now admits
when the chemistry axes cannot be computed, rather than fabricating a zero reading under
`marker="computed"`.

### 2.2 Per-cell table (9 cells)

| Seed | NFE | wb (s) | wf (s) | composite | status | composite_marker | chemistry_input_source |
|------|-----|--------|--------|-----------|--------|-------------------|------------------------|
| 42 | 10  | 0.5396 | 0.0028 | 0.000000  | TIE    | degraded_chemistry | neutral_zero_stub      |
| 42 | 50  | 0.0047 | 0.0060 | 0.000000  | TIE    | degraded_chemistry | neutral_zero_stub      |
| 42 | 200 | 0.0176 | 0.0188 | 0.000000  | TIE    | degraded_chemistry | neutral_zero_stub      |
| 43 | 10  | 0.0009 | 0.0025 | 0.000000  | TIE    | degraded_chemistry | neutral_zero_stub      |
| 43 | 50  | 0.0042 | 0.0058 | 0.000000  | TIE    | degraded_chemistry | neutral_zero_stub      |
| 43 | 200 | 0.0164 | 0.0185 | 0.000000  | TIE    | degraded_chemistry | neutral_zero_stub      |
| 44 | 10  | 0.0009 | 0.0024 | 0.000000  | TIE    | degraded_chemistry | neutral_zero_stub      |
| 44 | 50  | 0.0042 | 0.0058 | 0.000000  | TIE    | degraded_chemistry | neutral_zero_stub      |
| 44 | 200 | 0.0166 | 0.0186 | 0.000000  | TIE    | degraded_chemistry | neutral_zero_stub      |

All cells have:
- `chemistry_input = {frac_valid_mols: 0.0, frac_mols_stable: 0.0, energy_js_div: 0.0, reos_cum_dev: 0.0}` — neutral-0 stub.
- `geometry_input = None` — `xtb` not on `$PATH` (expected, geometry axis correctly drops).
- `chemistry_input_source = "neutral_zero_stub"` — legacy caller path.
- `xtb_present = false` — environment, not a code issue.
- `baseline_marker = "computed"`, `framework_marker = "computed"` — the entropy reduction reading (0.0734 nats) is byte-stable.

### 2.3 Comparison vs closure sweep

| Field | closure (`flowmol3_closure_q4_2026.json`) | v2 (`flowmol3_v2_q4_2026.json`) | Delta |
|-------|------------------------------------------|----------------------------------|-------|
| `composite` | 0.0 (all 9 cells) | 0.0 (all 9 cells) | **NO CHANGE** |
| `composite_marker` | `computed` (HONEST-LIE — fabricated) | `degraded_chemistry` (HONEST — surfaced) | **IMPROVED** |
| `wallclock_baseline_s` range | 0.0009 — 0.5397 | 0.0009 — 0.5396 | identical (no-op fast) |
| `wallclock_framework_s` range | 0.0024 — 0.0189 | 0.0024 — 0.0188 | identical (no-op fast) |
| `verdict_overall` | TIE_AT_SATURATION | TIE_AT_SATURATION | unchanged |
| `chemistry_input_source` (new field) | n/a (not surfaced in closure) | `neutral_zero_stub` (all 9) | **NEW — additive** |
| `composite_marker` debug field (new) | n/a | `degraded_chemistry` (all 9) | **NEW — additive** |

**Honest verdict:** the Agent 2 fix is a **half-win**. It:

1. ✅ **Correctly surfaced** the `degraded_chemistry` marker (replacing the prior fabricated `marker="computed"` with all-zeros chemistry — that was a quiet lie).
2. ❌ **Did NOT change `composite` from 0.0** because the caller at `tools/run_real_ckpt_eval.py:3723` does not supply `sampled_molecules` — every cell falls through to the legacy `neutral_zero_stub` path.

---

## 3. New root cause: caller never supplies `sampled_molecules`

### 3.1 The Phase 2 fix is purely additive at the helper signature

Per `docs/audit/wave69-phase2-fix.md` §2.1 the Phase 2 fix modifies **only**
`_compute_flowmol3_composite(...)` to accept `sampled_molecules: Sequence[Any] | None = None`
and conditionally invoke `FlowMol3Glue.compute_chemistry_metrics(...)`. The fix is correctly
**interface-first and byte-stable** — it preserves the legacy caller contract (no molecules →
neutral-0 stub → `marker="degraded_chemistry"`).

### 3.2 But the caller never supplies `sampled_molecules`

The call site at `tools/run_real_ckpt_eval.py:3723`:

```python
(
    composite_value, composite_marker, composite_dbg,
) = _compute_flowmol3_composite(
    adapter=adapter,
    baseline_trace=baseline_trace,
    framework_trace=framework_trace,
    seed=int(seed), nfe=int(nfe),
)
```

The kwarg `sampled_molecules` is **never passed** by the caller. This means:

- `sampled_molecules is None` at the helper level → `chemistry_input_source = "neutral_zero_stub"` →
  `marker = "degraded_chemistry"` → `composite = 0.0`.

The Phase 2 fix created the **plumbing** (helper accepts the kwarg + correctly degrades), but did
NOT update the **caller** to extract RDKit `Mol` objects from the v2 adapter's captured trajectory
and feed them into the helper.

### 3.3 Secondary issue: v2 adapter is NOT running a real ckpt forward on GPU

The wallclock numbers are no-op-fast:

- NFE=10 baseline: 0.5 s (initial model load once) / 0.0009 s for subsequent cells.
- NFE=50 baseline: 0.004 — 0.005 s.
- NFE=200 baseline: 0.016 — 0.018 s.

A real FlowMol3 forward pass at NFE=200 on the RTX PRO 6000 should take seconds (1 — 5 s).
The wallclock being <20 ms even at NFE=200 confirms the v2 adapter is returning the
**synthetic placeholder trace** (the deterministic one-hot atom-type lineage described in
`docs/audit/wave69-phase1-audit.md` §2.6), NOT a real ckpt forward.

GPU utilisation was 0% throughout the sweep (`nvidia-smi` idle at 37 °C, 10 W).

The per-position entropy reduction reading (0.07340423794186401 nats, byte-stable across all
9 cells) is the **uniform-vs-uniform** reading from the synthetic placeholder — it does not
depend on seed or NFE because the cached trajectory is deterministic.

### 3.4 Why the entropy metric IS byte-stable but chemistry is not

The v2 adapter's `observe_as_dict()` correctly computes a real reading at
`adaptive_reflow/adapters/flowmol3_v2_adapter.py:3351`:

```python
reduction_value = float(
    per_position_entropy_reduction(theta_before_arr, theta_after_arr)
)
```

But `theta_after_arr` is derived from `traj_a` (the cached trajectory at line 3285-3309),
which is the v2 placeholder's deterministic one-hot atom-type lineage. The reading is constant
per `(n_atoms, K_atom)` and independent of seed/NFE.

A **real** FlowMol3 forward would:

1. Load `flowmol3_ctmc.ckpt` from disk into GPU memory.
2. Run the CTMC velocity field at NFE=200 steps.
3. Cache the trajectory of shape `(B, n_atoms, K_atom, K_bond, n_timesteps, 3)`.
4. Decode to RDKit `Mol` objects (with atom types + bond types + 3D coords).

None of steps 1 — 4 happen. The v2 adapter short-circuits to the placeholder trace because
**the upstream FlowMol3 package is not installed in the sidecar venv** (only
`torch + CUDA + numpy` are available — `flowmol` upstream is not pip-installable from PyPI, it
lives at `data/flowmol_upstream/` and was never mirrored into `.venvs/flowmol3_venv`).

### 3.5 Three-step close for the next agent (escalation to Agent 2 retry)

Per the Phase 1 audit §3.1 "interface-first additive fix" — Phase 2 delivered step 1 (kwarg +
helper logic). Steps 2 + 3 are missing:

| Step | Surface | Status | Required for composite > 0 |
|------|---------|--------|----------------------------|
| 1 | `_compute_flowmol3_composite(...)` accepts `sampled_molecules` | DONE (Phase 2) | — |
| 2 | Caller at line 3723 supplies `sampled_molecules` from the v2 trace | **MISSING** | yes |
| 3 | v2 adapter exposes a method to decode `traj_a` → RDKit `Mol` list | **MISSING** | yes (or `flowmol` upstream available so step 2 can use it) |
| 4 | `xtb` binary on `$PATH` for geometry axis | out of scope (env) | enables geometry axis |

The minimal Phase 3 fix:

1. Add `FlowMol3V2Adapter.export_sampled_molecules(trace) -> list[Any]` that decodes
   `traj_a` (atom-type lineage + bond-type lineage + 3D coords) to RDKit `Mol` objects.
2. Update the caller at line 3723 to compute `sampled_molecules = adapter.export_sampled_molecules(baseline_trace)`
   and pass it to `_compute_flowmol3_composite`.
3. If RDKit is not importable, fall back to `marker="degraded_chemistry"` (already implemented).

A Phase 4 follow-up (env-level): install the upstream `flowmol` package in `.venvs/flowmol3_venv`
so the glue's `compute_chemistry_metrics` can use the real `SampleAnalyzer` instead of the
proxy SMILES fallback.

---

## 4. Improvement vs closure sweep — honest score

| Aspect | Phase 2 fix delivered? | Notes |
|--------|------------------------|-------|
| Honest marker (no fabricated `computed` with zero readings) | ✅ YES | `degraded_chemistry` correctly surfaced |
| Composite > 0 in at least one cell | ❌ NO | Caller never supplies `sampled_molecules` |
| Wallclock realistic (real ckpt forward) | ❌ NO | v2 adapter still returns synthetic placeholder; GPU idle |
| Chemistry axis populated (`frac_valid_mols > 0` OR `energy_js_div > 0`) | ❌ NO | All 9 cells: chemistry_input_source = `neutral_zero_stub` |
| `baseline_marker = computed` AND `framework_marker = computed` | ✅ YES | entropy reduction reading is real (just from placeholder trace) |

**Overall verdict:** the Phase 2 fix is a **debug-surface honesty improvement** — not a chemistry
metric unblock. The composite is still 0.0 because the caller never supplies molecules, and
the v2 adapter is still returning a synthetic placeholder trace (not a real ckpt forward).

**Per Phase 1 audit §3.4 and the agent task spec Step 5:** "If still 0.0: report new root cause,
do NOT commit, escalate to Agent 2 retry." This document is the escalation.

---

## 5. Files written

| Path | Type | Notes |
|------|------|-------|
| `verification_outputs/flowmol3_v2_q4_2026.json` | NEW | 9-cell sweep output (composite still 0.0) |
| `docs/audit/wave69-phase3-sweep.md` | NEW | this doc (honest escalation) |

Per the agent task spec: **NO commit**. The Phase 2 fix remains committed (Agent 2's deliverable);
this re-run is a verification that did not produce a new feature, only evidence.

---

## 6. JSON output

```json
{
  "wallclock_baseline_avg_s": 0.0672,
  "wallclock_framework_avg_s": 0.0112,
  "n_supported": 0,
  "n_tie": 9,
  "n_regression": 0,
  "n_blocked": 0,
  "composite_avg": 0.0,
  "chemistry_axis_populated": false,
  "verdict_overall": "TIE_AT_SATURATION (composite_marker=degraded_chemistry for all 9 cells; chemistry_input_source=neutral_zero_stub)",
  "improvement_vs_closure_sweep": "honest_only: composite_marker changed from 'computed' (fabricated) to 'degraded_chemistry' (surfaced). Composite value unchanged (0.0) because caller never supplies sampled_molecules; v2 adapter still returns synthetic placeholder trace (no GPU forward).",
  "files_written": [
    "verification_outputs/flowmol3_v2_q4_2026.json",
    "docs/audit/wave69-phase3-sweep.md"
  ],
  "notes": [
    "Wave 69 Phase 2 fix correctly surfaced composite_marker='degraded_chemistry' (was 'computed' in closure sweep with fabricated zero readings) — this is the honesty half of the fix.",
    "Phase 2 fix did NOT change composite from 0.0: the caller at tools/run_real_ckpt_eval.py:3723 never passes sampled_molecules to _compute_flowmol3_composite. All 9 cells fall through to chemistry_input_source='neutral_zero_stub'.",
    "Wallclock is no-op fast (NFE=200 baseline = 0.017s, NFE=10 baseline = 0.5s first call / 0.001s subsequent). Real FlowMol3 forward at NFE=200 should take 1-5s on RTX PRO 6000. GPU utilisation = 0% throughout. This confirms the v2 adapter is returning the deterministic synthetic placeholder trajectory, not a real ckpt forward — the upstream flowmol package is not pip-installed in .venvs/flowmol3_venv.",
    "Per-position entropy reduction reading = 0.07340423794186401 (byte-stable across all 9 cells) is the uniform-vs-uniform reading from the placeholder trace; it's real but not informative.",
    "Three-step escalation: (1) Agent 2 retry should add FlowMol3V2Adapter.export_sampled_molecules(trace) -> list[RDKit Mol] decoding traj_a lineage + bond lineage + 3D coords. (2) Update caller at line 3723 to compute sampled_molecules = adapter.export_sampled_molecules(baseline_trace) and pass it. (3) Phase 4 env: install upstream flowmol in .venvs/flowmol3_venv so compute_chemistry_metrics uses real SampleAnalyzer not SMILES proxy.",
    "NO commit per task spec Step 7. NO push per Wave 69 Agent 3 constraint. Phase 2 fix remains committed from Agent 2; this re-run is verification-only."
  ]
}
```
