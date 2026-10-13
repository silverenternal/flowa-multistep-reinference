# GAP-25 — R1 restart-blend isolation (with an honest equivalence bound)

**Date:** 2026-10-13
**Branch:** main
**Base commit:** `8a9fed4f`
**Scope:** settle the R1 mechanism question — is the real-forward win the
restart-blend or the per-record random init? — and bound the blend's *marginal*
contribution so "≈ 0" is not confused with "not significant".
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

| Item | Value |
|---|---|
| Isolation | the win is the **per-record random init**; the blend adds no significant gain (B ≈ C, B ≫ A) |
| New (this doc) | an **equivalence bound** on the blend's marginal effect B − C |
| Per-record B − C | **+0.0187 hits/record**, 95% CI `[-0.009, +0.046]` → over 1000 records `[-9, +46]` |
| Upper bound | **≤ +46 hits (≤ 28 % of the baseline mean 164)** — a *moderate* blend gain cannot be excluded |
| Seed-level B − C | +18.7 hits, 95% CI `[-18.5, +55.9]` (n = 3 seeds — wide, uninformative) |
| Manuscript wording | live R1 row is **PARTIAL / single-seed-disclosed** and does **not** claim the blend mechanism → no overclaim to correct |
| Verdict | isolation **CONFIRMED**; the "≈ 0" reading is honest as a point estimate but must travel with the `≤ +46` bound |

---

## 1. The isolation (already measured)

The experiment exists in `docs/audit/r1-d004b-attribution.md` (D-004B-ATTRIBUTION).
Three arms, 3 seeds × N = 1000:

| arm | init | rounds |
|---|---|---|
| **A** baseline | canonical near-uniform | 1 pass |
| **B** init-only | per-record random simplex | 1 pass |
| **C** framework | canonical init + random-simplex restart | 3 restart-blend rounds |

Seed totals: A = 158/159/174, B = 298/274/290, C = 275/272/259.

* **B ≫ A** (pooled +123.7 hits, `p = 0.0043`) — the random init alone reproduces
  the win.
* **B ≈ C** (pooled +18.7 hits, `p = 0.16`, n.s.) — the 3-round restart-blend
  adds nothing measurable over a single random-init pass.

So the framework arm's win is **not** evidence for the restart-blend mechanism on
R1; it is evidence for per-record stochastic initialisation (the D-004b
surrogate, itself a tool convention).

---

## 2. New — the equivalence bound on B − C

"B ≈ C, n.s." is a *failure to reject*, not an equivalence. The honest question
is how large the blend's marginal effect could still be. Runner:
`tools/gap25_r1_blend_equivalence.py`; output
`verification_outputs/gap25-r1-blend-equivalence/equivalence.json`.

**Per-record pooled (n = 3000 records):**

| quantity | value |
|---|---|
| mean B − C | **+0.0187** hits/record |
| sd | 0.7772 |
| SE | 0.0142 |
| 95 % CI | **[−0.009, +0.046]** hits/record |
| over 1000 records | **[−9, +46]** hits |
| as % of the baseline mean (164) | **≤ +28 %** |

**Seed-level (n = 3):** mean +18.7 hits, 95 % CI `[−18.5, +55.9]` — the 3-seed
test is too wide to bound anything.

**Reading.** The point estimate is *slightly negative for the blend* (init-only
edges the framework on every seed), and it is not significant — but the design
**cannot exclude a blend gain up to ≈ +46 hits (≈ 28 % of the baseline)**. The
correct statement is therefore:

> The restart-blend's marginal contribution on R1 is **not established and not
> significant** (point estimate slightly negative), and is **bounded above by
> ≈ +46 hits at 95 % confidence** — a moderate blend gain is not excluded by
> this 3-seed design.

This *strengthens* the honesty of the attribution (which reported only "≈ 0")
without changing any recorded number.

---

## 3. Manuscript wording

The live manuscript R1 row (`docs/drafts/paper-A-final.md:558`) is
**PARTIAL / single-seed-disclosed**; it reports the framework-arm reading and
does **not** attribute it to the restart-blend mechanism. The ledger row
(`docs/audit/todo-history.md` §4) already carries the correct attribution
("the win is carried by the per-record random **INIT**, not the restart-blend").

So there is **no overclaim to correct**. An *optional* additive disclosure —
naming the init attribution and the `≤ +46` bound in the R1 row — is a
frozen-manuscript edit and is therefore **user-gated** (folded into
GAP-29-MANUSCRIPT-DENSITY, which already covers manuscript edits pending
authorization). It is **not** applied here.

---

## 4. Guardrail compliance

| Guardrail (AGENTS.md §3) | Status |
|---|---|
| #1 vendored upstream byte-identical | ✅ untouched |
| #2 additive is the rule | ✅ new analysis script + audit; no recorded number changed; no frozen surface edited |
| #3 NO-PUSH | ✅ commit only |
| #4 honest uncertainty | ✅ the `≤ +46` bound is the point — "≈ 0" is not overstated as equivalence |
| #5 TNNLS freeze | ✅ no `tnnls_submission/` number moved |
| #6 per-increment audit doc | ✅ this file |
| #7 stricter = cleaner | ✅ the analysis is a pure read of the committed attribution JSON |

---

## 5. Verification

| Gate | Result |
|---|---|
| `python tools/gap25_r1_blend_equivalence.py` | writes equivalence.json; per-record CI `[−0.009, +0.046]` |
| `ruff check tools/` | All checks passed |
| `python tools/check_docs_against_code.py` | OK 4143 claims |
| `mkdocs build --strict` | exit 0 |

---

## 6. Unresolved / noted

- **A tighter blend bound** would need more seeds (the seed-level CI is the
  bottleneck) or a direct blend-off arm (framework with `m` forced to 0), which
  is a runner change. Not required for the isolation verdict; recorded as the
  natural strengthening.
- **The init mechanism is the D-004b surrogate**, not the upstream intervention
  sampler (D-004b caveat, unchanged).
