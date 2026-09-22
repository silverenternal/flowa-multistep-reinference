# Wave 273 P1 — README State Audit

**Branch:** main
**Date:** 2026-09-22
**Scope:** README.md + README.zh.md audit. No source code, vendored code, CI
workflow, or background tasks touched.

---

## 1. File state

```
$ wc -l README.md README.zh.md
  301 README.md
  302 README.zh.md
  603 total
```

The two files are sibling structures of the same length (delta = 1 trailing
blank line in the ZH mirror). Both contain the same 15 TOC anchors; both
start with the language switcher banner `[English](README.md) | [中文](README.zh.md)` /
`[English](README.md) | [中文](README.zh.md)`. Section-by-section line parity
is intact across the two READMEs.

---

## 2. Consistency with repo structure

| Repo artifact | README reference | Reality | Status |
|---|---|---|---|
| `Dockerfile` (only) | `Dockerfile.tnnls` (4 README occurrences) | `Dockerfile` only exists; no `.tnnls` variant in git tree | **DRIFT** |
| `requirements-kanzi.txt` | `requirements_kanzi.txt` | hyphens not underscores | **DRIFT** |
| `requirements-lineageflow.txt` | `requirements_lineageflow.txt` | hyphens not underscores | **DRIFT** |
| `requirements-lock.txt` (canonical flowmol3_venv lock) | not referenced | README invents `requirements_flowmol3.txt` | **MISSING** |
| `.venvs/flowmol3_venv` (Python 3.12.13, torch 2.7.0+cu128) | `python3.11 -m venv .venvs/flowmol3_venv` | venv was created with python 3.12.13 via uv-managed CPython | **MINOR DRIFT** (recipe still works for `python3.11`/`python3.12`) |
| `.venvs/lineageflow_venv` (Python 3.12.13) | `python3.10 -m venv .venvs/lineageflow_venv` | venv was created with system `/usr/bin/python3.12` | **DRIFT** |
| `.venvs/kanzi_venv` (Python 3.12.13) | `python3.11 -m venv .venvs/kanzi_venv` | venv was created with uv-managed Python 3.12.13 | **MINOR DRIFT** |
| `reproduce/01_R1..07_R6_*.sh` (7 scripts) | matches | all 7 exist | OK |
| `reproduce/verify_all_headlines.sh` | matches | exists | OK |
| `tnnls_submission/{MANIFEST,cover_letter,highlights,tables,figures,data_availability,submission_checklist}.md` (7 files) | matches | all 7 exist | OK |
| `verification_outputs/wave218-p3-kanzi-framework-wins.json` | matches | exists | OK |
| `verification_outputs/wave216-p1-r3-per-record.json` | matches | exists | OK |
| `verification_outputs/wave235-p1-r5b-fix.json` | matches | exists | OK |
| `verification_outputs/wave235-p3-r6-uplift.json` | matches | exists | OK |
| `verification_outputs/g1_deep_dive_q3_2026.json` | matches | exists | OK |
| `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/SOURCE.md` | matches | exists | OK |
| `docs/audit/wave262-p{1,2,5}-*.md` | matches | all 3 exist | OK |
| `docs/audit/wave238-p3-journal-decision.md` | matches | exists | OK |
| `adaptive_reflow/adapters/{flowmol3,freqflow,graphbfn,hidream_i1,kanzi,lineageflow,lumina_image_2_0,mnist_fm,protbfn_abbfn,rectified_flow_cifar,reference_flowa,self_flow,synthetic,toy_gaussian,toy_linear,twodim_fm,wan2_2}.py` (≥ 17 concrete adapters) | "12 adapters" | ≥ 17 concrete adapters | **STALE COUNT** |

---

## 3. Badge audit

| Badge | EN README | ZH README | Consistent? |
|---|---|---|---|
| CI | yes | yes | yes |
| D.4 30/30 PASS | yes (no link target) | yes (no link target) | yes (consistent, but both `()` no-target) |
| License: MIT | yes (links to LICENSE) | yes (links to LICENSE) | yes |
| Python 3.12+ | yes (no link target) | yes (no link target) | yes |
| TNNLS | yes (no link target) | yes (no link target) | yes |
| Adapters (12) | yes (no link target) | yes (no link target) | yes — but counter stale (see §2) |

Three of six badges have empty `()` link targets — they render as visual
badges but are not clickable. Not a defect per spec, but a UX polish
opportunity.

---

## 4. R-cell consistency (EN vs ZH)

Spot-checked each of the 7 R-cells across both READMEs:

| Cell | EN `Δ` column | ZH `Δ` column | EN/Ver. link | ZH/Ver. link | Notes |
|---|---|---|---|---|---|
| R1 | +116.46% | +116.46% | matches | matches | OK |
| R2 | d_z = −0.0990 | d_z = −0.0990 | matches | matches | OK |
| R3 | d_z = −0.285 | d_z = −0.285 | matches | matches | OK |
| R4 | −78.25% | −78.25% | matches | matches | OK |
| R5 | −67.10% | −67.10% | matches | matches | OK |
| R5b | −2.53% to −0.66% on 3/4 schedulers | −2.53% to −0.66% on 3/4 schedulers | matches | matches | OK |
| R6 | +189% | +189% | matches | matches | OK |

All 7 R-cells are consistent between the two READMEs in numbers, units,
and verification links.

---

## 5. Submission package path

`## TNNLS Submission Package` (README.md:245, README.zh.md:245) lists all 7
files with SHA-256 prefixes and byte sizes, pointing at `tnnls_submission/`.
All 7 entries match the actual directory contents:

| Listed file | Real file | Size match |
|---|---|---|
| `MANIFEST.md` | exists | 5630 bytes (matches) |
| `cover_letter.md` | exists | 60394 bytes (matches) |
| `highlights.md` | exists | 1913 bytes (matches) |
| `tables.md` | exists | 7435 bytes (matches) |
| `figures.md` | exists | 23307 bytes (matches) |
| `data_availability.md` | exists | 4641 bytes (matches) |
| `submission_checklist.md` | exists | 7368 bytes (matches) |

The "Re-verify with `cd tnnls_submission && sha256sum -- *.md`" recipe at
README.md:261 / README.zh.md:261 is correct and matches what the MANIFEST
itself documents.

---

## 6. Duplicate sections

A grep for repeated H2 anchors across both READMEs returns nothing — every
`## ` heading appears exactly once per file. The level-3 subsections inside
`## Repository Structure` (A. Core Framework / B. Reproduction & Verification)
and `## Reproducing the Paper` (Per-cell table + Environment Setup) are
intentional nesting, not duplicates.

---

## 7. Acknowledgements / License / Contact

Both READMEs carry all three required closing blocks:

- **Acknowledgements** (README.md:284, README.zh.md:284) lists FlowMol3,
  LineageFlow, Kanzi with vendor URLs and commit SHAs. Matches the
  numerical-stability section's "vendored upstream" enumeration exactly.
- **License** (README.md:280, README.zh.md:280) is a single line
  "MIT — see [LICENSE](LICENSE)" linking to the actual file. LICENSE exists
  at the repo root.
- **Contact** (README.md:294, README.zh.md:294) points to
  `tnnls_submission/cover_letter.md` and a GitHub-issue/PR fallback. No
  email/ORCID/affiliation — appropriate for double-blind submission.

---

## 8. Identified remaining improvements

The following are the high-signal findings, ranked by impact (P1 = highest).

### P1 — Fix broken install/Dockerfile references in both READMEs

The Installation block (README.md:99-114, README.zh.md:99-114) tells reviewers
to run commands that do not work against the current tree:

1. `requirements_flowmol3.txt` — file does NOT exist. The canonical lockfile
   for the flowmol3_venv is `requirements-lock.txt`; there is no per-flowmol3
   recipe file. Reviewers who copy-paste will hit `ERROR: Could not open
   requirements file: [Errno 2] No such file or directory: 'requirements_flowmol3.txt'`.
2. `requirements_kanzi.txt` / `requirements_lineageflow.txt` — files exist
   but with hyphens (`requirements-kanzi.txt`, `requirements-lineageflow.txt`).
   The underscore variants will also fail with the same ENOENT.
3. `python3.10 -m venv .venvs/lineageflow_venv` — pyvenv.cfg shows the
   venv was actually created with `/usr/bin/python3.12`. The 3.10 recipe
   is harmless but stale.
4. `Dockerfile.tnnls` (README.md:167,229 + README.zh.md:167,229) — file
   does NOT exist; only `Dockerfile` exists in the repo root. Reviewers who
   run `docker build -f Dockerfile.tnnls -t flowa:tnnls-v3.0 .` will get
   `ERROR: unable to prepare context: path "Dockerfile.tnnls" not found`.

These four issues are part of the public-facing README (Tier-1 venue
reviewers will see them first). They each turn a documented
"copy-paste-to-verify" into an instant failure mode.

### P2 — Title drift between README header / Citation / MANIFEST

| Source | Title |
|---|---|
| README.md H1 | "FlowA: Training-Free, Paper-Quantity-Driven Re-Inference for Flow-Matching Checkpoints" |
| README.md bibtex (Citation) | "FlowA: Training-Free, Paper-Quantity-Driven Re-Inference for Flow-Matching Checkpoints" |
| `tnnls_submission/MANIFEST.md` | "FlowA: Training-Free, Paper-Quantity-Driven Re-Inference Control for Deployed Flow-Matching Checkpoints" |
| `tnnls_submission/cover_letter.md` Subject | "FlowA: Training-free, paper-quantity-driven …" |
| `cover_letter.md` (root) Re: line | "FlowA: Re-inference as Inference-Time Control for Frozen Flow-Matching Checkpoints" |

Three different titles in play. The README ↔ Citation agree, but the
MANIFEST adds "Control for Deployed", and the root `cover_letter.md` (a
historical draft) uses an entirely different formulation. TNNLS reviewer
correspondence will surface this if anyone cross-references.

### P3 — Stale "adapters-12" badge

The README's `[![Adapters](https://img.shields.io/badge/adapters-12-orange.svg)]()`
badge claims 12 adapters, but `ls adaptive_reflow/adapters/*.py | grep
-v shim | grep -v glue | …` returns ≥ 17 concrete adapters (flowmol3,
freqflow, graphbfn, hidream_i1, kanzi, lineageflow, lumina_image_2_0,
mnist_fm, protbfn_abbfn, rectified_flow_cifar, reference_flowa, self_flow,
synthetic, toy_gaussian, toy_linear, twodim_fm, wan2_2). The count was
correct at Wave 33 but has grown since. The badges are consistent with
each other (both 12) but neither matches reality.

### P4 — Three empty-link badges

`D.4 30/30 PASS`, `Python 3.12+`, `TNNLS`, and `Adapters-12` all have
empty `()` link targets. They render as shields but are not clickable.
A trivial UX polish — point `D.4` at `tests/test_d4_regression_vectors.py`,
`Python` at `pyproject.toml`, `TNNLS` at `tnnls_submission/`, `Adapters` at
`adaptive_reflow/adapters/__init__.py` or `docs/ADAPTER_INTERFACE_SPEC.md`.

### P5 — Stale Python version pin

README.md:7 says `Python 3.12+`, matching `pyproject.toml: requires-python =
">=3.12"`. CI matrix uses `["3.12", "3.13"]`. The badge is correct.

But the install recipe `python3.11 -m venv .venvs/flowmol3_venv` /
`python3.11 -m venv .venvs/kanzi_venv` / `python3.10 -m venv .venvs/lineageflow_venv`
uses Python 3.10/3.11, contradicting the 3.12+ badge. The actual venvs
on disk are all Python 3.12.13 (per `pyvenv.cfg`). Either the badge or
the install commands need to change for consistency.

---

## 9. Hard-rules compliance

- **DO NOT modify framework source code** — HONORED. Only this audit
  document is created.
- **DO NOT modify vendored code** — HONORED. No `data/` files modified.
- **DO NOT touch background tasks** — HONORED. No `todo.json` / `todo/`
  modifications.
- **DO preserve D.4 30/30 PASS** — PRESERVED. No Python source touched.
- **DO preserve mkdocs 0 warnings** — PRESERVED. No `mkdocs.yml` /
  `docs/` changes.
- **DO preserve claims consistency no drift** — PRESERVED. No
  `docs/CLAIMS.md` changes.
- **DO NOT introduce any new internal IDs** — HONORED. This audit uses
  the conventional `Wave 273 P1` identifier on a single new audit doc
  inside `docs/audit/`, mirroring the established naming pattern.

---

## 10. Summary

README.md (301 lines) and README.zh.md (302 lines) are structurally
complete: language switcher, 15-section TOC, headline table, architecture
diagram, install/quickstart/reproduce sections, repository structure
diagram, submission gates, data availability, numerical stability,
TNNLS submission package, citation, license, acknowledgements, contact.
R-cell rows (R1–R6, R5b) are EN/ZH-consistent in numbers and verification
links. Submission package references match the real `tnnls_submission/`
directory. No duplicate sections.

The four high-impact items remaining for Wave 273 follow-up are the
broken install/Dockerfile references (P1), the title drift across
docs (P2), the stale 12-adapter badge (P3), and the empty-link badges
(P4). All are localized README edits; none touches framework source,
vendored code, CI workflows, or background tasks.
