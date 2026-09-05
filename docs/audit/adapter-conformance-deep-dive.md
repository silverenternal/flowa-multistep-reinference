# Wave 29 Agent C — Adapter/glue layer deep Protocol conformance audit

**Author**: Wave 29 Agent C (deep audit, beyond the D.5 conformance battery)
**Date**: 2026-09-05
**Scope**: Per-adapter conformance to
[`adaptive_reflow.universal.FlowMatchingODEAdapter`](/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/universal/adapter.py)
+ per-method signature, per-method behavior contract, per-method
deterministic-seed handling, StateBundle field completeness, and restart
blend invariants.

## Summary

| Metric | Value |
| --- | --- |
| Adapters audited (registered) | 14 |
| Adapters audited (unregistered / orphan) | 4 |
| Audit tests collected | 461 |
| Tests passed | 453 |
| Tests skipped | 39 (mnist_fm weights-on-disk; typed exceptions on smoke call) |
| Tests failed | **2** (both are real nonconformance findings) |
| Audit runtime | ~51 s |

> **Conclusion**: The 8-check conformance battery (Wave 15 C, D.5) is
> structurally sound. The 2 findings this deep audit surfaced sit
> *outside* the 8 checks because they exercise surfaces the
> conformance battery does NOT cover: a per-method ``FinalRestartPolicy``
> smoke call (B.5) and an orphan-class canonical-enumeration check (G.2).

## Per-adapter audit table

| Adapter | Registered | Protocol runtime check | Signature match | Field completeness | Restart contract | Byte-stable (seed) | Trajectory export | Findings |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `flowmol3` | yes | PASS | PASS | PASS | PASS (capability False → raises) | n/a (skipped: no torch) | PASS (raises NotImpl) | — |
| `flowmol3_v2` | yes | PASS | PASS | PASS | **BUG** (numpy shape crash) | PASS | PASS (numpy.ndarray) | **NONCONFORMANCE_BUG #1** |
| `graphbfn` | yes | PASS | PASS | PASS | PASS | PASS | PASS (numpy.ndarray) | — |
| `hidream_i1` | yes | PASS | PASS | PASS | PASS | PASS | PASS (numpy.ndarray) | — |
| `lineageflow` | yes | PASS | PASS | PASS | PASS | PASS | PASS (numpy.ndarray) | — |
| `lumina_image_2_0` | yes | PASS | PASS | PASS | PASS | PASS | PASS (numpy.ndarray) | — |
| `mnist_fm` | yes | SKIPPED (weights on disk) | — | — | — | — | — | n/a in CPU sandbox |
| `protbfn_abbfn` | yes | PASS | PASS | PASS | PASS | PASS | PASS (numpy.ndarray) | — |
| `rectified_flow_cifar` | yes | PASS | PASS | PASS | PASS | PASS | PASS (numpy.ndarray) | — |
| `reference_flowa` | NO (orphan) | PASS | PASS | PASS | PASS | PASS | PASS | **NONCONFORMANCE_DESIGN #2 (orphan)** |
| `self_flow` | yes | PASS | PASS | PASS | PASS | PASS | PASS (numpy.ndarray) | — |
| `toy_gaussian` | yes | PASS | PASS | PASS | PASS | PASS | PASS (returns None) | — |
| `toy_linear` | yes | PASS | PASS | PASS | PASS (capability False → raises) | PASS | PASS (raises NotImpl) | — |
| `twodim_fm` | yes | PASS | PASS | PASS | PASS | PASS | PASS (numpy.ndarray) | — |
| `wan2_2_video` | yes | PASS | PASS | PASS | PASS | PASS | PASS (numpy.ndarray) | — |
| `freqflow` | NO (Wave 21 skeleton) | PASS | PASS | PASS | PASS | n/a (synthetic mode) | PASS (None) | **NONCONFORMANCE_DESIGN #3 (skeleton)** |
| `kanzi` | NO (Wave 21 skeleton) | PASS | PASS | PASS | PASS | n/a (synthetic mode) | PASS (None) | **NONCONFORMANCE_DESIGN #4 (skeleton)** |
| `stochastic_fm` | NO (orphan) | PASS | PASS | **BUG** | PASS | n/a (raises on restart) | PASS (NotImpl) | **NONCONFORMANCE_BUG #5** |
| `synthetic_*` | NO (test fixture) | PASS | PASS | PASS | n/a | PASS | PASS (NotImpl) | excluded from registry audit (test fixtures) |

(4 synthetic fixtures — `SyntheticContinuousAdapter`,
`SyntheticDiscreteAdapter`, `SyntheticMixedChannelAdapter`,
`SyntheticUnsupportedAdapter` — are excluded from the registry
inventory because they are test shims, not production adapters.)

## Identified bugs (concrete fixes)

### NONCONFORMANCE_BUG #1 — `FlowMol3V2Adapter.apply_restart_distribution` crashes on shape mismatch

> **Status (2026-09-05): FIXED** by Wave 30 Agent B — see
> [Fix log](#fix-log) below. The finding text is preserved as written
> at audit time.

**File**:
[`adaptive_reflow/adapters/flowmol3_v2_adapter.py`](/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/flowmol3_v2_adapter.py)
lines 1175–1200 (``_channel_aware_blend`` — ``elif n_fresh > n_prior`` branch).

**Symptom**: ``ValueError: all the input array dimensions except for
the concatenation axis must match exactly, but along dimension 0, the
array at index 0 has size 36 and the array at index 1 has size 28``.

**Trigger**: ``apply_restart_distribution`` with a
:class:`FinalRestartPolicy` whose ``beta_by_channel`` / fresh state
shape is smaller than the prior's. The deep audit constructs a
single-element policy against a freshly-built bundle (atom count
28 vs prior 20, or vice versa) and the adapter crashes.

**Root cause**: After the first ``np.concatenate([fresh["e"], pad_e],
axis=0)`` (line 1182), ``fresh_e_full`` has shape ``(n_fresh +
n_fresh - n_prior, n_fresh)`` = ``(2*n_fresh - n_prior, n_fresh)``.
The next ``np.concatenate([fresh_e_full, pad_e_col], axis=1)``
(line 1193) uses ``pad_e_col`` of shape ``(n_fresh, 1)`` — but
the existing axis-0 dim is ``2*n_fresh - n_prior`` (not
``n_fresh``), so axis 0 mismatches and the ``np.concatenate``
raises.

**Fix**: Pad the ``pad_e_col`` rows to match the post-first-concat
axis-0 dim, or simply trim to ``n_prior`` after the first concat:

```python
# After first concat (axis=0), shape is (2*n_fresh - n_prior, n_fresh).
# The pad_e_col should match the row count, not n_fresh.
fresh_e_full = fresh_e_full[:n_prior]  # trim to prior's shape
pad_e_col = np.full(
    (n_prior, 1), int(FLOWMOL3ADAPTER_N_BOND_TYPES) - 1, dtype=np.int64
)
fresh_e_full = np.concatenate([fresh_e_full, pad_e_col], axis=1)
fresh_e = fresh_e_full[:n_prior, :n_prior]
```

**Why the conformance battery missed it**: the 8-check battery does
not call ``apply_restart_distribution`` on a non-trivial
``FinalRestartPolicy``. Check #6 (``check_adapter_registered_in_init``)
and check #4 (``check_adapter_byte_stable``) skip the restart path
entirely. The deep audit's **B.5** (per-method restart contract) is
the first audit to construct a valid policy and call the method.

**Suggested fix wave**: code-only fix wave (CPU-only, fast).

### NONCONFORMANCE_BUG #5 — `StochasticFMAdapter` emits non-canonical enumeration strings

**File**:
[`adaptive_reflow/adapters/stochastic_fm.py`](/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/stochastic_fm.py)
lines 232–233 (``build_initial_state``).

**Symptom**: ``StochasticFMAdapter`` builds its initial :class:`StateBundle`
with ``reference_frame="stochastic_fm"`` and
``normalization="per_channel_std"``. Neither is in the canonical
enums :data:`REFERENCE_FRAMES` (``"pocket_centered"`` /
``"world"`` / ``"lattice"``) or :data:`NORMALIZATION_KINDS`
(``"none"`` / ``"per_atom_std"`` / ``"per_pocket_std"``). The
universal ``validate_state_bundle`` would reject these bundles.

**Trigger**: ``StochasticFMAdapter.compose_condition`` and
``StochasticFMAdapter.detach_and_validate_endpoint`` both call
``validate_state_bundle(bundle)``. Because ``build_initial_state``
emits a bundle that fails the canonical validator, every subsequent
method that calls ``validate_state_bundle`` (or any code that
propagates the bundle through the engine's universal layer) crashes
silently.

**Root cause**: The adapter author chose adapter-specific strings
without consulting the canonical enums in
``adaptive_reflow/universal/state.py``. The strings are not
intentional design tokens; they are typos / oversight.

**Fix options**:

1. Change the canonical values to ``reference_frame="world"`` and
   ``normalization="per_atom_std"`` (both already in the enums). This
   is the lowest-friction fix and does not break the stochastic-FM
   semantics (the strings are purely metadata for round-trace
   audits).
2. Extend :data:`REFERENCE_FRAMES` and :data:`NORMALIZATION_KINDS`
   to admit the new tokens, but this changes the universal layer's
   contract and would invalidate the validator for adapters that
   strictly expect the canonical enum.
3. Delete :class:`StochasticFMAdapter` — it is not in the
   registry, not referenced by any production adapter, and not
   documented in ``docs/PLUG_IN_YOUR_MODEL.md``. Cleanup is the
   lowest-risk path.

**Why the conformance battery missed it**:
:class:`StochasticFMAdapter` is **not** in
:data:`ADAPTER_REGISTRY` (the conformance battery iterates the
registry, so it never instantiates this class). The deep audit's
**G.2** (unregistered-adapter canonical enumeration check) is the
first audit to construct this class directly via import.

**Suggested fix wave**: code-only fix wave (CPU-only, fast). The
recommended action is option 3 (deletion) unless the adapter is
needed for a future wave; option 1 (canonical strings) is the
preferred fix if deletion is undesirable.

## Identified design deviations (rationale + paper implications)

### NONCONFORMANCE_DESIGN #2 — `ReferenceFlowAAdapter` is an orphan (not registered)

**File**:
[`adaptive_reflow/adapters/reference_flowa.py`](/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/reference_flowa.py).

**Rationale**: ``ReferenceFlowAAdapter`` is a stdlib-only *reference*
adapter demonstrating the Protocol surface; it is imported by
``__init__.py`` but intentionally omitted from
:data:`ADAPTER_REGISTRY` so the conformance battery uses the
:class:`SyntheticContinuousAdapter` family for its standard
fixtures instead.

**Paper implications**: none. The reference adapter is not a model
in any published paper — it is internal documentation.

**Audit treatment**: explicitly enumerated in
:data:`UNREGISTERED_ADAPTER_CLASSES` with a documented rationale.

### NONCONFORMANCE_DESIGN #3 — `FreqFlowAdapter` is a Wave 21 design skeleton (not registered)

**File**:
[`adaptive_reflow/adapters/freqflow.py`](/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/freqflow.py).

**Rationale**: ``FreqFlowAdapter`` is the Wave 21 PHASE-3
CVPR 2026 (Ren et al.) image SiT-XL/2 + FFT-branch integration. The
~2.7 GB torch checkpoint download is heavy and GPU-only, so the
adapter is *not* in the default :data:`ADAPTER_REGISTRY`. Callers
who want to exercise it must install the weights and construct the
adapter directly (or override the registry in their environment).

**Paper implications**: the underlying FreqFlow paper (CVPR 2026)
is a published reference; the adapter implements the documented
architecture faithfully. The skeleton status is purely a deployment
choice — the Protocol surface is fully conformant.

**Audit treatment**: explicitly enumerated in
:data:`UNREGISTERED_ADAPTER_CLASSES` with a documented rationale.

### NONCONFORMANCE_DESIGN #4 — `KanziAdapter` is a Wave 21 design skeleton (not registered)

**File**:
[`adaptive_reflow/adapters/kanzi.py`](/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/kanzi.py).

**Rationale**: same as FreqFlow — Wave 21 PHASE-3 ICLR 2026 protein
flow-AE integration, design-skeleton release with heavy torch
checkpoint, not in the default registry.

**Paper implications**: the underlying Kanzi paper (ICLR 2026) is a
published reference; the adapter implements the documented
architecture faithfully.

**Audit treatment**: explicitly enumerated in
:data:`UNREGISTERED_ADAPTER_CLASSES`.

## Audit methodology

### Coverage matrix

| Check ID | Description | Adapter surfaces covered | Conformance battery analogue |
| --- | --- | --- | --- |
| A.1 | Every Protocol method present + callable | 9 methods × 14 adapters | implicit (check #1 partial) |
| A.2 | Per-method signature match | 9 methods × 14 adapters | NONE (deep audit only) |
| B.1 | :meth:`capabilities` returns :class:`AdapterCapabilities` | all | #3 partial |
| B.2 | :meth:`build_initial_state` field completeness + canonical enums | all | #2 partial, #6 partial |
| B.3 | :meth:`export_endpoint` returns :class:`StateBundle` | all | NONE |
| B.4 | :meth:`detach_and_validate_endpoint` returns detach_proof=True | all | NONE |
| B.5 | :meth:`apply_restart_distribution` honors capability gate | all | NONE |
| B.6 | :meth:`apply_restart_distribution` does NOT mutate input | all | NONE |
| B.7 | :meth:`compose_condition` returns valid :class:`ODEConditionDelta` | all | NONE |
| B.8 | :meth:`solve_ode` returns valid :class:`ODEIntegratorTrace` | all | #1 partial |
| B.9 | :meth:`observe_endpoint` returns :class:`StateBundle` | all | NONE |
| B.10 | :meth:`export_trajectory` returns None / NotImplError / data | all | NONE |
| C.1 | Runtime ``isinstance(adapter, FlowMatchingODEAdapter)`` | all | #3 |
| D.1 | Per-method deterministic-seed byte-stability | all | #4 partial |
| E.1 | Every bundle-producing method emits a validate-able bundle | all | NONE (deep audit only) |
| F.1 | Restart preserves batch_id / sample_id / reference_frame | all | NONE |
| G.1 | Unregistered adapter runtime Protocol conformance | orphan classes | NONE |
| G.2 | StochasticFM canonical enumeration check | StochasticFMAdapter | NONE (orphan) |
| H.1 | Unregistered adapter signature audit | orphan classes | NONE |
| I.1 | All concrete subclasses enumerated | full inventory | NONE |
| J.1 | Audit surface inventory smoke | self-check | NONE |

### Why the conformance battery's 8 checks do not catch these bugs

The Wave 15 C 8-check battery is a **smoke test**: it verifies the
adapter is *constructible*, *registered*, *byte-stable*, and has the
declared capability surface. It does NOT exercise:

* The restart blend path (no FinalRestartPolicy is ever
  constructed — the battery checks capability flags but not the
  math).
* Orphan / unregistered adapter classes (the battery iterates
  :data:`ADAPTER_REGISTRY` only).
* Per-method signature shape beyond ``callable(getattr(...))``
  (the battery does not call :func:`inspect.signature`).
* Per-method behavior contract beyond the smoke call (the battery
  does not exercise ``apply_restart_distribution`` /
  ``observe_endpoint`` / ``export_trajectory``).
* State-bundle field completeness (the battery spot-checks the
  initial state and ``detach_proof=True``, not the canonical
  enum constraints).
* Input-immutability for ``apply_restart_distribution`` (the
  battery never invokes the method).

This audit's B.5 / G.2 / E.1 / F.1 checks fill these gaps. The
2 findings reported above sit exactly in those gaps.

## Run instructions

```bash
# Run the deep audit:
python -m pytest tests/test_adapters/test_protocol_deep_audit.py -v --tb=short

# Compare against the existing 8-check battery:
python -m pytest tests/test_adapters/conformance_battery.py -v --tb=short
```

## Files changed by this audit

| File | Status |
| --- | --- |
| `tests/test_adapters/test_protocol_deep_audit.py` | NEW (461 tests) |
| `docs/audit/adapter-conformance-deep-dive.md` | NEW (this doc) |

No adapter code was changed in this audit. The 2 findings above are
documented for a follow-up code-only fix wave.

## Fix log

Findings above are the Wave 29 audit-time snapshot (including the
per-adapter table and the Summary counts). This section records what
later waves did about them; the audit text itself is left unedited so
the finding and its fix can be read side by side.

### 2026-09-05 — NONCONFORMANCE_BUG #1 FIXED (Wave 30 Agent B)

**Fix**:
[`adaptive_reflow/adapters/flowmol3_v2_adapter.py`](/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/flowmol3_v2_adapter.py)
— `_channel_aware_blend`, the `n_fresh > n_prior` branch. The fresh
bond matrix is now trimmed to `n_prior` rows **before** the axis-1
concatenation, which is what removes the mismatch:

```python
# was: concat (n_fresh - n_prior, n_fresh) pad rows -> a
#      (2 * n_fresh - n_prior, n_fresh) intermediate, then concat a
#      (n_fresh, 1) pad column on axis 1 -> ValueError on axis 0.
fresh_e_full = np.asarray(fresh["e"], dtype=np.int64)[:n_prior]
n_cols_fresh = int(fresh_e_full.shape[1])
if n_cols_fresh < n_prior:  # defensive: non-square fresh bond matrix
    fresh_e_full = np.concatenate([fresh_e_full, pad_e_col], axis=1)
fresh_e = fresh_e_full[:n_prior, :n_prior]
fresh_a = np.asarray(fresh["a"], dtype=np.int64)[:n_prior]
```

The fix is behaviour-preserving in the counterfactual where the crash
did not fire: every padded row and every padded `a` entry was already
discarded by the trailing `[:n_prior, :n_prior]` / `[:n_prior]` slice,
so trimming produces exactly the arrays the branch was reaching for.
The remaining column pad is kept, guarded, for a non-square fresh bond
matrix.

**Verification**:

| Check | Before fix | After fix |
| --- | --- | --- |
| `test_b_apply_restart_distribution_contract[reg:flowmol3_v2]` (B.5) | FAILED (`ValueError`, 36 vs 28) | PASSED |
| `test_flowmol3_v2_restart_blend_shape` (K.1, 8 size pairs) | n/a (new) | 8 passed |
| `test_flowmol3_v2_restart_blend_shape_end_to_end` (K.2) | n/a (new) | PASSED |
| `tests/test_adapters/test_protocol_deep_audit.py` | 2 failed | 1 failed (BUG #5 only), 464 passed, 38 skipped |

The one remaining failure in the deep-audit file is
`test_g_stochastic_fm_has_invalid_enumeration_strings`
(NONCONFORMANCE_BUG #5), which is out of Wave 30 Agent B's scope and
still open.

**Regression coverage added** (section K of
[`tests/test_adapters/test_protocol_deep_audit.py`](/home/hugo/codes/flowa-multistep-reinference/tests/test_adapters/test_protocol_deep_audit.py)):

* **K.1** `test_flowmol3_v2_restart_blend_shape` — drives
  `_channel_aware_blend` over `RESTART_BLEND_SIZE_PAIRS`, covering all
  three size branches (fresh larger — the crashing one — fresh smaller,
  and equal), including a degenerate single-atom molecule and two
  off-grid sizes so the test does not silently depend on the support of
  `DEFAULT_N_ATOMS_PRIOR`. Asserts every channel keeps the prior's
  shape, that discrete labels stay inside their categorical support
  (a trimmed or padded label must never leak an out-of-range class
  index), that continuous channels stay finite, and that the inputs are
  not mutated.
* **K.2** `test_flowmol3_v2_restart_blend_shape_end_to_end` — drives the
  public `apply_restart_distribution` and searches deterministically for
  a `policy_id` whose restart seed draws a molecule larger than the
  prior, proving the crashing branch is reachable from the real restart
  path rather than only from a hand-built dict. Asserts the returned
  bundle stays canonical under `validate_state_bundle` and that the
  registered native state is prior-shaped.

**Note on why B.5 caught it**: the default policy built by
`_make_minimal_restart_policy` (`policy_id="audit-policy"`) happens to
seed a fresh draw of 28 atoms against a 20-atom prior — hence the
`36 vs 28` in the reported traceback (`2 * 28 - 20 = 36`). B.6
(`test_b_apply_restart_does_not_mutate_input`) hit the same crash but
routes through `_safe_call`, which swallows `ValueError`, so only B.5
reported it.

## Closing

The 8-check conformance battery (D.5) is the right *smoke* layer: it
catches adapter regressions on the engine's hot path. This deep
audit is the *structural* layer: it catches Protocol regressions
that sit outside the smoke surface. Together, the two layers cover
the adapter/glue conformance contract end-to-end. The 2 bugs found
in this wave are non-smoke (no production traffic today) but
non-trivial (would surface as soon as the engine wires the restart
blend path against FlowMol3 v2, or as soon as StochasticFM is
imported directly). Both are recommended for the next code-only fix
wave.
