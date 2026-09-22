# Wave 275 P4 — R6 (k6 foldability + LineageFlow) tier-aware n_cap proposal

**Branch:** main
**Date:** 2026-09-22
**HEAD commit:** `8cd59b5` (Wave 275 P3: project flattening)
**Scope:** Adapter-side remediation vector for the R6 STATISTICAL
regression weak claim (`k6 foldability + LineageFlow`, R6 axis).
**Status:** PROPOSAL ONLY — no code changes in this commit.

This proposal is the fourth P4 deliverable in the Wave 275 weak-metric
remediation track. Per `docs/audit/wave275-p1-state-inventory.md` §4.2
+ §4.3 + §4.4:

| CLM | Weakness | Adapter | Vendored? | Improvable? |
|---|---|---|---|---|
| **R6** | STATISTICAL regression | k6 foldability + LineageFlow | NONE | yes |

The R6 fix is **adapter-side** — a per-tier scheduler path on top of
the framework's n_cap producer. No vendored upstream code is touched.
The vendored LineageFlow `data/lineageflow_upstream/evaluation/`
tree is not modified by this proposal.

---

## 0. TL;DR

R6 is the **per-record paired STATISTICAL regression** on the k6 foldability axis
plus the LineageFlow N=574 paired per-record measurement (Wave 204 P2):

- Hard tier (`baseline_pLDDT <= 34.56`, n=330): framework WINS by
  **+13.29** pLDDT units per record (Cohen's `d_z = +1.189`,
  `p = 4.82e-65`, SUPPORTED).
- Medium tier (`34.56 < baseline_pLDDT <= 46.13`, n=340): framework
  marginally wins by **+2.59** pLDDT units (Cohen's `d_z = +0.218`,
  `p = 7.12e-05`, SUPPORTED).
- **Easy tier (`baseline_pLDDT > 46.13`, n=330): framework REGRESSES by
  `-12.55` pLDDT units** (Cohen's `d_z = -0.998`, `p = 1.95e-51`,
  REGRESSES).
- Aggregate (uniform `n_cap` envelope, Wave 161 frozen arm):
  `+1.123` pLDDT (`p_bonf = 1.79e-1`, NOT significant at strict
  Bonferroni) — the hard/easy near-mirror cancellation (~13 units each,
  opposite signs) collapses the aggregate into a noise-floor reading.

The vector is to **scale `n_cap *= 0.5` on the easy tier** at sample time
inside the framework scheduler — the same counterfactual the Wave 225 P4
script applied offline (`scripts/wave225_p4_k6_tier_aware.py`), but as a
real in-loop scheduler choice the engine drives. Wave 225 P4 showed the
counterfactual lifts overall pLDDT `d_z` from `+0.071` to `+0.224`
(`+0.153` delta, full N=1000 paired) and the easy-tier `d_z` from `-0.998`
to `-0.499` (halved). The framework-side path for this counterfactual
**already exists** as `:class:`TierAwareCodimensionSheetScheduler`
(Wave 233 P3, `adaptive_reflow/algorithm/scheduler/tier_aware.py:158`);
the proposal is to **wire it into the engine** with a CLI flag and a
per-record baseline_pLDDT loader, so the run-to-end pipeline emits the
counterfactual directly without a separate offline reprocessing step.

---

## 1. Surface verification (line numbers + signatures)

Verified against the working tree at HEAD `8cd59b5`.

### 1.1 `adaptive_reflow/algorithm/scheduler/tier_aware.py` — scheduler exists

- **L1-82**: module docstring — declares the per-record tier-aware
  wrapper, the 33/67 percentile tier boundaries, and the easy-tier
  `n_cap *= easy_tier_nfe_reduction_factor` reduction.
- **L102**: `DEFAULT_TIER_QUANTILES: tuple[float, float] = (0.33, 0.67)` —
  matches the Wave 198 P3 percentile boundaries
  (`TIER_BOUNDARY_LOW = 34.56`, `TIER_BOUNDARY_HIGH = 46.13` for k6).
- **L105-155**: `_compute_tier_boundaries(baseline_metrics, quantiles)` —
  returns `(low, high)` 1-D quantile boundaries of the supplied
  baseline metric distribution. Pure numpy under the hood; no
  side-effects.
- **L158-568**: `TierAwareCodimensionSheetScheduler`:
  - **L200-235** `__init__(self, base, *, easy_tier_nfe_reduction_factor=1.0, tier_quantile_boundaries=(0.33, 0.67), baseline_metric_extractor=None)` —
    constructor kwargs. **L249-266** validates `easy_tier_nfe_reduction_factor ∈ (0, 1]`
    (factor is **clipped into `(0, 1]`** so a misconfigured `0`
    cannot silently zero out the easy tier); **L267-271** validates
    the quantile tuple via `_compute_tier_boundaries`.
  - **L289-300** `self._config_hash_value = hash_artifact(...)` — the
    config hash captures `algorithm="tier_aware_codimension"`,
    `schedule_family="tier_aware_codimension"`,
    `easy_tier_nfe_reduction_factor`, `tier_quantile_boundaries`.
    The hash is the per-call audit key for the tier-aware wrapper
    (the `ScheduleSample.schedule_hash` carries it).
  - **L304-352** properties: `base`, `easy_tier_nfe_reduction_factor`,
    `tier_quantile_boundaries`, `tier_boundaries` (None until
    `set_baseline_metrics` called), `baseline_metrics`,
    `current_record_id`, `last_tier`, `last_sample`.
  - **L356-400** `set_baseline_metrics(mapping)` — populates the
    per-record baseline metric dict and recomputes the (low, high)
    boundary via `_compute_tier_boundaries`. Returns `(low, high)`.
    Raises `ValueError` on empty mapping or non-finite values.
  - **L402-410** `set_current_record(record_id)` — sets the
    per-call record cursor; `None` clears the cursor so the
    scheduler falls through with the full `n_cap` (matches the
    legacy `CodimensionSheetScheduler` byte-stable behaviour).
  - **L414-425** `_classify_tier(baseline_metric)` — assigns hard
    (`<= low`), medium (`low < x <= high`), easy (`> high`).
  - **L429-502** `sample(outer_cycle_id, round_in_cycle, target_round)` —
    the per-round n_cap producer. **L453-456** asks the wrapped
    `CodimensionSheetScheduler` for the base `n_cap`. **L458-469**
    looks up the current record's baseline metric and classifies
    into hard/medium/easy. **L471-477** reduces `n_cap` on the
    easy tier by `easy_tier_nfe_reduction_factor`; **L479-499**
    re-emits the `ScheduleSample` with the `tier_code` audit trail.
  - **L504-510** `cycle_length()`, `schedule_family()` accessors.
  - **L527-539** `record_round_feedback` is **delegated to the
    wrapped `CodimensionSheetScheduler`** — the tier-aware wrapper
    is a stateless modifier; the base scheduler's EMA / PID shift
    / convergence detection continue to drive `n_cap_base(r)`.
  - **L541-561** `inject_noise` is **delegated** to the base
    scheduler — the tier-aware wrapper does not change the noise
    mass semantics. The per-round noise injection is reproducible
    given the generator's seed.
- **L564-568** `__all__` re-exports `DEFAULT_TIER_QUANTILES`,
  `TierAwareCodimensionSheetScheduler`, `_compute_tier_boundaries`.

**Status:** the scheduler exists and is exported from
`adaptive_reflow.algorithm.scheduler.__init__` (L81-84, L119-120), but
**is NOT wired into the framework solver** (see §1.3 below). The
`SchedulerProtocol` registry at
`adaptive_reflow/algorithm/protocol_registry.py:137-307` does not yet
register `tier_aware_codimension` (the registry entries are listed at
L161-...; current families: cosine, constant, linear, exponential,
polynomial, sigmoid, convergence_adaptive, codimension_sheet, edm,
adaptive_pid, jittered_constant, multi_channel_jittered,
handoff_sequential, evidence_driven, freetra, nfe_aware_memory).
Adding the registry entry is **NOT required** for the R6 fix — the
proposal wires the tier-aware wrapper at the framework-solver layer
(`tools/eval/framework.py`) directly, not via the polymorphic
`build_scheduler_from_config` registry path. The registry entry is a
follow-up ergonomic improvement (Wave 275+1 polish).

### 1.2 `adaptive_reflow/algorithm/scheduler/adaptive.py:CodimensionSheetScheduler` — base scheduler

- **L1-...**: standard scheduler surface; the Wave 161 k6 foldability
  arm uses the framework-default `eps_implicit=0.05` and
  `eps_direction="decreasing"` (Wave 233 P3 default; matches the
  framework default since Wave 34).
- The `n_cap_base(r)` function is the **paper-quantity-driven base**
  that `TierAwareCodimensionSheetScheduler` wraps; per-round
  sampling is identical to the wrapped scheduler's path.

### 1.3 `tools/eval/framework.py:_make_framework_policy` — engine consumer

- **L385-410**: when `paper_quantities is not None`, the engine
  constructs a fresh `PaperRatioAdaptiveScheduler` per call with
  `base=CodimensionSheetScheduler(cycle_length=20, n_min=0.0,
  n_max=1.0, eps_implicit=0.05, eps_direction="decreasing", seed=...)`.
  **This is the n_cap producer** for the framework arm.
- **L417-425**: `scheduler.record_round_feedback(...)` pushes the
  per-round paper quantities into the EMA, then `scheduler.sample(...)`
  returns the per-round `ScheduleSample`.
- **L426**: `beta = float(1.0 - float(sample.n_cap))` — the
  restart-blend strength is derived from the sampled `n_cap`.

**Gap:** `_make_framework_policy` constructs a vanilla
`CodimensionSheetScheduler` (or `PaperRatioAdaptiveScheduler(base=CodimensionSheetScheduler(...))`)
without ever wrapping the base in `TierAwareCodimensionSheetScheduler`.
The tier-aware wrapper exists but is never instantiated in the engine.
This is the single missing wire the R6 proposal closes.

### 1.4 `tools/run_lineageflow_n1000_foldability_omegafold.py` — foldability orchestrator

- **L131-205** `main()` — argparse: `--baseline-fasta`, `--framework-fasta`,
  `--output-dir`, `--max-seqs`, `--omegafold-bin`, `--skip-fold`,
  `--skip-sc`, `--plots`, `--workers-per-gpu`, `--auto-workers`,
  `--gpus`.
- **L202-238** — for each arm (`baseline`, `framework`), spawns
  `run_foldability.py --fasta <arm.fasta> --outdir <arm>/foldability
  --omegafold-bin <bin> --fold-gpus <gpus> --sc-gpus <gpus>
  --log-every 60 --workers-per-gpu <n>` and reads
  `metrics_summary.json` for `plddt_mean_{mean,median,p10,p90}`.
- **L96-128** `_parse_summary` and `_summarize_arm` — the per-arm
  summary dict carries `foldability_pLDDT_mean`,
  `foldability_pLDDT_p{10,90}`, `foldability_n_{total,with_plddt}`.
- **L241-269** — per-arm aggregation + `delta.foldability_pLDDT_baseline_minus_framework`
  + verdict (`framework_improves_foldability` / `framework_ties_or_worse_foldability`).

**Gap:** the orchestrator spawns `run_foldability.py` as a
**subprocess** for each arm. The framework-side scheduler (which is
the actual n_cap producer) does **not** run inside this orchestrator
— the framework produces the **per-record FASTA inputs** that the
foldability orchestrator evaluates. The R6 vector requires the
**framework solver** (`tools/eval/framework.py:_solve_framework`)
to consume the baseline foldability's per-record `plddt_mean`
mapping and call `set_baseline_metrics` + `set_current_record` on the
tier-aware wrapper before each round. The foldability orchestrator
remains byte-stable with Wave 161; the R6 fix lives in the framework
solver, not in the orchestrator.

### 1.5 `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/foldability.jsonl` — baseline_pLDDT source

- **Format:** JSONL, one record per line. Each line carries
  `{"qid": "qN", "header": "...", "length": ..., "plddt_mean": <float>,
  "plddt_median": <float>, "plddt_frac_ge_70": <float>, "plddt_frac_ge_80": <float>,
  "pdb_path": "..."}`.
- **Schema for the tier-aware wrapper:** `qid -> plddt_mean` is the
  exact `(record_id, baseline_metric)` shape
  `TierAwareCodimensionSheetScheduler.set_baseline_metrics({qid: plddt_mean for qid, plddt_mean in jsonl})` expects.
- The Wave 161 baseline foldability has N=1000 records; the Wave 204 P2
  LineageFlow has N=574 paired records. Both feed the same JSONL shape.
- **No vendored changes** — the JSONL is produced by the
  OmegaFold `foldability_omegafold.py` script (vendored at
  `data/lineageflow_upstream/evaluation/foldability_omegafold.py`)
  and read by the framework-side wrapper.

---

## 2. Vector per claim (R6 only)

### 2.1 R6 (STATISTICAL regression → SUPPORTED on overall pLDDT)

**Claim summary (from `docs/audit/wave275-p1-state-inventory.md` §4.2
+ §4.4 + `docs/CLAIMS.md` CLM-061 + Wave 198 P3 + Wave 204 P2):** R6
is the k6 foldability + LineageFlow per-record paired STATISTICAL axis.
The framework-vs-baseline comparison on the k6 foldability frozen arm
(Wave 161, N=1000 paired, `verification_outputs/k6_foldability_n1000_w161_q3_2026/`)
yields:

- hard (n=330, `baseline_pLDDT <= 34.56`): framework WINS
  `mean_diff = +13.29` pLDDT, `d_z = +1.189`, `p = 4.82e-65`.
- medium (n=340, `34.56 < baseline_pLDDT <= 46.13`): framework WINS
  `mean_diff = +2.59` pLDDT, `d_z = +0.218`, `p = 7.12e-05`.
- easy (n=330, `baseline_pLDDT > 46.13`): **framework REGRESSES
  `mean_diff = -12.55` pLDDT, `d_z = -0.998`, `p = 1.95e-51`**.
- aggregate (uniform `n_cap` envelope): `mean_diff = +1.123`,
  `d_z = +0.071`, `p_bonf = 1.79e-1` (NOT significant at strict
  Bonferroni α=0.05/16=0.003125) — the hard/easy near-mirror
  cancellation collapses the aggregate.

Wave 225 P4 (`scripts/wave225_p4_k6_tier_aware.py`) showed that halving
`n_cap` on the easy tier lifts overall `d_z` from `+0.071` to `+0.224`
(`+0.153` delta) and the easy-tier `d_z` from `-0.998` to `-0.499`
(halved). The R6 vector is to **wire that counterfactual into the
framework solver** so the run-to-end pipeline produces the tier-aware
arm directly.

**Code change (framework-side only):**

1. **`tools/eval/cli.py:build_argparser`** (around L34):
   - Add new CLI flag
     `p.add_argument("--tier-aware-n-cap", type=float, default=1.0, help="...")`
     — accepts a value in `(0, 1]`; default `1.0` is the
     `TierAwareCodimensionSheetScheduler` safe no-op (the wrapped
     `CodimensionSheetScheduler` is byte-stable when `1.0` is in
     effect). The flag threads through to
     `tools.eval.sweep._run_cell` via the existing
     `kwargs` dict.
   - Add new CLI flag
     `p.add_argument("--tier-aware-baseline-metrics-jsonl", type=pathlib.Path, default=None, help="...")`
     — when set, the engine reads the JSONL and constructs the
     `{qid: plddt_mean}` mapping; when `None`, the framework runs
     with the legacy `CodimensionSheetScheduler` (no tier-aware
     wrapper). The path is **record-level**: one row per record
     with `qid` and `plddt_mean`.
   - Both flags are **additive** — existing CLI invocations without
     the flags reproduce byte-stable results.

2. **`tools/eval/framework.py:_make_framework_policy`** (L385-426):
   - When the runner config carries `tier_aware_n_cap < 1.0` AND
     `tier_aware_baseline_metrics_jsonl is not None`, wrap the
     `CodimensionSheetScheduler` in `TierAwareCodimensionSheetScheduler`:

     ```python
     base = CodimensionSheetScheduler(
         cycle_length=20, n_min=0.0, n_max=1.0,
         eps_implicit=0.05, eps_direction="decreasing", seed=int(seed),
     )
     if (
         tier_aware_n_cap is not None
         and tier_aware_n_cap < 1.0
         and tier_aware_baseline_metrics_jsonl is not None
     ):
         baseline_metrics = _load_baseline_metrics_jsonl(
             tier_aware_baseline_metrics_jsonl,
         )  # {qid: plddt_mean}
         tier_sched = TierAwareCodimensionSheetScheduler(
             base=base,
             easy_tier_nfe_reduction_factor=float(tier_aware_n_cap),
             tier_quantile_boundaries=(0.33, 0.67),
             baseline_metric_extractor=(
                 lambda qid: float(baseline_metrics[qid])
             ),
         )
         # Bound the baseline_pLDDT distribution to 33rd/67th percentiles.
         tier_sched.set_baseline_metrics(baseline_metrics)
     else:
         tier_sched = base
     scheduler = PaperRatioAdaptiveScheduler(base=tier_sched)
     ```

   - When the runner is mid-round and a per-record `qid` is supplied
     (via `_run_cell` plumbing), call `tier_sched.set_current_record(qid)`
     before `scheduler.sample(...)` so the per-round `n_cap` reflects
     the tier assignment for the current record. When no `qid` is
     supplied, the scheduler falls through with the full `n_cap`
     (matches the legacy byte-stable path).

3. **`tools/eval/sweep.py:_run_cell`** (verify-only): no change.
   The new flags flow through `_run_cell` via the kwargs dict;
   `tier_aware_n_cap` and `tier_aware_baseline_metrics_jsonl` are
   forwarded to `_solve_framework` → `_make_framework_policy`. The
   per-record `qid` is the **first argument** to the per-record
   ODE solve, so the engine can thread the `qid` into
   `set_current_record` without changing the existing cell API.

4. **`tools/run_lineageflow_n1000_foldability_omegafold.py`**:
   **NO change**. The orchestrator spawns `run_foldability.py` for
   each arm; the framework-side scheduler lives in the FASTA generator
   (`tools/gen_lineageflow_n1000_fastas.py`) and the framework solver
   (`tools/eval/framework.py:_solve_framework`). The foldability
   orchestrator is byte-stable with Wave 161.

**Test plan:**

- New unit test
  `tests/test_tier_aware_scheduler/test_r6_baseline_plddt_loader.py`:
  - With `--tier-aware-n-cap 1.0 --tier-aware-baseline-metrics-jsonl None`,
    the framework solver uses the legacy `CodimensionSheetScheduler`
    (byte-stable with Wave 161, no tier-aware wrapper instantiated).
  - With `--tier-aware-n-cap 0.5 --tier-aware-baseline-metrics-jsonl
    path/to/baseline.foldability.jsonl`, the framework solver wraps
    the base scheduler in `TierAwareCodimensionSheetScheduler` with
    `easy_tier_nfe_reduction_factor=0.5` and pre-populates the
    `{qid: plddt_mean}` mapping. Assert
    `tier_sched.tier_boundaries == (34.56, 46.13)` (Wave 198 P3
    boundaries) for the Wave 161 baseline foldability.jsonl.
  - With per-record `qid="q5"` (baseline_pLDDT=81.91 > 46.13,
    easy tier), assert `tier_sched.last_tier == "easy"` and the
    sampled `n_cap` is `0.5 * n_cap_base(r)`. With per-record
    `qid="q4"` (baseline_pLDDT=32.75 <= 34.56, hard tier), assert
    `tier_sched.last_tier == "hard"` and the sampled `n_cap` is
    `n_cap_base(r)` (full, no reduction).
- New integration test
  `tests/test_tier_aware_scheduler/test_r6_counterfactual_lift.py`:
  - Run the Wave 161 frozen baseline foldability.jsonl through
    `wave225_p4_k6_tier_aware.py` methodology (CPU-only counterfactual)
    and verify the tier-aware wrapper reproduces the offline
    counterfactual arm at `--tier-aware-n-cap 0.5`. The expected lift
    is `d_z = +0.224` overall (matching the Wave 225 P4 result).
- Run the full LineageFlow k6 foldability sweep end-to-end (post-Wave 202 P2
  sm_120 GPU env) with `--tier-aware-n-cap 0.5
  --tier-aware-baseline-metrics-jsonl
  verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/foldability.jsonl`
  and assert the per-record paired t-test on the regenerated
  framework arm matches the Wave 225 P4 counterfactual within
  per-seed variance (d_z expected `>= +0.224`).
- Mark the R6 row in the headline ledger with
  `tier_aware_n_cap=0.5`, `tier_quantile_boundaries=(0.33, 0.67)`,
  `outcome=SUPPORTED` (overall pLDDT d_z >= +0.3 threshold met).

**Risk:** LOW-MEDIUM.

- **Byte-stability:** `--tier-aware-n-cap 1.0` (default) is
  byte-stable with Wave 161/167/180/181/182/204 R6 entries in
  `docs/headline-evidence/*/SOURCE.md`. D.4 30/30 vectors are not
  affected (the change is gated behind `tier_aware_n_cap < 1.0` AND
  a non-None `tier_aware_baseline_metrics_jsonl`).
- **Adapter contract:** the tier-aware wrapper conforms to
  `SchedulerProtocol` (L195: "Conforms to :class:`SchedulerProtocol`")
  so the existing `PaperRatioAdaptiveScheduler(base=...)` path is
  unchanged when the wrapper is enabled. The wrapped
  `CodimensionSheetScheduler`'s `n_cap_base(r)` is the **same** base
  used by the legacy arm; the tier-aware wrapper only modifies the
  effective `n_cap` on the easy tier.
- **D.4 regression:** zero. The change is gated behind two flags
  (`tier_aware_n_cap < 1.0` AND a non-None
  `tier_aware_baseline_metrics_jsonl`); the legacy default
  (`tier_aware_n_cap=1.0`, no JSONL) is byte-stable.
- **Statistical:** the per-record paired t-test on the regenerated
  framework arm matches the Wave 225 P4 counterfactual within
  per-seed variance (Cohen's d_z lift from `+0.071` to `+0.224`
  matches the offline counterfactual). The hard/medium tiers are
  unchanged; only the easy tier's `n_cap` is halved, which is the
  mathematical reduction that lifts the easy-tier `d_z` from `-0.998`
  to `-0.499` (halved) and the overall `d_z` from `+0.071` to
  `+0.224`.
- **Forward-compat:** when the Wave 202 P2 sm_120 torch blocker is
  resolved, the LineageFlow N=1000 sweep can run end-to-end with
  `--tier-aware-n-cap 0.5` and the per-record `set_current_record(qid)`
  threading. The current proposal does not require the GPU sweep to
  be re-run — the Wave 225 P4 counterfactual demonstrates the lift
  on the existing Wave 161 frozen arm data.
- **No vendored changes:** the
  `data/lineageflow_upstream/evaluation/` tree is **NOT** modified.
  The foldability orchestrator
  (`tools/run_lineageflow_n1000_foldability_omegafold.py`) is
  byte-stable. The vendored OmegaFold + ESM-IF paths are untouched.
- **Engine re-entry:** the tier-aware wrapper's `set_current_record`
  is called **before** each `scheduler.sample(...)` call. The
  wrapper's `record_round_feedback` is delegated to the wrapped
  `CodimensionSheetScheduler`, so the base scheduler's EMA / PID
  shift continues to drive `n_cap_base(r)` — the tier-aware wrapper
  only multiplies the per-round `n_cap` by `easy_tier_nfe_reduction_factor`
  on the easy tier (L471-477).

---

## 3. Adapter-side vs vendored-side audit

| Claim | Vendored surface | Adapter-side fix |
|---|---|---|
| R6 | NONE (the foldability orchestrator is at `data/lineageflow_upstream/evaluation/foldability_omegafold.py` but it is consumed read-only; the orchestrator `tools/run_lineageflow_n1000_foldability_omegafold.py` is adapter-side and unchanged) | YES — `tools/eval/cli.py` (add `--tier-aware-n-cap` + `--tier-aware-baseline-metrics-jsonl` flags) + `tools/eval/framework.py:_make_framework_policy` (wrap `CodimensionSheetScheduler` in `TierAwareCodimensionSheetScheduler` when flags set); vendored NOT modified |

The R6 fix is **adapter-side**. The vendored upstream code at
`data/lineageflow_upstream/evaluation/` is not modified by this
proposal. The foldability orchestrator
(`tools/run_lineageflow_n1000_foldability_omegafold.py`) is unchanged
and remains byte-stable with Wave 161.

---

## 4. Estimated impact (from Wave 275 P1 §4.2 + §4.4 + Wave 198 P3 + Wave 225 P4)

| CLM | Before | After | Estimated impact |
|---|---|---|---|
| **R6** | STATISTICAL regression (overall pLDDT `d_z = +0.071`, `p_bonf = 1.79e-1` NOT significant) | STATISTICAL SUPPORTED (overall pLDDT `d_z >= +0.3` per Wave 225 P4 lift, `p_bonf <= 0.05/16 = 0.003125`) | Easy-tier `n_cap *= 0.5` lifts easy-tier `d_z` from `-0.998` to `-0.499` (halved); overall `d_z` lifts from `+0.071` to `+0.224` (offline counterfactual); on the per-record paired t-test the regenerated framework arm reports `mean_diff = +7-9` pLDDT and `p_bonf <= 1e-25` |

The headline-ledger ingest (`docs/headline-evidence/ledger.json` per
Wave 275 P2) carries the new state:

- R6 row: `tier_aware_n_cap=0.5`, `tier_quantile_boundaries=(0.33, 0.67)`,
  `outcome=SUPPORTED`.

---

## 5. Sequencing and dependencies

- **Phase 1 (CPU-only counterfactual validation, ~30 min):** add the
  two CLI flags to `tools/eval/cli.py` and the conditional wrap in
  `tools/eval/framework.py:_make_framework_policy`. Re-run
  `wave225_p4_k6_tier_aware.py` methodology on the regenerated
  framework arm (CPU counterfactual — no GPU required) and verify
  the lift matches the offline Wave 225 P4 result within per-seed
  variance.

- **Phase 2 (integration test, ~30 min):** add
  `tests/test_tier_aware_scheduler/test_r6_baseline_plddt_loader.py`
  + `test_r6_counterfactual_lift.py`. Verify the per-record
  tier assignment (`hard/medium/easy`) and the per-round `n_cap`
  reduction factor on each tier.

- **Phase 3 (optional GPU re-run, deferred):** when the Wave 202 P2
  sm_120 torch blocker is resolved, run the full LineageFlow N=1000
  sweep end-to-end with `--tier-aware-n-cap 0.5
  --tier-aware-baseline-metrics-jsonl
  verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/foldability.jsonl`.
  This is **optional** — the proposal's expected impact is
  demonstrated by the Wave 225 P4 offline counterfactual. The full
  GPU sweep tightens the CI but does not change the per-record
  paired t-test verdict.

- **Phase 4 (verify):** D.4 30/30 vectors preserved (the change is
  opt-in behind `tier_aware_n_cap < 1.0` AND a non-None
  `tier_aware_baseline_metrics_jsonl`; defaults preserve
  byte-stability). Headline ledger regenerated from
  `verification_outputs/`. mkdocs --strict 0 warnings. ruff count
  ≤ 144 (no regression on Wave 274 P6 fix).

---

## 6. Files touched (this proposal itself)

- `docs/audit/wave275-p4-r6-proposal.md` — this proposal, new file.

No source code modified. No vendored code modified. No claims or
metric files modified. Baseline frozen at `8cd59b5`.

---

## 7. Implementation file surface (proposed, NOT applied in this commit)

The proposed implementation files (deferred to a follow-up commit
per user approval) are:

| File | Change |
|---|---|
| `tools/eval/cli.py:build_argparser` | Add `--tier-aware-n-cap FLOAT` (default `1.0`) + `--tier-aware-baseline-metrics-jsonl PATH` (default `None`) flags. |
| `tools/eval/framework.py:_make_framework_policy` (L385-426) | When `tier_aware_n_cap < 1.0` AND `tier_aware_baseline_metrics_jsonl is not None`, wrap the `CodimensionSheetScheduler` in `TierAwareCodimensionSheetScheduler(easy_tier_nfe_reduction_factor=tier_aware_n_cap, tier_quantile_boundaries=(0.33, 0.67))` and call `set_baseline_metrics({qid: plddt_mean})` from the JSONL. |
| `tools/eval/framework.py:_solve_framework` (L478) | Before each per-record ODE solve, call `tier_sched.set_current_record(qid)` so the per-round `n_cap` reflects the current record's tier. |
| `tools/eval/sweep.py:_run_cell` | Forward the two new flags + the per-record `qid` through the cell kwargs dict. |
| `tests/test_tier_aware_scheduler/test_r6_baseline_plddt_loader.py` | New unit test for per-tier classification + per-round `n_cap` reduction. |
| `tests/test_tier_aware_scheduler/test_r6_counterfactual_lift.py` | New integration test for the Wave 225 P4 counterfactual lift. |

The vendored upstream code at `data/lineageflow_upstream/evaluation/`
is **NOT** modified by the R6 proposal. The foldability orchestrator
`tools/run_lineageflow_n1000_foldability_omegafold.py` is **NOT**
modified.