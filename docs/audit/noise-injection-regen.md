# The C.5 noise-injection sweep: four numbers, one protocol

**Date:** 2026-10-31
**Scope:** `tools/noise_injection_experiment.py`, `docs/CONDITIONS.md`,
`docs/figures/noise_injection_{two_moons,eight_gaussians}_*.png`,
`verification_outputs/noise_injection_*.csv`, `paper-data/R5a_2d_two_moons/`,
`paper-data/R5_legacy_2d_eight_gaussians/`, `tnnls_submission/figures.md` rows 27–32
**Method:** CPU only. Three runs of the sweep driver (one `--quick` into
scratch, one full into scratch, one full into the tracked tree), compared by
digest and by table.

## What was found

The C.5 diagnostic shipped four mutually inconsistent readings of the same
quantity. At `σ = 0` on `two_moons`, with `U = (F − M) / M` and lower W₂ better:

| Source | framework W₂ | `U(σ=0)` | Reading |
|---|---|---|---|
| `verification_outputs/noise_injection_two_moons_framework.csv` (frozen 2026-09-05) | 0.3302 | **+191.61%** | regresses badly |
| `docs/CONDITIONS.md` table (same CSV) | 0.3302 | +191.61% | regresses badly |
| `docs/figures/noise_injection_two_moons_sigma_vs_w2.png` (the shipped PNG) | 0.0850 | **−25.15%** | **helps** |
| full re-run, 2026-10-31 | 0.1227 | **+8.38%** | regresses mildly |

The shipped figure was the worst of the four: it showed the framework *beating*
the baseline on a page whose table said the framework lost by 191%.

Three separate causes:

1. **The figure was a different sweep.** It was a `--quick` render: one seed,
   three NFE budgets, and `framework_rounds = 3`. The CSV is three seeds, five
   budgets, five rounds. A `--quick` run reproduces the committed PNG bytes
   exactly, which is how this was identified.
2. **The framework arm's W₂ is not monotone in the round count.** At `σ = 0`,
   three rounds gives 0.0850 and five rounds gives 0.1227. The five-round arm
   is the one the paper's protocol names, and it is the one the CSV records.
3. **The CSV itself no longer reproduces.** The baseline arm is byte-identical
   across the two months; the framework arm is not. The inference path under
   `_run_framework_arm` changed between 2026-09-05 and today, and no audit
   record covers that change.

`docs/CONDITIONS.md` carried the consequences: its header prose claimed the
framework was "byte-identical to the baseline at `sigma = 0`", its table said
+191.61% `regresses`, and its Interpretation section listed the *hypotheses*
("neutral at σ=0", "starts to help at small σ") as if they were the result.
Three statements, three different answers, in one file.

## What was done

The whole chain was regenerated from one protocol — three seeds, five NFE
budgets `{2, 5, 10, 20, 50}`, five framework rounds, `σ ∈ {0, 0.01, 0.05, 0.10,
0.20, 0.50}`:

```
python3 tools/noise_injection_experiment.py \
    --out-dir verification_outputs --figures-dir docs/figures \
    --conditions-doc /tmp/conditions_new.md
```

The pre-regeneration artifacts are preserved verbatim under
`verification_outputs/noise-injection-pre-regen-2026-10-31/` (four CSVs, six
PNGs, the old `CONDITIONS.md`).

| Cell | pre-refresh | post-refresh | verdict |
|---|---|---|---|
| `two_moons` `U(σ=0)` | +191.61% | **+8.38%** | `regresses` → `regresses` |
| `two_moons` `U(σ=0.5)` | +176.19% | **+9.22%** | `regresses` → `regresses` |
| `eight_gaussians` `U(σ=0)` | +116.04% | **+26.62%** | `regresses` → `regresses` |
| `eight_gaussians` `U(σ=0.5)` | +122.01% | **+31.16%** | `regresses` → `regresses` |

All twelve cells still read `regresses`, so the regime verdict, the
out-of-regime statement, and the G.6 honest-negative accounting
(`n_regressing = 12`, `hns = 1.0`) are unchanged.

One conclusion does change. The pre-refresh uplift *shrank* as σ grew
(191.61% → 176.19%), and three documents read that as a hint that averaging
might dominate at σ ≫ 1. The refreshed uplift *grows* (8.38% → 9.22%,
26.62% → 31.16%), so the hint is gone. The sharper statement is available now:
the penalty is already present at σ = 0 and moves by under one point on
`two_moons` across the whole noise range, so it is a property of the
multi-round inference loop rather than of the injected noise.

## Driver changes

The generator was producing three of the contradictions itself, so it was
fixed before the regeneration:

- `docs/CONDITIONS.md`'s date and `**Wave:**` line were hardcoded to
  2026-09-05 / Wave 17 Phase 2. The date is now the run date and the wave
  label is gone.
- The cross-reference asserted that the framework is byte-identical to the
  baseline at σ = 0. It never was. It now says what the row measures.
- The Interpretation section printed a fixed hypothesis list. It now computes
  the uplift range, the verdict set, the per-target trend and whether a
  transition point exists, from the table it just wrote.
- The three plot titles carried `Wave 17 Phase 2 —`.
- The σ axis used `set_xscale("log")` with a tick at σ = 0, which matplotlib
  silently drops; the tick labels bunched at the right edge. Sigma is a
  categorical axis here and is now drawn as one.

`--conditions-doc PATH` was added so a preview run does not rewrite the
tracked page. `docs/CONDITIONS.md` also carries hand-maintained sections after
the generated block (operating-regime statement, regime summary, honest
unknowns, acceptance gate); a regeneration overwrites them, so the regenerated
head was spliced onto the existing tail.

## Files updated

- `docs/CONDITIONS.md` — regenerated head, spliced tail, refresh disclosure.
- `docs/theory/operating-regime.md` — §1.3 table and the σ* unknown; the
  "monotonically decreasing |U|" reading is replaced by the measured trend.
- `docs/baseline-audit-report.md` §C.5 — the twelve mirrored percentages;
  `n_regressing` and `hns` unchanged.
- `tnnls_submission/figures.md` rows 27–32 — new digests and sizes, and the
  false `§4.2` provenance (the manuscript's §4.2 is "Nine baselines" and cites
  none of these figures) replaced with "supplementary diagnostic".
- `paper-data/SHA256SUMS`, `paper-data/MANIFEST.md`,
  `paper-data/R5a_2d_two_moons/REPRODUCIBILITY_RECIPE.md` — the two framework
  CSV digests, and the claim anchors that pointed at the σ sweep for readings
  it does not contain (`−10.40%` and `−78.25%` come from
  `verification_outputs/wave189-p2-sota-2d-rerun/`, not from this sweep).

## Left alone, and why

- `docs/audit/algorithm-gap-investigation.md` quotes the pre-refresh table. It
  is a dated audit record, so it stays as the record of what was observed then;
  this note is the pointer to what replaced it.
- `docs/baseline-audit-report.md` is labelled "(historical)" in the nav. Only
  the table it mirrors from `CONDITIONS.md` was refreshed; the rest of the
  document is untouched.
- `paper-data/*_SOURCE.md` describe the noise CSVs accurately ("baseline
  noise-injection sweep CSV") and needed no change.

## Unresolved

1. **Which change moved the framework arm** was not bisected. The baseline arm
   reproduces byte for byte, so the change is confined to the framework path
   (`_run_framework_arm` → `CodimensionSheetScheduler` +
   `BatchedTrajectoryRunner`), but the specific commit is unidentified.
2. **The round-count sensitivity is unexplained.** `σ = 0` gives W₂ 0.0850 at
   three rounds and 0.1227 at five. More rounds producing a worse endpoint is
   the opposite of what the multi-round mechanism is for, and nothing in the
   docs addresses it. This is the more interesting finding of the two and it
   needs its own audit.
3. **The two other `twodim_fm` readings are still separate.** The `−10.40%`
   and `−78.25%` ablation readings come from a different harness
   (`wave189-p2-sota-2d-rerun/`) at a different NFE convention. The refreshed
   C.5 sweep does not corroborate or contradict them; they remain a separate
   axis, as `R5a_SOURCE.md` already discloses.
