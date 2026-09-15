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

## 8. What is FlowA? (one-paragraph intro for reviewers)

FlowA — *Flow Matching, Adaptive* — is a thin, stdlib-only governance
layer that wraps any flow-matching ODE solver and turns it into a
multi-step, memory-aware, restart-aware inference loop. The framework
owns three things: (i) a typed round contract
(`adaptive_reflow/contracts/`) that pins what flows in and out of
every round, (ii) an `Engine` (`adaptive_reflow/frame/Engine`) that
orchestrates rounds, emits a byte-stable `RoundTrace`, and merges
restart memory with bounded idempotence, and (iii) the eight-method
`FlowMatchingODEAdapter` Protocol every model adapter implements.
Everything outside that surface — solver math, model weights, channel
arithmetic — is owned by the adapter. This split lets the same
framework driver carry 2D synthetic, CIFAR-10 RF, MNIST FM, LineageFlow
protein, and FlowMol3 molecular experiments with no per-domain code
in the framework core. The headline empirical claim, gated across
six Tier-1 axes, is that wrapping a pretrained FM model in the
framework produces a strictly better W2 / FID / domain-metric at
matched NFE, with the strongest two uplifts on synthetic 2D (no
external ckpt needed): **R4 Two Moons W2 −7.28 %** and **R5 Eight
Gaussians W2 −10.40 %**.

## 9. Five-minute reproduction — R4 + R5 (2D synthetic, no external deps)

Of the six headline R.N claims in
[`docs/headline-evidence/README.md`](docs/headline-evidence/README.md),
**only R4 and R5 need no external checkpoints, no GPU, and no model
weights** — they generate their own synthetic 2D targets. A reviewer
on a clean checkout can verify both uplifts from this directory in
under five minutes of compute:

```bash
# (Optional) create a venv + install dev deps once
python -m venv .venv
.venv/bin/pip install -e ".[test]"
```

### R4 — 2D Two Moons W2 −7.28 %

```bash
python tools/run_sota_2d_experiment.py \
    --target two_moons \
    --n-samples 1000 \
    --n-rounds 10 \
    --n-seeds 3 \
    --output-dir verification_outputs/sota_2d_w153/two_moons
```

Expected JSON / Markdown output paths:

- `verification_outputs/sota_2d_w153/two_moons/RESULTS.md`
- `verification_outputs/sota_2d_w153/two_moons/two_moons_<scheduler>_seed<int>.csv`

Expected headline numbers (matched NFE = 500, 3 seeds):

| arm       | W2 distance |
| --------- | ----------- |
| baseline  | 0.5029      |
| framework | 0.4663      |
| Δ         | **−7.28 %** |

Historical wall-clock: ~33 min CPU (Wave 16 sweep, commit `4a482ff`).
External dependencies: **none**.

### R5 — 2D Eight Gaussians W2 −10.40 %

```bash
python tools/run_sota_2d_experiment.py \
    --target eight_gaussians \
    --n-samples 1000 \
    --n-rounds 10 \
    --n-seeds 3 \
    --output-dir verification_outputs/sota_2d_w153/eight_gaussians
```

Expected JSON / Markdown output paths:

- `verification_outputs/sota_2d_w153/eight_gaussians/RESULTS.md`
- `verification_outputs/sota_2d_w153/eight_gaussians/eight_gaussians_<scheduler>_seed<int>.csv`

Expected headline numbers (matched NFE = 500, 3 seeds):

| arm       | W2 distance |
| --------- | ----------- |
| baseline  | 0.6606      |
| framework | 0.5919      |
| Δ         | **−10.40 %** |

Historical wall-clock: ~33 min CPU (same Wave 16 sweep as R4).
External dependencies: **none**.

Both sweeps live under one CLI driver
([`tools/run_sota_2d_experiment.py`](tools/run_sota_2d_experiment.py));
only `--target` changes. The byte-stable headline numbers are also
re-cited in [`docs/GATES.md`](docs/GATES.md) §1 and in
[`docs/r4-survey/10-sota-2d-experiment-results.md`](docs/r4-survey/10-sota-2d-experiment-results.md).

## 10. Engineering gates — current pass/fail snapshot

The framework keeps four hard gates green at HEAD; every doc on this
repo that cites a number cross-references them. To verify locally:

```bash
# G1 — D.4 pinned regression vectors: 72/72 PASS
PYTHONPATH=. python -m pytest tests/test_d4_regression_vectors.py \
    tests/test_adapters/test_regression_vectors.py -q
# expected: "72 passed"

# G2 — mypy type-coverage audit (I.1)
python scripts/run_mypy_audit.py | head -7
# expected: "coverage : 100.00%" + "meets target : True"

# G3 — claims consistency (no drift across 39 active claims)
python tools/check_claims_consistency.py | tail -3
# expected: "No drift detected."

# G4 — ruff-frozen source tree (no source touched since Wave 149 final close)
# See docs/GATES.md §3 for the frozen set; re-running ruff on those paths
# is intentionally skipped because the freeze is the contract, not the
# current ruff version.
```

| Gate | Scope                                  | Expected                  |
| ---- | -------------------------------------- | ------------------------- |
| D.4  | 33 + 39 pinned regression vectors      | `72 passed`               |
| I.1  | mypy type-coverage audit (`adaptive_reflow/`) | `100.00%`          |
| Claims | 39 active CLM-* claims across docs   | `No drift detected`       |
| Ruff | framework source frozen at Wave 149    | `0` (no source touched)   |

Source-of-truth: [`docs/GATES.md`](docs/GATES.md) (snapshot date
2026-09-14, commit `5677cf2`).

## 11. Reproducibility — R1 … R6 in one shell wrapper

For reviewers who want all six headline R.N claims documented in a
single bash invocation (with external dependencies and wall-clock
estimates per R.N), the wrapper at
[`scripts/reproduce_r1_to_r6.sh`](scripts/reproduce_r1_to_r6.sh)
(Wave 152 P5) prints the full per-R.N plan:

```bash
# Default: print plan only — commands are commented out for safety
bash scripts/reproduce_r1_to_r6.sh

# Skip heavyweight R.N on a host that can't run them:
SKIP_R1=1 SKIP_R2=1 bash scripts/reproduce_r1_to_r6.sh

# Per-R.N SKIP_Rn=1 flags are honored; see --help for the full list.
```

The wrapper is **safe to invoke** — every R.N python invocation is
commented out by default because R1 alone is ~30–50 h CPU and R2 is
~3–4 h GPU. To actually re-run a sweep, open the file and uncomment
the section header marked `# UNCOMMENT TO RUN` for the R.N you want.

Cumulative wall-clock (single host):

- R4 + R5 (synthetic 2D, no GPU): **~1 h CPU** ← start here
- R3 + R6 (FID math, GPU): ~1–2 h GPU
- R2 (FlowMol3 sweep, GPU): ~3–4 h GPU
- R1 (LineageFlow + HMMER / Pfam, CPU): ~30–50 h CPU

## 12. What to read next (paper / supplementary / README pointers)

| You want to…                                                    | Read |
| ------------------------------------------------------------ | ---- |
| Skim the full Tier-1 paper draft                             | [`docs/paper-draft.md`](docs/paper-draft.md) |
| Read the NeurIPS-camera-ready version (§1–§10)               | [`docs/paper-final-neurips.md`](docs/paper-final-neurips.md) (PDF mirror: `docs/paper-final-neurips.pdf`) |
| See the project README + scope statement                     | [`README.md`](README.md) |
| Walk the six R.N headline numbers + per-R.N source-of-truth  | [`docs/headline-evidence/README.md`](docs/headline-evidence/README.md) |
| Inspect the per-component ablation matrix cited in §Ablations | [`docs/ABLATION.md`](docs/ABLATION.md) |
| Confirm every engineering gate at HEAD                       | [`docs/GATES.md`](docs/GATES.md) |
| Audit the byte-stable reproduction record (8 experiments)    | [`docs/reproducibility_record.md`](docs/reproducibility_record.md) |
