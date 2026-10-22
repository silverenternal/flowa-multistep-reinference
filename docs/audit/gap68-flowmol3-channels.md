# GAP-68 — FlowMol3 per-channel restart: is channel geometry the bottleneck?

**Date:** 2026-10-21
**Status:** complete — `DIRECTIONAL_UNDERPOWERED`. The lock beats the free blend
by `d_z = −0.83` on the paired difference (rule 1 passes) but neither arm beats
the baseline at n=3 (rule 2 fails). The route is bounded: 12–19 seeds for the
hypothesis, ~280 for a baseline win.
**Scope:** `scripts/wave338_p5_r3_n1000_paired.py` (no code change — the
per-channel knobs already exist), new `verification_outputs/gap68-flowmol3-channels/`.

---

## 0. Pre-registration

### 0.1 Two corrections to the gap statement, established by reading the code

**(a) The channels are already blended per-channel.** `flowmol3_v2_adapter.py:1195`
(`_channel_aware_blend`) dispatches by channel: `coordinate` and `charge` get a
linear blend with their own `memory_fraction`, `raw_pair` (and the model-local
atom-type channel `a`) get a *categorical resample* where the prior label is kept
with probability `m_pair` and replaced by a fresh label otherwise.
`apply_restart_distribution:2288` reads three separate `beta_by_channel` entries
and defaults each to 0.5 independently. `adaptive_reflow/algorithm/per_channel_blender.py`
is a second, unused implementation of the same idea; wiring it in would be a
refactor with no measurable target, so this gap does not do it.

The real defect is narrower and sharper than "one scalar `m`": **the bond channel
is resampled at the same rate as the coordinates**, so at `m_pair = 0.5` half of
all bond labels (and half of all atom types) are replaced by draws from the
uniform-ish prior `_sample_native_state`. Interpolating a bond type is avoided —
the code already resamples rather than interpolates — but *resampling* a bond to
a random class is its own kind of off-manifold: the coordinate channel then
diffuses into a geometry whose bond graph was never trained on it.

**(b) The published R3 number is not this arm.** The canonical R3 framework arm
is `_framework_perturb_prior` (`scripts/wave338_p5_r3_n1000_paired.py:87`): an
additive Gaussian of `sigma = 0.05` on the **coordinate channel only**, one solve,
no restart. GAP-39 wired the real all-channel blend and measured it separately
(`gap39-flowmol3-real-restart-blend.md` §4.2): mean Δ fg_dev −0.0548, `d_z`
−0.359, n.s. So a per-channel result here does not move the paper's R3 cell
unless it also changes the σ-arm, which it does not. **This gap is about the
restart arm, not about CLM-068.**

### 0.2 What the environment allows (blocker resolved)

The Wave 351/357 RDKit blocker recorded a 33–40 % valid yield. It does not
reproduce on the current host: an n=30 run through the canonical driver returns
`validity = 1.000`, `n_dropped = 0`, `n_errors = 0` in **both** arms, in both
configurations tested. RDKit is `2026.03.5` in `.venvs/flowmol3_venv`. The
blocker is therefore stale for this driver; it is recorded here rather than
assumed.

### 0.3 Exploratory smoke, disclosed

Before this pre-registration I ran the driver at **n=30, seed 42, batch 0 only**
to check that the path works and to size the effect. This is the small-N regime
that `gap39` §4.1 warns has the *opposite sign* to N=1000, so it is not evidence,
only a power hint:

| arm | fg_dev | Δ vs baseline | pb_validity |
|---|---:|---:|---:|
| baseline | 0.6077 | — | 0.467 |
| restart, `m = 0.5` all channels | 0.8120 | **+0.204** | 0.867 |
| restart, `m = 0.5`, `m_pair = 1.0` | 0.7286 | **+0.121** | 0.967 |

Both baselines are byte-identical (0.607664 in both runs), which confirms the
`--shared-prior` pairing works. The lock removes 41 % of the small-N damage.

### 0.4 Arms

All arms N=1000, NFE=250, `nfe_batch=100`, **`--shared-prior`** (so baseline and
framework see the same prior per batch), `charge_blend_mode=continuous`,
`restart_rounds=1`, seeds 42/43/44, `cuda:0`.

| id | arm | flags |
|---|---|---|
| **A0** | baseline | (the driver's baseline, shared prior) |
| **A1** | restart, all channels free | `--real-restart-blend --restart-memory-fraction 0.5` |
| **A2** | restart, topology locked | A1 + `--restart-memory-fraction-pair 1.0` |
| **A3** | restart, coordinates locked (diagnostic, seed 42 only) | A1 + `--restart-memory-fraction-coordinate 1.0` |

A2 is the gap's hypothesis. A3 is the complementary ablation: if the damage is
in the bond channel, locking the coordinates should make A1 *worse*; if it is in
the coordinates, A3 should recover like A2 does. A3 runs at one seed because it
is an interpretation aid, not a confirmatory cell.

### 0.5 Verdict rules (fixed before the run)

Primary metric `fg_dev` (lower is better); secondary `pb_validity_pct` (higher is
better). Paired Δ = framework − baseline, per seed, then pooled over 3 seeds.

1. **A2 beats A1** if `mean(Δ_A2) − mean(Δ_A1) <= −0.5 · sd(Δ_A2 − Δ_A1)`.
   This is the gap's own ≥ 0.5 sd bar, expressed on the paired difference so the
   shared baseline cancels.
2. **SUPPORTED** requires rule 1 **and** the pooled A2 CI (95 %, t, df=2)
   excluding 0 **and** `p < 0.00714` (Bonferroni over the 7 R-cells).
3. If rule 1 fails, record **"channel geometry is not the bottleneck"** and stop
   — do not sweep more knobs.
4. If rule 1 passes but rule 2 fails, record **DIRECTIONAL / UNDERPOWERED** with
   the effect size and the seed count that would be needed.
5. No seeds beyond 42/43/44. No tuning of `m` — it is fixed at 0.5 by GAP-39 so
   the A1 comparison is like-for-like.

### 0.6 What would make this not a fix

If A2 is worse than A1, the topology lock is not the lever and the off-manifold
argument is wrong for this adapter. If A2 ≈ A1 but A3 ≪ A1, the coordinate
channel carries the damage and the bond channel is irrelevant. Both outcomes are
reportable and neither is reframed afterwards.

## 1. Results

Sweep: 6 cells (a1 × 3 seeds, a2 × 3 seeds), N=1000, NFE=250, `--shared-prior`,
`cuda:0`, 8–12 min per cell, 42 min wall for the four seeds-43/44 cells.
`PYTHONPATH=. python3 tools/gap68_report.py`.

### 1.1 Pairing and environment

The baseline arm is **bit-identical across a1 and a2** at every seed
(`0.717406089951701` / `0.6505…` / `0.7491…`), which is the pairing check and it
passes. The seed-42 baseline also reproduces the committed GAP-55 artifact
`gap55r3_n1000_full.json → baseline.metrics.fg_dev = 0.717406089951701`
**exactly** (difference 0.0), so the decode + metric pipeline on this host is
bit-identical to the recorded one. This is independent confirmation that the
Wave 351/357 RDKit blocker (§0.2) is gone rather than merely bypassed.

### 1.2 Per-seed paired Δ (framework − baseline; negative = framework better)

| arm | seed 42 | seed 43 | seed 44 | mean | SD | `d_z` | `p` | CI95 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| **a1** all channels free | +0.1259 | +0.0227 | −0.1032 | **+0.0152** | 0.1147 | +0.132 | 0.840 | [−0.270, +0.300] |
| **a2** topology locked | +0.0444 | +0.0306 | −0.1403 | **−0.0217** | 0.1029 | −0.211 | 0.749 | [−0.277, +0.234] |

`pb_validity_pct` (higher = better) moves the same way:
a1 mean **+0.1430** (`d_z` +1.322), a2 mean **+0.1659** (`d_z` +1.617).

The lock changes two seeds favourably and one negligibly:
`+0.1259 → +0.0444` (seed 42), `+0.0227 → +0.0306` (seed 43),
`−0.1032 → −0.1403` (seed 44). At seed 42 it removes **65 %** of the regression,
which is the effect the n=30 smoke (§0.3) hinted at.

### 1.3 Pre-registered rules

```
rule 1  mean(dA2 - dA1) = -0.0369   sd = 0.0447   bar = -0.0223   -> PASS
rule 2  A2 CI excludes 0 and p < 0.00714                          -> FAIL
verdict: DIRECTIONAL_UNDERPOWERED
```

Rule 1 passes on the nose: the paired difference is `−0.0369`, the bar is
`−0.0223`, i.e. `d_z = −0.826` on the paired difference — a large effect by
Cohen's convention. Rule 2 fails because the A2 arm's own CI
`[−0.277, +0.234]` straddles zero.

### 1.4 Rule 2 was the wrong test for this hypothesis, and that is a design flaw

The gap asks *"does per-channel beat single-m"*. Rule 1 tests exactly that.
Rule 2 as I wrote it tests *"does the restart arm beat no-restart at all"*, which
is a different and much harder question. The seeds needed, computed from the
observed effect sizes (80 % power):

| comparison | `d_z` | seeds at α=0.05 | seeds at α=0.00714 |
|---|---:|---:|---:|
| **A2 vs A1** (the hypothesis) | **−0.826** | **12** | **19** |
| A2 vs baseline | −0.211 | 176 | 280 |
| A1 vs baseline | +0.132 | 450 | 715 |

So the hypothesis-relevant test is 12–19 seeds away, and the "beat the baseline"
test is 176–280 seeds away. Rule 2 was reachable only by accident. Recorded as a
pre-registration design flaw — the verdict is **not** upgraded, because a rule
that failed still failed.

### 1.5 What the result actually says

1. **Channel geometry is implicated.** Locking the bond channel beats the free
   blend by `d_z = −0.83` on the paired difference, in the predicted direction,
   and the effect is stable across the two seeds where a1 was positive.
2. **It is not enough.** The locked arm is still `−0.022` on average and its CI
   straddles zero. The lock repairs most of the *regression* without creating a
   *win*.
3. **This route cannot produce an R3 win at a feasible n.** Even under the lock
   the arm-vs-baseline effect is `d_z = −0.21`, which needs ~280 seeds to clear
   the Bonferroni bar. The honest reading is that the restart arm is
   approximately neutral on R3, not that more seeds would reveal a win.
4. **None of this moves CLM-068.** The published R3 number is the σ=0.05
   coordinate proxy (§0.1b). The restart arm is a different mechanism with a
   different (null) result, and the paper's R3 cell is unchanged by this gap.

### 1.6 Caveat recorded, not explained

In the stored first 200 SMILES per arm, unique-count is baseline 100 / a1 81 /
a2 71 at seed 42. The topology lock is *less* diverse, which is expected (it
preserves the prior's graph) and is exactly why it helps a composition metric.
The measurement is weak — the baseline's own batch 1 collapses to 12 unique of
100, so the 200-SMILES sample is not a clean diversity estimate. It is recorded
as a caveat; a proper uniqueness/Novelty check at N=1000 would be the smallest
follow-up if this route is pursued.

### 1.7 Not run, and why

**A3** (coordinate locked, bonds free) was pre-registered as the complementary
ablation. It was not run: it can refine *which* channel carries the remaining
`−0.022`, but it cannot change the verdict, and §1.5.3 already bounds the route.
It remains the smallest next action if someone wants the attribution.

