# Wave 219 P4 — Standardized stats R2 row + CLM-057/CLM-060 update — BLOCKED

**Date:** 2026-09-21 (UTC)
**Beat:** Wave 219 P4 (intended: update `docs/tables/wave204-p3-standardized-stats.md` R2 row + flip CLM-057 to ACTIVE + upgrade CLM-060 R2 verdict)
**Authoring agent:** Wave 219 P4
**Status:** **BLOCKED — prerequisite P3 verdict CSV does not exist**

## Headline

The Wave 219 P4 task as specified ("Read
`verification_outputs/wave219-p3-kanzi-r2-verdict.csv` and use the new
numbers to update the standardized stats table R2 row + CLM-057/CLM-060")
**cannot be executed** at this time. The Wave 219 P3 verdict CSV does
not exist because the Wave 219 P2 (sweep completion + paired t-test)
has not run — both Wave 219 P1 sweep arms are still in flight.

## Why this task is blocked

### 1. Wave 219 P1 sweep is still running

Per `docs/audit/wave219-p1-sweep-launched.md`, the two arms of the N=1000
paired sweep on Wave 218 P1 fixed HEAD were launched on
2026-09-21 10:22 UTC / 10:23 UTC (PIDs 3170622 + 3170774). The launch
audit estimated ~12 h wallclock for the framework arm (long pole).

Current progress (read at 2026-09-21 02:33 UTC from the per-arm
`checkpoint.json`):

```
framework arm: 33 / 1000 records (3.3%) — PID 3170622 alive
baseline  arm: 459 / 1000 records (45.9%) — PID 3170774 alive
```

Both PIDs confirmed alive (`ps aux | grep`). The framework arm is the
long pole (≈44 s/record co-resident); the baseline arm is approximately
half-done. **No Wave 219 P2 postprocess has run, so no Wave 219 P3
verdict CSV exists.**

### 2. Wave 219 P3 verdict CSV does not exist

`find verification_outputs -name "wave219*" -type f` returns:

```
verification_outputs/wave219-p1-kanzi-framework-n1000/checkpoint.json
verification_outputs/wave219-p1-kanzi-baseline-n1000/checkpoint.json
docs/audit/wave219-p1-sweep-launched.md
```

The `wave219-p3-kanzi-r2-verdict.csv` artifact referenced in the task
spec is not on disk. It will be produced by Wave 219 P2 (sweep
completion + paired t-test postprocess) AFTER the framework arm of
Wave 219 P1 finishes.

### 3. The P3 sweep the user expected has been re-launched, not completed

The user request is framed as "after Wave 218 P3 N=1000 sweep completes":
the original Wave 218 P3 sweep was killed early (only 14 records on
disk at `verification_outputs/wave218-p3-kanzi-framework-n1000/
checkpoint.json`, no companion baseline). The Wave 219 P1 sweep is the
replacement N=1000 paired sweep on the Wave 218 P1 fixed code, and it
has not finished.

The P2 monitor script `/tmp/wave219-p2-monitor.sh` is running and polls
the checkpoint files every 5 min, but it will only emit the final
JSONs when both PIDs exit. The paired t-test postprocess (Wave 219 P2
output) and the verdict CSV (Wave 219 P3 output) follow the P2 monitor.

### 4. Pre-existing claim status — both CLM-057 and R2 are already in the target state

Even ignoring the missing P3 data, the two state transitions the task
asks me to perform are already in their target state from prior waves:

- **CLM-057 status:** already **ACTIVE** (PROVISIONAL flag was removed
  in Wave 214 P3, see `docs/audit/wave214-p3-clm057-update.md` and the
  Wave 214 P3 annotation on CLM-057 itself, line 2803 area). The
  `docs/CLAIMS.md` line 2663 header reads `- Status: ACTIVE`.
- **CLM-060 R2 verdict:** already **framework_wins / SUPPORTED** (Wave
  214 P3 flipped R2 from REGRESSES to SUPPORTED; see CLM-060 paragraph
  at line 3031–3046, "Wave 214 P3 UPDATE: the R2 cell is no longer
  REGRESSES… The R2 verdict is now SUPPORTED framework_wins").
- **`docs/tables/wave204-p3-standardized-stats.md` R2 row (line 38):**
  already reports framework_wins verdict with the current N=1000
  numbers (mean_diff = −0.02221, t = −5.094, p_raw = 3.49e-07,
  Cohen's d_z = −0.1612, source = `wave214-p2-kanzi-framework-inv-proj-n1000.csv`).

The only thing Wave 219 P4 was supposed to do that is NOT already in
the target state is **refresh the R2 row numbers from the new P3
paired t-test** — and that new t-test has not run.

## What I did NOT do (intentional, to avoid fabricating data)

1. **Did NOT update `docs/tables/wave204-p3-standardized-stats.md` R2
   row.** The current row already says framework_wins with the
   Wave 214 P2 source. Refreshing it with placeholder numbers from a
   sweep that has not finished would corrupt the audit-grade table.
2. **Did NOT change CLM-057 status in `docs/CLAIMS.md`.** It is
   already ACTIVE.
3. **Did NOT add a Wave 219 P4 annotation to CLM-060.** A "verify the
   already-flip verdict" annotation would be additive but
   meaningless (it would just restate what CLM-060 already says after
   Wave 214 P3). The honest annotation here is "Wave 219 P4 was
   BLOCKED — see `docs/audit/wave219-p4-stats-clm.md`" — which is what
   this file is.
4. **Did NOT commit anything.** No source-of-truth file changed.

## What Wave 219 P4 SHOULD do once the P3 verdict CSV is on disk

When Wave 219 P3 produces `verification_outputs/wave219-p3-kanzi-r2-verdict.csv`
(expected at ~2026-09-21 22:30 UTC + paired-t-test postprocess time ≈
2026-09-22 00:00 UTC), a re-run of Wave 219 P4 should:

1. Read the new CSV's `(framework_mean, baseline_mean, mean_diff,
   sd_diff, t, df, p_raw, CI95_low, CI95_high, d_z, bonf_sig)` cells.
2. Verify `framework_mean ≈ 0.8798 Å` (byte-stable Wave 127 reference).
   - If yes: R2 framework_wins CONFIRMED (R2 verdict stays
     framework_wins in the standardized stats table).
   - If no (framework_mean differs by > 0.01 Å): re-diagnose per the
     Wave 218 P1 + P2 fix-applied audit doc root cause analysis.
3. Update R2 row in `docs/tables/wave204-p3-standardized-stats.md`
   line 38 with the new numbers; update the `wave_source` column to
   reference `wave219-p3-kanzi-r2-verdict.csv` instead of
   `wave214-p2-kanzi-framework-inv-proj-n1000.csv`.
4. Add a Wave 219 P4 annotation to CLM-060 (R2 row) noting that the
   N=1000 paired t-test was re-run on Wave 218 P1 fixed HEAD and
   confirms the framework_wins verdict at the same byte-stable
   0.8798 Å framework reference. No CLM-057 status change needed
   (already ACTIVE).
5. Run `mkdocs build --strict` to confirm 0 warnings.
6. Commit with the Wave 219 P4 message.

## Pre-flight checklist for the future Wave 219 P4 re-run

- [ ] `verification_outputs/wave219-p3-kanzi-r2-verdict.csv` exists
- [ ] CSV reports `framework_mean ≈ 0.8798 Å` (within 1e-3)
- [ ] CSV reports `bonf_sig = True` at α = 0.007143
- [ ] CSV reports `d_z ≈ -0.16` (consistent with Wave 214 P2 d_z)
- [ ] D.4 byte-stable still PASS (re-run
      `pytest tests/test_d4_regression_vectors.py -q` in `lineageflow_venv`)
- [ ] No new audit-trail content drift (no `/home/user/` paths in any
      updated docs)

## Reference

- Wave 219 P1 audit doc: `docs/audit/wave219-p1-sweep-launched.md`
- Wave 218 P1 + P2 + P3 audits: `docs/audit/wave218-p1-fix-applied.md`,
  `docs/audit/wave218-p2-smoke.md`, `docs/audit/wave214-p3-clm057-update.md`
- Standardized stats table: `docs/tables/wave204-p3-standardized-stats.md`
- R2 verdict current state: framework_wins, mean_diff = −0.02221,
  t = −5.094, df = 999, p_raw = 3.49e-07, d_z = −0.1612
- CLM-057 current status: ACTIVE (Wave 214 P3)
- CLM-060 R2 current verdict: framework_wins (Wave 214 P3)
- Wave 219 P1 sweep PIDs: 3170622 (framework, 33/1000 records),
  3170774 (baseline, 459/1000 records)
- P2 monitor script: `/tmp/wave219-p2-monitor.sh` (running)