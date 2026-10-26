# GAP-79 — R1 per-family lever: the ceiling says the problem is strength, not columns

**Date:** 2026-10-25
**Author:** GAP-79 agent (USER AUTHORIZED, NO PUSH)
**Scope:** `todo.json` `GAP-79-R1-PER-FAMILY` (P0). Pre-registration is §0;
the measurement that re-scoped the gap is §1; the temperature screen is §2.1;
the lever-3 pre-registration is §3 (written before its first run).
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
| screen (N = 200, 5 doses) | **done** 2026-10-25, 5/5 cells (`reproduce/gap79_temperature_screen.sh`, seed 42) |
| screen table | `tools/gap79_dose_screen.py` + 6 tests (`f51cffb4` run script) |
| confirmation (N = 1000, 3 seeds) | **not run — no dose qualified**, so there is nothing to confirm |
| verdict | **`falsified: true`** — the init-strength lever moves hits, not identity (§2.1) |
| lever 3 code | `ProfileGuidance` in `adaptive_reflow/adapters/lineageflow.py`; `--profile-guidance-weight` / `--profile-guidance-t-start` in `tools/gen_lineageflow_n1000_fastas.py`; 17 tests in `tests/test_gap79_profile_guidance.py` |
| lever 3 pre-registration | **§3, written 2026-10-25 before any run** (dose grid `{0.5, 2, 8, 32, 128}`, `t_start = 0`, diversity guard) |
| lever 3 screen tool | `tools/gap79_guidance_screen.py` + 11 tests (`tests/test_gap79_guidance_screen.py`) |
| lever 3 screen run | **not run** — `reproduce/gap79_profile_guidance_screen.sh` (6 cells, N = 200, seed 42, ~2 h) |
| lever 3 verdict | **pending**; §3.7 states what falsification would mean |

### 2.1 The screen result: the lever is real and points at the wrong thing

`verification_outputs/gap79-r1-temperature/screen_report.json`
(`selected_temperature = null`, `falsified = true`). N = 200 per dose, seed 42,
50 sequences per family. `rate` is the fraction of a family's own 50 sequences
that hit that family's HMM.

| T | fw hits | fw coverage | PF00005 | PF00072 | PF00183 | PF02517 | top-1 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.02 | 1339 | 0.665 | 1.00 | 0.00 | 0.00 | 0.00 | 0.250 |
| 0.05 | 1314 | 0.630 | 1.00 | 0.00 | 0.00 | 0.00 | 0.250 |
| 0.10 | 1214 | 0.585 | 1.00 | 0.00 | 0.00 | 0.00 | 0.255 |
| 0.20 | 1191 | 0.545 | 1.00 | 0.00 | 0.00 | 0.00 | 0.245 |
| 0.50 | 915 | 0.465 | 0.90 | 0.00 | 0.00 | 0.00 | 0.210 |
| baseline | 37 | 0.150 | 0.00 | 0.00 | 0.00 | 0.00 | 0.000 |

**The mechanism read is positive.** Temperature is a genuine dose on the
profile term: as T falls 0.50 → 0.02, `hmmscan_total_hits` rises monotonically
915 → 1339 (baseline 37, i.e. 24.7× → 36.2×) and `coverage_any_hit` rises
0.465 → 0.665 (baseline 0.150). Sharpening the init does exactly what §0.3b
said it would: it makes the generated sequences more protein-like to HMMER.

**The identity read is dead.** Not one of the three failing families moves off
0/50 at any dose, and PF00005 — the family that already worked — is the only
one that ever fires. `top1_family_accuracy` is pinned at the 0.25 that one
family out of four implies. Per §0.4 rule 2 the required families (PF00072,
PF02517) must each leave 0 with PF00005 held; that never happens, so no dose is
eligible and the lever is falsified as an identity lever.

**What this means for the gap.** GAP-69's 8× hit gain is one family, and
sharpening the same init by 25× in temperature does not spread it. The binding
constraint is therefore not the *strength* of the profile signal at the init —
it is already strong enough to lift total hits by an order of magnitude and to
move coverage by 0.5 absolute. Whatever makes PF00072 / PF00183 / PF02517
unreachable lives downstream of the init: either the family's own HMM is not
representable by a single-profile perturbation of a shared consensus, or the
sampler destroys the per-family signal after the init. The next lever has to be
chosen against that, and §0.2's discriminative-column plan is falsified for the
same reason (it is still an init-column lever).

The screen is N = 200 and is therefore **screen-only** — none of the numbers in
the table may be quoted as a result (`screen_report.json.note`). It is used here
only to select a dose or to close the lever, which is what §0.4 authorises.

---

## 3. Pre-registration for lever 3 — in-loop profile drift (written before any run)

**Date written:** 2026-10-25, before any generation with
`--profile-guidance-weight > 0`. **Nothing in this section may be edited after
the first dose is scored**; results go in §4.

### 3.1 Why this placement and not another restart-side one

`apply_restart_distribution` calls `perturbation.propose` at **every** restart
(`adaptive_reflow/adapters/lineageflow.py`, the `_seeded_propose` branch), so
"put the profile at every restart" is already the shipped behaviour and §2.1's
temperature dose sharpened that injection by up to 25×. Both readings are flat
on identity. What has never been tried is a force applied *during* the
integration that follows the injection — the only stage that can undo it.
That is the entire justification for this lever; it is not another init knob.

### 3.2 The term

```
v_guided(x, t) = v(x, t) + weight * c * (p - x)        for t >= t_start
```

* `p` is the family's Pfam match-emission distribution (row-normalised), `c`
  its normalised information content — the same tensors GAP-69's
  `ConservationWeightedPerturbation` uses, loaded from the same
  `profiles.json`.
* `c = 0` columns do not move; positions past the profile's span do not move;
  channels past the amino-acid block do not move (state is `(256, 33)`,
  profile is `(150, 20)`).
* The drift is the proximal form of `-KL(p || x)` ascent: fixed point `x = p`,
  sign always toward `p`. The exact KL gradient `-p/x` is unusable as a
  velocity near `x = 0`.
* `weight = 0` is byte-identical to the unguided field (pinned by
  `tests/test_gap79_profile_guidance.py`).

**Arm definition.** Treatment = GAP-69 arm C (`--init-profile conservation`,
`T = 1.0`) **plus** the drift. Control = the same arm without the drift. The
incumbent init is kept in both arms so the comparison isolates the downstream
force. A guidance-only arm (`--init-profile off`) is deliberately **not** run:
it answers a different question and would double the cells.

### 3.3 Dose grid

`t_start = 0.0` (whole trajectory) is fixed for the screen. `weight` is the
only axis:

```
weight in {0.5, 2, 8, 32, 128}
```

Scale check, done analytically before the run: `dt = 1/150`, mean `c = 0.17`,
`|p - x| <= ~1.4`, so the per-step displacement is `~0.24 * weight * dt`; over
a half-horizon `weight = 1` moves a position by `~0.08` in probability, i.e.
the same order as the field itself. The grid brackets that by 0.5× to 128×,
and 128 is a deliberate **collapse probe**: if identity only moves when the
drift dominates the field, the lever is "replace the model with the profile",
which §1.2 already measured (arm D, 0/250 on three families).

### 3.4 Screen (N = 200, seed 42, `SCREEN_ONLY`)

Six cells: one control + five doses. Generation may run concurrently; scoring
is serial (shared MMseqs2 temp dir). Script:
`reproduce/gap79_profile_guidance_screen.sh`. Table produced by
`tools/gap79_guidance_screen.py` reading the per-record jsonl plus the FASTAs
(the diversity guard needs the sequences, not the hit flags).

A dose is **eligible** iff all four hold:

1. `PF00072` intended-hit rate ≥ 1/50 (i.e. leaves 0).
2. `PF02517` intended-hit rate ≥ 1/50.
3. `PF00005` rate ≥ control − 1/50 (no collapse of the family that works).
4. **Diversity guard:** unique-sequence fraction ≥ 0.95 **and** mean
   per-position entropy ≥ 0.5 × control. A dose that lifts identity by emitting
   near-copies of the consensus is not eligible — that is arm D wearing a
   velocity term, and it would die on K7 novelty.

Select the **smallest** eligible weight (least intervention). If none is
eligible, lever 3 is **falsified** and GAP-79 closes with all three placements
falsified — *provided the target is a valid family member*; §3.8 records the
round-1 target defect that voids this clause for that run.

Screen numbers may choose the dose; they may never be quoted.

### 3.5 Confirmation (N = 1000, seeds 42/43/44)

Only the selected weight runs. WIN requires, for **every** family, a paired
per-record CI on `intended_hit_evalue` that excludes 0 in the improving
direction, **and** PF00005 not regressing, **and** the §3.4 diversity guard
holding at N = 1000. Aggregate `hmmscan_total_hits` is reported but is not the
acceptance test. Three seeds, no top-ups.

### 3.6 Correction to §0.5 (recorded before any lever-3 run)

§0.5 declared PF00183 structurally out of reach because its HMM is 518 columns
and records are ≤ 150 aa. §1.1 contradicts the *strong* form of that claim: a
120-aa prefix of the same consensus scores **9.4e−45**, so a partial domain is
recognised and PF00183 is not hit-impossible. The boundary is on *full-domain*
coverage, not on recognisability, and PF00183 therefore **stays in the
acceptance set** of §3.5. §0.5's sentence is superseded by this paragraph; its
L1 caveat stands.

### 3.7 What falsification would mean

If all five weights fail, then for this profile and this checkpoint the
identity gap is not a *placement* problem: injecting the profile at the init,
sharpening it 25×, and pulling the trajectory toward it for the whole
integration all fail to move three of four families. The remaining
explanations are representational (a single global profile cannot encode a
family the shared prior has no mode for) and would need a different family
conditioning path, not another scalar knob. That is the honest closing
statement — it is not a claim that the framework cannot do the task.

### 3.8 F3 — the round-1 target was not a family member (recorded after round 1, before round 2)

Round 1 (2026-10-25, `verification_outputs/gap79-r1-guidance/seed42/`, git
`9dc35080`) returned no eligible dose: `PF00072` and `PF02517` stayed at 0/50
at every weight while the guard family `PF00005` went 8/50 → 50/50 at
`weight = 2`. That pattern is not what a live lever looks like, and it is not
what a dead lever looks like either — it is what a **broken target** looks
like. The drift was pointing at `verification_outputs/gap69-lineageflow-profile/profiles.json`,
whose `logp` is the GAP-69 **150-slot resample** of each HMM
(`tools/pfam_profile.py::resample`, slot `i` → column
`round(i·(M−1)/149)`).

The four families have `LENG` 137 / 111 / 518 / 93. For `M < 150` the
resample **duplicates** columns; for `M > 150` it **drops** them. The argmax of
a resampled profile is therefore a stretched or gappy sequence, not a family
member. Measured directly with the evaluator's own `hmmscan` call
(`--evalue 1e-3 --no-cut-ga`), on the pure argmax consensus of each profile:

| family | `LENG` | native consensus (top1 / E) | 150-slot resample (top1 / E) |
|---|---|---|---|
| PF00005 | 137 | PF00005 / 9.8e−58 | PF00005 / 8.7e−36 |
| PF00072 | 111 | PF00072 / 6.0e−48 | PF12363 / 0.068 — **no hit** |
| PF00183 | 518 | PF00183 / 2.4e−255 | *(no hit at all)* |
| PF02517 | 93 | PF02517 / 9.1e−33 | PF03384 / 1.4 — **no hit** |

The native consensus of each family is recognised at E ≤ 1e−32; the resampled
one is recognised **only for `M ≈ 150`** (PF00005, 137 → 150, 13 duplicated
columns). So a drift toward the resampled profile can only ever help the one
family whose length is already near the span — exactly the observed asymmetry.
The mechanism itself worked: mean per-position agreement between the output
and the (resampled) target rose from 0.20–0.25 at control to 0.78–0.88 at
`weight = 8` and 0.96–0.99 at `weight = 32`. The drift converged; it converged
onto a sequence the HMM does not recognise.

Round 1 is therefore **not** evidence about lever 3, and §3.4's "no eligible
dose ⇒ falsified" clause is **not** triggered — the same distinction GAP-80
drew between F1/F2 (harness defects) and a measured null.

**Fix (additive, defaults unchanged).** `tools/pfam_profile.py --span 0` keeps
each family's native `LENG` and writes `"resample": "none"`; the 150-slot
default is untouched, so every GAP-69 artifact and the pre-registered arm C
init stay byte-identical. The drift target is now a separate argument
(`--profile-guidance-json`, plumbed through
`reproduce/gap69_profile_init.sh` as `GUIDANCE_PROFILES`), so the init prior
and the drift target can differ without a second code path. The manifest
records `profile_guidance_profile_json` and the per-family
`profile_guidance_profile_span`, so a cell can never again be ambiguous about
which target it used. Round 2 re-runs the identical §3.4 screen at
`verification_outputs/gap79-r1-guidance/native/seed42/`; round 1's artifacts
are kept as the record of F3.

One consequence is worth stating because it is not repaired by this fix: the
drift is positional (`profile column i ↔ state position i`, §0.5 L1), and
generation length is not controlled (round 1 mean 86–92 aa). For `PF00183`
(`LENG` 518) the first 90 state positions cover 17 % of the domain; a native
target cannot make that a full-domain match, only a recognisable partial one
(§3.6). The fix removes the *invalid-target* confound; it does not remove the
coverage boundary.

## 4. Round 1 screen (2026-10-25) — VOID (F3), kept as the record

Six cells, N = 200, seed 42, NFE = 150, R = 3, `beta = 1.0`, arm C init
(`conservation`, T = 1.0), `t_start = 0.0`, weights
{0.5, 2, 8, 32, 128}. Artifacts:
`verification_outputs/gap79-r1-guidance/seed42/` (git `9dc35080`); the table
below is `tools/gap79_guidance_screen.py` on those artifacts.

| cell | PF00072 | PF02517 | PF00183 | PF00005 (guard) | unique | mean H | eligible |
|---|---|---|---|---|---|---|---|
| control | 0/50 | 0/50 | 0/50 | 8/50 | 1.000 | 3.77 | — |
| W0.5 | 0/50 | 0/50 | 0/50 | 39/50 | 1.000 | 3.55 | no |
| W2 | 0/50 | 0/50 | 0/50 | 50/50 | 1.000 | 3.09 | no |
| W8 | 1/50 | 0/50 | 0/50 | 50/50 | 1.000 | 2.23 | no |
| W32 | 0/50 | 0/50 | 0/50 | 50/50 | 0.955 | 1.73 | no |
| W128 | 0/50 | 0/50 | 0/50 | 50/50 | 0.810 | 1.70 | no |

`selected_weight: null`, `falsified: true` in the tool's output — **but §3.8
shows the target was not a family member for three of the four families, so
this table is a measurement of F3, not of lever 3.** Two readings survive it:

* The drift is mechanically real and dose-monotone: agreement with the
  (resampled) target rises 0.20–0.25 → 0.78–0.88 (W8) → 0.96–0.99 (W32).
* The diversity guard bites at the top of the grid, not in the middle:
  `W32` still holds unique ≥ 0.95 but entropy is already 0.46× control;
  `W128` fails both (0.810, 0.45×). Any eligible dose therefore has to sit at
  or below `W8`, which is where round 2's eligible set will be read.

Round 2 re-runs §3.4 unchanged against the native target and writes
`verification_outputs/gap79-r1-guidance/native/seed42/`; its §4.1 replaces the
verdict above.
