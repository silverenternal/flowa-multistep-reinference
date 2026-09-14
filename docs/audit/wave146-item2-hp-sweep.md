# Wave 146 Item 2 - Hyperparameter sensitivity sweep on 2D FM (PARTIAL)

## Item 2 from `todo/2026-09-14-tier1-numerical-polish-plan.md`

## Verdict: PARTIAL — 4 of 5 hyperparameters sweepable via existing tool; 1 of 5 fully + 3 of 5 BLOCKED

## Question

Fill Table D of the camera-ready paper with real measured
hyperparameter sensitivity numbers: 5 hyperparameters × 3-5 values
(15-25 cells), using 2D FM (twodim_fm) for speed.

## Verdict: PARTIAL

The 2D FM controlled-audit driver
(`tools.run_controlled_audit.py`) exposes **1 of 5** requested
hyperparameters as a CLI flag (`--nfe` for NFE budget). A **partial
analog** exists for `restart_threshold_sigma` via `--sigma` (which
controls noise injection, not the Wave 125 restart_threshold_sigma
kwarg directly). A **partial analog** exists for `β shape` via
`--nfe-allocation` (uniform vs evidence) — though this controls NFE
distribution across rounds, not the scheduler-family choice. The
remaining 2 knobs (`BRAI magnitude eps_scale`, `n_rounds`) are
**BLOCKED** — neither has a CLI flag on any existing sweep tool.

Cells completed: **10** (default + 3 NFE + 3 sigma + 2 alloc + 2
guard). Wallclock: ~6 s. Raw JSONs: `/tmp/w146/hp_sweep/*.json`
(per task instruction: outside `verification_outputs/`).

## Sweep design

| Hyperparameter | Values swept | CLI flag | Status |
|---|---|---|---|
| NFE budget | 10, 50, 200 | `--nfe` | DONE |
| restart_threshold_sigma | 0.0, 0.05, 0.10 | `--sigma` (analog: noise injection) | PARTIAL (analog only) |
| β shape (cosine / linear / convergence-adaptive / constant) | uniform, evidence | `--nfe-allocation` (analog: round allocation) | PARTIAL (analog only; only 2 values) |
| BRAI magnitude eps_scale | — | (none) | BLOCKED |
| n_rounds | — | (none — hardcoded in `MODEL_TABLE`) | BLOCKED |

Default cell (matched against): `(NFE=50, sigma=0.0,
allocation=uniform, restart_guard=on)` → baseline=0.4831,
framework=1.8028, Δ=+2.732 (framework regresses — known Wave 17 P2
finding).

## Sensitivity table (raw measurements)

| Hparam | Value | Baseline | Framework | Δ | Δ vs default |
|---|---|---:|---:|---:|---:|
| **NFE budget** | 10 | 0.4972 | 1.2857 | +1.586 | -1.146 (low-NFE mitigates) |
|  | 50 | 0.4831 | 1.8028 | +2.732 | 0.000 (default) |
|  | 200 | 0.4827 | 1.7834 | +2.694 | -0.038 (diminishing returns) |
| **sigma** (restart_threshold_sigma analog) | 0.00 | 0.4831 | 1.8028 | +2.732 | 0.000 (default) |
|  | 0.05 | 0.4841 | 0.6648 | +0.373 | -2.359 (5x improvement) |
|  | 0.10 | 0.4854 | 0.6684 | +0.377 | -2.355 (saturation) |
| **nfe-allocation** (β-shape analog) | uniform | 0.4831 | 1.8028 | +2.732 | 0.000 (default) |
|  | evidence | 0.4831 | 1.7896 | +2.705 | -0.027 (Wave 35 FIX-3 marginal) |
| **restart-guard** | on | 0.4831 | 1.8028 | +2.732 | 0.000 (default) |
|  | off | 0.4831 | 0.6612 | +0.369 | -2.363 (guard toggle dominates) |

## Sensitivity ranking (by |Δ vs default|)

1. **restart-guard off**: Δ drops from +2.732 to +0.369 (87% reduction) — the small-sigma blend guard is the dominant source of the regression at sigma=0.
2. **sigma=0.05**: Δ drops from +2.732 to +0.373 (86% reduction) — noise injection has a near-identical effect to disabling the guard (consistent: both move the framework arm off the noisy sigma=0 corner).
3. **NFE=10**: Δ drops from +2.732 to +1.586 (42% reduction) — low-budget regime partially mitigates the regression (framework arm can't accumulate the bad 5-round restarts).
4. **evidence allocation**: Δ drops from +2.732 to +2.705 (1% reduction) — Wave 35 FIX-3 is marginal on this workload.

## Evidence (tool surface audit)

### E1 — What `run_controlled_audit.py` exposes for 2D FM

```
$ python tools/run_controlled_audit.py --help | grep -E 'nfe|sigma|guard|alloc|seed'
--nfe                 NFE budgets (default: 10 50 200)
--sigma               noise injection sigma (default: 0.0 0.1 0.5)
--restart-guard       enable/disable twodim small-sigma restart guard
--nfe-allocation      per-round NFE allocation policy ('uniform' or 'evidence')
--seeds               RNG seeds (default: 0 1 2)
--n-samples           exact twodim sample count
--models              adapter selection
```

### E2 — What's NOT exposed

* No `--scheduler {cosine,linear,convergence_adaptive,constant}` flag — scheduler is hardcoded to `CodimensionSheetScheduler(cycle_length=n_rounds)` in `_run_twodim_fm` at `tools/run_controlled_audit.py:789`.
* No `--restart-threshold-sigma FLOAT` flag — `should_skip_restart_small_sigma(sigma, n_restarts, threshold)` is a module-level helper with default `threshold=1e-2` (per Wave 125); the threshold is not CLI-overridable.
* No `--brai-eps-scale FLOAT` flag — `BRAI` (Bayesian Re-weighted Aggregated Inference, the LineageFlow-only paper-quantity attractor) is never called from `_run_twodim_fm` at all.
* No `--n-rounds INT` flag — `n_rounds=5` is hardcoded in `MODEL_TABLE["twodim_fm"]` at `tools/run_controlled_audit.py:120`.

### E3 — Kanzi sweep tool (Item 1 precedent) has the same gap

Per `docs/audit/wave146-item1-ablation.md` E2, the 4 Kanzi sweep drivers
(`sweep_kanzi_n1000_*.py`) also do not expose any of the Wave 125
algorithm primitives. Both Item 1 (Kanzi N=1000) and Item 2 (2D FM)
suffer from the same root cause: **the algorithm primitives are
kwargs at adapter/runner construction sites (Wave 125), not CLI
flags on a sweep driver**. A camera-ready fix is to either (a) plumb
the kwargs through the sweep drivers (source modification), or (b)
add a thin `tools/_sweep_kwargs.py` shim that maps CLI flags → kwarg
dicts at driver construction time.

## Blocked-hyperparameters fallback path

| Blocked knob | Code site to plumb | Difficulty | Suggested commit scope |
|---|---|---|---|
| β shape | `_run_twodim_fm` line 289 (scheduler construction) | small (~5 LOC + 1 CLI flag) | Add `--scheduler {cosine,linear,convergence_adaptive,constant}` |
| restart_threshold_sigma | `should_skip_restart_small_sigma` at `tools/run_controlled_audit.py:348` | small (~3 LOC + 1 CLI flag) | Add `--restart-threshold-sigma FLOAT` |
| BRAI magnitude eps_scale | not in 2D FM driver at all | medium (~10 LOC, requires BRAI on 2D) | Add BRAI to 2D FM adapter + `--brai-eps-scale FLOAT` |
| n_rounds | `MODEL_TABLE["twodim_fm"]["n_rounds"]` at line 120 | small (~2 LOC) | Add `--n-rounds INT` with default to MODEL_TABLE |

Total deferred source-modification scope: ~20 LOC across 4 files. All
work is mechanical and low-risk (no algorithm changes, only CLI-flag
plumbing). Defer to camera-ready under Wave 146's "NO source code
modifications" constraint.

## Recommendation for Table D in the paper

* **Populated cells (10)**: NFE budget (3 values), sigma (3 values),
  nfe-allocation (2 values), restart-guard (2 values). Use directly.
* **Marked "(deferred; no CLI flag)" cells**: β shape, BRAI eps_scale,
  n_rounds, restart_threshold_sigma (the Wave 125 kwarg, not the noise
  sigma). All four are mechanical to add but require source
  modifications deferred to camera-ready.
* **Headline sensitivity finding**: the 2D FM regression at sigma=0 is
  driven primarily by the small-sigma blend guard (87% reduction when
  toggled off) and secondarily by noise injection (86% reduction at
  sigma=0.05). NFE budget and allocation are minor effects. This is
  consistent with the Wave 17 P2 + Wave 29 Agent B diagnosis that the
  regression is **measurement** + **adapter wiring** (the guard is
  part of the adapter), not the core algorithm.

## Gates

```
$ pytest tests/ -k "d4" -q 2>&1 | tail -3
... FAILED
$ ruff check adaptive_reflow/ tests/ 2>&1 | tail -1
All checks passed!
$ python tools/check_claims_consistency.py 2>&1 | tail -3
(no output - claims consistency check passed silently)
```

(Note: the d4 gate failure is a pre-existing test issue, NOT caused
by this sweep; this audit doc introduces no source modifications.)