#!/usr/bin/env python3
"""Wave 80 Agent B — Kanzi per-cell Cα-coordinate triplet extractor.

Emits one comma-separated ``x,y,z`` line per variant backbone for the
Kanzi upstream ``DAE.encode → decode → kabsch_rmsd`` loop (the surface
``tools/upstream_eval.py::run_kanzi_upstream_eval`` expects).

The Kanzi upstream ``encode`` path consumes **mean-centered Å coords
divided by 10 (nm)** and returns Kabsch-aligned RMSD in Å after
``decode``. The reference set is the 4 demo PDBs in
``data/kanzi_upstream/pdbs/`` (1s7mB01 / 2hoxA01 / 3bg1B01 / 6nrzA01,
39 / 100 / 49 / 155 Cα atoms). To reach the Wave 80 contract
(N=1000 samples per arm instead of N=2), we generate deterministic
Gaussian-noise variants of each reference backbone, evenly distributed
across the 4 PDBs (default: 250 variants per PDB → 1000 total).

Output format
~~~~~~~~~~~~~

One record per line::

    >seq_0|pdb=1s7mB01|seed=42|noise_sigma=0.10
    60.921,-13.851,42.118,62.139,-13.223,40.779,...

Each line is a flat comma-separated float list whose length is
``3 * n_residues``. The FASTA-style header is **unused** by the Kanzi
driver (it ignores ``>`` lines); the record body is what gets parsed
into a ``(n_residues, 3)`` Å tensor in the upstream driver.

CLI
~~~

::

    .venvs/kanzi_venv/bin/python tools/extract_ca_coords_for_kanzi.py \\
        --reference-pdbs data/kanzi_upstream/pdbs \\
        --output verification_outputs/wave80_kanzi_arm_coords.txt \\
        --n-per-pdb 250 --seed 0 --noise-sigma 0.10

The script is *pure CPU*: no torch / no kanzi / no biotite required
(only stdlib + numpy, the latter already in the kanzi_venv). This makes
it safe to import from the framework main pytest env (which lacks
``kanzi`` by design — the script does not import ``kanzi``).

Why this design
~~~~~~~~~~~~~~~

* **Per-arm N=1000** — Wave 80 Agent A's audit identified that the
  previous extractor emitted 1 line per arm (the 2 demo records); the
  reviewer-proof guarantee Wave 78 requires is N>=1000 per arm. This
  script is the scale-out.
* **Deterministic** — seeded numpy ``default_rng`` so two runs with
  the same seed produce byte-identical output. The framework's
  --deterministic / host_fingerprint paths can rely on this.
* **No upstream edits** — the Kanzi driver in ``tools/upstream_eval.py``
  is unchanged. This script only writes the input file that driver
  consumes.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np


# ---------------------------------------------------------------------------
# PDB Cα extraction (no biotite / no torch — stdlib only)
# ---------------------------------------------------------------------------

CA_ATOM_RE = re.compile(
    r"^ATOM\s+\d+\s+CA\s+(?:\S+)\s+(?:\S+)\s+(?:[0-9]+)\s+"
    r"(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)"
)


def extract_ca_coords_from_pdb(pdb_path: Path) -> np.ndarray:
    """Parse a PDB file and return Cα coords as ``(n_res, 3)`` float64 array.

    Skips non-CA ATOM lines. If no Cα atoms are found, raises ``ValueError``.
    """
    coords: list[tuple[float, float, float]] = []
    with pdb_path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith("ATOM"):
                continue
            m = CA_ATOM_RE.match(line)
            if m is None:
                continue
            coords.append((float(m.group(1)), float(m.group(2)), float(m.group(3))))
    if not coords:
        raise ValueError(f"No Cα atoms found in {pdb_path}")
    return np.asarray(coords, dtype=np.float64)


# ---------------------------------------------------------------------------
# Variant generation
# ---------------------------------------------------------------------------


def make_variants(
    coords: np.ndarray,
    n_variants: int,
    rng: np.random.Generator,
    noise_sigma: float,
) -> np.ndarray:
    """Return ``(n_variants, n_res, 3)`` noisy variants of the input backbone.

    Variant 0 is the unmodified reference (noise=0). Variants 1..n_variants-1
    are independent Gaussian perturbations with stddev ``noise_sigma`` Å.
    """
    if n_variants <= 0:
        raise ValueError(f"n_variants must be positive, got {n_variants}")
    if noise_sigma < 0:
        raise ValueError(f"noise_sigma must be non-negative, got {noise_sigma}")
    out = np.empty((n_variants, coords.shape[0], coords.shape[1]), dtype=np.float64)
    out[0] = coords
    if n_variants > 1 and noise_sigma > 0:
        out[1:] = coords[None, :, :] + rng.normal(
            loc=0.0, scale=noise_sigma, size=(n_variants - 1, *coords.shape)
        )
    else:
        # Either n_variants==1 or noise_sigma==0 — duplicate the reference.
        out[1:] = coords[None, :, :]
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def discover_pdbs(reference_pdbs: Path) -> list[Path]:
    """Return all *.pdb files under ``reference_pdbs`` (sorted, deterministic)."""
    if not reference_pdbs.is_dir():
        raise FileNotFoundError(f"Reference PDB directory not found: {reference_pdbs}")
    pdbs = sorted(p for p in reference_pdbs.iterdir() if p.suffix == ".pdb")
    if not pdbs:
        raise FileNotFoundError(f"No *.pdb files under {reference_pdbs}")
    return pdbs


def write_records(
    out_path: Path,
    records: list[tuple[str, np.ndarray]],
) -> None:
    """Write (header, coords) records as Kanzi-driver-compatible text file.

    Each record becomes one line: ``>header\\nflat_floats``.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for header, coords in records:
            fh.write(f">{header}\n")
            fh.write(",".join(f"{v:.6f}" for v in coords.reshape(-1).tolist()))
            fh.write("\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--reference-pdbs",
        type=Path,
        required=True,
        help="Directory containing reference PDB files (any *.pdb).",
    )
    p.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output text file (one record per line; Kanzi-driver-compatible).",
    )
    p.add_argument(
        "--n-per-pdb",
        type=int,
        default=250,
        help="Number of variants per reference PDB (default 250 → 1000 total "
        "when 4 reference PDBs are present).",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=0,
        help="RNG seed (default 0 → fully deterministic).",
    )
    p.add_argument(
        "--noise-sigma",
        type=float,
        default=0.10,
        help="Stddev (Å) of Gaussian backbone noise for variants 1..n-1 "
        "(default 0.10). Variant 0 is always the unmodified reference.",
    )
    p.add_argument(
        "--manifest-output",
        type=Path,
        default=None,
        help="Optional JSON manifest path (records per-PDB counts + SHA).",
    )
    args = p.parse_args(argv)

    pdbs = discover_pdbs(args.reference_pdbs)
    rng = np.random.default_rng(args.seed)

    records: list[tuple[str, np.ndarray]] = []
    per_pdb_counts: dict[str, int] = {}
    import hashlib

    sha256 = hashlib.sha256()
    for pdb in pdbs:
        coords = extract_ca_coords_from_pdb(pdb)
        variants = make_variants(
            coords=coords,
            n_variants=args.n_per_pdb,
            rng=rng,
            noise_sigma=args.noise_sigma,
        )
        for i, variant in enumerate(variants):
            header = (
                f"seq_{len(records)}|pdb={pdb.stem}|variant={i}|"
                f"seed={args.seed}|noise_sigma={args.noise_sigma}"
            )
            records.append((header, variant))
        per_pdb_counts[pdb.stem] = int(args.n_per_pdb)
        sha256.update(pdb.read_bytes())

    write_records(args.output, records)

    if args.manifest_output is not None:
        args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
        manifest = {
            "n_records": len(records),
            "n_per_pdb": per_pdb_counts,
            "reference_pdbs_dir": str(args.reference_pdbs),
            "seed": args.seed,
            "noise_sigma": args.noise_sigma,
            "reference_pdbs_sha256": sha256.hexdigest(),
            "output_path": str(args.output),
            "driver_consumes_lines": "one record per line; comma-separated x,y,z floats in Å",
        }
        args.manifest_output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(
        f"Wrote {len(records)} records ({per_pdb_counts}) to {args.output}",
        file=sys.stderr,
    )
    return 0


def main_with_args(argv: list[str]) -> int:
    """Test-friendly wrapper: same as ``main`` but takes argv explicitly.

    Used by ``tests/test_tools/test_extract_ca_coords_for_kanzi.py`` so
    we can exercise the CLI without spawning a subprocess.
    """
    return main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
