# GAP-70 round 2 — the tempered restart draw (`lam`)

Status: **code + pre-registration, no run yet.** GPU queue is GAP-79's
confirmation, then GAP-81's sigma screen, then GAP-71's before/after; this run
goes behind them because it is a P1 screen and nothing depends on it.

## 0. Where this comes from

Round 1 (`docs/audit/gap70-lineageflow-position-blend.md` §4) asked whether the
restart's novelty loss could be fixed by making the *blend position-selective*.
It cannot: at N = 1000, seed 42, NFE = 10, R = 3, the three arms measured

| arm | what it is | novelty | Pfam validity |
|---|---|---:|---:|
| A | baseline, no restart | 46.6 % | 14.5 % |
| B | scalar blend — K7's framework arm | 0.8 % | 21.4 % |
| C | position blend (`m_vec = m·(1 − c)`) | 1.5 % | 19.5 % |

so the mask moved novelty by +0.7 pp (CI [−0.35, +1.67], p = 0.167) while
costing 1.9 pp of validity. The drop from A to B is therefore produced by the
restart operator itself, and the same run measured the *other* direction of the
same operator: `V_B − V_A = +6.9 pp`, CI [+3.4, +10.2], p = 4.3e−5.

That is a validity-for-novelty trade. The next lever has to change **what the
restart draws**, not where it writes — which is what this round tests.

## 1. The lever

The shipped restart replaces the state with a fresh per-position categorical
and blends it in: `blended = m·prior + (1 − m)·fresh`, with
`fresh = softmax(randn(L, 20))` on the amino-acid columns (D-004b). The new
policy tempers that draw toward the state it replaces:

```
fresh = (1 − lam) · state + lam · softmax(randn)
```

implemented as `TemperedFreshPerturbation` and exposed as
`--restart-draw-lambda` on `tools/gen_lineageflow_n1000_fastas.py`
(`adaptive_reflow/algorithm/perturbation/perturbation.py`).

The two ends are **already-measured arms**:

* `lam = 0` returns the state unchanged, so the restart is a no-op and the
  round loop only continues the integration — the no-restart end (A).
* `lam = 1` is the shipped D-004b draw — the current arm (B). The test
  `test_lam_one_is_the_shipped_draw` pins the policy against the adapter's own
  `_synthesize_random_simplex`, so this is the same draw, not a similar one.

Algebraically the policy is the same restart at a higher effective memory
fraction, `m_eff = m + (1 − m)(1 − lam)`, which is deliberate: `m` is the
schedule's pre-registered quantity and `lam` is the draw's own knob. They are
kept separate so a cell cannot be ambiguous about which one it moved.

## 2. The arithmetic that constrains the design

Every interior `lam` is a point on the segment between A and B. **A point on a
segment cannot be better than both of its ends.** So no `lam` can win unless
the (novelty, validity) frontier *bulges above the chord*

```
chord_N(lam) = N_A + lam·(N_B − N_A)
chord_V(lam) = V_A + lam·(V_B − V_A)
```

and the report prints both chords and each arm's residual against them. This is
why the screen is a convexity test rather than a search over a free parameter:
the rule "pick the best of seven arms" would otherwise be exactly the
post-hoc freedom pre-registration exists to remove.

## 3. Mechanism, and the sign it predicts

The trade has two components that need not be produced by the same part of the
operator:

* **Validity** needs the restart to *escape* a bad local state. That benefit
  should saturate quickly: once enough positions are re-drawn to leave the
  attractor, more noise buys nothing.
* **Novelty** needs the sample to *stay put*. The metric is nearest-neighbour
  identity to Pfam-A, so it should stay near the baseline until enough
  positions change to make the sequence resemble a known family.

If validity is front-loaded and novelty is back-loaded, the frontier is convex
and an interior `lam` dominates both ends. If both are produced by the same
"re-solve from a flattened state" mechanism, the frontier is the chord and no
`lam` wins.

## 4. Arms and settings

Seven cells, one seed, N = 1000 each, config pinned to the K7 measurement:

```
lam ∈ {0, 0.1, 0.2, 0.35, 0.5, 0.75, 1}
N = 1000, seed = 42, NFE = 10, R = 3, restart_min_nfe = 5, temperature = 1.0
```

`reproduce/gap70_tempered_draw.sh` generates every cell with
`tools/gen_lineageflow_n1000_fastas.py`, asserts that all seven baseline arms
are byte-identical (the flag only touches the framework arm, so the records are
paired), scores validity with hmmscan against Pfam-A, scores novelty with
`mmseqs easy-search` against the canonical 63.8 M Pfam-A DB
(`-s 7.5 -e 100`), and writes `tools/gap70_tempered_report.py`'s report.

The generator's built-in novelty is never used: it searches a 200-sequence
holdout DB and saturates at 1.0.

## 5. Decision rules (fixed before the run)

Let `N_lam` be the novel fraction (`pctid < 30 %` or no hit) and `V_lam` the
Pfam hit rate, both on the same 1000 records.

A `lam` **wins** iff both hold:

1. **Novelty recovered.** `N_lam ≥ N_A` and the paired Newcombe 95 % CI on
   `N_lam − N_A` has a lower bound **above zero**. Recovering novelty is the
   claim, so it needs a lower bound, not a point estimate.
2. **Validity preserved.** `V_lam ≥ V_1 − 2 pp` and there is **no detectable
   loss**: either the paired difference `V_lam − V_1` is ≥ 0, or its exact
   McNemar p ≥ 0.05.

Verdicts:

* `TEMPERED_DRAW_WINS` — at least one interior `lam` wins. The smallest winning
  `lam` is selected (least intervention) and is the only cell replicated.
* `TRADE_IS_INTRINSIC` — no interior `lam` wins **and** no interior `lam` sits
  above both chords. Then the validity gain and the novelty cost are produced
  by the same part of the operator at this `R`/NFE allocation, and the next
  lever must move a different quantity (see §7).
* `INCONCLUSIVE` — an interior `lam` is above both chords but fails a CI, or the
  arms disagree in some other way. The failing quantity is named.

**No seed top-ups.** Rule 4 of round 1 stands: a second seed is run only when a
`lam` wins at 42, and then it is a replication, not a search.

## 6. Why the validity clause is not a non-inferiority interval

The obvious formulation — "the paired CI on `V_lam − V_1` must exclude a drop
larger than 2 pp" — is not usable here, and this is arithmetic, not preference.
At n = 1000 with **zero** discordant pairs, the paired Newcombe interval is
[−4.95 pp, +0.23 pp]. An arm whose validity is bit-identical to `lam = 1`
would fail a 2 pp non-inferiority test, so the test cannot be passed by
construction and is therefore not the test.

The novelty clause keeps the interval because there the burden is to *prove* a
gain. The validity clause carries the point-estimate margin plus "no
significant loss", which is the strongest statement that instrument supports at
this n. Both the interval and the p-value are printed either way.

## 7. What falsification would mean, and what runs next

`TRADE_IS_INTRINSIC` would say something specific: at R = 3 and NFE = 10 the
validity gain and the novelty cost are the same event — the re-solve from a
moved state is what both buys validity and loses novelty — and tempering the
draw cannot separate them.

The next lever is then **when** the restart re-enters, not how far it moves:
the restart currently re-enters at `t = 0` and re-integrates the whole interval,
which is a full re-generation. A restart that re-enters at `t* > 0` keeps the
sample's structure and lets the model make only a late correction. That is the
same time-coordinate mechanism GAP-56 found for MNIST and GAP-80 measured for
the 2D path (a one-line time-alignment change removed 96 % of the restart's
deficit there), and it is a separate, pre-registerable knob (`t_start` for the
re-solve), not a re-description of this one.

This section does not promote K7 and does not touch `docs/CLAIMS.md`.

## 8. Limitations, declared before the numbers

* **L1 — one seed.** Seed 42 only, matching K7's own record. Per-record pairing
  gives a CI on the paired difference, not a seed-level CI.
* **L2 — `lam` is a state-space mix, not a distribution-space mix.** Blending
  `m·prior + (1 − m)·((1 − lam)·prior + lam·simplex)` is algebraically a higher
  effective memory fraction, so a `lam` that wins is a statement about this
  schedule's `m`, not a new family of operators.
* **L3 — the grid is coarse.** Seven points across a segment. A narrow bulge
  between grid points would be missed; a bulge that matters should not be.
* **L4 — N = 1000, NFE = 10.** Same instrument as K7 and round 1, which is what
  makes the numbers comparable. It is not the production NFE.
* **L5 — the arm is the framework arm of one config.** No claim is made about
  other adapters or other `R`.
