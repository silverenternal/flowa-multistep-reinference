"""Tests for the Wave 150 K1 RC4 ablation-script CLI flags.

Adds 5 argparse flags to ``scripts/run_ablation_sweep.py`` so the
5-arm ablation can be retargeted at real-ckpt paths without source
patches (closes K1 RC4 per Wave 148 P3 dependency graph):

- ``--force-mode``: choices=("synthetic", "real"); default="synthetic"
- ``--metric-mode``: choices=("synthetic", "real"); default="synthetic"
- ``--limit``: int, default=0 (forward-compat hook)
- ``--model``: choices=("twodim_fm", "cifar10_rf", "lineageflow",
  "kanzi"); default=None (forward-compat hook)
- ``--ckpt``: Path, default=None (forward-compat hook)

Backward-compat invariant: defaults preserve the Wave 52 Agent B
behaviour (force_mode='synthetic', metric_mode='synthetic' on every
model).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_ablation_sweep.py"


def _load_ablation_module():
    """Load ``scripts.run_ablation_sweep`` as a module.

    Registers a synthetic module name in ``sys.modules`` so dataclass
    introspection (which looks up ``cls.__module__``) does not raise
    ``AttributeError: 'NoneType' object has no attribute '__dict__'``.
    """
    synthetic_name = "run_ablation_sweep_cli_test"
    spec = importlib.util.spec_from_file_location(
        synthetic_name, str(SCRIPT_PATH),
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[synthetic_name] = module
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    finally:
        sys.modules.pop(synthetic_name, None)
    return module


def test_force_mode_cli_accepts_real() -> None:
    """``--force-mode real`` parses without error."""
    module = _load_ablation_module()
    args = module.build_argparser().parse_args(["--force-mode", "real"])
    assert args.force_mode == "real"


def test_force_mode_cli_default_is_synthetic() -> None:
    """Default ``--force-mode`` is ``synthetic`` (Wave 52 backward-compat)."""
    module = _load_ablation_module()
    args = module.build_argparser().parse_args([])
    assert args.force_mode == "synthetic"


def test_limit_cli_required_for_real_ckpt() -> None:
    """Combined real-ckpt CLI combo (``--limit`` + ``--model`` + ``--ckpt``)
    parses without error.

    The flags are forward-compat hooks for K1 RC4 plumbing; the
    synthetic-mode cells still compute one number per arm regardless of
    ``--limit``. This test only asserts the CLI surface accepts the
    combination.
    """
    module = _load_ablation_module()
    args = module.build_argparser().parse_args([
        "--limit", "1000",
        "--model", "kanzi",
        "--ckpt", "/tmp/w150_fake_ckpt.pt",
    ])
    assert args.limit == 1000
    assert args.model == "kanzi"
    assert args.ckpt == Path("/tmp/w150_fake_ckpt.pt")


def test_metric_mode_cli_choices() -> None:
    """Out-of-range ``--metric-mode`` value is rejected by argparse."""
    module = _load_ablation_module()
    with pytest.raises(SystemExit):
        module.build_argparser().parse_args(["--metric-mode", "wronge"])
