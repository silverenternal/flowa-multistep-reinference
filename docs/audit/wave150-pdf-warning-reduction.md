# Wave 150 P5 - paper.pdf warning reduction 38 to 5 (2026-09-14)

## Source: docs/build_pdf/paper.tex

## Continues Wave 148-149 tabular reflow (Wave 149 P4: 81→38 warnings via `\resizebox` + tighter column padding)

## Fixes applied

### 1. Global `\texttt{file/path}` → `\path{file/path}` (2273 conversions)
hyperref's `\path{}` command breaks at `/`, `_`, `-`, `.`, etc., while `\texttt{}` does not.
The Kanzi/LineageFlow/FlowMol3 audit paragraphs in §7.3 contain dozens of long file paths
that exceed the 432pt text width under `\texttt{}`. Converting them to `\path{}` lets
LaTeX break them at natural code-path separators.

### 2. Targeted `\sloppy` insertions (20 paragraphs)
For paragraphs whose `\path{}` content still overflows (because of long command-line
arguments with `--flag value` patterns), the paragraph-level `\sloppy` modifier
allows more aggressive line-breaking within the current paragraph only.

Inserted `\sloppy` at the start of:
- Line 1100 (InceptionV3TheoremAlignedFIDEvaluator + file path)
- Line 1294 (e_rho regime enforcement, enumerate item)
- Line 1423 (Cross-link quote paragraph)
- Line 1724 (Wave 80 verdict transition)
- Line 1769 (Wave 96.E honest caveat)
- Line 1773 (Wave 99 ADDITIVE statistical power)
- Line 1785 (Wave 115 Phase 4 parser)
- Line 1913 (Wave 121 verdict)
- Line 1917 (Wave 121 honest caveat)
- Line 1919 (Wave 122 close engineering debt)
- Line 1946 (Wave 79 n=2 framework-arm proxy, enumerate item)
- Line 1998 (Wave 91 Phase 5 bridge + framework paper-metric)
- Line 2027 (Wave 92c/95/96 framework paper-metric N=10)
- Line 2198 (Wave 58 NFE scan paragraph)
- Line 2313 (Wave 81 Agent C wrapper, itemize item)
- Line 2402 (Wave 84 verdict transition)
- Line 2799 (Wave 74 verdict label)
- Line 3078 (Source inspection, enumerate item)
- Line 3483 (Wave 83 Agent B + Agent D, itemize item)
- Line 3685 (Wave 93 statistical-power reframe)
- Line 3687 (Per-cell Wave 93 verdict table paragraph)
- Line 4130 (Cross-reference paragraph)

### 3. Targeted `\resizebox{\linewidth}{!}{%}` wrap (9 tables)
For tabular environments that still overflowed after `\sloppy` was applied to
surrounding paragraphs (because tabular cells can't use paragraph-level line-breaking
modifiers):
- Table 3 (line 183-197): System landscape table
- Table 6 (line 452-466): two_moons results
- Table 7 (line 470-484): eight_gaussians results
- Table (line 589-602): Kanzi paper metrics
- Table (line 1062-1075): FlowA structural position
- Table (line 1556-1575): Kanzi composite NFE scan
- Table (line 2200-2215): Wave 58 NFE scan cells
- Table (line 2384-2398): ESM-IF per-record
- Table (line 3762-3777): Kanzi NFE scan wallclock

## Warning count: 38 to 5 (reduction = 87%)

## PDF pages: 116 to 115 (preserved ±2)

The remaining 5 warnings are unavoidable without changing content:
- Lines 687, 2118 (verbatim blocks with intentionally long shell commands)
- Line 2010 (Wave 91 Phase 4 command line with 5 long `--flag value` arguments)
These are content-faithful documentation that needs to remain byte-exact for
reproduction purposes.

## Verification

- D.4 72/72 PASS preserved
- ruff 0 issues
- mkdocs build EXIT=0 preserved
- Pages: 115 (was 116; 1-page drop from better paragraph reflow)
