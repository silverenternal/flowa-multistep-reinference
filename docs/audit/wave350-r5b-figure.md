# Wave 350 P4 — R5b 4-scheduler × 3-`n_rounds` Conditional Grid Figure

**Date:** 2026-09-25
**Author:** Wave 350 P4 audit agent (paper-evidence + dataviz)
**Scope:** R5b (CIFAR-10 RF matched-NFE = 50) `n_rounds` conditional grid rendering (paper §7.6 + §7.6.1 mechanism paragraph)
**Purpose:** Visualise the 4-scheduler × 3-`n_rounds` = 12-cell conditional grid from the §7.6 mechanism paragraph as a 2-panel figure; no number changes (per Wave 268 strict-clean).

---

## 1. Executive Summary

| Item                                | Value                                                                                              |
|-------------------------------------|----------------------------------------------------------------------------------------------------|
| Renderer                            | `tools/render_r5b_conditional_grid.py` (matplotlib 3.11.2 Agg backend, ruff-clean)                  |
| Figure output                       | `docs/drafts/figure_r5b_conditional_grid.png` (167015 bytes; sha256 `c4831bcd36a83133a909eee9734a669ab8c271e3e908c6d5d8a20973ec87b615`) |
| Panel A                             | Heatmap of $\Delta\text{FID}$ % across 4 schedulers (rows) × 3 `n_rounds` (cols); diverging red/green colour-coding |
| Panel B                             | Grouped bar chart of $\Delta\text{FID}$ % vs `n_rounds` per scheduler (3 grouped bars per scheduler)|
| Paper-text additions                | **§7.6.2 ADDITIVE footnote** (paper §7.6 R5b `n_rounds` conditional grid — figure ref; no number change) |
| MANIFEST.md update                  | New figure row added (`figure_r5b_conditional_grid.png` SHA + size + role); paper-A-final.md SHA + size updated to reflect §7.6.2 ADDITIVE |
| Number-change?                      | **NO** — additive only, byte-stable (§7.6 mechanism paragraph preserved verbatim underneath)        |
| Verification gates                  | `python3 tools/check_claims_consistency.py` → "No drift detected" (PASS); `ruff check tools/render_r5b_conditional_grid.py` → "All checks passed!" (PASS); `pytest tests/test_d4_regression_vectors.py -q` → 30/30 PASS |

---

## 2. Source Data (12-cell grid, byte-stable)

The 12-cell R5b conditional grid is sourced from three independent empirical sweeps on CIFAR-10 RF at matched NFE = 50. The data is transcribed verbatim from the audit material; no values are re-derived in this Wave.

### 2.1 Source 1 — `n_rounds=1` (Wave 235 P1, `verification_outputs/wave235-p1-r5b-fix.json`)

The Wave 235 P1 R5b-fix sweep (`scripts/wave235_p1_r5b_fix_sweep.py`) ran all 4 schedulers at `n_rounds=1` against the cosine ramp baseline. Baseline FID = 454.3854 (n=200 per arm, paired-t test).

| scheduler                         | $\Delta\text{FID}$ % |
|-----------------------------------|---------------------:|
| CosineAnnealScheduler             | -1.60%               |
| CodimensionSheetScheduler         | -2.53%               |
| EvidenceDrivenScheduler           | -0.12%               |
| FreeTrajScheduler                 | -0.66%               |

### 2.2 Source 2 — `n_rounds=2` (Wave 225 P7, `verification_outputs/wave225-p7-r5b-reduced-rounds.json`)

The Wave 225 P7 reduce-rounds counterfactual (`scripts/wave225_p7_r5b_reduced_rounds.py`) ran all 4 schedulers at `n_rounds=2`. Baseline FID = 458.5809 (n=200 per arm).

| scheduler                         | $\Delta\text{FID}$ % |
|-----------------------------------|---------------------:|
| CosineAnnealScheduler             | +9.77%               |
| CodimensionSheetScheduler         | +9.79%               |
| EvidenceDrivenScheduler           | +9.83%               |
| FreeTrajScheduler                 | +16.62%              |

### 2.3 Source 3 — `n_rounds=20` (Wave 206 P6, `verification_outputs/wave206-p6-honest-negative-curve.json`)

The Wave 206 P6 honest-negative curve (`scripts/wave206_p6_cifar_rf_v4_honest_negative_curve.py`) ran all 4 schedulers at `n_rounds=20`. Baseline FID = 83.0866 (n=500 per arm; pre-EMA-fix Liu 2022 published-style inception, the load-bearing Source-A reading at matched NFE = 50).

| scheduler                         | $\Delta\text{FID}$ % |
|-----------------------------------|---------------------:|
| CosineAnnealScheduler             | +24.89%              |
| CodimensionSheetScheduler         | +25.13%              |
| EvidenceDrivenScheduler           | +24.46%              |
| FreeTrajScheduler                 | +30.65%              |

### 2.4 Compose the 12-cell grid

The 4 × 3 grid (rows = schedulers, cols = `n_rounds`):

| scheduler \ `n_rounds` |   1   |   2   |   20  |
|------------------------|------:|------:|------:|
| CosineAnnealScheduler  | -1.60 | +9.77 | +24.89 |
| CodimensionSheetScheduler | -2.53 | +9.79 | +25.13 |
| EvidenceDrivenScheduler  | -0.12 | +9.83 | +24.46 |
| FreeTrajScheduler      | -0.66 | +16.62 | +30.65 |

All 12 cells are transcribed verbatim from the three sources above; the rendered figure's Panel A heatmap and Panel B grouped bars display these exact numbers.

---

## 3. Figure Design

### 3.1 Panel A — Heatmap

- **Grid**: 4 rows (schedulers) × 3 columns (`n_rounds` = 1, 2, 20)
- **Colour map**: `RdYlGn_r` (red = baseline_wins positive, yellow ≈ zero-line, green = framework_wins negative)
- **Diverging range**: `[-30.65, +30.65]` (symmetric around zero so the WINS/REGRESSES zero-line is the visual boundary)
- **Cell annotation**: each cell shows the $\Delta\text{FID}$ % value (e.g., `-1.60%`) and the verdict badge (`[framework_wins]` or `[baseline_wins]`); annotation colour flips to white when the cell intensity exceeds 55 % of vmax

### 3.2 Panel B — Grouped Bar Chart

- **3 bars per scheduler group** (one per `n_rounds`)
- **Bar colours**: `n_rounds=1` green (`#1b7837`); `n_rounds=2` purple (`#7570b3`); `n_rounds=20` orange (`#b35806`)
- **Zero-line**: horizontal dashed grey line at y=0 (the WINS/REGRESSES boundary)
- **Bar value annotations**: $\Delta\text{FID}$ % written above (positive bars) or below (negative bars) each bar
- **Legend**: top-right corner with `n_rounds` colour key

### 3.3 Suptitle / Layout

- Suptitle: "R5b 4-scheduler × 3-`n_rounds` conditional grid on CIFAR-10 RF (matched NFE = 50)"
- Subplot panel titles: "Panel A: Delta FID % heatmap (4 schedulers × 3 n_rounds)" / "Panel B: Delta FID % vs n_rounds, grouped per scheduler"
- Figure size: 12.0 × 4.8 inches @ 150 DPI (162788 bytes initial; 167015 bytes after legend clipping fix)
- Layout: tight_layout + bbox_inches="tight" to maximise data-ink ratio

---

## 4. Paper-Text Integration (§7.6.2 ADDITIVE footnote)

The §7.6.2 ADDITIVE footnote was inserted into `docs/drafts/paper-A-final.md` immediately after §7.6.1 (R5c regime curve cross-reference). The footnote:

- **Does NOT change any number** (§7.6 mechanism paragraph preserved verbatim)
- **References the new figure** at `docs/drafts/figure_r5b_conditional_grid.png`
- **References the renderer** at `tools/render_r5b_conditional_grid.py`
- **Cross-references** the three source artifacts (`verification_outputs/wave235-p1-r5b-fix.json`, `verification_outputs/wave225-p7-r5b-reduced-rounds.json`, `verification_outputs/wave206-p6-honest-negative-curve.json`)
- **Honors the Wave 268 strict-clean rule** (additive, no destructive edit, no number change)

The exact text inserted (verbatim):

> **§7.6.2 R5b `n_rounds` conditional grid — figure (Wave 350 P4 ADDITIVE, no number change).** The 4-scheduler × 3-`n_rounds` conditional grid from the §7.6 mechanism paragraph above is rendered as a 2-panel figure at [`docs/drafts/figure_r5b_conditional_grid.png`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/figure_r5b_conditional_grid.png) (renderer [`tools/render_r5b_conditional_grid.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tools/render_r5b_conditional_grid.py); the figure's PNG sha256 is recorded in `tnnls_submission/MANIFEST.md`). **Panel A**: heatmap of $\Delta\text{FID}$ % across 4 schedulers (rows) × 3 `n_rounds` (cols) with diverging red/green colour-coding (red = `baseline_wins`, green = `framework_wins`, zero-line as the WINS / REGRESSES boundary). **Panel B**: grouped bar chart of $\Delta\text{FID}$ % vs `n_rounds` per scheduler (3 grouped bars per scheduler, coloured by `n_rounds`). The 12-cell data points are transcribed verbatim from the §7.6 mechanism paragraph above (the audit material is `verification_outputs/wave235-p1-r5b-fix.json` for `n_rounds=1`, `verification_outputs/wave225-p7-r5b-reduced-rounds.json` for `n_rounds=2`, and `verification_outputs/wave206-p6-honest-negative-curve.json` for `n_rounds=20`; cross-referenced in [`docs/CLAIMS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md) CLM-070 R5b honest-negative row); the rendering uses matplotlib's `Agg` backend (no GUI dependency, no InceptionV3 activation) and is byte-stable under repeated invocation. The figure visualises the `n_rounds = 1` → `n_rounds ≥ 2` transition boundary described in §7.6.1 mechanism; the empirical regime-dependence is preserved verbatim per the Wave 268 strict-clean "no number change" rule.

---

## 5. MANIFEST.md Updates

Two additive rows / updates were made to `tnnls_submission/MANIFEST.md`:

### 5.1 New figure row — `figure_r5b_conditional_grid.png`

| `../docs/drafts/figure_r5b_conditional_grid.png` | 167015 | `c4831bcd36a83133a909eee9734a669ab8c271e3e908c6d5d8a20973ec87b615` | **Wave 350 ADDITIVE Figure 2 (auxiliary 2-panel)** — R5b 4-scheduler × 3-`n_rounds` conditional grid 2-panel PNG (Panel A: heatmap of $\Delta$ FID % across 4 schedulers × 3 `n_rounds` with diverging red/green colour-coding; Panel B: grouped bar chart of $\Delta$ FID % vs `n_rounds` per scheduler with 3 grouped bars per scheduler); byte-stable render of the §7.6 mechanism paragraph + Wave 235 P1 + Wave 225 P7 + Wave 206 P6 audit material (12-cell grid transcribed verbatim, 4 schedulers × 3 `n_rounds` = 12 cells); matplotlib Agg backend; renderer at `tools/render_r5b_conditional_grid.py` (matplotlib 3.11.2, ruff-clean); referenced from `paper-A-final.md` §7.6.2 |

### 5.2 `paper-A-final.md` row update — content description + SHA + size

| field | pre-Wave-350-P4 | post-Wave-350-P4 |
|---|---|---|
| size (bytes) | 155353 | 157204 |
| sha256 | `c7929b5a1115cbc3101b81837b54a41a1e065f743d6139da6a2d2bf3e5afbc8e` | `b1548b3cb8b44b0d2eea7f2168adb190b4069a7c3e9e06a3027afbf507a5cbb7` |
| content diff | "Wave 350 ADDITIVE: §6.6 Theorem 5 ... + §10.9.2 Theorem 5 partial close-out footnote" | "+ §7.6.2 R5b `n_rounds` conditional grid figure (Wave 350 P4 ADDITIVE 2-panel figure ref)" appended |

The MANIFEST.md self-row SHA (line 23) is preserved at the freeze-marker pre-edit hash `5812d5f4...` per the self-referencing-freeze convention documented in that row's content description.

---

## 6. Verification

| Verification gate                                         | Result      | Notes                                                                                  |
|------------------------------------------------------------|-------------|----------------------------------------------------------------------------------------|
| `python3 tools/check_claims_consistency.py`                | **PASS**    | "No drift detected." — 61 active claims, 0 provisional, 2 deprecated unchanged        |
| `pytest tests/test_d4_regression_vectors.py -q`            | **30/30 PASS** | D.4 byte-stable regression suite green                                                  |
| `ruff check tools/render_r5b_conditional_grid.py`          | **PASS**    | "All checks passed!" — 0 findings in the new renderer                                   |
| `python3 tools/render_r5b_conditional_grid.py`             | **PASS**    | renders to 167015 bytes; sha256 byte-stable on repeated invocation (deterministic)    |
| `mkdocs build --strict`                                    | deferred    | not run (no `mkdocs.yml` / `docs/` API-ref change in this Wave 350 P4; only paper-A-final.md content added) |

---

## 7. Honesty & Provenance Disclosures

1. **No number change**: the 12-cell grid data is transcribed verbatim from the three source JSON files (Wave 235 P1 rounds1, Wave 225 P7 rounds2, Wave 206 P6 n_rounds=20). The §7.6 mechanism paragraph in `paper-A-final.md` is preserved verbatim; only an ADDITIVE §7.6.2 footnote referencing the figure was inserted after §7.6.1.
2. **Pre-EMA-fix disclosure**: the `n_rounds=20` row uses pre-EMA-fix (Liu 2022 published-style) inception features from Wave 206 P6's Source-A reading (matched NFE = 50 baseline_fid=83.0866 vs framework 103.41-108.55); this is the load-bearing Source-A matching the §7.6 baseline 83.09 vs framework 103.41-108.55 reading. The Wave 191 P2 (n=1000 chunked FID), Source-B (n=200 post-EMA-fix), and Source-C readings preserve different magnitudes but the same 4-scheduler trend (all 4 schedulers REGRESS at `n_rounds=20`, all 4 schedulers WINS at `n_rounds=1`).
3. **Bidirectional SHA pinning**: the rendered PNG is sha256-stamped both in the MANIFEST figure row and in the §7.6.2 footnote (via the MANIFEST reference). Reviewers re-verify with `sha256sum docs/drafts/figure_r5b_conditional_grid.png`.
4. **Vendor byte-stability**: per AGENTS.md hard guardrail #1, no vendored upstream code (under `data/FlowMol3/`, `data/LineageFlow/`, `data/Kanzi/`, `data/HiDream-I1/`, `data/GraphBFN/`, `data/Lumina-Image-2.0/`, `data/ProtBFN-AbBFN/`, `data/Wan2.2/`, `data/FreqFlow/`) was modified. Verified via `git status` — only `tools/render_r5b_conditional_grid.py` (NEW), `docs/drafts/figure_r5b_conditional_grid.png` (NEW), `docs/drafts/paper-A-final.md` (MODIFIED ADDITIVE §7.6.2), `tnnls_submission/MANIFEST.md` (MODIFIED ADDITIVE 2 rows), and this audit doc are touched.
5. **NO-PUSH policy**: per AGENTS.md hard guardrail #3, no `git push` was performed; this Wave 350 P4 commit is local-only, USER AUTHORIZED, awaiting user gating before push (consistent with `todo/PUSH-READY.md`).

---

## 8. Files Modified (Wave 350 P4)

| File                                                  | Mode       | Reason                                                            |
|-------------------------------------------------------|------------|-------------------------------------------------------------------|
| `tools/render_r5b_conditional_grid.py`                | **NEW**    | matplotlib Agg renderer for the 4×3 conditional grid              |
| `docs/drafts/figure_r5b_conditional_grid.png`         | **NEW**    | rendered 2-panel figure (167015 bytes; sha256 `c4831bcd...`)     |
| `docs/drafts/paper-A-final.md`                        | MODIFIED   | ADDITIVE §7.6.2 footnote inserted after §7.6.1 (no number change) |
| `tnnls_submission/MANIFEST.md`                        | MODIFIED   | ADDITIVE 1 new figure row + paper-A-final.md row content + SHA   |
| `docs/audit/wave350-r5b-figure.md`                    | **NEW**    | this audit document                                              |

---

## 9. References

- **`docs/drafts/paper-A-final.md` §7.6 + §7.6.1 + §7.6.2** (canonical paper-text integration; §7.6 mechanism paragraph is the data source, §7.6.1 is the cross-reference to R5c, §7.6.2 is the new figure ref)
- **`docs/audit/wave336-r5b-mechanism.md`** (Wave 336 R5b `n_rounds` Conditional Boundary — Mechanism Analysis; the source code-path verification for the `n_rounds = 1` vs `n_rounds ≥ 2` mechanism)
- **`docs/audit/wave350-thm5.md`** (Wave 350 P2 Theorem 5 closed-form attenuation bound — paper §6.6; the theoretical counterpart to this empirical figure)
- **`verification_outputs/wave235-p1-r5b-fix.json`** (Wave 235 P1 R5b-fix sweep at `n_rounds=1` baseline)
- **`verification_outputs/wave225-p7-r5b-reduced-rounds.json`** (Wave 225 P7 reduce-rounds counterfactual at `n_rounds=2`)
- **`verification_outputs/wave206-p6-honest-negative-curve.json`** (Wave 206 P6 honest-negative curve at `n_rounds=20`)
- **`docs/CLAIMS.md` CLM-070** (R5b honest-negative row; the cross-reference pointer)
- **`tnnls_submission/MANIFEST.md` rows for `figure_r5b_conditional_grid.png` + `paper-A-final.md`** (this Wave 350 P4 addition)
