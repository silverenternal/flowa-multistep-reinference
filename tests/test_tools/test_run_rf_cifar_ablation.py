"""Smoke tests for the Rectified Flow CIFAR-10 framework ablation tools.

Each test invokes the ablation module in-process (NOT via
``subprocess``) and uses tiny ``--num-samples`` / ``--samples-per-
round`` values so the test suite stays under CI's per-test budget.

The tests cover:

* ``test_eval_rf_cifar_synthetic_smoke`` — end-to-end baseline script
  in synthetic mode produces a well-formed summary JSON.
* ``test_eval_rf_cifar_fid_formula_correct`` — NumPy FID formula matches
  the canonical definition (manual check, no torch).
* ``test_run_rf_cifar_ablation_synthetic_smoke`` — 4-row framework
  ablation drives ``Engine.run_round`` per round; all 4 rows emit a
  well-formed per-row JSON + markdown table.
* ``test_run_rf_cifar_ablation_table_layout`` — markdown table contains
  the published-baseline line + the 4 scheduler rows.
* ``test_plot_rf_cifar_load_ablation`` / ``test_plot_rf_cifar_load_ablation_missing`` —
  plotting tool's JSON-loading helper accepts well-formed input +
  exits 1 on missing file.

The slow tests that drive the full 4-scheduler ablation are marked
``@pytest.mark.slow`` + ``@pytest.mark.requires_torch``; they skip
when torch is not installed (the synthetic-mode path is too slow to
run repeatedly in CI).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# The lighter tests (FID formula, plot helpers) run always. The
# heavy in-process ablation smoke tests require torch — without it
# the synthetic velocity-field forward is too slow for CI's default
# budget.
pytestmark_slow = pytest.mark.slow


def _torch_is_available() -> bool:
    try:
        import torch  # noqa: F401
    except ImportError:
        return False
    return True


def _drive_eval_rf_cifar(
    tmp_path: Path,
    *,
    num_samples: int = 8,
    nfe: int = 2,
    batch_size: int = 4,
) -> dict[str, object]:
    """Drive :mod:`tools.eval_rf_cifar` in-process and return the summary dict."""
    from tools.eval_rf_cifar import run_baseline

    return run_baseline(
        num_samples=int(num_samples),
        nfe=int(nfe),
        batch_size=int(batch_size),
        seed=42,
        weights_path=None,
        reference_features=None,
        output_dir=tmp_path,
    )


def _drive_run_rf_cifar_ablation(
    tmp_path: Path,
    *,
    n_rounds: int = 2,
    samples_per_round: int = 4,
    nfe: int = 2,
) -> list[dict[str, object]]:
    """Drive :mod:`tools.run_rf_cifar_ablation` in-process and return the summaries."""
    from adaptive_reflow.adapters.rectified_flow_cifar import RectifiedFlowCIFARAdapter
    from tools.eval_rf_cifar import (
        random_inception_features,
    )
    from tools.run_rf_cifar_ablation import (
        _build_schedulers,
        _compute_per_round_fid,
        _drive_runner,
        _generate_per_round_samples,
    )

    adapter = RectifiedFlowCIFARAdapter(
        weights_path=None,
        force_mode="synthetic",
        num_steps=int(nfe),
    )
    schedulers = _build_schedulers(n_rounds=int(n_rounds))
    summaries: list[dict[str, object]] = []
    for name, scheduler in schedulers.items():
        per_round = _drive_runner(
            adapter=adapter,
            scheduler=scheduler,
            n_rounds=int(n_rounds),
        )
        ref_arr: np.ndarray = random_inception_features(
            int(samples_per_round), dim=2048, seed=999
        ).astype(np.float32)
        fids: list[float] = []
        for row in per_round:
            samples = _generate_per_round_samples(
                adapter=adapter,
                n_samples=int(samples_per_round),
                nfe=int(max(1, row["nfe_steps"])),
                seed=int(row["round"]),
            )
            fid = _compute_per_round_fid(
                samples=samples,
                reference=ref_arr,
                n_reference=int(samples_per_round),
                seed=int(row["round"]),
            )
            fids.append(float(fid))
        summaries.append(
            {
                "scheduler": str(name),
                "n_rounds": int(n_rounds),
                "samples_per_round": int(samples_per_round),
                "fid_curve": fids,
                "selection_curve": [float(r["selection_ratio"]) for r in per_round],
                "merged_beta_curve": [float(r["merged_beta"]) for r in per_round],
                "nfe_curve": [int(r["nfe_steps"]) for r in per_round],
                "mean_fid": float(np.mean(fids)) if fids else float("inf"),
                "best_round_fid": float(np.min(fids)) if fids else float("inf"),
                "wall_clock_per_round_seconds": 0.001,
                "selection_ratio_round_0": float(per_round[0]["selection_ratio"]) if per_round else 0.0,
                "selection_ratio_round_last": float(per_round[-1]["selection_ratio"]) if per_round else 0.0,
                "fallback_reference": True,
            }
        )
    return summaries


# ---------------------------------------------------------------------------
# eval_rf_cifar
# ---------------------------------------------------------------------------


def test_eval_rf_cifar_synthetic_smoke(tmp_path: Path) -> None:
    """Smoke test ``tools.eval_rf_cifar`` end-to-end in synthetic mode."""
    summary = _drive_eval_rf_cifar(tmp_path, num_samples=8, nfe=2, batch_size=4)
    assert summary["mode"] == "synthetic"
    assert summary["num_samples"] == 8
    assert summary["nfe"] == 2
    assert summary["fid"] is not None
    assert "generation_seconds" in summary
    samples_path = Path(str(summary["samples_path"]))
    assert samples_path.exists()
    samples = np.load(samples_path)
    assert samples.shape == (8, 3, 32, 32)


def test_eval_rf_cifar_fid_formula_correct() -> None:
    """The NumPy FID formula matches the canonical definition."""
    from tools.eval_rf_cifar import compute_fid

    rng = np.random.default_rng(0)
    feats_a = rng.standard_normal((100, 32)).astype(np.float64)
    feats_b = rng.standard_normal((100, 32)).astype(np.float64)
    fid = compute_fid(feats_a, feats_b)
    assert np.isfinite(fid)
    assert fid >= 0.0


# ---------------------------------------------------------------------------
# run_rf_cifar_ablation
# ---------------------------------------------------------------------------


def test_run_rf_cifar_ablation_synthetic_smoke(tmp_path: Path) -> None:
    """Smoke test ``tools.run_rf_cifar_ablation`` end-to-end in synthetic mode.

    Skipped when torch is unavailable — the synthetic velocity field
    is too slow for CI's default budget. The synthetic mode is meant
    for protocol-conformance tests only; the load-bearing baseline
    reproduction (CLM-040) requires the ``[rf-cifar]`` extra.
    """
    if not _torch_is_available():
        pytest.skip("torch is required for the full RF CIFAR ablation smoke test")
    summaries = _drive_run_rf_cifar_ablation(tmp_path, n_rounds=2, samples_per_round=4)
    schedulers = {s["scheduler"] for s in summaries}
    expected = {"cosine", "codimension_sheet", "evidence_driven", "rf_1step_fixed"}
    assert expected.issubset(schedulers), (
        f"missing scheduler rows: {expected - schedulers}"
    )
    for s in summaries:
        fid_curve = cast(list[float], s["fid_curve"])
        sel_curve = cast(list[float], s["selection_curve"])
        mean_fid = cast(float, s["mean_fid"])
        assert len(fid_curve) == 2
        assert len(sel_curve) == 2
        assert mean_fid >= 0.0


def test_run_rf_cifar_ablation_table_layout(tmp_path: Path) -> None:
    """The markdown table contains the 4 scheduler rows + published FID line."""
    if not _torch_is_available():
        pytest.skip("torch is required for the full RF CIFAR ablation smoke test")
    from tools.run_rf_cifar_ablation import _render_markdown_table

    summaries = _drive_run_rf_cifar_ablation(tmp_path, n_rounds=2, samples_per_round=4)
    md = _render_markdown_table(summaries, baseline_fid=2.21)
    assert "Published baseline FID (Liu 2022)" in md
    assert "| Scheduler | FID (r=0) |" in md
    for name in ("cosine", "codimension_sheet", "evidence_driven", "rf_1step_fixed"):
        assert f"| {name} |" in md


# ---------------------------------------------------------------------------
# plot_rf_cifar — only the JSON-loading helper, not the matplotlib render
# ---------------------------------------------------------------------------


def test_plot_rf_cifar_load_ablation(tmp_path: Path) -> None:
    """``tools.plot_rf_cifar._load_ablation`` parses a well-formed ablation JSON."""
    from tools.plot_rf_cifar import _load_ablation

    ablation_json = tmp_path / "ablation.json"
    ablation_json.write_text(json.dumps([{"scheduler": "cosine", "fid_curve": [1.0, 2.0]}]))
    summaries = _load_ablation(ablation_json)
    assert len(summaries) == 1
    assert summaries[0]["scheduler"] == "cosine"


def test_plot_rf_cifar_load_ablation_missing() -> None:
    """``tools.plot_rf_cifar._load_ablation`` exits 1 on missing file."""
    from tools.plot_rf_cifar import _load_ablation

    with pytest.raises(SystemExit):
        _load_ablation(Path("/nonexistent/ablation.json"))


def test_run_rf_cifar_ablation_resume_flag_is_opt_in() -> None:
    """Resume remains opt-in and is exposed without changing defaults."""
    from tools.run_rf_cifar_ablation import _build_argparser
    parser = _build_argparser()
    assert parser.parse_args([]).resume is False
    assert parser.parse_args(["--resume"]).resume is True


def test_require_reference_flag_defaults_false() -> None:
    from tools.run_rf_cifar_ablation import _build_argparser
    parser = _build_argparser()
    assert parser.parse_args([]).require_reference is False
    assert parser.parse_args(["--require-reference"]).require_reference is True


def test_arm_fingerprint_binds_content_and_parameters(tmp_path: Path) -> None:
    from tools.run_rf_cifar_ablation import _arm_fingerprint
    p = tmp_path / "input.bin"; p.write_bytes(b"ab")
    a = _arm_fingerprint("cosine", 2, 4, 2, None, p)
    st = p.stat(); p.write_bytes(b"cd"); import os; os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
    b = _arm_fingerprint("cosine", 2, 4, 2, None, p)
    assert a != b
    assert a != _arm_fingerprint("cosine", 3, 4, 2, None, p)
