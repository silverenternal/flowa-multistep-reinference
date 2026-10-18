# GAP-43 — Blend-positive run record (R3 `fg_dev`, 50 seeds)

**Status:** RUNNING — pre-registration prerequisites satisfied; sweep in progress.
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
| Verdict | _pending_ |

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

_Pending._

---

## 3. Results

_Pending._

---

## 4. Interpretation

_Pending._

---

## 5. Verification

_Pending._

---

## 6. Unresolved / noted

- The host is shared: at launch the 32-core load average was ~85–100 from
  other projects. Wall-clock is therefore not usable as a compute measure;
  the pre-registered test is metric-based and unaffected.
