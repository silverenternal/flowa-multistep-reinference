"""Exercise resume and reference validation through the CLI execution path."""
import json
from types import SimpleNamespace

import numpy as np
import pytest

from tools import run_rf_cifar_ablation as cli


@pytest.fixture
def run(tmp_path, monkeypatch):
    calls = []
    weights = tmp_path / "weights.bin"
    weights.write_bytes(b"original")
    ref = tmp_path / "reference.npz"
    np.savez(ref, features=np.ones((2, 2048), dtype=np.float32))
    output = tmp_path / "output"
    monkeypatch.setattr(cli, "RectifiedFlowCIFARAdapter", lambda **kw:
                        SimpleNamespace(_mode="synthetic", _weights_path=weights))
    monkeypatch.setattr(cli, "_build_schedulers", lambda **kw: {"cosine": object()})

    def execute(**kwargs):
        calls.append(kwargs)
        n = kwargs["n_rounds"]
        return {
            "scheduler": "cosine", "fid_curve": [1.] * n,
            "selection_curve": [0.5] * n, "merged_beta_curve": [0.2] * n,
            "nfe_curve": [4] * n, "mean_fid": 1., "best_round_fid": 1.,
            "wall_clock_per_round_seconds": 1., "selection_ratio_round_0": 0.5,
            "selection_ratio_round_last": 0.5,
            "per_round": [{"round": i, "fid": 1., "nfe": 4, "merged_beta": 0.2,
                           "selection_ratio": 0.5} for i in range(n)],
        }

    monkeypatch.setattr(cli, "_run_one_scheduler", execute)
    args = ["--output-dir", str(output), "--n-rounds", "2", "--samples-per-round", "2",
            "--weights-path", str(weights), "--reference-features", str(ref), "--resume"]
    return args, calls, output / "cosine.json", weights, ref


def test_matching_result_is_reused_and_changed_parameters_rerun(run):
    args, calls, path, _, _ = run
    assert cli.main(args) == 0
    assert cli.main(args) == 0
    assert len(calls) == 1
    assert cli.main(args + ["--n-rounds", "3"]) == 0
    assert len(calls) == 2
    assert len(json.loads(path.read_text())["per_round"]) == 3


def test_runner_failure_is_persisted_and_cli_reports_failure(run, monkeypatch):
    args, _, path, _, _ = run

    def fail(**kwargs):
        raise RuntimeError("sampling failed")

    monkeypatch.setattr(cli, "_run_one_scheduler", fail)
    assert cli.main(args) == 1
    assert "sampling failed" in json.loads(path.read_text())["error"]


@pytest.mark.parametrize("mutation", ["partial", "nan", "error", "list", "bad_json",
                                    "none_curve", "row_missing", "missing_summary", "inf_selection"])
def test_malformed_results_are_recomputed(run, mutation):
    args, calls, path, _, _ = run
    assert cli.main(args) == 0
    data = json.loads(path.read_text())
    if mutation == "partial":
        data["per_round"].pop()
    elif mutation == "nan":
        data["fid_curve"][0] = float("nan")
    elif mutation == "error":
        data["error"] = "interrupted"
    elif mutation == "list":
        data = []
    elif mutation == "none_curve":
        data["fid_curve"] = None
    elif mutation == "row_missing":
        del data["per_round"][0]["fid"]
    elif mutation == "missing_summary":
        del data["mean_fid"]
    elif mutation == "inf_selection":
        data["selection_curve"][0] = float("inf")
    path.write_text("{" if mutation == "bad_json" else json.dumps(data))
    assert cli.main(args) == 0
    assert len(calls) == 2


@pytest.mark.parametrize("kind", ["missing", "images", "single", "nan", "shape", "corrupt"])
def test_required_reference_fails_before_model_construction(tmp_path, monkeypatch, kind):
    ref = tmp_path / "reference.npz"
    if kind == "images":
        np.savez(ref, samples=np.zeros((2, 3, 32, 32)))
    elif kind == "single":
        np.savez(ref, features=np.zeros((1, 2048)))
    elif kind == "nan":
        np.savez(ref, features=np.full((2, 2048), np.nan))
    elif kind == "shape":
        np.savez(ref, features=np.zeros((2, 3)))
    elif kind == "corrupt":
        ref.write_bytes(b"not an NPZ")
    monkeypatch.setattr(cli, "RectifiedFlowCIFARAdapter",
                        lambda **kw: pytest.fail("invalid reference loaded a model"))
    assert cli.main(["--require-reference", "--reference-features", str(ref),
                     "--output-dir", str(tmp_path / "output")]) == 2
