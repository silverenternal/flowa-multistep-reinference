# Wave 269 P3 — Final verification (README-only wave, no source code changes)

**Date:** 2026-09-22
**Branch:** main
**Scope:** README.md (Wave 269 P1 + P2) verification + this audit doc.
**Trigger:** DeepSeek review feedback on README v5 (R6 Metric column typo, Zenodo TBD URLs, missing NI failure disclosure). P1 fixed R6, P2 fixed Zenodo + NI, this P3 confirms all three.

---

## Summary

Three README-only fixes from DeepSeek's review feedback are confirmed in
place and all four pre-existing gates (D.4 byte-stable, mkdocs strict,
claims consistency, 0 internal IDs in README) remain green. This P3 wave
introduces **no source code changes** — it writes the audit doc and
commits.

| Fix | Verified |
|---|---|
| R6 Metric column says "pLDDT d_z" (not FID d_z) | YES (README.md:20) |
| No `zenodo.TBD` / `zenodo/record/TBD` URLs in README | YES (0 matches) |
| NI description includes "negative result: framework is NOT non-inferior" | YES (README.md:34) |

---

## Gate 1 — D.4 byte-stable regression vectors

```
$ timeout 30 .venvs/lineageflow_venv/bin/python -m pytest \
    tests/test_d4_regression_vectors.py -q --no-header
30 passed, 3 warnings in 2.44s
```

- **30/30 PASS.** No regressions from Wave 269 P1 (R6 Metric-column label
  edit) or Wave 269 P2 (Zenodo URL removal + NI disclosure).
- The 3 warnings are pre-existing `DeprecationWarning` from
  `adaptive_reflow/contracts/__init__.py` (re-export bridge to
  `adaptive_reflow.molecular.bundle`); they have been stable since
  Wave 28e3bf9 and are unrelated to this wave.

---

## Gate 2 — mkdocs build --strict

```
$ timeout 30 mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 25.21 seconds
```

- **0 warnings, 0 errors.** Build is strict-clean.
- The "Formatting signatures requires either Black or Ruff" line is an
  informational INFO (not a warning) emitted by mkdocstrings regardless
  of whether strict mode is on; it has been stable since Wave 33.
- No new docstrings, no mkdocs.yml changes, no navigation edits
  introduced by Wave 269 P1 / P2.

---

## Gate 3 — claims consistency (`tools/check_claims_consistency.py`)

```
$ python3 tools/check_claims_consistency.py
- Forced to PROVISIONAL by `Disputed by` citation: CLM-040
- Cross-referenced from at least one governance surface: CLM-001, CLM-002, ... (60 IDs total)

**No drift detected.**
```

- **No drift.** Headline numerical claims (`+0.224`, `+0.647`, `+189%`,
  `−78.25%`, `−67.10%`, `−2.53% to −0.66%`, `+116.46%`) and one-line
  summaries are byte-identical to before. The R6 Metric-column label
  was wrong but the *numbers* were always correct; the fix aligns the
  label with the numbers without touching the numbers.
- CLM-040's PROVISIONAL state (Sidecar/2D-RF framework 0/0 divergence
  investigated in Wave 29) is unchanged by this wave and is correctly
  acknowledged by the consistency check.

---

## Gate 4 — 0 internal IDs in README

```
$ grep -cE "Wave [0-9]+|CLM-[0-9]+|USER ACTION" /home/hugo/codes/flowa-multistep-reinference/README.md
0
```

- **0 internal IDs.** README remains free of `Wave N`, `CLM-N`, and
  `USER ACTION N` identifiers — the TNNLS submission surface stays
  reviewer-clean.
- This gate was already green after Wave 269 P2 (the audit doc
  `docs/audit/wave269-p2-zenodo-ni.md` introduced `Wave 269 P2` only
  inside the audit doc, not inside the README).

---

## Gate 5 — Three DeepSeek fixes verified

### 5.1 R6 Metric column fix (Wave 269 P1, commit `ad5df58`)

```
README.md:20: | R6 | k6 foldability (tier-aware) | **pLDDT d_z** | +0.224 | **+0.647** | +189% | large | §7.6.6 | [ver.](verification_outputs/wave235-p3-r6-uplift.json) |
```

- **Metric column:** `**pLDDT d_z**` (was `FID d_z`) — PASS.
- **Cell label:** `k6 foldability (tier-aware)` (was `MNIST FM (tier-aware k6 pLDDT)`) — PASS.
- **Numerical columns** (`+0.224 | **+0.647** | +189%`) — byte-identical to before.
- **Cross-reference parity:** One-line Summary on README.md:32
  (`tier-aware pLDDT d_z: +0.224 → +0.647`) and reproduce/ table on
  README.md:131 (`pLDDT d_z = +0.647 (+189%)`) all use `pLDDT d_z`,
  so the three sites are now mutually consistent.
- **R5b preserved:** `FID` metric on README.md:19 and reproduce/
  table on README.md:130 are unchanged — R5b is the CIFAR-10
  Rectified Flow cell whose genuine metric is FID.

### 5.2 Zenodo TBD URL removal (Wave 269 P2, commit `cef2634`)

```
$ grep -nE "zenodo\.TBD|zenodo/record/TBD" README.md
(no matches)
```

- **0 matches** for either `zenodo.TBD` or `zenodo/record/TBD` in the
  entire README. PASS.
- The top badge that previously pointed to `https://doi.org/10.5281/zenodo.TBD`
  is removed; the header now contains only CI, D.4 byte-stable, and
  License badges (README.md:3–4).
- The Data and Model Availability table (README.md:194–202) is reduced
  to 3 in-repo checkpoints (Kanzi, LineageFlow, FlowMol3) with their
  SHA-256 prefixes and on-disk paths; the 6 future-upload checkpoints
  (HiDream-I1, GraphBFN, Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2,
  FreqFlow) are summarized in a single line below the table:
  `Additional checkpoints ... will be uploaded to Zenodo at submission freeze.`
- No TBD URL anywhere; reviewers cannot 404.

### 5.3 Non-inferiority failure disclosure (Wave 269 P2, commit `cef2634`)

```
README.md:34: ... and non-inferiority test (R5b, negative result: framework is NOT non-inferior at multi-round regime, p_NI = 0.9985). Full details in [DATA_PRESENTATION.md §3](DATA_PRESENTATION.md).
```

- **Contains `negative result`:** YES.
- **Contains `NOT non-inferior`:** YES (verbatim).
- **Matches DATA_PRESENTATION.md §3 verdict:** YES — DATA_PRESENTATION.md
  states `verdict: NOT NON_INFERIOR at multi-round regime` and
  `p_NI = 0.9985`; the README now mirrors that verdict inline.
- No over-claim risk at peer review.

---

## Repo state at verification time

```
$ git status --short
 M docs/figures/noise_injection_two_moons_nfe_pareto.png
 M docs/figures/noise_injection_two_moons_pareto_front.png
 M docs/figures/noise_injection_two_moons_sigma_vs_w2.png
```

The three modified PNG files are pre-existing figure diffs unrelated
to this wave (they predate Wave 269 P1; they were already `M` at the
start of the conversation per the gitStatus snapshot). They are out of
scope for the README-only Wave 269 P3 and are not touched by this commit.

```
$ git log --oneline origin/main..HEAD | wc -l
24
```

24 unpushed commits on `main` (this P3 commit will be the 25th).
The unpushed history includes Wave 266, 267, 268, and 269 series —
all editorial/README/audit-only, all preserving the four gates. Push
to `origin/main` is the user's call (per the harness convention, this
wave does not auto-push).

---

## Hard-rule compliance

| Rule | Status |
|---|---|
| DO NOT modify framework source code | PASS — no source files touched |
| DO NOT touch vendored code | PASS — no files under `data/` modified |
| DO NOT touch background tasks | PASS — no background commands invoked |
| DO preserve D.4 30/30 PASS | PASS (Gate 1) |
| DO preserve mkdocs 0 warnings | PASS (Gate 2) |
| DO preserve claims consistency no drift | PASS (Gate 3) |
| DO NOT introduce any new internal IDs (Wave / CLM / USER ACTION) | PASS (Gate 4) |
| DO NOT touch unrelated PNG figures | PASS — pre-existing figure diffs left alone |

---

## Files touched by this P3

- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave269-p3-final-verify.md` — this audit doc.

No other files modified. No source code, no tests, no docs, no figures,
no config.