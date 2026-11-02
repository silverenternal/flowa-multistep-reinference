"""Check the RF-to-VE bridge on an analytic Gaussian flow and actual original-call cost."""

from pathlib import Path

import numpy as np
import pytest

from tools.cifar_matched_frontier_20261103 import RFDenoiser, main_steps, official_sampler
from tools.cifar_study_metrics_20261103 import kernel_rows, kernel_score


def test_blocked_kernel_terms_equal_direct_unbiased_formula():
    x = np.array([[1.0, 2.0], [3.0, 4.0], [0.0, -1.0]])
    y = np.array([[4.0, 2.0], [3.0, -1.0]])
    kxx = (x @ x.T / 2 + 1) ** 3
    kyy = (y @ y.T / 2 + 1) ** 3
    kxy = (x @ y.T / 2 + 1) ** 3
    expected = (kxx.sum() - np.trace(kxx)) / 6 + (kyy.sum() - np.trace(kyy)) / 2 - 2 * kxy.mean()
    for block in [1, 2, 128]:
        actual = kernel_score(
            kernel_rows(x, x, self_kernel=True, block=block),
            kernel_rows(x, y, block=block),
            kernel_rows(y, y, self_kernel=True, block=block).mean(),
        )
        assert actual == pytest.approx(expected)
    with pytest.raises(ValueError):
        kernel_rows(x, y, self_kernel=True)


def test_bridge_matches_conditional_mean_of_gaussian_data():
    torch = pytest.importorskip("torch")
    variance = 2.5

    def velocity(x, t):
        t = t[:, None, None, None]
        return (((variance + 1) * t - 1) / ((1 - t) ** 2 + variance * t * t)) * x

    net = RFDenoiser(velocity)
    y = torch.tensor([[[[0.2, -0.7], [2.0, 1.0]]]], dtype=torch.float64)
    for sigma in [0.002, 0.06, 0.3, 1.0, 999.0]:
        actual = net(y, torch.tensor(sigma, dtype=torch.float64))
        expected = variance / (variance + sigma * sigma) * y
        torch.testing.assert_close(actual, expected, rtol=3e-5, atol=1e-7)


def test_original_restart_counts_and_initial_state_are_matched():
    torch = pytest.importorskip("torch")
    source = Path("verification_outputs/cifar-study-20261103/restart_source.py")
    if not source.exists():
        pytest.skip("original reference source is an experiment artifact")
    sampler = official_sampler(source)
    for cost in [25, 49, 99, 199]:
        for restart in [False, True]:
            calls = []

            def velocity(x, t, calls=calls):
                calls.append((x.clone(), t.clone()))
                return torch.zeros_like(x)

            z = torch.ones((1, 3, 2, 2)) * 0.125
            result = sampler(
                RFDenoiser(velocity),
                z.double() / (999 / 1000),
                num_steps=main_steps(cost, restart),
                sigma_min=0.002,
                sigma_max=999,
                rho=7,
                S_noise=1.0,
                restart_gamma=0.0,
                S_churn=0.0,
                restart_info='{"0":[3,2,0.06,0.30]}' if restart else "",
            )
            assert len(calls) == cost
            torch.testing.assert_close(calls[0][0], z)
            assert torch.isfinite(result).all()
