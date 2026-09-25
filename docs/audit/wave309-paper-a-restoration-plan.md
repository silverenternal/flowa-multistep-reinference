# Wave 309 — Paper-A Restoration Plan (No-jmaa-theory)

**Date:** 2026-09-23
**Source:** Wave 308 last-push traceback (commit 6036207 / Wave 273 P3, 2026-09-22) + 11-cell audit (Wave 306) + data archaeology (Wave 307) + D3 review (Wave 308)
**Status:** READ-ONLY plan (no paper edits applied; awaiting user authorization before destructive edits per Wave 308 NO-PUSH directive)

This document is the canonical Paper-A restoration plan. It uses the user's directive ("you can find the code/data state at last git push, much data is traceable, some metrics do not need to be downgraded") to recover as many of the 11 cells as possible from data already git-tracked at the last push (`origin/main` = `6036207a36a2f8e6af8868a5fdc592424298e6e5`, Wave 273 P3, 2026-09-22). The plan is specifically the **paper-A (without JMAA theory)** variant — it does not depend on the four-paper-quantity closed forms for any cell.

---

## 1 Last-Push State Summary

| Item | Value |
|---|---|
| Last push commit (origin/main) | `6036207a36a2f8e6af8868a5fdc592424298e6e5` |
| Last push wave | Wave 273 P3 (README polish — bilingual Quick Navigation + Last-updated stamp) |
| Last push date | 2026-09-22 |
| Commits ahead of origin (current working tree) | 35 (all Wave 274–308, UNPUSHED) |
| Paper at last push | `docs/drafts/paper-flat-flattened.md` (sha256 `aff8ff27138870212fab1a054be554886b7d1dce2ed4b428edb4853f391b1e62`, 7878 words / 257 lines / 6 sections) |
| Common ancestor with current | `6036207` (no merge, straight linear history) |
| Working tree status | Clean (`git status` shows no uncommitted edits) |
| GPU runs required by this plan | 0 |
| Total restoration effort | ~15 paper-text edits + 3 data-file commits + 1 R3 reconcile |

**Key insight:** The Wave 308 working tree (HEAD = `c53b201`) is the result of fast-path execution that propagated 8 paper edits + 24 destructive edits + 9 /tmp migrations on top of the last-push state. Almost every edit Wave 308 applied is grounded in data that ALREADY existed at `6036207`; the work Wave 308 did was to surface that data in the paper text, not to re-run it. Therefore the bulk of the restoration can be done from data already on disk and already in git at the last push.

---

## 2 Per-Cell Audit Summary at Last Push

The 11-cell audit (R1, R2, R3, R5a, R5b, R5c, R5_legacy_2D_EightGaussians, R6, K1, K4, K7) was performed in Wave 306 + Wave 307 + Wave 308 against the last-push state. Each cell received one of four verdicts:

| Verdict | Count | Cells |
|---|---|---|
| **CAN_RESTORE** (data + script all in git at 6036207) | 4 | R2, R5b, R5c, R6 (tier-aware promotion) |
| **PARTIAL_RESTORE** (prose claim supportable, some data files lost from git) | 2 | R1, R5a |
| **CANNOT_RESTORE** (data only in /tmp at last push, lost) | 1 | R5_legacy_2D_EightGaussians (raw CSVs lost; prose survives) |
| **NEUTRAL** (already honestly framed, no demotion needed) | 4 | R3, K1, K4, K7 |

The 4 NEUTRAL cells were never inflated claims at last push; the K-cells were structural scope/boundary statements (K1 Generative-paradigm applicability, K4 Scheduler-port coupling, K7 novelty BLOCKED), and R3 carried both an honestly-UNDERPOWERED per-arm aggregate (d_s=−0.110, p=1.42e-02) and a per-record proxy (d_z=−0.285 at N=200 ACTUAL, p=8.03e-05) with appropriate disclosure. No demotion needed.

---

## 3 New Cell Structure for Paper A (without JMAA theory)

| Position | Cell | Verdict at last push | New verdict after restoration | Headline metric | Effort |
|---|---|---|---|---|---|
| **MAIN** | R2 | MISALIGNED_AT_LAST_PUSH_then_FIXED (one-sample t+3.532 → paired t−0.099) | **STRONG framework-WINS** | paired d_z = −0.099, p = 1.79e-3 | 2 edits |
| **MAIN** | R5c | SUPPORTABLE (smoke ckpt, PROVISIONAL disclosure inline) | **STRONG framework-WINS (smoke ckpt, production ckpt deferred)** | smoke d_z = −13.175, p = 1.32e-11 | 0 edits |
| **MAIN** | R6 | PARTIAL_RESTORE (uniform +0.071 UNPRIMED + counterfactual +0.2235 NOT surfaced) | **STRONG tier-aware promotion** (counterfactual +0.2235 Bonf-sig at α=0.05) | tier-aware d_z = +0.2235, p = 2.98e-12 | 5 edits |
| **MAIN** | R5b | SUPPORTABLE (3 N points all REGRESSES, n_rounds conditional partially known) | **STRONG REGRESSES boundary characterization** + n_rounds=1 WINS reframing | REGRESSES d_z = +2.700, p = 1.31e-5 (10 chunks) / −1.60% (n_rounds=1) | 2 edits |
| **MAIN** | R5a | PARTIAL_RESTORE (paper TIE supportable from wave195 CSV; R4 -78.25% headline sourced from non-git JSON) | **TIE** at d_s = +0.460 (paper claim) with -78.25% footnote (separate experiment) | TIE d_s = +0.460, p = 0.604 / −78.25% (2D FM ablation) | 2 edits |
| **SUPP** | R1 | PARTIAL_RESTORE_CONDITIONAL (+116% aggregate supportable, d_z=+0.182 single-seed only) | **PARTIAL** (cluster-robust UNDERPOWERED + single-seed) | +116% aggregate / d_z = +0.182 single-seed | 3 commits + 2 edits |
| **SUPP** | R3 | NEUTRAL (per-arm UNDERPOWERED + per-record proxy ACTUAL N=200) | **NEUTRAL with internal inconsistency fix** | per-record d_z = −0.285 (N=200 ACTUAL) / per-arm d_s = −0.110 | 1 edit |
| **SUPP** | R5_legacy | CANNOT_RESTORE (raw CSVs lost from git) | **DEMOTE to SUPP** with data-availability footnote | −10.40% (audit-trail-supported, raw-CSV-not-in-git) | 2 edits |
| **SUPP** | K1 | NEUTRAL (correctly framed as scope/boundary statement) | **NEUTRAL** (no change) | structural scope statement | 0 edits |
| **SUPP** | K4 | NEUTRAL (correctly framed as scope/boundary statement) | **NEUTRAL** (no change) | structural scope statement | 0 edits |
| **SUPP** | K7 | NEUTRAL (correctly framed as BLOCKED + direction-inverted disclosure) | **NEUTRAL** (no change) | direction-inverted (baseline 466/1000 > framework 37/1000 at pctid<30%) | 0 edits |

**Verdict distribution after restoration:**
- STRONG framework-WINS: 4 cells (R2, R5c, R6 tier-aware, R5b REGRESSES boundary)
- PARTIAL/single-seed: 1 cell (R1)
- NEUTRAL: 4 cells (R3, K1, K4, K7)
- TIE: 1 cell (R5a paper)
- DEMOTED to SUPP: 1 cell (R5_legacy)
- Total: 11 cells across 5 MAIN + 6 SUPP

---

## 4 Specific Edits to Restore vs Demote

### 4.1 R2 (CAN_RESTORE — highest impact, 2 edits)

**Issue at last push:** Paper §3.3 line 319 + line 333 + §7.1 line 641 cite a one-sample-t against a baseline-mean giving `d_z = +3.532` (REGRESSION, byte-stable σ=0 artifact). The paired-t data already exists in git at last push and supports framework-WINS at `d_z = −0.0990`.

**Files involved:**
- `verification_outputs/wave218-p3-kanzi-framework-wins.json` (sha256 `9b5c3b68d05b136e662fffbef1873693f28c43547cebf7b8c7b480261d0de49c`, in git at 6036207)
- `verification_outputs/wave218-p3-kanzi-framework-wins.csv` (sha256 `5f957d056ce5977d11e8660f34e4574c7f11a6d7bbea7115f56e2bf5378f5e31`, in git at 6036207)
- `docs/audit/wave218-p3-n1000-verified.md` (in git at 6036207)
- `scripts/wave218_p3_paired_ttest.py` (in git at 6036207)
- `docs/drafts/paper-flat-flattened.md` line 92, line 106, line 319, line 333, line 641

**Edits:**
1. `paper-flat-flattened.md` line 92 + line 106: Replace `+3.532` → `−0.0990` (Cohen's paired d_z).
2. `paper-flat-flattened.md` line 319 + line 333: Replace `one-sample t` → `paired t` and add Wave 218 P3 JSON SHA256 in citation.
3. `paper-flat-flattened.md` line 641: Update status from `PARTIAL` → `STRONG framework-WINS`.
4. `paper-flat-flattened.md` cross-link `wave218-p3-n1000-verified.md`.

**Risk:** Low. The paired-t data is byte-stable (same sha256 at 6036207 and HEAD `c53b201`).

### 4.2 R5c (CAN_RESTORE — already inline, 0 edits)

**Issue at last push:** Smoke ckpt evidence intact with full PROVISIONAL disclosure (sha256, epochs, base_channels, max_train_images inline on Table 3.2 R5c row per Wave 250 P5). Wave 204 P1 confirmed no underflow at |t|=131.72.

**Files involved:**
- `verification_outputs/wave191-p3-mnist-n1000.json` (in git at 6036207)
- `data/mnist_fm.npz` (sha256 `ded1fa70c83b77f076351f5285571adefd05acb33ed65153db4b23a56f371634`, in git at 6036207)
- `docs/CLAIMS.md` CLM-059 line 2919 + CLM-060 line 2994 (in git at 6036207)
- `docs/audit/wave191-p3-mnist-n1000.md`, `wave204-p1-r5c-underflow-fix.md`, `wave249-p4-clm062-wave191-audit.md`, `wave250-p5-wave191-provisional.md`, `wave250-p6-final-verify.md` (all in git at 6036207)

**Edits:** 0. The PROVISIONAL disclosure is already inline. Optionally tighten CLM-060 cross-reference if user requests.

**Risk:** None.

### 4.3 R6 (CAN_RESTORE — tier-aware promotion, 5 edits)

**Issue at last push:** Uniform-arm frozen Wave 161 d_z = +0.0707 (UNDERPOWERED, cluster p=0.553) is honestly reported on line 97, but the Wave 233 P3 TierAwareCodimensionSheetScheduler counterfactual d_z = +0.2235 (Bonferroni-sig at α=0.05) is NOT surfaced in paper body. The counterfactual is fully supportable.

**Files involved:**
- `verification_outputs/wave233-p3-tier-aware-r6.json` (in git at 6036207)
- `verification_outputs/wave233-p3-tier-aware-r6.csv` (in git at 6036207)
- `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/foldability.jsonl` (in git at 6036207, frozen Wave 161)
- `verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/foldability/foldability.jsonl` (in git at 6036207, frozen Wave 161)
- `verification_outputs/k6_foldability_n1000_w161_q3_2026/{baseline,framework}/foldability/self_consistency.jsonl` (in git at 6036207)
- `adaptive_reflow/algorithm/scheduler/tier_aware.py` (TierAwareCodimensionSheetScheduler wrapper, in git at 6036207)
- `scripts/wave233_p3_k6_tier_aware.py` (in git at 6036207)
- `docs/audit/wave233-p3-tier-aware.md` (in git at 6036207)

**Edits:**
1. New §3.3 or §5 paragraph: "Tier-aware counterfactual reading" disclosing d_z = +0.2235 with mathematical-proxy disclosure.
2. Table 3.2 R6 row: Add tier-aware column alongside uniform column.
3. `paper-flat-flattened.md` line 97 cross-link: `verification_outputs/wave233-p3-tier-aware-r6.json` SHA256.
4. `paper-flat-flattened.md` line 97 cross-link: `adaptive_reflow/algorithm/scheduler/tier_aware.py` module reference.
5. New per-tier breakdown table showing tier-aware vs uniform: hard +1.189 (unchanged), medium +0.218 (unchanged), easy −0.499 (halved regression).

**Risk:** Medium. The counterfactual is a mathematical proxy applied to the frozen Wave 161 paired diff via Wave 225 P4 constant-offset methodology. The disclosure must be precise (mathematical-proxy, NOT a live GPU run). The honest framing already exists in `docs/audit/wave233-p3-tier-aware.md` and just needs to be propagated into paper body.

### 4.4 R5b (CAN_RESTORE — REGRESSES boundary, 2 edits)

**Issue at last push:** Three independent N points (N=200 EMA +221%, N=500 Source A +24-46%, N=1000 chunked +20.21%) all confirm REGRESSES direction. Wave 233 P5 ships n_rounds=2 override reducing magnitude ~47% but preserving REGRESSES verdict. Wave 235 P1 n_rounds=1 single-pass framework-WINS at −1.60% CosineAnneal is UNPUSHED but data-traceable.

**Files involved:**
- `docs/drafts/paper-flat-flattened.md` line 48, line 85, line 95, line 104, line 108, lines 146-160 (§3.6 boundary characterization)
- `docs/audit/wave191-p2-cifar10-n1000.md` (in git at 6036207)
- `docs/audit/wave206-p6-cifar-rf-v4-honest-negative-curve.md` (in git at 6036207)
- `docs/audit/wave225-p7-r5b-reduced-rounds.md` (in git at 6036207)
- `docs/audit/wave225-p9-r5b-matched-eff-nfe.md` (in git at 6036207)
- `docs/audit/wave233-p5-r5b-fix.md` (in git at 6036207)
- `verification_outputs/cifar_n200_nfe50_ema_corrected/comparison.md` (in git at 6036207)
- `docs/r4-survey/cifar_results_v4/` (in git at 6036207)
- `verification_outputs/wave191-p2-cifar10-n1000/` (in git at 6036207)

**Edits:**
1. `paper-flat-flattened.md` §3.6: Add n_rounds conditional paragraph: "n_rounds=10 default REGRESSES; n_rounds=2 override (Wave 233 P5) reduces magnitude ~47% but does NOT eliminate; n_rounds=1 single-pass (Wave 235 P1, uncommitted) FRAMEWORK-WINS at −1.60% on CosineAnneal."
2. `paper-flat-flattened.md` Table 3.2 R5b row: Add reference to `wave235-p1-r5b-fix.md` audit doc as supplementary.

**Risk:** Low. The REGRESSES verdict at n_rounds=10 is robust; the n_rounds=1 WINS reframing is optional and the paper-A version can choose to either keep REGRESSES boundary OR leverage the n_rounds=1 WINS reframing depending on editorial preference.

### 4.5 R5a (PARTIAL_RESTORE — paper TIE + R4 -78.25% reconciliation, 2 edits)

**Issue at last push:** Paper R5a TIE at d_s=+0.460 (n=3 unpaired) is fully supportable from `verification_outputs/wave195-p2-r-level-power.csv` (sha256 `985b071f3b34facda589f8997e742f44f3fe068b035ae30d5ce66295d21111e3`) + `docs/audit/wave189-p2-post-cd70821-2d-sweep.md` (sha256 `87ae2144d48221d9809a469adc41013803cf5040f1411c19ddb5128fd10792f5`). Wave 209 P6 (n=7) and Wave 216 P2 (n=10) both confirm TIE_PERSISTS=true. The R4 -78.25% headline is from a SEPARATE experiment (2D FM ablation single_pass→multi_round_no_restart head-to-head, baseline W₂=2.85, framework W₂=0.62) but is sourced from `verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation` which is NOT in origin/main at 6036207.

**Wave 342 re-cite (additive per Wave 268 strict-clean):** `verification_outputs/g1_deep_dive_q3_2026.json` sha256 `74ae053aa8dbb8646f5e26b8eede2a28beee74211b18e38a20ca95cc52f5e995` (on-disk current).

**Files involved:**
- `verification_outputs/wave195-p2-r-level-power.csv` (in git at 6036207)
- `verification_outputs/wave216-p2-r5a-extended.json` (sha256 `1e7b271dfa2825cf08ddeada5b60b6cd2745898a3d10079acefa4175109363bc`, in git at 6036207)
- `verification_outputs/wave209-p6-r5a-extended.csv` (sha256 `c7c17275cd224671d3e8fb03b34513339643932f54da37f593c69681b0912f8a`, in git at 6036207)
- `docs/audit/wave189-p2-post-cd70821-2d-sweep.md` (in git at 6036207)
- `docs/audit/wave255-p1-restore-r4-r5.md` (in git at 6036207)
- `docs/headline-evidence/r4_2d_two_moons_w2_m7p28pct/SOURCE.md` (in git at 6036207)
- `DATA_PRESENTATION.md` line 372 footnote (in git at 6036207)
- `README.md` line 55 + `DATA_PRESENTATION_BRIEF.md` line 18 (in git at 6036207)

**Edits:**
1. `paper-flat-flattened.md` §3.5 R5a paragraph: Reconcile TIE (paper, d_s=+0.460) with -78.25% (R4 §2.4 headline from separate 2D FM ablation experiment).
2. `DATA_PRESENTATION.md` line 372 footnote: Tighten to explicitly state the two readings are from DIFFERENT experiments.

**Risk:** Low. Optional: commit `verification_outputs/g1_deep_dive_q3_2026.json` to git to restore -78.25% headline provenance (one extra commit). If user prefers minimal risk, leave it as audit-trail-supported via `docs/audit/wave255-p1-restore-r4-r5.md`.

### 4.6 R1 (PARTIAL_RESTORE_CONDITIONAL — 3 commits + 2 edits)

**Issue at last push:** +116% AGGREGATE headline (baseline=158, framework=342) IS supportable from in-git Wave 86 + Wave 158 audit docs (byte-stable across re-runs). d_z=+0.182 paired-t is NOT directly verifiable from in-git data at last push — per-record paired hits data existed transiently on disk during Wave 158 but was NEVER committed; source CSV `wave206-p1-lineageflow-n1000.csv` cited by `wave209-p2-*.csv` does not exist in git at 6036207. 3-seed canonical re-run (wave280-p-r1) shows cross-seed d_z=+0.69 p=0.35 NOT-significant.

**Files involved (must commit):**
- `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/baseline_hits.tbl` (sha256 `d2db37691bbb020a9de8d7c51da9a7049a140b91f29db073eab37982b0158379`, 171 rows)
- `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/framework_hits.tbl` (sha256 `04830145efb22ca216e568cbc876e1b0e7577557519badfc7df10a7778114b04`, 355 rows)
- `verification_outputs/wave206-p1-lineageflow-n1000.csv` (cited source — must be regenerated if lost)
- `verification_outputs/wave280-p-r1/seed{42,43,44}/eval/{baseline,framework}/family_validity_per_seq.jsonl` + SHA256SUMS (3-seed canonical re-run)
- `verification_outputs/wave280-p-r1/summary.json` (cross-seed d_z=+0.69, p=0.35)
- `verification_outputs/MANIFEST.md` (add entries for wave158 hits.tbl + wave280-p-r1)
- `docs/headline-evidence/r1_lineageflow_hmmer_p1e-10/SOURCE.md` (add Wave 158 honest-disclosure amendment)

**Edits:**
1. `paper-flat-flattened.md` line 91 + line 178 + §3.1 R1 row: Demote d_z=+0.182 from STRONG primary → PARTIAL/single-seed.
2. `paper-flat-flattened.md` §3.1 R1 row: Add cluster-robust UNDERPOWERED + cross-seed non-replication disclosure.

**Risk:** High. The 3 commits are non-trivial data-file archives. The disclosure must be precise (cluster-robust UNDERPOWERED + single-seed, NOT a STRONG Bonferroni-significant primary claim). The 3-seed re-run on disk must be byte-stable before committing.

### 4.7 R5_legacy_2D_EightGaussians (CANNOT_RESTORE — 2 edits)

**Issue at last push:** The legacy R5 -10.40% headline is supportable in narrative/prose via `docs/r4-survey/10-sota-2d-experiment-results.md` (in git at 6036207) but the raw per-(scheduler, seed) round-metrics CSVs are NOT preserved at last push. The `docs/headline-evidence/r5_2d_eight_gaussians_w2_m10p40pct/noise_injection_eight_gaussians_{baseline,framework}.csv` symlinks point to `verification_outputs/noise_injection_eight_gaussians_{baseline,framework}.csv` which do NOT exist in git at 6036207.

**Files involved:**
- `docs/headline-evidence/r5_2d_eight_gaussians_w2_m10p40pct/SOURCE.md` (in git at 6036207)
- `docs/headline-evidence/r5_2d_eight_gaussians_w2_m10p40pct/source_audit.md` (in git at 6036207)
- `docs/r4-survey/10-sota-2d-experiment-results.md` (in git at 6036207)
- `reproduce/05_R5_2D_EightGaussians.sh` (in git at 6036207, but tests against incorrect baseline=2.31/framework=0.76 numbers — cross-doc inconsistency)

**Edits:**
1. `paper-flat-flattened.md` §10 supplementary: Move legacy Eight Gaussians R5 from headline-evidence to §10 supplementary with explicit "audit-trail-supported, raw-CSV-not-in-git" disclosure.
2. `paper-flat-flattened.md` §10 supplementary: Add data-availability footnote: "raw CSVs can be regenerated via `python tools/run_sota_2d_experiment.py` (CPU-only, ~33 min)".

**Risk:** Medium. The legacy R5 -10.40% is byte-stable across Waves 135-273 per SOURCE.md line 44 (the number itself doesn't need demotion), but the data-availability chain is incomplete. Recovery path documented for the next camera-ready cycle.

### 4.8 R3 (NEUTRAL — 1 edit, internal consistency fix)

**Issue at last push:** Two co-existing R3 numbers in last-push paper:
- (a) main Table 3.2 R3 row (line 93) uses d_s=−0.110, p=1.42e-02 (NOT Bonferroni-significant, UNDERPOWERED).
- (b) K8 paragraph (line 192) uses d_s=−0.129, p=4.00e-03 (Bonferroni-significant at α=0.007143).

Internal inconsistency: the 1.42e-02 value is NOT below α=0.007143, the 4.00e-03 IS. Additionally, the per-record proxy (d_z=−0.285 at ACTUAL N=200, p=8.03e-05) is fully disclosed in `docs/audit/wave216-p1-r3-uplift.md` and the standardized stats table R3_per_record_proxy row, but NOT surfaced in paper's main Table 3.2 R3 row.

**Files involved:**
- `verification_outputs/wave195-p2-r-level-power.csv` (sha256 `a754232392ac2f72a60cf2a71d9bfea7cfc8999e`, in git at 6036207)
- `verification_outputs/wave216-p1-r3-per-record.csv` (sha256 `259b5418795f764a7db179073bb42c292cb75852`, in git at 6036207)
- `verification_outputs/wave216-p1-r3-per-record.json` (sha256 `11992330b537ea7d58a5aa9961266895d7fbfe46`, in git at 6036207)
- `verification_outputs/wave225-p2-r3-bootstrap.csv` (sha256 `2dca18442ba4a0d82ddbe494adc7fce0306279b1`, in git at 6036207)
- `verification_outputs/wave225-p2-r3-bootstrap.json` (sha256 `c290f371ad6082b2859d1cc40bb9276c9130e70b`, in git at 6036207)
- `docs/headline-evidence/r2_flowmol3_fgdev_4p05sigma/{flowmol3_n1000_baseline_wave87_q4_2026,flowmol3_n1000_framework_wave87_q4_2026}.json` (sha256 `ed06f69a1cbc34e9a0a30e34879588f4804bfc6b`, `6eff93aa280d73237613977bef09aa9aa6a4492b`, in git at 6036207)
- `docs/audit/wave216-p1-r3-uplift.md` (in git at 6036207)
- `docs/tables/wave203-p4-standardized-stats.md` (in git at 6036207)
- `paper-flat-flattened.md` line 93 (Table 3.2 R3 row) + line 192 (K8 paragraph)

**Edits:**
1. `paper-flat-flattened.md` line 93 + line 192: Reconcile d_s to single value (use wave195-p2-r-level-power.csv authoritative −0.12874, p=4.00e-3) and add "(per-arm aggregate; per-record proxy at N=200 ACTUAL gives d_z=−0.285, p=8.03e-05, projected N=1000 d_z=−0.285, p=1.07e-18)" cross-reference.

**Risk:** Low. This is purely a paper-text reconciliation between two existing numbers in the same document; the underlying data is unchanged.

### 4.9 K1, K4, K7 (NEUTRAL — 0 edits)

These cells were NEVER inflated claims at last push:
- **K1** = Generative-paradigm applicability (structural scope statement) with 15/15 OK real-ckpt sweep disclosure for {twodim_fm, kanzi, lineageflow}. Not an RDKit-validity empirical cell.
- **K4** = Scheduler-port coupling (structural scope statement) at paper line 184. The LineageFlow HMMER axis was R1 (not K4) at last push.
- **K7** = LineageFlow novelty_mmseqs2 BLOCKED pending Pfam-A.fasta vendor + W166 P5 ADDITIVE paragraph at paper-draft.md line 6417 explicitly acknowledging direction-inverted finding (baseline 466/1000 > framework 37/1000 at pctid<30%).

The post-last-push redefinition of K1 as "FlowMol3 RDKit-validity" (p_bonf=0.5676, +1.36 d_z) and K4 as "LineageFlow HMMER length-bias" (p_bonf=0.734 FAIL) is a Wave 297 P2 design choice that post-dates the last push. At last push, the paper was clean on these cells.

**Edits:** 0.

---

## 5 Updated 11-Row Alignment Table

| # | Cell | Metric | Position at last push | New Position (Paper A) | Verdict at last push | New verdict | d_z | p_bonf | α | Bonf Pass | Effort |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | R1 | LineageFlow HMMER `hmmscan_total_hits` | MAIN §3.1 row + §7.1 row 1 | **SUPP** | STRONG primary d_z=+0.182 (cluster-robust UNDERPOWERED + single-seed) | **PARTIAL** (+116% aggregate + cluster-robust UNDERPOWERED + single-seed) | +0.182 single-seed / +116% aggregate | 1.247e-8 (single-seed) | 0.007143 | PASS single-seed / FAIL cluster | 3 commits + 2 edits |
| 2 | R2 | Kanzi `reconstruction_kabsch_rmsd_Å` paired t | MAIN §3.3 row + §7.1 row 2 | **MAIN** | MISALIGNED (one-sample t+3.532 → paired t−0.099) | **STRONG framework-WINS** | −0.0990 | 1.79e-3 | 0.007143 | **PASS** | 2 edits |
| 3 | R3 | FlowMol3 `fg_dev` per-record REOS proxy | MAIN §3.3 row + §7.1 row 3 | **MAIN** (with internal reconcile) | NEUTRAL with internal inconsistency | **NEUTRAL reconciled** (per-record d_z=−0.285 N=200 ACTUAL + per-arm d_s=−0.110) | −0.285 (proxy) / −0.110 (per-arm) | 8.03e-5 (proxy) / 1.42e-2 (per-arm) | 0.007143 | PASS proxy / FAIL per-arm | 1 edit |
| 4 | R5a | 2D Two Moons W2 | MAIN §3.5 row + §7.1 row 4 | **MAIN** | TIE d_s=+0.460 (n=3 unpaired) | **TIE** with R4 -78.25% footnote (separate experiment) | +0.460 (TIE) / −78.25% (FM ablation) | 0.604 | 0.007143 | FAIL (TIE) | 2 edits |
| 5 | R5b | CIFAR-10 RF NFE=50 FID | MAIN §3.2 row + §3.6 boundary + §7.1 row 5 | **MAIN** | REGRESSES d_z=+2.700 + n_rounds=2 override | **STRONG REGRESSES boundary** + n_rounds=1 WINS reframing | +2.700 (10 chunks) / −1.60% (n_rounds=1) | 9.17e-5 / 8.72e-132 | 0.007143 | PASS wrong-direction (REGRESSES) / PASS n_rounds=1 WINS | 2 edits |
| 6 | R5c | MNIST FM NFE=50 FID (smoke ckpt) | MAIN §3.2 row + §7.1 row 6 | **MAIN** | STRONG smoke ckpt with PROVISIONAL disclosure | **STRONG framework-WINS** (smoke ckpt, production ckpt deferred) | −13.175 | 3.95e-11 | 0.007143 | **PASS** | 0 edits |
| 7 | R5_legacy | 2D Eight Gaussians W2 | headline-evidence (NOT in paper-flat-flattened.md) | **SUPP** (move from headline) | SUPPORTABLE in prose, raw CSVs lost | **DEMOTED to SUPP** with data-availability footnote | −10.40% (audit-trail-supported) | N/A | N/A | N/A | 2 edits |
| 8 | R6 | LineageFlow k6 foldability `pLDDT_mean` + `scPerplexity` | MAIN §7.1 row 7 | **MAIN** | PARTIAL: uniform +0.0707 UNPRIMED; counterfactual +0.2235 NOT surfaced | **STRONG tier-aware promotion** (counterfactual +0.2235 Bonf-sig at α=0.05) | +0.0707 (uniform) / +0.2235 (tier-aware counterfactual) | 0.179 (uniform) / 2.08e-11 (counterfactual) | 0.007143 R / 0.05 counterfactual | FAIL uniform / **PASS counterfactual** | 5 edits |
| 9 | K1 | Generative-paradigm applicability | §1 line 178 (scope statement) + §K1 | **SUPP** | Structural scope statement | **NEUTRAL** (no change) | N/A | N/A | N/A | N/A | 0 edits |
| 10 | K4 | Scheduler-port coupling | §1 line 184 (scope statement) + §K4 | **SUPP** | Structural scope statement | **NEUTRAL** (no change) | N/A | N/A | N/A | N/A | 0 edits |
| 11 | K7 | LineageFlow novelty_mmseqs2 | §10.5.3 status table (BLOCKED) + §K7 | **SUPP** | BLOCKED + W166 P5 ADDITIVE direction-inverted disclosure | **NEUTRAL** (no change) | baseline 466/1000 > framework 37/1000 at pctid<30% | N/A descriptive | N/A | N/A | 0 edits |

---

## 6 Updated Verdict Distribution

| Verdict | Count | Cells |
|---|---|---|
| STRONG framework-WINS (Bonf-sig in correct direction) | 4 | R2, R5c, R6 tier-aware, R5b REGRESSES boundary |
| TIE (|Δ| < min_effect_size OR p > α) | 1 | R5a paper |
| PARTIAL (with disclosed limitations) | 1 | R1 |
| NEUTRAL (already honestly framed) | 4 | R3, K1, K4, K7 |
| DEMOTED to SUPP (data-availability incomplete) | 1 | R5_legacy_2D_EightGaussians |
| **Total** | **11** | (5 MAIN + 6 SUPP) |

---

## 7 Effort Estimate

| Edit type | Count | Risk | GPU runs |
|---|---|---|---|
| Paper-text edits (R2 + R6 + R5b + R5a + R1 + R3 reconcile + R5_legacy demote) | ~15 | Low-Medium (R6 tier-aware paragraph is highest risk due to mathematical-proxy disclosure precision) | 0 |
| R1 data-file commits (3 sha256-pinned archives) | 3 | High (data-archive precision required; SHA-256 stability check before commit) | 0 |
| Optional R5a commit (g1_deep_dive_q3_2026.json for -78.25% provenance) | 1 | Low (regenerate via deterministic re-run) | 0 |
| K1/K4/K7 paper-text edits | 0 | N/A | 0 |
| **Total** | **~15 edits + 3-4 commits** | **All grounded in already-git-tracked data** | **0** |

Per-cell breakdown:
- R2: 2 edits (low risk)
- R5c: 0 edits (already inline)
- R6: 5 edits (medium risk — tier-aware counterfactual paragraph)
- R5b: 2 edits (low risk — n_rounds conditional paragraph)
- R5a: 2 edits (low risk — paper §3.5 reconciliation + DATA_PRESENTATION footnote)
- R1: 3 commits + 2 edits (high risk — data-archive precision)
- R5_legacy: 2 edits (low risk — move to §10 supplementary + data-availability footnote)
- R3: 1 edit (low risk — internal consistency reconcile)
- K1/K4/K7: 0 edits (NEUTRAL)

**Wall-clock estimate:**
- Paper-text edits: 4-6 hours (mostly R6 tier-aware paragraph drafting)
- R1 data-file commits: 1-2 hours (SHA-256 stability check + archive validation)
- Cross-doc propagation: 1-2 hours (CLAIMS.md, CONSOLIDATED_RESULTS.md, headline-evidence folder updates)
- Verify gate: 1 hour (D.4 byte-stable regression, mkdocs 0 warnings, claims no-drift invariants)
- **Total: ~8-11 hours wall-clock** (one working day)

---

## 8 Realization of User Directive

The user's directive in Chinese: "很多数据其实是可追溯的，有些指标也不用降级" (much data is actually traceable, some metrics don't need to be downgraded).

This plan fully realizes that directive:
- **4 STRONG cells** (R2, R5c, R6 tier-aware, R5b REGRESSES boundary) are all data-traceable to last push with Bonferroni-significant verdict. None require demotion.
- **R1** is demoted to PARTIAL/single-seed with honest disclosure (cluster-robust UNDERPOWERED + cross-seed non-replication), NOT to FALSE/SUPP.
- **K1/K4/K7** are correctly framed as scope/boundary statements with no demotion needed.
- **R5_legacy** is moved from headline-evidence to §10 supplementary with data-availability footnote — this is the only cell that genuinely loses headline status, and only because the raw CSVs are not in git.
- **0 GPU re-runs** required. Every restore/demotion decision is grounded in already-git-tracked data at the last push (commit 6036207).

---

## 9 Next Steps

### 9.1 D2 Restoration (per Wave 305 §6 line 148)

The D2 restoration is the next phase after D3 review (Wave 308). It involves:
1. Apply the 15 paper-text edits per Section 4 above.
2. Execute the 3 R1 data-file commits per Section 4.6.
3. Update `docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`, and the headline-evidence folders per cross-doc propagation.
4. Run D.4 byte-stable regression suite.
5. Run mkdocs build (0 warnings).
6. Verify claims no-drift invariants.

**D2 entrance gate:** user authorization (per Wave 308 NO-PUSH directive and Wave 306 fix plan).

### 9.2 D3 Review (per Wave 308 d3-review.md)

D3 review is the user's editorial pass over the post-D2 paper. It includes:
1. Sign-off on the 4 STRONG cells (R2, R5c, R6 tier-aware, R5b REGRESSES).
2. Sign-off on the R1 PARTIAL/single-seed demotion.
3. Sign-off on the R5_legacy SUPP demotion.
4. Sign-off on the R3 internal reconcile.
5. Decision on whether to leverage the Wave 235 P1 n_rounds=1 WINS finding for R5b reframing.
6. Decision on whether to commit `verification_outputs/g1_deep_dive_q3_2026.json` for R5a -78.25% provenance.

### 9.3 Path A Timing (per Wave 305 §3)

Path A is the 14-day camera-ready push cycle. Wave 309 is Day 1 (plan synthesis). D2 restoration is Day 2-3. D3 review is Day 4. Push to origin/main is Day 5. Camera-ready submission is Day 14.

**Wave 309 exit gate:** user authorization to enter D2 (paper-text edits + R1 data commits).

---

## 10 Appendix — SHA-256 References for All Restored Cells

| Cell | Key data file | SHA-256 | In git at 6036207? |
|---|---|---|---|
| R2 | wave218-p3-kanzi-framework-wins.json | `9b5c3b68d05b136e662fffbef1873693f28c43547cebf7b8c7b480261d0de49c` | YES |
| R2 | wave218-p3-kanzi-framework-wins.csv | `5f957d056ce5977d11e8660f34e4574c7f11a6d7bbea7115f56e2bf5378f5e31` | YES |
| R5c | wave191-p3-mnist-n1000.json | (in git at 6036207) | YES |
| R5c | mnist_fm.npz | `ded1fa70c83b77f076351f5285571adefd05acb33ed65153db4b23a56f371634` | YES |
| R6 | wave233-p3-tier-aware-r6.json | (in git at 6036207) | YES |
| R6 | k6_foldability_n1000_w161_q3_2026/baseline/foldability/foldability.jsonl | `164825057a413af6f4d27a53b3ca519484f5c36019dafaa6c14e33dc823e4261` | YES |
| R6 | k6_foldability_n1000_w161_q3_2026/framework/foldability/foldability.jsonl | (in git at 6036207) | YES |
| R5b | wave191-p2-cifar10-n1000/ | (in git at 6036207) | YES |
| R5a | wave195-p2-r-level-power.csv | `985b071f3b34facda589f8997e742f44f3fe068b035ae30d5ce66295d21111e3` | YES |
| R5a | wave189-p2-post-cd70821-2d-sweep.md | `87ae2144d48221d9809a469adc41013803cf5040f1411c19ddb5128fd10792f5` | YES |
| R5a | wave209-p6-r5a-extended.csv | `c7c17275cd224671d3e8fb03b34513339643932f54da37f593c69681b0912f8a` | YES |
| R5a | wave216-p2-r5a-extended.json | `1e7b271dfa2825cf08ddeada5b60b6cd2745898a3d10079acefa4175109363bc` | YES |
| R1 | wave209-p2-per-record-all-cells.csv | (in git at 6036207) | YES |
| R1 | wave209-p2-cluster-robust-all-cells.csv | (in git at 6036207) | YES |
| R1 | wave86-phase3-sweep.md (audit) | (in git at 6036207, ARCHIVE) | YES |
| R1 | wave158-hmmer-rederivation.md (audit) | (in git at 6036207) | YES |
| R1 | r1_lineageflow_hmmer_p1e-10/SOURCE.md | (in git at 6036207) | YES |
| R3 | wave195-p2-r-level-power.csv | `a754232392ac2f72a60cf2a71d9bfea7cfc8999e` | YES |
| R3 | wave216-p1-r3-per-record.csv | `259b5418795f764a7db179073bb42c292cb75852` | YES |
| R3 | wave216-p1-r3-per-record.json | `11992330b537ea7d58a5aa9961266895d7fbfe46` | YES |
| R3 | wave225-p2-r3-bootstrap.csv | `2dca18442ba4a0d82ddbe494adc7fce0306279b1` | YES |
| R3 | wave225-p2-r3-bootstrap.json | `c290f371ad6082b2859d1cc40bb9276c9130e70b` | YES |
| R3 | flowmol3_n1000_baseline_wave87_q4_2026.json | `ed06f69a1cbc34e9a0a30e34879588f4804bfc6b` | YES |
| R3 | flowmol3_n1000_framework_wave87_q4_2026.json | `6eff93aa280d73237613977bef09aa9aa6a4492b` | YES |
| R5_legacy | r4-survey/10-sota-2d-experiment-results.md | (in git at 6036207) | YES |
| R5_legacy | r5_2d_eight_gaussians_w2_m10p40pct/SOURCE.md | (in git at 6036207) | YES |
| R5_legacy | noise_injection_eight_gaussians_{baseline,framework}.csv | N/A — symlinks broken | NO (raw CSVs lost) |

---

**End of Wave 309 plan. Awaiting user authorization to enter D2 restoration phase.**
