# GAP-48 — K7 two-arm novelty, paired per record

**Date:** 2026-10-18
**Branch:** main
**Scope:** replace the K7 "direction inverted" reading's marginal-count
support (466/1000 vs 37/1000) with a **paired per-record** test over
the same frozen `mmseqs2` m8 files, with a 95 % CI. Analysis only — no
FASTA generation, no new `mmseqs2` search, no frozen surface touched.
**Frozen surfaces:** untouched (`docs/CLAIMS.md`,
`docs/CONSOLIDATED_RESULTS.md`, `docs/drafts/paper-A-final.*`,
`tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

| Item | Value |
|---|---|
| Verdict | **direction INVERTED — CONFIRMED**, not withdrawn |
| Threshold | `pctid < 30 %` (the canonical K7 threshold) |
| Baseline novel | **466 / 1000 = 46.6 %** |
| Framework novel | **37 / 1000 = 3.7 %** |
| Paired Δ (fw − bl) | **−0.4290** (−42.9 pp) |
| 95 % CI (Newcombe, paired) | **[−0.4609, −0.3946]** — excludes 0 by a wide margin |
| Exact McNemar p | **2.30 × 10⁻¹⁰²** (K-level α = 0.0125) |
| Discordant pairs | framework-only novel **26**, baseline-only novel **455** |
| Structural signal | paired `mean_max_pctid` (both-hit records) **+2.33 pp**, t(511) = 3.80, p = 1.6 × 10⁻⁴ |
| Seeds | **1** (seed 42, N = 1000) — see §4 |
| Artifact | `verification_outputs/gap48-k7-two-arm/paired.json` |

The direction is not an artifact of unpaired aggregation: the two arms
disagree on 481 of 1000 records, and the disagreement is 17.5 : 1 in
the direction of the baseline being more novel.

---

## 1. Method

### 1.1 Inputs (frozen, in-git)

| file | SHA-256 |
|---|---|
| `verification_outputs/novelty_pctid_w166_q3_2026/baseline/n1000_full_loose.m8` | `e4d5a52c…1aedde` |
| `verification_outputs/novelty_pctid_w166_q3_2026/framework/n1000_full_loose.m8` | `4d667b9a…ad94b2` |

These are the exact files behind the W166 P3 canonical counts. The
`mmseqs2` configuration is recorded in
`novelty_results_full.json:metadata.sweep_config` (sensitivity 7.5,
`-e 100`, target = the 63.8 M-sequence `pfam_canonical` W164 build,
query = the W158 N=1000 LineageFlow FASTAs).

### 1.2 Pairing

Query ids are `baseline_seed<I>|family=<F>` and
`framework_seed<I>|family=<F>`, where `I` is the record index emitted
by the generator's single record loop. The tool strips the arm prefix
and pairs on `I`; it **asserts** that every shared index agrees on
`family` (512 shared indices, 0 mismatches) before computing anything.
Records with no hit in an arm are treated as novel, matching
`novelty_metric_pctid.py`'s definition.

### 1.3 Statistics

* **Paired risk difference** `p_fw − p_bl` with a **Newcombe (1998)
  method-10** hybrid-score 95 % CI, which accounts for the pairing via
  the phi coefficient and stays inside `[−1, 1]`.
* **Exact McNemar** (two-sided binomial on the discordant pairs) — the
  correct test for paired binary outcomes.
* **Paired t** on the per-record binary delta, reported for continuity
  with the repo's other cells (it agrees with McNemar here because
  n = 1000 is large).
* **Paired t** on `max_pctid` among records with a hit in both arms —
  the "framework recapitulates known Pfam structure" signal.

Runner: `tools/gap48_k7_two_arm_novelty.py`.

```bash
python3 tools/gap48_k7_two_arm_novelty.py \
  --baseline-m8 verification_outputs/novelty_pctid_w166_q3_2026/baseline/n1000_full_loose.m8 \
  --framework-m8 verification_outputs/novelty_pctid_w166_q3_2026/framework/n1000_full_loose.m8 \
  --n-total 1000 --thresholds 20,30,50 \
  --out verification_outputs/gap48-k7-two-arm/paired.json
```

---

## 2. Results

### 2.1 Per-threshold paired table

| threshold | baseline novel | framework novel | Δ (pp) | 95 % CI | McNemar p |
|---|---:|---:|---:|---|---:|
| `pctid < 20` | 462 | 37 | **−42.50** | [−45.69, −39.06] | 2.95e−101 |
| `pctid < 30` | 466 | 37 | **−42.90** | [−46.09, −39.46] | 2.30e−102 |
| `pctid < 50` | 751 | 517 | **−23.40** | [−27.47, −19.29] | 2.99e−27 |

The inversion holds at all three thresholds; its magnitude shrinks as
the threshold loosens (at 50 % identity most framework sequences are
still "novel", so the gap narrows).

### 2.2 2 × 2 at `pctid < 30`

| | framework novel | framework not novel |
|---|---:|---:|
| **baseline novel** | 11 | 455 |
| **baseline not novel** | 26 | 508 |

`phi = −0.066`. The inversion is carried by 455 baseline-only-novel
records against 26 framework-only-novel records. It is not a
threshold-boundary effect on a handful of ties.

### 2.3 Hit coverage

| quantity | baseline | framework |
|---|---:|---:|
| records with ≥ 1 hit | 538 | 963 |
| records with no hit | 462 | 37 |

The framework arm hits the Pfam target for 96.3 % of records vs 53.8 %
for the baseline. This reproduces the paper's "hit-rate 53.8 % →
96.3 %" disclosure exactly.

### 2.4 Structural-correctness signal

Among the 512 records with a hit in **both** arms, the framework's
`max_pctid` is **+2.33 pp** higher (sd 13.84, t(511) = 3.80,
p = 1.6 × 10⁻⁴). The paper's disclosure says "+2.14 pp"; the small
difference is an aggregation choice (paired both-hit records here vs
the earlier all-hit mean). The direction and magnitude agree: the
framework produces sequences that are *closer* to known Pfam
sequences, which is why it is *less* novel.

---

## 3. Interpretation

1. **The K7 verdict stands.** "Direction INVERTED" is confirmed at the
   record level with a CI that excludes 0 by ~7 SE. The paper's
   authoritative reading (46.6 % vs 3.7 %) is correct.
2. **The "one-arm driver" caveat is now separable.** The W280 P driver
   really did score `baseline.fasta` only and produced the `d_z = ∞`
   artifact. But the W166 P3 evidence is a genuine two-arm search over
   the same 1000 records, and this increment shows the two arms are
   pairable record-by-record. The caveat applies to W280 P, not to the
   K7 headline.
3. **No promotion.** The cell remains PARTIAL / SUPP. A confirmed
   inversion is a *negative* result for the novelty claim; it does not
   become SUPPORTED by being significant.
4. **The structural reading is consistent.** Fewer novel sequences and
   higher identity to known Pfam families are the same phenomenon. The
   K7 cell is evidence for structural recapitulation, not for novelty.

---

## 4. Caveats and the seed question

* **One seed (42), N = 1000, paired.** The per-record design gives
  n = 1000 pairs, which is the powered substitute for a 3-seed design
  (same logic as GAP-27's per-record R3 design). A seed-level
  replication would be better; it is **not obtainable from existing
  artifacts**:
  * the canonical `mmseqs2` target DB (63.8 M sequences, W164 build)
    is **not on disk**, so seeds 43/44 cannot be searched against it;
  * the seed-43/44 N=1000 FASTAs were never retained;
  * the seed-43/44 N=200 NFE=150 FASTAs that do exist (GAP-41b) would
    have to be scored against the 200-sequence `pfam_holdout_targetDB`,
    whose novelty is saturated at 1.0 in both arms (W280 P) — that is a
    different metric, not a replication.
* **Regenerating a 3-seed replication** requires rebuilding the
  canonical target DB (≈63.8 M sequences) and re-running
  `easy-search` on 6 × 1000 queries. That is a multi-hour,
  multi-hundred-GB job and is **not** part of this analysis-only
  increment. Recorded as the smallest next action if a seed-level
  replication is ever required.
* **`pctid < 30` is the pre-registered threshold**; the 20 / 50 rows
  are sensitivity, not additional tests.

---

## 5. Verification

| command | result |
|---|---|
| `ruff check tools/gap48_k7_two_arm_novelty.py` | All checks passed |
| `python3 tools/gap48_k7_two_arm_novelty.py …` | reproduces 466 / 37 and the paired table |
| `pytest tests/test_d4_regression_vectors.py -q` | 30/30 PASS |
| `python3 tools/check_claims_consistency.py` | exit 0, no drift |
| `mkdocs build --strict` | exit 0 |

The m8 inputs are byte-frozen (SHA-256 above), so the analysis is
exactly reproducible on a fresh clone.

---

## 6. Unresolved / noted

* Seed-level replication blocked on the canonical target DB (§4).
* The paper's K7 row still says the audited driver is one-arm. That
  statement is true of W280 P and misleading about W166 P3; an additive
  manuscript clarification is a frozen-surface edit and remains
  **user-gated** (folded into GAP-29).
* `CLM-060`'s K7 status is unchanged (PARTIAL / SUPP). This increment
  supplies the paired CI; it does not change the status label.
