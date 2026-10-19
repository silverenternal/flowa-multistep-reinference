# GAP-43 — Blend-positive run record (R3 `fg_dev`, 50 seeds)

**Status:** COMPLETE — verdict `INCONCLUSIVE` on the primary `fg_dev` endpoint;
`pb_validity` is a decisive win.
**Pre-registration:** `docs/audit/gap43-blend-positive-preregistration.md`
(blob `ae3be8ac47227dd581310ad31abe69dd3d31cca1`).
**Analysis script:** `tools/gap43_blend_positive_analysis.py`
**Metadata recorder:** `tools/gap43_run_metadata.py`
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

| Item | Value |
|---|---|
| Cell | R3, FlowMol3 `fg_dev` (lower is better) |
| Framework arm | `--real-restart-blend --restart-memory-fraction 0.5` |
| Pairing | `--shared-prior` |
| Primary | 50 seeds (55, 65, …, 545), N=1000/arm, NFE=250 matched |
| Tuned gate | 10 seeds (55, …, 145), baseline NFE=1000, best-of per seed |
| Decision rule | POSITIVE / MATCHED-NFE-POSITIVE-NOT-ROBUST / BOUNDED NEGATIVE / INCONCLUSIVE |
| Verdict | **`INCONCLUSIVE`** — mean negative but n.s.; tuned gate fails |
| `fg_dev` primary | mean Δ = **−0.01921** (31/50 seeds), SD 0.0882, t(49) = −1.540, **p = 0.1301** (α = 0.00714), `d_z = −0.218` |
| `fg_dev` 95 % CI | **[−0.0542, +0.0158]** — includes 0 |
| Tuned gate | mean Δ_tuned = **+0.03418** (framework *worse*), 3/10 seeds pass → **fails** |
| `pb_validity` exploratory | mean Δ = **+0.21165**, **50/50 seeds**, p = 3.9 × 10⁻²⁶, **`d_z = +2.967`** |
| Flagged seeds | 0 |

---

## 1. Prerequisites (pre-registration §9)

### 1.1 Combined-path smoke (`--shared-prior --real-restart-blend`)

Never run together before this increment. `N=100`, seeds 55 and 65, both
arms, `cuda:0`, `.venvs/flowmol3_venv`.

| Check | Result |
|---|---|
| No exception | ✅ exit 0 |
| `n_sampled > 0` | ✅ 100 / 98 / 99 / 100 |
| Non-degenerate `fg_dev` | ✅ 0.9587 / 1.0038 (seed 55), 1.0487 / 1.4355 (seed 65) |
| `shared_prior = true` | ✅ recorded in `flowmol3_n1000_sweep_wave338_p5_seed{55,65}.json` |
| `real_restart_blend = true` | ✅ same file |
| `restart_memory_fraction = 0.5` | ✅ same file |

**Reading caveat (honest):** the per-arm JSONs do not carry the three
provenance flags; the sweep JSON does. The smoke's `fg_dev` levels
(~0.96–1.05 at N=100) are **not** comparable to the N=1000 numbers
(~0.56–0.61): the `fg_dev` estimator is strongly N-dependent. The smoke is
a wiring check only, not an effect estimate.

Artifacts: `verification_outputs/gap43-blend-positive/_smoke/`.

### 1.2 Determinism

Seed 55, `N=100`, rerun into `_smoke_determinism/`. Every metric key except
`wallclock_s` is **identical** for both arms (`baseline identical`,
`framework identical`).

### 1.3 Analysis script + CPU tests

`tools/gap43_blend_positive_analysis.py` implements §5/§7 verbatim
(paired t, d_z, 10k percentile bootstrap with `rng(0)`, best-of tuned gate,
flagged-seed sensitivity, leave-one-out, exploratory `pb_validity_pct`).
`tests/test_gap43_analysis.py`: 7 passed. `--self-test`: OK.

### 1.4 Run metadata

`tools/gap43_run_metadata.py` writes `run_metadata.json` into each run
directory: git SHA, git cleanliness, pre-registration blob hash, exact
command, seed list, Python/torch/CUDA/flowmol/PoseBusters/RDKit versions,
checkpoint md5, PoseBusters YAML sha256, GPU name/driver, start/end UTC.

### 1.5 GPU idle

_Recorded at launch._

---

## 2. Commands (as run)

```bash
# primary — 50 seeds x N=1000/arm, NFE=250 matched, cuda:0
CUDA_VISIBLE_DEVICES=0 PYTHONPATH="$PWD" .venvs/flowmol3_venv/bin/python \
  scripts/wave338_p5_r3_n1000_paired.py \
  --n-total 1000 --nfe 250 --nfe-batch 100 \
  --seeds $(seq 55 10 545) \
  --shared-prior --real-restart-blend --restart-memory-fraction 0.5 \
  --device cuda:0 --output-dir verification_outputs/gap43-blend-positive/primary

# tuned gate — 10 seeds, baseline NFE=1000 (best-of vs framework NFE=250)
CUDA_VISIBLE_DEVICES=0 PYTHONPATH="$PWD" .venvs/flowmol3_venv/bin/python \
  scripts/wave338_p5_r3_n1000_paired.py \
  --n-total 1000 --nfe 250 --nfe-batch 100 \
  --seeds $(seq 55 10 145) --baseline-nfe 1000 \
  --shared-prior --real-restart-blend --restart-memory-fraction 0.5 \
  --device cuda:0 --output-dir verification_outputs/gap43-blend-positive/tuned_baseline

# analysis (frozen rule)
.venvs/flowmol3_venv/bin/python tools/gap43_blend_positive_analysis.py \
  --primary-dir verification_outputs/gap43-blend-positive/primary \
  --tuned-dir verification_outputs/gap43-blend-positive/tuned_baseline \
  --out verification_outputs/gap43-blend-positive/summary.json
```

Wall-clock: primary 2026-10-18T17:39Z → 2026-10-19T00:06Z (6 h 27 m);
tuned gate 00:06Z → 02:47Z (2 h 41 m); analysis 10:47Z.

---

## 3. Results

### 3.1 Primary endpoint — R3 `fg_dev` (lower is better)

| quantity | value |
|---|---:|
| seeds | 50 |
| mean Δ (fw − bl) | **−0.01921** |
| SD | 0.08820 |
| SE | 0.01247 |
| t(49) | −1.540 |
| p (α = 0.0071429) | **0.13008** |
| `d_z` | −0.218 |
| `d_z` 95 % bootstrap CI | [−0.512, +0.058] |
| mean 95 % CI | [−0.05423, +0.01582] |
| seeds with Δ < 0 | **31 / 50** |
| median | −0.01210 |
| 10 % trimmed mean | −0.01680 |

Direction is consistently framework-favourable (31/50, negative mean, negative
median, negative trimmed mean), but the effect is small and the CI crosses 0.

### 3.2 Tuned-baseline gate

The pre-registered gate compares the framework at NFE=250 against the
**best of** baseline@250 and baseline@1000 per seed.

| quantity | value |
|---|---:|
| seeds | 10 |
| mean Δ_tuned | **+0.03418** |
| seeds where framework wins | **3 / 10** |
| gate passes | **False** |
| framework deterministic on subset | True |

So at matched *quality target*, a baseline given 4× the NFE beats the framework
on 7/10 seeds. The framework's `fg_dev` gain is not a compute-efficiency win.

### 3.3 Exploratory endpoint — K1 `pb_validity_pct` (higher is better)

| quantity | value |
|---|---:|
| seeds | 50 |
| mean Δ | **+0.21165** |
| SD | 0.07134 |
| t(49) | 20.979 |
| p | **3.94 × 10⁻²⁶** |
| `d_z` | **+2.967** |
| `d_z` 95 % bootstrap CI | [+2.537, +3.642] |
| seeds with Δ > 0 | **50 / 50** |
| mean 95 % CI | [+0.1833, +0.2400] |

This is not a marginal result: every one of 50 seeds favours the framework, and
the effect size is ~3 SD of the paired difference.

### 3.4 Robustness

- **Leave-one-out:** mean Δ range [−0.02481, −0.01338]; `d_z` range
  [−0.312, −0.170]. No single seed drives the primary result.
- **Flagged seeds:** 0 (no seed met the pre-registered run-validity flag).
- **Validity:** saturated at 1.0 in both arms, so it carries no signal.
- **`ood_ring_rate`:** no pre-registered direction; recorded per seed in
  `summary.json`.

---

## 4. Interpretation

**Observed.** On the frozen decision rule the primary endpoint is **not
significant** (p = 0.130 vs α = 0.00714) and the tuned-baseline gate **fails**
(3/10). The verdict is therefore `INCONCLUSIVE`, not `POSITIVE`. On the
exploratory `pb_validity` endpoint the framework wins on **50/50 seeds** with
`d_z = +2.97`.

**Inferred.** The two endpoints measure different things. `fg_dev` is a
distributional geometry deviation; `pb_validity` is chemical plausibility under
PoseBusters. The faithful all-channel restart-blend improves the latter
decisively while leaving the former a small, non-significant improvement. The
tuned gate says the `fg_dev` gain can be bought more cheaply by giving the
baseline more NFE, so the framework is **not** a `fg_dev` compute-efficiency
win at this checkpoint.

**Not claimed.** This run does not make R3 `fg_dev` a supported cell, and it
does not promote K1 by wording. K1 `pb_validity` is a large, fully consistent
effect at n=50 but was pre-registered as exploratory; promoting it requires a
separate pre-registration with `pb_validity` as the primary endpoint.

**Mechanism caveat (load-bearing).** The arm tested here is the *as-wired*
blend. Its `charge` channel is linearly mixed and then rounded to the upstream's
6-class categorical representation, which collapses the charge prior toward
neutral (std 1.0 → 0.707 at m=0.5; P(neutral class) 38 % → 52 %). GAP-52 tests
whether fixing that channel changes the `fg_dev` verdict.

---

## 5. Verification

| Gate | Result |
|---|---|
| `tools/gap43_blend_positive_analysis.py --self-test` | OK |
| `pytest tests/test_gap43_analysis.py -q` | 7 passed |
| Pre-registration blob | `ae3be8ac47227dd581310ad31abe69dd3d31cca1` |
| `run_metadata.json` in both dirs | present (git SHA, command, versions, md5) |
| Flagged seeds | 0 |
| Framework determinism on tuned subset | True |
| Frozen surfaces | untouched |
| Vendored upstream | untouched |

---

## 6. Unresolved / noted

- The host is shared: at launch the 32-core load average was ~85–100 from
  other projects. Wall-clock is therefore not usable as a compute measure;
  the pre-registered test is metric-based and unaffected.
- `pb_validity` was pre-registered as exploratory and is not adjusted for
  multiplicity. The effect is large enough that this is unlikely to matter,
  but a confirmatory run with `pb_validity` as the primary endpoint is the
  clean way to claim it.
- The tuned gate uses baseline NFE=1000 vs framework NFE=250, so it is a
  *quality-at-higher-budget* comparison, not a compute-matched one. Its role
  is to reject "the framework's gain is just a budget effect"; it does.
- The charge-channel representation mismatch is documented in GAP-52.
