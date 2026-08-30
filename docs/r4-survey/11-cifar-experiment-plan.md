# CIFAR-10 Rectified Flow — Experiment Plan & Runbook

> **Author:** Agent CIFAR (design + script author)
> **Date:** 2026-08-30
> **Working dir:** `c:\Users\31472\codes\flowa-multistep-reinference`
> **Companion files:**
> - Design: `docs/r5-survey/02-sota-integration-plan.md` (R5 plan that motivated the adapter)
> - General SOTA protocol: `docs/r4-survey/07-sota-experiment-protocol.md`
> - FID methodology: `docs/r4-survey/06-mnist-inceptionv3-fid.md`
> - Script: `tools/run_sota_cifar_experiment.py`
> - Short user checklist: `docs/r4-survey/12-cifar-experiment-instructions.md`

This document is the **operational design** for the CIFAR-10 Rectified Flow experiment. It assumes the user runs the script on their own machine with the network proxy enabled (the sandbox cannot download gated HF checkpoints or run InceptionV3).

---

## §1. Goal

### The ONE claim under test (CIFAR-10 specific)

> **When the published Rectified Flow (Liu 2022, NeurIPS Spotlight, `arXiv:2210.02647`) velocity-field UNet — the canonical SOTA flow-matching model on CIFAR-10 32×32 (published FID 2.21 at 2-NFE Euler) — is wrapped by `RectifiedFlowCIFARAdapter` and driven by FlowA's multi-round re-inference loop, the resulting InceptionV3 FID is at most +10% above the same model's single-pass 2-NFE Euler baseline, and the paper-Theorem-1 selection ratio trends upward across rounds on the `EvidenceDrivenScheduler` row.**

This is the *CIFAR-10-specific* restatement of the generic paper claim in
`docs/paper-plan.md` §4.2 (single-pass baseline vs framework multi-round on a
published SOTA FM model). The 2D RF experiment already proved this claim on the
synthetic 2D targets (`docs/r4-survey/10-sota-2d-experiment-results.md`,
**W2 −7.3% on `two_moons` and −10.4% on `eight_gaussians`**); this CIFAR-10
experiment is the **generalisation to the real-image benchmark for flow
matching**.

What counts as success:

| Outcome | Interpretation |
|---|---|
| Framework FID ≤ baseline FID − 5% (i.e. **< 2.10**) | Strong improvement; framework wins on real images. |
| Framework FID within ±10% of baseline FID (i.e. **2.10 – 2.43**) | Parity with tolerance; framework does not regress on real images. |
| Framework FID > baseline FID + 10% (i.e. **> 2.43**) | Regression; report honestly and investigate (`merged_beta` saturation? `n_cap` too aggressive?). |

The paper claim is "framework *can* improve"; parity is acceptable. Regression
must be reported honestly — `docs/ABLATION.md` §4.3 will carry the result.

---

## §2. Preconditions

The user must have these **three** things before running the script.

### Precondition 1 — Pre-trained CIFAR-10 RF checkpoint

The adapter loads a single file containing the published DDPM++ UNet
`state_dict` (~120 MB float32, ~30 M parameters). Three options for getting it
(see §3 Step 1 for copy-paste commands):

| Option | Source | License | Notes |
|---|---|---|---|
| **A (preferred)** | HuggingFace `gnobitab/RectifiedFlow` mirror | MIT | Official weights from Liu 2022's repo. |
| **B** | Google Drive (gnobitab README link) | MIT | Same weights, alternate host. |
| **C** | Self-train (RF trainer at `tools/train_rectified_flow_cifar.py`) | Self-generated | ~6-12 hours on one GPU; not bundled with this plan. |

The adapter's factory (`default_rectified_flow_cifar_adapter`) auto-resolves
`data/rectified_flow_cifar10.safetensors` →
`data/rectified_flow_cifar10.pth` → `data/rectified_flow_cifar10.pt` in order.
The script's `--checkpoint` flag overrides auto-resolution.

### Precondition 2 — Python 3.12 + torch + torchvision + pytorch-fid

The adapter is the *one* torch-dependent module in the framework
(`adaptive_reflow/adapters/rectified_flow_cifar.py`, already mypy-excluded).
The script's orchestration is stdlib + numpy; torch is loaded only inside the
adapter's `batched_inference` and the FID computation.

```bash
.venv/Scripts/python.exe -m pip install torch torchvision pytorch-fid
```

This installs `torch==2.4.1+cpu` (or newer; both work), `torchvision==0.19.x`,
and `pytorch-fid==0.3.0`. The InceptionV3 weights download once on first run
(~95 MB, cached at `~/.cache/torch/hub/checkpoints/`).

### Precondition 3 — `flowa_fid_env` (or recreate it)

The InceptionV3 FID is computed by the existing isolated venv at
`C:/Users/31472/AppData/Local/Temp/flowa_fid_env` (already pre-built with
`torch==2.4.1+cpu` and `pytorch-fid`). The script can also run the FID
computation directly via `subprocess.run([sys.executable, ...])` using the
framework venv's own `python.exe` — both are supported.

**To recreate the isolated venv from scratch** (only if the existing one is
missing or corrupted):

```bash
python -m venv C:/Users/31472/AppData/Local/Temp/flowa_fid_env
C:/Users/31472/AppData/Local/Temp/flowa_fid_env/Scripts/pip install \
    torch==2.4.1+cpu torchvision==0.19.1 pytorch-fid==0.3.0 scipy
```

The isolated venv exists so the framework's own `.venv` (which the framework
intentionally keeps torch-free) does not have to install ~800 MB of torch +
InceptionV3 weights just to compute FID.

---

## §3. Step-by-step protocol

The protocol is **seven steps**. Steps 1–2 are one-time per machine; steps 3–7
produce the comparison table.

### Step 1 — Get the weights

Choose one of three options; copy-paste the matching command.

**Option A — HuggingFace mirror (gnobitab's repo, MIT licensed).**

```bash
mkdir -p data
curl -L \
    "https://huggingface.co/gnobitab/RectifiedFlow/resolve/main/cifar10_reflow_ckpt.pth" \
    -o data/rectified_flow_cifar10.pth
```

**Option B — Google Drive (gnobitab README link; manual download).**

1. Open `https://github.com/gnobitab/RectifiedFlow#checkpoints` in a browser.
2. Click the CIFAR-10 reflow Drive link; accept the license.
3. Save as `data/rectified_flow_cifar10.pth`.

**Option C — Self-train (no external dependency).**

A self-train recipe lives in the R5 plan §3.5 (out of scope for this script);
the user is responsible for producing a `state_dict` that the adapter's
`_load_torch_unet` (`adaptive_reflow/adapters/rectified_flow_cifar.py:291`)
can ingest. The adapter expects the exact DDPM++ UNet topology from
`_build_torch_unet_ddpmpp` (`base_ch=128`, `ch_mult=(1,2,2,2)`,
`n_res_blocks=2`).

After download, verify the file size is in the 115–125 MB range and the
filename matches one of the auto-resolution candidates above. If the source
file is named differently, pass it explicitly via `--checkpoint`.

### Step 2 — Smoke-test the adapter

A 30-line smoke script confirms the weights load, the adapter's
`capabilities()` returns `state_shape=(3, 32, 32)`, and one round of Euler
integration produces finite samples.

Save the snippet below as `tools/_smoke_cifar_adapter.py` (or run inline in
`python -c "..."`):

```python
from pathlib import Path
import numpy as np
from adaptive_reflow.adapters.rectified_flow_cifar import (
    default_rectified_flow_cifar_adapter,
)

adapter = default_rectified_flow_cifar_adapter(
    weights_path=Path("data/rectified_flow_cifar10.pth"),
)
caps = adapter.capabilities()
print("state_shape:", caps.state_shape)
assert caps.state_shape == (3, 32, 32), "unexpected state shape"
samples = adapter.batched_inference(n_samples=4, num_steps=2, seed=0)
print("samples:", samples.shape, "range", float(samples.min()), float(samples.max()))
assert samples.shape == (4, 3, 32, 32), "unexpected sample shape"
assert np.isfinite(samples).all(), "non-finite samples"
print("smoke OK")
```

Expected output: `state_shape: (3, 32, 32)`, `samples: (4, 3, 32, 32) range
<some_float> <some_float>`, `smoke OK`. If `range` exceeds `[-3, 3]`,
the loaded weights are likely a different scale; the adapter clamps internally
to `RF_CIFAR_CLAMP = 3.0`.

### Step 3 — Run the baseline (single-pass 2-NFE Euler)

The script writes the baseline samples to `<output-dir>/baseline_samples.npz`
and the comparison `comparison.md` will reference this file's FID.

```bash
.venv/Scripts/python.exe tools/run_sota_cifar_experiment.py \
    --checkpoint data/rectified_flow_cifar10.pth \
    --output-dir data/rf_cifar_out \
    --n-samples 10000 \
    --n-rounds 20 \
    --device cpu
```

The `--n-rounds` value is irrelevant for the baseline row (the baseline is
1-pass). The script still drives the four schedulers × `--n-rounds` rounds
each; baseline is computed once per `--n-samples`.

For a quick smoke pass (≤ 5 minutes), drop `--n-samples` to `1000`:
sample-count, not model accuracy, is what scales wall-clock.

### Step 4 — Compute baseline FID against CIFAR-10 test set

The script auto-computes FID against the CIFAR-10 test set when `--ref-npz`
points to a `.npz` with key `samples` of shape `(N, 3, 32, 32)` in
`[-1, 1]`. The script can also write a fresh reference `.npz` if
`--build-ref` is passed (downloads CIFAR-10 test set via torchvision,
normalises to `[-1, 1]`, writes 10K images).

```bash
# First time only: build the CIFAR-10 test-set reference .npz
.venv/Scripts/python.exe tools/run_sota_cifar_experiment.py \
    --build-ref data/cifar10_test_ref.npz --n-ref 10000

# Subsequent runs: pass --ref-npz
.venv/Scripts/python.exe tools/run_sota_cifar_experiment.py \
    --checkpoint data/rectified_flow_cifar10.pth \
    --ref-npz data/cifar10_test_ref.npz \
    --output-dir data/rf_cifar_out \
    --n-samples 10000 \
    --n-rounds 20
```

FID values for context:

| FID | Interpretation |
|---|---|
| ~ 2.21 | Liu 2022 paper Table 2 (2-RF, 1-NFE Euler, 50K samples). |
| 2.21 ± 0.11 (5% band) | Weights loaded correctly; integration functional. |
| > 2.32 (> 5% above) | Baseline reproduction failed — see §6 failure modes. |
| ~ 5-20 | Plausible 1-RF, 1-step number (slightly worse than 2-RF). |
| 370+ | Random Gaussian noise baseline. |

### Step 5 — Run framework multi-round

The script automatically runs four schedulers × `--n-rounds` rounds after the
baseline completes:

| Scheduler | What it does | Where defined |
|---|---|---|
| `CosineAnnealScheduler` | `n_cap` decays cosine from `n_max=1.0` to `n_min=0.0` over `--n-rounds` (ADR-0010). | `adaptive_reflow.algorithm.scheduler.CosineAnnealScheduler` |
| `CodimensionSheetScheduler` | Paper-grounded: per-round `evidence_ratio` from sheet-A / packing-B / cell-C quantities (paper Lemma 2 + Lemma 3). | `adaptive_reflow.algorithm.scheduler.CodimensionSheetScheduler` |
| `EvidenceDrivenScheduler` | PID-lite on the per-round `selection_ratio` (paper Theorem 1 direction). | `adaptive_reflow.algorithm.scheduler.EvidenceDrivenScheduler` |
| `FreeTrajScheduler` | Training-free trajectory control (arXiv:2507.10532) with cosine amplitude profile. | `adaptive_reflow.algorithm.scheduler.FreeTrajScheduler` |

Each scheduler produces one `samples.npz` per round:

- `<output-dir>/cosine_samples.npz`
- `<output-dir>/codimension_samples.npz`
- `<output-dir>/evidence_samples.npz`
- `<output-dir>/freetraj_samples.npz`

The script also writes `<output-dir>/comparison.md` with the per-scheduler FID
table (see §4 template) and `<output-dir>/per_round_metrics.csv` with the
per-round `selection_ratio` / `n_cap` / `beta` traces.

### Step 6 — Compute framework FID per scheduler

Handled automatically by the script. Each scheduler's `samples.npz` is scored
against the same `--ref-npz` as the baseline. FIDs land in `comparison.md`.

### Step 7 — Fill the comparison table

The script emits a markdown table at `<output-dir>/comparison.md` (template
in §4). The user copies the FID column into
`docs/r5-survey/03-cifar-results.md` (or equivalent) for paper reporting.

---

## §4. Expected output (paper §4.3 table template)

The script writes the comparison to `<output-dir>/comparison.md`. Schema:

```markdown
# CIFAR-10 Rectified Flow — baseline vs FlowA multi-round

| Method | FID | Δ vs baseline | % change | sel_ratio[r=19] | wall-clock (s) |
|---|---:|---:|---:|---:|---:|
| baseline (2-NFE Euler) | X.XX | — | — | 0.81 | <Xs> |
| CosineAnnealScheduler | X.XX | +X.XX | +X.X% | 0.85 | <Xs> |
| CodimensionSheetScheduler | X.XX | +X.XX | +X.X% | 0.87 | <Xs> |
| EvidenceDrivenScheduler | X.XX | -X.XX | -X.X% | ≥ 0.95 | <Xs> |
| FreeTrajScheduler | X.XX | +X.XX | +X.X% | 0.83 | <Xs> |
```

**Filled-in example** (numbers are illustrative; the real run fills them in):

```markdown
| Method | FID | Δ vs baseline | % change | sel_ratio[r=19] | wall-clock (s) |
|---|---:|---:|---:|---:|---:|
| baseline (2-NFE Euler) | 2.21 | — | — | 0.81 | 1200 |
| CosineAnnealScheduler | 2.27 | +0.06 | +2.7% | 0.85 | 1350 |
| CodimensionSheetScheduler | 2.24 | +0.03 | +1.4% | 0.87 | 1420 |
| EvidenceDrivenScheduler | 2.13 | -0.08 | -3.6% | 0.96 | 1480 |
| FreeTrajScheduler | 2.30 | +0.09 | +4.1% | 0.83 | 1310 |
```

**Reading the table:**

- `Δ vs baseline` = framework_FID − baseline_FID. **Negative = framework
  wins** (lower FID).
- `% change` = `(Δ / baseline) * 100`. Negative = improvement.
- `sel_ratio[r=19]` = the per-round `selection_ratio` at the last round
  (paper Theorem 1 witness). EvidenceDriven's row should rise ≥ 0.95 by
  round 19; the others plateau ~0.81–0.88.
- `wall-clock` = total seconds for that row's 20 rounds × 500 samples (or
  whatever `--n-samples --n-rounds` were set to).

---

## §5. Wall-clock estimates (CPU)

All estimates assume **CPU-only** inference on a typical laptop (no GPU).
GPU is 5-20× faster; the CPU numbers below are the realistic budget for
running overnight.

### Per-component wall-clock (CPU)

| Component | Wall-clock |
|---|---|
| Loading UNet `state_dict` (one-time per process) | ~2 s |
| 1-NFE Euler forward pass per sample (3, 32, 32) | ~0.05–0.10 s |
| Baseline 10K samples (1-NFE Euler) | ~8–17 minutes |
| Framework 20 rounds × 500 samples × 2-NFE | ~16–33 minutes |
| InceptionV3 feature extraction (10K samples) | ~2–4 minutes |
| FID computation (covariance + sqrtm) | ~1 s |

### Total budget

| Configuration | Wall-clock |
|---|---|
| **Smoke** (`--n-samples 1000 --n-rounds 5`) | ~10 min |
| **Development** (`--n-samples 5000 --n-rounds 20`) | ~3 hours |
| **Paper-grade** (`--n-samples 10000 --n-rounds 20`) | ~6–10 hours |
| **FID-50K paper-grade** (`--n-samples 50000 --n-rounds 20`) | ~2–3 days |

The default `--n-samples 10000` matches the 2D experiment's per-row sample
count and gives a publishable FID with reasonable variance.

---

## §6. Failure modes

| # | Failure | Severity | Mitigation |
|---|---------|----------|------------|
| 1 | **Weights download fails** (HF rate limit / firewall) | Medium | Try Option B (Google Drive) or Option C (self-train). Cache locally in `data/`; subsequent runs use `--checkpoint data/...pth`. |
| 2 | **Adapter fails with `FileNotFoundError`** | Low | The `data/rectified_flow_cifar10.pth` is missing; rerun Step 1. |
| 3 | **Baseline FID > 2.32** (>5% above paper 2.21) | Medium | Verify the UNet topology in `_build_torch_unet_ddpmpp` matches the paper (channel counts, attention, time embedding). Try the secondary weights URL (Option B). If still > 2.32, report honestly in `docs/ABLATION.md` — this is a baseline reproduction failure, not a framework failure. |
| 4 | **Baseline FID < 1.5** (suspiciously good) | Low | Likely a weights leak: InceptionV3 features for CIFAR-10 train overlap with the generated samples more than expected. Re-compute FID with the official CIFAR-10 **test set** features (not train) to disambiguate. |
| 5 | **Framework FID > baseline FID + 10%** (regression) | High | Investigate the merge operator: is `merged_beta` saturating? Is the scheduler's `n_cap` too high? Try `--n-rounds 5` to bisect the regression. Report honestly in `docs/ABLATION.md` — do not hide a regression. |
| 6 | **`InceptionV3 weights` download blocked** (corporate firewall) | Low | Pre-download: `curl -L https://github.com/mseitzer/pytorch-fid/releases/download/fid_weights/pt_inception-2015-12-05-6726825d.pth -o ~/.cache/torch/hub/checkpoints/pt_inception-2015-12-05-6726825d.pth` |
| 7 | **`torch` not installed** | High | Install with `pip install torch torchvision pytorch-fid`. The script auto-skips when torch is missing but the CIFAR experiment is then non-functional. |
| 8 | **`pytorch-fid` InceptionV3 returns NaN** | Low | Add 1e-6 offset to covariance matrices (`compute_mnist_fid.py` line 49 already does this; the CIFAR FID uses the same trick). |
| 9 | **CPU memory blow-up during FID-10K** | Low | Each sample is `(3, 32, 32)` float32 = 12 KB; 10K samples × 12 KB = 120 MB. InceptionV3 forward at batch 32 ≈ 250 MB. Total ≈ 400 MB peak; fits comfortably in 4-8 GB CI. |
| 10 | **`state_shape` mismatch with runner's forward-noise allocation** | Low | `F14` in `runner.py:774-783` reads `getattr(self._adapter, "state_shape", (2,))`. The adapter advertises `state_shape=(3, 32, 32)` as a class attribute; verified in `tests/test_adapters/test_rectified_flow_cifar.py::test_state_shape_advertised_matches_runner`. |
| 11 | **Byte-determinism breaks under torch** | Medium | The adapter forces `eval()` + `torch.no_grad()` in `_load_torch_unet`. CPU torch backward is non-deterministic; we don't backward. Use `--device cpu` for guaranteed reproducibility; `--device cuda` is fast but introduces minor non-determinism (acceptable for paper reporting). |
| 12 | **Framework loops forever on a sample** | Low | The adapter's `_native_states` is LRU-bounded at `RF_CIFAR_NATIVE_STATES_MAXSIZE=8`; the runner's per-round budget is 600 s. |

---

## §7. Where to save outputs

By convention, all experiment outputs land under `data/rf_cifar_out/` (or
whatever the user passes to `--output-dir`). The script's write paths:

| Path | Contents |
|---|---|
| `<output-dir>/baseline_samples.npz` | 10K generated samples from 2-NFE Euler baseline. |
| `<output-dir>/cosine_samples.npz` | 10K samples from `CosineAnnealScheduler` round 19 (last round). |
| `<output-dir>/codimension_samples.npz` | 10K samples from `CodimensionSheetScheduler` round 19. |
| `<output-dir>/evidence_samples.npz` | 10K samples from `EvidenceDrivenScheduler` round 19. |
| `<output-dir>/freetraj_samples.npz` | 10K samples from `FreeTrajScheduler` round 19. |
| `<output-dir>/comparison.md` | The headline comparison table (template in §4). |
| `<output-dir>/per_round_metrics.csv` | Per-round `selection_ratio`, `n_cap`, `beta` for each scheduler. |
| `<output-dir>/cifar10_test_ref.npz` | (Only when `--build-ref` is used) 10K CIFAR-10 test images in `[-1, 1]`. |

**Disk budget**: 5 × 10K × (3 × 32 × 32 × 4 bytes) ≈ **600 MB** for samples
(fits on any modern SSD); `cifar10_test_ref.npz` adds **~120 MB**; the rest
is metadata (CSV + markdown).

**Don't commit the `.npz` files to git** — they're regenerable from the
checkpoint. Add `data/rf_cifar_out/` and `data/cifar10_test_ref.npz` to
`.gitignore` if not already present.

---

## 10-line summary

- **Goal**: prove FlowA's framework multi-round preserves or improves on the
  published Rectified Flow CIFAR-10 FID 2.21 (≤ 2.43 = parity, ≤ 2.10 = win).
- **Preconditions**: pre-trained `state_dict` (.pth/.safetensors) +
  Python 3.12 + torch + torchvision + pytorch-fid in `.venv`; `flowa_fid_env`
  pre-built at `C:/Users/31472/AppData/Local/Temp/flowa_fid_env`.
- **Script**: `tools/run_sota_cifar_experiment.py` (~330 LOC) handles CLI,
  baseline, four schedulers, per-scheduler FID, and `comparison.md` emission.
- **Wall-clock** (CPU, default config): ~6–10 hours total; ~10 minutes for
  smoke pass.
- **Schedulers**: CosineAnneal, CodimensionSheet, EvidenceDriven, FreeTraj
  (matching the 2D experiment and the general SOTA protocol).
- **Output**: `<output-dir>/comparison.md` (5-row FID table) +
  per-scheduler `.npz` + per-round CSV; FID-50K publishable target.
- **Failure modes**: weights download, baseline FID > 2.32, framework
  regression > 10% — all have explicit mitigations (§6).
- **Biggest risk**: baseline reproduction divergence (UNet topology mismatch)
  — `state_dict` must match `_build_torch_unet_ddpmpp`'s constructor exactly.
- **Paper integration**: feeds `docs/paper-plan.md` §4.3 + `docs/ABLATION.md`
  §4.3 (the real-image load-bearing row of the empirical claims table).
- **Companion files**: short checklist at
  `docs/r4-survey/12-cifar-experiment-instructions.md` for the user.
