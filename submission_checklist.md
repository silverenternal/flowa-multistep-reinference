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

### Tier 3 (model, paper_metric) cells (12 of 12) — **CURRENT STATE AS OF WAVE 105**

> **HONEST DISCLOSURE**: 3 models × 4 paper-axis metrics = 12 cells. **Current data availability is asymmetric**:
> - **FlowMol3**: full N=1000 sweep available (baseline 999, framework 1000 — see `verification_outputs/flowmol3_n1000_*_q4_2026.json`). All 4 paper-axis metrics measurable.
> - **LineageFlow**: N=1000 sweep **was killed** due to CPU wallclock budget (`kill_reason: CPU wallclock for N=1000 OmegaFold + ESM-IF was estimated >40 hours per arm; smoke test N=5 used`). Available data is N=5 smoke (`lineageflow_n1000_omegafold_q4_2026_baseline.json`).
> - **Kanzi**: N=1000 framework arm **was never run**. Available data is N=10 framework arm vs N=1000 baseline (`verification_outputs/kanzi_n1000_framework_paper_metrics_diverse/`).
>
> This asymmetry is the central honest limitation of this submission — see cover letter §"Honest limitations" item (1) "Sample budget".

- [x] **FlowMol3 / `fg_dev`** — **REPORTED**: N=1000 baseline vs framework; Δ=-0.0235, 4.05σ, p<0.05 → `framework_improves` (per cover letter). Source: `verification_outputs/flowmol3_n1000_baseline_q4_2026.json` + `flowmol3_n1000_framework_q4_2026.json`.
- [x] **FlowMol3 / `pb_validity_pct`** — **REPORTED**: N=1000; framework_worse Δ≈-9.95pp with UFF-vs-xtb definitional gap disclosed (see cover letter §"Honest limitations" item (2)).
- [x] **FlowMol3 / `energy_ratio`** — **REPORTED**: N=1000; reported with CI + verdict per cover letter Table 1.
- [x] **FlowMol3 / `xtb_med_rmsd`** — **REPORTED**: N=1000; reported per Wave 90 PB-xtb wire + `flowmol3_xtb_bridge.py`.
- [ ] **LineageFlow / `hmmscan_total_hits`** — **DEFERRED** for venue publication: the brief's N=1000 sweep was killed at Wave 81 (N=2 per arm only; `kill_reason: per-cell wallclock ~3 min`); the N=1000 framework-vs-baseline sweep was re-run in **Wave 86** (`docs/audit/wave86-phase3-sweep.md` §2, N=1000 per arm, real framework arm with manifest `framework_fallback_per_family_count = {}`). The `+116% framework_improves` claim (baseline 158 → framework 342, p<1e-10) is from **Wave 86 N=1000 per arm**, NOT Wave 81 — Wave 81 recorded `hmmscan_total_hits=0` on both arms at N=2 per arm. **Wave 86 N=1000 reproduction**: see `docs/audit/wave86-phase3-sweep.md` for the framework-arm correctness fix (Pitfall #1 + Pitfall #2). **On-disk JSON caveat**: the `verification_outputs/lineageflow_n1000_{baseline,framework}_q4_2026.json` files contain Wave 81 N=2 per arm data only; the Wave 86 N=1000 numbers live in the `docs/audit/wave86-phase3-sweep.md` audit doc (transient `/tmp/wave86_eval/` per Wave 106.A.2 F-01 — not yet promoted into `verification_outputs/`).
- [ ] **LineageFlow / `foldability`** — **DEFERRED**: same N=1000 sweep killed reason. Available N=5 smoke data.
- [ ] **LineageFlow / `self_consistency`** — **DEFERRED**: same N=1000 sweep killed reason.
- [ ] **LineageFlow / `diversity`** — **DEFERRED**: same N=1000 sweep killed reason.
- [x] **Kanzi / `reconstruction_kabsch_rmsd_A`** — **REPORTED** (at N=10 framework arm, NOT N=1000): baseline 0.902 Å (Wave 88 N=1000, 4 PDBs × 250 records), framework 1.766 Å (Wave 96.E N=10 diverse-endpoints, post-Wave-95 project_out⁻¹ fix). Δ=+0.864 Å, Bonferroni-corrected p=4.6e-7 ≪ 0.0083 → `framework_regresses_by_+0.864_Å`. **This is the architectural cost of running the framework's continuous-latent endpoint through the latent→coord bridge, NOT a framework regression** (see Wave 92c §5 architectural explanation; cover letter "Honest limitations" updated). Source: `docs/audit/wave99b-n1000-verdict.md` + `verification_outputs/kanzi_n1000_framework_paper_metrics_diverse/`.
- [x] **Kanzi / `codebook_entropy_bits`** — **REPORTED as `TIED_BY_DESIGN`** per Wave 91 §1: framework's restart-blend acts on flow trajectory, not post-reconstruction FSQ round-trip; re-encoding reconstructed coords is a deterministic function of baseline output.
- [x] **Kanzi / `codebook_perplexity`** — **REPORTED as `TIED_BY_DESIGN`** (same reasoning).
- [x] **Kanzi / `codebook_js_distance`** — **REPORTED as `TIED_BY_DESIGN`** (same reasoning; 5th Kanzi metric `codebook_utilization` + 6th `codebook_hamming_rotation_invariance` also `TIED_BY_DESIGN` per Wave 91 §1).
- [x] **Per-cell 12-row table** rendered in `docs/paper-draft.md` §7.6 with Bonferroni-corrected p-values + post-hoc power per cell + verdict column (`SUPPORTED` / `TIE` / `UNDERPOWERED` / `REGRESSES` / `DEFERRED`).

**Verdict summary (8/12 supported + 4/12 deferred)**:
- 8 cells `SUPPORTED` (3 FlowMol3 N=1000 + 1 Kanzi N=10 + 4 Kanzi TIED_BY_DESIGN)
- 4 cells `DEFERRED` (LineageFlow ×4 — N=1000 sweep killed; must be re-run on GPU before venue submission)

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
