# The docs tree still pointed at the retired governance surface, and E.2 measured its own transpose

**Date:** 2026-10-30
**Branch:** main
**Base commit:** `24f05bac`
**Scope:** repoint the live pointers that survived the 2026-10-13 `todo/`
retirement; correct `docs/GATES.md`, which described a gate chain and a test
suite that no longer existed; make `tools/check_doc_paper_refs.py` measure what
the E.2 gate claims to measure.
**Trigger:** CPU-only audit sweep. No GPU, no measurement, no verdict, no
`CLAIMS.md` number touched.

---

## 1. Observed facts

### 1.1 The retirement record's "no other live surface" claim was false

`docs/audit/todo-surface-reset.md` §2 (2026-10-13) states: *"No other live
surface references the deleted tree."* A scan of every tracked `*.md` on
2026-10-30 counts **822 citations** of `todo/…`:

| Area | Files | Citations |
|---|---:|---:|
| `docs/`, excluding `audit/` and `ARCHIVE/` | 24 | 176 |
| `docs/audit/` | 75 | 305 |
| `docs/ARCHIVE/` | 90 | 308 |
| outside `docs/` | 13 | 33 |

The 2026-10-13 pass scanned `docs/README.md` and `docs/RELEASE-NOTES.md` and
assumed the rest were audit records. It never scanned `docs/` outside
`audit/`, where `docs/baseline-audit-report.md` alone carries 80 and
`docs/CONSOLIDATED_RESULTS.md` 45.

### 1.2 `docs/GATES.md` described a repository that no longer exists

Five distinct defects, all live:

1. **Header.** "Source of truth: `todo/GATES.md` (canonical, BINDING)" — that
   file was deleted on 2026-10-13. Eighteen `todo/…` citations in total.
2. **D.4 per-file split.** The page claimed 33 tests in
   `tests/test_d4_regression_vectors.py` + 39 in
   `tests/test_adapters/test_regression_vectors.py` = 72. `pytest
   --collect-only` on 2026-10-30 returns **30 + 42 = 72**. Neither file has
   changed since `b88b32f6` / `1ce8e3a2`, so the split was a miscount, not a
   reorganisation. The *total*, which is what the gate asserts
   (`D4_EXPECTED_PASS_COUNT = 72`), was correct throughout.
3. **Full-suite counts.** "collects 5155 tests / 5012 pass" (Wave 131 era) is
   superseded by 5610 passed / 180 skipped / 0 failed on 2026-10-30
   (`todo.json` → `gate_note`).
4. **Three "pre-existing FAILED tests".** Re-checked one by one:
   `test_exp2_stochastic_fm_w2_ratio_reproduces_25pct_reduction` — the **file**
   was deleted in Wave 33 (`9c10d212`); the listing outlived the test.
   `test_check_docs_against_code.py::test_self_test_quiet_mode_returns_zero_exit`
   — no longer exists in that module. `test_no_false_positives_on_current_repo`
   — exists and **passes**.
5. **Paper grounding.** The E.2 sentence promised that "when
   `G-FRAMEWORK-HEALTH` passes, every A.0 paper statement has at least one doc
   anchor" — while the tool that backs it was failing at 0.818.

### 1.3 `tools/check_doc_paper_refs.py` measured the transpose of E.2

The gate's stated meaning is **statement coverage**: each numbered statement in
the A.0 inventory has ≥1 doc anchor. The implementation counted the fraction of
top-level `docs/*.md` pages citing *any* anchor. Those are different
propositions, and the implemented one falls mechanically whenever the docs tree
gains a page with no theory content — which is exactly what happened as
`docs/` grew from 31 to 44 top-level pages (1.000 → 0.818).

Measured statement coverage over `docs/**/*.md` (excluding `ARCHIVE/` and the
inventory itself, which names every statement by construction): **10 / 10**
A.0.1 statements are anchored, with 4 (Remark 1) to 921 (Theorem 1) anchors
each.

### 1.4 A path that never existed

`docs/RELEASING.md:229` and `docs/DEPRECATION.md:168` both cited
`docs/theory/PAPER_INVENTORY.md` as the A.0 inventory. `git log --all` for that
path is empty — it has never been in the repository. The inventory is
`docs/baseline-audit-report.md` §A.0 (line 13).

---

## 2. What was changed

### 2.1 `docs/GATES.md`

Header repointed to `todo.json` → `gate_chain` / `gate_note`, with the master
chain explicitly marked as the surviving *historical* copy rather than a second
list to run. The capability-metric definitions were kept in place (the three
`todo/` files that expanded them are gone, and `tools/capability_audit.py` is
still live with results under `verification_outputs/capability_audit_*.json`).
D.4 split corrected to 30 + 42, with a note that the earlier attribution was a
miscount. Full-suite figures replaced with the 2026-10-30 reading. The
three-failure list replaced with a per-test state table. Enforcement, see-also
and paper-grounding sections repointed.

### 2.2 `tools/check_doc_paper_refs.py`

Rewritten so the exit code follows statement coverage, which is what the gate
says it means. The statement set is **derived from the inventory** rather than
hard-coded — the A.0.1 *Statement* column only, so the gap rows in A.0.2
(Proposition 1, 4, 5 are recorded there as unimplemented by design) do not
enter the set, and a docstring quotation of "Lemma 1" in another column does
not leak a gap statement in. The old doc ratio is still printed, labelled
`[info]`, with an explicit note that it is not the gate and that
`--ratio-gate` restores the pre-2026-10-30 behaviour.

| Reading | Before | After |
|---|---|---|
| exit code | 1 (0.818 < 0.90) | 0 (10/10 statements anchored) |
| gate quantity | top-level doc ratio | A.0 statement coverage |
| statement set | n/a | read from `docs/baseline-audit-report.md` §A.0.1 |
| doc ratio | the gate | `[info]` diagnostic, 0.818, not met |

The docstring's citation of `todo/framework-internal-metrics.md` was repointed
to `docs/GATES.md` §"Paper grounding", which now carries the definition.

### 2.3 Live pointers repointed (six)

| File | Was | Now |
|---|---|---|
| `docs/FLOWA_WORKFLOW.md` | step 1: read `todo/WAVES.md` | `todo.json` → `open_gaps` / `gate_chain` / `execution_order` |
| `docs/INSIGHTS.md` | "camera-ready scope is bounded per todo/STATUS.md" | `todo.json` → `deferred` (each entry carries a `re_entry` condition) |
| `docs/PLUG_IN_YOUR_MODEL.md` | "the Phase-4 acceptance table at `todo/PHASE-4-…`" | the criterion stated inline, retirement noted |
| `docs/theory/theorem1_rate_bound.md` | two `todo/algo-improvement-*` specs | `todo.json` → `gate_chain` / `deferred`, the A.3 acceptance test restated |
| `docs/RELEASING.md`, `docs/DEPRECATION.md` | `docs/theory/PAPER_INVENTORY.md` | `docs/baseline-audit-report.md` §A.0 |
| `docs/drafts/paper-A-final.md:881` | "CLM-073 + the `todo/RISK-REGISTER.md` R-019 deferred items" | "CLM-073 and the R-019 deferred items" |

The manuscript edit is **markdown-only**: the string appears in neither
`paper-A-final.tex` nor the PDF (`pdftotext` finds no occurrence), so the PDF
and its digest are unchanged. The `.md` moved 224 429 → 224 407 bytes,
27 347 → 27 346 words, `417f3183…` → `46e42307…`; `CURRENT_ARTIFACTS`, the
`MANIFEST.md` rows and banner, `SHA256SUMS`, and the digests quoted in
`README.md` / `README.zh.md` were refreshed. `sha256sum -c SHA256SUMS` → 0
FAILED; `check_submission_manifest` → `known_stale=0 unknown=0
addendum_drift=0 ledger_drift=0`.

### 2.4 Provenance left alone (162 citations, 17 files)

The rest are statements about *where a decision's reasoning was filed at the
time* — "spec source: `todo/framework-capability-metrics.md` §G.1", "task spec:
`todo/algo-improvement-failure-modes.md`", "the Wave 19 analysis note in
`todo/models/freqflow.md`". That is the same class of statement as a commit
hash: rewriting it would assert the reasoning was filed somewhere it never was,
and deleting it would erase the provenance. AGENTS.md §3 #2 keeps them.

`docs/audit/todo-surface-reset.md` gained a §8 recording the corrected count,
the classification and this policy; `docs/README.md` gained one sentence
stating that a remaining `todo/…` path records where something was filed, not
a live path. That is the whole mitigation: one paragraph at the entry point
instead of 162 rewrites.

---

## 3. Interpretation

The 2026-10-13 retirement was correct and its file deletions were complete; what
was incomplete was the **scan**. It repointed the two files it thought of and
generalised from them. The same failure mode — a surface describing a
repository that no longer exists — has now been found in `SUBMISSION_READINESS`
(a 446 705-byte PDF that was really 615 789), the `MANIFEST` (13 stale rows),
and `docs/GATES.md` (a binding source of truth that had been deleted for
17 days). The common cause is that none of these surfaces was *executed*:
prose does not fail when the file it names disappears.

The E.2 case is the mirror image. There the tool did run, but it measured a
different quantity from the one the gate named, and nobody noticed because the
number it produced was plausible (0.818 of a 0.90 target reads like a near
miss, not like a category error). Fixing the *measurement* — not adding anchors
to eight unrelated pages to reach 0.90 — is what makes the reading mean
something. The doc ratio is still reported, so the information is not lost; it
just no longer decides anything.

---

## 4. Unresolved

- **`tools/check_doc_paper_refs.py` is still not in `todo.json` →
  `gate_chain`.** It now exits 0 honestly and runs in under a second, so wiring
  it is a one-line change — but that changes the chain length quoted in
  AGENTS.md §4.1 and in `gate_note`, which is a governance decision rather than
  a fix.
- **The doc ratio is 0.818 and will stay there.** Eight top-level pages
  (`CONTRIBUTING-cover-letter.md`, `FLOWA_WORKFLOW.md`, `README.md`,
  `capability_g1_analysis.md`, `code-release-checklist.md`, `configs.md`,
  `reproduce.md`, `submission-checklist-final.md`) cite no paper anchor, and
  several have no reason to. The metric is reported, not enforced, precisely so
  that this stays a judgement rather than a quota.
- **`docs/models/*.model_card.md` still cite `todo/models/*.md`.** They are
  model cards, so the citation is closer to a source than to a historical note;
  whether to repoint them to `docs/audit/` equivalents is an editorial call.

---

## 5. Verification

| Gate | Result |
|---|---|
| `ruff check adaptive_reflow/ tests/ scripts/ tools/` | All checks passed |
| `pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py -q` | 72 passed |
| `pytest tests/test_tools -q` | 428 passed, 53 skipped |
| `mkdocs build --strict` | exit 0, 27.42 s |
| `check_submission_manifest.py` | `rows=26 known_stale=0 unknown=0 addendum_drift=0 ledger_drift=0` |
| `check_submission_links.py` | `links=232 ok=232` |
| `check_data_integrity.py` | 15 dirs, 703 files, 0 mismatches |
| `check_doc_links.py` | `checked=1157 broken=2 ambiguous=1 archived=1` (all four pre-existing, inside the frozen supplementary bundle) |
| `check_paper_data_manifest.py` | `rows=56 ok=56 bad=0 sources=110 source_bad=0` |
| `check_artifact_hashes.py` | `citations=8 stale=0 uncited=0` |
| `check_clone_integrity.py` | `ok=139 broken=0` |
| `check_vendored_pristine.py` | pass |
| `check_doc_anchors.py` | 101 fragment links resolve |
| `check_reviewer_pointers.py` | `checked=634 dead=0` |
| `check_recipe_flags.py` | 0 problems |
| `check_data_provenance.py` | `citations=108 paths=66 drifts=0 disclosed=3` (108 at this commit; **127 / 83 / 0 / 3 / 8 not-checkable** after the scan was widened the same day — `provenance-gate.md` §6) |
| `check_claims_consistency.py` | No drift detected |
| `paper_evidence.py --check` | 11 cells verified |
| `regen_audit_index.py --check` | regenerated (one record promoted historical → active by the new `docs/README.md` link) |
| `check_docs_against_code.py` | 3371 claims verified |
| `sha256sum -c SHA256SUMS` | 0 FAILED |

No metric, claim, status label, verdict or frozen surface changed.
