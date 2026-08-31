# Tutorial — Quickstart (5–10 minutes)

This page is the **fastest on-ramp** to FlowA Multi-Step Re-Inference.
By the end of it you will have:

1. Installed the framework (stdlib + NumPy; no GPU required).
2. Run the full test battery to verify your install.
3. Loaded `TwoDimFMAdapter`, a real-model CPU-runnable adapter.
4. Run a 2-D rectified-flow experiment with one of the four canonical
   schedulers and read the per-round metrics.

For deeper material, see:

- [`PLUG_IN_YOUR_MODEL.md`](./PLUG_IN_YOUR_MODEL.md) — bring your own
  SOTA flow-matching checkpoint.
- [`ALGORITHMS.md`](./ALGORITHMS.md) — full catalog of the 16
  schedulers, 5 drivers, 8 merge operators, and 6 blenders.
- [`ADAPTER_INTERFACE_SPEC.md`](./ADAPTER_INTERFACE_SPEC.md) — the
  eight-method Protocol every adapter must satisfy.
- [`r4-survey/07-sota-experiment-protocol.md`](./r4-survey/07-sota-experiment-protocol.md)
  — the seven-step runbook for a four-scheduler ablation.

> **Reading time**: 5–10 minutes. **Wall time** (steps 1–4
> inclusive): ~3 minutes on a 4-core laptop.

---

## What you need

| Requirement | Notes |
|---|---|
| Python 3.12+ | The framework targets CPython 3.12. |
| A copy of this repo | `git clone …` |
| ~5 minutes of CPU time | Everything below runs on a laptop. |

The framework is **stdlib-only by design**. The only runtime dependency
the *core* (universal + contracts + frame + policy + schedule +
diagnostics + writer + eval) pulls in is the standard library; nothing
else is required to run this tutorial.

| Optional extra | When to install it | What it adds |
|---|---|---|
| `pip install -e .[flow_matching]` | When you exercise the **2-D rectified-flow adapter** (`TwoDimFMAdapter`) or compute Wasserstein-2 / energy-distance diagnostics | `numpy>=1.24`, `scipy>=1.10` |
| `pip install -e ".[cifar]"` | When you exercise the **CIFAR rectified-flow adapter** | `torch==2.4.1+cpu` (CPU-only). CIFAR support is **demo only** — not part of the unit-test battery. |
| `pip install -e .[mnist]` | When you exercise the **MNIST adapter** | `torch` (CPU). MNIST support is **demo only** — the adapter ships pre-trained weights but is not part of the unit-test battery. |
| `pip install -e .[test]` | When you run `pytest` | `pytest`, `hypothesis`, `pytest-benchmark` |
| `pip install -e .[docs]` | When you build the API reference with `mkdocs build --strict` | `mkdocs`, `mkdocstrings`, `pymdown-extensions`, `mkdocs-material` |

**Demo-only adapters** (`MnistFmAdapter`, the CIFAR UNet path): they
are present in the repo for end-to-end demonstration purposes; the
unit-test suite does not gate on them. If you only care about CPU
flow-matching math (the SOTA claim target), you only need
`numpy` + `scipy`.

---

## Step 1 — Clone and install (≈ 1 minute)

```bash
git clone https://github.com/silverenternal/flowa-multistep-reinference
cd flowa-multistep-reinference

# Create a venv (Windows path; use `python3 -m venv .venv` on Linux/macOS)
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e .[test,flow_matching]
```

> Linux/macOS: `source .venv/bin/activate` instead of the
> Windows activation step.

If `import adaptive_reflow` fails, the most common cause is forgetting
`PYTHONPATH=.` — the package's top-level layout has no
`__init__.py` at the repo root, so Python looks for subpackages
(`adaptive_reflow.frame`, `adaptive_reflow.universal`, …) under the
repo root.

```bash
# Verify the import path is right (should print "<class … Engine>")
PYTHONPATH=. ./.venv/Scripts/python.exe -c \
    "from adaptive_reflow.frame import Engine; print(Engine)"
```

If you see `<class 'adaptive_reflow.frame.engine.Engine'>`, you are
ready. If you see `ModuleNotFoundError`, your venv's `pip` installed
the package but Python can't find it; check the `PYTHONPATH=.` and the
site-packages `pip show adaptive-reflow` output.

---

## Step 2 — Run the test suite (≈ 10 seconds)

```bash
PYTHONPATH=. ./.venv/Scripts/python.exe -m pytest tests/ --no-header -q
```

The current suite is **1235 passing / 7 skipped** on the main branch;
the 7 skips are torch-gated molecule mixer tests. Skips are *expected*
on a stdlib-only install — they are gated by a `pytest.importorskip("torch")`
in `tests/test_adapters/test_mnist_fm.py`.

Targeted runs you may also want:

```bash
# Universal / molecular split guard (verifies no torch leak in the universal layer)
PYTHONPATH=. ./.venv/Scripts/python.exe -m pytest tests/test_universal/ -q

# Engine + bounded merge + ledger chain
PYTHONPATH=. ./.venv/Scripts/python.exe -m pytest tests/test_frame/ -q

# Full algorithmic + scheduler coverage
PYTHONPATH=. ./.venv/Scripts/python.exe -m pytest tests/test_algorithm/ -q
```

A green run prints something like `1235 passed, 7 skipped in 4.20s`.
A failing run names the test; the four workflow gates (`CPU`,
`docs-validate`, `bench`, `mutation-nightly`) are wired into
`.github/workflows/`.

---

## Step 3 — Plug in the toy adapter (≈ 30 seconds)

The canonical hello-world adapter is **`ToyGaussianAdapter`** at
`adaptive_reflow/adapters/toy_gaussian.py`. It implements all eight
`FlowMatchingODEAdapter` Protocol methods, with zero molecule
vocabulary, on a single channel `x`, and runs in milliseconds.

```python
"""Hello world — one round against ToyGaussianAdapter."""
from __future__ import annotations

from adaptive_reflow.contracts import (
    ChannelName, FinalRestartPolicy, ODEConditionDelta, make_default_phase_state,
)
from adaptive_reflow.adapters.toy_gaussian import (
    ToyGaussianAdapter, default_toy_gaussian_adapter,
)
from adaptive_reflow.frame import Engine

adapter = default_toy_gaussian_adapter()
engine = Engine(adapter=adapter)
phase = make_default_phase_state(run_id_seed="hello-gauss")

delta = ODEConditionDelta(
    delta_spec={"target_mean": 1.0},
    source="hello_gauss",
    target_round=0,
    calibration_artifact_hash="calibration:hello-gauss:v1",
)
policy = FinalRestartPolicy(
    policy_hash="policy:hello-gauss:v1",
    beta_by_channel={ChannelName("x"): 0.3},
)

result = engine.run_round(
    round_index=0,
    batch_id="batch-hello",
    sample_id="sample-hello",
    phase_state=phase,
    policy=policy,
    condition_delta=delta,
    seed=42,
)

print("gate:", result.gate)
print("audit_codes:", result.audit_codes)
print("trace.content_hash:", result.round_trace_v3.content_hash)
```

Save this as `hello_gauss.py` at the repo root and run:

```bash
PYTHONPATH=. ./.venv/Scripts/python.exe hello_gauss.py
```

A green run prints `gate: True`, an empty `audit_codes` list (or
`ERR_FEATURE_DISABLED` if a feature flag is off in your environment),
and a stable `content_hash` you can re-run byte-for-byte.

---

## Step 4 — Run a 2-D rectified-flow experiment (≈ 1–2 minutes)

`TwoDimFMAdapter` is the canonical real-model adapter in the repo. It
ships pre-trained weights under `data/`, runs end-to-end on a laptop,
and exposes the full Protocol surface. The standalone driver is
`tools/run_sota_2d_experiment.py`.

### Quick smoke run

```bash
# ~30 s; runs 4 schedulers × 2 seeds × 200 samples × 5 rounds
PYTHONPATH=. ./.venv/Scripts/python.exe tools/run_sota_2d_experiment.py --quick
```

This produces two markdown comparison tables (one per target
distribution: `two_moons`, `eight_gaussians`) under
`docs/r4-survey/`:

- `two_moons_comparison.md`
- `eight_gaussians_comparison.md`

Each table compares the **baseline** (1-pass single-shot, same
adapter, same weights) against the **four canonical schedulers**:

| Scheduler | What it does |
|---|---|
| `CosineAnnealScheduler` | Cosine anneal `n_cap`: ADR-0010. |
| `CodimensionSheetScheduler` | Paper-grounded `evidence_ratio` from sheet-A / packing-B / cell-C quantities (ADR-0013). |
| `EvidenceDrivenScheduler` | PID-lite on `selection_ratio` (paper Theorem 1 direction). |
| `FreeTrajScheduler` | Per-round free-trajectory budget. |

### Full run

```bash
# ~5 min on CPU; 4 schedulers × 5 seeds × 1000 samples × 20 rounds
PYTHONPATH=. ./.venv/Scripts/python.exe tools/run_sota_2d_experiment.py
```

Pass `--target two_moons` (or `eight_gaussians`) to single-target; pass
`--target both` (the default) to sweep both.

### Reading the per-round metrics

The driver writes per-round CSV files alongside the markdown tables:

```text
docs/r4-survey/two_moons_<scheduler>_seed<seed>.csv
docs/r4-survey/eight_gaussians_<scheduler>_seed<seed>.csv
```

Each CSV row carries:

- `round` — round index 0..N-1.
- `selection_ratio` — paper-Theorem-1 evidence witness.
- `wasserstein_2d` — closed-form 2-D Wasserstein on each axis.
- `support_coverage` — fraction of Voronoi cells hit.
- `energy_distance` — squared energy distance E².
- `n_cap` — the per-round budget selected by the scheduler.

The published 2-D RF baseline is `selection_ratio = 0.8061`;
framework target is `0.988+`. Numbers closer to 1.0 mean stronger
Theorem-1 evidence; numbers closer to 0.0 mean weaker.

---

## Step 5 — Sanity-check the docs scanner (≈ 5 seconds)

```bash
PYTHONPATH=. ./.venv/Scripts/python.exe tools/check_docs_against_code.py
```

The scanner walks every governance doc (`README.md`, `ARCHITECTURE.md`,
`TUTORIAL.md`, `QUICKSTART.md`, `docs/*.md`), extracts every concrete
class / function / module reference, and verifies each against an
AST-built symbol index. A green run prints `880+ claims verified,
0 unresolved` and exits `0`. A red run names the exact file and line
of the unresolved reference.

> Run this before every commit that touches `docs/` or
> `adaptive_reflow/`. CI runs it on every PR.

---

## Where to go next

| You want to… | Read |
| --- | --- |
| Plug your own SOTA flow-matching model into the engine | [`PLUG_IN_YOUR_MODEL.md`](./PLUG_IN_YOUR_MODEL.md) |
| Choose a different scheduler, driver, merge operator, or blender | [`ALGORITHMS.md`](./ALGORITHMS.md) |
| Understand the package layout, dependency DAG, governance invariants | [`ARCHITECTURE.md`](../ARCHITECTURE.md) |
| Implement the 8-method Protocol surface from scratch | [`ADAPTER_INTERFACE_SPEC.md`](./ADAPTER_INTERFACE_SPEC.md) |
| Run the four-scheduler ablation against your checkpoint | [`r4-survey/07-sota-experiment-protocol.md`](./r4-survey/07-sota-experiment-protocol.md) |
| Look up "why is X this way?" | [`FAQ.md`](../FAQ.md) |
| Run the worked example as an interactive notebook | [`examples/01_quickstart.ipynb`](../examples/01_quickstart.ipynb) |

---

## Appendix A — Why stdlib-only?

The framework's *universal layer* (`adaptive_reflow/universal/`,
`adaptive_reflow/contracts/`, `adaptive_reflow/frame/`,
`adaptive_reflow/policy/`, `adaptive_reflow/schedule/`,
`adaptive_reflow/diagnostics/`, `adaptive_reflow/writer/`,
`adaptive_reflow/eval/`) is implemented in pure Python with zero
non-stdlib imports. This is a load-bearing governance invariant,
verified at test time by
`tests/test_universal/test_no_molecular_import.py` and by an AST-level
guard that fails the build if any of those subpackages ever imports
`torch` or any other non-stdlib module.

The **molecular adapter** (`adaptive_reflow/molecular/`) and the
**real-model adapters** under `adaptive_reflow/adapters/` (MNIST,
CIFAR, Stochastic-FM) do import NumPy and (optionally) torch — but
they sit *above* the universal layer, and the universal layer
contracts (`FlowMatchingODEAdapter`, `RestartMixer`,
`EnvelopeCriterion`, `Evaluator`) are what make them swappable.

This split lets you run the entire engine, the four schedulers, the
bounded merge, and the ledger chain on a CPU laptop in well under a
second — no GPU, no model weights, no torch install.

## Appendix B — One-liner REPL tour

```bash
PYTHONPATH=. ./.venv/Scripts/python.exe - <<'PY'
from adaptive_reflow.algorithm.scheduler import (
    CosineAnnealScheduler, CodimensionSheetScheduler,
    EvidenceDrivenScheduler, FreeTrajScheduler,
)
from adaptive_reflow.contracts import CosineScheduleConfig

cos = CosineAnnealScheduler(CosineScheduleConfig(n_rounds=5, n_min=0.0, n_max=1.0))
print("cosine n_cap trajectory:", [cos.n_cap_for_round(r) for r in range(5)])

codim = CodimensionSheetScheduler(cycle_length=5)
print("codim n_cap trajectory:",
      [codim.n_cap_for_round(r, evidence_ratio=0.5) for r in range(5)])

freetraj = FreeTrajScheduler(amplitude=0.05, period=4)
print("freetraj n_cap trajectory:",
      [freetraj.n_cap_for_round(r, baseline=1.0) for r in range(5)])
PY
```

This drops you straight into the scheduler surface — no adapter, no
engine, no fixtures required. Use it as a scratchpad while you read
[`ALGORITHMS.md`](./ALGORITHMS.md).