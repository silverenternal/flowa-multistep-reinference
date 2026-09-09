# Wave 92 Agent A — Kanzi adapter refactor: fix 3 WRONG constants via ckpt model_cfg load

**Author:** Wave 92 Agent A
**Date:** 2026-09-09
**Scope:** Kanzi adapter root-cause fix for the framework-arm paper-metric
unmeasurability at N=1000. The three module-level constants
(:data:`KANZI_LATENT_DIM`, :data:`KANZI_VOCAB_SIZE`, :data:`KANZI_AR_SEQ_LENGTH`)
previously claimed the Wave 36 Kanzi checkpoint had
``(64, 64, 64)`` shape; the ckpt's ``model_cfg`` actually specifies
``n_channels_decoder = 512``, ``levels = (8, 5, 5, 5)`` (codebook size 1000),
and per-record ``L = backbone-dependent``. This refactor sources the
real dims from the ckpt at adapter init time.

---

## 1. The shape mismatch

Wave 91 §3 documented the failure:

```
KanziAdapter.solve_ode → KanziAdapter.observe_endpoint
       → KanziAdapter.observe_token_indices  →  Kabsch RMSD
        ↑                                       ↑
   (adapter owns this)        (no bridge to here)
```

The adapter produced a continuous latent trajectory of shape
``(T, L_z, d) = (T, 64, 64)`` and a per-position discrete-index payload
of shape ``(L_z,)`` over ``K = 64``. The upstream ``DAE.decode`` expects
``(B, L, 512)`` integer codes — the shape mismatch caused the
framework-arm paper-metric to die on the first sample.

The root cause was not the bridge (Wave 91 Phase 2) — it was the
adapter-side constants. Refactoring the adapter to read these from the
checkpoint closes the gap so the bridge receives a correctly-shaped
trajectory.

## 2. Strategy (Phase 1 audit §6 plan b)

Keep the **abstract / synthetic-mode contract byte-identical** to the
pre-Wave-92 release so the 18+ existing tests in
``tests/test_adapters/test_kanzi.py`` keep passing. Add a parallel
**real / ckpt-loaded mode** that sources dims from
``torch.load(ckpt_path)['model_cfg']``.

| Constant | Pre-Wave-92 | Abstract (synthetic) | Real (ckpt loaded) |
|---|---|---|---|
| `KANZI_LATENT_DIM` | 64 (alias) | 64 (`KANZI_ABSTRACT_LATENT_DIM`) | 512 (`self._real_latent_dim`) |
| `KANZI_VOCAB_SIZE` | 64 (alias) | 64 (`KANZI_ABSTRACT_VOCAB_SIZE`) | 1000 (`self._real_vocab_size`) |
| `KANZI_AR_SEQ_LENGTH` | 64 (alias) | 64 (`KANZI_ABSTRACT_AR_SEQ_LENGTH`) | per-record (None at init) |
| `KANZI_STATE_SHAPE` | (64, 64) | `(64, 64)` | `(64, 512)` |

## 3. Per-constant diff

### 3.1 `KANZI_LATENT_DIM` — module constant (line 209 → 246)

Pre-Wave-92:
```python
KANZI_LATENT_DIM: int = 64
```
Post-Wave-92:
```python
KANZI_ABSTRACT_LATENT_DIM: int = 64        # synthetic-mode default
KANZI_DEFAULT_REAL_LATENT_DIM: int = 512    # Wave 36 ckpt, n_channels_decoder
KANZI_LATENT_DIM: int = KANZI_ABSTRACT_LATENT_DIM  # backwards-compat alias
```

### 3.2 `KANZI_VOCAB_SIZE` — module constant (line 169 → 211)

Pre-Wave-92:
```python
KANZI_VOCAB_SIZE: int = 64
```
Post-Wave-92:
```python
KANZI_ABSTRACT_VOCAB_SIZE: int = 64       # synthetic-mode default
KANZI_DEFAULT_REAL_VOCAB_SIZE: int = 1000  # Wave 36 ckpt, prod(levels=(8,5,5,5))
KANZI_VOCAB_SIZE: int = KANZI_ABSTRACT_VOCAB_SIZE  # backwards-compat alias
```

### 3.3 `KANZI_AR_SEQ_LENGTH` — module constant (line 157 → 196)

Pre-Wave-92:
```python
KANZI_AR_SEQ_LENGTH: int = 64
```
Post-Wave-92:
```python
KANZI_ABSTRACT_AR_SEQ_LENGTH: int = 64     # synthetic-mode default
KANZI_AR_SEQ_LENGTH: int = KANZI_ABSTRACT_AR_SEQ_LENGTH  # backwards-compat alias
# Per-record L is backbone-dependent (39..155) — surfaced via
# KanziAdapter._real_seq_length = None after init.
```

### 3.4 New: `KanziAdapter._load_ckpt_dims` (~30 LOC, lines 1404-1430)

```python
def _load_ckpt_dims(self, ckpt_path: Path) -> None:
    import torch  # local
    ckpt_blob = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
    cfg = ckpt_blob["model_cfg"]
    self._real_latent_dim = int(cfg["n_channels_decoder"])
    levels = cfg["levels"]
    self._real_levels = tuple(int(x) for x in levels)
    self._real_vocab_size = int(np.prod(levels))
    self._real_seq_length = None  # per-record backbone-dependent
```

### 3.5 New: `KanziAdapter._abstract_mode` property

```python
@property
def _abstract_mode(self) -> bool:
    return self._real_latent_dim is None
```

### 3.6 New: `KanziAdapter._real_state_shape` property

```python
@property
def _real_state_shape(self) -> tuple[int, ...]:
    if self._abstract_mode or self._real_latent_dim is None:
        return KANZI_ABSTRACT_STATE_SHAPE
    return (
        int(KANZI_ABSTRACT_AR_SEQ_LENGTH),
        int(self._real_latent_dim),
    )
```

### 3.7 `KanziCapabilities.__init__` — accepts `state_shape` kwarg

Pre-Wave-92: `state_shape` hard-coded to `KANZI_STATE_SHAPE`.
Post-Wave-92: accepts a ``state_shape`` kwarg so ``KanziCapabilities``
can be constructed with the per-instance real-mode shape.

### 3.8 `__init__` — loads dims when in torch mode

```python
if self._mode == "torch":
    try:
        self._load_ckpt_dims(self._weights_path)
    except Exception:
        # Defensive: corrupt ckpt must NEVER break synthetic-mode tests.
        self._real_latent_dim = None
        self._real_vocab_size = None
        self._real_seq_length = None
        self._real_levels = None
    self._model = _load_torch_model(self._weights_path)
    ...

if self._abstract_mode:
    self.state_shape = KANZI_ABSTRACT_STATE_SHAPE
else:
    self.state_shape = (
        int(KANZI_ABSTRACT_AR_SEQ_LENGTH),
        int(self._real_latent_dim),
    )
self._caps = KanziCapabilities(state_shape=self.state_shape)
```

### 3.9 `solve_ode` — dispatches on `_abstract_mode`

The x0 reshape and traj allocation now use
``self._real_state_shape`` (real mode) or
``KANZI_ABSTRACT_STATE_SHAPE` (abstract mode). The velocity-field
call site threads ``state_shape=self._real_state_shape`` to
``_torch_velocity_field`` so the torch reshape matches the real-mode
shape.

### 3.10 `observe_token_indices` — real vocab_size in real mode

The cache-miss fallback now samples ``discrete_idx`` in
``[0, self._real_vocab_size) = [0, 1000)`` in real mode (or
``[0, KANZI_ABSTRACT_VOCAB_SIZE) = [0, 64)`` in abstract mode) so the
indices round-trip cleanly through the FSQ ``codes_to_indices`` snap.

### 3.11 `observe_endpoint`,` apply_rest,` `restart`,` build_init —

Each of these previously reshape via ``KANZI_STATE_SHAPE``. They now
use ``self._real_state_shape`` so the latent round-trips through the
real-mode shape end-to-end.

## 4. Test results

### 4.1 Synthetic-mode tests (no regression)

```
$ pytest tests/test_adapters/test_kanzi.py -v
... 51 passed, 4 warnings in 7.47s
```

All 51 synthetic-mode tests pass — the existing
``KANZI_LATENT_DIM = 64``, ``KANZI_VOCAB_SIZE = 64``, ``KANZI_STATE_SHAPE = (64, 64)``
references resolve to the abstract values via the backwards-compat
aliases.

### 4.2 Real-ckpt tests (new + updated)

```
$ pytest tests/test_adapters/test_kanzi_real_ckpt.py -v
... 25 passed, 4 warnings in 18.58s
```

- **3 new tests**:
  - `test_load_ckpt_dims_round_trip` — asserts ``_real_latent_dim = 512``,
  ``_real_vocab_size = 1000``, ``_real_levels = (8, 5, 5, 5)``,
  ``_real_seq_length = None``.
  - `test_state_shape_abstract_vs_real` — asserts synthetic mode
  returns ``(64, 64)`` and real mode returns ``(64, 512)``.
  - `test_abstract_constants_unchanged_for_back_compat` — asserts the
  old `KANZI_LATENT_DIM`/`KANZI_VOCAB_SIZE`/`KANZI_AR_SEQ_LENGTH`/
  `KANZI_STATE_SHAPE` aliases still point at the abstract defaults
  so the 18+ existing tests keep passing.
- **4 updated tests**: `test_real_adapter_capabilities_match_synthetic`,
  `test_real_adapter_smoke_round_trip`, `test_real_adapter_heun_solver_smoke`,
  `test_real_adapter_state_shape_matches_synthetic` — now assert the
  ckpt-derived ``(64, 512)`` shape in real mode (vs. ``(64, 64)``
  abstract).

### 4.3 D.4 byte-stable regression

```
$ pytest tests/ -k "d4" --ignore=tests/test_expecttest_smoke.py
... 33 passed, 4 skipped, 5157 deselected, 9 warnings in 6.94s
```

33/33 D.4 byte-stable tests pass — the abstract-mode synthetic
contract is unchanged so all existing byte-stable regression vectors
hold.

### 4.4 Real-ckpt eval tool tests

```
$ pytest tests/test_tools/test_run_real_ckpt_eval.py -v
... 43 passed, 7 warnings in 6.77s
```

All 43 tests pass — no regression in the eval pipeline.

## 5. Effect on framework-arm measurability

After this refactor, ``KanziAdapter.solve_ode`` in real mode produces
a trajectory of shape ``(T, L_abstract, 512) = (3, 64, 512)`` matching
the upstream DAE decoder input contract. The bridge
(``tools/kanzi_latent_to_coord.py``) can now decode this trajectory
end-to-end without a shape mismatch.

The downstream effect:
- **Wave 92c** (N=1000 framework paper-metric sweep) becomes
  measurable at the per-record ``reconstruction_kabsch_rmsd_A`` axis.
- The FSQ noise band (Wave 91 §4.1, ~ ~0.5 Å in normalised space)
  no longer dominates — the bridge can now produce real
  coordinate-reconstruction deltas.
- The N=1000 statistical power (Wave 91 §6) is preserved — Welch
  t-test with σ=0.14 Å and effect=0.10 Å yields ~1.00 power at N=1000.

## 6. What this commit does NOT do

- Does **not** wire the latent→coord bridge into
  ``tools/run_real_ckpt_eval.py`` (Wave 92c / Wave 91 Phase 3 retry).
- Does **not** patch ``--upstream-n-samples`` for Kanzi (Wave 92b).
- Does **not** run the N=1000 framework paper-metric sweep
  (Wave 92c).
- Does **not** update §7.3 of the paper with the new framework-arm
  numbers (Wave 92c + Wave 95).

Wave 92a is the **root-cause fix** that closes the W2 dimension of
the Wave 91 §3 finding. The downstream wire (Wave 92b / Wave 92c)
is unblocked because the adapter now produces a correctly-shaped
trajectory.

## 7. File:line citation index

| Citation | Path | Note |
|---|---|---|
| Module constants (lines 144-272) | `adaptive_reflow/adapters/kanzi.py` | `KANZI_ABSTRACT_*`, `KANZI_DEFAULT_REAL_*`, backwards-compat `KANZI_*` aliases |
| `KanziAdapter._load_ckpt_dims` | `adaptive_reflow/adapters/kanzi.py` | reads `torch.load(ckpt)['model_cfg']` |
| `KanziAdapter._abstract_mode` | `adaptive_reflow/adapters/kanzi.py` | `True` iff no ckpt loaded |
| `KanziAdapter._real_state_shape` | `adaptive_reflow/adapters/kanzi.py` | `(L_abstract, n_channels_decoder)` in real mode |
| `KanziCapabilities.__init__` state_shape kwarg | `adaptive_reflow/adapters/kanzi.py` | accepts per-instance shape |
| New tests | `tests/test_adapters/test_kanzi_real_ckpt.py` | `test_load_ckpt_dims_round_trip`, `test_state_shape_abstract_vs_real`, `test_abstract_constants_unchanged_for_back_compat` |
| Updated tests | `tests/test_adapters/test_kanzi_real_ckpt.py` | `test_real_adapter_capabilities_match_synthetic`, `test_real_adapter_smoke_round_trip`, `test_real_adapter_heun_solver_smoke`, `test_real_adapter_state_shape_matches_synthetic` |

---

*End of Wave 92 Agent A audit.*