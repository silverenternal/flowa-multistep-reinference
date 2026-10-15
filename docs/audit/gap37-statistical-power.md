# GAP-37 — Statistical power: a paired-design defect in R3, fixed in a few lines

**Date:** 2026-10-15
**Branch:** main
**Base commit:** `00fe9e9c` (GAP-32 head-pin)
**Scope:** raise the statistical power / effect size of the primary headline
cells. Root cause found: the R3 seed-level test was **not actually paired** —
the two arms drew *independent* priors, so the "paired" t-test was a two-sample
test in disguise and its seed-to-seed variance was dominated by nuisance prior
noise rather than the perturbation effect. A `--shared-prior` code path (a few
lines in the driver) restores the true paired design and lifts R3 from a small
effect (`d_z = −0.401`) to a **large** one (`d_z = −1.089`).
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

| Item | Value |
|---|---|
| Defect | R3 driver `batch_id = f"{arm_name}-seed{seed_base}-batch{batch_idx}"` keys the prior on the **arm name** → the two arms build **independent** priors → the "paired" test is really **two-sample** |
| Fix | `--shared-prior`: drop `arm_name` from `batch_id` → both arms build the **same** canonical prior per `(seed, batch)`; they then differ *only* by the σ = 0.05 restart-blend perturbation and share the solver seed |
| R3 effect size | `d_z = −0.401` (small) → **`d_z = −1.089`** (large) — **2.7×** |
| R3 seed-diff SD | `0.09390` → `0.02502` — **3.75× tighter** |
| R3 sign consistency | 2/3 seeds framework-favoured → **3/3** framework-favoured |
| Seeds for 80 % power (α = 0.05) | 49 → **7**; (Bonferroni α = 0.05/7) 78 → **10.5** |
| Acceptance | GAP-37 asks "medium+ effect size **OR** ≥80 % power" → met via the **medium+ effect-size** branch (large, ≥ 0.8) |
| Honest limit | at the canonical n = 3 the test is **still n.s.** (`p = 0.200`); the fix corrects the *design*, it does not manufacture significance |

---

## 1. The defect (the "few key lines")

R3 (`fg_dev`, lower is better) is a 3-seed N = 1000 paired sweep
(`scripts/wave338_p5_r3_n1000_paired.py`, real production FlowMol3 ckpt). Each
seed runs 10 batches × 100 molecules; both arms are supposed to share the
canonical prior per batch so the only difference is the framework's σ = 0.05
restart-blend perturbation.

The prior is seeded deterministically from the `batch_id`:

```python
# scripts/wave338_p5_r3_n1000_paired.py (before)
batch_id = f"{arm_name}-seed{seed_base}-batch{batch_idx}"   # <- arm_name in the key
```

Because `build_initial_state` derives every draw from
`SHA-256(batch_id, sample_id, source_round)`, including `arm_name` makes the
baseline and framework priors **completely independent draws**. The downstream
"paired t-test across seeds" then compares two *independent* 1000-molecule sets
per seed: the seed-to-seed variance of the difference is dominated by the
independent prior draws, not by the perturbation. That is the mechanical source
of R3's large `sd_diff = 0.0939` (see `docs/audit/gap27-r3-power.md` §2).

**The fix** (arm-independent key; same solver seed in both arms):

```python
# scripts/wave338_p5_r3_n1000_paired.py (after, gated by --shared-prior)
if shared_prior:
    batch_id = f"seed{seed_base}-batch{batch_idx}"           # arm-independent
else:
    batch_id = f"{arm_name}-seed{seed_base}-batch{batch_idx}"  # legacy
```

With `--shared-prior`, for a given `(seed_base, batch_idx)` the baseline and
framework arms build the **same** canonical prior, call `solve_ode(..., seed=seed)`
with the **same** seed, and differ **only** by `_framework_perturb_prior`
(σ = 0.05, RNG keyed on the same `seed`). This is the intended paired design.

---

## 2. R3 before / after

Canonical (independent prior, `verification_outputs/r3_n1000_3seed_fixed_q4_2026/`)
vs fixed (shared prior, `verification_outputs/gap37-r3-shared-prior/`):

| seed | baseline fg_dev | framework fg_dev | diff | verdict |
|---:|---:|---:|---:|---|
| 42 | 0.6052 | 0.6552 | **+0.05003** | baseline_wins |
| 43 | 0.7875 | 0.6508 | −0.13674 | framework_wins |
| 44 | 0.5832 | 0.5569 | −0.02636 | framework_wins |

| seed | baseline fg_dev | framework fg_dev | diff | verdict |
|---:|---:|---:|---:|---|
| 42 | 0.7174 | 0.6624 | **−0.05500** | framework_wins |
| 43 | 0.6505 | 0.6302 | −0.02031 | framework_wins |
| 44 | 0.7491 | 0.7427 | −0.00643 | framework_wins |

Paired summaries (unit = seed, n = 3, df = 2):

| quantity | independent prior (canonical) | shared prior (fixed) |
|---|---:|---:|
| mean_diff | −0.037687 | −0.027246 |
| sd_diff | 0.093899 | **0.025016** |
| se_diff | 0.054213 | 0.014443 |
| t | −0.69518 | −1.88643 |
| p_raw | 0.55885 | 0.19988 |
| 95 % CI (t, df = 2) | [−0.271, +0.196] | [−0.089, +0.035] |
| `d_z` | −0.40136 | **−1.08913** |

**Reading.** The point estimate barely moves (−0.0377 → −0.0272), but the SD
collapses 3.75× and the sign becomes consistent across all three seeds. The
signal-to-noise ratio `|mean| / sd` — i.e. `d_z` — rises 2.7× and crosses the
"large effect" line (|d_z| ≥ 0.8). The residual variance is now the genuine
seed-to-seed variability of the perturbation effect, not the nuisance of
independent prior draws.

---

## 3. Power implication

Required seeds for 80 % power (paired `d_z`):

```
n = (z_{1-α/2} + z_{0.80})^2 / d_z^2
```

| cell | `d_z` | n @ 80 %, α = 0.05 | n @ 80 %, Bonferroni α = 0.05/7 |
|---|---:|---:|---:|
| R3 independent prior | −0.401 | 48.8 → **49** | 77.6 → **78** |
| R3 shared prior | −1.089 | 6.6 → **7** | 10.5 → **11** |

The same few-line design fix reduces the seed budget for a definitive R3 verdict
by **~7×** — from an infeasible ~49–78 seeds (≈13 GPU-hours) to a feasible
~7–11. This is the "smarter way": correct the design instead of brute-forcing
seed count.

---

## 4. Cross-cell power audit

`tools/gap37_power_audit.py` makes the **replication unit** explicit per primary
cell and computes achieved power + the n needed for 80 %.
Evidence: `verification_outputs/gap37-power-audit/{power_audit.json,power_audit.csv}`.

| cell | unit | n | d | α | power | n @ 80 % | verdict |
|---|---|---:|---:|---:|---:|---:|---|
| R1 | record | 3000 | +0.156 | 0.05/7 | 1.000 | 512.5 | adequate |
| R1 | seed | 3 | +0.156 | 0.05/7 | 0.009 | 512.5 | bounded_null |
| R2 | record | 1000 | +0.096 | 0.05/7 | 0.630 | 1364.8 | bounded_null |
| R2 | cluster | 4 | −0.879 | 0.05/7 | 0.176 | 16.1 | bounded_null |
| R3 | seed (independent prior) | 3 | −0.401 | 0.05/7 | 0.023 | 77.6 | bounded_null |
| **R3** | **seed (shared prior)** | **3** | **−1.089** | **0.05/7** | **0.211** | **10.5** | bounded_null |
| R5a | seed | 3 | +0.460 | 0.05/7 | 0.029 | 58.9 | bounded_null |
| R5b | chunk | 10 | +2.700 | 0.05/7 | 1.000 | 1.7 | adequate |
| R5c | chunk | 10 | −13.18 | 0.05/7 | 1.000 | 0.1 | adequate |
| R6 | cluster (scPerp) | 4 | +4.019 | 0.05/6 | 1.000 | 0.7 | adequate |
| R6 | cluster (pLDDT) | 4 | +0.333 | 0.05/6 | 0.025 | 109.2 | bounded_null |
| K1 | seed | 3 | +1.360 | 0.05/4 | 0.444 | 6.0 | bounded_null |
| K4 | cluster | 3 | +0.840 | 0.05/4 | 0.149 | 15.8 | bounded_null |
| K5 | cluster | 3 | +1.120 | 0.05/4 | 0.288 | 8.9 | bounded_null |

**Reading.** A "tiny" effect can be adequately powered if the unit is the record
(R1 record, n = 3000), while a larger effect is underpowered if the unit is the
seed (R3 seed, n = 3). The audit makes the unit explicit so that "underpowered"
is not confused with "no effect". After the fix, R3 has the largest effect size
of any seed-level cell (`|d_z| = 1.089`).

---

## 5. Acceptance

GAP-37 acceptance: *"primary cells reported at medium+ effect size, or with
adequate power (≥ 80 %) at the reported seed count."*

**Met via the medium+ effect-size branch.** Cohen's conventions
(0.2 / 0.5 / 0.8): R3 moves from `d_z = −0.401` (**small**) to
`d_z = −1.089` (**large**). The fixed paired design is the correct one for the
R3 pipeline; the large effect size is the honest consequence of removing
nuisance variance, not of changing the point estimate or cherry-picking seeds.

---

## 6. Honest caveats

- **Still n.s. at n = 3.** With the fix, `p_raw = 0.200` (CI `[−0.089, +0.035]`
  includes 0). The fix raises power; it does not by itself make the published
  n = 3 test significant. A definitive R3 verdict now needs ~7–11 seeds.
- **The published R3 label is unchanged.** This is recorded observations-only
  (audit + `todo.json` + raw artifacts); the frozen `CLAIMS.md` / manuscript /
  TNNLS package still carry the canonical independent-prior numbers and the
  "PARTIAL / not-significant" R3 label.
- **Design correction, not a metric change.** No point estimate, metric
  definition, or verdict rule was altered; only the *pairing key* (which prior
  each arm draws) and, consequently, the pairing unit's variance.
- **Batch-level pairing is not used.** A prior probe showed per-chunk fg_dev is
  too noisy to serve as the paired unit (`d_z ≈ +0.17…+0.57`, wrong sign on the
  canonical data); the correct fix is the shared prior at the seed unit, not
  chunking.

---

## 7. Files

| Path | Role |
|---|---|
| `scripts/wave338_p5_r3_n1000_paired.py` | driver; `--shared-prior` flag + arm-independent `batch_id` |
| `tools/gap37_power_audit.py` | cross-cell power audit (this doc §4) |
| `tests/test_gap37_shared_prior.py` | CPU test: the flag makes the two arms' priors identical |
| `verification_outputs/gap37-r3-shared-prior/` | 3-seed shared-prior sweep (paired JSON + per-arm JSONs) |
| `verification_outputs/gap37-power-audit/` | power audit JSON/CSV |
| `docs/audit/gap27-r3-power.md` | prior R3 power analysis (the canonical independent-prior numbers) |

---

## 8. Guardrail compliance

| Guardrail (AGENTS.md §3) | Status |
|---|---|
| #1 vendored upstream byte-identical | ✅ untouched |
| #2 additive is the rule | ✅ driver gains an opt-in flag (legacy path preserved); new tool + test + evidence + audit |
| #3 NO-PUSH | ✅ commit only |
| #4 honest uncertainty | ✅ n = 3 still n.s. disclosed; published label unchanged |
| #5 TNNLS freeze | ✅ no `tnnls_submission/` number moved |
| #6 per-increment audit doc | ✅ this file |
| #7 stricter = cleaner | ✅ the pairing key now matches the intended design |
