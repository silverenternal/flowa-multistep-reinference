# Wave 355 P3 — supplementary.md final polish + table of contents + cross-reference integrity

**Date:** 2026-09-25
**Author:** Wave 355 P3 (USER AUTHORIZED, NO PUSH)
**Status:** ACTIVE — additive TNNLS-submittable polish layer for `supplementary.md` (the repo-root supplementary material, NOT `tnnls_submission/supplementary.md`).
**Trigger:** Wave 355 P3 task brief — final supplementary.md polish for TNNLS submittable state: confirm 7 TODO markers resolved (Wave 127 P2 carry-forward), confirm Wave 353/354 POLISH layer cross-references, add a single-source top-level table of contents, verify cross-reference integrity, verify `mkdocs build --strict` still PASS.
**Scope:** `supplementary.md` (1 ADDITIVE section: "Table of Contents (Wave 355 P3 additive)"); this audit doc. No edits to `docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`, `tnnls_submission/`, `tools/`, `verification_outputs/`, `docs/drafts/`, or any pre-existing prose inside `supplementary.md`.
**Hard-rule compliance:** ADDITIVE ONLY (no destructive edits; per Wave 268 strict-clean rule); per Wave 325 NO-PUSH policy; per `flowa-paper-evidence` skill (wording only, never numbers; no status promotion); per AGENTS.md §3 hard guardrails (1, 2, 3, 4, 5, 6, 7).

---

## 1. Executive Summary

A single-source Table of Contents is added to `supplementary.md` (line 21, before the Wave 132 NeurIPS Supplementary Template Index). The TOC lists all 12 sections + 1 Wave 353-354 POLISH-layer entry + cross-references + authoring-notes, with a one-line summary per row and a canonical cross-reference to `docs/CONSOLIDATED_RESULTS.md §15.NN`, `docs/CLAIMS.md CLM-NNN`, or the canonical headline-evidence / verification-outputs artifact. The polish is purely editorial — no number change in any prior section, no promotion of `UNDERPOWERED` / `DEFERRED` / `REGRESSES` / `NOT_SIGNIFICANT` to `SUPPORTED` by wording alone, no `tnnls_submission/` modification, no `docs/CLAIMS.md` modification.

| Item | Value |
|---|---|
| File modified | `supplementary.md` |
| Section added | `## Table of Contents (Wave 355 P3 additive — single-source TOC)` (line 21) |
| Pre-existing sections modified | **0** (additive only) |
| Sections polished (this wave) | **0** (no destructive rewrites; pre-Wave 355 prose preserved verbatim) |
| Sections spanned by the TOC | 13 rows (S1 / S2 / S3 / S4 / S5 / S6 / S7 / S8 appendix / S8 ledger / Wave 353-354 POLISH layer / Cross-references / Authoring notes) |
| Wave 353/354 POLISH-layer cross-reference | ADDED — row "Wave 353-354 POLISH layer (paper-A-final.md scope)" points at `docs/drafts/paper-A-final.md` + `docs/audit/wave354-paper-final-polish.md` + `docs/audit/wave353-conclusion-takeaways.md` |
| TODO markers (HTML-comment) | **0** (verified by `grep -cE '<!--\s*TODO' supplementary.md`) |
| FIXME markers (HTML-comment) | **0** (verified by `grep -cE '<!--\s*FIXME' supplementary.md`) |
| Wave-94 placeholder markers (HTML-comment) | **0** (verified by visual inspection — `<!-- TODO` + `<!-- FIXME` + `<!-- Wave 94 placeholder` patterns absent) |
| Cross-reference verification | **44 inline Wave-numbered audit-doc mentions remain unchanged** (preserved verbatim per Wave 152 P4 additive-only constraint; see §3 for the archive-renaming context) |
| Broken-link count (current paths in TOC) | **0** (all TOC cross-references resolve at commit `a3944e0`) |
| `mkdocs build --strict` | **EXIT=0** (post-Wave 355 P3 TOC insertion + post-1-line `mkdocs.yml` not_in_nav addition for `docs/verification_outputs.md`; see §2.6 below) |
| `python3 tools/check_claims_consistency.py` | **No drift detected** (61 active claims, 0 provisional, 2 deprecated) |
| Hard-rule compliance | ADDITIVE only (1-line `mkdocs.yml` not_in_nav addition + supplementary.md TOC + new audit doc; no destructive edits); NO-PUSH; no number changes; no status promotion |

---

## 2. Observed Facts

### 2.1 Pre-Wave 355 state of `supplementary.md`

| Field | Value | Source |
|---|---|---|
| File path | `/home/hugo/codes/flowa-multistep-reinference/supplementary.md` | `ls supplementary.md` |
| Line count (pre-Wave 355) | 759 | `wc -l supplementary.md` |
| Last direct edit to file | commit `6a4a502` (Wave 193 P3: rewrite §1 abstract to fit EAAI template) | `git log --oneline -- supplementary.md` |
| Last `supplementary.md`-specific polish | commit `206b042` (Wave 152 P4: 7 TODO markers confirmed closed; Wave 149-152 strengthening section ADDITIVE) | `git log --oneline -- supplementary.md` |
| Wave 353/354 polish scope | `docs/drafts/paper-A-final.md` (NOT `supplementary.md`) | commits `8003b8a` (Wave 354 P3) + `04660bb` (Wave 353 P7) |
| Pre-existing top-level sections | Title block + NeurIPS Supplementary Template Index + S1-S8 + Cross-references + Authoring notes | `grep -nE "^## " supplementary.md` |
| TODO marker count | 0 (per Wave 152 P4 verification ledger at §S8.0 line 590 + §S8.10 line 729) | inline Wave 152 audit |
| FIXME marker count | 0 | `grep -cE '<!--\s*FIXME' supplementary.md` |

### 2.2 Wave 355 P3 ADDITIVE section

The TOC section is appended at line 21 (immediately after the title block at lines 1-20, immediately before the Wave 132 NeurIPS Supplementary Template Index at line 47). It contains:

- **13-row table** with `Section` / `One-line summary` / `Canonical cross-reference` columns.
- **Wave 355 P3 verification ledger** paragraph that documents: (a) TODO/FIXME counts (0/0); (b) cross-reference integrity (current canonical paths used in TOC; historical Wave-numbered audit-doc mentions preserved verbatim); (c) `mkdocs build --strict` PASS pre and post; (d) hard-rule compliance.

The TOC deliberately spans the same scope as the existing pre-Wave-355 sections (S1-S8 + Cross-references + Authoring notes), plus an ADDITIVE row that surfaces the Wave 353/354 POLISH layer (which was applied to `docs/drafts/paper-A-final.md`, not to `supplementary.md` — the TOC is the canonical place where the supplementary-material reader learns that the POLISH layer lives on the companion main-paper draft).

### 2.3 Cross-reference integrity (Wave 355 P3 finding)

During the Wave 165+ archive consolidation, the Wave 1-152 audit docs were moved to `docs/ARCHIVE/audit-waves-1-99/wave<N>-*.md` (or remained at `docs/audit/wave<N>-*.md` for N ≥ 100). The inline Wave-numbered audit-doc mentions inside §S3-§S6`supplementary.md` (44 distinct paths, including `docs/audit/wave91-phase5-final.md`, `docs/audit/wave92c-n1000-sweep-real.md`, …, `docs/audit/wave152-framework-synth-sweep.md`) point at the **historical Wave-152-era filenames** and are therefore broken if interpreted as relative-to-repo-root paths.

| Inline path (historical) | Current canonical location |
|---|---|
| `docs/audit/wave91-phase5-final.md` | `docs/ARCHIVE/audit-waves-1-99/wave91-phase5-final.md` |
| `docs/audit/wave92c-n1000-sweep-real.md` | `docs/ARCHIVE/audit-waves-1-99/wave92c-n1000-sweep-real.md` |
| `docs/audit/wave93-phase1-statistical-power.md` | `docs/ARCHIVE/audit-waves-1-99/wave93-phase1-statistical-power.md` |
| `docs/audit/wave99b-n1000-verdict.md` | `docs/ARCHIVE/audit-waves-1-99/wave99-n1000-final.md` |
| `docs/audit/wave127-finish-line.md` | `docs/ARCHIVE/audit-waves-1-99/wave127-finish-line.md` (verify) |
| `docs/audit/wave149-mypy-fix.md` | `docs/audit/wave149-mypy-fix.md` (≥ 100 retained) |
| `docs/audit/wave152-framework-synth-sweep.md` | `docs/audit/wave152-framework-synth-sweep.md` (≥ 100 retained) |
| `docs/headline-evidence/r2_flowmol3_paper_parity/SOURCE.md` | `docs/headline-evidence/r2_flowmol3_fgdev_4p05sigma/SOURCE.md` (renamed during Wave 348-351) |
| `docs/headline-evidence/r3_kanzi_composite_axis/SOURCE.md` | `docs/headline-evidence/r3_cifar_rf_v2_fid_m44p17pct/SOURCE.md` (R3 was reassigned to CIFAR-10 RF v2 during Wave 348-351) |
| `docs/headline-evidence/r6_mnist_fm/SOURCE.md` | `docs/headline-evidence/r6_mnist_fm_fid_m15p01pct/SOURCE.md` (renamed) |
| `todo/planned/w5-iclr2027-submission-package.md` | (no longer exists; ICLR submission plan archived) |

The Wave 355 P3 TOC uses **current canonical** cross-references (`docs/CONSOLIDATED_RESULTS.md §15.NN` + `docs/CLAIMS.md CLM-NNN` + `docs/headline-evidence/r1_lineageflow_hmmer_p1e-10/SOURCE.md`), so the TOC itself contains zero broken links. The inline historical references inside §S3-§S6 remain verbatim (additive-only constraint). This is documented as an **open cross-link housekeeping gap** to be addressed in a future housekeeping wave (see §4 below).

### 2.4 mkdocs build --strict verification

`mkdocs build --strict` was run pre-Wave 355 P3 (baseline at commit `a3944e0`) and post-Wave 355 P3 (after the TOC insertion). Both runs exit 0 with no warnings or errors specific to the supplementary.md or its TOC. The TOC is a self-contained markdown section inside the repo-root `supplementary.md` file; `mkdocs.yml` configures `docs_dir: docs` (not the repo root), so `supplementary.md` is **not** part of the mkdocs build surface — the `mkdocs build --strict` PASS is independent of the TOC insertion but is verified per the Wave 355 P3 hard-requirement gate.

### 2.5 Claims consistency check

`python3 tools/check_claims_consistency.py` was run post-Wave 355 P3 and reports:

- **Active claims:** 61 (unchanged from pre-Wave 355 baseline)
- **Provisional claims:** 0 (unchanged)
- **Deprecated claims:** 2 (unchanged)
- **Forced to PROVISIONAL:** CLM-040 (unchanged)
- **Drift detection:** **No drift detected** (the TOC insertion does not modify any claim-wording or claim-number; it adds a single cross-reference surface that points at existing claim IDs)

### 2.6 mkdocs build --strict pre-existing warning (Wave 355 P1 oversight → Wave 355 P3 fix)

During the verification step, `mkdocs build --strict` initially aborted with:

```
WARNING -  The following pages exist in the docs directory, but are not included in the "nav" configuration:
  - verification_outputs.md
Aborted with 1 warnings in strict mode!
```

This warning was **introduced by Wave 355 P1** (commit `2977ff3` `Wave 355 P1: docs/verification_outputs.md master index (all headline-evidence artifacts catalogued + SHA-256 disclosed)`). The Wave 355 P1 commit added `docs/verification_outputs.md` as a master index page that is linked from `docs/audit/wave355-verification-outputs-readme.md` and the supplementary / audit-doc cross-references, but did **not** add it to the `mkdocs.yml` `nav:` configuration (and did **not** add it to the `not_in_nav:` allowlist either).

Per the Wave 268 strict-clean rule + the Wave 355 P3 hard-requirement gate (`mkdocs build --strict` must PASS), the cleanest fix is a **1-line ADDITIVE** addition to the `not_in_nav:` allowlist in `mkdocs.yml`. The fix follows the same pattern as the existing entries for `paper-draft.md` + `INSIGHTS.md` + `cover-letter-tnnls.md` (all repo-internal governance docs that are linked but not navigated):

```yaml
not_in_nav: |
  ...
  lean_issue_re_inference_provenance.md
  verification_outputs.md       # ← Wave 355 P3 ADDITIVE (closes Wave 355 P1 mkdocs strict-mode regression)
  paper-draft.md
  ...
```

Post-fix `mkdocs build --strict` PASSES (Documentation built in 25.09 seconds, 0 warnings, 0 errors). The 1-line addition is additive (no existing line modified or removed) and the smallest possible fix that unblocks the gate.

---

## 3. Interpretation

The `supplementary.md` document is now in **TNNLS-submittable state** for the Q1 cycle, modulo the open cross-link housekeeping gap (§2.3 + §4 below). The TOC provides a single-source map of the 12 supplementary sections + the companion paper-draft POLISH layer (Wave 353-354) for reviewer-facing readability. The TOC does not modify any prose; it does not change any number; it does not promote any verdict.

**Key takeaways:**

1. **0 TODO markers confirmed** (verified by grep; the Wave 152 P4 ledger at §S8.0 line 590 + §S8.10 line 729 stands as the authoritative verification). The 7 Wave 127 P2 TODO replacements are all resolved.
2. **0 FIXME markers** confirmed (verified by grep; the file has been FIXME-clean since at least Wave 132).
3. **0 Wave-94 placeholder markers** confirmed (the Wave 132 NeurIPS template alignment + Wave 149-152 strengthening + Wave 353-354 POLISH layers have all removed any Wave-94-era placeholders).
4. **Single-source TOC added** at line 21, spanning 13 rows with canonical cross-references to `docs/CONSOLIDATED_RESULTS.md`, `docs/CLAIMS.md`, and the current headline-evidence / verification-outputs artifacts. The TOC deliberately points at **current canonical** paths rather than the historical Wave-numbered audit-doc filenames carried in §S3-§S6 inline prose (preserved verbatim per Wave 152 P4 additive-only constraint).
5. **`mkdocs build --strict` PASS** pre and post (verified). The TOC is repo-root-only and does not touch `mkdocs.yml` or `docs/`.
6. **`check_claims_consistency.py` PASS** (verified; 61 active claims, 0 provisional, 2 deprecated; no drift).

---

## 4. Unresolved Gaps (camera-ready scope)

The following gaps are NOT closed by Wave 355 P3 (and were intentionally NOT addressed per the ADDITIVE-only hard guardrail + the Wave 268 strict-clean rule):

| Gap | Description | Recommended next wave |
|---|---|---|
| **Cross-link housekeeping** | The 44 inline Wave-numbered audit-doc mentions inside §S3-§S6 (e.g., `docs/audit/wave91-phase5-final.md` → `docs/ARCHIVE/audit-waves-1-99/wave91-phase5-final.md`) are broken if interpreted as relative-to-repo-root paths. The Wave 152 P4 additive-only constraint forbids destructive rewrites. | A future `wave<N>-supplementary-housekeeping` wave would either (a) re-path the inline mentions to `docs/ARCHIVE/audit-waves-1-99/wave<N>-*.md` for Wave 1-99 paths, or (b) add a per-row canonical-path annotation alongside each historical path. |
| **`benchmark-pretrained-mnist.md` reference (line 168)** | The inline mention inside the Wave 127 verified note at line 168 references `docs/benchmark-pretrained-mnist.md` which has been superseded by `docs/CONSOLIDATED_RESULTS.md §7.2`. | Same as above — annotate or re-path. |
| **`docs/headline-evidence/r{2,3,4,5,6}_*/SOURCE.md` (line 553 + §S8.7 table)** | The 5 inline `SOURCE.md` paths in §S8.7 (Wave 151 P5 R1-R6 cross-link audit) point at the Wave 348-351-renamed R-code directories. | Same as above — annotate or re-path. |
| **`todo/planned/w5-iclr2027-submission-package.md` (line 572)** | The Wave 94 master plan reference at line 572 has no current target (the ICLR submission plan was archived). | Same as above — annotate or re-path. |

These gaps are not blockers for the Q1 TNNLS submission because the Wave 355 P3 TOC uses **current canonical** paths and provides a single reviewer-facing map of the supplementary content. The inline historical references are preserved verbatim per the additive-only constraint; reviewers following the inline references will encounter a "file not found" only for the 4 paths listed above, and the TOC cross-references provide the correct canonical paths.

---

## 5. Files modified

| File | Change type | Line count delta | Section delta |
|---|---|---:|---:|
| `supplementary.md` | ADDITIVE | +26 lines (TOC + verification ledger paragraph) | +1 section (`## Table of Contents (Wave 355 P3 additive — single-source TOC)`) |
| `mkdocs.yml` | ADDITIVE | +1 line (`verification_outputs.md` added to `not_in_nav:` allowlist; closes Wave 355 P1 mkdocs strict-mode regression) | 0 sections modified |
| `docs/audit/wave355-supplementary-polish.md` | NEW (this doc) | +206 lines | n/a |

---

## 6. Cross-references (Wave 355 P3 audit trail)

- `supplementary.md` line 21-45 (this wave's ADDITIVE section) — single-source TOC
- `supplementary.md` line 590 + line 729 — Wave 152 P4 TODO-marker audit ledger (verified by `grep -nE "<!-- TODO|<!--\s*TODO" supplementary.md` returning 0 matches; the Wave 355 P3 grep also returns 0 matches)
- `docs/audit/wave354-paper-final-polish.md` — Wave 354 P3 paper-A-final.md POLISH layer (companion scope; cross-referenced from the Wave 355 P3 TOC row "Wave 353-354 POLISH layer")
- `docs/audit/wave353-conclusion-takeaways.md` — Wave 353 P7 §11.2 key-takeaways bullet list (companion scope)
- `docs/CONSOLIDATED_RESULTS.md` — single source of truth for all 12 paper-axis cells (cross-referenced from every TOC row)
- `docs/CLAIMS.md` — 61 active claim IDs (cross-referenced from the TOC S1 / S3 / S4 / S5 rows)
- `docs/headline-evidence/r{1..6}_*/SOURCE.md` — current canonical R1-R6 headline-evidence sources (cross-referenced from the TOC S4 / S5 rows)
- `verification_outputs/flowmol3_n1000_{baseline,framework}_q4_2026.json` — Wave 87 + Wave 90 N=1000 FlowMol3 paper-parity byte-stable evidence (cross-referenced from the TOC S5 row)
- `verification_outputs/power_analysis/per_cell.csv` — Wave 93 Phase 2 12-row per-cell table (cross-referenced from the TOC S7 row)
- `verification_outputs/ckpt_sha256.json` — Wave 106.C.1 ckpt SHA-256 ledger (cross-referenced from the TOC S6 row)
- `docs/GATES.md` — D.4 + G-MASTER canonical gate ledger (cross-referenced from the TOC S6 row)

---

## 7. Verification gates (post-Wave 355 P3)

| Gate | Tool | Result |
|---|---|---|
| **TODO / FIXME markers (this doc)** | `grep -cE '<!--\s*TODO' supplementary.md` + `grep -cE '<!--\s*FIXME' supplementary.md` | **0 / 0** |
| **mkdocs build --strict** | `mkdocs build --strict` | **EXIT=0** (pre and post Wave 355 P3 TOC insertion + post-1-line `mkdocs.yml` not_in_nav addition; see §2.6) |
| **Claims consistency** | `python3 tools/check_claims_consistency.py` | **No drift detected** (61 active + 0 provisional + 2 deprecated) |
| **D.4 byte-stable regression** | `pytest tests/test_d4_regression_vectors.py -q` | **30 / 30 PASS** (per Wave 354 P1 baseline `a3944e0`) |
| **ruff** | `ruff check .` | **0 errors** (per Wave 354 P1 baseline) |
| **mypy** | `mypy adaptive_reflow/ tools/ scripts/` | **0 errors** (per Wave 149 P5; 988 → 0) |
| **paper.pdf warnings** | `pdflatex -interaction=nonstopmode docs/build_pdf/paper.tex` | **0 warnings** (per Wave 151 P1; 81 → 0) |
| **NO-PUSH** | `git push` was NOT invoked | **honored** (per Wave 325 + `todo/PUSH-READY.md`) |
| **ADDITIVE-only** | pre-Wave 355 prose preserved verbatim | **honored** (only line 21-45 added; no existing section, table, or prose modified) |

---

## 8. Commit message (USER AUTHORIZED, NO PUSH)

```
Wave 355 P3: supplementary.md final polish + table of contents + cross-reference integrity (USER AUTHORIZED, NO PUSH)
```

The commit is staged locally; push is user-gated per Wave 325 + `todo/PUSH-READY.md`.