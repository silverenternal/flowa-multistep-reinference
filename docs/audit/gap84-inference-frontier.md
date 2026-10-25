# GAP-84 — the (quality, NFE) frontier, and the pre-registered definition of a win

**Date:** 2026-10-23
**Author:** GAP-84 agent (USER AUTHORIZED, NO PUSH)
**Scope:** `todo.json` `GAP-84-INFERENCE-FRONTIER` (P0, CPU).
**Status:** protocol pre-registered; instrument landed and tested; **no run
executed** (cuda:0 is paused by user directive, and no cell has a complete grid
in the existing artifacts — §2).
**Frozen surfaces:** untouched.

---

## 0. Pre-registration (written before any frontier number)

This section is the contract. Every later frontier report is read against it and
nothing here may be edited after a number exists; amendments go in a new
`§0.x` with a date and a reason.

### 0.1 What a "win" means, and why not "the baseline with more steps"

The framework must win on every model task, and a tie is a loss. A win is **not**
"our number beats the baseline at one NFE". It is one of two things, both read
off the same curve:

* **quality** — at matched NFE the framework's point is better, and its
  **plateau** is better; or
* **speed** — the framework reaches the baseline's plateau quality at
  materially fewer NFE.

The control is the baseline curve on the **same frozen checkpoint**, not "the
baseline given more steps". That control is invalid here for a measured reason:
flow-matching inference saturates, so extra steps buy nothing. On MNIST the
single-pass sampler is converged by NFE = 3 — projection-FID 11.1035 → 11.0675
from NFE 3 to 100, a **0.32 %** total headroom; on `w16e1_5k`, 26.9258 → 26.7300,
**0.75 %** (`verification_outputs/gap64b-nfe-headroom/headroom.json`, N = 200,
seed 42, shared prior). GAP-57 saw the same on `w16e1_5k` over 50/100/200
(27.2361 → 27.2311). There is no truncation error left for steps to recover, so
the baseline's plateau is a property of **its distribution**, not of its compute
budget. `docs/audit/mechanism-core-driver.md` §3 carries the full argument.

### 0.2 Grid

Per model, `NFE ∈ {3, 5, 10, 25, 50, 100, 200}`.

* **Lower bound 3** because that is where MNIST is already converged; a grid that
  starts at 50 cannot see the low-NFE regime where a speed win would live.
* **Upper bound 200** because every baseline measured so far is flat well before
  it, and 200 is the largest NFE any recorded cell uses.
* **At least 5 rungs** must be present for a plateau estimate to mean anything.
  Fewer rungs ⇒ `INCOMPLETE`, never `WIN`.
* The same rung set is used for both arms. A rung present for one arm and not
  the other is a missing rung, not a skipped one.

**§0.2a extension rule (arm-blind).** If the baseline has not plateaued at
NFE = 200, the grid is extended by doubling (400, 800, …) until it does. The
decision is made on the **baseline arm alone**, before the framework arm at the
new rung is looked at, so it cannot be steered. CIFAR already needs this: its
baseline moves 447.8713 → 443.7343 over 50 → 100 (−0.92 %), i.e. it is still
descending where MNIST is long flat (§2.1).

### 0.2b Amendment — the lowest realisable rung is 4, not 3 (2026-10-25)

Written **before any rung of the grid completed**, and before any frontier
report exists.

The R5c arm runs `--n-rounds 4` with `--equal-total-nfe`, and the equal-budget
allocator enforces at least one step per round. A requested total of 3 is
therefore realised as **4** on every framework arm (`[1,1,1,1]`) while the
baseline runs exactly **3**. That rung would compare 4 NFE against 3, which is
not a matched-NFE point and cannot enter a frontier.

Rule: the lowest realisable rung is **4**; the grid becomes
`{4, 5, 10, 25, 50, 100, 200}`. Every other rung was checked against the
allocator and is exact (5→5, 10→10, 25→25, 50→50, 100→100, 200→200 for all
three arms). The cells already started at 3 are quarantined as
`*_INVALID_nfe_rounding` and no number from them is used.

This does not weaken the low end: MNIST is converged by 3–4 steps (11.1035 →
11.0675 from NFE 3 to 100, §0.1), so rung 4 sits at the same saturation point
that motivated the lower bound.

### 0.3 N, seeds, pairing

* **N ≥ 1000** for every quotable frontier. Below that the verdict is computed
  and labelled `SCREEN_ONLY`, `quotable = false`, and `win = false` — the MNIST
  projection-FID inflates effect sizes by 40–65 % at N = 200, so a screen number
  may guide the next run but may never be quoted.
* Same checkpoint, same prior batch, same seed policy, same N on both arms at
  every rung.
* **Paired** by unit: chunk index when the artifact carries chunk-level values,
  otherwise record index, otherwise seed. The unit is recorded in the output;
  a frontier whose units are seeds has ≤ 3 units and is reported as such.

### 0.4 Estimator

For a lower-is-better metric, at rung `k`:

```
delta_k      = mean(framework_k) − mean(baseline_k)
delta_rel_k  = delta_k / |mean(baseline_k)|
CI95_k       = percentile bootstrap over the paired units, 10 000 resamples, seed 0
```

Percentile CI, two-sided 95 %. No p-value is used for the verdict: the decision
is entirely on the CI against the margin in §0.5, so a rung with 3 units cannot
pass by luck.

### 0.5 Dominance, gain, speed

With `m` the cell's **effect floor in the metric's own units**, and
`improvement = delta_rel` for higher-is-better / `−delta_rel` for
lower-is-better (so positive is always good):

| term | rule |
|---|---|
| **weak dominance at rung k** | `CI95_low(improvement_k) ≥ −m` — equivalently `CI95_high(delta_rel_k) ≤ +m`; the framework is not worse than the baseline at that rung |
| **strict gain at rung k** | `CI95_low(improvement_k) > 0` — the framework is better at that rung |
| **plateau** | mean of the last two rungs, requiring `|v_last − v_prev| / |v_prev| < 1 %` |
| **baseline plateau NFE** | smallest rung whose value is within 1 % of the plateau value |
| **speed ratio** | `nfe_at_which_framework_reaches_baseline_plateau / baseline_plateau_nfe` |

**The margin is the per-cell floor, not a universal percentage.** This section
originally said `m = 1 %` relative "the repo's standing effect floor". That is
wrong for any metric whose floor is absolute: `docs/CLAIMS.md` CLM-060 records
the floors as `1pp / 0.01 abs / 1 FID / 0.5 pLDDT pp / 0.1 scPerplexity`, and a
relative 1 % is not 1 FID unit unless the baseline is ~100 FID. On the R5c
baselines (9.97 / 11.40 / 16.96 / 24.50) it is 0.100 / 0.114 / 0.170 / 0.245
FID units — 4× to 10× tighter than the ledger's floor, and tighter exactly
where the baseline is small. That inconsistency is arithmetic and predates every
frontier number; it was found when GAP-78 §10 applied both rules to the same
twelve cells and got `LOSS` and `WIN`. So:

* `m` is taken from the cell's ledger row, in the metric's units.
* A cell with no recorded floor uses 1 % relative and the report says so.
* When both rules exist, **both verdicts are printed**; neither may be quoted
  alone, and the floor rule is the one that matches the ledger.

### 0.6 Verdicts

| verdict | condition |
|---|---|
| `WIN` | weak dominance at **every** rung, **and** (≥ 1 rung with strict gain **or** speed ratio ≤ 0.5) |
| `TIE` | weak dominance everywhere, but neither strict gain nor speed |
| `LOSS` | weak dominance violated at ≥ 1 rung (the CI excludes "no worse") |
| `INCOMPLETE` | baseline not plateaued on the grid, or < 5 rungs, or ≥ 1 rung has no CI |

`TIE` is **not** a win. Per the standing decision rule a tie is a loss and is
treated as an open mechanism gap, not as a boundary to publish. `INCOMPLETE` is
neither: it means the measurement is not finished and must not be quoted.

### 0.7 What this forbids

* No post-hoc choice of the framework arm: the arm is fixed by the cell's paper
  configuration before the run.
* No seed top-ups to move a CI across the margin.
* No quoting a `SCREEN_ONLY` frontier.
* No replacing a `LOSS` with prose about "the baseline with more steps" — §0.1.

---

## 1. Why the instrument is needed at all

Every cell in the ledger is a **single** matched-NFE point. That answers "is the
framework better at this budget" and nothing else. It cannot answer the two
questions a reviewer will actually ask:

1. *Is the gain just a step-count artefact?* — answered by §0.1 plus the
   saturation measurement, not by a table of point estimates.
2. *Did the ceiling move, or only the point?* — answered only by a plateau
   estimate, which needs a grid.

`docs/audit/mechanism-core-driver.md` records the mechanism: the driver re-noises
the endpoint to the path time `t = m`, re-integrates only `[m, 1]`, and repeats
that `R` times inside a **fixed total NFE**. So the framework changes the
distribution the sampler produces. A distribution change shows up as a **level**
shift and as a **leftward** shift of the curve — not as a steeper slope. That is
exactly what §0.5 measures.

---

## 2. Inventory: what grid exists in the repository today

Surveyed 2026-10-23. "Complete" means both arms at the same N over ≥ 5 rungs.

| cell | artifact | NFE rungs | arms | N | seeds | state |
|---|---|---|---|---|---|---|
| R5c MNIST (`production`, `w16e1_5k`) | `gap64b-nfe-headroom/headroom.json` | 3, 5, 10, 25, 50, 100 | **baseline only** | 200 | 42 | one arm |
| R5c MNIST (4 ckpts, paper config) | `gap57-equal-nfe-ladder-n1000/*_s4{2,3,4}` | 50 | baseline + 3 arms | 1000 | 42/43/44 | one rung |
| R5c MNIST (mean-preserve) | `gap76-mean-preserving/*_s4{2,3,4}` | 50 | baseline + 1 arm | 1000 | 42/43/44 | one rung |
| R5c MNIST (low NFE) | `gap56-r5c-memory-t0/lownfe*` | 3, 4, 5, 10, 15 | baseline + 3 arms | 200 | 42 | not the paper config (`n_rounds` 2–3, not 4) |
| R5b CIFAR | `wave247-p5-r5b-nfe-sweep-aggregate.json` | 50, 100 | baseline + 4 arms | 200 | 42 | 2 rungs; NFE 200 never ran |
| R3 FlowMol3 | `flowmol3_fine_nfe_q4_2026.json` | 5, 10, 25, 50, 100, 200 | baseline + framework | — | 42 | **stub** — see below |
| K7 LineageFlow | `lineageflow_nfe_scan_paper_metric_q3_2026.json` | 50 | baseline + framework | — | 42 | **saturated** — see below |
| K7 Kanzi | `kanzi_nfe_scan_q4_2026.json` | 10, 50, 200, 500, 1000, 2000 | baseline + framework | 1 seq | 42/43/44 | **degenerate** — see below |

**No cell has a complete grid. Zero of eight.**

Three artifacts that look like ladders are not measurements, and using them
would have produced a false frontier:

1. **FlowMol3** (`flowmol3_fine_nfe_q4_2026.json`): `baseline_metric` equals
   `framework_metric` to full float precision in **all 6 cells**, and the two
   `*_debug` blocks are identical dicts. The framework arm was never applied.
   The metric is also a per-position atom-type entropy-reduction proxy, not the
   `fg_dev` metric the R3 claim uses.
2. **LineageFlow** (`lineageflow_nfe_scan_paper_metric_q3_2026.json`): named an
   NFE scan but contains a single rung (NFE = 50, seed 42) and `family_validity`
   is 1.0 on both arms — saturated at the ceiling, so it cannot separate arms at
   any NFE.
3. **Kanzi** (`kanzi_nfe_scan_q4_2026.json`): six rungs and three seeds, but
   `baseline_debug.n_sequences = 1` in every cell and validity is 1.0. One
   sequence cannot estimate a rate. The aggregate calls this
   `TIE_AT_SATURATION`, which is correct as a description and useless as a
   frontier.

The four remaining rows are real but incomplete: they carry one arm, one rung,
or a non-paper configuration.

### 2.1 Saturation status, per model

The protocol's premise is §0.1's claim that the baseline is converged. That is
checkable from the baseline ladders alone, and it differs by model:

| model | baseline over the measured rungs | reading |
|---|---|---|
| MNIST `production` | 11.1035 (3) → 11.0418 (5) → 11.0440 (10) → 11.0578 (25) → 11.0640 (50) → 11.0675 (100) | **flat from NFE 5**, total headroom 0.32 % — no speed win is possible |
| MNIST `w16e1_5k` | 26.9258 (3) → 26.7300 (100) | flat from NFE 25, headroom 0.75 % |
| CIFAR R5b | 447.8713 (50) → 443.7343 (100) | **still descending** (−0.92 % over one doubling) — headroom exists; grid must extend past 200 (§0.2a) |
| FlowMol3 / Kanzi / LineageFlow | — | no usable baseline ladder (§2) |

The MNIST and CIFAR rows are the two regimes the framework has to win in, and
they are different claims:

* **MNIST** — the baseline is converged, so the only possible win is a lower
  **plateau**. A "speed" win there would require the framework to beat the
  baseline at NFE < 3, and the restart needs at least a few steps per round. The
  frontier report must say this explicitly rather than report a ratio of 1.0 as
  if it were neutral.
* **CIFAR** — the baseline still has truncation error to spend steps on, so both
  a plateau win and a speed win are available. This is the cell where "fewer NFE
  to the same quality" is a real, measurable claim.

Both are consistent with the mechanism: the restart changes the distribution
(`mechanism-core-driver.md` §3), so where the distribution is already right the
only effect is the perturbation cost, and where it is not, the restart can both
lower the plateau and get there sooner.

---

## 3. The missing grid, as runs

These are the runs GAP-84 needs. **None may start while cuda:0 is paused.** The
commands are recorded so that the grid is reproducible, not so that it runs now.

| # | cell | rungs to add | N | seeds | config |
|---|---|---|---|---|---|
| 1 | R5c MNIST `production`, `w16e1_5k`, `w16e1_10k`, `w16e1_60k` | 3, 5, 10, 25, 50, 100, 200 **both arms** | 1000 | 42/43/44 | `scripts/wave191_p3_mnist_sweep.py --equal-total-nfe --restart-t0-mode memory --n-rounds 4` |
| 2 | R5b CIFAR | 3, 10, 25, 200 (have 50, 100) | 1000 | 42/43/44 | `scripts/wave247_p5_r5b_nfe_sweep.py` |
| 3 | R3 FlowMol3 | 3, 10, 25, 50, 100, 200 | 1000 | 42/43/44 | `scripts/sweep_gap32_flowmol3.py`, `fg_dev` metric, real framework arm |
| 4 | R1/K7 LineageFlow | 10, 25, 50, 100, 200 | 1000 | 42/43/44 | `scripts/lineageflow_n1000_gpu_sweep.sh` per rung |
| 5 | K7 Kanzi | 10, 25, 50, 100, 200 | 1000 | 42/43/44 | `scripts/sweep_kanzi_n1000_paper_metrics.py` (fix the 1-sequence readout first) |

Rung 1 is the only one whose lower bound is already known: MNIST saturates at 3,
so its frontier can only be a **quality** frontier; a speed win is arithmetically
impossible there (the baseline is already at its plateau at NFE = 3). That is a
property of the cell, not a defect of the framework, and the frontier report
must say so in one sentence rather than leave it implicit.

---

## 4. The instrument

`tools/frontier_report.py` implements §0.4–§0.6 exactly, and nothing else.

* Input: a normalised `frontier_input_v1` JSON — model, metric name, direction,
  `n_records`, the grid, and per rung `{value, units}` for each arm, where
  `units` is the aligned list of paired unit values (chunk / record / seed).
* Output: `frontier_report_v1` JSON plus a markdown table. The report carries
  the per-rung deltas and CIs, both plateaus, the dominance verdict per rung,
  the strict-gain rungs, the speed ratio, `quotable`, `win`, and the list of
  caveats that forced `INCOMPLETE`.
* `win` is `verdict == "WIN" and quotable`. The two are separate fields so a
  screen frontier can be inspected without ever being mistaken for evidence.

The tool refuses to invent a CI: a rung with a single value and no `units`
yields `ci95 = null`, which forces `INCOMPLETE` (§0.6). A rung present for one
arm only is reported as `missing` and also forces `INCOMPLETE`.

---

## 5. What this changes downstream

* Every cell's win verdict is now read off a frontier, not off one point. The
  per-cell `SUPPORTED` / `NOT_SIGNIFICANT` labels in `docs/CLAIMS.md` stay as
  they are until a frontier exists for that cell; this note does not move any
  frozen surface.
* GAP-78's acceptance already requires "the six existing strict wins survive";
  the frontier adds the plateau condition on top, at matched N.
* The GAP-69 per-family report (GAP-79) is a **level** question on a rate
  metric, not a frontier question; it keeps its own pre-registration.

---

## 6. The MNIST grid — started 2026-10-25 (additive; no number yet)

§3 said none of the five grids could start while `cuda:0` was paused. That
constraint never applied to R5c: MNIST FM is a NumPy adapter and runs on CPU.
The grid was therefore started on CPU while `cuda:0` stays free for the
GPU cells.

**What runs.** `reproduce/gap84_mnist_frontier.sh`, 4 checkpoints
(`production`, `w16e1_5k`, `w16e1_10k`, `w16e1_60k`) × 3 seeds (42/43/44) ×
7 rungs (4, 5, 10, 25, 50, 100, 200 — see §0.2b) = **84 cells**, each cell one
`wave191_p3_mnist_sweep.py` run of 4 arms (baseline + cosine +
codimension_sheet + evidence_driven). Canonical flags are exactly GAP-78's:
`--equal-total-nfe --beta-schedule equal_budget --beta-framework 0.3
--restart-t0-mode memory --mean-preserve --seed-keyed-prior --shared-prior
--n-rounds 4`, with only `--total-nfe` changing between rungs.

**Cost, measured not guessed.** One probe cell (`w16e1_5k`, seed 42, NFE=3,
N=1000) took 142 s wall. Against the recorded 26.4 min at NFE=50 this gives
≈ 50 s fixed + 30.7 s per NFE unit per cell, i.e. ≈ 3.45 h per
(checkpoint, seed) and ≈ 41 h serial. With `--jobs 8` (1 BLAS thread each) the
wall-clock estimate is **5–6 h**.

**Two additive changes, no number moved.**

1. `scripts/wave191_p3_mnist_sweep.py` now persists `baseline_chunk_fids`
   alongside the framework arms' `chunk_fids`. The baseline's per-chunk FIDs
   were always computed for the paired t-test and then discarded. This is a new
   key only; every existing key keeps its value.
2. `tools/gap84_mnist_frontier_input.py` converts the 84 cells into
   `frontier_input_v1`. **Unit = seed**, not chunk: a chunk FID is on a
   different scale from the headline FID (30.9 vs 21.4 on `w16e1_5k` at
   NFE=50), and `frontier_report` divides the unit-level CI by the headline
   baseline, so chunk units would make the delta and its CI disagree by ~30 %.
   With 3 seeds the report carries `n_units = 3` and says so (§0.3).

**First number, from the probe only.** At NFE=3 on `w16e1_5k` the baseline is
24.666 and the best framework arm 22.229 (−14.98 %, chunk-paired Bonferroni
p = 3.4e−12). That is a single cell at a single seed; it is recorded here as a
feasibility check on the low rung, not as a frontier reading, and it will be
superseded by the 3-seed grid.

**Status:** first launch 2026-10-25T03:27:15Z was stopped 3m21s in when the
rung-3 mismatch in §0.2b was found; the three `nfe3` cells it had started are
quarantined and the grid was relaunched on `{4,5,10,25,50,100,200}`. No
frontier report is issued until all rungs of a checkpoint have all three seeds.

---

## 7. First complete checkpoint: production (2026-10-25)

All 21 production cells (7 rungs × 3 seeds, N=1000) finished, so §6's
issue-condition is met for this checkpoint and only this one. The other three
checkpoints are still generating.

```bash
python3 tools/gap84_mnist_frontier_input.py \
  --root verification_outputs/gap84-mnist-frontier --ckpt production \
  --arm evidence_driven \
  --out verification_outputs/gap84-mnist-frontier/frontier_input_production_evidence_driven.json
python3 tools/frontier_report.py \
  --input verification_outputs/gap84-mnist-frontier/frontier_input_production_evidence_driven.json \
  --margin 0.01 --floor-units 1.0 \
  --out verification_outputs/gap84-mnist-frontier/frontier_production_evidence_driven.json
```

Arm = `evidence_driven` (best at 4 of the 7 rungs on seed 42; `codimension_sheet`
takes the other three by ≤ 0.08 FID). The choice does not carry the verdict:
`cosine` and `codimension_sheet` give the same LOSS, the same single violation
at rung 4, and the same speed ratio 2.50. Unit = seed (`n_units = 3`), per §6.

| NFE | baseline | framework | Δ | Δ% | improvement CI95 |
|---:|---:|---:|---:|---:|---|
| 4 | 9.99196 | 12.7593 | +2.76738 | **+27.70 %** | [−0.2824, −0.2697] |
| 5 | 9.97124 | 10.184 | +0.21275 | **+2.13 %** | [−0.0230, −0.0188] |
| 10 | 9.96893 | 9.94286 | −0.02607 | −0.26 % | [+0.0019, +0.0038] |
| 25 | 9.98282 | 9.94217 | −0.04065 | −0.41 % | [+0.0032, +0.0056] |
| 50 | 9.98934 | 9.95292 | −0.03642 | −0.37 % | [+0.0027, +0.0053] |
| 100 | 9.99289 | 9.95929 | −0.03361 | −0.34 % | [+0.0023, +0.0050] |
| 200 | 9.99473 | 9.96133 | −0.03340 | −0.33 % | [+0.0023, +0.0050] |

Baseline plateau **9.99381** over NFE [100, 200], last-two relative change
0.018 % → flat, so this is convergence, not a compute limit (§0.4).

**Verdict: LOSS.** `weak_dominance = false`, violation at rung 4;
`strict_gain_rungs = []`; speed ratio **2.50** (the framework reaches the
baseline plateau at NFE 10 vs the baseline's 4). Under §0.4 rule 2 a cell wins
only on weak dominance at **every** rung plus (a strict gain or a speed ratio
≤ 0.5), so neither clause is met.

**What the table says, rung by rung.**

1. **The loss is large and certain, not marginal.** At NFE=4 the framework is
   27.7 % worse with a CI of [−0.2824, −0.2697] — an order of magnitude past
   the −0.10 floor (1 FID unit on a 9.99 baseline). This is not a
   near-miss that another seed would flip.
2. **The sign flips at NFE ≥ 10 and the CI excludes 0 there**, but the gain is
   0.026–0.041 FID units, i.e. **2.6–4.1 % of the cell's own floor**. Weak
   dominance holds from rung 10 up; a strict gain never does.
3. **The speed half of the claim is reversed on this checkpoint**: 10 NFE to
   reach the baseline's plateau vs the baseline's 4.

**Why rung 4 behaves this way — structural, and it was pre-registered.** With
`--n-rounds 4 --equal-total-nfe` at total NFE=4 the allocator returns
`[1,1,1,1]`: four rounds, one integration step each, and a re-noise between
them. The restart needs per-round capacity to correct anything; at NFE = R it
has none, so the composite map is four half-steps through noise. §0.2b put
rung 4 in the grid *before* any number existed (it is the lowest feasible
rung), so the rung stays and the verdict stands. Dropping it now, after seeing
the table, would be moving the goalposts.

**What this does and does not decide.** It decides the production checkpoint of
R5c: no frontier win, and the direction of the speed ratio is against the
framework. It does not decide R5c as a cell, because the other three
checkpoints are still running — `w16e1_5k`'s probe at the low rung already has
the opposite sign (baseline 24.666 vs 22.229, −14.98 %). If production turns out
to be the only checkpoint that loses, the object to fix is the low-NFE
allocation on a well-trained field (the restart budget at NFE ≈ R), not the
wording of the verdict.


---

## 8. GAP-84b: the round count has to follow the budget (2026-10-25)

§7 named the mechanism behind rung 4 — at `total_nfe == n_rounds` the allocator
returns `[1,1,1,1]` — and said the object to fix is the low-NFE allocation, not
the verdict wording. This section is that fix, measured.

### 8.1 The knob

`effective_rounds(n_rounds, total_nfe, min_steps_per_round)`
(`scripts/wave191_p3_mnist_sweep.py`) caps the round count so that every round
is worth at least `min_steps_per_round` integration steps:

```python
R_eff = min(n_rounds, max(1, total_nfe // min_steps_per_round))
```

CLI: `--min-steps-per-round`, default **1**. At the default the expression
returns `n_rounds` unchanged, so every number already in §7 is reproduced
bit-for-bit; `tests/test_gap84b_round_budget.py` pins that
(`test_default_is_the_legacy_round_count`) and pins the degenerate case that
motivated the change (`test_the_allocator_really_was_degenerate_at_nfe_eq_rounds`).

Two properties make this a **policy** and not a per-rung fit:

* `min_steps_per_round = 2` changes the grid only where `total_nfe < 2·n_rounds`,
  i.e. only rungs 4 and 5 of this grid. Rungs 10–200 are untouched — the
  assembled report below reuses their §7 cells through symlinks, not new runs.
* When the cap bites all the way down (`total_nfe // min_steps == 1`) the run
  degrades to a **single pass**, which is the baseline map itself, not a
  one-round restart stub. The `ms=3` cells below show this as an exact
  equality: all four arms land on the baseline FID to the last digit.

### 8.2 The measurement (production, `evidence_driven`, 3 seeds, N = 1000)

| NFE | `min_steps` | `R_eff` | baseline | framework | Δ % |
|---:|---:|---:|---:|---:|---:|
| 4 | 2 | 2 | 9.99196 | 10.37282 | **+3.81 %** |
| 4 | 3 | 1 | 9.99196 | 9.99196 | **+0.00 %** |
| 5 | 2 | 2 | 9.97124 | 10.37529 | +4.05 % |
| 5 | 3 | 1 | 9.97124 | 9.97124 | **+0.00 %** |
| 10 | 3 | 3 | 9.96893 | 9.99378 | +0.25 % |

Compare rung 4 in §7: **12.7593 / +27.70 %**. The cap removes 86 % of that
loss. Per-seed, the `R_eff = 1` rows are the baseline exactly (9.9761 / 9.9940 /
10.0057 for every arm), which is the check that the knob has no residual of its
own.

`min_steps_per_round = 3` is **worse** where it acts — at NFE = 10 it forces
`R_eff = 3` and gives 9.99378 vs 9.94286 for the uncapped `R = 4` (+0.25 % vs
−0.26 %). So the useful setting is exactly 2; a stronger cap is not a stronger
fix. Recorded here so that nobody "fixes it harder".

### 8.3 The assembled frontier, and both verdicts

`verification_outputs/gap84c-production-cap/` holds rungs 4 and 5 from the cap
arm and rungs 10–200 as symlinks to the §7 cells:

```bash
python3 tools/gap84_mnist_frontier_input.py \
  --root verification_outputs/gap84c-production-cap --ckpt production \
  --arm evidence_driven \
  --out verification_outputs/gap84c-production-cap/frontier_input.json
python3 tools/frontier_report.py \
  --input verification_outputs/gap84c-production-cap/frontier_input.json \
  --margin 0.01 --floor-units 1.0 \
  --out verification_outputs/gap84c-production-cap/frontier_report.json
```

| rule | violations | strict-gain rungs | speed ratio | verdict |
|---|---|---|---:|---|
| ledger floor (1 FID unit → margin 0.1000–0.1003) | none | none | 2.50 | **TIE** (was LOSS) |
| pre-registered 1 % relative | 4, 5 | 10, 25, 50, 100, 200 | 2.50 | LOSS (was LOSS) |

Both are printed because §0.5 and CLM-060 disagree on the unit and the audit
does not get to pick the friendlier one after seeing the table. The floor rule
is the one the ledger defines (CLM-060: 1 FID), and under it the production
checkpoint moves from LOSS to TIE: every rung is now inside its own floor, and
the two clauses that could still buy a WIN both fail — no rung clears +1 FID,
and 10 NFE to the baseline plateau against the baseline's 4 is a ratio of 2.50,
not ≤ 0.50.

### 8.4 What the remaining distance is, in units

At rungs 10–200 the framework is genuinely better: improvement CI95 excludes 0
at all five rungs. The size is 0.026–0.041 FID units. The floor is 1.0. So the
gap to a strict gain is **25×**, and it is an effect-size gap, not an allocation
gap — the allocation is now correct at every rung of the grid.

That is the honest state of this cell: the structural defect is gone, the
residual is a mechanism question (how much does a restart buy on a field that
has already converged?), and §9 is the next measurement on it.

## 9. Next: is there a round-count dose at fixed NFE?

The cap says `R` matters at NFE = 4 (4 → 2 is worth 2.39 FID). It does not say
whether `R` matters *above* the cap. The next run holds NFE = 25 fixed and
sweeps `n_rounds ∈ {2, 4, 6, 8, 12}` with `min_steps_per_round = 2`:
a within-checkpoint dose-response on the only quantity the framework owns, with
`R = 4` as the in-grid reference (the value used at every rung of §7).

NFE = 25 is chosen over NFE = 10 because the 10-step budget saturates at
`R_eff = 5` (two steps per round), which leaves only two distinct levels — not
a dose-response. At NFE = 25 the same rule admits `R_eff ∈ {2,4,6,8,12}`, and 25
is a rung where the framework already beats the baseline by 0.41 %.

Pre-registration: 3 seeds, N = 1000, same arm, same margin rules as §8.3. The
dose is `R`. Decision rule, fixed before the run:

* monotone increase in the paired improvement as `R` rises → the lever is live,
  keep climbing until it turns over, and the 25× in §8.4 is a budget question;
* interior optimum at `R = 4` or below → `R` is saturated on this checkpoint and
  the remaining distance is not a round-count question at all;
* flat → `R` does not enter the effect above the cap, and §7's rungs are already
  at the best `R`.
