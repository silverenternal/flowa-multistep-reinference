"""Atomic, validated per-record recovery for Kanzi sweeps."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any


def file_sha256(path: Path) -> str:
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def _validate_record(record: dict[str, Any]) -> None:
    if set(record) != {"index", "rmsd_A", "codebook_indices"}:
        raise ValueError("invalid Kanzi checkpoint record schema")
    index, rmsd, codes = record["index"], record["rmsd_A"], record["codebook_indices"]
    if type(index) is not int or index < 0:
        raise ValueError("invalid Kanzi checkpoint record index")
    if type(rmsd) not in (float, int) or not math.isfinite(rmsd) or rmsd < 0:
        raise ValueError("invalid Kanzi checkpoint RMSD")
    if not isinstance(codes, list) or not codes or any(type(c) is not int or c < 0 for c in codes):
        raise ValueError("invalid Kanzi checkpoint codebook indices")


class SweepCheckpoint:
    """Recover only records with the same inputs, code and execution protocol."""

    def __init__(self, path: Path, protocol: dict[str, Any], *, resume: bool):
        self.path = path
        self.protocol = protocol
        self.records: dict[int, dict[str, Any]] = {}
        if path.exists():
            if not resume:
                raise FileExistsError(f"{path} exists; use --resume or a new output directory")
            payload = json.loads(path.read_text())
            if payload.get("schema") != "kanzi-sweep-checkpoint-v1" or payload.get("protocol") != protocol:
                raise ValueError("Kanzi checkpoint input, source or protocol mismatch")
            for record in payload["records"]:
                _validate_record(record)
                if record["index"] in self.records:
                    raise ValueError("duplicate Kanzi checkpoint record")
                self.records[record["index"]] = record
        elif resume:
            raise FileNotFoundError(f"no checkpoint to resume at {path}")
        else:
            self._write()

    def add(self, index: int, rmsd_A: float, codebook_indices: list[int]) -> None:
        record = {"index": index, "rmsd_A": rmsd_A, "codebook_indices": codebook_indices}
        _validate_record(record)
        if index in self.records:
            raise ValueError(f"Kanzi record {index} already checkpointed")
        self.records[index] = record
        self._write()

    def _write(self) -> None:
        payload = {"schema": "kanzi-sweep-checkpoint-v1", "protocol": self.protocol,
                   "records": [self.records[k] for k in sorted(self.records)]}
        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w") as fh:
            json.dump(payload, fh, allow_nan=False)
            fh.flush()
            os.fsync(fh.fileno())
        temporary.replace(self.path)
