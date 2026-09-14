# Wave 91 Agent A — Phase 1 READ-ONLY audit: Kanzi latent→coord bridge

**Author:** Wave 91 Agent A (READ-ONLY)
**Date:** 2026-09-09
**Scope:** Kanzi protein flow-AE framework-arm measurability gap.
**Goal:** Produce a precise plan for Wave 91 Phase 2 (the latent→coord bridge code)
so the framework arm can be measured at N=1000 on the paper's headline metric
(reconstruction Kabsch RMSD in Ångström).

---

## 1. The measurability gap (Wave 88 verbatim)

From `verification_outputs/kanzi_n1000_paper_metrics/kanzi_n1000_paper_metrics.json`
(line 42-46):

```json
"verdict": {
    "arm": "baseline_only",
    "framework_arm_source": "Wave 79 Phase 3: n=2 baseline=1.40 Å vs
     framework=1.67 Å (Δ=+0.27 Å inside FSQ quantisation noise
     band); not re-run at N=1000 here (the framework arm requires the main
     repo's adapter solver + GPT-prior restart-blend which is wired only
     through tools/run_real_ckpt_eval.py ..."
}
```

The baseline arm is measurable (Wave 88 produced N=200 recon RMSD at
0.82 Å mean). The **framework arm is not measurable end-to-end at
N=1000** because the chain

```
KanziAdapter.solve_ode → KanziAdapter.observe_endpoint
       → KanziAdapter.observe_token_indices  →  Kabsch RMSD
        ↑                                       ↑
   (adapter owns this)        (no bridge to here)
```

is missing the central arrow. The adapter produces a continuous latent
trajectory of shape `(T, L_z, d)` and a per-position discrete-index
payload of shape `(L_z,)`, but nothing in the adapter or eval pipeline
takes those indices and runs them through the upstream
``DAE.decode(idx_BL)`` → ``kabsch_rmsd`` loop. Wave 91 Phase 2 closes
this gap.

## 2. Current framework plumbing (read)

### 2.1 Adapter — `adaptive_reflow/adapters/kanzi.py`

**Path-side state shape (lines 152-227):**

| Constant | Value | Reality (Wave 36 ckpt, see §4) | Status |
|---|---|---|---|
| `KANZI_LATENT_DIM` (l.152) | `64` | `n_channels_decoder = 512` (cfpt cfg) | **WRONG** |
| `KANZI_AR_SEQ_LENGTH` (l.157) | `64` | per-backbone `L` (e.g. 39 for 1s7mB01, 100 for 2hoxA01, 155 for 6nrzA01) | **WRONG** |
| `KANZI_VOCAB_SIZE` (l.169) | `64` | `prod(levels) = 8*5*5*5 = 1000` | **WRONG** |
| `KANZI_STATE_SHAPE` (l.220) | `(64, 64)` | `(L, 512)` — backbone-dependent | **WRONG** |

All three "WRONG" lines are the load-bearing adapter-side constants
that prevent the adapter from round-tripping real Kanzi ckpt data.
Wave 91 Phase 2 must either (a) refactor the adapter to read these
from `DAEConfig` at ckpt-load time, or (b) keep the adapter's
`(64, 64)` synthetic shape but consume **only the indices** from the
trajectory endpoint via the FSQ quantizer.

**The eight Protocol methods (l.1314-2285):**

1. `capabilities()` — `KANZICapabilities` dataclass (l.1022-1056) declares
   `state_shape = (64, 64)`. This is the wrong shape — Wave 91
   Phase 3 must surface the real DAEConfig shape here so callers can
   pre-allocate without hard-coding.
2. `build_initial_state()` (l.1314-1403) — `x0` shape `(L_z, d) =
   (64, 64)` per `_synthesize_latent_like_tensor` (l.595). Synthetic
   mode only.
3. `export_endpoint()` (l.1409-1416) — identity pass-through.
4. `detach_and_validate_endpoint()` (l.1422-1430) — validation only.
5. `apply_restart_distribution()` (l.1436-1641) — restart blend in
   latent space. Wave 45 Agent F wired
   `KanziGPTPriorRestartPolicy` here; the GPT-prior logits key is
   `gpt_prior_logits` on the prior entry (l.858).
6. `compose_condition()` (l.1647-1719) — family-id / CFG / num_steps
   conditioning resolution.
7. `solve_ode()` (l.1754-1902) — Euler/Heun integration on the
   `(L_z, d)` latent; calls `self._velocity_field(...)` (l.1725-1752)
   which dispatches to `_torch_velocity_field` (l.900-944) when in
   `torch` mode. Output: trajectory `traj[T, L_z, d]` and
   `ODEIntegratorTrace`.
8. `observe_endpoint()` (l.1908-1991) — extracts `x_final =
   trajectory[-1]` shape `(L_z, d)` and stores under
   `endpoint_digest`.
9. `observe_token_indices(trace, paper_quantities)` (l.2011-2100) —
   walks the native-state chain back to find a prior entry with
   `discrete_idx` (shape `(L_z,)` over `[0, KANZI_VOCAB_SIZE=64)`).
   **This is the natural handoff point for the bridge** — but the
   indices it currently emits are NOT from the real FSQ quantizer
   (they're from `_synthesize_discrete_token_indices`, l.600).

### 2.2 Eval pipeline — `tools/run_real_ckpt_eval.py`

The framework-arm path for Kanzi is wired at:

* **l.2967-3002** — `class _KanziGlue` holds a reference to
  `KanziAdapter`. (Forward-declared `Any` to dodge the circular
  import flagged Wave 41 Agent C.)
* **l.4148-4214** — the per-cell runner thread that calls
  `solve_ode` + `observe_endpoint` + the downstream metric
  computation.

**The exact missing wire:** the eval pipeline reads
`observe_token_indices(trace, paper_quantities)` and gets a dict
keyed by `"discrete_token_index"` mapping to an `(L_z,)`` float64
array (l.2181-2194). The Wave 91 Phase 2 bridge takes this dict +
the loaded DAE and produces `(L, 3)` coords in Ångström, then runs
`kabsch_rmsd(coords, reference_coords)` against the FASTA-extracted
reference.

### 2.3 Reference extraction — `tools/extract_ca_coords_for_kanzi.py`

Already produces one ``>seq_N`` header + comma-separated
``x,y,z`` triplet list per record (l.30-32 docstring). N=1000 over
4 PDBs (250 each). The reference coords in Ångström are read by the
upstream driver at `tools/upstream_eval.py:347-358` (see §3 below).
The bridge consumes the same format — no new reference extraction
work is needed.

## 3. Upstream forward pipeline (read)

### 3.1 `DAEConfig` — `data/kanzi_upstream/src/kanzi/models.py:237-254`

```python
@dataclass
class DAEConfig:
    n_channels_decoder: int
    n_channels_encoder: int
    n_layers_encoder: int
    n_layers_decoder: int
    n_heads: int
    mlp_factor: int
    use_qknorm: bool
    sigma: float = 0.0
    levels: tuple[int] = (8, 8, 8, 8)  # 4096
    drop_cond_p: float = 0.0
    conditioning_type: str = "cat"
    n_channels_pair: int = -1
    n_neighbors: int = 32
    encoder_type: str = "xformer"
    gpt_prior: bool = False
    ...
```

### 3.2 `DAE.__init__` — `models.py:260-332`

* Builds `self.quantize = FSQ(levels, dim_out=cfg.n_channels_decoder,
  dim=cfg.n_channels_encoder, jitter_spread=0.0)` (l.266-271).
  → `codebook_size = prod(levels)`, `project_in` maps
  `n_channels_encoder → effective_codebook_dim`,
  `project_out` maps `effective_codebook_dim → n_channels_decoder`.
* Builds `self.net = DiT(n_channels=cfg.n_channels_decoder, ..., channels_in=3)`
  (l.308-318) — the diffusion network that scores the coords.
* Optionally builds `self.gpt = GPT(...)` (l.320-332) when
  `cfg.gpt_prior=True`.

### 3.3 `DAE.encode` — `models.py:346-362`

```python
def encode(self, x_BLD, preprocess=False):
    # always mean-center
    x_BLD = x_BLD - x_BLD.mean(dim=1, keepdim=True)
    B, L, D = x_BLD.shape  # D = 3
    pair_BLLD = None
    if self.pair_bias:
        pair_BLLD = self.pair_embedder(x_BLD)
    s_BLD = self.up(x_BLD)  # (B, L, n_channels_encoder)
    s_BLD = self.encoder(s_BLD, pair_bias_BLLD=pair_BLLD)
    c_BLD, idx_BL = self.quantize(s_BLD)  # c_BLD: (B, L, n_channels_decoder); idx_BL: (B, L) int
    return s_BLD, c_BLD, idx_BL
```

### 3.4 `DAE.decode` — `models.py:364-429`

```python
def decode(
    self,
    idx_BL,                       # (B, L) int tensor in [0, codebook_size)
    n_steps=100,                  # diffusion steps
    noise_weight=0.45,
    score_weight=1.0,
    cfg_weight=1.0,
    g_fn=None,
):
    c_BLD = self.quantize.indices_to_codes(idx_BL)  # → (B, L, n_channels_decoder)
    device = c_BLD.device
    x_BLD = torch.randn(*c_BLD.shape[:-1], 3, device=device)  # (B, L, 3)
    x_BLD = x_BLD - x_BLD.mean(dim=1, keepdim=True)
    t = torch.linspace(0, 1, n_steps, device=device)
    gt = self.get_gt(t)
    dt = t[1] - t[0]

    # loop over diffusion steps: v, v0, vcfg; score, score0, scorecfg;
    # eps, std_eps; delta_x; x_BLD = x_BLD + delta_x
    # ...

    return x_BLD  # (B, L, 3) in nm (matches encode's input scale)
```

**Key invariant:** `DAE.encode(x).round-trip via DAE.decode(idx)`
gives coordinates in the same units (nm after the `/10.0`
division in the eval driver) as the input. This is the round-trip
RMSD the Wave 88 baseline arm measures.

### 3.5 `FSQ` — `data/kanzi_upstream/src/kanzi/fsq.py:42-187`

Critical API:

* `indices_to_codes(indices, project_out=True)` (l.122-144) — given
  `(B, L)` int indices, returns `(B, L, dim)` codes. With
  `project_out=True` (default) the shape is `(B, L, n_channels_decoder)`.
* `codes_to_indices(zhat)` (l.116-120) — inverse: given
  `(B, L, codebook_dim)` codes, returns `(B, L)` indices via the
  basis decomposition `(zhat * basis).sum(dim=-1)`.
* The `quantize` method (l.102-106) implements straight-through
  rounding; `quantize.forward(z)` returns
  `(zhat, indices)`. This is what `DAE.encode` calls.

### 3.6 The eval driver — `tools/upstream_eval.py:325-374`

```python
sys.path.insert(0, str(_KANZI_SRC))  # vendor upstream on sys.path
import torch
from kanzi import DAE, kabsch_rmsd

raw = DAE.from_pretrained(args.ckpt).eval()
rmsd_by_seq = {}
with open(args.input, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith(">"):
            continue
        vals = [float(t) for t in line.split(",") if t.strip()]
        if len(vals) < 3 or len(vals) % 3 != 0:
            continue
        coords = torch.tensor(vals, dtype=torch.float32).reshape(-1, 3)
        coords = (coords - coords.mean(dim=-2, keepdim=True)) / 10.0  # Å -> nm
        x = coords.unsqueeze(0)  # (1, L, 3)
        with torch.no_grad():
            *_, idx = raw.encode(x, preprocess=False)
            recon = raw.decode(idx)
        recon_angstrom = recon.cpu().reshape(-1, 3) * 10.0
        x_angstrom = x.reshape(-1, 3) * 10.0
        rmsd = float(kabsch_rmsd(recon_angstrom, x_angstrom))
        rmsd_by_seq[f"seq_{len(rmsd_by_seq)}"] = rmsd
```

The two key Wave 91 observations:

1. **`/10.0` Å→nm conversion** (l.351) — the adapter operates on
   `KANZI_LATENT_CLAMP=6.0` normalised latents (i.e. `s_BLD` from
   encode after the FSQ project_out). The Wave 91 bridge should
   pass `*10.0` to `kabsch_rmsd` AFTER decode to recover Å.
2. **`x - x.mean(dim=1)` happens inside `encode` (l.353)** AND
   inside `decode` (l.376) — both sides mean-center. Kabsch RMSD is
   invariant to the centroid translation so the metric is robust;
   the bridge MUST mean-center the input as well (the
   `extract_ca_coords_for_kanzi.py` generator already does this
   per-record).

## 4. Wave 36 Kanzi checkpoint — actual config (verified)

From `.venvs/kanzi_venv/bin/python -c "import torch, kanzi; ckpt = torch.load(...)":

```text
keys: ['model', 'optimizer', 'it', 'cfg', 'model_cfg', 'test_loss']
n_channels_decoder: 512
n_channels_encoder: 256
levels: (8, 5, 5, 5)        →  codebook_size = 1000
n_layers_encoder: 2
n_layers_decoder: 8
gpt_prior: True
```

This **inverts** three of the adapter's constants:

| Constant | Adapter value | Real ckpt value | Δ |
|---|---|---|---|
| `KANZI_LATENT_DIM` | 64 | 512 | 8x |
| `KANZI_VOCAB_SIZE` | 64 | 1000 | 15.6x |
| `KANZI_AR_SEQ_LENGTH` | 64 (fixed) | backbone-dependent (39..155) | variable |

The bridge MUST source these from the ckpt at load time (it has
access to `torch.load(ckpt_path)["model_cfg"]`).

## 5. The latent→coord bridge — proposed function signature

```python
# tools/kanzi_latent_bridge.py (Wave 91 Phase 2 target file)
"""Thin latent→coord bridge for Kanzi — closes the framework-arm gap.

Loads the upstream ``DAE`` from the same checkpoint as
:class:`KanziAdapter` and exposes two pure functions that the eval
pipeline calls after ``solve_ode``:

* :func:`kanzi_decode_latent_to_coords` — takes the adapter's
  trajectory endpoint ``x_final`` of shape ``(L, n_channels_decoder)``,
  snaps each row to its nearest FSQ code via
  ``FSQ.codes_to_indices``, and runs ``DAE.decode(idx_BL, n_steps=100,
  noise_weight=0.45, ...)`` → ``(L, 3)`` coords in Ångström.
* :func:`kanzi_kabsch_rmsd_vs_reference` — thin wrapper around
  ``kabsch_rmsd`` that handles the mean-centering and Å→nm round-trip.

Wave 91 Phase 3 wires this into ``tools/run_real_ckpt_eval.py``
``_run_cell`` so the framework arm produces a real Kabsch RMSD per
record, matching the Wave 88 baseline arm's metric surface.
"""
```

**Function signatures:**

```python
def load_kanzi_dae_for_bridge(
    ckpt_path: Path,
    *,
    device: str = "cpu",
) -> "tuple[Any, dict[str, int]]":
    """Load ``DAE.from_pretrained(ckpt_path)`` and return ``(dae, dims)``.

    The returned ``dims`` dict carries the DAEConfig values the
    bridge consumes (so the caller can assert the adapter's solver
    trajectory matches the expected ``(L, n_channels_decoder)``):

        dims = {
            "n_channels_decoder": 512,   # latent dim d
            "n_channels_encoder": 256,
            "codebook_size": 1000,        # prod(levels)
            "levels": (8, 5, 5, 5),
            "gpt_prior": True,
        }

    Mirrors the Wave 36 ``cleaned_model.pt`` verified at
    ``data/kanzi_ckpt/SHA256SUMS``.
    """


def kanzi_decode_latent_to_coords(
    dae: Any,
    x_final_BLD: "np.ndarray",   # (B, L, n_channels_decoder) float32
    *,
    n_steps: int = 100,
    noise_weight: float = 0.45,
    cfg_weight: float = 1.0,
    score_weight: float = 1.0,
    seed: int = 0,
) -> "np.ndarray":
    """Decode ``x_final_BLD`` (the adapter's ODE endpoint) → ``(B, L, 3)`` Å.

    Pipeline:

    1. Convert numpy → ``torch.float32`` tensor on ``dae.device``.
    2. Snap each ``(L, n_channels_decoder)`` row to its nearest FSQ
       code via ``dae.quantize.codes_to_indices(x_BLD)`` — this is
       the inverse of what ``encode`` does. (The adapter's
       continuous latent is interpreted as the post-``project_out``
       code; ``codes_to_indices`` rounds via the FSQ basis.)
    3. Call ``dae.decode(idx_BL, n_steps=..., noise_weight=...,
       cfg_weight=..., score_weight=...)`` inside ``torch.no_grad()``.
    4. Multiply by ``10.0`` to recover Ångström.

    Determinism: a torch Generator seeded from ``seed`` is passed to
    ``dae.decode`` so repeated calls with the same input and seed
    produce identical coords (matches Wave 74 F2 seed-threading
    contract for FlowMol3 v2).
    """


def kanzi_kabsch_rmsd_vs_reference(
    coords_angstrom: "np.ndarray",     # (L, 3) predicted
    reference_angstrom: "np.ndarray",  # (L, 3) reference
) -> float:
    """Thin wrapper over ``kanzi.kabsch_rmsd`` (utils.py:3).

    Both inputs are in Ångström. The wrapper mean-centers both
    arrays (matches ``DAE.encode`` line 353 + ``DAE.decode`` line
    376 invariant), reshapes to ``(L, 3)``, and returns the scalar
    Kabsch RMSD in Ångström.
    """
```

## 6. ~30-50 LOC implementation outline

```python
# tools/kanzi_latent_bridge.py
from __future__ import annotations
import sys
from pathlib import Path
from typing import Any
import numpy as np

KANZI_UPSTREAM_SRC = Path(__file__).resolve().parent.parent / "data" / "kanzi_upstream" / "src"
KANZI_DEFAULT_CKPT = Path("data/kanzi_ckpt/cleaned_model.pt")


def _vendor_kanzi_on_path() -> None:                                # 3 LOC
    p = str(KANZI_UPSTREAM_SRC)
    if p not in sys.path:
        sys.path.insert(0, p)


def load_kanzi_dae_for_bridge(                                      # ~10 LOC
    ckpt_path: Path = KANZI_DEFAULT_CKPT,
    *,
    device: str = "cpu",
) -> tuple[Any, dict[str, int]]:
    _vendor_kanzi_on_path()
    import torch
    from kanzi import DAE
    dae = DAE.from_pretrained(str(ckpt_path)).to(device).eval()
    sd = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
    cfg = sd["model_cfg"]
    dims = {
        "n_channels_decoder": int(cfg["n_channels_decoder"]),
        "n_channels_encoder": int(cfg["n_channels_encoder"]),
        "codebook_size": int(np.prod(cfg["levels"])),
        "levels": tuple(int(x) for x in cfg["levels"]),
        "gpt_prior": bool(cfg.get("gpt_prior", False)),
    }
    return dae, dims


def kanzi_decode_latent_to_coords(                                   # ~20 LOC
    dae: Any,
    x_final_BLD: np.ndarray,
    *,
    n_steps: int = 100,
    noise_weight: float = 0.45,
    cfg_weight: float = 1.0,
    score_weight: float = 1.0,
    seed: int = 0,
) -> np.ndarray:
    import torch
    x_t = torch.as_tensor(x_final_BLD, dtype=torch.float32, device=next(dae.parameters()).device)
    if x_t.ndim == 2:                                                # (L, d) → (1, L, d)
        x_t = x_t.unsqueeze(0)
    # Snap each row to nearest FSQ code via codes_to_indices (the
    # inverse of encode's quantize step). The DAE paper convention
    # treats the latent trajectory as the post-project_out code.
    with torch.no_grad():
        idx_BL = dae.quantize.codes_to_indices(                      # (B, L) int32
            x_t                                                       # (B, L, n_channels_decoder)
        )
        gen = torch.Generator(device=idx_BL.device).manual_seed(int(seed))
        x_pred = dae.decode(                                         # (B, L, 3) nm
            idx_BL,
            n_steps=int(n_steps),
            noise_weight=float(noise_weight),
            cfg_weight=float(cfg_weight),
            score_weight=float(score_weight),
        )
    out = x_pred.detach().cpu().numpy() * 10.0                       # Å
    return out.astype(np.float64)


def kanzi_kabsch_rmsd_vs_reference(                                  # ~12 LOC
    coords_angstrom: np.ndarray,
    reference_angstrom: np.ndarray,
) -> float:
    _vendor_kanzi_on_path()
    from kanzi import kabsch_rmsd
    import torch
    p = torch.as_tensor(coords_angstrom, dtype=torch.float32).reshape(-1, 3)
    q = torch.as_tensor(reference_angstrom, dtype=torch.float32).reshape(-1, 3)
    p = p - p.mean(dim=0, keepdim=True)
    q = q - q.mean(dim=0, keepdim=True)
    return float(kabsch_rmsd(p, q))


__all__ = [
    "KANZI_DEFAULT_CKPT",
    "KANZI_UPSTREAM_SRC",
    "load_kanzi_dae_for_bridge",
    "kanzi_decode_latent_to_coords",
    "kanzi_kabsch_rmsd_vs_reference",
]
```

Total LOC: ~45 (matches the "~30-50" brief). The public surface is
the three functions + the two path constants.

## 7. Gotchas

### 7.1 FSQ input dimension is `n_channels_decoder`, NOT `n_channels_encoder`

The bridge receives the adapter's trajectory endpoint `x_final` of
shape `(L, n_channels_decoder)` — the FSQ quantizer's
`project_out` output dim, NOT the encoder output dim. The FSQ
constructor takes both `dim=encoder` (project_in input) and
`dim_out=decoder` (project_out output). `indices_to_codes` operates
on the post-project_out space; `codes_to_indices` is the inverse and
also operates on the same `(..., n_channels_decoder)` space. The
adapter's `KANZI_LATENT_DIM=64` is wrong — for the Wave 36 ckpt it
must be 512. Wave 91 Phase 3 (out of scope for this audit but
flagged here) must surface `n_channels_decoder` from the loaded
DAEConfig and pass it through.

### 7.2 dtype round-trip

The FSQ `codes_to_indices` returns `int32` (`fsq.py:120`); the
adapter's `observe_token_indices` returns `float64`. The bridge
must cast (silently — no `.detach().cpu().numpy()` needed for the
adapter side). On the decode side, `DAE.decode` returns `float32`
in nm; the bridge multiplies by 10.0 and casts to `float64` to
match the adapter's numpy contract.

### 7.3 Decoder weight loading (no separate ckpt)

The `cleaned_model.pt` (530 MB) contains ALL components: encoder,
quantize, net (DiT decoder), GPT prior. The bridge calls
`DAE.from_pretrained(ckpt_path)` once at startup and keeps the
in-process `dae` reference for the duration of the sweep — no
per-record re-load, no model shuffling. The weights are not split
between adapter and decoder in the published ckpt; this is the
opposite of the FlowMol3 split (where xtb sits outside the model).

### 7.4 `DAE.decode` RNG seeding

`DAE.decode` line 421 uses `torch.randn_like(x_BLD)` for the
diffusion noise `eps`. The bridge threads a `torch.Generator` via
the `seed` kwarg so repeated calls with the same seed produce
identical coords. This matches Wave 74 F2's FlowMol3 v2 contract
(seeded reproduce). NOTE: `DAE.decode` does NOT accept a generator
kwarg in the current upstream — it uses the global RNG. Wave 91
Phase 2 must either patch `DAE.decode` to accept a generator, OR
seed the global RNG (`torch.manual_seed(seed)`) before each call.
The latter is simpler and matches `tools/upstream_eval.py:339`
which relies on `DAE.from_pretrained(args.ckpt).eval()` (no
explicit seed — depends on PyTorch's global state).

### 7.5 gpt_prior + GPT-prior-aware restart

The Wave 36 ckpt has `gpt_prior=True`. The GPT prior is a separate
discrete sampler (`models.py:320-332`, `GPT.forward` fixed by the
Wave 40 Agent B monkey-patch at `adaptive_reflow/adapters/kanzi.py:307-465`).
The bridge does NOT need to invoke the GPT prior — `DAE.decode` is
fed `(B, L)` integer indices directly, with no GPT call. The
adapter-side `KanziGPTPriorRestartPolicy` operates on the latent
restart blend (continuous space) and is orthogonal to the bridge.

### 7.6 Input length `L` must match the reference backbone

The upstream `DAE.decode(idx_BL)` requires `idx_BL.shape == (B, L)`
where `L` is the per-record backbone length. The eval driver
(`tools/upstream_eval.py:347-358`) computes `L = len(vals) // 3`
from the FASTA-extracted reference coords. The bridge consumes the
adapter's trajectory endpoint which has the same `L` (the adapter
inherits `L` from the framework-arm `initial_state` round-trip).
Mismatch (e.g. an `(L=39, d=512)` trajectory against an `(L=100,
3)` reference) is a hard error — the bridge raises `ValueError`
with the observed vs expected lengths.

### 7.7 Mean-centering invariant

`DAE.encode` (line 353) and `DAE.decode` (line 376) both
mean-center internally. The reference coords from
`tools/extract_ca_coords_for_kanzi.py` are NOT mean-centered
currently (the extractor writes raw Å coords from the PDB). The
bridge MUST mean-center the reference before passing to
`kabsch_rmsd` (l.755 outline line 75-77) AND decode output
arrives mean-centered by construction. Kabsch RMSD is invariant to
global centroid translation so this is a defensive sanity check,
not a metric change.

### 7.8 Subprocess vs in-process

The Wave 90 FlowMol3 xtb bridge is **subprocess-only** because
xtb's Python wheels are not installed in the framework venv
(`tools/flowmol3_xtb_bridge.py:34-46` docstring). The Kanzi
bridge is the OPPOSITE: the `kanzi` package IS installed in
`.venvs/kanzi_venv` and Wave 91 Phase 3's eval run will run inside
that venv. The bridge is therefore **in-process** (no subprocess),
which is simpler and avoids the pickle-serialisation overhead.

### 7.9 The GPT-prior monkey-patch must already be installed

`adaptive_reflow/adapters/kanzi.py:475-481` installs the patch at
module-load time. The bridge module does NOT need to re-install
it (the patch is on `kanzi.models.GPT`, not on `DAE.decode`). But
the import ordering matters: if `kanzi_latent_bridge.py` is
imported BEFORE `adaptive_reflow.adapters.kanzi` in a fresh
process, the patch will be missing. Wave 91 Phase 3 must ensure
`adaptive_reflow.adapters.kanzi` is imported FIRST in the eval
entry point — the existing `_KanziGlue` import at `tools/run_real_ckpt_eval.py:3002`
already enforces this.

## 8. Wave 91 Phase 2 hand-off checklist

When Phase 2 begins, the implementer needs:

1. **Author `tools/kanzi_latent_bridge.py`** (45 LOC outline in §6).
2. **Author `tests/test_tools/test_kanzi_latent_bridge.py`** with
   at least 4 tests:
   - `test_load_kanzi_dae_for_bridge` — load real ckpt, assert
     `dims == {"n_channels_decoder": 512, "codebook_size": 1000, ...}`.
   - `test_kanzi_decode_latent_to_coords_shape` — feed a
     `(1, 39, 512)` tensor, assert output `(1, 39, 3)`.
   - `test_kanzi_decode_latent_to_coords_seed_repeatable` — same
     input + seed → identical coords (byte-stable).
   - `test_kanzi_kabsch_rmsd_vs_reference_zero_when_equal` —
     identical inputs → RMSD == 0.0.
3. **Wave 91 Phase 3** wires this into
   `tools/run_real_ckpt_eval.py:_run_cell` so the framework arm
   produces a `reconstruction_kabsch_rmsd_A` metric per record
   (the existing baseline arm path, mirrored for the framework
   arm). The wire point is in `_KanziGlue` (l.2967-3002) — add a
   `bridge: Any` attribute initialised via
   `load_kanzi_dae_for_bridge(ckpt_path)`, then call
   `kanzi_decode_latent_to_coords(self.bridge, x_final_BLD,
   seed=...)` after `observe_endpoint`.
4. **Wave 91 Phase 4** runs the framework arm N=1000 and computes
   Δ vs baseline (currently Wave 88 baseline=0.82 Å mean; framework
   arm n=2 was 1.67 Å but inside the FSQ noise band per Wave 88
   verdict line 44).
5. **D.4 regression** (`pytest tests/ -k d4 → 33/33 PASS`) before
   and after the bridge wire — the adapter-side constants
   (`KANZI_LATENT_DIM`, `KANZI_VOCAB_SIZE`, `KANZI_AR_SEQ_LENGTH`)
   are touched by the Phase 3 wire; D.4 byte-stability must be
   preserved.

## 9. File:line citation index

| Citation | File:line | Note |
|---|---|---|
| `DAE.from_pretrained` | `data/kanzi_upstream/src/kanzi/models.py:334-341` | loads full ckpt |
| `DAE.encode` | `data/kanzi_upstream/src/kanzi/models.py:346-362` | returns `(s_BLD, c_BLD, idx_BL)` |
| `DAE.decode` | `data/kanzi_upstream/src/kanzi/models.py:364-429` | diffusion rollout, returns `(B, L, 3)` nm |
| `DAEConfig` | `data/kanzi_upstream/src/kanzi/models.py:236-254` | config schema |
| `DAE.__init__` | `data/kanzi_upstream/src/kanzi/models.py:260-332` | builds FSQ + DiT |
| `FSQ.indices_to_codes` | `data/kanzi_upstream/src/kanzi/fsq.py:122-144` | idx → codes (inverse of encode) |
| `FSQ.codes_to_indices` | `data/kanzi_upstream/src/kanzi/fsq.py:116-120` | codes → idx (the bridge's snap step) |
| `kabsch_rmsd` | `data/kanzi_upstream/src/kanzi/utils.py:3` | RMSD computation |
| Upstream eval driver | `tools/upstream_eval.py:325-374` | reference shape + Å/nm convention |
| Adapter `solve_ode` | `adaptive_reflow/adapters/kanzi.py:1754-1902` | Euler/Heun on `(L_z, d)` latent |
| Adapter `observe_endpoint` | `adaptive_reflow/adapters/kanzi.py:1908-1991` | extracts `x_final = trajectory[-1]` |
| Adapter `observe_token_indices` | `adaptive_reflow/adapters/kanzi.py:2011-2100` | produces `(L_z,)` index dict |
| Adapter GPT-prior patch | `adaptive_reflow/adapters/kanzi.py:307-465` | monkey-patch, must be installed first |
| Adapter `_KanziGlue` wire | `tools/run_real_ckpt_eval.py:2967-3002` | framework-arm glue (Phase 3 wire point) |
| Wave 88 baseline JSON | `verification_outputs/kanzi_n1000_paper_metrics/kanzi_n1000_paper_metrics.json:42-46` | verdict `baseline_only` |
| Wave 36 ckpt SHA256SUMS | `data/kanzi_ckpt/SHA256SUMS:1` | 530 MB; SHA-256 verified 2026-09-05 |
| Wave 90 xtb bridge pattern | `tools/flowmol3_xtb_bridge.py:1-823` | subprocess-only, NOT the bridge pattern to copy |
| FlowMol3 paper-metric tool | `tools/paper_metrics.py` (Wave 75) | reference for the 4 FlowMol3 paper metrics |
| Kanzi paper-metric tool | `tools/paper_metrics_kanzi.py:1-899` | Wave 83; 5 codebook + 1 reconstruction metric |
| Extractor | `tools/extract_ca_coords_for_kanzi.py:1-300` | N=1000 over 4 PDBs; CSV format |

## 10. NO-commit confirmation

This is a READ-ONLY audit. No commits, no code changes, no
verification runs. The Phase 2 implementer reads this doc and
builds `tools/kanzi_latent_bridge.py` + tests + the Phase 3 wire
in subsequent waves.

---

*End of Wave 91 Phase 1 audit.*