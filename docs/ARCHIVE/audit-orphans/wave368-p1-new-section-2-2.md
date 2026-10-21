# Wave 368 P1 — §2.2 The Inference-Dynamics Reformulation (Phase 1 NEW SECTION)

**Status:** COMPLETE — `docs/drafts/paper-A-final.md` §2.2 NEW subsection inserted between §2.1 and §2.3; verification gates 4/4 PASS
**Date:** 2026-09-27 (Wave 368 P1)
**Scope:** §2 Related Work — NEW subsection §2.2 "The inference-dynamics reformulation" inserted after §2.1 + before §2.3 (paper draft)
**Hard guardrails:** NO-PUSH; ADDITIVE only — never modify existing §2.X subsections; preserve all Wave 353-367 audit cross-references intact; do NOT touch vendored code; do NOT touch tnnls_submission/ files

---

## 1. Observed facts

### 1.1 File modified

- **File:** `docs/drafts/paper-A-final.md`
- **Pre-edit SHA-256 (HEAD, Wave 367 P5 final):** `8e3e56a8fa9128aefb202e02753a027ebc620316ffd69b691abc6bbc1e591199`
- **Post-edit SHA-256 (after §2.2 insertion only):** `3bea44960cb0caf9b53eb3498b5cf2bd33da28c179a9f36051adef1a87d1fb7d`
- **`git diff --stat` for Phase 1:** 21 insertions(+), 0 deletions(-) — purely ADDITIVE
- **Total line count:** 1136 → 1159 (+23 lines net including the trailing-newline accounting)

### 1.2 Phase 1 placement decision

The new subsection was placed as **§2.2 "The inference-dynamics reformulation"** between the existing §2.1 and §2.3.

The placement rationale:
- **Wave 367 P3 (commit 755dd7c) DELETED the prior §2.2** ("Convergence theory and theoretical bounds"), moving the Paper B companion cross-reference to §6.7. After Wave 367 P3, the §2 structure is §2.1 → §2.3 → §2.4 (no §2.2).
- The next available subsection number after §2.1 is therefore **§2.2**.
- §2.3 retains its current numbering "Typed ML systems and contract-driven design"; §2.4 retains its current numbering "ML pipeline frameworks: design-level comparison". No renumbering needed.
- Insertion point: line 46 (immediately after the §2.1 final sentence "...This paper occupies a fourth position: algorithm-level re-inference with convergence theory." and immediately before the §2.3 heading "### 2.3 Typed ML systems and contract-driven design").

### 1.3 Content of the new §2.2

The new subsection contains:

- **Title:** "§2.2 The inference-dynamics reformulation"
- **Paragraph 1:** Defines standard flow-matching inference as a single ODE-flow evaluation via Eq. (1): $x_T = \Phi_T^{v_\theta}(x_0)$, $x_0 \sim p_\text{prior}$, $dx_t/dt = v_\theta(x_t, t)$.
- **Paragraph 2:** Defines FlowA's rewrite of both sides of (1) — the iteration formula via Eq. (2) with the restart-blend operator $B_m(a, b) = m \cdot a + (1-m) \cdot b$, $m \in [0, 1]$, and the composite map $G := \Phi_T^{v_\theta} \circ B_m \circ (\text{fresh injection})$.
- **Paragraph 3:** Defines the fixed-point equation (3) for $G$ and notes the frozen velocity field is untouched.
- **Paragraph 4:** Positions Eq. (2) as a fourth position relative to the three known inference-acceleration families (solver-level, trajectory-level, re-inference α-blending); cross-references §6 convergence theory.

The boxed equations (1), (2), (3) define:
- **Eq. (1):** The standard single-shot inference evaluation.
- **Eq. (2):** The two-line iteration formula: restart-blend initial condition + composite map evaluation per round $k = 1, \ldots, n_\text{rounds}$.
- **Eq. (3):** The fixed-point equation for $G$: $x^* = \Phi_T^{v_\theta}(B_m(x^*, x^{\text{fresh}}))$.

### 1.4 Cross-reference validity

The new §2.2's cross-references resolve correctly:

- **"Theorems 4 and 5 below"** — Theorem 4 is at §6.5 (line ~410 of HEAD, post-edit line ~430), Theorem 5 is at §6.6 (line ~439 of HEAD, post-edit line ~459). Both are "below" §2 in the document order.
- **"§6 convergence theory"** — §6 is "Framework Properties" (line 346 of HEAD), which contains Theorems 4 and 5.
- **No dangling cross-references**: the §2.2 text refers only to §6 (which exists) and Theorems 4/5 (which exist at §6.5/§6.6).

### 1.5 SHA-256 delta

| Surface | Pre-edit SHA-256 | Post-edit SHA-256 | Δ |
|---|---|---|---|
| `docs/drafts/paper-A-final.md` | `8e3e56a8fa9128aefb202e02753a027ebc620316ffd69b691abc6bbc1e591199` | `3bea44960cb0caf9b53eb3498b5cf2bd33da28c179a9f36051adef1a87d1fb7d` | +21 lines (ADDITIVE only) |

---

## 2. Verification gates (all 4 PASS)

| Gate | Command | Result |
|---|---|---|
| D.4 byte-stable regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30 passed, 3 warnings in 5.91s |
| Claims consistency | `python3 tools/check_claims_consistency.py` | No drift detected (61 active, 0 provisional, 2 deprecated) |
| ruff lint | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | All checks passed! |
| mkdocs strict build | `mkdocs build --strict` | EXIT_CODE=0 (Documentation built in 28.52 seconds) |

### 2.1 Post-§2.2 verification invariant preservation

- All Theorem 4 / Theorem 5 / Lemma 1-3 equations preserved verbatim (cross-checked)
- §2.1 "fourth position" sentence preserved verbatim (Wave 367 P3 ADDITIVE; unchanged)
- §2.3 / §2.4 content preserved verbatim (no renumbering, no edits)
- §3.4 capability-token-handshake wording preserved verbatim
- §6.5 Theorem 4 multi-round re-inference convergence rate bound preserved verbatim
- §6.6 Theorem 5 R5b restart-blend attenuation formal bound preserved verbatim
- §7.1 11-cell verdict distribution preserved verbatim
- §8.10 reproducibility manifest preserved verbatim
- §11.1 honest-verdict disclosure block preserved verbatim
- All 30/30 D.4 byte-stable regression vectors pass

---

## 3. Interpretation

### 3.1 What was achieved

The new §2.2 introduces the **inference-dynamics reformulation** as the paper's mathematical core. The section formalises FlowA's departure from standard single-shot inference (Eq. 1) into a feedback-driven multi-round dynamical system (Eq. 2) whose composite map $G$ admits a fixed-point characterisation (Eq. 3). The boxed equations now anchor the paper's mathematical identity: every subsequent convergence claim (§6.5 Theorem 4, §6.6 Theorem 5) refers back to $G$ as the object of analysis.

### 3.2 Why this matters

The §2.2 introduction closes a long-standing reviewer's perspective gap: prior to Wave 368 P1, the paper's framework was anchored by the typed-contracts Protocol surface (§3.1) and the per-round StateBundle (§3.3), but the **mathematical core** — what FlowA's loop *is* as a dynamical system — was implicit in §3 prose and explicit only in §6 derivations. The §2.2 insertion makes the mathematical core visible to reviewers at the point where they first encounter FlowA's identity (§2 Related Work), before the framework's typed-contracts surface or the convergence proofs are introduced. The boxed equations (1), (2), (3) now appear within the first 70 lines of §2, anchoring the reader's mental model of FlowA as a dynamical system rather than a control-flow framework.

The §2.2 insertion also strengthens the §2.1 "fourth position" framing from Wave 367 P3: §2.1 established FlowA's position relative to the three inference-acceleration families (solver-level / trajectory-level / re-inference α-blending); §2.2 now shows the **mathematical machinery** that occupies that fourth position — the composite map $G$ and its fixed-point equation. The reader can immediately see *what* the fourth position is, not just *that* it exists.

### 3.3 What was preserved

All Wave 353-367 audit cross-references preserved intact:
- Wave 367 P2 §1 Introduction rewrite (commit 8340320) — unchanged
- Wave 367 P3 §2.1 "fourth position" sentence (commit 755dd7c) — unchanged
- Wave 367 P5 §6 Theory de-wave (commit 7354a49) — unchanged
- Wave 366 P1 abstract disclosure (commit fb04752) — unchanged
- Wave 366 P2 §8.10 reproducibility manifest (commit 79464c7) — unchanged
- Wave 366 P3 §7.2 R6 row footnote (commit 3ee3688) — unchanged

All §3-§11 cross-references preserved. All 30/30 D.4 byte-stable regression vectors preserved. Claims consistency preserved.

### 3.4 What was deliberately not changed

- §1 Introduction (not in scope; Wave 367 P2 handled)
- §2.1 Flow matching inference paradigms (not in scope; Wave 367 P3 ADDITIVE preserved)
- §2.3 Typed ML systems and contract-driven design (not in scope)
- §2.4 ML pipeline frameworks: design-level comparison (not in scope)
- §3 Framework (§3.1-§3.6 not in scope)
- §4 Scheduler family (not in scope)
- §5 Adapter protocol (not in scope)
- §6 Framework properties (not in scope; Wave 367 P5 handled)
- §7 Empirical results (not in scope; numbers preserved)
- §8 Reproducibility (not in scope)
- §9-§11 Limitations / Future work / Conclusion (not in scope)

---

## 4. Smallest next action

No follow-up required. Wave 368 P1 is complete. The §2.2 inference-dynamics reformulation is added, the boxed equations (1)/(2)/(3) anchor the paper's mathematical identity, all four verification gates (D.4 30/30, claims consistency, ruff 0, mkdocs strict) pass.

If Wave 369 opens, the natural follow-up would be to add a back-reference from §6.5 (Theorem 4) and §6.6 (Theorem 5) to the new §2.2, replacing the current prose-level descriptions of $G$ with the boxed-equation formal references. This is not part of the current Wave 368 P1 scope and is documented for future-wave planning only.

---

## 5. Provenance

- **Phase 1 task spec:** computed by workflow script (ADDITIVE §2.2 new section with boxed equation; Wave 268 strict-clean preserved)
- **§2.2 changes applied by:** Wave 368 P1 (this audit doc)
- **Section number assigned:** §2.2 (next available after §2.1, before §2.3)
- **No prior §2.2 collision:** Wave 367 P3 deleted the prior §2.2 (Paper B companion); the §2.2 number is now free.
- **Co-Authored-By:** Claude Code <noreply@anthropic.com>
- **NO-PUSH:** every agent commits; no agent pushes (per `todo/PUSH-READY.md` and AGENTS.md §3 hard guardrail #3)