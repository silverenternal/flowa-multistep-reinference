# Wave 43 Agent B — Paper writeup Tier 3 (Kanzi + LineageFlow) audit

**Date:** 2026-09-05
**Owner:** Wave 43 Agent B (paper-tier3-writeup)
**Parent task:** `todo/wave43-problems-review.md` Problem 4
**Disjoint file scope:** `docs/paper-draft.md`, `docs/figures/tier3_real_ckpt_signed_mean.png`,
`docs/audit/wave43-paper-tier3-writeup.md` (this file), `README.md`,
`tools/_make_wave42_figure.py` (note-text-only update)
**Status:** COMPLETE — paper Tier 3 section updated, figure regenerated,
README Tier 3 evidence section appended, this audit authored, no
experiments re-run, no framework code touched.

---

## 1. Scope (what was touched vs not)

**Touched (additive):**

| File | Change |
|---|---|
| `docs/paper-draft.md` | §7 — added **one-sentence claim statement** at top; **honest verdict block** enumerating closed vs pending items; **cross-link** to `docs/CONSOLIDATED_RESULTS.md` §15.8–§15.10; new **§7.6 Wave 43 Agent B paper-tier3-writeup (this wave)** subsection documenting the Wave 43 artefacts |
| `docs/figures/tier3_real_ckpt_signed_mean.png` | Regenerated from `tools/_make_wave42_figure.py` with the updated honest-reading note text (no data change) |
| `tools/_make_wave42_figure.py` | Updated only the **note text** to reference the Wave 43 WF1 metric-layer fix + §15.10 cross-link (not a data change) |
| `README.md` | New **Tier 3 evidence (2026 real-ckpt)** section (additive) referencing Kanzi + LineageFlow plumbing, the Tier 3 figure, the honest reading, and the Wave 43 audit trail |
| `docs/audit/wave43-paper-tier3-writeup.md` | This file (new) |

**NOT touched (per disjoint-file-scope contract):**

- `adaptive_reflow/` — no framework code change
- `tests/` — no test change
- `tools/run_real_ckpt_eval.py` — no eval-pipeline change (Wave 43 WF1
  Agent A + Agent B own this in parallel)
- `adaptive_reflow/algorithm/`, `adaptive_reflow/scheduler/`,
  `adaptive_reflow/eval/`, `adaptive_reflow/adapters/*` — no scheduler,
  adapter, or metric-layer change
- `tools/run_real_ckpt_eval.py` — out of scope; the metric-layer
  `_compute_metric()` real-metric branch is Wave 43 WF1 Agent A's
  deliverable

## 2. Background and motivation

Per `todo/wave43-problems-review.md` Problem 4:

> docs/CONSOLIDATED_RESULTS.md §15.8 (Kanzi) + §15.9 (LineageFlow)
> have raw per-cell tables but the **paper writeup**
> (docs/paper-draft.md or wherever) hasn't been updated with Tier 3
> results. Wave 42 WF3 paper-writeup agents should be doing this
> in-flight, but verify.

The Wave 42 Agent B paper-writeup commit `ccf32e9` did add the §7
Tier 3 section + the figure, but the section lacked:

1. An explicit one-sentence claim statement (the §7.4 reading
   paragraph is descriptive, not a claim).
2. An honest verdict block distinguishing what's closed (adapter +
   sidecar plumbing) from what's pending (the metric-layer unblock).
3. A cross-link from the paper-side digest back to
   `docs/CONSOLIDATED_RESULTS.md` §15.8 (Kanzi fresh re-execution)
   and §15.9 (LineageFlow partial sweep), so readers can navigate
   from the paper digest to the raw per-cell evidence and the
   reproduction recipe in both directions.

This wave's writeup closes those three gaps and updates the
Tier 3 figure's honest-reading note text to point at the Wave 43
WF1 metric-layer fix as the next deliverable.

## 3. Paper §7 updates (the headline)

### 3.1 One-sentence claim statement (added)

Added at the top of §7, immediately after the existing tier-classification
blockquote:

> **One-sentence claim statement.** When a published 2026 flow-matching
> checkpoint (Kanzi ICLR 2026 protein flow-AE; LineageFlow ICML 2026
> protein flow-matching) is integrated into FlowA and run through the
> multi-round re-inference loop against the SHA-256-verified real
> weights, the **adapter + sidecar plumbing** runs cleanly end-to-end
> (`adapter_mode=torch` in every Kanzi cell; forward pass succeeds on
> the LineageFlow 657 M-param ckpt) and the framework's per-cell
> wall-clock is uniformly **0.4–0.6×** the baseline wall-clock, but the
> **decision-metric evidence** sits at the synthetic-fallback ceiling
> (`TIE_AT_SATURATION`) until the metric layer (ESM-2 + Pfam holdout
> for Kanzi; LineageFlow model-own classifier for LineageFlow) is
> unblocked by the Wave 43 WF1 follow-up.

This claim statement is honest about what is currently closed (plumbing
+ wall-clock) versus what is still pending (real decision-metric
evidence), without softening either side.

### 3.2 Honest verdict block (added)

Added at the end of §7.5 (immediately after the verdict table). The
block enumerates:

- **Closed (Kanzi):** `--force-mode real` plumbing, `adapter_mode=torch`
  in all 9 cells, monotone-NFE wall-clock scaling, exit code 0.
- **Closed (LineageFlow):** forward smoke on SHA-256-verified 657 M-param
  ckpt (Wave 41 Agent B), 1/9 cells executed end-to-end on real ckpt
  (Wave 42 Agent B), per-position entropy 2.266 / log(K=20) 2.996
  (mid-entropy, neither collapse nor saturation).
- **Pending (both):** metric layer returns synthetic-fallback ceiling
  (`0.95` for Kanzi, `0.999` for LineageFlow) because
  `_compute_metric()` is hard-wired to `saturation_threshold`. Wave 43
  WF1 metric-layer fix (Pfam held-out reference + per-cell real-metric
  branches) is the next-wave deliverable. When it lands,
  `docs/CONSOLIDATED_RESULTS.md §15.10` will carry the real per-cell
  numbers and this §7 will fold them in.

### 3.3 Cross-link to CONSOLIDATED_RESULTS (added)

Added at the top of §7:

> **Cross-link:** The per-cell Kanzi and LineageFlow tables, the
> reproduction recipe, and the Wave 42 / Wave 43 audit trail live in
> `docs/CONSOLIDATED_RESULTS.md` §15.8 (Kanzi fresh re-execution),
> §15.9 (LineageFlow partial sweep), and §15.10 (Wave 43 WF1
> metric-layer fix, when that lands). This §7 is the **paper-side
> digest**; §15.8–§15.10 are the **raw evidence**.

This makes the paper-side digest and the raw evidence navigable in
both directions (paper → raw evidence for verification; raw evidence →
paper for context).

### 3.4 §7.6 Wave 43 Agent B paper-tier3-writeup (this wave, new)

New §7.6 subsection documenting what Wave 43 Agent B added:

1. One-sentence claim statement
2. Honest verdict block
3. Cross-link to CONSOLIDATED_RESULTS §15.8–§15.10
4. Regenerated figure with updated honest-reading note text

Plus pointer to this audit doc for the full Wave 43 audit trail.

## 4. Figure regeneration (note text only)

The Tier 3 figure (`docs/figures/tier3_real_ckpt_signed_mean.png`) was
regenerated from `tools/_make_wave42_figure.py` with only the **note
text** updated. The data sources and bar heights are unchanged:

- `verification_outputs/capability_audit_q4_2026.json` — G.1 evidence
  rows for Tier 1 (twodim_fm, mnist_fm) and Tier 2 (rectified_flow_cifar)
- `verification_outputs/kanzi_real_ckpt_eval_q4_2026_kanzi.json` —
  Tier 3 Kanzi 9 cells (all `TIE_AT_SATURATION` per §15.8)
- `verification_outputs/lineageflow_real_ckpt_forward_q4_2026.json` —
  Tier 3 LineageFlow forward-smoke probe (status=success, no NaN/Inf)

The updated note text now reads:

> Tier 3 honest reading: Kanzi real-ckpt eval (9 cells, adapter_mode=torch) hits the
> synthetic-mode saturation ceiling for protein_sequence_validity_rate (0.95).
> LineageFlow forward smoke passes (657.6M params, no NaN/Inf), but the real-ckpt
> eval-vs-baseline cell has not yet been wrapped; signed_mean = 0.0 by construction.
> Wave 43 WF1 metric-layer fix (Pfam held-out + per-cell real-metric branches) is the
> unblock; see docs/audit/wave43-paper-tier3-writeup.md + CONSOLIDATED_RESULTS §15.10.

This is **identical-by-construction** to the Wave 42 figure because
the underlying evidence rows have not changed (Kanzi: 9 cells at
`TIE_AT_SATURATION`; LineageFlow: 1/9 cells executed + synthetic-shim
tie on the rest). The note text update is what tells readers where
the unblock is going to come from.

## 5. README Tier 3 evidence section (new, additive)

Appended a new **Tier 3 evidence (2026 real-ckpt)** section at the
end of `README.md` (after "Why this framework matters" + the docs map
paragraph). The section:

- Lists Kanzi (ICLR 2026) + LineageFlow (ICML 2026) plumbing details
- Shows the Tier 3 figure inline
- Provides the honest reading (Tier 3 bars at zero because of the
  metric-layer trivial fallback; plumbing is verified)
- Points at `docs/CONSOLIDATED_RESULTS.md` §15.8 / §15.9 for the
  per-cell tables and §15.10 (when it lands) for the real numbers
- Cross-links to `docs/paper-draft.md` §7 and this audit doc

This is a non-breaking additive change to the README — no existing
section is touched or removed.

## 6. What was NOT done (deferred)

The following items are NOT in scope for this writeup wave:

- **Wave 43 WF1 metric-layer fix** — owned by Wave 43 Agent A
  (`tools/run_real_ckpt_eval.py:_compute_metric()` real-metric branch).
  When this lands, §15.10 will carry the real per-cell numbers and
  this §7's honest verdict block moves from "metric layer pending"
  to "metric layer PASS".
- **Wave 43 WF1 Pfam held-out reference** — owned by Wave 43 Agent B
  (separate disjoint-file-scope agent). Adds
  `data/pfam_holdout/random_clan.fasta` for the
  `protein_sequence_validity_rate` round-trip check.
- **Pytest pollution cleanup** — owned by Wave 43 WF2 Agent A
  (separate disjoint-file-scope agent, fixes `rectified_flow_cifar`
  OrderedDict import + `_make_ref` shim loss).
- **MUST-3 PARTIAL → PASS** — owned by Wave 42 WF2 background work
  (separate disjoint-file-scope agent).

This writeup's disjoint file scope is purely **paper-side artefacts**
(paper, figure, README, audit doc + the note-text-only update on the
figure script). No framework code, no eval-pipeline code, no tests.

## 7. Acceptance gate (against `todo/wave43-problems-review.md` §4)

| Gate | Status | Evidence |
|---|---|---|
| Paper has explicit Tier 3 section with Kanzi + LineageFlow per-cell tables | **PASS** | `docs/paper-draft.md` §7.2 (Kanzi 9 cells) + §7.3 (LineageFlow 1/9 cells + synthetic shim) |
| One-sentence claim statement at top of §7 | **PASS** | §7 preamble (added by this wave) |
| Honest verdict block (closed vs pending) | **PASS** | §7.5 verdict block (added by this wave) |
| Cross-link from paper to `docs/CONSOLIDATED_RESULTS.md` §15.8–§15.10 | **PASS** | §7 preamble cross-link (added by this wave) |
| `docs/figures/tier3_real_ckpt_signed_mean.png` exists | **PASS** | regenerated with updated note text |
| Figure is referenced from the paper | **PASS** | §7.4 references the figure (Wave 42 commit `ccf32e9`) and from §7.6 (this wave) |
| README short Tier 3 evidence section | **PASS** | appended at end of README (this wave) |
| `docs/audit/wave43-paper-tier3-writeup.md` exists | **PASS** | this file (new) |

All 8 gates PASS.

## 8. Reproducibility

```bash
# Re-render the figure (note text only update)
cd /home/hugo/codes/flowa-multistep-reinference
/usr/bin/python3 tools/_make_wave42_figure.py
# -> writes docs/figures/tier3_real_ckpt_signed_mean.png

# Inspect the paper-side Tier 3 section
sed -n '/^## §7\./,/^## References/p' docs/paper-draft.md

# Inspect the README Tier 3 evidence section
sed -n '/^## Tier 3 evidence/,/^## /p' README.md | head -40
```

No experiments were re-run for this writeup. All numeric claims in
the paper-side §7 and README Tier 3 evidence section are reproducible
from the JSON files cited:

- `verification_outputs/capability_audit_q4_2026.json` (G.1 evidence)
- `verification_outputs/kanzi_real_ckpt_eval_q4_2026_kanzi.json` (Kanzi 9 cells)
- `verification_outputs/lineageflow_real_ckpt_forward_q4_2026.json` (LineageFlow forward smoke)
- `verification_outputs/lineageflow_real_force_mode_q4_2026.json` (LineageFlow 1/9 cell)

## 9. Honest enumeration

What's closed at Wave 43 Agent B close:

- Paper §7 has the one-sentence claim statement, honest verdict
  block, and §15.8–§15.10 cross-link
- Figure regenerated with updated honest-reading note text
- README has a short Tier 3 evidence section (additive)
- This audit doc captures the wave's audit trail

What's still pending (carried into Wave 43 WF1 metric-layer fix and
the next paper-writeup cycle):

- Real per-cell Tier 3 metric numbers (Wave 43 WF1 Agent A +
  Pfam Agent B)
- §15.10 in `docs/CONSOLIDATED_RESULTS.md` with the real numbers
- Update §7 of the paper with the real numbers (when they land)
- Regenerate the figure to show the Tier 3 bars moved off zero

The framework's value proposition at Tier 3 remains **adapter +
sidecar plumbing verified; metric layer pending** — the next-wave
metric-layer unblock is the deliverable that closes the headline
Tier 3 claim.
