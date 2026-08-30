# CIFAR-10 Rectified Flow — User Checklist (1-page)

**Date:** 2026-08-30
**Companion design doc:** `docs/r4-survey/11-cifar-experiment-plan.md`
**Script:** `tools/run_sota_cifar_experiment.py`

A short, copy-pasteable checklist for running the CIFAR-10 Rectified Flow
experiment on your own machine. The full design + FID methodology + failure
modes are in the companion design doc.

---

## §1. One-time setup (do once per machine)

```bash
# 1. Install torch + torchvision + pytorch-fid into the framework venv.
.venv/Scripts/python.exe -m pip install torch torchvision pytorch-fid scipy

# 2. (Optional) Confirm the pre-built flowa_fid_env is still alive.
ls C:/Users/31472/AppData/Local/Temp/flowa_fid_env/Scripts/python.exe
ls C:/Users/31472/AppData/Local/Temp/flowa_fid_env/compute_mnist_fid.py
```

If the `flowa_fid_env` is missing, recreate it:

```bash
python -m venv C:/Users/31472/AppData/Local/Temp/flowa_fid_env
C:/Users/31472/AppData/Local/Temp/flowa_fid_env/Scripts/pip install \
    torch==2.4.1+cpu torchvision==0.19.1 pytorch-fid==0.3.0 scipy
```

---

## §2. Get the weights (3 options)

### Option A — HuggingFace mirror (recommended)

```bash
mkdir -p data
curl -L \
    "https://huggingface.co/gnobitab/RectifiedFlow/resolve/main/cifar10_reflow_ckpt.pth" \
    -o data/rectified_flow_cifar10.pth
```

### Option B — Google Drive (manual download)

1. Open `https://github.com/gnobitab/RectifiedFlow#checkpoints` in a browser.
2. Click the CIFAR-10 reflow Drive link; accept the MIT license.
3. Save the file as `data/rectified_flow_cifar10.pth`.

### Option C — Self-train (no external dependency)

Use a self-training recipe (e.g. `tools/train_rectified_flow_cifar.py`,
out of scope for this runbook) and save the `state_dict` as
`data/rectified_flow_cifar10.pth`. The adapter expects the DDPM++ UNet
topology from `adaptive_reflow/adapters/rectified_flow_cifar.py`
(`_build_torch_unet_ddpmpp`).

---

## §3. Smoke-test the adapter (30 seconds)

```bash
.venv/Scripts/python.exe -c "
from pathlib import Path
import numpy as np
from adaptive_reflow.adapters.rectified_flow_cifar import default_rectified_flow_cifar_adapter

adapter = default_rectified_flow_cifar_adapter(
    weights_path=Path('data/rectified_flow_cifar10.pth'),
)
caps = adapter.capabilities()
print('state_shape:', caps.state_shape)
assert caps.state_shape == (3, 32, 32)
samples = adapter.batched_inference(n_samples=4, num_steps=2, seed=0)
print('samples:', samples.shape, 'range', float(samples.min()), float(samples.max()))
assert samples.shape == (4, 3, 32, 32)
assert np.isfinite(samples).all()
print('smoke OK')
"
```

Expected output ends with `smoke OK`. If `state_shape` is wrong, the loaded
weights don't match the adapter's expected DDPM++ UNet topology.

---

## §4. Build the CIFAR-10 test reference (one-time, ~3 minutes)

```bash
.venv/Scripts/python.exe tools/run_sota_cifar_experiment.py \
    --build-ref data/cifar10_test_ref.npz --n-ref 10000
```

Downloads CIFAR-10 test set via torchvision (~170 MB), normalises to
`[-1, 1]`, writes 10K images to `data/cifar10_test_ref.npz` (~120 MB).

---

## §5. Run the experiment

### Quick smoke (10 minutes)

```bash
.venv/Scripts/python.exe tools/run_sota_cifar_experiment.py \
    --quick
```

Uses 200 baseline samples × 5 rounds × 50 framework samples. Verifies the
full pipeline end-to-end without computing FID.

### Paper-grade (6-10 hours, CPU)

```bash
.venv/Scripts/python.exe tools/run_sota_cifar_experiment.py \
    --checkpoint data/rectified_flow_cifar10.pth \
    --output-dir data/rf_cifar_out \
    --ref-npz data/cifar10_test_ref.npz \
    --n-samples 10000 \
    --n-rounds 20 \
    --framework-samples 500 \
    --device cpu
```

**Skip FID** (useful for CI / quick runs without the reference):

```bash
.venv/Scripts/python.exe tools/run_sota_cifar_experiment.py \
    --output-dir data/rf_cifar_out \
    --ref-npz data/cifar10_test_ref.npz.MISSING \
    --n-samples 10000 --n-rounds 20 --framework-samples 500
```

---

## §6. Read the results

```bash
cat data/rf_cifar_out/comparison.md
```

**Expected output table** (numbers filled in by your run):

| Method | FID | Δ vs baseline | % change | sel_ratio[r=19] | wall-clock (s) |
|---|---:|---:|---:|---:|---:|
| baseline (2-NFE Euler) | 2.21 | — | — | 0.81 | <Xs> |
| CosineAnnealScheduler | x.xx | +x.xx | +x.x% | 0.85 | <Xs> |
| CodimensionSheetScheduler | x.xx | +x.xx | +x.x% | 0.87 | <Xs> |
| EvidenceDrivenScheduler | x.xx | -x.xx | -x.x% | ≥ 0.95 | <Xs> |
| FreeTrajScheduler | x.xx | +x.xx | +x.x% | 0.83 | <Xs> |

**Reading the table:**

- Negative Δ vs baseline = framework wins (lower FID is better).
- EvidenceDrivenScheduler's `sel_ratio[r=19]` should be ≥ 0.95; the other
  three plateau around 0.81–0.88.
- A regression > +10% must be reported honestly; check failure modes in
  `docs/r4-survey/11-cifar-experiment-plan.md` §6.

---

## §7. What to send back to me

After running, please report:

1. **The `comparison.md` table** (copy-paste from
   `data/rf_cifar_out/comparison.md`).
2. **The baseline FID number** (e.g. `baseline FID = 2.24`).
3. **Wall-clock per scheduler** (from the comparison table).
4. **The output of `summary.json`** (one-line headline from `data/rf_cifar_out/summary.json`).
5. **Any failure mode encountered** (FID > 2.32, regression > 10%, download
   failure, NaN samples, etc.) — quote the relevant error line from stdout
   or the FID row.
6. **(Optional) A 1-paragraph honest assessment** of whether the framework
   beat the baseline (e.g. "EvidenceDriven reduced FID from 2.21 to 2.13,
   a 3.6% improvement; CosineAnneal was within +2.7%; both within the
   ±10% parity band — claim holds").

If the framework regressed by > 10%, please report that honestly so I can
investigate the merge-operator / scheduler tuning.

---

## §8. Output files (under `data/rf_cifar_out/`)

| Path | Contents |
|---|---|
| `baseline_samples.npz` | 10K baseline images (paper's 2-NFE Euler). |
| `cosineanneal_samples.npz` | 500 framework samples (round 19, cosine scheduler). |
| `codimensionsheet_samples.npz` | 500 framework samples (codimension scheduler). |
| `evidencedriven_samples.npz` | 500 framework samples (evidence-driven scheduler). |
| `freetraj_samples.npz` | 500 framework samples (free-traj scheduler). |
| `comparison.md` | The 5-row FID table (§6). |
| `per_round_metrics.csv` | Per-round `n_cap` / `beta` / `selection_ratio` traces. |
| `summary.json` | Machine-readable headline. |

**Don't commit the `.npz` files to git** — they're regenerable from the
checkpoint. Add `data/rf_cifar_out/` and `data/cifar10_test_ref.npz` to
`.gitignore` if not already present.
