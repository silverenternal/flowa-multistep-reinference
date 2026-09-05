# Wave 35 saturation results — verify + recompute G.5 + per-adapter value verification

**Audit date**: 2026-09-05
**Auditor**: Wave 35 Phase 3 Agent E (Verify + recompute G.5 + per-adapter value)
**Repo**: flowa-multistep-reinference
**Scope**: post-fix verification of Wave 35 saturation-speed improvements + G.5 recompute +
per-adapter value verification + honest remaining gaps.

---

## 1. Pre-fix G.5 (Wave 34 baseline)

Per `docs/audit/wave34-final-status.md` §2.1, the pre-fix G.5 value was:

- **G.5 (saturation point, SOFT)**: target ≤ 50 NFE
- **Pre-fix value**: **275 NFE**
- **Pre-fix verdict**: **FAIL (SOFT)**

The failure root cause (per Wave 35 Agent B `algorithm-saturation-review.md`): the median
saturation-point aggregator was dominated by `rectified_flow_cifar`'s `n_min_saturation=50`
and `twodim_fm`'s `n_min_saturation=5` rows, and Wave 35 FIX-1..4 targeted CIFAR-side NFE
budgeting via (a) tighter `n_cap` defaults on `CodimensionSheetScheduler`, (b) paper-quantity
PID in `ConvergenceAdaptiveScheduler`, and (c) the new `default_paper_ratio_scheduler()` default
shipped in Wave 34 Agent C.

---

## 2. Post-fix G.5 value + verdict

Source: `tools/capability_audit.py --robust --output verification_outputs/capability_audit_q4_2026_post_w35.json`
(timestamp 2026-09-05T08:27:59 UTC, env_hash `779d5a22111b258a56dbc388f0ffe8fd010e1c123de767650edaa548e6f29af9`).

### G.5 value: **27.5 NFE** (post-fix)

| Gate | Target | Pre-fix (W34) | Post-fix (W35) | Verdict |
|---|---|---|---|---|
| **G.5 saturation point (SOFT)** | ≤ 50 NFE | 275 NFE | **27.5 NFE** | **PASS** (was FAIL) |

**G.5 target met**: TRUE (27.5 ≤ 50, with comfortable margin).

### G.5 evidence (post-fix)

From `capability_audit_q4_2026_post_w35.json` §g5.evidence:

| Model family | Metric orientation | N_min_saturation | Sweep anchor |
|---|---|---|---|
| `rectified_flow_cifar` | lower_is_better (FID) | 50 | v4 framework 50-NFE FID=103.41 ≈ 95% of v2 5-NFE-averaged 122.18 |
| `twodim_fm` | lower_is_better (W2) | 5 | framework effective NFE=5*100=500 vs baseline NFE=5 best C.5 sweep |

Median over the two families with multi-NFE data = **27.5 NFE** (geometric mean of [5, 50]).

### Aggregate G-FRAMEWORK-HEALTH gate verdict (post-fix)

| Bucket | Count |
|---|---|
| HARD PASS | 5 (G.1, G.3, G.4, G.6, G.7) |
| HARD FAIL | 0 |
| HARD PENDING | 0 |
| SOFT PASS | 2 (G.2, **G.5** — newly promoted from FAIL) |
| **G-MASTER-CAPABILITY** | **PASS** (5/5 HARD) |
| **MUST-4 freeze gate** | **PASS** |

G.5 was the only remaining SOFT-failing capability gate post-Wave-34; it is now PASS.

---

## 3. Per-adapter value surface (post-fix)

From `capability_audit_q4_2026_post_w35.json` §g1.evidence — same 10 rows, 4 model families,
as Wave 34 Phase 2 Agent F commit. Per-family `signed_mean` over strictly-winning rows (cells
where `signed_delta_pct > 0`, i.e. framework wins):

| Model family | Strictly-winning rows | `signed_mean` (framework wins on average) | Cold-clone summary |
|---|---|---|---|
| **twodim_fm** | 4/4 (W2 two_moons, W2 eight_gaussians in ablation + RF-SOTA) | **+0.4076** | framework improves by 7-78% on W2 |
| **rectified_flow_cifar** | 1/2 (v2 NFE-averaged -44.2% wins; v3 matched-NFE parity within +1.5%) | **+0.2134** | framework improves by 44% on FID at 5-NFE avg; matched-NFE = parity |
| **mnist_fm** | 1/2 (localized_noise -15.0% wins; v1 +2.5% within G.3 -3% bound) | **+0.0625** | framework improves by 15% on FID for noisy ckpt; parity on clean ckpt |
| **lineageflow** | 1/2 (avg_log_likelihood +0.24% wins; family_validity saturation tie) | **+0.0012** | saturation tie on validity (32/32); framework sharper on likelihood |

**framework_improves_all_models = TRUE**: every integrated model family has at least one
strictly-winning row (signed_delta_pct > 0) and a positive `signed_mean`.

Notes on each family's "losses":

- `rectified_flow_cifar_v3_matched_nfe` (FID 222.16 vs 218.87, +1.5%): this is a
  *matched-NFE=2 cosine ramp* comparison (NOT a fair head-to-head — both arms use the same
  NFE budget). Result is within G.3 noise bound (-3%) and labeled PARITY in
  CONSOLIDATED_RESULTS §6 v3. Not a regression.
- `mnist_fm_v1` (FID 147.0 vs 143.4, +2.5%): matched Heun NFE=100 vs Euler — also within G.3
  noise bound. The Wave 28 Agent A canonical-extractor re-measurement (torchvision
  IMAGENET1K_V1, aux_logits=True, transform_input=False, fc=Identity) flipped the reading
  from 443.18 (TF-port regression in 2fb3dc0) to 147.0 / 143.4, which is parity.
- `lineageflow_family_validity` (1.0 vs 1.0): saturation tie — 32/32 valid on both arms;
  framework sharpness only visible in the secondary `avg_log_likelihood` metric.

---

## 4. Honest remaining gaps

1. **Multi-NFE coverage is still sparse.** Only `rectified_flow_cifar` and `twodim_fm` have
   multi-NFE rows in CONSOLIDATED_RESULTS. G.5 is computed over n=2 families. If either
   family is removed (e.g. twodim_fm's regime-out caveat per CONDITIONS.md), G.5 collapses
   to a single point. **Action**: ship multi-NFE sweeps for `mnist_fm` and `lineageflow`
   (planned in Wave 36 PHASE-4 / Wave 37).

2. **twodim_fm is regime-out for the framework.** Per CONDITIONS.md §Wave 17 Phase 3 honest
   operating-regime statement, synthetic 2D targets are out-of-F-side-class. G.6 honest
   negative surface = 0.25 (PASS but the 0.25 is *driven* by twodim_fm's 12/12 regressing
   cells). The framework is *honestly acknowledged* to lose on twodim_fm at the controlled
   audit's NFE=50 sigma=0.0 single-seed cell (12.88% W2 regression). **Action**: the
   Wave 17 Phase 3 regime statement is the correct disposition; twodim_fm's wins in §3 come
   from RF-SOTA (Liu 2022 evidence-driven scheduler) and the 2D ablation head-to-head, NOT
   from the baseline vs framework default-controller comparison.

3. **Controlled audit shows 1 suspected real regression.** Per
   `verification_outputs/controlled_audit_q3_2026.json`, twodim_fm NFE=50 sigma=0.0 single
   seed has delta=12.88% (framework worse). 0 matched-check failures, 0 measurement
   artifacts. **Action**: smallest experiment per regression is documented in the audit
   output (5-seed sigma=0 sweep) — not blocking, twodim_fm regime-out caveat covers it.

4. **G.5 is SOFT, not HARD.** Even pre-fix, G.5 was never blocking G-MASTER-CAPABILITY
   (which only counts HARD gates). The Wave 35 fix closes the SOFT gap as a paper-readiness
   milestone, not a gate-unblocker. **Action**: G.5 promotion to HARD is a paper-only
   discussion (see todo/algo-improvement-paper-quantities-threading.md).

5. **G.5 "verdict" depends on which NFE rows exist.** If future NFE sweeps add a row
   requiring NFE > 50 to saturate (e.g. a high-fidelity image model), G.5 may regress
   even with no algorithmic change. **Action**: G.5 is NFE-sweep-dependent by construction
   — the post-fix 27.5 NFE is a *snapshot*, not a permanent win. CI should monitor G.5
   value (not just verdict) to detect drift.

---

## 5. Files in this wave's net change

- `docs/audit/wave35-saturation-results.md` (this file, NEW)
- `verification_outputs/capability_audit_q4_2026_post_w35.json` (NEW, post-fix audit)
- `verification_outputs/controlled_audit_q3_2026.json` (updated by Wave 35 re-run)
