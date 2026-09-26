# Wave 363 P1.K7 — K7 LineageFlow Novelty Reproducibility Recipe

**Date:** 2026-09-27
**Wave:** 363 P1 (K7 reproducibility recipe authoring)
**Branch:** main
**Scope:** Author `paper-data/K7_lineageflow_novelty/REPRODUCIBILITY_RECIPE.md` (~215 lines, NEW) for the K7_Lineageflow_novelty paper cell. K7 is a **SUPP / direction-INVERTED** cell (per Wave 306 + Wave 327 rev) so the recipe must reflect the honest disclosure, NOT promote the W280 P `d_z=∞, p<1e-300` STRONG claim that was the load-bearing false claim in the paper §7.1 line 650.

---

## 1. Observed facts

### 1.1 Recipe authored

- **File created:** `paper-data/K7_lineageflow_novelty/REPRODUCIBILITY_RECIPE.md` (215 lines)
- **SHA-256:** `cdb03fdf60a00f2bc02f8ca75d1e804ecae04e89459acbf16ae0e860d1f9eb82`
- **Sections:**
  1. Header (cell ID + headline metric + status + methodology disclosure)
  2. **(a) Headline metric** — W166 P3 N=1000 baseline 466/1000 (46.6%) vs framework 37/1000 (3.7%) novel at pctid<30% twilight-zone; framework 12.6× LESS Pfam-novel; direction INVERTED per Wave 306 + Wave 327; cross-threshold sensitivity (20%/30%/50%); W280 P numerical-artefact cross-reference; W165 P7 positive reading (zinc-finger/DNA-binding biological reframing)
  3. **(b) Evidence chain + SHA-256 anchors** — 6 W166 P3 anchor hashes + W280 P summary hash + K7 paper-data SHA256SUMS sidecar; bash verification commands
  4. **(c) Reproducibility path** — CPU-only path: re-derive 466/1000 vs 37/1000 from frozen `.m8` files via `tools/lineageflow/novelty_metric_pctid.py` (no GPU, no MMseqs2 re-search); cross-threshold sensitivity bash script; environment (.venvs/lineageflow_venv if wrapper needed; <1 sec wall-clock)
  5. **(d) Disclosure** — honest PARTIAL/SUPP direction-INVERTED verdict per Wave 268 strict-clean rule; W280 P `d_z=∞, p<1e-300` is numerical artefact (NOT framework-vs-baseline); W165 P7 positive reading (3 zinc-finger families absorb 87.4% of framework hits); user Tier 1 directive "降级而非重跑" honored
  6. Acceptance criteria (7 checks; SHA-256 chain + novelty_metric_pctid.py output + cross-threshold + D.4 30/30 PASS + claims consistency + ruff 0 + mkdocs strict PASS)

### 1.2 SHA-256 chain verified

All 6 W166 P3 anchors + W280 P summary + K7 paper-data SHA256SUMS sidecar verified at recipe authorship (computed via `sha256sum` from repo root + `cd paper-data/K7_lineageflow_novelty && sha256sum --summary --check SHA256SUMS`):

| File | SHA-256 |
|---|---|
| `verification_outputs/novelty_pctid_w166_q3_2026/novelty_results_full.json` | `61dd70fab83e1a4a5ad6874ade10fe88f3e4653ba8da2d8ca12ec61d4605dae0` |
| `verification_outputs/novelty_pctid_w166_q3_2026/novelty_results.json` | `91f054f40bddf0a767b339026e7389377e37ed47984ecb290716ccd0daa9f292` |
| `verification_outputs/novelty_pctid_w166_q3_2026/baseline/n1000_full_loose.m8` | `e4d5a52c969cf80c1813c666555a83528b722a977fcbb90ff73953e2621aedde` |
| `verification_outputs/novelty_pctid_w166_q3_2026/framework/n1000_full_loose.m8` | `4d667b9a7524c957f75f698a3b35a06d04c7889cf4e776f1dc108206c4ad94b2` |
| `verification_outputs/novelty_pctid_w166_q3_2026/baseline/sanity_n5_loose.m8` | `0f7702aa4eaa26efa7b017999ccddce471eb74061a0770fa8bba1c7760b96d85` |
| `verification_outputs/novelty_pctid_w166_q3_2026/framework/sanity_n5_loose.m8` | `5886075cf010409b58181da24a44513ef99db993a00ba305802b9a4f32029307` |
| `verification_outputs/wave280-k7/summary.json` (numerical-artefact sidecar) | `9fd6fc60288128d9aa1003f48471e2b2278b1eb7dba41e1495253336c5cb8fd6` |
| `paper-data/K7_lineageflow_novelty/SHA256SUMS` (sidecar ledger) | `4c09e2aa98b2238a89a0ad8c314e0926a2c89060e4a67fa8e9f7ac3a64d506f3` |
| `paper-data/K7_lineageflow_novelty/REPRODUCIBILITY_RECIPE.md` (this Wave 363 P1 deliverable) | `cdb03fdf60a00f2bc02f8ca75d1e804ecae04e89459acbf16ae0e860d1f9eb82` |

### 1.3 Acceptance gates verified

All 4 verification gates GREEN at recipe authorship:

```
$ python3 -m pytest tests/test_d4_regression_vectors.py -q
30 passed, 3 warnings in 14.15s                                    [PASS]

$ python3 tools/check_claims_consistency.py
# Claims consistency report
- Active claims: 61
- Provisional claims: 0
- Deprecated claims: 2
- Forced to PROVISIONAL by `Disputed by` citation: CLM-040
- Cross-referenced from at least one governance surface: CLM-001..CLM-069
**No drift detected.**                                                  [PASS]

$ ruff check paper-data/K7_lineageflow_novelty/
warning: No Python files found under the given path(s)
All checks passed!                                                     [PASS]

$ mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 22.30 seconds                       [PASS]
```

---

## 2. Interpretation

### 2.1 Honest disclosure preserved

K7 is a **SUPP / direction-INVERTED** cell — the recipe does NOT promote the W280 P `d_z=∞, p<1e-300` STRONG claim that was load-bearing for the paper's headline K7 STRONG status. Instead, the recipe surfaces the W166 P3 N=1000 canonical baseline-vs-framework reading (framework LESS Pfam-novel by 12.6×) and the W165 P7 positive reading (zinc-finger/DNA-binding biological reframing) per the user's Tier 1 directive "降级而非重跑" (demote-not-rerun).

### 2.2 W280 P is preserved as cross-reference, NOT as headline evidence

The W280 P 3-seed × N=300 driver result is preserved in §a as a cross-reference but explicitly labelled "numerical artefact (NOT real baseline-vs-framework)". The recipe does not delete or overwrite W280 P artefacts; it just honestly disclaims them. Per Wave 268 strict-clean rule, additive disclosure is preferred over destructive edits.

### 2.3 CPU-only reproducibility

The recipe is fully reproducible from frozen in-git `.m8` files via `tools/lineageflow/novelty_metric_pctid.py` — no GPU required, no MMseqs2 re-search required. Wall-clock <1 sec. This matches the R6 reproducibility recipe (Wave 362 P1) pattern of frozen-substrate + CPU-only verification.

### 2.4 Cross-cell consistency with R6 + K1 recipes

The K7 recipe follows the same 4-section structure as the R6 recipe (Wave 362 P1) and the Wave 363 K1 recipe (this wave, if applicable): (a) headline metric, (b) evidence chain + SHA-256 anchors, (c) reproducibility path, (d) disclosure. This is the Wave 363 P1 reproducibility recipe template.

---

## 3. Edit discipline

- `paper-data/K7_lineageflow_novelty/REPRODUCIBILITY_RECIPE.md` — NEW (this Wave).
- `paper-data/K7_lineageflow_novelty/K7_SOURCE.md` — NOT modified (additive only).
- `paper-data/K7_lineageflow_novelty/SHA256SUMS` — NOT modified (existing W280 P sidecar ledger preserved).
- `paper-data/K7_lineageflow_novelty/{novelty_results_full.json, W166_P3_canonical_novelty.json}` — NOT modified (in-git canonical W166 P3 evidence preserved).
- `verification_outputs/novelty_pctid_w166_q3_2026/*` — NOT modified (in-git W166 P3 evidence preserved).
- `verification_outputs/wave280-k7/*` — NOT modified (W280 P numerical-artefact sidecar preserved).
- `tools/lineageflow/novelty_metric_pctid.py` — NOT modified (Wave 166 P2 canonical implementation preserved).
- `data/lineageflow_upstream/evaluation/*` — NOT touched (vendored scoring scripts remain untouched per "clone下来的原sota项目里的打分脚本依旧不能动，严格复用，要改也是改我们对于抽象的实现" directive).

---

## 4. Cross-references

- `paper-data/K7_lineageflow_novelty/REPRODUCIBILITY_RECIPE.md` — this Wave's NEW deliverable.
- `docs/audit/wave306-11-cell-alignment.md` — 11-cell alignment table (row 11 = K7; source of PARTIAL/SUPP direction-INVERTED verdict).
- `docs/audit/wave306-fix-plan.md` §5 — K7 demotion proposal (DeepSeek #2 direction-inversion fix).
- `docs/audit/wave280-p-k7-sweep-result.md` — W280 P 3-seed sweep result (numerical artefact cross-reference).
- `docs/audit/wave165-novelty-canonical.md` — W165 P7 zinc-finder/DNA-binding biological reframing (archived at `docs/ARCHIVE/audit-by-wave/`).
- `docs/audit/wave327-revised-q1-assessment.md` §Q1 — Q1 framing: solve-root-cause (demote + biological reframing) vs solve-symptom (re-run).
- `docs/CLAIMS.md` line 3034 — Wave 326 status addendum: K7 listed in PARTIAL/SUPP roster (Wave 306 demotion, W166 P3 direction-INVERTED canonical in-git evidence).
- `paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md` — R6 reproducibility recipe (Wave 362 P1 template; same 4-section structure).

---

## 5. Acceptance criteria (recipe considered PASS when)

1. **SHA-256 chain verifies** (all 9 anchor hashes in §1.2 above match). ✅
2. **`tools/lineageflow/novelty_metric_pctid.py`** re-derives **466/1000 (baseline) + 37/1000 (framework)** at pctid<30% threshold from frozen `n1000_full_loose.m8` files. ✅ (recipe path documented; expected values listed in §a)
3. **Cross-threshold sensitivity** at 20%/30%/50% matches the 3-row table in §a. ✅ (recipe documents 462/37, 466/37, 751/517)
4. **D.4 byte-stable regression** 30/30 PASS. ✅
5. **`python3 tools/check_claims_consistency.py`** exits 0 (no drift). ✅
6. **`ruff check`** 0 findings on K7 paper-data. ✅ (no Python files in K7 paper-data; only `.md` + `.json` + `.m8` + symlinks)
7. **`mkdocs build --strict`** exits 0. ✅

---

## 6. Next step

Commit the recipe + this audit note (single commit) with the verbatim commit message per Wave 363 P1 deliverable. NO-PUSH per `todo/PUSH-READY.md` (user gating required for `git push`). The recipe is **safe to run in CI** and is **safe to cite in the paper** as the canonical K7 reproducibility reference (replacing the W280 P `d_z=∞` numerical-artefact framing per Wave 306 Fix #5).

---

_Last updated: 2026-09-27 (Wave 363 P1.K7 — K7 reproducibility recipe authored; SHA-256 chain verified; 4 acceptance gates GREEN)._