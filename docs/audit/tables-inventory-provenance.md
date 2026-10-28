# The internal table inventory does not always match the artifacts it cites

**Date:** 2026-10-28
**Scope:** `tnnls_submission/tables.md`, read against every artifact its rows cite.
**Status:** CPU-only. The frozen submission files were **not** edited.
**Reproducer:** `tools/check_tables_inventory.py` (27 checks, 14 documented drifts,
0 undocumented), `tests/test_tables_inventory.py` (3 tests).

## 0. Why this file exists

`tables.md` opens with a promise:

> All data sourced from `verification_outputs/` with byte-addressable provenance.

It also carries an authority note saying that where a row disagrees with the
manuscript, the manuscript wins, and it flags two known mismatches (Table 1's R1
basis and its old R6 label). That note is correct and important: **the
manuscript and the cover letter are consistent with their artifacts.** What
follows is a defect in the internal inventory, not in the paper.

The inventory is nevertheless shipped inside `tnnls_submission/` and reviewers
will read it as the provenance table. Fourteen rows cannot be reproduced from
the file they point at. Each is listed below with the artifact value.

## 1. Table 2 — the 4-arm d_z values are from a different wave, with the sign dropped

Table 2 cites `verification_outputs/wave230-p2-real-4arm-per-record.csv` and
reports three Bonferroni-significant cells as `framework_WINS`.

| Row | Table 2 says | The cited CSV says | Verdict in CSV |
|---|---:|---:|---|
| vanilla scPerplexity NFE50 | **+0.145** | **−0.9901** | SUPPORTED |
| vanilla scPerplexity NFE100 | **+2.103** | **−0.9746** | SUPPORTED |
| abcache scPerplexity NFE50 | **+0.704** | **−0.0684** | UNDERPOWERED |

Three separate problems:

1. **The magnitudes belong to Wave 229, not Wave 230.** The archived Wave 229
   audit (`docs/ARCHIVE/audit-by-wave/wave229-p1-4arm-per-record.md`) reports
   `−2.082`, `−2.103`, `−0.145` for exactly these three cells. Wave 230 then
   replaced the bootstrap projection with real per-record variance and the
   effects fell to `−0.990`, `−0.975`, `−0.068`
   (`wave230-p2-real-4arm-per-record.md` prints the two columns side by side).
2. **The sign is wrong.** scPerplexity is lower-is-better, so a framework win is
   a *negative* `d_z` — the CSV's `higher_better=False` column says so. Table 2
   writes all three as positive while labelling them `framework_WINS`.
3. **`+0.704` matches neither wave.** It is not in the Wave 229 table, the Wave
   230 table, or any `verification_outputs/` file. The row it sits on
   (`abcache_scPerplexity_NFE50`) is UNDERPOWERED at `−0.0684` in the artifact it
   cites.

The summary line inherits the error:

| Claim | Table 2 | Cited CSV |
|---|---|---|
| cells with `|d_z| < 0.07` | 14/16 | **11/16** |
| Bonferroni-significant | 3/16 | **2/16** |
| significant range | `[0.145, 2.103]` | **`[0.975, 0.990]`** |

The `[0.145, 2.103]` interval is verbatim from
`wave229-p4-integration.md:52`. The correct Wave 230 reading is *two* cells at
`|d_z| ≈ 0.98`, which is a larger effect than 0.145 — the paper is not
weakened by the correction, but the count drops from three to two.

The cover letter already uses the right numbers (`−0.990 / −0.975`, p < 4e-44),
so Table 2 is the only surface in the package that disagrees with the artifact.

## 2. Table 1 — three rows whose numeric cells come from somewhere else

### R2 (Kanzi)

| Cell | Table 1 | Kanzi artifact |
|---|---:|---:|
| baseline RMSD | 0.6146 | **0.9028** |
| framework RMSD | 0.5941 | **0.8838** |
| d_z | +0.3927 | −0.0990 (manuscript) |

`0.6146` is **FlowMol3's framework `fg_dev`** — a different cell, under the old
taxonomy where R2 meant FlowMol3. `0.5941` appears nowhere in the repository.
`+0.3927` is the Wave 235 P2 counterfactual grid-search maximum, whose
`mean_diff` is 0.0763 Å, not the 0.0205 Å implied by `0.6146 − 0.5941`. The
row therefore combines FlowMol3's metric, an unattributed number, and a
counterfactual effect size, and its own note then points at the manuscript's
`−0.0990`. The manuscript (§7.2) is right; the row is not.

### R4 / R5 (2D)

The numbers are correct — `0.5029 → 0.4663` is −7.28 % and `0.6606 → 0.5919`
is −10.40 % — but both `Verification` cells point at directories that do not
exist:

```
verification_outputs/r4_2d_two_moons_w2_m7p28pct/     missing
verification_outputs/r5_2d_eight_gaussians_w2_m10p40pct/  missing
```

The values live in `verification_outputs/g1_deep_dive_q3_2026.json`
(`analysis.per_cell_breakdown`, rows `rectified_flow_2d_sota_two_moons` and
`rectified_flow_2d_sota_eight_gaussians`).
`docs/audit/engineering/headline-evidence.md:22-23` repeats the two dead paths,
so the error is duplicated in a second doc.

### R5b (CIFAR-10 RF)

| Cell | Table 1 | `wave235-p1-r5b-fix.json` |
|---|---:|---:|
| baseline FID | 218.87 | **454.39** |
| framework FID | 122.18 | **442.89** (best of 4, n_rounds=1) |

`218.87 → 122.18` is the v2 FID pair from an earlier wave (a different FID
implementation). The cited artifact is the n=200 Wave 235 P1 rerun on a
different scale. Its four `n_rounds=1` deltas are −1.60 %, −2.53 %, −0.12 %,
−0.66 % — **4/4 negative**, so "3/4 schedulers" understates the result, and the
stated range `[−2.53 %, −0.66 %]` excludes `cosineanneal` (−1.60 %) and
`evidencedriven` (−0.12 %).

### R6 — one note

The row quotes the pooled pLDDT `d_z = +0.1466`, which is the
`uniform_vs_baseline` arm. The file also carries `as_designed_vs_baseline =
+0.1604`. Both are below the pre-registered +0.2235 bar, so the verdict does
not change, but the row should say which arm it quotes.

## 3. Table 3 — four of six rows are correct; the JT rows were not reproducible

| Row | Check |
|---|---|
| TOST `0/16 equivalent`, `14/16 in band` | recomputed from `wave234-p2-tost.csv`, **match** |
| BF01 `9/16 ≥ 10` | recomputed from `wave234-p2-tost.csv`, **match** |
| Meta pooled `+1.117`, CI `[+0.645, +1.589]`, `I² 99.60 %` | recomputed, **match** |
| Non-inferiority `p_NI = 0.9985` | recomputed, **match** |
| JT R2 `z = −10.0`, `p = 9.86e-23` | artifact gives **z = +20.67, p = 3.02e-95** |
| JT R6 `z = −10.7`, `p = 5.11e-25` | artifact gives **z = +21.78, p = 1.86e-105** |

The JT rows carry the pre-fix values (the variance bug fixed in `17de1fa3`), and
their sign is wrong in the same way Table 2's is: the trend is increasing, so
`z > 0`.

**A second defect, now fixed.** The cited CSV
(`wave234-p3-jonckheere.csv`) did **not store** the two quantities Table 3
quotes. The driver computed `jt.z` and `jt.p_asymptotic` and then wrote only
`jt_statistic` and the *permutation* p (floored at 1e-4). The row's numbers were
therefore not reproducible from the file it points at, by construction.
`scripts/wave234_p3_jonckheere.py` now persists `jt_z`, `jt_p_permutation_raw`
and `jt_p_asymptotic`; the regenerated CSV carries
`z = 20.673 / p = 3.017e-95` and `z = 21.778 / p = 1.863e-105`. The previously
stored columns are byte-identical, and no consumer reads the CSV positionally
(`build_verification_manifest.py` and `build_metric_ledger.py` only hash it).

## 4. Table 4 — the wall-clock row mixes two runs

| Cell | Table 4 | Wave 236 (original) | Wave 238 (re-measure) |
|---|---:|---:|---:|
| before | 7.94 s | 7.8122 s | **7.9422 s** |
| after | 1.87 s | 1.8137 s | **1.8737 s** |
| ratio after | 1.26× | **1.26×** | 1.30× |
| speedup | 4.24× | 4.31× | **4.24×** |

The two wall-clock times and the speedup come from the Wave 238 re-measurement;
the ratio column comes from the Wave 236 original. Either pair is internally
consistent; the row as written is not. `framework_baseline_ratio_before = 3.40`
is the same in both runs, so only `ratio_after` is affected.

## 5. Table 5 — two stale numbers

- **Pytest:** the row says `5155 passed / 196 skipped`. The last full run
  recorded before this audit was `5505 passed / 180 skipped / 12 xfailed`.
  A count that moves with every commit should be a pointer to the run, not a
  literal.
- **Abstract word count:** the row says `328 words` and cites
  `docs/drafts/abstract-final.md`. That file states in its own header that it
  is *"Historical working abstract … not the submitted text"*, and it records
  that Wave 244 P3 re-trimmed the body from 328 to 250 words. The abstract of
  record (`paper-A-final.md` §Abstract) is **167 words**. The gate is passing
  for a different reason than the row claims.

The other Table 5 rows (D.4 30/30, mkdocs strict, claims consistency, ruff) are
gates that the chain re-checks; they are fine.

## 6. What is not affected

- The manuscript's R2 (`d_z = −0.0990`, 0.8798 vs 0.9020 Å), R5c
  (24.4839 → 21.3632), R3 (`−0.0377`, p = 0.559, `d_z = −0.401`) and R6
  (`−0.8393` / `+1.1211`) all match their artifacts.
- The cover letter's 4-arm sentence uses the correct `−0.990 / −0.975`.
- No claim, verdict, or status label changes. The corrected Table 2 reading is
  two significant cells at `|d_z| ≈ 0.98` instead of three at
  `|d_z| ∈ [0.145, 2.103]`.

## 7. Reproduction

```
python3 tools/check_tables_inventory.py          # 27 checks, 14 known, 0 unknown
python3 -m pytest tests/test_tables_inventory.py -q
```

The checker recomputes each quantity from the cited artifact's own columns. The
14 current disagreements are listed in `KNOWN_DRIFT` so the run exits 0 while
the frozen file is pending; any *new* drift fails immediately, and
`test_known_drift_list_stays_honest` fails if an entry is left behind after the
row is corrected.

## 8. Authorisation required

`tnnls_submission/tables.md` is frozen. The following edits are one-line
changes per row and would make the inventory reproduce from its artifacts:

1. Table 2: three `d_z` values, the sign, and the three summary counts.
2. Table 1 R2: baseline/framework cells → Kanzi RMSD, or drop the two numeric
   cells and keep the counterfactual `d_z` with its note.
3. Table 1 R4/R5: two `Verification` paths → `g1_deep_dive_q3_2026.json`
   (plus the same fix in `headline-evidence.md`).
4. Table 1 R5b: two FID cells and the `3/4`/range wording.
5. Table 3: four JT cells (z sign and the two p-values).
6. Table 4: pick one run for the whole row.
7. Table 5: replace the pytest literal with a pointer; point the abstract row at
   `paper-A-final.md` and quote 167 words.
