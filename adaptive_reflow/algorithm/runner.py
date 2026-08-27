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

from dataclasses import dataclass, field
from typing import Any, Protocol

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
    PolicyDriverProtocol,
    default_policy_driver,
)
from adaptive_reflow.algorithm.scheduler import (
    SchedulerProtocol,
    default_cosine_scheduler,
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
    hash_policy_hash,
)
from adaptive_reflow.frame.adapter import FlowMatchingODEAdapter, ODEConditionDelta
from adaptive_reflow.frame.engine import (
    Engine,
    PhaseState,
    RoundTrace,
)
from adaptive_reflow.universal.state import StateBundle

# ---------------------------------------------------------------------------
# Evaluator protocol (duck-typed; both Real + Synthetic evaluators satisfy it)
# ---------------------------------------------------------------------------


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
        Identifier of the outer cycle (forwarded to the scheduler's
        ``sample`` method).
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
    """

    n_rounds: int = 20
    outer_cycle_id: int = 0
    target_round: int = 0
    seed: int = 42
    channels: tuple[str, ...] = ("xy",)


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
        oracle keys plus the promoted ``W2`` and ``coverage``.
    algorithm_signatures:
        ``{component_name: config_hash}`` provenance mapping for the
        scheduler, policy driver, merge operator, and blender.
    """

    config: ReInferenceConfig
    round_traces: tuple[RoundTrace, ...]
    final_endpoint_digest: str
    endpoints: NDArray[np.float64]
    per_round_metrics: dict[int, dict[str, float]] = field(default_factory=dict)
    algorithm_signatures: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers (pure)
# ---------------------------------------------------------------------------


def _build_base_policy(
    *,
    schedule_sample: Any,
    beta: float,
    channel: ChannelName,
    target_round: int,
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
    """
    placeholder = FinalRestartPolicy(
        policy_id=PolicyId(f"runner-{target_round}"),
        writer_id=MechanismId("inference.adaptive_reflow"),
        run_id=RunId("runner-run"),
        target_round=int(target_round),
        outer_cycle_id=0,
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


def _build_initial_phase_state(*, horizon_remaining: int) -> PhaseState:
    """Build a deterministic initial :class:`PhaseState` for round 0."""
    return PhaseState(
        outer_cycle_id=0,
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
        self._scheduler: SchedulerProtocol = (
            scheduler if scheduler is not None else default_cosine_scheduler()
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
        """
        n_rounds = int(config.n_rounds)
        if n_rounds < 1:
            raise ValueError("n_rounds must be >= 1")
        channels = tuple(config.channels)
        if not channels:
            raise ValueError("channels must be non-empty")
        primary_channel = ChannelName(str(channels[0]))

        round_traces: list[RoundTrace] = []
        per_round_metrics: dict[int, dict[str, float]] = {}
        endpoints: NDArray[np.float64] = np.empty((n_rounds, 2), dtype=np.float64)
        phase_state = _build_initial_phase_state(horizon_remaining=n_rounds)
        bundle: StateBundle | None = None
        prior_endpoint_digest = ""

        for r in range(n_rounds):
            sample = self._scheduler.sample(
                int(config.outer_cycle_id), r, int(config.target_round) + r
            )
            base_policy = _build_base_policy(
                schedule_sample=sample.as_cosine_schedule_sample(),
                beta=0.0,
                channel=primary_channel,
                target_round=int(config.target_round) + r,
            )
            applied_policy = self._driver.compute_policy(
                sample.as_cosine_schedule_sample(),
                base_policy=base_policy,
                channel=str(primary_channel),
                prior_endpoint_digest=prior_endpoint_digest,
            )
            condition_delta = _build_condition_delta(
                target_round=int(config.target_round) + r,
                source="adaptive_reflow.algorithm.runner",
            )

            if r == 0:
                bundle = self._adapter.build_initial_state(
                    batch_id=f"runner-batch-{channels[0]}",
                    sample_id=f"runner-sample-{channels[0]}-r{r}",
                )

            result = self._engine.run_round(
                round_index=r,
                phase_state=phase_state,
                bundle=bundle,
                adapter=self._adapter,
                policy=applied_policy,
                condition_delta=condition_delta,
                seed=int(config.seed) + r,
            )
            trace = result.round_trace
            round_traces.append(trace)

            # Capture the per-round endpoint (final trajectory point) so
            # downstream consumers (e.g. the ablation script) can compute
            # custom scoring outside the runner. The trajectory is keyed
            # by ``integrator_trace.native_state_digest`` in the
            # adapter's private ``_native_states`` map.
            if trace.integrator_trace is not None:
                native_states = getattr(self._adapter, "_native_states", None)
                if isinstance(native_states, dict):
                    traj_entry = native_states.get(
                        trace.integrator_trace.native_state_digest
                    )
                    if traj_entry is not None and "trajectory" in traj_entry:
                        endpoints[r] = np.asarray(
                            traj_entry["trajectory"][-1], dtype=np.float64
                        ).reshape(2)

            # Per-round metrics: evaluator oracle + algorithm scalars.
            metric: dict[str, float] = {
                "n_cap": float(sample.n_cap),
                "memory_fraction": float(sample.memory_fraction()),
                "beta": float(
                    applied_policy.beta_by_channel.get(primary_channel, 0.0)
                ),
            }
            if self._evaluator is not None and bundle is not None:
                oracle_metrics = self._evaluator.oracle(
                    bundle, channel=primary_channel, seed=int(config.seed) + r
                )
                metric.update({str(k): float(v) for k, v in oracle_metrics.items()})
                # Promote the canonical W2 / coverage keys when present.
                metric["W2"] = float(
                    oracle_metrics.get("raw_score", 0.0)
                )
                metric["coverage"] = float(
                    oracle_metrics.get("bounded_score", 0.0)
                )
            per_round_metrics[r] = metric

            phase_state = result.next_phase_state
            prior_endpoint_digest = str(trace.endpoint_digest)

            # Carry the detached endpoint forward as the next source bundle.
            if trace.integrator_trace is not None and bundle is not None:
                bundle = self._adapter.observe_endpoint(
                    trace.integrator_trace, bundle
                )

        final_endpoint_digest = (
            round_traces[-1].endpoint_digest if round_traces else ""
        )
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
        )

    def run_with_default_engine(self, config: ReInferenceConfig) -> ReInferenceResult:
        """Convenience alias of :meth:`run` (always uses a fresh :class:`Engine`)."""
        self._engine = Engine()
        return self.run(config)


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "ReInferenceConfig",
    "ReInferenceResult",
    "ReInferenceRunner",
]
