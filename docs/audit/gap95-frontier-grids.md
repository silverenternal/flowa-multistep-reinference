# GAP-95 pre-registration — which cells can carry a frontier, and in what order

**Status:** PRE-REGISTERED 2026-10-27, NOT RUN.
**Gap:** six of seven R-level cells have no (quality, NFE) grid. The packaging
pass discloses this in §VII-A ("Frontier coverage") and in §IX. A disclosure is
not a measurement, and the paper calls the grid load-bearing.

---

## 1. The ordering rule, stated before the data

The gap list orders these cells R1, R2, R3, R5a, R5b. That order is wrong for
this purpose. A grid is worth running only where **both** hold:

* **the baseline can still descend** — a baseline that is already flat across
  NFE cannot produce a frontier, only a flat line with error bars;
* **the verdict could change** — if a grid cannot move a cell out of TIE /
  REGRESSES / PARTIAL, the measurement is documentation, not evidence.

Ranked by that rule:

| rank | cell | current budget | can the baseline descend? | can the verdict change? |
|---:|---|---|---|---|
| 1 | **R5b CIFAR-10 RF** | NFE=50, baseline FID **447.9** | **Yes, strongly** — 448 at 50 steps is far from converged | **Yes** — REGRESSES today; a plateau comparison could flip it |
| 2 | **R3 FlowMol3** | NFE=250 | Probably not — 250 steps is near-converged for a 3D flow | Maybe; currently n.s. at `N=1000` |
| 3 | **R2 Kanzi** | one canonical budget | Unknown | Low — RMSD is a reconstruction metric, not a quality-vs-NFE curve |
| 4 | **R1 LineageFlow** | NFE=150, **fixed by upstream fidelity** | Probably flat — the metric is a discrete hit count | Low; and moving NFE breaks the upstream-config match |
| 5 | **R5a Two Moons** | one budget | Analytic toy; the baseline likely converges in a handful of steps | Low — currently a TIE below the effect floor |

## 2. The measurement that comes first: baseline-only rung scans

For every cell in the table, run the **baseline alone** across the rung set
before running any framework arm. One arm instead of two halves the cost and
answers the only question that decides whether a grid exists.

A cell is declared **saturated** when the baseline's metric moves by less than
the cell's floor between the lowest and highest rung. That measurement is the
justification for a point-only verdict, and it is what the paper cites instead
of an omission.

## 3. R5b first — the only cell where a grid can flip a verdict

**What is measured now.** Matched NFE=50, N=200 and N=1000, framework FID
**+20.21%** relative to a baseline at 447.9 (`CLM-060`; `gap04-r5b-rounds.md`).
That is the one REGRESSES cell in the ledger.

**Why a grid is the right next measurement.** At NFE=50 the baseline is nowhere
near converged, so the restart is being asked to repair a model that has not
learned the distribution. Two outcomes are possible and both are informative:

* the baseline's FID falls steeply with NFE and the framework's relative
  regression shrinks or reverses → the current REGRESSES verdict is a low-NFE
  artifact and R5b flips;
* the regression persists at the plateau → R5b is a genuine regression on this
  model, and the paper says so without qualification.

**Pre-registered prediction.** The baseline descends by more than 10× between
NFE=50 and NFE=200 (448 → below 45). Whether the framework's delta reverses is
**not** predicted: the κ reading says a converged model has no excess dispersion
to remove, so a reversal is not expected. The grid is run to find out, not to
confirm.

**Scope limit, recorded now.** The CIFAR checkpoint in the repository is a weak
model. Even a flipped R5b is evidence about *this* checkpoint, not about
competitive models. Closing the competitive-benchmark objection is GAP-94's job
and this measurement does not substitute for it.

**Protocol.** Rungs {10, 25, 50, 100, 200}, seeds 42/43/44, N=1000, `--n-rounds
4`, `--equal-total-nfe`, `--min-steps-per-round 2` (which binds at rungs 10 and
below), headline arm `evidence_driven`, plateau = mean of the last two rungs,
floor rule 1 FID, verdict via `tools/frontier_report.py` unmodified.

**Cost.** 5 rungs × 3 seeds × 2 arms = 30 arm-cells. At the measured CIFAR
throughput (1167–1573 s per 200-sample cell at NFE=50), a N=1000 rung at
NFE=200 is roughly 1.5 h per arm → **≈1 GPU-day**.

## 4. Four artifacts that look like grids and are not

These must not be reused as frontier evidence. Each is a flat line, which is
exactly the failure mode §2 exists to detect:

| artifact | why it is degenerate |
|---|---|
| `kanzi_nfe_scan_q4_2026.json` | validity 1.0 on **both** arms at **every** rung |
| `flowmol3_fine_nfe_q4_2026.json` | 0.0734 on both arms at every rung |
| `lineageflow_nfe_scan_paper_metric_q3_2026.json` | n=8, 8/8 saturated ties |
| `nfe_curve_fair_w170_q3_2026.csv` | baseline constant across rungs |

## 5. Acceptance

Every R-level cell has **either** a grid of five or more rungs **or** a recorded
saturation measurement with the number that shows saturation. No cell is left
with a bare assertion, and no cell is closed by citing one of the four artifacts
above.

## 6. Cost, in the order the rule implies

1. Baseline-only scans for R2, R3, R5a, R1: ≈0.5 GPU-day total.
2. Full grid for R5b: ≈1 GPU-day.
3. Full grids only for the cells whose baseline scans descend: unknown, bounded
   by 3 more GPU-days.

Do step 2 first if only one step is funded — it is the only one that can change
a verdict.

## 7. Unresolved

1. **R1's NFE=150 is an upstream-fidelity constraint**, not a free parameter
   (`reproduce/01_R1_LineageFlow.sh:94`). A grid there trades fidelity to the
   released config for a frontier; if the baseline is flat the trade is not
   worth making, which is why R1 is ranked fourth.
2. **R2's baseline budget is not recorded in the reproduce script.** It has to
   be read off the cell's audit before any rung scan is planned.
3. **A flipped R5b on a weak model is a narrow result.** The paper must state
   the checkpoint's FID in the same sentence as the verdict.
