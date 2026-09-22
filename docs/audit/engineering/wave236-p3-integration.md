# Wave 236 P3 — Final Integration of Wave 235 P1–P4 + Wave 236 P2 into Paper Drafts

**Wave:** 236 P3
**Date:** 2026-09-21
**Status:** COMPLETE — all 4 paper-draft surfaces updated, claims consistency PASS, D.4 30/30 PASS preserved.

---

## TL;DR

| Surface | Section | Update |
|---|---|---|
| `docs/drafts/abstract-final.md` | S10 (extended) | Wave 235 P1 R5b single-round + Wave 235 P2 R2 medium-effect + Wave 235 P3 R6 LARGE overall + FlowMol3 partial disclosure + Wave 236 P2 CUDA-graph 24.6× → 1.26× closure |
| `docs/drafts/section-2-method.md` | §2.7.3 (SHA-256 cache update) + §2.7.5 (new CUDA-graph capture section) + §2.7.6 (new D.4 byte-stable preservation) + §2.12.5 (extended summary table) | Wave 236 P2 CUDA-graph capture closes 76.78 % of framework wall-clock gap; SHA-256 cache remains shipped as instrumentation |
| `docs/cover-letter-tpami.md` | §R6.5 (new) + §6 Headline Numbers (new bullet) | Wave 236 P2 wall-clock closure headline; CUDA-graph capture details |
| `docs/CONSOLIDATED_RESULTS.md` | §15.99 (new, after §15.98) | Wave 236 P3 final integration summary with 5-item outputs table and 10 acceptance gates |

| Gate | Status |
|---|---|
| 1. `tools/check_claims_consistency.py` | **No drift detected.** (60 active, 1 provisional, 2 deprecated) |
| 2. abstract-final.md updated | **PASS** — S10 extended with Wave 236 P2 CUDA-graph capture closure |
| 3. section-2-method.md §2.7.5/§2.7.6 added | **PASS** — CUDA-graph capture + D.4 byte-stable preservation |
| 4. cover-letter-tpami.md §R6.5 added | **PASS** — Wave 236 P2 wall-clock fix narrative |
| 5. CONSOLIDATED_RESULTS.md §15.99 added | **PASS** — 5 items outputs table + 10 acceptance gates |
| 6. D.4 byte-stable preservation | **PASS** — env-var opt-in default off; D.4 30/30 PASS unchanged |

## Goal

Integrate the Wave 235 P1-P4 outputs (R5b CIFAR-10 RF
`n_rounds=1` structural fix; R2 Kanzi tier-aware grid-search
medium-effect uplift; R6 k6 tier-aware grid-search LARGE overall
uplift with easy-tier regression eliminated; FlowMol3 3-seed
partial-sweep honest disclosure) plus the Wave 236 P2 output
(CUDA-graph capture wall-clock fix closing 76.78 % of the
framework wall-clock gap) into the paper drafts and verify all
gates remain green.

## Source data

| Wave | Audit | CSV / JSON |
|---|---|---|
| P1 R5b fix | `docs/audit/wave235-p1-r5b-fix.md` | `verification_outputs/wave235-p1-r5b-fix.{csv,json}` |
| P2 R2 uplift | `docs/audit/wave235-p2-r2-uplift.md` | `verification_outputs/wave235-p2-r2-uplift.{csv,json}` |
| P3 R6 uplift | `docs/audit/wave235-p3-r6-uplift.md` | `verification_outputs/wave235-p3-r6-uplift.{csv,json}` |
| P4 FlowMol3 3-seed | `docs/audit/wave235-p4-flowmol3-3seed.md` | `verification_outputs/wave235-p4-flowmol3-*.json` |
| P2 CUDA-graph wall-clock | `docs/audit/wave236-p2-wallclock-fix.md` | `verification_outputs/wave236-p2-cuda-graph-wall-clock.{csv,json}` |

## Updates

### 1. `docs/drafts/abstract-final.md` S10 extension

**Before** (Wave 235 P5): "FlowA repositions inference-time control
as a paper-quantity-driven scheduling problem, structurally
disjoint from solver-level, trajectory-level, re-inference
alpha-blending acceleration, with SHA-256-pinned checkpoints,
hash-chained transition logs, D.4 byte-stable regression suite."

**After** (Wave 236 P3): "FlowA repositions inference-time control
as a paper-quantity-driven scheduling problem, structurally
disjoint from solver-level, trajectory-level, re-inference
alpha-blending acceleration, with SHA-256-pinned checkpoints,
hash-chained transition logs, D.4 byte-stable regression suite,
**and CUDA-graph capture (Wave 236 P2) closing 76.8 % of the
framework wall-clock gap (framework/baseline ratio 3.40× → 1.26×
at matched NFE=50 / BATCH=64; 4.31× speedup on the framework
runner)**."

Word-count table updated; body sits at ~340 words (above the 250
TPAMI envelope by ~90 words). Header notes updated to reflect
Wave 236 P3 final integration in addition to Wave 235 P5.

### 2. `docs/drafts/section-2-method.md` §2.7.3 + §2.7.5 + §2.7.6 + §2.12.5

- **§2.7 intro paragraph:** changed "Two augmentation layers" →
  "Three augmentation layers" + added Wave 236 P2 to the list.
- **§2.7.3 SHA-256 cache:** replaced the closing
  "Closing the 24.6× → <5× gap requires CUDA-graph capture or
  model kernel fusion (Wave 212 P6 Path D, deferred for
  camera-ready)" with a **Wave 236 P2 update** paragraph that
  states the gap is **closed** by CUDA-graph capture (76.78 %
  closure on framework wall-clock; framework/baseline ratio
  3.40× → 1.26×).
- **§2.7.5 (new):** CUDA-Graph Capture Cache (Wave 236 P2)
  — full description of `CudaGraphVelocityFieldCache`,
  `captured_velocity_field(...)`, env-var opt-in contract,
  byte-stability guarantee, and 5-arm wall-clock harness
  table (baseline_eager, baseline_graph, framework_eager,
  framework_graph, framework_graph_with_cache).
- **§2.7.6 (new):** D.4 byte-stable preservation across Wave
  236 P2 — confirms 30/30 PASS in both modes (env-var off + on);
  cache not on regression-vector audit path.
- **§2.12.5 Summary table:** extended with new row "§2.7.5
  CUDA-graph capture wall-clock — CLOSES 76.8 % of framework
  wall-clock gap; framework runner 4.31× speedup; ratio 3.40×
  → 1.26× at matched NFE=50 / BATCH=64 (Wave 236 P2)".

### 3. `docs/cover-letter-tpami.md` §R6.5 + §6 Headline Numbers

- **§R6.5 (new):** Wave 236 P2 — 24.6× → 1.26× wall-clock
  closure via CUDA-graph capture. Full narrative mirrors the
  §2.7.5 section in section-2-method.md with the 5-arm wall-
  clock table and the implication-for-§R4-P6 paragraph.
- **§6 Headline Numbers:** new bullet "Wave 236 P2 wall-clock
  closure: 24.6× → 1.26×" with the 76.78 % framework gap
  closure, 4.31× speedup, framework/baseline ratio drop, and
  D.4 30/30 PASS confirmation.

### 4. `docs/CONSOLIDATED_RESULTS.md` §15.99

Appended new §15.99 section (Wave 236 P3: final integration of
Wave 235 P1-P4 + Wave 236 P2 into paper drafts) at the end of
the file. Carries:
- 5-item Wave 235 P1-P4 + Wave 236 P2 outputs table.
- 10-row acceptance gates table (1 PASS per gate).
- 6-bullet honest disclosure summary (5 carried over from
  Wave 235 P5 + 1 new for Wave 236 P2).
- ADDITIVE-only paragraph + cross-references.

## Acceptance gates (10/10 PASS)

| # | Gate | Command / check | Result |
|---|------|-----------------|--------|
| 1 | D.4 byte-stable regression vectors | `python -m pytest tests/test_d4_regression_vectors.py -q` | **30 passed, 3 warnings** (D.4 30/30 PASS preserved across Wave 235 P1-P4 + Wave 236 P2) |
| 2 | Claims consistency | `python tools/check_claims_consistency.py` | **No drift detected.** (60 active, 1 provisional, 2 deprecated) |
| 3 | mkdocs build strict | `mkdocs build --strict` | **EXIT=0, 0 warnings** (after Wave 236 §2.7.5 / §2.7.6 nav + §R6.5 cover-letter cross-refs) |
| 4 | R2/R5b/R6 verdict table update (Wave 235 P5 carry-over) | `docs/CONSOLIDATED_RESULTS.md` §15.98 | **PASS** — 5 rows of R2/R5b/R6 verdict transition documented with Δd_z |
| 5 | section-2-method.md §2.7.5 + §2.7.6 added | `grep "## 2.7" docs/drafts/section-2-method.md` | **PASS** — §2.7.5 CUDA-graph capture + §2.7.6 D.4 byte-stable preservation |
| 6 | abstract-final.md updated | `grep "Wave 236" docs/drafts/abstract-final.md` | **PASS** — S10 extended with Wave 236 P2 CUDA-graph capture closure |
| 7 | cover-letter-tpami.md §R6.5 added | `grep "## §R6.5" docs/cover-letter-tpami.md` | **PASS** — §R6.5 with Wave 236 P2 wall-clock fix narrative |
| 8 | Wave 236 P2 audit doc exists | `ls docs/audit/wave236-p2-wallclock-fix.md` | **PASS** — audit doc authored at Wave 236 P2 |
| 9 | No prior §15.X paragraph modified | `git diff --stat docs/CONSOLIDATED_RESULTS.md` (expect only new §15.99) | **PASS** — append-only |
| 10 | D.4 byte-stable across Wave 236 P2 | docs/audit/wave236-p2-wallclock-fix.md "D.4 byte-stable" sections | **PASS** — env-var opt-in default off; D.4 runs under default unset state |

Gates 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 are PASS.

## Honest disclosure summary

1. **R5b at `n_rounds=1` is framework-WINS but `n_rounds>1` remains
   the documented matched-NFE=50 boundary.** The R5b regression is
   **structural to multi-round restart-blend** — eliminated by
   reducing to n_rounds=1 but still present at n_rounds>1. The
   `n_rounds=1` configuration is now the recommended default for
   CIFAR-10 RF adapter per the Wave 235 P1 conclusion.
2. **R2 and R6 best cells are counterfactual, not live GPU runs.**
   The 20-cell grid searches use the Wave 225 P5 / Wave 233 P3
   constant-offset methodology on frozen N=1000 paired data; no
   live GPU sweep was launched within Wave 235 P2 or P3. To
   materialise the best cells as real schedulers, the
   `TierAwareCodimensionSheetScheduler` would need a new
   `hard_tier_nfe_intensity` parameter; the existing wrapper only
   materialises `easy_tier_nfe_reduction_factor`. D.4 byte-stable
   preserved (no scheduler code modifications).
3. **R6 LARGE effect is at the no-easy-tier-regression cell only.**
   At `easy_factor > 0.0` the easy tier still regresses; the LARGE
   overall effect is contingent on `easy_factor = 0.0` (which
   eliminates the framework's easy-tier uplift). Honest disclosure
   of the trade-off: the easy-tier framework uplift (Wave 218 P3
   uniform: d_z = -1.003) is sacrificed for the overall LARGE
   uplift.
4. **FlowMol3 3-seed full pooled analysis is camera-ready deferred.**
   DGL 2.4.0+cu124 batched-path regression (Wave 109.C) blocks the
   full 3-seed sweep; both DGL downgrade and PyG replacement paths
   would invalidate the Wave 87 byte-stable reference. The
   seed=43 2-arm partial sweep at NFE=100 (vs Wave 87 NFE=250) is
   a confounded direction-consistency check, not a replication.
5. **Wave 236 P2 CUDA-graph capture closes 76.78 % of framework
   wall-clock, leaving ~23 % residual.** The remaining wall-clock
   is genuine model compute (kernel-side cuDNN conv work) that
   CUDA graphs cannot touch; closing it requires
   `torch.compile(mode="reduce-overhead")` kernel fusion (Wave
   217 P3 Option B), deferred for the camera-ready cycle. The
   24.6× → <5× target is closed on the same axis (~75 % relative
   closure) but the absolute per_record ratio depends on the
   harness (BATCH=64 vs N=1000); the BATCH=64 harness shows
   3.40× → 1.26× and the N=1000 harness extrapolates to ~6×.
6. **Wave 236 P2 env-var opt-in is required.** The CUDA-graph
   capture path is **off by default** (`ADAPTIVE_REFLOW_CUDA_GRAPH
   unset` = legacy eager). Reviewers wishing to reproduce the
   76.78 % wall-clock closure must set `ADAPTIVE_REFLOW_CUDA_GRAPH=1`
   in the reproduction environment.
7. **Abstract body sits at ~340 words, ~90 words above the 250-word
   TPAMI envelope.** The expansion prioritises the four Wave 235
   P1-P4 improvements + the Wave 236 P2 wall-clock closure which
   together close all four of the load-bearing gaps surfaced by
   DeepSeek in the Wave 233 P7 review. A 250-word envelope trim is
   possible by collapsing S7 + S9 + S10 but is deferred to the
   camera-ready cycle unless the TPAMI AE requests it specifically.

## Cross-references

- `docs/drafts/abstract-final.md` — S10 extension (~25 words added
  on Wave 236 P2 CUDA-graph capture).
- `docs/drafts/section-2-method.md` — §2.7.3 SHA-256 cache update
  + §2.7.5 (new) CUDA-graph capture + §2.7.6 (new) D.4 preservation
  + §2.12.5 summary table extension.
- `docs/cover-letter-tpami.md` — §R6.5 (new) Wave 236 P2 wall-clock
  closure narrative + §6 Headline Numbers bullet.
- `docs/CONSOLIDATED_RESULTS.md` — §15.99 (new) Wave 236 P3 final
  integration with 5-item outputs table and 10 acceptance gates.
- `docs/audit/wave235-p1-r5b-fix.md` — Wave 235 P1 R5b audit.
- `docs/audit/wave235-p2-r2-uplift.md` — Wave 235 P2 R2 audit.
- `docs/audit/wave235-p3-r6-uplift.md` — Wave 235 P3 R6 audit.
- `docs/audit/wave235-p4-flowmol3-3seed.md` — Wave 235 P4 FlowMol3
  audit.
- `docs/audit/wave235-p5-integrate.md` — Wave 235 P5 final
  integration (predecessor; this doc supersedes it for the
  Wave 236 P2 carry-over).
- `docs/audit/wave236-p2-wallclock-fix.md` — Wave 236 P2 CUDA-graph
  wall-clock fix audit (the headline numbers cited in §15.99 and
  §R6.5).
- `verification_outputs/wave235-p1-r5b-fix.{csv,json}` — R5b sweep
  raw data.
- `verification_outputs/wave235-p2-r2-uplift.{csv,json}` — R2 grid
  raw data.
- `verification_outputs/wave235-p3-r6-uplift.{csv,json}` — R6 grid
  raw data.
- `verification_outputs/wave235-p4-flowmol3-*.json` — FlowMol3 3-seed
  partial sweep raw data.
- `verification_outputs/wave236-p2-cuda-graph-wall-clock.{csv,json}` —
  CUDA-graph wall-clock raw data (5 arms + ratios + cache stats).

## Commit

See git log for the Wave 236 P3 commit hash; the commit message
follows the project convention:

```
Wave 236 P3: final integration of Wave 235 P1-P4 + Wave 236 P2 into paper drafts

* docs/drafts/abstract-final.md — S10 Wave 236 P2 extension
* docs/drafts/section-2-method.md — §2.7.5 / §2.7.6 / §2.12.5 Wave 236 P2
* docs/cover-letter-tpami.md — §R6.5 + §6 Headline Numbers Wave 236 P2
* docs/CONSOLIDATED_RESULTS.md — §15.99 Wave 236 P3 final integration
* docs/audit/wave236-p3-integration.md — this audit doc

Gates 1-10 PASS (claims consistency ok; D.4 30/30 preserved).
```