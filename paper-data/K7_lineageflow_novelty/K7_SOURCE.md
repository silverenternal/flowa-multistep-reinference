# K7 LineageFlow Novelty — Source Provenance

**Paper cell:** K7 LineageFlow novelty (SUPP / direction-INVERTED)
**Headline:** W166 P3 canonical in-git evidence (sha256 61dd70fa) shows framework 12.6× LESS Pfam-novel than baseline at pctid<30% twilight-zone (direction OPPOSITE of paper's framework-WINS claim); W280 P d_z=+∞ is a numerical artifact (driver subsamples baseline.fasta only)
**Date:** 2026-09-23 (Wave 280 P + W166 P3 capture)

## Primary data (in this directory)

| File | Description | SHA-256 anchor |
|---|---|---|
| `summary.json` | Wave 280 P K7 (numerical-artifact driver) summary | (see `K7_lineageflow_novelty/SHA256SUMS`) |
| `SHA256SUMS` | Wave 280 P K7 sidecar SHA-256 ledger | (sidecar) |
| `seed42/` `seed43/` `seed44/` | Wave 280 P K7 per-seed sub-directories | (directory symlinks) |
| `W166_P3_canonical_novelty.json` | **W166 P3 canonical in-git evidence** (the real K7 reading) | `91f054f40bddf0a767b339026e7389377e37ed47984ecb290716ccd0daa9f292` |
| `novelty_results_full.json` | W166 P3 full per-record novelty JSON | `61dd70fab83e1a4a5ad6874ade10fe88f3e4653ba8da2d8ca12ec61d4605dae0` |
| `sanity_n5_loose.m8` (baseline) | W166 P3 baseline MMseqs2 loose-threshold hits | `0f7702aa4eaa26efa7b017999ccddce471eb74061a0770fa8bba1c7760b96d85` |
| `sanity_n5_loose.m8` (framework) | W166 P3 framework MMseqs2 loose-threshold hits | `5886075cf010409b58181da24a44513ef99db993a00ba305802b9a4f32029307` |

## Audit trail

- Wave 280 P — `verification_outputs/wave280-k7/` (W280 P driver subsamples baseline.fasta only — d_z=∞ is a numerical artifact, NOT framework-vs-baseline)
- Wave 166 P3 — `verification_outputs/novelty_pctid_w166_q3_2026/` (CANONICAL in-git evidence, sha256 61dd70fa)
- Wave 297 P6 + Wave 308 fast-path — K7 demotion from MAIN STRONG → §10 supplementary
- Wave 306-11-cell-alignment.md line 81 — W280 P numerical artifact identified + discarded
- Wave 165 P7 — zinc-finder / DNA-binding biological reframing (3 zinc-finger families absorb 87.4% of framework hits)

## Honest disclosure (preserved)

K7 is SUPP / direction-INVERTED. W280 P d_z=+∞ is a numerical artifact (NOT real). W166 P3 is the canonical reading: framework 12.6× LESS Pfam-novel than baseline at pctid<30% twilight-zone. Positive reading: W165 P7 zinc-finger/DNA-binding — framework sequences recapitulate known Pfam family structure (3 zinc-finger families absorb 87.4% of framework hits) — biologically meaningful sequences that match known Pfam families.

User's Tier 1 directive "降级而非重跑" (demote-not-rerun) cited verbatim in paper §10.6.5.

## Verification

```bash
sha256sum -- K7_lineageflow_novelty/*.{json,md} > K7_lineageflow_novelty/SHA256SUMS.new
```
