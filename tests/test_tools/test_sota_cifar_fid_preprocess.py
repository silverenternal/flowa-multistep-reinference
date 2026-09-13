"""Check tensor inputs delivered to the TF-port extractor (no model download)."""
import numpy as np
import pytest

torch = pytest.importorskip("torch")
inception = pytest.importorskip("pytorch_fid.inception")
from tools import run_sota_cifar_experiment as cli


def test_tfport_receives_zero_one_images_with_its_own_preprocessing(monkeypatch):
    captured = []

    class FakeInception(torch.nn.Module):
        BLOCK_INDEX_BY_DIM = {2048: 3}

        def __init__(self, blocks):
            super().__init__()
            assert blocks == [3]

        def forward(self, x):
            captured.append(x.clone())
            return [torch.ones((len(x), 2048, 1, 1))]

    monkeypatch.setattr(inception, "InceptionV3", FakeInception)
    monkeypatch.setattr(cli, "compute_frechet_distance", lambda *a, **kw: 0.0)
    gen = np.linspace(-1, 1, 35*3*32*32).reshape(35, 3, 32, 32)
    ref = -gen
    assert cli._compute_fid_tfport_inline(gen, ref) == 0.0
    assert [len(x) for x in captured] == [32, 3, 32, 3]
    expected = torch.from_numpy((gen.astype(np.float32) + 1) / 2)
    torch.testing.assert_close(torch.cat(captured[:2]), expected)
    torch.testing.assert_close(torch.cat(captured[2:]), 1-expected)
