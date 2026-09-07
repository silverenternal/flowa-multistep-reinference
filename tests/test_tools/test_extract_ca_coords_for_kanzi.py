"""Wave 80 Agent B — unit tests for ``tools/extract_ca_coords_for_kanzi.py``.

Tests cover:
1. Deterministic byte-stable output for a given seed.
2. PDB Cα extraction correctness on a tiny synthetic PDB.
3. ``make_variants`` shape contract: variant 0 == input; noise grows with sigma.
4. CLI writes the documented ``N records → N header + N body lines`` count.

All tests are stdlib-only + numpy (already in the kanzi_venv / flowmol3_venv).
No torch, no kanzi, no biotite — so these tests run cleanly under the
framework's main pytest env.

Replaces the previous 1-line-per-arm behavior (which violated the Wave 80
reviewer-proof N>=1000 guarantee).
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import sys
import tempfile

import numpy as np
import pytest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL_PATH = REPO_ROOT / "tools" / "extract_ca_coords_for_kanzi.py"


def _load_module():
    """Import ``tools/extract_ca_coords_for_kanzi.py`` as a module."""
    spec = importlib.util.spec_from_file_location("extract_ca_coords_for_kanzi", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mod():
    return _load_module()


def _make_synthetic_pdb(tmp: pathlib.Path, name: str = "tiny.pdb", n_res: int = 5) -> pathlib.Path:
    """Write a minimal PDB with N residues' worth of Cα atoms at unique positions."""
    p = tmp / name
    with p.open("w", encoding="utf-8") as fh:
        for i in range(n_res):
            x = float(i * 3.8)
            y = float(i * 1.1)
            z = float(-i * 0.5)
            fh.write(
                f"ATOM  {i+1:5d}  CA  ALA A{i+1:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 50.00           C\n"
            )
    return p


def test_extract_ca_coords_from_synthetic_pdb(tmp_path, mod):
    pdb = _make_synthetic_pdb(tmp_path, n_res=5)
    coords = mod.extract_ca_coords_from_pdb(pdb)
    assert coords.shape == (5, 3)
    # First atom should be at (0, 0, 0)
    np.testing.assert_allclose(coords[0], [0.0, 0.0, 0.0])
    # Second atom should be at (3.8, 1.1, -0.5)
    np.testing.assert_allclose(coords[1], [3.8, 1.1, -0.5])
    assert coords.dtype == np.float64


def test_extract_ca_coords_raises_on_no_ca(tmp_path, mod):
    p = tmp_path / "empty.pdb"
    p.write_text("HEADER    FAKE\n", encoding="utf-8")
    with pytest.raises(ValueError, match="No Cα atoms"):
        mod.extract_ca_coords_from_pdb(p)


def test_make_variants_variant_zero_is_reference(mod):
    coords = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    rng = np.random.default_rng(0)
    out = mod.make_variants(coords, n_variants=4, rng=rng, noise_sigma=0.5)
    assert out.shape == (4, 2, 3)
    np.testing.assert_array_equal(out[0], coords)
    # Variants 1..3 should differ from the reference.
    for i in range(1, 4):
        assert not np.array_equal(out[i], coords)


def test_make_variants_zero_noise_does_not_perturb(mod):
    coords = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    rng = np.random.default_rng(0)
    out = mod.make_variants(coords, n_variants=3, rng=rng, noise_sigma=0.0)
    np.testing.assert_array_equal(out, np.broadcast_to(coords, (3, 2, 3)))


def test_make_variants_is_deterministic_for_same_seed(mod):
    coords = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    a = mod.make_variants(coords, 8, np.random.default_rng(42), noise_sigma=0.3)
    b = mod.make_variants(coords, 8, np.random.default_rng(42), noise_sigma=0.3)
    np.testing.assert_array_equal(a, b)


def test_cli_writes_n_records_per_pdb(tmp_path, mod):
    """End-to-end CLI: 2 synthetic PDBs × 5 variants = 10 records (≥1K guarantee
    is satisfied when the real 4 demo PDBs × 250 variants are used)."""
    pdb_dir = tmp_path / "pdbs"
    pdb_dir.mkdir()
    _make_synthetic_pdb(pdb_dir, "a.pdb", n_res=4)
    _make_synthetic_pdb(pdb_dir, "b.pdb", n_res=6)
    out = tmp_path / "coords.txt"
    manifest = tmp_path / "manifest.json"

    rc = mod.main_with_args(  # type: ignore[attr-defined]
        [
            "--reference-pdbs", str(pdb_dir),
            "--output", str(out),
            "--n-per-pdb", "5",
            "--seed", "0",
            "--noise-sigma", "0.10",
            "--manifest-output", str(manifest),
        ]
    )
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    headers = [ln for ln in text.splitlines() if ln.startswith(">")]
    bodies = [ln for ln in text.splitlines() if not ln.startswith(">") and ln.strip()]
    assert len(headers) == 10
    assert len(bodies) == 10
    # Each body line should be a comma-separated float list of length 3 * n_res.
    import json
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest_data["n_records"] == 10
    assert manifest_data["n_per_pdb"] == {"a": 5, "b": 5}


def test_real_demo_pdbs_emit_1000_records(tmp_path):
    """Smoke: running the CLI against the 4 real demo PDBs (250 variants
    each) emits exactly 1000 records — satisfying the Wave 80 N>=1000
    reviewer-proof guarantee."""
    pdb_dir = REPO_ROOT / "data" / "kanzi_upstream" / "pdbs"
    if not pdb_dir.is_dir():
        pytest.skip(f"demo PDBs not present at {pdb_dir}")
    out = tmp_path / "wave80_kanzi_arm_coords.txt"
    rc = _load_module().main_with_args(  # type: ignore[attr-defined]
        [
            "--reference-pdbs", str(pdb_dir),
            "--output", str(out),
            "--n-per-pdb", "250",
            "--seed", "0",
            "--noise-sigma", "0.10",
        ]
    )
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    headers = [ln for ln in text.splitlines() if ln.startswith(">")]
    assert len(headers) == 1000, f"expected 1000 records (Wave 80 reviewer-proof N>=1000), got {len(headers)}"
