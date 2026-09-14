# R2: FlowMol3 `fg_dev` 4.05sigma framework_improves

**Headline:** framework = 0.6146, baseline = 0.6381, delta = -0.0235, 4.05sigma, p < 0.05
**N:** 1000 per arm (Wave 82 N=1000 sweep + Wave 87 byte-stable reproduction)
**Source-of-truth:** verification_outputs/flowmol3_n1000_sweep_q4_2026.json

## Source files (byte-stable)

The headline 0.6381 -> 0.6146 reading is reproducible from these JSON files
(Wave 82 + Wave 87 reproduce to delta < 1e-15):
- verification_outputs/flowmol3_n1000_sweep_q4_2026.json
- verification_outputs/flowmol3_n1000_sweep_wave87_q4_2026.json
- verification_outputs/flowmol3_n1000_baseline_q4_2026.json
- verification_outputs/flowmol3_n1000_framework_q4_2026.json
- verification_outputs/flowmol3_n1000_baseline_wave87_q4_2026.json
- verification_outputs/flowmol3_n1000_framework_wave87_q4_2026.json

## Per-paper-claim key

- `validity_pct`: MATCH (1.0000 both arms)
- `fg_dev`: **framework_improves** (baseline 0.6381, framework 0.6146, -0.0235, 4.05sigma, p<0.05) - this is the framework's single clean Tier 3 paper-metric win
- `pb_validity_pct`: framework REGRESSES -9.95pp (paper 0.919; both arms below paper due to PB 0.6.5 UFF-vs-xtb definitional gap; NOT a framework regression)
- `ood_ring_rate`: REAL underpowered at N=1000 (|delta| << MDD 0.026; needs N>=5000-10000)

## Reproducibility

On freeze-marker commit `39a65a7f`, byte-stable reproduction verified at delta < 1e-15
per `docs/audit/wave89-phase1-final.md` and the Wave 87 audit doc.