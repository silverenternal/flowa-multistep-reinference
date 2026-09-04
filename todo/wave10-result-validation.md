# Wave 10 result validation (LineageFlow + "any FM improves" claim)

**Status:** done (Wave 10 LineageFlow integration shipped; per-model analysis in todo/models/lineageflow.md; BLOCKED on upstream `core` documented)
**Depends on:** Wave 10 completion (commit on origin/main)
**Owner:** framework maintainer
**Goal:** decide if the paper headline claim — "any flow matching model, when
integrated into our framework, improves" — is supported or needs qualifier.

## Next action (when starting)

When Wave 10's comparison agent reports `framework_improves_baseline=True` AND
`delta_pct > 0`: append the Wave 10 numbers to `docs/CONSOLIDATED_RESULTS.md` §6.3
as a new protein-axis row; update `docs/CLAIMS.md` to add a CLM-048 documenting the
"any FM improves" claim with protein evidence.
When `framework_improves_baseline=False` AND `delta_pct < -5%`: report blocked,
re-frame the claim to "framework provides corrective value on buggy base models,
is neutral on correctly-trained base models" (per Wave 8 FIX-2 inversion
narrative).

## Acceptance

- `docs/CONSOLIDATED_RESULTS.md` reflects the Wave 10 result honestly.
- `docs/CLAIMS.md` either adds CLM-048 or amends CLM-018/022/039/040 with the
  final framing.
- One-line summary in `todo.json` under `wave_10_summary`.

## Acceptance gate (BINDING — see `todo/GATES.md`)

**Gate name:** `G-MASTER-PHASE-4` (per-model component) for LineageFlow

**Pre-condition:** `G-MASTER-PHASE-3` passed for LineageFlow (it is — see
`todo/models/lineageflow.md` §C for the gate status)

**Pass conditions (ALL must hold):**
- [ ] `docs/CONSOLIDATED_RESULTS.md` §6.3 has a LineageFlow row (or `§7.3`)
- [ ] `docs/CLAIMS.md` has either CLM-048 ("any FM improves on protein") OR an
      amendment to CLM-018/022/039/040 reflecting the actual result
- [ ] `todo.json` `wave_10_summary` has a one-line entry
- [ ] `todo/STATUS.md` "Last completed wave" = Wave 10
- [ ] `git status --short` returns empty

**Verification commands:**
```bash
cd /home/hugo/codes/flowa-multistep-reinference
grep -q "LineageFlow" docs/CONSOLIDATED_RESULTS.md
grep -q "Wave 10" todo/STATUS.md
.venvs/flowmol3_venv/bin/python -c "import json; d=json.load(open('todo.json')); print('wave_10_summary' in d)"
git status --short
```

**Block rule:** if any pass condition fails, `rerun-wave10-with-refactored-framework.md`
cannot start.

## Out of scope

- Re-running Wave 10 (that is `rerun-wave10-with-refactored-framework.md`).
- Push (that is `push-unpushed-commits.md`).