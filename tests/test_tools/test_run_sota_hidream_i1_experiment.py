"""Per-round dump regression test for ``tools.run_sota_hidream_i1_experiment``.

Phase 4 design #2. The HiDream harness now invokes the diffusers
pipeline ONCE per chain with ``num_inference_steps = n_rounds *
per_round_nfe`` and installs a ``callback_on_step_end`` hook that
decodes latents + saves a PNG at every round boundary into
``framework_round{r}/sample_{i:04d}.png``. The final round also
writes the legacy single-shot endpoint ``framework/sample_{i:04d}.png``
so :func:`tools.run_sota_hidream_i1_experiment._run_image_eval` (the
subprocess bridge over :mod:`tools.run_image_eval`) keeps scoring the
endpoint byte-stable.

This test exercises the synthetic (no-weights) fallback path so it
runs on CPU without torch / diffusers / a CUDA host. It verifies:

* ``framework_round{0..n_rounds-1}/sample_*.png`` directories exist
  with the expected file count.
* The legacy ``framework/sample_*.png`` endpoint path is preserved.
* ``summary.json`` includes ``framework.per_round_png_dirs`` and the
  per-round PNG count is consistent with ``n_mols * n_rounds``.

Stdlib + pytest only (no torch, no diffusers required).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Preflight: ``test_make_per_round_callback_signature`` exercises
# ``_make_per_round_callback`` which imports torch at the top of
# :mod:`tools.run_sota_hidream_i1_experiment`. The
# :func:`requires_torch` session fixture in ``tests/conftest.py``
# short-circuits the suite on sandboxes where torch is not vendored.
# (Most other tests in this module are synthetic-fallback paths
# that don't need torch — module-level skip keeps the gating
# uniform and lets the skip reason explain the harness dependency.)
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.usefixtures("requires_torch")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH: Path = REPO_ROOT / "tools" / "run_sota_hidream_i1_experiment.py"
VENV_PYTHON: Path = REPO_ROOT / ".venv" / "bin" / "python"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _venv_python() -> Path:
    """Return the venv python executable path; skip if missing."""
    if not VENV_PYTHON.exists():
        pytest.skip(f"venv python not found at {VENV_PYTHON}")
    return VENV_PYTHON


@pytest.fixture()
def hidream_out_dir(tmp_path: Path) -> Path:
    """Return a fresh output directory under ``tmp_path``."""
    return tmp_path / "hidream_out"


# ---------------------------------------------------------------------------
# Import + --help smoke tests
# ---------------------------------------------------------------------------


def test_module_imports() -> None:
    """The script must import without errors (catches typos / bad imports)."""
    spec = importlib.util.spec_from_file_location(
        "run_sota_hidream_i1_experiment", str(SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    assert hasattr(module, "main")
    assert hasattr(module, "_generate_pngs_framework")
    assert hasattr(module, "_emit_synthetic_pngs")
    assert hasattr(module, "_make_per_round_callback")


def test_help_flag_exits_cleanly(_venv_python: Path) -> None:
    """``--help`` must exit with code 0 and print argparse usage."""
    import subprocess

    result = subprocess.run(
        [str(_venv_python), str(SCRIPT_PATH), "--help"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=60,
    )
    assert result.returncode == 0, f"stderr: {result.stderr!r}"
    assert "--n-mols" in result.stdout
    assert "--n-rounds" in result.stdout
    assert "--per-round-nfe" in result.stdout
    assert "--output-dir" in result.stdout
    assert "--skip-eval" in result.stdout


# ---------------------------------------------------------------------------
# Synthetic-mode per-round dump regression
# ---------------------------------------------------------------------------


def test_per_round_dumps_subdirs(_venv_python: Path, hidream_out_dir: Path) -> None:
    """Synthetic-mode smoke test: per-round PNG dirs are emitted correctly.

    Runs ``tools/run_sota_hidream_i1_experiment.py`` with
    ``--skip-eval`` so the FID subprocess bridge is not invoked. The
    synthetic backend emits PIL-noise PNGs; we verify:

    * ``framework_round{r}/sample_{i:04d}.png`` exists for every
      ``r in [0, n_rounds)`` and every ``i in [0, n_mols)``.
    * The legacy ``framework/sample_{i:04d}.png`` endpoint path is
      preserved (byte-stable for the existing ``_run_image_eval``
      subprocess).
    * ``summary.json`` carries ``framework.per_round_png_dirs`` (length
      ``n_rounds``) and ``framework.per_round_png_count ==
      n_mols * n_rounds``.
    """
    import subprocess

    n_mols = 2
    n_rounds = 3
    cmd = [
        str(_venv_python),
        str(SCRIPT_PATH),
        "--n-mols",
        str(n_mols),
        "--n-rounds",
        str(n_rounds),
        "--baseline-nfe",
        "6",
        "--per-round-nfe",
        "2",
        "--resolution",
        "64",
        "--output-dir",
        str(hidream_out_dir),
        "--seed",
        "0",
        "--device",
        "cpu",
        "--allow-cuda0",  # explicitly opt into cuda:0 (we run on cpu)
        "--skip-eval",
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    assert result.returncode == 0, (
        f"hidream harness failed rc={result.returncode}\n"
        f"  stdout={result.stdout!r}\n  stderr={result.stderr!r}"
    )

    framework_dir = hidream_out_dir / "framework"
    # 1. Legacy endpoint PNGs preserved.
    for i in range(n_mols):
        ep = framework_dir / f"sample_{i:04d}.png"
        assert ep.exists(), f"missing legacy endpoint PNG: {ep}"

    # 2. Per-round directories + PNGs exist.
    for r in range(n_rounds):
        rdir = framework_dir / f"framework_round{r}"
        assert rdir.exists(), f"missing per-round dir: {rdir}"
        for i in range(n_mols):
            rp = rdir / f"sample_{i:04d}.png"
            assert rp.exists(), f"missing per-round PNG: {rp}"

    # 3. summary.json contract: per_round_png_dirs + per_round_png_count.
    summary_path = hidream_out_dir / "summary.json"
    assert summary_path.exists(), f"missing summary.json: {summary_path}"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["n_mols"] == n_mols
    assert summary["n_rounds"] == n_rounds
    fw = summary["framework"]
    assert fw["per_round_png_dirs"] == [
        f"framework/framework_round{r}" for r in range(n_rounds)
    ]
    assert fw["per_round_png_count"] == n_mols * n_rounds


def test_per_round_dumps_n_rounds_one(
    _venv_python: Path, hidream_out_dir: Path,
) -> None:
    """Edge case: ``n_rounds=1`` does NOT emit per-round subdirectories.

    Phase 4 contract: when ``n_rounds == 1``, the framework arm
    collapses to a single forward pass and ``per_round_png_dirs`` is
    empty (no ``framework_round0/`` dir is created). The legacy
    endpoint PNG is still written.
    """
    import subprocess

    n_mols = 2
    n_rounds = 1
    cmd = [
        str(_venv_python),
        str(SCRIPT_PATH),
        "--n-mols",
        str(n_mols),
        "--n-rounds",
        str(n_rounds),
        "--baseline-nfe",
        "6",
        "--per-round-nfe",
        "6",
        "--resolution",
        "64",
        "--output-dir",
        str(hidream_out_dir),
        "--seed",
        "0",
        "--device",
        "cpu",
        "--allow-cuda0",
        "--skip-eval",
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    assert result.returncode == 0, (
        f"hidream harness failed rc={result.returncode}\n"
        f"  stderr={result.stderr!r}"
    )
    framework_dir = hidream_out_dir / "framework"
    # Legacy endpoint PNGs still present.
    for i in range(n_mols):
        assert (framework_dir / f"sample_{i:04d}.png").exists()
    # No per-round subdirs when n_rounds == 1.
    assert not (framework_dir / "framework_round0").exists()
    summary = json.loads(
        (hidream_out_dir / "summary.json").read_text(encoding="utf-8")
    )
    assert summary["framework"]["per_round_png_dirs"] == []
    assert summary["framework"]["per_round_png_count"] == 0


# ---------------------------------------------------------------------------
# Direct unit test of the per-round callback synthetic path
# ---------------------------------------------------------------------------


def test_emit_synthetic_pngs_emits_per_round() -> None:
    """Direct unit test: ``_emit_synthetic_pngs`` returns the new 3-tuple.

    When ``tag='framework'`` and ``n_rounds > 1``, the helper must
    create ``framework_round{r}/`` subdirs and populate them. When
    ``tag='baseline'`` (or ``n_rounds == 1``), no per-round subdirs are
    emitted.
    """
    spec = importlib.util.spec_from_file_location(
        "run_sota_hidream_i1_experiment", str(SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    # framework + n_rounds > 1 -> per-round subdirs
    out_dir = REPO_ROOT / "data" / "_smoke_hidream_per_round_unit"
    if out_dir.exists():
        import shutil
        shutil.rmtree(out_dir)
    wall, endpoints, per_round = module._emit_synthetic_pngs(
        output_dir=out_dir,
        n_mols=2,
        n_rounds=3,
        resolution=32,
        seed=42,
        tag="framework",
    )
    assert wall >= 0.0
    assert len(endpoints) == 2
    assert len(per_round) == 2 * 3  # n_mols * n_rounds
    for r in range(3):
        rdir = out_dir / f"framework_round{r}"
        assert rdir.exists()
        for i in range(2):
            assert (rdir / f"sample_{i:04d}.png").exists()

    # baseline + n_rounds > 1 -> no per-round subdirs
    base_dir = REPO_ROOT / "data" / "_smoke_hidream_per_round_unit_base"
    if base_dir.exists():
        import shutil
        shutil.rmtree(base_dir)
    wall_b, endpoints_b, per_round_b = module._emit_synthetic_pngs(
        output_dir=base_dir,
        n_mols=2,
        n_rounds=3,
        resolution=32,
        seed=43,
        tag="baseline",
    )
    assert wall_b >= 0.0
    assert len(endpoints_b) == 2
    assert len(per_round_b) == 0  # baseline emits no per-round dirs
    # No framework_round* dirs.
    for r in range(3):
        assert not (base_dir / f"framework_round{r}").exists()


def test_make_per_round_callback_signature() -> None:
    """The callback closure must accept the diffusers 0.30+ signature.

    The HiDream pipeline calls
    ``callback_on_step_end(self, step_index, timestep, callback_kwargs)``
    and the closure MUST return ``callback_kwargs`` so the pipeline
    state flows forward. The closure must be a no-op for steps that
    are not at a round boundary.
    """
    spec = importlib.util.spec_from_file_location(
        "run_sota_hidream_i1_experiment", str(SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    framework_dir = REPO_ROOT / "data" / "_smoke_hidream_per_round_unit_cb"
    if framework_dir.exists():
        import shutil
        shutil.rmtree(framework_dir)
    framework_dir.mkdir(parents=True, exist_ok=True)

    cb = module._make_per_round_callback(
        sample_index=0,
        n_rounds=3,
        per_round_nfe=2,
        framework_dir=framework_dir,
    )

    # The closure must be callable with 4 args and return callback_kwargs.
    fake_kwargs = {"latents": None}
    out = cb(object(), 0, None, fake_kwargs)
    assert out is fake_kwargs  # round 0 boundary: would fire but no latents -> no-op
    out2 = cb(object(), 1, None, fake_kwargs)
    assert out2 is fake_kwargs  # round 1 boundary: same
    # Mid-step (not at a round boundary): closure must return unchanged.
    out_mid = cb(object(), 2, None, fake_kwargs)
    assert out_mid is fake_kwargs
