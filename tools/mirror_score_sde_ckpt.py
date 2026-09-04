#!/usr/bin/env python3
"""Download and prepare the Score-SDE / gnobitab RectifiedFlow CIFAR-10 checkpoint.

Background
----------

The framework's ``tools/run_sota_cifar_experiment.py`` requires the
published ``gnobitab`` "CIFAR10 1-Rectified Flow (FID=2.58)" checkpoint
to reproduce CLM-040's v4 matched-NFE baseline. The canonical download
path is Google Drive (file ID ``10aPF5KC30SjVwr6rOnNosStpSGXnELXn``,
990 MB) which is reachable from this sandbox via ``gdown``. This script:

1. Downloads the 990 MB raw checkpoint to ``data/rectified_flow_cifar10.pth``
2. Extracts the EMA-only ``shadow_params`` and re-pairs them with the
   ``state_dict`` keys (skipping the non-trainable ``module.sigmas``
   buffer) into ``data/cifar10_rf.pth`` (~247 MB clean EMA-only state-dict)

This mirrors the procedure documented in
``docs/r4-survey/13-weights-acquisition.md`` (Wave 14). The script is
idempotent: if ``data/cifar10_rf.pth`` already exists and matches the
expected SHA-256, it is reused. If the Google Drive download fails (no
network, drive blocked), the script exits non-zero with a clear message
pointing at the HF mirror option (which is also NOT available for this
checkpoint per the upstream ``gnobitab/RectifiedFlow`` README).

Usage::

    python tools/mirror_score_sde_ckpt.py

CLI flags:
  --force            re-download even if ``data/cifar10_rf.pth`` exists.
  --raw-only         download the 990 MB raw checkpoint but skip the EMA
                     extraction (used for testing the download path).
  --verify-only      verify ``data/cifar10_rf.pth`` against the expected
                     SHA-256 (no download).

Output:
- ``data/rectified_flow_cifar10.pth`` (990 MB; raw Gnobitab ckpt)
- ``data/cifar10_rf.pth`` (247 MB; clean EMA-only state_dict)

Exit codes:
  0  success (or verify-only finds expected hash)
  1  download failure
  2  EMA extraction failure
  3  verify-only hash mismatch
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_CKPT_PATH = REPO_ROOT / "data" / "rectified_flow_cifar10.pth"
CLEAN_CKPT_PATH = REPO_ROOT / "data" / "cifar10_rf.pth"

#: Google Drive file ID for the gnobitab "CIFAR10 1-Rectified Flow" ckpt
GOOGLE_DRIVE_FILE_ID = "10aPF5KC30SjVwr6rOnNosStpSGXnELXn"
#: Canonical source URL (for provenance)
GOOGLE_DRIVE_URL = (
    f"https://drive.google.com/file/d/{GOOGLE_DRIVE_FILE_ID}/view?usp=sharing"
)

#: SHA-256 of the EMA-only clean ckpt (data/cifar10_rf.pth); captured
#: 2026-09-05 from a gdown-fetched copy of the 990 MB raw ckpt
#: (file ID 10aPF5KC30SjVwr6rOnNosStpSGXnELXn, gnobitab "CIFAR10
#: 1-Rectified Flow (FID=2.58)"). The clean ckpt = EMA shadow_params
#: paired with the ``module.*`` trainable keys + the non-trainable
#: ``sigmas`` buffer; ``module.`` prefix stripped from all keys to
#: match the ``NCSNppDDPMpp`` topology the adapter loads via
#: ``load_gnobitab_rf_cifar_unet``. Re-verify on every regeneration;
#: reject the file if it drifts.
EXPECTED_CLEAN_SHA256 = (
    "c29936c219f34800131c07b81a8da4862b0c0b6f4e5e50efea267d24eef1f2ec"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256_file(path: Path, *, chunk_bytes: int = 1 << 20) -> str:
    """Stream-hash ``path`` and return the hex SHA-256."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_bytes)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _check_gdown() -> None:
    """Verify that ``gdown`` is importable from PATH or fall back to a venv.

    We don't install ``gdown`` into the project venv by default (it
    pulls in ``beautifulsoup4``); instead we expect the operator to run
    this script inside the Python 3.11 sidecar at
    ``/home/hugo/.venv-flowmol311`` (where ``gdown`` is preinstalled per
    Wave 15 F.2). If ``gdown`` isn't on PATH we raise.
    """
    if shutil.which("gdown") is None:
        print(
            "[mirror_score_sde_ckpt] ERROR: `gdown` not found on PATH. "
            "Install via `pip install gdown` or run this script inside "
            "/home/hugo/.venv-flowmol311 (the Wave 15 F.2 sidecar).",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)


def download_raw_ckpt() -> None:
    """Download the 990 MB raw checkpoint via gdown."""
    _check_gdown()
    print(
        f"[mirror_score_sde_ckpt] downloading {GOOGLE_DRIVE_URL} -> "
        f"{RAW_CKPT_PATH}",
        flush=True,
    )
    cmd = [
        "gdown",
        GOOGLE_DRIVE_FILE_ID,
        "-O",
        str(RAW_CKPT_PATH),
    ]
    rc = subprocess.call(cmd)
    if rc != 0:
        print(
            f"[mirror_score_sde_ckpt] gdown failed with exit code {rc}; "
            "check network policy and the upstream README",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)
    size_mb = RAW_CKPT_PATH.stat().st_size / (1024 * 1024)
    print(
        f"[mirror_score_sde_ckpt] downloaded {size_mb:.1f} MB raw ckpt",
        flush=True,
    )


def extract_ema_clean_ckpt() -> str:
    """Extract the EMA shadow_params into a clean ``state_dict`` and return the SHA-256."""
    import torch  # late import: only needed on the extraction path

    if not RAW_CKPT_PATH.exists():
        print(
            f"[mirror_score_sde_ckpt] ERROR: raw ckpt missing at {RAW_CKPT_PATH}",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(2)

    print(
        f"[mirror_score_sde_ckpt] extracting EMA shadow_params from "
        f"{RAW_CKPT_PATH} -> {CLEAN_CKPT_PATH}",
        flush=True,
    )
    try:
        ckpt: dict[str, Any] = torch.load(
            str(RAW_CKPT_PATH), map_location="cpu", weights_only=False
        )
    except Exception as exc:  # noqa: BLE001
        print(
            f"[mirror_score_sde_ckpt] ERROR: torch.load failed: {exc!r}",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(2)

    if "ema" not in ckpt or "model" not in ckpt:
        print(
            "[mirror_score_sde_ckpt] ERROR: ckpt missing 'ema' or 'model' key",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(2)

    ema = ckpt["ema"]
    model_state: dict[str, torch.Tensor] = ckpt["model"]
    shadow_params: list[torch.Tensor] = ema["shadow_params"]

    # Pair shadow_params with the ``module.*`` keys from the live model,
    # skipping the non-trainable ``module.sigmas`` buffer. Documented in
    # ``docs/r4-survey/13-weights-acquisition.md``.
    trainable_keys = [k for k in model_state.keys() if k != "module.sigmas"]
    if len(shadow_params) != len(trainable_keys):
        print(
            "[mirror_score_sde_ckpt] ERROR: shadow_params length "
            f"({len(shadow_params)}) != trainable_keys length "
            f"({len(trainable_keys)})",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(2)

    clean_state = dict(zip(trainable_keys, shadow_params))
    # Add the non-trainable ``sigmas`` buffer (NCSNpp log-schedule,
    # length 1000) so the adapter's ``NCSNppDDPMpp.load_state_dict``
    # call succeeds. Without this, ``load_state_dict(strict=True)`` raises
    # ``Missing key(s) in state_dict: 'sigmas'``.
    clean_state["sigmas"] = model_state["module.sigmas"]
    # Strip the ``module.`` prefix so the keys match the topology the
    # adapter rebuilds via ``_gnobitab_ddpmpp.load_gnobitab_rf_cifar_unet``.
    clean_state = {
        (k[7:] if k.startswith("module.") else k): v
        for k, v in clean_state.items()
    }
    CLEAN_CKPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save(clean_state, str(CLEAN_CKPT_PATH))

    sha = _sha256_file(CLEAN_CKPT_PATH)
    size_mb = CLEAN_CKPT_PATH.stat().st_size / (1024 * 1024)
    print(
        f"[mirror_score_sde_ckpt] wrote {size_mb:.1f} MB clean EMA-only "
        f"state_dict (sha256={sha})",
        flush=True,
    )
    return sha


def verify_clean_ckpt() -> bool:
    """Return True if ``data/cifar10_rf.pth`` matches the expected SHA-256."""
    if not CLEAN_CKPT_PATH.exists():
        print(
            f"[mirror_score_sde_ckpt] ERROR: {CLEAN_CKPT_PATH} does not exist",
            file=sys.stderr,
            flush=True,
        )
        return False
    sha = _sha256_file(CLEAN_CKPT_PATH)
    if EXPECTED_CLEAN_SHA256 and sha != EXPECTED_CLEAN_SHA256:
        print(
            f"[mirror_score_sde_ckpt] SHA-256 mismatch: expected "
            f"{EXPECTED_CLEAN_SHA256}, got {sha}",
            file=sys.stderr,
            flush=True,
        )
        return False
    print(
        f"[mirror_score_sde_ckpt] OK {CLEAN_CKPT_PATH} sha256={sha}",
        flush=True,
    )
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mirror_score_sde_ckpt",
        description=(
            "Download + extract the gnobitab Score-SDE CIFAR-10 1-Rectified "
            "Flow checkpoint into the framework's data/ directory."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if data/cifar10_rf.pth exists",
    )
    parser.add_argument(
        "--raw-only",
        action="store_true",
        help="Download the 990 MB raw ckpt but skip EMA extraction",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify data/cifar10_rf.pth SHA-256; do not download",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.verify_only:
        return 0 if verify_clean_ckpt() else 3

    if (
        CLEAN_CKPT_PATH.exists()
        and not args.force
        and not args.raw_only
    ):
        print(
            f"[mirror_score_sde_ckpt] {CLEAN_CKPT_PATH} already exists; "
            "pass --force to re-download",
            flush=True,
        )
        return 0 if verify_clean_ckpt() else 3

    download_raw_ckpt()
    if args.raw_only:
        return 0
    extract_ema_clean_ckpt()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
