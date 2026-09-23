# R3 FlowMol3 fg_dev — Source Provenance

**Paper cell:** R3 FlowMol3 fg_dev (PARTIAL; 3-seed direction-consistency BLOCKED at vendor level)
**Headline:** Wave 87 seed=42 N=1000 batched direction framework-WINS −0.0235 (4.05σ); 3-seed reproducibility blocked (Wave 109.C DGL + Wave 244-262 vendored revert CLM-076/077)
**Date:** 2026-09-23 (Wave 235 P4 3-seed sweep)

## Primary data (in this directory)

| File | Description | SHA-256 anchor |
|---|---|---|
| `wave206-p3-flowmol3-n1000.csv` | Wave 206 P3 single-seed FlowMol3 N=1000 CSV | `f1abacbdee70f8734ec1300b6f1c769c7b15366adffe2d5002efb4381cd3bb80` |
| `wave206-p3-flowmol3-n1000.json` | Wave 206 P3 single-seed FlowMol3 N=1000 JSON | `c20a9183931c2b10a3074981204676c83f630ebfd95a60afa248531261c42f36` |
| `wave235-p4-flowmol3-3seed.csv` | Wave 235 P4 3-seed direction-consistency CSV | `4ff2a7eeb914d859a2e798d7f4c83968d5919c9995f38f8be5a77ffcc1f31c73` |
| `wave235-p4-flowmol3-3seed.json` | Wave 235 P4 3-seed direction-consistency JSON | `4ef06440229ec31ca49b0aeceb8f34746dcd7e3f441552d317c6bd7d3cd3a120` |
| `wave235-p4-flowmol3-3seed-per-record.csv` | Wave 235 P4 3-seed per-record CSV | `a20d902e454707dfae1302541eada99f5e58655b62a846bab089c7539d8b2977` |
| `wave240-p2-flowmol3-direction.csv` | Wave 240 P2 direction probe | `c4f5b0b3ad5d8839919dddca22834ae89ea993d2d39c491be514404f040e54d5` |
| `wave242-p2-flowmol3-direction.csv` | Wave 242 P2 direction probe (Wave 109.C vendor revert) | `4edb517cc8080b405ac5d24aa9d753228b1abdec119cc41e2b1f79432e4a632b` |
| `flowmol3_n1000_sweep_q4_2026.json` | Wave 87 sweep summary JSON | (see `verification_outputs/MANIFEST.md`) |
| `flowmol3_n1000_baseline_q4_2026.json` | Wave 87 baseline summary JSON | (see `verification_outputs/MANIFEST.md`) |
| `flowmol3_n1000_framework_q4_2026.json` | Wave 87 framework summary JSON | (see `verification_outputs/MANIFEST.md`) |
| `SOURCE.md` | Wave 135 freeze headline-evidence provenance | (symlink) |

## Audit trail

- Wave 87 — `flowmol3_n1000_*_q4_2026.json` (single-seed batched DGL 4.05σ)
- Wave 109.C — DGL 2.4.0 batched-path bug identified
- Wave 235 P4 — 3-seed sweep attempt (direction-inconsistent at single_mol path)
- Wave 244-262 — vendored DGL revert (CLM-076/077)
- `docs/CLAIMS.md` CLM-076/077 — vendor-blocked honest disclosure

## Honest disclosure (preserved)

R3 is PARTIAL: single-seed framework-WINS at batched DGL path; 3-seed direction-consistency BLOCKED at vendor level. Seed=44 framework arm NOT run in budget (single_mol path due to DGL batched-path bug).

## Verification

```bash
sha256sum -- R3_flowmol3_fgdev/*.{csv,json,md} > R3_flowmol3_fgdev/SHA256SUMS
```
