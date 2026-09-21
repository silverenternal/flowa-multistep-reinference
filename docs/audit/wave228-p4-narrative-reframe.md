# Wave 228 P4 — Path B Narrative Reframe Audit

**Date:** 2026-09-21
**Phase:** Wave 228 P4 (Path B: reframe, not refactor)
**Inputs:** Wave 228 P3 Path A vs Path B decision
(`docs/audit/wave228-p3-path-a-vs-path-b-decision.md`)

---

## 1. Goal

Apply Path B: reframe section-2-method.md + abstract-final.md +
cover-letter-tpami.md + methods-why-per-record.md to honest
narrative. Path B was selected over Path A (refactor) because
**no source code changes are required** — the closed-form
coefficients stay canonical-witness-derived, and the narrative
now honestly delineates that the framework's per-record adaptation
comes from the **scheduler architecture** (the listed five
scheduler components + BRAI) rather than from per-adapter
paper-quantity overrides that are not implemented.

---

## 2. Edits applied

### 2.1 `docs/drafts/section-2-method.md` — 2 over-claim locations reframe

**Location 1 — §2.5.1 Per-Adapter F-Side Profile Table disclosure
(lines ~341–359 in pre-edit file).** The original text asserted
that "the F-side constants are computed from the adapter's
posterior geometry at runtime (via `sheet_evidence_A`,
`root_cell_packing_B`, `per_cell_coefficient_C`,
`exterior_gap_e_rho` on the adapter's residual profile $g$ derived
from the velocity field)". This over-claim was replaced with:

> "The four paper quantities $(A_g, B_g, C_g, e_\rho)$ are derived
> from the canonical F-side witness (Proposition 2 family $g(x) =
> (1 + 0.25\cdot\tanh(x))\cdot\sin(x)$; see
> `adaptive_reflow/theory/paper_quantities.py`), which is **shared
> across adapters** under the framework default F-side profile.
> The framework value-add is the **scheduler architecture**
> (`CosineAnnealScheduler` + `CodimensionSheetScheduler` +
> `BoundedMergeOperator` + `EvidenceDrivenScheduler` + BRAI),
> which adapts per-record to local velocity-field geometry rather
> than depending on per-adapter paper-quantity values."

An explicit caveat was added:

> "**Explicit caveat (per-adapter $g(s)$).** Per-adapter $g(s)$
> from each adapter's posterior geometry is **not currently
> implemented**; the framework exposes the
> `AdapterCapabilities.profile_residual_fn` hook (see
> `adaptive_reflow/universal/adapter.py`) for future per-adapter
> $g(s)$ extension, but no adapter declares that hook and the
> runner/scheduler fall back to legacy closed forms that do not
> compute a per-adapter $g(s)$. The canonical witness $g(x) =
> (1 + 0.25\cdot\tanh(x))\cdot\sin(x)$ is therefore **shared
> across all 12 adapters** at the framework default F-side
> profile."

**Location 2 — §2.7 Theoretical-Justification Paragraph (line
~441 in pre-edit file).** The original text asserted that
"$(A_g, B_g, C_g, e_\rho)$ are **computable from the adapter's
posterior geometry at runtime**". This over-claim was replaced
with:

> "The four paper quantities $(A_g, B_g, C_g, e_\rho)$ are
> **derived from the canonical F-side witness** $g(x) = (1 + 0.25
> \cdot\tanh(x))\cdot\sin(x)$ (Proposition 2 family) with default
> $(d, c, \rho, \eta) = (1.0, 1.0, 0.1, 0.1)$, through the
> closed-form evaluators in
> `adaptive_reflow/theory/paper_quantities.py` (re-exported from
> the `contracts/paper_quantities.py` shim for backward
> compatibility). The framework precomputes these values once
> for the canonical witness and **caches** them on the
> `PhysicalComplement` typed carrier, so the per-round scheduler
> calls are $O(1)$ table lookups rather than re-integration of the
> integrals (D1)–(D4). Per-adapter $g(s)$ from each adapter's
> posterior geometry is **not currently implemented** (see §2.5.1
> caveat and `AdapterCapabilities.profile_residual_fn` in
> `adaptive_reflow/universal/adapter.py`)."

The "outside caller" paragraph was reframed to describe the
scheduler-architecture value-add instead of "runtime packaging".

### 2.2 `docs/drafts/abstract-final.md` — Sentence 2 + Sentence 3 reframe

**Sentence 2** was updated to drop the "checkpoint's own posterior
geometry" claim (which over-promised per-checkpoint adaptation)
and replaced with "local velocity-field geometry":

> "Deployed flow matching checkpoints ship as frozen weights,
> leaving practitioners without a mechanism to schedule the
> inference loop as a function of local velocity-field geometry."

**Sentence 3** was expanded to introduce the canonical F-side
witness and the framework value-add architecture (five
scheduler/operator components + BRAI):

> "...derived from a canonical F-side witness $g(x) = (1 + 0.25
> \cdot\tanh(x))\cdot\sin(x)$ (Proposition 2 family), which is
> shared across adapters under the framework default F-side
> profile. The framework value-add is the scheduler architecture
> (CosineAnnealScheduler + CodimensionSheetScheduler +
> BoundedMergeOperator + EvidenceDrivenScheduler + BRAI), which
> adapts per-record to local velocity-field geometry rather than
> depending on per-adapter paper-quantity values, and consumes
> those quantities directly as scheduler inputs."

Word-count impact: Sentence 2 went from 31 words → 32 words;
Sentence 3 went from 86 words → 121 words; total abstract body
went from 225 words → 261 words. **This pushes the abstract above
the TPAMI 250-word envelope** — flagged as a follow-up for the
author to either trim the §MS.10.5.1 cross-reference (currently
embedded) or accept the override (TPAMI allows up to 300 words
when the journal considers the methodology mathematically heavy).

### 2.3 `docs/drafts/methods-why-per-record.md` — §MS.10.5.2 added

A new sub-section §MS.10.5.2 ("Framework value-add — scheduler
architecture, not per-adapter paper quantities") was added
immediately after the existing §MS.10.5.1. The new sub-section:

1. Lists each of the five scheduler components and what quantity
   each consumes (`CosineAnnealScheduler` → $A_g$ smoothing-ramp,
   `CodimensionSheetScheduler` → $(A_g, B_g, C_g)$ → `n_cap`,
   `BoundedMergeOperator` → $e_\rho$ → merge envelope noise floor,
   `EvidenceDrivenScheduler` → full quadruple → per-cell restart
   probability, BRAI → per-record aggregation).
2. Articulates the architectural separation: paper quantities are
   canonical closed-form coefficients (computed once for the
   shared canonical witness); scheduler architecture is the
   per-record adaptation layer.
3. Adds an explicit caveat that per-adapter $g(s)$ is not currently
   implemented (`AdapterCapabilities.profile_residual_fn` is the
   future-extension hook).
4. Closes the loop on Wave 228 P3 Path A vs Path B decision:
   **reframe not refactor** — closed-form coefficients stay
   canonical-witness-derived (no source-code change).

### 2.4 `docs/cover-letter-tpami.md` — 2 over-claim locations reframe

**Location 1 — §2 Suitability, "Mathematical foundations of flow
matching" paragraph (lines ~51–63 in pre-edit file).** The original
text asserted the bound was "parameterised by four paper
quantities computable from the checkpoint's posterior geometry".
This over-claim was replaced with the canonical-witness framing:

> "parameterised by four paper quantities derived from a canonical
> F-side witness $g(x) = (1 + 0.25\cdot\tanh(x))\cdot\sin(x)$
> (Proposition 2 family) under the framework default F-side profile
> $(d, c, \rho, \eta) = (1.0, 1.0, 0.1, 0.1)$ — shared across all
> 12 adapters."

**Location 2 — §3 Insight, "Paper-Quantity-Driven Scheduling"
paragraph (lines ~93–111 in pre-edit file).** The original text
asserted that the four quantities "are **computable from the
adapter's posterior geometry at runtime**". This over-claim was
replaced with the canonical-witness + scheduler-architecture
framing:

> "These four quantities are **derived from the canonical F-side
> witness** $g(x) = (1 + 0.25\cdot\tanh(x))\cdot\sin(x)$
> (Proposition 2 family) under the framework default F-side
> profile $(d, c, \rho, \eta) = (1.0, 1.0, 0.1, 0.1)$, through
> typed evaluators in `adaptive_reflow/theory/paper_quantities.py`,
> and are **shared across all 12 adapters** at that canonical
> witness. The framework's value-add is the **scheduler
> architecture** — `CosineAnnealScheduler` (consumes $A_g$ →
> smoothing-ramp aggressiveness), `CodimensionSheetScheduler`
> (consumes $A_g, B_g, C_g$ → `n_cap`), `BoundedMergeOperator`
> (consumes $e_\rho$ → merge envelope noise floor),
> `EvidenceDrivenScheduler` (consumes the full quadruple →
> per-cell restart probability), and BRAI (Bayesian Re-inference
> Aggregator) — which adapts per-record to local velocity-field
> geometry rather than depending on per-adapter paper-quantity
> overrides. Per-adapter $g(s)$ from each adapter's posterior
> geometry is **not currently implemented** (the framework
> exposes `AdapterCapabilities.profile_residual_fn` in
> `adaptive_reflow/universal/adapter.py` as the future-extension
> point, but no adapter declares that hook today)."

The "four-port control surface" claim was upgraded to "five-port
control surface (four scheduler/operator ports plus BRAI)" to
honestly delineate BRAI as the fifth component.

---

## 3. Verification — `tools/check_claims_consistency.py`

```
$ python tools/check_claims_consistency.py --quiet
claims: active=60 provisional=1 deprecated=2 drift=0
```

**Result: PASS (drift = 0).** The claims ledger remains consistent
with the cross-references after the narrative reframe. No claim
was newly disputed; no `Asserted by` reference is broken; no
`Disputed by` reference is created.

---

## 4. Honesty checklist

| Over-claim | Location | Status after Wave 228 P4 |
|---|---|---|
| "F-side constants are computed from the adapter's posterior geometry at runtime" | §2.5.1 disclosure | **Reframed** — canonical-witness derivation, shared across adapters |
| "$(A_g, B_g, C_g, e_\rho)$ are computable from the adapter's posterior geometry at runtime" | §2.7 theoretical-justification paragraph | **Reframed** — derived from canonical F-side witness, with caveat about `profile_residual_fn` hook |
| "schedules inference loop as a function of checkpoint's own posterior geometry" (abstract sentence 2) | abstract-final.md sentence 2 | **Reframed** — "local velocity-field geometry" |
| "computable from the adapter's posterior geometry at runtime" (cover letter §3) | cover-letter-tpami.md §3 | **Reframed** — canonical-witness derivation, scheduler architecture emphasized |
| "computable from the checkpoint's posterior geometry" (cover letter §2) | cover-letter-tpami.md §2 | **Reframed** — canonical-witness framing |
| "four-port control surface" | cover-letter-tpami.md §3 | **Updated** — "five-port control surface (four scheduler/operator ports plus BRAI)" |
| "scheduler adapts to per-adapter paper-quantity values" | implied throughout | **Reframed** — scheduler architecture is the per-record adaptation layer, not per-adapter paper-quantity overrides |

---

## 5. What this audit does NOT change

- **No source code is changed.** This is a narrative reframe
  (Path B), not a refactor (Path A). The closed-form coefficients
  stay canonical-witness-derived at the framework default F-side
  profile; no `paper_quantities.py` / `rate_bound.py` /
  `validation.py` code is touched.
- **No claims ledger entry is added, removed, or status-changed.**
  `tools/check_claims_consistency.py` reports `drift=0` — the
  ledger remains consistent.
- **No empirical numbers change.** The R-level headline observables
  (R6 scPerplexity $d_z = -1.077$, R6 hard pLDDT $d_z = +1.189$),
  the 4-arm per-seed Table B values, and the 2.5–10× NFE compression
  figures are unchanged. The reframed narrative is
  *self-consistent with the published numbers* — adapter-specificity
  lives in the per-record BL-distance witness (R6 R-level headline
  observable), not in per-adapter $A_g$ values.
- **No TPAMI submission package metadata changes.** Cover-letter
  date, author placeholders, suggested-AE placeholders, Zenodo DOI
  placeholders, freeze-marker commit SHA `5b21cca` all unchanged.

---

## 6. Follow-up items (NOT in scope for Wave 228 P4)

1. **Abstract word-count breach.** The reframe expanded the abstract
   from 225 → 261 words (TPAMI envelope = 250; TPAMI allows up to
   300 for methodology-heavy submissions). If the corresponding
   author prefers to stay under 250, a trim pass on sentence 3
   (e.g. dropping the "which is shared across adapters under the
   framework default F-side profile" parenthetical) would restore
   the original 225-word envelope.
2. **Per-adapter $g(s)$ implementation.** The framework exposes
   `AdapterCapabilities.profile_residual_fn` as the future-extension
   hook. Implementing per-adapter $g(s)$ for any of the 12
   adapters would shift $A_g$ (and other coefficients) to be
   per-adapter empirical, and would require a follow-up audit
   (Wave 229+ or later) to re-evaluate the canonical-witness
   narrative if any adapter declares the hook.
3. **CLM-039 / CLM-040 narrative cross-check.** The 2D RF SOTA and
   CIFAR-10 SOTA entries in `docs/CLAIMS.md` reference
   "schedule-independent `selection_ratio`" (CLM-003, CLM-004)
   and "framework is not perturbing the adapter's posterior
   geometry, only the per-round endpoint distribution" (CLM-039).
   These are consistent with the Wave 228 P4 reframe: the framework
   adapts the **endpoint distribution** (per-record) via scheduler
   architecture, not the adapter's posterior geometry. No
   inconsistency introduced.

---

## 7. Files modified

- `/home/hugo/codes/flowa-multistep-reinference/docs/drafts/section-2-method.md`
- `/home/hugo/codes/flowa-multistep-reinference/docs/drafts/abstract-final.md`
- `/home/hugo/codes/flowa-multistep-reinference/docs/drafts/methods-why-per-record.md`
- `/home/hugo/codes/flowa-multistep-reinference/docs/cover-letter-tpami.md`

## 8. Files created

- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave228-p4-narrative-reframe.md`
  (this file)
