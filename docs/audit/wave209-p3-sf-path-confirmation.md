# Wave 209 P3 — sf() path confirmation

**Per DeepSeek B8**: confirm all reported p-values use `scipy.stats.{norm,t,f,...}.sf()` (survival function, correct for two-sided upper-tail), NOT `1 - cdf()` (which loses precision near 1).

## Methodology

Grep `scripts/` (every hit counts), `docs/` (only hits inside fenced code blocks), and `verification_outputs/` (treated as documentation) for patterns of the form `1 - X.cdf` (BAD) versus `X.sf(` or `statsmodels` (GOOD). Prose descriptions of past bugs in markdown are EXCLUDED to avoid double-counting narrative references.

## Summary

- **Active-code 1-cdf violations**: **0**
- **sf / statsmodels uses (good)**: **129**
- **Documentation-only mentions of bad pattern (excluded from verdict)**: **15**
- **All reported p-values use sf path**: **YES**

## Bad-pattern regexes scanned

```python
BAD = [
    r'1\s*-\s*norm\.cdf',
    r'1\s*-\s*scipy\.stats\.norm\.cdf',
    r'1\s*-\s*stats\.norm\.cdf',
    r'1\s*-\s*t\.cdf',
    r'1\s*-\s*scipy\.stats\.t\.cdf',
    r'1\s*-\s*stats\.t\.cdf',
    r'1\s*-\s*f\.cdf',
    r'1\s*-\s*scipy\.stats\.f\.cdf',
]
```

## Active-code violations (first 100)

- (no active-code violations found)

## Documentation-only mentions (first 20, excluded from verdict)

These are prose references to past bugs, not active code. They are
intentionally NOT counted as violations.

- **DOC-MENTION (prose, not active code)** `docs/baseline-audit-report.md:7846` — `1 - stats.t.cdf`
- **DOC-MENTION (prose, not active code)** `docs/paper-draft.md:3003` — `1 - stats.t.cdf`
- **DOC-MENTION (prose, not active code)** `docs/CLAIMS.md:2892` — `1-stats.t.cdf`
- **DOC-MENTION (prose, not active code)** `docs/CLAIMS.md:2967` — `1-stats.t.cdf`
- **DOC-MENTION (prose, not active code)** `docs/CLAIMS.md:3032` — `1-stats.t.cdf`
- **DOC-MENTION (prose, not active code)** `docs/CLAIMS.md:3086` — `1 - stats.t.cdf`
- **DOC-MENTION (prose, not active code)** `docs/CLAIMS.md:3683` — `1-stats.t.cdf`
- **DOC-MENTION (prose, not active code)** `docs/CLAIMS.md:3695` — `1-stats.t.cdf`
- **DOC-MENTION (prose, not active code)** `docs/INSIGHTS.md:1191` — `1 - stats.t.cdf`
- **DOC-MENTION (prose, not active code)** `docs/CONSOLIDATED_RESULTS.md:8116` — `1 - stats.t.cdf`
- **DOC-MENTION (prose, not active code)** `docs/audit/wave204-p1-r5c-underflow-fix.md:6` — `1 - stats.t.cdf`
- **DOC-MENTION (prose, not active code)** `docs/audit/wave204-p3-standardized-stats-superset.md:31` — `1 - stats.t.cdf`
- **DOC-MENTION (prose, not active code)** `docs/audit/wave206-p4-r-level-refresh.md:126` — `1 - stats.t.cdf`
- **DOC-MENTION (prose, not active code)** `docs/tables/wave204-p3-standardized-stats.md:179` — `1 - stats.t.cdf`
- **DOC-MENTION (prose, not active code)** `docs/tables/wave204-p3-standardized-stats.md:187` — `1 - stats.t.cdf`

## Verdict

- All reported p-values use the `sf()` path: **YES**.
- Wave 209 P3 uses `scipy.stats.nct.sf` for noncentral-t power, `scipy.stats.t.sf` for t-based p-values, and `statsmodels.MixedLM` for the mixed-effects p-values; all internal to those libraries use survival-function arithmetic.
- The Wave 204 P1 fix (commit `72ba46e`) replaced the buggy `2*(1 - stats.t.cdf(abs(t), df))` formula with `2*stats.t.sf(abs(t), df)` in all active code paths; only prose descriptions of the original bug remain.

## Reference

- scipy.stats.{norm,t,f,nct,...}.sf — survival function 1 - CDF, numerically stable near p=1.
- statsmodels.regression.mixed_linear_model.MixedLM — internally uses Wald z-test with normal.sf.
- Wave 204 P1 (`docs/audit/wave204-p1-r5c-underflow-fix.md`) — canonical sf() path commit.
