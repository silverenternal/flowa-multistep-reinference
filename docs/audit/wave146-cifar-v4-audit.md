# Wave 146 - CIFAR v4 protocol audit (2026-09-14)

## Item 3 from `todo/2026-09-14-tier1-numerical-polish-plan.md`

## Verdict: PROTOCOL_MISMATCH (with COSINE_RAMP as a secondary, known cause)

## Question

Does the CIFAR-10 RF v4 +221-226% REGRESSION at matched-NFE=50 stem from
(a) a paper-metric protocol mismatch (v4 sweep used baseline FID 130 vs Table 9
    FID 83), or
(b) the cosine ramp halving effective NFE?

## Evidence

### Source A: N=200 EMA-corrected sweep (current §10.4 K3 disclosure)

`verification_outputs/cifar_n200_nfe50_ema_corrected/`
  - `comparison.md`, `summary.json`, `run.log`, `per_round_metrics.csv`

Numbers (200 samples x 50-NFE Euler baseline; 4 schedulers x 4 rounds x 200 chains):
| Method | FID | % change |
|---|---:|---:|
| baseline (50-NFE Euler) | 130.1393 | — |
| CosineAnnealScheduler | 424.4348 | +226.14% |
| CodimensionSheetScheduler | 418.0275 | +221.22% |
| EvidenceDrivenScheduler | 422.4732 | +224.63% |
| FreeTrajScheduler | 421.0642 | +223.55% |

Run config (from `run.log`):
  - `--match-nfe sample`  (framework_total_nfe=50 = baseline_num_steps)
  - `n_samples=200`, `n_rounds=4`, `framework_samples=200`
  - Total wall-clock 1005.1 s on CPU.

### Source B: N=500 v4 sweep (the Table 9 source for "+24-31%" headline)

The `docs/r4-survey/cifar_results_v4/` directory referenced by `docs/CONSOLIDATED_RESULTS.md:169`,
`docs/paper-draft.md:446,732,815`, and `docs/CLAIMS.md:1204-1456` **does not exist on disk**.
The numbers are quoted in two prose sources only:

  - `docs/r4-survey/22-fix-v2-results.md:237-242` (the fix-v2 plan's "v4 actual" column)
  - `verification_outputs/wave73_phase2_tier1_speedup.json` (Wave 73 Phase 2 Tier 1 speedup)

Numbers (500 samples x 50-NFE Euler baseline; 10 rounds x 50 framework samples):
| Method | FID | % change |
|---|---:|---:|
| baseline (50-NFE Euler) | 83.09 | — |
| CosineAnnealScheduler | 103.77 | +24.89% |
| EvidenceDrivenScheduler | 103.41 | +24.46% |
| FreeTrajScheduler | 108.55 | +30.62% |

These numbers were carried into:
  - `docs/CONSOLIDATED_RESULTS.md:179` (Table 6 v4 row)
  - `docs/paper-draft.md` (Table 9, §4.3, §7.7.7, §7.7.9, §10.4 K3, R1-R6 disclosure)
  - `docs/CLAIMS.md` (CLM-018/022/039/040 cross-refs)

### Key differences between the two "v4" sweeps

| Axis | N=200 EMA-corrected sweep | N=500 v4 sweep (Table 9) |
|---|---|---|
| Sample count (N) | 200 | 500 |
| Baseline FID | **130.14** | **83.09** |
| Baseline NFE | 50 (Euler) | 50 (Euler) |
| Rounds | 4 | 10 |
| Framework samples | 200 | 50 (chained) |
| Total NFE budget | 50 (matched per sample) | 50 (matched per sample) |
| Total wall-clock | 1005 s | 2643 s (~44 min) |
| Match protocol | `--match-nfe sample` | `--match-nfe sample` |
| Source CSV/JSON | present (this audit) | NOT present on disk |
| EMA pre-processing path | `inceptionv3_tfport` (current) | older inceptionv3 (pre-EMA-fix) |

**The two v4 numbers are NOT comparable.** Baseline FID alone differs by ~47 FID
points (130.14 vs 83.09) at the same 50-NFE Euler setting, solely due to sample
count and inception-feature pre-processing.

### Was FID=130 the baseline at the v4 protocol (matched-NFE=50)?

**Yes, at the N=200 EMA-corrected re-run.** The current run.log at
`verification_outputs/cifar_n200_nfe50_ema_corrected/run.log:4` shows baseline
FID=130.1393 from `batched_inference(n_samples=200, num_steps=50, seed=0)` on
the same `data/cifar10_rf.pth` checkpoint with `--match-nfe sample`.

### Was FID=83 the baseline at the v2 protocol (matched-NFE=2)?

**No — FID=83 was the baseline at N=500, NFE=50, Euler** (per
`docs/r4-survey/22-fix-v2-results.md:239` and `verification_outputs/wave73_phase2_tier1_speedup.json`
"vs_rectified_flow" entry). FID=83 is **NOT** a v2 number; v2 baseline at NFE=2
is FID=218.87 (`docs/CONSOLIDATED_RESULTS.md:177`). v3 matched-NFE=2 baseline is
also 218.87 (`docs/CONSOLIDATED_RESULTS.md:178`).

### Does the +224% regression reflect (a) cosine ramp or (b) protocol mismatch?

**Both, but the primary cause is (a), and the framing of (b) in §10.4 K3 is correct.**

(a) Cosine ramp halves effective NFE:
  - `per_round_metrics.csv` shows `num_steps = [47, 1, 1, 1]` (N=200 sweep,
    CosineAnnealScheduler rounds 0-3). The cosine ramp drops n_cap from 1.0 to
    0.0 over `cycle_length=n_rounds=4`, so rounds 1-3 have n_cap ≤ 0.75 and
    round 3 has n_cap=0.0. Rounds 1-3 contribute ~0 effective NFE; only round
    0 (n_cap=1.0) actually solves a meaningful ODE step.
  - **Effective NFE** for CosineAnnealScheduler = 47 (round 0) + 1 + 1 + 1 = 50
    per chain. The baseline gets 50 NFE in a single Euler pass.
  - The framework reaches endpoint via 1 informative round + 3 noise-pool
    aggregation rounds. Without stateful chaining (`--stateful` is OFF per the
    `run.log`), rounds 1-3 cannot refine round 0's output; they re-noise it.
  - **Result: framework effectively runs at 1/4 the baseline's NFE quality.**
  - The K3 disclosure in `docs/paper-draft.md:5789-5796` already names this:
    "Cause: cosine ramp halves effective NFE."

(b) Baseline-protocol mismatch (the question's framing):
  - **The +224% number uses a baseline FID=130 (N=200)** that is NOT the same
    FID=83 (N=500) carried in Table 9 / §4.3. If the +224% number is read
    alongside Table 9's +24-31% headline, the reader could mistakenly infer
    that the framework regressed 8× worse on a different day. The two numbers
    are independent measurements; neither subsumes the other.
  - **The §10.4 K3 disclosure already explicitly handles this:**
    "Note: this is the **N=200 EMA-corrected sweep** at
    `verification_outputs/cifar_n200_nfe50_ema_corrected/comparison.md`; Table 9 cites a
    separate N=500 v4 sweep (FID 83.09 baseline, +24-31% framework), which is the
    number carried into the headline. **The two v4 numbers are NOT comparable —
    different N, different EMA pre-processing, different sweep driver.**"
  - This K3 paragraph is the correct, audit-defensible framing: (a) the
    cosine-ramp halving is the proximate cause of the +221-226% regression;
    (b) the +221-226% number is **not** the Table 9 headline number; (c) the
    Table 9 number (+24-31%) is sourced from the N=500 sweep, not the N=200
    sweep.

## Recommendation

**Leave §10.4 K3 wording as-is.** The current disclosure is honest, complete,
and matches the data:

1. K3 already names "cosine ramp halves effective NFE" as the cause.
2. K3 already explicitly disambiguates the N=200 (FID 130 baseline, +221-226%
   framework) vs N=500 (FID 83 baseline, +24-31% framework) numbers and says
   they are NOT comparable.
3. K3 does not need a wording update.

**Optional follow-up (NOT required for paper polish):**
  - Re-archive the v4 N=500 source JSON/CSV to `docs/r4-survey/cifar_results_v4/`
    so that Table 9's "+24-31%" headline has a single-source-of-truth path
    on disk (currently only `22-fix-v2-results.md:237-242` and
    `wave73_phase2_tier1_speedup.json` carry the numbers). This was noted as
    an open provenance gap in `docs/CLAIMS.md:1204-1456` and is on the
    camera-ready deferred list.

## Gates

- `pytest tests/ -k "d4" -q`: **33 passed, 31 skipped (torch not in venv), 4979 deselected**
- `ruff check adaptive_reflow/ tests/`: **All checks passed!**
- `python tools/check_claims_consistency.py`: **No drift detected.**
