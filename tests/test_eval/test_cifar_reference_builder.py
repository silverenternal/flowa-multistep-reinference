"""Reference extraction validates inputs and publishes only complete features."""
import json

import numpy as np
import pytest

from tools import eval_rf_cifar as cli


def test_reference_cli_extracts_features_without_sampling(tmp_path, monkeypatch):
    source = tmp_path / "images.npz"
    output = tmp_path / "features.npz"
    images = np.zeros((3, 3, 32, 32), dtype=np.float32)
    np.savez(source, samples=images)
    calls = []

    def extract(samples, *, device, batch_size):
        calls.append((samples.shape, device, batch_size))
        return np.ones((len(samples), 2048), dtype=np.float32)

    monkeypatch.setattr(cli.tools_run_image_eval, "extract_inception_features_for_image_eval", extract)
    monkeypatch.setattr(cli, "run_baseline", lambda **kw: pytest.fail("unexpected sampling"))
    assert cli.main([
        "--extract-reference-features", "--reference-samples", str(source),
        "--reference-features", str(output), "--feature-device", "cuda:0", "--batch-size", "2",
    ]) == 0
    assert calls == [((3, 3, 32, 32), "cuda:0", 2)]
    with np.load(output, allow_pickle=False) as data:
        assert data["features"].shape == (3, 2048)
        metadata = json.loads(data["metadata"].item())
    assert len(metadata["source_sha256"]) == 64
    assert metadata["sample_count"] == 3
    assert metadata["published_tf_fid_comparable"] is False
    with pytest.raises(FileExistsError):
        cli.build_reference_features(source, output)


@pytest.mark.parametrize("kind", ["one", "uint8", "nan", "range", "shape", "key"])
def test_invalid_images_rejected_before_extraction(tmp_path, monkeypatch, kind):
    images = np.zeros((2, 3, 32, 32), dtype=np.float32)
    if kind == "one":
        images = images[:1]
    elif kind == "uint8":
        images = images.astype(np.uint8)
    elif kind == "nan":
        images[0, 0, 0, 0] = np.nan
    elif kind == "range":
        images[0, 0, 0, 0] = 2
    elif kind == "shape":
        images = images[:, :1]
    source, output = tmp_path / "images.npz", tmp_path / "features.npz"
    np.savez(source, **{("features" if kind == "key" else "samples"): images})
    monkeypatch.setattr(cli.tools_run_image_eval, "extract_inception_features_for_image_eval",
                        lambda *a, **kw: pytest.fail("invalid input reached extractor"))
    with pytest.raises(ValueError):
        cli.build_reference_features(source, output)
    assert not output.exists()


@pytest.mark.parametrize("failure", ["exception", "nan", "shape"])
def test_failed_extraction_never_publishes_partial_reference(tmp_path, monkeypatch, failure):
    source, output = tmp_path / "images.npz", tmp_path / "features.npz"
    np.savez(source, samples=np.zeros((2, 3, 32, 32), dtype=np.float32))

    def extract(*args, **kwargs):
        if failure == "exception":
            raise RuntimeError("model unavailable")
        if failure == "nan":
            return np.full((2, 2048), np.nan)
        return np.zeros((1, 2048))

    monkeypatch.setattr(cli.tools_run_image_eval, "extract_inception_features_for_image_eval", extract)
    with pytest.raises((RuntimeError, ValueError)):
        cli.build_reference_features(source, output)
    assert not output.exists()
