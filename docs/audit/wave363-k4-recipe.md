# Wave 363 P1 — K4 LineageFlow HMMER length-bias_long reproducibility recipe

**Branch:** main
**Date:** 2026-09-27
**Headline metric (K4 POWERED at metric-collection level):** `hmmscan_total_hits` 12-22 hits / 100 records non-zero across all 3 seeds (coverage 12-22% at 200-300 AA range). The pre-Wave-280 K4 STATISTICAL-underpowered status is resolved.
**Headline metric (K5 paired delta on K4 substrate, NOT_SIGNIFICANT at strict Bonferroni):** mean Δ = +1.33 hits (+8.9%), Cohen's d_z = +1.15, raw p_value = 0.184, Bonferroni p_bonf = 0.734 at α=0.0125 (m=4 metrics). The 3-seed paired-seeds design (d_f=2) is structurally underpowered for paired t-tests.
**Scope:** Author `paper-data/K4_k5_lineageflow_hmmer/REPRODUCIBILITY_RECIPE.md` (NEW ~185-line doc, 4 sections a-d) per the Wave 363 P1 reproducibility-recipe pattern (mirrors Wave 362 P1 R6 recipe + Wave 363 P1 R5c recipe formats).

---

## 1. Observed Facts

1. **NEW file created:** `paper-data/K4_k5_lineageflow_hmmer/REPRODUCIBILITY_RECIPE.md` (185 lines, 4 sections: a Headline metric, b Evidence chain + SHA-256 anchors, c Reproducibility path, d Disclosure).
2. **SHA-256 chain verified at recipe authorship (2026-09-27):**
   - `verification_outputs/wave280-p-k4k5/summary_n100.json` = `f382c79a209c29fe5115d83fc646d0321102a8f11176eb6aeac959410ddc71a3` (matches `summary_n100.json` line 1 of the canonical SHA256SUMS ledger).
   - `verification_outputs/wave280-p-k4k5/SHA256SUMS` = `906420fb95c24cd316ba904102b2e21c69f82f6ab358d0be9ff009ca6a0c4f4a`.
   - 17 anchor files (3 seeds × 6 artefacts: `manifest.json` + `baseline_n100.fasta` + `framework_n100.fasta` + `baseline/hmmscan.tbl` + `framework/hmmscan.tbl`) all carry their canonical SHA-256 from the 44-line `SHA256SUMS` ledger.
   - `sha256sum --check SHA256SUMS` returns **43 OK + 1 FAILED** (the FAILED is the SHA256SUMS self-referential line, which is expected and not a corruption).
3. **Headline numbers from `summary_n100.json`:** k4k5_status="PASS", sweep_name="wf280_k4k5_3seed_n100", seeds_run=3, n_records_per_seed=100, flags={"upstream_eval_len_bias": "long", "lineageflow_prior_mix": 1.0}, elapsed_total_s=124.01. Per-seed: (42, baseline=20, framework=22, Δ=+2), (43, baseline=12, framework=14, Δ=+2), (44, baseline=13, framework=13, Δ=0). Aggregate: mean_delta=1.3333, std_paired=1.1547, t=2.0, d_f=2, p_value=0.1835, d_z=1.1547, m_tests=4, bonferroni_p_values=[0.7340, 0.7340, 0.7340, 0.7340].
4. **Verified provenance anchors:**
   - `docs/audit/wave280-p-k4k5-sweep-result.md` §3.2 (aggregate statistics table) — matches `summary_n100.json` byte-for-byte on mean_delta, std_paired, t, d_f, p_value, d_z, m_tests, p_bonf.
   - `docs/CLAIMS.md` CLM-060 line 3031 (Wave 280 P status addendum, preserved verbatim across Wave 306 demotion + Wave 326 cross-doc-snapshot): "K4 POWERED (hit-counts 12-22/100 records non-zero across all 3 seeds) + K5 SUPPORTS-WITH-CAVEAT (mean delta +1.33 hits / +8.9%, d_z=1.15, raw p=0.184 not significant at α=0.05 due to d_f=2; Bonferroni p=0.734 not significant at α=0.0125 due to n=3 paired-seeds design)".
5. **Pre-flight guard-rails GREEN:**
   - `python3 -m pytest tests/test_d4_regression_vectors.py -q` → **30 passed, 3 warnings in 5.04s** (D.4 30/30 PASS).
   - `python3 tools/check_claims_consistency.py` → **No drift detected** (61 active claims, 0 provisional, 2 deprecated; CLM-040 forced PROVISIONAL by Disputed-by citation, pre-existing).
   - `ruff check adaptive_reflow/ tests/ scripts/ tools/` → **All checks passed!** (0 findings).
   - `mkdocs build --strict` → **Documentation built in 30.43 seconds** (INFO-only mkdocs-material license warning, not a build error).
6. **Recipe doc SHA-256:** `50a1a8a512e7df8df1926fe50081fa4b6ca1b5d26ce671fe783cfa4ed18d932b` (of the NEW `paper-data/K4_k5_lineageflow_hmmer/REPRODUCIBILITY_RECIPE.md` itself, for downstream audit trail).

---

## 2. Interpretation

The K4 cell's POWERED status + K5 paired delta's NOT_SIGNIFICANT-at-Bonferroni status are both honest disclosures per Wave 268 strict-clean rule + Wave 268 hard guardrail #4 ("Never promote UNDERPOWERED/DEFERRED/REGRESSES/NOT_SIGNIFICANT to SUPPORTED by wording alone"). The recipe doc makes this two-cell distinction explicit in section (a) and section (d): the K4 metric-collection path is non-degenerate (12-22 hits / 100 records non-zero across all 3 seeds), and the K5 framework-vs-baseline paired delta is visible (+8.9%) but does not reach strict Bonferroni significance at α=0.0125 due to the n=3 paired-seeds design.

The recipe's reproducibility path is **CPU-only** (no GPU required): all aggregate statistics are re-derivable from `summary_n100.json` in <1 second; per-record raw counts are re-derivable from the per-seed `hmmscan.tbl` files via `grep -c '^[^#]'` in seconds. The wall-clock for the canonical 3-seed × N=100 sweep is 124.01 seconds (≈ 20 sec per (seed, arm) for hmmscan `--cpu 4 --noali --tblout --acc`). Per Wave 280 P §6 edit discipline: 0 vendored files touched (`data/lineageflow_upstream/databases/pfam35/Pfam-A.hmm` + `data/lineageflow_upstream/evaluation/*.py` unchanged); 0 project-owned files touched in the K4K5 branch (`tools/gen_lineageflow_n1000_fastas.py` + `tools/upstream_eval.py` unchanged at the Wave 276 P state); sweep driver lived in `/tmp/wf280_k4k5_n100_driver.py` and was NOT committed per "claude相关的确实不要commit" directive.

The task description suggested numbers (cluster-robust d_z=+0.84, p_bonf=0.009 at K-level α=0.0125) do NOT appear in the verified evidence artifacts (`verification_outputs/wave280-p-k4k5/summary_n100.json` + `docs/audit/wave280-p-k4k5-sweep-result.md` + `docs/CLAIMS.md` CLM-060 line 3031). Per Wave 363 P1 explicit directive "never fabricate numbers — only anchor to verified artifacts" + Wave 268 hard guardrail #4, the recipe doc anchors to the verified d_z=+1.15 + p_bonf=0.734 values (which are the actual aggregate statistics for the K5 paired delta on the K4 substrate). The K4 cell's headline is the hit-count range (POWERED at metric-collection level), NOT a d_z/p_bonf claim.

---

## 3. ADDITIVE changes (preserved per Wave 268 strict-clean)

- `paper-data/K4_k5_lineageflow_hmmer/REPRODUCIBILITY_RECIPE.md` — NEW ~185-line doc. No existing files in `paper-data/K4_k5_lineageflow_hmmer/` were modified (per "never modify existing paper-data files" guardrail).
- `paper-data/K4_k5_lineageflow_hmmer/K4_k5_SOURCE.md` — NOT modified (preserved verbatim at Wave 280 P state).
- `verification_outputs/wave280-p-k4k5/*` — NOT modified (frozen at Wave 280 P 2026-09-22 state; SHA-256 chain verified at recipe authorship).
- `docs/CLAIMS.md` — NOT modified (CLM-060 line 3031 Wave 280 P status addendum preserved verbatim).
- `docs/audit/wave280-p-k4k5-sweep-result.md` — NOT modified (canonical provenance doc, preserved verbatim at Wave 280 P state).
- `docs/audit/wave280-final.md` — NOT modified (Wave 280 P final consolidation, preserved verbatim).
- `tools/check_claims_consistency.py` — NOT modified (still PASSES with 61 active / 0 provisional / 2 deprecated).
- `tests/test_d4_regression_vectors.py` — NOT modified (still 30/30 PASS).
- No vendored files modified (Pfam DB + LineageFlow evaluation scripts unchanged per "clone下来的原sota项目里的打分脚本依旧不能动" directive).

---

## 4. Verification gates

| Gate | Status | Evidence |
|---|---|---|
| D.4 30/30 PASS | PASS | `python3 -m pytest tests/test_d4_regression_vectors.py -q` → 30 passed, 3 warnings in 5.04s |
| claims consistency PASS | PASS | `python3 tools/check_claims_consistency.py` → No drift detected |
| ruff 0 findings | PASS | `ruff check adaptive_reflow/ tests/ scripts/ tools/` → All checks passed! |
| mkdocs strict PASS | PASS | `mkdocs build --strict` → Documentation built in 30.43 seconds (INFO-only license warning, not a build error) |
| SHA-256 chain verified | PASS | 17 anchor files + summary_n100.json + SHA256SUMS ledger verified at recipe authorship |
| Edit discipline (no existing files modified) | PASS | only NEW file added: `paper-data/K4_k5_lineageflow_hmmer/REPRODUCIBILITY_RECIPE.md` |
| NO-PUSH policy honored | PASS | commit-and-stop; no `git push` invoked |

---

## 5. Acceptance criteria

The K4 reproducibility recipe is considered PASS when:

1. `paper-data/K4_k5_lineageflow_hmmer/REPRODUCIBILITY_RECIPE.md` exists, is ~120-line or longer (185 lines), and has 4 sections a-d covering (a) headline metric, (b) evidence chain + SHA-256 anchors, (c) reproducibility path, (d) disclosure.
2. SHA-256 chain verifies: `verification_outputs/wave280-p-k4k5/summary_n100.json` hash matches `f382c79a209c29fe5115d83fc646d0321102a8f11176eb6aeac959410ddc71a3`; the 17 anchor files (3 seeds × 6 artefacts) match their canonical SHA-256 from the `SHA256SUMS` ledger.
3. Python re-derivation snippet reproduces the aggregate statistics from `summary_n100.json` byte-for-byte (mean_delta=1.3333, std_paired=1.1547, d_z=1.1547, raw p_value=0.1835, p_bonf=0.7340).
4. D.4 30/30 PASS + claims PASS + ruff 0 + mkdocs strict PASS (all 4 verified at recipe authorship).
5. Honest disclosure: K4 = POWERED (metric-collection level); K5 paired delta = NOT_SIGNIFICANT at strict Bonferroni α=0.0125 (sample-size limitation honestly disclosed; promotion to STRONG/STRONG-with-caveat requires n≥7 paired seeds per Wave 280 P §8 option 1).

The recipe is **safe to run in CI** — no GPU required, all artefacts are read-only, the Python re-derivation is <1 sec.

---

## 6. Honored directives

| Directive | How honored |
|---|---|
| Wave 363 P1 K4 reproducibility recipe | NEW `paper-data/K4_k5_lineageflow_hmmer/REPRODUCIBILITY_RECIPE.md` (~185 lines, 4 sections a-d, K4 POWERED + K5 NOT_SIGNIFICANT-Bonferroni disclosure) |
| "never fabricate numbers — only anchor to verified artifacts" | All numbers anchored to `summary_n100.json` + `docs/audit/wave280-p-k4k5-sweep-result.md` + `docs/CLAIMS.md` CLM-060 line 3031. The task's suggested cluster-robust d_z=+0.84 / p_bonf=0.009 values (which do not appear in any verified artifact) are NOT used; the verified d_z=1.15 / p_bonf=0.734 values are used instead. |
| Wave 268 strict-clean rule (status history additive, no removal; reframing wording instead of changing numbers) | Recipe section (d) distinguishes K4 POWERED (verbatim from CLM-060 line 3031) from K5 NOT_SIGNIFICANT-Bonferroni (verbatim from CLM-060 line 3031). No number is re-framed or changed. |
| Wave 268 hard guardrail #4 (never promote UNDERPOWERED/DEFERRED/REGRESSES/NOT_SIGNIFICANT to SUPPORTED) | K4 status is POWERED (not SUPPORTED — POWERED is the metric-collection-level label, distinct from SUPPORTED). K5 paired delta is NOT_SIGNIFICANT at strict Bonferroni, NOT promoted to SUPPORTED by wording. |
| "never modify existing paper-data files" | No existing files in `paper-data/K4_k5_lineageflow_hmmer/` were modified; only the NEW `REPRODUCIBILITY_RECIPE.md` was added. |
| NO-PUSH policy | Commit-and-stop; no `git push` invoked. |
| Vendored file sacredness | 0 vendored files touched (Pfam DB + LineageFlow evaluation scripts unchanged). |
| ADDITIVE only | Only 1 NEW file added (`paper-data/K4_k5_lineageflow_hmmer/REPRODUCIBILITY_RECIPE.md`); no existing files modified. |

---

## 7. Next step

The K4 cell's POWERED status + K5 paired delta's NOT_SIGNIFICANT status are the canonical honest disclosures for the LineageFlow HMMER length-bias_long cell as of Wave 280 P (2026-09-22). Per Wave 280 P §8 next-step analysis, the K5 promotion to STRONG would require either (1) n≥7 paired seeds to push d_f above 5, (2) a per-record paired design, or (3) Wave 22 rubric revision. None of these are within the scope of this Wave 363 P1 recipe-authoring task.

The recipe is **complete and verified**. Future waves may author the n≥7 sweep (option 1) to promote K5 to STRONG/STRONG-with-caveat under Wave 22 metric-rev3 rubric; this would be a separate research-scope wave, not a recipe-authoring wave.

---

_Last updated: 2026-09-27 (Wave 363 P1 — K4 reproducibility recipe authored; SHA-256 chain verified + 4/4 gates PASS + honest K4 POWERED + K5 NOT_SIGNIFICANT-Bonferroni disclosure)._
