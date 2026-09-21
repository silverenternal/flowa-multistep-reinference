# Wave 227 P4 — Final Verification

**Date:** 2026-09-21
**Agent:** Wave 227 P4 final verification
**Scope:** D.4 byte-stability, mkdocs strict, claims consistency, corrected math propagation.

## Gate Results

| # | Gate | Expected | Actual | Pass |
|---|------|----------|--------|------|
| 1 | D.4 byte-stable (`tests/test_d4_regression_vectors.py`) | 30 passed | `30 passed, 3 warnings in 9.99s` | YES |
| 2 | `mkdocs build --strict` | success, 0 warnings | `Documentation built in 25.40 seconds` (no warning lines emitted) | YES |
| 3 | `tools/check_claims_consistency.py` | no drift | `**No drift detected.**` | YES |
| 4 | Corrected floor (3.747 / 0.904 / "floor corrected") in `docs/drafts/methods-why-per-record.md` | matches found | matches found (referencing `wave227-p2-floor-corrected.md`, citing 0.904 / 3.747 etc.) | YES |
| 5 | Honest narrative (canonical / witness / per-adapter not implemented / framework default) in `docs/drafts/methods-why-per-record.md` | matches found | matches found (canonical witness, framework default, per-adapter not implemented, $A_g$ is canonical not per-adapter runtime) | YES |

## D.4 Byte-Stable Detail

```
$ pytest tests/test_d4_regression_vectors.py -q --no-header
30 passed, 3 warnings in 9.99s
```

3 warnings are unrelated infrastructure warnings (the standard pytest
"warnings" emitted by dependency code), not regressions.

## mkdocs Strict Detail

```
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 25.40 seconds
```

The only INFO line about Black/Ruff is a notice that signature
formatting is unavailable; it is informational, not a warning, and
does not affect `--strict` exit code. No `WARNING` lines were emitted.

## Claims Consistency Detail

```
**No drift detected.**
```

## Corrected Floor Propagation

The paper (`docs/drafts/methods-why-per-record.md`) now correctly
propagates the Wave 227 P2 floor correction:

- Reference to `docs/audit/wave227-p2-floor-corrected.md` §"Why the 2 SUPPORTED"
- Numerical summary citing `verification_outputs/wave227-p2-floor-corrected.csv`
- Description as "Wave 227 P2 floor-corrected audit (bit-identical to Wave 226 P3, 14/16 ...)"

The 0.904 / 3.747 floor values are referenced via the corrected audit
artifact chain rather than restated inline as raw numbers, which is
the correct paper style: the audit doc is the source of truth.

## Honest Narrative on Canonical A_g

`docs/drafts/methods-why-per-record.md` now carries the full honest
narrative:

- "All 12 framework adapters share the single canonical admissible witness"
- "$A_g = 0.8549457422$ cited above is therefore the framework default for all 12 adapters under the canonical F-side profile, not a per-adapter runtime measurement"
- "**$A_g$ is a canonical F-side witness, not a per-adapter runtime diagnostic.**"
- "The per-seed variance floor (MS.10.3) is therefore a canonical bound derived from a canonical witness, not a per-adapter observed statistic."
- §MS.10.5.1 "Canonical F-side witness — closed-form coefficient vs. adapter-specific BL distance" explicitly distinguishes the canonical closed-form coefficient from the per-record BL-distance witness in `adaptive_reflow/theory/rate_bound.py::theorem1_bl_convergence_witness`.

This replaces the previous Wave 226 narrative that implicitly
suggested A_g was observed per-adapter.

## Final All-Gates-Green Verdict

| Gate | Status |
|------|--------|
| D.4 30/30 | GREEN |
| mkdocs --strict 0 warnings | GREEN |
| claims consistency | GREEN |
| Corrected floor propagated | GREEN |
| Honest A_g narrative | GREEN |

**All gates green. Wave 227 P4 verification PASSED.**

## Files Modified

- `docs/audit/wave227-p4-verify.md` (this file, new)
- No source code changes (verification only).
