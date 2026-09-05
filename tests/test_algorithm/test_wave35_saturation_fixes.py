"""Wave 35 saturation fixes — regression tests (FIX-1 / FIX-2 / FIX-3).

Covers the three HIGH-confidence fixes from
``docs/audit/saturation-improvement-plan.md``:

* **FIX-1** — :meth:`CodimensionSheetScheduler.record_round_feedback`
  consumes the runner's per-round signals instead of dropping them.
* **FIX-2** — :meth:`CodimensionSheetScheduler.should_terminate_round`
  plus ``BatchedRunnerConfig.early_termination`` let the runner stop
  paying NFE once the metric has plateaued.
* **FIX-3** — :mod:`adaptive_reflow.algorithm.nfe_allocation` allocates
  per-round NFE by evidence instead of uniformly, and
  ``tools/capability_audit.py``'s G.5 saturation test is applied with
  the metric's orientation.

Every test asserts the *no-degradation* half as well: the default
(opt-out) paths must behave exactly as they did before Wave 35.
"""
from __future__ import annotations

import numpy as np
import pytest

from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
from adaptive_reflow.algorithm import (
    BatchedRunnerConfig,
    BatchedTrajectoryRunner,
)
from adaptive_reflow.algorithm.nfe_allocation import (
    nfe_steps_for_evidence,
    nfe_steps_uniform,
)
from adaptive_reflow.algorithm.scheduler import CodimensionSheetScheduler


def _adapter(weights_path) -> TwoDimFMAdapter:
    return TwoDimFMAdapter(weights_path=weights_path, target="two_moons")


# ---------------------------------------------------------------------------
# FIX-1 -- record_round_feedback is no longer a no-op
# ---------------------------------------------------------------------------


def test_feedback_populates_smoothed_w2() -> None:
    sched = CodimensionSheetScheduler(cycle_length=5)
    assert sched.smoothed_w2 is None
    for r, w2 in enumerate([0.5, 0.4, 0.35]):
        sched.record_round_feedback(r, {"W2": w2})
    assert sched.w2_history == (0.5, 0.4, 0.35)
    assert sched.smoothed_w2 is not None
    # EMA of a decreasing series sits between the first and last value.
    assert 0.35 < float(sched.smoothed_w2) < 0.5


def test_feedback_populates_smoothed_evidence_ratio() -> None:
    sched = CodimensionSheetScheduler(cycle_length=5)
    assert sched.smoothed_evidence_ratio is None
    sched.record_round_feedback(0, {"W2": 0.5, "selection_ratio": 0.6})
    sched.record_round_feedback(1, {"W2": 0.5, "evidence_ratio": 0.8})
    assert sched.smoothed_evidence_ratio is not None
    assert 0.6 <= float(sched.smoothed_evidence_ratio) <= 0.8


def test_feedback_accepts_paper_quantities_ratio() -> None:
    sched = CodimensionSheetScheduler(cycle_length=5)
    sched.record_round_feedback(
        0, {"W2": 0.5}, paper_quantities={"sheet_vs_cells_proxy": 0.75}
    )
    assert sched.smoothed_evidence_ratio == pytest.approx(0.75)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), "x", None, True])
def test_feedback_ignores_broken_oracle_values(bad: object) -> None:
    sched = CodimensionSheetScheduler(cycle_length=5)
    sched.record_round_feedback(0, {"W2": bad})  # type: ignore[dict-item]
    assert sched.w2_history == ()
    assert sched.smoothed_w2 is None


def test_feedback_does_not_change_the_schedule() -> None:
    """FIX-1 is observational: ``sample`` must be byte-identical."""
    quiet = CodimensionSheetScheduler(cycle_length=5)
    fed = CodimensionSheetScheduler(cycle_length=5)
    for r in range(5):
        expected = quiet.sample(0, r, r)
        fed.record_round_feedback(r, {"W2": 0.1 * (r + 1)})
        got = fed.sample(0, r, r)
        assert got.n_cap == expected.n_cap
        assert got.evidence_ratio == expected.evidence_ratio
        assert got.eps_implicit == expected.eps_implicit
    assert fed.config_hash() == quiet.config_hash()


def test_early_stop_knobs_stay_out_of_config_hash() -> None:
    """Runtime-control knobs must not invalidate pinned schedule vectors."""
    default = CodimensionSheetScheduler(cycle_length=5)
    tuned = CodimensionSheetScheduler(
        cycle_length=5,
        early_stop_min_rounds=4,
        early_stop_window=3,
        early_stop_plateau_rel_tol=0.05,
    )
    assert tuned.config_hash() == default.config_hash()
    assert tuned.to_config() == default.to_config()


def test_reset_clears_feedback_history() -> None:
    sched = CodimensionSheetScheduler(cycle_length=5)
    for r in range(4):
        sched.record_round_feedback(r, {"W2": 0.4})
    assert sched.should_terminate_round() is True
    sched.reset()
    assert sched.w2_history == ()
    assert sched.smoothed_w2 is None
    assert sched.should_terminate_round() is False


# ---------------------------------------------------------------------------
# FIX-2 -- should_terminate_round + runner early termination
# ---------------------------------------------------------------------------


def test_no_termination_without_evidence() -> None:
    sched = CodimensionSheetScheduler(cycle_length=20)
    assert sched.should_terminate_round() is False
    sched.record_round_feedback(0, {"W2": 0.4})
    assert sched.should_terminate_round() is False


def test_terminates_on_plateau() -> None:
    sched = CodimensionSheetScheduler(cycle_length=20)
    for r, w2 in enumerate([0.9, 0.5, 0.4000, 0.4001, 0.4002]):
        sched.record_round_feedback(r, {"W2": w2})
    assert sched.should_terminate_round() is True


def test_does_not_terminate_while_improving() -> None:
    sched = CodimensionSheetScheduler(cycle_length=20)
    for r, w2 in enumerate([0.9, 0.7, 0.5, 0.3, 0.1]):
        sched.record_round_feedback(r, {"W2": w2})
    assert sched.should_terminate_round() is False


def test_tighter_tolerance_delays_termination() -> None:
    series = [0.9, 0.5, 0.400, 0.401, 0.402]
    loose = CodimensionSheetScheduler(cycle_length=20)
    strict = CodimensionSheetScheduler(
        cycle_length=20, early_stop_plateau_rel_tol=0.0
    )
    for r, w2 in enumerate(series):
        loose.record_round_feedback(r, {"W2": w2})
        strict.record_round_feedback(r, {"W2": w2})
    assert loose.should_terminate_round() is True
    assert strict.should_terminate_round() is False


@pytest.mark.parametrize(
    "kwargs",
    [
        {"early_stop_min_rounds": 0},
        {"early_stop_window": 0},
        {"early_stop_plateau_rel_tol": -0.1},
        {"early_stop_plateau_rel_tol": float("nan")},
    ],
)
def test_invalid_early_stop_knobs_rejected(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        CodimensionSheetScheduler(cycle_length=5, **kwargs)  # type: ignore[arg-type]


def test_runner_default_runs_every_round(twodim_fm_weights_path) -> None:
    """No-degradation: the default path is the pre-Wave-35 open loop."""
    cfg = BatchedRunnerConfig(
        cycle_length=6,
        trajectories_per_round=2,
        endpoints_per_trajectory=4,
        scheduler=CodimensionSheetScheduler(cycle_length=6),
        seed=7,
    )
    result = BatchedTrajectoryRunner(cfg, _adapter(twodim_fm_weights_path)).run()
    assert result.rounds_run == 6
    assert result.early_terminated is False
    assert len(result.per_round_w2) == 6


def test_runner_early_termination_saves_rounds(twodim_fm_weights_path) -> None:
    """FIX-2: opting in stops the loop once the scheduler reports a plateau."""
    def build(early: bool) -> BatchedRunnerConfig:
        return BatchedRunnerConfig(
            cycle_length=12,
            trajectories_per_round=2,
            endpoints_per_trajectory=4,
            scheduler=CodimensionSheetScheduler(
                cycle_length=12, early_stop_plateau_rel_tol=0.2
            ),
            seed=7,
            early_termination=early,
        )

    full = BatchedTrajectoryRunner(build(False), _adapter(twodim_fm_weights_path)).run()
    early = BatchedTrajectoryRunner(build(True), _adapter(twodim_fm_weights_path)).run()

    assert full.rounds_run == 12
    assert early.rounds_run < full.rounds_run, (
        "early termination must cost strictly fewer rounds (=fewer NFE) "
        "than the open-loop control"
    )
    assert early.early_terminated is True
    # The rounds it DID run are the same rounds the control ran: early
    # termination truncates the schedule, it does not perturb it.
    assert early.per_round_n_cap == full.per_round_n_cap[: early.rounds_run]
    assert np.allclose(
        early.per_round_w2, full.per_round_w2[: early.rounds_run]
    )


def test_early_termination_is_config_hash_visible(twodim_fm_weights_path) -> None:
    common = dict(
        cycle_length=4,
        trajectories_per_round=2,
        endpoints_per_trajectory=4,
        seed=7,
    )
    off = BatchedTrajectoryRunner(
        BatchedRunnerConfig(
            scheduler=CodimensionSheetScheduler(cycle_length=4), **common
        ),
        _adapter(twodim_fm_weights_path),
    ).run()
    on = BatchedTrajectoryRunner(
        BatchedRunnerConfig(
            scheduler=CodimensionSheetScheduler(cycle_length=4),
            early_termination=True,
            **common,
        ),
        _adapter(twodim_fm_weights_path),
    ).run()
    assert off.config_hash != on.config_hash


def test_runner_ignores_hook_on_schedulers_without_it(twodim_fm_weights_path) -> None:
    """A family with no ``should_terminate_round`` runs the full cycle."""
    from adaptive_reflow.algorithm import ConstantScheduler

    sched = ConstantScheduler(cycle_length=5, n_cap=0.5)
    assert not hasattr(sched, "should_terminate_round")
    result = BatchedTrajectoryRunner(
        BatchedRunnerConfig(
            cycle_length=5,
            trajectories_per_round=2,
            endpoints_per_trajectory=4,
            scheduler=sched,
            seed=7,
            early_termination=True,
        ),
        _adapter(twodim_fm_weights_path),
    ).run()
    assert result.rounds_run == 5
    assert result.early_terminated is False


# ---------------------------------------------------------------------------
# FIX-3a -- evidence-weighted NFE allocation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("nfe", [5, 12, 50, 275])
def test_evidence_allocation_preserves_matched_nfe(nfe: int) -> None:
    eps = [0.05, 0.0375, 0.025, 0.0125, 1e-9]
    steps = nfe_steps_for_evidence(nfe, eps)
    assert sum(steps) == nfe
    assert len(steps) == len(eps)
    assert all(s >= 1 for s in steps)


def test_evidence_allocation_favours_refinement_rounds() -> None:
    eps = [0.05, 0.0375, 0.025, 0.0125, 1e-9]
    steps = nfe_steps_for_evidence(50, eps)
    assert steps == sorted(steps), "steps must be monotone in decreasing eps"
    assert steps[-1] > steps[0]
    # Bounded skew: the terminal eps floor (1e-9) must not starve the
    # other rounds down to a single step each.
    assert min(steps) > 1


def test_uniform_eps_matches_uniform_allocation() -> None:
    assert nfe_steps_for_evidence(50, [0.05] * 5) == nfe_steps_uniform(50, 5)


@pytest.mark.parametrize(
    "eps", [[0.05, 0.0, 0.01], [0.05, -1.0, 0.01], [0.05, float("nan"), 0.01]]
)
def test_degenerate_eps_falls_back_to_uniform(eps: list[float]) -> None:
    assert nfe_steps_for_evidence(30, eps) == nfe_steps_uniform(30, 3)


def test_evidence_allocation_is_deterministic() -> None:
    eps = [0.05, 0.0375, 0.025, 0.0125, 1e-9]
    assert nfe_steps_for_evidence(50, eps) == nfe_steps_for_evidence(50, eps)


@pytest.mark.parametrize(
    "args", [(0, [0.1]), (5, []), (3, [0.1, 0.2, 0.3, 0.4])]
)
def test_allocation_rejects_invalid_budgets(args: tuple) -> None:
    with pytest.raises(ValueError):
        nfe_steps_for_evidence(*args)


def test_audit_tool_default_allocation_unchanged() -> None:
    """No-degradation: the audit grid's default split is still uniform."""
    import tools.run_controlled_audit as audit

    assert audit.NFE_ALLOCATION == "uniform"
    assert audit._nfe_steps_per_round(275, 5) == [55] * 5


def test_audit_tool_evidence_allocation_opt_in(monkeypatch) -> None:
    import tools.run_controlled_audit as audit

    monkeypatch.setattr(audit, "NFE_ALLOCATION", "evidence")
    steps = audit._nfe_steps_per_round(275, 5)
    assert sum(steps) == 275
    assert steps != [55] * 5
    assert steps == sorted(steps)


# ---------------------------------------------------------------------------
# FIX-3b -- G.5 saturation criterion orientation
# ---------------------------------------------------------------------------


def test_g5_flat_sweep_saturates_at_first_point() -> None:
    """A flat lower-is-better sweep is saturated at its FIRST NFE.

    Pre-Wave-35 the test demanded ``metric <= 0.95 * metric_full``
    (5% BETTER than the full run), which no point of a flat sweep can
    satisfy, so ``n_min`` fell back to ``N_full`` and G.5 reported 275.
    """
    from tools.capability_audit import g5_saturation_point

    payload = g5_saturation_point(["twodim_fm", "rectified_flow_cifar"])
    per_family = {
        e["model_family"]: e["n_min_saturation"] for e in payload["evidence"]
    }
    # twodim_fm's sweep is (5, 0.33) -> (500, 0.33): flat, so saturated at 5.
    assert per_family["twodim_fm"] == 5
    # CIFAR's sweep genuinely improves to NFE=50, so N_min stays 50.
    assert per_family["rectified_flow_cifar"] == 50
    assert payload["value"] <= 50
    assert payload["verdict"] == "PASS"


def test_g5_does_not_regress_a_genuinely_unsaturated_sweep() -> None:
    """The looser threshold must not declare an improving sweep saturated."""
    from tools.capability_audit import g5_saturation_point

    payload = g5_saturation_point(["rectified_flow_cifar"])
    evidence = payload["evidence"][0]
    assert evidence["metric_orientation"] == "lower_is_better"
    # 222.16 and 122.18 are both far worse than 103.41 / 0.95 = 108.85.
    assert evidence["n_min_saturation"] == 50
