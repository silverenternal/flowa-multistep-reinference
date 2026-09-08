# Wave 91-94 small workflow design

**Date:** 2026-09-09
**Purpose:** Document the small-workflow design (≤3 agents per workflow, ≤5 steps each)

> **Why this exists:** Previous workflows (100-step ultracode with 25 agents) failed twice (wf90-93 never persisted; wf86-89 hit API 529). User feedback 2026-09-09: "workflow 设计的太长了...防止出现上次步骤太多导致运行失败". Switch to: **many small workflows, each with 2-3 agents**.

---

## 1. Workflow inventory (5 small workflows, 12 total agents)

| # | Workflow script | Wave | Agents | Phases | Output |
|---|---|---|---|---|---|
| **WF-91a** | `/tmp/wf91a-kanzi-audit-bridge.js` | Wave 91 Phase 1-2 | 2 | 2 | 1 audit doc + 1 commit |
| **WF-91b** | `/tmp/wf91b-kanzi-wire-eval-paper.js` | Wave 91 Phase 3-5 | 3 | 3 | 1 commit + paper update |
| **WF-93** | `/tmp/wf93-statistical-power.js` | Wave 93 Phase 1-2 | 2 | 2 | 1 commit + §7.6 reframe |
| **WF-94** | `/tmp/wf94-iclr-package.js` | Wave 94 Phase 1-3 | 3 | 3 | 1 commit + submission package |

**Total: 10 agents across 4 workflows**

Wave 92 (N=5000 OPT-IN) **not yet designed** — depends on Wave 91 outcome + user decision.

---

## 2. Workflow design constraints

- **Max 3 agents per workflow** (down from 25)
- **Max 5 steps per phase** (down from 8-12)
- **Each phase has clear READ-ONLY/CREATE/MODIFY/COMMIT boundary**
- **Each workflow has 1-3 commits total** (down from 5-8)
- **Synchronous checkpoint between workflows** — user gets notified, can intervene
- **Wall-clock per workflow**: 30-90 min (down from 2-7h)
- **API 529 failure recovery**: any single agent failure → user can re-launch THAT workflow only

---

## 3. Per-workflow expected output

### WF-91a (Wave 91 Phase 1-2)
- Output 1: `docs/audit/wave91-phase1-audit.md` (READ-ONLY, no commit)
- Output 2: `tools/kanzi_latent_to_coord.py` (NEW, ~30-50 LOC)
- Output 3: `tests/test_tools/test_kanzi_latent_to_coord.py` (NEW, 4 tests)
- Output 4: `docs/audit/wave91-phase2-bridge.md` (NEW)
- Output 5: 1 commit `Wave 91 Phase 2: Kanzi latent→coord bridge...`

### WF-91b (Wave 91 Phase 3-5)
- Output 1: `tools/run_real_ckpt_eval.py` modified (1 new flag + 1 helper)
- Output 2: `tests/test_tools/test_run_real_ckpt_eval.py` modified (1 new test)
- Output 3: 1 commit `Wave 91 Phase 3: wire --kanzi-framework-paper-metrics...`
- Output 4: `verification_outputs/kanzi_n1000_framework_paper_metrics/per_metric.json`
- Output 5: `docs/audit/wave91-phase4-eval.md` (no commit)
- Output 6: `docs/paper-draft.md` §7.3 updated
- Output 7: `docs/audit/wave91-phase5-final.md` (NEW)
- Output 8: 1 commit `Wave 91: Kanzi latent→coord bridge + framework paper-metric — W2 closed`

### WF-93 (Wave 93)
- Output 1: `tools/statistical_power_analysis.py` (NEW, ~100 LOC)
- Output 2: `tests/test_tools/test_statistical_power_analysis.py` (NEW, 4 tests)
- Output 3: 1 commit `Wave 93 Phase 1: statistical power analysis tool...`
- Output 4: `verification_outputs/power_analysis/per_cell.csv`
- Output 5: `docs/paper-draft.md` §7.6 replaced
- Output 6: `docs/audit/wave93-phase2-final.md` (NEW)
- Output 7: 1 commit `Wave 93: statistical power analysis...`

### WF-94 (Wave 94)
- Output 1: `cover_letter.md` (NEW, top-level)
- Output 2: `docs/paper-draft.md` §1 abstract + §7.3-§7.6 + §5.7 + §8.5 updated
- Output 3: `supplementary.md` (NEW, top-level)
- Output 4: `submission_checklist.md` (NEW, top-level)
- Output 5: `docs/audit/wave94-phase3-final.md` (NEW)
- Output 6: 1 commit `Wave 94: ICLR 2027 submission package...`

---

## 4. Activation order

1. **WF-91a first** (already launched 2026-09-09, Task ID `wjqxqm12p`)
2. **WF-91b** after WF-91a completes (user check)
3. **WF-93** after WF-91b completes (depends on Wave 91 numbers)
4. **WF-94** after WF-93 completes (final ship)

Each step waits for user OK before advancing.

---

## 5. Failure recovery

If any agent fails with API 529:
- Re-launch **only the failed agent** via fresh workflow with same script
- Other agents' results preserved via journal cache
- No re-run of completed work

---

## 6. Differences from previous Wave 86-89 / Wave 90 ultracode workflows

| Old (ultracode, 25 agents) | New (small workflow, 2-3 agents) |
|---|---|
| 100 steps / 25 agents per wave | 2-3 agents per wave |
| Multiple parallel agents | Single sequential agent |
| Often hits API 529 | Bounded wall-clock per workflow |
| Multi-commit per wave | 1-3 commits per workflow |
| Hard to recover | Each workflow = checkpoint |
| 2-7h wall-clock per wave | 30-90 min per workflow |

---

## 7. Cross-references

- Master plan: `todo/planned/tier3-final-close-master-plan.md`
- Per-wave plans: `todo/planned/w{2,3,4,5}-*.md`
- Workflow scripts: `/tmp/wf9{1,3,4}-*.js`
- Status: `todo/STATUS.md` (updated per workflow completion)