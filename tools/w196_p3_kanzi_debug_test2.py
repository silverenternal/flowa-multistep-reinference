#!/usr/bin/env python3
"""Debug v2: corrected batched path with Å → nm before encode."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import torch
from kanzi import DAE, kabsch_rmsd

dae = DAE.from_pretrained("data/kanzi_ckpt/cleaned_model.pt").eval()
dae = dae.to("cuda")

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

# SINGLE record with Å → nm
print("\n=== SINGLE RECORD (Å→nm before encode) ===")
for i, r in enumerate(records[:2]):
    L = r.shape[0]
    coords_A = r.astype(np.float64)
    coords_A = coords_A - coords_A.mean(axis=0, keepdims=True)
    coords_nm = (coords_A / 10.0).astype(np.float32)
    coords_BLD = coords_nm.reshape(1, L, 3)
    torch.manual_seed(42 * 1_000_003 + i)
    x_t = torch.from_numpy(coords_BLD).to("cuda")
    *_, idx_BL = dae.encode(x_t, preprocess=False)
    recon = dae.decode(idx_BL, n_steps=100).detach().cpu().numpy() * 10.0
    recon_A = recon.reshape(-1, 3).astype(np.float64)
    pred_A = coords_A.reshape(-1, 3).astype(np.float64)
    recon_c = recon_A - recon_A.mean(axis=0, keepdims=True)
    pred_c = pred_A - pred_A.mean(axis=0, keepdims=True)
    rmsd = float(kabsch_rmsd(
        torch.from_numpy(pred_c.astype(np.float32)),
        torch.from_numpy(recon_c.astype(np.float32)),
    ))
    print(f"  rec {i}: idx_BL[0,:5]={idx_BL[0,:5].tolist()}, pred_max={np.abs(pred_c).max():.2f}, recon_max={np.abs(recon_c).max():.2f}, rmsd={rmsd:.4f} Å")
