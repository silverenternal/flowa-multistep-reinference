# Algorithm improvement — ML-aware mutation score (F.6)

**Status:** done (Wave 18 F.6 — first Q4 2026 audit complete; commit 6ec3385; tools/run_mutation_audit.py + docs/mutation_audit_q4_2026.md; theory subsystem 0.500 ≥ 0.4) (+ Wave 25 F.6 subsystem survivors + Wave 38 --apply-survivor flag; no new quarterly audit scheduled in Wave 41-54; framework remains at 0.833 score)
**Date:** 2026-09-05
**Priority:** medium (per rev 2 §1 F.6 = 0%; test discrimination power
unknown — we don't know if our tests can catch real bugs)
**Depends on:** Wave 16 Algo D completed (for algorithm-code coverage)
**Owner:** framework maintainer
**Goal:** Quarterly audit using DL-specific mutation operators against
theory checkers + integrators + schedulers + adapters. Mutation score
= killed mutants / total mutants; per-subsystem scores reported.

## Background

Framework-internal-metrics rev 2 §1 F.6:
> ML-aware mutation score (MuNN/DeepMutation operators, quarterly):
> scope = theory checkers + integrators + schedulers + adapters (one
> representative per family); report per-subsystem scores so
> theory-checker score doesn't mask algorithmic gaps.
> Current: none; Target: ≥ 0.6 aggregate AND ≥ 0.4 per-subsystem by Wave 18.

Per Research 3: mutation score measures test discrimination power
directly. Without it, a test suite can score 100% on coverage while
missing real fault classes.

Per Research 1 pitfall: full mutation testing per-PR is prohibitively
expensive. Quarterly cadence is the right level.

## Scope

### Subsystems to mutate (target list)

- **Theory checkers**: `adaptive_reflow/theory/checkers.py`,
  `paper_quantities.py`, `lemma2_checker.py`, `validation.py`
- **Integrators**: `adaptive_reflow/algorithm/integrators.py` (or
  wherever FM integrators live)
- **Schedulers**: `adaptive_reflow/algorithm/scheduler/_core.py`
- **Adapters** (one representative per family):
  - FlowMol3 (chemistry)
  - Self-Flow (image FM)
  - LineageFlow (protein)
  - twodim_fm (toy)

## Tasks

1. **Install mutation testing tool** (recommend `mutmut` for Python;
   or `cosmic-ray` for richer reports)
2. **Define ML-aware mutation operators**:
   - Weight perturbation (Gaussian noise on constants)
   - Activation swap (relu → tanh etc.)
   - Structural mutation (remove conditional branch)
   - Threshold flip (> vs >=)
   - Constant substitution (e.g., 1.0 → 1.1)
3. **Run quarterly mutation audit** (Q4 2026 target)
4. **Generate per-subsystem report** in
   `docs/mutation_audit_<quarter>.md`
6. **Track per-subsystem scores**; require ≥ 0.4 per subsystem and ≥
   0.6 aggregate

## Files affected

- `tools/run_mutation_audit.py` (NEW; runner script)
- `pyproject.toml` (UPDATE; add `mutmut` as dev dep)
- `docs/mutation_audit_q4_2026.md` (NEW; first quarterly report)
- `framework-internal-metrics.md` §1 F.6 (UPDATE)

## Acceptance

- [ ] Mutation runner script exists + reproducible
- [ ] First quarterly audit completed (Q4 2026)
- [ ] Per-subsystem mutation score ≥ 0.4
- [ ] Aggregate mutation score ≥ 0.6
- [ ] Report published in `docs/mutation_audit_<quarter>.md`
- [ ] `docs/baseline-audit-report.md` §F.6 updated to "MET"
- [ ] Commit + push

## Estimated time

- Setup: 2-4 hours
- First audit run: 8-24 hours compute (full mutation sweep is expensive)
- Report writing: 1-2 hours

## Acceptance gate

**Gate name:** `G-F6-MUTATION-AUDIT` (new, quarterly)

**Pre-condition:** Wave 16 Algo D completed (for algorithm-code coverage)
**Pass conditions:**
- [ ] All acceptance checklist items
- [ ] First quarterly audit published

## Pitfall (per Research 3)

Mutation score on ML models is sensitive to the choice of mutation
operators and killing criterion; without a standardised operator set
the number is not comparable across systems and can be pushed up by
trivially distinguishable mutants. Mitigation: use a fixed operator
set per quarter; report raw score + per-operator breakdown.

## Out of scope

- Mutation testing per PR (prohibitively expensive; quarterly only)
- Mutation testing on adapter-specific code beyond one representative
  per family

## Wave 56 close-out

Status refreshed: F.6 mutation testing remains at 0.833 (theory subsystem 0.500 ≥ 0.4). Wave 25 added SM/TF subsystem survivor tests; Wave 38 added --apply-survivor flag. No new quarterly audit required in Wave 41-54 (the framework is otherwise occupied with composite eval and paper finalization). Last touched commit: `811ca75` (Wave 55 Agent C: Author todo/INDEX.md master entry point).

## Related

- `framework-internal-metrics.md` §1 F.6 (defines the metric)