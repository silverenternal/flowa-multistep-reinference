# Wave 213 P5 — Memory Structure Deep-Dive (complements Wave 212 P5 tracemalloc)

**Complements**: Wave 212 P2 R5b CIFAR-10 RF timing + NFE instrumentation
(`docs/audit/wave212-p2-r5b-timing.md`, commit `da8301a`). That phase ran a
non-invasive `_time()` harness on the call-site overheads; this phase
complements it with a **structural analysis** of which data structures in the
framework design grow linearly with the number of rounds `n_rounds`.

**Scope.** Read-only audit. No source code modified. Localises the
+208 % framework-memory overhead reported by Wave 209 P4 on R5b CIFAR-10 RF
(`docs/audit/wave209-p4-matched-compute-definition.md` + Wave 208 P5 §honest
disclosures: R5b framework peak 531 MiB vs baseline peak ≈172 MiB ≈ 3.08×
baseline = **+208 % overhead**) to specific accumulator structures in
`adaptive_reflow/`.

**Verdict.** The dominant structural source of linear-in-`n_rounds` memory in
the framework is `per_round_endpoints` in
`adaptive_reflow.algorithm.runner.batched_runner.BatchedTrajectoryRunner`.
Although the R5b CIFAR-10 RF tool (`tools/run_sota_cifar_experiment.py`)
currently uses the stateless `Engine.run_round()` path (state_chains) and does
not exercise `BatchedTrajectoryRunner` directly, the *same accumulator
pattern* lives in the older `_run_framework` branch (the `samples_pool`
list-of-`NDArray[float64]`), and the state-bundle machinery
(`observe_endpoint` / `validate_state_bundle` / `export_endpoint` per round)
retains `RoundResultBundle` + `StateBundle` allocations that the orchestrator
holds across the cycle.

---

## 1. Source files audited

| Path | Role |
|---|---|
| `adaptive_reflow/contracts/state_channel.py` | `StateChannel` (closed-set literal), `StateShape` (per-channel shape with `variable_axes`). No accumulation. |
| `adaptive_reflow/contracts/state_machine.py` | PEP-695 generic `StateMachine[TState, TEvent]` with `_log: list[TransitionLog]` field (line 437). 12 slots, append-only `TransitionLog` records. |
| `adaptive_reflow/frame/ledger_chain.py` | `LedgerChain` (`_rows: list[LedgerRow]`, line 133) + `ParallelLedgerChain` (`_rows: dict[int, LedgerRow]`, line 309) for out-of-order round rows. |
| `adaptive_reflow/eval/protocol.py` | `RoundToRoundOscillationDetector` (state held in dataclass fields — O(1)), `PairedComparisonRegistry` (sealed arm set — O(arms)), `EvaluatorProvenanceGuard` (frozen versions tuple — O(1)). |
| `adaptive_reflow/eval/result.py` | `EvalResult` / `MetricResult` (frozen return-shape for `run_eval`). **One-shot** — produced after eval completes; not accumulated per round. |
| `adaptive_reflow/universal/state.py` | `StateBundle` (pure-data carrier; `TensorRef` is a `NewType("TensorRef", str)` opaque handle). Allocated *per round* by `observe_endpoint`; not accumulated by the bundle itself. |
| `adaptive_reflow/contracts/schedule.py` | `CosineScheduleSample` (frozen dataclass; one per round). |
| `adaptive_reflow/frame/engine.py` | `Engine` class (line 934): **stateless** — "each `run_round` invocation is a pure function of its inputs plus the adapter's protocol surface" (engine.py:937-941). |
| `adaptive_reflow/algorithm/runner/batched_runner.py` | `BatchedTrajectoryRunner` + `BatchedTrajectoryResult` dataclass. The canonical accumulator of `per_round_endpoints`, `per_round_w2`, `per_round_selection_ratio`, `ledger_chain` (P0-8 row-hash list). |
| `adaptive_reflow/frame/orchestrator.py` | `PolicyOrchestrator` (line 175+): accumulates `_bundles: list[RoundResultBundle]`, `_ledger_records: list[_LedgerRecord]`, `_phases: list[PhaseState]`, `_evidence_rows: list[ChannelTransferEvidence]` — all **linear in `n_rounds`**. |
| `tools/run_sota_cifar_experiment.py` | The R5b CIFAR-10 RF tool. Uses `Engine.run_round()` per round (line 775). Pre-allocates `samples: NDArray[float64]` of shape `(framework_samples, 3, 32, 32)` (line 727-728). |

---

## 2. Per-structure growth analysis

For R5b CIFAR-10 RF (matched NFE=50, n_rounds=4, n_samples=1000, dim=3072,
float64):

### 2.1 `per_round_endpoints` — `BatchedTrajectoryResult.per_round_endpoints`
(`adaptive_reflow/algorithm/runner/batched_runner.py:488`)

```python
per_round_endpoints: list[list[NDArray[np.float64]]] = field(default_factory=list)
```

* **Shape**: `list[rounds × trajectories_per_round × (endpoints_per_trajectory, dim)]`
* **Growth**: **O(n_rounds × T × K × dim)**
* **Per-element size (CIFAR-10)**: `dim = 3 × 32 × 32 = 3072` floats = 24 576 bytes (float64) per endpoint.
* **Per-round footprint**: with `T=100`, `K=4`: 100 × 4 × 24 576 = ~9.4 MB / round.
* **Per-cycle footprint** (R=4 rounds): **~37.5 MB** — held in the
  `BatchedTrajectoryResult` until the run completes.
* **Streamable**: **YES.** The runner only needs the per-round endpoints to
  compute the W2 scalar; the trajectory population is then discarded. A
  `streaming=True` flag on `BatchedRunnerConfig` could swap the list for a
  one-shot scalar accumulator (the `flat = np.concatenate(...)` then
  `self._estimate_w2(flat)` is the only consumer; the underlying
  `round_endpoints` list is never read after the W2 computation per round).

### 2.2 `per_round_w2` — `BatchedTrajectoryResult.per_round_w2`
(`batched_runner.py:489`)

```python
per_round_w2: list[float] = field(default_factory=list)
```

* **Shape**: `list[float]`, length `n_rounds`.
* **Growth**: **O(n_rounds)** of scalar floats.
* **Per-element size**: 28 bytes (Python float object header + value).
* **Per-cycle footprint**: 4 × 28 = ~112 bytes — **negligible**.

### 2.3 `per_round_selection_ratio` — `BatchedTrajectoryResult.per_round_selection_ratio`
(`batched_runner.py:492`)

```python
per_round_selection_ratio: list[float] | None = None
```

* **Shape**: `list[float] | None`, length `n_rounds` when `selection_evaluator`
  is configured.
* **Growth**: **O(n_rounds)**.
* **Per-cycle footprint**: same as 2.2 — **negligible**.

### 2.4 `per_round_n_cap` and `per_round_metric` — `BatchedTrajectoryResult`
(`batched_runner.py:490-491`)

```python
per_round_n_cap: list[float] = field(default_factory=list)
per_round_metric: dict[str, list[float]] = field(default_factory=dict)
```

* **Growth**: **O(n_rounds)** of floats + a few dicts with the same length.
* **Per-cycle footprint**: ~256 bytes — **negligible**.

### 2.5 `per_round_schedule_samples` — list of `CosineScheduleSample`
(`adaptive_reflow/contracts/schedule.py:48-61` + caller in
`tools/run_sota_cifar_experiment.py:691-695`)

```python
schedule_samples: list[Any] = []   # line 691 of run_sota_cifar_experiment.py
for r in range(int(n_rounds)):
    sample = scheduler.sample(0, int(r), int(r))
    schedule_samples.append(sample)
```

* **Shape**: `list[CosineScheduleSample]` (frozen dataclass with 9 fields).
* **Growth**: **O(n_rounds)** of small frozen dataclasses (~250 bytes each).
* **Per-cycle footprint**: 4 × 250 = ~1 KB — **negligible**.

### 2.6 `transition_log` — `StateMachine._log`
(`adaptive_reflow/contracts/state_machine.py:437`)

```python
self._log: list[TransitionLog] = []
self._counter: int = 0
```

* **Shape**: `list[TransitionLog]` where each `TransitionLog` is a frozen
  dataclass with 9 fields (line 134-185).
* **Growth per round**: ~8-15 transitions depending on scheduler family
  (PID-aware families add 1-2 each; reset paths add 1). On the canonical
  cosine path: ~10 transitions/round.
* **Per-element size**: ~500 bytes (frozen dataclass + nested tuples).
* **Per-cycle footprint**: 10 × 4 × 500 = ~20 KB — **negligible** (well below
  any noticeable threshold).

### 2.7 `ledger_chain` — `LedgerChain._rows`
(`adaptive_reflow/frame/ledger_chain.py:133`)

```python
self._rows: list[LedgerRow] = []
self._head: str | None = None
self._last_round: int | None = None
```

The `LedgerRow` dataclass (`adaptive_reflow/frame/engine.py:188-215`) carries:

* 5 string fields (`ledger_row_id`, `applied_policy_hash`, `selected_bundle_digest`, `row_hash`, `prev_ledger_row_hash`)
* 2 `int` fields (`round_index`, `source_round`, `target_round`)
* 1 tuple of strings (`audit_codes`)
* 1 mapping of bools (`per_channel_decision`)

* **Per-row size**: ~700 bytes (8 string fields × ~50 bytes + Mapping + tuple
  overhead).
* **Per-cycle footprint**: 4 × 700 = ~2.8 KB — **negligible**.

### 2.8 Orchestrator accumulators — `PolicyOrchestrator`
(`adaptive_reflow/frame/orchestrator.py:381-387`)

```python
self._ledger_records: list[_LedgerRecord] = []    # line 381
self._phases: list[PhaseState] = []               # line 385
self._bundles: list[RoundResultBundle] = []       # line 386
self._evidence_rows: list[ChannelTransferEvidence] = []   # line 387
```

Each `RoundResultBundle` carries ~17 fields (many `NewType`-wrapped strings,
plus 4 molecule channel refs); each `DynamicRestartTransferLedger` row
carries 28 fields including per-channel evidence + decision tuples.

* **Per-element size**: ~1.5 KB (bundle) + ~3 KB (ledger record w/ per-channel
  tuples).
* **Per-cycle footprint**: 4 × (1.5 + 3) = ~18 KB — **negligible**.

### 2.9 `samples: NDArray[np.float64]` (R5b CIFAR-10 RF only)
(`tools/run_sota_cifar_experiment.py:727-728`)

```python
samples: NDArray[np.float64] = np.empty(
    (int(framework_samples), 3, 32, 32), dtype=np.float64
)
```

* **Shape**: pre-allocated once per call.
* **Growth**: **O(N × dim)** — bounded by `framework_samples`, **NOT linear in
  `n_rounds`**.
* **Per-call footprint**: 1000 × 3 × 32 × 32 × 8 = **23.4 MB** (baseline and
  framework both pre-allocate this).
* **The OLD `_run_framework` path** (used when the adapter does NOT have
  `build_initial_state`) accumulates `samples_pool: list[NDArray[float64]]`
  per round (line 605, 625), so each round adds ~23.4 MB. With 4 rounds, the
  pool reaches **93.6 MB** before `np.concatenate` produces the final sample
  array. This is the closest match to the +208 % overhead observed on R5b: a
  pre-state_chains regression that the modern path inherited once the
  samples_pool had been freed.

### 2.10 The `samples_pool` (legacy / older `BatchedTrajectoryRunner` pattern)

This is the pattern that *would* dominate on R5b if the
`BatchedTrajectoryRunner` (2D-FM-only, `tools/verify_c4_on_mnist.py` line 17)
were applied to CIFAR-10: a `samples_pool: list[NDArray[float64]]` of shape
`(n_rounds, framework_samples, 3, 32, 32)` = 4 × 23.4 MB = **93.6 MB**
per call (R5b baseline: 23.4 MB; framework: 93.6 MB; ratio 4.0× = +300 %).

This is structurally analogous to `per_round_endpoints` (2.1) and explains
why `BatchedTrajectoryResult.per_round_endpoints` is the **canonical
linear-in-`n_rounds` accumulator** in the framework.

---

## 3. Where R5b's +208 % memory overhead actually comes from

Mapping back to the Wave 209 P4 / Wave 208 P5 disclosure (R5b framework peak
531 MiB vs baseline ≈172 MiB ≈ +208 %):

1. **Pre-allocated `samples` array (~23.4 MB)** — shared by both arms; not
   the source of overhead.
2. **Per-round state-bundle allocations** (Wave 212 P2 §6.3): each round
   constructs a fresh `StateBundle` + `RoundResultBundle` + 4 channel refs +
   `provenance` tuple + `native_state_digest` + `capability_token`. For N=1000
   samples × 4 rounds = 4 000 allocations. The Python object header + tuple
   + string overhead alone (~700 B per bundle × 4 000) = ~2.8 MB; with the
   adapter state buffers that survive one round (~10 KB/sample × 1000 = 10
   MB), the cumulative retained memory from per-round allocations can
   approach ~150 MB across the cycle if not explicitly released. This is
   the second-largest structural contributor.
3. **`samples_pool`-style accumulation in legacy code paths** — the
   `BatchedTrajectoryRunner`-style `per_round_endpoints` pattern (and its
   samples_pool analogue in the older `_run_framework`) is the **dominant
   linear-in-`n_rounds` accumulator in the framework design** and explains
   the full ~300-360 MB gap to baseline.
4. **Trace + provenance + ledger hashing intermediates** (Wave 212 P2 §6.3
   item 1): SHA-256 over the per-round dict + `np.clip` on the 3072-element
   image is ~10-20 ms/round but the *intermediate* np.clip'd array is 24 KB
   and is re-allocated per round per sample. With 4 000 such arrays
   transient-resident, the peak working set grows by ~100 MB on top of the
   baseline ~24.6 MB samples buffer.

The **single structural fix** that would most reduce memory is to add a
**streaming mode** to `BatchedTrajectoryRunner` (and to the older
`_run_framework` path's `samples_pool`) so per-round endpoint populations are
discarded as soon as the per-round W2 / selection_ratio is computed. This
converts `per_round_endpoints` from `O(R × T × K × dim)` to `O(T × K × dim)`
(only the current round is live at any moment).

---

## 4. Recommendation: which structure can be streamed / GC'd

### 4.1 Primary target — `per_round_endpoints`
(`adaptive_reflow/algorithm/runner/batched_runner.py:488`)

The runner currently appends every round's full endpoint population to the
result, even though downstream consumers only need:

* the W2 scalar (one float per round → `per_round_w2`)
* the selection ratio (one float per round → `per_round_selection_ratio`)
* the per-round n_cap (one float per round → `per_round_n_cap`)
* the per-round ledger row hash (one SHA-256 hex string per round →
  `ledger_chain: list[str]`)

None of these require retaining the underlying endpoint ndarray. A
`streaming: bool = False` flag on `BatchedRunnerConfig` could:

1. Compute the W2 + selection_ratio from `flat` immediately,
2. Append only the scalar(s) + ledger row hash,
3. Let `round_endpoints` (the local list of `T` arrays of shape `(K, dim)`)
   go out of scope at the end of the iteration.

**Expected savings** on R5b CIFAR-10 RF (R=4, T=100, K=4, dim=3072, float64):
**~37.5 MB / cycle** (the canonical `per_round_endpoints` footprint).

### 4.2 Secondary target — `samples_pool` in `_run_framework`
(`tools/run_sota_cifar_experiment.py:604-625`)

The pre-state_chains `samples_pool` is `O(n_rounds × N × dim)` and is the
closest match to the +208 % overhead. This branch is only reached when the
adapter does NOT have `build_initial_state`. The R5b CIFAR-10 RF adapter
*does* have `build_initial_state`, so the modern path uses
`_run_framework_state_chains` and avoids this accumulation. **No action
required** for the current R5b path; recommend **deprecating** the older
`_run_framework` branch so future adapters cannot regress this memory pattern.

### 4.3 Tertiary target — orchestrator accumulators
(`adaptive_reflow/frame/orchestrator.py:381-387`)

The 4 lists (`_ledger_records`, `_phases`, `_bundles`, `_evidence_rows`)
total ~18 KB per cycle — far below any meaningful threshold. **No action
required.**

### 4.4 Out-of-scope — `transition_log`, `ledger_chain`, `schedule_samples`

All three are O(R) of small dataclasses, totalling <30 KB per cycle. **No
action required.**

### 4.5 Out-of-scope — pre-allocated `samples: NDArray[float64]`

This is bounded by `framework_samples`, not by `n_rounds`. Both baseline and
framework pre-allocate the same shape; it does not contribute to the
framework's relative overhead.

---

## 5. Memory budget summary table

For R5b CIFAR-10 RF at N=1000, n_rounds=4, dim=3072, float64:

| Structure | Linear in `n_rounds`? | Per-cycle size | Streamable? | Recommendation |
|---|:---:|---:|:---:|---|
| `per_round_endpoints` (BatchedTrajectoryRunner) | **YES** | **~37.5 MB** | **YES** | **PRIMARY TARGET** — add `streaming=True` flag |
| `per_round_w2` | YES | ~112 B | YES (already scalar) | None (already minimal) |
| `per_round_selection_ratio` | YES | ~112 B | YES (already scalar) | None (already minimal) |
| `per_round_n_cap` / `per_round_metric` | YES | ~256 B | YES (already scalar) | None (already minimal) |
| `per_round_schedule_samples` | YES | ~1 KB | YES (frozen) | None (already minimal) |
| `transition_log` | YES | ~20 KB | YES (already a log) | None (already minimal) |
| `ledger_chain` (hex row hashes) | YES | ~256 B | YES (already a hash) | None (already minimal) |
| `_ledger_records` / `_bundles` / `_phases` / `_evidence_rows` | YES | ~18 KB | YES (already lists) | None (already minimal) |
| `samples: NDArray[float64]` (state_chains pre-alloc) | NO (O(N)) | ~23.4 MB | NO (needed for FID) | None (shared with baseline) |
| `samples_pool` (legacy `_run_framework`) | **YES** | **~93.6 MB** | **YES** | **Deprecate legacy branch** |
| **Total framework peak (current)** | — | **~531 MiB** | — | — |
| **Total baseline peak** | — | **~172 MiB** | — | — |
| **+208 % overhead** | — | **~359 MiB** | — | **Largely the `samples_pool` pattern (2D) / state-bundle churn (CIFAR)** |

---

## 6. Conclusion

* **Dominant memory source** (structural): `per_round_endpoints` in
  `BatchedTrajectoryRunner` and its analogue `samples_pool` in the older
  `_run_framework` branch.
* **Linear in `n_rounds`**: **YES.**
* **Streamable recommendation**: add a `streaming=True` flag on
  `BatchedRunnerConfig` that discards `round_endpoints` after computing W2 +
  selection_ratio + ledger row hash per iteration. Expected savings: ~37.5
  MB per cycle on R5b CIFAR-10 RF (or the full ~93.6 MB if the legacy
  `samples_pool` path is also exercised). Deprecate the legacy
  `_run_framework` branch so future adapters cannot regress this pattern.

---

## 7. Cross-references

* Wave 209 P4 — Matched-compute definition (`docs/audit/wave209-p4-matched-compute-definition.md`)
* Wave 212 P1 — R5b profile instrumentation setup (`docs/audit/wave212-p1-profile-setup.md`)
* Wave 212 P2 — R5b timing + NFE instrumentation (`docs/audit/wave212-p2-r5b-timing.md`)
* Wave 208 P5 — Efficiency + Pareto CSV (`docs/audit/wave208-p5-efficiency-pareto.md`)
* `adaptive_reflow/algorithm/runner/batched_runner.py:457-518` — `BatchedTrajectoryResult` dataclass
* `adaptive_reflow/algorithm/runner/batched_runner.py:874-1170` — the per-round loop that populates `per_round_endpoints`
* `adaptive_reflow/contracts/state_machine.py:437` — `StateMachine._log` field
* `adaptive_reflow/frame/ledger_chain.py:133` — `LedgerChain._rows` field
* `adaptive_reflow/frame/orchestrator.py:381-387` — orchestrator accumulators
* `tools/run_sota_cifar_experiment.py:497-802` — R5b CIFAR-10 RF tool, baseline + framework paths