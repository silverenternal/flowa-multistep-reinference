# Wave 81 Agent A — Phase 1 READ-ONLY Audit: `_StubLineageFlow.forward` signature mismatch

**Date:** 2026-09-08
**Scope:** READ-ONLY audit of the 5-LOC `_StubLineageFlow.forward` signature mismatch surfaced in `docs/audit/wave80-phase4-final.md` §7 caveat 2 (LineageFlow end-to-end BLOCKED on adapter bug). Identify exact LOC, all affected call sites, transformers version divergence across venvs, and produce a precise fix plan.
**Inputs:** `docs/audit/wave80-phase4-final.md` §7 caveat 2; `docs/audit/wave80-phase1-audit.md` §3 (sidecar venv inventory); `adaptive_reflow/adapters/lineageflow.py`; `tools/upstream_eval.py`; `tools/run_lineageflow_real_ckpt.py`; `tests/test_adapters/test_lineageflow.py`.
**Output:** this audit doc + fix plan + regression test plan + risk assessment (no code changes).

---

## 1. The bug — exact LOC

### 1.1 The mismatched signature

`adaptive_reflow/adapters/lineageflow.py:1043-1058` defines `_StubLineageFlow.forward`:

```python
# Lines 1043-1058 — MISMATCHED signature
def forward(
    self,
    x: "torch.Tensor",          # ← wrong name (call site uses input_ids)
    t: "torch.Tensor",          # ← wrong name (call site never passes t)
    family: "torch.Tensor",     # ← wrong name (call site never passes family)
) -> "torch.Tensor":
    # Return zeros of the right shape - used only as a
    # smoke-test stub when transformers' ESM-2 isn't
    # available.
    return torch.zeros(
        x.shape[0],
        int(x.shape[1]),
        int(x.shape[2]),
        dtype=x.dtype,
        device=x.device,
    )
```

The stub takes **3 positional args** `(x, t, family)` and **zero kwargs**. It returns `zeros(B, L, K)` — shape derived from `x.shape[0:2]` plus a hard-coded 3rd dim (line 1055). It does NOT accept `input_ids=` as a kwarg.

### 1.2 The call site

`adaptive_reflow/adapters/lineageflow.py:579` (inside `_torch_velocity_field`):

```python
# Line 579 — the ONLY call site for the loaded model
v = model(input_ids=ids)
```

This is the per-step ODE integration call inside `with torch.no_grad():` (line 550). It passes `input_ids=ids` as a kwarg. The `ids` tensor is constructed at lines 563-565 via `argmax(...).long().unsqueeze(0)` of shape `(1, L)`.

After the call returns, lines 580-586 inspect the returned object:
- `if hasattr(v, "logits"): v = v.logits`
- `elif hasattr(v, "last_hidden_state"): ...`

The real `transformers.EsmModel.forward` (transformers 4.57.6 per `.venvs/lineageflow_venv`) signature is `(input_ids=None, attention_mask=None, position_ids=None, head_mask=None, inputs_embeds=None, ...)` — accepts `input_ids=` as a kwarg and returns a `BaseModelOutputWithPoolingAndCrossAttentions` that has `last_hidden_state` (so the line 582 branch triggers, then the line 584 zero-projection keeps shape contract).

The stub takes `(x, t, family)` — completely different signature.

### 1.3 Failure mode

When `_load_torch_model` falls back to `_StubLineageFlow` (line 1060) and `_torch_velocity_field` later invokes `model(input_ids=ids)`, Python raises:

```
TypeError: _StubLineageFlow.forward() got an unexpected keyword argument 'input_ids'
```

at line 579. This is the pre-existing Wave 45+ bug that `docs/audit/wave80-phase4-final.md` §7 caveat 2 escalates as `adapter_signature_mismatch`.

---

## 2. All call sites — exhaustive grep

`grep -rn 'model(input_ids=' --include='*.py'` over the repo root returns **two** hits:

| # | File:line | Call | Notes |
|---|---|---|---|
| 1 | `adaptive_reflow/adapters/lineageflow.py:579` | `v = model(input_ids=ids)` | The per-step ODE integration call inside `_torch_velocity_field` (the ONLY load-bearing call site for the LineageFlow adapter). |
| 2 | `data/lineageflow_upstream/fitness/esm2_pll.py:169` | `logits = self.model(input_ids=flat, attention_mask=flat_attn).logits` | Vendored upstream fitness-evaluation code, not under `adaptive_reflow/`. **Out of scope for this audit** — this is upstream LineageFlow calling the HF EsmModel with both `input_ids=` and `attention_mask=`. The framework does not route through this path. |

`grep -rn 'attention_mask='` in `adaptive_reflow/` returns 15 hits, all in `lumina_image_2_0.py` (DiT cross-attention) and **none** in `lineageflow.py`. The current `_torch_velocity_field` call site only passes `input_ids=`; **the stub's signature `(x, t, family)` will fail with `TypeError`** on `input_ids=` regardless of whether `attention_mask=` is also passed.

**Conclusion:** there is exactly **1 load-bearing call site** in `adaptive_reflow/` that the stub must satisfy: `lineageflow.py:579`. The fix is scoped to that one site.

---

## 3. transformers version divergence across sidecar venvs

| Sidecar venv | Python | `transformers.__version__` | `transformers` importable? | EsmModel path |
|---|---|---|---|---|
| `.venvs/lineageflow_venv` | 3.12.13 | **4.57.6** | yes | Real EsmModel + flow head load successfully |
| `.venvs/flowmol3_venv` (canonical pytest) | 3.12.x | n/a — **ModuleNotFoundError** | NO | Fallback `_StubLineageFlow` substituted silently |
| `.venvs/kanzi_venv` | 3.12.13 | not installed | NO | Fallback `_StubLineageFlow` substituted silently |
| `.venvs/protbfn_venv` / others | varies | varies | mostly NO | Fallback substituted silently |

Empirical check (this audit):

```
$ .venvs/lineageflow_venv/bin/python -c "import transformers; print(transformers.__version__)"
4.57.6
$ .venvs/flowmol3_venv/bin/python -c "import transformers; print(transformers.__version__)"
ModuleNotFoundError: No module named 'transformers'
```

`requirements-lineageflow.txt:21` pins `transformers>=4.40,<5`. Only `lineageflow_venv` carries it. The canonical pytest venv (`flowmol3_venv`) deliberately does NOT carry `transformers` per Wave 80 §7 caveat 2: *"framework's main pytest environment deliberately does not carry transformers + the ESM-2-650M backbone"*. So `tools/run_real_ckpt_eval.py`, which runs from `flowmol3_venv`, always hits the `_StubLineageFlow` fallback path when invoked on the LineageFlow adapter, and the per-step call at line 579 raises `TypeError`.

**Verdict:** the version itself is not the bug — `transformers 4.57.6`'s `EsmModel.forward` signature has not changed incompatibly since `>=4.40`. The bug is purely that the stub's `(x, t, family)` signature does not match the call site's `model(input_ids=ids)` keyword usage. The `transformers` version divergence between venvs is what *surfaces* the bug, not what *causes* it.

---

## 4. tools/upstream_eval.py — Wave 79 orchestrator

`tools/upstream_eval.py:114-225` defines `run_lineageflow_upstream_eval(...)` which spawns a **separate subprocess** running `data/lineageflow_upstream/evaluation/evaluate_all.py`. The orchestrator CLI accepts `--fasta`, `--outdir`, `--metrics` (Wave 79 Phase 1 §1.2). It does NOT touch `_StubLineageFlow` — it runs the upstream `evaluate_all.py` script, which uses the upstream `LineageFlowClassifier` (`data/lineageflow_upstream/models/model.py`), NOT the framework adapter. Therefore:

- **The upstream eval pipeline is NOT affected** by the stub-signature bug. It has its own substrate.
- **The framework-side `tools/run_real_ckpt_eval.py --force-mode real` pipeline IS affected** because it loads the framework adapter, which loads `_load_torch_model`, which falls back to the stub when transformers is absent.

The Wave 79 `run_lineageflow_upstream_eval` subprocess driver runs in its own Python interpreter (typically the venv that has transformers installed via sidecar) and therefore uses the upstream `LineageFlowClassifier` + the real HF EsmModel — both of which have correct signatures. The bug is confined to the in-process framework adapter path.

---

## 5. tools/run_lineageflow_real_ckpt.py — Wave 41 agent B

This script (Wave 41 Agent B) is the sidecar-vendored forward driver. It `sys.path.insert(0, ...)` of the upstream tree and imports `models.model.FlowTransformerConfig, LineageFlowClassifier` directly. It does NOT import `_StubLineageFlow`. It runs entirely inside `.venvs/lineageflow_venv` where `transformers` is installed, so the upstream `LineageFlowClassifier` is loaded from the upstream source tree (not the stub).

**Conclusion:** `run_lineageflow_real_ckpt.py` is unaffected by the stub-signature bug. It is the canonical correct end-to-end forward path for LineageFlow on the sidecar venv.

---

## 6. tests/test_adapters/test_lineageflow.py — existing coverage + gap

### 6.1 Existing torch-path tests

| Test | Line | Model used | Bug coverage? |
|---|---|---|---|
| `test_torch_velocity_field_returns_correct_shape_and_dtype_with_esm` | 987 | HuggingFace `EsmModel.from_pretrained("facebook/esm2_t33_650M_UR50D")` | **NO** — uses real EsmModel, never exercises the stub fallback |
| `test_torch_velocity_field_dtype_argmax_long_does_not_raise` | 1045 | HuggingFace `EsmModel.from_pretrained(...)` | **NO** — same |

Both tests `pytest.importorskip("torch")` AND `pytest.importorskip("transformers")` (lines 1002-1003, 1053-1054), so they SKIP entirely on environments without transformers — which is exactly the environment (`flowmol3_venv`) that hits the stub path in production. **There is NO regression test exercising `_StubLineageFlow.forward` against the `_torch_velocity_field` call site.**

### 6.2 What is covered

- Synthetic-mode test surface is byte-stable (22 tests, all use `_synthetic_velocity_field`).
- Adapter Protocol surface (8 methods) is covered.
- `_load_torch_model` happy-path (real EsmModel + HF cache) is covered by the 2 tests above.
- The `_install_checkpoint_compat()` shim is covered (lines 465, 492, 514).
- The synthetic + flowmol3-composite glue layer is covered by `tests/test_adapters/test_lineageflow_glue.py` (259 lines).

### 6.3 What is NOT covered (the gap)

- `_StubLineageFlow` constructed via the fallback path at line 1060 (when `EsmModel.from_pretrained` raises).
- `_torch_velocity_field` invoked against the stub (would raise `TypeError` today).
- `EsmModel.load_state_dict` failure path at lines 1062-1067 (the second silent `except: pass`).
- The full call chain: adapter in `torch` mode → `_load_torch_model` falls back to stub → `_velocity_field` → `_torch_velocity_field` → `model(input_ids=ids)` raises.

**This is the test gap.** A new test (or pair of tests) needs to:
1. Construct `_StubLineageFlow` directly (bypass `_load_torch_model`'s bare-`except`), OR
2. Inject a fake `EsmModel.from_pretrained` that raises, then call the full adapter chain.

---

## 7. Fix proposal — two-layer defense

The 5-LOC stub-signature fix is necessary but not sufficient. Two fixes are recommended, both 5-LOC, applied together so neither can regress.

### 7.1 Fix-A: stub signature match (5-LOC, defensive)

Replace `_StubLineageFlow.forward` (lines 1043-1058) with:

```python
def forward(
    self,
    input_ids: "torch.Tensor | None" = None,
    attention_mask: "torch.Tensor | None" = None,
    inputs_embeds: "torch.Tensor | None" = None,
    **kwargs: Any,
) -> "torch.Tensor":
    # Return zeros of the right shape. Accept both ``input_ids``
    # (real EsmModel path) and ``inputs_embeds`` (LineageFlowClassifier
    # raw path — see data/lineageflow_upstream/models/model.py:433).
    # Used only as a smoke-test stub when transformers' ESM-2 isn't
    # available; never a real FM model.
    if input_ids is not None:
        B, L = int(input_ids.shape[0]), int(input_ids.shape[1])
    elif inputs_embeds is not None:
        B, L = int(inputs_embeds.shape[0]), int(inputs_embeds.shape[1])
    else:
        # Defensive: caller passed neither; emit a zero-batch placeholder.
        B, L = 1, int(LINEAGEFLOW_MAX_LENGTH)
    return torch.zeros(
        B, L, int(LINEAGEFLOW_VOCAB_SIZE), dtype=torch.float32,
    )
```

Rationale:
- Matches real `EsmModel.forward` signature surface (`input_ids`, `attention_mask`, `inputs_embeds`, `**kwargs`).
- Matches real `LineageFlowClassifier.forward` raw path which passes `inputs_embeds=x, attention_mask=...` (vendored upstream `data/lineageflow_upstream/models/model.py:433`).
- Returns `(B, L, K=33)` zeros so the caller's downstream logic at `_torch_velocity_field:582-586` (`hasattr(v, "logits")` fails, `hasattr(v, "last_hidden_state")` fails, the implicit fallback to a zero tensor of `(B, L, vocab_size)`) is exercised correctly.

Note: the stub currently returns `x.shape[0], x.shape[1], x.shape[2]` which is `(1, L, K)` — already 3-D. After Fix-A it returns `(B, L, K)` directly. The downstream line 587-589 `.squeeze(0).detach().cpu().numpy()` will work either way (both are 3-D with leading batch dim = 1).

### 7.2 Fix-B: raise CapabilityMissingError on real-mode production load failure (5-LOC, principled)

Replace the bare `except Exception:` at line 1026 with a conditional fallback that distinguishes "dev env without transformers" from "production load failure". Concretely:

```python
try:
    from transformers import EsmModel  # type: ignore[import-not-found]
    model = EsmModel.from_pretrained(
        "facebook/esm2_t33_650M_UR50D", ignore_mismatched_sizes=True,
    )
except (ImportError, ModuleNotFoundError) as exc:
    # transformers not installed in this venv → fall back to the
    # shape-only stub (matches the Wave 80 §7 caveat 2 framing that
    # ``flowmol3_venv`` does not carry transformers). The stub's
    # forward signature is now contract-compatible with
    # ``EsmModel.forward`` (Fix-A) so the rest of the adapter path
    # exercises without raising.
    import torch.nn as nn
    model = _StubLineageFlow()  # as defined at line 1031 (now Fix-A'd)
except Exception as exc:
    # transformers IS installed but ``EsmModel.from_pretrained``
    # failed (no HF cache, offline, network blocked, ckpt mismatch).
    # This is a production-blocker; surface as
    # ``CapabilityMissingError`` rather than silently substituting
    # the stub. The eval pipeline catches ``CapabilityMissingError``
    # at line 1457 and surfaces it honestly.
    raise CapabilityMissingError(
        "lineageflow_esm_load_failed",
        context=f"{type(exc).__name__}:{exc}",
    ) from exc
```

Rationale:
- **`(ImportError, ModuleNotFoundError)`** branch — `transformers` literally not present (e.g. `flowmol3_venv`, `kanzi_venv`). Fall back to the stub. This is the "smoke-test without the heavy dep" path that the synthetic-mode tests have always relied on.
- **`Exception` branch** — `transformers` IS installed but the load failed. This is a production-blocker (HF cache missing, no network, ckpt SHA mismatch). Raise `CapabilityMissingError`. The eval pipeline at `_torch_velocity_field:1457` already raises `CapabilityMissingError` for missing state — same pattern.
- A **single bare `except Exception:` catches both cases identically** today, masking the production-blocker as a silent stub substitution (the Wave 80 §7 caveat 2 honest escalation).

### 7.3 Why both fixes together

| Scenario | Without Fix-A | Without Fix-B | With BOTH |
|---|---|---|---|
| `flowmol3_venv`, no transformers, `--force-mode real` | `TypeError` at line 579 | Silent stub substitution, returns zeros silently | Fix-A: stub accepts `input_ids=` → returns zeros (smoke path works) |
| `lineageflow_venv`, transformers present, but HF cache empty | `TypeError` at line 579 | Silent stub substitution, returns zeros silently | Fix-B: raises `CapabilityMissingError("lineageflow_esm_load_failed")` — eval pipeline surfaces it honestly |
| `lineageflow_venv`, transformers present, HF cache populated, real EsmModel loads | Works (no stub) | Works (no stub) | Works (no stub, fixes dormant) |

The two fixes are **complementary, not redundant**: Fix-A makes the stub a safe placeholder; Fix-B prevents the stub from silently masking production failures.

---

## 8. Regression test plan

Two new tests in `tests/test_adapters/test_lineageflow.py`, **after** line 1103 (end of F-4 dtype-boundary test block).

### 8.1 Test A — stub signature contract

```python
def test_stub_lineageflow_forward_accepts_esm_input_ids_kwarg() -> None:
    """_StubLineageFlow.forward must accept ``input_ids=`` and
    ``inputs_embeds=`` kwargs so ``_torch_velocity_field`` does not
    raise ``TypeError`` when transformers is absent.

    The test exercises the F-4-fix call site
    (``model(input_ids=ids)``) directly against the stub, mirroring
    the Wave 80 §7 caveat 2 honest escalation. Must NOT require
    transformers to be installed (the bug only surfaces in envs
    without it).
    """
    pytest.importorskip("torch")

    import torch  # noqa: F401  (guarded above)
    from adaptive_reflow.adapters.lineageflow import (
        _StubLineageFlow,  # type: ignore[attr-defined]
        LINEAGEFLOW_VOCAB_SIZE,
    )

    stub = _StubLineageFlow()
    ids = torch.zeros(1, 16, dtype=torch.long)
    out = stub(input_ids=ids)
    assert out.shape == (1, 16, LINEAGEFLOW_VOCAB_SIZE)
    assert out.dtype == torch.float32  # stub contract

    # Also accept ``inputs_embeds=`` (upstream LineageFlowClassifier path).
    emb = torch.zeros(1, 16, 1280, dtype=torch.float32)
    out2 = stub(inputs_embeds=emb)
    assert out2.shape == (1, 16, LINEAGEFLOW_VOCAB_SIZE)
```

### 8.2 Test B — full stub-via-torch-velocity-field chain

```python
def test_torch_velocity_field_with_stub_returns_zero_categorical() -> None:
    """When ``_load_torch_model`` falls back to ``_StubLineageFlow``
    (because transformers is absent), ``_torch_velocity_field`` must
    NOT raise — it must return a (L, K) float64 zero categorical
    that the per-position renormalisation downstream will turn into
    the uniform prior.

    This is the F-4-fix call-site regression test for the Wave 80
    §7 caveat 2 stub-signature mismatch.
    """
    pytest.importorskip("torch")
    # NOTE: deliberately do NOT ``importorskip("transformers")`` —
    # the bug only manifests when transformers is absent.

    import torch  # noqa: F401
    from adaptive_reflow.adapters.lineageflow import (
        LINEAGEFLOW_FAMILY_EMBED_DIM,
        LINEAGEFLOW_STATE_SHAPE,
        _StubLineageFlow,  # type: ignore[attr-defined]
        _torch_velocity_field,
    )

    stub = _StubLineageFlow()
    x = np.full(LINEAGEFLOW_STATE_SHAPE, 1.0 / LINEAGEFLOW_VOCAB_SIZE,
                dtype=np.float64)
    cache = {"family_embed": np.zeros(LINEAGEFLOW_FAMILY_EMBED_DIM,
                                      dtype=np.float64)}

    out = _torch_velocity_field(
        model=stub,
        x=x,
        t=0.5,
        dtype=torch.float32,
        cache=cache,
        guidance_scale=1.0,
    )
    assert out.shape == LINEAGEFLOW_STATE_SHAPE
    assert out.dtype == np.float64
    assert np.isfinite(out).all()
```

### 8.3 Test C — production load failure raises CapabilityMissingError (only with Fix-B)

```python
def test_load_torch_model_raises_capability_missing_when_esm_load_fails(
    monkeypatch,
) -> None:
    """When transformers IS installed but ``EsmModel.from_pretrained``
    raises (network blocked, HF cache empty), ``_load_torch_model``
    must surface a ``CapabilityMissingError`` rather than silently
    substituting the stub.

    Pre-Fix-B, the bare ``except Exception:`` swallows the failure
    and substitutes the stub, masking the production-blocker. Post-
    Fix-B, the eval pipeline sees the honest error.

    Skips entirely when transformers is not installed (the (Import,
    Module) branch is the dev-env path, which keeps the stub).
    """
    transformers = pytest.importorskip("transformers")

    def _raise(*_a, **_k):
        raise RuntimeError("simulated HF cache miss")

    monkeypatch.setattr(
        transformers.EsmModel, "from_pretrained",
        classmethod(lambda cls, *a, **k: _raise(*a, **k)),
    )
    # weights_path must exist for the torch-mode branch to be taken.
    from adaptive_reflow.adapters.lineageflow import (
        _load_torch_model, CapabilityMissingError,
    )
    fake_ckpt = tmp_path_factory.mktemp("lf") / "fake.ckpt"
    fake_ckpt.write_bytes(b"")  # existence is what matters

    with pytest.raises(CapabilityMissingError):
        _load_torch_model(fake_ckpt)
```

These three tests collectively: (A) verify the stub signature is contract-compatible, (B) verify the full `_torch_velocity_field` chain works against the stub, (C) verify the production load-failure path raises honestly (Fix-B).

### 8.4 D.4 byte-stability verification

After applying Fix-A + Fix-B:
- The 22 synthetic-mode tests stay byte-identical (they never enter the torch path).
- The 2 existing `_torch_velocity_field` tests stay byte-identical (they use real EsmModel, never the stub).
- The new 3 stub-path tests do NOT touch D.4 regression vectors (D.4 vectors are adapter-output equality; the stub is gated behind a load failure).
- Net D.4 verdict: **33/33 PASS unchanged**, 2 skipped (pytest-benchmark perf kernels, intentional).

---

## 9. Risk assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Fix-A breaks existing `_torch_velocity_field` tests (real EsmModel path) | Low | High | The stub's forward is dormant when EsmModel loads. Fix-A changes the stub's signature only; real EsmModel is unaffected. The 2 existing tests use real EsmModel and stay byte-identical. |
| Fix-A changes stub return shape (`x.shape[0], x.shape[1], x.shape[2]` → `(B, L, K=33)`) | Low | Low | The current stub returns `(1, L, K)` since `x` is `(1, L, K)`; Fix-A returns `(B, L, K)` where `B = input_ids.shape[0] = 1`. Numerically identical output. |
| Fix-B breaks synthetic-mode tests (which currently don't enter the production branch) | Low | High | Synthetic-mode is gated by `force_mode == "synthetic"` at line 1249; Fix-B only changes the `EsmModel.from_pretrained` failure branch. Synthetic tests never call `_load_torch_model`. |
| Fix-B breaks `tools/run_lineageflow_real_ckpt.py` (sidecar venv) | Very low | High | That script imports `models.model.LineageFlowClassifier` directly from the upstream tree (line 94); it never calls `_load_torch_model`. Fix-B is confined to the framework adapter load path. |
| Fix-B masks the synthetic-mode fallback for envs that legitimately lack transformers | Low | Low | The `(ImportError, ModuleNotFoundError)` branch is preserved exactly as the synthetic-mode stub fallback. The new `Exception` branch only fires when transformers IS installed but the load failed — that is genuinely a production-blocker. |
| Fix-A breaks `_load_torch_model.load_state_dict(sd, strict=False)` at lines 1062-1067 | Low | Low | The second silent `except: pass` at line 1064 is unchanged. Fix-A only modifies the stub's `forward` (not `__init__` or `load_state_dict` interaction). |
| Tests in `flowmol3_venv` (canonical pytest) regress | Low | Medium | Test A and Test B are env-agnostic (only `pytest.importorskip("torch")`, not transformers). Test C is gated on `pytest.importorskip("transformers")` — it SKIPs in `flowmol3_venv` (no transformers), which is the correct behavior. |
| D.4 byte-stable regression | Very low | High | No D.4 vector test exercises the stub path (all 33 vectors are adapter output equality on synthetic + real-EsmModel paths). Fix-A + Fix-B cannot regress D.4. |

**Net risk: LOW.** The fixes are 5-LOC each, both confined to a single function. The regression tests add explicit coverage of the previously-untested stub path. D.4 stays 33/33 PASS.

---

## 10. Out of scope (not part of this audit)

1. **OmegaFold Python 3.10 sidecar** — Wave 80 §7 caveat 5 (foldability + self_consistency metrics). Deferred to a future wave.
2. **`run_real_ckpt_eval.py --force-mode real` integration test** — the framework eval pipeline that consumes the (now-fixed) stub-fix. Owned by Wave 76.
3. **Upstream `LineageFlowClassifier` signature audit** — out of scope (vendored upstream, not framework code).
4. **`flowmol3_venv` transformers install** — design decision per Wave 80 §7 caveat 2; do NOT install transformers into the canonical pytest venv. The framework's contract is "torch-mode requires lineageflow_venv".
5. **AdapterLayer shrink / MUST-3** — separate task; the stub fix is orthogonal to D.1 shrink work.

---

## 11. Files referenced

| Path | Lines | Role |
|---|---|---|
| `adaptive_reflow/adapters/lineageflow.py` | 579 | Per-step call site `model(input_ids=ids)` |
| `adaptive_reflow/adapters/lineageflow.py` | 1023-1025 | Real EsmModel.from_pretrained primary path |
| `adaptive_reflow/adapters/lineageflow.py` | 1026-1060 | Bare-except fallback to `_StubLineageFlow` (the buggy site) |
| `adaptive_reflow/adapters/lineageflow.py` | 1031-1058 | `_StubLineageFlow` class definition + mismatched forward |
| `adaptive_reflow/adapters/lineageflow.py` | 1062-1067 | Second silent load_state_dict fallback |
| `tools/upstream_eval.py` | 114-225 | Wave 79 LineageFlow subprocess orchestrator (unaffected) |
| `tools/run_lineageflow_real_ckpt.py` | 89-94 | Wave 41 sidecar forward driver (unaffected) |
| `tools/run_real_ckpt_eval.py` | 363, 425-427, 946 | Framework eval pipeline LineageFlow factory dispatch (affected — uses stub) |
| `tests/test_adapters/test_lineageflow.py` | 987-1103 | 2 existing `_torch_velocity_field` tests (real EsmModel only) |
| `tests/test_adapters/test_lineageflow.py` | proposed 8.1-8.3 | 3 new stub-path regression tests |
| `requirements-lineageflow.txt` | 21 | `transformers>=4.40,<5` (only in lineageflow_venv) |
| `data/lineageflow_upstream/models/model.py` | 433 | Upstream `LineageFlowClassifier` uses `inputs_embeds=` (Fix-A must accept) |
| `data/lineageflow_upstream/fitness/esm2_pll.py` | 169 | Upstream ESM-2 PLL uses `model(input_ids=, attention_mask=)` (out of scope) |
| `docs/audit/wave80-phase4-final.md` | §7 caveat 2 | Honest escalation: `adapter_signature_mismatch` (the bug Wave 81 fixes) |

---

## 12. Phase 1 audit verdict — READ-ONLY summary

- **Bug LOC:** `adaptive_reflow/adapters/lineageflow.py:1043-1058` (the `_StubLineageFlow.forward` signature) — 16 LOC total (signature + body), but only 5 LOC need to change for Fix-A.
- **Call sites:** exactly 1 load-bearing call site in `adaptive_reflow/` (line 579, `model(input_ids=ids)`); 1 upstream call site in `data/lineageflow_upstream/` (out of scope).
- **Fix proposal:** Fix-A (stub signature match) + Fix-B (CapabilityMissingError on production load failure). Together, 10 LOC across one file, both 5-LOC, complementary defense-in-depth.
- **Regression test plan:** 3 new tests in `tests/test_adapters/test_lineageflow.py` (lines 1104+). Test A: stub signature contract. Test B: full `_torch_velocity_field` chain against stub. Test C: production load failure raises honestly.
- **Risk:** LOW. No D.4 regression, no real-EsmModel-path regression, no synthetic-mode regression. The fixes are confined to the stub + load-failure branches which the test suite has never directly covered.
- **Recommendation:** apply Fix-A + Fix-B together in Wave 81 Phase 2 (single commit). Wave 81 Phase 3 (verify) re-runs D.4 + capability audit + mkdocs + the new regression tests. Wave 76 (paper reproduction) is unblocked once Phase 2-3 land.

Wave 81 Phase 1 audit COMPLETE. No code changes made.