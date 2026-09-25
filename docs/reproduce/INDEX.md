# `reproduce/` — One-Cell Script INDEX

> **Wave:** 361 P1 (CPU-only documentation surface, NO GPU)
> **Date:** 2026-09-25
> **Owning audit doc:** [`docs/audit/wave361-reproduce-scripts-verify.md`](../audit/wave361-reproduce-scripts-verify.md)
> **Sibling guide:** [`docs/reproduce.md`](../reproduce.md) — the 5-step full Reproduction Guide (hardware, software, troubleshooting)
> **Status:** 8/8 scripts syntax-PASS (`bash -n`); 12/12 referenced drivers EXIST; 7/7 verification_outputs artefacts EXIST

---

## 1. Per-cell scripts (7 R-level cells)

| # | Script | R-cell | Headline (metric, baseline → framework, Δ) | Env | Wall-time | Byte-stable artefact | Driver (optional run) |
|---|---|---|---|---|---|---|---|
| 1 | `reproduce/01_R1_LineageFlow.sh` | **R1** | HMMER total hits, 158 → 342, +184 (+116.46%, Bonf-sig p ≈ 1.5e-08) | `.venvs/lineageflow_venv` | ~30-50 h CPU | `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/{baseline,framework}_hits.tbl` | `tools/run_lineageflow_n1000_foldability_omegafold.py` |
| 2 | `reproduce/02_R2_Kanzi.sh` | **R2** | RMSD d_z = -0.0990, p = 0.0018 (Bonf-sig, framework_WINS) | `.venvs/kanzi_venv` | ~4 h CPU (2 h/arm × 2 arms) | `verification_outputs/wave218-p3-kanzi-framework-wins.json` | `tools/sweep_kanzi_n1000_{framework_,}paper_metrics.py` + `scripts/wave218_p3_paired_ttest.py` |
| 3 | `reproduce/03_R3_FlowMol3.sh` | **R3** | per-record fg_dev proxy d_z = -0.285, p < 1e-4 (Bonf-sig, framework_WINS) | `.venvs/flowmol3_venv` (GPU) | ~30 min GPU | `verification_outputs/wave216-p1-r3-per-record.json` | `tools/wave87_n1000_sweep.py` + `scripts/wave216_p1_r3_per_record.py` |
| 4 | `reproduce/04_R4_2D_TwoMoons.sh` | **R4** | 2D W₂, 2.85 → 0.62, -78.25% (framework_WINS) | `.venvs/flowmol3_venv` (CPU) | ~1 min/arm CPU | `verification_outputs/g1_deep_dive_q3_2026.json` (row: `twodim_fm_2d_ablation`) | `tools/materialize_twodim_fm.py` + `tools/run_sota_2d_experiment.py --target two_moons` |
| 5 | `reproduce/05_R5_2D_EightGaussians.sh` | **R5** | 2D W₂, 0.6606 → 0.5919, -10.40% (framework_WINS) | `.venvs/flowmol3_venv` (CPU) | ~1 min/arm CPU | `verification_outputs/g1_deep_dive_q3_2026.json` (row: `twodim_fm_2d_eight_gaussians`) | `tools/materialize_twodim_fm.py` + `tools/run_sota_2d_experiment.py --target eight_gaussians` |
| 6 | `reproduce/06_R5b_CIFAR_n_rounds1.sh` | **R5b** | CIFAR-10 RF n_rounds=1, framework_WINS on 4/4 schedulers (ΔFID range -2.53% to -0.12%) | `.venvs/flowmol3_venv` (GPU) | ~30 min GPU (3 seeds × 4 schedulers) | `verification_outputs/wave235-p1-r5b-fix.json` (key: `rounds1`) | `tools/run_sota_cifar_experiment.py --n-rounds 1 --n-seeds 3` |
| 7 | `reproduce/07_R6_MNIST_TierAware.sh` | **R6** | tier-aware pLDDT d_z 0.224 → 0.647, +189% uplift (Bonf-sig, easy-regression eliminated) | `.venvs/flowmol3_venv` (CPU) | <1 min CPU (counterfactual) | `verification_outputs/wave235-p3-r6-uplift.json` (best grid cell) | `scripts/wave235_p3_r6_uplift.py` |

All 7 per-cell scripts verify the headline from a byte-stable `verification_outputs/` artefact (no re-execution required for headline confirmation). The actual re-execution sweep commands are commented out inside each per-cell script (cells range from <1 min CPU to ~50 h CPU+GPU). To re-run, open the relevant `reproduce/0X_R*_*.sh` and uncomment the "Run command" block.

---

## 2. Master verifier (1)

| Script | Purpose | Wall-time | Notes |
|---|---|---|---|
| `reproduce/verify_all_headlines.sh` | Loops over `reproduce/[0-9]*.sh` in numeric order; prints PASS/FAIL per cell; exits non-zero on any failure | <1 min CPU (depends on per-cell artefact I/O) | Safe to invoke in CI; prints `OK: All 7/7 R-level headlines verified` on full PASS |

---

## 3. Per-cell audit docs (cross-reference)

| R-cell | Audit doc | Wave source |
|---|---|---|
| R1 (LineageFlow HMMER) | [`docs/audit/wave086-lineageflow-hmmer-n1000.md`](../audit/) (archived in `docs/ARCHIVE/audit-by-wave/`) + `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/SOURCE.md` (Wave 158 final) | Wave 86 N=1000 + Wave 158 byte-stable |
| R2 (Kanzi paper-metric) | `docs/ARCHIVE/audit-by-wave/wave218-p3-n1000-verified.md` + `docs/headline-evidence/kanzi_n1000_byte_reproducible/source_audit.md` (Wave 131 retrospective) | Wave 218 P3 paired-t + Wave 127 byte-reproducible anchor |
| R3 (FlowMol3 per-record) | `docs/audit/wave360-claims-status-summary.md` (CLM-031) + Wave 87 N=1000 sweep evidence | Wave 87 N=1000 + Wave 216 P1 per-record |
| R4 (2D Two Moons W₂) | [`docs/audit/wave189-p2-sota-2d-rerun.md`](../audit/) (Wave 189 P2 SOTA-rerun consolidation) + `docs/audit/wave351-r5a-n10.md` (Wave 351 P5 n=10 paired-t confirmation) | Wave 189 P2 + Wave 351 P5 |
| R5 (2D Eight Gaussians W₂) | [`docs/audit/wave189-p2-sota-2d-rerun.md`](../audit/) + `docs/audit/wave351-r5a-n10.md` + `docs/audit/wave308-d3-review.md` (Wave 308 cosmetic fix: baseline 2.31 → 0.6606, framework 0.76 → 0.5919) | Wave 189 P2 + Wave 308 cosmetic fix |
| R5b (CIFAR-10 RF n_rounds=1) | [`docs/audit/wave235-p1-r5b-fix.md`](../audit/) (Wave 235 P1 3-seed re-sweep) | Wave 235 P1 |
| R6 (MNIST FM tier-aware) | [`docs/audit/wave235-p3-r6-uplift.md`](../audit/) (Wave 235 P3 counterfactual grid) + `docs/audit/wave233-p3-r6-baseline.md` (Wave 233 P3 baseline) | Wave 233 P3 baseline + Wave 235 P3 grid |
| Master verifier | `reproduce/verify_all_headlines.sh` (no source citation; first appeared Wave 267) | Wave 267 |

---

## 4. Wave 127 N=1000 framework_inv_proj byte-stability anchor

The **R2 Kanzi cell** has an additional byte-stability anchor that predates the `reproduce/*.sh` package:

| Anchor | Path | Provenance |
|---|---|---|
| Wave 127 N=1000 framework_inv_proj | `verification_outputs/kanzi_n1000_framework_inv_proj_seed42_wave127_q3_2026/kanzi_n1000_paper_metrics.json` | [`docs/headline-evidence/kanzi_n1000_byte_reproducible/SOURCE.md`](../headline-evidence/kanzi_n1000_byte_reproducible/SOURCE.md) (Wave 131 retrospective) |
| Wave 131 byte-reproducibility appendix | (no separate audit doc; embedded in `source_audit.md`) | `docs/headline-evidence/kanzi_n1000_byte_reproducible/source_audit.md` |
| Inv-proj sweep driver | `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` | (executable; not referenced by any per-cell script — superseded by Wave 218 P3 paired-t path) |

The Wave 127 N=1000 framework_inv_proj headline is **framework mean_rmsd = 0.8798 ± 0.1364 Å (n=1000, deterministic)**, paired against **baseline_seed42 mean_rmsd = 0.9020 ± 0.1375 Å**, **delta = -0.0222 Å (TIES)**. Byte-reproducibility verified at delta = 0.00e+00 across Wave 127 + Wave 131 commits on the ruff-frozen code.

The R2 per-cell script (`reproduce/02_R2_Kanzi.sh`) uses the **Wave 218 P3 paired-t JSON** for the framework_WINS verdict (d_z = -0.0990, p = 0.0018, Bonf-sig), not the Wave 127 byte-reproducible path. The Wave 127 path is cross-referenced here for **per-record provenance**, not for runnable headline confirmation.

---

## 5. Master verification recipe

```bash
# Single-command verification of all 7 R-level headlines
bash reproduce/verify_all_headlines.sh

# Expected output (on full PASS):
#   OK: All 7/7 R-level headlines verified

# Per-cell invocation (e.g. just R4):
bash reproduce/04_R4_2D_TwoMoons.sh

# Expected output (on PASS):
#   R4 reproduced: W2 baseline=2.85 -> framework=0.62 (Delta = -78.25%, framework_WINS)
#   OK R4 reproduced: framework W2 = 0.62 (Delta = -78.25%, framework_WINS)
```

To **re-execute** a cell (not just verify the headline), open the relevant `reproduce/0X_R*_*.sh` and uncomment the "Run command" block at the bottom. The wall-time budgets in §1 are historical estimates from the corresponding Wave; actual re-execution time depends on hardware.

---

## 6. Cross-references (not modified by this INDEX)

- `docs/reproduce.md` — full Reproduction Guide (hardware, software, 5-step recipe, troubleshooting)
- `docs/audit/wave361-reproduce-scripts-verify.md` — this INDEX's owning audit doc
- `docs/headline-evidence/kanzi_n1000_byte_reproducible/SOURCE.md` — Wave 127 byte-stability anchor provenance
- `docs/audit/wave189-p2-sota-2d-rerun.md` — R4 + R5 SOTA-rerun consolidation
- `docs/audit/wave308-d3-review.md` — R5 cosmetic fix (Wave 308)
- `docs/audit/wave360-claims-status-summary.md` — CLM-031 R3 cross-reference
- `docs/CLAIMS.md` — 84 CLMs total (61 ACTIVE / 0 PROVISIONAL / 2 DEPRECATED + 1 verifier-forced PROVISIONAL on CLM-040)
- `tnnls_submission/data_availability.md` — §9 "Reproduction instructions" (Wave 356 P2)

---

_Last updated: 2026-09-25 (Wave 361 P1 — CPU-only documentation surface)._