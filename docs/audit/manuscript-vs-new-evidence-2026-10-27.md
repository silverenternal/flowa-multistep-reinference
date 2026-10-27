# Manuscript vs the new evidence — audit, 2026-10-27

**Status:** READ-ONLY audit. No frozen surface was edited.
**Trigger:** GAP-90 (two more checkpoints), GAP-91 (the contraction fit) and
GAP-93 (the beta dose) landed today. This note checks what the manuscript now
says against what the artifacts now show.
**Surfaces read:** `docs/drafts/paper-A-final.tex` (588 lines),
`docs/drafts/paper-A-final.md`, `docs/audit/gap84-inference-frontier.md`,
`scripts/wave191_p3_mnist_sweep.py`, `verification_outputs/gap84-*/`.

Severity is about whether a reviewer holding the repository could falsify the
sentence, not about how bad it sounds.

---

## A. HIGH — the paper cites two different runs without saying so

**Root cause.** There are two seven-rung MNIST grids in the repository:

| run | directory | `--min-steps-per-round` | rung 4 allocation |
|---|---|---|---:|
| uncapped | `verification_outputs/gap84-mnist-frontier/` | 1 (driver default) | `[1,1,1,1]` |
| capped | `verification_outputs/gap84-cap-frontier/` | 2 | `[2,2]` |

They are **bit-identical from rung 10 upward** and differ only at rungs 4 and
5. Verified per checkpoint against
`frontier_<ckpt>_evidence_driven.json` (uncapped) and
`frontier_<ckpt>.json` (capped): every rung from 10 to 200 matches to the last
digit, so every plateau value and the whole κ table are unaffected by the
choice. The two lowest rungs are not — A3 tabulates how they move.

The manuscript, however, mixes them:

* Figure 1 is rendered from the **uncapped** run
  (`tools/render_r5c_frontier_figure.py:46`), and so is the caption's
  "2.3--2.8 FID" penalty at NFE=4 (measured: `production` +2.767,
  `w16e1_60k` +2.322).
* "no rung violates weak dominance on any checkpoint" (§VII-B line 487, §VII-D
  line 550) is true only of the **capped** run. In the uncapped run
  `frontier_production_evidence_driven.json` and
  `frontier_w16e1_60k_evidence_driven.json` both carry
  `dominance.violations = [4]` and `weak_dominance = false`, i.e. the verdict
  fields of the very files the figure reads say **LOSS**, not TIE.

A reviewer who opens `verification_outputs/gap84-mnist-frontier/` finds the
figure, then finds `verdict: LOSS` in the same directory, and the sentence that
contradicts it cites nothing.

The caption is contradicted twice, not once. It also says "on the three
better-trained checkpoints no rung's confidence bound clears the one-FID floor,
so the rung rule returns a tie" (`paper-A-final.tex:65`). In the run the caption
cites, two of those three files carry a rung-4 improvement of **+2.767**
(`production`) and **+2.322** (`w16e1_60k`), whose bounds clear the floor in the
unfavourable direction — that is what `violations = [4]` encodes. Only
`w16e1_10k` ties in the plotted run.

**The register already points at the capped run.** `docs/paper-evidence.json`
(R5c cell) names `verification_outputs/gap84-cap-frontier/frontier_w16e1_5k.json`
as its artifact, and its caveat says "The other three checkpoints are TIEs, not
losses" — true of the capped run and false of the uncapped one. So the split is
not manuscript-vs-artifact but figure-vs-register: the governance surface the
project treats as current has already chosen the capped run, and the figure is
the outlier. That removes the judgement call from A3 — the fix is to make the
figure follow the register, not the reverse. The same cell's `protocol` string
carries A1's "min 2 steps per round" and needs the same one-phrase correction.

### A1. "at least two integration steps per round" is false in both runs

Six source occurrences:

| file | line | context |
|---|---:|---|
| `paper-A-final.tex` | 65 | Figure 1 caption |
| `paper-A-final.tex` | 487 | §VII-B R5c cell |
| `paper-A-final.tex` | 550 | §VII-D R5c frontier |
| `paper-A-final.md` | 21 | Figure 1 caption |
| `paper-A-final.md` | 567 | R5c cell |
| `paper-A-final.md` | 668 | §7.9 R5c frontier |

Realized allocations, read from
`framework_arms.evidence_driven.per_round_num_steps`:

| run | NFE=4 | NFE=5 | NFE=10 | NFE=50 |
|---|---|---|---|---|
| uncapped (Figure 1) | `[1,1,1,1]` | `[2,1,1,1]` | `[5,3,1,1]` | `[25,18,6,1]` |
| capped | `[2,2]` | `[2,3]` | `[5,3,1,1]` | `[25,18,6,1]` |

`effective_rounds` (`scripts/wave191_p3_mnist_sweep.py:283`) is
`min(n_rounds, total_nfe // min_steps)`, so the cap binds only when `NFE < 8`;
above that the round count stays at four and the equal-budget allocator still
gives the last round the residual step. What the cap guarantees is an **average**
of at least two steps per round, never a floor of two in every round.

**Replacement wording, true of either run.**

> seven NFE rungs $\{4,5,10,25,50,100,200\}$ at equal total NFE, with the round
> count capped so the budget averages at least two integration steps per round

### A2. The caption's causal explanation names a floor that is not in the run it plots

`paper-A-final.tex:65` / `paper-A-final.md:21`:

> At 4 NFE the 60k and production checkpoints pay 2.3--2.8 FID for the round
> boundary, **because the two-step-per-round floor leaves no integration budget
> to trade**.

The measured penalty is right for the uncapped run. The cause is not: at NFE=4
that run allocates `[1,1,1,1]` — one step per round, no two-step floor. The
operative cause is that four restarts of a single Euler step cannot integrate a
field the baseline covers in four steps. GAP-84b measured the same thing as
"4 rounds → 2 is worth 2.39 FID" (`docs/audit/gap84-inference-frontier.md:520`).

### A3. The clean fix is to point everything at one run

Switching Figure 1 to the **capped** run makes A2 disappear, makes "no rung
violates weak dominance" true of the plotted artifact, and costs no plateau
number: rungs 10–200 and the plateau are bit-identical, and the figure script's
plateau assertions (`EXPECTED_PLATEAU_DELTA`) still pass because they are
computed from rungs 100 and 200. It is also the run the register already cites,
so the change aligns three surfaces (register, figure, caption) instead of two.

**What switching actually changes in the plot.** Rungs 10–200 and the plateau
are bit-identical, so the plateau annotation, the grey window and the
`EXPECTED_PLATEAU_DELTA` assertions in the figure script are untouched. Rungs 4
and 5 do move, in all four panels:

| checkpoint | rung 4, uncapped → capped | rung 5, uncapped → capped |
|---|---|---|
| `w16e1_5k` | −2.361 → −2.719 | −2.912 → −2.691 |
| `w16e1_10k` | **+0.043 → −0.500** | −0.782 → −0.464 |
| `w16e1_60k` | **+2.322 → +0.503** | +0.243 → +0.520 |
| `production` | **+2.767 → +0.381** | +0.213 → +0.404 |

So the visual claim changes at two of seven points. The ordering is monotone in
training completeness at rung 4 in both runs, so what changes is magnitude and
sign, not shape: the 2.3–2.8 FID cliff on the two best-trained checkpoints
becomes a 0.38–0.50 FID dip, and `w16e1_10k`'s rung-4 value moves from +0.043 to
−0.500. Both changes make the low-NFE behaviour match the caption's own story.
This is still a new figure file with a new hash, not a silent regeneration, and
the caption numbers must be updated with it.

Two edits are then required:

1. The caption's NFE=4 penalty becomes **0.38 FID (`production`) and 0.50 FID
   (`w16e1_60k`)**, not 2.3–2.8, and the "recovered by 10–25 NFE" clause becomes
   unnecessary because there is nothing to recover.
2. A1's wording fix, which is needed either way.

If instead the uncapped run is kept, then the paper has to say that
`production` and `w16e1_60k` are **LOSS** under the rung rule — which is what
their artifacts say — and the R5c verdict stops being "one WIN, three TIEs". The
paper would then be reporting a result worse than the one it currently claims,
in exchange for a figure whose low-NFE panel shows a 2.8 FID cliff at the two
checkpoints the framework is supposed to help. Regenerating the figure is the
cheaper and the more honest option.

## C. MEDIUM — the scope limitation is now contradicted by the dose structure

**Where.** `paper-A-final.tex:584`:

> R5c's four checkpoints still differ in architecture and training-set size as
> well as in training time.

**Observed.** This is the same error that `docs/audit/gap90-optsteps-dose.md`
§1 corrected for the plan, and it survived into the manuscript.

* All four checkpoints the sentence names are width 16. There is no architecture
  difference among them.
* `w16e1_5k` / `w16e1_10k` / `w16e1_60k` are the same architecture, the same
  epoch count and the same 60k-image pool; they differ **only** in how many
  images the trainer saw (`gap35-mnist-regime/aggregate.json`:
  78 / 156 / 937 optimizer steps at 5k / 10k / 60k images).
* `w16e1_60k` / `epochs2` / `production` are the same architecture, the same
  60k images, and differ **only** in epochs (1 / 2 / 3 → 937 / 1,874 / 2,811
  steps).

So the family is two clean one-dimensional doses, not a four-way confound. The
sentence understates the evidence, which is the opposite of the usual failure
mode and is still a defect: a reviewer who reads the artifacts will see the
paper claiming a confound it does not have.

**And GAP-90 adds a control the sentence cannot survive.** `w8e3` is width 8 at
production's 2,811 steps, so the pair (`production`, `w8e3`) is a width contrast
at matched training budget. Measured plateau deltas: `production` −0.0335,
`w8e3` −0.2360. Under the 1-FID floor both are TIE, but the seven-fold ratio at
matched steps is what points the predictor at baseline quality rather than at
step count (§10 of the GAP-90 audit).

**Replacement wording.**

> R5c's checkpoints are two one-dimensional doses — training-set size at fixed
> width and epoch count, and epoch count at fixed width and training set — plus
> one width contrast at production's optimizer-step budget. The residual
> confound is between the doses, not within them.

**The same paragraph also lists completed work as future work.** It ends
`...and vary MNIST training epochs under fixed architecture and data.` GAP-90 is
exactly that experiment: six checkpoints, one architecture family, epochs
1/2/3 at fixed 60k images plus three training-set doses, seven rungs, three
seeds. Leaving it in "Future work" invites the question of why the paper did not
run something it already ran.

---

## D. LOW — "four checkpoints" is now six

**Where.** `paper-A-final.tex:65, 487, 550`; `paper-A-final.md:21, 567, 601,
668, 710, 733, 903`; `paper-A-final.tex:442` and `paper-A-final.md:557` ("four
checkpoints × seven rungs × three seeds").

**Observed.** `verification_outputs/gap90-optsteps-dose/` holds the same
seven-rung grid for `epochs2` and `w8e3`, 42/42 cells, same flags, same seeds,
same $N$. The manuscript's four-checkpoint statements describe the set it
measured and are not false; they are simply one day out of date.

**Why it matters beyond completeness.** The two new points are the ones that
turn "the gain is conditional on the checkpoint" from an observation on four
points into a dose with a measured knee at 156–937 optimizer steps. That is the
strongest form of the paper's central claim and it currently is not in the
paper.

**What would have to change.** Figure 1 would go from 2×2 to 2×3 (or 3×2), the
abstract's "three better-trained checkpoints" would become "five", and §VII-B/D
would carry the dose table. This is a packaging decision, not an audit fix, and
it is user-gated.

---

## E. OPPORTUNITY — the beta objection is now answerable and the paper does not answer it

**Where.** `paper-A-final.tex:73` and `:75` criticise the re-inference family
for "a hand-set or ramp-shaped per-round $\beta$, leaving the loop's behaviour
dependent on operator tuning rather than on the checkpoint's structure".

**Observed.** The paper makes that criticism and then says nothing about its own
$\beta$, which every reported cell fixes at 0.30. That is an open invitation.
`docs/audit/gap93-converged-lever.md` §9 now closes it: on `production`, over
$\beta \in \{0.15, 0.30, 0.50, 0.70\}$ at NFE=50 and at the plateau, the largest
absolute delta anywhere is **0.576 FID** against a 1.0 floor, and 0.30 is the
measured optimum of the dose (the curve is −0.024 / −0.036 / +0.109 / +0.573).

**One sentence that would be true and cheap.**

> The per-round budget is not a free parameter in the reported cells: on the
> converged checkpoint a four-level $\beta$ dose at both the NFE$=50$ budget and
> the plateau moves the FID by at most 0.58, against the one-FID floor, and the
> reported $\beta=0.3$ is the measured optimum of that dose
> (\texttt{verification\_outputs/gap93-beta-dose/}).

It also sharpens the differentiation: the criticism of prior work is that
$\beta$ is *hand-set and unmeasured*, not that a $\beta$ exists.

---

## F. What the audit found to be correct

Checked against artifacts and found accurate, so they are not at risk of a
correction pass:

* The `w16e1_5k` plateau 24.4839 → 21.3632 (−3.1206, −12.75 %), weakly dominant
  at 7/7, strict at 7/7 — `gap84-mnist-frontier/frontier_w16e1_5k_evidence_driven.json`.
* `w16e1_10k` −1.0036 with a CI lower bound of 0.984 FID — same file.
* `w16e1_60k` +0.0150 and production −0.0335 — same file.
* The kappa table's four rows and the statement that kappa is computed at
  NFE=50 while the delta is at the 100–200 plateau — `gap92-kappa-bridge.md`.
* "Only R5c carries a full (quality, NFE) grid" — no other R-level headline
  artifact sweeps NFE. R6's 20-cell grid varies `easy_factor` / `hard_intensity`
  at fixed budget (`wave235-p3-r6-uplift.json`); R5b contrasts round counts at a
  single budget (`06_R5b_CIFAR_n_rounds1.sh`, `wave235-p1-r5b-fix.json`); and
  R1/R2/R3/R5a report one budget each.
* "weakly dominant at all seven rungs and gains strictly at 7/7" on
  `w16e1_5k` — `dominance.strict_gain_rungs = [4,5,10,25,50,100,200]`,
  `violations = []`, in both runs.
* `w16e1_10k`'s rung deltas (−0.78 to −1.005 from rung 5 up) and its
  improvement CI lower bound of 0.984 FID, which is why it is a TIE and not a
  WIN — the numbers are right; only the "no rung violates" sentence is
  run-dependent (finding A).
* The claim that `epochs2`'s only violation is rung 4 — GAP-90 §11 shows it
  disappears under the cap, which is the same mechanism as finding A.

---

## G. Recommended order, if the user authorises manuscript edits

**Every item below makes the paper stronger, not weaker.** The test applied to
each: does the edit move a verdict up, remove a self-inflicted limitation, or
replace an unmeasured statement with a measured one?

1. **A and A1–A3 together.** The paper already says "the three better-trained
   checkpoints tie" (`paper-A-final.tex:487`, `:550`) and the abstract already
   says "returns a tie on three better-trained checkpoints" (`:49`). In the run
   the figure plots, two of those three are `LOSS`. Pointing the figure at the
   capped run — the run the register already cites — makes the paper's existing
   sentence true. Concretely:

   | | uncapped (current figure) | capped (register) |
   |---|---|---|
   | R5c verdicts | 1 WIN, 1 TIE, **2 LOSS** | 1 WIN, **3 TIE** |
   | NFE=4 penalty, 60k / production | +2.32 / +2.77 FID | **+0.50 / +0.38 FID** |
   | plateau Δ, all four checkpoints | unchanged | unchanged |

   No number in the body changes. The caption's 2.3–2.8 becomes 0.38–0.50, which
   is below the one-FID floor and therefore reads as "the round boundary is
   nearly free at this checkpoint", not as a cliff. A1's protocol phrase is a
   correction of a false statement and is neutral to the result.

2. **C.** One sentence in §IX. It deletes a limitation ("checkpoints differ in
   architecture and training-set size") that the artifacts show is false, and it
   stops listing a completed experiment as future work. Strictly additive
   evidence, strictly subtractive limitation.

3. **E.** One sentence in §VII. It answers an objection the paper itself raises
   against prior work, with a measurement already on disk, and the answer
   favours the reported operating point (β=0.30 is the measured optimum).

4. **D.** The packaging decision. This is the only item that adds new evidence
   to the body: two more checkpoints, a measured knee at 156–937 optimizer
   steps, and a width contrast at matched budget. It requires a new figure, a
   new table and a 12-page rebuild, so it is a separate decision.
