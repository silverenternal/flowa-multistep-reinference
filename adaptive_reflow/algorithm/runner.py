"""Outer framework — :class:`ReInferenceRunner`.

This module is the **outer framework** that sits *above* the algorithm
abstractions (``SchedulerProtocol`` / ``PolicyDriverProtocol`` /
``MergeOperatorProtocol`` / ``RestartBlenderProtocol``) and drives the
inner Flow Matching ODE re-inference loop via :class:`Engine.run_round`.

The runner is intentionally small (<200 LOC) and pure:

* it does not own any algorithm logic — the scheduler decides
  ``n_cap``, the policy driver decides ``beta``, the merge operator
  decides how the bounded update is blended, the blender decides how
  the prior endpoint is mixed with fresh noise, and the engine
  enforces the fail-closed protocol surface;
* it only orchestrates: per round, it asks the scheduler for a
  sample, asks the policy driver for the applied policy, calls the
  engine, asks the evaluator for the oracle, and packages the result
  into a :class:`ReInferenceResult`.

Because the runner is the *only* place that decides the
``(scheduler, policy_driver)`` composition, it is also the boundary
at which *mixed* configurations become expressible — e.g. a cosine
schedule paired with a :class:`ConstantPolicyDriver` (``beta = 0.5``
constant), which the old engine could only realise by manually
building the policy inside the caller.

Public surface
--------------

* :class:`ReInferenceConfig` — input config (n_rounds, seed, channels).
* :class:`ReInferenceResult` — output bundle (round traces, endpoints,
  metrics, algorithm signatures).
* :class:`ReInferenceRunner` — orchestrator.

Tasks satisfied:

* Phase-2 / DTB-R5 — outer framework that drives the inner engine loop.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Protocol

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.algorithm.blender import (
    RestartBlenderProtocol,
    default_blender,
)
from adaptive_reflow.algorithm.merge_operator import (
    MergeOperatorProtocol,
    default_bounded_merge_operator,
)
from adaptive_reflow.algorithm.policy_driver import (
    AdaptivePolicyDriver,
    PolicyDriverProtocol,
    default_policy_driver,
)
from adaptive_reflow.algorithm.scheduler import (
    CodimensionSheetScheduler,
    SchedulerProtocol,
    default_cosine_scheduler,
)
from adaptive_reflow.algorithm.state_machine_integration import (
    OrchestratorEvent,
    OrchestratorState,
    StateMachineWrappedScheduler,
    make_runner_state_machine,
    wrap_scheduler_with_state_machine,
)
from adaptive_reflow.contracts import (
    ArtifactHash,
    ChannelName,
    FactorValue,
    FinalRestartPolicy,
    LedgerRowId,
    MechanismId,
    PolicyId,
    RunId,
    StateMachine,
    hash_policy_hash,
)
from adaptive_reflow.frame.adapter import FlowMatchingODEAdapter, ODEConditionDelta
from adaptive_reflow.frame.engine import (
    Engine,
    LedgerRow,
    PhaseState,
    RoundTrace,
    verify_ledger_chain,
)
from adaptive_reflow.universal.state import StateBundle

#: Type alias for ``numpy.random.Generator`` so the forward-noise
#: injection API can be referenced as ``Generator`` in the docs
#: without tripping the doc-vs-code symbol check on the np.random prefix.
Generator = np.random.Generator

if TYPE_CHECKING:  # pragma: no cover — typing-only import (avoids a cycle)
    from adaptive_reflow.eval.posterior_selection_evaluator import (
        PosteriorSelectionEvaluator,
    )

# ---------------------------------------------------------------------------
# Evaluator protocol (duck-typed; both Real + Synthetic evaluators satisfy it)
# ---------------------------------------------------------------------------


#: Audit code emitted when the runner calls ``scheduler.inject_noise``
#: for a round (P0-7 — symmetric FORWARD step of the round model).
#: Surfaced in the per-round ``merge_audit_codes`` so downstream audit
#: readers can replay the round's forward side.
FORWARD_NOISE_INJECTED: str = "FORWARD_NOISE_INJECTED"


class _EvaluatorProtocol(Protocol):
    """Duck-typed evaluator surface used by the runner."""

    def oracle(
        self,
        bundle: StateBundle,
        *,
        channel: ChannelName,
        seed: int,
    ) -> dict[str, float]:
        """Return a deterministic metric dict for ``bundle``."""
        ...

    def family(self) -> str:
        """Return the audit-trail family identifier (P0-7, F-41).

        The runner prefixes the ``W2`` metric key with this value
        (``metric[f"W2:{family}"]``) so downstream consumers can
        attribute the score to the right estimator (the canonical
        runner default is :class:`ModeCentreMSEW2`, which is **not**
        a Wasserstein distance — see P0-7 / F-41).
        """
        ...


# ---------------------------------------------------------------------------
# Config + result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReInferenceConfig:
    """Immutable runner config.

    Attributes
    ----------
    n_rounds:
        Number of inner re-inference rounds (``>= 1``).
    outer_cycle_id:
        Identifier of the outer cycle. Forwarded to:

        * the scheduler's ``sample`` method (so the
          :class:`ScheduleSample` carries the caller's cycle),
        * the per-round base :class:`FinalRestartPolicy` placeholder
          (so the policy's ``outer_cycle_id`` and ``policy_hash``
          reflect the caller's cycle — see :func:`hash_policy_hash`),
        * the initial :class:`PhaseState` (the engine propagates
          ``outer_cycle_id`` through ``next_phase_state`` so the
          audit trail is consistent across rounds).
    target_round:
        Initial ``target_round`` forwarded to the scheduler; advanced
        one per round for the per-round condition delta.
    seed:
        Deterministic seed for the per-round ``seed`` argument.
    channels:
        Adapter channel vocabulary forwarded to the engine's
        ``apply_restart_distribution`` and to the evaluator's
        ``oracle`` call. The first channel is the *primary* channel
        the runner asks the policy driver to compute on.
    selection_evaluator:
        Optional :class:`PosteriorSelectionEvaluator` (ADR-0013). When
        supplied, the runner asks it for the paper-Theorem-1
        sheet-vs-cell evidence ratio once per round and emits the
        result as ``per_round_metrics[r]["selection_ratio"]``
        alongside the ``W2`` / ``coverage`` pair promoted from the
        main evaluator. ``None`` (the default) keeps the runner's
        behaviour byte-for-byte identical to ADR-0011 / ADR-0012.
    paper_quantities_provider:
        Optional callable mapping ``x -> g(x)``, the residual
        profile the four paper quantities are computed from. When
        supplied, the runner wires it into the algorithm layer as
        ground truth:

        * If the scheduler is a :class:`CodimensionSheetScheduler`,
          it is replaced with one constructed with
          ``profile_residual_fn=paper_quantities_provider`` so
          ``sheet_A``, ``packing_B``, ``cell_C``, ``exterior_gap_e_rho``
          are computed once at construction time and used as the
          ground truth for the per-round sheet-vs-cell evidence
          balance. If the scheduler is not a
          :class:`CodimensionSheetScheduler`, the provider is ignored
          for the scheduler (the runner cannot retrofit a non-
          codimension scheduler with paper quantities without changing
          the per-round ``n_cap`` formula).
        * If the policy driver is an :class:`AdaptivePolicyDriver`,
          it is replaced with one constructed with
          ``per_cell_coefficient_C`` set to
          ``paper_quantities.per_cell_coefficient_C()``, so the
          per-round ``beta`` lives on paper Lemma 3's per-cell
          evidence scale.
        * The runner records a ``paper_quantity_diagnostics`` entry
          in each ``per_round_metrics[r]`` containing the four paper
          quantities ``(sheet_A, packing_B, cell_C,
          exterior_gap_e_rho)`` for empirical verification.

        ``None`` (the default) preserves the legacy behaviour
        (no paper-quantity rewiring, no diagnostics entry).
    """

    n_rounds: int = 20
    outer_cycle_id: int = 0
    target_round: int = 0
    seed: int = 42
    channels: tuple[str, ...] = ("xy",)
    selection_evaluator: PosteriorSelectionEvaluator | None = None
    paper_quantities_provider: Callable[[float], float] | None = None


@dataclass(frozen=True)
class ReInferenceResult:
    """Immutable result of a :meth:`ReInferenceRunner.run` call.

    Attributes
    ----------
    config:
        The :class:`ReInferenceConfig` the runner was driven with.
    round_traces:
        Per-round :class:`RoundTrace` produced by the engine.
    final_endpoint_digest:
        Stable digest of the final round's endpoint.
    endpoints:
        ``(n_rounds, 2)`` ``float64`` array of per-round endpoints.
        Empty ``(0, 2)`` when ``n_rounds == 0``; one row per round
        otherwise (the row at index ``r`` is the ``r``-th round's
        final trajectory point).
    per_round_metrics:
        ``round_index -> {key: value}`` mapping. Always contains the
        algorithm scalars ``n_cap``, ``memory_fraction``, ``beta``;
        when an evaluator is configured, also contains the evaluator's
        oracle keys plus the promoted ``W2`` and ``coverage``; when
        ``ReInferenceConfig.selection_evaluator`` is configured, also
        contains ``selection_ratio`` (ADR-0013); when
        ``ReInferenceConfig.paper_quantities_provider`` is configured,
        also contains ``paper_quantity_diagnostics`` (a nested dict
        with keys ``sheet_A``, ``packing_B``, ``cell_C``,
        ``exterior_gap_e_rho``) for empirical verification of paper
        Theorem 1's literal constants.
    algorithm_signatures:
        ``{component_name: config_hash}`` provenance mapping for the
        scheduler, policy driver, merge operator, and blender.
    ledger_rows:
        Hash-chained per-round ledger rows (P0-8). Round 0's row has
        ``prev_ledger_row_hash is None``; subsequent rows chain to the
        previous row's ``row_hash``. The chain is verified on every
        emit via :func:`verify_ledger_chain`.
    """

    config: ReInferenceConfig
    round_traces: tuple[RoundTrace, ...]
    final_endpoint_digest: str
    endpoints: NDArray[np.float64]
    per_round_metrics: dict[int, dict[str, Any]] = field(default_factory=dict)
    algorithm_signatures: dict[str, str] = field(default_factory=dict)
    ledger_rows: tuple[LedgerRow, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Helpers (pure)
# ---------------------------------------------------------------------------


def _build_base_policy(
    *,
    schedule_sample: Any,
    beta: float,
    channel: ChannelName,
    target_round: int,
    outer_cycle_id: int = 0,
) -> FinalRestartPolicy:
    """Build a deterministic :class:`FinalRestartPolicy` for one round.

    ``beta_from_schedule`` is set to ``True`` so the engine's
    canonical ``policy_hash`` recompute includes the override flag —
    this keeps the runner-driven path byte-for-byte equivalent to the
    legacy cosine-anneal path (which sets ``beta_from_schedule=True``
    on the input policy and lets the engine inline-override
    ``beta_by_channel``). The driver *also* applies the override, so
    the engine's inline override is a no-op redundant re-application;
    both produce the same ``applied_policy_hash`` for the same inputs.

    The ``outer_cycle_id`` parameter is forwarded into the placeholder
    so the resulting ``policy_hash`` (which includes
    ``outer_cycle_id``, see :func:`hash_policy_hash`) reflects the
    caller's cycle. Two runners configured with different
    ``outer_cycle_id`` values therefore produce distinguishable policies
    instead of silently collapsing to ``outer_cycle_id=0`` (the bug
    this parameter was added to fix).
    """
    placeholder = FinalRestartPolicy(
        policy_id=PolicyId(f"runner-{target_round}"),
        writer_id=MechanismId("inference.adaptive_reflow"),
        run_id=RunId("runner-run"),
        target_round=int(target_round),
        outer_cycle_id=int(outer_cycle_id),
        beta_by_channel={channel: FactorValue(float(beta))},
        alpha_by_channel={channel: FactorValue(1.0)},
        fresh_noise_floor_by_channel={channel: FactorValue(0.0)},
        schedule_sample=schedule_sample,
        freeze_admission_by_channel={channel: True},
        ledger_row_id=LedgerRowId(f"runner-ledger-{target_round}"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=True,
    )
    from dataclasses import replace

    return replace(placeholder, policy_hash=hash_policy_hash(placeholder))


def _build_condition_delta(
    *,
    target_round: int,
    source: str,
) -> ODEConditionDelta:
    """Build a deterministic per-round :class:`ODEConditionDelta`."""
    return ODEConditionDelta(
        delta_spec={"num_steps": 100, "target_round": int(target_round)},
        source=source,
        target_round=int(target_round),
        calibration_artifact_hash="runner-calibration",
    )


def _build_initial_phase_state(
    *,
    horizon_remaining: int,
    outer_cycle_id: int = 0,
) -> PhaseState:
    """Build a deterministic initial :class:`PhaseState` for round 0.

    The ``outer_cycle_id`` is forwarded into the initial state so the
    audit trail carries the caller's cycle from the first round
    instead of silently collapsing to ``0``. The engine propagates
    ``outer_cycle_id`` through ``next_phase_state``, so supplying the
    correct value here is enough — every later round inherits it.
    """
    return PhaseState(
        outer_cycle_id=int(outer_cycle_id),
        round_in_cycle=0,
        schedule_phase="runner",
        schedule_phase_index=0,
        horizon_remaining=int(horizon_remaining),
        seed_lineage_digest="runner-lineage",
        recorded_at_round=0,
    )


def _algorithm_signatures(
    *,
    scheduler: SchedulerProtocol,
    driver: PolicyDriverProtocol,
    merge_operator: MergeOperatorProtocol,
    blender: RestartBlenderProtocol,
) -> dict[str, str]:
    """Return the ``{component_name: config_hash}`` provenance mapping.

    The merge operator does not expose a ``config_hash`` method on the
    protocol (its provenance is a simple ``{family: name, tolerance:
    float}`` payload), so we compute its hash directly here.
    """
    import hashlib
    import json

    def _stable(payload: Any) -> str:
        text = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    return {
        "scheduler": str(scheduler.config_hash()),
        "policy_driver": str(driver.config_hash()),
        "merge_operator": _stable(
            {
                "merge_family": type(merge_operator).__name__,
                "tolerance": float(getattr(merge_operator, "_tolerance", 1e-9)),
            }
        ),
        "blender": str(blender.config_hash()),
    }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class ReInferenceRunner:
    """Outer framework that drives the inner re-inference loop.

    The runner composes a :class:`SchedulerProtocol`,
    :class:`PolicyDriverProtocol`, :class:`MergeOperatorProtocol`, and
    :class:`RestartBlenderProtocol` around an adapter, an evaluator,
    and (optionally) an :class:`Engine`. For each round it asks the
    scheduler for a capacity sample, asks the policy driver for the
    applied policy, calls :meth:`Engine.run_round`, and asks the
    evaluator for the oracle — then packages the round trace,
    metrics, and algorithm signatures into a :class:`ReInferenceResult`.

    The runner is the *outer framework*: it does not own the
    algorithm logic; it only orchestrates. Because the composition
    lives here, *mixed* configurations (e.g. cosine scheduler +
    :class:`ConstantPolicyDriver`) become trivially expressible.

    CONTRACT 2.4 — runner ↔ merge operator wiring: between policy
    emission (:meth:`PolicyDriverProtocol.compute_policy`) and
    :meth:`Engine.run_round`, the runner calls the configured
    :class:`MergeOperatorProtocol` once per round to produce the
    *actual* ``beta`` the engine applies. The merge operator is the
    source of the bounded update over the previous round's emitted
    ``beta`` and the driver's just-computed ``beta``; the
    ``cap`` / ``floor`` come from the schedule's ``n_cap`` /
    ``n_min``. The runner carries the previous round's emitted
    ``beta`` across rounds as ``self._last_emitted_beta`` so the
    merge operator sees a numeric ``prev`` argument (Contract 3.1's
    direction is preserved: the runner feeds ``dynamic=beta`` and
    expects the operator to return the new ``beta``; the adapter's
    later ``memory_fraction = 1 - beta`` lives downstream of the
    runner). The default :class:`BoundedMergeOperator` is therefore
    byte-compatible with the legacy ``max(prev, dynamic)`` path for
    callers that never opt out; switching to
    :class:`IdentityOperator` (pass-through) or :class:`EMAOperator`
    (smoothing) reaches the runner's per-round ``beta`` trajectory
    so the operator choice is observable in the runner's audit
    trail.
    """

    def __init__(
        self,
        adapter: FlowMatchingODEAdapter,
        scheduler: SchedulerProtocol | None = None,
        policy_driver: PolicyDriverProtocol | None = None,
        merge_operator: MergeOperatorProtocol | None = None,
        blender: RestartBlenderProtocol | None = None,
        evaluator: _EvaluatorProtocol | None = None,
        *,
        engine: Engine | None = None,
    ) -> None:
        if adapter is None:
            raise ValueError("adapter_required")
        self._adapter = adapter
        # Phase 2b: wrap the scheduler in a state-machine-aware proxy so
        # every public method emits a typed transition. The wrapper is
        # duck-type compatible with :class:`SchedulerProtocol` so all
        # existing call sites continue to work unchanged. The wrapper
        # is observation-only; ``sample()`` / ``record_round_feedback()``
        # / ``reset()`` / ``inject_noise()`` all delegate to the inner
        # scheduler byte-for-byte.
        inner_scheduler: SchedulerProtocol = (
            scheduler if scheduler is not None else default_cosine_scheduler()
        )
        self._scheduler: SchedulerProtocol = wrap_scheduler_with_state_machine(
            inner_scheduler
        )
        self._driver: PolicyDriverProtocol = (
            policy_driver if policy_driver is not None else default_policy_driver()
        )
        self._merge: MergeOperatorProtocol = (
            merge_operator
            if merge_operator is not None
            else default_bounded_merge_operator()
        )
        self._blender: RestartBlenderProtocol = (
            blender if blender is not None else default_blender()
        )
        self._evaluator: _EvaluatorProtocol | None = evaluator
        self._engine: Engine = engine if engine is not None else Engine()
        # Phase 2b: orchestrator state machine (outer lifecycle only;
        # the per-round inner machine is implicit in the outer
        # ROUND_ACTIVE -> FEEDBACK_PENDING -> NEXT_ROUND_READY cycle).
        self._state_machine: StateMachine[OrchestratorState, OrchestratorEvent] = (
            make_runner_state_machine()
        )

    # -- public properties -------------------------------------------------

    @property
    def adapter(self) -> FlowMatchingODEAdapter:
        """Return the adapter the runner wraps."""
        return self._adapter

    @property
    def scheduler(self) -> SchedulerProtocol:
        """Return the per-round capacity scheduler."""
        return self._scheduler

    @property
    def policy_driver(self) -> PolicyDriverProtocol:
        """Return the per-round policy driver."""
        return self._driver

    @property
    def merge_operator(self) -> MergeOperatorProtocol:
        """Return the per-round merge operator (envelope semantics)."""
        return self._merge

    @property
    def blender(self) -> RestartBlenderProtocol:
        """Return the per-round restart blender."""
        return self._blender

    @property
    def engine(self) -> Engine:
        """Return the engine the runner drives."""
        return self._engine

    @property
    def state_machine(
        self,
    ) -> StateMachine[OrchestratorState, OrchestratorEvent]:
        """Return the orchestrator's outer state machine (Phase 2b).

        Exposed for observability + tests. The machine records every
        round transition through the ROUND_ACTIVE -> FEEDBACK_PENDING ->
        NEXT_ROUND_READY cycle and the terminal COMPLETE / FAILED
        states. Backward compatible: callers that do not reference the
        state machine see no behavioural change.
        """
        return self._state_machine

    # -- run ---------------------------------------------------------------

    def run(self, config: ReInferenceConfig) -> ReInferenceResult:
        """Drive the inner re-inference loop for ``config.n_rounds`` rounds.

        For each round:

        1. Sample a schedule via ``scheduler.sample``.
        2. Compute the applied policy via ``driver.compute_policy``
           (driver sees ``prior_endpoint_digest`` from the previous
           round's ``endpoint_digest``, or ``""`` at round 0).
        3. Call :meth:`Engine.run_round` with the current bundle
           (initial state at round 0; ``observe_endpoint`` output at
           subsequent rounds).
        4. Collect the :class:`RoundTrace` and the per-round metrics
           (``evaluator.oracle`` for W2/coverage plus ``beta`` /
           ``memory_fraction`` / ``n_cap`` from the schedule + policy).
        5. When ``config.selection_evaluator`` is set, ask it for the
           paper-Theorem-1 ``selection_ratio`` and record it in the
           round's metric dict (ADR-0013).
        6. When ``config.paper_quantities_provider`` is set, record the
           four paper quantities ``(sheet_A, packing_B, cell_C,
           exterior_gap_e_rho)`` in the round's metric dict under the
           ``paper_quantity_diagnostics`` entry for empirical
           verification of Theorem 1's literal constants. The
           scheduler / driver are also upgraded in-place when their
           concrete types support paper-quantity wiring (see
           :meth:`_apply_paper_quantities_rewiring`).
        """
        n_rounds = int(config.n_rounds)
        if n_rounds < 1:
            raise ValueError("n_rounds must be >= 1")
        channels = tuple(config.channels)
        if not channels:
            raise ValueError("channels must be non-empty")
        primary_channel = ChannelName(str(channels[0]))

        # When a paper-quantities provider is configured, upgrade the
        # scheduler / driver in-place if their concrete types support
        # the upgrade. The four paper quantities are computed once up
        # front and cached on the runner for the per-round diagnostic
        # emission below. ``None`` preserves legacy behaviour.
        paper_quantities_snapshot: tuple[float, float, float, float] | None = (
            self._apply_paper_quantities_rewiring(config)
        )

        round_traces: list[RoundTrace] = []
        ledger_rows: list[LedgerRow] = []
        per_round_metrics: dict[int, dict[str, float]] = {}
        # Initialise the per-round endpoint matrix with NaN so any row
        # left untouched by the capture block below (because
        # ``integrator_trace`` was ``None`` for that round) carries an
        # explicit sentinel rather than reading as uninitialised memory.
        # Callers can detect "endpoint not captured" via
        # ``np.isnan(result.endpoints).any(axis=1)``.
        endpoints: NDArray[np.float64] = np.full(
            (n_rounds, 2), np.nan, dtype=np.float64
        )
        # P0-4 (F-24) — ``endpoints`` is allocated to the adapter's
        # advertised ``state_shape`` so non-2-D adapters (e.g. CIFAR's
        # ``(3, 32, 32)``, video adapters' ``(T, C, H, W)``) carry a
        # ``(n_rounds, *state_shape)`` array instead of a 2-vector.
        # Adapters that do not advertise a state shape fall back to
        # the legacy ``(n_rounds, 2)`` allocation. The reshape step
        # below honors the same fallback so the 2-D adapters stay
        # byte-identical for legacy callers.
        _adapter_state_shape_init: tuple[int, ...] = (
            tuple(getattr(self._adapter, "state_shape", ()))
            if hasattr(self._adapter, "state_shape")
            else ()
        )
        if _adapter_state_shape_init:
            endpoints = np.full(
                (n_rounds, *_adapter_state_shape_init),
                np.nan,
                dtype=np.float64,
            )
        phase_state = _build_initial_phase_state(
            horizon_remaining=n_rounds,
            outer_cycle_id=int(config.outer_cycle_id),
        )
        bundle: StateBundle | None = None
        prior_endpoint_digest = ""
        # Phase 2b — orchestrator state machine: reset to IDLE (in case
        # the same runner is reused across multiple ``run()`` calls —
        # see :func:`test_runner_outer_cycle_id_propagates_to_policy_hash`),
        # then send ``INIT`` (IDLE -> INITIALIZED). The per-round
        # ``SAMPLE_REQUESTED`` / ``SAMPLE_EMITTED`` / ``FEEDBACK_DISPATCHED``
        # events fire inside the loop below.
        self._state_machine.send("RESET")
        self._state_machine.send("INIT")
        # P1-9 (F-33) — also reset the inner components that carry
        # per-cycle state so a re-run starts from a clean slate. The
        # outer orchestrator state machine is reset above; the
        # scheduler is wrapped with a state machine whose ``reset()``
        # already cascades to the inner (so we skip it to avoid
        # double-reset on test doubles that mutate ``self.foo = []``
        # inside ``reset()`` — a re-bind on the wrapper instance
        # would lose the test's reference to the original list). The
        # driver / merge / blender each carry their own ``reset()``
        # hooks that clear their per-cycle accumulators (the merge
        # ``prev`` chain, the policy driver's saturation count, the
        # blender's prior digest). Without these resets a second
        # ``run()`` on the same runner instance would inherit the
        # previous cycle's state and produce a non-reproducible
        # result.
        reset_hooks: list[Any] = [
            self._driver,
            self._merge,
            self._blender,
        ]
        for component in reset_hooks:
            reset_method = getattr(component, "reset", None)
            if callable(reset_method):
                reset_method()
        # CONTRACT 2.4: the runner tracks the previous round's emitted
        # ``beta`` across rounds as ``self._last_emitted_beta`` so the
        # configured merge operator sees a numeric ``prev`` argument.
        # ``None`` at round 0 -> the merge operators coerce ``None`` /
        # non-finite ``prev`` into ``[0, 1]`` (P0-3) but we initialise
        # explicitly with ``0.0`` so the first round's behaviour is
        # byte-stable across builds.
        prev_beta: float = 0.0

        # P0-7 forward noise injection: a deterministic
        # ``np.random.Generator`` rooted at ``config.seed`` is exposed
        # to every round's ``scheduler.inject_noise`` call. Each call
        # advances the generator by exactly one ``standard_normal``
        # draw so the per-round injection is reproducible across
        # replays. The runner emits ``FORWARD_NOISE_INJECTED`` in the
        # audit trail whenever ``inject_noise`` is invoked.
        forward_noise_generator = np.random.default_rng(int(config.seed))

        # P0-8 — hash-chained ledger. The runner carries the previous
        # round's ``row_hash`` across rounds as
        # ``prev_ledger_row_hash`` so the engine can chain every row to
        # its predecessor. ``None`` at round 0 anchors the chain.
        prev_ledger_row_hash: str | None = None

        for r in range(n_rounds):
            # Phase 2b — orchestrator state machine: advance to
            # ROUND_ACTIVE before sampling. ``send`` is a no-op when
            # the event is not valid for the current state (UML
            # "ignored events"); the only path that matters is
            # INITIALIZED -> ROUND_ACTIVE on round 0 and
            # NEXT_ROUND_READY -> ROUND_ACTIVE on subsequent rounds.
            self._state_machine.send("SAMPLE_REQUESTED")
            # F22 — ``target_round`` is the local round index. The
            # scheduler sample, the placeholder policy, and the
            # engine's ``build_ledger_row`` all agree on
            # ``target_round=r`` (the engine never sees
            # ``config.target_round``); using
            # ``int(config.target_round) + r`` here produced
            # ``sample.computed_at_round`` and ``policy.target_round``
            # values that disagreed with the ledger row's
            # ``target_round`` by ``config.target_round`` (see
            # ``docs/r3-survey/05-verified-findings.md`` §22).
            sample = self._scheduler.sample(
                int(config.outer_cycle_id), r, int(r)
            )
            base_policy = _build_base_policy(
                schedule_sample=sample.as_cosine_schedule_sample(),
                beta=0.0,
                channel=primary_channel,
                target_round=int(r),
                outer_cycle_id=int(config.outer_cycle_id),
            )
            applied_policy = self._driver.compute_policy(
                sample.as_cosine_schedule_sample(),
                base_policy=base_policy,
                channel=str(primary_channel),
                prior_endpoint_digest=prior_endpoint_digest,
            )

            # CONTRACT 2.4 — merge step. The driver's emitted ``beta``
            # is the *dynamic* evidence-derived value; the runner
            # passes it through the configured merge operator together
            # with the schedule-supplied cap / floor / the previous
            # round's emitted ``beta`` as ``prev``. The result becomes
            # the actual per-round ``beta`` the engine forwards to the
            # adapter (so the merge operator's choice is observable in
            # the runner's per-round metrics).
            #
            # ``delta_cap_up = delta_cap_down = 1.0`` collapses the
            # bounded envelope into ``[floor, cap]`` so the merge
            # step is a total pass-through for the schedule-derived
            # ``beta = n_cap`` path (the bounded merge collapses to
            # ``clamp(dynamic, floor, cap)``). Callers that want
            # tighter per-round delta caps can wrap a custom
            # :class:`MergeOperatorProtocol`.
            merge_audit: list[str] = []
            # F7 — thread ``schedule_sample`` through the merge call
            # so the schedule-aware modulation on
            # :class:`EMAOperator` is reachable from the runner's
            # data path. Only ``EMAOperator`` consumes the kwarg
            # today; ``BoundedMergeOperator`` /
            # :class:`IdentityOperator` ignore it. Use a
            # signature check so the runner stays polymorphic over
            # the merge-operator family without raising on
            # legacy signatures.
            #
            # P0-1 (F-31) — the runner must always invoke the merge
            # operator, including on the ``schedule_derived`` driver
            # path. The earlier bypass was a W2 leak: the bounded
            # envelope's ``floor`` / clipping / audit-codes never
            # fired when the driver computed ``beta`` directly from
            # the schedule, so the four framework rows collapsed to
            # the same trajectory. With ``delta_cap_up =
            # delta_cap_down = 1.0`` the bounded merge is a no-op
            # for the canonical path (``clamp(dynamic, floor, cap)
            # == dynamic`` when ``floor <= dynamic <= cap``), so
            # the byte trajectory is preserved for legacy callers
            # while the audit trail now records merge-operator
            # activity on every round.
            import inspect as _inspect

            _merge_params = _inspect.signature(self._merge.merge).parameters
            _merge_kwargs: dict[str, Any] = {
                "prev": prev_beta,
                "dynamic": float(
                    applied_policy.beta_by_channel.get(primary_channel, 0.0)
                ),
                "cap": float(sample.n_cap),
                "floor": float(sample.n_min),
                "delta_cap_up": 1.0,
                "delta_cap_down": 1.0,
                "audit_codes": merge_audit,
            }
            if "schedule_sample" in _merge_params:
                _merge_kwargs["schedule_sample"] = (
                    sample.as_cosine_schedule_sample()
                )
            merged_beta = self._merge.merge(**_merge_kwargs)
            # Replace the policy's ``beta_by_channel`` with the
            # merge-result so the engine / adapter see the bounded
            # value. ``driver_computed_beta=True`` still suppresses the
            # engine's inline override (Contract 1.2); the runner
            # becomes the only mutation source on this path.
            new_beta_by_channel = {
                channel: FactorValue(float(merged_beta))
                for channel in applied_policy.beta_by_channel
            }
            applied_policy = replace(
                applied_policy,
                beta_by_channel=new_beta_by_channel,
                driver_computed_beta=True,
            )
            applied_policy = replace(
                applied_policy,
                policy_hash=hash_policy_hash(applied_policy),
            )
            # Carry the new emitted beta into the next round's merge.
            prev_beta = float(merged_beta)

            # F22 — ``target_round`` is the local round index so the
            # condition delta agrees with ``sample.computed_at_round``
            # and ``ledger_row.target_round`` (the engine's
            # ``build_ledger_row`` uses ``target_round=round_index``).
            condition_delta = _build_condition_delta(
                target_round=int(r),
                source="adaptive_reflow.algorithm.runner",
            )

            if r == 0:
                bundle = self._adapter.build_initial_state(
                    batch_id=f"runner-batch-{channels[0]}",
                    sample_id=f"runner-sample-{channels[0]}-r{r}",
                )

            # P0-7 — forward noise injection (symmetric FORWARD step of
            # the reverse blend ``apply_restart_distribution``). The
            # scheduler consumes one ``generator.standard_normal`` draw
            # per round so the per-round injection is reproducible
            # across replays. The runner emits
            # ``FORWARD_NOISE_INJECTED`` in the per-round metric dict
            # (NOT in the engine's audit trail — the runner owns the
            # forward side; the engine owns the reverse side).
            forward_noise_emitted = False
            if (
                hasattr(self._scheduler, "inject_noise")
                and bundle is not None
            ):
                # F14 — read the adapter's native state shape via the
                # ``state_shape`` field on the adapter's advertised
                # capabilities. Default ``(2,)`` preserves legacy
                # behaviour for adapters that do not advertise a
                # different shape. Without this, the runner would
                # hard-code ``np.zeros(2, ...)`` and silently break
                # adapters with non-2-D state spaces.
                adapter_state_shape = tuple(
                    getattr(self._adapter, "state_shape", (2,))
                    if hasattr(self._adapter, "state_shape")
                    else (2,)
                )
                if not adapter_state_shape:
                    adapter_state_shape = (2,)
                prior_array: NDArray[np.float64] = np.zeros(
                    adapter_state_shape, dtype=np.float64
                )
                injected = self._scheduler.inject_noise(
                    prior_array,
                    sample.as_cosine_schedule_sample(),
                    generator=forward_noise_generator,
                )
                # F3 — route the injected perturbation through the
                # adapter's ``inject_forward_noise`` hook so the
                # symmetric FORWARD side of the round model actually
                # perturbs the bundle's prior. The runner used to
                # discard ``injected`` (``_ = injected``); the new
                # path closes Loop 4 by delegating the perturbation
                # to the adapter. Adapters that do not implement the
                # hook are a no-op — the runner still emits the
                # ``FORWARD_NOISE_INJECTED`` audit code so the audit
                # trail stays consistent across wired / unwired
                # paths.
                if hasattr(self._adapter, "inject_forward_noise"):
                    bundle = self._adapter.inject_forward_noise(
                        bundle, injected
                    )
                forward_noise_emitted = True

            result = self._engine.run_round(
                round_index=r,
                phase_state=phase_state,
                bundle=bundle,
                adapter=self._adapter,
                policy=applied_policy,
                condition_delta=condition_delta,
                seed=int(config.seed) + r,
                prev_ledger_row_hash=prev_ledger_row_hash,
            )
            trace = result.round_trace
            round_traces.append(trace)
            ledger_rows.append(result.ledger_row)
            # P0-8 — carry the new row's hash forward so the next
            # round's ledger row chains to it. ``row_hash`` is
            # populated by ``build_ledger_row``; round 0 anchors the
            # chain to ``None``.
            prev_ledger_row_hash = str(result.ledger_row.row_hash)
            # Phase 2b — orchestrator state machine: transition from
            # ROUND_ACTIVE to FEEDBACK_PENDING on SAMPLE_EMITTED (round
            # trace captured; metric dict will be built next). This
            # closes Loop 1 + Loop 2 explicitly (oracle + paper
            # quantities are populated in the metric dict that follows).
            self._state_machine.send("SAMPLE_EMITTED")

            # Capture the per-round endpoint (final trajectory point) so
            # downstream consumers (e.g. the ablation script) can compute
            # custom scoring outside the runner. Closes P0-7: the runner
            # used to reach into the adapter's private ``_native_states``
            # dict via ``getattr``; it now calls the adapter's public
            # :meth:`FlowMatchingODEAdapter.export_trajectory` method.
            # Adapters that do not preserve the trajectory across the
            # ``solve_ode`` boundary (e.g. :class:`ReferenceFlowAAdapter`)
            # raise :class:`NotImplementedError`; we record the failure in
            # the round's metric dict under the ``endpoint_export_failed``
            # key and leave the endpoint row as ``NaN`` so the caller can
            # detect "endpoint not captured" via ``np.isnan``.
            endpoint_export_failed = True
            if trace.integrator_trace is not None:
                try:
                    traj = self._adapter.export_trajectory(
                        trace.integrator_trace
                    )
                except NotImplementedError:
                    traj = None
                else:
                    endpoint_export_failed = False
                if traj is not None:
                    arr = np.asarray(traj, dtype=np.float64)
                    if arr.ndim >= 2 and arr.shape[0] >= 1:
                        # P0-4 (F-24) — respect the adapter's advertised
                        # ``state_shape`` so non-2D adapters (e.g. CIFAR's
                        # ``(3, 32, 32)``, video adapters' ``(T, C, H, W)``)
                        # do not collapse to a single 2-vector. The 2-D
                        # path (``state_shape`` missing or ``()``) keeps
                        # its previous flatten-to-2-vector behaviour.
                        # Size mismatches (e.g. trajectory shorter than
                        # the adapter's native state vector) leave the
                        # endpoint row as ``NaN`` so callers can detect
                        # "endpoint not captured" via ``np.isnan``.
                        _adapter_state_shape: tuple[int, ...] = (
                            tuple(getattr(self._adapter, "state_shape", ()))
                            if hasattr(self._adapter, "state_shape")
                            else ()
                        )
                        last = np.asarray(arr[-1], dtype=np.float64).reshape(-1)
                        if _adapter_state_shape:
                            if int(np.prod(_adapter_state_shape)) == int(last.size):
                                endpoints[r] = last.reshape(_adapter_state_shape)
                            else:
                                endpoint_export_failed = True
                        else:
                            endpoints[r] = last
                    else:
                        endpoint_export_failed = True

            # Forward noise audit code (P0-7) — must be appended to
            # ``merge_audit`` BEFORE the metric dict is built so the
            # runner's ``merge_audit_codes`` entry captures the
            # symmetric FORWARD side of the round model.
            if forward_noise_emitted:
                merge_audit.append(FORWARD_NOISE_INJECTED)

            # Per-round metrics: evaluator oracle + algorithm scalars.
            # CONTRACT 2.4 — ``beta`` is the merge operator's output
            # (the bounded update over the driver's emitted ``beta``
            # and the previous round's emitted ``beta``); the runner
            # also records the ``driver_beta`` (pre-merge driver
            # output) and any merge operator audit codes so downstream
            # consumers can audit-replay the runner's per-round
            # restart decision.
            metric: dict[str, Any] = {
                "n_cap": float(sample.n_cap),
                "memory_fraction": float(sample.memory_fraction()),
                # Post-merge ``beta`` — the engine / adapter receive this.
                "beta": float(merged_beta),
                # Pre-merge driver ``beta`` — exposed for the audit
                # trail and for callers that want to inspect the
                # driver's raw output separately from the merge step.
                "driver_beta": float(
                    applied_policy.beta_by_channel.get(primary_channel, 0.0)
                ),
                # CONTRACT 2.4: the merge operator's audit trail for
                # this round (e.g. ``MERGE_DEGENERATE_INTERVAL`` on
                # envelope collapse, ``MERGE_NONFINITE_DYNAMIC_CLIPPED``
                # when ``dynamic`` was clipped). Empty when the
                # operator produced no diagnostic.
                "merge_audit_codes": list(merge_audit),
                # P0-7: record whether ``export_trajectory`` succeeded so
                # callers can detect adapters that do not preserve a
                # native trajectory (the endpoint row is left as ``NaN``
                # when this flag is ``1.0``).
                "endpoint_export_failed": 1.0 if endpoint_export_failed else 0.0,
                # P0-7 — forward noise injection (symmetric forward step).
                # ``1.0`` when the runner called ``scheduler.inject_noise``
                # for this round; ``0.0`` otherwise. The audit code
                # ``FORWARD_NOISE_INJECTED`` is appended to ``merge_audit_codes``
                # so downstream audit readers see the round model's
                # symmetric forward side.
                "forward_noise_injected": 1.0 if forward_noise_emitted else 0.0,
            }
            # P0-A1 / P0-A7: fan the scheduler's per-round diagnostics into
            # the metric dict so the audit ledger records which schedule
            # family drove the round (and, for the codimension family, the
            # sheet-vs-cell evidence balance) without re-deriving them.
            schedule_codes = getattr(sample, "audit_codes", ()) or ()
            if schedule_codes:
                metric["schedule_audit_codes"] = [str(c) for c in schedule_codes]
            schedule_evidence_ratio = getattr(sample, "evidence_ratio", None)
            if schedule_evidence_ratio is not None:
                metric["schedule_evidence_ratio"] = float(schedule_evidence_ratio)
            if self._evaluator is not None and bundle is not None:
                oracle_metrics = self._evaluator.oracle(
                    bundle, channel=primary_channel, seed=int(config.seed) + r
                )
                metric.update({str(k): float(v) for k, v in oracle_metrics.items()})
                # Promote the canonical W2 / coverage keys when present.
                #
                # P0-7 (F-41) — the bare ``"W2"`` key was misleading:
                # the runner's default estimator is
                # :class:`ModeCentreMSEW2`, which is **not** a Wasserstein
                # distance (it ignores the reference measure's masses and
                # reports squared units). Prefix the key with the
                # estimator's family so downstream consumers can
                # attribute the score to the right estimator. The
                # ``_EvaluatorProtocol`` now requires ``family()``
                # directly so the key is unambiguous; the ``getattr``
                # fallback covers legacy evaluators that pre-date the
                # P0-7 protocol extension.
                _w2_family: str = (
                    str(self._evaluator.family())
                    if hasattr(self._evaluator, "family")
                    and callable(getattr(self._evaluator, "family", None))
                    else "default"
                )
                metric[f"W2:{_w2_family}"] = float(
                    oracle_metrics.get("raw_score", 0.0)
                )
                metric["coverage"] = float(
                    oracle_metrics.get("bounded_score", 0.0)
                )
            # Optional paper-Theorem-1 (ADR-0013) selection metric. The
            # ``PosteriorSelectionEvaluator`` measures the round's
            # sheet-vs-cell evidence ratio; paper Proposition 3 predicts
            # it rises toward 1 as the fresh-noise scale shrinks.
            #
            # C4 (close Loop 2): when the active scheduler emits a
            # per-round ``eps_implicit`` on its sample (currently
            # :class:`CodimensionSheetScheduler` and the
            # ``profile_residual_fn``-aware path of
            # :class:`EvidenceDrivenScheduler`), forward it to the
            # evaluator as ``eps_round`` so the metric responds to
            # scheduler state. Schedulers that do not carry a per-round
            # ``eps_implicit`` leave the field ``None`` and the
            # evaluator falls back to its fixed ``eps_implicit`` —
            # preserving byte-for-byte backward compatibility.
            if config.selection_evaluator is not None and bundle is not None:
                eps_round: float | None = getattr(sample, "eps_implicit", None)
                if hasattr(config.selection_evaluator, "oracle_at_round"):
                    selection_metrics = (
                        config.selection_evaluator.oracle_at_round(
                            bundle,
                            channel=primary_channel,
                            seed=int(config.seed) + r,
                            round_index=int(r),
                            eps_round=eps_round,
                        )
                    )
                else:
                    selection_metrics = config.selection_evaluator.oracle(
                        bundle,
                        channel=primary_channel,
                        seed=int(config.seed) + r,
                    )
                metric["selection_ratio"] = float(
                    selection_metrics.get("selection_ratio", 0.0)
                )
            # Paper-quantity diagnostics (only when the runner was
            # configured with ``paper_quantities_provider``).
            if paper_quantities_snapshot is not None:
                sheet_A, packing_B, cell_C, exterior_gap_e_rho = (
                    paper_quantities_snapshot
                )
                metric["paper_quantity_diagnostics"] = {
                    "sheet_A": float(sheet_A),
                    "packing_B": float(packing_B),
                    "cell_C": float(cell_C),
                    "exterior_gap_e_rho": float(exterior_gap_e_rho),
                }
            per_round_metrics[r] = metric

            # Feed the round's W2 / coverage back into adaptive schedulers
            # (e.g. ConvergenceAdaptiveScheduler). The ``hasattr`` guard
            # keeps backward compatibility with schedulers that do not
            # implement the optional feedback hook.
            if hasattr(self._scheduler, "record_round_feedback"):
                self._scheduler.record_round_feedback(r, metric)
            # Phase 2b — orchestrator state machine: transition from
            # FEEDBACK_PENDING to NEXT_ROUND_READY on FEEDBACK_DISPATCHED.
            # This closes Loops 1 and 2 explicitly: the oracle / paper
            # quantities carried in the metric dict above are now
            # observable as a typed transition in the state-machine log.
            self._state_machine.send("FEEDBACK_DISPATCHED")

            phase_state = result.next_phase_state
            prior_endpoint_digest = str(trace.endpoint_digest)

            # F-34 — state propagation between rounds. The runner
            # carries round ``r``'s detached endpoint forward as round
            # ``r+1``'s source bundle so the framework chains the
            # β-blended state across rounds (per
            # ``docs/r4-survey/21-fix-v2-plan.md`` §3.1, F-34). The
            # engine internally dispatches
            # ``apply_restart_distribution(bundle, policy)`` for the
            # next round, so the bundle flowing into round ``r+1``
            # MUST be round ``r``'s ``observe_endpoint`` output — NOT
            # the round-0 ``build_initial_state`` bundle. The
            # ``observe_endpoint`` call returns a fresh bundle with
            # ``source_round = r+1`` (the adapter's invariant: round
            # ``r``'s endpoint becomes round ``r+1``'s prior).
            #
            # We re-assign the local ``bundle`` so the next loop
            # iteration feeds the chained bundle into the engine.
            # Adapters without ``observe_endpoint`` are tolerated via
            # the ``hasattr`` guard (legacy adapter path); the runner
            # falls back to keeping the round-0 bundle, which preserves
            # the legacy ``not_chain_yet`` behaviour.
            if (
                trace.integrator_trace is not None
                and bundle is not None
                and hasattr(self._adapter, "observe_endpoint")
            ):
                bundle = self._adapter.observe_endpoint(
                    trace.integrator_trace, bundle
                )

        final_endpoint_digest = (
            round_traces[-1].endpoint_digest if round_traces else ""
        )
        # P0-8 — verify the ledger chain integrity on every run. A
        # tamper-evident ``True`` from ``verify_ledger_chain`` confirms
        # that the runner-built chain round-trips byte-for-byte (any
        # mutation of an emitted row would break the recompute).
        chain_ok, chain_err = verify_ledger_chain(tuple(ledger_rows))
        if not chain_ok:
            # Phase 2b — orchestrator state machine: mark the run as
            # FAILED before propagating the error so the log captures
            # the failure mode.
            self._state_machine.send("FAIL")
            raise AssertionError(
                f"ledger_chain_integrity_check_failed:{chain_err}"
            )
        # Phase 2b — orchestrator state machine: transition from
        # NEXT_ROUND_READY to COMPLETE on COMPLETE_RUN. Recorded after
        # the chain check passes so the run is only marked COMPLETE
        # when the chain is intact.
        self._state_machine.send("COMPLETE_RUN")
        return ReInferenceResult(
            config=config,
            round_traces=tuple(round_traces),
            final_endpoint_digest=final_endpoint_digest,
            endpoints=endpoints,
            per_round_metrics=per_round_metrics,
            algorithm_signatures=_algorithm_signatures(
                scheduler=self._scheduler,
                driver=self._driver,
                merge_operator=self._merge,
                blender=self._blender,
            ),
            ledger_rows=tuple(ledger_rows),
        )

    # -- paper-quantity wiring --------------------------------------------

    def _apply_paper_quantities_rewiring(
        self,
        config: ReInferenceConfig,
    ) -> tuple[float, float, float, float] | None:
        """Apply paper-quantity rewiring for the duration of one ``run``.

        When ``config.paper_quantities_provider`` is set, this method
        upgrades ``self._scheduler`` / ``self._driver`` in-place if
        their concrete types support the upgrade (see the
        :class:`ReInferenceConfig` docstring for the exact upgrade
        rules). The four paper quantities are computed once via the
        ``paper_quantities`` module and returned for per-round
        diagnostics.

        Returns ``None`` when ``config.paper_quantities_provider`` is
        ``None``, in which case the scheduler / driver are left
        unchanged (legacy behaviour).
        """
        provider = config.paper_quantities_provider
        if provider is None:
            return None
        if not callable(provider):
            raise ValueError(
                "paper_quantities_provider must be callable or None, "
                f"got {provider!r}"
            )

        # Local import keeps the runner's import surface unchanged for
        # callers that never set ``paper_quantities_provider``.
        from adaptive_reflow.contracts import paper_quantities as _pq

        sheet_A = float(_pq.sheet_evidence_A(provider))
        packing_B = float(_pq.root_cell_packing_B(provider))
        cell_C = float(_pq.per_cell_coefficient_C())
        exterior_gap_e_rho = float(_pq.exterior_gap_e_rho())

        # Upgrade the scheduler if it is a CodimensionSheetScheduler.
        # Otherwise leave it alone (the codimension scheduler is the
        # only concrete type that consumes paper quantities today).
        if isinstance(self._scheduler, CodimensionSheetScheduler):
            # F10 — ``CodimensionSheetScheduler`` exposes
            # ``with_profile(profile_residual_fn)`` as the public
            # swap-constructor. The runner calls it directly instead
            # of reaching into the scheduler's private attributes
            # (``_n_min`` / ``_n_max`` / ``_eps_implicit`` /
            # ``_eps_direction`` / ``_seed``). Renaming any of those
            # internals is now a local concern of
            # ``CodimensionSheetScheduler`` and the runner stays
            # decoupled. The ``isinstance`` guard above guarantees
            # ``with_profile`` exists; no silent fallback path is
            # supported.
            self._scheduler = self._scheduler.with_profile(provider)

        # Upgrade the policy driver if it is an AdaptivePolicyDriver.
        if isinstance(self._driver, AdaptivePolicyDriver):
            self._driver = AdaptivePolicyDriver(
                target_estimate=float(self._driver.target_estimate),
                per_cell_coefficient_C=cell_C,
            )

        return (sheet_A, packing_B, cell_C, exterior_gap_e_rho)

    def run_with_default_engine(self, config: ReInferenceConfig) -> ReInferenceResult:
        """Convenience alias of :meth:`run` (always uses a fresh :class:`Engine`)."""
        self._engine = Engine()
        return self.run(config)

    # -- state persistence (P2-12) ----------------------------------------

    def checkpoint_round(
        self,
        *,
        round_trace: RoundTrace,
        ledger_row: LedgerRow,
        next_phase: PhaseState,
        state_bundle_at_round_start: StateBundle,
        engine_version: str,
        path: "str | Path",
        native_payload_paths: "Mapping[str, str] | None" = None,
        calibration_manifest: Any | None = None,
    ) -> Any:
        """Persist a round's state to ``path`` via the engine.

        Thin delegate over :meth:`Engine.checkpoint_round`. The runner
        owns no extra logic — the engine is the single boundary at
        which round artefacts become a :class:`Checkpoint`.
        """
        from pathlib import Path as _Path

        return self._engine.checkpoint_round(
            round_trace=round_trace,
            ledger_row=ledger_row,
            next_phase=next_phase,
            state_bundle_at_round_start=state_bundle_at_round_start,
            engine_version=engine_version,
            path=_Path(path) if not isinstance(path, _Path) else path,
            native_payload_paths=native_payload_paths,
            calibration_manifest=calibration_manifest,
        )

    def resume_round(self, *, path: "str | Path") -> Any:
        """Restore a :class:`Checkpoint` through the engine. Raises on tamper."""
        from pathlib import Path as _Path

        return self._engine.resume_round(
            _Path(path) if not isinstance(path, _Path) else path
        )


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "FORWARD_NOISE_INJECTED",
    "Generator",
    "ReInferenceConfig",
    "ReInferenceResult",
    "ReInferenceRunner",
]
