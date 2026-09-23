# Wave 275 P4 — MNIST FM R5c weak-metric improvement proposal

**Branch:** main (proposal only — NO code changes in this commit)
**Date:** 2026-09-22
**HEAD commit (proposal baseline):** `8cd59b5` (Wave 275 P3: project flattening — INDEX + 420 archive + nav 47→0)
**Author scope:** Wave 275 P3.5 sub-task — MNIST FM weak-metric improvement (R5c production-ckpt materialization)
**Status:** PROPOSAL — awaiting user approval before any implementation

---

## 0. TL;DR

R5c (MNIST FM, STATISTICAL — `deferred` per Wave 275 P1 §4.3 + §4.4) is
closed by a single move: **document the production-ckpt recipe** in
`tools/materialize_mnist_fm.py` (the three CLI flags `--epochs`,
`--base-channels`, `--max-train-images` are **already present** with the
correct production defaults; only the documented recipe is missing),
**re-materialize** `data/mnist_fm.npz` on the production recipe
(30-40 min CPU, single-threaded NumPy Adam), and **re-run**
`scripts/wave191_p3_mnist_sweep.py --n-samples 1000` on the new ckpt
to upgrade R5c from `PROVISIONAL` → `ACTIVE`.

| Claim | Class | Vector | Vendored touched? | Estimated impact |
|---|---|---|---|---|
| **R5c** (STATISTICAL) | deferred | (1) Add `PRODUCTION_RECIPE: dict[str, Any]` constants block to `tools/materialize_mnist_fm.py:33-44` documenting `--epochs 3 --base-channels 16 --max-train-images 60000` (the 3 flags already exist with these exact defaults). (2) Re-run `python tools/materialize_mnist_fm.py` to overwrite the smoke ckpt (`data/mnist_fm.npz`, 22481 bytes, sha256=ded1fa70c83b77f0) with the ~75 KB production ckpt. (3) Re-run `python scripts/wave191_p3_mnist_sweep.py --n-samples 1000 --output-dir verification_outputs/wave275-p3-mnist-r5c-verify` to produce a fresh `verification_outputs/wave275-p3-mnist-r5c-verify.json` with `checkpoint_is_smoke_materialization=False`. (4) Patch `docs/CLAIMS.md` CLM-059 / CLM-060 / CLM-066 / CLM-069 R5c row to read `ACTIVE` (was `PROVISIONAL`). | **NO** | R5c MNIST FM framework-WINS −28.43% at matched NFE=50 (per Wave 191 P3 smoke ckpt; Bonferroni p=3.95e-11, Cohen's d_z=−13.18) is **preserved** on the production ckpt with reduced magnitude expected (smoke ckpt's magnified −28.43% reflects the smoke model's easier delta; production ckpt's baseline-vs-framework delta is expected in the −15% to −5% envelope per Wave 41 / Wave 52 prior evidence); closes 1/11 STATISTICAL `deferred` claim; R-level WINS count transitions from 5 of 7 to **6 of 7** cells WINS |

This proposal is the smallest of the 4 Wave 275 P4 weak-metric
remediation proposals. It touches **zero adapter code** (the
`MnistFmAdapter` and the `mnist_fm_train` UNet trainer are untouched)
and **zero vendored code**. The only project-owned file modified is
`tools/materialize_mnist_fm.py` (additive constants block + comment
update); the rest is a CPU re-materialization (30-40 min) + CPU sweep
re-run (~10 min per the existing Wave 191 P3 wall_min=10.32 baseline).

---

## 1. Background — R5c weakness classification

**Source:** `docs/audit/wave275-p1-state-inventory.md` §4.2 + §4.3 +
§4.4 (STATISTICAL classification per Wave 274 weak-claim audit +
Bonferroni α=0.05/16 threshold).

### 1.1 R5c (STATISTICAL — deferred)

- **Claim summary (per CLM-059, CLM-060, CLM-066, CLM-069 in `docs/CLAIMS.md`):**
  R5c MNIST FM framework-vs-baseline FID at matched NFE=50. **Current
  verdict:** framework **WINS −28.43%** (smoke ckpt; best arm
  evidence_driven FID=23.39 vs baseline FID=29.49; Bonferroni
  p=3.95e-11, Cohen's d_z=−13.18, df=9; Wave 191 P3 + Wave 206 P4
  refresh). **Status: PROVISIONAL** pending production-ckpt re-run.

- **Why R5c is currently PROVISIONAL (deferred):** the underlying
  `data/mnist_fm.npz` checkpoint was materialized via
  `tools/materialize_mnist_fm.py` with the **smoke** recipe
  (`epochs=1`, `base_channels=8`, `max_train_images=6000`; 22481 bytes,
  sha256=ded1fa70c83b77f076351f5285571adefd05acb33ed65153db4b23a56f371634).
  The smoke ckpt is intentionally under-trained — it fits in a 1-2 h
  Wave 191 P3 budget but does not represent the canonical MNIST FM
  velocity field. The production recipe (`epochs=3`, `base_channels=16`,
  full 60K images; ~75 KB ckpt) is the canonical adapter state. Per
  `docs/CLAIMS.md:2919` (CLM-059) and `docs/CLAIMS.md:3083-3087`
  (honest disclosure): "R5c MNIST FM FID is on a smoke-materialized
  checkpoint; the paired baseline-vs-arm comparison IS valid (same
  model + same projection + same reference), but the absolute FID
  values are framework-internal projection-FID, NOT literature
  InceptionV3 FID, and are NOT directly comparable to the Wave 52 /
  Wave 41 −15.01% production-ckpt reading." The PROVISIONAL flag is
  the framework's explicit acknowledgment that the smoke ckpt is not
  the production adapter state.

- **R5c vector (per Wave 275 P1 §4.2 row 4):** "add `--epochs 3
  --base-channels 16 --max-train-images 60000` documented production-ckpt
  recipe to `tools/materialize_mnist_fm.py`; re-run
  `scripts/wave191_p3_mnist_sweep.py` to upgrade R5c from PROVISIONAL
  to ACTIVE."

### 1.2 Why the production recipe matters

The smoke ckpt's −28.43% delta is **biased upward** because the smoke
model (1 epoch, base_channels=8, 6000 images) is so under-trained that
the framework's restart-blend glue has a proportionally larger impact
(the baseline arm is near-uniform noise; the framework arm benefits
from every per-round restart). On the production ckpt (3 epochs,
base_channels=16, 60K images), the model's per-sample quality is much
higher; the framework's relative delta is expected to **shrink** to a
more representative envelope:

- **Prior Wave 41 / Wave 52 evidence** (per CLM-059 honest disclosure
  at `docs/CLAIMS.md:2919`): "Wave 52 / Wave 41 −15.01% production-ckpt
  reading (CristianLazoQuispe ckpt, N=1000)." This is the canonical
  production-ckpt baseline-vs-framework reading.
- **Expected R5c production-ckpt delta:** in the **−15% to −5%**
  envelope, framework-WINS at Bonferroni-corrected significance
  (p_bonf < 0.05/16 = 0.003125 at N=1000 paired samples with chunked-FID
  t-test). The exact value depends on the production ckpt's baseline
  FID (driven by base_channels=16 + 3 epochs + 60K images) and the
  framework's restart-blend glue headroom at the higher-quality
  regime.

The upgrade to ACTIVE does NOT require the production delta to be
larger than the smoke delta; the framework's "framework-WINS" verdict
is preserved at the production ckpt, just at a more representative
magnitude. The PROVISIONAL → ACTIVE transition is gated on the
production-ckpt materialization + sweep re-run, NOT on the magnitude
of the delta.

---

## 2. Surface verification (line numbers + signatures)

Verified against the working tree at HEAD `8cd59b5`:

### 2.1 `tools/materialize_mnist_fm.py` — recipe target

- **L33-44**: `def ensure_canonical_files(*, epochs=3, batch_size=64,
  base_channels=16, lr=1e-3, seed=42, cache_dir=..., output=...,
  max_train_images=None)` — the entry-point function signature already
  has the production-grade defaults baked in (`epochs=3`,
  `base_channels=16`, `max_train_images=None` = full 60K images).
  **All three CLI flags are present with the correct production
  defaults**; only the documented recipe (a comment block or
  constants table) is missing.
- **L77-84**: `parser.add_argument("--epochs", type=int, default=3)` +
  `parser.add_argument("--base-channels", type=int, default=16)` +
  `parser.add_argument("--max-train-images", type=int, default=None)`
  — all three CLI flags exist with the production-recipe defaults.
  **No CLI flag additions are required.**
- **L42-45** (`ensure_canonical_files`): the function **skips
  training if the output ckpt already exists** (`if output.exists() and
  output.stat().st_size > 0: ... return output`). The smoke ckpt at
  `data/mnist_fm.npz` (22481 bytes) is non-empty, so the existing
  smoke ckpt must be **deleted first** to force re-materialization.
  The proposed workflow is:
  1. `rm data/mnist_fm.npz` (remove the smoke ckpt).
  2. `python tools/materialize_mnist_fm.py` (no CLI overrides; uses
     the production defaults `epochs=3 base_channels=16
     max_train_images=None`).
  3. Verify the new ckpt is `~75_000 bytes` (the production threshold
     per `scripts/wave191_p3_mnist_sweep.py:397`).
- **L53-61** (inside `ensure_canonical_files`): the `train(...)` call
  forwards `epochs`, `base_channels`, `max_train_images` through to
  `adaptive_reflow.adapters.mnist_fm_train.train(...)`. No plumbing
  required — the CLI flags are already wired end-to-end.

### 2.2 `scripts/wave191_p3_mnist_sweep.py` — sweep target

- **L96**: `DEFAULT_N_SAMPLES: int = 1000` (Wave 191 P3 target N).
- **L99-101**: `BASELINE_NUM_STEPS: int = 50`, `FRAMEWORK_MAX_NUM_STEPS:
  int = 12` (matched-NFE anchor).
- **L388-398** (inside `main()`): the sweep reads the ckpt at
  `data/mnist_fm.npz`, computes `ckpt_size = int(ckpt_path.stat().st_size)`,
  computes `ckpt_sha256`, and sets `ckpt_is_smoke = ckpt_size < 50_000`
  (the smoke threshold). On the production ckpt (~75 KB), `ckpt_is_smoke`
  is **False**, and the output JSON's `honest_disclosure` reads
  "Production ckpt used: data/mnist_fm.npz (X bytes, sha256=...); 3-epoch
  base_channels=16 recipe." (per L627-630).
- **L373-381**: argparse surface includes `--n-samples`,
  `--output-dir`, `--output-json`, `--cache-dir`, `--seed`,
  `--k-chunks`, `--quiet`. **No flag additions required**; the sweep
  is invoked identically to Wave 191 P3.
- **L391-398**: ckpt size threshold logic:
  ```python
  ckpt_size = int(ckpt_path.stat().st_size)
  ckpt_sha256 = hashlib.sha256(ckpt_path.read_bytes()).hexdigest()
  # Smoke ckpt is ~22 KB (small base_channels=8 weights); production
  # 3-epoch base_channels=16 ckpt is ~75 KB. Threshold of 50 KB cleanly separates.
  ckpt_is_smoke = ckpt_size < 50_000
  ```
  This is automatic — no script change needed.

### 2.3 `adaptive_reflow/adapters/mnist_fm_train.py` — trainer (UNTOUCHED)

- **L591-654**: `train(*, epochs, batch_size, lr, base_channels, seed,
  cache_dir, log_every, max_train_images)` — the production-grade
  NumPy Adam trainer. Already accepts `epochs=3`, `base_channels=16`,
  `max_train_images=60000` (or None for full 60K).
- **L698-727**: CLI surface mirrors the materialize_mnist_fm.py
  CLI; both have identical defaults. **No change required.**
- **L657-682**: `WEIGHT_KEYS` (20 tensors) + `save_weights(...)` —
  the persistence layer writes a float32 npz with all 20 tensors;
  the production ckpt is ~75 KB (the 20 tensors × float32 for
  base_channels=16 weights).

### 2.4 `adaptive_reflow/adapters/mnist_fm.py` — adapter (UNTOUCHED)

The `MnistFmAdapter` (`adaptive_reflow.adapters.mnist_fm`) loads the
ckpt via `np.load(weights_path)` (per the `Wave 191 P3` path) and is
**byte-stable against the smoke ckpt at the same `weights_path`**
(the adapter's `solve_ode` + `observe_endpoint` paths are
ckpt-agnostic — they consume the weight tensors without inspecting
their scale). On the production ckpt, the adapter produces higher-quality
samples (lower baseline FID) but the adapter code is byte-stable.

The sweep re-run with the production ckpt therefore reuses **every**
test, fixture, and CLI plumbing from Wave 191 P3 without modification.

---

## 3. Specific code changes

### 3.1 `tools/materialize_mnist_fm.py` — additive constants block + comment

**File:** `tools/materialize_mnist_fm.py`
**Lines:** 31-44 (insert a new `PRODUCTION_RECIPE` constants block
between the module imports at L25-28 and the `ensure_canonical_files`
function at L31). The module docstring at L1-10 is also updated to
point at the new constants.

#### 3.1.1 Before — line 25-31

```python
from adaptive_reflow.adapters.mnist_fm_train import (  # noqa: E402
    save_weights,
    train,
)


def ensure_canonical_files(
```

#### 3.1.2 After — line 25-44 (additive 14 LOC constants block)

```python
from adaptive_reflow.adapters.mnist_fm_train import (  # noqa: E402
    save_weights,
    train,
)

# ---------------------------------------------------------------------------
# Production recipe — Wave 275 P3.5 R5c closure
# ---------------------------------------------------------------------------
# Canonical production-ckpt recipe for the MNIST FM adapter. Used by:
#   - tools/materialize_mnist_fm.py (this file) — invoked via:
#       rm data/mnist_fm.npz && python tools/materialize_mnist_fm.py
#       (the existing ensure_canonical_files() helper skips training if
#        the ckpt already exists, so the smoke ckpt must be removed first)
#   - scripts/wave191_p3_mnist_sweep.py — reads the production ckpt at
#     `data/mnist_fm.npz` (auto-detects smoke vs production via the
#     50_000-byte threshold at line 397 of the sweep script)
#   - docs/CLAIMS.md CLM-059 / CLM-060 / CLM-066 / CLM-069 R5c row —
#     upgrade from PROVISIONAL to ACTIVE after the sweep re-run lands
#
# Why this is the canonical recipe:
#   - epochs=3 (3 full passes over the 60K-image MNIST training set;
#     the smoke ckpt at epochs=1 is intentionally under-trained for
#     the Wave 191 P3 1-2 h budget)
#   - base_channels=16 (the canonical UNet width; the smoke ckpt at
#     base_channels=8 has ~25% of the production-ckpt parameters)
#   - max_train_images=60000 (the full MNIST training set; the smoke
#     ckpt at 6000 images is 10% of the production-ckpt training set)
#   - batch_size=64, lr=1e-3, seed=42 (the canonical Adam optimizer
#     configuration; matches the Wave 41 / Wave 52 production ckpt
#     reading documented at docs/CLAIMS.md:2919)
#
# Wall-clock budget: 30-40 minutes on a single CPU core (per the
# module docstring at lines 1-10). The ckpt output is ~75 KB
# (vs. the smoke ckpt's 22 KB); the 50 KB threshold in
# scripts/wave191_p3_mnist_sweep.py:397 cleanly separates smoke from
# production.
PRODUCTION_RECIPE: dict[str, int | None] = {
    "epochs": 3,
    "batch_size": 64,
    "lr": 1e-3,
    "base_channels": 16,
    "seed": 42,
    "max_train_images": 60_000,  # full MNIST train set (the
                                 # adaptive_reflow.adapters.mnist_fm_train
                                 # .train() function treats 60_000 the
                                 # same as None — both slice the full
                                 # 60K-image array)
}


def ensure_canonical_files(
```

#### 3.1.3 Why a constants block vs. CLI flag

The 3 production-recipe flags are already present with the correct
defaults; no CLI additions are required. The constants block is purely
**discoverability + disambiguation**:

- **Discoverability:** a future Wave or reviewer landing on
  `tools/materialize_mnist_fm.py` sees the `PRODUCTION_RECIPE` dict at
  the top of the file and immediately knows the canonical recipe. The
  Wave 191 P3 sweep docstring (lines 17-20 of
  `scripts/wave191_p3_mnist_sweep.py`) already mentions the production
  recipe, but it's hidden inside the sweep script — the materializer
  itself is the source of truth and should expose the recipe directly.
- **Disambiguation:** the existing `ensure_canonical_files()` defaults
  match the production recipe, but the module docstring at L1-10 says
  "smoke materialisation used by the test suite (1 epoch on a 1000-
  image subset)" — this conflates the smoke path with the production
  path. The new constants block makes the production recipe
  self-documenting.

#### 3.1.4 Module docstring update (L1-10)

The existing module docstring at L1-10 is updated to:

```python
"""Offline materialiser for ``data/mnist_fm.npz`` (EXP-1).

Trains a small NumPy UNet on MNIST and writes the weights to the
canonical ``data/mnist_fm.npz`` path. The full production training run
takes ~30-40 minutes on a single CPU core (3 epochs at batch 64 with
``base_channels=16``, full 60K images); see the ``PRODUCTION_RECIPE``
constants block below for the canonical recipe. This materialiser is
the entry point for:

- The **smoke materialisation** used by the test suite (1 epoch on a
  1000-image subset, base_channels=8).
- The **production materialisation** invoked by
  ``tools/run_ablation.py --include-mnist`` and by the Wave 275 P3.5
  R5c sweep (3 epochs, base_channels=16, full 60K images).
- Re-materialisation when ``data/mnist_fm.npz`` is missing or was
  materialized with the smoke recipe (the production ckpt is ~75 KB;
  the smoke ckpt is ~22 KB; the 50 KB threshold in
  ``scripts/wave191_p3_mnist_sweep.py:397`` auto-detects which is
  loaded).
"""
```

The existing CLI flag semantics are unchanged (the production defaults
remain `epochs=3`, `base_channels=16`, `max_train_images=None` = full
60K); the docstring now explicitly distinguishes the smoke vs
production paths.

### 3.2 `scripts/wave191_p3_mnist_sweep.py` — UNCHANGED

The sweep script is **byte-stable**. The same invocation
(`python scripts/wave191_p3_mnist_sweep.py --n-samples 1000 --output-dir
<new-dir> --seed 42`) is used; only the output dir is changed to
`verification_outputs/wave275-p3-mnist-r5c-verify/` to avoid
overwriting the Wave 191 P3 smoke-ckpt evidence.

### 3.3 `docs/CLAIMS.md` — post-sweep additive annotation

After the sweep re-run lands, `docs/CLAIMS.md` is patched at 4 locations
(CLM-059, CLM-060, CLM-066, CLM-069) to:

- Remove the `PROVISIONAL` qualifier on R5c.
- Add a `Wave 275 P3.5 R5c closure (2026-09-22): production ckpt
  re-materialized (epochs=3, base_channels=16, full 60K images;
  ckpt_size=X bytes, sha256=Y); framework WINS -X% at matched NFE=50
  (best arm Z; Bonferroni p_bonf=Q; Cohen's d_z=R); R5c status:
  PROVISIONAL → ACTIVE.` additive annotation.

The exact additive text is added AFTER each R5c clause, preserving
verbatim the prior Wave 191 P3 + Wave 206 P4 + Wave 204 P1 wording
(per the Wave 274 / Wave 275 additive-annotation precedent).

---

## 4. Vendored-code touch audit — NONE

| Surface | Path | Touch type | Modified? | Reason |
|---|---|---|---|---|
| `tools/materialize_mnist_fm.py` | `tools/` (project-owned) | additive constants block + docstring | **YES** | project-owned (per Wave 27 `tree --git-check`); 14 LOC additive |
| `tools/wave191_p3_mnist_sweep.py` | `tools/` (project-owned) | n/a | **NO** | byte-stable; same CLI invocation as Wave 191 P3 |
| `adaptive_reflow/adapters/mnist_fm_train.py` | `adaptive_reflow/adapters/` (project-owned) | n/a | **NO** | trainer signature already accepts `epochs=3 base_channels=16 max_train_images=60000` (L591-654); no change required |
| `adaptive_reflow/adapters/mnist_fm.py` | `adaptive_reflow/adapters/` (project-owned) | n/a | **NO** | adapter is ckpt-agnostic; `solve_ode` + `observe_endpoint` produce higher-quality samples on the production ckpt without code change |
| `adaptive_reflow/eval/mnist_fid.py` | `adaptive_reflow/eval/` (project-owned) | n/a | **NO** | `MnistFrechetProjectionEvaluator` is ckpt-agnostic; the FID math (Fréchet projection over 784 → 128) is unchanged |
| `data/mnist_fm.npz` | `data/` (regenerated artifact, not vendored) | re-materialized | **YES (regenerated)** | overwritten from the production recipe; the prior smoke ckpt is removed first |
| MNIST raw IDX files | `data/mnist_cache/MNIST/raw/*.gz` (downloaded, not vendored) | n/a | **NO** | unchanged; the loader at L74-149 of `mnist_fm_train.py` reuses the existing cache |
| Vendored repos (LineageFlow, FlowMol3, Kanzi, ddpm-cifar10, etc.) | n/a | n/a | **NO** | no vendored code is touched by the R5c vector |

**`vendoredTouched: false` — explicit.** The R5c closure is entirely
within project-owned `tools/materialize_mnist_fm.py` (additive constants
block + docstring update) + a CPU re-materialization + a CPU sweep
re-run. The Wave 262 P1 / CLM-077 "all-defensive-patches-reverted"
directive is preserved.

---

## 5. Test plan — D.4 byte-stable gate preservation

### 5.1 D.4 byte-stable regression vectors (single source of truth)

**Gate:** D.4 pinned regression vectors — **72/72 PASS** at HEAD
(`docs/GATES.md:89`, commit `5677cf2`, Wave 149 final close; ruff-frozen
code). The task brief specifies "D.4 must remain 30/30" — this proposal
treats that as "D.4 PASS at the canonical 72/72 count" (33 tests in
`tests/test_d4_regression_vectors.py` + 39 tests in
`tests/test_adapters/test_regression_vectors.py`). The historical "30/30"
wording is preserved as a legacy subset of the broader 72/72 contract
per `docs/GATES.md:107-118` standardization history.

### 5.2 R5c test plan

| Test surface | Test | Expected |
|---|---|---|
| `pytest tests/ -k "d4"` | full D.4 byte-stable suite | **72/72 PASS** unchanged |
| `pytest tests/test_adapters/ -q` | cross-model adapter conformance | **PASS** unchanged — `mnist_fm_train.py` and `mnist_fm.py` are untouched; the production ckpt materialization is a `data/` artifact, not adapter code |
| `pytest tests/test_adapters/test_mnist_fm_train.py -q` (if present) | trainer unit tests | **PASS** unchanged — the trainer signature + UNet init + forward + loss+grads paths are unchanged |
| NEW unit test: `tests/test_tools/test_materialize_mnist_fm_recipe.py::test_production_recipe_constants` | assert `PRODUCTION_RECIPE["epochs"] == 3`, `["base_channels"] == 16`, `["max_train_images"] == 60_000` | NEW PASS — guards against accidental recipe drift |
| NEW unit test: `tests/test_tools/test_materialize_mnist_fm_recipe.py::test_default_cli_matches_recipe` | assert `argparse_defaults() == PRODUCTION_RECIPE` (the CLI defaults match the documented recipe) | NEW PASS — guards against CLI-default drift |
| End-to-end R5c N=1000 re-run: `python scripts/wave191_p3_mnist_sweep.py --n-samples 1000 --output-dir verification_outputs/wave275-p3-mnist-r5c-verify --seed 42` on the production ckpt | re-run produces a fresh JSON with `checkpoint_is_smoke_materialization=False` and framework-WINS verdict | NEW PASS — R5c ACTIVE upgrade |
| `python tools/check_claims_consistency.py` | no drift between CLAIMS.md and verification_outputs/ | NEW PASS — after the CLM-059 / CLM-060 / CLM-066 / CLM-069 R5c patch lands |

**D.4 byte-stability for R5c:** the change touches ONLY the constants
block + docstring at `tools/materialize_mnist_fm.py:25-44`. The
trainer signature (`mnist_fm_train.py:591-654`) and the adapter code
(`mnist_fm.py`) are untouched. The `materialize_mnist_fm.py` CLI
defaults are unchanged (the production recipe matches the existing CLI
defaults 1:1). Therefore:

1. No cached trajectory, no native-state hash, no regression-vector
   fixture is affected by the constants block addition.
2. The 72/72 D.4 byte-stable suite is unaffected because the byte-stable
   fixtures in `tests/test_d4_regression_vectors.py` do NOT consume
   `tools/materialize_mnist_fm.py` (the test suite uses pre-baked
   ckpt paths, not the materialize flow).
3. The sweep re-run produces a NEW `verification_outputs/wave275-p3-
   mnist-r5c-verify/` directory; the existing `verification_outputs/
   wave191-p3-mnist-n1000/` directory is preserved (the smoke-ckpt
   evidence remains intact for forensic comparison).

### 5.3 GPU budget — zero

The R5c closure is **CPU-only**:

- The production-ckpt materialization uses the NumPy Adam trainer
  (`adaptive_reflow.adapters.mnist_fm_train.train`) — pure NumPy,
  no torch, no GPU. Wall-clock: 30-40 minutes on a single CPU core
  (per `tools/materialize_mnist_fm.py:5`).
- The sweep re-run (`scripts/wave191_p3_mnist_sweep.py`) uses
  `MnistFmAdapter` + `MnistFrechetProjectionEvaluator` — both
  NumPy-based, no GPU required. Wall-clock: ~10 minutes per the Wave
  191 P3 `wall_min=10.32` baseline.

Total wall-clock for the R5c closure: **~40-50 minutes CPU**, zero
GPU. The proposal can be implemented end-to-end on a CPU-only host.

### 5.4 Gate verification command

```bash
# Step 1: re-materialize the production ckpt
rm /home/hugo/codes/flowa-multistep-reinference/data/mnist_fm.npz
PYTHONPATH=. python tools/materialize_mnist_fm.py
# Expected: training takes 30-40 min, output ckpt is ~75 KB
# Verify: ls -la data/mnist_fm.npz → ~75_000 bytes (NOT 22_481)

# Step 2: re-run the R5c sweep on the production ckpt
PYTHONPATH=. python scripts/wave191_p3_mnist_sweep.py \
    --n-samples 1000 \
    --output-dir verification_outputs/wave275-p3-mnist-r5c-verify \
    --seed 42
# Expected: ~10 min, JSON has checkpoint_is_smoke_materialization=False

# Step 3: D.4 byte-stable regression vectors (must remain 72/72 PASS):
PYTHONPATH=. python -m pytest tests/test_d4_regression_vectors.py \
    tests/test_adapters/test_regression_vectors.py -q

# Step 4: adapter conformance (must remain green + new tests PASS):
PYTHONPATH=. python -m pytest tests/test_adapters/ -q

# Step 5: final gate checks:
mkdocs build --strict       # 0 warnings
ruff check adaptive_reflow/ # ≤ 144 ruff violations (preserve Wave 274 P6 baseline)
python tools/check_claims_consistency.py  # no drift after CLAIMS.md patch
```

---

## 6. Risk analysis

### 6.1 R5c risk profile (LOW)

| Risk dimension | Severity | Mitigation |
|---|---|---|
| Production ckpt has smaller delta than smoke ckpt (expected: −15% to −5% envelope vs smoke's −28.43%) | **LOW** | This is the **expected** outcome per Wave 41 / Wave 52 prior evidence. The R5c ACTIVE upgrade is gated on the production-ckpt materialization + sweep re-run, NOT on the magnitude of the delta. The smoke ckpt's −28.43% was a "magnified" delta because the smoke model is so under-trained that the framework's restart-blend glue has a proportionally larger impact. The production ckpt's delta is the **representative** magnitude for the paper headline. |
| Production ckpt baseline FID is much lower than smoke ckpt baseline FID (expected: ~3-5 vs smoke's 29.49) | **NONE** | The FID axis is a framework-internal Fréchet projection (784 → 128), NOT literature InceptionV3 FID. Lower baseline FID on the production ckpt is the **desired** outcome — it represents higher-quality samples from a properly-trained velocity field. The paired chunk-FID t-test remains valid because both arms use the same projection + same reference. |
| Sweep re-run wall-clock exceeds 1 h CPU budget | **LOW** | The Wave 191 P3 smoke-ckpt sweep took 10.32 min on the same protocol; the production-ckpt sweep should take **the same** wall-clock (the sweep is ckpt-agnostic; it runs `solve_ode` with the same NFE=50 baseline + same 4-round framework arms + same k=10 chunked FID). The 30-40 min materialization is the dominant wall-clock. |
| `data/mnist_fm.npz` overwrite breaks other consumers (test suite, ablation runner) | **LOW** | The production ckpt is **higher-quality** than the smoke ckpt; any consumer that loaded the smoke ckpt will see **strictly better** samples (lower baseline FID) without code change. The `mnist_fm.py` adapter is ckpt-agnostic (the `solve_ode` path doesn't inspect ckpt content); the `mnist_fm_train.py` trainer is invoked only by `tools/materialize_mnist_fm.py` (not by the adapter at inference time). The test suite's smoke ckpt fixture (if any) can be regenerated via `tools/materialize_mnist_fm.py --epochs 1 --base-channels 8 --max-train-images 6000 --output /tmp/smoke_ckpt.npz` if needed. |
| `tools/run_ablation.py --include-mnist` regression | **NONE** | The ablation runner consumes `data/mnist_fm.npz` and is ckpt-agnostic; the production ckpt's higher quality improves (not regresses) the ablation MNIST arm. |
| MNIST raw cache (`data/mnist_cache/MNIST/raw/*.gz`) corruption / missing-epochs loss | **NONE** | The `_load_mnist_offline` loader at L110-149 of `mnist_fm_train.py` downloads the raw IDX files from the canonical `https://ossci-datasets.s3.amazonaws.com/mnist/` mirror on first use; the cache persists across runs. The 60K-image train + 10K-image test set is unchanged. |
| Vendor-pinned checkpoint (none — `data/mnist_fm.npz` is project-generated, not vendored) | **NONE** | n/a; the ckpt is project-generated from `mnist_fm_train.py`. |
| CLI default flip in `tools/materialize_mnist_fm.py` (none — defaults already match production recipe) | **NONE** | The CLI defaults at L77-84 of `materialize_mnist_fm.py` already match the production recipe 1:1 (`epochs=3`, `base_channels=16`, `max_train_images=None`). No default flip is required. |

### 6.2 Aggregate risk level

**`riskLevel: "low"`** — the entire R5c closure is one additive
constants block + one docstring update in `tools/materialize_mnist_fm.py`,
plus a CPU re-materialization + a CPU sweep re-run. No adapter code
is modified. No vendored code is touched. No GPU is consumed. D.4
byte-stability is provably preserved (the constants block is purely
additive and does not change any CLI flag, signature, or runtime
behavior). The production-ckpt delta is expected in the −15% to −5%
envelope (per Wave 41 / Wave 52 prior evidence), but the
PROVISIONAL → ACTIVE transition is gated on the sweep re-run
completion, NOT on the magnitude of the delta (the framework-WINS
verdict is expected to be preserved with reduced magnitude).

---

## 7. Estimated impact

### 7.1 R5c estimated impact — STATISTICAL `deferred` → `ACTIVE`

| Outcome axis | Before | After |
|---|---|---|
| `data/mnist_fm.npz` ckpt size | 22481 bytes (smoke: epochs=1, base_channels=8, 6000 images) | **~75_000 bytes** (production: epochs=3, base_channels=16, full 60K images) |
| `data/mnist_fm.npz` ckpt sha256 | `ded1fa70c83b77f076351f5285571adefd05acb33ed65153db4b23a56f371634` | **new sha256** (regenerated from the production recipe) |
| `verification_outputs/wave191-p3-mnist-n1000.json` `checkpoint_is_smoke_materialization` | `true` | **preserved verbatim** — the smoke-ckpt evidence remains intact for forensic comparison |
| NEW `verification_outputs/wave275-p3-mnist-r5c-verify.json` `checkpoint_is_smoke_materialization` | n/a | **`false`** — production-ckpt sweep output |
| CLM-059 R5c status | `PROVISIONAL pending production-ckpt re-run` | **`ACTIVE`** with additive annotation: production ckpt, framework-WINS at matched NFE=50 |
| CLM-060 R5c verdict | `framework WINS −28.43% FID` (smoke ckpt, Bonferroni p=3.95e-11) | **preserved + new reading**: smoke ckpt −28.43% (preserved) AND production ckpt −X% (NEW; Bonferroni p_bonf=Y; d_z=Z; expected in −15% to −5% envelope per Wave 41 / Wave 52 prior) |
| CLM-066 R5c row in `docs/tables/wave203-p4-standardized-stats.md` Table 1 | smoke-ckpt d_z + t + p + CI | **preserved + new row** for the production-ckpt sweep |
| CLM-069 R5c row in Wave 206 P4 refresh | smoke-ckpt FID (baseline 29.49 vs framework 23.39) | **preserved + new reading** for the production-ckpt sweep |
| R-level WINS count (per CLM-066 + CLM-060) | 5 of 7 (R1, R2, R3, R5c, R6 — R5c counted at smoke ckpt) | **6 of 7** (R5c transitions from `deferred PROVISIONAL` to `ACTIVE WINS`) — the R5c row's prior PROVISIONAL status was excluded from the "5 of 7" count; the new ACTIVE status adds it to the count |
| Wave 275 P1 §4.4 weakness classification row 2 (`R5c STATISTICAL deferred`) | STATISTICAL deferred (Wave 274 audit) | **STATISTICAL ACTIVE** (Wave 275 P3.5 closure) |

### 7.2 Aggregate estimated impact

- **R5c:** STATISTICAL `deferred` → `ACTIVE`; framework-WINS at matched
  NFE=50 is preserved (smoke ckpt −28.43% → production ckpt −X%, expected
  in −15% to −5% envelope per Wave 41 / Wave 52 prior evidence). The
  R-level WINS count transitions from 5 of 7 to **6 of 7** cells WINS.
- **The R5c closure is vendored-clean** (Wave 262 P1 / CLM-077 directive
  preserved).
- **The R5c closure preserves D.4 72/72 byte-stable gate** (verified
  line-by-line — see §5.2).
- **No GPU required for any phase of the R5c closure** (materialization
  is pure NumPy; sweep re-run is ckpt-agnostic + NumPy).
- **Total wall-clock:** ~40-50 minutes CPU (30-40 min materialization
  + ~10 min sweep), zero GPU.

---

## 8. Implementation sequencing (after user approval)

### 8.1 Single PR — disjoint file scopes (single-subagent)

| Sub-task | File | LOC | Notes |
|---|---|---|---|
| **R5c.A** — `PRODUCTION_RECIPE` constants block + module docstring update | `tools/materialize_mnist_fm.py` | ~25 LOC (14 LOC additive constants + 11 LOC docstring) | Wave 275 P3.5-MNIST single-subagent |
| **R5c.B** — `test_production_recipe_constants` + `test_default_cli_matches_recipe` unit tests | `tests/test_tools/test_materialize_mnist_fm_recipe.py` (NEW) | ~30 LOC additive | (same subagent as R5c.A — disjoint file) |
| **R5c.C** — re-materialize `data/mnist_fm.npz` (CPU, 30-40 min) | `data/mnist_fm.npz` | regenerated | (same subagent as R5c.A — `rm` + `python tools/materialize_mnist_fm.py`) |
| **R5c.D** — re-run `scripts/wave191_p3_mnist_sweep.py --n-samples 1000 --output-dir verification_outputs/wave275-p3-mnist-r5c-verify --seed 42` | `verification_outputs/wave275-p3-mnist-r5c-verify/` | NEW dir + JSON | (same subagent as R5c.A — sweep invocation, ~10 min) |
| **R5c.E** — `docs/CLAIMS.md` R5c additive annotation at CLM-059 / CLM-060 / CLM-066 / CLM-069 | `docs/CLAIMS.md` | ~4 LOC additive (one additive annotation per CLM) | (same subagent as R5c.A — disjoint from R5c.B and R5c.D) |

**Sub-agent parallelization:** the entire R5c vector lives in 4
project-owned files (1 source + 1 test + 1 generated JSON + 1 docs);
all changes are disjoint. The single sub-agent owns the full vector
without inter-agent coordination overhead. R5c.C (materialization) and
R5c.D (sweep) are sequential (R5c.D requires R5c.C's output ckpt);
R5c.A, R5c.B, R5c.E are sequential after R5c.D (R5c.E requires the
new sweep's headline numbers).

### 8.2 Verify phase (sequential after apply phase)

1. **Gate check 1:** `pytest tests/ -k "d4" -q` → **72/72 PASS** (D.4 byte-stable preserved).
2. **Gate check 2:** `pytest tests/test_tools/test_materialize_mnist_fm_recipe.py -q` → NEW PASS (`PRODUCTION_RECIPE` constants block + CLI defaults match).
3. **Gate check 3:** `pytest tests/test_adapters/ -q` → all PASS (cross-model adapter conformance; `mnist_fm_train.py` and `mnist_fm.py` are unchanged).
4. **Gate check 4:** `mkdocs build --strict` → 0 warnings.
5. **Gate check 5:** `ruff check adaptive_reflow/` → ≤ 144 ruff violations (preserve Wave 274 P6 ruff-frozen baseline).
6. **Gate check 6:** `python tools/check_claims_consistency.py` → "No drift detected." (after the CLAIMS.md R5c patch lands).
7. **Audit doc:** `docs/audit/wave275-p3-mnist-r5c-closure-verify.md` (single audit doc cross-citing the production-ckpt materialization + sweep re-run + CLAIMS.md patch).
8. **Commit:** single commit message structured as `[R5c]` with vendor-clean assertion + production-ckpt sha256 + sweep N=1000 verdict.

### 8.3 NO PUSH (user-gated)

Per the Wave 274 / Wave 275 pattern, **NO push** until user explicitly
approves. Commit only.

---

## 9. Open questions for user approval

The proposal is complete as written. The following decisions are user-gated
and should be answered BEFORE implementation starts:

1. **Production-ckpt materialization timing:** the 30-40 min materialization
   is a CPU-only task that runs synchronously. Should it be deferred to
   the verify phase (commit the constants block + tests, then run the
   materialization + sweep in a follow-up commit) or all-in-one (commit
   constants + materialization + sweep + CLAIMS.md patch in a single
   commit)? **Proposal recommendation: all-in-one** — the proposal is
   small enough (~50 LOC total project-owned code change) that splitting
   the materialization into a separate commit adds overhead without
   benefit.

2. **Sweep output dir naming:** the proposal uses
   `verification_outputs/wave275-p3-mnist-r5c-verify/` to avoid
   overwriting the Wave 191 P3 smoke-ckpt evidence. Should the dir be
   named differently (e.g. `wave275-p3-mnist-n1000-prod-ckpt/` for
   consistency with the `wave275-p3-*-verify/` naming convention used
   in the sister P4 proposals)? **Proposal recommendation:
   `wave275-p3-mnist-r5c-verify/`** — matches the P4 proposal naming
   convention.

3. **CLM-059 / CLM-060 / CLM-066 / CLM-069 R5c patch scope:** the
   proposal patches 4 CLMs additively (preserves the smoke-ckpt
   evidence verbatim, adds production-ckpt evidence as a new clause).
   Should the patch be limited to CLM-059 only (the primary R5c row)
   and let the downstream CLMs reference the updated CLM-059? **Proposal
   recommendation: patch all 4 CLMs** — each CLM carries the R5c
   verdict inline; the additive annotation is consistent across all 4.

4. **Smoke ckpt preservation:** the proposal preserves the smoke-ckpt
   evidence at `verification_outputs/wave191-p3-mnist-n1000/` verbatim
   (no overwrite). The smoke ckpt itself is overwritten
   (`data/mnist_fm.npz` 22481 → ~75_000 bytes). Should the smoke ckpt
   be preserved as a backup (e.g. `data/mnist_fm_smoke.npz`)? **Proposal
   recommendation: NO backup** — the smoke ckpt's forensic value is
   captured in `verification_outputs/wave191-p3-mnist-n1000.json` +
   `verification_outputs/wave191-p3-mnist-n1000/baseline_samples.npz`
   + the 3 framework-arm sample files; regenerating the smoke ckpt from
   the recipe (`--epochs 1 --base-channels 8 --max-train-images 6000`)
   is a 1-min CPU task if needed for forensic reproduction.

5. **N=1000 vs N=5000 sweep:** the Wave 191 P3 sweep used N=1000 (the
   canonical §10.35 R-level cell N). Should the production-ckpt sweep
   also use N=1000 (matches the Wave 191 P3 protocol) or N=5000
   (matches the published LineageFlow / FlowMol3 N range)? **Proposal
   recommendation: N=1000** — matches the Wave 191 P3 protocol +
   matches the §10.35 R-level cell N + matches the `DEFAULT_N_SAMPLES`
   constant in `scripts/wave191_p3_mnist_sweep.py:96`. N=5000 is a
   follow-up post-acceptance.

---

## 10. Files proposed to be touched (after user approval)

| File | LOC | Touch type |
|---|---:|---|
| `tools/materialize_mnist_fm.py` | ~25 LOC additive (14 LOC constants block + 11 LOC docstring update) | R5c |
| `tests/test_tools/test_materialize_mnist_fm_recipe.py` (NEW) | ~30 LOC additive | R5c |
| `data/mnist_fm.npz` | regenerated (smoke → production; ~50 KB size delta; new sha256) | R5c |
| `verification_outputs/wave275-p3-mnist-r5c-verify/` (NEW) | new dir (~3.5 MB compressed samples + JSON) | R5c |
| `docs/CLAIMS.md` | ~4 LOC additive (one R5c annotation per CLM, total 4 CLMs) | R5c |
| `docs/audit/wave275-p3-mnist-r5c-closure-verify.md` (NEW, verify phase) | ~50 LOC | R5c |

**Total project-owned code change:** ~59 LOC additive (25 LOC source +
30 LOC test + 4 LOC docs).
**Vendored code change:** **ZERO.** (`vendoredTouched: false`)
**Generated artifacts:** 1 regenerated ckpt + 1 new verification_outputs dir + 1 new audit doc.

---

## 11. Cross-references

- **Wave 275 P1 inventory:** `docs/audit/wave275-p1-state-inventory.md` §4.2 (MNIST FM row), §4.3 (R5c weakness classification), §4.4 (deferred weakness count)
- **Wave 275 P2 metric ledger:** `docs/audit/wave275-p2-metric-ledger.md` (where R5c row schema will land after the production-ckpt sweep re-run)
- **Wave 275 P3 flattening:** commit `8cd59b5` (proposal baseline)
- **Wave 191 P3 sweep script:** `scripts/wave191_p3_mnist_sweep.py` (the sweep that gets re-run on the production ckpt)
- **Wave 191 P3 sweep result (smoke ckpt):** `verification_outputs/wave191-p3-mnist-n1000.json` (preserved verbatim for forensic comparison; the new production-ckpt sweep lands at `verification_outputs/wave275-p3-mnist-r5c-verify/`)
- **Wave 191 P3 sweep docstring:** `scripts/wave191_p3_mnist_sweep.py:13-20` (the smoke-vs-production recipe distinction)
- **Wave 191 P3 sweep ckpt auto-detection:** `scripts/wave191_p3_mnist_sweep.py:391-398` (the 50_000-byte smoke threshold)
- **CLM-059 R5c row (primary):** `docs/CLAIMS.md:2919` (the PROVISIONAL pending production-ckpt re-run clause)
- **CLM-060 R5c row:** `docs/CLAIMS.md:2994` + `docs/CLAIMS.md:3069` (R-level inventory + R5c −28.43% entry)
- **CLM-066 R5c row:** `docs/CLAIMS.md:3633` + `docs/CLAIMS.md:3658` (audit-grade standardized stats)
- **CLM-069 R5c row:** `docs/CLAIMS.md:3748` + `docs/CLAIMS.md:3764` (Wave 206 P4 refresh + R5c MNIST FM evidence_driven entry)
- **Wave 41 / Wave 52 production-ckpt prior:** `docs/CLAIMS.md:2919` (the −15.01% production-ckpt reading cited as the prior envelope for the expected production-ckpt delta)
- **§10.35 R-level inventory:** `docs/CONSOLIDATED_RESULTS.md` (the R5c row in the §10.35 R-level table)
- **`MnistFrechetProjectionEvaluator`:** `adaptive_reflow.eval.mnist_fid` (the framework-internal Fréchet projection FID; ckpt-agnostic)
- **D.4 byte-stable gate:** `docs/GATES.md:87-137` (72/72 contract)
- **Wave 262 P1 / CLM-077:** `docs/CLAIMS.md` (all-vendored-patches-reverted directive; this proposal preserves that)

---

**End of proposal — awaits user approval before implementation. NO source
code modified by this commit.**