"""Tests for ``tools.build_synthetic_image_dataset`` — P-15 image oracle.

These tests lock in five contracts for the P-15 synthetic-image
ground-truth dataset:

1. **Determinism** (``test_generate_5000_images_deterministic``) — two
   calls with the same seed produce bit-identical pixel arrays.
2. **Schema** (``test_image_shape_and_label``) — every image is
   ``(256, 256, 3)`` ``uint8`` on disk; the label record matches
   :class:`SyntheticImageLabel`'s typed schema.
3. **Stats finiteness** (``test_inception_reference_stats_finite``) —
   the reference ``mu`` is all-finite and the reference ``sigma`` is
   symmetric positive-semidefinite within ``1e-6`` tolerance.
4. **Pretrained-load guard**
   (``test_reference_stats_pretrained``) — ``|mu.mean()|`` is below
   the absolute upper bound; the random-init bug signature
   (~``5.9e10``) is rejected. This is the audit-``2fb3dc0``
   regression-guard mirror.
5. **Class distribution** (``test_label_distribution``) — each shape
   class accounts for roughly ``n / 4`` labels (``>= 20 %`` and
   ``<= 30 %`` — within 5 pp of 25 %), so the per-round FID can be
   decomposed across shape classes later.

The InceptionV3 forward is run on the real pretrained network at
``~/.cache/torch/hub/checkpoints/`` (so the test is end-to-end). For
unit-level determinism checks we mock the network with a small
deterministic stub.

CLI smoke
---------

``test_cli_writes_artifacts`` invokes the script as a subprocess
against a small ``--n-samples`` to validate the entry point + output
manifest without paying for 5K PIL renders.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Preflight: this module exercises
# :mod:`tools.build_synthetic_image_dataset` end-to-end (InceptionV3
# pretrained reference stats, CLI subprocess smoke). Both paths
# require ``torch``. The :func:`requires_torch` session fixture in
# ``tests/conftest.py`` short-circuits the suite on sandboxes where
# torch is not vendored.
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.usefixtures("requires_torch")

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BUILDER_PATH = _REPO_ROOT / "tools" / "build_synthetic_image_dataset.py"


def _load_builder() -> Any:
    """Import :mod:`tools.build_synthetic_image_dataset` without registering ``tools`` as a package.

    Registers the loaded module in :data:`sys.modules` so the
    ``dataclass`` decorator can resolve ``cls.__module__`` when the
    annotations are namespace strings (PIL / numpy names live as
    forward references under :mod:`tools`; the synthetic-image
    builder relies on :mod:`typing.Any` etc.). Without the
    registration, :func:`dataclasses._create_fn` raises
    ``AttributeError: 'NoneType' object has no attribute '__dict__'``
    at the first ``@dataclass`` decorator site.
    """
    repo_str = str(_REPO_ROOT)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)
    spec = importlib.util.spec_from_file_location(
        "tools_build_synthetic_image_dataset_under_test",
        str(_BUILDER_PATH),
    )
    if spec is None or spec.loader is None:  # pragma: no cover — defensive
        raise ImportError(f"could not load {_BUILDER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def builder() -> Any:
    """Loaded builder module (one-shot import per test session)."""
    return _load_builder()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def tiny_real_dataset(builder: Any, tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Run a real (small) build to produce PNGs + labels.csv + reference stats.

    Uses ``n_samples=64`` so the test stays under a few seconds even
    on CPU. The full pretrained InceptionV3 is loaded so the random-init
    bug-signature test is exercised end-to-end.
    """
    out = tmp_path_factory.mktemp("synthetic_image_v1_64") / "v1"
    report = builder.build_synthetic_image_dataset(
        n_samples=64,
        seed=int(builder.BUILD_DEFAULT_SEED),
        output_dir=str(out),
        device="auto",
    )
    return {"report": report, "output_dir": out}


@pytest.fixture()
def stub_inception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Monkeypatch ``torchvision.models.inception_v3`` with a deterministic stub.

    Returns ``(B, 2048)`` features produced by mean-pooling the input
    channels, then padding to 2048 with a noise-free constant so the
    feature space is deterministic. The stub mimics the canonical
    pool3 contract (last-axis dim == 2048) so the post-processing math
    in :meth:`GeometricShapeImageOracle.compute_inception_reference_stats`
    runs unchanged.
    """
    import torch
    import torch.nn as nn

    class _TinyInception(nn.Module):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__()
            self.kwargs = dict(kwargs)
            self.fc = nn.Identity()

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            # Deterministic: per-batch constant features. mean over
            # spatial dims gives (B, 3); we pad to 2048 with a known
            # fill value so the covariance is exactly rank-3 and the
            # eigenvalues-decomposition PSD check succeeds. This
            # shape is irrelevant — the test only cares that
            # ``compute_inception_reference_stats`` completes and
            # produces a (2048,) + (2048, 2048) result.
            pooled = x.mean(dim=(2, 3))
            out = torch.zeros(int(x.shape[0]), 2048, dtype=torch.float32)
            out[:, :3] = pooled
            # Channel-wise tiny positive slope so the rank-3
            # covariance is non-degenerate.
            arange = torch.arange(2048, dtype=torch.float32).unsqueeze(0)
            out = out + 0.001 * arange
            return out

        def eval(self) -> "_TinyInception":
            return super().eval()

    def _factory(**kwargs: Any) -> _TinyInception:
        return _TinyInception(**kwargs)

    monkeypatch.setattr(
        "torchvision.models.inception_v3", _factory, raising=True,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_generate_5000_images_deterministic(builder: Any) -> None:
    """Same seed -> bit-identical pixel arrays across two oracle runs.

    We use a small ``n`` for speed; the determinism contract is
    identical for any ``n >= 1`` because every ``generate_batch`` call
    constructs a fresh ``random.Random(seed)`` instance and uses only
    ``randrange`` to advance state.
    """
    oracle = builder.GeometricShapeImageOracle()
    arr_a, labels_a = oracle.generate_batch(n=16, seed=42)
    arr_b, labels_b = oracle.generate_batch(n=16, seed=42)
    # ``np.array_equal`` requires bit-identical values for ``float32``.
    assert np.array_equal(arr_a, arr_b), (
        "two generate_batch calls with seed=42 produced different arrays"
    )
    # Cross-version stability check: labels should also be equal.
    assert len(labels_a) == len(labels_b)
    for la, lb in zip(labels_a, labels_b):
        assert (
            la.image_index == lb.image_index
            and la.shape_name == lb.shape_name
            and la.color_name == lb.color_name
            and la.position_x == lb.position_x
            and la.position_y == lb.position_y
            and la.size == lb.size
            and la.text_label == lb.text_label
        )
    # Negative control: a different seed produces different arrays.
    arr_c, _ = oracle.generate_batch(n=16, seed=43)
    assert not np.array_equal(arr_a, arr_c)


def test_image_shape_and_label(builder: Any, tmp_path: Path) -> None:
    """Each PNG is 256x256x3; label schema matches :class:`SyntheticImageLabel`."""
    out = tmp_path / "schema"
    builder.build_synthetic_image_dataset(
        n_samples=4,
        seed=int(builder.BUILD_DEFAULT_SEED),
        output_dir=str(out),
        device="auto",
    )
    images_dir = out / "images"
    assert images_dir.is_dir()
    png_paths = sorted(images_dir.glob("image_*.png"))
    assert len(png_paths) == 4
    # Read back with PIL + verify shape.
    from PIL import Image
    for p in png_paths:
        with Image.open(p) as im:
            assert im.mode == "RGB", f"mode mismatch for {p}: {im.mode}"
            assert im.size == (256, 256), f"size mismatch for {p}: {im.size}"
    # Verify labels.csv is parseable + matches the schema.
    import csv as _csv
    with (out / "labels.csv").open("r", encoding="utf-8") as fh:
        reader = _csv.DictReader(fh)
        rows = list(reader)
    assert len(rows) == 4
    expected_keys = {
        "image_index", "shape_name", "color_name",
        "position_x", "position_y", "size", "text_label",
    }
    for row in rows:
        assert set(row.keys()) == expected_keys
        assert row["shape_name"] in builder.SHAPE_NAMES
        assert row["color_name"] in builder.COLOR_NAMES
        assert int(row["size"]) >= 16
        # Position must be within the canvas.
        assert 0 <= int(row["position_x"]) < 256
        assert 0 <= int(row["position_y"]) < 256 - 18  # 18-px bottom band


def test_inception_reference_stats_finite(
    builder: Any, tmp_path: Path, stub_inception: None,
) -> None:
    """mu is finite and sigma is PSD (eigenvalues >= 0 within 1e-6 tolerance).

    The stub InceptionV3 ensures the test stays fast + hermetic.
    """
    out = tmp_path / "psd"
    builder.build_synthetic_image_dataset(
        n_samples=16,
        seed=int(builder.BUILD_DEFAULT_SEED),
        output_dir=str(out),
        device="auto",
    )
    stats = np.load(out / "inception_reference_stats.npz")
    mu = np.asarray(stats["mu"], dtype=np.float64)
    sigma = np.asarray(stats["sigma"], dtype=np.float64)
    assert mu.shape == (2048,), f"unexpected mu shape {mu.shape}"
    assert sigma.shape == (2048, 2048), f"unexpected sigma shape {sigma.shape}"
    assert np.all(np.isfinite(mu)), "mu is not all-finite"
    # Numerical symmetry tolerance — np.cov is symmetric by
    # construction; allow 1e-10 round-off.
    assert np.allclose(sigma, sigma.T, atol=1e-10), "sigma is not numerically symmetric"
    # PSD: eigenvalues >= 0 (allow tiny negative numerical noise).
    eigvals = np.linalg.eigvalsh(sigma)
    min_eig = float(eigvals.min())
    assert min_eig >= -1e-6, (
        f"sigma is not PSD: min eigenvalue {min_eig} < -1e-6"
    )


def test_reference_stats_pretrained(builder: Any, tiny_real_dataset: dict[str, Any]) -> None:
    """Reject the random-init bug signature.

    ``|mu.mean()| < 1e3`` is sufficient: a pretrained ImageNet InceptionV3
    produces pool3 features with magnitudes around ``0.3``, while a
    randomly-initialized network produces magnitudes around ``5.9e10``
    (the audited regression signature from commit ``2fb3dc0``).
    The ``is_pretrained`` predicate on :class:`InceptionReferenceStats`
    formalises the same gate.
    """
    stats_path = Path(tiny_real_dataset["report"]["reference_stats_path"])
    assert stats_path.is_file(), f"reference stats not written: {stats_path}"
    stats = np.load(stats_path)
    mu = np.asarray(stats["mu"], dtype=np.float64)
    sigma = np.asarray(stats["sigma"], dtype=np.float64)
    abs_mu_mean = float(abs(mu.mean()))
    # Random-init bug signature
    assert abs_mu_mean != pytest.approx(builder.RANDOM_INIT_FID_MU_MEAN_BUG_SIGNATURE, rel=0.5)
    # Absolute pretrained guard — pretrained ImageNet pool3 means
    # sit at ~0.3, well below 1e3. Random-init sits at ~1e10+ so the
    # 7-order-of-magnitude margin rejects it cleanly.
    assert abs_mu_mean < builder.BUILD_PRETRAINED_MU_MEAN_ABS_UPPER_BOUND, (
        f"random-init bug suspected: |mu.mean()|={abs_mu_mean:e} >= "
        f"{builder.BUILD_PRETRAINED_MU_MEAN_ABS_UPPER_BOUND:e}"
    )
    # Sigma diagonal mean should be finite too (pretrained variance).
    sigma_diag_mean = float(np.mean(np.diag(sigma)))
    import math
    assert math.isfinite(sigma_diag_mean)
    # Sanity-check the diagonal is positive (a PSD covariance has
    # non-negative diagonal).
    diag = np.diag(sigma)
    assert np.all(diag >= -1e-10), "sigma diagonal has unexpectedly large negative entries"


def test_label_distribution(builder: Any, tmp_path: Path) -> None:
    """Roughly 1/4 of each shape class in a 256-image batch.

    With 4 shape classes drawn uniformly from ``random.Random(seed)``
    over 256 trials, each class is expected to be ~64 with a
    standard deviation of ~6 (binomial ``sqrt(256 * 0.25 * 0.75) ≈
    6.9``). The test asserts each class count is between ``[52,
    76]`` (``[-2σ, +2σ]``) so a bad RNG (e.g. one that always picks
    the first class) is rejected.
    """
    out = tmp_path / "dist"
    builder.build_synthetic_image_dataset(
        n_samples=256,
        seed=int(builder.BUILD_DEFAULT_SEED),
        output_dir=str(out),
        device="auto",
    )
    import csv as _csv
    shape_counts: dict[str, int] = {n: 0 for n in builder.SHAPE_NAMES}
    with (out / "labels.csv").open("r", encoding="utf-8") as fh:
        reader = _csv.DictReader(fh)
        for row in reader:
            shape_counts[row["shape_name"]] += 1
    # Each class should be ~64 (n / 4) within the ±2σ envelope.
    for shape_name, count in shape_counts.items():
        assert 52 <= count <= 76, (
            f"shape class {shape_name!r} count {count} is outside [52, 76] "
            f"for n=256"
        )
    # Sanity: total == n.
    assert sum(shape_counts.values()) == 256


def test_manifest_written(builder: Any, tmp_path: Path) -> None:
    """Build writes ``manifest.json`` with the documented schema."""
    out = tmp_path / "manifest"
    builder.build_synthetic_image_dataset(
        n_samples=4,
        seed=int(builder.BUILD_DEFAULT_SEED),
        output_dir=str(out),
        device="auto",
    )
    manifest_path = out / "manifest.json"
    assert manifest_path.is_file(), f"manifest missing: {manifest_path}"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_keys = {
        "schema", "oracle", "n_samples", "seed", "image_height", "image_width",
        "shape_names", "color_names", "inception_weights", "feature_dim",
        "ref_n_samples", "mu_mean_abs", "sigma_diag_mean", "wall_clock_s",
        "png_dir", "labels_csv", "reference_stats_npz",
    }
    assert set(payload.keys()) >= expected_keys
    assert payload["schema"] == "synthetic_image_dataset_manifest.v1"
    assert payload["oracle"] == "GeometricShapeImageOracle"
    assert payload["n_samples"] == 4
    assert payload["feature_dim"] == 2048


def test_cli_writes_artifacts(
    builder: Any, tmp_path: Path,
) -> None:
    """Subprocess smoke against the CLI entry point.

    The script writes PNGs + ``labels.csv`` + ``manifest.json`` +
    ``inception_reference_stats.npz`` under ``--output-dir``. We
    invoke with a tiny ``--n-samples 2`` so the test stays under
    a few seconds on CPU.
    """
    out = tmp_path / "cli"
    proc = subprocess.run(
        [
            sys.executable,
            str(_BUILDER_PATH),
            "--n-samples", "2",
            "--seed", str(builder.BUILD_DEFAULT_SEED),
            "--output-dir", str(out),
            "--device", "cpu",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (
        f"CLI failed (rc={proc.returncode}); "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    assert (out / "images").is_dir()
    assert (out / "labels.csv").is_file()
    assert (out / "manifest.json").is_file()
    assert (out / "inception_reference_stats.npz").is_file()
    # Exactly 2 PNGs.
    png_paths = sorted((out / "images").glob("image_*.png"))
    assert len(png_paths) == 2
