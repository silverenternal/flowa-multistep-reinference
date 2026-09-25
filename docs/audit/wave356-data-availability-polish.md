# Wave 356 P2 — tnnls_submission/data_availability.md final polish (9 vendored repos table + reproduction instructions)

**Date:** 2026-09-25
**Wave:** 356
**Phase:** P2
**Status:** ACTIVE — additive TNNLS-submittable polish layer for `tnnls_submission/data_availability.md`.
**Trigger:** Wave 356 P2 task brief — final `data_availability.md` polish for TNNLS submittable state: confirm 9 vendored repos table (FlowMol3 / LineageFlow / Kanzi / HiDream-I1 / GraphBFN / Lumina-Image-2.0 / ProtBFN-AbBFN / Wan2.2 / FreqFlow) is present, Wave 260 user-directive preservation is intact, SHA-256 pinning statement exists; ADD a 4-step Reproduction Instructions section cross-referenced to `reproduce/*.sh`; APPEND a Wave 343-355 supporting audit documents section; refresh `tnnls_submission/MANIFEST.md` SHA-256 column.
**Scope:** `tnnls_submission/data_availability.md` (3 ADDITIVE sections — `## Upstream vendored repositories — pinned commits (Wave 356 P2 additive — 2026-09-25)`, `## Reproduction instructions (Wave 356 P2 additive — 2026-09-25)`, `## Supporting audit documents (Wave 343-355; Wave 356 P2 additive — 2026-09-25)`) + this audit doc + 1-line `tnnls_submission/MANIFEST.md` SHA-256 column refresh for the `data_availability.md` row.
**Hard-rule compliance:** ADDITIVE ONLY (no destructive edits to pre-existing prose inside `data_availability.md`; per Wave 268 strict-clean rule); per Wave 325 NO-PUSH policy; per `flowa-paper-evidence` skill (wording only, never numbers; no status promotion); per AGENTS.md §3 hard guardrails (1, 2, 3, 4, 5, 6, 7); vendored upstream code preserved byte-identical to pinned commits (rows 1–9 below).

---

## 1. Executive Summary

`data_availability.md` is now TNNLS-submittable with a complete evidence trail: a 9-row "Upstream vendored repositories — pinned commits" table (8 git-vendored + 1 tarball-vendored), a 4-step "Reproduction instructions" section cross-referenced to `reproduce/0[1-7]_*.sh` + `reproduce/verify_all_headlines.sh`, and a "Supporting audit documents (Wave 343-355)" cross-reference list (35+ audit docs). The MANIFEST.md SHA-256 column for the `data_availability.md` row was refreshed to the post-Wave-356 P2 value. No pre-existing prose was destructively rewritten; no vendored code was modified; no number in any headline table changed; no status label was promoted (e.g. `UNDERPOWERED` / `DEFERRED` / `REGRESSES` / `NOT_SIGNIFICANT` → `SUPPORTED`).

| Item | Value |
|---|---|
| File modified | `tnnls_submission/data_availability.md` |
| Sections added (this wave, additive) | **3** (§8 `## Upstream vendored repositories — pinned commits (Wave 356 P2 additive — 2026-09-25)` + §9 `## Reproduction instructions (Wave 356 P2 additive — 2026-09-25)` + §10 `## Supporting audit documents (Wave 343-355; Wave 356 P2 additive — 2026-09-25)`) |
| Pre-existing sections modified | **0** (additive only — all 7 prior sections preserved verbatim) |
| Sections preserved byte-identically | **7** (Code availability, Data availability — Per-record CSVs, 4-arm H2H, Statistical methods, Engineering gates; Checkpoint availability; Theorem 1 source paper; Honesty disclosure — incomplete / partial data; Cross-references prior to §8/§9/§10) |
| Vendored repos pinned in new §8 table | **9** (FlowMol3, LineageFlow, Kanzi, HiDream-I1, GraphBFN, Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow) |
| Vendored repos git-vendored | **8** (rows 1–8: git clone at upstream commit hash) |
| Vendored repos tarball-vendored | **1** (row 9 FreqFlow: SHA-256-pinned per `data/freqflow_ckpt/SHA256SUMS`) |
| Vendored files modified during verification | **0** (read-only `git log -1 --format='%H'` + SHA-256SUMS inspection only; no checkout updated, no file written) |
| Reproduction steps documented in §9 | **4** (1. activate sidecar venv; 2. install (reviewer-side idempotent); 3. reproduce per-cell via `reproduce/0[1-7]_*.sh`; 4. verify all 7 R-level headlines via `reproduce/verify_all_headlines.sh` + 6 engineering gate commands) |
| `reproduce/*.sh` cross-references | **8** (7 per-cell scripts + 1 master verifier) |
| Wave 349-355 audit docs cross-referenced in §10 | **35+** (Wave 343: 1, Wave 345: 1, Wave 348: 1, Wave 349: 3, Wave 350: 4, Wave 351: 4, Wave 352: 7, Wave 353: 8, Wave 354: 5, Wave 355: 5, Wave 356: 1 — this doc) |
| `MANIFEST.md` SHA-256 row updated | **1** (`data_availability.md` row: size `10035` → `20866`; SHA `eb410e1f...2692` → `86127df70c...c979`) |
| `MANIFEST.md` post-edit audit pin list appended | **1** (+ `docs/audit/wave356-data-availability-polish.md`) |
| Wave 260 user directive preservation | PRESERVED verbatim in the §"Unmodified vendored upstream code" pre-existing section (line 16-58) — 8 reverted files table intact |
| Wave 260 SHA-256 pinning statement | PRESERVED verbatim — no change to bytewise-identical-to-upstream language |
| Wave 121-273 12-decimal-CLAIMS-table audit-trail format | APPLIED — this audit doc mirrors the §9 "interpretation" + §"observed facts" pattern from Wave 121-273 |
| `python3 tools/check_claims_consistency.py` | No drift detected (no `docs/CLAIMS.md` touch) |
| `mkdocs build --strict` | Not run (no `mkdocs.yml` or `docs/` touch beyond this audit doc; `data_availability.md` is referenced from `tnnls_submission/`, not from `docs/`) |
| Hard-rule compliance | ADDITIVE only (3 sections appended + MANIFEST.md SHA refresh + new audit doc; no destructive edits); NO-PUSH; no number changes; no status promotion; vendored upstream untouched |

---

## 2. Observed Facts

### 2.1 Pre-Wave-356 state of `data_availability.md`

| Field | Value | Source |
|---|---|---|
| File path | `/home/hugo/codes/flowa-multistep-reinference/tnnls_submission/data_availability.md` | `ls tnnls_submission/` |
| Pre-Wave-356 line count | 134 | `wc -l data_availability.md` (pre-edit) |
| Pre-Wave-356 byte count | 10035 | `wc -c data_availability.md` (pre-edit) |
| Pre-Wave-356 SHA-256 | `eb410e1fd8a60b6f93d9e2dd7ba391c9a3b31e7ff79d64afbdfde52f70de2692` | `sha256sum data_availability.md` (pre-edit) |
| Last direct edit to file (pre-Wave-356) | commit `4af95da` (Wave 260 P1: `flowmol/analysis/metrics.py` revert) / commit `8f0255d` (Wave 262 P1: 8-file revert) | `git log --oneline -- tnnls_submission/data_availability.md` |
| Pre-existing top-level sections | Code availability + Data availability (+4 subsections) + Checkpoint availability + Theorem 1 source paper + Honesty disclosure + Cross-references | `grep -nE "^## " data_availability.md` |
| Pre-existing 9-file reverted-table | rows 1–9 (FlowMol3 4 files + LineageFlow 5 files) preserved verbatim | `grep -nE "^\\| [0-9]+ \\|" data_availability.md` (rows 1–9) |
| Pre-existing Wave 260 user directive preservation | "per user academic-integrity directive (2026-09-22)" preserved verbatim | `grep -nE "user academic-integrity directive" data_availability.md` |
| Pre-existing SHA-256 pinning statement | "bytewise identical to their upstream commit hash" preserved verbatim | `grep -nE "bytewise identical" data_availability.md` |
| Vendored 9-repo table (pre-Wave-356) | **NOT PRESENT** (the §"Unmodified vendored upstream code" subsection names 9 repos in prose but does not have a 9-row pinned-commit table) | `grep -nE "FlowMol3.*LineageFlow.*Kanzi.*HiDream" data_availability.md` |
| Reproduction instructions section (pre-Wave-356) | **NOT PRESENT** | `grep -nE "Reproduction instructions" data_availability.md` (pre-edit match count = 0) |
| Wave 349-355 audit docs cross-reference (pre-Wave-356) | **NOT PRESENT** in dedicated section (only `wave{235,236,238}-*.md` are mentioned in the `Cross-references` section) | `grep -nE "wave(349|35[0-5])" data_availability.md` (pre-edit match count = 0) |

### 2.2 Wave 356 P2 additive sections (§8 + §9 + §10)

| # | Section | Lines added | Cross-references | Key content |
|---|---------|-------------|------------------|-------------|
| §8 | `## Upstream vendored repositories — pinned commits (Wave 356 P2 additive — 2026-09-25)` | ~25 lines | `data/`, `data/FlowMol3/repo`, `data/lineageflow_upstream`, `data/kanzi_upstream`, `data/hidream_i1/weights`, `data/graphbfn/repo`, `data/lumina_image_2_0/repo`, `data/protbfn_abbfn/repo`, `data/wan2_2/repo`, `data/freqflow_ckpt/{upstream,SHA256SUMS}`, [`docs/CLAIMS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md) (CLM-056 FreqFlow disclosure), [`docs/audit/wave262-p2-verify.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave262-p2-verify.md) | 9-row table with full SHA-256 + git commit message + vendor mode column; honest-uncertainty disclosure for tarball-vendored FreqFlow (row 9); pre-Wave-262 byte-identical verification cross-reference |
| §9 | `## Reproduction instructions (Wave 356 P2 additive — 2026-09-25)` | ~30 lines | [`docs/environments.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/environments.md), `reproduce/0[1-7]_*.sh` (7 per-cell scripts), `reproduce/verify_all_headlines.sh` (master verifier), `tests/test_d4_regression_vectors.py`, `ruff check`, `mkdocs build --strict`, `tools/check_claims_consistency.py`, [`docs/audit/wave{086,235,236}-*.md`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/audit) | 4 ordered steps (activate sidecar venv; install; reproduce per-cell; verify all 7 + 6 engineering gates); out-of-scope cells (K4/K5/K6) honestly disclosed |
| §10 | `## Supporting audit documents (Wave 343-355; Wave 356 P2 additive — 2026-09-25)` | ~22 lines | Wave 343 + 345 + 348 + 349 + 350 + 351 + 352 + 353 + 354 + 355 audit doc links; [`docs/verification_outputs.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/verification_outputs.md) (Wave 355 P1 master index); this audit doc | Wave-by-wave enumeration of 35+ supporting audit docs |

### 2.3 Pinned upstream commit hashes (read-only verification)

All 9 vendored upstream commit hashes were verified by running
`git -C data/<repo>/<path> log -1 --format='%H %s' 2>/dev/null`
(or `cat data/freqflow_ckpt/SHA256SUMS | head -3` for tarball mode)
**read-only** on 2026-09-25. No vendored file was modified during this
verification (git status `data/` clean per Wave 262 P2 baseline).

| # | Repository | Verified commit SHA | Short SHA | Commit message | Source command |
|---|------------|---------------------|-----------|----------------|----------------|
| 1 | FlowMol3 | `77cae22174b7792b0e25e9e0414038420736d841` | `77cae22` | Update readme.md | `git -C data/FlowMol3/repo log -1 --format='%H %s'` |
| 2 | LineageFlow | `ccef84adff421fcb6b855285bc1860e1f9a94f59` | `ccef84a` | Prepare LineageFlow public release | `git -C data/lineageflow_upstream log -1 --format='%H %s'` |
| 3 | Kanzi | `cfed9cf4be06a98bd2ce5f8492e20c0b9fa0d41b` | `cfed9cf` | add nano banana strip | `git -C data/kanzi_upstream log -1 --format='%H %s'` |
| 4 | HiDream-I1 | `8ccbbfb270ccdae26d6bb0081df67dc81e4033bf` | `8ccbbfb` | Update README.md | `git -C data/hidream_i1/weights log -1 --format='%H %s'` |
| 5 | GraphBFN | `a36ce07d680a3299b56d2e1436917c30b9817fc0` | `a36ce07` | Initial commit | `git -C data/graphbfn/repo log -1 --format='%H %s'` |
| 6 | Lumina-Image-2.0 | `4a4d6f856115db07e8ae127280ebcc3d9f65004e` | `4a4d6f8` | Update README.md | `git -C data/lumina_image_2_0/repo log -1 --format='%H %s'` |
| 7 | ProtBFN-AbBFN | `869a9afb2c0167b2d5a35b07867220da9732ef43` | `869a9af` | Update README.md | `git -C data/protbfn_abbfn/repo log -1 --format='%H %s'` |
| 8 | Wan2.2 | `42bf4cfaa384bc21833865abc2f9e6c0e67233dc` | `42bf4cf` | fix readme | `git -C data/wan2_2/repo log -1 --format='%H %s'` |
| 9 | FreqFlow | (tarball, no git) | (n/a) | (n/a — SHA-256SUMS pinned per `data/freqflow_ckpt/SHA256SUMS`) | `head -3 data/freqflow_ckpt/SHA256SUMS` |

The 8 git-vendored commit SHAs above match the Wave 260 / Wave 262
P1 reverted-file commit references (`77cae22` for FlowMol3 + `ccef84a`
for LineageFlow) AND extend them to all 9 repos. The HiDream-I1 + GraphBFN +
Lumina-Image-2.0 + ProtBFN-AbBFN + Wan2.2 commits are new pins (rows
4–8) — these repos were cloned at their initial-commit or repo-mirror
state during Wave 36 PHASE-4 prep. The FreqFlow row (9) is honestly
disclosed as tarball-vendored because no public git release exists
per [CLM-056](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CLAIMS.md).

### 2.4 `MANIFEST.md` SHA-256 column refresh

| Field | Pre-Wave-356 P2 value | Post-Wave-356 P2 value | Delta |
|---|---|---|---|
| `data_availability.md` row size (bytes) | 10035 | 20866 | +10831 |
| `data_availability.md` row SHA-256 | `eb410e1fd8a60b6f93d9e2dd7ba391c9a3b31e7ff79d64afbdfde52f70de2692` | `86127df70c02c5890b1a8f74fc29cbc3c89c3342427d0478f42a36ab0642c979` | refreshed |
| `data_availability.md` row role column | "Data availability statement + Zenodo DOI references + per-record CSV provenance — **Wave 348 Phase 1b cross-doc fix**: 24 local repo paths → GitHub URLs" | ...same prefix + " + **Wave 356 P2 final polish**: 9 vendored upstream repos table ... + 4-step Reproduction Instructions section ... + Wave 343-355 supporting audit docs cross-reference ... + Wave 260 user-directive preservation note (audit at [`docs/audit/wave356-data-availability-polish.md`](...))" | appended |
| `MANIFEST.md` self-row post-edit audit pin list | ends at `+ docs/audit/wave356-highlights-polish.md` | ...same prefix + `+ docs/audit/wave356-data-availability-polish.md` | appended |

The `MANIFEST.md` row refresh is the standard SHA-256 column
regeneration per the AGENTS.md hard-rule ("When you change
`tnnls_submission/*`, update the SHA-256 column in
`tnnls_submission/MANIFEST.md`"). The self-row of MANIFEST.md is
managed by separate SHA-refresh waves (e.g. Wave 355 P-final); this
wave appended only the `wave356-data-availability-polish.md` entry to
the post-edit audit pin list (ADDITIVE: 1 line, no destructive edit).

---

## 3. Interpretation

### 3.1 What this polish achieves

The Wave 356 P2 polish closes three audit-trail gaps in
`data_availability.md` that were inherited from the pre-Wave-356 state:

1. **9 vendored repos table (NEW).** The pre-Wave-356 §"Unmodified
   vendored upstream code" subsection already named the 9 repos
   (FlowMol3 + LineageFlow + Kanzi + HiDream-I1 + GraphBFN + Lumina-Image-2.0
   + ProtBFN-AbBFN + Wan2.2 + FreqFlow) and listed the 9 reverted files
   for FlowMol3 + LineageFlow (the only 2 repos whose files were
   actually patched-and-reverted during Wave 260 + Wave 262). But it
   did NOT have a row-per-repo pinned-commit table for all 9 repos.
   Reviewers reading the §"Unmodified vendored upstream code"
   subsection could not pinpoint the upstream commit hash for
   HiDream-I1 / GraphBFN / Lumina-Image-2.0 / ProtBFN-AbBFN / Wan2.2 /
   FreqFlow without checking `data/` manually. The new §8 table closes
   that gap with a 9-row table including the full commit SHA + commit
   message + vendor mode for each repo.

2. **Reproduction instructions (NEW).** The pre-Wave-356 §"Data
   availability" subsection told reviewers where the per-record CSVs
   lived but did NOT tell them how to re-run the headline experiments.
   The new §9 section provides a 4-step review path: (1) activate the
   appropriate sidecar venv per `docs/environments.md`; (2) install
   the framework + per-model deps; (3) reproduce per-cell via
   `reproduce/0[1-7]_*.sh`; (4) verify all 7 R-level headlines via
   `reproduce/verify_all_headlines.sh` + 6 engineering-gate commands.
   Each `reproduce/*.sh` script is a one-click verifier that reads the
   byte-stable `verification_outputs/<cell>/` artifact and prints
   "OK" / "FAIL" against the pinned headline; full live-sweep
   re-execution is commented out by default (cells range from 30 min
   GPU to 50 h CPU). This is the canonical reviewer-side reproduction
   path and was previously inlined only into the per-cell SOURCE.md
   provenance + supplementary bundle.

3. **Supporting audit documents (NEW).** The pre-Wave-356 §"Cross-references"
   subsection cited only Wave 235-238 audit docs (the original
   statistical-validation wave). It did NOT cite the 35+ Wave 343-355
   audit docs that constitute the Wave 343 + Wave 344 freeze-marker
   evidence chain + Wave 348 Phase 1b cross-doc fix + Wave 353
   paper-polish layer + Wave 354 cover-letter scaffold + Wave 355
   SHA-refresh + verification-outputs README. The new §10 section
   enumerates these by wave so reviewers can navigate the audit trail
   from the data availability statement.

### 3.2 Why ADDITIVE only

Per Wave 268 ("stricter = cleaner" rule, "do the cleanest thing") +
AGENTS.md §3.2 ("No destructive edits. Additive is the rule. If a fix
is destructive, do it as: (a) ADDITIVE paragraph first; (b) the
destructive edit; (c) update the audit trail") + the Wave 356 P2 task
brief explicit instruction ("ADDITIVE only (append reproduction
instructions; do not modify existing content)"):

- **§8 + §9 + §10 are appended AFTER the existing `## Cross-references`
  section** (the very last pre-Wave-356 section). No pre-existing
  prose was rewritten.
- **MANIFEST.md `data_availability.md` row update** modifies the row's
  SHA-256 + size + role-column suffix. The pre-Wave-348 role-column
  prefix (cross-doc fix description) is preserved verbatim; the Wave
  356 P2 suffix is appended.
- **MANIFEST.md self-row audit pin list** gets 1 additive entry
  (`+ docs/audit/wave356-data-availability-polish.md` appended after
  `+ docs/audit/wave356-highlights-polish.md`). Displayed self-SHA is
  not changed (managed by separate Wave-355-style SHA-refresh waves).
- **No `docs/CLAIMS.md` touch** — claims consistency check passes
  because no claim was added, modified, or status-promoted.
- **No `data/` touch** — vendored upstream is byte-identical to pinned
  commits (verified by the read-only `git log -1` commands in §2.3).
- **No `docs/drafts/paper-A-final.*` touch** — manuscript, .tex, .pdf,
  .aux, .log, .out are pre-existing-modified by other waves.

### 3.3 Hard-rule compliance audit

| Guardrail | Compliance | Evidence |
|---|---|---|
| §3.1 Vendored upstream is sacred | YES | All 9 vendored repos verified read-only; no vendored file modified |
| §3.2 No destructive edits | YES | 3 ADDITIVE sections appended; pre-existing 7 sections preserved byte-identically |
| §3.3 NO-PUSH policy | YES | No `git push` invocation; commit-only |
| §3.4 Honest uncertainty | YES | No status promotion; FreqFlow tarball vendoring honestly disclosed; K4/K5/K6 out-of-scope status disclosed |
| §3.5 TNNLS submission freeze | YES | `data_availability.md` is additive-only; pre-Wave-356 numerics byte-identical |
| §3.6 Per-phase audit doc | YES | This doc mirrors the 12-decimal-CLAIMS-table pattern from Wave 121-273 (observed facts / interpretation / unresolved gaps) |
| §3.7 Stricter = cleaner | YES | 3 additive sections appended; no destructive rewrites; vendored only read |
| `flowa-paper-evidence` hard-requirement #1 | YES | `check_claims_consistency.py` runs without drift |
| `flowa-paper-evidence` hard-requirement #2 | n/a | No `mkdocs.yml` or `docs/` source touched (`data_availability.md` is in `tnnls_submission/`, not in `docs/`) |
| `flowa-paper-evidence` hard-requirement #3 | YES | No `*.py` touched |

### 3.4 Why "data_availability now submittable"

The `data_availability.md` was already submittable before Wave 356 P2
(per the Wave 343 freeze-marker). Wave 356 P2 adds:

- A canonical 9-repo pinned-commit table (rows 4–8 — HiDream-I1,
  GraphBFN, Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2 — were NOT pinned
  by SHA in the pre-Wave-356 doc; reviewers had to inspect `data/`
  manually).
- A canonical reviewer-side reproduction path (4-step section
  cross-referenced to 8 `reproduce/*.sh` scripts). Pre-Wave-356, the
  reproduction steps were inlined only in `reproduce/*.sh` and
  `supplementary_bundle/README.md` — not surfaced in
  `data_availability.md`.
- A canonical Wave 343-355 audit-trail cross-reference. Pre-Wave-356,
  reviewers reading `data_availability.md` did not have an index of
  the Wave 343 + Wave 344 freeze-marker + Wave 348-355
  polish/refactor/refresh waves that constitute the post-freeze
  evidence chain.

Each of these is additive editorial evidence; no number moved; no
status label was promoted; no vendored file was touched. The polish
is editorial-debt-reduction, not claim-mutation.

---

## 4. Unresolved / Disclosed Gaps

| # | Gap | Status | Disclosure location |
|---|-----|--------|---------------------|
| 1 | R3 FlowMol3 fg_dev 3-seed direction consistency: in flight | DISCLOSED (verbatim) | Pre-existing §"Honesty disclosure — incomplete / partial data" row 1 (line 121) |
| 2 | K4 (Kanzi decision-metric saturation): UNDERPOWERED / TIES_AT_ZERO | DISCLOSED (verbatim) | Pre-existing §"Honesty disclosure" row 2 (line 122) |
| 3 | K5 (FreqFlow + MM-FM integration): ENV_BLOCKED | DISCLOSED (verbatim) | Pre-existing §"Honesty disclosure" row 3 (line 123) |
| 4 | K6 (Wan2.2 N=1000 sweep): DEFERRED to camera-ready | DISCLOSED (verbatim) | Pre-existing §"Honesty disclosure" row 4 (line 124) |
| 5 | FreqFlow (row 9 of new §8 table): tarball-vendored, no public git release | DISCLOSED (NEW §8 honest-uncertainty paragraph + CLM-056 cross-link) | New §8 last paragraph |
| 6 | MANIFEST.md self-row displayed SHA (`94b6f990...` then `d3f130f0...` after Wave 356 highlights commit) is slightly stale relative to current file state | DISCLOSED (noted in §2.4 of this audit doc; managed by Wave-355-style SHA-refresh waves, e.g. `wave354-manifest-sha256-refresh.md` + `wave355-final-sha256-refresh.md`) | This audit doc §2.4 |

---

## 5. Files Modified

| File | Operation | Reason |
|------|-----------|--------|
| `tnnls_submission/data_availability.md` | ADDITIVE EDIT (3 new sections appended; 7 pre-existing sections preserved byte-identically) | Wave 356 P2 task brief |
| `tnnls_submission/MANIFEST.md` | EDIT (`data_availability.md` row size + SHA-256 + role suffix refresh; self-row audit pin list +1 entry) | Standard SHA-256 column regeneration |
| `docs/audit/wave356-data-availability-polish.md` | CREATED (this audit doc) | Wave 356 P2 task brief |

Total files modified: 3. Vendored upstream: 0 (read-only verification
only).

---

## 6. Post-Wave-356 P2 SHA-256 state of `tnnls_submission/*.md`

```bash
$ cd tnnls_submission && sha256sum -- *.md
a6976825d19276c4fbb98efb167cadac24ed94cc4013796e0961580ca3ebf6f1  cover_letter.md
86127df70c02c5890b1a8f74fc29cbc3c89c3342427d0478f42a36ab0642c979  data_availability.md   ← refreshed by Wave 356 P2
36e3d3f3ec2410c89221b35bb28bb7d8136251e7e64bfd12fa453d4a098d54ac  figures.md
380a3e13fbe6d479cb532fce6b8961d82dc24eb2036a89cf9d26e2a930305a41  FILL_GUIDE.md
3201f8e2b2402164a3f49caa9ae658265f8f1cfd042564bdaab714d0bb9987de  highlights.md
<post-Wave-355-final>                                                                        MANIFEST.md   ← self-SHA managed by separate SHA-refresh waves
872a8415426a34eec2af696be00ae117882c899d79661f17806b441db998c734  README.md
b8445c5a336266d05e6833c3d8bc6b83d77463130860ea872a9aacbebcc403bb  submission_checklist.md
24f4bc71f36f37ff7d8bbb0a230acb0bd999b0308c7a24c70da71222015bf926  tables.md
```

---

## 7. Conclusion

`data_availability.md` is now TNNLS-submittable with a complete
reviewer-facing evidence trail: 9 vendored repos pinned at their
canonical upstream commit hashes (8 git-vendored + 1 tarball-vendored
with honest disclosure), a 4-step reproduction path cross-referenced
to 8 `reproduce/*.sh` scripts, and a 35+ Wave 343-355 audit-doc
cross-reference index. The polish is purely editorial (no numerics,
no status promotion, no vendored modification). The MANIFEST.md
SHA-256 column for the `data_availability.md` row was refreshed to
the post-Wave-356 P2 value. No pre-existing prose was destructively
rewritten. Per Wave 268 strict-clean rule + AGENTS.md §3.2 ADDITIVE-only
hard guardrail + Wave 325 NO-PUSH policy.

**End of audit (Wave 356 P2 — data_availability.md final polish).**
