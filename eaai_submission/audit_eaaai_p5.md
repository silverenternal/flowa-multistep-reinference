# Wave 187 P5 — EAAI Submission Package Audit

**Date:** 2026-09-18
**Branch:** main
**Scope:** Wave 187 P5 — prepare the EAAI submission package for *Engineering Applications of Artificial Intelligence* (Elsevier). Four artifacts authored; freeze-marker commit verified; final tag created and pushed.

---

## 1. Artifacts authored

| Artifact | Path | Word count / length | Spec target |
|---|---|---|---|
| Cover letter | `eaai_submission/cover_letter.md` | 498 words | 300-500 words |
| Highlights | `eaai_submission/highlights.md` | 3 EAAI editor-facing bullets | 3-5 bullets |
| Data availability | `eaai_submission/data_availability.md` | full statement | required by EAAI |
| Submission checklist | `eaai_submission/submission_checklist.md` | 8 sections, 30+ ticks | required |

### 1.1 Cover letter framing

The 498-word cover letter frames FlowA as a **training-free, inference-time re-inference framework** for deployed flow-matching checkpoints. The five content sections are:

1. **What FlowA is, in one sentence** — 8-method `FlowMatchingODEAdapter` Protocol, 17 typed state machines, 333 typed transitions, 4 pluggable feedback loops, $(A_g, B_g, C_g, e_\rho)$ as algorithm inputs, solver-agnostic, Wave 185 §11.1 localization.
2. **Six R-level Bonferroni-significant claims** — R1 HMMER +116%, R2 Kanzi foldability, R3 FlowMol3 fg_dev, R4 ESM-2 NLL, R5 TwoDim-FM Pareto-frontier (CIFAR-10 RF FID −44.17%, 2D Two Moons $W_2$ −7.28%, 2D Eight Gaussians $W_2$ −10.40%, MNIST FM FID −15.01%), R6 LineageFlow foldability + scPerplexity.
3. **Four-arm head-to-head wins** — vanilla + Fast-DLLM + AB-Cache + LeDiFlow on R6 task (§10.30, N=30 per cell, 3 seeds × 2 NFE settings, 16 per-cell cells).
4. **Five adapters × three domains** — `KanziAdapter` + `LineageFlowAdapter` + `FlowMol3Adapter` + `FreqFlowAdapter` + `TwoDimFMAdapter` spanning protein / molecular / image.
5. **Reproducibility — D.4 33/33 PASS + SHA-256 + Zenodo DOI** — D.4 regression vectors, SHA-256 ckpt pinning, hash-chained ledger, Zenodo tarball SHA-256 `9699cd42...430d7` (≈ 3.00 GiB).

The closing section justifies the EAAI fit: FlowA is an AI-engineering contribution (improves deployed checkpoints without retraining), ships behind a typed Protocol (domain experts can plug in), is governed by a published theoretical bound (JMAA Theorem 1), and is byte-stable reproducible across heterogeneous FM deployments. Honest negatives are disclosed plainly in §5.7 of the manuscript.

### 1.2 Highlights

Three EAAI editor-facing bullets summarize the manuscript's contribution for the journal homepage / editor's desk:

- Training-free, drop-in inference layer for deployed flow-matching checkpoints.
- Six Bonferroni-significant empirical claims + four-arm head-to-head wins.
- 5 adapters × 3 domains cross-domain validation, byte-stable reproducible, with 2.5-10× NFE speedup.

A closing paragraph ("Why this matters to the EAAI readership") ties the contribution back to EAAI's emphasis on deployment-relevant AI-engineering systems.

### 1.3 Data availability

The data availability statement enumerates:

- Repository + freeze-marker commit + license + final tag.
- SHA-256 ckpt manifest (Kanzi, LineageFlow, FlowMol3).
- Vendored upstream snapshots (LineageFlow `ccef84a`, Kanzi `cfed9cf`, FlowMol3 `77cae22`).
- Vendored reference data (Pfam-A.hmm, MMseqs2 target DB, 4-PDB Kanzi reference set, CIFAR-10 inception features, MNIST FM cache).
- Per-claim evidence paths on disk.
- Reproducibility methodology (D.4 + SHA-256 + hash-chained ledger).
- Zenodo long-term archival (tarball SHA-256 `9699cd42...430d7`, ≈ 3.00 GiB).
- Out-of-band resources (Pfam-A.fasta re-hosted separately).

### 1.4 Submission checklist

8 sections, 30+ tickboxes covering editorial requirements, reviewer-proof guarantees (4 gates green), manuscript content checks, length / format checks, code + data + reproducibility checks, supplementary checks (S1-S7), honest disclosure (§5.7 / §7.3 / §7.5), and final pre-flight steps. Status: all boxes ticked except user-gated Editorial Manager upload (out of scope).

## 2. Freeze-marker commit verification

The freeze-marker commit is **`3d816e0`** (Wave 187 P4 final-gate verification, 2026-09-18, parent of all Wave 187 P5 work). All four gates were verified green at this commit:

| Gate | Status |
|---|---|
| D.4 byte-stable regression (`pytest tests/ -k "d4" -q`) | **33 passed, 30 skipped, 5028 deselected** |
| ruff lint | **All checks passed!** |
| claims_consistency | **No drift detected.** (45 active, 0 provisional, 2 deprecated) |
| mkdocs build --strict | **EXIT=0** |

Reference: `docs/audit/wave187-p4-final-gate-verification.md`.

## 3. Commit + push + tag

The four `eaai_submission/*.md` artifacts + this audit doc were committed to `main` and pushed to `origin/main`. The final tag `v1.1-paper-final-eaai-ready` was created with the annotated message `Wave 187 camera-ready + EAAI submission package` and pushed to `origin`.

## 4. Outstanding (user-gated)

- **Editorial Manager upload** — the four files + `docs/paper-draft-anonymous.md` + `supplementary.md` are ready to upload to `https://www.editorialmanager.com/ENGAP/`. This step is user-gated and not in scope of Wave 187 P5.
- **Confirmation email** — the EAAI editorial office will issue a manuscript ID after upload.

## 5. Cross-references

- `eaai_submission/cover_letter.md` — anonymized cover letter (498 words).
- `eaai_submission/highlights.md` — 3 editor-facing bullets + EAAI fit paragraph.
- `eaai_submission/data_availability.md` — full data + code + ckpt + reproducibility statement.
- `eaai_submission/submission_checklist.md` — 8-section submission checklist.
- `docs/paper-draft-anonymous.md` — double-blind manuscript.
- `supplementary.md` — S1-S7 supplementary material.
- `docs/audit/wave187-p4-final-gate-verification.md` — pre-submission 4-gate verification.
- `docs/zenodo-release/manifest.md` — Zenodo release manifest.
- `verification_outputs/ckpt_sha256.json` — SHA-256 ckpt manifest.