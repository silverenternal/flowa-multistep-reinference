# Wave 262 P1: revert all vendored upstream modifications

## User directive (academic-integrity)

> 所有对于别人官方仓库里做的所有更改都要撤回
> (All changes made to other people's official repos must be reverted.)

This includes every vendored file in the project regardless of category
(bug_fix, logic_change, gray_zone).

## Scope

8 vendored files across 2 upstream repos. (Directive copy said "7" but the
enumerated list contains 8 entries: 3 FlowMol3 + 5 LineageFlow.)

### FlowMol3 (3 files — bug_fix category, still reverted per directive)

Upstream reference: `/home/hugo/codes/pocket/new/external_baselines/FlowMol/`
@ commit `77cae22`.

| # | Path | Lines (modified) |
|---|------|------------------|
| 1 | `data/FlowMol3/repo/flowmol/analysis/molecule_builder.py` | 86, 97 |
| 2 | `data/FlowMol3/repo/flowmol/models/flowmol.py` | 510, 534 |
| 3 | `data/FlowMol3/repo/flowmol/utils/ctmc_utils.py` | 2, 12 |

### LineageFlow (5 files — 4 logic_change + 1 gray_zone, all reverted)

Upstream commit: `ccef84a Prepare LineageFlow public release`
(via `git -C data/lineageflow_upstream checkout HEAD -- <file>`).

| # | Path | Lines (modified) | Category |
|---|------|-------------------|----------|
| 4 | `data/lineageflow_upstream/evaluation/evaluate_all.py` | 136, 157, 222 | gray_zone |
| 5 | `data/lineageflow_upstream/evaluation/foldability_omegafold.py` | 257, 339, 476, 523 | logic_change |
| 6 | `data/lineageflow_upstream/evaluation/novelty_mmseqs2.py` | 492, 517, 738, 857, 964, 970, 1047, 1048, 1063 | logic_change |
| 7 | `data/lineageflow_upstream/evaluation/run_foldability.py` | 136, 142, 181, 182, 215, 216 | logic_change |
| 8 | `data/lineageflow_upstream/evaluation/self_consistency_esmif.py` | 109, 134, 338, 343, 371, 374, 377, 379, 380, 382, 393, 399, 403, 409 | logic_change |

## Method

### LineageFlow (5 files)

```bash
cd data/lineageflow_upstream
git checkout HEAD -- \
  evaluation/evaluate_all.py \
  evaluation/foldability_omegafold.py \
  evaluation/novelty_mmseqs2.py \
  evaluation/run_foldability.py \
  evaluation/self_consistency_esmif.py
```

`git status` after: `nothing to commit, working tree clean`.

### FlowMol3 (3 files)

`data/FlowMol3/` is `.gitignore`d with no local upstream-tracking repo,
so used the mirror at
`/home/hugo/codes/pocket/new/external_baselines/FlowMol/` @ `77cae22`.

```bash
cp /home/hugo/codes/pocket/new/external_baselines/FlowMol/flowmol/analysis/molecule_builder.py \
   data/FlowMol3/repo/flowmol/analysis/molecule_builder.py
cp /home/hugo/codes/pocket/new/external_baselines/FlowMol/flowmol/models/flowmol.py \
   data/FlowMol3/repo/flowmol/models/flowmol.py
cp /home/hugo/codes/pocket/new/external_baselines/FlowMol/flowmol/utils/ctmc_utils.py \
   data/FlowMol3/repo/flowmol/utils/ctmc_utils.py
```

## Verification: md5 before/after

### LineageFlow

| # | File | md5 BEFORE (modified) | md5 AFTER (reverted) | Matches HEAD ccef84a? |
|---|------|------------------------|----------------------|------------------------|
| 4 | evaluate_all.py | `1ae077de61863eefa02e49cd1f356627` | `01c3f121e0ca2b8dd65666ed096120da` | YES |
| 5 | foldability_omegafold.py | `3c015823a4be1dd20b71f662cbd273d8` | `c21219e263a70404c5524177dddf78a7` | YES |
| 6 | novelty_mmseqs2.py | `64d5b01ae50b31e37d3cceaae664efeb` | `729d5a36d9a4b8fbce398f783336dae7` | YES |
| 7 | run_foldability.py | `d2abe86d665b8304f62db43684d37659` | `8b11a3390518eeb2ddcf5c48d9490d2d` | YES |
| 8 | self_consistency_esmif.py | `fa057a98da6c9fce9210cb34789c02bb` | `a4a0cf3c6e8ebdb2549c82613c060c6a` | YES |

### FlowMol3

| # | File | md5 BEFORE (modified) | md5 AFTER (reverted) | Matches upstream 77cae22? |
|---|------|------------------------|----------------------|---------------------------|
| 1 | molecule_builder.py | `5865bc02b63779f4ec130887e12a3ea7` | `449e98677581fab0474356bfe667fb0d` | YES |
| 2 | flowmol.py | `d3a0149197f0d723dd386267a56612a7` | `7cca52b0cfff6837214f4297c84f823e` | YES |
| 3 | ctmc_utils.py | `604f1faacdc1da4aec2501285294ee74` | `7777b6f887abecdde9dc7ec54d4a84f5` | YES |

All 8/8 files: md5 AFTER = upstream reference md5.
All 8/8 files: bytewise identical to upstream commit.

## Confirmation: no vendored file modifications remain

- `git -C data/lineageflow_upstream status` -> `nothing to commit, working tree clean`
- `git -C data/lineageflow_upstream diff HEAD -- <each file>` -> empty (0 lines each)
- FlowMol3 files: bytewise identical to upstream reference at commit `77cae22`

## Hard-rule compliance

- DO revert ALL files (no exception): **DONE** (8/8, including 3 bug_fix category files)
- DO preserve D.4 30/30 PASS: no test-relevant code touched outside vendored files
- DO preserve mkdocs 0 warnings: no docs-side change beyond this audit doc
- DO preserve claims consistency no drift: no claim doc touched
- DO NOT touch Wave 242 GPU task: Wave 242 is not running; no wave touched

## Notes

- The user directive copy in the task header says "7 files" but the
  enumerated list contains 8 (3 FlowMol3 + 5 LineageFlow). The
  enumeration is canonical because the directive says "ALL changes ... to
  official repos" and the 5th LineageFlow file (evaluate_all.py) is on the
  enumeration list with the gray_zone category flagged.
- bug_fix category reverts are intentional per user directive even though
  they had been technically defensible under "bug_fix acceptable" criteria
  used in Wave 261 P3.
- LineageFlow was reverted via `git checkout HEAD --` because the repo is
  tracked at upstream commit ccef84a (HEAD = upstream HEAD).
- FlowMol3 was reverted via `cp` because the vendored directory is
  gitignored and there is no in-tree upstream-tracking repo. The mirror
  at `/home/hugo/codes/pocket/new/external_baselines/FlowMol/` @ `77cae22`
  is the canonical upstream source.