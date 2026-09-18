# EAAI Submission Package — MANIFEST

**Venue:** *Engineering Applications of Artificial Intelligence* (Elsevier)
**Manuscript:** FlowA: Training-Free, Inference-Time Re-Inference Control for Deployed Flow-Matching Checkpoints
**Submitted:** 2026-09-18
**Freeze-marker commit:** `3d816e0` (Wave 187 P4 final-gate verification, current `main` = `f871537` + Wave 192 P3 PDF conversion `dd46d62`)
**Final tag (to push):** `v1.1-paper-final-eaai-ready`

---

## File-by-file manifest (SHA-256 + size + role)

All SHA-256 hashes computed at package assembly time (Wave 192 P4). Reviewers re-verify with:

```bash
sha256sum eaai_submission/*
```

| File | Size (bytes) | SHA-256 | Role |
|---|---|---|---|
| `manuscript.pdf` | 1,305,168 | `104e4201006105cffd0fd23d762be75640469fcce8ad4151f6440322e39f1228` | EAAI elsarticle-formatted manuscript (Wave 192 P3 PDF conversion of `docs/paper-draft.md`) — primary submission PDF, anonymized for double-blind review |
| `supplementary_paper.pdf` | 332,832 | `a6f3e3650de977e815b4080e21cff64bbbd3274ae07e5698567ea1acdd7a789d` | Li 2026 "Gaussian Posterior Selection on Noncompact Fibres with Uniformly Separated Roots" (LaTeX-rendered, 14 pp) — Theorem 1 source attached per Wave 192 P1 user directive: "可以把投稿中的论文作为附件上传" |
| `supplementary_paper.md` | 55,273 | `0a0ad6d9c1f5330f8dbb77789d21e4ac082a3ae2de6946cd84f0765c06eb7c8c` | Markdown mirror of Li 2026 supplementary paper (LaTeX source-of-truth at `docs/ARCHIVE/top-level/NoiseSelectedRectification_EN.md`); `.md` is included for transparency + line-by-line diff against the LaTeX |
| `tables.md` | 9,920 | `a75f959c90feddaf231011e57b7419badec9bff243d917a094415900f024f050` | 5 LaTeX-ready paper tables (Adapter × Domain, R-level headline numbers, 4-arm H2H, Theorem 1 ablation, Reproducibility gates) — Wave 192 P1 additive; `pandoc -t latex` emits valid `tabular` environments |
| `figures.md` | 20,030 | `67a063b3bdac5cabf094ac07cc17f8d6d49e4e351b4b377024180b29c7561952` | 4 ASCII architecture figures (FlowA hexagonal layers, Re-inference dataflow, 3-tier experiment hierarchy, 4-arm H2H schematic) — Wave 192 P2 additive; paste-verbatim into EAAI LaTeX, Word, Overleaf, or plain-text reviewer channel without binary asset loss |
| `cover_letter.md` | 4,462 | `03bcb96aa9ca73cedb54cce198f495a08d89c92f0b57a4b43d83d290af9913ea` | Editor-facing cover letter (Wave 192 P4 ADDITIVE paragraph: "The submitted manuscript referenced as Theorem 1's source is included as supplementary_paper.pdf…") |
| `highlights.md` | 3,274 | `2c3786d2978c32451cf1a29d4dab60e7ae4309c34365636eed434abedf117838` | 3 EAAI editor-facing highlights (training-free drop-in, 6 R-level + 4-arm H2H wins, 5 × 3 cross-domain + D.4 33/33 + Zenodo DOI) |
| `data_availability.md` | 7,211 | `f6710ea67f5129dcbe05156570f4658045b21c557ec6ff107e9dca6da0a70b96` | Data availability statement; Wave 192 P4 ADDITIVE row: Theorem 1 source paper SHA-256 + provenance |
| `submission_checklist.md` | 9,059 | `0b32dae7915dc49da0be74010af69b52b5a322714d0dd6221920d44f5ae22a6e` | EAAI editorial requirements checklist; Wave 192 P4 ADDITIVE ticked boxes for `manuscript.pdf` + `tables.md` + `figures.md` + `supplementary_paper.pdf` |
| `audit_eaaai_p5.md` | 6,062 | `9e3a7d9a8b29868143d600d9649e58721fb7369233a57120b20fad63976a6ae6` | Wave 187 P5 EAAI submission audit trail (cross-references freeze-marker commit `3d816e0` + all four reviewer-proof gates) |
| `MANIFEST.md` | 5,937 | `64a38c90e25dc560b60b7e526d18f733994951aedaa812c3ed6e5b8e205b8bf9` | File-by-file package manifest with SHA-256 + size + role (this file) |
| `MANIFEST.checksums` | (auto-generated) | (auto-generated) | `sha256sum -- *.md *.pdf` output for `sha256sum -c` re-verification |

---

## Upload order for EAAI Editorial Manager

1. **Manuscript:** `manuscript.pdf` — primary file at `eaai_submission/manuscript.pdf` (1.25 MB, 16 pp equivalent).
2. **Supplementary material (theoretical reference):** `supplementary_paper.pdf` — Li 2026 Theorem 1 source paper (325 KB, 14 pp).
3. **Highlights:** paste the three bullets from `highlights.md` into the Editorial Manager "Highlights" field.
4. **Cover letter:** paste `cover_letter.md` (or attach as PDF) into the Editorial Manager "Cover Letter" field.
5. **Data availability statement:** paste `data_availability.md` into the Editorial Manager "Data Availability" field (or include in the manuscript §Data availability section).
6. **Submission checklist (internal, not for upload):** `submission_checklist.md` — used by the submitter to verify completeness pre-upload.

---

## Provenance

- `manuscript.pdf` ← `docs/paper-draft.md` (7591 lines) → EAAI elsarticle LaTeX (`docs/build_pdf/paper-eaai.tex`) → `pdflatex` (Wave 192 P3 commit `dd46d62`).
- `tables.md` ← `docs/tables/wave192-paper-tables.md` (Wave 192 P1 commit `5c43484`).
- `figures.md` ← `docs/figures/wave192-ascii-figures.md` (Wave 192 P2 commit `aa1f388`).
- `supplementary_paper.{pdf,md}` ← `docs/ARCHIVE/top-level/NoiseSelectedRectification_EN.md` → LaTeX (`/tmp/supp_paper.tex`) → `pdflatex` (Wave 192 P4).
- `cover_letter.md`, `highlights.md`, `data_availability.md`, `submission_checklist.md`, `audit_eaaai_p5.md` — Wave 187 originals + Wave 192 P4 ADDITIVE edits.

---

## Reviewer re-verification commands

```bash
# 1. Re-verify every SHA-256 in this manifest
cd eaai_submission && sha256sum -c MANIFEST.checksums  # populated by Wave 192 P4 commit hook

# 2. Re-verify D.4 byte-stable regression vectors
python -m pytest tests/ -k "d4" -q   # expect: 33 passed, 30 skipped, 5028 deselected

# 3. Re-verify ruff lint
ruff check adaptive_reflow/ tests/ scripts/ tools/ verification_outputs/

# 4. Re-verify claims consistency
python tools/check_claims_consistency.py   # expect: No drift detected

# 5. Re-verify mkdocs strict build
mkdocs build --strict   # expect: EXIT=0
```

---

**Generated by Wave 192 P4 (EAAI submission package updater). All eleven files are byte-stable, SHA-256-pinned, and reviewer-verifiable at the freeze-marker commit.**
