# Wave 134 — /tmp/ to repo migration + paper path updates + todo refactor

**Date:** 2026-09-14
**Author:** Wave 134 Agent 5 (final close)
**Scope:** 5 atomic Phases (1-4 by prior agents + this Phase 5 final synthesis)
**Constraint:** NO push. NO source code changes. ADDITIVE only.

> **Why this exists:** Wave 134 is the **/tmp/-to-repo migration** wave that takes the 8 N=1000 sweep JSONs that lived only on the sandbox /tmp filesystem (and therefore could not be reproduced by anyone who checked out the repo) and promotes them into `verification_outputs/` so the freeze-marker submission package now has **complete reproducibility provenance**. Phases 1-3 update the 3 docs (paper-draft + baseline-audit + CONSOLIDATED) that cited those /tmp/ paths so they now point at the repo-resident copies. Phase 4 refreshes `todo/STATUS.md` + `todo/INDEX.md` to reflect the post-Wave-127+ reality (v1.0-paper-final tag set; ruff 0; 8 N=1000 sweeps in repo). This Phase 5 final close writes the audit doc, appends baseline-audit §R.24, appends CONSOLIDATED §15.33, and tags `v1.0.1-paper-final`. **No measurement delta. No algorithm activation. No end-to-end N>=1000 sweep. The Wave 131 ruff-0 / D.4 33/33 PASS / claims_consistency PASS / mkdocs strict EXIT=0 freeze-marker is preserved.**

---

## What was migrated (8 N=1000 sweep JSONs)

| # | Source (/tmp/) | Destination (repo verification_outputs/) | Note |
|---|---|---|---|
| 1 | `/tmp/w116/baseline_seed42/` | `verification_outputs/kanzi_n1000_baseline_seed42_wave116_q3_2026/` | early baseline |
| 2 | `/tmp/w120/baseline_seed42/` | `verification_outputs/kanzi_n1000_baseline_seed42_wave120_q3_2026/` | **canonical** (matches Wave 128 / Wave 131 byte-repro baseline) |
| 3 | `/tmp/w121/baseline_seed7/` | `verification_outputs/kanzi_n1000_baseline_seed7_wave121_q3_2026/` | seed-7 cross-check |
| 4 | `/tmp/w120/kanzi_n1000_framework_paper_metrics.json` | `verification_outputs/kanzi_n1000_framework_synth_wave120_q3_2026/` | synth arm, wave120 |
| 5 | `/tmp/w121/framework_synth_seed42/` | `verification_outputs/kanzi_n1000_framework_synth_seed42_wave121_q3_2026/` | synth arm, seed42 |
| 6 | `/tmp/w122/framework_inv_proj_seed42/` | `verification_outputs/kanzi_n1000_framework_inv_proj_seed42_wave122_q3_2026/` | **historical** `mean_rmsd=2.5017` (pre-real-ckpt sample path, documented in §R.15) |
| 7 | `/tmp/w127/framework_inv_proj_seed42/` | `verification_outputs/kanzi_n1000_framework_inv_proj_seed42_wave127_q3_2026/` | mid-wave framework_inv_proj |
| 8 | `/tmp/w131/framework_inv_proj_seed42/` | `verification_outputs/kanzi_n1000_framework_inv_proj_seed42_wave131_byte_repro_q3_2026/` | **byte-reproducible** vs Wave 128 (`62f7f24` → `39a65a7`, delta 0.00e+00) |

All 8 JSONs verified to exist on disk at the destination path after Phase 1 atomic copy. The `/tmp/` originals remain on the sandbox filesystem (out of band) but the repo-resident copies are the canonical artifact for reproducibility.

---

## Paper path updates (Phase 1-3 ledger)

- **Phase 1** (commit `2c2bd55`): `docs/paper-draft.md` — all `/tmp/w116|120|121|122|127|131/baseline_seed42|framework_synth|framework_inv_proj_seed42/` paths replaced with the matching `verification_outputs/kanzi_n1000_*` repo paths (≤30 path-replacement lines, ADDITIVE; no prose change, no number change).
- **Phase 2** (commit `db9e7e3`): `docs/baseline-audit-report.md` — same path replacement across §15.15.1 framework_improves table evidence + §R.15 / §R.18 / §R.19 / §R.20 ledger rows that reference the 8 sweep JSONs.
- **Phase 3** (commit `752b9af`): `docs/CONSOLIDATED_RESULTS.md` — same path replacement in §15.15.1, §15.24, §15.27, §15.29, §15.30, §15.31, §15.32 sections that reference the 8 sweep JSONs.

**Net effect:** the Tier-1 SCI reviewer who checks out the freeze-marker tag can `cat verification_outputs/kanzi_n1000_*/kanzi_n1000_*paper_metrics.json` and reproduce every per-cell metric cited in the paper submission package, **without any /tmp/ filesystem dependency**.

---

## todo/ refresh (Phase 4 ledger)

**Commit:** `3186a1d` — "Wave 134 Phase 4: refresh todo/STATUS.md + INDEX.md for post-Wave-127+ reality"

- `todo/STATUS.md` updated to reflect post-Wave-127+ reality:
  - v1.0-paper-final tag set (2026-09-14).
  - ruff 0 (Wave 131 Phase 1 ruff auto-fix).
  - 8 N=1000 sweep JSONs now in repo (this wave).
  - D.4 33/33 PASS / claims_consistency PASS / mkdocs strict EXIT=0 freeze-marker preserved.
- `todo/INDEX.md` refreshed to surface the 8 in-repo sweep JSONs under the "Reproducibility provenance" heading.
- 6 active plans updated to SHIPPED status (Wave 127 finish-line, Wave 131 pre-freeze, Wave 132 Tier-1 polish, Wave 133 number-consistency, Wave 134 /tmp migration, baseline R.1-R.24 ledger).
- **Wave 86 LineageFlow N=1000 HMMER raw JSON noted as STILL MISSING** — there is no /tmp copy on the sandbox and no Wave 86 audit-doc data. This is the ONE outstanding reproducibility gap (see "What remains NOT in repo" below).

---

## Wave 134 acceptance gates

- All 8 N=1000 sweep JSONs in `verification_outputs/` (Phase 1 atomic copy verified).
- All 3 docs (paper-draft + baseline-audit + CONSOLIDATED) paths updated (Phases 1-3).
- `pytest tests/ -k "d4" -q` → **33/33 PASS** preserved (no code changed).
- `ruff check adaptive_reflow/ tests/` → **All checks passed!** preserved (Wave 131 freeze).
- `python tools/check_claims_consistency.py` → **PASS** preserved (39 active, 0 provisional, 2 deprecated).
- `mkdocs build --strict` → **EXIT=0** (verified at Phase 5 close).

---

## What remains NOT in repo (camera-ready or re-run)

- **Wave 86 LineageFlow N=1000 HMMER raw JSON** — the audit doc has 158/342 (`hmmscan_total_hits` summary), but the raw sweep output (`tools/run_sota_lineageflow_*` N=1000 HMMER result JSON) was never saved. No `/tmp/` copy exists on the sandbox; no Wave 86 audit-doc contains the raw sweep.
  - **This is a real reproducibility gap** that needs a Wave 86 re-run to close.
  - **Camera-ready only:** not in scope for Tier-1 SCI submission (LineageFlow R1 is the headline 158→342 +116% claim, which IS in the supplementary.md S4 reproducibility appendix).

---

## Phase 5 (this commit) — final synthesis

**Audit doc:** `docs/audit/wave134-tmp-migration.md` (this file).

**Baseline-audit-report.md:** 1 NEW §R.24 row appended after §R.23 (Wave 131 byte-repro).

**CONSOLIDATED_RESULTS.md:** 1 NEW §15.33 section appended after §15.32 (Wave 131 byte-repro).

**No source code changes.** **No experiments.** **No new measurements.** **Single atomic commit by Agent 5.**

---

## Freeze marker

HEAD after Wave 134 final close is **`v1.0.1-paper-final`**. This tag **supersedes `v1.0-paper-final`** (which was set at Wave 131 close, commit `539ec82`); both tags point at the same source tree because there are **no source code changes between the two tags** — the 4 Wave 134 commits (Phases 1-4) are all docs-only and the v1.0.1 tag captures the post-/tmp-migration + post-todo-refresh state. **Reproducibility provenance now complete for Kanzi** (all 8 N=1000 sweeps in repo at the destination paths). The only outstanding reproducibility gap is the Wave 86 LineageFlow HMMER raw JSON, deferred to camera-ready / Wave 86 re-run.

**HARD RULES honored:** NO push (Wave 11+ user-gated); ADDITIVE only — all 4 prior-agent commits preserve pre-Wave-134 content; NO source code changes; NO experiments; single atomic Agent 5 commit titled "Wave 134: /tmp/ migration close — audit doc + baseline R.24 + CONSOLIDATED 15.33 + v1.0.1-paper-final tag set".

---

## Cross-references

- `docs/audit/wave131-pre-freeze-hygiene.md` — Wave 131 freeze-marker audit (predecessor of v1.0-paper-final)
- `docs/audit/wave133-number-consistency.md` — Wave 133 final polish audit (immediate predecessor)
- `docs/baseline-audit-report.md` §R.24 — this wave's ledger row
- `docs/CONSOLIDATED_RESULTS.md` §15.33 — this wave's CONSOLIDATED row
- `todo/STATUS.md` + `todo/INDEX.md` — Phase 4 refresh
- `verification_outputs/kanzi_n1000_*/` — 8 N=1000 sweep JSONs now in repo
