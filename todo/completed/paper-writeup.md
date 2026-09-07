# Workshop paper writeup (typed-contracts framework for flow matching re-inference)

**Status:** done (Wave 19 P2 — commit 2f436f1; docs/paper-draft.md restructured to 5-section outline, 990 lines, 13 tables, 3 SVG figures via tools/_make_wave19_figures.py; honest negative results reported) (+ Wave 41 paper Tier 3 evidence + per-family signed_mean bar chart; Wave 44 paper §Tier 3 update + regenerated tier3 figure; Wave 52 paper §7 Tier 3 substantive rewrite + §Ablations per-component; Wave 54 final rewrite with 3 real Tier 3 numbers; §7.6 honest verdict)
**Depends on:** Wave 11 (theory refactor shipped) + Wave 10 (LineageFlow result) +
`push-unpushed-commits.md` (so reviewers can pull)
**Owner:** framework maintainer
**Goal:** 6-page workshop paper suitable for FlowML / NeurReps / ICLR workshop on
FM. Honest framing of "framework provides corrective value when base adapter
needs it; is neutral when base adapter is correctly trained".

## Possible framings (choose after Wave 10 + Wave 11 settle)

### Framing A — "any FM improves" (if Wave 10 re-run supports it)

- Title candidate: *Typed Contracts and Multi-Round Re-Inference for Flow Matching
  ODE Sampling*
- Headline: framework improves every SOTA FM model we tested (3 SOTA + 5 toy).
- 6 pages: 1 abstract + 1 intro + 2 method (typed contracts + abstract interfaces
  + JMAA theory) + 1 experiments + 1 discussion.

### Framing B — "framework as corrective wrapper" (if Wave 10 re-run still regresses)

- Title candidate: *When Does Multi-Round Re-Inference Help Flow Matching? A
  Diagnostic Framework*
- Headline: framework value is conditional on base adapter correctness; honest
  characterization of when it helps vs when it's neutral.
- 6 pages: 1 abstract + 1 intro + 2 method + 2 experiments (positive + negative
  results table) + 0 discussion (let data speak).

## Required content (both framings)

- §1 Introduction: re-inference for FM is a 2024-2026 active research area; the
  framework's contribution is the typed-contract + abstract-interface
  separation that decouples theory from model glue.
- §2 Framework: `docs/ARCHITECTURE.md` summary, JMAA theorem mapping,
  abstract interfaces (SchedulerProtocol, FinalRestartPolicy,
  FlowMatchingODEAdapter).
- §3 Algorithm: the 5 paper-uplifts + 36 algorithm uplifts measured pass
  (`docs/benchmark-uplifts.md`).
- §4 Experiments: 2D RF SOTA table (CLM-039 + Wave 8 FIX-3 inversion), CIFAR-10
  RF v4 (matched-NFE honest record), FlowMol3 N=5000 paper-parity, Self-Flow
  2026, LineageFlow 2026.
- §5 Discussion: honest negative results; when the framework helps vs doesn't.

## Acceptance gate (BINDING — see `todo/GATES.md`)

**Gate name:** `G-MASTER-PAPER` (defined in `todo/GATES.md`)

**Pre-condition:** `G-MASTER-PHASE-4` passed for **>= 3 models**

**Pass conditions (ALL must hold):**
- [ ] `docs/paper-draft.md` (or equivalent) exists with **>= 6 pages** of content
- [ ] Sections match the proposed outline in this file (intro / framework /
      algorithm / experiments / discussion / conclusion)
- [ ] At least 3 models' results are cited (one per section §4)
- [ ] `docs/CONSOLIDATED_RESULTS.md` reflects all 3+ models
- [ ] All items in this file's checklist marked done
- [ ] `git status --short` returns empty
- [ ] `todo/STATUS.md` is up-to-date

**Verification commands:**
```bash
cd /home/hugo/codes/flowa-multistep-reinference
test -f docs/paper-draft.md && echo "✓ draft exists"
wc -l docs/paper-draft.md                          # expect: >= 600 (6 pages × 100 lines)
grep -c "^## " docs/paper-draft.md                 # expect: >= 6 (sections)
grep -c "Per-model\|per-model" docs/paper-draft.md # expect: >= 3 (model citations)
.venvs/flowmol3_venv/bin/mkdocs build --strict 2>&1 | tail -3
```

**Block rule:** if any pass condition fails, the paper cannot be submitted.
Continue drafting.

## Wave 56 close-out

Status refreshed: paper-draft.md evolved from Wave 19 P2 (5-section outline, 990 lines, 13 tables, 3 SVG figures) through Wave 41 (per-family signed_mean bar chart + Wave 41 paper-audit), Wave 44 (§Tier 3 update + regenerated figure + README Tier 3 evidence), Wave 52 (§7 Tier 3 substantive rewrite + §Ablations per-component), and Wave 54 (final rewrite with 3 real Tier 3 numbers + §7.6 honest verdict). Paper is final-form with all real numbers as of Wave 54 Agent B commit `c119d66`. Last touched commit: `811ca75` (Wave 55 Agent C: Author todo/INDEX.md master entry point).