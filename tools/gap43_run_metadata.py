#!/usr/bin/env python3
"""GAP-43 — run-metadata recorder (pre-registration §9.4).

Writes the provenance record that the pre-registered analysis depends on:
git SHA + cleanliness, the pre-registration blob hash, the exact command,
the seed list, the Python/torch/CUDA/flowmol/PoseBusters/RDKit versions,
the checkpoint md5, the PoseBusters YAML sha256, the GPU name/driver, and
the start/end UTC timestamps.

Run it with the same interpreter as the sweep so the version fields are
the ones that produced the numbers::

    .venvs/flowmol3_venv/bin/python tools/gap43_run_metadata.py \
        --output-dir verification_outputs/gap43-blend-positive/primary \
        --command "<the exact sweep command>" \
        --seeds 55,65,...,545 \
        --start 2026-10-19T00:00:00Z --end 2026-10-19T06:00:00Z
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT = REPO_ROOT / "data" / "flowmol3" / "weights_real" / "checkpoints" / "last.ckpt"
PB_CONFIG = REPO_ROOT / "tools" / "pb_config_with_energy_ratio.yaml"
PREREG = REPO_ROOT / "docs" / "audit" / "gap43-blend-positive-preregistration.md"


def _run(cmd: list[str]) -> str:
    try:
        out = subprocess.run(
            cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False, timeout=60
        )
        return (out.stdout or out.stderr).strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _md5(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.md5()  # noqa: S324 - matches the upstream checkpoint checksum
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _versions() -> dict[str, str | None]:
    out: dict[str, str | None] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }
    for name in ("torch", "flowmol", "flowmol3", "posebusters", "rdkit"):
        try:
            module = __import__(name)
            out[name] = str(getattr(module, "__version__", "unknown"))
        except Exception:  # noqa: BLE001 - version probing must never fail the recorder
            out[name] = None
    out["upstream_flowmol3_git_sha"] = _run(
        ["git", "-C", str(REPO_ROOT / "data" / "FlowMol3"), "rev-parse", "HEAD"]
    ) or None
    try:
        import torch

        out["torch_cuda"] = str(torch.version.cuda)
        out["cuda_available"] = str(torch.cuda.is_available())
        if torch.cuda.is_available():
            out["gpu_name"] = torch.cuda.get_device_name(0)
    except Exception:  # noqa: BLE001
        out["torch_cuda"] = None
    driver = _run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"])
    out["nvidia_driver"] = ", ".join(dict.fromkeys(driver.splitlines())) or None
    return out


def collect(command: str, seeds: list[int], start: str, end: str) -> dict:
    return {
        "kind": "gap43_run_metadata",
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "git_sha": _run(["git", "rev-parse", "HEAD"]),
        "git_status_porcelain": _run(["git", "status", "--porcelain"]),
        "prereg_path": str(PREREG.relative_to(REPO_ROOT)),
        "prereg_blob_hash": _run(["git", "hash-object", str(PREREG)]),
        "prereg_sha256": _sha256(PREREG),
        "command": command,
        "seeds": seeds,
        "n_seeds": len(seeds),
        "device": "cuda:0",
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "start_utc": start,
        "end_utc": end,
        "checkpoint": str(CHECKPOINT.relative_to(REPO_ROOT)),
        "checkpoint_md5": _md5(CHECKPOINT),
        "pb_config": str(PB_CONFIG.relative_to(REPO_ROOT)),
        "pb_config_sha256": _sha256(PB_CONFIG),
        "versions": _versions(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--command", required=True)
    ap.add_argument("--seeds", required=True, help="comma-separated seed list")
    ap.add_argument("--start", required=True, help="UTC start, ISO-8601")
    ap.add_argument("--end", required=True, help="UTC end, ISO-8601")
    args = ap.parse_args()

    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]
    doc = collect(args.command, seeds, args.start, args.end)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out = args.output_dir / "run_metadata.json"
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"[gap43] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
