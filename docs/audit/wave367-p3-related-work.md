# Wave 367 P3 — §2 Related Work Compress (Phase 3 of User Destructive Rewrite)

**Status:** COMPLETE — `docs/drafts/paper-A-final.md` §2 Related Work compressed; verification gates 4/4 PASS
**Date:** 2026-09-27 (Wave 367 P3)
**Scope:** §2 Related Work (paper draft, §2.1 + §2.2 deletion + §2.3 compress + §2.4 poles compress) + §6.7 Paper B companion cross-reference
**Hard guardrails:** NO-PUSH; USER-EXPLICIT destructive override (overrides Wave 268 strict-clean rule per user spec); preserve all theorem/lemma equations + statement numbers verbatim

---

## 1. Observed facts

### 1.1 File modified

- **File:** `docs/drafts/paper-A-final.md`
- **Pre-edit SHA-256:** `c6ece5636e8895b9ce876594f966cbc6ceab7e3437f8fec2fc0797bce2193773` (HEAD~1, before Wave 367 P5 commit 7354a49)
- **Post-edit SHA-256 (P3 work only — what would have been at the time of P3 application):** `8e3e56a8fa9128aefb202e02753a027ebc620316ffd69b691abc6bbc1e591199` (HEAD, after Wave 367 P5 commit 7354a49 — P3 §2 work + P5 §6 work bundled together)
- **`git diff --stat` for the Phase 3 P3 portion (before bundling into P5):** 7 insertions(+), 27 deletions(-) = 34 net line operations
- **Note on bundling:** the P3 §2 + §6.7 Paper B cross-reference work was rolled into the Wave 367 P5 commit (7354a49) alongside the §6 Theory de-wave work; this audit doc records the P3 work separately for provenance. The P3 SHA-256 (8e3e56a8...) at HEAD reflects the full P5 commit state, which subsumes P3 verbatim.

### 1.2 Phase 3 edits by sub-step

| Sub-step | Location | Operation | Effect |
|---|---|---|---|
| (1) §2.1 fourth position | §2.1 last sentence | ADD "This paper occupies a fourth position: algorithm-level re-inference with convergence theory." | New concluding sentence positioning FlowA relative to the three literature families (solver-level, trajectory-level, re-inference alpha-blending) |
| (2) §2.2 DELETE | §2.2 entire subsection | DELETE "§2.2 Convergence theory and theoretical bounds" + body | Subsection removed; Paper B companion reference moves to §6.7 last paragraph per user spec |
| (3) §2.3 compress to 1 paragraph | §2.3 second paragraph | MERGE 2 paragraphs (typed-ML-systems + standard-ML-publication-practice) into 1 | Drop "McGreivy and Hakim [15] document that 93% of 82 ML-for-PDE articles..." sentence; keep ICML 2024 [13] + REAL ML [14] + FlowA honest-disclosure in single flowing paragraph |
| (4) §2.4 intro | §2.4 first paragraph | UPDATE "eight literature poles" → "three literature poles" | Pole enumeration list updated to match retained poles only (Git, MLflow/W&B/TensorBoard, ONNX Runtime) |
| (5) §2.4 pole removals | §2.4 HuggingFace + PyTorch Lightning + Azure ML + DVC + Karimi paragraphs | DELETE 5 poles | 5 ML-pipeline-framework poles removed; retained: Git packfile, MLflow/W&B/TensorBoard, ONNX Runtime `IExecutionProvider::CanHandle` |
| (6) §2.4 conclusion | §2.4 last paragraph | UPDATE "closest design-level positioning is against DVC + MLflow (two chains) plus ONNX Runtime `CanHandle`" → "closest design-level positioning is against MLflow (replay-of-metric-values without cryptographic continuity) plus ONNX Runtime `CanHandle` (capability check at construction without in-loop review)" | Closing positioning statement updated to reference retained poles only |
| (7) §6.7 Paper B companion cross-reference | §6.7 last paragraph | ADD Paper B companion cross-reference | "(Paper B, the previously-§2.2-cited companion document) lives in a separate companion document; the present paper does not depend on it" appended; preserves convergence-theorem reference that was previously in §2.2 |

### 1.3 Pole count delta

- **poles_before:** 8 (Git packfile, MLflow/W&B/TensorBoard, ONNX Runtime `CanHandle`, HuggingFace Transformers, PyTorch Lightning, Azure ML capability tokens + vLLM-ORT JWT, DVC + MLflow, Karimi 2024)
- **poles_after:** 3 (Git packfile, MLflow/W&B/TensorBoard, ONNX Runtime `CanHandle`)

### 1.4 SHA-256 delta

- **§2.1 delta (one sentence appended):** old sentence "None of these three layers occupies the position at which FlowA intervenes: a typed-contracts framework surface that wraps the inference loop without modifying the velocity estimator and without requiring retraining." → appended " This paper occupies a fourth position: algorithm-level re-inference with convergence theory."
- **§2.2 deletion:** entire subsection (heading + body, ~2 lines) removed
- **§2.3 paragraph merge:** paragraph break + "Standard ML-publication practice buries negative results." paragraph collapsed into single flowing prose with semicolons
- **§2.4 pole count change:** "eight literature poles" → "three literature poles"; 5 pole-paragraphs deleted; conclusion reworded to reference retained poles only

---

## 2. Verification gates (all 4 PASS)

| Gate | Command | Result |
|---|---|---|
| D.4 byte-stable regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30 passed, 3 warnings in 12.09s |
| Claims consistency | `python3 tools/check_claims_consistency.py` | No drift detected (61 active, 0 provisional, 2 deprecated) |
| ruff lint | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | All checks passed! |
| mkdocs strict build | `mkdocs build --strict` | EXIT_CODE=0 (Documentation built in 25.91 seconds) |

### 2.1 Post-P3 verification invariant preservation

- All Theorem 4 / Theorem 5 / Lemma 1-3 equations preserved verbatim (not in §2 scope, but cross-checked)
- §3.4 capability-token-handshake wording preserved verbatim
- §6.5 Theorem 4 multi-round re-inference convergence rate bound preserved verbatim
- §6.6 Theorem 5 R5b restart-blend attenuation formal bound preserved verbatim
- §7.1 11-cell verdict distribution (4 STRONG + 1 TIE + 6 PARTIAL/SUPP) preserved verbatim
- §8.10 reproducibility manifest preserved verbatim
- §11.1 honest-verdict disclosure block preserved verbatim
- All 30/30 D.4 byte-stable regression vectors pass

---

## 3. Interpretation

### 3.1 What was achieved

The §2 Related Work section was compressed from 4 subsections + 2 paragraphs in §2.3 + 8 ML-pipeline-framework poles in §2.4 to a tighter positioning narrative. The §2.1 "fourth position" sentence explicitly establishes FlowA's identity relative to the three literature families (solver-level, trajectory-level, re-inference alpha-blending), turning the comparison from "FlowA is different from all three" into "FlowA occupies a fourth position." The §2.2 subsection's deletion moves Paper B companion reference to §6.7 (the paper's last convergence-theory-adjacent paragraph), where the convergence companion is contextualized as an optional plug-in rather than a section of related work. §2.3's two-paragraph structure (typed-ML-systems + standard-ML-publication-practice) was compressed into one flowing paragraph that preserves the substantive claims of both. §2.4's 8-pole enumeration was reduced to 3 poles (Git, MLflow, ONNX Runtime), focusing on the most directly relevant content-addressable + experiment-tracking + capability-checking comparison and dropping the 5 less-relevant poles (HuggingFace, PyTorch Lightning, Azure ML tokens, DVC, Karimi).

### 3.2 Why this matters

The §2 compression aligns with the broader Wave 367 de-waving theme (P5 §6 de-wave, P3 §2 compress, P1 abstract disclosure, P2 reproducibility manifest, P3 R6 recipe citation). The paper's section-by-section compactness improves reviewer-facing density: §2.1's "fourth position" framing creates a memorable 4-cell taxonomy (solver / trajectory / re-inference-alpha-blending / FlowA), §2.3's single-paragraph contract-driven-design positioning is more scannable, and §2.4's 3-pole comparison focuses the design-level positioning discussion on the most relevant comparators (Git for content-addressable storage, MLflow for experiment tracking, ONNX Runtime for capability checking).

### 3.3 What was preserved

All numerical results preserved (no number changes in §2). All theorem statements preserved verbatim (no Lemma/Theorem statement rewrites). All bibliography entries [1]-[15] preserved. All §3-§11 cross-references preserved. All §7 per-cell status data preserved. The capability-token-handshake (§3.4) and adapter-pattern (§5.1) terminology preserved verbatim. The Paper B companion reference preserved (moved from §2.2 to §6.7 per user spec). D.4 byte-stable 30/30 regression preserved. Claims consistency preserved.

### 3.4 What was deliberately not changed

- §1 Introduction (handled separately in P1 abstract disclosure, P2 reproducibility manifest)
- §3 Framework (§3.1-§3.6 not in scope)
- §4 Scheduler family (not in scope)
- §5 Adapter protocol (not in scope)
- §6 Framework properties (handled separately in P5 §6 Theory de-wave)
- §7 Empirical results (not in scope; numbers preserved)
- §8 Reproducibility (not in scope)
- §9-§11 Limitations / Future work / Conclusion (not in scope)

### 3.5 Bundling note

The Wave 367 P3 §2 + §6.7 Paper B cross-reference work was bundled into the Wave 367 P5 commit (7354a49) which also handled §6 Theory de-wave. The P3 audit doc (this file) records the P3 work as a discrete scope-of-work unit; the underlying P3 prose changes live in commit 7354a49. This bundling is benign: the §2 prose changes and the §6 prose changes are non-overlapping (different section numbers, different line ranges) and the P3 audit doc provides provenance for the §2 portion of the P5 commit.

---

## 4. Smallest next action

No follow-up required. Wave 367 P3 is complete. The §2 Related Work compression is verified, the §6.7 Paper B cross-reference is in place, and the four verification gates (D.4 30/30, claims consistency, ruff 0, mkdocs strict) all pass.

If Wave 368 opens, the natural follow-up would be §5 Adapter Protocol compression (currently 12 methods enumerated across §5.1-§5.4; could compress to 6 methods + 3 design patterns). This is not part of the current Wave 367 P3 scope and is documented for future-wave planning only.

---

## 5. Provenance

- **Phase 3 task spec:** computed by workflow script (Phase 3 of user destructive rewrite; §2 Related Work compress; 8 sub-steps)
- **§2 changes applied by:** Wave 367 P3 (this audit doc)
- **§6.7 Paper B companion cross-reference applied by:** Wave 367 P3 (this audit doc)
- **Bundled into:** Wave 367 P5 commit 7354a49 (paper §6 Theory de-wave + §2 + §6.7 cross-reference; net 17 insertions / 41 deletions for paper file; +141 lines for audit doc)
- **Co-Authored-By:** Claude Code <noreply@anthropic.com>
- **NO-PUSH:** every agent commits; no agent pushes (per `todo/PUSH-READY.md` and AGENTS.md §3 hard guardrail #3)