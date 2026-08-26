"""Tests for DTB-R7 evaluation protocol (CPU-only).

Acceptance:

* All 7 canonical paired-arm kinds can be registered; the registry
  rejects additions after sealing.
* :class:`EvaluatorProvenanceGuard` rejects missing evaluator versions
  and routes.
* :class:`RoundToRoundOscillationDetector` is deterministic on CPU:
  identical inputs yield identical state across runs.

No torch. No GPU.
"""

from __future__ import annotations

import pytest

import adaptive_reflow.contracts as rmt
import adaptive_reflow.eval.protocol as ep

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _arm(name: str, kind: str, *, policy: str | None = None, config: str | None = None):
    return ep.PairedComparisonArm(
        name=ep.ArmName(name),
        kind=kind,  # type: ignore[arg-type]
        policy_hash=ep.PolicyHash(policy or f"pol-{name}"),
        config_hash=ep.ConfigHash(config or f"cfg-{name}"),
    )


# ---------------------------------------------------------------------------
# Paired-arm registration
# ---------------------------------------------------------------------------


def test_register_all_seven_canonical_kinds():
    """The registry accepts every kind in :data:`PAIRED_ARM_KINDS`."""
    reg = ep.PairedComparisonRegistry()
    for i, kind in enumerate(ep.PAIRED_ARM_KINDS):
        reg.register(_arm(f"arm-{i}", kind))
    assert reg.has_all_kinds()
    assert len(reg.arms) == 7


def test_registry_rejects_addition_after_seal():
    reg = ep.PairedComparisonRegistry()
    reg.register(_arm("arm-0", "disabled"))
    reg.register(_arm("arm-1", "fixed_scheduled"))
    sealed_hash = reg.seal()
    assert sealed_hash != ""
    assert reg.is_sealed is True

    with pytest.raises(RuntimeError):
        reg.register(_arm("arm-x", "dynamic_uncalibrated"))


def test_registry_rejects_duplicate_names():
    reg = ep.PairedComparisonRegistry()
    reg.register(_arm("arm-0", "disabled"))
    with pytest.raises(ValueError):
        reg.register(_arm("arm-0", "fixed_scheduled"))


def test_registry_rejects_duplicate_kinds():
    reg = ep.PairedComparisonRegistry()
    reg.register(_arm("arm-A", "disabled"))
    with pytest.raises(ValueError):
        reg.register(_arm("arm-B", "disabled"))


def test_registry_rejects_unknown_kind():
    with pytest.raises(ValueError):
        _arm("arm-A", "not_a_real_kind")


def test_registry_seal_returns_combined_hash():
    """seal() returns a deterministic sha256 digest."""
    reg_a = ep.PairedComparisonRegistry()
    reg_b = ep.PairedComparisonRegistry()
    arms = [
        ("arm-A", "disabled"),
        ("arm-B", "fixed_scheduled"),
        ("arm-C", "dynamic_uncalibrated"),
    ]
    for n, k in arms:
        reg_a.register(_arm(n, k))
        reg_b.register(_arm(n, k))
    # Sealing in either order yields the same digest (insertion order
    # is normalized at hash time).
    assert reg_a.seal() == reg_b.seal()


def test_registry_seal_cannot_be_called_twice():
    reg = ep.PairedComparisonRegistry()
    reg.register(_arm("arm-0", "disabled"))
    reg.seal()
    with pytest.raises(RuntimeError):
        reg.seal()


def test_registry_rejects_non_arm_argument():
    reg = ep.PairedComparisonRegistry()
    with pytest.raises(TypeError):
        reg.register("not an arm")  # type: ignore[arg-type]


def test_registry_combined_hash_independent_of_insertion_order():
    """Inserting arms in two different orders yields the same digest."""
    kinds = list(ep.PAIRED_ARM_KINDS)
    reg_fwd = ep.PairedComparisonRegistry()
    reg_rev = ep.PairedComparisonRegistry()
    for i, k in enumerate(kinds):
        reg_fwd.register(_arm(f"arm-{i}", k))
        reg_rev.register(_arm(f"arm-{len(kinds) - 1 - i}", kinds[len(kinds) - 1 - i]))
    assert reg_fwd.combined_hash == reg_rev.combined_hash


def test_arm_constructor_rejects_empty_policy_hash():
    with pytest.raises(ValueError):
        ep.PairedComparisonArm(
            name=ep.ArmName("arm-A"),
            kind="disabled",
            policy_hash=ep.PolicyHash(""),
            config_hash=ep.ConfigHash("cfg-A"),
        )


def test_arm_constructor_rejects_empty_config_hash():
    with pytest.raises(ValueError):
        ep.PairedComparisonArm(
            name=ep.ArmName("arm-A"),
            kind="disabled",
            policy_hash=ep.PolicyHash("pol-A"),
            config_hash=ep.ConfigHash(""),
        )


def test_arm_constructor_rejects_empty_name():
    with pytest.raises(ValueError):
        ep.PairedComparisonArm(
            name=ep.ArmName(""),
            kind="disabled",
            policy_hash=ep.PolicyHash("pol-A"),
            config_hash=ep.ConfigHash("cfg-A"),
        )


# ---------------------------------------------------------------------------
# Evaluator provenance guard
# ---------------------------------------------------------------------------


def _guard(**overrides):
    base = {
        "required_evaluator_versions": (
            ep.EvaluatorVersion("gnina-1.3.2"),
            ep.EvaluatorVersion("admet-0.9.0"),
        ),
        "required_materialization_route": ep.MaterializationRoute(
            "route-canonical-2026-01"
        ),
        "evaluator_hash": rmt.ArtifactHash(ep.evaluator_guard_digest(
            versions=("gnina-1.3.2", "admet-0.9.0"),
            materialization_route="route-canonical-2026-01",
        )),
    }
    base.update(overrides)
    return ep.EvaluatorProvenanceGuard(**base)


def test_guard_accepts_listed_version_and_route():
    g = _guard()
    assert g.check_version("gnina-1.3.2") is True
    assert g.check_version("admet-0.9.0") is True
    assert g.check_route("route-canonical-2026-01") is True


def test_guard_rejects_missing_version():
    g = _guard()
    assert g.check_version("gnina-1.3.3") is False
    assert g.check_version("") is False
    assert g.check_version("unknown-evaluator") is False


def test_guard_rejects_wrong_route():
    g = _guard()
    assert g.check_route("route-alternative") is False
    assert g.check_route("") is False


def test_guard_rejects_empty_versions_tuple():
    with pytest.raises(ValueError):
        _guard(required_evaluator_versions=())


def test_guard_rejects_empty_route():
    with pytest.raises(ValueError):
        _guard(required_materialization_route=ep.MaterializationRoute(""))


def test_guard_rejects_empty_evaluator_hash():
    with pytest.raises(ValueError):
        _guard(evaluator_hash=rmt.ArtifactHash(""))


def test_guard_rejects_empty_version_string():
    with pytest.raises(ValueError):
        _guard(
            required_evaluator_versions=(
                ep.EvaluatorVersion(""),
                ep.EvaluatorVersion("admet-0.9.0"),
            )
        )


def test_guard_digest_is_deterministic():
    """Same inputs -> same digest; order of versions is normalized."""
    d1 = ep.evaluator_guard_digest(
        versions=("a", "b"),
        materialization_route="route-x",
    )
    d2 = ep.evaluator_guard_digest(
        versions=("b", "a"),
        materialization_route="route-x",
    )
    assert d1 == d2
    assert d1 != ep.evaluator_guard_digest(
        versions=("a", "b"),
        materialization_route="route-y",
    )


# ---------------------------------------------------------------------------
# Oscillation detector (deterministic, CPU)
# ---------------------------------------------------------------------------


def _trace():
    """A canonical 12-round trace (scores + fresh-noise mass)."""
    return [
        (0.10, 0.50),
        (0.12, 0.48),  # up
        (0.11, 0.46),  # down -> 1 oscillation
        (0.13, 0.04),  # up
        (0.11, 0.03),  # down -> 2 oscillations; fresh-noise collapse starts
        (0.13, 0.02),  # up -> 3 oscillations; collapse streak = 3
        (0.13, 0.02),  # identical score -> run=2; collapse streak = 4
        (0.13, 0.01),  # identical score -> run=3; collapse streak = 5 (stuck)
        (0.20, 0.40),  # different -> run=1; collapse streak resets
        (0.20, 0.39),  # identical -> run=2
        (0.22, 0.38),  # different -> run=1
        (0.22, 0.37),  # identical -> run=2
    ]


def test_detector_is_deterministic_across_runs():
    """Same trace -> same detector state on every run."""
    trace = _trace()

    def _run():
        d = ep.RoundToRoundOscillationDetector(
            fresh_noise_collapse_threshold=0.05,
            consecutive_identical_score_threshold=3,
        )
        for score, fn in trace:
            d.update(score, fn)
        return d.snapshot()

    snap_a = _run()
    snap_b = _run()
    assert snap_a == snap_b


def test_detector_counts_oscillations():
    d = ep.RoundToRoundOscillationDetector(
        fresh_noise_collapse_threshold=0.05,
        consecutive_identical_score_threshold=3,
    )
    # Strict alternation. The first delta sets the baseline sign; each
    # subsequent delta is a sign flip. So six rounds -> five deltas,
    # four of which are sign flips.
    for score in (0.0, 1.0, 0.0, 1.0, 0.0, 1.0):
        d.update(score, 0.5)
    assert d.oscillation_count == 4


def test_detector_does_not_count_zero_delta_as_oscillation():
    """Equal scores should not register as a sign flip."""
    d = ep.RoundToRoundOscillationDetector()
    for score in (0.5, 0.5, 0.5, 0.5):
        d.update(score, 0.5)
    assert d.oscillation_count == 0


def test_detector_identical_run_resets_on_change():
    d = ep.RoundToRoundOscillationDetector(consecutive_identical_score_threshold=3)
    d.update(1.0, 0.5)
    d.update(1.0, 0.5)  # run=2
    d.update(1.0, 0.5)  # run=3
    assert d.consecutive_identical_score_runs == 3
    assert d.is_stuck() is True
    d.update(2.0, 0.5)  # different
    assert d.consecutive_identical_score_runs == 1
    assert d.is_stuck() is False


def test_detector_fresh_noise_collapse_threshold():
    """A long collapse streak is flagged via has_fresh_noise_collapse."""
    d = ep.RoundToRoundOscillationDetector(
        fresh_noise_collapse_threshold=0.10,
        consecutive_identical_score_threshold=3,
    )
    # First round initializes the trailing run; collapse streak applies.
    d.update(0.5, 0.5)  # streak = 0
    for score in (0.5, 0.5, 0.5, 0.5):
        d.update(score, 0.05)  # streak: 1, 2, 3, 4
    assert d.has_fresh_noise_collapse() is True
    assert d.max_fresh_noise_collapse_streak == 4


def test_detector_collapse_streak_resets():
    d = ep.RoundToRoundOscillationDetector(
        fresh_noise_collapse_threshold=0.10,
        consecutive_identical_score_threshold=3,
    )
    d.update(0.5, 0.05)  # streak = 1
    d.update(0.5, 0.05)  # streak = 2
    d.update(0.5, 0.20)  # streak = 0 (reset)
    d.update(0.5, 0.05)  # streak = 1
    assert d.max_fresh_noise_collapse_streak == 2


def test_detector_snapshot_keys():
    d = ep.RoundToRoundOscillationDetector()
    d.update(0.5, 0.5)
    snap = d.snapshot()
    for key in (
        "oscillation_count",
        "consecutive_identical_score_runs",
        "fresh_noise_collapse_threshold",
        "consecutive_identical_score_threshold",
        "max_fresh_noise_collapse_streak",
    ):
        assert key in snap


def test_detector_rejects_non_finite_score():
    d = ep.RoundToRoundOscillationDetector()
    with pytest.raises(ValueError):
        d.update(float("inf"), 0.5)
    with pytest.raises(ValueError):
        d.update(float("nan"), 0.5)


def test_detector_rejects_out_of_range_fresh_noise():
    d = ep.RoundToRoundOscillationDetector()
    with pytest.raises(ValueError):
        d.update(0.5, 1.5)
    with pytest.raises(ValueError):
        d.update(0.5, -0.1)


def test_detector_rejects_non_real_inputs():
    d = ep.RoundToRoundOscillationDetector()
    with pytest.raises(ValueError):
        d.update("not a number", 0.5)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        d.update(0.5, "not a number")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        d.update(True, 0.5)  # type: ignore[arg-type]


def test_detector_reset_returns_to_empty_state():
    d = ep.RoundToRoundOscillationDetector(consecutive_identical_score_threshold=3)
    d.update(0.5, 0.5)
    d.update(0.5, 0.5)
    assert d.oscillation_count >= 0
    d.reset()
    snap = d.snapshot()
    assert snap["oscillation_count"] == 0
    assert snap["consecutive_identical_score_runs"] == 0
    assert snap["max_fresh_noise_collapse_streak"] == 0


def test_detector_is_oscillating_false_for_monotone():
    d = ep.RoundToRoundOscillationDetector()
    for score in (0.1, 0.2, 0.3, 0.4):
        d.update(score, 0.5)
    assert d.is_oscillating() is False


def test_detector_is_oscillating_true_after_one_flip():
    d = ep.RoundToRoundOscillationDetector()
    d.update(0.1, 0.5)
    d.update(0.2, 0.5)  # up
    d.update(0.1, 0.5)  # down -> 1 flip
    assert d.is_oscillating() is True
