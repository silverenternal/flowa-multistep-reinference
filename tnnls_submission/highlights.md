# TNNLS Editor-Facing Highlights — FlowA

**Status:** 5 highlights, each ≤ 25 words (Wave 356 P4 final polish; expanded from
3 highlights at ≤ 85 chars to 5 highlights at ≤ 25 words so the editor-facing
summary surfaces the framework innovations, the two formal theorems, the honest
11-cell verdict distribution, and the camera-ready scope — see
[`docs/audit/wave356-highlights-polish.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave356-highlights-polish.md)
for the per-bullet word-count, character-count, cross-reference, and
quantification audit).

---

## Highlight 1 — Framework innovations (paper §3.4)
**Typed 4-port contract + capability-token handshake enable framework-agnostic
multi-round re-inference with byte-stable evidence trail (Theorem 4 + paper §3.4).**

---

## Highlight 2 — Theorem 4 convergence rate bound (paper §6.5 / §A.1)
**Multi-round re-inference convergence rate bound: VA ≤ C1·exp(-n/τ_residual) +
C2·exp(-T/τ_velocity), derived in Theorem 4 / paper §A.1.**

---

## Highlight 3 — Theorem 5 R5b restart-blend attenuation bound (paper §6.6)
**R5b restart-blend attenuation formal bound (Theorem 5): VA_k(m, ε_θ, L_local)
≤ (1-m)·ε_θ·1_{k=1} − (1-m)·σ_blend²·(k-1)·√(k/L_local), derived in paper §6.6.**

---

## Highlight 4 — Honest 11-cell verdict distribution (paper §5 / §7)
**11 empirical cells validated with honest verdict distribution: 4 STRONG + 1
TIE + 6 PARTIAL/SUPP (paper §5 / §7, three generative domains).**

---

## Highlight 5 — Camera-ready scope disclosed
**Camera-ready scope disclosed: full 3-seed R6 live GPU sweep + R3 RDKit fix +
17 cover-letter USER placeholders (cover_letter.md §0).**

---

## Highlight provenance

- **Highlight 1:** Wave 355 P5 §3.4 capability-token handshake concrete SHA-256
  example ([`docs/audit/wave355-capability-token-example.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave355-capability-token-example.md);
  artifact
  [`verification_outputs/wave355-capability-token-example/synthetic_continuous_capability_token.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave355-capability-token-example/synthetic_continuous_capability_token.json),
  762 bytes, SHA-256 `584f8e02c3eda4fde2bfe1f65651cca6ec2cb9063eea42c70ce15c0ae8b619c8`)
  + Wave 352 P4 framework code anchors
  ([`docs/audit/wave352-framework-code-anchors.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave352-framework-code-anchors.md);
  [`adaptive_reflow/universal/adapter.py:132`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/adaptive_reflow/universal/adapter.py#L132)
  `class AdapterCapabilities`) + paper §3.4 fail-closed-with-audit pattern.
- **Highlight 2:** Wave 353 P1 §A.1 Theorem 4 derivation appendix
  ([`docs/audit/wave353-a1-theorem4-derivation.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave353-a1-theorem4-derivation.md);
  8-section proof extending the §6.5 sketch with BGV12 concentration inequality +
  Grönwall Lipschitz-propagation bound + Sub-claim 4.1 regime-curve corollary) +
  paper §6.5 Theorem 4 main-text statement (line 297).
- **Highlight 3:** Wave 350 P1 §6.6 Theorem 5 closed-form attenuation bound
  ([`docs/audit/wave350-thm5.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave350-thm5.md);
  Eq. (6) at paper line 318) + Wave 351 P3 Theorem 5 numerical validation
  against the Wave 350 P4 12-cell grid
  ([`docs/audit/wave351-thm5-numerical.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave351-thm5-numerical.md);
  L_local ≈ 0.3810 from finite-difference on synthetic RF CIFAR velocity field,
  fitted eps_theta ≈ 0.0506 at canonical m=0.5) + Sub-claims 5.1–5.4 (k* ∈ (1,2)
  Lipschitz-agnostic; first-round-only regime identification; m_max upper bound;
  §10.9 partial close-out).
- **Highlight 4:** Wave 326 crossdoc-metrics-snapshot +
  Wave 306 11-cell alignment
  ([`docs/audit/wave306-11-cell-alignment.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave306-11-cell-alignment.md);
  11 rows × 17 columns audit-grade alignment table) + Wave 307 cross-cell data
  archaeology synthesis
  ([`docs/audit/wave307-archaeology-summary.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave307-archaeology-summary.md);
  verdict distribution: R2 + R5b + R5c + R6 STRONG; R5a TIE; R1 + R3 + R5-legacy
  + K1 + K4 + K5 + K7 PARTIAL/SUPP) + paper §5 (11-cell verdict distribution) +
  §7 (boundary disclosure: matched-NFE=50 first-class honest negative).
- **Highlight 5:** Wave 235 P4 FlowMol3 3-seed partial sweep
  ([`docs/audit/wave235-p4-flowmol3-3seed.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave235-p4-flowmol3-3seed.md);
  DGL 2.4.0+cu124 batched-path bug deferred to camera-ready) +
  [`tnnls_submission/cover_letter.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/cover_letter.md)
  §0 USER TO FILL 17 placeholders enumerated in
  [`tnnls_submission/FILL_GUIDE.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/FILL_GUIDE.md)
  (1 authors block + 1 editor + 5 reviewers × {affiliation, email} + 3
  corresponding-author fields) + camera-ready deferred list (R6 live GPU sweep,
  R3 RDKit fix, FreqFlow + MM-FM integration, Wan2.2 N=1000 sweep).

## Wave provenance

- Wave 235 P1-P5: Top-4 high-leverage improvements
- Wave 236 P1-P5: 24.6× wall-clock fix + final integration
- Wave 237 P1-P2: Abstract trim to ≤250 words (extended to 328 in Wave 242 P3)
- Wave 238 P1-P4: FlowMol3 per-seed diagnostic + journal decision TPAMI → TNNLS +
  CUDA-graph verification + final pre-push
- Wave 242 P1 (in flight): FlowMol3 3-seed NFE=250 single_mol rescue (DGL 2.4.0
  batched-path bug workaround)
- Wave 350 P1: §6.6 Theorem 5 closed-form attenuation bound (paper ADDITIVE)
- Wave 351 P3: Theorem 5 numerical validation against Wave 350 P4 12-cell grid
- Wave 352 P4: §3.4-§3.7 framework code-anchor cross-references
- Wave 353 P1: §A.1 Theorem 4 full derivation appendix (paper ADDITIVE)
- Wave 355 P5: §3.4 capability-token handshake concrete SHA-256 example
- **Wave 356 P4 (this wave): 5-bullet final polish of highlights.md (≤ 25 words
  per bullet, quantified, concrete cross-reference per bullet)**

## Cross-references

- [`docs/cover-letter-tnnls.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/cover-letter-tnnls.md)
  §3 Insight — Paper-Quantity-Driven Scheduling
- [`docs/drafts/abstract-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/abstract-final.md)
  — 250-word TPAMI-envelope abstract
- [`docs/internal/tnnls_submission_action_checklist.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/internal/tnnls_submission_action_checklist.md)
  — TNNLS editorial requirements
- [`tnnls_submission/MANIFEST.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/MANIFEST.md)
  — package manifest
- [`docs/drafts/paper-A-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.md)
  §3.4 + §3.5 + §6.5 + §6.6 + §A.1 — paper source for all 5 highlights
- [`docs/audit/wave356-highlights-polish.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave356-highlights-polish.md)
  — this wave's 5-bullet polish audit