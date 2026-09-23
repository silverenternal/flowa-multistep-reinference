# K4 + K5 LineageFlow HMMER — Source Provenance

**Paper cells:** K4 (length-bias) + K5 (uniform-AA) on LineageFlow HMMER
**Headline:** K4 POWERED at metric-collection level (12-22 hits/100 records non-zero across all 3 seeds); K5 paired-delta +8.9% (+1.33 hits) visible but Bonf-FAIL at α=0.0125 (n=3 paired seeds d_f=2)
**Date:** 2026-09-23 (Wave 280 P capture)

## Primary data (in this directory)

| File | Description | SHA-256 anchor |
|---|---|---|
| `summary_n100.json` | Wave 280 P K4+K5 3-seed hmmscan summary | (see `K4_k5_lineageflow_hmmer/SHA256SUMS`) |
| `SHA256SUMS` | Wave 280 P K4+K5 sidecar SHA-256 ledger | (sidecar) |
| `seed42/` | K4+K5 seed=42 sub-directory | (directory symlink) |
| `seed43/` | K4+K5 seed=43 sub-directory | (directory symlink) |
| `seed44/` | K4+K5 seed=44 sub-directory | (directory symlink) |

## Audit trail

- Wave 280 P — `verification_outputs/wave280-p-k4k5/`
- Wave 306 — K4+K5 demotion (K4 POWERED + K5 SUPP-WITH-CAVEAT)
- `docs/CLAIMS.md` — K4/K5 honest disclosure

## Honest disclosure (preserved)

K4 is POWERED at metric-collection level (12-22 hits/100 records non-zero across all 3 seeds). K5 paired-delta +8.9% (+1.33 hits) is visible but Bonf-FAIL at α=0.0125.

## Verification

```bash
sha256sum -- K4_k5_lineageflow_hmmer/*.{json,md} > K4_k5_lineageflow_hmmer/SHA256SUMS.new
```
