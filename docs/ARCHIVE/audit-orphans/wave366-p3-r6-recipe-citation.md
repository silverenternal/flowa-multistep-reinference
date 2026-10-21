# Wave 366 P3 — paper §7.2 R6 row ADDITIVE footnote citing R6 reproducibility recipe

**Date:** 2026-09-27
**Author:** Wave 366 P3 (R6 recipe-citation agent — additive paper-polish pass)
**Scope:** Add an ADDITIVE citation footnote to `docs/drafts/paper-A-final.md` §7.2 R6 row that references the Wave 362 P1-published `paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md` and the `reproduce/08_verify_R6_recipe.sh` verification harness — surfacing the reviewer-facing reproducibility contract for the R6 §7.2 STRONG-via-tier-aware-counterfactual verdict without modifying the row's numbers or labels.

**Status:** **FOOTNOTE ADDED — ADDITIVE-only verified; §7.2 R6 row preserved verbatim.**

---

## 1. Executive Summary

| Item | Value | Source |
|---|---|---|
| Footnote location | `docs/drafts/paper-A-final.md` line 549 (between §7.2 R6 row at line 547 and §7.2 R1 row at line 551) | this audit |
| Footnote length | 2 lines (1 prose paragraph) | `git diff --stat` |
| R6 row modification | **NONE** — preserved verbatim per Wave 268 strict-clean | `git diff` shows 0 lines of R6 row modified |
| Recipe file cited | `paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md` | Wave 362 P1 (sha256 `a5ce94a0...`, 11567 bytes, ~204 lines) |
| Verifier harness cited | `reproduce/08_verify_R6_recipe.sh` | Wave 362 P2 (sha256 `ba98ec60...`, 181 lines, 5 checks) |
| Verifier runtime | <1 sec CPU (no GPU required) | `bash reproduce/08_verify_R6_recipe.sh` (5/5 PASS at this audit) |
| Counterfactual methodology | mathematical proxy on frozen Wave 161 paired diff via `TierAwareCodimensionSheetScheduler` wrapper at `adaptive_reflow/algorithm/scheduler/tier_aware.py:158` | Wave 209 P1 A3 / Wave 225 P4 + Wave 268 strict-clean |
| Camera-ready scope | live-GPU 3-seed × N=1000 paired re-verification deferred per Wave 357 P5 §10.5 | paper §10.5 + CLM-073 + R-019 |
| Status change | **NONE** — additive footnote only; §7.2 STRONG-via-tier-aware-counterfactual label preserved verbatim | this audit |

---

## 2. Observed Facts (this audit)

### 2.1 File modified (ADDITIVE — 2 lines added at line 549)

```bash
$ git diff --stat docs/drafts/paper-A-final.md
 docs/drafts/paper-A-final.md | 2 ++
 1 file changed, 2 insertions(+)
```

The diff is exactly 2 added lines: a single ADDITIVE footnote paragraph inserted between the §7.2 R6 row (preserved verbatim) and the §7.2 R1 row (preserved verbatim). No other lines of `docs/drafts/paper-A-final.md` are modified.

```bash
$ git diff docs/drafts/paper-A-final.md
@@ -546,6 +546,8 @@ We validate FlowA across 11 headline cells — 7 R-level cells (R1 LineageFlow,

 **R6 — Kanzi k6 foldability (STRONG via tier-aware counterfactual).** ...
+*Wave 366 P3 ADDITIVE footnote (R6 reproducibility-recipe citation, no number / no label change — `STRONG via tier-aware counterfactual` preserved verbatim per §7.2 R6 row above and Wave 361 P4 row + Wave 362 P1 recipe publication).* ...
+
 **R1 — LineageFlow HMMER (PARTIAL / single-seed).** ...
```

### 2.2 R6 row preserved verbatim (verified at this audit)

The §7.2 R6 row at line 547 is the canonical row from Wave 357 P3 / Wave 357 P5 / Wave 361 P4 / Wave 362 P1. Every number is unchanged:

- Overall pLDDT $d_z = +0.071$ (uniform-arm naive, UNDERPOWERED at R-level $\alpha = 0.007143$) — preserved
- Tier-aware-arm counterfactual $d_z = +0.2235$ (Bonferroni-significant at $\alpha = 0.05$ via `easy_tier_nfe_reduction_factor = 0.5`) — preserved
- Hard-tier pLDDT $d_z = +1.189$ — preserved
- scPerplexity $d_z = -1.077$ (naive) / $-4.019$ (cluster-robust) — preserved
- Status: **STRONG via tier-aware counterfactual upgrade** — preserved verbatim
- All cluster-robust verdicts (hard 3/3 SUPPORTED; medium 1/3 SUPPORTED + 2/3 UNDERPOWERED; easy 3/3 REGRESSES; scPerplexity framework-WINS uniformly) — preserved

No number change. No label change. No wording reframe. Per Wave 268 strict-clean rule.

### 2.3 Recipe file SHA-256 chain (verified at this audit)

```bash
$ sha256sum paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md
a5ce94a0cd3645a06c1ee9104c158eff04838b8e9408ce1cafd5d53565758645  paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md
$ wc -c paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md
11567 paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md
$ wc -l paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md
204 paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md
```

- Recipe file SHA-256: `a5ce94a0cd3645a06c1ee9104c158eff04838b8e9408ce1cafd5d53565758645` (full hash; first 8 chars `a5ce94a0` cited in footnote for brevity per Wave 361 P4 citation convention)
- Recipe file size: 11567 bytes (cited verbatim in footnote)
- Recipe file line count: 204 lines (cited as ~204-line per Wave 362 P1 audit doc convention)

### 2.4 Reproduce script SHA-256 + line count (verified at this audit)

```bash
$ sha256sum reproduce/08_verify_R6_recipe.sh
ba98ec60666d527ed9ceee9f707c109b04d93aa32749bff5186ef31863884d3e  reproduce/08_verify_R6_recipe.sh
$ wc -l reproduce/08_verify_R6_recipe.sh
181 reproduce/08_verify_R6_recipe.sh
```

- Verifier SHA-256: `ba98ec60...` (full hash; not cited in footnote to keep the citation compact)
- Verifier line count: 181 lines (cited verbatim in footnote per Wave 362 P2 audit doc baseline)

### 2.5 Verifier harness output (5/5 PASS at this audit)

```bash
$ bash reproduce/08_verify_R6_recipe.sh
Step 1: verify Wave 161 frozen substrate SHA-256...
  OK: baseline + framework foldability.jsonl SHA-256 verified
Step 2: verify Wave 233 P3 tier-aware counterfactual SHA-256...
  OK: wave233-p3-tier-aware-r6.json SHA-256 verified
Step 3: verify Wave 235 P3 grid-search uplift SHA-256...
  OK: wave235-p3-r6-uplift.json SHA-256 verified
Step 4: reproduce Wave 233 P3 tier-aware d_z = +0.2235...
  reproduced d_z = 0.223463  (expected +0.223463)
  OK: Wave 233 P3 tier-aware d_z reproduced (+/-1e-4)
Step 5: verify Wave 235 P3 best grid cell...
  OK: Wave 235 P3 best cell verified (cell_idx=3, easy_factor=0.0, hard_intensity=3.0, d_z=0.646718)

OK: R6 recipe verified — SHA-256 chain + Wave 233 P3 d_z + Wave 235 P3 best cell
```

All 5 checks PASS. Wall time: <1 sec CPU (no GPU required).

The footnote text references:
- "reproduced d_z = 0.223463 matching expected +0.223463 within ±1e-4 tolerance" — verified ✓
- "best-cell d_z = 0.646718 verified at cell_idx=3" — verified ✓

### 2.6 TierAwareCodimensionSheetScheduler class location (verified at this audit)

```bash
$ grep -n "class TierAwareCodimensionSheetScheduler" adaptive_reflow/algorithm/scheduler/tier_aware.py
158:class TierAwareCodimensionSheetScheduler:
```

The class definition is at `adaptive_reflow/algorithm/scheduler/tier_aware.py:158` — cited verbatim in the footnote.

### 2.7 §10.5 cross-reference (verified at this audit)

The footnote's camera-ready-scope reference points to "Wave 357 P5 §10.5" — this corresponds to `docs/drafts/paper-A-final.md` line 756:

> "**§10.5 R6 3-seed N=1000 live GPU sweep scope (Wave 357 P5, ADDITIVE camera-ready scope, no number change).** The R6 Kanzi k6 foldability §10.5 camera-ready deferred item is **scoped** as a 3-seed × $N = 1000$ paired live-GPU re-verification on **GPU 0 (RTX PRO 6000 Blackwell, 98 GB, sm_120)**..."

Verified: §10.5 is "Live re-run of high-priority cells" (line 750), and Wave 357 P5 is the wave that scoped the camera-ready R6 sweep per this paragraph. Cross-reference is accurate.

---

## 3. Interpretation

### 3.1 Why this footnote is sufficient (not a workaround)

The §7.2 R6 STRONG-via-tier-aware-counterfactual verdict is the framework's load-bearing headline for the R6 cell — it carries the 4 STRONG label in the 11-cell verdict distribution. A reviewer landing on §7.2 R6 row should be able to navigate to:
- (a) The reproducibility recipe that exposes the counterfactual methodology
- (b) The verification harness that re-derives d_z = +0.2235 from the frozen Wave 161 substrate
- (c) The Wave 235 P3 best-cell verification that confirms d_z = +0.6467 at cell_idx=3

The Wave 362 P1 recipe publication provides (a) and (b); the Wave 362 P2 verifier script provides (b) and (c). The footnote exposes both to the reviewer in one click — without modifying the §7.2 row's numbers or labels. The same evidence chain that Wave 310 + Wave 336 + Wave 350 + Wave 361 + Wave 362 already established is now reviewer-visible at the §7.2 R6 row, anchored by the Wave 362 P1 recipe publication.

### 3.2 Why the §10.5 camera-ready cross-reference is load-bearing

The §7.2 R6 STRONG verdict is **carried by the counterfactual methodology applied to the frozen Wave 161 paired diff**, not by a live GPU re-run. This is preserved verbatim in the §7.2 R6 row. The footnote cites "live-GPU 3-seed × N=1000 paired re-verification deferred to camera-ready scope per Wave 357 P5 §10.5" to surface this honest disclosure inline alongside the row — making it clear that:
- (i) the §7.2 STRONG verdict is mathematical-proxy-based (Wave 161 frozen substrate + Wave 209 P1 A3 / Wave 225 P4 counterfactual)
- (ii) the load-bearing full live-GPU re-verification is explicitly deferred to the camera-ready cycle (not silently omitted)

The §10.5 disclosure is preserved verbatim per Wave 268 strict-clean; the footnote does not propose a status promotion, a number change, or a sweep launch.

### 3.3 What this footnote does NOT do

- Does **NOT** modify the §7.2 R6 row's numbers (preserved verbatim — 0 lines of R6 row modified).
- Does **NOT** modify the §7.2 R6 row's status label (preserved verbatim — `STRONG via tier-aware counterfactual upgrade`).
- Does **NOT** promote `UNDERPOWERED` / `DEGRESSES` / `NOT_SIGNIFICANT` to `SUPPORTED` by wording alone (per Wave 268 strict-clean guardrail #4).
- Does **NOT** re-run the live GPU 3-seed N=1000 paired sweep (camera-ready deferred per Wave 357 P5 §10.5).
- Does **NOT** touch `tnnls_submission/` (no SHA-256 manifest update required since the citation is purely additive).
- Does **NOT** modify the recipe file or the verifier script (both already published in Wave 362 P1 / P2).
- Does **NOT** push to remote (NO-PUSH policy, USER AUTHORIZED only).

### 3.4 Why I cite `~204-line` and `181-line` (not `480-line`)

The verifier script `reproduce/08_verify_R6_recipe.sh` is **181 lines** (verified by `wc -l`). The footnote cites "181-line bash verifier" — the actual line count — to preserve honest disclosure per Wave 268 strict-clean rule. The Wave 363 P2 master verifier `reproduce/09_verify_all_cell_recipes.sh` is a separate ~480-line script, but that script is not cited in this footnote (it is the master verifier for all 11 cells, not the R6-specific verifier). Citing the actual line count keeps the footnote reviewer-verifiable.

---

## 4. Hard guardrail compliance + verification runs

### 4.1 D.4 byte-stable regression

```bash
$ python3 -m pytest tests/test_d4_regression_vectors.py -q
... 30 passed, 3 warnings in 5.63s
```

PASS — 30/30 D.4 vectors byte-stable.

### 4.2 Claims consistency

```bash
$ python3 tools/check_claims_consistency.py
...
**No drift detected.**
```

PASS — no drift in `docs/CLAIMS.md` (61 active + 2 deprecated claims).

### 4.3 Ruff lint

```bash
$ ruff check adaptive_reflow/ tests/ scripts/ tools/
All checks passed!
```

PASS — 0 findings in scope dirs (the new content is markdown only; ruff scope is `.py` only, none touched).

### 4.4 Mkdocs strict

```bash
$ mkdocs build --strict
...
INFO    -  Documentation built in 26.37 seconds
```

PASS — exit 0; no mkdocs nav errors.

---

## 5. AGENTS.md hard guardrail compliance

1. **Vendored upstream is sacred** ✓: this audit did not modify any vendored file. The 9 vendored repos are byte-identical to pinned upstream commits (verified via `git -C data/<repo>/log -1` per Wave 365 P1 §2.5).
2. **No destructive edits** ✓: 0 lines of `docs/drafts/paper-A-final.md` §7.2 R6 row modified; the only change is 2 added lines (single ADDITIVE footnote) between R6 row and R1 row.
3. **NO-PUSH policy** ✓: no `git push` performed. The commit is local; user authorization required to push.
4. **Honest uncertainty** ✓: the §7.2 STRONG-via-tier-aware-counterfactual label is preserved verbatim; the counterfactual methodology is explicitly disclosed in the footnote; the camera-ready scope is cross-referenced; the verifier line count is cited honestly as 181 (not the ~480-line master verifier count).
5. **TNNLS submission freeze** ✓: no edits to `tnnls_submission/`. The footnote is in `docs/drafts/paper-A-final.md` (allowed surface) and references existing `paper-data/` + `reproduce/` artefacts (both pre-existing).
6. **Per-phase audit doc** ✓: this file follows the observed-facts / interpretation / gaps format from Wave 188/189/190/195/196/197/198 + Wave 349 + Wave 350 + Wave 351 + Wave 352 + Wave 362 + Wave 363 + Wave 365.
7. **Stricter = cleaner** ✓: chose the additive-footnote path (2 lines added) over any modification to the §7.2 R6 row; the row is preserved verbatim; the citation is anchored on pre-existing SHA-256-pinned recipe + verifier files.

---

## 6. Cross-references

- **`docs/drafts/paper-A-final.md` §7.2 R6 row (line 547)**: the preserved R6 row (Cohen's d_z = +0.071 naive / +0.2235 tier-aware; hard-tier pLDDT d_z = +1.189; scPerplexity d_z = -1.077 naive / -4.019 cluster-robust; STRONG via tier-aware counterfactual).
- **`docs/drafts/paper-A-final.md` line 549**: the new Wave 366 P3 ADDITIVE footnote (this audit).
- **`docs/drafts/paper-A-final.md` §10.5 (line 750 + 754 + 756)**: the R6 camera-ready scope disclosure (Wave 336 P1 + Wave 357 P5).
- **`paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md`** (Wave 362 P1 NEW ~204-line doc, sha256 `a5ce94a0...`, 11567 bytes): the recipe doc with 5 sections (a-e) — SHA-256 anchors, bash/python recipes, counterfactual disclosure, acceptance criteria.
- **`reproduce/08_verify_R6_recipe.sh`** (Wave 362 P2 NEW 181-line bash verifier, sha256 `ba98ec60...`, 5 checks): the single-command reproducibility harness for the R6 cell.
- **`docs/audit/wave362-p1-r6-recipe.md`**: Wave 362 P1 recipe publication audit (the foundational audit for the R6 recipe).
- **`docs/audit/wave362-p2-verify-r6-recipe.md`**: Wave 362 P2 verifier-script publication audit (the foundational audit for `08_verify_R6_recipe.sh`).
- **`docs/audit/wave361-r6-forensic-evidence-chain.md`**: Wave 361 forensic-evidence-chain audit (cites the same substrate + counterfactual chain).
- **`adaptive_reflow/algorithm/scheduler/tier_aware.py:158`**: the `TierAwareCodimensionSheetScheduler` class definition (the §7.2 R6 row's headline scheduler).
- **`verification_outputs/k6_foldability_n1000_w161_q3_2026/`**: Wave 161 frozen baseline + framework foldability (the canonical substrate for §7.2 R6).
- **`verification_outputs/wave233-p3-tier-aware-r6.json`**: Wave 233 P3 R6 tier-aware counterfactual (the §7.2 STRONG verdict derivation).
- **`verification_outputs/wave235-p3-r6-uplift.json`**: Wave 235 P3 R6 20-cell grid-search (the §7.2 d_z = +0.6467 best-cell derivation).
- **`docs/CLAIMS.md` CLM-073**: the canonical R6 tier-aware counterfactual claim row (status preserved verbatim).
- **`docs/CLAIMS.md` CLM-061**: the canonical R6 cluster-robustness claim row.

---

## 7. Smallest next action

If the user later authorizes the camera-ready R6 live-GPU 3-seed N=1000 sweep (per §10.5 + Wave 357 P5), the recipe will be **extended** (not replaced) — the Wave 366 P3 footnote will become a §7.2 R6 cross-reference to:
- (a) the existing Wave 362 P1 counterfactual recipe (preserved verbatim — counterfactual methodology remains valid)
- (b) a new "## Live GPU re-verification" section added to `R6_REPRODUCIBILITY_RECIPE.md` with the live-GPU SHA-256 chain + python snippet reproducing the live d_z (Wave 352 P1 §3.4 + CLM-073 deferred scope)
- (c) a new audit doc `docs/audit/wave352-r6-live-n1000.md` (or successor) with the live-sweep results

Until then, the Wave 366 P3 footnote anchors the §7.2 R6 row on the existing Wave 362 P1 counterfactual evidence chain — byte-stable, verifier-reproducible, and reviewer-visible at the §7.2 row in one click.

---

## 8. Acceptance Criteria (verified)

| # | Criterion | Result |
|---|---|---|
| 1 | ADDITIVE footnote inserted at line 549 of `docs/drafts/paper-A-final.md` (between R6 row at 547 and R1 row at 551) | ✓ PASS |
| 2 | R6 row preserved verbatim (0 lines modified) | ✓ PASS |
| 3 | R1 row preserved verbatim (0 lines modified) | ✓ PASS |
| 4 | Footnote cites recipe file + verifier script + counterfactual methodology + §10.5 camera-ready scope | ✓ PASS |
| 5 | Footnote cites honest line counts (181 for verifier) and honest SHA-256 prefix (`a5ce94a0...`) | ✓ PASS |
| 6 | D.4 byte-stable regression (`tests/test_d4_regression_vectors.py`) 30/30 PASS | ✓ PASS (verified §4.1) |
| 7 | `python3 tools/check_claims_consistency.py` exits 0 | ✓ PASS (verified §4.2) |
| 8 | `ruff check adaptive_reflow/ tests/ scripts/ tools/` 0 findings | ✓ PASS (verified §4.3) |
| 9 | `mkdocs build --strict` exits 0 | ✓ PASS (verified §4.4) |
| 10 | `bash reproduce/08_verify_R6_recipe.sh` 5/5 PASS | ✓ PASS (verified §2.5) |

---

**End of Wave 366 P3 audit doc.**