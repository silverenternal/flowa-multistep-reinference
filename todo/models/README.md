# `todo/models/` — Per-model analysis files (Phase 2 unit-of-work)

**Date:** 2026-09-05
**Purpose:** one markdown file per candidate SOTA model. Each file
captures intrinsic model complexity + integration difficulty + the empirical
record (what we tried, what worked, what didn't). Phase 2 reads these files to
produce `RANKING.md`; Phase 3-4 update them as glue + integration progresses.

## Template (per-model file structure)

Each `todo/models/<model>.md` should contain:

```
# <Model> — <venue> <year> (<domain>)

**Status:** pending | in_progress | partially_integrated | fully_integrated | blocked
**Wave:** (which wave shipped it, e.g. "Wave 9" or "Wave 10")
**Last updated:** YYYY-MM-DD
**GitHub:** <if not already-integrated>
**HF:** <if not already-integrated>

## A. Identification
- arxiv_id, authors, year, venue
- domain (image / video / molecule / protein / audio / other)
- weights URL, weight file size
- license (commercial / non-commercial / research-only)

## B. Intrinsic model complexity
- params (M / B)
- inference FLOPs (per N samples)
- training compute (GPU days, paper-reported)
- dataset (size, source, license)
- expected metric on standard benchmark

## C. Integration difficulty
- architecture family (DiT / UNet / GNN / Transformer / VAE)
- weight format (HF Hub / GitHub releases / proprietary)
- environment deps (flash-attn / dgl / jax / custom CUDA)
- inference API clarity (well-defined forward? opaque? opaque pickle?)
- paper-claim reproduction needs (institutional weights? sidecar? source repo?)

## D. Risk profile
- license risks
- environment fragility (incompatibilities, version pins)
- paper-axis gaps (vocab mismatch, protocol differences)
- network reachability (sandbox network blocks: drive.google.com, huggingface.co, github.com often blocked)

## E. Framework-fit score
- 1-10 on: intrinsic_complexity_score (lower = simpler model)
- 1-10 on: integration_difficulty_score (lower = easier to integrate)
- combined_score = (intrinsic × integration_difficulty), ascending sort
- 1-10 on: claim-reproduction_cost (lower = closer to paper numbers without heroic effort)

## F. Empirical record (after wave ships)
- Wave X outcome
- baseline-vs-framework result (table)
- claims_supported / claims_diverged
- surprises / blockers

## G. Next action
- (if blocked) what would unblock
- (if partially integrated) what glue is missing
- (if fully integrated) what's next (other models in ranking order?)

## See also
- `../PHASE-2-model-complexity-analysis.md` (parent phase)
- `../lessons-learned.md` (cross-cutting patterns)
- `../STATUS.md` (current state)
```

## Existing files

- `lineageflow.md` — Wave 10 (blocked on missing `core` source)
- (others added as needed)
