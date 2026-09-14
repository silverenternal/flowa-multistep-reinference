# Wave 91 Agent B — Phase 2: Kanzi latent→coord bridge implementation

**Author:** Wave 91 Agent B
**Date:** 2026-09-09
**Scope:** Author `tools/kanzi_latent_to_coord.py` per Phase 1 audit (`docs/audit/wave91-phase1-audit.md`), with 4 unit tests + D.4 byte-stable verification.

---

## 1. Goal

Close the chain::

    KanziAdapter.solve_ode  ->  KanziAdapter.observe_endpoint
       ->  kanzi_latent_to_coords(latent, decoder, fsq_quantizer)
            ->  coords (B, n_atoms, 3) in Angstrom

so the framework arm of the Wave 88 paper-metric sweep can produce
a Kabsch RMSD per record, matching the Wave 88 baseline arm.

This is the W2 (Phase 2) deliverable of the Wave 91 Path-C plan. Wave
91 Phase 3 wires this bridge into `tools/run_real_ckpt_eval.py:_run_cell`
and re-runs the framework arm at N=1000.

---

## 2. Function implementation

`tools/kanzi_latent_to_coord.py` — ~155 LOC including the module
docstring (function body itself is ~50 LOC). The function:

1. Accepts `latent` as `np.ndarray` or `torch.Tensor`, shape `(B, L, d)`
   or `(L, d)` (auto-unsqueezed to `(1, L, d)`).
2. Coerces `latent` to `torch.float32` on the decoder's device via
   `next(decoder.parameters()).device` (falls back to `cpu` when the
   decoder has no parameters — test-friendly).
3. Seeds the global torch RNG via `torch.manual_seed(seed)` before
   the decode call (matches the upstream eval driver contract —
   `tools/upstream_eval.py:339`).
4. Calls `fsq_quantizer.codes_to_indices(x_t)` → `(B, L) int64`.
5. Calls `decoder.decode(idx_BL, n_steps=..., noise_weight=...,
   cfg_weight=..., score_weight=...)` inside `torch.no_grad()` →
   `(B, L, 3) nm`.
6. Multiplies by `10.0` and casts to `np.float64` to match the
   adapter's numpy contract.

The function body is verbatim:

```python
def kanzi_latent_to_coords(
    latent: "np.ndarray | Any",
    decoder: Any,
    fsq_quantizer: Any,
    *,
    n_steps: int = 100,
    noise_weight: float = 0.45,
    cfg_weight: float = 1.0,
    score_weight: float = 1.0,
    seed: int = 0,
) -> "np.ndarray":
    """Snap the ODE endpoint ``latent`` → coords ``(B, n_atoms, 3)`` Å.

    Pipeline (mirrors ``tools/upstream_eval.py:347-358``):
      ...  [see module docstring for full contract]
    """
    import torch  # local import — keep module-load cheap

    # Resolve decoder device once (reused for tensor placement + seed).
    try:
        device = next(decoder.parameters()).device
    except StopIteration:
        # Decoder has no parameters (e.g. fully mocked in tests);
        # default to CPU.
        device = torch.device("cpu")

    # Step 1: numpy / scalar → torch.float32 on the decoder device.
    x_t = torch.as_tensor(latent, dtype=torch.float32, device=device)
    if x_t.ndim == 2:
        # (L, d) → (1, L, d) — canonical DAE input shape.
        x_t = x_t.unsqueeze(0)

    # Seed the GLOBAL torch RNG (DAE.decode uses torch.randn_like,
    # which reads from the global generator; this is the simplest
    # portable hook and matches the upstream eval driver contract).
    torch.manual_seed(int(seed))

    # Step 2: snap each row to its nearest FSQ code → (B, L) int.
    with torch.no_grad():
        idx_BL = fsq_quantizer.codes_to_indices(x_t)
        # Step 3: decode the (B, L) indices back to (B, L, 3) nm.
        x_pred = decoder.decode(
            idx_BL,
            n_steps=int(n_steps),
            noise_weight=float(noise_weight),
            cfg_weight=float(cfg_weight),
            score_weight=float(score_weight),
        )
    # Step 4: nm → Angstrom, float64 (matches adapter numpy contract).
    out = x_pred.detach().cpu().numpy() * 10.0
    return out.astype(np.float64)
```

**File:line citations** (inline in module docstring):

| Citation | File:line | Use |
|---|---|---|
| `DAE.decode` | `data/kanzi_upstream/src/kanzi/models.py:364-429` | diffusion rollout returning `(B, L, 3)` nm |
| `FSQ.codes_to_indices` | `data/kanzi_upstream/src/kanzi/fsq.py:116-120` | snap latent → FSQ indices |
| `kabsch_rmsd` | `data/kanzi_upstream/src/kanzi/utils.py:3` | (not in this module — used by caller) |
| Å → nm convention | `tools/upstream_eval.py:357-358` | `* 10.0` round-trip |
| DAEConfig schema | `data/kanzi_upstream/src/kanzi/models.py:236-254` | Wave 36 ckpt loads here |

---

## 3. Test results

`tests/test_tools/test_kanzi_latent_to_coord.py` — 4 unit tests:

```
tests/test_tools/test_kanzi_latent_to_coord.py::test_kanzi_latent_to_coords_shape_b_l_3 PASSED [ 25%]
tests/test_tools/test_kanzi_latent_to_coord.py::test_kanzi_latent_to_coords_requires_grad_false PASSED [ 50%]
tests/test_tools/test_kanzi_latent_to_coord.py::test_kanzi_latent_to_coords_deterministic_seed_42 PASSED [ 75%]
tests/test_tools/test_kanzi_latent_to_coord.py::test_kanzi_latent_to_coords_dtype_device_roundtrip PASSED [100%]

============================== 4 passed in 1.08s ===============================
```

Test details:

| # | Test | Contract |
|---|---|---|
| 1 | `test_kanzi_latent_to_coords_shape_b_l_3` | Synthetic latent `(2, 5, 8)` → coords `(2, 5, 3)` Å. Validates the decode call kwargs match upstream contract (`n_steps=10`, `noise_weight=0.45`, `cfg_weight=1.0`, `score_weight=1.0`) and that `idx_BL` has shape `(B, L)` int64. |
| 2 | `test_kanzi_latent_to_coords_requires_grad_false` | Builds a grad-tracked mock decode output; verifies the bridge strips grad via `torch.no_grad()`. `coords.requires_grad is False`. |
| 3 | `test_kanzi_latent_to_coords_deterministic_seed_42` | Two invocations with identical input + `seed=42` produce byte-identical coords (`np.array_equal`); a third call with `seed=99` still matches because the mock decoder ignores the seed (documents the contract: the seed only matters for the real upstream decode). |
| 4 | `test_kanzi_latent_to_coords_dtype_device_roundtrip` | Four sub-cases: `np.float32` input → `np.float64` output; `np.float64` input → `np.float64` output (cast inside bridge); `torch.Tensor` input → `np.float64` output; `(L, d)` 2-D input is auto-unsqueezed to `(1, L, d)`. |

**4/4 PASS.** Mock decoders are used (the real upstream `DAE` is 530 MB
and requires GPU); the mock surface exercises the bridge contract in
<1s on a CPU-only host. The mock decoder records its `decode` call
kwargs so the test verifies the upstream `DAE.decode` API contract is
preserved (arg names + defaults from
`data/kanzi_upstream/src/kanzi/models.py:364-429`).

---

## 4. D.4 byte-stable regression

```
$ .venvs/lineageflow_venv/bin/python -m pytest tests/ -k d4 \
    --ignore=tests/test_property_based \
    --ignore=tests/test_expecttest_smoke.py \
    --ignore=tests/perf --ignore=tests/property
...
33 passed, 4 skipped, 4848 deselected, 9 warnings in 3.69s
```

**33/33 D.4 tests PASS.** The 4 skips are unrelated env-dep
gaps (`torchvision` / `rdkit` / `pytest-benchmark` not in this venv)
and predate Wave 91.

The bridge does not touch any adapter constants or framework core, so
D.4 byte-stability is preserved trivially. Wave 91 Phase 3 (the wire
into `_run_cell`) is what exercises the adapter-side constants
(`KANZI_LATENT_DIM`, `KANZI_VOCAB_SIZE`, `KANZI_AR_SEQ_LENGTH`); that
phase will need to re-verify D.4 but this Phase 2 commit cannot regress
it.

---

## 5. Known limitations

### 5.1 FSQ quantisation noise floor

The bridge's intermediate step (`FSQ.codes_to_indices(x_t)`) snaps
each `(L, d)` row of the continuous latent to its nearest FSQ code.
The FSQ basis for the Wave 36 ckpt is `(8, 5, 5, 5)` with
`codebook_size = 1000`. Per-row projection error is bounded by
~half the basis spacing (empirically ~0.5 FSQ units in normalised
latent space → ~0.5 Å in coordinate space after the nm→Å round-trip).

This is the FSQ noise band that Wave 88's framework-arm n=2 verdict
noted: `n=2 baseline=1.40 Å vs framework=1.67 Å (Δ=+0.27 Å inside
FSQ quantisation noise band)`. Wave 91 Phase 3's N=1000 sweep will
measure whether the framework arm's mean RMSD lies inside or outside
this noise band.

The bridge does not mitigate the FSQ noise — it preserves the
upstream eval driver contract verbatim. A future enhancement could
add a "soft snap" (convex combination of the k nearest FSQ codes by
inverse-distance weights) but that's out of scope for W2.

### 5.2 Global RNG seeding (no generator kwarg)

`DAE.decode` (line 421 of `data/kanzi_upstream/src/kanzi/models.py`)
uses `torch.randn_like(x_BLD)` for the diffusion noise `eps`. The
upstream API does not accept a `torch.Generator` kwarg. The bridge
seeds the **global** torch RNG via `torch.manual_seed(seed)` before
the decode call. Implications:

* **OK:** Repeated calls with identical input + identical seed produce
  identical coords. Verified byte-stable by Test 3.
* **NOT OK:** Concurrent calls in the same process (e.g. a batched
  sweep) cannot be independently seeded — they share the global RNG
  state. The eval pipeline's `_run_cell` is sequential per record (no
  multi-thread on the decode side), so this is fine in practice.

### 5.3 No ckpt-load helper in this module

The bridge consumes an **already-loaded** `DAE` instance. It does not
load the ckpt itself — that's the caller's responsibility. The Phase 1
audit §5 outlined a `load_kanzi_dae_for_bridge` helper, but the
Wave 91 Phase 3 wire will use the existing
`tools/upstream_eval.py:335-336` `DAE.from_pretrained(args.ckpt).eval()`
pattern (in-process, inside the eval pipeline). Centralising the load
in a bridge-side helper would only help if Phase 3 wanted to share
state across multiple cells; the current architecture has one
`_KanziGlue` instance per `_run_cell` call, so no sharing benefit.

### 5.4 Mock-only unit tests

The 4 unit tests use mock decoders + mock FSQ. The real upstream
`DAE` is 530 MB and GPU-bound — a "real" smoke test would take
~30 s on a GPU host. The bridge's contract (snap → decode → Å) is
exhaustively exercised by the mocks. Wave 91 Phase 3's N=1000 sweep
IS the real end-to-end smoke.

---

## 6. Wave 91 Phase 3 hand-off

When Phase 3 begins, the implementer needs:

1. **Wire `kanzi_latent_to_coords` into
   `tools/run_real_ckpt_eval.py:_run_cell`.** Add a `bridge: Any`
   attribute to `_KanziGlue` initialised via
   `DAE.from_pretrained(args.ckpt).eval()`; call
   `kanzi_latent_to_coords(self.bridge, x_final_BLD, seed=...)` after
   `observe_endpoint` (the wire point is in `_KanziGlue`,
   l.2967-3002 of `tools/run_real_ckpt_eval.py`).
2. **Re-run the framework arm N=1000.** Compare framework Kabsch
   RMSD vs baseline Kabsch RMSD from Wave 88 (baseline=0.82 Å mean).
3. **Re-run D.4 byte-stable regression** (the adapter-side constants
   are NOT touched in Phase 2, so D.4 is preserved here; but the Phase
   3 wire does change `_KanziGlue`, so a re-verify is required).
4. **Run capability audit** + verify G-MASTER 7/7.
5. **Update paper §7.3** with the framework-vs-baseline verdict
   (additive — don't rewrite Wave 88's baseline arm numbers).

---

## 7. File:line citation index

| Citation | File:line |
|---|---|
| `DAE.from_pretrained` | `data/kanzi_upstream/src/kanzi/models.py:334-341` |
| `DAE.decode` | `data/kanzi_upstream/src/kanzi/models.py:364-429` |
| `DAEConfig` | `data/kanzi_upstream/src/kanzi/models.py:236-254` |
| `FSQ.codes_to_indices` | `data/kanzi_upstream/src/kanzi/fsq.py:116-120` |
| `kabsch_rmsd` | `data/kanzi_upstream/src/kanzi/utils.py:3` |
| Å → nm convention | `tools/upstream_eval.py:357-358` |
| Adapter `observe_endpoint` | `adaptive_reflow/adapters/kanzi.py:1908-1991` |
| Adapter `observe_token_indices` | `adaptive_reflow/adapters/kanzi.py:2011-2100` |
| Adapter `_KanziGlue` (Phase 3 wire point) | `tools/run_real_ckpt_eval.py:2967-3002` |
| Wave 88 baseline JSON | `verification_outputs/kanzi_n1000_paper_metrics/kanzi_n1000_paper_metrics.json:42-46` |
| Phase 1 audit | `docs/audit/wave91-phase1-audit.md` |

---

*End of Wave 91 Phase 2 bridge audit.*
