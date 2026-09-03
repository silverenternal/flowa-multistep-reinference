# `tools/convert_reos_pickle_to_npy.py` — REOS pickle → mmap-friendly `.npy`

## Problem

`data/FlowMol3/repo/data/geom_full_kekulized/train_reos_ring_counts.pkl`
(187,510,843 bytes) is loaded by `flowmol.analysis.metrics.MoleculeAnalyzer.get_train_reos_rings`
via `pickle.load(f)` on every metrics call. The unpickled payload is a
`(1_170_522, 160) bool` array which (a) inflates peak RSS by ~3–5x versus the
equivalent contiguous `int8` buffer (pickle of `bool` stores one byte per
element plus per-row Python objects), and (b) blocks row-wise streaming on
large evaluation runs because the whole matrix lands in heap memory at once.

## Fix

Convert the pickle **once** into a layout that supports `np.load(...,
mmap_mode="r")`. The matrix is now read directly from disk and the resident
RSS stays flat (~0 pages) regardless of `N_mols`.

### What the converter produces

In `data/FlowMol3/repo/data/geom_full_kekulized/`:

| File                                       | Size           | Contents                                                         |
| ------------------------------------------ | -------------- | ---------------------------------------------------------------- |
| `train_reos_ring_counts.npy`               | 187,283,648 B  | `int8` array, shape `(1_170_522, 160)`, contiguous, mmap-friendly |
| `train_reos_ring_counts.header.txt`        | 4,001 B        | 160 REOS flag column names, one per line                         |
| `train_reos_smiles.txt`                    | 151,835 B      | 6,354 ring SMILES (sorted), one per line — **see note**          |

**Note on `train_reos_smiles.txt`:** the upstream pickle does *not* carry
per-molecule SMILES strings. Its three keys are `reos_flag_arr`,
`reos_flag_header`, and `ring_counts` (a tuple of `(defaultdict, dict, int)`
over *ring* SMILES, not per-mol). The sidecar therefore contains the sorted
ring-SMILES vocabulary extracted from `ring_counts[0]`. A true per-molecule
SMILES sidecar would have to be derived from `data/FlowMol3/references/geom_raw_train.pickle`
(~6.4 GiB) — out of scope for this MMAP fix.

### How the conversion was run

Under the 24 GiB virtual-address cap:

```bash
ulimit -v $((24*1024*1024)) && \
  .venvs/flowmol3_venv/bin/python tools/convert_reos_pickle_to_npy.py
```

Captured peak RSS (via `resource.getrusage(RUSAGE_SELF).ru_maxrss`):

| Stage                    | Peak RSS |
| ------------------------ | -------- |
| after `pickle.load`      | 208.7 MB |
| after `.astype(int8)`    | 387.5 MB |
| after `np.save`          | 387.8 MB |
| wall-clock               | 0.33 s   |

Threshold for abort was 20 GB; actual peak was 0.38 GB. Cap respected by ~50x.

### Mmap smoke test

```bash
.venvs/flowmol3_venv/bin/python -c \
  "import numpy as np; a = np.load('data/FlowMol3/repo/data/geom_full_kekulized/train_reos_ring_counts.npy', mmap_mode='r'); print(a.shape, a.dtype, a.nbytes, a[0:5].tolist())"
```

Output: `(1170522, 160) int8 187283520 [[0, 0, 0, ...], ..., [0, 0, 0, ...]]` — 5 rows
materialised without touching more than ~160 KiB of heap.

## Upstream patch path (NOT applied yet)

The upstream patch is a **separate** task. When it is applied, it should
target `data/FlowMol3/repo/flowmol/analysis/metrics.py` lines ~259–275
(`MoleculeAnalyzer.get_train_reos_rings`). The minimal, drop-in shape is:

```python
# data/FlowMol3/repo/flowmol/analysis/metrics.py  --  inside get_train_reos_rings

def get_train_reos_rings(self):
    base = Path(flowmol_root()) / 'data/geom_full_kekulized'
    npy_path   = base / 'train_reos_ring_counts.npy'
    pkl_path   = base / 'train_reos_ring_counts.pkl'
    side_path  = base / 'train_reos_smiles.txt'        # ring SMILES vocab (optional)
    head_path  = base / 'train_reos_ring_counts.header.txt'  # 160 column names

    if npy_path.is_file():
        flag_arr = np.load(npy_path, mmap_mode='r')    # <-- zero-copy, O(1) RSS
        flag_names = head_path.read_text(encoding='utf-8').splitlines() if head_path.is_file() \
            else [f'flag_{i}' for i in range(flag_arr.shape[1])]
        df_reos = build_reos_df(np.asarray(flag_arr), flag_names)
        return df_reos

    # ----- legacy fallback: pick up the old pickle if the .npy has not yet
    #       been generated (e.g. fresh clone of repo without the converter run).
    train_reos_file = pkl_path
    if not train_reos_file.exists():
        download_reos_train_data(download_path=train_reos_file)
        if not train_reos_file.exists():
            raise FileNotFoundError(...)
    with open(train_reos_file, 'rb') as f:
        data = pickle.load(f)
    flag_arr   = data['reos_flag_arr']
    flag_names = data['reos_flag_header']
    df_reos = build_reos_df(flag_arr, flag_names)
    return df_reos
```

Key points:

1. **Prefer `.npy` with `mmap_mode="r"`** when present. This is the only change
   required for the OOM fix — no other call site needs updating.
2. **Keep the pickle fallback** so fresh clones (and CI without the sidecar)
   still work. The `download_reos_train_data` URL remains the source of
   truth; the converter is a derived artefact.
3. **`build_reos_df`** (in `flowmol/analysis/reos.py`) only consumes the
   `(N, 160)` matrix plus the 160-element name list — it does **not** care
   whether the matrix is memory-mapped or RAM-resident. The `.tolist()` /
   `.sum()` calls inside `compute_cumulative_reos_deviation` are column-wise
   reductions that work fine on a memmap slice because numpy materialises
   only the accessed axis (≈ 160 × 1 MiB at most).
4. **The `train_reos_smiles.txt` sidecar is currently ring-SMILES vocab, not
   per-mol SMILES.** If/when a true per-mol SMILES file is generated (from
   `geom_raw_train.pickle`), the upstream patch can additionally load it via
   `smiles = side_path.read_text().splitlines()` to align `flag_arr` rows to
   molecules — but that is **out of scope** for this MMAP fix and only
   relevant if a downstream caller needs row→SMILES mapping (none currently
   do; see `metrics.py:reos_and_rings` which only does aggregate flag-rate
   comparisons).

## Re-running the conversion

The script is idempotent — `np.save` overwrites the destination. It does not
delete the original pickle (intentionally, so the legacy download/fallback
path still works). To regenerate after an upstream pickle revision:

```bash
ulimit -v $((24*1024*1024)) && \
  timeout 600 .venvs/flowmol3_venv/bin/python tools/convert_reos_pickle_to_npy.py
```

Verify with the smoke test command above.
