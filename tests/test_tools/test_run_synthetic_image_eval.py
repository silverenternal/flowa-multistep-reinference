"""Tests for ``tools.run_synthetic_image_eval`` — P-15 phase 3 image oracle gate.

Three test contracts:

1. **Reference stats loader** (``test_load_synthetic_reference``) —
   the canonical synthetic-image InceptionV3 reference statistics
   load through ``load_synthetic_image_reference_stats`` with the
   expected ``(mu, sigma, feature_dim)`` schema. The lookup searches
   the in-repo path first and falls back to the external canonical
   location (``/home/hugo/data/synthetic_image_v1/...``) when the
   in-repo path is absent (the repo ``.gitignore`` excludes ``data/``).

2. **Wrapper end-to-end**
   (``test_wrapper_emits_theorem_aligned_json``) — the
   :class:`tools.run_synthetic_image_eval.run_synthetic_image_eval`
   orchestrator discovers ``framework_round00..02/`` sub-directories,
   extracts InceptionV3 features per round, computes per-round FID
   against the canonical reference, runs the theorem-aligned
   diagnostic via
   :class:`adaptive_reflow.eval.fid_theorem_aligned.PerRoundFIDTracker`,
   and writes a JSON report containing
   ``baseline_fid_per_round`` (null when no baseline dir is supplied),
   ``framework_fid_per_round``, and
   ``theorem_aligned_diagnostic``. The InceptionV3 forward is
   monkeypatched so the test stays hermetic.

3. **Backward compatibility** (``test_backward_compat_no_flag``) —
   invoking ``tools.run_image_eval.main`` *without* the new
   ``--synthetic-image`` flag preserves the legacy byte-stable
   behaviour: when ``--reference-stats`` is provided the runner
   loads it; when it is not, the FID is nulled out (not overridden
   by the canonical synthetic-image stats).
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
# :mod:`tools.run_synthetic_image_eval` + the synthetic-image
# reference stats loader; both depend on ``torch`` (InceptionV3
# forward via torchvision). The :func:`requires_torch` session
# fixture in ``tests/conftest.py`` short-circuits the suite on
# sandboxes where torch is not vendored.
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.usefixtures("requires_torch")

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_RUN_SYNTH_EVAL_PATH = _REPO_ROOT / "tools" / "run_synthetic_image_eval.py"
_RUN_IMAGE_EVAL_PATH = _REPO_ROOT / "tools" / "run_image_eval.py"


def _load_module(name: str, path: Path) -> Any:
    """Import the named module from ``path`` without registering it as a package."""
    repo_str = str(_REPO_ROOT)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def synth_eval_module() -> Any:
    """Loaded ``tools.run_synthetic_image_eval`` (one-shot import)."""
    return _load_module(
        "tools_run_synthetic_image_eval_under_test", _RUN_SYNTH_EVAL_PATH,
    )


@pytest.fixture(scope="module")
def image_eval_module() -> Any:
    """Loaded ``tools.run_image_eval`` (one-shot import)."""
    return _load_module(
        "tools_run_image_eval_under_test", _RUN_IMAGE_EVAL_PATH,
    )


@pytest.fixture()
def canonical_reference_stats(synth_eval_module: Any) -> dict[str, Any]:
    """Return the canonical synthetic-image reference stats ``(mu, sigma, dim)``.

    Skips the test if neither the in-repo nor the external canonical
    path is present (both paths are documented in P-15 phase 1; the
    external path is produced by ``tools/build_synthetic_image_dataset.py``).
    """
    try:
        path = synth_eval_module.resolve_synthetic_image_reference_stats_path()
    except FileNotFoundError:
        pytest.skip(
            "canonical synthetic-image reference stats not found at "
            "either in-repo or external canonical path"
        )
    mu, sigma, dim = synth_eval_module.load_synthetic_image_reference_stats(path)
    return {"path": path, "mu": mu, "sigma": sigma, "feature_dim": int(dim)}


@pytest.fixture()
def tiny_inception_v3(monkeypatch: pytest.MonkeyPatch) -> None:
    """Monkeypatch the canonical InceptionV3 to a deterministic stub.

    The stub produces per-batch constant features ``(B, 2048)`` so the
    covariance is rank-1 (the Fréchet math still produces a finite
    non-negative FID). The stub is registered against
    ``torchvision.models.inception_v3`` so the canonical
    :func:`tools.run_image_eval.load_inception_for_fid` call site
    picks it up.
    """
    import torch
    import torch.nn as nn

    class _TinyInceptionV3(nn.Module):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__()
            self.kwargs = dict(kwargs)
            self.fc = nn.Identity()

        def forward(self, x: torch.Tensor) -> torch.Tensor:  # type: ignore[override]
            # Constant per-batch features; round_index-dependent mean
            # is not modelled (the per-round directory ordering is the
            # only signal the stub needs to vary).
            return torch.zeros(
                (int(x.shape[0]), 2048), dtype=torch.float32,
            )

        def eval(self) -> _TinyInceptionV3:  # type: ignore[override]
            return super().eval()

    monkeypatch.setattr(
        "torchvision.models.inception_v3",
        lambda **kwargs: _TinyInceptionV3(**kwargs),
        raising=True,
    )


def _seed_round_dir(parent: Path, round_idx: int, n_samples: int) -> Path:
    """Create ``parent/framework_round{XX}/`` with ``n_samples`` solid-color PNGs."""
    from PIL import Image

    rd = parent / f"framework_round{round_idx:02d}"
    rd.mkdir(parents=True, exist_ok=True)
    for i in range(n_samples):
        color = ((round_idx * 64 + i * 16) % 256, (round_idx * 32) % 256, 96)
        Image.new("RGB", (8, 8), color).save(rd / f"sample_{i:04d}.png")
    return rd


def _seed_baseline_round_dir(parent: Path, round_idx: int, n_samples: int) -> Path:
    """Create ``parent/baseline_round{XX}/`` with ``n_samples`` solid-color PNGs."""
    from PIL import Image

    rd = parent / f"baseline_round{round_idx:02d}"
    rd.mkdir(parents=True, exist_ok=True)
    for i in range(n_samples):
        # Use a different colour palette so baseline and framework
        # produce distinguishable Inception features.
        color = ((round_idx * 96 + i * 24) % 256, (round_idx * 16) % 256, 160)
        Image.new("RGB", (8, 8), color).save(rd / f"sample_{i:04d}.png")
    return rd


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_load_synthetic_reference(
    synth_eval_module: Any, canonical_reference_stats: dict[str, Any],
) -> None:
    """The canonical synthetic-image reference stats load with the expected schema.

    Locks in:

    * ``mu`` is ``(2048,)`` ``float64`` and finite.
    * ``sigma`` is ``(2048, 2048)`` ``float64`` and PSD.
    * The loaded path is either the in-repo or external canonical
      location (resolved by
      :func:`resolve_synthetic_image_reference_stats_path`).
    """
    path = canonical_reference_stats["path"]
    assert path.is_file(), f"reference stats file not present: {path}"

    mu = canonical_reference_stats["mu"]
    sigma = canonical_reference_stats["sigma"]
    feature_dim = canonical_reference_stats["feature_dim"]

    assert feature_dim == 2048, f"expected feature_dim=2048; got {feature_dim}"
    assert mu.shape == (2048,), f"unexpected mu shape {mu.shape}"
    assert mu.dtype == np.float64, f"mu must be float64; got {mu.dtype}"
    assert np.all(np.isfinite(mu)), "mu is not all-finite"

    assert sigma.shape == (2048, 2048), f"unexpected sigma shape {sigma.shape}"
    assert sigma.dtype == np.float64, f"sigma must be float64; got {sigma.dtype}"
    # Numerical symmetry.
    assert np.allclose(sigma, sigma.T, atol=1e-10), "sigma is not numerically symmetric"
    # PSD (eigenvalues >= -1e-6).
    eigvals = np.linalg.eigvalsh(sigma)
    assert float(eigvals.min()) >= -1e-6, (
        f"sigma is not PSD: min eigenvalue {float(eigvals.min())} < -1e-6"
    )


def test_wrapper_emits_theorem_aligned_json(
    synth_eval_module: Any,
    canonical_reference_stats: dict[str, Any],
    tiny_inception_v3: None,
    tmp_path: Path,
) -> None:
    """``run_synthetic_image_eval`` emits a JSON report with the documented fields.

    Creates 3 ``framework_roundXX/`` subdirs (16 PNGs each) + 3
    ``baseline_roundXX/`` subdirs (16 PNGs each) under a tmp dir,
    invokes the orchestrator, and asserts the JSON contains:

    * ``schema == synthetic_image_theorem_aligned_report.v1``
    * ``framework_fid_per_round`` (list of length 3)
    * ``baseline_fid_per_round`` (list of length 3; both arms supplied)
    * ``theorem_aligned_diagnostic`` (dict with monotone / O_eps_holds /
      paper_quantities_snapshot / epsilon_schedule keys)
    * ``paper_quantities`` (top-level ``(A_g, B_g, C_g, e_rho)`` dict)
    """
    samples_dir = tmp_path / "test_synth_imgs"
    samples_dir.mkdir()
    # Framework: 3 rounds, 16 samples each.
    for r in range(3):
        _seed_round_dir(samples_dir, round_idx=r, n_samples=16)
    # Baseline: 3 rounds, 16 samples each (parallel structure).
    baseline_dir = tmp_path / "test_synth_imgs_baseline"
    baseline_dir.mkdir()
    for r in range(3):
        _seed_baseline_round_dir(baseline_dir, round_idx=r, n_samples=16)

    output_json = tmp_path / "theorem_aligned.json"
    report = synth_eval_module.run_synthetic_image_eval(
        synthetic_images_dir=samples_dir,
        output_json=output_json,
        baseline_images_dir=baseline_dir,
        reference_stats_path=canonical_reference_stats["path"],
        epsilon_schedule=(0.5, 0.25, 0.1),  # 3 rounds
        image_target_size=8,  # tiny for speed
        fid_batch_size=4,
        device_arg="cpu",
    )

    assert output_json.is_file(), "wrapper did not write the JSON report"

    # In-memory contract.
    assert report["schema"] == synth_eval_module.RUN_SYNTHETIC_IMAGE_REPORT_SCHEMA
    assert report["n_rounds"] == 3, f"expected 3 rounds; got {report['n_rounds']}"
    assert isinstance(report["framework_fid_per_round"], list)
    assert len(report["framework_fid_per_round"]) == 3
    for entry in report["framework_fid_per_round"]:
        assert "round_index" in entry
        assert "n_samples" in entry
        assert "fid" in entry
    assert isinstance(report["baseline_fid_per_round"], list)
    assert len(report["baseline_fid_per_round"]) == 3
    for entry in report["baseline_fid_per_round"]:
        assert "round_index" in entry
        assert "n_samples" in entry
        assert "fid" in entry
    # Paper quantities (top-level).
    pq = report["paper_quantities"]
    assert set(pq.keys()) >= {"A_g", "B_g", "C_g", "e_rho", "rho", "c", "eta", "K", "h"}
    # Theorem-aligned diagnostic.
    td = report["theorem_aligned_diagnostic"]
    assert set(td.keys()) >= {
        "monotone", "O_eps_holds", "per_round_deltas",
        "paper_implied_constant", "observed_constant",
        "regime_violations", "paper_quantities_snapshot", "epsilon_schedule",
    }
    assert isinstance(td["monotone"], bool)
    assert isinstance(td["O_eps_holds"], bool)
    assert td["epsilon_schedule"] == [0.5, 0.25, 0.1]

    # On-disk contract.
    on_disk = json.loads(output_json.read_text(encoding="utf-8"))
    assert on_disk["schema"] == synth_eval_module.RUN_SYNTHETIC_IMAGE_REPORT_SCHEMA
    assert on_disk["n_rounds"] == 3
    assert "framework_fid_per_round" in on_disk
    assert "baseline_fid_per_round" in on_disk
    assert "theorem_aligned_diagnostic" in on_disk
    assert len(on_disk["framework_fid_per_round"]) == 3
    assert len(on_disk["baseline_fid_per_round"]) == 3


def test_wrapper_without_baseline_dir(
    synth_eval_module: Any,
    canonical_reference_stats: dict[str, Any],
    tiny_inception_v3: None,
    tmp_path: Path,
) -> None:
    """When no baseline dir is provided, ``baseline_fid_per_round`` is null in the report."""
    samples_dir = tmp_path / "framework_only"
    samples_dir.mkdir()
    for r in range(3):
        _seed_round_dir(samples_dir, round_idx=r, n_samples=16)

    output_json = tmp_path / "framework_only.json"
    report = synth_eval_module.run_synthetic_image_eval(
        synthetic_images_dir=samples_dir,
        output_json=output_json,
        baseline_images_dir=None,  # no baseline arm
        reference_stats_path=canonical_reference_stats["path"],
        epsilon_schedule=(0.5, 0.25, 0.1),
        image_target_size=8,
        fid_batch_size=4,
        device_arg="cpu",
    )
    assert report["baseline_fid_per_round"] is None
    assert report["baseline_round_dirs"] is None
    assert report["baseline_n_samples_per_round"] is None
    assert report["baseline_images_dir"] is None
    assert len(report["framework_fid_per_round"]) == 3


def test_parse_g_profile_source_rejects_unsafe(synth_eval_module: Any) -> None:
    """``parse_g_profile_source`` rejects non-``math`` attribute access and unknown names."""
    # ``os.system(...)`` — the attribute check fires first because the
    # AST walk visits the ``Attribute`` node before its child ``Name``
    # ``os``. Either rejection (disallowed_name or disallowed_attribute)
    # is acceptable so long as the source is rejected.
    with pytest.raises(ValueError, match="disallowed_"):
        synth_eval_module.parse_g_profile_source("os.system('rm -rf /')")
    # Disallowed attribute (not math.<symbol>).
    with pytest.raises(ValueError, match="disallowed_attribute"):
        synth_eval_module.parse_g_profile_source("open('/etc/passwd').read()")
    # Disallowed non-math builtin name.
    with pytest.raises(ValueError, match="disallowed_name"):
        synth_eval_module.parse_g_profile_source("len(x)")
    # Disallowed chained math access via non-math prefix.
    with pytest.raises(ValueError, match="disallowed_attribute"):
        synth_eval_module.parse_g_profile_source("os.tanh(x)")
    # Valid expression parses + evaluates.
    g = synth_eval_module.parse_g_profile_source(
        "(1 + 0.25 * math.tanh(x)) * math.sin(x)",
    )
    assert g(0.0) == 0.0  # sin(0) = 0
    assert abs(g(1.0)) < 2.0  # bounded


def test_backward_compat_no_flag(
    image_eval_module: Any, tmp_path: Path, tiny_inception_v3: None,
) -> None:
    """``run_image_eval.main`` without ``--synthetic-image`` preserves legacy behaviour.

    When ``--synthetic-image`` is omitted and ``--reference-stats`` is
    provided explicitly, the runner uses the explicit path. When
    ``--synthetic-image`` is omitted and ``--reference-stats`` is also
    omitted, the FID is nulled (NOT overridden by the canonical
    synthetic-image stats).
    """
    # 1. Explicit --reference-stats path is honoured (no --synthetic-image).
    from PIL import Image

    samples_dir = tmp_path / "samples"
    samples_dir.mkdir()
    for i in range(4):
        Image.new("RGB", (8, 8), (i * 32, 64, 96)).save(samples_dir / f"sample_{i:04d}.png")
    out_explicit = tmp_path / "explicit.json"
    ref_npz = tmp_path / "ref.npz"
    np.savez(
        ref_npz,
        mu=np.zeros(2048, dtype=np.float64),
        sigma=np.eye(2048, dtype=np.float64),
    )
    rc = image_eval_module.main([
        "--samples-dir", str(samples_dir),
        "--reference-stats", str(ref_npz),
        "--output", str(out_explicit),
        "--device", "cpu",
        "--fid-batch-size", "4",
        "--image-target-size", "8",
    ])
    assert rc == 0
    assert out_explicit.is_file()
    on_disk = json.loads(out_explicit.read_text(encoding="utf-8"))
    assert on_disk["reference_stats"] == str(ref_npz)

    # 2. No --reference-stats and no --synthetic-image: FID is null,
    # NOT overridden by the canonical synthetic-image stats.
    out_no_ref = tmp_path / "no_ref.json"
    rc2 = image_eval_module.main([
        "--samples-dir", str(samples_dir),
        "--output", str(out_no_ref),
        "--device", "cpu",
        "--fid-batch-size", "4",
        "--image-target-size", "8",
    ])
    assert rc2 == 0
    on_disk_no_ref = json.loads(out_no_ref.read_text(encoding="utf-8"))
    assert on_disk_no_ref["reference_stats"] is None
    assert on_disk_no_ref["metrics"]["fid"]["value"] is None
    assert on_disk_no_ref["metrics"]["fid"]["error"] == "reference_stats_not_provided"


def test_synthetic_image_flag_overrides_reference_stats(
    image_eval_module: Any, tmp_path: Path, tiny_inception_v3: None,
    canonical_reference_stats: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``--synthetic-image`` is set, the runner loads the canonical stats.

    Verifies the additive flag in ``run_image_eval.py`` resolves the
    canonical path and overrides any explicit ``--reference-stats``.
    """
    from PIL import Image

    samples_dir = tmp_path / "samples"
    samples_dir.mkdir()
    for i in range(4):
        Image.new("RGB", (8, 8), (i * 32, 64, 96)).save(samples_dir / f"sample_{i:04d}.png")
    out = tmp_path / "synth_override.json"
    # Pass a *different* --reference-stats to confirm it gets
    # overridden by the canonical synthetic-image path.
    other_ref = tmp_path / "other_ref.npz"
    np.savez(
        other_ref,
        mu=np.zeros(2048, dtype=np.float64),
        sigma=np.eye(2048, dtype=np.float64),
    )
    rc = image_eval_module.main([
        "--samples-dir", str(samples_dir),
        "--reference-stats", str(other_ref),
        "--synthetic-image",
        "--output", str(out),
        "--device", "cpu",
        "--fid-batch-size", "4",
        "--image-target-size", "8",
    ])
    assert rc == 0
    on_disk = json.loads(out.read_text(encoding="utf-8"))
    # The reported reference_stats path is the canonical synthetic path,
    # NOT the explicit ``other_ref`` we passed.
    assert on_disk["reference_stats"] == str(canonical_reference_stats["path"])
    assert str(canonical_reference_stats["path"]) != str(other_ref)
