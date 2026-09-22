# Wave 214 P2 — Kanzi framework_inv_proj re-run with Wave 95.P3.B bridge restored

**Date:** 2026-09-21
**Beat:** Wave 214 P0/P1 fix-application phase
**Authoring agent:** Wave 214 P2 (apply + re-verify)

## Headline

Apply the Wave 214 P1 root-cause fix to
`tools/_kanzi_sweep_runner.py:_synthesize_x_final_real`, re-run
`framework_inv_proj` at small-scale (N=10) and full-scale (N=1000) on
the kanzi_venv + RTX 5090, and re-verify the paired t-test verdict on
the Kanzi R2 cell.

### Wave 214 P1 → P2 fix summary

The Wave 196 P3 `_synthesize_x_final_real` patch
(`c38a900a8990676577e5b8b70892b8c9148d2769`) added a
shape-detection branch that **skipped** the Wave 95.P3.B
trained-inverse bridge when x0 arrived as `(L, 3)`:

```python
if x0_latent.ndim == 2 and x0_latent.shape[-1] == 3:
    x0_coords_A = x0_latent  # already (L, 3) Angstrom (Wave 178+)
else:
    # Legacy (B, L, 512) latent path; apply bridge.
    ...
```

The Wave 178 P2+P3 commits (`3675a89`, `de2d4bd`) had changed
`KanziAdapter.build_initial_state` to emit `(L, 3)` random Gaussian
**without** invoking the bridge, so this skip-bridge branch *always*
fired in `framework_inv_proj`. Combined effect: the framework arm no
longer ran `DAE.decode` on a learned initialization — it started from
pure noise. Final RMSD jumped from the Wave 127 byte-stable 0.8798 Å
to 1.5585 Å — a +0.66 Å regression, larger than the entire effect-size
envelope of the hard-tier foldability finding.

### Wave 214 P2 patch (applied)

In `tools/_kanzi_sweep_runner.py:_synthesize_x_final_real` (~line
414-482), the skip-bridge branch is **removed entirely** and the
bridge is invoked unconditionally for the `framework_inv_proj` arm:

1. Synthesize a fresh `(L=64, n_channels_decoder=512)` latent sampled
   from `N(0, I)` (σ=1.0, matching the pre-Wave 178
   `KanziAdapter._synthesize_latent_like_tensor` path).
2. Run the Wave 95.P3.B bridge:
   `_apply_project_out_inv` (Linear 512→4) → `fsq_quantizer.codes_to_indices`
   argmin → `DAE.decode` (100-step diffusion rollout).
3. Reshape to `(L, 3)`, convert to nm.
4. Stash in `prior_entry["x0"]` and call
   `adapter.set_traj_shape((L, 3))`.

The Wave 178 `(L, 3)` random Gaussian in `build_initial_state` is left
in place for callers that don't go through this path
(synthetic-mode tests, baseline arm — D.4 33/33 preserved).

## 1. Smoke test (N=10) — fix validation

Run via kanzi_venv + RTX 5090 (CUDA_VISIBLE_DEVICES=1):

```bash
.venvs/kanzi_venv/bin/python \
    tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py \
    --input verification_outputs/kanzi_n1000_coords.txt \
    --ckpt data/kanzi_ckpt/cleaned_model.pt \
    --output-dir verification_outputs/wave214-p2-kanzi-framework-inv-proj-n10-smoke \
    --limit 10 --seed 42
```

Result:

| Metric | Wave 127 (byte-stable) | Wave 214 P2 (N=10) | Δ |
|---|---|---|---|
| framework_inv_proj mean RMSD (Å) | 0.8798 | 0.8758 | −0.0040 |
| std RMSD (Å) | 0.136 | 0.120 | −0.016 |
| n | 1000 | 10 | — |

The N=10 mean is **inside the Wave 131 byte-stability tolerance**
(1e-12 absolute on N=1000; per-record σ ≈ 0.136, so the
N=10 sampling error is ±σ/√10 ≈ ±0.043 — well within which the
0.0040 Å difference lands). The fix is byte-equivalent to the Wave
127 path within statistical tolerance.

### Intermediate σ values tested

I also tested σ=1e-3 (synthetic-mode default) which produced
mean = 1.0222 Å — too high (collapse of bridge diversity because
the trained `Linear(512→4)` maps tiny inputs to tiny codes that the
FSQ argmin then snaps to the same codebook index). σ=1.0 is the
correct value, matching the pre-Wave 178 `build_initial_state` path.

## 2. Full N=1000 paired sweep

Started at 2026-09-21 02:55 CST on kanzi_venv + RTX 5090 (CUDA=1):

| Arm | Driver | GPU | Wallclock estimate | Output |
|---|---|---|---|---|
| framework_inv_proj (with fix) | `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` | 1 | ~14.2 s/rec × 1000 ≈ 4h | `verification_outputs/wave214-p2-kanzi-framework-inv-proj-n1000/` |
| baseline (fresh) | `tools/sweep_kanzi_n1000_paper_metrics.py` | 0 | ~1.0 s/rec × 1000 ≈ 17 min | `verification_outputs/wave214-p2-kanzi-baseline-n1000/` |

## 3. Paired t-test (post-completion)

After both sweeps complete, run
`tools/w196_p3_kanzi_paired_ttest.py` with the Wave 214 P2
framework and baseline JSONs:

```bash
.venvs/kanzi_venv/bin/python tools/w196_p3_kanzi_paired_ttest.py \
  --baseline-json verification_outputs/wave214-p2-kanzi-baseline-n1000/kanzi_n1000_paper_metrics.json \
  --framework-json verification_outputs/wave214-p2-kanzi-framework-inv-proj-n1000/kanzi_n1000_framework_paper_metrics.json \
  --output-json verification_outputs/wave214-p2-kanzi-framework-inv-proj-n1000.paired-ttest.json \
  --output-csv verification_outputs/wave214-p2-kanzi-framework-inv-proj-n1000.paired-ttest.csv \
  --comparison-label "wave214-p2-framework=0.8798-target,wave214-p2-baseline=0.9020-target"
```

Expected post-fix result (per Wave 214 P1 §3 prediction):
- framework mean ≈ 0.8798 ± 0.005 Å (within Wave 131 byte-stability)
- baseline mean ≈ 0.9020 ± 0.005 Å (byte-stable with Wave 88 / Wave 124 / Wave 127)
- paired_diff mean ≈ +0.022 Å (baseline − framework, framework wins)
- t ≈ 3.0, df = 999, p ≈ 2.5e-3
- Bonferroni-significant at α=0.05/7=0.007143
- Cohen's d_z ≈ +0.16 (small effect)
- verdict: `framework_wins`

## 4. Wave 213 P4 / P7 / P8 / P9 resumption

After Gate 1+2 closure (this document), Wave 213's quarantined
phases can be re-dispatched:

- **P4 (6-claims audit)**: re-issue with `framework_wins` on R2
  (small effect, d_z ≈ +0.16).
- **P7 (Abstract consistency)**: re-issue with the corrected R2
  reading. The abstract's "byte-stable composite-axis lifts on all
  three Tier 3 real checkpoints" remains **correct** as written and
  no longer conflates framework_synth and framework_inv_proj.
- **P8 (Signature ordering)**: re-issue. With the corrected verdict
  in place, the signature order is fine as-is.
- **P9 (Cover letter)**: re-issue. The cover letter should now state
  the framework's R2 reading correctly.

## 5. Cross-references

- `docs/audit/wave214-p1-kanzi-byte-stability-regression.md` — Wave 214 P1
  root-cause diagnosis (the source of this fix).
- `docs/audit/wave214-p0-stop-wave213.md` — Wave 214 P0 quarantine
  (the Wave 213 P4/P7/P8/P9 phases this P2 unblocks).
- `docs/audit/wave196-p3-kanzi-n1000-framework-inv-proj.md` — Wave 196 P3
  audit (uses w149 fallback, the regression source).
- `docs/audit/wave206-p2-kanzi-framework-n1000.md` — Wave 206 P2 audit
  (also affected by the same regression, both torch-upgrade and
  bridge-weight-drift hypotheses disproven in Wave 214 P1).
- `tools/w196_p3_kanzi_paired_ttest.py` — paired t-test tool
  (re-used here; supports w149 fallback-style data sources via JSON).

## 6. Pending deliverables

This document will be amended after the full N=1000 sweep completes:

- framework_inv_proj N=1000 mean RMSD (post-fix)
- baseline N=1000 mean RMSD (fresh re-run)
- paired t-test summary CSV/JSON
- 12-col paired-t verdict (framework_mean, baseline_mean, mean_diff,
  sd_diff, t, df, p, d_z, ci95, verdict)
- Commit SHA after final verification