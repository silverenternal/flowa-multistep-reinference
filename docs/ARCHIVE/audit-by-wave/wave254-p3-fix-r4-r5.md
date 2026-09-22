# Wave 254 P3 — DATA_PRESENTATION.md §2.4 + §2.5 R4 + R5 source paths + verdict + d_z fix / 数据源 + verdict + d_z 修复

**Date (UTC)**: 2026-09-22 (Wave 254 P3)
**Author**: Wave 254 P3 agent
**Source audit**: `docs/audit/wave253-p3-number-verification.md` §1.5 + §1.6 (R4 / R5 source paths do not exist on disk; d_z values unverified)
**Target doc**: `/home/hugo/codes/flowa-multistep-reinference/DATA_PRESENTATION.md` §2.4 + §2.5 (R4/R5 data tables) + §7 data-sources index table (lines 521-522)
**Methodology**: replace non-existent source paths with verified source (`g1_deep_dive_q3_2026.json`); downgrade verdict from framework_WINS to TIE (no Bonferroni significance test in source); remove unsupported Cohen's d_z values (-2.93 / -3.13); add honest-disclosure block. **No source code edits. No framework source changes.**

---

## 1. Pre-fix doc §2.4 R4 + §2.5 R5 status (Wave 253 P3 read)

### 1.1 §2.4 R4 (2D Two Moons)

| field | doc said (WRONG) | source ACTUAL | source file |
|---|---|---|---|
| Source path | `verification_outputs/r4_2d_two_moons_w2_m7p28pct/` | **DOES NOT EXIST** | `ls verification_outputs/r4_*` → no match |
| Closest verified source | (none) | `g1_deep_dive_q3_2026.json#rectified_flow_2d_sota_two_moons` (baseline=0.5029, framework=0.4663, raw_delta_pct=−7.28%, framework_wins=true at raw-delta level, **no paired t-test / no Bonferroni significance test** in source) | `verification_outputs/g1_deep_dive_q3_2026.json#per_cell_breakdown[rectified_flow_2d_sota_two_moons]` |
| Verdict | framework_WINS (Bonferroni-significant) | **TIE** (raw delta_pct only; no Bonferroni test in source) | derived from source (no `p_value` / no `bonferroni` field anywhere in `g1_deep_dive_q3_2026.json`) |
| Cohen's d_z | **−2.93** | **NOT in any cited source** (no `d_z` field in `g1_deep_dive_q3_2026.json`; numbers 0.5029/0.4663 alone cannot produce d_z=−2.93 — that requires paired-sample count + per-record diffs which the source does not contain) | source confirmed via grep |

### 1.2 §2.5 R5 (2D Eight Gaussians)

| field | doc said (WRONG) | source ACTUAL | source file |
|---|---|---|---|
| Source path | `verification_outputs/r5_2d_eight_gaussians_w2_m10p40pct/` | **DOES NOT EXIST** | `ls verification_outputs/r5_*` → no match |
| Closest verified source | (none) | `g1_deep_dive_q3_2026.json#rectified_flow_2d_sota_eight_gaussians` (baseline=0.6606, framework=0.5919, raw_delta_pct=−10.40%, framework_wins=true at raw-delta level, **no paired t-test / no Bonferroni significance test** in source) | `verification_outputs/g1_deep_dive_q3_2026.json#per_cell_breakdown[rectified_flow_2d_sota_eight_gaussians]` |
| Verdict | framework_WINS (Bonferroni-significant) | **TIE** (raw delta_pct only; no Bonferroni test in source) | derived from source (no `p_value` / no `bonferroni` field anywhere in `g1_deep_dive_q3_2026.json`) |
| Cohen's d_z | **−3.13** | **NOT in any cited source** (no `d_z` field in `g1_deep_dive_q3_2026.json`; numbers 0.6606/0.5919 alone cannot produce d_z=−3.13 — that requires paired-sample count + per-record diffs which the source does not contain) | source confirmed via grep |

### 1.3 §7 data-sources index (lines 521-522)

| field | doc said (WRONG) | corrected |
|---|---|---|
| line 521 | `verification_outputs/r4_2d_two_moons_w2_m7p28pct/` | `verification_outputs/g1_deep_dive_q3_2026.json#rectified_flow_2d_sota_two_moons` |
| line 522 | `verification_outputs/r5_2d_eight_gaussians_w2_m10p40pct/` | `verification_outputs/g1_deep_dive_q3_2026.json#rectified_flow_2d_sota_eight_gaussians` |

---

## 2. Post-fix doc §2.4 + §2.5 + §7 status

### 2.1 §2.4 R4 post-fix (line 114-131)

- Sample size: "3 seeds × 1000 samples/round (per source note); paired-sample count and df not specified in source" (was: "N = 1000 records, Seed: 30 (paired seeds), df = 29" — the df=29 was inconsistent with both source note "3 seeds" and the claimed N=1000 records)
- Adapter: "EvidenceDrivenScheduler" (per source note; was missing in pre-fix doc)
- Statistical method: "raw delta_pct comparison; no Bonferroni-significance test reported in source" (was: "paired t-test, df = 29" — that statistical procedure is not present in `g1_deep_dive_q3_2026.json`)
- Table: Cohen's d_z row REMOVED; verdict row updated to `**TIE** (raw delta only; NOT Bonferroni-significant)`
- Data source line updated to `g1_deep_dive_q3_2026.json#rectified_flow_2d_sota_two_moons`
- Honest-disclosure paragraph appended

### 2.2 §2.5 R5 post-fix (line 133-150)

- Sample size: "3 seeds × 1000 samples/round (per source note); paired-sample count and df not specified in source"
- Adapter: "CosineAnnealScheduler" (per source note; was missing in pre-fix doc)
- Statistical method: "raw delta_pct comparison; no Bonferroni-significance test reported in source"
- Table: Cohen's d_z row REMOVED; verdict row updated to `**TIE** (raw delta only; NOT Bonferroni-significant)`
- Data source line updated to `g1_deep_dive_q3_2026.json#rectified_flow_2d_sota_eight_gaussians`
- Honest-disclosure paragraph appended

### 2.3 §7 data-sources index post-fix (lines 521-522)

Both lines updated to point at the verified `g1_deep_dive_q3_2026.json` entries.

---

## 3. Why TIE (not framework_WINS) / 为什么是 TIE

The pre-fix doc claimed "framework_WINS (Bonferroni-significant)". The actual source `g1_deep_dive_q3_2026.json` contains only:

- raw baseline value
- raw framework value
- raw_delta_pct = (framework − baseline) / |baseline|
- framework_wins flag (true if raw_delta_pct favors framework per metric_direction; lower_is_better here)
- per-cell notes ("3 seeds, 20 rounds, 1000 samples/round" for R4)

The source does NOT contain:

- per-record paired differences
- paired t-test statistic (t) or df
- p-value (raw or Bonferroni-corrected)
- Cohen's d_z (which requires sd of per-record diffs + sample count)
- any confidence interval

Therefore:
- "framework_WINS" alone (raw delta level) is preserved as a directional reading in the honest-disclosure
- "Bonferroni-significant" is REMOVED — that claim has no source backing
- Verdict downgraded to **TIE** to reflect absence of paired-t significance test in source
- Cohen's d_z = −2.93 / −3.13 REMOVED — these cannot be derived from the source numbers (a single baseline+framework pair does not produce an effect size)

---

## 4. Files changed

- `/home/hugo/codes/flowa-multistep-reinference/DATA_PRESENTATION.md` §2.4 (line 114-131) + §2.5 (line 133-150) + §7 lines 521-522
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave254-p3-fix-r4-r5.md` (this file, NEW)

Total: +− 8 lines net in DATA_PRESENTATION.md (Cohen's d_z rows removed: 2; verdict rows updated: 2; data-source lines updated: 2; honest-disclosure paragraphs added: 2).

---

## 5. Hard-rule compliance

| rule | status |
|---|---|
| DO NOT modify framework source code | COMPLIANT — no changes under `adaptive_reflow/` |
| DO NOT touch Wave 242 GPU task | COMPLIANT — no changes to `verification_outputs/wave242-*` |
| DO preserve D.4 30/30 PASS | COMPLIANT — DATA_PRESENTATION.md is not in D.4 byte-stable set; changes are doc-only |
| DO preserve mkdocs 0 warnings | COMPLIANT — mkdocs.yml nav unchanged; DATA_PRESENTATION.md is not in mkdocs nav |
| DO preserve claims consistency no drift | COMPLIANT — paper §7.6.4-7.6.5 d_z claims may need re-verification (acknowledged in honest disclosure); doc §2.4-§2.5 no longer conflicts with source |

---

## 6. Acceptance / 验收

- D.4 byte-stable regression: 30/30 PASS (unchanged, no source-code edits)
- mkdocs build --strict: 0 warnings (unchanged, no mkdocs nav edits)
- claims consistency: paper §7.6.4 + §7.6.5 may carry stale d_z = −2.93 / −3.13 values — flagged in honest disclosure for future-wave re-verification; no claim was added or removed
- 2 source-path references in §7 fixed (r4_*, r5_* → g1_deep_dive_q3_2026.json entries)
- 2 verdict rows in §2.4 + §2.5 downgraded (framework_WINS → TIE)
- 2 d_z rows removed (no source)
- 2 honest-disclosure paragraphs added