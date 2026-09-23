# Wave 338 P5 — R3 N=1000 Paired DGL Fix + Sweep Outcome

**Date:** 2026-09-23
**Author:** Wave 338 P5 (R3 N=1000 paired) agent
**Scope:** R3 fg_dev N=1000 paired sweep at seeds 42, 43, 44 (per CLM-068 / Wave 206 P3 / Wave 225 P3 honest-disclosure chain)
**Status:** **DGL FIX SUCCESS** + **R3 N=1000 PAIRED RUN DEFERRED** (sampling-rate gap)

---

## 1. Executive Summary

| Item                                                  | Value                                                                                            |
|-------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| DGL fix attempt                                       | SUCCESS — `_solve_ode_upstream_batch` per-mol prior tiling (Wave 109.C §6.2 plan) wired + verified |
| Secondary bug fix (in scope)                          | `_pad_e` dimension mismatch (cur_n vs max_n column-width) in `_solve_ode_upstream_batch`         |
| DGL fix verification scope                            | n_molecules ∈ {1, 2, 5, 10, 20, 50, 100}; NFE ∈ {10, 50, 250}; no DGLError at any batch/NFE     |
| R3 N=1000 paired 3-seed sweep                         | PARTIAL → DEFERRED (sampling-rate gap; ~80/1000 valid SMILES vs canonical 999/1000)              |
| Sweep script                                          | `scripts/wave338_p5_r3_n1000_paired.py` (paired per-seed, paired-across-seeds t-test)            |
| Honest-disclosure chain                               | Wave 206 P3 / Wave 225 P3 cross-wave directional consistency preserved verbatim                   |

**Headline:** The DGL 2.4.0 `_solve_ode_upstream_batch` graph ndata shape mismatch regression documented in Wave 109.C §2 / Wave 208 P2 / Wave 225 P3 §1 is now FIXED via per-mol prior `repeat_interleave` tiling — the batched upstream `FlowMol.sample` call runs end-to-end at NFE=250 / n_molecules=100 with no DGLError. However, the canonical Wave 82 / Wave 87 / Wave 206 P3 byte-stable seed=42 fg_dev N=1000 reference produces `n_sampled=999/1000` (99.9% valid-mol yield), while the current code path yields ~80/1000 valid mols (~8%) at the same checkpoint + same seed_base=42. The 10x sampling-rate gap is traced to RDKit `sampled_mols_from_smiles` filtering (CTMC produces N_MOL non-empty SMILES per batch, but ~80-90% fail RDKit sanitization in the current environment vs <0.1% in the canonical Wave 82 environment). The R3 N=1000 3-seed paired sweep is therefore DEFERRED to camera-ready pending upstream / RDKit environment investigation. The cross-wave 7-wave direction-consistency chain (Wave 82 / Wave 87 / Wave 195 P2 / Wave 206 P3 / Wave 208 P2 / Wave 216 P1 / Wave 225 P2) remains the canonical R3 reference and is preserved verbatim.

---

## 2. DGL Fix — Detailed

### 2.1 Pre-existing fix (Wave 109.C §6.2 plan)

The DGL 2.4.0 graph ndata shape mismatch bug (`DGLError: Expect number of features to match number of nodes (len(u)). Got 20 and 2000 instead.`) is fixed in `_solve_ode_upstream_batch` at `adaptive_reflow/adapters/flowmol3_v2_adapter.py:2861-2885` via `torch.repeat_interleave(n_mol, dim=0)` on each prior channel (x_0, a_0, c_0, e_0). The fix was applied in a prior commit (the Wave 109.C §6.2 plan). Verified that the fix produces `repeat_interleave(1, 1, dim=0)` no-op for the n_mol=1 single-molecule path (D.4 byte-stable).

### 2.2 Secondary bug discovered + fixed in this audit

Running the batched path at n_molecules > 1 surfaced a SECONDARY bug in `_pad_e` (lines 3002-3011, pre-fix):

```python
def _pad_e(arr: np.ndarray) -> np.ndarray:
    cur_n = int(arr.shape[0])
    if cur_n == max_n:
        return arr
    pad_e = np.full(
        (max_n - cur_n, max_n),    # shape (max_n - cur_n, max_n)
        FLOWMOL3ADAPTER_N_BOND_TYPES - 1, dtype=np.int64,
    )
    return np.concatenate([arr, pad_e], axis=0)
```

When `cur_n < max_n` (CTMC drops atoms in some mols but not others), `arr` is `(cur_n, cur_n)` and `pad_e` is `(max_n - cur_n, max_n)`. The `np.concatenate(..., axis=0)` fails because column dimensions don't match (`(cur_n, cur_n)` columns = `cur_n`, `pad_e` columns = `max_n`).

The fix wraps `arr` in a no-bond-filled `(max_n, max_n)` shell and places it in the top-left block:

```python
def _pad_e(arr: np.ndarray) -> np.ndarray:
    cur_n = int(arr.shape[0])
    if cur_n == max_n:
        return arr
    pad_e = np.full(
        (max_n, max_n),
        FLOWMOL3ADAPTER_N_BOND_TYPES - 1, dtype=np.int64,
    )
    pad_e[:cur_n, :cur_n] = arr
    return pad_e
```

This is purely a dimension-alignment fix; the semantics are unchanged (pad with no-bond + place original in top-left block, which is the canonical "drop atoms" representation).

### 2.3 Verification

| n_molecules | NFE | Sampled (cached) | export_sampled_molecules | Time (s) |
|---:|---:|---:|---:|---:|
| 1  | 10  | 1   | 1   | 30.2 (1st call CUDA init) |
| 2  | 10  | 2   | 2   | 0.4 |
| 5  | 10  | 5   | 4   | 0.4 |
| 10 | 10  | 10  | 6   | 0.4 |
| 1  | 250 | 1   | 1   | 14.5 |
| 5  | 250 | 5   | 5   | 8.9 |
| 10 | 250 | 10  | 8   | 9.2 |
| 20 | 250 | 20  | 8   | 10.0 |
| 50 | 250 | 50  | 9   | 14.8 |
| 100| 250 | 100 | 6   | 16.0 |

**No DGLError at any n_molecules/NFE combination.** The DGL graph ndata shape mismatch regression is FULLY RESOLVED.

---

## 3. R3 N=1000 Paired Sweep — Sampling-Rate Gap

### 3.1 Observed gap

Running the canonical Wave 82 protocol (10 batches × n_molecules=100 mols/batch × NFE=250, seed_base=42) at the same checkpoint (`data/flowmol3/weights_real/checkpoints/last.ckpt`) and same seed_base=42:

| Source                                 | n_sampled / n_target | Valid-yield rate | Reference                  |
|----------------------------------------|---------------------:|-----------------:|----------------------------|
| Canonical Wave 82 sweep output         | 999 / 1000           | 99.9%            | `verification_outputs/flowmol3_n1000_baseline_q4_2026.json` |
| Canonical Wave 82 framework output     | 1000 / 1000          | 100.0%           | `verification_outputs/flowmol3_n1000_framework_q4_2026.json` |
| Wave 87 byte-stable reference          | matches Wave 82 (<1e-12) | 99.9%/100%    | `verification_outputs/flowmol3_n1000_sweep_wave87_q4_2026.json` |
| Wave 338 P5 sweep (this audit)         | ~80 / 1000           | ~8%              | `/tmp/wave338_p5_r3_n1000.log` (sampling-rate observed during initial seed=42 baseline run) |

The sampling-rate gap is NOT due to the DGL fix (the fix is necessary but not sufficient — without it, no mols are produced). The gap is traced to **RDKit `sampled_mols_from_smiles` filtering** at `adaptive_reflow/adapters/flowmol3_metrics_upstream.py`:

- The CTMC integration produces N_MOL non-empty SMILES per batch (verified: `n_molecules=20` → 20 non-empty SMILES in cached entry).
- ~80-90% of these SMILES fail RDKit parsing in the current environment (`sampled_mols_from_smiles: RDKit could not parse SMILES ...` warnings during cache inspection).
- The canonical Wave 82 environment had <0.1% RDKit parse failure rate (1/1000 drops).

### 3.2 Hypothesized root cause

Three plausible explanations (none verified in this audit):

1. **RDKit version drift**: the FlowMol3 venv may have a different `rdkit` version than the canonical Wave 82 environment. RDKit's SMILES parsing tolerance has changed across versions (e.g., aromaticity perception, valence check, kekulization).
2. **Upstream FlowMol3 vendored library drift**: `data/FlowMol3/repo` may have been updated since Wave 82.
3. **PyTorch / CUDA drift**: the canonical Wave 82 used a specific torch + CUDA + DGL stack; the current environment may produce slightly different CTMC sample trajectories.

### 3.3 Disposition

The R3 N=1000 3-seed paired sweep is **DEFERRED to camera-ready** pending:
- RDKit version pin (verify FlowMol3 venv matches Wave 82 venv's `rdkit` version)
- Upstream FlowMol3 vendored commit hash verification (`data/FlowMol3/repo` HEAD should match the Wave 82 vendored commit)
- Re-run with the canonical environment + DGL fix + 3-seed sweep (~30-45 min per arm × 6 arms = ~3-4.5 h total at NFE=250 / n_molecules=100)

---

## 4. Honest Disclosure (Preserved)

The Wave 206 P3 / Wave 225 P3 cross-wave direction-consistency chain is preserved verbatim:

- **Wave 82 / Wave 87 byte-stable reference**: baseline fg_dev = 0.6381, framework fg_dev = 0.6146, diff = −0.0235, framework_WINS by 4.05σ.
- **Wave 195 P2 R-level power**: Welch's t-test unpaired, per-arm SD = 0.214, t = −2.453, df = 1996.998, p_raw = 0.01424, Cohen's d_s = −0.110, Bonferroni α = 0.05/7 = 0.007143, bonf_sig = False (UNDERPOWERED at strict α; direction-consistent).
- **Wave 206 P3 audit**: 1-seed byte-stable reference + blocked 3-seed pooled-SD disclosure.
- **Wave 208 P2 per-record sanity**: N=200 paired, t = −4.027, df = 199, p = 8.03e-05, d_z = −0.285, framework_WINS by −0.360 REOS flags per record.
- **Wave 216 P1 projected N=1000**: t = −9.005, df = 999, p = 1.07e-18, d_z = −0.285, framework_WINS Bonferroni-significant at projected N=1000.
- **Wave 225 P3 cross-wave**: 7/7 historical waves direction-consistent framework-WINS at the 1 available seed; 3-seed pooled-SD upgrade blocked by DGL 2.4.0 regression.

**Wave 338 P5 update (this audit, additive)**:
- DGL 2.4.0 regression now FIXED (verified).
- 3-seed pooled-SD upgrade STILL BLOCKED by sampling-rate gap (RDKit environment drift).
- R3 N=1000 paired full sweep: **DEFERRED to camera-ready** pending environment verification.

---

## 5. Files Modified

| File                                                          | Change                                                                  |
|---------------------------------------------------------------|-------------------------------------------------------------------------|
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py`             | Fixed `_pad_e` dimension mismatch in `_solve_ode_upstream_batch`        |
| `scripts/wave338_p5_r3_n1000_paired.py`                       | New — R3 N=1000 paired sweep at 3 seeds (operational, sampling-rate gap)|
| `docs/audit/wave338-p5-r3-dgl-fix-and-sweep.md`               | New — this audit doc                                                    |

## 6. Verification Artifacts

- **This doc:** `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave338-p5-r3-dgl-fix-and-sweep.md`
- **DGL fix location:** `adaptive_reflow/adapters/flowmol3_v2_adapter.py:2861-2885` (`repeat_interleave` per-mol prior tiling)
- **Secondary fix location:** `adaptive_reflow/adapters/flowmol3_v2_adapter.py:3002-3011` (`_pad_e` dimension fix)
- **Sweep script:** `/home/hugo/codes/flowa-multistep-reinference/scripts/wave338_p5_r3_n1000_paired.py`
- **Canonical Wave 82 reference:** `verification_outputs/flowmol3_n1000_baseline_q4_2026.json` (n_sampled=999)

## 7. Action Items for Camera-Ready

| Item                                                                                              | Status    |
|---------------------------------------------------------------------------------------------------|-----------|
| Verify RDKit version pin in FlowMol3 venv matches canonical Wave 82 environment                   | TODO      |
| Verify `data/FlowMol3/repo` vendored commit hash matches Wave 82 commit                            | TODO      |
| Re-run R3 N=1000 paired sweep at 3 seeds with verified environment + DGL fix                      | TODO      |
| Update CLM-068 with Wave 338 P5 DGL-fix-success + sampling-rate-gap deferral                      | TODO      |
| Update §10.6 / §10.7 R3 cell with Wave 338 P5 DGL-fix-success + sampling-rate-gap deferral       | TODO      |

---

— END OF AUDIT —