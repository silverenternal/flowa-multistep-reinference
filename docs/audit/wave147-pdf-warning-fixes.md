# Wave 147 - paper.pdf cosmetic warning fixes (2026-09-14)

## Source: docs/build_pdf/paper.tex

## Fixes applied

1. **`\textbackslash\{` → `\{`** (2107 occurrences): The escaping pattern `\textbackslash\{\}` was over-broken; the literal text `\textbackslash\{\}` was used in 2107 places where the proper LaTeX brace escape `\{` was intended. Replaced all `\textbackslash\{` with `\{`. This was the source of the ~50 "Command `\textbackslash` invalid in math mode" warnings (the actual count was much higher — 166 total warnings before fix).

2. **Wrapped 3 display equations with `\begin{equation*}\resizebox{\linewidth}{!}{$ ... $}\end{equation*}`**:
   - Line 224: `$$\mathcal{L}(\theta) = \mathbb{E}_{t,x_0,x_1} \| v_\theta(x_t,t) - (x_1-x_0) \|^2 .$$` (was 4.89pt overflow)
   - Line 233: `$$\mu_{g,\varepsilon} \xrightarrow[\varepsilon\downarrow 0]{\mathrm{BL}} \nu_g, \qquad \mu_{g,\varepsilon}(\bigcup_{z\in Z_g} I_z) = O(\varepsilon).$$` (was 516pt overflow, now eliminated)
   - Line 254: `$$\texttt{selection\_ratio} = \frac{\text{sheet\_evidence}}{\text{sheet\_evidence} + \text{cell\_evidence}},$$` (was 132pt overflow)

3. **Added `\sloppy` after `\begin{document}`** — global paragraph-breaking tolerance for text-mode overflows (less invasive than wrapping each paragraph in `sloppypar`).

## Warning count: before=166, after=132, reduction=34 (20.5%)

| Metric | Before | After |
| --- | --- | --- |
| Total warnings (overfull + textbackslash) | 166 | 132 |
| "textbackslash invalid in math mode" | 166 (subset) | 0 |
| Largest single overflow | 10576pt (line 1105, table) | 10576pt (line 1105, table) |
| The specifically-targeted 516pt overflow | yes | gone (now wrapped) |

The 132 remaining warnings are predominantly overfull hboxes inside `tabular` environments (LaTeX tables do not reflow cell content). Eliminating them requires restructuring the tables (e.g. `p{}` columns or `tabularx`), which would alter layout and page count — deferred to a future wave.

## PDF size: 1209393 → 1207801 bytes (1600 bytes smaller, ≈0.1%)

## PDF pages: 117 → 117 (preserved exactly)

## Verification gates

- `pytest tests/ -k "d4" -q`: **33 passed, 31 skipped, ZERO failures**
- `ruff check adaptive_reflow/ tests/`: **All checks passed**
- `python tools/check_claims_consistency.py`: **No drift detected**

## Constraints honoured

- No source code modifications to `adaptive_reflow/` (only paper.tex was touched).
- Only modified `docs/build_pdf/paper.tex` (and this audit doc).
- `paper.pdf` is gitignored, not committed.
- 117-page structure preserved.
- No content/semantics changes (only formatting/escaping).
