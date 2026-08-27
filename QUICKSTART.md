# QUICKSTART

This page is a five-minute on-ramp: install, run the tests, walk one round
against the canonical hello-world adapter, capture a golden, run the docs
scanner, then move on.

For the *what* and the *why*, see [`ARCHITECTURE.md`](ARCHITECTURE.md). For
common questions, see [`FAQ.md`](FAQ.md). For the deeper walk-through of a
round, see [`TUTORIAL.md`](TUTORIAL.md).

## 1. What this is and isn't

1. **It is**: a typed-contracts framework for governed, multi-step flow
   matching inference: round orchestration, restart memory, condition
   control policy, external-metric feedback, and restart plans.
2. **It is not**: an end-to-end pocket-conditioned generation pipeline, a
   model implementation, or a torch/numpy dependency. Everything in
   `adaptive_reflow/universal/` and `adaptive_reflow/contracts/` is
   stdlib-only.
3. **It is**: CPU-only by design. The test suite runs in well under a
   second; there is no GPU runner and no model in the loop.
4. **It is not**: a single-authority writer for the downstream
   restart-noise bias library. That companion lives in
   `silverenternal/flowa-noise-bias`; this repo is the *sole executable
   writer* for the restart distribution and ODE condition updates.
5. **It is**: the canonical home of the eight-method
   `FlowMatchingODEAdapter` Protocol — the surface every adapter (this
   repo's own plus external ones) implements.

## 2. Install

The package is pip-install-free by design. Python 3.12+ is the only
runtime requirement; `pytest`, `hypothesis`, and `pytest-benchmark` are
the test-time dependencies pinned in `pyproject.toml`.

```bash
# Clone
git clone https://github.com/silverenternal/flowa-multistep-reinference
cd flowa-multistep-reinference

# Create venv (Windows; use python3 / venv on Linux)
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[test]"

# Sanity import — should print the package version line
PYTHONPATH=. ./.venv/Scripts/python.exe -c \
    "from adaptive_reflow.frame import Engine; print(Engine)"
```

If `import adaptive_reflow` fails, the most common cause is forgetting
`PYTHONPATH=.` — the package has no top-level `__init__.py` so
imports go straight to a subpackage (`adaptive_reflow.frame`,
`adaptive_reflow.universal`, etc.).

## 3. Run the test suite

```bash
# Full suite (~475 tests, < 1 s on CPU)
PYTHONPATH=. ./.venv/Scripts/python.exe -m pytest tests/ --no-header -q

# Targeted runs
PYTHONPATH=. ./.venv/Scripts/python.exe -m pytest tests/test_universal/   # universal / molecular split guards
PYTHONPATH=. ./.venv/Scripts/python.exe -m pytest tests/test_adversarial/ # hostile-case battery
PYTHONPATH=. ./.venv/Scripts/python.exe -m pytest tests/test_frame/       # engine + bounded merge + trace
```

The four workflow gates (CPU, docs-validate, bench, mutation-nightly)
are wired into `.github/workflows/`; see
[`docs/TESTING_STRATEGY.md`](docs/TESTING_STRATEGY.md) §5.

## 4. Run a single round against `ToyGaussianAdapter`

The canonical hello world is the 1-D Gaussian-mixture adapter at
[`adaptive_reflow/adapters/toy_gaussian.py`](adaptive_reflow/adapters/toy_gaussian.py).
It implements all eight `FlowMatchingODEAdapter` Protocol methods with
zero molecule vocabulary, on the single channel `x`.

```python
"""Hello-world: one round against ToyGaussianAdapter.

Stdlib-only. No torch, no numpy. Mirrors the test in
``tests/test_universal/test_toy_gaussian.py``.
"""
from __future__ import annotations

import os
import sys

# Allow running this file directly from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adaptive_reflow.contracts import (  # frozen typed dataclasses (leaf)
    ChannelName,
    FinalRestartPolicy,                 # aka RestartPolicy (re-export)
    ODEConditionDelta,                  # condition delta carrier
    PhaseState,                         # round phase state
    make_default_phase_state,           # factory used by Engine.run_round
)
from adaptive_reflow.adapters.toy_gaussian import (
    ToyGaussianAdapter,                 # the canonical hello-world adapter
    default_toy_gaussian_adapter,       # factory
)
from adaptive_reflow.frame import Engine   # the canonical round driver

# 1. Adapter + engine (engine reads capabilities at registration).
adapter = default_toy_gaussian_adapter()
engine = Engine(adapter=adapter)

# 2. Build the per-run state.
phase = make_default_phase_state(run_id_seed="hello-gauss")

# 3. Condition delta — moves the target mean away from the prior.
delta = ODEConditionDelta(
    delta_spec={"target_mean": 1.0},
    source="hello_gauss",
    target_round=0,
    calibration_artifact_hash="calibration:hello-gauss:v1",
)

# 4. Restart policy: beta=0.3 means 30% memory on the `x` channel.
policy = FinalRestartPolicy(
    policy_hash="policy:hello-gauss:v1",
    beta_by_channel={ChannelName("x"): 0.3},
)

# 5. One round end-to-end — emit RoundTrace + ledger + audit_codes.
result = engine.run_round(
    round_index=0,
    batch_id="batch-hello",
    sample_id="sample-hello",
    phase_state=phase,
    policy=policy,
    condition_delta=delta,
    seed=42,
)

# 6. Inspect the result.
print("gate:", result.gate)
print("audit_codes:", result.audit_codes)
print("trace.operation_order:", result.round_trace_v3.operation_order)
print("trace.content_hash:", result.round_trace_v3.content_hash)
```

Save this as `hello_gauss.py` at the repo root and run:

```bash
PYTHONPATH=. ./.venv/Scripts/python.exe hello_gauss.py
```

A green run prints `gate: True`, an empty audit list (or
`ERR_FEATURE_DISABLED` if the feature flag is off in your environment),
and a stable `content_hash`.

## 5. Generate a golden snapshot

Goldens are recorded JSON input / output pairs under
[`tests/golden/<kernel>/`](tests/golden/) and replayed by
[`tests/property/test_golden_replay.py`](tests/property/test_golden_replay.py).
Generate them deterministically via
[`tools/generate_golden.py`](tools/generate_golden.py):

```bash
# All subjects (bounded_merge, channel_rule, claim_gate, synthetic_evaluator)
PYTHONPATH=. ./.venv/Scripts/python.exe tools/generate_golden.py

# One subject only — faster for spot-regenerations during a refactor
PYTHONPATH=. ./.venv/Scripts/python.exe tools/generate_golden.py --only bounded_merge

# Replay + verify — should pass on every golden
PYTHONPATH=. ./.venv/Scripts/python.exe -m pytest tests/property/test_golden_replay.py --no-header -q
```

Always commit the regenerated JSON alongside the change that produced
it; the bench and property suites compare against the checked-in
golden, never against re-derived values.

## 6. Run the docs scanner

The scanner at
[`tools/check_docs_against_code.py`](tools/check_docs_against_code.py)
walks every governance doc (this file, `ARCHITECTURE.md`, `README.md`,
`STATUS.md`, `DESIGN_BOUNDARY.md`, `CONTRACTS.md`) plus `docs/*.md`,
extracts every concrete claim (CamelCase / SCREAMING_SNAKE_CASE
identifiers inside python fenced blocks, `adaptive_reflow/...` path
references, inline-backtick class names), and verifies each against an
AST-built symbol index. It exits non-zero on drift.

```bash
# Default: scan governance docs only
PYTHONPATH=. ./.venv/Scripts/python.exe tools/check_docs_against_code.py

# Phase 2 — also scan docstrings inside adaptive_reflow/ for inline references
PYTHONPATH=. ./.venv/Scripts/python.exe tools/check_docs_against_code.py --scan-docstrings

# Quiet — useful in CI when only the exit code matters
PYTHONPATH=. ./.venv/Scripts/python.exe tools/check_docs_against_code.py --quiet
```

A green run prints a markdown table with 880+ verified claims and exits
`0`. A failing run names the unresolved identifier and the file/line
that referenced it.

## 7. Where to go next

| You want to… | Read |
| --- | --- |
| Walk one round end-to-end, hands-on | [`TUTORIAL.md`](TUTORIAL.md) |
| Understand the package layout, dependency DAG, governance invariants | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Look up a quick "why is X this way?" | [`FAQ.md`](FAQ.md) |
| Trace a load-bearing boundary decision back to its rationale | [`docs/adr/`](docs/adr/) |
| Add a new model family (latent FM, discrete CTMC FM, audio FM, …) | [`docs/ADAPTER_INTERFACE_SPEC.md`](docs/ADAPTER_INTERFACE_SPEC.md) |
| Audit the typed contracts themselves | [`CONTRACTS.md`](CONTRACTS.md) and [`DESIGN_BOUNDARY.md`](DESIGN_BOUNDARY.md) |
| Tune or extend the perf budgets | [`docs/PERFORMANCE_BUDGETS.md`](docs/PERFORMANCE_BUDGETS.md) |
