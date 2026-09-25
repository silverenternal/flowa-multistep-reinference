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

---

## Post-Wave-151 P5 audit reconciliation note (2026-09-14)

The prose-text audit-doc reference in this SOURCE.md (line 27) points to
`docs/audit/wave89-phase1-final.md`. **Wave 137 Phase 1 (commit `3f4a09e`)
archived all Wave 1-99 audit docs** from `docs/audit/` to
`docs/ARCHIVE/audit-waves-1-99/`. The canonical path is now:

- `docs/ARCHIVE/audit-waves-1-99/wave89-phase1-final.md` (R2 byte-stable reproduction audit)

Note: this directory (R2) does NOT have a separate `source_audit.md` file
because the SOURCE.md is self-sufficient — it cites all 6 sweep JSONs by
name (which all resolve via symlinks to `verification_outputs/`). The
Wave 135 Phase 3 (`docs/audit/wave135-headline-evidence.md`) explicitly
documents this design choice.

This note is **ADDITIVE only** — the existing prose reference above is
preserved verbatim per the Wave 137 archive invariant (no destructive
edits to historical SOURCE.md text). The headline numbers
(0.6381 → 0.6146, -0.0235, 4.05σ) are byte-stable across Waves 135-151.

See `docs/audit/wave151-headline-evidence-audit.md` for the per-R
audit ledger and fix inventory.