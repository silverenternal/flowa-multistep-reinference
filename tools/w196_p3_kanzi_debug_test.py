#!/usr/bin/env python3
"""Debug: compare single-record vs batched encode/decode on the same record."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import torch
from kanzi import DAE, kabsch_rmsd

# Load DAE on CUDA
dae = DAE.from_pretrained("data/kanzi_ckpt/cleaned_model.pt").eval()
dae = dae.to("cuda")

# Read first record from input file
records = []
with open("verification_outputs/kanzi_n1000_coords.txt") as fh:
    for line in fh:
        line = line.strip()
        if not line or line.startswith(">"):
            continue
        vals = line.split(",")
        records.append(np.asarray([float(v) for v in vals], dtype=np.float64).reshape(-1, 3))
        if len(records) >= 4:
            break

print(f"loaded {len(records)} records, L={records[0].shape[0]}")

# SINGLE record path (mirrors runner)
print("\n=== SINGLE RECORD ===")
for i, r in enumerate(records[:2]):
    L = r.shape[0]
    coords_BLD = r.reshape(1, L, 3).astype(np.float32)
    torch.manual_seed(42 * 1_000_003 + i)
    x_t = torch.from_numpy(coords_BLD).to("cuda")
    *_, idx_BL = dae.encode(x_t, preprocess=False)
    print(f"  rec {i}: idx_BL shape={tuple(idx_BL.shape)}, idx_BL[0,:5]={idx_BL[0,:5].tolist()}")
    recon = dae.decode(idx_BL, n_steps=100).detach().cpu().numpy() * 10.0
    recon_A = recon.reshape(-1, 3).astype(np.float64)
    pred_A = coords_BLD.reshape(-1, 3).astype(np.float64)
    recon_c = recon_A - recon_A.mean(axis=0, keepdims=True)
    pred_c = pred_A - pred_A.mean(axis=0, keepdims=True)
    rmsd = float(kabsch_rmsd(
        torch.from_numpy(pred_c.astype(np.float32)),
        torch.from_numpy(recon_c.astype(np.float32)),
    ))
    print(f"  rec {i}: pred_max={np.abs(pred_c).max():.2f} Å, recon_max={np.abs(recon_c).max():.2f} Å, rmsd={rmsd:.4f} Å")

# BATCHED record path (mirrors my batched driver)
print("\n=== BATCHED 2 RECORDS ===")
coords_BLD = np.stack(records[:2], axis=0).astype(np.float32)
print(f"  coords_BLD shape={coords_BLD.shape}, max={np.abs(coords_BLD).max():.2f}")
torch.manual_seed(42 * 1_000_003 + 0)  # batch_start=0
x_t = torch.from_numpy(coords_BLD).to("cuda")
*_, idx_BL = dae.encode(x_t, preprocess=False)
print(f"  idx_BL shape={tuple(idx_BL.shape)}, idx_BL[:, :5]={idx_BL[:, :5].tolist()}")
recon = dae.decode(idx_BL, n_steps=100).detach().cpu().numpy() * 10.0
print(f"  recon shape={recon.shape}, max={np.abs(recon).max():.2f}")
for i in range(2):
    recon_i = recon[i].reshape(-1, 3).astype(np.float64)
    pred_i = coords_BLD[i].reshape(-1, 3).astype(np.float64)
    recon_c = recon_i - recon_i.mean(axis=0, keepdims=True)
    pred_c = pred_i - pred_i.mean(axis=0, keepdims=True)
    rmsd = float(kabsch_rmsd(
        torch.from_numpy(pred_c.astype(np.float32)),
        torch.from_numpy(recon_c.astype(np.float32)),
    ))
    print(f"  rec {i}: pred_max={np.abs(pred_c).max():.2f} Å, recon_max={np.abs(recon_c).max():.2f} Å, rmsd={rmsd:.4f} Å")
