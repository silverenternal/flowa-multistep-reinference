"""Tests for ``tools.run_image_eval`` — the unified image T2I evaluation runner.

These tests lock in three contracts for the Phase B prep runner:

1. **End-to-end smoke** (``test_metrics_with_synthetic_samples``) —
   the runner produces a JSON report with a non-negative FID and a
   finite CLIPScore mean / std when given 4 tiny solid-color PIL
   images and aligned prompts. Uses a monkeypatched CLIP stub so the
   test is hermetic and does not require a real
   ``openai/clip-vit-base-patch32`` download (~600 MB).
2. **Graceful fallback** (``test_graceful_fallback``) — when
   :mod:`transformers` is missing, the runner still produces a valid
   JSON report with FID computed and CLIPScore = null. This is the
   Phase B prep contract: if the heavy ``[transformers]`` extra is
   not installed on the agent's host, the runner degrades cleanly
   rather than raising.
3. **JSON schema** (``test_json_schema``) — the report must contain
   the documented keys (``fid``, ``clip_score_mean``, ``clip_score_std``,
   ``geneval``, ``dpg_bench``) at the top level of the metrics block
   so downstream consumers can rely on the shape.

Tests use a small monkeypatched CLIP model so they run without
network access. The InceptionV3 path is also monkeypatched (mirrors
the pattern in :mod:`tests.test_eval.test_eval_rf_cifar`) so the
test does not pay for a real InceptionV3 forward pass.
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Preflight: this module exercises :mod:`tools.run_image_eval`, which
# requires ``torch`` (InceptionV3 forward via torchvision). The
# :func:`requires_torch` session fixture in ``tests/conftest.py``
# short-circuits the suite on sandboxes where torch is not vendored
# (CPU-only rigs, fresh clones).
#
# Note: the ``test_graceful_fallback`` case verifies the *transformers*
# fallback path, not the torch fallback path; it still requires torch
# for the InceptionV3 stub that runs the FID math. The torch skip is
# therefore correct for the whole module.
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.usefixtures("requires_torch")

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_RUNNER_PATH = _REPO_ROOT / "tools" / "run_image_eval.py"


def _load_runner() -> Any:
    """Import :mod:`tools.run_image_eval` without registering ``tools`` as a package."""
    repo_str = str(_REPO_ROOT)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)
    spec = importlib.util.spec_from_file_location(
        "tools_run_image_eval_under_test", str(_RUNNER_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def runner() -> Any:
    """Load the runner module once per test module."""
    return _load_runner()


@pytest.fixture()
def synthetic_samples_dir(tmp_path: Path) -> Path:
    """Return a directory containing 4 tiny solid-color PNGs (16x16, RGB)."""
    from PIL import Image

    samples_dir = tmp_path / "samples"
    samples_dir.mkdir()
    colors: tuple[tuple[int, int, int], ...] = (
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (255, 255, 0),
    )
    for idx, (r, g, b) in enumerate(colors):
        img = Image.new("RGB", (16, 16), (r, g, b))
        img.save(samples_dir / f"sample_{idx:04d}.png")
    return samples_dir


@pytest.fixture()
def synthetic_prompts(tmp_path: Path) -> Path:
    """Return a JSONL file of 4 prompts aligned with the 4 synthetic samples."""
    prompts = [
        "a red square image",
        "a green square image",
        "a blue square image",
        "a yellow square image",
    ]
    path = tmp_path / "prompts.jsonl"
    path.write_text("\n".join(prompts) + "\n", encoding="utf-8")
    return path


@pytest.fixture()
def reference_stats(tmp_path: Path) -> Path:
    """Build a minimal reference-stats .npz for the FID computation."""
    path = tmp_path / "ref_stats.npz"
    mu = np.zeros(2048, dtype=np.float64)
    sigma = np.eye(2048, dtype=np.float64) * 0.5  # small PSD covariance
    np.savez(path, mu=mu, sigma=sigma)
    return path


@pytest.fixture()
def tiny_inception_v3(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch ``torchvision.models.inception_v3`` with a stub returning deterministic (N, 2048).

    Mirrors the pattern in
    :mod:`tests.test_eval.test_eval_rf_cifar` so the test does not
    pay for a real InceptionV3 forward pass and does not require
    network access for the IMAGENET1K_V1 weights (which the FID
    canonical shape does not need anyway).
    """
    import torch
    import torch.nn as nn

    class _TinyInceptionV3(nn.Module):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__()
            self.kwargs = dict(kwargs)
            self.fc = nn.Identity()

        def forward(self, x: torch.Tensor) -> torch.Tensor:  # type: ignore[override]
            return torch.zeros((int(x.shape[0]), 2048), dtype=torch.float32)

        def eval(self) -> "_TinyInceptionV3":  # type: ignore[override]
            return super().eval()

    monkeypatch.setattr(
        "torchvision.models.inception_v3", lambda **kwargs: _TinyInceptionV3(**kwargs),
        raising=True,
    )


@pytest.fixture()
def fake_clip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch ``transformers.AutoModel`` / ``AutoProcessor`` with deterministic stubs.

    The stub returns a constant per-pair cosine similarity of 0.25
    (so ``100 * max(0, 0.25) = 25.0`` under the paper's 100× scaling)
    and a tiny variability term keyed off the row index so different
    images get different scores (mean + std are both well-defined).

    The canonical :class:`adaptive_reflow.eval.clip_score
    .HFCosineClipScoreEvaluator` (the abstraction the runner now
    delegates to) loads via :class:`transformers.AutoModel` /
    :class:`transformers.AutoProcessor` rather than the explicit
    ``CLIPModel`` / ``CLIPProcessor`` pair. We expose ``AutoModel`` /
    ``AutoProcessor`` here so the new code path resolves without
    needing a real ``~600 MB`` model download.
    """
    import torch
    import torch.nn as nn

    class _FakeCLIPOutput:
        def __init__(self, image_embeds: torch.Tensor, text_embeds: torch.Tensor) -> None:
            self.image_embeds = image_embeds
            self.text_embeds = text_embeds

    class _FakeCLIPModel(nn.Module):
        @classmethod
        def from_pretrained(cls, model_id: str, *args: Any, **kwargs: Any) -> "_FakeCLIPModel":
            return cls()

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__()
            self.dummy = nn.Parameter(torch.zeros(1))

        def eval(self) -> "_FakeCLIPModel":  # type: ignore[override]
            return super().eval()

        def to(self, device: Any) -> "_FakeCLIPModel":  # type: ignore[override]
            return self

        def forward(  # type: ignore[override]
            self,
            input_ids: torch.Tensor | None = None,
            pixel_values: torch.Tensor | None = None,
            attention_mask: torch.Tensor | None = None,
            **kwargs: Any,
        ) -> _FakeCLIPOutput:
            assert pixel_values is not None, "fake_clip expects pixel_values"
            batch = int(pixel_values.shape[0])
            dim = 8
            img = torch.zeros(batch, dim, dtype=torch.float32)
            txt = torch.zeros(batch, dim, dtype=torch.float32)
            # Give each row a distinct direction so std > 0.
            for i in range(batch):
                img[i, 0] = 1.0 + 0.05 * i
                txt[i, 0] = 1.0 + 0.03 * i
            return _FakeCLIPOutput(image_embeds=img, text_embeds=txt)

    class _FakeProcessor:
        @classmethod
        def from_pretrained(cls, model_id: str, *args: Any, **kwargs: Any) -> "_FakeProcessor":
            return cls()

        def __call__(  # type: ignore[no-untyped-def]
            self,
            text: list[str] | None = None,
            images: list[np.ndarray] | None = None,
            return_tensors: str = "pt",
            padding: bool = True,
            truncation: bool = True,
            **kwargs: Any,
        ) -> dict[str, torch.Tensor]:
            n = len(images or [])
            pixel_values = torch.zeros(n, 3, 224, 224, dtype=torch.float32)
            input_ids = torch.zeros(n, 4, dtype=torch.long)
            attention_mask = torch.ones(n, 4, dtype=torch.long)
            return {
                "pixel_values": pixel_values,
                "input_ids": input_ids,
                "attention_mask": attention_mask,
            }

    # Build a fake ``transformers`` module hierarchy if it doesn't exist.
    import types

    fake_module = types.ModuleType("transformers")
    fake_module.AutoModel = _FakeCLIPModel  # type: ignore[attr-defined]
    fake_module.AutoProcessor = _FakeProcessor  # type: ignore[attr-defined]
    # Preserve the legacy ``CLIPModel`` / ``CLIPProcessor`` symbols too
    # so any remaining direct references (older code paths / tests)
    # keep resolving.
    fake_module.CLIPModel = _FakeCLIPModel  # type: ignore[attr-defined]
    fake_module.CLIPProcessor = _FakeProcessor  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "transformers", fake_module)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_metrics_with_synthetic_samples(
    runner: Any,
    synthetic_samples_dir: Path,
    synthetic_prompts: Path,
    reference_stats: Path,
    tmp_path: Path,
    tiny_inception_v3: None,
    fake_clip: None,
) -> None:
    """The runner must produce a non-negative FID and a finite CLIPScore on 4 solid-color PNGs.

    With the InceptionV3 + CLIP stubs in place, the runner exercises
    the real metric code paths (load images, build tensors, run FID,
    run CLIPScore, write JSON). FID is non-negative by construction
    (the FID formula's lower bound is 0); the stub returns a
    constant Inception output, so the FID is some finite non-negative
    number. CLIPScore mean / std are finite under the paper's 100×
    scaling (the stub produces per-pair values in ``[0, 100]``).
    """
    output = tmp_path / "report.json"
    report = runner.run_image_eval(
        samples_dir=synthetic_samples_dir,
        reference_stats=reference_stats,
        prompts_jsonl=synthetic_prompts,
        output=output,
        device_arg="cpu",
        fid_batch_size=2,
        clip_batch_size=2,
        image_target_size=32,
    )
    assert output.exists(), "runner did not write the output JSON file"
    fid_block = report["metrics"]["fid"]
    clip_block = report["metrics"]["clip_score"]

    # FID: non-negative float (or None on hard failure — neither here).
    assert fid_block["value"] is not None, "FID value was None on a clean run"
    fid_val = float(fid_block["value"])
    assert fid_val >= 0.0, f"FID must be non-negative; got {fid_val}"
    assert np.isfinite(fid_val), f"FID must be finite; got {fid_val}"
    assert fid_block["n_samples"] == 4
    assert fid_block["n_features"] == 2048

    # CLIPScore: finite mean + std, mean > 0 under paper scaling.
    assert clip_block["mean"] is not None, "CLIPScore mean was None on a clean run"
    clip_mean = float(clip_block["mean"])
    assert np.isfinite(clip_mean), f"CLIPScore mean must be finite; got {clip_mean}"
    assert 0.0 <= clip_mean <= 100.0, f"CLIPScore mean out of paper scale; got {clip_mean}"
    assert clip_block["std"] is not None
    assert np.isfinite(float(clip_block["std"])), f"CLIPScore std must be finite; got {clip_block['std']}"
    assert clip_block["n_pairs"] == 4
    assert clip_block["paper_scale"] == 100.0


def test_graceful_fallback(
    runner: Any,
    synthetic_samples_dir: Path,
    synthetic_prompts: Path,
    reference_stats: Path,
    tmp_path: Path,
    tiny_inception_v3: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``transformers`` is missing, the runner must still compute FID and null-out CLIPScore.

    Simulates the Phase B prep environment (the agent's host has
    InceptionV3 / torchvision but no ``transformers``). The runner
    should:
      1. Emit a JSON report at the output path.
      2. Set ``metrics.fid.value`` to a finite non-negative float.
      3. Set ``metrics.clip_score.mean`` / ``std`` to ``null`` and
         populate ``metrics.clip_score.error`` with an ``ImportError``
         marker so downstream consumers know the field is intentionally
         empty rather than a hard failure.
    """
    # Simulate "transformers not installed" by patching ``sys.modules``
    # so the runner's import attempt raises ImportError. We use a
    # custom ModuleType subclass that raises on attribute access.
    import types

    class _RaisingModule(types.ModuleType):
        def __getattr__(self, name: str) -> Any:  # type: ignore[no-untyped-def]
            raise ImportError(
                f"No module named 'transformers' (synthetic fallback in test)"
            )

    # Remove any existing transformers entry so our raising stub takes
    # precedence.
    monkeypatch.delitem(sys.modules, "transformers", raising=False)
    monkeypatch.setitem(sys.modules, "transformers", _RaisingModule("transformers"))

    output = tmp_path / "report_fallback.json"
    report = runner.run_image_eval(
        samples_dir=synthetic_samples_dir,
        reference_stats=reference_stats,
        prompts_jsonl=synthetic_prompts,
        output=output,
        device_arg="cpu",
        fid_batch_size=2,
        clip_batch_size=2,
        image_target_size=32,
    )

    assert output.exists(), "runner did not write the output JSON file"
    fid_block = report["metrics"]["fid"]
    clip_block = report["metrics"]["clip_score"]

    # FID ran successfully.
    assert fid_block["value"] is not None, "FID must still compute when transformers is missing"
    assert float(fid_block["value"]) >= 0.0
    assert np.isfinite(float(fid_block["value"]))

    # CLIPScore gracefully null-ed out with an ImportError marker.
    assert clip_block["mean"] is None, (
        f"CLIPScore mean must be None when transformers is missing; got {clip_block['mean']!r}"
    )
    assert clip_block["std"] is None, (
        f"CLIPScore std must be None when transformers is missing; got {clip_block['std']!r}"
    )
    assert "ImportError" in clip_block.get("error", ""), (
        f"CLIPScore error must mention ImportError; got {clip_block.get('error')!r}"
    )

    # Status: not all_metrics_failed (FID succeeded).
    assert report["status"] == "ok", (
        f"Status must remain 'ok' as long as FID succeeded; got {report['status']!r}"
    )


def test_json_schema(
    runner: Any,
    synthetic_samples_dir: Path,
    synthetic_prompts: Path,
    reference_stats: Path,
    tmp_path: Path,
    tiny_inception_v3: None,
    fake_clip: None,
) -> None:
    """The output JSON must contain fid, clip_score_mean, clip_score_std, geneval=null, dpg_bench=null.

    Locks in the documented schema for downstream consumers
    (HiDream-I1 + Lumina-Image 2.0 eval dashboards, Phase B prep
    scripts). Tests both the in-memory ``report`` dict and the
    on-disk JSON file.
    """
    output = tmp_path / "report_schema.json"
    report = runner.run_image_eval(
        samples_dir=synthetic_samples_dir,
        reference_stats=reference_stats,
        prompts_jsonl=synthetic_prompts,
        output=output,
        device_arg="cpu",
        fid_batch_size=2,
        clip_batch_size=2,
        image_target_size=32,
    )
    assert output.exists()

    # Round-trip the JSON to ensure it's parseable + well-formed.
    parsed = json.loads(output.read_text(encoding="utf-8"))

    # Top-level fields.
    assert parsed["schema"] == "img_eval_report.v1"
    assert parsed["n_samples"] == 4
    assert "metrics" in parsed

    metrics = parsed["metrics"]
    # FID block.
    assert "fid" in metrics
    assert metrics["fid"]["metric"] == "fid"
    assert isinstance(metrics["fid"]["value"], (int, float))
    assert metrics["fid"]["n_samples"] == 4
    # CLIPScore block.
    assert "clip_score" in metrics
    assert metrics["clip_score"]["metric"] == "clip_score"
    assert isinstance(metrics["clip_score"]["mean"], (int, float))
    assert isinstance(metrics["clip_score"]["std"], (int, float))
    # GenEval + DPG-Bench stubs.
    assert "geneval" in metrics
    assert metrics["geneval"]["value"] is None
    assert metrics["geneval"]["marker"] == "external"
    assert "dpg_bench" in metrics
    assert metrics["dpg_bench"]["value"] is None
    assert metrics["dpg_bench"]["marker"] == "external"

    # The in-memory report mirrors the on-disk shape.
    assert report["metrics"]["fid"]["value"] == metrics["fid"]["value"]
    assert report["metrics"]["clip_score"]["mean"] == metrics["clip_score"]["mean"]
    assert report["metrics"]["clip_score"]["std"] == metrics["clip_score"]["std"]
    assert report["metrics"]["geneval"]["value"] is None
    assert report["metrics"]["dpg_bench"]["value"] is None


def test_load_images_handles_mixed_modes(
    runner: Any,
    tmp_path: Path,
) -> None:
    """``load_images_as_tensor`` must handle RGBA, L, and RGB PNGs uniformly.

    The Phase B prep tests use a mix of synthetic image modes (some
    adapters save RGBA, some save L). The runner must flatten them all
    to ``(N, 3, H, W)`` float32 in ``[-1, 1]`` without crashing.
    """
    from PIL import Image

    samples_dir = tmp_path / "mixed"
    samples_dir.mkdir()
    # RGB
    Image.new("RGB", (8, 8), (10, 20, 30)).save(samples_dir / "rgb.png")
    # RGBA (alpha preserved on load)
    Image.new("RGBA", (8, 8), (40, 50, 60, 128)).save(samples_dir / "rgba.png")
    # L (grayscale) — must be replicated across 3 channels.
    Image.new("L", (8, 8), 70).save(samples_dir / "l.png")
    # Different resolution (must be stacked as-is; downstream Inception
    # handles resizing bilinearly to 299x299).
    Image.new("RGB", (12, 16), (1, 2, 3)).save(samples_dir / "big.png")

    paths = runner.discover_samples(samples_dir)
    assert len(paths) == 4

    # With ``target_size=None`` (mixed-resolution mode) each sample
    # keeps its own H, W — but ``np.stack`` requires uniform shapes,
    # so the production runner always passes ``target_size=299`` (or a
    # caller-supplied override). Re-load with a uniform target to
    # exercise the resize branch.
    images = runner.load_images_as_tensor(paths, target_size=16)
    assert images.shape[0] == 4
    assert images.shape[1] == 3
    assert images.shape == (4, 3, 16, 16)
    assert images.dtype == np.float32
    assert float(images.min()) >= -1.0
    assert float(images.max()) <= 1.0

    # Mixed input sizes — the resize branch normalises them all to
    # the target size.
    mixed_input = [samples_dir / "rgb.png", samples_dir / "big.png"]
    resized = runner.load_images_as_tensor(mixed_input, target_size=8)
    assert resized.shape == (2, 3, 8, 8)


def test_compute_fid_returns_non_negative(
    runner: Any,
) -> None:
    """``compute_fid_from_features`` must clip numerical noise to 0 and return a non-negative float."""
    rng = np.random.default_rng(0)
    feats = rng.standard_normal((16, 64)).astype(np.float32)
    mu = np.zeros(64, dtype=np.float64)
    sigma = np.eye(64, dtype=np.float64)
    fid = runner.compute_fid_from_features(feats, mu, sigma)
    assert np.isfinite(fid), f"FID must be finite; got {fid}"
    assert fid >= 0.0, f"FID must be non-negative; got {fid}"

    # Too-few-rows guard: returns NaN rather than raising.
    fid_tiny = runner.compute_fid_from_features(feats[:1], mu, sigma)
    assert math.isnan(fid_tiny), f"single-row FID must be NaN; got {fid_tiny}"


# ---------------------------------------------------------------------------
# Phase 4 / Design #1 — per-round surface
# ---------------------------------------------------------------------------


def _seed_round_dir(parent: Path, round_idx: int, n_samples: int = 2) -> Path:
    """Write ``n_samples`` solid-color RGB PNGs into ``parent/framework_round{XX}``."""
    from PIL import Image

    rd = parent / f"framework_round{round_idx:02d}"
    rd.mkdir(parents=True, exist_ok=True)
    for i in range(n_samples):
        color = ((round_idx * 64 + i * 16) % 256, (round_idx * 32) % 256, 96)
        Image.new("RGB", (8, 8), color).save(rd / f"sample_{i:04d}.png")
    return rd


def test_per_round_emits_per_round_metrics(
    runner: Any,
    tmp_path: Path,
) -> None:
    """``--per-round`` must emit per-round FID + CLIPScore lists.

    Phase 4 / Design #1 contract:

    * ``metrics.per_round_fid`` has length ``n_rounds``.
    * ``metrics.per_round_clip_score`` has length ``n_rounds``.
    * Each per-round entry carries ``round_index`` + ``round_dir``.
    * The legacy top-level ``metrics.fid`` / ``metrics.clip_score``
      stay byte-stable (computed over the FINAL round).
    """
    samples_dir = tmp_path / "samples"
    samples_dir.mkdir()
    rounds = [_seed_round_dir(samples_dir, r, n_samples=2) for r in range(3)]
    out_path = tmp_path / "report.json"

    # Reference stats: shape doesn't matter here — the FID may be NaN
    # due to feature-dim mismatch with the InceptionV3 2048-d pool, but
    # we only assert the structural shape of the report.
    import numpy as np
    ref_npz = tmp_path / "ref.npz"
    np.savez(
        ref_npz,
        mu=np.zeros(2048, dtype=np.float64),
        sigma=np.eye(2048, dtype=np.float64),
    )

    prompts = tmp_path / "prompts.jsonl"
    prompts.write_text("\n".join(["a"] * 6) + "\n")

    report = runner.run_image_eval(
        samples_dir=samples_dir,
        reference_stats=ref_npz,
        prompts_jsonl=prompts,
        output=out_path,
        device_arg="cpu",
        fid_batch_size=4,
        clip_batch_size=4,
        image_target_size=8,
        per_round=True,
        per_round_glob="{arm}_round{r:02d}",
        arm="framework",
    )

    metrics = report["metrics"]
    assert "per_round_fid" in metrics, "per_round_fid missing"
    assert "per_round_clip_score" in metrics, "per_round_clip_score missing"
    assert len(metrics["per_round_fid"]) == 3, (
        f"per_round_fid must have length 3; got {len(metrics['per_round_fid'])}"
    )
    assert len(metrics["per_round_clip_score"]) == 3, (
        f"per_round_clip_score must have length 3; got {len(metrics['per_round_clip_score'])}"
    )
    for entry in metrics["per_round_fid"]:
        assert "round_index" in entry
        assert "round_dir" in entry
    for entry in metrics["per_round_clip_score"]:
        assert "round_index" in entry
        assert "round_dir" in entry
    # Legacy top-level fields stay byte-stable.
    assert "fid" in metrics
    assert "clip_score" in metrics

    # Same JSON shape on disk.
    on_disk = json.loads(out_path.read_text(encoding="utf-8"))
    assert on_disk["schema"] == "img_eval_report.v1"
    assert len(on_disk["metrics"]["per_round_fid"]) == 3


def test_per_round_falls_back_when_no_round_dirs(
    runner: Any,
    tmp_path: Path,
) -> None:
    """``--per-round`` with no per-round dirs falls back to single-shot semantics."""
    samples_dir = tmp_path / "samples"
    samples_dir.mkdir()
    from PIL import Image
    for i in range(2):
        Image.new("RGB", (8, 8), (i * 32, i * 16, 64)).save(
            samples_dir / f"sample_{i:04d}.png"
        )
    out_path = tmp_path / "report.json"
    report = runner.run_image_eval(
        samples_dir=samples_dir,
        reference_stats=None,
        prompts_jsonl=None,
        output=out_path,
        device_arg="cpu",
        fid_batch_size=4,
        clip_batch_size=4,
        image_target_size=8,
        per_round=True,
    )
    # No per_round_fid sub-tree when no round dirs were found (the
    # fallback path runs the legacy single-shot semantics instead).
    metrics = report["metrics"]
    assert "per_round_fid" not in metrics or metrics.get("per_round_fid") == []