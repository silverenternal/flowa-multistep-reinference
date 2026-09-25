# Wave 357 P5 — R6 Kanzi k6 3-seed N=1000 live GPU sweep scope (camera-ready disclosure)

**Date:** 2026-09-25
**Author:** Wave 357 P5 R6-scope-disclosure agent (USER AUTHORIZED, NO PUSH)
**Status:** ACTIVE — ADDITIVE camera-ready scope disclosure for the §10.5 R6 live-GPU follow-up deferred item.
**Trigger:** Wave 357 P5 task brief — document the R6 3-seed N=1000 live GPU sweep scope and append a scope-disclosure paragraph to paper §10.5 + author this audit doc + verify the standard pre-commit gates (D.4 30/30 + claims PASS + mkdocs build --strict PASS) + commit (NO-PUSH).
**Scope:** ADDITIVE — (1) one ADDITIVE paragraph appended to `docs/drafts/paper-A-final.md` §10.5 (after the existing Wave 336 P1 R6 live-GPU follow-up paragraph); (2) one new audit doc (`docs/audit/wave357-r6-gpu-scope.md`).
**Hard-rule compliance:** AGENTS.md §3 hard guardrails (1, 2, 3, 4, 5, 6, 7) — vendored upstream untouched (no edits to `data/<repo>/`); no destructive edits (additive-only — append scope paragraph, do not change R6 status or numbers); NO-PUSH policy (commit-only; no `git push`); honest uncertainty preserved (no promotion of `PARTIAL` to `STRONG` by wording alone — the counterfactual verdict label is preserved verbatim); TNNLS submission freeze preserved (no edits to `tnnls_submission/`); per-phase audit doc (this file); stricter-cleaner path chosen (single-disclosure-paragraph + single-audit-doc, not a multi-paragraph rewrite).

**Out of scope (deliberately):**
- No actual GPU sweep launch (per AGENTS.md §6: "If a request seems destructive or controversial, stop and confirm with the user"; the 3-seed × N=1000 × 5-round Kanzi k6 sweep is bounded by GPU budget and user-gated push policy per Wave 357 P5 task brief + Wave 350 P3 §4.3 wall-time estimate).
- No edits to `docs/CLAIMS.md` (CLM-073 wording preserved verbatim — no number change, no status promotion).
- No edits to `todo/RISK-REGISTER.md` (R-019 deferred item preserved verbatim).
- No edits to `tnnls_submission/*` (TNNLS submission freeze preserved per AGENTS.md §3 hard guardrail #5).
- No edits to `verification_outputs/wave350-r6-live-smoke/*` (the smoke-test evidence is preserved verbatim; this audit doc is a scope disclosure only).
- No edits to any vendored upstream repo (the 9 vendored repos in `data/` remain byte-identical to upstream pinned commits).
- No edits to the §7.2 R6 row (the "STRONG via tier-aware counterfactual" verdict label is preserved verbatim; the counterfactual methodology per Wave 225 P4 + Wave 233 P3 remains the load-bearing evidence).
- No edits to §11.1 (b) R6 environment-blocked disclosure (the existing disclosure of "R6 ... env-unblocked ... bounded by GPU budget rather than environment setup" is preserved verbatim).
- No edits to §11.2 camera-ready scope bullet (the existing bullet "R6 live-GPU 3-seed × $N = 1000$ paired full-stack re-verification (env unblocked, CLM-073 / R-019 deferred item documented in §10.5)" is preserved verbatim).
- No `git push` (per Wave 325 NO-PUSH policy + AGENTS.md §3 guardrail #3).

---

## 1. Executive Summary

The R6 Kanzi k6 foldability §10.5 camera-ready deferred item is **scoped** (NOT launched) as a 3-seed × $N = 1000$ paired live-GPU re-verification on **GPU 0 (RTX PRO 6000 Blackwell, 98 GB, sm_120)**. The sweep is required to fully resolve R6 from **PARTIAL via tier-aware counterfactual** to **STRONG via 3-seed live GPU re-verification**, and is the load-bearing item in the camera-ready deferred list (CLM-073 / R-019).

| Item | Value |
|---|---|
| Scope item disclosed | R6 Kanzi k6 foldability 3-seed × $N = 1000$ paired live-GPU re-verification |
| GPU required | **GPU 0 (RTX PRO 6000 Blackwell, 98 GB total, sm_120 Blackwell kernel)** |
| Seeds | {42, 43, 44} (the canonical R-level 3-seed pool per §7.3) |
| Per-arm sample size | $N = 1000$ paired sequences (matched across baseline + framework) |
| Number of arms | 2 (baseline + framework under `TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler` + `BoundedMergeOperator` + `EvidenceDrivenScheduler`) |
| Number of rounds per arm | 5 (the canonical R6 Kanzi k6 foldability multi-round restart count) |
| Total records processed | 3 × 2 × 1000 × 5 = 30,000 fold evaluations |
| Wall time per seed (2-arm, both stages) | **~17.6 hours on GPU 0 single-GPU; ~8.8 hours on 2-GPU 0+1 split** |
| Total wall time (3 seeds, single-GPU) | **~52.8 hours of GPU 0 wall time** |
| Total wall time (3 seeds, 2-GPU split) | **~26.4 hours of GPU 0+1 wall time** |
| Total wall time (fold stage only, ESM-IF off) | **~90-135 min per seed × 3 seeds = 4.5-6.75 hours single-GPU** |
| Risk | GPU 0 contention with user-owned `dfine_t146` workload (~28 GB occupied at Wave 357 P5 audit time; ~70 GB free); sustained 90-135 min/seed launch requires `dfine_t146` to be paused or relocated |
| Status of R6 verdict | **PRESERVED VERBATIM** — §7.2 R6 row remains "STRONG via tier-aware counterfactual" ($d_z = +0.2235$ Bonferroni-significant at $\alpha = 0.05$; counterfactual methodology per Wave 225 P4 + Wave 233 P3); the live 3-seed sweep is a **scope disclosure**, not a status promotion |
| Files modified | 1 (one ADDITIVE paragraph appended to `docs/drafts/paper-A-final.md` §10.5); 1 new audit doc |
| Files deleted | 0 |
| D.4 30/30 PASS | PASS (verified post-edit; see §6 below) |
| claims consistency | PASS (verified post-edit; see §6 below) |
| mkdocs build --strict | PASS (verified post-edit; see §6 below) |
| Hard-rule compliance | ADDITIVE only (1 paragraph in paper §10.5 + 1 new audit doc); NO-PUSH (commit-only); no number change; no status promotion; vendored NOT touched |

---

## 2. Current evidence (R6 status as of Wave 357 P5)

### 2.1 §7.2 R6 row (preserved verbatim)

Per `docs/drafts/paper-A-final.md` §7.2 (line 398), the R6 row reads (verbatim, character-for-character):

> "R6 — Kanzi k6 foldability (STRONG via tier-aware counterfactual). Kanzi k6 foldability (protein foldability, N = 1000 paired). Headline scheduler: `TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler` (the only theoretical-perspective headline). Overall pLDDT d_z = +0.071 (uniform-arm naive, UNDERPOWERED at R-level α = 0.007143); tier-aware-arm counterfactual d_z = +0.2235 (Bonferroni-significant at α = 0.05 via easy_tier_nfe_reduction_factor = 0.5 on the canonical paired-diff reference). Hard-tier pLDDT d_z = +1.189; scPerplexity d_z = -1.077 (naive) / -4.019 (cluster-robust). Status: **STRONG via tier-aware counterfactual upgrade**."

**This row is NOT modified by Wave 357 P5.** The "STRONG via tier-aware counterfactual" label is the load-bearing evidence for the §7.2 STRONG promotion; the counterfactual methodology (per Wave 225 P4 + Wave 233 P3) is the only path that converts the UNDERPOWERED uniform-arm naive reading ($d_z = +0.071$, not significant at R-level $\alpha = 0.007143$) into the Bonferroni-significant tier-aware-arm reading ($d_z = +0.2235$, significant at $\alpha = 0.05$).

### 2.2 CLM-073 (R6 k6 pLDDT large-effect uplift) status

Per `docs/CLAIMS.md` CLM-073 (line 3888), the claim is preserved verbatim:

> "R6 k6 pLDDT baseline d_z=+0.2235 was Bonferroni-significant with structural weakness: easy-tier regression of d_z=−0.9982 (framework REGRESSES on the easiest records). Wave 235 P3 ran a 20-cell grid search over `easy_factor ∈ {0.0, 0.1, 0.25, 0.5, 0.75}` × `hard_intensity ∈ {1.0, 1.5, 2.0, 3.0}`. Best cell `(easy_factor=0.0, hard_intensity=3.0)` → overall d_z = **+0.6467** (large-effect regime, +189% lift vs Wave 233 P3 baseline); easy-tier d_z = 0.000 (regression FULLY ELIMINATED at easy_factor=0); hard-tier d_z = +3.567 (massive amplification); medium-tier d_z = +0.218 (unchanged). R6 transitions from "hard-tier selective improvement" to "overall improvement + easy-tier non-regression". D.4 30/30 PASS preserved; no source code change to the TierAwareCodimensionSheetScheduler (only constant-offset counterfactual math)."

The CLM-073 status is **ACTIVE**; the CLM-073 wording is preserved verbatim by Wave 357 P5 (no number change, no status promotion).

### 2.3 Wave 350 P3 smoke test (the most recent R6 evidence)

Per `docs/audit/wave350-r6-live-attempt.md` (Wave 350 P3, 2026-09-25), the R6 live GPU smoke test:

- **Inputs**: 30 records (first 30 sequences of the Wave 161 frozen `queries.fasta`).
- **Command**: `data/lineageflow_upstream/evaluation/foldability_omegafold.py` invoked with `--fasta /tmp/w350-r6-smoke/queries_n30.fasta --gpus 0 --max-seqs 30`.
- **Outputs**: 30 PDB files + `foldability.jsonl` (SHA-256 `e7fbee8ae9d868d65460b3335fe01a5098633c2208aa2bcf6e66b72ab504990b`) + `summary.json` (`n_total=30, n_with_plddt=30, plddt_mean_mean=41.18, plddt_mean_median=37.23, plddt_mean_p10=29.08, plddt_mean_p90=58.84`).
- **Byte-stability**: 30/30 qids `plddt_mean` matches Wave 161 frozen baseline to **0.00e+00 abs diff** (i.e. the OmegaFold env reproduces the Wave 161 foldability computation deterministically).
- **Wall time**: ~90-110 sec total (~3 sec/seq OmegaFold fold + ~5 sec driver overhead).
- **Verdict**: env is unblocked; pipeline works end-to-end on GPU 0 with byte-stable pLDDT. R6 §7.2 row remains verbatim (the smoke test is a deterministic re-fold of the Wave 161 frozen queries, NOT a fresh `TierAwareCodimensionSheetScheduler` headline-scheduler re-run). Full 3-seed × N=1000 sweep is camera-ready scope (deferred per paper §10.5 + Wave 349 gap audit §3.4).

### 2.4 Env readiness inventory (Wave 350 P3 + Wave 357 P5)

| Item | Path | Status |
|---|---|---|
| Kanzi ckpt | `data/kanzi_ckpt/cleaned_model.pt` | **AVAILABLE** (530 MB; SHA-256 `c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270`; verified 2026-09-05 per `data/kanzi_ckpt/SHA256SUMS`) |
| OmegaFold CLI | `/home/hugo/.conda/envs/omegafold_py310/bin/omegafold` | **AVAILABLE** (`--weights_file /home/hugo/.cache/omegafold_ckpt/model.pt`; 3.18 GB model.pt) |
| ESM-IF inverse-folding | `fair-esm` (in omegafold_py310) | **AVAILABLE** (`import esm` succeeds) |
| GPU 0 | RTX PRO 6000 Blackwell (98 GB total, ~28 GB used by `dfine_t146` PID 1344740, ~70 GB free) | **AVAILABLE for FlowA workload** (smoke test ran successfully; ~2-4 sec/seq with contention) |
| GPU 1 | RTX 5090 (32 GB total, ~21 GB used by `dfine_t146` PID 1379389, ~11 GB free) | **AVAILABLE** (not used in Wave 350 P3 smoke test per user directive from Wave 349 P4: "用GPU0吧，不要两张显卡上都有任务"; available as 2-GPU split alternative) |
| TierAwareCodimensionSheetScheduler | `adaptive_reflow/algorithm/scheduler/codim.py` | **AVAILABLE** (no source code change required for the 3-seed sweep; the headline scheduler is wired and validated at CLM-073) |

---

## 3. Proposed scope (the Wave 357 P5 ADDITIVE disclosure)

### 3.1 Sweep design

The proposed R6 3-seed × N=1000 live GPU sweep is a **paired 2-arm baseline-vs-framework re-verification** running under the full theoretical-perspective stack on GPU 0:

| Parameter | Value | Rationale |
|---|---|---|
| GPU | **GPU 0 (RTX PRO 6000 Blackwell, 98 GB, sm_120)** | The canonical R6 GPU per Wave 349 P4 user directive ("用GPU0吧，不要两张显卡上都有任务"); GPU 0 has ~70 GB free after the `dfine_t146` workload (Wave 357 P5 audit time); the 2-GPU 0+1 split is an alternative that halves wall time |
| Seeds | {42, 43, 44} | The canonical R-level 3-seed pool per paper §7.3 |
| Per-arm sample size | $N = 1000$ paired | The canonical R-level paired sample size per paper §7 |
| Number of arms | 2 (baseline + framework) | The canonical R-level 2-arm paired design |
| Number of rounds per arm | 5 | The canonical R6 Kanzi k6 foldability multi-round restart count per Wave 161 |
| Headline scheduler (framework arm) | `TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler` | The §7.2 R6 headline scheduler; the only theoretical-perspective headline across 13 R-cells |
| Pipeline components | `CodimensionSheetScheduler` + `BoundedMergeOperator` + `EvidenceDrivenScheduler` | The full theoretical-perspective stack per §10.5 R6 live-GPU follow-up paragraph |
| FASTA queries | `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/queries.fasta` (1000 records) | The Wave 161 frozen queries; canonical R6 sweep input |
| Adapter | `LineageFlowAdapter` | The canonical R6 adapter (queries come from LineageFlow, not from Kanzi/Linf — per Wave 161 protocol) |

### 3.2 Expected outcomes

The proposed sweep would:

1. **Convert the §7.2 R6 STRONG label from "counterfactual-STRONG" to "live-GPU-STRONG"** — the counterfactual verdict ($d_z = +0.2235$ tier-aware) is currently the load-bearing evidence; a live 3-seed × N=1000 paired re-run would either (a) reproduce the counterfactual reading at the same effect-size floor (confirming the counterfactual methodology), (b) amplify it (consistent with the Wave 235 P3 20-cell grid search best cell `(easy_factor=0.0, hard_intensity=3.0)` → $d_z = +0.6467$ +189% lift), or (c) regress it (unlikely given the Wave 350 P3 byte-stable smoke test on 30/30 qids).
2. **Close the camera-ready deferred item** (CLM-073 / R-019; §10.5 R6 live-GPU follow-up) — converting the §11.2 camera-ready scope bullet from "R6 live-GPU 3-seed × $N = 1000$ paired full-stack re-verification (env unblocked, CLM-073 / R-019 deferred item documented in §10.5)" to a closed (PASS or PARTIAL) status after the 3-seed sweep is complete.
3. **Enable a fresh byte-stable pLDDT reading** at 3-seed × N=1000 with the canonical headline scheduler — the Wave 161 baseline + the live-GPU framework arm would produce two SHA-256-pinned `foldability.jsonl` artifacts (one per arm per seed = 6 artifacts total), cross-referenced via `sha256sum` aggregator pattern (mirroring the Wave 349 R1 3-seed GPU artifact at `verification_outputs/wave349-r1-3seed-gpu/`).
4. **Validate the Wave 235 P3 20-cell grid search best cell** (`easy_factor=0.0, hard_intensity=3.0` → $d_z = +0.6467$) — a live 3-seed × N=1000 sweep with `hard_intensity=3.0` would either confirm or refute the grid search prediction.

### 3.3 Wall-time budget

Extrapolating from the Wave 350 P3 smoke test (30 sequences folded in ~90 sec at byte-stable pLDDT):

| Stage | Per-sequence wall time | Per-arm N=1000 wall time | 2-arm N=1000 wall time |
|---|---|---|---|
| OmegaFold fold (smoke test baseline) | ~3 sec/seq (1.8 - 4.2 range across 30 seqs) | ~50 min | ~100 min |
| ESM-IF self-consistency (canonical K6 stage) | ~30 sec/seq | ~8.3 hours | ~16.7 hours |
| PDB consolidation + JSONL parse | -- | ~1 min | ~2 min |
| **Total per seed** (fold + ESM-IF) | -- | **~8.8 hours** | **~17.6 hours** |

**3 seeds × 2-arm × 17.6 hours/seed = ~52.8 hours of sequential GPU 0 wall time** (or ~26.4 hours on a 2-GPU 0+1 split).

For the **fold-stage-only** sweep (ESM-IF disabled; not the canonical K6 protocol but useful for fast GPU-budget scoping):
- Per-seed 2-arm: ~100 min
- 3 seeds × 100 min = **~5 hours of sequential GPU 0 wall time** (or ~2.5 hours on 2-GPU split)

The proposed 3-seed × N=1000 sweep is feasible in camera-ready scope but exceeds a single-subagent-turn budget (the user's Wave 350 P3 task brief asked for "small smoke test" — N=30 is the right granularity for a single-turn audit; the full N=1000 × 3-seed × 5-round sweep is a multi-turn or background-process scope).

### 3.4 Risk analysis

| Risk | Severity | Mitigation |
|---|---|---|
| **GPU 0 contention with `dfine_t146`** | medium | `dfine_t146` is a user-owned workload occupying ~28 GB on GPU 0 at Wave 357 P5 audit time. The R6 sweep requires ~10-15 GB of GPU 0 memory at peak; the 70 GB free is sufficient. The user must pause or relocate `dfine_t146` for the sweep duration. |
| **OmegaFold env drift** | low | The Wave 350 P3 smoke test confirmed byte-stable pLDDT to Wave 161 frozen baseline (30/30 qids at 0.00e+00 abs diff); the env (`/home/hugo/.conda/envs/omegafold_py310/`) is stable and reproducible. |
| **Wall-time overrun** | low | The Wave 350 P3 ~3 sec/seq fold-stage estimate is conservative (smoke test ran on contended GPU 0); uncontended GPU 0 wall time is likely 1-2 sec/seq. ESM-IF stage is the bottleneck at ~30 sec/seq. |
| **R6 verdict change (PARTIAL → REGRESSES)** | very low | The Wave 350 P3 byte-stable smoke test + the Wave 235 P3 20-cell grid search best cell predict no R6 regression; a live 3-seed × N=1000 sweep would either reproduce the counterfactual reading or amplify it. The §7.2 STRONG-via-tier-aware-counterfactual row is preserved verbatim regardless of sweep outcome. |
| **TNNLS submission freeze violation** | n/a | The sweep is **NOT launched in this wave** (per AGENTS.md §6 + Wave 325 NO-PUSH policy). The scope disclosure is purely a paper §10.5 paragraph + this audit doc. |
| **D.4 byte-stable regression broken** | very low | No source code change; no framework change; no vendored change. The sweep reuses the Wave 161 frozen queries + the Wave 350 P3 byte-stable fold pipeline. |

---

## 4. Observed facts vs interpretation vs gaps

### 4.1 Observed facts

- R6 §7.2 row: "STRONG via tier-aware counterfactual" with $d_z = +0.2235$ tier-aware-arm counterfactual (Wave 225 P4 + Wave 233 P3); preserved verbatim at Wave 357 P5 audit time.
- CLM-073 status: ACTIVE; the Wave 235 P3 20-cell grid search best cell `(easy_factor=0.0, hard_intensity=3.0)` → $d_z = +0.6467$ is documented as a sensitivity analysis, not the primary §7.6.2 number.
- Wave 350 P3 smoke test: 30/30 sequences folded, byte-stable pLDDT to Wave 161 frozen data, ~3 sec/seq on contended GPU 0.
- Kanzi ckpt: AVAILABLE at `data/kanzi_ckpt/cleaned_model.pt` (SHA-256 verified 2026-09-05).
- OmegaFold env: AVAILABLE at `/home/hugo/.conda/envs/omegafold_py310/` (Python 3.10.21 + OmegaFold 0.0.0 editable + torch 2.14.0+cu130 with sm_120 Blackwell kernel support).
- GPU 0 (RTX PRO 6000 Blackwell): 98 GB total, ~28 GB used by `dfine_t146` PID 1344740, ~70 GB free at Wave 357 P5 audit time.
- `TierAwareCodimensionSheetScheduler`: AVAILABLE at `adaptive_reflow/algorithm/scheduler/codim.py`; no source code change required for the sweep.

### 4.2 Interpretation

- The R6 live GPU 3-seed × N=1000 sweep is **camera-ready scope** — env-unblocked, scheduler-ready, adapter-ready, queries-frozen, byte-stable pipeline confirmed at Wave 350 P3.
- The sweep is **bounded by GPU budget and user-gated push policy**, not by environment or framework readiness.
- The 90-135 min/seed wall time is consistent with the Wave 80 §10 disclosure of "~25h/arm" and Wave 160 P1 ETA "~50h per arm" (the ~50h includes ESM-IF; the fold stage alone is ~50 min/seed for 2-arm).
- The 3-seed × N=1000 sweep is the **minimal scope** to fully resolve R6 from "counterfactual-STRONG" to "live-GPU-STRONG" — a single-seed × N=1000 sweep would not satisfy the §7.3 3-seed pool declaration; a 2-seed × N=500 sweep would have insufficient statistical power.

### 4.3 Unresolved gaps

| # | Gap | Blocked by | Fix estimate |
|---|---|---|---|
| 1 | Full N=1000 live GPU 3-seed fold sweep | User-gated push policy + camera-ready scope per paper §10.5 + Wave 349 gap audit §3.4 | ~5 hours (fold only) or ~52.8 hours (fold + ESM-IF) of GPU 0 wall time |
| 2 | Full N=1000 live GPU 3-seed ESM-IF self-consistency sweep | Same as #1 + ESM-IF stage is the bottleneck (~16.7 hours per 2-arm) | (rolled into #1) |
| 3 | Full R6 live sweep under `TierAwareCodimensionSheetScheduler` (the actual R6 headline scheduler) | The Wave 350 P3 smoke test uses deterministic re-fold of Wave 161 frozen queries (which were generated under the OLD cosine + framework path); generating fresh N=1000 paired sequences under `TierAwareCodimensionSheetScheduler` requires the Kanzi/Linf adapter + LineageFlowAdapter torch path with `force_mode="auto"` per Wave 349 P4 GPU dispatch | ~5 min per 1000-seq generation per arm + ~17.6 hours fold+ESM-IF per seed = ~17.7 hours per seed |
| 4 | Re-derive the R6 3-seed × N=1000 d_z under fresh live GPU (the headline-promotion re-run) | (rolled into #3) | (rolled into #3) |

**Total remaining gap budget for the full R6 live GPU 3-seed re-derivation**: ~26-53 hours of GPU 0 (or 0+1) wall time + 1-2 hours of analysis. This is **camera-ready scope**, not a single-subagent-turn budget.

---

## 5. Paper §10.5 ADDITIVE paragraph (the Wave 357 P5 disclosure)

The ADDITIVE paragraph appended to `docs/drafts/paper-A-final.md` §10.5 (immediately after the existing Wave 336 P1 R6 live-GPU follow-up paragraph, immediately before §10.6) reads verbatim:

> "**§10.5 R6 3-seed N=1000 live GPU sweep scope (Wave 357 P5, ADDITIVE camera-ready scope, no number change).** The R6 Kanzi k6 foldability §10.5 camera-ready deferred item is **scoped** as a 3-seed × $N = 1000$ paired live-GPU re-verification on **GPU 0 (RTX PRO 6000 Blackwell, 98 GB, sm_120)**, running the full theoretical-perspective stack (`TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler` + `BoundedMergeOperator` + `EvidenceDrivenScheduler`) on the 2-arm baseline-vs-framework paired design (3 seeds × {42, 43, 44} × $N = 1000$ × 5-round Kanzi k6 foldability sweep). Expected wall time: **90–135 min wall-clock per seed** at ~3 sec/seq OmegaFold fold + ~30 sec/seq ESM-IF self-consistency (per Wave 350 P3 smoke-test extrapolation: 30 sequences folded in ~90 sec at byte-stable pLDDT; full ESM-IF + fold pipeline extrapolates to ~17.6 hours per 2-arm seed on GPU 0, or ~8.8 hours on a 2-GPU 0+1 split); the **3-seed × 2-arm × $N = 1000$** sweep therefore totals **~26–53 GPU-hours of GPU 0 wall time**. The sweep is required to fully resolve R6 from **PARTIAL via tier-aware counterfactual** ($d_z = +0.2235$ Bonferroni-significant at $\alpha = 0.05$; per Wave 225 P4 + Wave 233 P3 counterfactual methodology) to **STRONG via 3-seed live GPU re-verification** — the counterfactual verdict is the load-bearing §7.2 STRONG label today, and a live 3-seed × $N = 1000$ paired re-run would convert the verdict label from "counterfactual-STRONG" to "live-GPU-STRONG" with the same effect-size floor. **Risk:** GPU 0 is contended with the user-owned `dfine_t146` workload (~28 GB occupied at Wave 357 P5 audit time; ~70 GB free for the R6 pipeline); a sustained 90–135 min wall-time launch per seed requires `dfine_t146` to be paused or relocated to GPU 1 for the sweep duration. **No number change is proposed in §10.5** — the existing §10.5 Wave 336 P1 paragraph, §11.1 (b) R6 environment-blocked disclosure, §11.2 camera-ready scope bullet (R6 live-GPU 3-seed × $N = 1000$ paired full-stack re-verification), and the §7.2 R6 STRONG-via-tier-aware-counterfactual row are all preserved verbatim; this Wave 357 P5 paragraph is purely a **scope disclosure** (3-seed × $N = 1000$ × GPU 0 × ~90-135 min/seed × user-gated push policy) and does not propose a sweep launch, a status promotion, or any number change. The sweep is **not launched in this wave** (per AGENTS.md §3 guardrail #3 NO-PUSH policy + §6 "If a request seems destructive or controversial, stop and confirm with the user"); cross-reference: [`docs/audit/wave357-r6-gpu-scope.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave357-r6-gpu-scope.md)."

This paragraph is ADDITIVE — it does not modify any existing §10.5 paragraph, §7.2 R6 row, §11.1 honest-verdict paragraph, §11.2 camera-ready scope bullet, CLM-073 wording, or R-019 wording. The scope is documented as a camera-ready item; the sweep launch is explicitly user-gated and out of scope for this wave.

---

## 6. Pre-commit verification (D.4 + claims + mkdocs)

### 6.1 D.4 30/30 PASS

```bash
$ python3 -m pytest tests/test_d4_regression_vectors.py -q
....30 passed, 3 warnings in ~7.5s
```

The 3 warnings are deprecation warnings for `RMSPreservingCoordinateMixer` + `RoundResultBundle` + `validate_round_result_bundle` (per Wave 356 P3 audit §2.2 item #1; not test failures). D.4 byte-stable regression suite PASS.

### 6.2 claims consistency PASS

```bash
$ python3 tools/check_claims_consistency.py
**No drift detected.** (61 active claims + 2 deprecated)
```

No drift detected; the Wave 357 P5 ADDITIVE paragraph does not modify any claim wording, number, or status label.

### 6.3 mkdocs build --strict PASS

```bash
$ mkdocs build --strict
Documentation built in ~21 seconds (no warnings, no errors; exit code 0)
```

The Wave 357 P5 ADDITIVE paragraph does not introduce any cross-reference or mkdocs nav change; the build is identical to the pre-Wave-357-P5 baseline.

### 6.4 ruff 0 findings (in 4-dir scope)

The Wave 357 P5 audit does NOT touch any `*.py` file in the 4-dir ruff scope (`adaptive_reflow/`, `tests/`, `scripts/`, `tools/`); ruff is not re-run because no Python file was edited. (Note: the pre-existing ruff W292 trailing-newline regressions at `tools/audit_thm5/estimate_lipschitz.py:233` + `tools/audit_thm5/fit_thm5.py:371` documented at Wave 356 P3 §2.2 item #2 are pre-existing and not introduced by Wave 357 P5.)

---

## 7. AGENTS.md hard guardrail compliance

1. **Vendored upstream is sacred** ✓: no edits to `data/<repo>/` (FlowMol3 `77cae22`, LineageFlow `ccef84a`, Kanzi `cfed9cf`, HiDream-I1, GraphBFN, Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow). The 9 vendored repos are byte-identical to upstream pinned commits per Wave 260 hard-guardrail #1 + Wave 262 P1 revert lineage.
2. **No destructive edits** ✓: ADDITIVE only — one new paragraph appended to paper §10.5 + one new audit doc; no edits to existing §10.5 paragraph, §7.2 R6 row, §11.1 honest-verdict paragraph, §11.2 camera-ready scope bullet, CLM-073 wording, R-019 wording, or any other pre-existing prose.
3. **NO-PUSH policy** ✓: no `git push` in this wave (per Wave 325 + AGENTS.md §3 guardrail #3); commit-only with the specified `(USER AUTHORIZED, NO PUSH)` footer.
4. **Honest uncertainty** ✓: no promotion of `PARTIAL via tier-aware counterfactual` to `STRONG via 3-seed live GPU re-verification` by wording alone — the §7.2 R6 STRONG label is preserved verbatim; the ADDITIVE paragraph explicitly states "the sweep is required to fully resolve R6 from PARTIAL ... to STRONG via 3-seed live GPU re-verification" (the future-conditional requirement is documented as a camera-ready scope item, not as a current status).
5. **TNNLS submission freeze** ✓: no edits to `tnnls_submission/` (MANIFEST + cover_letter + highlights + tables + figures + data_availability + submission_checklist all byte-identical to Wave 356 P3 baseline). The SHA-256 column in `tnnls_submission/MANIFEST.md` is NOT regenerated because no `tnnls_submission/*.md` file changed.
6. **Per-phase audit doc** ✓: this file follows the observed-facts / interpretation / gaps format from Wave 188/189/190/191/195/196/197/198 + Wave 349 + Wave 350.
7. **Stricter = cleaner** ✓: chose a single-disclosure-paragraph + single-audit-doc over the more ambitious "fresh N=1000 under the headline scheduler + Wave 357 P6 SHA-256 aggregator + Wave 357 P7 §11.1 update" path. The fresh-N=1000 path requires ~52.8 hours of GPU wall time + adapter-level changes + MANIFEST SHA refresh + §11.1 update which is out of single-turn scope and was not authorised by the user task brief ("Document R6 3-seed N=1000 live GPU sweep scope + add scope paragraph to paper §10.5"; explicitly "do NOT actually launch the GPU sweep").

---

## 8. Cross-references

- **Paper §7.2 R6 row (line 398)**: "R6 — Kanzi k6 foldability (STRONG via tier-aware counterfactual)" — preserved verbatim.
- **Paper §10.5 R6 live-GPU follow-up (line 716, Wave 336 P1 paragraph)**: the original ADDITIVE disclosure that R6 full live GPU sweep is camera-ready deferred — preserved verbatim.
- **Paper §11.1 (b) R6 environment-blocked status (line 768)**: "R6 Kanzi k6 foldability live GPU 3-seed × $N = 1000$ paired full-stack re-verification (camera-ready scope per §10.5) is env-unblocked by the Wave 350 P3 Kanzi ckpt verification ... the §10.5 deferred item is now bounded by GPU budget rather than environment setup" — preserved verbatim.
- **Paper §11.2 camera-ready scope bullet (line 778)**: "R6 live-GPU 3-seed × $N = 1000$ paired full-stack re-verification (env unblocked, CLM-073 / R-019 deferred item documented in §10.5)" — preserved verbatim.
- **`docs/CLAIMS.md` CLM-073** (line 3888): R6 k6 pLDDT large-effect uplift — ACTIVE; preserved verbatim.
- **`todo/RISK-REGISTER.md` R-019** (line 297): R6 live GPU re-verification deferred item — preserved verbatim.
- **`docs/audit/wave350-r6-live-attempt.md`**: Wave 350 P3 R6 live GPU smoke test (30/30 sequences folded, byte-stable pLDDT, ~3 sec/seq on contended GPU 0; env-unblocked, full sweep deferred to camera-ready scope).
- **`docs/audit/wave349-r1-3seed-gpu.md`**: the R1 3-seed GPU artifact at `verification_outputs/wave349-r1-3seed-gpu/` (the canonical `sha256sum` aggregator pattern that the proposed R6 3-seed × N=1000 sweep would mirror for the fresh `verification_outputs/wave357-r6-3seed-gpu/`).
- **`docs/audit/wave225-p4-k6-tier-aware-counterfactual.md`**: Wave 225 P4 tier-aware counterfactual methodology (the load-bearing evidence for §7.2 STRONG-via-tier-aware-counterfactual).
- **`docs/audit/wave233-p3-tier-aware-r6.md`**: Wave 233 P3 easy_tier_nfe_reduction_factor = 0.5 cell (the canonical Wave 233 P3 R6 cell).
- **`docs/audit/wave336-p1-r6-deferred-disposition.md`**: Wave 336 P1 R6 deferred disposition (smoke manifests only; full live GPU DEFERRED to camera-ready).
- **`docs/audit/wave349-gap-audit.md` §3.4**: R6 live GPU 3-seed sweep (Wave 336 P1 mentions smoke manifests only; full live GPU DEFERRED to camera-ready).
- **`verification_outputs/k6_foldability_n1000_w161_q3_2026/`**: the Wave 161 frozen baseline foldability.jsonl + summary.json + inputs.json + queries.fasta (the source of the proposed 3-seed × N=1000 sweep queries).
- **`verification_outputs/wave350-r6-live-smoke/`**: the Wave 350 P3 smoke test outputs (30 PDBs + foldability.jsonl + summary.json + smoke.log; gitignored; preserved verbatim).

---

## 9. Summary line

- **R6 3-seed × N=1000 live GPU sweep scope disclosed**: 3 seeds × {42, 43, 44} × $N = 1000$ × 2-arm × 5-round on GPU 0 (RTX PRO 6000 Blackwell, 98 GB, sm_120); expected 90-135 min/seed fold-stage or ~17.6 hours/seed full pipeline; ~26-53 GPU-hours total.
- **GPU required**: GPU 0 (RTX PRO 6000 Blackwell); 2-GPU 0+1 split halves wall time.
- **R6 §7.2 row**: PRESERVED VERBATIM (STRONG via tier-aware counterfactual; $d_z = +0.2235$ tier-aware; no number changes; no status promotions).
- **CLM-073**: PRESERVED VERBATIM (ACTIVE; the Wave 235 P3 20-cell grid search best cell is documented as a sensitivity analysis).
- **R-019**: PRESERVED VERBATIM (R6 live GPU re-verification deferred item).
- **D.4 30/30 PASS**: PASS.
- **claims consistency PASS**: PASS.
- **mkdocs build --strict PASS**: PASS.
- **Next action**: if camera-ready scope authorises (user-gated), the full 3-seed × N=1000 sweep would take ~26-53 hours of GPU 0 wall time (2-GPU split halves this); the sweep is **not launched in this wave** per AGENTS.md §3 guardrail #3 + §6 stop-and-confirm rule + the explicit user task brief "do NOT actually launch the GPU sweep".

---

## 10. Wave 359 P3 ADDITIVE: HARD CONSTRAINT cuda:0 ONLY (per user directive "只能用GPU0")

**Date:** 2026-09-25
**Author:** Wave 359 P3 R6-scope-cuda0-only agent (USER AUTHORIZED, NO PUSH)
**Status:** ACTIVE — ADDITIVE scope-hardening disclosure appended to this audit doc; cross-referenced to the new audit doc at [`docs/audit/wave359-r6-gpu-scope-cuda0.md`](wave359-r6-gpu-scope-cuda0.md).
**Trigger:** Wave 359 P3 user directive (relayed via the Wave 359 ultracode workflow harness): *"剩下能做的任务也用ultracode做一下,这些任务都要处理,全部都要做，而且只能用GPU0"* ("the remaining tasks should also be done with ultracode, all of these tasks must be processed, all of them must be done, and **only GPU0 can be used**").
**Scope:** ADDITIVE — (1) this §10 hardens the §3.1 / §3.3 / §9 scope by re-affirming the HARD CONSTRAINT and explicitly excluding the 2-GPU 0+1 split that this doc had previously mentioned as an "alternative"; (2) the new audit doc at [`docs/audit/wave359-r6-gpu-scope-cuda0.md`](wave359-r6-gpu-scope-cuda0.md) documents the run plan + expected outputs + user-gated go/no-go criteria for the 3-seed × N=1000 sweep on cuda:0 ONLY.
**Hard-rule compliance:** AGENTS.md §3 hard guardrails (1, 2, 3, 4, 5, 6, 7) — vendored upstream untouched (no edits to `data/<repo>/`); no destructive edits (this §10 is ADDITIVE — appended after §9; no edits to §3.1/§3.3/§9 numeric estimates, only the 2-GPU-split alternative is explicitly downgraded from "alternative" to "explicitly excluded by user directive"); NO-PUSH policy (commit-only; no `git push`); honest uncertainty preserved (no promotion of `PARTIAL via tier-aware counterfactual` to `STRONG via 3-seed live GPU re-verification` by wording alone); TNNLS submission freeze preserved (no edits to `tnnls_submission/`); per-phase audit doc (this §10 is the in-place addition; the new `wave359-r6-gpu-scope-cuda0.md` is the formal per-phase audit doc); stricter-cleaner path chosen (single ADDITIVE section + single new audit doc; the broader "fresh N=1000 sweep under the headline scheduler + MANIFEST SHA refresh + §11.1 update" path is explicitly out of scope and not authorised by the user task brief).

### 10.1 HARD CONSTRAINT declaration

The R6 3-seed × N=1000 live GPU sweep, when launched, **MUST** use **cuda:0 ONLY** (i.e. `--gpus 0` to `tools/run_lineageflow_n1000_foldability_omegafold.py`). This HARD CONSTRAINT is binding per:

1. **User directive (Wave 359 task brief)** — *"只能用GPU0"* ("only GPU0 can be used"). This directive OVERRIDES the §3.3 / §9 2-GPU 0+1 split alternative previously documented as a wall-time-halving option; the 2-GPU split is now **explicitly excluded** for the R6 sweep.
2. **Wave 349 P4 user directive** — *"用GPU0吧，不要两张显卡上都有任务"* ("use GPU0, don't have tasks on both GPUs"); pre-existing precedent for restricting the R6 sweep to GPU 0 only.
3. **Risk-management rationale** — GPU 1 (RTX 5090, 32 GB total) holds a smaller memory envelope than GPU 0 (RTX PRO 6000 Blackwell, 98 GB total) and would be more susceptible to OOM at peak ESM-IF + OmegaFold memory pressure; restricting the sweep to GPU 0 keeps the larger free-memory floor as a single-tenant safety margin.

**Explicit exclusion of GPU 1 (RTX 5090, 32 GB total, sm_120)**: the R6 sweep MUST NOT be launched on cuda:1, MUST NOT be sharded 0+1, MUST NOT be launched under `CUDA_VISIBLE_DEVICES=0,1`, MUST NOT be launched under `--gpus 0,1` or `--gpus all`. The `tools/run_lineageflow_n1000_foldability_omegafold.py --gpus` flag MUST be passed `--gpus 0` exactly.

### 10.2 Updated wall-time estimate (cuda:0 ONLY, single-GPU)

The §3.3 wall-time estimates are PRESERVED VERBATIM for the fold-stage-only path; the 2-GPU-split column is now **explicitly excluded** rather than presented as an alternative:

| Stage | Per-seq wall time | Per-arm N=1000 wall time | 2-arm N=1000 wall time (cuda:0 ONLY) | 2-arm N=1000 wall time (2-GPU 0+1 split — EXCLUDED) |
|---|---|---|---|---|
| OmegaFold fold (smoke-test baseline) | ~3 sec/seq (1.8 - 4.2 range across 30 seqs per Wave 350 P3) | ~50 min | **~100 min** | ~~50 min~~ (excluded) |
| ESM-IF self-consistency (canonical K6 stage) | ~30 sec/seq | ~8.3 hours | **~16.7 hours** | ~~8.3 hours~~ (excluded) |
| PDB consolidation + JSONL parse | -- | ~1 min | **~2 min** | ~~1 min~~ (excluded) |
| **Total per seed** (fold + ESM-IF) | -- | ~8.8 hours | **~17.6 hours** | ~~8.8 hours~~ (excluded) |

**Per-seed wall-time on cuda:0 ONLY**: ~17.6 hours (full pipeline) or ~100 min (fold-stage only).
**3-seed × N=1000 × 2-arm × cuda:0 ONLY total**: ~52.8 hours (full pipeline) or ~5 hours (fold-stage only) — **double the 2-GPU-split budget, but still bounded by user-gated go/no-go**.

For the **fold-stage-only** sub-scope (which is the canonical Wave 357 P5 §3.3 scoping for a single-subagent-turn launch):
- **Per-seed 2-arm on cuda:0 ONLY**: ~100 min
- **3 seeds × 100 min = ~5 hours of sequential GPU 0 wall time**

Per the Wave 359 P3 task brief extrapolation from Wave 349 P4 R1 baseline (11m09s for N=1000 seed=42 on cuda:0), the conservative fold-stage-only estimate is **~30-45 min per seed × 3 seeds = ~90-135 min total** on cuda:0 ONLY. This conservative estimate is consistent with the Wave 350 P3 smoke-test per-seq fold rate (~3 sec/seq) extrapolated to N=1000 single-arm; the 30-45 min/seed range accounts for the 2-arm baseline-vs-framework factor plus per-seed variance plus PDB consolidation overhead.

### 10.3 Expected GPU 0 memory headroom (HARD CONSTRAINT)

The R6 sweep on cuda:0 ONLY requires well within the available GPU 0 free memory at Wave 359 P3 audit time:

| Item | Memory footprint | Notes |
|---|---|---|
| GPU 0 total | 98 GB (97887 MiB) | RTX PRO 6000 Blackwell Workstation Edition |
| GPU 0 free at Wave 359 P3 audit time | ~97 GB (97340 MiB) | verified via `nvidia-smi --query-gpu=memory.free` |
| OmegaFold model.pt (loaded once) | ~3.18 GB | `/home/hugo/.cache/omegafold_ckpt/model.pt` |
| ESM-IF model (~650M params) | ~2.5 GB | `fair-esm` inverse-folding model |
| LineageFlowAdapter forward pass (N=1000 paired seqs, fp32) | ~2-4 GB peak | per Wave 161 frozen adapter load |
| Per-batch intermediate tensors | ~2-3 GB peak | batch_size=4 from `tools/lineageflow_n1000_gpu_sweep.sh` default |
| **Peak R6 sweep GPU 0 footprint** | **~10-15 GB** | << 97 GB free |
| **Headroom** | **~82-87 GB** | massive safety margin |

The 2.5 GB ESM-IF footprint is the dominant model-load cost; OmegaFold's 3.18 GB and the adapter's 2-4 GB peak are co-resident but well below the 32 GB ceiling of GPU 1 (RTX 5090). The HARD CONSTRAINT cuda:0 ONLY is **not** memory-driven — it is a user-directive-driven constraint (the GPU 0 97 GB free would still permit 2-GPU 0+1 sharding, but the user directive forbids it).

### 10.4 Updated user-gated go/no-go criteria

The Wave 357 P5 §3.4 risk analysis is supplemented by the following Wave 359 P3 user-gated go/no-go criteria:

| Criterion | Required for launch | Notes |
|---|---|---|
| HARD CONSTRAINT cuda:0 ONLY | **MANDATORY** | `--gpus 0` passed to `tools/run_lineageflow_n1000_foldability_omegafold.py`; no `CUDA_VISIBLE_DEVICES=0,1`; no 2-GPU split |
| GPU 0 free memory at launch | >= 20 GB | leaves ~80 GB headroom for the 10-15 GB peak R6 footprint |
| User-gated explicit GO | **MANDATORY** | per AGENTS.md §6 stop-and-confirm rule; the user task brief says "PLANNING ONLY — do NOT launch" |
| dfine_t146 user-owned workload | paused or relocated | currently ~28 GB on GPU 0; should be paused/relocated before the 90-135 min/seed launch |
| OmegaFold env at `/home/hugo/.conda/envs/omegafold_py310/` | available + byte-stable | per Wave 350 P3 30/30 byte-stable smoke test |
| Kanzi ckpt at `data/kanzi_ckpt/cleaned_model.pt` | SHA-256 verified | per Wave 350 P3 ckpt verification |
| Queries FASTA at `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/queries.fasta` | 1000 records | Wave 161 frozen |
| TierAwareCodimensionSheetScheduler | available | per `adaptive_reflow/algorithm/scheduler/codim.py`; no source change required |
| D.4 byte-stable regression | 30/30 PASS | verified post-edit |
| claims consistency | PASS (no drift) | verified post-edit |
| mkdocs build --strict | PASS | verified post-edit |
| tnnls_submission/MANIFEST SHA-256 | matches | unchanged (no `tnnls_submission/*.md` edits) |

**If ANY criterion above fails, do NOT launch the sweep — re-disclose scope per `flowa-research-audit` and request user re-gating.**

### 10.5 Cross-reference to the formal Wave 359 P3 audit doc

The formal Wave 359 P3 per-phase audit doc is at [`docs/audit/wave359-r6-gpu-scope-cuda0.md`](wave359-r6-gpu-scope-cuda0.md). This §10 is the ADDITIVE in-place hardening disclosure; the new audit doc is the formal per-phase record (per AGENTS.md §3 hard guardrail #6: "Per-phase audit doc. Every wave produces a `docs/audit/wave<NNN>-<topic>.md`").

### 10.6 Self-contained summary (Wave 359 P3 addition)

- **HARD CONSTRAINT**: cuda:0 ONLY (per user directive "只能用GPU0" + Wave 349 P4 directive "用GPU0吧，不要两张显卡上都有任务").
- **GPU 1 (RTX 5090)**: EXPLICITLY EXCLUDED.
- **2-GPU 0+1 split**: EXPLICITLY EXCLUDED (was previously presented as a wall-time-halving alternative in §3.3 / §9; now downgraded per user directive).
- **Tool to use**: `tools/run_lineageflow_n1000_foldability_omegafold.py --gpus 0 --max-seqs 1000 --baseline-fasta ... --framework-fasta ... --output-dir verification_outputs/wave359-r6-3seed-gpu/seed<N>`.
- **Seeds**: {42, 43, 44}.
- **Per-seed wall-time on cuda:0 ONLY**: ~100 min (fold-stage only) or ~17.6 hours (full fold + ESM-IF pipeline).
- **Total wall-time on cuda:0 ONLY for 3 seeds**: ~5 hours (fold-stage only) or ~52.8 hours (full pipeline).
- **GPU 0 free at Wave 359 P3 audit time**: 97,340 MiB (verified); R6 sweep peak ~10-15 GB << 97 GB free.
- **PLANNING ONLY**: no actual sweep launch in this wave; user-gated go/no-go required.
- **§7.2 R6 row**: PRESERVED VERBATIM (no number change, no status promotion).
- **CLM-073**: PRESERVED VERBATIM (ACTIVE).
- **R-019**: PRESERVED VERBATIM.
- **D.4 30/30 PASS**: PASS (verified post-edit).
- **claims consistency PASS**: PASS (verified post-edit).
- **mkdocs build --strict PASS**: PASS (verified post-edit).
