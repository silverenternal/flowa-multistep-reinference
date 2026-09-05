"""CLM-034: Universal state machine coverage — every scheduler wrapped.

Asserted by docs/CLAIMS.md:951-1022.
Every scheduler class that `SchedulerProtocol` admits is wrapped with
an observation-only `StateMachine` at the moment `ReInferenceRunner.__init__`
consumes it. The integration lives in
`adaptive_reflow.algorithm.state_machine_integration`.

We pin:
    1. The integration module exposes `wrap_scheduler_with_state_machine`.
    2. The integration module exposes `make_runner_state_machine`.
    3. The orchestrator's lifecycle vocabulary is documented in the
       module's `ORCHESTRATOR_STATES` constant (or equivalent).
"""
from __future__ import annotations

import importlib


def test_claim_034_wrap_scheduler_with_state_machine_exposed() -> None:
    """The wrapper function is importable from state_machine_integration."""
    mod = importlib.import_module(
        "adaptive_reflow.algorithm.state_machine_integration"
    )
    assert hasattr(mod, "wrap_scheduler_with_state_machine"), (
        "wrap_scheduler_with_state_machine missing"
    )


def test_claim_034_make_runner_state_machine_exposed() -> None:
    """The runner state-machine factory is importable."""
    mod = importlib.import_module(
        "adaptive_reflow.algorithm.state_machine_integration"
    )
    assert hasattr(mod, "make_runner_state_machine"), (
        "make_runner_state_machine missing"
    )


def test_claim_034_orchestrator_states_constant_documented() -> None:
    """The orchestrator's lifecycle states are exposed as a constant."""
    mod = importlib.import_module(
        "adaptive_reflow.algorithm.state_machine_integration"
    )
    assert hasattr(mod, "ORCHESTRATOR_STATES"), "ORCHESTRATOR_STATES missing"
    # The constant should be a tuple/list/set of state names.
    states = getattr(mod, "ORCHESTRATOR_STATES")
    assert len(states) >= 3, (
        f"ORCHESTRATOR_STATES has only {len(states)} entries; expected >=3"
    )
