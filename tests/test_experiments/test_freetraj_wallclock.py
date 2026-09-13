"""EXP-3 — FreeTrajScheduler wall-clock reproduction (arXiv:2507.10532).

Plan: ``docs/r4-survey/05-exp3-freetraj-wallclock-plan.md``.

The plan's hypothesis (H1) is that
:class:`~adaptive_reflow.algorithm.scheduler.freetraj.FreeTrajScheduler`
delivers a 15-25% wall-clock reduction against the cosine-anneal
baseline on the 2-moons bench, because its trajectory-aware ``n_cap``
substep is supposed to modulate the per-round bounded update.

This module measures that claim and, per plan §5.1 / §5.4, also audits
whether the trajectory substep is *reachable at all* when the scheduler
is driven statefully (which is how :class:`ReInferenceRunner` drives
it: one scheduler instance, ``sample()`` once per round).

Findings are recorded, not asserted, for the wall-clock number itself
(plan §2.2: "Diagnostic logging only (not assertions)"); the
*mechanism* assertions below are hard, because they are exact and
deterministic.
"""

from __future__ import annotations

import json
import math
import pathlib
import time
from statistics import mean, stdev

import pytest

from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
from adaptive_reflow.algorithm import ReInferenceConfig, ReInferenceRunner
from adaptive_reflow.algorithm.scheduler import (
    CosineAnnealScheduler,
    FreeTrajScheduler,
    default_cosine_scheduler,
)
from adaptive_reflow.frame.engine import Engine

# Plan §1 — experimental setup constants.
N_TRIALS = 10
N_ROUNDS = 20
NUM_STEPS = 100
CHANNELS: tuple[str, ...] = ("xy",)
WARMUP_SEED = 999
TRAJECTORY_AMPLITUDE = 0.05
TRAJECTORY_PERIOD = 4

#: Plan §3.3 pass threshold: ``reduction_mean >= 0.15``.
REDUCTION_THRESHOLD = 0.15
#: Plan §5.4 mitigation 1: the two arms' ``n_cap`` must differ by at
#: most ``trajectory_amplitude``.
MAX_NCAP_DEVIATION = TRAJECTORY_AMPLITUDE + 0.01


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _make_cosine() -> CosineAnnealScheduler:
    """Build the baseline arm's scheduler (plan Appendix C)."""
    return default_cosine_scheduler(
        cycle_length=N_ROUNDS, n_min=0.0, n_max=1.0, seed=0
    )


def _make_freetraj() -> FreeTrajScheduler:
    """Build the treatment arm's scheduler on the baseline's config."""
    return FreeTrajScheduler(
        config=_make_cosine().config,
        trajectory_amplitude=TRAJECTORY_AMPLITUDE,
        trajectory_period=TRAJECTORY_PERIOD,
    )


def _build_runner(scheduler: CosineAnnealScheduler | FreeTrajScheduler) -> ReInferenceRunner:
    """Build a runner whose only varying component is ``scheduler``."""
    return ReInferenceRunner(
        adapter=TwoDimFMAdapter(num_steps=NUM_STEPS, target="two_moons"),
        scheduler=scheduler,
        engine=Engine(),
    )


def _runner_config(seed: int) -> ReInferenceConfig:
    return ReInferenceConfig(
        n_rounds=N_ROUNDS,
        outer_cycle_id=0,
        target_round=0,
        seed=seed,
        channels=CHANNELS,
    )


def _time_runner(runner: ReInferenceRunner, seed: int) -> float:
    """Return the wall-clock seconds of one ``runner.run`` call."""
    cfg = _runner_config(seed)
    t0 = time.perf_counter()
    runner.run(cfg)
    return time.perf_counter() - t0


def _paired_t(deltas: list[float]) -> tuple[float, float]:
    """Return ``(t_statistic, one_sided_p)`` for ``mean(deltas) > 0``.

    Uses a normal approximation to the Student-t survival function,
    which is adequate for the plan's ``p < 0.05`` decision rule at
    ``n = 10`` when the effect is either overwhelming or absent (the
    two regimes the plan's rubric distinguishes).
    """
    n = len(deltas)
    if n < 2:
        return (0.0, 1.0)
    sd = stdev(deltas)
    if sd == 0.0:
        return (0.0, 0.5)
    t_stat = mean(deltas) / (sd / math.sqrt(n))
    # Normal survival function via erfc (one-sided).
    p = 0.5 * math.erfc(t_stat / math.sqrt(2.0))
    return (t_stat, p)


# ---------------------------------------------------------------------------
# Mechanism audit (plan §5.4 — is the trajectory substep wired?)
# ---------------------------------------------------------------------------


@pytest.mark.experiments
def test_freetraj_trajectory_substep_is_live_on_a_fresh_instance() -> None:
    """A *fresh* FreeTrajScheduler per round does apply the sin substep.

    This establishes that the trajectory-control code path exists and
    is numerically correct: the deviation from the cosine baseline is
    ``amplitude * sin(2*pi * (r % period) / period)``, clipped to
    ``[0, 1]``.
    """
    cosine = _make_cosine()
    deviations: list[float] = []
    for r in range(8):
        fresh = _make_freetraj()
        base = cosine.sample(
            outer_cycle_id=0, round_in_cycle=r, target_round=0
        )
        traj = fresh.sample(outer_cycle_id=0, round_in_cycle=r, target_round=0)
        deviations.append(float(traj.n_cap) - float(base.n_cap))
        # Plan §5.4 mitigation 1.
        assert abs(deviations[-1]) <= MAX_NCAP_DEVIATION

    # Rounds 3 and 7 sit at progress 0.75 -> sin = -1 -> full -amplitude.
    assert deviations[3] == pytest.approx(-TRAJECTORY_AMPLITUDE, abs=1e-12)
    assert deviations[7] == pytest.approx(-TRAJECTORY_AMPLITUDE, abs=1e-12)
    # Round 5 sits at progress 0.25 -> sin = +1 -> full +amplitude.
    assert deviations[5] == pytest.approx(TRAJECTORY_AMPLITUDE, abs=1e-12)
    # Some round must be non-zero, otherwise the knob is dead.
    assert any(abs(d) > 1e-9 for d in deviations)


@pytest.mark.experiments
def test_freetraj_trajectory_progress_varies_when_driven_statefully() -> None:
    """Post-P0-2 regression — the substep *now* fires on the runner's path.

    Pre-fix (F-1): ``FreeTrajScheduler.sample`` wrote
    ``self._last_trajectory_progress = progress`` on every call, and
    ``_compute_trajectory_progress`` short-circuited and returned that
    cached value whenever it was non-``None``. From round 1 onwards
    the trajectory substep was frozen at round 0's progress forever.

    Post-fix (P0-2): the cache is *only* consulted when an external
    ``trajectory_progress`` signal has been received via
    ``record_round_feedback``; otherwise the deterministic baseline is
    re-computed every round, so the substep actually oscillates.

    The runner drives one scheduler instance across all rounds
    (production path), so this test exercises the runner's path. It
    now asserts that the substep is *live*: the odd-round ``n_cap``
    values deviate from the cosine baseline by > 0.01 (the plan's
    audit threshold).
    """
    cosine = _make_cosine()
    freetraj = _make_freetraj()

    caps_cosine = [
        float(cosine.sample(outer_cycle_id=0, round_in_cycle=r, target_round=0).n_cap)
        for r in range(N_ROUNDS)
    ]
    caps_freetraj = [
        float(
            freetraj.sample(outer_cycle_id=0, round_in_cycle=r, target_round=0).n_cap
        )
        for r in range(N_ROUNDS)
    ]

    # The substep is *live*: the trajectory control fires on the
    # runner's path. With trajectory_period=4, round 3 sits at
    # progress 0.75 -> sin = -1 -> full -amplitude; round 5 at 0.25
    # -> sin = +1 -> full +amplitude. Both must deviate from the
    # cosine baseline by more than 0.01.
    assert abs(caps_freetraj[3] - caps_cosine[3]) > 0.01
    assert abs(caps_freetraj[5] - caps_cosine[5]) > 0.01
    # Some round must differ from the cosine baseline; otherwise the
    # knob is still dead.
    assert any(
        abs(f - c) > 0.01 for f, c in zip(caps_freetraj, caps_cosine, strict=True)
    )
    # The cache flag stays False because no feedback was recorded.
    assert freetraj._external_signal_received is False
    # The cached progress is NOT pinned at round 0 anymore; it is
    # only set when ``record_round_feedback`` supplies a value.
    assert freetraj._last_trajectory_progress is None


@pytest.mark.experiments
def test_freetraj_runner_result_differs_from_cosine_post_fix() -> None:
    """Post-P0-2 — the two arms now diverge; substep is live in the runner.

    Pre-fix this test asserted byte-identity of the runner outputs.
    Post-fix the trajectory substep fires on the runner's path (P0-2
    inverted the cache freeze), so the per-round ``n_cap`` and the
    downstream ``beta`` series now differ from the cosine baseline.

    The endpoint digest may or may not match exactly depending on the
    seed (the substep amplitude is small, ``0.05``, so the cosine
    baseline dominates), but the ``n_cap`` series must differ.
    """
    cosine_result = _build_runner(_make_cosine()).run(_runner_config(seed=0))
    freetraj_result = _build_runner(_make_freetraj()).run(_runner_config(seed=0))

    # The substep is now live; per-round ``n_cap`` diverges from
    # cosine at odd rounds where sin(2 pi * (r % 4) / 4) is non-zero.
    ncap_diverges = False
    for r in range(N_ROUNDS):
        cos_metrics = cosine_result.per_round_metrics[r]
        free_metrics = freetraj_result.per_round_metrics[r]
        if float(free_metrics["n_cap"]) != float(cos_metrics["n_cap"]):
            ncap_diverges = True
            break
    assert ncap_diverges, (
        "Post-P0-2 the FreeTraj scheduler's n_cap series must diverge "
        "from the cosine baseline at the trajectory-substep rounds."
    )


# ---------------------------------------------------------------------------
# Wall-clock measurement (plan §3.1)
# ---------------------------------------------------------------------------


@pytest.mark.experiments
def test_freetraj_scheduler_only_microbenchmark() -> None:
    """Plan §5.1 mitigation — scheduler-only cost, no adapter, no engine.

    Isolates the wrapper overhead so the runner-level number can be
    attributed to the right layer. Recorded, not asserted (timing on a
    shared CI box is not a stable assertion surface).
    """
    reps = 20_000
    cosine = _make_cosine()
    freetraj = _make_freetraj()

    t0 = time.perf_counter()
    for i in range(reps):
        cosine.sample(outer_cycle_id=0, round_in_cycle=i % N_ROUNDS, target_round=0)
    cosine_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    for i in range(reps):
        freetraj.sample(outer_cycle_id=0, round_in_cycle=i % N_ROUNDS, target_round=0)
    freetraj_s = time.perf_counter() - t0

    print(
        f"EXP-3 scheduler-only ({reps} samples): "
        f"cosine={cosine_s:.4f}s freetraj={freetraj_s:.4f}s "
        f"overhead_ratio={freetraj_s / cosine_s:.3f}x"
    )
    assert cosine_s > 0.0
    assert freetraj_s > 0.0


@pytest.mark.experiments
def test_freetraj_wallclock_reduction(tmp_path: pathlib.Path) -> None:
    """EXP-3 headline — Cosine vs FreeTraj, 10 trials x 20 rounds.

    Emits an isolated ``tmp_path/exp3-results.json`` sidecar. The test
    must not overwrite recorded research evidence. The 15% threshold is
    *recorded* in the sidecar rather than asserted, so the sidecar is
    produced even when the claim fails (the plan's rubric needs the
    number in every branch, including REFUTED).
    """
    cosine_runner = _build_runner(_make_cosine())
    freetraj_runner = _build_runner(_make_freetraj())

    # Plan §3.1 step 1 — pre-warm, discarded.
    _time_runner(cosine_runner, seed=WARMUP_SEED)
    _time_runner(freetraj_runner, seed=WARMUP_SEED)

    cosine_times: list[float] = []
    freetraj_times: list[float] = []
    for trial in range(N_TRIALS):
        cosine_times.append(_time_runner(cosine_runner, seed=trial))
        freetraj_times.append(_time_runner(freetraj_runner, seed=trial))

    cosine_mean = mean(cosine_times)
    cosine_std = stdev(cosine_times)
    freetraj_mean = mean(freetraj_times)
    freetraj_std = stdev(freetraj_times)
    reduction = (cosine_mean - freetraj_mean) / cosine_mean

    # Plan §3.3 — paired per-trial reduction.
    per_trial = [(c - f) / c for c, f in zip(cosine_times, freetraj_times, strict=True)]
    reduction_paired_mean = mean(per_trial)
    reduction_paired_std = stdev(per_trial)
    t_stat, p_value = _paired_t(per_trial)

    if reduction_paired_mean >= REDUCTION_THRESHOLD and p_value < 0.05:
        verdict = "CONFIRMED"
    elif reduction_paired_mean >= 0.05 and p_value < 0.10:
        verdict = "PARTIAL"
    elif reduction_paired_mean <= -0.05 and p_value > 0.90:
        verdict = "REFUTED"
    else:
        verdict = "INCONCLUSIVE"

    payload = {
        "experiment": "EXP-3",
        "paper": "arXiv:2507.10532",
        "plan": "docs/r4-survey/05-exp3-freetraj-wallclock-plan.md",
        "n_trials": N_TRIALS,
        "n_rounds": N_ROUNDS,
        "num_steps": NUM_STEPS,
        "trajectory_amplitude": TRAJECTORY_AMPLITUDE,
        "trajectory_period": TRAJECTORY_PERIOD,
        "cosine_mean_s": cosine_mean,
        "cosine_std_s": cosine_std,
        "cosine_mean_s_per_round": cosine_mean / N_ROUNDS,
        "freetraj_mean_s": freetraj_mean,
        "freetraj_std_s": freetraj_std,
        "freetraj_mean_s_per_round": freetraj_mean / N_ROUNDS,
        "reduction": reduction,
        "reduction_paired_mean": reduction_paired_mean,
        "reduction_paired_std": reduction_paired_std,
        "paired_t_statistic": t_stat,
        "paired_p_value_one_sided": p_value,
        "threshold": REDUCTION_THRESHOLD,
        "threshold_met": bool(reduction_paired_mean >= REDUCTION_THRESHOLD),
        "verdict": verdict,
        "cosine_times_s": cosine_times,
        "freetraj_times_s": freetraj_times,
        "note": (
            "P0-2 fix applied (F-1, docs/r4-survey/19-fix-plan.md): "
            "FreeTrajScheduler.sample no longer caches "
            "trajectory_progress on every call. The cache is only "
            "consulted when record_round_feedback supplied an external "
            "trajectory_progress signal. Driven statefully (the "
            "runner path), the trajectory substep is now live; the "
            "treatment arm diverges from the cosine baseline by "
            "amplitude * sin(2 pi * (r % period) / period) at every "
            "round. See "
            "test_freetraj_trajectory_progress_varies_when_driven_statefully."
        ),
    }

    print(
        f"EXP-3 cosine={cosine_mean:.4f}s +/- {cosine_std:.4f}; "
        f"freetraj={freetraj_mean:.4f}s +/- {freetraj_std:.4f}; "
        f"reduction={reduction:.3%}; paired={reduction_paired_mean:.3%} "
        f"+/- {reduction_paired_std:.3%}; t={t_stat:.3f} p={p_value:.4f}; "
        f"verdict={verdict}"
    )

    out = tmp_path / "exp3-results.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    assert out.is_file()
    assert -1.0 < reduction < 1.0
