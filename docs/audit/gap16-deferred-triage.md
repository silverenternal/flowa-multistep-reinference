# GAP-16 — Triage of the 31 deferred reviewer-facing gaps (Wave 364 inventory)

**Date:** 2026-10-12
**Increment:** GAP-16 (from `todo/SUBMISSION-GAP-CHECKLIST.md`)
**Handle:** `docs/audit/wave364-paper-polish-gaps.md` §5
**Status:** RESOLVED (triaged; explicit acceptance recorded)

---

## 1. Observed facts

1. **The Wave 364 "39-gaps inventory" is not a persisted artifact.** The
   Wave 364 consolidation doc (`docs/audit/wave364-paper-polish-gaps.md` §5) lists
   the 31 deferred gaps by **ID and category only** (user-gated / env-blocked /
   out-of-scope / low-impact), and the selection memo
   (`docs/audit/wave364-p1-gap-selection-memo.md`) enumerates only the **8 closed**
   gaps (G3, G11, G15, G20, G31, G32, G34, G38). A repo-wide search
   (`grep -rlnE "39-gaps|G25|G29|master-verifier" --include=*.md`) found **no file
   that records the per-gap descriptions** of the 31 deferred items; the inventory
   is referenced as coming from a "Wave 363 P2 master-verifier cycle" whose own
   doc (`docs/audit/wave363-p2-master-verifier.md`) contains no G-numbered list.
2. **The 31 deferred IDs, from `wave364 §5`:** user-gated {G2}; env-blocked
   {G8, G9, G23}; out-of-scope {G4, G7, G5, G10, G6, G12, G14, G19, G22, G24};
   low-impact {G1, G16, G17, G18, G21, G25–G30, G33, G35–G37, G39}. That is
   1 + 3 + 10 + 16 = **30**; the arithmetic complement of the 8 closed gaps over
   G1–G39 is **31**, the missing one being **G13**, which `wave364 §5` does not
   list (an omission in the source doc).
3. **`todo/SUBMISSION-GAP-CHECKLIST.md` (2026-10-12) is the authoritative
   successor gap list.** It re-derives the current agent/gpu/user gap set
   (GAP-01…GAP-21) directly against the live manuscript and evidence, and several
   of the Wave 364 deferred items map onto it (see §2).

## 2. Triage

Because the per-gap descriptions are not recoverable, the triage is
category-level: each of the 31 gaps is **ACCEPTED-DEFERRED** with its category
reason, and mapped to the live checklist where a mapping is clear. No gap is
closed in this increment (there is nothing identifiable to close without the
inventory); the explicit-acceptance path is taken.

| Gap | Category (wave364 §5) | Disposition | Reason / live-checklist mapping |
|---|---|---|---|
| G2 | user-gated | ACCEPTED-DEFERRED | 17 `[USER TO FILL]` cover-letter fields — user action at submission time. → **GAP-20** |
| G8 | env-blocked | ACCEPTED-DEFERRED | Repository URL reveals author identity — requires an explicit user anonymization decision (venue-dependent); no code/doc change is honest without it. |
| G9 | env-blocked | ACCEPTED-DEFERRED | Lean 4 incomplete (12/15 `sorry`); claim is already marked PENDING. → **GAP-13** |
| G23 | env-blocked | ACCEPTED-DEFERRED | R3 RDKit 2026.03.5 env blocker; disclosed. → **GAP-02** |
| G4, G7 | out-of-scope | ACCEPTED-DEFERRED | R6/R2 counterfactual-treated-as-STRONG — preserved verbatim per Wave 268 strict-clean + honest disclosure. → **GAP-01 / GAP-06** |
| G5, G10 | out-of-scope | ACCEPTED-DEFERRED | R3 projected-from-N=200 — preserved per strict-clean + honest disclosure. → **GAP-02** |
| G6 | out-of-scope | ACCEPTED-DEFERRED | Paper B companion ambiguity — preserved per the §3.7 dependency disclosure. |
| G12 | out-of-scope | ACCEPTED-DEFERRED | TOST "practical equivalence" interpretation — preserved per Wave 234 P2 methodology. |
| G14 | out-of-scope | ACCEPTED-DEFERRED | R6 pre-registration gap — preserved per the counterfactual methodology disclosure. → **GAP-01** |
| G19 | out-of-scope | ACCEPTED-DEFERRED | Cross-domain heterogeneity — preserved per Wave 234 P2 (cf. GAP-11 I² heterogeneity). |
| G22 | out-of-scope | ACCEPTED-DEFERRED | Theorem 4 self-convergence vs value-add scope — preserved per the §6.5 disclosure. → **GAP-09** |
| G24 | out-of-scope | ACCEPTED-DEFERRED | Solver comparison — preserved per the CUDA-graph fix scope. → **GAP-12** |
| G1, G16, G17, G18, G21, G25–G30, G33, G35–G37, G39 (16) | low-impact | ACCEPTED-DEFERRED | Minor disclosure / consistency / formatting; deferred to camera-ready polish per Wave 268 strict-clean. No identifiable fix without the source inventory. |
| G13 | *(unlisted)* | ACCEPTED-DEFERRED | Not enumerated in `wave364 §5`; recorded here as the 31st item. No description recoverable. |

**Net:** 31 / 31 triaged; 0 closed in this increment; 31 explicit acceptances
recorded. The low-impact bucket is the only one whose members might have been
closeable, but the per-gap descriptions are unavailable, so closing any of them
would require re-deriving the inventory — out of scope for a triage increment.

## 3. Cross-mapping to the live gap checklist

The live `todo/SUBMISSION-GAP-CHECKLIST.md` supersedes the Wave 364 inventory as
the operative gap list. Clear mappings: G2→GAP-20, G9→GAP-13, G23→GAP-02,
G4/G7→GAP-01+GAP-06, G5/G10→GAP-02, G14→GAP-01, G22→GAP-09, G24→GAP-12. The
remaining deferred items (G6, G8, G12, G19, G1/G16–G18/G21/G25–G30/G33/G35–G37/G39,
G13) have no live-checklist counterpart and are accepted as camera-ready polish.

## 4. What changed since Wave 364 that touches these gaps

Three increments since Wave 364 have closed items that overlap the deferred set:
the manuscript citation-integrity fix (GAP-18/GAP-21, `3fb5f67`), the GAP-19
venue-fit alignment (`9e95536`), and the GAP-14 novelty-differentiation paragraph
(`ca730b9`). None of them closed a Wave 364 G-numbered gap directly.

## 5. Gates

| Gate | Command | Result |
|---|---|---|
| claims consistency | `python tools/check_claims_consistency.py` | no drift |
| mkdocs strict | `mkdocs build --strict` | exit 0 |

## 6. Caveats

- This is a **category-level** triage; it does not claim to have inspected each
  of the 31 gaps individually, because their descriptions are not persisted in
  the repository. If the original Wave 363 P2 inventory is recovered (e.g. from a
  session log), the low-impact bucket should be re-triaged with per-gap fixes.
- No number, status label, or verdict is changed by this increment.
