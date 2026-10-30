# The evidence pointers nobody followed

**Date:** 2026-10-30
**Scope:** backticked repository paths in `README.md`, `README.zh.md`,
`AGENTS.md`, `docs/README.md`, `docs/PAPER-EVIDENCE.md`, `tnnls_submission/*.md`
and the docs those files cite; `tools/check_reviewer_pointers.py`.
**Status:** 4 dead pointers repaired in the READMEs and the submission package,
110 archived-record citations repointed, gate added. No metric, claim, status
label, or verdict moved. No GPU was used.

---

## 1. Two kinds of link, one of them checked

The repository points at its evidence in two ways:

```markdown
[`docs/audit/INDEX.md`](docs/audit/INDEX.md)        <- markdown link
`tools/check_data_integrity.py`                     <- inline code span
```

`tools/check_doc_links.py` resolves the first kind and explicitly ignores the
second, because a code span is usually an example. But in this project the
code span is the pointer: the README evidence table's third column is nothing
but code spans. So the file a reviewer is told to open was checked by nothing.

The same is true of the fragment half of a link (`doc-anchor-audit.md`), and
the same is true of symlink targets (`clone-reproducibility.md`). Three rounds,
one shape.

## 2. Four dead pointers in the reviewer-facing surfaces

| Surface | Pointer | Reality |
|---|---|---|
| `README.md`, `README.zh.md` | `tools/verify_reproducibility.py` | the file is `tools/verify_reproducibility_smoke.py` |
| `README.md`, `README.zh.md` | `verification_outputs/composite_axis_byte_stable/SOURCE.md` | that directory has never existed in this tree; the record is `docs/headline-evidence/composite_axis_byte_stable/SOURCE.md` |
| `tnnls_submission/cover_letter.md` | `docs/tnnls_submission_checklist.md` | `tnnls_submission/submission_checklist.md` |
| `tnnls_submission/cover_letter.md` | `scripts/wave242_p1_flowmol3_rescue_single_mol.py` | the sentence itself says "never committed to the repository" |

The composite-axis row is the one that mattered: it carried the numbers
`Kanzi +0.1695, LineageFlow +0.2083, FlowMol3 +0.1182` and sent the reader to
a directory that does not exist. The numbers are correct — `SOURCE.md` states
all three with their N and σ — so the repair was the pointer, not the numbers.
The rescue-script pointer was reworded to a bare filename, which is what the
surrounding sentence already claimed.

## 3. 110 citations of records that had been archived

Wave 137 moved the Wave 1–99 audit records into
`docs/ARCHIVE/audit-waves-1-99/` and updated `INDEX.md`, but 110 backticked
citations in the current docs still named the old flat paths:

```
docs/audit/wave52-sota-baseline-comparison.md
    -> docs/ARCHIVE/audit-waves-1-99/wave52-sota-baseline-comparison.md
docs/audit/wave234-p5-meta-analysis.md
    -> docs/ARCHIVE/audit-by-wave/wave234-p5-meta-analysis.md
```

Each of the 110 was resolved by basename against the whole `docs/` tree and
kept only when exactly one file matched. Twelve files changed; the largest was
`docs/CONSOLIDATED_RESULTS.md` (44 lines). Every diff was verified to differ
from `HEAD` only in the path token — a normalised comparison that substitutes
both spellings for a placeholder and the MANIFEST hash/size cells for `<H>`
reports `SAME` for all fourteen touched markdown files.

`docs/drafts/paper-flat-flattened.ARCHIVED-2026-09-23.md` was reverted
untouched: it is a frozen archive, and a stale pointer inside it is part of
what was archived.

## 4. The gate

`tools/check_reviewer_pointers.py` resolves every backticked path token on the
reviewer-facing surfaces. 377 pointers checked, 0 dead.

Scope is written into the module docstring rather than implied:

* in scope: the two READMEs, `AGENTS.md`, `docs/README.md`,
  `docs/PAPER-EVIDENCE.md`, `tnnls_submission/*.md`;
* out of scope: `CHANGELOG.md` (append-only history — an entry naming a file
  that was later deleted is a true statement about that release), and tokens
  under `docs/audit/` or `docs/drafts/` (a citation into the audit tree is
  provenance, not a live pointer).

`tests/test_tools/test_reviewer_pointers.py` pins the gate with six cases,
including the two exemptions and a negative control that a symbol
(`tools.paper_metrics.compute_validity_pct`) and a glob (`tools/sweep_*.py`)
are not treated as paths.

## 5. What is still dead, and why it is not being rewritten

159 backticked `docs/audit/<name>.md` citations (117 distinct) in the current
docs resolve to no file anywhere:

```
docs/CONSOLIDATED_RESULTS.md  ->  docs/audit/wave115-p4-final.md
docs/CONSOLIDATED_RESULTS.md  ->  docs/audit/wave186-p2-ladder.md
docs/CLAIMS.md                ->  docs/audit/wave186-p2-pin-commit-sha.md
docs/drafts/section-2-method.md -> docs/audit/wave235-p1-r5b-fix.md
```

Some were renamed during consolidation (`wave280-p-k7-audit.md` →
`wave280-p-k7-sweep-result.md` is a plausible successor; `wave115-p4-final.md`
→ `wave115-bucket-d-regressions.md` is a guess). Guessing a successor would
attach a citation to a record that may not contain the claim, which is worse
than a citation that resolves to nothing: a dead pointer is visibly dead, a
wrong pointer is not.

These are recorded as **GAP-97** in `todo.json` with the triage rule: resolve
only against `docs/audit/INDEX.md`, and only when the successor is confirmed by
matching claim text. They are not deleted, and the gate does not silently
accept them — the exemption is by prefix and is stated in the gate's own
docstring, so the residual count is a number in this record rather than an
invisible assumption.

## 6. The same check over the evidence tree (2026-10-30, later the same day)

`check_reviewer_pointers.py` only sees paths that start with a repo-relative
prefix and end in a known extension, and it only sees the reviewer-facing
surfaces. Running the same resolution over every backticked
`verification_outputs/...` token in the two READMEs, `CONSOLIDATED_RESULTS.md`,
`INSIGHTS.md`, `CLAIMS.md`, `PAPER-EVIDENCE.md`, the paper draft and the
submission package:

| | count |
|---|---:|
| backticked evidence pointers | 437 |
| that resolve to a file | 408 |
| that resolve to nothing | **29** |

Twenty-nine is small enough to look at one by one, and three things came out of
doing that:

**One was a wrong extension, not a missing file.** The Wave 93 §15.15 block
named `power_analysis/per_cell.json`; the directory contains `per_cell.csv` and
nothing else, and the CSV is the 12-row table the same section quotes (its
header is `model,metric,n,baseline,framework,delta,delta_se,ci_95_lower,ci_95_upper,p_value_raw,p_value_bonferroni,power_to_detect_1pp,verdict`).
The section now says the CSV is the only serialisation and the table row is
marked `PLANNED` rather than `NEW`. `per_cell.csv` was force-added (1.2 KB) —
it is the source for a number in the ledger and was not being shipped.

**One is the honest-negative record.** `CLAIMS.md` cites
`verification_outputs/wave188-p5-fix-1-cd70821-inversion.json` as the preserved
Wave 188 P5 §4.2 reframe of the framework-vs-baseline inversion. That file is
not in the tree and no file with its stem exists anywhere. It is left as a
citation: the claim it supports is a *disclosure*, and deleting the citation
would remove the pointer to a negative result, which is the one direction this
round must not move.

**The other twenty-seven are artifacts that were never committed.**
`verification_outputs/` is gitignored (`.gitignore:64`); only artifacts that
back a headline number are force-added, and the wave-era CSVs named in
`CONSOLIDATED_RESULTS.md` were written into the working copy and never tracked.
They cannot be repointed, because there is no file with that stem to repoint
them at.

Two of them look like renames — `kanzi_n1000_framework_paper_metrics_real/per_metric.json`
against `kanzi_n1000_framework_paper_metrics/per_metric.json` on disk, and
`kanzi_n1000_real_v2/per_metric.jsonl` against three `..._paper_metrics_*`
directories — and both are left alone. The GAP-97 rule applies: a dead pointer
is visibly dead, a pointer to a different run's file is not, and the values
would be attributed to the wrong sweep.

**GAP-97 now covers both classes.** Its acceptance criterion is unchanged in
spirit: resolve against an authority (`docs/audit/INDEX.md` for audit records,
the tree for artifacts) and only when the successor is confirmed. The residual
counts are 159 audit citations and 28 evidence pointers.
