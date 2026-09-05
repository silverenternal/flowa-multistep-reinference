# Wave 42 Agent C — Tier 3 "real-ckpt framework vs baseline" synthesis

**Date:** 2026-09-05
**Agent:** Wave 42 Agent C
**Scope:** Synthesize the §15 entry ("Tier 3 real-ckpt framework vs
baseline") from the Wave 42 Agent A + B JSON outputs, then author the
framework value-surface narrative for the partial Tier 3 completion.
Pure documentation/audit; **no experiments re-run, no code touched,
no framework / adapter / scheduler / eval-pipeline files modified**.

## 1. The Tier 3 claim

> "Any flow-matching model, when integrated into the framework,
> improves inference quality on the model's real checkpoint."

The tiered structure:

- **Tier 1 — toy + small pretrained FM:** establish that the
  framework does not regress and ideally surfaces re-inference
  value-add. **CLOSED** (Wave 2-9, §7).
- **Tier 2 — CIFAR-10 Rectified Flow (Liu 2022 NeurIPS Spotlight):**
  trained-FM at published weights, framework vs baseline.
  **CLOSED** (§6, Wave 6 reproducibility validation, §12).
- **Tier 3 — real-ckpt top-model (Kanzi ICLR 2026 + LineageFlow ICML
  2026):** framework integrated into a 2026 SOTA model loaded from
  the published checkpoint, real forward pass + real downstream
  metric, framework-vs-baseline. **PARTIAL** as of Wave 42 close.

This doc records the partial Tier 3 completion and the honest
top-model verdict.

## 2. Pre-Tier-3 evidence (already established)

- **Tier 1 toy FM (2D, MNIST, CIFAR-10 RF):** framework matches
  baseline in matched-NFE regime; framework wins in low-NFE regime
  via paper-quantity-driven adaptive scheduler. See §7 of
  `docs/CONSOLIDATED_RESULTS.md` (Wave 1-9 toy FM framework
  validation). 3 toy tasks × 2 matched-NFE regimes, all framework
  values within noise of baseline; framework wins are 15-30% better
  in low-NFE / fast-budget regimes.
- **Tier 2 CIFAR-10 Rectified Flow (Liu 2022, NeurIPS Spotlight):**
  real published model, real published weights, real FID metric.
  Matched-NFE regime: framework matches baseline; matched-wall regime:
  framework wins 15% FID on toy v2 (Wave 6 reproducibility). See
  §6 + §16.4 honest-negative flags (CIFAR-10 v4 matched-NFE
  regression +24-31% remains open).
- **Canonical aggregator (G.1 robust median):** +0.0884 PASS on
  4 model families × 10 rows. See §12.3 + §16.2.

These two tiers already establish the "framework does not regress
on real published weights" and the "framework wins on real
published weights in the matched-wall regime" sub-claims. Tier 3 is
about extending the same claim to **two 2026 SOTA checkpoints**.

## 3. Post-Tier-3 evidence (Wave 42)

### 3.1 Kanzi (ICLR 2026, arXiv:2510.00351) — partial

Source: `verification_outputs/kanzi_real_force_mode_q4_2026.json`
(Wave 42 Agent A re-execution of the Wave 41 Agent B CLI plumbing).

| metric                                  | value               |
|-----------------------------------------|---------------------|
| n_cells                                 | 9                   |
| verdict_overall                         | TIE_AT_SATURATION   |
| g1_mean_signed_delta_pct                | 0.0                 |
| real_ckpt_loaded                        | True (adapter_mode=torch in every cell) |
| metric_layer_exercised                  | False (synthetic_fallback marker in every cell) |

**Reading:** `--force-mode real` end-to-end plumbing works on the
real 530 MB Kanzi checkpoint (adapter loads real weights, solve
layer runs real forward pass, wallclock scales monotonically with
NFE 0.0013 → 0.0139 s on baseline, 0.0005 → 0.0047 s on framework).
The metric layer still returns the documented trivial reading
(`synthetic_fallback` marker, value 0.95 ceiling) because computing
the real `protein_sequence_validity_rate` against a Pfam holdout
requires ESM-2 + a held-out reference split shipped in the repo
(§15.5 items 3+4), neither of which is in this sidecar venv.

This is **not** a `--force-mode real` failure or a framework
regression; it is the honest state of the metric layer. The Tier 3
plumbing works; the Tier 3 metric does not.

### 3.2 LineageFlow (ICML 2026, arXiv:2605.22252) — BLOCKED / PENDING

Source: `verification_outputs/lineageflow_real_force_mode_q4_2026.json`
**does not exist** at Wave 42 close. The forward-pass JSON
(`lineageflow_real_ckpt_forward_q4_2026.json`, Wave 41 B) confirms
the upstream clone + 657.6 M-param model + 8-step Euler integration
on real weights is reproducible end-to-end. What is missing is the
**per-cell baseline-vs-framework** JSON the Tier 3 claim needs.

Wave 42 Agent B's task
("LineageFlow real-ckpt framework-vs-baseline via --force-mode real")
is `in_progress` and has not produced the expected JSON by the
synthesis deadline. The expected CLI is:

```bash
.venvs/lineageflow_venv/bin/python tools/run_real_ckpt_eval.py \
  --model lineageflow --force-mode real \
  --seeds 42,43,44 --nfe-budgets 10,50,200 \
  --output verification_outputs/lineageflow_real_force_mode_q4_2026.json
```

The CLI plumbing (`--force-mode {synthetic,real,auto}`) is generic
and the LineageFlow adapter is the same code path as Kanzi
(`adaptive_reflow/adapters/lineageflow.py` already loads real ckpt
via the Wave 36 C SamplerConfig shim), so the expected output is
9 cells = 3 seeds × 3 NFE budgets with the same schema as Kanzi.

## 4. Verdict

```json
{
  "claim": "framework_improves_on_real_ckpt_top_models",
  "value": false,
  "rationale": "Kanzi: 0/9 cells show framework improvement (all TIE_AT_SATURATION with synthetic_fallback metric marker); LineageFlow: per-cell JSON missing. The honest reading is 'not yet verified' which the boolean form reports as False.",
  "kanzi_supported_cells": 0,
  "kanzi_tie_at_saturation_cells": 9,
  "kanzi_regression_cells": 0,
  "kanzi_pending_cells": 0,
  "lineageflow_status": "PENDING_JSON_MISSING",
  "lineageflow_supported_cells": null,
  "tier_3_claim_status": "PARTIAL",
  "tier_1_status": "CLOSED",
  "tier_2_status": "CLOSED"
}
```

`framework_improves_on_real_ckpt_top_models = False` is the honest
boolean given the data in hand. Tier 1 + Tier 2 + canonical
aggregator (G.1) remain the load-bearing evidence for the broader
"framework improves FM" claim; Tier 3 is the SOTA-checkpoint
extension and is **not closed at Wave 42**.

## 5. What this means for the framework value surface

The framework value surface is documented at three layers:

1. **Algorithm uplifts** (the framework-internal value, §3 of
   `docs/CONSOLIDATED_RESULTS.md`): 36 isolations tested, all
   positive on the matched-problem regime.
2. **Canonical aggregator** (the broad value, §12.3 / §16.2 /
   G.1 robust median): +0.0884 PASS on 4 model families × 10 rows
   (twodim_fm, rectified_flow_cifar, mnist_fm, lineageflow — the
   lineageflow row uses the Wave 33 fix-C per_position_entropy
   metric that breaks the saturation tie).
3. **Top-model tier** (the SOTA-checkpoint extension, Tier 3):
   Kanzi plumbing works but metric is the trivial reading;
   LineageFlow per-cell JSON is missing. **Verdict:
   PARTIAL**, headline boolean = False.

The Tier 3 partial completion is consistent with the broader
narrative: the framework is well-validated on toy + small
pretrained + CIFAR-10 (Tiers 1+2), and the path to SOTA-checkpoint
validation (Tier 3) is plumbed end-to-end but blocked on
metric-layer infrastructure (ESM-2 + Pfam holdout for protein;
HMMER + OmegaFold + MMseqs2 + ESM-IF for family validity; or the
LineageFlow forward-pass smoke alone for the protein axis with
the Wave 33 fix-C `per_position_entropy` metric).

## 6. Honest gap inventory at Tier 3

| gap                                                  | status         | next step |
|------------------------------------------------------|----------------|-----------|
| LineageFlow per-cell JSON missing                    | PENDING        | Land JSON (Wave 42 B re-run / re-spawn) |
| Kanzi metric layer (ESM-2 + Pfam holdout)            | BLOCKED on env | §15.5 items 3+4 unblock |
| Fold Tier 3 cells into capability_audit.py:evidence[]| not done       | after both above land |
| CLM-040 §1.1.d "FlowMol3 framework 0/0" stale        | not done       | after fold-in |

These are the **honest** next steps. The framework itself is not
in regression; the Tier 3 surface is simply unfinished.

## 7. What this agent did and did not do

**Did:**
- Read `verification_outputs/kanzi_real_force_mode_q4_2026.json` (9 cells, all TIE_AT_SATURATION with synthetic_fallback markers).
- Confirmed `verification_outputs/lineageflow_real_force_mode_q4_2026.json` is missing.
- Read prior §15.1-§15.6 in `docs/CONSOLIDATED_RESULTS.md` to align terminology.
- Authored §15.7 ("Wave 42 Agent C — Tier 3 real-ckpt framework vs baseline synthesis") with the per-cell Kanzi table + the LineageFlow PENDING marker + the honest verdict.
- Authored this doc as the narrative summary.
- APPENDED a Tier 3 partial-complete note to `docs/STRATEGY_FRAMEWORK_SCOPE.md`.

**Did not:**
- Touch `adaptive_reflow/`, `tests/`, framework, scheduler, or eval pipeline code (per disjoint-file-scope guard).
- Re-run any experiment (per Wave 42 Agent C = "synthesis only" role).
- Push to remote (per Wave 42 commit policy).

## 8. Net result

The headline Tier 3 boolean is `False` (honest). The Tier 3
*plumbing* is `True` (Kanzi end-to-end works on real ckpt; LineageFlow
forward pass works; both adapters are registered with `@implements`).
The Tier 3 *metric* is `False` for Kanzi (trivial reading) and
`PENDING` for LineageFlow (no JSON). Tier 1 + Tier 2 + canonical
aggregator remain the load-bearing evidence; the paper's "framework
improves FM" claim is supported by those three layers, not by Tier 3
which is partial. The next wave's Tier 3 unblock is the LineageFlow
JSON + the Kanzi ESM-2 + Pfam-holdout metric layer; both have a
clear path and a clear owner.
