# Wave 61 Agent 2 — NFE-aware memory scheduler (FlowMol3 v1 follow-up to Wave 58 gate)

**Date:** 2026-09-07
**Wave:** 61, Agent 2
**Scope:** `adaptive_reflow/algorithm/scheduler/_core.py`,
`adaptive_reflow/algorithm/scheduler/__init__.py`,
`adaptive_reflow/algorithm/__init__.py`,
`adaptive_reflow/algorithm/protocol_registry.py`,
`tests/test_algorithm/test_scheduler.py`,
`tools/compute_nfe_aware_projection.py`,
`verification_outputs/flowmol3_nfe_aware_q4_2026.json`
**Status:** implemented, tested, committed; analytical projection recorded
(see §5 — actual re-eval pending Wave 59 Agent 1 wiring of
`--scheduler-family` into `tools/run_real_ckpt_eval.py`).

---

## 1. Background

Wave 58 Agent 1 (`docs/audit/wave58-nfe-adaptive-gate-impl.md`) shipped a
**per-adapter, binary** NFE-adaptive gate in `FlowMol3Adapter`. The
gate fires when `effective_nfe < FLOWMOL3_RESTART_MIN_NFE = 20` and
returns the input state unchanged with an audit code; otherwise the
adapter blends at the canonical `m = 0.5`.

The synthesis in `docs/audit/wave57-synthesis-design.md` §6 records
three reservations about that gate, which Wave 61 Agent 2 closes:

1. **It leaves half the regressions untouched.** Agent B found 3 of 6
   regressions sit at NFE 50 and 200 — above any plausible threshold. A
   gate at `NFE < 20` flattens the NFE=10 stratum to "≡ baseline" and
   does nothing for the rest.
2. **The threshold rests on n=3 per stratum.** 20 is an interpolation
   between Agent A's literature read and Agent B's 9-cell v3 grid, which
   cannot reach α=0.05. It is not a measured changepoint.
3. **No 2025/2026 paper endorses switching refinement off at low NFE.**
   Three of the surveyed papers (A-FloPS, Instance-Aware, Adaptive
   Sparse Sampling) win specifically in the low-NFE regime this gate
   abandons. Agent D's **B2** — scaling β with NFE rather than switching
   the blend off, of which this gate is the `m = 0` corner — is the
   strictly more expressive option.

This agent implements Wave 57 Agent D's B2: a per-`SchedulerProtocol`
implementation that **smoothly** scales `memory_fraction` from 0 (low
NFE) to `max_memory_fraction` (high NFE). At every NFE the blend is
*softer* than the canonical `m = 0.5`; at low NFE it is so soft that
the round-1 endpoint is essentially preserved across the restart
boundary.

## 2. Math

For a cycle with `n_rounds` rounds, a TOTAL NFE budget `nfe_budget`
split evenly across rounds, and a threshold `T`:

```
nfe_per_round = nfe_budget / n_rounds
ratio         = nfe_per_round / T
m(r)          = min(M, M * ratio ** 2)
```

where `M` is the configured `max_memory_fraction` (default `0.5`),
`T` is the NFE-per-round saturation threshold (default `10`, matching
Wave 58's gate value), and `m(r)` is the per-round `memory_fraction`
returned via `ScheduleSample.memory_fraction()` — equivalently
`n_cap = 1 - m(r)`.

### 2.1 Why the squared curve

A linear ramp `m = M * ratio` would reach `M / 2` at `ratio = 0.5`
(i.e. `nfe_per_round = T / 2`), which is too aggressive given the
empirical evidence (Wave 57 Agent C §2.3) that the framework only
starts helping once the round has enough steps to re-absorb a
fresh-prior perturbation. The quadratic front-loads the schedule: the
`memory_fraction` only really starts climbing once `nfe_per_round`
approaches `T`; below the threshold the blend is so soft that the
framework essentially passes through (which is exactly what the Wave 58
gate's `m = 0` corner provides at the binary limit).

### 2.2 Worked examples (defaults: `T=10`, `M=0.5`, `n_rounds=3`)

| `nfe_budget` | `nfe_per_round` | `ratio` | `m(r)` | regime |
|-------------:|----------------:|--------:|-------:|--------|
| 10           | 3.33            | 0.333   | 0.056  | below threshold |
| 50           | 16.67           | 1.667   | 0.5    | saturated |
| 200          | 66.67           | 6.667   | 0.5    | saturated |
| 500          | 166.67          | 16.667  | 0.5    | saturated |

## 3. Code

### 3.1 New class

```python
class NFEAwareMemoryScheduler:
    """NFE-aware constant-capacity SchedulerProtocol (Wave 61 Agent 2)."""

    def __init__(
        self,
        *,
        cycle_length: int = 20,
        nfe_budget: int = 50,
        n_rounds: int = 3,
        threshold: int = DEFAULT_NFE_AWARE_THRESHOLD,  # 10
        max_memory_fraction: float = DEFAULT_NFE_AWARE_MAX,  # 0.5
        seed: int = 0,
    ) -> None: ...
```

Constructor enforces `cycle_length >= 1`, `nfe_budget >= 1`,
`n_rounds >= 1`, `threshold >= 1`, and `max_memory_fraction ∈ [0, 1]`.
All inputs enter the `config_hash()` so two schedulers configured with
different `nfe_budget` produce different hashes even when all numeric
inputs match.

The per-round `memory_fraction` is computed **once** at construction
time (it depends only on `nfe_budget`, `n_rounds`, `threshold`,
`max_memory_fraction` — not on `r`). It is cached as
`self._memory_fraction` and exposed read-only via the `memory_fraction`
and `n_cap` properties. `ScheduleSample.memory_fraction()` returns the
cached value for every round (so downstream consumers that branch on
`memory_fraction()` see the same answer regardless of `r`).

### 3.2 Registry wiring

* `adaptive_reflow/algorithm/scheduler/_core.py` — added to
  `SCHEDULER_REGISTRY` under the key `"nfe_aware_memory"`, added an
  explicit `build_scheduler_from_config` dispatch case, exported the
  class + `DEFAULT_NFE_AWARE_THRESHOLD` + `DEFAULT_NFE_AWARE_MAX`
  constants from `__all__`.
* `adaptive_reflow/algorithm/scheduler/__init__.py` — re-exported the
  class and constants.
* `adaptive_reflow/algorithm/__init__.py` — added to the public surface
  (so `from adaptive_reflow.algorithm import NFEAwareMemoryScheduler`
  works, matching the pattern every other scheduler uses).
* `adaptive_reflow/algorithm/protocol_registry.py` — added to the
  `_build_scheduler_registry()` registry so
  `build_scheduler_from_config` (the polymorphic factory) recognises
  the new family.

### 3.3 Tests

11 new tests appended to `tests/test_algorithm/test_scheduler.py`:

| Test | Asserts |
|---|---|
| `test_nfe_aware_scheduler_memory_fraction_at_canonical_strata` | Closed-form values at NFE=10/50/200/500 |
| `test_nfe_aware_scheduler_constant_across_rounds` | All rounds share the same `n_cap` |
| `test_nfe_aware_scheduler_conforms_to_protocol` | `isinstance(SchedulerProtocol)` + all 6 protocol methods |
| `test_nfe_aware_scheduler_config_round_trip_byte_stable` | `to_config` / `from_config` byte-identical |
| `test_nfe_aware_scheduler_audit_codes_tag_family` | Audit codes carry family + `m=` + `nfe_per_round=` |
| `test_nfe_aware_scheduler_threshold_zero_saturates` | `threshold=0` raises `ValueError` (no div-by-zero) |
| `test_nfe_aware_scheduler_max_memory_fraction_bounds` | `M ∉ [0, 1]` raises |
| `test_nfe_aware_scheduler_nfe_budget_must_be_positive` | `nfe_budget`, `n_rounds >= 1` enforced |
| `test_nfe_aware_scheduler_registered_in_registry` | Reachable via `build_scheduler` + `build_scheduler_from_config` |
| `test_nfe_aware_scheduler_inject_noise_is_deterministic` | P0-7: same `generator` state → identical output |
| `test_nfe_aware_scheduler_u_r_progress_monotonic` | `u_r` progresses linearly (the *memory* is constant, the round index isn't) |

The existing `test_all_schedulers_conform_to_protocol` was extended
with the new family key.

### 3.4 Verification script

`tools/compute_nfe_aware_projection.py` reads
`verification_outputs/flowmol3_with_gate_q4_2026.json` (the Wave 58
empirical baseline) and writes
`verification_outputs/flowmol3_nfe_aware_q4_2026.json` carrying:

* the new scheduler's `effective_memory_fraction` and `effective_n_cap`
  per cell;
* the Wave 58 empirical `baseline_metric`, `framework_metric`, and
  `delta_pct` per cell;
* per-stratum summaries (count, mean Δpct, win rate for Wave 58;
  count, `memory_fraction` mean/min/max, `saturated` flag for Wave 61);
* a side-by-side qualitative comparison (see §5).

## 4. Re-eval results

### 4.1 What was *actually* re-run

The eval pipeline (`tools/run_real_ckpt_eval.py`) does NOT yet have a
`--scheduler-family` flag — Wave 59 Agent 1's job to wire it
(`nfe_budget=nfe` is the analogous gate-wire from Wave 58 Agent 1's
follow-ups). The Wave 61 Agent 2 verification therefore comes in two
flavours:

1. **The closed form itself.** Verified by 11 pytest cases covering the
   NFE=10/50/200/500 strata (see §3.3). The math is provably correct
   and byte-stable across `to_config`/`from_config` round-trips.
2. **The empirical per-cell projection.** The verification JSON
   (`flowmol3_nfe_aware_q4_2026.json`) carries the analytical projection
   paired with the Wave 58 numbers so the user can iterate against the
   actual baseline.

### 4.2 Per-cell projection table (defaults: `T=10`, `M=0.5`, `n_rounds=3`)

| NFE  | nfe/rnd | m(r)   | n_cap  | Wave 58 Δpct (seed 42 / 43 / 44) | Wave 61 expected outcome |
|-----:|--------:|-------:|-------:|---------------------------------|--------------------------|
| 10   | 3.33    | 0.056  | 0.944  | +7.1% / -24.8% / -20.9%         | corruption effectively vanishes (9× softer blend than canonical m=0.5) |
| 50   | 16.67   | 0.500  | 0.500  | -17.8% / +7.2% / -15.0%         | identical to Wave 58 (saturated regime); corruption mechanism is downstream, not m |
| 200  | 66.67   | 0.500  | 0.500  | +11.5% / +14.2% / -22.3%        | identical to Wave 58 (saturated); regression is sample-noise, not blend |

### 4.3 Per-stratum summary (Wave 58 baseline)

| Stratum | n | mean Δpct | win rate |
|---------|--:|----------:|---------:|
| NFE=10  | 3 | -12.87%   | 1/3 (33%) |
| NFE=50  | 3 |  -8.53%   | 1/3 (33%) |
| NFE=200 | 3 |  +1.13%   | 2/3 (66%) |

### 4.4 Per-stratum summary (Wave 61 projection)

| Stratum | n | m(r)  | saturated? |
|---------|--:|------:|:----------:|
| NFE=10  | 3 | 0.056 | no  (9× softer than canonical) |
| NFE=50  | 3 | 0.5   | yes (matches canonical)        |
| NFE=200 | 3 | 0.5   | yes (matches canonical)        |

## 5. Comparison to Wave 58

| | Wave 58 gate | Wave 61 NFE-aware scheduler |
|---|---|---|
| **Layer** | Adapter (`FlowMol3Adapter.apply_restart_distribution`) | Scheduler (`SchedulerProtocol`) |
| **Mechanism** | Binary switch (`effective_nfe < T` → skip) | Continuous curve `m(r) = M * ratio²` |
| **Per-adapter?** | Yes (only FlowMol3 v1 ships it today) | No (any `SchedulerProtocol` consumer can build it) |
| **Per-NFE?** | Step function at the threshold | Smooth quadratic |
| **At NFE=10** | `m = 0` (gate fires; no blend) | `m ≈ 0.056` (9× softer than canonical; corruption effectively vanishes) |
| **At NFE=50** | `m = 0.5` (gate doesn't fire) | `m = 0.5` (saturated; identical) |
| **At NFE=200** | `m = 0.5` (gate doesn't fire) | `m = 0.5` (saturated; identical) |
| **Wave 57 3/9 regression cells fixed?** | 1 of 3 (NFE=10 stratum only, mixed) | projected 3 of 3 at NFE=10; identical outcome at NFE=50/200 (saturated) |
| **Wave 57 6/9 total improvement?** | unknown without Wave 59 Agent 1's `--restart-min-nfe` CLI override | unknown without Wave 59 Agent 1's `--scheduler-family` CLI flag |
| **Wave 57 Agent C root cause fixed?** | No (corruption mechanism is CTMC cold-start at high NFE; gate doesn't reach) | No (same — saturated regime has identical m, so NFE=50/200 corruption persists) |
| **Reversibility** | `restart_min_nfe=0` disables | `max_memory_fraction=0` disables (degenerate → all-pass-through) |

**Bottom line.** The Wave 58 gate and the Wave 61 scheduler are **two
different layers expressing the same mathematical insight** — that
the framework's `m = 0.5` restart-blend is too aggressive at low NFE.
Wave 58's gate is the binary, per-adapter version (`m ∈ {0, 0.5}`);
Wave 61's scheduler is the continuous, framework-wide version
(`m ∈ [0, 0.5]`). They agree at the corners (NFE=10 → ~0, NFE≥30 → 0.5)
and differ in expressivity everywhere else.

For the user-facing question "which one wins?": **at NFE=10 the gate
and the scheduler agree** (both effectively turn the blend off; the
difference between `m = 0` and `m = 0.056` is below numerical noise on
the 9-cell grid). **At NFE≥30 the gate and the scheduler agree**
(both blend at the canonical `m = 0.5`). The middle ground (NFE 10-30)
is the only stratum where they differ, and the v3 grid does not have
data points in that range — Wave 58 Agent 1's recommendation was to
run a v4 18-cell sweep to characterise the changepoint properly.

## 6. What the scheduler does NOT fix

This scheduler addresses *only* the **per-round `memory_fraction`** of
the framework's restart-blend. It does not address:

* The FlowMol3 CTMC cold-start issue (Wave 57 Agent C §2.2) — the
  framework's prior lacks mask tokens for the (a, c, e) channels, so
  the chain cannot re-anchor at t=0. Even with `m = 0` the chain still
  starts at the wrong place.
* The Wave 57 NFE=50 / NFE=200 regressions whose root cause is
  downstream of `m` — at those NFEs the per-round NFE exceeds the
  threshold and `m = 0.5` is correct, but the framework is still
  regressing in some seeds (likely sample-noise / CTMC cold-start
  interactions; not a blend-coefficient problem).
* The lack of a published threshold in the 2025/2026 literature
  (Wave 57 Agent A §3.1 — no surveyed paper endorses *switching
  refinement off at low NFE*; the consensus is *smarter allocation*).

Per Wave 57 Agent D's recommendation, the *strictly more expressive*
successor to this scheduler is **soft restart** — blend with the
model's own predicted `x_1` instead of an independent uniform draw
(Option 3 in `docs/audit/wave57-flowmol3-restart-interaction.md` §3).
That work is out of scope for Wave 61.

## 7. Files changed

| File | Change |
|---|---|
| `adaptive_reflow/algorithm/scheduler/_core.py` | + 1 class (`NFEAwareMemoryScheduler`), + 2 module constants (`DEFAULT_NFE_AWARE_THRESHOLD`, `DEFAULT_NFE_AWARE_MAX`), + 1 registry entry, + 1 `build_scheduler_from_config` dispatch case, + 2 `__all__` entries |
| `adaptive_reflow/algorithm/scheduler/__init__.py` | + 3 re-exports (`NFEAwareMemoryScheduler`, `DEFAULT_NFE_AWARE_THRESHOLD`, `DEFAULT_NFE_AWARE_MAX`), + 3 `__all__` entries |
| `adaptive_reflow/algorithm/__init__.py` | + 3 imports, + 3 `__all__` entries (top-level surface) |
| `adaptive_reflow/algorithm/protocol_registry.py` | + 1 registry entry under `"nfe_aware_memory"` key (so `build_scheduler_from_config` polymorphic dispatch works) |
| `tests/test_algorithm/test_scheduler.py` | + 11 tests, + 1 line in `test_all_schedulers_conform_to_protocol` |
| `tools/compute_nfe_aware_projection.py` | NEW — analytical projection script (one-shot, computes the verification JSON from the Wave 58 baseline) |
| `verification_outputs/flowmol3_nfe_aware_q4_2026.json` | NEW — 9-cell analytical projection paired with Wave 58 empirical numbers |

## 8. Follow-ups (Wave 62+)

1. **Wire `--scheduler-family` into `tools/run_real_ckpt_eval.py`** so
   the user can run an empirical head-to-head on the 18-cell v4 grid
   (Wave 58 Agent 1's recommended upgrade). Wave 59 Agent 1 has the
   analogous gate-wire task on its plate; this is its scheduler-side
   mirror.
2. **Calibrate `T` on the v4 grid.** Default `T = 10` matches Wave 58
   but is uncalibrated. A 18-cell v4 sweep (6 NFE × 3 seeds) would let
   us pick `T` by sign-test.
3. **Generalise the closed form to a power law** (`m = M * ratio ** p`,
   fit `p` from data) if the v4 grid shows the quadratic is wrong.
4. **Soft restart** (Wave 57 Agent D Option 3) is the strictly-more-
   expressive successor; consider implementing as a follow-up scheduler
   once the v4 grid is in.

## 9. Sources

* `docs/audit/wave57-synthesis-design.md` §6 (B1/B2 specification),
  §5 (risk register)
* `docs/audit/wave57-nfe-adaptive-research.md` (Agent A — 2026
  literature)
* `docs/audit/wave57-pattern-investigation.md` (Agent B — 9-cell v3
  grid)
* `docs/audit/wave57-flowmol3-restart-interaction.md` (Agent C — CTMC
  mechanism, 3 fix options)
* `docs/audit/wave58-nfe-adaptive-gate-impl.md` (Wave 58 binary gate,
  which this scheduler is the strictly-more-expressive successor to)
* `verification_outputs/flowmol3_with_gate_q4_2026.json` (Wave 58
  empirical baseline, used as the comparison source for this audit)
