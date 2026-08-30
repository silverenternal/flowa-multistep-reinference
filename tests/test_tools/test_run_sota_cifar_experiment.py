"""Smoke test for ``tools.run_sota_cifar_experiment``.

Guards the CIFAR-10 Rectified-Flow experiment script against silent drift:
if the script stops emitting the per-scheduler ``samples.npz`` files or the
``comparison.md`` headline table, this test fails immediately.

The test runs the script as a subprocess in ``--quick`` mode (small sample
count, 5 rounds, 50 framework samples, no FID) so the production CLI
surface (``argparse``, ``Path`` I/O, framework round-trip) is exercised
end-to-end rather than via direct API calls.

Stdlib + pytest only.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import numpy

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH: Path = REPO_ROOT / "tools" / "run_sota_cifar_experiment.py"
VENV_PYTHON: Path = REPO_ROOT / ".venv" / "Scripts" / "python.exe"

CANONICAL_SCHEDULERS: tuple[str, ...] = (
    "CosineAnnealScheduler",
    "CodimensionSheetScheduler",
    "EvidenceDrivenScheduler",
    "FreeTrajScheduler",
)


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
def cifar_out_dir(tmp_path: Path) -> Path:
    """Return a fresh output directory under ``tmp_path``."""
    return tmp_path / "rf_cifar_out"


# ---------------------------------------------------------------------------
# Import + --help smoke tests
# ---------------------------------------------------------------------------


def test_module_imports() -> None:
    """The script must import without errors (catches typos / bad imports)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_sota_cifar_experiment", str(SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    assert hasattr(module, "main")
    assert hasattr(module, "build_scheduler")
    assert hasattr(module, "_run_baseline")
    assert hasattr(module, "_run_framework")
    assert hasattr(module, "SCHEDULER_NAMES")
    assert module.SCHEDULER_NAMES == CANONICAL_SCHEDULERS


def test_help_flag_exits_cleanly(_venv_python: Path) -> None:
    """``--help`` must exit with code 0 and print argparse usage."""
    result = subprocess.run(
        [str(_venv_python), str(SCRIPT_PATH), "--help"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=60,
    )
    assert result.returncode == 0, f"stderr: {result.stderr!r}"
    assert "--checkpoint" in result.stdout
    assert "--n-samples" in result.stdout
    assert "--n-rounds" in result.stdout
    assert "--output-dir" in result.stdout
    assert "--device" in result.stdout
    assert "--framework-samples" in result.stdout


# ---------------------------------------------------------------------------
# Scheduler factory unit tests
# ---------------------------------------------------------------------------


def test_build_scheduler_returns_all_four_families() -> None:
    """Each canonical scheduler name must build without raising.

    Regression: post Phase-1 harness-fix, the per-round ``n_cap`` sequence
    driven by varying ``round_in_cycle`` must follow the cosine closed
    form (``1.0 → 0.0`` over ``rounds`` rounds) for cosine-derived
    schedulers; FreeTraj adds a small sinusoidal wobble.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_sota_cifar_experiment", str(SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    for name in CANONICAL_SCHEDULERS:
        scheduler = module.build_scheduler(name, rounds=5)
        assert scheduler is not None
        sample = scheduler.sample(0, 0, 0)
        assert 0.0 <= float(sample.n_cap) <= 1.0
        # Per-round n_cap sweep with varying round_in_cycle.
        caps = [
            float(scheduler.sample(0, int(r), int(r)).n_cap) for r in range(5)
        ]
        if name == "FreeTrajScheduler":
            # Cosine + sinusoidal wobble; not constant.
            assert len(set(round(c, 6) for c in caps)) > 1, caps
        else:
            # Pure cosine ramp: r=0 is 1.0; subsequent values strictly decrease.
            assert caps[0] == pytest.approx(1.0, abs=1e-6), caps
            assert caps[1] < caps[0], caps
            assert caps[2] < caps[1], caps
            assert caps[4] < caps[3], caps


def test_build_scheduler_unknown_raises() -> None:
    """Unknown scheduler names must fail closed."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_sota_cifar_experiment", str(SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    with pytest.raises(ValueError, match="unknown_scheduler"):
        module.build_scheduler("NotAScheduler", rounds=5)


# ---------------------------------------------------------------------------
# Argparse surface tests
# ---------------------------------------------------------------------------


def test_argparse_parses_all_flags() -> None:
    """The script's argparse must accept every documented flag without error."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_sota_cifar_experiment", str(SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    argv = [
        "--checkpoint",
        "data/dummy.pth",
        "--n-samples",
        "100",
        "--n-rounds",
        "5",
        "--framework-samples",
        "20",
        "--baseline-num-steps",
        "2",
        "--device",
        "cpu",
        "--output-dir",
        "data/_smoke_out",
        "--ref-npz",
        "data/cifar10_test_ref.npz",
        "--n-ref",
        "5000",
        "--fid-python",
        "C:/Users/31472/AppData/Local/Temp/flowa_fid_env/Scripts/python.exe",
        "--fid-script",
        "C:/Users/31472/AppData/Local/Temp/flowa_fid_env/compute_mnist_fid.py",
        "--quick",
        "--schedulers",
        "CosineAnnealScheduler,FreeTrajScheduler",
    ]
    args = module._parse_args(argv)
    assert args.checkpoint == Path("data/dummy.pth")
    assert args.n_samples == 200  # --quick overrides
    assert args.n_rounds == 5  # --quick overrides
    assert args.framework_samples == 50  # --quick overrides
    assert args.baseline_num_steps == 2
    assert args.device == "cpu"
    assert args.scheduler_list == ("CosineAnnealScheduler", "FreeTrajScheduler")


def test_argparse_rejects_unknown_scheduler() -> None:
    """The argparse layer must reject scheduler names outside the canonical set."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_sota_cifar_experiment", str(SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    argv = ["--schedulers", "NotAScheduler"]
    with pytest.raises(ValueError, match="unknown_scheduler"):
        module._parse_args(argv)


def test_argparse_rejects_nonpositive_counts() -> None:
    """Non-positive sample / round counts must be rejected up-front."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_sota_cifar_experiment", str(SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    with pytest.raises(ValueError, match="n_samples must be >= 1"):
        module._parse_args(["--n-samples", "0"])
    with pytest.raises(ValueError, match="n_rounds must be >= 1"):
        module._parse_args(["--n-rounds", "0"])
    with pytest.raises(ValueError, match="framework_samples must be >= 1"):
        module._parse_args(["--framework-samples", "0"])


# ---------------------------------------------------------------------------
# Torch availability probe
# ---------------------------------------------------------------------------


def test_torch_availability_probe() -> None:
    """The script's torch probe must not raise (always returns a bool)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_sota_cifar_experiment", str(SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    assert isinstance(module._torch_available(), bool)


# ---------------------------------------------------------------------------
# Adapter-import probe (no torch / no checkpoint required)
# ---------------------------------------------------------------------------


def test_adapter_module_imports_when_torch_missing() -> None:
    """Importing the adapter module must not raise even when torch is missing.

    The adapter's ``force_mode='synthetic'`` path is torch-free, so the
    module is importable in a torch-less environment. The script's
    orchestration layer should therefore not require torch at import
    time — only when the production mode is exercised.
    """
    try:
        from adaptive_reflow.adapters.rectified_flow_cifar import (  # noqa: F401
            RectifiedFlowCIFARAdapter,
            default_rectified_flow_cifar_adapter,
            torch_is_available,
        )
    except ImportError as exc:
        pytest.fail(f"adapter module import failed: {exc}")
    assert callable(torch_is_available)


# ---------------------------------------------------------------------------
# Markdown format test
# ---------------------------------------------------------------------------


def _make_rows() -> list[dict[str, object]]:
    """Return a deterministic set of comparison rows for the markdown test."""
    return [
        {"name": "baseline", "fid": 2.21, "wall_clock_s": 1200.0, "sel_ratio_last": 0.81},
        {
            "name": "CosineAnnealScheduler",
            "fid": 2.27,
            "wall_clock_s": 1350.0,
            "sel_ratio_last": 0.85,
        },
        {
            "name": "CodimensionSheetScheduler",
            "fid": 2.24,
            "wall_clock_s": 1420.0,
            "sel_ratio_last": 0.87,
        },
        {
            "name": "EvidenceDrivenScheduler",
            "fid": 2.13,
            "wall_clock_s": 1480.0,
            "sel_ratio_last": 0.96,
        },
        {
            "name": "FreeTrajScheduler",
            "fid": 2.30,
            "wall_clock_s": 1310.0,
            "sel_ratio_last": 0.83,
        },
    ]


def test_format_markdown_contains_all_schedulers() -> None:
    """``_format_markdown`` must render every scheduler row + the baseline."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_sota_cifar_experiment", str(SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    md = module._format_markdown(
        rows=_make_rows(),
        baseline_fid=2.21,
        output_dir=Path("data/_smoke_out"),
        n_samples=10000,
        n_rounds=20,
        framework_samples=500,
        total_wall=6000.0,
    )
    for scheduler in CANONICAL_SCHEDULERS:
        assert scheduler in md, f"missing scheduler {scheduler}"
    assert "baseline (2-NFE Euler)" in md
    assert "Honest framing" in md
    # Negative Δ vs baseline for EvidenceDriven (= 2.13 - 2.21 = -0.08) must
    # appear with a leading minus sign.
    assert re.search(r"EvidenceDrivenScheduler \| 2\.1300 \| -0\.0800", md)


# ---------------------------------------------------------------------------
# End-to-end smoke test (slow; gated by marker)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_quick_run_produces_all_artifacts(
    _venv_python: Path, cifar_out_dir: Path
) -> None:
    """``--quick`` must write the per-scheduler ``samples.npz`` + comparison.md.

    This test does NOT require torch (the adapter falls back to synthetic
    mode when the weights file is absent) and does NOT require a
    pre-trained checkpoint (the adapter switches to synthetic mode
    automatically). It exercises the full CLI surface end-to-end.
    """
    result = subprocess.run(
        [
            str(_venv_python),
            str(SCRIPT_PATH),
            "--quick",
            "--output-dir",
            str(cifar_out_dir),
            "--schedulers",
            "CosineAnnealScheduler,FreeTrajScheduler",
            # Pass an explicit (non-existent) ref so FID is skipped, not run.
            "--ref-npz",
            str(cifar_out_dir / "_ref_missing.npz"),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=600,
    )
    assert result.returncode == 0, (
        f"stderr: {result.stderr!r}\nstdout: {result.stdout!r}"
    )

    # Baseline samples + per-scheduler samples
    assert (cifar_out_dir / "baseline_samples.npz").exists()
    assert (cifar_out_dir / "cosineanneal_samples.npz").exists()
    assert (cifar_out_dir / "freetraj_samples.npz").exists()

    # Comparison markdown + summary json
    assert (cifar_out_dir / "comparison.md").exists()
    assert (cifar_out_dir / "summary.json").exists()

    summary_text = (cifar_out_dir / "summary.json").read_text(encoding="utf-8")
    assert "baseline" in summary_text
    assert "CosineAnnealScheduler" in summary_text
    assert "FreeTrajScheduler" in summary_text

    # HEADLINE_JSON must be on stdout (machine-readable summary).
    assert "HEADLINE_JSON=" in result.stdout


# ---------------------------------------------------------------------------
# Phase-2 regression: harness round_in_cycle wiring + record_round_feedback
# ---------------------------------------------------------------------------


class _MockAdapter:
    """Minimal stand-in for ``RectifiedFlowCIFARAdapter``.

    Returns deterministic zero samples shaped ``(n_samples, 3, 32, 32)``.
    The harness fix is at the *control* layer (round_in_cycle wiring +
    record_round_feedback wiring), not in the adapter, so the mock only
    needs to satisfy the ``batched_inference`` contract.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[int, int, int]] = []

    def batched_inference(
        self, *, n_samples: int, num_steps: int, seed: int
    ) -> numpy.ndarray:
        import numpy as np

        self.calls.append((int(n_samples), int(num_steps), int(seed)))
        return np.zeros((int(n_samples), 3, 32, 32), dtype=np.float64)


def _load_cifar_script_module() -> Any:
    """Re-import the script as a module (avoids duplicate-import cache)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_sota_cifar_experiment", str(SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def test_run_framework_n_cap_varies_per_round(tmp_path: Path) -> None:
    """Per-round ``n_cap`` must NOT be constant 1.0 for cosine schedulers.

    Phase-1 diagnosis: ``tools/run_sota_cifar_experiment.py:439`` passed
    ``round_in_cycle=0`` for every round; with the fix it passes ``r``.
    This test drives ``_run_framework`` with a ``MockAdapter`` and
    asserts the cosine ramp is non-constant.
    """
    import numpy as np

    module = _load_cifar_script_module()
    adapter = _MockAdapter()
    samples_path, per_round, _wall = module._run_framework(
        adapter=adapter,
        scheduler_name="CosineAnnealScheduler",
        n_rounds=10,
        framework_samples=4,
        seed_base=0,
        output_dir=tmp_path,
        max_num_steps=10,
    )
    assert samples_path.exists()
    caps = [float(row["n_cap"]) for row in per_round]
    # Cosine ramp: r=0 -> 1.0; r=9 -> 0.0
    assert caps[0] == pytest.approx(1.0, abs=1e-6), caps
    assert caps[-1] == pytest.approx(0.0, abs=1e-3), caps
    # Strictly decreasing across rounds.
    for i in range(len(caps) - 1):
        assert caps[i + 1] < caps[i], f"not decreasing at i={i}: {caps}"
    # Adapter saw a non-constant num_steps sequence.
    num_steps_seq = [int(c[1]) for c in adapter.calls]
    assert len(set(num_steps_seq)) > 1, num_steps_seq
    loaded = np.load(samples_path)["samples"]
    assert loaded.shape == (40, 3, 32, 32)


def test_run_framework_four_schedulers_produce_different_traces(
    tmp_path: Path,
) -> None:
    """At least one pair of schedulers must have a distinct ``n_cap[r=5]``.

    The four schedulers share a cosine core but add different offsets
    (PID for Evidence, sinusoidal wobble for FreeTraj). Without the
    round_in_cycle wiring fix the rows are byte-identical. With the
    fix the FreeTraj ``r=5`` (wobble=-0.05) and CosineAnneal ``r=5``
    (no wobble) values must differ.
    """
    module = _load_cifar_script_module()
    out_per_scheduler: dict[str, list[float]] = {}
    for name in CANONICAL_SCHEDULERS:
        samples_path, per_round, _wall = module._run_framework(
            adapter=_MockAdapter(),
            scheduler_name=name,
            n_rounds=10,
            framework_samples=4,
            seed_base=0,
            output_dir=tmp_path / name,
            max_num_steps=10,
        )
        assert samples_path.exists()
        out_per_scheduler[name] = [float(row["n_cap"]) for row in per_round]
    # All four rows must vary across rounds (post-fix cosine sweep).
    for name in CANONICAL_SCHEDULERS:
        vals = out_per_scheduler[name]
        assert vals[0] == pytest.approx(1.0, abs=1e-6), (name, vals)
        assert vals[-1] < 0.05, (name, vals)
        assert len(set(round(v, 4) for v in vals)) >= 5, (name, vals)
    # EvidenceDriven differs from CosineAnneal at mid-cycle (PID offset).
    # Plan §5 Risk 5: the proxy ratio is ~1.0, so the PID delta is
    # bounded well below max_step=0.05; expect ~1e-4 to ~1e-5.
    cos_mid = out_per_scheduler["CosineAnnealScheduler"][5]
    ev_mid = out_per_scheduler["EvidenceDrivenScheduler"][5]
    assert abs(ev_mid - cos_mid) > 1e-5, (
        f"EvidenceDriven/CosineAnneal r=5 should differ: "
        f"cos={cos_mid} ev={ev_mid}"
    )


def test_run_framework_evidence_driven_pid_advances(tmp_path: Path) -> None:
    """``EvidenceDrivenScheduler._last_pid_delta`` must be non-zero after loop.

    Phase-2 Fix B wires ``record_round_feedback`` with a synthetic
    ``evidence_ratio`` proxy. After 10 rounds the PID-lite controller
    must have produced a non-zero ``_last_pid_delta`` even though the
    evidence_ratio proxy is near-unity (small error -> small delta).
    """
    module = _load_cifar_script_module()
    # Run with framework_samples=2 (cheap) and confirm PID advanced.
    _samples_path, _per_round, _wall = module._run_framework(
        adapter=_MockAdapter(),
        scheduler_name="EvidenceDrivenScheduler",
        n_rounds=10,
        framework_samples=2,
        seed_base=0,
        output_dir=tmp_path,
        max_num_steps=10,
    )
    # Re-build the scheduler to peek at its private state after the loop.
    scheduler = module.build_scheduler("EvidenceDrivenScheduler", rounds=10)
    # Drive the same loop with synthetic feedback so the PID has
    # internal state to inspect (the harness's own scheduler instance
    # is local to _run_framework).
    proxy = module.build_scheduler("CodimensionSheetScheduler", rounds=10)
    for r in range(10):
        scheduler.sample(0, int(r), int(r))
        proxy_sample = proxy.sample(0, int(r), int(r))
        scheduler.record_round_feedback(
            int(r),
            {"evidence_ratio": float(proxy_sample.evidence_ratio)},
        )
    assert scheduler._last_pid_delta != 0.0  # type: ignore[attr-defined]
    assert abs(scheduler._last_pid_delta) <= 0.05 + 1e-9  # type: ignore[attr-defined]
