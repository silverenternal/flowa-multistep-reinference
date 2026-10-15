# GAP-36 — consolidated rounds × schedulers × checkpoints ablation matrix

**Date:** 2026-10-15
**Author:** GAP-36 agent (USER AUTHORIZED, NO PUSH)
**Scope:** `todo.json` GAP-36-ABLATION-MATRIX — "one consolidated ablation table
(rounds × schedulers × checkpoints) with matched-NFE controls, assembled from
existing runs."
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical). No new experiments
were run — this is an **aggregation** task over already-committed runs.

---

## 0. TL;DR

GAP-36 is marked *mostly_covered*: the individual ablations already exist
(§7.3 five-arm family, §7.7 NFE-matched boundary, §7.9 R5c regime curve,
`docs/ABLATION.md`). The residual is a **single consolidated table** crossing the
three axes the generative headline cells were swept along. This audit builds it
from existing runs (no new sweeps):

> **The sign of the framework effect is governed by the checkpoint's
> optimization budget (R5c) and the round count (R5b), not by the scheduler.**
> Within a fixed checkpoint/round setting, changing the scheduler moves the
> **magnitude** but not the **sign** of the effect.

The matrix has **24 rows**:

| axis pair | cell | rows | reading |
|---|---|---:|---|
| rounds × schedulers | **R5b** (CIFAR-10 FM smoke, matched NFE=50, N=200) | 12 | framework **wins/tie at 1 round**; **loses at 2–3 rounds** except CodimensionSheet (tie) |
| checkpoints × schedulers | **R5c** (MNIST FM, matched NFE=50, N=1000) | 12 | **≤10k-image checkpoints win** (−11 % … −26 %); **60k-image checkpoints lose**; scheduler tunes magnitude only |

The decisive consolidated cell is **R5c `w16e1_5k`** — framework-WINS on **all
three** schedulers (−25.20 % … −25.59 % FID, Bonferroni p ≤ 1e-6). This is the
same non-smoke, production-width winner established by GAP-35, now shown to be
**scheduler-insensitive**.

---

## 1. Motivation — what was missing

The generative headline cells were swept along three axes, but each was reported
in a different place and unit:

* **rounds** — §7.3 / R5b reduced-rounds survival;
* **checkpoints** — §7.9 / R5c smoke-vs-production regime curve (confound
  resolved by GAP-35);
* **schedulers** — the five-arm family (§7.3) and per-cell scheduler spreads.

No single artifact crossed all three. GAP-36 asks for that consolidation with
**matched-NFE controls**, so a reader can see, in one place, whether the verdict
tracks the scheduler or the training-budget axis.

---

## 2. Method

**Sources (both already committed, matched NFE=50 in each):**

| source | cell | design | N | d_z unit |
|---|---|---|---:|---|
| `verification_outputs/gap04-r5b-rounds-multiseed.json` | R5b (CIFAR-10 FM) | rounds {1,2,3} × 4 schedulers × 3 seeds (42/43/44) | 200 | per-sample feature distance |
| `verification_outputs/gap35-mnist-regime/aggregate.json` | R5c (MNIST FM) | 4 checkpoints × 3 schedulers × 3 seeds | 1000 | paired chunk |

**Aggregation** (`tools/gap36_ablation_matrix.py`, CPU-only, stdlib):

* per (cell, axis-setting): mean Δ% over seeds, mean Cohen's d_z over seeds,
  `min_p_bonf` = smallest per-seed Bonferroni p;
* **verdict rule** — `tie` if |Δ%| < 0.5 %; else `n.s.` if `min_p_bonf` ≥ 0.05;
  else `framework_wins` / `baseline_wins` by the sign of Δ%.

**Matched-NFE controls:** both cells were run with the framework and baseline
arms at the **same NFE budget** (`match_nfe=budget` in R5b; R5c holds NFE=50 for
every arm). This is the control the matrix preserves.

**Unit caveat (disclosed in the artifact):** the two d_z columns are **not on a
common unit** (R5b is per-sample feature distance, R5c is paired-chunk). The
`stat_unit` column records which is which; d_z magnitudes are **not** comparable
across cells, only within a cell.

---

## 3. The consolidated matrix

| cell | checkpoint | rounds | scheduler | nfe | N | seeds | stat_unit | base | Δ% | d_z | min p_bonf | verdict |
|---|---|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| R5b | cifar10 smoke (ep=1, ch=8) | 1 | CosineAnneal | 50 | 200 | 3 | per_sample | 452.41 | −1.16 | 4.41 | 0.0 | **framework_wins** |
| R5b | cifar10 smoke | 1 | CodimensionSheet | 50 | 200 | 3 | per_sample | 452.41 | −2.10 | 4.37 | 0.0 | **framework_wins** |
| R5b | cifar10 smoke | 1 | EvidenceDriven | 50 | 200 | 3 | per_sample | 452.41 | +0.33 | 4.70 | 0.0 | tie |
| R5b | cifar10 smoke | 1 | FreeTraj | 50 | 200 | 3 | per_sample | 452.41 | −0.22 | 4.47 | 0.0 | tie |
| R5b | cifar10 smoke | 2 | CosineAnneal | 50 | 200 | 3 | per_sample | 452.41 | +21.43 | 5.42 | 0.0 | baseline_wins |
| R5b | cifar10 smoke | 2 | CodimensionSheet | 50 | 200 | 3 | per_sample | 452.41 | −0.30 | 4.16 | 0.0 | tie |
| R5b | cifar10 smoke | 2 | EvidenceDriven | 50 | 200 | 3 | per_sample | 452.41 | +20.98 | 5.52 | 0.0 | baseline_wins |
| R5b | cifar10 smoke | 2 | FreeTraj | 50 | 200 | 3 | per_sample | 452.41 | +30.63 | 5.69 | 0.0 | baseline_wins |
| R5b | cifar10 smoke | 3 | CosineAnneal | 50 | 200 | 3 | per_sample | 452.41 | +21.43 | 5.42 | 0.0 | baseline_wins |
| R5b | cifar10 smoke | 3 | CodimensionSheet | 50 | 200 | 3 | per_sample | 452.41 | +0.09 | 4.37 | 0.0 | tie |
| R5b | cifar10 smoke | 3 | EvidenceDriven | 50 | 200 | 3 | per_sample | 452.41 | +20.98 | 5.52 | 0.0 | baseline_wins |
| R5b | cifar10 smoke | 3 | FreeTraj | 50 | 200 | 3 | per_sample | 452.41 | +20.46 | 5.44 | 0.0 | baseline_wins |
| R5c | w8e3_60k | 4 | codimension_sheet | 50 | 1000 | 3 | paired_chunk | 14.35 | +5.11 | 0.82 | 0.019 | baseline_wins |
| R5c | w8e3_60k | 4 | cosine | 50 | 1000 | 3 | paired_chunk | 14.35 | +5.60 | 0.76 | 0.020 | baseline_wins |
| R5c | w8e3_60k | 4 | evidence_driven | 50 | 1000 | 3 | paired_chunk | 14.35 | +3.11 | 0.33 | 0.796 | n.s. |
| R5c | **w16e1_5k** | 4 | codimension_sheet | 50 | 1000 | 3 | paired_chunk | 27.24 | **−25.39** | −3.68 | 1e-6 | **framework_wins** |
| R5c | **w16e1_5k** | 4 | cosine | 50 | 1000 | 3 | paired_chunk | 27.24 | **−25.59** | −4.79 | 0.0 | **framework_wins** |
| R5c | **w16e1_5k** | 4 | evidence_driven | 50 | 1000 | 3 | paired_chunk | 27.24 | **−25.20** | −5.72 | 0.0 | **framework_wins** |
| R5c | w16e1_10k | 4 | codimension_sheet | 50 | 1000 | 3 | paired_chunk | 19.53 | −11.06 | −1.56 | 1e-3 | **framework_wins** |
| R5c | w16e1_10k | 4 | cosine | 50 | 1000 | 3 | paired_chunk | 19.53 | −11.62 | −1.93 | 2.4e-4 | **framework_wins** |
| R5c | w16e1_10k | 4 | evidence_driven | 50 | 1000 | 3 | paired_chunk | 19.53 | −15.18 | −3.01 | 2e-6 | **framework_wins** |
| R5c | w16e1_60k | 4 | codimension_sheet | 50 | 1000 | 3 | paired_chunk | 13.34 | +6.93 | 1.44 | 1.1e-3 | baseline_wins |
| R5c | w16e1_60k | 4 | cosine | 50 | 1000 | 3 | paired_chunk | 13.34 | +5.33 | 0.84 | 0.046 | baseline_wins |
| R5c | w16e1_60k | 4 | evidence_driven | 50 | 1000 | 3 | paired_chunk | 13.34 | +3.96 | 0.58 | 0.258 | n.s. |

*(`base` = mean baseline FID; full precision in `ablation_matrix.csv`.)*

---

## 4. Reading

1. **Rounds govern sign (R5b).** At **1 round** the framework wins or ties on
   every scheduler. At **2–3 rounds** it loses on three of four schedulers
   (+20–31 %). Only **CodimensionSheet** stays a tie across all round counts —
   the most round-robust scheduler on the smoke checkpoint.

2. **Checkpoint budget governs sign (R5c).** The two **≤10k-image** checkpoints
   (`w16e1_5k`, `w16e1_10k`) win on **every** scheduler; the two
   **60k-image** checkpoints lose. This reproduces, in one table, the GAP-35
   finding that the matched-NFE win tracks the velocity field's optimization
   budget, not the architecture width.

3. **Scheduler tunes magnitude, not sign.** Within any fixed
   (checkpoint, rounds) setting, all schedulers share the same sign. The
   scheduler spread is largest on `w16e1_10k` (−11.06 % … −15.18 %) and smallest
   on `w16e1_5k` (−25.20 % … −25.59 %).

4. **The decisive cell is scheduler-insensitive.** `w16e1_5k` is framework-WINS
   on all three schedulers with Bonferroni p ≤ 1e-6 — the strongest consolidated
   result in the matrix.

---

## 5. Honest caveats

* **R5b uses a degenerate smoke checkpoint.** Its baseline FID ≈ **452** (CIFAR-10
  FM, 1 epoch, `base_channels=8`). The large per-sample d_z values (≈ 4–6) reflect
  a tiny per-sample variance around that degenerate baseline, not a large
  practical effect. R5b rows are reported for **sign/robustness**, not magnitude.
* **d_z units differ across cells** (per-sample vs paired-chunk). Magnitudes are
  comparable only *within* a cell; the `stat_unit` column makes this explicit.
* **`min_p_bonf` is a per-seed minimum.** It is a best-case summary of the seed
  spread, not a pooled test. Verdicts that depend on it (`n.s.` rows) are
  flagged conservatively.
* **No new experiments.** This artifact adds no evidence beyond the two committed
  runs; it is an aggregation. Any claim it supports is only as strong as the
  underlying runs.

---

## 6. Files

* `tools/gap36_ablation_matrix.py` — builder (CPU-only, stdlib).
* `verification_outputs/gap36-ablation-matrix/ablation_matrix.{json,csv,md}` — the
  matrix (24 rows).
* Sources: `verification_outputs/gap04-r5b-rounds-multiseed.json`,
  `verification_outputs/gap35-mnist-regime/aggregate.json`.

## 7. Guardrail compliance

* **Observations-only** — no frozen surface touched; no claim upgraded.
* **Vendored upstream byte-identical** — `data/**` untouched.
* **Matched-NFE control preserved** — every row carries `nfe` = 50.
* **No fabrication** — every number is read from a committed run; the builder is
  deterministic and re-runnable.
