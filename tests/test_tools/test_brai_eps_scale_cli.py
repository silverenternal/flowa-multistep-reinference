"""Tests for the ``--brai-eps-scale`` CLI flag (Wave 149 P2).

Wire ``--brai-eps-scale FLOAT`` through ``tools/run_controlled_audit.py``
so that Wave 146 Item 1 (Kanzi N=1000 algorithm-primitive ablation
BLOCKED on missing ``--primitive`` flags) can be retried at camera-ready
without source-code patches.

BRAI is consumed only by ``adaptive_reflow/adapters/lineageflow.py`` via
``adaptive_reflow/algorithm/perturbation/perturbation.py:824`` + ``1056``.
The flag's default is ``0.1`` (matches
``DEFAULT_BRAI_EPS_SCALE`` at
``adaptive_reflow/algorithm/perturbation/perturbation.py:137``); the
``choices=[0.01, 0.05, 0.1, 0.2, 0.5]`` constrain the BRAI
push-magnitude to safe values (Risk C: keep below sigma threshold to
avoid ``restart_blend`` crash).

Resolution precedence: CLI flag > ``DEFAULT_BRAI_EPS_SCALE``. When the
flag matches the default (``0.1``), the byte-stable
``UniformFreshPerturbation`` path is preserved (Wave 47/52/58 regression
vectors). When the user passes a non-default value, the framework arm
routes through ``PaperQuantityAttractorInversion(eps_scale=args.brai_eps_scale)``.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "tools" / "run_controlled_audit.py"


def _load_audit_module():
    """Load ``tools.run_controlled_audit`` as a module.

    Registers the synthetic module name in ``sys.modules`` so dataclass
    introspection (which looks up ``cls.__module__``) does not raise
    ``AttributeError: 'NoneType' object has no attribute '__dict__'``.
    """
    synthetic_name = "run_controlled_audit_test"
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


def _parse_args(argv):
    """Invoke the script's argparse layer with the given argv."""
    module = _load_audit_module()
    return module._parse_args(argv)


# ---------------------------------------------------------------------------
# Wave 149 P2: argparse smoke
# ---------------------------------------------------------------------------


def test_argparse_default_is_0_1() -> None:
    """Without ``--brai-eps-scale``, default is ``0.1`` (matches DEFAULT_BRAI_EPS_SCALE)."""
    args = _parse_args([])
    assert args.brai_eps_scale == 0.1


@pytest.mark.parametrize("value", [0.01, 0.05, 0.1, 0.2, 0.5])
def test_argparse_accepts_in_choices(value: float) -> None:
    """Each choice value is accepted (no SystemExit)."""
    args = _parse_args(["--brai-eps-scale", str(value)])
    assert abs(args.brai_eps_scale - value) < 1e-9


@pytest.mark.parametrize("value", [1.0, 0.5 - 1e-9, 0.3, -0.1, 2.0])
def test_argparse_rejects_out_of_choices(value: float) -> None:
    """Out-of-choices values raise SystemExit (argparse calls ``error`` -> exit 2)."""
    with pytest.raises(SystemExit):
        _parse_args(["--brai-eps-scale", str(value)])


# ---------------------------------------------------------------------------
# Wave 149 P2: default resolves to DEFAULT_BRAI_EPS_SCALE constant
# ---------------------------------------------------------------------------


def test_default_matches_perturbation_constant() -> None:
    """The argparse default ``0.1`` matches ``DEFAULT_BRAI_EPS_SCALE``.

    Pins the byte-stability invariant: with the flag's default value,
    the framework arm's BRAI push-magnitude equals the canonical
    ``DEFAULT_BRAI_EPS_SCALE`` from
    ``adaptive_reflow/algorithm/perturbation/perturbation.py:137``.
    """
    from adaptive_reflow.algorithm.perturbation import DEFAULT_BRAI_EPS_SCALE
    args = _parse_args([])
    assert abs(args.brai_eps_scale - DEFAULT_BRAI_EPS_SCALE) < 1e-9


# ---------------------------------------------------------------------------
# Wave 149 P2: LineageFlow-only scope (Risk D)
# ---------------------------------------------------------------------------


def test_brai_eps_scale_with_non_lineageflow_emits_warning() -> None:
    """``--brai-eps-scale`` with non-LineageFlow model emits UserWarning (Risk D)."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _parse_args(
            ["--brai-eps-scale", "0.5", "--models", "twodim_fm"]
        )
        lineageflow_warnings = [
            warning for warning in w
            if "LineageFlow" in str(warning.message)
        ]
        assert len(lineageflow_warnings) >= 1, (
            "expected UserWarning for --brai-eps-scale with non-LineageFlow model"
        )


def test_brai_eps_scale_default_with_non_lineageflow_no_warning() -> None:
    """``--brai-eps-scale 0.1`` (default) with non-LineageFlow model does NOT warn.

    The default value matches ``DEFAULT_BRAI_EPS_SCALE`` so no warning
    is emitted — the user did not explicitly opt into a non-default
    BRAI push-magnitude.
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _parse_args(
            ["--brai-eps-scale", "0.1", "--models", "twodim_fm"]
        )
        lineageflow_warnings = [
            warning for warning in w
            if "LineageFlow" in str(warning.message)
        ]
        assert len(lineageflow_warnings) == 0


def test_brai_eps_scale_with_lineageflow_no_warning() -> None:
    """``--brai-eps-scale`` with LineageFlow model does NOT emit warning (in-scope)."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _parse_args(
            ["--brai-eps-scale", "0.5", "--models", "lineageflow"]
        )
        lineageflow_warnings = [
            warning for warning in w
            if "LineageFlow" in str(warning.message)
        ]
        assert len(lineageflow_warnings) == 0


# ---------------------------------------------------------------------------
# Wave 149 P2: end-to-end argparse smoke (CLI subprocess)
# ---------------------------------------------------------------------------


def test_cli_subprocess_help_includes_brai_eps_scale() -> None:
    """``--help`` output must include the ``--brai-eps-scale`` flag entry."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--help"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "--brai-eps-scale" in proc.stdout
    assert "{0.01,0.05,0.1,0.2,0.5}" in proc.stdout


def test_cli_subprocess_rejects_brai_eps_scale_1_0() -> None:
    """Passing ``--brai-eps-scale 1.0`` exits with code 2 (argparse error)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--brai-eps-scale", "1.0"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 2
    assert "invalid choice" in proc.stderr
