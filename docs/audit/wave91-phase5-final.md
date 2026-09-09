# Wave 91 Agent E — Phase 5: Final synthesis + paper §7.3 update + push-ready

**Author:** Wave 91 Agent E
**Date:** 2026-09-09
**Scope:** Ship the Wave 91 W2 result (Kanzi latent→coord bridge + framework paper-metric at N=1000). Update paper §7.3 additively, author this final synthesis doc, update push-ready-summary.md additively, run D.4/G-MASTER/mkdocs verification, single commit (NO push).

---

## 0. TL;DR

Wave 91 Phase 5 closes the **Kanzi latent→coord bridge** item from the Wave 91 master plan (`todo/wave91-master-plan.md` W2) with the following result:

- **Bridge authored:** `tools/kanzi_latent_to_coord.py` (~150 LOC, 4 unit tests, all PASS) — converts the Kanzi adapter's `(64, 64)` synthetic latent endpoint into `(L, 256)` continuous-latent coords that can enter the upstream `kanzi.DAE.encode + decode + kabsch_rmsd` pipeline.
- **Framework paper-metric at N=1000 (Wave 91 Phase 4):** verdict **`NOT_MEASURABLE_N1000`** — the framework arm's Kabsch RMSD cannot be measured at N=1000 because the Phase 3 wire (bridge → `tools/run_real_ckpt_eval.py:_run_cell`) is NOT committed. The n=2 proxy shows `Δ = +0.769 Å` (+85.3%) vs the Wave 88 N=1000 baseline (0.902 Å → 1.671 Å); n=2 is not a statistical test.
- **5 codebook metrics:** `TIED_BY_DESIGN` — the framework restart-blend acts on the flow trajectory, not on the post-reconstruction FSQ round-trip; DAE.encode re-encodes reconstructed coords deterministically for a given input.
- **Internal composite axis (KanziGlue, Wave 52 byte-stable):** **`SUPPORTED`** — composite +0.1895 on the [-1, +1] scale, identical to Wave 52/Wave 58 byte-stable reading.
- **Statistical power at N=1000:** with σ ≈ 0.14 Å (Wave 88 baseline std), N=1000 per arm gives ~1.00 power to detect a 0.1 Å RMSD shift (Welch one-sided, α=0.05) — if Phase 3 lands, the framework-vs-baseline paper-metric verdict will be statistically airtight.
- **D.4 byte-stable regression:** **72/72 PASS in 42.70s** (matches Wave 86/87/88 baseline).
- **G-MASTER capability gate:** **7/7 PASS** (hard_pass=5, soft_pass=2).
- **mkdocs build --strict:** **EXIT=0 in 13.47s**.
- **Commit:** Wave 91 Phase 5 (NO push per Wave 68-89 closure pattern).

**Honest verdict:** Wave 91 Phase 2 + Phase 5 are real progress (bridge + 4 tests + paper update + verification), but the framework arm's paper-metric verdict at N=1000 stays at `NOT_MEASURABLE_N1000` — the same Wave 88 status — because Phase 3 (bridge wire into `_run_cell`) is not yet committed. The Wave 91 W2 result is **infra-ready, not measurement-ready**.

---

## 1. Per-metric per-arm N=1000 numbers (Wave 91 Phase 4 + Wave 88 baseline cross-reference)

| # | Metric | Source | Baseline (N=1000) | Framework (N=1000) | Δ | Δ (%) | p-value | Verdict |
|---|---|---|---:|---:|---:|---:|---:|:---|
| 1 | `reconstruction_kabsch_rmsd_A` (paper #1) | Wave 88 N=1000 baseline + Wave 79 n=2 framework proxy | **0.902 Å** (std 0.137, n=1000) | **1.671 Å** (range [1.49, 1.85], n=2) | **+0.769** | **+85.3%** | not testable (n=2 → Welch t-test returns NaN; Mann-Whitney U ∈ {0,1,2} degenerate) | **`NOT_MEASURABLE_N1000`** — n=2 is below Wave 76 R1 budget of 1000 |
| 2 | `codebook_entropy_bits` (paper #2, FSQ entropy) | Wave 88 N=1000 sweep | **8.558 bits** (out of log2(V)=log2(1000)≈9.97) | n/a (TIED_BY_DESIGN) | n/a | n/a | n/a | **`TIED_BY_DESIGN`** — framework restart-blend acts on flow trajectory, not on post-reconstruction FSQ round-trip |
| 3 | `codebook_perplexity` (paper #3, =2^H) | Wave 88 N=1000 sweep | **376.87** (=2^8.558) | n/a | n/a | n/a | n/a | **`TIED_BY_DESIGN`** |
| 4 | `codebook_js_distance` (paper #4, sqrt(JS) bits^0.5) | Wave 88 N=1000 sweep on records 0/1 of pdb 1s7mB01 | **0.560** | n/a | n/a | n/a | n/a | **`TIED_BY_DESIGN`** |
| 5 | `codebook_utilization` (paper #5, |unique|/V) | Wave 88 N=1000 sweep | **0.614** (≈ 61.4% of 1000 cells used) | n/a | n/a | n/a | n/a | **`TIED_BY_DESIGN`** |
| 6 | `codebook_hamming_rotation_invariance` (paper #6) | Wave 83 Agent B N=16 smoke + Wave 88 N=1000 skip | **0.000** (skipped at N=1000) | n/a | n/a | n/a | n/a | **`TIED_BY_DESIGN`** |

**Sources:**
- Baseline (Wave 88 N=1000): `verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json` (commit 6add1b9)
- Framework (Wave 79 n=2 proxy, reused in Wave 91 Phase 4): `verification_outputs/kanzi_upstream_framework_q4_2026.json`
- Wave 91 Phase 4 sweep: `verification_outputs/kanzi_n1000_framework_paper_metrics/kanzi_n1000_framework_paper_metrics.json` (n_seqs=2 emitted by upstream_eval layer; `--upstream-n-samples 1000` not honoured at kanzi upstream layer — see Wave 91 Phase 4 §4.3)
- Wave 91 Phase 2 bridge: `tools/kanzi_latent_to_coord.py` (committed in `dfe0f4e` Wave 91 Phase 2)

**Statistical test choice:** Welch t-test (`equal_var=False`) requires ≥2 observations per group. The framework arm has n=2 (Wave 79 proxy) so the variance is degenerate (1 degree of freedom → NaN p-value). Mann-Whitney requires ≥1 observation per group and produces a degenerate U-statistic at n=2 (rank sums {1, 2} → U ∈ {0, 1, 2}). Neither test yields a meaningful p-value at this sample size. We therefore report the n=2 framework-arm summary without a p-value and flag the verdict as `NOT_MEASURABLE_N1000`.

For the 5 codebook metrics, the framework arm does not change the values by design: the Kanzi `DAE.encode + DAE.decode + FSQ` round-trip is deterministic for a given input coords tensor, so the codebook statistics after the round-trip are dominated by the decoder (which is shared between baseline and framework arms). Wave 91 Phase 3 cannot move these 5 metrics either — they are `TIED_BY_DESIGN`.

---

## 2. Statistical power at N=1000 (forward-looking)

If Wave 91 Phase 3 lands (bridge wire into `tools/run_real_ckpt_eval.py:_run_cell`), the per-metric power analysis for `reconstruction_kabsch_rmsd_A` (one-sided test of `mean(framework) < mean(baseline) - 0.1 Å` with σ ≈ 0.14 Å from Wave 88 baseline std):

| n (per arm) | σ | effect | α | power (Welch) |
|---|---|---|---|---|
| 100 | 0.14 Å | 0.10 Å | 0.05 | ~0.91 |
| 500 | 0.14 Å | 0.10 Å | 0.05 | ~1.00 |
| **1000** | **0.14 Å** | **0.10 Å** | **0.05** | **~1.00** |

**Implication:** N=1000 framework arm gives essentially unlimited power to detect a 0.1 Å RMSD shift. If Phase 3 lands and framework improves by ≥0.1 Å, the verdict is statistically airtight; if it doesn't improve by ≥0.1 Å, the null reading is also definitive. The Wave 79 n=2 proxy `Δ=+0.769 Å` is *outside* the FSQ noise band (~0.5 Å step), but n=2 is not a statistical test.

The 5 codebook metrics are `TIED_BY_DESIGN` regardless of statistical power — the framework cannot change them through any N.

---

## 3. Internal composite axis (the framework DOES improve here)

The framework arm's `KanziGlue.compute_composite` (Wave 52 Agent A, byte-stable across NFE 10…2000) is computed by the eval pipeline regardless of the bridge wire state — it operates on the trajectory's per-position token indices, not on the reconstructed coords. This Wave 91 Phase 4 sweep's composite:

| Composite (Wave 52 KanziGlue) | Value |
|---|---:|
| `composite` (primary) | **+0.1895** |
| `phi1_entropy_reduction_normalised` | -0.0720 |
| `phi2_max_prob_delta` | -0.0460 |
| `phi3_argmax_turnover_signed` | **+0.9375** |
| weights | [0.4, 0.35, 0.25] |
| K (FSQ codebook cells) | 64 (adapter-side; real DAE vocab is 1000 — Wave 91 Phase 1 §2.1) |
| glue_class | KanziGlue |

**Internal composite axis verdict: SUPPORTED** (composite +0.1895 on KanziGlue's [-1, +1] scale, identical to Wave 52/Wave 58 byte-stable reading).

---

## 4. Honest caveats

### 4.1 FSQ quantisation noise floor

The Wave 91 Phase 1 audit (`docs/audit/wave91-phase1-audit.md` §5.1) and the Phase 2 bridge audit (`docs/audit/wave91-phase2-bridge.md` §5.1) document the FSQ quantisation noise band for the Wave 36 Kanzi ckpt:

* **FSQ basis:** `(8, 5, 5, 5)` → codebook_size = 1000
* **Per-row projection error:** ~half the basis spacing (~0.5 FSQ units in normalised latent space → ~0.5 Å in coord space after nm→Å)
* **Decoder stochasticity:** `DAE.decode` uses `torch.randn_like` for diffusion noise; unseeded, this contributes ~0.095 Å per-record run-to-run σ (Wave 88 F-4: 8 records × 8 unseeded repeats). Seeding drops the spread to 0.

The n=2 framework-arm proxy at 1.671 Å sits **outside** the FSQ noise band (+0.769 Å above the Wave 88 N=1000 baseline 0.902 Å), but the n=2 sample is too small to rule out sampling noise as the cause. **The honest interpretation: the framework arm at N=2 looks bad, but N=2 is not a statistical test.**

### 4.2 Bridge wire into `_run_cell` is NOT committed (Phase 3 missing)

Wave 91 Phase 2 authored `tools/kanzi_latent_to_coord.py` (committed in `dfe0f4e`) — the standalone bridge module that converts `(64, 64)` synthetic latent → `(L, 256)` continuous coords. **Phase 3 (the wire into `tools/run_real_ckpt_eval.py:_run_cell` that calls `kanzi_latent_to_coords(observe_endpoint(trace))` after the framework solver runs) was NOT committed.** Until Phase 3 lands, the framework arm's Kabsch RMSD at N=1000 cannot be measured through the public eval pipeline.

### 4.3 `--upstream-n-samples 1000` not honoured at upstream_eval layer

Even if Phase 3 were done, the current `tools/run_real_ckpt_eval.py:_KanziGlue` calls the upstream eval at the Wave 79 default `n_seqs=2` per cell. Wave 81 patched this for LineageFlow (`tools/upstream_eval.py: --hmmdb + --target-db args`) but the Kanzi upstream driver was not patched in Wave 81. A Phase 3 follow-up would also need to thread `--upstream-n-samples` into the Kanzi upstream call.

### 4.4 n=2 is not a statistical test

The Wave 79 n=2 framework-arm proxy was used by Wave 88 and Wave 89 to author the §7.3 Kanzi caveat, and it is the only data point we have for the framework arm on the paper-metric axis. Reporting a Δ +0.769 Å at n=2 without a p-value is **descriptive, not inferential**. Wave 91 Phase 3 was designed to produce a real N=1000 framework-arm number — without it, the framework-vs-baseline Tier 3 paper-metric verdict for Kanzi stays at the Wave 88/89 `NOT_MEASURABLE` reading.

### 4.5 Wave 79 n=2 proxy was RETRACTED in Wave 88 (separate point)

Wave 88 Agent B F-2 verified that `_extract_ca_coords_for_kanzi(trace)` falls back to `",".join(["0.0"] * 30)` on every trace (the `_StubLineageFlow`-style placeholder bug). The Wave 79 n=2 reading of "baseline 1.40 Å vs framework 1.67 Å, Δ=+0.27 Å" is **retracted** as an artifact. The 1.67 Å Wave 79 n=2 reading cited in Wave 91 Phase 4 is from the `kanzi.DAE.encode + decode + kabsch_rmsd` upstream eval (a separate path), NOT from the retracted `_extract_ca_coords_for_kanzi` placeholder. Per `verification_outputs/kanzi_upstream_framework_q4_2026.json:upstream_eval_metrics.mean_rmsd_A: 1.6711168560108585`, this is the real upstream Kabsch RMSD pipeline number. The retraction applies only to the `_extract_ca_coords_for_kanzi(trace)` placeholder artifact in `tools/run_real_ckpt_eval.py:4119-4144`, not to the Wave 79 upstream-eval number.

---

## 5. Wave 91 W2 verdict evolution table (Kanzi paper-metric, all waves)

| Wave | Sample size (per arm) | Baseline | Framework | Δ | Verdict | Source |
|---|---|---:|---:|---:|:---|---|
| **Wave 79** (Phase 3 first run, retracted placeholder) | n=2 | 1.40 Å | 1.67 Å | +0.27 Å | `TIES` (FSQ noise band) — RETRACTED in Wave 88 F-2 | placeholder artifact |
| **Wave 79** (upstream-eval path, NOT retracted) | n=2 | 1.40 Å | 1.671 Å | +0.27 Å | `TIES` (FSQ noise band) | `kanzi_upstream_framework_q4_2026.json` |
| **Wave 80** | n=32 (smoke) | 0.887 Å | n/a (smoke baseline-only) | n/a | `framework_improves_inconclusive_n=32_noisy_band` | `wave80_kanzi_smoke_eval/reconstruction.json` |
| **Wave 83** | n=200 (1s7mB01-dominant first 200 records) | 0.824 Å (std 0.132) | n/a | n/a | `framework_improves_inconclusive_noisy_band` | `kanzi_n1000_paper_metrics.json` |
| **Wave 88** | n=1000 baseline + framework `NOT_MEASURABLE` (structural) | 0.902 Å (std 0.137) | n/a (no bridge) | n/a | `NOT_MEASURABLE` (framework arm); `TIE_NOISY_BAND` baseline-only | Wave 88 F-3 + Wave 88 baseline sweep |
| **Wave 91 Phase 4** (this) | n=1000 baseline + n=2 framework proxy | 0.902 Å | 1.671 Å | +0.769 Å | `NOT_MEASURABLE_N1000` (n=2 too small; Phase 3 not committed) | Wave 91 Phase 4 §3 |

The headline Wave 91 number is the **same Wave 88 status** (`NOT_MEASURABLE_N1000` for the framework arm): the bridge is authored but not wired into `_run_cell` (Phase 3 missing), and `--upstream-n-samples 1000` is not honoured at the upstream_eval layer for kanzi. The +0.769 Å at n=2 is *outside* the FSQ noise band, but n=2 is not a statistical test.

---

## 6. Verification status (Wave 91 Phase 5)

### 6.1 D.4 byte-stable regression

```text
.venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_d4_regression_vectors.py \
    tests/test_adapters/test_regression_vectors.py -q --tb=line
```

```
........................................................................ [100%]
=============================== warnings summary ===============================
tests/test_d4_regression_vectors.py::test_d4_first_batch_vector_reproduces_on_current_host[flowmol3]
  /home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/molecular/__init__.py:151: DeprecationWarning: RMSPreservingCoordinateMixer is deprecated; use EqualRmsCoordinateMixer
    from .mixer import (

... (3 pre-existing DeprecationWarnings from commit 28e3bf9 lazy __getattr__ shim)

72 passed, 3 warnings in 42.70s
```

**Status: PASS — 72/72 in 42.70s.** Wallclock variance only vs Wave 86/87/88 baselines (42-46s range); no regression. 3 pre-existing DeprecationWarnings unchanged.

### 6.2 G-MASTER capability gate

```text
.venvs/flowmol3_venv/bin/python tools/capability_audit.py --robust \
    --output /tmp/wave91_final_capability.json
```

```
{
  "hard_pass": 5,
  "hard_fail": 0,
  "hard_pending": 0,
  "soft_pass": 2,
  "g_master_capability": "PASS",
  "must_4_freeze_gate": "PASS"
}
```

**Status: PASS — 7/7 (hard_pass=5, soft_pass=2).** Unchanged from Wave 86/87/88 closure (paper-edit only).

### 6.3 mkdocs build --strict

```text
PATH=/home/hugo/codes/flowa-multistep-reinference/.venvs/flowmol3_venv/bin:$PATH \
    mkdocs build --strict
```

```
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 13.47 seconds
```

**Status: PASS — EXIT=0 in 13.47s.** Wave 73 Phase 6 `not_in_nav` fix for `push-ready-summary.md` preserved.

---

## 7. File:line citation index

| Citation | Path |
|---|---|
| `--kanzi-upstream-eval` flag (Wave 79 wire) | `tools/run_real_ckpt_eval.py:5107` |
| Wave 79 n=2 framework-arm proxy (upstream-eval path) | `verification_outputs/kanzi_upstream_framework_q4_2026.json` |
| Wave 88 N=1000 baseline arm | `verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json` (commit 6add1b9) |
| Wave 91 Phase 2 bridge module | `tools/kanzi_latent_to_coord.py` (commit dfe0f4e) |
| Wave 91 Phase 2 bridge audit | `docs/audit/wave91-phase2-bridge.md` |
| Wave 91 Phase 1 audit (constant mismatch) | `docs/audit/wave91-phase1-audit.md` |
| Wave 91 Phase 4 N=1000 framework sweep | `verification_outputs/kanzi_n1000_framework_paper_metrics/kanzi_n1000_framework_paper_metrics.json` |
| Wave 91 Phase 4 per-metric JSON | `verification_outputs/kanzi_n1000_framework_paper_metrics/per_metric.json` |
| Wave 91 Phase 4 audit (numbers + verdict) | `docs/audit/wave91-phase4-eval.md` |
| Wave 88 NOT_MEASURABLE verdict | commit 6add1b9 (Wave 88) |
| Wave 89 final synthesis | commit e77d2d4 (Wave 89) |
| Wave 91 Phase 5 final synthesis (this doc) | `docs/audit/wave91-phase5-final.md` |
| Wave 91 Phase 5 paper update | `docs/paper-draft.md` §7.3 (this wave) |
| Wave 91 Phase 5 push-ready | `docs/push-ready-summary.md` Wave 91 Phase 5 (this wave) |

---

## 8. Wave 91 → Wave 92+ plan surface

- **Wave 92+ (or future):** Apply Wave 91 Phase 3 — wire `tools/kanzi_latent_to_coord.py` into `tools/run_real_ckpt_eval.py:_run_cell` (a) load `DAE.from_pretrained` in `_KanziGlue`, (b) call `kanzi_latent_to_coords(observe_endpoint(trace))` after the framework solver runs, (c) thread `--upstream-n-samples` into the Kanzi upstream call. Combined with the Wave 91 Phase 2 bridge, this unblocks the framework arm's Kabsch RMSD at N=1000 in <30 min wallclock.

- **Wave 93+:** Statistical-power confirmation sweep — if Phase 3 lands, run the framework arm at N=1000/2000/5000 and verify the framework-vs-baseline delta at statistical significance (σ ≈ 0.14 Å, MDD @ α=0.05 power=0.8 ≈ 0.016 Å).

- **Wave 94+:** ICLR 2027 submission package — bundle the Wave 76-91 Tier 3 paper-metric final status (LineageFlow `framework_improves` on `hmmscan_total_hits` +116% p<1e-10, FlowMol3 `framework_improves` on `fg_dev` 4.05σ, Kanzi `NOT_MEASURABLE_N1000` if Phase 3 not landed / `framework_improves` if Phase 3 lands and confirms a real delta).

These are not blockers for push. The repo is push-ready as-is.

---

## 9. Per-metric JSON

`verification_outputs/kanzi_n1000_framework_paper_metrics/per_metric.json` — programmatic copy of the §1 table (machine-readable for downstream consumers, including the next Wave 92/93 phase).

---

## 10. Unpushed commits count

```text
git log --oneline @{u}..main 2>&1 | wc -l
```

```
309
```

**309 unpushed commits** on `main` ahead of `origin/main`. Wave 91 Phase 5 commit lands locally without push, matching the Wave 68-90 closure pattern.

---

*End of Wave 91 Phase 5 final synthesis.*
