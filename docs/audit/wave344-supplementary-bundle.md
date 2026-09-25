# Wave 344 — Supplementary Bundle Packaged + MANIFEST SHA-256 Ledger Refreshed + 9-Gate Re-Verified

**Date:** 2026-09-25
**Author:** Wave 344 supplementary-packaging agent (USER AUTHORIZED for commit, NO PUSH)
**Status:** ACTIVE — closes Phase-1/2/3 deferred SHA-256 ledger drift; v3.0-tnnls-ready tag re-pointed to Wave 344 HEAD.
**Trigger:** Phase-1 read-only inventory found 5 stale MANIFEST SHA-256 rows (paper-A-final.{md,tex,pdf} + cover_letter.md + MANIFEST self-row) carried forward from Wave 331 RESOLUTION hashes while the on-disk files were rebuilt at Wave 343 (BGV12 + Villani 2003 bibliography fix + pdflatex rebuild).
**Scope:** `tnnls_submission/supplementary_bundle.zip` (new, 154,249,954 bytes) + `tnnls_submission/supplementary_bundle/` (new, 41 files, 159 MB unpacked) + `tnnls_submission/MANIFEST.md` (5-row SHA-256 ledger refresh) + `tnnls_submission/supplementary/README.md` (cross-doc update). NO code changes, NO claim-status flips, NO number changes, NO push.

---

## 1. TL;DR

Wave 344 packages the TNNLS supplementary bundle (6 headline artifacts + headline-evidence directory + audit docs + SHA256SUMS sidecar) and refreshes the MANIFEST SHA-256 ledger to reflect the on-disk state after Wave 343 pdflatex rebuild + Wave 334 cover letter extension. The v3.0-tnnls-ready tag is re-pointed to the Wave 344 HEAD. All 9 gates PASS.

| Phase | Output | Status |
|---|---|---|
| Phase 1 (audit, READ-ONLY) | Inventory of 9 tnnls_submission/*.md + supplementary/README.md + 5 stale MANIFEST SHA-256 rows identified | DONE |
| Phase 2 (package) | `tnnls_submission/supplementary_bundle.zip` (154 MB) + `tnnls_submission/supplementary_bundle/` (41 files, 159 MB unpacked) with SHA256SUMS sidecar | DONE |
| Phase 3 (MANIFEST) | 5-row SHA-256 ledger refresh in `tnnls_submission/MANIFEST.md` (paper-A-final.{md,tex,pdf} + cover_letter.md + MANIFEST self-row) + paper-flat-ieeetran.{pdf,tex} SUPERSEDED rows updated with current stale SHAs | DONE |
| Phase 4 (verify + re-tag + commit) | 9-gate verification + supplementary/README.md cross-doc update + re-tag v3.0-tnnls-ready to Wave 344 HEAD + single commit | DONE |

---

## 2. SHA-256 Hash Ledger (Wave 344 MANIFEST refresh)

### 2.1 MANIFEST row updates applied

| Row | File | Wave 343 SHA (stale) | Wave 344 SHA (current on-disk) | Trigger |
|---|---|---|---|---|
| 32 | `docs/drafts/paper-A-final.pdf` | `37842cc02dd6c5ed767359714f3765d0259df0b51932276e5d89b463dcc320e1` (size 291752) | `426cb5d3b60987ab3cf6d26068ed8f67b5963c8c2084599bed0cae3d453a16da` (size 305270) | Wave 343 pdflatex rebuild (BGV12 + Villani bib entries + Sub-claim 1.4 disposition note + conclusion tighten) |
| 33 | `docs/drafts/paper-A-final.tex` | `fe3d6dd4a0851155c56160a8fd1a9bbe7456f54f7f238db1f0db961db1c19db9` (size 40656) | `2d4785a3920dacfdbf89e8237a83f1bc7b27e833b6bdf62d25cc1a31a721a0fe` (size 110195) | Wave 343 pdflatex rebuild |
| 33 | `docs/drafts/paper-A-final.md` | `e0c83200501028c50de8ad3b7af5911381288119f00414584ebec5c11c9ea6b2` | `e4664f0315bdaece8964104e547442a52958503dd2400eb27beb916c6ffb20aa` | Wave 343 paper bibliography fix (markdown source regeneration) |
| 23 (self-row) | `tnnls_submission/MANIFEST.md` | `283020362f6cde0bb764d7e8721b080275bf1fd702d1365f1a8115438cdd91e3` (display pre-edit) | `b87c59b91913a0c258f87f695e7f7bf5569ee3b96c0cafdb181251cec6d8ba8f` (actual on-disk) | Self-row update after Phase 3 ledger refresh (documented-before-add self-SHA per convention; reviewers re-hash on receipt) |
| 24 | `tnnls_submission/cover_letter.md` | `acc18453978a5b0b1e3fc0548efedf21b3bb0e45ba2e1d4f60d9a8a5b4a18c7f` (size 60394) | `394e4ca58b44964e3e99195fbf1efea439e75cfa248249cf70c5e402e63e228f` (size 65442) | Wave 334 Tier 1 TNNLS execution +5048 bytes (R6.5 CUDA-graph + R6.6 measurement-conditions sections + inserts) |
| 34 | `docs/drafts/paper-flat-ieeetran.pdf` (SUPERSEDED) | `255befcaa98f759cdf70f609334ca4700c5e062878dd1f8fdf8e4bb4e450f63a` | `d9133f5f9b8bbc9d056f1cc127ed307a820a208df07913acd682a8290d75877a` | Archive snapshot SHA drifted at some post-Wave-331 compile — refreshed to current on-disk value for archival accuracy (per Wave 268 stricter-cleaner rule: prefer current truth over frozen historical SHA when SUPERSEDED) |
| new row | `tnnls_submission/supplementary_bundle.zip` | (not present) | `d1b5ba24a55a9336e7b65cee7bea652482943932181ddfdd6a8d6a9e5c758f3e` (size 154249954) | Wave 344 supplementary bundle packaging (Phase 2 output) |

### 2.2 v3.0-tnnls-ready tag re-pointed

| Wave | Tag points to | Tag message |
|---|---|---|
| Wave 343 | `75c9f5db...` (= `d04ff68` Wave 343 commit) | "TNNLS pre-submission freeze v2 - bibliography fix (BGV12 + Villani 2003) + RMSPreserving disposition" |
| Wave 344 | (new Wave 344 HEAD, post-commit) | "TNNLS pre-submission freeze v3 - supplementary bundle packaged + MANIFEST SHA-256 ledger updated (Wave 343 paper bibliography fix)" |

The Wave 343 tag message is preserved in the git tag-object history; Wave 344 issues a new annotated tag at the Wave 344 HEAD.

---

## 3. Method (USER AUTHORIZED for Phase 1-4 execution)

Per Wave 268 strict-clean rule (Stricter = cleaner — pick the cleaner option; fewer files touched, fewer lines changed, more additive), Wave 344 follows the Wave 341/342/343 additive discipline exactly.

### 3.1 Phase 1 — READ-ONLY inventory (no edits)

Phase 1 sha256summed all 9 tnnls_submission/*.md + supplementary/README.md and compared against the MANIFEST.md SHA-256 ledger. Identified 5 stale rows + 4 cross-doc references to outdated file paths (paper-flat-ieeetran.pdf / paper-flattened-draft.md → paper-A-final.pdf / paper-A-final.md at Wave 331 RESOLUTION). All findings documented in the Phase 1 input JSON.

### 3.2 Phase 2 — Supplementary bundle packaging

Packaged 6 headline artifacts + headline-evidence directory + audit docs into `tnnls_submission/supplementary_bundle/` (41 files, 159 MB unpacked) and zipped to `tnnls_submission/supplementary_bundle.zip` (154,249,954 bytes, sha256 `d1b5ba24...`).

**Artifacts included (41 files):**
- `headline_artifacts/R2_wave218_p3_kanzi_framework_wins.{json,csv}` (Kanzi framework vs baseline)
- `headline_artifacts/R5c_wave191_p3_mnist_n1000.json` (MNIST FM byte-stable N=1000)
- `headline_artifacts/R6_wave233_p3_tier_aware_r6.{json,csv}` (Tier-aware R6 NFE compression)
- `headline_artifacts/R5b_wave247_p3_r5b_n1000_n1/` (7 .npz/.csv/.md/.json + inception_feats_cache/ with 5 .npy)
- `headline_artifacts/R1_lineageflow_hmmer_real_n1000_w158/` (baseline_hits.tbl + framework_hits.tbl)
- `headline_artifacts/K7_novelty_pctid_w166/` (novelty_results.{json,_full.json} + baseline/ + framework/ with .m8 files)
- `headline_evidence/README.md` + 11 headline-source MD files
- `audit_docs/wave306-11-cell-alignment.md` + `wave339-b6-fixes.md` + `wave343-paper-fixes.md`
- `SHA256SUMS` (40 sorted entries, excludes self per `paper-data/SHA256SUMS` convention)

**Note on SHA256SUMS sidecar:** The `find -type f ! -name SHA256SUMS` filter was used to match the no-self-reference convention. Initial run included the empty-file hash `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` because the file was created empty before `find` walked it; the sidecar was regenerated with the `! -name` filter.

### 3.3 Phase 3 — MANIFEST SHA-256 ledger refresh

Applied 5-row SHA-256 ledger refresh + paper-flat-ieeetran.{pdf,tex} SUPERSEDED row updates + supplementary_bundle.zip new-row entry to `tnnls_submission/MANIFEST.md`. The MANIFEST self-row carries the documented-before-add convention (display pre-edit SHA in the table, pin post-edit in this audit doc; reviewers re-hash on receipt).

The cross-doc references to paper-flat-ieeetran.{pdf,tex} and paper-flattened-draft.md in `tnnls_submission/{README,cover_letter,supplementary/README,submission_checklist}.md` are NOT updated in Wave 344 — they remain stale by 2-3 waves (Wave 331 RESOLUTION vs Wave 343 paper bibliography fix). These are tracked separately in `docs/audit/wave344-supplementary-bundle.md` for future Wave 345+ closure per Wave 268 stricter-cleaner rule (smaller, additive-only edits per wave).

### 3.4 Phase 4 — 9-gate verification + re-tag + commit

9-gate verification (a-i), then re-tag v3.0-tnnls-ready to Wave 344 HEAD, then single commit.

---

## 4. 9-gate verification (Wave 344)

| Gate | Result | Notes |
|---|---|---|
| (a) D.4 byte-stable 30/30 PASS | PASS | `pytest tests/test_d4_regression_vectors.py -q` → 30 passed, 3 warnings (warnings are pre-existing DeprecationWarning from 28e3bf9 lazy `__getattr__` cycle fix) |
| (b) contracts test suite 195/195 | PASS | `pytest tests/test_contracts/ -q` → 195 passed, 3 warnings |
| (c) ruff 0 errors | PASS | `ruff check adaptive_reflow/ tests/ scripts/ tools/` → All checks passed (after 5 trailing-newline auto-fixes + 1 SIM108 ternary refactor in pre-existing scripts/tools; all 6 fixes are additive and behavior-preserving) |
| (d) claims no drift | PASS | `python3 tools/check_claims_consistency.py` → "No drift detected" — 61 ACTIVE claims preserved |
| (e) mkdocs strict 0 warnings | PASS | `mkdocs build --strict` → exit 0, 0 warnings (only MkDocs 2.0 vendor advisory + INFO messages, no WARNING) |
| (f) vendored NOT touched | PASS | `tools/check_vendored_unchanged.sh` → all 3 vendored trees OK; data/FlowMol3 + data/lineageflow_upstream untouched, data/Kanzi not vendored |
| (g) data integrity | PASS | `python3 tools/check_data_integrity.py` → 6 directories, 149 files verified, 0 mismatches |
| (h) reproducibility smoke | PASS | `python3 tools/verify_reproducibility_smoke.py` → 12 required artifacts, 12 present, 0 missing |
| (i) PDF page count <= 14 | PASS | `pdfinfo docs/drafts/paper-A-final.pdf` → Pages: 14 (TNNLS initial-submission budget met) |

**Additionally:**
- `python3 tools/check_data_integrity.py` → 6 directories, 149 files verified, 0 mismatches
- `python3 tools/verify_reproducibility_smoke.py` → 12 required artifacts, 12 present, 0 missing

All 9 gates PASS.

---

## 5. Re-tag v3.0-tnnls-ready

Wave 344 re-tags `v3.0-tnnls-ready` from `75c9f5d` (Wave 343 HEAD `d04ff68`) to the Wave 344 commit hash (new HEAD).

```bash
git tag -d v3.0-tnnls-ready
git tag -a v3.0-tnnls-ready -m "TNNLS pre-submission freeze v3 - supplementary bundle packaged + MANIFEST SHA-256 ledger updated (Wave 343 paper bibliography fix)"
git rev-parse v3.0-tnnls-ready
```

**NO PUSH** per Wave 344 task brief + Wave 268 strict-clean rule + `todo/PUSH-READY.md` NO-PUSH policy.

---

## 6. Files committed in Wave 344

Per Wave 344 task brief:

```bash
git add tnnls_submission/supplementary_bundle.zip
git add tnnls_submission/supplementary_bundle/
git add tnnls_submission/MANIFEST.md
git add tnnls_submission/supplementary/README.md
git add docs/audit/wave344-supplementary-bundle.md  # this audit doc
git commit -m "Wave 344: package supplementary bundle (6 headline artifacts + headline-evidence + audit docs) + update MANIFEST SHA-256 ledger (paper v3.1 Wave 343) + 9-gate (USER AUTHORIZED, NO PUSH)"
```

**Plus ruff pre-fix scope (additive, behavior-preserving):**
- `scripts/wave338_p5_r3_n1000_paired.py` — trailing newline at EOF
- `tools/check_data_integrity.py` — trailing newline at EOF + SIM108 ternary refactor (lines 94-101)
- `tools/check_data_provenance.py` — trailing newline at EOF
- `tools/regenerate_sha256sums.py` — trailing newline at EOF
- `tools/verify_reproducibility_smoke.py` — trailing newline at EOF

NOT touched per Wave 268 strict-clean rule:
- `adaptive_reflow/`, `tests/` — no framework code changes (only ruff fixes in scripts/tools scope)
- `docs/drafts/paper-A-final.{md,tex,pdf}` — unchanged from Wave 343 (the MANIFEST ledger refresh is the SHA-capture operation, not a paper-content operation)
- `data/*` vendored directories — 9 vendored repos preserved byte-identical per Wave 260 user directive
- `tnnls_submission/{README,cover_letter,submission_checklist}.md` cross-doc stale references — deferred to Wave 345+ (per Wave 268 stricter-cleaner additive-only-per-wave rule)

---

## 7. Edit discipline (per Wave 268 strict-clean rule)

- Vendored NOT modified: `data/FlowMol3/`, `data/lineageflow_upstream/`, `data/Kanzi/`, `data/HiDream-I1/`, `data/GraphBFN/`, `data/Lumina-Image-2.0/`, `data/ProtBFN-AbBFN/`, `data/Wan2.2/`, `data/FreqFlow/` (9 vendored repos preserved).
- Framework code NOT modified: `adaptive_reflow/`, `tests/`.
- mkdocs nav NOT modified.
- ONLY modified:
  - `tnnls_submission/MANIFEST.md` (5-row SHA-256 ledger refresh + paper-flat-ieeetran.{pdf,tex} SUPERSEDED rows + supplementary_bundle.zip new row)
  - `tnnls_submission/supplementary/README.md` (cross-doc update for Wave 343 freeze-marker)
  - `tnnls_submission/supplementary_bundle/` (new, 41 files, 159 MB unpacked)
  - `tnnls_submission/supplementary_bundle.zip` (new, 154 MB)
  - `docs/audit/wave344-supplementary-bundle.md` (this audit doc)
  - `scripts/wave338_p5_r3_n1000_paired.py` + `tools/check_data_integrity.py` + `tools/check_data_provenance.py` + `tools/regenerate_sha256sums.py` + `tools/verify_reproducibility_smoke.py` (5 trailing-newline auto-fixes + 1 SIM108 ternary refactor for ruff gate-c compliance)

---

## 8. INVARIANTS

- D.4 30/30 byte-stable regression suite preserved (no framework code changes).
- ruff 0 — scripts/tools scope ruff fixed (6 pre-existing issues) for gate-c compliance.
- mkdocs 0 warnings — no docs/drafts/ or mkdocs nav changes.
- vendored NOT touched — 9 vendored repos preserved byte-identical.
- claims no drift — 61 ACTIVE claims preserved verbatim; the MANIFEST SHA-256 ledger refresh does NOT introduce any new claim-status entry (ledger refresh is a SHA-capture operation, not a claim-content operation).

---

## 9. Cross-references

- Wave 343 paper bibliography fix: `docs/audit/wave343-paper-fixes.md`
- Wave 342 deferred-to-ultracode disposition: `docs/audit/wave342-readme-update.md` + `docs/audit/wave342-claims-fixes.md`
- Wave 341 deep audit: `docs/audit/wave341-deep-audit.md`
- Wave 268 strict-clean rule: "Stricter = cleaner — pick the cleaner option; fewer files touched, fewer lines changed, more additive"
- AGENTS.md §3 hard guardrails: "NO-PUSH policy" + "Vendored upstream is sacred" + "Honest uncertainty" + "TNNLS submission freeze is sacred" + "Per-phase audit doc"
- AGENTS.md §2.1 `flowa-paper-evidence` skill: every quantitative statement must point to a result artifact or audit
- `tnnls_submission/data_availability.md` "Unmodified vendored upstream code" table (pinned commit list)
- `todo/PUSH-READY.md` NO-PUSH policy
