"""Behavioral checks for counted, continuous TwoDimFM audit trajectories."""
import numpy as np
import pytest

from tools import run_controlled_audit as audit


@pytest.fixture
def local_weights(monkeypatch):
    from adaptive_reflow.adapters import twodim_fm
    original = twodim_fm.TwoDimFMAdapter
    def build(**kwargs):
        return original(**kwargs, init_random_weights=True, hidden_width=8)
    monkeypatch.setattr(twodim_fm, "TwoDimFMAdapter", build)
    return twodim_fm


@pytest.mark.parametrize("guard,expected_restarts", [(True, 1), (False, 4)])
def test_chained_states_actual_nfe_and_guard(local_weights, guard, expected_restarts):
    result = audit._run_twodim_fm(audit.CellSpec("twodim_fm", 4, 50, 0.0, n_samples=3, restart_guard=guard))
    assert not result.error, result.error
    assert result.nfe_matched
    assert result.protocol["scheduler_family"] == "codimension_sheet"
    assert result.protocol["metric_family"] == "empirical_joint_w2_equal_weight"
    for sample in result.protocol["samples"]:
        assert sample["baseline_nfe"] == sample["framework_nfe"] == 50
        rows = sample["rounds"]
        assert sum(r["actual_nfe"] for r in rows) == 50
        assert sum(r["restart_applied"] for r in rows) == expected_restarts
        assert sum(r["restart_skipped"] for r in rows) == 4 - expected_restarts
        assert rows[0]["solve_initial"] == sample["initial"]
        assert [r["steps"] for r in rows] == result.protocol["per_round_steps"]
        for previous, current in zip(rows, rows[1:]):
            assert previous["endpoint"] == current["previous_endpoint"]
            assert previous["endpoint_digest"] == current["previous_digest"]
            if current["restart_skipped"]:
                assert current["solve_initial"] == previous["endpoint"]
            else:
                assert current["solve_initial"] != previous["endpoint"]


def test_exact_hundred_samples_without_rounding(local_weights):
    result = audit._run_twodim_fm(audit.CellSpec("twodim_fm", 0, 10, 0.5, n_samples=100))
    assert not result.error, result.error
    assert result.protocol["n_samples"] == len(result.protocol["samples"]) == 100
    assert all(s["baseline_nfe"] == s["framework_nfe"] == 10 for s in result.protocol["samples"])
    assert all(sum(r["restart_applied"] for r in s["rounds"]) == 4 for s in result.protocol["samples"])


def test_counter_restored_after_solver_error(local_weights):
    velocity = local_weights._velocity_field
    class Broken:
        def solve_ode(self, *args, **kwargs):
            raise RuntimeError("solver failed")
    with pytest.raises(RuntimeError, match="solver failed"):
        audit._solve_twodim_counted(Broken(), None, None, 0)
    assert local_weights._velocity_field is velocity


def test_joint_w2_distinguishes_same_marginals():
    a = np.array([[-1., -1.], [1., 1.]])
    b = np.array([[-1., 1.], [1., -1.]])
    assert audit._empirical_joint_w2(a, b) == pytest.approx(2.)
    assert audit._empirical_joint_w2(a, a[::-1]) == pytest.approx(0.)


@pytest.mark.parametrize("budget", [9, 11])
def test_infeasible_budget_is_not_claimed_matched(local_weights, budget):
    result = audit._run_twodim_fm(audit.CellSpec("twodim_fm", 0, budget, 0.0, n_samples=2))
    assert result.error
    assert not result.nfe_matched


def test_cli_passes_exact_count_and_guard_switch(monkeypatch, tmp_path):
    seen = []
    def run(spec):
        seen.append(spec)
        return audit.CellResult(spec.model, spec.seed, spec.nfe, spec.sigma,
                                baseline_metric=1., framework_metric=1.,
                                baseline_nfe=10, framework_nfe=10, nfe_matched=True)
    monkeypatch.setattr(audit, "_run_cell", run)
    monkeypatch.setattr(audit, "NFE_ALLOCATION", audit.NFE_ALLOCATION)
    assert audit.main(["--models", "twodim_fm", "--quick", "--nfe", "10",
                       "--sigma", "0", "--n-samples", "100", "--no-restart-guard",
                       "--output", str(tmp_path / "report.json")]) == 0
    assert len(seen) == 1
    assert seen[0].n_samples == 100
    assert seen[0].restart_guard is False


def test_unpaired_initial_states_fail_closed(local_weights, monkeypatch):
    factory = local_weights.TwoDimFMAdapter
    created = 0
    def unequal_pair(**kwargs):
        nonlocal created
        created += 1
        kwargs["seed_offset"] += created % 2
        return factory(**kwargs)
    monkeypatch.setattr(local_weights, "TwoDimFMAdapter", unequal_pair)
    result = audit._run_twodim_fm(audit.CellSpec("twodim_fm", 0, 10, 0., n_samples=2))
    assert "paired initial states differ" in result.error
    assert not result.nfe_matched
