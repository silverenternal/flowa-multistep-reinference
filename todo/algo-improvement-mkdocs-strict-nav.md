# Algorithm improvement — mkdocs --strict nav fix (Wave 32 audit gap)

**Status:** pending (NEW — Wave 32 audit gap; small fix)
**Date:** 2026-09-05
**Priority:** high (B.3 mkdocs --strict HARD gate at risk)
**Depends on:** none (purely mkdocs.yml configuration)
**Owner:** framework maintainer
**Wave:** Wave 33 (target)
**Goal:** add a `Models` section to `mkdocs.yml` `nav:` linking the 5
`docs/models/*.model_card.md` files + `capability_g1_analysis.md` +
`theory/DEVIATIONS.md`, restoring the B.3 mkdocs `--strict` HARD gate
that was claimed PASS at Wave 15 Phase 3 but currently aborts with 8
unnavmed files.

## Background

Per Wave 32 Agent A (`docs/audit/gap-audit.md` §4):
- `mkdocs build --strict` aborts with 1 warning per 2026-09-05 run
- 8 unnavmed files:
  - `docs/capability_g1_analysis.md` (Wave 28 Agent B output)
  - `docs/models/flowmol3.model_card.md` (F.4)
  - `docs/models/lineageflow.model_card.md` (F.4)
  - `docs/models/rectified_flow_cifar.model_card.md` (F.4)
  - `docs/models/self_flow.model_card.md` (F.4)
  - `docs/models/twodim_fm.model_card.md` (F.4)
  - `docs/theory/DEVIATIONS.md`

Per `framework-freeze-checklist.md` MUST-1 B.3:
> **B.3** mkdocs `--strict` pass | **AT RISK** (Wave 32 A finding) |
> `mkdocs build --strict` was reported PASS at Wave 15 Phase 3 but
> currently aborts with 8 unnavmed files

## Why this is a HARD gate risk

The B.3 HARD gate is part of MUST-1 G-FRAMEWORK-HEALTH. If B.3 fails,
the framework cannot be declared "frozen for model integration testing"
(per `framework-freeze-checklist.md` §MUST-1). This blocks all PHASE-4
work.

## What to do

### Phase A — Choose the fix approach

Two options per Wave 32 Agent A §4:

**Option (a): add `Models` nav section** (preferred; cards become discoverable)

```yaml
nav:
  - ...
  - Models:
      - FlowMol3 v2: models/flowmol3.model_card.md
      - LineageFlow: models/lineageflow.model_card.md
      - Rectified Flow CIFAR: models/rectified_flow_cifar.model_card.md
      - Self-Flow: models/self_flow.model_card.md
      - Twodim FM: models/twodim_fm.model_card.md
      - Capability G.1 analysis: capability_g1_analysis.md
      - Theory deviations: theory/DEVIATIONS.md
  - ...
```

**Option (b): add to `not_in_nav` allowlist** (silent; cards not linkable)

```yaml
not_in_nav: |
  ...
  models/*.model_card.md
  capability_g1_analysis.md
  theory/DEVIATIONS.md
```

**Recommendation**: Option (a) — cards become discoverable via the
nav tree, restoring discoverability (the Wave 24 Agent A goal for F.4).

### Phase B — Implement the fix

1. **Edit `mkdocs.yml`** to add the `Models` section to `nav:`
   - Place under `Architecture` (semantically these are architecture
     components — model integrations)
   - OR place under a new top-level `Models` section (more visible)

2. **Decision**: place under `Architecture` as a sub-section (preserves
   the existing nav hierarchy; minimal disruption)

3. **The exact `mkdocs.yml` edit** (insert after line 66, after `Adapter dependencies`):
   ```yaml
       - Models:
           - FlowMol3 v2: models/flowmol3.model_card.md
           - LineageFlow: models/lineageflow.model_card.md
           - Rectified Flow CIFAR: models/rectified_flow_cifar.model_card.md
           - Self-Flow: models/self_flow.model_card.md
           - Twodim FM: models/twodim_fm.model_card.md
           - Capability G.1 analysis: capability_g1_analysis.md
           - Theory deviations: theory/DEVIATIONS.md
   ```

### Phase C — Verification

1. **Run `mkdocs build --strict`** locally
   - Should exit 0 (no warnings, no errors)
   - All 7 nav entries should resolve to existing files

2. **Run `pytest tests/`** — no regression (mkdocs change is config-only)

3. **Inspect `site/` directory** — verify the `Models` section appears
   in the rendered nav tree

### Phase D — Documentation update

1. **Update `framework-freeze-checklist.md` MUST-1 B.3**:
   - Change status from **AT RISK** to **PASS**
   - Update the one-line evidence: "`mkdocs build --strict` exits 0;
     `Models` nav section links 5 model cards + 2 supporting docs"

2. **Update `docs/baseline-audit-report.md` §B.3** if it lists the gate

## Files affected

- `mkdocs.yml` (UPDATE; add `Models` section under `Architecture`)
- `framework-freeze-checklist.md` MUST-1 B.3 (UPDATE; PASS)

## Acceptance

- [ ] `mkdocs.yml` carries the new `Models` section
- [ ] `mkdocs build --strict` exits 0 (no warnings, no errors)
- [ ] All 7 nav entries resolve to existing files
- [ ] `pytest tests/` still passes (no regression)
- [ ] `framework-freeze-checklist.md` MUST-1 B.3 marks PASS

## Acceptance gate

Passes if:
1. `mkdocs build --strict` exits 0
2. The Models nav section is visible in the rendered site
3. B.3 entry in `framework-freeze-checklist.md` is updated to PASS

## Estimated time

~5-10 min total (config edit + verify).

## Risk

- **LOW**: a typo in the nav entry will cause mkdocs to fail; the
  `--strict` flag will catch the failure immediately
- **LOW**: a model card file may not exist (rename / move); the fix
  should first verify all 5 files exist before committing the nav change

## Pre-flight check

Before editing `mkdocs.yml`, verify all 7 files exist:

```bash
test -f docs/models/flowmol3.model_card.md && echo OK
test -f docs/models/lineageflow.model_card.md && echo OK
test -f docs/models/rectified_flow_cifar.model_card.md && echo OK
test -f docs/models/self_flow.model_card.md && echo OK
test -f docs/models/twodim_fm.model_card.md && echo OK
test -f docs/capability_g1_analysis.md && echo OK
test -f docs/theory/DEVIATIONS.md && echo OK
```

If any check fails, **stop** and report the missing file (it's likely
a different gap to fix first).

## Follow-up

This fix restores B.3 PASS but does not address the broader
discoverability of model cards on HF Hub (see
`todo/algo-improvement-hf-model-card-pipeline.md` for the
HF-side fix).