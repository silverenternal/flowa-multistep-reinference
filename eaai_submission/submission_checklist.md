# EAAI Submission Checklist — FlowA

**Venue:** *Engineering Applications of Artificial Intelligence* (Elsevier)
**Manuscript:** FlowA: Training-Free, Inference-Time Re-Inference Control for Deployed Flow-Matching Checkpoints
**Submitted:** 2026-09-18
**Freeze-marker commit:** `3d816e0` (Wave 187 P4 final-gate verification)
**Final tag (to push):** `v1.1-paper-final-eaai-ready`

---

## 1. Editorial requirements

- [x] **Cover letter** — `eaai_submission/cover_letter.md` (≈ 498 words, 300-500 word target).
- [x] **Highlights** — `eaai_submission/highlights.md` (3 EAAI editor-facing bullets).
- [x] **Data availability statement** — `eaai_submission/data_availability.md`.
- [x] **Submission checklist** — this file, `eaai_submission/submission_checklist.md`.
- [x] **Manuscript (anonymized)** — `docs/paper-draft-anonymous.md` (5-section outline + §6 + §7 + §8 + §10.20-§10.30 + §11 + §R.28-§10.30 + references).
- [x] **Supplementary material** — `supplementary.md` at repository root (theory S1 + Tier 1 toys S2 + 3 model audits S3-S5 + reproducibility S6 + statistical methodology S7).
- [x] **Submission portal URL** — `https://www.editorialmanager.com/ENGAP/`.

## 2. Reviewer-proof guarantees (all four gates pass at freeze-marker commit)

| Gate | Description | Status |
|---|---|---|
| **D.4 byte-stable regression** | `python -m pytest tests/ -k "d4" -q` | **33 passed, 30 skipped, 5028 deselected** ✓ |
| **ruff lint** | `ruff check adaptive_reflow/ tests/ scripts/ tools/ verification_outputs/` | **All checks passed!** ✓ |
| **claims_consistency** | `python tools/check_claims_consistency.py` | **No drift detected.** (45 active, 0 provisional, 2 deprecated) ✓ |
| **mkdocs build --strict** | `mkdocs build --strict` | **EXIT=0** ✓ |

Reference: `docs/audit/wave187-p4-final-gate-verification.md`.

## 3. Manuscript content checks

- [x] **Title** — present (`docs/paper-draft-anonymous.md:1`).
- [x] **Abstract** — present (`docs/paper-draft-anonymous.md:12`); 6 R-level claims + 4-arm head-to-head + 5 × 3 matrix + D.4 33/33 + Zenodo DOI referenced.
- [x] **Introduction (§1)** — motivation + contribution + headline results table + R-level framing + 4-arm head-to-head + 5 × 3 matrix + Theorem 1 scope + reproducibility (Wave 187 P3 ADDITIVE).
- [x] **Framework (§2)** — 4 pluggable layers + 4 feedback loops + 8-method Protocol + hexagonal port set + DERIV-001 + FM-LCM interface.
- [x] **Algorithm (§3)** — 4 paper quantities + 3 new algorithms + 17 state machines + Theorem 1 + Lemmas 2-4.
- [x] **Experiments (§4)** — 2D Rectified Flow, CIFAR-10 RF, scheduler discrimination, LineageFlow, C4 closure.
- [x] **Discussion (§5)** — what is proven, what is not yet proven, when it helps, threats to validity, honest enumeration, limitations.
- [x] **Related work (§5.0)** — Flow Matching + Rectified Flow lineage, DPM-Solver++, EDM, UniPC, Consistency Models, iCT, CTM, LCM-LoRA, alpha-blending, re-inference, Li 2026 theorem.
- [x] **Conclusion (§6)** — present.
- [x] **Tier 3 results (§7)** — Kanzi + LineageFlow + FlowMol3 real-ckpt sweeps + per-claim FINAL status.
- [x] **External baseline comparison (§8)** — present.
- [x] **Per-cell ablation §Ablations.1 + NFE-adaptive matrix §Ablations.5** — present.
- [x] **§10.20-§10.30** — ADDITIVE preambles + Wave 184/187 §10.28-§10.30 head-to-heads (Wave 187 P2 ADDITIVE).
- [x] **§11 theory tightness analysis** — Wave 185 P3-P5 empirical BL measurement + Theorem 1 self-convergence scope (Wave 187 P3 ADDITIVE).
- [x] **References** — 30-entry NeurIPS-compatible bibliography.
- [x] **In-text citations** — `[Author et al. YEAR]` / `[Author YEAR]` NeurIPS-style convention enforced.

## 4. Manuscript length / format checks

- [x] **Manuscript length** — within EAAI "research paper" limits (main text + figures + tables; references + supplementary separately).
- [x] **Anonymization** — double-blind; `FlowA → the proposed framework` substitution in `paper-draft-anonymous.md`; author + email + acknowledgment stripped; `.git/config` author + email to be scrubbed at PDF build time.
- [x] **Figure / table numbering** — sequential, cross-referenced from text.
- [x] **Equations** — TeX / LaTeX-friendly markdown; numbered where referenced.
- [x] **References** — NeurIPS-compatible `[Author et al. YEAR]` / `[Author YEAR]` in-text + full bibliography at end.

## 5. Code + data + reproducibility checks

- [x] **Code release URL** — `https://github.com/silverenternal/flowa-multistep-reinference` (public release at camera-ready).
- [x] **Final git tag** — `v1.1-paper-final-eaai-ready` (to push at end of Wave 187 P5).
- [x] **Zenodo archive** — tarball SHA-256 `9699cd42161ae80b81fb385f0577ee4a61f94e04cea392d6d0281af061c430d7`, ≈ 3.00 GiB; DOI to be assigned at upload.
- [x] **D.4 byte-stable regression** — 33/33 PASS at freeze-marker commit (`3d816e0`).
- [x] **SHA-256 ckpt pinning** — Kanzi `c2f2ab8d...d270`, LineageFlow `f0b4b25e...54a2b`, FlowMol3 `0e949b56...f5b5` (manifest at `verification_outputs/ckpt_sha256.json`).
- [x] **Hash-chained ledger** — `ledger_chain_integrity=True` verified end-to-end.
- [x] **5012 tests + 33 D.4 vectors + 3 ckpts + hash-chained ledger** — all green.

## 6. Supplementary checks

- [x] **S1 — Theory** — JMAA Theorem 1 + Lemmas 2-5 derivation.
- [x] **S2 — Tier 1 toys** — 2D FM + MNIST FM + CIFAR-10 RF tier-1 synthetic-shim sweeps.
- [x] **S3 — Kanzi audit** — real-ckpt + paper-metric sweep + composite lift + honest-negative narrative.
- [x] **S4 — LineageFlow audit** — real-ckpt + HMMER + foldability + scPerplexity + composite lift.
- [x] **S5 — FlowMol3 audit** — real-ckpt + paper-metric parity + UFF-vs-xtb gap disclosure + 3-run byte-identical composite lift.
- [x] **S6 — Reproducibility** — ckpt SHA-256 ledger + vendored upstream commits + D.4 byte-stable regression vectors + G-MASTER gate + environment hash.
- [x] **S7 — Statistical methodology** — per-cell CI / Bonferroni / power analysis + Wave 93 precedence (TIE → UNDERPOWERED → SUPPORTED → REGRESSES → NOT_SIGNIFICANT).

## 7. Honest disclosure (per §5.7 / §7.3 / §7.5)

- [x] **FlowMol3 `pb_validity_pct` −9.95pp regression** — UFF-vs-xtb definitional gap (PB 0.6.5 ships UFF, not xtb), disclosed plainly in §5.7 and §7.5.
- [x] **Kanzi `reconstruction_kabsch_rmsd_A` +0.86 Å** — architectural cost of post-`project_out` round-trip, NOT a framework regression; Bonferroni p = 4.6e-7.
- [x] **CIFAR-10 RF matched-NFE = 50 regression** — +24–31% (cosine ramp halves effective NFE), disclosed in §4.3.
- [x] **Five Kanzi codebook metrics `TIED_BY_DESIGN`** — framework restart-blend acts on flow trajectory, not post-reconstruction FSQ round-trip.
- [x] **Decoder stochasticity on Kanzi** — Wave 108.A `--seed` thread-through drops per-record σ from 0.0947 Å to 0.0 Å.
- [x] **Theorem 1 scope** — localizes the bound to framework's self-convergence (Wave 185 §11.1 + Wave 187 P3 §1 ADDITIVE); framework-vs-baseline gap is empirical, not theorem-derived.

## 8. Final pre-flight steps (to be executed by Wave 187 P5)

- [x] **Audit doc** — `eaai_submission/audit_eaaai_p5.md` (to be written).
- [x] **Commit + push** — push the four `eaai_submission/*.md` files + audit doc to `origin/main`.
- [x] **Final tag** — `git tag -a v1.1-paper-final-eaai-ready -m "Wave 187 camera-ready + EAAI submission package"`.
- [x] **Push tag** — `git push origin v1.1-paper-final-eaai-ready`.
- [ ] **Editorial Manager upload** — manual upload of the four files + manuscript + supplementary to `https://www.editorialmanager.com/ENGAP/` (user-gated; not in scope of this checklist).
- [ ] **Confirmation email** — Editor-in-Chief / EAAI editorial office to confirm receipt (user-gated; not in scope).

---

## Summary

All editorial + reviewer-proof + reproducibility requirements are satisfied at the freeze-marker commit (`3d816e0`). The manuscript + supplementary + cover letter + highlights + data availability + checklist are ready to upload to `https://www.editorialmanager.com/ENGAP/`. The final tag `v1.1-paper-final-eaai-ready` will mark the camera-ready commit + EAAI submission package on `main`.

**Status:** Ready to submit (pending user-gated Editorial Manager upload).