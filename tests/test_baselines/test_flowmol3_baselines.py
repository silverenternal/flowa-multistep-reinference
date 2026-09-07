"""Smoke tests for the Wave 54 Phase 2 FlowMol3 baseline scripts.

These tests invoke the baseline scripts as subprocesses (via the
``flowmol3_venv`` sidecar). They are skipped when the venv is not
available — they exist to provide a *real* end-to-end check of the
new scripts when the sidecar is on disk.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VENV_PYTHON = REPO_ROOT / ".venvs" / "flowmol3_venv" / "bin" / "python"
SKIP_REASON = "flowmol3_venv sidecar not on disk (subprocess smoke test)"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(script: str, nfe_list: str) -> dict:
    """Run a baseline script with a tiny NFE list and return the parsed JSON."""
    if not VENV_PYTHON.exists():
        pytest.skip(SKIP_REASON)
    out_path = REPO_ROOT / "verification_outputs" / f"_smoke_{script}.json"
    cmd = [
        str(VENV_PYTHON),
        str(REPO_ROOT / "scripts" / "baselines" / script),
        "--nfe-list", nfe_list,
        "--output", str(out_path),
    ]
    res = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(REPO_ROOT),
        timeout=180,
    )
    assert res.returncode == 0, (
        f"baseline script {script!r} failed:\nstdout={res.stdout}\n"
        f"stderr={res.stderr}"
    )
    return json.loads(out_path.read_text())


# ---------------------------------------------------------------------------
# Script-level smoke tests
# ---------------------------------------------------------------------------

def test_moldiff_baseline_smoke() -> None:
    """Smoke: run MolDiff baseline with 3 NFEs and verify schema."""
    record = _run("run_flowmol3_baseline_moldiff.py", "10,50,250")
    assert record["schema"] == "flowmol3_baseline_report.v1"
    assert record["baseline"] == "moldiff_ddpm"
    assert len(record["cells"]) == 3
    # Each cell must have composite + phi1..phi4 keys
    for cell in record["cells"]:
        assert "composite" in cell
        assert "phi1_frac_valid_mols" in cell
        assert "phi2_frac_mols_stable" in cell
        assert "phi3_neg_energy_js_div" in cell
        assert "phi4_neg_reos_cum_dev" in cell
        # And the chemistry marker must be either "ok" or "blocked_rdkit"
        assert cell["chemistry_marker"] in ("ok", "blocked_rdkit")


def test_equifm_baseline_smoke() -> None:
    """Smoke: run EquiFM baseline with 3 NFEs and verify schema."""
    record = _run("run_flowmol3_baseline_equifm.py", "10,50,250")
    assert record["schema"] == "flowmol3_baseline_report.v1"
    assert record["baseline"] == "equifm_linear_ot"
    assert len(record["cells"]) == 3
    for cell in record["cells"]:
        assert "composite" in cell
        assert cell["chemistry_marker"] in ("ok", "blocked_rdkit")


# ---------------------------------------------------------------------------
# Cross-script comparison
# ---------------------------------------------------------------------------

def test_moldiff_vs_equifm_categorical_endpoint_differs() -> None:
    """MolDiff collapses to uniform; EquiFM collapses to C + no-bond.

    The ``argmax_change_rate_atom_types`` axis is the qualitative
    discriminator between the two baselines (MolDiff's CTMC re-mask
    collapses to uniform → no argmax change; EquiFM's linear-OT
    collapses to C → 100% argmax change).
    """
    moldiff = _run("run_flowmol3_baseline_moldiff.py", "10,50,250")
    equifm = _run("run_flowmol3_baseline_equifm.py", "10,50,250")
    # EquiFM's categorical channel converges to a single atom type
    # (C) so the argmax changes for every position vs the random prior.
    equifm_turnover = equifm["cells"][-1]["argmax_change_rate_atom_types"]
    moldiff_turnover = moldiff["cells"][-1]["argmax_change_rate_atom_types"]
    assert equifm_turnover > moldiff_turnover, (
        f"expected EquiFM turnover ({equifm_turnover}) > MolDiff "
        f"turnover ({moldiff_turnover}) because MolDiff re-mask "
        f"collapses to uniform (no argmax change)."
    )


def test_baseline_outputs_have_wave54_agent_marker() -> None:
    """All baseline records must carry the Wave 54 / Agent B marker."""
    for script in ("run_flowmol3_baseline_moldiff.py",
                   "run_flowmol3_baseline_equifm.py"):
        record = _run(script, "10,50,250")
        assert record["wave"] == 54
        assert record["agent"] == "B"
        assert record["task"] == "flowmol3_tier3_baseline_comparison"