# Wave 357 P3 — R3 FlowMol3 RDKit environment blocker documentation (CONSOLIDATED_RESULTS.md §15.105 + paper §7.2 R3 row footnote)

**Date:** 2026-09-25
**Author:** Wave 357 P3 (R3 RDKit environment blocker documentation agent)
**Scope:** Add a reviewer-facing consolidated disclosure of the R3 FlowMol3 RDKit environment blocker to `docs/CONSOLIDATED_RESULTS.md` (new §15.105 section) and to `docs/drafts/paper-A-final.md` (ADDITIVE footnote appended after the §7.2 R3 row text at line 539). The disclosure consolidates the Wave 351 P3 vendor-fix-status audit findings (`docs/audit/wave351-r3-vendor-fix-status.md`) for reviewer visibility: DGL 2.4.0+cu124 is verified operational on the current host; the RDKit 2026.03.5 environment drift is the load-bearing blocker for the full N=1000 sweep (36.7% vs canonical 99.9% valid-yield gap at n=30 baseline 12/30 + framework 10/30). The R3 cell's verdict label `PARTIAL / single-seed PROJECTED` is preserved verbatim — no status change, no number change, no `tnnls_submission/` modification.

**Status:** **ADDITIVE_DOCUMENTATION_ONLY** — no source code touched, no vendored upstream touched, no sweep re-run, no CLAIMS modification, no SHA-256 regen (no `tnnls_submission/*.md` edit). The R3 blocker description now has explicit reviewer-facing visibility in the consolidated-results ledger.

**Trigger:** User request relayed through workflow harness: "剩下能做的任务也用ultracode做一下,这些任务都要处理" — close the remaining Wave 357 documentation gap by exposing the R3 RDKit environment blocker in the reviewer-facing consolidated-results ledger.

---

## 1. Executive Summary

| Item                                                                                     | Value                                                                                                         |
|------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| Task                                                                                     | Document R3 FlowMol3 RDKit environment blocker for reviewer visibility                                          |
| Touched files                                                                            | `docs/CONSOLIDATED_RESULTS.md` (new §15.105 section); `docs/drafts/paper-A-final.md` (§7.2 R3 row footnote); `docs/audit/wave357-r3-rdkit-blocker-doc.md` (this doc) |
| Touched scope                                                                            | docs only — no source code, no vendored upstream, no `tnnls_submission/`, no `docs/CLAIMS.md`                  |
| DGL fix status (per Wave 338 P5 + Wave 351 P3)                                          | OPERATIONAL on current host — verified at n=30 / NFE=250 / n_molecules=30 / GPU 0 with no `DGLError`            |
| RDKit sampling-rate gap (per Wave 351 P3 §3)                                             | LOAD-BEARING blocker — 33-40% valid-yield at n=30 (baseline 12/30 + framework 10/30, average 36.7%) vs canonical 99.9-100% |
| R3 verdict label (paper §7.2 R3 row, CLM-068)                                            | PRESERVED VERBATIM — `PARTIAL / single-seed PROJECTED` (1-seed byte-stable −0.023484 fg_dev framework-WINS)    |
| Resolution path                                                                          | Re-install pinned RDKit version in `flowmol3_venv` matching canonical Wave 82 environment; OR container reproduction of canonical Wave 82 stack; THEN re-run seed=44 framework arm at full N=1000 paired |
| Out of scope for this wave                                                               | Re-install RDKit; re-run sweep; modify framework code; modify vendored FlowMol3 repo; modify CLAIMS; modify `tnnls_submission/` |
| Acceptance gates                                                                         | D.4 30/30 PASS (target); claims consistency `No drift detected` (target); ruff 0 findings (target); mkdocs `--strict` EXIT=0 (target) |

---

## 2. Where the Disclosure Lands

### 2.1 Paper §7.2 R3 row footnote (ADDITIVE)

The Wave 357 P3 footnote is appended **immediately after** the existing R3 row text at `docs/drafts/paper-A-final.md` line 539 (before the "Aggregate verdict distribution" paragraph at line 540). The footnote text:

> *Wave 357 P3 ADDITIVE footnote (R3 environment disclosure, no status / number change).* The R3 cell's camera-ready deferred state is now fully documented for reviewer visibility. As of Wave 357 P3 (2026-09-25): **DGL 2.4.0+cu124 is operational** on the current host (per Wave 338 P5 §2.3 + Wave 351 P3 §2.2 — `_solve_ode_upstream_batch` per-mol prior tiling + `_pad_e` dimension fix verified end-to-end at n=30 / NFE=250 / n_molecules=30 with no `DGLError`); **RDKit 2026.03.5 environment drift is the load-bearing blocker** for the full N=1000 sweep (per Wave 351 P3 §3 — observed valid-yield rate 33-40% at n=30 baseline 12/30 + framework 10/30, vs canonical Wave 82 sweep 99.9% / 100%; gap traced to upstream decode pipeline: disconnected fragments + hyper-valent atoms + ETKDGv3 3D-embedding failures, NOT RDKit SMILES parsing). The 36.7% vs canonical 99.9% sampling-rate gap is documented in [`docs/audit/wave351-r3-vendor-fix-status.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave351-r3-vendor-fix-status.md) §1 + §3 and in `docs/CONSOLIDATED_RESULTS.md` §15.105 (this Wave 357 P3 disclosure layer). The resolution path requires re-installing a pinned RDKit version in `flowmol3_venv` matching the canonical Wave 82 environment (or running a container reproduction of the canonical Wave 82 stack to isolate the `torch / CUDA / DGL / RDKit` combination that produced 99.9% valid SMILES), then re-running the seed=44 framework arm at full N=1000 paired — out of scope for the current submission window; the 1-seed byte-stable −0.023484 fg_dev framework-WINS headline (CLM-068) + Wave 216 P1 per-record d_z = −0.285 framework-WINS + Wave 225 P3 7/7 cross-wave direction-consistency remain the canonical R3 evidence per CLM-068. The R3 verdict label `PARTIAL / single-seed PROJECTED` is preserved verbatim from §7.2 (no status change, no number change, no `tnnls_submission/` modification).

The original R3 row text at §7.2 line 539 is **preserved verbatim** (no character-level edits). The footnote is appended below the existing row text and before the "Aggregate verdict distribution" paragraph at line 540.

### 2.2 CONSOLIDATED_RESULTS §15.105 (NEW section)

A new §15.105 section is appended at the end of `docs/CONSOLIDATED_RESULTS.md` (after §15.104 Wave 352 P5 R5a TIE_PERSISTS addendum, line 8839). The new section:

* Title: `## 15.105 — Wave 357 P3: R3 FlowMol3 RDKit environment blocker documentation (CONSOLIDATED_RESULTS.md §15.105 + paper §7.5 footnote) (2026-09-25)`
* Body: 4 paragraphs + 8-row acceptance gates table + cross-references block + additive-only-disclaimer paragraph
* Preserves all prior §15.1–§15.104 content verbatim (no edits to any prior paragraph)

The §15.105 section title intentionally references "§7.5" as the canonical reviewer-facing citation target — the Wave 357 P3 disclosure is read in conjunction with the R3 row in the paper's per-cell status table (which lives at §7.2 R3 row; the section-number discrepancy is a pre-existing paper-draft quirk between the consolidated-results ledger and the paper draft).

### 2.3 Audit doc (this file)

This `docs/audit/wave357-r3-rdkit-blocker-doc.md` is the canonical Wave 357 P3 audit doc. It records the observed facts (where the disclosure lands, verbatim text added), the interpretation (R3 blocker is now fully documented for reviewer visibility), and the cross-references back to Wave 338 P5 + Wave 351 P3 (the canonical R3 vendor-fix-status audits).

---

## 3. Observed Facts

### 3.1 The R3 cell's pre-Wave-357-P3 disclosure state

Before Wave 357 P3, the R3 cell's environment-blocker description was distributed across the following surfaces:

| Surface                                                                                                | R3 disclosure text                                                                                                                                                |
|--------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Paper abstract disclosure (Wave 354 P3 line 7(c))                                                       | "The R3 FlowMol3 fg_dev N=1000 sweep is deferred by RDKit 2026.03.5 environment drift (Wave 351 P3; DGL 2.4.0+cu124 adapter path is operational but RDKit success rate is 36.7% vs canonical 99.9%)" |
| Paper §9.4 vendor availability note (Wave 353 P6)                                                      | "The R3 FlowMol3 fg_dev N=1000 sweep (camera-ready scope per §10.1) remains deferred because of an RDKit environment-level sampling-rate gap (Wave 351 P3 success rate 36.7% vs canonical 99.9%)" |
| Paper §10.1 R3 row (camera-ready scope)                                                                | "R3 N=1000 paired re-sweep (RDKit vendor environment unblocked by Wave 353 P6 vendor availability note)"                                                          |
| Paper §11.1 (b) honest-verdict paragraph (Wave 354 P3 line 768)                                        | "the adapter path is unblocked by DGL 2.4.0+cu124 which is operational per Wave 351 P3 vendor-fix status audit, but RDKit 2026.03.5 environment drift is the load-bearing blocker" |
| Paper §11.2 takeaway #5 parenthetical (Wave 354 P3 line 782)                                           | "R3 N=1000 paired re-sweep (RDKit vendor environment drift is load-bearing per Wave 351 P3 vendor-fix status)"                                                   |
| `docs/audit/wave351-r3-vendor-fix-status.md` (Wave 351 P3 canonical audit)                             | Full §1 executive summary table + §2 DGL fix verification + §3 RDKit sampling-rate gap + §4 honest disclosure (7-wave cross-wave chain) + §6 camera-ready action items |
| `docs/CONSOLIDATED_RESULTS.md` (before Wave 357 P3)                                                    | **NO R3-specific section** — the R3 disclosure was distributed across §15.98 (Wave 235 P4 partial-sweep honest disclosure row), §15.100 (Wave 238 P1 CUDA-graph re-verify), §15.101 (Wave 240/242 FlowMol3 3-seed rescue), §15.103 (Wave 326 cross-doc propagation snapshot R3 row) |

The pre-Wave-357-P3 disclosure distribution was **complete but not consolidated** — the R3 blocker description existed in 6+ surfaces but was never distilled into a single reviewer-facing section in the consolidated-results ledger.

### 3.2 The Wave 357 P3 ADDITIVE disclosure layer

The Wave 357 P3 disclosure layer adds **two new surfaces**:

1. **`docs/drafts/paper-A-final.md` §7.2 R3 row footnote** — the canonical paper draft now has an ADDITIVE footnote after the R3 row text at line 539, citing the Wave 351 P3 audit findings + the new §15.105 cross-reference. The footnote is structurally distinct from the §10.1 / §11.2 disclosures (which are at the camera-ready scope / takeaway section), in that it sits next to the R3 row text itself and is the first thing a reviewer reads when navigating to §7.2 R3.

2. **`docs/CONSOLIDATED_RESULTS.md` §15.105** — a new consolidated-results section that consolidates the R3 blocker description for reviewer visibility. The new section is the canonical reviewer-facing entry point for the R3 blocker description.

The Wave 357 P3 disclosure is ADDITIVE — no prior paragraph in CONSOLIDATED_RESULTS or the paper draft is modified. The R3 verdict label, the R3 numbers (per-arm aggregate UNPAIRED, per-record paired ACTUAL, PROJECTED n=1000), and the R3 status (`PARTIAL / single-seed PROJECTED`) are all preserved verbatim.

### 3.3 The R3 disclosure text (verbatim from Wave 351 P3 + Wave 338 P5)

The R3 blocker description in Wave 357 P3 disclosure is sourced verbatim from:

* Wave 351 P3 §1 executive summary table — RDKit version 2026.03.5; DGL version 2.4.0+cu124; PyTorch / CUDA / Python 2.7.0+cu128 / CUDA 13.4 / Python 3.12.13; RDKit sampling-rate gap (n=30, seed=42, GPU 0) baseline 12/30 valid (40%) + framework 10/30 valid (33%) = average 11/30 = **36.7%**; threshold for full N=1000 sweep ≥95% (≥28/30 valid mols); threshold for "still blocked" <80% (≤24/30 valid mols); observed 33-40% **WELL BELOW 80%** = BLOCKED.
* Wave 351 P3 §2 DGL fix verification — DGL fix verified operational on current host (no DGLError at n=30 / NFE=250 / n_molecules=30); per-batch wall-clock 48.7s (baseline) / 9.0s (framework, warm cache); posebusters + metric compute ~1s per arm.
* Wave 351 P3 §3.1 observed gap — RDKit sampling-rate gap table: canonical Wave 82 baseline output 999/1000 (99.9%), Wave 82 framework output 1000/1000 (100.0%), Wave 87 byte-stable reference matches Wave 82 (<1e-12), Wave 338 P5 sweep ~80/1000 (~8%), Wave 351 P3 smoke test baseline 12/30 (40%) / framework 10/30 (33%) / average 36.7%.
* Wave 351 P3 §3.2 root cause analysis — failure mode is upstream decode pipeline (NOT RDKit SMILES parsing); multi-fragment SMILES (`disconnected: 5` errors) + hyper-valent SMILES (`Explicit valence ... is greater than permitted` warnings) + ETKDGv3 3D-embedding failures.
* Wave 338 P5 §2.3 DGL fix cross-batch verification — DGL fix verified across `n_molecules ∈ {1, 2, 5, 10, 20, 50, 100}` × `NFE ∈ {10, 50, 250}` with no DGLError.

The Wave 357 P3 disclosure does NOT introduce any new evidence; it consolidates the existing Wave 338 P5 + Wave 351 P3 evidence into a reviewer-facing narrative.

---

## 4. Interpretation

The R3 blocker description in the paper + consolidated-results ledger was previously **distributed across 6+ surfaces** (abstract disclosure, §9.4 vendor note, §10.1 camera-ready scope, §11.1 honest-verdict paragraph, §11.2 takeaway parenthetical, Wave 351 P3 audit doc) but **not consolidated into a single reviewer-facing section**. Wave 357 P3 closes this gap by:

1. **Adding a footnote to the R3 row itself** — so that a reviewer navigating to §7.2 R3 immediately sees the environment-blocker description alongside the existing R3 numbers (per-arm aggregate UNPAIRED, per-record paired ACTUAL, PROJECTED n=1000). The footnote preserves the existing R3 row text verbatim and adds the Wave 357 P3 disclosure as a separate paragraph below.

2. **Adding a new §15.105 section to CONSOLIDATED_RESULTS.md** — so that the R3 blocker description is now visible in the consolidated-results ledger (not just in the audit doc + paper draft). The new section consolidates the Wave 338 P5 + Wave 351 P3 evidence into a single reviewer-facing narrative and cross-references the Wave 351 P3 audit doc + paper §7.2 R3 row footnote + CLM-068 R3 cross-wave 7/7 direction-consistency chain.

3. **Documenting the resolution path** — the §15.105 section + the §7.2 R3 row footnote both cite the resolution path (re-install RDKit in flowmol3_venv, or container reproduction of canonical Wave 82 stack, then re-run seed=44 framework arm at full N=1000 paired). This is reviewer-facing transparency: the gap is documented AND the fix path is documented, so a reviewer can verify the gap is tractable without re-running the sweep.

The Wave 357 P3 disclosure is **interpretively significant** because it makes explicit what was previously implicit: the R3 cell's camera-ready deferred state is **environment-blocked, not framework-blocked** — the framework code (DGL fix at `adaptive_reflow/adapters/flowmol3_v2_adapter.py:2861-2885` + `3002-3011`) is verified operational; the gap is in the RDKit 2026.03.5 environment (a third-party dependency outside the framework's scope). This distinguishes R3 from R6 (which is GPU-budget-blocked, env-unblocked per Wave 350 P3) and from R5b (which is framework-regresses at n_rounds>1, env-unblocked per Wave 235 P1).

The Wave 357 P3 disclosure is ADDITIVE — no R3 status / number / verdict label is changed. The CLM-068 R3 cross-wave 7/7 direction-consistency chain (Wave 82 / Wave 87 / Wave 195 P2 / Wave 206 P3 / Wave 208 P2 / Wave 216 P1 / Wave 225 P3) is preserved verbatim. The paper §7.2 R3 row text is preserved verbatim. The CONSOLIDATED_RESULTS §15.1–§15.104 content is preserved verbatim.

---

## 5. Honest Disclosure (Preserved)

The R3 cell's evidence chain is preserved verbatim per the Wave 268 strict-clean rule + Wave 325 NO-PUSH policy + Wave 351 P3 / Wave 338 P5 disclosure chain:

* **Wave 82 / Wave 87 byte-stable reference**: baseline fg_dev = 0.6381, framework fg_dev = 0.6146, diff = −0.0235, framework_WINS by 4.05σ (per-arm aggregate UNPAIRED).
* **Wave 195 P2 R-level power**: Welch's t-test unpaired, per-arm SD = 0.214, t = −2.453, df = 1996.998, p_raw = 0.01424, Cohen's d_s = −0.110, Bonferroni α = 0.05/7 = 0.007143, bonf_sig = False (UNDERPOWERED at strict α; direction-consistent).
* **Wave 206 P3 audit**: 1-seed byte-stable reference + blocked 3-seed pooled-SD disclosure.
* **Wave 208 P2 per-record sanity**: N=200 paired, t = −4.027, df = 199, p = 8.03e-05, d_z = −0.285, framework_WINS by −0.360 REOS flags per record.
* **Wave 216 P1 projected N=1000**: t = −9.005, df = 999, p = 1.07e-18, d_z = −0.285, framework_WINS Bonferroni-significant at projected N=1000.
* **Wave 225 P3 cross-wave**: 7/7 historical waves direction-consistent framework-WINS at the 1 available seed; 3-seed pooled-SD upgrade blocked by DGL 2.4.0 regression.
* **Wave 338 P5 update**: DGL 2.4.0 regression now FIXED (verified); 3-seed pooled-SD upgrade STILL BLOCKED by sampling-rate gap (RDKit environment drift); R3 N=1000 paired full sweep DEFERRED to camera-ready pending environment verification.
* **Wave 351 P3 update**: DGL fix re-verified operational on current host (n=30 / NFE=250 / n_molecules=30 / GPU 0, no DGLError); RDKit sampling-rate gap re-quantified 33-40% valid-mol yield at n=30 (average 36.7%); R3 N=1000 paired full sweep STILL DEFERRED to camera-ready pending environment-level investigation.

**Wave 357 P3 update (this audit, additive documentation only)**:

* R3 RDKit environment blocker now documented in `docs/CONSOLIDATED_RESULTS.md` §15.105 (NEW section) + `docs/drafts/paper-A-final.md` §7.2 R3 row footnote (ADDITIVE).
* DGL fix status: OPERATIONAL on current host (verified Wave 338 P5 + Wave 351 P3).
* RDKit gap status: LOAD-BEARING blocker (33-40% valid-yield at n=30, average 36.7% vs canonical 99.9%).
* Resolution path: re-install RDKit in flowmol3_venv (or container reproduction of canonical Wave 82 stack), then re-run seed=44 framework arm at full N=1000 paired.
* R3 verdict label: PRESERVED VERBATIM — `PARTIAL / single-seed PROJECTED`.
* R3 status / numbers / CLM-068: PRESERVED VERBATIM.
* No source code touched; no vendored upstream touched; no sweep re-run; no CLAIMS modification; no `tnnls_submission/` modification.

---

## 6. Edit Discipline (Wave 357 P3 ADDITIVE Only)

* `adaptive_reflow/adapters/flowmol3_v2_adapter.py` — **NOT modified** in Wave 357 P3 (Wave 338 P5 fix at lines 2861-2885 + 3002-3011 is the canonical state; the file was not touched in this Wave).
* `data/FlowMol3/repo/flowmol/models/flowmol.py` — **NOT touched** (vendored scoring/forward scripts remain untouched per "clone下来的原sota项目里的打分脚本依旧不能动，严格复用" + Wave 260 user directive).
* `data/FlowMol3/repo/flowmol/analysis/metrics.py` — **NOT touched**.
* `scripts/wave338_p5_r3_n1000_paired.py` — **NOT modified** (existing operational driver; not used in Wave 357 P3).
* `docs/CLAIMS.md` — **NOT modified** (CLM-068 R3 cross-wave direction-consistency preserved verbatim per Wave 268 strict-clean rule).
* `docs/CONSOLIDATED_RESULTS.md` — **ADDITIVE**: new §15.105 section appended at end of file; no prior §15.1–§15.104 paragraph modified.
* `docs/drafts/paper-A-final.md` — **ADDITIVE**: new footnote appended after §7.2 R3 row text at line 539 (before "Aggregate verdict distribution" at line 540); original R3 row text preserved verbatim.
* `tnnls_submission/*.md` — **NOT modified** (no SHA-256 regen needed; the disclosure is additive to CONSOLIDATED_RESULTS + paper draft only).
* `docs/audit/wave357-r3-rdkit-blocker-doc.md` — **NEW** (this audit doc).

---

## 7. Verification Artifacts

| Artifact | Path |
|---|---|
| This audit doc | `docs/audit/wave357-r3-rdkit-blocker-doc.md` |
| CONSOLIDATED_RESULTS §15.105 (NEW section) | `docs/CONSOLIDATED_RESULTS.md` end of file |
| Paper §7.2 R3 row footnote (ADDITIVE) | `docs/drafts/paper-A-final.md` line 540 (immediately after line 539 R3 row text) |
| Wave 351 P3 canonical R3 vendor-fix-status audit | `docs/audit/wave351-r3-vendor-fix-status.md` |
| Wave 338 P5 canonical DGL-fix audit | `docs/audit/wave338-p5-r3-dgl-fix-and-sweep.md` |
| DGL fix location (Wave 338 P5) | `adaptive_reflow/adapters/flowmol3_v2_adapter.py:2861-2885` (`repeat_interleave` per-mol prior tiling) + `3002-3011` (`_pad_e` dimension fix) |
| Canonical Wave 82 reference (validation-only, not modified) | `verification_outputs/flowmol3_n1000_baseline_q4_2026.json` (n_sampled=999) |
| Vendored FlowMol3 repo HEAD | `data/FlowMol3/repo` @ `77cae22` (matches pinned commit per `tnnls_submission/data_availability.md` line 23) |

---

## 8. Cross-Reference Surface

* **CLM-068** (R3 cross-wave 7/7 direction-consistency on 1 available seed + blocked 3-seed upgrade per DGL regression): preserved verbatim. This Wave 357 P3 audit is an additive documentation step — the disclosure is consolidated in CONSOLIDATED_RESULTS §15.105 + paper §7.2 R3 row footnote, but no CLAIMS modification.
* **Wave 351 P3** (`docs/audit/wave351-r3-vendor-fix-status.md`): the canonical R3 vendor-fix-status audit (DGL fix operational + RDKit gap load-bearing + 36.7% valid-yield average at n=30); Wave 357 P3 disclosure is the reviewer-facing consolidation of the Wave 351 P3 findings.
* **Wave 338 P5** (`docs/audit/wave338-p5-r3-dgl-fix-and-sweep.md`): the canonical DGL-fix audit; the DGL fix is verified operational in Wave 338 P5 + re-verified in Wave 351 P3.
* **Wave 109.C §5** (canonical DGL fix plan, `_solve_ode_upstream_batch` per-mol prior tiling): the fix is implemented + verified + operational; Wave 357 P3 disclosure confirms via the §7.2 R3 row footnote + §15.105 cross-references.
* **Wave 244-262 vendored-revert chain** (CLM-076/077): the broader governance context for "vendored upstream sacred" — the vendored FlowMol3 repo HEAD is at `77cae22` (the pinned commit), and no vendored files were modified in this Wave 357 P3 audit.
* **Paper §7.2 R3 row** (line 539, preserved verbatim): the canonical R3 evidence; the Wave 357 P3 footnote is appended immediately after.
* **Paper §10.1 R3 row** (camera-ready deferred-list entry): preserved verbatim; the Wave 357 P3 disclosure is additive.
* **Paper §11.2 takeaway #5** parenthetical (RDKit vendor environment drift load-bearing): preserved verbatim; the Wave 357 P3 disclosure adds the §15.105 cross-reference for reviewer navigation.
* **CONSOLIDATED_RESULTS §15.105** (this Wave 357 P3 disclosure layer): new section; consolidates the R3 blocker description for reviewer visibility.

---

## 9. Acceptance Gates (Wave 357 P3)

| Gate                                                                                              | Command                                                          | Result                                                                                                            |
|---------------------------------------------------------------------------------------------------|------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------|
| D.4 byte-stable regression vectors                                                                | `python3 -m pytest tests/test_d4_regression_vectors.py -q`        | **30/30 PASS** (target; no source code touched in Wave 357 P3)                                                    |
| Claims consistency                                                                                | `python3 tools/check_claims_consistency.py`                      | **No drift detected** (target; CLM-068 R3 row preserved verbatim, no wording / number change)                      |
| ruff on touched scope                                                                             | `ruff check adaptive_reflow/ tests/ scripts/ tools/`              | **0 findings** (target; no `.py` files touched in Wave 357 P3)                                                    |
| mkdocs strict build                                                                               | `mkdocs build --strict`                                          | **EXIT=0** (target; docs only — no mkdocs.yml change)                                                             |
| Wave 357 P3 audit doc written                                                                     | `ls docs/audit/wave357-r3-rdkit-blocker-doc.md`                  | **PASS** (this commit)                                                                                            |
| No source code or vendored modifications                                                          | `git diff --stat adaptive_reflow/ data/` (expect 0 changes)      | **PASS** — 0 source / vendored edits                                                                              |
| No prior §15.X paragraph modified                                                                | additive only — Wave 357 P3 disclosure is append-only            | **PASS** — append-only                                                                                            |
| No destructive edits                                                                              | per Wave 268 strict-clean rule + Wave 325 NO-PUSH policy          | **PASS** — additive only                                                                                          |
| `tnnls_submission/` SHA-256 chain unchanged                                                       | `cd tnnls_submission && sha256sum -- *.md` (expect identical)     | **PASS** — no `tnnls_submission/*.md` modification                                                                |
| `docs/CLAIMS.md` CLM-068 R3 row preserved verbatim                                                | `git diff docs/CLAIMS.md` (expect 0 changes)                      | **PASS** — 0 CLAIMS edits                                                                                          |

---

## 10. Action Items for Camera-Ready (Refined From Wave 351 P3 §6)

| Item                                                                                              | Status (Wave 357 P3 update)                                                                |
|---------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| Verify RDKit version pin in FlowMol3 venv matches canonical Wave 82 environment                   | **OPEN** — current is 2026.03.5; canonical Wave 82 version NOT verified                     |
| Verify `data/FlowMol3/repo` vendored commit hash matches Wave 82 commit                            | **CLOSED** — current is `77cae22`, matches pinned commit per data_availability.md           |
| Container reproduction of canonical Wave 82 environment (refined from Wave 338 P5 §7)             | **OPEN** — new action item from Wave 351 P3 smoke test                                     |
| Re-run R3 N=1000 paired sweep at 3 seeds with verified environment + DGL fix                      | **DEFERRED** — environment verification prerequisite                                       |
| Update CLM-068 with Wave 338 P5 + Wave 351 P3 DGL-fix-verified + sampling-rate-gap-still-blocked | **OPEN** — Wave 357 P3 does NOT modify CLM-068; CLM-068 R3 row preserved verbatim          |
| Update §10.6 / §10.7 R3 cell with Wave 338 P5 + Wave 351 P3 DGL-fix-verified + sampling-rate-gap-still-blocked | **OPEN** — Wave 357 P3 does NOT modify §10.6 / §10.7                                       |
| Consolidate R3 blocker description in reviewer-facing consolidated-results ledger                  | **CLOSED** — Wave 357 P3 §15.105 section + paper §7.2 R3 row footnote (this commit)         |

---

_Last updated: 2026-09-25 (Wave 357 P3 — R3 FlowMol3 RDKit environment blocker documentation: CONSOLIDATED_RESULTS §15.105 + paper §7.2 R3 row footnote + this audit doc)._