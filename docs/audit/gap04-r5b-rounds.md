# GAP-04-R5B-ROUNDS — matched multi-seed round-count test

**Date:** 2026-10-13
**Author:** GAP-04 agent (USER AUTHORIZED, NO PUSH)
**Scope:** `todo.json` GAP-04-R5B-ROUNDS — close the missing `n_rounds = 3`
cell of the matched-protocol round-count test and re-state the boundary as a
multi-seed result.
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

| Item | Value |
|---|---|
| Boundary verdict | **CONFIRMED** at multi-seed on the FID axis |
| `n_rounds = 1` | 2/4 schedulers **framework-WINS**, 1 TIE, 1 MIXED (worst arm +0.33 %) |
| `n_rounds = 2` | 3/4 schedulers **REGRESS** (+21.0 % to +30.6 % FID); CodimensionSheet MIXED (−0.30 %) |
| `n_rounds = 3` | 3/4 schedulers **REGRESS** (+20.5 % to +21.4 % FID); CodimensionSheet MIXED (+0.09 %) |
| New cell closed | `n_rounds = 3` × seeds 43, 44 (seed 42 already existed) |
| **Material disclosure** | The **framework arm is byte-identical across seeds** — `WAVE247_SEED` moves only the baseline arm. The "3 seeds" probe **baseline-side** variability, not framework-side. Direction is consistent across all 3 baseline draws. |

---

## 1. Protocol

Driver: `scripts/gap04_r5b_rounds_multiseed.py` (committed `ea1e36a`).

- Runner: `tools/run_sota_cifar_experiment.py`, `--device cuda`,
  `--n-samples 200 --framework-samples 200`, `--baseline-num-steps 50`,
  `--framework-max-num-steps 50`, `--integrator euler`, `--match-nfe budget`.
- Grid: `n_rounds ∈ {1, 2, 3}` × 4 schedulers × `WAVE247_SEED ∈ {42, 43, 44}`.
- Seed plumbing: the runner reads `WAVE247_SEED` at
  `tools/run_sota_cifar_experiment.py:1423` (baseline) and `:1448`
  (framework `seed_base`).
- FID: recomputed uniformly from the cached InceptionV3-tfport features with
  `wave247_p2_r5b_multiseed._fid_numpy` (baseline FID 447.894 / 455.682 /
  453.657 for seeds 42/43/44 — the same 447.8943 as the GAP-12 R5b
  tuned-baseline sweep at baseline NFE = 50, i.e. the FID path is shared).
- GPU: `CUDA_VISIBLE_DEVICES=1` (GPU 0 was reserved for the GAP-01 R6 sweep).
- 9 cells, 1167–1573 s wall each.

---

## 2. Result — ΔFID vs the matched-NFE baseline (negative = framework better)

Per-seed ΔFID (%) at N = 200, matched NFE = 50:

| scheduler | `n_rounds = 1` | `n_rounds = 2` | `n_rounds = 3` |
|---|---|---|---|
| CosineAnnealScheduler | −0.17 / −1.88 / −1.44 (**WINS**) | +22.65 / +20.55 / +21.09 (REGRESSES) | +22.65 / +20.55 / +21.09 (REGRESSES) |
| CodimensionSheetScheduler | −1.12 / −2.81 / −2.37 (**WINS**) | +0.70 / −1.02 / −0.58 (MIXED) | +1.09 / −0.64 / −0.19 (MIXED) |
| EvidenceDrivenScheduler | +1.34 / −0.40 / +0.05 (MIXED) | +22.20 / +20.11 / +20.64 (REGRESSES) | +22.20 / +20.11 / +20.64 (REGRESSES) |
| FreeTrajScheduler | +0.78 / −0.94 / −0.50 (TIE) | +31.94 / +29.69 / +30.27 (REGRESSES) | +21.67 / +19.59 / +20.13 (REGRESSES) |

Aggregate (`verification_outputs/gap04-r5b-rounds-multiseed.csv`):

| `n_rounds` | WINS | REGRESSES | MIXED | TIE |
|---:|---:|---:|---:|---:|
| 1 | 2 | 0 | 1 | 1 |
| 2 | 0 | 3 | 1 | 0 |
| 3 | 0 | 3 | 1 | 0 |

**Reading.** The `n_rounds = 1 → ≥ 2` flip is reproduced at multi-seed for
CosineAnneal, EvidenceDriven and FreeTraj (all three cross from win/neutral to
+20 %…+32 % FID). CodimensionSheet is the stable exception: it never regresses
(−2.10 % at 1 round, −0.30 % at 2, +0.09 % at 3) and its per-seed sign flips
across seeds at `n_rounds ≥ 2`, i.e. it is genuinely neutral rather than
winning.

The `cohens_dz` column in the aggregate JSON is the standardized magnitude of
the **per-sample feature-space displacement**
(`diff_sq = ((f_baseline − f_framework)²).sum(axis=1)`), so it is positive by
construction (4.1–6.0 here) and carries no direction. The win/loss verdict is
the **sign of ΔFID**, not the sign of `d_z`.

---

## 3. Material disclosure — the framework arm is seed-invariant

`_run_framework_state_chains` (`tools/run_sota_cifar_experiment.py:725`)
accepts `seed_base` but **never uses it**: the only seed-like quantity in the
function body is `SCHEDULER_SEED_OFFSETS.get(scheduler_name, 0)`, a fixed
per-scheduler constant. Consequently `WAVE247_SEED` moves only the baseline
arm.

Verified directly (md5 of the per-arm sample archives, all 9 cells):

```
rounds1: cosineanneal distinct_hashes=1  codimensionsheet=1  evidencedriven=1  freetraj=1
rounds2: cosineanneal distinct_hashes=1  codimensionsheet=1  evidencedriven=1  freetraj=1
rounds3: cosineanneal distinct_hashes=1  codimensionsheet=1  evidencedriven=1  freetraj=1
baseline (rounds3): e5d5f8f6 / 9c05986e / cf54e733   # all three differ
```

**Therefore this sweep is 1 framework draw × 3 baseline draws.** The correct
statement is *"the round-count boundary is invariant to three independent
baseline draws at fixed framework output"* — **not** "3 independent framework
seeds". The boundary conclusion is unaffected (it is consistent across every
baseline draw), but the multi-seed framing must not overstate the design. The
same caveat applies to the earlier Wave 247 P2 `n_rounds = 1` multi-seed claim
and to the GAP-12 R5b tuned-baseline sweep (where the framework arm is likewise
one fixed draw).

No frozen surface was changed by this finding; it is recorded here and in
`todo.json`.

---

## 4. Acceptance

`todo.json` acceptance: *"round-count boundary confirmed or refuted at
multi-seed."* → **CONFIRMED**, with the seed-invariance disclosure of §3.
Residual: the framework-side multi-seed axis is still untested (the runner
would need `seed_base` to reach `batched_inference`); that is a runner change,
not a GAP-04 requirement, and is left as a documented caveat.

---

## 5. Artifacts

- `verification_outputs/gap04-r5b-rounds{1,2,3}-seed{42,43,44}-n200/`
  (`summary.json`, per-arm `*_samples.npz`, `inception_feats_cache/`).
- `verification_outputs/gap04-r5b-rounds-multiseed.json` (per-cell + aggregate).
- `verification_outputs/gap04-r5b-rounds-multiseed.csv` (headline table).
- `verification_outputs/_gap04-logs/gap04-r{1,2,3}-seed*.log` (raw runs).
- Driver: `scripts/gap04_r5b_rounds_multiseed.py`.

Reproduce the aggregate from the existing cells:

```
CUDA_VISIBLE_DEVICES=1 python scripts/gap04_r5b_rounds_multiseed.py \
    --skip-runs --seeds 42,43,44 --n-rounds 1,2,3 --n-samples 200
```

---

## 6. Gates

`check_claims_consistency.py` → No drift · `check_docs_against_code.py` →
OK 4143 claims · `pytest tests/test_d4_regression_vectors.py` → 30 passed ·
`mkdocs build --strict` → PASS.
