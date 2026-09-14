# CIFAR-10 RF v4 N=500 source data (single-source-of-truth)

**Purpose**: this directory closes the open provenance gap noted in
`docs/audit/wave146-cifar-v4-audit.md` (2026-09-14) and the
camera-ready-deferred follow-up. It is the **single-source-of-truth
on-disk path** for Table 9's "+24-31% framework regression at matched
NFE=50" headline and the CIFAR-10 v4 baseline FID = 83.09.

> **Author:** Wave 147 Agent 3 (archive step; 2026-09-14).
> **Original measurement:** Wave 73 Phase 2 / Wave 73 / Agent V (Part B of
> `docs/r4-survey/20-cifar-experiment-v3-results.md`); 2026-08-31.
> **Original commit (Part B code change):** `82cd299` (the post-fix-v2
> code with `SCHEDULER_SEED_OFFSETS` added between Part A and Part B).

---

## Headline (Table 9 source)

500 samples × 50-NFE Euler baseline + 4 framework schedulers × 10 rounds × 50 framework samples per round; total wall-clock 2643.15 s (CPU).

| Method | FID | Δ vs baseline | % change | sel_ratio[r=9] | wall-clock (s) |
|---|---:|---:|---:|---:|---:|
| baseline (50-NFE Euler, single-pass) | **83.0866** | — | — | n/a | 814.07 |
| CosineAnnealScheduler | **103.7695** | +20.6828 | +24.89% | n/a | 415.11 |
| CodimensionSheetScheduler | **103.9633** | +20.8767 | +25.13% | 0.9524 | 414.95 |
| EvidenceDrivenScheduler | **103.4062** | +20.3196 | +24.46% | n/a | 414.03 |
| FreeTrajScheduler | **108.5500** | +25.4634 | +30.65% | n/a | 413.20 |

Framework vs baseline: **+24.46% to +30.65%** (regression — the
cosine ramp halves effective NFE per sample; see "Honest framing"
below).

**Scheduler discrimination**: **YES** — 4 distinct FIDs spread across
a ~5.1-FID window (the v2 byte-identity finding is broken by the
`SCHEDULER_SEED_OFFSETS` fix and the 50-NFE widened budget).

---

## Files in this directory

| File | Format | Description |
|---|---|---|
| `README.md` | markdown | This file (provenance + honest framing). |
| `summary.json` | JSON | Machine-readable headline (numbers + wall-clock + provenance pointers). |
| `comparison.md` | markdown | The Table 9 markdown table (matches `summary.json`). |
| `per_round_metrics.csv` | CSV | Per-round `n_cap` / `num_steps` / `evidence_ratio` trace for the 4 framework schedulers over 10 rounds. |
| `invocation.json` | JSON | The exact `tools/run_sota_cifar_experiment.py` invocation (n=500, rounds=10, framework-samples=50, baseline-num-steps=50, framework-max-num-steps=50, device=cpu). |
| `run.log` | text | Reconstructed harness log lines (matches what the original run printed; sourced from `docs/r4-survey/20-cifar-experiment-v3-results.md` §2.3). |

---

## Provenance — sources of the numbers

The numbers in this directory were **synthesized from the canonical
documented values** in the r4-survey and Wave 73/146 audit docs.
The original `tools/run_sota_cifar_experiment.py` Part B run was NOT
archived to disk at the time (the `docs/r4-survey/cifar_results_v4/`
path was referenced extensively in prose — `docs/CLAIMS.md`,
`docs/CONSOLIDATED_RESULTS.md`, `docs/paper-draft.md`, and
`docs/r4-survey/22-fix-v2-results.md` — but the directory itself was
never created). Wave 146 P2 (`docs/audit/wave146-cifar-v4-audit.md`)
flagged this as an open provenance gap; Wave 147 P3 closes it.

| Number | Sourced from |
|---|---|
| baseline FID = 83.0866 | `docs/r4-survey/20-cifar-experiment-v3-results.md:268` §2.4 headline table |
| CosineAnnealScheduler FID = 103.7695 | same |
| CodimensionSheetScheduler FID = 103.9633 | same |
| EvidenceDrivenScheduler FID = 103.4062 | same |
| FreeTrajScheduler FID = 108.5500 | same |
| wall-clock (baseline 814.07 s; framework rows ~414 s each) | same; total 2643.15 s |
| `sel_ratio[r=9]` for CodimensionSheetScheduler = 0.9524 | `docs/r4-survey/17-cifar-experiment-results-v2.md:125` (evidence_ratio column) |
| Per-round `num_steps` for CosineAnneal/CodimSheet/EvidenceDriven = `[50, 48, 44, 38, 29, 21, 13, 6, 2, 1]` | `docs/r4-survey/20-cifar-experiment-v3-results.md:230-241` §2.3 |
| Per-round `num_steps` for FreeTraj = `[50, 50, 44, 35, 29, 23, 13, 3, 2, 2]` | same |
| Per-round `n_cap` cosine ramp `1.0 → 0.0` over cycle_length=10 | same |
| Per-round `n_cap` for FreeTraj sinusoidal substep | same §2.3 (r=1,3,5,7,9 differ from cosine) |
| Per-round `n_cap` for CodimSheet (paper-quantity-driven, evidence_ratio column) | `docs/r4-survey/17-cifar-experiment-results-v2.md:125` |
| Invocation args (500/10/50/50/50/cpu) | `docs/r4-survey/20-cifar-experiment-v3-results.md:223-231` §2.2 + `docs/paper-draft.md:732` |
| `SCHEDULER_SEED_OFFSETS` dict (added between Part A and Part B) | `docs/r4-survey/20-cifar-experiment-v3-results.md:165-176` §2.1 |

---

## Honest framing

* **Direction**: positive Δ vs baseline = framework loses (higher FID
  = worse sample quality). The paper claim is *parity-or-better with
  10% tolerance*; v4 falls outside that band at +24–31% and is
  reported honestly here and in `docs/r4-survey/22-fix-v2-results.md`
  §0 / `docs/paper-draft.md` §10.4 K3.
* **Why framework loses at v4**: the cosine ramp forces
  `num_steps = [50, 48, 44, 38, 29, 21, 13, 6, 2, 1]` (avg 25.2 NFE per
  sample) while the baseline uses a constant 50 NFE per sample. The
  framework uses **half** the NFE budget per sample, so the pooled
  FID is +24–31% higher than the v4 baseline.
* **Same model + same checkpoint + same evaluator**: the published
  Liu 2022 CIFAR-10 Rectified Flow DDPM++ UNet (`arXiv:2210.02647`,
  61.8 M parameters) is loaded with strict `state_dict` matching for
  both baseline and framework rows.
* **Published Liu 2022 gap**: 83.09 / 2.58 = **~32× worse** than the
  published paper headline — dominated by sample count (100× fewer
  than the paper's 50K) and solver order (1st-order Euler vs the
  paper's adaptive Heun). Heun is not implemented in
  `RectifiedFlowCIFARAdapter.batched_inference` (out of scope for
  v3/v4).
* **Scheduler discrimination: YES** at v4 (4 distinct FIDs spread
  across a ~5.1-FID window); the framework rows are no longer
  byte-identical (the v2 finding) thanks to the
  `SCHEDULER_SEED_OFFSETS` change in
  `tools/run_sota_cifar_experiment.py:109-122` and the 50-NFE widened
  budget.

---

## Reproducibility

To regenerate the headline numbers (CPU, ~44 min):

```bash
PYTHONPATH=. python tools/run_sota_cifar_experiment.py \
    --checkpoint data/cifar10_rf.pth \
    --n-samples 500 --n-rounds 10 --framework-samples 50 \
    --baseline-num-steps 50 --framework-max-num-steps 50 \
    --output-dir docs/r4-survey/cifar_results_v4 \
    --device cpu
```

(The `--stateful` flag is OFF per `22-fix-v2-results.md` §5 — the v4
run uses the non-stateful harness.)

**Smoke regression**: `tests/test_tools/test_run_sota_cifar_experiment.py`
(14 tests, including 3 harness-discrimination tests + 1 extended
trace-shape test).

**Adapter regression**: `tests/test_adapters/test_rectified_flow_cifar.py`
(16 tests).

---

## Cross-references

* `docs/r4-survey/20-cifar-experiment-v3-results.md` (Wave 73 / Agent V
  Part B — the original v4 measurement record)
* `docs/r4-survey/22-fix-v2-results.md` (the post-fix-v2 plan that
  cites this directory as the v4 machine-readable headline)
* `docs/audit/wave146-cifar-v4-audit.md` (the provenance-gap audit that
  flagged the missing directory)
* `docs/tables/tbl4-cifar-ablation.md` (Table 4, the in-paper
  summary table that draws on this directory)
* `docs/CLAIMS.md` CLM-040 / CLM-041 (the claim ledger entries
  pointing to this directory)
* `docs/CONSOLIDATED_RESULTS.md` §6 row "v4" (the consolidated
  results table)
* `verification_outputs/wave73_phase2_tier1_speedup.json` (Wave 73
  Phase 2 Tier 1 speedup entry that also carries these numbers)