# Documentation and log inventory — 2026-10-21

**Why this exists.** The user asked for a full pass over the project's
documentation and logs, with an explicit split between what is useful and what
is not. This record states the classification, what was moved, what was
deliberately left alone, and the hygiene findings that are still open.

**Scope:** everything under `docs/`, the repo-root `*.md` files, and
`verification_outputs/`. Excluded by policy: `data/**` (9 vendored upstream
repos, byte-identical), `docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**` (frozen surfaces).

---

## 1. Classification

Four tiers. The test for each is stated so it can be re-applied.

| tier | test | treatment |
|---|---|---|
| **LIVE** | in the `mkdocs.yml` nav, or cited by a frozen surface, or read by tooling | keep in place; a path change needs a nav/link update in the same commit |
| **EVIDENCE** | a result artifact or an audit record with an inbound reference from a live surface or a closed gap | keep in place; never archived |
| **HISTORICAL** | superseded, but still cited by historical audit records | move to `docs/ARCHIVE/`; leave the historical citations pointing at the old path (they describe where the file was) |
| **JUNK** | build intermediates, scratch trees, generated caches | safe to delete or archive |

The reference graph was computed by counting inbound `audit/<name>.md` links
across every `.md`/`.py`/`.yml`/`.sh`/`.json`/`.tex` file in the repo
(9,988 files scanned, `data/`, `.venvs/`, `.git/`, `site/`,
`verification_outputs/` excluded).

---

## 2. Surface map

| surface | size | verdict | notes |
|---|---:|---|---|
| repo root `*.md` (19 files) | ~370 KB | **LIVE** | `AGENTS.md` is the routing contract; `README.md`/`README.zh.md` are user-facing. `cover_letter.md`, `submission_checklist.md`, `supplementary.md`, `DATA_PRESENTATION*.md` are ICLR/NeurIPS/EAAI-era leftovers, each already carrying a LEGACY banner pointing at `tnnls_submission/`. Kept: they are cited 59-128 times and the banners work. |
| `docs/` top level (43 files) | 57 MB total tree | mixed | 18 in nav; the rest are reference material (`ARCHITECTURE.md`, `CLAIMS.md`, `CONSOLIDATED_RESULTS.md`, `METRIC_LEDGER.md`) or historical (`push-ready-summary.md`, `submission-checklist-final.md`). |
| `docs/audit/` (560 records: 328 flat + 232 clustered) | 9.8 MB | **EVIDENCE** | the audit trail. 315 had inbound references; 38 did not (see §3). `INDEX.md` is a topic-cluster reading guide, not a completeness proof. |
| `docs/drafts/` | 2.7 MB | mixed | `paper-A-final.*` is the frozen canonical surface. Flattened intermediates (`abstract-final.md`, `results-final.md`, `section-2-method.md`) are still cited by the build. |
| `docs/ARCHIVE/` (739 md) | 11 MB | **HISTORICAL** | excluded from the mkdocs build by `exclude_docs`. Now also holds `legacy-paper/` and `audit-orphans/`. |
| `docs/references/` | 17 MB | **LIVE** | bibliography PDFs. |
| `docs/figures/` | 3.3 MB | **LIVE** | paper figures. |
| `docs/r4-survey/`, `r5-survey/`, `r17-survey/` | 1.5 MB | **HISTORICAL** | wave-era surveys; `r17` is still nav'd. |
| `docs/adr/`, `docs/governance/`, `docs/lean/`, `docs/theory/`, `docs/models/`, `docs/tables/`, `docs/api/` | ~1 MB | **LIVE** | design records, theorem notes, model cards, paper tables, mkdocstrings output. |
| `docs/build_pdf/` | 2.7 MB | **HISTORICAL** | LaTeX class/style files + the old `md_to_tex` converters. No tool invokes them (`paper-A-final.tex` is built directly). |
| `verification_outputs/` | **4.8 GB, 52,170 files** | **EVIDENCE** | see §4. 41,560 tracked, 10,610 ignored. |
| `paper-data/` (114 files) | 620 KB | **EVIDENCE** | per-cell logs and CSVs cited from the paper tables. |
| `paper-figures/`, `plots/`, `regression-vectors/` | small | **LIVE** | figure sources, plot scripts, frozen D.4 vectors. |
| `results/` | 2.0 MB → 0 | **JUNK, deleted** | untracked `mmseqs_tmp` left by the concurrent-scoring collision on 2026-10-21. Gitignored by `results/*_tmp/`. |
| `site/` | — | **JUNK** | mkdocs build output, gitignored. |

---

## 3. What changed in this pass

### 3.1 Archived: superseded manuscript surfaces → `docs/ARCHIVE/legacy-paper/`

17 files, `git mv` only (history preserved, nothing deleted):

`paper-draft.md`, `paper-draft-anonymous.md`, `paper-final-neurips.md`,
`paper-final-neurips.pdf`, `paper-eaai.pdf`, `paper-tnnls.pdf`,
`paper-draft-precut.md.bak`, `paper-draft-precut-w193.md.bak`,
`paper-flat-ieeetran.{tex,pdf,aux,out,log}`, `pdflatex-rerun{,2,3,4}.log`.

Two things were checked first:

- **No tooling reads them.** A repo-wide grep of `*.py`/`*.sh`/`*.yml` found
  zero references. The `docs/drafts/ARCHIVE_INDEX.md` claim that
  `paper-flat-ieeetran.tex` was "still actively referenced by paper-build flow"
  was stale; that row is now marked MOVED.
- **`paper-flat-flattened.ARCHIVED-2026-09-23.md` was NOT moved**, because the
  frozen `tnnls_submission/MANIFEST.md` links it by GitHub blob URL. Moving it
  would dangle a frozen surface. Same reasoning kept `paper-flat-flattened-zh.md`
  (cited as the bilingual provenance copy).

### 3.2 Archived: 25 orphan audit records → `docs/ARCHIVE/audit-orphans/`

Of the 38 audit records with zero inbound references, 25 are 2026-09
paper-polish / cover-letter / submission-prep notes absorbed into
`paper-A-final.*`. The other 13 are recent and load-bearing and were **cited
instead of archived** — `docs/audit/todo-history.md` gained §14
("Evidence-artifact index") naming `gap46`, `gap49`, `gap56`, `gap60`.

`docs/audit/INDEX.md` had its 25 bullet lines removed and its per-cluster and
cluster-map counts **re-derived from the remaining bullets**, not hand-adjusted.

### 3.3 Fixed: 17 dead mkdocs nav entries

`mkdocs.yml` nav referenced 73 files, of which **17 did not exist** (all
2026-09-13 snapshot names under `- Current audit records:`). The build was
green only because `validation.nav.not_found: ignore` is set. The dead entries
are removed; the 4 live entries in that block are kept and a comment records
why. Nav is now **56 references, 0 missing**.

This is a real defect that was being masked: `not_found: ignore` means any
future dead nav entry fails silently. Worth reconsidering that setting before
the next documentation pass (see §6.3).

### 3.4 Fixed: stale pointers

- `docs/README.md` — three links repointed at `ARCHIVE/legacy-paper/`; two new
  archive directories documented.
- `docs/drafts/ARCHIVE_INDEX.md` — `paper-flat-ieeetran.*` rows marked MOVED
  with the reason the "still in use" note was wrong.
- `docs/audit/INDEX.md` — `docs/paper-draft.md` removed from the
  "active surface" list (it no longer exists at that path).
- `mkdocs.yml` `not_in_nav` — three draft paths repointed.

### 3.5 Side effect on the docs-vs-code gate (expected, verified)

`tools/check_docs_against_code.py` scans `docs/*.md` **top level only**, so
archiving the three large legacy drafts removes their claims from the scan:
**4,148 → 3,370 verified claims** (-778). This was confirmed by temporarily
restoring the three files (4,148 again) and removing them (3,370 again), so it
is entirely the archive move and not a lost check. The gate still exits 0.

That is the correct scope: those drafts are superseded, and their inline
symbol references should not be validated as live claims. The number in the
gate output will be 3,370 from now on; it is not a regression.

### 3.6 Left alone, on purpose

| surface | why |
|---|---|
| `data/**` (9 vendored repos) | byte-identical-to-upstream guardrail |
| `docs/CLAIMS.md`, `CONSOLIDATED_RESULTS.md`, `paper-A-final.*`, `tnnls_submission/**` | frozen surfaces |
| 41,560 tracked files in `verification_outputs/` | raw evidence; the user chose to keep all 44,780 R6 PDBs (2.59 GiB) rather than sample or repack them |
| historical audit records citing old paths | they describe where a file was at the time; rewriting them would falsify the trail |
| `docs/build_pdf/` | dead, but only 2.7 MB and it documents the old EAAI build; not worth the churn |

---

## 4. `verification_outputs/` — what is actually in there

4.8 GB, 52,170 files. Composition by extension:

| ext | size | files | share | what it is |
|---|---:|---:|---:|---|
| `.pdb` | 2.59 GiB | 44,780 | 55% | R6 generated protein structures (`gap01`, `gap28`, `gap30`, `gap31`) |
| `.npz` | 1.58 GiB | 586 | 34% | sample arrays behind every FID / W2 number |
| `.npy` | 0.39 GiB | 199 | 8% | cached Inception feature matrices |
| `.json`/`.jsonl` | 0.05 GiB | 2,304 | 1% | the actual metrics — these are what the paper quotes |
| `.log` | 0.03 GiB | 518 | 0.7% | run logs; the ones under `gap*` record the exact command |
| `.fasta` | 0.02 GiB | 401 | 0.5% | R1 sequence sets |

Two hygiene facts worth recording:

1. **`verification_outputs/` is gitignored (`.gitignore:64`) but 41,560 files
   in it are tracked** via historical `git add -f`. There is no written rule
   for which subset gets force-added; the tracked/untracked split (41,560 vs
   10,610) is accidental. A future pass should either state the rule or stop
   force-adding.
2. **`verification_outputs/gap60-tradeoff/_scratch/`** (4.8 MB, 19
   `mmseqs_tmp` trees) was untracked scratch from the GAP-60 run and has been
   **deleted** in this pass. The real GAP-60 outputs are the sibling
   `seed4*_{on,off,b1}/` directories plus `tradeoff.json`, all untouched.
   The repo-root `results/mmseqs_tmp/` (2.0 MB, left by the concurrent-scoring
   collision) was deleted for the same reason; `results/` is recreated on
   demand and is covered by the `results/*_tmp/` gitignore rule.

---

## 5. Root-level leftovers

| file | verdict | note |
|---|---|---|
| `cover_letter.md`, `submission_checklist.md`, `supplementary.md` | LEGACY, kept | ICLR-2027 / NeurIPS-workshop era. Each has a top banner pointing at `tnnls_submission/`. Moving them would break 59-128 inbound links for no gain. |
| `DATA_PRESENTATION.md` (56 KB), `DATA_PRESENTATION_BRIEF.md` | LEGACY, kept | EAAI-era data presentation. Same reasoning. |
| `INSTALL_REPORT.md`, `QUICKSTART.md`, `TUTORIAL.md`, `FAQ.md`, `SECURITY.md`, `CONTRADCTS.md`, `CONTRIBUTING.md`, `ROADMAP.md`, `DESIGN_BOUNDARY.md` | **LIVE** | user-facing / contributor-facing. |
| `RELEASE-NOTES-v3.0.md` | **HISTORICAL**, kept | superseded by `docs/RELEASE-NOTES.md`; small. |
| `CHANGELOG.md` | **LIVE** | development history. |

---

## 6. Open hygiene findings (not fixed here)

**6.1 `docs/audit/INDEX.md` lists 484 of 558 audit records.** The generator
(`/tmp/regen_index.py`, Wave 347) was never committed, so the listing cannot be
regenerated reproducibly. Either commit a generator or stop claiming the index
is a map of *all* records. Until then `ls docs/audit/` is authoritative.

**6.2 `docs/audit/INDEX_MAINTENANCE.md` documents a script that does not
exist in the repo.** Same root cause as 6.1.

**6.3 `mkdocs.yml` sets `validation.nav.not_found: ignore`.** This is why 17
dead nav entries survived unnoticed. Changing it to `warn` would have caught
them, and `--strict` would then fail on any future one. Recommended, but it is
a config change with build-breaking potential, so it needs its own commit.

**6.4 No written rule for which `verification_outputs/` files are tracked.**
See §4.1.

**6.5 `docs/build_pdf/` is dead code** (2.7 MB: `md_to_tex.py`,
`md_to_tex_eaai.py`, `elsarticle-*.bst`, `neurips_2025.sty`). Nothing invokes
it. Archiving it would be correct but is cosmetic.

---

## 7. How to re-run the scan

```bash
# reference graph over every audit record
python3 - <<'PY'
import os, re, collections
audit = sorted(f for f in os.listdir('docs/audit') if f.endswith('.md'))
corpus = []
skip = {'data','.venvs','.git','site','verification_outputs','node_modules','__pycache__'}
for dp, dn, fn in os.walk('.'):
    dn[:] = [d for d in dn if d not in skip]
    for f in fn:
        if f.endswith(('.md','.py','.yml','.yaml','.sh','.json','.txt')):
            p = os.path.join(dp, f)
            if os.path.getsize(p) < 3_000_000:
                corpus.append(open(p, encoding='utf-8', errors='ignore').read())
refs = collections.Counter()
for t in corpus:
    for m in re.finditer(r'audit/([A-Za-z0-9_.\-]+\.md)', t):
        refs[m.group(1)] += 1
print("orphans:", [f for f in audit if refs.get(f, 0) <= 1])
PY

# nav integrity (0 missing expected)
python3 - <<'PY'
import re, os
s = open('mkdocs.yml').read()
refs = re.findall(r'^\s*-\s+[^:]+:\s*(\S+\.md)\s*$', s, re.M)
print(len(refs), "refs;", [r for r in refs if not os.path.exists('docs/'+r)], "missing")
PY
```
