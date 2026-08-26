# FAQ

Twenty short answers to the questions that come up most often while
working on `flowa-multistep-reinference`. For the deeper rationale, see
[`ARCHITECTURE.md`](ARCHITECTURE.md) and [`docs/adr/`](docs/adr/).

## 1. Why is the universal layer stdlib-only?

So that any model family (latent image FM, discrete CTMC FM, audio FM,
graph FM) can implement the eight-method `FlowMatchingODEAdapter`
Protocol without inheriting a torch / numpy / pocket_modules
dependency. The boundary is enforced by the AST-level guard at
[`tests/test_universal/test_no_molecular_import.py`](tests/test_universal/test_no_molecular_import.py),
which fails the suite if anything under `adaptive_reflow/universal/`
imports from `adaptive_reflow.molecular/` or pulls a non-stdlib
module. See [ADR-0003](docs/adr/0003-universal-vs-molecular-split.md).

## 2. What's the difference between `flow_matching_engine.Engine` and `frame.Engine`?

There is only **one** canonical engine: `adaptive_reflow.frame.Engine`
(importable as `from adaptive_reflow.frame import Engine`). Any legacy
`flow_matching_engine` symbol is a pre-refactor quarantine artefact;
importing it emits a `DeprecationWarning` via
[`adaptive_reflow/legacy/__init__.py`](adaptive_reflow/legacy/__init__.py)
and should not be used by new code. The canonical home is
[`adaptive_reflow/frame/engine.py`](adaptive_reflow/frame/engine.py).

## 3. Where does the `ERR_*` audit-code list live?

The canonical `ERR_*` constants live in
[`adaptive_reflow/frame/engine.py`](adaptive_reflow/frame/engine.py)
(e.g. `ERR_BUNDLE_INVALID`, `ERR_CHANNEL_UNSUPPORTED`,
`ERR_DETACH_PROOF_FAILED`, `ERR_FEATURE_DISABLED`). The
`BLOCKER_*` constants live in
[`adaptive_reflow/frame/channel_rule.py`](adaptive_reflow/frame/channel_rule.py);
the `OBS_*` and `_BLOCKER_GEOMETRY` constants live in
[`adaptive_reflow/envelope/classifier.py`](adaptive_reflow/envelope/classifier.py);
the literal-set tuples (`COMPLEMENT_BLOCKER_CODES`,
`RESTART_TRIGGER_CODES`, `FEEDBACK_MODES`) live in
[`adaptive_reflow/contracts/types.py`](adaptive_reflow/contracts/types.py).
Every constant is re-exported from its subpackage's `__init__.py` so
the doc scanner can resolve it. See
[ADR-0005](docs/adr/0005-fail-closed-audit-code-policy.md).

## 4. How do I add a new hostile-case test?

Add a fixture under [`tests/test_adversarial/`](tests/test_adversarial/).
Each hostile case in `DESIGN_BOUNDARY.md` §3 maps to one test method
that asserts the gate closes, the right `ERR_*` / `BLOCKER_*` audit
code is emitted, and the ledger row is recorded. Mark it with
`@pytest.mark.adversarial`, place a paired narrative in
`DESIGN_BOUNDARY.md`, and run the full adversarial battery plus the
docs scanner before pushing. See
[`docs/TESTING_STRATEGY.md`](docs/TESTING_STRATEGY.md) §2.3.

## 5. Why are there two engines?

There aren't — there is only **one** canonical engine:
`adaptive_reflow.frame.Engine`. Any other `Engine` symbol is a stale
re-export shim from the pre-refactor layout and emits a
`DeprecationWarning` on import. New code imports
`from adaptive_reflow.frame import Engine`. Removing the legacy shims
is on the follow-up pass tracked in `todo.json`.

## 6. How do I write an adapter that doesn't touch torch?

Copy the `ToyGaussianAdapter` skeleton at
[`adaptive_reflow/adapters/toy_gaussian.py`](adaptive_reflow/adapters/toy_gaussian.py)
or `ToyLinearAdapter` at
[`adaptive_reflow/adapters/toy_linear.py`](adaptive_reflow/adapters/toy_linear.py).
Both are stdlib-only, implement all eight `FlowMatchingODEAdapter`
Protocol methods, advertise `has_continuous_channels` only, and pass
[`tests/test_universal/test_adapter_universality.py`](tests/test_universal/test_adapter_universality.py).
If you need a tensor library, wrap it behind an opaque `TensorRef`
string so the engine never sees a native tensor — that is the contract
the universal layer enforces.

## 7. What's `PERTURBATION_STABILITY_FLOOR` and how do I override it?

It is the module-level constant `PERTURBATION_STABILITY_FLOOR` in
[`adaptive_reflow/frame/channel_rule.py`](adaptive_reflow/frame/channel_rule.py)
(default `0.5`). The gate closes on a channel when its
`perturbation_stability_lower_bound` falls strictly below this floor —
i.e. the metric becomes unstable under the stability perturbation
protocol. To override, pass a custom
[`StabilityPerturbationProtocol`](adaptive_reflow/eval/calibration.py)
to your calibration manifest rather than mutating the constant; the
constant is part of the public surface.

## 8. How does the docs scanner know what's true?

[`tools/check_docs_against_code.py`](tools/check_docs_against_code.py)
walks every governance doc (`README.md`, `ARCHITECTURE.md`,
`STATUS.md`, `DESIGN_BOUNDARY.md`, `CONTRACTS.md`) plus everything
under `docs/`, extracts three claim kinds — python-fenced class /
function names, `adaptive_reflow/...` path references, and inline-
backtick CamelCase identifiers — and resolves each against an
AST-built symbol index of `adaptive_reflow/`. Drift fails the run.
See [`docs/TESTING_STRATEGY.md`](docs/TESTING_STRATEGY.md) §2.7.

## 9. Why does mutmut show "no surviving mutants" as success?

The mutation runner is scoped to
[`contracts/`](adaptive_reflow/contracts/),
[`universal/`](adaptive_reflow/universal/),
[`molecular/`](adaptive_reflow/molecular/), and
[`frame/`](adaptive_reflow/frame/) only
(per `tools/mutate/mutmut.toml`). A green run with zero surviving
mutants means the test suite catches every syntactic mutation the
runner tried in those four scopes — i.e. every branch is reachable.
Surviving mutants in `contracts/` or `universal/` are, by definition,
missing tests and block the PR. See
[`docs/TESTING_STRATEGY.md`](docs/TESTING_STRATEGY.md) §7.

## 10. Why are there xfail tests? How do I close one?

`xfail` markers document a known-broken state and let the suite stay
green while a fix lands. Closing one means: (1) reproduce the
behaviour the test expects, (2) implement the fix, (3) remove the
`@pytest.mark.xfail` decorator (and the `reason=…` arg), (4) run
the targeted test, then the full suite, then the docs scanner. The
fix commit must include an ADR or a `todo.json` entry if the fix
touches a load-bearing boundary.

## 11. What's a golden snapshot?

A JSON file under [`tests/golden/<kernel>/`](tests/golden/) that
records a kernel's input + output for a curated set of cases. Goldens
are deterministic and re-generated via
[`tools/generate_golden.py`](tools/generate_golden.py); they are
replayed by
[`tests/property/test_golden_replay.py`](tests/property/test_golden_replay.py)
and gate refactors that change kernel behaviour. They are the
property-test analogue of a snapshot regression test.

## 12. How do I run the stress tests?

The stress profile lives in
[`tests/perf/test_stress_1000_rounds.py`](tests/perf/test_stress_1000_rounds.py);
every test is decorated with `@pytest.mark.stress` and runs only
on the stress-nightly workflow:

```bash
PYTHONPATH=. ./.venv/Scripts/python.exe -m pytest tests/perf/ \
    -m stress --no-header -q
```

The profile keeps each test inside a wall-clock budget so the
nightly job stays green even on slow Windows file-IO. See
[`docs/PERFORMANCE_BUDGETS.md`](docs/PERFORMANCE_BUDGETS.md).

## 13. Where do I put a new ADR?

Under [`docs/adr/`](docs/adr/) with a numeric prefix
(`NNNN-kebab-case-slug.md`). The prefix is monotonic but otherwise
meaningless; the slug is the searchable identifier. Follow the
MADR 4.0 template that
[ADR-0001](docs/adr/0001-record-architecture-decisions.md)
demonstrates: frontmatter (status, date, deciders, consulted,
informed) plus body sections (Context, Decision Drivers, Considered
Options, Decision Outcome, Consequences, Confirmation, More
Information). The doc scanner indexes ADR filenames.

## 14. How do I deprecate a public symbol?

Three steps. (1) Move the implementation under
[`adaptive_reflow/legacy/`](adaptive_reflow/legacy/) (or keep it
where it is). (2) Make `legacy/__init__.py` emit a
`DeprecationWarning` at import time so accidental dependents are
warned. (3) Remove the re-export from the curated
`__init__.py` of the package that used to expose it. Existing
tests stay green (legacy tests are quarantined under
`@pytest.mark.legacy`) until the symbol is fully removed in a
follow-up pass.

## 15. What's the policy for breaking changes?

Bumping `OperationCompositionContract.version`
(`DEFAULT_OPERATION_COMPOSITION_VERSION`) is a public breaking
change — every consumer that compares the string directly must
migrate. Renaming or removing a public symbol requires (1) a new
ADR, (2) a paired acceptance test, (3) a `DTB-Q` decision in
`todo.json`, and (4) a one-cycle deprecation window with a
`DeprecationWarning` at import time. The bar is set by
[ADR-0004](docs/adr/0004-engine-seven-step-operation-order.md)
for operation-order changes and
[ADR-0005](docs/adr/0005-fail-closed-audit-code-policy.md)
for audit-code renames.

## 16. How does the engine emit a `RoundTrace` even when the round fails?

Every `Engine.run_round` call wraps the seven-step operation in a
try / except that appends `ERR_*` audit codes to
`EngineRoundResult.audit_codes` and constructs a
`RoundTraceV3` regardless of outcome. The `gate` boolean is
`False` on failure but the trace is byte-equal to a successful
run's trace shape — only the audit-code list differs. That
property is what makes golden replay and the adversarial battery
possible: you can replay a hostile round and still diff the
trace. See
[`adaptive_reflow/frame/engine.py`](adaptive_reflow/frame/engine.py).

## 17. What's `perturbation_stability_lower_bound` and why does the gate close on it?

It is the lower-bound factor on the round's perturbation-stability
score, carried in `RoundResultBundle.perturbation_stability_lower_bound`
(see [`adaptive_reflow/contracts/bundle.py`](adaptive_reflow/contracts/bundle.py)).
The gate closes on a channel when this lower bound falls strictly
below `PERTURBATION_STABILITY_FLOOR` (`0.5` by default) — i.e. the
estimator's stability collapses under the
[`StabilityPerturbationProtocol`](adaptive_reflow/eval/calibration.py).
This is the fail-closed defence against confidently-wrong estimates:
the gate refuses to publish a beta for a channel whose uncertainty
the perturbation protocol cannot bound.

## 18. Why does `validate_round_result_bundle` return `tuple[bool, tuple[str, …]]` instead of raising?

Because the validator is called inside hot-path loops (the engine
itself, the bounded merge, the channel rule) where raising would
force every caller to wrap a `try / except`. Returning
`(ok, errors)` lets callers branch on `ok` and accumulate errors
into the ledger without unwinding the stack. The engine still
fails closed: any `ok=False` path appends `ERR_BUNDLE_INVALID` (and
per-error `ERR_BUNDLE_INVALID:<code>`) to the audit list. See
[`adaptive_reflow/contracts/bundle.py`](adaptive_reflow/contracts/bundle.py).

## 19. What's `source_revoked` and when does it fire?

`AUDIT_SOURCE_REVOKED` is the literal string `"source_revoked"` in
[`adaptive_reflow/contracts/validators.py`](adaptive_reflow/contracts/validators.py).
It is appended to a round's audit list when the source data (the
calibration manifest, evaluator artifact, or upstream bundle) is
marked `revoked=True` after the round has been registered. The gate
closes on every channel that draws from the revoked source. There
is an adversarial test for this path at
[`tests/test_adversarial/test_hostile_cases.py`](tests/test_adversarial/test_hostile_cases.py)
(`test_source_revocation_closes_subsequent_gate`).

## 20. How do I add a new channel to a molecule-aware adapter without breaking the universal layer?

Add the channel to `MOLECULE_CHANNELS` in
[`adaptive_reflow/molecular/channels.py`](adaptive_reflow/molecular/channels.py),
register the `ChannelDomain` in `MOLECULE_DOMAIN_BY_CHANNEL` in
[`adaptive_reflow/molecular/domain.py`](adaptive_reflow/molecular/domain.py),
extend the adapter's `SUPPORTED_CHANNELS` and `CHANNEL_DOMAINS`,
update `MoleculeRoundResultBundle`, and add a paired test. The
universal layer is untouched because the channel vocabulary lives
entirely under `molecular/`; the AST-level guard
([`tests/test_universal/test_no_molecular_import.py`](tests/test_universal/test_no_molecular_import.py))
stays green. See [ADR-0003](docs/adr/0003-universal-vs-molecular-split.md).
