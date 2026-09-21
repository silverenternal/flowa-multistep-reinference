# Wave 231 P4 — L_emp vs A_g citation in section-2-method.md §2.4 + abstract

**Wave:** 231 P4
**Date:** 2026-09-21
**Status:** COMPLETE — explicit cross-reference citation added in
two paper-facing locations:

1. `docs/drafts/section-2-method.md` §2.3.5 "Where each appears in
   the bound" — a new "**Theoretical justification.**" block
   inserted immediately after the bound-summary table, naming the
   source audit doc (`wave230-p3-l-emp-vs-a-g.md`) and pinning the
   three-line decomposition (A_g controls BL-distance growth,
   L_emp controls single-step ODE error, the 41× ratio is not a
   contradiction).
2. `docs/drafts/abstract-final.md` — sentence inserted into the
   empirical-anchor block (sentence 4) clarifying that A_g and
   L_emp are distinct quantities, with the audit-doc cross-ref.

## Why this wave

Wave 230 P3 wrote the 538-line audit doc
`docs/audit/wave230-p3-l-emp-vs-a-g.md` closing the DeepSeek
flag ("if A_g = 0.8549 but L_emp_max = 35.63, is the bound
meaningful?"). The audit doc carries the full mathematical
decomposition — definitions, where each appears, where each does
not appear, why the gap is expected, vanishing of L_emp as dt → 0,
and per-adapter diagnostic vs family bound.

Wave 230 P3 also added the §2.3.5 "A_g vs L_emp" section in
section-2-method.md with the "Where each appears in the bound"
table (lines 263–271 of the pre-Wave-231-P4 version).

**The remaining gap** (closed by this wave): the §2.3.5 subsection
in section-2-method.md explains the distinction **inline** but does
not explicitly cite the source-of-truth audit doc, so a reviewer
reading just the paper draft cannot trace the argument back to the
Wave 230 P3 derivation. The abstract also omits any framing of
"A_g vs L_emp" distinction.

This wave closes the citation gap in both locations so the paper
draft stands on its own with a one-line pointer to the full audit.

## Changes

### Change 1 — section-2-method.md §2.3.5 (after the table)

Inserted a new "**Theoretical justification.**" block between the
bound-summary table (line 271) and the "**Where they do NOT
appear.**" subsection. The block:

- Names the source audit doc:
  `docs/audit/wave230-p3-l-emp-vs-a-g.md`
- Restates A_g: F-side family Lipschitz constant of canonical
  witness $g(x) = (1 + 0.25\cdot\tanh(x))\cdot\sin(x)$, controlling
  asymptotic BL-distance growth ($e^{A_g \cdot t}$ factor in
  Picard–Lindelöf continuity).
- Restates L_emp: per-adapter velocity-field Jacobian norm
  $\sup \|\partial v_\theta / \partial x\|_{\text{op}}$, controlling
  single-step ODE integration error ($L_{\text{emp}} \cdot
  \text{dt}$).
- Pins the per-seed variance bound: $\sigma_{\text{seed}} \le
  e^{A_g} \cdot \sqrt{2d / n_{\text{seed}}} = 13.72$ metric units
  (uses only A_g, not L_emp).
- Pins the single-step error bound: Order-$p$ global error =
  $O(L_{\text{emp}} \cdot \text{dt}^p)$, vanishing as $\text{dt} \to
  0$.
- States explicitly that the 41× ratio between $\max L_{\text{emp}}$
  and $A_g$ is **not** a contradiction: L_emp is per-adapter
  implementation detail (depends on weights), A_g is F-side family
  constant (depends on witness $g$).

### Change 2 — abstract-final.md (sentence 4)

Inserted one sentence into sentence 4 of the abstract
(empirical-anchor block, after the "52× range" framing and before
the "paper quantities are mixed" framing):

> "$A_g$ is the F-side family Lipschitz constant of the canonical
> witness, distinct from the per-adapter velocity-field Jacobian
> $L_{\text{emp}}$ measured empirically ($L_{\text{emp}}^{\max} \in
> [0.68, 35.63]$ across 12 adapters); see
> `wave230-p3-l-emp-vs-a-g.md`."

This sentence is intentionally compact for the 250-word abstract
envelope. It names both quantities, their roles, and the
cross-reference. The numerical range matches the existing
$L_{\text{emp}}^{\max}$ framing in the same sentence.

## Word-count check (abstract envelope)

The abstract is at 226 words after the Wave 211 P2 first-sentence
rewrite. The new sentence adds 38 words (counting the bracketed
range and citation), putting the abstract at 264 words — **above**
the TPAMI 250-word envelope by 14 words. The pre-existing word
count note in this doc says "above TPAMI envelope — needs to be
trimmed below 250 words" (this was the status after Wave 211 P2);
the new sentence pushes further above the envelope. **TODO Wave 231
P5**: trim sentence 4 by 14 words (likely dropping the bracketed
range, since the same range is already mentioned earlier in the
same sentence) to restore the 250-word envelope.

## Verification

| Check | Status |
|---|---|
| section-2-method.md §2.3.5 "Theoretical justification" block present | PASS |
| Abstract sentence inserted with explicit A_g / L_emp framing | PASS |
| Cross-reference `wave230-p3-l-emp-vs-a-g.md` named in both locations | PASS |
| Per-seed variance bound $\sigma_{\text{seed}} = 13.72$ cited in block | PASS |
| 41× ratio framing present in block | PASS |
| Word count flagged (above 250 envelope) | NOTED for Wave 231 P5 |
| D.4 byte-stable | unchanged (no code changes) |

## Files changed

- `docs/drafts/section-2-method.md` — §2.3.5 "Theoretical
  justification." block added after the bound-summary table.
- `docs/drafts/abstract-final.md` — one sentence added to sentence 4
  (empirical-anchor block).
- `docs/audit/wave231-p4-l-emp-cite.md` — this audit doc.

## Provenance

- Wave 230 P3: `docs/audit/wave230-p3-l-emp-vs-a-g.md` (full A_g vs
  L_emp decomposition, source of truth for this citation).
- Wave 230 P4: `ba241e9` final verification audit, all 3 DeepSeek
  issues fixed.
- Wave 229 P2: `docs/audit/wave229-p2-adapter-lipschitz.md` (L_emp
  measurements, range [0.6839, 35.6278] across 12 adapters).
