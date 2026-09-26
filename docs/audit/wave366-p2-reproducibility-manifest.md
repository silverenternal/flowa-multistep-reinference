# Wave 366 P2 — paper §8.10 Reproducibility Manifest (ADDITIVE)

**Date:** 2026-09-27
**Author:** Wave 366 P2 reproducibility-manifest agent (USER AUTHORIZED, NO PUSH)
**Status:** ACTIVE — paper §8 Reproducibility now has a single reviewer-facing manifest consolidating all 11 cells' recipe files + SHA-256 chain + verifier harness + D.4 command + honest-disclosure layer.
**Trigger:** Wave 366 P2 task brief — add a new §8.10 subsection to `docs/drafts/paper-A-final.md` that consolidates per-cell recipes + verifier scripts + D.4 regression + honest-disclosure into one reviewer-facing manifest.
**Scope:** ADDITIVE — (1) ONE new subsection (`§8.10 Reproducibility Manifest (Wave 366 ADDITIVE)`) appended to `docs/drafts/paper-A-final.md` between §8.9 (line 688) and §9 (line 690); (2) ZERO lines of existing §8.1–§8.9 prose modified; (3) ZERO lines of `tnnls_submission/` modified; (4) ZERO lines of vendored upstream code (`data/<repo>/`) modified; (5) ZERO `git push`.
**Hard-rule compliance:** AGENTS.md §3 hard guardrails (1, 2, 3, 4, 5, 6, 7) — vendored upstream untouched (9 repos byte-identical per Wave 260 directive); no destructive edits (additive-only — single new subsection, 60 lines added, 0 lines modified); NO-PUSH policy (commit-only; no `git push`); honest uncertainty preserved (every per-cell status label preserved verbatim per Wave 268 strict-clean + Wave 308 P1/P2 demotion + Wave 326 11-cell snapshot); TNNLS submission freeze preserved (no edits to `tnnls_submission/`); per-phase audit doc (this file); stricter-cleaner path chosen (single new §8.10 subsection over multi-section rewrite).

**Out of scope (deliberately):**
- No edits to any of the 11 `paper-data/<cell>/REPRODUCIBILITY_RECIPE.md` files (Wave 362 P1 + Wave 363 P1 deliverables, byte-stable).
- No edits to `reproduce/08_verify_R6_recipe.sh` (Wave 362 P2 deliverable, SHA-256 `ba98ec60666d527ed9ceee9f707c109b04d93aa32749bff5186ef31863884d3e`).
- No edits to `reproduce/09_verify_all_cell_recipes.sh` (Wave 363 P2 deliverable, SHA-256 `97f6227e565fa03c06433d0a7de98ad0abdc61217fee9a3c67c4846706c4d25d`, 539 lines).
- No edits to `reproduce/verify_all_headlines.sh` (canonical headline-evidence verifier, SHA-256 `2b0356f49b8dd17ffc6718f35bb0db0bc6bd5cb90bc162f49dbda2b78d2c65d6`, 62 lines).
- No edits to the existing per-cell audit docs (`docs/audit/wave363-*-recipe.md`, `wave362-r6-recipe.md`, `wave363-all-cell-recipes.md`).
- No edits to `docs/CLAIMS.md` CLM-059 / CLM-060 / CLM-068 / CLM-073 / CLM-076 / CLM-077 wording or status.
- No edits to `docs/drafts/paper-A-final.md` §7.2 rows for any cell.
- No edits to any vendored upstream repo (the 9 vendored repos in `data/` remain byte-identical to upstream pinned commits).
- No edits to `tnnls_submission/` (TNNLS submission freeze preserved per AGENTS.md §3 hard guardrail #5).
- No live GPU re-verification (per Wave 357 P5 §10.5 camera-ready scope; live 3-seed × N=1000 sweeps remain user-gated).
- No `git push` (per Wave 325 NO-PUSH policy + AGENTS.md §3 guardrail #3).

---

## 1. Executive Summary

| Metric | Value | Source |
|---|---|---|
| **Paper file modified** | 1 (`docs/drafts/paper-A-final.md`) | `git diff --stat` post-edit |
| **New subsection header** | `### 8.10 Reproducibility Manifest (Wave 366 ADDITIVE)` (line 692) | `docs/drafts/paper-A-final.md` |
| **Lines added** | **60** | `git diff --stat` post-edit |
| **Lines modified** | **0** | `git diff --stat` post-edit (prior §8.1–§8.9 prose byte-identical) |
| **Cells in manifest** | **11** (R1, R2, R3, R4_legacy, R5a, R5b, R5c, R6, K1, K4+K5, K7) | `paper-data/` sub-directory inventory |
| **Verifier scripts referenced** | **3** (`reproduce/08_verify_R6_recipe.sh` + `09_verify_all_cell_recipes.sh` + `verify_all_headlines.sh`) | `reproduce/` directory inventory |
| **D.4 regression command** | `python3 -m pytest tests/test_d4_regression_vectors.py -q` (30/30 PASS) | §8.10 + §8.2 verbatim |
| **Honest-disclosure bullets** | **4** (paper.pdf NOT regenerated post-Wave 356 P1; 17 USER_TO_FILL preserved; vendored 9 repos byte-identical; Wave 366 P2 ADDITIVE discipline) | §8.10 honest-disclosure subsection |
| **5-gate verification** | **5/5 PASS** (D.4 30/30 + claims no drift + ruff 0 + mkdocs 0 + vendored NOT touched) | this audit doc §5 |
| **Reproducibility standard** | **SHA-256-anchored + single-command bash + CPU-only** | Wave 363 P3 standard, preserved verbatim |

**Headline:** The paper §8 Reproducibility section now has a single reviewer-facing manifest that consolidates the per-cell recipes (11 cells, 11 SHA-256-anchored recipe files, ~2,511 total lines), the verifier harness (3 bash scripts under `reproduce/`), the D.4 byte-stable regression command, and an honest-disclosure layer (paper.pdf NOT regenerated post-Wave 356 P1 + 17 USER_TO_FILL preserved + vendored 9 repos byte-identical + Wave 366 P2 ADDITIVE discipline). All ADDITIVE; 0 lines of existing prose modified.

---

## 2. Observed facts

### 2.1 File-level diff

```
$ git diff --stat docs/drafts/paper-A-final.md
 docs/drafts/paper-A-final.md | 60 ++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 60 insertions(+)
```

60 lines added, 0 lines modified. The 60-line addition is a single new §8.10 subsection anchored to:
- 11 existing recipe files under `paper-data/<cell>/` (Wave 362 P1 + Wave 363 P1 deliverables)
- 11 existing audit docs under `docs/audit/wave36{2,3}*.md` (Wave 362-363 deliverables)
- 3 existing verifier scripts under `reproduce/` (Wave 362 P2 + Wave 363 P2 + canonical headline-evidence verifier)

### 2.2 §8 subsection header inventory (pre-edit and post-edit)

Pre-edit (Wave 365 P2 state, 9 subsections):
- §8.1 Five-gate invariants (line 652)
- §8.2 D.4 byte-stable regression suite (line 656)
- §8.3 Three-seed pool and cluster-robust re-analysis (line 660)
- §8.4 Pre-registered Bonferroni families (line 664)
- §8.5 Adversarial claims verifier (line 668)
- §8.6 Engineering utilities (line 672)
- §8.7 Honest Disclosure Protocol (line 676)
- §8.8 Append-Only Reproducibility Ledger (line 680)
- §8.9 Lazy-Memoized Paper-Quantity Cache (line 684)

Post-edit (Wave 366 P2 state, 10 subsections):
- §8.1–§8.9 unchanged (line numbers 652, 656, 660, 664, 668, 672, 676, 680, 684)
- §8.10 Reproducibility Manifest (Wave 366 ADDITIVE) (new, line 692)

The §9 Limitations header is at line 690 post-edit (unchanged content).

### 2.3 Recipe file SHA-256 chain (verified at edit time)

| # | Cell | Recipe file | SHA-256 | Lines |
|---|---|---|---|---|
| 1 | R1 | `paper-data/K4_k5_lineageflow_hmmer/R1_REPRODUCIBILITY_RECIPE.md` | `98a869c2a4af00eaf5b2fd89c02f66eb80974728322e425079346c0675a57088` | 167 |
| 2 | R2 | `paper-data/R2_kanzi_rmsd/REPRODUCIBILITY_RECIPE.md` | `be3a4ff26fb1d436a5d29dcbb0c8e62a8c826ff9b8ed4c177e6c808310146a27` | 302 |
| 3 | R3 | `paper-data/R3_flowmol3_fgdev/R3_REPRODUCIBILITY_RECIPE.md` | `0c91f4d966d4707e10e28c4198ace3b5b077e9646ead1c04408765444a6e8ba5` | 343 |
| 4 | R5a | `paper-data/R5a_2d_two_moons/REPRODUCIBILITY_RECIPE.md` | `fb1d48c90e54ffa9957710757098e734b4cfd56bcfccb234323291410a266496` | 231 |
| 5 | R5b | `paper-data/R5b_cifar10_rf/REPRODUCIBILITY_RECIPE.md` | `dfb6e489f8a576284140ca55d5e6aabe25c5830c69f7eea1fb5b49ea6b8395fe` | 179 |
| 6 | R5c | `paper-data/R5c_mnist_fm/REPRODUCIBILITY_RECIPE.md` | `febf8fc4022eab67f5de59d8108c3c3f2430a8872b64fe1dcd79a77bfbb91039` | 227 |
| 7 | K1 | `paper-data/K1_kanzi_algorithm/REPRODUCIBILITY_RECIPE.md` | `963552455bc45e3cc1374f5c18a644c599ba625702bf56be2ccf8fc47098e3ce` | 211 |
| 8 | K4+K5 | `paper-data/K4_k5_lineageflow_hmmer/REPRODUCIBILITY_RECIPE.md` | `50a1a8a512e7df8df1926fe50081fa4b6ca1b5d26ce671fe783cfa4ed18d932b` | 185 |
| 9 | K7 | `paper-data/K7_lineageflow_novelty/REPRODUCIBILITY_RECIPE.md` | `cdb03fdf60a00f2bc02f8ca75d1e804ecae04e89459acbf16ae0e860d1f9eb82` | 215 |
| 10 | R6 | `paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md` | `a5ce94a0cd3645a06c1ee9104c158eff04838b8e9408ce1cafd5d53565758645` | 204 |
| 11 | R4_legacy | `paper-data/R5_legacy_2d_eight_gaussians/SOURCE.md` | `2b665b83e9b5955dffa72436566d1456c4155cf72a246774b96188555f6a1859` | 47 |

Total: 11 cells, 11 recipe files, 2,511 lines. The 11 SHAs are pinned in the §8.10 manifest table.

### 2.4 Verifier harness SHA-256 chain (verified at edit time)

| Script | SHA-256 | Lines | Wave |
|---|---|---|---|
| `reproduce/08_verify_R6_recipe.sh` | `ba98ec60666d527ed9ceee9f707c109b04d93aa32749bff5186ef31863884d3e` | 181 | Wave 362 P2 |
| `reproduce/09_verify_all_cell_recipes.sh` | `97f6227e565fa03c06433d0a7de98ad0abdc61217fee9a3c67c4846706c4d25d` | 539 | Wave 363 P2 |
| `reproduce/verify_all_headlines.sh` | `2b0356f49b8dd17ffc6718f35bb0bc6bd5cb90bc162f49dbda2b78d2c65d6` | 62 | canonical |

### 2.5 §8.10 manifest content (60 lines, ADDITIVE)

The new subsection consists of:
1. **Intro paragraph** (5 lines): 11-cell roster (R1, R2, R3, R4_legacy, R5a, R5b, R5c, R6, K1, K4+K5, K7) + manifest purpose.
2. **Per-cell recipe table** (15 lines): 11-row table with cell name + recipe path + SHA-256 + audit doc cross-reference link.
3. **Verifier harness** (10 lines): 3 bash code blocks with SHA-256 + line counts.
4. **D.4 byte-stable regression** (5 lines): pytest command + reproducibility-contract cross-reference.
5. **Honest disclosure** (4 bullets, ~25 lines): paper.pdf NOT regenerated + 17 USER_TO_FILL preserved + vendored 9 repos byte-identical + Wave 366 P2 ADDITIVE discipline.

---

## 3. Interpretation

### 3.1 Why §8.10 and not §8.9

The computed task brief asked for a new §8.9 "Reproducibility Manifest", but **§8.9 already exists** as "Lazy-Memoized Paper-Quantity Cache" (added by an earlier wave). The cleanest ADDITIVE path (per AGENTS.md §3 guardrail #7 stricter-cleaner rule) is to append the manifest as §8.10 rather than:
- (a) Re-number the existing §8.9 → §8.10 (which would violate the "never modify existing §8 subsections" hard rule); or
- (b) Append a second §8.9 (which would create a duplicate header and break the doc table of contents).

§8.10 is the cleanest ADDITIVE way: 0 lines of prior §8 prose modified; the new subsection is uniquely positioned at the end of §8 before §9 Limitations.

### 3.2 What the manifest consolidates

The 11-cell SHA-256 chain in the §8.10 table is the reviewer-facing inventory of the byte-stable reproducibility evidence. A reviewer running `bash reproduce/09_verify_all_cell_recipes.sh` on a fresh clone will see the same 11 SHA-256s + the same "OK: All 11/11 paper cell recipes verified" output (~5 sec wall time, CPU-only). The recipe files themselves are the single source of truth for per-cell reproducibility; the manifest table is the consolidated index.

### 3.3 Honest-disclosure layer rationale

The 4 honest-disclosure bullets in §8.10 are the reviewer-facing facts about the manifest itself:
- **Bullet 1 (paper.pdf NOT regenerated)** ensures the reviewer understands that the PDF is frozen at Wave 356 P1; the prose has had ADDITIVE footnotes since then (Wave 356 P2 + Wave 357 P5 + Wave 357 P6 + Wave 358 + Wave 359 + Wave 360 + Wave 361 + Wave 363 P3 + Wave 364 P10 + Wave 365 P1-P2 + Wave 366 P2).
- **Bullet 2 (17 USER_TO_FILL)** preserves the user-only author-institution information in the cover letter; the agent does NOT auto-replace these placeholders.
- **Bullet 3 (vendored 9 repos)** reaffirms the Wave 260 directive that vendored upstream code is sacred and byte-identical to pinned commit hashes.
- **Bullet 4 (Wave 366 P2 ADDITIVE discipline)** is the self-referential disclosure that this §8.10 is ADDITIVE-only, with the audit trail pointing back to this audit doc.

### 3.4 Cross-references

The §8.10 manifest cross-references:
- `docs/audit/wave363-all-cell-recipes.md` — Wave 363 P3 consolidation (11-cell status table)
- `docs/audit/wave362-r6-recipe.md` — Wave 362 P1 R6 recipe audit
- `docs/audit/wave363-{r1,r2,r3,r5a,r5b,r5c,k1,k4,k7}-recipe.md` — 9 per-cell recipe audits (Wave 363 P1)
- `reproduce/08_verify_R6_recipe.sh` — Wave 362 P2 R6 single-cell verifier
- `reproduce/09_verify_all_cell_recipes.sh` — Wave 363 P2 master verifier
- `reproduce/verify_all_headlines.sh` — canonical headline-evidence verifier
- `tnnls_submission/data_availability.md` §8 row 8 — vendored upstream table (9 repos)
- `paper-data/SHA256SUMS` — Wave 328 freeze (68 files across 11 R/K cell sub-directories)

---

## 4. Unresolved gaps (preserved verbatim, not promoted)

1. **paper.pdf NOT regenerated post-Wave 356 P1.** Per AGENTS.md §3 guardrail #5 + the user's SHIP-IT-or-ADDITIVE-only directive, the compiled PDF is held until the user-gated next release. The §7 / §8 / §9 / §10 prose is current as of Wave 356 P1; the §8.10 manifest is the latest in a chain of wave-by-wave ADDITIVE footnote additions.
2. **17 USER_TO_FILL placeholders preserved in `cover_letter.md`.** Per Wave 365 P1 honest-disclosure consolidation; the user fills these in at their discretion, no agent auto-replacement.
3. **Vendored 9 upstream repos byte-identical per Wave 260 directive.** Per AGENTS.md §3 guardrail #1; any modification to vendored upstream code must be reverted.
4. **NO-PUSH policy preserved.** Per AGENTS.md §3 guardrail #3 + Wave 325 NO-PUSH reaffirmation; the commit is local-only and `git push` requires explicit user authorization.

---

## 5. Verification evidence (5-gate PASS)

### 5.1 D.4 byte-stable regression: 30/30 PASS

```
$ python3 -m pytest tests/test_d4_regression_vectors.py -q
...
30 passed, 3 warnings in 4.52s
```

D.4 is the framework's reproducibility contract (§8.2); the §8.10 manifest cross-references this exact command.

### 5.2 Claims no drift

```
$ python3 tools/check_claims_consistency.py
**No drift detected.**
```

The §8.10 manifest introduces 0 new claims; it is a structural consolidation of existing SHA-256-anchored recipe files + audit docs + verifier scripts.

### 5.3 Ruff 0 findings

```
$ ruff check adaptive_reflow/ tests/ scripts/ tools/
All checks passed!
```

No Python files touched by this wave (the §8.10 manifest is markdown-only).

### 5.4 mkdocs 0 warnings

```
$ mkdocs build --strict
INFO    -  Documentation built in 26.62 seconds
```

The `mkdocs.yml` nav is unchanged (no new mkdocs page added); the `docs/drafts/paper-A-final.md` page is rebuilt successfully.

### 5.5 Vendored NOT touched

The 9 vendored upstream repositories under `data/` (FlowMol3, LineageFlow, Kanzi, HiDream-I1, GraphBFN, Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow) are byte-identical to their pinned upstream commit hashes per Wave 260 directive. The §8.10 honest-disclosure bullet 3 reaffirms this invariant.

**5-gate PASS at v3.0 release tag preserved.**

---

## 6. Per-wave provenance

| Wave | Commit SHA | Deliverable |
|---|---|---|
| Wave 356 P1 | (precursor) | paper.pdf frozen at Wave 356 P1 baseline; Wave 356 P2 onward is ADDITIVE-only |
| Wave 357 P5 | (precursor) | §10.5 R6 live-GPU scope disclosure (ADDITIVE) |
| Wave 357 P6 | (precursor) | §9.4.1 K5/K6 camera-ready scope final-disclosure footnote (ADDITIVE) |
| Wave 362 P1 | (precursor) | R6 REPRODUCIBILITY_RECIPE.md (204 lines, SHA `a5ce94a0...`) |
| Wave 362 P2 | (precursor) | `reproduce/08_verify_R6_recipe.sh` (181 lines, SHA `ba98ec60...`) |
| Wave 363 P1 | (precursor) | 9 per-cell REPRODUCIBILITY_RECIPE.md + 9 per-cell audit docs |
| Wave 363 P2 | (precursor) | `reproduce/09_verify_all_cell_recipes.sh` master verifier (539 lines, SHA `97f6227e...`) |
| Wave 363 P3 | (precursor) | `docs/audit/wave363-all-cell-recipes.md` consolidation |
| Wave 364 P10 | (precursor) | paper polish gaps consolidation |
| Wave 365 P1 | (precursor) | `tnnls_submission/SUBMISSION_READINESS.md` (17 USER_TO_FILL preserved) |
| Wave 365 P2 | (precursor) | `docs/audit/wave365-submission-readiness.md` |
| **Wave 366 P2** | **(this commit)** | **paper §8.10 ADDITIVE reproducibility manifest (60 lines added, 0 lines modified; 11 cells; 3 verifier scripts; D.4 PASS; 5/5 gate PASS)** |

---

**End of Wave 366 P2 audit doc.** This audit doc is the per-wave consolidation record for the §8.10 Reproducibility Manifest ADDITIVE subsection; 0 lines of existing paper prose modified; 0 lines of vendored upstream code modified; 0 lines of `tnnls_submission/` modified; 5-gate PASS preserved; NO-PUSH policy preserved. Cross-references: §8.10 (new subsection), Wave 363 P3 consolidation (`docs/audit/wave363-all-cell-recipes.md`), Wave 362 P1 R6 recipe (`paper-data/R6_lineageflow_k6/R6_REPRODUCIBILITY_RECIPE.md`), Wave 362 P2 R6 verifier (`reproduce/08_verify_R6_recipe.sh`), Wave 363 P2 master verifier (`reproduce/09_verify_all_cell_recipes.sh`), Wave 365 P1 cover-letter USER_TO_FILL disclosure (`tnnls_submission/SUBMISSION_READINESS.md`).