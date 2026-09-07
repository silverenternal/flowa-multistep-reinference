# Wave 76 — LineageFlow paper reproduction

**Date:** 2026-09-08
**Status:** IN PROGRESS (Wave 75 committed; this wave activated 2026-09-08)
**Depends on:** Wave 75 commits landed ✓ (verified SHAs 9998580 / 6cd6491 / 39c8cbb)
**Blocks:** Wave 77 (Kanzi paper reproduction)

> **Sample count strategy (revised 2026-09-08):** **N = 1000 samples per arm**
> (baseline + framework), NOT paper's 5000+. See §"Sample count rationale"
> below. Strategy B (partial run, paper protocol unchanged) chosen to bound
> total wall-clock at ~5-10h for all 3 Tier 3 models.

> **Reviewer-proof guarantees (Wave 75-78 master plan §5c, locked 2026-09-08):**
> All Wave 76 work must capture and report these 4 guarantees so reviewers
> can verify every claim in §7.4 with upstream artifacts, not our code.
> See §"Reviewer-proof guarantees" below.

## 1. Goal

Reproduce the 4 paper metrics from LineageFlow (Jinx-byebye, ICML 2026) on our real LineageFlow checkpoint using the vendored upstream pipeline (`data/lineageflow_upstream/`). Then compare framework vs baseline on the same paper metrics.

## 2. Paper metrics + upstream implementation

| Metric | What it measures | Upstream implementation |
|---|---|---|
| family_validity | Profile-HMM scan match (HMMER `hmmscan`) vs Pfam | `evaluation/family_validity_hmmer.py` |
| foldability | OmegaFold pLDDT on predicted structure | `evaluation/foldability_omegafold.py` + `evaluation/run_foldability.py` |
| self_consistency | ESM-IF1 inverse folding perplexity | `evaluation/self_consistency_esmif.py` |
| novelty | MMseqs2 nearest-neighbor identity to training corpus | `evaluation/novelty_mmseqs2.py` |

## 3. Upstream resources (already vendored — fast path)

- Repo: `data/lineageflow_upstream/` (clone of https://github.com/Jinx-byebye/LineageFlow)
- Key dirs: `evaluation/` (4 metric scripts + evaluate_all.py orchestrator), `core/` (model definition), `inference/` (rerouting), `scripts/` (sample runners)
- Eval pipeline: `python evaluation/evaluate_all.py --fasta outputs/generation.fasta --outdir results/eval/run1 --hmmdb databases/pfam35/Pfam-A.hmm --target-db results/mmseqs/pfam_train_gap060_gt80_020 --metrics family_validity foldability self_consistency novelty`
- Config: `config/generation.json` (rp55 checkpoint + default inference params)
- Citation: `citation.bib`

## 4. Constraints

- **CALL upstream `evaluate_all.py`** — do not reimplement
- **Same eval protocol** — same Pfam reference, same MMseqs2 db, same HMMER, same OmegaFold
- **D.4 byte-stable**: 72/72 unchanged
- **Interface-first**: new `--lineageflow-paper-metrics` flag opt-in
- **NO push**

## 5. Phases (5 sequential)

### Phase 1 — READ-ONLY audit + check upstream deps
- Read `data/lineageflow_upstream/evaluation/evaluate_all.py` — confirm all 4 metrics wired
- Check `.venvs/lineageflow_venv` has HMMER (hmmscan binary), OmegaFold, MMseqs2, ESM-IF1 deps
- Document gap in `docs/audit/wave76-phase1-audit.md`
- **No commit**

### Phase 2 — Wire upstream eval into our pipeline (~50-100 LOC)
- Add `tools/lineageflow_paper_metrics.py` (thin wrapper calling upstream `evaluate_all.py` as subprocess)
- Add `--lineageflow-paper-metrics` flag to `tools/run_real_ckpt_eval.py`
- Add 4 unit tests in `tests/test_tools/test_lineageflow_paper_metrics.py` (one per metric, with mocked stdout)
- D.4 verification
- **Commit (NO push)**

### Phase 3 — Reproduce paper numbers on real ckpt
- Smoke test (10 samples) on `data/lineageflow/lineageflow-rp55.ckpt`
- Full reproduction: 1000 samples (paper uses 5000+ but our budget is GPU-bound; document this honestly)
- Generate `outputs/generation.fasta` via `tools/run_real_ckpt_eval.py --model lineageflow --force-mode real --paper-metrics`
- Run `python data/lineageflow_upstream/evaluation/evaluate_all.py --fasta outputs/generation.fasta --outdir results/eval/wave76 --metrics family_validity foldability self_consistency novelty`
- Compare 4 metrics vs paper Table 1
- **NO commit**

### Phase 4 — Run framework on same protocol + per-metric verdict
- Framework runs `--framework-rounds 3` (paper-equivalent: restart-blend with paper's defaults)
- Same 4 paper metrics on framework output fasta
- Per-metric delta vs Phase 3 baseline
- **NO commit**

### Phase 5 — Update paper §7.4 + final synthesis
- §7.4 ADDITIVE Wave 76 paragraph (paper-reproduced numbers)
- `docs/audit/wave76-phase6-final.md` final synthesis
- Update `docs/push-ready-summary.md` (additive)
- D.4 + G-MASTER + mkdocs verify
- **Commit (NO push)**

## 6. Honest caveats

- **Sample count**: paper uses 5000+ samples per family; we may need 1000-2000 (GPU-bound, document as honest caveat)
- **HMMER + OmegaFold deps**: check `.venvs/lineageflow_venv` has all 4 external tools; if missing, document
- **MMseqs2 db**: paper uses pre-computed MMseqs2 db from training corpus — check if vendored in `data/lineageflow_upstream/results/mmseqs/`
- **fasta generation**: need to generate fasta from framework runs (currently our eval outputs JSON, not fasta) — may need small adapter

## 7. Time estimate (revised under strategy B, N=1000)

- Phase 1: ~10 min (audit + dep check)
- Phase 2: ~15-20 min (thin wrapper + tests)
- Phase 3: ~45-60 min (1K samples × 4 metrics: HMMER + OmegaFold pLDDT + ESM-IF1 + MMseqs2)
- Phase 4: ~45-60 min (framework 1K samples × 4 metrics)
- Phase 5: ~10 min (paper update + commit)
- **Total: ~125-160 min wall-clock** (similar to Wave 75)

## 7b. Sample count rationale (mandatory for paper §7.4)

**Why N=1000 instead of paper's 5000+:**

1. **Total wall-clock budget for 3 Tier 3 models**: Strategy B keeps
   FlowMol3 + LineageFlow + Kanzi under ~5-10 hours wall-clock.
   Full-spec would be 30-50 hours (single-GPU serial).
2. **Per-metric statistical power at N=1000**:
   - `family_validity` (HMMER scan, binomial): ±1.5% CI at N=1000,
     ±0.7% at N=5000. ±1.5% is enough to detect a 5% framework
     improvement (typical paper diff for family_validity).
   - `foldability` (OmegaFold pLDDT, continuous): standard error of
     mean ≈ 0.5 at N=1000 vs 0.2 at N=5000. Can detect 1-2 pLDDT
     differences.
   - `self_consistency` (ESM-IF1 perplexity, continuous): standard error
     of mean ≈ 0.05 at N=1000. Enough for sanity check.
   - `novelty` (MMseqs2 NN identity, bounded [0,1]): standard error
     ≈ 0.5% at N=1000. Can detect 2% novelty diff.
3. **OmegaFold pLDDT cost**: ~5-15s per protein at 1000 samples = 1.5-4
   hours. At 5000 samples = 7-20 hours. OmegaFold is the bottleneck.
   ESM-IF1 inference is also heavy.

**What this means for paper §7.4 honest framing:**

- Report N=1000 explicitly
- Frame as "framework vs baseline on the paper-metric protocol at
  reduced sample count due to GPU budget"
- Per-metric verdict with confidence interval where applicable
- If `foldability` (OmegaFold pLDDT) regression appears at N=1000:
  don't claim framework improves foldability — say "framework ties
  ±0.5 pLDDT at N=1000; full paper sample count would tighten CI but
  is not within this paper's GPU budget"

## 7c. Reviewer-proof guarantees (4 external verifiability anchors)

Per Wave 75-78 master plan §5c, every Wave 76 commit must capture and
report these 4 guarantees. Reviewers verify each independently against
upstream artifacts — **no trust in our code or numbers required**.

| # | Guarantee | What this wave must capture |
|---|---|---|
| **G1** | Model weights are upstream release | SHA-256 hash of `data/lineageflow/lineageflow-rp55.ckpt` matches upstream release. Save to `verification_outputs/lineageflow_ckpt_sha256.json` |
| **G2** | Sampling config is upstream default | Baseline calls upstream's LineageFlow sampling entrypoint with paper's default args (no override). Document default args in Wave 76 Phase 1 audit |
| **G3** | Eval pipeline is upstream code | Wave 76 Phase 2 writes **zero LOC metric code**; thin subprocess wrapper calls `data/lineageflow_upstream/evaluation/evaluate_all.py` (HMMER + OmegaFold + ESM-IF1 + MMseqs2). Both arms invoke the same upstream `evaluate_all.py` |
| **G4** | Vendored snapshot is frozen | `data/lineageflow_upstream/` is at the vendored commit hash (capture `git rev-parse HEAD` in Wave 76 Phase 1 audit; if non-git, write hash to `data/lineageflow_upstream/COMMIT.txt`) |

**Why these guarantees kill reviewer attacks on §7.4:**

| Reviewer attack | Defense |
|---|---|
| "你们的 metric 是自己造的" | G3: zero LOC; `evaluate_all.py` is upstream |
| "你们的 baseline sampling config 错了" | G2: we call upstream's default sampling entrypoint |
| "你们的 ckpt 不是官方 release" | G1: SHA-256 verifies against release tag |
| "你们的 upstream code 跟 paper 不一样" | G4: vendored at frozen commit hash |

**Paper §7.4 framing template (locked)**:

> "We apply the framework to LineageFlow (Jinx-byebye et al., ICML
> 2026) without retraining the released checkpoint
> (`data/lineageflow/lineageflow-rp55.ckpt`, SHA-256 verified against
> upstream release). Both baseline (frozen ckpt + upstream
> LineageFlow sampling entrypoint) and framework (frozen ckpt + our
> 3-round re-inference loop) are evaluated using the upstream
> `evaluate_all.py` (vendored at `data/lineageflow_upstream/`, commit
> {HASH}), with the paper's evaluation protocol unchanged: HMMER
> `hmmscan` vs Pfam for family_validity, OmegaFold pLDDT for
> foldability, ESM-IF1 inverse folding perplexity for
> self_consistency, MMseqs2 NN identity for novelty. We run N=1000
> samples per arm due to GPU budget."

## 8. Success criteria

- [ ] All 4 paper metrics called via upstream `evaluate_all.py`
- [ ] Paper Table 1 numbers reproduced within ±5% (or honest caveat if sample count differs)
- [ ] Framework per-metric verdict on paper metrics documented
- [ ] §7.4 updated with paper-reproduced numbers (additive only)
- [ ] D.4 72/72 byte-stable
- [ ] G-MASTER 7/7 PASS
- [ ] mkdocs build --strict EXIT=0
- [ ] NO push

## 9. Risks

- HMMER/OmegaFold/MMseqs2 binaries not in lineageflow_venv → fall back to docs-only audit + caveat
- Upstream eval too slow (> 30 min/sample at 1000 samples) → reduce to 200 samples + document
- framework output format (JSON vs fasta) incompatibility → small adapter
