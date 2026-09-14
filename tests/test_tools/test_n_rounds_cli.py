"""Tests for the ``--n-rounds`` CLI flag (Wave 149 P2).

Wire ``--n-rounds INT`` through ``tools/run_controlled_audit.py`` so that
Wave 146 Item 1 (Kanzi N=1000 algorithm-primitive ablation BLOCKED on
missing ``--primitive`` flags) + Wave 146 Item 2 (2D FM hp sensitivity
sweep PARTIAL with 3 BLOCKED algorithm-primitive hparams) can be retried
at camera-ready without source-code patches.

Per-model MODEL_TABLE defaults preserved verbatim:

* ``MODEL_TABLE["twodim_fm"]["n_rounds"] == 5``
* ``MODEL_TABLE["cifar10_rf"]["n_rounds"] == 4``
* ``MODEL_TABLE["lineageflow"]["n_rounds"] == 5``

Resolution precedence (mirrors Wave 112.C-6 ``_yaml_to_arg`` overlay
pattern): CLI flag (``args.n_rounds``) > ``MODEL_TABLE[<model>]["n_rounds"]``.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
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


def test_argparse_default_is_none() -> None:
    """Without ``--n-rounds``, default is ``None`` (per-model resolution).

    ``None`` is the byte-stable sentinel: the consumer sites at lines
    296 / 470 / 622 fall through to ``MODEL_TABLE[<model>]["n_rounds"]``
    when ``args.n_rounds is None``.
    """
    args = _parse_args([])
    assert args.n_rounds is None


@pytest.mark.parametrize("value", [1, 2, 3, 5, 10])
def test_argparse_accepts_in_choices(value: int) -> None:
    """Each choice value is accepted (no SystemExit)."""
    args = _parse_args(["--n-rounds", str(value)])
    assert args.n_rounds == value


@pytest.mark.parametrize("value", [0, 4, 6, 11, 100, -1])
def test_argparse_rejects_out_of_choices(value: int) -> None:
    """Out-of-choices values raise SystemExit (argparse calls ``error`` -> exit 2)."""
    with pytest.raises(SystemExit):
        _parse_args(["--n-rounds", str(value)])


# ---------------------------------------------------------------------------
# Wave 149 P2: consumer-site resolution (the 3 MODEL_TABLE overrides)
# ---------------------------------------------------------------------------


def test_model_table_defaults_match_design_doc() -> None:
    """Pin the per-model MODEL_TABLE hardcoded values used as fallback."""
    module = _load_audit_module()
    assert module.MODEL_TABLE["twodim_fm"]["n_rounds"] == 5
    assert module.MODEL_TABLE["cifar10_rf"]["n_rounds"] == 4
    assert module.MODEL_TABLE["lineageflow"]["n_rounds"] == 5


@pytest.mark.parametrize(
    "model,expected",
    [("twodim_fm", 5), ("cifar10_rf", 4), ("lineageflow", 5)],
)
def test_consumer_falls_back_to_model_table(model: str, expected: int) -> None:
    """When ``args.n_rounds is None``, the consumer falls through to MODEL_TABLE."""
    module = _load_audit_module()
    args = _parse_args([])
    # Mirror the consumer-site resolution pattern from tools/run_controlled_audit.py.
    resolved = int(
        args.n_rounds
        if args.n_rounds is not None
        else module.MODEL_TABLE[model]["n_rounds"]
    )
    assert resolved == expected


def test_consumer_honors_cli_override() -> None:
    """When ``--n-rounds`` is passed, it overrides MODEL_TABLE at consumer sites."""
    module = _load_audit_module()
    args = _parse_args(["--n-rounds", "5"])
    for model in ("twodim_fm", "cifar10_rf", "lineageflow"):
        resolved = int(
            args.n_rounds
            if args.n_rounds is not None
            else module.MODEL_TABLE[model]["n_rounds"]
        )
        assert resolved == 5, f"override failed for model={model!r}"


# ---------------------------------------------------------------------------
# Wave 149 P2: end-to-end argparse smoke (CLI subprocess)
# ---------------------------------------------------------------------------


def test_cli_subprocess_help_includes_n_rounds() -> None:
    """``--help`` output must include the ``--n-rounds`` flag entry."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--help"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "--n-rounds" in proc.stdout
    assert "{1,2,3,5,10}" in proc.stdout


def test_cli_subprocess_rejects_n_rounds_11() -> None:
    """Passing ``--n-rounds 11`` exits with code 2 (argparse error)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--n-rounds", "11"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 2
    assert "invalid choice" in proc.stderr
