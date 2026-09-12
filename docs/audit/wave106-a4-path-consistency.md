# Wave 106.A.4 — Path + Data Consistency Audit

**Audit type:** READ-ONLY (no source code edits, no docs edits, no commits)
**Date:** 2026-09-11
**Auditor:** Wave 106.A.4
**Repo:** `/home/hugo/codes/flowa-multistep-reinference`
**Commit SHA at audit start:** `d6925838342a865e7825438f547847ad1ed2a582` (Wave 101/102 final)
**Branch:** `main`
**Unpushed commits vs `origin/main` (90a8e48da5ddf4bbbe3c4969eca71ba4d9b1a992):** **1** (`d692583`)

---

## 0. Method

For each finding: `file:line | claim (text excerpt) | actual state (path/existence check) | severity (high/medium/low)`.

Evidence was gathered via:
- `git rev-parse HEAD` / `git log --oneline origin/main..HEAD | wc -l`
- `ls`, `find` for path-existence checks
- `sha256sum` for ckpt digest checks
- `grep` for citation claims
- `cat` for context

Files audited: 38 (5 paper-package docs + 2 README + 1 GATES + 1 ARCHITECTURE + 1 INDEX + 1 baseline-audit + 30 wave audit docs sampled).

---

## 1. Findings table

| # | file:line | claim (excerpt) | actual state | severity |
|---|-----------|-----------------|--------------|----------|
| 1 | `cover_letter.md:39` | "**327 unpushed commits** sit on `main` ahead of `origin/main`" | `git log --oneline origin/main..HEAD \| wc -l` returns **1** (commit `d692583` is the only one ahead of `origin/main` = `90a8e48da5ddf4bbbe3c4969eca71ba4d9b1a992`). | **high** |
| 2 | `supplementary.md:270` | "**327 unpushed commits** on `main` ahead of `origin/main` as of commit `e69ffd8` (Wave 93 Phase 1)." | Same root cause as #1. Current `HEAD` is `d692583`, NOT `e69ffd8`. The "327" figure and the anchor commit are both stale (HEAD has moved past `e69ffd8` and most unpushed commits were either rebased or pushed). | **high** |
| 3 | `README.md:12` | "Test count: 1235 passing / 7 skipped (torch-gated)" | `pytest_results.txt` and `pytest_final.txt` both show **2165 passed, 9 skipped, 3 FAILED, 39 warnings**. README is 930 tests out-of-date and omits the 3 current pre-existing failures (`test_exp2_stochastic_fm_w2_ratio_reproduces_25pct_reduction`, `test_check_docs_against_code.py::test_no_false_positives_on_current_repo`, `test_check_docs_against_code.py::test_self_test_quiet_mode_returns_zero_exit`). | **high** |
| 4 | `README.md:372` | "Current state on this tree: 1235 tests pass, 7 skipped" | Same root cause as #3. | **high** |
| 5 | `/INSTALL_REPORT.md` (no such file) | task #1169 marked complete: "Wave 80 Agent B: Author INSTALL_REPORT.md + commit (no push)". cover_letter.md and submission_checklist.md cite it indirectly via the Wave 80 task list. | Neither `/home/hugo/codes/flowa-multistep-reinference/INSTALL_REPORT.md` nor `docs/INSTALL_REPORT.md` exists. `find / -name INSTALL_REPORT.md` returns nothing under repo root. | **high** |
| 6 | `cover_letter.md:39` | "Vendored checkpoints with SHA-256 pinned: Kanzi `c2f2ab8d...d270`, LineageFlow `f0b4b25e...54a2b`, FlowMol3 `data/flowmol3/weights_real/checkpoints/last.ckpt` (epoch 17, global_step 1,547,236). A reviewer re-verifies with each JSON's `sha256` field." | No JSON file in `verification_outputs/` contains a SHA-256 hash for FlowMol3 ckpt. Kanzi + LineageFlow JSONs exist and verify against actual ckpts (`c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270` ✓ ; `f0b4b25e626878be5c26da9e65d44c2e1551a076652d416f955b1357cde54a2b` ✓). FlowMol3 actual SHA-256 (`0e949b56b54c1d2fcbded4f0c9857bfd33dbde86bcc9db2f82572628f7f9f5b5`) is not pinned in any verification_output file. The epoch/global_step claim has no .ckpt.meta file to verify against. | **medium** (Kanzi/LineageFlow ✓ ; FlowMol3 missing pinned JSON) |
| 7 | `supplementary.md` (entire file, 12+ TODO markers) | File explicitly states: "This document is the **TEMPLATE** for the venue supplementary material. Each section below carries a `<!-- TODO -->` marker that Wave 94 Phase 2/3 must replace with the actual numbers / pointers" (line 7). 12 explicit `<!-- TODO(Wave 94 Phase 2) -->` markers at lines 39, 49, 88, 118, 150, 178, 220, 244, 288 + footer line 321. | The file is still in TEMPLATE state; no Wave 94 Phase 2/3 work has landed. cover_letter.md line 41 says "**D.4 byte-stable regression vectors: 33/33 PASS**. **G-MASTER capability gate: 7/7 PASS**. **`mkdocs build --strict`: EXIT=0**" — yet the supplementary it points to contains placeholder TODOs. | **high** |
| 8 | `submission_checklist.md:64` | "ckpt SHA-256 verified — every entry in `verification_outputs/ckpt_sha256.json`" | `ls verification_outputs/ckpt_sha256.json` → No such file. Line 64 admits: "(placeholder path; confirm `verification_outputs/` artifact exists post-Wave 92c)". | **medium** |
| 9 | `submission_checklist.md:51-58` (Tier 3 cells, marked with `[x]`) | 8 of 12 cells ticked `REPORTED` for FlowMol3 + Kanzi + 4 LineageFlow cells ticked `DEFERRED`. | The submission_checklist self-declares (line 6): "All boxes are **PLACEHOLDERS** until Wave 92c and Wave 93 Phase 2 land". Yet the boxes are pre-ticked. The LineageFlow rows are correctly `[ ]` but the FlowMol3 + Kanzi rows are `[x]`. Same CHECKBOX state mismatch. | **medium** |
| 10 | `cover_letter.md:39` | "D.4 byte-stable regression vectors: **33/33 PASS**" | `pytest_results.txt` (latest in-repo run) shows **3 failed** (`test_exp2_stochastic_fm_w2_ratio_reproduces_25pct_reduction`, `test_check_docs_against_code.py::test_no_false_positives_on_current_repo`, `test_check_docs_against_code.py::test_self_test_quiet_mode_returns_zero_exit`). The "33/33" only applies to `-k d4`, not the whole pytest suite. The cover letter conflates the two. | **medium** |
| 11 | Multiple env_hash variants | cover_letter.md cites env_hash `983f7707e7207ed6dee1972cc1fb9306448ad6367963edefd612f88b76519092` from `env_hash.txt`. | `env_hash.txt` reports `composite_hash=3bbab6fef2471772a5d49834419b40c43a45104a7f9bd865eb708aa48ff73ed0`, `env_hash_R2.txt`/`R3.txt`/`R6.txt` report `composite_hash=8ca7e3031a7ddc97d13b85dbb92e1cf63da1c3082573507d30c99de8cfb87480`, `env_hash_R5.txt` reports `2c05d22012bd9cf7f58ad88cfca96176afb54bf10e16bdb98dba0092e9a4cb4f`, `env_hash_host_fingerprint.json` reports `17c56995791f2ab424230ded201d34ca47c8872dcaaed67db7a583b5dea6bce2`. **5 different composite_hash values** for what should be 1 environment anchor. None of the variants match. | **medium** |
| 12 | `cover_letter.md:39` | "Kanzi at commit `cfed9cf` (`data/kanzi_upstream/`)" | `data/kanzi_upstream/` exists (with `assets/ pdbs/ src/ uv.lock pyproject.toml README.md`); the commit SHA is not stored in any tracked file — no `.git` folder inside `data/kanzi_upstream/`. Reviewer cannot verify `cfed9cf` is the snapshot commit. | **medium** |
| 13 | `cover_letter.md:39` | "LineageFlow at commit `ccef84a`" | `data/lineageflow_upstream/` exists; verified upstream.commit is `ccef84adff421fcb6b855285bc1860e1f9a94f59` per `verification_outputs/lineageflow_real_ckpt_forward_q4_2026.json:36` (matches `ccef84a` ✓). Kanzi not verifiable (no upstream audit JSON). | **low** (LineageFlow ✓) |
| 14 | `cover_letter.md:39` | "FlowMol3 at commit `77cae22` (`data/FlowMol3/repo/`)" | `data/FlowMol3/repo/` exists; no `.git` folder inside. Commit SHA not stored in any tracked file. Reviewer cannot verify `77cae22`. | **medium** |
| 15 | `cover_letter.md:38` | "**Sample budget**... 5,000-50,000 trajectories" | Section 5.7 of `paper-draft.md` may cite different numbers; not cross-checked in this audit. UNVERIFIED — paper-draft §5.7 contents out of scope for this audit but flagged as a potential inconsistency. | **low** (UNVERIFIED) |
| 16 | `cover_letter.md:39` | "**mkdocs build --strict**: EXIT=0" | UNVERIFIED — not re-run in this audit (per audit constraints). Multiple recent audit docs (`wave83-phase4-final.md`, `wave96e-final-synthesis.md`, `wave88-phase3-final.md`, etc.) cite the same. Risk: if a recent commit added a broken link, this would be EXIT≠0. | **low** (UNVERIFIED) |
| 17 | `cover_letter.md:39` | "**G-MASTER capability gate: 7/7 PASS**" | UNVERIFIED — not re-run in this audit. Multiple recent audit docs cite the same. | **low** (UNVERIFIED) |
| 18 | `cover_letter.md:39` | "**D.4 byte-stable regression vectors: 33/33 PASS**" | Last verified per `docs/audit/wave100-kanzi-load-torch-fix.md:76` and `wave105-p2a-final.md`. `-k d4` is a *subset* of the full pytest (which is 3 failed). The "33/33" refers only to the D.4 regression vectors (not the full pytest). cover_letter phrasing is technically OK if read literally but ambiguous. | **low** (technically OK; reader could misread) |
| 19 | `cover_letter.md:39` | "reviewer re-verifies with each JSON's `sha256` field" (referring to all 3 ckpts) | Only Kanzi + LineageFlow have `verification_outputs/*_real_ckpt_forward_q4_2026.json` files with `checkpoint.sha256` fields. FlowMol3 has NO equivalent JSON — no ckpt-digest JSON exists for FlowMol3. | **medium** |
| 20 | `cover_letter.md:39` + `cover_letter.md:9` | "FlowMol3 ... (epoch 17, global_step 1,547,236)" | No `.ckpt.meta` file in `data/flowmol3/weights_real/checkpoints/`; cannot verify epoch or global_step. The 68 MB ckpt is a vanilla PyTorch Lightning `.ckpt` but cover letter claims PyTorch Lightning 2.1.3 (from `submission_checklist.md:24`). | **medium** |
| 21 | `submission_checklist.md:24` | "FlowMol3 ... PyTorch Lightning 2.1.3" | UNVERIFIED — actual torch version in ckpt environment: 2.14.0+cu130 (per `verification_outputs/kanzi_real_ckpt_forward_q4_2026.json:46` shows kanzi_venv torch, but flowmol3 ckpt env not pinned). | **low** (UNVERIFIED) |
| 22 | `docs/audit/wave99b-n1000-verdict.md:9-11` | "The task brief expected `verification_outputs/kanzi_n1000_real_v2/per_metric.jsonl` with 1000 records from Wave 99.A. **That directory does not exist** on the working tree" | Confirmed: `ls verification_outputs/kanzi_n1000_real_v2/` → "No such file or directory". Only `kanzi_n1000_real_v3/` exists. | **medium** (documented gap; correctly flagged by Wave 99.B) |
| 23 | `docs/audit/wave76-*`, `wave77-*`, `wave78-*` (none exist) | submission_checklist + cover_letter cite these as if they exist. push-ready-summary.md:747-756 lists Wave 76/77/78 plan surface. | `ls docs/audit/wave7{6,7,8}*` returns no matches. Wave 76 + 77 + 78 were "pending" per task list (Wave 77 / Wave 78 marked `pending`); never landed. cover_letter and submission_checklist implicitly treat them as completed. | **medium** |
| 24 | `docs/audit/wave69-phase6-final.md`, `wave75-phase6-final.md`, `wave99-n1000-final.md` | Cited as evidence trail in cover_letter + submission_checklist | All 3 files exist (verified by `ls`). Content match not verified beyond existence. | **low** (existence ✓) |
| 25 | `docs/audit/wave88-phase2-sweep.md` | Cited in cover_letter G2 + submission_checklist:25 | File exists. Content mentions Wave 88 has "negative structural result on the framework arm" (line 8) — matches cover_letter's Kanzi REGRESSES_BY_+0.864_Å verdict. | **low** (consistent) |
| 26 | `docs/audit/wave88-phase3-final.md` | Referenced in submission_checklist + Wave 88 evidence trail | File exists (verified). | **low** (existence ✓) |
| 27 | `docs/audit/wave89-phase1-final.md` | Referenced as Wave 89 final synthesis | File exists (verified). | **low** (existence ✓) |
| 28 | `docs/audit/wave99b-n1000-verdict.md` | Referenced in cover_letter §"Wave 99 update on Kanzi" | File exists; opens with the honest "the brief expected `verification_outputs/kanzi_n1000_real_v2/per_metric.jsonl`... does not exist" disclosure. | **low** (existence ✓; honest disclosure present) |
| 29 | `docs/audit/wave{81,82,88}-phase4-final.md` (referenced as audit trail for G2 in `submission_checklist.md:25`) | All 3 exist (verified). | OK. | **low** (consistent) |
| 30 | `docs/audit/wave{75,83}-*.md` (referenced as audit trail for G3 in `submission_checklist.md:26`) | All exist (verified). | OK. | **low** (consistent) |
| 31 | `docs/architecture.md` (referenced in `README.md:12`) | Cited as Architecture at a glance, links to `docs/architecture.md`. | The actual file is `docs/ARCHITECTURE.md` (uppercase) per `ls docs/`. README.md:79 has `[`docs/architecture.md`](docs/architecture.md)` — case-sensitive paths on Linux: this link would 404. | **medium** (case-mismatch bug) |
| 32 | `docs/theory/DEVIATIONS.md`, `operating-regime.md`, `theorem1_rate_bound.md` (all in `docs/theory/`) | Referenced as theory docs. | All 3 exist (verified by `ls docs/theory/`). | **low** (existence ✓) |
| 33 | `docs/GATES.md` | Referenced in `submission_checklist.md` and `README.md` | File exists (verified by `ls docs/`). Content not re-checked. | **low** (existence ✓) |
| 34 | `submission_checklist.md:14` | "Paper ≤ 9 pages" — left as `[ ]` placeholder | Per cover_letter.md:39 + supplementary.md TEMPLATE markers, the paper is in mid-rewrite state; pages not finalized. | **medium** (paper not final; still in flight) |
| 35 | `submission_checklist.md:13` | "Cover letter ≤ 1 page" — `[ ]` | cover_letter.md is ~700+ words (~3 pages when rendered); already violates the ICLR 1-page limit if interpreted strictly. | **medium** |
| 36 | `submission_checklist.md:69-70` | "rebase required to drop it before venue submission" (referring to Co-Authored-By trailer) | Verified: `git log --pretty=format:"%H %s" -10` shows recent commits all carry Co-Authored-By trailer (per task #1466: "Push Wave 101-105 hygiene commits"). Rebase not done. | **low** (honest disclosure in checklist ✓) |
| 37 | `paper-draft.md:2117` | "Wave 83 Agent B + Agent D additive update — all 6 Kanzi paper metrics at N=200 baseline arm" — cites `verification_outputs/kanzi_n1000_paper_metrics/kanzi_n1000_paper_metrics.json` | File exists (`ls verification_outputs/kanzi_n1000_paper_metrics/` ✓). | **low** (existence ✓) |
| 38 | `paper-draft.md:2117` | "The N=1000 reference coord file is `verification_outputs/kanzi_n1000_coords.txt`" | File exists (verified by `ls verification_outputs/kanzi_n1000_coords.txt` ✓). | **low** (existence ✓) |
| 39 | `paper-draft.md:2489-2494` | NOT INSTALLED list: `hmmpress`, `hmmscan`, `mmseqs`, `omegafold`, `fair-esm`, `biotite` | Wave 79 audit doc (`wave79-phase1-audit.md:59-67`) also reports NOT INSTALLED for these. Wave 80 task list claims some were installed (HMMER, MMseqs2, OmegaFold — task #1161-1163). Status drift between Wave 79 audit and Wave 80 task claims. UNVERIFIED in this audit whether Wave 80 install actually completed. | **medium** (UNVERIFIED; depends on whether task #1161-1163 actually completed) |
| 40 | `docs/CONSOLIDATED_RESULTS.md:2133, 2143, 2373` | "D.4 33/33 PASS" (multiple) | Same root cause as #10 (the 33/33 is for `-k d4` subset, not full pytest). | **medium** |
| 41 | `docs/CONSOLIDATED_RESULTS.md:2133` | "params, 0 missing/unexpected keys" | UNVERIFIED. The claim seems to be about Wave 92a Kanzi adapter refactor (per task #1283). | **low** (UNVERIFIED) |

---

## 2. Severity distribution

| severity | count |
|----------|-------|
| **high** | 5 (#1, #2, #3, #4, #5, #7) — actually 6 |
| **medium** | 14 (#6, #8, #9, #10, #11, #12, #14, #19, #20, #22, #23, #31, #34, #35, #39, #40) |
| **low** | 19 (#13, #15, #16, #17, #18, #21, #24-30, #32-33, #36-38, #41) |
| UNVERIFIED | 7 (#15, #16, #17, #21, #39, #41 + #41) |

(Counting high: 1+2+3+4+5+7 = 6 high; re-count: items 1, 2, 3, 4, 5, 7 are high → 6 high.)

---

## 3. Findings ranked most-severe first

1. **#5 — INSTALL_REPORT.md missing.** Task #1169 marked complete but file not on disk. Reviewer cannot verify environment install state.
2. **#1 + #2 — "327 unpushed commits" is a 326-off claim.** Actual unpushed count is 1. cover_letter and supplementary both cite this stale number.
3. **#3 + #4 — README test count is 930 tests stale.** Says "1235 passing" but actual is "2165 passed + 9 skipped + 3 failed" per pytest_results.txt.
4. **#7 — supplementary.md is a TEMPLATE with 12+ TODO markers.** cover_letter claims reproducibility gates passed but supplementary.md is unfilled.
5. **#6 — FlowMol3 ckpt SHA-256 not pinned in any verification_output JSON.** Cover_letter says "reviewer re-verifies with each JSON's `sha256` field" but no JSON exists for FlowMol3.
6. **#10 — D.4 33/33 conflated with full pytest PASS.** Cover_letter implies whole test suite is green; in fact 3 pre-existing pytest failures.
7. **#11 — 5 different env_hash composite_hash values.** env_hash.txt, R2/R3/R6, R5, host_fingerprint all disagree. No canonical anchor.
8. **#22 — `verification_outputs/kanzi_n1000_real_v2/` missing.** Wave 99.B doc honestly disclosed this; consistent with broader pattern.
9. **#23 — Wave 76/77/78 audit docs missing.** Cited in submission_checklist + cover_letter evidence trail but never authored.
10. **#31 — README.md links to `docs/architecture.md` (lowercase) but file is `docs/ARCHITECTURE.md`.** Case-sensitive Linux path → 404 link.

---

## 4. Reviewer-proof guarantee check (G1-G4)

| Guarantee | Status | Gap |
|-----------|--------|-----|
| G1 SHA-256 ckpt verification | **Partial** | Kanzi ✓ (`c2f2ab8d...d270` matches), LineageFlow ✓ (`f0b4b25e...54a2b` matches), FlowMol3 ✗ (no JSON file with the hash; epoch/global_step unverifiable). |
| G2 Upstream default sampling config | **OK** | Audit trail docs (`wave{81,82,88}*.md`) all exist. |
| G3 Zero new LOC in upstream metric code | **OK** | Audit trail docs (`wave{75,83}*.md`) all exist. |
| G4 Vendored upstream snapshot frozen | **Partial** | LineageFlow commit `ccef84adff421fcb6b855285bc1860e1f9a94f59` is verifiable from `verification_outputs/lineageflow_real_ckpt_forward_q4_2026.json:36`. Kanzi (`cfed9cf`) + FlowMol3 (`77cae22`) are NOT verifiable from any tracked file (no `.git` in vendored dirs). |

---

## 5. Honest limitations of this audit

- I did NOT re-run `pytest tests/ -k "d4"` or `mkdocs build --strict` or `tools/capability_audit.py` — relied on pytest_results.txt + audit doc citations.
- I did NOT verify paper-draft §5.7 / §7 / §1 numbers against actual JSON files.
- I did NOT inspect content of every wave{1..105} audit doc — only sampled cited ones (wave69, 75, 81, 82, 83, 87, 88, 89, 92c, 96e, 99b).
- I did NOT grep all 100+ audit docs for TODO markers; only `supplementary.md` + `cover_letter.md` + `submission_checklist.md` were checked.
- The 5 env_hash variants' interpretation (R2/R3/R5/R6 = Wave 2/3/5/6 repro env) is inferred from filename, not documented.

---

## 6. JSON return

```json
{
  "commit_sha": "d6925838342a865e7825438f547847ad1ed2a582",
  "files_audited": 38,
  "issues_found_count": 41,
  "high_severity_count": 6,
  "medium_severity_count": 14,
  "low_severity_count": 19,
  "unverified_count": 7,
  "output_file": "docs/audit/wave106-a4-path-consistency.md",
  "key_findings": [
    "INSTALL_REPORT.md missing (task #1169 marked complete but file absent)",
    "cover_letter claims 327 unpushed commits but actual is 1",
    "README test count is 930 tests stale (claims 1235; actual 2165 + 9 skipped + 3 failed)",
    "supplementary.md is TEMPLATE with 12+ TODO markers; cover_letter cites it as final",
    "FlowMol3 ckpt SHA-256 not pinned in any verification_output JSON",
    "5 different env_hash composite_hash values across env_hash.txt/R2/R3/R5/R6/host_fingerprint",
    "D.4 33/33 PASS conflates -k d4 subset with full pytest (which has 3 failed)",
    "verification_outputs/kanzi_n1000_real_v2/ missing (Wave 99.B honestly disclosed)",
    "Wave 76/77/78 audit docs missing (cited in submission_checklist as completed)",
    "README.md links to docs/architecture.md (lowercase) but file is docs/ARCHITECTURE.md (case-sensitive bug)"
  ]
}
```
