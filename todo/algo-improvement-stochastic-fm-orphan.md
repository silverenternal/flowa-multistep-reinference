# Algorithm improvement — StochasticFMAdapter enum orphan (Wave 29 Agent C follow-up)

**Status:** done (Wave 39; deleted orphan per audit recommendation)
**Date:** 2026-09-05
**Priority:** medium (audit cleanup; no production impact)
**Depends on:** none (orphan adapter)
**Owner:** framework maintainer
**Wave:** Wave 39 (target — Wave 33 actually performed the deletion; Wave 39 closes out the todo + verifies)
**Goal:** resolve the StochasticFMAdapter enum-bug orphan by **deleting
the adapter** (per Wave 29 Agent C + Wave 32 Agent A audit
recommendation — lowest-risk option since the adapter is unused).

## Background

Per `docs/audit/adapter-conformance-deep-dive.md` (NONCONFORMANCE_BUG #5):
- `StochasticFMAdapter.reference_frame = "stochastic_fm"` (non-canonical)
- `StochasticFMAdapter.normalization = "per_channel_std"` (non-canonical)
- The canonical enums (validated by `validate_state_bundle`) are:
  - `reference_frame`: `world` / `body` / `none`
  - `normalization`: `per_atom_std` / `per_channel_l2` / `none`

Per Wave 32 Agent A (`docs/audit/gap-audit.md` §2.3):
- **StochasticFMAdapter is orphan** — not in `ADAPTER_REGISTRY`; not
  referenced by production adapters; not exercised by tests
- Three resolution options:
  - (a) Change strings to canonical `world` + `per_atom_std` (low-risk but
    doesn't address the underlying orphan status)
  - (b) Extend canonical enums to include `stochastic_fm` / `per_channel_std`
    (introduces non-canonical strings; against the audit philosophy)
  - (c) **Delete StochasticFMAdapter** (audit-doc recommendation;
    lowest-risk path since adapter is unused)

Per Wave 29 Agent C (`docs/audit/adapter-conformance-deep-dive.md`):
> Recommend (c) — the adapter has no callers; deleting it removes the
> canonical-enum drift and frees the namespace.

## Why delete (rationale)

1. **Adapter is unused** — no caller in the repo (production or test)
2. **No tests reference it** — `pytest -k stochastic_fm` returns 0 hits
3. **Not in `ADAPTER_REGISTRY`** — adapter is dead code
4. **Deletion is reversible** — git history retains the file; can be
   resurrected if a future need arises
5. **Avoids canonical-enum extension** — adding `stochastic_fm` /
   `per_channel_std` to canonical enums would muddy the audit trail

## What to do

### Phase A — Verify orphan status (before deletion)

1. **Run `grep -r "StochasticFMAdapter" /home/hugo/codes/flowa-multistep-reinference/`**:
   - Should return only the file that defines the adapter
   - Should NOT return test files, ADAPTER_REGISTRY entries, or production adapters

2. **Run `pytest --collect-only -q | grep -i stochastic`**:
   - Should return 0 hits

3. **Run `grep -r "ADAPTER_REGISTRY" adaptive_reflow/adapters/__init__.py`**:
   - Confirm `StochasticFMAdapter` is NOT registered

If any of these checks finds a non-orphan usage, **abort deletion** and
escalate to option (a) — change strings to canonical.

### Phase B — Delete the adapter

1. **Identify the file**: locate the file that defines
   `class StochasticFMAdapter` (likely `adaptive_reflow/adapters/stochastic_fm.py`
   or similar)

2. **Delete the file** with `git rm`

3. **Update `adaptive_reflow/adapters/__init__.py`** if the adapter was
   imported at the package level

4. **Search and remove any stray references**:
   ```bash
   grep -r "stochastic_fm" /home/hugo/codes/flowa-multistep-reinference/
   ```
   - Remove any `__all__` entries, type-hint imports, or docstring cross-refs

### Phase C — Verification

1. **Run `pytest --collect-only -q`** — should still succeed (no broken imports)
2. **Run `pytest tests/ -v --timeout=60`** — full suite should still pass
3. **Run `mkdocs build --strict`** — should still pass
4. **Run `python tools/capability_audit.py`** — should not regress any gate

### Phase E — Documentation update

1. **Update `docs/audit/adapter-conformance-deep-dive.md` §2.5** —
   mark NONCONFORMANCE_BUG #5 as RESOLVED (deleted)
2. **Update `docs/baseline-audit-report.md`** if it lists StochasticFMAdapter
3. **Add a CHANGELOG entry** (or commit message line) noting the deletion
4. **No update to `framework-freeze-checklist.md`** required (the adapter
   was never in the freeze summary)

## Files affected

- `adaptive_reflow/adapters/<stochastic_fm_file>.py` (DELETE)
- `adaptive_reflow/adapters/__init__.py` (UPDATE if imports exist)
- `docs/audit/adapter-conformance-deep-dive.md` §2.5 (UPDATE; mark RESOLVED)
- `docs/baseline-audit-report.md` (UPDATE if applicable)

## Acceptance

- [ ] Pre-deletion grep confirms orphan status (no callers)
- [ ] File deleted with `git rm`
- [ ] `pytest --collect-only` still succeeds
- [ ] `pytest tests/ -v --timeout=60` still passes (no regression)
- [ ] `mkdocs build --strict` still passes
- [ ] `python tools/capability_audit.py` still passes (no gate regression)
- [ ] `docs/audit/adapter-conformance-deep-dive.md` marks NONCONFORMANCE_BUG #5 RESOLVED

## Acceptance gate

Passes if:
1. Pre-deletion grep confirms orphan status
2. Post-deletion pytest passes (full suite)
3. Post-deletion mkdocs passes
4. No gate regression in capability audit

**Rollback**: if post-deletion pytest fails, restore the file with
`git checkout HEAD -- <file>` and escalate to option (a) (string
change) — but option (a) is not expected to be needed.

## Estimated time

~10-20 min total (verification + deletion + audit doc update).

## Risk

- **LOW**: if a caller is found during pre-deletion grep, the deletion
  is aborted and option (a) is taken instead
- **ZERO**: deletion is reversible via `git checkout`; the file remains
  in git history

## Follow-up (none expected)

This is a cleanup task with no follow-up. The other orphan noted in the
audit (`Reference_flowa`) follows the same pattern; if a Wave 33 audit
confirms orphan status, that adapter can be deleted in the same PR.

## Related cleanup opportunities (within scope of this PR)

Per `docs/audit/adapter-conformance-deep-dive.md`:
- `Reference_flowa` (orphan class) — same fix pattern; include in this PR if
  pre-deletion grep confirms orphan status
- `FreqFlow` / `Kanzi` skeletons — NOT orphans; these are Wave 21 PHASE-3
  adapters; registered in `ADAPTER_REGISTRY`; deferred per MUST-2 / PHASE-3