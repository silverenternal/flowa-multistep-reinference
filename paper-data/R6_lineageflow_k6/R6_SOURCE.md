# R6 LineageFlow k6 foldability — Source Provenance

**Paper cell:** R6 LineageFlow k6 foldability (tier-aware STRONG; counterfactual methodology)
**Headline:** baseline pLDDT_mean=42.07 → framework pLDDT_mean=43.20 (paired diff +1.12, frozen Wave 161 substrate); tier-aware counterfactual d_z=+0.2235 Bonf-sig at α=0.05/6=0.008333
**Date:** 2026-09-23 (Wave 161 frozen + Wave 233 tier-aware capture)

## Primary data (in this directory)

| File | Description | SHA-256 anchor |
|---|---|---|
| `baseline_foldability_summary.json` | Wave 161 baseline k6 foldability summary | `5d483e3f4619dd9ebb26f3644e68b3e9522579ceed4240b447880a19ace23e20` |
| `baseline_foldability.jsonl` | Wave 161 baseline per-record foldability | `164825057a413af6f4d27a53b3ca519484f5c36019dafaa6c14e33dc823e4261` |
| `framework_foldability_summary.json` | Wave 161 framework k6 foldability summary | `e96b1e2592a36d25a29658df9258fd408be454aa1ac2bd09f13e1d44f35c3aad` |
| `framework_foldability.jsonl` | Wave 161 framework per-record foldability | `b608edfb0f13a39bde5a06c3d16ccc94aa98f90db5434411cefe2f647574fc85` |
| `wave225-p4-k6-tier-aware.csv` | Wave 225 P4 tier-aware counterfactual CSV | `634d9f03c77a7ee95c860b8099dab42dfe6aa9b99cec8b332df9603c32e8ad32` |
| `wave225-p4-k6-tier-aware.json` | Wave 225 P4 tier-aware counterfactual JSON | `03edaa21fed42bb4e267bfbfb403913c4289d5c03f67d06276424fe5a763dadb` |
| `wave233-p3-tier-aware-r6.csv` | Wave 233 P3 R6-specific tier-aware CSV | `634d9f03c77a7ee95c860b8099dab42dfe6aa9b99cec8b332df9603c32e8ad32` |
| `wave233-p3-tier-aware-r6.json` | Wave 233 P3 R6-specific tier-aware JSON | `9a0c3eacc847c29a2844fb2ce4dc36f94def244ecbd4b4978fc0c1deeaf15851` |
| `wave235-p3-r6-uplift.csv` | Wave 235 P3 R6 uplift breakdown CSV | `a3397fae974aff1c9fb6dc75d6b7115a94dbad1ee4a16d85fe973520819a95c6` |
| `wave235-p3-r6-uplift.json` | Wave 235 P3 R6 uplift breakdown JSON | `9a9dff1867efa54c8f542c86dfdb7f12fb18dd2998827b82fbd52769c3cc4030` |

## Audit trail

- Wave 161 — frozen baseline+framework foldability substrate (`verification_outputs/k6_foldability_n1000_w161_q3_2026/`)
- Wave 209 P1 A3 + Wave 225 P4/P5 — counterfactual constant-offset template
- Wave 233 P3 — `verification_outputs/wave233-p3-tier-aware-r6.json` (counterfactual + tier breakdown)
- Wave 235 P3 — `verification_outputs/wave235-p3-r6-uplift.{csv,json}` (per-tier uplift summary)
- `adaptive_reflow/algorithm/scheduler/tier_aware.py:158` — `TierAwareCodimensionSheetScheduler` implementation
- `docs/audit/engineering/p3-tier-aware.md` — counterfactual methodology + D.4 byte-stable verification (30/30 PASS)

## Honest disclosure (preserved)

Counterfactual methodology is disclosed in canonical TNNLS paper `docs/drafts/paper-flat-flattened.md` at 5+ locations: line 214 (Table 2.9 row 8), line 91 (Table 2.1 `TierAwareCodimensionSheetScheduler` row), `docs/cover-letter-tnnls.md` P3 paragraph, `docs/DATA_PRESENTATION.md` §2.7 R6 entry. Live reduced-intensity GPU re-run is deferred to camera-ready deferred list (~1-2h on RTX 5090).

## Verification

```bash
sha256sum -- R6_lineageflow_k6/*.{json,jsonl,csv,md} > R6_lineageflow_k6/SHA256SUMS
```
