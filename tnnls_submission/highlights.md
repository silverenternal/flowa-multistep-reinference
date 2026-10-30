# TNNLS Editor-Facing Highlights — FlowA

**Manuscript:** FlowA: Re-Inference Control for Frozen Flow-Matching Checkpoints

Five highlights, each ≤ 25 words. They are the editor-facing summary and match
the abstract of the current manuscript (`docs/drafts/paper-A-final.pdf`,
2026-10-27 build).

1. Moving the control variable from step count to round boundary changes what a
   frozen flow-matching sampler can reach.
2. At equal NFE, re-inference lowers the MNIST FID plateau by 12.75% on the
   least-trained checkpoint and returns a tie on three better-trained ones.
3. Conditional contraction and an exact restart-blend squared-error identity are
   proved; neither determines the sign of an FID change.
4. Four typed control ports wrap five vendored checkpoints with zero upstream
   edits, and every round is replayable from a hash-chained ledger.
5. The 2.5–10× NFE range is a trajectory-based extrapolation; the directly
   measured Tier-1 speedup is 1.0×.

**Withdrawn.** The former Theorem 4 convergence-rate bound
(`VA ≤ C1·exp(-n/τ_residual) + C2·exp(-T/τ_velocity)`) and Theorem 5
restart-blend attenuation bound (`VA_k ≤ (1-m)·ε_θ·1_{k=1} − (1-m)·σ_blend²·
(k-1)·√(k/L_local)`) are **not** claims of this manuscript and appear in no
editor-facing surface. They were withdrawn after the audit: the
theorems the paper states are conditional contraction (under `mK < 1`) and an
exact squared-error identity, neither of which bounds an FID change. Trail:
[`docs/audit/wave372-manuscript-claim-audit.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave372-manuscript-claim-audit.md);
see also the §IX limitation on the contraction hypothesis.

**Provenance (per highlight).**

- **1–2** — `docs/drafts/paper-A-final.tex` Abstract, §I contribution (ii),
  §VII-J; `docs/audit/paper-packaging-2026-10-27.md`;
  `docs/audit/gap84-inference-frontier.md`; figure
  `docs/figures/fig_r5c_frontier.png`
  (SHA-256 `f677c9b69a99f8f3be6617182c2290503040c18fd47bd4f0e44846395cc486f1`).
- **3** — `docs/drafts/paper-A-final.tex` §VI-B, §VI-C (conditional contraction,
  exact restart-blend identity); proofs in Appendix A.
- **4** — `docs/drafts/paper-A-final.tex` §III-A (four-port surface), §III-E
  (hash-chained ledger), §V-A (zero-line vendored integration).
- **5** — `tnnls_submission/supplementary_bundle/headline_evidence/NFE_SPEEDUP_2P5_TO_10X_SOURCE.md`;
  `verification_outputs/wave73_phase2_tier1_speedup.json`.

**Cross-references.**

- [`docs/drafts/paper-A-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.md)
  — manuscript source
- [`docs/PAPER-EVIDENCE.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/PAPER-EVIDENCE.md)
  — cell-level evidence register
- [`tnnls_submission/cover_letter.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/cover_letter.md)
  — cover letter
- [`tnnls_submission/MANIFEST.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/MANIFEST.md)
  — package manifest and SHA-256 ledger
- [`docs/audit/paper-packaging-2026-10-27.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper-packaging-2026-10-27.md)
  — the packaging pass that produced this file
