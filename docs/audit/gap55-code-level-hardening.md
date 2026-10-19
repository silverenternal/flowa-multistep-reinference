# GAP-55 — code-level hardening: which weak cells are driver defects, not compute gaps

**Date:** 2026-10-19
**Author:** GAP-55 agent (USER AUTHORIZED, NO PUSH)
**Trigger:** the user directive — *"实际上这些问题改几个关键的代码实现就可以做到了，你没发现吗？"*
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

The previous answer priced "make the data harder" as a compute budget. That was
the wrong frame. Five of the weak cells are limited by **what the driver
measures or feeds the model**, not by sample size:

| Cell | Defect class | Where | Minimal fix | New compute |
|---|---|---|---|---|
| R5c | `matched NFE=50` is false: arms run 25 / 48 / 25 NFE vs baseline 50 | `scripts/wave191_p3_mnist_sweep.py:98,210` | allocate a fixed 50-NFE budget by `n_cap` weight | MNIST re-run (minutes) |
| R3 | headline `d_z=-0.285` is a **projection** of a 200-record **proxy** (`reos_n_flags`), not `fg_dev` | `tools/wave87_n1000_sweep.py:320` (`smiles_list[:200]`) | keep all 1000 SMILES; compute per-record `fg_dev` | 30 min GPU |
| R6 | headline `+0.2235` is a **counterfactual**, while a live axis already measures `d_z=-0.84` | `scripts/wave225_p4_k6_tier_aware.py:164`; `verification_outputs/gap31-r6-live-uplift/` | report the live axis; fix the tier-β direction | 0 (already measured) |
| R1 | canonical `--nfe 10` < `--restart-min-nfe 20` → `n_rounds=1`, blend never chains | `tools/gen_lineageflow_n1000_fastas.py:613` | open the gate (`--restart-min-nfe 5`) in the canonical recipe | config only |
| R1 | inference budget is 15× below upstream (10 vs ~150) | same | canonical budget = 150 (NFE is load-bearing, GAP-41b) | 21 h CPU (the one real cost) |
| GAP-53 | FlowMol3 `stochasticity=8.0` makes the map discontinuous across CTMC class flips | `ctmc_vector_field.py:149` default; adapter does not pass `0.0` | thread `sampler_stochasticity` | small |

The first four are **pure code/config**. Only the R1 NFE=150 decisive run is a
real compute decision.

---

## 1. R5c — the "matched NFE=50" label is not what the driver runs

### 1.1 Observed

`FRAMEWORK_MAX_NUM_STEPS = 12` (`scripts/wave191_p3_mnist_sweep.py:98`) is
consumed as a **per-round cap**, not a budget:

```python
ns = int(round(n_cap * float(max_num_steps)))   # :220
```

Measured by importing the module and calling `per_round_num_steps`:

```
baseline NFE = 50
cosine               per-round=[12, 9, 3, 1] total=25
codimension_sheet    per-round=[12, 12, 12, 12] total=48
evidence_driven      per-round=[12, 9, 3, 1] total=25
```

The module docstring discloses this ("average per-round NFE", `:28-30`), but
`CLM-059` and `CLM-060` both label the cell **matched NFE=50**. The label and
the driver disagree by up to 2×.

### 1.2 Interpretation

The direction of the bias is conservative for `cosine` / `evidence_driven`
(they win at half the baseline budget) and roughly neutral for
`codimension_sheet` (48 vs 50). So this is **not** a fabricated win. It is a
**mislabeled comparison**: the paper cannot say "at matched NFE" while the arms
differ by 2×. A reviewer who checks the driver will find it.

### 1.3 Fix

`_allocate_nfe_budget(weights, nfe, n_rounds)` already exists in
`tools/eval/framework.py:737` and guarantees `sum(result) == nfe`. Add
`--equal-total-nfe` to the R5c driver: when set, each arm's per-round NFE is
apportioned from the scheduler `n_cap` weights so **every arm totals exactly 50**.
Default off preserves the historical bytes.

---

## 2. R3 — the headline is a projection of a proxy, not a measurement

### 2.1 Observed

`reproduce/03_R3_FlowMol3.sh` verifies `d_z = -0.285`, `p < 1e-4`, from
`verification_outputs/wave216-p1-r3-per-record.json`. That file's own docstring
(`scripts/wave216_p1_r3_per_record.py:19-25,57-62`) states:

- `fg_dev` is **not** a per-record scalar; the analysis uses the **REOS
  Glaxo+Dundee flag count** as the per-record proxy.
- the actual test is on **n=200** recoverable SMILES; the N=1000 row is a
  `t_N = t_200 * sqrt(N/200)` **projection**.

Root cause of the 200 cap: `tools/wave87_n1000_sweep.py:320`

```python
"smiles_list": smiles_list[:200],  # cap for the JSON dump
```

The N=1000 sweep did run; only the persisted SMILES were truncated. The real
N=1000 aggregate `fg_dev` reading is `p_raw = 0.01424` against the R-level
Bonferroni floor `0.007143` → **UNDERPOWERED** (CLM-060). The reproduce script
therefore asserts a number the claim ledger does not support.

### 2.2 Interpretation

This is the single largest evidence-grade gap in the R-level table: a
projected proxy is presented next to measured cells. It is also the cheapest to
close — 30 min GPU (the historical sweep wall-clock in `reproduce/03`).

### 2.3 Fix

Add `--smiles-cap` to `tools/wave87_n1000_sweep.py` (default 200, legacy
byte-stable; `0` = no cap). Re-run the canonical N=1000 sweep with
`--smiles-cap 0`, then compute the **true per-record `fg_dev` decomposition**
(each record's marginal contribution `Σ_i |1{record carries flag i} -
flag_rate_i^train|`) rather than the flag-count proxy. The aggregate `fg_dev`
is already measured; only its per-record decomposition is missing.

---

## 3. R6 — the live evidence is stronger than the counterfactual headline

### 3.1 Observed

`scripts/wave225_p4_k6_tier_aware.py:164` builds the "tier-aware framework arm"
by **arithmetic**: it takes the frozen Wave-161 `f_plddt`, shifts the easy-tier
per-record diff mean by 0.5, and writes the result back. No model is run. The
JSON's own `honest_disclosure` says: *"Counterfactual construction, NOT a live
GPU run."* The headline `+0.2235` is that construction.

Meanwhile the repository already contains **live** R6 measurements:

| axis | source | n | `d_z` | seeds |
|---|---|---:|---:|---|
| scPerplexity (ESM-IF) | `verification_outputs/gap31-r6-live-uplift/` | 3000 | **−0.8393** | 3/3, all tiers |
| hard-tier pLDDT | GAP-30 / GAP-31 | 990 | **+1.1211** | 3/3 |
| uniform pLDDT | GAP-01 / GAP-31 | 3000 | +0.1466 | 3/3 |

Lower scPerplexity is better, so `−0.84` is a **live framework win on every
seed and every tier** — stronger evidence than the synthetic `+0.2235`.

### 3.2 Interpretation

R6 is not underpowered. It is **headlining the weaker of two available
measurements**. The counterfactual was necessary when no live tier-aware run
existed; it is no longer necessary.

The one real code defect on this cell is the **β-direction inversion**
(`docs/audit/gap01-r6-live-wiring.md` §1.2): the tier-aware wrapper maps
`β = 1 − n_cap`, so halving easy-tier `n_cap` (0.5 → 0.25) *raises* easy-tier β
to 0.75 = more perturbation, while the counterfactual means *less*. The live
as-designed run therefore amplifies exactly the tier the counterfactual damps.

### 3.3 Fix

1. Headline the **live scPerplexity** axis (no new compute; data on disk).
2. For the pLDDT axis, flip the easy-tier direction (`n_cap` factor 1.5, i.e.
   β 0.5 → 0.25) — one constant in the tier-aware wrapper, then one bounded
   re-run if the pLDDT pooled number is retained.

---

## 4. R1 — the canonical config switches the mechanism off

### 4.1 Observed

`tools/gen_lineageflow_n1000_fastas.py:613`:

```python
if int(NFE_PER_RECORD) < int(RESTART_MIN_NFE):
    effective_n_rounds = 1
```

The canonical R1 recipe uses `--nfe 10`; the default `--restart-min-nfe` is 20.
So the canonical framework arm **never chains the restart blend across rounds**.
GAP-40 §0 verified this directly ("the framework arm is a single `solve_ode`
pass — neither the scalar nor the classifier-aware blend fires").

Two consequences:

1. Any lever evaluated at the canonical config (GAP-38/39/40/40b/34/41) was
   evaluated with the mechanism disabled — their "inert" verdicts are
   **conditional on a closed gate**, not mechanism-level.
2. The frozen `158 → 342` headline was produced by Wave 158, **before** the
   gate was introduced (Wave 186 P2). It is not reproducible under current
   defaults. `reproduce/01_R1_LineageFlow.sh` verifies the `.tbl` artifacts,
   not that the current code regenerates them.

### 4.2 Observed — the budget axis

GAP-41b measured the same arm at the upstream budget (`steps_base=100 +
steps_final=50 ≈ 150 NFE`):

| NFE | framework − baseline (N=200, seed 42) | n=3 screen (seeds 42/43/44) |
|---:|---:|---|
| 10 | +1 (p≈0.91) | — |
| 150 | +11 (p≈0.22) | +11 / +19 / +31, mean **+20.33**, 3/3 positive, t=3.50 p=0.073 |

The baseline arm is byte-identical across budgets (37 = 37): the movement is
entirely in the framework arm.

### 4.3 Fix

- **Config (free):** canonical recipe adds `--restart-min-nfe 5` and records
  `effective_n_rounds` in `METADATA.json`. This makes the headline arm actually
  run the described mechanism.
- **Budget (the one real cost):** canonical `--nfe 150`. GAP-41b's
  `--start-index` makes the N=1000 run resumable; measured cost is ~21 h CPU
  for the legacy arm. At N=1000 the N=200 `p=0.073` scales by `sqrt(5)` to
  ≈0.002 if `SD_diff` holds — a decisive test, but a genuine compute decision.

---

## 5. GAP-53 — the FlowMol3 map is discontinuous, by default

`FlowMol3.sample()` defaults to `stochasticity=8.0`
(`data/FlowMol3/.../ctmc_vector_field.py:149`). At that setting a 1e-2
coordinate perturbation can flip a discrete class, and has been observed to
change the atom count (24 → 23). Theorem 4's Lipschitz premise holds only on a
fixed `(atom types, bonds)` stratum. GAP-54 already specifies the fix:
thread `sampler_stochasticity=0.0` and restrict the restart to the coordinate
channel. No new theory is needed; it is a pass-through parameter.

---

## 6. What this changes for the Q1 gap

The prior assessment said "evidence homogeneity is the bottleneck, and closing
it costs compute". The corrected reading:

- **4 cells (R5c, R3, R6, R1-config) can be made measurement-grade with code
  and configuration alone.** Three of them (R3, R6, R1-config) currently rest
  on a proxy, a counterfactual, or a disabled mechanism — the exact defects a
  Q1 reviewer probes first.
- **1 axis (R1 NFE=150) is a real compute decision**, and its pilot is already
  3/3 direction-consistent.
- **1 mechanism (GAP-54)** needs a parameter pass-through, then a small paired
  run.

No seed engineering is involved anywhere in this list.

---

## 7. Reproduce (current state)

```bash
# R5c NFE audit (no model run)
python3 -c "
import sys; sys.path.insert(0,'.')
from scripts.wave191_p3_mnist_sweep import per_round_num_steps, ARM_LABELS
for a in ARM_LABELS:
    ns = per_round_num_steps(a, 4, 12); print(a, ns, sum(ns))
"

# R3 SMILES cap
grep -n "smiles_list\[:200\]" tools/wave87_n1000_sweep.py

# R1 gate
grep -n "effective_n_rounds = 1" tools/gen_lineageflow_n1000_fastas.py

# R6 live axes
python3 -c "
import json; d=json.load(open('verification_outputs/gap31-r6-live-uplift/gap31_summary.json'))
print(d['scperplexity_live']['pooled'])
"
```
