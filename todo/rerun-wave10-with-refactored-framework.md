# Re-run Wave 10 with refactored framework (JMAA theory applied to protein)

**Status:** done (Wave 19 P1A2 — commit a37476b; verdict=not_supported; decision metric saturated 1.0000 vs 1.0000 (decision tied at ceiling); G-MASTER-PHASE-4 block rule triggered → PHASE-4 blocked, back to PHASE-1)
**Depends on:** Wave 11 (JMAA refactor) shipped + Wave 10 initial result recorded
**Owner:** framework maintainer
**Goal:** validate the user's claim that "framework has theory; if integration
doesn't improve, must be implementation wrong" by re-running the LineageFlow
baseline-vs-framework comparison against the **refactored** framework.

## Background

The user diagnosed that previous negative results (Wave 8 FIX-3: framework WORSE
on 2D RF post-cd70821) might be due to the theory being lost in adapter code
during changes. Wave 11 lifts the theory back into framework core. If the theory
was the missing piece, re-running Wave 10 should show framework improvement on
protein.

## Next action (when starting)

1. Verify Wave 11 refactor is committed.
2. Re-run `tools/experiments/run_lineageflow_comparison.py` (the Wave 10 comparison
   script) against the refactored framework — expect framework_improves_baseline=True
   this time, with positive delta_pct on family validity + log-likelihood.
3. If framework improves: update `docs/CONSOLIDATED_RESULTS.md` §6.3 with both
   pre-refactor and post-refactor numbers; add CLM-048 ("framework lift to
   protein after theory refactor") to `docs/CLAIMS.md`.
4. If framework still regresses: revert the refactor and reframe the claim.

## Acceptance

- New comparison.md in `/tmp/wave10_lineageflow/refactor_retry/` (or similar).
- Two-arm table in `docs/CONSOLIDATED_RESULTS.md` showing before/after refactor.
- A clear yes/no on whether the refactor improves the framework's value on
  protein.

## Acceptance gate (BINDING — see `todo/GATES.md`)

**Gate name:** `G-MASTER-PHASE-4` (per-model component) for LineageFlow re-run

**Pre-condition:** `G-MASTER-PHASE-1` passed (Wave 11 done) + `G-MASTER-PHASE-3`
passed for LineageFlow (already true)

**Pass conditions (ALL must hold):**
- [ ] `comparison.md` in `/tmp/wave10_lineageflow/refactor_retry/` exists
- [ ] Two-arm table in `docs/CONSOLIDATED_RESULTS.md` (or new file
      `docs/PHASE-4-RESULTS/lineageflow.md`) shows pre-refactor AND post-refactor
      numbers
- [ ] PHASE-4 acceptance metric table is updated with the new result
- [ ] `todo/models/lineageflow.md` §F (empirical record) is updated
- [ ] If verdict = supported: row added to `docs/CONSOLIDATED_RESULTS.md` §7+
- [ ] If verdict = not_supported: **STOP and return to Phase 1-3** (per
      `G-MASTER-PHASE-4` block rule)

**Verification commands:**
```bash
cd /home/hugo/codes/flowa-multistep-reinference
test -f /tmp/wave10_lineageflow/refactor_retry/comparison.md
grep -q "LineageFlow" docs/CONSOLIDATED_RESULTS.md
grep -q "post-refactor\|refactor_retry" todo/models/lineageflow.md
.venvs/flowmol3_venv/bin/mkdocs build --strict 2>&1 | tail -3
```

**Block rule:** if verdict = not_supported, **the entire Phase 4 is blocked**
(per the user "如果...实现做错了" hypothesis). Back to Phase 1.

## Out of scope

- Doing this on more than LineageFlow. Repeat for other Wave 9 candidates
  (Flowception, MM-FM, FreqFlow) only if the LineageFlow re-run shows clear
  framework improvement.