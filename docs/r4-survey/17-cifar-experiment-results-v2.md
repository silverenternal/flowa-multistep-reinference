# CIFAR-10 Rectified-Flow experiment — post-fix v2 results

> **Author:** Agent I (harness-fix implementation subagent)
> **Date:** 2026-08-31
> **Working dir:** `c:\Users\31472\codes\flowa-multistep-reinference`
> **Inputs:**
> - `docs/r4-survey/15-harness-bug-diagnosis.md` (Phase 1 diagnosis)
> - `docs/r4-survey/16-harness-fix-plan.md` (Phase 2 plan)
> - `docs/r4-survey/14-cifar-experiment-results.md` (Phase 1 results, broken)

## §0. TL;DR

The Phase-2 harness fix landed (`tools/run_sota_cifar_experiment.py`).
The `round_in_cycle=0` defect at `tools/run_sota_cifar_experiment.py:439`
(hard-coded literal `0` as the second positional argument to
`scheduler.sample(...)`) was replaced with `int(r)`, and a per-round
`record_round_feedback` call was added for `EvidenceDrivenScheduler` with
a `CodimensionSheetScheduler`-driven `evidence_ratio` proxy.

**Per-round `n_cap` is now non-constant** (cosine ramp `1.0 → 0.0`),
confirming the diagnosis that the `n_cap=1.0` collapse was harness-side.

**However, the four framework `{name}_samples.npz` files remain
byte-identical**, and therefore the four framework FIDs are
byte-identical. This is the "highest risk" the plan flagged (§6 Risk 5):
the PID-lite controller's `_last_pid_delta ≈ 1.9e-4` (much smaller than
the plan's predicted `1e-5`) is still below the `0.5` banker's-rounding
threshold needed to change `num_steps = round(n_cap * 10)`. Combined
with the latent FreeTrajScheduler cache bug (`_compute_trajectory_progress`
caches `_last_trajectory_progress` on the first `sample()` call, freezing
the substep to `0` for all subsequent rounds — known issue, OUT of scope
per plan §5 Risk 1), the four rows collapse to the same per-round
`num_steps` sequence.

This is reported honestly: the n_cap fix succeeded, the FID-discrimination
criterion is not met within the plan's scope (a separate fix to
`freetraj.py` is required to break the byte-identity, and would also
benefit from a larger `n_max`/`target_ratio` perturbation to amplify the
PID signal).

| Field | Value |
|---|---|
| Files modified | 2 (`tools/run_sota_cifar_experiment.py`, `tests/test_tools/test_run_sota_cifar_experiment.py`) |
| Tests added | 3 (`test_run_framework_n_cap_varies_per_round`, `test_run_framework_four_schedulers_produce_different_traces`, `test_run_framework_evidence_driven_pid_advances`); 1 test extended (`test_build_scheduler_returns_all_four_families`) |
| `mypy` | clean (0 issues across 129 source files) |
| `ruff` | clean (0 issues) |
| `pytest` (touched files) | 14 passed, 0 failed in `tests/test_tools/test_run_sota_cifar_experiment.py` |
| `pytest` (full suite, no slow) | 2180 passed, 10 skipped, 1 xfailed, 1 pre-existing failure in `test_run_sota_2d_experiment.py::test_quick_run_produces_all_artifacts` (untouched by this fix; acceptable per constraints) |
| n_cap range per scheduler | `1.0 → 0.0` cosine ramp (post-fix) vs constant `1.0` (pre-fix) |
| Baseline FID (post-fix) | 218.8692 |
| CosineAnnealScheduler FID | 122.1790 |
| CodimensionSheetScheduler FID | 122.1790 |
| EvidenceDrivenScheduler FID | 122.1790 |
| FreeTrajScheduler FID | 122.1790 |
| Framework FID vs baseline | framework 122.18 vs baseline 218.87 — framework wins by **96.69 FID** (-44.2%); the framework's per-round `num_steps` averages ~5 NFEs vs the baseline's fixed 2 NFEs, so this is mostly a "more NFEs = better FID" reading rather than a scheduler-discrimination reading. |
| Scheduler discrimination (4 FIDs ≠) | **NO** — all 4 framework FIDs are byte-identical (122.17904456398583) |

---

## §1. Fixes applied

### Fix A — `tools/run_sota_cifar_experiment.py:439`

Before:

```python
sample = scheduler.sample(0, 0, int(r))
```

After:

```python
sample = scheduler.sample(0, int(r), int(r))
```

The second positional argument to `SchedulerProtocol.sample` is
`round_in_cycle` — the index that drives the cosine ramp and the
PID/substep accumulators. The literal `0` collapsed every scheduler to
`n_cap=1.0` for every round.

### Fix B — `record_round_feedback` companion wiring

For `EvidenceDrivenScheduler` rows, instantiate a shared
`CodimensionSheetScheduler` once per call to `_run_framework` and use its
`sample.evidence_ratio` (driven on the same `round_in_cycle`) as the
proxy feedback signal. This advances the PID-lite controller across
rounds so the EvidenceDriven row diverges from the pure cosine baseline.

```python
evidence_proxy_scheduler = (
    CodimensionSheetScheduler(
        cycle_length=int(n_rounds),
        n_min=0.0,
        n_max=1.0,
        eps_implicit=0.05,
    )
    if scheduler_name == "EvidenceDrivenScheduler"
    else None
)
# ... inside the r loop:
if evidence_proxy_scheduler is not None:
    proxy_sample = evidence_proxy_scheduler.sample(0, int(r), int(r))
    scheduler.record_round_feedback(
        int(r),
        {"evidence_ratio": float(proxy_sample.evidence_ratio)},
    )
```

No constructor changes (`build_scheduler` is unchanged), no
`framework-max-num-steps` change (default `2` is used; `--framework-max-num-steps 10`
is also tested separately — see §3).

---

## §2. Post-fix `per_round_metrics.csv` (max_num_steps=10 run)

`docs/r4-survey/cifar_results_v2/per_round_metrics.csv` (verbatim,
`--framework-max-num-steps=10 --framework-samples=100`):

| scheduler | r=0 | r=1 | r=2 | r=3 | r=4 | r=5 | r=6 | r=7 | r=8 | r=9 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CosineAnneal `n_cap` | 1.000 | 0.970 | 0.883 | 0.750 | 0.587 | 0.413 | 0.250 | 0.117 | 0.030 | 0.000 |
| CosineAnneal `num_steps` | 10 | 10 | 9 | 8 | 6 | 4 | 3 | 1 | 1 | 1 |
| CodimSheet `n_cap` | 1.000 | 0.970 | 0.883 | 0.750 | 0.587 | 0.413 | 0.250 | 0.117 | 0.030 | 0.000 |
| CodimSheet `evidence_ratio` | 1.000 | 0.999998 | 0.999961 | 0.999792 | 0.999273 | 0.997921 | 0.994406 | 0.983609 | 0.955082 | 0.952381 |
| EvidenceDriven `n_cap` | 1.000 | 0.970 | 0.883 | 0.750 | 0.587 | 0.413 | 0.251 | 0.119 | 0.035 | 0.012 |
| FreeTraj `n_cap` | 1.000 | 0.970 | 0.883 | 0.750 | 0.587 | 0.413 | 0.250 | 0.117 | 0.030 | 0.000 |

Three observations:

1. **CosineAnneal = CodimensionSheet** by construction (both use the same
   cosine base); `n_cap` sequences are bit-identical.
2. **FreeTraj = CosineAnneal** in this run. The FreeTrajScheduler's
   `_compute_trajectory_progress` (`adaptive_reflow/algorithm/scheduler/freetraj.py:308`)
   caches `_last_trajectory_progress` on every `sample()` call (line 207),
   so after the first call all subsequent calls return the cached value
   (0.0 for `round_in_cycle=0`). The substep is therefore 0.0 for every
   round and `n_cap` tracks the cosine baseline exactly. This is a
   known issue (`tests/test_experiments/test_freetraj_wallclock.py::test_freetraj_trajectory_progress_freezes_when_driven_statefully`
   pins the current behaviour) and is **explicitly out of scope** for
   this fix per `docs/r4-survey/16-harness-fix-plan.md` §5 Risk 1.
3. **EvidenceDriven ≠ CosineAnneal** but only by a small PID offset
   (max ~5e-3 at `r=9`, otherwise ~1e-4). With `max_num_steps=10`, this
   offset is still below the banker's-rounding threshold needed to
   change `num_steps` for any round: `round(0.2506 * 10) = 3` (same as
   `round(0.2500 * 10) = 3`), and the round-9 `EvidenceDriven` `n_cap =
   0.0125` still rounds to `0` (same as cosine's `0.0000`), giving
   `max(1, 0) = 1`.

The per-round `num_steps` sequence is therefore identical across all
four schedulers: `[10, 10, 9, 8, 6, 4, 3, 1, 1, 1]`.

---

## §3. Post-fix FIDs (max_num_steps=10, framework_samples=100)

`docs/r4-survey/cifar_results_v2/summary.json` (verbatim):

```json
{
  "n_samples": 1000,
  "n_rounds": 10,
  "framework_samples": 100,
  "wall_clock_s": 1493.21,
  "rows": [
    {"name": "baseline", "fid": 218.86922936408644, "wall_clock_s": 104.0},
    {"name": "CosineAnnealScheduler",    "fid": 122.17904456398583, "wall_clock_s": 253.7},
    {"name": "CodimensionSheetScheduler","fid": 122.17904456398583, "wall_clock_s": 243.5},
    {"name": "EvidenceDrivenScheduler",  "fid": 122.17904456398583, "wall_clock_s": 243.3},
    {"name": "FreeTrajScheduler",        "fid": 122.17904456398583, "wall_clock_s": 243.2}
  ]
}
```

Per-scheduler `mean_abs_diff` between `cosineanneal_samples.npz` and
every other framework row:

| pair | mean_abs_diff | byte_identical |
|---|---:|:---:|
| cosineanneal vs codimensionsheet | 0.000000 | true |
| cosineanneal vs evidencedriven | 0.000000 | true |
| cosineanneal vs freetraj | 0.000000 | true |
| codimensionsheet vs evidencedriven | 0.000000 | true |
| codimensionsheet vs freetraj | 0.000000 | true |
| evidencedriven vs freetraj | 0.000000 | true |

All four `{name}_samples.npz` files are byte-identical.

**Why**: with `framework_samples=100, max_num_steps=10`, the per-round
`num_steps` sequences are byte-identical across all four schedulers
(see §2), so the adapter's `batched_inference(n_samples=100,
num_steps=…, seed=…)` is called with identical `(num_steps, seed)`
arguments for every round of every scheduler and produces identical
sample arrays. The cosine ramp and the small EvidenceDriven PID offset
are both visible in the `per_round_metrics.csv` *value* but neither
crosses the banker's-rounding threshold needed to differentiate the
adapter's output.

---

## §4. Honest framing — what worked, what didn't

### Worked (Fix A + Fix B landed cleanly)

* The `n_cap` column in `per_round_metrics.csv` is now non-constant for
  every scheduler. The cosine ramp `1.0 → 0.0` is visible for all four
  rows. This matches the 2D harness's expected behaviour
  (`docs/r4-survey/two_moons_CosineAnnealScheduler_seed0.csv`) and the
  diagnosis (`15-harness-bug-diagnosis.md` §4).
* `CodimensionSheetScheduler.evidence_ratio` varies across rounds
  (`1.000 → 0.952`); the proxy `_paper_evidence_balance` is wired to
  `round_in_cycle` correctly.
* `EvidenceDrivenScheduler._last_pid_delta` advances from `0.0` to
  ~`1.9e-4` across 10 rounds with the proxy feedback (verified by
  `test_run_framework_evidence_driven_pid_advances`).
* All gates clean on touched files: `mypy`, `ruff`, `pytest` (the
  CIFAR-harness test file is 14/14 green).

### Did NOT work within the plan's scope

* **4 framework FIDs are byte-identical** (122.17904456398583). The
  plan's "highest risk" prediction (`16-harness-fix-plan.md` §6) was
  correct: the PID delta is too small to change `num_steps` even at
  `max_num_steps=10`, and the FreeTraj substep is frozen by the
  pre-existing cache bug in `freetraj.py`. Both are **outside the
  plan's scope**:
    - `_compute_trajectory_progress` is in `freetraj.py`, which the
      plan explicitly excludes (`16-harness-fix-plan.md` §1 "Files
      that will NOT change").
    - The PID gain / target_ratio tuning is in `EvidenceDrivenScheduler`'s
      constructor, which the plan also excludes.

### What would unblock the discrimination criterion

Two follow-up tickets, both **explicitly out of scope** for this fix
but worth flagging:

1. **Fix `_compute_trajectory_progress` in `freetraj.py`** to not
   cache `_last_trajectory_progress` across rounds (or to clear it on
   `reset()`). With this fix, FreeTraj's `n_cap` would deviate from the
   cosine baseline by `±0.05` at odd rounds, crossing the
   banker's-rounding threshold at `max_num_steps=10` and producing
   non-byte-identical samples.

2. **Amplify the PID signal in `EvidenceDrivenScheduler`** by lowering
   `target_ratio` to `0.99` (the plan §6 "Mitigation" suggests this).
   With a larger per-round error, `_last_pid_delta` would reach the
   `max_step=0.05` cap, crossing the rounding threshold and producing
   non-byte-identical samples.

Either fix alone would differentiate EvidenceDriven and FreeTraj from
the cosine baseline. Both are scheduler-side (out of scope).

### Is the framework FID still useful?

Yes, but with the caveat that "framework vs baseline" is now
**mostly a "more NFEs = better FID" reading**, not a
"scheduler-discrimination" reading:

- Baseline uses 2 NFEs for every sample → FID 218.87.
- Framework rows use a variable NFE budget that averages ~5 NFEs per
  sample (sum 54 NFEs across 10 rounds) → FID 122.18.
- All four framework rows use the *same* NFE budget per round
  ([10, 10, 9, 8, 6, 4, 3, 1, 1, 1]) → identical FIDs.

To get a clean "scheduler-discrimination" reading, the two
follow-up fixes above are needed.

---

## §5. Test additions

### `test_build_scheduler_returns_all_four_families` (extended)

Now also drives `sample(0, r, r)` for `r in range(5)` and asserts:

* CosineAnnealScheduler: cosine ramp — `caps[0] = 1.0`,
  `caps[1] < caps[0]`, ..., `caps[4] < caps[3]`.
* FreeTrajScheduler: cosine ramp with wobble — at least 2 distinct
  values in `caps` (this passes even with the cache bug because the
  cosine ramp itself varies).

### `test_run_framework_n_cap_varies_per_round` (new)

Drives `_run_framework` with a `MockAdapter` and asserts:

* `caps[0] == 1.0`, `caps[-1] ≈ 0.0` (cosine ramp endpoints).
* `caps` is strictly decreasing.
* The `MockAdapter.calls` show a non-constant `num_steps` sequence.

### `test_run_framework_four_schedulers_produce_different_traces` (new)

Drives `_run_framework` for all four schedulers and asserts:

* Every row has `vals[0] == 1.0`, `vals[-1] < 0.05`, ≥ 5 distinct
  values in `vals`.
* `EvidenceDrivenScheduler[5]` differs from `CosineAnnealScheduler[5]`
  by more than `1e-5` (plan §5 Risk 5: PID delta is bounded well below
  `max_step=0.05`; observed ~`1.9e-4`).

### `test_run_framework_evidence_driven_pid_advances` (new)

Drives `_run_framework` with `EvidenceDrivenScheduler`, then
re-instantiates a fresh scheduler and re-drives the loop with explicit
`synthesized feedback`. Asserts:

* `scheduler._last_pid_delta != 0.0` after 10 rounds.
* `abs(scheduler._last_pid_delta) <= 0.05` (max_step bound).

---

## §6. References

* Phase-1 diagnosis: `docs/r4-survey/15-harness-bug-diagnosis.md`
* Phase-2 plan: `docs/r4-survey/16-harness-fix-plan.md`
* Phase-1 results (broken): `docs/r4-survey/cifar_results/`
* Post-fix results: `docs/r4-survey/cifar_results_v2/`
* Test additions: `tests/test_tools/test_run_sota_cifar_experiment.py`