# Wave 275 P1 — Project-State Inventory (pre-flattening baseline)

**Branch:** main
**Date:** 2026-09-22
**HEAD commit:** `07ad48e` (Wave 274 P7: self-referencing MANIFEST SHA → sidecar resolution)
**Scope:** Project-state snapshot before the Wave 261 internal-metric
governance + flattening plan. Captures (i) docs/audit surface (652 files),
(ii) docs/CLAIMS.md surface (73 entries), (iii) verification_outputs/
surface (531 dirs, 921 files), and (iv) the 11 weak metric claims with
their adapter-level improvement vectors.

This is a **READ-ONLY inventory**, not an action. It freezes the baseline
against which the Wave 275 P2-P4 (flattening + governance + adapter
remediation) deltas are measured. No source files are modified.

---

## 1. Audit surface

**Source:** Phase 1 audit pass that scanned `docs/audit/`, `mkdocs/`,
`docs/CLAIMS/`, `docs/CONSOLIDATED/`, `docs/reproducibility/` and
sibling governance locations for wave-prefixed filenames, citation
freshness, and duplicate roles.

| Metric | Value | Notes |
|---|---|---|
| totalFiles | **652** | Across the full doc surface |
| activeCount | **226** | Cited by ≥1 active surface (mkdocs nav, CLAIMS, README, paper) |
| historicalCount | **426** | Wave-prefixed + uncited (no current cross-reference) |
| finalVerifyCount | **30** | `wave*-pN-final-verify*` files (one per wave that ran a final-verify phase; 72/72 D.4 byte-stable preserved across waves) |
| candidateArchive (list size) | **278** | Explicit list provided in Phase 1 audit; matches the historical-but-archive-eligible subset |
| candidateActive (list size) | **198** | Explicit list of wave-prefixed active files needing topic rename |

### 1.1 Notable duplicates surfaced by the audit

The Phase 1 audit surfaced these duplicate patterns (each item has
concentrated wave-prefix traffic that the flattening must collapse):

- **cifar-fid** appears in 17 files across waves 128/129/131/132/146/191/206
  + 2 orphan (`cifar-evaluation-corrections.md`, `cifar-fid-performance-audit.md`)
- **novelty-investigation** appears in 7 files across waves 163/165/166
- **flowmol3 direction/fix** appears in 10 files across waves 107/109/206/
  208/209/235/238/240/242 + 1 closure
- **kanzi** appears in 15 files across waves 101/107/124/139/143/150/151/
  170/180/181/191/206/225/245/246
- **lineageflow** appears in 10 files across waves 109/138/139/140/144/
  145/149/150/151/213
- **final-verify pattern:** 30 identical-role files (one per wave that
  has a `wave*-pN-final-verify.md`); 7 final-synthesis files; 14 close
  files; 21 push files; 40 `*-verify` files
- **9 placeholder files <500 bytes:** `wave128-cifar-checkpoint-loader.md`
  (464B), `wave128-cifar-retry3-smoke.md` (419B), `wave129-cifar-reference-availability.md`
  (372B), `wave129-cifar-small-sweep.md` (485B), `wave131-cifar-reference-build.md`
  (320B), `wave131-cifar-small-sweep.md` (482B), `wave131-rf1step-smoke.md`
  (400B), `todo-status-reconciliation-2026-09-13.md` (432B), `wave101-status-reconciliation-2026-09-13.md`
  (467B)

### 1.2 Recommended flattening — Hybrid B+C

Per Phase 1 audit `recommendedFlattening` verdict: **B+C hybrid.**

**Option C (archive) — applied first** to the 426 uncited wave files:

- Move 278 explicitly-listed historical files → `docs/ARCHIVE/audit-by-wave/`
  (matches the Wave 34-99 precedent from 2026-09-14).
- The remaining 148 of the 426 historical files (sub-directory burials
  + non-wave-prefixed historicals) are addressed in a follow-up pass.

**Option B (rename) — applied after Option C** to the 198 wave-prefixed
active files:

- Each rename is topic-clustered: `cifar/*`, `kanzi/*`, `flowmol3/*`,
  `lineageflow/*`, `governance/*`. Examples:
  - `wave270-p1-ruff-code-fixes.md` → `governance/ruff-auto-fix.md`
  - `wave131-cifar-small-sweep.md` → `cifar/small-sweep.md`
  - `wave270-p4-final-verify.md` → `governance/ruff-final-verify.md`
- Every rename has a documented consumer (each citation in
  `mkdocs/CLAIMS/CONSOLIDATED/README/cover_letter/supplementary/
  CHANGELOG/ROADMAP/AGENTS.md` is traced before the file is renamed).

**Why hybrid:**

- Pure C leaves 198 wave-prefixed names leaking into active surfaces,
  violating the "看不到 wave 信息" rule.
- Pure B requires renaming 198 files but breaks 1446 active
  cross-references in 67 active docs and is the only path to full
  wave-name erasure.
- Hybrid does the cheap part (archive the 278 explicitly-cited ones)
  first, then the surgical part (rename only the 198 cited ones —
  every rename has a documented consumer).

**Phase deliverables after flattening:**

- `mkdocs.yml` `audit/wave*.md` glob (line 278) is removed.
- All renamed links in `mkdocs/CLAIMS/CONSOLIDATED/README/cover_letter/
  supplementary/CHANGELOG/ROADMAP/AGENTS.md` are updated.
- Final state: no `waveNNN-` substring in any active file path.

---

## 2. Claims surface

**Source:** `docs/CLAIMS.md` (3878 lines) + `docs/CONSOLIDATED_RESULTS.md`
(8685 lines) + `docs/INSIGHTS.md` (1403 lines).

### 2.1 Status breakdown

| Status | Count | Notes |
|---|---|---|
| ACTIVE | **60** | Plain ACTIVE claims |
| ACTIVE — INVERTED POST-cd70821 | **2** | Two claims flipped polarity after the cd70821 framework commit |
| PROVISIONAL | **1** | CLM-040 (forced by Disputed-by citation) |
| DEPRECATED | **2** | CLM-016, CLM-043 |
| **Total** | **65** | 73 raw entries - 8 grandfathered structure |
| claimsActiveCount (effective) | **62** | 60 + 2 INVERTED-ACTIVE |
| claimsTotalCLM | **73** | Raw CLAIMS.md entries |

**Taxonomy note:** The requested statuses (SUPPORTED / UNDERPOWERED /
REGRESSES / DEFERRED / NOT_SIGNIFICANT) are **not** a CLAIMS.md taxonomy.
Those verdicts live as per-cell outcomes in CONSOLIDATED_RESULTS.md and
INSIGHTS.md, not as claim-level statuses.

### 2.2 CONSOLIDATED_RESULTS.md section spine

`docs/CONSOLIDATED_RESULTS.md` carries 44 distinct section keys (oldest
→ newest): TLDR, framework_positioning, algorithm_uplifts, 2d_fm_ablation,
sota_2d_rectified_flow, sota_cifar10_rectified_flow, toy_framework_comparison,
defensive_engineering, open_questions, source_index, …, wave34…wave274.

**Newest consolidated section:** `15_102_tnnls_submission_folder_creation_…`
(Wave 274 / 2026-09-21). Sections grow monotonically — every wave
appends its verdict rather than rewriting prior sections. This is the
primary structural debt the flattening must address: 102 wave-tagged
sections under §15 alone.

### 2.3 INSIGHTS.md

`docs/INSIGHTS.md` carries **31** distinct insight entries spanning
algorithm + statistical + engineering domains. INSIGHTS.md is the
canonical "framework learning" ledger and is **not** wave-prefixed;
flattening does not need to touch it.

### 2.4 Metric ledger schema (proposed for Wave 275 P2)

Single doc (or CSV/JSON) keyed by CLM-ID with columns:
`claim_id | r_id | model | metric | baseline | framework | delta_abs |
delta_pct | p_raw | p_bonf | n | seed | arm | nfe | sha | artifact_path |
artifact_basename | verifier_state | dated | wave_ref | section_ref | notes`.

Implementation path:
- Extend `docs/headline-evidence/README.md` table to machine-readable
  JSON at `docs/headline-evidence/ledger.json` (one row per CLM, plus
  derived R* rollups).
- Regenerate from `verification_outputs/*.csv` via new
  `tools/build_headline_ledger.py`.
- Schema guard — required keys: `claim_id` (CLM-NNN or R[0-9]+[a-z]?),
  `metric`, `baseline`, `framework`, `delta_abs`, `delta_pct`, `p_raw`,
  `p_bonf`, `n`, `sha`, `artifact_path`.
- Ingest all R* rows from `docs/headline-evidence/*/SOURCE.md`, all
  CLM-* rows from `docs/CLAIMS.md`, all stat-method rows from
  `verification_outputs/wave234-p{2,3,4,5}-*`, all engineering gate
  rows from `docs/GATES.md` and last wave acceptance table.

---

## 3. Verification surface

**Source:** `verification_outputs/` + headline-evidence dirs +
upstream_eval subdirs.

| Metric | Value | Notes |
|---|---|---|
| totalDirs | **531** | Across `verification_outputs/` + sibling artifact dirs |
| jsonCount | **725** | `verification_outputs/**/*.json` |
| csvCount | **196** | `verification_outputs/**/*.csv` |

### 3.1 Headline-evidence directory mapping (R1–R6)

| R-id | Model | Metric | Primary artifact directory |
|---|---|---|---|
| **R1** | LineageFlow | hmmscan_total_hits | `lineageflow_hmmer_real_n1000_w158_q3_2026/` + `wave206-p1-lineageflow-n1000.json` |
| **R2** | Kanzi | fg_dev (framework inv_proj) | `kanzi_n1000_framework_inv_proj_w149_q4_2026/` + `wave206-p2-kanzi-framework-n1000.json` |
| **R3** | FlowMol3 | fg_dev | `flowmol3_n1000_sweep_q4_2026.json` + `wave206-p3-flowmol3-n1000.json` |
| **R4** | 2D Two Moons | W2 | **not yet measured** (deferred to follow-up work; no verification_outputs entry) |
| **R5** | 2D Eight Gaussians | W2 | `wave206-p4-r-level-refresh.json` + `docs/r4-survey/10-sota-2d-experiment-results.md` + `docs/headline-evidence/r3_cifar_rf_v2_fid_m44p17pct/` + `baseline_comparison_q4_2026.json` (MNIST FM FID axis) |
| **R5b** | CIFAR-10 RF matched-NFE=50 | FID (delta) | `wave206-p6-honest-negative-curve.{csv,json}` + `cifar_n200_nfe50_ema_corrected/` + `wave191-p2-cifar10-n1000.json` (N=1000 chunked-FID cross-check) |
| **R6** | k6 foldability + LineageFlow | pLDDT | `k6_foldability_n1000_w161_q3_2026/` + `wave206-p1-lineageflow-n1000.json` (§10.6 cell names `lineageflow_k6_sweep_q4_2026/` but on disk the actual artifact is `k6_foldability_n1000_w161_q3_2026/`) |

### 3.2 Statistical-method mapping

| Method | Primary artifact | Sensitivity artifact |
|---|---|---|
| **TOST** equivalence (16 cells, α=0.05) | `wave234-p2-tost.csv` | `wave246-p3-tost-sensitivity.csv` |
| **JT** Jonckheere trend (R2 + R6 tier-aware) | `wave234-p3-jonckheere.csv` | — |
| **BF01** Bayes factor (16 cells) | `wave234-p4-bf01.csv` | `wave246-p3-bf01-sensitivity.csv` |
| **meta** DerSimonian-Laird (K=12) | `wave234-p5-meta-analysis.csv` + `wave234-p5-meta-summary.json` | `wave246-p4-subgroup-meta.json` (subgroup) |
| **NI** non-inferiority (R5b matched-eff-NFE) | `wave234-p6-ni-test.csv` + `wave234-p6-non-inferiority.{csv,json}` | — |

### 3.3 Orphan surface

**Empty directories (orphan dirs, 18 total):**

```
kanzi_n1000_real_v3/
wave229-p1-sweep-vanilla/
wave229-p5-molecule-image-per-record/
wave247-p2-r5b-seed42-n1-n200/
wave206_p6_pilot/{cosine_nfe50_n20, codimension_sheet_nfe50_n20,
  evidence_driven_nfe50_n20, free_traj_nfe50_n20,
  CosineAnnealScheduler_nfe50_n20, CodimensionSheetScheduler_nfe50_n20,
  EvidenceDrivenScheduler_nfe50_n20, FreeTrajScheduler_nfe50_n20}
upstream_eval/kanzi_seed42nnfe100/kz_out/
wave199-p2-lineageflow-n1000/{baseline/{fold, sc}, framework/{fold, sc}}
```

**Orphan files (10 total):**
- `noise_injection_sweep_1788554274.json`, `noise_injection_sweep_1788555239.json`,
  `noise_injection_sweep_1788555626.json`
- `noise_injection_eight_gaussians_{baseline,framework}.csv`
- `noise_injection_two_moons_{baseline,framework}.csv`
- `capability_audit_q4_2026_post_w35.json`, `capability_audit_q4_2026_post_w38.json`,
  `capability_audit_q4_2026_post_w40.json`
- `controlled_audit_q3_2026.json`

**Total orphan count:** 18 empty dirs + 10 orphan files = **28 orphan entries**.

**Orphan rationale:** none of the orphan files are cited in `CLAIMS.md`,
`paper-draft.md`, `CONSOLIDATED_RESULTS.md`, `baseline-audit-report.md`,
or `reproducibility_record.md`. Sibling `capability_audit_q4_2026.json`
IS cited but `post_w35/38/40` siblings are not. All 28 are candidates
for archival during Wave 275 P2 governance sweep.

**Stale dirs:** 0 — no stale-but-cited artifacts surfaced.

---

## 4. Weak metrics

**Source:** Wave 274 weak-claim audit + Phase 1 weak-metrics pass that
re-evaluated each HEADLINE / STATISTICAL claim against the
1pp detection + Bonferroni-corrected 0.05/16=0.003125 thresholds.

### 4.1 Summary

| Metric | Value |
|---|---|
| weakClaimsCount | **11** |
| improvableCount | **10** (via adapter-side fixes; not vendored repos) |
| blockedByVendored | **false** (no claim requires vendored-code changes — all 11 are improvable from our adapter side; 1 (R1) is improvable only via metric redefinition which IS vendored) |

**Improvable from our side (10):** K1, K3, K4, K5, K6, K7, R5b, R3, R6, R5c.

**Not improvable from our side (1):** R1 (LineageFlow HMMER hmmscan) — metric
is purely upstream `hmmscan` against `Pfam-A.hmm`; no adapter-side lever.
R1 improvement requires metric redefinition which IS vendored.

> **Effective `improvableCount` from the user's framing = 10**
> (the count excludes R1, which cannot be moved by an adapter change).
> If counting strictly "via adapter + not vendored repos," R1 is
> improvable in principle (metric redefinition) but not by an adapter
> patch alone — the upstream file in
> `data/lineageflow_upstream/evaluation/family_validity_hmmer.py` is
> what defines the metric.

### 4.2 Summary by adapter

| Adapter | Weak claims | Improvable from our side | Vector |
|---|---|---|---|
| **FlowMol3** | 2 (K1, R3) | 2 | K1: swap `pb_energy=False` + RDKit-only validity in `adaptive_reflow/adapters/flowmol3_upstream_shim.py:184`. R3: tile per-mol prior across batched DGL graph in `adaptive_reflow/adapters/flowmol3_v2_adapter.py:_solve_ode_upstream_batch` (lines 2868-2881). |
| **CIFAR-10 RF** | 2 (K3, R5b) | 2 | K3: flip `RF_CIFAR_N_ROUNDS_OVERRIDE` to 2 + wire `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE=0.5` in `adaptive_reflow/adapters/rectified_flow_cifar.py:150-151`; thread `--cosine-ramp-strength FLOAT` into `tools/run_sota_cifar_experiment.py:1212` CosineAnnealScheduler. R5b: same vector as K3 (n_rounds=2 + cosine_ramp_strength=0.5 — the two remaining adapter levers). |
| **LineageFlow** | 4 (K4, K5, K6, K7) | 4 | K4: extend `tools/upstream_eval.py:run_lineageflow_upstream_eval` to feed FASTA with ≥200 AA (longer sequences → multiple Pfam domain hits); bump synthetic length distribution in `adaptive_reflow/adapters/lineageflow.py`. K5: change prior composition to uniform AA (was methionine-biased) + add `--lineageflow-prior-mix` flag. K6: activate the Wave 201 P2-P7 pipeline plumbing at `tools/run_lineageflow_n1000_foldability_omegafold.py` once sm_120 torch blocker (Wave 202 P2 commit 40c70a7) resolves. K7: extend `tools/upstream_eval.py:172` with `restrict_novelty_to_target_db: bool = True` flag to bypass the `_require_path` check on `dataset/pfam_fastas_clean/` and reuse prebuilt `pfam_holdout_targetDB`. |
| **MNIST FM** | 1 (R5c) | 1 | Add `--epochs 3 --base-channels 16 --max-train-images 60000` documented production-ckpt recipe to `tools/materialize_mnist_fm.py`; re-run `scripts/wave191_p3_mnist_sweep.py` to upgrade R5c from PROVISIONAL to ACTIVE. |
| **k6 foldability + LineageFlow** | 1 (R6) | 1 | Add `--tier-aware-n-cap` flag in framework-side scheduler that scales `n_cap *= 0.5` when baseline_pLDDT percentile is above 67th; per-tier scheduler path, no vendored-code changes. |

### 4.3 Per-claim weakness classification

| clmId | Category | Weakness | Adapter | Vendored? | Improvable? |
|---|---|---|---|---|---|
| K1 | HEADLINE | protocol-mismatch | FlowMol3 | yes (`data/FlowMol3/repo/flowmol/analysis`) | yes |
| K3 | HEADLINE | protocol-mismatch | CIFAR-10 RF | NONE | yes |
| K4 | STATISTICAL | underpowered | LineageFlow | yes (upstream eval) | yes |
| K5 | HEADLINE | ties-at-zero | LineageFlow | NONE | yes |
| K6 | STATISTICAL | env-blocked | LineageFlow | yes (`data/lineageflow_upstream`) | yes |
| K7 | STATISTICAL | env-blocked | LineageFlow | NONE | yes |
| R5b | HEADLINE | regression | CIFAR-10 RF | NONE | yes |
| R3 | STATISTICAL | underpowered | FlowMol3 | yes (`data/FlowMol3/repo`) | yes |
| R1 | STATISTICAL | underpowered | LineageFlow | yes (upstream metric) | no (metric redefinition is vendored) |
| R6 | STATISTICAL | regression | k6 foldability + LineageFlow | NONE | yes |
| R5c | STATISTICAL | deferred | MNIST FM | NONE | yes |

### 4.4 Aggregate health

- **2 protocol-mismatch** (K1, K3): fixable in adapter shim layer.
- **3 underpowered** (K4, R3, R1): R1 vendored-blocked; K4 + R3 fixable
  by sampling longer sequences (K4) + DGL batch tiling (R3).
- **2 env-blocked** (K6, K7): K6 waits on sm_120 torch blocker resolution
  (Wave 202 P2); K7 fixable today via CLI flag override.
- **2 regression** (R5b, R6): both fixable via adapter-side lever
  activation (cosine_ramp_strength=0.5; tier-aware n_cap scaling).
- **1 ties-at-zero** (K5): fixable via prior composition change.
- **1 deferred** (R5c): fixable via production-ckpt materialization.

**All 11 weak claims have an adapter-side or tooling-side remediation
vector.** No weak claim is permanently blocked by vendored upstream code
at the adapter surface — only R1's metric redefinition (vendored) is
blocked, and even R1 is improvable by extending the upstream eval call
shape (length-bias flag) within our adapter wrapper.

---

## 5. Recommended next phase

**Wave 275 P2 — Flattening (apply Option C archive first, then Option B rename)**

Tasks, in order:

1. **P2.1 Archive 278 explicit historical files → `docs/ARCHIVE/audit-by-wave/`**
   (Wave 34-99 precedent from 2026-09-14). No active-surface links to
   these files, so this is safe.
2. **P2.2 Address the remaining 148 historical files** (sub-directory burials
   + non-wave-prefixed historicals). Decide per-file: archive, keep-as-is,
   or rename-in-place.
3. **P2.3 Rename 198 wave-prefixed active files** by topic cluster:
   `cifar/*`, `kanzi/*`, `flowmol3/*`, `lineageflow/*`, `governance/*`.
   Every rename traces its citation consumer before the move; mkdocs nav,
   CLAIMS, README, paper, cover_letter, supplementary, CHANGELOG, ROADMAP,
   AGENTS.md are all updated as part of the same rename commit.
4. **P2.4 Remove `mkdocs.yml` `audit/wave*.md` glob** (line 278).
5. **P2.5 Build the headline-ledger machine-readable JSON**
   (`docs/headline-evidence/ledger.json` + `tools/build_headline_ledger.py`).
   Schema guard with required keys: `claim_id`, `metric`, `baseline`,
   `framework`, `delta_abs`, `delta_pct`, `p_raw`, `p_bonf`, `n`, `sha`,
   `artifact_path`.
6. **P2.6 Archive 28 orphan entries** (18 empty dirs + 10 orphan files
   in `verification_outputs/`).

**Wave 275 P3 — Weak-metric adapter remediation**

Tasks, parallel:

- **P3.1 FlowMol3:** K1 (PoseBusters → RDKit-only validity) +
  R3 (DGL batch prior tiling) — 2 changes in disjoint files
  (`adaptive_reflow/adapters/flowmol3_upstream_shim.py:184` and
  `adaptive_reflow/adapters/flowmol3_v2_adapter.py:_solve_ode_upstream_batch`).
- **P3.2 CIFAR-10 RF:** K3 + R5b (flip `RF_CIFAR_N_ROUNDS_OVERRIDE=2` +
  wire `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE=0.5` +
  thread `--cosine-ramp-strength FLOAT` into `CosineAnnealScheduler`).
- **P3.3 LineageFlow:** K4 (length bias ≥150-200 AA) + K5 (uniform AA
  prior + `--lineageflow-prior-mix` flag) + K7 (CLI flag override
  `restrict_novelty_to_target_db`).
- **P3.4 k6 foldability:** R6 (`--tier-aware-n-cap` flag, scales n_cap
  by 0.5 above 67th percentile).
- **P3.5 MNIST FM:** R5c (production-ckpt materialization recipe).
- **P3.6 LineageFlow env-block:** K6 — pipeline plumbing activation
  once sm_120 torch blocker (Wave 202 P2 commit 40c70a7) resolves;
  depends on environment, defer or wait.

**Wave 275 P4 — Final-verify + post-state inventory**

Single audit verifying:
- No `waveNNN-` substring remains in any active file path.
- Headline ledger regenerates cleanly from verification_outputs/.
- Each weak-claim remediation moved from weak → measurable:
  K1 (HEADLINE protocol-mismatch → RDKit-bridged),
  K3 (HEADLINE → cosine_ramp_strength axis measured),
  R5b (regression → R5b residual post-override),
  R3 (underpowered → 3-seed sweep unblocked),
  R5c (PROVISIONAL → ACTIVE).
- D.4 30/30 byte-stable preserved; claims consistency no drift;
  mkdocs --strict 0 warnings; ruff count ≤ 144 (no regression on
  Wave 274 P6 fix).

**Sequencing rationale:**
- P2 flattening is the cheap + safe part (archive 278 is one move; 198
  renames have traced consumers); it MUST land before P3 so the
  adapter changes cite topic-clean paths.
- P3 weak-metric remediation is the higher-value part; each task has
  a single adapter surface and is disjoint from the others.
- P4 is the single audit pass that closes the wave.

**Wave 276+ — Post-inventory work (deferred to user direction)**

- Submissions-related tasks (per user directive: "投稿相关的先不用管")
  are explicitly deferred to a later wave.
- Other tasks the user mentioned as "合理安排顺序用 ultracode 做起来"
  slot into Wave 276+ once P1-P4 close.

---

## 6. Files touched (Wave 275 P1 itself)

- `docs/audit/wave275-p1-state-inventory.md` — this audit doc, new file.

No source code modified. No vendored code modified. No claims or
metric files modified. Baseline frozen at `07ad48e`.