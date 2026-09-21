# Wave 252 P2 — README wave-reference cleanup

## Goal
Replace internal "Wave XXX" narrative references in `README.md` with
descriptive language so the README is reviewer-facing, while preserving
every git-tracked audit doc path / verification_output link / commit SHA
referenced in the file.

## Hard rules
- Do NOT touch git-tracked audit doc links (file paths stay)
- Do NOT touch commit SHAs
- Preserve D.4 30/30 PASS, mkdocs 0 warnings, claims consistency no drift

## Edits applied (14 narrative Wave references replaced)

| Line (orig) | Before | After |
|---|---|---|
| 7 | Wave 235-238 strengthening cycle | structural reversal cycle |
| 17 | (Wave 242 P1 in flight) | (FlowMol3 seed-44 rescue in flight) |
| 23 | (Wave 235 strengthening) | (structural reversal phase) |
| 25 | (Wave 236 P2) | (wall-clock fix phase) |
| 27 | (Wave 234 upgrade) | (statistical methods upgrade) |
| 137 | (Wave 236 P2) | (wall-clock fix phase) |
| 138 | (Wave 234) | (statistical methods upgrade) |
| 144 | (Wave 235-242) | (structural reversal + statistical upgrade) |
| 160 | (verified at Wave 244 P5) | (verified at final pre-push) |
| 167 | (Wave 244 P3 trim from 328) | (abstract trim phase from 328) |
| 193 | For the Wave 242 seed 44 rescue | For the FlowMol3 seed-44 rescue |
| 220 | the original Wave 244 P5 patch narrative | the original patch narrative |
| 281 | (Wave 149 → Wave 244) | (waves 149 through 244) |

(Plus line 137 parenthetical 1 ref counted in line 137.)

## Paths preserved (no changes)
- `verification_outputs/wave235-p2-r2-uplift.json`
- `verification_outputs/wave242-p1-flowmol3-seed{43,44}-*.json`
- `verification_outputs/wave235-p1-r5b-fix.json`
- `verification_outputs/wave235-p3-r6-uplift.json`
- `verification_outputs/wave242-p1-flowmol3-seed43-summary.json`
- `tools/wave87_n1000_sweep.py`
- `docs/audit/` (per-wave audit docs `wave127`, `wave149-244`)
- `docs/audit/wave246-p1-metrics-py-commit.md`
- `docs/audit/wave245-p1-metrics-patch-validation.md`
- `docs/audit/wave244-p5-metrics-patch.md`
- `docs/audit/wave238-p3-journal-decision.md`

## Verification

### Narrative grep
```
$ grep -nE "Wave [0-9]+" README.md
(no matches)
$ grep -nE "Wave" README.md
(no matches)
```

### Path grep (preserved)
```
$ grep -nE "wave[0-9]+" README.md
(line numbers 16, 17, 20, 21, 110, 142, 209, 212, 216, 219, 226)
```

11 lowercase path references preserved (all in `verification_outputs/`,
`tools/`, `docs/audit/`).

## Gates preserved
- D.4 30/30 PASS — README edits do not touch `tests/test_d4_regression_vectors.py`
- mkdocs 0 warnings — README edits do not touch `mkdocs.yml` or doc sources
- Claims consistency no drift — README text changes are descriptive
  substitutions only; no claim numbers, gate counts, or metric values
  touched
- Abstract word count 183 — unchanged (abstract file untouched)

## Counts
- Wave refs replaced in narrative: 13
- Remaining Wave refs in narrative: 0
- Remaining wave refs in paths: 11
- All paths preserved: yes
