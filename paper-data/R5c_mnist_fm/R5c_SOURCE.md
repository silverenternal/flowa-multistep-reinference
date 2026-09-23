# R5c MNIST FM — Source Provenance

**Paper cell:** R5c MNIST FM FID (smoke ckpt STRONG; production ckpt PARTIAL direction-FLIPS)
**Smoke ckpt headline:** Baseline FID 29.49 → Framework FID 23.39 (−28.43%, d_z=−13.175, smoke ckpt N=1000)
**Production ckpt headline:** per-seed d_z = [+1.5463, +1.3312, +1.0243] ALL POSITIVE = framework REGRESSES +10.37% (Wave 280 P §10 disclosure)
**Date:** 2026-09-23 (Wave 280 P capture)

## Primary data (in this directory)

| File | Description | SHA-256 anchor |
|---|---|---|
| `wave191-p3-mnist-n1000.json` | Smoke ckpt 4-arm N=1000 sweep JSON | `a5270a0aacc99551c3ed15304f00d68baa41ac3f6012e3ad26f2dbbe96dc5e06` |
| `baseline_samples.npz` | MNIST FM baseline samples N=1000 | `f7eb8c3536426c70faae951803fd84814bdb3900aed5b7adfebd537e6c3fe290` |
| `cosine_samples.npz` | MNIST FM cosine-arm samples N=1000 | `6b44d91efb097d7456d39f7151c851a7d477ba16a53b0aef0e0333b1f90baa45` |
| `codimension_sheet_samples.npz` | MNIST FM codimension-sheet arm N=1000 | `eb6cf305d88c536ba223844ccb08208ae3c797a972b93d6c6a12de77491aeeac` |
| `evidence_driven_samples.npz` | MNIST FM evidence-driven arm N=1000 | `be0d58de1e91d972fa03b01e0477bda5065534870cd09079f7c468b8bf698327` |
| `aggregate.json` | Wave 280 P production ckpt 3-seed aggregate | `806da3905748d51194713fd140c8a6258aaddb9dcdbbd65579fe6d4293947221` |
| `SOURCE.md` | Wave 135 freeze headline-evidence provenance | (see `paper-data/MANIFEST.md`) |
| `wave280-p-r5c-SHA256SUMS.txt` | Wave 280 P R5c sidecar SHA-256 sums | (sidecar) |

## Audit trail

- Wave 280 P — `verification_outputs/wave280-p-r5c/aggregate.json` (sha256 806da390)
- Wave 191 P3 — `verification_outputs/wave191-p3-mnist-n1000/` 4-arm N=1000 smoke ckpt
- Wave 135 freeze — `docs/headline-evidence/r6_mnist_fm_fid_m15p01pct/SOURCE.md` (Wave 135 R-cell ID = paper R5c)
- Production ckpt recipe: `tools/materialize_mnist_fm.py:71-82 PRODUCTION_RECIPE` (sha256 27e2bb6c, 75472 bytes, 3 epochs, base_channels=16, full 60K images)

## Honest disclosure (preserved)

Direction-INVERSION on production ckpt is disclosed in canonical TNNLS paper `docs/drafts/paper-flat-flattened.md` at 5+ locations: lines 213 (Table 2.9 row 7b), 323, 393 (§3.6 R5 cells family), 614 (§10.4 MnistFmAdapter), 673 (§7.1 Table 7.1 row 6 R5c), 696 (§7.2 verdict table), 781 (§7.9 paper bullet). Smoke ckpt remains STRONG; production ckpt is PARTIAL.

## Verification

```bash
sha256sum -- R5c_mnist_fm/* > R5c_mnist_fm/SHA256SUMS
```

All hashes must match those in `paper-data/MANIFEST.md` and the `wave280-p-r5c-SHA256SUMS.txt` sidecar.
