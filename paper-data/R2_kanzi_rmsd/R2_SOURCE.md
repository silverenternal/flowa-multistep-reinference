# R2 Kanzi RMSD — Source Provenance

**Paper cell:** R2 Kanzi RMSD uplift (paired-t Bonf-sig at α=0.007143)
**Headline:** Baseline RMSD 0.9020 Å → Framework RMSD 0.8798 Å (−0.022 Å, d_z=−0.0990)
**Date:** 2026-09-23 (Wave 218 P3 capture)

## Primary data (in this directory)

| File | Description | SHA-256 anchor |
|---|---|---|
| `kanzi_n1000_paper_metrics.json` | Kanzi baseline N=1000 paper-metrics | `02e9df307defda4f25acadb3dcd135ed697898f9766908f82f823f892e1aa942` |
| `kanzi_framework_paper_metrics.json` | Kanzi framework inv_proj N=1000 paper-metrics | `a0c37b498f8c664bfdb5b7e39182aad79a083f040d2a61cf05aa29f5206321bd` |
| `per_metric.jsonl` | Per-record framework RMSD distribution | `c9a5956441ec0bf4ce2f6ea74d054f47389cdd05e8655da159bd3517339abeea` |
| `wave218-p3-kanzi-framework-wins.csv` | Wave 218 framework-WINS paired-diff headline | `5f957d056ce5977d11e8660f34e4574c7f11a6d7bbea7115f56e2bf5378f5e31` |
| `wave218-p3-kanzi-framework-wins.json` | Wave 218 framework-WINS paired-diff headline JSON | `9b5c3b68d05b136e662fffbef1873693f28c43547cebf7b8c7b480261d0de49c` |
| `wave218-p3-kanzi-baseline-n1000.log` | Baseline run log | (sha-256 in `../R2_kanzi_rmsd/SHA256SUMS`) |
| `wave218-p3-kanzi-framework-n1000.log` | Framework run log | (sha-256 in `../R2_kanzi_rmsd/SHA256SUMS`) |

## Audit trail

- Wave 218 P3 — `verification_outputs/wave218-p3-kanzi-framework-wins.{csv,json}`
- Wave 131 — byte-reproducibility capture
- Wave 122 — initial framework inv_proj N=1000 capture
- `docs/DATA_PRESENTATION.md` §2.2 — paper-cited R2 row
- `docs/CLAIMS.md` CLM-039 — paired-t Bonf-sig source

## Verification

```bash
sha256sum -- R2_kanzi_rmsd/*.{json,csv,jsonl,md,log} > R2_kanzi_rmsd/SHA256SUMS
```

All hashes must match those listed above and in `paper-data/MANIFEST.md`.
