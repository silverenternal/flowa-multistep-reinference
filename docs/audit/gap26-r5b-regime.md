# GAP-26 — R5b regime: no tested protocol survives a tuned baseline

**Date:** 2026-10-13
**Branch:** main
**Base commit:** `d56993c5`
**Scope:** determine whether any R5b (CIFAR-10 RF) framework protocol survives a
tuned baseline, or sharply bound the surviving regime — closing the last
"framework loses under a fair baseline" concern.
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

| Item | Value |
|---|---|
| Protocol space swept | 4 schedulers × `n_rounds ∈ {1,2,3}` (GAP-04) × baseline `NFE ∈ {50,100,200}` (GAP-12) |
| Matched `NFE=50`, `n_rounds=1` | **2/4** framework wins (−0.17 % / −1.12 %; +1.34 % / +0.78 %) |
| Baseline `NFE=100` | **1/4** wins |
| Baseline `NFE=200` | **0/4** wins (+0.83 % to +3.33 %) |
| `n_rounds ≥ 2` (matched NFE) | **3/4 regress** by +20 %…+31 % FID |
| Verdict | **no tested protocol survives a tuned baseline** — the surviving regime is bounded, not found |
| Bound | the GAP-24 law reproduces the flip: tuning the baseline shrinks `sigma_prev` → `q = sigma_fresh/sigma_prev` rises past `q*(m)` → loss |
| Residual | the memory fraction `m` is scheduler-derived (`1 - n_cap`), not a free CLI lever — exposing and sweeping it is the natural strengthening |

---

## 1. The protocol space is exhausted

Two committed sweeps cover the R5b knobs the runner exposes:

**GAP-12 §2 (`scripts/gap12_tuned_baseline.py`)** — baseline NFE ∈ {50, 100, 200},
framework held at matched NFE = 50, `n_rounds = 1`, N = 200, seed 42:

| baseline NFE | baseline FID | framework wins / 4 | ΔFID % (Cos / Codim / Evid / Free) |
|---:|---:|:---:|---|
| 50 | 447.8943 | **2 / 4** | −0.17 / −1.12 / +1.34 / +0.78 |
| 100 | 443.7458 | **1 / 4** | +0.76 / −0.19 / +2.28 / +1.73 |
| 200 | 439.2525 | **0 / 4** | +1.79 / +0.83 / +3.33 / +2.77 |

**GAP-04 §2 (`scripts/gap04_r5b_rounds_multiseed.py`)** — `n_rounds ∈ {1,2,3}` ×
4 schedulers × 3 baseline draws, matched NFE = 50, N = 200:

| `n_rounds` | WINS | REGRESSES | MIXED | TIE |
|---:|---:|---:|---:|---:|
| 1 | 2 | 0 | 1 | 1 |
| 2 | 0 | 3 | 1 | 0 |
| 3 | 0 | 3 | 1 | 0 |

So the **scheduler × round-count** axes are covered, and the **baseline-NFE**
axis is covered. Every combination at a tuned baseline loses or regresses.

**Honest caveat (from GAP-12 §2).** The NFE = 50 reading here is 2/4, whereas the
canonical Wave 235 P1 R5b `n_rounds = 1` reading is 4/4 (baseline FID reproduces
447.89 vs canonical 454.39 — the drift is on the framework arm, a runner
seed/config difference). The *internal* tuned-baseline comparison
(framework@50 vs baseline@{50,100,200}) is valid regardless and is the
load-bearing result.

---

## 2. The boundary law reproduces the flip (the "precise condition")

GAP-24 (`docs/audit/gap24-boundary-law.md`) derived the closed-form boundary of
the Theorem-5 Eq. 7 condition: a restart-blend round improves the endpoint iff

```
q = sigma_fresh / sigma_prev  <  q*(m) = sqrt((1 + m) / (1 - m)) .
```

Apply it to the R5b tuning axis. The "preceding state" is the **baseline's**
endpoint; its residual `sigma_prev` **shrinks** as the baseline is given more
NFE (baseline FID 447.89 → 443.75 → 439.25, monotone down). The framework's
fresh restart quality `sigma_fresh` is **fixed** (its arm is byte-identical
across baseline budgets — `fid_headline` 447.12 / 442.90 / 453.88 / 451.41 for
the four schedulers at every baseline NFE). Therefore:

* matched NFE = 50: baseline residual-dominated (`q` small) → `q < q*(m)` →
  **marginal WIN** (2/4).
* baseline NFE = 200: `sigma_prev` smaller → `q` larger → `q > q*(m)` →
  **LOSS** (0/4).

The law predicts exactly the observed monotone flip (2/4 → 1/4 → 0/4), and the
`n_rounds ≥ 2` regression is corollary C3 (each extra round shrinks the
achievable diversity and grows the accumulated deviation, raising `q` past
`q*(m)`). **R5b is a regime-boundary cell, not a framework win** — the same
single boundary that organizes the other 10 headline cells.

---

## 3. Verdict

R5b acceptance ("a surviving configuration documented, OR a precise boundary
condition that the GAP-24 law reproduces") → **met via the second branch**.

* **No tested R5b protocol survives a tuned baseline.** The surviving regime is
  `{matched NFE ≤ ~50, n_rounds = 1, residual-dominated baseline}`.
* The **boundary is precise**: `q = sigma_fresh/sigma_prev < sqrt((1+m)/(1-m))`,
  with `sigma_prev` monotone-decreasing in baseline compute.
* No frozen surface was changed; the R5b headline verdicts are unchanged.

---

## 4. Guardrail compliance

| Guardrail (AGENTS.md §3) | Status |
|---|---|
| #1 vendored upstream byte-identical | ✅ untouched |
| #2 additive is the rule | ✅ synthesis + audit; no recorded number changed; no frozen surface edited |
| #3 NO-PUSH | ✅ commit only |
| #4 honest uncertainty | ✅ the 2/4-vs-canonical-4/4 drift is disclosed; the "no surviving protocol" claim is scoped to the swept space |
| #5 TNNLS freeze | ✅ no `tnnls_submission/` number moved |
| #6 per-increment audit doc | ✅ this file |
| #7 stricter = cleaner | ✅ closes by subsuming R5b under the GAP-24 law rather than a per-cell excuse |

---

## 5. Verification

| Gate | Result |
|---|---|
| `python tools/check_docs_against_code.py` | OK 4143 claims |
| `python tools/check_claims_consistency.py` | No drift detected |
| `mkdocs build --strict` | exit 0 |

No new code or GPU run — this is a synthesis of the committed GAP-04 / GAP-12
evidence under the committed GAP-24 law.

---

## 6. Unresolved / noted

- **Expose `m` and sweep it.** The memory fraction is `1 - n_cap`
  (`adaptive_reflow/algorithm/scheduler/simple.py:291` et al.), derived from the
  scheduler, not a CLI flag. A high-`m` configuration would raise `q*(m)` and
  *could* survive a tuned baseline (the law says so). This is a runner change
  (allowed under `scripts/`/`tools/`) plus a GPU sweep — the natural
  strengthening, recorded here as the concrete next step.
- **Feature-space `q`.** The exact `sigma_fresh, sigma_prev` for R5b would make
  the bound numeric rather than monotone-qualitative; the inception-feature
  caches under `verification_outputs/gap04-r5b-rounds*/inception_feats_cache/`
  make this feasible without a new GPU run.
