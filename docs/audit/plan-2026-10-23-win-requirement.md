# Plan change, 2026-10-23 — the win requirement, and a corrected control

**Scope:** `todo.json` only. No frozen surface touched
(`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`, `docs/drafts/paper-A-final.*`,
`tnnls_submission/**` unchanged).

---

## 1. Two corrections to the previous plan

### 1.1 The requirement is "win everywhere", not "state the boundaries"

The plan inherited a framing in which a losing cell could be closed by writing
the boundary down: GAP-69's deliverable allowed "stays an empirical perturbation
result", GAP-71's allowed "the image boundary is stated", GAP-70's allowed "K7
is stated as an unexplained boundary". Under the actual agreement — the
framework must win on every model task — those are not deliverables, they are
open gaps.

`todo.json` now carries an `objective` and a `win_definition`, and every
non-winning cell has a mechanism gap whose acceptance test is the win itself:

| cell | state before this plan | gap that must produce the win |
|---|---|---|
| R1 LineageFlow | wins single-seed, but 8.20× is one family | GAP-69 → **GAP-79** |
| R2 Kanzi | wins, small, one seed | folded into **GAP-84**'s frontier |
| R3 FlowMol3 | near-miss (`p=0.043` vs α=0.00714) | **GAP-81** |
| R5a 2D FM | tie at the effect floor | **GAP-80** |
| R5b CIFAR | loses (magnitude inflated) | **GAP-71** |
| R5c MNIST | 6 W / 6 R after GAP-76 | **GAP-78** |
| K1 FlowMol3 | saturated metric | **GAP-47** |
| K7 LineageFlow | inverted | **GAP-70** |

### 1.2 "Just run the baseline with more steps" was the wrong control

I treated an equal-compute baseline (best-of-N / extra NFE) as a missing
experiment. That is wrong, and the repo already contains the evidence: flow
matching's inference protocol saturates in the step count, so more steps do not
raise the baseline's ceiling. GAP-57 measured it directly — `w16e1_5k` gives
27.2361 → 27.2311 across 50/100/200 steps, i.e. flat.

The correct claim is therefore a **(quality, NFE) frontier**:

1. **dominance** — the framework's curve at or below the baseline's at every
   NFE on the grid;
2. **ceiling** — the framework's plateau is better than the baseline's;
3. **speed** — the NFE at which the framework first reaches the baseline's
   plateau quality.

`win_definition` requires (1) and (2) in addition to the point win, and
`frontier_protocol` fixes the grid and the plateau rule. This is stronger than
the old single-point criterion, and it is the claim the paper actually makes:
the framework raises what the frozen checkpoint can reach, and reaches a given
quality sooner.

## 2. What this does not change

* **No seed engineering.** `decision_rule` keeps the prohibition and adds that
  a cell's canonical seed set is fixed before its first number.
* **No promotion by wording.** A win is a CI result, not a label.
* **GAP-76's result stands.** It removed the MNIST first-moment defect (mean
  ΔFID +7.75 % → −3.34 %, 6 W / 0 T / 6 R strict), so GAP-78 targets a
  contraction, not a location error. GAP-67's scalar second-moment null also
  stands, which is why GAP-78 must be directional.

## 3. Order

GAP-84 first: it defines the win metric that every other gap is judged by, and
it is CPU-only. GAP-69 is already in flight on `cuda:0` and is not displaced.
GAP-79 opens only if the 3-seed per-family decomposition reproduces seed 42's
PF00005 concentration — that condition is written into the gap, not decided
afterwards.
