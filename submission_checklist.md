# Submission Checklist — FlowA (ICLR 2027 / NeurIPS Flow-Matching Workshop)

**Date authored:** 2026-09-10
**Author:** Wave 97 Agent A
**Status:** TEMPLATE — pending Wave 92c (Kanzi N=1000 framework paper-metric) + Wave 93 Phase 2 (per-cell CI / Bonferroni / power analysis)

> All boxes are **PLACEHOLDERS** until Wave 92c and Wave 93 Phase 2 land. Wave 94 Phase 2/3 will tick each box with the verified evidence pointer. The list below mirrors §10 of `todo/planned/w5-iclr2027-submission-package.md` (the Wave 94 plan).

---

## Pre-submission gates (tick once verified)

### Paper structure

- [ ] **Paper ≤ 9 pages** (ICLR main-track limit) excluding refs + supplementary — confirm against the current `docs/paper-draft.md` page count post Wave 89 §7.6 reframe. Cite `todo/planned/w5-iclr2027-submission-package.md` §7 risk-register row "Paper > 9 pages after §7 update" mitigation.
- [ ] **Cover letter ≤ 1 page** — `cover_letter.md` at top-level (~700 words; cite `cover_letter.md`).
- [ ] **Anonymized** — no author / institution / acknowledgement visible in `docs/paper-draft.md`, `cover_letter.md`, or supplementary. Strip `.git/config` author + email before final PDF build; use the paper `--anonymize` flag if present in the build pipeline.

### Reviewer-proof guarantees (G1..G4)

- [ ] **G1 SHA-256 ckpt verification** — Kanzi `c2f2ab8d…d270` (cited in `verification_outputs/kanzi_real_ckpt_forward_q4_2026.json`); LineageFlow `f0b4b25e…54a2b` (cited in `verification_outputs/lineageflow_real_ckpt_forward_q4_2026.json`); FlowMol3 `data/flowmol3/weights_real/checkpoints/last.ckpt` (epoch 17, global_step 1,547,236, PyTorch Lightning 2.1.3). Re-verify against `verification_outputs/kanzi_n1000_manifest.json` before ship.
- [ ] **G2 upstream default sampling config** — FlowMol3 `flowmol.FlowMol.sample(...)` at paper-default NFE 250 + perturbation σ 0.05 (framework arm); LineageFlow `evaluation/evaluate_all.py` with `--nfe 250` against Wave-80-vendored Pfam-A.hmm + MMseqs2 target DB; Kanzi `kanzi.DAE.encode+decode+kabsch_rmsd` on Wave-88-vendored 4-PDB reference set. Audit trail: `docs/audit/wave82-phase4-final.md`, `docs/audit/wave81-phase4-final.md`, `docs/audit/wave88-phase2-sweep.md`.
- [ ] **G3 zero new LOC in upstream metric code** — `tools/paper_metrics.py` wraps `posebusters/modules/energy_ratio.py` (PB 0.6.5) + `flowmol/fm3_evals/geometry/{xtb_optimization,rmsd_energy}.py`; `tools/paper_metrics_kanzi.py` wraps `kanzi.DAE` encode/decode/kabsch utilities; `tools/upstream_eval.py` wraps `LineageFlow/evaluation/evaluate_all.py`. No net-new metric math. Audit trail: `docs/audit/wave75-phase2-paper-metrics.md`, `docs/audit/wave83-agent-b-codebook-metrics.md`.
- [ ] **G4 vendored upstream snapshot frozen** — LineageFlow at `ccef84a` ("Prepare LineageFlow public release") under `data/lineageflow_upstream/`; Kanzi at `cfed9cf` under `data/kanzi_upstream/`; FlowMol3 at `77cae22` ("Update readme.md") under `data/FlowMol3/repo/`. All three referenced by SHA-pinned paths in every `verification_outputs/*_n1000_*.json`.

### Tier 3 (model, paper_metric) cells (12 of 12)

> **WAIT** for Wave 92c (Kanzi N=1000 framework paper-metric) + Wave 93 Phase 2 (per-cell CI / Bonferroni / power). The 12 cells are 3 models × 4 paper-axis metrics: FlowMol3 {`fg_dev`, `pb_validity_pct`, `energy_ratio`, `xtb_med_rmsd`} + LineageFlow {`hmmscan_total_hits`, `foldability`, `self_consistency`, `diversity`} + Kanzi {`reconstruction_kabsch_rmsd_A`, `codebook_entropy_bits`, `codebook_perplexity`, `codebook_js_distance`} (5 codebook metrics exist for Kanzi but 4 are `TIED_BY_DESIGN` per `docs/audit/wave91-phase5-final.md` §1).

- [ ] **FlowMol3 / `fg_dev`** — reported with CI + verdict (Wave 82/87 + Wave 90 PB-xtb wire; expect `framework_improves` Δ=-0.0235 / 4.05σ per cover letter)
- [ ] **FlowMol3 / `pb_validity_pct`** — reported with CI + verdict (UFF-vs-xtb definitional gap disclosure required per cover letter; expect `framework_worse` Δ≈-9.95pp)
- [ ] **FlowMol3 / `energy_ratio`** — reported with CI + verdict
- [ ] **FlowMol3 / `xtb_med_rmsd`** — reported with CI + verdict (Wave 90 PB-xtb wire + `flowmol3_xtb_bridge.py`)
- [ ] **LineageFlow / `hmmscan_total_hits`** — reported with CI + verdict (Wave 81 N=1000 sweep; expect `framework_improves` +116% per cover letter)
- [ ] **LineageFlow / `foldability`** — reported with CI + verdict (Wave 84 N=1000 sweep)
- [ ] **LineageFlow / `self_consistency`** — reported with CI + verdict
- [ ] **LineageFlow / `diversity`** — reported with CI + verdict
- [ ] **Kanzi / `reconstruction_kabsch_rmsd_A`** — **WAIT Wave 92c** — currently `NOT_MEASURABLE_N1000` per `docs/audit/wave91-phase5-final.md` §1; expect n=2 → n=1000 jump after Wave 91 Phase 3 bridge wire (commit `8c5eaaf`) + Wave 92a constants fix (`73c6978`) + Wave 92b N-samples patch (`60dcbb7`)
- [ ] **Kanzi / `codebook_entropy_bits`** — reported as `TIED_BY_DESIGN` per Wave 91 §1
- [ ] **Kanzi / `codebook_perplexity`** — reported as `TIED_BY_DESIGN`
- [ ] **Kanzi / `codebook_js_distance`** — reported as `TIED_BY_DESIGN` (5th Kanzi metric `codebook_utilization` + 6th `codebook_hamming_rotation_invariance` also `TIED_BY_DESIGN` per Wave 91 §1)
- [ ] **Per-cell 12-row table** rendered in `docs/paper-draft.md` §7.6 with Bonferroni-corrected p-values + post-hoc power per cell + verdict column (`SUPPORTED` / `TIE` / `UNDERPOWERED`)

### Verification gates (hard / soft)

- [ ] **D.4 byte-stable regression** — **33/33 PASS** (`tests/test_d4_regression_vectors.py` + `tests/test_adapters/test_regression_vectors.py`); reference run baseline `docs/audit/wave91-phase5-final.md` §0
- [ ] **G-MASTER capability gate** — **7/7 PASS** (hard_pass=5, soft_pass=2; `tools/capability_audit.py --robust`)
- [ ] **`mkdocs build --strict`** — **EXIT=0** (verify before commit; per `todo/STATUS.md` last green at commit `e69ffd8`)

### Submission logistics

- [ ] **Supplementary linked** — `supplementary.md` at top-level; sections S1..S7 covering theory, Tier 1 toys, three model audits, reproducibility, and statistical methodology
- [ ] **Code release URL ready** — user provides HF / GitHub URL (open follow-up per `todo/STATUS.md` "Open follow-ups" §3)
- [ ] **ckpt SHA-256 verified** — every entry in `verification_outputs/ckpt_sha256.json` re-hashed at ship time (placeholder path; confirm `verification_outputs/` artifact exists post-Wave 92c)
- [ ] **Anonymized PDF build** — final PDF built with `--anonymize` flag (if available); `.git/config` author + email scrubbed; no `Co-Authored-By: Claude Code` in any commit currently on `main` (current commits carry this trailer; **rebase required** to drop it before venue submission — coordinate with user)
- [ ] **No push — user-gated** — final commit authored by Wave 94; push deferred until user authorizes (per locked-in constraint since Wave 11; `todo/STATUS.md` push state)

---

## Summary

> Once all boxes above are ticked, `docs/paper-draft.md` is venue-ready for either:
> - **NeurIPS 2026 Workshop on Flow Matching** (deadline 2026-09-25, no anonymization required), or
> - **ICLR 2027 main track** (deadline 2026-09-??, requires anonymization).
>
> User picks one or both per `todo/planned/w5-iclr2027-submission-package.md` §10.

---

## Cross-references

- `cover_letter.md` — anonymized cover letter (TL;DR + 4 reviewer-proof guarantees + honest limitations + reproducibility statement)
- `supplementary.md` — supplementary material (theory S1 + Tier 1 S2 + 3 model audits S3-S5 + reproducibility S6 + statistical methodology S7)
- `todo/planned/w5-iclr2027-submission-package.md` — Wave 94 master plan
- `todo/STATUS.md` — current Wave 93 / 92a/b/c state (in-flight items)
- `docs/CONSOLIDATED_RESULTS.md` — Tier 3 numbers (composite + paper axis)
- `docs/audit/wave91-phase5-final.md` — Wave 91 Kanzi framework paper-metric baseline
- `docs/audit/wave92a-kanzi-fix-constants.md` — Wave 92a constants fix audit
- `docs/audit/wave93-phase2-final.md` — Wave 93 Phase 2 power analysis (pending Wave 92c data)
- `verification_outputs/kanzi_n1000_manifest.json` — ckpt SHA-256 manifest
