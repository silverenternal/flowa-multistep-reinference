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
