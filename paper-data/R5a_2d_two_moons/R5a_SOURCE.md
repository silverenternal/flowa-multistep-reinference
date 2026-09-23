# R5a 2D Two Moons — Source Provenance

**Paper cell:** R5a 2D Two Moons (TIE at paper R-level d_s=+0.460 at n=3; SEPARATE 2D FM ablation framework-WINS −78.25%)
**Headline:** Paper R-level verdict is TIE (d_s=+0.460 at n=3 verified Wave 209 P6 n=7 + Wave 216 P2 n=10); 2D FM ablation reads framework-WINS −78.25% at matched NFE (separate axis — not the paper R-level reading)
**Date:** 2026-09-23

## Primary data (in this directory)

| File | Description | SHA-256 anchor |
|---|---|---|
| `noise_injection_two_moons_baseline.csv` | Two Moons baseline noise-injection sweep CSV | (see `paper-data/MANIFEST.md`) |
| `noise_injection_two_moons_framework.csv` | Two Moons framework noise-injection sweep CSV | (see `paper-data/MANIFEST.md`) |
| `noise_injection_two_moons_sigma_vs_w2.png` | σ vs W₂ scatter | (PNG) |
| `noise_injection_two_moons_nfe_pareto.png` | NFE vs W₂ Pareto front | (PNG) |
| `noise_injection_two_moons_pareto_front.png` | Pareto front visualization | (PNG) |
| `wave189-p2-sota-2d-rerun/` | SOTA 2D paired-N baseline-vs-framework rerun | (directory symlink) |
| `SOURCE.md` | Wave 135 freeze headline-evidence provenance | (symlink) |

## Audit trail

- Wave 135 freeze — `docs/headline-evidence/r4_2d_two_moons_w2_m7p28pct/SOURCE.md` (Wave 135 R-cell ID = paper R5a)
- Wave 209 P6 — n=7 verification of paper R-level TIE
- Wave 216 P2 — n=10 verification of paper R-level TIE
- Wave 311 R5a reconciliation footnote — `DATA_PRESENTATION.md` §3 line 374 explicitly documents the two-readings coexistence
- `docs/r4-survey/10-sota-2d-experiment-results.md` — 2D FM ablation SOTA results (−78.25% framework-WINS)

## Honest disclosure (preserved)

R5a paper R-level verdict is **TIE** (d_s=+0.460 at n=3). The −78.25% framework-WINS is from a SEPARATE 2D FM ablation axis (matched NFE), NOT the paper R-level reading. Both readings are honestly disclosed.

## Verification

```bash
sha256sum -- R5a_2d_two_moons/*.{csv,png,md} > R5a_2d_two_moons/SHA256SUMS
```
