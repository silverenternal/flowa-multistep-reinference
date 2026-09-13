import json

import pytest

from tools._kanzi_checkpoint import SweepCheckpoint


def test_records_survive_interruption_and_protocol_change_is_rejected(tmp_path):
    path = tmp_path / "checkpoint.json"
    checkpoint = SweepCheckpoint(path, {"input_sha256": "abc", "seed": 42}, resume=False)
    checkpoint.add(0, 0.75, [0, 3, 9])
    recovered = SweepCheckpoint(path, checkpoint.protocol, resume=True)
    assert recovered.records[0] == {"index": 0, "rmsd_A": 0.75, "codebook_indices": [0, 3, 9]}
    with pytest.raises(ValueError, match="mismatch"):
        SweepCheckpoint(path, {"input_sha256": "different", "seed": 42}, resume=True)
    with pytest.raises(FileExistsError):
        SweepCheckpoint(path, checkpoint.protocol, resume=False)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -0.1])
def test_invalid_result_is_not_checkpointed(tmp_path, bad):
    path = tmp_path / "checkpoint.json"
    checkpoint = SweepCheckpoint(path, {}, resume=False)
    with pytest.raises(ValueError, match="RMSD"):
        checkpoint.add(0, bad, [1, 2])
    assert json.loads(path.read_text())["records"] == []


def test_invalid_checkpoint_is_rejected(tmp_path):
    path = tmp_path / "checkpoint.json"
    checkpoint = SweepCheckpoint(path, {}, resume=False)
    checkpoint.add(0, 0.75, [1, 2])
    payload = json.loads(path.read_text())
    payload["records"][0]["codebook_indices"] = [-1]
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="codebook indices"):
        SweepCheckpoint(path, {}, resume=True)


def test_resume_requires_a_checkpoint(tmp_path):
    with pytest.raises(FileNotFoundError):
        SweepCheckpoint(tmp_path / "missing.json", {}, resume=True)
