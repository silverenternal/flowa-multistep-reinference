# Wave 86 Agent A — Phase 1 READ-ONLY Audit: framework-loop bug fix plan

**Date:** 2026-09-08
**Scope:** READ-ONLY audit of two framework-internal bugs surfaced in Wave 86
auditor findings, ahead of Wave 86 Agent B code changes:

1. **Pitfall #2 — `tools/gen_lineageflow_n1000_fastas.py:86-97`**: baseline and
   framework arms are generated from a **shared `random.Random` instance** in
   the same `for arm in ("baseline", "framework"):` loop. The framework arm is
   therefore byte-identical to baseline except for the `>header` line — there
   is no real framework-driven re-inference applied to the FASTA generation.
   `N=1000` was therefore never actually run; the sweep ran `sweep_actual_n_per_arm=5`
   because the resulting FASTAs were indistinguishable from baseline.

2. **Pitfall #1 PARTIAL — `tools/run_real_ckpt_eval.py:1105`**: `_make_framework_policy`
   hardcodes `beta = 0.5` as a constant per round. The Wave 31
   `PaperRatioAdaptiveScheduler.record_round_feedback(round_in_cycle, paper_quantities)`
   entry point exists and is fully wired into the scheduler module
   (`adaptive_reflow/algorithm/scheduler/_core.py:3814` + `:4122`), but the
   eval pipeline never feeds `paper_quantities` to it. The per-round `β`
   is therefore not paper-quantity-driven in production.

**Inputs (read in full this audit):**
- `tools/gen_lineageflow_n1000_fastas.py` (107 LOC, 2026-09-08 HEAD)
- `tools/run_real_ckpt_eval.py:1030-1271` (Wave 64/45-fixed `_solve_baseline` /
  `_make_framework_policy` / `_solve_framework`)
- `adaptive_reflow/algorithm/scheduler/_core.py:2783-4150` (`CodimensionSheetScheduler`
  + `PaperRatioAdaptiveScheduler` + the `default_paper_ratio_scheduler` factory
  at `:631`)
- `adaptive_reflow/adapters/lineageflow.py:1858, 1515, 1543` (`solve_ode`,
  `export_endpoint`, `apply_restart_distribution`)
- `adaptive_reflow/contracts/paper_quantities.py:37-50` (the 4 paper-quantity
  exports: `sheet_evidence_A`, `root_cell_packing_B`, `per_cell_coefficient_C`,
  `exterior_gap_e_rho`)
- `docs/audit/wave81-phase1-audit.md` (5-LOC `_StubLineageFlow.forward`
  signature fix — already shipped in HEAD)
- `docs/audit/wave81-phase3-sweep.md` (N=1000 upstream eval sweep results)

**Output:** this audit doc + LOC estimates + risk assessment + D.4 byte-stable
verification plan. NO code changes. NO commits.

---

## 1. Pitfall #2 fix plan — `gen_lineageflow_n1000_fastas.py`

### 1.1 Current state (the bug)

`tools/gen_lineageflow_n1000_fastas.py:86-97`:

```python
for arm in ("baseline", "framework"):
    out_path = args.outdir / f"{arm}.fasta"
    with out_path.open("w") as f:
        for i in range(args.n):
            family_id = family_ids[i % len(family_ids)]
            length = rng.randint(args.min_len, args.max_len)
            seq = _generate_sequence(rng, family_id, length)
            f.write(f">{arm}_seed{i}|family={family_id}\n")
            f.write(f"{seq}\n")
            manifest["per_family_count"].setdefault(family_id, 0)
            manifest["per_family_count"][family_id] += 1
    print(f"wrote {out_path} (n={args.n})")
```

Both arms consume from the SAME `rng` (line 74: `rng = random.Random(args.seed)`).
Because Python's `random.Random.choices` and `.randint` advance internal state,
the framework arm's first record starts from the state the baseline arm's
last record left — but more importantly, **no framework glue layer is ever
applied**. There is no call to `LineageFlowAdapter.solve_ode`, no
`apply_restart_distribution`, no scheduler sample, no `inject_noise`. The
"framework" arm is just the continuation of the same `random.Random`
sequence — its sequences ARE different from baseline (because RNG state
differs), but they are NOT produced by the framework.

This means the upstream eval orchestrator (`tools/upstream_eval.py`) ran the
framework-arm FASTAs through `data/lineageflow_upstream/evaluation/evaluate_all.py`,
which is independent of any framework glue. So:

* `Wave 81 Phase 3 N=1000 sweep` (`docs/audit/wave81-phase3-sweep.md`) ran
  1000 FASTA sequences per arm through the upstream classifier, NOT
  through the framework adapter.
* The Wave 81 numbers in `docs/paper-draft.md §7.4` measure "lineageflow
  upstream eval on 2 different random AA distributions" — NOT "framework
  re-inference vs. baseline re-inference".
* `sweep_actual_n_per_arm=5` reflects the auditor's empirical
  observation that the framework arm produces effectively the same
  per-family distribution as baseline, just shifted by N samples.

### 1.2 Fix plan — replace shared RNG with `LineageFlowAdapter.solve_ode`

**Location:** `tools/gen_lineageflow_n1000_fastas.py:86-97` (the `for arm`
loop body).

**Goal:** the baseline arm keeps the current `_generate_sequence(rng, ...)` path
(the bare-RNG draws are the literal "baseline" — what the adapter would emit
if asked to sample without framework glue). The framework arm must drive
the **real** `LineageFlowAdapter.solve_ode(...)` call so the produced
sequences are the result of `n_rounds` framework passes with
restart-blend + paper-quantity-driven scheduler.

The fix is ~30 LOC of new code plus an import. The cleanest design:

1. Import the LineageFlowAdapter (lazy, inside `main`, to avoid hard-coupling
   `tools/gen_lineageflow_n1000_fastas.py` to the `lineageflow_venv`-only
   `transformers` dep):

   ```python
   try:
       from adaptive_reflow.adapters.lineageflow import LineageFlowAdapter
   except Exception as _exc:  # pragma: no cover — fallback path
       LineageFlowAdapter = None
       _LINEAGEFLOW_IMPORT_ERR = _exc
   ```

2. Build the adapter once in `main`, immediately after the `rng` construction,
   with `family_id=family_ids[0]` and the canonical LineageFlow stub-mode
   settings (this is the same shape `_build_initial_state_and_condition`
   uses at `run_real_ckpt_eval.py:1006-1029`):

   ```python
   adapter = None
   if LineageFlowAdapter is not None:
       try:
           adapter = LineageFlowAdapter(
               family_id=family_ids[0],
               num_steps=10,            # matches Wave 81 NFE=10 default
               solver="euler",
               seed=int(args.seed),
           )
       except Exception as _exc:
           print(f"WARNING: LineageFlowAdapter init failed ({_exc}); "
                 "falling back to bare-RNG framework arm (Pitfall #2 not closed).")
           adapter = None
   ```

3. Replace the shared-RNG loop with **two separate arms**, each with its
   own RNG sub-stream derived from `args.seed` (so the framework arm is
   reproducible without contaminating baseline):

   ```python
   baseline_rng = random.Random(args.seed)
   framework_rng = random.Random(args.seed ^ 0x5A5A)  # distinct sub-stream

   # Baseline arm: bare RNG draws (current behaviour, preserved)
   out_path = args.outdir / "baseline.fasta"
   with out_path.open("w") as f:
       for i in range(args.n):
           family_id = family_ids[i % len(family_ids)]
           length = baseline_rng.randint(args.min_len, args.max_len)
           seq = _generate_sequence(baseline_rng, family_id, length)
           f.write(f">baseline_seed{i}|family={family_id}\n")
           f.write(f"{seq}\n")
           manifest["per_family_count"].setdefault(family_id, 0)
           manifest["per_family_count"][family_id] += 1
   print(f"wrote {out_path} (n={args.n})")

   # Framework arm: drive the real LineageFlowAdapter.
   # The adapter's per-step velocity field consumes the
   # conditioning family + a Pfam-conditioned prior; we
   # thread the per-record family_id + length via the
   # adapter's state-bundle API.
   out_path = args.outdir / "framework.fasta"
   framework_adapter = LineageFlowAdapter(
       family_id=family_ids[0], num_steps=10, solver="euler",
       seed=int(args.seed),
   ) if adapter is not None else None
   with out_path.open("w") as f:
       for i in range(args.n):
           family_id = family_ids[i % len(family_ids)]
           length = framework_rng.randint(args.min_len, args.max_len)
           if framework_adapter is None:
               # Fallback: bare RNG (Pitfall #2 not closed; auditor must escalate)
               seq = _generate_sequence(framework_rng, family_id, length)
           else:
               seq = _framework_emit_sequence(
                   framework_adapter,
                   family_id=family_id,
                   length=length,
                   seed=int(args.seed) + int(i),
               )
           f.write(f">framework_seed{i}|family={family_id}\n")
           f.write(f"{seq}\n")
   print(f"wrote {out_path} (n={args.n})")
   ```

4. Add a helper `_framework_emit_sequence(adapter, family_id, length, seed)`
   that constructs the StateBundle + ODEConditionDelta pair and calls
   `adapter.solve_ode(...)`, then extracts the per-position categorical
   sample via the existing adapter observation surface
   (`adapter.observe(...)` from Wave 68 Phase 2, OR
   `_extract_aa_for_fasta` fallback):

   ```python
   def _framework_emit_sequence(
       adapter: "LineageFlowAdapter",
       *,
       family_id: str,
       length: int,
       seed: int,
   ) -> str:
       """Drive one LineageFlow round; emit a length-L AA string."""
       from adaptive_reflow.universal.state import StateBundle, ODEConditionDelta
       from adaptive_reflow.adapters.lineageflow import (
           _synthesize_latent_like_tensor,  # already imported in lineageflow.py
       )
       # Build a placeholder StateBundle (identity-then-export_endpoint).
       placeholder_theta = _synthesize_latent_like_tensor(
           np.random.default_rng(seed)
       )
       bundle = StateBundle(
           raw_state=placeholder_theta,
           source_round=0,
           detach_proof=True,
           native_state_digest=f"placeholder:{seed}:{family_id}:{length}",
           provenance=("lineageflow_adapter.placeholder",),
           capability_token=adapter.capabilities(),
       )
       condition = ODEConditionDelta(
           delta_spec={
               "num_steps": 10,
               "sampler_id": "euler",
               "family_id": family_id,
           },
           source="gen_lineageflow_n1000_fastas.framework_arm",
           target_round=0,
           calibration_artifact_hash="gen_lineageflow_n1000_fastas:default",
       )
       trace = adapter.solve_ode(bundle, condition, seed=int(seed))
       # Decode the trace to AA via argmax (matches _extract_aa_for_fasta).
       theta = np.asarray(trace.native_state_digest, dtype=np.float64)
       # The trace carries the per-position categorical posterior as
       # ``native_state_digest``-encoded payload; argmax over the
       # last axis yields per-position AA indices. See
       # Wave 68 Phase 2 `observe()` for the canonical extraction path.
       if hasattr(trace, "positions"):
           aa_idx = np.asarray(trace.positions, dtype=np.int64)
       else:
           # Fallback: reconstruct from raw_state.
           aa_idx = theta.reshape(-1, 33).argmax(axis=-1)
       aa_idx = aa_idx.flatten()[:length]
       from adaptive_reflow.adapters.lineageflow import AMINO_ACID_SET
       AA_SET_LOCAL = AMINO_ACID_SET  # 20-AA canonical alphabet
       return "".join(AA_SET_LOCAL[i % len(AA_SET_LOCAL)] for i in aa_idx)
   ```

   **Note:** the exact decode path depends on the trace payload — Wave 68
   Phase 2 `LineageFlowAdapter.observe()` returns `dict[ObservationKind, ...]`
   keyed by `POSITION_CATEGORICAL` etc. The implementer should consult
   `docs/audit/wave68-phase2.md` §3 for the canonical extraction surface
   and adapt `_framework_emit_sequence` accordingly. The placeholder above
   is illustrative.

### 1.3 LOC estimate

| File | New code | Existing code deleted | Total |
|---|---|---|---|
| `tools/gen_lineageflow_n1000_fastas.py` | +45 (helper + adapter init + new loop body) | -12 (old shared-RNG loop) | ~33 LOC net |

Total: **~35-45 LOC**.

### 1.4 Risk assessment

| Risk | Severity | Mitigation |
|---|---|---|
| **Adapter not importable in canonical venv** (no `transformers` installed) — fallback to bare RNG | HIGH | Lazy `try/except` import + explicit `print("WARNING … Pitfall #2 not closed")` + manifest entry recording `framework_arm_mode: "adapter" / "fallback_rng"` so the auditor can detect failed runs |
| **Adapter output shape drift** — `native_state_digest` payload format may differ from Wave 68 Phase 2 expectations | MEDIUM | Unit test: feed a known seed and assert the emitted AA string matches a pinned reference; if it does not, fall back to the synthetic `argmax` path and log the mismatch |
| **D.4 byte-stable regression** — the previous gen script's output was pinned by D.4 vector tests; changing the FASTA generation may break the pinned baseline.fasta | HIGH (Pitfall #2's whole point is that baseline.fasta WAS already stale-because-shared-RNG) | Refresh D.4 vectors for `lineageflow_n1000` after the fix; this is an EXPECTED regeneration, not a regression — `tests/test_d4_vectors.py` should be updated to use the new pinned hashes, with a one-line note in `docs/audit/wave86-phase2-verify.md` |
| **AA alphabet mismatch** — `AMINO_ACID_SET` length vs `_extract_aa_for_fasta` expectation | LOW | Read `adaptive_reflow/adapters/lineageflow.py:AMINO_ACID_SET` (canonical 20-AA alphabet, defined inline) before implementing the helper |
| **`_synthesize_latent_like_tensor` is private** — its signature may change | LOW | Use `adapter._resolve_conditioning(family_id=..., seed=...)` to build a real (non-placeholder) bundle, then call `adapter.solve_ode(bundle, condition, seed=...)` directly — see Wave 47 Phase 2 `LineageFlowGlue` for the canonical bundle-construction pattern |

### 1.5 Verification plan

1. **D.4 byte-stable regression** (HARD gate): `pytest tests/ -k "d4"` must
   remain 33/33 PASS. The `lineageflow_n1000` vector sub-suite
   (`tests/test_d4_vectors.py::test_lineageflow_*`) must be re-pinned to
   match the new (correctly-distinct) baseline.fasta + framework.fasta
   outputs. See `docs/audit/wave82-phase4-final.md` for the precedent of
   intentional D.4 re-pinning after a PB-xtb fix.
2. **Unit test on the helper**: assert `_framework_emit_sequence(adapter,
   family_id="PF00005.27", length=80, seed=42)` returns a string of length
   80 consisting only of characters in `AMINO_ACID_SET`.
3. **Determinism test**: two calls with the same `(family_id, length, seed)`
   must return byte-identical strings.
4. **Smoke test on N=10**: run the patched script with `--n 10` and verify
   that `framework.fasta` differs from `baseline.fasta` at the byte level
   (not just the header). Audit-script can grep for shared-line count and
   assert it's < 10% of N.
5. **Adapter conformance**: `pytest tests/test_adapters/test_lineageflow.py`
   must remain 22/22 PASS (or current count).

---

## 2. Pitfall #1 fix plan — paper-quantity → per-round β

### 2.1 Current state (the bug)

`tools/run_real_ckpt_eval.py:1105`:

```python
beta = 0.5  # constant beta per round; framework's scheduler drives
            # the per-round beta in production, this value only
            # shapes the restart blend math.
```

This `beta` flows into `_make_framework_policy`'s `beta_by_channel`
(line 1117):
```python
beta_by_channel={ch: FactorValue(float(beta)) for ch in channel_names},
```

The constant 0.5 means **every** framework round uses `β=0.5` regardless of
the paper quantities (`sheet_A`, `packing_B`, `exterior_gap_e_rho`). The
`PaperRatioAdaptiveScheduler.record_round_feedback(round_in_cycle,
paper_quantities)` entry point at `_core.py:4122-4125` exists and is fully
wired into the scheduler module (`adaptive_reflow/algorithm/scheduler/__init__.py:41`
re-exports it), but **the eval pipeline never calls it** — so the
paper-quantity-aware PID-lite controller never gets a `paper_quantities`
update.

The Wave 31 design intent was that the `n_cap` (and therefore the
restart-blend `β`) should be driven by `sheet_evidence_A` /
`root_cell_packing_B` / `exterior_gap_e_rho` from
`adaptive_reflow.contracts.paper_quantities`. The four paper-quantity
exports at `paper_quantities.py:37-50` are:

- `sheet_evidence_A(profile)` — Lemma 2 / Proposition 3
- `root_cell_packing_B(profile)` — Lemma 5 / line 159
- `per_cell_coefficient_C()` — Lemma 3 / line 191
- `exterior_gap_e_rho()` — Lemma 4 / Lemma 5

These four functions take a residual profile `g(x)` callable (from the
adapter) and return floats. The eval pipeline currently has no path from
the per-round trace → profile residual → paper quantities → `β`.

### 2.2 Fix plan — wire paper_quantities through `_solve_framework` + `_make_framework_policy`

**Locations:** `tools/run_real_ckpt_eval.py:1132-1271` (`_solve_framework`)
+ `:1057-1129` (`_make_framework_policy`).

**Goal:** per round, derive a per-round `β` from the paper-quantity signal
sourced from the just-completed `solve_ode` round, then feed that `β`
into `_make_framework_policy` as a kwarg. The result: framework-arm β
values are paper-quantity-driven, not constant 0.5.

**The signature to add** (Wave 31 already declared it; the wiring is the
only missing piece):

```python
# In adaptive_reflow/algorithm/scheduler/__init__.py — already exported (line 41)
from adaptive_reflow.algorithm.scheduler._core import PaperRatioAdaptiveScheduler

# In adaptive_reflow/contracts/__init__.py — already exported (line 37-50)
from adaptive_reflow.contracts.paper_quantities import (
    sheet_evidence_A,
    root_cell_packing_B,
    per_cell_coefficient_C,
    exterior_gap_e_rho,
)
```

**The eval pipeline wiring (the actual fix):**

1. In `_solve_framework`, after each per-round `trace = adapter.solve_ode(...)`
   call (line 1199-1208) and BEFORE the `_make_framework_policy` call (line
   1232), compute the paper quantities from a profile residual callable:

   ```python
   # Wave 86 — Pitfall #1 fix. Compute paper quantities from
   # the just-completed per-round trace, then feed them into
   # the per-round β via _make_framework_policy(target_round=r,
   # seed=seed, beta_by_quantities=pq). When the adapter cannot
   # supply a profile_residual_fn (the dev-env fallback path),
   # we pass beta=None and the existing constant-0.5 fallback
   # path is taken — preserving byte-stability for adapters
   # that don't yet expose paper quantities.
   pq = _compute_paper_quantities(adapter, trace, round_index=int(r))
   policy = _make_framework_policy(
       adapter, target_round=int(r), seed=int(seed),
       paper_quantities=pq,
   )
   ```

2. Add a helper `_compute_paper_quantities(adapter, trace, round_index)`:

   ```python
   def _compute_paper_quantities(
       adapter: Any, trace: Any, *, round_index: int,
   ) -> dict[str, float] | None:
       """Derive the 4 paper quantities from the just-completed per-round trace.

       Returns ``None`` if the adapter does not supply a
       ``profile_residual_fn`` (preserves legacy constant-β behaviour).
       """
       # Adapters may publish a profile_residual_fn via capabilities()
       # OR via a direct attribute on the adapter. Check both.
       profile_residual_fn = None
       caps = (
           adapter.capabilities() if hasattr(adapter, "capabilities") else None
       )
       if caps is not None and hasattr(caps, "profile_residual_fn"):
           profile_residual_fn = caps.profile_residual_fn
       if profile_residual_fn is None:
           profile_residual_fn = getattr(adapter, "profile_residual_fn", None)
       if profile_residual_fn is None:
           return None
       try:
           from adaptive_reflow.contracts import paper_quantities as _pq
           sheet_A = float(_pq.sheet_evidence_A(profile_residual_fn))
           packing_B = float(_pq.root_cell_packing_B(profile_residual_fn))
           exterior_gap = float(_pq.exterior_gap_e_rho())
       except Exception:
           # Defensive: a broken paper-quantity oracle must NOT poison
           # the framework arm — fall back to constant β.
           return None
       return {
           "sheet_A": sheet_A,
           "packing_B": packing_B,
           "exterior_gap": exterior_gap,
       }
   ```

3. Update `_make_framework_policy` signature to accept an optional
   `paper_quantities` kwarg and use it via `PaperRatioAdaptiveScheduler.sample`
   to derive the per-round β:

   ```python
   def _make_framework_policy(
       adapter: Any, *, target_round: int, seed: int,
       paper_quantities: dict[str, float] | None = None,
   ) -> Any:
       """Build a fresh FinalRestartPolicy for one framework round.

       Wave 86 — Pitfall #1 fix: when ``paper_quantities`` is supplied,
       the per-round β is driven by the Wave 31
       PaperRatioAdaptiveScheduler (paper Lemma 2 / Lemma 3 / Lemma 5
       ground truth), NOT the legacy constant-0.5. When
       ``paper_quantities`` is None (legacy adapter without
       ``profile_residual_fn``), the constant-0.5 fallback is preserved
       byte-identically to Wave 45.
       """
       # ... [existing channel_names construction unchanged] ...

       if paper_quantities is not None:
           # Drive β via PaperRatioAdaptiveScheduler.
           from adaptive_reflow.algorithm.scheduler import (
               PaperRatioAdaptiveScheduler,
               CodimensionSheetScheduler,
           )
           scheduler = PaperRatioAdaptiveScheduler(
               base=CodimensionSheetScheduler(
                   cycle_length=int(n_rounds) if n_rounds is not None else 20,
                   eps_implicit=0.05,
                   eps_direction="decreasing",
                   seed=int(seed),
               ),
           )
           # Push the current paper_quantities into the EMA, then sample
           # the per-round beta. For round 0 (no prior history), the
           # shift is 0 and n_cap_base is the canonical paper-ratio.
           scheduler.record_round_feedback(
               round_in_cycle=int(target_round),
               paper_quantities=paper_quantities,
           )
           sample = scheduler.sample(
               outer_cycle_id=0,
               round_in_cycle=int(target_round),
               target_round=int(target_round),
           )
           # n_cap ∈ [0, 1] → β = 1 - n_cap (matches the Wave 45
           # restart-blend convention: m = 1 - β, so β=0 → full
           # memory, β=1 → fresh). This makes a high paper-ratio
           # (sheet-dominant) → high β → more fresh noise → more
           # exploration, and a low paper-ratio (cell-dominant)
           # → low β → more memory → exploitation.
           beta = float(1.0 - float(sample.n_cap))
       else:
           beta = 0.5  # legacy constant — preserved byte-identical
       # ... [rest of existing FinalRestartPolicy construction unchanged] ...
   ```

### 2.3 LOC estimate

| File | New code | Existing code modified | Total |
|---|---|---|---|
| `tools/run_real_ckpt_eval.py` (new helper) | +35 (`_compute_paper_quantities`) | — | ~35 LOC |
| `tools/run_real_ckpt_eval.py` (`_make_framework_policy` body) | +25 (paper-quant path) | ~10 (signature change, kwarg threading) | ~35 LOC |
| `tools/run_real_ckpt_eval.py` (`_solve_framework` call site) | +8 (call to `_compute_paper_quantities` + pass to `_make_framework_policy`) | — | ~8 LOC |
| `tests/test_tools/test_run_real_ckpt_eval.py` (regression tests) | +40 (paper-quant driving β test + fallback test) | — | ~40 LOC |

Total: **~80 LOC** (excluding tests: ~80 LOC; including tests: ~120 LOC).

### 2.4 Risk assessment

| Risk | Severity | Mitigation |
|---|---|---|
| **`PaperRatioAdaptiveScheduler` semantics** — round 0 produces `shift=0`, so β_round0 = `1 - n_cap_base(0)` (not 1.0); round 0 paper-quantities don't actually shift β. Auditor must understand this is correct | LOW | Document in the helper's docstring; add a test that asserts β_round0 ≠ 1.0 when `paper_quantities` is non-None |
| **D.4 byte-stable regression** — adding `paper_quantities` kwarg changes the `policy_hash` for every framework cell. The D.4 pinned vectors at `tests/test_d4_vectors.py` will break | HIGH (same as Pitfall #2) | Refresh D.4 vectors after the fix; this is an EXPECTED regeneration, not a regression. Use the same pattern as Wave 82 PB-xtb fix (`docs/audit/wave82-phase4-final.md`) — update pinned hashes with a one-line note in `docs/audit/wave86-phase2-verify.md` |
| **Adapter profile_residual_fn API** — Wave 31 designs `profile_residual_fn` on the scheduler constructor, not on the adapter. Adapters may not expose it yet | MEDIUM | Step 1: check `caps.profile_residual_fn` AND `adapter.profile_residual_fn` (defensive lookup). Step 2: if neither is present, return `None` and fall back to constant β — preserves byte-stability. Step 3: document the expected adapter surface in `docs/PLUG_IN_YOUR_MODEL.md` |
| **`record_round_feedback` is mutable** — calling it from `_solve_framework` mutates the scheduler across rounds, which is the correct design but means the scheduler cannot be reused across cells | LOW | Construct a fresh `PaperRatioAdaptiveScheduler` inside `_make_framework_policy` per call (the proposed design does this); alternative: cache on the adapter instance — but the per-call-fresh design is safer and matches the `FinalRestartPolicy` per-round construction pattern |
| **Beta is in [0, 1] but n_cap is also in [0, 1]** — the `β = 1 - n_cap` mapping inverts the paper-ratio signal. Auditor must confirm this matches Wave 31's intended semantics | LOW | Cross-reference with `docs/audit/wave31-*.md` (Wave 31 Phase 2 docs are not in `docs/audit/` — they live in `docs/audit/wave31-paper-quantity-scheduler.md` if it exists, OR in the Wave 31 task list at #557; otherwise inspect `scheduler/_core.py:3999-4050` `PaperRatioAdaptiveScheduler.sample` to confirm the audit codes carry `schedule_paper_ratio_adaptive_shift`) |

### 2.5 Verification plan

1. **D.4 byte-stable regression**: same as §1.5 #1.
2. **Adapter conformance**: `pytest tests/test_adapters/` must remain at
   current count (all green). Particularly watch
   `tests/test_adapters/test_lineageflow.py` and
   `tests/test_adapters/test_kanzi.py` for any new
   `profile_residual_fn` expectations.
3. **Per-round β diversity test**: for a 5-round framework pass on the
   LineageFlow adapter, assert that the per-round β values differ from
   each other AND from 0.5 (proves the paper-quantity signal is reaching
   the policy). When `paper_quantities=None` is forced, assert all β == 0.5
   (byte-stability for the legacy path).
4. **Fallback test**: for adapters that don't expose
   `profile_residual_fn`, the `_compute_paper_quantities` helper must
   return `None`, the `_make_framework_policy` must take the constant-0.5
   path, and the framework arm must be byte-identical to the Wave 45
   output.
5. **Paper-quantity threading test**: instrument `_make_framework_policy`
   to log the per-round β; assert that β_round0 differs from β_round1
   when both rounds have `paper_quantities` supplied.

---

## 3. Cross-cutting concerns

### 3.1 Wave 81 `_StubLineageFlow.forward` fix is already shipped

`docs/audit/wave81-phase1-audit.md` describes the 5-LOC fix to
`_StubLineageFlow.forward` (lines 1043-1058 originally → now lines 1018-1044
with the `(input_ids=None, attention_mask=None, inputs_embeds=None, **kwargs)`
signature). This fix is **already on HEAD** (confirmed by reading
`adaptive_reflow/adapters/lineageflow.py:1018-1024`). So Pitfall #2's
"framework arm will hit CapabilityMissingError" risk from the prompt is
already mitigated — when `_load_torch_model` falls back to `_StubLineageFlow`
on a venv without `transformers`, the call site at line 579 (`v =
model(input_ids=ids)`) will now succeed (returning zeros of shape
`(B, L, K=33)`) instead of raising `TypeError`.

**Wave 86 Agent B does NOT need to re-touch `_StubLineageFlow.forward`** —
the Pitfall #2 fix's `_framework_emit_sequence` helper can rely on the
stub-path being call-safe.

### 3.2 Framework-arm loop already calls `solve_ode` + `apply_restart_distribution`

`tools/run_real_ckpt_eval.py:1190-1238` (`_solve_framework`'s per-round
loop body) already exercises the canonical Wave 45 contract:

1. `trace = adapter.solve_ode(cur_bundle, condition, seed=...)` (line 1199)
2. `endpoint = adapter.export_endpoint(cur_bundle)` (line 1218)
3. `policy = _make_framework_policy(adapter, target_round=r, seed=...)` (line 1232)
4. `cur_bundle = adapter.apply_restart_distribution(endpoint, policy)` (line 1235)

Confirmed against `adaptive_reflow/adapters/lineageflow.py:1543-1619`
(`apply_restart_distribution`) and `:1515-1523` (`export_endpoint`): both
signatures are `(state: StateBundle, policy: RestartPolicy)` and `(state:
StateBundle) -> StateBundle` respectively, matching the Wave 45 F-2 fix.

So the **only** Wave 86 changes are:

- `_make_framework_policy` signature gets `paper_quantities=None` kwarg
  (Pitfall #1 fix, ~25 LOC).
- `_solve_framework` per-round loop gets a `_compute_paper_quantities(adapter,
  trace, round_index=r)` call and threads its result into `_make_framework_policy`
  (Pitfall #1 fix, ~8 LOC).
- New `_compute_paper_quantities` helper (~35 LOC).
- `gen_lineageflow_n1000_fastas.py` per-arm loops split + `_framework_emit_sequence`
  helper (~35 LOC).

### 3.3 D.4 byte-stable regression (HARD gate)

The D.4 vector suite at `tests/test_d4_vectors.py` (33 vectors currently
PASS, per `docs/audit/wave82-phase4-final.md` §D.4 + Wave 66 v2 wiring)
pins the framework-arm output of `_solve_framework` and
`_make_framework_policy`. After Wave 86:

- The `paper_quantities`-driven β path will produce a different
  `FinalRestartPolicy.policy_hash` for every round, which propagates
  through `apply_restart_distribution` → `cur_bundle` →
  `integrated_trace` (the final `solve_ode` call at line 1268-1270).
  → The integrated trace bytes change. → D.4 vectors for LineageFlow
  and Kanzi will need re-pinning.
- The `gen_lineageflow_n1000_fastas.py` fix will produce a
  different `framework.fasta` (because the framework arm now actually
  drives the adapter), so the Wave 81 sweep's pinned outputs will
  need re-pinning.

The **expected** workflow:

1. Wave 86 Agent B applies both fixes.
2. Wave 86 Agent B runs `pytest tests/ -k "d4"` and observes the
   expected breakages (LineageFlow + Kanzi + the lineageflow_n1000
   sub-suite).
3. Wave 86 Agent B refreshes the pinned hashes via the existing
   D.4 vector refresh utility (`tools/refresh_d4_vectors.py` or
   equivalent — see Wave 82 / Wave 66 precedents), with a one-line
   note in the docstring of each refreshed vector: "Wave 86 — Pitfall #2
   fix changed framework-arm FASTA generation; Pitfall #1 fix changed
   per-round β derivation".
4. Wave 86 Agent B runs `pytest tests/ -k "d4"` again and confirms
   33/33 (or current count, post-refresh) PASS.

This is **not** a regression — it is an expected consequence of fixing two
genuine framework bugs. The D.4 gate's purpose is to detect UNINTENDED
changes; the changes here are INTENDED and documented.

### 3.4 Verification summary

| Verification | Trigger | Expected result | Owner |
|---|---|---|---|
| `pytest tests/ -k "d4"` | After both fixes applied | FAIL first (expected), PASS after refresh | Wave 86 Agent B |
| `pytest tests/test_adapters/test_lineageflow.py` | After Pitfall #2 fix | 22/22 PASS (stub path now exercised; Wave 81 fix sufficient) | Wave 86 Agent B |
| `pytest tests/test_tools/test_run_real_ckpt_eval.py` | After Pitfall #1 fix | All PASS (new tests for paper-quant-driven β + fallback β=0.5 path) | Wave 86 Agent B |
| Smoke test N=10 on patched `gen_lineageflow_n1000_fastas.py` | After Pitfall #2 fix | `framework.fasta` differs from `baseline.fasta` at >10% of positions | Wave 86 Agent B |
| Per-round β diversity test | After Pitfall #1 fix | β_round0 ≠ β_round1 (and neither == 0.5) when paper_quantities supplied | Wave 86 Agent B |

---

## 4. Wave 86 Agent B implementation checklist

The implementer should, in this order:

1. **Pitfall #1 first** (smaller blast radius — only touches
   `_make_framework_policy` + `_solve_framework` + a new helper):
   - Add `_compute_paper_quantities(adapter, trace, round_index)` (~35 LOC)
   - Add `paper_quantities=None` kwarg to `_make_framework_policy` (~25 LOC)
   - Thread the helper call from `_solve_framework` per-round loop (~8 LOC)
   - Add 2 regression tests (per-round β diversity + fallback β=0.5 path)
2. **Pitfall #2 second** (larger blast radius — touches the FASTA generator
   AND the D.4 lineageflow_n1000 vector sub-suite):
   - Refactor `tools/gen_lineageflow_n1000_fastas.py:86-97` into two arms
   - Add `_framework_emit_sequence(adapter, family_id, length, seed)` helper
   - Add 1 smoke test (N=10, framework.fasta ≠ baseline.fasta)
3. **D.4 refresh** (single commit at the end):
   - `pytest tests/ -k "d4"` → expected breakage
   - Refresh LineageFlow + Kanzi + lineageflow_n1000 vectors
   - Annotate the refreshed vectors in their docstrings
4. **Verify**:
   - `pytest tests/ -k "d4"` → 33/33 PASS
   - `pytest tests/test_adapters/test_lineageflow.py` → 22/22 PASS
   - `pytest tests/test_tools/test_run_real_ckpt_eval.py` → all PASS
   - `mkdocs build --strict` → exit 0
5. **Commit** (single, NO push):
   - Title: "Wave 86 Agent B: fix Pitfall #1 (paper-quant-driven β) + Pitfall #2 (framework-arm real FASTA generation)"
   - Body must reference `docs/audit/wave86-phase1-audit.md` + this checklist
   - Author the Phase 2-verify doc: `docs/audit/wave86-phase2-verify.md`

---

## 5. Out-of-scope for Wave 86 (do NOT touch)

- **`_StubLineageFlow.forward`** — Wave 81 already shipped the 5-LOC fix.
  Re-touching risks regressing D.4 stability.
- **`PaperRatioAdaptiveScheduler` semantics** — Wave 31 design is
  complete. The fix only WIRES the existing scheduler into the eval pipeline.
- **Adapter `profile_residual_fn` surface** — adding this to each
  adapter is a separate MUST-3 / D.1-shrink concern. Wave 86's helper
  falls back to constant β when the adapter doesn't expose it.
- **`tools/run_real_ckpt_eval.py` CLI flags** — no new flags needed.
  The paper-quantity path activates automatically when the adapter
  exposes `profile_residual_fn`; the legacy path is preserved
  byte-identically otherwise.
- **Push** — Wave 86 Agent B does NOT push. Push is Wave 86 Agent C's
  responsibility after verify passes.

---

## 6. References

- `tools/gen_lineageflow_n1000_fastas.py:1-107` (the buggy script)
- `tools/run_real_ckpt_eval.py:1030-1271` (`_solve_baseline`,
  `_make_framework_policy`, `_solve_framework`)
- `adaptive_reflow/algorithm/scheduler/_core.py:2783-4150`
  (`CodimensionSheetScheduler`, `PaperRatioAdaptiveScheduler`)
- `adaptive_reflow/algorithm/scheduler/_core.py:4122-4170`
  (`record_round_feedback(round_in_cycle, paper_quantities)` entry point)
- `adaptive_reflow/contracts/paper_quantities.py:37-50`
  (4 paper-quantity exports)
- `adaptive_reflow/adapters/lineageflow.py:1018-1044` (`_StubLineageFlow.forward`
  — Wave 81 fix already shipped)
- `adaptive_reflow/adapters/lineageflow.py:1515-1619`
  (`export_endpoint`, `apply_restart_distribution`)
- `docs/audit/wave81-phase1-audit.md` (5-LOC stub-signature fix)
- `docs/audit/wave81-phase3-sweep.md` (N=1000 upstream eval sweep)
- `docs/audit/wave82-phase4-final.md` (D.4 byte-stable regression
  precedent for intentional vector refresh)
- `docs/audit/wave68-phase2.md` (LineageFlow `observe()` extraction
  surface for `_framework_emit_sequence`)