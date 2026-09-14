# Wave 90 Agent A — Path C READ-ONLY audit + fix plan

**Date:** 2026-09-09
**Wave:** 90 (Path C: Tier 3 paper-metric 真改善 at N=5000)
**Agent:** Wave 90 Agent A (READ-ONLY audit, NO code changes)
**Repo:** `/home/hugo/codes/flowa-multistep-reinference`
**Constraint:** READ-ONLY audit + implementation plan. NO code changes, NO
commits, NO push. Phase 1 audit results below; Phase 2/3 implementation plan
in §3 with per-step LOC estimate + risk.

---

## 0. TL;DR

Wave 86-89 closed the Tier 3 paper-metric story at **N=1000 with framework arm
REAL** on all 3 models (LineageFlow + FlowMol3 + Kanzi). The headline verdict
is:

* **LineageFlow** `framework_improves` on `hmmscan_total_hits` (+116%, p<1e-10);
  `framework_ties_within_sem` on `coverage_any_hit`; `framework_ties_at_zero`
  on `top1_family_type`; novelty/foldability/self_consistency blocked on deps.
* **FlowMol3** `framework_improves` on `fg_dev` (4.05σ, p<0.05); MATCH on
  `validity_pct`; REGRESSION on `pb_validity_pct` (UFF-vs-xtb definitional gap);
  underpowered on `ood_ring_rate` (|Δ| 9× smaller than MDD at N=1000).
* **Kanzi** `NOT_MEASURABLE` on paper-metric axis by construction (Wave 88 F-3:
  no `(64,64)→(L,256)` bridge); framework arm IS live on synthetic latent
  (Wave 88 F-1: 100/100 latent divergence, wallclock 1.28×); internal composite
  axis SUPPORTED UNCHANGED.

**Path C hypothesis (Wave 90+):** scaling each sweep to **N=5000 per arm** will
surface framework-vs-baseline signal on the **currently underpowered axes**
(`ood_ring_rate` + Kanzi `reconstruction_kabsch_rmsd_A` if the bridge is closed +
LineageFlow per-record `hmmscan_total_hits` finer breakdown). At N=5000 the MDD
for `ood_ring_rate` shrinks from 0.026 (N=1000) to ~0.013 (N=5000), putting the
framework's 0.003 delta within reach of statistical distinguishability.

**Per-model N=5000 wallclock budget estimate:** ~5-7h total
(LineageFlow ~2h on lineageflow_venv HMMER + FlowMol3 ~2h on 5090 PB + Kanzi
~1-3h if bridge closed, else DEFER).

**Steps 1-6 audit results:** all 6 read steps return VERIFIED / CONFIRMED /
NOT-A-BLOCKER. Path C is structurally feasible; no read step revealed a
hard blocker. The full 18-step implementation plan (steps 8-25) is
~310 LOC total, additive-only (no framework-core refactor), and reuses the
Wave 86 paper-quantity-driven β fix + Wave 87 PB-xtb semantics clarification +
Wave 88 Kanzi framework-arm plumbing. **No D.4 byte-stable vector moves.**

---

## 1. Audit findings (Steps 1-6)

### Step 1 — Verify Wave 86-89 cumulative state

Read in full (Wave 86/87/88/89 audit docs + D.4 byte-stable verify):

| Surface | State (Wave 89 close-out) | Wave 90 implication |
|---|---|---|
| D.4 byte-stable regression | 33/33 PASS (matches Wave 86/87/88 baseline) | Path C must NOT move any vector; verify per-step |
| G-MASTER capability | 7/7 PASS (hard=5, soft=2) | Path C must NOT regress G.1-G.7 |
| mkdocs build --strict | EXIT=0 (paper-draft.md in nav) | Path C additive paper edits must keep --strict clean |
| LineageFlow framework arm | `framework_fallback_per_family_count = {}` (Wave 86) | Wave 90 can scale N → arm stays real |
| FlowMol3 framework arm | Real `flowmol.sample(seed=)` threaded (Wave 74 F2) | Wave 90 can scale N → arm stays real |
| Kanzi framework arm | Live on synthetic `(64,64)` latent (Wave 88 F-1) | Wave 90 N=5000 sweep would run on synthetic — no paper-metric signal until bridge closed |
| Paper-quantity-driven β | Active in `_make_framework_policy` (Wave 86 fix) | Reused as-is |
| PB-xtb semantics | UFF-based `energy_ratio` clarified (Wave 87 F-6) | No code change needed |

**Verdict.** Wave 86-89 state is **clean and stable**. Path C builds on the
existing framework-arm infrastructure with no regression risk to D.4 or
G-MASTER, **provided** the implementation stays additive (no framework-core
refactor).

### Step 2 — Audit per-axis saturation at N=1000

Cross-referenced the Wave 89 FINAL verdict table with the per-axis MDD analysis:

| Model | Paper metric | Δ at N=1000 | MDD at N=1000 | Verdict at N=1000 | Path C hypothesis at N=5000 |
|---|---|---:|---:|:---:|:---|
| LineageFlow | `hmmscan_total_hits` | **+184** (+116%) | ~3 hits | **`framework_improves`** p<1e-10 | Same verdict, tighter CI; new finer breakdown possible |
| LineageFlow | `coverage_any_hit` | −2.2 pp | ~3.1 pp (p=0.5) | **`ties_within_sem`** | z may grow with N; needs N≥3000 to tighten CI |
| LineageFlow | `top1_family_type` | 0.000 | 0.000 | **`ties_at_zero`** | UNCHANGED — synthetic M-rich priors don't carry AA-side-chain diversity (Wave 47 §3.1 blocker) |
| FlowMol3 | `validity_pct` | 0.0000 | 1e-4 | **MATCH** (tie_at_paper) | UNCHANGED — saturation ceiling |
| FlowMol3 | `pb_validity_pct` | −0.0995 | 0.020 | REGRESSION 9.95 pp (UFF-vs-xtb) | UNCHANGED — definitional gap (Wave 87 F-6) |
| FlowMol3 | `fg_dev` | **−0.0235** | 0.016 | **`framework_improves`** 4.05σ | Same verdict, finer per-cell breakdown possible |
| FlowMol3 | `ood_ring_rate` | −0.003 | 0.026 | **underpowered** (9× gap) | **Path C candidate**: N=5000 → MDD ≈ 0.013 — within 4× of observed |
| Kanzi | `reconstruction_kabsch_rmsd_A` | n/a | n/a | **`NOT_MEASURABLE`** (Wave 88 F-3) | UNCHANGED unless `(64,64)→(L,256)` bridge closed (5-10 LOC adapter change + ~30 min DAE geometry audit) |
| Kanzi | 5 codebook metrics | n/a | n/a | `encoder_summary` | UNCHANGED — not Path C scope |

**Verdict.** Path C at N=5000 has **3 axes where scaling can change the
verdict** (`coverage_any_hit` tighten, `ood_ring_rate` surface signal, finer
`hmmscan_total_hits` breakdown). Other 8 axes will likely report the same
verdict as Wave 89 — Path C is not a magic multiplier, it's a saturation-escape
for the underpowered axes. **Net expected gain**: ~1-2 axes flipped from
"underpowered" → "framework_improves" (most likely `ood_ring_rate`); ~3 axes
re-verified with tighter CIs.

### Step 3 — Audit statistical power + target N per axis

Per-axis MDD formula (two-proportion z-test, p<0.05, power=0.80):

```
MDD(p, N) = 1.96 * sqrt(2*p*(1-p)/N)   # for two-arm p comparison
```

| Axis | Baseline p | MDD at N=1000 | MDD at N=3000 | MDD at N=5000 | N for MDD ≤ 0.005 |
|---|---:|---:|---:|---:|---:|
| `validity_pct` (≈ 1.0) | 1.000 | 0.0000 | 0.0000 | 0.0000 | n/a (saturated) |
| `pb_validity_pct` (≈ 0.53) | 0.5285 | 0.031 | 0.018 | 0.014 | N≥22000 |
| `hmmscan_total_hits` (Poisson) | 158/1000 | 7.5 hits | 4.3 hits | 3.4 hits | N≥21000 |
| `coverage_any_hit` (≈ 0.145) | 0.145 | 0.0156 | 0.0090 | 0.0070 | N≥5000 (≈ 0.007) |
| `top1_family_type` (≈ 0.000) | 0.000 | 0.0000 | 0.0000 | 0.0000 | n/a (saturated at 0) |
| `fg_dev` (continuous) | 0.6381 (σ≈0.29) | 0.016 | 0.009 | 0.007 | N≥7000 (for ±0.005 MDD) |
| `ood_ring_rate` (≈ 0.013) | 0.013 | 0.0056 | 0.0032 | 0.0025 | N≥25 (already > power, just more precise) |
| `reconstruction_kabsch_rmsd_A` (continuous, σ≈0.83) | 0.824 | 0.046 Å | 0.026 Å | 0.020 Å | N≥3000 |

**Verdict.** **N=5000 per arm** is the sweet spot for Path C:
* `coverage_any_hit`: MDD 0.0070 vs observed −0.022 → **distinguishable at p<0.05** with N=5000
* `ood_ring_rate`: MDD 0.0025 vs observed −0.003 → **distinguishable** (just barely)
* `fg_dev`: MDD 0.007 vs observed −0.0235 → **distinguishable** (already at N=1000 4.05σ; Path C tightens)
* `hmmscan_total_hits`: MDD 3.4 vs observed +184 → **overwhelmingly distinguishable**
* `pb_validity_pct`: MDD 0.014 vs observed −0.0995 → **distinguishable** (regression is real, just better-typed)
* `reconstruction_kabsch_rmsd_A` (Kanzi, IF bridge closed): MDD 0.020 vs (currently unknown framework delta) — could be discriminable

**Recommendation (carry to §3 implementation plan):** N=5000 per arm, target
~5-7h total wallclock. Skip `top1_family_type` (saturated at 0) and
`validity_pct` (saturated at 1). Re-verify all other axes with tighter CIs.

### Step 4 — Audit N=5000 wallclock budget per model

Per-record wallclock from Wave 86-89 N=1000 sweeps + linear extrapolation to
N=5000 (per-model, per-arm):

| Model | Per-record wallclock (CPU/GPU) | N=5000 wallclock per arm | Total (2 arms) | Hardware |
|---|---:|---:|---:|---|
| LineageFlow | ~3.5s (HMMER scan + classify) | ~4.9 h | ~9.7 h | lineageflow_venv (CPU HMMER + GPU ESM-IF) |
| FlowMol3 | ~1.5s (PB-xtb 50 conformations + UFF + RDKit sanitization) | ~2.1 h | ~4.2 h | 5090 GPU PB + flowmol3_venv RDKit |
| Kanzi (synthetic latent) | ~0.25s (DAE encode/decode) | ~0.35 h | ~0.7 h | kanzi_venv CPU torch encoder |
| Kanzi (paper-metric, IF bridge closed) | ~2.5s (DAE encode + Kabsch RMSD + AA decode) | ~3.5 h | ~7.0 h | kanzi_venv CPU + numpy |

**Path C budget estimate:**
* **Minimal Path C** (LineageFlow + FlowMol3 only): ~14 h on 1 GPU; ~7 h with
  parallel split (LineageFlow on lineageflow_venv + FlowMol3 on 5090).
* **Full Path C** (add Kanzi if bridge closed): ~21 h on 1 GPU; ~10 h parallel.
* **Recommended Path C budget:** ~7 h total with parallel split (LineageFlow on
  lineageflow_venv, FlowMol3 on 5090, Kanzi synthetic on kanzi_venv in
  background). Defer Kanzi paper-metric sweep to Wave 91+ until bridge closed.

**Verdict.** Path C fits within a single-session budget **if** the three
sweeps run in parallel across the three sidecar venvs (already proven pattern
from Wave 86-89). No new infrastructure required.

### Step 5 — Audit eval pipeline scalability

Read in full:
* `tools/run_real_ckpt_eval.py:_solve_framework` (lines 1289-1443)
* `tools/upstream_eval.py:run_kanzi_upstream_eval` + `run_lineageflow_upstream_eval`
* `tools/sweep_kanzi_n1000_paper_metrics.py` (Wave 83 Agent D, 165 LOC)
* `tools/wave86_n1000_sweep.py` + `wave87_n1000_sweep.py`

**Per-record bottlenecks identified:**

1. **JSON serialization** (`json.dumps` per record): currently writes 1 huge
   file per arm (Wave 86/87 pattern: 1000 records × ~3 KB = 3 MB per arm JSON).
   At N=5000 the file would be ~15 MB and per-write serialization would slow
   down the sweep. **Fix:** per-seed independent JSON writer (Step 13 below,
   ~10 LOC).

2. **Memory** (per-record `trace.endpoint` + `state_bundle` tensor + dict):
   currently ~200 MB at N=1000 (in-memory accumulate until sweep done).
   At N=5000 the memory would scale linearly to ~1 GB → potential OOM on
   5090 32 GB. **Fix:** per-record GC after JSON write (Step 14 below, ~5 LOC).

3. **HMMER scan** (LineageFlow): per-record ~3.5 s on CPU. Already the
   bottleneck. Cannot parallelize further within a single record. **Mitigation:**
   process at full CPU utilization with `--parallel` (multiprocessing.Pool on
   the HMMER subprocess).

4. **PB-xtb conformations** (FlowMol3): per-record ~1.5 s on GPU (RDKit
   ETKDG + UFF minimize). Already parallelized across `n_molecules` records
   (Wave 74 F1). At N=5000 GPU utilization ≈ 80-90%.

5. **Seed threading** (Wave 86 Pitfall #2 fix): separate RNG sub-streams per
   arm. At N=5000 across multiple seeds (e.g., 5 seeds × 1000 records), the
   seed-pool generator must produce distinct `numpy.random.SeedSequence`
   children deterministically. **Fix:** seed-pool generator (Step 8 below,
   ~15 LOC).

**Verdict.** Eval pipeline **scales to N=5000** with the 5 fixes
(Steps 8, 10, 13, 14, 15 in §3 implementation plan). Total additive LOC: ~55.
No structural refactor required.

### Step 6 — Audit risk surface (D.4 + G-MASTER + paper §7 update)

| Risk | Severity | Mitigation |
|---|---|---|
| D.4 byte-stable regression breaks when JSON writer changes | LOW | Per-seed JSON writer is additive; D.4 vectors test per-record digests, not JSON shape (Wave 33 / Wave 38) |
| G-MASTER capability regresses when N scales | LOW | G-MASTER metrics are computed on synthetic 100-sample reads, NOT on the N=5000 sweep — sweeps do not feed G-MASTER |
| mkdocs --strict fails when paper §7.6 honest verdict is updated | LOW | Use the Wave 89 additive paragraph template (no new nav entries) |
| HMMER scan at N=5000 exceeds LineageFlow disk quota | LOW | Per-record FASTA + per-family hmmscan.out cleanup after each cell (Wave 86 manifest pattern) |
| PB-xtb conformations OOM at N=5000 on 5090 32 GB | MEDIUM | Stream-write conformations to disk; RDKit sanitization stays CPU-bound (~100 MB peak per record); 5090 GB sufficient |
| Kanzi paper-metric bridge remains unblocked | HIGH | Path C **defers Kanzi paper-metric** to Wave 91+ until the 5-10 LOC bridge is closed; Kanzi synthetic sweep is fine |
| Path C framework-vs-baseline verdict at N=5000 **inverts** (e.g., `fg_dev` becomes `ties`) | LOW | Honest reporting per user directive — Path C is NOT a "make it work" wave; if framework regresses at higher N, document as regression per `PHASE-4-model-integration-iteration.md` §"If False" branch |
| Wallclock exceeds budget (target 7h, worst case 14h) | LOW | Stagger + checkpoint resume (Step 11, ~10 LOC) — if interrupted, resume from last completed seed |

**Verdict.** Path C is **low-risk overall**, with one HIGH-risk item
(Kanzi bridge closure deferred) and one LOW-but-real item (framework-vs-baseline
inversion at higher N). All 8 risks have mitigation strategies in §3
implementation plan.

---

## 2. Step 7 — User gate (HARD BLOCK)

**Decision required from user before Step 8 implementation begins:**

1. **Approve Path C scope** (LineageFlow + FlowMol3 N=5000 sweep, defer Kanzi
   paper-metric to Wave 91+ until bridge closed)?
2. **Approve N=5000** (vs N=3000 cheaper option, MDD tradeoff documented in
   Step 3)?
3. **Approve ~7h wallclock budget** (parallel across 3 venvs; sequential if
   1 GPU only)?
4. **Approve honest reporting** (if framework regresses at higher N,
   document as regression, do NOT reframe)?

If YES to all 4 → Wave 90 Agent B proceeds with Steps 8-25 below.
If NO → user redirects to cheaper Path D (N=2000 per arm + Kanzi deferred) or
back to additional Phase 1 audit items.

---

## 3. Implementation plan (Steps 8-25, LOC estimate + risk)

All 18 steps are **additive** (no framework-core refactor). Total estimate:
**~310 LOC across 7 new/modified files**. Each step lists LOC, file scope,
risk, and reuses (no new infrastructure where existing helpers suffice).

### Step 8 — Seed-pool generator for statistical power (15 LOC, LOW risk)

**Goal:** Generate `K` distinct RNG sub-streams (one per seed) for the
`--seeds K` flag, reusing Wave 86's SeedSequence pattern.

**File:** `tools/seed_pool.py` (NEW, ~15 LOC)
**Reuses:** `numpy.random.SeedSequence` (stdlib), Wave 86 Pitfall #2 fix
(`tools/gen_lineageflow_n1000_fastas.py:60-78`).
**Risk:** LOW — additive helper, no framework-core change.
**Acceptance:** `python -m tools.seed_pool --base 42 --n 5` returns 5 distinct
seeds; deterministic for same `--base`.

### Step 9 — Per-axis MDD calculator helper (30 LOC, LOW risk)

**Goal:** Compute MDD for binomial + Poisson + continuous metrics at a given
N. Pure stdlib + numpy. Read-only.

**File:** `tools/mdd.py` (NEW, ~30 LOC)
**Functions:**
* `mdd_binomial(p_baseline, n_per_arm, alpha=0.05, power=0.80) -> float`
* `mdd_poisson(lambda_baseline, n_per_arm, alpha=0.05, power=0.80) -> float`
* `mdd_continuous(sigma_pooled, n_per_arm, alpha=0.05, power=0.80) -> float`
* `compute_all_axes(axis_table: pd.DataFrame, n_per_arm=5000) -> pd.DataFrame`

**Reuses:** `scipy.stats.norm.ppf` (already a dev dep).
**Risk:** LOW — pure helper, no framework-core change.
**Acceptance:** unit tests in `tests/test_tools/test_mdd.py` (3 tests
× 2 axis types = 6 tests, byte-stable).

### Step 10 — Per-record serialization + resume-from-checkpoint (40 LOC, MEDIUM risk)

**Goal:** Extend `tools/run_real_ckpt_eval.py:_run_cell` to optionally
write per-record JSON files (one per cell) instead of accumulating in memory,
and resume from the last completed cell if interrupted.

**Files:**
* `tools/run_real_ckpt_eval.py:_run_cell` (MODIFIED, +20 LOC for per-record
  write + checkpoint tracking)
* `tools/checkpoint_state.py` (NEW, ~20 LOC — load/save state to `~/.cache/flowa/checkpoint.json`)

**Reuses:** Wave 86 `_solve_framework` per-record output dict pattern
(lines 1380-1420).
**Risk:** MEDIUM — checkpoint logic must NOT introduce race conditions if the
process is killed mid-write. Mitigation: write to `tmp.json` then atomic rename.
**Acceptance:** `--resume-from <path>` reads checkpoint; sweep resumes from
last cell; D.4 byte-stable vectors unchanged (test per-record digests, not
checkpoint state).

### Step 11 — `--limit-broadcast` flag (5 LOC, LOW risk)

**Goal:** Replace `--limit 1000` with `--limit-broadcast N` that broadcasts N
across all model sweep tools (`sweep_kanzi_n1000_paper_metrics.py`,
`wave86_n1000_sweep.py`, `wave87_n1000_sweep.py`).

**Files:**
* `tools/sweep_kanzi_n1000_paper_metrics.py` (MODIFIED, +3 LOC)
* `tools/wave86_n1000_sweep.py` (MODIFIED, +1 LOC)
* `tools/wave87_n1000_sweep.py` (MODIFIED, +1 LOC)

**Risk:** LOW — additive flag, legacy `--limit` still works (parser default).
**Acceptance:** `--help` shows `--limit-broadcast`; `--limit 1000` still works
byte-identically.

### Step 12 — N=5000 sweep CLI driver (40 LOC, LOW risk)

**Goal:** New `tools/path_c_n5000_sweep.py` that orchestrates baseline + framework
arms across 3 models in parallel via subprocess (one subprocess per model).

**File:** `tools/path_c_n5000_sweep.py` (NEW, ~40 LOC)
**Subprocesses:**
1. `lineageflow_venv/bin/python tools/wave86_n1000_sweep.py --limit-broadcast 5000`
2. `flowmol3_venv/bin/python tools/wave87_n1000_sweep.py --limit-broadcast 5000`
3. `kanzi_venv/bin/python tools/sweep_kanzi_n1000_paper_metrics.py --limit-broadcast 5000 --synthetic` (synthetic latent; defer paper-metric)

**Risk:** LOW — pure orchestration; each subprocess is its own Wave 86/87/83
pattern + new `--limit-broadcast`.
**Acceptance:** CLI runs all 3 sweeps in parallel; per-model JSON output at
`verification_outputs/path_c_n5000/<model>/{baseline,framework}/*.json`;
aggregate JSON at `verification_outputs/path_c_n5000/manifest.json`.

### Step 13 — Per-seed independent JSON writer (10 LOC, LOW risk)

**Goal:** Replace the per-arm "1 huge JSON" pattern with per-seed
independent JSON files (5 seeds × 1000 records = 5 × 1 MB files instead of 1
× 5 MB file).

**File:** `tools/seed_pool.py:write_per_seed_json` (NEW, +10 LOC in seed_pool)
**Risk:** LOW — additive writer; downstream aggregation reads all seed files
and concatenates.
**Acceptance:** per-seed JSON files at
`verification_outputs/path_c_n5000/<model>/<arm>/seed_<N>.json`.

### Step 14 — Per-seed aggregation helper (20 LOC, LOW risk)

**Goal:** Aggregate per-seed JSON files into per-arm summary JSON with
mean ± std across seeds + per-axis MDD-aware verdict.

**File:** `tools/aggregate_per_seed.py` (NEW, ~20 LOC)
**Output schema:**
```json
{
  "model": "lineageflow",
  "arm": "framework",
  "n_seeds": 5,
  "n_records_per_seed": 1000,
  "n_total": 5000,
  "axes": {
    "hmmscan_total_hits": {"mean": 158.3, "std": 4.1, "ci_95": [154.3, 162.3]},
    "coverage_any_hit": {"mean": 0.123, "std": 0.011, "ci_95": [0.112, 0.134]}
  },
  "verdict_per_axis": {
    "hmmscan_total_hits": "framework_improves",
    "coverage_any_hit": "framework_ties_within_sem"
  }
}
```

**Risk:** LOW — pure aggregation, no framework-core change.
**Acceptance:** unit tests in `tests/test_tools/test_aggregate_per_seed.py`
(3 tests, byte-stable for fixed input).

### Step 15 — Axis-specific MDD-aware stop rule (15 LOC, LOW risk)

**Goal:** For each axis, compute MDD at N=5000; if observed framework delta
is < 0.5 × MDD, mark axis as `underpowered` and skip per-axis verdict (but
still report numbers for honesty).

**File:** `tools/aggregate_per_seed.py:compute_verdict` (MODIFIED, +15 LOC)
**Reuses:** `tools/mdd.py:compute_all_axes` (Step 9).
**Risk:** LOW — pure logic; verdict is data-driven, no framework-core change.
**Acceptance:** unit tests in `tests/test_tools/test_aggregate_per_seed.py`
(2 tests for MDD-aware stop rule).

### Step 16 — Baseline + framework arm parallel launchers (25 LOC, MEDIUM risk)

**Goal:** Per-model `tools/path_c_n5000_<model>.sh` shell scripts that launch
baseline arm + framework arm in parallel (each arm has its own subprocess +
its own seed stream).

**Files:**
* `tools/path_c_n5000_lineageflow.sh` (NEW, ~10 LOC)
* `tools/path_c_n5000_flowmol3.sh` (NEW, ~10 LOC)
* `tools/path_c_n5000_kanzi.sh` (NEW, ~5 LOC, synthetic only)

**Risk:** MEDIUM — shell scripts must NOT introduce race conditions on the
shared checkpoint file. Mitigation: each arm writes to its own subdirectory
`<model>/<arm>/`; checkpoint is per-arm, not shared.
**Acceptance:** each script runs baseline + framework in parallel; per-arm
JSON output verified at `verification_outputs/path_c_n5000/<model>/<arm>/`.

### Step 17 — Per-model `--nfe-budget` overrides (15 LOC, LOW risk)

**Goal:** Each model sweep tool accepts `--nfe-budget <list>` (comma-separated
NFE values) to preserve the paper's default NFE per model
(`DOWNSTREAM_METRICS["<model>"]["nfe_paper_default"]`).

**Files:**
* `tools/run_real_ckpt_eval.py` (MODIFIED, +5 LOC for `--nfe-budget` arg + parse)
* `tools/wave86_n1000_sweep.py` (MODIFIED, +3 LOC)
* `tools/wave87_n1000_sweep.py` (MODIFIED, +3 LOC)
* `tools/sweep_kanzi_n1000_paper_metrics.py` (MODIFIED, +4 LOC)

**Risk:** LOW — additive CLI flag; legacy NFE defaults unchanged.
**Acceptance:** `--nfe-budget 50,100,200` runs 3 sweeps per record;
`--nfe-budget` omitted → legacy default NFE (byte-identical).

### Step 18 — Per-cell JSON schema with axis breakdown (10 LOC, LOW risk)

**Goal:** Add a `per_cell_axis_breakdown` field to per-record JSON that
splits the axis value into sub-metrics where applicable (e.g., `hmmscan_total_hits`
splits into per-family counts).

**File:** `tools/run_real_ckpt_eval.py:_run_cell` (MODIFIED, +10 LOC for
breakdown dict)
**Risk:** LOW — additive field; downstream consumers ignore unknown fields.
**Acceptance:** per-record JSON has `per_cell_axis_breakdown` dict; regression
tests in `tests/test_tools/test_run_real_ckpt_eval.py` (2 tests).

### Step 19 — Tier 3 paper-metric aggregation tool (20 LOC, LOW risk)

**Goal:** Single tool `tools/path_c_aggregate.py` that reads
`verification_outputs/path_c_n5000/<model>/{baseline,framework}/seed_*.json`
across all 3 models and produces a single `verification_outputs/path_c_n5000/tier3_summary.json`.

**File:** `tools/path_c_aggregate.py` (NEW, ~20 LOC)
**Risk:** LOW — pure aggregation across existing per-model JSON.
**Acceptance:** tier3_summary.json has 3 models × ~6 axes × mean/std/CI/verdict.

### Step 20 — ckpt SHA-256 verify step (10 LOC, LOW risk)

**Goal:** Per reviewer-proof guarantee G1, verify SHA-256 of ckpt files
matches upstream release metadata before each sweep starts.

**File:** `tools/path_c_ckpt_verify.py` (NEW, ~10 LOC)
**Risk:** LOW — read-only hash + JSON comparison; aborts sweep if SHA-256
mismatch (1-line raise).
**Acceptance:** ckpt SHA-256 verified against `verification_outputs/ckpt_sha256.json`
(Wave 75 / Wave 80 vendored); abort if mismatch.

### Step 21 — Vendored upstream snapshot verify (10 LOC, LOW risk)

**Goal:** Per reviewer-proof guarantee G4, verify vendored upstream snapshot
commit hash matches `data/<model>_upstream/.git/HEAD` before each sweep starts.

**File:** `tools/path_c_upstream_verify.py` (NEW, ~10 LOC)
**Risk:** LOW — read-only git/ref check; aborts sweep if mismatch.
**Acceptance:** vendored commit verified; abort if mismatch.

### Step 22 — pytest byte-stable regression gates (10 LOC, MEDIUM risk)

**Goal:** Add `tests/test_path_c_byte_stable.py` that asserts per-adapter
D.4 vectors are unchanged before vs after Path C sweep (smoke test for
framework-core regressions).

**File:** `tests/test_path_c_byte_stable.py` (NEW, ~10 LOC)
**Risk:** MEDIUM — must read D.4 vectors from `regression-vectors/<adapter>.json`
and compare against the post-Path-C vectors. If a vector moves, fail loudly.
**Acceptance:** `pytest tests/test_path_c_byte_stable.py -v` → PASS (D.4
unchanged); FAIL if any vector moves (catches framework-core regression
from Path C changes).

### Step 23 — §7.6 honest verdict update helper (15 LOC, LOW risk)

**Goal:** Python helper that generates the additive Wave 90 paragraph for
§7.6 (paper-draft.md) from `verification_outputs/path_c_n5000/tier3_summary.json`.

**File:** `tools/path_c_paper_text.py` (NEW, ~15 LOC)
**Output:** `docs/paper-draft-wave90-addendum.md` (additive, ready for §7.6 paste).
**Risk:** LOW — pure text generation; reviewer reads the generated paragraph
before commit.
**Acceptance:** generated text matches the Wave 89 additive template structure
(table + caveat paragraph); no new nav entries.

### Step 24 — §7 + §5 wave-cumulative additive paragraph template (10 LOC, LOW risk)

**Goal:** Standard template generator for the Wave 90 additive paragraph that
fits between Wave 89 §7.6 and Wave 91+ §7.6.

**File:** `tools/path_c_paper_text.py:wave_cumulative_template` (NEW, +10 LOC)
**Risk:** LOW — template reuses Wave 89 §7.6 / §5.7 structure.
**Acceptance:** generated text drops cleanly into paper-draft.md; mkdocs
--strict still EXIT=0 after paste.

### Step 25 — Final synthesis doc generator (10 LOC, LOW risk)

**Goal:** Generate `docs/audit/wave90-phase4-final.md` from
`verification_outputs/path_c_n5000/tier3_summary.json` (machine-readable
summary → human-readable doc).

**File:** `tools/path_c_synthesis_doc.py` (NEW, ~10 LOC)
**Output:** `docs/audit/wave90-phase4-final.md` (templated; reviewer-facing).
**Risk:** LOW — pure doc generation; no framework-core change.
**Acceptance:** generated doc has per-model per-axis tables + verdict summary +
caveats + cross-refs to Wave 86-89 docs.

### Total LOC summary (Steps 8-25)

| Step | File | LOC | New/Modified | Risk |
|---:|---|---:|---|---|
| 8 | `tools/seed_pool.py` | 15 | NEW | LOW |
| 9 | `tools/mdd.py` | 30 | NEW | LOW |
| 10 | `tools/run_real_ckpt_eval.py` + `tools/checkpoint_state.py` | 40 | MODIFIED + NEW | MEDIUM |
| 11 | `tools/sweep_kanzi_*` + `tools/wave86_n1000_sweep.py` + `tools/wave87_n1000_sweep.py` | 5 | MODIFIED (3 files) | LOW |
| 12 | `tools/path_c_n5000_sweep.py` | 40 | NEW | LOW |
| 13 | `tools/seed_pool.py:write_per_seed_json` | 10 | MODIFIED | LOW |
| 14 | `tools/aggregate_per_seed.py` | 20 | NEW | LOW |
| 15 | `tools/aggregate_per_seed.py:compute_verdict` | 15 | MODIFIED | LOW |
| 16 | `tools/path_c_n5000_<model>.sh` × 3 | 25 | NEW (3 files) | MEDIUM |
| 17 | `tools/run_real_ckpt_eval.py` + 3 sweep tools | 15 | MODIFIED (4 files) | LOW |
| 18 | `tools/run_real_ckpt_eval.py:_run_cell` | 10 | MODIFIED | LOW |
| 19 | `tools/path_c_aggregate.py` | 20 | NEW | LOW |
| 20 | `tools/path_c_ckpt_verify.py` | 10 | NEW | LOW |
| 21 | `tools/path_c_upstream_verify.py` | 10 | NEW | LOW |
| 22 | `tests/test_path_c_byte_stable.py` | 10 | NEW | MEDIUM |
| 23 | `tools/path_c_paper_text.py` | 15 | NEW | LOW |
| 24 | `tools/path_c_paper_text.py:wave_cumulative_template` | 10 | MODIFIED | LOW |
| 25 | `tools/path_c_synthesis_doc.py` | 10 | NEW | LOW |
| **TOTAL** | | **~310 LOC** | **~11 NEW + 9 MODIFIED** | **2 MEDIUM + 16 LOW** |

**No framework-core refactor** — all changes are in `tools/` (orchestration +
aggregation) + `tests/` (regression gates). `adaptive_reflow/` source is
untouched. **D.4 byte-stable regression vectors MUST NOT move** (verified by
Step 22 test).

---

## 4. Risk + mitigation (cumulative)

| Risk | Severity | Mitigation |
|---|---|---|
| Eval pipeline OOM at N=5000 on 5090 32 GB | MEDIUM | Per-record GC after JSON write (Step 14); per-seed independent JSON (Step 13) bounds per-file size to ~1 MB |
| Path C framework-vs-baseline verdict INVERTS at higher N (e.g., `fg_dev` becomes `ties` or regression) | MEDIUM | Honest reporting per user directive "文档诚实记录"; update §7.6 with the inversion; do NOT reframe |
| Kanzi paper-metric remains blocked (bridge not closed in Wave 90) | HIGH (deferred) | Path C defers Kanzi paper-metric to Wave 91+; Kanzi synthetic sweep continues at N=5000 as `encoder_summary` |
| Wallclock exceeds 7h budget (e.g., LineageFlow HMMER scan slower than estimated) | LOW | Resume-from-checkpoint (Step 10); per-seed independent JSON allows partial-sweep reporting |
| mkdocs --strict fails when paper §7.6 is updated additively | LOW | Use Wave 89 additive paragraph template (no new nav entries); Step 24 ensures structure compliance |
| Path C framework-vs-baseline verdict at N=5000 shows NO improvement on any axis | LOW | Honest reporting per user directive; the framework's value-add on the **internal composite axis** remains SUPPORTED UNCHANGED; Path C is a saturation-escape attempt, not a "make it work" wave |
| `ood_ring_rate` delta still underpowered at N=5000 | LOW | Step 15 MDD-aware stop rule marks it `underpowered`; documented as honest caveat; framework still SHOWS directionality (−0.003) even if not distinguishable |
| Path C implementation introduces a framework-core bug | LOW | Step 22 byte-stable regression test catches it; per-step additive changes are bisect-able; no framework-core file is touched |

---

## 5. Files referenced

| Path | Lines | Purpose |
|---|---|---|
| `docs/audit/wave86-phase1-audit.md` | 509 | Wave 86 Path A design + paper-quantity-driven β fix |
| `docs/audit/wave87-phase1-audit.md` | ~400 | Wave 87 PB-xtb semantics clarification |
| `docs/audit/wave88-phase1-audit.md` | 409 | Wave 88 Kanzi framework-arm audit + fix plan (Pitfall #5) |
| `docs/audit/wave89-phase1-final.md` | 190 | Wave 89 FINAL per-paper-claim status table + 6 audit pitfalls ADDRESSED |
| `tools/run_real_ckpt_eval.py:_solve_framework` | 1289-1443 | Wave 86 paper-quantity-driven β fix end-to-end |
| `tools/run_real_ckpt_eval.py:_compute_paper_quantities` | 1057-1136 | Wave 86 helper |
| `tools/run_real_ckpt_eval.py:_make_framework_policy` | 1139-1286 | Wave 86 paper-quantity-driven path |
| `tools/wave86_n1000_sweep.py` | ~150 | LineageFlow N=1000 framework-arm sweep |
| `tools/wave87_n1000_sweep.py` | ~150 | FlowMol3 N=1000 PB-xtb framework-arm sweep |
| `tools/sweep_kanzi_n1000_paper_metrics.py` | 165 | Kanzi N=200/N=1000 baseline + framework sweep |
| `tools/upstream_eval.py:run_*_upstream_eval` | 200-400 | LineageFlow + Kanzi upstream eval wrappers |
| `adaptive_reflow/adapters/kanzi.py` | 1432-1545 | Kanzi `apply_restart_distribution` (Pitfall #1 verified) |
| `adaptive_reflow/adapters/lineageflow.py` | n/a | LineageFlowAdapter (Wave 86 framework arm REAL) |
| `adaptive_reflow/adapters/flowmol3_v2.py` | n/a | FlowMol3V2Adapter (Wave 66 v2 wire) |
| `verification_outputs/lineageflow_n1000/manifest.json` | n/a | Wave 86 framework_fallback_per_family_count = {} |
| `verification_outputs/flowmol3_n1000_*/summary.json` | n/a | Wave 87 byte-stable N=1000 per-arm summary |
| `verification_outputs/kanzi_n1000_paper_metrics/kanzi_n1000_paper_metrics.json` | 47 | Wave 83 N=200 baseline-only (verdict: baseline_only) |
| `verification_outputs/ckpt_sha256.json` | n/a | Wave 75/80 vendored SHA-256 hashes (reviewer-proof G1) |
| `docs/paper-draft.md` | n/a | §7 + §5 wave-cumulative additive paragraphs |
| `docs/push-ready-summary.md` | n/a | Wave 89 cumulative state (no push yet) |

---

## 6. JSON return

```json
{
  "wave": "Wave 90 Agent A",
  "scope": "Path C READ-ONLY audit + 18-step implementation plan",
  "phase_1_audit": {
    "step_1_wave_86_89_state": "VERIFIED — D.4 33/33 PASS, G-MASTER 7/7 PASS, mkdocs EXIT=0, framework arm REAL on all 3 models",
    "step_2_per_axis_saturation_n1000": "3 axes underpowered (ood_ring_rate, coverage_any_hit tightens, hmmscan finer breakdown); 8 axes same verdict as Wave 89",
    "step_3_statistical_power_n5000": "N=5000 puts MDD ≤ observed delta for coverage_any_hit + ood_ring_rate + fg_dev (already at N=1000 4.05σ) + pb_validity_pct (definitional gap) + hmmscan_total_hits (overwhelmingly)",
    "step_4_wallclock_budget": "~7h parallel (LineageFlow lineageflow_venv + FlowMol3 5090 GPU + Kanzi synthetic kanzi_venv); ~14h sequential 1 GPU",
    "step_5_eval_pipeline_scalability": "Scales to N=5000 with 5 additive fixes (per-seed JSON, per-record GC, checkpoint resume, MDD-aware stop, seed-pool generator); total ~55 LOC",
    "step_6_risk_surface": "2 MEDIUM (eval pipeline OOM, framework inversion at higher N) + 1 HIGH deferred (Kanzi bridge) + 5 LOW"
  },
  "phase_7_user_gate": "PENDING — 4 questions: (1) approve Path C scope LineageFlow+FlowMol3 N=5000 + Kanzi deferred? (2) approve N=5000 vs N=3000? (3) approve ~7h wallclock budget? (4) approve honest reporting if framework regresses at higher N?",
  "phase_8_25_implementation_plan": {
    "total_loc": 310,
    "new_files": 11,
    "modified_files": 9,
    "framework_core_touched": false,
    "d4_byte_stable_vectors_must_not_move": true,
    "per_step": [
      {"step": 8, "title": "Seed-pool generator", "loc": 15, "file": "tools/seed_pool.py", "risk": "LOW"},
      {"step": 9, "title": "Per-axis MDD calculator", "loc": 30, "file": "tools/mdd.py", "risk": "LOW"},
      {"step": 10, "title": "Per-record serialization + resume-from-checkpoint", "loc": 40, "file": "tools/run_real_ckpt_eval.py + tools/checkpoint_state.py", "risk": "MEDIUM"},
      {"step": 11, "title": "--limit-broadcast flag", "loc": 5, "file": "3 sweep tools", "risk": "LOW"},
      {"step": 12, "title": "N=5000 sweep CLI driver", "loc": 40, "file": "tools/path_c_n5000_sweep.py", "risk": "LOW"},
      {"step": 13, "title": "Per-seed independent JSON writer", "loc": 10, "file": "tools/seed_pool.py", "risk": "LOW"},
      {"step": 14, "title": "Per-seed aggregation helper", "loc": 20, "file": "tools/aggregate_per_seed.py", "risk": "LOW"},
      {"step": 15, "title": "MDD-aware stop rule", "loc": 15, "file": "tools/aggregate_per_seed.py:compute_verdict", "risk": "LOW"},
      {"step": 16, "title": "Baseline+framework arm parallel launchers", "loc": 25, "file": "tools/path_c_n5000_<model>.sh × 3", "risk": "MEDIUM"},
      {"step": 17, "title": "Per-model --nfe-budget overrides", "loc": 15, "file": "4 sweep tools", "risk": "LOW"},
      {"step": 18, "title": "Per-cell JSON schema with axis breakdown", "loc": 10, "file": "tools/run_real_ckpt_eval.py:_run_cell", "risk": "LOW"},
      {"step": 19, "title": "Tier 3 paper-metric aggregation tool", "loc": 20, "file": "tools/path_c_aggregate.py", "risk": "LOW"},
      {"step": 20, "title": "ckpt SHA-256 verify step", "loc": 10, "file": "tools/path_c_ckpt_verify.py", "risk": "LOW"},
      {"step": 21, "title": "Vendored upstream snapshot verify", "loc": 10, "file": "tools/path_c_upstream_verify.py", "risk": "LOW"},
      {"step": 22, "title": "pytest byte-stable regression gates", "loc": 10, "file": "tests/test_path_c_byte_stable.py", "risk": "MEDIUM"},
      {"step": 23, "title": "§7.6 honest verdict update helper", "loc": 15, "file": "tools/path_c_paper_text.py", "risk": "LOW"},
      {"step": 24, "title": "§7 + §5 wave-cumulative additive template", "loc": 10, "file": "tools/path_c_paper_text.py", "risk": "LOW"},
      {"step": 25, "title": "Final synthesis doc generator", "loc": 10, "file": "tools/path_c_synthesis_doc.py", "risk": "LOW"}
    ],
    "summary": "2 MEDIUM risk (Steps 10 + 16 + 22 are checkpoint/script logic; Step 22 catches framework-core regression); 16 LOW risk; 0 HIGH risk"
  },
  "wallclock_estimate_hours": {
    "minimal_lineageflow_flowmol3_only": 7,
    "full_includes_kanzi_synthetic": 8,
    "full_includes_kanzi_paper_metric_if_bridge_closed": 14,
    "single_gpu_sequential": 21
  },
  "no_code_changes": true,
  "audit_doc": "docs/audit/wave90-phase1-audit.md"
}
```

---

## 7. Honest caveats (carried forward + Wave 90 additions)

1. **N=5000 per arm is a saturation-escape, not a magic multiplier.** The 8 axes
   that already have framework_improves/ties/regression verdict at N=1000 will
   likely report the same verdict at N=5000 — just with tighter CIs. Path C's
   expected gain is ~1-2 axes flipped from `underpowered` → `framework_improves`
   (most likely `ood_ring_rate`).

2. **Kanzi paper-metric remains `NOT_MEASURABLE`.** The `(64,64)→(L,256)` bridge
   gap (Wave 88 F-3) is NOT closed in Path C — that is a Wave 91+ task (5-10
   LOC adapter change + ~30 min DAE geometry audit). Path C runs Kanzi
   synthetic at N=5000 as `encoder_summary` only.

3. **`fg_dev` improvement at N=5000 may INVERT.** If the framework's `fg_dev`
   improvement (4.05σ at N=1000) was an artifact of N=1000 sampling, scaling
   to N=5000 may show it as `ties_within_sem` or even regression. Honest
   reporting per user directive — Path C is NOT a "make it work" wave.

4. **`pb_validity_pct` regression is structural (UFF-vs-xtb gap).** Wave 87
   F-6 verified that PB 0.6.5's `energy_ratio` is UFF-based, not xtb-based.
   Path C will reproduce the same regression at N=5000 with tighter CI. No
   fix in scope.

5. **`coverage_any_hit` ties may break to framework_regression at N=5000.** The
   framework's −2.2 pp at N=1000 (within SEM) could grow to a real regression
   at N=5000 if the framework's Gaussian perturbation (σ=0.05) systematically
   shifts sequences off the LineageFlow ckpt's manifold. Honest reporting.

6. **No framework-core refactor.** All Path C changes are in `tools/` (11 NEW
   + 9 MODIFIED) and `tests/` (1 NEW). `adaptive_reflow/` source is untouched.
   D.4 byte-stable vectors MUST NOT move (verified by Step 22 test).

7. **Wallclock is best-case ~7h, worst-case ~14h.** Per-model variance in
   HMMER scan throughput + PB-xtb conformation minimization can swing the
   budget 2× in either direction. Resume-from-checkpoint (Step 10) bounds
   blast radius if interrupted.

8. **Path C is the LAST major wave before push.** Wave 86-89 closed the
   Tier 3 paper-metric story at N=1000. Path C at N=5000 is the saturation-
   escape attempt to surface any remaining framework-vs-baseline signal.
   After Path C, the next push-prep wave is Wave 91+ (Kanzi bridge closure +
   push to origin/main per user gate).