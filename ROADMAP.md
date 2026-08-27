# Roadmap

`flowa-multistep-reinference` is a single-maintainer research project. The
roadmap below tracks the items currently open in `todo.json` and the
planned governance work for the S-tier upgrade. Every entry is a one-line
imperative with a target date and an ADR ID where one applies.

The "Now / Next / Later" buckets are calendar quarters, not promises.
They are reviewed at every release tag and updated when an item closes.

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
- [x] Python 3.12 + `numpy<2.5` pin enforced across all declarative
      configs (`pyproject.toml` `requires-python` / ruff `target-version`
      / mypy `python_version`, and every `.github/workflows/*.yml`
      `python-version`)
- [x] Cosine annealing drives memory fraction — closed 2026-08-27
      [ADR-0010]. `memory_fraction_from_schedule` helper added in
      `adaptive_reflow/schedule/cosine.py`; `Frame.engine.run_round` now
      wires `schedule.n_cap` to `policy.beta_by_channel` per round when
      `FinalRestartPolicy.beta_from_schedule = True`. Empirical toy
      ablation recorded in `docs/ABLATION.md`: on `eight_gaussians` the
      cosine schedule cut final W2 by `0.2115` and lifted final coverage
      by `+0.250` vs the constant-`beta=0.5` baseline; on `two_moons`
      the constant-beta baseline tied cosine on coverage and was
      slightly tighter on W2.

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