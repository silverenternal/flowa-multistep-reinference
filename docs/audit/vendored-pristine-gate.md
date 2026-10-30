# Guardrail 1 was prose; now it is a check

**Date:** 2026-10-30
**Scope:** the nine vendored upstream repositories under `data/`, the
"unmodified vendored code" claim in `tnnls_submission/data_availability.md`,
and the new `tools/check_vendored_pristine.py`.
**Status:** gate added; one count corrected in the package (8 → 9); every tree
verified pristine. No metric, claim about results, status label, or verdict
moved; no GPU was used.

---

## 1. The rule that nothing enforced

AGENTS.md guardrail 1: *"Files under `data/FlowMol3/`, `data/LineageFlow/`, …
must stay byte-identical to upstream commit hashes … Verify md5 matches
upstream before commit."* `data_availability.md` tells the reviewer the same
thing, and names nine files that were patched during internal development and
reverted at Wave 260 / Wave 262.

Nothing checked either statement. `data/` is gitignored (`.gitignore:9`), so no
CI job can see the trees; the rule lived entirely in prose, and the eight files
it describes were patched *silently* once already. A guardrail that is only
written down is a guardrail that has already been broken once.

## 2. What the gate checks

`tools/check_vendored_pristine.py` runs three checks over the eight vendored
*code* trees (the `data/*/weights` directories are also git repositories, but
they hold downloaded weights rather than vendored source, so they are reported
and not checked):

| Check | Failure condition |
|---|---|
| Cleanliness | `git status --porcelain -uno` is non-empty — a tracked file was edited |
| Pin | a repository whose commit AGENTS.md pins is not at that commit |
| Revert | one of the nine disclosed files differs from its pinned commit (`git diff <pin> -- <file>`) |

Untracked additions are allowed on purpose: weights, caches and generated
configs land in these trees and are not modifications to upstream code.

On a clone there is no `data/` tree, so the gate prints `SKIP` and exits 0 —
the same convention `verify_submission_readiness.py` uses for `paper_warns`. The
rule is about the authoring machine's inputs, and `data_availability.md` already
tells a reader how to re-fetch them at the right commits.

## 3. What it found

All eight code trees are clean at their commits, and all nine disclosed files
are byte-identical to their pins:

```
OK: 20 checks across 8 vendored repositories, all pristine
  data/FlowMol3/repo            77cae22   modified tracked: 0
  data/lineageflow_upstream     ccef84a   modified tracked: 0
  data/kanzi_upstream           cfed9cf   modified tracked: 0
  data/HiDream-I1/repo          5f92bab   modified tracked: 0
  data/graphbfn/repo            a36ce07   modified tracked: 0
  data/lumina_image_2_0/repo    4a4d6f8   modified tracked: 0
  data/protbfn_abbfn/repo       869a9af   modified tracked: 0
  data/wan2_2/repo              42bf4cf   modified tracked: 0
```

One documentation defect surfaced while wiring it: `data_availability.md` said
*"8 files had been silently patched"* and *"ALL 8 files were reverted"* above a
table of **nine** rows, whose own closing note says *"All 9 files are bytewise
identical"*. The count is now 9 in all three places, and the paragraph names
the gate that re-verifies it. No number about a result changed.

## 4. Tests

`tests/test_tools/test_vendored_pristine.py` (6 tests) builds throwaway git
repositories in `tmp_path` and pins the gate's behaviour:

* no `data/` tree → zero checks, no failure;
* a clean tree → no problems;
* a modified tracked file → reported, with the filename;
* an untracked addition → not reported;
* a HEAD off its pin → reported;
* a disclosed file that differs from its pin → reported, and the same file
  before the edit → not.

The first draft of the gate had a real bug that these tests caught: `git status`
output was `.strip()`-ed before parsing, which ate the leading space of the
`XY` status columns and reported `mod.py` as `od.py`. The fix is `.rstrip("\n")`
plus a comment saying why the leading whitespace matters.

## 5. Wiring

Entry 16 of `todo.json`'s `gate_chain`, and part of CI's Gate 7. In CI it
prints `SKIP` for the reason above, which is correct: the check is for the
machine that holds the trees.

## 6. What this does not cover

The gate proves the trees are pristine *now*. It cannot prove that the evidence
already on disk was produced by pristine trees — that would need a run log per
artifact. `data_availability.md`'s disclosure table is the record of what was
patched and when it was reverted; this gate keeps the state it describes from
drifting again.
