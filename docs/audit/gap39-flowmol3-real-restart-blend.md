# GAP-39 — wiring the real FlowMol3 restart-blend into the R3/K1 framework arm

**Date:** 2026-10-15
**Author:** GAP-39 agent (USER AUTHORIZED, NO PUSH)
**Base commit:** `ecd7edd3` (GAP-38 shared-prior spread)
**Scope:** the user directive — *"前面的 gap 修复的不够彻底 … 要扭转这些差一点点
的指标只需要改几处关键代码"*, and the user's explicit selection of the
**FlowMol3 real-restart-blend wiring** lever from the dormant-lever menu.
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

| Item | Result |
|---|---|
| Defect class | the canonical R3/K1 framework arm never calls the adapter's real `apply_restart_distribution`; it uses a **coordinate-only single-shot Gaussian proxy** (`x += N(0, 0.05)`) |
| Fix (additive, default off) | `--real-restart-blend` on `scripts/wave338_p5_r3_n1000_paired.py`; the framework arm builds the real prior via `apply_restart_distribution` (all three channels) |
| Harness | `tools/run_sota_flowmol3_v2_adapter_experiment.py` gains `--restart-blend`; the stale "size-mismatch bug" comment (bug fixed at `flowmol3_v2_adapter.py:1299`) is corrected |
| Bounded A/B (N=200, 3 seeds) | legacy fg_dev Δ = **+0.0859** (framework *worse*, `d_z=+1.19`); real blend Δ = **+0.0011** (neutral, `d_z=+0.02`) — the blend **removes the regression** but does not produce a framework win at this N |
| Canonical A/B (N=1000, 3 seeds) | **K1 `pb_validity`**: effect size jumps `d_z +0.65 → +0.92` (large; 3/3 seeds framework-favourable). **R3 `fg_dev`**: mean improves (`−0.0377 → −0.0548`) but SD grows, so `d_z −0.401 → −0.359` — **not** flipped |
| Net | The faithful mechanism is a real, load-bearing correction that makes **K1 a large-effect cell**; it does **not** flip R3. Additive, default-off; no frozen surface moved. |

---

## 1. The defect and where it lived

The R3/K1 headline cell is FlowMol3 `fg_dev` / RDKit-`pb_validity`. Its canonical
driver is `scripts/wave338_p5_r3_n1000_paired.py` (3 seeds × N=1000). The
framework arm is **not** the FlowA restart-blend — it is a proxy:

```python
# scripts/wave338_p5_r3_n1000_paired.py  (_framework_perturb_prior)
x_perturbed = x_canonical + sigma * Normal(0, 1)      # sigma = 0.05, coordinate channel ONLY
# c_perturbed = c_canonical   (charges are categorical; left alone)
# a_perturbed = a_canonical   (atom types are categorical; left alone)
# e_perturbed = e_canonical   (bonds are categorical; left alone)
```

So the "framework" arm perturbs **one** channel (coordinates) with an additive
Gaussian and solves **once**. The FlowA restart-blend
(`FlowMol3V2Adapter.apply_restart_distribution`, `flowmol3_v2_adapter.py:2167`)
blends **all three** channels (coordinate + charge + raw_pair) with a fresh draw
via `_channel_aware_blend` — and it was **never called by any headline driver**.

A second copy of the same gap lived in the SOTA harness
`tools/run_sota_flowmol3_v2_adapter_experiment.py:615-627`, where the inner loop
explicitly skipped `apply_restart_distribution` because of a *known size-mismatch
bug* — but that bug was **already patched** (Wave 30 Agent B,
`flowmol3_v2_adapter.py:1299`), so the comment was stale.

## 2. The fix (additive, default off)

### 2.1 Canonical R3/K1 driver — `scripts/wave338_p5_r3_n1000_paired.py`

New helpers `_make_real_restart_policy` + `_apply_real_restart_blend`, and a new
`--real-restart-blend` flag (default **off**). When on, the framework arm builds
its prior through the adapter's real blend:

```python
bundle = _build_canonical_prior(adapter, batch_id)
if real_restart_blend:
    bundle = _apply_real_restart_blend(adapter, bundle, memory_fraction=m, seed=seed)
elif perturbation_sigma > 0.0:
    _framework_perturb_prior(adapter, bundle, perturbation_sigma=..., seed=seed)
```

`_apply_real_restart_blend` builds a `FinalRestartPolicy` with
`beta_by_channel = 1 - memory_fraction` on all three FlowMol3 channels and calls
`adapter.apply_restart_distribution(bundle, policy)`. The returned bundle carries
the blended native state, which the subsequent `solve_ode(..., n_molecules=...)`
tiles across the batch — a genuine **prior-side** all-channel restart-blend
rather than a coordinate-only perturbation. `--restart-memory-fraction`
(default `0.5`) is the single knob.

### 2.2 SOTA harness — `tools/run_sota_flowmol3_v2_adapter_experiment.py`

`--restart-blend` (default off) wires `apply_restart_distribution(endpoint, policy)`
into the per-sample multi-round loop (all three channels); the stale size-mismatch
comment is replaced with the GAP-39 note. `restart_blend` is recorded in
`summary.json`.

**Byte-stability.** With the new flags absent, both drivers emit the exact legacy
behaviour. Verified: `pytest tests/test_d4_regression_vectors.py
tests/test_adapters/test_regression_vectors.py -q` → **72 passed**.

## 3. Harness export-path finding (why the harness cannot measure R3/K1)

The harness `--restart-blend` A/B was attempted first at N=64, 3 rounds,
NFE=250 (cuda:0). Both arms produced **all-`None` molecules** (64/64 in each
arm), so `run_mol_eval` reports `validity=0.0` and the upstream paper metrics
are `not_requested` (`no_valid_input_smiles`). This is the pre-existing
partial-fidelity export ceiling documented in
`docs/r17-survey/mol-comparison.md` §9.4 (GPU run: `validity=0.0/0.0`), **not**
a GAP-39 regression — the baseline arm (no blend) is equally affected. The
harness therefore cannot produce a paper-metric R3/K1 reading; the canonical
driver (which exports via `export_sampled_molecules`) is the right surface.

## 4. Bounded A/B on the canonical R3/K1 driver

**Protocol.** `scripts/wave338_p5_r3_n1000_paired.py`, FlowMol3 `last.ckpt`,
NFE=250, `nfe_batch=100`, seeds 42/43/44, cuda:0. Legacy = `--real-restart-blend`
absent; blend = `--real-restart-blend --restart-memory-fraction 0.5`.
Evidence: `verification_outputs/gap39-flowmol3-real-restart-blend/`.

### 4.1 N=200 (2 batches/arm) — regime check

`fg_dev` (lower is better); paired Δ = framework − baseline.

| mode | seed 42 | seed 43 | seed 44 | mean | SD | `d_z` |
|---|---:|---:|---:|---:|---:|---:|
| legacy (x-only proxy) | +0.1195 | +0.1356 | +0.0027 | **+0.0859** | 0.0726 | **+1.185** |
| real restart-blend | +0.0729 | −0.0482 | −0.0216 | **+0.0011** | 0.0636 | **+0.017** |

At N=200 the legacy proxy makes the framework arm **worse** on `fg_dev`
(`d_z=+1.19`); the real all-channel blend **removes that regression** (mean
`+0.0011`, `d_z=+0.02`) and flips 2/3 seeds to framework-favoured. `pb_validity`
moves only slightly (framework still ≥ baseline in every seed).

**Regime caveat (important).** The N=200 subset uses batches 0–1 only; the
canonical cell uses batches 0–9. The two are **different regimes**: at N=1000
the committed legacy result is framework-**better** (`mean=−0.0377`,
`d_z=−0.401`), the *opposite* sign to N=200 legacy (`+0.0859`). N=200 is
therefore a directional probe, not a substitute for the canonical N=1000 read.

### 4.2 N=1000 (canonical, 10 batches/arm)

**Protocol.** `scripts/wave338_p5_r3_n1000_paired.py --n-total 1000 --seeds 42 43 44`
(the exact canonical R3/K1 config). Run on physical GPU 1
(`CUDA_VISIBLE_DEVICES=1`, `--device cuda:0`) because GPU 0 was saturated by an
unrelated user job during the run. The **legacy arm reproduces the committed
`r3_n1000_3seed_fixed_q4_2026` numbers bit-for-bit** (`+0.05003, −0.13674,
−0.02636` vs committed `+0.05, −0.1367, −0.0264`), confirming the result is
device-invariant and that the comparison against the committed canonical is
valid.

**R3 `fg_dev`** (lower is better; paired Δ = framework − baseline):

| mode | seed 42 | seed 43 | seed 44 | mean | SD | `d_z` | `p` |
|---|---:|---:|---:|---:|---:|---:|---:|
| legacy (x-only proxy) | +0.05003 | −0.13674 | −0.02636 | **−0.03769** | 0.09390 | **−0.401** | 0.559 |
| real restart-blend | −0.04789 | −0.21070 | +0.09432 | **−0.05476** | 0.15262 | **−0.359** | 0.598 |

The blend **flips seed 42** (+0.050 → −0.048) and **deepens seed 43**
(−0.137 → −0.211), but **flips seed 44 the other way** (−0.026 → +0.094). Net:
the mean moves further in the framework-favourable direction but the cross-seed
SD grows (0.094 → 0.153), so the effect size is essentially unchanged
(`d_z −0.401 → −0.359`). **R3 is not flipped.**

**K1 `pb_validity_pct`** (higher is better):

| mode | seed 42 | seed 43 | seed 44 | mean | SD | `d_z` | `p` |
|---|---:|---:|---:|---:|---:|---:|---:|
| legacy | +0.0204 | −0.0003 | +0.2356 | **+0.0852** | 0.13064 | **+0.652** | 0.376 |
| real restart-blend | +0.0162 | +0.0948 | +0.3118 | **+0.1410** | 0.15313 | **+0.921** | 0.252 |

This is the GAP-39 headline: under the **faithful** all-channel restart-blend the
framework's `pb_validity` advantage is **3/3 seeds framework-favourable** (legacy
had seed 43 at ≈ 0) and the effect size crosses the `|d_z| ≥ 0.8` "large" line
(`+0.652 → +0.921`). `validity_pct` is saturated at 1.0/1.0 in every arm, so K1's
signal is carried entirely by `pb_validity`.

(Computed from the persisted per-seed `paired_diff` values; the driver's own
`_paired_summary` reports the `fg_dev` numbers in the JSON.)

## 5. Interpretation — observed vs inferred

**Observed.** (a) The canonical R3/K1 framework arm did not call the adapter's
real restart-blend; it used a coordinate-only Gaussian proxy. (b) Wiring the real
all-channel blend (additive, default off) changes the paired deltas materially:
at N=200 the legacy framework *regression* on `fg_dev` (`+0.0859`, `d_z=+1.19`)
collapses to neutral (`+0.0011`, `d_z=+0.02`); at the canonical N=1000 the K1
`pb_validity` effect size rises from `d_z=+0.65` to `d_z=+0.92` (3/3 seeds
framework-favourable) while R3 `fg_dev` stays a near-miss (`d_z −0.401 →
−0.359`). (c) The harness cannot measure R3/K1 (all-`None` export).

**Inferred.** The coordinate-only proxy is **not** the framework's mechanism: it
under-perturbs the discrete channels and, on `fg_dev`, mis-signs the effect at
N=200. The faithful all-channel blend is closer to the framework's actual
behaviour and, on the K1 `pb_validity` axis, turns a medium effect into a large
one. On `fg_dev` the blend trades a smaller mean shift for a larger cross-seed
variance, leaving the effect size flat.

**Unresolved.** R3 `fg_dev` remains n.s. at n=3 under both mechanisms (needs
~7–11 seeds per GAP-37's power table); K1 `pb_validity` is now a large effect but
still n.s. at n=3 (`p=0.252`).

## 6. What this means for the "flip the weak metrics" directive

The user's hypothesis — *a few key code lines flip the near-miss cells* — is
**half-confirmed**. The "few key lines" are real: the canonical R3/K1 framework
arm was running a **proxy**, not the framework's restart-blend, and wiring the
real `apply_restart_distribution` (additive, default-off) is a genuine,
load-bearing correction.

- **K1 `pb_validity` — improved to a large effect.** `d_z +0.65 → +0.92`
  (3/3 seeds framework-favourable). The cell is still n.s. at n=3, but it now
  clears the `|d_z| ≥ 0.8` large-effect bar under the *faithful* mechanism, and
  the legacy seed-43 tie disappears. This is the strongest positive result of the
  dormant-lever programme.
- **R3 `fg_dev` — not flipped.** The blend improves the mean but not the effect
  size (`d_z −0.401 → −0.359`); the cell remains a near-miss.
- **Honest limit.** Neither cell becomes significant at n=3; a definitive R3/K1
  verdict needs more seeds (a compute decision, per GAP-37). The fix corrects the
  *mechanism*, it does not manufacture significance.

**Recommendation.** Adopt `--real-restart-blend` for any future canonical R3/K1
re-run (it is the faithful mechanism and it strengthens K1). Record K1 as a
large-effect-but-underpowered cell; do **not** promote it to `SUPPORTED` by
wording. No frozen surface was moved.

---

**Cross-references**

- GAP-37 / GAP-38 (shared-prior design fix): `docs/audit/gap37-statistical-power.md`,
  `docs/audit/gap38-shared-prior-thorough.md`
- GAP-32 head-to-head (R3 x-channel restart-blend loses): `docs/audit/gap32-headtohead.md`
- Harness export ceiling: `docs/r17-survey/mol-comparison.md` §9.4
- Evidence: `verification_outputs/gap39-flowmol3-real-restart-blend/`
