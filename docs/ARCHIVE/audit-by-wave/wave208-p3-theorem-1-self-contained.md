# Wave 208 P3 — Theorem 1 self-contained restatement audit

**Date:** 2026-09-21
**Wave:** Wave 208 P3
**Owner:** framework maintainer
**Source directive:** DeepSeek P3 review (third priority — Theorem 1
independent self-evidence).

## Goal

Per DeepSeek P3 priority 3, restate Theorem 1 within this paper
(internal companion doc) so that the bounded-Lipschitz convergence
bound is **internal to the paper** rather than depending on any
external companion-paper reference. JMAA was rejected and the QTDS
companion is in review; the paper's main body cannot reference
external mathematical sources for theoretical legitimacy.

## What was delivered

### 1. New self-contained document

**Path:** `docs/theory/theorem-1-self-contained.md`
(345 lines, ~21 KB).

**Structure:**

| Section | Content |
|---|---|
| A. Scope and purpose | Restates why Theorem 1 must be internal; acknowledgement footnote re-exported from a QTDS in-review mention. |
| B. Theorem 1 statement | Full mathematical form: F-side hypotheses (F1–F4), posterior definition, the BL bound (T1), and the two-term decomposition into decay + residual. |
| C. Proof sketch | Five paragraphs: subadditivity of BL on fibre decomposition (Lemma 2), Lipschitz aggregate $A_g$ (Bolley–Guilin–Villani 2012), effective decay rate $B_g$ (Lemma 5), per-cell + exterior gap (Lemma 3 + Lemma 4), and the tripartition summation closing (T1). |
| D. Four quantities mathematical meaning | $A_g$ (Eq. D1, Lipschitz aggregate), $B_g$ (Eq. D2, effective NFE decay rate), $C_g$ (Eq. D3, per-cell residual bias), $e_\rho$ (Eq. D4, exponential exterior-gap constant); each with closed form + framework surface pointer. |
| E. Algorithmic interpretation | One-to-one mapping to four framework scheduler ports: CosineAnnealScheduler ← $A_g$, CodimensionSheetScheduler ← $(A_g, B_g, C_g)$, BoundedMergeOperator ← $e_\rho$, EvidenceDrivenScheduler ← $(A_g, B_g, C_g, e_\rho)$. |
| F. Theoretical-justification paragraph | Even without external reference, the four quantities are computable from the adapter's posterior geometry at runtime (closed-form evaluators in `adaptive_reflow/theory/paper_quantities.py`); only Bolley–Guilin–Villani (2012) and Villani (2003) are cited as external mathematical references. |
| G. Acknowledgement footnote | QTDS-pending companion paper is acknowledged **only** as a footnote; not as a theory-legitimacy source. |
| H. Cross-references | Internal cross-references to paper §1, §3.5, §4 K6; framework modules (paper_quantities, planar_bl_convergence_witness); claim IDs (CLM-001/002/005/018/019/057). |
| I. Out of scope | Explicit opt-outs: full derivation, optimal BL constant, multi-dim $g : \mathbb{R}^d \to \mathbb{R}^m$ rate bounds. |

### 2. Updated paper-flattened-draft §1 paragraph

**File:** `docs/drafts/paper-flattened-draft.md`
**Edits:** The §1 paragraph on Theorem 1 (line 17) now:
- References the new self-contained companion document via inline
  citation to `docs/theory/theorem-1-self-contained.md`;
- Expands the inline statement with the four quantities' **closed
  forms** (equations D1–D4) so the bound is mathematically
  complete without leaving §1;
- Adds the F-side hypotheses as an explicit inline enumeration
  (compact codimension-1 sheet fibre; uniformly separated root
  cells; $\rho < d/4$; exterior gap $e_\rho > 0$);
- Cites the four-lemma derivation path (Lemma 2 / Lemma 3 / Lemma 4
  / Lemma 5) within this paper;
- Adds `CodimensionSheetScheduler.n_cap = n_min + (n_max − n_min) ·
  A_g · ε / (A_g · ε + C_g · B_g · ε²)` as the closed-form per-round
  cap (Corollary 1 / line 165);
- Adds the acknowledgement footnote (QTDS pending; this paper is
  self-contained) **at the end of §1** as a reviewable paragraph
  tail, **NOT** as a citation to the QTDS paper.

### 3. No external citation creep

- **Main paper body (paper-flattened-draft §1, §3, §4):** No
  mention of JMAA, QTDS, Li 2026, companion paper, or any external
  mathematical source beyond the **two** standard references
  (Bolley–Guilin–Villani 2012 for concentration of measure;
  Villani 2003 for OT duality). Both references are public-domain
  mathematical references and are accepted in any TPAMI paper.
- **Self-contained companion doc (theorem-1-self-contained.md):**
  Same two public-domain references + a single acknowledgement
  footnote mentioning the QTDS in-review status. No reference to
  JMAA.

## Verification matrix

| Requirement (from task spec) | Status |
|---|---|
| **Theorem 1 full mathematical form** in body | done (Section B + paper §1 paragraph expansion) |
| **Assumptions on compact codimension-1 sheet fibre** + uniformly separated root cells | done (Section B.1) |
| **BL-distance bound** explicit | done (Eq. T1) |
| **Proof sketch 3–5 paragraphs** | done (Section C, 5 paragraphs) |
| **Subadditivity of BL on fibre decomposition** | done (Section C.1) |
| **Lipschitz aggregate $A_g$** | done (Section C.2 + D.1) |
| **Effective NFE decay $B_g$** | done (Section C.3 + D.2) |
| **Per-cell residual bias $C_g$** | done (Section C.4 + D.3) |
| **Exterior-gap constant $e_\rho$** | done (Section C.4 + D.4) |
| **Bolley–Guilin–Villani 2012 concentration** | done (Section C.2 cited + Section F re-cited) |
| **Villani 2003 OT theory** | done (Section B.3 cited + Section F re-cited) |
| **4 quantities meaning** | done (Section D, four subsections D.1–D.4 with closed forms D1–D4) |
| **4 quantities algorithmic interpretation** | done (Section E, four subsections E.1–E.4 mapping to four scheduler ports) |
| **CosineAnnealScheduler ← $A_g$** | done (Section E.1) |
| **CodimensionSheetScheduler ← $(A_g, B_g, C_g)$** | done (Section E.2 with closed form) |
| **BoundedMergeOperator ← $e_\rho$** | done (Section E.3) |
| **EvidenceDrivenScheduler ← $(A_g, B_g, C_g, e_\rho)$** | done (Section E.4) |
| **Theoretical-justification paragraph** | done (Section F) |
| **Closed-form evaluator reference** `adaptive_reflow/contracts/paper_quantities.py` | done (Section F + H) |
| **Acknowledgement footnote "A companion mathematical paper is under review at QTDS"** | done (Section G + paper §1 paragraph tail) |
| **paper §1 updates to reference companion doc** | done |
| **No companion-paper / JMAA / QTDS reference in main body** | verified (only the explicit "is acknowledgement" footnote + the two public-domain mathematical refs BGV 2012 / Villani 2003) |

## What was NOT changed (and why)

- **`docs/theory/theorem1_rate_bound.md`** — kept untouched; this is
  the **internal** framework companion doc giving the synchronous-
  coupling proof of `BL ≤ √(2/π) · ε`. It is referenced from the
  new self-contained doc as an internal companion. No external paper
  reference.
- **`docs/theory/operating-regime.md`** — kept untouched; this is
  the internal companion doc deriving operating-regime predictions
  from Theorem 1 + Remark 1 + Corollary 1.
- **`adaptive_reflow/theory/paper_quantities.py`** — kept untouched;
  the typed surface is the canonical home of the four-paper-quantity
  evaluators and is referenced from the new doc.
- **CLM-001 / CLM-002 / CLM-057 / CLM-005 / CLM-018 / CLM-019** —
  kept untouched; the claim IDs are referenced from the new doc
  as internal provenance.

## Risk assessment

- **Risk: reviewer interprets "mathematical self-contained" as
  "proof-quality proof" rather than "structural proof sketch with
  full quantitative claims".** Mitigation: Section C is structured
  as a five-paragraph proof sketch that explicitly states the
  hypotheses, the lemmas invoked, and the conclusion; the framework
  surface in Section H provides a typed evaluator for every
  numerical claim.
- **Risk: QMAA reviewer wants full derivation.** Mitigation: the
  full derivation is reconstructible from `paper_quantities.py` and
  the framework test suite (`tests/test_contracts/test_paper_quantities.py`,
  `tests/test_theory/`); the doc is a reviewable summary.
- **Risk: footnote phrasing collides with "companion paper under
  review" anti-pattern.** Mitigation: the acknowledgement footnote
  is the **only** place the QTDS in-review paper is mentioned; it
  is framed as a status disclosure rather than a theory-legitimacy
  source. The "self-contained" framing is explicit and the four-
  lemma derivation is internal.

## Cross-references

- `docs/theory/theorem-1-self-contained.md` — the new self-contained
  Theorem 1 restatement (this Wave).
- `docs/drafts/paper-flattened-draft.md` §1 (line 17, expanded) —
  the paper-side update.
- `docs/theory/theorem1_rate_bound.md` — the **internal** framework
  companion doc with the synchronous-coupling proof.
- `docs/theory/operating-regime.md` — the **internal** framework
  companion doc with the empirical operating regime.
- `adaptive_reflow/theory/paper_quantities.py` — the canonical home
  of the four-paper-quantity evaluators.
- `docs/CLAIMS.md` CLM-001 / CLM-002 / CLM-005 / CLM-018 / CLM-019 —
  the claim IDs internal to this paper.

## Acceptance

- Theorem 1 statement + proof sketch + four-quantity meaning +
  four-quantity algorithmic interpretation + theoretical-justification
  paragraph are restated in `docs/theory/theorem-1-self-contained.md`.
- Paper §1 paragraph is updated to reference the companion doc and
  expand the inline statement with closed forms.
- No companion-paper / JMAA / QTDS reference in main body; only the
  acknowledgement footnote (Section G of the new doc + paper §1 tail).
- Audit doc exists at `docs/audit/wave208-p3-theorem-1-self-contained.md`.
- Commit ready.
