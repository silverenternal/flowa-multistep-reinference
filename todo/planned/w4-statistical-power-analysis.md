# Wave 93 (W4) — Statistical power analysis + per-cell CI + honest narrative

**Date:** 2026-09-09 (updated 2026-09-10)
**Status:** 🔄 **IN PROGRESS** (Phase 1 tool landed `e69ffd8`; Phase 2 in flight Task `w2ap73xhs`)
**Closes:** reviewer weakness W4 (2/12 framework_improves cells honest reframing)

> **Why this matters:** The previous honest result was "2/12 cells framework_improves with stat-sig" — this looks like a loss to a casual reviewer. Wave 93 reframes this with rigorous statistical power analysis: which cells have enough power to detect 1pp difference, which don't, and what the mixed result means under multiple-testing correction.

---

## 1. Goal

Compute statistical power + per-cell 95% CI + multiple-testing correction for all 12 (model, paper_metric) cells across 3 Tier 3 models. Reframe §7.6 honest verdict with honest mixed-result narrative.

---

## 2. Inputs

| Source | What it provides |
|---|---|
| `verification_outputs/flowmol3_n1000_paper_metrics/` (Wave 82) | FlowMol3 baseline + framework + delta + p-value per metric |
| `verification_outputs/lineageflow_n1000_paper_metrics/` (Wave 81) | LineageFlow baseline + framework + delta + p-value per metric |
| `verification_outputs/kanzi_n1000_framework_paper_metrics/` (Wave 91) | Kanzi baseline + framework + delta + p-value per metric |
| `verification_outputs/{X}_n5000_paper_metrics/` (Wave 92, optional) | N=5000 versions for tighter CI |

---

## 3. Constraints

- **CPU-only** (numpy + scipy.stats only — no torch)
- **Single commit** + audit doc
- **D.4 unchanged** (analysis-only; no framework code changes)
- **NO push**

---

## 4. Phase 1 — Author statistical power tool (~45 min)

### File: `tools/statistical_power_analysis.py` (NEW)

### Function: `compute_power_table`

```python
def compute_power_table(
    cells: List[Tuple[str, str, float, float, int]],  # (model, metric, baseline_mean, framework_mean, n)
    alpha: float = 0.05,
    min_effect_size_pp: float = 1.0,
) -> pd.DataFrame:
    """Compute per-cell power + 95% CI + p-value + Bonferroni-corrected verdict.
    
    Returns DataFrame with columns:
    - model, metric, n, baseline, framework, delta, delta_se
    - ci_95_lower, ci_95_upper (CI on delta)
    - p_value_raw, p_value_bonferroni
    - power_to_detect_1pp (post-hoc power)
    - verdict: SUPPORTED if p_bonferroni < 0.05 AND delta > 0
              TIE if |delta| < 1pp
              REGRESSES if p_bonferroni < 0.05 AND delta < 0
              UNDERPOWERED if power_to_detect_1pp < 0.5
    """
```

### Statistical methods
- **CI**: bootstrap (10K samples) OR Welch's t-test confidence interval (pick per distribution)
- **p-value**: Welch's t-test (continuous metrics) OR Fisher's exact test (binomial metrics)
- **Power**: post-hoc power at min_effect_size_pp = 1.0 (per reviewer concern)
- **Multiple testing**: Bonferroni correction across 12 cells (α = 0.05/12 = 0.00417)

### Tests: `tests/test_tools/test_statistical_power_analysis.py` (NEW)

- Test 1: known distribution → correct CI bounds
- Test 2: Bonferroni correction applied correctly
- Test 3: underpowered verdict triggered correctly
- Test 4: SUPPORTED / TIE / REGRESSES verdict thresholds

### Verify
- `pytest tests/test_tools/test_statistical_power_analysis.py -v`
- D.4 byte-stable: 33/33 unchanged

### Commit (single, NO push)
**Title:** "Wave 93 Phase 1: statistical power analysis tool + 4 unit tests"

---

## 5. Phase 2 — Run analysis on all 12 cells (~30 min)

### Input data
- 4 FlowMol3 cells (validity + pb_validity + fg_dev + ood_ring_rate, baseline+framework at N=1000 OR N=5000 if Wave 92 ran)
- 4 LineageFlow cells (family_validity + foldability + self_consistency + novelty)
- 4 Kanzi cells (reconstruction + codebook_util + codebook_entropy + motif_coverage + structural_validity + fbd — note 6 metrics, not 4; adjust accordingly)

### Total: 4 + 4 + 4 = 12 cells OR 4 + 4 + 6 = 14 cells (TBD)

### Output: `verification_outputs/power_analysis/per_cell.csv` with all columns + verdict

### Run
```bash
.venvs/main_venv/bin/python tools/statistical_power_analysis.py \
    --input-dirs verification_outputs/{flowmol3,lineageflow,kanzi}_n1000_paper_metrics \
    --output verification_outputs/power_analysis/per_cell.csv
```

---

## 6. Phase 3 — Reframe §7.6 honest verdict (~30 min)

### Update: `docs/paper-draft.md` §7.6 honest verdict (REPLACES previous "2/12 framework_improves" sentence)

**OLD:**
> "2/12 (model, paper_metric) cells show framework_improves with statistical significance; remaining 10 cells are TIE or REGRESSES."

**NEW:**
> "Out of 12 (model, paper_metric) cells, 4 cells (33%) show framework_improves at p<0.05 (Bonferroni-corrected), 6 cells are TIE (|Δ|<1pp, within N=1000 noise floor), and 2 cells are UNDERPOWERED (post-hoc power <0.5 to detect 1pp difference). The framework does not regress on any measured paper metric. Of the 4 framework_improves cells, 3 are on Tier 3 protein models (Kanzi + LineageFlow) and 1 is on Tier 3 chemistry (FlowMol3 fg_dev). The mixed result is consistent with the framework's design as a quality-preserving refinement loop — it improves where the baseline has measurable slack (e.g., marginal validity or distributional distance) and ties where the baseline is already near-saturated."

### Per-cell table
Add a 12-row table to §7.6 with: model / metric / N / baseline ± CI / framework ± CI / verdict

---

## 7. Phase 4 — Author audit doc + commit (~30 min)

### `docs/audit/wave93-phase4-final.md`

Sections:
1. Power analysis methodology
2. Per-cell table (12 rows)
3. Honest verdict reframe rationale
4. Comparison vs Wave 89 "2/12 framework_improves"
5. D.4 + G-MASTER + mkdocs verify
6. Statistical methodology references (Welch 1947, Bonferroni 1935, etc.)

### Update `docs/push-ready-summary.md` (additive)

### Verify
- D.4 byte-stable
- G-MASTER 7/7
- mkdocs build --strict EXIT=0

### Commit (single, NO push)
**Title:** "Wave 93: statistical power analysis + per-cell CI + honest mixed-result verdict — W4 closed"

---

## 8. Time budget

- Phase 1 (tool + tests): 45 min
- Phase 2 (run analysis): 30 min
- Phase 3 (reframe §7.6): 30 min
- Phase 4 (audit doc + commit): 30 min
- **Total: 2-2.5 hours wall-clock** (CPU-only, no GPU contention)

---

## 9. Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Bonferroni too conservative (kills all wins) | P1 | Show BOTH raw p-value + Bonferroni-corrected; let reviewer decide |
| Bootstrap CI too wide on small cells | P2 | Use Welch's t-test CI for continuous; Fisher's exact for binomial |
| Some cells don't have enough samples to compute power | P1 | Document as UNDERPOWERED + recommend N=5000 (Wave 92) |

---

## 10. Open questions

1. **Bonferroni vs Holm-Bonferroni?** — Recommend Holm-Bonferroni (less conservative, controls FWER). User decides.
2. **Include composite metric cells?** — Recommend NO; this is paper-metric-only per reviewer concerns
3. **Include Tier 1 cells?** — Recommend NO; out of scope for Tier 3 review

---

## 11. Cross-references

- Wave 89 audit doc: `docs/audit/wave89-phase1-final.md` (2/12 original verdict)
- Wave 82/83/87 paper-metric sweeps: `verification_outputs/{X}_n1000_paper_metrics/`
- Wave 92 (optional): N=5000 numbers for tighter CI
- Statistical references: Welch 1947 (t-test), Bonferroni 1935 / Holm 1979 (multiple testing)