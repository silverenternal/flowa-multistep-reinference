# Kanzi N=1000 framework_inv_proj byte-reproducible (Wave 127 + Wave 131)

**Headline:** framework mean_rmsd = 0.8798 +- 0.1364 angstroms (n=1000, deterministic),
baseline_seed42 mean_rmsd = 0.9020 +- 0.1375 angstroms, delta = -0.0222 angstroms (TIES).

**Byte-reproducibility verified at delta = 0.00e+00 across Wave 127 + Wave 131 commits**
on the ruff-frozen code (per docs/audit/wave131-pre-freeze-hygiene.md byte-repro appendix).

**Source files (8 N=1000 sweep JSONs across Wave 116/120/121/122/127/131):**
- verification_outputs/kanzi_n1000_baseline_seed42_wave116_q3_2026/
- verification_outputs/kanzi_n1000_baseline_seed42_wave120_q3_2026/
- verification_outputs/kanzi_n1000_baseline_seed7_wave121_q3_2026/
- verification_outputs/kanzi_n1000_framework_synth_wave120_q3_2026/
- verification_outputs/kanzi_n1000_framework_synth_seed42_wave121_q3_2026/
- verification_outputs/kanzi_n1000_framework_inv_proj_seed42_wave122_q3_2026/
- verification_outputs/kanzi_n1000_framework_inv_proj_seed42_wave127_q3_2026/
- verification_outputs/kanzi_n1000_framework_inv_proj_seed42_wave131_byte_repro_q3_2026/

**Reproducibility CLI (from docs/audit/wave131-pre-freeze-hygiene.md):**
source .venvs/kanzi_venv/bin/activate
python tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py \
  --input verification_outputs/kanzi_n1000_coords.txt \
  --ckpt data/kanzi_ckpt/cleaned_model.pt \
  --output-dir /tmp/w127/framework_inv_proj_seed42 \
  --seed 42 --n-steps-decoder 100 --adapter-num-steps 50 \
  --adapter-solver euler --adapter-force-mode torch

**Determinism:** Per-record seed fixed; reproducible across ruff-frozen code boundary.