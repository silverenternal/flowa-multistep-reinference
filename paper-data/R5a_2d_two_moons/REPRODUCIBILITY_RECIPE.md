# R5a 2D Two Moons W₂ — Reproducibility Recipe

**Cell:** R5a 2D Two Moons W₂ (paper R-level TIE; corroborated at n=10 paired seeds under 4 statistical conventions)
**Headline:** Paper R-level d_s = +0.460 at n=3 unpaired (Wave 189 P2); corroborated at n=10 paired seeds by Wave 351 P2 — unpaired d_s = +1.011, paired d_z = +0.845, Hedges g = +0.773, DerSimonian-Laird random-effects meta-d_z = +0.844 (p = 0.0007); all classify as **TIE** under Wave 195 P1 verdict-precedence rule (|Δ| = 0.0091 < min_effect_size = 0.01 floor).
**Date:** 2026-09-27 (Wave 363 P1 — reproduction recipe authored)
**Methodology disclosure:** Counterfactual-on-frozen-substrate for the n=10 paired-t extension (the Wave 216 P2 per-seed CSV is already on disk and is the canonical input; no GPU re-run required for the headline); live 2D FM NFE=100 sweep is the original Wave 189 P2 source.

---

## (a) Headline metric — R5a 2D Two Moons W₂ verdict persistence at n=10

R5a is the **single TIE cell** in the paper R-level verdict distribution (CLM-060 / Wave 195 P2 row 4: 0 SUPPORTED / 1 REGRESSES / **1 TIE** / 6 UNDERPOWERED / 0 NOT_SIGNIFICANT). The TIE verdict is preserved at every extension of the canonical seed ladder (`[0, 1, 2, 3, 4, 5, 6, 43, 44, 45]`) and persists under **four independent statistical conventions**:

| Convention | Effect size | p-value (Bonferroni) | Verdict |
|---|---|---|---|
| Unpaired Cohen's d_s (Welch) | **+1.011** | 0.258 | **TIE** (Δ = +0.0091 < min_effect_size = 0.01) |
| Paired Cohen's d_z (within-subject) | **+0.8452** | 0.179 | **TIE** (same |Δ| floor) |
| Hedges g (small-sample corrected) | **+0.7728** | 0.179 | **TIE** (same |Δ| floor) |
| DerSimonian-Laird random-effects meta-d_z (k=10) | **+0.8437** | **0.0007** | **TIE** at min_effect_size floor (significant at conventional α but Δ < 0.01) |

### Per-seed breakdown (n=10, CosineAnnealScheduler primary arm, N=1000 records/seed, NFE=100)

| seed | framework W₂ | baseline W₂ | diff (framework − baseline) | per-seed d_z |
|---|---|---|---|---|
| 0 | 0.074679 | 0.078995 | -0.004316 | -0.4028 |
| 1 | 0.071267 | 0.066503 | +0.004764 | +0.4446 |
| 2 | 0.073442 | 0.067280 | +0.006162 | +0.5751 |
| 3 | 0.077280 | 0.067920 | +0.009360 | +0.8736 |
| 4 | 0.082968 | 0.081613 | +0.001355 | +0.1265 |
| 5 | 0.083770 | 0.059151 | +0.024619 | +2.2978 |
| 6 | 0.086952 | 0.064610 | +0.022342 | +2.0852 |
| 43 | 0.082761 | 0.078594 | +0.004167 | +0.3889 |
| 44 | 0.096742 | 0.073088 | +0.023654 | +2.2077 |
| 45 | 0.090371 | 0.091919 | -0.001548 | -0.1445 |

DL random-effects meta-analysis: k=10, tau²=0.6181, tau=0.7862, I²=99.8%, z-stat=+3.389, 95% CI=[+0.3557, +1.3316]. The DL p=0.0007 is **statistically significant at conventional α=0.05** but the absolute effect magnitude Δ=0.0091 is **below the pre-specified min_effect_size=0.01 floor**, so Wave 195 P1 verdict-precedence rule 1 classifies the cell as **TIE** (TIE > NOT_SIGNIFICANT/SUPPORTED when |Δ| < min_effect_size). The high I²=99.8% reflects per-seed heterogeneity — seeds 5, 6, 44 show large framework-WORSE diffs while seeds 0, 45 show framework-BETTER.

### Verdict persistence ladder (TIE confirmed at every extension)

| Wave | n seeds | Statistic | Effect | p (Bonf) | Verdict |
|---|---|---|---|---|---|
| Wave 189 P2 | n=3 | unpaired d_s (Welch) | +0.460 | 1.0 | **TIE** |
| Wave 209 P6 | n=7 | unpaired d_s (Welch) | +1.302 | n/a | **TIE** |
| Wave 216 P2 | n=10 | unpaired d_s (Welch) | +1.011 | 0.258 | **TIE** |
| Wave 351 P2 | n=10 (paired) | paired d_z | +0.845 | 0.179 | **TIE** |
| Wave 351 P2 | n=10 (paired) | Hedges g | +0.773 | 0.179 | **TIE** |
| Wave 351 P2 | n=10 (paired) | DL random-effects meta-d_z | +0.844 | 0.0007 | **TIE** (Δ < floor) |
| Wave 233 P4 | n=30 | unpaired d_s (Welch) | -0.089 | 1.0 | **TIE** (already in repo) |

---

## (b) Evidence chain + SHA-256 anchors

The R5a evidence chain has 4 SHA-256-anchored artefact groups: (i) Wave 189 P2 n=3 aggregate JSON (paper headline source); (ii) Wave 209 P6 n=7 per-seed CSV; (iii) Wave 216 P2 n=10 per-seed CSV (canonical n=10 source); (iv) Wave 351 P2 n=10 paired-t + DL meta-analysis outputs. The Wave 233 P4 n=30 evidence is already in `verification_outputs/wave233-p4-r5a-expanded.{csv,json}` (not re-derived here; superseded for power but corroborates TIE at n=30).

### Per-file SHA-256 anchors (verified at recipe authorship, 2026-09-27)

| File | SHA-256 |
|---|---|
| `verification_outputs/wave189-p2-post-cd70821-combined.json` (R5a n=3 aggregate JSON; paper headline source) | `dee7...` *(see `verification_outputs/MANIFEST.md`)* |
| `verification_outputs/wave209-p6-r5a-extended.csv` (n=7 per-seed CSV) | `c7c17275cd224671d3e8fb03b34513339643932f54da37f593c69681b0912f8a` |
| `verification_outputs/wave216-p2-r5a-extended.csv` (n=10 per-seed CSV, canonical n=10 source) | `3df3b09cc33bafa550e21f99747ad420ffe5d14c7829d18714c58d94ef699686` |
| `verification_outputs/wave216-p2-r5a-extended.json` (n=10 paired-t Welch headline JSON) | `1e7b271dfa2825cf08ddeada5b60b6cd2745898a3d10079acefa4175109363bc` |
| `verification_outputs/wave351-r5a-n10/r5a_n10_paired.csv` (n=10 paired CSV, all 4 arms) | `1b2727e480ee7d201b2a3b9bb6d0af2bca89dc737df3b69c9801c499c3351feb` |
| `verification_outputs/wave351-r5a-n10/r5a_n10_paired.json` (n=10 paired-t + DL meta JSON) | `2ba43ccb1ce3ffc035b7427177725842493e271e3eac202a0a25a42187f3276e` |
| `verification_outputs/wave351-r5a-n10/r5a_n10_paired.md` (human-readable summary) | `bfaffb6b397f80feb0492f37cf5b220a578511fd3374bf3bed51cb1eac19766a` |
| `verification_outputs/wave233-p4-r5a-expanded.csv` (n=30 per-seed CSV, supersedes for power) | `55b65b67798c00660b64928f5e7db467f2b7e4f1bcf1ef23f1ed3457eddd9227` |
| `verification_outputs/wave233-p4-r5a-expanded.json` (n=30 paired-t JSON) | `56bcbfb1190287d7b101bc388740b3fee03032d09c0a2ce60b3cc9d4b7362281` |
| `tools/wave351_r5a_n10_paired.py` (Wave 351 P2 paired-t + DL meta driver) | *(see `verification_outputs/MANIFEST.md`)* |

### Bash verification (reviewer runs from repo root)

```bash
# 1. Verify the canonical n=10 per-seed CSV (Wave 216 P2)
sha256sum -- verification_outputs/wave216-p2-r5a-extended.csv \
             verification_outputs/wave216-p2-r5a-extended.json
# expected: 3df3b09c... (CSV) ; 1e7b271d... (JSON)

# 2. Verify the Wave 351 P2 paired-t + DL meta outputs (3 files)
sha256sum -- verification_outputs/wave351-r5a-n10/r5a_n10_paired.csv \
             verification_outputs/wave351-r5a-n10/r5a_n10_paired.json \
             verification_outputs/wave351-r5a-n10/r5a_n10_paired.md
# expected: 1b2727e4... (CSV) ; 2ba43ccb... (JSON) ; bfaffb6b... (MD)

# 3. Verify the n=30 supersession artefacts (Wave 233 P4)
sha256sum -- verification_outputs/wave233-p4-r5a-expanded.csv \
             verification_outputs/wave233-p4-r5a-expanded.json
# expected: 55b65b67... (CSV) ; 56bcbfb1... (JSON)
```

### Cross-check from `paper-data/MANIFEST.md`

The `paper-data/R5a_2d_two_moons/` folder carries 4 symlinked artefacts (per Wave 328 freeze SHA-256SUMS):

| Path | SHA-256 |
|---|---|
| `R5a_2d_two_moons/noise_injection_two_moons_baseline.csv` | `bcd1bb1ca17ecc53c9abf794f8404f678979c00c996b058e86b2548570aaa325` |
| `R5a_2d_two_moons/noise_injection_two_moons_framework.csv` | `162406303bddbdf20792e841b9ed8616ec98ba259d855828b89ce9453b6d177b` |
| `R5a_2d_two_moons/SOURCE.md` | `48cb5e6e4ab151ab227c0a94b4e354faa3d734379b56052cf91af5266ab13402` |
| `R5a_2d_two_moons/two_moons_baseline_seed0.csv` | `32057caec570888de6b982dcc769f41d5f28da7d752b37c1aae55a76e65f9548` |

These 4 files are the **2D FM ablation axis** artefacts (`-78.25% framework-WINS` at matched NFE on `R5_legacy` 2D FM framework-WINS line). The R-level W₂ reading uses the canonical `verification_outputs/wave189-p2-sota-2d-rerun/two_moons_*.csv` per-seed CSVs (n=3 seed ladder) plus the n=7 / n=10 / n=30 extensions — see `verification_outputs/MANIFEST.md` line 580 (Wave 209 P6 n=7) + line 583 (Wave 216 P2 n=10) + line 527 (Wave 233 P4 n=30).

---

## (c) Reproducibility path

The R5a cell has **two reproducibility paths**: (i) a CPU-only counterfactual path that reads the existing Wave 216 P2 per-seed CSV and emits the paired-t + DL meta-analysis JSON/MD (no GPU required); (ii) a GPU live-sweep path that re-runs the original 2D FM NFE=100 sweep from scratch (the Wave 189 P2 source).

### (c.1) CPU-only path (recommended for reviewers; <1 sec wall time)

```bash
# Activate the canonical FlowMol3 / 2D FM venv (per docs/environments.md)
source .venvs/flowmol3_venv/bin/activate

# Re-emit the Wave 351 P2 paired-t + DL meta outputs from the existing
# Wave 216 P2 per-seed CSV (NO GPU, NO network; <1 sec wall time).
python3 tools/wave351_r5a_n10_paired.py

# Verify the SHA-256 chain
sha256sum -- verification_outputs/wave351-r5a-n10/r5a_n10_paired.{csv,json,md}
# expected: 1b2727e4... ; 2ba43ccb... ; bfaffb6b...

# Cross-check the headline values from the JSON
python3 - <<'PY'
import json
d = json.load(open("verification_outputs/wave351-r5a-n10/r5a_n10_paired.json"))
h = d["headline_n10"]
dl = d["dersimonian_laird_meta"]
print(f"n=10 paired d_z = {h['paired_d_z']:.4f}  (expected +0.8452)")
print(f"Hedges g = {h['hedges_g']:.4f}  (expected +0.7728)")
print(f"DL meta-d_z = {dl['dl_d_z']:.4f}  (expected +0.8437)")
print(f"DL p = {dl['p_value_raw']:.4g}  (expected 0.0007)")
print(f"verdict_paired = {h['verdict_paired']}  (expected TIE)")
print(f"verdict_welch  = {h['verdict_welch']}  (expected TIE)")
PY
```

### (c.2) GPU live-sweep path (original Wave 189 P2 / Wave 216 P2 source)

```bash
# Activate the canonical FlowMol3 / 2D FM venv
source .venvs/flowmol3_venv/bin/activate

# Step 1: regenerate the n=3 seed baseline + framework per-seed CSVs (Wave 189 P2)
python3 tools/materialize_twodim_fm.py
python3 tools/run_sota_2d_experiment.py \
    --target two_moons \
    --n-seeds 3

# Step 2: extend to n=10 by re-running 7 additional seeds (43, 44, 45 + ...).
# This is the Wave 216 P2 path: N=1000 records/seed × 10 seeds × NFE=100.
# Wall time ~20-30 min on RTX 5090 or ~40-60 min on RTX 3090.

# Step 3: re-emit the paired-t + DL meta outputs from the new CSV.
python3 tools/wave351_r5a_n10_paired.py
```

### Environment summary

| Component | Value |
|---|---|
| Sidecar venv | `.venvs/flowmol3_venv` (per `docs/environments.md` — 2D / CIFAR / MNIST FM all share this venv) |
| GPU | Optional for CPU path; required for live sweep (RTX 5090 / RTX 3090 / PRO 6000) |
| Wall time (CPU) | <1 sec |
| Wall time (GPU live sweep) | ~20-30 min on RTX 5090 |
| NFE | 100 (paper R-level convention) |
| N records/seed | 1000 (Wave 216 P2 / Wave 351 P2 standard) |
| Canonical seed ladder | `[0, 1, 2, 3, 4, 5, 6, 43, 44, 45]` (Wave 189 P2 + 209 P6 + 216 P2) |
| Bonferroni α per cell | 0.05 / 7 = **0.007143** (Wave 195 P1 spec) |
| min_effect_size floor | 0.01 absolute W₂ (Wave 195 P1 verdict-precedence rule 1) |

### Linked scripts / surfaces

- `tools/wave351_r5a_n10_paired.py` — Wave 351 P2 paired-t + Hedges g + DL meta-analysis driver (CPU-only; reads `verification_outputs/wave216-p2-r5a-extended.csv`).
- `tools/wave195_p2_r_level_power.py` — Wave 195 P1 verdict-precedence spec (unpaired d_s + Bonferroni × 7 + min_effect_size = 0.01 floor).
- `tools/run_sota_2d_experiment.py` — Wave 189 P2 / Wave 216 P2 2D FM ablation driver (GPU).
- `reproduce/04_R4_2D_TwoMoons.sh` — existing 2D FM ablation verifier (R4 cell, separate axis; verifies the `-78.25% framework-WINS` reading at matched NFE).
- `docs/audit/wave351-r5a-n10.md` — Wave 351 P2 paired-t audit doc (canonical n=10 paired-t evidence).
- `docs/audit/wave347-r5a-ds-aggregation-clarification.md` — Wave 347 aggregation-source audit (unpaired aggregate-JSON d_s vs paired per-seed d_z semantic).
- `docs/audit/wave352-claims-r5a-update.md` — Wave 352 P5 CLM-060 R5a row Wave 351 P2 confirmation addendum.
- `docs/CLAIMS.md` CLM-060 — Wave 195 P2 R-level Table A row 4 (R5a d_s = 0.45990942269947244, TIE, preserved verbatim).

---

## (d) Disclosure — honest status label per Wave 268 strict-clean rule

The R5a cell carries a **TIE** verdict per Wave 195 P1 verdict-precedence rule. Per Wave 268 strict-clean rule, the status label is preserved verbatim — no promotion by wording.

| Verdict dimension | Status | Evidence |
|---|---|---|
| Effect direction | framework slightly WORSE on W₂ at NFE=100 (mean_diff = +0.009056, framework W₂ = 0.0820 vs baseline 0.0730; positive diff means framework has higher W₂ = worse W₂ since lower-is-better) | Wave 216 P2 per-seed CSV row 3 (CosineAnneal n=10 summary) + Wave 351 P2 per-seed data |
| Effect magnitude | small (Δ = 0.0091 absolute W₂; 12.4% relative of baseline 0.0730) | Wave 351 P2 JSON `headline_n10.diff_mean` = 0.009056 |
| Statistical significance at unpaired Bonferroni α=0.007143 | NOT significant (p_bonf = 0.258, Welch) | Wave 216 P2 JSON `primary_headline.welch.p_value_bonferroni` = 0.258 |
| Statistical significance at paired Bonferroni α=0.007143 | NOT significant (p_bonf = 0.179, paired t-test) | Wave 351 P2 JSON `headline_n10.p_value_paired_bonf` = 0.179 |
| DL random-effects p-value (k=10) | p = 0.0007 (statistically significant at conventional α=0.05; raw stat-significance IS detected but Δ below floor → verdict TIE) | Wave 351 P2 JSON `dersimonian_laird_meta.p_value_raw` = 0.0007 |
| min_effect_size floor | Δ = 0.0091 < min_effect_size = 0.01 → **TIE** | Wave 195 P1 verdict-precedence rule 1 |
| **Honest verdict label** | **TIE** | CLM-060 row 4 (Wave 195 P2 R-level table, preserved verbatim) + Wave 326 cross-doc-snapshot 11-cell distribution (4 STRONG + 1 TIE + 6 PARTIAL/SUPP, preserved verbatim) |

**What this is NOT (preserved disclosure):**
- **NOT** SUPPORTED: even though DL meta-d_z p=0.0007 is statistically significant at conventional α, the Δ=0.0091 is below the pre-specified min_effect_size=0.01 floor, so Wave 195 P1 rule 1 correctly classifies TIE.
- **NOT** NOT_SIGNIFICANT: TIE takes priority over NOT_SIGNIFICANT when |Δ| < min_effect_size (Wave 195 P1 precedence rule); the raw Bonferroni p=0.258 is also NOT-significant at the per-cell α=0.007143 level, but the verdict label is TIE.
- **NOT** UNDERPOWERED: the n=10 paired-t has Bonferroni p=0.179, which fails at the strict per-cell α=0.007143 level, BUT the per-seed heterogeneity is well-resolved (k=10 seeds × N=1000 records/seed = 10000 observations across paired seeds) and the DL meta-d_z p=0.0007 IS significant; the verdict is TIE driven by the effect-size floor, not by power.
- **NOT** REGRESSES: even though the **direction** of the framework-vs-baseline gap is consistently positive (framework slightly WORSE on W₂), the **magnitude** is below the practical-significance floor and the per-seed d_z range crosses zero (-0.40 to +2.30). Wave 195 P1 rule 1 (TIE > REGRESSES when |Δ| < min_effect_size) correctly classifies TIE.

### Why the R5a 2D Two Moons cell is TIE (not framework-WINS, not framework-WORSE)

The 2D base model converged to W₂ ≈ 0.073 within ~2× MC noise floor 1/√N ≈ 0.032 for N=1000. The framework's restart-blend at NFE=100 produces a mean W₂ of 0.082 (framework WORSE by +0.0091 absolute), but the per-seed variance is wide enough that individual seed readings can flip direction (seeds 0, 45 show framework BETTER; seeds 5, 6, 44 show framework WORSE). The DL meta-d_z = +0.844 reflects a real but small consistently-positive framework-vs-baseline gap; the **min_effect_size = 0.01 floor** is the canonical Wave 195 P1 mechanism for distinguishing "statistically detectable small effect" from "practically meaningful effect".

### Separate 2D FM ablation axis disclosure (preserved)

The `paper-data/R5a_2d_two_moons/` folder (via symlinks to `verification_outputs/noise_injection_two_moons_{baseline,framework}.csv`) carries a **separate 2D FM ablation reading** at matched NFE: **framework-WINS −78.25%** on the 2D FM framework-WINS line. Per Wave 311 DATA_PRESENTATION.md §3 line 374 (and `R5a_SOURCE.md` honest disclosure), this is a **separate axis** from the paper R-level W₂ reading — the framework-WINS is at matched NFE on the SOTA-vs-framework comparison, while the paper R-level W₂ reading uses the canonical n=10 seed ladder with NFE=100 NFE-only comparison. Both readings are honestly disclosed; this recipe covers the **paper R-level W₂ axis** only (the 2D FM ablation axis is documented in `paper-data/R5a_2d_two_moons/R5a_SOURCE.md` and `docs/r4-survey/10-sota-2d-experiment-results.md`).

---

## (e) Acceptance Criteria

The R5a reproducibility recipe is considered PASS when:

1. **SHA-256 chain verifies** (Wave 216 P2 per-seed CSV + Wave 216 P2 JSON + Wave 351 P2 CSV + Wave 351 P2 JSON + Wave 351 P2 MD + Wave 209 P6 n=7 CSV + Wave 233 P4 n=30 CSV + Wave 233 P4 n=30 JSON — all 8 hashes match).
2. **Wave 351 P2 driver re-emits the headline JSON** with `headline_n10.diff_mean = +0.009056`, `paired_d_z = +0.8452`, `hedges_g = +0.7728`, `dersimonian_laird_meta.dl_d_z = +0.8437`, `dersimonian_laird_meta.p_value_raw = 0.0007` to ±1e-4 absolute tolerance.
3. **All 4 verdict labels read TIE** (CosineAnnealScheduler paired + CosineAnnealScheduler Welch + CodimensionSheetScheduler paired + CodimensionSheetScheduler Welch + EvidenceDrivenScheduler paired + Welch + FreeTrajScheduler paired + Welch — all 8 verdict dimensions read TIE; the EvidenceDrivenScheduler and FreeTrajScheduler have only n=4 / n=3 seeds and are not used for the paper headline).
4. **D.4 byte-stable regression** (`tests/test_d4_regression_vectors.py`) is **30/30 PASS**.
5. **`python3 tools/check_claims_consistency.py`** exits 0 (no drift).
6. **`ruff check adaptive_reflow/ tests/ scripts/ tools/`** reports 0 findings.
7. **`mkdocs build --strict`** exits 0.

The recipe is **safe to run in CI** — the CPU-only path uses no GPU and no network. The GPU live-sweep path is optional and is documented for completeness (re-runs the original Wave 189 P2 / Wave 216 P2 source).

---

_Last updated: 2026-09-27 (Wave 363 P1 — R5a reproducibility recipe authored; SHA-256 chain + bash/python recipes for Wave 189 P2 + Wave 209 P6 + Wave 216 P2 + Wave 233 P4 + Wave 351 P2 evidence chain; honest TIE disclosure per Wave 268 strict-clean rule)._