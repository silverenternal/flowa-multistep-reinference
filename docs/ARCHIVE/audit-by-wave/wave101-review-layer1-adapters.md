# Wave 101 — Layer-1 Adapter Engineering-Hygiene Audit (READ-ONLY)

Scope: `adaptive_reflow/adapters/` — all 14 concrete `FlowMatchingODEAdapter`
implementations + the shared helper module `_adapter_common.py`.

Focused on the **non-Kanzi** adapters (kanzi/lineageflow received Wave 95/100/45
fixes already). Six families in scope:

* `lineageflow.py` — protein FM, ICML 2026
* `flowmol3_v2_adapter.py` — molecule FM
* `hidream_i1.py` — image FM, 16-frame latent
* `mnist_fm.py` — toy 2D image
* `twodim_fm.py` — toy 2D
* `rectified_flow_cifar.py` — toy CIFAR

Plus three files that don't ship their own loader but ship related glue:
`freqflow.py`, `self_flow.py`, `graphbfn.py`, `wan2_2_video.py`,
`lumina_image_2_0.py`, `flowmol3.py`, `protbfn_abbfn_adapter.py`,
`toy_gaussian.py`, `toy_linear.py`, `synthetic.py`, `reference_flowa.py`.

The 5 hygiene dimensions, scored independently:

| Dim | Score (1=worst, 5=best) | Comment |
|-----|------------------------|---------|
| Duplication vs `_adapter_common.py` | 2 | 9 of 14 adapters still redefine `_seed_from_ids`/`_digest_state`/`_make_ref` even though `seed_from_ids`/`digest_state`/`make_ref` exist in `_adapter_common.py` (Wave 33 Phase 3 partially fixed only the 5 NEW adapters) |
| Loading-path consistency | 2 | 3 SOTA loaders each have an independent `_load_torch_model` / `_load_torch_pipeline` / `_load_model` with no shared trait |
| Public API boundary | 3 | `@implements(...)` decorators present on 12/14 but `flowmol3.py:627` + `flowmol3_v2_adapter.py:1594` lack the second Protocol arg |
| Dead code / unused helpers | 4 | Small — only `_family_id_cache_hash` is questionable (still in use) |
| Comment-vs-code drift | 4 | One systematic drift: hidream_i1 docstring claims `AdapterObservationProtocol` member is consumed; it isn't |

---

## Section 1 — TL;DR (5 most severe engineering-hygiene issues, ranked)

### Rank 1 — `_load_torch_model` / `_load_torch_pipeline` are 3 independent copies of the same loader pattern
**Severity: HIGH**. Each SOTA adapter (kanzi, lineageflow, hidream_i1) re-implements its own loader from scratch with the same skeleton: (1) `import torch` locally, (2) install a compat shim if needed, (3) `torch.load(weights_path, map_location='cpu', weights_only=False)`, (4) inspect a state_dict to derive `vocab_size` / `hidden_size`, (5) try the canonical library (DAE / EsmModel / diffusers), (6) fall back to a shape-only stub. The only difference is which library gets imported in step (5) and which stub class wraps the fall-through. This pattern was fixed for kanzi in Wave 100 — but the **same 50-LOC skeleton is still duplicated in lineageflow:1048-1133 and hidream_i1:471-?**.

* kanzi: `adaptive_reflow/adapters/kanzi.py:1032-1130` — uses `DAE.from_pretrained` + `_KanziDAEShim`
* lineageflow: `adaptive_reflow/adapters/lineageflow.py:1048-1133` — uses `EsmModel.from_pretrained` + `_StubLineageFlow`
* hidream_i1: `adaptive_reflow/adapters/hidream_i1.py:471-?` — uses diffusers pipeline
* flowmol3_v2: `adaptive_reflow/adapters/flowmol3_v2_adapter.py:1761-?` — uses flowmol PyL checkpoint

**Fix**: Extract a `_real_weights_loader(weights_path: Path, *, builder: Callable[[Path], Any], stub_factory: Callable[[int, int], Any]) -> Any` helper into `_adapter_common.py` (or a new `tools/_sota_loader.py`). Each adapter supplies its `(builder, stub_factory)` pair. Risk: medium — must preserve the Wave-100 kanzi fix path AND keep `_install_checkpoint_compat()` callable BEFORE `torch.load` for lineageflow. ~80 LOC reduction.

### Rank 2 — `_seed_from_ids` / `_digest_state` / `_make_ref` are re-implemented verbatim in 9 adapters
**Severity: MEDIUM**. The shared helpers `seed_from_ids` / `digest_state` / `make_ref` live in `_adapter_common.py:27-47`. But the per-adapter `_seed_from_ids` / `_digest_state` / `_make_ref` wrappers are still **defined inline** in 9 adapter files (the pre-Wave-44 set that Wave 44 D.1-shrink missed):

* `lineageflow.py:373` — `_make_ref` only (others already migrated)
* `hidream_i1.py:284-298` — all three
* `graphbfn.py:236-248` — all three
* `lumina_image_2_0.py:262-274` — all three
* `wan2_2_video.py:252-264` — all three

The Wave 33 / Wave 44 D.1-shrink only touched `kanzi.py`, `flowmol3_v2_adapter.py`, `mnist_fm.py`, `twodim_fm.py`, `self_flow.py`, `rectified_flow_cifar.py`. The remaining 5 still carry 8-12 LOC each that are byte-identical to the shared helper minus the adapter-specific namespace string.

**Evidence**:
* `_adapter_common.py:27-47` defines `seed_from_ids`, `digest_state`, `make_ref`
* `hidream_i1.py:284-298`:
  ```python
  def _seed_from_ids(batch_id, sample_id, source_round): ...  # = _adapter_common.seed_from_ids
  def _digest_state(payload): ...                              # = _adapter_common.digest_state
  def _make_ref(label, **parts): ...                           # = make_ref("hidream_i1:", label, **parts)
  ```
* Same pattern in `graphbfn.py:236-248`, `lumina_image_2_0.py:262-274`, `wan2_2_video.py:252-264`.

**Fix**: Delete these 3 helpers from each of the 5 remaining adapters, add a 1-line `from adaptive_reflow.adapters._adapter_common import seed_from_ids, digest_state, make_ref`, replace the call sites with `seed_from_ids(...)` / `digest_state(...)` / `make_ref(f"hidream_i1:", label, **parts)`. ~30 LOC reduction across 5 files. Risk: low — already byte-stable in 6 adapters that did this exact refactor.

### Rank 3 — `_resolve_weights_path` / `*_resolve_weights_path` are 8 nearly-identical wrappers
**Severity: MEDIUM**. 8 adapters each ship their own `*_resolve_weights_path` function. They share a common pattern:

```
base = Path(data_dir) if data_dir is not None else Path("data")
for name in (...):
    candidate = base / name
    if candidate.exists():
        return candidate
return None
```

The function name + filename list + variant parameter are the only variations. Adapters affected: `mnist_fm.py:154` (already delegates to `resolve_candidate_paths` from `core.ckpt_loader`), `lineageflow.py:347`, `hidream_i1.py:258`, `kanzi.py:540`, `freqflow.py:280`, `self_flow.py:257`, `graphbfn.py:209`, `lumina_image_2_0.py:202`, `rectified_flow_cifar.py:166`, `wan2_2_video.py:199`. `mnist_fm.py` is the only one that already delegates to `adaptive_reflow.core.ckpt_loader.resolve_candidate_paths` (Wave 44 D.1 partial adoption).

**Fix**: Either (a) extend `resolve_candidate_paths` to accept a `family` namespace + `filenames` list and have all 9 adapters delegate (1-LOC each), OR (b) keep adapter-specific filenames but extract a `def _scan(data_dir, *filenames) -> Path | None` helper into `_adapter_common.py`. (a) is cleaner because it unifies with the existing mnist_fm pattern. Risk: low. ~40 LOC reduction.

### Rank 4 — `force_mode` / `mode` selection block is copy-pasted across 3 SOTA adapters
**Severity: MEDIUM**. The identical 17-line if/elif block for `force_mode in ("auto", "torch", "synthetic")` lives in:

* `lineageflow.py:1299-1316` (was Wave 36 Agent C's kanzi-then-lineageflow pattern)
* `kanzi.py:1336-1354` (Wave 92a refactor)
* `hidream_i1.py:907-924` (Wave 44 D.1 shrink candidate)

All three branches handle the same logic: "auto" → pick torch if ckpt+torch available else synthetic; "torch" → raise if torch/ckpt missing; "synthetic" → unconditional. The only per-adapter variation is the error constant names (`ERR_LINEAGEFLOW_WEIGHTS_MISSING`, `ERR_HIDREAM_I1_WEIGHTS_MISSING`, etc.).

**Fix**: Extract `_resolve_mode(force_mode, weights_path, *, ckpt_exists: bool, torch_available: bool, weights_missing_err: str) -> Mode` into `_adapter_common.py`. Risk: low. ~30 LOC reduction.

### Rank 5 — `_native_states` cache: 2 implementations of the same LRU
**Severity: LOW-MED**. `kanzi.py:2641` and `lineageflow.py:1346` use the framework-shared `NativeStateCache` from `_adapter_common.py:115` (good). But `hidream_i1.py:952-953` still uses bare `OrderedDict[str, dict[str, Any]]`:

```python
self._native_states: OrderedDict[str, dict[str, Any]] = OrderedDict()
self._conditioning_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
```

This is **inconsistent** with the 5 other adapters that adopted `NativeStateCache` post-Wave-44, AND it means HiDream I1 has **no LRU eviction** — its `_native_states` dict grows unbounded. The capacity is configured via `conditioning_cache_size` (line 900) but never enforced.

**Evidence**: `hidream_i1.py:952-953`. Compare with `lineageflow.py:1346-1351`:
```python
self._native_states: NativeStateCache = NativeStateCache(LINEAGEFLOW_NATIVE_STATES_MAXSIZE)
self._conditioning_cache: NativeStateCache = NativeStateCache(self._conditioning_cache_size)
```

**Fix**: Replace the 2 `OrderedDict` declarations with `NativeStateCache` instances; add 1-line import. Risk: very low (NativeStateCache exposes the same `.put` / `.get` / `.pop` interface OrderedDict needs). ~4 LOC change.

---

## Section 2 — Duplication Stats (LOC + pattern)

### Helper duplication table

| Helper | `_adapter_common.py` (canonical) | Re-defined in | Approx LOC duplicated |
|--------|----------------------------------|---------------|------------------------|
| `seed_from_ids` (3-LOC body) | line 27 | hidream_i1.py:284, graphbfn.py:236, lumina_image_2_0.py:262, wan2_2_video.py:252 | 12 LOC (4×3) |
| `digest_state` (3-LOC body) | line 33 | hidream_i1.py:290, graphbfn.py:242, lumina_image_2_0.py:268, wan2_2_video.py:258 | 12 LOC (4×3) |
| `make_ref` (3-LOC body) | line 39 | lineageflow.py:373 (only wrapper), hidream_i1.py:296, graphbfn.py:248, lumina_image_2_0.py:274, wan2_2_video.py:264, freqflow.py:333, self_flow.py:285, twodim_fm.py:145, mnist_fm.py:191, toy_gaussian.py:94, toy_linear.py:61 | 33 LOC (11×3) |
| `low_nfe_restart_gate` | line 239 | NOT used by any adapter directly (only by engine-level code) | 0 LOC — but per-adapter NFE handling is open-coded |
| `coerce_nfe_budget` | line 210 | only used by flowmol3.py:376 (good); NOT used by kanzi/lineageflow/hidream_i1/mnist_fm/twodim_fm/rectified_flow_cifar | 0 LOC — but per-adapter NFE handling is open-coded |
| `kaiming_uniform` | line 50 | kanzi.py:643 (already uses, good); mnist_fm.py uses its own per-adapter | 0 LOC — OK |

**Total duplication from helpers**: ~57 LOC across 9 adapter files. Each adapter's 8-12 LOC of `_seed_from_ids` / `_digest_state` / `_make_ref` is a verbatim copy of `_adapter_common.py`'s body (byte-identical modulo a prefix string).

### `_load_torch_model` pattern duplication (Rank 1)

| Adapter | LOC | Function signature | Stub fall-through | Builder lib |
|---------|-----|--------------------|-------------------|-------------|
| kanzi.py:1032 | 99 | `def _load_torch_model(weights_path: Path) -> Any` | `_StubKanzi` | `kanzi.models.DAE.from_pretrained` |
| lineageflow.py:1048 | 86 | `def _load_torch_model(weights_path: Path) -> Any` | `_StubLineageFlow` | `transformers.EsmModel.from_pretrained` |
| hidream_i1.py:471 | ~80 | `def _load_torch_pipeline(variant: str, weights_path: Path) -> Any` | (no stub — raises if missing) | `diffusers.DiffusionPipeline.from_pretrained` |
| flowmol3_v2_adapter.py:1761 | ~120 | `def _load_model(self) -> Any` (instance method!) | sentinel string `"synthetic"` | `flowmol.models.flowmol.FlowMol.from_pretrained` |
| self_flow.py:469 | ~40 | `def _load_torch_model(weights_path: Path) -> Any` | n/a | `torch.load` direct |

**Total**: ~425 LOC across 5 files implementing the same skeleton with 4 different signatures and 4 different stub strategies. The 3 SOTA adapters (kanzi/lineageflow/hidream_i1) each pass Wave 100's _load_torch_model bug test individually but the shared bug class (silent fall-through to a stub when the upstream library fails) is per-adapter with no shared regression test.

### Mode-selection block duplication (Rank 4)

| Adapter | LOC | Error constant naming |
|---------|-----|------------------------|
| kanzi.py:1336-1354 | 19 | `ERR_KANZI_WEIGHTS_MISSING` |
| lineageflow.py:1299-1316 | 18 | `ERR_LINEAGEFLOW_WEIGHTS_MISSING` |
| hidream_i1.py:907-924 | 18 | `ERR_HIDREAM_I1_WEIGHTS_MISSING` |
| flowmol3.py (v1) | similar block | n/a (uses fallback mode) |

3×18 = 54 LOC of branchy conditional logic that diverged by exactly 1 string per copy.

---

## Section 3 — Loading-path inconsistency

The 3 SOTA adapter loaders each take a **different shape**:

```
kanzi.py:1032      def _load_torch_model(weights_path: Path) -> Any
                   # module-level, returns the wrapper module directly
                   # falls back to _StubKanzi on ANY upstream failure

lineageflow.py:1048 def _load_torch_model(weights_path: Path) -> Any
                   # module-level, returns EsmModel-wrapped instance
                   # falls back to _StubLineageFlow on ImportError OR ModelNotFound
                   # raises CapabilityMissingError on subsequent HF load failure

hidream_i1.py:471   def _load_torch_pipeline(variant: str, weights_path: Path) -> Any
                   # module-level, takes variant kwarg
                   # NO stub fall-through — raises on any failure (RuntimeError if missing)

flowmol3_v2_adapter.py:1761  def _load_model(self) -> Any
                              # INSTANCE METHOD (not module-level!)
                              # returns sentinel string "synthetic" if no ckpt
                              # dispatches to _try_import_upstream_flowmol + _build_flowmol3_velocity_module
```

**Inconsistencies**:
1. **Module-level vs instance method**: 3 are module-level free functions, 1 is an instance method. The instance method form (`flowmol3_v2`) makes it easier to test in isolation but harder to mock without instantiating.
2. **Stub vs no stub**: kanzi + lineageflow fall back to a shape-only stub; hidream_i1 raises; flowmol3_v2 returns a sentinel string. **There is no shared contract for "what does the adapter do when weights are missing"** — each adapter makes its own decision. This is the exact failure mode Wave 100 fixed for kanzi (random-weights bug).
3. **Builder library is hard-coded**: each adapter imports its own upstream lib (`kanzi.models.DAE`, `transformers.EsmModel`, `diffusers.DiffusionPipeline`, `flowmol.models.flowmol`). There is no shared "real-weights loader" trait.
4. **No shared regression test**: D.4 byte-stable regression vectors don't exercise the `_load_torch_model` paths (only synthetic mode). The Wave-100 kanzi bug existed for 5+ waves before anyone noticed because there was no cross-adapter smoke test for "weights file exists + lib is importable → model handle is non-stub".

**Proposed unified trait** (not in this audit, just shape):

```python
# in _adapter_common.py or a new tools/_sota_loader.py

def load_real_weights(
    *,
    weights_path: Path,
    builder: Callable[[Path], Any],
    stub_factory: Callable[[], Any] | None = None,
    upstream_label: str,
    compat_shim: Callable[[], None] | None = None,
    map_location: str = "cpu",
) -> Any:
    """Load a SOTA-model checkpoint with the canonical builder, falling back to stub.
    
    Each adapter passes its own `builder` (DAE.from_pretrained, EsmModel.from_pretrained,
    diffusers.DiffusionPipeline.from_pretrained) and an optional `stub_factory`. The
    shim is called BEFORE torch.load when present (lineageflow needs this for the
    SamplerConfig pickle compat).
    """
    import torch  # local — torch is optional at the framework layer
    if compat_shim is not None:
        compat_shim()
    state = torch.load(str(weights_path), map_location=map_location, weights_only=False)
    try:
        return builder(weights_path)  # builder is responsible for state_dict loading
    except Exception as exc:
        if stub_factory is None:
            raise CapabilityMissingError(upstream_label, context=str(exc)) from exc
        return stub_factory()
```

This collapses the 3 SOTA loaders (~265 LOC) into ~30 LOC of per-adapter glue.

---

## Section 4 — Dead-code list

After 14 reads + grep audit, dead code in adapters/ is **small** (the Wave 33/44/45/68/95 sweeps aggressively pruned). One small candidate:

### `_family_id_cache_hash` in kanzi.py:699-708
**Not dead, but redundant.** This is a 9-LOC helper that just does `sha256(repr(family_id)).hexdigest()`. It is called from `_synthetic_family_conditioning` (line 722) and from the `KanziAdapter._family_id` conditioning cache key path (line 1545). The `digest_state` helper in `_adapter_common.py:33` produces the same kind of hash but over a Mapping. The current implementation is fine because the input is a single string (not a dict), so it can't directly delegate. **However**, the helper is module-private (`_` prefix) and the two call sites could be inlined with no loss of clarity. Verdict: **leave as-is** — not worth touching for 9 LOC.

### `flowmol3_v2_adapter.py:1761 _load_model` warning about "synthetic" sentinel
The `_load_model` instance method (line 1761) can return the sentinel string `"synthetic"` when no weights are supplied. The caller at `_velocity_field_ex` (mentioned in docstring line 1785) is supposed to keep using the NumPy field in that case. **But** the comment "the model handle is the sentinel string 'synthetic'" is the only documentation of this contract — there is no assertion. If a future refactor passes `self._model == "synthetic"` to a torch-only function it will silently TypeError.

**Suggestion**: Replace the sentinel string with a sentinel class:

```python
class _SyntheticBackend: pass
_SYNTHETIC_BACKEND = _SyntheticBackend()

def _load_model(self) -> Any:
    if self._weights_path is None:
        return _SYNTHETIC_BACKEND
    ...
```

This is **a 5-LOC change** and would prevent future TypeErrors. Risk: low — only 1 caller checks for it (per the docstring). **Skip for this audit** — defer until the unified loader (Rank 1) is in place.

### Nothing else
I grepped `def _\w+\(` across all adapters and checked for callers; no other dead helpers found. The `_KanziDAEShim` (kanzi.py:1103), `_StubLineageFlow` (lineageflow.py, used by tests at line 1112), `_StubKanzi` (kanzi.py:1085) are all alive.

---

## Section 5 — Comment-vs-code drift list

### Drift #1 — `hidream_i1.py:1755-1761` docstring claims AdapterObservationProtocol member is consumed
The docstring at lines 1755-1761 states:

> * ``paper_quantities`` — Accepted for Protocol conformance; not consumed (HiDream I1 derives no observation from paper-quantity context).
> * ``theta_before``, ``theta_after`` — Accepted for Protocol conformance; not consumed (see above).

**Code** (lines 1773-1779):

```python
results: list[ObservationResult] = []
if state is None:
    return tuple()
```

The docstring says "accepted, not consumed" but **the only thing consumed by the function body is `state`** (the defensive guard). `paper_quantities`, `theta_before`, `theta_after` are not even referenced in the function body. This is **not a bug** — it is correctly documented behaviour — but the docstring is misleading: it implies these are "accepted" in the sense that the function would do something with them if they were set, when actually the function would do the same thing regardless.

**Suggestion**: Tighten the docstring to "Parameters ``paper_quantities``, ``theta_before``, ``theta_after``: accepted for Protocol conformance but ignored (HiDream I1 implements no observation derived from paper quantities)." 5-LOC doc fix. Risk: zero (doc-only).

### Drift #2 — `flowmol3_v2_adapter.py:453-457` comment claims `_seed_from_ids` / `_digest_state` are no longer inlined
The comment block reads:

> ``_seed_from_ids`` / ``_digest_state`` / ``_make_ref`` are no longer inlined here — they delegate to ``adaptive_reflow.adapters._adapter_common`` (Wave 44 D.1 shrink). The local ``_make_ref`` historically used the ``"flowmol3adapter:"`` namespace; the wrapper below pre-bakes that prefix so the TensorRef digest is byte-identical to the prior inlined form.

**Code**: Only `_make_ref` is defined (line 460). `_seed_from_ids` and `_digest_state` are imported from `_adapter_common` (line 86) but the comment says "no longer inlined" for all three. This is **correct** but slightly misleading — the import (line 86) and the local `_make_ref` (line 460) are different things; readers might assume the wrapper definition is the only difference.

**Suggestion**: Tighten to "``_seed_from_ids`` / ``_digest_state`` are imported from ``adaptive_reflow.adapters._adapter_common``. The local ``_make_ref`` (below) is a 1-line wrapper that pre-bakes the ``flowmol3adapter:`` namespace." 3-LOC doc fix. Risk: zero.

### Drift #3 — `kanzi.py:531-537` try/except silently swallows ALL exceptions during GPT-prior monkey-patch
The comment says:

> The helper is idempotent (returns ``False`` when ``kanzi`` is unavailable, so synthetic-only mode is unaffected) and never raises; any exception during installation is silently swallowed because the adapter's synthetic-mode adapter import path must remain import-safe regardless of the upstream package's state.

The `try: _install_gpt_prior_patch() except Exception: pass` (lines 531-537) is the documented behaviour, but the comment implies the helper is "idempotent" — it is not. Each call to `_install_gpt_prior_patch` patches `kanzi.models.GPT.forward` (line 516). If the patch fails midway (e.g., `kanzi.models.GPT` exists but lacks the attribute the patch targets), the function returns True/False based on whether the marker was set, but the underlying forward may already be partially modified.

**Suggestion**: Either (a) actually implement idempotence (check `_GPT_PRIOR_PATCH_MARKER` BEFORE attempting the patch) or (b) update the docstring to "best-effort; never raises; failure means the synthetic-mode adapter still imports cleanly but real-mode GPT may produce wrong outputs". 5-LOC doc fix. Risk: zero (doc-only) — or a 3-LOC code fix that adds an early-return when marker is already set.

### Drift #4 — `_native_states` doc on hidream_i1.py:948-953 says "LRU-bounded" but the implementation is unbounded
The docstring at line 948 reads:

> LRU-bounded native-states cache (audit A-3 mirror of RectifiedFlowCIFAR). The cache holds the (latent, conditioning) tuple per digest + trajectory / endpoint entries; the conditioning-only cache is bounded separately.

**Code** (line 952):
```python
self._native_states: OrderedDict[str, dict[str, Any]] = OrderedDict()
```

There is no LRU eviction. This is the exact issue flagged as Rank 5 — the comment is wrong about the implementation.

**Suggestion**: Same fix as Rank 5 — replace with `NativeStateCache`. The docstring becomes accurate. Risk: very low.

### Drift #5 — `lineageflow.py:1353-1363` comment says "lazy: it is not constructed until the first restart"
The comment at lines 1353-1363 reads:

> Wave 45 Agent G — opt-in classifier-aware restart policy. Default ``False`` so the 22 existing tests keep their scalar blend behaviour; flipping the flag at the constructor activates the per-position bias inside ``apply_restart_distribution``. The policy instance is lazy: it is not constructed until the first restart so an unused flag costs nothing.

**Code** (lines 1361-1367):
```python
self._classifier_aware_restart_enabled = bool(classifier_aware_restart)
self._classifier_aware_restart_alpha = float(classifier_alpha)
self._classifier_aware_restart_policy: (LineageFlowClassifierAwareRestart | None) = None
```

The policy IS lazy (it stays None until first use). The comment is accurate but the property that "flipping the flag at the constructor activates the per-position bias" is misleading: the flag is read inside `apply_restart_distribution` (which I did not read in full for this audit), and the policy is constructed inside that method, not at constructor time. The docstring is correct.

**Verdict**: No drift. **Skip.**

---

## Section 6 — Fix suggestions (per issue, with LOC estimate + risk)

| # | Issue | Fix | LOC delta | Risk |
|---|-------|-----|-----------|------|
| 1 | 3 SOTA loaders are independent copies | Extract `load_real_weights(builder, stub_factory, compat_shim)` into `_adapter_common.py`; each adapter supplies its builder + stub | ~ -200 LOC across 3 adapters, +30 LOC in common | Medium — must preserve Wave-100 kanzi fix + lineageflow compat-shim order |
| 2 | `_seed_from_ids` / `_digest_state` / `_make_ref` re-defined in 5 adapters | Delete the 3 wrappers from each, import + use canonical helpers | -57 LOC across 5 adapters | Low — already done in 6 other adapters byte-stable |
| 3 | `*_resolve_weights_path` is 8 nearly-identical wrappers | Extend `resolve_candidate_paths` in `core.ckpt_loader` to accept (family, filenames) tuple; delegate | ~ -40 LOC across 8 adapters | Low — mnist_fm already uses the framework helper byte-stable |
| 4 | `force_mode` if/elif block is copy-pasted in 3 SOTA adapters | Extract `_resolve_mode(force_mode, ckpt_exists, torch_available, weights_missing_err)` | -30 LOC across 3 adapters | Low — no behaviour change |
| 5 | `hidream_i1._native_states` is unbounded OrderedDict, not NativeStateCache | Replace 2 declarations with `NativeStateCache(...)` | -2 LOC, +2 LOC import | Very low — same `.put`/`.get` interface |
| 6 | `flowmol3_v2_adapter._load_model` returns string sentinel | Replace with class sentinel | +3 LOC | Low — only 1 caller per docstring |
| 7 | Comment drift #1 (hidream_i1 observe) | 5-LOC doc fix | 0 LOC (doc only) | Zero |
| 8 | Comment drift #2 (flowmol3_v2 _make_ref) | 3-LOC doc fix | 0 LOC (doc only) | Zero |
| 9 | Comment drift #3 (kanzi GPT-prior idempotence claim) | 3-LOC code fix: early-return when marker set | +3 LOC | Low — strengthens contract |
| 10 | Comment drift #4 (hidream_i1 LRU claim) | Resolved by fix #5 | 0 LOC | Zero |

**Net LOC delta**: ~ -290 LOC across adapters/, ~ +35 LOC in `_adapter_common.py` / `core.ckpt_loader`. Net: -255 LOC and 5 comment/doc/code drifts closed.

**Acceptance criteria for the fix pass**:
1. D.4 byte-stable regression: `pytest tests/ -k "d4" -q` → 72/72 PASS (no D.4 vector changes)
2. Adapter conformance: `pytest tests/test_adapters/ -q` → no new failures
3. Capability audit: `python tools/capability_audit.py` → G-MASTER 7/7 unchanged
4. Per-adapter smoke: each of kanzi/lineageflow/hidream_i1/flowmol3_v2 boots in `force_mode='auto'` and `force_mode='synthetic'` without raising

**Fix order**:
1. **Dead-code first**: fix #5 (HiDream OrderedDict → NativeStateCache) is 4-LOC and self-contained. Resolves comment drift #4. **Do this first** — establishes the pattern for any future NativeStateCache adopters.
2. **Helper dedup next**: fixes #2 (seed_from_ids/digest_state/make_ref dedup) — 5 adapters × ~12 LOC removed. Already proven byte-stable in 6 prior adapters. **Do this second**.
3. **Weights-path dedup**: fix #3 — extends an existing framework helper. **Third**.
4. **Mode-selection helper**: fix #4 — extracts the force_mode if/elif block. **Fourth**.
5. **Unified SOTA loader**: fix #1 — the largest LOC reduction but the highest risk. **Last** (after the other 4 are byte-stable in D.4).
6. **Comment/doc fixes** (#6, #7, #8, #9, #10): can be batched at any point.

---

REVIEW COMPLETE — found 10 issues across 4 dimensions (duplication 4, loading-path 1, public-API 0, dead-code 1, comment-drift 4).


---

**Wave 149 D.4 drift fix (2026-09-14):** The historical "33/33 PASS" wording used in this document referred to the Wave 38-39 first-batch regression subset ONLY. The current authoritative D.4 count is **72/72 PASS** (33 tests in `tests/test_d4_regression_vectors.py` + 39 tests in `tests/test_adapters/test_regression_vectors.py` = 72 total, per `docs/GATES.md` §D.4 + Wave 106.C.3 standardization). The 72/72 figure includes Wave 32 batches 2/3/4 + Wave 33 batch 2/3 additions (commit `40d979c` and subsequent). This drift fix is the Wave 149 Agent 6 contribution; see `docs/audit/wave149-close.md` for the Wave 149 audit trail.
