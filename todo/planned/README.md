# `todo/planned/` — Plans ready to execute (waiting for user go-ahead)

**Date:** 2026-09-13 (status reconciliation)
**Purpose:** This folder holds plans for the **next 4 一区 reviewer weaknesses** to close + ICLR 2027 submission package. Each plan is **sequential (1 agent per wave, not 25-agent parallel ultracode)**, with single commit + audit doc per wave. No workflow launches until user approves.

## Why this folder exists (2026-09-09)

User feedback: "之前的workflow设计的太长了，我们还是先在todo文件夹里按照目录设计做好详细规划好了"

Translation: Previous workflows (100-step ultracode) were too long. Switch to: **detailed plans in `todo/` first, then small sequential waves** instead of launching big workflows.

## What's here (4 plans + 1 master)

| File | Wave | Closes | Wall-clock | Status |
|---|---|---|---|---|
| [tier3-final-close-master-plan.md](tier3-final-close-master-plan.md) | 91-94 cascade | (overview) | 11-19h | HISTORICAL / PARTIAL |
| [w2-kanzi-latent-coord-bridge.md](w2-kanzi-latent-coord-bridge.md) | Wave 91 | W2 (Kanzi framework NOT_MEASURABLE) | 3-5h | DONE |
| [w3-n5000-paper-metric-sweep.md](w3-n5000-paper-metric-sweep.md) | Wave 92 | W3 (N=1000 too small) | 4-8h | PLANNED (OPT-IN) |
| [w4-statistical-power-analysis.md](w4-statistical-power-analysis.md) | Wave 93 | W4 (2/12 framework_improves) | 2-3h | DONE |
| [w5-iclr2027-submission-package.md](w5-iclr2027-submission-package.md) | Wave 94 | (final ship) | 2-3h | DEFERRED / RESOURCE-GATED |

## Reading order for user approval

1. Read **tier3-final-close-master-plan.md** (overview)
2. Read **w2-kanzi-latent-coord-bridge.md** (next to execute)
3. Decide: Wave 92 (N=5000) is opt-in; say yes or skip
4. Read **w4-statistical-power-analysis.md** (depends on Wave 91; Wave 92 optional)
5. Read **w5-iclr2027-submission-package.md** (final ship; depends on W91 + W93)

## Differences from previous Wave 86-89 / Wave 90 ultracode workflows

| Old (Wave 86-89, 90) | New (Wave 91-94 plans) |
|---|---|
| 100 steps / 25 agents per wave | 4-6 phases / 1 agent per wave |
| Multiple parallel agents | Single sequential agent |
| Often hits API 529 (server overload) | Bounded wall-clock, low failure mode |
| Multi-commit per wave | Single commit per wave |
| Hard to recover from partial failure | Easy to checkpoint / pause |

## Activation

When user says "开始 Wave 91" or "go" or similar, I will:
1. Run Wave 91 sequentially (one agent, 5 phases, ~3-5h)
2. Stop at end of Wave 91, report results, ask "continue to Wave 92?"
3. Etc.

No automatic chain. User decides when to advance.

## Decision evolution

- **2026-09-09**: Created this folder + 5 plans after user feedback about workflow length
- Earlier waves (75-90) used large ultracode workflows — that's archived in `docs/audit/wave75-phase1-audit.md` through `docs/audit/wave96-xtb-verification.md`

## Cross-references

- `todo/STATUS.md` — current state (auto-updated per wave)
- `todo/INDEX.md` — master entry point
- `todo/inprogress/` — currently in-flight waves
- `todo/pending/` — queued but not started
- `todo/completed/` — closed waves
