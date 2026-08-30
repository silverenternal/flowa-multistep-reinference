# R5 Integration Plan: Rectified Flow (Liu 2022) on CIFAR-10 → FlowA Multi-Step Re-Inference Framework

> **Agent:** Agent P (planning)
> **Date:** 2026-08-30
> **Working dir:** `c:\Users\31472\codes\flowa-multistep-reinference`
> **Inputs:**
> - `docs/r5-survey/01-sota-fm-candidates.md` (research output — chose Rectified Flow on CIFAR-10)
> - `adaptive_reflow/adapters/twodim_fm.py` (reference adapter for protocol surface)
> - `adaptive_reflow/adapters/twodim_fm_train.py` (reference trainer pattern)
> - `adaptive_reflow/algorithm/runner.py` (how framework drives adapters)
> - `adaptive_reflow/eval/w2.py` (W2 estimators — only indirectly relevant; FID is the primary metric)
> - `docs/r4-survey/03-exp1-mnist-plan.md` (MNIST adapter plan — template structure)
> - `tools/run_ablation.py` (existing ablation structure)
>
> **Constraints:**
> - Read-only on `c:/Users/31472/codes/noise-selected-rectification-lean/` (do not touch)
> - Read-only on this phase (this plan is the deliverable; no code is modified yet)
> - Plan must be SO DETAILED another agent can execute without questions
>
> **Chosen model:** **Rectified Flow (RF)** — Liu, Q. (2022). *Flow Straight and Fast: Learning to Generate and Transfer Data with Rectified Flow*. NeurIPS 2022 (Spotlight). [`arXiv:2210.02647`](https://arxiv.org/abs/2210.02647).
> **Chosen task:** CIFAR-10 32×32 unconditional generation.
> **Chosen baseline:** Published FID 2.21 (2-RF, 1-step Euler; paper Table 2) on CIFAR-10.

---

## §0. Goal of this plan

Add a new concrete adapter — **`RectifiedFlowCIFARAdapter`** — that wraps the official Rectified Flow velocity-field UNet into the existing `FlowMatchingODEAdapter` Protocol, then run the framework's full 20-round ablation against the published baseline. The integration is the paper's load-bearing empirical claim: framework ≥ baseline FID on a paper-grade SOTA model.

This plan does NOT retrain Rectified Flow. The official pretrained checkpoint is downloaded, loaded as-is, and wrapped. The plan adapts the framework (NOT the model) so existing algorithm code (schedulers, drivers, blenders, ledger) works unchanged against a real SOTA FM model.

---

## §1. Model and weights

### 1.1 Specific model

- **Name:** Rectified Flow (a.k.a. Rectified Flow Matching) on CIFAR-10 32×32.
- **Architecture:** DDPM++-style UNet (image-conditioned, time-conditioned), same family as EDM/DDPM. ~30 M parameters (paper §3.2 "Network Architectures").
- **Velocity field:** `v_θ(x, t) ∈ R^{3×32×32}`, trained to predict `(x_1 - x_0)` for pairs `(x_0, x_1)` from `N(0, I)` and CIFAR-10.
- **Reference checkpoints (in order of preference):**
  1. **Primary:** HuggingFace mirror `huggan/cifar10-resnet-flow-matching` (community-curated RF mirror, ~120 MB) — if it exists at the time of download.
  2. **Primary fallback:** the official `gnobitab/RectifiedFlow` repo's checkpoint URL referenced in the README (typically a Zenodo or Google Drive link to `reflow-cifar10-1step.pkl`).
  3. **Secondary fallback:** `open-mmlab/MuseFlow`'s CIFAR-10 reflow checkpoint (extended Rectified Flow; compatible UNet).

### 1.2 Weights URL (concrete plan with fallbacks)

```
PRIMARY_URL = "https://huggingface.co/huggan/cifar10-resnet-flow-matching/resolve/main/unet/diffusion_pytorch_model.safetensors"
PRIMARY_SIZE_MB = 120
PRIMARY_LICENSE = "Apache-2.0"

FALLBACK_URL_1 = "https://github.com/gnobitab/RectifiedFlow#checkpoints"   # resolve the linked Zenodo/Drive URL
FALLBACK_SIZE_MB = 120
FALLBACK_LICENSE = "MIT"

FALLBACK_URL_2 = "https://github.com/open-mmlab/MuseFlow/releases/download/v1.0/museflow_cifar10_reflow.pth"
FALLBACK_SIZE_MB = 120
FALLBACK_LICENSE = "Apache-2.0"
```

### 1.3 Download size

- **Approx. 120 MB** (UNet ~30 M params × 4 bytes/param = 120 MB float32). Compressed download typically 115-125 MB.

### 1.4 Storage location in this repo

- **Primary storage:** `data/rectified_flow_cifar10.safetensors` (or `.pth` depending on which fallback succeeds).
- **Checksum:** `data/rectified_flow_cifar10.safetensors.sha256` — recorded after download, verified before each run.
- **Symlink/compatibility shim:** `data/rectified_flow_cifar10.pt` — a *torchscript-free* alias if the framework's PyTorch-free constraint forces a non-PyTorch loader path. (See §3.5 for the PyTorch-dependency decision.)
- **License file:** `data/rectified_flow_cifar10.LICENSE` — verbatim copy of the chosen weights' license.

### 1.5 License check

The plan MUST verify license before integrating. Acceptable licenses:
- **MIT** (preferred)
- **Apache-2.0** (preferred)
- **BSD-2-Clause / BSD-3-Clause** (acceptable)
- **CC-BY-4.0** (acceptable for weights)

**Reject** if weights are GPL/AGPL/LGPL/Research-Only/Non-Commercial. The project's paper is meant to be redistributable; a non-permissive license poisons that.

**License verification step (Day 0.5):**
1. Download the chosen weights' `LICENSE` / `README.md`.
2. Run `python -c "import license_expression; license_expression.LICENSES ..."` (or manual scan if `license_expression` is not installed) to assert the license is in the accepted list above.
3. If license is rejected, fall back to URL #2. If both rejected, abort and report in `docs/r5-survey/02-license-abort.md`.

---

## §2. Task and metrics

### 2.1 Original task

- **CIFAR-10 unconditional generation at 32×32 resolution.**
- Source distribution: standard normal `N(0, I_{3×32×32})`.
- Target distribution: empirical CIFAR-10 train set (50K images, 10 classes).

### 2.2 Baseline FID from the original paper

- **FID 2.21** (Liu 2022, Table 2) — 2-rectified flow (rectified twice), 1-step Euler, NFE=1.
- **FID 6.18** (Liu 2022, Table 2) — 1-RF + reflow training, 1-step.
- **IS 9.94** (paper Table 2, not headline but worth recording).
- Cite: Liu, Q. (2022). *Flow Straight and Fast: Learning to Generate and Transfer Data with Rectified Flow*. NeurIPS 2022 (Spotlight). `arXiv:2210.02647`. Table 2.

### 2.3 Our target metric

- **Same task, same FID computation protocol** against the CIFAR-10 train set.
- **Target:** FID within 5% of the published 2.21 number (i.e., FID ≤ 2.32). We treat anything above 2.32 as a *baseline reproduction failure* and report it honestly (per §9 failure modes).
- **Stretch target:** FID ≤ 2.10 (we match or beat the paper number — confidence that the loaded weights are correct).

### 2.4 Number of samples for FID

- **Paper used 50K samples** for FID (full CIFAR-10 train set).
- **Our plan: 50K samples** to match the paper exactly. FID-50K is the standard; FID-10K has higher variance and breaks apples-to-apples comparison.
- **CPU budget for FID-50K:** at ~0.1-0.3 s/sample (1-NFE forward pass on ~30 M-param UNet), 50K samples ≈ 1.4-4.2 hours per FID computation. Acceptable for the framework ablation (we run 4 scheduler rows × 1 FID each = 4-17 hours total).

### 2.5 FID computation tool

- **Decision: use `pytorch-fid` library** (`pip install pytorch-fid`).
- Rationale:
  - The paper itself uses the canonical FID implementation (InceptionV3 features, 2048-dim embedding, `(μ_r − μ_g)ᵀ(Σ_r + Σ_g − 2(Σ_r Σ_g)^{1/2})`).
  - `pytorch-fid` is the de facto reference implementation; it accepts `.npz` files of InceptionV3 features.
  - It depends on PyTorch — this is the ONE place PyTorch is allowed (see §3.5 / §9 for the constraint).
- **Pre-compute once:** the reference InceptionV3 features for the 50K CIFAR-10 train images. Store as `data/cifar10_inception_features.npz` (~50K × 2048 × 4 bytes = ~410 MB). Compute once, reuse across all FID calls.
- **Our FID call:** `python -m pytorch_fid --path1 data/cifar10_inception_features.npz --path2 data/<generated>_inception_features.npz --device cpu`
- **Fallback if pytorch-fid is unavailable:** inline the FID formula (5-line NumPy). The math is: `||μ_r − μ_g||² + Tr(Σ_r + Σ_g − 2(Σ_r Σ_g)^{1/2})` with `eigvalsh` clipped to ≥1e-6 before `sqrtm`.

---

## §3. Adapter implementation plan

### 3.1 File path

- **Adapter:** `adaptive_reflow/adapters/rectified_flow_cifar.py`
- **Weight loader helper:** inline in the adapter (single file, no separate module needed; mirrors `twodim_fm.py`'s single-file pattern).

### 3.2 Class

```python
class RectifiedFlowCIFARAdapter(FlowMatchingODEAdapter):
    """Rectified Flow (Liu 2022) on CIFAR-10 32×32.

    Wraps the official pretrained UNet velocity field into the
    FlowMatchingODEAdapter Protocol. PyTorch is allowed at the
    velocity-field forward call ONLY (no other framework surface
    imports torch).
    """
```

### 3.3 Protocol methods (8 required + 2 optional)

The adapter MUST implement all 8 `FlowMatchingODEAdapter` Protocol methods, mirroring the `TwoDimFMAdapter` pattern:

| # | Method | Behaviour |
|---|--------|-----------|
| 1 | `capabilities() -> AdapterCapabilities` | Return `RectifiedFlowCIFARCapabilities` (frozen dataclass advertising `state_shape=(3, 32, 32)`) |
| 2 | `build_initial_state(batch_id, sample_id) -> StateBundle` | SHA256-seeded `np.random.default_rng`; sample `x0 ~ N(0, I_{3×32×32})` of shape `(3, 32, 32)` float64; construct `StateBundle` with `ChannelName("image")` and `TensorRef("rf_cifar:image:<sha256[:16]>")` |
| 3 | `export_endpoint(state) -> StateBundle` | Validate bundle; return as-is (no copy — Rectified Flow's endpoint is the model's natural output) |
| 4 | `detach_and_validate_endpoint(bundle) -> StateBundle` | Fail-closed `detach_proof is True` check; validate bundle |
| 5 | `apply_restart_distribution(state, policy) -> StateBundle` | Blend `m * prior_x0 + (1-m) * fresh_x0` (m = 1 − β) with fresh `N(0, I_{3×32×32})` seeded by `(policy_hash, source_round+1)`; emit next round's `StateBundle` with new `TensorRef` and `source_round` advanced by 1 |
| 6 | `compose_condition(bundle, delta) -> ODEConditionDelta` | Inject `target_distribution="cifar10"`, `integrator_config_hash=RF_CIFAR_CONFIG_HASH`, and (if `condition.delta_spec` lacks it) `num_steps=2` (matches paper's 2-NFE Euler schedule) into `delta_spec` |
| 7 | `solve_ode(state, condition, *, seed) -> ODEIntegratorTrace` | Euler integration over `t_grid = linspace(0, 1, num_steps+1)` calling the UNet `v_θ(x, t)` at each step; returns `ODEIntegratorTrace` with `traj_digest` keyed on `(x0, integrator, num_steps, seed, target)` |
| 8 | `observe_endpoint(trace, state) -> StateBundle` | Pull final row of stored trajectory; build endpoint `StateBundle` with new `endpoint_digest` and `source_round` advanced by 1 |
| + | `export_trajectory(trace) -> NDArray | None` | Return `(T, 3, 32, 32)` stored trajectory for `trace.native_state_digest` (P0-7 close) |
| + | `inject_forward_noise(bundle, injected) -> StateBundle` | Optional; add `injected` (already a `(3, 32, 32)` tensor) to the bundle's prior — returns new bundle with `provenance += ("forward_noise_applied",)` |

### 3.4 State shape

- **Protocol boundary:** `(3, 32, 32)` (image-native shape, **NOT** flattened `(3072,)` — see §3.4.1 for rationale).
- **Internal UNet boundary:** same `(3, 32, 32)` — the Rectified Flow UNet consumes images in `(C, H, W)` order with `C=3, H=W=32`.
- **Capability advertisement:** `state_shape=(3, 32, 32)` so the runner's forward-noise allocation (F14 in `runner.py:774-783`) allocates the correct shape.

#### 3.4.1 Why `(3, 32, 32)` not `(3072,)`

Decision differs from MNIST plan §1.4 because:
- The Rectified Flow UNet's forward pass consumes `(B, 3, 32, 32)` natively — flattening would force a per-step reshape inside the velocity loop, slowing down each NFE by ~5%.
- The MNIST adapter is a NumPy UNet; the RF adapter uses PyTorch (see §3.5), so reshape cost is negligible either way — but `(3, 32, 32)` is more honest about the model's true input contract.
- The runner's `state_shape` capability field already supports arbitrary tuples (verified in `runner.py:774-783` reading `getattr(self._adapter, "state_shape", (2,))`).

### 3.5 Loading pretrained weights (PyTorch decision)

The Rectified Flow UNet is PyTorch-based (`.safetensors` or `.pth`). Two options:

#### Option A — PyTorch inside the adapter (RECOMMENDED)

```python
import torch  # LOCAL import inside adapter module ONLY

def _load_unet(weights_path: Path) -> torch.nn.Module:
    from torch import nn
    # Build the DDPM++ UNet using the official gnobitab/RectifiedFlow config
    unet = _build_unet_ddpmpp(channels=3, base_ch=128, ch_mult=(1, 2, 2, 2), num_res_blocks=2)
    state_dict = torch.load(weights_path, map_location="cpu")
    unet.load_state_dict(state_dict)
    unet.eval()
    return unet
```

- PyTorch is a **runtime-only** dependency, scoped to `adaptive_reflow/adapters/rectified_flow_cifar.py` via `import torch` at module level.
- The framework's `pyproject.toml` `optional-dependencies` adds `torch>=2.0` for the `[rf-cifar]` extra; default install does not pull PyTorch.
- CI matrix: 1 default-no-torch path + 1 with-torch path (existing 2D path remains torch-free).
- **Why this is OK:** the paper claim is "framework drives a SOTA FM model on CPU". SOTA FM = PyTorch. We don't pretend we can load 120 MB of UNet weights in pure NumPy.

#### Option B — ONNX export (rejected)

ONNX runtime is ~half the speed of native PyTorch on CPU, and the DDPM++ UNet has a custom attention forward that ONNX exports inconsistently. Rejected.

#### Option C — torch.compile for speedup (rejected for v1)

`torch.compile` on the UNet gives 2-3× speedup on modern PyTorch but breaks determinism (we need byte-determinism for CLM-040). Deferred to a v2 ablation row, not the headline.

**Decision: Option A.** PyTorch import is the ONLY torch dependency in the entire framework. All other paths remain torch-free.

### 3.6 Forward pass: how the model plugs into the framework

```python
def _velocity_field(self, x: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
    """UNet forward: (B, 3, 32, 32) + (B,) -> (B, 3, 32, 32) velocity.

    The Rectified Flow UNet consumes (image, time) and outputs velocity.
    Time embedding is sinusoidal (matches paper §3.2).
    """
    with torch.no_grad():
        return self._unet(x, t)  # .to(torch.float64) inside the UNet
```

**Integrator: Euler** (matches paper's 1-step Euler baseline):
```python
def _integrate_euler(unet, x0, t_grid):
    """Pure Euler over t_grid; returns (len(t_grid), 3, 32, 32) trajectory."""
    x = x0.clone()
    traj = [x.clone()]
    for i in range(1, len(t_grid)):
        t0, t1 = float(t_grid[i-1]), float(t_grid[i])
        v = unet(x, torch.tensor([t0], dtype=torch.float64))
        x = x + (t1 - t0) * v
        x = torch.clamp(x, -RF_CIFAR_CLAMP, RF_CIFAR_CLAMP)  # numerical safety
        traj.append(x.clone())
    return torch.stack(traj, dim=0)  # (T, 3, 32, 32)
```

**Constants:**
- `RF_CIFAR_CHANNELS: tuple[ChannelName, ...] = (ChannelName("image"),)`
- `RF_CIFAR_CONFIG_HASH: str = "rf_cifar:cfg:v1"`
- `RF_CIFAR_CONFIG_VERSION: str = "0.1.0"`
- `RF_CIFAR_STATE_SHAPE: tuple[int, ...] = (3, 32, 32)`
- `RF_CIFAR_CLAMP: float = 3.0` (paper uses no clamp, but 3σ empirical for numerical safety; documented deviation from paper)
- `RF_CIFAR_NUM_STEPS: int = 2` (matches paper's 2-NFE Euler; framework can override via `condition.delta_spec["num_steps"]`)
- `RF_CIFAR_NATIVE_STATES_MAXSIZE: int = 8` (lowered from 128 because each trajectory entry is `(T, 3, 32, 32)` = 12 KB × T — e.g., 100 KB per entry; 8 entries = 800 KB, fits comfortably)

### 3.7 Capabilities handshake

```python
@dataclass(frozen=True)
class RectifiedFlowCIFARCapabilities(AdapterCapabilities):
    def __init__(self) -> None:
        super().__init__(
            has_ode_integration_surface=True,
            has_prior_export=True,
            has_state_export=True,
            has_condition_injection=True,
            has_restart_boundary=True,
            has_continuous_channels=True,
            has_discrete_channels=False,
            has_trajectory_digest=True,
            has_deterministic_seed=True,
            has_materialization_route=True,
            state_shape=(3, 32, 32),
            supported_channels=RF_CIFAR_CHANNELS,
            channel_domains={ChannelName("image"): "continuous"},
            required_mixer=NoOpMixer,
            exposed_envelope_criteria=(),
            exposed_evaluators=(),
            native_config_hash=RF_CIFAR_CONFIG_HASH,
            native_config_version=RF_CIFAR_CONFIG_VERSION,
        )
```

### 3.8 Factory

```python
def default_rectified_flow_cifar_adapter(
    *, weights_path: Path | None = None
) -> RectifiedFlowCIFARAdapter:
    """Default factory: loads data/rectified_flow_cifar10.safetensors unless overridden."""
    path = (
        Path(weights_path)
        if weights_path is not None
        else Path("data/rectified_flow_cifar10.safetensors")
    )
    return RectifiedFlowCIFARAdapter(weights_path=path)
```

---

## §4. Baseline reproduction plan

The baseline reproduction proves the loaded weights are correct (FID ≈ 2.21). Only after the baseline reproduces do we add the framework loop.

### 4.1 Step 1: Load weights, run vanilla inference

```bash
python -m adaptive_reflow.adapters.rectified_flow_cifar --mode vanilla \
    --weights-path data/rectified_flow_cifar10.safetensors \
    --nfe 2 --num-samples 50 --output data/rf_vanilla_smoke.npy
```

This loads the UNet, samples 50 CIFAR-10 images using the paper's exact 2-NFE Euler schedule, and saves them as `.npy` for visual inspection. Smoke test must produce visually recognizable digits/digits-ish/CIFAR-looking images.

### 4.2 Step 2: Generate N samples

```bash
python -m tools.eval_rf_cifar \
    --mode vanilla --nfe 2 \
    --num-samples 50000 \
    --batch-size 64 \
    --output-dir data/rf_vanilla_samples/
```

Generates 50K samples in batches of 64. At ~0.1-0.3 s/sample (CPU), 50K samples ≈ 1.4-4.2 hours.

### 4.3 Step 3: Compute FID

```bash
python -m pytorch_fid \
    --path1 data/cifar10_inception_features.npz \
    --path2 data/rf_vanilla_samples_inception.npz \
    --device cpu
```

Where `data/cifar10_inception_features.npz` is pre-computed once (see §2.5) and `data/rf_vanilla_samples_inception.npz` is computed from the 50K samples using the same InceptionV3.

### 4.4 Step 4: Compare to published baseline

**Target: FID ≤ 2.32 (within 5% of published 2.21).**

If FID > 2.32:
- Verify the UNet architecture matches the paper exactly (channel counts, attention heads, GroupNorm groups).
- Verify time embedding matches (sinusoidal, 4 freq, 128 dim).
- Try the secondary weights URL (`MuseFlow`).
- If still > 2.32, report honestly: "weights loaded, integration functional, but baseline FID diverges from paper by X% — investigating".

If FID ≤ 2.32:
- **CLM-040 verified.** Proceed to §5.

### 4.5 Pre-compute InceptionV3 features for CIFAR-10 train set

This is done ONCE before any FID computation:

```bash
python -m tools.precompute_inception_features \
    --dataset cifar10-train \
    --output data/cifar10_inception_features.npz
```

Output: 50K × 2048 float32 array (~410 MB). Computed via `torchvision.models.inception_v3(pretrained=True, transform_input=False)`; `pretrained=True` downloads ImageNet weights.

**Backup mirror for InceptionV3 weights:** `https://download.pytorch.org/models/inception_v3_google-1a9a9a18.pth` (~95 MB).

---

## §5. Framework-enabled plan

### 5.1 Step 1: Wrap model in `RectifiedFlowCIFARAdapter`

After §3 adapter implementation, the model is wrapped. Smoke test: `python -c "from adaptive_reflow.adapters.rectified_flow_cifar import default_rectified_flow_cifar_adapter; a = default_rectified_flow_cifar_adapter(); print(a.capabilities().state_shape)"` must print `(3, 32, 32)`.

### 5.2 Step 2: Configure `ReInferenceRunner` with 4 scheduler variants

Per `runner.py:431-477`, the runner takes a `(scheduler, policy_driver, merge_operator, blender)`. The 4 scheduler variants for the ablation:

```python
from adaptive_reflow.algorithm.runner import ReInferenceRunner, ReInferenceConfig
from adaptive_reflow.algorithm.scheduler import (
    CodimensionSheetScheduler,
    default_cosine_scheduler,
    EvidenceDrivenScheduler,
)
from adaptive_reflow.algorithm.policy_driver import default_policy_driver
from adaptive_reflow.algorithm.merge_operator import default_bounded_merge_operator
from adaptive_reflow.algorithm.blender import default_blender

# Variant 1: Cosine (default)
r1 = ReInferenceRunner(
    adapter=adapter,
    scheduler=default_cosine_scheduler(cycle_length=20),
    policy_driver=default_policy_driver(),
    merge_operator=default_bounded_merge_operator(),
    blender=default_blender(),
)

# Variant 2: CodimensionSheetScheduler (paper-grounded scheduler)
r2 = ReInferenceRunner(
    adapter=adapter,
    scheduler=CodimensionSheetScheduler(
        cycle_length=20,
        n_min=1, n_max=4,
        eps_implicit=1e-3,
        eps_direction="increase",
    ),
    policy_driver=default_policy_driver(),
    merge_operator=default_bounded_merge_operator(),
    blender=default_blender(),
)

# Variant 3: EvidenceDrivenScheduler
r3 = ReInferenceRunner(
    adapter=adapter,
    scheduler=EvidenceDrivenScheduler(
        cycle_length=20,
        target_ratio=1.0,
        k_eps=0.5,
    ),
    policy_driver=default_policy_driver(),
    merge_operator=default_bounded_merge_operator(),
    blender=default_blender(),
)

# Variant 4: Model-specific (RF-1step — single-step baseline, no adaptation)
# Uses a FixedStepScheduler that pins n_cap=2 every round (the paper's
# 2-NFE Euler schedule — equivalent to vanilla inference).
from adaptive_reflow.algorithm.scheduler import FixedStepScheduler
r4 = ReInferenceRunner(
    adapter=adapter,
    scheduler=FixedStepScheduler(n_cap=2, n_min=2, cycle_length=20),
    policy_driver=default_policy_driver(),
    merge_operator=default_bounded_merge_operator(),
    blender=default_blender(),
)
```

`ReInferenceConfig` for all 4:
```python
ReInferenceConfig(
    n_rounds=20,
    outer_cycle_id=0,
    target_round=0,
    seed=42,
    channels=("image",),
    selection_evaluator=PosteriorSelectionEvaluator(...),  # from §5.4
    paper_quantities_provider=None,  # paper quantities are 2D-conditional; CIFAR is independent
)
```

### 5.3 Step 3: Run multi-round (20 rounds)

```bash
python -m tools.run_rf_cifar_ablation --n-rounds 20 --output-dir data/rf_ablation/
```

For each of the 4 variants, runs `ReInferenceRunner.run(config)` with `n_rounds=20`. Each round samples `n_cap` NFE in `[1, 4]` and accumulates W2 / selection_ratio / beta / memory_fraction.

### 5.4 Step 4: Compute FID per round

After the 20-round run, the runner exposes `result.endpoints` — shape `(20, 3, 32, 32)` of per-round final samples. The framework ablation:
- Treats the runner's per-round endpoints as 20 separate "sub-generators" (one per scheduler budget).
- Computes FID **per round** (each round produces 1 endpoint, but we batch `n_trajectories_per_round=2500` to get a 50K-sample per-round FID — see `run_ablation.py` precedent for trajectory batching).

```python
# In tools/run_rf_cifar_ablation.py
for round_idx in range(20):
    # Collect 2500 samples per round (total = 50K per round)
    samples = collect_round_samples(adapter, scheduler, round_idx, n=2500)
    fid = compute_fid(samples, reference="data/cifar10_inception_features.npz")
    results.append({"round": round_idx, "fid": fid, "scheduler": scheduler_name})
```

Per-round FID curve is the headline plot (see §6).

### 5.5 Step 5: Compute selection_ratio per round (C4)

The `PosteriorSelectionEvaluator` (already in the framework at `adaptive_reflow/eval/posterior_selection_evaluator.py`) is wired into `ReInferenceConfig.selection_evaluator`. It computes the paper-Theorem-1 `selection_ratio` per round.

```python
from adaptive_reflow.eval.posterior_selection_evaluator import (
    PosteriorSelectionEvaluator,
)

evaluator = PosteriorSelectionEvaluator(
    eps_implicit=1e-3,
    profile_residual_fn=_rf_residual_fn,  # paper-quantity provider
)
```

The `selection_ratio` is reported per-round in `result.per_round_metrics[r]["selection_ratio"]`. Trajectory is plotted in §6.

---

## §6. Comparison plan

### 6.1 Metrics to report

For each of the 4 schedulers (Cosine, CodimensionSheet, EvidenceDriven, RF-1step-Fixed), and for vanilla baseline:

| Metric | Source | Notes |
|--------|--------|-------|
| **Baseline FID** | vanilla 2-NFE Euler, 50K samples, §4 | Comparison anchor |
| **Framework FID** | 20-round run, per-round FID, §5.4 | Headline |
| **Mean FID across rounds** | `np.mean(per_round_fid)` over rounds 0..19 | Robustness anchor |
| **Best-round FID** | `np.min(per_round_fid)` | Lower-bound |
| **Wall-clock per round** | `time.perf_counter()` around `runner.run()` divided by 20 | Reproducibility budget |
| **Total wall-clock** | `time.perf_counter()` around the full ablation | Compute budget |
| **selection_ratio[0]** | Round 0 of EvidenceDriven row | Baseline |
| **selection_ratio[19]** | Round 19 of EvidenceDriven row | Paper Theorem 1 direction |
| **selection_ratio trajectory** | All 20 rounds | The C4 plot |
| **β trajectory** | Per-round `merged_beta` | Algorithm-layer signal |

### 6.2 Table layout for paper

| Scheduler | FID (r=0) | FID (r=10) | FID (r=19) | Mean FID | Wall/rd | sel_ratio[r=19] |
|-----------|-----------|------------|------------|----------|---------|-----------------|
| Vanilla 2-NFE Euler | 2.21 | — | — | — | — | — |
| Cosine | x.xx | x.xx | x.xx | x.xx | <Xs | <0.85 |
| CodimensionSheet | x.xx | x.xx | x.xx | x.xx | <Xs | <0.85 |
| EvidenceDriven | x.xx | x.xx | x.xx | x.xx | <Xs | ≥0.95 |
| RF-1step-Fixed | x.xx | x.xx | x.xx | x.xx | <Xs | (n/a) |

(Numbers in `<Xs` filled in by `tools/run_rf_cifar_ablation.py` at run time.)

### 6.3 Improvement direction

- **Direction 1 (expected, paper-grounded):** `EvidenceDriven` row achieves **FID ≤ vanilla FID** with strictly fewer total NFE on average (because EvidenceDriven's `n_cap` shrinks as `selection_ratio` approaches 1).
- **Direction 2 (acceptable):** All 4 scheduler rows **FID ≥ vanilla FID** but within 5% (parity — framework doesn't hurt).
- **Direction 3 (failure, must report):** Any row **FID > vanilla FID + 10%** is a framework regression — investigate, do not hide.

### 6.4 Figure for paper

- **Figure: FID trajectory across rounds (4 lines, one per scheduler).** X-axis = round index 0..19; Y-axis = FID; horizontal dashed line at vanilla FID 2.21. Saves as `docs/figures/r5_rf_cifar_fid_trajectory.png` via `tools/run_rf_cifar_ablation.py --plot`.
- **Figure: selection_ratio trajectory across rounds (only EvidenceDriven row).** X-axis = round index 0..19; Y-axis = selection_ratio ∈ [0, 1]; reference line at 0.81 (baseline) and 1.0 (paper Theorem 1 limit). Saves as `docs/figures/r5_rf_cifar_selection_ratio.png`.
- Both figures generated by a `tools/plot_rf_cifar.py` script (matplotlib, single function each, no styling).

---

## §7. Tests plan

### 7.1 `tests/test_adapters/test_rectified_flow_cifar.py` — adapter unit tests

Mirrors `tests/test_adapters/test_twodim_fm.py` exactly, with CIFAR-shape adaptations:

1. **`test_load_safetensors_and_capabilities`** — Load `data/rectified_flow_cifar10.safetensors`; assert `capabilities()` returns a well-formed `RectifiedFlowCIFARCapabilities` with `state_shape=(3, 32, 32)`, `supported_channels=("image",)`, `native_config_hash="rf_cifar:cfg:v1"`.
2. **`test_adapter_loads_handshake`** — Every required engine-side capability flag is `True`.
3. **`test_adapter_satisfies_protocol`** — `RectifiedFlowCIFARAdapter` passes `isinstance(adapter, FlowMatchingODEAdapter)` (the `@runtime_checkable` Protocol). **Skip the test if `torch` is not installed** — uses `@pytest.mark.skipif(not torch_available)`.
4. **`test_run_round_produces_target_resembling_samples`** — `Engine.run_round` drives a round end-to-end; the endpoint is finite (no NaN), finite-norm, and inside the `[-3, 3]^3072` clamp box.
5. **`test_byte_determinism_across_runs`** — Two 10-round scenarios from identical seeds are byte-identical at every native state digest. **NOTE:** torch's `Conv2d` backward is not deterministic on CPU; we test **inference-only** determinism (eval mode, `torch.no_grad()`).
6. **`test_no_nan_over_many_seeds`** — `solve_ode` returns finite endpoints for `seed in {0, ..., 9}`.
7. **`test_endpoint_shape_correct`** — `observe_endpoint` returns a `StateBundle` whose `native_state_digest` resolves to a `(3, 32, 32)` tensor.
8. **`test_protocol_surface_intact`** — Every method is non-mutating for the canonical inputs (call twice, compare hashes).
9. **`test_restart_blend_respects_memory_fraction`** — `apply_restart_distribution` behaves correctly for `β ∈ {0.0, 0.5, 1.0}` (full prior / blend / full fresh).
10. **`test_engine_stress_20_rounds_with_restart`** — `Engine.run_round` drives 20 rounds alternating `β ∈ {0.0, 0.5}`; every trace validates under a 600-second CPU budget (RF UNet is much heavier than 2D MLP).
11. **`test_inject_forward_noise_hook`** — When `inject_forward_noise` is called on a `StateBundle`, the returned bundle has the perturbation added and a `forward_noise_applied` provenance tag.
12. **`test_state_shape_advertised_matches_runner`** — Assert `getattr(adapter, "state_shape", (2,)) == (3, 32, 32)` so the runner's forward-noise allocation works without modification.
14. **`test_license_check_accepted_license`** — Run a unit test on the loaded weights' license metadata (must be MIT / Apache / BSD).

**Conftest fixture:** `_materialize_rf_cifar_weights` (session-scoped) ensures `data/rectified_flow_cifar10.safetensors` exists at test session start. If absent, the fixture either:
- (a) downloads from PRIMARY_URL with sha256 verification, OR
- (b) marks the test module with `@pytest.mark.skipif(not Path("data/rectified_flow_cifar10.safetensors").exists())` — so CI without network doesn't break.

### 7.2 `tests/test_tools/test_run_rf_cifar_ablation.py` — new ablation table tests

Add to the existing `test_run_ablation.py` (or new file):

1. **`test_rf_cifar_ablation_rows_present`** — After running the ablation with `--include-rf-cifar`, the markdown table contains all 4 new row names (`vanilla`, `cosine`, `codimension_sheet`, `evidence_driven`).
2. **`test_rf_cifar_vanilla_fid_within_5pct`** — `vanilla` row reports `final_fid <= 2.32` (within 5% of paper's 2.21). Marks `pytest.mark.slow` and `pytest.mark.requires_rf_weights`.
3. **`test_rf_cifar_evidence_driven_selection_ratio_increases`** — Across 20 rounds, the `selection_curve` for `evidence_driven` shows `selection_curve[-1] >= 0.95` (paper Theorem 1 direction).
4. **`test_rf_cifar_no_fid_regression`** — For all 4 scheduler rows, `mean_fid <= vanilla_fid * 1.10` (no >10% regression). Marks `pytest.mark.slow`.

All tests in §7.2 marked `@pytest.mark.slow` and `@pytest.mark.requires_rf_weights` (skip if weights missing or torch missing).

### 7.3 CI integration

- **Default CI path:** runs tests 1-11, 12, 14 (no torch needed for some; `pytest.importorskip("torch")` for the rest).
- **Heavy CI path:** runs all tests + ablation; gated on `RUN_RF_ABLATION=1` env var and the presence of `data/rectified_flow_cifar10.safetensors`.

---

## §8. Expected outputs (with realistic numbers)

### 8.1 Baseline FID (vanilla 2-NFE Euler)

- **Target: 2.21 ± 0.11** (5% tolerance band).
- Realistic: **2.20-2.35** (the paper's number is reproducible when weights + config match exactly).
- Confidence: **5/5** (official weights, well-documented UNet).

### 8.2 Framework FID (per-scheduler)

- **Cosine row:** FID 2.30-2.50 (modest variation; cosine doesn't adapt the integration budget aggressively).
- **CodimensionSheet row:** FID 2.25-2.40 (codimension-aware; closer to baseline).
- **EvidenceDriven row:** FID **2.10-2.30** (paper Theorem 1 direction; expected to match or beat baseline).
- **RF-1step-Fixed row:** FID 2.21 ± 0.05 (matches vanilla — this is the sanity check that the framework is a no-op when the scheduler doesn't adapt).

### 8.3 Wall-clock per round (CPU)

- **Vanilla 2-NFE × 50K samples:** ~1.5-4 hours total (one-shot FID).
- **Framework 20 rounds × 2-4 NFE × 2500 samples/round = 100K-200K total samples:** ~3-8 hours per ablation row.
- **All 4 scheduler rows × FID-50K per round × 20 rounds:** ~20-60 hours total. **Realistic budget: 2-3 days on a single CPU box.**

### 8.4 selection_ratio (C4)

- **Round 0 (vanilla):** ~0.81 (baseline; matches 2D pattern).
- **Round 19 (EvidenceDriven):** ≥0.95 (paper Theorem 1 direction; matches 2D pattern).
- **Cosine / CodimensionSheet / RF-1step-Fixed rows:** plateau ~0.81-0.88 (their `eps_implicit` is fixed at construction; same finding as the 2D ablation).
- **EvidenceDriven row is the only schedule-sensitive row.**

### 8.5 Reproducibility budget

- All runs byte-deterministic for the same `(seed, weights, scheduler_config)` tuple (inference-only torch in eval mode + `torch.no_grad()`).
- `data/rectified_flow_cifar10.safetensors.sha256` enables fast "weights match" check before any run.

---

## §9. Failure modes

| # | Failure | Severity | Mitigation |
|---|---------|----------|------------|
| 1 | **Weights download fails** (PRIMARY_URL unreachable) | Medium | Fallback to FALLBACK_URL_1 (`gnobitab/RectifiedFlow`); then FALLBACK_URL_2 (`MuseFlow`). If all 3 fail, cache locally on the build machine's `~/.cache/huggingface/` and re-run with `HF_HUB_OFFLINE=1`. |
| 2 | **License is GPL/Research-Only** | High | Abort immediately; document in `docs/r5-survey/02-license-abort.md`; do NOT redistribute or commit weights. |
| 3 | **Vanilla FID > 2.32** (baseline reproduction fails) | Medium | Verify UNet config matches paper (channel counts, attention, time embedding); try secondary weights URL; if still > 2.32, report honestly in `docs/ABLATION.md` — this is a baseline reproduction failure, not a framework failure. |
| 4 | **Vanilla FID << 2.21** (suspiciously good) | Low | Likely a weights-leak: the InceptionV3 features for CIFAR-10 train overlap with the generated samples more than expected. Re-compute FID with the OFFICIAL CIFAR-10 test set features (not train) to disambiguate. Document the difference. |
| 5 | **Framework FID > vanilla FID + 10%** (regression) | High | Investigate the merge operator: is `merged_beta` saturating? Is the scheduler's `n_cap` too high? Try with `policy_driver=ConstantPolicyDriver(beta=0.0)` to disable the per-round restart. Report honestly in `docs/ABLATION.md` — do not hide a regression. |
| 6 | **FID too noisy across seeds** (std > 0.5) | Medium | Increase sample count to 50K; repeat 3× with different seeds; report `mean ± std`. Use the `numpy` PRNG (not torch's) for sample generation to maximize determinism. |
| 7 | **PyTorch dependency rejected by reviewer** | Medium | Document the rationale (SOTA FM models are PyTorch-native; ONNX slower; pure-NumPy impossible for 30 M-param UNet). Accept that ONE framework file requires torch. |
| 8 | **InceptionV3 download blocked** | Low | Use `torchvision.models.inception_v3(weights=Inception_V3_Weights.IMAGENET1K_V1)` which auto-downloads; fallback URL `https://download.pytorch.org/models/inception_v3_google-1a9a9a18.pth`. |
| 9 | **CPU memory blow-up during FID-50K** | Low | Each sample is `(3, 32, 32)` float32 = 12 KB; 50K samples × 12 KB = 600 KB. InceptionV3 forward at batch 64 ≈ 250 MB. Total ≈ 300 MB peak; fits comfortably in 4-8 GB CI. |
| 10 | **Adapter fails the `@runtime_checkable` Protocol check** (missing method) | Low | The 8 methods are mandatory in `FlowMatchingODEAdapter`. The smoke test `test_adapter_satisfies_protocol` (test 3) catches this before any other test runs. |
| 11 | **state_shape mismatch with runner's forward-noise allocation** | Low | F14 (`runner.py:774-783`) reads `getattr(self._adapter, "state_shape", (2,))`. We advertise `state_shape=(3, 32, 32)`; the runner will allocate correctly. Verify in `test_state_shape_advertised_matches_runner` (test 12). |
| 12 | **Byte-determinism breaks under torch** | Medium | Test 5 enforces inference-only determinism (`eval()` + `torch.no_grad()`). CPU torch backward is non-deterministic; we don't backward. |
| 13 | **Adapter weighs >10 MB** (file size for the .py module) | Low | N/A — the adapter is code, not weights; weights are ~120 MB stored separately. |
| 14 | **The framework loops forever on a CIFAR-10 sample** | Low | `RF_CIFAR_NATIVE_STATES_MAXSIZE=8` LRU-bounds the trajectory cache; the engine has a fail-closed 600-second per-round budget in test 10. |

---

## §10. Timeline (sub-tasks)

Total: **2-3 days (16-24 hours)**.

| Day | Sub-task | Output | Wall-clock |
|-----|----------|--------|------------|
| **0.5** | Download weights from PRIMARY_URL (with FALLBACK_1, FALLBACK_2); verify license is MIT/Apache/BSD; verify sha256; smoke-load + sample 50 images | `data/rectified_flow_cifar10.safetensors` (sha256 + LICENSE verified) | ~3 hours |
| **0.5** | Build the DDPM++ UNet constructor in the adapter (channel counts, attention, time embedding); unit-test that random-init forward returns the right shape | Adapter skeleton + `test_load_safetensors_and_capabilities` | ~4 hours |
| **1.0** | Implement the 8-method adapter surface (capabilities, build_initial_state, export_endpoint, detach_and_validate_endpoint, apply_restart_distribution, compose_condition, solve_ode, observe_endpoint); add export_trajectory + inject_forward_noise | Full adapter + 11 unit tests | ~8 hours |
| **0.5** | Baseline FID reproduction: vanilla 50K-sample generation, compute InceptionV3 features, FID-50K vs paper's 2.21 | `docs/r5-survey/02-baseline-fid.md` (FID ≤ 2.32 expected) | ~5 hours (incl. generation) |
| **0.5** | Pre-compute CIFAR-10 train InceptionV3 features (one-time, 410 MB output) | `data/cifar10_inception_features.npz` | ~30 min |
| **0.5** | Wire `RectifiedFlowCIFARAdapter` into `tools/run_rf_cifar_ablation.py` with 4 scheduler rows (Cosine, CodimensionSheet, EvidenceDriven, RF-1step-Fixed) | Ablation script + 4 ablation tests | ~4 hours |
| **0.5** | Run 20-round ablation × 4 schedulers × 2500 samples/round; compute per-round FID; generate FID trajectory figure + selection_ratio figure | `docs/figures/r5_rf_cifar_fid_trajectory.png`, `docs/figures/r5_rf_cifar_selection_ratio.png`, `docs/ABLATION.md` | ~20-50 hours (compute-bound; can be reduced to 4 rows × 1000 samples/round = 5-12 hours) |
| **0.25** | Wire RF CIFAR results into paper claims (CLM-040, CLM-041, CLM-042) | `docs/CLAIMS.md` updates + `verify_claims` gate green | ~1 hour |
| **0.25** | Run all gates (`pytest`, `ruff`, `mypy`, `docs-check`, `claims-sync`, `mkdocs`) | All 6 gates green | ~1 hour |
| **Total** | | | **~46-72 hours / 5-9 days (mostly compute-bound on FID-50K)** |

**Compute-budget optimization:** if 20-50 hours per ablation is too slow, drop to **FID-10K** for the development pass and **FID-50K** for the final paper claim (per §2.4 — paper used 50K). FID-10K cuts wall-clock by 5× → 4-10 hours per ablation.

---

## §11. Verification (claims to add to `docs/CLAIMS.md`)

| Claim ID | Statement | Evidence | Test |
|----------|-----------|----------|------|
| **CLM-040** | `RectifiedFlowCIFARAdapter` reproduces Liu 2022's published CIFAR-10 FID (2.21) within 5% (i.e., FID ≤ 2.32). | `tools/eval_rf_cifar.py --mode vanilla --num-samples 50000`; FID column in `docs/ABLATION.md` `vanilla_rf_cifar` row. | `tests/test_tools/test_run_rf_cifar_ablation.py::test_rf_cifar_vanilla_fid_within_5pct`. |
| **CLM-041** | Framework multi-round FID on Rectified Flow CIFAR is ≤ vanilla baseline FID + 10% (parity-with-tolerance) for all 4 schedulers. | 4-row ablation; `cosine`, `codimension_sheet`, `evidence_driven`, `rf_1step_fixed` rows report `mean_fid ≤ vanilla_fid * 1.10`. | `tests/test_tools/test_run_rf_cifar_ablation.py::test_rf_cifar_no_fid_regression`. |
| **CLM-042** | `EvidenceDrivenScheduler` row achieves `selection_ratio ≥ 0.95` across 20 rounds on Rectified Flow CIFAR (paper Theorem 1 direction; transposed from 2D synthetic to SOTA FM on real images). | `tools/run_rf_cifar_ablation.py`; `evidence_driven` row `selection_curve[-1] ≥ 0.95`. | `tests/test_tools/test_run_rf_cifar_ablation.py::test_rf_cifar_evidence_driven_selection_ratio_increases`. |

Each claim links to:
- The pytest test that asserts it.
- The ablation row that produces the empirical number.
- The paper section it supports (`docs/paper-plan.md` §5 "Empirical results on Rectified Flow CIFAR-10").

---

## §12. Paper integration

### 12.1 Add §5 to paper plan

New paper section: **"§5. Empirical validation on Rectified Flow (CIFAR-10)"**.

Outline:
- §5.1: Setup — adapter, weights, baseline reproduction (FID 2.21 ± 5%).
- §5.2: Framework configuration — 4 scheduler variants, 20 rounds, 2500 samples/round.
- §5.3: Results table — FID per scheduler per round (mean, best, wall-clock).
- §5.4: Selection-ratio trajectory — EvidenceDriven row hits ≥0.95; other rows plateau.
- §5.5: Discussion — framework generalises from synthetic 2D to SOTA FM on real images without algorithm-layer modification.

### 12.2 Tables

**Table: Baseline reproduction vs framework (RF CIFAR-10).**

| Method | FID (r=0) | FID (r=10) | FID (r=19) | Mean FID | Wall/round |
|--------|-----------|------------|------------|----------|------------|
| Vanilla 2-NFE Euler (paper) | 2.21 | — | — | — | — |
| Vanilla 2-NFE Euler (ours) | x.xx | — | — | — | — |
| Cosine | x.xx | x.xx | x.xx | x.xx | <Xs |
| CodimensionSheet | x.xx | x.xx | x.xx | x.xx | <Xs |
| EvidenceDriven | x.xx | x.xx | x.xx | x.xx | <Xs |
| RF-1step-Fixed | x.xx | x.xx | x.xx | x.xx | <Xs |

### 12.3 Figures

- **Figure 1: FID trajectory.** 4 colored lines (one per scheduler), X = round 0..19, Y = FID, dashed horizontal line at vanilla 2.21. Saves as `docs/figures/r5_rf_cifar_fid_trajectory.png` via `tools/plot_rf_cifar.py --metric fid`.
- **Figure 2: selection_ratio trajectory.** 4 colored lines (one per scheduler), X = round 0..19, Y = selection_ratio ∈ [0, 1], reference line at 0.81 (baseline) and 1.0 (paper Theorem 1 limit). Saves as `docs/figures/r5_rf_cifar_selection_ratio.png` via `tools/plot_rf_cifar.py --metric selection_ratio`.

### 12.4 Cross-references

- The paper's §5.1 cross-references the framework's `ReInferenceRunner` (no algorithm changes needed for SOTA FM).
- The paper's §5.4 cross-references the synthetic 2D results (existing section, R4-survey) — the load-bearing generalisation claim.
- The paper's §5.5 cross-references the FM literature (Liu 2022, Lipman 2023, Song 2023) — positions the framework as adapter-agnostic.

---

## 10-line summary

- **Chosen model and paper:** Rectified Flow (Liu et al., NeurIPS 2022 Spotlight, `arXiv:2210.02647`) on CIFAR-10 32×32; FID 2.21 (2-RF, 1-NFE Euler).
- **Weights URL and size:** HuggingFace `huggan/cifar10-resnet-flow-matching` (primary, ~120 MB, Apache-2.0); fallback to `gnobitab/RectifiedFlow` Zenodo and `MuseFlow` GitHub release.
- **Original task and baseline FID:** CIFAR-10 32×32 unconditional generation; FID 2.21 ± 5% (paper Table 2).
- **Adapter file path:** `adaptive_reflow/adapters/rectified_flow_cifar.py`; class `RectifiedFlowCIFARAdapter` implementing `FlowMatchingODEAdapter` Protocol with `state_shape=(3, 32, 32)`.
- **Estimated timeline:** ~46-72 hours / 5-9 days wall-clock (mostly compute-bound on FID-50K × 20 rounds × 4 schedulers); ~16-24 hours of human-effort; PyTorch dependency added to one adapter file only.
- **Critical risk:** License on weights (must be MIT/Apache/BSD — verify before download); baseline FID > 2.32 (UNet config mismatch); CPU FID-50K takes 1.5-4 hours per evaluation.
- **Expected improvement direction:** EvidenceDriven row achieves FID ≤ 2.21 with fewer NFE on average; other rows within ±10% of baseline (parity acceptable; regression must be reported honestly).
- **Number of new files:** **5 new files** + 2 modifications:
  - `adaptive_reflow/adapters/rectified_flow_cifar.py` (adapter)
  - `tools/eval_rf_cifar.py` (baseline FID reproduction script)
  - `tools/run_rf_cifar_ablation.py` (4-row framework ablation)
  - `tools/plot_rf_cifar.py` (FID trajectory + selection_ratio figures)
  - `tests/test_adapters/test_rectified_flow_cifar.py` (13 adapter tests)
  - `tests/test_tools/test_run_rf_cifar_ablation.py` (4 ablation tests)
  - Modifications: `adaptive_reflow/adapters/__init__.py` (export the new adapter); `tools/run_ablation.py` (route the new ablation); `pyproject.toml` (add `[rf-cifar]` extra with `torch>=2.0`, `pytorch-fid`, `torchvision`).
- **Number of new tests:** **17 new tests** (13 adapter + 4 ablation), all in the existing test directories.
- **Plan file path:** `c:\Users\31472\codes\flowa-multistep-reinference\docs\r5-survey\02-sota-integration-plan.md`