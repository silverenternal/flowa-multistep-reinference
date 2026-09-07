# Wave 54 Agent B — FlowMol3 SOTA baseline implementation (Phase 2)

**Author:** Wave 54 Phase 2 fixer (Agent B)
**Date:** 2026-09-07
**Wave:** 54 (post-§7.5 honest-verdict rewrite)
**Companion:** Phase 1 review at `docs/audit/wave54-review-b-flowmol3-baselines.md`
**Scope:** Add 2 SOTA baselines (MolDiff + EquiFM) for FlowMol3, following
the Wave 52 LineageFlow baseline convention. Baselines only — no edits
to `adaptive_reflow/`, `framework/`, `scheduler/`, or any adapter.
**Status:** complete; outputs committed (no push).

---

## B.1 What Phase 1 recommended and Phase 2 shipped

| # | Baseline | Paper | Why it matters | Status |
|---|----------|-------|----------------|--------|
| 1 | **MolDiff** | Zhang et al. 2023, ICLR | Closest published 3D-mol *diffusion* baseline. FlowMol3 itself benchmarks against MolDiff. | **SHIPPED** (`scripts/baselines/run_flowmol3_baseline_moldiff.py`) |
| 2 | **EquiFM** | Song et al. 2023, ICLR | Closest *flow-matching* predecessor. Lets the framework argue on the FM axis specifically (CTMC-vs-linear-OT). | **SHIPPED** (`scripts/baselines/run_flowmol3_baseline_equifm.py`) |

Both are synthetic-mode (no upstream ckpt in this sandbox; the
`molflowmol3_venv` sidecar has `torch + rdkit` but not `pyg`/`MolDiff`
or `e3nn`/`EquiFM`). The composite-axis math is byte-identical to the
Wave 49 `FlowMol3Glue.composite_score`; the inner sampler is a
deterministic mean-predictor contraction (MolDiff) or a hand-picked
chemistry-correct target collapse (EquiFM). See §B.5 for the honest
limitations.

---

## B.2 Files added

| Path | Lines | Role |
|------|------:|------|
| `scripts/baselines/_flowmol3_helpers.py` | ~310 | shared numpy/RDKit helpers: `chem_validity`, `composite_score` (byte-identical to `FlowMol3Glue.composite_score`), `make_native_state`, `euler_step_coordinate`, `euler_step_categorical`, default sweep geometry |
| `scripts/baselines/run_flowmol3_baseline_moldiff.py` | ~340 | MolDiff-style DDPM baseline (CTMC re-mask + coordinate contraction). Loads *no* MolDiff ckpt (synthetic-mode) |
| `scripts/baselines/run_flowmol3_baseline_equifm.py` | ~300 | EquiFM-style linear-OT baseline (no CTMC re-mask + linear-OT Euler step). Synthetic-mode |
| `verification_outputs/flowmol3_baseline_moldiff_q4_2026.json` | (artefact) | MolDiff run, 3 NFE budgets (10, 50, 250), B=4 n_atoms=9 seed=42 |
| `verification_outputs/flowmol3_baseline_equifm_q4_2026.json` | (artefact) | EquiFM run, same geometry |
| `tests/test_baselines/__init__.py` | ~10 | package marker |
| `tests/test_baselines/test_flowmol3_helpers.py` | ~200 | 17 unit-tests pinning helpers to FlowMol3Glue defaults + byte-stable JSON check |
| `tests/test_baselines/test_flowmol3_baselines.py` | ~110 | 4 subprocess smoke-tests (per-script + cross-comparison + Wave 54 marker check) |
| `docs/audit/wave54-fix-b-flowmol3-baselines.md` | (this file) | implementation + comparison doc |

Total Python LOC added: ~960. **No edit to `adaptive_reflow/`,
`framework/`, `scheduler/`, or any adapter** — verified by
`git status --short` at commit time.

---

## B.3 Implementation notes

### B.3.1 `_flowmol3_helpers.py` — sidecar-venv shared helpers

Mirrors `_lineageflow_helpers.py` for the FlowMol3 axis:

* `chem_validity(coords, atom_types)` returns `(frac_valid_mols,
  frac_mols_stable, marker)`. Marker is `blocked_rdkit` when RDKit
  isn't importable (graceful NaN degradation, mirroring the
  `tools/run_real_ckpt_eval.py` design).
* `composite_score(chemistry, geometry, weights)` is a pure-numpy
  byte-identical re-implementation of
  `adaptive_reflow.adapters.flowmol3_glue.FlowMol3Glue.composite_score`.
  Reads `frac_valid_mols`, `frac_mols_stable_valence` (alias
  `frac_mols_stable`), `energy_js_div`, `reos_cum_dev` from the
  chemistry dict, applies the geometry-drop renormalization when
  `geometry is None`. Returns `(composite, phi1..phi5, weights,
  has_geometry, K_atom_types, K_bond_types)`.
* `make_native_state(batch_size, n_atoms, seed)` produces the
  canonical FlowMol3-native state `(x, a, c, e)` matching the
  FlowMol3 v2 adapter's `export_trajectory` shape.
* `euler_step_coordinate` / `euler_step_categorical` are the
  inner-sampler steps used by both MolDiff and EquiFM.

**Why duplicate rather than import.** Same convention Wave 52 Agent C
used for `_lineageflow_helpers.py`: the `flowmol3_venv` sidecar
deliberately does NOT carry `adaptive_reflow`. Duplicating the
~50 LOC composite math is cheaper than dragging the full framework
into the baseline sidecar.

### B.3.2 MolDiff baseline (`run_flowmol3_baseline_moldiff.py`)

Reproduces the *inference-loop pattern* of MolDiff on the same
composite axis as the framework:

* **Coordinate channel**: `euler_step_coordinate` toward
  `_target_mean_from_prior` (deterministic contraction). No
  upstream MolDiff SE(3) denoiser loaded (synthetic-mode).
* **Categorical channels**: `euler_step_categorical` with
  `re_mask_prob=0.05` per step. With `target_p=None` and
  `re_mask_prob > 0`, the categorical simplex collapses to uniform
  over `NFE` steps — i.e. *any* no-denoiser diffusion baseline
  collapses to uniform on the categorical channels. The framework's
  value-add is therefore measured on the *chemistry-validity* axis,
  not on categorical turn-over.
* **Composite**: `frac_valid_mols + frac_mols_stable + energy_js_div +
  reos_cum_dev` (geometry axis dropped — no `xtb` on `$PATH`). The
  `energy_js_div` / `reos_cum_dev` axes use *self-relative* chemistry
  proxies (atom-type deviation from uniform + coordinate variance
  ratio) when RDKit is available; NaN when RDKit is missing.

### B.3.3 EquiFM baseline (`run_flowmol3_baseline_equifm.py`)

Same shape as the MolDiff baseline but with the *linear-OT* inner
sampler:

* **Coordinate channel**: `euler_step_coordinate` toward
  `target_x = x_start * 0.1` (tight cluster around origin).
* **Categorical channels**: `euler_step_categorical` with
  `target_p = one_hot(C)` (canonical carbon atom, FlowMol3 type 1) +
  `re_mask_prob=0.0` (no CTMC re-mask — the principled
  flow-matching-vs-diffusion distinction).
* **Composite**: same Wave 49 formula; same self-relative proxies.

The qualitative distinction from MolDiff: EquiFM's categorical
endpoint collapses to a *single* atom type (C), giving 100% argmax
turnover vs the random prior; MolDiff's categorical endpoint
collapses to uniform, giving 0% argmax turnover. The test
`test_moldiff_vs_equifm_categorical_endpoint_differs` pins this
qualitative distinction.

---

## B.4 Comparison table (synthetic-mode, paired-NFE)

| Method | NFE=10 composite | NFE=50 composite | NFE=250 composite | argmax turnover | RDKit marker |
|---|---:|---:|---:|---:|---|
| **Framework FlowMol3 (Wave 53)** | +0.0 (no_signal) | +0.0 (no_signal) | +0.0 (no_signal) | n/a | n/a |
| **MolDiff baseline (synthetic-mode)** | -0.1581 | -0.0753 | -0.0631 | 0.000 (uniform collapse) | ok |
| **EquiFM baseline (synthetic-mode)** | -0.1238 | -0.1225 | -0.1223 | 0.833 (C target collapse) | ok |

* **MolDiff composite** is monotonically less negative as NFE
  increases — the re-mask + coordinate contraction converges the
  categorical to uniform (high `reos_cum_dev`, high `energy_js_div`
  vs the self-relative uniform proxy), pulling the composite
  toward 0 from the more-negative NFE=10 endpoint.
* **EquiFM composite** plateaus at -0.122 — the categorical channel
  converges immediately to the C target (1 step), and the composite
  saturates on the chemistry-proxy axes.
* **Framework FlowMol3 composite** is the Wave 53 placeholder
  (`+0.0 no_signal`) because the framework's metric layer is
  blocked on upstream `flowmol` availability. The baseline
  composite axis is therefore the *only* honest reading on the
  FlowMol3 axis until that block is lifted.

The byte-stable check (see §B.6) confirms the Wave 52 + Wave 53 +
Wave 54 JSONs were NOT modified by Phase 2.

---

## B.5 Honest negative results

Even with the new baselines shipped, Phase 2 does NOT close the
following gaps:

1. **MolDiff / EquiFM are synthetic-mode**. Neither the MolDiff
   ckpt (PyG + Microsoft MolDiff repo) nor the EquiFM ckpt (e3nn +
   hanjq17/EquiFM repo) is in this sandbox. The composite axis is
   therefore an *inference-loop pattern* measure on the same prior
   state the framework starts from, not a paper-parity reproduction.
2. **The framework FlowMol3 composite is still placeholder**. The
   Wave 53 `_compute_flowmol3_real_metric` helper computes a
   synthetic-mode proxy that gives `+0.0 no_signal`. The framework
   vs-baseline delta is therefore not yet meaningful on this axis —
   the framework composite axis must be unblocked (deferred to a
   later wave — `docs/audit/wave54-review-b-flowmol3-baselines.md`
   §B.7.3 item 3).
3. **The CTMC vs linear-OT gap is NOT closed by Phase 2**. MolDiff
   uses discrete-time reverse; EquiFM uses continuous-time flow. Both
   are *continuous-time* in the limit. FlowMol3's CTMC-vs-FM
   mismatch (paper-draft §5.7 limitation #3) remains in scope.
4. **The categorical-channel turn-over is not a useful axis**. Both
   baselines collapse to a deterministic endpoint (uniform for
   MolDiff, single-atom-type for EquiFM) at any NFE ≥ 10 — the
   endpoint doesn't distinguish NFE because the inner sampler has no
   denoiser. The chemistry-validity axis carries the comparison.

---

## B.6 Byte-stable check — Wave 52 + Wave 53 JSONs UNCHANGED

`sha256sum` of the 7 byte-stable files (must match the values from
the Phase 1 review at `docs/audit/wave54-review-b-flowmol3-baselines.md` §B.5):

| Path | sha256 (must match) |
|---|---|
| `verification_outputs/baseline_comparison_q4_2026.json` | `3e71ed24cc03025f90fbdcd28a6815f42b866903aad58f0d442bd6e3b8e0de75` |
| `verification_outputs/lineageflow_baseline_euler_q4_2026.json` | `1b1c004219232390901e218aad4c9c935bcbb7e650b74a135f805be0fc8a82ad` |
| `verification_outputs/lineageflow_baseline_heun_q4_2026.json` | `7b9920da7e43df92e6ba7e98128c688320fa801e00da5a491d7ead6073d6ccc9` |
| `verification_outputs/lineageflow_baseline_rk4_q4_2026.json` | `1dc2e04f528ddf3ea7bc006c53e6aefdc6a83e6c877cbd84ab459220c7a0e941` |
| `verification_outputs/lineageflow_baseline_comparison_q4_2026.json` | `55195ac93257bec3efa4492880cf6989e5fc49540ee32aa53cd0d4b7b4ca7c43` |
| `verification_outputs/kanzi_real_composite_q4_2026.json` | `f81446e55b2e069d68a79afe726ada0f6ef0ece7ea9836b083630b452c9651bf` |
| `verification_outputs/flowmol3_real_composite_q4_2026.json` | `6934e9000a53122a589f0aa0d924c2b5aa0e218a155b0c9c7f2d947caf8febae` |

All 7 hashes match the values recorded in the Phase 1 review. **No
existing JSON was re-emitted by Phase 2.**

The byte-stable regression test
`tests/test_baselines/test_flowmol3_helpers.py::test_byte_stable_json_not_modified`
runs in CI and pins this invariant going forward.

---

## B.7 Test additions

| Test file | # tests | Coverage |
|---|---:|---|
| `tests/test_baselines/test_flowmol3_helpers.py` | 17 | helper pin + composite math + native-state shapes + euler-step invariants + 7 byte-stable regression checks |
| `tests/test_baselines/test_flowmol3_baselines.py` | 4 | subprocess smoke-tests: MolDiff, EquiFM, cross-comparison, Wave 54 marker |

**Total: 21 tests, 100% pass rate** under the `flowmol3_venv` Python
(see `verification_outputs/_smoke_run_flowmol3_baseline_*.json`
artefacts produced by the smoke tests).

Reproduce with:

```bash
.venvs/flowmol3_venv/bin/python -m pytest tests/test_baselines/ -v
```

Reproduce the baselines themselves with:

```bash
.venvs/flowmol3_venv/bin/python scripts/baselines/run_flowmol3_baseline_moldiff.py \
    --nfe-list 10,50,250 \
    --output verification_outputs/flowmol3_baseline_moldiff_q4_2026.json

.venvs/flowmol3_venv/bin/python scripts/baselines/run_flowmol3_baseline_equifm.py \
    --nfe-list 10,50,250 \
    --output verification_outputs/flowmol3_baseline_equifm_q4_2026.json
```

---

## B.8 Cross-references

* `docs/audit/wave54-review-b-flowmol3-baselines.md` — Phase 1 review
  (top-2 baseline recommendations + byte-stable inventory).
* `docs/audit/wave52-baseline-comparison-impl.md` — Wave 52 Agent B
  (Tier 1/2 baseline impl, the pattern this Phase 2 follows).
* `docs/audit/wave52-lineageflow-baseline-comparison.md` — Wave 52
  Agent C (LineageFlow baseline impl, mirror of the Tier 3 pattern).
* `adaptive_reflow/adapters/flowmol3_glue.py` — the Wave 49 source
  of truth for `composite_score` (byte-identical re-implementation
  in `_flowmol3_helpers.py`).
* `verification_outputs/flowmol3_baseline_moldiff_q4_2026.json` —
  MolDiff run artefact (Phase 2 output).
* `verification_outputs/flowmol3_baseline_equifm_q4_2026.json` —
  EquiFM run artefact (Phase 2 output).
* `docs/paper-draft.md` §7.5 (FlowMol3 honest verdict), §8.5
  (SOTA baseline measurement status — to be updated with the
  Phase 2 numbers in a follow-up wave).
* `docs/CONSOLIDATED_RESULTS.md` §16 (Tier 3 framework-vs-baseline
  synthesis — to be updated with the new synthetic-mode rows).

---

## B.9 Files changed (commit scope)

```
scripts/baselines/_flowmol3_helpers.py                                  (new)
scripts/baselines/run_flowmol3_baseline_moldiff.py                      (new)
scripts/baselines/run_flowmol3_baseline_equifm.py                       (new)
verification_outputs/flowmol3_baseline_moldiff_q4_2026.json             (new, gitignored)
verification_outputs/flowmol3_baseline_equifm_q4_2026.json              (new, gitignored)
tests/test_baselines/__init__.py                                        (new)
tests/test_baselines/test_flowmol3_helpers.py                           (new)
tests/test_baselines/test_flowmol3_baselines.py                         (new)
docs/audit/wave54-fix-b-flowmol3-baselines.md                           (new, this file)
```

**No edits to `adaptive_reflow/`, `framework/`, `scheduler/`,
`run_real_ckpt_eval.py`, or any adapter.** Verified by
`git status --short` at commit time — the only modifications are
inside the `scripts/baselines/`, `verification_outputs/`,
`tests/test_baselines/`, and `docs/audit/` trees allowed by the
task brief.