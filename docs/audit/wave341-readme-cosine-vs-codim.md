# Wave 341 — README Cosine vs Codim Scheduler Audit

**Date:** 2026-09-25
**Author:** Wave 341 cosine-vs-codim audit agent (READ-ONLY investigation)
**Status:** ACTIVE — read-only audit; no code, claim, or headline number changed
**Scope:** README.md + README.zh.md Headline Results table (lines 140-150) + per-cell `verification_outputs/` data files + `docs/CLAIMS.md` scheduler claims
**Trigger:** User request "readme里的数据能不能查到（数据应该是对的，但是用的是cosine而不是codim）" — dig deeper into whether README headline numbers are correctly attributable to the codim scheduler, given that 6/7 headline cells cite a framework_WINS verdict.

---

## 1. TL;DR

The README is **honest about the cosine-vs-codim boundary** (the scheduler-scope banner at line 16 of both README.md and README.zh.md discloses it), but the **Headline Results table does not show per-cell scheduler attribution** and the **Baseline/Framework columns for R5b are sourced from a DIFFERENT verification file than the Δ% column**. Specifically:

| Cell | Baseline / Framework values | Δ% range | Scheduler used (verified) | Codim tested? |
|---|---|---|---|---|
| R1 | 158 / 342 | +116.46% | CosineAnnealScheduler (default; not explicitly tested) | **NO** |
| R2 | reference / d_z=−0.0990 | Bonf-sig p=0.0018 | **NO scheduler** — `framework_inv_proj` mode (synthetic x_final + trained Linear(512→4) inverse projection; see `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:154` + `tools/_kanzi_sweep_runner.py:367`) | **NO** |
| R3 | reference / d_z=−0.285 | Bonf-sig <1e-4 | **NO scheduler** — "small Gaussian perturbation applied to the canonical prior before upstream sampling" (Wave 87 Agent C) | **NO** |
| R4 | 2.85 / 0.62 | −78.25% | "single_pass → multi_round_no_restart" — scheduler choice undocumented in the headline-evidence JSON | **NO** (not in headline-evidence) |
| R5 | 2.31 / 0.76 | −67.10% | "single_pass → multi_round_no_restart" — scheduler choice undocumented | **NO** (not in headline-evidence) |
| R5b | **218.87 / 122.18** (v2 NFE-averaged source) | **−2.53% to −0.66%** on "3/4 schedulers" (rounds1 matched-NFE source) | **All 4 schedulers tested** at n_rounds=1 (cosineanneal / codimensionsheet / evidencedriven / freetraj) | **YES** (1 of 4 schedulers) |
| R6 | +0.224 / +0.647 | +189% (grid best) | **TierAwareCodimensionSheetScheduler** (counterfactual grid search) | **YES** (only headline cell using codim) |

**Headline findings:**

1. **CRITICAL — R5b row mixes two verification sources.** The Baseline 218.87 / Framework 122.18 numbers come from `verification_outputs/g1_deep_dive_q3_2026.json#rectified_flow_cifar_v2_avg_nfe` (v2 NFE-averaged; "NOT fair comparison; baseline 2-NFE vs framework avg 5-NFE"). The Δ% range "−2.53% to −0.66%" comes from `verification_outputs/wave235-p1-r5b-fix.json#rounds1` (matched NFE=50, baseline_fid=454.39 not 218.87). The ver. link in the README points to `wave235-p1-r5b-fix.json` but the Baseline/Framework columns do NOT match that file.

2. **HIGH — R5b "3/4 schedulers" is wrong.** The README says "−2.53% to −0.66% on 3/4 schedulers". The actual `wave235-p1-r5b-fix.json#rounds1` data shows **4/4 schedulers win** (cosineanneal −1.60%, codimensionsheet −2.53%, evidencedriven −0.12%, freetraj −0.66%). The README is dropping evidencedriven (−0.12%) from the range without explanation; the paper draft line 369 says "at `n_rounds = 1` the framework WINS 4/4 schedulers".

3. **MEDIUM — Headline Results table has no per-cell "Scheduler" column.** Readers of the headline table cannot tell which scheduler was used for each cell without reading the per-cell verification scripts. The scheduler-scope banner at line 16 mentions this for the headline block, but the table itself is scheduler-agnostic. The paper draft line 181 enumerates this: "Only R6 (k6 foldability) wires a theoretical-perspective headline (TierAwareCodimensionSheetScheduler wrapping CodimensionSheetScheduler)".

4. **MEDIUM — R2/R3 framework arms do not use a scheduler at all.** R2 (Kanzi) `framework_inv_proj` synthesizes x_final from N(0, sigma=1e-3) and routes it through a trained Linear(512→4) inverse projection (`tools/kanzi_latent_to_coord.py`, sha `5ab6234d...`). R3 (FlowMol3) framework arm is a "small Gaussian perturbation applied to the canonical prior before upstream sampling" (`tools/wave87_n1000_sweep.py:11-13`). Neither uses a `SchedulerProtocol` implementation; both produce a framework_WINS verdict by **structural property of the synthetic test**, not by scheduler choice.

5. **LOW — CodimensionSheetScheduler partial validation status is correct.** Per CLM-006 Wave 292 addendum: "CodimensionSheetScheduler is **research-stage** in the cosine-baseline deployment. Of the 13 R-cell + weak-claim headline sweeps, only 1 (R6's tier-aware counterfactual) wraps CodimensionSheetScheduler; the other 12 use CosineAnnealScheduler."

**Honest assessment:** The README headline numbers are **numerically correct** (the data points themselves are sourced from real verification artefacts), but the **scheduler attribution is incomplete** for 6/7 cells (only R6 explicitly uses codim; R5b tested codim as one of 4 schedulers but its Δ% range is sourced from a different file than its Baseline/Framework columns). The user's intuition is correct: most "framework_WINS" verdicts in the headline table are NOT attributable to the codim scheduler. They come from (a) the default CosineAnnealScheduler (R1), (b) synthetic / perturbation-based framework arms (R2, R3, R4, R5), or (c) only R6 uses codim.

**Recommendation:** Apply Wave 341 P1-P3 surgical fix train (additive only; no number changes):

- **P1 — add a "Scheduler" column to the Headline Results table** (README.md line 140-148 + README.zh.md line 130-138) showing the scheduler used for each row: CosineAnnealScheduler (R1), `framework_inv_proj` synthetic (R2), Gaussian-perturbation (R3), `multi_round_no_restart` (R4, R5), 4 schedulers / codim-tested (R5b), TierAwareCodimensionSheetScheduler (R6).
- **P2 — fix the R5b row data-source inconsistency.** Either (a) replace the Baseline 218.87 / Framework 122.18 with the rounds1 baseline_fid 454.39 + per-scheduler framework FIDs (447.11 / 442.89 / 453.85 / 451.37), or (b) cite the v2 source for the columns and remove the rounds1 Δ% range. Per Wave 268 strict-clean rule, pick the cleaner option: option (a) preserves the rounds1 matched-NFE finding (the load-bearing framework_WINS for R5b).
- **P3 — fix the R5b "3/4 schedulers" wording to "4/4 schedulers"** matching the actual data and the paper draft line 369.

After P1-P3: re-run `python3 tools/check_claims_consistency.py` + `mkdocs build --strict` + `ruff check` to verify gates preserved. No claim text edits; only README headline-table wording (which is owned by `flowa-paper-evidence`, not `flowa-research-audit`, per AGENTS.md §2.1).

---

## 2. Background: the two scheduler families

The framework exposes 13 schedulers partitioning into:

- **9 baselines** (no paper quantities): `CosineAnneal | Constant | Linear | Exponential | Polynomial | Sigmoid | AdaptivePID | EDM | FreeTraj`
- **4 paper-quantity-driven controllers**: `CodimensionSheetScheduler | PaperRatioAdaptiveScheduler | EvidenceDrivenScheduler | ConvergenceAdaptiveScheduler`

The paper-quantity-driven controllers consume `A_g / B_g / C_g / e_rho` from `adaptive_reflow/contracts/paper_quantities.py` [CLM-011]. Per Wave 292 / Wave 297 addenda, **15 of 16 application sites are dormant under the validated cosine baseline**; Wave 296 `PaperQuantitiesCache` opt-in is in-progress for full activation.

Per `docs/drafts/paper-A-final.md:181` (the canonical paper-draft paragraph on scheduler usage):

> "Of the 13 families, only `CosineAnnealScheduler` is the headline scheduler on 12/13 R-cells (R1 LineageFlow HMMER, R2 Kanzi byte-stable composite, R3 FlowMol3 fg_dev, R5a 2D Two Moons, R5b CIFAR-10 RF, R5c MNIST FM smoke + production, K1 FlowMol3 RDKit, K3+R5b CIFAR-10 RF fix, K4+K5 LineageFlow, K7 LineageFlow novelty). Only R6 (k6 foldability) wires a theoretical-perspective headline (`TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler`). The 4 optional theoretical-perspective controllers consume companion quantities and were designed for them, but appear as headline on none of the 13 R-cells. This usage pattern means the historical headline numbers are the cosine-arm reading, not the theoretical-perspective reading."

---

## 3. Per-cell scheduler audit (the 7 R-level headlines)

For each R-level headline in the README Headline Results table (line 142-148), I traced (a) the verification source file, (b) which scheduler (if any) was used, and (c) whether the codim scheduler was tested.

### 3.1 R1 — LineageFlow HMMER (158 → 342, +116.46%)

| Field | Value |
|---|---|
| README headline | `Baseline 158, Framework 342, Δ +116.46%, p ≈ 1.5e-08, framework_WINS` |
| Verification source | `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/{baseline,framework}_hits.tbl` |
| Scheduler used | **CosineAnnealScheduler** (default — no scheduler override in `scripts/wave202_p5_lineageflow_n1000_paired.py`; the script reads pre-computed foldability.jsonl + self_consistency.jsonl from Wave 204 P2 resume run at `/tmp/w202-lineageflow/baseline/{baseline,framework}/`) |
| Codim tested? | **NO** — the framework arm is the framework's re-inference loop applied to LineageFlow, which uses `CosineAnnealScheduler` as the headline scheduler per CLM-006 Wave 292 addendum |
| Severity | LOW — disclosed in scheduler-scope banner at line 16 |
| Recommendation | Add "Scheduler: CosineAnnealScheduler" to the row in the Headline Results table |

### 3.2 R2 — Kanzi RMSD (d_z = −0.0990, Bonf-sig p=0.0018)

| Field | Value |
|---|---|
| README headline | `d_z = -0.0990, p_raw = 1.79e-3, framework_WINS, §7.6.2` |
| Verification source | `verification_outputs/wave218-p3-kanzi-framework-wins.json` |
| Scheduler used | **NONE** — R2 framework arm uses `framework_inv_proj` mode (`tools/sweep_kanzi_n1000_framework_paper_metrics.py:184`), which synthesizes x_final from N(0, sigma=1e-3) and routes it through a trained Linear(512→4) inverse projection at `tools/kanzi_latent_to_coord.py` (sha `5ab6234d20e2421452eea65a54e422e560d7efaf8115c475584ab95deee0df2a`). This is a synthetic test that does NOT use a `SchedulerProtocol` implementation. |
| Codim tested? | **NO** |
| Severity | MEDIUM — the framework_WINS verdict is a structural property of the synthetic test (small noise + trained inverse projection wins on reconstruction by construction), not a scheduler verdict |
| Recommendation | Disclose "Scheduler: NONE (framework_inv_proj synthetic x_final)" in the Headline Results row |

### 3.3 R3 — FlowMol3 fg_dev (d_z = −0.285, Bonf-sig <1e-4)

| Field | Value |
|---|---|
| README headline | `d_z = -0.285, Bonf-sig <1e-4, framework_WINS, §7.6.3` |
| Verification source | `verification_outputs/wave216-p1-r3-per-record.json` |
| Scheduler used | **NONE** — R3 framework arm is "a small Gaussian perturbation applied to the canonical prior before upstream sampling" per `tools/wave87_n1000_sweep.py:11-13`. The actual sweep data (`verification_outputs/flowmol3_n1000_sweep_wave87_q4_2026.json`) shows framework `perturbation_sigma: 0.05` vs baseline `perturbation_sigma: 0.0`. This is NOT a scheduler-driven multi-round re-inference loop. |
| Codim tested? | **NO** |
| Severity | MEDIUM — same structural-property concern as R2 |
| Recommendation | Disclose "Scheduler: NONE (Gaussian-perturbation framework arm)" in the Headline Results row |

### 3.4 R4 — 2D Two Moons W₂ (2.85 → 0.62, −78.25%)

| Field | Value |
|---|---|
| README headline | `Baseline 2.85, Framework 0.62, Δ -78.25%, framework_WINS (raw Δ%), §7.6.4` |
| Verification source | `verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation` |
| Scheduler used | **"single_pass → multi_round_no_restart"** (per `g1_deep_dive_q3_2026.json:23` note field). The note says "best head-to-head" but the scheduler choice is **not specified in the JSON**. The source citation is `CONSOLIDATED_RESULTS §4.1`. |
| Codim tested? | **NO** — neither headline-evidence nor CONSOLIDATED_RESULTS §4.1 explicitly identifies the scheduler |
| Severity | LOW — disclosure needed for completeness |
| Recommendation | Add "Scheduler: multi_round_no_restart (scheduler-choice unspecified)" or trace the source to identify the scheduler |

### 3.5 R5 — 2D Eight Gaussians W₂ (2.31 → 0.76, −67.10%)

| Field | Value |
|---|---|
| README headline | `Baseline 2.31, Framework 0.76, Δ -67.10%, framework_WINS (raw Δ%), §7.6.5` |
| Verification source | `verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_eight_gaussians` |
| Scheduler used | Same as R4: "single_pass → multi_round_no_restart". The CONSOLIDATED_RESULTS §4.2 entry does not specify the scheduler. |
| Codim tested? | **NO** |
| Severity | LOW |
| Recommendation | Same as R4 |

### 3.6 R5b — CIFAR-10 RF FID (Baseline 218.87, Framework 122.18, Δ −2.53% to −0.66% on "3/4 schedulers")

| Field | Value |
|---|---|
| README headline | `Baseline 218.87, Framework 122.18, Δ -2.53% to -0.66% on 3/4 schedulers, framework-WINS, §7.6.7` |
| Verification source cited in README | `verification_outputs/wave235-p1-r5b-fix.json` |
| **Actual data in `wave235-p1-r5b-fix.json#rounds1`** | `baseline_fid: 454.39` (NOT 218.87); 4 schedulers tested (NOT 3/4): cosineanneal FID 447.11 (Δ −1.60%), codimensionsheet FID 442.89 (Δ −2.53%), evidencedriven FID 453.85 (Δ −0.12%), freetraj FID 451.37 (Δ −0.66%) |
| Scheduler used | **All 4 schedulers tested** at `n_rounds=1` (matched NFE=50). The README cites this file but reports columns from a different source. |
| Codim tested? | **YES** — codimensionsheet is one of the 4 schedulers (Δ −2.53%, the best result of the 4) |
| Severity | **CRITICAL** — Baseline/Framework columns and Δ% range are from different verification sources (v2 NFE-averaged vs rounds1 matched-NFE). The "3/4 schedulers" wording is wrong; actual data shows 4/4 schedulers win. |
| Recommendation | (a) Replace Baseline 218.87 / Framework 122.18 with the rounds1 actual baseline_fid 454.39 + per-scheduler framework FIDs. (b) Change "−2.53% to −0.66% on 3/4 schedulers" to "−2.53% to −0.12% on 4/4 schedulers (cosineanneal / codimensionsheet / evidencedriven / freetraj)" matching the paper-draft line 369 ("at `n_rounds = 1` the framework WINS 4/4 schedulers") |

### 3.7 R6 — k6 foldability (d_z +0.224 → +0.647, +189%)

| Field | Value |
|---|---|
| README headline | `Baseline +0.224, Framework +0.647, Δ +189%, framework_WINS (cluster-robust 5/8 SUPPORTED)` |
| Verification source | `verification_outputs/wave235-p3-r6-uplift.json` |
| Scheduler used | **`TierAwareCodimensionSheetScheduler`** (counterfactual grid search over `easy_factor × hard_intensity` on the k6 N=1000 paired foldability sweep; the only headline cell that explicitly uses a codim-family scheduler) |
| Codim tested? | **YES** — this is the load-bearing codim headline |
| Severity | LOW — correct attribution |
| Recommendation | Add "Scheduler: TierAwareCodimensionSheetScheduler" to the Headline Results row (the only cell that should be highlighted as a codim use) |

---

## 4. The R5b data-source inconsistency (the load-bearing finding)

The R5b headline has a critical issue that the user is exactly right to be concerned about: **the Baseline/Framework columns and the Δ% range come from two different verification sources**.

| README column | Source | Value |
|---|---|---|
| Baseline 218.87 | `verification_outputs/g1_deep_dive_q3_2026.json#rectified_flow_cifar_v2_avg_nfe` | 218.87 (v2 NFE-averaged, "NOT fair comparison") |
| Framework 122.18 | `verification_outputs/g1_deep_dive_q3_2026.json#rectified_flow_cifar_v2_avg_nfe` | 122.18 (v2 NFE-averaged) |
| Δ −2.53% to −0.66% | `verification_outputs/wave235-p1-r5b-fix.json#rounds1` (matched NFE=50, baseline_fid 454.39) | -2.53% (codim) to -0.12% (evidencedriven); the README range -2.53% to -0.66% is 3 of the 4 schedulers |
| `framework-WINS` | Both | confirmed at rounds1 for all 4 schedulers |

**Direct comparison shows the inconsistency:**

- If Baseline=218.87 and Framework=122.18, then Δ = (122.18 - 218.87) / 218.87 = -44.17% (v2 reading)
- If Δ = -2.53% to -0.66%, then Framework should be ~217.34 to 213.43 (assuming Baseline=218.87), but 122.18 is far outside this range

The README is reporting v2 (NFE-averaged, unfair comparison) baseline/framework numbers with rounds1 (matched-NFE, fair comparison) Δ% range. This is internally inconsistent.

Per `docs/CONSOLIDATED_RESULTS.md:176-178`:

> | v1 | (initial baseline) | 218.87 | (n/a) | — | — |
> | **v2** | framework 2-NFE → avg 5-NFE | 218.87 | **122.18** | **-44.17%** | ~25 min (CPU) |
> | v3 | matched NFE=2 (cosine ramps all round to 1-2) | 218.87 | 222.16 | +1.5% (noise) | — |

The v2 218.87/122.18 reading is "framework 2-NFE → avg 5-NFE" — a **NOT fair comparison** per the same file. The README headline is reporting v2's baseline and v2's framework alongside v3/rounds1's Δ% range. This is a data-source mix-up.

**Recommendation (per Wave 268 strict-clean rule, pick the cleaner option):** Replace the Baseline/Framework columns with the rounds1 baseline_fid 454.39 + per-scheduler framework FIDs, and keep the rounds1 Δ% range "−2.53% to −0.12% on 4/4 schedulers". This preserves the load-bearing framework_WINS at matched NFE=50 (the headline finding) and removes the v2 confusion.

---

## 5. Cross-doc consistency check

| Source | Scheduler disclosure for R1-R6 |
|---|---|
| `README.md` line 16 (scheduler-scope banner) | "All 7 headline numbers ... were produced under `CosineAnnealScheduler` (the controller that ignores all 4 paper quantities). `CodimensionSheetScheduler` and the other paper-quantity-grounded controllers ... are research-stage" |
| `README.md` line 142-148 (Headline Results table) | **No per-cell scheduler column** |
| `README.md` line 154-160 (One-line summary per cell) | **No scheduler mention** |
| `README.zh.md` line 16 | Bilingual mirror of scheduler-scope banner (correct) |
| `docs/drafts/paper-A-final.md:181` | "the historical headline numbers are the cosine-arm reading, not the theoretical-perspective reading" (the canonical paper-draft paragraph) |
| `docs/CLAIMS.md:117-138` (CLM-005 + CLM-006 Wave 292 addenda) | CodimensionSheetScheduler is **research-stage** in cosine-baseline deployment; only R6 wraps CodimensionSheetScheduler |
| `docs/CLAIMS.md:3966-3970` | "CLM-005/006/011/012 remain ACTIVE at the implementation level — they describe what the code does — but their headline-pivot interpretation is research-stage / Wave 287 + Wave 291 audit pending" |

The scheduler disclosure is **scattered across 3+ locations** and **not directly tied to the headline table**. A reader scanning only the Headline Results table cannot determine scheduler attribution without consulting the scheduler-scope banner, the paper draft, or CLAIMS.md.

---

## 6. Verification path for the proposed fixes

Per AGENTS.md §3 hard guardrail #7 ("Stricter = cleaner — per Wave 268, pick the cleaner option"), the proposed fix is the minimal additive change that closes the disclosure gap without modifying any claim number.

If the user opts into the fix train:

```bash
# 1. Apply P1 (add Scheduler column to README headline table)
# 2. Apply P2 (fix R5b data-source inconsistency)
# 3. Apply P3 (fix R5b "3/4 schedulers" to "4/4 schedulers")
# 4. Apply P1-P3 to README.zh.md bilingual mirror

# Verify
python3 tools/check_claims_consistency.py  # must exit 0
mkdocs build --strict                       # must exit 0
ruff check README.md 2>/dev/null           # not applicable (markdown)

# No new commits in this wave (READ-ONLY per the user's request)
```

**No claim text changes** (the proposed edits are all to the README headline table, which is owned by `flowa-paper-evidence` per AGENTS.md §2.1, not `flowa-research-audit`). The fixes are additive disclosures + one source-mix correction on R5b.

---

## 7. PUSH status

This audit doc is **READ-ONLY investigation output**. No code, claim, or headline number has been modified. The push to `origin/main` is **BLOCKED at the USER permission gate** per Wave 325 directive; this audit doc is committed locally only when the user opts in.

**Status:** READ-ONLY AUDIT COMPLETE — recommendations §1 + §3 + §4 + §6 ready for user review before any Wave 341 P1-P3 fix train is launched.

---

## 8. References

- `README.md:14` (last-updated stamp)
- `README.md:16` (scheduler-scope banner — the existing cosine disclosure)
- `README.md:140-150` (Headline Results table — no per-cell Scheduler column)
- `README.md:154-160` (One-line summary per cell — no scheduler mention)
- `README.zh.md:16,130-150` (bilingual mirror of the above)
- `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/{baseline,framework}_hits.tbl` (R1 source)
- `verification_outputs/wave218-p3-kanzi-framework-wins.json` (R2 source)
- `verification_outputs/wave214-p2-kanzi-framework-inv-proj-n1000/checkpoint.json` (R2 framework mode = framework_inv_proj)
- `verification_outputs/wave216-p1-r3-per-record.json` (R3 source)
- `verification_outputs/flowmol3_n1000_sweep_wave87_q4_2026.json` (R3 framework = perturbation_sigma 0.05 vs baseline 0.0)
- `verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation` (R4 source)
- `verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_eight_gaussians` (R5 source)
- `verification_outputs/g1_deep_dive_q3_2026.json#rectified_flow_cifar_v2_avg_nfe` (R5b v2 NFE-averaged source for README Baseline 218.87 / Framework 122.18)
- `verification_outputs/wave235-p1-r5b-fix.json#rounds1` (R5b matched-NFE source for README Δ% range)
- `verification_outputs/wave235-p3-r6-uplift.json` (R6 source)
- `tools/sweep_kanzi_n1000_framework_paper_metrics.py:184` (R2 framework mode = framework_synthetic / framework_inv_proj)
- `tools/wave87_n1000_sweep.py:11-13` (R3 framework arm = "small Gaussian perturbation applied to the canonical prior")
- `tools/kanzi_latent_to_coord.py` (sha `5ab6234d...`, R2 trained Linear(512→4) inverse projection)
- `docs/drafts/paper-A-final.md:181` (paper-draft canonical paragraph on scheduler usage)
- `docs/drafts/paper-A-final.md:334,369` (R5b 4/4 schedulers framework-WINS at n_rounds=1)
- `docs/CONSOLIDATED_RESULTS.md:176-178` (R5b v2 NFE-averaged reading = "NOT fair comparison")
- `docs/CLAIMS.md:117-138` (CLM-005 + CLM-006 Wave 292 addenda — codim is research-stage)
- `docs/CLAIMS.md:3966-3970` (CLM-005/006 headline-pivot interpretation is research-stage)
- `docs/audit/wave297-p2-paper-design.md` (paper-narrative reframe to typed-contracts framework)
- `docs/audit/wave292-p1-pipeline-inventory.md` (16-site pipeline inventory; cos is default on 12/13 R-cells)
- `docs/audit/wave339-b6-fixes.md` (Wave 339 B6 fix #1: R5b FID range + Δ% aligned to CLM-070 Source-A — already addressed the v3 reading for `n_rounds=10`, but did NOT address the README headline-table mix-up with v2 numbers)

---

**End of Wave 341 audit doc.** No claim text or number has been modified; the document is a read-only investigation of the cosine-vs-codim boundary in the README Headline Results table.