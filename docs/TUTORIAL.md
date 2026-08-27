# Tutorial — Writing your own adapter

This is the **worked-example** companion to
[ADAPTER_INTERFACE_SPEC.md](./ADAPTER_INTERFACE_SPEC.md). The spec
describes the universal contract every adapter must satisfy; this
tutorial walks through one **non-toy, real-model, CPU-runnable**
adapter end-to-end — `TwoDimFMAdapter` — so adapter authors can see
how the contract is wired up against a real velocity-field network.

The tutorial is organised as a single worked example that progressively
goes from "load pre-trained weights" to "score the round with a real
evaluator". Each step is self-contained; you can stop after any step
and still have a runnable adapter.

---

## Worked example — `TwoDimFMAdapter` end-to-end

This example uses the canonical pre-trained weights shipped under
`data/` and the canonical evaluator shipped under
`adaptive_reflow.eval.twodim_fm_evaluator`. The whole pipeline runs on
a laptop CPU in a few seconds; no GPU, no PyTorch, no external
services.

### Worked example — Step 1. Install the optional extra

`TwoDimFMAdapter` is the only module under `adaptive_reflow.adapters`
that imports NumPy at runtime, so the framework keeps NumPy / SciPy
behind an opt-in extra. Install it with:

```bash
pip install -e .[flow_matching]
```

This installs `numpy>=1.24` and `scipy>=1.10` (see
`pyproject.toml [project.optional-dependencies].flow_matching`). The
rest of the framework remains stdlib-only.

### Worked example — Step 2. Load the pre-trained `.npz` weights

The shipped `data/twodim_fm_*.npz` files are the **only** artifact the
runtime adapter consumes at module load. Each file holds six NumPy
arrays (`W1, b1, W2, b2, W3, b3`) that define the velocity-field MLP:

```python
from pathlib import Path
import numpy as np

weights_path = Path("data/twodim_fm_two_moons.npz")
with np.load(weights_path) as data:
    W1, b1 = data["W1"], data["b1"]
    W2, b2 = data["W2"], data["b2"]
    W3, b3 = data["W3"], data["b3"]

assert W1.shape == (3, 64) and W3.shape == (64, 2), (
    "Unexpected velocity-MLP shape — did the trainer change?"
)
```

`TwoDimFMAdapter` re-binds the activation between ReLU (trainer) and
Tanh (runtime), but the weight shapes and key names are identical, so
the `.npz` files are byte-compatible across the trainer/runtime
boundary. The two shipped files are ~2 kB each:

| File | Target distribution |
|---|---|
| `data/twodim_fm_two_moons.npz` | `target="two_moons"` |
| `data/twodim_fm_eight_gaussians.npz` | `target="eight_gaussians"` |

### Worked example — Step 3. Build the adapter

`TwoDimFMAdapter` is the standard concrete implementation of
`FlowMatchingODEAdapter` for the 2D rectified-flow model. It exposes
all eight Protocol methods (`build_initial_state`,
`export_endpoint`, `detach_and_validate_endpoint`,
`apply_restart_distribution`, `compose_condition`, `solve_ode`,
`observe_endpoint`, `capabilities`).

```python
from pathlib import Path
from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter

adapter = TwoDimFMAdapter(
    weights_path=Path("data/twodim_fm_two_moons.npz"),
    target="two_moons",
    integrator="rk4",       # "rk4" (default) or "dormand_prince"
    num_steps=100,          # integration steps on t ∈ [0, 1]
)
# Capability handshake: the engine calls this exactly once at registration.
caps = adapter.capabilities()
assert caps.has_ode_integration_surface
assert caps.has_restart_boundary
assert caps.supported_channels == ("xy",)
```

The constructor fails closed on unknown targets, unknown integrators,
or non-positive step counts. The default weight path resolution looks
under `data/` when `weights_path=None`.

### Worked example — Step 4. Build the engine

`Engine` is the model-family-agnostic orchestrator. It accepts the
adapter via its capability handshake and drives one round at a time:

```python
from adaptive_reflow.frame.engine import Engine

engine = Engine()
# Run the capability handshake exactly once at registration.
caps = engine.handshake(adapter)
assert caps.native_config_hash == "twodim_fm:cfg:v1"
```

`Engine` is **stateless**: each `run_round` invocation is a pure
function of its inputs plus the adapter's Protocol surface. This
property is what makes round-to-round paired evaluation
(DTB-R7 / DTB-R8) reproducible.

### Worked example — Step 5. Run five rounds with `restart_beta=0.5`

The `FinalRestartPolicy` is the per-channel beta schedule. We pin
`beta_by_channel["xy"] = 0.5` so the engine blends **50% memory +
50% fresh noise** at each round boundary (the adapter's
`_blend_endpoint_with_prior` formula maps `m = 1 - beta`).

```python
from adaptive_reflow.contracts.authority import FinalRestartPolicy
from adaptive_reflow.contracts import ChannelName, FactorValue

policy = FinalRestartPolicy(
    policy_id="tutorial-twodim-policy",
    run_id="tutorial-twodim-run",
    beta_by_channel={ChannelName("xy"): FactorValue(0.5)},
    alpha_by_channel={ChannelName("xy"): FactorValue(1.0)},
    fresh_noise_floor_by_channel={ChannelName("xy"): FactorValue(0.0)},
)

# Initial state: source N(0, I_2), seeded by (batch_id, sample_id).
bundle = adapter.build_initial_state(
    batch_id="tutorial-batch", sample_id="tutorial-sample"
)

# PhaseState + condition_delta are the other two engine.run_round inputs;
# see tests/test_adapters/test_twodim_fm.py for the canonical construction.
```

Run five rounds in a loop:

```python
from adaptive_reflow.adapters.twodim_fm import TWODIM_FM_NUM_STEPS

endpoints: list[tuple[float, float]] = []
for r in range(5):
    result = engine.run_round(
        round_index=r,
        phase_state=...,                 # your phase-state fixture
        bundle=bundle,
        adapter=adapter,
        policy=policy,
        condition_delta=...,             # num_steps=TWODIM_FM_NUM_STEPS
        seed=42 + r,
    )
    # The engine returns an `EngineRoundResult`; the round trace carries
    # the integrator trace, the audit codes, and the detached flag.
    assert result.round_trace.detached
    endpoints.append(
        (float(result.endpoint_xy[0]), float(result.endpoint_xy[1]))
    )
    bundle = result.next_bundle  # for the next round's input
```

After five rounds the adapter has produced five endpoints sampled from
the (approximate) two-moons distribution. Each endpoint is finite and
inside the bounding box `[-3, 3]^2` because of the
`TWODIM_FM_CLAMP = 5.0` overflow clamp and the RK4 integrator's
byte-deterministic stability.

### Worked example — Step 6. Score the round with `TwoDimFMEvaluator`

`TwoDimFMEvaluator` is the canonical "real replay-through-adapter"
evaluator. It owns one `TwoDimFMAdapter` instance (with the same
weights) and, on every `evaluate` call, replays the adapter's
`solve_ode` for `n_gen` endpoints and compares them against `n_ref`
analytic samples from the same target distribution.

```python
from adaptive_reflow.eval.twodim_fm_evaluator import TwoDimFMEvaluator

evaluator = TwoDimFMEvaluator(
    target="two_moons",
    n_gen=1000,     # endpoints generated by replaying solve_ode
    n_ref=1000,     # analytic samples drawn from the target sampler
    seed=42,
)

evidence = evaluator.evaluate(
    bundle, channel=ChannelName("xy"), seed=42,
)
# `support_coverage` is a FactorValue in the canonical four-evidence
# surface; the numerical `coverage_score` helper is the underlying
# Voronoi-fraction computation.
print("W2 =", 2.0 * (1.0 - float(evidence.raw_score)))
print("bounded_score =", float(evidence.bounded_score))
print("support_coverage =", float(evidence.support_coverage))
```

The three numerical diagnostics are computed as:

| Diagnostic | Definition |
|---|---|
| `wasserstein_2d` | `sqrt(W2_x^2 + W2_y^2)` — closed-form 2D Wasserstein distance via `scipy.stats.wasserstein_distance`. |
| `support_coverage` | Fraction of Voronoi cells (one per target mode) covered by at least one generated endpoint within `TWODIM_FM_COVERAGE_RADIUS = 0.3`. |
| `energy_distance` | Squared energy distance `E^2` via `scipy.spatial.distance.cdist` / `pdist`. |

The four `ChannelTransferEvidence` diagnostics are derived from these
as `raw_score = 1 - W2 / TWODIM_FM_W2_MAX` (with `TWODIM_FM_W2_MAX = 2.0`),
`bounded_score = clip(raw_score, 0, 1)`, `calibration_lower_bound = 0.95`,
and `perturbation_stability_lower_bound = 0.85`. The `oracle` method
exposes the same values as a plain dict, and the byte-for-byte equality
contract between `evaluate` and `oracle` is asserted in
`tests/test_eval/test_twodim_fm_evaluator.py`.

### Worked example — Step 7. Plot the endpoint samples (text description)

The framework deliberately ships **no** plotting dependency — NumPy and
SciPy are the only optional extras. To eyeball the trajectory you
either:

1. **Save the endpoints to disk** as `.npy` / `.csv` and import them
   into your favourite plotting tool (`matplotlib`, `plotly`, `vega`).
   The adapter's stored trajectory is keyed by `native_state_digest`
   and is reachable from the engine's `EngineRoundResult` via the
   adapter's internal state, so a small script can dump the full
   trajectory.
2. **Print a textual summary**: for each round, print the endpoint
   coordinates and the W2 / coverage / energy diagnostics.

A minimal textual summary looks like this (the numerical values are
illustrative):

```
round 0 endpoint = (0.91, -0.42)   W2=0.18   coverage=0.50   energy=0.07
round 1 endpoint = (0.83, -0.51)   W2=0.17   coverage=0.50   energy=0.06
round 2 endpoint = (1.02, -0.39)   W2=0.18   coverage=0.50   energy=0.07
round 3 endpoint = (0.88, -0.47)   W2=0.18   coverage=0.50   energy=0.07
round 4 endpoint = (0.79, -0.55)   W2=0.18   coverage=0.50   energy=0.07
```

For visual diagnostics, the recommended pattern is:

```python
import numpy as np

endpoints_arr = np.asarray(endpoints, dtype=np.float64)  # shape (5, 2)
np.save("endpoints.npy", endpoints_arr)
```

Then drop `endpoints.npy` into a notebook cell with `matplotlib.pyplot.scatter`.

---

## What's next?

Once you have a runnable `TwoDimFMAdapter` you have seen every load-
bearing piece of the universal contract: the capability handshake, the
eight Protocol methods, the channel vocabulary, the mixer selection
(`NoOpMixer`), the restart distribution, and the evaluator. Porting
the same shape to a new model family — Stable Diffusion 3 latent,
CTMC over discrete states, graph-flow over molecular graphs — is a
matter of:

1. **Pick the channel vocabulary** — see
   [ADAPTER_INTERFACE_SPEC.md §9](./ADAPTER_INTERFACE_SPEC.md) "Adding a
   new model — step-by-step recipe".
2. **Pick the right mixer** — `NoOpMixer`, `LatentConvexMixer`,
   `DiscreteIdentityMixer`, or a custom `RestartMixer` subclass.
3. **Implement the eight Protocol methods** — every method is total,
   deterministic, non-mutating, and raises `CapabilityMissingError` for
   capabilities the adapter does not advertise.
4. **Wire up the envelope / evaluator** — register them via
   `exposed_envelope_criteria` and `exposed_evaluators` in the
   `AdapterCapabilities` declaration.
5. **Run the test battery** —
   `tests/test_universal/test_adapter_universality.py` is the canonical
   pass condition.

The `TwoDimFMAdapter` is the smallest non-trivial real-model
implementation in the codebase; it is the **proof artifact** for
DTB-G3 phase 1 (real-model runtime) and the canonical reference for
adapter authors.
