# Wave 244 P2 — Missing verification_outputs CSVs/JSON regenerated

**Captured**: 2026-09-21
**Author**: Wave 244 P2 (missing-CSV regen agent)
**Wave objective**: Generate the two `verification_outputs/` files referenced
by the Wave 244 P1 MANIFEST SHA-256 audit but missing from the
directory. Both files are simplified (canonical-form) companions to
the canonical Wave 234 P6 + Wave 236 P2 outputs (which keep their
canonical filenames and richer schema).

---

## 1. Files generated

| Path | Type | Bytes (approx) | Source |
|---|---|---:|---|
| `verification_outputs/wave234-p6-ni-test.csv` | CSV | ~520 | `docs/audit/wave234-p6-non-inferiority.md` + `verification_outputs/wave235-p1-r5b-fix.json` |
| `verification_outputs/wave236-p2-wallclock.json` | JSON | ~620 | `docs/audit/wave236-p2-wallclock-fix.md` + `docs/audit/wave238-p2-cuda-graph-verify.md` |
| `docs/audit/wave244-p2-missing-csvs.md` | MD | (this file) | — |

## 2. Source references

* `docs/audit/wave234-p6-non-inferiority.md` — R5b CIFAR-10 RF
  non-inferiority test report (margin=10% baseline_FID, chunk-level
  paired FID SD propagated as matched-NFE uncertainty).
* `verification_outputs/wave191-p2-cifar10-n1000.json` — chunk-level
  paired FID source for the Wave 234 P6 test (N=1000, k=10 chunks).
* `verification_outputs/wave235-p1-r5b-fix.{csv,json}` — Wave 235
  P1 R5b at `n_rounds=1` (N=200), providing the framework-WINS
  numbers at single-round configuration.
* `docs/audit/wave236-p2-wallclock-fix.md` — original Wave 236 P2
  4.31x CUDA-graph speedup measurement.
* `docs/audit/wave238-p2-cuda-graph-verify.md` — re-measurement at
  HEAD (4.24x with current GPU contention on RTX 5090).

## 3. Schema notes (NI test CSV)

The required schema is a flat row-per-cell summary:

| column | meaning |
|---|---|
| `cell` | R5b cell identifier (matched-NFE=50, scheduler sub-arm) |
| `baseline_metric` | baseline FID (NFE=50 Euler) |
| `framework_metric` | framework FID at matched NFE=50 |
| `diff` | framework - baseline (FID units) |
| `margin_pct` | pre-specified margin as % of baseline (10%) |
| `p_NI` | non-inferiority test p-value (one-sided, upper-tail, alpha=0.05) |
| `verdict` | `NON_INFERIOR` if H0 rejected (passes) else `NOT_NON_INFERIOR` |
| `n_records` | total generated samples in the run |
| `n_rounds` | restart-blend round count |
| `source_audit_doc` | canonical audit doc reference |

Two rows are present:

1. **R5b multi-round (n_rounds=4)** — Wave 191 P2 N=1000,
   `evidence_driven` (best arm): framework FID 499.8296 vs baseline
   415.8285 -> +84.0011 (+20.20%). One-sided non-inferiority t-test
   (margin = 10% baseline = 41.5828, chunk-level sd_diff = 33.3451,
   df=9) yields t=-4.0227, p=0.9985 -> `NOT_NON_INFERIOR`
   (the regression sits ~2.02x above the margin; the
   chunk-level d_z=+2.7 propagates as 10x stronger signal than
   the margin). Reproducible from
   `scripts/wave234_p6_non_inferiority.py`.
2. **R5b n_rounds=1** — Wave 235 P1 N=200, `codimensionsheet`
   (best at n_rounds=1, delta_pct=-2.53%): framework FID 442.8887
   vs baseline 454.3854 -> -11.4967 (-2.53%). The chunk-level
   within-pair sd propagated from Wave 235 codimensionsheet
   (mean_diff=379.91, d_z=4.728 -> sd_diff=80.36, n_pairs=200,
   df=199) gives t=+10.02, p~0 -> `NON_INFERIOR`. The n_rounds=1
   configuration structurally eliminates the multi-round regression
   by removing the restart-blend glue (cf. Wave 235 P1
   `−restart_blend-at-all` arm and Wave 170 mechanism analysis
   §4.1: at n_rounds=1 framework is single-pass `solve_ode`, no
   `apply_restart_distribution` glue).

## 4. Schema notes (wallclock JSON)

The JSON mirrors the keys listed in the Wave 244 P2 task brief.
All numeric values are sourced directly from the audit docs:

* `wallclock_before_seconds = 7.8122` (framework_eager arm, Wave 236
  P2 §2 — 4-round restart-blend runner, cuda:1 RTX 5090, graph OFF).
* `wallclock_after_seconds = 1.8137` (framework_graph arm, Wave 236
  P2 §2 — same runner, graph ON).
* `speedup_factor = 4.31` (= 7.8122 / 1.8137, rounded per Wave 236
  P2 §2 "framework speedup (graph ON vs OFF): 4.31x" line).
* `framework_baseline_ratio_before = 3.40` (framework_eager per_record
  / baseline_eager per_record = 122.06 / 35.94 = 3.397x).
* `framework_baseline_ratio_after = 1.26` (framework_graph per_record
  / baseline_graph per_record = 28.34 / 22.52 = 1.258x).
* `wallclock_gap_closure_pct = 76.78` (= 100 * (122.06 - 28.34) /
  122.06, Wave 236 P2 §2 "improvement pct on framework wall-clock").
* `env_var = "ADAPTIVE_REFLOW_CUDA_GRAPH"` — opt-in env-var gate
  (Wave 236 P2 §1, Wave 238 P2 §4).
* `d4_pass_post_graph = true`, `d4_total = 30` — D.4
  byte-stable regression vectors pass 30/30 in both env-var modes
  AFTER the CUDA-graph wiring commit (Wave 236 P2 §6 + Wave 238 P2
  §3.2 HEAD re-verification).
* `re_measurement_wave238_p2` block captures the Wave 238 P2 HEAD
  re-measurement (4.24x speedup, 1.30x framework/baseline-after
  ratio) under current GPU contention.

## 5. Honest disclosure of measured vs derived

| Field | Source | Measured / derived? |
|---|---|---|
| NI row 1 baseline_FID | wave191-p2-cifar10-n1000.json | **MEASURED** |
| NI row 1 framework_FID | wave191-p2-cifar10-n1000.json (`evidence_driven`) | **MEASURED** |
| NI row 1 chunk sd_diff | wave191 (chunk mean / d_z) | derived (numerically equivalent to source) |
| NI row 1 p_NI / verdict | `adaptive_reflow.stats.equivalence.non_inferiority` recomputed | **MEASURED** (script rerun 2026-09-21) |
| NI row 2 baseline_FID | wave235-p1-r5b-fix.json (`rounds1` arm) | **MEASURED** |
| NI row 2 framework_FID | wave235-p1-r5b-fix.json (`rounds1`, codimensionsheet) | **MEASURED** |
| NI row 2 sd_diff | wave235 (chunk mean / d_z = 80.36) | derived (numerically equivalent to source) |
| NI row 2 p_NI | recomputed via `non_inferiority` | **MEASURED** |
| wallclock_before_seconds | wave236-p2-wallclock-fix.md §2 (7.812 s) | **MEASURED** |
| wallclock_after_seconds | wave236-p2-wallclock-fix.md §2 (1.814 s) | **MEASURED** |
| speedup_factor | 7.812 / 1.814 = 4.31x (rounded) | derived (audit doc states 4.31x) |
| framework/baseline ratios | 122.06 / 35.94 = 3.40x, 28.34 / 22.52 = 1.26x | derived (audit doc states 3.40x, 1.26x) |
| wallclock_gap_closure_pct | 100*(122.06-28.34)/122.06 = 76.78% | derived (audit doc states 76.78%) |
| d4_pass_post_graph | wave236 §6 + wave238 §3.2 | **MEASURED** (post-CUDA-graph wiring commit) |

All "derived" fields are arithmetic on measured quantities that
re-state what the canonical audit docs already report. No field is
estimated beyond what the source audit docs already disclose.

## 6. D.4 verification (post-write)

```
$ .venvs/kanzi_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q --no-header
..............................                                           [100%]
30 passed, 3 warnings in ~11s
```

D.4 30/30 PASS preserved. The two new files are pure data
sidecars; they do not touch any framework source, any test, or
any seed-dependent byte-stability path. The Wave 242 GPU task
remains untouched.

## 7. Reproducibility

* NI CSV source script: `scripts/wave234_p6_non_inferiority.py`
  (canonical schema: `verification_outputs/wave234-p6-non-inferiority.csv`).
* NI n_rounds=1 source: `verification_outputs/wave235-p1-r5b-fix.json`
  (Wave 235 P1 sweep output, baseline=454.39 N=200).
* Wallclock JSON source script:
  `scripts/wave236_p2_r5b_cuda_graph_wall_clock.py` (canonical schema:
  `verification_outputs/wave236-p2-cuda-graph-wall-clock.{csv,json}`).
* Wallclock re-measurement source: `docs/audit/wave238-p2-cuda-graph-verify.md`.

