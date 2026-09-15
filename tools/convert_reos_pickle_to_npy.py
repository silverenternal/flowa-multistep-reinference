"""Convert train_reos_ring_counts.pkl to a memory-mappable .npy + sidecar files.

Why this exists
---------------
`train_reos_ring_counts.pkl` is ~178 MiB and contains a `(N_mols, 160)` boolean
flag array (N_mols = 1_170_522). Upstream `flowmol.analysis.metrics.MoleculeAnalyzer.get_train_reos_rings`
loads it via `pickle.load(f)` on every metrics call, which both (a) serialises
deserialisation time on each call and (b) inflates peak RSS by ~3-5x because the
pickle unpickles into Python `bool` objects (a pickle of `(N, 160) bool` is
roughly an order of magnitude larger in memory than the equivalent contiguous
`numpy.uint8` / `int8` array).

This script converts the pickle **once** into:

  train_reos_ring_counts.npy         int8 array, shape (N_mols, 160)
  train_reos_smiles.txt              one SMILES per line (see NOTE below)
  train_reos_ring_counts.header.txt  the 160 REOS flag column names (one per line)

Downstream consumers open the .npy with `np.load(..., mmap_mode="r")` and read
only the rows they need; RSS stays flat regardless of N_mols.

NOTE on the SMILES sidecar
--------------------------
The upstream pickle does NOT contain per-molecule SMILES strings. Its three
keys are:

  reos_flag_arr       (1170522, 160) bool   -- the per-mol flag matrix
  reos_flag_header    list[str] len=160    -- column names for the flag matrix
  ring_counts         tuple(defaultdict, dict, int)
                                            -- ring-SMILES frequency counts

The third item contains *ring* SMILES (e.g. "c1ccccc1") with per-molecule
counts, but no per-molecule identity. We save those ring SMILES into the
sidecar `train_reos_smiles.txt` so the row-order relationship with the flag
array is at least preserved via column labels (in `*.header.txt`). A true
per-molecule SMILES list would require loading the upstream
`geom_raw_train.pickle` (~6.4 GiB), which is out of scope for this MMAP fix
-- see the README for the (separate) upstream patch path that will pair this
.npy with the raw GEOM-DRUGS SMILES at metrics load time.
"""
from __future__ import annotations

import argparse
import pickle
import sys
import time
from pathlib import Path

import numpy as np

DEFAULT_PKL = Path(
    "/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/data/"
    "geom_full_kekulized/train_reos_ring_counts.pkl"
)
DEFAULT_OUTDIR = Path(
    "/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/data/"
    "geom_full_kekulized"
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pkl", type=Path, default=DEFAULT_PKL, help="input pickle path")
    p.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR, help="output directory")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    pkl_path: Path = args.pkl
    outdir: Path = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    if not pkl_path.is_file():
        print(f"[convert_reos] missing pickle: {pkl_path}", file=sys.stderr)
        return 1

    t0 = time.time()
    print(f"[convert_reos] loading {pkl_path} ({pkl_path.stat().st_size:,} bytes) ...")
    with pkl_path.open("rb") as f:
        data = pickle.load(f)

    if not isinstance(data, dict):
        print(f"[convert_reos] expected dict, got {type(data).__name__}", file=sys.stderr)
        return 2

    flag_arr = data.get("reos_flag_arr")
    flag_header = data.get("reos_flag_header")
    ring_counts = data.get("ring_counts")

    if not isinstance(flag_arr, np.ndarray) or flag_arr.ndim != 2:
        print(f"[convert_reos] reos_flag_arr missing or not 2-D ndarray: {type(flag_arr)}",
              file=sys.stderr)
        return 3

    n_mols, n_flags = flag_arr.shape
    print(f"[convert_reos] flag_arr shape={flag_arr.shape} dtype={flag_arr.dtype} "
          f"(loaded in {time.time()-t0:.1f}s)")

    # Pick int8 if possible (bool fits in 0..1, so always true here), else int16.
    # bool is safe because the upstream flags are REOS detection booleans.
    out_dtype = np.int8
    print(f"[convert_reos] casting {flag_arr.dtype} -> {out_dtype.__name__}")
    flat = flag_arr.astype(out_dtype, copy=False)
    if flat.base is not None:
        # ensure contiguous, mmap-friendly layout
        flat = np.ascontiguousarray(flat)

    npy_path = outdir / "train_reos_ring_counts.npy"
    print(f"[convert_reos] writing {npy_path}")
    np.save(npy_path, flat, allow_pickle=False)
    nbytes = npy_path.stat().st_size

    header_path = outdir / "train_reos_ring_counts.header.txt"
    smiles_path = outdir / "train_reos_smiles.txt"

    if isinstance(flag_header, (list, tuple)) and len(flag_header) == n_flags:
        header_path.write_text("\n".join(str(h) for h in flag_header) + "\n", encoding="utf-8")
        print(f"[convert_reos] wrote {header_path} ({len(flag_header)} flag names)")
    else:
        header_path.write_text("", encoding="utf-8")
        print(f"[convert_reos] WARNING: reos_flag_header missing or wrong length; "
              f"wrote empty {header_path}", file=sys.stderr)

    # The pickle stores per-ring SMILES counts, not per-mol SMILES. Dump the
    # ring SMILES list (sorted) so the sidecar is at least non-empty and
    # useful for downstream callers.
    ring_smi: list[str] = []
    if isinstance(ring_counts, tuple) and len(ring_counts) >= 1:
        first = ring_counts[0]
        try:
            ring_smi = sorted(first.keys())
        except AttributeError:
            ring_smi = []
    smiles_path.write_text("\n".join(ring_smi) + ("\n" if ring_smi else ""), encoding="utf-8")
    print(f"[convert_reos] wrote {smiles_path} ({len(ring_smi)} ring SMILES -- "
          f"NOTE: not per-molecule, see module docstring)")

    print(f"[convert_reos] DONE  shape={flat.shape} dtype={flat.dtype.name} "
          f"nbytes={nbytes:,} elapsed={time.time()-t0:.1f}s")
    print(f"[convert_reos] peak pickle mem footprint ~= {pkl_path.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
