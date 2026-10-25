# GAP-79 — R1 per-family lever: the ceiling says the problem is strength, not columns

**Date:** 2026-10-25
**Author:** GAP-79 agent (USER AUTHORIZED, NO PUSH)
**Scope:** `todo.json` `GAP-79-R1-PER-FAMILY` (P0). Pre-registration is §0;
the measurement that re-scoped the gap is §1. **No framework run exists yet.**
**Frozen surfaces:** untouched.

---

## 0. Pre-registration (written before any run of the new lever)

### 0.1 What GAP-69 established

Three seeds, N = 1000: the conservation-weighted init raises `hmmscan_total_hits`
8.20× / 8.06× / 8.46× over the init-only arm, and the gain is one family —
PF00005 27.81× / 40.90× / 31.61× (3/3), PF00072 0.85 / 0.74 / 0.78 (0/3),
PF00183 0.81 / 0.87 / 0.73 (0/3), PF02517 1.07 / 1.10 / 1.42 but with every
per-seed CI including 0. Excluding PF00005: 0.908 / 0.895 / 0.920.
Verdict: `HEADLINE_GAIN_NO_FAMILY_IDENTITY`.

### 0.2 The plan GAP-79 inherited, and why it is being replaced before coding

`todo.json` says: perturb the **discriminative** columns (those separating the
family from its nearest Pfam neighbours) instead of the conserved ones.
§1 below measures the ceiling and shows that this lever cannot work: the
profile is already discriminative enough at full length to be recognised at
E = 1e−33…1e−255, and the generated sequences are not recognised at all. The
loss is not in *which* columns are used. Writing the discriminative-column tool
would have been a day of code aimed at the wrong stage.

**This is an amendment to the gap's lever, not to its acceptance test.** The
acceptance stays exactly as `todo.json` states it: every family's paired CI
must exclude 0 in the improving direction, at 3 seeds, N = 1000, no seed
top-ups.

### 0.3 The replacement lever: init strength, as a pre-registered dose

The GAP-69 init is

```
logits[i] = c_i * log p_i + (1 - c_i) * randn(AA)
```

with `c_i` the column's normalised information content. The measured mean of
`c` is **0.17–0.18 for all four families** (§1.2), so ~83 % of the init's logit
variance is noise. The ODE then integrates 150 steps with a velocity field
trained on real proteins, and the argmax of its output is the sequence. A weak
profile seed is exactly what a trained field would smooth away.

Dose family (fixed here, before any run):

```
c'_i(alpha) = min(1, alpha * c_i),   alpha in {1, 2, 4, 8}
```

`alpha = 1` is byte-identical to GAP-69's arm C. The dose is monotone and has
no per-family tuning: one `alpha` is chosen for all four families, exactly as
GAP-78's `beta = 0.3` was one value for all four checkpoints.

> **Superseded by §0.3b before any run.** The weight dose was replaced by a
> temperature on the profile term; the monotone, one-value-for-all-four rule
> is unchanged.

### 0.3b Superseded before any run: the dose is a temperature, not a weight

§0.3's `c' = min(1, alpha*c)` was replaced **before any generation run**,
because its own limit is an already-measured arm: as `alpha -> inf` the draw
becomes "sample from `p`", which is GAP-69's arm D, and arm D scores
**0/250** intended hits on PF00072, PF00183 and PF02517 (§1.2). A dose whose
endpoint is a known failure cannot be the lever that fixes the endpoint.

The replacement keeps the profile's *shape* and changes only its *weight
against the noise*:

```
logits[i] = (c_i * log p_i) / T + (1 - c_i) * randn(AA),   T in {0.5, 0.2, 0.1, 0.05, 0.02}
```

`T = 1` is byte-identical to GAP-69's arm C (asserted in
`tests/test_gap69_conservation_perturbation.py`). As `T -> 0` every column
with `c_i > 0` becomes the profile's argmax — the configuration the family's
own HMM recognises at 1e−33…1e−255 (§1.1) — while `c_i = 0` columns stay a
plain draw, so the init never collapses to a single sequence. Dividing the
**whole** logit row instead would be a monotone transform of each row: same
argmax, less sampling diversity, no change of mode. It would look like a dose
and behave like a no-op, so it is explicitly not what is implemented.

Reading §0.4 below: `alpha = 1/T` (smaller `T` = larger dose).

### 0.4 Decision rule

1. **Screen (N = 200, seed 42, `SCREEN_ONLY`).** For each dose, record
   `intended_hit_evalue` and `hmmscan_total_hits` per family. A screen number
   may choose the dose; it may never be quoted (§0.3 of GAP-84, and the MNIST
   small-N bias does not apply here but the principle does). The table is
   produced by `tools/gap79_dose_screen.py` from the per-record jsonl, so it is
   re-derivable without re-scoring; the run itself is
   `reproduce/gap79_temperature_screen.sh`.
2. **Dose selection.** Pick the **smallest** dose (`T` closest to 1) at which
   PF00072 and PF02517 each reach a non-zero intended-hit rate on the screen,
   subject to PF00005 not losing its hits. If no dose does that, the lever is
   falsified and GAP-79 closes with that result.
3. **Confirmation (N = 1000, seeds 42/43/44).** WIN requires, for **every**
   family, a paired per-record CI on `intended_hit_evalue` that excludes 0 in
   the improving direction, **and** PF00005 not regressing. Aggregate hits are
   reported but are not the acceptance test.
4. **No seed top-ups.** Three seeds, as pre-registered.

### 0.5 Declared boundaries

* PF00183's HMM is **518 columns**; the record-length distribution is 30–150 aa.
  A 518-column domain cannot be represented in a 150-aa sequence. Whatever the
  dose does, PF00183 cannot clear the per-family condition by this lever. That
  is a property of the task's length distribution, not of the framework, and it
  will be stated as a boundary **in the same table as the result**, not in a
  discussion.
* L1 (positional, no aligner) is inherited from GAP-69 and is not fixed here.
* The lever changes the *init*, not the ODE, the decode, or the checkpoint.

---

## 1. The ceiling measurement that re-scoped the gap (2026-10-25)

Everything here is CPU and uses the vendored `Pfam-A.hmm` read-only. `hmmscan`
is `/home/hugo/hmmer_build/bin/hmmscan`, invoked exactly as the upstream
evaluator does (`--noali --acc --tblout`), E-value threshold 0.001.

### 1.1 The profile consensus is recognised at every length

Consensus = argmax of each match-emission row of the family's HMM.

| family | M | full-length self-hit E | 60-aa prefix | 90-aa prefix | 120-aa prefix |
|---|---:|---:|---:|---:|---:|
| PF00005 | 137 | 9.8e−58 | 3.8e−22 | 1.1e−33 | 2.9e−47 |
| PF00072 | 111 | 6.0e−48 | 1.1e−24 | 3.2e−37 | — |
| PF00183 | 518 | 2.4e−255 | 3.2e−16 | 5.6e−29 | 9.4e−45 |
| PF02517 | 93 | 9.1e−33 | 3.2e−18 | 3.9e−31 | — |

Every family's own model recognises its consensus, including a 60-aa prefix.
**The profile is not the problem, and neither is the length.**

### 1.2 The generated sequences are not recognised, and the init is mostly noise

Per-family `intended_hit_evalue` rate, N = 250 records/family, seed 42:

| arm | PF00005 | PF00072 | PF00183 | PF02517 |
|---|---:|---:|---:|---:|
| A baseline | 0.000 | 0.000 | 0.000 | 0.000 |
| B init-only | 0.000 | 0.000 | 0.000 | 0.000 |
| C conservation (GAP-69) | 0.160 | 0.000 | 0.000 | 0.000 |
| D pure profile draw, no model | 0.240 | 0.000 | 0.000 | 0.000 |

Mean normalised information content `c` (the init's profile weight):
PF00005 0.178, PF00072 0.176, PF00183 0.168, PF02517 0.174.

So: the same profile whose consensus scores 1e−33…1e−255 produces sequences
that score below threshold, and the init is ~17 % profile / 83 % noise. Arm D
shows this is not the model's fault — even a pure draw from the profile, with
no ODE, fails on the three families, because sampling at ~24 % identity to the
consensus is not a domain.

### 1.3 Consequence

The lever must make the init closer to the profile, not choose different
columns. That is §0.3's dose. The two things that would falsify it: (a) no
`alpha` produces a non-zero intended rate for PF00072/PF02517 on the screen;
(b) the dose raises them but PF00005 collapses, which would mean the families
are in tension and one init cannot serve both.

---

## 2. Status

| item | state |
|---|---|
| §0 pre-registration | written before any run of the dose |
| §1 ceiling diagnostic | done, CPU, this document |
| discriminative-column tool | **not built — the lever it implements is falsified in §1** |
| dose knob | implemented as `--init-temperature` (profile-term temperature, §0.3b; commit `5afe3935`) |
| screen (N = 200, 5 doses) | **RUNNING** since 2026-10-25T04:43Z (`reproduce/gap79_temperature_screen.sh`, PAR=3, GPU-bound) |
| screen table | `tools/gap79_dose_screen.py` + 6 tests (`f51cffb4` run script) |
| confirmation (N = 1000, 3 seeds) | not run — only the selected dose goes there |
| verdict | deferred until the screen reports |
