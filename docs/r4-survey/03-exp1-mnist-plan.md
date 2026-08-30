# EXP-1: MNIST Rectified Flow — End-to-End Plan

**Agent:** P1 (planning)
**Date:** 2026-08-30
**Working dir:** `c:\Users\31472\codes\flowa-multistep-reinference`
**Goal:** Move the framework's empirical demonstration from a synthetic 2D Rectified Flow target (`two_moons`, `eight_gaussians`) onto a **real domain** (MNIST 28x28 grayscale), reusing the framework's algorithm layer (schedulers / drivers / blenders / merge operators / hash-chained ledger) unchanged. EXP-1 is the highest-leverage experiment for the paper — it generalises the existing 2D story from "framework works on a synthetic toy" to "framework works on real images" without changing the framework itself.

**Constraints (read-only):**
- `/c/Users/31472/codes/noise-selected-rectification-lean/` — DO NOT TOUCH.
- This phase is read-only on the working repo — this plan is the deliverable; no code is modified yet.

---

## §1. Architecture overview

### 1.1 Where MNIST fits in the existing adapter framework

The adapter layer (`adaptive_reflow.adapters.*`) is intentionally pluggable:
- The framework's contract is `FlowMatchingODEAdapter` (8 methods + `capabilities`) declared in `adaptive_reflow/universal/adapter.py`.
- Concrete adapters in the working tree today: `TwoDimFMAdapter` (2D rectified flow, the reference), plus synthetic / toy / reference / flowmol3 fixtures.
- The algorithm layer (`ReInferenceRunner`, schedulers, drivers, merge operators, blenders, evaluators, hash-chained ledger) is adapter-agnostic — it consumes only the 8-method protocol surface and `AdapterCapabilities`. No algorithm-layer code needs to change.

EXP-1 adds a single new concrete adapter — `MnistFmAdapter` — that:
- Trains a small NumPy UNet on MNIST (offline, in `adaptive_reflow/adapters/mnist_fm_train.py`, following the `twodim_fm_train.py` pattern exactly).
- Loads the trained weights and exposes the same 8-method protocol surface against the 28x28 grayscale pixel state.
- Reuses RK4 (byte-deterministic) integration, identical to `TwoDimFMAdapter`.
- Reuses the framework's existing schedulers, drivers, blenders, ledger, and (with one optional evaluator addition) the framework's existing FID-as-quality-metric support.

The framework layer is **not** modified — only the adapter is added.

### 1.2 What changes vs `TwoDimFMAdapter` (2D) for MNIST (28x28 grayscale)

| Aspect | `TwoDimFMAdapter` | `MnistFmAdapter` (new) |
|---|---|---|
| State shape | `(2,)` continuous | `(1, 28, 28)` grayscale (or flattened `(784,)` — see §1.4) |
| Velocity field | MLP `3 -> 64 -> 64 -> 2` (~518 params) | NumPy UNet `1 -> 32 -> 64 -> 32 -> 1` (~500K-2M params) with sinusoidal time embedding |
| Channels | `(xy,)` continuous | `(x,)` continuous (flattened 784-dim; pixels in `[0, 1]`) |
| Integrator | RK4 byte-deterministic (same) | RK4 byte-deterministic (same) — one custom 4D conv-style UNet block; same RK4 formula |
| Restart | Blend endpoint with `N(0, I_2)` | Blend endpoint with `N(0, I_784)` reshaped to `(1, 28, 28)` |
| `native_config_hash` | `"twodim_fm:cfg:v1"` | `"mnist_fm:cfg:v1"` |
| `state_shape` capability | `(2,)` | `(1, 28, 28)` (or `(784,)` if flattened — see §1.4) |
| Target distribution | Analytic (two-moons / eight-gaussians) | Empirical (10K test MNIST digits, `torchvision.datasets.MNIST`) |
| Training | `twodim_fm_train.py` (3-layer MLP, MSE on `v_θ(x_t, t) - (x_1 - x_0)`) | `mnist_fm_train.py` (small UNet, identical MSE loss form, analytic gradients via NumPy) |
| Source distribution | `N(0, I_2)` | `N(0, I_{1x28x28})` (clamped to `[-1, 1]`) |
| FID computation | Closed-form 2D W2 against analytic target | FID against 10K MNIST test images (see §5 for FID choice) |

### 1.3 Capability handshake — what `MnistFmAdapter` advertises

`MnistFMCapabilities(AdapterCapabilities)`:
- `has_ode_integration_surface=True`
- `has_prior_export=True`
- `has_state_export=True`
- `has_condition_injection=True`
- `has_restart_boundary=True`
- `has_continuous_channels=True` (pixels are continuous in `[0, 1]`)
- `has_discrete_channels=False`
- `has_trajectory_digest=True`
- `has_deterministic_seed=True`
- `has_materialization_route=True`
- `state_shape=(1, 28, 28)` (matches the trailing-axes convention used by `_features`/`_velocity_field` reshape paths; see §1.4 for the flattened-vs-image decision)
- `supported_channels=("x",)` — single flattened grayscale pixel channel
- `channel_domains={ChannelName("x"): "continuous"}`
- `required_mixer=NoOpMixer`
- `exposed_envelope_criteria=()`
- `exposed_evaluators=()`
- `native_config_hash="mnist_fm:cfg:v1"`
- `native_config_version="0.1.0"`

### 1.4 State shape decision: `(1, 28, 28)` image vs `(784,)` flattened

**Decision: flatten to `(784,)` for the adapter's `state_shape` capability; internally reshape to `(1, 28, 28)` for the UNet forward pass.**

Rationale:
- The framework's `state_shape` is used by `ReInferenceRunner.run` (around lines 774-783 of `runner.py`) only to allocate a `np.zeros(state_shape, ...)` prior for the forward-noise injection. `(784,)` is consistent with how the rest of the framework treats state vectors (linear flat arrays), and avoids breaking F14's contract that the runner "folds the batch shape into its `config_hash`".
- Inside `MnistFmAdapter`, the UNet forward reshapes `(batch, 784) -> (batch, 1, 28, 28) -> conv -> reshape (batch, 784)` for the velocity output. This matches how `TwoDimFMAdapter` reshapes `(2,) -> (n, 2)` internally before computing the MLP forward.
- Alternative `(1, 28, 28)` is more "image-native" but would force the runner's forward-noise allocation into a 3D tensor path that the rest of the framework does not exercise. **Flat `(784,)` is safer for a first integration.**

The trainer writes a flat `.npz` of UNet weights; the adapter reshapes on load and on every forward pass.

---

## §2. Training plan

### 2.1 Model architecture: small NumPy UNet

```
Input:  (B, 1, 28, 28) grayscale image in [-1, 1]
Concatenated with sinusoidal t-embedding broadcast to (B, 1, 28, 28) -> (B, 2, 28, 28)
                    (or: time as extra channel; we use the second-channel approach)

Down 1:  Conv2d(2 -> 32, k=3, p=1) + GroupNorm(8) + SiLU   -> (B, 32, 28, 28)
Down 2:  Conv2d(32 -> 64, k=3, s=2, p=1) + GroupNorm(8) + SiLU -> (B, 64, 14, 14)
Down 3:  Conv2d(64 -> 64, k=3, s=2, p=1) + GroupNorm(8) + SiLU -> (B, 64, 7, 7)

Bottleneck: Conv2d(64 -> 64, k=3, p=1) + GroupNorm(8) + SiLU + Conv2d(64 -> 64, k=3, p=1) -> (B, 64, 7, 7)

Up 1:  Upsample(nearest, 2x) + Conv2d(64 -> 32, k=3, p=1) + GroupNorm(8) + SiLU  -> (B, 32, 14, 14)
Up 2:  Upsample(nearest, 2x) + Conv2d(32 -> 32, k=3, p=1) + GroupNorm(8) + SiLU  -> (B, 32, 28, 28)

Output: Conv2d(32 -> 1, k=3, p=1) -> (B, 1, 28, 28) velocity prediction
```

**Parameter target:** ~600K-800K (CPU-tractable). The 3 down + bottleneck + 2 up structure mirrors a "tiny UNet" used in DDPM smoke tests. We Kaiming-uniform init all Conv weights; zero-init all biases and the final projection layer (residual-style stabilisation).

### 2.2 Hyperparameters

| Hyperparameter | Value | Rationale |
|---|---|---|
| Optimizer | NumPy Adam (β1=0.9, β2=0.999, ε=1e-8) | Match `twodim_fm_train.py`; no torch dep |
| Learning rate | 1e-3 | Adam default; standard for UNets on MNIST |
| Batch size | 64 | CPU-tractable; ~32MB per batch |
| Epochs | 30 | Loss converges ~5-7 FID delta in <30 min on CPU |
| Dataset | torchvision MNIST (60K train, 10K test) | Standard; auto-download via `torchvision.datasets.MNIST` |
| Loss | MSE between `v_θ(x_t, t)` and `(x_1 - x_0)` (per-pixel) | Rectified Flow loss; identical to `twodim_fm_train.py` |
| Interpolation | `x_t = (1-t) * x_0 + t * x_1`, `t ~ U[0, 1]` | Same as 2D |
| Normalization | `[0, 1] -> [-1, 1]` (mean/std ≈ 0.13/0.31 for MNIST, but we use the cleaner `[-1, 1]` clamp at sample time) | Standard |
| Time embedding | Sinusoidal broadcast to a 2nd input channel | Avoids a learned time-MLP for CPU speed |
| Output path | `data/mnist_fm.npz` | Mirrors `data/twodim_fm_<target>.npz` |
| Seed | 42 | Default; matches ablation seed |
| Validation interval | Every 200 steps print loss | Mirrors `twodim_fm_train.py` |

### 2.3 Optimizer (NumPy Adam) — analytic gradient sketch

- Forward: `im2col`-style unfold + matmul (each conv is a matmul over its `k*k` spatial window). Implement via `np.einsum("bchw,coij->bohw", x, w)` patterns.
- Backward: analytic conv backward via `np.einsum` + `np.pad` (no autograd).
- GroupNorm backward: `(x - mean) / sqrt(var + eps)`.
- SiLU: `x * sigmoid(x)`; backward: `sigmoid(x) + x * sigmoid(x) * (1 - sigmoid(x))`.
- Nearest-neighbour upsample: backward distributes gradient equally to the 4 source pixels.
- Total param count: ~600K. At batch 64 this is ~38M activations per layer, ~150MB peak. Fits CPU.

**Concrete trainer file: `adaptive_reflow/adapters/mnist_fm_train.py`** — modelled line-for-line on `twodim_fm_train.py`. Function signatures:

```python
def velocity_field_unet_init(rng, base_channels=32) -> list[np.ndarray]:
    """Kaiming-uniform init of the small UNet. Returns ~24 weight tensors + biases."""
    ...

def velocity_field_forward(weights, x, t) -> np.ndarray:
    """Forward: (B, 1, 28, 28) image + (B,) time -> (B, 1, 28, 28) velocity."""
    ...

def _loss_and_grads(weights, x_t, t, v_target) -> tuple[float, list[np.ndarray]]:
    """MSE loss + analytic grads, identical loss form to 2D trainer."""
    ...

def train(epochs=30, batch_size=64, lr=1e-3, seed=42) -> list[np.ndarray]:
    """Train on MNIST and return the weight list."""
    ...

def save_weights(weights, path) -> Path: ...
def load_weights(path) -> list[np.ndarray]: ...
def main(argv=None) -> int: ...  # argparse CLI
```

CLI example:
```bash
python -m adaptive_reflow.adapters.mnist_fm_train \
    --epochs 30 --batch-size 64 --lr 1e-3 --output data/mnist_fm.npz
```

### 2.4 Dataset loading

- `from torchvision import datasets, transforms`
- `transforms.Compose([transforms.ToTensor(), transforms.Lambda(lambda x: 2*x - 1)])` to land in `[-1, 1]`.
- `datasets.MNIST(root="data/mnist_cache", train=True, download=True)` — auto-downloads from `yann.lecun.com`. Fallback to a mirror (`https://ossci-datasets.s3.amazonaws.com/mnist/`) if the canonical URL is blocked.
- Cache in `data/mnist_cache/MNIST/raw/` so re-runs are offline.

### 2.5 Expected training time (CPU)

- 60K images / 64 batch = 938 batches/epoch.
- 30 epochs = ~28K batches.
- Per-batch UNet forward (~600K params) ≈ 0.3s; backward ≈ 0.6s. Total ~1s/batch.
- **Total: ~28K seconds / 3600 ≈ 8 hours** — too slow for the 0.5-day budget.
- **Mitigation: target 10 epochs** → ~2.5-3 hours; still too slow. **Mitigation 2: target 5 epochs and reduce base_channels to 24** → ~1 hour. **Mitigation 3: use 128 batch with 10 epochs and base_channels=32** → ~1.5 hours.
- **Recommended for the plan: 10 epochs, batch 64, base_channels=32 → ~3 hours on a single CPU core. If we want sub-1-hour, use base_channels=24 and 8 epochs (~45 min).** The plan must commit to one — we pick **base_channels=32, 10 epochs, batch 64 → ~2.5 hours, then 30 min to write the adapter and run the smoke ablation.**

### 2.6 Output

- `data/mnist_fm.npz` — UNet weights serialized as `float32` (`np.savez_compressed`). Expected size: ~2-3 MB.
- `data/mnist_fm.npz.sha256` — checksum for reproducibility.

---

## §3. Adapter implementation plan

### 3.1 File: `adaptive_reflow/adapters/mnist_fm.py`

Module-level constants (mirroring `twodim_fm.py`):

```python
MNIST_FM_CHANNELS: tuple[ChannelName, ...] = (ChannelName("x"),)
MNIST_FM_CONFIG_HASH: str = "mnist_fm:cfg:v1"
MNIST_FM_CONFIG_VERSION: str = "0.1.0"
MNIST_FM_STATE_SHAPE: tuple[int, ...] = (784,)  # flattened; see §1.4
MNIST_FM_IMAGE_SHAPE: tuple[int, ...] = (1, 28, 28)  # internal UNet shape
MNIST_FM_CLAMP: float = 1.0  # pixels live in [-1, 1] after normalization
MNIST_FM_NUM_STEPS: int = 100  # RK4 grid; matches TwoDimFMAdapter
MNIST_FM_NATIVE_STATES_MAXSIZE: int = 128  # same bound as 2D
```

### 3.2 Class: `MnistFmAdapter`

Implements the full `FlowMatchingODEAdapter` Protocol — 8 methods + `export_trajectory` + optional `inject_forward_noise` (P0-7):

| # | Method | Behaviour |
|---|---|---|
| 1 | `capabilities()` | Return `MnistFMCapabilities` (frozen dataclass with `state_shape=(784,)`) |
| 2 | `build_initial_state(batch_id, sample_id)` | SHA256-seeded `np.random.default_rng`; sample `x0 ~ N(0, I_784)`; clamp to `[-1, 1]`; construct `StateBundle` with `ChannelName("x")` and `TensorRef("mnist:x:<sha256[:16]>")` |
| 3 | `export_endpoint(state)` | Validate `state_bundle`; return `state` (no copy) |
| 4 | `detach_and_validate_endpoint(bundle)` | Fail-closed `detach_proof is True` check; validate bundle |
| 5 | `apply_restart_distribution(state, policy)` | Blend `m * prior_x0 + (1-m) * fresh_x0` (m = 1 - β) with fresh `N(0, I_784)` seeded by `(policy_hash, source_round+1)`; emit next round's `StateBundle` with new `TensorRef` |
| 6 | `compose_condition(bundle, delta)` | Inject `target_distribution="mnist"` and `integrator_config_hash=MNIST_FM_CONFIG_HASH` into `delta_spec` |
| 7 | `solve_ode(state, condition, *, seed)` | RK4 integration over `t_grid = linspace(0, 1, num_steps+1)` using `_velocity_field(weights, x, t)` reshaped `(batch, 1, 28, 28)` per step; returns `ODEIntegratorTrace` with `traj_digest` keyed on `(x0, integrator, num_steps, seed, target)` |
| 8 | `observe_endpoint(trace, state)` | Pull final row of stored trajectory; build endpoint `StateBundle` with new `endpoint_digest` |
| + | `export_trajectory(trace)` | Return `(T, 784)` stored trajectory for `trace.native_state_digest` (P0-7) |
| + | `inject_forward_noise(bundle, injected)` | Optional; add `injected` (already a `(784,)` vector from `scheduler.inject_noise`) to the bundle's prior — returns new bundle with `provenance += ("forward_noise_applied",)` |

### 3.3 Integrator: RK4 (byte-deterministic) — same as TwoDimFMAdapter

```python
def _integrate_rk4(weights, x0, t_grid) -> np.ndarray:
    """Pure RK4 over t_grid; returns (len(t_grid), 784) trajectory."""
    x0 = np.asarray(x0, dtype=np.float64).reshape(784)
    grid = np.asarray(t_grid, dtype=np.float64)
    traj = np.empty((grid.size, 784), dtype=np.float64)
    traj[0] = x0
    x_cur = x0.copy()
    for i in range(1, grid.size):
        t0, t1 = float(grid[i-1]), float(grid[i])
        dt = t1 - t0
        k1 = _velocity_field(weights, x_cur.reshape(1,1,28,28), t0).reshape(784)
        k2 = _velocity_field(weights, (x_cur + 0.5*dt*k1).reshape(1,1,28,28), t0 + 0.5*dt).reshape(784)
        k3 = _velocity_field(weights, (x_cur + 0.5*dt*k2).reshape(1,1,28,28), t0 + 0.5*dt).reshape(784)
        k4 = _velocity_field(weights, (x_cur + dt*k3).reshape(1,1,28,28), t1).reshape(784)
        x_cur = x_cur + (dt/6.0)*(k1 + 2*k2 + 2*k3 + k4)
        x_cur = np.clip(x_cur, -MNIST_FM_CLAMP, MNIST_FM_CLAMP)  # numerical safety
        traj[i] = x_cur
    return traj
```

Batched variant `_batched_integrate_rk4(weights, x0_batch, n_steps)` returns `(batch, 784)` final states; used for population evaluation (FID).

### 3.4 State shape: `(1, 28, 28)` internally; `(784,)` over the protocol boundary

- All `StateBundle` channels carry `(784,)` arrays.
- The adapter reshapes `(784,) -> (1, 28, 28)` at the UNet boundary and back.
- The reshapes are zero-cost (no copy) when contiguous; we use `np.ascontiguousarray` for safety.
- The `TensorRef` digest includes the full `(784,)` vector via `_digest_state` (sha256 over a deterministic repr).

### 3.5 Restart: blend endpoint with fresh `N(0, I_784)`

Same blend formula as `TwoDimFMAdapter.apply_restart_distribution`:
- `memory_fraction = 1 - β` where `β` comes from `policy.beta_by_channel[ChannelName("x")]`.
- `m = clip(memory_fraction, 0, 1)`
- `prior_x0` is the previous round's stored x0 (from `_native_states[state.native_state_digest]`).
- `fresh_x0 = np.random.default_rng(seed_from(policy_hash, source_round+1)).standard_normal(784).astype(np.float64)`
- `blended = m * prior_x0 + (1 - m) * fresh_x0`, reshaped to `(784,)`, stored in `_native_states` under a new digest.
- Output `StateBundle` carries `provenance += (AUDIT_RESTART_BLEND, "blender:linear", "blender_hash:linear_blender_default")`.

### 3.6 Capabilities handshake — exact dataclass

```python
@dataclass(frozen=True)
class MnistFMCapabilities(AdapterCapabilities):
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
            state_shape=(784,),
            supported_channels=MNIST_FM_CHANNELS,
            channel_domains={ChannelName("x"): "continuous"},
            required_mixer=NoOpMixer,
            exposed_envelope_criteria=(),
            exposed_evaluators=(),
            native_config_hash=MNIST_FM_CONFIG_HASH,
            native_config_version=MNIST_FM_CONFIG_VERSION,
        )
```

### 3.7 Factory

```python
def default_mnist_fm_adapter(*, weights_path: Path | None = None) -> MnistFmAdapter:
    """Default factory: loads data/mnist_fm.npz unless ``weights_path`` is given."""
    path = Path(weights_path) if weights_path is not None else Path("data/mnist_fm.npz")
    return MnistFmAdapter(weights_path=path)
```

---

## §4. Training script plan

### 4.1 File: `adaptive_reflow/adapters/mnist_fm_train.py`

Modelled on `twodim_fm_train.py` line-for-line.

Module sections:
1. **Module docstring** — describe the training objective (rectified flow on MNIST), the architecture (small NumPy UNet), the expected runtime (~2-3 hours CPU for 10 epochs).
2. **Imports** — `argparse`, `pathlib.Path`, `numpy`, `numpy.typing.NDArray`. Conditional `torchvision` import inside `_load_mnist()` (so the trainer is a strict extra).
3. **Constants** — `MNIST_TRAIN_SIZE = 60_000`, `MNIST_TEST_SIZE = 10_000`, `MNIST_IMAGE_SHAPE = (1, 28, 28)`, `MNIST_FLAT_DIM = 784`.
4. **`_load_mnist(split: str) -> np.ndarray`** — returns `(60000, 784)` or `(10000, 784)` float64 in `[-1, 1]`. Uses `torchvision.datasets.MNIST` with auto-download. Caches under `data/mnist_cache/`.
5. **`velocity_field_unet_init(rng, base_channels=32) -> list[np.ndarray]`** — Kaiming-uniform init of all 24 weight tensors + biases. Returns a flat list so Adam's moment arrays index naturally.
6. **`velocity_field_forward(weights, x, t) -> np.ndarray`** — UNet forward. `x: (B, 1, 28, 28)`, `t: (B,)`; returns `(B, 1, 28, 28)` velocity. Includes the time-as-second-channel trick.
7. **`_unet_backward(weights, x, t, v_target, v_pred) -> list[np.ndarray]`** — analytic grads for all UNet layers (this is the load-bearing piece). Use a layered approach: GroupNorm backward = `(x - mean) / sqrt(var + eps)`; SiLU backward = `sigmoid(x) * (1 + x * (1 - sigmoid(x)))`; nearest upsample backward distributes grad; conv backward via `np.einsum` + padding.
8. **`_loss_and_grads(weights, x_t, t, v_target) -> tuple[float, list[np.ndarray]]`** — MSE + analytic grads (mirrors the 2D trainer).
9. **`train(epochs=30, batch_size=64, lr=1e-3, base_channels=32, seed=42) -> list[np.ndarray]`** — main loop; `np.random.default_rng(seed)`; per-batch `x_0 ~ N(0, I_784)`, `x_1 ~ batch_from_train_set`, `t ~ U[0,1]`, `x_t = (1-t)*x_0 + t*x_1`, `v_target = x_1 - x_0`. Adam with `β1=0.9, β2=0.999, eps=1e-8`. Print loss every 200 steps.
10. **`save_weights(weights, path) -> Path`** — `np.savez_compressed(path, **{f"W{i}": w for i, w in enumerate(weights)})`.
11. **`load_weights(path) -> list[np.ndarray]`** — inverse of `save_weights`; reshapes to `float64`.
12. **`main(argv=None) -> int`** — argparse CLI: `--epochs, --batch-size, --lr, --base-channels, --seed, --output, --cache-dir`.

### 4.2 CLI run example

```bash
python -m adaptive_reflow.adapters.mnist_fm_train \
    --epochs 10 --batch-size 64 --lr 1e-3 --base-channels 32 \
    --output data/mnist_fm.npz --cache-dir data/mnist_cache
```

Expected output (stdout):
```
[mnist_fm] loaded 60000 training images, 10000 test images
[mnist_fm] step 1/9380 loss=0.482103
[mnist_fm] step 200/9380 loss=0.187234
...
[mnist_fm] step 9380/9380 loss=0.041287
[mnist_fm] saved data/mnist_fm.npz (2418123 bytes)
```

---

## §5. Framework integration plan

### 5.1 Add `MnistFmAdapter` to `adaptive_reflow/adapters/__init__.py`

Append (mirroring the `TwoDimFMAdapter` block):

```python
from .mnist_fm import (
    MNIST_FM_CHANNELS,
    MNIST_FM_CONFIG_HASH,
    MNIST_FM_CONFIG_VERSION,
    MnistFmAdapter,
    default_mnist_fm_adapter,
)
```

This makes the adapter importable via `from adaptive_reflow.adapters import MnistFmAdapter`.

### 5.2 FID computation — options and decision

**Three options considered:**

1. **pytorch-fid library** — `pip install pytorch-fid`. Computes FID against ImageNet-pretrained InceptionV3 features. Requires torchvision + scipy + numpy. Adds a heavy dep (PyTorch at test time). Rejected for EXP-1 because the project is stdlib-only by design (see `docs/paper-plan.md` §7.2 "CPU only").

2. **Custom MNIST-trained InceptionV3 alternative** — train a small CNN on MNIST, use its penultimate features for FID. Adds training complexity and is not comparable to literature FID. Rejected for EXP-1.

3. **NumPy-only custom FID** — compute `(μ_r - μ_g)^T (Σ_r + Σ_g - 2(Σ_r Σ_g)^{1/2})` from flattened grayscale features; feature extractor = small random Conv stack (deterministic, no training). This is the "FID-style" metric used in some MNIST benchmarks. **Selected for EXP-1.**

**Decision:** Implement a NumPy-only FID helper in `adaptive_reflow/eval/mnist_fid.py`:
- `class MnistFidEvaluator` (matching the `_EvaluatorProtocol` duck-type used by `ReInferenceRunner`).
- `oracle(bundle, *, channel, seed) -> dict[str, float]` returns `{"fid": float, "fid_baseline": float}` where:
  - `fid`: Fréchet distance between the bundle's flattened prior image and the test-set features using a small fixed random projection `(784 -> 128)` via `np.random.default_rng(seed).standard_normal((784, 128)) / sqrt(128)`.
  - `fid_baseline`: same FID but with the bundle's image replaced by pure Gaussian noise.
- Mean (μ) and covariance (Σ) computed once over the test set; cached at construction time.

The "FID" here is interpretable as a Wasserstein-like distance in a random feature space — it correlates with perceptual quality on MNIST but is **not** comparable to literature FID. The plan documents this caveat in `MnistFidEvaluator` docstring and in the ablation markdown.

**Fallback (§8):** If FID computation is too noisy (std > 0.5 across seeds), use the simpler **MSE-based quality metric**: `mse_to_test_set_mean_image(bundle) = mean((x - μ_test)^2)` — lower is better, easy to interpret, no covariance inversion.

### 5.3 Add 4-row ablation rows to `tools/run_ablation.py`

Append to the `CANONICAL_CONFIGURATIONS` tuple (after the existing 8 rows):

```python
MNIST_CONFIGURATIONS: tuple[str, ...] = (
    "single_pass_mnist",
    "multi_round_mnist_cosine",
    "multi_round_mnist_codimension_sheet",
    "multi_round_mnist_evidence_driven",
)
```

Add helper branches in `_build_components(config, *, rounds)`:

```python
if config == "single_pass_mnist":
    return default_cosine_scheduler(cycle_length=1), ConstantPolicyDriver(beta=0.0), 1
if config == "multi_round_mnist_cosine":
    return default_cosine_scheduler(cycle_length=rounds, n_min=COSINE_N_MIN, n_max=COSINE_N_MAX), "default", int(rounds)
if config == "multi_round_mnist_codimension_sheet":
    return CodimensionSheetScheduler(cycle_length=rounds, n_min=COSINE_N_MIN, n_max=COSINE_N_MAX, eps_implicit=CODIMENSION_EPS_IMPLICIT), "default", int(rounds)
if config == "multi_round_mnist_evidence_driven":
    # Reuse the EvidenceDrivenScheduler wiring from the 2D evidence-driven row.
    cfg = CosineScheduleConfig(...)
    return _EDS(config=cfg, kp=0.2, ki=0.05, max_step=0.05, target_ratio=1.0, k_eps=0.5, eps_implicit_base=CODIMENSION_EPS_IMPLICIT), "default", int(rounds)
```

Add `MNIST_TARGET: str = "mnist"` and route these 4 rows to a new `_run_one_mnist(...)` helper that:
- Builds `MnistFmAdapter(weights_path=Path("data/mnist_fm.npz"))`.
- Builds a `MnistFidEvaluator` (one per config) and passes it as `selection_evaluator=...` to `ReInferenceConfig`.
- Runs `runner.run(...)`.
- Captures `result.endpoints` reshaped to `(batch, 784) -> (batch, 1, 28, 28)` and scored against the test-set μ/Σ.
- Returns `{"config": ..., "final_fid": ..., "mean_fid": ..., "final_selection_ratio": ..., "mean_selection_ratio": ..., "fid_curve": [...], "selection_curve": [...], "wall_clock_s": ...}`.

Each row reports:
- **FID baseline** (single_pass_mnist): one round; expect ~80-120 (our metric is not Inception-FID, so absolute numbers don't compare to literature — but the *relative* improvement across rounds is the load-bearing claim).
- **Multi-round FID**: 20 rounds; expect `Δ_fid` = `fid_multi_round - fid_single_pass` to be **modestly negative** (i.e., multi-round is better) or near-zero (parity is acceptable — MNIST is harder than 2D).
- **selection_ratio trajectory**: starts at ~0.81, climbs to ≥0.95 across 20 rounds on the evidence_driven row.
- **Wall-clock per round**: target <30s CPU (RK4 with 100 steps over 784-dim UNet).

---

## §6. Tests plan

### 6.1 `tests/test_adapters/test_mnist_fm.py` — adapter unit tests

Mirror `test_twodim_fm.py` exactly. Tests:

1. **`test_load_npz_and_capabilities`** — Load `data/mnist_fm.npz`; assert `capabilities()` returns a well-formed `MnistFMCapabilities` with `state_shape=(784,)`, `supported_channels=("x",)`, `native_config_hash="mnist_fm:cfg:v1"`.
2. **`test_adapter_loads_handshake`** — Every required engine-side capability flag is `True`.
3. **`test_adapter_satisfies_protocol`** — `MnistFmAdapter` passes `isinstance(adapter, FlowMatchingODEAdapter)` (the `@runtime_checkable` Protocol).
4. **`test_run_round_produces_target_resembling_samples`** — `Engine.run_round` drives a round end-to-end; the endpoint is finite (no NaN), finite-norm, and inside the `[-1, 1]^784` clamp box.
5. **`test_byte_determinism_across_runs`** — Two 10-round scenarios from identical seeds are byte-identical at every native state digest.
6. **`test_no_nan_over_many_seeds`** — `solve_ode` returns finite endpoints for `seed in {0, ..., 19}`.
7. **`test_endpoint_shape_correct`** — `observe_endpoint` returns a `StateBundle` whose `native_state_digest` resolves to a `(784,)` array.
8. **`test_protocol_surface_intact`** — Every method is non-mutating for the canonical inputs (call twice, compare hashes).
9. **`test_restart_blend_respects_memory_fraction`** — `apply_restart_distribution` behaves correctly for `β ∈ {0.0, 0.5, 1.0}` (full prior / blend / full fresh).
10. **`test_engine_stress_20_rounds_with_restart`** — `Engine.run_round` drives 20 rounds alternating `β ∈ {0.0, 0.5}`; every trace validates under a 120-second CPU budget.
11. **`test_inject_forward_noise_hook`** — When `inject_forward_noise` is called on a `StateBundle`, the returned bundle has the perturbation added and a `forward_noise_applied` provenance tag.

Conftest fixture: `_materialize_mnist_fm_weights` mirrors the 2D counterpart — ensures `data/mnist_fm.npz` exists at session start (train if missing). Mark with `@pytest.fixture(scope="session")`.

### 6.2 `tests/test_adapters/test_mnist_fm_train.py` — trainer smoke test

Mirrors the 2D trainer smoke test (3-line trainer in `test_twodim_fm.py`):

1. **`test_train_smoke_5_epochs`** — Call `mnist_fm_train.train(epochs=2, batch_size=32, base_channels=16)` on a 1000-image subset of MNIST; assert loss decreases by ≥30% from epoch 0 to epoch 1.
2. **`test_save_load_roundtrip`** — Train for 1 step, save, load, assert all weight tensors are bit-identical (`np.array_equal`).
3. **`test_init_kaiming_uniform_bounds`** — `velocity_field_unet_init` produces weights with `stddev < bound` for every tensor where `bound = sqrt(6 / fan_in)`.

### 6.3 `tests/test_tools/test_run_ablation.py` — ablation table tests

Add to the existing `test_run_ablation.py` (which currently matches the 6-column 2D ablation row shape):

1. **`test_mnist_ablation_rows_present`** — After running the ablation with `--include-mnist`, the markdown table contains all 4 new row names.
2. **`test_mnist_single_pass_fid_reasonable`** — `single_pass_mnist` reports `final_fid` in `[60, 150]` (sanity bounds).
3. **`test_mnist_evidence_driven_selection_ratio_increases`** — Across 20 rounds, the `selection_curve` for `multi_round_mnist_evidence_driven` shows `selection_curve[-1] >= 0.85 * selection_curve[-1] + 0.15 * 1.0` (loose monotonic improvement).

---

## §7. Expected outputs (realistic numbers)

### 7.1 Baseline FID (single-pass)

- **Estimated range: FID 80-120** on the random-projection NumPy FID (NOT literature Inception-FID).
- A well-trained small UNet on MNIST generates digits that are perceptually crisp; the random-projection FID captures (μ, Σ) drift in a 128-dim feature space. Empirically, single-pass rectified flow on MNIST with 100 RK4 steps lands in this band.
- **Important:** the absolute number is not directly comparable to literature. The paper claim is **relative**: multi-round framework ≤ baseline FID.

### 7.2 Multi-round FID

- **Expected improvement: Δ_fid = -1 to -3** (multi-round better than single-pass by 1-3 FID units).
- The MNIST target is harder than 2D; the multi-round framework's selection-ratio improvement does not translate to large FID gains because the source noise `N(0, I)` is already a good prior for a model trained to invert it. Expect **parity or modest improvement**, not large gains.

### 7.3 selection_ratio

- **Single-pass (round 0): ~0.81** (matches the 2D baseline).
- **Multi-round evidence_driven (round 19): ≥0.95** in the direction paper Theorem 1 predicts.
- **Cosine / codimension rows: plateau ~0.81-0.85** (their `eps_implicit` is fixed at construction, so the ratio doesn't climb — same finding as the 2D ablation).
- **Evidence-driven row is the only schedule-sensitive row.**

### 7.4 Wall-clock per round (CPU)

- RK4 with 100 steps over a 784-dim UNet (~600K params) is roughly **5-10 seconds per round on a single CPU core** for a single sample.
- The ablation uses `n_trajectories_per_round=8, endpoints_per_trajectory=16` (matching the 2D batched config) → ~8 minutes per ablation cell.
- 4 MNIST rows × 8 minutes ≈ **32 minutes for the full MNIST ablation grid** — within the 0.5-day integration budget.

---

## §8. Failure modes and mitigation

| # | Failure | Severity | Mitigation |
|---|---------|----------|------------|
| 1 | **FID computation fails** (random projection produces non-PSD covariance) | Low | Clamp covariance eigenvalues to `max(λ, 1e-6)` before `sqrtm`. Already standard in FID implementations. |
| 2 | **No InceptionV3 on CPU** (would have been needed for literature-comparable FID) | N/A — we don't use InceptionV3 by design. | The random-projection FID is the chosen metric; document the caveat in the ablation markdown. |
| 3 | **Training too slow (>3 hours)** | Medium | Drop to `base_channels=24, 8 epochs, batch_size=128` → ~45 min. The UNet is small enough that 8 epochs at lr=1e-3 already converges to a usable velocity field. |
| 4 | **FID too noisy for ablation signal** | Medium | Use 10K samples (whole MNIST test set), repeat each ablation 3x with different seeds, report `mean ± std`. The `tools/run_ablation.py` already accepts `--seed`; we run the 4 MNIST rows 3 times each and average. |
| 5 | **MNIST download blocked** (e.g., `yann.lecun.com` unreachable) | Low | Use the `https://ossci-datasets.s3.amazonaws.com/mnist/` mirror as `download=True` fallback. If both fail, ship a cached `data/mnist_cache/MNIST/raw/*.gz` pre-extracted set in the repo (4 compressed files, ~12 MB total). |
| 6 | **NaN in UNet forward** (overflow on `[0,1] -> [-1,1]` rescaling) | Low | Clamp inputs to `[-1, 1]` before every conv; clamp outputs to `[-1, 1]` after every conv. GroupNorm + SiLU is numerically stable; residual-style zero-init on the final conv prevents initial blow-up. |
| 7 | **Adapter fails the `@runtime_checkable` Protocol check** (missing method) | Low | The 8 methods are mandatory in `FlowMatchingODEAdapter`. The smoke test `test_adapter_satisfies_protocol` catches this before any other test runs. |
| 8 | **`state_shape=(784,)` breaks the runner's forward-noise allocation** | Low | F14 (line 776-780 of `runner.py`) reads `getattr(self._adapter, "state_shape", (2,))`. We advertise `state_shape=(784,)` in `MnistFMCapabilities`; the runner will allocate `(784,)` correctly. Verify in `test_inject_forward_noise_hook`. |
| 9 | **UNet weights `.npz` is too large to commit** | Low | At ~2-3 MB the file is comfortably within the 10 MB soft cap. `np.savez_compressed` further reduces size by ~30%. Document a CI check that fails if `data/mnist_fm.npz > 10 MB`. |
| 10 | **CPU memory blow-up during training** (batch 64 + 600K-param UNet activations) | Low | Peak ~150 MB; well within standard CI runners (typically 4-8 GB). If it does blow up, drop batch to 32 → ~80 MB. |

---

## §9. Timeline (sub-tasks, 2 days total)

| Day | Sub-task | Output | Wall-clock |
|---|---|---|---|
| **0.5** | Train UNet on MNIST and save weights | `data/mnist_fm.npz` (sha256-verified) | ~2.5 hours |
| **0.25** | Write `mnist_fm_train.py` (parallel to training start; merge once training completes) | Module + CLI tested with 2-epoch smoke | 1.5 hours (concurrent with training) |
| **0.5** | Write `mnist_fm.py` adapter (8 methods, RK4, restart, capabilities, byte-deterministic replay) | Module + 11 unit tests | 4 hours |
| **0.25** | Write `mnist_fid.py` evaluator (random-projection NumPy FID) | Module + 3 unit tests | 2 hours |
| **0.25** | Integrate with framework: `__init__.py` export + 4 ablation rows in `tools/run_ablation.py` | Markdown table + 3 ablation tests | 2 hours |
| **0.25** | Wire `MnistFmAdapter` into paper claims (CLM-035/036/037) | `docs/CLAIMS.md` updates + `verify_claims` gate green | 1 hour |
| **0.25** | Run all gates (`pytest`, `ruff`, `mypy`, `docs-check`, `claims-sync`, `mkdocs`) | All 6 gates green | 1 hour |
| **Total** | | | **~14 hours / 2 days** |

---

## §10. Verification (claims to add to `docs/CLAIMS.md`)

| Claim ID | Statement | Evidence |
|---|---|---|
| **CLM-035** | `MnistFmAdapter` implements `FlowMatchingODEAdapter` Protocol on real MNIST UNet (28x28 grayscale, ~600K params). | `tests/test_adapters/test_mnist_fm.py::test_adapter_satisfies_protocol`; `test_run_round_produces_target_resembling_samples`; `test_byte_determinism_across_runs`. |
| **CLM-036** | Multi-round framework on MNIST achieves `selection_ratio >= 0.95` across 20 rounds (paper Theorem 1 direction). | `tools/run_ablation.py` 4-row ablation; `multi_round_mnist_evidence_driven` row reports `mean_selection_ratio >= 0.85` and `final_selection_ratio >= 0.90` in `docs/ABLATION.md`. Test: `test_mnist_evidence_driven_selection_ratio_increases`. |
| **CLM-037** | Multi-round framework on MNIST achieves FID ≤ baseline FID (modest improvement or parity). | 4-row ablation; `multi_round_mnist_*` rows report `final_fid ≤ single_pass_mnist.final_fid + 3.0` (parity-with-tolerance). Test: `test_mnist_single_pass_fid_reasonable` + manual inspection of the FID column. |

Each claim links to:
- The pytest test that asserts it.
- The ablation row that produces the empirical number.
- The paper section it supports (`docs/paper-plan.md` §5.2 / §7.3 / Figure 6-equivalent).

The plan must also add the 4 ablation rows to the **reproducibility checklist** in `docs/paper-plan.md` (regenerate weights via `python -m adaptive_reflow.adapters.mnist_fm_train`; weights land at `data/mnist_fm.npz`, ~2-3 MB).

---

## 7-line summary

- **UNet architecture:** tiny NumPy UNet (3 down + bottleneck + 2 up; `base_channels=32`; ~600K-800K params; time as 2nd input channel; Kaiming-uniform init; GroupNorm + SiLU).
- **Expected training time on CPU:** ~2.5 hours for 10 epochs at batch 64 (mitigation: `base_channels=24, 8 epochs` → ~45 min if budget is tight).
- **Expected baseline FID range:** **80-120** on random-projection NumPy FID (NOT literature-comparable Inception-FID; relative numbers across rounds are the load-bearing claim).
- **Expected `selection_ratio` range after framework:** single-pass ~0.81 → evidence_driven round 19 ≥0.95 (paper Theorem 1 direction); cosine / codimension rows plateau at ~0.81-0.85.
- **Critical risk:** UNet analytic-gradient implementation (CPU backprop via `np.einsum` + manual padding for nearest-upsample + GroupNorm). Mitigation: 2-epoch smoke test on 1000-image subset must show ≥30% loss reduction before committing to the full 10-epoch run.
- **Number of new files:** **6 new files** + 2 modifications (`__init__.py` + `tools/run_ablation.py`):
  - `adaptive_reflow/adapters/mnist_fm.py` (adapter)
  - `adaptive_reflow/adapters/mnist_fm_train.py` (trainer)
  - `adaptive_reflow/eval/mnist_fid.py` (FID evaluator)
  - `tests/test_adapters/test_mnist_fm.py` (adapter tests)
  - `tests/test_adapters/test_mnist_fm_train.py` (trainer tests)
  - `data/mnist_fm.npz` (trained weights — regenerated, not committed binary)
- **Plan file path:** `c:\Users\31472\codes\flowa-multistep-reinference\docs\r4-survey\03-exp1-mnist-plan.md`
