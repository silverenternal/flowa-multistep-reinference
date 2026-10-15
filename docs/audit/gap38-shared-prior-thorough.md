# GAP-38 — shared-prior fix applied to the remaining arm-keyed drivers (and what it does / does not change)

**Date:** 2026-10-15
**Author:** GAP-38 agent (USER AUTHORIZED, NO PUSH)
**Base commit:** `c6d0a3d2` (GAP-15 additive addendum)
**Scope:** the user's directive — *"前面的 gap 修复的不够彻底，要做进一步的修复 … 要扭转这些差一点点
的指标只需要改几处关键代码"*. GAP-37 found the "few key lines" defect (an
arm-keyed prior that turned the R3 "paired" test into a two-sample test) and
fixed it in **one** driver (`scripts/wave338_p5_r3_n1000_paired.py`). This
increment applies the **same** fix to the **five** other drivers that still
carry the defect, then measures honestly whether it flips the near-miss cells.
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

| Item | Result |
|---|---|
| Defect class | GAP-37's arm-keyed prior (`batch_id` includes the arm/scheduler name → the two arms draw **independent** priors) |
| Fixed in (this increment) | 5 drivers, additive `--shared-prior` flag, **default off = byte-stable** |
| Design defect confirmed? | **Yes** — the shared prior collapses the cross-seed SD of the arm delta (fg_dev **0.359 → 0.131**, 2.75× tighter; pb_validity **0.202 → 0.115**, 1.76× tighter) |
| Does it *flip* the near-miss cells? | **No, not at the tested N.** fg_dev sign flips to framework-favoured but stays n.s. (`d_z = −0.10`); **pb_validity's apparent framework advantage shrinks** (`d_z = +1.35 → +0.28`) — the legacy advantage was partly nuisance-prior noise |
| GraphBFN | **Not testable** — no usable weights (`weights_metadata.json` status `failed`; synthetic-only) |
| Net | The fix corrects the **design** (a real, load-bearing correction) but is **not** a "flip the metric" lever by itself. Recorded observations-only; no frozen surface moved. |

---

## 1. The defect and where it still lived

GAP-37 (`docs/audit/gap37-statistical-power.md`) found that the R3 driver keyed
each batch's prior on the arm name:

```python
batch_id = f"{arm_name}-seed{seed_base}-batch{batch_idx}"   # arm_name in the key
```

Because `build_initial_state` derives every draw from
`SHA-256(batch_id, sample_id, source_round)`, including the arm name makes the
baseline and framework priors **independent draws** — the "paired" test is a
two-sample test in disguise, and its cross-seed variance is dominated by
nuisance prior noise rather than the perturbation effect. GAP-37 added a
`--shared-prior` code path to **one** driver and lifted R3 from `d_z = −0.401`
to `d_z = −1.089`.

The same key pattern survived in five more drivers (grep
`batch_id.*f"` over `scripts/` + `tools/`):

| # | driver | key (legacy) | cell(s) fed |
|---|---|---|---|
| 1 | `tools/wave87_n1000_sweep.py:206` | `f"{arm_name}-batch{i}-seed{seed}"` | canonical K1 / R3 |
| 2 | `tools/run_sota_flowmol3_v2_adapter_experiment.py:464,535` | `f"flowmol3-baseline-{seed}"` / `f"flowmol3-framework-{seed}"` | K1 / R3 (SOTA harness) |
| 3 | `tools/run_sota_graphbfn_experiment.py:256,388` | `f"graphbfn-baseline-{seed}"` / `f"graphbfn-framework-{seed}"` | GraphBFN |
| 4 | `tools/run_sota_cifar_experiment.py:842` | `f"sota-cifar-{scheduler_name}"` | R5b / K3 |
| 5 | `scripts/wave235_p4_flowmol3_3seed.py:82` | `f"w235p4-{arm_name}-s{seed_base}-i{i}"` | R3 (3-seed) |

## 2. The fix (additive, byte-stable)

Each driver gains a `--shared-prior` flag (default **off**). When off, the
legacy key is reproduced **exactly** (byte-stable); when on, the arm/scheduler
name is dropped so both arms build the same canonical prior:

```python
# tools/wave87_n1000_sweep.py (after)
def _make_batch_id(*, arm_name, seed_base, batch_idx, shared_prior):
    if shared_prior:
        return f"seed{seed_base}-batch{batch_idx}"          # arm-independent
    return f"{arm_name}-batch{batch_idx}-seed{seed_base + batch_idx}"  # legacy
```

- `tools/wave87_n1000_sweep.py` — new `_make_batch_id`; `--shared-prior`; `shared_prior` in the output JSON.
- `tools/run_sota_flowmol3_v2_adapter_experiment.py` — `shared_prior` kwarg on `_run_baseline` / `_run_framework`; `--shared-prior`.
- `tools/run_sota_graphbfn_experiment.py` — same shape (framework arm already runs the real `apply_restart_distribution`).
- `tools/run_sota_cifar_experiment.py` — `shared_prior` threaded through `_run_framework` → `_run_framework_state_chains`; drops the **scheduler** name from the key (the CIFAR baseline draws via `batched_inference`, a separate RNG, so this aligns the framework arms across schedulers only — disclosed in the flag help).
- `scripts/wave235_p4_flowmol3_3seed.py` — `--shared-prior`.

**Byte-stability.** With `--shared-prior` absent, every driver emits the exact
legacy key. Verified: `pytest tests/test_d4_regression_vectors.py
tests/test_adapters/test_regression_vectors.py -q` → **72 passed**.

## 3. Bounded A/B on the canonical K1/R3 driver (`wave87`)

Because the fix is a **paired-design** correction, the honest test is the
**cross-seed** behaviour of the arm delta under legacy vs shared prior.

**Protocol:** `tools/wave87_n1000_sweep.py`, FlowMol3 `last.ckpt`, N = 100 per
arm, NFE = 250, `nfe_batch = 100`, seeds 42 / 43 / 44, cuda:0.
Evidence: `verification_outputs/gap38-shared-prior-thorough/`.
*Disclosed deviation:* the canonical wave87 sweep uses `nfe_batch = 1`; this
bounded A/B uses `nfe_batch = 100` (2 batches/run) for tractability. The
pairing mechanism is identical; the absolute magnitudes are not directly
comparable to the canonical headline.

### 3.1 `fg_dev` (lower is better)

| mode | per-seed Δ (fw − base) | mean | SD | `d_z` |
|---|---|---:|---:|---:|
| legacy (arm-keyed) | −0.3579, **+0.5207**, +0.1189 | +0.0939 | **0.3591** | +0.261 |
| shared | −0.0239, +0.1518, −0.1675 | −0.0132 | **0.1306** | −0.101 |

The legacy deltas swing wildly across seeds (−0.36 → +0.52); the shared prior
collapses the SD **2.75×** and flips the mean to framework-favoured. But the
shared `d_z = −0.10` is still far from the `|d_z| ≥ 0.8` "large" line.

### 3.2 `pb_validity_pct` (higher is better)

| mode | per-seed Δ | mean | SD | `d_z` |
|---|---|---:|---:|---:|
| legacy | −0.010, **+0.450**, +0.380 | +0.273 | **0.202** | **+1.351** |
| shared | +0.120, −0.130, +0.106 | +0.032 | **0.115** | +0.279 |

This is the key honest finding: under the **paired** design the framework's
apparent `pb_validity` advantage **shrinks** from `d_z = +1.35` to `d_z = +0.28`.
The legacy "advantage" was substantially a nuisance-prior artifact, not the
perturbation effect. The SD still tightens 1.76×.

## 4. Interpretation — observed vs inferred

**Observed.** (a) The arm-keyed prior is present in 5 more drivers. (b) Under a
shared prior the cross-seed SD of the arm delta collapses (2.75× / 1.76×) —
the GAP-37 defect is real and its fix is a genuine design correction. (c) At
N = 100 / 3 seeds the shared prior does **not** produce a significant framework
win on either `fg_dev` or `pb_validity_pct`.

**Inferred.** The shared-prior fix is a **design** correction (it removes
nuisance variance), **not** a lever that manufactures significance. Where the
legacy arm-keyed test appeared to favour the framework (K1 `pb_validity`,
`d_z = +1.35`), the paired design reveals the effect is much smaller — i.e. the
legacy number was partly an artifact. This is consistent with GAP-37's own
honest limit ("the fix corrects the *design*, it does not manufacture
significance"; R3 stays n.s. at n = 3).

**Unresolved / not tested.**
- The canonical `nfe_batch = 1` protocol was not re-run (bounded A/B only).
- GraphBFN could not be tested (no usable weights).
- The FlowMol3 SOTA and CIFAR drivers were patched but not re-run (the SOTA
  framework arm is the same FlowMol3 model; the CIFAR baseline uses a separate
  RNG path and the metric is set-level FID, where pairing does not move the
  point estimate — cf. the earlier R5c MNIST negative).

## 5. What this means for the "flip the weak metrics" directive

The user's hypothesis was that a few key code changes would *flip* the
near-miss cells. The key code changes are real and are now in place (additive,
default-off, in all 6 drivers). But the measurement says the mechanism is
**variance reduction, not a point-estimate flip**:

- **R3** (already recorded by GAP-37): `d_z = −0.40 → −1.09` — the *design*
  improves; the cell stays n.s. at n = 3.
- **K1** (this increment): the paired design **reduces** the apparent advantage
  (`d_z = +1.35 → +0.28`) — the legacy number was partly noise.
- **R5c MNIST** (prior session): FID is set-level; the shared prior does not
  move it (already recorded as a negative).

**Recommendation (honest):** the `--shared-prior` path should be used for any
*future* canonical re-run (it is the correct design), but it should **not** be
presented as a metric-flipping fix. The near-miss cells remain near-miss under
the corrected design; promoting them would require either more seeds (a
compute decision) or a different mechanism (e.g. the FlowMol3 restart-blend
wiring gap documented in `docs/r17-survey/mol-comparison.md:186`).

---

**Cross-references**

- GAP-37 (the one-driver fix): `docs/audit/gap37-statistical-power.md`
- GAP-32 head-to-head: `docs/audit/gap32-headtohead.md`
- Evidence: `verification_outputs/gap38-shared-prior-thorough/{summary.json, sweep_*.json}`
