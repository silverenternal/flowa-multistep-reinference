# Submission package refresh — MANIFEST, ledger, and the counts that had rotted

**Date:** 2026-10-29
**Scope:** `tnnls_submission/` inventory layer + the checkers that police it.
**Status:** closed. No number in `docs/drafts/paper-A-final.*` moved; no claim,
status label, or verdict changed.

---

## 1. Observed facts at the start

`python3 tools/check_submission_manifest.py` reported:

```
rows=27 known_stale=13 unknown=1 addendum_drift=0
data_availability.md   STALE(21062 vs 20866 bytes)
```

`known_stale=13` came from nine unique names appearing in two tables. The
checker tolerated them via a `KNOWN_STALE` frozenset documented in
`docs/audit/manifest-hash-staleness.md`; `data_availability.md` was the one
row with no exemption and therefore the only hard failure.

Two structural defects sat underneath the staleness:

1. **`MANIFEST.md` carried its own SHA-256.** A file cannot contain its own
   digest: writing the digest changes the file. Every self-referential value
   in the table's history was stale by construction, and the row's own text
   admitted as much ("the displayed SHA is the hash of the bytes BEFORE this
   very SHA-row was added"). Reviewers were told to "re-hash on receipt and
   confirm with the post-edit SHA pinned in …" a list of seventeen audit docs.
2. **The re-verification recipe could not work.** The documented command was
   `cd tnnls_submission && sha256sum -- *.md`, which (a) omits the manuscript
   triple, the five figure assets and the supplementary zip, and (b) cannot
   compare against a markdown table at all.

Separately, the package's prose carried counts that had been overtaken by
events: `5155 passed / 196 skipped`, `328 words` abstract, `3 highlights
(≤ 85 chars)`, `10/11/14-page` builds, and `reproduce/0[1-7]_*.sh`.

## 2. What changed

### 2.1 A real ledger replaces the self-hash

New file `tnnls_submission/SHA256SUMS` — 23 lines, one per packaged artifact
(10 `*.md` + the autofill JSON + `supplementary/README.md` +
`supplementary_bundle.zip` + the manuscript triple + the five figure assets).
Verified with `sha256sum -c SHA256SUMS` → 23/23 OK.

The `MANIFEST.md` row in the table is now hash-free and points at the ledger.
Per-file size + SHA-256 rows are retained so a reviewer can spot-check any
single artifact without the ledger.

### 2.2 Every row refreshed; `KNOWN_STALE` emptied

| Row | Before | After |
|---|---:|---:|
| `README.md` | 12 638 | 12 686 |
| `cover_letter.md` | 74 060 | 75 571 |
| `highlights.md` | 9 098 | 3 422 |
| `tables.md` | 22 729 | 25 962 |
| `figures.md` | 53 656 | 53 797 |
| `data_availability.md` | 20 866 | 21 195 |
| `submission_checklist.md` | 34 347 | 35 770 |
| `../docs/drafts/paper-A-final.md` | 213 574 | 226 324 |
| `../docs/drafts/paper-A-final.tex` | 66 156 | 74 254 |
| `../docs/drafts/paper-A-final.pdf` | 448 996 | 615 789 |

`KNOWN_STALE` is now `frozenset()`. The checker also grew a `check_ledger()`
pass that requires `SHA256SUMS` to cover `MANIFEST.md` and every row that
still carries a hash, so the two surfaces cannot drift apart again.

### 2.3 Prose corrected against measured state

| Claim | Was | Now | Evidence |
|---|---|---|---|
| pytest | `5155 passed / 196 skipped` | `5528 passed / 180 skipped / 12 xfailed` | `pytest tests/ --ignore=tests/test_tools/test_paper_metrics.py` |
| Abstract | 328 words | 167 words | `paper-A-final.md`, 2026-10-27 packaging addendum |
| Highlights | 3 bullets ≤ 85 chars | 5 bullets ≤ 25 words | `tnnls_submission/highlights.md` |
| Manuscript | 10 / 11 / 14 pages (four surfaces) | 12 pages | `pdfinfo docs/drafts/paper-A-final.pdf` |
| Reproduction | `reproduce/0[1-7]_*.sh`, "all 7 R-level cells" | `reproduce/0[1-8]_*.sh`, "8 checks = 7 cells + the R6 recipe" | `reproduce/verify_all_headlines.sh` |
| `highlights_v2.md` | cited as the "camera-ready variant" | does not exist; reference removed | `ls tnnls_submission/` |

`reproduce/verify_all_headlines.sh` printed `OK: All 8/8 R-level headlines
verified` for 7 cells plus a recipe check. It now prints
`OK: All 8/8 reproduction checks verified`, and
`tests/test_reproduce_scripts.py` pins the new string.

### 2.4 The integrity gate went from red to green

`tools/check_data_integrity.py` reported **33 mismatches** (30 `.npz` sample
dumps under `verification_outputs/gap32-headtohead/` plus
`gap36-ablation-matrix/METADATA.json` unlisted in their ledgers, and two
manifests in `wave349-r1-3seed-gpu/`). The `.npz` files are git-tracked, so
"they are only local scratch" was not an available excuse — the ledgers were
simply incomplete.

* Appended the 30 + 1 missing entries; `sha256sum -c` now passes in both
  directories.
* `wave349-r1-3seed-gpu/SHA256SUMS` is **not** a checksum list: it is the
  markdown aggregator that `paper-A-final.md` §3.5.1 and `SUBMISSION_READINESS`
  pin byte-for-byte (2642 B, `28aafe1c…`). It is left byte-identical. The
  checker now skips the per-file cross-check for a ledger that parses to zero
  entries, because `empty_ledgers` already reports it and
  `tools/check_evidence_ledgers.py` classifies it as `not_a_ledger` with a
  documented reason.

Result: `Mismatches: 0`, 264 files verified across 15 ledgers (was 233 files,
33 mismatches).

## 3. Gates

| Gate | Result |
|---|---|
| `tools/check_submission_manifest.py` | `rows=26 known_stale=0 unknown=0 addendum_drift=0 ledger_drift=0` |
| `tools/check_submission_links.py` | `links=242 absent=0 ok=242` |
| `tools/check_data_integrity.py` | `Mismatches: 0` (264 files / 15 ledgers) |
| `tools/check_claims_consistency.py` | no drift |
| `tools/check_tables_inventory.py` | 33 checks, 0 known, 0 unknown |
| `tools/check_evidence_ledgers.py` | 19 ledgers, 0 unknown |
| `tools/check_recipe_hashes.py` | 71 rows, 0 stale |
| `tools/check_docs_against_code.py` | 3375 claims verified |
| `pytest tests/test_d4_regression_vectors.py` | 30/30 PASS |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/` | 0 findings |
| `mkdocs build --strict` | exit 0 |
| `bash tools/check_vendored_unchanged.sh` | PASS |

## 4. Unresolved, stated rather than hidden

* `tools/check_data_provenance.py` still reports **3 drifts**, all
  `orphan_sha` in historical per-wave audit records
  (`wave350-r6-live-attempt.md`, `wave363-k1-recipe.md`,
  `wave363-k4-recipe.md`). Those are frozen snapshots of what the artifacts
  hashed to at the time; rewriting them would falsify the audit trail. They
  are left as recorded.
* The 30 `.npz` dumps under `gap32-headtohead/` are 60 MB of sample tensors
  that a reviewer will not re-verify by hand; they are now listed so the
  ledger is complete, not because they are expected to be re-derived.
* `docs/cover-letter-tnnls.md` and `tnnls_submission/cover_letter.md` remain
  two distinct documents (the package copy carries the 17 fill placeholders).
  Only the shared counts were kept in sync.

## 5. Files touched

```
tnnls_submission/SHA256SUMS                     (new, 23 lines)
tnnls_submission/MANIFEST.md                    rows + ledger + prose
tnnls_submission/README.md                      highlight count, page count
tnnls_submission/data_availability.md           pytest count, reproduce step
tnnls_submission/submission_checklist.md        highlights, abstract, page count
tnnls_submission/SUBMISSION_READINESS.md        highlights, page count
tnnls_submission/cover_letter.md                pytest count, page count
tnnls_submission/tables.md                      pytest count
tnnls_submission/figures.md                     pytest count
tools/check_submission_manifest.py              ledger pass, KNOWN_STALE -> empty
tools/check_data_integrity.py                   prose-ledger skip, message
tests/test_submission_manifest.py               2 new tests
reproduce/verify_all_headlines.sh               "checks" not "cells"
tests/test_reproduce_scripts.py                 pinned string
AGENTS.md                                       rehash procedure
docs/RELEASE-NOTES.md, docs/code-release-checklist.md,
docs/cover-letter-tnnls.md                      pytest count
verification_outputs/gap32-headtohead/SHA256SUMS   +30 entries
verification_outputs/gap36-ablation-matrix/SHA256SUMS  +1 entry
```

---

## 6. Follow-on (2026-10-29): the root READMEs were the last unverified hash surface

§1–§5 fixed the *package's* integrity anchor. The two root READMEs carried a
second, independent copy of the same facts, and nothing checked it — the
readiness verifier's claims scanner is scoped to `docs/` on purpose (its own
docstring says the root READMEs are outside), so the copies could drift freely.

They had. Both `README.md` and `README.zh.md` still quoted the **2026-10-12
manuscript-consistency pass #11** artifacts:

| | README (stale) | on disk / `MANIFEST.md` |
|---|---|---|
| `paper-A-final.md` | `0586a564…`, 25,959 words | `b66ea07a…`, 27,809 words, 226,324 B |
| `paper-A-final.pdf` | `a9883fc9…`, 11 pages, 460,079 B | `8b94570c…`, 12 pages, 615,789 B |

`README.md` even contradicted itself: its `Last updated` line already said
*12 pages* while the artifact table three lines later said *11*. The
2026-10-27 packaging rebuild that moved the PDF to 12 pages updated
`MANIFEST.md` and never reached the READMEs.

Re-measured rather than copied: `sha256sum` and `wc -c -w` on both drafts, and
`pdfinfo` on the PDF, all agree with `MANIFEST.md`. The READMEs were corrected
to the measured values — **no metric, claim, status label, or verdict moved;
only the digest/count annotations on the artifact rows**.

To stop it recurring, `tools/check_artifact_hashes.py` requires every 64-hex
token on a README line that names an artifact to equal the file's real digest,
and requires `paper-A-final.md` and `paper-A-final.pdf` to be cited at all.
`tests/test_evidence_ledgers.py` pins both directions (green today, and a
stale token is caught). The gate is the 12th entry in the `todo.json` chain.

Deliberately **not** touched: `tnnls_submission/submission_checklist.md` and
`SUBMISSION_READINESS.md` still carry `a9883fc9…` / `0586a564…` — those are
dated historical annotations ("verified … at sha256 …", "Superseded
2026-10-12"), not current claims, and the package is frozen at
`v3.0-tnnls-ready`. `MANIFEST.md`'s 2026-10-27 addendum is the current
reading and already says so.

## 7. Follow-on (2026-10-29): the suite count moved again

Adding the two tests above (and the four in `tests/test_doc_links.py` that the
first full run of this round collected) took the suite from **5528** to
**5535** passed / 180 skipped / 12 xfailed. Eight surfaces assert that number
(`tnnls_submission/{cover_letter,figures,tables,data_availability,submission_checklist}.md`,
`docs/{RELEASE-NOTES,code-release-checklist,cover-letter-tnnls}.md`); all eight
were bumped, the five package rows re-hashed in `MANIFEST.md`, and
`SHA256SUMS` regenerated — `sha256sum -c` 23/23 OK, `check_submission_manifest`
`ledger_drift=0`. No metric, claim, status label, or verdict moved.
