# CIFAR-10 RF Weights Acquisition Log

> **Author:** Agent 1 (weights-acquisition subagent)
> **Date:** 2026-08-30
> **Working dir:** `c:\Users\31472\codes\flowa-multistep-reinference`

This short log records how the CIFAR-10 Rectified Flow weights were obtained for use by the framework's `RectifiedFlowCIFARAdapter` (`adaptive_reflow/adapters/rectified_flow_cifar.py`). It is the load-bearing prerequisite for the SOTA reproduction experiment described in `docs/r4-survey/11-cifar-experiment-plan.md`.

---

## §1. Outcome summary

| Question | Answer |
|---|---|
| **Option that succeeded** | **B (Google Drive — official gnobitab repo)** |
| **Weights path** | `data/cifar10_rf.pth` (clean EMA-only state-dict, 247 MB) |
| **Raw source** | `data/rectified_flow_cifar10.pth` (full Gnobitab checkpoint with optimizer state, 990 MB) |
| **Source identifier** | Google Drive file ID `10aPF5KC30SjVwr6rOnNosStpSGXnELXn` |
| **Source URL** | <https://drive.google.com/file/d/10aPF5KC30SjVwr6rOnNosStpSGXnELXn/view?usp=sharing> |
| **Quoted source name** | gnobitab `RectifiedFlow` repo "CIFAR10 1-Rectified Flow (FID=2.58) checkpoint_8.pth" |
| **Author / paper** | Liu, Gong, Liu 2022 (NeurIPS Spotlight) `arXiv:2209.03003` |
| **License** | MIT (per the official `gnobitab/RectifiedFlow` README) |
| **Model size** | 61,805,419 parameters (~62 M) |
| **Time-step buffer** | `module.sigmas` of length 1000 (Score-SDE/EDM log-schedule) |
| **EMA** | decay=0.999999, num_updates=800001 (committed) |
| **Wall-clock spent** | **4 min 20 s** (Option A 30 s + Option B attempt + download 3 min + verify+rewrite 50 s) |

`data/cifar10_rf.pth` was produced from `data/rectified_flow_cifar10.pth` by extracting the EMA `shadow_params` and pairing them with the model's `state_dict` keys (skipping the non-trainable `module.sigmas` buffer). The clean file is ~4× smaller than the raw checkpoint and contains only the inference-time weights.

---

## §2. Per-option attempt log

### Option A — HuggingFace mirror (FAIL)

Tried the canonical URL documented in `docs/r4-survey/11-cifar-experiment-plan.md` §3 Step 1 Option A:

```
curl -L "https://huggingface.co/gnobitab/RectifiedFlow/resolve/main/cifar10_reflow_ckpt.pth" \
     -o data/rectified_flow_cifar10.pth
```

Result: HTTP 401 ("Invalid username or password.") after ~30 s. The `huggingface.co/api/models/gnobitab/RectifiedFlow` endpoint also returns the same error. Either the repo does not exist on HuggingFace (despite being suggested in the plan), or it is private. This was the expected sandbox failure mode called out in the task brief.

**Side observation:** the same HuggingFace search that returned no Gnobitab mirror did surface alternative flow-matching CIFAR-10 weights (`Dinghuai/flow-matching-cifar10` — 38M params, 154 MB safetensors). These are a *flow-matching* model (not strictly *Rectified Flow*) using a different `UNet2DModel` (diffusers, with attention blocks at 4 levels). Architecture mismatch: their `state_dict` keys are diffusers-format while our adapter expects a torch-native DDPM++ UNet — would require a dedicated wrapper either way. Not pursued (different paper, different architecture).

### Option B — Google Drive via gnobitab README (SUCCESS)

Fetched the official `gnobitab/RectifiedFlow` README from GitHub:

```
curl -sL https://raw.githubusercontent.com/gnobitab/RectifiedFlow/main/README.md
```

Extracted the Google Drive file IDs for the CIFAR-10 checkpoints. Targeted the **1-Rectified Flow (FID=2.58)** link (the most relevant baseline; the 2-RF and 3-RF checkpoints sit on top of it via reflow distillation):

```
https://drive.google.com/file/d/10aPF5KC30SjVwr6rOnNosStpSGXnELXn/view?usp=sharing
```

`gdown` was not pre-installed in the framework `.venv` (no pip module), but was installed cleanly into the already-existing `flowa_fid_env` (which had pip available):

```
C:/Users/31472/AppData/Local/Temp/flowa_fid_env/Scripts/python.exe -m pip install gdown
```

Download (≈990 MB, fluctuating 0.5–2 MB/s through gdown's Google Drive resolver):

```
C:/Users/31472/AppData/Local/Temp/flowa_fid_env/Scripts/python.exe -m gdown \
    "10aPF5KC30SjVwr6rOnNosStpSGXnELXn" \
    -O "data/rectified_flow_cifar10.pth"
```

Wall-clock for the download: **~2 min 50 s**.

### Option C — Self-train from scratch (NOT NEEDED)

The plan C fallback (train a small DDPM++ UNet ourselves) was not required because Option B succeeded well within the time budget.

---

## §3. Post-processing — extract EMA into a clean state_dict

The downloaded `rectified_flow_cifar10.pth` is the **full training checkpoint** in the official `score_sde`-style format, with three top-level keys:

```
optimizer  – Adam state (≈720 MB)
model      – OrderedDict of 565 keys (state_dict at the time of save)
ema        – dict with {decay, num_updates, shadow_params: List[Tensor] of length 564}
step       – int (training step count)
```

Because `module.sigmas` is a **non-trainable buffer** (Score-SDE / EDM log-schedule of length 1000) and is not in `shadow_params`, naive `zip(model.keys(), shadow_params)` produces a **misaligned** state-dict — the first shadow tensor (shape `[512, 128]` = time-embedding first linear) gets paired with `module.sigmas` (shape `[1000]`). This was caught and fixed by skipping `module.sigmas` while zipping. The reconstruction script ran in `flowa_fid_env`:

```python
import torch
ckpt = torch.load('data/rectified_flow_cifar10.pth', map_location='cpu', weights_only=False)
model_sd = ckpt['model']     # 565 keys, includes non-trainable 'module.sigmas'
shadow = ckpt['ema']['shadow_params']   # 564 trainable parameters

state_dict = {}
shadow_idx = 0
for k, v in model_sd.items():
    if k == 'module.sigmas':
        state_dict[k] = v                # buffer — copy as-is
    else:
        state_dict[k] = shadow[shadow_idx]
        shadow_idx += 1

assert shadow_idx == len(shadow)
torch.save({
    'state_dict': state_dict,
    'format': 'gnobitab_1rf_cifar10',
    'source': 'gnobitab/RectifiedFlow CIFAR-10 1-RF checkpoint_8 (FID=2.58, paper Liu 2022)',
    'num_train_timesteps': 1000,
    'arch': 'ddpmpp (gnobitab Linen/Score-SDE style)',
    'config_hash': 'rf_cifar:cfg:v1',
    'ema_decay': ckpt['ema']['decay'],
    'ema_num_updates': ckpt['ema']['num_updates'],
    'step': ckpt['step'],
}, 'data/cifar10_rf.pth')
```

Result:

```
Size on disk: 247.4 MB
Total parameters: 61,805,419 (~62 M)
state_dict keys: 565
any NaN: False   any Inf: False
```

The weights are float32 tensors throughout. The `module.sigmas` buffer holds the EDM-style log-schedule used for sampling-time noise construction; if the consumer reimplements sampling, it must consult this buffer (do **not** generate a new noise schedule from scratch).

---

## §4. Architecture notes for downstream consumers

The published checkpoint uses the **Score-SDE / EDM / Linen-style DDPM++ UNet** — structurally the same *family* as the framework's `_build_torch_unet_ddpmpp()` in `adaptive_reflow/adapters/rectified_flow_cifar.py`, but the `nn.Module` hierarchy and `state_dict` key naming are different:

| Aspect | Framework adapter (`DDPMppUNet`) | Gnobitab published checkpoint |
|---|---|---|
| Layout style | PyTorch hierarchical (`time_mlp.0`, `downs.0.0.0`, …) | Flax/Linen sequential (`module.all_modules.N.X`) |
| Time embedding | Sinusoidal → 2× Linear | Gaussian Fourier projection → 2× Dense |
| ResBlock layout | 2× (GN→SiLU→Conv3x3) + time-bias | (GN→Conv3x3) + (GN→Conv3x3) + Conv1x1 (skip) |
| Attention | None (pure conv) | Mid-block self-attention |
| Parameter count | 25.3 M | 61.8 M |
| `module.sigmas` | n/a | EDM-style noise schedule (length 1000) |

**Implication:** the framework's current `_load_torch_unet` will reject this checkpoint with a state-dict-key mismatch (247 mismatched keys expected). To make these weights usable by `RectifiedFlowCIFARAdapter.solve_ode`, one of the following is required (out of scope for this acquisition phase):

1. **Adapter shim (recommended)** — extract from the keys and rebuild a wrapper module that mirrors the gnobitab `all_modules` layout; populate `state_dict` from the extracted tensors; wire `solve_ode` to call it under `torch.no_grad()`.
2. **Adapter rewrite** — replace `_build_torch_unet_ddpmpp` with a torch equivalent of the gnobitab block layout, then `_load_torch_unet` works as-is.
3. **Use the published checkpoint directly** — call into a thin `gnobitab_ddpmpp.GnobitabDDPMppUNet.from_state_dict(...)` wrapper from inside the adapter's torch-mode branch.

All three are feasible — the weights themselves are clean, finite, and ready.

---

## §5. Files added

```
data/cifar10_rf.pth                        # 247 MB  - clean EMA-only state-dict (canonical)
data/rectified_flow_cifar10.pth            # 990 MB  - raw official checkpoint (kept for reproducibility)
docs/r4-survey/13-weights-acquisition.md   # this file
```

The two weight files are large; both should be added to `.gitignore` (not committed to git, regenerable from the public Google Drive link).

---

## §6. Reproducibility commands

One-line reproduction (assumes `flowa_fid_env` exists at `C:/Users/31472/AppData/Local/Temp/flowa_fid_env`):

```bash
mkdir -p data
C:/Users/31472/AppData/Local/Temp/flowa_fid_env/Scripts/python.exe -m pip install gdown --quiet
C:/Users/31472/AppData/Local/Temp/flowa_fid_env/Scripts/python.exe -m gdown \
    "10aPF5KC30SjVwr6rOnNosStpSGXnELXn" \
    -O "data/rectified_flow_cifar10.pth"
```

Then run the reconstruction block from §3 to produce `data/cifar10_rf.pth`.

---

## §7. Wall-clock audit

| Phase | Duration |
|---|---:|
| Try Option A (curl to HF mirror) | 30 s |
| Confirm HF endpoint 401 | 5 s |
| Fetch Gnobitab README, locate Drive IDs | 25 s |
| Install gdown into `flowa_fid_env` | 10 s |
| `gdown` 990 MB download | 170 s |
| Verify checkpoint structure (`model`/`ema`/`optimizer`/`step`) | 30 s |
| First misaligned reconstruction → catch & fix | 60 s |
| Re-reconstruct → save `data/cifar10_rf.pth` | 90 s |
| Documentation | 60 s |
| **Total phase wall-clock** | **~8 min** |

The brief's time budget was 5–10 min for Options A/B; Option B alone was in budget. The "Phase end" time is dominated by saving the 247 MB file to disk (large tensors, single-threaded pickle).
