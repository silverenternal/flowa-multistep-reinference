#!/usr/bin/env python3
"""Wave 235 P4: Run ONLY seed=44 framework arm (n_total=500, nfe=100).

This is a focused script (avoiding redundant seed44 baseline re-run).
Output:
  - verification_outputs/wave235-p4-flowmol3-seed44-framework.json
  - verification_outputs/wave235-p4-flowmol3-seed44-framework.smiles.txt
"""
from __future__ import annotations

import json
import os
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

REPO = Path("/home/hugo/codes/flowa-multistep-reinference")
OUT_DIR = REPO / "verification_outputs"

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "data" / "FlowMol3" / "repo"))

import numpy as np

# Re-use helpers from the main script
sys.path.insert(0, str(REPO / "scripts"))
import wave235_p4_flowmol3_3seed as w  # noqa: E402

N_TOTAL = 500
NFE = 100
SEED = 44


def main() -> int:
    print("=" * 78, flush=True)
    print(f"Wave 235 P4: seed={SEED} framework arm ONLY (n_total={N_TOTAL}, nfe={NFE})", flush=True)
    print("=" * 78, flush=True)

    from adaptive_reflow.adapters.flowmol3_v2_adapter import FlowMol3V2Adapter

    print("Loading FlowMol3 v2 adapter (upstream path) ...", flush=True)
    t0 = time.perf_counter()
    adapter = FlowMol3V2Adapter(
        backend="torch",
        num_steps=NFE,
        weights_path=str(REPO / "data" / "flowmol3" / "weights_real" / "checkpoints" / "last.ckpt"),
        device="cuda:0",
        use_upstream=True,
        upstream_repo_dir=str(REPO / "data" / "FlowMol3" / "repo"),
    )
    _ = adapter._load_model()
    print(f"Adapter loaded in {time.perf_counter()-t0:.2f}s", flush=True)

    arm_raw = w._generate_arm_single_mol(
        adapter=adapter,
        arm_name="framework",
        perturbation_sigma=0.05,
        seed_base=int(SEED),
        n_total=N_TOTAL,
        nfe=NFE,
    )
    arm_full = dict(arm_raw)
    smiles_list = arm_full.pop("smiles_list")
    arm_capped = dict(arm_full)
    arm_capped["smiles_list_capped_200"] = smiles_list[:200]
    arm_capped["smiles_count"] = len(smiles_list)
    out_json = OUT_DIR / f"wave235-p4-flowmol3-seed{SEED}-framework.json"
    out_json.write_text(json.dumps(arm_capped, indent=2), encoding="utf-8")
    print(f"Wrote {out_json}", flush=True)
    smiles_txt = OUT_DIR / f"wave235-p4-flowmol3-seed{SEED}-framework.smiles.txt"
    smiles_txt.write_text("\n".join(smiles_list) + "\n", encoding="utf-8")
    print(f"Wrote {smiles_txt}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())