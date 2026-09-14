# Final Submission Pre-Flight Checklist (2026-09-14)

## A. Paper package
- [ ] docs/paper-final-neurips.pdf — NeurIPS-template PDF (≤9 pages for main text)
- [ ] docs/paper-draft-anonymous.md — double-blind review version
- [ ] docs/supplementary-neurips.pdf — supplementary PDF (no page limit)
- [ ] cover_letter.md — submission cover letter
- [ ] docs/CLAIMS.md — 39 ACTIVE claims (test-coupled)
- [ ] submission_checklist.md — original Wave 94 submission checklist

## B. Code + data archive
- [ ] Source code archive: `flowa-multistep-reinference-v1.0.1.tar.gz` (git tag 0ef6465)
- [ ] All 8 N=1000 sweep JSONs in `verification_outputs/kanzi_n1000_*/`
- [ ] ckpt SHA-256 manifest (`verification_outputs/ckpt_sha256.json`)
- [ ] vendored upstream snapshots frozen (LineageFlow ccef84a, Kanzi cfed9cf, FlowMol3 77cae22)

## C. Reproducibility gates
- [ ] ruff check: 0 findings (verified Wave 131 Phase 1)
- [ ] D.4 byte-stable: 33/33 PASS (verified Wave 131 + Wave 137)
- [ ] pytest tests/ -k "d4": 33 passed (verified Wave 137)
- [ ] pytest tests/ -q: 5155 passed / 196 skipped / 0 failed (verified Wave 137)
- [ ] python tools/check_claims_consistency.py: PASS — 39 ACTIVE, 0 drift (verified Wave 137)
- [ ] mkdocs build --strict: EXIT=0 (verified Wave 136)
- [ ] Kanzi N=1000 byte-reproducible: delta=0.00e+00 (10 decimal exact)

## D. Reviewer-facing docs
- [ ] docs/headline-evidence/ (10 subdirs + 31 symlinks + 7 SOURCE.md)
- [ ] README.md (Tier-1 SCI submission pointer, freeze SHA 0ef6465)
- [ ] docs/paper-draft.md §10.4 (8 honest negatives + provenance discipline)
- [ ] docs/INSIGHTS.md (A- self-assessment post-Wave 137)
- [ ] docs/GATES.md (D.4 33/33 PASS, pytest 5155 current-state)

## E. Honest negatives (all 8 acknowledged in §10.4)
- [ ] K1: FlowMol3 pb_validity_pct -9.95pp (UFF-vs-xtb gap)
- [ ] K2: Kanzi N=1000 paper-metric TIES (architecture cost)
- [ ] K3: CIFAR v4 matched-NFE +221-226% REGRESSION (cosine ramp)
- [ ] K4: LineageFlow coverage_any_hit UNDERPOWERED
- [ ] K5: LineageFlow top1_family_type TIES at 0
- [ ] K6: LineageFlow foldability/self_consistency N=5 (OmegaFold blocker)
- [ ] K7: LineageFlow novelty_mmseqs2 BLOCKED (Pfam fastas placeholder)
- [ ] K8: Wave 86 LineageFlow N=1000 HMMER raw JSON NOT in repo

## F. Camera-ready deferred (acknowledged, NOT in submission scope)
- [ ] mypy 988 hand-fix
- [ ] Wan2.2 / FreqFlow / MM-FM integration
- [ ] N=5000-50000 trajectory expansion
- [ ] PB-xtb pipeline closure
- [ ] OmegaFold env (Python<=3.10)
- [ ] LineageFlow novelty_mmseqs2

## G. Final commit info
- HEAD: 89e635e (v1.0.1-paper-final tag = 0ef6465)
- Repo: https://github.com/silverenternal/flowa-multistep-reinference.git
- Tier-1 target venue: NeurIPS 2026 / ICML 2026 / ICLR 2026
