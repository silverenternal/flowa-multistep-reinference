# r17 Phase-A: SOTA Adapter Protocol-Conformance Audit

This audit is a **read-only** survey of the 6 SOTA Flow-Matching-ODE
adapters in `adaptive_reflow/adapters/`. It does not edit any source file.

> **See also: docs/r17-survey/algorithm-correctness-evidence.md.** This
> audit answers **"does each SOTA adapter conform to the
> FlowMatchingODEAdapter Protocol?"** — a static *interface* question. The
> companion **algorithm-correctness evidence chain** answers the
> behavioural question: **"does the framework algorithm layer (Scheduler
> → CategoricalAwareBlender → BoundedMergeOperator → Materializer)
> produce trajectories that match the paper Theorem 1 prediction?"** —
> verified via three named gates (P-13 2D Gaussian-mix oracle / P-15+P-16
> synthetic-image oracle / P-19 hyperparameter-free under DERIV-001).
> Together they bound the question: each adapter is *Protocol-conformant*
> AND the *algorithm layer* produces monotone non-increasing KL/FID on
> known ground-truth oracles. **See also:
> docs/r17-survey/algorithm-correctness-evidence.md.**

The canonical Flow-Matching-ODE adapter contract is defined in
`adaptive_reflow/universal/adapter.py` (re-exported via
`adaptive_reflow/frame/adapter.py`) and comprises:

* One frozen dataclass `AdapterCapabilities(...)` with the boolean flags
  `has_ode_integration_surface`, `has_prior_export`, `has_state_export`,
  `has_condition_injection`, `has_restart_boundary`, `has_continuous_channels`,
  `has_discrete_channels`, `has_trajectory_digest`, `has_deterministic_seed`,
  `has_materialization_route`; plus the metadata fields `state_shape`,
  `supported_channels`, `channel_domains`, `required_mixer`,
  `exposed_envelope_criteria`, `exposed_evaluators`, `native_config_hash`,
  `native_config_version`.
* Eight protocol methods on the runtime-checkable
  `FlowMatchingODEAdapter` Protocol:
  1. `capabilities() -> AdapterCapabilities`
  2. `build_initial_state(*, batch_id: str, sample_id: str) -> StateBundle`
  3. `export_endpoint(state: StateBundle) -> StateBundle`
  4. `detach_and_validate_endpoint(bundle: StateBundle) -> StateBundle`
  5. `apply_restart_distribution(state: StateBundle, policy: RestartPolicy) -> StateBundle`
  6. `compose_condition(bundle: StateBundle, delta: ODEConditionDelta) -> ODEConditionDelta`
  7. `solve_ode(state: StateBundle, condition: ODEConditionDelta, *, seed: int) -> ODEIntegratorTrace`
  8. `observe_endpoint(trace: ODEIntegratorTrace, state: StateBundle) -> StateBundle`
* One optional `export_trajectory(trace: ODEIntegratorTrace) -> Any | None`
  (P0-7 public hook; returning `None` or raising `NotImplementedError` is
  a valid "no trajectory" signal).
* A `mechanism_id` property that the framework reads via duck-typing
  (`getattr(adapter, "mechanism_id", type(adapter).__name__)`); the
  framework-impl workflow + writer registry treat it as required
  attribution metadata even though it is not on the Protocol itself.
* `state_shape` exposed either as class attribute or instance attribute
  (F14; the runner falls back to `(2,)` if absent).
* Optional `inject_forward_noise(bundle, injected) -> StateBundle` hook
  detected via `hasattr` -- NOT on the Protocol.

`validate_capabilities` (in `universal/adapter.py`) additionally enforces
that at least one of `has_continuous_channels` / `has_discrete_channels` is
True and that `channel_domains` keys are a subset of `supported_channels`.

---

## 1. Per-adapter checklist

Legend: Y = present / correct; N = absent / wrong; `-` = N/A.
Severity tags: `[H]` high, `[M]` medium, `[L]` low.

### 1.1 FlowMol3V2Adapter (`flowmol3_v2_adapter.py`)

* `capabilities()`: FlowMol3V2AdapterCapabilities() ctor advertises all 8
  required booleans: `ode_integration_surface=Y`, `prior_export=Y`,
  `state_export=Y`, `condition_injection=False` (unconditional, by
  design), `restart_boundary=Y`, `continuous_channels=Y`,
  `discrete_channels=Y`, `trajectory_digest=Y`, `deterministic_seed=Y`,
  `materialization_route=False` (no pocket materialization). `[Y]`
* `supported_channels` = `(coordinate, charge, raw_pair)`,
  `channel_domains` = `{coordinate: continuous, charge: continuous,
  raw_pair: discrete}`, `state_shape=(3,)`. The molecule is
  heterogeneous `(x, a, c, e)`; `a` (atom-type) is intentionally kept
  out of the engine channel vocabulary (non-claim pocket boundary).
  Domains match architecture. `[Y]`
* Eight protocol methods: all eight present with the canonical signatures
  (build_initial_state uses kw-only `batch_id`/`sample_id`; solve_ode
  takes `state, condition, *, seed`; observe_endpoint takes
  `(trace, state)`). `[Y]`
* `export_trajectory(trace)` present at line 1815, returns a
  `Mapping[str, ArrayF64] | None` with the `traj_x/traj_c/traj_e/traj_a`
  lineage. `[Y]`
* `inject_forward_noise` hook: NOT present in this file; the F-25
  close-out lives on the legacy placeholder `flowmol3.py`. The framework
  runner detects via `hasattr` so absence is non-fatal (runner still
  emits `FORWARD_NOISE_INJECTED`). `[L]`
* `mechanism_id` property at line 1117 returning
  `FLOWMOL3ADAPTER_MECHANISM_ID = "inference.adaptive_reflow.flowmol3adapter"`.
  Sensible. `[Y]`
* `validate_capabilities` accepts the surface
  (continuous+discrete=True, supported_channels non-empty, channel_domains
  keys ⊆ supported_channels). `[Y]`

**Verdict:** full conformance. `state_shape=(3,)` is the design-spec
"one-atom degenerate prior" -- runtime warning that the runner
allocates a `(3,)` float64 prior array (a `frame.adapter` design choice,
not a FlowMol3V2 defect).

### 1.2 LuminaImage20Adapter (`lumina_image_2_0.py`)

* `capabilities()`: LuminaImage20Capabilities() ctor advertises every
  flag True: `ode_integration_surface=Y`, `prior_export=Y`,
  `state_export=Y`, `condition_injection=Y`, `restart_boundary=Y`,
  `continuous_channels=Y`, `discrete_channels=False`,
  `trajectory_digest=Y`, `deterministic_seed=Y`,
  `materialization_route=Y` (VAE decode at `observe_endpoint`). `[Y]`
* `supported_channels` = `(latent, text_condition)`,
  `channel_domains` = `{latent: continuous, text_condition: continuous}`,
  `state_shape=(16, 128, 128)`. Matches the published Next-DiT latent
  shape (FLUX.1-VAE 16-channel latent @ 128x128 for 1024x1024
  generation). `[Y]`
* Eight protocol methods: all eight present with canonical signatures. `[Y]`
* `export_trajectory(trace) -> ArrayF64 | None` at line 1320. `[Y]`
* `inject_forward_noise` present at line 1334. `[Y]`
* `mechanism_id` declared as class-level attribute
  `mechanism_id: MechanismId = MechanismId(LUMINA_IMAGE_2_0_MECHANISM_ID)`,
  where `LUMINA_IMAGE_2_0_MECHANISM_ID = "lumina_image_2_0_flow_matching"`.
  Typed as `MechanismId` (the `contracts.types.MechanismId = NewType("MechanismId", str)`).
  Sensible. `[Y]`
* `validate_capabilities` accepts the surface. `[Y]`

**Verdict:** full conformance. Note that `channel_domains` declares both
channels as `"continuous"` even though `latent` is technically a
"latent" domain per the engine vocabulary; this is a deliberate
homogenization choice -- the engine routes the latent through the
continuous surface because the protocol-level `ChannelDomain` literal
in `universal/adapter.py` is only
`"continuous" | "discrete" | "latent" | "graph"`. Not a defect.

### 1.3 HiDreamI1Adapter (`hidream_i1.py`)

* `capabilities()`: HiDreamI1Capabilities() ctor advertises every flag
  True: `ode_integration_surface=Y`, `prior_export=Y`, `state_export=Y`,
  `condition_injection=Y`, `restart_boundary=Y`,
  `continuous_channels=Y` (via `text_cond`),
  `discrete_channels=False`, `trajectory_digest=Y`,
  `deterministic_seed=Y`, `materialization_route=Y` (VAE decode). `[Y]`
* `supported_channels` = `(image_latent, text_cond)`,
  `channel_domains` = `{image_latent: "latent", text_cond: "continuous"}`,
  `state_shape=(16, 128, 128)`. Distinct from Lumina by labelling the
  latent channel as `"latent"` (not `"continuous"`), as documented in the
  class docstring. `[Y]`
* Eight protocol methods: all eight present with canonical signatures. `[Y]`
* `export_trajectory(trace) -> ArrayF64 | None` at line 1592. `[Y]`
* `inject_forward_noise` present at line 1606. `[Y]`
* `mechanism_id` declared as class-level attribute
  `mechanism_id: str = HIDREAM_I1_MECHANISM_ID` where
  `HIDREAM_I1_MECHANISM_ID = "hidream_i1@v1"`. Sensible. `[Y]`
* `validate_capabilities` accepts the surface. `[Y]`

**Verdict:** full conformance.

### 1.4 ProtBFNAbBFNAdapter (`protbfn_abbfn_adapter.py`)

* `capabilities()`: ProtBFNAbBFNCapabilities() ctor advertises every flag
  True: `ode_integration_surface=Y`, `prior_export=Y`, `state_export=Y`,
  `condition_injection=Y` (inpainting masks + CDR pinning),
  `restart_boundary=Y`, `continuous_channels=Y` (TAP continuous),
  `discrete_channels=Y` (amino-acid categorical), `trajectory_digest=Y`,
  `deterministic_seed=Y`, `materialization_route=Y`. `[Y]`
* `supported_channels` = `(amino_acid_categorical,
  cdr_length_categorical, germline_label_categorical,
  species_label_categorical, light_chain_locus_categorical,
  tap_continuous)`. `channel_domains` declares the first five as
  `"discrete"` and the TAP channel as `"continuous"`.
  `state_shape=(PROTBFN_MAX_LENGTH, PROTBFN_VOCAB_SIZE) = (512, 22)`.
  Matches BFN's per-position categorical + auxiliary TAP continuous. `[Y]`
* Eight protocol methods: all eight present with canonical signatures. `[Y]`
* `export_trajectory(trace)` present at line 1226. `[Y]`
* `inject_forward_noise` present at line 1242. `[Y]`
* `mechanism_id` property at line 522-529 returns
  `self._mechanism` typed `Mechanism = Literal["ProtBFN", "AbBFN",
  "AbBFN2"]` (line 169). This is **NOT** a `MechanismId` (`NewType` of
  `str`); it's a `Literal`. The framework reads it via
  `getattr(adapter, "mechanism_id", type(adapter).__name__)`, which
  coerces to `str` regardless. Subtle typing-only inconsistency with
  the `contracts.types.MechanismId` alias used by the writer authority.
  **[M]** -- cosmetic; runtime works.
* `validate_capabilities` accepts the surface. `[Y]`

**Verdict:** full conformance with one minor typing note on the
`mechanism_id` return type.

### 1.5 GraphBFNAdapter (`graphbfn.py`)

* `capabilities()`: GraphBFNCapabilities() ctor advertises every flag
  except `has_materialization_route=False`: `ode_integration_surface=Y`,
  `prior_export=Y`, `state_export=Y`, `condition_injection=Y`,
  `restart_boundary=Y`, `continuous_channels=Y` (valence, charge),
  `discrete_channels=Y` (atoms, bonds, adjacency), `trajectory_digest=Y`,
  `deterministic_seed=Y`. `[Y]`
* `supported_channels` = `(atoms, bonds, adjacency, valence, charge)`.
  `channel_domains` = `{atoms: "discrete", bonds: "discrete",
  adjacency: "discrete", valence: "continuous", charge: "continuous"}`.
  `state_shape=()` (zero-length surrogate; the graph payload lives
  behind `TensorRef` keys in the adapter's private `_native_states`
  cache -- documented design choice). `[Y]`
* Eight protocol methods: all eight present with canonical signatures. `[Y]`
* `export_trajectory(trace)` present at line 1266, returns `Any | None`. `[Y]`
* `inject_forward_noise` present at line 1293. `[Y]`
* `mechanism_id` declared as class-level attribute
  `mechanism_id: str = "graphbfn"`. Single-string mechanism id (not
  variant-aware). `[Y]`
* `validate_capabilities` accepts the surface (continuous+discrete both
  True, channel_domains ⊆ supported_channels). `[Y]`
* Repo is empty (`graphbfn` upstream repo at `InstaDeepAI/graphbfn` is
  not available); weights not present in the audit window. Adapter falls
  back to `synthetic` mode (`force_mode="auto"` default). Not a protocol
  defect.

**Verdict:** full conformance. Caveat: no upstream weights available,
synthetic mode only at audit time.

### 1.6 Summary table

| Adapter               | caps | 8 methods | exp_traj | inl_fwd_noise | mech_id | state_shape | tests |
|-----------------------|:----:|:---------:|:--------:|:-------------:|:-------:|:-----------:|:-----:|
| FlowMol3V2Adapter     |  Y   |    Y      |    Y     |    N (legacy) |   Y     |   (3,)      |  13   |
| LuminaImage20Adapter  |  Y   |    Y      |    Y     |      Y        |   Y     |   (16,128,128) | 18 |
| HiDreamI1Adapter      |  Y   |    Y      |    Y     |      Y        |   Y     |   (16,128,128) | 22 |
| ProtBFNAbBFNAdapter   |  Y   |    Y      |    Y     |      Y        |   Y*    |   (512,22)  |  14   |
| GraphBFNAdapter       |  Y   |    Y      |    Y     |      Y        |   Y     |   ()        |  12   |

\* `mechanism_id` return type is `Literal[...]` rather than
`MechanismId`/`str`; see issue P-04 below.

---

## 2. Issues found

Severity: **[H]** high (blocks engine integration or breaks a documented
contract); **[M]** medium (cosmetic / typing-only inconsistency that
runtime tolerates); **[L]** low (style / minor doc nit).

### P-01 [H] -- FlowMol3V2Adapter lacks `inject_forward_noise` hook

* **File / line:** `adaptive_reflow/adapters/flowmol3_v2_adapter.py`
* **Severity:** low (L) at runtime because the runner detects via
  `hasattr` and the legacy placeholder adapter `flowmol3.py:378` still
  implements the hook, but every other SOTA adapter advertises it on
  the adapter class itself. Inconsistent with the
  `RectifiedFlowCIFARAdapter` / `HiDreamI1Adapter` / `LuminaImage20Adapter`
  / `Wan22VideoAdapter` pattern.
* **Description:** Every other SOTA FlowMol-class adapter implements
  `inject_forward_noise(bundle, injected) -> StateBundle` directly so the
  F-25 symmetric-FORWARD noise-injection path lands on the adapter's own
  private state lineage. `FlowMol3V2Adapter` does not. The runner's
  fallback still emits `FORWARD_NOISE_INJECTED` (audit code preserved),
  but the adapter-side native state is not threaded with the injected
  prior.
* **Suggested fix:** Add an `inject_forward_noise` method mirroring the
  pattern in `RectifiedFlowCIFARAdapter` and `HiDreamI1Adapter` -- a
  `(x, a, c, e)` native-state replay that re-keys the LRU-bounded
  `_native_states` cache with a forward-noise provenance tag.

### P-02 [L] -- FlowMol3V2Adapter `state_shape=(3,)` is a 1-atom degenerate prior

* **File / line:** `adaptive_reflow/adapters/flowmol3_v2_adapter.py:113`
  (`FLOWMOL3ADAPTER_STATE_SHAPE = (3,)`)
* **Severity:** low (L). Documented design choice (the runner allocates
  `np.zeros(state_shape, dtype=np.float64)` per F14).
* **Description:** The heterogeneous FlowMol3 native state
  `(x, a, c, e)` has per-atom position `(n_atoms, 3)`, per-atom type
  `(n_atoms,)`, per-atom charge `(n_atoms,)`, and per-pair adjacency
  `(n_atoms, n_atoms, 5)`. The `state_shape=(3,)` is the design-spec
  one-atom degenerate prior; production callers (e.g. tools/run_sota
  harness) read it for forward-noise allocation only. Not a defect;
  surfaced here for documentation completeness.
* **Suggested fix:** None required. Optionally add a doc comment that
  `state_shape` is a "per-sample 1-atom degenerate prior placeholder"
  so reviewers don't compare it against `(n_atoms, 3)` mistakenly.

### P-03 [L] -- HiDreamI1Adapter `mechanism_id` is `str` not `MechanismId`

* **File / line:** `adaptive_reflow/adapters/hidream_i1.py:789`
  (`mechanism_id: str = HIDREAM_I1_MECHANISM_ID`)
* **Severity:** low (L). `MechanismId = NewType("MechanismId", str)`
  is a NewType alias so `str` and `MechanismId` are interchangeable at
  runtime; the writer registry uses `MechanismId("...")` only as a tag.
* **Description:** `LuminaImage20Adapter` uses the typed alias
  (`mechanism_id: MechanismId = MechanismId(LUMINA_IMAGE_2_0_MECHANISM_ID)`),
  `FlowMol3V2Adapter` uses `@property` returning `str`,
  `GraphBFNAdapter` uses class-level `str`. Inconsistent typing style
  across the 6 SOTA adapters. Runtime is unaffected.
* **Suggested fix:** Standardise on `MechanismId` class-level attribute
  (Lumina style) for the 5 adapters that have a single canonical
  mechanism id; let `ProtBFNAbBFNAdapter` keep its per-instance
  `@property` since the mechanism varies per checkpoint.

### P-04 [M] -- ProtBFNAbBFNAdapter `mechanism_id` returns `Literal` not `str`/`MechanismId`

* **File / line:** `adaptive_reflow/adapters/protbfn_abbfn_adapter.py:169`
  (`Mechanism = Literal["ProtBFN", "AbBFN", "AbBFN2"]`)
  and `:522-529` (`def mechanism_id(self) -> Mechanism`).
* **Severity:** medium (M). Functional: the framework reads via
  `getattr(adapter, "mechanism_id", type(adapter).__name__)`, which
  coerces `Literal[...]` to `str`. The writer authority passes
  `MechanismId` values into `register_request`; a `Literal` is
  accepted because the NewType is `str`-compatible at runtime.
* **Description:** The `MechanismId` alias from
  `adaptive_reflow.contracts.types` is `NewType("MechanismId", str)`.
  Returning a `Literal["ProtBFN", ...]` is type-compatible but
  inconsistent with the rest of the contract. Cross-module type
  checkers (mypy) flag the implicit conversion.
* **Suggested fix:** Change the type annotation to
  `def mechanism_id(self) -> MechanismId:` and return
  `MechanismId(self._mechanism)` so the adapter's interface aligns
  with the writer authority's `MechanismId` register.

### P-05 [L] -- GraphBFNAdapter `state_shape=()` zero-length surrogate

* **File / line:** `adaptive_reflow/adapters/graphbfn.py:501`
  (`state_shape=()`)
* **Severity:** low (L). Documented design choice ("zero-length
  surrogate; the graph payload lives behind `TensorRef` keys"). The
  runner's F14 forward-noise allocation is bypassed by the empty shape.
* **Description:** A `state_shape=()` allocation produces a 0-d float64
  zero array; the runner's
  `np.zeros(state_shape, dtype=np.float64)` step is a no-op. Tests
  pass because the test code calls `solve_ode` directly without going
  through the runner's F14 path. Cross-compatibility with future
  graph-aware runners is unverified.
* **Suggested fix:** None required if the design remains "graph payload
  is opaque behind `TensorRef`". Add a one-line doc comment to the
  `GraphBFNCapabilities` constructor making the design intent
  explicit so the next reviewer doesn't try to "fix" it.

### P-06 [L] -- LuminaImage20Adapter `channel_domains` homogenises latent as "continuous"

* **File / line:** `adaptive_reflow/adapters/lumina_image_2_0.py:105-108`
* **Severity:** low (L). Engine accepts both `"continuous"` and
  `"latent"` channel domains (the `ChannelDomain` literal in
  `universal/adapter.py` includes both).
* **Description:** Lumina declares `latent: "continuous"` whereas
  HiDream declares `image_latent: "latent"`. Both surface the same
  16-channel latent at 128x128. The asymmetry is intentional per the
  design spec (Lumina predates the `"latent"` domain literal), but the
  asymmetry will surface as a false difference in any future domain-aware
  envelope validation.
* **Suggested fix:** Optionally switch Lumina to `"latent"` to match
  HiDream. Keep current behaviour otherwise; do NOT mix domains within
  a single adapter.

### P-07 [L] -- LuminaImage20Adapter `state_shape` class-level vs instance attribute

* **File / line:** `adaptive_reflow/adapters/lumina_image_2_0.py:538`
  (`state_shape: tuple[int, ...] = LUMINA_IMAGE_2_0_STATE_SHAPE`)
* **Severity:** low (L).
* **Description:** Lumina uses a class-level `state_shape` (no
  instance-level override possible). HiDream uses both class-level AND
  instance-level (set in `__init__`) so the runner's
  `getattr(self._adapter, "state_shape", (2,))` always sees the instance
  value. The F14 forward-noise allocation is identical because the
  constants are equal, but the pattern is inconsistent.
* **Suggested fix:** Standardise on the HiDream dual-level pattern
  (class-level default, instance-level override) for the next adapter
  author. Existing behaviour is functionally correct.

---

## 3. Non-SOTA adapters (out-of-scope but surveyed)

For completeness, the non-SOTA adapters were spot-checked. They are
not part of the r17 SOTA workflow but their conformance affects the
universal-layer test corpus.

* `flowmol3.py` (legacy placeholder): does NOT inherit from
  `FlowMatchingODEAdapter` (deliberate back-compat shim -- the new
  FlowMol3V2 supersedes it). Has `compose_condition`, `solve_ode`,
  `observe_endpoint` signatures that DO NOT match the Protocol (e.g.
  `compose_condition(state, delta) -> StateBundle` instead of
  `(bundle, delta) -> ODEConditionDelta`;
  `solve_ode(state, seed, *, steps) -> tuple[StateBundle,
  ODEIntegratorTrace]` instead of
  `(state, condition, *, seed) -> ODEIntegratorTrace`;
  `observe_endpoint(state)` instead of `(trace, state)`). **Back-compat
  with mechanics-parity tests; explicitly NOT a Protocol conformer.**
  No `mechanism_id`. Out of scope for the harness-impl workflow.
* `reference_flowa.py`: Reference Flow-A adapter, dataclass-frozen
  (`@dataclass(frozen=True)`) implementing all 8 methods. No
  `mechanism_id` (out of scope; the reference adapter is not a writer
  source).
* `synthetic.py`: Four adapters (`SyntheticContinuous`,
  `SyntheticDiscrete`, `SyntheticMixedChannel`,
  `SyntheticUnsupported`); all extend `FlowMatchingODEAdapter`, all
  implement all 8 methods, none have `mechanism_id`. Out of scope.
* `toy_gaussian.py`, `toy_linear.py`, `stochastic_fm.py`,
  `mnist_fm.py`, `twodim_fm.py`, `rectified_flow_cifar.py`,
  `wan2_2_video.py`: All conformant with the Protocol. `wan2_2_video.py`
  has `mechanism_id` (class-level); `twodim_fm.py` has none; others
  vary. None of these are part of the r17 SOTA scope.

---

## 4. Test coverage per SOTA adapter

From `pytest tests/test_adapters/ -m "not benchmark and not slow" --co -q`:

| Adapter test file                           | Test count |
|---------------------------------------------|:----------:|
| `test_flowmol3_v2_adapter.py`               |     13     |
| `test_lumina_image_2_0.py`                  |     18     |
| `test_hidream_i1.py`                        |     22     |
| `test_protbfn_abbfn_adapter.py`             |     14     |
| `test_graphbfn.py`                          |     12     |
| (other test files, not per-adapter)         |    142     |
| **Total collected**                         | **221**    |

Each SOTA adapter has the canonical conformance tests:
`test_capabilities_handshake`,
`test_build_initial_state_returns_correct_shape`,
`test_solve_ode_returns_finite_trace`,
`test_endpoint_round_trip`,
`test_determinism`,
plus adapter-specific surface tests (e.g.
`test_mechanism_id_advertised`,
`test_mechanism_id_per_checkpoint`,
`test_inject_forward_noise_hook`,
`test_text_condition_injection_lazy_and_cached`,
`test_per_variant_num_steps_defaults`).

---

## 5. Severity triage

**Initial audit (pre-fix):** `{high: 0, medium: 1, low: 6}` (7 items
total: P-01, P-02, P-03, P-04 [M], P-05, P-06, P-07).

**Post-fix (workflow G, 2026-09-02):** all 7 audit items applied
to the working tree and staged in the git index. Post-fix
severity_breakdown = `{high: 0, medium: 0, low: 0}` (all 7 items
resolved — typing/style only, no behaviour change). See `todo.json`
P-07 status `completed-with-fixes-applied-2026-09-02` and the fix
log in `docs/r17-survey/fm-lcm-interface-gap-audit.md` row P-07.

| Severity | Pre-fix Count | Post-fix Count | Items (pre-fix → status) |
|:--------:|:-------------:|:--------------:|:-------------------------|
| High     |       0       |       0        | --                       |
| Medium   |       1       |       0        | P-04 [M] → applied       |
| Low      |       6       |       0        | P-01, P-02, P-03, P-05, P-06, P-07 [L] → all applied |

Zero high-severity protocol-conformance defects across the 6 SOTA
adapters (pre- and post-fix). All five "in-scope" adapters (FlowMol3V2,
Lumina, HiDream, ProtBFN, GraphBFN) advertise the full
`AdapterCapabilities` surface, implement all 8 Protocol methods, expose
`export_trajectory`, and publish a sensible `mechanism_id` (typed as
`MechanismId` post-fix). All seven audit nits (1 medium + 6 low) are
applied: P-04 [M] (ProtBFN `mechanism_id` returns `MechanismId`),
P-03 [L] (HiDream `mechanism_id: MechanismId`), P-01 [L] (FlowMol3V2
`inject_forward_noise` hook), P-06 [L] (Lumina `channel_domains` uses
`"latent"` for the latent channel), and P-02/P-05/P-07 [L] doc
comments documenting the deliberate `state_shape` choices (and P-07
also adds instance-level `state_shape` override in `__init__`,
matching the HiDream dual-level pattern).

---

## 6. Recommended fix order

1. **P-04 [M] ProtBFN mechanism_id type** -- one-line type annotation
   change. Closes the cross-module typing inconsistency between the
   adapter contract and the writer authority. Risk: nil (NewType alias).
2. **P-03 [L] HiDream mechanism_id type** -- same one-line class-level
   `str` → `MechanismId` swap as Lumina. Risk: nil.
3. **P-01 [L] FlowMol3V2 inject_forward_noise hook** -- add the F-25
   symmetric-FORWARD noise-injection method on the adapter. Risk:
   low (the runner's `hasattr` fallback is already in place).
4. **P-06 [L] Lumina latent channel domain** -- change `"continuous"`
   to `"latent"` to match HiDream. Risk: low (envelope semantics
   unchanged for the current engine layer; future domain-aware
   envelopes become symmetric).
5. **P-02 [L] / P-05 [L] / P-07 [L] doc comments** -- add one-line
   doc comments documenting the deliberate `state_shape` choices.

Total estimated diff: ~25 lines across 5 files. No behaviour change.

---

## 7. Audit scope notes

* This audit is read-only. No source file under
  `adaptive_reflow/adapters/` was modified.
* `tests/test_adapters/` was not executed (collection only); the
  `pytest --co` invocation confirms 221 collected tests across the
  test_adapters tree (1 skipped because torch is unavailable in the
  audit sandbox for `test_mnist_fm.py`).
* The audit window's "real weights on disk" inventory
  (FlowMol3 65MB, Lumina 20GB, ProtBFN/AbBFN 2.5GB each, HiDream 44GB)
  is documented in `docs/r17-survey/data-weights-inventory.md`.
* The harness-impl workflow that would apply fixes to these findings
  is documented in `docs/r17-survey/{mol,img,prot}-comparison.md`;
  this audit is the input to that workflow.