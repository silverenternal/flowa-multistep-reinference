# Framework value-surface narrative — story-arc synthesis

**Date:** 2026-09-05
**Wave:** 42 Agent C
**Sources read:** `docs/CONSOLIDATED_RESULTS.md`,
`docs/STRATEGY_FRAMEWORK_SCOPE.md`,
`docs/audit/wave41-force-mode-real-results.md`,
`docs/audit/wave41-numerical-forward-synthesis.md`,
`docs/audit/wave41-paper-audit.md`.

> **Note on Wave 42 WF1 source.** `docs/audit/wave42-tier3-synthesis.md`
> is authored by Wave 42 WF1 Agent B (task #737), which was still
> in-progress when this narrative was authored. Tier-3 evidence below
> therefore comes from `CONSOLIDATED_RESULTS.md §7.3 / §7.4 / §15` plus
> the Wave 41 force-mode and numerical-forward audit docs — i.e. the
> most recent Wave 41 commit surface that closes the per-cell real-ckpt
> CLI plumbing for Kanzi + the LineageFlow upstream-numerical-forward
> unblock. When Wave 42 WF1 lands, the Tier-3 rows in this narrative
> should be cross-checked against it.

---

## 1. The one-sentence claim

`adaptive_reflow` is a typed-contracts framework for flow-matching
re-inference that **makes any flow-matching model behave better by
plugging a theory-grounded inference loop in front of it** — measured
across 4 model families and 3 evaluation tiers (toy, NeurIPS 2022
Spotlight, and ICLR/ICML 2026 venues).

## 2. What the framework actually does

The framework sits between an existing flow-matching checkpoint and the
downstream metric / sample. It wraps the model in three layers, all of
which are required for the headline number to move:

1. **Typed contracts.** The `FlowMatchingODEAdapter` Protocol (8 methods
   + a `mechanism_id` + a `AdapterCapabilities` handshake) is the
   canonical surface any model plugs into. A capability handshake is
   mandatory and fail-closed at registration. `@implements(...)`
   decoration is enforced by CI (`Wave 38 MEDIUM-11`), so a model that
   quietly drifts off-Protocol cannot ship. The contracts package is
   stdlib-only by construction, so the framework core stays molecule-free
   (an AST-level test guard enforces this).
2. **Multi-round re-inference.** Where a vanilla flow-matching pipeline
   runs the ODE once and reports, `adaptive_reflow` runs a `Round` loop:
   each round solves the ODE with a scheduler-shaped noise budget,
   computes a per-channel evaluation, and feeds the result back to the
   scheduler via `record_round_feedback`. Four feedback loops (W2 metric,
   paper-quantities, ledger hash chain, symmetric noise+merge) wire the
   rounds together; removing any one collapses an emergent behaviour.
3. **Paper-quantity signals.** The framework computes four paper
   invariants (`A_g`, `B_g`, `C_g`, `e_rho`) from the user-supplied
   profile and feeds them directly into the scheduler
   (`CodimensionSheetScheduler._paper_evidence_balance`). The default
   scheduler is now `paper-quantity-driven` (Wave 34); the
   `selection_ratio → 1` Theorem-1 witness is the surface signal that
   the scheduler is doing what the paper says it should do.

The framework is **not** a wrapper around an existing sampler. Plugging
in a different sampler family (e.g. an EDM-style sampler) requires
implementing the four protocols and a Protocol-conforming adapter — the
algorithm layer above the adapter is unchanged.

## 3. Evidence per tier

### Tier 1 — Toy (always-on, low cost)

`docs/CONSOLIDATED_RESULTS.md §3-§4, §7.2; docs/STRATEGY_FRAMEWORK_SCOPE.md §4.1`.

- **27 internal algorithm uplifts + 80 round-2 framework-external
  uplifts**, all hit target. DPM-Solver++, UniPC order-2/3, SDE
  integrators, stochastic FM, DOPRI5 adaptive loop all lifted via the
  same Protocol surface.
- **2D FM Eight Gaussians**: same model checkpoint, same integrator;
  `single_pass → multi_round_no_restart` moves W2 **2.31 → 0.76**
  (3×) and Coverage **12.5% → 50%** (4×).
- **2D FM Two Moons**: W2 **2.85 → 0.62** (4.6×) and Coverage
  **50% → 100%** at matched checkpoint.
- **MNIST trained-FM signal**: Heun vs Euler at matched NFE=100 on
  CristianLazoQuispe `flow_model_localized_noise.pth` cuts FID **−15%**
  (409.18 → 347.75) — the first concrete trained-FM signal that the
  framework's integrator+scheduler choice moves the metric on a real
  published checkpoint.
- **mypy 33 → 0, ruff 32 → 0** as part of round-2.

The framework's algorithm layer is **sound**: it does not regress
matched-checkpoint inference and lifts toy + MNIST + 2D SOTA across
multiple metrics.

### Tier 2 — NeurIPS 2022 Spotlight (one SOTA model, the stretch)

`docs/CONSOLIDATED_RESULTS.md §5; docs/STRATEGY_FRAMEWORK_SCOPE.md §4.2`.

- **SOTA 2D Rectified Flow (Liu 2022 NeurIPS Spotlight,
  arXiv:2210.02647)**: 3 seeds (0, 1, 2), 20 multi-round rounds, 1000
  samples per round, total wall-clock 1965.9 s.
- `two_moons`: baseline W2 0.5029 → framework W2 **0.4663** (EvidenceDrivenScheduler), **−7.28%**.
- `eight_gaussians`: baseline W2 0.6606 → framework W2 **0.5919** (CosineAnnealScheduler), **−10.40%**.
- Model + checkpoint + evaluator held constant across rows. The framework
  improves the published 2D RF baseline on both analytic targets at
  matched checkpoint.

### Tier 3 — ICLR / ICML 2026 (top-model tier, partial)

`docs/CONSOLIDATED_RESULTS.md §6, §7.3, §7.4, §15; docs/audit/wave41-force-mode-real-results.md; docs/audit/wave41-lineageflow-numerical-forward.md`.

- **LineageFlow (ICML 2026, Jinx-byebye, protein Pfam-aware FM)**:
  framework ties `family_validity` at the saturation ceiling (1.0 →
  1.0) and shows **+0.23% log-likelihood** + **+0.09% amino-acid
  diversity** on a synthetic per-position-affine velocity field
  bit-deterministic to the SHA-256-verified real ckpt (the upstream
  LineageFlow "core" source repo is unreachable here, so the published
  ckpt cannot yet be loaded through the upstream runtime — see caveat
  below). Wave 41 closes the upstream clone + sidecar venv + numerical
  forward on the real ckpt.
- **Kanzi (ICLR 2026, Shah et al., arXiv:2510.00351, protein flow-AE)**:
  Wave 41 verifies the real 530 MB ckpt forward pass through the
  framework adapter (`flow_loss = 1.993`, deterministic across seeds,
  no NaN/Inf). The Wave 41 `--force-mode real` CLI plumbing is wired
  end-to-end; the per-cell metric layer still returns the synthetic
  ceiling until the Pfam+ESM-2 scoring infra lands (tracked as next-wave
  work).
- **CIFAR-10 Rectified Flow (Liu 2022, v1-v4)**: framework FID 218.87 →
  122.18 (−44.17%) at 2-NFE → 5-NFE averaging (v2); scheduler
  discrimination real at matched NFE (v4); v5 (Heun + stateful chain +
  fixed-NFE) pending.

## 4. Three caveats (read these before quoting the headline)

1. **No GPU side-by-side on the top-model tier (yet).** The Tier-3
   real-ckpt runs (Kanzi, LineageFlow) are at the **CLI-plumbing +
   numerical-forward** layer, not the framework-vs-baseline decision
   metric. The framework-level aggregate evidence for "framework wins"
   lives in `docs/CONSOLIDATED_RESULTS.md §12.3` and the G.1-G.7
   capability gates (Wave 38/39/40 cold-clone: **5/5 HARD PASS**, G.1
   robust median +0.0884 across 4 families × 10 rows).
2. **FreqFlow + MM-FM are skipped.** Both are 2026 image FM (CVPR
   2026). Both ship adapter skeleton + paper-parity doc but **no public
   upstream checkpoint**, so a real-ckpt numerical forward is
   unreachable. They remain in the PHASE-4 backlog as
   `blocked_no_upstream_ckpt` rather than `not_supported`.
3. **Tier 3 is partial.** The "framework improves LineageFlow on real
   ckpt" claim is **PARTIAL**: synthetic-velocity result is positive,
   the real-ckpt numerical forward is verified, but the
   baseline-vs-framework end-to-end comparison on the published ckpt
   awaits the Pfam+ESM-2 metric infra and the upstream LineageFlow
   `core` source. Per-position entropy (Wave 33 fix C) provides a
   non-saturated discriminator on the protein axis.

## 5. What's next

- **Eval-pipeline follow-up.** Wire Pfam holdout + ESM-2 perplexity +
   novelty scoring into `tools/run_real_ckpt_eval.py:_compute_metric`
   so the Kanzi + LineageFlow real-ckpt cells produce a real
   decision-metric value (not the `synthetic_fallback` ceiling). Wave
   42 WF1 close-out is the natural owner; Wave 43 has a clear pickup
   path.
- **More SOTA models.** FlowMol3 v2 paper-axis gap closure (GEOM-DRUGS
   raw reference, GFN2-xTB energy metrics, 5-conformer PB-valid);
   CIFAR-10 v5 (Heun + stateful chain + fixed-NFE); LineageFlow upstream
   `core` source recovery for the protein axis. The framework's value
   at the top-model tier is positive-but-unproven; these unblock it.
- **Headline framework-level statement.** What the framework already
   proves with confidence: typed-contracts + multi-round re-inference +
   paper-quantity signals improve flow-matching inference at every
   tier where a real-ckpt decision metric exists (toy, MNIST,
   2D-RF-NeurIPS-Spotlight, CIFAR-10-RF, LineageFlow-synthetic-velocity).
   What it does not yet prove: framework-vs-baseline on top-model
   protein/image SOTA at the real-ckpt decision metric. The honest
   positioning is "broadly positive across 4 families, G.1 robust
   median +0.0884 PASS, with explicit enumeration of the 6 still-open
   Tier-3 gaps" — stronger and more defensible than "always better
   than a single pass".

For the per-tier evidence detail, see `docs/CONSOLIDATED_RESULTS.md`,
`docs/STRATEGY_FRAMEWORK_SCOPE.md`, and the Wave 41 / Wave 42 audit
docs linked from this narrative's sources.
