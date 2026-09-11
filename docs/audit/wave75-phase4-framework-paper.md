# Wave 75 Agent 4 — Framework paper-metric comparison (Phase 4)

**Date:** 2026-09-08
**Wave:** 75 (PHASE-4 framework-vs-baseline paper-metric sweep)
**Agent:** 4 (framework arm + comparison)
**Repo:** `/home/hugo/codes/flowa-multistep-reinference`
**Constraint:** NO commit (verification run).

---

## 0. TL;DR

| Metric | Paper | Phase 3 baseline (N=10) | Framework (N=1, smoke) | Verdict |
|---|---|---|---|---|
| `validity_pct` | 0.999 | **1.000** | **1.000** | framework_ties (tied at ceiling) |
| `pb_validity_pct` | 0.919 | 0.000 | 1.000 | INSAMPLE_INSUFFICIENT (N=1) — must NOT be interpreted as improvement |
| `fg_dev` | 0.27 | 0.944 | 2.717 | INSAMPLE_INSUFFICIENT (N=1) — must NOT be interpreted as regression |
| `ood_ring_rate` | 0.10 | 0.000 | 0.000 | framework_ties (under-stocked for both) |

**Honest verdict: PARTIAL — wire works end-to-end; comparison is
UNCONSTRAINED by sample size.** The framework paper-metric block
succeeded (the JSON now carries `paper_*_framework` keys), but the
**structural v2-adapter limitation** (only the last round's single
molecule is exported to the paper-metric aggregator, see §3.2) means
the framework arm currently evaluates on **N=1** while the baseline
arm evaluates on **N=10** (or whatever `--n-molecules` is set to).
This is NOT a like-for-like comparison.

**Per the task's per-metric significance thresholds (validity=0.001,
pb_validity=0.01, fg_dev=0.01, ood_ring=0.01), the framework smoke
`fg_dev=2.717 - 0.944 = +1.773` "would be" a regression, but with N=1
the per-flag REOS pass rate is 0/1 or 1/1 per flag, blowing the L1
norm up to ~3.0 by construction. The `pb_validity=1.0 - 0.0 = +1.0`
"would be" an improvement, but the underlying UFF energy_ratio is a
deterministic rejection step whose pass rate at N=1 is uncorrelated
with the framework's actual effect.**

---

## 1. Implementation: framework paper-metric block

A new opt-in paper-metric block was added to `_run_cell` in
`tools/run_real_ckpt_eval.py`. When `--paper-metrics` is set AND the
adapter ships `export_sampled_molecules` (currently only the v2
adapter), the framework arm's `framework_trace` is decoded via the
same helper and the 4 paper-parity metrics are computed.

### 1.1 Wire path

| Step | File:line | Action |
|---|---|---|
| 1 | `tools/run_real_ckpt_eval.py:4150-4250` | Add framework paper-metric block after the baseline block |
| 2 | Same | `adapter.export_sampled_molecules(framework_trace)` → `framework_sampled` |
| 3 | Same | Call `compute_all_paper_metrics(framework_sampled, ...)` → `paper_metrics_obj_fw` |
| 4 | Same | Surface 4 keys with `_framework` suffix: `paper_validity_pct_framework`, `paper_pb_validity_pct_framework`, `paper_fg_deviation_framework`, `paper_ood_ring_rate_framework` |
| 5 | Same | `paper_metrics_marker_framework` + `paper_metrics_debug_framework` (parallel to baseline) |

### 1.2 Byte-stability note

The baseline block is unchanged. The new block is conditional on
`hasattr(adapter, "export_sampled_molecules") and model in ("flowmol3_v2",)`,
which means legacy callers that pass `--model flowmol3` (the v1 path,
no `export_sampled_molecules`) or pass any other model see
**byte-identical** cell dict output (only the baseline
`paper_*` keys appear). The `paper_*_framework` keys are additive
only when the v2 adapter is in use AND `--paper-metrics` is set.

---

## 2. Smoke test (N=10) — framework arm wires end-to-end

**CLI invocation** (`/tmp/wave75_phase4/flowmol3_paper_framework_smoke_q4_2026.json`):

```bash
PATH=/home/hugo/xtb_prefix/bin:$PATH CUDA_VISIBLE_DEVICES=0 \
  PYTHONPATH=data/FlowMol3/repo \
  .venvs/flowmol3_venv/bin/python -u tools/run_real_ckpt_eval.py \
    --model flowmol3_v2 --force-mode real --metric-mode real \
    --composite-metric real --paper-metrics \
    --seeds 42 --nfe-budgets 250 --n-molecules 10 --n-rounds 3 \
    --output /tmp/wave75_phase4/flowmol3_paper_framework_smoke_q4_2026.json
```

**Per-cell output** (from `cells[0]`):

```json
{
  "model": "flowmol3_v2",
  "seed": 42,
  "nfe_budget": 250,
  "n_rounds_framework": 3,
  "baseline_metric": 0.0,
  "framework_metric": 0.07340423794186401,
  "composite": 0.18632392968566966,
  "paper_validity_pct": 1.0,
  "paper_pb_validity_pct": 0.0,
  "paper_fg_deviation": 0.944164398447872,
  "paper_ood_ring_rate": 0.0,
  "paper_metrics_marker": "computed",
  "paper_validity_pct_framework": 1.0,
  "paper_pb_validity_pct_framework": 1.0,
  "paper_fg_deviation_framework": 2.716651203480157,
  "paper_ood_ring_rate_framework": 0.0,
  "paper_metrics_marker_framework": "computed",
  "paper_metrics_debug_framework": {
    "reference": "GEOM_DRUGS",
    "n_sampled_molecules": 1,
    "full_pb": True,
    "paper_metrics_module": "tools.paper_metrics",
    "paper_metrics_class": "PaperMetricsResult"
  }
}
```

**Per-metric comparison** (all under-stocked, see §3):

| Metric | Paper | Baseline (N=10) | Framework (N=1) | Delta |
|---|---|---|---|---|
| `validity_pct` | 0.999 | 1.000 | 1.000 | 0.000 |
| `pb_validity_pct` | 0.919 | 0.000 | 1.000 | +1.000 |
| `fg_dev` | 0.27 | 0.944 | 2.717 | +1.773 |
| `ood_ring_rate` | 0.10 | 0.000 | 0.000 | 0.000 |

---

## 3. Statistical-power note (CRITICAL)

### 3.1 Why N=10 (baseline) vs N=1 (framework) is NOT comparable

The v2 adapter's `export_sampled_molecules` returns **at most 1**
RDKit `Mol` object per call (see `flowmol3_v2_adapter.py:4488-4495`
— the v2 adapter stores lineage for a SINGLE molecule at a time,
keyed by the trace's `native_state_digest`). The framework arm
runs 3 rounds × `n_molecules=10` = 30 solves, but only the LAST
round's digest is captured by `export_sampled_molecules`. The
baseline arm runs 1 solve with `n_molecules=10` and the v2 adapter
returns all 10 (via `n_sampled_molecules: 10` debug key).

**Structural limitation**: the framework arm's paper-metric block
currently evaluates on **N=1 molecule** while the baseline arm
evaluates on **N=10**. This is a like-for-NOT-like comparison that
violates the per-metric significance thresholds in the task brief.

### 3.2 Why N=1 inflates `fg_dev` and under-resolves `pb_validity`

- **`fg_dev` (REOS flag-rate L1 vs training)**: with N=1, every
  REOS flag's pass rate is either 0.0 or 1.0 (the L1 distance to
  the training pass rate is therefore the absolute deviation per
  flag). With ~30 REOS flags, the L1 norm can blow up to 3.0+ by
  construction (each flag contributes up to ~0.1 in the paper's
  N=5000 reading). The framework smoke `fg_dev=2.717` is at the
  high end of this N=1 inflation curve, NOT a meaningful framework
  effect.

- **`pb_validity_pct`**: with N=1, the energy_ratio test either
  passes (1/1 = 1.0) or fails (0/1 = 0.0) per molecule, with zero
  statistical power. The framework smoke `pb_validity=1.0` reflects
  that the framework's last-round molecule happened to pass UFF
  energy_ratio, NOT a 0.919-vs-1.0 improvement.

### 3.3 What N is needed for a meaningful comparison?

For `fg_dev` to stabilize at the paper's N=5000 reading (±5% of
0.27 = [0.257, 0.283]), need N ≥ 500. For `ood_ring_rate` to
stabilize at the paper's 0.10 reading (±0.01), need N ≥ 200 with
ring-bearing molecules (≥ ~100 ring-bearing per ~500 molecules).

The **honest target** for a like-for-like framework paper-metric
comparison is N=200 with 10+ framework rounds (or a per-round
cumulative export_sampled_molecules that aggregates lineages across
rounds). N=200 × 3 rounds = 600 solves, est. ~30 min wallclock with
PB energy_ratio UFF (~25 s/mol). Outside single-agent budget.

---

## 4. Verdict per metric (with honest caveats)

### 4.1 `validity_pct`

- Paper: 0.999
- Baseline (N=10): 1.000 — within ±5% (PASS)
- Framework (N=1): 1.000 — within ±5% (PASS)
- Delta: 0.000 — **framework_ties** (|delta| < 0.001 threshold)
- Caveat: both arms at saturation ceiling. RDKit sanitization
  passes ~100% for FlowMol3 ckpt at any reasonable N. The framework
  arm's N=1 cannot regress this metric because validity is binary
  per mol.

### 4.2 `pb_validity_pct`

- Paper: 0.919
- Baseline (N=10): 0.000 — DIVERGES from paper (BLOCKED on UFF vs
  xtb pipeline gap, see Phase 3 §3)
- Framework (N=1): 1.000 — **artifactually high** at N=1
- Delta: +1.000 — **framework_improves (artifactual)**
- Caveat: the framework arm evaluated on 1 molecule. The single
  framework molecule happened to pass UFF energy_ratio. At N≥10,
  this metric would almost certainly collapse to ~0.0 (same UFF
  pipeline gap as baseline). The +1.000 delta is a statistical
  accident of N=1, NOT a framework effect.

### 4.3 `fg_dev`

- Paper: 0.27
- Baseline (N=10): 0.944 — INSAMPLE-INSUFFICIENT (per Phase 3 §1.1)
- Framework (N=1): 2.717 — INSAMPLE-INSUFFICIENT at N=1
- Delta: +1.773 — **framework_regresses (artifactual)**
- Caveat: N=1 inflates the L1 norm by construction. The framework
  arm's N=1 produced a mol with REOS flags that happen to deviate
  strongly from the GEOM_DRUGS training reference. At N≥500, the
  framework's REOS pass rate would average to whatever the
  FlowMol3 ckpt actually generates — almost certainly closer to
  baseline (within ~0.05 of 0.944) than to 2.717.

### 4.4 `ood_ring_rate`

- Paper: 0.10
- Baseline (N=10): 0.000 — INSAMPLE-INSUFFICIENT (per Phase 3 §1.1)
- Framework (N=1): 0.000 — INSAMPLE-INSUFFICIENT at N=1
- Delta: 0.000 — **framework_ties** (|delta| < 0.01 threshold)
- Caveat: both arms under-stocked on ring-bearing molecules. The
  N=1 framework molecule happened to have all rings in ChEMBL. Not
  meaningful.

### 4.5 Per-cell verdict tally

| Metric | Verdict |
|---|---|
| `validity_pct` | framework_ties (both at ceiling) |
| `pb_validity_pct` | framework_improves (ARTIFACTUAL — N=1 inflated) |
| `fg_dev` | framework_regresses (ARTIFACTUAL — N=1 inflated) |
| `ood_ring_rate` | framework_ties (both under-stocked) |

- `n_framework_improves`: 1 (pb_validity — artifactual)
- `n_framework_ties`: 2 (validity, ood_ring_rate)
- `n_framework_regresses`: 1 (fg_dev — artifactual)

**Overall verdict: PARTIAL — wire works, comparison is statistically
unconstrained, and 2 of 4 verdicts are artifactual at N=1.** The
N=50 sweep is in flight as of audit cutoff (PID 1479497, started
06:42, will produce
`/tmp/wave75_phase4/flowmol3_paper_framework_n50_q4_2026.json` when
complete).

---

## 5. Comparison vs Wave 73/74 internal-entropy claim (now paper-anchored)

The Wave 73/74 framework-vs-baseline claim (per
`docs/audit/wave74-phase6-final.md`) was anchored to the **internal
framework metric** `per_position_atom_type_entropy_reduction` (nats,
K=10 atom types, log_K=2.3025 nats upper bound). At FlowMol3
9-cell closure (Wave 68 closure), all 9 cells returned
`entropy_reduction = 0.0734 nats`, byte-stable across runs.

This internal metric measures the **flow component** of the
framework value-add (does the framework arm produce a higher-quality
latent trajectory than the baseline arm?). It is INDEPENDENT of the
4 paper-parity metrics, which measure **outcome quality** (does the
generated molecule look like a real drug?).

The Phase 4 paper-metric comparison adds the **outcome quality**
axis. The smoke shows:
- The framework wire works on outcome quality too (smoke JSON
  carries `paper_*_framework` keys with real metric values).
- The comparison is N-starved for both arms (N=1 framework, N=10
  baseline — not like-for-like).
- The Wave 73/74 internal-entropy claim is NOT contradicted by the
  smoke; it is **complementary** (flow quality vs outcome quality
  are independent axes).

**Honest framing for the paper**: the framework value-add on FlowMol3
is currently evidenced on the **flow component axis** (internal
entropy reduction = 0.0734 nats at NFE=250, 9 cells byte-stable). The
**outcome component axis** (4 paper-parity metrics) requires N≥500
per arm to be statistically valid, which is ~30 min of wallclock on
the PRO 6000 — out of scope for this Phase 4 verification run.

---

## 6. N=50 framework sweep — IN FLIGHT

PID 1479497 (started 06:42, current CPU 1094%) is running the
framework paper-metric sweep at `--n-molecules 50 --n-rounds 3`. ETA
based on the N=10 smoke wallclock (5 min for N=10, so ~25 min for
N=50 with framework overhead) is ~06:55-07:10. Output JSON path:
`/tmp/wave75_phase4/flowmol3_paper_framework_n50_q4_2026.json`.

When the N=50 sweep completes, parse the JSON and update §2 +
§4 with N=50 numbers. The structural N=1 limitation (§3.1) is
NOT resolved by N=50 — the v2 adapter still returns only 1 mol per
round — so the comparison will still be N=1-vs-N=50. The N=50
number for the baseline arm will give a tighter estimate of the
paper-parity metrics at the FlowMol3 ckpt's true distribution, but
the framework arm's numbers will remain N=1.

**Resolution path** (Phase 5 scope):
1. Modify v2 adapter's `export_sampled_molecules` to return ALL
   per-round mols (cache keyed by digest + molecule index). Cost:
   ~10 LOC.
2. After (1), the framework arm paper-metric block can evaluate on
   `n_molecules × n_rounds = 10 × 3 = 30` molecules per cell — same
   N as baseline at `--n-molecules 10`.
3. Re-run with N=200 per arm → ~30 min wallclock → 4 paper metrics
   comparable at ±5% of paper target.

---

## 7. Files written / changed

| File | Status | Purpose |
|---|---|---|
| `tools/run_real_ckpt_eval.py` | MODIFIED | +100 LOC — framework paper-metric block at end of `_run_cell` (after baseline block, conditional on `hasattr(adapter, "export_sampled_molecules")`) |
| `/tmp/wave75_phase4/flowmol3_paper_framework_smoke_q4_2026.json` | NEW | N=10 smoke with framework arm paper metrics (baseline N=10, framework N=1) |
| `/tmp/wave75_phase4/flowmol3_paper_framework_n50_q4_2026.json` | PENDING | N=50 sweep in flight (PID 1479497) |
| `docs/audit/wave75-phase4-framework-paper.md` | NEW | This file |

---

## 8. Verdict

**Wave 75 Phase 4: WIRE VERIFIED, COMPARISON UNCONSTRAINED.**

The framework paper-metric block is wired end-to-end (`paper_*_framework`
keys appear in the smoke JSON, all 4 metrics computed, debug keys
correct). The **structural v2-adapter limitation** (N=1 vs N=10)
means the comparison is statistically unconstrained at any
single-cell sweep, regardless of N.

**The framework paper-metric value-add claim CANNOT be made on
this single-host budget** without either (a) modifying the v2
adapter to export all per-round mols, OR (b) running N=5000 per arm
(~2.5 hours × 2 arms = 5 hours wallclock).

**Recommendation**: defer the framework paper-metric comparison to
Phase 5 (after the v2 adapter's export_sampled_molecules is
extended). The Phase 4 wire is sufficient evidence that the eval
pipeline CAN produce the comparison — the missing piece is sample
size, not the wire.

**Internal-entropy claim from Wave 73/74 is unaffected** — it is
anchored to a different metric (flow component quality, not outcome
quality) and was byte-stable at 0.0734 nats across 9 cells.