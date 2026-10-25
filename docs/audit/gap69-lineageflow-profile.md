# GAP-69 — Profile-aware perturbation on R1 (LineageFlow): does protein knowledge buy anything?

**Date:** 2026-10-22
**Author:** GAP-69 agent (USER AUTHORIZED, NO PUSH)
**Scope:** `todo.json` `GAP-69-ADAPTER-LINAGEFLOW-PROTEIN` (P0). R1's +74 % hmmscan
hit gain is the flagship positive, and its mechanism is a **per-record random
initial state** (D-004b), not a design. GAP-69 asks whether replacing that
isotropic random draw with a **Pfam-profile-aware** draw turns R1 into a
mechanism that can be described in one sentence.
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` read-only; the Pfam HMM is only
stream-parsed, never modified or re-indexed).

---

## 0. Pre-registration (written BEFORE any code, any run, any number)

This section is the contract. It is committed before the extractor, the policy,
and the sweeps exist. Anything below §0 is outcome, not plan.

### 0.1 The four arms

All arms share: seed 42, `N = 1000`, `NFE = 150`, `R = 3`, `β = 1.0`
(`memory_fraction = 0`), the same per-record `(family_id, length)` RNG stream
(`random.Random(seed ^ 0x5A5A)`), and the same per-record solver seed
`seed + i`.

| arm | init / fresh-restart draw | model | existing artifact |
|---|---|---|---|
| **A** `baseline` | bare-RNG draw over `FAMILY_PROFILES[f]["bias"]` | no | `gap58-r1-beta1-n1000/seed42` → **158** |
| **B** `init-only` | `softmax(randn(256, 20))` (D-004b) | yes | `gap58-r1-beta1-n1000/seed42` → **284** |
| **C** `conservation` | `softmax(c_i · log p_i + (1 − c_i) · randn(20))` | yes | **new** |
| **D** `hmm-draw` | `a_i ~ Categorical(p_i)`, no model, same lengths/families | no | **new (CPU, minutes)** |

* `p_i` — the assigned family's Pfam **match-emission** distribution at profile
  column `round(i · (M−1)/(span−1))`, `M` = HMM `LENG`, `span = max_len = 150`.
* `c_i = IC_i / log2(20)` — the normalised information content of that column,
  `IC_i = log2(20) + Σ_a p_ia log2 p_ia`, so `c_i ∈ [0, 1]`.
* `c_i = 1` ⇒ the draw **is** the HMM emission (arm D's distribution, but
  decoded by argmax rather than sampled — see §0.5 L5).
* `c_i = 0` ⇒ exactly the D-004b `softmax(randn)` draw (arm B).

So arm C is the single-parameter interpolation between "no protein knowledge"
and "pure Pfam profile", with **zero free hyperparameters**: `c` is read off
the HMM, `span` is the sweep's own `--max-len`.

### 0.2 Why the comparison arm is B, not A

`docs/audit/r1-d004b-attribution.md`: `B (init-only) ≥ C_framework`, and
`B − A = +123.7` hits. Beating A again proves nothing new. The only question
worth compute is **B → C**.

### 0.3 The metric problem, stated up front

`gap58`'s own `upstream_eval.json` reports, for **both** arms:

```
family_validity__top1_family_accuracy      = 0.0
family_validity__topk_contains_intended    = 0.0
family_validity__intended_hit_rate_evalue  = 0.0
```

i.e. **not one of the 2000 generated sequences hits its own assigned family.**
The headline `hmmscan_total_hits` counts hits to *any* Pfam family. A
profile-aware draw aimed at the assigned family therefore has **no target** in
the headline metric. This is research item (b) of the gap answered from
existing data, before spending compute.

Consequence for the pre-registration — two readouts, fixed in advance:

* **Primary (mechanistic, qualitative):** `intended_hit_rate_evalue`.
  Currently exactly `0.000` for A and B. Prediction: `C > 0`.
* **Secondary (headline, must not regress):** `hmmscan_total_hits`.
  Prediction: `C ≥ 0.85 · B` (non-inferiority, not superiority).

### 0.4 Decision rules (fixed before the run)

Let `H_C`, `H_B` be total hits and `I_C`, `I_B` the intended-family hit rates.

1. **Escalation to seeds 43/44** happens **only if**
   `H_C ≥ 1.15 · H_B` **and** the paired per-record bootstrap 95 % CI on
   `H_C − H_B` excludes 0 at seed 42.
   This is the gap's own acceptance rule, unchanged.
2. `I_C > 0` does **not** trigger escalation by itself. It is reported as a
   seed-42 lead and would need its own pre-registered run.
3. **Verdicts** (seed 42 unless escalated):
   * `SUPPORTED` — rule 1 fires at 3 seeds **and** `I_C > 0`.
   * `HEADLINE_GAIN_NO_FAMILY_IDENTITY` — rule 1 fires but `I_C = 0`.
   * `FAMILY_IDENTITY_ONLY` — `I_C > 0` but rule 1 does not fire.
   * `NO_PROFILE_GAIN` — `H_C < H_B` and `I_C = 0`.
   * `MODEL_REDUNDANT` — `H_D ≥ H_C` (pure HMM sampling already does as well as
     the model on the same metric).
4. **Anti-seed-shopping clause.** Seeds are a diagnostic axis, never a
   confirmatory lever. If seed 42 does not fire rule 1, the run stops at seed
   42 and the boundary is written down. No seed is added to make a null
   significant. (Standing user directive, reaffirmed at the close of GAP-68.)

### 0.5 Limitations, declared before the numbers

* **L1 — positional, not aligned.** `state position i ↔ profile column
  round(i·(M−1)/(span−1))` assumes an N-terminal colinear correspondence
  between the generated sequence and the family model. No aligner is run
  (`hmmalign` per record is out of budget and would make the arm depend on the
  aligner's own choices). This is a **proxy**, and it is the arm's main
  weakness: if C fails, L1 is a candidate explanation that this experiment
  cannot exclude.
* **L2 — profile version drift.** `FAMILY_PROFILES` keys are `.24`-era
  accessions; the vendored Pfam-A.hmm is the 2025-05 release
  (`PF00072.31`, `PF00005.34`, `PF00183.30`, `PF02517.25`). Families are
  matched by the stable `PF` number; the *model* differs from whatever the
  original `.24` profile was.
* **L3 — variant (b) is not implementable here.** The gap's variant (b)
  ("perturb the ESM-2 embedding only, keep sequence identity") has no
  implementation in this decode path: the endpoint is decoded by
  `argmax` over the AA dims only, so any perturbation that preserves the AA
  argmax is a **no-op on the output**. Implementing (b) would require
  perturbing inside the flow head, which is not an adapter-level operation.
  Stated as a boundary, not silently dropped.
* **L4 — `hmmfetch` is unusable.** `hmmfetch Pfam-A.hmm PF00072` fails with
  "not found in SSI index" (no `.ssi`; only the pressed `.h3f/.h3i/.h3m/.h3p`
  exist, and creating an index would write into the vendored tree). The
  extractor therefore **stream-parses** the 2.2 GB ASCII HMM file. Read-only.
* **L5 — arms C and D differ in decode.** C decodes by `argmax` after the ODE
  (the pipeline's canonical decode); D samples the AA categorically from `p_i`.
  D is a *ceiling reference*, not a paired arm: it answers "what would profile
  sampling alone score", not "C minus D is the model's contribution" with a
  CI.
* **L6 — n = 1 seed at the primary readout.** Per-record pairing gives a CI on
  `H_C − H_B`; it does **not** give a seed-level CI. A single-seed verdict is
  labelled as such.

### 0.6 What would falsify the design hypothesis

* `H_C ≤ H_B` ⇒ conservation weighting does not help; R1 stays an empirical
  perturbation result and the paper says so.
* `H_D ≥ H_C` ⇒ the model contributes nothing that pure Pfam sampling does not;
  R1 would have to be re-described as "profile sampling through a model".
* `I_C = 0` while `I_D > 0` ⇒ the model actively destroys family identity that
  the init supplied — a stronger negative than "no gain".

---

## 1. Observed facts (filled in after the runs)

### 1.1 What the existing metric files already say (§0.3 confirmed)

Both pre-GAP-69 arms have `top1_family_accuracy = 0.0`,
`topk_contains_intended = 0.0`, `intended_hit_rate_evalue = 0.0`. The headline
`hmmscan_total_hits` is a count of hits to *any* Pfam family. Confirmed from
`verification_outputs/gap58-r1-beta1-n1000/seed42/upstream_eval.json`; no new
compute was needed.

### 1.2 Arm D — pure Pfam-profile draw, no model (the ceiling reference)

1000 records, same `(family, length)` stream as the model arms, sampled
categorically from the assigned family's match emission. CPU only, seconds.

| metric | A baseline | B init-only | **D hmm-draw** |
|---|---:|---:|---:|
| `hmmscan_total_hits` | 158 | 284 | **1634** |
| `hmmscan_unique_queries` | 145 | 239 | **430** |
| `coverage_any_hit` | 0.145 | 0.239 | **0.430** |
| `intended_hit_rate_evalue` | 0.000 | 0.000 | **0.060** |
| `top1_family_accuracy` | 0.000 | 0.000 | **0.110** |
| `topk_contains_intended` | 0.000 | 0.000 | **0.142** |

Three facts follow, and they are the frame for everything below.

1. **The metric is not saturated.** `1634` hits is `5.75×` the model arm's
   `284`. There is a large amount of headroom above the current flagship
   number.
2. **The metric *does* reward family identity** — it is not a broken or
   unreachable readout. It is `0.000` for A and B because neither arm ever
   produces a family-like sequence, not because the e-value threshold is
   impossible at this length. §0.3's worry that the intended-family readout
   might be structurally unreachable is **refuted**.
3. **The model is not doing what the profile does.** Arm D has no model at
   all, and it dominates both model arms on every readout. So whatever the
   ESM-2 + flow head contributes, it is not "making the samples more
   protein-like" — it moves them *away* from the assigned family relative to a
   plain profile draw.

Arm D is not a paired arm (it decodes by categorical sampling rather than
`argmax`; limitation L5), so its numbers are a reference, not a contrast.

### 1.3 Arm C — conservation-weighted init (seed 42)

Config exactly as pre-registered: `N=1000`, `NFE=150`, `R=3`, `β=1.0`,
`--init-profile conservation`, same prior, `seed 42`.
Manifest: `init_profile_is_active = true`, `framework_fallback_per_family_count = {}`
(the §1.4 guard passed, so this is the profile arm).

**Pairing.** `baseline.fasta` md5 is `363cc04d…`, byte-identical to
`gap58-r1-beta1-n1000/seed42/baseline.fasta`. The `--init-profile` flag touches
only the framework arm's fresh-restart state, so the two runs are record-paired
by `qid` and per-record differences are meaningful.

| metric | A baseline | B init-only | **C conservation** | C/B |
|---|---:|---:|---:|---:|
| `hmmscan_total_hits` | 158 | 284 | **2329** | **8.20×** |
| `hmmscan_unique_queries` | 145 | 239 | **394** | 1.65× |
| `coverage_any_hit` | 0.145 | 0.239 | **0.394** | 1.65× |
| `intended_hit_rate_evalue` | 0.000 | 0.000 | **0.040** | — |
| `top1_family_accuracy` | 0.000 | 0.000 | **0.080** | — |
| `topk_contains_intended` | 0.000 | 0.000 | **0.184** | — |
| `score_margin_mean` | 2.336 | 2.336 | **3.429** | — |

**Paired per-record contrast, C − B (n = 1000, pairing by `qid`):**

| quantity | mean diff | sd | t | p (normal) | 95 % bootstrap CI |
|---|---:|---:|---:|---:|---|
| hits per record | **+2.045** | 4.944 | 13.08 | < 1e−38 | **[+1.744, +2.354]** |
| intended-hit rate | **+0.040** | 0.196 | 6.45 | 1.1e−10 | **[+0.028, +0.052]** |

**Rule 1 (§0.4): FIRES.** `H_C / H_B = 8.20 ≥ 1.15`, and the paired CI on
`H_C − H_B` excludes 0 by a wide margin. Escalation to seeds 43/44 is therefore
mandatory under the pre-registration, and `reproduce/gap69_profile_escalate.sh`
is running it. **No verdict is issued until those two seeds land** — §0.4.3
requires 3 seeds for `SUPPORTED`.

Note what rule 1 is a rule *about*: it was written on `hmmscan_total_hits`,
which the decomposition below shows is ~92 % PF00005. So a 3-seed confirmation
will confirm **a PF00005 effect**, not a general profile-aware effect. Rule 1 is
left exactly as pre-registered — changing it after seeing the data would be the
thing the anti-seed-shopping clause exists to prevent — but the scope of what it
can establish is narrowed here, in the same section as the number, not in a
discussion afterwards.

**The 8.2× is one family, not four.** Decomposing by the record's assigned
family kills the "profile init helps protein generation" reading:

| assigned family | n | B hits | C hits | ratio | Δ hits/record | t |
|---|---:|---:|---:|---:|---:|---:|
| **PF00005** (ABC transporter ATPase) | 250 | 77 | **2141** | **27.81×** | **+8.256** | **19.56** |
| PF00072 (response regulator) | 250 | 68 | 58 | 0.85× | −0.040 | −0.83 |
| PF00183 (HSP90) | 250 | 72 | 58 | 0.81× | −0.056 | −1.24 |
| PF02517 (CitB) | 250 | 67 | 72 | 1.07× | +0.020 | +0.41 |

**Excluding PF00005, C/B = 0.908 (n = 750, Δ = −0.025 hits/record, t = −0.93).**
The conservation init does nothing — slightly negative, not significant — on
three of the four families. Every one of C's 40 intended-family hits and 184
top-k recalls comes from PF00005. So the honest one-line summary of seed 42 is
*"PF00005's profile works; the other three do not"*, not *"profile-aware init
works"*.

**Why PF00005 and not the others — the metric's "any family" definition.** It is
not a difference in how much profile information was injected: mean
conservation is 0.175 / 0.172 / 0.174 / 0.176 across the four families (§0.1's
`c` is read off the HMM, so this was not a tunable). The difference is what the
resulting sequence *matches*. C's PF00005 records hit **187 distinct Pfam
models**, and the top of that list is the whole P-loop NTPase / AAA+ clan:

```
PF00005 185   PF13555 173   PF13191 101   PF03193  99   PF13401  94
PF05729  90   PF25199  89   PF13476  63   PF20720  61   PF13481  60
PF12775  53   PF00437  41   PF13671  39   PF02492  38   PF00931  34
```

A profile init that produces a recognizable P-loop (Walker A/B) motif lights up
dozens of related models at once, and `hmmscan_total_hits` counts hits to *any*
Pfam family. So the headline gain is substantially a **motif-promiscuity
effect**: one short, ubiquitous motif matching a clan of ~187 models. That is a
real property of the generated sequences, but it is not "the sample resembles
its intended family" — only 40/250 do.

**Diversity is intact, so the count is not duplicates.**
1000/1000 sequences are unique in every arm, and the length distribution is
identical to B (mean 90.4, sd 35.6, min 30, max 150) because lengths come from
the same `(family, length)` RNG stream. The 8.2× is not a diversity collapse.

**C vs D (the ceiling reference) — the model now adds, it no longer subtracts.**
Arm D, with no model at all, scored 1634. Arm C scores 2329, i.e. **1.42× the
pure-profile reference**, and beats D on `topk_contains_intended`
(0.184 vs 0.142). D still leads on `hmmscan_unique_queries` (430 vs 394),
`intended_hit_rate_evalue` (0.060 vs 0.040) and `top1` (0.11 vs 0.08). Read
honestly: **C is not uniformly better than D**. The `MODEL_REDUNDANT` falsifier
(`H_D ≥ H_C`) is not triggered, but neither is the model shown to dominate pure
sampling on family identity. The per-record truncation caveat below applies to D
more than to C.

**Caveat on the per-record hit cap.** `family_validity_per_seq.jsonl` records at
most 20 hits per sequence. C's per-record sum (2329) equals its
`hmmscan_total_hits`, so C is unaffected. D's per-record sum is 1485 against a
reported 1634 — 149 hits are truncated. The D reference is therefore a **lower
bound** on its own total, which only strengthens the reading that C > D on total
hits and weakens any claim that C > D on everything.

### 1.4 An invalidated run, and the guard it produced

The first attempt (2026-10-22 13:08–13:11 local) **completed with exit code 0
and produced a manifest that looked valid**, but it was not the profile arm.
GPU 0 was shared with three ~21.6 GB neighbours; the ESM-2 forward hit
`CUDACachingAllocator ... OOM on device 0` and `_write_framework_arm` did what
it is designed to do — substituted the **bare-RNG draw** for the record. All
1000 records fell back:

```
framework_fallback_per_family_count = {PF00005.27: 249, PF00072.24: 250,
                                       PF00183.19: 250, PF02517.18: 250}
```

The scored "framework" arm was **181 hits / 0.0 % intended**, i.e. a second
independent bare-RNG sample (baseline is 158). Had this been read at face
value it would have been reported as "the profile arm regresses R1 from 284 to
181" — a completely false conclusion.

Two changes, both additive:

* `tools.gen_lineageflow_n1000_fastas._assert_no_profile_fallback` — a profile
  arm now **fails closed** (`SystemExit`) on any fallback, before the manifest
  is written. The default (`--init-profile off`) path still tolerates
  fallbacks exactly as before.
* `reproduce/gap69_profile_init.sh` waits for ≥ 20 GB free on `cuda:0` before
  starting, so a shared-device OOM costs minutes, not hours.

The invalid artifacts are quarantined in
`verification_outputs/gap69-lineageflow-profile/seed42_INVALID_oom/` with a
`README.txt`. They are **not** evidence and no number from them appears above.

This is a general hazard for every model arm in the repo, not just GAP-69: the
defensive fallback is invisible unless someone reads
`framework_fallback_per_family_count`. The guard closes it for the arms where
the fallback is unambiguously invalid.

### 1.5 Second abort — user-directed, because `cuda:0` ran out of memory

2026-10-23 03:02 local. The user reported that GPU 0 was out of memory and asked
for the framework's job to be stopped. The escalation process tree
(`gap69_profile_escalate.sh` → `gap69_profile_init.sh` → the generator) was
terminated with `SIGTERM`; no framework process remains on the device. The
remaining GPU 0 occupancy after the stop belongs to other jobs, not to this repo.

The interrupted cell was `seed43_init_only` (arm B, `--init-profile off`). Its
`framework.fasta` held **134 of 1000 records** and ended on a header with no
sequence, i.e. truncated mid-write. The whole directory is quarantined as
`verification_outputs/gap69-lineageflow-profile/seed43_init_only_INVALID_aborted/`
and no number from it is used. The resume key of
`gap69_profile_escalate.sh` is `upstream_eval.json`, which was never written, so
a later rerun regenerates the cell rather than skipping it.

Cost: ~40 min of the first of four generations. The driver is unchanged and the
pre-registration is untouched.

**Resumed 2026-10-24.** `cuda:0` reported 2 MiB used / 0 % util (the 41.9 GB
neighbour had exited) and the user lifted the pause, so `gap69_profile_escalate.sh`
was restarted unchanged. The 20 GB headroom pre-flight passed (11.3 GB in use at
start, 34 % util), and `seed43_init_only` regenerates from scratch because its
`upstream_eval.json` was never written — the resume key still works as designed.
No parameter, seed, or scoring rule changed; the quarantined directory stays
quarantined and is never read.

---

### 1.6 Three seeds — the escalation result (2026-10-25)

`gap69_profile_escalate.sh` finished at `2026-10-24T23:57:32Z` with
`ESCALATION_DONE`. Both seeds passed the record-pairing assertion
(`cmp` on the two runs' `baseline.fasta`): seed 43 `82a4dae1…`, seed 44
`b8ecb79c…`, each identical across its `_init_only` and profile runs. No
parameter, seed, or scoring rule changed between seeds.

**Aggregate (`hmmscan_total_hits`, C over B, N = 1000/arm/seed):**

| seed | B init-only | C conservation | C/B | paired 95 % CI on hits/record | report |
|---:|---:|---:|---:|---|---|
| 42 | 284 | 2329 | 8.20× | [+1.744, +2.354] | `report_seed42.json` |
| 43 | 279 | 2250 | 8.06× | [+1.686, +2.270] | `report_seed43.json` |
| 44 | 281 | 2376 | 8.46× | [+1.797, +2.405] | `report_seed44.json` |

Rule 1 fires at all three seeds (ratio ≥ 1.15 and the CI excludes 0 in each).
The aggregate is reproducible to ±0.2× across seeds.

**Per-family (the condition the acceptance rule also requires).** Computed by
`tools/gap69_per_family.py` → `per_family_3seed.json`; pairing by `qid`,
grouping by `intended_family_canon`, n = 250 per family per seed.

| family | seed 42 | seed 43 | seed 44 | seeds ≥ B | mean C/B |
|---|---:|---:|---:|---:|---:|
| **PF00005** | 27.81× | 40.90× | 31.61× | 3/3 | 33.44× |
| PF00072 | 0.85× | 0.74× | 0.78× | **0/3** | 0.79× |
| PF00183 | 0.81× | 0.87× | 0.73× | **0/3** | 0.80× |
| PF02517 | 1.07× | 1.10× | 1.42× | 3/3 | 1.20× |
| *excluding PF00005* | 0.908× | 0.895× | 0.920× | — | 0.908× |

The seed-42 concentration **replicates exactly**. PF00072 and PF00183 are below
the init-only arm at every seed (0/3), with per-seed paired CIs that include 0
(t = −0.83/−1.43/−1.36 and −1.24/−0.74/−1.86). PF02517 is nominally at or above
1.0 at every seed but is not a gain: its per-seed paired CIs all include 0
(t = +0.41/+0.62/+1.83). Excluding PF00005, the ratio is 0.908/0.895/0.920 —
the intervention does nothing on three families, at three seeds.

Recomputation note: the tool gives seed 42 PF00005 t = 19.52 where §1.3's ad hoc
table printed 19.56. The mean difference (+8.256) and ratio (27.81×) are
identical; the difference is the sd convention in the ad hoc computation. The
tool is now the canonical source for every per-family number.

**Verdict under §0.4.3: `HEADLINE_GAIN_NO_FAMILY_IDENTITY`.**

* rule 1 fires at 3/3 seeds — the aggregate condition is met;
* the per-family condition (`todo.json` GAP-69 acceptance: every family at or
  above the comparison arm) is met by 2 of 4 families;
* therefore GAP-69 is **not** a win, R1 does not become a 3-seed STRONG cell,
  and `GAP-79-R1-PER-FAMILY` opens.

This is the outcome §3 was written to bound, and it is the honest one: the
mechanism is real and reproducible, and it is a PF00005 mechanism.

---

## 2. Status

| item | state |
|---|---|
| §0 pre-registration | committed before any code/run (`9ec61f6d`) |
| arm D (ceiling reference) | done, CPU, `armD_hmm_draw/` |
| arm C seed 42 | done, rule 1 **fires** (`report_seed42.json`) |
| seeds 43/44 (B and C) | **done 2026-10-24T23:57:32Z**; both baseline arms byte-identical to their partners (`report_seed43.json`, `report_seed44.json`) |
| per-family, 3 seeds | done, `per_family_3seed.json` (§1.6) |
| verdict | **`HEADLINE_GAIN_NO_FAMILY_IDENTITY`** (§1.6): aggregate 3/3, families 2/4 → GAP-79 opens |

The escalation runs **both** arms per seed. Arm B exists only at seed 42 on this
config: the D-004b attribution runs
(`verification_outputs/r1_d004b_attribution_q4_2026/`) are `NFE=10` and are not
comparable to the `NFE=150` gap58 config. Each seed therefore needs two
generations (~7.5 h each) plus scoring, and the driver asserts the two runs'
baseline arms are byte-identical before the seed is accepted.

## 3. What this will and will not license

Written now, before the 3-seed verdict, so the claim cannot be inflated after
the fact.

**If seeds 43/44 confirm rule 1**, the defensible statement is narrow and
mechanical:

> On R1 (LineageFlow, `N=1000`, `NFE=150`, `R=3`, `β=1.0`), seeding the
> per-record fresh-restart state with the assigned family's Pfam match emission
> (weighted by that column's normalised information content) raises
> `hmmscan_total_hits` by ~8× over the D-004b init-only arm — **and that gain is
> entirely carried by PF00005**, whose profile yields a P-loop NTPase-like
> sequence that matches ~187 related Pfam models. On the other three families
> the intervention is null (C/B = 0.91, t = −0.93).

That is a much weaker claim than "protein knowledge helps", and it is the
strongest one the data supports.

**It does not license:**

* "protein knowledge improves protein generation" — one metric, one config,
  one adapter, one decode path.
* "the model learned family structure" — arm D reaches a comparable regime with
  no model at all; what C shows is that the *init* carries the signal and the
  model no longer destroys it.
* that `hmmscan_total_hits` measures family fidelity. It counts hits to *any*
  Pfam family, and 92 % of the gain is a single P-loop NTPase clan. A
  reviewer-facing statement must say "matches many ATPase-family models", not
  "recovers the intended domain".
* any statement about foldability, novelty or designability. Only
  `family_validity` was scored.
* escape from limitation **L1**. The positional correspondence
  `state position i ↔ profile column round(i·(M−1)/(span−1))` is a proxy with no
  aligner. If C's gain were an artifact of that proxy, this experiment cannot
  tell — a follow-up would need `hmmalign` per record, which is out of budget.
  This is the single largest threat to the result and it is declared in §0.5,
  not discovered afterwards.

The R1 claim in the paper stays "empirical perturbation result" until the
3-seed verdict exists. If seeds 43/44 fail, that is where it stays, and this
section is the record that the boundary was pre-declared.

**Resolved 2026-10-25 (§1.6).** Seeds 43/44 confirmed rule 1 and confirmed the
concentration: PF00005 3/3 at 27.81–40.90×, PF00072 and PF00183 0/3, PF02517
nominally ≥ 1.0 but n.s. at every seed. The quoted paragraph at the top of §3
therefore stands as written, with its numbers now measured at three seeds rather
than extrapolated from one. The verdict is
`HEADLINE_GAIN_NO_FAMILY_IDENTITY`; the paper-facing statement is the
narrow one above, and the mechanism work moves to GAP-79.

