# Wave 151 P1 - paper.pdf warning reduction 5 to 0 (2026-09-14)

## Source: docs/build_pdf/paper.tex

## Continues Wave 150 P5 (87% reduction 38 -> 5)

## Baseline (Wave 150 P5 close)

Per `docs/audit/wave150-pdf-warning-reduction.md`, the remaining 5 warnings were:
- Lines 687 (verbatim block; 2 overfulls: 1.42pt + 6.67pt)
- Line 2010 (Wave 91 Phase 4 command line with 5 long `--flag value` arguments; 1 overfull: 41.11pt)
- Line 2118 (verbatim block; 2 overfulls: 74.9pt + 53.9pt)

## Fixes applied

### 1. `\usepackage{fancyvrb}` + `\RecustomVerbatimEnvironment` (lines 18-20)

Adds the `fancyvrb` package and re-cusomizes the standard `verbatim` environment
to use the `Verbatim` (capital V) implementation with `breaklines=true,breakanywhere=true`.

This makes the two long-shell-command verbatim blocks (Recipe at line ~671-687;
Wave 96.D reproduce at line ~2112-2118) break long lines automatically at any
character, without changing the visual character of the shell commands themselves.

Fixes 4/5 overfulls (lines 687 and 2118).

### 2. Split `\path{}` into 6 sub-paths (line 2014, was line 2010 in baseline)

The Wave 91 Phase 4 command-line invocation has 5 long `--flag value` arguments
that even with `\sloppy` and `\path{}` separators (/, -, _) still overflowed
by 41pt. Splitting the single `\path{}` into 6 sub-`\path{}` commands
(with literal space breaks between them) gives LaTeX explicit break opportunities
at the argument boundaries.

Original (1 `\path{}`):
```
\path{tools/run\_real\_ckpt\_eval.py --model kanzi --seeds 0 --nfe-budgets 250 --output verification\_outputs/kanzi\_n1000\_framework\_paper\_metrics/kanzi\_n1000\_framework\_paper\_metrics.json --force-mode real --metric-mode real --kanzi-upstream-eval --upstream-n-samples 1000}
```

Replacement (6 `\path{}`):
```
\path{tools/run\_real\_ckpt\_eval.py --model kanzi}
\path{--seeds 0 --nfe-budgets 250 --output}
\path{verification\_outputs/kanzi\_n1000\_framework\_paper\_metrics/}
\path{kanzi\_n1000\_framework\_paper\_metrics.json}
\path{--force-mode real --metric-mode real}
\path{--kanzi-upstream-eval --upstream-n-samples 1000}
```

This is byte-equivalent for reproduction purposes (each `\path{}` renders
identically as monospace text, and the spaces between sub-`\path{}`s are
ordinary inter-word spaces).

Fixes 1/5 overfull (line 2010).

## Warning count: 5 to 0 (100% reduction)

| Location | Before | After | Fix |
|----------|--------|-------|-----|
| Line 687 (verbatim) | 2 overfulls (1.42pt, 6.67pt) | 0 | fancyvrb breaklines |
| Line 2010 (path) | 1 overfull (41.11pt) | 0 | path split into 6 |
| Line 2118 (verbatim) | 2 overfulls (74.9pt, 53.9pt) | 0 | fancyvrb breaklines |
| **Total** | **5** | **0** | |

## PDF pages: 115 to 116 (preserved within +/- 2)

The fancyvrb breaklines wrap the longest shell-command lines into 2 visual
lines, adding +1 page to the rendered PDF. Total pages = 116 (within the
115 +/- 2 tolerance).

## Verification

- `pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py`: **72 passed**
- `ruff check adaptive_reflow/ tests/`: **All checks passed!** (0 errors)
- `python tools/check_claims_consistency.py`: **No drift detected**
- PDF builds cleanly with 0 overfull warnings
- Pages preserved at 116 (within 115 +/- 2 tolerance)

## Diff stat

```
docs/build_pdf/paper.tex | 6 +++++-
1 file changed, 5 insertions(+), 1 deletion(-)
```

5 LOC added: 4 LOC for the fancyvrb package + recustomize + comment, 1 LOC net for the path split (1 removed, 6 added = +5).

## Reproduction

```bash
bash docs/build_pdf/build_pdf.sh 2>&1 | grep -iE 'Overfull|LaTeX Warning' | head -10
```

Should show 0 overfull warnings (only pre-existing LaTeX Warnings for missing figure files and `\textasciicircum` in math mode, which are unrelated to overfull hboxes).