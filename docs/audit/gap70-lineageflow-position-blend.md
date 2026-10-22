# GAP-70 (re-scoped to LineageFlow) — per-position restart blend and the K7 novelty drop

**Date:** 2026-10-23
**Author:** GAP-70 agent (USER AUTHORIZED, NO PUSH)
**Scope:** `todo.json` `GAP-70-ADAPTER-KANZI-LATENT`, **re-scoped by user
decision on 2026-10-23** from Kanzi to LineageFlow.
**Supersedes:** the Kanzi design in `docs/audit/gap70-kanzi-latent.md`, which
stays on record for its premise audit (§0.2 there: K7 is a LineageFlow cell, and
no Kanzi driver computes validity or novelty).
**Status:** code landed behind a default-off flag; **the run is not executed**
(GPU busy with the GAP-69 escalation).
**Frozen surfaces:** untouched.

---

## 0. Pre-registration (written before the run)

### 0.1 The hypothesis

K7 is the paper's worst cell: the framework arm produces **3.7 %** novel
sequences against the baseline's **46.6 %** (12.6× less novel, McNemar
p = 2.3e−102, one seed, N = 1000), while its Pfam hit rate rises from **53.8 %**
to **96.3 %**. `gap60` showed this is not a diversity collapse, so the samples
are diverse *and* recognisable — they all look like known Pfam families.

The current restart blend is uniform over positions:

```
theta_restart = m · theta_prior + (1 − m) · theta_fresh,     m = 1 − beta
```

Every position is pulled toward the prior at the same rate. If the prior carries
family identity in a few conserved columns, a uniform blend imports exactly the
thing K7 measures as un-novel, while also overwriting the positions that were
carrying the sample's own identity.

The lever: make the blend **position-selective**, and give the conserved columns
the *fresh* draw rather than the prior:

```
m_vec[j] = m · w[j],        w[j] = 1 − c[j]
```

where `c[j]` is the normalised information content of the Pfam column that
position `j` maps to (the same `profiles.json` GAP-69 built). Conserved columns
(`c → 1`) are fully re-randomised; variable columns (`c → 0`) keep the prior.

Note the **deliberate opposite polarity to GAP-69**: GAP-69 seeded the init with
the profile at conserved columns and raised Pfam recognisability; K7 penalises
exactly that. The two are the two ends of one knob, which is why the same
`profiles.json` serves both.

### 0.2 Why this is the right adapter

K7's samples are `data/lineageflow_n1000/{baseline,framework}.fasta`
(`n=1000, seed=42, nfe_per_record=10, n_rounds=3`), scored by
`tools/lineageflow/novelty_metric_pctid.py` over
`verification_outputs/novelty_pctid_w166_q3_2026/`. A Kanzi change cannot move
that number (`docs/audit/gap70-kanzi-latent.md` §0.2 P1).

### 0.3 The arms

Config is pinned to the K7 measurement, not to the GAP-69 config — a different
config would produce a number that cannot be compared with 3.7 % / 46.6 %.

| arm | restart blend | artifact |
|---|---|---|
| **B** scalar (K7's framework arm) | `m · prior + (1−m) · fresh` | `verification_outputs/novelty_pctid_w166_q3_2026/framework/` |
| **C** position-selective | `m · w · prior + (1 − m · w) · fresh`, `w = 1 − c` | **new** |
| **A** baseline | no restart | `verification_outputs/novelty_pctid_w166_q3_2026/baseline/` |

`N = 1000`, `seed = 42`, `nfe = 10`, `n_rounds = 3`, `restart_min_nfe = 5`
(gate open at NFE=10), `temperature = 1.0`, same `FAMILY_PROFILES` assignment.

### 0.4 Decision rules (fixed before the run)

Let `N_A`, `N_B`, `N_C` be the novel fraction (pctid < 30 % or no hit) and
`V_A`, `V_B`, `V_C` the Pfam hit rate, all on the same N = 1000.

1. **Validity must not fall.** `V_C ≥ V_B` with the paired 95 % CI on
   `V_C − V_B` excluding a drop larger than 2 pp. A blend that buys novelty by
   destroying validity is a trade, not a win.
2. **Novelty drop ≤ 2×.** `N_A / N_C ≤ 2`, i.e. `N_C ≥ 23.3 %` (half of the
   baseline's 46.6 %). This is the gap's own acceptance criterion.
3. **Falsification.** If `N_C` is within the CI of `N_B = 3.7 %`, the decoder
   prior / blend locality is **not** the lever and K7 stays an unexplained
   boundary. It is not reported as "a partial improvement".
4. **No seed shopping.** Seed 42 only, matching K7's own record. A second seed
   is run only if rules 1 and 2 both hold at 42, and then it is a replication,
   not a search.
5. **Verdicts.**
   * `POSITION_BLEND_SUPPORTED` — rules 1 and 2 hold.
   * `TRADE_NOT_WIN` — novelty rises but validity falls by more than 2 pp.
   * `NOT_THE_LEVER` — rule 3.
   * `INCONCLUSIVE` — anything else, with the failing quantity named.

### 0.5 Limitations, declared before the numbers

* **L1 — `w = 1 − c` is a proxy for "identity-carrying".** Conservation is not
  identity: a conserved column can be a structural scaffold rather than a
  family signature. The design has no free parameter precisely because there is
  no better signal available without a per-position decoder probe.
* **L2 — the positional mapping is the GAP-69 colinear proxy.** State position
  `j` ↔ profile column `round(j·(span−1)/(255))`, with no aligner. If the arm
  fails, this is a candidate explanation the experiment cannot exclude.
* **L3 — the synthetic adapter cannot exercise the operator.** Its `theta` is
  uniform to ~1e-7 and so is the fresh draw, so *every* blend of them is a
  numerical no-op (measured; see the test helper's docstring). Only the
  real-checkpoint path is informative — the same "wired but inert" trap GAP-44
  documented. A synthetic-mode run of this arm would produce byte-identical
  FASTA files and must be discarded, not reported.
* **L4 — one seed.** K7 is a one-seed cell and this arm matches it. The
  per-record pairing gives a CI on the paired difference, not a seed-level CI.

---

## 1. Code landed

`adaptive_reflow/adapters/lineageflow.py`:

* `LineageFlowAdapter(..., token_keep_weights: Any | None = None)`;
* validated at construction (length `LINEAGEFLOW_STATE_SHAPE[0]`, finite, in
  `[0, 1]`), so there is no silent fallback to the scalar blend;
* `m_vec = m · w` broadcast over the categorical dimension, followed by the
  existing row renormalisation;
* mutually exclusive with `classifier_aware_restart` (both write `m_vec`);
* `None` (default) keeps the scalar blend byte-identical.

`tools/gen_lineageflow_n1000_fastas.py`:

* `--token-keep-weights {off,conservation}` (default `off`);
* `_build_token_keep_weights` maps `conservation` to `w = 1 − c` per family;
* manifest records `token_keep_weights_mode` / `token_keep_weights_is_active`.

### 1.1 A self-caught defect: the first wiring was inert

Recorded because it is the same failure class as §0.5 L3 and GAP-44, and
because the endpoint tests did **not** catch it.

The first version computed the per-position `blended` in a standalone `if`
block and then fell through into the pre-existing scalar `if
classifier_aware_restart ... else:` chain. Since the two flags are mutually
exclusive, the `else` always ran and overwrote `blended` with
`mean(m·w)·prior + (1−mean(m·w))·fresh`. The operator was therefore a **scalar
blend with a shrunk memory fraction** — wired, validated, and inert.

Why the tests were blind: `w ≡ 1` and `w ≡ 0` agree under both readings, and the
"partial weights land between the two ends" test is satisfied by the collapsed
form too. Fixed by making the three branches a single exclusive `if / elif /
else`, and pinned by
`test_memory_is_redistributed_per_position_not_averaged`, which reconstructs the
fresh draw from the scalar run, asserts the per-position expectation to 1e-10,
and asserts the scalar-collapsed hypothesis is **rejected**.

## 2. Status

| item | state |
|---|---|
| §0 pre-registration | this file, committed before the run |
| adapter operator | landed, default off |
| operator is non-inert (per-position, not scalar-mean) | **asserted by test** (§1.1) |
| generator wiring | landed, default off |
| scoring + verdict tooling | landed (§3) |
| arm B/C run (N=1000, seed 42, NFE=10) | **not run** — GPU occupied by GAP-69 |
| canonical-DB novelty + Pfam validity | **not run** |
| verdict | none |

## 3. The scoring path, and a trap it avoids

`tools/gap70_position_blend_report.py` takes the three arms' m8 + validity
files and emits the §0.4 rules and one verdict. It is paired by record index and
asserts the family matches at every index before computing anything, so a
mis-ordered arm fails loudly instead of producing a plausible number.

The trap: the generator's built-in `novelty` metric searches the **200-sequence**
`data/lineageflow_upstream/databases/pfam35/pfam_holdout_targetDB`, and on this
data it saturates — GAP-69's seed-42 run reports `novelty_all = 1.0` for both
arms with `hits_kept = 0`. That is the same W280 artefact the K7 recipe already
documents. K7's 46.6 % / 3.7 % come from `mmseqs easy-search` against the
canonical **63.8 M**-sequence Pfam-A DB with `-s 7.5 -e 100`. The driver
therefore runs `gap55` with `--metrics family_validity` **only** (validity is
hmmscan and is sound) and does the novelty search separately against the
canonical DB. Nothing from the built-in novelty is quotable.

The whole run is one command once the GPU frees up:

```bash
bash reproduce/gap70_position_blend.sh          # SEED=42 by default
```

It generates **both** framework arms (scalar control and treatment) from the
current commit rather than reusing the W166 artifacts, so the C-vs-B comparison
never crosses a code era; it asserts the two `baseline.fasta` files are
byte-identical (the flag only touches the framework arm) before scoring, which
is what makes the per-record pairing valid. `B`'s novelty is then checked
against K7's 3.7 % as a sanity read, not used as an input.

Note the generator cannot reproduce W166's exact `framework.fasta` (no recorded
generation command survives for `data/lineageflow_n1000/`), so `N_B` here is
this commit's scalar arm, not necessarily 3.7 %. Rule 2 is written against
`N_A` for that reason — the ratio is internal to the run.

