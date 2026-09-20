# Wave 213 P7 — Abstract consistency across §1 Intro and §2 Method

**Scope.** Verify that the abstract's first sentence —

> "Standard ODE solvers for flow matching treat the entire trajectory with
> uniform boundary conditions, ignoring the local geometric structure of
> the velocity field." (`docs/drafts/abstract-final.md`)

— is echoed in (a) Intro §1 first paragraph
(`docs/drafts/paper-flattened-draft.md` line 13) and (b) Method §2 first
paragraph (`docs/drafts/section-2-method.md` lines 1–20 + the §2 stub in
`docs/drafts/paper-flattened-draft.md` lines 33–50), and that the three
load-bearing alignment axes are consistent across all three places:

1. **Problem statement** (uniform boundary conditions problem).
2. **Insight** (paper-quantity-driven scheduling solves it).
3. **Validation scope** (six R-level cells at paired N = 1000).

**Provenance.** Abstract was finalised in Wave 211 P2
(commit `a818ed6`, DeepSeek F3 framing). Intro §1 first paragraph and
Method §2 stub were last touched in Wave 213 P3 (commit `7c78fb7`).
Method §2 full body (`section-2-method.md`) was last touched in Wave 211
P3 (commit `9774fd3`).

---

## 1. Three alignment axes — extracted from the abstract

| Axis | Abstract source (`abstract-final.md` line 12) |
|---|---|
| **Problem (P)** | "Standard ODE solvers for flow matching treat the entire trajectory with uniform boundary conditions, ignoring the local geometric structure of the velocity field." (S1, 19 words) |
| **Insight (I)** | "We introduce FlowA, a training-free, solver-agnostic re-inference framework that derives a closed-form upper bound … through four paper quantities $(A_g, B_g, C_g, e_\rho)$ … and consumes those quantities directly as scheduler inputs via the CodimensionSheetScheduler, EvidenceDrivenScheduler, and BoundedMergeOperator algorithms." (S3, 86 words) |
| **Scope (V)** | "We validate the framework across six R-level cells spanning protein (LineageFlow, Kanzi), molecular 3D (FlowMol3), and image (CIFAR-10 Rectified Flow, MNIST Flow Matching, 2D Rectified Flow) flow matching models at paired sample sizes of N = 1000, observing 2.5–10× cross-budget NFE compression at matched quality alongside byte-stable composite-axis lifts on all three Tier 3 real checkpoints …" (S4, 64 words) |

---

## 2. Intro §1 first paragraph — alignment check

Source: `docs/drafts/paper-flattened-draft.md` line 13 (one long
sentence that spans the whole paragraph).

**Extracted fragments (in order):**

1. *Setup.* "Flow matching [Lipman et al. 2023] and Rectified Flow [Liu
   et al. 2022] define generation as the integration of a learned
   velocity field $v_\theta(x,t)$ along a single ordinary differential
   equation …" — establishes the standard formulation that the
   abstract's S1 rejects.
2. *Frozen-checkpoint consequence.* "… the released checkpoints of
   2024–2026 — LineageFlow (ICML 2026), Kanzi (ICLR 2026), FlowMol3
   (NeurIPS 2024), the open DDPM++/RF UNet weights, and the MNIST flow
   matching recipe — ship as frozen parameters $\theta$." — echoes
   abstract S2 (frozen-checkpoint gap).
3. *Gap statement.* "A frozen flow matching checkpoint carries a
   latent distribution gap: its natural prior differs from the
   test-time target distribution …; one-shot sampling cannot close
   this gap because each sample is drawn independently from the
   learned marginal with no mechanism to consume outcome-conditioned
   feedback from prior samples." — rephrases the abstract's "ignoring
   the local geometric structure" gap as "latent distribution gap" +
   "no mechanism to consume outcome-conditioned feedback".
4. *Scheduling witness.* "… no published framework schedules the
   noise-and-step budget across inference rounds as a function of a
   convergence-theory witness." — previews the paper-quantity-driven
   insight.

**Alignment verdict:**

| Axis | Aligned? | Reason |
|---|---|---|
| **Problem (P)** | **Partially aligned — rephrased.** | The intro names "latent distribution gap … one-shot sampling cannot close … no outcome-conditioned feedback", which is the *consequence* of the abstract's "uniform boundary conditions" assumption, not the assumption itself. The literal phrase "uniform boundary conditions" / "local geometric structure" does **not** appear. Conceptually consistent (no contradiction), but the literal echo of abstract S1 is missing. |
| **Insight (I)** | **Partially aligned — prefigured.** | "no published framework schedules … as a function of a convergence-theory witness" is the negative form of "consumes [paper quantities] directly as scheduler inputs". The literal four quantities / three scheduler components do **not** appear in the first paragraph (they appear in the third paragraph of §1 — line 17). |
| **Scope (V)** | **Not in first paragraph.** | Scope appears in §1 third paragraph (line 19), not in the first paragraph. The task explicitly limits this check to "Intro §1 first paragraph + Method §2 first paragraph", so the absence is a structural choice, not a divergence. No contradiction. |

**Conclusion.** No **divergence** (contradiction) exists. The intro's
first paragraph is a rephrased echo of abstract S1 + S2, consistent with
the abstract's framing. The literal phrase "uniform boundary conditions
… ignoring the local geometric structure" is absent; **a minimal clause
echoing this exact framing is added** below in §4.

---

## 3. Method §2 first paragraph — alignment check

Two files contain §2 first paragraphs:

- **A.** `docs/drafts/section-2-method.md` lines 1–20 — the **full**
  §2 Scope paragraph that introduces the Theorem 1 restatement, the
  F-side hypotheses, the four paper quantities, the three-step proof,
  the four-quantity algorithmic interpretation, and the
  theoretical-justification paragraph.
- **B.** `docs/drafts/paper-flattened-draft.md` lines 34–50 — the §2
  **stub** in the flattened paper that abbreviates (A) and explicitly
  defers the full restatement to `docs/drafts/section-2-method.md`.

**Extracted fragments (both files, in order):**

- (A) "**Scope.** This section restates Theorem 1 (the bounded-Lipschitz
  convergence bound that the framework's four paper quantities $(A_g,
  B_g, C_g, e_\rho)$ imply) in a self-contained form so that the bound
  is **internal to this paper** and does not depend on any companion
  paper, external manuscript, or out-of-paper reference. …"
- (B) "This section restates Theorem 1 (the bounded-Lipschitz
  convergence bound that the framework's four paper quantities $(A_g,
  B_g, C_g, e_\rho)$ imply) in a self-contained form so that the bound
  is **internal to this paper** and does not depend on any companion
  paper, external manuscript, or out-of-paper reference. …"

**Alignment verdict:**

| Axis | Aligned? | Reason |
|---|---|---|
| **Problem (P)** | **Not echoed.** | Both files' first paragraphs open with "This section restates Theorem 1 …". The literal phrase "uniform boundary conditions … ignoring the local geometric structure" does **not** appear. The Method's job is to state the theorem, so the absence is partly structural — but the task asks for an **echo**, and no echo currently exists. |
| **Insight (I)** | **Aligned.** | "the framework's four paper quantities $(A_g, B_g, C_g, e_\rho)$" is named verbatim in both first paragraphs; the Method is where these quantities are introduced. The three scheduler/operator components (CodimensionSheetScheduler, EvidenceDrivenScheduler, BoundedMergeOperator) appear in the §1 third paragraph (line 17) and in §2.3 of `section-2-method.md`, not in the first paragraph. |
| **Scope (V)** | **Not in first paragraph.** | Scope is a §1 / §3 / §5 concern, not a §2 concern. No contradiction. |

**Conclusion.** No **divergence** (contradiction) exists. The Method's
first paragraph aligns on the Insight axis (four paper quantities named
verbatim). The Problem axis lacks the literal echo; **a minimal
leading sentence echoing the abstract's S1 is added** below in §4.

---

## 4. Minimal edits applied

The absence of the literal phrase "uniform boundary conditions … ignoring
the local geometric structure" in the intro and method first paragraphs
is not a contradiction, but it is a missing echo. Three minimal edits
add the echo without altering the surrounding argument:

1. **`docs/drafts/paper-flattened-draft.md` line 13 (Intro §1 first
   sentence):** append an em-dash clause echoing abstract S1 to the
   tail of the existing first sentence, immediately before "and the
   released checkpoints of 2024–2026".
2. **`docs/drafts/section-2-method.md` line 1 (Method §2 Scope
   paragraph):** add a leading sentence that states the abstract's
   framing before the existing "**Scope.** This section restates
   Theorem 1 …" sentence.
3. **`docs/drafts/paper-flattened-draft.md` line 34 (Method §2 stub):**
   add a parallel leading sentence mirroring edit (2) above so that
   the flattened-draft §2 stub and the full §2 Scope paragraph stay in
   lockstep.

**Edit count: 3 minimal insertions, zero deletions, zero rewordings of
existing load-bearing sentences.** Each insertion is a single
sentence / em-dash clause that quotes the abstract's S1 framing
verbatim.

---

## 5. Final consistency verdict (post-edit)

| Axis | Abstract | Intro §1 ¶1 | Method §2 ¶1 | Aligned? |
|---|---|---|---|---|
| **Problem (P)** | "uniform boundary conditions, ignoring local geometric structure" | echo added (post-edit) | echo added (post-edit) | **YES** |
| **Insight (I)** | FlowA + four paper quantities + three scheduler/operator algorithms | "no published framework schedules … convergence-theory witness" (negative form); full quantities appear in §1 ¶3 | "the framework's four paper quantities $(A_g, B_g, C_g, e_\rho)$" verbatim | **YES** (consistent across the three places; full elaboration is in later paragraphs) |
| **Scope (V)** | six R-level cells, N = 1000, 2.5–10× NFE compression | not in ¶1 (appears in §1 ¶3) | not in ¶1 (out of scope for §2) | **YES** (structural absence, no contradiction) |

**Final verdict.** After the three minimal insertions, the abstract's
problem framing is echoed in Intro §1 ¶1 and Method §2 ¶1; the abstract's
insight is consistent (rephrased in intro, verbatim in method); the
abstract's scope is structurally absent from the intro and method first
paragraphs (which is correct — scope belongs to the validation section,
not the framing sections). **No divergence remains.**

---

## 6. Provenance

- **Abstract first sentence** — `docs/drafts/abstract-final.md` line 12,
  finalised in Wave 211 P2 (commit `a818ed6`, DeepSeek F3 framing).
- **Intro §1 ¶1** — `docs/drafts/paper-flattened-draft.md` line 13,
  last touched in Wave 213 P3 (commit `7c78fb7`).
- **Method §2 Scope paragraph** — `docs/drafts/section-2-method.md`
  lines 1–20, last touched in Wave 211 P3 (commit `9774fd3`).
- **Method §2 stub** — `docs/drafts/paper-flattened-draft.md` lines
  34–50, last touched in Wave 213 P3 (commit `7c78fb7`).