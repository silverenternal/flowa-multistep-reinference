# `todo/inprogress/` — Active plans only

**Date:** 2026-09-08

This folder holds plans for waves currently in flight. Anything archived
(closed-but-still-cited, strategy exploration superseded by later decisions,
or historical problem-review docs) lives in `../completed/`.

## What's here

| File | Status | What it does |
|---|---|---|
| [wave75-flowmol3-paper-repro.md](wave75-flowmol3-paper-repro.md) | **IN FLIGHT** (workflow `w9sveok4w`) | FlowMol3 paper-metric reproduction via upstream `SampleAnalyzer.analyze` (vendored at `data/FlowMol3/repo/`) |
| [wave75-78-master-plan.md](wave75-78-master-plan.md) | **IN FLIGHT** (Wave 75 active; 76/77/78 cascade) | Cascade plan for Tier 3 paper-metric reproduction across Kanzi / LineageFlow / FlowMol3 |

## Decision evolution (why some plans moved to `completed/`)

These plans were in `inprogress/` until the 2026-09-08 archive sweep and
were moved here because their content is now **historical** rather than
**active**:

| Archived plan | Why it moved |
|---|---|
| `PHASE-4-model-integration-iteration.md` | Kanzi + LineageFlow + FlowMol3 close-outs landed in Wave 47-74. FreqFlow + MM-FM deferred indefinitely (no upstream ckpt). Future model additions (if any) will get a fresh plan file. |
| `wave43-problems-review.md` | All 6 problems were closed by Wave 45-52 work. Retained as historical traceability only. |
| `wave45-adapter-fix-master-plan.md` | Wave 47-52 LineageFlow glue + Wave 52 Kanzi composite + Wave 53 FlowMol3 metric layer closed every item. |
| `wave58-nfe-adaptive-plan.md` | Wave 58 implementation landed (NFE-adaptive gate + 6-point Kanzi NFE scan + paper §7.9). Plan doc retained for traceability. |
| `two-paper-algo-design.md` | Strategic exploration that has been **superseded** by the single-paper framing (see Wave 78 caveat update). |
| `two-paper-strategy.md` | Same as above — design exploration; current framing is single-paper: **framework SOTA at inference time on frozen ckpt**, toy evidence (mechanism) + chemistry evidence (sanity check). |

## When to add to `inprogress/`

Add a new plan here only when:
1. It corresponds to a wave that has been launched but not yet completed
2. OR it's a master plan that orchestrates multiple in-flight waves

Move to `../completed/` once the wave lands (commit on disk + final
audit doc authored). The trigger is **wave lands**, not **wave plan
fully consumed**.
