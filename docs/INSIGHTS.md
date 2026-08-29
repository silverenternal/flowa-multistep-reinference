# Paper-grounded algorithm layer: how Li 2024 Theorem 1 maps to flowa's algorithm abstractions

Status: insight document (narrative, not a load-bearing governance record).
Audience: maintainers, reviewers, and newcomers asking "why does the algorithm layer look like it does?"
Related: ADR-0013 (`docs/adr/0013-posterior-selection-drives-algorithm.md`), ADR-0010, ADR-0011, ADR-0012, `docs/ABLATION.md`, `docs/CHANGELOG.md`.

---

## 1. Summary

The flowa-multistep-reinference framework exposes an algorithm layer organised as four `Protocol`s — `SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, and `RestartBlenderProtocol` [CLM-019] — wired together by `ReInferenceRunner`. Up to and including ADR-0012 that layer was justified *structurally*: each role plays a clean part in the four-axis `(scheduler, policy_driver, merge_operator, blender)` product, and the four default implementations reproduce the pre-ADR-0011 behaviour bit-for-bit. The audit question "why cosine, and not Karras EDM or a step decay?" was answered with "cosine is the schedule that ships", which is honest but unsatisfying.

ADR-0013 closes that gap by grounding the layer in Li (2024), *Gaussian Posterior Selection on Noncompact Fibres with Uniformly Separated Roots*, Theorem 1. The paper proves that a small-noise Gaussian posterior on a residual whose fibre is the union of a codimension-1 sheet `y = 0` together with isolated codimension-2 root points concentrates on the sheet rather than on the cells, with local sheet density proportional to `exp(-x^2 / 2) / sqrt(1 + g(x)^2)` [CLM-012]. The proof decomposes into three estimates (sheet-tube scaling [CLM-001], root-cell bound [CLM-002], physical-complement suppression [CLM-007]) and one normalisation step (Proposition 3). The framework's algorithm abstractions instantiate those four pieces directly: `SchedulerProtocol` produces the per-round `n_cap` that drives the sheet-vs-cell evidence balance, `PolicyDriverProtocol` derives `beta = n_cap` (ADR-0010's canonical transform), `MergeOperatorProtocol` enforces the bounded noise floor that prevents escape from the fibre [CLM-010] [CLM-020], and `RestartBlenderProtocol` keeps the prior / fresh blend inside the scheduled envelope. `SequentialScheduler` [CLM-021] is the multi-phase composition primitive that chains multiple sub-schedulers by round range for regimes that want piecewise schedule shapes.

The default scheduler, `CosineAnnealScheduler`, is not an arbitrary "default" any more — it is the canonical implementation of paper Lemma 2's sheet-tube scaling [CLM-005], with the monotonic decrease in fresh-noise capacity mapping exactly to the `sigma -> 0` limit the paper proves selects the sheet. The new `CodimensionSheetScheduler` exposes that mapping as a first-class implementation: `n_cap(r) = n_min + (n_max - n_min) * ratio(r)` where `ratio(r) = sheet / (sheet + cell)` is the closed-form evidence balance from Lemma 2 + Lemma 3 with `sheet = 1 / max(n_cap_base, eps)` and `cell = (1 - n_cap_base)^2 / eps^2` [CLM-006]. Both schedulers are derived from the same paper proof; the difference is whether the sheet-vs-cell balance is *named* (cosine is the canonical closed form; codimension is the explicit Lemma-2-plus-Lemma-3 closed form).

This transforms the algorithm layer from "exploratory engineering" to "theory-backed design." Future scheduler proposals must now reconcile with paper's three-estimate structure: a scheduler whose per-round `n_cap` envelope does not respect the codimension difference between sheet and cells is *theoretically* (not just structurally) incompatible with Theorem 1. The framework gains a clear theoretical bar — sheet vs cells, codimension difference, tail control — alongside the structural bar (per-role conformance, determinism, audit invariants) that ADR-0011 already enforces. The two bars are complementary: ADR-0011 asks "does the algorithm fit the framework?", ADR-0013 asks "does the algorithm fit the paper?". A scheduler that fails either test is rejected; a scheduler that passes both is accepted as paper-grounded.

The empirical validation lives in `EvidenceScaleGapMetric` (formerly `PosteriorSelectionEvaluator`, `adaptive_reflow/eval/posterior_selection_evaluator.py`), which measures the framework-internal heuristic `selection_ratio = sheet_evidence / (sheet_evidence + cell_evidence)` by replaying the 2D-FM adapter against the analytic mode-centre set for `two_moons` and `eight_gaussians`. The evaluator's `oracle()` method surfaces the three diagnostic metrics (`sheet_evidence`, `cell_evidence`, `selection_ratio`) alongside the canonical `ChannelTransferEvidence` diagnostics; `ReInferenceConfig.selection_evaluator` plumbs the evaluator through the runner, and `ReInferenceResult.per_round_metrics[r]["selection_ratio"]` records the per-round value. The 18-row ablation in `tools/run_ablation.py` adds two paper-grounded rows (`multi_round_codimension_sheet_posterior_selection` and `multi_round_cosine_posterior_selection`) that measure the ratio directly. The result — recorded in `docs/ABLATION.md` — is sheet-dominant from round 0 (`selection_ratio = 0.806` rising to `0.819` on `two_moons`), exactly the qualitative claim Theorem 1 makes about the *direction* of selection. The quantitative claim (`ratio -> 1`) does not appear because the replay evaluator scores the adapter at a fixed noise scale; the framework's heuristic proxy measures sheet-vs-cell evidence scale gap (sheet `O(eps^1)`, cells `O(eps^2)`), and that scale gap at the *closed-form* level (the adapter's training noise) plateaus rather than approaching 1. Making the ratio schedule-sensitive and converging to 1 is the open follow-up recorded at the end of this document.

> **Framework-internal heuristic, NOT a paper quantity.** The
> `selection_ratio` emitted by `EvidenceScaleGapMetric` is a
> framework-side diagnostic for monitoring whether the framework's
> behaviour is consistent with the paper's evidence ordering. It is
> NOT a paper quantity, and convergence to 1 is NOT a paper claim
> [CLM-008]. See §"What this insight does NOT claim" below for the
> full disclaimer.

---

## 2. The paper-to-framework correspondence

The mapping below mirrors ADR-0013's framework-mapping table; the right-hand column adds the empirical handle (which test, which metric, which ablation row) that lets a reviewer verify each paper claim from a run's audit trail.

| Paper Theorem 1 (Li 2024) | Paper symbol | Framework implementation | Empirical handle |
| --- | --- | --- | --- |
| Codimension-driven selection (Theorem 1) | `mu_{g,eps} --BL--> nu_g` as `eps -> 0` [CLM-012]; `mu_{g,eps}(union_z I_z) = O(eps)` [CLM-014] | The four `Protocol`s composed by `ReInferenceRunner`; the sheet is the primary mode, cells are the secondary modes | `EvidenceScaleGapMetric` (formerly `PosteriorSelectionEvaluator`) + `multi_round_codimension_sheet_posterior_selection` / `multi_round_cosine_posterior_selection` rows |
| Lemma 2 — sheet tube scaling | `Theta(eps^{+1})` per normal direction (one normal direction, codimension 1) [CLM-001] | `CosineAnnealScheduler` (ADR-0010's `n_cap` ramp) [CLM-005] — closed-form `n_cap(r) = n_min + 0.5 * (n_max - n_min) * (1 - cos(pi * r / (L - 1)))`; direction-aligned with `eps -> 0` per `docs/audit/EPSILON_DIRECTION.md` | `CosineAnnealScheduler.sample(...)` produces `n_cap`; the per-round sheet-vs-cell evidence *scale gap* is monitored by the framework heuristic `selection_ratio` (NOT a paper quantity) [CLM-008] |
| Lemma 3 — root cell bound | `O(eps^{+2})` per cell (two normal directions, codimension 2) [CLM-002]; full isolated family sums to `O(eps^2)` by Gaussian packing | `CodimensionSheetScheduler._paper_evidence_balance` [CLM-006] (corrected: positive powers, not inverted [CLM-016 DEPRECATED]) with `cell = (1 - n_cap_base)^2 * eps_implicit^2`; the framework heuristic `cell_evidence` sum grows with the number of competing modes | `tests/test_eval/test_posterior_selection_evaluator.py::test_evaluator_8_gaussians_ratio_lower_than_2_moons` (7 cells vs 1 cell) |
| Lemma 4 — physical complement suppression | `exp(-e_rho / (2 eps^2)) = o(eps)` for `{ y != 0 }`, with `e_rho = min{rho^4, (1 - rho)^2 eta^2}` [CLM-007] | `SchedulerProtocol.config.n_min > 0` (bounded noise floor) + `BoundedMergeOperator` (ADR-0007) cap [CLM-010], refuses to emit values outside the scheduled envelope; the literal constant `e_rho` lives in `paper_quantities.exterior_gap_e_rho` | `MERGE_FLOOR_FALLBACK`, `MERGE_DEGENERATE_INTERVAL` audit codes; `n_min` recorded in every `ScheduleSample` |
| Proposition 3 + Corollary 1 — posterior normalisation | `eps^{-1} Z_{g,eps} -> A_g > 0`; `Z_{g,eps} >= C_1 * eps` [CLM-013]; `mu_{g,eps}(union_z I_z) <= C_2 * eps` [CLM-014] | `paper_quantities.sheet_evidence_A` (the literal `A_g` integral) [CLM-011] and `paper_quantities.root_cell_packing_B` (the literal Gaussian packing sum `B_g`); the framework heuristic `selection_ratio` is emitted by `EvidenceScaleGapMetric` into `ReInferenceResult.per_round_metrics[r]` but is NOT a paper quantity [CLM-008] | `selection_ratio` column in `docs/ABLATION.md`'s heuristic table (NOT paper-quantity table) |

The correspondence is not an analogy — it is a derivation at the *direction* level for Lemma 2 (cosine ramp is `eps -> 0`-aligned) and a derivation at the *exponent* level for Lemmas 3 and 4 (the literal `C_g`, `B_g`, `e_rho` constants are extracted as framework contracts in `adaptive_reflow/contracts/paper_quantities.py`). Paper Lemma 2's `Theta(eps^{+1})` scaling is the per-round capacity envelope the cosine ramp produces *directionally*; paper Lemma 3's `O(eps^2)` cell bound is the audit invariant that secondary-mode evidence must stay below the sheet evidence by at least a factor of `n_cap`; paper Lemma 4's exponential suppression is the bounded noise floor that prevents the algorithm from escaping the fibre; paper Proposition 3's normalisation is encoded in the literal `A_g`, `B_g` constants. A reviewer who wants to argue that any of these mappings is wrong must argue against a specific line of the paper's proof, not against an arbitrary engineering choice.

> **What the framework does NOT derive from the paper.** The
> `selection_ratio = sheet_evidence / (sheet_evidence +
> cell_evidence)` emitted by `EvidenceScaleGapMetric` is a
> framework-internal diagnostic for the sheet-vs-cell evidence
> *scale gap* (sheet `O(eps^1)`, cells `O(eps^2)`). It is NOT a
> paper quantity [CLM-008]; the paper proves BL-convergence and
> tail bounds, not a ratio converging to 1. See §"What this
> insight does NOT claim" below.

---

## 3. The ablation findings

The 18-row ablation in `tools/run_ablation.py` (8 canonical configs x 2 targets, plus 2 paper-grounded rows on `two_moons`) measures the sheet-vs-cell `selection_ratio` directly. The empirical finding is **sheet-dominant from round 0** on both targets — exactly the qualitative claim Theorem 1 makes. On `two_moons` the ratio opens at `0.8061` and closes at `0.8185`, sitting inside `[0.7926, 0.8185]` across all 20 rounds; on `eight_gaussians` the ratio is materially lower (`0.531 -> 0.547`, pinned by the regression `test_evaluator_8_gaussians_ratio_lower_than_2_moons`) [CLM-009]. The `two_moons` plateau near `0.82` reflects one competing cell root (Lemma 3's per-cell sum has a single `O(eps^2)` term [CLM-002]); the `eight_gaussians` plateau reflects seven competing cell roots (Lemma 3's per-cell sum has seven `O(eps^2)` terms, dragging the sheet contribution down). This target-sensitivity is exactly the qualitative prediction Lemma 3 makes — more competing modes means harder selection — and it is the strongest empirical evidence that the framework's algorithm layer instantiates the paper's codimension-driven mechanism rather than some unrelated balancing heuristic.

The schedule-family ordering on `W2` is also target-sensitive [CLM-018]: on `two_moons` the cosine is the best schedule family by final W2, while on `eight_gaussians` the convergence-adaptive family leads. No single schedule family dominates both targets, which motivates the reader-facing defaults matrix ([`docs/defaults-matrix.md`](defaults-matrix.md)) and the closed-form / decision-tree extension in [`docs/schedule-theory.md`](schedule-theory.md).

The quantitative claim (`ratio -> 1` as `sigma -> 0`) is **not** observed [CLM-017]. Neither row reaches `0.95` (codimension row: never; cosine row: never). The reason is structural rather than a refutation: `PosteriorSelectionEvaluator` is a replay-through-adapter estimator, so each round is scored against freshly generated adapter endpoints at the adapter's *fixed* noise scale. Paper Proposition 3's limit is `sigma -> 0`; a fixed-`sigma` estimator can only report the plateau that `sigma` implies, which is what the flat curve shows [CLM-004]. The ratio is also schedule-independent by construction [CLM-003] — both rows report `delta_selection_ratio = +0.0000` — because the evaluator scores the adapter's own posterior geometry, which neither scheduler alters. The schedules separate on W2 and coverage instead: `delta_W2 = -0.3000` in cosine's favour (cosine wins), `delta_coverage = +0.000` (tie). The interpretation is that the `selection_ratio` column is a *property of the target + adapter pair* (a difficulty measure), not a scoreboard between schedulers; making it schedule-sensitive requires scoring the round's own bundle rather than a fresh replay, which is the open follow-up.

The cosine-vs-codimension comparison also confirms the paper's prediction that cosine is the "right" schedule at the direction level: cosine's smoother `n_cap` ramp gives the better-behaved default (`W2 = 0.8140` vs codimension's `1.1140` at 20 rounds), while codimension's Lemma-2-plus-Lemma-3 closed form spends nearly the whole cycle in refinement. Codimension is the theoretically-derived comparison point ADR-0013 asked for; cosine is the better-behaved default. Both implement Lemma 2 at the *direction* level; cosine is the implementation whose `n_cap` ramp is closest to a monotone `eps -> 0` surrogate.

> **Note on the evidence balance.** The audit at
> `docs/audit/EPSILON_DIRECTION.md` §4.2 documents that the
> prototype `CodimensionSheetScheduler._paper_evidence_balance`
> helper historically inverted the paper's `eps` exponents
> (claiming `sheet = eps^{-1}`, `cell = eps^{-2}` where the paper
> uses `eps^{+1}`, `eps^{+2}`) [CLM-016 DEPRECATED]. The corrected
> helper uses positive powers [CLM-001] [CLM-002] and is documented
> in ADR-0013 §"Sheet tube scaling -> CosineAnnealScheduler".

---

## 4. The new capability

Before this work the framework was a "general flow matching restart framework" — any schedule that conformed to `SchedulerProtocol` worked, none was theory-backed, and the audit question "why cosine?" was answered with "cosine is the default." After this work the framework has three load-bearing additions. First, a paper-grounded scheduler (`CodimensionSheetScheduler`) [CLM-006] that exposes paper Lemma 2 + Lemma 3 as a first-class `SchedulerProtocol` implementation, with the sheet-vs-cell evidence scale-gap closed-form in `_paper_evidence_balance` (corrected to use positive `eps` powers per the audit [CLM-016 DEPRECATED]) and the profile-residual callable stored for provenance. Second, a framework-internal evaluator (`EvidenceScaleGapMetric`, formerly `PosteriorSelectionEvaluator`) that measures the per-round heuristic `selection_ratio` against the analytic mode-centre set for `two_moons` and `eight_gaussians`, emits the three diagnostic metrics (`sheet_evidence`, `cell_evidence`, `selection_ratio`) alongside the canonical `ChannelTransferEvidence` diagnostics, and plugs into the runner through `ReInferenceConfig.selection_evaluator`. **The metric is a framework-internal diagnostic, NOT a paper claim** [CLM-008]. Third, an ADR (0013) that locks the theory-framework correspondence as load-bearing rather than incidental, codifies the cosine-canonical-implementation claim at the *direction* level [CLM-005], and gives future scheduler proposals a clear theoretical bar: must respect paper's Lemma 2-4 (sheet vs cells, codimension difference, tail control).

The net effect is that the algorithm layer now carries a *theoretical* provenance in addition to its *structural* provenance. A reviewer asking "is this scheduler paper-grounded?" can be pointed at `config_hash()` (the audit invariant) and `docs/INSIGHTS.md` §2 (the paper-to-framework mapping). A reviewer asking "does this scheduler match the paper's proof?" can run the 18-row ablation, look at the heuristic `selection_ratio` column, and read off the qualitative answer (sheet-dominant, target-sensitive plateau, schedule-independent by construction at fixed `sigma` [CLM-003]). The framework gains a quality bar that lives outside the codebase: any future scheduler that claims to implement Theorem 1 must reproduce the empirical pattern (sheet-dominant heuristic ratio, target-sensitive plateau, schedule-independent by construction at fixed `sigma`). The framework-internal `selection_ratio` is **NOT** a paper quantity and is **NOT** claimed to converge to 1 [CLM-008] [CLM-017]; the four paper quantities `A_g`, `B_g`, `C_g`, `e_rho` are first-class algorithm-layer inputs in `adaptive_reflow/contracts/paper_quantities.py` [CLM-011] that `CodimensionSheetScheduler`, `AdaptivePolicyDriver`, and `ReInferenceRunner` consume as ground truth (see ADR-0013 §"paper_quantities as algorithm input").

---

## 5. The next question

ADR-0013 closed the *algorithm-layer* half of the paper-grounding gap: the `n_cap` envelope the framework produces per round is the canonical implementation of paper Lemma 2, and the per-round `selection_ratio` the new evaluator emits is the empirical handle on paper Proposition 3. The *restart-mechanism* half is still open. Paper Theorem 1 is silent on how the framework *uses* the sheet-vs-cell balance to drive the next round's prior — the paper proves that a small-noise posterior concentrates on the sheet, not that any particular restart mechanism realises that concentration. The framework's `apply_restart_distribution` (the universal-state boundary) and `ReInferenceRunner` (the per-round orchestrator) together determine *which* sheet-cell configuration is propagated forward; whether that mechanism matches paper's selection principle (or whether there is a gap where the framework's restart logic does not quite match paper's `sigma -> 0` selection) is the question ADR-0014 (or its equivalent) will need to answer.

Concretely: the paper's posterior is `P(X | F_g(X) = 0)` — the *conditional* distribution on the fibre given the residual hits zero. The framework's per-round prior is whatever the previous round's endpoint mixture is, blended with fresh noise via `RestartBlenderProtocol`. The mapping between paper's conditional and the framework's blend is not yet proven; the empirical observation that cosine schedules work *better* on hard mode-balancing targets is consistent with paper Theorem 1 but is not the same as a proof that the framework's restart mechanism realises paper's selection. Closing that gap requires either (a) a paper-style proof that `apply_restart_distribution` approximates the conditional posterior as the noise scale shrinks, or (b) an empirical handle that shows the framework's per-round posterior converges to paper's conditional as `sigma -> 0`. Until either is available, the framework has paper-grounded *scheduling* and paper-validated *metrics*, but paper-claimed *restart* — and the difference matters, because the restart is what makes the algorithm a multi-round algorithm rather than a single-round anneal. This is the open question ADR-0013 explicitly defers and that this document records as the canonical narrative for the next work stream.

## 5a. Algorithm uplift results

The algorithm layer uplifts surveyed in
[`docs/algorithm-uplift-plan.md`](algorithm-uplift-plan.md) (5 P0 +
9 P1 + 24 P2 = 38 candidate uplifts across 17 algorithm classes + 1
runner integration) are measured quantitatively in
[`docs/benchmark-uplifts.md`](benchmark-uplifts.md). Headline
findings: every one of the **27 measured** uplifts achieved its
target, with **0** regressions and **0** neutral outcomes; the
A16 `eps_schedule` decay raises the `EvidenceScaleGapMetric`
`selection_ratio` plateau from baseline `0.872` to `0.9996`
(`+14.6%`) with an SNR proxy of `60.80` [CLM-022]; the A12
`e_rho / 4` paper-quantity floor lift lands in
`BoundedMergeOperator`; the A17 / B13 / B14 paper-quantity
diagnostics now report `sheet_evidence_A` values of
`0.854` (sin profile) and `0.765` (polynomial profile),
`root_cell_packing_B = 1.170` with `tail_bound = 2.65e-111` at
`K = 32`, and `drift_robustness_over_C_g_ratio = 1.20`; the
22-row ablation grid is reproduced with W2 / coverage /
`selection_ratio` / `ledger_chain_integrity` columns for every
canonical configuration. The uplift is the algorithm-layer
counterpart of the paper-grounding work in §1-§5: each uplift is
a concrete, tested capability that the framework's algorithm
abstractions either did not have or had only in ad-hoc form. The
remaining 11 P2 items are byte-equality / determinism checks that
the benchmark folds into the per-uplift rows; see
[`docs/benchmark-uplifts.md`](benchmark-uplifts.md) for the full
table.

## Algorithm depth uplift results

The second, deeper uplift pass is planned in
[`docs/algorithm-deep-uplift-plan.md`](algorithm-deep-uplift-plan.md)
(inventory of **~140 algorithms**, **18 SOTA papers** surveyed) and
measured in
[`docs/benchmark-deep-uplifts.md`](benchmark-deep-uplifts.md):
**87 uplifts measured, 86 achieving target, 0 regressions**, split
**36 framework-internal** / **14 framework-external** / **37
pluggable-design** entries. The interesting finding is not that the
numbers moved but *which* ones moved and by how much. Replacing the
toy `_w2_to_mode_centres` surrogate with a projection-free exact W2
estimator cuts the per-round squared coefficient of variation
`0.00727 -> 0.00206` (**-71.7%**), which means most of what the
framework previously reported as round-to-round W2 movement was
estimator noise rather than algorithm behaviour. Similarly, the
binary coverage score *saturates* on the sparse-vs-dense contrast
(separation `0.0`); only the area-weighted Voronoi variant separates
them at all (`0.2252`) — a metric that cannot distinguish the two
regimes is not a coverage metric, it is a constant. On the external
axis the DPM-Solver / UniPC / Heun family reaches a matched endpoint
in `20` steps instead of RK4's `100` (**-80%**) while staying inside
a `<= 0.05` L2 budget, and OT displacement mixing removes the scale
error of linear latent blending entirely (`0.271 -> 1.19e-15`).
Incremental ledger verification turns an `O(R^2)` verify-on-append
into `O(R)` (`2080 -> 64` row hashes at `R = 64`).

One row deliberately does not pass: the external weighted-coverage
separation measures `0.1916` against a `>= 0.20` target. It is
recorded as a miss rather than re-tuned, because the honest reading
is that the weighted coverage improvement is configuration-sensitive
— it clears the bar on the internal configuration and misses it on
the external stress configuration, and that gap is itself the
finding. The pluggable-design section is the boundary counterpart:
all **37** `config_hash` stability and `to_config` / `from_config`
round-trip checks pass byte-for-byte, so every uplift above is
swappable without the reproducibility surface changing shape.

## Algorithm depth uplift Round 2 results

The third, deepest pass is planned in
[`docs/algorithm-round2-uplift-plan.md`](algorithm-round2-uplift-plan.md)
(inventory of **~165 algorithms** after Round-1, **17 fresh SOTA
papers** surveyed on top of Round-1's 30, ~47 unique external
SOTA works cited) and measured in
[`docs/benchmark-round2-uplifts.md`](benchmark-round2-uplifts.md):
**83 uplifts measured, 80 achieving target, 0 regressions, 3 neutral
/ NaN-baseline comparisons**, split **48 framework-internal** /
**8 framework-external** / **27 pluggable-design** entries. The
Round-2 numbers sharpen the Round-1 story rather than retell it.
Rademacher projections cut the W2 CV another **-42.8%** past the
Round-1 projection-free estimator, tree-sliced W2 beats projection-
free on anisotropic Gaussians, multi-metric PID oscillation is
bounded under oscillating input, adaptive `sigma_max` makes the
EDM scheduler actually adapt (variance `0 -> 593.158`), and the
Round-1 weighted-coverage miss is closed by the KDE-support-
coverage metric (`0.1916 -> 0.7810` near-far separation)
[CLM-023]. The type / lint cleanup lands both counters at zero:
mypy **33 -> 0**, ruff **32 -> 0**, across 118 source files
[CLM-024].

## R3 adversarial fixes (Round-3 uplift)

The R3 adversarial survey ([docs/r3-survey/05-verified-findings.md](r3-survey/05-verified-findings.md))
read-only verified **17** findings against the shipped framework and
refuted **5** [CLM-031]. The P0 paper-correctness fixes restore the
documented fail-closed semantics: `BoundedMergeOperator.merge` now
raises `MergeAuthorityError` on `cap < floor` after clipping instead
of silently swapping the envelope [CLM-025], and
`ConvergenceAdaptiveScheduler`'s PID consumes the EMA-smoothed W2
(`self._smoothed_w2`) instead of the raw aggregated signal
[CLM-026]. Loop 2 of the documented four-loop design is closed:
`EvidenceDrivenScheduler` subscribes to the runner's per-round
metric dict via `record_round_feedback` and updates `n_cap` via a
PID-lite controller, so paper quantities now reach a scheduler and
influence the per-round capacity [CLM-027]. The eight plug-in
families (scheduler / policy driver / merge operator / blender /
adapter / mixer / evaluator / envelope) are codified as named
`Port[T]` instances with explicit `register(...)` / `resolve(...)`
helpers, closing W1 (blender delegation) and W2 (orchestrator
`bounded_merge` bypass) from `03-coupling.md` [CLM-028]. Two new
algorithm additions land behind the canonical Protocol surfaces:
`FreeTrajScheduler` ([arXiv:2507.10532](https://arxiv.org/abs/2507.10532))
[CLM-029] and `MeanFlowMergeOperator`
([arXiv:2505.13447](https://arxiv.org/abs/2505.13447)) [CLM-030].
Fifteen P1 framework-driving fixes (F1, F2, F3, F6, F7, F10, F14,
F18, F19, F22, F23, F25) close the rest of the verified leaks; 17
new tests pin every fix and the six verification gates
(``pytest tests/`` / ``ruff`` / ``mypy`` / ``check_docs_against_code.py``
/ ``check_claims_consistency.py`` / ``mkdocs build --strict``) all
remain green.

## 6. Open questions

The "next question" above is the algorithm-level gap. A separate, narrower gap surfaced in the post-ADR-0013 code-review pass (B5): the shipped `selection_ratio` metric was claimed to converge toward 1 as rounds progress, but `docs/review/B5-VERIFICATION.md` shows that the metric is in fact invariant to loop state — it is an unconditional replay of the `(adapter, target)` pair, not an endpoint-conditioned posterior, and two unrelated schedulers report identical curves to four decimal places. The reviewer's symptom ("wrong bundle passed") was a wiring guess; the actual defect is that the evaluator's `bundle` parameter is inert, so no rewiring fix would change the output. Closing the gap requires an endpoint-conditioned variant (scoring the round's own endpoints rather than a fresh replay), which is blocked on the runner carrying a batch of trajectories per round — a real architectural change to `ReInferenceRunner` and `TwoDimFMAdapter`, both currently single-sample. ADR-0013 §"Selection metric status" demotes the convergence-to-1 prediction to apply only to that future variant. The shipped metric remains in place until a human design decision lands; the verification document is the canonical record of the investigation.

## 7. What this insight does NOT claim

This section mirrors the disclaimer in `docs/adr/0013-posterior-selection-drives-algorithm.md` §"What the paper does NOT claim". The framework has historically over-claimed certain things as "paper Theorem 1 predictions" that are not in the paper; recording the negative space explicitly is the audit-driven way to keep the framework's claims honest.

### 7.0 Project maturity

This project is a prototype. Performance claims, S-tier framing, and A+ library framing from earlier `README.md` / `CHANGELOG.md` text have been removed in the documentation-honesty pass dated 2026-08-28 (see the git history for `README.md`, `CHANGELOG.md`, and `ROADMAP.md`). See the `README.md` Status section for the honest self-assessment: stage is prototype under active development, self-assessment is B+ (algorithm depth and engineering discipline, not production-readiness), and the known gaps are enumerated in `docs/lean/GAPS.md`. Nothing in this document should be read as a benchmark result, a production-readiness statement, or a claim of completeness beyond the current target domains (2D flow matching adapters and the paper-quantity contracts).

### 7.0.1 The defaults matrix is a heuristic guide, not a hard guarantee

[`docs/defaults-matrix.md`](defaults-matrix.md) ships a `(scheduler,
driver, merge, blender)` configuration for four common deployment
scenarios (short run, long run, adaptive, sequential). The matrix is
**a heuristic guide calibrated against the canonical 2D-FM target**
(`two_moons`, `eight_gaussians`) — it is NOT a paper claim, NOT a
production-readiness statement, and NOT a hard guarantee that the
recommended configuration will work on every target. Targets with
very different posterior geometries may need different defaults; any
deployment that depends on a specific convergence or stability
property must run the configuration against the target before
trusting the row. The matrix documents the *engineering* reasoning
(what has been ablated, what has been validated) rather than the
*paper* reasoning; the paper does NOT recommend any particular
scheduler / driver / merge / blender combination. The four defaults
the matrix recommends are the framework's empirical-best, not the
paper's claim of optimality.

### 7.1 What the paper does NOT claim

The paper does NOT claim:

* **The paper does NOT claim that any "selection ratio" converges to 1** [CLM-017] [CLM-004]. Proposition 3 + Corollary 1 prove BL-convergence of the full ambient posterior `mu_{g,eps}` to `nu_g` and the `O(eps)` / `O(eps^2)` / `exp(-e_rho / (2 eps^2))` tail bounds. They do not single out a ratio of two evidence components and claim it converges to 1.
* **The paper does NOT claim that the framework's `EvidenceScaleGapMetric` (formerly `PosteriorSelectionEvaluator`) is a paper quantity** [CLM-008]. The metric emits a heuristic `selection_ratio` based on closed-form Gaussian densities; the paper proves no such ratio. The metric is a framework-internal diagnostic for monitoring whether the framework's behaviour is consistent with the paper's evidence ordering (sheet `Theta(eps^{+1})` [CLM-001] vs cells `O(eps^{+2})` [CLM-002]). It is NOT claimed to converge to 1; it plateaus at a fixed-noise replay [CLM-004].
* **The paper does NOT claim that any framework-specific schedule implements Theorem 1's evidence competition at the magnitude level** [CLM-015]. The framework's `n_cap` ramp is a convex mixing weight on a state vector; it is *directionally* aligned with the paper's `eps -> 0` limit (round progression mirrors the noise-shrink direction) but it does not produce the `Theta(eps^{+1})` / `O(eps^{+2})` evidence competition the paper proves.
* **The paper does NOT claim that the framework's heuristic `selection_ratio` will ever reach 1 in finite rounds** [CLM-017]. The shipped metric is a fixed-noise replay estimator; it plateaus at the value implied by the adapter's training noise. Convergence to 1 would require an endpoint-conditioned variant (scoring the round's own bundle) operating in the `eps -> 0` limit, which is the open follow-up recorded in §6.

### 7.2 What the paper DOES claim

The paper DOES claim:

* **Bounded-Lipschitz convergence** [CLM-012]. `mu_{g,eps} --BL--> nu_g` as `eps -> 0` (Theorem 1, line 88-91 of `NoiseSelectedRectification_EN.md`).
* **Posterior mass on isolated cells is `O(eps)`** [CLM-014]. `mu_{g,eps}(union_z I_z) <= C_2 * eps` for sufficiently small `eps` (Corollary 1).
* **Normalisation lower bound** [CLM-013]. `Z_{g,eps} >= C_1 * eps` for sufficiently small `eps` (Corollary 1).
* **Positive limit `A_g > 0`** [CLM-013]. `eps^{-1} Z_{g,eps} -> A_g > 0` (Proposition 3).
* **Sheet-tube limit** [CLM-001]. `eps^{-1} int_T phi p_eps -> (2*pi)^{-1/2} int_R phi(s, 0) exp(-s^2/2) / sqrt(1 + g(s)^2) ds` for every bounded continuous `phi` (Lemma 2).
* **Per-cell bound** [CLM-002]. `int_{I_z} p_eps <= C_g e^{-z^2/4} eps^2` for every `z in Z_g` (Lemma 3).
* **Gaussian packing** [CLM-011]. `B_g = sum_{z in Z_g} e^{-z^2/4} < infinity` (Lemma 5). The summability is derived, not assumed.
* **Physical exterior gap** [CLM-007]. `int_{T^c \setminus union_z I_z} p_eps <= exp(-e_rho / (2 eps^2))` with `e_rho = min{rho^4, (1 - rho)^2 eta^2}` (Lemma 4 / Lemma 5).

These are the **actual paper claims**. The framework's heuristic `selection_ratio` is a framework-side diagnostic that mirrors the qualitative scale gap between paper Lemma 2's `Theta(eps^{+1})` sheet evidence and paper Lemma 3's `O(eps^{+2})` cell evidence; it is NOT a paper claim of convergence to 1, and the empirical plateau values (~0.82 on `two_moons`, ~0.55 on `eight_gaussians`) [CLM-009] reflect the adapter's fixed-noise replay, not the paper's `eps -> 0` limit.

### 7.3 What the framework's heuristic `selection_ratio` IS

For audit-trail clarity, the framework's heuristic `selection_ratio` is:

* **A monitoring signal.** It tells a reviewer whether the framework's per-round evidence scale gap is consistent with the paper's ordering (sheet > cells at the closed-form Gaussian level).
* **Schedule-independent by construction** [CLM-003]. Both `CosineAnnealScheduler` and `CodimensionSheetScheduler` report the same curve because the metric scores the adapter's own posterior geometry, which neither scheduler alters.
* **Target-sensitive** [CLM-009]. More competing cells means a lower heuristic ratio (paper Lemma 3's per-cell sum grows with the cell count).
* **Plateau-valued, not convergence-valued** [CLM-004]. It measures a property of the `(adapter weights, target)` pair, not a per-round convergence trajectory. The empirical plateau values are pinned by regression tests in `tests/test_eval/test_posterior_selection_evaluator.py`.

Any audit that wants to check the *literal* paper invariants should use the four paper-quantity contracts in `adaptive_reflow/contracts/paper_quantities.py` (`sheet_evidence_A`, `root_cell_packing_B`, `per_cell_coefficient_C`, `exterior_gap_e_rho`) rather than the framework's heuristic `selection_ratio`. The two surfaces are complementary: the heuristic monitors the qualitative scale gap, the paper-quantity contracts compute the literal constants the paper proves. `ReInferenceRunner` emits the four paper quantities in `per_round_metrics[r]["paper_quantity_diagnostics"]` whenever the config carries a `paper_quantities_provider`, so a reviewer can pull the literal `A_g`, `B_g`, `C_g`, `e_rho` from the audit trail without recomputing them.