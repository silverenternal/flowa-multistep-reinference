# Wave 77 — Kanzi paper reproduction

**Date:** 2026-09-08
**Status:** PLANNED (waits for Wave 76)
**Depends on:** Wave 76 commits landed
**Blocks:** Wave 78 (cross-tier synthesis)

> **Sample count strategy (revised 2026-09-08):** **N = 1000 samples per arm**
> (baseline + framework), unless Kanzi paper specifies otherwise in Phase 1
> audit. See §"Sample count rationale" below. Strategy B (partial run,
> paper protocol unchanged) chosen to bound total wall-clock at ~5-10h
> for all 3 Tier 3 models.

## 1. Goal

Reproduce Kanzi paper metrics (likely FBD / perplexity / motif coverage / structural validity — to be confirmed in Phase 1) on our real Kanzi checkpoint using upstream repo. Then compare framework vs baseline on the same paper metrics.

## 2. Pre-requisite (NEW vs Wave 75/76)

**Kanzi upstream repo is NOT vendored** — only model ckpts in `data/kanzi_ckpt/cleaned_model.pt` + `data/kanzi_ckpt/kanzi_encoder.pt`. Wave 77 must include a clone step before audit can begin.

## 3. Step 0 — Clone Kanzi upstream (NEW pre-Phase)

- Confirm Kanzi paper GitHub URL (likely https://github.com/.../Kanzi from ICLR 2026)
- Read `docs/models/kanzi.model_card.md` to find the URL
- `git clone <kanzi-url> data/kanzi_upstream/`
- Verify `data/kanzi_upstream/evaluation/` (or similar) exists
- Document pre-Phase result

## 4. Phase 1 — READ-ONLY audit + identify paper metrics
- Read Kanzi paper / model card / upstream README for actual reported metrics
- Map metrics to upstream evaluation code (file:line)
- Check `.venvs/kanzi_venv` has all required deps
- Map our current composite (entropy_reduction + max_prob_delta + argmax_turnover) to upstream
- Document in `docs/audit/wave77-phase1-audit.md`
- **No commit**

## 5. Phase 2 — Wire upstream eval into our pipeline
- Same pattern as Wave 76: thin wrapper calling upstream eval as subprocess
- New `--kanzi-paper-metrics` flag on `tools/run_real_ckpt_eval.py`
- Per-metric unit tests
- D.4 verification
- **Commit (NO push)**

## 6. Phase 3 — Reproduce paper numbers on real ckpt
- Smoke test (10 samples)
- Full reproduction on `data/kanzi_ckpt/cleaned_model.pt` via `.venvs/kanzi_venv`
- Compare vs paper target (specific numbers TBD after Phase 1 audit)
- **NO commit**

## 7. Phase 4 — Run framework on same protocol
- Framework runs `--framework-rounds 3`
- Same paper metrics on framework output
- Per-metric delta vs Phase 3 baseline
- **NO commit**

## 8. Phase 5 — Update paper §7.3 + final synthesis
- §7.3 ADDITIVE Wave 77 paragraph (paper-reproduced numbers)
- `docs/audit/wave77-phase6-final.md` final synthesis
- Update `docs/push-ready-summary.md` (additive)
- D.4 + G-MASTER + mkdocs verify
- **Commit (NO push)**

## 9. Constraints

- **Step 0 (clone) must succeed** — if Kanzi upstream is private/404, escalate
- **Same eval protocol** as paper
- **D.4 byte-stable**: 72/72 unchanged
- **Interface-first**: `--kanzi-paper-metrics` flag opt-in
- **NO push**

## 10. Honest caveats (more than Wave 75/76)

- **Upstream not vendored yet** — Phase 1 may reveal Kanzi upstream is private or requires special access
- **Paper metrics unknown** — need Phase 1 audit to confirm what Kanzi paper actually reports
- **FBD / perplexity / motif coverage may require heavy deps** — UMAP / ESM-2 650M / MSA search etc.
- **Sample count**: Kanzi paper sample count TBD

## 11. Time estimate (revised under strategy B, N=1000)

- Step 0 (clone): ~5-15 min (depends on repo size + network)
- Phase 1: ~10-15 min (audit — identify paper metrics + sample count)
- Phase 2: ~15-20 min (wire eval)
- Phase 3: ~45-60 min (1K samples + upstream eval)
- Phase 4: ~45-60 min (framework 1K samples + upstream eval)
- Phase 5: ~10 min (paper update + commit)
- **Total: ~130-180 min wall-clock** (similar to Wave 75/76)

## 11b. Sample count rationale (mandatory for paper §7.3)

**Why N=1000 unless paper specifies otherwise:**

1. **Total wall-clock budget for 3 Tier 3 models**: Strategy B keeps
   FlowMol3 + LineageFlow + Kanzi under ~5-10 hours wall-clock.
   Full-spec would be 30-50 hours (single-GPU serial).
2. **Kanzi-specific** (Phase 1 audit will confirm exact metrics):
   - If FBD / perplexity (continuous): standard error ≈ 0.5% at N=1000
   - If motif coverage (binomial): ±1.5% CI at N=1000
   - If structural validity (binomial): ±1.5% CI at N=1000
3. **ESM-2 perplexity cost** (if applicable): ~2-5s per sequence at
   N=1000 = 30-80 min. At 5000+ = 2.5-7 hours.

**What this means for paper §7.3 honest framing:**

- Report N=1000 explicitly (unless paper specifies otherwise)
- Frame as "framework vs baseline on the paper-metric protocol at
  reduced sample count due to GPU budget"
- Per-metric verdict with confidence interval where applicable

## 11c. Reviewer-proof guarantees (4 external verifiability anchors)

Per Wave 75-78 master plan §5c, every Wave 77 commit must capture and
report these 4 guarantees. Reviewers verify each independently against
upstream artifacts — **no trust in our code or numbers required**.

| # | Guarantee | What this wave must capture |
|---|---|---|
| **G1** | Model weights are upstream release | SHA-256 hash of `data/kanzi_ckpt/cleaned_model.pt` matches upstream release. Save to `verification_outputs/kanzi_ckpt_sha256.json` |
| **G2** | Sampling config is upstream default | Baseline calls upstream's Kanzi sampling entrypoint with paper's default args (no override). Document default args in Wave 77 Phase 1 audit (after clone) |
| **G3** | Eval pipeline is upstream code | Wave 77 Phase 2 writes **zero LOC metric code**; thin subprocess wrapper calls the Kanzi upstream evaluation script (TBD after clone, e.g. `evaluate.py` or `compute_metrics.py`). Both arms invoke the same upstream eval script |
| **G4** | Vendored snapshot is frozen | **Step 0 clone** records upstream commit hash (after `git clone`, run `git rev-parse HEAD` and save to `data/kanzi_upstream/COMMIT.txt`) |

**Why these guarantees kill reviewer attacks on §7.3:**

| Reviewer attack | Defense |
|---|---|
| "你们的 metric 是自己造的" | G3: zero LOC; upstream's eval script |
| "你们的 baseline sampling config 错了" | G2: we call upstream's default sampling entrypoint |
| "你们的 ckpt 不是官方 release" | G1: SHA-256 verifies against release tag |
| "你们的 upstream code 跟 paper 不一样" | G4: vendored at frozen commit hash captured in Step 0 |

**Paper §7.3 framing template (locked)**:

> "We apply the framework to Kanzi (ICLR 2026) without retraining the
> released checkpoint (`data/kanzi_ckpt/cleaned_model.pt`, SHA-256
> verified against upstream release). Both baseline (frozen ckpt +
> upstream Kanzi sampling entrypoint) and framework (frozen ckpt + our
> 3-round re-inference loop) are evaluated using the upstream
> {EVAL_SCRIPT} (vendored at `data/kanzi_upstream/`, commit {HASH}),
> with the paper's evaluation protocol unchanged: {paper metric 1},
> {paper metric 2}, {paper metric 3} — to be filled in after Phase 1
> audit. We run N=1000 samples per arm due to GPU budget."

## 12. Success criteria

- [ ] Kanzi upstream cloned successfully
- [ ] Paper metrics identified + reproduced within ±5% (or honest caveat)
- [ ] Framework per-metric verdict on paper metrics documented
- [ ] §7.3 updated with paper-reproduced numbers (additive only)
- [ ] D.4 72/72 byte-stable
- [ ] G-MASTER 7/7 PASS
- [ ] mkdocs build --strict EXIT=0
- [ ] NO push

## 13. Risks

- Kanzi upstream private / 404 → Step 0 fails, escalate
- Paper metrics require heavy deps not in kanzi_venv → document as honest limitation
- Upstream eval too slow at scale → reduce to minimum viable sample count
