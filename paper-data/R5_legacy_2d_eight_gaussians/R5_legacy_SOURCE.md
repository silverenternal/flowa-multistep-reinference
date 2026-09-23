# R5_legacy 2D Eight Gaussians — Source Provenance

**Paper cell:** R5_legacy 2D Eight Gaussians (SUPP / LEGACY; per-round raw CSVs NOT preserved)
**Headline:** Wave 135 freeze baseline W2 0.6606 → framework W2 0.5919 (−10.40%); demoted to SUPP/LEGACY at Wave 256 P2; per-round raw CSV files NOT preserved per `docs/CLAIMS.md` line 3783
**Date:** 2026-09-23

## Primary data (in this directory)

| File | Description | SHA-256 anchor |
|---|---|---|
| `noise_injection_eight_gaussians_baseline.csv` | Eight Gaussians baseline noise-injection sweep CSV | (see `paper-data/MANIFEST.md`) |
| `noise_injection_eight_gaussians_framework.csv` | Eight Gaussians framework noise-injection sweep CSV | (see `paper-data/MANIFEST.md`) |
| `noise_injection_eight_gaussians_sigma_vs_w2.png` | σ vs W₂ scatter | (PNG) |
| `noise_injection_eight_gaussians_nfe_pareto.png` | NFE vs W₂ Pareto front | (PNG) |
| `noise_injection_eight_gaussians_pareto_front.png` | Pareto front visualization | (PNG) |
| `SOURCE.md` | Wave 135 freeze headline-evidence provenance | (symlink) |

## Audit trail

- Wave 135 freeze — `docs/headline-evidence/r5_2d_eight_gaussians_w2_m10p40pct/SOURCE.md`
- Wave 256 P2 — demotion from STRONG to SUPP/LEGACY
- `docs/CLAIMS.md` line 3783 — per-round raw CSVs NOT preserved (audit-trail partial gap; aggregate numbers preserved)

## Honest disclosure (preserved)

R5_legacy is SUPP/LEGACY. The headline number (−10.40%) is preserved but per-round raw CSVs are NOT preserved. Cited as the "matched-NFE 500" legacy cell.

## Verification

```bash
sha256sum -- R5_legacy_2d_eight_gaussians/*.{csv,png,md} > R5_legacy_2d_eight_gaussians/SHA256SUMS
```
