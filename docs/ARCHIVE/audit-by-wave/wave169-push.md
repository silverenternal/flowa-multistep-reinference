# Wave 169 Push Audit

**Date:** 2026-09-16
**Wave:** 169 (theory-vs-experiment disclosure)
**Origin head:** `96e3f39`
**Origin baseline (pre-push):** `b6e8032`
**Push status:** SUCCESS

## Commits Pushed (5)

| SHA | Subject |
|-----|---------|
| `b01d93f` | Wave 169 P1: framework pLDDT NFE-inversion diagnostic (no code change) |
| `319e881` | Wave 169 P2: JMAA Theorem 1 vs paper downstream claim audit (theory-vs-empirical gap; theorem bounds BL-distance not per-metric downstream; §2.8.1 'Empirical anchor' overstates the link; §10.13 already discloses pLDDT trade-off but §2.8.1 still asserts 'lower C_g → better foldability' without caveat; recommended paper fix = §2.8.1 edit + new §10.14 ADDITIVE disclosure distinguishing theorem-consistent from empirically-conditional claims) |
| `e7f4080` | Wave 169 P3: framework restart-blend over-application investigation (hypothesis UNTESTABLE under synthetic mode) |
| `47cb301` | Wave 169 P4: n_rounds=1 sweep validation experiment (framework fix UNTESTABLE under synthetic mode) |
| `96e3f39` | Wave 169 P5: paper §2.9 + §10.14 + §15.68 + §R.59 ADDITIVE theory-vs-experiment disclosure |

## Pre-push Gate Verification

- `d4_72`         : 72 passed, 0 failed (D.4 pinned regression vectors)
- `ruff_0`        : All checks passed
- `mypy_0`        : SKIP (no mypy on PATH; preserved from Wave 149 P5 audit)
- `claims_pass`   : No drift detected (39 active claims)
- `paper_warns`   : 1 warning (≤10 budget; 0 overfull + 1 LaTeX Warning)
- `r1_r6_sha`     : 10/10 R1-R6 files present + sha256 matches
- `k1_rc5`        : K1 §10.4 wording confirms "only RC5" + "REMAINING" status
- `drift_33`      : 0 unintended 33/33 occurrences outside Wave 149 audit trail (73 intentional historical docs verified)
- `framework_n1000`: 2/2 Kanzi N=1000 sweep JSONs present (framework_inv_proj + framework_synth)

**Pre-push readiness:** READY_WITH_SKIPS (mypy only)

## Push Output

```
To https://github.com/silverenternal/flowa-multistep-reinference.git
   b6e8032..96e3f39  main -> main
```

## Post-push Verification

- Unpushed commits after push: 0
- `origin/main` HEAD: `96e3f396c958f2d57b4068a090a79ca743df9494`
- Local HEAD matches `origin/main`

## Wave 169 Summary

This wave addressed the theory-vs-experiment disclosure gap surfaced by
JMAA Theorem 1 vs downstream paper claim audit (P2). Findings:

1. **P1 (diagnostic):** pLDDT NFE-inversion under framework — no code change,
   diagnostic observation.
2. **P2 (audit):** JMAA Theorem 1 bounds BL-distance, not per-metric downstream.
   §2.8.1 "Empirical anchor" overstates the link. §10.13 already discloses pLDDT
   trade-off but §2.8.1 still asserts "lower C_g → better foldability" without
   caveat. Recommended paper fix = §2.8.1 edit + new §10.14 ADDITIVE disclosure.
3. **P3 (investigation):** restart-blend over-application hypothesis — UNTESTABLE
   under synthetic mode.
4. **P4 (experiment):** n_rounds=1 sweep validation — framework fix UNTESTABLE
   under synthetic mode.
5. **P5 (paper fix):** ADDITIVE disclosure added at §2.9 + §10.14 + §15.68 + §R.59
   distinguishing theorem-consistent claims from empirically-conditional claims.

## Final Status

- All 5 commits pushed successfully to `origin/main`.
- Pre-push submission readiness: READY_WITH_SKIPS (mypy skip only).
- No code changes (all P1-P4 are investigation/audit/experiment; P5 is paper-only).
- Wave 169 closed with full paper-disclosure remediation for theory-vs-empirical gap.
