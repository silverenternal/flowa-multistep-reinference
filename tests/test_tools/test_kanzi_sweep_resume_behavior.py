"""Interruption recovery must preserve records and avoid selection on failures."""
import json
from types import SimpleNamespace

import pytest

torch = pytest.importorskip("torch")

from tools import _kanzi_sweep_runner as runner


@pytest.fixture
def sweep(tmp_path, monkeypatch):
    runner._ensure_sys_path()
    import kanzi

    calls = {"encode": 0, "decode": 0, "fail_decode": 2}

    class DAE(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.parameter = torch.nn.Parameter(torch.zeros(1))
            self.quantize = SimpleNamespace(codebook_size=1000,
                                           project_out=SimpleNamespace(weight=torch.zeros(512, 4)))

        @classmethod
        def from_pretrained(cls, path):
            return cls()

        def encode(self, coords, preprocess=False):
            calls["encode"] += 1
            return (torch.arange(coords.shape[1]).reshape(1, -1),)

        def decode(self, codes, n_steps=100):
            calls["decode"] += 1
            if calls["decode"] == calls["fail_decode"]:
                raise RuntimeError("injected interruption during reconstruction")
            return torch.zeros(1, codes.shape[1], 3)

    monkeypatch.setattr(kanzi, "DAE", DAE)
    monkeypatch.setattr(kanzi, "kabsch_rmsd", lambda a, b: torch.sqrt(torch.mean((a-b)**2)))
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    source = tmp_path / "coords.txt"
    source.write_text("0,0,0,1,1,1\n0,0,0,2,2,2\n0,0,0,3,3,3\n")
    checkpoint = tmp_path / "model.pt"
    checkpoint.write_bytes(b"stand-in weights")
    kwargs = dict(mode="baseline", seed=42, max_records=3, nfe_steps=10,
                  input_path=source, ckpt_path=checkpoint)
    return calls, kwargs


def test_resume_fills_failed_record_without_rerunning_successes(tmp_path, sweep):
    calls, kwargs = sweep
    out = tmp_path / "interrupted"
    with pytest.raises(RuntimeError, match="incomplete"):
        runner.run_kanzi_sweep(**kwargs, output_dir=str(out))
    assert calls["encode"] == 3
    assert [r["index"] for r in json.loads((out / "checkpoint.json").read_text())["records"]] == [0, 2]
    assert not (out / "kanzi_n1000_paper_metrics.json").exists()
    runner.run_kanzi_sweep(**kwargs, output_dir=str(out), resume=True)
    assert calls["encode"] == 4
    resumed = json.loads((out / "kanzi_n1000_paper_metrics.json").read_text())
    assert resumed["sweep_n_records_actual"] == 3
    assert resumed["resumed_records"] == 2
    assert resumed["n_records_skipped"] == 0
    clean = tmp_path / "uninterrupted"
    runner.run_kanzi_sweep(**kwargs, output_dir=str(clean))
    expected = json.loads((clean / "kanzi_n1000_paper_metrics.json").read_text())
    assert resumed["per_seq_rmsd_A"] == expected["per_seq_rmsd_A"]
    assert resumed["codebook_metrics"] == expected["codebook_metrics"]


def test_limit_caps_attempts_including_failures(tmp_path, sweep):
    calls, kwargs = sweep
    kwargs["max_records"] = 2
    with pytest.raises(RuntimeError, match="incomplete"):
        runner.run_kanzi_sweep(**kwargs, output_dir=str(tmp_path / "limited"))
    assert calls["encode"] == 2
