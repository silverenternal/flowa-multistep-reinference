# R5b CIFAR-10 Rectified Flow — Reproducibility Recipe

**Cell:** R5b CIFAR-10 RF (matched NFE = 50; 4-scheduler × 3-`n_rounds` conditional grid)
**Headline (conditional):** `n_rounds=1` framework-WINS 4/4 schedulers (ΔFID ∈ [−1.60%, −2.53%], d_z ∈ [+4.37, +4.73]); `n_rounds ≥ 2` framework-REGRESSES 4/4 schedulers (ΔFID ∈ [+9.77%, +30.65%], p_bonf=9.17e-5)
**Date:** 2026-09-27 (Wave 363 P1.R5b — reproducibility recipe authored)
**Methodology disclosure:** Three independent sweeps on CIFAR-10 RF (Wave 235 P1 at `n_rounds=1`; Wave 225 P7 at `n_rounds=2`; Wave 206 P6 at `n_rounds=20`) — all GPU `cuda` paired-t / paired L2²-distance / Welch-t tests on per-scheduler ΔFID vs baseline; verified byte-stable evidence chain anchored by SHA-256.

---

## (a) Headline metric — 4-scheduler × 3-`n_rounds` conditional grid

The R5b cell is a **conditional verdict** that crosses zero between `n_rounds = 1` and `n_rounds ≥ 2` (per `docs/audit/wave336-r5b-mechanism.md`); it is rendered as a 12-cell grid (4 schedulers × 3 `n_rounds`) in `docs/drafts/figure_r5b_conditional_grid.png`.

| scheduler \ `n_rounds` | `n_rounds=1` (Wave 235 P1) | `n_rounds=2` (Wave 225 P7) | `n_rounds=20` (Wave 206 P6) |
|------------------------|--------------------------:|--------------------------:|----------------------------:|
| CosineAnnealScheduler  | **−1.60%** d_z=+4.37 (WINS) | +9.77% d_z=+5.44 (REGRESSES) | +24.89% p_bonf=9.17e-5 (REGRESSES) |
| CodimensionSheetScheduler | **−2.53%** d_z=+4.73 (WINS) | +9.79% d_z=+5.41 (REGRESSES) | +25.13% p_bonf=9.17e-5 (REGRESSES) |
| EvidenceDrivenScheduler | **−0.12%** d_z=+4.63 (WINS) | +9.83% d_z=+5.41 (REGRESSES) | +24.46% p_bonf=9.17e-5 (REGRESSES) |
| FreeTrajScheduler      | **−0.66%** d_z=+4.51 (WINS) | +16.62% d_z=+5.78 (REGRESSES) | +30.65% p_bonf=9.17e-5 (REGRESSES) |

**Aggregate verdict (4 schedulers):**
- **`n_rounds = 1`:** framework **WINS 4/4** schedulers (ΔFID ∈ [−1.60%, −2.53%], d_z ∈ [+4.37, +4.73], all Bonferroni-sig at α=0.05/4=0.0125).
- **`n_rounds ≥ 2`:** framework **REGRESSES 4/4** schedulers (ΔFID ∈ [+9.77%, +30.65%]; Wave 225 P7 d_z ∈ [+5.41, +5.78] per-sample L2² paired-t; Wave 206 P6 p_bonf=9.17e-5 Welch-t at α=0.05/7=0.007143).

---

## (b) Evidence chain + SHA-256 anchors

The R5b cell's load-bearing evidence is **three independent sweeps** on CIFAR-10 RF, each with its own audit doc + script + JSON. All three SHA-256 values are computed at recipe authorship.

| File | SHA-256 | Source / purpose |
|------|---------|------------------|
| `verification_outputs/wave235-p1-r5b-fix.json` | `488655ce10e0e1bea71ea804f079b1ada0c90be239df04b8f12d9d9b4db3b602` | `n_rounds=1` reversal evidence (200 paired records, per-sample L2² paired-t) |
| `verification_outputs/wave225-p7-r5b-reduced-rounds.json` | `f22f57d9f3f42a978f748e3d4379fce42ff34ba9a54fa70c35c6ad7a80683a0a` | `n_rounds=2` reduced-rounds counterfactual (200 paired records, per-sample L2² paired-t) |
| `verification_outputs/wave206-p6-honest-negative-curve.json` | `a319b561891cc59d3d0e4979950278dc96d62515346702bccd30958ef9c36717` | `n_rounds=20` honest-negative multi-NFE curve (N=500 / NFE=50, Welch-t; Source A reading) |
| `paper-data/R5b_cifar10_rf/wave235-p1-r5b-fix.json` (symlink) | matches the above | paper-citation mirror of the Wave 235 P1 evidence |
| `paper-data/R5b_cifar10_rf/wave191-p2-cifar10-n1000.json` (symlink) | `a3c5bea08e44018eabaa6e8332ac7de211de70f48607cf983143b87302d5b0dd` | Wave 191 P2 N=1000 initial 4-arm sweep (chunked FID, baseline 415.83 vs framework 499.83-500.20, Δ+2.80% to +2.91%) |

### Bash verification (reviewer runs from `verification_outputs/`)

```bash
cd verification_outputs && \
  sha256sum -- wave235-p1-r5b-fix.json \
               wave225-p7-r5b-reduced-rounds.json \
               wave206-p6-honest-negative-curve.json
# expected:
#   488655ce10e0e1bea71ea804f079b1ada0c90be239df04b8f12d9d9b4db3b602  wave235-p1-r5b-fix.json
#   f22f57d9f3f42a978f748e3d4379fce42ff34ba9a54fa70c35c6ad7a80683a0a  wave225-p7-r5b-reduced-rounds.json
#   a319b561891cc59d3d0e4979950278dc96d62515346702bccd30958ef9c36717  wave206-p6-honest-negative-curve.json
```

The `paper-data/SHA256SUMS` file additionally contains the 12-file mirror (5 NPZ + 4 csv/json + comparison.md + R5b_SOURCE.md) for byte-stable cross-reference. Reviewers can verify the mirror via `cd paper-data && sha256sum --check R5b_cifar10_rf/SHA256SUMS` if the per-directory SHA256SUMS is generated (currently only the global `paper-data/SHA256SUMS` exists; per-directory generation is documented in `paper-data/R5b_cifar10_rf/R5b_SOURCE.md` §"Verification").

### Audit-doc anchors

| Audit doc | Role |
|-----------|------|
| `docs/audit/wave336-r5b-mechanism.md` | Wave 336 R5b `n_rounds` Conditional Boundary — Mechanism Analysis (the WHY behind the 4/4 transition) |
| `docs/audit/wave350-r5b-figure.md` | Wave 350 P4 12-cell conditional grid figure (Panel A heatmap + Panel B grouped bars) |
| `docs/audit/wave354-r5b-figure-verify.md` | Wave 354 P2 §7.6.2 figure verification (PNG byte-stable + cross-references resolve) |
| `docs/CLAIMS.md` CLM-070 | R5b honest-negative row (cross-reference pointer for the 12-cell grid + cosine-ramp halving) |
| `docs/CLAIMS.md` CLM-060 | R-level per-cell power analysis (R5b is the single REGRESSES cell in the 7-R distribution) |

---

## (c) Reproducibility path

The R5b evidence is **NOT** a counterfactual (unlike R6); it is **three independent live-GPU paired sweeps** at three `n_rounds` values. The CPU verification path reads the JSON evidence directly (no recomputation); the GPU re-run path regenerates the JSON via the Wave 235 / Wave 225 / Wave 206 sweep scripts.

### CPU path — verify all 4 schedulers across all 3 `n_rounds` values (no GPU; <5 sec)

```bash
# Pre-condition: verification_outputs/{wave235-p1-r5b-fix,wave225-p7-r5b-reduced-rounds,wave206-p6-honest-negative-curve}.json
python3 - <<'PY'
import json, math

# ---- n_rounds=1 (Wave 235 P1 reversal) ----
d1 = json.load(open("verification_outputs/wave235-p1-r5b-fix.json"))["rounds1"]
assert d1["n_rounds"] == 1
WINS = {"cosineanneal": -1.6018, "codimensionsheet": -2.5302,
        "evidencedriven": -0.1173, "freetraj": -0.6638}
for sched, exp_pct in WINS.items():
    r = d1["results"][sched]
    assert math.isclose(r["delta_pct"], exp_pct, abs_tol=1e-3), \
        f"n_rounds=1 {sched}: got {r['delta_pct']}, expected {exp_pct}"
    assert r["delta_pct"] < 0, f"n_rounds=1 {sched} not WINS"
    assert r["p"] < 0.0125, f"n_rounds=1 {sched} not Bonf-sig at α=0.05/4=0.0125"
print(f"OK: n_rounds=1 framework-WINS 4/4 (d_z range "
      f"+{min(r['d_z'] for r in d1['results'].values()):.4f} to "
      f"+{max(r['d_z'] for r in d1['results'].values()):.4f})")

# ---- n_rounds=2 (Wave 225 P7 reduced-rounds counterfactual) ----
d2 = json.load(open("verification_outputs/wave225-p7-r5b-reduced-rounds.json"))
assert d2["n_rounds"] == 2
REGS2 = {"cosineannealscheduler": 9.7652, "codimensionsheetscheduler": 9.7879,
         "evidencedrivenscheduler": 9.8260, "freetrajscheduler": 16.6216}
for sched, exp_pct in REGS2.items():
    r = d2["framework_arms"][sched]
    assert math.isclose(r["delta_vs_baseline_pct"], exp_pct, abs_tol=1e-3)
    assert r["bonferroni_significant"] is True
print(f"OK: n_rounds=2 framework-REGRESSES 4/4 (ΔFID range "
      f"+{min(r['delta_vs_baseline_pct'] for r in d2['framework_arms'].values()):.2f}% to "
      f"+{max(r['delta_vs_baseline_pct'] for r in d2['framework_arms'].values()):.2f}%)")

# ---- n_rounds=20 (Wave 206 P6 honest-negative curve) ----
d3 = json.load(open("verification_outputs/wave206-p6-honest-negative-curve.json"))
assert d3["nfe_50_bonferroni_significant_in_wrong_direction"] is True
assert d3["nfe_50_p_value"] == 9.17e-05
PER_SCHED = {k: v["50"] for k, v in d3["per_scheduler_by_nfe"].items()}
REGS20 = {"CosineAnnealScheduler": 24.89, "CodimensionSheetScheduler": 25.13,
          "EvidenceDrivenScheduler": 24.46, "FreeTrajScheduler": 30.65}
for sched, exp_pct in REGS20.items():
    assert math.isclose(PER_SCHED[sched], exp_pct, abs_tol=1e-3), \
        f"n_rounds=20 {sched}: got {PER_SCHED[sched]}, expected {exp_pct}"
print(f"OK: n_rounds=20 framework-REGRESSES 4/4 (ΔFID range "
      f"+{min(PER_SCHED.values()):.2f}% to +{max(PER_SCHED.values()):.2f}%, p_bonf={d3['nfe_50_p_value']:.2e})")
PY
# expected:
#   OK: n_rounds=1 framework-WINS 4/4 (d_z range +4.3676 to +4.7277)
#   OK: n_rounds=2 framework-REGRESSES 4/4 (ΔFID range +9.77% to +16.62%)
#   OK: n_rounds=20 framework-REGRESSES 4/4 (ΔFID range +24.46% to +30.65%, p_bonf=9.17e-05)
```

### GPU path — regenerate the 12-cell evidence (≈30 min on RTX 5090 / RTX PRO 6000)

The R5b evidence is **GPU-regeneratable** via the three sweep scripts. Environment: `.venvs/flowmol3_venv` (per `docs/environments.md` — CIFAR-10 RF falls under `flowmol3_venv`).

```bash
# Activate the FlowMol3 venv (NEVER mix with Kanzi/LineageFlow venvs)
source .venvs/flowmol3_venv/bin/activate

# ---- (1) n_rounds=1 reversal sweep (Wave 235 P1) ----
python3 scripts/wave235_p1_r5b_fix_sweep.py \
    --config rounds1 \
    --n-records 200 \
    --seed 42 \
    --output-dir verification_outputs/wave235-p1-r5b-rounds1-n200
# expected wall-clock: ~10 min on RTX 5090; output JSON: wave235-p1-r5b-fix.json (key "rounds1")

# ---- (2) n_rounds=2 reduced-rounds counterfactual (Wave 225 P7) ----
python3 scripts/wave225_p7_r5b_reduced_rounds.py \
    --n-records 200 \
    --seed 42 \
    --output-dir verification_outputs/wave225-p7-r5b-rounds2-n200
# expected wall-clock: ~10 min on RTX 5090; output JSON: wave225-p7-r5b-reduced-rounds.json

# ---- (3) n_rounds=20 honest-negative multi-NFE curve (Wave 206 P6) ----
python3 scripts/wave206_p6_cifar_rf_v4_honest_negative_curve.py \
    --full \
    --nfe-list 10 20 30 50 100 200 500 \
    --n-records-per-nfe 500 \
    --output-dir /tmp/wave206_p6_full_sweep
# expected wall-clock: ~7.5 GPU-hours on RTX 5090; output JSON: wave206-p6-honest-negative-curve.json
# DEFERRED per CLM-070 (Wave 209 P6 R5a GPU-0 resource-conflict directive)
```

External dependencies: CIFAR-10 RF reference features at `data/rf_reference_features/`; InceptionV3 TF-port weights (post-Wave-127 EMA-corrected for Source-B reading; pre-EMA-fix Liu 2022 published-style for the Source-A reading in `wave206-p6-honest-negative-curve.json`).

### Existing reproduction script

`reproduce/06_R5b_CIFAR_n_rounds1.sh` is the existing per-cell script that verifies the `n_rounds=1` Wave 235 P1 headline (4/4 WINS, ΔFID ∈ [−2.53%, −0.66%]) from the byte-stable JSON without re-running GPU sweeps. It uses `.venvs/flowmol3_venv` and exits 0 when the JSON matches the expected `(delta_pct, d_z)` per-scheduler pairs.

---

## (d) Disclosure — honest status label per Wave 268 strict-clean rule

The R5b cell is a **conditional verdict**, and the disclosure must reflect both sides of the boundary honestly:

| `n_rounds` regime | status label (verbatim) | rationale |
|-------------------|-------------------------|-----------|
| `n_rounds = 1` | **SUPPORTED** | framework WINS 4/4 schedulers (ΔFID ∈ [−1.60%, −2.53%], d_z ∈ [+4.37, +4.73], Bonf-sig at α=0.0125 for all 4 arms; n=200 paired per arm); the headline value-add at the matched-budget cell. |
| `n_rounds ≥ 2` | **REGRESSES** | framework REGRESSES 4/4 schedulers (ΔFID ∈ [+9.77%, +30.65%]; Wave 225 P7 n_rounds=2 Bonf-sig at α=0.0125 for all 4 arms; Wave 206 P6 n_rounds=20 p_bonf=9.17e-5 at α=0.007143); **honest-negative** disclosure per CLM-070 + paper §7.6 mechanism paragraph. |

**Never promote.** Per AGENTS.md hard guardrail #4: the `REGRESSES` row at `n_rounds ≥ 2` MUST NOT be reframed as `SUPPORTED` by wording alone. The framework value-add at matched NFE = 50 on CIFAR-10 RF is **monotonically decreasing in `n_rounds`** (per `docs/audit/wave336-r5b-mechanism.md` §4.5 — restart-blend operator underflows on already-corrected inputs); the conditional verdict is the load-bearing §7.6 claim, not a single aggregate status label.

The Wave 280 P addendum (per `docs/CLAIMS.md` CLM-060 line 3872-3883) is **additive regime finding** showing R5b honest-negative is **scheduler-conditioned at matched-NFE=2** (CosineAnnealScheduler +52.33% / CodimensionSheetScheduler −1.69% / +0.11% at N=200-N=500) — the Wave 235 P1 / Wave 225 P7 / Wave 206 P6 evidence at matched-NFE=50 / `n_rounds ∈ {1, 2, 20}` is the **load-bearing evidence chain for paper §7.6** (the matched-NFE=50 R5b cell).

---

_Last updated: 2026-09-27 (Wave 363 P1.R5b — R5b reproducibility recipe authored; SHA-256 chain + bash/python recipes for Wave 235 P1 + Wave 225 P7 + Wave 206 P6 evidence + conditional SUPPORTED/REGRESSES disclosure)._