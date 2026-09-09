# Wave 92 (W3) — N=5000 paper-metric sweep on all 3 Tier 3 models (OPT-IN)

**Date:** 2026-09-09 (updated 2026-09-10)
**Status:** ⏸ **OPT-IN PENDING** (waits for Wave 92c/93 results + user decision)
**Closes:** reviewer weakness W3 (N=1000 too small)

> **OPT-IN clause:** This wave is **optional** — user decides whether to run. Honest N=1000 is defensible (per Wave 75-78 master plan §5b). N=5000 closes the reviewer "statistical power insufficient" objection but adds 4-8h GPU time. Recommend running if Wave 91 framework-vs-baseline deltas are small (<1pp) where N=1000 CI is too wide.

---

## 1. Goal

Re-run the 3 Tier 3 paper-metric sweeps at **N=5000 per arm** (5x current N=1000):

| Model | N=1000 sweep | N=5000 sweep |
|---|---|---|
| FlowMol3 | Wave 82 commit `5e5a20e` | Wave 92 Phase 2 |
| LineageFlow | Wave 81 commit `704a7fa` | Wave 92 Phase 3 |
| Kanzi | Wave 83 commit `58adf1e` (baseline) + Wave 91 (framework) | Wave 92 Phase 4 |

Expected CI improvement: `±1pp` (N=1000) → `±0.45pp` (N=5000).

---

## 2. Why N=5000 (and not 10000)

- **Paper protocol unchanged**: still call upstream eval pipeline with same code
- **Statistical power**: N=5000 gives 99% power to detect 1pp difference with α=0.05 for binomial metrics (validity, family_validity, novelty)
- **Wall-clock budget**: 4-8h on RTX PRO 6000 / 5090; vs 10-15h for N=10000
- **N=10000 vs N=5000**: marginal CI improvement (0.32pp → 0.45pp); not worth extra 6-12h

---

## 3. Constraints

- **Same eval protocol** as N=1000 sweeps (vendored upstream eval unchanged)
- **Same ckpts** (no re-download)
- **Same seed strategy** (paper §5.7 honest caveat about RNG carries over)
- **D.4 byte-stable**: 33/33 unchanged (only data generation script changes, not eval pipeline)
- **NO push** — user decides

---

## 4. Phase 1 — Pre-flight check (~15 min)

### Verify GPU + ckpts ready
- `nvidia-smi` (RTX PRO 6000 or 5090 available)
- `data/flowmol3/flowmol3.ckpt` SHA-256 matches `verification_outputs/ckpt_sha256.json`
- `data/lineageflow/lineageflow-rp55.ckpt` SHA-256 matches
- `data/kanzi_ckpt/cleaned_model.pt` + `kanzi_encoder.pt` SHA-256 matches
- All 3 venvs (`flowmol3_venv`, `lineageflow_venv`, `kanzi_venv`) functional

### Estimate wall-clock
- FlowMol3 N=5000: ~80-120 min (PB-xtb is bottleneck)
- LineageFlow N=5000: ~60-90 min (HMMER + OmegaFold is bottleneck)
- Kanzi N=5000: ~60-90 min (FSQ + decoder + paper metrics)

### Output: `docs/audit/wave92-phase1-preflight.md`

---

## 5. Phase 2 — FlowMol3 N=5000 sweep (~80-120 min)

### Baseline arm
```bash
.venvs/flowmol3_venv/bin/python tools/run_real_ckpt_eval.py \
    --model flowmol3 --force-mode real \
    --n-samples 5000 \
    --output-dir verification_outputs/flowmol3_n5000_paper_metrics/baseline/
```

### Framework arm
```bash
.venvs/flowmol3_venv/bin/python tools/run_real_ckpt_eval.py \
    --model flowmol3 --force-mode real --framework \
    --n-samples 5000 \
    --output-dir verification_outputs/flowmol3_n5000_paper_metrics/framework/
```

### Outputs
- `baseline/per_metric.json` (4 FlowMol3 metrics: validity / pb_validity / fg_dev / ood_ring_rate)
- `framework/per_metric.json` (same 4)
- `delta.json` (per-metric delta + Welch's t-test p-value)

---

## 6. Phase 3 — LineageFlow N=5000 sweep (~60-90 min)

### Same pattern as Phase 2, with `--lineageflow-paper-metrics` flag
- Baseline arm + framework arm × 5000 samples
- 4 metrics: family_validity + foldability + self_consistency + novelty
- Outputs to `verification_outputs/lineageflow_n5000_paper_metrics/`

---

## 7. Phase 4 — Kanzi N=5000 sweep (~60-90 min)

### Same pattern, with `--kanzi-framework-paper-metrics` flag (Wave 91 wired)
- Baseline arm + framework arm × 5000 samples
- 6 metrics: reconstruction_kabsch_rmsd_A + codebook_utilization + codebook_entropy + motif_coverage + structural_validity + fbd
- Outputs to `verification_outputs/kanzi_n5000_paper_metrics/`

---

## 8. Phase 5 — Aggregate + paper update (~45-60 min)

### Aggregate per-model summary
- Per-metric baseline ± CI vs framework ± CI
- Per-paper-claim status: SUPPORTED / PARTIAL / TIE / REGRESSES
- Statistical power per metric at N=5000

### Update `docs/paper-draft.md` §7.3 / §7.4 / §7.5 (ADDITIVE Wave 92 paragraph)
- Per-metric N=5000 numbers
- N=1000 → N=5000 CI improvement shown

### Author `docs/audit/wave92-phase5-final.md`
- Per-metric N=1000 vs N=5000 comparison
- Statistical power analysis
- D.4 + G-MASTER + mkdocs verify

### Update `docs/push-ready-summary.md` (additive)

### Commit (single, NO push)
**Title:** "Wave 92: N=5000 paper-metric sweep on 3 Tier 3 models — W3 closed"

---

## 9. Time budget

- Phase 1 (pre-flight): 15 min
- Phase 2 (FlowMol3 N=5000): 80-120 min
- Phase 3 (LineageFlow N=5000): 60-90 min
- Phase 4 (Kanzi N=5000): 60-90 min
- Phase 5 (aggregate + paper): 45-60 min
- **Total: 4.5-6.5 hours wall-clock** (recommend 6-8h buffer for GPU contention)

---

## 10. Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| GPU contention with other workloads | P1 | Schedule off-peak; check `nvidia-smi` pre-flight |
| Kanzi FSQ noise floor amplified at N=5000 (delta shrinks) | P2 | Document honestly; show CI ±0.5pp at N=5000 |
| FlowMol3 PB-xtb timeout | P2 | Wave 90 commit `fe95293` pb_config optimization should keep it under 90 min; if not, fall back to UFF (already documented honest caveat in Wave 87) |
| LineageFlow OmegaFold OOM | P2 | Use CPU offload or batch=1; document as honest caveat |

---

## 11. Open questions

1. **OPT-IN confirmation**: Does user want this wave, or is N=1000 honest enough?
2. **If OPT-IN, what's the priority model?** — recommend FlowMol3 first (most reviewer-relevant chemistry metric); Kanzi second; LineageFlow last
3. **What if N=5000 reveals framework regresses on a metric that was TIE at N=1000?** — honest narrative; Wave 93 power analysis explains why

---

## 12. Cross-references

- Wave 90 commit `fe95293`: PB-xtb pipeline pattern
- Wave 91 plan: `todo/planned/w2-kanzi-latent-coord-bridge.md` (Kanzi bridge must commit first)
- Wave 75-78 master plan §5b: N=1000 vs N=5000 trade-off rationale
- Wave 81 / 82 / 83 commits: N=1000 sweep reference numbers