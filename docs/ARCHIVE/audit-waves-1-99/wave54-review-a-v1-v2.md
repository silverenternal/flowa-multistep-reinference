# Wave 54 Agent A — READ-ONLY review of FlowMol3 v1 / v2 interface gap

**Date:** 2026-09-07
**Wave:** 54 Phase 1 reviewer
**Constraint:** READ-ONLY audit. No code changes. No commits.
**Goal:** Identify the exact interface gap between the v1 placeholder (`adaptive_reflow/adapters/flowmol3.py`) and the v2 real integration (`adaptive_reflow/adapters/flowmol3_v2_adapter.py`) so a Phase 2 fix can be designed interface-first (old preserved, new opt-in, byte-stable for v1).

---

## A.1 — Current v1 placeholder API surface (`FlowMol3Adapter`)

Class: `adaptive_reflow.adapters.flowmol3.FlowMol3Adapter` (line 627).
Decorator: `@implements(FlowMatchingODEAdapter)`.

| # | Method | Signature | Return | Source lines |
|---|--------|-----------|--------|--------------|
| 1 | `capabilities` | `(self) -> AdapterCapabilities` | capability token; `FlowMol3Capabilities` projected | 731 |
| 2 | `build_initial_state` | `(self, *, batch_id: str, sample_id: str) -> StateBundle` | hash-stable placeholder bundle with `(coordinate, charge, raw_pair)` channels | 734 |
| 3 | `export_endpoint` | `(self, state: StateBundle) -> StateBundle` | re-validates and returns input bundle | 779 |
| 4 | `detach_and_validate_endpoint` | `(self, bundle: StateBundle) -> StateBundle` | re-validates detach_proof=True | 789 |
| 5 | `apply_restart_distribution` | `(self, state, policy, *, nfe_budget=None) -> StateBundle` | blended bundle via framework-core `blend_graph_features`; NFE-adaptive gate (Wave 58) | 797 |
| 6 | `compose_condition` | `(self, bundle, delta: ODEConditionDelta) -> ODEConditionDelta` | null-condition injector annotation | 927 |
| 7 | `solve_ode` | `(self, state, condition: ODEConditionDelta, *, seed: int) -> ODEIntegratorTrace` | **hash-stable stub** (see A.4) | 966 |
| 8 | `observe_endpoint` | `(self, trace, state) -> StateBundle` | re-validates and returns input bundle | 996 |
| 9 | `observe` | `(self, trace, state, paper_quantities=None, *, strategies=(...), theta_before=None, theta_after=None) -> tuple[ObservationResult, ...]` | NEW (Wave 68 Phase 3) wraps `observe_endpoint` + `observe_entropy_reduction` into tagged tuple; supports `ENDPOINT_BUNDLE` + `POSITION_ENTROPY_REDUCTION` | 1009 |
| 10 | `observe_entropy_reduction` | `(self, trace, paper_quantities=None, *, theta_before=None, theta_after=None) -> dict[str, float]` | per-atom Shannon-entropy reduction; returns `{PER_POSITION_ENTROPY_REDUCTION: float}`; synthetic-mode fallback returns 0.0 | 1135 |
| 11 | `export_trajectory` | `(self, trace: ODEIntegratorTrace) -> Any` | **raises `NotImplementedError`** — v1 preserves no native trajectory (P0-7) | 1125 |
| 12 | `inject_forward_noise` | `(self, bundle, injected) -> StateBundle` | SHA-256 over noise provenance; P1-8 close | 1267 |

Plus the wrapper class:

| Symbol | Purpose |
|--------|---------|
| `FlowMol3Capabilities` (frozen dataclass, line 216) | capability token; `has_trajectory_digest=False`, `has_materialization_route=True` |
| `FlowMol3AtomTypeEntropyRestartPolicy` (line 419) | per-atom entropy restart policy; degrades to uniform `alpha=0.5` in v1 (no native-state cache) |
| `default_flowmol3_adapter(...)` (line 1365) | factory; kwargs include `force_mode ∈ {"synthetic", "real", "auto"}` (Wave 50 Agent A); only LOADS the ckpt envelope, does NOT swap the materializer |
| `_try_load_real_ckpt` (line 1306) | envelope-only ckpt loader |

**Total public methods on the class:** 12 (incl. `__init__` not counted).
**Total protocol surface (excluding legacy methods + Wave 68 wrap):** the 8-method `FlowMatchingODEAdapter` set + `inject_forward_noise` + the legacy observation trio.

---

## A.2 — Current v2 API surface (`FlowMol3V2Adapter`)

Class: `adaptive_reflow.adapters.flowmol3_v2_adapter.FlowMol3V2Adapter` (line 1493).
Decorator: `@implements(FlowMatchingODEAdapter)`.

| # | Method | Signature | Return | Source lines |
|---|--------|-----------|--------|--------------|
| 1 | `capabilities` | `(self) -> AdapterCapabilities` | `FlowMol3V2AdapterCapabilities` (frozen dataclass, line 1460); `has_trajectory_digest=True`, `has_materialization_route=False`, `has_condition_injection=False` | 1632 |
| 2 | `build_initial_state` | `(self, *, batch_id, sample_id) -> StateBundle` | samples real `(x, a, c, e)` native state via `_sample_native_state`; per-channel SHA-256 digest | 1873 |
| 3 | `export_endpoint` | `(self, state) -> StateBundle` | re-validates and returns input | 1978 |
| 4 | `detach_and_validate_endpoint` | `(self, bundle) -> StateBundle` | re-validates detach_proof=True | 1993 |
| 5 | `apply_restart_distribution` | `(self, state, policy: RestartPolicy) -> StateBundle` | **NOTE: NO `nfe_budget` kwarg** (positional only); channel-aware blend; bumps `source_round` (Wave 63 Agent 1 Bug B fix); requires native-state cache entry | 2014 |
| 6 | `compose_condition` | `(self, bundle, delta) -> ODEConditionDelta` | rejects channel-keyed deltas (`has_condition_injection=False`); passes through `num_steps` | 2160 |
| 7 | `solve_ode` | `(self, state, condition, *, seed: int) -> ODEIntegratorTrace` | **REAL integration** — dispatches to `_solve_ode_ctmc` (default), `_solve_ode_linear` (ablation), or `_solve_ode_upstream` (when `use_upstream=True` and model_kind="upstream_flowmol") | 2190 |
| 7a | `_solve_ode_ctmc` | `(self, state, condition, *, seed) -> ODEIntegratorTrace` | paper-correct CTMC path for discrete (a, e); linear-interpolant ODE for continuous (x, c) | 2702 |
| 7b | `_solve_ode_linear` | `(self, state, condition, *, seed) -> ODEIntegratorTrace` | pre-Stage-3 linear-interpolant ODE + greedy argmax | 2547 |
| 7c | `_solve_ode_upstream` | `(self, state, condition, *, seed) -> ODEIntegratorTrace` | end-to-end `FlowMol.sample` entrypoint (P-22 close) | 2266 |
| 8 | `observe_endpoint` | `(self, trace, state) -> StateBundle` | reads t=1 slice from cached `traj_x / traj_c / traj_e / traj_a` lineage; materialises endpoint bundle | 2994 |
| 9 | `observe` | `(self, trace, state, paper_quantities=None, *, strategies=(...), theta_before=None, theta_after=None) -> tuple[ObservationResult, ...]` | NEW (Wave 68 Phase 3) wraps `observe_endpoint` + the entropy shim (`_atom_type_logit_marginal_from_endpoint` / `_atom_type_logit_marginal_from_prior`); supports `ENDPOINT_BUNDLE` + `POSITION_ENTROPY_REDUCTION`; same skipping semantics as v1 | 3161 |
| 10 | `inject_forward_noise` | `(self, bundle, injected) -> StateBundle` | additive noise on `x` channel (one-atom degenerate + multi-atom fallback); audit-tagged | 2037 |
| 11 | `export_trajectory` | `(self, trace: ODEIntegratorTrace) -> Mapping[str, ArrayF64] | None` | **REAL trajectory**: returns `{traj_x, traj_c, traj_e, traj_a}` of shapes `(num_steps+1, n_atoms, 3)`, `(num_steps+1, n_atoms)`, `(num_steps+1, n_atoms, n_atoms)`, `(num_steps+1, n_atoms)`; closes P0-7 | 3446 |

**Missing in v2 (present in v1):**
- `observe_entropy_reduction` (legacy) — v2 only exposes `observe(...)` with `POSITION_ENTROPY_REDUCTION` (Wave 68 Phase 3).
- `inject_forward_noise` is present in both — but v2 uses different math (real-shape-aware).
- v1 has `_try_load_real_ckpt`; v2 has `_load_flowmol3_state_dict` + `_build_flowmol3_velocity_module` (heavier, lazy-torch).

**Missing in v1 (present in v2):**
- `solve_ode` does real integration (v1 is a hash stub — see A.4).
- `export_trajectory` returns real lineage (v1 raises `NotImplementedError`).
- `_solve_ode_ctmc` / `_solve_ode_linear` / `_solve_ode_upstream` (three backend dispatchers).
- `_atom_type_logit_marginal_from_endpoint` / `_atom_type_logit_marginal_from_prior` (entropy shim helpers).
- `_load_model` (lazy torch backend loader, line 1655).
- `mechanism_id` property + `model_metadata` property (line 1635, 1784).
- `use_upstream` / `upstream_import_error` properties (line 1607, 1618).
- `ctmc_enabled` class/instance toggle (line 1535).

**Factory:** `default_flowmol3adapter(backend, num_steps, weights_path, device, ctmc_enabled, force_mode)` (line 3477) — kwargs DIFFERENT shape than v1's factory (no `atom_type_entropy_restart_policy`, no `nfe_budget`, no `restart_min_nfe`).

**Total public methods on v2:** 11 + 6 private (`_solve_ode_*`, `_atom_type_logit_marginal_*`, `_load_model`, `_put_native_state`, `_velocity_field_ex`, `_velocity_field`, `_get_synthetic_weights`, `_loaded_model_kind`).
**v2-only properties:** 3 (`use_upstream`, `upstream_import_error`, `model_metadata`).

---

## A.3 — Protocol gap (v1 vs v2)

### A.3.1 Methods v1 has that v2 does NOT

| Method | Where (v1) | Why v2 lacks it | Interface implication |
|--------|-------------|-----------------|----------------------|
| `observe_entropy_reduction` (legacy) | `flowmol3.py:1135` | v2 replaced it with the `observe(...)` shim (Wave 68 Phase 3) that computes the same formula from cached `traj_a`. The legacy hook was never migrated. | **GAP**: metric helper `_extract_observation_legacy` at `run_real_ckpt_eval.py:1736` still calls `adapter.observe_entropy_reduction(...)`. For v2, this raises `AttributeError` → metric layer returns `BLOCKED` (`adapter_missing_observe_entropy_reduction`). The `hasattr(adapter, "observe_entropy_reduction")` check at line 1737 is the structural failure point. |
| `FlowMol3AtomTypeEntropyRestartPolicy` (public class) | `flowmol3.py:419` | v2 has its own restart path (`_channel_aware_blend` + native-state cache); the per-atom entropy policy is v1-side glue only. | v2 has no equivalent class. Not currently a metric-axis gap, but a documented difference. |
| `__init__` kwargs | `force_mode`, `real_ckpt_meta`, `nfe_budget`, `restart_min_nfe`, `atom_type_entropy_restart_policy` | v2's `__init__` takes `backend`, `num_steps`, `seed_offset`, `blender`, `weights_path`, `device`, `ctmc_enabled`, `use_upstream`, `upstream_repo_dir`. **No overlap** for the gate / restart kwargs. | **GAP**: v1's `FlowMol3Adapter(nfe_budget=10, restart_min_nfe=25)` (Wave 58 NFE-adaptive gate) has no v2 analog. When the eval pipeline wires v2 (Wave 66 wire), the gate kwargs are silently filtered out (see `_resolve_adapter` lines 942-946). |

### A.3.2 Methods v2 has that v1 does NOT

| Method | Where (v2) | Why v1 lacks it | Interface implication |
|--------|-------------|-----------------|----------------------|
| `solve_ode` (real) | `flowmol3_v2_adapter.py:2190` (CTMC / linear / upstream dispatch) | v1 is a **hash-based stub** by design (A.4) | **GAP**: v1's placeholder cannot produce a real FlowMol3 trajectory. The eval pipeline now wires v2 for `force_mode=real` so the real model integrates (Wave 66 close). |
| `export_trajectory` (real) | `flowmol3_v2_adapter.py:3446` | v1 raises `NotImplementedError` (line 1125) | **GAP**: any downstream consumer wanting the native `(x, a, c, e)` lineage cannot use v1. Currently only `_compute_flowmol3_real_atom_type_marginal` needs the trajectory; it lazy-imports v2 helpers. |
| `_solve_ode_ctmc` / `_solve_ode_linear` / `_solve_ode_upstream` | `flowmol3_v2_adapter.py:2702, 2547, 2266` | v1 has no integration at all | v1 cannot honour any of these dispatcher paths. |
| `_load_model` | `flowmol3_v2_adapter.py:1655` | v1's `_try_load_real_ckpt` is envelope-only | v1 records the ckpt loaded but never loads the tensors — the model never integrates. |
| `_atom_type_logit_marginal_from_endpoint` / `_atom_type_logit_marginal_from_prior` | `flowmol3_v2_adapter.py:3073, 3133` | v1 has no native-state cache, so no `traj_a` lineage to derive from | v1's `observe_entropy_reduction` synthesises a uniform fallback. v2's entropy reading is real. |
| `mechanism_id` / `model_metadata` | `flowmol3_v2_adapter.py:1635, 1784` | v1 has no `mechanism_id`; the registry entry is built by `flowmol3_registry_entry()` instead | Writer-authority mechanism ID contract — v1 never joins the registry's mechanism ID scheme. |
| `use_upstream` / `upstream_import_error` | `flowmol3_v2_adapter.py:1607, 1618` | v1 has no upstream path at all | v1 cannot host the §3.4 repair-plan hook. |
| `ctmc_enabled` (class + per-instance toggle) | `flowmol3_v2_adapter.py:1535, 1600` | v1 has no CTMC path | Ablation toggle lives only on v2. |

### A.3.3 Signatures that DIFFER (interface mismatch, not missing)

| Method | v1 signature | v2 signature | Interface implication |
|--------|--------------|--------------|----------------------|
| `apply_restart_distribution` | `(state, policy, *, nfe_budget=None)` — extra kwarg | `(state, policy)` — positional only, no `nfe_budget` | **GAP**: v1 has the Wave 58 NFE-adaptive gate; v2 doesn't honour the gate kwarg. A caller constructing v2 with `nfe_budget=10` from a v1-shaped factory would have the kwarg dropped silently (the factory in `_resolve_adapter` filters via `inspect.signature`). |
| `__init__` kwargs | `(atom_type_entropy_restart_policy, force_mode, real_ckpt_meta, nfe_budget, restart_min_nfe)` | `(backend, num_steps, seed_offset, blender, weights_path, device, ctmc_enabled, use_upstream, upstream_repo_dir)` | **GAP**: the two factories are not interchangeable. The Wave 50/66 wiring uses the per-model `_ADAPTER_FORCE_MODE_ALIAS` table + `inspect.signature` filtering to keep both reachable from a single dispatch site. |
| `solve_ode` trace return | `ODEIntegratorTrace(steps, accept_rate=1.0, native_state_digest=<hash>, integrator_config_hash=<hash>)` | `ODEIntegratorTrace(steps, accept_rate=1.0, native_state_digest=<trajectory digest>, integrator_config_hash=<hash of (backend, num_steps, seed, pinned_commit, weights_path, device)>)` | The shape is the same dataclass; the digest CONTENT differs. v1's digest is a hash of `(state.digest, seed, steps)`, v2's is a SHA over per-step lineage. **Both are valid `ODEIntegratorTrace`s**, but the metric helper's reading of `trace.native_state_digest` means downstream consumers cannot swap between them at the trace-digest layer (Bug C root-cause, Wave 65 Agent 2 fix lives in the metric helper, not the adapter). |
| `inject_forward_noise` noise provenance | SHA over `{kind, src_digest, injected_head[repr(float)]}` | `digest_state({kind, src_digest, noise_head, noise_x_first})` (separate helper) | Different digest formula — both v1 and v2 digests are stable but not cross-comparable. |

### A.3.4 Protocol-level surface

Both v1 and v2 declare:
- `@implements(FlowMatchingODEAdapter)` (the 8-method base protocol).
- v1 additionally `@implements(AdapterObservationProtocol)` (Wave 68 Phase 3, `flowmol3.py:626` line is on the class decorator; the `observe` method itself is at line 1009).
- v2 also `@implements(AdapterObservationProtocol)` (`flowmol3_v2_adapter.py:1492`; `observe` method at line 3161).

`assert_adapter_compliance` is enforced at import time (Wave 38 HIGH-4 fix). Both adapters pass.

---

## A.4 — Why v1 is a hash stub

The v1 `solve_ode` (lines 966-994) does NOT integrate any ODE. The placeholder returns a deterministic `ODEIntegratorTrace` whose `native_state_digest` and `integrator_config_hash` are SHA-256 hashes of `(state.native_state_digest, seed, steps)`.

**Hash function:**

```python
# _make_tensor_ref (flowmol3.py:286-300)
def _make_tensor_ref(label: str, **parts: Any) -> TensorRef:
    blob = repr((label, sorted(parts.items()))).encode("utf-8")
    return TensorRef(f"flowmol3:{hashlib.sha256(blob).hexdigest()[:16]}")
```

* Hash algorithm: SHA-256.
* Output: first **16 hex chars** (= 64 bits) of the digest, prefixed with `flowmol3:`.
* Encoding: `repr((label, sorted(parts.items())))` (deterministic Python repr).

**Return shape:**

```python
# flowmol3.py:983-994
new_digest = _make_tensor_ref(
    "post_step", source=state.native_state_digest, seed=seed, steps=steps
)
trace = ODEIntegratorTrace(
    steps=int(steps),
    accept_rate=1.0,
    native_state_digest=new_digest,
    integrator_config_hash=_make_tensor_ref(
        "integrator_config", seed=seed, steps=steps
    ),
)
```

The trace contains:
- `steps`: integer from `condition.delta_spec['num_steps']`.
- `accept_rate`: hard-coded `1.0` (no rejection sampling).
- `native_state_digest`: SHA prefix of `(state.digest, seed, steps)` — NOT the model's prediction.
- `integrator_config_hash`: SHA prefix of `(seed, steps)` — NOT the integrator state.

**No trajectory is preserved.** `export_trajectory(trace)` raises `NotImplementedError` (line 1127).

**Why it's a stub by design:** the placeholder exists so the public engine + adapter protocol surface (DTB-G1) can be exercised in tests without importing FlowMol3 source. The model itself is NOT loaded at construction time; only `force_mode in {"real", "auto"}` triggers an envelope-only ckpt load that records `_real_ckpt_meta` (line 1306-1362). The state materializer (`to_engine_caps` line 253) wires `ConcreteFlowMol3Materializer` lazily when torch + the molecular layer are importable; on the placeholder path it stays `None`.

**D.4 consequence:** every per-cell artifact in `regression-vectors/flowmol3.json` is a deterministic SHA derived from `(batch_id, sample_id, steps, seed)`. The `output_sha256` at the per-condition level is a SHA over the canonicalised bundle+trace JSON. All 9 conditions (3 seeds × 3 NFEs) are byte-stable against any change to FlowMol3 source as long as `_make_tensor_ref` is untouched. The D.4 vector header even warns: *"Do not change the `repr((label, sorted(parts.items())))` encoding without regenerating that vector."* (line 296-297 of `flowmol3.py`).

---

## A.5 — Factory dispatch in `_resolve_adapter`

File: `tools/run_real_ckpt_eval.py`.

**Registry entries** (lines 484-547 + 548-609): both `flowmol3` (v1) and `flowmol3_v2` exist in `DOWNSTREAM_METRICS`:
* `flowmol3.adapter_factory = "adaptive_reflow.adapters.flowmol3:default_flowmol3_adapter"` (line 542).
* `flowmol3_v2.adapter_factory = "adaptive_reflow.adapters.flowmol3_v2_adapter:default_flowmol3adapter"` (line 604).

**Wire-active override** (lines 910-917):

```python
if (
    model == "flowmol3"
    and factory_path.endswith(":default_flowmol3_adapter")
    and force_mode in {"real", "auto"}
):
    factory_path = (
        "adaptive_reflow.adapters.flowmol3_v2_adapter:default_flowmol3adapter"
    )
```

This is the Wave 66 Agent 1 fix. **Effect:** when the CLI runs `python tools/run_real_ckpt_eval.py --model flowmol3 --force-mode real --metric-mode real --composite-metric real`, the factory is swapped to v2 at line 918, and the v2 module is loaded in place of the v1 placeholder. The `synthetic` path is preserved (`force_mode == "synthetic"` is required to fail the guard and fall through to the v1 placeholder).

**Other-model guard** (line 911): the override is `model == "flowmol3"`-scoped. The other 13 models (kanzi, freqflow, lineageflow, hidream_i1, rectified_flow_cifar, graphbfn, self_flow, wan2_2_video, protbfn_abbfn, lumina_image_2_0, mm_fm, etc.) are untouched.

**Per-model force_mode token translation** (lines 960-969):

```python
_ADAPTER_FORCE_MODE_ALIAS: dict[str, dict[str, str]] = {
    "kanzi": {"real": "torch"},
    "lineageflow": {"real": "torch"},
    "freqflow": {"real": "torch"},
    "hidream_i1": {"real": "torch"},
    "rectified_flow_cifar": {"real": "torch"},
    "graphbfn": {"real": "torch"},
    "self_flow": {"real": "torch"},
    # flowmol3 + flowmol3_v2 are identity — no entry needed.
}
```

flowmol3 + flowmol3_v2 use the CLI-native `"real"` token directly (no alias needed).

**Factory call** (lines 931-947):

```python
mod = importlib.import_module(module_path)
factory = getattr(mod, attr)
kwargs: dict[str, Any] = {"force_mode": adapter_force_mode}
sig_params = inspect.signature(factory).parameters
if restart_min_nfe is not None and "restart_min_nfe" in sig_params:
    kwargs["restart_min_nfe"] = int(restart_min_nfe)
if nfe_budget is not None and "nfe_budget" in sig_params:
    kwargs["nfe_budget"] = int(nfe_budget)
adapter = factory(**kwargs)
```

This is the **second interface gap**: v1's `default_flowmol3_adapter` accepts `restart_min_nfe` and `nfe_budget` (Wave 58 gate); v2's `default_flowmol3adapter` does NOT. The `inspect.signature` filter (Wave 61 Agent 1) silently drops the kwargs for v2 — the gate is wired on v1 but has no effect on v2.

**Summary of dispatch routing for `force_mode in {"real", "auto"}`:**
1. `_resolve_adapter("flowmol3", force_mode="real")` is called.
2. `spec["adapter_factory"]` is loaded — points to v1 (`default_flowmol3_adapter`).
3. The Wave 66 guard (line 910) rewrites `factory_path` to v2 (`default_flowmol3adapter`).
4. `importlib.import_module("adaptive_reflow.adapters.flowmol3_v2_adapter")` loads v2.
5. `factory(force_mode="real")` constructs `FlowMol3V2Adapter` (v2's factory accepts `force_mode` and translates to `backend="torch"`).
6. `restart_min_nfe` and `nfe_budget` kwargs are filtered out (v2's factory doesn't declare them).
7. The v2 adapter is returned with `adapter_force_mode == "real"`.

---

## A.6 — Byte-stable regression vector locations

### A.6.1 v1 D.4 regression vectors — must NOT change

File: `regression-vectors/flowmol3.json`. Schema: `d4.v1`. Captured at 2026-09-05T11:06:11Z, git SHA `ff56e55`.

**9 conditions** (3 seeds × 3 NFEs):
* Seeds: `[41, 42, 43]`.
* NFEs: `[5, 10, 50]`.
* input_id: `batch_id="d4-b{seed}", sample_id="d4-s{seed}"`.

**Per-condition artifacts (all byte-stable):**

| Field | What it captures | Source line(s) in v1 |
|-------|------------------|----------------------|
| `trace.native_state_digest` | `flowmol3:<16-hex>` of SHA over `(state.digest, seed, steps)` | `solve_ode` line 983-985 |
| `trace.integrator_config_hash` | `flowmol3:<16-hex>` of SHA over `(seed, steps)` | `solve_ode` line 990-992 |
| `endpoint.native_state_digest` | `flowmol3:<16-hex>` of SHA over `(batch, sample, 0)` (initial state digest; identical for all 3 NFEs of a given seed) | `build_initial_state` line 765-767 |
| `endpoint.channels` | `["charge", "coordinate", "raw_pair"]` (sorted alphabetically per registry) | `FLOWMOL3_CHANNELS` |
| `endpoint.provenance` | `["flowmol3@77cae22174b7792b0e25e9e0414038420736d841", "DTB-G2 placeholder"]` | `build_initial_state` line 769 |
| `trajectory.present` | `false` | v1's `export_trajectory` raises `NotImplementedError` |
| `output_sha256` | SHA-256 over canonicalised per-condition JSON | harness-level |

**Specific values that MUST be preserved:**

```
seed=41, nfe=5:   trace.digest=flowmol3:ccf1613bd1d00bfc, cfg=flowmol3:458e224249527046, output_sha256=7c1ad50f...
seed=41, nfe=10:  trace.digest=flowmol3:676bed3865909539, cfg=flowmol3:e6db6ea06d77d57d, output_sha256=fd7a3b6b...
seed=41, nfe=50:  trace.digest=flowmol3:54cff28f4cb0f934, cfg=flowmol3:5f0772278b837c02, output_sha256=a782f3b7...
seed=42, nfe=5:   trace.digest=flowmol3:387f3faef330ddfc, cfg=flowmol3:31f7ea3670954c13, output_sha256=83c5a4b9...
seed=42, nfe=10:  trace.digest=flowmol3:039165e11d658baa, cfg=flowmol3:becf230aff45821a, output_sha256=746519df...
seed=42, nfe=50:  trace.digest=flowmol3:69833c5679e300b9, cfg=flowmol3:fdccb3262acb8e6f, output_sha256=33b988ae...
seed=43, nfe=5:   trace.digest=flowmol3:6f2fb87e47b3df75, cfg=flowmol3:4e082d7970678f42, output_sha256=c75f11ac...
seed=43, nfe=10:  trace.digest=flowmol3:156c38839242108c, cfg=flowmol3:d0b1a30c0ac548ca, output_sha256=c168b2c0...
seed=43, nfe=50:  trace.digest=flowmol3:9a420f09ea2fa8a5, cfg=flowmol3:1e462bb6b1f0c603, output_sha256=0a44f20c...
```

**Total count of v1 D.4 vectors that must remain unchanged: 9** (per condition: trace digest + cfg hash + endpoint digest + output_sha256, all locked).

### A.6.2 v2 regression vectors — captured but not pinned

File: `regression-vectors/flowmol3_v2.json` exists (it is in the regression-vectors/ directory listing). The Wave 68 Phase 3 verification ran "10/10 passed" for "flowmol3 or FlowMol3" (combining v1 + v2). The v2 vectors are NOT yet pinned as the byte-stability gate (the Wave 66 wire audit reports the metric layer is `BLOCKED` on v2 — not byte-stability-testable). Once the metric helper is refactored (Wave 68 Phase D), v2 vectors will join the pinned set.

### A.6.3 What may change in v1 (no D.4 byte-stability impact)

* Adding NEW methods (additive, e.g. Wave 68 Phase 3's `observe(...)` did not touch the v1 byte-stable surface — confirmed by Phase 3 verification §4.2: 10/10 D.4 vectors unchanged).
* Adding NEW constructor kwargs that default to None / safe values (Wave 50's `force_mode`, Wave 58's `nfe_budget`, `restart_min_nfe`).
* Adding NEW module-level constants (Wave 49's `FLOWMOL3_ATOM_TYPE_VOCAB_SIZE`, `PER_POSITION_ENTROPY_REDUCTION`, `AUDIT_FLOWMOL3_*`).
* Adding NEW private helpers.

### A.6.4 What would BREAK v1 byte stability

* Changing the `_make_tensor_ref` encoding (the D.4 vector header explicitly forbids it).
* Changing `FLOWMOL3_CHANNELS` order or contents.
* Changing `FLOWMOL3_PINNED_COMMIT` value.
* Changing `build_initial_state` provenance tuple.
* Changing `solve_ode`'s trace construction formula.
* Changing `_graph_payload_for` seed math (it feeds the `apply_restart_distribution` digest, not the D.4 vectors directly, but downstream consumers may transitively depend on it).

---

## A.7 — Concrete Phase 2 fix design (interface-first, old preserved, byte-stable)

### A.7.1 Design principle (Wave 11 / Wave 59 / Wave 68 pattern)

> **Interface-first.** Add a new typed surface that the metric layer can opt into. The existing methods stay in place byte-identically. The new surface is the structural close for the gap; the existing surface is preserved for backward compat with every other consumer.

### A.7.2 The interface gap, restated as a single sentence

> The v2 adapter exposes `observe(...)` (Wave 68 Phase 3) but does NOT expose `observe_entropy_reduction` (the v1 legacy hook the metric helper currently dispatches on); the v2 adapter does NOT honour the `nfe_budget` / `restart_min_nfe` kwargs the v1 factory forwards; and the v2 adapter's `apply_restart_distribution` lacks the NFE-adaptive gate that the v1 has.

### A.7.3 Phase 2 fix surface — what is added (NOT changed)

1. **Protocol extension (interface-first):** add `nfe_budget` and `restart_min_nfe` as keyword-only kwargs to the `FlowMatchingODEAdapter.apply_restart_distribution` Protocol declaration (or to a new `RestartGateProtocol`). Default values = None (no behaviour change). The v1 implementation already accepts them; the v2 implementation is updated to accept them (also default None = no behaviour change). Existing callers that don't pass these kwargs see byte-identical behaviour on both adapters.

2. **Metric helper refactor (Wave 68 Phase D, in flight):** the `_extract_observation_legacy` fallback at `run_real_ckpt_eval.py:1736-1737` (`hasattr(adapter, "observe_entropy_reduction")`) becomes the SECOND-CHOICE path; the FIRST-CHOICE path is `adapter.observe(...)` (typed Protocol). When the Protocol path returns an `ObservationResult` of `kind == POSITION_ENTROPY_REDUCTION`, the helper uses that and skips the legacy call entirely. This is the structural close for the Wave 66 BLOCKED-on-v2 failure mode.

3. **Byte-stable guarantees:**
   * v1: no method signature changes. New `observe(...)` stays additive. D.4 vectors (9/9) untouched.
   * v2: no method signature changes for the LEGACY methods it has (it has none). New `observe(...)` already exists (Wave 68 Phase 3). The new `apply_restart_distribution` kwargs are forward-compatible additions.
   * Factory: `default_flowmol3adapter` (v2) gains optional `nfe_budget=None` and `restart_min_nfe=None` kwargs that are no-ops (the v2 adapter ignores them in the absence of a real gate implementation; OR a v2 NFE-gate shim is added if the user wants parity).
   * The Wave 66 wire at `run_real_ckpt_eval.py:910-917` is unchanged.

4. **Opt-in / opt-out:** the dispatch is controlled by:
   * `--force-mode real/auto/synthetic` (existing CLI flag — drives v1 vs v2 selection).
   * `--metric-mode real/auto/synthetic` (existing — drives whether the metric helper does real compute or saturates).
   * `--composite-metric real/synthetic` (existing — drives whether `FlowMol3Glue.compute_chemistry_metrics` is invoked).
   * NO new CLI flag needed. The Protocol-method-vs-legacy-method choice is internal to the helper.

### A.7.4 Phase 2 fix shape (sketch, not implementation)

```python
# Option A — protocol extension in interfaces.py (additive)
@runtime_checkable
class AdapterObservationProtocol(Protocol):
    """Existing surface, unchanged."""
    def observe(self, trace, state, paper_quantities=None, *, ...): ...

# Option B — restart-gate Protocol (new, additive)
@runtime_checkable
class RestartGateProtocol(Protocol):
    """Adapters that support the Wave 58 NFE-adaptive gate opt into this."""
    def gate_kwargs(self) -> tuple[str, ...]:
        """Return the constructor kwargs this adapter accepts for the gate."""
        ...
```

The `FlowMol3V2Adapter` does NOT need to opt into the gate for v2 to function; the kwargs are simply ignored. v1 continues to honour the gate via `apply_restart_distribution(nfe_budget=...)`.

### A.7.5 What is explicitly OUT of scope for Phase 2

* No byte-stability change for v1 (Phase 2 must verify 9/9 D.4 vectors unchanged).
* No behaviour change for `synthetic` path (force_mode=synthetic still routes to v1 placeholder).
* No removal of legacy `observe_endpoint` / `observe_entropy_reduction` (Wave 11 constraint: old preserved).
* No change to the Wave 66 wire (lines 910-917 of `run_real_ckpt_eval.py`).
* No change to `_resolve_adapter`'s `inspect.signature` filter (lines 942-946).

### A.7.6 Verification gate

After Phase 2:

1. `pytest tests/test_adapters/test_flowmol3_adapter.py -q` → all pre-existing tests pass byte-identically (the v1 byte-stable surface is untouched).
2. `pytest tests/test_adapters/test_flowmol3_v2_adapter.py -q` → all pre-existing tests pass byte-identically (the v2 surface is additive-only).
3. `pytest tests/test_d4_regression_vectors.py -k flowmol3 -q` → 9/9 vectors unchanged (the SHA-encoded fields are bit-identical).
4. `pytest tests/test_adapters/test_regression_vectors.py -k flowmol3 -q` → unchanged.
5. `pytest tests/test_framework/test_adapter_observation_protocol.py -q` → 19/19 unchanged (the Phase 1 Protocol contract is intact).

---

## A.8 — Files to modify

### A.8.1 v1 (`adaptive_reflow/adapters/flowmol3.py`) — preserve byte-stable behaviour

**Files NOT to modify:**
* `adaptive_reflow/adapters/flowmol3.py` — Phase 2 must NOT touch this file. The 9 D.4 vectors are pinned to its `_make_tensor_ref`, `solve_ode`, `build_initial_state`, `apply_restart_distribution` behaviour.

**Files MAY modify (v1-side tests only):**
* `tests/test_adapters/test_flowmol3_adapter.py` — additive tests only (no edits to existing test bodies that would alter byte-stable assertions).

### A.8.2 v2 (`adaptive_reflow/adapters/flowmol3_v2_adapter.py`) — add new dispatch methods

**Files MAY modify (additive only):**
* `adaptive_reflow/adapters/flowmol3_v2_adapter.py` — add a new method (e.g. `def has_restart_gate(self) -> bool: return False` or extend `apply_restart_distribution` with optional `nfe_budget=None` and `restart_min_nfe=None` kwargs that are no-ops on v2). Existing signatures preserved; new kwargs are forward-compatible additions.
* `tools/run_real_ckpt_eval.py:_resolve_adapter` (lines 859-950) — if v2's factory signature gains `nfe_budget` / `restart_min_nfe`, the `inspect.signature` filter already routes the kwargs correctly (no change needed in `_resolve_adapter` itself). The Wave 66 wire (lines 910-917) is untouched.
* `adaptive_reflow/framework/interfaces.py` — if a new Protocol is added (e.g. `RestartGateProtocol`), it goes here, alongside the existing `AdapterObservationProtocol`. Stdlib-only constraint preserved.

**Files NOT to modify (v2-side):**
* `regression-vectors/flowmol3.json` — v1 vectors only; do not add v2 vectors here.
* `regression-vectors/flowmol3_v2.json` — when v2 byte-stability vectors are pinned (post-Phase D), they go in this file, but Phase 2 is NOT the right place to pin them (the metric layer is still BLOCKED on v2).

### A.8.3 Net surface for Phase 2 (additive, no edits to existing code)

| File | Change | LOC impact |
|------|--------|-----------|
| `adaptive_reflow/framework/interfaces.py` | (optional) add `RestartGateProtocol` | +0 to +50 |
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py` | add `nfe_budget` / `restart_min_nfe` kwargs to `apply_restart_distribution` + factory (both default None, no-op on v2) | +0 to +30 |
| `tools/run_real_ckpt_eval.py` | (already supports the kwargs via `inspect.signature` filter; no change unless v2 factory signature changes) | +0 to +5 |
| `tests/test_adapters/test_flowmol3_v2_adapter.py` | additive test for the new kwargs (no-op behaviour) | +0 to +50 |
| `docs/audit/wave54-phase2-fix-design.md` | (NEW) Phase 2 design doc — mirrors this review's structure | +150 |

**Files explicitly untouched in Phase 2:**
* `adaptive_reflow/adapters/flowmol3.py` — v1 byte-stable.
* `tests/test_adapters/test_flowmol3_adapter.py` — v1 tests byte-stable.
* `regression-vectors/flowmol3.json` — 9 D.4 vectors pinned.
* `tools/run_real_ckpt_eval.py:910-917` — Wave 66 wire active.

---

## A.9 — Risks and mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Phase 2 inadvertently changes v1 byte-stable behaviour | HIGH | No edits to `flowmol3.py`; 9 D.4 vectors gate the change |
| v2 NFE-gate shim creates new semantics divergence | MEDIUM | Default `None` for both kwargs; v2 ignores them unless explicitly invoked |
| Metric helper still BLOCKED on v2 (Wave 66 status) | MEDIUM | Phase 2 is the structural close (Wave 68 Phase D in flight); Phase 2 must wait for Phase D to land before claiming the gap closed |
| `apply_restart_distribution` signature change breaks legacy callers | LOW | New kwargs are forward-compatible; positional args unchanged |
| v1's `observe_entropy_reduction` removed by mistake | HIGH | Out of scope per Wave 11 constraint; review explicitly forbids removal |

---

## A.10 — Notes for the Phase 2 designer

1. **The interface gap is structural, not numerical.** Both adapters produce real FlowMol3 inferences (v2) or stable placeholders (v1); the gap is the SURFACE (which methods exist + which kwargs are honoured), not the numbers.

2. **The Wave 66 wire is a workaround, not a fix.** It forces `force_mode in {real, auto}` to construct the v2 adapter regardless of the registry's adapter_factory. The proper Phase 2 close is to give the metric helper a generic dispatch (Wave 68 Phase D) so the wire becomes a no-op for the observation path.

3. **v1 byte-stability is the highest-priority invariant.** The 9 D.4 vectors are the regression test gate. Any Phase 2 change that breaks them fails the gate.

4. **The `nfe_budget` / `restart_min_nfe` kwargs are a Wave 58 forward-compatible addition.** v1 added them in Wave 58 and they default to None; v2 adding them now (with default None and no-op behaviour) is a strictly additive change that does not affect any existing caller.

5. **The observation Protocol is the strategic interface.** v1 + v2 both adopt it (Wave 68 Phase 3). The legacy `observe_entropy_reduction` (v1 only) and `observe_token_indices` (Kanzi + LineageFlow) are the deprecation path. Phase 2 should not accelerate the deprecation; it should make the new Protocol the primary dispatch target.

---

## A.11 — Final response JSON

```json
{
  "review_doc_path": "docs/audit/wave54-review-a-v1-v2.md",
  "v1_methods_count": 12,
  "v2_methods_count": 11,
  "protocol_gap_summary": "v2 lacks observe_entropy_reduction (legacy metric-helper dispatch hook) — the metric helper _extract_observation_legacy returns BLOCKED via hasattr(adapter, 'observe_entropy_reduction') check at run_real_ckpt_eval.py:1737; v2's apply_restart_distribution does not honour nfe_budget/restart_min_nfe kwargs (v1's Wave 58 NFE-adaptive gate is silently dropped by inspect.signature filter); v2's factory default_flowmol3adapter accepts a different kwarg set than v1's default_flowmol3_adapter (no atom_type_entropy_restart_policy, no nfe_budget, no restart_min_nfe); v1's solve_ode is a hash stub (SHA-256 of state.digest+seed+steps), v2's solve_ode does real CTMC / linear / upstream integration; v1's export_trajectory raises NotImplementedError, v2's returns real lineage Mapping[str, ArrayF64]; both adapters now conform to AdapterObservationProtocol via Wave 68 Phase 3 observe() shim, but the metric helper does not yet consume the new path (Wave 68 Phase D in flight).",
  "factory_dispatch_line": "tools/run_real_ckpt_eval.py:910-917 (Wave 66 Agent 1 wire override routes model=='flowmol3' AND factory_path.endswith(':default_flowmol3_adapter') AND force_mode in {'real','auto'} to v2's default_flowmol3adapter)",
  "d4_vectors_unchanged_count": 9,
  "files_to_modify_v1": [],
  "files_to_modify_v2": [
    "adaptive_reflow/adapters/flowmol3_v2_adapter.py",
    "tools/run_real_ckpt_eval.py",
    "adaptive_reflow/framework/interfaces.py",
    "tests/test_adapters/test_flowmol3_v2_adapter.py"
  ],
  "byte_stable_risk_assessment": "LOW — Phase 2 design preserves v1 byte-stable surface (no edits to flowmol3.py); v2 changes are strictly additive (new optional kwargs that default to None); 9/9 D.4 vectors in regression-vectors/flowmol3.json must remain unchanged (verified by tests/test_d4_regression_vectors.py + tests/test_adapters/test_regression_vectors.py)",
  "notes": "The v1 byte-stable surface is pinned at flowmol3.py:_make_tensor_ref (SHA-256, 16 hex prefix, repr((label, sorted(parts.items()))) encoding) + solve_ode + build_initial_state + FLOWMOL3_CHANNELS + FLOWMOL3_PINNED_COMMIT. The 9 D.4 vectors cover seeds [41,42,43] × nfes [5,10,50] with fixed input_id (d4-b{seed}, d4-s{seed}). The Wave 66 wire at run_real_ckpt_eval.py:910-917 is the active eval-time bridge; Wave 68 Phase D (in flight) is the proper structural close via the AdapterObservationProtocol dispatch. Phase 2 of Wave 54 should NOT remove legacy methods (Wave 11 constraint); it should make the Protocol path the primary dispatch and keep the legacy methods as fallback for adapters that have not yet adopted the Protocol."
}
```