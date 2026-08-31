# Plug In Your Model — Adapter Walkthrough

<!-- skip-doc-check -->

> **Audience**: a researcher with one pre-trained SOTA flow-matching
# checkpoint who wants to evaluate FlowA's multi-round re-inference
# against a single-pass baseline on the same checkpoint.
>
> **Time budget**: ~1 hour for first-time setup; ~5 minutes per
# subsequent checkpoint once the wiring is in place.

This page is the **adapter side** of the
[`r4-survey/07-sota-experiment-protocol.md`](./r4-survey/07-sota-experiment-protocol.md)
runbook. The protocol describes the seven steps end-to-end; this page
drills into **Step 2** (build the adapter) and **Step 4**
(compute baseline + framework comparison), with copy-paste code.

---

## What "plug in your model" means here

The framework speaks **one language**: the eight-method
[`FlowMatchingODEAdapter`](./ADAPTER_INTERFACE_SPEC.md) Protocol. Every
flow-matching model — a 2-D rectified flow, a CIFAR UNet, a latent
Stable-Diffusion-3 backbone, a discrete-state CTMC — plugs in by
implementing these eight methods against its own native checkpoint.
The framework's algorithm layer (16 schedulers, 5 drivers, 8 merge
operators, 6 blenders) is then **identical** across model families.

The five steps in this page:

1. **Pick a checkpoint** (URL or self-trained).
2. **Wrap it as an adapter** (using the template at
   [`r4-survey/08-adapter-template.py`](./r4-survey/08-adapter-template.py)).
3. **Wire it into `ReInferenceRunner`**.
4. **Run baseline vs framework comparison** with
   [`tools/run_sota_comparison.py`](../tools/run_sota_comparison.py).
5. **Compute FID** (image models) or W2 (2-D models).

---

## Step 1 — Pick a checkpoint

Any flow-matching checkpoint will do. The framework is **inference-only**:
training is your contribution. Three typical paths:

| Path | Source | License |
|---|---|---|
| **Your own published checkpoint** | `path/to/your_model.ckpt` | yours |
| **`huggan/cifar10-resnet-flow-matching`** on HuggingFace | HF Hub token required | Apache-2.0 |
| **`gnobitab/cifar10-rf`** (rectified-flow CIFAR-10 UNet) | Google Drive | CC-BY-NC-4.0 |
| **Self-train** | Run the framework's `TwoDimFMAdapter.train()` for ~5 min | n/a |

Two requirements:

1. **Save weights as a NumPy `.npz`** (or translate from
   `safetensors` / `state_dict` / `eqx` once). The adapter template
   assumes NumPy access. Translation recipe:

   ```python
   import numpy as np, torch
   state = torch.load("/path/to/your_model.ckpt", map_location="cpu")
   np.savez(
       "/path/to/your_model.npz",
       **{k: (v.cpu().numpy() if hasattr(v, "cpu") else v) for k, v in state.items()},
   )
   ```

2. **Inspect the shapes**. Record the answers in the table below —
   you'll paste them into the adapter in Step 2.

   ```python
   >>> import numpy as np
   >>> data = np.load("/path/to/your_model.npz")
   >>> list(data.keys())                                         # what tensors?
   >>> {k: data[k].shape for k in data.files}                   # what shapes?
   ```

   | Field | Your answer |
   |---|---|
   | **Model class** (UNet / MLP / DiT / …) | |
   | **Input noise shape** (the prior's tensor shape) | e.g. `(1, 3, 32, 32)` for CIFAR |
   | **Output shape** (`v(x, t)` shape) | usually matches input |
   | **Sampling steps** (what the original codebase used) | e.g. 50 / 100 / 250 |
   | **Original task** + **original metric** | e.g. CIFAR-10 image generation, FID |

---

## Step 2 — Wrap it as an adapter

Copy the template:

```bash
# 1. Copy the template into your project's adapters directory.
cp docs/r4-survey/08-adapter-template.py \
   your_project/adapters/my_sota_adapter.py

# 2. Rename the class (default: `MySotaModelAdapter` -> `MyCIFARAdapter`)
# 3. Open the file; fill in the five TODO-marked methods.
```

The template ships **stubbed bodies for the 5 methods you must
implement** and **working defaults for the 3 methods that almost
never need custom logic**:

| # | Method | Implement? | Why |
|---|---|---|---|
| 1 | `capabilities()` | default (fill `MY_SOTA_*` constants) | Returns the cached `AdapterCapabilities`. |
| 2 | `build_initial_state(*, batch_id, sample_id)` | **stub** | Sample `x0 ~ N(0, I)`, store under SHA-256 digest, return a `StateBundle`. |
| 3 | `export_endpoint(state)` | **stub** | Post-observation side-effect (optional; default is pass-through). |
| 4 | `detach_and_validate_endpoint(bundle)` | default | Asserts `detach_proof=True`; re-validates. |
| 5 | `apply_restart_distribution(state, policy)` | default | Linear blend `m * prior + (1-m) * fresh`. |
| 6 | `compose_condition(bundle, delta)` | **stub** | Inject model-specific `num_steps`, `integrator_config_hash`, `calibration_artifact_hash`. |
| 7 | `solve_ode(state, condition, *, seed)` | **stub** | Port your model's forward step (Euler / Heun / RK4 / DPM-Solver / UniPC). |
| 8 | `observe_endpoint(trace, state)` | **stub** | Read final trajectory point, advance `source_round`, return `StateBundle`. |

### 2a. Fill the constants block

Edit the top of `my_sota_adapter.py`:

```python
MY_SOTA_CHANNELS: tuple[str, ...] = ("rgb",)             # <- your model's output vocab
MY_SOTA_CONFIG_HASH: str = "your_model:cfg:v1"          # <- stable hash
MY_SOTA_CONFIG_VERSION: str = "0.1.0"                   # <- free-form
MY_SOTA_CHANNEL_DOMAINS: Mapping[str, str] = {"rgb": "continuous"}
# F14: declare your model's native state shape so the runner can size
# the prior array. Examples:
#   (3, 32, 32)        CIFAR-10 RGB image
#   (4, 64, 64)        latent 4-channel 64x64
#   (1024,)            MLP on a flat 1-D vector
```

> **What `MY_SOTA_CONFIG_HASH` should be**: a stable string derived
> from `(model architecture + version + checkpoint digest)`. Two
> adapters that load the same checkpoint must produce byte-identical
> `MY_SOTA_CONFIG_HASH`. Use SHA-256 of the
> `.npz` file's bytes if you don't have a model-versioning scheme.

### 2b. Implement `build_initial_state`

The method's job: sample `x0 ~ N(0, I)` (or whatever prior your model
expects), store it under a SHA-256 digest in the LRU cache, and
return a `StateBundle` whose `native_state_digest` matches the
cached entry.

```python
def build_initial_state(self, *, batch_id: str, sample_id: str) -> StateBundle:
    seed = _seed_from_ids(str(batch_id), str(sample_id), int(self._seed_offset) + 0)
    rng = np.random.default_rng(seed)
    x0 = rng.standard_normal(YOUR_MODEL_STATE_SHAPE).astype(np.float64)
    digest = _digest_state({
        "kind": "initial",
        "batch_id": str(batch_id),
        "sample_id": str(sample_id),
        "x0": x0.tolist(),
    })
    self._put_native_state(digest, {"x0": x0, "source_round": 0})
    return StateBundle(
        channels={ChannelName("rgb"): _make_ref("initial", batch=batch_id, sample=sample_id)},
        masks={},
        batch_id=str(batch_id), sample_id=str(sample_id),
        reference_frame="world", normalization="none",
        source_round=0, detach_proof=True,
        native_state_digest=digest,
        provenance=("your_model@v1",),
        capability_token=self.capabilities(),
    )
```

### 2c. Implement `solve_ode` (the model-specific core)

This is the only method that depends on your model's actual forward
step. Replace the stub with the integrator your model's original
codebase used:

```python
def solve_ode(
    self, state: StateBundle, condition: ODEConditionDelta, *, seed: int,
) -> ODEIntegratorTrace:
    ok, errs = validate_state_bundle(state)
    if not ok:
        raise CapabilityMissingError("validate_state_bundle", context=",".join(errs))

    prior_entry = self._resolve(state.native_state_digest)
    if prior_entry is None:
        raise CapabilityMissingError("missing_native_state",
                                     context=state.native_state_digest)
    x0 = np.asarray(prior_entry["x0"], dtype=np.float64)

    num_steps = int(condition.delta_spec.get("num_steps", self._num_steps))
    t_grid = np.linspace(0.0, 1.0, num_steps + 1, dtype=np.float64)

    x_cur = x0.copy()
    for i in range(1, t_grid.size):
        t_cur, t_next = float(t_grid[i - 1]), float(t_grid[i])
        h = float(t_next - t_cur)
        v = _velocity_field(self._weights, x_cur, t_cur)   # <- port your model
        x_cur = x_cur + h * v                               # <- or RK4 stages etc.

    if YOUR_MODEL_CLAMP is not None:
        x_cur = np.clip(x_cur, -YOUR_MODEL_CLAMP, YOUR_MODEL_CLAMP)

    traj_digest = _digest_state({
        "kind": "trajectory",
        "src_digest": state.native_state_digest,
        "num_steps": int(num_steps),
        "x0": x0.tolist(),
    })
    self._put_native_state(traj_digest, {"x_final": x_cur, "t_final": 1.0})
    cfg_blob = repr(("your_model_config", int(num_steps), int(seed))).encode("utf-8")
    return ODEIntegratorTrace(
        steps=int(num_steps), accept_rate=1.0,
        native_state_digest=str(traj_digest),
        integrator_config_hash=hashlib.sha256(cfg_blob).hexdigest(),
    )
```

> **Determinism**: the runner calls `solve_ode` with the *same*
> `seed` for the *same* `(state, condition)` pair. Your integrator
> MUST produce byte-identical outputs for byte-identical inputs — pass
> `seed` to your model's seeding kwargs and do **not** reseed inside
> the inner loop.

### 2d. Implement `observe_endpoint`

```python
def observe_endpoint(self, trace: ODEIntegratorTrace, state: StateBundle) -> StateBundle:
    ok, errs = validate_state_bundle(state)
    if not ok:
        raise CapabilityMissingError("validate_state_bundle", context=",".join(errs))
    traj_entry = self._resolve(trace.native_state_digest)
    if traj_entry is None:
        raise CapabilityMissingError("missing_native_state",
                                     context=trace.native_state_digest)
    x_final = np.asarray(traj_entry["x_final"], dtype=np.float64)
    endpoint_digest = _digest_state({
        "kind": "endpoint",
        "traj_digest": trace.native_state_digest,
        "src_digest": state.native_state_digest,
        "x_final": x_final.tolist(),
        "t_final": 1.0,
    })
    self._put_native_state(endpoint_digest, {"x": x_final, "t": 1.0})
    next_round = int(state.source_round) + 1
    return StateBundle(
        channels=dict(state.channels), masks=dict(state.masks),
        batch_id=str(state.batch_id), sample_id=str(state.sample_id),
        reference_frame=str(state.reference_frame),
        normalization=str(state.normalization),
        source_round=int(next_round), detach_proof=True,
        native_state_digest=str(endpoint_digest),
        provenance=tuple(state.provenance) + ("your_model_observed",),
        capability_token=self.capabilities(),
    )
```

### 2e. Validate the adapter

Two smoke tests before you trust the adapter on a long run:

```python
from adaptive_reflow.frame.engine import Engine
from your_project.adapters.my_sota_adapter import MyCIFARAdapter

adapter = MyCIFARAdapter(weights_path="data/your_model.npz", num_steps=50)
caps = Engine(adapter=adapter).handshake(adapter)
print("OK", caps.supported_channels, caps.has_ode_integration_surface)
# Must print: OK (rgb,) True

# 10-round smoke test
from adaptive_reflow.algorithm.runner import ReInferenceRunner, ReInferenceConfig
result = ReInferenceRunner(adapter=adapter).run(
    ReInferenceConfig(n_rounds=10, seed=0, channels=("rgb",))
)
assert __import__("numpy").isfinite(result.endpoints).all(), "NaN/Inf in endpoints!"
print("smoke OK; endpoint shape:", result.endpoints.shape)
```

If either fails, jump to [Troubleshooting](#troubleshooting) below.

---

## Step 3 — Wire it into `ReInferenceRunner`

`ReInferenceRunner` is the canonical multi-round driver. It takes
your adapter, a scheduler, and a config, and returns per-round
endpoints + metrics.

```python
from adaptive_reflow.algorithm.runner import ReInferenceRunner, ReInferenceConfig
from adaptive_reflow.algorithm.scheduler import (
    CosineAnnealScheduler, CodimensionSheetScheduler,
    EvidenceDrivenScheduler, FreeTrajScheduler,
)
from adaptive_reflow.contracts import CosineScheduleConfig

adapter = MyCIFARAdapter(weights_path="data/your_model.npz", num_steps=50)

# 4-scheduler ablation (canonical paper-claim run)
schedulers = {
    "cosine":    CosineAnnealScheduler(CosineScheduleConfig(n_rounds=20, n_min=0.0, n_max=1.0)),
    "codim":     CodimensionSheetScheduler(cycle_length=20),
    "evidence":  EvidenceDrivenScheduler(cycle_length=20),
    "freetraj":  FreeTrajScheduler(amplitude=0.05, period=4),
}

results = {}
for name, sched in schedulers.items():
    runner = ReInferenceRunner(adapter=adapter, scheduler=sched)
    results[name] = runner.run(ReInferenceConfig(
        n_rounds=20, seed=42, channels=("rgb",),
    ))
```

For each scheduler you now have:

- `result.endpoints` — shape `(n_rounds, *YOUR_MODEL_STATE_SHAPE)`.
- `result.per_round_metrics` — dict mapping `round → {metric_name: value}`.
- `result.ledger_rows` — round-by-round ledger chain (verifiable via
  `verify_ledger_chain(result.ledger_rows) == (True, "")`).

---

## Step 4 — Run baseline vs framework comparison

The framework ships a one-shot driver at
[`tools/run_sota_comparison.py`](../tools/run_sota_comparison.py):

```bash
PYTHONPATH=. ./.venv/Scripts/python.exe tools/run_sota_comparison.py \
    --adapter-class your_project.adapters.my_sota_adapter:MyCIFARAdapter \
    --n-samples 200 --n-rounds 20 --output-dir ./my_sota_out
```

It walks the four schedulers, generates per-scheduler `.npz` files
under `./my_sota_out/`, and writes a `comparison.md` summary table.

### Manual baseline

The **baseline** is the same model, same checkpoint, single-pass
inference (no FlowA re-inference). Compute it with your model's
original sampling loop:

```python
import numpy as np
images = []
for i in range(1000):
    x = your_sampling_function(checkpoint, num_steps=50, seed=i)
    images.append(x)
images = np.stack(images)                       # (1000, 3, 32, 32)
np.savez("/tmp/your_model_baseline.npz", samples=images)
```

> **Important**: keep `num_steps` and the seed schedule identical to
> what your model's original sampling code uses. The baseline is
> *that* sampling loop, not something FlowA invented. FlowA's job is
> to improve on it via multi-round re-inference.

---

## Step 5 — Compute FID (image models)

The framework ships a CPU-runnable FID harness at
[`tools/compute_cifar_fid.py`](../tools/compute_cifar_fid.py). It
expects a torch-capable venv; the canonical isolated venv is
`C:/Users/31472/AppData/Local/Temp/flowa_fid_env` (or create your
own: `python -m venv flowa_fid_env && pip install torch==2.4.1+cpu pytorch-fid`).

```bash
# 1. Baseline FID
PYTHONPATH=. ./.venv/Scripts/python.exe tools/compute_cifar_fid.py \
    --gen /tmp/your_model_baseline.npz \
    --ref data/your_test_set.npz \
    --out /tmp/your_model_baseline_fid.txt

# 2. Framework FID per scheduler (uses last-round endpoints as the
#    multi-round sample set; pad by tile if n_rounds < 1000)
PYTHONPATH=. ./.venv/Scripts/python.exe tools/compute_cifar_fid.py \
    --gen ./my_sota_out/your_model_framework_cosine.npz \
    --ref data/your_test_set.npz \
    --out ./my_sota_out/your_model_cosine_fid.txt

# 3. Aggregate
python - <<'PY'
fid = lambda p: float(open(p).read().strip())
print(f"baseline   FID = {fid('/tmp/your_model_baseline_fid.txt'):.4f}")
print(f"cosine     FID = {fid('./my_sota_out/your_model_cosine_fid.txt'):.4f}")
print(f"codim      FID = {fid('./my_sota_out/your_model_codim_fid.txt'):.4f}")
print(f"evidence   FID = {fid('./my_sota_out/your_model_evidence_fid.txt'):.4f}")
print(f"freetraj   FID = {fid('./my_sota_out/your_model_freetraj_fid.txt'):.4f}")
PY
```

If `torch` is unavailable, the framework ships a NumPy random-projection
FID that works on any machine but is less accurate. See §5 of the
SOTA protocol for the trade-off.

### Expected results

For a published SOTA image-flow model with `num_steps=50` and ~1 K
samples per run, the published 2-D RF baseline result is:

| Scheduler | Mean FID | Δ vs Baseline |
|---|---|---|
| baseline (single-pass) | X | — |
| CosineAnnealScheduler | Y₁ | Y₁ − X |
| CodimensionSheetScheduler | Y₂ | Y₂ − X (negative = improvement) |
| EvidenceDrivenScheduler | Y₃ | Y₃ − X |
| FreeTrajScheduler | Y₄ | Y₄ − X |

The paper claim from `docs/paper-plan.md` §4 is *"framework *can*
improve"*, not *"always improves"*. Honest reporting:

- **≥ 1–2 of 4 schedulers beat the baseline** = publishable positive.
- **All 4 ≥ baseline** = strong result (rare; report honestly).
- **All 4 > baseline** = honest negative result (also publishable).

The paper Theorem-1-driven schedulers (CodimensionSheet,
EvidenceDriven) have a theoretical reason to improve on Theorem-1-style
metrics; the heuristic ones (Cosine, FreeTraj) are ablation rows.

---

## Troubleshooting

Six categories of failure that bite a fresh adapter.

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | `CapabilityMissingError: has_ode_integration_surface` at handshake | Adapter advertises the capability but the method body is the stub | Either implement the method or set the corresponding `has_*=False` in the capability block. |
| 2 | `result.endpoints.shape` is `(20,)` instead of `(20, 3, 32, 32)` | `build_initial_state` returns the wrong `state_shape` | Match `MY_SOTA_STATE_SHAPE` (or equivalent) to your model's output, not its input. The engine flattens for you. |
| 3 | `result.endpoints.std(axis=0)` is nonzero across rounds for the same input | `solve_ode` reseeds RNG per call | Pass `seed` to your model's seeding kwargs *once* per round; do **not** reseed inside the integrator loop. |
| 4 | `np.isnan(result.endpoints).any() == True` after round 10+ | Unbounded trajectory growth or numerical instability | Set `MY_SOTA_CLAMP` to a reasonable bound (e.g. `1.0` for `[-1, 1]` images). Check the round where NaN first appears and inspect that round's input. |
| 5 | `ModuleNotFoundError: No module named 'torch'` when running FID | Framework venv has no torch by design | Use the isolated `flowa_fid_env` venv (already pre-built) or fall back to the NumPy random-projection FID. |
| 6 | InceptionV3 weights won't download (corporate firewall) | `github.com` blocked | Pre-download: `curl -L https://github.com/mseitzer/pytorch-fid/releases/download/fid_weights/pt_inception-2015-12-05-6726825d.pth -o ~/.cache/torch/hub/checkpoints/pt_inception-2015-12-05-6726825d.pth` |

Two less common ones:

- **`selection_ratio` missing from `per_round_metrics`** — you forgot
  to pass `selection_evaluator=...` to `ReInferenceConfig`.
  `EvidenceDrivenScheduler` needs it.
- **`AssertionError: ledger_chain_integrity_check_failed:...`** —
  usually a non-pure `apply_restart_distribution` (mutates inputs, or
  uses non-deterministic RNG). Re-run that round's adapter inputs in
  isolation.

---

## What success looks like

- **Adapter validates** the capability handshake on the first try.
- **10-round smoke test** has no NaN / Inf, `endpoints.shape` matches
  `MY_SOTA_STATE_SHAPE`, ledger chain verifies.
- **At least 1–2 of 4 schedulers** show strictly better metric than the
  baseline. Reporting 0/4 is a publishable negative result.
- **No NaN / Inf** in any per-round endpoint.
- **Ledger chain** verifies intact (`verify_ledger_chain(...) == (True, "")`).
- **Selection ratio** (where applicable) trends monotonically toward
  1.0 as rounds progress (paper Theorem 1 direction).

For the full seven-step protocol — including FID harness details,
common pitfalls, expected output artifacts, and sandbox limitations —
see
[`r4-survey/07-sota-experiment-protocol.md`](./r4-survey/07-sota-experiment-protocol.md).

---

## See also

- [`ADAPTER_INTERFACE_SPEC.md`](./ADAPTER_INTERFACE_SPEC.md) — full
  eight-method Protocol contract.
- [`r4-survey/07-sota-experiment-protocol.md`](./r4-survey/07-sota-experiment-protocol.md)
  — the seven-step SOTA runbook.
- [`ALGORITHMS.md`](./ALGORITHMS.md) — pick the right scheduler for
  your task.
- [`adaptive_reflow/adapters/twodim_fm.py`](../adaptive_reflow/adapters/twodim_fm.py)
  — the canonical real-model reference implementation.
- [`adaptive_reflow/adapters/toy_linear.py`](../adaptive_reflow/adapters/toy_linear.py)
  — the smallest possible adapter (≤ 60 LOC).

---

## Plug-in catalogue

The framework's adapter registry currently ships the following
production adapters (see
[`adaptive_reflow/adapters/__init__.py`](../adaptive_reflow/adapters/__init__.py)
for the canonical re-exports):

| Adapter | Channels | `state_shape` | Mode | License |
|---|---|---|---|---|
| `TwoDimFMAdapter` | `xy` | `(2,)` | NumPy | n/a (synthetic trainer) |
| `RectifiedFlowCIFARAdapter` | `image` | `(3, 32, 32)` | torch / synthetic | depends on checkpoint |
| `LuminaImage20Adapter` | `latent`, `text_condition` | `(16, 128, 128)` | torch (diffusers) / synthetic | Apache-2.0 |
| `ReferenceFlowAAdapter` | `(model-specific)` | model-specific | torch | Apache-2.0 |
| `FlowMol3Adapter` | molecule channels | model-specific | torch | MIT |
| `ToyLinearAdapter`, `ToyGaussianAdapter` | various | various | NumPy | n/a |

### Lumina-Image 2.0

```python
from adaptive_reflow.adapters.lumina_image_2_0_adapter_lumina_image_2_0 import (
    LuminaImage20Adapter,
    default_lumina_image_2_0_adapter,
)

# Synthetic mode (no checkpoint, no torch) -- protocol conformance.
adapter = LuminaImage20Adapter(
    weights_path=None, force_mode="synthetic", num_steps=2
)

# Torch mode (requires diffusers + transformers + the published
# Alpha-VLLM/Lumina-Image-2.0 checkpoint).
adapter = default_lumina_image_2_0_adapter(
    weights_path=Path("data/Lumina-Image-2.0"),
    force_mode="torch",
    num_steps=50,
)
```

Per-model `mechanism_id`: `lumina_image_2_0_flow_matching` (stamped
on every round trace alongside the canonical writer authority
`inference.adaptive_reflow`).