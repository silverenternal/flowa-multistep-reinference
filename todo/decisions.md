# `todo/decisions.md` — decision log (append-only)

**Purpose:** record WHY choices were made. Future readers (or future-us) need
to know "why X not Y". Each entry: date, context, choice, rationale,
consequences.

---

## D-001 — 4-phase plan over single-wave "one big push"

**Date:** 2026-09-05
**Context:** Wave 10 LineageFlow integration partially failed (real forward
pass blocked on missing `core` source repo). Previous waves (1, 2, 3, 5, 6,
7, 8, 9) all took a "one wave at a time" approach with mixed results.
**Choice:** Adopt a 4-phase deployment plan (see `PHASE-1` through
`PHASE-4` in this directory): framework + theory → per-model analysis →
glue improvement → one-model-at-a-time integration.
**Rationale:** Wave 10's BLOCKED issue was preventable — a Phase 2
per-model analysis (with "is the upstream source accessible?" question) would
have caught the missing `core` source BEFORE we spent time on adapter
+ tests + comparison. The user explicitly said: "如果前面确保做的足够好的
话我们只要好好改胶水层就好了" — which maps to: if Phase 1-3 is solid,
Phase 4 is just glue. The 4-phase plan enforces that ordering.
**Consequences:** Phase 1 must complete before any Phase 4 work; any new
model integration follows Phase 2 → Phase 3 → Phase 4 sequencing. Per-model
analysis files in `todo/models/` capture the "is this model even
integrable?" question explicitly.

---

## D-002 — "any FM improves" claim: requires per-model acceptance metric table

**Date:** 2026-09-05
**Context:** Wave 10 LineageFlow comparison tied at family_validity=1.0
ceiling (synthetic shim ties; real-ckpt verdict OPEN). The headline claim
"any FM model, when integrated into our framework, improves" cannot be
validated on a saturated metric.
**Choice:** Define per-model "Acceptance metric table" (in
`PHASE-4-model-integration-iteration.md`) with primary metric, secondary
metric, improvement bar, saturation check. Per-model verdict rules:
- `supported`: primary metric Δ ≥ improvement bar (positive direction) AND
  not at saturation
- `partially_supported`: primary metric Δ = 0% (TIE) OR at saturation
- `not_supported`: primary metric Δ < 0% (regression)
- `blocked`: cannot run real forward pass (separate from supported/not)
**Rationale:** Without a quantified metric + bar, every integration is a
subjective "did the framework help?" question. The acceptance table makes
"framework improves" falsifiable per model, and the aggregate verdict
(supported count) determines whether the headline claim survives.
**Consequences:** Every Phase 4 wave must populate the acceptance table
BEFORE running the comparison (otherwise verdict is uncomputable). If
a model's primary metric saturates, the comparison is `partially_supported`
NOT `supported` even if the numbers look good.

---

## D-003 — `todo/` folder structure: per-task markdown alongside machine-readable JSON

**Date:** 2026-09-05
**Context:** `todo.json` is the machine-readable task index. Per-task
planning needs human-readable markdown files for: per-phase overview,
per-model analysis, decision log, lessons learned.
**Choice:** Create `todo/` folder with:
- `README.md` (index)
- `PHASE-1..4-*.md` (4 strategic phase overviews)
- `models/README.md` + `models/<model>.md` (per-model analysis unit)
- `STATUS.md` (single source of truth, auto-updated per wave)
- `lessons-learned.md` (cross-cutting patterns, append-only)
- `decisions.md` (decision log, append-only)
- per-task files (Wave 10/11, rerun, push, paper)
**Rationale:** `todo.json` is good for `tasks[]` arrays with structured
fields but bad for prose. Markdown is good for prose but bad for
machine queries. The two coexist: `todo.json` is the index, `todo/*.md`
holds the content.
**Consequences:** Each wave's verify agent should also update
`STATUS.md` and append to `lessons-learned.md` / `decisions.md` as
appropriate. The `add-more-2026-sota-models.md` per-task file is folded
into `PHASE-2-model-complexity-analysis.md` (its content is Phase 2 work).

---

## D-004 — Wave 10: do NOT re-run on synthetic shim only

**Date:** 2026-09-05
**Context:** Wave 10's adapter ships on a synthetic velocity field (since
upstream `core` source is unreachable). Wave 10's comparison ran
baseline-vs-framework on the synthetic shim, giving family_validity
1.0 vs 1.0 = TIE.
**Choice:** Do NOT re-run Wave 10 on the synthetic shim. Either:
- (a) unblock the real forward pass (find LineageFlow GitHub source)
- (b) re-classify LineageFlow as "design-only integration" and remove the
  adapter file
**Rationale:** A re-run on the synthetic shim produces no new signal
(LL-002). The user has not yet chosen (a) vs (b). The next action item
is to attempt (a) (find source on GitHub, or via arxiv code link, or via
author contact); if (a) fails, declare (b).
**Consequences:** LineageFlow remains a "design-only" integration until
real forward pass works. The framework's adapter file is still useful
for protocol surface + tests, even if real generation can't run.