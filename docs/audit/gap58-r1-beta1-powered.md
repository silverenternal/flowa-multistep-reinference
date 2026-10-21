# GAP-58 — β=1 at N=1000: the memory term is bounded at ±0.057 hits/record

**Date:** 2026-10-21
**Status:** closed. Single seed, by user decision (see `todo-history.md` §15).
**Question:** at the R1 headline N, how much does the memory term actually contribute?

---

## 1. What was run

`reproduce/gap58_r1_beta1_n1000.sh`, pinned to **seed 42 only**. β=1.0 sets the
memory fraction m = 1 − β = 0, so the restart blend reduces to the fresh prior
and the arm contains no memory term at all. Everything else matches
`verification_outputs/gap55-r1-nfe150-n1000/seed42`: N=1000, NFE=150, R=3,
`restart_min_nfe=5`, temperature 1.0, `--start-index 0`, same four Pfam
families, same length bias.

Two seeds were cancelled mid-run. β=1 is a null bound: it cannot raise any
metric, so under the decision rule recorded in `todo-history.md` §15 it does
not earn three seeds. The result below is therefore **single-seed** and is
labelled that way everywhere.

| control | result |
|---|---|
| baseline hits | **158**, byte-identical to GAP-55's baseline (same prior) |
| framework FASTA md5 | `bbb8d764…`, differs from GAP-55's `77d63648…` (the arm is live, not a copy) |
| manifest | `beta_override: 1.0`, `effective_n_rounds: 3`, `nfe_per_record: 150` |
| scorer | `tools/gap55_r1_score_fastas.py --metrics family_validity` (sequential; the novelty metric collides on the shared MMseqs2 temp dir) |

## 2. Observed

Per-record paired analysis over the 1000 records (bootstrap 95 % CI, exact sign test):

| arm | hits | Δ hits/record | 95 % CI | up/down | sign p |
|---|---:|---:|---|---:|---:|
| baseline | 158 | — | — | — | — |
| β=1/6 (GAP-55, canonical) | 275 | +0.117 | [+0.073, +0.160] | 207 / 121 | 2.4e-06 |
| **β=1 (this run)** | **284** | **+0.126** | **[+0.084, +0.168]** | 207 / 109 | 3.8e-08 |
| **β=1 − β=1/6** | — | **+0.009** | **[−0.041, +0.057]** | 192 / 189 | **0.918** |

Headline deltas vs baseline: β=1 **+126 hits (+79.7 %)**; β=1/6 **+117 hits (+74.1 %)**.

## 3. Interpretation

**3.1 The perturbation channel carries the whole effect.** With no memory term
at all, R1 still gains +79.7 % at N=1000 with a per-record CI far from zero
(p = 3.8e-08). Nothing about the gain requires the blend.

**3.2 The memory term is bounded, not merely unmeasured.** The β=1 − β=1/6
contrast is +0.009 hits/record with a CI of [−0.041, +0.057] and a sign test at
p = 0.918 (192 up, 189 down — a coin flip). At N=1000 that excludes any memory
contribution larger than **+0.057 hits/record**, i.e. more than ~36 % of the
perturbation effect. The point estimate is 7 % of it. Compare the N=200 screen,
which could only say "a tie in 3/3 seeds"; this says how large the tie can be.

**3.3 This closes the mechanism question that GAP-45 opened, at the headline N.**
GAP-45 §8 found β=0 collapses (0 hits) and β=1/6 vs β=1 ties at N=200. Together
with this run the picture is: the fresh per-record perturbation is necessary and
sufficient; the memory term is optional and worth ≤ 36 % of it.

**3.4 Consequence for the shrinkage mechanism (recorded, not acted on).** β=1
means m = 0, so the operator in GAP-64 has nothing to contract: no blend, no
variance shrinkage. On R1 the framework can therefore sidestep the entire
fidelity-regression mechanism for free. That is an operating point, not a
result — it says the framework's gain on this cell is a *restart* gain, and the
paper must describe it that way. Whether the same holds in the image cells,
where the prior carries real structure, is exactly what GAP-67's design space
has to settle (m = 0 is the limiting case of a covariance-preserving blend, and
it is already a one-line variant).

## 4. What this does NOT establish

- It is **one seed**. It bounds the memory term tightly at this N but does not
  estimate seed-to-seed variability of the bound.
- The novelty metric was not scored (shared-temp collision). K7's novelty
  question is untouched here and is GAP-70's.
- It says nothing about any cell other than R1 at NFE=150.

## 5. Reproduction

```bash
bash reproduce/gap58_r1_beta1_n1000.sh          # seed 42 only, ~5.7 h, cuda:0
D=verification_outputs/gap58-r1-beta1-n1000/seed42
.venvs/lineageflow_venv/bin/python tools/gap55_r1_score_fastas.py \
    --run-dir "$D" --length-bias short --metrics family_validity
```

Artifacts: `verification_outputs/gap58-r1-beta1-n1000/seed42/`
(`baseline.fasta`, `framework.fasta`, `manifest.json`, `upstream_baseline/`,
`upstream_framework/`, `upstream_eval.json`, `score.log`).
