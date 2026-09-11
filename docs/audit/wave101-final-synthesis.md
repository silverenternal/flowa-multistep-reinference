# Wave 101 — Engineering-Hygiene Layered Review (Final Synthesis)

**Date:** 2026-09-11
**Status:** DONE (review-only). 4 audit docs + 4 fix plans committed (in working tree).

---

## Goal

Audit project engineering hygiene across 4 disjoint layers and write a **fix plan
per layer** to `todo/planned/`. No source code was modified in this wave; the
deliverables are read-only audits + execution plans.

Per user's request: "用ultracode分层review... 每个步骤都要有往todo目录加规划的动作".

---

## Deliverables (8 files)

| Layer | Review doc (docs/audit) | Fix plan (todo/planned) | Issues found | Net LOC delta plan |
|---|---|---|---|---|
| 1. adapters/ | `wave101-review-layer1-adapters.md` | `w101-fix-layer1-adapters.md` | 10 | -290 adapters, +35 common |
| 2. algorithm/ + tools/ | `wave101-review-layer2-algorithm-tools.md` | `w101-fix-layer2-algorithm-tools.md` | 9 | -7100 |
| 3. tests/ | `wave101-review-layer3-tests.md` | `w101-fix-layer3-tests.md` | 6 | -6500 (split + dedup) |
| 4. docs/ + config | `wave101-review-layer4-docs-config.md` | `w101-fix-layer4-docs-config.md` | 7 | +435 (additive only) |
| **Total** | | | **32** | **-13,420 LOC** |

---

## Top 5 cross-layer findings

1. **`scheduler/_core.py` is a 5227-LOC monolith** (Layer 2 Rank 1) — should split into `protocols.py` + `simple.py` + `adaptive.py` + `nfe_aware.py` with a slim re-export shim. Highest single leverage point.
2. **5 `_extra` / `_r2` companion files** (~3500 LOC, Layer 2 Rank 2) — should merge back into canonical modules. Already 30+ waves stable.
3. **3 SOTA `_load_torch_model` / `_load_torch_pipeline` / `_load_model` are 3 independent copies** (Layer 1 Rank 1) — should extract `load_real_weights(builder, stub_factory, compat_shim)` into `_adapter_common.py`.
4. **`_seed_from_ids` / `_digest_state` / `_make_ref` re-implemented verbatim in 5 adapters** (Layer 1 Rank 2) — should delete local copies + import from `_adapter_common.py`.
5. **`docs/audit/` has 290+ wave docs without curated INDEX** (Layer 4 Rank 1) — biggest discoverability gap.

---

## Execution order (per the user's "delete before extract, extract before split" directive)

The 4 fix plans follow a consistent P0 → P3 priority scheme. The recommended
inter-wave execution order is:

1. **Layer 4** (docs/config, ~2.5h, zero risk) — pure doc additions, no source change
2. **Layer 1** (adapters, ~3.5h) — small dedup first (P0), then trait extraction (P2-A last)
3. **Layer 3** (tests, ~6.5h) — pure file-system split + dedup
4. **Layer 2** (algorithm + tools, ~6.5h) — biggest structural change (`_core.py` 4-way split last)

Total wall-clock: ~19 hours across ~32 commits. Each commit is independently revertable.

---

## Constraints honored (per the user's "don't reinvent the wheel" + Wave 100 fix pattern)

1. **NO D.4 byte-stable vector changes** (preserved in all 4 fix plans).
2. **NO source code deletions** — only file-organization moves + dead-code removal where 30+ waves stable.
3. **NO new public exports** — new helpers are module-private (`_` prefix).
4. **NO behavior change** for any scheduler / adapter / runner / merge-operator.
5. **NO scope creep** — Layer 4 is docs/config only; Layer 3 is tests only; etc.

---

## How to apply the 4 plans

The user has been running small-wave patterns (1 commit per fix) since Wave 95.
Each fix in the 4 plans has:

* Estimated LOC delta
* Estimated wall-clock
* Per-fix acceptance criteria (grep / D.4 / capability audit / mkdocs)
* Risk level (zero / very-low / low / medium)

A reasonable next step is to launch **Wave 102 = Layer 4 first** (2.5h, zero
risk), then iterate Layer 1 / 3 / 2 in subsequent waves.

---

## What this wave does NOT do

1. Does NOT modify any source code in `adaptive_reflow/` or `tests/`.
2. Does NOT commit any of the 4 fix plans — they live in `todo/planned/` as
   **future execution guides**.
3. Does NOT modify `paper-draft.md` (still 5270 LOC; structure preserved).
4. Does NOT touch `requirements-lock.txt` (canonical lockfile).
5. Does NOT push any commits (user-gated push per Wave 11+).

---

## Author note

Wave 101 originally launched 4 parallel ultracode review agents. Only Layer-1
completed cleanly before the other 3 stalled (180-second agent timeout × 6
retries per agent). Layers 2/3/4 were authored manually with the same
5-dimension rubric and the same format as Layer-1 to preserve consistency.
All deliverables match the user's request: "每个步骤都要有往todo目录加规划的动作".

---

REVIEW COMPLETE — 32 issues across 4 layers, ~13.4k LOC reduction plan, 32 commits across 4 fix plans.

Co-Authored-By: Claude Code <noreply@anthropic.com>
