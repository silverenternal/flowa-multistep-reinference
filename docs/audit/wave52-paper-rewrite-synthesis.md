# Wave 52 Agent D — paper §Discussion + README + §17 synthesis (final)

**Wave:** 52
**Agent:** D
**Date:** 2026-09-07
**Role:** Paper-final + repo-final synthesis (paper §Discussion,
README headline numbers, CONSOLIDATED_RESULTS §17 summary).
**Disjoint-file-scope:** own `docs/`, `README.md`, and this audit
doc. NO code change to `adaptive_reflow/`, `tests/`, scheduler,
framework, eval pipeline, `tools/run_real_ckpt_eval.py`, any adapter,
any verification output.

---

## 1. What this agent added

| File | Status | Section |
|---|---|---|
| `docs/paper-draft.md` | MODIFIED (additive) | §5.6 Framework value statement, §5.7 Limitations, §5.8 Future work |
| `README.md` | MODIFIED | "Why this framework matters" rewrite (table form + capability gate health + theorem-as-code) |
| `docs/CONSOLIDATED_RESULTS.md` | APPENDED | §17 Wave 52 Agent D — final synthesis |
| `docs/audit/wave52-paper-rewrite-synthesis.md` | NEW | this document |
| `site/` | REBUILT | `mkdocs build --strict` passes (66.71 s) |

**No code change** to `adaptive_reflow/`, `tests/`, scheduler,
framework, eval pipeline, `tools/run_real_ckpt_eval.py`, any
adapter, or any verification output.

## 2. Why this agent exists

Wave 47 + Wave 49 + Wave 50 + Wave 52 added three SOTA 2026
flow-matching adapters (Kanzi ICLR 2026 protein flow-AE,
LineageFlow ICML 2026 protein flow-matching, FlowMol3 NeurIPS 2024
molecular 3D flow-matching) with a Tier 3 composite-metric glue
that lands at `composite = +0.211, verdict = "framework_improves"`
on LineageFlow. The §7 paper-side digest (§7.1 setup, §7.2
composite formula, §7.3 Kanzi, §7.4 LineageFlow, §7.5 FlowMol3,
§7.6 honest verdict, §7.7 figure, §7.8 Wave 52 audit trail) and the
audit trail (`docs/audit/wave52-paper-tier3-rewrite.md` + §16 in
`CONSOLIDATED_RESULTS.md`) document the *what*. This agent
documents the *so what* — the framework value statement, the
limitations, and the future work — at the paper-discussion level
and at the reader-first-encounter level (README).

## 3. §5.6 — Framework value statement

Five enumerated claims, each with a verified number attached:

1. **Typed contracts are not optional.** 14 integrated adapters,
   17 typed state machines, 333 typed transitions exist because
   the 8-method `FlowMatchingODEAdapter` Protocol is tight.
2. **Theorem-as-code is auditable.** Theorem 1's numerical
   witness `selection_ratio` moves from a 0.8061 plateau to
   0.9881 / 0.9896 once C4 is closed (§4.6 paper-draft.md); the
   rate bound is enforced by `assert_convergence_rate` on
   $(A_g, B_g, C_g, e_\rho)$.
3. **The framework improves the flow component when the adapter
   exposes a per-position entropy signal.** Tier 3 honest
   reading (§7.6): pure flow-matching on a per-position latent
   (LineageFlow) yields composite `+0.211, framework_improves`,
   driven by `LineageFlowClassifierAwareRestart` flipping ~84% of
   33 token-position argmaxes round-over-round.
4. **Lower-is-better metrics dominate the value surface.** 2D
   Rectified Flow $W_2$ −7.28% / −10.40% (3 seeds × 1 000 samples,
   §5 of CONSOLIDATED_RESULTS.md); CIFAR-10 Rectified Flow FID
   −44.17% at v2 NFE-averaged protocol (§6); MNIST FM FID −15.01%
   on the CristianLazoQuispe `flow_model_localized_noise.pth`
   checkpoint (capability-audit q4 row); 2D FM ablation
   `single_pass → multi_round_no_restart` yields $W_2$ 2.85 →
   0.62 (4.6×) on two_moons, 2.31 → 0.76 (3.0×) on
   eight_gaussians at matched weights.
5. **Capability gates are hard and audited cold-clone.** From
   `verification_outputs/capability_audit_q4_2026.json`: G.1
   `+0.0884 PASS`, G.2 `0.962 PASS`, G.3 `−0.0251 PASS`, G.4 `3
   PASS`, G.5 `27.5 PASS`, G.6 `0.25`, G.7 `7/7 PASS`,
   `g_master_capability = PASS`, `must_4_freeze_gate = PASS`.

## 4. §5.7 — Limitations

Ten enumerated limitations, each tied to a specific evidence cell:

1. Endpoint-saturation masking (Kanzi / LineageFlow on the
   decision-metric axis; composite axis is the workaround).
2. No end-to-end CTMC or BFN integration (FlowMol3's
   `frac_mols_stable_valence` regression is the documented
   root cause).
3. No $n \geq 30\,000$ SOTA-paper-metric FID (v4 CIFAR sweep
   INFEASIBLE on this rig; v5 protocol wired but GPU sweep
   pending).
4. Single-seed CIFAR-10 v4 (no variance estimate on the FID rows).
5. Matched-NFE regression on the image domain (v4 FID
   103.41–108.55 vs 50-NFE baseline 83.09, **24–31% worse**).
6. Infeasible external baselines at matched NFE (§8 Table 14
   every cell `NOT YET MEASURED`).
7. Framework wall-clock > 1× baseline at higher NFE (1.0–1.6×
   on Kanzi warm-cache CPU; framework is doing more work, not
   regressing).
8. `e_rho` regime enforcement is diagnostic-only (Lemma 4's
   $\varepsilon^2 < e_\rho / \log(2)$ is *reported* but not
   *blocked*).
9. `FreeTrajScheduler` progress-cache bug is a known open defect.
10. No published test-time training step (framework is
    inference-only — no fine-tuning of $\theta$, no LoRA, no
    test-time adaptation).

## 5. §5.8 — Future work

Ten enumerated future-work items, ordered by expected effect on
the framework's value surface (each sized to a single wave):

1. Wire FlowMol3's `frac_valid_mols` metric layer (Tier 3 closure)
2. CTMC transition-kernel swap for FlowMol3 (closes limitation
   item 2)
3. Heun v5 sweep end-to-end on CIFAR-10 (workflow A phase 4)
4. CIFAR-10 sample count to 10 K on GPU (workflow A phase 5)
5. Promote `ConvergenceDiagnostic.regime_violations` from
   diagnostic to blocking (1-LOC guard)
6. Fix the `FreeTrajScheduler` progress-cache bug
7. Extend to MNIST FID-50K, ImageNet FID-50K, FlowMol3
   (post-CTMC), ProtBFN (post-trained-baseline), GraphBFN
   (post-replacement)
8. Kanzi composite per-cell sweep (Wave 52 Agent A in flight)
9. Add a `observe_metric_layer` Protocol contract
10. External-baseline sweep on the three SOTA 2026 ckpts at
    matched NFE (closes the §8 `NOT YET MEASURED` cells)

## 6. README — "Why this framework matters" rewrite

Replaces the prose paragraph with three explicit tables:

**Per-family value surface.** Five rows (toy 2D FM, SOTA 2D RF,
CIFAR-10 RF, MNIST FM, Tier 3 LineageFlow) with the headline
number per row, the matching protocol, and the source-cell in
`docs/CONSOLIDATED_RESULTS.md`.

**Capability gate health.** Eight rows (G.1–G.7 + the
`g_master_capability` aggregate) with the value, the target,
the verdict, and the source JSON
(`verification_outputs/capability_audit_q4_2026.json`).

**Theorem-as-code callout.** Three independent ground-truth
oracles (G1 2D Gaussian mixture, G2 5K synthetic geometric-shape
images, G3 DERIV-001 closed-form hparams) PASS with 97 oracle
tests and 0 bugs filed. Once C4 is closed, Theorem 1's numerical
witness `selection_ratio` moves from 0.8061 to 0.9881 / 0.9896.

The honest-gaps sentence at the end remains: top-model Tier 3
decision-metric evidence is partial on hybrid adapters (Kanzi
composite in flight) and blocked on FlowMol3's missing metric
layer; FreqFlow + MM-FM remain blocked on upstream ckpt release;
matched-NFE CIFAR-10 v4 reads 24–31% worse than the 50-NFE
baseline, reported without softening.

## 7. CONSOLIDATED_RESULTS §17 — final synthesis summary

§17 has 7 subsections (§17.1–§17.7) that mirror the agent's
deliverables:

* §17.1 file delta
* §17.2 paper §5.6 summary
* §17.3 paper §5.7 summary
* §17.4 paper §5.8 summary
* §17.5 README rewrite summary
* §17.6 honest gaps still open at end-of-Wave-52
* §17.7 reproducibility recipes

The §17.6 honest-gaps subsection names the three open items that
carry into Wave 53+: Kanzi composite per-cell sweep in flight,
LineageFlow 9-cell composite re-sweep in flight, external-baseline
§8 cells `NOT YET MEASURED` pending the result artefact.

## 8. Verification

```bash
.venv/bin/mkdocs build --strict
# INFO    -  Cleaning site directory
# INFO    -  Building documentation to directory: .../site
# INFO    -  ... Formatting signatures requires either Black or Ruff ...
# INFO    -  Documentation built in 66.71 seconds
# (exit 0; no WARN or ERROR)
```

The pre-existing `docs/CONSOLIDATED_RESULTS.md` (2176 lines
pre-Wave-52-D) is now 2305 lines. The pre-existing `paper-draft.md`
(1854 lines pre-Wave-52-D) is now 2072 lines. The pre-existing
`README.md` (482 lines pre-Wave-52-D) is now 524 lines.

## 9. Disjoint-file-scope contract (verified)

**Modified:**
* `docs/paper-draft.md` (§5.6 + §5.7 + §5.8 — additive)
* `README.md` ("Why this framework matters" — additive rewrite)
* `docs/CONSOLIDATED_RESULTS.md` (§17 appended)

**Created:**
* `docs/audit/wave52-paper-rewrite-synthesis.md` (this file)

**Rebuilt:**
* `site/` (mkdocs build --strict, 66.71 s, exit 0)

**NOT touched:**
* `adaptive_reflow/`
* `tests/`
* scheduler, framework, eval pipeline
* `tools/run_real_ckpt_eval.py`
* any adapter
* any verification output

## 10. What this wave closes

* **§5 Discussion of paper-draft.md** now has the three
  subsections a paper-reviewer asks for: value statement
  (§5.6), limitations (§5.7), future work (§5.8). The §5.1–§5.5
  subsections from earlier waves (what is/isn't proven, when helps,
  threats, caveats) remain untouched.
* **README "Why this framework matters"** now exposes the
  full value surface in table form, not prose form. A reader
  can answer "does this framework help?" in one screen-scroll.
* **CONSOLIDATED_RESULTS §17** is the single source of truth
  for the Wave 52 final synthesis; cross-references
  `paper-draft.md §5.6–§5.8`, the README, the §15 audit trail,
  and `verification_outputs/capability_audit_q4_2026.json`.
* **mkdocs build --strict** passes; the docs site is rebuilt
  end-to-end with no warnings or errors.

## 11. What this wave does NOT close (carries into Wave 53+)

* Kanzi composite per-cell sweep (Wave 52 Agent A in flight).
* LineageFlow 9-cell composite re-sweep (Wave 52 Agent C in
  flight).
* External-baseline §8 cell values (every cell `NOT YET
  MEASURED`; gated on the framework-vs-external signed-delta
  artefact under `verification_outputs/baseline_comparison_*.json`).
* `frac_valid_mols` metric layer for FlowMol3 (5.8 item 1;
  metric-spec work, not framework work).
* CTMC transition-kernel swap for FlowMol3 (5.8 item 2; plug-in
  point declared but not wired).
* Promote `ConvergenceDiagnostic.regime_violations` from
  diagnostic to blocking (5.8 item 5; 1-LOC guard in
  `CodimensionSheetScheduler.record_round_feedback`).
* The push itself (per Wave 41–Wave 51 push-prep directive, all
  Wave 52 agents commit but DO NOT push).
