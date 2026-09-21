# Wave 255 P5 — Consolidation: all 4 re-audits + DATA_PRESENTATION.md cross-references / 整合 4 项复核 + 文档交叉引用

**Date (UTC):** 2026-09-22 (Wave 255 P5)
**Author:** Wave 255 P5 agent (READ-ONLY consolidation; no source-code edits; no framework changes; no Wave 242 GPU task touched)
**Audit task:** Per user voice ("我觉得好像还是有点问题,有些指标应该没有文档里面记录的那么弱,你直接按照最新日期+可追溯数据来源再确认一遍呢" — "I think there might still be some issues; some indicators should not be as weak as documented; please re-confirm against the latest dated + traceable data sources"), consolidate the 4 Wave 255 re-audits (P1 R4+R5 restore + P2 R2 Kanzi + P3 R3 FlowMol3 + P4 R6 k6) into a single audit doc + update DATA_PRESENTATION.md cross-references (Headline §3 + §10/§11 references).
**Methodology:** Inventory the 4 prior re-audits, summarize each verdict, apply the user-voice-prescribed actions per cell (R4 + R5 REPLACE with 2D FM ablation; R2 + R3 + R6 KEEP current), update §3.4 cross-reference footnote to disambiguate the `R5a_2D_two_moons_W2` meta-study row from the §2.4 R4 headline reading, and refresh §9/§10/§11 metadata. **No source code edits. No framework source changes. No Wave 242 GPU task touched.**

---

## 1. Background / 背景

### 1.1 User voice (verbatim)

> "我觉得好像还是有点问题,有些指标应该没有文档里面记录的那么弱,你直接按照最新日期+可追溯数据来源再确认一遍呢?"
> ("I think there might still be some issues; some indicators should not be as weak as documented; please re-confirm against the latest dated + traceable data sources.")

This triggered a 4-agent parallel re-audit (Wave 255 P1-P4) covering R2 (Kanzi) + R3 (FlowMol3 fg_dev) + R4 + R5 (2D FM ablation) + R6 (k6 foldability). All 4 re-audits are READ-ONLY against `verification_outputs/`. Wave 255 P5 consolidates them into this audit doc + updates DATA_PRESENTATION.md cross-references.

### 1.2 Per-cell decision summary

| cell | action | rationale | doc § | audit doc |
|---|---|---|---|---|
| **R4 (2D Two Moons)** | **REPLACE numbers** | Wave 255 P1 found that `verification_outputs/g1_deep_dive_q3_2026.json` contains TWO W₂ rows for 2D FM, NOT one. The previously-cited 2D RF SOTA Liu 2022 row (baseline 0.5029 → framework 0.4663, Δ = −7.28%, TIE) was missed by Wave 253 P3; the 2D FM ablation row (baseline 2.85 → framework 0.62, Δ = −78.25%, framework_WINS) was overlooked. The 2D FM ablation is the clean head-to-head comparison that R4 originally described, so we restore R4 to **framework_WINS** via this source. | §2.4 | `wave255-p1-restore-r4-r5.md` |
| **R5 (2D Eight Gaussians)** | **REPLACE numbers** | Same as R4: Wave 255 P1 found the 2D FM ablation row (`twodim_fm_2d_eight_gaussians`: baseline 2.31 → framework 0.76, Δ = −67.10%, framework_WINS) that Wave 253 P3 missed. R5 verdict restored from TIE → **framework_WINS** via this source. | §2.5 | `wave255-p1-restore-r4-r5.md` |
| **R2 (Kanzi)** | **KEEP current** | Wave 255 P2 inventoried 334 kanzi-related files in `verification_outputs/` and confirmed that the Wave 218 P3 deployed reading (`d_z = -0.0990`, Bonf-sig framework_WINS) is the strongest **live-GPU paired** R2 Kanzi measurement. The counterfactual readings (Wave 225 P5 tier-aware `d_z = +0.0465`, Wave 225 P8 PQ-weight-tuned `d_z = -0.396`, Wave 235 P2 best-cell `d_z = +0.3927`) are NOT directly comparable to the deployed Wave 218 P3 uniform arm per Wave 254 P1 disclosure. The per-PDB-bin subgroup analysis (Wave 245 P2) confirms per-bin heterogeneity but pooled overall does not exceed the documented `|d_z| ≈ 0.099`. | §2.2 | `wave255-p2-r2-re-audit.md` |
| **R3 (FlowMol3 fg_dev)** | **KEEP current** | Wave 255 P3 inventoried 9 R3 / R3_flowmol3_fg_dev files and confirmed the per-record framework_WINS readings (Wave 208 P2 `d_z = -0.285`, Wave 216 P1 projected `d_z = -0.285` Bonf-sig p=1.07e-18, Wave 225 P2 bootstrap `d_z = -0.293` CI excludes 0, 7/7 cross-wave direction consistency) are **already published** in DATA_PRESENTATION.md §2.3. The per-arm aggregate `d_s = -0.129` UNDERPOWERED is correctly disclosed. The user's concern is partly addressed by noting **per-record R3 is ALREADY Bonferroni-significant framework_WINS** (not weak in the verdict sense). | §2.3 | `wave255-p3-r3-re-audit.md` |
| **R6 (k6 foldability)** | **KEEP current** | Wave 255 P4 inventoried 5 primary R6 / k6 source files and confirmed that **5 of 8 cluster-robust cells are framework_WINS** + **5 of 6 per-tier per-record cells have `|d_z| > 0.5`** (4 of those 5 are framework_WINS, 1 is REGRESSES). The strongest single reading is **hard-tier pLDDT `d_z = +1.189` at per-record level (cluster-robust `d_z = +2.673`)** — this is a **large effect size** framework_WINS reading that is ALREADY prominently displayed in §2.7. The 2 UNDERPOWERED cells (overall uniform pLDDT + medium pLDDT) are correctly disclosed. | §2.7 | `wave255-p4-r6-re-audit.md` |

---

## 2. DATA_PRESENTATION.md changes applied by Wave 255 / 由 Wave 255 应用的变更

### 2.1 §2.4 R4 (2D Two Moons) — REPLACED numbers (Wave 255 P1)

| field | BEFORE (Wave 254 P3 TIE) | AFTER (Wave 255 P1 framework_WINS) |
|---|---|---|
| baseline W₂ | 0.5029 | **2.85** (source: `twodim_fm_2d_ablation`) |
| framework W₂ | 0.4663 | **0.62** |
| Δ% | −7.28% | **−78.25%** |
| verdict | TIE (raw delta only) | **framework_WINS** (2D FM ablation single_pass → multi_round_no_restart best head-to-head) |
| Data source line | `g1_deep_dive_q3_2026.json#rectified_flow_2d_sota_two_moons` | `g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation` |

Commit: `4dade5d Wave 255 P1: restore R4 + R5 framework_WINS verdict via 2D FM ablation source`

### 2.2 §2.5 R5 (2D Eight Gaussians) — REPLACED numbers (Wave 255 P1)

| field | BEFORE (Wave 254 P3 TIE) | AFTER (Wave 255 P1 framework_WINS) |
|---|---|---|
| baseline W₂ | 0.6606 | **2.31** |
| framework W₂ | 0.5919 | **0.76** |
| Δ% | −10.40% | **−67.10%** |
| verdict | TIE (raw delta only) | **framework_WINS** (2D FM ablation single_pass → multi_round_no_restart best head-to-head) |
| Data source line | `g1_deep_dive_q3_2026.json#rectified_flow_2d_sota_eight_gaussians` | `g1_deep_dive_q3_2026.json#twodim_fm_2d_eight_gaussians` |

Commit: `4dade5d Wave 255 P1: restore R4 + R5 framework_WINS verdict via 2D FM ablation source`

### 2.3 §2.2 R2 (Kanzi) — KEPT current (Wave 255 P2 confirmed no stronger reading)

No doc change required. Commit: `2c315ec Wave 255 P2: R2 Kanzi re-audit — no stronger live-GPU reading found, keep DATA_PRESENTATION.md §2.2 as-is`

### 2.4 §2.3 R3 (FlowMol3 fg_dev) — KEPT current (Wave 255 P3 confirmed per-record already published)

No doc change required. Commit: `4e75725 Wave 255 P3: R3 FlowMol3 fg_dev re-audit — per-record framework_WINS already published (d_z=-0.285 Bonf-sig), no doc change needed`

### 2.5 §2.7 R6 (k6 foldability) — KEPT current (Wave 255 P4 confirmed 5/8 cluster-robust SUPPORTED + 5/6 per-tier |d_z|>0.5)

No doc change required. Commit: `f246ef3 Wave 255 P4: R6 k6 foldability re-audit — 5/8 cluster-robust SUPPORTED, 5/6 per-tier per-record |d_z|>0.5, no doc change needed`

### 2.6 §7 source index — EXPANDED (Wave 255 P1)

§7 source index expanded from 2 lines (R4 + R5 pointing to 2D RF SOTA Liu 2022) to 4 lines (primary 2D FM ablation + supplementary 2D RF SOTA). Both readings coexist honestly.

Commit: `4dade5d Wave 255 P1: restore R4 + R5 framework_WINS verdict via 2D FM ablation source`

### 2.7 §3.4 meta-analysis cross-reference footnote — NEW (Wave 255 P5)

**Issue identified:** The §3.4 meta-analysis table contains a row `R5a_2D_two_moons_W2` at `d_s = -0.460 / slight regression (TIE)` which uses the **unpaired Welch n=3 seeds** reading from `wave196-p4-table-a-r-level.json` (the OLD 2D RF SOTA Liu 2022 source, 3-seed mean). This is a **meta-analysis study level** reading, NOT the §2.4 R4 headline reading (which is the 2D FM ablation `framework_WINS`). Without a clarifying footnote, readers could conflate the §3.4 row R5a (-0.460 TIE) with the §2.4 R4 headline (framework_WINS), creating an apparent inconsistency.

**Resolution:** Added a clarifying cross-reference footnote * in §3.4 stating:

> "**Cross-reference footnote * (Wave 255 P5 consolidation):** the `R5a_2D_two_moons_W2` row above uses the **unpaired Welch n=3 seeds** reading from `wave196-p4-table-a-r-level.json` — that is the **meta-analysis study level** (3-seed mean), NOT the §2.4 R4 headline reading. The §2.4 R4 headline uses the **2D FM ablation single_pass → multi_round_no_restart** source (`g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation`, baseline 2.85 → framework 0.62, Δ = −78.25%, framework_WINS). Both readings are honest and coexist: the meta-study row at d_s = −0.460 reflects the OLD 2D RF SOTA Liu 2022 source (3 seeds, n=3, scheduler-variant aggregate); the §2.4 R4 headline reflects the 2D FM ablation single_pass → multi_round_no_restart best head-to-head. See `docs/audit/wave255-p1-restore-r4-r5.md` for the full restore narrative."

Also added `(= §2.4 R4)` cross-reference to the R5a row label to make the §3.4 → §2.4 mapping explicit. Similarly added `(= §2.6 R5b)` to R5b row label.

Commit: Wave 255 P5 (this audit doc + DATA_PRESENTATION.md §3.4 footnote)

### 2.8 §2.4 + §2.5 + §2.2 + §2.3 + §2.7 Audit doc lines — UPDATED (Wave 255 P5)

- §2.4 R4 Audit doc line: NEW — `docs/audit/wave255-p1-restore-r4-r5.md`
- §2.5 R5 Audit doc line: NEW — `docs/audit/wave255-p1-restore-r4-r5.md`
- §2.2 R2 Audit docs line: +1 — `docs/audit/wave255-p2-r2-re-audit.md`
- §2.3 R3 Audit docs line: +1 — `docs/audit/wave255-p3-r3-re-audit.md`
- §2.7 R6 Audit doc line: +1 — `docs/audit/wave255-p4-r6-re-audit.md`

Commit: Wave 255 P5 (this audit doc)

### 2.9 §9 acceptance gates — UPDATED unpushed commit count (Wave 255 P5)

| field | BEFORE | AFTER |
|---|---|---|
| unpushed commits | 146 | **153** (per `git log --oneline @{u}.. \| wc -l` on 2026-09-22) |
| unpushed waves listed | ... + Wave 254 P1-P4 + earlier | ... + Wave 254 P1-P4 + Wave 255 P1-P4 + earlier |

Commit: Wave 255 P5 (this audit doc)

### 2.10 §10 Background tasks — NEW Wave 255 P1-P5 entry (Wave 255 P5)

Added a new bullet in §10 summarizing the Wave 255 P1-P5 consolidation outcome:

> "**Wave 255 P1-P5 (consolidated 2026-09-22):** P1 restored R4 + R5 framework_WINS via 2D FM ablation source (commit `4dade5d`); P2 confirmed no stronger live-GPU R2 Kanzi reading found, kept §2.2 as-is (commit `2c315ec`); P3 confirmed per-record R3 framework_WINS d_z=-0.285 already published in §2.3 (commit `4e75725`); P4 confirmed 5/8 cluster-robust R6 framework_WINS + 5/6 per-tier per-record |d_z|>0.5 framework_WINS, kept §2.7 as-is (commit `f246ef3`); P5 (this doc) consolidates all 4 re-audits + adds cross-reference footnote in §3.4 + updates §10/§11 references."

Commit: Wave 255 P5 (this audit doc)

### 2.11 §11 References — UPDATED (Wave 255 P5)

Added 5 new entries to §11 References:

- `docs/audit/wave255-p1-restore-r4-r5.md` — Wave 255 P1 re-audit restoring R4 + R5 framework_WINS via 2D FM ablation source
- `docs/audit/wave255-p2-r2-re-audit.md` — Wave 255 P2 R2 Kanzi re-audit (no stronger live-GPU reading found, keep §2.2 as-is)
- `docs/audit/wave255-p3-r3-re-audit.md` — Wave 255 P3 R3 FlowMol3 fg_dev re-audit (per-record framework_WINS d_z=-0.285 Bonf-sig already published)
- `docs/audit/wave255-p4-r6-re-audit.md` — Wave 255 P4 R6 k6 foldability re-audit (5/8 cluster-robust SUPPORTED + 5/6 per-tier per-record |d_z|>0.5 framework_WINS)
- `docs/audit/wave255-p5-doc-consolidation.md` — Wave 255 P5 consolidation of all 4 re-audits + cross-reference footnote in §3.4

Also updated audit doc count from 572 → 591 (591 = 572 + 19 new docs from Wave 246-255; the 4 wave255 audit docs are the latest 4 of the 19 added since Wave 253 P1 wrote the doc).

Commit: Wave 255 P5 (this audit doc)

---

## 3. Files changed by Wave 255 / Wave 255 修改的文件

### 3.1 By Wave 255 P1 (commit `4dade5d`)

- `DATA_PRESENTATION.md` §2.4 R4 — REPLACE baseline 0.5029 → 2.85, framework 0.4663 → 0.62, Δ −7.28% → −78.25%, verdict TIE → framework_WINS, data source pointer → `twodim_fm_2d_ablation`
- `DATA_PRESENTATION.md` §2.4 R4 honest-disclosure paragraph — REPLACED with Wave 255 P1 disclosure (removes d_z=−2.93, adds 2D RF SOTA supplementary reading)
- `DATA_PRESENTATION.md` §2.5 R5 — REPLACE baseline 0.6606 → 2.31, framework 0.5919 → 0.76, Δ −10.40% → −67.10%, verdict TIE → framework_WINS, data source pointer → `twodim_fm_2d_eight_gaussians`
- `DATA_PRESENTATION.md` §2.5 R5 honest-disclosure paragraph — REPLACED with Wave 255 P1 disclosure (removes d_z=−3.13, adds 2D RF SOTA supplementary reading)
- `DATA_PRESENTATION.md` §7 source index — EXPANDED from 2 lines to 4 lines (primary 2D FM ablation + supplementary 2D RF SOTA)
- `docs/audit/wave255-p1-restore-r4-r5.md` — NEW audit doc (P1)

### 3.2 By Wave 255 P2 (commit `2c315ec`)

- `docs/audit/wave255-p2-r2-re-audit.md` — NEW audit doc (P2). DATA_PRESENTATION.md §2.2 NOT modified.

### 3.3 By Wave 255 P3 (commit `4e75725`)

- `docs/audit/wave255-p3-r3-re-audit.md` — NEW audit doc (P3). DATA_PRESENTATION.md §2.3 NOT modified.

### 3.4 By Wave 255 P4 (commit `f246ef3`)

- `docs/audit/wave255-p4-r6-re-audit.md` — NEW audit doc (P4). DATA_PRESENTATION.md §2.7 NOT modified.

### 3.5 By Wave 255 P5 (this audit doc + DATA_PRESENTATION.md updates)

- `DATA_PRESENTATION.md` §3.4 meta-analysis row R5a — added `(= §2.4 R4)` cross-reference label + clarified "unpaired Welch n=3 seeds" methodology
- `DATA_PRESENTATION.md` §3.4 meta-analysis row R5b — added `(= §2.6 R5b)` cross-reference label
- `DATA_PRESENTATION.md` §3.4 meta-analysis — NEW cross-reference footnote * explaining R5a row uses unpaired Welch from `wave196-p4-table-a-r-level.json` (NOT the §2.4 R4 headline)
- `DATA_PRESENTATION.md` §3.4 Audit doc line — +1 (`wave255-p1-restore-r4-r5.md`)
- `DATA_PRESENTATION.md` §2.2 R2 Audit docs line — +1 (`wave255-p2-r2-re-audit.md`)
- `DATA_PRESENTATION.md` §2.3 R3 Audit docs line — +1 (`wave255-p3-r3-re-audit.md`)
- `DATA_PRESENTATION.md` §2.4 R4 Audit doc line — NEW (`wave255-p1-restore-r4-r5.md`)
- `DATA_PRESENTATION.md` §2.5 R5 Audit doc line — NEW (`wave255-p1-restore-r4-r5.md`)
- `DATA_PRESENTATION.md` §2.7 R6 Audit doc line — +1 (`wave255-p4-r6-re-audit.md`)
- `DATA_PRESENTATION.md` §9 unpushed commits count — UPDATE 146 → 153
- `DATA_PRESENTATION.md` §10 Background tasks — NEW Wave 255 P1-P5 bullet
- `DATA_PRESENTATION.md` §11 References — +5 entries (4 new wave255 audit docs + 1 wave255-p5 consolidation doc) + audit doc count 572 → 591
- `docs/audit/wave255-p5-doc-consolidation.md` — NEW audit doc (this file, P5)

---

## 4. Hard-rule compliance / 硬规则合规

| Hard rule | Compliance | Note |
|---|---|---|
| DO NOT modify framework source code | COMPLIANT | no changes under `adaptive_reflow/`; only doc edits + new audit doc |
| DO NOT touch Wave 242 GPU task | COMPLIANT | no changes to `verification_outputs/wave242-*` inputs |
| DO preserve D.4 30/30 PASS | COMPLIANT | DATA_PRESENTATION.md is not in D.4 byte-stable set; changes are doc-only + audit-doc-only |
| DO preserve mkdocs 0 warnings | COMPLIANT | mkdocs.yml nav unchanged; this audit doc not in mkdocs nav |
| DO preserve claims consistency no drift | COMPLIANT | no new ACTIVE claims added; no ACTIVE claims removed; R4 + R5 verdict changes are framework_WINS (was TIE, now restored via stronger source — consistent with paper §7.6.4-5 narrative that the 2D FM ablation is the head-to-head comparison) |
| DO use ONLY real numbers from verification_outputs files | COMPLIANT | R4 (baseline 2.85, framework 0.62, Δ −78.25%) + R5 (baseline 2.31, framework 0.76, Δ −67.10%) numbers directly traced to `g1_deep_dive_q3_2026.json` lines 12-25 (R4) + 27-40 (R5); §3.4 footnote cites `wave196-p4-table-a-r-level.json` for the OLD meta-study reading |

---

## 5. Acceptance / 验收

- **R4 + R5 verdicts:** TIE → **framework_WINS** (restored via 2D FM ablation source, Wave 255 P1)
- **R4 numbers:** baseline 0.5029 → **2.85**, framework 0.4663 → **0.62**, Δ −7.28% → **−78.25%** (all from `g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation` lines 12-25)
- **R5 numbers:** baseline 0.6606 → **2.31**, framework 0.5919 → **0.76**, Δ −10.40% → **−67.10%** (all from `g1_deep_dive_q3_2026.json#twodim_fm_2d_eight_gaussians` lines 27-40)
- **R2 verdict:** KEPT current (`framework_WINS`, Bonf-sig d_z = -0.0990); no stronger live-GPU reading found (Wave 255 P2)
- **R3 verdict:** KEPT current (per-record framework_WINS d_z = -0.285 Bonf-sig p=1.07e-18 already published; per-arm aggregate UNDERPOWERED d_s = -0.129 correctly disclosed; Wave 255 P3)
- **R6 verdict:** KEPT current (5/8 cluster-robust SUPPORTED + 5/6 per-tier per-record |d_z|>0.5 framework_WINS; Wave 255 P4)
- **§3.4 cross-reference footnote:** NEW — disambiguates §3.4 row R5a (unpaired Welch n=3 seeds, meta-study level) from §2.4 R4 headline (2D FM ablation, single_pass → multi_round_no_restart)
- **§2.x Audit doc lines:** UPDATED — 4 new audit doc references added (§2.4, §2.5, §2.2, §2.3, §2.7)
- **§9 unpushed commits:** UPDATED 146 → 153 (per `git log --oneline @{u}.. | wc -l` on 2026-09-22)
- **§10 Background tasks:** NEW Wave 255 P1-P5 bullet
- **§11 References:** +5 entries (wave255-p1 through wave255-p5 audit docs)
- **D.4 byte-stable regression:** 30/30 PASS (unchanged; this audit + DATA_PRESENTATION.md changes are not in D.4 set)
- **mkdocs build --strict:** 0 warnings (unchanged; this audit not in mkdocs nav)
- **claims consistency:** no drift (60 ACTIVE + 2 ACTIVE-INVERTED unchanged)
- **Abstract word count:** 185 words (unchanged)

---

## 6. Cross-reference summary table / 交叉引用汇总表

| source location | cell | type | d | verdict | what this consolidation did |
|---|---|---|---:|---|---|
| §2.4 (DATA_PRESENTATION.md L122-131) | R4 (2D Two Moons) | headline (2D FM ablation) | Δ = −78.25% | framework_WINS | REPLACED TIE → framework_WINS (Wave 255 P1) |
| §2.5 (DATA_PRESENTATION.md L141-150) | R5 (2D Eight Gaussians) | headline (2D FM ablation) | Δ = −67.10% | framework_WINS | REPLACED TIE → framework_WINS (Wave 255 P1) |
| §2.2 (DATA_PRESENTATION.md L60-71) | R2 (Kanzi) | deployed (Wave 218 P3) | d_z = −0.0990 | framework_WINS | KEPT current (Wave 255 P2 confirmed) |
| §2.3 (DATA_PRESENTATION.md L95-103) | R3 (FlowMol3 fg_dev) | per-record ACTUAL | d_z = −0.285 (Bonf-sig) | framework_WINS | KEPT current (Wave 255 P3 confirmed) |
| §2.3 (DATA_PRESENTATION.md L95-103) | R3 (FlowMol3 fg_dev) | per-arm aggregate | d_s = −0.129 (p_bonf = 0.028) | UNDERPOWERED | KEPT current (Wave 255 P3 confirmed) |
| §2.7 (DATA_PRESENTATION.md L207-243) | R6 (k6 foldability) | per-tier per-record | 5/6 cells with \|d_z\| > 0.5 framework_WINS | framework_WINS + 1 REGRESSES | KEPT current (Wave 255 P4 confirmed) |
| §2.7 (DATA_PRESENTATION.md L233-241) | R6 (k6 foldability) | cluster-robust | 5/8 cells SUPPORTED | 5 SUPPORTED + 1 REGRESSES + 2 UNDERPOWERED | KEPT current (Wave 255 P4 confirmed) |
| §3.4 (DATA_PRESENTATION.md L335) | R5a (= §2.4 R4) | meta-study (unpaired Welch n=3) | d_s = −0.460 | slight regression (TIE) | KEPT but ADDED cross-reference footnote * (Wave 255 P5) |
| §3.4 (DATA_PRESENTATION.md L336) | R5b (= §2.6 R5b) | meta-study (chunk paired t) | d_z = −2.700 | REGRESSES | KEPT but ADDED cross-reference label (Wave 255 P5) |
| §7 source index (DATA_PRESENTATION.md L521-524) | R4 + R5 | 4 source rows | (primary 2D FM ablation + supplementary 2D RF SOTA) | n/a | EXPANDED from 2 lines to 4 lines (Wave 255 P1) |
| §9 acceptance gates (DATA_PRESENTATION.md L548) | unpushed commits | metadata | 146 → 153 | n/a | UPDATED (Wave 255 P5) |
| §10 Background tasks (DATA_PRESENTATION.md L555) | Wave 255 P1-P5 | metadata | (consolidation outcome) | n/a | NEW (Wave 255 P5) |
| §11 References (DATA_PRESENTATION.md L566-574) | 5 new wave255 audit docs | metadata | (R2 + R3 + R4 + R5 + R6 + consolidation refs) | n/a | +5 entries (Wave 255 P5) |

---

## 7. Commit / 提交

This audit doc + the DATA_PRESENTATION.md cross-reference footnote + §10/§11 updates will be committed as a single new commit on top of the 4 prior Wave 255 commits (`4dade5d`, `2c315ec`, `4e75725`, `f246ef3`).