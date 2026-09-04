# Algorithm improvement — F.2: flip NOT_REPRODUCED to REPRODUCED

**Status:** done (Wave 15 F — commit e397528; F.2: 4/8 → 7/8 REPRODUCED; Python 3.11 sidecar installed for FlowMol3 §1.1.d)
**Date:** 2026-09-05
**Priority:** medium (paper-writeup gate requires ≥ 6/8 REPRODUCED;
currently 4/8)
**Depends on:** F.5 env_hash infrastructure (separate task; HARD gate
blocker)
**Owner:** framework maintainer
**Goal:** flip 2 of 3 NOT_REPRODUCED rows from Wave 6 reproducibility
audit to REPRODUCED via cold-clone discipline + per-experiment env_hash
capture.

## Background

Wave 14 baseline audit §F.2:
- **REPRODUCED**: R1, R4, R7, R8 (4 / 8)
- **PARTIAL**: R2 (1 / 8)
- **NOT_REPRODUCED**: R3, R5, R6 (3 / 8)
- All 8 classified

Rev 2 §3 paper-writeup gate: `F.2 >= 6/8 REPRODUCED + all 8 classified`.
Currently 4/8 → need +2 REPRODUCED.

## What's NOT_REPRODUCED (per baseline audit)

- **R3**: W2-magnitude discrepancy (timeout / wall-clock issue)
- **R5**: FlowMol3 §1.1.d (Python 3.11 sidecar missing `dgl==2.1.0`)
- **R6**: 990 MB Score-SDE checkpoint not sandbox-reachable

## What's PARTIAL

- **R2**: `docs/ABLATION.md` not regenerated on current HEAD → table
  shows stale numbers

## What to do

1. **R5 — install Python 3.11 sidecar** with `dgl==2.1.0` and
   `torch==2.2.1+cpu`
   - `uv venv --python 3.11 /home/hugo/.venv-flowmol311`
   - Install pinned deps for FlowMol3
   - Re-run FlowMol3 §1.1.d head experiment
   - Capture env_hash + result (per F.5 protocol — requires F.5 task)
2. **R6 — provide sandbox-reachable mirror** for 990 MB Score-SDE
   checkpoint
   - Try HuggingFace tarball approach
   - Or use `download.pytorch.org` pattern
   - Re-run Score-SDE head experiment
   - Capture env_hash + result
3. **R3 — investigate W2-magnitude discrepancy**
   - Only after R5 + R6 are done
   - Bump timeout ≥ 2000s
   - Re-run
   - Capture env_hash + result
4. **R2 (PARTIAL → REPRODUCED)** — regenerate `docs/ABLATION.md` from
   current HEAD
   - Either manually regenerate (run framework + capture metrics)
   - Or add a regenerate-on-build hook (mkdocs plugin)
5. **Capture env_hash for each re-run** (per F.5 protocol)

## Files affected

- `docs/reproducibility_record.md` (UPDATE; per-experiment status)
- `docs/baseline-audit-report.md` §F.2 (UPDATE; re-audit)
- New sidecar: `/home/hugo/.venv-flowmol311` (NEW; gitignored)
- `docs/ABLATION.md` (UPDATE; regenerate)
- HuggingFace mirror config or download script (NEW; for R6)

## Acceptance

- [ ] F.2 = 6/8 REPRODUCED + R2 = REPRODUCED (7/8 total)
- [ ] env_hash captured for each re-run (per F.5)
- [ ] `docs/reproducibility_record.md` updated
- [ ] `docs/baseline-audit-report.md` §F.2 updated
- [ ] Commit + push

## Estimated time

- R5: 1-2 hours (sidecar install + head re-run)
- R6: 30-60 min (mirror + head re-run)
- R3: 30-60 min (after R5+R6)
- R2: 15-30 min (ABLATION regenerate)

Total: ~3-5 hours (CPU mostly; R5 + R6 might need small GPU).

## Acceptance gate

**Gate name:** `G-F2-REPRODUCTION` (new; defined here)

**Pre-condition:** F.5 env_hash infrastructure shipped (separate task)
**Pass conditions:**
- [ ] All acceptance checklist items
- [ ] `docs/baseline-audit-report.md` §F.2 updated to "6/8 REPRODUCED"

## Out of scope

- F.5 env_hash (separate; HARD gate blocker)
- LineageFlow real-ckpt verdict (separate; depends on D-004)
- Algorithm improvement B/C/D