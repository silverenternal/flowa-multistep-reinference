# Algorithm improvement C — uplift isolation test suite

**Status:** done (Wave 14/15 rescue — commit a1f8650; 37 tests in tests/test_algo_uplifts/test_uplifts.py) (+ Wave 41 Agent C: circular import fix in test_algo_uplifts; Wave 47: composite metric smoke tests added)
**Priority:** medium
**Depends on:** `docs/benchmark-uplifts.md` inventory complete
**Owner:** framework maintainer
**Goal:** for each of the 36 measured algorithm uplifts, add an
independent toggle test that verifies the uplift is real (not noise)
and quantifies its isolated contribution. Identifies the top-10
strongest uplifts and produces a clean ablation table.

## Background

The framework's `docs/benchmark-uplifts.md` lists 36 measured algorithm
uplifts (BEFORE/AFTER metric deltas). These are the framework's
algorithm-layer value claim — each is a piece of evidence that the
typed-contracts framework improves over a naïve baseline.

However, the table is **aggregate**: it reports the cumulative effect
of all uplifts on, e.g., `selection_ratio`. It does NOT isolate each
uplift's individual contribution. A reviewer (or future framework
maintainer) cannot tell from the table:

1. Which uplifts are the strongest contributors?
2. Are there pairwise interactions (synergistic or antagonistic)?
3. Are any uplifts redundant (i.e., contribute nothing once another is
   enabled)?

This task produces the isolation test suite + a clean ablation table
that answers all three questions.

## Method

For each uplift U in `docs/benchmark-uplifts.md`:

1. Find the flag/env-var/option that toggles U in code (most are in
   `adaptive_reflow/algorithm/dynamic_noise_bias.py` or scheduler
   modules).
2. Write a test that:
   - Default: U enabled, run baseline metric `M_off`.
   - Toggle U off via the flag, run metric `M_off`.
   - Assert `|M_on - M_off| > 3 * MC_noise` (real effect, not noise).
3. Report the ratio `delta = (M_on - M_off) / M_off` to a new
   `docs/ABLATION.md` v2 table.

After all 36 isolated tests:

- Sort by absolute `delta` desc → top-10 are "strongest".
- Run 2-uplift interaction sweep on the top-5 → detect synergy /
  antagonism.
- Run full-on vs full-off → cumulative effect.

## Files affected (estimated)

- `tests/test_algo_uplifts/` (new directory) — 36 test files
  (or 1 parametrized test with 36 ids).
- `docs/ABLATION.md` (existing, 173 lines) — version 2 with
  isolation table + interaction table + cumulative table.
- `docs/benchmark-uplifts.md` (existing) — link to ABLATION.md v2.

## Acceptance

- [ ] `tests/test_algo_uplifts/` exists with >= 36 tests, all passing.
- [ ] `docs/ABLATION.md` v2 has the three tables (isolation +
  interaction + cumulative).
- [ ] Top-10 strongest uplifts identified + ranked.
- [ ] pytest passes (existing 3228 + new 36 = 3264).
- [ ] mkdocs --strict exit 0.
- [ ] Commit + push.

## Estimated time

1-2 hours (no GPU; pure test writing + table generation).

## Acceptance gate

**Gate name:** `G-ALGO-UPLIFT-ISOLATION` (new; defined here)

**Pre-condition:** `docs/benchmark-uplifts.md` has 36 entries
**Pass conditions:**
- [ ] Acceptance checklist above all met
- [ ] `todo/STATUS.md` updated

## Scope limits

- Test only uplifts that have a clean toggle (some uplifts may be
  entangled in code paths that can't be cleanly disabled).
- For uplifts that can't be cleanly toggled: document the entanglement
  + append to `todo/lessons-learned.md` as LL-NNN.
- Pairwise interaction sweep is on the top-5 only, not the full
  C(36, 2) = 630 pairs.

## Out of scope

- Re-measuring uplifts on different base models (that's a Phase 4
  task).
- Adding NEW uplifts (this task characterises what exists).

## Wave 56 close-out

Status refreshed: 37-uplift isolation test suite (Wave 14/15 rescue) is now the canonical per-uplift characterisation layer. Wave 41 circular-import fix (Agent C) unblocked test_algo_uplifts collection; Wave 47 composite metric smoke tests added on top. Wave 52 ablation matrix tests individual uplift combinations. Last touched commit: `811ca75` (Wave 55 Agent C: Author todo/INDEX.md master entry point).