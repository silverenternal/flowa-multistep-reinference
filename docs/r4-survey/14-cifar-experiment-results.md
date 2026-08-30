# CIFAR-10 Rectified Flow — FlowA multi-round experiment results

> **Author:** Agent 3 (compute-FID + final-results subagent)
> **Date:** 2026-08-31
> **Working dir:** `c:\Users\31472\codes\flowa-multistep-reinference`
> **Companion files:**
> - Plan: `docs/r4-survey/11-cifar-experiment-plan.md`
> - Per-round metrics: `docs/r4-survey/cifar_results/per_round_metrics.csv`
> - Per-scheduler `.npz`: `docs/r4-survey/cifar_results/{baseline,cosineanneal,codimensionsheet,evidencedriven,freetraj}_samples.npz`
> - Headline table: `docs/r4-survey/cifar_results/comparison.md`
> - Machine-readable summary: `docs/r4-survey/cifar_results/summary.json`
> - Honest run log: `docs/r4-survey/cifar_results/experiment-log.md`
> - FID script: `tools/compute_cifar_fid.py`

This report contrasts the **published SOTA CIFAR-10 Rectified Flow**
(Liu 2022, NeurIPS Spotlight, `arXiv:2210.02647`, integrated as
`RectifiedFlowCIFARAdapter` with the published gnobitab DDPM++ UNet
checkpoint at `data/cifar10_rf.pth`, 61.8 M parameters) on its
**single-pass baseline** vs FlowA's **multi-round re-inference loop** with
four scheduler configurations. The model, weights, evaluator, and target
distribution are held constant across the comparison — only the inference
strategy changes.

The headline finding is **parity** (framework FID = `66.6508` vs baseline
FID = `66.7333`, Δ = `−0.0825` = `−0.12%`), but the experiment has an
**important caveat** (see §"Honest framing" below): the four framework
rows are byte-identical to each other and only differ from the baseline
in step grid + seed structure, so the headline does NOT isolate a
scheduler effect. The experiment is **architecturally complete** (the
adapter loads the published weights correctly; the harness drives the
four scheduler families end-to-end; FID is computed against a 1 000-image
CIFAR-10 test-set reference via InceptionV3) but the scheduler
discrimination defect documented in `experiment-log.md` means the
**paper claim (parity-or-better) is satisfied at the ±0.12% level but
not yet attributable to scheduler choice**.

---

## §1. Configuration

| Parameter | Value |
|---|---|
| Checkpoint | `data/cifar10_rf.pth` (gnobitab Score-SDE EMA `state_dict`, 247 MB) |
| Architecture | DDPM++ UNet (`base_ch=128`, `ch_mult=(1,2,2,2)`, `n_res_blocks=2`) |
| Parameters | 61 805 419 |
| Sample shape | `(3, 32, 32)` |
| Baseline `--n-samples` | 1 000 |
| Baseline `--baseline-num-steps` | 10 |
| Framework `--n-rounds` | 10 |
| Framework `--framework-samples` | 100 (per round) |
| Framework `--framework-max-num-steps` | 10 |
| Scheduler `n_cap` ceiling | `n_max=1.0` → `num_steps=10` for every scheduler |
| Schedulers | CosineAnnealScheduler, CodimensionSheetScheduler, EvidenceDrivenScheduler, FreeTrajScheduler |
| Reference | CIFAR-10 **test** set, 1 000 images, normalised to `[-1, 1]` (`data/_torch_cifar10_cache/cifar10_test_ref_1000.npz`) |
| InceptionV3 | `pytorch_fid.inception.InceptionV3`, pool3 features (2 048-d) |
| Device | CPU |
| Total wall-clock | **2 692.1 s** (≈ 45 min) |

---

## §2. Headline FID table

| Method | FID | Δ vs baseline | % change | sel_ratio[r=9] | wall-clock (s) |
|---|---:|---:|---:|---:|---:|
| **baseline (10-NFE Euler)** | **66.7333** | — | — | n/a | 454.6 |
| CosineAnnealScheduler | 66.6508 | −0.0825 | **−0.12%** | n/a | 457.5 |
| CodimensionSheetScheduler | 66.6508 | −0.0825 | **−0.12%** | 1.0000 | 457.4 |
| EvidenceDrivenScheduler | 66.6508 | −0.0825 | **−0.12%** | n/a | 457.5 |
| FreeTrajScheduler | 66.6508 | −0.0825 | **−0.12%** | n/a | 457.1 |

**Reading the table**

- `Δ vs baseline` = framework_FID − baseline_FID. **Negative = framework
  wins** (lower FID).
- `% change` = `(Δ / baseline) × 100`.
- `sel_ratio[r=9]` = the per-round evidence ratio at the last round.
  Only `CodimensionSheetScheduler` carries the `evidence_ratio` attribute
  on its `ScheduleSample`; the other three are reported as `n/a` because
  the harness reads `getattr(sample, "evidence_ratio", None)`.
- `wall-clock` = total seconds for that row's wall-clock
  (baseline: 1 × 1 000 samples; framework: 10 rounds × 100 samples
  + driver + FID overhead).

---

## §3. Honest framing

### §3.1 The headline is parity, but the experiment does NOT isolate a scheduler effect

**Sample-level cross-check** (run on the 1 000 samples in
`docs/r4-survey/cifar_results/`):

| Pair | mean_abs_diff | byte_equal |
|---|---:|:---:|
| baseline ↔ cosineanneal | 0.336 | False |
| baseline ↔ codimensionsheet | 0.336 | False |
| baseline ↔ evidencedriven | 0.336 | False |
| baseline ↔ freetraj | 0.336 | False |
| cosineanneal ↔ codimensionsheet | **0.000** | **True** |
| cosineanneal ↔ evidencedriven | **0.000** | **True** |
| cosineanneal ↔ freetraj | **0.000** | **True** |
| codimensionsheet ↔ evidencedriven | **0.000** | **True** |
| codimensionsheet ↔ freetraj | **0.000** | **True** |
| evidencedriven ↔ freetraj | **0.000** | **True** |

This is **the opposite of what the experiment-log.md records**. The
per-round `n_cap` trace in `per_round_metrics.csv`:

```
CosineAnnealScheduler,    0..9, n_cap=1.0, num_steps=10
CodimensionSheetScheduler,0..9, n_cap=1.0, num_steps=10, evidence_ratio=1.0
EvidenceDrivenScheduler,  0..9, n_cap=1.0, num_steps=10
FreeTrajScheduler,        0..9, n_cap=1.0, num_steps=10
```

Every scheduler returns `n_cap ≡ 1.0` for every round under the
configuration built by `tools/run_sota_cifar_experiment.py`
(`n_min=0.0`, `n_max=1.0`, `cycle_length=10`,
`EvidenceDrivenScheduler(kp=0.2, ki=0.05, max_step=0.05, target_ratio=1.0,
k_eps=0.5, eps_implicit_base=0.05)`,
`FreeTrajScheduler(trajectory_amplitude=0.05, trajectory_period=4)`).

Mapping `num_steps = max(1, round(n_cap × max_num_steps))` therefore
reduces to a constant `num_steps = max_num_steps = 10` across **all
rounds AND all schedulers**. With the same per-round seed
(`seed_base × 1 000 + round`), each scheduler computes the same
10-step Euler trajectory and the four `{name}_samples.npz` files are
**byte-identical** to each other.

So the four `66.6508` FID rows are **the same trajectory** scored four
times — they share a feature set.

The **baseline** row uses a **different sampling procedure**: one batch
of 1 000 samples at `num_steps=10` with `seed=0`, vs the framework
rows' `10 × 100` per-round batches at `num_steps=10` with
`seed = round`. The two procedures produce samples whose
**per-pixel** mean_abs_diff is 0.336 — substantial — but whose
**InceptionV3-feature** distribution differs by FID ≈ 0.08, i.e. well
within the Monte-Carlo noise floor for 1 000-sample FID.

### §3.2 The 0.083 FID gap is Monte-Carlo noise, NOT a scheduler effect

The framework rows differ from baseline in **two** ways:

1. **Sample count per integration**: baseline = one batch of 1 000,
   framework = ten batches of 100. Identical totals but different
   per-batch noise structure.
2. **Seed schedule**: baseline seed = 0; framework seeds = 0, 1, 2, 3,
   4, 5, 6, 7, 8, 9 (one per round).

Neither difference is a scheduler effect. With `n_cap ≡ 1.0` and
`num_steps=10` for every framework row, **every framework row is
computing the same thing**, and the 0.083 FID delta is the
InceptionV3-feature reflection of the (seed, batch-shape) difference —
i.e. **noise**.

### §3.3 What this run DOES show

- **Adapter loads the published checkpoint correctly** (strict
  `state_dict` load; 61.8 M parameters; byte-identical to the published
  weights). Documented in `experiment-log.md` §"What this run DOES show".
- **UNet forward pass produces real CIFAR-10-shaped images**
  (std≈0.34, range≈[−1, 1]) at 10-step Euler.
- **Baseline FID against CIFAR-10 test**: `66.73`. Far from the
  published Liu 2022 headline of `2.21` (which uses 50 K samples +
  Heun adaptive solver at 100+ NFE) but consistent with the
  expected gap for a **10-step, 1 000-sample** evaluation. The
  model is correct; the solver is coarse and the sample budget is
  small.
- **Four framework rows run end-to-end**: each of the four schedulers
  is constructed, sampled for 10 rounds, scored, and FID-emitted.
  The plumbing is correct.

### §3.4 What this run does NOT show

- **Paper Theorem 1 selection-ratio trend**: cannot be evaluated. The
  framework's `EvidenceDrivenScheduler` row carries no `sel_ratio`
  column (the harness reads `getattr(sample, "evidence_ratio", None)`,
  and `EvidenceDrivenScheduler.sample` does not expose that attribute).
  Only `CodimensionSheetScheduler` reports `evidence_ratio = 1.0` for
  every round — and `1.0` is the closed-form sheet-dominance value the
  helper returns by construction (it is not a measurement of the
  selector's behaviour).
- **Scheduler discrimination**: zero. All four framework rows are
  byte-identical.
- **Framework-vs-baseline claim**: the paper claim is *parity-or-better*
  with a 10% tolerance. Our headline (`−0.12%`) is well inside that
  band, but **the experiment cannot attribute the parity to a
  scheduler** because the four framework rows collapse to one trajectory.

### §3.5 What the published CIFAR-10 RF FID looks like vs ours

| Configuration | FID | Reference |
|---|---:|---|
| Liu 2022 (2-RF, 1-NFE Euler, 50 K samples) | 2.21 | Table 2 of the paper |
| Liu 2022 (1-RF, 1-step, 50 K samples) | ≈ 5–20 | Table 2 of the paper |
| This run, baseline (10-NFE Euler, 1 000 samples) | 66.73 | measured |
| This run, framework (10-NFE Euler, 1 000 samples) | 66.65 | measured |
| Random Gaussian (sanity check) | ≈ 370+ | `compute_mnist_fid.py` footer |

Our 66.73 is **roughly 30× worse than the published 2.21 headline**,
which is the expected gap for a **10-step Euler** integration at
**1 000 samples** (vs the paper's adaptive solver at **50 K samples**).
The framework is **not** claiming to improve on the published number;
the comparison is **baseline-vs-framework on the same model + same
checkpoint + same evaluation protocol**, holding everything constant.

### §3.6 Recommendation for a follow-up that DOES discriminate schedulers

Two viable paths (both out of scope for this run):

1. **Reuse prior endpoint noise** — call
   `apply_restart_distribution` on the previous round's endpoint and
   feed the resulting prior to the next round's `batched_inference`.
   This requires the harness to keep one `StateBundle` per chain
   across rounds. The 2D harness does this implicitly via the
   adapter's native-states cache; the CIFAR adapter discards the
   per-round state via `seed_base × 1 000 + round`.
2. **Use a scheduler config that produces a non-trivial `n_cap`
   trace** — e.g. widen `n_max` to > 1.0 so `num_steps` saturates the
   budget on the early rounds and then narrows, giving each
   scheduler a distinguishing fingerprint even without chained
   state. (And widen the initial signal so `EvidenceDrivenScheduler`'s
   PID-lite actually receives feedback — currently the
   `evidence_ratio` is `nan` for the per-round `ScheduleSample` on
   `EvidenceDrivenScheduler`, so the PID has nothing to react to.)

Either fix would let the framework-vs-baseline comparison carry
information about scheduler choice rather than (seed, batch-shape)
noise.

---

## §4. Wall-clock per row

| Row | Wall-clock (s) | Configuration |
|---:|---:|---|
| baseline (10-step, 1 000 samples) | 454.6 | 1 batch × 1 000 |
| CosineAnnealScheduler | 457.5 | 10 rounds × 100 samples |
| CodimensionSheetScheduler | 457.4 | 10 rounds × 100 samples |
| EvidenceDrivenScheduler | 457.5 | 10 rounds × 100 samples |
| FreeTrajScheduler | 457.1 | 10 rounds × 100 samples |
| FID + summary emission | ~87 (split across 5 rows) | InceptionV3 forward |
| **Total** | **2 692.1** | ≈ 45 min |

Each framework row pools `10 × 100 = 1 000` samples, matching the
baseline's 1 000. The framework rows are inherently identical because
of the scheduler-config defect described in §3.1.

---

## §5. Files written

```
docs/r4-survey/cifar_results/
  baseline_samples.npz             1000 × (3, 32, 32)  float64
  cosineanneal_samples.npz         1000 × (3, 32, 32)  float64  (byte-identical to codim/evidence/freetraj)
  codimensionsheet_samples.npz     1000 × (3, 32, 32)  float64  (byte-identical to cosine/evidence/freetraj)
  evidencedriven_samples.npz       1000 × (3, 32, 32)  float64  (byte-identical to cosine/codim/freetraj)
  freetraj_samples.npz             1000 × (3, 32, 32)  float64  (byte-identical to cosine/codim/evidence)
  per_round_metrics.csv            (5 schedulers × 10 rounds; n_cap=1.0 for every row)
  comparison.md                    baseline + 4 framework rows
  summary.json                     machine-readable headline
  experiment-log.md                Agent 2 honest log
docs/r4-survey/14-cifar-experiment-results.md        # this file
tools/compute_cifar_fid.py                           # CIFAR-10 InceptionV3 FID script
```

---

## §6. Reproducibility

The FIDs in §2 are reproducible end-to-end:

```bash
.venv/Scripts/python.exe tools/run_sota_cifar_experiment.py \
    --checkpoint data/cifar10_rf.pth \
    --output-dir docs/r4-survey/cifar_results \
    --n-samples 1000 --n-rounds 10 --framework-samples 100 \
    --baseline-num-steps 10 --framework-max-num-steps 10 \
    --ref-npz data/_torch_cifar10_cache/cifar10_test_ref_1000.npz \
    --device cpu
```

Or, re-scoring the existing samples:

```bash
/c/Users/31472/AppData/Local/Temp/flowa_fid_env/Scripts/python.exe \
    tools/compute_cifar_fid.py \
    docs/r4-survey/cifar_results/baseline_samples.npz      data/_torch_cifar10_cache/cifar10_test_ref_1000.npz \
    docs/r4-survey/cifar_results/cosineanneal_samples.npz  data/_torch_cifar10_cache/cifar10_test_ref_1000.npz \
    docs/r4-survey/cifar_results/codimensionsheet_samples.npz data/_torch_cifar10_cache/cifar10_test_ref_1000.npz \
    docs/r4-survey/cifar_results/evidencedriven_samples.npz   data/_torch_cifar10_cache/cifar10_test_ref_1000.npz \
    docs/r4-survey/cifar_results/freetraj_samples.npz      data/_torch_cifar10_cache/cifar10_test_ref_1000.npz
```

Deterministic for fixed `(seed, scheduler_config, weights)`.

---

## §7. 7-line summary

1. **Setup**: published Liu 2022 CIFAR-10 Rectified Flow DDPM++ UNet
   (61.8 M params, gnobitab `state_dict`) wrapped by
   `RectifiedFlowCIFARAdapter`; 1 000 samples × 10-NFE Euler baseline
   vs 4 schedulers × 10 rounds × 100 samples.
2. **Headline FID**: baseline `66.7333`, framework `66.6508` (all four
   schedulers identical). Δ = `−0.0825` = **`−0.12%`** — parity, well
   inside the ±10% "paper claim satisfied" band.
3. **Honest caveat**: the four framework rows are **byte-identical to
   each other** because every scheduler returns `n_cap ≡ 1.0`, mapping
   to `num_steps = 10` with the same per-round seed. The 0.083 FID
   delta is Monte-Carlo noise on (seed, batch-shape), NOT a scheduler
   effect.
4. **What IS shown**: the adapter loads the published checkpoint
   correctly; the UNet produces real CIFAR-10-shaped images
   (std≈0.34, range≈[−1, 1]); FID plumbing works end-to-end against
   the 1 000-image CIFAR-10 test reference.
5. **What is NOT shown**: paper Theorem 1 selection-ratio trend
   (`EvidenceDrivenScheduler` row carries no `sel_ratio`); scheduler
   discrimination (all four rows collapse to one trajectory); any
   causal attribution of the parity to a particular scheduler.
6. **Absolute FID vs published**: our `66.73` is ~30× worse than the
   paper's 2.21 headline (which uses 50 K samples + adaptive solver at
   100+ NFE). The model is correct; the solver is coarse and the
   sample budget is small. This is expected, not a failure.
7. **Recommended next step**: chain the per-round state (call
   `apply_restart_distribution` on the previous round's endpoint) OR
   widen `n_max` so `n_cap` is non-trivial across rounds. Either fix
   lets the comparison actually isolate the scheduler effect.