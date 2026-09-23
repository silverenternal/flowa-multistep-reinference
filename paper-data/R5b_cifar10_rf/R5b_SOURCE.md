# R5b CIFAR-10 RF — Source Provenance

**Paper cell:** R5b CIFAR-10 RF v2 FID (matched NFE=50, n_rounds=1)
**Headline:** ΔFID = −1.60% to −2.53% framework-WINS at n_rounds=1; +9.77% to +30.19% at n_rounds≥2 (REGRESSES, documented honest-negative)
**Date:** 2026-09-23 (Wave 235 P1 reversal)

## Primary data (in this directory)

| File | Description | SHA-256 anchor |
|---|---|---|
| `wave191-p2-cifar10-n1000.json` | CIFAR-10 RF N=1000 4-arm sweep JSON | `a3c5bea08e44018eabaa6e8332ac7de211de70f48607cf983143b87302d5b0dd` |
| `baseline_samples.npz` | CIFAR-10 RF baseline samples N=1000 | `f87247276fb6850313b091485af0962d43397654626db74c1be8e9b4163b0e96` |
| `freetraj_samples.npz` | CIFAR-10 RF free-trajectory arm N=1000 | `ac68231c7f0628ee38a9bf279b0ab8204e8f5c85536eb48706aa851a2592e806` |
| `cosineanneal_samples.npz` | CIFAR-10 RF cosine-anneal arm N=1000 | `ff2b1e822d311925f2a78bc590019c247f3b2bca3cdacd1530e9fa9bc391f062` |
| `codimensionsheet_samples.npz` | CIFAR-10 RF codimension-sheet arm N=1000 | `49f22d5543b31fa2259c6be3287122531289a1debd90d0aa490f0876a2df67f1` |
| `evidencedriven_samples.npz` | CIFAR-10 RF evidence-driven arm N=1000 | `252a71a96d64a09867703db7b2e04e3687feb828f08828ad06580ee24c0a05a6` |
| `wave235-p1-r5b-fix.csv` | Wave 235 P1 reversal evidence CSV | `32d72a9bf00b3f7e9a2d27fda34866c2582a00959a950f232484b24e96e86106` |
| `wave235-p1-r5b-fix.json` | Wave 235 P1 reversal evidence JSON | (see `paper-data/MANIFEST.md`) |
| `per_round_metrics.csv` | Per-round (n_rounds=1..4) FID summary | `7b0f99e18597b2f1358c6244e9dcd4d15a9cbb664c7965afec2b0d7f5fadc17f` |
| `comparison.md` | CIFAR N=200 NFE=50 EMA-corrected comparison | `e51720f3f872e142b95912264107340105be70bd503c8a68bd3dcb48ad0a617d` |
| `SOURCE.md` | Wave 135 freeze headline-evidence provenance | (symlink) |

## Audit trail

- Wave 235 P1 — reversal evidence: `verification_outputs/wave235-p1-r5b-fix.{csv,json}`
- Wave 191 P2 — initial N=1000 4-arm sweep
- Wave 175 P3 + Wave 178 P6 — sanity sweeps
- `docs/DATA_PRESENTATION.md` §2.5 — paper-cited R5b row
- `docs/CLAIMS.md` CLM-039/040 — R5b STRONG conditional at n_rounds=1

## Honest disclosure (preserved)

R5b is STRONG conditional: framework-WINS at n_rounds=1, REGRESSES at n_rounds≥2. The matched-NFE=50 reading is the headline; n_rounds≥2 is documented as honest-negative in paper §10.5 supplementary and DATA_PRESENTATION.md §2.5.

## Verification

```bash
sha256sum -- R5b_cifar10_rf/*.{json,csv,jsonl,md,npz} > R5b_cifar10_rf/SHA256SUMS
```
