# `todo/models/RANKING.md` — Integration order by combined score

**Date:** 2026-09-05
**Purpose:** sort candidate SOTA models by `combined_score =
intrinsic_complexity_score × integration_difficulty_score` (ascending
= easiest first). Per-model analyses live in `todo/models/<model>.md`.
This file is the **integration order** for Phase 3-4.

## Sort key

`combined_score = intrinsic_complexity_score × integration_difficulty_score`
(1-100 scale; ascending = easier to integrate + simpler model).
`claim-reproduction_cost` is listed separately and does NOT enter the
sort.

## Sorted table

| Rank | Model | Domain | Venue | Year | Intrinsic (1-10) | Integration (1-10) | Claim-repro (1-10) | Combined (1-100) | Wave | Status | One-line rationale |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Kanzi** | protein | ICLR 2026 | 2026 | 3 | 5 | 5 | **15** | Wave 11 (proposed) | pending | smallest model in pack (<2 GB, 280M params), GH-only ckpts, fresh protein axis orthogonal to LineageFlow/ProtBFN — Wave 9 R1's "highest ROI" pick |
| 2 | **FreqFlow** | image | CVPR 2026 | 2026 | 5 | 4 | 6 | **20** | Wave 12 (proposed) | pending | SiT-XL/2 backbone already known to framework; FID 1.38 SOTA but saturation risk vs SiT baseline (FID ~2.0); ckpt URL conditional |
| 3 | **MM-FM** | image | CVPR 2026 | 2026 | 5 | 6 | 7 | **30** | Wave 13 (proposed) | pending | DiT-XL/2 + RAE decoder + AutoGuidance are novel glue; 160 GB HF repo requires cherry-pick; FID 2.74 has room vs SiT (NOT saturated) |
| 4 | **LineageFlow** | protein | ICML 2026 | 2026 | 6 | 9 | 9 | **54** | Wave 10 (done; BLOCKED) | partially_integrated | adapter ships but real forward pass BLOCKED on missing `core` source repo; design-only integration candidate |

## Notes on the ranking

1. **Sort order rationale.** Lower `combined_score` = easier to integrate
   + simpler model. Kanzi is the smallest and most modular; FreqFlow
   reuses an architecture we already understand; MM-FM adds novel glue
   (RAE + AutoGuidance); LineageFlow is blocked upstream.

2. **LineageFlow is at rank 4** despite being Wave 10. The ranking reflects
   *current integratability*, not historical order. Wave 10 shipped the
   adapter but cannot run the real model without the `core` source.

3. **Saturation check (LL-002) per model.**
   - **Kanzi** at designability 0.617: NOT saturated (~38% headroom).
   - **FreqFlow** at FID 1.38: NEAR saturation vs SiT baseline FID ~1.96
     (ΔFID 0.58); framework comparison must use N≥5000 + CIs.
   - **MM-FM** at FID 2.74: NOT saturated vs SiT baseline (ΔFID ≥ 0.7);
     clear room for framework improvement.
   - **LineageFlow** at family validity 0.953: already saturated
     (deterministic shim gave 1.0 in both arms → TIE); needs real model
     to differentiate.

4. **Wave assignments are PROPOSED** — they depend on which previous
   wave's results are reproducible. The actual Wave-11/12/13 model
   targets are decided in `EXECUTION-PLAN.md` §Wave 11/12/13 once a
   pre-condition wave ships.

5. **Two CVPR 2026 image candidates (FreqFlow + MM-FM) rank above MM-FM
   only if the user prefers image-axis diversity over protein-axis
   fresh-ground (LineageFlow/Kanzi already cover protein).** If image
   diversity is the goal, Kanzi could be deferred and FreqFlow/MM-FM
   could ship in Wave 11/12.

6. **Excluded candidates** (per `PHASE-2-model-complexity-analysis.md`
   §2.2) are listed in `models/README.md` and the Wave 9 R1/R2/R3
   research docs:
   - Flowception (no public pretrained ckpts)
   - Purrception (7B Lumina-mGPT VQ; too big for 5090)
   - AG-REPA (audio; new axis, not prioritized)
   - HiDream-O1-Image-Dev-2604 (8B; smaller sibling of HiDream-I1,
     which is already integrated)

## Verification (per G-MASTER-PHASE-2)

```bash
cd /home/hugo/codes/flowa-multistep-reinference
ls todo/models/*.md | wc -l         # expect: >= 4 (3 models + README)
test -f todo/models/RANKING.md && echo "RANKING.md exists"
for f in todo/models/{lineageflow,freqflow,mm-fm,kanzi}.md; do
  echo "=== $f ==="
  grep -c "^## " "$f"           # expect: >= 7 (one per section A-G)
done
git status --short                 # expect: empty after commit
```

## See also

- `../PHASE-2-model-complexity-analysis.md` (parent phase + gate spec)
- `../PHASE-4-model-integration-iteration.md` (per-model acceptance
  metrics)
- `README.md` (template + existing files index)
- Wave 9 research: `/tmp/wave9_sota_fm/R{1,2,3}-*/diagnose.md`