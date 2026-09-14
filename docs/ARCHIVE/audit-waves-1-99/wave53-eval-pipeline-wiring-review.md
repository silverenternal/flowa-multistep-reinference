# Wave 53 Agent B — eval-pipeline `force_mode` wiring review

**Wave**: 53 Agent B (READ-ONLY review)
**Date**: 2026-09-07
**Scope**: `tools/run_real_ckpt_eval.py` ↔ `adaptive_reflow.adapters.flowmol3` (and cross-adapter impact)
**Status**: review only; no code changes committed here. Fix lands in Wave 53 Agent C.

---

## 1. The wiring mismatch

There are two related `--force-mode real` translation bugs in the eval pipeline. Both surface as soon as a downstream model is requested with `--model flowmol3` or `--model flowmol3_v2` and `--force-mode real` (or `auto`).

### 1.1 Translation site

`tools/run_real_ckpt_eval.py:825-864` (`_resolve_adapter`):

```python
adapter_force_mode = "torch" if force_mode == "real" else force_mode
...
adapter = factory(force_mode=adapter_force_mode)
```

This unconditionally maps the CLI token `"real"` → the legacy adapter token `"torch"` before calling the factory. The CLI choices (declared at `tools/run_real_ckpt_eval.py:2981-2990`) are `("synthetic", "real", "auto")`.

### 1.2 What each factory actually accepts

| Adapter factory | Accepted `force_mode` set | Source line |
|---|---|---|
| `default_kanzi_adapter` | `{"torch", "synthetic", "auto"}` | `kanzi.py:1080, 1175-1191` |
| `default_lineageflow_adapter` | `{"torch", "synthetic", "auto"}` | `lineageflow.py:1133, 1218-1234` |
| `default_freqflow_adapter` | `{"torch", "synthetic", "auto"}` | `freqflow.py:586, 669-685` |
| `default_hidream_i1_adapter` | `{"torch", "synthetic", "auto"}` | `hidream_i1.py:794, 880-896` |
| `default_lumina_image_2_0_adapter` | `{"torch", "upstream", "synthetic", "auto"}` | `lumina_image_2_0.py:777, 859-892` |
| `default_rectified_flow_cifar_adapter` | `{"torch", "synthetic", "auto"}` | `rectified_flow_cifar.py:581, 652-666` |
| `default_graphbfn_adapter` | `{"torch", "synthetic", "auto"}` | `graphbfn.py:584, 666-682` |
| `default_self_flow_adapter` | `{"torch", "synthetic", "auto"}` | `self_flow.py:645, 718-734` |
| `default_wan2_2_video_adapter` | `{"torch", "upstream", "synthetic", "auto"}` | `wan2_2_video.py:628-630, 705-757` |
| `default_protbfn_abbfn_adapter` | `{"torch", "synthetic", "auto", "upstream_jax"}` | `protbfn_abbfn_adapter.py:416, 488-551` |
| `default_flowmol3_adapter` (Wave 50) | `{"synthetic", "real", "auto"}` | **`flowmol3.py:1133, 626`** |
| `default_flowmol3adapter` (v2) | **does NOT accept `force_mode` kwarg** (factory takes `backend="numpy"`, `weights_path`, `device`, `ctmc_enabled`) | **`flowmol3_v2_adapter.py:3207-3233`** |

### 1.3 Two distinct bugs

**Bug A — `flowmol3` (v1 placeholder, Wave 50 Agent A)**

The v1 factory uses the *new* convention `{"synthetic", "real", "auto"}` (it was added by Wave 50 Agent A and the docstring at `flowmol3.py:1116` explicitly states: *"Accepted values (mirrors `tools.run_real_ckpt_eval._resolve_adapter`)"*). The pipeline at line 855 unconditionally translates `"real"` → `"torch"` before calling the factory, so the factory raises:

```
ValueError: unknown_force_mode:torch (expected 'synthetic' | 'real' | 'auto')
```

(see `flowmol3.py:1133-1137`). The cell falls through to `IMPORT_FAILED:...` and the entire flowmol3 real-ckpt run is blocked.

**Bug B — `flowmol3_v2` (real upstream adapter)**

The v2 factory `default_flowmol3adapter` (`flowmol3_v2_adapter.py:3207-3233`) does NOT accept a `force_mode` keyword argument at all — its factory signature is:

```python
def default_flowmol3adapter(
    backend: str = "numpy",
    *,
    num_steps: int = FLOWMOL3ADAPTER_NUM_STEPS_DEFAULT,
    weights_path: Any = None,
    device: str = "cpu",
    ctmc_enabled: bool | None = None,
) -> FlowMol3V2Adapter:
```

So `factory(force_mode="torch")` (after the line-855 translation) raises:

```
TypeError: default_flowmol3adapter() got an unexpected keyword argument 'force_mode'
```

The cell again falls through to `IMPORT_FAILED:...`.

### 1.4 Confirmed working — kanzi + lineageflow

The line-855 translation exists *because* kanzi (and later lineageflow / freqflow / hidream / etc.) use the legacy `"torch"` token for real-mode operation. So `--model kanzi --force-mode real` works today: CLI `"real"` → adapter `"torch"` → kanzi loads the upstream `kanzi.DAE` checkpoint. Same for lineageflow (CLI `"real"` → adapter `"torch"` → loads `lineageflow-rp55.ckpt`).

The 10 legacy adapters are the dominant population; the eval pipeline was tuned for them. Wave 50 Agent A then added flowmol3 with a *new* convention but the pipeline was never updated, and flowmol3_v2 was never given a `force_mode` kwarg at all.

---

## 2. Fix options

### Option A — defensive alias in flowmol3 factory (1 LOC)

Add a "torch" → "real" alias at the top of `FlowMol3Adapter.__init__` (and mirror in `default_flowmol3_adapter`):

```python
if force_mode == "torch":
    force_mode = "real"
```

This is 1 LOC, requires no other change, and unblocks Bug A. It does NOT fix Bug B (flowmol3_v2 still rejects `force_mode`). Wave 50 Agent A would probably prefer this because it is minimal and backward-compatible.

**Pro**: 1 LOC; zero impact on legacy adapters; the eval pipeline's "all flowmol3-family receive the same `force_mode` token" property is preserved.

**Con**: perpetuates the two-convention split (legacy "torch" vs new "real"). Future adapter authors will be confused by the divergence. Does NOT fix flowmol3_v2 (Bug B).

### Option B — change the pipeline translation to a per-model mapping (3 LOC)

Replace the unconditional translation at `tools/run_real_ckpt_eval.py:855` with a per-model mapping:

```python
_ADAPTER_FORCE_MODE_ALIAS: dict[str, dict[str, str]] = {
    "kanzi": {"real": "torch", "synthetic": "synthetic", "auto": "auto"},
    "lineageflow": {"real": "torch", "synthetic": "synthetic", "auto": "auto"},
    "freqflow": {"real": "torch", "synthetic": "synthetic", "auto": "auto"},
    # ...etc for the other legacy-token adapters...
    "flowmol3": {"real": "real", "synthetic": "synthetic", "auto": "auto"},
    # flowmol3_v2 needs Option B.1 (see below)
}
adapter_force_mode = _ADAPTER_FORCE_MODE_ALIAS.get(model, {}).get(force_mode, force_mode)
```

This is 5-10 LOC of plumbing. Does NOT fix flowmol3_v2 by itself (Bug B); needs Option B.1.

**Option B.1** — add `force_mode` kwarg to `default_flowmol3adapter` factory (3 LOC). Mirror the flowmol3 v1 surface: accept `force_mode="synthetic"|"real"|"auto"`, internally map `real|auto` → `backend="torch"` and `synthetic` → `backend="numpy"`. Pure thin shim over the existing `backend` parameter.

```python
def default_flowmol3adapter(
    *,
    force_mode: str = "synthetic",
    backend: str | None = None,  # NEW: optional explicit override
    ...
):
    if force_mode not in {"synthetic", "real", "auto"}:
        raise ValueError(...)
    if backend is None:
        backend = "torch" if force_mode in {"real", "auto"} else "numpy"
    return FlowMol3V2Adapter(backend=backend, ...)
```

**Pro**: semantically clean — CLI token directly matches adapter token for every new-style adapter; legacy adapters continue to receive their legacy token via the explicit mapping; both bugs are fixed in one coordinated change.

**Con**: ~10 LOC of new plumbing; the per-model mapping adds a small maintenance surface (every newly registered adapter needs an entry, or it silently falls through to the identity default).

### Option C — both (defensive; ~12 LOC)

Apply Option A (1 LOC alias in flowmol3) AND Option B + B.1 (pipeline + flowmol3_v2 factory). Most defensive — works regardless of which caller passes which token, and future adapter authors see both conventions accepted.

**Pro**: bullet-proof. Any future adapter that adopts either convention is handled. The Wave 50 / Wave 53 split is bridged.

**Con**: ~12 LOC across 3 files. The "two conventions accepted" property is preserved at the adapter level, which slightly muddies the long-term API story (but the eval pipeline is the only multi-convention caller).

---

## 3. Recommendation

**Option C** — apply both A and B+B.1 in the same Wave 53 Agent C change.

Rationale:

1. **Wave 50 Agent A's new convention is correct.** "real" matches the CLI semantic directly and is what every new adapter should adopt. The Wave 50 deliverable explicitly says *"mirrors `tools.run_real_ckpt_eval._resolve_adapter`"* — that intent needs to be honoured at the pipeline level, not papered over at the adapter level.

2. **Legacy adapters cannot be migrated in this wave.** Kanzi, lineageflow, freqflow, hidream, lumina, rectified_flow_cifar, graphbfn, self_flow, wan2_2_video, protbfn_abbfn — all 10 use `"torch"`. Migrating them is a multi-wave refactor (each adapter's `__init__` + tests + D.4 regression vector + E.1 claim tests). Wave 53 should not block on that.

3. **Both bugs are blocking PHASE-4.** Wave 50 Agent B's flowmol3 real-ckpt eval (the headline PHASE-4 + G.3 evidence on the molecular axis) cannot run with `--force-mode real` until both bugs are fixed. The block has been standing for ~1 week (since Wave 50 commit `ecced10`'s predecessors). Closing it cleanly is more valuable than a quick patch.

4. **Option B's per-model mapping is small.** 5-10 LOC in the eval tool is trivial. The mapping table lives next to `DOWNSTREAM_METRICS` so a future adapter author adding to `DOWNSTREAM_METRICS` is *one grep away* from seeing they also need a mapping entry.

5. **Option A's defensive alias is free.** 1 LOC inside `flowmol3.py` that no other code path notices. If a future caller (not the eval pipeline) drops "torch" into the v1 factory, it still works.

Concretely:

| File | LOC | Change |
|---|---|---|
| `tools/run_real_ckpt_eval.py` | +8 | Add `_ADAPTER_FORCE_MODE_ALIAS` table near `_PAPER_QUANTITY_PROFILES` (~line 660); replace line 855 with `adapter_force_mode = _ADAPTER_FORCE_MODE_ALIAS.get(model, {}).get(force_mode, force_mode)`. |
| `adaptive_reflow/adapters/flowmol3.py` | +1 | Inside `FlowMol3Adapter.__init__` (line 626): `if force_mode == "torch": force_mode = "real"`. Mirror in `default_flowmol3_adapter` (line 1133) for symmetry. |
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py` | +5 | Inside `default_flowmol3adapter` (line 3207): add `force_mode="synthetic"` kwarg that maps to `backend` parameter (defaults `backend` from `force_mode`). |
| `tests/test_adapters/test_flowmol3_force_mode.py` (NEW) | +20 | Add regression test that `--force-mode real` on flowmol3 loads real ckpt (no ValueError, no TypeError); covers both v1 and v2. |

Total: ~34 LOC across 3 files + 1 test.

---

## 4. Cross-adapter impact analysis

Grep results for `force_mode` across `adaptive_reflow/adapters/*.py`:

- **10 legacy `{torch, synthetic, auto}` adapters** — kanzi, lineageflow, freqflow, hidream_i1, lumina_image_2_0, rectified_flow_cifar, graphbfn, self_flow, wan2_2_video, protbfn_abbfn. All continue to work after Option B (pipeline sends "torch" for these via the mapping table). No change required.
- **1 new `{synthetic, real, auto}` adapter** — flowmol3 (Wave 50 Agent A). Bug A fix via Option A (defensive alias) + Option B (pipeline sends "real" directly).
- **1 factory that doesn't take `force_mode`** — flowmol3_v2_adapter. Bug B fix via Option B.1 (add `force_mode` kwarg mapping to `backend`).
- **2 adapters with extra tokens** — `lumina_image_2_0` ("upstream"), `wan2_2_video` ("upstream"), `protbfn_abbfn` ("upstream_jax"). These are outside the eval pipeline's default scope (DOWNSTREAM_METRICS doesn't include them), so no impact. If a future `lumiknowimage_2_0` entry is added to DOWNSTREAM_METRICS, the mapping table needs a `"upstream"` row.
- **No other adapter factories** are wired through `_resolve_adapter`. The eval pipeline is the only multi-convention caller.

No impact on:
- `ADAPTER_REGISTRY` (`adaptive_reflow/adapters/__init__.py`) — registry entries don't consume `force_mode` from the factory; they construct adapters at import time.
- `tests/` — pytest tests construct adapters directly via `default_*_adapter(...)` with their native convention; the eval pipeline is the only multi-convention bridge.
- The capability audit (`tools/capability_audit.py`) — doesn't consume `force_mode`.
- The synthetic eval tool (`tools/run_synthetic_image_eval.py`) — uses default `synthetic` mode only.

---

## 5. What ships in Wave 53 Agent C

Concrete deliverables for Wave 53 Agent C (separate from this review):

1. **Apply Option A** to `adaptive_reflow/adapters/flowmol3.py` (1 LOC alias in `__init__` + mirror in `default_flowmol3_adapter`).
2. **Apply Option B** to `tools/run_real_ckpt_eval.py` (replace line 855 with per-model mapping; add `_ADAPTER_FORCE_MODE_ALIAS` table).
3. **Apply Option B.1** to `adaptive_reflow/adapters/flowmol3_v2_adapter.py` (add `force_mode` kwarg to `default_flowmol3adapter`).
4. **Add regression test** `tests/test_adapters/test_flowmol3_force_mode.py` covering:
   - `default_flowmol3_adapter(force_mode="torch")` succeeds and `_force_mode == "real"`.
   - `default_flowmol3_adapter(force_mode="real")` succeeds.
   - `default_flowmol3adapter(force_mode="torch")` succeeds and loads `backend="torch"` path.
   - `default_flowmol3adapter(force_mode="real")` succeeds and loads `backend="torch"` path.
5. **Run pytest** on `tests/test_adapters/test_flowmol3_force_mode.py` + `tests/test_adapters/test_flowmol3.py` + `tests/test_adapters/test_flowmol3_v2.py` (no regression).
6. **Re-run** `python tools/run_real_ckpt_eval.py --model flowmol3 --force-mode real --seeds 42 --nfe-budgets 50 --composite-metric real` end-to-end and confirm `n_real_computed > 0` (was 0 pre-fix).
7. **Verify + commit** (no push) with message: `Wave 53 Agent C: force_mode wiring fix (Option A+B) closes flowmol3 + flowmol3_v2 PHASE-4 block`.

---

## 6. Quick reference — code sites

| Site | Path | Lines |
|---|---|---|
| CLI `--force-mode` choices | `tools/run_real_ckpt_eval.py` | 2981-2990 |
| Pipeline translation | `tools/run_real_ckpt_eval.py` | 855 |
| `_resolve_adapter` docstring | `tools/run_real_ckpt_eval.py` | 825-846 |
| kanji `force_mode` validator | `adaptive_reflow/adapters/kanzi.py` | 1175-1191 |
| flowmol3 v1 `force_mode` validator (Bug A) | `adaptive_reflow/adapters/flowmol3.py` | 626-631, 1133-1137 |
| flowmol3 v2 factory signature (Bug B) | `adaptive_reflow/adapters/flowmol3_v2_adapter.py` | 3207-3233 |
| `DOWNSTREAM_METRICS` flowmol3 entries | `tools/run_real_ckpt_eval.py` | 450-575 |

---

## 7. Conclusion

The `real→torch` translation in `_resolve_adapter` was correct for the 10 legacy `{torch, synthetic, auto}` adapters. Wave 50 Agent A's adoption of the new `{synthetic, real, auto}` convention for the v1 flowmol3 placeholder broke the translation (Bug A), and the v2 flowmol3 factory never gained a `force_mode` kwarg at all (Bug B). The recommended fix is **Option C** (apply A + B + B.1 in the same Wave 53 Agent C change), yielding ~34 LOC across 3 files plus a regression test. No legacy adapter or test is affected. The fix unblocks the PHASE-4 flowmol3 real-ckpt evaluation (Wave 50 Agent B's open deliverable).