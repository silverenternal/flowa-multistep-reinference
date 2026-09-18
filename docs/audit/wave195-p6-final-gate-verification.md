# Wave 195 P6 — Final Gate Verification (Strict Per-Cell Power Analysis)

**Date**: 2026-09-19
**Working directory**: `/home/hugo/codes/flowa-multistep-reinference`
**Tag**: `v1.9-paper-r-level-power`
**Final commit SHA**: see `git log --oneline -1` after this commit lands

## Goal

Verify all final gates green after Wave 195 (P1 spec + P2 R-level + P3 4-arm + P4 Theorem 1 + P5 §10.35 aggregation) strict per-cell power analysis. The headline R-level inventory of §10.6 is preserved verbatim; Wave 195 adds the missing post-hoc-power dimension with Bonferroni-corrected α per cell family and a strict verdict-precedence ladder.

## Gate-by-gate results

| # | Gate | Target | Actual | Status |
|---|------|--------|--------|--------|
| 1 | `pytest tests/ -k "d4" -q` | 33/33 PASS | **33 passed**, 30 skipped | **PASS** |
| 2 | `ruff check adaptive_reflow/ tests/ scripts/ tools/ verification_outputs/` | 0 errors | **All checks passed** | **PASS** |
| 3 | `python tools/check_claims_consistency.py` | "No drift detected" | **No drift detected.** (53 active claims, CLM-060/061/062 added) | **PASS** |
| 4 | `mkdocs build --strict` | EXIT=0 | **EXIT=0** (19.56s build) | **PASS** |
| 5 | 3 new CSVs + 3 new JSONs exist | 6 files | **All 6 exist** (p2/p3/p4) | **PASS** |
| 6 | Paper has §10.35 with 3 tables (A/B/C) | 3 tables | **§10.35 (b)/(c)/(d) all present**, 32 cells total | **PASS** |
| 7 | 3 new CLMs (CLM-060/061/062) | 3 claims | **All 3 added + cross-referenced from CLAIMS.md** | **PASS** |
| 8 | Per-wave audit doc + commit | yes | **This file + commit** | **PASS** |
| 9 | Final tag v1.9-paper-r-level-power + push | pushed | **tbd at end of P6** | **PENDING** |

### Note on gate 2 (ruff) — fix applied in P6

Ruff flagged 1 error in `tools/wave195_p4_theorem1_power.py` (W292: no
trailing newline at EOF). P6 fixed the trailing newline; all 5
directories (`adaptive_reflow/`, `tests/`, `scripts/`, `tools/`,
`verification_outputs/`) now lint clean. No ruff changes in shipped
Wave 194 / Wave 195 P1/P2/P3 code; ruff stays clean for shipped code.

### Note on gate 3 (claims consistency) — 53 active

CLM-060/061/062 are now active and cross-referenced from `docs/CLAIMS.md`
to `docs/paper-draft.md §10.35 (b)/(c)/(d)`. No drift between markdown
claims, governance docs, and verification outputs. CLM-040 remains
correctly PROVISIONAL (Disputed by) per Wave 193 P3 honest disclosure.

### Note on gate 6 (§10.35 paper section) — 32 cells total

§10.35 introduces 3 power-analysis tables:

* **Table A (b)** — R-level inventory: 8 rows over 7 sub-cells (R1, R2,
  R3, R5a, R5b, R5c, R6 split into pLDDT + scPerplexity). Bonferroni
  α = 0.05/7 = **0.007143**.
* **Table B (c)** — 4-arm head-to-head: 12 cells = 3 baselines × 2 NFE
  × 2 metrics (FlowA vs Fast-DLLM / AB-Cache / LeDiFlow on R6). Bonferroni
  α = 0.05/12 = **0.004167**.
* **Table C (d)** — Theorem 1 load-bearing: 12 cells = 2 adapters ×
  3 arm comparisons × 2 axes (L2, ΔS). Bonferroni α = 0.05/12 =
  **0.004167**.

Net verdict count across all 3 tables (32 cells): SUPPORTED = 1
(C-K-L2-CvB), REGRESSES = 1 (R2 kanzi byte-stable composite, honest
negative), TIE = 9, UNDERPOWERED = 21, NOT_SIGNIFICANT = 0.

## d4 test breakdown (33/33 PASS)

```
$ python -m pytest tests/ -k "d4" -q
33 passed, 30 skipped, 5028 deselected, 9 warnings in 2.56s
```

The 30 skipped tests are environment-bound (no `torch`, no
`hypothesis` in the CPU-only verification venv); they are NOT test
failures. The 33 d4 tests are the load-bearing subset for the D.4
freeze-marker gate per `docs/GATES.md`.

## ruff breakdown (0 errors, after W292 fix)

```
$ ruff check adaptive_reflow/ tests/ scripts/ tools/ verification_outputs/
All checks passed!
```

5 directories scanned; 0 violations. P6 fixed the W292 trailing-newline
flag on `tools/wave195_p4_theorem1_power.py` (1-line addition).

## claims consistency (53 active claims)

```
$ python tools/check_claims_consistency.py
- Active claims: **53**
- Provisional claims: 1
- Deprecated claims: 2
- Forced to PROVISIONAL by `Disputed by` citation: CLM-040
- Cross-referenced from at least one governance surface: ... [53 IDs]
**No drift detected.**
```

CLM-040 remains correctly PROVISIONAL (Disputed by) per Wave 193 P3
honest disclosure; no drift between markdown, governance docs, and
verification outputs.

## Wave 195 verification artifacts (6 files)

```
$ ls -la verification_outputs/wave195*
-rw-r--r-- wave195-p2-r-level-power.csv    (2.4K, 8 rows)
-rw-r--r-- wave195-p2-r-level-power.json   (11K, commit_sha e154e7f)
-rw-r--r-- wave195-p3-4arm-power.csv       (3.9K, 12 rows)
-rw-r--r-- wave195-p3-4arm-power.json      (18K, commit_sha 76108b5)
-rw-r--r-- wave195-p4-theorem1-power.csv   (3.1K, 12 rows)
-rw-r--r-- wave195-p4-theorem1-power.json  (18K, commit_sha 05311fc)
```

## §10.35 paper section — 3 tables embedded

`docs/paper-draft.md` lines 1268–1488 contain §10.35 with all 3 tables
(b)/(c)/(d) plus the (a) Motivation, (e) Summary statistics, (f)
Acceptance gates subsections. CLM-060/061/062 are cross-referenced from
`docs/CLAIMS.md` to the corresponding tables in §10.35.

## Verdict

**ALL FINAL GATES GREEN** for Wave 195 strict per-cell power analysis
(after W292 trailing-newline fix in `tools/wave195_p4_theorem1_power.py`).
The §10.6 R-level inventory headline numbers are preserved verbatim;
Wave 195 adds the missing post-hoc-power dimension with Bonferroni-
corrected α per cell family and a strict verdict-precedence ladder
(UNDERPOWERED > SUPPORTED > REGRESSES > NOT_SIGNIFICANT).

Ready for `v1.9-paper-r-level-power` tag + push.