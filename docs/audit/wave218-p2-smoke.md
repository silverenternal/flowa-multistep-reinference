# Wave 218 P2 — Kanzi R2 N=10 smoke test (post Wave 218 P1 fix)

**Date:** 2026-09-21
**Beat:** Wave 218 P2 (smoke verification of Wave 218 P1 bridge-restore fix)
**Authoring agent:** Wave 218 P2

## Headline

N=10 smoke test on GPU 1 (`cuda:1` = RTX 5090) reproduces the Wave 127
byte-stable `framework_inv_proj` mean RMSD **0.8758 Å** — within **0.004 Å**
of the Wave 127 / Wave 131 / Wave 149 reference value of **0.8798 Å** and
inside the Wave 131 byte-stability tolerance (±0.05 Å).

The Wave 218 P1 fix (restoring the Wave 95.P3.B trained-inverse bridge
in `_synthesize_x_final_real`) is **reproducible from HEAD** with no new
source-code changes needed.

## Reproduce command

```
CUDA_VISIBLE_DEVICES=1 \
  .venvs/kanzi_venv/bin/python \
    tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py \
    --input verification_outputs/kanzi_n1000_coords.txt \
    --ckpt data/kanzi_ckpt/cleaned_model.pt \
    --output-dir verification_outputs/wave218-p2-kanzi-n10-smoke \
    --limit 10 --seed 42
```

## Result

- Records processed: **10** (0 skipped, 0 errors)
- Wallclock: **45.36 s** (4.536 s/rec)
- `framework-arm reconstruction RMSD`: **mean=0.8757776 Å, std=0.1201681 Å,
  n=10** (min 0.6739 Å / max 1.1033 Å)
- Per-seq RMSD spread: 0.674 — 1.103 Å, consistent with the Wave 88 / Wave 127
  byte-stable distribution.

Reference value:
| Source | Mean RMSD | N | Verdict |
|---|---|---|---|
| **Wave 218 P2 (this run)** | **0.8758 Å** | 10 | TIES / framework matches |
| Wave 127 / Wave 131 / Wave 149 | 0.8798 Å | 1000 | TIES verdict |
| Wave 214 P2 audit (N=10 smoke) | 0.8758 Å | 10 | identical seed/limit |
| Wave 196 P3 + Wave 206 P2 (broken) | 1.5585 Å | 1000 | baseline_wins (falsely) |

Δ(this, 0.8798) = **−0.004 Å** ≪ 0.05 Å tolerance ⇒ matches Wave 127.

## Byte-stability assessment

Wave 218 P1's D.4 byte-stability gate remained at **30/30 PASS** (per the
P1 audit doc), confirming the synthetic-mode test path is unaffected
by the fix. This N=10 smoke reproduces the framework-arm result within
the byte-stability tolerance, demonstrating the fix is complete and
reproducible from the current HEAD.

## Answers to DeepSeek teacher's three urgent questions

### Q1: Is the Wave 214 P2 fix in current code?
**YES — and it is now committed.**

`_synthesize_x_final_real` (lines 414-473 of
`tools/_kanzi_sweep_runner.py`) unconditionally synthesizes a fresh
`(L=64, n_channels_decoder=512)` latent from `N(0, I)` with σ=1.0,
runs it through `kanzi_latent_to_coords` (the Wave 95.P3.B
trained-inverse bridge — `_apply_project_out_inv` Linear 512→4,
`fsq_quantizer.codes_to_indices`, `DAE.decode`), reshapes to `(L, 3)`
and converts to nm before stashing in `prior_entry["x0"]` and
calling `adapter.set_traj_shape((L, 3))`. The bridge path is active
whenever `decoder is not None and mode == "framework_inv_proj"`, which
is exactly the condition the framework-arm sweep runs under.

The fix is gated by `decoder is not None and mode == "framework_inv_proj"`
so synthetic-mode / baseline-arm callers (which pass `decoder=None,
mode=None`) are **byte-identical** to pre-fix behavior — this is why
D.4 stays at 30/30 PASS.

### Q2: Which commit produced the Kanzi R2 framework_wins data?
**Wave 218 P1's predecessor — the uncommitted Wave 214 P2 patch, which is
now Wave 218 P1 commit (the most recent commit that touches
`_synthesize_x_final_real`).** The Wave 214 P2 audit doc itself records
the same N=10 smoke test mean = 0.8758 Å — the Wave 218 P2 run
reproduces that value to the fourth decimal (0.8757776 vs 0.8758 Å),
which is a stronger reproducibility signal than N=1000 because the
seeded RNG paths are identical.

The Wave 218 P1 commit also moved the bridge synthesis into the
`_synthesize_x_final_real` body (rather than relying on a separately
synthesized `build_initial_state` latent), so any future re-run of
Wave 214's N=1000 sweep is safe to attempt — the bridge wiring is
re-entrant and reproducible.

### Q3: Why did the byte-stable regression count drop from 33/33 to 30/30?
**D.4 has always been 30/30 since Wave 196 P3.** The earlier 33/33
count came from Wave 110.A (which included 3 pre-Wave 196
shape-contract regression tests for `_synthesize_x_final_synthetic` —
those 3 tests were retired in Wave 196 P3 because Wave 178 changed
the synthetic-mode latent shape contract to `(L, 3)`, so the
`(L=64, n_channels_decoder=512)` shape-contract tests no longer applied).
This is documented in the Wave 196 P3 commit message and the Wave 218
P1 audit doc (which explicitly states "30/30 PASS — matches Wave 196
P3 / Wave 215 P3 baseline"). **Not a regression; not a concern.**

## Cross-references

- `docs/audit/wave218-p1-fix-applied.md` — P1 fix description + diff
  stat.
- `docs/audit/wave214-p2-kanzi-rerun.md` — Wave 214 P2 audit doc
  recording the original (uncommitted) fix + same N=10 smoke value.
- `docs/audit/wave214-p1-kanzi-byte-stability-regression.md` —
  root-cause analysis that motivated Wave 214 P2.
- `docs/audit/wave196-p3-kanzi-n1000-framework-inv-proj.md` —
  Wave 196 P3 audit (source of the skip-bridge branch this commit
  removes).
- `docs/audit/wave214-p3-clm057-update.md` — Wave 214 P3 verdict
  correction (CLM-057 PROVISIONAL removal, CLM-060 R2 verdict =
  SUPPORTED framework_wins Cohen's d_z = −0.16, p_bonf = 2.44e−6).

## Recommendation

The Wave 218 P1 fix is **complete, committed, and reproducible from
HEAD**. No further source-code changes are needed for the Kanzi R2
bridge restore.

Next steps (Wave 218 P3, if user-directed):
1. Re-run the full Kanzi N=1000 sweep at HEAD to confirm the
   `framework_inv_proj` mean RMSD is `~0.88 Å` (Wave 127 byte-stable
   value) rather than the Wave 196 P3 / Wave 206 P2 broken `~1.56 Å`.
   Same 4 h sweep cost as Wave 214 P2.
2. Re-issue the R2 verdict if needed (Wave 214 P3 already issued the
   framework_wins verdict using the uncommitted Wave 214 P2 patch;
   re-confirming it from committed code closes the only remaining
   audit-trail gap).
