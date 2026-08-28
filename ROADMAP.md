# Roadmap

`flowa-multistep-reinference` is a single-maintainer research prototype. The
roadmap below tracks the items currently open in `todo.json` and the
planned governance work. Every entry is a one-line
imperative with a target date and an ADR ID where one applies.

The "Now / Next / Later" buckets are calendar quarters, not promises.
They are reviewed at every release tag and updated when an item closes.

Status vocabulary: `[ ]` is open; `[x]` means **implemented and available
in this tree** — it does not mean production-hardened, benchmarked at
scale, or feature-frozen. Items whose surface exists but is opt-in / not
wired into a default path are labelled inline.

## Now (2026-Q3 — July through September)

- [ ] Close DTB-R0 §3 case 2 / case 5 hostile fixtures by 2026-09-15 [ADR-0005]
- [ ] Land `ToyGaussianAdapter` as the first non-molecular adapter under
      `adaptive_reflow.adapters` by 2026-09-22 [ADR-0003]
- [ ] Add a synthetic oracle harness that exercises the universal
      `Evaluator` Protocol without a model in the loop by 2026-09-29
- [ ] Author docs/adr/0006 (universal evaluator-oracle ADR) by 2026-09-30
- [ ] Stress-test `Engine.run_round` at 5,000 consecutive rounds under the
      synthetic oracle; budgets gated by `tools/bench/budgets.json` by
      2026-09-30 [ADR-0004]
- [ ] Update reader docs (`README.md`, `ARCHITECTURE.md` §5) to reflect
      the ToyGaussianAdapter recipe by 2026-09-30 [ADR-0003]
- [x] Algorithm depth uplift — implemented 2026-08-29. Phase 1 of
      [`docs/algorithm-deep-uplift-plan.md`](docs/algorithm-deep-uplift-plan.md)
      inventoried **~140 algorithms** across `adaptive_reflow/` and
      `tools/` and researched **18 SOTA papers** (W2 estimators,
      diffusion ODE solvers, coverage / energy metrics, noise
      schedules, controllers, Bayesian merge, OT mixing,
      bounded-Lipschitz estimators). Phase 2 implemented the P0 / P1
      uplifts in parallel on three axes: **36 framework-internal**,
      **14 framework-external**, **37 pluggable-design** entries.
      Phase 3 measured every one BEFORE / AFTER in
      [`docs/benchmark-deep-uplifts.md`](docs/benchmark-deep-uplifts.md):
      **86 of 87** measured uplifts achieved their quantitative
      target, **0** regressed. Headline numbers: projection-free
      exact W2 cuts the per-round squared CV `0.00727 -> 0.00206`
      (**-71.7%**); the batched runner cuts adapter invocations per
      round `8 -> 1` (**-87.5%**); DPM-Solver / UniPC / Heun reach a
      matched endpoint in `20` steps instead of `100` (**-80%**) at
      `<= 0.05` L2 error; OT displacement mixing cuts worst relative
      scale error `0.271 -> 1.19e-15`; incremental ledger
      verification cuts row hashes `2080 -> 64` (**-96.9%**) at
      `R = 64`. The one miss is the external weighted-coverage
      separation row (`0.1916` against a `>= 0.20` target), recorded
      rather than tuned to pass.
- [x] Algorithm layer uplift — implemented 2026-08-29. Phase 1 of
      [`docs/algorithm-uplift-plan.md`](docs/algorithm-uplift-plan.md)
      surveyed **38 candidate uplifts** across 17 algorithm classes +
      1 runner integration (5 P0, 9 P1, 24 P2). Phase 2 implemented
      the 5 P0 + 9 P1 + 13 of 24 P2 items behind regression tests
      with concrete audit-code / digest changes. Phase 3 ran
      [`docs/benchmark-uplifts.md`](docs/benchmark-uplifts.md)
      against every implemented uplift: **27 of 27** measured uplifts
      achieved their quantitative target, **0** regressed, **0**
      neutral; the 22-row ablation grid is reproduced with W2 /
      coverage / `selection_ratio` / `ledger_chain_integrity`
      columns. Headline numbers: A16 `eps_schedule` lifts the
      `selection_ratio` plateau from `0.872` to `0.9996` with SNR
      proxy `60.80`; A12 `e_rho / 4` paper-quantity floor lift
      lands; A17 reports `A_g_sin = 0.854`; B13 reports
      `B_g_sin_K32 = 1.170` with `tail_bound = 2.65e-111`.
- [x] Python 3.12 + `numpy<2.5` pin enforced across all declarative
      configs (`pyproject.toml` `requires-python` / ruff `target-version`
      / mypy `python_version`, and every `.github/workflows/*.yml`
      `python-version`)
- [x] Paper-grounded algorithm layer — implemented 2026-08-28 [ADR-0013].
      Li (2024) *Gaussian Posterior Selection on Noncompact Fibres with
      Uniformly Separated Roots*, Theorem 1, is now mapped onto the
      algorithm layer: the paper's three-estimate proof architecture
      (Lemma 2 sheet tube, Lemma 3 root cells, Lemma 4 complement
      suppression) is the structure the three algorithm abstractions
      already had. Cosine annealing is documented as the canonical
      implementation of paper Lemma 2's sheet-tube scaling **at the
      direction level only** — see `docs/audit/EPSILON_DIRECTION.md`; it
      is not claimed to reproduce the paper's evidence competition at the
      magnitude level. `CodimensionSheetScheduler` implements the
      sheet-vs-cell evidence balance in
      `_paper_evidence_balance` (positive `eps` powers, per the audit
      correction); `EvidenceScaleGapMetric` measures the resulting
      `selection_ratio`, which is a framework-internal heuristic and not
      a paper quantity; `ReInferenceRunner` optionally
      emits it per round via `ReInferenceConfig.selection_evaluator`.
      Ablation grid extended from 16 to **18 rows**.
- [x] Algorithm abstractions — implemented 2026-08-28 [ADR-0011]. The
      algorithm layer (scheduler, policy driver, merge operator,
      restart blender) is now abstract and optional: four `Protocol`s
      in `adaptive_reflow/algorithm/` with 2-4 implementations each,
      composed by the `ReInferenceRunner` outer framework. Cosine
      annealing is one option (`CosineAnnealScheduler`), no longer the
      framework. `tools/run_ablation.py` gained a mixed
      cosine-scheduler + `ConstantPolicyDriver` row that the old code
      could not express.
- [x] New scheduler families — implemented 2026-08-28 [ADR-0012]. Three
      new deterministic `SchedulerProtocol` implementations:
      `PolynomialScheduler` (power-law ramp, `p > 0`),
      `SigmoidScheduler` (logit curve with configurable steepness +
      midpoint), and `ConvergenceAdaptiveScheduler` (PID-lite
      feedback-driven shift on a base cosine — no-train, bounded in
      `[-shift_max, +shift_max]`). `SchedulerProtocol` extended with
      an optional `record_round_feedback(round_in_cycle, metrics)`
      hook (default no-op on the four pre-existing families and the
      two new trivial families). `ReInferenceRunner` wires feedback
      gated on `hasattr`. Ablation grid extended from 8 to **16 rows**
      (8 configs x 2 targets). `tools/run_ablation.py` gained
      `multi_round_polynomial_schedule_derived`,
      `multi_round_sigmoid_schedule_derived`,
      `multi_round_convergence_adaptive_schedule_derived`, and
      `multi_round_cosine_adaptive_driver`. ADR-0012 documents the
      literature survey of 11 candidate methods and the decisions
      (accept polynomial/sigmoid/convergence-adaptive; reject
      Karras EDM `sigma(t)` — needs score gradients; defer
      bandit/RL — breaks determinism; defer cyclical and step —
      subsumed by sigmoid or incompatible).
- [x] Cosine annealing drives memory fraction — implemented 2026-08-27
      [ADR-0010]. `memory_fraction_from_schedule` helper added in
      `adaptive_reflow/schedule/cosine.py`; `Frame.engine.run_round` now
      wires `schedule.n_cap` to `policy.beta_by_channel` per round when
      `FinalRestartPolicy.beta_from_schedule = True`. Empirical toy
      ablation recorded in `docs/ABLATION.md`: on `eight_gaussians` the
      cosine schedule cut final W2 by `0.2115` and lifted final coverage
      by `+0.250` vs the constant-`beta=0.5` baseline; on `two_moons`
      the constant-beta baseline tied cosine on coverage and was
      slightly tighter on W2.
- [x] Paper-grounded framework alignment — implemented 2026-08-28.
      Four paper quantities (`A_g`, `B_g`, `C_g`, `e_rho`) from
      Li (2024) Theorem 1 are formalized as framework contracts in
      `adaptive_reflow/contracts/paper_quantities.py`, with
      dedicated tests in
      `tests/test_contracts/test_paper_quantities.py`. The
      `PosteriorSelectionEvaluator` is renamed to
      `EvidenceScaleGapMetric` (the legacy name remains as a
      deprecated alias); the audit reason literal moves from
      `posterior_selection_evaluator:sheet_vs_cell_ratio` to
      `evidence_scale_gap:sheet_vs_cells_O_eps_1_vs_O_eps_2`.
      `docs/audit/EPSILON_DIRECTION.md` records the framework's
      round-direction vs the paper's `eps -> 0` asymptotic and the
      `CodimensionSheetScheduler` alignment flip. ADR-0013 and
      `docs/INSIGHTS.md` were restructured with explicit "what the
      paper does NOT claim" sections and the `selection_ratio` is
      reframed as a framework-internal heuristic, not a paper
      quantity.
      **Wiring status:** the four paper quantities are now consumed
      by `CodimensionSheetScheduler.profile_residual_fn` (ground
      truth for `_paper_evidence_balance`), by
      `AdaptivePolicyDriver.per_cell_coefficient_C` (normalisation
      constant), and by `ReInferenceRunner` (per-round diagnostic
      emission into `per_round_metrics[r]["paper_quantity_diagnostics"]`).
      `ReInferenceConfig.paper_quantities_provider` upgrades the
      scheduler / driver in-place via
      `ReInferenceRunner._apply_paper_quantities_rewiring`; without
      the provider the legacy inline formula is used (regression
      coverage in `tests/test_algorithm/test_legacy_fallback.py`).
      The ablation (`tools/run_ablation.py`) records the
      round-by-round diagnostics; see `docs/ABLATION.md`
      §"paper_quantities as algorithm input" for the table and the
      non-triviality check.
- [x] Close 3 identified gaps — implemented 2026-08-28. Phase 1
      wires paper quantities into the algorithm layer (above);
      Phase 2 introduces `docs/CLAIMS.md` + `tools/check_claims_consistency.py`
      to enforce cross-doc claim consistency (16 ACTIVE / 0
      PROVISIONAL / 2 DEPRECATED, no drift on the latest run);
      Phase 3 removes the "S-tier" / "A+ library" /
      "production-ready" framing from `README.md`, `CHANGELOG.md`,
      `ROADMAP.md`, and `FINAL_STATUS.md` (which is annotated as
      a stale snapshot, not a live status). All six gates green:
      pytest 1235 passed / 7 skipped, ruff 0, mypy 0, docs scanner
      2251, claims sync clean, mkdocs `--strict` clean.
- [x] Ecosystem extensions — implemented 2026-08-29. Four
      reader-facing additions that close the P1-2 / P1-4 external
      recommendations: `SequentialScheduler` reference doc
      ([`docs/sequential-protocol.md`](docs/sequential-protocol.md))
      with a worked three-phase example (cosine for 8 rounds,
      exponential for 4, constant for 8); the
      [`docs/defaults-matrix.md`](docs/defaults-matrix.md) heuristic
      guide with a `(scheduler, driver, merge, blender)` row for
      each of the four common scenarios; extended
      [`docs/schedule-theory.md`](docs/schedule-theory.md) with a
      closed-form expressions table for all eight schedulers, a
      "comparison to field standards" table (Nichol-Dhariwal cosine,
      Karras EDM rho-spacing, SD3 exponential shift), and a "How to
      choose a schedule" decision tree; and three new CLM IDs
      ([CLM-019], [CLM-020], [CLM-021]) for the canonical
      `SchedulerProtocol`, `BoundedMergeOperator` floor semantics,
      and `SequentialScheduler` analogy respectively.
- [x] Final polish pass — implemented 2026-08-29. P1 / P2 cleanup
      (8 concrete items), ablation extended to 22 rows (4 new
      rows exercise forward-noise, clip-and-audit, hash-chained
      ledger, and identity merge paths), ecosystem documentation
      extended with `SequentialScheduler` worked examples, a
      defaults recommendation matrix, and an extended schedule
      theory reference (closed-form table + field-standards
      comparison + decision tree). All six gates green: pytest
      1403 passed / 7 skipped, ruff 0, mypy 0, docs scanner 2461,
      claims sync clean (19 active / 0 provisional / 2 deprecated,
      no drift), mkdocs `--strict` clean.

## Next (2026-Q4 — October through December)

- [ ] Add a non-molecular `RestartMixer` (`ToyGaussianMixer`) so the
      universal Protocol surface is exercised by two independent adapters
      by 2026-10-15
- [ ] Promote the nightly `mutmut` score for `contracts/` to ≥ 90% killed
      (already met on Linux baseline; close out the Windows backlog) by
      2026-10-31
- [ ] Add a fourth hostile-case fixture (DTB-R0 §3 case 6 — proxy-only
      evidence) to `tests/test_adversarial/` by 2026-11-15 [ADR-0005]
- [ ] Land docs/adr/0007 (legacy/ removal schedule) once the legacy
      quarantine empties by 2026-12-01

## Later (2027 — aspirational, no commitment)

- [ ] Cross-family adapter: a discrete CTMC FM adapter that satisfies the
      same universal Protocol surface [ADR-0003]
- [ ] Reader-facing tutorial notebook (`docs/tutorial/`) covering the
      eight-method `FlowMatchingODEAdapter` recipe end-to-end
- [ ] Public-API freeze: tag `v1.0.0` only when `contracts/` and
      `universal/` mutation scores both clear ≥ 90% killed on two
      consecutive nightly runs
- [ ] External auditor handoff: publish a `docs/audit/` dossier mapping
      every DTB-R7 / DTB-R8 gate to the public symbol that implements it

---

Quarter boundaries are the calendar quarter that contains the target date.
Items roll forward if they slip; nothing here is silently removed. When an
item closes, its line is deleted (not struck through) and the closure is
recorded in `CHANGELOG.md`.