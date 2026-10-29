"""The live ``workers-per-gpu`` heuristic.

These replace ten tests that pinned a ``--workers-per-gpu`` flag inside the
*vendored* LineageFlow scripts. That flag does not exist there: the vendor tree
is byte-identical to upstream, and the capability lives in our own wrapper
``tools/run_lineageflow_n1000_foldability_omegafold.py``. The old tests were
xfailed with a copy-pasted reason (``k1_rc5 historical drift``) that named an
unrelated documentation gate — see ``docs/audit/xfail-triage.md``.

The auto-detection is what the R1 wall-clock evidence actually runs on, so it
is worth pinning directly: ``workers_per_gpu = max(1, min(4, floor(free_gb /
4)))`` over the *most-constrained* GPU, defaulting to 1 whenever ``nvidia-smi``
is unavailable or unparseable.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WRAPPER = REPO_ROOT / "tools" / "run_lineageflow_n1000_foldability_omegafold.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_lf_fold_wrapper", str(WRAPPER))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["_lf_fold_wrapper"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def wrapper() -> ModuleType:
    return _load()


def _nvsmi(module: ModuleType, monkeypatch: pytest.MonkeyPatch, rows: list[tuple[int, float]]) -> None:
    """Make ``nvidia-smi`` report the given (index, free MiB) rows."""
    out = "\n".join(f"{idx}, {free}" for idx, free in rows) + "\n"

    def fake_run(*args, **kwargs):  # noqa: ANN002, ANN003
        return SimpleNamespace(returncode=0, stdout=out, stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)


def test_sixteen_gb_gives_four_workers(wrapper, monkeypatch) -> None:
    _nvsmi(wrapper, monkeypatch, [(0, 16 * 1024)])
    assert wrapper._detect_gpu_workers() == 4


def test_twelve_gb_gives_three_workers(wrapper, monkeypatch) -> None:
    """The formula is the source of truth; the docstring table used to say 2."""
    _nvsmi(wrapper, monkeypatch, [(0, 12 * 1024)])
    assert wrapper._detect_gpu_workers() == 3


def test_nine_gb_gives_two_workers(wrapper, monkeypatch) -> None:
    _nvsmi(wrapper, monkeypatch, [(0, 9 * 1024)])
    assert wrapper._detect_gpu_workers() == 2


def test_six_gb_gives_one_worker(wrapper, monkeypatch) -> None:
    _nvsmi(wrapper, monkeypatch, [(0, 6 * 1024)])
    assert wrapper._detect_gpu_workers() == 1


def test_two_gb_still_gives_the_safe_floor(wrapper, monkeypatch) -> None:
    _nvsmi(wrapper, monkeypatch, [(0, 2 * 1024)])
    assert wrapper._detect_gpu_workers() == 1


def test_the_most_constrained_gpu_wins(wrapper, monkeypatch) -> None:
    """24 GB beside 8 GB must schedule for the 8 GB device, not the big one."""
    _nvsmi(wrapper, monkeypatch, [(0, 24 * 1024), (1, 8 * 1024)])
    assert wrapper._detect_gpu_workers() == 2


def test_missing_nvidia_smi_falls_back_to_one(wrapper, monkeypatch) -> None:
    def boom(*args, **kwargs):  # noqa: ANN002, ANN003
        raise FileNotFoundError("nvidia-smi")

    monkeypatch.setattr(wrapper.subprocess, "run", boom)
    assert wrapper._detect_gpu_workers() == 1


def test_nonzero_exit_falls_back_to_one(wrapper, monkeypatch) -> None:
    monkeypatch.setattr(
        wrapper.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(returncode=9, stdout="", stderr="boom"),
    )
    assert wrapper._detect_gpu_workers() == 1


def test_empty_output_falls_back_to_one(wrapper, monkeypatch) -> None:
    monkeypatch.setattr(
        wrapper.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout="  \n", stderr=""),
    )
    assert wrapper._detect_gpu_workers() == 1


def test_malformed_rows_are_skipped(wrapper, monkeypatch) -> None:
    monkeypatch.setattr(
        wrapper.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(
            returncode=0, stdout="not,a,number\n0, 16384\n", stderr=""
        ),
    )
    assert wrapper._detect_gpu_workers() == 4
