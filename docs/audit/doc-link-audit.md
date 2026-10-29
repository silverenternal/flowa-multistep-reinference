# Documentation link audit — 146 unique targets, 50 files

**Date:** 2026-10-29
**Scope:** every relative markdown link in `docs/**/*.md` (excluding
`docs/ARCHIVE/`), the repository-root `*.md`, and `tnnls_submission/**/*.md`.
**Status:** closed. No number in `docs/drafts/paper-A-final.*` moved; no claim,
status label, or verdict changed.

---

## 1. The defect

GitHub resolves a relative link against the directory of the file that
contains it. Nothing in the repository checked that, so links rotted silently:
the text still rendered, the target 404'd, and every gate stayed green.

Measured with `python3 tools/check_doc_links.py` before any edit:

```
checked=1153 broken=146  root-relative=12 docs-relative=6 moved=52 archived=29 ambiguous=9 missing=38
```

146 unique `(file, target)` pairs across 50 files. The worst offenders were
`docs/CLAIMS.md` (33 distinct targets), `docs/ARCHITECTURE.md` (17),
`docs/schedule-theory.md` (11), `docs/configs.md` (7) and
`docs/audit/wave348-link-fix.md` (5).

Four distinct failure modes:

| class | count | cause |
|---|---:|---|
| `root-relative` | 12 | target written as if the repo root were the current directory (`docs/ARCHITECTURE.md` → `adaptive_reflow/frame/channel_rule.py`) |
| `docs-relative` | 6 | same, with the target under `docs/` |
| `moved` | 52 | target exists at a different path (cluster subdirectories, package splits) |
| `archived` | 29 | target survives only under `docs/ARCHIVE/` |
| `ambiguous` | 9 | several files share the basename; the link text disambiguates |
| `missing` | 38 | no file with that basename exists anywhere |

## 2. What was repaired

**144 of the 146 targets repaired**, by the four mechanisms below. The class
table in §1 is the *pre-repair* measurement; the two entries not repaired are
the supplementary bundle's (one `ambiguous`, one `archived`) and are exempted
with a written reason in §3.

**Mechanical rewrites**, each target re-pointed relative to its own file:

- 12 `root-relative` + 6 `docs-relative` — path made relative.
- 52 `moved` + 29 `archived` — repointed to the single file with that
  basename (one `archived` target, in the bundle, is exempted). The largest
  group is the ADR renumbering
  (`adr/0006-hyperparameter-free-framework-principle.md` → `adr/0014-…`,
  `0007` → `0015`, `0008` → `0016`, `0012-schedule-family-survey` →
  `0012-noise-schedule-survey`).

**13 targets fixed from the link text.** `docs/CLAIMS.md` links were written
as `[`docs/audit/sweep_eval/p3-comparison.md`](audit/p3-comparison.md)` — the
label carried the canonical path while the target was ambiguous. Reading the
label resolves the cluster unambiguously, so the `ambiguous` targets were
fixed per-occurrence rather than by a global rule (one `ambiguous` target, in
the bundle, is exempted).

**6 label corrections.** `docs/schedule-theory.md`, `docs/sequential-protocol.md`
and `docs/defaults-matrix.md` linked to `adaptive_reflow/algorithm/scheduler.py`,
which is now the package `adaptive_reflow/algorithm/scheduler/`. The table rows
in `schedule-theory.md` were re-pointed per class:
`ConstantScheduler`/`Linear`/`Exponential`/`Polynomial`/`Sigmoid` →
`scheduler/simple.py`; `ConvergenceAdaptive`/`CodimensionSheet` →
`scheduler/adaptive.py`; `SchedulerProtocol`/`SCHEDULER_REGISTRY` →
`scheduler/protocols.py`. The stale `scheduler.py:478`-style line anchors were
dropped rather than carried forward — the line numbers no longer exist.

**28 links unwrapped** where the target exists under no name. The label is
kept, so the path stays visible as inline code; only the hyperlink is removed.
Full list in §4.

## 3. The checker

`tools/check_doc_links.py` — 1153 relative links scanned, 0 broken.

It blanks out fenced code blocks and inline code spans before extracting
links, because several audit documents quote example markdown such as
`[alt](figures/foo.png)` and `[text](relative/path)`. Without that step those
examples are reported as 14 phantom defects. It also skips `docs/ARCHIVE/`,
which is a frozen historical tree.

Exit status is 1 on any `missing` or `ambiguous` target outside `FROZEN`.
`FROZEN` holds one entry — the supplementary bundle's README — because that
file is a *shipped artifact*: it is byte-identical to its copy inside
`tnnls_submission/supplementary_bundle.zip` (pinned by `MANIFEST.md`), so
rewriting its two links here would desynchronise the repository from the zip a
reviewer downloads. `tests/test_doc_links.py` pins `broken == 0` outside
`FROZEN`, pins that every `FROZEN` entry names a file that still exists (so
the exemption cannot outlive its issue), asserts the scanner really walks the
tree (`count_links() >= 1000`), and asserts example snippets inside code
fences are not treated as links.

## 4. Unwrapped links — 28 occurrences, 20 targets

| file | target | why |
|---|---|---|
| `CHANGELOG.md` | `docs/audit/wave244-p5-metrics-patch.md` | never committed; the archived `wave244-p5-final-verify.md` covers a different subject |
| `CHANGELOG.md` | `scripts/wave242_p1_flowmol3_rescue_single_mol.py` | never committed (the script was never executed) |
| `TUTORIAL.md` | `mutmut_results.txt` | generated report, not tracked |
| `docs/ARCHITECTURE.md` | `docs/audit/wave201-p2-foldability-sc-workers-per-gpu.md` | absent; `wave201` has no archived copy |
| `docs/ARCHITECTURE.md` | `docs/audit/wave201-p3-run-foldability-propagate-workers-per-gpu.md` | same |
| `docs/CLAIMS.md` | `docs/audit/wave186-p2-ladder.md` | absent; `wave186-p2-generate.md` is a different subject |
| `docs/CLAIMS.md` | `docs/audit/wave186-p2-pin-commit-sha.md` | same |
| `docs/CLAIMS.md` | `scripts/wave189_p2_post_cd70821_2d_sweep.py` | never committed |
| `docs/CLAIMS.md` | `tools/aggregate_wave189_p2.py` | never committed |
| `docs/CLAIMS.md` | `data/kanzi_ckpt/README.md` | the directory has no README |
| `docs/PLUG_IN_YOUR_MODEL.md` | `todo/PHASE-4-model-integration-iteration.md` | `todo/` was retired 2026-10-13 |
| `docs/audit/algorithm_4arm/p6-boundary-framing.md` | `docs/audit/wave208-p6-boundary-framing.md` | `wave208` p3/p5/p7 are archived, p6 is not |
| `docs/audit/data_packaging/data-linkage-closure.md` | `docs/audit/wave111-b-config-scattering-audit.md` | `wave111` a/c are archived, b is not |
| `docs/audit/data_packaging/data-linkage-closure.md` | `docs/audit/wave111-data-linkage-plan.md` | never archived |
| `docs/audit/flowmol3/p3-flowmol3-n1000.md` | `docs/audit/wave109-c-flowmol3-n1000.md` | only `wave109-a` survives |
| `docs/audit/flowmol3/p3-flowmol3-n1000.md` | `docs/audit/wave195-p2-r-level-power.md` | the artifact survives (`verification_outputs/wave195-p2-r-level-power.json`), the audit doc does not |
| `docs/configs.md` | `docs/audit/wave111-{b-config-scattering,data-linkage-plan,data-linkage-closure}.md` | as above |
| `docs/push-ready-summary.md` | `../todo/PUSH-READY.md` | `todo/` retired, no successor |

Rewritten instead of unwrapped, because a real successor exists:

- `docs/algorithm-{deep-,round2-,}uplift-plan.md` → the consolidated
  `docs/ARCHIVE/algorithm-uplift/algorithm-uplift-plans.md` (it contains all
  three rounds).
- `todo/WAVES.md` → `docs/audit/todo-history.md`, which is what the README
  already cites elsewhere.

## 5. Two side effects worth recording

**`check_docs_against_code` moved 3375 → 3370.** The five lost path-claims are
`docs/ARCHITECTURE.md` lines 15/17/1313/1315/1359, where the link target used
to be the repo-relative `adaptive_reflow/…` and is now the correct
file-relative `../adaptive_reflow/…`. The claim extractor's
`PATH_CLAIM_RE` only matches paths starting at a top-level directory, so those
five stopped being counted. They are still verified — by
`check_doc_links.py`, which resolves the same targets and is stricter (it
checks the file the reader will actually open). No claim became unchecked.

**`paper-data/SHA256SUMS` broke, and `paper-data/MANIFEST.md` was already
stale.** `paper-data/headline-evidence/README.md` is a symlink into
`docs/headline-evidence/README.md`, so fixing the latter changed the former's
hash. That surfaced a second defect: `paper-data/MANIFEST.md` carried five
stale rows, four of them symlinks into `verification_outputs/` that later
waves had rewritten (`R5b_cifar10_rf/wave235-p1-r5b-fix.csv`,
`R6_lineageflow_k6/{baseline,framework}_foldability_summary.json`,
`R6_lineageflow_k6/wave225-p4-k6-tier-aware.json`) plus the headline README.
All five refreshed; `tools/check_paper_data_manifest.py` now verifies all 56
rows and `tests/test_evidence_ledgers.py` pins it.

## 6. Gates

| Gate | Result |
|---|---|
| `tools/check_doc_links.py` | `checked=1153 broken=2`, both `FROZEN` (supplementary bundle) |
| `tools/check_submission_links.py` | `links=242 ok=242` |
| `tools/check_paper_data_manifest.py` | `rows=56 ok=56 bad=0` |
| `tools/check_evidence_ledgers.py` | 19 ledgers, 0 unknown |
| `tools/check_data_integrity.py` | 264 files / 15 ledgers, 0 mismatches |
| `tools/check_claims_consistency.py` | no drift |
| `tools/check_docs_against_code.py` | 3370 claims verified |
| `tools/check_submission_manifest.py` | `known_stale=0 unknown=0 ledger_drift=0` |
| `tools/check_tables_inventory.py` | 33 checks, 0 drift |
| `tools/check_recipe_hashes.py` | 71 rows, 0 stale |
| `pytest tests/test_d4_regression_vectors.py` | 30/30 PASS |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/` | 0 findings |
| `mkdocs build --strict` | exit 0 |

## 7. Still open

`tools/check_doc_paper_refs.py` reports `E.2 ratio 0.818 (36 / 44)` against a
0.90 target. **This predates the audit** — verified by running the same tool
against a pristine `HEAD` worktree, which gives the identical 0.818. Eight
top-level docs carry no paper anchor (`README.md`, `CONTRIBUTING-cover-letter.md`,
`FLOWA_WORKFLOW.md`, `capability_g1_analysis.md`, `code-release-checklist.md`,
`configs.md`, `reproduce.md`, `submission-checklist-final.md`). The gate
references `todo/framework-internal-metrics.md`, a retired path, and its anchor
list still names `JMAA` — the pre-TNNLS venue. Closing it means either adding
genuine cross-references or retiring the metric; both are editorial decisions,
not mechanical fixes, so it is left as found and recorded here.

## 8. Files touched

`tools/check_doc_links.py` and `tools/check_paper_data_manifest.py` (new);
`tests/test_doc_links.py` (new); `tests/test_evidence_ledgers.py` (+1 test);
272 lines rewritten in place across 30 markdown files (equal add/remove — no
line was added or removed); `paper-data/SHA256SUMS` (1 line);
`paper-data/MANIFEST.md` (5 rows); `todo.json` (2 gate-chain entries).

### 7.1 A second, larger class: dead paths in backticks

The repair above covered markdown links — the ones that render as clickable
404s. A broader scan of backticked paths (`docs/…`, `tools/…`, `paper-data/…`
inside inline code) finds **4,290** occurrences whose target does not exist.
The overwhelming majority sit inside `docs/audit/` wave records, which quote a
path as it stood at the time; rewriting those would falsify the trail, so they
stay.

The actionable subset is the live, reviewer-facing documents that still point
at `docs/paper-draft.md`, which commit `941c361a` archived into
`docs/ARCHIVE/legacy-paper/paper-draft.md` (and which
`docs/ARCHIVE/legacy-paper/INDEX.md` already marks "superseded by
`paper-A-final.md`"):

| document | `docs/paper-draft.md` | `docs/drafts/paper-flat-flattened.md` |
|---|---:|---:|
| `docs/CONSOLIDATED_RESULTS.md` | 173 | 0 |
| `docs/baseline-audit-report.md` | 68 | 0 |
| `docs/CLAIMS.md` | 52 | 10 |
| `docs/INSIGHTS.md` | 18 | 0 |
| `docs/push-ready-summary.md` | 18 | 0 |
| `supplementary.md` | 9 | 0 |
| `docs/ARCHITECTURE.md` | 1 | 0 |
| `docs/paper-profile.md` | 1 | 0 |
| `docs/submission-checklist-final.md` | 1 | 0 |
| `docs/算法实现说明.md` | 1 | 0 |
| **total** | **342** | **10** |

The fix is mechanical — `docs/paper-draft.md` → `docs/ARCHIVE/legacy-paper/paper-draft.md`
and `docs/drafts/paper-flat-flattened.md` →
`docs/drafts/paper-flat-flattened.ARCHIVED-2026-09-23.md`, both of which exist
— and the section numbers the surrounding prose cites (§7.6.6 and friends)
remain valid in the archived copy.

**Resolution (2026-10-29, authorised).** All 352 were repointed — 342 for
`paper-draft.md`, 10 for `paper-flat-flattened.md` — including the 62 in
`docs/CLAIMS.md`. The edit is path-only: the section numbers the surrounding
prose cites are unchanged, because the archived copy is the same document.
`docs-vs-code` stays at 3370 verified claims (its extractor scopes to
non-ARCHIVE paths, so the repointed targets moved out of its scan rather than
out of existence); `check_doc_links` and `check_claims_consistency` are
unchanged. No number, claim, status label, or verdict moved.
