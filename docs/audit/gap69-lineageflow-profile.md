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

_Pending: `reproduce/gap69_profile_init.sh` is running at the pre-registered
config (N=1000, NFE=150, R=3, β=1.0). Decision rule §0.4 applies unchanged._

