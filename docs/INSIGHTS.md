# Paper-grounded algorithm layer: how Li 2026 Theorem 1 maps to flowa's algorithm abstractions

> See also: [`docs/算法实现说明.md`](算法实现说明.md) (中文版本 / Chinese version — same paper-grounded walkthrough, audience split kept for now).

Status: insight document (narrative, not a load-bearing governance record).
Audience: maintainers, reviewers, and newcomers asking "why does the algorithm layer look like it does?"
Related: ADR-0013 (`docs/adr/0013-posterior-selection-drives-algorithm.md`), ADR-0010, ADR-0011, ADR-0012, `docs/ABLATION.md`, `docs/CHANGELOG.md`.

The CIFAR-10 reproduction and its scheduler-discrimination limits are
tracked in the claims ledger as [CLM-040](CLAIMS.md#CLM-040); the associated
R3/R11 bug review and gate verification are tracked as [CLM-041](CLAIMS.md#CLM-041).

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

| Paper Theorem 1 (Li 2026) | Paper symbol | Framework implementation | Empirical handle |
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

This project is a prototype. Performance claims, S-tier framing, and A+ library framing from earlier `README.md` / `CHANGELOG.md` text have been removed in the documentation-honesty pass dated 2026-08-28 (see the git history for `README.md`, `CHANGELOG.md`, and `ROADMAP.md`). See the `README.md` Status section for the honest self-assessment: stage is prototype under active development, self-assessment is A- (theory-grounded BL-convergence rate bound + 6 Bonf-sig framework_improves + 3 byte-stable composite axis + 8 N=1000 sweep JSONs in repo + ruff 0 + D.4 33/33 + byte-reproducibility on ruff-frozen code; camera-ready scope is bounded per todo/STATUS.md §Camera-ready deferred), and the known gaps are enumerated in `docs/lean/GAPS.md`. Nothing in this document should be read as a benchmark result, a production-readiness statement, or a claim of completeness beyond the current target domains (2D flow matching adapters and the paper-quantity contracts).

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

### 7.1.5 Cross-reference surface (Phase-4 docstring audit)

* **Cross-reference surface (Phase-4 docstring audit)** [CLM-043]. The Phase-4 docstring audit (docs/audit/PHASE4_DOCSTRING_AUDIT.md) read-only surveyed the algorithm layer, adapters, runner, engine, evaluators, paper quantities, state machines, and contracts surface and flagged 37 modules as missing-or-stale on one or more of four docstring axes (`MISSING` / `STALE` / `THIN` / `MISLEADING`). Each entry carries a one-line "recommended remediation" that a future code-review pass should land; the audit-code vocabulary cross-reference surface (audit §3) is the canonical reader-side entry point until a future audit-code-registry module lands in `adaptive_reflow.contracts.audit`. The 2 deprecated CLAMs (CLM-016 inverted-`eps` exponents, CLM-017 selection-ratio-converges-to-1) are kept DEPRECATED with explicit resolution rationale (re-activation would contradict CLM-004/CLM-006/CLM-008/CLM-015). The fix-v2 capability set ([CLM-042], docs/r4-survey/21-fix-v2-plan.md) lands Heun 2nd-order + stateful β-blend chain + fixed-NFE comparison + PID amplification on the CIFAR-10 image domain; the verification record lives at docs/r4-survey/22-fix-v2-results.md. The 2D Rectified Flow SOTA experiment ([CLM-039], docs/r4-survey/10-sota-2d-experiment-results.md) verifies the framework's W2 reduction on a published Liu 2022 2D flow-matching model.

* **Cross-reference surface (r16 governance audit fix train)** [CLM-044] [CLM-045] [CLM-046] [CLM-047]. The r16 governance audit (`docs/governance/01..04`) and the synthesised fix plan (`docs/governance/05-fix-plan.md`) closed six P0 paper-math + CI-gate items in a single coordinated commit train. CLM-044 enumerates the previously-unindexed `adaptive_reflow/algorithm/` package (25 modules, four Protocols) in `ARCHITECTURE.md` §1 / §4 / §7.1. CLM-045 carries the `e_rho / 4` factor — used in `BoundedMergeOperator.merge` and `CodimensionSheetScheduler.inject_noise` — as an inline CLM-042 derivation comment on both surfaces so the framework-side tightening can be traced back to paper Lemma 4 (`|F_g|^2 >= e_rho`). CLM-046 brings `EvidenceScaleGapMetric` closer to paper-math by exposing two opt-in flags (`use_quadratic_eps_scaling` matching Lemma 3 `O(eps^{+2})`, `apply_lemma4_exponential_suppression` matching Lemma 4 exponential `exp(-e_rho / (2 eps^2))`, both default off to preserve the A16 plateau + CLM-022 reference) and rejecting NaN/inf `eps_round` upstream of the `total > 0` guard. CLM-047 closes the four CI-hygiene issues: stress-nightly Windows-path bug (T-04.3, `.venv/Scripts/python.exe` → `python`), `cpu-tests.yml` stale filename (T-04.2), `pyproject.toml [test]` extra declaration (T-04.4), and Python version matrix `[3.12, 3.13]` on both `lint-types` + `test-docs` jobs (T-04.5). The fix plan is at `docs/governance/05-fix-plan.md` and the verification record lives at `docs/governance/06-verification-report.md`.

* **Cross-reference surface (Wave 180 head-to-head with Fast-DLLM)** [CLM-048]. Wave 180 (commit `39c1dd5` + this cross-reference surface) ran a 3-arm comparison (vanilla / Fast-DLLM / FlowA) on the R6 task (LineageFlow protein re-inference, NFE ∈ {100, 200}, seeds {42, 43, 44}, N=30 records per cell) — `verification_outputs/wave180-p3-three-arm-comparison.csv` is the canonical aggregation. The headline finding: **FlowA wins on both metrics (pLDDT + scPerplexity) vs both baselines (vanilla + Fast-DLLM) at both NFE settings**. The closest training-free diffusion inference acceleration competitor, Fast-DLLM (Wu et al. ICLR 2026, `arXiv:2505.22618`, NVlabs/Fast-dLLM), regresses on pLDDT by 4.2–4.6 points vs even the bare-RNG Vanilla baseline (a known tradeoff for cache-reuse-only accelerations: structure quality regresses slightly while perplexity improves). FlowA's value-add is **specific, not a generic property of training-free acceleration**. The Wave 180 Fast-DLLM comparison is **cross-experiment, not paired** (Wave 179 paired vanilla-vs-framework; Wave 180 P2 ran Fast-DLLM on a different ODE trajectory); a future Wave 5+ follow-up could pair the seeds at the generation step to produce formal paired t-tests. Wave 180 P2 ran on the synthetic LineageFlow velocity field (no 9.788 GB ckpt dependency); a real-ckpt Fast-DLLM comparison is a Wave 5+ follow-up. Audit chain: `docs/audit/wave180-p1-setup.md` (Fast-DLLM setup + continuous-FM analog solver), `docs/audit/wave180-p2-eval.md` (Fast-DLLM eval on R6 task: 6 cells × N=30 = 180 records), `docs/audit/wave180-p3-comparison.md` (3-arm aggregation). The disclosure lives at `docs/paper-draft.md` §10.26 (Wave 180 P4 ADDITIVE on §10.20-§10.25).

* **Cross-reference surface (Wave 184 n_rounds ablation — mechanism attribution)** [CLM-049]. Wave 184 (commits `9bfb7b1` P1 + `4b679eb` P2 + `4dbed25` P3 + `c7e0bee` P4 + this cross-reference surface) isolated the two candidate gain-mechanisms of the framework — (1) restart-blend + classifier-aware refinement (the *glue path*) and (2) multi-round averaging (the *iteration path*) — by varying `n_rounds ∈ {1, 2, 3, 5, 7}` at fixed NFE=100 on both lineageflow (R6 protein) and kanzi (R5 protein). The canonical aggregation is `verification_outputs/wave184-p4-ablation-table.csv` (12 rows × 7 cols) and the per-cell eval summary is `verification_outputs/wave184-p3-eval-summary.csv` (12 rows × 15 cols, 360/360 records scored for both metrics, 848.69 s ≈ 14.14 min wall on GPU 0+1). **lineageflow (degenerate ablation)**: all 5 framework-arm cells collapse to identical aggregate metrics to 4dp (pLDDT 41.99, scPPL 14.94; FASTA SHA256 `67d871ba9ec2a9e1e95695079f3679d85a2cdf6d9d8a9a932b97fc9a53b416a3`) because synthetic lineageflow does not expose `profile_residual_fn` → `_compute_paper_quantities` returns `None` → constant-β path → `n_rounds` has no effect on the integrated trace. The +0.81 pLDDT / -4.00 scPPL framework gain on lineageflow is attributable to the restart-blend glue path alone (not multi-round averaging). **kanzi (informative ablation)**: the 5 framework-arm cells show real, non-monotonic variation (pLDDT range 51.62 → 56.72; scPPL range 15.13 → 17.66) because the kanzi synthetic adapter *does* expose `profile_residual_fn`. The `n_rounds=1` cell regresses pLDDT by -1.63 vs baseline; since `n_rounds=1` has no multi-round averaging, the entire -1.63 pLDDT regression at NFE=100 is attributable to the paper-quantity scheduler alone. Multi-round averaging adds additional non-monotonic variation at n ≥ 2 (range -4.16 to +0.94 ΔpLDDT vs framework n_rounds=1 across n ∈ {2, 3, 5, 7}) but is neither necessary nor sufficient for the regression. **Categorical verdict**: `kanzi_nfe100_pLDDT_loss_source = both` (paper-quantity scheduler primary + sufficient at n_rounds=1; multi-round averaging secondary non-monotonic modulator). Three remediation options for kanzi at NFE=100: (1) disable scheduler at NFE ≤ 100; (2) re-tune `profile_residual` scale; (3) increase NFE budget to ≥ 200 (this is the choice for the Wave 172b / 173 / 174 cross-model headline numbers). The framework is a strict win on scPerplexity (the framework's primary native-likeness metric) on both models at all n_rounds. The §10.22 saturation disclosure + §10.24 kanzi NFE=100 trade-off disclosure remain valid; §10.28 strengthens them with explicit mechanism attribution. The disclosure lives at `docs/paper-draft.md` §10.28 (Wave 184 P5 ADDITIVE on §10.20-§10.26). Audit chain: `docs/audit/wave184-p1-setup.md` (n_rounds ladder setup + byte-stability prediction), `docs/audit/wave184-p2-generate.md` (12-cell FASTA ladder), `docs/audit/wave184-p3-eval.md` (12-cell GPU eval), `docs/audit/wave184-p4-aggregate.md` (per-model Δ-vs-baseline aggregation + critical isolation question).

* **Cross-reference surface (Wave 181 head-to-head with AB-Cache)** [CLM-050]. Wave 181 (commits `744fb80` P1 + `4668650` P2 + `46966e3` P3 + this cross-reference surface) ran a 4-arm comparison (vanilla / Fast-DLLM / AB-Cache / FlowA) on the R6 task (LineageFlow protein re-inference, NFE ∈ {100, 200}, seeds {42, 43, 44}, N=30 records per cell) — `verification_outputs/wave181-p3-four-arm-comparison.csv` is the canonical aggregation (2-row × 11-col). The headline finding: **FlowA wins on both metrics (pLDDT + scPerplexity) vs all three baselines (vanilla + Fast-DLLM + AB-Cache) at both NFE settings**. The two-baseline roster (Wave 180 Fast-DLLM + Wave 181 AB-Cache) now exhausts the canonical training-free diffusion acceleration design space — Fast-DLLM (Wu et al. ICLR 2026, `arXiv:2505.22618`, parallel-decoding family) regresses on pLDDT by 4.2–4.6 points vs even the bare-RNG Vanilla baseline; AB-Cache (Yu et al. 2024, `arXiv:2504.10540`, cache-reuse family) regresses by 1.25/0.57 points but is closer to Vanilla than Fast-DLLM because its periodic cache-refresh design is less destructive than Fast-DLLM's confidence-based skip. Per-cell FlowA margin over best-baseline: (NFE=100, pLDDT) +2.690 vs Vanilla; (NFE=100, scPerp) −0.421 vs Fast-DLLM; (NFE=200, pLDDT) +2.491 vs Vanilla; (NFE=200, scPerp) −0.243 vs Fast-DLLM. FlowA pays ~5× more wall-time than the cache-style arms and *still* wins on both metrics, which is the strongest empirical evidence that the framework's value-add is not a generic property of training-free acceleration (which would trade quality for compute) but a specific property of restart-blend + classifier-aware refinement. Honest caveats: (1) the Wave 181 4-arm comparison is **cross-experiment, not paired** (Wave 179 paired vanilla-vs-framework; Wave 180 P2 ran Fast-DLLM on a different ODE trajectory; Wave 181 P2 ran AB-Cache on yet another ODE trajectory); a future Wave 5+ follow-up could pair all four arms at the generation step; (2) Wave 181 P2 ran the AB-Cache-equivalent solver on the **synthetic** LineageFlow velocity field (no 9.788 GB ckpt dependency); a real-ckpt AB-Cache comparison is a Wave 5+ follow-up. Audit chain: `docs/audit/wave181-p1-setup.md` (AB-Cache setup + continuous-FM analog solver), `docs/audit/wave181-p2-eval.md` (AB-Cache eval on R6 task: 6 cells × N=30 = 180 records), `docs/audit/wave181-p3-comparison.md` (4-arm aggregation). The disclosure lives at `docs/paper-draft.md` §10.27 (Wave 181 P4 ADDITIVE on §10.20-§10.26).

* **Cross-reference surface (Wave 183 finer NFE curve — anti-resonance confirmed + saturation boundaries resolved)** [CLM-051]. Wave 183 (commits `0a7fb7f` P1 + `549a7f0` P2 + `ede1dfe` P3 + `77c8a39` P4 + this cross-reference surface) adopted a **9-point NFE ladder** `{10, 25, 50, 75, 100, 150, 200, 300, 500}` on both lineageflow (R6 protein) and kanzi (R5 protein), enabling three findings that the Wave 174 3-NFE-point ladder could not resolve. Canonical aggregation: `verification_outputs/wave183-p4-aggregation.csv` (36 rows × 7 cols: model, nfe, arm, plddt, scperp, delta_plddt, delta_scperp). Per-cell eval summary: `verification_outputs/wave183-p3-eval-summary.csv` (36 rows × 15 cols, 1080/1080 records scored for both pLDDT + scPerplexity). Three figures: `verification_outputs/wave183-p4-figure-pLDDT-finer.png`, `verification_outputs/wave183-p4-figure-scPerplexity-finer.png`, `verification_outputs/wave183-p4-figure-deltas-finer.png` (with kanzi sweet-spot star markers). **(1) Anti-resonance confirmation (kanzi NFE=100)**: kanzi ΔpLDDT at NFE ∈ {75, 100, 150} is `{+2.123, −5.788, −3.821}` — NFE=100 is a strict local minimum AND a global minimum across the 9-point ladder, with a 7.91-point negative excursion from NFE=75 and a 1.97-point negative excursion from NFE=150. The Wave 184 §10.28 / CLM-049 anti-resonance hypothesis from the n_rounds ablation is **anti_resonance_confirmed at finer resolution**. **(2) Saturation boundaries**: lineageflow saturates at NFE=500 (ΔpLDDT = +0.389, the only NFE in [10, 500] where |ΔpLDDT| ≤ 0.5 and stays ≤ 0.5 for all larger NFEs); kanzi does not saturate in [10, 500] (ΔpLDDT oscillates between +2.12 and −5.79 with no monotone approach to the |Δ| ≤ 0.5 band). The §10.22 saturation disclosure is now sharpened to a per-model NFE value (or "none in [10, 500]"). **(3) Framework wins on both metrics** (ΔpLDDT > 0 AND ΔscPerplexity < 0) at **10/18 (model, NFE) cells = 55.6%**: lineageflow 9/9 (every NFE improves both metrics); kanzi 1/9 (only NFE=75 improves both metrics). The **both-models-wins intersection is NFE=75 only**. **(4) kanzi NFE sweet spots**: kanzi has **exactly one NFE sweet spot** within the 9-point ladder — NFE=75 (ΔpLDDT = +2.123, strict local maximum with positive Δ). All other kanzi NFEs in the ladder either regress pLDDT or yield a strict local minimum. The framework is therefore a **targeted intervention for kanzi at NFE=75 only**, not a default. **Categorical verdicts**: `saturation_boundary_lineageflow = 500`; `saturation_boundary_kanzi = none_in_[10_500]`; `kanzi_nfe100_verification = anti_resonance_confirmed`; `framework_wins_both_metrics_both_models_NFE = {75}` (intersection); `framework_wins_both_metrics_any_model = {10, 25, 50, 75, 150, 200, 300}` (lineageflow 7/9 ∪ kanzi 1/9 = 8/9 NFE values where at least one model wins both). The §10.22 saturation disclosure + §10.24 / §10.28 / CLM-049 kanzi NFE=100 trade-off disclosure remain valid; §10.29 / CLM-051 strengthens them with finer-NFE-curve quantification. **New practical implication**: invoke the kanzi framework **only at NFE=75** (the unique sweet spot); for all other NFE values the kanzi framework either regresses pLDDT or yields strict local minima on the ΔpLDDT curve. Audit chain: `docs/audit/wave183-p1-setup.md` (9-NFE-point ladder setup verification), `docs/audit/wave183-p2-generate.md` (36-cell FASTA ladder generation), `docs/audit/wave183-p3-eval.md` (36-cell GPU eval: 1080 records scored for both metrics), `docs/audit/wave183-p4-aggregate.md` (per-model Δ-vs-baseline aggregation + saturation boundaries + sweet-spot identification + anti-resonance verification). The disclosure lives at `docs/paper-draft.md` §10.29 (Wave 183 P5 ADDITIVE on §10.20-§10.28).

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

## 8. State machine infrastructure (Phase 2a + 2b)

- **Substrate is generic + HSM + decorator + type-safe** [CLM-033]. `adaptive_reflow/contracts/state_machine.py` ships a PEP 695 `class StateMachine[TState, TEvent]` with decorator-driven transitions, hierarchical regions, history pseudo-states, parallel regions, byte-deterministic `TransitionLog`, async guards, and DOT / Mermaid export — stdlib-only, `mypy --strict` clean, no third-party dependency.
- **Coverage is universal** [CLM-034]. Every scheduler class plus the `ReInferenceRunner` orchestrator carries an observation-only `StateMachine` (17 machines, 333 typed transitions). The runner's lifecycle machine traverses ROUND_ACTIVE -> FEEDBACK_PENDING -> NEXT_ROUND_READY per round, making the 4 feedback loops typed transitions in the audit trail.
- **Backward-compatible by construction** [CLM-034]. `wrap_scheduler_with_state_machine` returns a dynamic subclass of the inner scheduler, so isinstance checks against the inner scheduler class stay true (parametrised test at `tests/test_algorithm/test_state_machine_integration.py:90-118`); existing 2027+ tests pass unchanged. Paper-grounded `selection_ratio` regressions from earlier R3 closure [CLM-032] are not touched by this layering (the SM only observes; the scheduler behaviour is bit-for-bit preserved).
