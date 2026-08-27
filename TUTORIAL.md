# Tutorial

This is a hands-on walk through `flowa-multistep-reinference` aimed at
someone who has never read the package before and wants to (a) understand
*what* the universal layer is and *why* it exists, (b) write an adapter
against the `FlowMatchingODEAdapter` Protocol, (c) extend the test
harness with a hostile-case, property, golden, mutation, or bench test,
and (d) know which governance files to read before opening a PR.

The package is **CPU-only and stdlib-only**. Everything you read below
runs in plain Python 3.12 with no `torch`, no `numpy`, no I/O, no
network. If a snippet appears to use a third-party library, it is a
type-hint only and is not imported at runtime.

For project-wide context see [ARCHITECTURE.md](ARCHITECTURE.md). For
the test-layer catalogue see [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md).
For the Protocol surface see
[docs/ADAPTER_INTERFACE_SPEC.md](docs/ADAPTER_INTERFACE_SPEC.md). For
decisions see [docs/adr/](docs/adr/).

---

## 1. Mental model — protocol vs adapter, and why a universal layer exists

A *flow-matching model* (FlowMol3, Stable Diffusion 3, a 1D Gaussian
ODE, …) takes a noisy prior state, integrates a learned ODE, and emits
an endpoint. The integration can be restarted from previous-round
memory; the endpoint can be rejected by per-channel rules; the policy
that decides *how much* memory to mix back in is itself a learned
schedule.

A naive code layout couples the engine to the model: the engine knows
about molecules, and adding Stable Diffusion 3 means rewriting the
engine. The package solves this with a **two-layer split**:

* **`adaptive_reflow.universal/`** declares *what the engine needs*
  from any adapter, in `FlowMatchingODEAdapter`,
  `RestartMixer`, `EnvelopeCriterion`, and `Evaluator`. It is
  stdlib-only and has **zero** molecule-specific imports.
* **A concrete adapter** (`adaptive_reflow.molecular`,
  `adaptive_reflow.adapters.ToyLinearAdapter`,
  `adaptive_reflow.adapters.ToyGaussianAdapter`, future
  `LatentImageAdapter`, …) implements those Protocols for one model
  family.

The engine drives the Protocol; the adapter satisfies the Protocol. A
new model family means a new adapter — the engine never changes.

The split is *load-bearing* and is enforced by two guards documented
in ADR-0003. The first is an AST walk (`tests/test_universal/
test_no_molecular_import.py`) that refuses any `import
adaptive_reflow.molecular` inside `universal/`. The second is a
*positive* satisfiability check: a non-molecular adapter
(`ToyGaussianAdapter`) must actually exist and must drive the engine
end-to-end, proving that the Protocols are satisfiable by code that
never opens a chemistry book.

So when you read "universal" in this repo, read *engine-facing*; when
you read "molecular", read *one specific adapter that happens to be the
first one we shipped*. The mental model is "engine = kernel, adapter =
plugin", with `molecular/` being the most elaborate plugin to date.

---

## 2. The seven-step engine round

`adaptive_reflow.frame.engine.Engine.run_round` is a deterministic
seven-step operation, pinned in
[`DEFAULT_OPERATION_STEPS`](adaptive_reflow/frame/engine.py) and
explained in ADR-0004. The order is part of the public surface — the
round trace v3 records it, the kernel benchmark pins it, and the golden
replay re-derives it.

```
                       ┌────────────────────────────────────────┐
                       │ Engine.run_round(round_index, …)       │
                       └────────────────────────────────────────┘
                                          │
        ┌────────────────┬────────────────┼────────────────┬───────────────┐
        ▼                ▼                ▼                ▼               ▼
   1. capabilities   2. build_initial   3. apply_restart  4. compose_     5. solve_ode
   (cached at         state             distribution     condition       (dt or
   registration;      (round 0 only;     (mix prior +     (injects delta  adaptive
   per-call guard     seed-keyed        memory under     into the ODE    steps)
   on demand)         hash-stable       RestartPolicy    trajectory
                      digest)           → next prior)
        │                │                │                │               │
        ▼                ▼                ▼                ▼               ▼
                       6. observe_endpoint          7. detach_and_validate
                       (snapshot the final          (refuse any non-detached
                       bundle, run evaluators,      bundle; fail closed)
                       emit audit codes)
```

Walkthrough:

1. **Capability handshake.** `capabilities()` is called once at
   adapter registration; the result is cached. If the engine later
   asks for a capability the adapter does not declare, the adapter
   raises `CapabilityMissingError` and the round is marked
   `gate=False`.
2. **`build_initial_state`.** Constructs the round-0 prior bundle
   with a deterministic `native_state_digest`. Negative `source_round`
   raises `ValueError` immediately.
3. **`apply_restart_distribution`.** Blends the current round's prior
   with the previous round's endpoint under the `FinalRestartPolicy`.
   The mixer (`NoOpMixer`, `LatentConvexMixer`,
   `RMSPreservingCoordinateMixer`, …) is selected by the adapter's
   `required_mixer`.
4. **`compose_condition`.** The condition delta (`ODEConditionDelta`)
   is composed into the ODE trajectory. Adapters that do not declare
   `has_condition_injection` raise `CapabilityMissingError`.
5. **`solve_ode`.** The adapter integrates the ODE. The
   `ODEIntegratorTrace` is byte-stable for fixed `(state, seed, steps)`
   so round-to-round paired comparisons are reproducible (DTB-R7).
6. **`observe_endpoint`.** Snapshots the final bundle, runs evaluators,
   and emits audit codes (`AUDIT_STABILITY_COLLAPSE`,
   `AUDIT_SOURCE_REVOKED`, `BLOCKER_PROXY_ONLY`, etc.).
7. **`detach_and_validate_endpoint`.** Refuses any bundle whose
   `detach_proof` is not `True`. Fail-closed surface for the engine's
   state lifecycle.

The bench budget for one full round is `engine_round_loop_us_p95 =
1000 µs` (see `docs/PERFORMANCE_BUDGETS.md`). The seven steps are not
negotiable — adding an eighth requires a new ADR that names the step,
its position, and the migration path for every golden and benchmark.

---

## 3. Writing your own adapter

The Protocol surface is eight methods (see
[docs/ADAPTER_INTERFACE_SPEC.md §2](docs/ADAPTER_INTERFACE_SPEC.md) for
the full description). The two in-tree worked examples are
`adaptive_reflow.adapters.ToyLinearAdapter` (single continuous
channel, no restart, no condition) and `adaptive_reflow.adapters.
ToyGaussianAdapter` (single continuous channel with full restart and
condition). Below is a representative excerpt of `ToyGaussianAdapter`
that exercises the full lifecycle; the full source is at
`adaptive_reflow/adapters/toy_gaussian.py`.

```python
import hashlib, math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from adaptive_reflow.contracts.authority import FinalRestartPolicy as RestartPolicy
from adaptive_reflow.universal import (
    AdapterCapabilities, ArtifactHash, CapabilityMissingError,
    FlowMatchingODEAdapter, NoOpMixer,
)
from adaptive_reflow.universal.state import (
    ChannelName, ODEConditionDelta, ODEIntegratorTrace, StateBundle,
    TensorRef, validate_state_bundle,
)

SUPPORTED_CHANNELS = (ChannelName("x"),)
CHANNEL_DOMAINS = {ChannelName("x"): "continuous"}
NATIVE_CONFIG_HASH = ArtifactHash("toy:gaussian:cfg:v1")

def _ref(label, **parts):
    blob = repr((label, sorted(parts.items()))).encode("utf-8")
    return TensorRef(f"toy:gauss:{hashlib.sha256(blob).hexdigest()[:16]}")

class ToyGaussianAdapter(FlowMatchingODEAdapter):
    def capabilities(self):
        return AdapterCapabilities(
            has_ode_integration_surface=True, has_prior_export=True,
            has_state_export=True, has_condition_injection=True,
            has_restart_boundary=True, has_continuous_channels=True,
            has_discrete_channels=False, has_trajectory_digest=True,
            has_deterministic_seed=True, has_materialization_route=True,
            supported_channels=SUPPORTED_CHANNELS,
            channel_domains=CHANNEL_DOMAINS,
            required_mixer=NoOpMixer,
        )

    def build_initial_state(self, *, batch_id, sample_id):
        bundle = StateBundle(
            channels={ChannelName("x"): _ref("initial", b=batch_id, s=sample_id)},
            masks={}, batch_id=str(batch_id), sample_id=str(sample_id),
            reference_frame="world", normalization="none",
            source_round=0, detach_proof=True,
            native_state_digest="gauss-init-digest",
            provenance=("toy_gaussian@v1",), capability_token=self.capabilities(),
        )
        ok, errs = validate_state_bundle(bundle)
        if not ok: raise AssertionError(errs)
        return bundle

    # ... export_endpoint, detach_and_validate_endpoint,
    #     apply_restart_distribution, compose_condition,
    #     solve_ode, observe_endpoint ...
```

The accompanying tests live at
`tests/test_universal/test_toy_gaussian.py` and assert:

* the capability handshake values,
* `solve_ode` is deterministic for fixed `(state, seed, steps)`,
* `apply_restart_distribution` blends the weights / means / stddevs
  according to the policy's `memory_fraction`,
* no file under `adaptive_reflow/universal/` ever imports
  `adaptive_reflow.molecular` (AST guard),
* a Gaussian adapter round-trip succeeds against the
  `AdaptiveReflowPolicyOrchestrator`.

To add a third adapter, copy `toy_gaussian.py` into
`adaptive_reflow/adapters/your_model.py`, set the channel vocabulary
to whatever your model carries, re-export from
`adaptive_reflow/adapters/__init__.py`, and add a test file under
`tests/test_adapters/test_your_model.py` mirroring the structure of
`tests/test_adapters/test_toy_linear.py`. The five-section
[ToyLinearAdapter test
file](tests/test_adapters/test_toy_linear.py) is a good template.

---

## 4. Running hostile-case tests

`tests/test_adversarial/` is the load-bearing adversarial layer. One
test per hostile case in `DESIGN_BOUNDARY.md` §3; each test is
*fail-closed* (a regression means the envelope / gate can be talked
into an unsafe state). Six cases are pinned today:

| # | Hostile case | Test | Audit code |
|---|--------------|------|------------|
| 1 | High GNINA, PoseBusters failure | `test_geometry_failure_closes_gate_and_emits_geometry_failure_audit_code` | `geometry_failure` |
| 2 | Confident point estimate, instability on perturbation | `test_monotonic_uncertainty_closes_gate_when_stability_collapses` (and four siblings) | `AUDIT_STABILITY_COLLAPSE` = `perturbation_stability_below_threshold` |
| 3 | Two metric rows from one `bundle_id` | `test_duplicate_evidence_does_not_inflate_transfer_score_mass` | `duplicate_evidence_row_ignored` |
| 4 | `source_round=k-3` mixed with `source_round=k` | `test_cross_round_stitch_rejects_bundle_at_validation` | `cross_round_stitching` |
| 5 | `revoked=True` after registration | `test_source_revocation_closes_subsequent_gate` (and three siblings) | `AUDIT_SOURCE_REVOKED` = `source_revoked` |
| 6 | `feedback_mode == "proxy_only"` with non-zero `raw_score` | `test_proxy_only_evidence_cannot_satisfy_calibration_lower_bound` | `BLOCKER_PROXY_ONLY` = `proxy_only_cannot_satisfy_calibration` |

The two new audit codes are
[`AUDIT_STABILITY_COLLAPSE`](adaptive_reflow/frame/channel_rule.py)
(case 2) and
[`AUDIT_SOURCE_REVOKED`](adaptive_reflow/contracts/validators.py)
(case 5). Both are re-exported from `adaptive_reflow.frame`,
`adaptive_reflow.contracts`, and `adaptive_reflow.policy`, so the doc
scanner can verify them.

To add a new hostile case, follow `CONTRIBUTING.md` §1: add the case
to `DESIGN_BOUNDARY.md` §3 with its expected audit code, add a fixture
under `tests/test_adversarial/`, mirror the case in
`docs/TESTING_STRATEGY.md` §2.3, and confirm the test passes
locally. Run `pytest tests/test_adversarial/ -v` — a *passing* test
is the goal (it means the gate stays closed).

---

## 5. Golden snapshots

The golden layer (`tests/golden/<kernel>/`) records input / output
pairs for the hot-path kernels (`bounded_merge`, `channel_rule`,
`claim_gate`, `synthetic_evaluator`). The replay path is
`tests/property/test_golden_replay.py`; a new golden is generated by
[`tools/generate_golden.py`](tools/generate_golden.py) and committed
alongside the change.

The workflow:

```
# 1. Make your code change (e.g. tighten a validator).

# 2. Regenerate the goldens for the affected kernel.
PYTHONPATH=. ./.venv/Scripts/python.exe tools/generate_golden.py \
    --kernel bounded_merge \
    --output tests/golden/bounded_merge/

# 3. Verify the suite still replays every golden.
PYTHONPATH=. ./.venv/Scripts/python.exe -m pytest \
    tests/property/test_golden_replay.py -v

# 4. If a golden genuinely needs to change (new field, new shape),
#    update the JSON file in place and add a one-line changelog entry
#    in CHANGELOG.md explaining why the golden moved.
```

Goldens are checked in as JSON so the diff is human-reviewable. A
golden change without a justifying code change is a bug; a code
change without a regenerated golden is a flaky-test future.

---

## 6. Property-based tests

The package uses [`hypothesis`](https://hypothesis.readthedocs.io/) for
property-based exploration of the bounded `[0, 1]` envelopes. The
strategies live in `tests/property/conftest.py` and are deliberately
small (`max_examples=200`, `deadline=5000 ms`) so the budgets stay
bounded. The five existing files cover:

* `bounded_merge` invariants (monotonicity, idempotence, commutativity).
* `compute_channel_decision` truth-table closure.
* `evaluate_claim_gate` invariants.
* Mixer RMS-preservation.
* Validator rejection paths.

To add a new property test that survives shrinking:

```python
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

@given(
    raw=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    cal=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_my_invariant_holds(raw, cal):
    """Property: my invariant must hold over the bounded envelope."""
    evidence = _build_evidence(raw, cal)
    decision = compute_channel_decision(evidence)
    assert decision.gate in (True, False)
    assert 0.0 <= float(decision.beta) <= 1.0
```

Three rules keep property tests shrinking-friendly: (1) prefer
`floats(min_value=…, max_value=…, allow_nan=False)` over unconstrained
floats — `NaN` poisons the predicate and stalls the shrinker; (2)
keep the `max_examples` small and the predicate fast — the property
test budget is part of CI; (3) wrap any I/O or timing check in
`suppress_health_check=[HealthCheck.too_slow]` so Windows file-IO
variance doesn't kill the test.

---

## 7. Mutation testing

[`mutmut`](https://mutmut.readthedocs.io/) runs against the
contracts + universal core in the nightly Linux job
(`.github/workflows/mutation-nightly.yml`). On Windows the runner is
deferred to upstream issue 397; the Linux job captures the canonical
score and uploads the report as the `mutmut-report` artifact.

To read [`mutmut_results.txt`](mutmut_results.txt):

```
# Mutant id, status, surviving because...
:lineno:func_a    KILLED  via test_x
:lineno:func_b    SURVIVED  (no test asserts the boundary)
:lineno:func_c    NO TESTS  (file is not covered)
```

Three statuses to triage:

* `KILLED` — the test suite caught the mutation. Nothing to do.
* `SURVIVED` — the mutant is reachable but no test asserts its
  behaviour. This is either (a) an equivalent mutant (annotate in
  `tools/mutate/`) or (b) a missing test. (b) is filed as a
  follow-up and blocks the PR that introduced it (ADR-0005).
* `NO TESTS` — the file is not exercised by any test. Either add a
  test, or drop the file from the mutation scope in
  [`tools/mutate/mutmut.toml`](tools/mutate/mutmut.toml).

Mutation score targets (see
[docs/TESTING_STRATEGY.md §7](docs/TESTING_STRATEGY.md)): `contracts/`
≥ 90 %, `universal/` ≥ 85 %, `molecular/` ≥ 70 % best-effort,
`frame/` ≥ 75 %. A surviving mutant in `contracts/` or `universal/`
is, by definition, a missing test.

---

## 8. Performance budgets

The kernel performance budgets are documented in
[`docs/PERFORMANCE_BUDGETS.md`](docs/PERFORMANCE_BUDGETS.md). The
authoritative numbers live in
[`tools/bench/budgets.json`](tools/bench/budgets.json); the
measurements live in [`docs/benchmarks.json`](docs/benchmarks.json).

| Kernel | Budget (µs, p95) | Ceiling (×1.2) |
|---|---:|---:|
| `bounded_merge` | 50 | 60 |
| `compute_channel_decision` | 200 | 240 |
| `evaluate_claim_gate` | 100 | 120 |
| `engine_round_loop` | 1000 | 1200 |

The `engine_round_loop` metric captures the **end-to-end** per-round
cost (all seven steps), not just one kernel; it is produced by
[`tools/bench/runner.py`](tools/bench/runner.py) driving 200
consecutive `evaluate_bundle` calls.

The bench workflow:

```
# 1. Capture fresh measurements.
PYTHONPATH=. ./.venv/Scripts/python.exe -m pytest tests/perf/ \
    --benchmark-only --benchmark-json=docs/benchmarks.json --no-header

# 2. Update the engine-round-loop metric.
PYTHONPATH=. ./.venv/Scripts/python.exe tools/bench/runner.py \
    --output docs/benchmarks.json

# 3. Run the regression gate.
PYTHONPATH=. ./.venv/Scripts/python.exe tools/bench/check_budgets.py
```

A clean run prints four `ok` lines and exits `0`. A failing gate is
a same-day fix — not a reason to bump the budget up. If the ceiling
needs to move, update `tools/bench/budgets.json` together with a
`CHANGELOG.md` entry explaining why.

---

## 9. Contributing

The four workflows are documented in
[`CONTRIBUTING.md`](CONTRIBUTING.md); the architecture decisions are
in [`docs/adr/`](docs/adr/); the deprecation table is in
[`docs/DEPRECATION.md`](docs/DEPRECATION.md); the security posture is
in [`SECURITY.md`](SECURITY.md); the reviewer routing is in
[`CODEOWNERS`](CODEOWNERS). The local gate before pushing is:

```
PYTHONPATH=. ./.venv/Scripts/python.exe -m pytest tests/ --no-header -q
PYTHONPATH=. ./.venv/Scripts/python.exe tools/check_docs_against_code.py
.venv/Scripts/ruff.exe check adaptive_reflow/ tests/
```

All three must be green. The nightly mutation and weekly bench jobs
do not block the PR but their artifacts are expected to be triaged.

If your change touches a load-bearing boundary (the contracts / universal
split, the universal / molecular split, the seven-step order, the
audit-code policy), write an ADR first and link it from your PR. The
format is MADR 4.0 — see [`docs/adr/0001`](docs/adr/0001-record-architecture-decisions.md)
for the template.
