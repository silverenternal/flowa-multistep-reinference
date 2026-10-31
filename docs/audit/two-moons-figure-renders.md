# The two-moons noise-injection figures: three versions, and which one ships

**Date:** 2026-10-31
**Scope:** `docs/figures/noise_injection_two_moons_{nfe_pareto,pareto_front,sigma_vs_w2}.png`,
`tnnls_submission/figures.md` rows 30–32, `tools/noise_injection_experiment.py`
**Method:** CPU only. Two `--figures-dir` runs of the experiment driver (one
`--quick`, one full) into scratch directories, compared by digest.

## What was found

Running the test suite rewrote these three tracked PNGs. The cause is
mechanical: `tests/test_algo_uplifts/test_noise_injection.py` runs
`tools/noise_injection_experiment.py --quick`, the tool wrote its CSVs to the
requested `--out-dir` but its plots to the module constant `FIGURES_DIR`
(`docs/figures`), so a smoke test wrote over the paper's figures. The tool now
takes `--figures-dir` and the test points it at its own scratch directory.

Fixing that exposed a second problem. With the working tree restored to the
committed bytes, `tools/check_figure_hashes.py` went red on rows 30–32: the
digests in `figures.md` matched neither the committed files nor each other.
Three different renders of the same three plots are in play:

| Render | `nfe_pareto` | `pareto_front` | `sigma_vs_w2` |
|---|---|---|---|
| committed PNGs (and the `paper-data/` copies) | `5e377f28…` 75039 B | `5c271c0c…` 48395 B | `f8a928f3…` 48181 B |
| quoted in `figures.md` rows 30–32 | `dff1d7b4…` 74993 B | `dc32fa69…` 48303 B | `6ed7222c…` 48107 B |
| full-mode re-render, 2026-10-31 | `147dce29…` | `7162dab8…` | `75c45c45…` |

## Which render is which

`--quick` is not a rendering difference, it is a different sweep. It sets
`n_seeds = 1` and `nfe_budgets = (2, 5, 20)`; the default run uses
`n_seeds = 3` and `NFE_BUDGETS = (2, 5, 10, 20, 50)`. The baseline CSV holds
18 rows under `--quick` and 90 rows at full settings, and the plots carry the
matching number of points.

A `--quick` run into a scratch directory reproduces the committed PNGs
**byte for byte** (`5e377f28…`, `5c271c0c…`, `f8a928f3…`). The three figures
the package ships are therefore the 1-seed, 3-budget smoke render.

The `figures.md` digests are a `--quick` render as well, but from a different
matplotlib build: the same 18-row sweep rendered under system python3
(3.14) rather than the `flowmol3` venv (3.12) produces those bytes. They
agree with the committed files as pictures and disagree as files.

The full-mode digests above are a third, genuinely different plot: 90 rows,
three seeds, five budgets.

## What this pass changed

`figures.md` rows 30–32 now quote the committed files. That is what the table
is for — it is a manifest of the bytes the package carries, and those bytes
did not change in this pass.

## What it did not change, and why

The committed figures are smoke renders. Whether the paper should carry the
1-seed diagnostic or the 3-seed, 5-budget render is a content decision about
a frozen submission artifact, not a digest repair, so this pass stopped at
the manifest. Regenerating is one command:

```
python3 tools/noise_injection_experiment.py --targets two_moons
```

That writes the full sweep to `docs/figures/` (the new `--figures-dir`
defaults there) and the `paper-data/R5a_2d_two_moons/` copies would need the
same treatment, then rows 30–32 refreshed from the new digests.

The 34 other figure rows are stable because nothing regenerates them; these
three were the only ones a test could reach.
