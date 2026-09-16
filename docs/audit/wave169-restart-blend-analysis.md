# Wave 169 P3 — Restart-Blend Over-Application Investigation at High NFE

**Status:** investigation complete; hypothesis CANNOT be confirmed under
synthetic-mode test surface.
**Auditor:** Wave 169 P3 (paper-quality follow-up to Wave 169 P1 + P2).
**Goal:** Determine if the framework's restart-blend mechanism (default
`n_rounds=3`) is over-applying at high NFE, causing the pLDDT degradation
observed in Wave 168 (NFE=50→500: framework loses pLDDT by 0.83→1.56
while winning scPerplexity by 3.05→3.37).

---

## 1. TL;DR — Finding

**Hypothesis CANNOT be confirmed under the synthetic-mode test surface.**

The framework's `n_rounds=1` and `n_rounds=3` produce **byte-identical**
sequences when the LineageFlowAdapter runs in `force_mode="synthetic"`
(default in the cold-clone / test environment). Confirmed by:

- **MD5 match:** both fastas hash to
  `a7eec2835a34be0a82f2a5315867575d`
  (`/tmp/w169/n_rounds_test/nfe_200_n_rounds_1/framework.fasta` and
  `/tmp/w168/fastas/nfe_200/framework.fasta` are byte-identical).
- **Per-position token-index match:** across all 4 Pfam families × 3
  seed_offsets (12/12 cells), `n_rounds=1` and `n_rounds=3` produce
  identical `(256,)` argmax arrays via
  `adapter.observe_token_indices(trace, ...)`.
- **Implied eval result:** since the eval operates on the produced
  fasta, `n_rounds=1` will produce the SAME `pLDDT=41.00`,
  `scPerplexity=15.10` as `n_rounds=3` (these are deterministic
  functions of the fasta content).

**Why synthetic mode makes them identical:** the synthetic velocity
field (adaptive_reflow/adapters/lineageflow.py:408) is a 2-layer MLP
with a fixed attractor for each `(seed, family)` pair. After ~30 NFE
steps, the integrated state collapses to a single dominant
argmax-token at every position. The restart-blend dilutes the
integrated state by 50% per round (default `memory_fraction=0.5`), but
the diluted state still has the same dominant argmax — argmax is
insensitive to sub-modal-probability mass. So `n_rounds=3` (surviving
12.5% of integrated state) and `n_rounds=1` (surviving 50% of
integrated state) both observe the same argmax tokens.

**Implication:** the over-application hypothesis is theoretically
plausible but UNTESTABLE on the cold-clone / synthetic test surface.
Testing it requires either (a) a trained LineageFlow torch-mode
checkpoint (the real checkpoint is gated / not vendored in this
environment), or (b) a synthetic velocity field with sub-modal
sensitivity that distinguishes 12.5% vs 50% survival.

---

## 2. Mechanism — What restart-blend does

The framework arm (Wave 45 + Wave 81 path) chains three calls in a loop
for `n_rounds` iterations:

```
for r in range(n_rounds):
    trace = adapter.solve_ode(cur_bundle, condition, seed+r)
    endpoint = adapter.export_endpoint(cur_bundle)            # identity pass-through
    cur_bundle = adapter.apply_restart_distribution(endpoint, policy)
```

`_solve_framework` (tools/eval/framework.py:434) splits the total NFE
budget evenly across `n_rounds` rounds:

```python
base_per_round = max(1, int(nfe) // n_rounds_int)
remainder_per_round = max(0, int(nfe) - base_per_round * n_rounds_int)
nfe_per_round_list = [base_per_round] * n_rounds_int
if remainder_per_round > 0:
    nfe_per_round_list[-1] += remainder_per_round
```

For `nfe=200, n_rounds=3`, each round gets 66/66/68 NFE. For
`nfe=200, n_rounds=1`, a single round gets 200 NFE.

`apply_restart_distribution` (adaptive_reflow/adapters/lineageflow.py:1640)
blends the integrated state with a fresh uniform perturbation:

```python
m = max(0.0, min(1.0, float(memory_fraction)))   # default = 0.5
blended = (m * prior_theta + (1.0 - m) * fresh_theta).astype(np.float64)
blended = blended / np.maximum(blended.sum(axis=-1, keepdims=True), 1e-30)
```

With the default `memory_fraction = 0.5` (from `memory_fraction_for`
at adaptive_reflow/adapters/_adapter_common.py:70, fallback when
`policy.beta_by_channel` lacks the channel entry), the blend is
**50/50** between the prior integrated state and a fresh uniform
prior. After `n_rounds` rounds, the surviving fraction of the
original integrated state follows `(memory_fraction)^n_rounds` =
`0.5^3 = 0.125` (12.5%) for n_rounds=3, vs `0.5^1 = 0.5` (50%)
for n_rounds=1.

The framework arm observes the **final round's `solve_ode` trace**
(tools/gen_lineageflow_n1000_fastas.py:186-191 → `_solve_framework`
returns `(trace, _wall)`), NOT the blended state. But the **initial
condition for that final `solve_ode`** is the blended state — so the
blend controls what the final trace sees, not what it directly returns.

---

## 3. Hypothesis — Why n_rounds=3 hurts at high NFE

At low NFE (e.g. NFE=10), the per-round integration budget is so small
(3-4 NFE per round) that the blend is harmless — the integrated state
from each round is barely informative, so blending with uniform doesn't
destroy much signal.

At high NFE (NFE=200), each round integrates 67 NFE steps, producing a
sharp posterior. The 50/50 blend with uniform then DILUTES this
sharpness by 50% per round. After 3 rounds, only 12.5% of the
original integrated state survives — the framework is integrating
sharp posteriors then erasing them.

`n_rounds=1` runs the full 200 NFE integration in a single round,
with a single 50/50 blend applied to the START state. The final
trace observes the FULL 200-NFE integrated posterior with minimal
distortion.

---

## 4. Experiment — n_rounds=1 vs n_rounds=3 at NFE=200

**Setup:**
- Same 4 Pfam families as Wave 168 (PF00005.27, PF00072.24,
  PF00183.19, PF02517.18), N=100 records (25/family), seed=42
- Framework fasta generated via
  `tools/gen_lineageflow_n1000_fastas.py --outdir ... --n 100 --nfe 200 --n-rounds {1,3}`
  (the `--n-rounds` CLI flag was added temporarily for this audit; it is NOT in the final committed script per §5 — see `N_ROUNDS=3` revert note at the bottom of this section)
- n_rounds=3 fasta is the canonical Wave 168 artifact at
  `/tmp/w168/fastas/nfe_200/framework.fasta` (n_rounds default 3,
  manifest confirms n_rounds=3)
- n_rounds=1 fasta generated for this experiment at
  `/tmp/w169/n_rounds_test/nfe_200_n_rounds_1/framework.fasta`
  (manifest confirms n_rounds=1, nfe_per_record=200)

**Sanity-check result (BEFORE running eval):**

```text
md5sum /tmp/w169/n_rounds_test/nfe_200_n_rounds_1/framework.fasta \
        /tmp/w168/fastas/nfe_200/framework.fasta
a7eec2835a34be0a82f2a5315867575d  /tmp/w169/n_rounds_test/nfe_200_n_rounds_1/framework.fasta
a7eec2835a34be0a82f2a5315867575d  /tmp/w168/fastas/nfe_200/framework.fasta
```

The two fastas are **byte-identical** (same MD5). Confirmed by
per-family × per-seed spot-check:

```
PF00005.27 seed=42   : equal=True
PF00005.27 seed=100  : equal=True
PF00005.27 seed=1234 : equal=True
PF00072.24 seed=42   : equal=True
PF00072.24 seed=100  : equal=True
PF00072.24 seed=1234 : equal=True
PF00183.19 seed=42   : equal=True
PF00183.19 seed=100  : equal=True
PF00183.19 seed=1234 : equal=True
PF02517.18 seed=42   : equal=True
PF02517.18 seed=100  : equal=True
PF02517.18 seed=1234 : equal=True
ALL EQUAL: True
```

(Verification script: `_solve_framework(adapter, nfe=200, seed, n_rounds={1,3})`
for each cell, then `adapter.observe_token_indices(trace, ...)` and
`np.array_equal(idx1, idx3)`.)

**Implied eval result (deterministic):**

| arm | n_rounds | NFE | pLDDT_mean | scPerplexity_mean |
|------|----------|------|------------|--------------------|
| framework | 3 | 200 | 41.00 | 15.10 |
| framework | 1 | 200 | 41.00 (same) | 15.10 (same) |
| baseline (Wave 168) | — | 200 | 42.33 | 18.15 |

The eval run was started but killed after confirming the fasta
byte-identity — no value in completing a 30+ minute eval that will
return the same numbers already captured in Wave 168.

---

## 5. Conclusion — Over-application is untestable under synthetic mode

**Under the synthetic-mode test surface (default in cold-clone),
the framework's restart-blend over-application hypothesis CANNOT be
empirically confirmed or denied** — the synthetic velocity field's
attractor is so strong that argmax produces identical tokens
regardless of n_rounds.

**The theoretical prediction remains:**
- For a real torch-mode checkpoint with sub-modal-sensitive
  outputs, `n_rounds=1` should preserve more of the integrated
  sharpness than `n_rounds=3`, possibly recovering 1-3 pLDDT absolute
  at the cost of +0.5-2 scPerplexity.
- This is the Wave 169 P1 trade-off hypothesis at finer
  granularity: the restart-blend dilutes the integrated state by
  `memory_fraction^n_rounds`, and the dilution is the causal axis
  on which the trade-off turns.

**For paper §10.14 (ADDITIVE disclosure):**

The §10.14 block should acknowledge the synthetic-mode
limitation and frame the over-application claim as **mechanistic**
(not empirically demonstrated under synthetic mode):

> "The framework's restart-blend mechanism (3 rounds by default)
>  applies a 50/50 blend with a fresh uniform perturbation between
>  rounds. After 3 rounds, only 12.5% of the original integrated
>  state survives (with the default memory_fraction=0.5). This
>  mechanism predicts that reducing n_rounds at high NFE should
>  recover pLDDT by reducing dilution, but the synthetic-mode
>  test surface used in this audit collapses to identical argmax
>  outputs regardless of n_rounds (verified across 4 families × 3
>  seeds = 12 cells, all byte-identical). Confirming the
>  prediction empirically requires a real torch-mode
>  LineageFlow checkpoint."

**No code change recommended.** The `--n-rounds` CLI flag added in
this audit is kept for future re-runs but `N_ROUNDS=3` remains the
canonical default (backward-compatible with Wave 81/86 manifest).

---

## 6. Why this matters — paper §10.14 ADDITIVE block

The Wave 169 P1 audit (319e881) recommended that §2.8.1 "lower C_g →
better foldability" be hedged with the Wave 168 §10.13 trade-off
disclosure, and that a new §10.14 block ADDITIVELY distinguish
theorem-consistent claims (BL-distance bounds) from
empirically-conditional claims (pLDDT per-metric downstream). This
audit supplies the missing mechanism evidence: the framework's
restart-blend IS theoretically predicted to over-apply at high NFE,
but the synthetic test surface cannot empirically confirm this.

For the paper text, §10.14 should:

1. Disclose the NFE × n_rounds interaction explicitly (mechanism
   description with `memory_fraction^n_rounds` decay formula).
2. Add an explicit "UNTESTED UNDER SYNTHETIC MODE" caveat for any
   quantitative pLDDT-recovery claim that would require a real
   torch-mode checkpoint to confirm.
3. Cite the 12-cell byte-identity finding from this audit as
   evidence that the synthetic mode's argmax invariance makes
   it insensitive to restart-blend dilution.

---

## 7. Reproducibility — commands

```bash
# Generate n_rounds=1 fastas @ NFE=200
# (NB: --n-rounds CLI flag was reverted; re-add to the script first
#  OR temporarily patch N_ROUNDS module-level constant before running)
python tools/gen_lineageflow_n1000_fastas.py \
    --outdir /tmp/w169/n_rounds_test/nfe_200_n_rounds_1/ \
    --n 100 --nfe 200 --n-rounds 1

# Compare to n_rounds=3 fasta
md5sum /tmp/w169/n_rounds_test/nfe_200_n_rounds_1/framework.fasta \
       /tmp/w168/fastas/nfe_200/framework.fasta

# Per-cell spot-check (12 cells: 4 families × 3 seeds)
python -c "
import sys, numpy as np
sys.path.insert(0, '/home/hugo/codes/flowa-multistep-reinference')
from adaptive_reflow.adapters.lineageflow import LineageFlowAdapter, AMINO_ACID_CATEGORICAL
from tools.run_real_ckpt_eval import _solve_framework
for fam in ['PF00005.27', 'PF00072.24', 'PF00183.19', 'PF02517.18']:
    for seed in [42, 100, 1234]:
        a1 = LineageFlowAdapter(family_id=fam, num_steps=200, solver='euler', force_mode='synthetic', seed_offset=seed)
        a3 = LineageFlowAdapter(family_id=fam, num_steps=200, solver='euler', force_mode='synthetic', seed_offset=seed)
        t1, _ = _solve_framework(a1, nfe=200, seed=seed, n_rounds=1)
        t3, _ = _solve_framework(a3, nfe=200, seed=seed, n_rounds=3)
        o1 = np.asarray(a1.observe_token_indices(t1, None)[str(AMINO_ACID_CATEGORICAL)])
        o3 = np.asarray(a3.observe_token_indices(t3, None)[str(AMINO_ACID_CATEGORICAL)])
        print(f'{fam} seed={seed}: equal={np.array_equal(o1, o3)}')
"
```

The `--n-rounds` CLI flag was added temporarily for this Wave 169 P3
audit but is NOT in the final committed script (reverted per the
"don't commit" instruction in the Wave 169 P3 task brief). To re-run
this ablation, re-add the flag at `tools/gen_lineageflow_n1000_fastas.py:296`
and wire it through `N_ROUNDS` exactly as `--nfe` is wired through
`NFE_PER_RECORD`. `N_ROUNDS=3` remains the module default.

---

## 8. Provenance

- Wave 168 P4 §10.13 ADDITIVE disclosure: commit 754f299, eval + plot + paper-quality audit
- Wave 169 P1 framework pLDDT NFE-inversion diagnostic: commit b01d93f, doc-only
- Wave 169 P2 JMAA Theorem 1 vs paper downstream claim audit: commit 319e881, doc-only
- Wave 169 P3 (this audit): n_rounds=1 vs n_rounds=3 ablation @ NFE=200 → byte-identical
  in synthetic mode; hypothesis marked UNTESTED under synthetic mode
