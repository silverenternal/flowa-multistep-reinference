"""Tests for ``tools.run_image_fid_per_round`` — Phase 4 / Design #1.

The wrapper bridges per-round PNG dumps (Phase 4 / Designs #1 + #2)
to the :class:`PerRoundFIDTracker.run` orchestrator (Phase 3 surface
— preserved unchanged). Tests here lock in:

1. **End-to-end smoke** — the wrapper returns a JSON-serialisable
   dict shaped like :class:`TheoremAlignedFIDReport` over a tmp_path
   of synthetic round dirs. Uses a monkeypatched InceptionV3 to keep
   the test hermetic.
3. **CLI contract** — ``--per-round-dir`` repeated, ``--epsilon-schedule``
   parsed as JSON, ``--output`` is required.

The hermetic InceptionV3 monkeypatch mirrors the pattern in
:mod:`tests.test_tools.test_run_image_eval`.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Preflight: this module exercises
# :mod:`tools.run_image_fid_per_round`, which depends on
# ``torch`` (InceptionV3 forward via torchvision). The
# :func:`requires_torch` session fixture in ``tests/conftest.py``
# short-circuits the suite on sandboxes where torch is not vendored.
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.usefixtures("requires_torch")

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_WRAPPER_PATH = _REPO_ROOT / "tools" / "run_image_fid_per_round.py"


def _load_wrapper() -> Any:
    """Import :mod:`tools.run_image_fid_per_round` without registering ``tools`` as a package."""
    repo_str = str(_REPO_ROOT)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)
    spec = importlib.util.spec_from_file_location(
        "tools.run_image_fid_per_round", _WRAPPER_PATH
    )
    if spec is None or spec.loader is None:  # pragma: no cover — defensive
        raise ImportError(f"could not load { _WRAPPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def wrapper() -> Any:
    """Loaded wrapper module (one-shot import for the test session)."""
    return _load_wrapper()


def _seed_round_dir(parent: Path, round_idx: int, n_samples: int = 2) -> Path:
    """Write ``n_samples`` solid-color RGB PNGs into ``parent/framework_round{XX}``."""
    from PIL import Image

    rd = parent / f"framework_round{round_idx:02d}"
    rd.mkdir(parents=True, exist_ok=True)
    for i in range(n_samples):
        color = ((round_idx * 64 + i * 16) % 256, (round_idx * 32) % 256, 96)
        Image.new("RGB", (8, 8), color).save(rd / f"sample_{i:04d}.png")
    return rd


@pytest.fixture
def tmp_round_dirs(tmp_path: Path) -> list[Path]:
    """Two-round tree of PNGs; deterministic colors."""
    return [_seed_round_dir(tmp_path, r, n_samples=2) for r in range(2)]


@pytest.fixture
def inception_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    """Monkeypatch InceptionV3 so the test does not load the real network.

    The stub returns a deterministic Gaussian vector of length 2048 for
    each input image (the wrapper only consumes the *shape* of the
    features; the theorem-aligned FID math is exercised in unit tests
    in :mod:`tests.test_eval`).
    """
    import torch

    def _stub_load(_device: Any) -> Any:
        class _Stub(torch.nn.Module):  # type: ignore[misc]
            def forward(self, x: torch.Tensor) -> torch.Tensor:
                # shape: (B, 3, H, W) -> (B, 2048) by mean-pool then pad
                pooled = x.mean(dim=(2, 3))  # (B, 3)
                out = torch.zeros(x.shape[0], 2048, device=x.device)
                out[:, :3] = pooled
                return out

        return _Stub()

    monkeypatch.setattr(
        "tools.run_image_eval.load_inception_for_fid", _stub_load
    )


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


def test_wrapper_returns_theorem_aligned_report_shape(
    wrapper: Any,
    tmp_path: Path,
    tmp_round_dirs: list[Path],
    inception_stub: None,
) -> None:
    """Wrapper returns a TheoremAlignedFIDReport-shaped JSON dict."""
    out_path = tmp_path / "report.json"
    report = wrapper.run_image_fid_per_round(
        per_round_dirs=tmp_round_dirs,
        epsilon_schedule=[0.1, 0.05],
        reference_stats_path=None,
        rho=0.1,
        c=1.0,
        eta=0.1,
        device_arg="cpu",
        image_target_size=8,
        fid_batch_size=4,
        feature_dim=2048,
        monte_carlo_n=0,
        seed=0,
        tolerance=1e-3,
        output=out_path,
    )
    assert out_path.exists(), "output JSON not written"
    on_disk = json.loads(out_path.read_text(encoding="utf-8"))
    for key in (
        "schema",
        "rounds",
        "convergence",
        "paper_quantities_snapshot",
        "n_rounds",
    ):
        assert key in on_disk, f"missing key in JSON: {key}"
    assert on_disk["schema"] == "theorem_aligned_fid_report.v1"
    assert len(on_disk["rounds"]) == 2, (
        f"rounds must have length 2; got {len(on_disk['rounds'])}"
    )
    # Convergence diagnostic is fully populated.
    for k in (
        "monotone",
        "O_eps_holds",
        "per_round_deltas",
        "paper_implied_constant",
        "observed_constant",
        "regime_violations",
    ):
        assert k in on_disk["convergence"], f"missing convergence.{k}"
    # Paper quantities are finite.
    pq = on_disk["paper_quantities_snapshot"]
    for k in ("A_g", "B_g", "C_g", "e_rho", "rho", "c", "eta"):
        assert k in pq, f"missing paper_quantities_snapshot.{k}"
        assert np.isfinite(float(pq[k])), f"{k} not finite: {pq[k]}"
    assert report["n_rounds"] == 2


def test_wrapper_propagates_paper_quantities_via_cli(
    wrapper: Any,
    tmp_path: Path,
    tmp_round_dirs: list[Path],
    inception_stub: None,
) -> None:
    """``--rho`` / ``--c`` / ``--eta`` flow into ``paper_quantities_snapshot``."""
    out_path = tmp_path / "report.json"
    report = wrapper.run_image_fid_per_round(
        per_round_dirs=tmp_round_dirs,
        epsilon_schedule=[0.2, 0.1],
        reference_stats_path=None,
        rho=0.2,
        c=1.5,
        eta=0.3,
        device_arg="cpu",
        image_target_size=8,
        fid_batch_size=4,
        feature_dim=2048,
        monte_carlo_n=0,
        seed=0,
        tolerance=1e-3,
        output=out_path,
    )
    pq = report["paper_quantities_snapshot"]
    assert float(pq["rho"]) == 0.2
    assert float(pq["c"]) == 1.5
    assert float(pq["eta"]) == 0.3


def test_wrapper_input_validation(
    wrapper: Any,
    tmp_path: Path,
    tmp_round_dirs: list[Path],
    inception_stub: None,
) -> None:
    """Both input-validation failure modes raise ``ValueError`` with a useful message.

    Aggregates the two distinct input-validation paths into a single
    test because they exercise the same contract: a malformed input
    raises ``ValueError`` whose message matches a documented prefix.
    """
    # Mismatched ``per_round_dirs`` vs ``epsilon_schedule``.
    with pytest.raises(ValueError, match="must match"):
        wrapper.run_image_fid_per_round(
            per_round_dirs=tmp_round_dirs,
            epsilon_schedule=[0.1],  # only one entry, two dirs
            reference_stats_path=None,
            output=None,
        )
    # Empty ``per_round_dirs``.
    with pytest.raises(ValueError, match="non-empty"):
        wrapper.run_image_fid_per_round(
            per_round_dirs=[],
            epsilon_schedule=[],
            reference_stats_path=None,
            output=None,
        )


def test_wrapper_cli_parses_and_rejects_epsilon_schedule(
    wrapper: Any,
    tmp_path: Path,
    tmp_round_dirs: list[Path],
    monkeypatch: pytest.MonkeyPatch,
    inception_stub: None,
) -> None:
    """CLI accepts a JSON list of floats and rejects malformed input.

    Combines the happy-path parse and the malformed-schedule
    rejection into one test because they exercise the same argparse
    surface (``--epsilon-schedule``) on opposite sides of the
    success/failure boundary.
    """
    # Happy path: a JSON list of floats routes through the wrapper.
    out_path = tmp_path / "report.json"
    rc = wrapper.main(
        [
            "--per-round-dir", str(tmp_round_dirs[0]),
            "--per-round-dir", str(tmp_round_dirs[1]),
            "--epsilon-schedule", "[0.1, 0.05]",
            "--output", str(out_path),
            "--device", "cpu",
            "--image-target-size", "8",
            "--fid-batch-size", "4",
            "--feature-dim", "2048",
            "--monte-carlo-n", "0",
        ]
    )
    assert rc == 0
    on_disk = json.loads(out_path.read_text(encoding="utf-8"))
    assert on_disk["n_rounds"] == 2
    # Sad path: malformed JSON exits non-zero.
    bad_rc = wrapper.main(
        [
            "--per-round-dir", str(tmp_round_dirs[0]),
            "--epsilon-schedule", "not-a-json-list",
            "--output", str(out_path),
        ]
    )
    assert bad_rc == 1


def test_wrapper_default_profile_is_x_squared(
    wrapper: Any,
    tmp_path: Path,
    tmp_round_dirs: list[Path],
    inception_stub: None,
) -> None:
    """Default profile is ``g(x) = x^2`` — paper Section 4.1 canonical."""
    out_path = tmp_path / "report.json"
    report = wrapper.run_image_fid_per_round(
        per_round_dirs=tmp_round_dirs,
        epsilon_schedule=[0.1, 0.05],
        reference_stats_path=None,
        output=out_path,
    )
    assert report["profile_id"] == "x^2"