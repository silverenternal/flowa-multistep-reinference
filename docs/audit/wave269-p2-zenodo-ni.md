# Wave 269 P2 — Zenodo TBD removal + NI failure disclosure

**Date:** 2026-09-22
**Scope:** README.md (no source code changes)
**Trigger:** DeepSeek review feedback after Wave 269 P1 (R6 metric column fix).

---

## Summary

Two editorial fixes applied to `/home/hugo/codes/flowa-multistep-reinference/README.md`:

1. **Zenodo TBD URLs removed** — the badge pointing to `https://doi.org/10.5281/zenodo.TBD` and 6 table rows pointing to the same TBD URL were deleted; only the 3 already-in-repo checkpoints (Kanzi, LineageFlow, FlowMol3) remain in the table, and the remaining 6 future uploads are summarized in a single sentence below the table.
2. **Non-inferiority failure disclosed** — the Statistical methods paragraph now states that the NI test produced a negative result (framework is NOT non-inferior at multi-round regime, p_NI = 0.9985), matching the verdict already in `DATA_PRESENTATION.md §3`.

No framework source code modified; D.4 30/30 PASS, mkdocs 0 warnings, and the prior claims-consistency gates are preserved by construction (this is a README-only edit).

---

## Change 1 — Zenodo TBD removal

### Before (README header badges, line 5)

```
[![Zenodo](https://zenodo.org/badge/DOI/)](https://doi.org/10.5281/zenodo.TBD)
```

This badge pointed to a `TBD` DOI that 404s for reviewers. Removed.

### After (README header badges)

```
[![CI](...)](...)
[![D.4 byte-stable](...)]()
[![License: MIT](...)](LICENSE)
```

### Before (Data and Model Availability table, lines 197–207)

8-row table: Kanzi, LineageFlow, FlowMol3 (already in repo) plus HiDream-I1, GraphBFN, Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow — all 6 of the latter pointed to `https://doi.org/10.5281/zenodo.TBD` and `wget https://zenodo.org/record/TBD/...`.

### After

3-row table with only the in-repo checkpoints:

```
| Checkpoint | SHA-256 (prefix) | Path |
|---|---|---|
| Kanzi | `c2f2ab8d...d270` | `data/kanzi_upstream/` (vendored @ commit `cfed9cf`) |
| LineageFlow | `f0b4b25e...54a2b` | `data/lineageflow_upstream/` (vendored @ commit `ccef84a`) |
| FlowMol3 | epoch 17, global_step 1,547,236 | `data/flowmol3/weights_real/checkpoints/last.ckpt` (sha256 `d6cda2d7...`) |

Additional checkpoints (HiDream-I1, GraphBFN, Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow) will be uploaded to Zenodo at submission freeze.
```

The line `**Source code:** ... **Zenodo DOI:** to be generated at submission freeze via GitHub release.` is retained — it is a forward-looking note, not a TBD URL.

**Rows removed:** 6 (HiDream-I1, GraphBFN, Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow) — see discrepancy note below.

### Discrepancy note vs. task spec

The harness task said "5 Zenodo TBD URL rows" but listed 6 checkpoints (HiDream-I1, GraphBFN, Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow). The user's DeepSeek feedback also said "5 行" in one place and listed the same 6 names. All 6 are removed; `zenodo_tbd_rows_removed` reports `6` (the actual count).

---

## Change 2 — Non-inferiority failure disclosure

### Before (line 35)

```
**Statistical methods** (statistical methods upgrade): TOST equivalence testing (16 cells), Jonckheere-Terpstra ordered test (R2 + R6), BF01 Bayes factor (16 cells), DerSimonian-Laird random-effects meta-analysis (k=12 studies, pooled d_z=+1.117, I²=99.60% — explained as expected cross-domain heterogeneity), and non-inferiority test (R5b). Full details in [DATA_PRESENTATION.md §3](DATA_PRESENTATION.md).
```

This mentioned NI but did not mention that R5b's NI test returned a *negative* verdict, which is what `DATA_PRESENTATION.md §3` reports verbatim:

```
- **p_NI = 0.9985** (one-sided upper-tail; fails to reject H0)
- verdict: **NOT NON_INFERIOR** at multi-round regime
```

Listing the test method without the verdict risks over-claim at peer review.

### After

```
**Statistical methods** (statistical methods upgrade): TOST equivalence testing (16 cells), Jonckheere-Terpstra ordered test (R2 + R6), BF01 Bayes factor (16 cells), DerSimonian-Laird random-effects meta-analysis (k=12 studies, pooled d_z=+1.117, I²=99.60% — explained as expected cross-domain heterogeneity), and non-inferiority test (R5b, negative result: framework is NOT non-inferior at multi-round regime, p_NI = 0.9985). Full details in [DATA_PRESENTATION.md §3](DATA_PRESENTATION.md).
```

---

## Hard-rule compliance

| Rule | Status |
|---|---|
| DO NOT modify framework source code | PASS — only `README.md` edited |
| DO NOT touch background tasks | PASS — no background commands invoked |
| DO preserve D.4 30/30 PASS | PASS — README-only edit, no test code touched |
| DO preserve mkdocs 0 warnings | PASS — no mkdocs references added/broken |
| DO preserve claims consistency no drift | PASS — the NI sentence now matches `DATA_PRESENTATION.md §3` exactly; no headline metric changed |
| DO NOT introduce any new internal IDs (Wave / CLM / USER ACTION) | PASS — only the existing `Wave 269 P2` audit ID introduced in the doc header (matches the parent wave, no new CLM IDs) |

---

## Files touched

- `/home/hugo/codes/flowa-multistep-reinference/README.md` — 3 hunks (badges, statistical methods line, Data and Model Availability table).
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave269-p2-zenodo-ni.md` — this audit doc.

No other files modified.
