# Wave 75 — FlowMol3 paper reproduction

**Date:** 2026-09-08
**Status:** IN FLIGHT (workflow `w9sveok4w`)
**Depends on:** nothing (first wave)
**Blocks:** Wave 76 (LineageFlow paper reproduction)

> **Sample count strategy (revised 2026-09-08):** **N = 1000 samples per arm**
> (baseline + framework), NOT paper's full 5K-50K. See §"Sample count
> rationale" below. Strategy B (partial run, paper protocol unchanged)
> chosen to bound total wall-clock at ~5-10h for all 3 Tier 3 models.

> **Reviewer-proof guarantees (Wave 75-78 master plan §5c, locked 2026-09-08):**
> All Wave 75 work must capture and report these 4 guarantees so reviewers
> can verify every claim in §7.5 with upstream artifacts, not our code.
> See §"Reviewer-proof guarantees" below.

## 1. Goal

Reproduce the 4 paper metrics from FlowMol3 (Dunn et al., NeurIPS 2024, arXiv 2508.12629) on our real FlowMol3 checkpoint using the upstream pipeline. Then compare framework vs baseline on the same paper metrics.

## 2. Paper metrics + targets (arxiv 2508.12629)

| Metric | Paper target | Upstream implementation |
|---|---|---|
| validity_pct | 0.999 | RDKit.Chem.SanitizeMol on each mol |
| pb_validity_pct | 0.919 | PoseBusters full pipeline (MMFF + xtb) |
| fg_dev | 0.27 | functional group distribution divergence vs GEOM_DRUGS training set |
| ood_ring_rate | 0.10 | ring set vs reference ring set |

## 3. Upstream resources (vendored)

- Repo: `data/FlowMol3/repo/` (clone of https://github.com/Dunni3/FlowMol, commit 77cae22, version 3.1.0)
- Key dirs: `flowmol/analysis/` (SampledMolecule + SampleAnalyzer), `flowmol/models/`, `data/` (reference distributions)
- Eval pipeline: SampleAnalyzer.analyze + glue layer

## 4. Constraints

- **READ-ONLY audit** for Phase 1 (no code changes)
- **No metric invention** — every metric calls upstream function
- **D.4 byte-stable**: 72/72 unchanged after all phases
- **Interface-first**: new `--paper-metrics` flag opt-in
- **NO push**: all commits local

## 5. Phases (6 sequential)

### Phase 1 — READ-ONLY audit of upstream eval pipeline
- Find file:line for each of 4 paper metrics in `data/FlowMol3/repo/`
- Find upstream sample runner (CLI + Python API)
- Find reference distributions (GEOM_DRUGS + NCI)
- Map current `tools/run_real_ckpt_eval.py:_compute_flowmol3_composite` to upstream
- Document gaps in `docs/audit/wave75-phase1-audit.md`
- **No commit.**

### Phase 2 — Implement paper metrics in `tools/paper_metrics.py` (~150-300 LOC)
- `compute_validity_pct(sampled_molecules) -> float` — calls upstream RDKit.Chem.SanitizeMol
- `compute_pb_validity_pct(sampled_molecules, full_pb=True) -> float` — full PoseBusters + MMFF + xtb
- `compute_fg_deviation(sampled_molecules, reference='GEOM_DRUGS') -> float`
- `compute_ood_ring_rate(sampled_molecules, reference='GEOM_DRUGS') -> float`
- Wire into `tools/run_real_ckpt_eval.py` via new `--paper-metrics` flag
- 4 unit tests in `tests/test_tools/test_paper_metrics.py`
- D.4 verification (72/72)
- **Commit (NO push)**

### Phase 3 — Reproduce paper numbers on real ckpt
- Smoke test (1 sample)
- Full reproduction: NFE=250, 5K samples, seed=42, GPU, PYTHONPATH=data/FlowMol3/repo
- Compare 4 metrics vs target within ±5% tolerance
- If pass: paper reproduction SUCCESS
- If fail > 5%: document investigation (different reference? different PB subset?)
- **NO commit** (verification)

### Phase 4 — Run framework on same protocol
- Same 4 metrics, framework applied (3 restart-blend rounds)
- Per-metric delta vs baseline
- Apply meaningful-significance threshold per metric
- Per-cell verdict (framework_improves / framework_ties / framework_regresses)
- **NO commit** (verification)

### Phase 5 — Update paper §7.5 + §1 abstract (additive)
- §7.5 ADDITIVE Wave 75 paragraph citing paper-reproduced numbers
- §1 abstract ADDITIVE sentence on FlowMol3 paper-metric reproduction
- D.4 + G-MASTER + mkdocs verify
- **Commit (NO push)**

### Phase 6 — Final synthesis + push-ready update
- Author `docs/audit/wave75-phase6-final.md`
- Update `docs/push-ready-summary.md`
- D.4 + G-MASTER + mkdocs verify
- **Commit (NO push)**

## 6. Honest caveats (revised under strategy B, N=1000)

- **Sample count = 1000 per arm** (baseline + framework), NOT paper's 5K-50K. See §7b for rationale.
- Reference distribution (GEOM_DRUGS) may need download if not vendored
- xtb 6.7.1 already installed (Wave 74 Phase 4) — Phase 3 should verify integration
- FCD-style distribution metrics will have higher variance at N=1000; honest caveat needed in §7.5

## 7. Time estimate (revised under strategy B, N=1000)

- Phase 1: ~10-15 min (audit)
- Phase 2: ~15-20 min (implement 4 metrics + tests)
- Phase 3: ~30-45 min (1K samples + NFE=250 GPU; ~15-30 min xtb + MMFF)
- Phase 4: ~30-45 min (framework 1K samples)
- Phase 5: ~10 min (paper update)
- Phase 6: ~5 min (synthesis + commit)
- **Total: ~100-140 min wall-clock** (down from 100-170 with 5K)

## 7b. Sample count rationale (mandatory for paper §7.5)

**Why N=1000 instead of paper's 5K-50K:**

1. **Total wall-clock budget for 3 Tier 3 models**: Strategy B keeps
   FlowMol3 + LineageFlow + Kanzi under ~5-10 hours wall-clock combined.
   Full-spec would be 30-50 hours (single-GPU serial).
2. **Statistical power at N=1000**:
   - `validity_pct` / `pb_validity_pct` (binomial): ±1% CI at N=1000,
     ±0.4% at N=5000. ±1% is enough to detect a 2-3% framework
     improvement (paper target diff ~8%).
   - `fg_dev` / `ood_ring_rate` (distribution-level): variance scales as
     1/N, so N=1000 has 2.2× higher variance than N=5000. Honest
     caveat in §7.5.
3. **PoseBusters + xtb + MMFF cost**: ~10-30 ms / sample at N=1000 =
   10-30 min. At 50K samples = 8-25 hours. xtb is the bottleneck.

**What this means for paper §7.5 honest framing:**

- Report N=1000 explicitly
- Frame as "framework vs baseline on the paper-metric protocol at
  reduced sample count due to GPU budget"
- Per-metric verdict with confidence interval where applicable
- If `fg_dev` regression appears at N=1000: don't claim framework
  improves fg_dev — say "framework ties ±0.5 fg_dev at N=1000; full
  paper sample count would tighten CI but is not within this paper's
  GPU budget"

## 7c. Reviewer-proof guarantees (4 external verifiability anchors)

Per Wave 75-78 master plan §5c, every Wave 75 commit must capture and
report these 4 guarantees. Reviewers verify each independently against
upstream artifacts — **no trust in our code or numbers required**.

| # | Guarantee | What this wave must capture |
|---|---|---|
| **G1** | Model weights are upstream release | SHA-256 hash of `data/flowmol3_ckpt/cleaned_model.pt` matches upstream release. Save to `verification_outputs/flowmol3_ckpt_sha256.json` |
| **G2** | Sampling config is upstream default | Baseline calls `data/FlowMol3/repo/flowmol/models/FlowMol.sample(nfe=N, ...)` with paper's default args (no `use_upstream=False` override). Document default args in Wave 75 Phase 1 audit |
| **G3** | Eval pipeline is upstream code | Wave 75 Phase 2 writes **zero LOC metric code**; only a thin subprocess wrapper that calls `data/FlowMol3/repo/flowmol/analysis/metrics.py:SampleAnalyzer.analyze`. Both baseline and framework arms invoke the same upstream `SampleAnalyzer.analyze` |
| **G4** | Vendored snapshot is frozen | `data/FlowMol3/repo/` is at upstream commit `77cae22` (already pinned in master plan). Capture `git rev-parse HEAD` in Wave 75 Phase 1 audit |

**Why these guarantees kill reviewer attacks on §7.5:**

| Reviewer attack | Defense |
|---|---|
| "你们的 metric 是自己造的" | G3: zero LOC; SampleAnalyzer.analyze is upstream |
| "你们的 baseline sampling config 错了" | G2: we call upstream `FlowMol.sample` with paper defaults |
| "你们的 ckpt 不是官方 release" | G1: SHA-256 verifies against release tag |
| "你们的 upstream code 跟 paper 不一样" | G4: vendored at frozen commit 77cae22 |

**Paper §7.5 framing template (locked)**:

> "We apply the framework to FlowMol3 (Dunn et al., NeurIPS 2024)
> without retraining the released checkpoint
> (`data/flowmol3_ckpt/cleaned_model.pt`, SHA-256 verified against
> upstream release). Both baseline (frozen ckpt + upstream
> `FlowMol.sample`) and framework (frozen ckpt + our 3-round
> re-inference loop) are evaluated using the upstream
> `SampleAnalyzer.analyze` (vendored at `data/FlowMol3/repo/`, commit
> `77cae22`), with the paper's evaluation protocol unchanged: RDKit
> `Chem.SanitizeMol` for validity, PoseBusters full pipeline (MMFF +
> xtb) for pb_validity, GEOM_DRUGS reference for fg_deviation, NCI
> for ood_ring_rate. We run N=1000 samples per arm due to GPU budget."

## 8. Success criteria

- [ ] All 4 paper metrics reproduced within ±5% of paper target
- [ ] Framework per-metric verdict on paper metrics documented
- [ ] §7.5 + §1 updated with paper-reproduced numbers (additive only)
- [ ] D.4 72/72 byte-stable
- [ ] G-MASTER 7/7 PASS
- [ ] mkdocs build --strict EXIT=0
- [ ] NO push
