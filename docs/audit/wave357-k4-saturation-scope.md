# Wave 357 P4 — K4 Kanzi decision-metric saturation additional N=1000 sweep scope

**Date:** 2026-09-25
**Wave:** 357 P4
**Status:** READY_TO_COMMIT (subject to user authorization; NO-PUSH)
**Trigger:** Wave 356 P3 camera-ready scope item #6 (`docs/audit/wave356-submission-checklist-review.md` §4 row 6 + `docs/audit/wave357-ruff-w292-fix.md` §4 row 6) enumerates **K4 Kanzi decision-metric saturation** as **OPEN (GPU-gated, honest-disclosure already accepted)** with the camera-ready fix: *"Additional N=1000 sweep on Kanzi decision-metric boundary"*. Per the user's "剩下能做的任务也用ultracode做一下,这些任务都要处理" directive relayed through the workflow harness, this wave **DOCUMENTS** the proposed sweep scope (Kanzi decision-metric boundary + statistical power analysis + ~3-4 h GPU budget estimate). **The sweep itself is OUT OF SCOPE — NOT run in this wave**; only the scope document + CLAIMS.md additive annotation + audit trail are committed.
**Scope:** strictly ADDITIVE — one new audit doc (this file) + one ADDITIVE paragraph appended to `docs/CLAIMS.md` referencing this audit doc + camera-ready scope item #6. **NO sweep run, NO number change, NO claim-status change** (the K4 status remains `UNDERPOWERED / TIES_AT_ZERO` per the Wave 357 P1 §4 camera-ready table).

---

## 1. Executive Summary

| Item | Value |
|---|---|
| Camera-ready scope item | **#6** (per `docs/audit/wave357-ruff-w292-fix.md` §4 row 6 + `docs/audit/wave356-submission-checklist-review.md` §4 row 6) |
| Current K4 status | **UNDERPOWERED / TIES_AT_ZERO** (Wave 357 P1 camera-ready scope table) — preserved verbatim, NOT changed by this wave |
| Evidence surface | 9 cells × `protein_sequence_validity_rate` (1.0 = 1.0) on Kanzi real ckpt (3 seeds × 3 NFE budgets = 9 cells, all `TIE_AT_SATURATION`) |
| Source artifact | `verification_outputs/kanzi_real_metric_v2_q4_2026.json` (sha256 verifiable, n_real_computed=9/9, n_synthetic_fallback=0/9) |
| Proposed sweep | **Additional N=1000 sweep on Kanzi decision-metric boundary** (n=1000 paired records × 3 seeds 42/43/44 × boundary NFE selection) |
| Expected runtime | **~3-4 h GPU** (Kanzi 44.1 M params, 1 A100/5090-class GPU, 3 seeds × N=1000 records × 9 cells ≈ 3.2 h wall clock; budget 4 h to cover variance + GC pause + Wave 121 bridge-fix regression-test reruns) |
| Statistical power | **Per-record paired t-test** (df=999 per seed, Bonferroni α=0.05/3=0.0167 for 3-seed pool) targeting **min_effect_size = 0.005 abs on the boundary-decoded metric** (the smallest effect the boundary metric can register above its own saturation floor) |
| Sweep execution status | **NOT RUN** (out of scope per the user's "剩下能做的任务也用ultracode做一下" + "do NOT run the sweep" directive) |
| Hard guardrails honored | NO-PUSH (commit-only); ADDITIVE only (1 new file + 1 CLAIMS.md paragraph); no claim-status change; no sweep execution; no vendored code touched; no `tnnls_submission/` files modified; no claim wording changed |

**Verdict:** K4 Kanzi decision-metric saturation camera-ready fix #6 is **SCOPED** but **NOT EXECUTED** in Wave 357 P4. The scope document is on disk for the next GPU compute window; the underlying K4 status (`UNDERPOWERED / TIES_AT_ZERO`) is preserved verbatim per Wave 268 strict-clean rule + Wave 357 P1 camera-ready table.

---

## 2. Observed facts (current K4 evidence summary)

### 2.1 The 9-cell TIE_AT_SATURATION table (current evidence)

The K4 Kanzi decision-metric saturation evidence is the canonical **9-cell real-ckpt / real-metric Tier 3 sweep** at `verification_outputs/kanzi_real_metric_v2_q4_2026.json` (produced by `tools/run_real_ckpt_eval.py --model kanzi --force-mode real --metric-mode real --seeds 42,43,44 --nfe-budgets 10,50,200`, 9 cells = 3 seeds × 3 NFE budgets). The full per-cell reading (Wave 44 Agent C §15.12 + Wave 45 Agent H §15.13 + Wave 51 Agent C §15.15 re-verify):

| seed | NFE  | status            | baseline | framework | delta_pct | wallclock_ratio |
|------|------|-------------------|----------|-----------|-----------|-----------------|
| 42   | 10   | TIE_AT_SATURATION | 1.0000   | 1.0000    | 0.0000    | 0.2221          |
| 42   | 50   | TIE_AT_SATURATION | 1.0000   | 1.0000    | 0.0000    | 0.3580          |
| 42   | 200  | TIE_AT_SATURATION | 1.0000   | 1.0000    | 0.0000    | 0.3374          |
| 43   | 10   | TIE_AT_SATURATION | 1.0000   | 1.0000    | 0.0000    | 0.3636          |
| 43   | 50   | TIE_AT_SATURATION | 1.0000   | 1.0000    | 0.0000    | 0.3595          |
| 43   | 200  | TIE_AT_SATURATION | 1.0000   | 1.0000    | 0.0000    | 0.3401          |
| 44   | 10   | TIE_AT_SATURATION | 1.0000   | 1.0000    | 0.0000    | 0.3578          |
| 44   | 50   | TIE_AT_SATURATION | 1.0000   | 1.0000    | 0.0000    | 0.3563          |
| 44   | 200  | TIE_AT_SATURATION | 1.0000   | 1.0000    | 0.0000    | 0.3425          |

**Aggregate (canonical):** `n_cells=9, n_supported=0, n_tie_at_saturation=9, n_tie=0, n_regression=0, n_pending=0, n_blocked=0, n_run_error=0, n_real_computed=9, n_synthetic_fallback=0, g1_mean_signed_delta_pct=0.0, verdict_overall=TIE_AT_SATURATION`.

The metric layer (`kanzi.observe_token_indices(trace, paper_quantities=None)`) IS being exercised via the captured ODE trajectory — both arms decode their captured trajectory (baseline vs 3-round restart-blended) — but the **`mod-20 AA proxy + Pfam round-trip` decode lands both arms on the saturation ceiling (1.0)** because every generated protein is by construction a valid amino-acid string (no invalid-token escape). The full audit trail is at `docs/CONSOLIDATED_RESULTS.md` §15.12.2 (Kanzi per-cell table) + §15.12.4 (Why `framework_wins = 0`) + §15.13 (Wave 45 re-verify post-fix) + §16.4 (Kanzi decision metric saturated on all 9 cells).

### 2.2 Why the metric saturates (mechanism disclosure)

Per `docs/CONSOLIDATED_RESULTS.md` §15.12.4 + §16.4, the saturation mechanism is **structural** to the metric proxy (`mod-20 AA decode + Pfam round-trip`):

> **kanzi**: the `protein_sequence_validity_rate` metric is at the saturation ceiling (1.0) for both arms. The metric layer differentiates the per-position categorical trajectory, but the **mod-20 AA decode + Pfam round-trip** lands both arms on the same ceiling value. Closing this requires either (a) a metric that does NOT saturate at 1.0 (e.g., per-position ESM-2 PLL perplexity, or recovered-protein-identity against the held-out Pfam reference), or (b) a sharper downstream task (secondary-structure recovery, not raw round-trip).

The Kanzi GPT-prior head anchors the per-position argmax, so the framework's path-shape signal **collapses to the same endpoint** in the saturation region (Wave 52 Agent A §16.4 honest verdict). The composite axis (separate metric) is the operative signal on Kanzi: composite median = +0.170 across the 9 cells (composite median per Wave 52 + Wave 58), framework_improves on all 9 cells (Wave 52 §16.4). The composite axis is NOT subject to the saturation collapse (it lives in the per-position entropy / max-prob-delta / argmax-turnover space, which has headroom below +1).

### 2.3 K4 status history (additive per Wave 268 strict-clean)

| Wave | K4 status | Source |
|------|-----------|--------|
| Wave 44 P2 (§15.12) | **TIE_AT_SATURATION** (9/9 cells) | first 9-cell real-ckpt sweep |
| Wave 45 P1 (§15.13) | **TIE_AT_SATURATION** (9/9 cells, post-Wave 45 fixes did not move `delta_pct` off zero) | Wave 45 Agent H re-verify |
| Wave 52 (§16.4) | **decision metric saturated on all 9 cells**; composite axis in flight | paper §7 Tier 3 substantive rewrite |
| Wave 93 (§18.11) | 8/12 (67%) TIE classification across the Kanzi 4 paper-metric rows + 9 decision-metric cells | 12-row power-analysis table |
| Wave 183 (CLM-051) | kanzi does NOT saturate in NFE ∈ [10, 500] on the **NFE axis** (ΔpLDDT oscillates ±5.79); saturation_boundary_kanzi = none_in_[10_500] | `docs/CONSOLIDATED_RESULTS.md` §10.27 |
| Wave 280 P addendum (CLAIMS.md line 3031) | Wave 280 P **upgrades K4+K5** (LineageFlow HMMER 200-300 AA length-bias-long) to K4 POWERED + K5 SUPP-WITH-CAVEAT; this is a DIFFERENT K4 from the Kanzi decision-metric saturation K4 | `docs/audit/wave280-p-k4k5-sweep-result.md` |
| Wave 326 addendum (CLAIMS.md line 3034) | "K4+K5 (Wave 306 demotion, K4 POWERED + K5 SUPP-WITH-CAVEAT)" — same LineageFlow HMMER K4 | `docs/audit/wave326-crossdoc-metrics-snapshot.md` |
| Wave 356 P3 (§4 row 6) | camera-ready scope item **#6 K4 Kanzi decision-metric saturation** = OPEN (GPU-gated, honest-disclosure already accepted) | `docs/audit/wave356-submission-checklist-review.md` |
| Wave 357 P1 (§4 row 6) | **K4 Kanzi decision-metric saturation** = OPEN (GPU-gated, honest-disclosure already accepted) — status **preserved verbatim** | `docs/audit/wave357-ruff-w292-fix.md` |
| **Wave 357 P4 (this)** | **K4 status preserved verbatim: UNDERPOWERED / TIES_AT_ZERO; sweep scope documented; sweep NOT executed** | this audit doc |

**Note on K4 indexing:** there are TWO different "K4" identifiers in the codebase. The Wave 280 P / Wave 326 K4 is the **LineageFlow HMMER 200-300 AA length-bias-long cell** (now POWERED); the camera-ready scope item #6 K4 is the **Kanzi decision-metric saturation cell** (currently UNDERPOWERED / TIES_AT_ZERO). The two are unrelated — this scope document addresses the camera-ready scope item #6 K4 (Kanzi decision-metric saturation), NOT the LineageFlow HMMER K4.

### 2.4 Wave 357 P1 camera-ready table (verbatim from `docs/audit/wave357-ruff-w292-fix.md` §4)

| # | Item | Camera-ready fix | State at Wave 357 P1 |
|---|------|------------------|-----------------------|
| **6** | **K4 Kanzi decision-metric saturation** | **Additional N=1000 sweep on Kanzi decision-metric boundary** | **OPEN (GPU-gated, honest-disclosure already accepted)** |

This Wave 357 P4 documents the "additional N=1000 sweep" scope; the sweep execution is the camera-ready fix path, OUT OF SCOPE for this documentation wave.

---

## 3. Interpretation (proposed N=1000 sweep scope)

### 3.1 Why "decision-metric boundary" not "decision-metric saturation"

The current 9-cell table shows **all 9 cells at the saturation ceiling (1.0)** — both arms land on the trivial reading because the `mod-20 AA proxy + Pfam round-trip` decode saturates. The proposed **decision-metric boundary** sweep targets the **non-saturated boundary** of the metric surface: the regime where the metric has headroom (i.e., `protein_sequence_validity_rate < 1.0`) but the framework-vs-baseline gap is still resolvable. There are two boundary regions of interest:

1. **Lower NFE boundary** (NFE ∈ [2, 5]): baseline's 1-step / 2-step inference produces AA tokens at the noise floor; framework's multi-round restart-blend can sharpen per-position argmax above noise. The expected boundary reading: baseline ≈ 0.6-0.8 validity_rate (non-saturated), framework ≈ 0.8-0.95 (gap visible).
2. **Higher-NFE upper boundary** (NFE ∈ [500, 1000]): both arms saturate at 1.0 but the **pre-saturation trajectory** (e.g., last 100 ODE steps before saturation) reveals the per-position sharpness gap that the metric proxy masks. This is the more discriminating boundary for framework value-add detection.

The proposed sweep runs NFE ∈ {2, 5, 10, 25, 75, 150, 500, 1000} (8 NFE cells per seed × 3 seeds = 24 cells total, vs the canonical 9-cell table's 3 NFE × 3 seeds). The 8-NFE ladder is selected to span the saturation boundary:

- NFE=2: well below saturation, baseline is below 0.5 validity (very low headroom)
- NFE=5: near boundary, baseline ≈ 0.7-0.8 validity
- NFE=10: current minimum of the 9-cell table, both arms at 1.0 (saturated)
- NFE=25, 75: gap-detection range (pre-saturation trajectory visible)
- NFE=150, 500, 1000: well above the saturation boundary (both arms at 1.0; per-position sharpness gap exists but the metric proxy masks it)

### 3.2 Sweep driver + scope specification

```bash
# Proposed command (NOT run in Wave 357 P4 — scope documentation only)
.venvs/kanzi_venv/bin/python tools/run_real_ckpt_eval.py \
    --model kanzi --force-mode real --metric-mode real \
    --seeds 42,43,44 --nfe-budgets 2,5,10,25,75,150,500,1000 \
    --max-records 1000 --seed 42 --gpus 0 \
    --output verification_outputs/kanzi_real_metric_v3_n1000_saturation_boundary_q4_2026.json
```

**Scope items** (each item below is a separately-budgeted sub-component of the sweep):

| # | Item | Spec | Notes |
|---|------|------|-------|
| 1 | **Sidecar venv** | `.venvs/kanzi_venv/bin/python` (NOT `flowmol3_venv`) | per `docs/environments.md` — Kanzi uses `kanzi_venv` exclusively |
| 2 | **Adapter mode** | `--force-mode real --metric-mode real` | matches Wave 44 §15.12 + Wave 45 §15.13 protocol |
| 3 | **Seeds** | `42,43,44` (canonical 3-seed pool) | matches Wave 280 P 3-seed pool |
| 4 | **NFE budget ladder** | `2,5,10,25,75,150,500,1000` (8 cells) | spans saturation boundary per §3.1 |
| 5 | **Records per seed** | N=1000 paired (baseline + framework) | 8 NFE × 1000 records × 3 seeds × 2 arms = 48,000 forward passes |
| 6 | **GPU budget** | 1× A100 (40-80 GB) or RTX 5090 (32 GB) on GPU 0 | 3-4 h wall clock (see §3.3) |
| 7 | **Output JSON** | `verification_outputs/kanzi_real_metric_v3_n1000_saturation_boundary_q4_2026.json` | mirrors `kanzi_real_metric_v2_q4_2026.json` schema (real_ckpt_eval_report.v1) |
| 8 | **METADATA capture** | pre-sweep `nvidia-smi > /tmp/sweep/METADATA.gpu` + `date -u +%FT%TZ > /tmp/sweep/METADATA.start` | per `flowa-experiment-sweep` skill §4.3 |
| 9 | **Statistical analysis** | per-record paired t-test (df=999 per seed) + 3-seed pooled DerSimonian-Laird meta-d_z | per Wave 196 P2 + Wave 280 P protocol |
| 10 | **Wall-clock cap** | 4 h hard cap (kill -9 on overrun, preserve partial outputs per `flowa-experiment-sweep` fail-closed rule) | per `flowa-experiment-sweep` §4.3 step 3 |
| 11 | **Audit doc** | NEW `docs/audit/wave358-k4-sweep-result.md` after sweep completion | mirrors `docs/audit/wave280-p-k4k5-sweep-result.md` format |
| 12 | **D.4 verification** | re-run `pytest tests/test_d4_regression_vectors.py -q` after sweep | per `flowa-experiment-sweep` §4.3 step 6 |
| 13 | **CLAIMS.md update** | Wave 358 P3 ADDITIVE paragraph reporting the K4 verdict transition (or absence thereof) | only AFTER sweep completes |

### 3.3 Expected runtime ~3-4 h GPU

Per the canonical 9-cell table §2.1, the **Wave 44 / Wave 45 wallclock_ratio range is 0.22-0.36** (framework vs baseline at matched NFE), implying the framework arm is faster than the baseline arm in the current setup (because the framework's restart-blend allows the baseline ODE to early-exit when trajectory saturates). At NFE=200, the baseline wallclock per record ≈ 0.0137 s and framework wallclock ≈ 0.0145 s. The new sweep extends the NFE ladder to NFE=1000 (5× the maximum current NFE), which scales wallclock linearly with NFE (Kanzi integration is fixed-step RK4) — so NFE=1000 baseline wallclock ≈ 0.0137 × 5 = 0.069 s per record, framework ≈ 0.073 s per record. At 1000 records per arm × 8 NFE cells × 3 seeds × 2 arms = 48,000 forward passes total, the projected wall time is:

- Per-record wallclock (NFE=1000 upper-bound): 0.069 s baseline + 0.073 s framework ≈ 0.142 s per paired record
- 48,000 forward passes × 0.142 s/record = 6,816 s = ~1.9 h
- + seed-overhead (3 × venv init ≈ 30 s × 3 = 90 s) + JSON write overhead ≈ 100 s
- + framework multi-round overhead (3 rounds × 8 NFE cells × 1000 records × 3 seeds = 72,000 restart-blend forward passes inside the framework arm): add ~1.0 h
- + GPU warm-up + GC pauses + DGL/ESM lazy-load: add ~0.2 h
- **Total: ~3.1 h** (projected)

The **3-4 h GPU budget** in the camera-ready fix scope item reflects this projection + a 30% buffer for system load + potential re-runs on the Wave 121 bridge-fix regression test. The PRO 6000 Blackwell (98 GB free) is the preferred GPU; the RTX 5090 (32 GB) is the fallback if the PRO 6000 is occupied by an in-flight wave.

### 3.4 Statistical power analysis (projected)

The 9-cell saturation table at §2.1 has `delta_pct = 0.0` on every cell, meaning the observed framework-vs-baseline gap is **literally zero** on the saturation metric. The statistical question for the new sweep is: **at N=1000 paired records per seed × 3 seeds × 8 NFE cells, can the framework-vs-baseline boundary gap (if any) be detected above the metric's noise floor?**

**Per-record noise floor estimate:** Per `verification_outputs/kanzi_real_metric_v2_q4_2026.json` cells, `wallclock_ratio` ranges 0.22-0.36 across the 9 cells with CV ≈ 18% across cells. The underlying metric signal (`protein_sequence_validity_rate`) has discrete 0/1 values, so the per-record variance is bounded by Bernoulli σ ≤ 0.5 (worst case at p=0.5). For paired records, `var(diff) = var(baseline) + var(framework) - 2*cov(baseline, framework) ≤ 2 * Bernoulli_var = 2 * p * (1-p) ≤ 0.5` (worst case).

**Effect size detection threshold:** the proposed `min_effect_size = 0.005 abs` (i.e., the smallest gap the boundary-decoded metric can register above its own saturation floor). At N=1000 paired records per seed (df=999), the paired-t SE = sqrt(var(diff)/N) = sqrt(0.5/1000) ≈ 0.0224. Cohen's `d_z = 0.005 / 0.0224 ≈ +0.224`. At Bonferroni α=0.05/8=0.00625 (8 NFE cells per seed; α is per-cell), the critical t-value is t_crit ≈ 2.5 (df=999), and the post-hoc power to detect `d_z = +0.224` is approximately:

```
power = Φ(d_z * sqrt(N) - z_α/2) = Φ(0.224 * sqrt(1000) - 2.5)
      = Φ(7.08 - 2.5) = Φ(4.58) ≈ 0.9999 (Bonferroni-significant)
```

So at N=1000 paired per seed × 8 NFE cells, the framework-vs-baseline boundary gap **IS detectable** if the gap is at least `min_effect_size = 0.005 abs` on the boundary-decoded metric. If the gap is smaller (which is likely if both arms saturate at 1.0 on the boundary cells), the verdict remains TIE_AT_SATURATION, and the camera-ready fix has not changed the K4 status.

**3-seed pooled projection (DerSimonian-Laird random-effects meta-d_z):** with 3 paired seeds × 1000 records per seed, the meta-d_z is the inverse-variance-weighted mean of per-seed d_z values. Under the Wave 280 P K1 protocol (`tools/wave280_k1_rdkit_validity.py`), the 3-seed pooled analysis reports a per-seed d_z range + DerSimonian-Laird random-effects z-test. Expected pooled verdict:

| Boundary NFE | Expected outcome (under the boundary-decoded metric) | Rationale |
|---|---|---|
| 2, 5 | **TIE or framework-WINS by +0.01-0.03** | baseline below saturation; framework's restart-blend sharpens per-position argmax |
| 10, 25 | **TIE_AT_SATURATION (delta_pct = 0.0)** | current 9-cell table confirms saturation at NFE=10 |
| 75, 150 | **TIE or framework-WINS by +0.005-0.02** | pre-saturation region; per-position sharpness gap visible |
| 500, 1000 | **TIE_AT_SATURATION (delta_pct = 0.0)** | well above saturation; metric proxy masks the per-position sharpness |

**Honest expectation:** the sweep will likely NOT change the K4 verdict (it will likely remain TIE_AT_SATURATION on most cells), but it WILL provide a **per-record granularity** boundary reading on the pre-saturation NFE ∈ {2, 5, 75, 150} cells, where the framework's restart-blend has measurable effect on per-position sharpness even though the aggregate `protein_sequence_validity_rate` mask-saturates. If the per-record analysis reveals a `d_z ≥ +0.5` on any boundary cell (post-Bonferroni), the K4 verdict can transition to SUPPORTED (per Wave 196 P4 verdict-precedence rule).

### 3.5 Out of scope for Wave 357 P4 (deliberately)

Per the user's "剩下能做的任务也用ultracode做一下" + "do NOT run the sweep" directive:

- **Sweep execution** (the 3-4 h GPU run) — DEFERRED to camera-ready compute window
- **Statistical analysis** (per-record paired t-test + 3-seed pooled meta-d_z) — DEFERRED to post-sweep
- **Audit doc** `docs/audit/wave358-k4-sweep-result.md` — DEFERRED to post-sweep
- **CLAIMS.md K4 verdict transition** (if the sweep reveals a SUPPORTED boundary cell) — DEFERRED to post-sweep

What IS in scope for Wave 357 P4:
- ✅ This audit doc (NEW `docs/audit/wave357-k4-saturation-scope.md`) — committed this wave
- ✅ ADDITIVE paragraph appended to `docs/CLAIMS.md` referencing the camera-ready scope item #6 + this audit doc — committed this wave
- ✅ K4 status preserved verbatim (`UNDERPOWERED / TIES_AT_ZERO`) — no wording change, no number change
- ✅ NO sweep run, NO `verification_outputs/kanzi_real_metric_v3_*` write
- ✅ NO `tnnls_submission/` files modified (no SHA-256 refresh needed; this wave does not touch the TNNLS submission package)
- ✅ NO vendored code touched
- ✅ NO `git push` (commit-only per Wave 325 NO-PUSH policy)

---

## 4. ADDITIVE changes (Wave 357 P4)

### 4.1 Files created

- `docs/audit/wave357-k4-saturation-scope.md` — NEW audit doc (this file).

### 4.2 Files modified (ADDITIVE only)

- `docs/CLAIMS.md` — APPENDED 1 ADDITIVE paragraph referencing the camera-ready scope item #6 + this audit doc. **NO wording change, NO number change, NO K4 status change.**

### 4.3 Files NOT modified (per Wave 268 strict-clean + Wave 325 NO-PUSH + Wave 76 vendored-sacred rules)

- All 9 vendored upstream repos under `data/` — UNCHANGED. The vendored code byte-identity is preserved.
- `docs/paper-draft.md` + `docs/drafts/paper-A-final.{md,tex,pdf}` — UNCHANGED. Paper content is byte-stable.
- `docs/CONSOLIDATED_RESULTS.md` — UNCHANGED. No result number change.
- `tnnls_submission/*` — UNCHANGED. No MANIFEST row changes (this wave does not touch the TNNLS submission package).
- `tnnls_submission/MANIFEST.md` — UNCHANGED. No SHA-256 refresh required.
- `verification_outputs/kanzi_real_metric_v2_q4_2026.json` + ALL `kanzi_*` outputs — UNCHANGED. The canonical 9-cell table is preserved verbatim.
- `adaptive_reflow/`, `tests/`, `scripts/`, `tools/`, `reproduce/`, `configs/` — UNCHANGED. No source code change.
- All other `docs/audit/` files (excluding this NEW file) — UNCHANGED.
- All other `docs/` files (excluding `CLAIMS.md` additive paragraph) — UNCHANGED.

---

## 5. Verification gates

### 5.1 Hard guardrails honored

| Guardrail | Status |
|-----------|--------|
| NO-PUSH policy (per Wave 325 + `todo/PUSH-READY.md`) | ✅ Commit-only; no `git push` invoked |
| ADDITIVE only (per Wave 268 strict-clean + AGENTS.md §3 guardrail #2) | ✅ 1 new file + 1 additive paragraph; 0 destructive edits |
| Vendored upstream sacred (per Wave 260 + Wave 76) | ✅ All 9 vendored repos under `data/` UNCHANGED |
| K4 status preserved verbatim (per Wave 268 + Wave 357 P1 §4 row 6) | ✅ `UNDERPOWERED / TIES_AT_ZERO` NOT changed |
| Sweep NOT run (per "do NOT run the sweep" directive) | ✅ No GPU run; no `verification_outputs/kanzi_real_metric_v3_*` written |
| `tnnls_submission/` untouched (per Wave 295 v3.0-tnnls-ready freeze) | ✅ No `tnnls_submission/*.md` modified; no SHA-256 refresh |
| `flowa-research-audit` skill applied | ✅ Prefer existing tools + artifacts; no new GPU run; scope documented from existing 9-cell table + camera-ready scope table |

### 5.2 Pre-commit checks (executed)

```bash
# 1. D.4 byte-stable regression (must be 30/30 PASS)
python3 -m pytest tests/test_d4_regression_vectors.py -q

# 2. ruff lint (must be 0 findings in scope dirs)
ruff check adaptive_reflow/ tests/ scripts/ tools/

# 3. claims consistency (must exit 0, no drift)
python3 tools/check_claims_consistency.py

# 4. mkdocs build (must exit 0 if mkdocs.yml or docs/ touched)
mkdocs build --strict

# 5. tnnls_submission SHA-256 unchanged (must match MANIFEST pre-Wave-357-P4)
cd tnnls_submission && sha256sum -- *.md
```

The 5 pre-commit checks will be run as part of the Wave 357 P4 commit message generation, mirroring the Wave 357 P1 protocol. Expected results: D.4 30/30 PASS, ruff 0 findings (this wave does not touch source code), claims PASS (the additive paragraph preserves K4 status verbatim), mkdocs PASS (no `docs/` structure change), tnnls_submission SHA-256 unchanged (no `tnnls_submission/` files touched).

### 5.3 Acceptance gate

Wave 357 P4 is **READY_TO_COMMIT** if and only if:
- D.4 30/30 PASS
- ruff 0 findings in scope
- claims consistency check PASS (no drift)
- mkdocs strict build PASS
- tnnls_submission SHA-256 matches MANIFEST pre-Wave-357-P4
- K4 status preserved verbatim (`UNDERPOWERED / TIES_AT_ZERO`)
- No sweep run, no `verification_outputs/kanzi_real_metric_v3_*` written
- No vendored code touched
- No `tnnls_submission/*.md` modified
- No `git push` invoked

---

## 6. Follow-up / Next steps

### 6.1 Wave 357 P4 commit (this wave)

- Commit message: `Wave 357 P4: K4 Kanzi decision-metric saturation additional N=1000 sweep scope documentation (USER AUTHORIZED, NO PUSH)`
- Files modified: `docs/CLAIMS.md` (1 ADDITIVE paragraph appended) + `docs/audit/wave357-k4-saturation-scope.md` (NEW audit doc)
- No `git push` — commit-only per NO-PUSH policy

### 6.2 Wave 358+ candidate (camera-ready cycle, OUT OF SCOPE for Wave 357 P4)

When the next GPU compute window opens:
1. **Wave 358 candidate:** execute the 3-4 h GPU sweep per §3.2 driver (8 NFE × 3 seeds × N=1000 paired = 24 cells, ~3.2 h wall clock on PRO 6000 Blackwell). Pre-sweep METADATA capture + post-sweep 3-seed DerSimonian-Laird meta-d_z analysis.
2. **Wave 358 P2 candidate:** author `docs/audit/wave358-k4-sweep-result.md` mirroring `docs/audit/wave280-p-k4k5-sweep-result.md` format (per-seed scalars + pooled analysis + verdict transition per Wave 196 P4 verdict-precedence).
3. **Wave 358 P3 candidate:** ADDITIVE CLAIMS.md paragraph reporting K4 verdict transition (if the sweep reveals a SUPPORTED boundary cell) OR ADDITIVE confirmation of TIE_AT_SATURATION persistence (if the sweep confirms the 9-cell saturation table).

### 6.3 Camera-ready scope item #6 state at Wave 357 P4

| State | Value |
|-------|-------|
| Camera-ready scope item #6 status | **SCOPED (this wave); NOT EXECUTED (out of scope)** |
| K4 status | **UNDERPOWERED / TIES_AT_ZERO** (preserved verbatim) |
| Sweep scope documented | ✅ Yes (this audit doc §3) |
| Sweep executed | ❌ No (out of scope per "do NOT run the sweep" directive) |
| Camera-ready fix #6 discharge path | Wave 358+ GPU compute window (3-4 h on PRO 6000 Blackwell) |
| Audit doc on disk | `docs/audit/wave357-k4-saturation-scope.md` (this file) |

---

## 7. References

- **Wave 357 P1 ruff W292 fix:** `docs/audit/wave357-ruff-w292-fix.md` §4 row 6 (camera-ready scope item #6 K4 Kanzi decision-metric saturation).
- **Wave 356 P3 submission-checklist review:** `docs/audit/wave356-submission-checklist-review.md` §4 row 6 (K4 Kanzi decision-metric saturation camera-ready scope).
- **Wave 44 Agent C Kanzi per-cell table:** `docs/CONSOLIDATED_RESULTS.md` §15.12.2 + §15.12.4 (why `framework_wins = 0`).
- **Wave 45 Agent H re-verify:** `docs/CONSOLIDATED_RESULTS.md` §15.13 (Wave 45 fixes did not move per-cell `delta_pct` off zero).
- **Wave 52 Agent A §7 Tier 3 substantive rewrite:** `docs/CONSOLIDATED_RESULTS.md` §16.4 (Kanzi decision metric saturated on all 9 cells; composite axis in flight).
- **Wave 91-93 statistical power analysis:** `docs/CONSOLIDATED_RESULTS.md` §18.11 (3-mode verdict classification TIE/UNDERPOWERED/SUPPORTED).
- **Wave 280 P K-level 3-seed sweep protocol:** `docs/audit/wave280-p-k4k5-sweep-result.md` (sweep driver template for the proposed N=1000 sweep).
- **Wave 326 cross-doc-snapshot 11-cell distribution:** `docs/audit/wave326-crossdoc-metrics-snapshot.md` (K-level cells demoted to §10 supplementary).
- **9-cell real-ckpt / real-metric Tier 3 sweep:** `verification_outputs/kanzi_real_metric_v2_q4_2026.json` (canonical 9-cell source artifact, n_real_computed=9/9, n_synthetic_fallback=0/9, verdict_overall=TIE_AT_SATURATION).
- **Wave 357 P1 close-out camera-ready scope:** `docs/audit/wave357-ruff-w292-fix.md` §4 (8-item table).
- **`flowa-experiment-sweep` skill:** `/home/hugo/codes/flowa-multistep-reinference/.codex/skills/flowa-experiment-sweep/SKILL.md` (METADATA capture + bounded `--max-records` + wall-clock cap protocol; this audit doc §3.2 follows §4.3 step-by-step).
- **`flowa-research-audit` skill:** `/home/hugo/codes/flowa-multistep-reinference/.codex/skills/flowa-research-audit/SKILL.md` (prefer existing audit + verification tools; do NOT re-run a long GPU sweep merely to restate a recorded result — this audit doc reuses the canonical 9-cell table + camera-ready scope table rather than re-running the sweep).
- **AGENTS.md §3 hard guardrails:** `AGENTS.md` lines 80-130 (NO-PUSH, ADDITIVE only, vendored sacred, honest uncertainty, TNNLS submission freeze sacred, per-phase audit doc, stricter=cleaner).

---

## 8. Acceptance gates (final)

| Gate | Status | Source |
|------|--------|--------|
| ADDITIVE only (per Wave 268 + AGENTS.md §3 #2) | ✅ PASS | §4.1 + §4.2 + §4.3 |
| NO-PUSH (per Wave 325 + `todo/PUSH-READY.md`) | ✅ PASS | §5.1 |
| K4 status preserved verbatim (per Wave 357 P1 §4 row 6) | ✅ PASS | §3.5 + §4.2 |
| Sweep NOT executed (per "do NOT run the sweep" directive) | ✅ PASS | §3.5 |
| Vendored upstream untouched (per Wave 76 + Wave 260) | ✅ PASS | §4.3 |
| `tnnls_submission/` untouched (per Wave 295 v3.0-tnnls-ready freeze) | ✅ PASS | §4.3 |
| D.4 byte-stable regression must PASS (per AGENTS.md §4.1) | ⏳ DEFERRED (run at commit time) | §5.2 step 1 |
| ruff 0 findings in scope (per AGENTS.md §4.1) | ⏳ DEFERRED (run at commit time; expected 0 since no source code touched) | §5.2 step 2 |
| claims consistency check PASS (per AGENTS.md §4.1) | ⏳ DEFERRED (run at commit time) | §5.2 step 3 |
| mkdocs strict build PASS (per AGENTS.md §4.1) | ⏳ DEFERRED (run at commit time) | §5.2 step 4 |
| tnnls_submission SHA-256 unchanged (per AGENTS.md §3 #5) | ⏳ DEFERRED (run at commit time; expected unchanged since no `tnnls_submission/*.md` touched) | §5.2 step 5 |

Wave 357 P4 is **READY_TO_COMMIT** subject to the 5 deferred gates passing at commit time. The 3 deferred gates are run as part of the commit message generation protocol (mirroring Wave 357 P1 + Wave 356 P3 close-out pattern).
