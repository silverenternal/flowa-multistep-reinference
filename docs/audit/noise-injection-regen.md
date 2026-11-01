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
2. **The figure also used a different round count.** It rendered three
   framework rounds; the CSV and the paper's protocol use five. At `σ = 0`
   and seed 0, three rounds gives 0.0850 and five gives 0.1150. That
   single-seed contrast is not a trend — the round-count probe under
   "Unresolved" below shows W₂ is not monotone in the round count at `n = 3`
   — but it does mean the figure and the table were not describing the same
   arm.
3. **The CSV itself no longer reproduces.** The baseline arm is byte-identical
   across the two months; the framework arm is not. The inference path under
   `_run_framework_arm` changed twice on the day the CSV was written, and no
   audit record covers either change. Both are bisected below.

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
- `tools/verify_submission_readiness.py` — the same two digests in the
  `r1_r6_sha` gate, plus the comments that labelled the CSVs
  "R4 2D Two Moons W2 −7.28%" and "R5 2D Eight Gaussians W2 −10.40%". That
  gate was the one checker that caught the regeneration, which is the
  behaviour a pinned digest should have.

## Left alone, and why

- `docs/audit/algorithm-gap-investigation.md` quotes the pre-refresh table. It
  is a dated audit record, so it stays as the record of what was observed then;
  this note is the pointer to what replaced it.
- `docs/baseline-audit-report.md` is labelled "(historical)" in the nav. Only
  the table it mirrors from `CONDITIONS.md` was refreshed; the rest of the
  document is untouched.
- `paper-data/*_SOURCE.md` describe the noise CSVs accurately ("baseline
  noise-injection sweep CSV") and needed no change.

## Which change moved the framework arm

Bisected. CPU only, in a detached `git worktree` under `/tmp`, so the working
tree was never checked out to an old commit. The probe calls
`_run_framework_arm("two_moons", 0.0, 5, seed)` for seeds 0–2 and reports the
mean W₂; it reproduces the current CSV exactly (`0.11498652813900606` /
`0.12344828077618251` / `0.12971672568990109`), and at `441f54f2` it
reproduces the frozen CSV's seed-0 value to the last digit
(`0.32676622586323734`).

| Commit | Date | Change | mean W₂ at σ = 0 |
|---|---|---|---|
| `441f54f2` | 2026-09-05 | Wave 17 Phase 2 — the run that produced the CSV | 0.330199 |
| `51130a76` | 2026-09-05 08:31 | Wave 31-C — `CodimensionSheetScheduler.n_cap` driven by the sheet-vs-cell ratio instead of the cosine ramp | 0.135968 |
| `12365dfd` | 2026-09-05 10:26 | W33 Agent E — per-round diminishing `eps` schedule instead of a constant `eps` | 0.122717 |
| `a81b3de2` | 2026-10-31 | HEAD — nothing further moved this arm | 0.122717 |

Both transitions are step changes, not drifts: `8944a095` (parent of
`51130a76`) returns 0.330199 and `51130a76` returns 0.135968; `9c10d212`
(parent of `12365dfd`) returns 0.135968 and `12365dfd` returns 0.122717.

One bisect point, without touching the working tree:

```bash
git worktree add --detach /tmp/wt 51130a76
mkdir -p /tmp/wt/data && ln -sf "$PWD/data/twodim_fm_two_moons.npz" /tmp/wt/data/
python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('nie', '/tmp/wt/tools/noise_injection_experiment.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print('%.6f' % (sum(m._run_framework_arm('two_moons', 0.0, 5, s)['w2'] for s in (0, 1, 2)) / 3))
"
git worktree remove --force /tmp/wt
```

The `data/` symlink is needed because the 2D FM weights are untracked, so a
fresh worktree has no `data/` directory at all; without it the adapter raises
`weights_file_not_found`.

So the CSV was generated once at Wave 17 and never regenerated through two
scheduler changes made later the same day. The `**Date:** 2026-09-05` in the
old `CONDITIONS.md` was the date of that one run, and by the end of that day
the table described a scheduler that no longer existed. Nothing about the
table's shape showed it: same six σ levels, same 18 rows, same `rounds = 5`,
same NFE 500 — only the values were from a different operator.

Neither change is a defect, and neither is a regression fix aimed at this
sweep. `51130a76` makes `n_cap` follow the paper's sheet-vs-cell evidence
balance (Lemma 2 / Corollary 1) instead of a generic cosine ramp; `12365dfd`
realises Theorem 1's `eps → 0` limit as a per-round schedule instead of a
constant. Both are the paper-aligned direction, and both were committed under
Wave 31 / Wave 33 without re-running C.5.

The direction of the finding is invariant across the three states. The
baseline mean at σ = 0 is 0.1132 in all of them (the baseline arm is
byte-identical across the two months), and the framework mean is 0.330 /
0.136 / 0.123, i.e. +192% / +20% / +8%. Every state is `regresses`; what the
two commits moved is the size of the penalty, not its sign. That is why the
regime verdict and `hns` are unchanged by the refresh, and why the bisect does
not reopen them.

## Unresolved

1. **The round-count sensitivity is unresolved.** The shipped figure used
   `framework_rounds = 3` and the CSV uses 5, so the round count was probed
   directly: `two_moons`, `σ = 0`, seeds 0–2, `K ∈ {1, 2, 3, 4, 5, 8, 16}`.

   | K | NFE | mean W₂ | sd | per-seed |
   |---:|---:|---:|---:|---|
   | 1 | 100 | 0.1103 | 0.0295 | 0.1441 / 0.0897 / 0.0971 |
   | 2 | 200 | 0.1467 | 0.0245 | 0.1665 / 0.1543 / 0.1193 |
   | 3 | 300 | 0.0907 | 0.0113 | 0.0850 / 0.1037 / 0.0833 |
   | 4 | 400 | 0.1958 | 0.0449 | 0.1505 / 0.1966 / 0.2403 |
   | 5 | 500 | 0.1227 | 0.0074 | 0.1150 / 0.1234 / 0.1297 |
   | 8 | 800 | 0.1259 | 0.0130 | 0.1137 / 0.1396 / 0.1245 |
   | 16 | 1600 | 0.1246 | 0.0088 | 0.1304 / 0.1289 / 0.1144 |

   W₂ is not monotone in K: `K = 3` is the best cell and `K = 4` the worst,
   with a gap of 1.6 pooled sd. At `n = 3` seeds that is not a resolvable
   effect, and the seed spread is of the same size as the between-K spread.
   What can be said is narrower than what this note said before the probe:
   the 0.0850 / 0.1227 contrast that opened this investigation is a
   single-seed (`K = 3`) versus three-seed (`K = 5`) comparison, so it is
   not evidence that more rounds hurt. The round count's effect on this
   target is unmeasured, and settling it needs a within-seed design with
   more than three seeds rather than a re-read of the existing runs.
2. **The two other `twodim_fm` readings are still separate.** The `−10.40%`
   and `−78.25%` ablation readings come from a different harness
   (`wave189-p2-sota-2d-rerun/`) at a different NFE convention. The refreshed
   C.5 sweep does not corroborate or contradict them; they remain a separate
   axis, as `R5a_SOURCE.md` already discloses.
