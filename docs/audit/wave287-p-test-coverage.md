# Wave 287 P -- Paper-grounded Scheduler Test Coverage

**Date:** 2026-09-23
**Branch:** main
**Scope:** add edge-case test coverage for the seven paper-grounded
controllers audited in ``docs/audit/wave287-p-scheduler-codepath-audit.md``.

## Summary

| Metric | Value |
|---|---|
| New test file | ``tests/test_paper_grounded_schedulers.py`` |
| New test classes | 8 (one per scheduler + 1 determinism class) |
| New tests added | 65 (all PASS) |
| Test classes per scheduler | 1:1 (every paper-grounded scheduler has a dedicated class) |
| Invariants verified | D.4 (30/30 PASS), claims consistency (no drift), ruff (0 findings) |

## Test classes

| Class | Scheduler | File:line (audit) |
|---|---|---|
| ``TestCodimensionSheetScheduler`` | ``CodimensionSheetScheduler`` | ``adaptive_reflow/algorithm/scheduler/adaptive.py:1004`` |
| ``TestPaperRatioAdaptiveScheduler`` | ``PaperRatioAdaptiveScheduler`` | ``adaptive_reflow/algorithm/scheduler/adaptive.py:2035`` |
| ``TestConvergenceAdaptiveScheduler`` | ``ConvergenceAdaptiveScheduler`` | ``adaptive_reflow/algorithm/scheduler/adaptive.py:117`` |
| ``TestEvidenceDrivenScheduler`` | ``EvidenceDrivenScheduler`` | ``adaptive_reflow/algorithm/scheduler/evidence_driven.py:248`` |
| ``TestNFEAwareMemoryScheduler`` | ``NFEAwareMemoryScheduler`` | ``adaptive_reflow/algorithm/scheduler/nfe_aware.py:110`` |
| ``TestFreeTrajScheduler`` | ``FreeTrajScheduler`` | ``adaptive_reflow/algorithm/scheduler/freetraj.py:63`` |
| ``TestTierAwareCodimensionSheetScheduler`` | ``TierAwareCodimensionSheetScheduler`` | ``adaptive_reflow/algorithm/scheduler/tier_aware.py:158`` |
| ``TestSchedulerDeterminism`` | (all 6 deterministic families) | cross-cutting |

## Edge case matrix

Edge cases covered per scheduler (each row is a test):

### ``CodimensionSheetScheduler`` (10 edge cases)

| # | Edge case | Expected outcome |
|---|---|---|
| 1 | ``A_g = 0`` | no raise; ``n_cap in [0, 1]`` |
| 2 | ``A_g = 1e-12`` | no raise; ``n_cap in [0, 1]`` |
| 3 | ``A_g = 1e12`` | no raise; ``n_cap ≈ 1`` |
| 4 | ``B_g = 0`` | no raise; ``n_cap ≈ 1`` |
| 5 | ``e_rho = 0`` | no raise; noise injection finite |
| 6 | ``e_rho < 0`` | no raise; noise injection finite |
| 7 | All-4-zero paper quantities | falls back to heuristic; ``n_cap in [0, 1]`` |
| 8 | ``n_min == n_max`` | collapses to constant ``n_cap = n_min`` |
| 9 | ``n_min > n_max`` | silent clip; ``n_cap in [0, 1]`` (current contract) |
| 10 | ``profile_residual_fn = None`` | audit = ``codimension_framework_heuristic``; legacy fallback |

### ``PaperRatioAdaptiveScheduler`` (9 edge cases)

| # | Edge case | Expected outcome |
|---|---|---|
| 1 | ``paper_quantities = None`` | ``shift == 0``; no shift update |
| 2 | ``paper_quantities = {}`` | ``shift == 0``; same as ``None`` |
| 3 | ``paper_quantities["sheet_A"] = 0`` | no shift change; bounded by ``shift_max`` |
| 4 | ``sheet_A`` negative | EMA stays ``None``; dropped defensively |
| 5 | ``sheet_A = NaN`` | EMA stays ``None`` |
| 6 | ``sheet_A = inf`` | EMA stays ``None`` |
| 7 | Very large ``sheet_A`` (1e12) | shift stays in ``[-shift_max, +shift_max]`` |
| 8 | Many improving samples | shift saturates at ``+shift_max`` |
| 9 | All edge cases through wrapper | ``n_cap in [0, 1]`` invariant |

### ``ConvergenceAdaptiveScheduler`` (8 edge cases)

| # | Edge case | Expected outcome |
|---|---|---|
| 1 | Empty ``w2_history`` | ``shift == 0``; first sample = baseline |
| 2 | ``W2 = NaN`` | EMA + history untouched |
| 3 | ``W2 = inf`` | EMA + history untouched |
| 4 | ``W2 = -inf`` | EMA + history untouched |
| 5 | ``kp = 0`` | proportional branch silent; derivative may move |
| 6 | ``kd = 0`` | derivative branch silent; proportional may move |
| 7 | ``shift_max = 0`` | shift pinned at 0 |
| 8 | Aggressive gains | ``n_cap in [0, 1]`` invariant survives |

### ``EvidenceDrivenScheduler`` (8 edge cases)

| # | Edge case | Expected outcome |
|---|---|---|
| 1 | Empty feedback history | sample equals cosine baseline |
| 2 | ``kp = 0`` | proportional branch silent |
| 3 | ``ki = 0`` | integral branch silent |
| 4 | ``evidence_ratio = 0`` | positive delta (move ``n_cap`` up) |
| 5 | ``evidence_ratio = 1`` | zero delta (at set-point) |
| 6 | ``evidence_ratio = NaN`` / no key | emits ``EVIDENCE_RATIO_MISSING``; falls back to 0.5 |
| 7 | NaN input coercion | delta is finite (no NaN propagation) |
| 8 | Aggressive ratio swings | ``n_cap in [0, 1]`` invariant |

### ``NFEAwareMemoryScheduler`` (8 edge cases)

| # | Edge case | Expected outcome |
|---|---|---|
| 1 | ``nfe_budget = 0`` | ``ValueError`` (avoids zero division) |
| 2 | ``threshold = 0`` | ``ValueError`` (avoids zero division) |
| 3 | ``n_rounds = 0`` | ``ValueError`` |
| 4 | ``nfe_budget = 1`` (smallest legal) | no raise; tiny but finite memory fraction |
| 5 | ``max_memory_fraction = 0`` | ``n_cap = 1`` (no memory dominance) |
| 6 | ``max_memory_fraction = 1`` | ``n_cap = 0`` (full memory dominance) |
| 7 | Seed variant | identical schedule (deterministic family) |
| 8 | Legal parameter walk | ``n_cap in [0, 1]`` invariant |

### ``FreeTrajScheduler`` (7 edge cases)

| # | Edge case | Expected outcome |
|---|---|---|
| 1 | ``cycle_length = 1`` | single-round cycle; ``n_cap in [0, 1]`` |
| 2 | ``cycle_length = 1000`` (very long) | no raise; samples finite |
| 3 | ``trajectory_amplitude = 0`` | matches cosine baseline exactly |
| 4 | ``trajectory_amplitude < 0`` | ``ValueError`` |
| 5 | ``trajectory_amplitude > 1`` | ``ValueError`` |
| 6 | ``trajectory_period = 0`` | ``ValueError`` |
| 7 | ``trajectory_amplitude = 1`` (extreme) | ``n_cap in [0, 1]`` invariant |

### ``TierAwareCodimensionSheetScheduler`` (9 edge cases)

| # | Edge case | Expected outcome |
|---|---|---|
| 1 | Tier ties at low boundary | record == low -> ``hard`` |
| 2 | Single-tier fallback | every record same tier (hard/medium/easy) |
| 3 | No baseline metrics | falls through with full ``n_cap`` |
| 4 | ``easy_tier_nfe_reduction_factor = 1`` | wrapper is a no-op |
| 5 | ``easy_tier_nfe_reduction_factor = 0.5`` | ``n_cap`` floor at ``n_min`` |
| 6 | ``easy_tier_nfe_reduction_factor = 0`` | ``ValueError`` (must be > 0) |
| 7 | ``easy_tier_nfe_reduction_factor > 1`` | ``ValueError`` |
| 8 | ``tier_quantile_boundaries`` not strictly ordered | ``ValueError`` |
| 9 | Aggressive factor (0.1) | ``n_cap in [0, 1]`` invariant |

### ``TestSchedulerDeterminism`` (6 byte-stable tests)

| # | Scheduler | Bytes-stable across 3 runs? |
|---|---|---|
| 1 | ``CodimensionSheetScheduler`` | YES |
| 2 | ``PaperRatioAdaptiveScheduler`` | YES |
| 3 | ``ConvergenceAdaptiveScheduler`` | YES |
| 4 | ``NFEAwareMemoryScheduler`` | YES |
| 5 | ``FreeTrajScheduler`` | YES |
| 6 | ``TierAwareCodimensionSheetScheduler`` | YES |

Hash: ``hashlib.sha256`` of the ``float64`` little-endian ``n_cap``
sequence. Any rounding-mode change (e.g. switching from C ``double``
to ``longdouble``) would surface as a hash mismatch -- the
deterministic property is verified at the bit level, not at
``pytest.approx`` precision.

## Bugs surfaced (Phase 3 fix candidates)

**No new bugs were surfaced** -- all 65 tests pass against the current
framework. Two latent issues were *documented* but are NOT
considered Phase 3 fixes:

### Documented issue 1 -- ``n_min > n_max`` silently accepted

:class:`CodimensionSheetScheduler` validates each of ``n_min`` and
``n_max`` lies in ``[0, 1]`` independently but does NOT enforce
ordering. The closed form ``n_min + (n_max - n_min) * ratio`` can
produce values outside the canonical ``[0, 1]`` range for some
ratios; the defensive clip in :meth:`sample` keeps ``n_cap in
[0, 1]``.

The test ``test_n_min_greater_than_n_max_is_silently_clipped``
documents the **current** behaviour. If the contract is tightened
in a future wave (to raise on ``n_min > n_max``), this test will
need to be updated.

### Documented issue 2 -- F16 EMA in PID ``prev`` reference

The :class:`ConvergenceAdaptiveScheduler` PID uses the EMA-smoothed
``w2_history`` (NOT the raw aggregated signal) as the ``prev``
reference. The F16 fix from Wave 31 is verified by
``test_kd_zero_no_derivative_shift``: with ``ema=0.3``, two
records ``W2 = [1.0, 0.5]`` produce ``shift ≈ +0.075``, not the
naive ``+0.25`` one would expect from the raw delta. The behaviour
is correct (matches the F16 invariant).

## Invariant verification

| Invariant | Status |
|---|---|
| ``tests/test_d4_regression_vectors.py`` | **30/30 PASS** |
| ``python3 tools/check_claims_consistency.py`` | **No drift** (61 active claims, 0 provisional) |
| ``ruff check tests/test_paper_grounded_schedulers.py`` | **0 findings** |
| ``mkdocs build --strict`` | pre-existing warnings only (3 nav warnings unrelated to this file) |

## Vendored code

**No vendored code modified.** All changes are confined to
``tests/test_paper_grounded_schedulers.py`` (new file) and
``docs/audit/wave287-p-test-coverage.md`` (new file).

## File inventory

| File | Status | Lines |
|---|---|---|
| ``tests/test_paper_grounded_schedulers.py`` | NEW | 1320 |
| ``docs/audit/wave287-p-test-coverage.md`` | NEW | this file |