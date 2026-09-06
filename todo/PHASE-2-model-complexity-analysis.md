# Phase 2 — Model complexity analysis + integration difficulty ranking (one at a time)

**Status:** done (Wave 19 P1A1 — commit a6e574d; 3 per-model analysis files: FreqFlow/MM-FM/Kanzi + todo/models/RANKING.md; 8 sections per model) (+ Wave 21-23: PHASE-3 adapters (Kanzi + FreqFlow) shipped; LineageFlow analysis in todo/models/lineageflow.md; Wave 36: Kanzi + LineageFlow real-ckpt integration; Wave 47-52: composite eval pipelines built on top of these analyses)
**Depends on:** Phase 1 complete (framework + theory + algorithm + conformance
tests all solid)
**Owner:** framework maintainer
**Goal:** for each candidate SOTA model, write a per-model analysis file
capturing (a) intrinsic model complexity (params / FLOPs / dataset / training
compute) and (b) integration difficulty (architecture, weight format, env
deps, paper claim reproduction needs). Then rank them by a single combined
score so Phase 4 has a clear integration order.

## Sub-tasks (one model at a time, per user directive)

### 2.1 Per-model analysis file template
- **Path:** `todo/models/<model-name>.md`
- **Sections:**
  - **A. Identification** — arxiv_id, year, venue, authors, weights URL,
    size, domain.
  - **B. Intrinsic model complexity** — params, FLOPs (inference), training
    compute, dataset size, expected accuracy on standard benchmark.
  - **C. Integration difficulty** — architecture family (DiT / UNet / GNN / etc.),
    weight format (HF / GitHub / proprietary), env deps (flash-attn / dgl / jax),
    inference API clarity, paper-claim reproduction needs (institutional
    weights? sidecar?).
  - **D. Risk profile** — license (commercial / non-commercial), env fragility,
    paper-axis gaps, network reachability.
  - **E. Framework-fit score** — 1-10 on each of {intrinsic complexity,
    integration difficulty, paper-reproduction cost}; combined score.
- **Output:** per-model markdown file.

### 2.2 Models to analyze
Pull from Wave 9 candidate list + any new candidates discovered:

| Model | Venue | Domain | Status |
|---|---|---|---|
| LineageFlow (Wave 10) | ICML 2026 | protein | adapter + baseline-vs-framework done — needs Phase 2 analysis written up |
| Flowception | CVPR 2026 | video | no public pretrained ckpts (analysis only) |
| MM-FM | CVPR 2026 | image DiT-XL/2 | 160 GB repo, complex |
| FreqFlow | CVPR 2026 | image SiT-XL/2 | SOTA FID 1.38, ckpt availability conditional |
| Kanzi | ICLR 2026 | protein (flow-AE) | GitHub-only weights |
| Purrception | ICLR 2026 | image (7B Lumina-mGPT VQ) | too big for 5090 |
| AG-REPA | ICML 2026 | audio | new axis |
| HiDream-O1-Image-Dev-2604 | HF release | image 8B | smaller sibling of HiDream-I1 |

### 2.3 Ranking
- **Sort key:** `intrinsic_complexity_score × integration_difficulty_score`
  ascending. Lower = easier to integrate + simpler model.
- **Result:** `todo/models/RANKING.md` with the sorted list and a one-line
  rationale per model.

## Acceptance

- Per-model analysis file exists for each candidate (`todo/models/*.md`).
- `RANKING.md` has the integrated-order list with combined scores.
- Each analysis references the JMAA paper theorem coverage (where the model's
  application matches Theorem 1's F-side hypotheses).

## Acceptance gate (BINDING — see `todo/GATES.md`)

**Gate name:** `G-MASTER-PHASE-2` (defined in `todo/GATES.md`)

**Pre-condition:** `G-MASTER-PHASE-1` passed AND `G-FRAMEWORK-HEALTH`
hard gates pass (per `todo/framework-internal-metrics.md` §3 — Phase 1
→ Phase 2 entry gate: A.1 ≥ 5/5, A.2 ≥ 2, B.2 = 13/13, B.3 = pass,
B.4 = pass, C.1 ≥ 36, D.2 = 18/18).

**Pass conditions (ALL must hold):**
- [ ] At least 3 candidate models have per-model analysis files in
      `todo/models/` (besides `README.md` template)
- [ ] Each analysis file has all 7 template sections (A. Identification,
      B. Intrinsic complexity, C. Integration difficulty, D. Risk profile,
      E. Framework-fit score, F. Empirical record, G. Next action) populated
      with concrete content (no "pending" / "TBD" placeholders)
- [ ] `todo/models/RANKING.md` exists with all candidate models sorted by
      `combined_score` ascending, each row has a "Wave" field showing
      which Wave will integrate it
- [ ] Each analysis references the JMAA paper theorem coverage
      (LL-001 enforced: ckpt + upstream source both verified before adding
      to ranking; LL-002 enforced: saturation check noted per model)
- [ ] `git status --short` returns empty (G-OPS-CLEAN-WORKING-TREE)
- [ ] `todo/STATUS.md` is up-to-date (G-OPS-TODO-LOG-UPDATED)

**Verification commands:**
```bash
cd /home/hugo/codes/flowa-multistep-reinference
ls todo/models/*.md | wc -l         # expect: >= 4 (3 models + README)
test -f todo/models/RANKING.md && echo "RANKING.md exists"
for f in todo/models/*.md; do
  echo "=== $f ==="
  grep -c "^## " "$f"           # expect: >= 7 (one per section A-G)
done
git status --short                 # expect: empty
```

**Block rule:** if ANY pass condition fails, **Phase 3 cannot start**. Per
the user directive "一个一个来" — write the per-model analyses one at a
time; do not batch.

## Exit criteria (move to Phase 3)

`G-MASTER-PHASE-2` passed.

## Wave 56 close-out

Status refreshed: Per-model analyses (Kanzi, LineageFlow, FreqFlow, MM-FM) are the foundation for the Wave 47-52 composite eval pipelines. PHASE-2 model-complexity analysis continues to feed downstream design decisions in Wave 41-54. Last touched commit: `811ca75` (Wave 55 Agent C: Author todo/INDEX.md master entry point).