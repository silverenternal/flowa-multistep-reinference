# Wave 107.A.1 — Seeded Kanzi decoder wrapper reuse opportunities

READ-ONLY audit. No source code edits. No commits. Goal: find the cheapest
existing pattern to add seed-controlled `torch.randn_like` to `DAE.decode`
so the **Wave 88 F-4 stochasticity caveat** can be eliminated WITHOUT
reinventing the decoder wrapper.

## 0. Wave 88 F-4 context (the target bug)

- **File**: `<repo_root>/docs/audit/wave88-phase2-sweep.md:192` — *"F-4 — `DAE.decode` is stochastic, and nothing seeds it"*.
- **File**: `<repo_root>/docs/audit/wave88-phase3-final.md:122` — *"F-4 — `DAE.decode` is stochastic and unseeded. Run-to-run σ 0.0947 Å; sweep script's `"deterministic": true` is incorrect; Wave 83's 'byte-stable' claim is incorrect."*
- **Evidence file**: `/tmp/wave88/probe_determinism.py` — *"F-4 determinism probe (torch.manual_seed(1234) drives spread to 0)"*.
- **Fix recommendation** (wave88-phase3-final.md:178): *"thread `--seed` into `dae.decode` in the sweep script to drive the run-to-run σ to 0 (Wave 88 F-4 fix)."*

The fix is therefore: ensure the Kanzi decoder wrapper applies a seed
BEFORE calling `DAE.decode`, so the per-record spread drops from
σ=0.0947 Å to σ=0.0.

---

## 1. Does Kanzi upstream `DAE.decode` have a seed parameter?

**Answer: NO.** `DAE.decode` signature
(`<repo_root>/data/kanzi_upstream/src/kanzi/models.py:364-372`):

```python
def decode(
    self,
    idx_BL,
    n_steps=100,
    noise_weight=0.45,
    score_weight=1.0,
    cfg_weight=1.0,
    g_fn=None,
):
```

No `seed=`, no `torch.Generator=`, no `rng=` keyword argument. Stochasticity
is injected unconditionally via global torch RNG:

- **Line 375**: `x_BLD = torch.randn(*c_BLD.shape[:-1], 3, device=device)` — initial-state noise, reads global RNG.
- **Line 421**: `eps = torch.randn_like(x_BLD)` — per-step SDE noise, reads global RNG.

The *only* noise sources in `DAE.decode` are these two `torch.randn` /
`torch.randn_like` calls. Both consume the **global default torch
generator** (no Generator argument is accepted).

`DAE` has **no `sample()` method** — `sample()` is defined on the
**`RnFlowMatcher`** class (different module), not on `DAE`. From
`<repo_root>/data/kanzi_upstream/src/kanzi/models.py:608`:

```python
def sample(self, x_BLD, n_steps):
    """Pure ODE (no SDE noise) — uses odeint, no torch.randn calls."""
```

…which is NOT the function the bridge calls; the bridge uses
`DAE.decode`. **DAE.euler_maruyama_sample** (`models.py:635-664`) is also
unused by the bridge and has the same global-RNG pattern at line 656.

So: the upstream `DAE.decode` has no seed path → we MUST seed externally
via `torch.manual_seed` / `torch.Generator`.

---

## 2. Does `adaptive_reflow/adapters/kanzi.py` wrap `DAE.decode`?

**Answer: NO.** The adapter (`kanzi.py`) does NOT call `DAE.decode`
directly. The `solve_ode` path is a custom NumPy Euler/Heun integrator
(`kanzi.py:2156-2187`) that does NOT consult the upstream DAE. The DAE
is only invoked at the **bridge layer**.

The wrapper that does call `DAE.decode` is
`tools/kanzi_latent_to_coord.py` (see §3). The adapter code in
`kanzi.py:2098-2235` (`solve_ode`) is the *custom* NumPy Euler/Heun
integration surface — not a decode wrapper.

**Implication**: The F-4 fix lives in the **bridge** (`tools/kanzi_latent_to_coord.py`), not the adapter. There is no upstream seed to thread into `adapter.solve_ode`.

---

## 3. Does `tools/kanzi_latent_to_coord.py` call `DAE.decode`? Can we thread a `torch.Generator`?

**Answer: YES, it already does — via `torch.manual_seed` on the global RNG.**
But there is a *better* existing pattern already in the codebase.

The bridge function `kanzi_latent_to_coords(latent, decoder, fsq_quantizer, *, ..., seed=0)`
(`<repo_root>/tools/kanzi_latent_to_coord.py:72-238`)
calls the upstream `DAE.decode` at **line 229-235**:

```python
x_pred = decoder.decode(
    idx_BL,
    n_steps=int(n_steps),
    noise_weight=float(noise_weight),
    cfg_weight=float(cfg_weight),
    score_weight=float(score_weight),
)
```

It already accepts a `seed: int = 0` parameter and applies it via global
RNG at **line 165**:

```python
torch.manual_seed(int(seed))
```

This is **REUSE #1**: the existing `seed=` parameter on the bridge
function is the F-4 fix entry point. The bridge already does what F-4
asks for — it just does it via `torch.manual_seed` (global) rather than
`torch.Generator` (local). See §6 for the safer wrapper.

### LOC delta if REUSED as-is (no code change)

- **0 LOC delta** (already implemented; the F-4 fix is `seed=int(seed)`
  at the bridge call site, not a new wrapper).

### LOC delta if UPGRADED to `torch.random.fork_rng()` (hygiene only)

- **+4 LOC** (replace the 1-line `torch.manual_seed` with a
  `with torch.random.fork_rng():` block — no semantic change, but
  prevents leaking the seed to the caller's global RNG).

---

## 4. Does `paper_quantities.py` have a seeded wrapper or stochasticity-acknowledgment helper?

**Answer: NO.** Searched
`<repo_root>/adaptive_reflow/theory/paper_quantities.py`
for `seed`, `generator`, `Generator`, `stochastic`, `noise` — no
seed-wrapping or stochasticity-acknowledgment helper exists.

The only `noise`-adjacent code is the `CodimensionSheetScheduler.inject_noise`
*reference* in the docstring (line 52, 653) — a docstring pointer, not
a helper.

**No existing helper found for this in `paper_quantities.py`.**

---

## 5. Does vendored Kanzi upstream have a `sample()` function with seed support?

**Answer: NO seed support anywhere in the vendored Kanzi upstream.**

Searched
`<repo_root>/data/kanzi_upstream/src/kanzi/`
for `seed`, `Generator`, `manual_seed`, `fork_rng`:

- `models.py:1137` — *only* `torch.manual_seed(1137 + rank)` in **`train_cb.py:220`** — TRAINING-SIDE seed for DDP rank init. NOT in the inference path.
- `models.py:438, 596, 656` — three `torch.randn_like` calls in
  `DAE.forward`, `RnFlowMatcher.forward`, and `euler_maruyama_sample`
  (training + inference path, all global RNG, no Generator parameter).
- `fsq.py:96` — `torch.randn_like(z) * self.jitter_spread` in
  `FSQ.quantize` (training jitter only).

**Conclusion**: No upstream function accepts a `torch.Generator`. The
Kanzi upstream uses global RNG throughout; any seed must be set
externally (i.e. in our wrapper) before calling `DAE.decode`.

---

## 6. Existing generator context manager / seed-fork patterns in `adaptive_reflow/`

**REUSE #2 (canonical pattern)**: `torch.Generator(device=...).manual_seed(seed)`
appears in 5+ existing call sites in `adaptive_reflow/`:

### Hidream I1 image generation (Wave 105 forward)

- File: `<repo_root>/adaptive_reflow/adapters/_hidream_i1_upstream_shim.py:416` —
  ```python
  generator = torch.Generator(device="cpu").manual_seed(int(seed))
  ```
  passed to diffusers pipeline as `generator=generator` (line 423).

### HiDream I1 adapter

- File: `<repo_root>/adaptive_reflow/adapters/hidream_i1.py:1116` —
  ```python
  generator = torch.Generator(device="cpu").manual_seed(int(seed) + i)
  ```
  passed per-prompt.

### Wan2.2 video shim

- File: `<repo_root>/adaptive_reflow/adapters/wan2_2_upstream_shim.py:135` —
  ```python
  generator = torch.Generator(device=getattr(self.pipeline, "device", "cpu")).manual_seed(...)
  ```

### FlowMol3 v2 adapter (Wave 74 F2 — the closest analog)

- File: `<repo_root>/adaptive_reflow/adapters/flowmol3_v2_adapter.py:627-629` —
  ```python
  _torch.manual_seed(int(seed))
  if _torch.cuda.is_available():
      _torch.cuda.manual_seed_all(int(seed))
  ```
  This is the global-RNG seeding pattern (matches what
    `kanzi_latent_to_coord.py` already does) — REUSE.

### Global-RNG pattern (KANZI CURRENT PATTERN)

- File: `<repo_root>/tools/kanzi_latent_to_coord.py:165` —
  `torch.manual_seed(int(seed))` — REUSE this.

### Conclusion on existing helpers

There is **NO shared `_adapter_common.seed_context()` context manager**
in `<repo_root>/adaptive_reflow/adapters/_adapter_common.py`. Each call site inlines its own pattern. The two reuse options are:

- **(A) `torch.manual_seed(int(seed))`** (global, simple, already done in the bridge) — REUSE.
- **(B) `torch.Generator(device=...).manual_seed(int(seed))` + pass to a function that accepts Generator** — does NOT work for `DAE.decode` because the upstream doesn't accept a Generator.

**No existing helper found for this in `_adapter_common.py`** — there is
no shared `seed_context()` to wrap in. The F-4 fix is a 0-LOC change
(bridge already does it) or a +4-LOC hygiene upgrade (`fork_rng`).

---

## 7. The cheapest fix — 0 LOC delta, REUSE existing bridge

The F-4 fix is already in place at
`tools/kanzi_latent_to_coord.py:165`:

```python
torch.manual_seed(int(seed))
```

This is the **cheapest** path. The bridge already accepts a `seed`
parameter and applies it before the `DAE.decode` call. The Wave 88
F-4 caveat can be closed by:

1. **Updating the sweep driver** (e.g.
   `tools/sweep_kanzi_n1000_paper_metrics.py:239` —
   `"deterministic": true`) to call the bridge with a non-zero seed
   (or by exposing `--seed` at the sweep CLI and threading it into
   the bridge call).

2. **No new wrapper needed**. The bridge function IS the seeded
   decoder wrapper. `DAE.decode` doesn't accept a `Generator`, so we
   must seed externally — and the bridge already does.

### LOC delta summary

| Approach | LOC delta | Notes |
|---|---|---|
| REUSE existing `seed=` bridge param + `torch.manual_seed` | **0 LOC** | Already implemented; just thread `--seed` from the sweep CLI |
| HYGIENE UPGRADE: wrap `torch.manual_seed` in `torch.random.fork_rng()` | **+4 LOC** | Prevents seed leak to caller's RNG state |
| NEW `seed_context()` helper in `_adapter_common.py` | **+15 LOC** | Avoided — no existing helper to reuse; if added, would require touching all 5+ existing inline sites (out of scope) |
| NEW monkey-patch on `DAE.decode` to thread `Generator` | **+30 LOC** | Avoided — invasive, modifies vendored upstream semantics |

**REUSE wins.** The cheapest fix is 0 LOC.

---

## 8. Files audited (READ-ONLY)

- `<repo_root>/data/kanzi_upstream/src/kanzi/models.py` (lines 364-429 DAE.decode, 608-664 sample/euler_sample/euler_maruyama_sample, 1137)
- `<repo_root>/data/kanzi_upstream/src/kanzi/cfm.py` (lines 41, 98, 150 sample_noise_like, 153)
- `<repo_root>/data/kanzi_upstream/src/kanzi/fsq.py` (line 96 jitter noise)
- `<repo_root>/data/kanzi_upstream/src/kanzi/utils.py` (kabsch_rmsd, no RNG)
- `<repo_root>/data/kanzi_upstream/src/kanzi/train_cb.py` (line 220 train-side seed)
- `<repo_root>/adaptive_reflow/adapters/kanzi.py` (lines 2098-2235 solve_ode — no DAE.decode call; line 165 bridge uses torch.manual_seed)
- `<repo_root>/adaptive_reflow/adapters/_adapter_common.py` (full file — no seed_context helper exists)
- `<repo_root>/adaptive_reflow/adapters/_hidream_i1_upstream_shim.py` (line 416 — pattern A)
- `<repo_root>/adaptive_reflow/adapters/hidream_i1.py` (line 1116 — pattern A)
- `<repo_root>/adaptive_reflow/adapters/wan2_2_upstream_shim.py` (line 135 — pattern A)
- `<repo_root>/adaptive_reflow/adapters/flowmol3_upstream_shim.py` (lines 168-170 — pattern B)
- `<repo_root>/adaptive_reflow/adapters/flowmol3_v2_adapter.py` (lines 627-629 — pattern B, Wave 74 F2)
- `<repo_root>/adaptive_reflow/theory/paper_quantities.py` (full file — no seed helper)
- `<repo_root>/tools/kanzi_latent_to_coord.py` (lines 72-238 — bridge, line 165 torch.manual_seed, line 229 DAE.decode call)
- `<repo_root>/tools/upstream_eval.py` (lines 396, 470, 544 — DAE.encode→decode→kabsch_rmsd path; no seed currently)
- `<repo_root>/docs/audit/wave88-phase2-sweep.md` (line 192 F-4 finding)
- `<repo_root>/docs/audit/wave88-phase3-final.md` (lines 72-94, 122-178 — F-4 evidence + fix path)

## 9. External libraries audited

- **PyTorch stdlib**: `torch.manual_seed`, `torch.Generator`,
`torch.random.fork_rng` — all available; no new dependency needed.
- **Kanzi upstream** (vendored): no seed support, confirmed.
- **transformers / diffusers** (already in pyproject.toml): not relevant
to Kanzi (protein, not image); Hidream I1 / Wan2.2 use them but those
patterns accept `generator=` — Kanzi upstream does NOT.
- **mdtraj / biotite / torchdiffeq** (already in pyproject.toml): not
relevant — no decoder wrapping concern.

## 10. Reuse opportunities summary

| ID | Reuse opportunity | LOC delta | Status |
|---|---|---|---|
| REUSE-1 | Existing `seed=` kwarg on `kanzi_latent_to_coords()` + `torch.manual_seed(int(seed))` at bridge line 165 | **0 LOC** | ALREADY IMPLEMENTED; just needs `--seed` threaded from the sweep CLI |
| REUSE-2 | `torch.Generator(device="cpu").manual_seed(int(seed))` pattern from hidream_i1 / wan2_2 / hidream shim | **0 LOC** | UNUSABLE — `DAE.decode` does not accept a Generator |
| REUSE-3 | `torch.manual_seed` + `torch.cuda.manual_seed_all` pattern from `flowmol3_v2_adapter.py:627-629` | **0 LOC** | Same as REUSE-1; could copy the cuda guard to bridge (currently bridge uses CPU only — matches `DAE.decode` running on CPU sidecar venv) |
| REUSE-4 | `torch.random.fork_rng()` context manager (stdlib) | **+4 LOC** | HYGIENE UPGRADE — wrap the existing `torch.manual_seed` to prevent seed leak to caller's RNG state |

**REUSE-1 (0 LOC) is the recommended path.** It eliminates the F-4
caveat by ensuring the sweep driver passes a fixed `seed=` to the
existing bridge function. No new wrapper, no new helper, no upstream
patch.

## 11. Recommendation

- **REUSE the existing `kanzi_latent_to_coords(seed=...)` parameter.**
- **No new code needed** — just thread `--seed` from
  `tools/sweep_kanzi_n1000_paper_metrics.py` (or whichever sweep runs
  Kanzi) into the bridge call.
- **Optional hygiene upgrade**: wrap the existing
  `torch.manual_seed(int(seed))` at bridge line 165 in
  `with torch.random.fork_rng():` (+4 LOC, no semantic change, prevents
  seed leak).
- **Do NOT** add a `seed_context()` helper to `_adapter_common.py` —
  there is no existing helper to share with (the 5+ existing call
  sites all inline their own pattern); adding one would touch every
  site and is out of scope for the F-4 fix.
- **Do NOT** monkey-patch upstream `DAE.decode` to accept a
  `torch.Generator` — invasive, modifies vendored semantics, and
  unnecessary given REUSE-1 already works.

---

## JSON return (per Wave 107 contract)

```json
{
  "commit_sha": "c0dd9e4",
  "files_audited": [
    "data/kanzi_upstream/src/kanzi/models.py",
    "data/kanzi_upstream/src/kanzi/cfm.py",
    "data/kanzi_upstream/src/kanzi/fsq.py",
    "data/kanzi_upstream/src/kanzi/utils.py",
    "data/kanzi_upstream/src/kanzi/train_cb.py",
    "adaptive_reflow/adapters/kanzi.py",
    "adaptive_reflow/adapters/_adapter_common.py",
    "adaptive_reflow/adapters/_hidream_i1_upstream_shim.py",
    "adaptive_reflow/adapters/hidream_i1.py",
    "adaptive_reflow/adapters/wan2_2_upstream_shim.py",
    "adaptive_reflow/adapters/flowmol3_upstream_shim.py",
    "adaptive_reflow/adapters/flowmol3_v2_adapter.py",
    "adaptive_reflow/theory/paper_quantities.py",
    "tools/kanzi_latent_to_coord.py",
    "tools/upstream_eval.py",
    "docs/audit/wave88-phase2-sweep.md",
    "docs/audit/wave88-phase3-final.md"
  ],
  "external_libs_audited": [
    "torch.manual_seed (stdlib)",
    "torch.Generator (stdlib)",
    "torch.random.fork_rng (stdlib)",
    "kanzi upstream models.DAE.decode (vendored)",
    "kanzi upstream models.RnFlowMatcher.sample (vendored)",
    "hidream_i1 generator pattern (diffusers-compatible)",
    "flowmol3_v2 torch.manual_seed pattern (Wave 74 F2)",
    "transformers/diffusers (in pyproject.toml — not applicable to Kanzi)"
  ],
  "reuse_opportunities_count": 4,
  "output_file": "docs/audit/wave107-a1-seeded-decoder.md"
}
```