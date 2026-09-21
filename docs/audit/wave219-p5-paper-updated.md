# Wave 219 P5 — Paper §3.3 + cover letter reproducibility note — BLOCKED

**Date:** 2026-09-21 (UTC)
**Beat:** Wave 219 P5 (intended: update paper §3.3 R2 row + add cover-letter
reproducibility note + finalize standardized stats table + clean
`/home/user/` paths + push)
**Authoring agent:** Wave 219 P5
**Status:** **BLOCKED — Wave 218 P3 N=1000 sweep still in flight**

## Headline

The Wave 219 P5 task spec ("update `docs/drafts/paper-flattened-draft.md`
§3.3 R2 row with verified framework numbers; add the cover-letter
reproducibility note pointing at the new commit hash; clean
`/home/user/` paths; confirm 35 unpushed commits safe + D.4
byte-stable + mkdocs build 0 warnings + claims_consistency ok; push")
**cannot be executed** at this time. The Wave 218 P3 (= Wave 219 P1)
N=1000 paired sweep has not completed.

## Why this task is blocked

### 1. Wave 218 P3 N=1000 sweep is still running

Per `docs/audit/wave219-p1-sweep-launched.md` and the Wave 219 P4
BLOCKED note (`docs/audit/wave219-p4-stats-clm.md`, commit `da14d9f`),
the two arms of the N=1000 paired sweep on the Wave 218 P1 fixed HEAD
(`1dcae06`) were launched at 2026-09-21 10:22 UTC / 10:23 UTC:

```
framework arm: PID 3170622 — sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py
baseline  arm: PID 3170774 — sweep_kanzi_n1000_paper_metrics.py
```

Current progress (read at 2026-09-21 02:35 UTC from per-arm
`checkpoint.json`):

```
framework arm:  37 / 1000 records (3.7%) — PID 3170622 alive, 12:51 elapsed
baseline  arm: 499 / 1000 records (49.9%) — PID 3170774 alive, 12:37 elapsed
```

Both PIDs confirmed alive (`ps -p 3170622 -p 3170774`). The framework
arm is the long pole (~21 s/record × 963 remaining ≈ ~5.6 h to
completion). The baseline arm is approximately half-done.

**No Wave 219 P2 postprocess has run, so no Wave 219 P3 verdict CSV
exists, and the Kanzi R2 framework mean cannot be confirmed to be
≈ 0.8798 Å yet.**

### 2. Per-task blockers (mapped to the user directive checklist)

| User checklist item | Status | Reason |
|---|---|---|
| Kanzi R2 framework mean ≈ 0.8798 Å confirmed | **DEFERRED** | Sweep not done; verdict CSV missing |
| R2 framework_wins confirmed → CLM-057 ACTIVE | **DEFERRED** | CLM-057 is already ACTIVE (Wave 214 P3); no flip needed, but the *confirmed-with-N=1000-numbers* status requires the new verdict |
| CLM-060 upgraded | **DEFERRED** | Depends on the new verdict numbers |
| Standardized stats table R2 row updated with framework_wins numbers | **DEFERRED** | The pre-existing R2 row already reports framework_wins with Wave 214 P2 source numbers (mean_diff=-0.02221, t=-5.094, df=999, p=3.49e-07, d_z=-0.1612); refresh-with-N=1000 numbers requires the new verdict |
| d_z, p_bonf consistent with paper | **DEFERRED** | Same — needs new verdict |
| Cover letter reproducibility note with new commit hash | **DEFERRED** | The reproduce-commit hash is `1dcae06` (Wave 218 P1 fixed HEAD — already where the sweep is running) — once Wave 219 P2/P3 produce the verdict CSV, we can finalize the byte-stable reproduce command. Note cannot be added until sweep completes |
| `/home/user/` → `<repo_root>/` batch replace + audit-trail integrity check | **DEFERRED** | Per user directive, this happens at the push-prep stage, which itself is downstream of the sweep verdict |
| 35 unpushed commits safety re-confirmation | **DEFERRED** | E4 scan was Wave 217 P1 (commit `b29eac7`, "32 commits + 23 untracked, SAFE TO PUSH"). Push is the final user step; a re-scan is appropriate then but not now |
| D.4 byte-stable 30/30 PASS | **VERIFIED** (already) | Last verified in Wave 219 P1 launch: `pytest tests/test_d4_regression_vectors.py -q --no-header` → 30 passed in 5.90s. No new code change since, so still PASS. Will re-verify at push-prep |
| mkdocs build 0 warnings | **DEFERRED** | Should be re-verified at push-prep; the last 0-warning build was Wave 215 P2 (`aa08051`, "fix mkdocs strict cross-ref warnings in cover-letter-tpami.md"). Wave 219 P5 cover-letter edit would invalidate the previous 0-warning state |
| claims_consistency ok | **DEFERRED** | Should be re-verified at push-prep |

### 3. The verbatim reproduce command is not yet writable

The user requested a cover-letter note of the form:

> All Kanzi framework_inv_proj results are reproducible from commit
> <Wave 219 P1 commit hash> via the following command:
> <verbatim reproduce command>
> Reviewers can git checkout this commit to verify byte-stable
> framework mean RMSD ≈ 0.8798 Å.

The commit hash we will write is `2b9e50a` (Wave 219 P1: "N=1000 paired
sweep launched on Wave 218 P1 fixed HEAD (PIDs 3170622 + 3170774)").
The reproduce command will be the framework-arm launch line from that
commit. **But the "framework mean RMSD ≈ 0.8798 Å" claim is not yet
verified at N=1000** — it is verified at N=10 (Wave 218 P2 commit
`1dcae06`, smoke test). Writing "≈ 0.8798 Å" to the cover letter before
N=1000 confirms it would be making a forward-looking promise. So this
note stays blank until Wave 219 P2 + P3 produce the N=1000 verdict.

## What needs to happen before this task is unblocked

1. **Wait** for both Wave 219 P1 sweep PIDs (3170622 + 3170774) to
   complete. Estimated wallclock remaining: ~5–6 h for the framework
   arm.
2. Wave 219 P2: run sweep postprocess (paired t-test, Cohen's d_z,
   Bonferroni correction) and produce
   `verification_outputs/wave219-p3-kanzi-r2-verdict.csv` (or
   equivalent).
3. Wave 219 P3: confirm the framework mean is ≈ 0.8798 Å to the
   expected precision. If yes → R2 framework_wins confirmed with the
   new numbers; if no → re-diagnose before any paper / cover-letter /
   push action.
4. Only then re-run this Wave 219 P5 task spec — and replace the
   contents of this audit doc with the actual paper-update log,
   cover-letter diff, `/home/user/` cleanup report, push prep
   checklist, and final JSON output.

## Existing pre-conditions that are already met (verified at this read)

- **HEAD = `2b9e50a`** — Wave 219 P1 N=1000 sweep launch.
- **D.4 byte-stable 30/30 PASS** — last verified 2026-09-21 in
  Wave 219 P1 launch (`docs/audit/wave219-p1-sweep-launched.md`).
  No code change since.
- **CLM-057 already ACTIVE** — Wave 214 P3 (commit `3c91d43`, "user-
  directed R2 verdict correction + CLM-057 PROVISIONAL removal").
- **CLM-060 R2 verdict already framework_wins** — Wave 214 P3 flip.
- **Standardized stats R2 row already reports framework_wins** with
  Wave 214 P2 source numbers — `docs/tables/wave204-p3-standardized-stats.md`
  (verified by Wave 219 P4 commit message `da14d9f`).
- **35 unpushed commits last safety-scanned SAFE TO PUSH** —
  Wave 217 P1 E4 scan (commit `b29eac7`).
- **mkdocs build last 0-warning** — Wave 215 P2 (commit `aa08051`).
- **claims_consistency last OK** — Wave 215 P3 (commit `4e72c6c`).

All of these would still need to be re-verified at push-prep, but no
remediation is anticipated.

## Reference files

- `docs/audit/wave219-p1-sweep-launched.md` — sweep launch details
- `docs/audit/wave219-p4-stats-clm.md` — Wave 219 P4 BLOCKED note
  (predecessor placeholder; same blocker, same PIDs)
- `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` —
  framework arm (PID 3170622)
- `tools/sweep_kanzi_n1000_paper_metrics.py` — baseline arm (PID 3170774)
- `verification_outputs/wave219-p1-kanzi-framework-n1000/checkpoint.json`
- `verification_outputs/wave219-p1-kanzi-baseline-n1000/checkpoint.json`
- `docs/tables/wave204-p3-standardized-stats.md` — existing R2 row
  (already framework_wins)