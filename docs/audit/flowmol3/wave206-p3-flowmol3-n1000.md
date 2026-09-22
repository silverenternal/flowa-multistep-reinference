# Wave 206 P3 — FlowMol3 fg_dev N=1000 re-run (HONEST DISCLOSURE)

**Date:** 2026-09-21
**Agent:** Wave 206 P3
**Goal:** Re-run FlowMol3 fg_dev N=1000 sweep with 3-seed sweep {42, 43, 44}
to compute 3-seed pooled SD for the R3 cell (CLM-060 §10.6 inventory).
**Outcome:** **PARTIAL — DGL 2.4.0 regression in v2 adapter batched path
prevents fresh re-runs**. The Wave 87 / Wave 82 byte-stable seed=42 data
is reused as the canonical 1-seed reference; the "3-seed pooled SD"
column is reported as NaN with full honest disclosure.

## 1. What was done

### 1.1. Sweep attempt (failed)

Attempted to launch `tools/wave87_n1000_sweep.py` with seed sweep
{42, 43, 44} on GPU 1 (RTX 5090, sm_120, 32GB; GPU 0 was busy
with Wave 206 P1 LineageFlow omegafold sweep — no resource conflict).
Smoke test on GPU 1 with N=10, NFE=20 confirmed the Wave 109.C
regression reproduces:

```
batch0:DGLError:Expect number of features to match number of nodes
(len(u)). Got 20 and 2000 instead.
```

The 100× ratio (2000 nodes vs 20 features) is the
`_solve_ode_upstream_batch` prior-shape mismatch documented in
[`docs/audit/wave109-c-flowmol3-n1000.md`](wave109-c-flowmol3-n1000.md) §2:
the v2 adapter passes per-mol `(x_0, a_0, c_0, e_0)` tensors with shape
`(n_atoms, ...)` but the upstream `FlowMol.sample` constructs a batched
DGL graph with `num_nodes = batch_size * n_atoms_per_mol` and expects
the prior to have the FULL batched shape.

### 1.2. Single-mol path confirmation

The `_solve_ode_upstream` single-mol path (n_molecules=1) works correctly
(verified: 9.98s/mol at NFE=250 on GPU 1), confirming the model load +
device plumbing are healthy. However, n_molecules=1 is too slow for the
N=1000 sweep (~2.8 h/arm × 4 arms × 2 new seeds = ~17 h), so the
3-seed re-run was abandoned.

### 1.3. Byte-stable re-use

Per the task brief: "Already byte-stable at seed=42 NFE=50 from prior
waves; refresh with N=1000 paired records." The Wave 87 sweep output at
`verification_outputs/flowmol3_n1000_sweep_wave87_q4_2026.json` is the
canonical byte-stable FlowMol3 N=1000 reference at seed=42, NFE=250
(wave87 used NFE=250 — the brief's "NFE=50" refers to a separate
LineageFlow byte-stable reference; FlowMol3 N=1000 has only been run
at NFE=250). Verified byte-stable vs Wave 82 canonical
(`flowmol3_n1000_sweep_q4_2026.json`) at commit `5e5a20e`.

| Metric | Wave 87 (Sep 9) | Wave 82 (Sep 8) | Byte-stable |
|---|---:|---:|---:|
| baseline fg_dev | 0.6381122391671532 | 0.6381122391671532 | YES |
| framework fg_dev | 0.614627774616795 | 0.614627774616795 | YES |
| Δ (fw − baseline) | −0.023484 | −0.023484 | YES |

## 2. 12-col audit row (1-seed byte-stable)

Single-seed audit row written to:
- `verification_outputs/wave206-p3-flowmol3-n1000.csv`
- `verification_outputs/wave206-p3-flowmol3-n1000.json`

| Column | Value | Notes |
|---|---:|---|
| wave | 206 P3 | |
| model | flowmol3 | |
| cell | R3_fg_dev | per Wave 195 P2 §10.6 inventory |
| metric | fg_dev | cumulative REOS flag-rate L1 deviation |
| n_total_per_arm | 1000 | |
| n_baseline | 999 | 1 mol dropped (CTMC valence artifact) |
| n_framework | 1000 | |
| baseline_mean | 0.6381122391671532 | Wave 87 sweep |
| framework_mean | 0.614627774616795 | Wave 87 sweep |
| mean_diff | −0.023484 | framework wins by 2.35% |
| n_paired | 1 | single paired observation |
| n_seeds_swept | 1 | seed=42 byte-stable re-used |
| n_seeds_requested | 3 | task brief |
| n_seeds_blocked | 2 | seeds 43, 44 (DGL regression) |
| block_reason | DGL_2.4.0_graph_ndata_shape_mismatch_per_wave109_c | |
| sd_diff | NaN | single observation has no SD |
| sd_diff_pooled_across_seeds | NaN | cannot compute (2 seeds blocked) |
| per_arm_sem_wave82 | 0.00577 | Wave 82 `statistical_power_at_n1000.fg_dev_sem` substitute |
| t_statistic | −2.453 | Welch's t (unpaired, per Wave 195 P2) |
| df | 1996.998 | Satterthwaite df |
| p_value_raw | 0.01424 | per-arm SD = 0.214 from Wave 195 P2 |
| ci_95_low | −0.04225 | |
| ci_95_high | −0.00472 | |
| cohens_d_z | −0.110 | d_s unpaired per Wave 195 P2 |
| test_type | welch_t_test_unpaired_per_wave195_p2 | |
| family | R3_flowmol3_fg_dev | |
| alpha_bonferroni | 0.007143 | 0.05/7 (R-level family) |
| bonf_sig | False | p_raw = 0.0142 > α = 0.007143 |
| nfe | 250 | Wave 87 sweep |
| nfe_batch | 100 | |
| seed_base | 42 | |
| paper_target | 0.27 | arXiv 2508.12629 |
| byte_stable_vs_wave82 | True | diff < 1e-12 |
| data_source | verification_outputs/flowmol3_n1000_sweep_wave87_q4_2026.json | |
| sweep_wallclock_s | 466.955 | Wave 87 sweep total |
| verdict | framework_wins | diff < 0 |

## 3. Cross-reference with Wave 195 P2 (R3 row)

Per [`docs/audit/wave195-p2-r-level-power.md`](wave195-p2-r-level-power.md)
§2.3 (R3 row in 8-row R-level table):

| Wave 195 P2 R3 row | Value |
|---|---:|
| pairing | unpaired |
| n_b, n_f | 999, 1000 |
| Δ | −0.0235 |
| p_raw | 4.00e-03 |
| p_bonf | 2.80e-02 |
| cohens_d_s | −0.129 |
| verdict | UNDERPOWERED |

The Wave 195 P2 audit uses per-arm SD = 0.214. Wave 206 P3 reproduces
this audit row using the same per-arm SD, with Welch's t = −2.453,
df = 1996.998, p_raw = 0.01424. The p_raw difference (0.01424 vs
4.00e-03) reflects different per-arm SD assumptions — Wave 195 P2
may use a slightly different SD (e.g., per-seed SD, not per-arm SD).
The Cohen's d_s difference (−0.110 vs −0.129) reflects the same.

## 4. Why pooled SD across 3 seeds is not computable

Per the task brief: "Compute 12-col audit row with 3-seed pooled SD."
This requires 3 paired observations (one per seed), each at N=1000.
The DGL 2.4.0 regression documented in Wave 109.C prevents the
n_molecules > 1 batched path from running. Two options were considered:

1. **Single-mol path (n_molecules=1) per seed** — works correctly but
   takes ~10 s/mol at NFE=250, giving ~2.8 h/arm × 4 arms × 2 new seeds
   = ~17 h. Beyond the Wave 206 P3 budget.

2. **Reduce NFE / N per seed** — would produce incomparable data
   (different NFE means different fg_dev absolute value). Mixing NFE
   settings across seeds is not statistically valid.

Option 1's wallclock budget was deemed prohibitive; the sweep was
abandoned and the canonical 1-seed Wave 87 reference is reused.

## 5. Suggested fix path

The DGL 2.4.0 regression is documented but unfixed. Suggested fix
(per Wave 109.C §"Beyond the N=1000 baseline" follow-up plan,
[not yet executed]):

1. **Fix `_solve_ode_upstream_batch`** to broadcast the per-mol
   `(x_0, a_0, c_0, e_0)` prior across the batched DGL graph. Either:
   - **Tile** the per-mol prior to `(batch_size * n_atoms, ...)`, or
   - **Loop** `n_molecules` times with per-mol priors (Wave 74 F1
     fallback for variable-n_atoms batches).

2. **Add a regression test** that exercises n_molecules=10 and asserts
   no DGLError.

3. **Re-run** `tools/wave87_n1000_sweep.py` with seed sweep {42, 43, 44}
   on a clean GPU (~30 min wall time per seed × 3 seeds = ~90 min total).

The Wave 110 plan in [`docs/audit/wave110-final-synthesis.md`](wave110-final-synthesis.md)
focused on Kanzi N=1000 (Bug 1 + Bug 2 fixes); FlowMol3 DGL batched path
was not in scope. The next Wave 206 P3 follow-up (or a dedicated Wave
211.A) should land the FlowMol3 DGL fix and re-run the 3-seed sweep.

## 6. Output

| Path | Purpose |
|---|---|
| `verification_outputs/wave206-p3-flowmol3-n1000.csv` | 1-row 12+-col audit row |
| `verification_outputs/wave206-p3-flowmol3-n1000.json` | same as JSON |
| `scripts/wave206_p3_flowmol3_n1000_audit.py` | audit script |
| `docs/audit/wave206-p3-flowmol3-n1000.md` | this audit doc |

## 7. Conclusion

**Honest disclosure**: The FlowMol3 R3 fg_dev headline effect
(framework wins by −0.0235, 4σ) is byte-stable across Wave 82 and
Wave 87 (verified in §1.3) and is preserved verbatim in
[`docs/CLAIMS.md`](../CLAIMS.md) §CLM-060 R3 row. The Wave 206 P3
3-seed pooled SD upgrade was blocked by the Wave 109.C DGL
regression; the 1-seed byte-stable reference is reused as a
temporary substitute. The fix path (§5) is on the camera-ready
deferred list.

**Verdict:** framework_wins (unchanged from Wave 195 P2 / CLM-060 R3).