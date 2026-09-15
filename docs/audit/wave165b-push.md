# Wave 165b Push Audit (2026-09-16)

## Scope

Pushed Wave 165b (5 commits) to origin/main after P1–P5 fix-ups completed.

## Commits pushed

```
3d76c70 Wave 165b P5: ADDITIVE consolidated §15.63 + §R.54 disclosures for Wave 165b fix-up (2026-09-16)
0fce142 Wave 165b P4: paper section 10.9 ADDITIVE update with actual NFE curve numbers (replaces failed Wave 165 P4 reference; concrete NFE-budget numbers)
c6b8335 Wave 165b P3: novelty_mmseqs2 canonical Pfam-A re-sweep at max sensitivity (-s 7.5)
f68c603 Wave 165b P2: per-component ablation matrix (8 cells, explicit non-loop)
eb62e46 Wave 165b P1: NFE-sample-efficiency curve (NFE=50/100/200/500/1000/2000 baseline+framework; explicit non-loop commands; plot + CSV; gates preserved)
```

## Pre-push gates

```
[ OK ] d4_72          : 72 passed, 0 failed (D.4 pinned regression vectors)
[ OK ] ruff_0         : All checks passed!
[SKIP] mypy_0         : mypy not on PATH (sandbox without mypy); preserved from Wave 149 P5 audit
[ OK ] claims_pass    : No drift detected (39 active claims)
[ OK ] paper_warns    : 1 warning (≤10 budget; 0 overfull + 1 LaTeX Warning)
[ OK ] r1_r6_sha      : 10/10 R1-R6 files present + sha256 matches
[ OK ] k1_rc5         : K1 §10.4 wording confirms "only RC5" + "REMAINING" status
[ OK ] drift_33       : 0 unintended 33/33 occurrences outside Wave 149 audit trail (73 intentional historical docs verified)
[ OK ] framework_n1000 : 2/2 Kanzi N=1000 sweep JSONs present (framework_inv_proj + framework_synth)
READY_WITH_SKIPS: mypy_0
```

## Push result

```
To https://github.com/silverenternal/flowa-multistep-reinference.git
   186f46b..3d76c70  main -> main
```

Post-push: 0 unpushed commits. origin/main HEAD = 3d76c70.

## Notes

- All 5 Wave 165b commits pushed atomically as part of fast-forward merge.
- Pre-push gate READY_WITH_SKIPS (mypy_0 only — sandbox limitation, preserved).
- No force-push needed; local was strictly ahead of origin.