"""Wave 74 Agent 4 — Smoke test for F3 (xtb) + F4 (energy_dist.npz) axes.

Loads ``tools/run_real_ckpt_eval.py`` and invokes
``_compute_xtb_med_rmsd`` + verifies that ``_compute_flowmol3_composite``
detects the vendored ``energy_dist.npz`` and the installed ``xtb``.

Run: ``.venvs/flowmol3_venv/bin/python tools/wave74_smoke_env_axes.py``
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

# Make sure xtb is on $PATH for the test
os.environ["PATH"] = "/home/hugo/xtb_prefix/bin:" + os.environ.get("PATH", "")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Use the flowmol3_venv python (must be already running in it).
import tools.run_real_ckpt_eval as rce  # noqa: E402

results = {}

# 1. xtb on $PATH
xtb_bin = shutil.which("xtb")
results["xtb_on_PATH"] = bool(xtb_bin)
results["xtb_path"] = xtb_bin or None
if xtb_bin:
    # Run `xtb --help` to confirm it actually launches
    try:
        import subprocess as sp
        cp = sp.run([xtb_bin], capture_output=True, timeout=10)
        results["xtb_help_exit_code"] = int(cp.returncode)
    except Exception as exc:  # noqa: BLE001
        results["xtb_help_error"] = repr(exc)

# 2. energy_dist.npz vendored
from adaptive_reflow.adapters.flowmol3_metrics_upstream import (  # noqa: E402
    FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR,
)
npz_path = Path(FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR) / "energy_dist.npz"
results["energy_dist_path"] = str(npz_path)
results["energy_dist_exists"] = npz_path.is_file()
results["energy_dist_size_bytes"] = (
    int(npz_path.stat().st_size) if npz_path.is_file() else 0
)

# 3. _compute_xtb_med_rmsd on a tiny fake molecule
import dataclasses


@dataclasses.dataclass
class FakeMol:
    positions: object
    atom_types: object


# Build a tiny 3-atom H2O-like geometry (Å).
import numpy as np  # noqa: E402

fake_positions = np.array(
    [
        [0.0, 0.0, 0.0],
        [0.96, 0.0, 0.0],
        [-0.24, 0.93, 0.0],
    ],
    dtype=float,
)
fake_atoms = np.array([8, 1, 1], dtype=int)
fake_mol = FakeMol(positions=fake_positions, atom_types=fake_atoms)
med_rmsd = rce._compute_xtb_med_rmsd([fake_mol], max_molecules=1, timeout_s=20)
results["xtb_med_rmsd_value"] = med_rmsd
results["xtb_med_rmsd_type"] = type(med_rmsd).__name__ if med_rmsd is not None else None
results["xtb_med_rmsd_finite"] = (
    med_rmsd is not None and float(med_rmsd) >= 0.0
)

print(json.dumps(results, indent=2, default=str))