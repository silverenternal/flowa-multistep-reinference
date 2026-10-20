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
| R3 | headline `d_z=-0.285` is a **projection** of a **200-record** **proxy** (`reos_n_flags`), not `fg_dev`; the file named `n1000` is `n_total_per_arm=200` | `tools/wave87_n1000_sweep.py:320` (`smiles_list[:200]`) + artifact N | keep all 1000 SMILES; run N=1000; compute per-record `fg_dev` | 30 min GPU |
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

**The canonical artifact itself is N=200.** The files named
`flowmol3_n1000_{baseline,framework}_wave87_q4_2026.json` record
`n_total_per_arm = 200`, `n_sampled = 200`, `n_smiles = 0`:

```
$ python3 -c "import json; d=json.load(open('verification_outputs/flowmol3_n1000_sweep_wave87_q4_2026.json')); print(d['n_total_per_arm'])"
200
```

So the "N=1000" label is a filename, not a measurement. The projection step is
therefore not a convenience — it is the only thing standing between a
200-record proxy and the claimed N=1000 headline.

A second, independent defect compounds it: `tools/wave87_n1000_sweep.py:320`

```python
"smiles_list": smiles_list[:200],  # cap for the JSON dump
```

Even a future N=1000 run would persist only the first 200 SMILES, so a
per-record `fg_dev` decomposition could not be computed from the dump.

### 2.2 Interpretation

This is the single largest evidence-grade gap in the R-level table: a
projected proxy is presented next to measured cells, and the underlying
artifact is one fifth of the advertised sample size. It is also cheap to close
— 30 min GPU (the historical sweep wall-clock in `reproduce/03`).

### 2.3 Fix

Add `--smiles-cap` (default 200, legacy byte-stable; `0` = no cap) and
`--output-dir` / `--wave-id` (so a new run cannot clobber the historical
artifacts) to `tools/wave87_n1000_sweep.py`. Re-run the canonical **N=1000**
sweep with `--smiles-cap 0`, then compute the **true per-record `fg_dev`
decomposition** (each record's marginal contribution `Σ_i |1{record carries
flag i} - flag_rate_i^train|`) rather than the flag-count proxy.

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

---

## 8. Results (2026-10-19, all three re-runs completed)

### 8.1 R5c — equal NFE flips the cell to a significant honest negative

Run: `verification_outputs/gap55-r5c-equal-nfe/`, production ckpt, N=1000,
`--equal-total-nfe --shared-prior`, seed 42, 33 min.

| arm | per-round NFE | total | FID | Δ vs baseline | Bonferroni p | `d_z` |
|---|---|---:|---:|---:|---:|---:|
| baseline | — | 50 | 9.8785 | — | — | — |
| cosine | [25, 18, 6, 1] | **50** | 11.8322 | **+12.43%** | 1.17e-07 | +5.36 |
| codimension_sheet | [13, 12, 12, 13] | **50** | 12.1874 | **+14.64%** | 4.10e-09 | +7.83 |
| evidence_driven | [25, 18, 6, 1] | **50** | 11.0440 | **+9.17%** | 3.49e-06 | +3.61 |

Verdict: **baseline_wins** on all three arms.

Reading. The historical R5c headline (`−28.43%`, framework wins) came from
(a) the **smoke** checkpoint and (b) arms at 25/48/25 NFE against a 50-NFE
baseline. Under a truly equal budget on the **production** checkpoint the
direction is a significant regression on every arm. This is consistent with
the Wave 280 production-ckpt reading (+10.37%) and removes the "matched NFE"
ambiguity from the cell. R5c should be reported as **REGRESSES at matched
NFE=50**, not as a win.

### 8.2 R3 — N=1000 measured, nominal but not Bonferroni-significant

Run: `verification_outputs/gap55-r3-full-smiles/`, FlowMol3 `last.ckpt`,
N=1000/arm, NFE=250, `--smiles-cap 0 --shared-prior`, seed 42, 17 min.

| arm | n_sampled | n_smiles persisted | `fg_dev` |
|---|---:|---:|---:|
| baseline | 998 | 1000 | 0.7174 |
| framework | 995 | 1000 | 0.6624 |

Sweep Δ = **−0.0550** (framework improves).

Record-level bootstrap (`tools/gap55_r3_per_record_fg_dev.py`, B=2000,
recomputed `fg_dev` from the REOS flag matrix):

| quantity | value |
|---|---:|
| recomputed `fg_dev` baseline | 0.6562 |
| recomputed `fg_dev` framework | 0.5949 |
| Δ (framework − baseline) | **−0.0613** |
| bootstrap 95% CI | **[−0.1169, −0.0010]** |
| bootstrap p (two-sided) | 0.043 |
| favourable draws | 97.85% |
| R-level Bonferroni α (k=7) | 0.00714 |

Reading. The measured N=1000 effect is **negative and its 95% CI excludes 0**,
so R3 now has a real directional result instead of a projection. It does
**not** clear the pre-registered R-level Bonferroni floor, and it is a single
seed — the R-level bar is 3 seeds. It is therefore **NOT_SIGNIFICANT at the
R-level bar**, not a win.

**The proxy is not a decomposition.** The historical per-record test used the
REOS flag-count proxy. On this N=1000 run the proxy's paired diff is
**+0.0021** (p=0.25, `d_z`=+0.036) — the opposite sign from the aggregate
`fg_dev` (−0.061). A per-record t-test on the flag count is therefore not a
test of `fg_dev`; the record-level bootstrap of the set-level metric is the
correct inference. This independently confirms that the historical
`d_z=-0.285` proxy result should not be presented as an `fg_dev` effect.

### 8.3 R1 — the gate-open mechanism is live under current code

Run: `verification_outputs/gap55-r1-gate-open-n200/`, N=200, seed 42,
`--nfe 10 --n-rounds 3 --restart-min-nfe 5`.

| check | observed |
|---|---|
| `effective_n_rounds` in manifest | **3** (gate open) |
| `framework_fallback_per_family_count` | `{}` (no bare-RNG fallback) |
| framework sequences differing from baseline | **200 / 200** |

Reading. With the gate open, the canonical driver really does chain
`export_endpoint -> apply_restart_distribution` across three rounds on the
current code. The canonical recipe previously left the gate closed, which is
why every lever screen at `--nfe 10` measured a single-pass arm. This run does
not by itself produce a hit count; it verifies the wiring that the N=1000
NFE=150 decisive run depends on.

### 8.4 Net effect on the evidence table

| cell | before | after |
|---|---|---|
| R5c | "framework wins −28.43% at matched NFE=50" (smoke ckpt, unequal NFE) | **REGRESSES +9.2…+14.6% at true NFE=50** (production ckpt, 3/3 arms) |
| R3 | `d_z=-0.285` projected from a 200-record proxy | **Δfg=−0.061, CI [−0.117, −0.001], p=0.043**, single seed, not Bonferroni-significant |
| R1 | canonical arm had the mechanism switched off | **wiring verified live**; NFE=150 decisive run is the remaining compute decision |
| R6 | counterfactual `+0.2235` | live scPerplexity `−0.84` (3/3 seeds) available as the headline |

No seed engineering was used. The only new compute was 33 min CPU (R5c),
17 min GPU (R3), and ~11 min CPU (R1).

### 4.4 Observed — the N=1000, NFE=150 confirmation (seed 42)

`verification_outputs/gap55-r1-nfe150-n1000/seed42/` (the run whose cost §4.3
called "the one real cost"). N=1000, `--nfe 150 --n-rounds 3
--restart-min-nfe 5 --temperature 1.0 --upstream-eval-len-bias short`, gate
open, `.venvs/lineageflow_venv`, `cuda:0`. Scoring is the canonical upstream
HMMER pipeline (`family_validity__hmmscan_total_hits`).

| arm | total hits | unique queries | coverage | eval wall |
|---|---:|---:|---:|---:|
| baseline | 158 | 145 | 0.145 | 441.8 s |
| framework | **275** | **230** | **0.230** | 349.9 s |
| Δ | **+117 (+74.1 %)** | +85 (+58.6 %) | +0.085 | — |

Per-record paired analysis over the 1000 records (`family_validity_per_seq.jsonl`,
paired by `qid`, 4000-replicate bootstrap, seed 20261020):

| quantity | value |
|---|---|
| mean Δ hits per record | **+0.1170** |
| 95 % CI | **[+0.0730, +0.1600]** |
| records with framework > baseline | 207 |
| records with baseline > framework | 121 |
| ties | 672 |

**Reading.** At the budget where the mechanism actually runs, the framework arm
produces 74 % more Pfam hits and the paired CI excludes zero by a wide margin.
This is a **single draw** (seed 42), so the honest label is *powered but
single-seed*, not `SUPPORTED` under the three-seed convention used elsewhere.
The N=200 screen in §4.2 gave `p = 0.073`; at N=1000 the paired CI excludes 0,
which is consistent with that screen scaling rather than contradicting it.

The remaining attribution question — does the *blend* earn this, or is it the
initial-condition/prior difference? — is GAP-45 (`docs/audit/gap45-r1-blend-off-wiring.md`),
which runs the same recipe with `--beta-override 0.0` (β = 0, m = 1, identity
restart) at three seeds. Until that lands, the R1 NFE=150 win is
**mechanism-unattributed**.
