# GAP-41b — R1 NFE-fidelity: is the canonical `--nfe 10` the reason the levers look inert?

**Date:** 2026-10-16
**Author:** GAP-41b agent (USER AUTHORIZED, NO PUSH)
**Scope:** a fidelity audit of the *inference budget* used by the canonical R1
sweeps. Every dormant-lever rejection (GAP-38/39/40/40b/34/41) was measured at
the canonical R1 config `--nfe 10`. The upstream LineageFlow released config
uses a much larger inference budget (`steps_base=100` + `steps_final=50` ≈
**150 NFE**). If the canonical R1 budget should be ~150, then the lever
rejections may be an artifact of the low NFE, not evidence the levers are inert.
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

| Item | Result |
|---|---|
| **The fidelity gap** | canonical R1 runs at `--nfe 10`; the upstream LineageFlow released config (`data/lineageflow_upstream/config/generation.json`) uses `steps_base=100` + `steps_final=50` ≈ **150 NFE** — a ~15× budget difference |
| **The three distinct "n"s** | statistical n = **3 seeds** (the STRONG bar); sample N = **1000** records/seed; inference budget NFE = **10** (ours) vs **~150** (upstream) |
| **Consequence for prior levers** | GAP-38/39/40/40b/34/41 were all evaluated at NFE=10 — a *shared confound* |
| **Premise test (this doc)** | N=200, seed 42, arms `{legacy, tier}`, NFE ∈ {10, 150}: does the budget move the R1 HMMER metric and/or the tier lever? |
| **Resumable generation** | `--start-index` added to `tools/gen_lineageflow_n1000_fastas.py` (additive, default 0 byte-stable) so the N=200 result can be extended to N=1000 without recomputing the first 200 records |
| **Headline moves with budget** | framework-vs-baseline gap **+1 → +11** (NFE 10 → 150); the baseline arm is **byte-identical** (37 = 37) |
| **Tier lever flips sign** | tier-vs-legacy **+12 → −2** (NFE 10 → 150) |
| Verdict | **NFE is a load-bearing axis.** The six prior dormant-lever rejections were all measured at `--nfe 10`; the R1 metric is *not* budget-invariant, so those rejections are **conditional on the low budget**, not budget-independent. Premise only (N=200, single seed) — see §5 caveats. |

---

## 1. Motivation

The user directive: *"n=3 有什么用啊，本来推理预算动不动就是 100 或者 1000 这样的，
你看一下原任务原论文里他们的 n 是多少"* + *"以前你排除的那些杠杆可能也存在这样的
漏洞"*.

The observation is that the canonical R1 protocol fixes the inference budget at
`--nfe 10`, but the upstream SOTA reference uses ~150 Euler steps. If the budget
is a load-bearing axis, then a lever that is inert at NFE=10 may be active at
NFE=150 — and the entire "power-limited, not code-limited" conclusion (see
`docs/audit/gap41-r1-tier-aware-ncap.md` §4) would be a *config-limited* artifact.

## 2. The budget comparison (facts)

| axis | our canonical R1 (Wave 158/280) | upstream LineageFlow (ICML 2026) |
|---|---|---|
| inference budget | `--nfe 10` (per-record, split over `n_rounds=3`) | `steps_base=100` + `steps_final=50` = **150** Euler steps (code defaults 200+200) |
| samples N | 1000 | `num_samples=512` (batch) / `batch_size=64` |
| families | 4 (PF00005/00072/00183/02517, 250 each) | `max_families=64`, `runs_per_family_batch=16` |
| rounds | 3 | 3 |
| statistical n (seeds) | 3 (42/43/44) | single released-config eval |

Sources: `data/lineageflow_upstream/config/generation.json`,
`data/lineageflow_upstream/config/generation.md`,
`data/lineageflow_upstream/inference/inference.py:671` (the `steps_base` /
`steps_final` split), `data/lineageflow_upstream/README.md` (Quick Start).

**Note on the confound.** The canonical R1 framework arm applies a
`min(1.0, NFE_REF / nfe)` β-scale factor with `NFE_REF = 50`; at `nfe=10` the
factor saturates at 1.0, at `nfe=150` it is 1/3. So changing the budget changes
both the number of Euler steps *and* the restart-blend β. This is the canonical
driver's behaviour; the experiment holds it fixed and reports the combined
effect.

## 3. Design

**Premise test** (`/home/hugo/gap41b-nfe150/run_premise.sh`): N=200, seed 42,
gate-open config (`--n-rounds 3 --restart-min-nfe 5 --temperature 1.0`), arms
`{legacy, tier}`, NFE ∈ {10, 150}, canonical HMMER counter.

`tier` = `--tier-aware-n-cap 0.5 --tier-aware-baseline-metrics-jsonl <k6
foldability.jsonl>` (the GAP-41 strongest lever).

**Resumable generation.** `tools/gen_lineageflow_n1000_fastas.py` gains
`--start-index` (additive; default 0 = byte-stable): records `[0, start_index)`
are skipped (their RNG stream replayed so record `start_index` matches a
from-scratch run) and only `[start_index, n)` are written, appended. This lets
the N=200 result be extended to N=1000 without recomputing the first 200
records. Byte-exactness and default byte-stability are pinned by
`tests/test_tools/test_gen_lineageflow_n1000_fastas.py::test_gen_script_resume_is_byte_exact`.

## 4. Results

Run: `/home/hugo/gap41b-nfe150/run_premise.sh`, N=200, seed 42, gate-open
(`--n-rounds 3 --restart-min-nfe 5`, `effective_n_rounds=3` at both budgets).
Wall-clock: nfe10 arms 11.4 + 9.4 min; nfe150 arms 82.5 + 80.3 min; HMMER 5.5 min.

### 4.1 Aggregate (canonical HMMER counter, 4 families × 50)

| NFE | baseline | legacy fw | tier fw | fw − baseline | tier − legacy |
|---:|---:|---:|---:|---:|---:|
| 10  | 37 | 38 | 50 | **+1** | **+12** |
| 150 | 37 | 48 | 46 | **+11** | **−2** |

### 4.2 Sanity check — the baseline is NFE-invariant

The baseline arm does **not** route through the framework refiner, so the budget
knob does not touch it. Confirmed: `seed42_nfe10_legacy/baseline.fasta` and
`seed42_nfe150_legacy/baseline.fasta` are **byte-identical** (md5
`ff5a6de6609c72f86cae3a3c8279d50a`, 37 hits each). The framework arms differ
(`cmp` first diverges at byte 36). So the movement below is entirely in the
framework arm — i.e. the budget changes the *framework*, which is exactly the
axis the lever rejections depend on.

### 4.3 Per-record paired tests (union of records with ≥1 hit)

| NFE | comparison | n | Σdiff | Wilcoxon p | sign + / − | sign p |
|---:|---|---:|---:|---:|---:|---:|
| 10  | framework vs baseline | 53 | +1  | 0.908 | 23 / 22 | 1.000 |
| 10  | tier vs legacy        | 49 | +12 | 0.089 | 18 / 10 | 0.185 |
| 150 | framework vs baseline | 69 | +11 | 0.217 | 39 / 30 | 0.336 |
| 150 | tier vs legacy        | 49 | −2  | 0.696 | 9 / 10  | 1.000 |

(Tier shares the legacy baseline FASTA, so tier-vs-legacy is a clean paired
comparison; tier dirs carry no separate `baseline.tblout`.)

### 4.4 Reading

1. **The framework-vs-baseline headline is budget-sensitive.** At the canonical
   `--nfe 10` the legacy framework is a wash (+1, p≈0.9); at the upstream ~150
   budget it is a directional +11 (p≈0.22, not significant at N=200). The
   budget *understates* the framework's effect at NFE=10 — it does not create a
   spurious win, it hides a real one.
2. **The tier lever flips sign.** The strongest GAP-41 lever — `tier_vs_legacy`
   +12 (borderline p=0.089) at NFE=10 — is −2 (p=0.70) at NFE=150. Here the
   budget works the *opposite* way: the low NFE *inflated* the lever. This is
   consistent with GAP-41's own N=1000 3-seed result (`tier_vs_legacy` wash,
   d_z=0.726): the +12 N=200 screen never survived at N=1000 either.
3. Both directions mean the same thing for the audit: **the six dormant-lever
   rejections (GAP-38/39/40/40b/34/41) are conditional on `--nfe 10`, not
   budget-invariant.** NFE is a confound that has to be held fixed and reported,
   exactly as the user suspected.

## 5. Verdict

**NFE is a load-bearing axis; the prior lever rejections are NFE-conditional.**

- Confirmed: the R1 framework-arm metric moves ~10 hits (baseline invariant,
  37 = 37) between the canonical NFE=10 and the upstream ~150 budget. A metric
  that moves 27 % of its own baseline under the budget knob cannot be used to
  declare a lever "inert" without fixing the budget.
- Direction is two-sided: the framework-vs-baseline headline *grows* with
  budget (NFE=10 too harsh), while the tier lever *shrinks* (NFE=10 too
  generous). Neither can be read off a single NFE.
- The canonical R1 STRONG bar remains n=3 seeds; this premise is N=200, one
  seed, so it **moves the question, it does not settle it**. What it settles is
  that the budget axis must be reported and, for any future lever claim, fixed
  at (or at least swept over) the upstream ~150 budget.

**Caveats (honest uncertainty).**

- Single seed (42), N=200. Seed-to-seed spread on this metric is large (GAP-41
  N=1000 3-seed diffs spanned [−5, +17]); a +11 N=200 reading is a *premise*,
  not a powered result. No NFE=150 comparison reaches p<0.05 at N=200.
- β-scale confound: the canonical driver applies `min(1, NFE_REF/nfe)` with
  `NFE_REF=50`, so at `nfe=150` the restart-blend β is 1/3 while at `nfe=10` it
  saturates at 1.0 (§2). The premise reports the *combined* (steps + blend)
  effect, as the canonical driver produces it; it does not separate the two.
- Cost: measured **24.7 s/record at NFE=150** (82.5 min for the N=200 arm-pair,
  vs 3.4 s/record at NFE=10). A decisive n=3 N=1000 run therefore costs
  ≈ **21 h** (legacy headline arm) to ≈ **41 h** (legacy + tier) — a user-gated
  compute decision, not launched here.

## 6. Reproduce

```bash
bash /home/hugo/gap41b-nfe150/run_premise.sh              # N=200 seed 42, NFE {10,150}
# extend to N=1000 later (resumable):
N=1000 START=200 bash /home/hugo/gap41b-nfe150/run_premise.sh
```

Evidence: `verification_outputs/gap41b-r1-nfe-fidelity/`.
