# K1 Kanzi Algorithm-Primitive Ablation — Source Provenance

**Paper cell:** K1 FlowMol3 RDKit-validity (SUPP / UNDERPOWERED)
**Headline:** d_z=+1.3645 REAL but p_bonf=0.5676 FAILS K-level α=0.0125 by 45.4× (paper-cited 0.054 mis-applied R-level k=7 family to a K-level cell)
**Date:** 2026-09-23 (Wave 280 P capture)

## Primary data (in this directory)

| File | Description | SHA-256 anchor |
|---|---|---|
| `summary.json` | Wave 280 P K1 5-arm algorithm-primitive ablation summary | (see `K1_kanzi_algorithm/SHA256SUMS`) |
| `SHA256SUMS` | Wave 280 P K1 sidecar SHA-256 ledger | (sidecar) |
| `driver.py` | Wave 280 P K1 driver script (for reproducibility) | (script) |
| `run.log` | Wave 280 P K1 run log | (log) |

## Audit trail

- Wave 280 P — `verification_outputs/wave280-p-k1/`
- Wave 308 P2 — demotion from PARTIAL/BORDERLINE-STRONG to SUPP/UNDERPOWERED
- Wave 157 — K1 algorithm-primitive 5/5 ablation (`docs/audit/wave157-close.md`)

## Honest disclosure (preserved)

K1 is SUPP/UNDERPOWERED. The d_z is REAL but Bonferroni correction is mis-applied (paper-cited 0.054 used R-level k=7 family where K-level k=8 family at α=0.0125 applies). p_bonf=0.5676 FAILS at α=0.0125 by 45.4×.

## Verification

```bash
sha256sum -- K1_kanzi_algorithm/*.{json,py,log,SHA256SUMS,md} > K1_kanzi_algorithm/SHA256SUMS.new
diff K1_kanzi_algorithm/SHA256SUMS K1_kanzi_algorithm/SHA256SUMS.new  # should be empty
```
