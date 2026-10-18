# GAP-43 — Pre-registration: a decisive blend-positive test

**Status:** PRE-REGISTERED, NOT YET RUN.
**Registration date:** 2026-10-18 (UTC).
**Base commit:** `7281a1ee` (todo.json rewrite).
**Author:** GAP-43 agent (USER AUTHORIZED, NO PUSH).
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).
**Registration record:** the authoritative version is the git blob of this file
at the commit that introduces it; the blob hash is recorded in the commit
message and in `todo.json`. Any edit after the run starts is a deviation and
must be appended to §12.

---

## 0. TL;DR

| Item | Pre-registered value |
|---|---|
| Cell | R3, FlowMol3 `fg_dev` (lower is better) |
| Framework arm | faithful all-channel restart-blend (`--real-restart-blend`, memory fraction 0.5, β = 0.5 on coordinate + charge + raw_pair) |
| Pairing | `--shared-prior` (same canonical prior for both arms, same solver seed) |
| Baseline | FlowMol3 `last.ckpt`, NFE = 250 matched; tuned-baseline gate at NFE = 1000 (4×) |
| Seeds | **55, 65, …, 545** (50 fresh seeds, step 10; the 42–44 pilot is excluded from the confirmatory test) |
| N per arm per seed | 1000 molecules (10 batches × 100) |
| Primary test | one-sample two-sided t on the 50 per-seed paired Δ, df = 49 |
| α | 0.05/7 = 0.0071429 (the project-wide family threshold) |
| Effect-size floor | `|d_z| >= 0.5` |
| Power target | 80 % at the floor `d_z = 0.5`; n = 50 is the smallest n that achieves it |
| Decision | POSITIVE / BOUNDED NEGATIVE / INCONCLUSIVE (§5) |
| Cost | ~8.5–9 h serial on cuda:0 (§11) |

---

## 1. Why this experiment

The paper's namesake mechanism — the restart-blend — still has **no clean
positive cell**. The current evidence is:

- **R1** is init-attributed, and its pooled effect fell from `+0.1609` to
  `+0.1178` at NFE = 150 (GAP-42f).
- **R3** is a near-miss: canonical `d_z = -0.401`, `p = 0.559` at n = 3.
- **R5b** dies under a tuned baseline (0/4 wins at baseline NFE = 200).
- **K1**'s canonical headline metric (`rdkit_validity_pct`) is saturated at
  1.0 in both arms, so it cannot discriminate.

A review of the prior pilots found **two design defects** that this
pre-registration corrects:

1. **The GAP-39 blend pilot used the legacy arm-keyed prior**
   (`"shared_prior": false` in
   `verification_outputs/gap39-flowmol3-real-restart-blend/n1000/`). GAP-37
   showed that this design inflates the cross-seed SD of R3 by 3.75×
   (0.0939 → 0.0250) and understates `d_z` by 2.7×. The pilot's blend effect
   (`d_z = -0.359`) is therefore measured under the wrong pairing.
2. **The GAP-39 "K1" endpoint is not the canonical K1 metric.** It is
   `paper_pb_validity_pct`, i.e. `SampleAnalyzer.analyze(...)["pb_valid"]`
   (UFF-based PoseBusters pass rate), not the canonical
   `rdkit_validity_pct` (saturated) and not the xtb-based
   `compute_pb_validity_pct`. It is a legitimate metric, but it cannot be
   called "K1". It is retained here as an **exploratory** endpoint only.

The combination **faithful blend + shared prior** has never been run. It is
the only design that simultaneously (a) uses the paper's actual mechanism,
(b) uses the correct paired design, and (c) tests a non-saturated canonical
metric. That is the decisive test.

**Why not candidate B (R6 hard-tier)?** R6's framework arm is the
codimension-sheet scheduler, not the restart-blend. A win there would
strengthen the paper's breadth but would not answer "where does the blend
win". It remains a fallback for overall breadth, not a GAP-43 primary.

---

## 2. Prior evidence and what it predicts

Paired Δ = framework − baseline. For `fg_dev`, negative is framework-favourable.

| Estimate | Design | n | mean Δ | SD | `d_z` | `p` | Source |
|---|---|---:|---:|---:|---:|---:|---|
| R3 `fg_dev`, x-only proxy, arm-keyed | canonical (GAP-27) | 3 | −0.03769 | 0.09390 | −0.401 | 0.559 | `gap27-r3-power.md` |
| R3 `fg_dev`, x-only proxy, **shared prior** | GAP-37 | 3 | −0.02725 | **0.02502** | **−1.089** | 0.200 | `gap37-statistical-power.md` |
| R3 `fg_dev`, **real blend**, arm-keyed | GAP-39 | 3 | −0.05476 | 0.15262 | −0.359 | 0.598 | `gap39-flowmol3-real-restart-blend.md` |
| `pb_valid`, real blend, arm-keyed | GAP-39 | 3 | +0.1410 | 0.15313 | +0.921 | 0.252 | same |
| **R3 `fg_dev`, real blend, shared prior** | **this experiment** | **50** | — | — | — | — | — |

**What the table predicts, and what it does not.** The shared-prior design
left R3's point estimate almost unchanged (−0.0377 → −0.0272) while cutting
the SD 3.75×. If the real blend's point estimate (−0.0548) survived the same
variance reduction, `d_z` would be ≈ −1.3. That is an **extrapolation from
n = 3**, not an assumption. The pre-registration is powered at the
*acceptance floor* `d_z = 0.5`, not at the extrapolation, so the design does
not depend on it.

---

## 3. Design

### 3.1 Model and protocol

| Item | Value |
|---|---|
| Model | FlowMol3, production checkpoint `data/flowmol3/weights_real/checkpoints/last.ckpt` |
| Checkpoint md5 | `d6cda2d7bc3d190db1ef7c07a2b84c81` |
| Solver | upstream FlowMol3, `num_steps = 250`, `nfe_batch = 100`, 10 batches |
| N per arm per seed | 1000 target molecules |
| Device | `cuda:0` only (project constraint) |
| Python | `.venvs/flowmol3_venv/bin/python` |
| Metrics | `tools.paper_metrics.compute_all_paper_metrics(..., reference="GEOM_DRUGS")` |
| PoseBusters config | `tools/pb_config_with_energy_ratio.yaml`, sha256 `fa4e1a8d5fb10726c95fe5554426798e9bf84f9445fad0a36ff0a448187a598a` |

### 3.2 Arms

- **Baseline:** no restart, no blend. `perturbation_sigma = 0`.
- **Framework:** `--real-restart-blend --restart-memory-fraction 0.5`.
  The adapter's `apply_restart_distribution` blends the canonical prior's
  `(x, a, c, e)` with a fresh draw via `_channel_aware_blend` on
  coordinate + charge + raw_pair, with β = 1 − memory_fraction = 0.5 on each
  channel. The blended bundle is then solved once.
- **Pairing:** `--shared-prior`. Both arms build the **same** canonical prior
  for each `(seed, batch)` (arm-independent `batch_id = seed{S}-batch{B}`)
  and call `solve_ode(..., seed = S + B)` with the same seed. The framework
  arm differs from the baseline **only** by the prior-side blend.

### 3.3 Seeds and sample

- Confirmatory seeds: **55, 65, …, 545** (50 fresh seeds, step 10).
  The driver derives the per-batch solver seed as `S + batch_idx`, so a
  contiguous seed list reuses solver seeds across neighbouring `seed_base`
  values (42/43/44 already overlap). Step 10 makes the blocks
  `[S, S+9]` **disjoint**, removing cross-seed reuse of the solver noise
  stream. Starting at 55 also clears the pilot's blocks (`42–53`).
- Pilot seeds 42–44 are **excluded** from the confirmatory test (they were
  used to select the cell and to set the power calculation). They are
  reported separately as calibration.
- Each seed contributes one paired Δ (unit = seed). N = 1000 is the
  within-seed sample; it is **not** the replication unit.

### 3.4 Tuned-baseline gate

The baseline is allowed to choose its better solver budget per seed:

```
Δ_tuned(S) = fg_dev(framework@250, S)
           − min( fg_dev(baseline@250, S), fg_dev(baseline@1000, S) )
```

Run on seeds **55, 65, …, 145** (10 seeds). This is the GAP-12 "tuned
baseline" protocol (baseline at 4× the matched compute), made stricter by
taking the per-seed minimum. The framework arm stays at NFE = 250.

The gate is **descriptive**, not a significance test: it passes iff
`mean(Δ_tuned) < 0`. A pass means the matched-NFE win is not a
baseline-compute artifact.

---

## 4. Hypotheses

- **H1 (directional):** under the faithful all-channel blend and the shared
  prior, the framework's `fg_dev` is lower than the baseline's:
  `mean(Δ) < 0`.
- **H0:** `mean(Δ) >= 0`.

The test is two-sided; the directional claim is made only if the sign is
framework-favourable.

---

## 5. Primary analysis and decision rule

### 5.1 Test

For the 50 per-seed paired differences `Δ_i`:

```
mean = (1/n) Σ Δ_i
sd   = sqrt( Σ(Δ_i − mean)² / (n − 1) )
se   = sd / sqrt(n)
t    = mean / se,          df = n − 1 = 49
p    = 2 · P(T_49 ≥ |t|)
d_z  = mean / sd
CI95(mean) = mean ± t_{0.975, 49} · se
```

`d_z`'s 95 % CI is a percentile bootstrap over seeds (10,000 resamples,
`numpy.random.default_rng(0)`).

### 5.2 POSITIVE

All four conditions must hold:

1. `mean(Δ) < 0`;
2. `p < 0.05/7 = 0.0071429`;
3. `|d_z| >= 0.5`;
4. the tuned-baseline gate passes (`mean(Δ_tuned) < 0` on seeds
   55, 65, …, 145).

If conditions 1–3 hold but 4 fails, the result is reported as
**"matched-NFE positive, not robust to baseline compute tuning"** and is
**not** a positive claim.

### 5.3 BOUNDED NEGATIVE

If POSITIVE is not met, and the bootstrap 95 % CI for `d_z` has
**lower bound > −0.5**, the result is a **bounded negative at the
pre-registered floor**: the data rule out a framework improvement of
0.5 SD or more on this cell/regime. The paper must then stop claiming a
blend win and reposition the contribution.

### 5.4 INCONCLUSIVE

Otherwise (the `d_z` CI reaches −0.5 but the test is not significant), the
result is **inconclusive**. The only permitted follow-up is a pre-registered
extension on **fresh** seeds (95 onward), with the same α; the 50 seeds are
not re-tested or re-analysed with a different metric.

### 5.5 Robustness diagnostics (reported, not decision rules)

- Sign count (`#Δ_i < 0`), median Δ, 10 % trimmed mean.
- Leave-one-seed-out range of `mean` and `d_z`.
- Per-seed `n_sampled` per arm; flag any seed with a between-arm
  `n_sampled` difference > 2 % (20 molecules).
- `paper_validity_pct` (RDKit) and `ood_ring_rate` per arm.
- The framework@250 metrics for the tuned subset must be **identical** in
  the primary and tuned-baseline runs (determinism check).

### 5.6 Exploratory endpoint

`paper_pb_validity_pct` (`SampleAnalyzer.analyze(...)["pb_valid"]`, UFF-based
PoseBusters pass rate) is reported per seed with the same descriptive
statistics, **unadjusted**, and labelled exploratory. It is **not** the
canonical K1 metric (`rdkit_validity_pct`, saturated at 1.0) and is not part
of the confirmatory claim.

---

## 6. Sample size and power

Paired one-sample test, two-sided α = 0.05/7, 80 % power:

```
n = (z_{1−α/2} + z_{0.80})² / d_z² = (2.6926 + 0.8416)² / d_z² = 12.50 / d_z²
```

| n | smallest detectable `|d_z|` at 80 % power |
|---:|---:|
| 15 | 0.91 |
| 25 | 0.71 |
| 30 | 0.65 |
| 40 | 0.56 |
| **50** | **0.50** |

**n = 50 is chosen because it powers the pre-registered acceptance floor
exactly.** At the pilot-implied `|d_z| ≈ 1.0–1.3`, power is ≈ 1.0. At
`|d_z| = 0.6`, power is ≈ 0.94; at 0.4, ≈ 0.55.

**Honest risk.** The pilot's `d_z` comes from n = 3 and a different pairing.
If the true effect is 0.4, the study is underpowered and will return an
inconclusive or bounded-negative result. That outcome is informative: it
would say the blend effect is below the materiality floor, not that it does
not exist.

No interim efficacy stopping. The primary test is computed only after all
50 seeds complete.

---

## 7. Analysis plan (frozen)

- **Script:** `tools/gap43_blend_positive_analysis.py` (to be committed
  before the run; its blob hash is recorded in the run metadata).
- **Inputs:** `--primary-dir` (50 seeds, matched NFE), `--tuned-dir`
  (10 seeds, baseline NFE = 1000), `--out`.
- **Extraction:** for each seed `S`, read
  `flowmol3_n1000_baseline_wave338_p5_seed{S}.json` and
  `flowmol3_n1000_framework_wave338_p5_seed{S}.json`; use
  `["metrics"]["fg_dev"]`, `["metrics"]["pb_validity_pct"]`,
  `["metrics"]["validity_pct"]`, `["metrics"]["ood_ring_rate"]`,
  `["n_sampled"]`.
- **Outputs:** `summary.json` (all per-seed rows + all aggregate statistics)
  and `summary.md` (the table + verdict).
- **Self-test:** `--self-test` on a synthetic vector with known mean/SD
  checks `mean`, `sd`, `t`, `p`, `d_z` to 1e-9; a CPU pytest
  (`tests/test_gap43_analysis.py`) covers the same.
- **No exclusions.** All 50 pre-registered seeds enter the primary analysis.
  A seed that raises or returns < 900 sampled molecules is **retained and
  flagged**; a sensitivity analysis excludes flagged seeds and must reach
  the same verdict. If > 5 seeds are flagged, the run is declared **invalid**
  (not a negative result) and repeated.

---

## 8. What this establishes, and what it does not

**If POSITIVE.** The faithful all-channel restart-blend reduces `fg_dev`
relative to a baseline that is allowed 4× compute on a pre-registered
subset. This is a pre-registered, power-calibrated, blend-isolating positive
cell on a canonical, non-saturated metric. Combined with R6, K4/K5 and the
reproducibility infrastructure, it is the missing empirical piece for a
Q1-defensible submission.

**If BOUNDED NEGATIVE.** The blend effect is below 0.5 SD on this cell and
regime. The paper must stop claiming a blend win; R1 stays init-attributed
and R3 stays PARTIAL. This is a publishable bounded negative, but it does
not close the Q1 gap.

**It does not establish:** other cells, other checkpoints, other NFE
budgets, other memory fractions, other datasets, or a universal advantage of
the blend. It does not establish the K1 headline metric (saturated) or the
xtb-based PoseBusters number. It is one cell, one regime, one mechanism
setting.

---

## 9. Prerequisites (must be satisfied before the run)

1. **Smoke of the combined path.** `--shared-prior --real-restart-blend` has
   never been run together. Run N = 100, seeds 55 and 65, both arms, and
   verify: no exception, `n_sampled > 0`, non-degenerate `fg_dev`, and
   `shared_prior=true` / `real_restart_blend=true` in the JSON.
2. **Determinism.** Re-run seed 55 at N = 100 and confirm the per-arm
   metrics are identical (excluding `wallclock_s` / `timestamp`).
3. **Analysis script + CPU test** committed; blob hash recorded.
4. **Run metadata recorder** writing `run_metadata.json`: git SHA, git
   status (clean), this document's blob hash, the exact command, the seed
   list, Python/torch/CUDA/flowmol/PoseBusters/RDKit versions, checkpoint
   md5, PoseBusters YAML sha256, GPU name, driver version, start/end UTC.
5. **GPU 0 idle** at launch (`nvidia-smi` check); no co-tenant job.

If (1) or (2) fails, the run is paused and the failure is recorded as a
deviation in §12; the pre-registration is not silently altered.

---

## 10. Commands (frozen)

Primary (50 seeds, matched NFE):

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH="$PWD" \
.venvs/flowmol3_venv/bin/python scripts/wave338_p5_r3_n1000_paired.py \
  --n-total 1000 --nfe 250 --nfe-batch 100 \
  --seeds 55 65 75 85 95 105 115 125 135 145 \
          155 165 175 185 195 205 215 225 235 245 \
          255 265 275 285 295 305 315 325 335 345 \
          355 365 375 385 395 405 415 425 435 445 \
          455 465 475 485 495 505 515 525 535 545 \
  --shared-prior --real-restart-blend --restart-memory-fraction 0.5 \
  --device cuda:0 \
  --output-dir verification_outputs/gap43-blend-positive/primary
```

Tuned-baseline gate (10 seeds, baseline NFE = 1000):

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH="$PWD" \
.venvs/flowmol3_venv/bin/python scripts/wave338_p5_r3_n1000_paired.py \
  --n-total 1000 --nfe 250 --baseline-nfe 1000 --nfe-batch 100 \
  --seeds 55 65 75 85 95 105 115 125 135 145 \
  --shared-prior --real-restart-blend --restart-memory-fraction 0.5 \
  --device cuda:0 \
  --output-dir verification_outputs/gap43-blend-positive/tuned_baseline
```

Analysis:

```bash
python3 tools/gap43_blend_positive_analysis.py \
  --primary-dir verification_outputs/gap43-blend-positive/primary \
  --tuned-dir verification_outputs/gap43-blend-positive/tuned_baseline \
  --out verification_outputs/gap43-blend-positive/summary.json
```

---

## 11. Cost

Measured from GAP-39's N = 1000 runs (same checkpoint, NFE = 250):

| Component | Seeds | Per seed | Total |
|---|---:|---:|---:|
| Primary (baseline@250 + framework@250) | 50 | ~7 min | ~5.8 h |
| Tuned gate (baseline@1000 + framework@250) | 10 | ~17 min | ~2.8 h |
| Smoke + determinism | 2 | ~2 min | ~5 min |
| **Total** | | | **~8.5–9 h** |

The framework@250 arm is duplicated in the tuned run; the duplicate is the
determinism check (§5.5). The run is serial on cuda:0; no concurrency is
used, so there is no scheduling or numerics interaction to validate.

---

## 12. Deviations log

_Empty at registration._ Any change to the design, seeds, metric, α, or
decision rule after the run starts must be appended here with a timestamp,
the reason, and the affected analysis. The original blob hash remains the
authoritative registration.

---

## 13. Guardrail compliance

| Guardrail (AGENTS.md §3) | Status |
|---|---|
| #1 vendored upstream byte-identical | ✅ untouched |
| #2 additive is the rule | ✅ new audit doc; no driver change required for the run |
| #3 NO-PUSH | ✅ commit only |
| #4 honest uncertainty | ✅ n = 50 powered at the floor, not the pilot; failure modes defined |
| #5 TNNLS freeze | ✅ no `tnnls_submission/**` change |
| #6 per-increment audit doc | ✅ this file |
| #7 stricter = cleaner | ✅ shared prior + best-of tuned baseline + fresh seeds |

---

## 14. References

- `docs/audit/gap37-statistical-power.md` — the shared-prior pairing fix and
  the 3.75× SD reduction.
- `docs/audit/gap39-flowmol3-real-restart-blend.md` — the faithful
  all-channel blend and the arm-keyed pilot.
- `docs/audit/gap12-tuned-baseline.md` §4.2 — R3/K1 tuned-baseline protocol.
- `docs/audit/gap27-r3-power.md` — the canonical independent-prior R3
  numbers.
- `docs/audit/gap42-scheduler-budget-conservation.md` §9.4 — the NFE = 150
  R1 result that motivates the blend-positive gap.
- `scripts/wave338_p5_r3_n1000_paired.py` — the driver (`--shared-prior`,
  `--real-restart-blend`, `--baseline-nfe`).
- `tools/paper_metrics.py` — the metric definitions and the PoseBusters
  config path.
